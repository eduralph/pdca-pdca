# Build notes — issue 412 / merge-mode-atomic-merge-group (iteration 2)

Target: `eduralph/pdca-harness @ main`, worktree base `a6af7f3`. Every `path:line` below is on
the patched tree unless it says "base". Paths are under `template/src/pdca_harness/` unless
they start with `docs/` or `template/`.

I started from iteration 1's patch (`iteration-v1/patch.diff`), which applies cleanly to the
same base, and fixed each finding in the carry-forward. The design is unchanged: the field,
the up-front refusals, the hold and release at the wave boundary, the dependents' hold. What
changed is how the hold survives the rest of the run.

## The carry-forward, finding by finding

### 1. A group wholly in the final wave said nothing (C5)

Cause: the end-of-run report (`_report_group_holds` in iteration 1) only looked at members a
boundary had held. A group whose members all finish in the final wave is never held, because
`merge_wave` is only called for non-final waves (`flow.py:3127`), so the run printed nothing.

Fix: `flow._report_groups` (`flow.py:3244`) now walks every group of the run, not the held
set. A group is reported when a member is COMPLETE with a patch and was not merged by the run
(`merge_wave` now records what it merged in `landed`, `merge.py:186`; the run keeps that in
`group_landed`, `flow.py:2957`). One line per group, members in merge order (wave, then name),
with one of three reasons:

- something blocks it: a member is not COMPLETE ("issue_B is DISCONTINUED"), or a member's
  record merge mode refuses ("issue_B has no recorded PR …");
- it landed in part: some members merged, others not;
- nothing blocks it, but no boundary merged it: the final-wave case. The line ends "Merge its
  PRs together, back to back, in this order: issue_A, issue_B."

It is called only in merge mode with publishing on (`flow.py:3214-3217`).

Exit code: a group wholly in the final wave is **not** a hold. Nothing was held: its PRs are
drafts, as every final-wave PR in merge mode is, so the run did exactly what it would have
done without the field. It exits 0 and the stderr line carries the instruction. A member a
boundary did hold (it would have merged there otherwise) stays a `"group"` hold and gives
exit 3, as in iteration 1 (`flow.py:3239`). This is written down in the `holds` docstring
(`flow.py:2803-2807`) and in `docs/07-crosscutting.md:903-905`. If the maintainer wants 3
for the final-wave case too, it is about three lines: have `_report_groups` return the
members it names, and add them to `holds` as `"group"`.

Test: `test_a_group_wholly_in_the_final_wave_is_named_for_the_human`
(`template/tests/test_merge_group.py:378`), the independent A/B case the reviewer ran.

### 2. A split before the group's last member broke the group

Cause: after a split, `_adopt_split_children` re-levels only the un-driven tail
(`flow.py:2392-2394`). The merge-mode group check in `waves.partition_schedulable` then saw
A (already driven, held as a draft) as "not in this run's batch" and held B and C.
`compute_waves` → `check_dep_graph` on the same tail would have raised the same refusal.

Fix: a keyword `in_run` (bundle names of the run that are not in the list being levelled)
through the four functions on that path:

- `flow._reschedule` (`flow.py:2181`) passes it to `waves.partition_schedulable`
  (`flow.py:2198`) and `waves.compute_waves` (`flow.py:2203`);
- `_adopt_split_children` passes the run's drive set, `batch_names` (`flow.py:2394`);
- `compute_waves` hands it to `check_dep_graph` (`waves.py:354`), which counts it, with
  `offered`, as in the batch for the group check only (`waves.py:151`);
- the per-group check moved into `waves._group_refusal` (`waves.py:283`), which takes the
  scheduled names and the `known` names (scheduled + `in_run`) separately: only a member
  outside `known` is "outside".

Why `batch_names` and not `accepted` (the reviewer's first suggestion): the outside rule
asks "can this run merge that member at all". Any bundle in the drive set can be, if it
completes. A driven member that did not complete (DISCONTINUED) is handled at the boundary,
with that reason. Counting only `accepted` would refuse such a group as "outside", with the
wrong reason.

`offered` (a recovery seed's children) now counts as in the batch for the group check too
(`waves.py:151`). Before, a named bundle declaring `Merges with` a child the seed splice was
about to adopt was refused as outside. The seed splice then levels both together, with the
same `partition_schedulable` rules. This one is not covered by a test of its own: it needs
a recovery-seed fixture, and the change is the `set(offered) |` on that one line.

Test: `test_a_split_before_the_last_member_does_not_break_the_group` (`:276`) is fixture (a)
plus a wave-0 bundle S that splits into S1 through the production `split.accept`. Before the
fix: "issue_B held this run — … names issue_A, which is not in this run's batch", and B and C
were never built. After: S1 is adopted into wave 1, and A and B still merge together at wave
1's boundary, A first, before C builds.

### 3. A member with no recorded PR (or an `Onto branch` record) half-landed the group

Cause: once every member was COMPLETE, `merge_wave` merged them one at a time. `_merge_one`
then refused the later member on its own record (no `pr_url`, base `merge.py:475-478`; a
`"stacked"` record, base `:486-494`; no repo under `merge_requires != "required"`, base
`:543-545`), after the earlier one had already merged.

Fix: `merge.group_blocker` (`merge.py:191`) decides, for the whole group, before the first
`gh` call, whether it can all merge now:

1. a member that ended without completing (DISCONTINUED, RESOLVED) → blocked for good;
2. a member still in flight → waiting (the iteration-1 hold);
3. otherwise, outside a dry run, `merge._unmergeable` (`merge.py:216`) asks each member's
   record the same three questions `_merge_one` asks before readying it.

If anything blocks, every member is held (`merge.py:156-167`): no `gh pr ready`, no
`gh pr merge`, one line per member, the first time only. The run goes on. Its dependents are
held by `_runnable` as before, and the end-of-run line names the reason.

`cfg.expected_checks_error` is not part of the check. It refuses every PR alike, and
`_merge_one` refuses it before readying the group's first member, so nothing of the group
lands. The guard test `test_a_malformed_expected_checks_refuses_the_group_before_any_member_is_readied`
(`:360`) shows this. It passes with or without the fix, by design: it is not a red→green case.

Tests: `test_a_member_without_a_recorded_pr_holds_the_whole_group` (`:348`) and
`test_a_member_with_an_onto_branch_record_holds_the_whole_group` (`:355`).

### 4. One-sided declarations got lost once the declaring bundle dropped out

Two paths, both fixed.

**The sweep.** `flow_batch` replaces its bundles with `partition_schedulable`'s survivors (base
`flow.py:3327`), and the relation was read off the survivors only. Fix: `partition_schedulable`
now reads the relation off every bundle it was given, held ones included
(`waves.py:507`). It holds a group whole when one of its members is held for any reason
("its `Merges with` group cannot land together this run: issue_X is held too",
`waves.py:520`), or when `_group_refusal` refuses it. Then it holds their dependents, and
repeats until a round holds nothing new (`waves.py:509-533`). Test:
`test_the_sweep_holds_the_partner_of_a_held_bundle_that_declared_the_group` (`:492`). X
declares `Merges with: A` one-sided and is held for an unresolvable dependency. Before the
fix, A was built and merged alone at wave 0's boundary.

**The run.** A split child adopted earlier that a later re-levelling holds is taken back out
of `bundles` (base `flow.py:2403`). If it was the only side declaring the group, its partner
then merged alone at the next boundary. Fix: `_drive_and_act` keeps `group_pool`, every
bundle the run has had in its drive set (`flow.py:2958`), grown right after each splice
(`flow.py:3079`). The relation is read off it (`_groups`, `flow.py:2960`) at the boundary
(`flow.py:3137`), for `_runnable` (`flow.py:2977`) and for the end report (`flow.py:3216`).
Test: `test_a_split_child_dropped_later_still_holds_the_member_it_declared` (`:512`). T
splits into T1 (`Merges with: A`, `Depends on: P`). P is DISCONTINUED in wave 1, where U
splits too, so that re-levelling holds and drops T1. A stays held, and the end line says
"issue_T1 is PLANNED".

### 5. Test gaps

All three named gaps now have a case: the split (finding 2), the one-sided declaration from a
held bundle (finding 4, both paths), and a release where a later member has no PR (finding
3). Plus the final-wave case (finding 1).

## Two existing tests changed (stand-ins for a function whose signature grew)

`tests/test_flow_adopt_split.py:1260` and `tests/test_flow_single_driver.py:285` swap in a
stand-in for `waves.partition_schedulable` that took exactly `(cfg, bundles)`. With
`in_run=` added, the call raised `TypeError` inside the stand-in. `_reschedule` caught it and
the run went the same way, but the first test no longer saw its own fault injected (it
asserts `len(raised) == 1`), and the second passed for the wrong exception. Both stand-ins
now take and pass on `**kw`.

Ruled out: passing `in_run` only in merge mode so that stack mode's call stays two
arguments:

```python
extra = {"in_run": in_run} if cfg.wave_mode == "merge" else {}
schedulable, held = waves.partition_schedulable(cfg, remaining, **extra)
...
return waves.compute_waves(cfg, schedulable, **extra) if schedulable else []
```

That is three production lines shaped around two test stand-ins, against two changed lines
in the tests. `in_run` has no effect in stack mode anyway: the relation is empty there
(`waves.py:507`) and `check_dep_graph` checks groups only in merge mode (`waves.py:150`).

## Other choices, and what I ruled out

- **Hold, not STOP, for a member whose record merge mode refuses.** STOP would cost nothing
  in code (refuse before the first merge with `_merge_one`'s own message, and return 1).
  But the brief's hold semantics, leg (b), and the reviewer's fix direction ("hold the whole
  group instead") all say hold, and the hold already protects what STOP protects: the
  group's dependents are not built on a base without it. A non-group bundle with no PR still
  STOPs the run, as before. Exit code: such members are `"group"` holds, so exit 3 when
  everything else finished. That matches stack mode's #593, where a COMPLETE bundle whose
  publish pushed no branch is held with exit 3.
- **Record check skipped in a dry run** (`merge.py:210-211`). A dry run merges nothing, so
  it cannot half-land, and a stub publisher writes no `publish.json`. With the check on, every
  group in a dry run would read "has no recorded PR" and be held, a rehearsal of something a
  real run would not do. Without it, `_merge_one` refuses the missing record as it always
  has in a dry run. The waiting hold still applies in a dry run, as in iteration 1.
- **Hold line printed once per member** (`merge.py:158`). I tried printing it again when the
  reason changed. In leg (b) that gives a second "issue_B (DISCONTINUED) …" line right before
  the end-of-run line that says the same. Once at the first hold, plus the end line with the
  reason as it then stands, is enough.
- **`_merge_one` not rewritten to call `_unmergeable`.** Its three refusals each print their
  own message, which `tests/test_merge.py` and `tests/test_merge_onto_branch.py` assert on.
  Routing them through the helper means mapping each reason back to its message: about 15
  lines changed in `_merge_one` for no change in behaviour. The `_unmergeable` docstring names
  the checks it mirrors, so a new local refusal in `_merge_one` has an obvious second place
  to go.
- **No second check at merge time for an outside member.** Keeping outside members in
  `merge_groups` and holding on them in `merge_wave` would also hold a group whose earlier
  member was legitimately merged at an earlier boundary (it is not in a later call's list).
  Telling "outside" from "already merged" would need the run's merged set passed in too. The
  three refusal layers (`check_dep_graph` for `pdca flow <ids>`, `partition_schedulable` for
  the sweep, the same with `in_run` after a split) keep outside members out of a run.

## Known limits (not changed in this iteration)

- **Resume with a finished member.** `pdca flow A B` after a run that left A COMPLETE as a
  draft: `flow_ids` skips A as terminal, so B's group names a bundle outside the batch and the
  run refuses with "add A to this run's ids", although A was named. Merge mode cannot merge a
  member it did not build (`merge_wave` only sees `accepted`), so the refusal itself is right;
  only the remedy reads wrong. Iteration 1 made the same call. A better message needs
  `check_dep_graph` to know the finished named ids. Left for a follow-up.
- **A chain through a member the run already drove, introduced by a split child** (a child
  that declares both `Merges with: A` and `Depends on: A`). The re-levelling sees only the
  tail's edges, so it does not refuse this. At its wave, `_runnable` holds the child (A is
  held for its group), so A stays held and the end line names the child as PLANNED. The run
  fails closed: nothing lands in part.
- **A split child joining a group after the rest merged.** Reported as "landed only in part".
  Making `pdca split` respect groups is out of scope per the brief.

## Open question carried from the brief (maintainer)

The motivating wyrd pairs are chained. This design refuses them in merge mode (make them one
bundle, or use stack mode). Built as written; alternative A (build the consumer on the
producer's unmerged branch) is not attempted.

## Test — `template/tests/test_merge_group.py` (18 cases)

Imports only modules (`cli, flow, leaves, merge, publish, signoff, split, state, waves`),
never a new symbol. Real `flow._drive_and_act` / `flow.flow_batch` / `cli.main`, real
`merge.merge_wave` → `_merge_one` → `merged.is_merged`, real `split.accept` →
`_adopt_split_children` → `_reschedule`. Stubbed: the build/sign-off leaf (`flow._drive_wave`
writes a patch, signs off, writes `publish.json` unless told not to, or splits the bundle),
`flow._publish_bundle`, `publish.draft_texts`, `leaves.do_plan_batch`, `merge._sleep`, and `gh`
(a recorder in front of `subprocess.run`; every non-`gh` call runs for real). The publisher
mode is `command`, so this is not a dry run.

| Leg / finding | Test |
|---|---|
| (a) | `test_a_group_member_is_held_until_the_group_completes_then_merged_with_it` |
| (b) | `test_a_member_that_ends_discontinued_leaves_the_rest_unmerged` |
| (c) | `test_a_bundle_depending_on_a_held_member_is_not_built` |
| (d) | `test_a_chained_group_is_refused_before_any_do` (`cli.main`, rc 2, `Ways out:`) |
| (e) | `test_the_chained_group_runs_as_today_in_stack_mode` (guard, green both legs) |
| (f) | `test_merges_with_declared_on_one_side_binds_both` |
| (g) | `test_a_group_whose_members_conflict_is_refused_before_any_do`, `test_a_group_naming_an_id_outside_the_batch_is_refused_before_any_do` |
| finding 1 | `test_a_group_wholly_in_the_final_wave_is_named_for_the_human`, `test_a_group_whose_last_member_completes_in_the_final_wave_stays_all_draft` |
| finding 2 | `test_a_split_before_the_last_member_does_not_break_the_group` |
| finding 3 | `test_a_member_without_a_recorded_pr_holds_the_whole_group`, `test_a_member_with_an_onto_branch_record_holds_the_whole_group`, `test_a_malformed_expected_checks_refuses_the_group_before_any_member_is_readied` (guard) |
| finding 4 | `test_the_sweep_holds_the_partner_of_a_held_bundle_that_declared_the_group`, `test_a_split_child_dropped_later_still_holds_the_member_it_declared` |
| host refusal | `test_a_member_refused_after_another_merged_names_what_landed` |
| sweep refusal | `test_the_sweep_holds_a_refused_group_and_drives_the_rest` |

### Refuting my own test

- **(a) Genuine red? Yes.** I ran the project's C4 runner (`engine/scripts/run-verify.sh`,
  with `PDCA_BUNDLE` and `PDCA_WORKTREE` set), which reverts only the production hunks in
  place. Green leg: `test_merge_group` ran 18 tests, OK. Red leg: `FAILED (failures=16)`, all
  assertion failures, no import error. Verdict: `PDCA-EVIDENCE: C4 PASS — red without the
  fix, green with it`. Log: `results/issue_412/build-c4-run.log`. The two cases green on both
  legs are the guards that are meant to pass without the fix: (e), stack mode unchanged, and
  the `expected_checks` one. The two edited stand-in modules ran green on both legs, as they
  should. I also ran the new test file against **iteration 1's** production code (its
  production hunks applied under the new test): 9 failures, namely the 6 new finding cases
  plus 3 cases whose end-of-run wording changed. So each new case fails on the gap it was
  written for, not only on the bare base. Afterwards the worktree was restored, and
  `git diff` was byte-identical to `patch.diff`.
- **(b) Production path? Yes.** The cases go through the real `flow._drive_and_act`,
  `flow.flow_batch` and `cli.main`. Below those they reach the real `waves.compute_waves`,
  `check_dep_graph` and `partition_schedulable`, the real `merge.merge_wave`, `group_blocker`
  and `_merge_one`, the real `flow._runnable`, and the real `split.accept`,
  `_adopt_split_children` and `_reschedule`. None of the group logic is mocked. Only the
  model leaves, the publish mechanics and the host (`gh`) are stubbed.
- **(c) Fixture includes the fault? Yes.** The split case really splits a wave-0 bundle,
  through production code, before the group's last member, so the re-levelling runs on the
  real tail. The no-PR case leaves B with no `publish.json`: the state a failed T4 or publish
  leaves. The `Onto branch` case writes a real `"stacked"` record. In the sweep case X is held
  for a real unresolvable dependency. In the dropped-child case P is really DISCONTINUED and a
  second split really re-levels the tail. The final-wave case is the independent A/B batch
  from the review. Every `gh` call is recorded, none filtered.

## Other checks run

- Full offline driver suite (`cd template && PYTHONPATH=src python3 -m unittest discover -s
  tests`, under `timeout`) on the near-final tree: 2647 tests, 1 failure, which was the
  stand-in signature above. After that fix, the affected modules (`test_flow_adopt_split`,
  `test_flow_single_driver`, `test_merge_group`, `test_merge`, `test_waves`, `test_flow_slice`,
  `test_merge_onto_branch`) ran 261 tests, OK. The final full run is part of T3 below.
- T2, `engine/scripts/run-docs-check.sh`: `PDCA-EVIDENCE: docs lint clean, site render + link
  audit clean`.
- T3, `engine/scripts/run-suite.sh` on the final tree: root render/update suite `Ran 24 tests
  … OK` (copier present, nothing skipped), driver suite `Ran 2648 tests … OK (skipped=2)`,
  `PDCA-EVIDENCE: root suite OK, driver suite OK`. Log: `results/issue_412/build-t3-run.log`.
  Nothing in the worktree changed while it ran.
- Commit-readiness: the target has no formatter or pre-commit config (no
  `.pre-commit-config.yaml`, no ruff/black/flake8 config, nothing in CONTRIBUTING.md). Its CI
  runs the docs check (T2) and the render suite (T3), both run here. Every new Python line is
  within 100 columns. The one long line is the template field line
  (`template/templates/brief.md.tpl:34`), which matches the field lines around it.

No external dependency beyond what the brief lists (none) was needed.
