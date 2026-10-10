## Summary
**User impact:** When you send a fix back for another build round (iterate-do), every
finding from the plan review comes back unticked in the next round's sign-off
checklist, including the ones you already cleared. You have to clear the same items
again every round, and accept stays blocked until you do. On real bundles this meant
re-clearing 5 findings in each of 4 rounds, and 6 findings across 3 rounds.

This PR remembers which plan-review findings you ticked, so they stay cleared in later
rounds until the plan review itself is redone.

Reported in [#603](https://github.com/eduralph/pdca-harness/issues/603).

## What to look at
- The change is in how the sign-off checklist (SUMMARY.md §6) is built, plus one new
  step when an iterate-do starts that saves your ticks on plan-review findings.
- To try it: take a bundle with a plan-review finding, tick it in §6, sign off with
  `iterate-do` and run the next round. Before this PR the finding is unticked again.
  With it, the finding is gone from §6, and it stays gone after another iterate-do.
- Things that still reopen a finding, on purpose: an iterate-plan, or running the plan
  review again (even when it raises exactly the same text). A finding you never ticked
  stays open and still blocks accept.

## Root cause
Every assembly of §6 re-reads all `plan-advisory-*.md` files and lists each finding as an
open row. An iterate-do keeps those files (only iterate-plan archives them), and the one
place that reads ticks at the iterate, `_retire_cleared_deferrals`, handles only the
deferred-findings ledger, so the plan-review ticks were lost.

## Fix
- **Save the ticks.** New `assemble.carry_plan_advisory_ticks` runs in the iterate-do path,
  before SUMMARY.md is archived. It reads ticks only with `signoff.cleared_needs_human`
  (the last §6 heading, not a quote elsewhere in the document). It records a finding only
  when the ticked text exactly matches a current plan finding and that text is not also
  still open in another §6 row. The record grows across rounds in
  `plan-advisory-cleared.json`, written to a temp file and then renamed into place.
- **Skip saved findings.** `collect_needs_human` leaves recorded findings out of §6. They
  are dropped, not rendered as `- [x]`, so assembly never writes a tick that would count
  as the human's. `_deferred_needs_human` treats them as already seen, so a ledger copy
  cannot bring one back.
- **Lifetime.** The file name starts with `plan-advisory-`, so the existing iterate-plan
  archive and the plan-review re-run's cleanup both remove it with no new code. It is not
  `.md`, so nothing reads it as findings, and it does not match `state.DOWNSTREAM_GLOBS`,
  so an iterate-do keeps it. `plan-advisory-benefit.json` already uses the same prefix and
  has the same lifetime.
- **Failure mode.** If the record cannot be read or written, the driver prints a warning
  and the findings show as open again, which is the safe side.

## Verification
- **Claim:** a ticked plan finding is not an open row after one iterate-do, and still not
  after a second one with no new tick. An unticked finding stays open and blocks accept.
  - **Checked:** `template/src/pdca_harness/assemble.py:446-448` on `main` (`b5f5c29`) is
    the loop that re-reads every `plan-advisory-*.md`. With the patch it filters by the
    record (`assemble.py:450-451`).
  - **Test:** `template/tests/test_autoiterate.py:2361`
- **Claim:** an iterate-do keeps the plan-review files, so nothing removed the stale rows.
  - **Checked:** `template/src/pdca_harness/driver.py:460-464` on `main` archives
    `plan-advisory-*` only when `include_brief` is true (iterate-plan).
- **Claim:** nothing carried the tick before this change.
  - **Checked:** `driver.py:317-340` on `main` returns at once when the ledger is empty
    (`:332-333`). `autoiterate.py:366-370` retires nothing for a tick on a finding from
    the current Check.
- **Claim:** the tick is saved in the iterate-do path, before SUMMARY.md moves.
  - **Checked:** with the patch, `driver.py:136` calls `_carry_plan_advisory_ticks`
    (`driver.py:344`) after `_retire_cleared_deferrals` and before `_archive_iteration`.
    The CLI path (`pdca signoff --iterate-do` then `pdca run`) and the flow path
    (`flow.py:516`) both go through `driver.advance`, so this one call covers both.
- **Claim:** iterate-plan, or a plan-review re-run with the same text, reopens it.
  - **Checked:** `driver.py:460-464` and `leaves.py:4341-4342` on `main` both remove
    `plan-advisory-*`, and that includes the record.
  - **Test:** `test_autoiterate.py:2378` (iterate-plan, byte-identical text) and `:2392`
    (re-run through the real stub plan-review leaf).
- **Claim:** a deferred-findings ledger copy does not bring a ticked finding back.
  - **Checked:** with the patch, `assemble.py:676` adds the record to the seen set in
    `_deferred_needs_human`.
  - **Test:** `test_autoiterate.py:2412`
- **Claim:** a `- [x]` quoted outside §6 clears nothing.
  - **Test:** `test_autoiterate.py:2437`. This is a guard and passes with or without the fix.
- **Red/green:** with the `assemble.py` and `driver.py` changes reverted, 4 of the 5 new
  tests in `PlanAdvisoryTickSurvivesIterateDo` (`test_autoiterate.py:2295`) fail, each
  because the ticked row is back as `- [ ]`. With the fix all 5 pass. Full template
  suite: `Ran 2374 tests … OK (skipped=2)`. The tests use only existing API and call the
  real `signoff.record`, `driver.advance`, `gates.run_gates`, `assemble.assemble_summary`
  and `flow.accept_blockers`, with nothing mocked.

Overlap: #605 also edits `collect_needs_human` and `_deferred_needs_human`. Expect a textual
conflict there if it lands after this PR. The two changes do not depend on each other.

Fixes #603
