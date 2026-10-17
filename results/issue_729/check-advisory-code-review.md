# Advisory code review — issue #729 (flow-merged-prereq-judged-by-merged-into)

**Verdict: no correctness bugs found, and nothing a human needs to decide.** The three notes below are small cleanups. None of them gates anything.

What I checked:

- **The production change is right.** `_runnable` now reads the line only when the bundle is in `on_line` (`template/src/pdca_harness/flow.py:795-796`). `on_line` is built from the same `_base_plans` answer that `_bundle_bases` later uses to point the bundle (`flow.py:2695-2698`, `:2761`). So the predicate is called, not copied, as the brief asks. I moved the plan computation from inside `_bundle_bases` to the top of the wave loop and checked that nothing it reads changes in between: `accepted`, `finished`, `bundles` and `line_cut` are not touched by `_runnable`, the budget check or the preflight. `_closure_members` (`flow.py:922-967`), `_fold_candidates` (`integrate.py:240`) and `waves.conflict_map` only read state, so running them on the whole wave (not only `runnable`) changes no results.
- **The iteration-1 finding is fixed.** The own-base test no longer calls `_built_on_line()`. It checks the base branch, the tip, P's merge commit and W's tip directly (`template/tests/test_flow_merged_prereq_dependency_base.py:90-102`).
- **The old suite is re-pointed as criterion (4) asks.** The held cases now pass `on_line=True` (`Stacks on: W`, a seam), via `template/tests/test_flow_merged_prereq_on_line.py:56` and `:177-180`. Their held assertions are unchanged.
- **Gates.** C4 is red before the fix (D held with the #655 message) and green after (`gate-logs/C4-verify.log`). T3 ran 2594 tests, all OK.

Minor notes (not NEEDS-HUMAN):

- `template/src/pdca_harness/flow.py:2697-2698`: in the run loop, the `if own_bases else None` branch can never change a result. `own_bases` is the same value as `hold_unmerged` (`flow.py:2680`), and when `hold_unmerged` is false `_runnable` never reaches the merged-prerequisite line check. The `None` default ("every bundle is on the line") only matters for direct callers of `_runnable` in tests (`test_flow_slice.py:1984`, `test_flow_out_of_batch_prereq_hold.py:156`), which pass no `lines`. This is harmless and the docstring explains it, so I'd leave it.
- `template/src/pdca_harness/flow.py:2695`: `_base_plans` now runs for every wave in stack mode, before `_runnable`. It also runs for waves where nothing turns out runnable, and for bundles that end up held. Before, it ran only for runnable bundles. The cost is brief reads plus one `conflict_map` per wave, so it is not worth changing.
- `template/tests/test_flow_merged_prereq_dependency_base.py:125-126`: in the real-base case, `read_stack_base(d) == ""` repeats the `seen == ("", "")` check on line 124. `_ancestor(merge_oid["P"], "main")` checks the test setup, not D. Neither weakens the test, since the real base is `main` and line 124 already shows D had no stack base. You could drop both lines or merge them into one.

<!-- pdca:leaf-complete -->
