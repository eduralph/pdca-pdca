## Summary
**User impact:** when you re-run a stack-mode batch and one of the fixes finished
in an earlier run can no longer be merged (it now conflicts with the base, or its
branch is gone), the run says that fix is "not carried". But if another finished
fix was built on it, or simply shares some of its commits, that other fix is still
merged, so the commits of the fix you were told was left out end up on the
integration line anyway. Later fixes in the run are then built and tested on top
of work that should not be there, and nothing tells you.

This PR makes the run keep every finished fix that holds any of the skipped fix's
commits off the line too, names the skipped fix as the reason, and holds the fixes
that depend on it. The line is still pushed exactly once.

Reported in [#672](https://github.com/eduralph/pdca-harness/issues/672).

## What to look at
- The change is inside the fold the carry runs before the first wave: after its
  merges, it checks which of the merged fixes contain commits of a skipped one,
  takes them out, and rebuilds the line from the same start before pushing.
  Ordinary in-run folds are not touched.
- To try it: finish a fix `P` that changes `base.txt`, and a fix `Q` cut from
  `P`'s branch, plus a planned `D` (`Depends on: Q`). Change `base.txt` on main so
  `P` conflicts, and update `Q` from main so `Q` alone merges cleanly. Re-issue
  `P, Q, D`. Before: `P` is not carried, `Q` is carried with `P`'s commit, and `D`
  is built on it. After: `Q` is held ("issue_Q was built on issue_P, which is not
  carried"), `D` waits, and no commit of `P` is on the line.
- All cases run against real git with no host, in
  `template/tests/test_flow_resume_stack_prereqs.py`.

## Root cause
The carry spread "not clean" from one finished fix to the ones built on it only
for fixes judged not clean *before* the fold, and only along `Depends on` edges.
A fix that failed *during* the fold was skipped on its own: the fold went on,
merged any finished fix holding its commits, and pushed, and the carry heard of
the skip only after the push.

## Fix
- `integrate.fold` takes `pr_heads=` (each finished fix's PR head) and `holds=`
  (filled with `held fix → the skipped fix it holds work of`). Only the carry
  passes them.
- When a pass of the fold's merge loop skips something, `_work` lists that fix's
  commits: everything reachable from its branch tip or its PR head and not from
  the base or the commit the line started from (merge commits and shared commits
  count). `_hold_work` then leaves out each merged fix whose head reaches any of
  those, and, repeating until nothing changes, each fix holding commits of one
  left out that way. The cause is the first such fix in fold order.
- If anything was left out, the line is reset to its starting commit and the
  loop runs again with only the kept fixes. Each extra pass drops at least one
  more fix, so it ends. A fix that fails on the restarted line is skipped the same
  way. Nothing left out is retried. The push stays where it was, once, after the
  loop.
- `_built_on_skipped`: a fix whose own merge fails and which holds commits of a
  failed fix earlier in fold order is reported for holding that fix's work,
  not for its own conflict.
- `flow._carry_finished` passes its PR heads through `_fold_lines`, and gives each
  held fix the existing "was built on …, which is not carried" message with the
  skipped fix as cause; its `Depends on` dependents wait as before.
- Docs: the "known residual" sentence in `docs/07-crosscutting.md` is replaced,
  and the known limits below are added there. The `_carry_finished` and `fold`
  docstrings say the same.

Why inside the fold and not in the carry: the carry only learns what was skipped
after the fold has already pushed. Doing it in the carry would mean either two
folds per carry (merge everything twice, and take the integration lock twice, so
the line could move in between) or copying the fold's merge and error handling.

## Verification
Line numbers are on this PR's branch (`main` @ `d6057eb` plus this change).

- **Claim:** no commit of a skipped fix reaches the pushed line through another
  finished fix, whatever the history shape, and the line is pushed once.
  **Checked:** `template/src/pdca_harness/integrate.py:537-596` (the pass loop:
  skip, work, hold, restart from `start_ref`), `:1000-1010` (`_work`),
  `:1019-1050` (`_hold_work`), `:608` (the single push, after the loop).
  **Tests**, each also asserting one `git push`, the held dependent, and that the
  skipped fix's commit is not an ancestor of the line or of a later fix built on it:
  - `test_a_skipped_ids_work_does_not_reach_the_line_through_one_built_on_it`
    (`Depends on` edge, holder updated from main);
  - `test_a_branch_holding_a_skipped_ids_work_is_held_with_no_depends_on_edge`
    (same, no edge);
  - `test_one_merged_before_the_skip_is_taken_off_the_line_before_the_push`
    (holder folded first, then the skip);
  - `test_history_shared_through_an_earlier_line_is_held_too`
    (shared commit comes from an earlier, deleted line).
- **Claim:** a skip that is not a conflict (branch deleted, PR still open) holds
  the same way.
  **Checked:** `integrate.py:588` uses the PR head when the branch is gone.
  **Test:** `test_a_skip_that_is_not_a_conflict_holds_the_ids_holding_its_work`
  (asserts the skipped fix really reached the fold: "is not known to be merged").
- **Claim:** a holder that also fails on its own is reported for the skipped
  fix's work, with the earlier fix in fold order as the cause.
  **Checked:** `integrate.py:597-600`, `:1053-1074` (`failed[:i]` at `:1068`).
  **Tests:** `test_a_holder_whose_own_merge_fails_too_is_held_for_the_skipped_ids_work`,
  `test_a_failing_holder_of_an_earlier_commit_of_a_skipped_id_names_it`.
- **Claim:** the hold carries on through fixes that hold only commits of a held
  fix.
  **Checked:** `integrate.py:1034-1048` (the repeat loop; `:1044` adds a held
  fix's own work).
  **Test:** `test_one_holding_only_a_commit_of_a_held_id_is_held_too`.
- **Claim:** a fix that merged in the first pass but fails on the restarted line
  is skipped, and its holders are held.
  **Test:** `test_one_merged_only_on_a_held_ids_work_fails_on_the_restarted_line`
  (a wrapper around the real merge records it succeeding, then failing).
- **Claim:** the carry reports held fixes with the existing "built on" message and
  holds their dependents.
  **Checked:** `template/src/pdca_harness/flow.py:1116-1130`.
- **Claim:** nothing else changes; in-run folds compute nothing new.
  **Checked:** `integrate.py:580` (without `skipped`, the loop exits after one
  pass, before any work is computed).
  **Tests:** every existing case in `test_flow_resume_stack_prereqs.py`,
  `test_integrate_stack_bases.py` and `test_flow_same_wave_conflict.py` passes
  unchanged.
- **Red / green:** with the production changes reverted and the tests kept, the 9
  new cases fail on their assertions (a dependent built on the skipped fix's
  commit, or the wrong cause named) and the other 18 pass. With the change, 27/27
  pass. Each of the new cases was also shown to fail when only the piece of code
  it targets is broken. Full offline suites: root 24 OK, driver 2468 OK (2
  skipped, environment guards in unrelated files). Docs lint and link audit clean.

## Known limits (documented in `docs/07-crosscutting.md`)
The hold is deliberately conservative: it may hold more than needed, but it does
not let a skipped fix's commits through.
- A fix is held for a commit it shares with the skipped one even if that commit
  is its own (for example, the skipped fix was built on it).
- Following on from that, a held fix's commits include those of a clean fix it
  was cut from, so that earlier fix can be held too, and the message then reads
  the wrong way round ("issue_Y was built on issue_Q" when `Q` was built on `Y`).
  The docs do not yet spell out this case.
- A fix that failed only because of another fix that was then taken off the line
  stays held for this run; it is not retried.
- Two fixes that conflict with each other, one holding the other's commit, may
  both be held.
- On a line continued from an earlier run, the skipped fix's commits that the
  earlier run already pushed stay on it. This change adds none.
- In the rare case the line is rebuilt, a fix whose branch is gone may print its
  "gone" message and look up its PR twice.

Fixes #672
