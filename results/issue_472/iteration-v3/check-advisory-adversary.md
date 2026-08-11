# Adversarial review — issue #472 (flow-adopt-core)

Advisory only; nothing here gates. Every `path:line` is on the target source at
`/home/eddie/pdca/pdca-harness.pdca-wt`. Toolchain was fully available (python3, git) —
no provisional verdicts.

## What I attacked and could not refute

- **The red→green is real, and it is the production path.** I reproduced C4 independently
  by rebuilding the base from `git show HEAD:` for the four production modules and keeping
  only the new test: **21 of 22 tests fail pre-fix, 22/22 pass post-fix** (the one that
  passes pre-fix, `test_a_run_that_adopts_nothing_keeps_a_full_budget_per_wave`
  `test_flow_adopt_split.py:503`, is by construction a no-regression guard). Every test
  drives through `cli._flow` (`test_flow_adopt_split.py:158`) and builds fixtures with the
  production `split.accept` (`split.py:525`) — no parallel re-implementation, no simulated
  split. Full offline driver suite: **1655 tests, OK**.
- **The suite is not over-broad.** I ran 24 targeted mutations of the production hunks;
  23 were killed. Notably: dropping the traversal guard (`flow.py:881`), the in-record
  dedup (`flow.py:873`), the terminal half of `_is_split_parent` (`flow.py:827`), the
  retraction block (`flow.py:1030`), `budget = allowance * len(wave_list)` →
  `allowance` (`flow.py:1216`), `min(allowance, budget - spent)` → `allowance`
  (`flow.py:1260`), `return used` → `return 0` on **both** un-finished `_drive_wave`
  exits (`flow.py:1105`, `flow.py:1144`), `k < len(wave_list) - 1` → a length cached
  before the loop (`flow.py:1312`), narrowing the marker catch to `OSError`
  (`flow.py:832`), and the brief's own required mutation `known=batch_names | taken` →
  `known=batch_names` (`flow.py:1001`), which fails exactly
  `test_two_parents_splitting_in_one_wave_adopt_a_shared_child_once` — the test the
  docstring cites at `flow.py:976`, as the brief demands.
- **The only surviving mutation is provably unobservable**, not a hole: `return sorted(out,
  key=lambda p: p.name)` → `return out` at `flow.py:903` survives, because the wave levelling
  (`waves.compute_waves`) and the announcement (`', '.join(sorted(...))`, `flow.py:1045`)
  both re-sort. No finding.
- **I could not break the pool arithmetic.** `spent >= budget` (`flow.py:1226`) provably
  cannot fire on a non-adopting run (`spent ≤ allowance·k` after `k` waves, `budget =
  allowance·len(wave_list)`), `budget - spent ≥ 1` whenever `_drive_wave` is reached, and
  `spent` can never exceed `budget`. Probed a 10-deep recursive split chain at
  `--max-passes 20`: terminates at 10 waves / 20 passes, rc 1, correctly named.
- **I could not break the splice on hostile lineage records.** Probed absolute ids
  (`"/etc/shadow"`), a non-list `children` value, a dependency **cycle** between two adopted
  children, `flow_batch` (CSV shape) adoption, a child declaring `Depends on <the split
  parent>`, and a child conflicting with an un-driven named tail bundle. All degrade to a
  report and rc 0/1 as documented — no traceback, no double-drive, no bundle outside
  `cfg.bundle_root`, `bundles` and `batch_names` stay in sync across every splice and
  retraction.
- **I could not find a wrong citation.** I checked all ~30 `path:line` citations the patch
  adds or updates (`split.py:373/382-390/296-311/525/627-634/635`, `flow.py:675/678/758/
  1141/1255/1260`, `config.py:686`, `waves.py:243-246`, `gates.py:782`,
  `test_flow_slice.py:32-55/1122-1128/1137`, and both rewritten `cli.py:609-610` targets
  `flow.py:1450-1464` / `flow.py:1485-1491`). All resolve exactly, including the two
  `cli.py` line numbers the previous rounds churned on.

## Findings

- **NEEDS-HUMAN [human] — `check-gates.json:84-93` records the *gating* T4 row as `pass`, but
  it attests nothing.** `gate-logs/T4-contribution.log` shows `exit 0`, `duration 0s`,
  `(no output captured)`, and the bundle directory contains **neither `commit-msg.txt` nor
  `pr-description.md`**. The target's own checker says that is not a pass: `cli.py:1094-1100`
  prints `gates.DEFERRED_MARKER` when `pr-description.md` is absent, precisely so the matrix
  records `deferred — re-gated at publish` "instead of a vacuous green the reviewer cannot
  reproduce" (`cli.py:1075-1083`, issue #401). So either the checker that ran is not the one
  this repo ships, or the row was recorded as `pass` where the contract says `deferred`;
  either way the row's own claim ("user-impact opener + tracker id in **both artifacts**")
  has no subject and the recorded green is not reproducible. This is **not** caused by the
  diff — but it is the third consecutive round the carry-forward has raised it
  (`brief.md:112`, `brief.md:117`) and two auto-iterate rebuilds did not move it, so routing
  it back to Do a third time would be wasted. A human has to decide whether a gating T4
  `pass` may stand on absent artifacts.

- **NEEDS-HUMAN [impl] — `flow.py:1003` prints a claim that `flow.py:1019-1021` then makes
  false, producing exactly the "one situation, two report shapes" the patch's own docstring
  (`flow.py:956-960`) exists to prevent.** `taken` is grown from `_adoptable`'s return
  *before* `_reschedule` runs, so a child the reschedule then **holds** is still reported to a
  second parent as "already in this run's drive set" — while it is in neither the drive set
  nor the results map. Concrete, reproduced case: `pdca flow 500 700`, both split in wave 0,
  `700`'s lineage record also names `602` (hand-edit / re-plan), and `602`'s brief carries an
  unresolvable `Depends on: GHOST`. stderr then carries both
  `flow: issue_602 — child of issue_700 not adopted again: already in this run's drive set`
  (`flow.py:890-891`) and `flow: issue_602 held this run — unresolved dependency (GHOST)`
  (`flow.py:776-777`), with `results == {500, 700, 601, 801}` — `602` excluded. The end state is
  correct (one hold, no double adoption), so this is report-only, but the first line is a
  false statement about the run's drive set at exactly the moment an operator is reading the
  log to find out who owns `602`. Not covered by any test: the shared-child tests
  (`test_flow_adopt_split.py:880`, `:847`) only exercise the case where the shared child is
  schedulable. Builder-fixable (report the skip after the reschedule, or re-report the held
  child against the parent that was refused).

- **NEEDS-HUMAN [impl] — `flow.py:895-896` prints the raw lineage id, re-opening the
  "uncopyable hint" hazard that `_lineage_children`'s strip at `flow.py:693-694` was written
  to close.** `_lineage_children` only strips *outer* whitespace, and its docstring justifies
  that strip as stopping "an uncopyable `pdca flow \" 469 \"` hint". The new consumer builds a
  path from the same value and then interpolates it unquoted into a resume hint. Concrete,
  reproduced case: a hand-edited record `{"children": ["6\n01", "602"]}` passes the traversal
  guard (`cfg.bundle("6\n01").parent == cfg.bundle_root`) and emits a stderr line that breaks
  in two — `flow: issue_6` / `01 — child of issue_500 NOT adopted: no brief.md (brief it at
  Plan, then \`pdca flow 6` / `01\`)`. The sibling guard one branch up already does the right
  thing (`{cid!r}`, `flow.py:882`); this branch and the "already terminal" branch
  (`flow.py:899-900`) do not. Low severity — `split.validate` (`split.py:281`) only ever
  *writes* `[A-Za-z0-9._-]+`, so it needs a hand edit — but it is a one-token fix and the
  guard's stated rationale already covers it.

## Explicitly considered and NOT filed

- The run-wide pool means a `pdca flow <id>` whose parent burns most of its 20 passes before
  splitting can adopt children and then abandon them "budget spent". That is not a
  refutation: `brief.md:19-20` scopes budget re-sizing to the sibling child, the outcome is
  named with a resume hint (`flow.py:1230-1233`), and the pre-fix behaviour stranded the same
  children with no announcement at all.
- A run whose only unfinished work is a **held** adopted child exits 0 (documented at `flow.py:990-995`).
  Checked against the base: pre-fix the identical scenario also exits 0 with the children
  stranded PLANNED, so this is not a regression, and `brief.md:23` asks for the exclusion.
- `flow.flow()` does not adopt (`flow.py:389-394`). Verified it is not a CLI route post-#468
  (`cli.py:604-622`), so the planner/doc claim "every shape" holds for every operator-facing
  shape; the library caller is documented.
