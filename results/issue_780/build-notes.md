# Build notes — issue #780 (standalone-signoff-consumes-decision)

Target: eduralph/pdca-harness @ main, worktree `/home/eddie/pdca/pdca-harness.pdca-wt-l1`.

## The change

One line plus a comment in `cli._signoff`:
`template/src/pdca_harness/cli.py:1538-1542` (post-patch) adds
`(d / leaves.SIGNOFF_DECISION).unlink(missing_ok=True)`, placed

- after the `signoff.record(...)` try/except (`cli.py:1529-1537`), so a C6 refusal
  (`cli.py:1515-1520`, returns earlier) or a `ValueError` from `record` (returns at
  `cli.py:1537`) records nothing and consumes nothing;
- before `driver.run_issue(d, cfg)` (`cli.py:1545` post-patch), so a held transition
  (`cli.py:1547-1554`) or a raising one cannot leave the stale decision behind.

This mirrors `flow._apply_decision`'s consume-on-record (`template/src/pdca_harness/flow.py:205`),
which also deletes after `record` and before `driver.run_issue` (flow.py:211). `leaves` was
already imported in cli.py (`cli.py:22`), so no import change.

Out of scope and untouched, per the brief: the `state.SESSION_CARRY` capture
(flow.py:201-204), `flow._apply_decision` itself, `state.DOWNSTREAM_OF_BRIEF`.

## Alternatives ruled out

- Delete at the top of `_signoff` (before C6). Rejected: leg (c) — a refused accept records
  nothing, so it must not consume the human's decision.
- Delete after `driver.run_issue`. Rejected: leg (e) — a raise or a held state would skip it
  (the held path returns at `cli.py:1554`), leaving the stale decision.
- Add `signoff-decision` to `DOWNSTREAM_OF_BRIEF` so iterate-plan archives it. Out of scope
  per the brief, and it only covers iterate-plan; iterate-do and the held/raise paths would
  still keep it.

## Test

`template/tests/test_signoff_consumes_decision.py` (new; copy in the bundle). Imports modules
only (`cli, driver, flow, leaves, signoff, state` + `config`), nothing this change adds.

- (a) `test_iterate_plan_consumes_stale_accept` — :103
- (d) `test_every_recording_action_consumes_the_file` — :111, subTest per action
  (`accept` clears §6 first; asserts `signoff.record` was called once so the fixture really
  records)
- (b) `test_stale_accept_does_not_finish_the_rebuilt_bundle` — :126. `--iterate-plan`, then
  re-plan + `driver.run_issue` back to AWAITING_SIGNOFF, `_clear_needs_human`, asserts
  `open_needs_human == []`, then `flow._drive_wave(..., max_passes=1)` with
  `auto_iterate=False` and a spying `run_signoff_batch` that writes nothing. Asserts not
  COMPLETE, still AWAITING_SIGNOFF, and the bundle was offered a session.
- (c) `test_c6_refused_accept_leaves_the_file` :154, `test_failed_record_leaves_the_file` :162
  (green on both sides; guards against an over-eager fix).
- (e) `test_consumed_before_a_raising_transition` :171 (`driver.run_issue` raises),
  `test_consumed_before_a_held_transition` :179 (`run_issue` returns PLANNED and `held`
  patched True → `_signoff` returns 1).

All legs use `no_publish=True` on the args namespace so the accept leg stays offline;
publish is not under test.

Runner: the project's documented offline suite command
(`cd template && PYTHONPATH=src python3 -m unittest …`, docs/INTEGRATION.md §3), wrapped in
`timeout`.

## Refute-your-own-test

- **(a) Genuine red? Yes.** Ran before writing the fix: `FAILED (failures=8)` — (a), (b),
  (d)×4 subtests, (e)×2; (c) passed. After the fix: `OK`, 7 tests. Then reverted only the
  `template/src/*` hunk of patch.diff with `git apply -R --include='template/src/*'`:
  `FAILED (failures=8)` again; re-applied: `OK`. Leg (b) on main fails with
  `'COMPLETE' == 'COMPLETE' : the stale accept finished a rebuilt bundle nobody reviewed`,
  which is the end-to-end defect from the brief.
- **(b) Production path? Yes.** Calls the real `cli._signoff` with a real argparse
  namespace, the real `signoff.record`, real `driver.run_issue` (except in leg (e), where
  patching it is the point), and the real `flow._drive_wave` pre-apply. Only the
  interactive sign-off leaf (`leaves.run_signoff_batch`) is replaced by a spy, as in
  `test_signoff_orphan.py`.
- **(c) Fixture includes the fault? Yes.** Each bundle is driven by stub Plan→Do→Check to a
  real AWAITING_SIGNOFF with a real SUMMARY, then the stale `accept` is written to disk. In
  leg (b) §6 is cleared and the precondition asserted, so C6 does not mask the bug.

## Whole suite / commit readiness

Full offline suite post-fix: `Ran 2654 tests … OK (skipped=2)`. The target has no formatter
or pre-commit hook configured (no `.pre-commit-config.yaml`, no `core.hooksPath`, no
ruff/black config; CI workflows are docs/render/DCO). New lines kept ≤ 95 chars to match
the surrounding style. The publish commit needs a DCO `Signed-off-by` (`.github/workflows/dco.yml`).
