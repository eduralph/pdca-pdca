# Advisory code review — issue 632 (publish-raise-after-push-counts-as-pushed)

Verdict: no correctness bugs found on either lens. Nothing here needs a human decision. The notes below are small, optional cleanups.

## Correctness

- `template/src/pdca_harness/publish.py:410-414` — The `try/except Exception` wraps only the `gh pr create` call, which is the one step between the push (`publish.py:318`, run in the loop at `:391-397`) and the record write (`publish.py:440`). A failure before the push still returns 1 from `:397` (or raises out to `_isolate`) without writing a record, so case (4) is unchanged. Catching `Exception`, not `BaseException`, lets ^C / `SystemExit` through, which matches `flow._isolate` (`flow.py:62-71`). The fake `CompletedProcess(pr_cmd, 1, "", "<Type>: <msg>")` sends the raise down the existing rc-1 path: `pr_failed=True`, the exception text goes to stderr, the record is written with `pr_url=""`, and the call returns 1 (`publish.py:445-446`). `flow._publish_bundle` then returns True from the record's new mtime (`flow.py:665`). No bug found.
- `template/src/pdca_harness/publish.py:419-422` — The new hint "re-run `pdca publish <id>`" is safe to follow. A re-run does `checkout -B` (`:300`) and `push --force-with-lease` (`:318`), so the branch that is already local and on origin does not make it fail.
- C4 log (`gate-logs/C4-verify.log`): the new test fails without the fix for the right reason. `_isolate` logs "publish failed (RuntimeError: gh exploded)" and `_publish_bundle` returns False after the push stub ran. It passes with the fix. T3 suite is green.

## Test quality / simplification (optional, not blocking)

- `template/tests/test_flow_publish_raise_after_push.py:139` — `assertIn("origin", err)` proves almost nothing, because "origin" can show up in any stderr line. Asserting the new phrase (for example `f"{branch} is pushed to origin"`) would pin criterion (3) to the new message from `publish.py:419`. Small strengthening only. The branch-name and "no draft PR was opened" asserts on the lines around it already cover most of it.
- `template/tests/test_flow_publish_raise_after_push.py:45-79` — `_cfg` / `_bundle` are copied from `tests/test_publish_slice.py:48-81`, with the publisher changed and the texts pre-written. The brief allowed copying them, and the suite has no shared helper module, so this is fine. If the copies drift apart they could be merged later.
- `template/src/pdca_harness/flow.py:662` (not changed by this diff) — When this path runs, the operator now sees publish's "branch … is pushed to origin" line, then flow's "publish did not complete (rc 1) — NOT published". The two lines read a bit inconsistently. This flow message came before this patch, and criterion (3) asks for the "did not complete" wording to stay, so it is not a defect in this diff. It is only a wording note for a later change.

<!-- pdca:leaf-complete -->
