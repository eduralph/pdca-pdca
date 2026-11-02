# Advisory code review: issue 626

I found no correctness bugs in this patch, and nothing needs a human decision. There are two small cleanups below, and neither blocks.

## Findings

- `template/tests/test_stack_squash_merge.py:417`: the name `test_those_records_keep_their_message_with_no_merge_commit_read` is misleading. In both cases the merge commit is read: one read returns no commit and the other fails. The test also never asserts that the read happened, so a mutation that skips `_squash_merged` for these records would still pass here. Rename it (for example `..._when_the_merge_commit_cannot_be_read`) and assert `"A"` and `"B"` are in `merge_commit_reads`.
- `template/src/pdca_harness/integrate.py:1454` and `template/src/pdca_harness/flow.py:1328`: the way-out text is written out by hand in three places: the fold's message, `_SQUASH_STEP`, and the `built_on_squashed` hint (`flow.py:1345`). The wording has already drifted: the fold says "re-drive", the carry says "rebuild". `integrate.py` already holds the shared `DROP_PREREQ`, so the common part could live beside it. Optional, because the three messages address different readers.

## Checked and found correct

- `_hold_all` (`flow.py:1365`) reads `why`, which is set before the `try`, so a `carry_view` failure cannot raise `NameError`. `causes` is also set before `foreign_commit` can raise, so a kept `built_on_squashed` line still names its cause.
- `_cascade_not_clean` (`flow.py:1458-1460`): a chain resolves to the merged id in any order. The loop only uses an id already in `why`, and a chained id gets its `causes` entry in the same step.
- `_finished_head` (`flow.py:1301-1303`): a head missing from the clone counts as off both refs without an error, because `_carries` returns False. An empty head skips the extra `gh` read and keeps the `open` hint.
- `_gone_branch` (`integrate.py:1445-1447`): checking the base earlier does not change the result for other-base records. A head on the base still makes no extra read and still raises the old message.
- `_others_build_on` (`publish.py:835`): it skips the bundle's own brief, catches `UnicodeDecodeError` through `ValueError`, and keeps scanning past an unreadable brief. The `Onto branch` return at `publish.py:225-228` happens before line 373, so no publish warns twice, and both warnings come after the dry-run return.
- "Re-issue without P" works from the real entry point: `flow_ids` passes `batch=list(ids)` (`flow.py:3545`) with no prerequisite added back, so the tests' direct `_drive_and_act` calls match it.

## Not checked

I read the code and the gate logs and did not run anything. The C4 and T3 logs show the new tests red before the fix and green after it, and the full suite passing. What `gh` reports for a real squash or rebase merge is still stubbed. The brief leaves that to #625.

<!-- pdca:leaf-complete -->
