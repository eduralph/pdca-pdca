# Adversarial review — issue 412 / merge-mode-atomic-merge-group

Verdict: **refuted on four concrete inputs.** The red→green proof is real, but the new
group logic breaks on paths the 11 tests never take: a mid-run split, a resumed run, a
member with no PR, and a group declared only from outside the run. Each was reproduced
against the patched tree at `$PDCA_TARGET`, using the bundle's own test fixture
(`scratch/probe/probe_group.py` in this sandbox subclasses `tests.test_merge_group.MergeGroup`;
run it with `PYTHONPATH=target/template/src:target/template`).

## The evidence (could not refute)

- `template/tests/test_merge_group.py:58` and on — re-ran on the patched tree: 11/11 pass.
  The frozen red leg (`gate-logs/C4-verify.log`) shows 10/11 failing on assertions, not on
  imports. The one test that passes red is (e), stack mode, which is a regression guard and
  is expected to pass both ways. The tests go through the real `flow._drive_and_act`,
  `cli.main` and `merge.merge_wave`, with only the leaves, publish and `gh` stubbed. So C4 and
  C5 hold. One coverage gap that is not a defect: every case pins `merge_requires="required"`
  (`test_merge_group.py:58`). That means the default `"all"` release path is never run. On
  that path every member after the first is always behind its base (the earlier member just
  merged), so it always goes through `gh pr update-branch` plus a rollup wait
  (`template/src/pdca_harness/merge.py:602-640`). That is the "narrower window" the brief
  accepts, but it is untested.

## The fix (refuted)

- NEEDS-HUMAN [impl] — **A split anywhere in the run before the group's last member breaks
  the group.** `template/src/pdca_harness/flow.py:2386-2387` re-plans only the un-driven
  tail (`remaining = wave_list[k+1:]`). Then `waves.partition_schedulable` runs the new
  merge-mode loop over that tail alone (`template/src/pdca_harness/waves.py:482-484`). A
  member already driven this run (A, wave 0) is not in that tail, so
  `merge_group_refusals` treats it as "outside the batch" (`waves.py:274`). Failing case:
  fixture (a) plus a bundle S in wave 0 that splits into S1. The run prints `issue_B held
  this run — … names issue_A, which is not in this run's batch … ways out: add A to this
  run's ids` (A *was* named). B and C are never built (results `B: PLANNED, C: PLANNED`), and
  A is left held as a draft. Without the split the same batch passes test (a). Fix
  direction: count bundles this run already drove (`accepted`) as in-batch for the group
  check in the reschedule. Or skip the outside-member refusal there, since `check_dep_graph`
  already vetted the request.

- NEEDS-HUMAN [impl] — **A member with no recorded PR half-lands the group, though the run
  could see that before any `gh` call.** `merge.py:144-164` checks only that every member is
  COMPLETE before merging the group one member at a time. Then `_merge_one` STOPs on a
  missing PR record (`merge.py:541-544`) or an `Onto branch` `"stacked"` record
  (`merge.py:552-560`). Failing case: fixture (a) where B's publish failed (texts did not
  pass T4, so there is no `publish.json`). At wave 1's boundary A is readied and merged, then
  B fails with `has no recorded PR`, and the run prints `landed only in part — issue_A
  merged`. That is the exact half-landed state this field exists to prevent. The brief's
  Impact section accepts this window only for a merge the *host* refuses. This cause is
  local and knowable. Fix direction: before the first merge of a group, check each member's
  record (`pr_url` present, `mode != "stacked"`). If any fails, hold the whole group instead.

- NEEDS-HUMAN [human] — **A held group cannot be finished by any later merge-mode run, and
  the run's own advice points the wrong way.** `flow.py:3524-3551` skips a named COMPLETE id
  (A) as terminal, so the drive set is just `[B]`. Then `waves.py:147-151` refuses B because
  its group names A "outside the batch". Failing case: run 1 ends as in test (b) (B
  DISCONTINUED, A held). `_report_group_holds` says "merge it together with the rest of the
  group once every member is COMPLETE" (`flow.py:3236`). The docs say the same at
  `docs/07-crosscutting.md:899`. The human re-plans B and runs `pdca flow A B C D`, which
  exits **2** with `Ways out: add A to this run's ids` — but A is already in the ids. The
  `--from-csv` sweep (`flow_batch` → `partition_schedulable`) holds B forever the same way.
  The only real ways out are stack mode or deleting the `Merges with` edge. A human has to
  decide whether a finished named member should count as a group member and be merged at a
  later boundary. At minimum, the remedy text at `waves.py:280` should not tell the user to
  add an id they already passed.

- NEEDS-HUMAN [human] — **A group declared only by a bundle outside the run is ignored, so
  A merges alone.** `waves._merges_with` reads only the briefs of the bundles passed in
  (`waves.py:180-184`). Failing case: X's brief says `Merges with: A`, and A's brief says
  nothing. `pdca flow A Z` (Z `Depends on: A`, so A is in a non-final wave) exits 0 with A's
  PR merged at wave 0's boundary. The brief says one-sided declarations bind both sides (f),
  and that an out-of-batch member is refused (g). Neither holds when the outside bundle is
  the one declaring. The builder copied `conflict_map`, which only reads in-batch briefs.
  The brief named it as the model, and for conflicts that is harmless. For a merge group it
  is not. Whether the check should scan other bundles on disk for `Merges with` lines that
  name an id in the batch is a scope call.

## The verdict

- `check-gates.json` reports `overall: "pass"` with C4/C5/T3 green. Those gates are accurate
  for what they measure. The unwarranted claim is in the docs and stderr text this diff
  adds: "the run goes on and merges the group once every member is COMPLETE"
  (`merge.py:150-157`, `docs/07-crosscutting.md:899`). As shown above, that only holds when
  the whole group is driven in one run with no split before its last member, and every
  member has a mergeable PR record.
- Also tried, and could not break. Run as a probe: a 3-member group across 3 waves, with
  a 4th wave so the release is not final. A is held at boundary 0, A and B at boundary 1,
  then A, B, C merge in that order before G builds, and `holds` ends empty. Checked by
  reading only: `_back_to_back` keeps members next to each other; the merge-mode loop in
  `partition_schedulable` ends, because each round holds at least one more survivor; a
  member that is COMPLETE with no patch is not held, and its merge is a no-op; stack mode
  ignores the field (`held_group` stays empty, and both refusal sites check
  `wave_mode == "merge"`).

<!-- pdca:leaf-complete -->
