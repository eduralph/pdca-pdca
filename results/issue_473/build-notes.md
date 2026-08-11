# Build notes — issue 473, iteration 4 (flow-adopt-recovery-reporting)

## Where this is built and what the citations mean

`$PDCA_WORKTREE` = `/home/eddie/pdca/pdca-harness.pdca-wt`, `HEAD` = `063203a
"pdca-integrate: issue_472"` — child-1's accepted adoption core folded onto `3e3b829`
(PR #470, the #468 unified drive path). Every `path:line` below is **that tree with this
patch applied**. Independent checks that the diff is a real patch against that base, not
just the state of my editor:

* `git archive HEAD | tar -x -C /tmp/base473 && git apply --check patch.diff` in the clean
  extract → **applies cleanly to 063203a**;
* the C4 gate's own revert/re-apply cycle round-trips (`engine/scripts/run-verify.sh`
  reverts the production hunks, runs, then restores).

## The three changes, and the one place each defect lives

### (1) Recovery — `flow.py:1773-1786` (`flow_ids`) + `flow.py:1471-1481` (`_drive_and_act`)

The pre-run terminal filter still skips a terminal bundle and still prints #468's
non-destructive hint (`flow.py:1765-1772`, untouched) — a terminal bundle has nothing to
build, and `_terminal_hint` is the one shared recovery advice both CLI shapes reach. What is
new is `flow.py:1773-1786`: when `_is_split_parent(d)` (the core's own predicate,
`flow.py:876`) holds, the id is appended to `seeds` and the run says so on stderr, qualifying
the hint rather than replacing it. `flow_ids` threads `seeds` into `_drive_and_act`'s new
`adopt_seeds` keyword (`flow.py:1792`); inside, `flow.py:1472` calls **the core's own**
`_adopt_split_children` once with `k=-1`, so `wave_list[k+1:]` is the whole schedule and the
seed's children are levelled in front of it — same detect (`_adoptable`), same guards
(`_PLAIN_ID`, `_inside_bundle_root`, alias dedup, `known`), same `_reschedule` tolerance,
same announcements, same results-map semantics. Recovery is a **use** of the adoption path,
not a second mechanism beside it; that is what makes the parity criterion hold structurally
rather than by two implementations being kept in step (the #449 failure mode).

Transitivity needed one addition. A child that is itself terminal **on a split** cannot be
driven, but is the only route to a generation an earlier run stranded below it (500 → 601 →
701 with 601 already split). `_adoptable` now returns a **pair** — `(drivable,
walk_through)` (`flow.py:902-903`, `flow.py:1034-1044`) — and `_adopt_split_children` drains
it as a breadth-first work queue with an `examined` set (`flow.py:1205-1218`), so the walk
re-enters the same reader under that child's name (its grandchildren attributed to the
parent that declared them) and a hand-edited record naming an ancestor drains instead of
spinning.

*Why a pair rather than an out-parameter list* (the shape iteration-3 used): `_adoptable` is
called through `_isolate`, whose contract is "returns None iff the read raised". With an
`onward` list mutated in place, a raise half-way leaves entries appended for a parent that
contributed nothing; with a returned pair, `got or ([], [])` (`flow.py:1216`) discards both
halves together. Same size (the out-param version is 2 lines shorter in the signature and 2
longer at the call), better contract.

### (2) Budget — `flow.py:1271` (`_pass_pool`) + `flow.py:1492`

The cause is arithmetic done before the waves it has to fund exist: `budget = allowance *
len(wave_list)` evaluated **once, before the loop**, while every splice grows `wave_list`.
`_pass_pool` names the rule and the pool is now read **off the live `wave_list` at each
wave** (`flow.py:1492`) — which is exactly "recomputed at splice", since a splice is the only
thing that changes that list. One assignment, one call site.

Rejected alternative — iteration 3's shape: keep a `budget` variable and re-assign it
`max(budget, _pass_pool(...))` after **each** splice. Concretely that is 3 sites (initial
sizing before the loop, after the seed splice, after the mid-run splice) plus the `max`
guard against a splice that *shrinks* the schedule, versus **1 site** here. I checked the
`max` is not load-bearing: after driving `k` waves `spent ≤ k·allowance`, and a live
`wave_list` at index `k` always holds at least `k+1` waves, so `_pass_pool ≥ (k+1)·allowance
> spent` — the pool cannot retract below what a run has spent, with or without `max`. The
two are behaviourally identical for `allowance ≥ 1` (they differ only in the number printed
in a message that cannot fire); the live read is smaller and states the invariant where it
is used.

The bound the brief asks to retain is retained, and is asserted, not asserted-about:
`_drive_wave`'s own per-wave cap (`min(allowance, budget - spent)`, `flow.py:1535-1536`),
`spent` never reset anywhere, and the admission rule `if spent >= budget` kept live at
`flow.py:1493`. What actually terminates a chain of splits is that **adoption** is finite —
a bundle adopted once (`known`), a candidate examined once (`examined`), every child a
bundle already on disk (`flow.py:1154-1164`) — so the schedule the pool funds cannot grow
forever. Total spend is bounded by `allowance × final wave count`.

I want to be honest about a consequence: with the pool covering the live schedule, the
admission rule can no longer fire for `allowance ≥ 1` (proof above), so `spent` is now an
accounting quantity rather than a binding one. I kept the rule and pinned it at the one
input that still reaches it, `allowance = 0`
(`test_no_wave_opens_on_budget_the_pool_does_not_hold`), rather than delete it: deleting it
would make the pool unrepresented in code, and the invariant "no wave opens on budget the
pool does not hold" must still hold if a future wave came to spend more than it was handed.
That is a deliberate call the human may want to look at — it is the Plan decision (re-size
over named-first service) followed to its end.

### (3) Stdout — `cli.py:644` (`_report_entry`) + `cli.py:688-691` (`_report_single`)

`_report_single` printed one line for `iid` and derived the rc from the whole map, so an
adopted child could make the rc non-zero while stdout said `COMPLETE`. Now **one shape for
every entry the map answers for**: `_report_entry` prints the documented `state<TAB>path`
line plus the §6 listing for an `AWAITING_SIGNOFF` bundle, and `_report_single` calls it for
the named id first (so `out.startswith(f"{state}\t{d}\n")` — pinned by
`test_flow_entrypoint_parity.py:414` — still holds) and then for every other entry, sorted.

*Why unconditionally, where iteration 3 printed extra lines only when `rc != 0`.* The
rc-gated version leaves a hole the criterion's own words cover ("never reports success it
did not deliver"): a single-id run counts `AWAITING_SIGNOFF` as a successful end (#468), so
a recovery whose adopted child halts for the human exits **0** — and stdout would say
`COMPLETE`, about a bundle an *earlier* run finished, while the work this run actually did
sits waiting for a sign-off nothing named. `test_stdout_names_an_adopted_child_left_waiting
_for_the_human` is that case, and it is red against the rc-gated shape as well as against
the base — **checked, not assumed**: I swapped the rc-gated body into `_report_single`,
re-ran the module, and got 4 failures (that case plus the three full-stdout ones), then
restored. Cost of the difference: 4 added lines vs 6. No pre-existing shape changes —
`flow_ids` answers for exactly the ids it was given, so a second map entry can only come
from an adoption (pinned by `test_a_single_id_run_that_adopts_nothing_still_prints_exactly
_one_line`).

### Documentation kept true, not decorated

`docs/07-crosscutting.md:259-271` (recovery), `:274-278` (what bounds adoption), `:289-297`
(the stdout rule), `:344-353` (the iteration budget) and `template/agents/planner.md.jinja:
170-181` all *asserted the old rule* — "children … draw from what their parent's schedule
was allowed, so a split can never quietly multiply the budget", "a parent an earlier run
already closed, whose children a later run does not yet pick up on its own". Left alone they
would be false statements about the shipped behaviour, in the two places an operator and the
planner leaf read it from. `run-docs-check.sh` (T2) is green: `lint_docs: OK`, 22 pages
rendered, `link audit OK`.

**Flag for the human:** `template/agents/` is a project-defined human-only class
(`docs/INTEGRATION.md` §4 — "changes to … the agent role prompts … process/prompt judgment
no deterministic gate can score"), so the planner-prompt hunk is expected to raise a §6 row.
I considered dropping it to keep §6 clean and decided against: the bullet it replaces states
the budget rule this bundle changes, and shipping a prompt that tells planners "a big split
can exhaust it" when the pool is now re-sized is a defect, not a smaller diff. The hunk is 14
lines and touches only the two bullets that became false plus one new bullet for recovery.

## Tests — `template/tests/test_flow_adopt_recovery.py` (14 cases, new)

Every case drives **`cli._flow`** (never a hand-picked `flow.*` call), builds its fixture
with the production `split.accept`, and carries the "an earlier run stranded these" state to
COMPLETE with the production `flow._drive_wave` — so the disk a recovery run starts from is
what a real interrupted run leaves, written by production code. Modules are imported, never
new symbols (a `from pdca_harness.flow import _pass_pool` would be ImportError → exit 77 on
the red leg, not red).

Coverage by criterion: recovery (`…drives_its_children`,
`…walks_through_a_generation_an_earlier_run_already_split`,
`…lineage_cycle_is_examined_once…`, `…nothing_left_to_adopt_is_a_clean_no_op`,
`…seed_is_re_levelled_together_with_the_ids_named_beside_it`,
`…mid_run_and_recovery_shapes_agree_on_equivalent_disk`); budget
(`…not_starved_by_a_wave_adoption_added` — the v3 adversary's exact scenario,
`…recovery_run_funds_every_wave…`, `…no_more_than_the_operators_allowance`,
`…no_wave_opens_on_budget_the_pool_does_not_hold`); stdout
(`…names_the_adopted_bundle_that_failed_the_run`,
`…never_reports_an_earlier_runs_success_as_its_own`,
`…names_an_adopted_child_left_waiting_for_the_human`, `…adopts_nothing_still_prints_exactly
_one_line`).

`…seed_is_re_levelled_together_with_the_ids_named_beside_it` closes a gap I found in the
iteration-3 suite: every other recovery case has an **empty** drive set, so nothing
exercised the `k=-1` splice against a non-empty `remaining` (a seed named beside an ordinary
id, whose `Conflicts with` must still orient the waves).

### Five child-1 tests rewritten, deliberately

`template/tests/test_flow_adopt_split.py` pinned the *old* pool rule, which the brief's Plan
decision replaces (Scope (2)). The rewrites keep every bound assertion and move only the
starved outcomes: `…is_capped_at_one_allowance_like_any_other` (a wave gets one allowance
and stops — the retained cap), `…does_not_starve_the_one_it_created`,
`…stalls_is_charged_and_the_adopted_wave_still_runs` (both still assert the un-finished wave
is charged and named, and that the run still exits 1 on un-terminal work),
`…splits_again_is_re_adopted_and_bounded` (bound re-expressed as "terminates having adopted
each bundle exactly once", with the exact adoption list),
`…every_wave_the_run_grows_into_is_funded_at_the_allowance`. `…adopts_nothing_keeps_a_full
_budget_per_wave` needed no change and still passes — the no-adoption regression pin.

## Before declaring done — the three forced questions

**(a) Genuine red?** Yes, established by the project's own gate, not by hand:
`PDCA_BUNDLE=… PDCA_WORKTREE=… ./engine/scripts/run-verify.sh` → `C4 PASS: red without the
fix, green with it`. Green leg 14/14 + 27/27 `OK`; red leg (production hunks reverted, tests
kept) **12 of 14** recovery cases fail and 5 of 27 adoption cases fail, no import error and
no "0 tests ran". The two recovery cases that stay green on the red leg are the deliberate
no-op pins (`…adopts_nothing_still_prints_exactly_one_line`,
`…no_wave_opens_on_budget_the_pool_does_not_hold`). The red-leg symptoms are the ones the
brief names: `AssertionError: 'PLANNED' != 'COMPLETE'` for `810` in the starvation case (the
adversary's reproduction), children left PLANNED in every recovery case, and one stdout line
where three are expected.

**(b) Production path?** Yes. The tests call `cli._flow(cfg, args)` — the real CLI entry —
which reaches the real `flow.flow_ids` → `_drive_and_act` → `_adopt_split_children` →
`_adoptable` → `_reschedule`, and the real `cli._report_single`. The only substitutions are
the six **model leaves** (stubbed, as the whole offline suite is) and two pass-through spies
(`flow._build_all`, `flow._drive_wave`) that call the production function and hand its exact
return value back — they count passes and record wave membership, they do not stand in for
anything. Fixtures are built with the production `split.accept` (`split.py:525`), so the
close marker, `split-lineage.json` and the child bundles are byte-for-byte what `pdca split
--accept` writes.

**(c) Fixture includes the fault?** Yes. `_strand_a_split` *creates* the fault on disk before
the run and asserts it: parent COMPLETE, its `close-disposition` file reading `split`, every
child PLANNED. The transitive case additionally splits and closes 601 so the fixture contains
the already-closed generation the walk has to pass through; the failure cases inject a real
`RuntimeError` in the Do leaf for the child under test (every other bundle builds normally);
the starvation case uses the operator-typed id `810` that the defect starves, rather than
observing only the adopted child. Nothing is curated out — the parity test compares a
mid-run leg and a recovery leg on equivalent disk with the *same* injected failure, and the
mid-run expectations are written out in full so the comparison cannot pass by comparing two
empty lists.

## Gate runs (all through the project's own scripts, from the instance root)

| Gate | Command | Result |
|---|---|---|
| C4 | `./engine/scripts/run-verify.sh` | `C4 PASS: red without the fix, green with it` |
| T2 | `./engine/scripts/run-docs-check.sh` | `lint_docs: OK`; `render_site: link audit OK` (22 pages) |
| T3 | `./engine/scripts/run-suite.sh` | `== T3: root suite OK, driver suite OK` |
| — | `cd template && PYTHONPATH=src python3 -m unittest discover -s tests` | `Ran 1674 tests … OK (skipped=2)` (2 pre-existing, unrelated) |

### On the iteration-3 carry-forward (T3 / copier) — evidence, not a workaround

Round 3 was rejected partly on *"`copier` is unavailable, so all 7 root compatibility tests
skipped"*. That is a limitation of the **reviewer's** sandbox, not of this instance: the
required doctor row `copier importable (.venv)` (`pdca.toml:819-824`) passes here —
`.venv/bin/python3 -c 'import copier'` → copier **9.17.0** — and the T3 gate uses that
interpreter. I re-ran it and captured the detail: the root suite ran **7 tests, all `ok`,
none skipped** (`test_render_then_slice`, `test_namespaced_cli_name_reaches_every_rendered
_command`, and the five `UpdateCompat` cases including `test_merged_config_still_loads` and
`test_no_model_work_is_newly_enabled`), in 22.2s. So the render/`copier update` compatibility
of this patch — which matters because it touches `template/agents/planner.md.jinja` — is
genuinely exercised, and a human can reproduce it with
`PDCA_WORKTREE=… ./engine/scripts/run-suite.sh`. No external dependency is missing, so there
is no NEEDS-HUMAN dependency declaration to make; what remains for the human is only to
accept the evidence.

The other round-3 row (T4: the PR body / commit message the checker lints are drafted by
**publish**, after sign-off, so they do not exist at Check for any bundle —
`cli.py:1075-1083` says so in the target's own code) is by design and not addressable from
Do without writing publish's artifacts, which the STOP discipline forbids. The novelty half I
*can* answer, and re-ran on this base: `git log --all -S "adopt_seeds" -- template/src/
pdca_harness/flow.py` → no commit in any ref; `git log --all -- template/tests/test_flow
_adopt_recovery.py` → empty; the only prior adoption commit on `flow.py` is `96c9704`
(child-1 / #472), folded here as `063203a`. No duplicate or prior art for this slice.

## What I did not do

* No change to `waves.compute_waves` / `partition_schedulable`, `split.accept`, the lineage
  schema, `flow_ids`' id list (no disk sweep), or the affirmed policy that a **held** child
  is excluded from the results map and compatible with rc 0.
* No change to the rc rule itself (`_results_rc`): a single-id run still counts
  `AWAITING_SIGNOFF` as a successful end. Criterion (3) is about stdout not disagreeing with
  the rc, and the fix makes stdout complete rather than re-deciding the rc.
* No PR pushed, opened, marked ready or merged.
