## Summary
**User impact:** with `wave_mode = "merge"`, a pull request that points at the wrong
branch is merged into that wrong branch, with no warning, and the run still reports
success. This happens for PRs opened by an earlier run (for example before switching a
batch from stack mode to merge mode) or PRs whose base someone changed on GitHub later.
The fix lands somewhere other than the branch it was meant for, and nothing tells you.

This PR makes merge mode check each PR's base before it merges. If the base is wrong, the
driver moves the PR to the right base. If it can't, the run stops and says why.

Reported in [#500](https://github.com/eduralph/pdca-harness/issues/500).

**Decision this asks the maintainer to confirm:** this reverses #411's stance that the
harness refuses at publish time and never retargets a PR itself. The PR now lets merge
mode retarget a PR it is about to merge, unattended, to the base its brief names. The
fallback, if you don't want that, is refuse-only: drop the retarget step and keep the
stop.

## What to look at
- The new check runs before the driver marks a PR ready. There are four outcomes: the
  base is already right (nothing changes), the base is wrong and gets fixed, the base is
  wrong and can't be fixed (stop), or the target branch is one this same batch produced
  (stop, no change on GitHub).
- If someone edits the PR's base on GitHub while the driver waits for checks, the run now
  stops instead of merging into the new base.
- To try it: `cd template && PYTHONPATH=src python -m unittest tests.test_merge_retarget`.
  The tests use a fake GitHub that carries a PR on the wrong base, can fail or ignore the
  base edit, and can move the base partway through the run.

## Root cause
`merge._merge_one` never compared the PR's host-side base with the bundle's target base.
`_pr_head` reads `baseRefName` only so `_base_read` can ask whether the head is behind
*that* base. So a wrong-based PR was readied and `gh pr merge` ran. The #411 guard runs
only at publish, so a PR that never passes through publish again is not covered.

## Fix
- **`merge._target_base`** (new). It resolves the target with `publish._resolve_target`
  (the parser publish uses, as `flow._runnable` does). It refuses a target that is a
  sibling bundle's published branch (`publish._batch_branch_producer`, #411 route 2)
  before any `gh` call. Then it reads the base with `_pr_head`. On a mismatch it runs
  `gh pr edit <pr> --base <target>`, reads the base again, and accepts only a read that
  reports the target. A missing brief or target refuses.
- **`_merge_one`** calls it after the `expected_checks_error` refusal and before
  `gh pr ready`, under both `merge_requires` values. A refusal prints a stderr STOP and
  returns 1, like the `expected_checks` refusal. It does not go through `_refuse`, which
  always sends `gh pr ready --undo`. So a refused PR keeps its draft/ready state.
- **`_base_read`** now takes a required keyword `target`. A read that finds any other
  base refuses before it fetches or updates anything. Both calls in `_merge_one` pass it,
  so a base edited during the rollup wait refuses, with the ready-mark undone.
- **`publish.MERGE_BASE_FIX`**: the #411 hint text, moved into one constant used by both
  publish and merge time. Publish's output is unchanged byte for byte. When the edit
  fails or doesn't take, the hint points at the PR on the host instead, since the brief
  is right in that case.
- **Docs:** `docs/07-crosscutting.md` (the merge-mode bullet and the #411 paragraph that
  said "the harness never retargets a PR for you"), the #411 comment in `publish.py`, the
  `merge.py` module docstring, and `template/docs/fork-discipline.md.jinja`. That last file
  lists the per-PR merge sequence, and said `merge_requires = "required"` skips every check,
  which is no longer true.
- **Existing tests** in `test_merge.py`, `test_merge_onto_branch.py` and
  `test_merge_third_remote.py` now give their bundles a brief and expect the one extra
  `gh pr view` before the ready-mark. No assertion was loosened.

**Known limits, accepted at review:**
- A base edited after the last read and before `gh pr merge` still merges into that base.
  `gh pr merge` has no way to pin the base, so no client can close this gap. Under
  `"required"` that window is the single `gh pr ready` call. The `merge.py` docstring says so.
- After a retarget, a head that already contains the new base's tip is not updated, so the
  existing check results for that commit are used. `pull_request`-triggered checks that ran
  against the old base are not re-run, because a base edit alone does not re-trigger CI.
- A merge-mode PR now costs one more `gh pr view`.

## Verification
Line numbers marked `main` are on `main` at `a6af7f3`. Unmarked line numbers are in the
patched files.

- **Claim:** before this change, a wrong-based PR was merged into its wrong base.
  - **Checked:** `template/src/pdca_harness/merge.py:278-294` (main). `_pr_head` reads
    `baseRefName`, and the only callers compare the head against that same base
    (`merge.py:552`, `:607` on main). Nothing between the `expected_checks_error` refusal
    (`merge.py:507-511`, main) and `gh pr ready` (`merge.py:519`, main) looks at the base.
- **Claim:** a wrong base is retargeted, read again, and only then merged, under both
  `merge_requires` values.
  - **Checked:** `merge.py:485-532` (`_target_base`), called at `merge.py:584-594`, before
    the ready-mark.
  - **Test:** `test_wrong_base_is_retargeted_then_merged_into_the_target`. The fake host
    records the base each `gh pr merge` lands on, and the test asserts it is the target.
- **Claim:** an edit that fails or doesn't take stops the run, names both branches, and
  makes no `gh pr ready` call (so no `--undo` either).
  - **Test:** `test_retarget_that_fails_or_does_not_take_refuses_with_the_pr_untouched`.
- **Claim:** a PR already on its target makes no `gh pr edit` call.
  - **Test:** `test_pr_on_its_target_base_makes_no_edit`.
- **Claim:** a target that a sibling bundle produced is refused before any `gh` call, with
  the same hint publish gives.
  - **Checked:** `merge.py:506-509`, which calls `publish._batch_branch_producer` as
    `publish._merge_base_refusal` does (`publish.py:798-802`, main).
  - **Test:** `test_batch_produced_target_is_refused_before_any_gh_call`. This test also
    compares the hint with `_merge_base_refusal`'s own output.
- **Claim:** a malformed `expected_checks` still refuses first, with no `gh pr edit`.
  - **Test:** `test_malformed_expected_checks_is_refused_before_any_edit`.
- **Claim:** under `"all"`, a base edited on the host after the check is never merged into
  and never updated against.
  - **Checked:** `merge.py:399-402` (`_base_read` refuses on any other base), passed
    `target=` at `merge.py:637` and `:694`.
  - **Test:** `test_base_edited_on_the_host_after_the_check_is_never_merged_into`. It has
    three cases: moved during the rollup wait after a retarget, moved right after the
    ready-mark, and moved during the wait on a PR that started on its target.
- **Claim:** a bundle with no usable target is refused and its PR is left alone.
  - **Test:** `test_bundle_with_no_target_base_is_refused_untouched`.
- **Red → green:** all of the tests above are in `template/tests/test_merge_retarget.py`.
  With the `merge.py` and `publish.py` changes reverted, they fail with 15 assertion
  failures. That includes merges into the wrong branch under both settings. The two cases
  where the old code was already right (base already right, malformed `expected_checks`)
  pass both ways, as they should. With the patch, they pass. A separate reviewer reproduced
  this on its own.
- **Rest of the suite:** driver suite 2637 tests OK (2 skipped, as before). Root
  render/update suite 24 OK. Docs lint and site link audit are clean.

Fixes #500
