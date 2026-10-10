# Build notes — issue 603 / plan-advisory-tick-survives-iterate-do

Target: eduralph/pdca-harness @ main, base `b5f5c29`. Worktree `$PDCA_WORKTREE` =
`/home/eddie/pdca/pdca-harness.pdca-wt-l0`. Line numbers below are post-patch in that tree.

## What changed

1. **A record of cleared plan findings** — `plan-advisory-cleared.json`
   (`template/src/pdca_harness/assemble.py:472`, `PLAN_ADVISORY_CLEARED`). `{"items": [...]}`,
   accumulated across rounds, written atomically (temp sibling + replace).
   Why this home (brief Scope (c)):
   - it starts with `plan-advisory-`, so the iterate-plan archive
     (`driver.py:478-482`, `d.glob("plan-advisory-*")`) and the plan-advisory re-run's unlink
     (`leaves.py:4341-4342`) both take it, with no extra code;
   - it is not `.md`, so no reader of `plan-advisory-*.md` (`assemble.py:486`, `leaves.py:3917`,
     `leaves.py:4272`) parses it as findings;
   - it matches none of `state.DOWNSTREAM_GLOBS` (`state.py:155`), so iterate-do keeps it.
   `plan-advisory-benefit.json` already lives under the same prefix with the same lifetime,
   which is precedent for this choice.

2. **Recording the ticks** — `assemble.carry_plan_advisory_ticks` (`assemble.py:510`), called
   from the new `driver._carry_plan_advisory_ticks` (`driver.py:344`), wired into the
   ITERATE_DO branch at `driver.py:136`, after `_retire_cleared_deferrals` and before
   `_archive_iteration` moves SUMMARY.md — the same spot as the brief's peer callsite.
   - Ticks are read with `signoff.cleared_needs_human` (strict, last §6 only), so a `- [x]`
     quoted into §5 records nothing (guard test `test_a_tick_quoted_into_section5_clears_no_plan_finding`).
   - Only an exact match (after `autoiterate._norm`) against a current plan finding counts.
     No fuzzy matching: an edited row clears nothing (fails closed).
   - A text that is also still an open row elsewhere in §6 is not recorded (fails closed).
   - Best-effort wrapper in the driver: an exception prints a warning and the rows stay open.
   - Only on iterate-do. On iterate-plan the archive moves the plan evidence, so a record
     would be thrown away anyway.

3. **Not rendering cleared findings** — `collect_needs_human` drops plan findings whose
   normalised text is in the record (`assemble.py:450-451`). They are dropped, not shown as
   `- [x]`, so assembly never writes a tick (Scope (a)). Because `collect_needs_human` is the
   single source for §6, auto-iterate's `deferrable`/`defer` also stop seeing them, so they
   are not re-deferred.

4. **Ledger copy** — `_deferred_needs_human` treats recorded plan texts as already seen
   (`assemble.py:676`), so a deferred-findings ledger entry with the same text cannot bring
   it back (Scope (b)). In the normal path the tick also retires the ledger entry through the
   existing `_retire_cleared_deferrals`; the filter covers a ledger that still holds it.

Both iterate entry points go through `driver.advance`'s ITERATE_DO branch: the CLI
(`pdca signoff --iterate-do` then `pdca run`) and the flow (`flow.py:516`,
`_isolate(d, "build/check", lambda: driver.advance(d, cfg))`). So one wiring point covers both.

## Alternatives ruled out

- **Retire plan findings through the #409 ledger** — `retire_cleared` deliberately retires
  nothing for a tick on a fresh finding (`autoiterate.py:366-370`) and returns at once with
  an empty ledger. Changing that contract would touch the ledger's carefully argued rules.
- **Archive plan-advisory files on iterate-do** — out of scope (it would let an unticked
  finding stop blocking accept).
- **Keying the reset on file content hash** — the brief says a re-run with the same bytes is
  new evidence; the prefix-based lifetime gives exactly event-driven reset.
- **Rendering cleared rows as read-only lines in §6** — allowed by Scope, but dropping them is
  simpler and cannot be mistaken for a checkbox by any §6 reader.

## Test

`template/tests/test_autoiterate.py:2295`, class `PlanAdvisoryTickSurvivesIterateDo`
(copy in this bundle at `template/tests/test_autoiterate.py`). Five tests:

- `:2361` tick survives two iterate-dos; the unticked finding stays open and in
  `flow.accept_blockers` / `signoff.open_needs_human` at N+1 and N+2 (criterion + (i)).
- `:2378` iterate-plan, then a byte-identical `plan-advisory-x.md` reopens it (ii).
- `:2392` plan-advisory re-run through the real stub leaf (`leaves.run_plan_advisory`),
  same text, reopens it (ii, the `leaves.py:4341` event).
- `:2412` ledger leg (iii): asserts `autoiterate.deferrable` keeps the plan finding, seeds the
  ledger, ticks, iterates; then re-seeds the ledger and checks it still stays out of §6.
- `:2437` guard: a tick quoted into §5 clears nothing (green both before and after).

Only pre-existing API is called from the tests, so the reverted tree loads the module and
fails on behaviour.

Runs: the project verify script
(`PDCA_BUNDLE=… PDCA_WORKTREE=… ./engine/scripts/run-verify.sh` from pdca-pdca) printed
`PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`. Red leg: 4 failures out of the
5 new tests, each `'- [ ] the success criterion names no test' unexpectedly found in …` (or the
stub row). Full template suite with the fix: `Ran 2374 tests … OK (skipped=2)`.

## Refuting my own test

- **(a) Genuine red?** Yes. `run-verify.sh` reverted the production hunks (`assemble.py`,
  `driver.py`) and re-ran the module: 4 tests failed with the ticked row back as `- [ ]`.
  The 5th is a guard by design and is green both ways.
- **(b) Production path?** Yes. The tests call `signoff.record`, `driver.advance`,
  `gates.run_gates`, `assemble.assemble_summary`, `assemble.collect_needs_human`,
  `leaves.run_plan_advisory` and `flow.accept_blockers` — the real code paths. Nothing is
  mocked.
- **(c) Fixture includes the fault?** Yes. The plan-advisory artifact stays in the bundle
  through iterate-do exactly as in production (asserted: `plan-advisory-x.md` still exists
  after the archive), the ledger leg seeds a real ledger entry, and the re-run leg uses the
  real stub plan-advisory leaf that writes byte-identical text.

## Commit-readiness

The target repo has no formatter config, no pre-commit hook and no `core.hooksPath`
(checked `.github/workflows`, `CONTRIBUTING.md`, `git config core.hooksPath`). No added line
is over 100 characters, matching the file's style. No ruff/pyflakes installed on this host.

## Overlap

#605 also edits `assemble.collect_needs_human` and `_deferred_needs_human`. Expect a textual
conflict at `assemble.py:450` and `:676` when 605 is folded on top; the changes are
independent.
