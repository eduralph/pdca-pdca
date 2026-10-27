# Build notes — issue 693 / flow-run-with-holds-exits-3 (iteration 2)

Target: `eduralph/pdca-harness` `main` @ `d6057eb`. Worktree: `$PDCA_WORKTREE`
(`pdca-harness.pdca-wt-l0`, HEAD `d6057eb`). Line numbers are post-patch in that worktree
unless marked `d6057eb:`. `patch.diff` is `git diff HEAD` of the worktree; the bundle's
`test_flow_hold_exit_code.py` is a byte copy of the patched test file.

## The carry-forward, and what I did about it

The finding: the old `test_the_single_id_shape_is_unchanged_with_no_hold` sat under a
header saying "the single-id shape reads the same signal", but it only ran one bundle
with no hold, so it exited 0 with or without the fix. Nothing tested that
`_report_single` hands `holds` to `_results_rc`.

I took neither of the two suggested routes. I replaced that test with real single-id runs
that do hold, driven through `cli._flow` only:

- **How a single id gets a fold.** One id is one wave, so no fold runs after it, unless
  the run adopts more bundles. `pdca flow <parent>` over a split parent that is already
  COMPLETE, whose children are still PLANNED, is the #473 recovery route: `flow_ids` skips
  the parent but hands it on as an adoption seed (`flow.py:2804-2831`), and
  `_drive_and_act` adopts its children at `k=-1` (`flow.py:2353-2356`), levelling them into
  their own waves. So the test builds parent `7` with the production `split.accept`
  (`split.py:885`) into the same four bundles the batch cases use (`10`, `11`, `12` in
  wave 0; `21` with `Depends on: 12` in wave 1), accepts the parent, and runs
  `cli._flow(["7"])`. The wave-0 fold holds `11`; the results map is
  `{7, 10, 11, 12, 21}`, all COMPLETE; the run answers through `_report_single`
  (`cli.py:681`). Before the fix that is 0; after it, 3. I checked the stderr of this run
  by hand: "issue_7 split → adopted children issue_10, issue_11, issue_12 into wave 0",
  "... issue_21 into wave 1", then the hold line for issue_11.
- **Why not rename the test.** The criterion says the rule "holds for both CLI shapes".
  A rename would leave the single-id half unproven.
- **Why not call `cli._report_single(..., holds)` directly.** The brief says the test
  "must not call a helper or parameter the fix adds". `holds` on `_report_single` is a
  parameter the fix adds, and before the fix the call fails with a TypeError, not on the
  exit-code assertion.

Two related gaps I closed while there:

- **The `--from-csv` route.** The brief's Citations line says the signal must reach `cli`
  on all three routes (`flow_ids` for both shapes, `flow_batch` for `--from-csv`). The
  previous attempt tested only `flow_ids`. New case: plan the conflict batch, run
  `cli._flow` with no ids and `from_csv="tracker.csv"`, the Plan session
  (`leaves.do_plan_batch`) stubbed to brief nothing (the test already planned every
  bundle). `flow_batch` sweeps the four bundles and drives them; the hold gives 3.
- **The single-id sign-off rule.** The criterion says the single-id shape "keeps its rule
  that AWAITING_SIGNOFF counts as success". New case: same split-parent run, but `21`
  (last wave) finishes Check and waits for sign-off. Expected 3: not 1 (the batch shape's
  answer for those results), not 0.

## What changed

**The rule — `template/src/pdca_harness/cli.py`**
- `cli.py:19` — `Mapping` added to the existing `collections.abc` import.
- `cli.py:170-177` — `epilog=` on the `flow` subparser lists exit codes 0/1/2/3.
  Reworded from iteration 1 so it is accurate: rc 2 also covers a bad `pdca.toml`
  (`cli.py:447-454`), and with one id a stop for sign-off counts as success (`cli.py:771`).
- `cli.py:637-640` — `_flow_claimed` makes the collector `holds: dict[str, str] = {}`.
- `cli.py:648-650` — passed to `flow.flow_batch` (`--from-csv` route) and on to
  `_report_batch`.
- `cli.py:665-667` — passed to `flow.flow_ids` (both id shapes).
- `cli.py:681-682` — passed to `_report_single` / `_report_batch`.
- `cli.py:690-691` — `_RC_HELD = 3`. No other `return 3` / `exit(3)` in `pdca_harness`.
- `cli.py:694-719` — `_results_rc(..., holds=None)`. Precedence, in code and docstring:
  any bundle not in `ok` → 1; else non-empty `holds` → 3; else 0. Empty map stays 0.
- `cli.py:737-738`, `:771` — `_report_single` takes `holds` and passes it with the
  single-id ok-set (`d6057eb:cli.py:741`).
- `cli.py:774`, `:779`, `:789` — `_report_batch` likewise (`d6057eb:cli.py:759`).

**The signal — `template/src/pdca_harness/flow.py`**
- `flow.py:2228` — `_drive_and_act(…, holds: dict[str, str] | None = None)`, keyword-only
  (after the existing `*`). Docstring `flow.py:2278-2283`.
- `flow.py:2581-2585` — at the end of the run, after `_report_conflict_holds`
  (`d6057eb:flow.py:2572`), fill `holds` from `held_unpushed` (`"unpushed"`) and
  `held_conflict` (`"conflict"`). Filled at the end, not at each record point, so every
  `break` out of the wave loop still reports what was held before the stop. Changed from
  iteration 1: keys are now spelled exactly as the results map's (`.replace("issue_", "")`,
  `flow.py:2570`) rather than `.removeprefix`, so each held id is a key of the map
  returned beside it (the advisory review's nit; #695 will reuse this signal by id). Same
  result for every real id.
- `flow.py:2602`, `:2628`, `:2689` — `flow_batch` takes `holds` and passes it on.
- `flow.py:2728`, `:2761-2762`, `:2847` — `flow_ids` takes `holds` and passes it on.
- Return types of `_drive_and_act` / `flow_ids` / `flow_batch` unchanged, as the brief
  pins; `holds=None` means no existing caller changes.

**Docs — `docs/07-crosscutting.md:711-722`** — a paragraph after the two stack-mode hold
paragraphs (`d6057eb:docs/07-crosscutting.md:684-711`): a held bundle is COMPLETE, the run
exits 3, 1 wins over 3, the rule holds with one id too (a stop for sign-off still counts
as finished), and the last-wave unpushed case is not covered.

**Existing test touched — `template/tests/test_flow_single_driver.py:806`, `:813`.**
Unchanged from iteration 1. `test_a_swept_bundle_is_let_go_before_the_nothing_schedulable_return`
replaces `cli._report_batch` with a pass-through spy that took only `results`; with the
new `holds` argument it raised TypeError. Now `report(results, *rest)` →
`real_report(results, *rest)`. It works against both signatures (green on the C4 red leg).

## Test — `template/tests/test_flow_hold_exit_code.py` (new, 311 lines)

Setup copied from `test_flow_same_wave_conflict.py:53-163`: `StackFoldGit` loaded by path
(`:49-52`), publisher mode `command`, `subprocess.run` → gh stub, and stubs for
`flow._drive_wave`, `flow._publish_bundle`, `publish.draft_texts`, plus
`leaves.do_plan_batch` (a Plan session that briefs nothing). Every case calls
`cli._flow(cfg, args)` (`:134-156`), publishing on, Act off, and asserts on its return
value. Imports are modules only (`:47`: `cli, flow, integrate, leaves, publish, split,
state`), all present on `d6057eb`.

| # | Case | Line | Expect | Red without fix? |
|---|------|------|--------|------------------|
| 1 | #674 hold, batch shape | `:213` | 3 | yes, `0 != 3` |
| 2 | #593 hold (stub publish returns False for 11, pushes nothing), batch | `:224` | 3 | yes, `0 != 3` |
| 3 | no hold, batch | `:235` | 0 | no (control) |
| 4 | case 1 + `20` depending on `11` → 20 PLANNED | `:246` | 1 | no (precedence guard) |
| 5 | #674 hold, `--from-csv` route (`flow_batch`) | `:257` | 3 | yes, `0 != 3` |
| 6 | #674 hold, single id over a split parent | `:284` | 3 | yes, `0 != 3` |
| 7 | no hold, single id over a split parent | `:290` | 0 | no (control) |
| 8 | case 6 with `21` left AWAITING_SIGNOFF | `:296` | 3 | yes, `0 != 3` |

Cases 6-8 also assert the single-id presentation was used: stdout is exactly the
`state<TAB>path` lines of `7` then each child (`:279-281`), not the batch table.

## Runs (all through the project's runners; tool timeouts as the bound)

- **C4** — `engine/scripts/run-verify.sh` with `PDCA_BUNDLE` / `PDCA_WORKTREE` set, on the
  final `patch.diff`: `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`. Green
  leg: 8/8 and `test_flow_single_driver` 23/23. Red leg (production hunks reverted, tests
  kept): cases 1, 2, 5, 6, 8 fail with `AssertionError: 0 != 3`; 3, 4, 7 pass;
  `test_flow_single_driver` 23/23.
- **Targeted mutations** (one production line changed at a time, then restored; the
  worktree diff was compared byte-for-byte with `patch.diff` afterwards):
  - `_report_single` calls `_results_rc` without `holds` (`cli.py:771`): only case 6
    failed, `0 != 3` (run before case 8 existed; case 8 would fail the same way).
  - `flow_batch` calls `_drive_and_act` without `holds` (`flow.py:2689`): only case 5
    failed, `0 != 3`.
  - `_report_single` uses the batch ok-set (drops AWAITING_SIGNOFF) but keeps `holds`:
    only case 8 failed, `1 != 3`.
- **T3** — `engine/scripts/run-suite.sh`: root suite 24 OK (real copier render/update),
  driver suite 2467 OK (2 skipped).
- **T2** — `engine/scripts/run-docs-check.sh`: docs lint clean; site render (22 pages) and
  link audit clean.
- **C5** — `engine/scripts/run-prod-path.py`: the added test imports `pdca_harness`.
- `flow --help` renders the epilog as one wrapped paragraph after the options.
- **Commit-ready:** the target has no pre-commit config, no `core.hooksPath`, no hook
  scripts and no Python formatter or linter config; its CI runs the docs lint, the site
  render and the render/update suites (T2 and T3 above, green). `git diff --check` is
  clean. The new test file has no line over 99 chars. The one added line over 100 is the
  `flow` help string moved onto its own line (`cli.py:171`); it is shorter than the line
  it replaced, and `cli.py` already has 33 lines over 100. DCO sign-off is added at
  publish.

## Refute-your-own-test

- **(a) Genuine red?** Yes. On the C4 red leg (production hunks reverted, test kept) the
  five hold cases fail on the exit-code assertion, `0 != 3`; none errors or fails to
  load. The three targeted mutations above show each new case binds the specific hand-off
  it is about.
- **(b) Production path?** Yes. Every case calls `cli._flow`, which runs the real
  `flow_ids` / `flow_batch` → `_drive_and_act` → real `integrate` folds on a real bare
  origin, real split adoption, and the real `_report_single` / `_report_batch` /
  `_results_rc`. The split parent is made by the production `split.accept`. Stubbed: the
  build and sign-off leaves (`_drive_wave`), the publish leaf (`_publish_bundle`, which
  still cuts and pushes a real branch), the Plan leaf (`do_plan_batch`, briefs nothing),
  `draft_texts` and the `gh` CLI. None of them is code this fix changes.
- **(c) Fixture includes the fault?** Yes. The #674 holds come from a real merge conflict
  the real fold hits (stderr names it; `fix/11` is checked not to be on the line). The
  #593 hold comes from the real `integrate.unpublished` check finding no push for 11. The
  single-id cases include the split parent and its adoption rather than a pre-levelled
  batch.

## Alternatives I ruled out

- **Single id via a mid-run split (#469)** instead of the #473 recovery seed: the stubbed
  build would have to split the parent during wave 0, and the parent (a close-disposition
  bundle with no patch) then goes through the publish step of that wave. The recovery
  route reaches the same `_report_single` call with no extra stub behaviour.
- **Lifting 0 → 3 in `_flow`** (`return _RC_HELD if rc == 0 and holds else rc`, about
  4 lines in `cli.py`) to keep `_report_batch(results)` one-argument and avoid the 2-line
  spy change in `test_flow_single_driver.py`: puts the precedence rule outside
  `_results_rc`. The brief wants the rule next to `_results_rc`, and #468's point was one
  exit-code rule, so I kept it there (same call as iteration 1).

## Not addressed here

The five items in `deferred-findings.json` (T5 prior-art judgment and the plan-review
items) are for the human at handover, not build work. No external dependency was missing:
everything ran offline with Python 3 and git.

## Housekeeping slips

- One command wrote a stray `/tmp/.unused` (a `git diff` redirect left in by mistake),
  outside my allowed roots. It holds only diff text. I did not delete it.
- I saved one C4 run's output to `.c4-run.log` at the worktree root. It is untracked and
  not git-ignored. It is not in `patch.diff`, and T3 ran green with it present, but a
  `git add -A` in that worktree would pick it up. I did not delete it.
