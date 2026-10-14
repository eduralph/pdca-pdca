# Advisory code review — issue 658 (merge mode never merges an `Onto branch` PR)

**Verdict: no correctness bugs found in this diff.** The findings below are small test cleanups. None needs a human.

## Correctness

- `template/src/pdca_harness/merge.py:486-494`: the refusal is placed right. It comes after the `pr_url` check (`:475-478`), so `rec` is never `None` when `rec.get("mode")` runs. It also comes before the dry-run return, the `is_merged` skip and every `gh` call. It returns `1` without calling `_undo_ready`, which is correct because nothing has been readied yet. `merge_wave` (`merge.py:124-127`) stops at the first non-zero result, so later bundles are not touched. The mode test (`== "stacked"`) matches the one in `merged.merged_into`, so `"stacked-pr"` and records with no mode still merge (`test_merge_onto_branch.py` case (5)). The message is written inline instead of going through `_refuse` (`merge.py:453`). That is the right call: `_refuse` would tell the operator to "resolve at the PR", which loops under criterion (3), and it also calls `_undo_ready`, which is not needed here.
- Gate evidence matches. C4 (the gate that checks the new tests fail without the fix and pass with it) shows them red without the fix: the stacked record goes to `gh pr ready`, `view`, `ready --undo`. They are green with the fix. T3 (the full test suite) is OK: 2427 tests, 2 skipped.

## Reuse / simplification (optional)

- `template/tests/test_merge_onto_branch.py:94-100`: in `_assert_no_pr_action`, the check on line 99 (no `gh pr …` call at all) already covers the specific `ready` / `ready --undo` / `update-branch` / `merge` checks above it. The specific checks could go, or stay as documentation. Cosmetic.
- `template/tests/test_merge_onto_branch.py:141-157`: `test_wave_stops_at_the_stacked_member` copies the stub setup from `_wave` (same `run` recorder, same three patches). If `_wave` took a list of bundles, this case could reuse it. Cosmetic.
- `template/tests/test_merge_onto_branch.py:120`: `self.assertEqual(b.name, "issue_658")` tests the fixture's naming, not the fix. It is harmless but could be removed.
- `template/tests/test_merge_third_remote.py:183`: the `for verdict in (failing, green)` loop has no effect. The refusal happens before `_wait_for_green` is reached, so both subtests run the same path. One case is enough. Keeping both is harmless.
- Coverage note, not a defect: the old `test_stacked_head_behind_is_updated_on_third_remote_and_reaches_wait` was removed and not turned into a direct `_base_read` case. That means `_base_read` returning `behind=True` for a third-remote head is no longer tested. This matches the brief's Scope (a), since that case was about `update-branch` and reaching the rollup wait, which is code inside `_merge_one`. The kept direct-read cases cover the fetch and the missing-head logic.

No NEEDS-HUMAN items.

<!-- pdca:leaf-complete -->
