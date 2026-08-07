# PR description

## Summary
**User impact:** when a build honestly reports "I could not verify this — a tool the
project needs is missing on this machine", the harness ignores the report and spends
the whole expensive review pass anyway (automated gates plus two model reviewers)
judging work everyone already knows cannot be verified. Honesty costs the operator
time and money, and a build that stays quiet about the same problem actually looks
better in review.

This PR makes the driver check that report the moment the build finishes: it runs the
detect command for the missing tool, and only if the tool is *genuinely* absent does
the run skip straight to the human sign-off — parked, and resumable once the tool is
installed. A report the check disproves buys the builder nothing: the full review runs
as before, with the disproven claim flagged for the human. Opt-in, off by default.

Reported in [#341](https://github.com/eduralph/pdca-harness/issues/341).

## What to look at
The new module `template/src/pdca_harness/dependency_halt.py` (the deterministic
adjudicator: report → matching detect row → run its command → exit code decides) and
the small routing change in `template/src/pdca_harness/driver.py` where a build
completes. To try it: set `dependency_halt = true` under `[driver]`, give a bundle a
`build-notes.md` carrying `NEEDS-HUMAN external dependency: <name> — …` plus a
`[[doctor.checks]]` row for `<name>`, and run the bundle — a failing detect command
parks it at sign-off; a passing one runs the full review. Or run the new test suite:
`cd template && PYTHONPATH=src python3 -m unittest tests.test_builder_dependency_halt`.

## Root cause
`driver.advance` at BUILT ran `gates.run_gates` → `leaves.run_review` →
`run_advisory_leaves` unconditionally, consulting nothing the builder wrote
(driver.py:75-92 on main); the close fast path that already knows how to skip the
Check spend was reachable only from a Plan-time disposition hint, one beat too early
for a dependency the builder discovers while building.

## Fix
- `dependency_halt.py` (new): parses the builder-contract marker via the one existing
  parser (`assemble._declared_external_deps`), resolves each declared name to a
  `[[doctor.checks]]` row — registered rows win over the builder's proposed fenced
  TOML block, so a builder cannot out-vote human-blessed config — and runs the row's
  detect cmd. Verdicts: confirmed (non-zero exit), refuted (exit 0), unconfirmed (no
  resolvable row; malformed TOML lands here — failing toward review, never away).
- `driver.advance` at BUILT: adjudicates before the normal Check band. Confirmed ⇒
  reuse the existing close machinery (`gates.run_close_gates` N/A matrix + a blocked
  review note whose NEEDS-HUMAN bullets reach SUMMARY §6) and halt at
  AWAITING_SIGNOFF — never a terminal state; sign-off keeps those. The bundle resumes
  via ordinary iterate-do.
- The verdict is recorded (`dependency-adjudication.json`, archived with its attempt)
  on both outcomes; refutations are lifted into §6 where `pdca act index` reads.
- `doctor.probe` (new): the inline detect-cmd subprocess duplicated at two doctor call
  sites is extracted and shared with the new adjudicator, so probing cannot drift.
- Config: `[driver].dependency_halt`, a strict boolean defaulting to off (a quoted
  "true"/"false" fails closed to off, loudly — this setting can skip the reviewer).
  Off ⇒ no probe is spawned and behaviour is byte-identical to today.

## Verification
- **Claim:** on current main the honest declaration changes nothing — Check runs
  unconditionally. **Checked:** `template/src/pdca_harness/driver.py:75-92` on main —
  the BUILT branch runs gates → reviewer → advisory leaves regardless of build-notes;
  the close fast path is reachable only pre-Do.
- **Claim:** the halt reuses existing, tested machinery rather than inventing a
  parallel path. **Checked:** `template/src/pdca_harness/gates.py:152`
  (`run_close_gates`, reused as-is), `template/src/pdca_harness/state.py:36`
  (`CLOSE_MARKER`, the pattern the new record constant sits beside),
  `template/src/pdca_harness/assemble.py:482` (`_declared_external_deps` — the single
  marker parser, delegated to rather than duplicated).
- **Claim:** the probe is the same one the Plan-exit guard uses. **Checked:**
  `template/src/pdca_harness/doctor.py:395` and `:539` on main — the identical inline
  `subprocess.run(..., shell=True, cwd=cfg.root)` at both sites, now extracted to
  `doctor.probe` with both callers refactored onto it.
- **Test:** `template/tests/test_builder_dependency_halt.py` — 13 tests covering:
  confirmed claim skips reviewer and halts at sign-off (via registered and proposed
  rows), blocked bundle resumes through iterate-do, refuted claim runs full Check and
  reaches §6, a registered row beats the builder's proposed row, unresolvable and
  malformed proposals run full Check, off spawns no probe and writes no record, and
  the strict-boolean config load. Fails pre-fix (with the driver routing reverted, the
  reviewer-not-invoked assertions fail on main's unconditional Check), passes
  post-fix. Full offline driver suite: 1386 tests OK; repo-root render/update suites
  (the documented `pdca.toml.jinja` key renders as valid TOML): 7 tests OK.

Fixes #341
