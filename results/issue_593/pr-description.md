## Summary
**User impact:** In stack mode (`wave_mode = "stack"`), a batch with three or more waves
can't be finished in one run and merged afterwards. Pull requests from the middle waves
turn empty, conflicting or fail the sign-off check while the run is still going. Even when
they survive, merging the stack from the bottom up lands only the first wave on `main`;
the later waves end up on a helper branch that never reaches `main`.

This PR makes every wave's pull request target the real base branch, and builds the shared
helper branch by merging the real PR branches into it (only adding to it during a run),
so the stack stays valid and merges cleanly onto `main` from the bottom up.

Reported in [#593](https://github.com/eduralph/pdca-harness/issues/593).

## What to look at
- **The fold** (how the shared helper branch is built between waves): it now merges each
  accepted PR branch instead of re-applying patches, only adds to the branch during a run,
  and pushes without force.
- **Publish of a later-wave bundle:** opens against the real base, cut from the point on
  the helper branch the bundle was built on. If a later run has replaced the helper
  branch, publish refuses instead of guessing.
- **A prerequisite whose PR was merged and its branch deleted:** decided by the merged
  PR's head commit, not by commit messages. If neither the helper branch nor the base has
  that commit (e.g. it was merged into some other branch, or squash-merged after a late
  fixup), the fold stops.
- **One unpublished bundle no longer stops the run:** only the bundles that depend on it
  are skipped.

To try it: three bundles A → B → C chained with `Depends on`, `wave_mode = "stack"`,
`pdca flow A B C`. Before this change, B's PR (opened against `pdca-integration/main`)
goes empty or conflicting after the second fold. After it, all three PRs open against
`main`; merge A, then B, then C with merge commits.

Things this PR does **not** cover (follow-ups): resuming a stack across runs (#616); a
run racing another run on the same base beyond a refusal (#591); squash or rebase merges
of stack PRs (merge commits are required). The docs say this.

## Root cause
`integrate.fold` rebuilt `pdca-integration/<base>` from the base on every call, re-applied
each `patch.diff` as a new commit and force-pushed, so a stacked PR's base held its own
change under a different SHA after the next fold. And for an own-repo target, `publish`
opened wave>0 PRs `--base` that integration branch, which nothing ever merged into the
real base.

## Fix
- `integrate.fold` takes `folded_this_run` (target → tip this run pushed). Listed target:
  continue from that tip, refuse if origin's line is not that SHA, push without
  `--force`. Unlisted: start fresh from the base and force-push (a new run). It then
  `git merge --no-ff --signoff`s each bundle's published branch (resolved from
  `publish.json`; an `Onto branch` record uses its own remote's ref), skipping one that is
  already an ancestor.
- Gone branch: `merged.merged_head` (new; `gh pr view --json state,headRefOid`, fails
  closed to `None`) gives the merged head. Already on the line → skip. In the base → merge
  the base in. Neither, or not merged → `IntegrationError`. The base remote is fetched
  last. `merged.is_merged` is unchanged.
- `publish`: a bundle with a recorded `stack-base` gets `--base <real base>`, cut from the
  new `stack-base-tip` (also the host-CI pin, so `host_ci_base` matches). Before cutting,
  `_line_tip_refusal` checks the tip is still an ancestor of `origin/<stack-base>`;
  otherwise it refuses with no push. The `stack-base` file format and `read_stack_base`
  are unchanged, so `$PDCA_VERIFY_BASE` and drift behave as before.
- `flow`: passes `folded_this_run` and each fold's tip on to the next wave. Tracks which
  bundles pushed a branch this run (`publish.json` written or changed by the call); a
  targeted, accepted, patched bundle that did not is left out of the fold and its
  dependents are skipped, rather than stopping the run.
- Docs: module docstrings, `pdca.toml.jinja`, `docs/05-check.md`,
  `docs/07-crosscutting.md` and the vendored model spec
  (`template/PCDA/quality-cycle/08-glossary.md`, `09-parallel-lanes.md`) now say: every
  PR targets the real base; merge bottom-up with merge commits; a PR that keeps showing an
  already-merged change needs "Update branch".

## Verification
Line numbers for "before" are on `main` at 24c7f83cca82764c279e75d0103f51ca33b97b18;
"after" are on this PR's branch.

- **Claim:** within a run the line only grows and carries the PRs' own commits.
  - **Before:** `template/src/pdca_harness/integrate.py:209-228` (`checkout -B` from the
    base, `git apply` + new commit per bundle, `push --force`).
  - **After:** `integrate.py:219` (`fold(…, folded_this_run=…)`).
  - **Test:** `template/tests/test_integrate_stack_bases.py` —
    `test_a_later_fold_appends_to_the_line_and_carries_the_pr_commits` (against an origin
    with `receive.denyNonFastForwards`), `test_a_continuing_fold_pushes_without_force`,
    `test_a_runs_first_fold_starts_fresh_over_an_earlier_runs_line`,
    `test_a_line_another_run_moved_is_refused`.
- **Claim:** wave>0 PRs target the real base and are cut from the recorded tip.
  - **Before:** `template/src/pdca_harness/publish.py:246`, `:258-259`
    (`pr_base = stack_branch` for own-repo).
  - **After:** `publish.py:282`; `write_stack_base` / `read_stack_base_tip`
    `publish.py:638`, `:681`; guard `_line_tip_refusal` `publish.py:691`.
  - **Test:** `test_a_wave_bundle_publishes_against_the_real_base`,
    `test_a_late_publish_is_cut_from_the_recorded_line_tip`,
    `test_a_late_publish_through_host_ci_pins_the_recorded_line_tip`,
    `test_a_late_publish_refuses_a_tip_the_line_no_longer_holds`, `StackPublishDryRun`.
- **Claim:** a merged-and-deleted prerequisite is judged by its head commit, and work
  merged elsewhere is never silently dropped.
  - **After:** `integrate.py:411-459` (`_gone_branch`), `_prepare_worktree` fetch order
    `integrate.py:521-542`, `merged.py:62` (`merged_head`).
  - **Test:** `test_merged_prerequisites_already_on_the_line_are_skipped_by_commit`,
    `test_a_fixup_merged_with_its_deleted_branch_reaches_the_line`,
    `test_a_merged_branch_the_line_never_carried_comes_in_through_the_base`,
    `test_a_fixup_merged_into_another_branch_stops_the_fold`,
    `test_a_branch_never_carried_and_merged_into_another_branch_stops_the_fold`,
    `test_a_pr_merged_and_deleted_between_the_folds_fetches_is_still_carried`, `MergedHead`.
- **Claim:** once earlier waves merge, a later PR's diff shrinks to its own change (or does
  after "Update branch" when it has several merge bases).
  - **Test:** `test_a_chain_dependents_diff_shrinks_once_its_prerequisite_merges`,
    `test_a_dependent_on_two_siblings_shrinks_after_a_base_update`,
    `test_a_chain_on_a_moved_base_keeps_a_second_merge_base_until_updated`.
- **Claim:** an unpublished bundle holds only its dependents; three-wave runs pass the
  right `folded_this_run`.
  - **Test:** flow cases in `template/tests/test_flow_slice.py` (hold, stale record,
    pushed-but-PR-create-failed, three-wave real and dry-run).
- **Red → green:** with production code reverted to `main`, `test_integrate_stack_bases`
  (17 failures, 30 errors), `test_flow_slice` (9 failures, 1 error) and `test_integrate`
  (1 failure) fail; with the patch all pass. Every module imports on both runs.
- **Suites:** driver suite 2269 tests OK (2 skips existed before), root suite 24 OK, docs
  lint and site render/link audit clean, `git diff --check` clean.
- **Not checked live:** tests use real git with a bare origin but stub `gh`. GitHub's own
  "Files changed" / "Update branch" view and a real `gh pr view --json
  state,headRefOid` response have not been run on a live repo yet; that is a follow-up.

### Known limits
- The merged-head check is by commit ancestry. If someone reverts a merged prerequisite on
  the base, the base still "has" the head, so the fold takes the base in and the revert
  with it.
- The hold only skips direct dependents of an unpublished bundle and anything not yet
  complete. A dependent that was already complete before the run started does not pass the
  hold on to its own dependents.

Fixes #593
