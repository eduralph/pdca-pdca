# Build notes — issue 693 / flow-run-with-holds-exits-3 (iteration 3)

Target: `eduralph/pdca-harness` `main` @ `d6057eb`. Worktree: `$PDCA_WORKTREE`
(`pdca-harness.pdca-wt-l0`, HEAD `d6057eb`, clean at the start of this round). Line numbers
are post-patch in that worktree unless marked `d6057eb:`. `patch.diff` is the worktree's
`git diff HEAD` plus the new test file as a new-file diff; `git apply -R --check patch.diff`
passes on the worktree, so the patch matches it exactly. The bundle's
`test_flow_hold_exit_code.py` is a byte copy of the patched test file.

## The carry-forward, and what I did about it

The iteration-2 finding: the two no-hold cases checked `assertNotIn("held", self.err)`
over all of stderr. Any unrelated line that contains "held" would fail them for the wrong
reason. Suggested fix: assert that the two exact phrases the hold cases match are absent.

What I did (test file only; the production hunks are byte-identical to iteration 2):

- `template/tests/test_flow_hold_exit_code.py:54-61` — two module constants, with a comment
  naming what prints each one: `_CONFLICT_HOLD = "held out of the integration fold"` (#674)
  and `_UNPUSHED_HOLD = "pushed no branch this run"` (#593).
- `:220-223` — `_assert_held_nothing()`: asserts neither phrase is in the last run's stderr.
- `:252`, `:306` — the two no-hold cases call it instead of `assertNotIn("held", …)`.
- `:230`, `:242`, `:265`, `:274`, `:300`, `:320` — the six hold checks now read
  `f"issue_11 {_CONFLICT_HOLD}"` / `f"issue_11 {_UNPUSHED_HOLD}"`, the same strings as
  before, now taken from the constants.

**Why these two phrases cover both holds.** The fold prints the #674 line through
`_announce_conflict_holds` (`flow.py:1158-1168`, the print at `:1165`) for every bundle it
newly adds to `held_conflict`, and the #593 line at `flow.py:2530` for every bundle it newly
adds to `held_unpushed`. Nothing else writes `held_conflict`. The only writer is the in-run
fold (`flow.py:2539-2554`: `held_out=… held_conflict` at `:2545`), and it announces the new
entries on both its error path (`:2548`) and its success path (`:2553`). So the end-of-run
report (`_report_conflict_holds`, `flow.py:1171-1180`, called at `:2580`, "was held out of
this run's integration line") can only print in a run that already printed the fold's
line. A third phrase would add nothing (see "Alternatives").

**Why shared constants, not two inline strings.** The no-hold checks only mean something if
the phrases are ones the run really prints on a hold. With one constant per phrase, the
hold cases prove that on every run. If the wording in `flow.py` changes, the hold cases go
red, instead of the no-hold checks passing quietly on a phrase the run no longer prints.

**Probes of the new check** (temporary edits to the test, run through
`engine/scripts/run-verify.sh`, then the test was restored from the bundle copy and
`git apply -R --check patch.diff` confirmed the worktree matched the patch again):

- *Probe A — the new check fires on a real hold and ignores unrelated text.* The batch
  no-hold case was switched to the conflict batch (so the run really holds `11`), and the
  `_drive_wave` stub printed `flow: PROBE — an unrelated line that says held, holding
  nothing` in every run. Result: 7/8 passed. The one failure was the switched case, at
  `_assert_held_nothing`: `AssertionError: 'held out of the integration fold' unexpectedly
  found in …`. The single-id no-hold case passed with the unrelated line in its stderr.
- *Probe B — the old check fails for the wrong reason.* Same unrelated line, switch undone,
  iteration 2's `assertNotIn("held", self.err)` put back in both no-hold cases. Result:
  both failed, `'held' unexpectedly found in 'flow: PROBE — an unrelated line that says
  held…'`. That is the finding, reproduced.

## What changed (production and docs unchanged from iteration 2)

**The rule — `template/src/pdca_harness/cli.py`**
- `cli.py:19` — `Mapping` added to the `collections.abc` import (`d6057eb:cli.py:19`).
- `cli.py:170-177` — `epilog=` on the `flow` subparser lists exit codes 0/1/2/3
  (`d6057eb:cli.py:170`). `flow --help` renders it as one wrapped paragraph after the
  options (checked this round).
- `cli.py:638-640` — `_flow_claimed` creates the collector `holds: dict[str, str] = {}`.
- `cli.py:648-650` — passed to `flow.flow_batch` (the `--from-csv` route) and on to
  `_report_batch` (`d6057eb:cli.py:638-640`).
- `cli.py:665-667` — passed to `flow.flow_ids`, which both id shapes use
  (`d6057eb:cli.py:655-657`).
- `cli.py:681-682` — passed to `_report_single` / `_report_batch` (`d6057eb:cli.py:671`).
- `cli.py:690-691` — `_RC_HELD = 3`.
- `cli.py:694-719` — `_results_rc(..., holds=None)` (`d6057eb:cli.py:679-690`). Precedence
  in the docstring (`:696-716`) and code (`:717-719`): any bundle not in `ok` → 1; else a
  non-empty `holds` → 3; else 0. An empty map stays 0.
- `cli.py:737-738`, `:771` — `_report_single` takes `holds` and passes it with the
  single-id ok-set, which keeps AWAITING_SIGNOFF as success (`d6057eb:cli.py:741`).
- `cli.py:774`, `:779`, `:789` — `_report_batch` likewise (`d6057eb:cli.py:759`).

**The signal — `template/src/pdca_harness/flow.py`**
- `flow.py:2228` — `_drive_and_act(…, holds: dict[str, str] | None = None)`, keyword-only
  (after the existing `*`; `d6057eb:flow.py:2227` is the last parameter before it).
  Docstring `:2278-2283`.
- `flow.py:2581-2585` — at the end of the run, after `_report_conflict_holds`
  (`d6057eb:flow.py:2572`), fill `holds` from `held_unpushed` (`"unpushed"`,
  `d6057eb:flow.py:2295`) and `held_conflict` (`"conflict"`, `d6057eb:flow.py:2300`), keyed
  as `results` is (`.replace("issue_", "")`, `flow.py:2570`). Filled at the end, not where
  each hold is recorded, so a `break` out of the wave loop still reports what was held
  before the stop.
- `flow.py:2602`, `:2628`, `:2689` — `flow_batch` takes `holds` and passes it on
  (`d6057eb:flow.py:2673`).
- `flow.py:2728`, `:2761-2762`, `:2847` — `flow_ids` likewise (`d6057eb:flow.py:2827`).
- The return types of `_drive_and_act` / `flow_ids` / `flow_batch` are unchanged, as the
  brief pins. `holds=None` by default, so no existing caller changes. The only callers of
  `_drive_and_act` are `flow.py:2687` and `:2844`; the only callers of `flow_ids` /
  `flow_batch` in `src/` are `cli.py:665` and `:648`. `--rehearse` reaches the same `_flow`
  with a stub publisher, whose dry-run folds hold nothing (`flow.py:2526`, `:2545`).

**Docs — `docs/07-crosscutting.md:711-722`** — a paragraph right after the two stack-mode
hold paragraphs (`d6057eb:docs/07-crosscutting.md:684-709`): a held bundle is COMPLETE, the
run exits 3, 1 wins over 3, the rule holds with one id too (a stop for sign-off still counts
as finished), and the last-wave unpushed case is not covered.

**Existing test touched — `template/tests/test_flow_single_driver.py:806`, `:813`.**
Unchanged from iterations 1-2. A spy on `cli._report_batch` took only `results`; with the
new argument it raised TypeError. Now `report(results, *rest)` → `real_report(results,
*rest)`, which works with both signatures (green on the C4 red leg, 23/23).

## Test — `template/tests/test_flow_hold_exit_code.py` (new, 325 lines)

Setup as in iteration 2: `StackFoldGit` loaded by path (`:49-52`), publisher mode `command`,
`subprocess.run` → `gh` stub, and stubs for `flow._drive_wave`, `flow._publish_bundle`,
`publish.draft_texts` and `leaves.do_plan_batch`. Every case calls `cli._flow(cfg, args)`
(`:143-165`), publishing on, Act off, and asserts on its return value. Imports are modules
only (`:47`), all present on `d6057eb`.

| # | Case | Line | Expect | Red without fix? |
|---|------|------|--------|------------------|
| 1 | #674 hold, batch shape | `:227` | 3 | yes, `0 != 3` |
| 2 | #593 hold (stub publish returns False for 11, pushes nothing), batch | `:238` | 3 | yes, `0 != 3` |
| 3 | no hold, batch | `:249` | 0 | no (control) |
| 4 | case 1 + `20` depending on `11` → 20 PLANNED | `:260` | 1 | no (precedence guard) |
| 5 | #674 hold, `--from-csv` route (`flow_batch`) | `:271` | 3 | yes, `0 != 3` |
| 6 | #674 hold, single id over a split parent | `:298` | 3 | yes, `0 != 3` |
| 7 | no hold, single id over a split parent | `:304` | 0 | no (control) |
| 8 | case 6 with `21` left AWAITING_SIGNOFF | `:310` | 3 | yes, `0 != 3` |

## Runs (all through the project's gate scripts, each under `timeout`)

- **C4** — `engine/scripts/run-verify.sh` with `PDCA_BUNDLE` / `PDCA_WORKTREE` set, on the
  final `patch.diff`: `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`. Green
  leg: 8/8, and `test_flow_single_driver` 23/23. Red leg (production hunks reverted, tests
  kept): cases 1, 2, 5, 6 and 8 fail with `AssertionError: 0 != 3`; 3, 4 and 7 pass;
  `test_flow_single_driver` 23/23. Worktree restored to base + patch afterwards (checked).
- **T3** — `engine/scripts/run-suite.sh`, run twice: once while I was still editing the
  constants' comment, and again on the final tree after the last C4 run. Both times: root
  suite 24 OK (real copier render/update), driver suite 2467 OK (2 skipped).
- **T2** — `engine/scripts/run-docs-check.sh`: docs lint clean; site render (22 pages) and
  link audit clean.
- **C5** — `PDCA_PROD_PACKAGE=pdca_harness engine/scripts/run-prod-path.py`: the added test
  imports `pdca_harness`.
- **Commit-ready.** The target has no pre-commit config, no `core.hooksPath`, no active
  hooks in its git dir (only `*.sample`), and no ruff / black / flake8 / isort config in any
  `.toml`, `.cfg`, `.ini` or `.jinja` file (the only `pyproject` is
  `template/pyproject.toml.jinja`, build and packaging sections only). Its CI runs the
  docs lint, the site render and the render/update suites (T2 and T3 above, green).
  `git diff --check` is clean. The new test file has no trailing whitespace, no tabs, no
  line over 99 characters, and compiles. The one added line over 100 characters is the
  `flow` help string on its own line (`cli.py:171`, 107 characters). It replaces a
  127-character line (`d6057eb:cli.py:170`), and `d6057eb`'s `cli.py` already has 33 lines
  over 100. The DCO sign-off (`CONTRIBUTING.md:7-17`) is a commit trailer added at publish.

## Refute-your-own-test

- **(a) Genuine red?** Yes. On the C4 red leg (production hunks reverted, test kept) the
  five hold cases fail on the exit-code assertion, `0 != 3`. All 8 cases load and run;
  none errors. The new no-hold check is itself binding: probe A makes it fail on a real
  hold. Probe B shows the old check failing on unrelated text, which the new one ignores.
- **(b) Production path?** Yes. Every case calls `cli._flow`, which runs the real
  `flow_ids` / `flow_batch` → `_drive_and_act` → real `integrate` folds on a real bare
  origin, real split adoption, and the real `_report_single` / `_report_batch` /
  `_results_rc`. The split parent is made by the production `split.accept`. Stubbed: the
  build and sign-off leaves (`_drive_wave`), the publish leaf (`_publish_bundle`, which
  still cuts and pushes a real branch), the Plan leaf (`do_plan_batch`, briefs nothing),
  `draft_texts` and the `gh` CLI. None of them is code this fix changes.
- **(c) Fixture includes the fault?** Yes. The #674 holds come from a real merge conflict
  the real fold hits (stderr names it; `fix/11` is checked not to be on the line). The #593
  hold comes from the real `integrate.unpublished` check finding no push for `11`. The
  single-id cases go through the split parent and its adoption, not a pre-levelled batch.

## Alternatives I ruled out

- **Add a third phrase, the end-of-run report** ("was held out of this run's integration
  line", `flow.py:1177`). Cost: 1 line in the constants. Rejected: it is redundant (shown
  above: it only prints in a run that already printed the fold's line), and no hold case
  asserts it. So if its wording changed, nothing would go red and the no-hold check would
  carry a stale phrase. That is the failure mode the shared constants exist to prevent.
- **A narrower regex, e.g. `r"issue_\d+ held"`.** It would still match `_runnable`'s
  "`{name} held —`" lines (`flow.py:810`, `:818`, `:832`, `:839`). Those are dependents held
  for other reasons, not the two holds this issue is about. It would also not match the #593
  phrase at all.
- **Check the `holds` collector's contents in the no-hold cases.** Not allowed: the brief
  says the test must not call a helper or parameter the fix adds (`brief.md:17`), and it
  would not load on the red leg.
- **Production unchanged.** The finding was test-only. The iteration-2 reviews found no
  correctness issue in the production hunks. I re-read them this round against the base
  (call sites, keys, precedence, the empty-map path at `cli.py:780-782`, the dry-run path)
  and found nothing to change.

## Not addressed here

The five items in `deferred-findings.json` are for the human at handover, not build work.
No external dependency was missing: everything ran offline with Python 3 and git.

## Housekeeping

- This round created no files outside the worktree and the bundle. The probe edits were
  made in the worktree's test file and undone by copying the bundle's final copy back; the
  gate scripts' own `mktemp` dirs and test temp dirs are theirs.
- From iteration 2: `/tmp/.unused` (diff text only, 15840 bytes) is still there. I did not
  delete it, since cleanup belongs to the harness. Iteration 2's `.c4-run.log` is gone from
  the worktree root (the worktree was reset before this round).
