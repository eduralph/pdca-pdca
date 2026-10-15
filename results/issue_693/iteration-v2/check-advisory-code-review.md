# Advisory code review — issue 693 (flow-run-with-holds-exits-3)

Lens: correctness bugs the patch introduces, plus reuse, simplification and efficiency.

I found no correctness bug. The two items below are small, and neither needs a human.

## What I checked

- **Every path still fills the hold signal.** In `_drive_and_act`, every early stop in the wave loop is a `break` (`template/src/pdca_harness/flow.py:2517`, `:2552`, `:2567`). A `break` still reaches the new fill at `flow.py:2583-2585`. The only early `return` is `return {}` at `flow.py:2371`, and that happens before any fold, so nothing has been held yet. A raised `PreflightError` (`flow.py:2442`) leaves `holds` empty, but `cli._flow` returns 1 on that path anyway.
- **The keys match the results map.** `holds` is keyed with the same `n.replace("issue_", "")` step that builds `results` (`flow.py:2570` and `:2584-2585`). Every held id is also a key of the returned map.
- **The two hold kinds never overlap.** The fold only looks at bundles that are not already unpushed (`flow.py:2543`), so the two `update` calls can't overwrite each other.
- **The precedence matches the brief.** `cli._results_rc` (`template/src/pdca_harness/cli.py:716-719`) returns 1 first. It returns 3 only when everything else succeeded and `holds` is not empty. The single-id shape still counts AWAITING_SIGNOFF as success, and that case is now tested (`test_a_single_id_run_stopped_for_sign_off_still_exits_3_for_its_hold`).
- **The return types are unchanged.** `_drive_and_act`, `flow_ids` and `flow_batch` still return `{id: state}`. `holds` is an optional keyword argument, so existing call sites are untouched.
- **The tests were red before the fix.** The C4 gate log (`gate-logs/C4-verify.log`) shows 5 of the 8 new tests failing without the fix and all passing with it. The 5 are the two hold cases, the CSV case, and both single-id hold cases. Last round's finding was that the single-id test could not fail. Real single-id cases over a split parent now cover it, including the 3-over-0 check (`template/tests/test_flow_hold_exit_code.py` around `:285-306`).
- **The test fixture edit is minimal.** The `*rest` pass-through in `template/tests/test_flow_single_driver.py:806-813` is the smallest change that keeps that existing probe working with the new `_report_batch` argument.

## Findings

- NEEDS-HUMAN [impl] — `template/tests/test_flow_hold_exit_code.py:238` and `:292`: `self.assertNotIn("held", self.err)` is a broad substring check over all of stderr. Any unrelated stderr line that happens to contain "held" (for example a future #646 carry note) would fail the no-hold cases for the wrong reason. The positive tests already match the exact phrases `"held out of the integration fold"` and `"pushed no branch this run"`. Asserting those two exact phrases are absent would be more precise and would match the other tests. This is a robustness nit; the tests pass today.
- `template/src/pdca_harness/flow.py:2584-2585` (minor, no action needed): the `sorted(...)` on `held_unpushed` only fixes the order keys go into a dict that callers only check for emptiness. It is harmless and cheap. Dropping it would be a little simpler, but keeping it makes the order predictable for #695, which plans to build on this signal.

Nothing found on the reuse or efficiency lens. The patch reuses the existing `held_unpushed` / `held_conflict` records and the existing id-key step instead of tracking holds a second time. The added work runs once per run, at the end.

<!-- pdca:leaf-complete -->
