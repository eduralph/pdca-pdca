## Summary
**User impact:** when a run stacks several waves of fixes on one shared line, and
someone force-pushes a rewrite of one of those fixes' branches near the end of the
run, the run still finishes green: every fix shows as complete and the command
exits 0. The line then contains commits that no open PR holds any more, and the PRs
built on it can merge work nobody is reviewing. Separately, a run can stop with
"could not fetch" just because another git command happened to be running in the
same checkout at that moment.

This PR adds a last check at the end of the run that reports any such rewrite and
exits 1, and retries that one fetch once before giving up.

Reported in [#695](https://github.com/eduralph/pdca-harness/issues/695).

**Stacked PR:** this builds on #693 (it extends the run-outcome channel #693 adds
from the flow to the CLI's exit code) and is ordered after #673 and #694, which
edit the same fold code and docs section. Review it after those land.

## What to look at
- **The end-of-run check.** After the last wave (and after Act), the run looks again
  at every branch it folded onto the line. If one was rewritten so it no longer
  contains the commit the line took from it, stderr gets one line per branch naming
  the bundle, the branch, that commit, and how to fix it (restore the branch, or
  rebuild the later PRs on it), and the exit code is 1, even if other bundles are
  only held (exit 3).
- **When the check itself can't run** (fetch fails twice, or git can't answer the
  ancestry question): the run prints which branches to check by hand and exits 1.
  It does not tell you to re-run, since the line is already pushed.
- **What stays quiet:** a branch that only moved forward, a branch that was merged
  and deleted, and a run that already stopped at a fold (that fold already reported
  the rewrite, so you see it once).
- **The fetch retry:** only the fetch made for this carried-branch check gets a
  second try. Every other git step behaves as before.

To try it: in a stack-mode run with two waves (`A`, then `B` depending on `A`),
force-push a rewrite of `fix/A` while `B` builds. Before this PR the run ends with
exit 0; with it you get one line naming `issue_A` and exit 1. The new test file does
exactly this against real git.

## Root cause
The rewrite check (`_carried_tips`, added in #633) only ran at the start of a fold,
and folds run only between waves, so nothing checked after the last one. Its fetch
also ran before the fold's integration lock, with a single attempt, so one ref-lock
clash with another git process stopped the run.

## Fix
- `integrate.py`: the rewrite judgment moves into `_carried_rewrite`, shared by the
  fold's check and a new `rewritten_carried`, which re-checks carried branches per
  target without raising and returns `(rewritten, unchecked)`. One target or branch
  that can't be checked does not hide a rewrite found on another.
  `IntegrationError` gains an optional keyword-only `cause` (the short "what failed",
  without the fold's remedy); `_fetch` and `_in_line` set it, and their messages stay
  byte-identical. `_fetch` takes `attempts=` (default 1); the carried-branch checks
  pass 2, with `_FETCH_RETRY_PAUSE` between tries.
- `flow.py`: `_drive_and_act` tracks `line_stopped` at the fold-error and red re-gate
  breaks, and after Act and the existing end-of-run reports calls
  `_report_late_rewrites`, which prints the lines and records `rewritten` /
  `unchecked` in #693's `holds` collector, after the holds so it outranks them.
- `cli.py`: `_results_rc` maps `rewritten` / `unchecked` to exit 1 ahead of the hold
  rule. The `{id: state}` return types are unchanged.
- `docs/07-crosscutting.md` and the `integrate.py` module docstring: the "next fold
  stops the run" text now also covers the end-of-run check and the retried fetch.

Out of scope: a carried branch deleted after the last fold (closed unmerged or
squash-merged) is not judged at the end of the run; the run does not repair the
line or re-drive any bundle; merge mode is unchanged.

## Verification
Line numbers are on this PR's branch (the stacked line with #693, #673 and #694).

- **Claim:** a rewrite after, or during, the last fold is reported and the run
  exits 1, ahead of any hold.
  - **Checked:** `template/src/pdca_harness/flow.py:2491`, `:2651`, `:2667`
    (`line_stopped`), `:2681-2697` (check runs after `_report_conflict_holds`, its
    result goes into `holds` last), `:2701-2733` (`_report_late_rewrites`);
    `template/src/pdca_harness/cli.py:698`, `:730` (exit 1 before the hold rule).
  - **Test:** `test_a_rewrite_while_the_last_wave_builds_is_reported_and_exits_1`
    (:234), `test_a_late_rewrite_outranks_a_hold` (:246),
    `test_a_rewrite_during_the_last_fold_is_reported_and_exits_1` (:258).
- **Claim:** the end-of-run check and the fold make the same judgment.
  - **Checked:** `template/src/pdca_harness/integrate.py:697-736` (`_carried_tips`),
    `:739-752` (`_carried_rewrite`), `:755-807` (`rewritten_carried`).
- **Claim:** a check that can't run fails closed with a clear message and does not
  hide a rewrite found elsewhere.
  - **Checked:** `integrate.py:85-98` (`IntegrationError.cause`), `:1186-1197`
    (`_in_line`), `:1530-1562` (`_fetch`).
  - **Test:** `test_an_end_of_run_check_that_cannot_fetch_is_named_and_exits_1`
    (:279), `test_a_target_that_cannot_be_fetched_does_not_hide_a_rewrite_on_another`
    (:341), `test_a_target_that_cannot_be_fetched_does_not_stop_the_check_of_the_next`
    (:346), `test_a_branch_that_cannot_be_judged_does_not_hide_a_rewrite_beside_it`
    (:351).
- **Claim:** no false or double report.
  - **Test:** `test_a_fast_forward_of_a_carried_branch_reports_nothing` (:391),
    `test_a_carried_branch_merged_and_deleted_reports_nothing` (:399),
    `test_a_rewrite_the_next_fold_stops_on_is_reported_once` (:413).
- **Claim:** one failed fetch no longer stops the fold; a persistent one still does,
  with the fold's original message.
  - **Test:** `test_one_failed_fetch_does_not_stop_the_fold` (:461),
    `test_a_fetch_that_keeps_failing_still_stops_the_fold` (:473),
    `test_a_fold_stopped_by_a_git_failure_in_its_check_still_says_to_re_run` (:483).

All in `template/tests/test_integrate_carried_rewrite_late.py` (13 cases, real git,
run cases driven through `cli._flow`). With the production change reverted, 9 fail
on their assertions and none error; with it, all 13 pass. The 4 that pass either way
are the no-false-report, no-double-report and unchanged-fold-message guards. The full
driver suite (2526 tests, 2 skipped, including every #633 test in
`test_integrate_stack_bases.py` and all of `test_flow_same_wave_conflict.py`) and the
root suite (24 tests) pass; docs lint and the site link audit are clean.

Fixes #695
