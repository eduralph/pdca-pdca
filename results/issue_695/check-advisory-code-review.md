# Advisory code review — issue 695 (round 4)

I found no correctness bugs and no NEEDS-HUMAN items. Both lenses are clean apart from the minor notes below. None of them block, and none needs routing back to Do.

The round-3 wording fix is in place. `IntegrationError` now has a `cause` field (`template/src/pdca_harness/integrate.py:96-98`). `_fetch` and `_in_line` fill it with only the failure, with no "re-run" advice (`integrate.py:1554-1562` and the `_in_line` raise). The end-of-run line prints `cause`, not the fold's full message (`template/src/pdca_harness/flow.py:2718-2733`). Earlier rounds' fixes are still intact: each target and each branch is judged on its own, so one that cannot be checked does not hide a rewrite found on another (`integrate.py:755-807`), and the "unchecked" path exits 1. The fold's own error text is unchanged, word for word. The test at `template/tests/test_integrate_carried_rewrite_late.py:483-510` pins it, and the refactor through `_carried_rewrite` (`integrate.py:739-752`) puts back the same sentence it took out.

## Correctness

- `template/src/pdca_harness/flow.py:2688-2689` — `line_stopped` is set only at the two fold/re-gate `break`s (`flow.py:2652`, `:2668`). The pass-budget `break` (`flow.py:2527`) and the merge-mode `break` (`flow.py:2616`) leave it False. That is correct. In merge mode `carried_heads` stays empty, so no check runs. After a budget stop, an earlier fold did carry branches, and no later fold judged them, so the end-of-run check is the only place a rewrite gets reported. This matches brief criterion (2b), which names only the fold-error and red re-gate breaks. Noting it so nobody "fixes" it later. No action.
- `template/src/pdca_harness/integrate.py:96-98` — `cause` is a keyword-only constructor argument and is not stored in `args`. A pickled or copied `IntegrationError` (for example one sent across a process boundary) would rebuild with `cause = str(self)`, the full message including the fold's advice. Today `cause` is read only in-process, in `rewritten_carried` (`integrate.py:784`, `:797`), so nothing breaks. No action.
- `template/src/pdca_harness/integrate.py:755-807` — `rewritten_carried` reads each bundle's branch from `publish.json` again at the end of the run (`_fold_candidates` → `_published_ref`). The fold judges against the `refs` it read at fold time. These differ only if a carried bundle's record names a different branch mid-run, which the flow does not do for a bundle it has already folded. No action.

## Reuse, simplification, efficiency

- `template/src/pdca_harness/integrate.py:739-752` — `_carried_rewrite` is now the one place that makes the rewrite judgment, shared by `_carried_tips` and `rewritten_carried`. That is the reuse the brief asked for. `cli._results_rc` (`template/src/pdca_harness/cli.py:698`, `:730`) extends #693's `holds` channel and does not add a second one.
- `template/src/pdca_harness/integrate.py:1530`, `:1554-1556` — the retry is per remote inside `_fetch` and only active with `attempts=2`. Every other caller keeps one try. The cost is at most one 1-second pause per failing remote, and only when a fetch has already failed. The tests set the pause to 0 (`test_integrate_carried_rewrite_late.py:77-81`). The end-of-run check adds one fetch per carried target to every stack-mode run that folded. That cost is expected for this feature.

## Tests and gates

- `template/tests/test_integrate_carried_rewrite_late.py:234-421` drives every run case through `cli._flow` and reads the exit code only from its return value. It covers (1), (1b), (1c), (2) both variants, (2b), the "unchecked" path, both orders of a target whose fetch fails next to a rewrite on another target, and an ancestry-check failure next to a rewrite on the same target. Lines `:461-481` cover (3) and (4).
- Gate evidence: `gate-logs/C4-verify.log` shows 9 of 13 tests fail with the fix reverted and pass with it. The 4 that pass before the fix are the no-false-report, no-double-report and fold-wording cases, which should pass either way. `gate-logs/T3-suite.log` shows the driver suite OK, 2526 tests.

<!-- pdca:leaf-complete -->
