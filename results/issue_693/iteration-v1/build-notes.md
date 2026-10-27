# Build notes — issue 693 / flow-run-with-holds-exits-3

Target: `eduralph/pdca-harness` `main` @ `d6057eb`. Worktree: `$PDCA_WORKTREE`
(`pdca-harness.pdca-wt-l0`). Line numbers below are post-patch in that worktree unless
marked `d6057eb:`.

## What changed

**The rule — `template/src/pdca_harness/cli.py`**
- `cli.py:690` — `_RC_HELD = 3`. Exit code 3 was unused anywhere in `pdca_harness`
  (grep for `return 3` / `exit(3)` found nothing).
- `cli.py:693-718` — `_results_rc` takes an optional `holds` mapping. Precedence, coded
  and written in the docstring: any bundle not in `ok` → 1; else non-empty `holds` → 3;
  else 0. Empty map stays 0 (nothing can be held without a drive).
- `cli.py:736-770` — `_report_single(…, holds=None)` passes `holds` through and keeps
  the `AWAITING_SIGNOFF` ok-set (`d6057eb:cli.py:741`).
- `cli.py:773-788` — `_report_batch(results, holds=None)` likewise (`d6057eb:cli.py:759`).
- `cli.py:637-639` — `_flow_claimed` makes `holds: dict[str, str] = {}` and hands it to
  `flow.flow_batch` (`:647-649`, the `--from-csv` path) and `flow.flow_ids` (`:664-666`,
  both id shapes), then to the reporters (`:649`, `:680-681`).
- `cli.py:170-176` — `epilog=` on the `flow` subparser lists exit codes 0/1/2/3.
- `cli.py:19` — `Mapping` added to the existing `collections.abc` import.

**The signal — `template/src/pdca_harness/flow.py`**
- `flow.py:2228` — `_drive_and_act(…, holds: dict[str, str] | None = None)`,
  keyword-only (after the existing `*`). Docstring `:2278-2283`.
- `flow.py:2581-2584` — at the end of the run, after `_report_conflict_holds`
  (`d6057eb:flow.py:2572`), fill `holds` from `held_unpushed` (`"unpushed"`) and
  `held_conflict` (`"conflict"`), keyed by the same bare id the results map uses. Filled
  at the end, not at each record point, so every `break` out of the wave loop still
  reports whatever was held before the stop.
- `flow.py:2601`, `:2627`, `:2688` — `flow_batch` takes `holds` and passes it on.
- `flow.py:2727`, `:2760-2761`, `:2846` — `flow_ids` takes `holds` and passes it on.
- Return types of `_drive_and_act` / `flow_ids` / `flow_batch` unchanged, as the brief
  pins. `holds=None` default means no existing caller changes.

**Docs — `docs/07-crosscutting.md:711-719`** — a new paragraph right after the two
stack-mode hold paragraphs (`d6057eb:docs/07-crosscutting.md:684-711`): a held bundle is
COMPLETE, the run exits 3, 1 wins, and the last-wave unpushed case is not covered.

**Existing test touched — `template/tests/test_flow_single_driver.py:806`, `:813`.**
`test_a_swept_bundle_is_let_go_before_the_nothing_schedulable_return` replaces
`cli._report_batch` with a spy its docstring calls "pass-through", but the spy only took
`results`, so the new `holds` argument raised `TypeError`. Changed to
`report(results, *rest)` → `real_report(results, *rest)`. It keeps its meaning and also
works against the pre-fix signature (it was green on the C4 red leg).

Ruled out for that: keeping `_report_batch(results)` one-argument and lifting 0 → 3 in
`_flow` with `return _RC_HELD if rc == 0 and holds else rc`. About 4 lines in
`cli.py` instead of 2 in the test, but it puts the precedence rule in `_flow` rather than
in `_results_rc`. The brief wants the rule next to `_results_rc`, and #468's point was to
have one exit-code rule, so I kept it there.

## Test — `template/tests/test_flow_hold_exit_code.py` (new)

Copies the `SameWaveConflict` setup of `test_flow_same_wave_conflict.py:53-163`: the
`StackFoldGit` real-git fixture loaded by path, publisher `command`, `subprocess.run` →
gh stub, `flow._drive_wave` / `flow._publish_bundle` / `publish.draft_texts` stubbed.
Every case drives `cli._flow(cfg, args)` with `issue_ids` = the batch, `no_publish=False`,
`no_act=True`, and asserts on its return value only. Imports are modules only
(`cli, flow, integrate, publish, state`).

1. #674 hold → 3: `10`/`11` edit the same line of `shared.txt`; `12`; `21` depends on
   `12`. Asserts the hold stderr line, `11` not on the line, all COMPLETE, rc 3.
2. #593 hold → 3: no conflict; the `_publish_bundle` stub returns False for `11`
   without pushing. Asserts "pushed no branch", all COMPLETE, rc 3.
3. No hold → 0: asserts no "held" on stderr, `11` on the line, rc 0.
4. Failure wins: case 1 plus `20` depending on `11` → `20` PLANNED, rc 1.
5. Extra: single-id shape with one bundle stays rc 0. A single id is one wave, so no
   fold runs and no hold can happen; this only guards against a regression in that shape.
   I did not find a way to make the single-id shape produce a hold without split
   adoption, which this brief does not cover. The single-id code path passes `holds`
   to `_results_rc` the same way the batch one does (`cli.py:770`).

## Runs

- Pre-fix (`PYTHONPATH=src python3 -m unittest tests.test_flow_hold_exit_code` in
  `template/`, the same command `run-verify.sh` uses): cases 1 and 2 FAIL `0 != 3`;
  3, 4, 5 pass.
- Post-fix: 5/5 OK.
- C4 gate (`engine/scripts/run-verify.sh` with `PDCA_BUNDLE` / `PDCA_WORKTREE` set):
  `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`.
- T3 (`engine/scripts/run-suite.sh`): root suite 24 OK, driver suite 2464 OK (2 skipped).
- T2 (`engine/scripts/run-docs-check.sh`): lint clean, site render + link audit clean.
- Formatter / hooks: the target has no `.pre-commit-config.yaml`, no `core.hooksPath`,
  and no Python linter config; its CI runs only the docs checks and render/update suites,
  all green above. One added line is 101 chars (`cli.py:171`), shorter than the
  `p_flow` line it replaced and shorter than several existing help lines.

## Refute-your-own-test

- **(a) Genuine red?** Yes. With the production hunks reverted (the C4 red leg, and the
  first run before any edit), `test_a_run_that_held_a_same_wave_conflict_exits_3` and
  `test_a_run_that_held_an_unpushed_bundle_exits_3` fail `AssertionError: 0 != 3`.
- **(b) Production path?** Yes. The test calls `cli._flow`, which runs the real
  `flow_ids` → `_drive_and_act` → real `integrate` folds against a real bare git origin,
  and the real `_results_rc` / `_report_batch`. Stubbed: the build and sign-off leaves
  (`_drive_wave`), the publish leaf (`_publish_bundle`, which still pushes a real branch),
  the `gh` CLI, and `draft_texts`. None of those is the code this fix changes.
- **(c) Fixture includes the fault?** Yes. Case 1's hold comes from a real merge conflict
  the real fold hits (stderr shows `issue_11 held out of the integration fold`, and the
  test checks `fix/11` is not an ancestor of the line tip). Case 2's hold comes from the
  real `integrate.unpublished` check finding no `publish.json` for `11`.

## Housekeeping slip

I redirected the T3 run's output to `/tmp/issue693-suite.log`, which is outside the
roots I'm allowed to write. I did not delete it (cleanup is the harness's job). It holds
only test output.
