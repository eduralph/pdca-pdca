## Summary
**User impact:** In stack mode, a run can quietly drop an earlier fix's files from the
integration line and push that line for the next wave to build on. It happens when a
maintainer reverts a merged PR on `main` and a later fix's branch is then cut from `main`,
or updated from it with "Update branch". That branch carries the revert, and folding it
removes the earlier fix's work with no warning. The run already stopped when `main`
itself was merged in with such a revert; it did not stop when the revert came in through
another fix's branch.

This PR makes the run stop in that case too, before it pushes, and say which file would
be lost, whose work it is, and which branch brings the change.

Reported in [#673](https://github.com/eduralph/pdca-harness/issues/673).

## What to look at
- The core of the change is one new check right after each fix's branch merges cleanly
  onto the line. It asks the same question the run already asks when it merges `main` in:
  "does this merge put back a file the line changed, so that work is gone?" If yes, and the
  branch's own commits did not make that change, the merge is undone and the run stops.
- A branch's own deliberate change is still merged. For example, a later fix that deletes
  or edits the earlier fix's file on purpose goes through as before.
- During the pre-wave carry (the step that re-folds already accepted work before a new
  wave), only the offending fix is left out; the others are still folded.
- The existing message for the `main` merge is unchanged, word for word.
- To try it: fold fix A (adds `a.txt`), merge A's PR into `main` and revert it there,
  publish fix B cut from `main`, then fold `[A, B]`. On `main` today the fold pushes a line
  without `a.txt`. With this PR it stops and names `a.txt`, `issue_A` and `issue_B`. The new
  test file `template/tests/test_integrate_revert_via_branch.py` builds this history and
  the related ones with real git.
- Known limit, documented rather than fixed: the check compares each file with where the
  line leaves `main`, so it misses a partial revert inside a file the line also changed in
  other ways, and a revert of work `main` already has.

## Root cause
The removed-work check from #623 lived only in `_take_in_base`, which runs when a gone
branch's merged PR brings the base in. A bundle's own branch was merged by
`_merge_published` (`template/src/pdca_harness/integrate.py:624` on `d6057eb`) with no
check at all, so a revert the branch inherited from the base reached the line unseen.

## Fix
All in `template/src/pdca_harness/integrate.py` (line numbers on `main` with this PR):
- `_merge_published` (`:617-654`) records the line tip before the merge and, on a clean
  merge, calls the new `_keep_merge` (`:643-644`).
- `_keep_merge` (`:657-686`) runs `_undone_paths` for the branch's tip; on a hit it resets
  the line with `_reset_line` and raises a plain `IntegrationError`, so the carry's
  `skipped` mode leaves out just that bundle.
- `_undone_paths` (`:917-980`) takes an optional `head`. With it, removals the branch made
  itself are dropped via the new `_own_removals` (`:889-914`). That judges by the commit
  that gave the branch tip its content at the path (`git rev-list -n 1 <head> -- <path>`),
  so an "Update branch" merge that took the path from the base is followed through to the
  base's revert and never counted as the branch's own change. A branch that holds another
  bundle's tip no longer counts that bundle's commits as its own, so the right bundle is
  named.
- `_removed` (`:797-807`) is the base-merge wording moved out of `_take_in_base`
  unchanged. `_branch_removed` (`:810-831`) words the new refusal. When a commit is shared
  by two branches it says "work from issue_A or issue_B — git cannot tell which branch
  made it", and when the work is the incoming bundle's own earlier work it says so
  ("issue_A's earlier work, which its branch no longer has"). It never describes a bundle
  as removing its own work.
- `_reset_line` (`:983-990`) now names the merge it undoes, so a failed reset no longer
  blames the base merge when the refused merge was a bundle's branch.
- Docs: `docs/07-crosscutting.md:684-697` and the module docstring (`integrate.py:51-57`)
  describe the new check and the documented limit.

## Verification
- **Claim:** a fix's branch that brings a revert of line work stops the fold, names
  `a.txt`, `issue_A` and `issue_B`, and pushes nothing.
  **Checked:** `integrate.py:643-644`, `:657-686`.
  **Test:** `test_a_branch_cut_from_a_base_that_reverted_line_work_stops_the_fold`
  (`test_integrate_revert_via_branch.py:165`).
- **Claim:** the same holds for a branch updated from the reverted base ("Update branch"),
  including one cut from the line or from another fix's branch first.
  **Checked:** `_own_removals`, `integrate.py:889-914`.
  **Test:** `:187`, `:198`, `:212`, plus a branch that edited the file and put it back
  (`:223`) and a revert merged through a revert PR (`:237`).
- **Claim:** under the carry's `skipped` mode only the offending fix is left out; a later
  fix is still merged, the line keeps `a.txt`, and the revert never reaches it.
  **Test:** `test_the_carry_skips_only_the_branch_that_brings_the_revert` (`:176`).
- **Claim:** a fix's own deliberate delete or edit of the file is merged, also after
  "Update branch".
  **Test:** `:332`, `:341`, `:348`.
- **Claim:** the message names the right bundle and never says a bundle removes its own
  work.
  **Checked:** `_branch_removed`, `integrate.py:810-831`.
  **Test:** `:258`, `:275`, `:296`, `:311`.
- **Claim:** a line that will not reset after a refusal stops even the carry.
  **Test:** `:364`.
- **Claim:** nothing else changes; the base-merge message stays word for word.
  **Checked:** `_take_in_base` uses `_removed` (`integrate.py:784`) with the old formula.
  **Test:** the existing `template/tests/test_integrate_stack_bases.py`,
  `test_flow_same_wave_conflict.py` and `test_flow_resume_stack_prereqs.py` stay green.
- **Red → green:** with the production changes reverted and the new tests kept, 12 of the
  15 new tests fail on their assertions (the three "is merged" cases pass both ways by
  design). With the change, all 15 pass, and the full offline suite passes (2491 tests,
  2 skipped). On `main` (`d6057eb`) with this patch applied, the new file plus
  `test_integrate_stack_bases` run 77 tests, all OK.

Fixes #673
