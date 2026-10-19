# Advisory code review — issue_738 (iteration after v5)

Lens: bugs the patch adds, plus reuse / simplification. Anchors are on the patched tree at `$PDCA_TARGET`.

No blocking defects found. The three carry-forward fixes are in place and each has a real-git test:
- (1) The "next fold" warning is now `fold_next=bool(runnable) and k < len(wave_list) - 1`, computed after the held bundles are dropped. It matches the fold guard at `template/src/pdca_harness/flow.py:2954`, and a fully held wave `continue`s before the fold (`flow.py:2883-2890`). Test: `test_a_rewrite_hold_that_leaves_its_wave_nothing_to_fold_warns_of_no_fold`.
- (2) The stop handler announces the already-held bundles with `stopping=True` before the `STOPPING` line (`flow.py:2877-2882`). Test: `test_a_broken_worktree_after_a_hold_in_its_wave_names_that_hold_first`.
- (3) `_bundle_bases` re-raises `(IntegrationTreeError, _LineBroken)` and the wave loop catches both (`flow.py:2877`). The test triggers a real `_LineBroken` through the trial-merge path, not a raise stub.

No existing expected exit code changed (`test_integrate_carried_rewrite_late.py` still asserts `rc == 1`). In `_results_rc` (`template/src/pdca_harness/cli.py:65-66` of the diff), PLANNED dependents and partners still give exit 1.

Minor notes. None of them needs a human; each is optional:

- `template/src/pdca_harness/flow.py:2887-2888`: `fold_next` reads `len(wave_list)` before `_drive_wave` / `_adopt_split_children` (`flow.py:2897-2906`) can add waves after wave k. If a split in the last wave adds a wave, a fold does run after it, but the rewrite hold line has already said nothing about it. This is a rare edge case and can't be known when the line prints, so the line can't easily be fixed. The run still stops at that fold with #633's own message, so nothing is hidden. Mentioned only for completeness.
- `template/src/pdca_harness/cli.py` (`_results_rc`, diff lines 65-66): the rule-1 exemption lets a base-held key pass with any state, not only PLANNED. In practice a base-held bundle is never driven this run, so it keeps whatever runnable state it came in with. That fits "held, not failed", and I see no path where it hides a real failure. Tightening it to `s == state.PLANNED` would match the brief's wording more literally, but it isn't required.
- `template/src/pdca_harness/flow.py:861-868` (the `unbuilt_partners` print in `_runnable`) is a third near-copy of the `partners` / `clashed` hold-line blocks just above it, including the same `into` string. A small shared helper could build the "wait until …, then re-run" tail. This is cleanup only; the patch follows the pattern already in that function.
- `template/src/pdca_harness/flow.py:1079-1098` (`_BASE_HOLD_STEPS` / `_base_hold_why`): the fix text depends on prefixes of `integrate` messages (`"could not fetch "`, `"could not start "`, …). Rewording any of those messages in `integrate.py` would quietly fall back to the raw message with no test failure. The fetch and push cases are pinned by tests. The checkout-missing, worktree and start cases are pinned too (`test_a_checkout_missing…`, `test_a_worktree_that_cannot_be_made…`, `test_a_base_branch_git_cannot_start…`), so the risk is covered for now. Matching on prefixes was the brief's choice, since it leaves `_fetch`'s text alone.

The diff is otherwise clean on both lenses.

<!-- pdca:leaf-complete -->
