## Summary
**User impact:** None today — this PR changes no behaviour. It guards one that users rely on: when a bundle splits in the middle of `pdca flow`, a problem with the new child bundles must never crash the run or throw away the results of the bundles it already finished. The code does this correctly now, but the tests would not notice if it stopped. One of the three ways to break it (making a child whose folder path can't be resolved crash the run with an uncaught `OSError`) passes the entire offline test suite.

This PR adds two tests that fail if that promise is broken, so a future change can't quietly undo it.

Reported in [#496](https://github.com/eduralph/pdca-harness/issues/496).

## What to look at
Only one file changes: `template/tests/test_flow_adopt_split.py`, which gets two new test methods at the end of the `AdoptSplitChildren` class. Each one runs `pdca flow` through the CLI with stubbed steps, makes a bundle split, and injects a single fault:

1. **Rescheduling after the split fails** while one more bundle is still waiting in a later wave. The run should report the problem, leave the new child bundles untouched, still finish the waiting bundle, and exit 0.
2. **One child's folder path can't be resolved.** That child should be skipped with a message, its sibling should still be picked up and finished, and the run should exit 0.

To try it:

```
cd template && PYTHONPATH=src python3 -m unittest tests.test_flow_adopt_split
```

A comment block above the two tests lists the three one-line edits to `flow.py` that each test catches, so you can check them yourself.

## Root cause
The rule is written into `flow.py`: `_reschedule` catches any exception and tells the caller to keep its current waves, and `_real` returns `None` for a path it can't resolve instead of raising. Nothing in the adoption suite checked either of those, so breaking them went unnoticed. The only test that caught two of them (`test_children_a_failed_reschedule_leaves_in_flight_are_let_go`, from fe8208f098556c8c3955aedec0c9f56cae2441dd) is about releasing claims across two processes and caught them by accident.

## Fix
Two test methods, plus the `pathlib` and `waves` imports they need:

- `test_a_failed_reschedule_after_a_split_never_aborts_the_run` runs `pdca flow 500 7 8`, where 8 depends on 7. Bundle 500 splits into 601/602, and `waves.partition_schedulable` is swapped for a wrapper that raises `RuntimeError` only when it is given `issue_601`. The test checks that the fault fired exactly once while 8 was still `PLANNED`, that rc is 0, that both stderr messages are printed and no traceback is, that 601/602 stay `PLANNED` and are left out of the results, and that 8 is driven in its own wave after the failure.
- `test_a_child_whose_path_will_not_resolve_never_aborts_the_run` runs `pdca flow 500`, where 500 splits into 601 and an independent 602. After the split, `pathlib.Path.resolve` is swapped for a wrapper that raises `OSError` only for `issue_601`. The fault goes one level below `flow._real` on purpose: replacing `_real` itself would replace the code under test. The test checks that rc is 0, that `ignoring child id '601'` is printed with no traceback, that 602 reaches `COMPLETE`, and that 601 stays `PLANNED` with no `patch.diff` and is not in the results.

Both swaps are undone with `addCleanup`. No production code changes.

## Verification
- **Claim:** a failed reschedule after a split leaves the children in flight and the run carries on.
  **Checked:** `template/src/pdca_harness/flow.py:1087-1100` (`_reschedule`'s broad `except` and its message) and `:1284-1291` (the `tail is None` branch keeps the existing waves) on `main` @ f33a23f342f0304f726ddbd314a515b83d1d86d7.
- **Claim:** a child whose path won't resolve is skipped, and the run does not crash.
  **Checked:** `flow.py:868-878` (`_real` returns `None` and never raises). It is reached from `:1035` (adoption) and `:1542` (`_warn_stranded_split_children`).
- **Test:** `template/tests/test_flow_adopt_split.py`. There is no fix to revert, so the failing case comes from mutating the code. Each edit was applied alone and only this module was run:
  - unmodified: 29 tests OK
  - M1, `flow.py:1286` `if tail is None:` → `if False:`: the reschedule test errors with `TypeError: must assign iterable to extended slice`
  - M2, `flow.py:1098` `except Exception` → `except ZeroDivisionError`: the reschedule test errors because the injected `RuntimeError` escapes `_reschedule`
  - M3, `flow.py:878` `return None` → `raise`: the unresolvable-child test errors with `OSError` escaping `_warn_stranded_split_children` (`:1542`)
  - extra: adding `wave_list[k + 1:] = []` in the `tail is None` branch (which throws away the remaining waves) makes the reschedule test fail, because bundle 8 is never driven
- **Full suite:** `cd template && PYTHONPATH=src python3 -m unittest discover -s tests` → 2073 tests OK (skipped=2), so the patched functions don't leak into other tests.

Fixes #496
