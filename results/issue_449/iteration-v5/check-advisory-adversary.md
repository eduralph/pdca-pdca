# Adversarial review — issue 449 (`flow-adopt-split-children`), iteration 5

**Evidence re-run (target `$PDCA_TARGET`).** C4's red→green reproduces: with the four
production files reverted to `HEAD` and `template/tests/test_flow_adopt_split.py` kept,
`cd template && PYTHONPATH=src python3 -m unittest tests.test_flow_adopt_split` gives
21 failures + 1 error on real assertions (no `ImportError`, so not PDCA-UNVERIFIABLE);
restored, 17/17 OK. The tests drive the real `flow.flow` / `flow.flow_ids` / `cli._flow`
and build the fixture with the production `split.accept`, so it is not a parallel
re-implementation. The whole offline driver suite (81 modules) is **green** here
(0 failures), which corroborates rather than refutes the carry-forward's claim that
check-gates.json's T3 red is an environmental `PDCA_VERIFY_BASE` isolation fault.
Mutation-probing the new logic, 10 of 14 mutations were caught. Findings below are the
survivors and two behavioural refutations.

- **NEEDS-HUMAN [impl] — the patch's headline contract is false at the CLI, the surface the
  docs describe.** `template/src/pdca_harness/cli.py:605-608` returns 0 for a single id
  whose bundle is `COMPLETE`, *before* `flow.flow` is ever called
  (`template/src/pdca_harness/cli.py:640`) — and a split parent is `COMPLETE`. Reproduced on
  byte-identical disk (500 terminal on `close-disposition = split`, 601/602 `PLANNED`):
  `pdca flow 500` → `rc=0`, stderr `already complete — nothing to run. To redo it: rm -rf
  …`, 601/602 still `PLANNED`, no adoption line; `pdca flow 500 999` (999 already COMPLETE,
  so the batch route drives the same nothing) → 601 and 602 both `COMPLETE`, both adoption
  lines printed. That is exactly the disagreement `docs/07-crosscutting.md:256-262` says
  cannot happen ("Naming a parent that is **already** terminal on a split does the same
  thing … `pdca flow 500` and `pdca flow 500 501` do the same thing to the same disk"), that
  `template/agents/planner.md.jinja:178-179` promises the planner ("Re-running the
  **parent's** id works too"), and that `template/src/pdca_harness/flow.py:409-416` calls
  "the recovery shape below". The recovery hint printed is also actively wrong for a split
  parent — `rm -rf` the bundle destroys the `split-lineage.json` adoption reads. The test
  suite misses it because `test_both_entry_points_recover_a_stranded_split_on_the_same_budget`
  (`template/tests/test_flow_adopt_split.py:389-423`) calls `flow.flow` / `flow.flow_ids`
  directly — the "hand-picked call" its own sibling test warns against at
  `template/tests/test_flow_adopt_split.py:257-262` ("the CLI's own arity switch … has to be
  the thing under test") — and the one test that does go through `cli._flow`
  (`:461`) arms a parent that is `PLANNED` at start, so the short-circuit never fires.

- **NEEDS-HUMAN [impl] — the two entry points still report the same run differently: rc 0 vs
  rc 1.** `template/src/pdca_harness/flow.py:473-476` discards the adoption tail's results
  map, so `flow.flow` still returns only the parent's state, and
  `template/src/pdca_harness/cli.py:649-656` derives both the stdout report and the exit code
  from that single value. Reproduced with `cfg.max_passes=3` and a mid-run Entry-B split of
  500 (adoption identical, 601 `COMPLETE`, 602 left `PLANNED` by the run pool in both cases):
  `pdca flow 500` → stdout `COMPLETE<TAB>…/issue_500`, **rc 0**; `pdca flow 500 999` → stdout
  `COMPLETE 500 / COMPLETE 601 / PLANNED 602 / flow: 2/3 complete`, **rc 1**. This is the
  same class of defect Iteration 4 sent back ("`pdca flow 500` exits 0 with children still
  PLANNED where `pdca flow 500 601` exits 1"), reached through a second route; the patch
  fixed only the `PreflightError` instance (`flow.py:78-79`) and pinned only that case
  (`template/tests/test_flow_adopt_split.py:461-488`). It contradicts
  `docs/07-crosscutting.md:259-262` ("on the same budget, and *report* it the same way") —
  a script reading the exit code records a clean run over an undriven child.

- **NEEDS-HUMAN — a scope/fitness call, not a code nit: this is the third distinct route by
  which the "both entry points agree" contract has broken.** Iteration 1 (RULING (b)) fixed
  the `flow_ids` terminal-parent filter, Iteration 4 fixed `_isolate` swallowing
  `PreflightError`, and this pass finds two more (CLI `COMPLETE` short-circuit; exit
  code/results map). The pattern is structural: `flow.flow` returns a *state* while
  `flow.flow_ids` returns a *results map*, and `cli._flow` gates the single-id route on
  pre-run disk state that the batch route does not consult
  (`template/src/pdca_harness/cli.py:604-628` vs `:657-663`). Patching each divergence as it
  is found has now cost four iterations; whether to keep doing so, route the single-id CLI
  path through `flow_ids` when the named bundle is a split parent, or scale the documented
  claim back to what the code actually guarantees is a human decision, not a rebuild.

- **NEEDS-HUMAN [impl] — the deliberate "terminal is part of the predicate" guard is
  unproven.** `template/src/pdca_harness/flow.py:811` (`_is_split_parent`) — deleting the
  `state.state(d) not in _TERMINAL` test leaves all 17 tests green. Its docstring
  (`flow.py:797-803`) argues at length that a parent still `AWAITING_SIGNOFF` is "a split
  nobody has accepted yet, and driving its children would spend whole cycles on work the next
  sign-off may reopen" — and the guard is load-bearing on the per-wave path
  (`flow.py:1248`), which passes `runnable` bundles that can still be non-terminal. Concrete
  missing case: a bundle on which `split.accept` has written the marker but whose sign-off
  recorded `iterate-do`, left in the wave at `ITERATE_DO`; no test asserts its children stay
  `PLANNED`.

- **NEEDS-HUMAN [impl] — the path-escape guard on hand-edited lineage ids is unproven.**
  `template/src/pdca_harness/flow.py:868` — deleting `if d.parent != cfg.bundle_root:` leaves
  all 17 tests green. The sibling hazard from the identical threat model (a duplicate id,
  `flow.py:860`) *does* have a test (`test_a_child_listed_twice_in_the_record_is_adopted_once`,
  `template/tests/test_flow_adopt_split.py:675`), so the omission is uneven, not a
  considered line. Concrete case: `"children": ["../../etc"]` in `split-lineage.json` —
  `cfg.bundle` (`config.py:469-471`) builds `results/issue_../../etc` happily.

- **NEEDS-HUMAN [impl] — two more guards survive mutation.** (a)
  `template/src/pdca_harness/flow.py:1002` — replacing `scheduled = [c for c in children if
  c.name in wave_of]` with `list(children)` is green, so nothing pins that a **held** child
  stays out of `bundles` / `batch_names` / the results map;
  `test_a_child_with_an_unresolvable_dependency_is_held_not_fatal`
  (`template/tests/test_flow_adopt_split.py:649-673`) asserts 602's *state* and that it is
  not announced, but never `assertNotIn("602", results)` — and via `_report_batch` that
  difference is an exit code. (b) `template/src/pdca_harness/flow.py:982` — replacing
  `known=batch_names | taken` with `set()` is green, so the "already in this run's drive set"
  skip that `_adoptable`'s docstring calls "the one skip they are most likely to be looking
  for in the log" (`flow.py:855-857`) is untested; `pdca flow 500 601` then double-counts 601
  into `bundles` and the closing `_sweep_quietly`.

## Attempted and could not refute

- The red→green itself: reverting the production hunks and keeping the test really does go
  red on assertions, not on imports; the fixture uses production `split.accept` and the real
  entry points, so it is not a mirror of the implementation.
- The run-budget pool is *provably* non-binding without adoption (`spent ≤ allowance·k` after
  `k` waves, `budget = allowance·len(wave_list)`, so `min(allowance, budget-spent) ==
  allowance` for every original wave) — `flow.py:1182`, `:1242-1243`; and
  `test_a_run_that_adopts_nothing_keeps_a_full_budget_per_wave` catches the mutation.
- Tried to break the splice with a *multi-wave named batch*: `flow_ids(["500","501"])` with
  `501 Depends on 500` and 500 splitting in wave 0 → waves `[500], [501, 601], [602]`, all
  four COMPLETE, nothing held. The `remaining`-goes-through-`partition_schedulable` path does
  not silently drop a named dependent.
- Tried to break recursion/termination: an **adopted** child that splits again mid-run
  (500 → 601,602; 601 → 701,702 during its own wave) is adopted correctly, attributed to 601,
  and terminates — waves `[500], [601,602], [701], [702]`, all COMPLETE.
- Mutations caught by the suite: wave-offset numbering, real-wave-vs-`k+1` announcement,
  the dedup `seen` set, `min(allowance, budget-spent)` clamping, `except PreflightError:
  raise`, `carried.left`, the `spent >= budget` run cap, the `flow()` terminal-break,
  `adopt_seeds` from `flow_ids`, the `onward` chain walk, and both `_adopt_split_children`
  callsites — 10 of 14.
- check-gates.json's `T3 fail` could not be reproduced: the full driver suite is green in
  this sandbox, consistent with the carry-forward's "pre-existing `PDCA_VERIFY_BASE`
  isolation fault", so it is not scored as a refutation.
