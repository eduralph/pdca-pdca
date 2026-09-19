# PR description

## Summary
**User impact:** A Plan session that picks its own issues (the CSV batch run and the
plain `plan` batch) can finish and print nothing about the briefs it just wrote. If one
of those briefs has an empty Success criterion — or an empty Slug or Repo + branch
target — you are never told. Nothing further down catches it either, so the empty brief
goes into the build with no stated end result, and the Check summary is assembled from
the blank field. You find out much later, from work that was built against nothing.

This PR makes such a session re-read, at the end, every brief it created or changed, and
report what is wrong with them.

Reported in [#549](https://github.com/eduralph/pdca-harness/issues/549).

## What to look at
The change lives in the session-end check for interactive leaves, plus its tests and one
documentation paragraph. Two things are worth a reviewer's eye: which sessions the new
behaviour applies to (only a Plan session the driver could not register a bundle set
for), and the rule for "the session's own work" (a brief is re-read only if it appeared
or changed since the session started).

To try it: start a CSV or default batch Plan, run `/handoff issue_<a>` for a brief that
is fine, then write a second brief with an empty **Success criterion** and end the
session. Before this change the terminal stays quiet; after it, the reap prints
`issue_<b>: brief.md field 'success criterion' is empty …`.

## Root cause
`stop_problems` re-reads the artifacts of the bundles the driver registered at spawn,
but a CSV/default batch Plan registers none — it chooses its issues mid-session
(`template/src/pdca_harness/leaves.py:1197` on `main`, `seeded = []` when `ids is None`).
With an empty bundle list the check falls through to its tail
(`template/src/pdca_harness/handoff.py:622-625`), which asks only whether some
`/handoff` passed during the session; if one did, it returns with nothing said about any
brief. A single `/handoff` for one issue therefore silences the check for every other
brief the same session wrote. The id-seeded batch is not affected — its bundles are
registered and each brief is re-read (`handoff.py:609-621`).

## Fix
`session()` now records a fingerprint (sha256 of the bytes) of every existing
`issue_*/brief.md` when — and only when — it opens a planner session with no registered
bundle set. At reap, the check diffs that snapshot against the bundle root and treats the
briefs that appeared or changed as the session's work set, feeding them into the same
per-bundle loop a registered session uses. So:

- a changed brief is checked and reported, `/handoff` or not;
- a brief that predates the session and is byte-identical is not re-read, even if
  malformed — it is not this session's work;
- a session that changed no brief behaves exactly as before (a passing `/handoff`
  discharges it, otherwise the existing "registered no bundle set … and verified none"
  item);
- a brief that cannot be read (no permission, a directory in its place) becomes its own
  `could not check (…)` item and never hides the others;
- the broken `[[doctor.checks]]` table stays one item for the session, and the re-read
  briefs are then checked with `dependencies=False`, as registered bundles are.

The snapshot is stored in the driver-registered half of the session state, which wins
over the scratch file the leaf can write, so a session cannot blank its own baseline.
The reap still only reports: it opens nothing, writes nothing, changes no bundle.
Sessions with a registered bundle set and the `act` role run the same code as before —
including the case where some unrelated brief elsewhere cannot be read, which now cannot
cost them their exit contract. `docs/01-render-and-integrate.md:178-187`, which promised
the old behaviour in so many words, is updated.

## Verification
- **Claim:** a Plan session opened with no registered bundle set reports, at session end,
  every problem in every brief it created or changed — whether or not a `/handoff` passed
  — and reports nothing for briefs it did not touch.
- **Checked:** `template/src/pdca_harness/handoff.py:609-625` on `main` — the empty-bundle
  tail that returns on `state["passed"]` without reading a brief; `handoff.py:609-621` —
  the registered path the fix now reuses for the derived work set;
  `template/src/pdca_harness/leaves.py:1193-1199` — the batch Plan opening the session
  with `seeded = []`, which is what makes the tail reachable;
  `docs/01-render-and-integrate.md:178-187` — the documented promise that had to change
  with it.
- **Test:** `template/tests/test_handoff_reap.py`, new class
  `UnregisteredPlanRereadsWhatItWrote` (8 tests, driven through the real
  `handoff.session`, no mocks). With the production changes reverted and the tests kept,
  7 of the 8 fail — including the reported case, which fails on an empty stderr. All 8
  pass with the fix. The two that also pass on `main` pin behaviour that must not move
  (an untouched pre-existing brief, and a registered Plan with an unreadable brief
  elsewhere); each of those fails against an earlier draft of the fix, so they are not
  free passes.
- **Suites:** the full offline suite is green (1928 driver tests, 24 root tests, 2
  pre-existing skips); the docs lint and site render/link audit are clean.

Follow-up worth a separate change: `template/.claude/commands/handoff.md.jinja:21-24`
still tells the model that a session which picks its own issues is checked by `/handoff`
"instead of re-reading what the session wrote". That is now an understatement rather than
a risk, and the file was deliberately left out of this change's scope.

Fixes #549
