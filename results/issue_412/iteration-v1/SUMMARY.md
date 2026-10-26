# Result — issue 412 / merge-mode-atomic-merge-group

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: A brief can declare `- **Merges with:** <id>[, <id>…]` — an atomic merge group: these bundles must not land on the base separately. In merge mode the driver does not ready or merge a COMPLETE group member while any member of its group is not yet COMPLETE; once all are COMPLETE it merges the whole group back-to-back, in dependency order, at one wave boundary, each through the normal `merge._merge_one` gates. A bundle that depends on a held group member is held too (not built on a base without it). A group that is also a dependency chain (one member `Depends on` another) cannot work in merge mode — the consumer can only build after the producer merges, which the group forbids — so such a batch is refused before anything is built, with a message giving the two ways out: make the pair one bundle, or run the batch in `wave_mode = "stack"`. Two more group shapes are refused the same way in merge mode, for the same reason: members that `Conflicts with` each other (the later one is built on a base without the held earlier one, so its PR needs `gh pr update-branch` across a declared overlap at the release boundary — the half-landed STOP this field exists to prevent), and a `Merges with` id that is not in this run's batch (`merge_wave` only ever sees this run's bundles, so the group could never be merged together). In stack mode the field changes nothing (the human already merges the stack and can take the pair together).
- Success criterion: With `wave_mode = "merge"` and `gh` stubbed: (a) A and B both declare `Merges with` each other and have no edge between them; D (no group) is in wave 0, B `Depends on: D` (so A in wave 0, B in wave 1), and C `Depends on: B` (so wave 2) — at the wave-0 boundary no `gh pr ready` / `gh pr merge` is called for A's PR and the run goes on; at the wave-1 boundary A's and B's PRs are both merged, A first, before C builds; (b) if B ends not COMPLETE (e.g. DISCONTINUED), A is never merged by the run and stderr names A as held for its group with B; (c) a bundle `Depends on: A` while A is held is not built and is named as held; (d) a batch where B `Depends on: A` and they declare `Merges with` each other makes `pdca flow` exit non-zero before any Do runs, stderr naming both ids and both ways out; (e) the same batch with `wave_mode = "stack"` runs as it does today (the field is ignored); (f) `Merges with` declared on one side only is treated as symmetric (as `Conflicts with` is); (g) in merge mode, a group whose members `Conflicts with` each other, and a group naming an id outside the batch, are each refused the same way as (d), before any Do. Cases (d) and (g) are tested at the CLI: `cli.main(["flow", …])` returns 2 and stderr carries the `Ways out:` line (`template/src/pdca_harness/cli.py:673-679`, which turns `waves.DependencyGraphError` into rc 2 with `exc.remedy`); the remedy names both ways out.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: The `Merges with` field (parse, symmetric, ids only), merge-mode hold-and-merge-together, the dependents' hold, the up-front refusal of a chained group in merge mode, and docs plus the brief template line (`template/templates/brief.md.tpl`, next to `Conflicts with`). / out of scope: building the consumer of a chained group on the producer's unmerged branch in merge mode (alternative A — see Open questions); making the sizer or `pdca split` refuse to split across a group (follow-up); host-side atomicity (GitHub has no multi-PR merge — if a later member's merge fails after an earlier one merged, the run stops and says which landed, see Impact); stack mode behaviour.

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: new-feature
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: pass — C4 PASS — red without the fix, green with it
- C5 added test exercises production, not a copy: pass — 1 added driver-suite test(s) import the production package 'pdca_harness'

## 4. Conformance (Check — stack)
- T1 Structure: none — (no gate configured)
- T2 shape: docs lint + site render link audit: pass — docs lint clean, site render + link audit clean
- T2 host CI parity: target docs-check.yml on the pushed tree: pass — host CI parity on the patched tree — docs lint clean, site render + link audit clean
- T3 runtime: render/update-compat + offline driver suites: pass — root suite OK, driver suite OK
- T4 PR body has a user-impact opener + tracker id in both artifacts: deferred — pr-description.md not drafted yet — the substantive T4 audit of the contribution artifacts runs at publish
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Review issue #412: add symmetric `Merges with` groups that wait and merge together in merge mode, hold dependents, and refuse unschedulable groups.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | NEEDS-HUMAN | Decide whether refusing chained pairs satisfies the motivating use cases or requires Plan re-entry for alternative A — the brief explicitly leaves this scope decision open (brief.md:51; target source: docs/03-plan.md:102). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing the tracked fix while retaining the added test reproduces 10 assertion failures in 11 tests, including premature ready/merge calls; imports succeed (review-red.log; template/tests/test_merge_group.py:201). |
| C3 Change | PASS | The optional field, scheduling refusals, group merge boundary, dependent holds, template, and docs address one declared feature; no unrelated production change found (template/src/pdca_harness/brief.py:227; template/src/pdca_harness/flow.py:3113; template/templates/brief.md.tpl:34). |
| C4 Verification (red→green) | PASS | Independently restored the stashed fix and reran the same 11 tests: all pass after 10 pre-fix assertion failures; this confirms the asserted regression coverage, with the additional missed case recorded under C5 (review-green.log; gate-logs/C4-verify.log:10; template/tests/test_merge_group.py:217). |
| C5 Causal adequacy | NEEDS-HUMAN [impl] | Cover and report groups whose members all finish in the final wave — the independent A/B case returns COMPLETE, rc 0, empty holds and empty stderr, omitting the promised instruction to merge together (template/src/pdca_harness/flow.py:3106; template/src/pdca_harness/flow.py:3192; docs/07-crosscutting.md:896; review-extra-cases.log:1). |
| T1 Structure | PASS | Parsing, graph policy, merge mechanics, and run-scoped holds remain in their existing modules; each member still uses the existing merge gates (template/src/pdca_harness/waves.py:174; template/src/pdca_harness/merge.py:164; template/src/pdca_harness/flow.py:2937). |
| T2 Shape | PASS | Independent docs lint, 22-page site render/link audit, and git diff whitespace check pass; frozen docs and host-CI logs corroborate the same commands (review-docs-lint.log:1; review-docs-render.log:1; gate-logs/host-ci-docs.log:10). |
| T3 Runtime | PASS | Independent driver discovery passes 2,641 tests with two skips; local root discovery skips three Copier suites because Copier is absent, but the frozen log shows actual render/update execution and all 24 root tests passing (review-driver-suite.log; review-root-suite.log; gate-logs/T3-suite.log:39; gate-logs/T3-suite.log:54). |
| T4 Contribution | N/A | Contribution artifacts are drafted after Check; the deferred gate explicitly requires the substantive contribution audit at publish (gate-logs/T4-contribution.log:10). |
| T5 Judgment | NEEDS-HUMAN | Confirm merged and closed/rejected prior art across the remaining affected paths — the brief records path-based checks only for brief.py, waves.py and merge.py; the supplied snapshot has one synthetic base commit and no remotes, preventing independent settlement for flow.py, cli.py, docs, template and tests (brief.md:22; review-prior-art.log:1). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Accept or reject best-effort grouping with a possible partially landed group after a later merge refusal, plus manual merging for final-wave groups — these limits determine whether the feature meets the operational need (docs/07-crosscutting.md:896; template/src/pdca_harness/merge.py:168; brief.md:47). |

Source citations are relative to `$PDCA_TARGET`; evidence paths are relative to this review directory. The target was readable, contained the applied patch, and was restored after the red leg. Production files were not edited. The instance-scoped gate wrappers are not supplied here; their complete frozen logs were inspected, and available underlying checks were rerun. The production-import scanner also passes independently against this patch (template/scripts/checks/test_exercises_production.py:71; template/tests/test_merge_group.py:38). The frozen Copier run exercised the required dependency, so its local absence is a rerun limitation rather than an undischarged dependency.

The C5 omission occurs because `held_group` is populated only through `merge_wave`, which is skipped for the final wave (template/src/pdca_harness/merge.py:158; template/src/pdca_harness/flow.py:3106). End-of-run reporting only visits that set (template/src/pdca_harness/flow.py:3228). When A declares `Merges with: B` and both are in the only wave, neither is registered, so the human receives no group-merge instruction. The existing final-wave test starts A in an earlier wave and therefore misses this case (template/tests/test_merge_group.py:265). Preserve the final-wave draft behavior while reporting these groups and adding regression coverage for this arrangement.

The independent reproduction is saved as `review-extra-cases.py`. From this review directory, run:

```sh
TMPDIR="$PWD/review-tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/target/template/src:$PWD/target/template" python3 review-extra-cases.py
```

Observed: both results COMPLETE, no merged PRs, `holds={}`, `rc=0`, `stderr=''`; the assertion requiring the group-merge notice fails. Additional probes passed: a connected three-member group merged consecutively, and an indirect dependency between group members was refused with exit 2 before any build (review-extra-cases.log:2; review-extra-cases.log:3).

This report is advisory; acceptance remains the human's decision.

<!-- pdca:leaf-complete -->

### Advisory — adversary

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

### Advisory — code-review

# Advisory code review — issue 412 (merge-mode atomic merge group)

Lens: bugs the patch introduces, plus reuse / simplification. Advisory only; nothing here gates. All path:line refs are on the patched tree at `$PDCA_TARGET`.

## Correctness

- NEEDS-HUMAN [impl] — **A split mid-run breaks any group that spans driven and undriven waves.** `template/src/pdca_harness/flow.py:2386-2387` re-waves only `wave_list[k + 1:] + children` through `waves.partition_schedulable`. In merge mode that now runs `merge_group_refusals` on those survivors (`template/src/pdca_harness/waves.py:482-491`). Take fixture (a): if any wave-0 bundle splits, the re-wave set is `[B, C, children]`. B's `Merges with: A` names A, which has already been driven and is no longer a survivor, so B is refused as "a member outside the batch" and held, and C is held with it. A then stays a draft forever, and the run blames a group shape that was fine. Fix: judge the "outside" rule against the whole run's batch (or skip it in `_reschedule`), not the remaining tail. No test covers a split in a merge-mode run that has a group.

- NEEDS-HUMAN [impl] — **One-sided declarations get lost once the declaring bundle drops out of the set.** `waves._merges_with` (`template/src/pdca_harness/waves.py:180-191`) reads only the briefs of the bundles it is given. In the sweep, `flow.py:3393` replaces `bundles` with the schedulable survivors, and the drive then calls `waves.merge_groups(cfg, bundles)` (`flow.py:3116`, `flow.py:2957`) on that reduced list. Example: X declares `Merges with: A`, A's brief is silent, and X is held (say for an unresolved dependency). A is then in no group and merges alone at its boundary, which is exactly the half-landing the field exists to stop. The `while` loop's comment at `waves.py:479-481` ("a group one of whose members is held now names a bundle outside the survivors") is only true when the survivor's own brief makes the declaration. Fix: build the relation from the full input `bundles`, and hold any survivor whose group has a held member.

- NEEDS-HUMAN [human] — **Same gap with explicit ids.** `pdca flow A`, where an out-of-batch X declares `Merges with: A` and A says nothing: `check_dep_graph` only reads in-batch briefs (`waves.py:180`), so nothing is refused and A merges alone. Success criterion (f) says either side binds both, and (g) refuses an out-of-batch member. Catching this needs a scan of on-disk briefs beyond the batch. That is a scope call, not a simple fix.

- NEEDS-HUMAN [impl] — **The release does not check that every member can be merged before merging the first one.** Once all members are COMPLETE, `merge_wave` merges them one after another (`template/src/pdca_harness/merge.py:163-176`). `_merge_one` refuses, *after* an earlier member has already landed, in cases the code could have detected up front: no recorded PR (`merge.py:541-544`, e.g. the later member's publish texts failed T4 — `flow.py:3094-3097` still leaves it in `complete`), a `"stacked"` record (`merge.py:552-560`), or `cfg.expected_checks_error` (`merge.py:573-577`). `_back_to_back` puts earlier-wave members first, so the member that has been waiting (A) lands, then B is refused, and the group is half landed. The "landed only in part" message makes this visible, but these local, deterministic refusals could be checked for every member before the first `gh pr ready`, with the whole group held if any member fails. That would leave only true host-side failures (red checks, refused merge) as the remaining window, which is the window the brief's Impact section accepts.

- `template/src/pdca_harness/merge.py:146` — a member with no patch (close/no-fix) skips the hold, and so does any bundle that isn't COMPLETE, which is fine. But a no-patch member still counts as a member its partners wait for (`merge.py:148-149` only checks state). So a group where one member resolves as no-fix still merges the others together once it is COMPLETE. That matches the design; noted only so the behaviour is known.

## Tests

- NEEDS-HUMAN [impl] — `template/tests/test_merge_group.py` has no case for the two gaps above: a split during a merge-mode run with a group across waves, and a one-sided `Merges with` from a bundle that ends up held. It also has no case for a release where a later member has no PR (`merge_fails` only models a host refusal at `gh pr merge`, `test_merge_group.py:101`). One case for each would pin the fixes.

## Reuse / simplification

- `template/src/pdca_harness/merge.py:148-149` and `template/src/pdca_harness/flow.py:3230-3231` compute the same "members not COMPLETE" list in the same two lines. A small shared helper (e.g. in `merge`) would keep the hold line and the end-of-run line in step.
- `waves.merge_groups(cfg, bundles)` re-reads every brief at each wave start when anything is held (`flow.py:2957`), again at each merge boundary (`flow.py:3116`), and once more at the end (`flow.py:3192`). Briefs are small, so this is cheap, but one call per wave, reused at both spots, is simpler. The value has to be recomputed when a split adds children, so it can't be cached for the whole run.
- `template/src/pdca_harness/cli.py:726-729` — the docstring reflow left a dangling short line ("the map (PLANNED, for one not built" / "yet), …"). Cosmetic.

No other problems found: the `_runnable` group hold (`flow.py:801-803`) runs after the not-COMPLETE check and is kept separate from the #593 `held` set as the brief asks; `_back_to_back` keeps group members adjacent; `held.discard` on a successful merge keeps a clean run's `holds` empty; and the stack-mode path is untouched.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] C1 Spec — Decide whether refusing chained pairs satisfies the motivating use cases or requires Plan re-entry for alternative A — the brief explicitly leaves this scope decision open (brief.md:51; target source: docs/03-plan.md:102).
- [ ] C5 Causal adequacy — Cover and report groups whose members all finish in the final wave — the independent A/B case returns COMPLETE, rc 0, empty holds and empty stderr, omitting the promised instruction to merge together (template/src/pdca_harness/flow.py:3106; template/src/pdca_harness/flow.py:3192; docs/07-crosscutting.md:896; review-extra-cases.log:1).
- [ ] T5 Judgment — Confirm merged and closed/rejected prior art across the remaining affected paths — the brief records path-based checks only for brief.py, waves.py and merge.py; the supplied snapshot has one synthetic base commit and no remotes, preventing independent settlement for flow.py, cli.py, docs, template and tests (brief.md:22; review-prior-art.log:1).
- [ ] Validation — fitness-to-purpose — Accept or reject best-effort grouping with a possible partially landed group after a later merge refusal, plus manual merging for final-wave groups — these limits determine whether the feature meets the operational need (docs/07-crosscutting.md:896; template/src/pdca_harness/merge.py:168; brief.md:47).
- [ ] **A split anywhere in the run before the group's last member breaks the group.** `template/src/pdca_harness/flow.py:2386-2387` re-plans only the un-driven tail (`remaining = wave_list[k+1:]`). Then `waves.partition_schedulable` runs the new merge-mode loop over that tail alone (`template/src/pdca_harness/waves.py:482-484`). A member already driven this run (A, wave 0) is not in that tail, so `merge_group_refusals` treats it as "outside the batch" (`waves.py:274`). Failing case: fixture (a) plus a bundle S in wave 0 that splits into S1. The run prints `issue_B held this run — … names issue_A, which is not in this run's batch … ways out: add A to this run's ids` (A *was* named). B and C are never built (results `B: PLANNED, C: PLANNED`), and A is left held as a draft. Without the split the same batch passes test (a). Fix direction: count bundles this run already drove (`accepted`) as in-batch for the group check in the reschedule. Or skip the outside-member refusal there, since `check_dep_graph` already vetted the request.
- [ ] **A member with no recorded PR half-lands the group, though the run could see that before any `gh` call.** `merge.py:144-164` checks only that every member is COMPLETE before merging the group one member at a time. Then `_merge_one` STOPs on a missing PR record (`merge.py:541-544`) or an `Onto branch` `"stacked"` record (`merge.py:552-560`). Failing case: fixture (a) where B's publish failed (texts did not pass T4, so there is no `publish.json`). At wave 1's boundary A is readied and merged, then B fails with `has no recorded PR`, and the run prints `landed only in part — issue_A merged`. That is the exact half-landed state this field exists to prevent. The brief's Impact section accepts this window only for a merge the *host* refuses. This cause is local and knowable. Fix direction: before the first merge of a group, check each member's record (`pr_url` present, `mode != "stacked"`). If any fails, hold the whole group instead.
- [ ] **A held group cannot be finished by any later merge-mode run, and the run's own advice points the wrong way.** `flow.py:3524-3551` skips a named COMPLETE id (A) as terminal, so the drive set is just `[B]`. Then `waves.py:147-151` refuses B because its group names A "outside the batch". Failing case: run 1 ends as in test (b) (B DISCONTINUED, A held). `_report_group_holds` says "merge it together with the rest of the group once every member is COMPLETE" (`flow.py:3236`). The docs say the same at `docs/07-crosscutting.md:899`. The human re-plans B and runs `pdca flow A B C D`, which exits **2** with `Ways out: add A to this run's ids` — but A is already in the ids. The `--from-csv` sweep (`flow_batch` → `partition_schedulable`) holds B forever the same way. The only real ways out are stack mode or deleting the `Merges with` edge. A human has to decide whether a finished named member should count as a group member and be merged at a later boundary. At minimum, the remedy text at `waves.py:280` should not tell the user to add an id they already passed.
- [ ] **A group declared only by a bundle outside the run is ignored, so A merges alone.** `waves._merges_with` reads only the briefs of the bundles passed in (`waves.py:180-184`). Failing case: X's brief says `Merges with: A`, and A's brief says nothing. `pdca flow A Z` (Z `Depends on: A`, so A is in a non-final wave) exits 0 with A's PR merged at wave 0's boundary. The brief says one-sided declarations bind both sides (f), and that an out-of-batch member is refused (g). Neither holds when the outside bundle is the one declaring. The builder copied `conflict_map`, which only reads in-batch briefs. The brief named it as the model, and for conflicts that is harmless. For a merge group it is not. Whether the check should scan other bundles on disk for `Merges with` lines that name an id in the batch is a scope call.
- [ ] **A split mid-run breaks any group that spans driven and undriven waves.** `template/src/pdca_harness/flow.py:2386-2387` re-waves only `wave_list[k + 1:] + children` through `waves.partition_schedulable`. In merge mode that now runs `merge_group_refusals` on those survivors (`template/src/pdca_harness/waves.py:482-491`). Take fixture (a): if any wave-0 bundle splits, the re-wave set is `[B, C, children]`. B's `Merges with: A` names A, which has already been driven and is no longer a survivor, so B is refused as "a member outside the batch" and held, and C is held with it. A then stays a draft forever, and the run blames a group shape that was fine. Fix: judge the "outside" rule against the whole run's batch (or skip it in `_reschedule`), not the remaining tail. No test covers a split in a merge-mode run that has a group.
- [ ] **One-sided declarations get lost once the declaring bundle drops out of the set.** `waves._merges_with` (`template/src/pdca_harness/waves.py:180-191`) reads only the briefs of the bundles it is given. In the sweep, `flow.py:3393` replaces `bundles` with the schedulable survivors, and the drive then calls `waves.merge_groups(cfg, bundles)` (`flow.py:3116`, `flow.py:2957`) on that reduced list. Example: X declares `Merges with: A`, A's brief is silent, and X is held (say for an unresolved dependency). A is then in no group and merges alone at its boundary, which is exactly the half-landing the field exists to stop. The `while` loop's comment at `waves.py:479-481` ("a group one of whose members is held now names a bundle outside the survivors") is only true when the survivor's own brief makes the declaration. Fix: build the relation from the full input `bundles`, and hold any survivor whose group has a held member.
- [ ] **Same gap with explicit ids.** `pdca flow A`, where an out-of-batch X declares `Merges with: A` and A says nothing: `check_dep_graph` only reads in-batch briefs (`waves.py:180`), so nothing is refused and A merges alone. Success criterion (f) says either side binds both, and (g) refuses an out-of-batch member. Catching this needs a scan of on-disk briefs beyond the batch. That is a scope call, not a simple fix.
- [ ] **The release does not check that every member can be merged before merging the first one.** Once all members are COMPLETE, `merge_wave` merges them one after another (`template/src/pdca_harness/merge.py:163-176`). `_merge_one` refuses, *after* an earlier member has already landed, in cases the code could have detected up front: no recorded PR (`merge.py:541-544`, e.g. the later member's publish texts failed T4 — `flow.py:3094-3097` still leaves it in `complete`), a `"stacked"` record (`merge.py:552-560`), or `cfg.expected_checks_error` (`merge.py:573-577`). `_back_to_back` puts earlier-wave members first, so the member that has been waiting (A) lands, then B is refused, and the group is half landed. The "landed only in part" message makes this visible, but these local, deterministic refusals could be checked for every member before the first `gh pr ready`, with the whole group held if any member fails. That would leave only true host-side failures (red checks, refused merge) as the remaining window, which is the window the brief's Impact section accepts.
- [ ] `template/tests/test_merge_group.py` has no case for the two gaps above: a split during a merge-mode run with a group across waves, and a one-sided `Merges with` from a bundle that ends up held. It also has no case for a release where a later member has no PR (`merge_fails` only models a host refusal at `gh pr merge`, `test_merge_group.py:101`). One case for each would pin the fixes.
- [ ] **The design doesn't fix any of the cases in the issue.** Both real-world cases in the thread are chained pairs: "wyrd 635.6→636.5: '#653 is never merged without #658 stacked behind it'; wyrd #625→#633: 'merge as one unit'" (notes.json body), and the issue says "a chained pair (consumer builds on the merged producer) forces the producer onto the base". The brief refuses exactly that shape in merge mode (Goal; success criterion (d)). Its two ways out, "make the pair one bundle, or run the batch in `wave_mode = "stack"`", are the same workarounds the issue already rejects: "folding each pair into a single over-budget bundle or pulling the pair out of the driver… both give up part of what the harness is for". The brief admits this under Open questions but still lists the mechanism as the goal. The maintainer should decide between refusal and alternative A **before** Do. As written, Do would spend a "high"-difficulty cycle on a field that, for the motivating batches, only produces a nicer error.
- [ ] **The test fixture in criterion (a) sets up the failure that Impact calls a narrow window.** In (a), B declares `Conflicts with` A, so B lands in wave 1. In merge mode B is built on the base without A, because A is held and not merged. At the wave-1 boundary A merges first. B's head is then behind the base, and `_merge_one` runs `gh pr update-branch`. If that fails ("a conflict with the base", `template/src/pdca_harness/merge.py:559-565`), the merge is refused and the run STOPs (`flow.py:3081-3084`) with A landed and B not: the forbidden half-landed state. `Conflicts with` exists to declare that these two touch the same code, so this is the expected outcome, not an edge case. The brief's Impact says "a narrower window than today, not zero" and doesn't name it. In stack mode the `Conflicts with` partner builds on a line that holds the earlier bundle; in merge mode a held group member gives no such base. The brief should do one of these:
- [ ] **Carrying a held member across waves isn't scoped to a code site.** At the boundary, `merge.merge_wave` is called with only the current wave's `complete` list (`flow.py:3081`; `complete` is per wave, `flow.py:3071-3072`). Under (a), merging A at the wave-1 boundary means the flow loop has to keep a run-scoped set of held members and pass them back into a later wave's merge call. The Design section ("Hold"/"Release") describes this as a skip inside `merge_wave`. That framing hides the state carry in `flow._drive_and_act`. The Citations list should name that site, and the brief should say how held state relates to `_runnable`'s `held` parameter (`flow.py:682`), which today means "no branch pushed" (#593).
- [ ] **The brief doesn't say what happens to a group member that is outside the batch or left over from an earlier run.** It never says what happens when `Merges with` names an id that isn't in this run's batch, or when a member was left held by an earlier run (case (b): "A is never merged by the run"). `merge_wave` only ever gets this run's wave bundles (`flow.py:3081`), so a later run that completes B can't merge an A that finished in an earlier run. A stays a draft forever, or else B merges alone. Out-of-batch ids are already a known hazard for the other edge fields: see `_runnable`'s long out-of-batch handling at `flow.py:703-714` and 793-830. Without a rule (refuse, treat as stack-only, or hold until both are in one batch) and a criterion for it, Do will choose one silently.
- [ ] **Criterion (d) puts the refusal at the `pdca flow` exit code, but the falsifiability plan drives `flow._drive_and_act`.** The rc-2 mapping and the "Ways out:" line are in `cli.py:673-679`, which catches `waves.DependencyGraphError` raised out of `flow.flow_ids`. A test that only drives `_drive_and_act` (as the falsifiability line says) can check that the exception is raised. It can't check criterion (d)'s "exit non-zero… stderr naming both ways out". The criterion should name the CLI entry, or say that (d) means `DependencyGraphError` with a `remedy` naming both ways out. The refusal also needs `cfg.wave_mode` wherever `check_dep_graph`/`compute_waves` run (`flow.py:2855`). Their signatures today don't take the wave mode, so that's another touch the Scope doesn't list.
- [ ] **I couldn't check the target and the declared ordering.** `Repo + branch target: eduralph/pdca-harness @ main` matches the issue URL. `Depends on: none` is consistent with the thread. There is no dependency-state.json, so I couldn't check whether `Conflicts with: 547, 464` exist or what state they're in. If 547 "rewrites `merge._merge_one` and the merge-mode stop" and lands first, the hold/release hook and criterion (a)'s `gh` call order could change under this bundle. A human should confirm that 547 and 464 are live, and decide whether this one should `Stacks on` 547 rather than only conflict with it.
- [ ] **One citation is wrong.** The brief says "hold a dependent as `flow._runnable` does… `flow.py:786-865`", but `_runnable` is defined at `flow.py:681`. Lines 786-865 are the prerequisite loop and its messages inside it. This is minor, but the brief says "Do must cite path:line", so the brief should be accurate too.

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: iterated-to-Do
- Iteration delta (if iterating): Auto-iterate (round 1): rebuilding for the implementation-level findings — C5 Causal adequacy — Cover and report groups whose members all finish in the final wave — the independent A/B case returns COMPLETE, rc 0, empty holds and empty stderr, omitting the promised instruction to merge together (template/src/pdca_harness/flow.py:3106; template/src/pdca_harness/flow.py:3192; docs/07-crosscutting.md:896; review-extra-cases.log:1).; **A split anywhere in the run before the group's last member breaks the group.** `template/src/pdca_harness/flow.py:2386-2387` re-plans only the un-driven tail (`remaining = wave_list[k+1:]`). Then `waves.partition_schedulable` runs the new merge-mode loop over that tail alone (`template/src/pdca_harness/waves.py:482-484`). A member already driven this run (A, wave 0) is not in that tail, so `merge_group_refusals` treats it as "outside the batch" (`waves.py:274`). Failing case: fixture (a) plus a bundle S in wave 0 that splits into S1. The run prints `issue_B held this run — … names issue_A, which is not in this run's batch … ways out: add A to this run's ids` (A *was* named). B and C are never built (results `B: PLANNED, C: PLANNED`), and A is left held as a draft. Without the split the same batch passes test (a). Fix direction: count bundles this run already drove (`accepted`) as in-batch for the group check in the reschedule. Or skip the outside-member refusal there, since `check_dep_graph` already vetted the request.; **A member with no recorded PR half-lands the group, though the run could see that before any `gh` call.** `merge.py:144-164` checks only that every member is COMPLETE before merging the group one member at a time. Then `_merge_one` STOPs on a missing PR record (`merge.py:541-544`) or an `Onto branch` `"stacked"` record (`merge.py:552-560`). Failing case: fixture (a) where B's publish failed (texts did not pass T4, so there is no `publish.json`). At wave 1's boundary A is readied and merged, then B fails with `has no recorded PR`, and the run prints `landed only in part — issue_A merged`. That is the exact half-landed state this field exists to prevent. The brief's Impact section accepts this window only for a merge the *host* refuses. This cause is local and knowable. Fix direction: before the first merge of a group, check each member's record (`pr_url` present, `mode != "stacked"`). If any fails, hold the whole group instead.; **A split mid-run breaks any group that spans driven and undriven waves.** `template/src/pdca_harness/flow.py:2386-2387` re-waves only `wave_list[k + 1:] + children` through `waves.partition_schedulable`. In merge mode that now runs `merge_group_refusals` on those survivors (`template/src/pdca_harness/waves.py:482-491`). Take fixture (a): if any wave-0 bundle splits, the re-wave set is `[B, C, children]`. B's `Merges with: A` names A, which has already been driven and is no longer a survivor, so B is refused as "a member outside the batch" and held, and C is held with it. A then stays a draft forever, and the run blames a group shape that was fine. Fix: judge the "outside" rule against the whole run's batch (or skip it in `_reschedule`), not the remaining tail. No test covers a split in a merge-mode run that has a group.; **One-sided declarations get lost once the declaring bundle drops out of the set.** `waves._merges_with` (`template/src/pdca_harness/waves.py:180-191`) reads only the briefs of the bundles it is given. In the sweep, `flow.py:3393` replaces `bundles` with the schedulable survivors, and the drive then calls `waves.merge_groups(cfg, bundles)` (`flow.py:3116`, `flow.py:2957`) on that reduced list. Example: X declares `Merges with: A`, A's brief is silent, and X is held (say for an unresolved dependency). A is then in no group and merges alone at its boundary, which is exactly the half-landing the field exists to stop. The `while` loop's comment at `waves.py:479-481` ("a group one of whose members is held now names a bundle outside the survivors") is only true when the survivor's own brief makes the declaration. Fix: build the relation from the full input `bundles`, and hold any survivor whose group has a held member.; **The release does not check that every member can be merged before merging the first one.** Once all members are COMPLETE, `merge_wave` merges them one after another (`template/src/pdca_harness/merge.py:163-176`). `_merge_one` refuses, *after* an earlier member has already landed, in cases the code could have detected up front: no recorded PR (`merge.py:541-544`, e.g. the later member's publish texts failed T4 — `flow.py:3094-3097` still leaves it in `complete`), a `"stacked"` record (`merge.py:552-560`), or `cfg.expected_checks_error` (`merge.py:573-577`). `_back_to_back` puts earlier-wave members first, so the member that has been waiting (A) lands, then B is refused, and the group is half landed. The "landed only in part" message makes this visible, but these local, deterministic refusals could be checked for every member before the first `gh pr ready`, with the whole group held if any member fails. That would leave only true host-side failures (red checks, refused merge) as the remaining window, which is the window the brief's Impact section accepts.; `template/tests/test_merge_group.py` has no case for the two gaps above: a split during a merge-mode run with a group across waves, and a one-sided `Merges with` from a bundle that ends up held. It also has no case for a release where a later member has no PR (`merge_fails` only models a host refusal at `gh pr merge`, `test_merge_group.py:101`). One case for each would pin the fixes.. Deferred, not addressed here: 12 finding(s) that need human judgment, held in deferred-findings.json for the human at handover — not build work
- By / date: auto-iterate / 2026-10-23

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 7 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
