# Advisory code review — issue #780 (standalone sign-off consumes `signoff-decision`)

No findings need a human. The diff is clean on both lenses: correctness and reuse/simplification.

## Correctness

- `template/src/pdca_harness/cli.py:1542` — the new `unlink(missing_ok=True)` runs only after `signoff.record` succeeds (`cli.py:1529-1537`). It runs before `driver.run_issue` (`cli.py:1545`). The C6 refusal (`cli.py:1515-1520`) and the `ValueError` return (`cli.py:1532-1537`) both exit before it, so nothing is consumed when nothing was recorded. This is the same call `flow._apply_decision` makes (`template/src/pdca_harness/flow.py:205`). `missing_ok=True` covers the usual case, where no stale file exists. No off-by-one, leak or ordering problem found.
- `template/src/pdca_harness/cli.py:1542` — as the brief requires, the CLI does not copy the `state.SESSION_CARRY` capture from `flow.py:201-204`. The CLI takes its rationale from `--delta`, so deleting the file loses nothing the CLI path used. Any session rationale lines in a stale file are dropped, but that is the point of the fix and is out of scope here.

## Tests

- `template/tests/test_signoff_consumes_decision.py:100-189` — every brief leg is covered: (a) iterate-plan, (d) all four actions with `signoff.record` wrapped so a decision is actually recorded, (b) end to end with §6 cleared and the precondition asserted, (c) C6 refusal and `ValueError`, (e) a raising and a held `run_issue`. The tests call production `cli._signoff`, `flow._drive_wave` and `driver.run_issue` (C5 passes). `gate-logs/C4-verify.log` shows the tests fail without the fix, including the leg (b) `'COMPLETE' == 'COMPLETE'` failure, and pass with it.
- `template/tests/test_signoff_consumes_decision.py:37-62` — `_stub_config` and `_clear_needs_human` copy the ones in `test_signoff_orphan.py`. Leaving them is fine: 26 test files each define their own `_stub_config`, and no test imports helpers from another test. That is the house style, so this is not worth changing.

## Reuse / simplification / efficiency

- Nothing to raise. The fix is one line on a cold CLI path. A shared "record and consume" helper used by both `cli._signoff` and `flow._apply_decision` could stop the two paths drifting apart again. The brief rules out touching `flow._apply_decision`, so this is only a note, not a finding.

<!-- pdca:leaf-complete -->
