# Advisory code review — issue 695 (round 2)

No correctness bug found that breaks the brief's criteria. All gates pass. C4 shows 6 of the 9 new tests red without the fix and all 9 green with it. The round-1 gap (no test for the `"unchecked"` path) is closed by `test_an_end_of_run_check_that_cannot_fetch_is_named_and_exits_1`. The points below are minor. None of them needs to block.

## Correctness

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/integrate.py:764` with `template/src/pdca_harness/flow.py:2712-2721`: when carried bundles span more than one (repo, base) target, `_carried_tips` writes rewrites into `found` group by group. If a later group's fetch or `_in_line` then raises, `_report_late_rewrites` drops the rewrites already found and prints only the generic "could not check … by hand" line. The exit code is still 1, so the run does not end as a success. But a rewrite that was actually detected gets reported less clearly than it should be. Fix: catch the error per group inside `rewritten_carried`, or have `_report_late_rewrites` print what `found` already holds before it falls back to `"unchecked"` for the rest. This is a narrow multi-target case and no test covers it.

## Reuse and simplification

- `template/src/pdca_harness/flow.py:2685`: `do_publish and cfg.wave_mode != "merge" and cfg.publisher.mode != "stub"` repeats `hold_unmerged` (`flow.py:2485-2486`) word for word. Reuse that variable, or rely on `not carried_heads`. Only a real (non-dry) stack fold fills `carried_heads`, and the #646 carry passes no `carried`. Either way, one copy of the "a real fold ran" rule is less likely to drift later.
- `template/src/pdca_harness/flow.py:2712` filters `accepted` by `d.name in carried`, then `integrate.rewritten_carried` filters again (`integrate.py:759`). One of the two filters can go. Passing `accepted` straight through would do.

## Tests and cost

- `template/src/pdca_harness/integrate.py:1510-1512`: the retry sleeps `_FETCH_RETRY_PAUSE` (1 s) of real time. `test_a_fetch_that_keeps_failing_still_stops_the_fold`, `test_one_failed_fetch_does_not_stop_the_fold` and the unchecked-path run test each pay that second. The module-level constant exists, so the tests could patch it to 0 to keep the suite fast. Production cost is fine: the sleep only happens on a failed fetch, and the retry applies only to the pre-lock check (`integrate.py:713`).
- The (1c) spy in `template/tests/test_integrate_carried_rewrite_late.py` rewrites `fix/A` on the first `push` it sees through `integrate._git`. That is correct today: the stubbed `_publish_bundle` and `_push_from_human` push through the fixture's own `_git` (`tests/test_integrate_stack_bases.py:75`), not through `integrate._git`. The test's ancestry assertions also confirm the line took the old head. It would quietly retarget if publish ever started pushing through `integrate._git`, but that is not a defect today.

<!-- pdca:leaf-complete -->
