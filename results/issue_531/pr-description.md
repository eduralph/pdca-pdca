## Summary
**User impact:** with `wave_mode = "merge"`, two PRs in the same wave could each pass
their checks and still leave `main` broken once both were merged, because neither was
ever tested with the other. The next wave then built on that broken `main`. On
repositories that require branches to be up to date before merging, the opposite
happened: the second merge was refused and the whole run stopped after merging one PR.

This PR makes merge mode bring each PR up to date with its base, wait for its checks to
pass again on the updated code, and merge exactly that tested version.

Reported in [#531](https://github.com/eduralph/pdca-harness/issues/531).

## What to look at
The main change is in how merge mode handles one PR: before merging, it checks whether
the PR is behind its base branch. If it is, it updates the PR branch on GitHub (a merge
commit, never a rebase), waits for the updated branch's checks, and merges only that
commit. Anything that goes wrong along the way stops the run and puts the PR back to
draft, the same way merge mode already handles red checks.

To try it: run a merge-mode flow with two independent bundles in one wave. Before this
change the log shows the second PR merged right after the first, with no update. After
it, the second PR is updated, its checks are waited on, and the merge is pinned to the
updated head. The new tests in `template/tests/test_merge.py`
(`MergeAgainstCurrentBase`) run this offline against a fake GitHub that models both
host settings.

`merge_requires = "required"` behaves exactly as before. Its config comment now says
plainly that it keeps the old stale-base behaviour and recommends `"all"` for merge mode.

## Root cause
`_merge_one` read the PR's check results and ran `gh pr merge`
(`template/src/pdca_harness/merge.py:228`, `:259-284` on `main`), but those results
belong to a head commit tested against the base from before the wave's earlier merges.
Nothing in `merge.py` or `flow.py` checked whether the PR was behind or updated it, so
the outcome was left to the host's "require branches to be up to date" setting, which
the harness neither read nor documented.

## Fix
- `_base_read` (`merge.py:276-300`): reads the PR head and base branch name from GitHub
  (`gh pr view --json headRefOid,baseRefName`), fetches the base remote (and `origin` if
  different), records the base tip, and decides with
  `git merge-base --is-ancestor <base-tip> <head>`. Exit 0 = up to date, 1 = behind,
  anything else or a failed fetch = refuse with a message starting `git failed:`.
- If behind: `gh pr update-branch` (no `--rebase`, whatever `merge_method` is), then
  `_wait_for_update` (`merge.py:303-337`) polls until the PR head contains the recorded
  base tip, because GitHub may apply the update with a delay.
- The existing `_wait_for_green` then runs on the new head. It gains a `spent=` argument
  (`merge.py:172-173`, `:204`) so the update poll and the check wait share one
  `merge_wait_secs` budget without skipping the existing "confirm green twice" step.
- The merge runs with `--match-head-commit <sha>` pinned to the head that was seen green,
  so a push after the green read is refused by GitHub instead of merged.
- Refusals go through a shared `_refuse` helper (`merge.py:355-362`) that undoes the ready
  mark.
- Docs: merge-mode comments in `template/pdca.toml.jinja` (including that
  `regate_between_waves` has no effect in merge mode), the merge sequence in
  `template/docs/fork-discipline.md.jinja:57-73`, and the merge bullet in
  `docs/07-crosscutting.md:686-696`. The fork-discipline text also says that after an
  update, the commit that merges is the reviewed branch plus the newer base, and that
  this combination is verified by the PR's own CI rather than by the original review.

**Known limits.** On a host without "require up to date", the base can still move in the
short window between the driver's last read and GitHub running the merge; the config
comment recommends turning that setting on for merge mode. The fetch covers the base
remote and `origin` only, so a PR branch pushed to some third remote cannot be merged once
it falls behind; it stops safely, but with a "git failed" message that does not name the
real cause.

## Verification
- **Claim:** under `merge_requires = "all"`, merge mode never merges a PR that was behind
  its base at the last read before the merge, and never merges a head other than the one
  whose checks it saw green.
  - **Checked:** `template/src/pdca_harness/merge.py:413-487` — the sequence ready →
    behind read → update if behind → wait for update → wait for green → re-read head and
    base → pinned merge.
  - **Test:** `test_second_member_is_updated_and_reverified_before_it_merges` — on `main`
    it fails with the second PR merged straight after the first with no update; passes
    with the fix.
- **Claim:** a head that changes after the green read is not merged.
  - **Test:** `test_head_changed_after_the_green_read_is_not_merged`,
    `test_pinned_merge_refused_when_the_head_moves_at_merge_time`.
- **Claim:** a multi-PR wave now completes on a host that requires branches to be up to
  date.
  - **Test:** `test_strict_host_completes_a_multi_member_wave` — on `main` the second merge
    is refused ("Head branch is out of date") and the run exits 1.
- **Claim:** a late update still merges; an update that never lands, a red updated head, a
  failed update, a failed fetch, or a failed `git merge-base` each stop the run with the
  ready mark undone.
  - **Test:** `test_update_that_lands_late_still_merges_pinned_to_the_updated_head`,
    `test_update_that_never_lands_refuses_readiness_undone`,
    `test_updated_head_that_is_not_green_is_not_merged`,
    `test_update_that_fails_stops_the_wave_readiness_undone`,
    `test_failed_fetch_refuses_saying_git_failed`,
    `test_merge_base_failure_refuses_saying_git_failed`.
- **Claim:** the update poll and the check wait together never exceed `merge_wait_secs`.
  - **Test:** `test_update_poll_and_rollup_wait_share_one_budget` (55-case sweep).
- **Claim:** `merge_requires = "required"` is unchanged.
  - **Test:** `test_merge_requires_required_call_log_is_unchanged` — exact call log, green
    both before and after the fix by design.
- **Overall:** `template/tests/test_merge.py`, 49 tests: with the production change
  reverted, 76 failures; with it applied, all pass. Full template suite (2314 tests),
  root suite (24 tests) and docs build/link check pass. Behaviour on a live GitHub
  repository with each host setting was not exercised; the fake host in the tests models
  both.

Fixes #531
