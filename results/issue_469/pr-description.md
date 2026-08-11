## Summary

**User impact:** A split that happened *inside* a `pdca flow` run left its own
children undriven. The parent closed, `pdca split --accept` created the children
fully briefed, and the run walked away from them — so every split cost a manual
restart (`pdca flow <child-ids>`), and a run interrupted before that restart left
the children stranded with nothing but the lineage record pointing at them.

After this change the run that caused the split drives the children too: they are
spliced into the waves after their parent's, ordered by their own `Depends on` /
`Conflicts with`, published and folded like any other wave, and drawn from the same
`max_passes` budget the run started with. Naming a parent that is *already* terminal
on a split recovers its stranded children the same way, so an interrupted run is
resumed by re-running the id you first typed.

Reported in [#469](https://github.com/eduralph/pdca-harness/issues/469).

## What to look at

One module carries the change: `template/src/pdca_harness/flow.py` (detect →
validate → splice → report, plus the run-wide pass pool), with a two-line exit-code
scope fix in `template/src/pdca_harness/cli.py` and documentation/prompt updates that
previously told operators the opposite.

The shape of it: `_drive_and_act`'s wave list is no longer computed once and frozen.
After each wave drives, the bundles it drove are examined for a `close-disposition =
split`; the children named in the parent's `split-lineage.json` are filtered, the
un-driven remainder of the run is re-levelled together with them, and the result
replaces the waves after the current one. The ordinary loop picks the new tail up —
so an adopted child is pointed at the integration branch, driven, signed off,
published and folded by exactly the code every other wave goes through, not by a
second mechanism.

To try it: take a bundle whose sign-off you answer `iterate-plan`, let the re-plan
split it, and watch the run continue into the children (`flow: issue_500 split →
adopted children issue_601 into wave 1`). Then interrupt a run mid-split and re-run
`pdca flow <parent-id>`: the parent reports as terminal and its stranded children are
adopted and driven.

## Root cause

The drive set was frozen at two points, and both are older than the split feature:
`flow_ids` built its bundle list once from the ids it was given, and `_drive_and_act`
called `waves.compute_waves` once at the top. Work that came into existence *during*
the run — which is exactly what a split produces — could not enter either. Nothing
was wrong with the split itself: it wrote the children, the lineage record and the
close marker correctly, and then the run had no way to hear about them.

## Fix

- **Detect** — after a wave drives, each bundle in it is tested for terminal *and*
  `close-disposition = split` (both halves: `split.accept` writes the marker, but the
  human confirms the decomposition at sign-off, so a parent still AWAITING_SIGNOFF is
  a split nobody has accepted yet). An unreadable marker means "not a split", never a
  crash — the probe runs over ids the operator merely named, outside any isolation.
- **Validate** — the children come from `split.read_lineage`, then are filtered
  exactly as `flow_ids` filters an explicitly named id: no brief, already terminal,
  already in this run's drive set, listed twice, or resolving outside the bundle root
  (a hand-editable record must not build a path out of `results/`). Every skip is
  reported. A terminal child that split in *its* turn is walked through, so a chain an
  earlier run abandoned part-way hands over the descendants that are actually stranded.
- **Splice** — the un-driven remainder plus the children go through
  `waves.partition_schedulable` + `compute_waves`, and the result replaces
  `wave_list[k+1:]`. A child whose declared dependency cannot be resolved is held with
  its reason in the existing "held this run — …; left in-flight" shape, excluded from
  the results map, and the run carries on. A split must never abort the flow that
  caused it.
- **Budget** — `max_passes` keeps its per-wave meaning and additionally sizes a
  run-wide pool (`max_passes` × the waves the run *set out to* drive), spent down by
  every wave including adopted ones. A run that adopts nothing cannot reach that pool,
  so it behaves exactly as before; a run whose drive set grows cannot multiply what
  the operator allowed. Running the pool out stops the run and names what it left.
- **Report** — the announced wave index is read back from the recomputed schedule
  (two children of one parent routinely land in different waves), and both CLI shapes
  produce the same child states, announcements and exit code because both reach the
  one drive path.
- **Exit code** — `_report_single`'s "an AWAITING_SIGNOFF single-id run is not a
  failure" leniency is scoped to the id the operator typed. Adoption is the first
  thing to put bundles nobody typed into that map, and map-wide leniency reported rc 0
  with an adopted child sitting unfinished.

Out of scope, deliberately: why recursive splits happen, `waves` scheduling semantics
(reused as is — including that a bundle declaring `Depends on <parent>` is levelled by
its own edges and not re-pointed at the children), the split command and lineage
schema, and the `--accept` hint that prints `pdca flow <child-ids>` (still right for a
split accepted outside a running flow).

## Verification

- **Claim:** a split inside a run drives that run's children to a terminal state in a
  later wave, honouring their own ordering, on one run-wide budget, announced with
  their real wave index. **Test:**
  `template/tests/test_flow_adopt_split.py` (new, 26 tests) — every one drives through
  `cli._flow`, and the split itself is performed by the production `split.accept`, so
  the marker, the lineage record and the child bundles are byte-for-byte what `pdca
  split --accept` writes.
- **Claim:** a run handed an id already terminal on a split adopts its stranded
  children. **Test:** `test_cli_flow_recovers_children_stranded_by_an_earlier_run`,
  and `test_a_stale_chain_is_walked_through_its_terminal_generation` for a chain
  abandoned two generations deep.
- **Claim:** both CLI shapes agree on the same bytes. **Test:**
  `test_both_cli_shapes_adopt_identically_on_the_same_bytes`,
  `test_a_refused_adopted_wave_exits_1_at_either_arity`,
  `test_an_adopted_child_left_unfinished_exits_1_at_either_arity` (each runs the two
  shapes against byte-identical copies of one instance root).
- **Claim:** the pool is one cap for the whole run, on every exit. **Tests:**
  `test_the_pass_budget_is_one_cap_for_the_whole_run`,
  `test_an_adopted_wave_only_gets_what_is_left_of_the_run_budget`,
  `test_a_wave_that_runs_its_allowance_out_still_charges_the_run_pool`,
  `test_a_wave_that_stalls_charges_the_run_pool_for_what_it_spent`, and
  `test_a_run_that_adopts_nothing_keeps_a_full_budget_per_wave` for the
  no-regression side.
- **Claim:** the guards hold. **Tests:** a split-marked but non-terminal parent is not
  adopted from; a lineage id escaping the bundle root is skipped with a report; a
  child listed twice is adopted once; a child already in the drive set — named by the
  operator, or adopted by an earlier wave — is not adopted twice; a lineage cycle
  terminates (asserted with a watchdog, since the unbounded version simply never
  returns); an unreadable close marker never kills the run.
- **Red→green:** with the production hunks reverted and the tests kept, 23 of the 26
  fail; with them applied, 26/26 pass. The three that pass on both legs are the
  no-regression guards, whose contract is that nothing changed.
- **Suites:** offline driver suite green at 1,659 tests; the template render and
  `copier update` compatibility suites green at 7 tests with copier actually installed
  (no self-skips); docs lint and the 22-page site render/link audit green.

Fixes #469
