# Advisory code review — issue 693 (flow-run-with-holds-exits-3)

I found no correctness bugs and no reuse problems that need action. Nothing here needs a human decision.

## Correctness

- `template/src/pdca_harness/flow.py:2583-2585` — The hold collector uses the same keys as the results map. Both strip the prefix with `d.name.replace("issue_", "")` (`flow.py:2570`), so every held id is also a key of `results`. A bundle can't be in both sets: the fold skips `held_unpushed` bundles before it can mark one as a conflict (`flow.py:2543`). If one ever were in both, the second `update` would just overwrite the reason, and the exit code would not change.
- `template/src/pdca_harness/flow.py:2547-2552`, `:2563-2567` — Early `break`s (an integration error or a failed re-gate) still reach the end, where the collector is filled. Those breaks only happen when `k < len(wave_list) - 1`, so a later wave's bundles stay PLANNED and the run exits 1. That matches the brief's rule that a failure wins over 3. `PreflightError` skips the fill, but `cli.py:668-670` returns 1 in that case anyway.
- `template/src/pdca_harness/cli.py:694-719` — `_results_rc` checks for 1 first, then 3, then 0, which is the order the brief asks for. An empty results map can't come with a non-empty `holds`, so the early `return 0` in `_report_batch` (`cli.py:780-782`) doesn't hide a hold.
- `template/src/pdca_harness/cli.py:640-682` — The collector reaches all three paths: `flow_batch`, then `flow_ids` reported by `_report_single`, then `flow_ids` reported by `_report_batch`. The return types of `_drive_and_act`, `flow_ids` and `flow_batch` are unchanged, as the brief requires. Existing callers that don't pass `holds` get `None` and behave as before.
- `template/tests/test_flow_hold_exit_code.py` — The C4 gate log (`gate-logs/C4-verify.log:24-104`) shows all five hold cases fail with the fix reverted (`0 != 3`) and pass with it. The no-hold and failure-wins cases pass both ways, which is expected. The test imports only modules (`:316`). Iteration 2's point is addressed: `_assert_held_nothing` (`:489-492`) now checks for the two exact hold phrases, not the bare word "held". Iteration 1's point is addressed too: the single-id shape now gets a real hold through a split-parent recovery run (`:552-590`).
- `template/tests/test_flow_single_driver.py:803-812` — Changing the spy to `report(results, *rest)` passes `holds` through, so that test still runs `_report_batch` the same way.

## Reuse / simplification

- `template/src/pdca_harness/flow.py:2584` — Optional nit: the `sorted(...)` around `held_unpushed` has no effect, because it fills a dict whose order nothing reads. Leaving it is harmless.

The diff looks clean on both counts: no new correctness bugs, and no logic that an existing helper already covers.

<!-- pdca:leaf-complete -->
