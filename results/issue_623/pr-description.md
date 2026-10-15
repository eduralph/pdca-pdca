## Summary
**User impact:** In stack mode, if a maintainer reverts a merged PR on the base branch, the next fold can quietly pull that revert into the integration line. The work of an already-folded bundle disappears from the line, the next wave builds without it (a bundle that depends on it builds without its prerequisite), and the run's output says the work "reaches" the line when it does not.

This PR makes the fold stop instead, before pushing anything, and name the bundle and files whose work would be lost. A base that only edits those files, rather than undoing them, is still merged in as before.

Reported in [#623](https://github.com/eduralph/pdca-harness/issues/623).

## What to look at
The change is in the fold step that merges the base into the integration line when a bundle's PR branch has been deleted after its PR merged. Before, it only checked that the base contains the merged PR. Now it also compares the line before and after that merge, and refuses the merge if any file the line had changed goes back to how it was before the line changed it.

To try it: fold bundle A, push a fixup to A's PR branch, merge that branch into `main` and delete it, then revert that merge on `main` (`git revert -m 1`). Publish B and fold A and B again. Before this PR the fold succeeds and the line loses `a.txt`. With it, the fold stops with a message naming `a.txt (issue_A)`, and nothing is pushed. The new tests in `template/tests/test_integrate_stack_bases.py` build exactly this history with real git.

## Root cause
`_gone_branch` (`template/src/pdca_harness/integrate.py:528` on `main`) checks only that the base has the PR's merged head by commit ancestry, then `_take_in_base` (`integrate.py:548-566`) merges the whole base into the line. Ancestry stays true after the merge is reverted on the base, so the revert comes in with the base, and the stderr line at `integrate.py:564-566` is printed regardless.

## Fix
- `_take_in_base` records the line tip before the base merge and, after a clean merge, calls the new `_undone_paths`. It finds the line's cut point (the first commit on its first-parent chain that the base already has, decided by commit, not by message). A path that differs between the cut point and the old tip, and no longer differs after the merge, counts as removed work. An edit that leaves new content does not.
- If any path is removed, the line is reset to its old tip (`_reset_line`) and an `IntegrationError` names each path with the bundle that brought it. Owners come from the fold's bundles plus the run's `batch`, looked up with `cfg.find_bundle` so archived bundles are found too, and deduplicated by name. A bundle's own commits include topic branches merged into its PR branch, but not what it got by being cut from the line or the base.
- Because of the reset, the pre-wave carry (`skipped`) records the refused bundle and merges and pushes the rest onto a line without the revert. If the reset fails, a new `_LineBroken` error is raised even under `skipped`, so the carry never pushes a line that still has the revert.
- The "reaches … through" message is printed only when nothing was undone.
- `docs/07-crosscutting.md`: one sentence in the stack-mode paragraph saying the run also stops in this case.

The reset is in `_take_in_base`, not in the shared `_merge` helper, to keep this change out of `_merge`'s abort handling.

## Verification
- **Claim:** a fold whose base merge would revert a folded bundle's work stops, names that bundle, and pushes nothing.
  **Checked:** `integrate.py:528` and `:548-566` on `main` (`b5f5c29`), the ancestry-only check and the unconditional merge plus message.
  **Test:** `test_a_base_that_reverts_the_gone_bundle_stops_the_fold` asserts `a.txt (issue_A) would go back`, the line still at its earlier tip, and no "reaches" on stderr.
- **Claim:** the same holds when the base reverts a *different* bundle already on the line, including one found only through the run's batch, one archived to `results/completed/`, and work a topic branch merged into that bundle's PR branch.
  **Test:** `test_a_base_that_reverts_another_bundle_on_the_line_stops_the_fold`, `test_an_archived_batch_bundle_is_still_named`, `test_a_reverted_topic_merged_into_a_bundles_branch_names_that_bundle`, `test_a_bundle_reached_twice_is_named_once`.
- **Claim:** under the pre-wave carry, the refused bundle is skipped and the remaining bundles are pushed on a line without the revert. If the line cannot be reset, nothing is pushed.
  **Test:** `test_the_carry_skips_a_bundle_whose_base_would_undo_it_and_folds_the_rest` and `test_a_line_that_will_not_go_back_stops_even_the_carry`.
- **Claim:** no false stop. A base that edits a bundle's file is still taken in, with the "reaches … through" message, and existing behavior is unchanged.
  **Test:** `test_a_base_that_edits_a_bundles_file_is_still_taken_in`, and the existing `test_a_merged_branch_the_line_never_carried_comes_in_through_the_base` plus the rest of the file pass unchanged.
- **Red → green:** with the production hunks reverted and the tests kept, 7 of the new tests fail on their assertions (none on import). With the patch, `template/tests/test_integrate_stack_bases.py` runs 54 tests, all passing. The full driver suite passes (2377 tests, 2 skipped) and the docs checks are clean.

**Known limits** (the fold still stops in each case; only the message or coverage differs):
- Detection works per file and starts at the cut point. A partial revert of a file another change also touched, or a revert of work below the cut point, is not seen.
- A PR merged by fast-forward instead of a merge commit is not named. The message falls back to the path and the commit that last changed it.
- A base that reverts its own change, which an earlier base merge brought onto the line, also stops. This is rare, and it fails safe.
- A later bundle whose branch was cut from a base that already has the revert still brings the revert in through its own branch. That case is outside this PR.

Fixes #623
