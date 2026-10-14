# Build notes — issue 605 / check-decorrelation-note-not-deferred

Target: `eduralph/pdca-harness` `main` @ `b5f5c29` (worktree `$PDCA_WORKTREE`). Line numbers
below are on the patched tree unless marked "base".

## What changed and why

The Check-side decorrelation note (`check-advisory-decorrelation.md`, written by
`leaves._decorrelation_note`, base `leaves.py:3637-3642`) was read by
`assemble.collect_needs_human` as an ordinary advisory finding, so its row was a plain HUMAN
item with `no_verdict=False`. `autoiterate.deferrable` (base `autoiterate.py:300-326`) then
held it in the ledger, and every later §6 showed it, even after a later round's selection
succeeded and wrote no note.

1. `template/src/pdca_harness/assemble.py:405-418` — in the advisory loop of
   `collect_needs_human`, the items read from the artifact whose stem is `decorrelation` are
   marked after the fact with `it._replace(no_verdict=True)`. This copies the peer the brief
   cites, the missing-review placeholder at `assemble.py:402-404`. I did not put the check in
   the `no_verdict=` lambda: `_items_from_artifact` only calls that for a placeholder (an
   artifact with a `pdca:leaf-status` marker), and the note has no marker, so it would never
   run. The check keys on the artifact name, not the note text.
2. `template/src/pdca_harness/assemble.py:47-54` — the `NeedsHumanItem.no_verdict` comment now
   says "a row about this Check's own run": a review or gate with no verdict, OR the note on
   this Check's own advisory selection (#605).
3. `template/src/pdca_harness/autoiterate.py:307-314` — the `deferrable` docstring is widened
   the same way.
4. `template/src/pdca_harness/flow.py:382-383` — the auto-iterate notice now says
   "N row(s) about this Check's own run left for the next Check to re-check", not
   "review/gate row(s) with no verdict … re-run". This uses the wording the brief suggests.
5. `template/tests/test_autoiterate.py:766` — the existing #409 test asserted the old notice
   text. I updated that one assertion to the new text. The behaviour under test is the same.

No flag was added. The brief chose to widen `no_verdict` (Scope), and the mechanism it rests
on already holds: every Check re-runs `_select_advisory`, which unlinks the prior note
(`leaves.py:3655` base) and writes it again only if decorrelation still fails.

## Test

`template/tests/test_autoiterate.py:2299` — new class `CheckDecorrelationNoteIsNotDeferred`.
A copy of the whole test file is at `results/issue_605/template/tests/test_autoiterate.py`.

- Round 1 (`_round1`): a stub bundle with a C4 IMPL row (`_IMPL_ONLY_REVIEW`). The
  config is `advisory_selection = {"mode": "vendor-complement"}` with one advisory leaf of
  family `codex`, and there is no `loop-telemetry.json`. The REAL `leaves._select_advisory`
  writes the note (family unknown). §6 shows it (precondition). Then
  `autoiterate.write_decision(d, collect_needs_human(...))`, `flow._apply_decision` (records
  §9, `apply_now=False`), and one `driver.advance` (the iterate-do archive). It asserts the
  round-1 note file is gone before round 2, so the premise is checked, not assumed.
- Case 1 (`:2348`): `loop-telemetry.json` now records builder family `claude`, so round 2's
  real selection picks the `codex` complement and writes no note. Round 2 runs through
  `driver.run_issue` (stub Do, real gates, real `run_advisory_leaves`, `run_review` mocked to
  a clean review). Asserts: no note file, no note text in §6, not in `autoiterate.deferred`,
  not in `flow.accept_blockers`.
- Case 2 (`:2363`): same, with no telemetry, so round 2's own `_select_advisory` writes the
  note again. Asserts: exactly one §6 row with the note text, it is `- [ ] …`, it is in
  `accept_blockers`, and the ledger does not hold it.
- Criterion (3) (`:2375`): `flow._maybe_auto_iterate` on a round with the note + an IMPL
  row. Its notice has no "with no verdict" and says "1 row(s) about this Check's own run left
  for the next Check"; nothing is written to the ledger.

## Red → green (run with the target's own driver-suite command, `cd template &&
PYTHONPATH=src python3 -m unittest …`, as in `engine/scripts/run-suite.sh`, wrapped in
`timeout`)

- Post-fix: `tests.test_autoiterate` — 143 tests OK. Full driver suite
  (`unittest discover -s tests`) — 2372 tests OK (2 skipped).
- Production hunks reverted (`git checkout -- template/src`), test kept: 7 failures. All 3
  new tests fail, plus the 4 subtests of the updated #409 notice assertion. Case 1's failure
  is the RED the brief names: round 2's §6 holds
  "- [ ] advisory reviewer 'adversary' could not be decorrelated from the builder — the
  builder family that ran is unknown (no loop-telemetry.json); …", carried from the ledger.
  Case 2 fails because the ledger holds the note. Criterion (3) fails because the notice
  says "1 finding(s) needing human judgment deferred".

## Refuting my own test

- **(a) Genuine red?** Yes. With `template/src` reverted, the three new tests fail (output
  above); with the fix reapplied, they pass.
- **(b) Production path?** Yes. The note is written by `leaves._select_advisory` (the real
  writer) in both rounds. The decision goes through `autoiterate.write_decision` and
  `flow._apply_decision`. The iterate goes through `driver.advance`. Round 2 goes through
  `driver.run_issue`, which calls the real `run_advisory_leaves` → `_select_advisory`. §6 comes
  from `assemble.assemble_summary`. Only `leaves.run_review` is mocked (to a clean review), as
  in the existing #409 test at `test_autoiterate.py:736-760`. The fix does not touch it.
- **(c) Fixture includes the fault?** Yes. Round 1 really has no `loop-telemetry.json`
  (asserted) and really writes the note beside a real IMPL row. The ledger, archive and
  re-selection are all real. Case 2 keeps the fault live in round 2 to show the row is still
  shown and still blocks accept while it lasts.

## Ruled out

- Adding the check to the `no_verdict=` lambda in the advisory loop: it never runs for the
  note (no status marker), as the brief explains. It would be a no-op.
- Matching on the note's text: fragile, and the brief says to key on the artifact.
- A new `NeedsHumanItem` field: the brief chose to widen `no_verdict`. A new field would need
  the same handling in `deferrable`, the flow notice count, and every reader that checks
  `no_verdict`. That is the same behaviour with more code.
- The plan-side note (`_plan_decorrelation_note`) is out of scope (#603).

## Commit-readiness

The target has no formatter or pre-commit config (no `.pre-commit-config.yaml`, no ruff/black
settings). Every added line is ≤ 100 columns, matching the file style. No docs quote the old
notice text (grep for "with no verdict left" / "review/gate row" found nothing outside the
patch). The target requires a DCO `Signed-off-by:` trailer on the commit (`CONTRIBUTING.md:9-17`).
That is for the publish step to add.

## Housekeeping

While checking the red leg I saved the production hunks to `$PDCA_WORKTREE/.prod.patch`
(untracked, not in `patch.diff`). I did not delete it, per the harness rule. It can be
dropped with the worktree.

## Ordering

Built on `b5f5c29` as the brief cites. #603 also edits `collect_needs_human` and appends to
`test_autoiterate.py`. If 603 lands first, this patch may need a rebase. The hunks are small
and in separate spots (advisory loop, new class at end of file).
