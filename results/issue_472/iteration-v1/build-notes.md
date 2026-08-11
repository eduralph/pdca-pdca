# Build notes — issue_472 (flow-adopt-core): mid-run split adoption on the unified drive path

Target: `eduralph/pdca-harness` @ `main` (worktree `/home/eddie/pdca/pdca-harness.pdca-wt`,
HEAD `3e3b829` — the merge of PR #470/#468, so the brief's `Depends on (merged): 468` is
satisfied and every line number below is against that tree **plus this patch**).

## What this is

The brief says: re-land the **mid-run adoption core** of the converged #469 v3 patch by
**carving** it out of `results/issue_469/iteration-v3/patch.diff`, not re-deriving it, and
leave terminal-parent recovery + the operator-facing reporting/budget refinements to the
sibling child. That is exactly what this is. Every production line below is v3's, edited
only where v3's prose named a mechanism that is *not* in this child (the adoption seeds).

## The carve — what came over, and what did not

Kept (v3 → here, essentially verbatim):

| piece | where it lands |
|---|---|
| `_report_held` (one held-report shape, shared with `flow_batch`) | `flow.py:768` |
| `SPLIT_DISPOSITION` | `flow.py:807` |
| `_is_split_parent` (terminal **and** marker; total catch) | `flow.py:810` |
| `_adoptable` (read lineage → filter → report every skip) | `flow.py:836` |
| `_reschedule` (tolerant re-levelling: `partition_schedulable` + `compute_waves`) | `flow.py:906` |
| `_adopt_split_children` (splice into `wave_list[k+1:]`, announce real waves) | `flow.py:929` |
| `_drive_wave` returns the passes it consumed, on **every** exit | `flow.py:1016`, `1073`, `1103`, `1112` |
| run-wide pass pool sized off the pre-adoption schedule | `flow.py:1177`, guard at `:1187`, spend at `:1220` |
| the splice call after each wave | `flow.py:1226` |
| live `len(wave_list)` instead of a cached `last` | `flow.py:1273` |
| `flow_batch`'s held loop → `_report_held` | `flow.py:1365` |
| `flow()`'s "this does not adopt; adoption lives on the shared path" note | `flow.py:389-394` |
| `max_passes` comment: it now also sizes the run pool | `config.py:293-300` |
| planner doctrine (role + runtime prompt) | `planner.md.jinja:162-176`, `leaves.py:581-590` |
| `docs/07-crosscutting.md`: adoption in §The split, the pool in §The iteration budget | `docs/07-crosscutting.md:243-268`, `:309-320` |
| `test_verify_base.py` hermetic env baseline (the v3 review accepted this as discharging an iteration carry-forward) | `template/tests/test_verify_base.py:23-42`, `:76-84` |

Deliberately **not** carried (sibling child's, per the brief's out-of-scope list):

* `_drive_and_act(adopt_seeds=…)` and `flow_ids`' seed branch — terminal-parent recovery.
* `cli._report_single`'s scoped rc leniency — single-id stdout reporting of adopted
  dispositions.
* Budget **re-sizing** on adoption (the pool here is sized once, off the pre-adoption
  schedule — the converged v3 mechanics the brief names).
* v3's `_children_of_split` wrapper and `_adoptable`'s `onward` chain-walk + the
  `examined` set + the `_deadline`/cycle test. Justification below.

## Two deviations from v3, and why

**1. `_children_of_split` folded into `_adoptable`.** In v3 the wrapper existed so "the
mid-wave splice and the already-terminal recovery **seed** cannot decide 'is this a split'
two ways" — its own docstring names the second caller, which this child does not ship. A
one-line wrapper with one caller whose stated reason is a function that isn't here would be
dead justification, so `_adoptable` now begins with `if not _is_split_parent(parent): return
[]` (`flow.py:860`). `_is_split_parent` stays a separate named predicate — the sibling needs
it in `flow_ids`, and the guard test asserts its behaviour.

**2. The `onward` chain-walk (`_adoptable` returning a second list, the work queue and the
`examined` set) is dropped.** Cost of keeping it, measured: `_adoptable` grows from `->
list[Path]` to `-> tuple[list[Path], list[Path]]` (+11 lines: the `onward` list, the
terminal-on-split branch, the second `sorted(...)`), `_adopt_split_children` grows a `while
queue_` loop + `examined` param (+8 lines), `_drive_and_act` grows an `examined: set[str]`
(+1), and the test module grows `_RunDidNotReturn` + `_deadline` + `_watch_examined` +
`_drive_to_complete` + the cycle test (**+95 lines**, measured against v3's
`test_flow_adopt_split.py:47-89`, `:335-355`, `:382-389`, `:1011-1049`). That is not the
deciding argument, though — the deciding argument is **reachability**: `onward` fires only
when a child *named in a lineage record* is itself already terminal on a split, and
`split.validate` refuses to create a child whose bundle already exists (`split.py:327-330`),
so within this child's scope (mid-run splits only) it is reachable **only** through a
hand-edited record. Its sole real consumer is the recovery walk ("500 → 601 already split →
adopt 701/702"), which is the sibling's `test_a_stale_chain_is_walked_through_its_terminal_
generation`. Shipping it here would be untested code carrying an untestable claim; without
it a hand-edited record naming a terminal-on-split child gets the ordinary reported skip
("NOT adopted: already terminal (COMPLETE)", `flow.py:899-900`) — a report, not a crash, and no
unbounded walk is even possible because there is no walk: `_adoptable` reads one record, one
level, per parent per wave. **Boundedness is preserved and still asserted**
(`test_an_adopted_child_that_splits_again_is_re_adopted_and_bounded`): the run-wide pool is
the recursion bound, which is what the brief's "bounded, no recursion reset" asks for.

## Rejected alternatives (with the cost, not an adjective)

* **Adopt in `flow_ids` (or in `flow()`) instead of `_drive_and_act`.** Rejected on the
  invariant, not on size: #468 made both CLI shapes share one drive path, and a second
  adoption site is the divergence #449 spent five iterations chasing. It also cannot work:
  outside `_drive_and_act` there is no `wave_list` to splice into and no run-scoped budget
  to spend, so the children would get a *fresh* `max_passes` each. Recorded as a docstring
  in `flow()` (`flow.py:389-394`) so the next reader does not re-propose it.
* **Announce `k + 1` instead of reading the wave back from the recomputed schedule.**
  Saves 4 lines (`wave_of`, `scheduled`, the `by_wave` grouping collapse) and is wrong
  whenever two children of one parent are ordered by `Depends on` — the default fixture
  case: 601 lands in wave 1 and 602 in wave 2
  (`test_cli_flow_drives_the_children_of_a_mid_run_split`).
* **Give each adopted wave a fresh `max_passes`** (drop `budget`, keep `_drive_wave`
  returning `None`): −14 production lines (`allowance`/`spent`/`budget`, the `spent >=
  budget` guard, `min(allowance, budget - spent)`, the four `return used`). Rejected because
  it hands a split the power to multiply what the operator allowed — `pdca flow 500
  --max-passes 3` would spend 5 (`test_the_pass_budget_is_one_cap_for_the_whole_run`
  measures exactly this: 3, not 5).
* **A disk sweep in `flow_ids`** (adopt anything in-flight after a Plan beat, as
  `flow_batch` does): fewer lines than the lineage read, and explicitly out of scope — the
  distinction between the id list and the CSV sweep is deliberate
  (`test_adoption_follows_the_lineage_edge_not_a_disk_sweep`).
* **Leaving the planner doctrine / `docs/07-crosscutting.md` alone** (−52 doc lines).
  Rejected: both currently assert "EVERY OTHER SHAPE … drives exactly the ids it was given
  and never looks for new ones" (`leaves.py:584-585`, `planner.md.jinja:169-171` on the base
  tree), which this patch makes **false**. A prompt that lies to the beat that owns the
  split decision is the #358 failure mode. The pre-existing tests that pin those texts
  (`test_split.py:1264`, `:1282`) still pass — the replacement keeps "csv", "flow 500 501"
  and "flow <child-ids>".

## Sizing versus the parent

|  | #469 v3 | this child |
|---|---|---|
| production `flow.py` | +407 / −18 | **+339 / −14** |
| `cli.py` | +10 / −1 | — |
| docs + prompts | +75 / −20 | +62 / −20 |
| test module | 1142 lines | **851 lines** |
| patch bytes | 113 473 | **87 804** |

## Verification

Run through the project's own runners (never a hand-rolled invocation):

* `./engine/scripts/run-verify.sh` (C4, with `PDCA_BUNDLE` / `PDCA_WORKTREE`) →
  **`C4 PASS: red without the fix, green with it`**; green leg 20 + 19 tests OK, red leg
  18/20 failures in `test_flow_adopt_split`.
* `./engine/scripts/run-suite.sh` (T3) → `== T3: root suite OK, driver suite OK`
  (offline driver suite: `Ran 1653 tests … OK (skipped=2)`).
* `./engine/scripts/run-docs-check.sh` (T2) → `lint_docs: OK`, `render_site: link audit OK`
  (the new `#the-split` / `#the-iteration-budget` cross-links resolve).

The target repo configures no formatter/linter (no pre-commit config, no ruff/flake8; CI is
docs-check, docs, render-check, require-linked-issue — the first and third are the T2/T3
gates above). Added lines are ≤ 95 characters, matching the surrounding style.

### The three refutation questions

**(a) Genuine red?** Yes — actually reverted and re-run, not assumed. With the production
hunks reverted (`git apply -R --exclude='template/tests/*'`, which is what the C4 gate
does), **18 of the 20 tests fail**. The two that stay green are deliberate:

* `test_a_run_that_adopts_nothing_keeps_a_full_budget_per_wave` is a **no-regression**
  test — it asserts the un-adopting run behaves exactly as before, so green pre-fix is its
  point. It binds by mutation: `budget = allowance * len(wave_list)` → `budget = allowance`
  makes it fail (verified).
* `test_an_unreadable_close_marker_never_kills_the_run` cannot be red pre-fix because
  pre-fix *nothing reads the marker*. It binds by mutation instead: removing the
  `try/except` from `_is_split_parent` (`flow.py:828-832`) makes it fail (verified).

Mutation evidence, each run through the suite (`cd template && PYTHONPATH=src python3 -m
unittest tests.test_flow_adopt_split`), each caught by exactly the intended test and no
other:

| mutation | result |
|---|---|
| `known=batch_names \| taken` → `known=batch_names` | 1 failure: `test_two_parents_splitting_in_one_wave_adopt_a_shared_child_once` (the brief's required mutation) |
| delete `batch_names \|= {c.name for c in scheduled}` | 1 failure: `test_a_child_adopted_earlier_is_not_re_adopted_by_a_later_parent` |
| delete the `try/except` in `_is_split_parent` | 1 failure: `test_an_unreadable_close_marker_never_kills_the_run` |
| `budget = allowance * len(wave_list)` → `budget = allowance` | 2 failures: `…keeps_a_full_budget_per_wave`, `…re_scheduled_tail_is_held_not_lost` |

**(b) Production path?** Yes. Every test drives `cli._flow` (`cli.py:558`) with a real
`argparse.Namespace`, which routes through the production `flow.flow_ids` →
`_drive_and_act` — the code this patch changes. Nothing is re-implemented: the fixture
builds the split with the **production** `split.accept` (`split.py:525`), so the close
marker, `split-lineage.json` and the child bundles are byte-for-byte what `pdca split
--accept` writes. The only patched functions are **pass-through spies** (`_build_all`,
`_drive_wave`, `_point_at_integration`, `flow.flow_ids`, `integrate.fold`) that record and
then call the real one and return its exact value — they observe, they do not substitute.
The leaves are the repo's own offline stubs (the `test_flow_slice.py:31-56` fixture shape),
which is how the whole driver suite runs headless.

**(c) Fixture includes the fault?** Yes — the failing element is present in every case, not
curated out. The split really happens *inside the run being measured* (the stubbed sign-off
records `iterate-plan`, the driver re-opens the bundle to UNPLANNED, the next pass's Plan
splits it — the documented Entry B), so the parent goes terminal mid-run with its children
PLANNED: exactly the #449/#469 defect. The guard fixtures inject the real fault rather than
avoiding it — a hand-edited `children` record holding `"../../etc"`, the same id twice, an
id the operator also named, a child brief with an unresolvable `Depends on: GHOST`, a
deleted `split-lineage.json`, a `close-disposition` written as non-UTF-8 bytes, a Do leaf
that raises every pass, a sign-off session nobody answers. The budget tests assert the
**observed pass count** (`self.passes`, incremented in the `_build_all` spy), so "the run
spent 3, not 5" is measured, not inferred.

## Known limits (for the human at sign-off)

* A run handed an id that is **already** terminal on a split still only prints the
  `pdca flow <child-ids>` hint — children stranded by an *earlier* run are the sibling
  child's scope, and the docs/prompt text here is worded to stay true of that
  (`docs/07-crosscutting.md:264-268`).
* An adopted child that is **held** (unschedulable) is excluded from the results map, so a
  run whose only unfinished work is a held child still exits 0. That is the contract the
  brief asks for; the hold itself is loud on stderr. Documented at the point of the
  decision (`flow.py:975-980`).
* A bundle that declared `Depends on <parent>` is levelled by its own edges and can share a
  wave with the children the parent decomposed into. Re-pointing such a dependent is a
  `waves` semantics change, deliberately out of scope (`flow.py:970-975`).

No external dependency beyond python3 ≥ 3.11 stdlib + git was needed; nothing to declare.
