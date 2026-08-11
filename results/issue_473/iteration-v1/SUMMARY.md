# Result — issue 473 / flow-adopt-recovery-reporting

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: 
- Success criterion: exercised **through `cli._flow`** on byte-identical disk state:
  (1) **recovery** — a run handed an id whose bundle is ALREADY terminal on a split
  adopts its stranded children (lineage-scoped, transitive, same guards as the core) —
  no pre-run short-circuit swallows it; the mid-run and recovery shapes produce the
  same child states, stderr announcements and exit code on equivalent disk state.
  (2) **budget** — the run-wide pool is RE-SIZED when adoption grows the schedule
  (per-wave allowance × live wave count, recomputed at splice), so the v3 adversary's
  starvation scenario now completes: bundles `500` (splits into `601`), `810` briefed
  `Depends on: 500` + `Conflicts with: 601`, `pdca flow 500 810 --max-passes 2`, `601`
  costing two passes → `810` reaches COMPLETE; the budget stays bounded because
  adoption itself is bounded (the recursion guard — no reset). (3) **stdout** — the
  single-id shape never reports success it did not deliver: when adopted children exist,
  their dispositions are printed as additional `state<TAB>path` lines (or one summary
  line naming what made the rc non-zero), so stdout and the exit code cannot disagree;
  a caller reading stdout of a failed run sees the bundle that failed. Demonstrable by
  C4-verify on the patch alone.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: (1) remove the pre-run short-circuit for an id already terminal on a split:
  route it through the same lineage-scoped adoption the core uses, with identical
  guards, announcements and results-map semantics; (2) re-size the run-wide pass pool
  when adoption grows the schedule (allowance × live wave count at splice) — the Plan
  decision resolving v3 carry-forward (1) in favour of re-sizing over named-first
  service, which would fight the dependency scheduler's ordering; (3) make the
  single-id stdout shape name adopted children's dispositions (or a one-line summary of
  what made the rc non-zero) so the documented `state<TAB>path` contract and the exit
  code cannot disagree.
  / out of scope: the adoption core's detect/validate/splice/report mechanics (child-1,
  reused as-is); any change to the affirmed policy that held children are excluded from
  the results map and compatible with rc 0 (§6 Validation ticked at v3 sign-off); a disk
  sweep in `flow_ids`; `waves.compute_waves` / `partition_schedulable` semantics; the
  split command, `split.accept`, or the lineage schema; publish/fold semantics beyond
  the existing reconciliation; the T4 reviewer-evidence gap (v3 carry-forward 4 — its
  own tracker issue, not this bundle).

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: new-feature
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: pass — C4 PASS: red without the fix, green with it
- C5 Causal adequacy: none — reviewer + human sign-off

## 4. Conformance (Check — stack)
- T1 Structure: none — (no gate configured)
- T2 shape: docs lint + site render link audit: pass — render_site: link audit OK
- T3 runtime: render/update-compat + offline driver suites: pass — == T3: root suite OK, driver suite OK
- T4 PR body has a user-impact opener + tracker id in both artifacts: pass — ./scripts/pdca contribcheck
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Review of split-child recovery, adoption-aware pass-budget resizing, and truthful single-id stdout reporting for `pdca flow`.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | Recovery, `allowance × live wave count` budget growth, and stdout/exit-code agreement are separately falsifiable, so the required behavior and operator impact are clear. |
| C2 Reproduction (red pre-fix) | PASS | With only the production hunks reverted, all five tests ran and four failed on recovery, named-id starvation, and stdout honesty, grounding the pre-fix defects at `template/tests/test_flow_adopt_recovery.py:220`, `template/tests/test_flow_adopt_recovery.py:302`, and `template/tests/test_flow_adopt_recovery.py:325`. |
| C3 Change | FAIL | The live-wave sizing requirement is not delivered: `_run_pool` expressly excludes purely adopted tail waves and pure recovery gets only one wave's allowance, so scheduled children can still be stranded at `template/src/pdca_harness/flow.py:1322`. |
| C4 Verification (red→green) | PASS | Independent execution kept all five tests runnable, observed four failures without the production hunks, and observed 5/5 passing with them; the exercised CLI assertions begin at `template/tests/test_flow_adopt_recovery.py:220`. |
| C5 Causal adequacy | NEEDS-HUMAN [impl] | Rebuild the budget rule around every live wave (while retaining the non-reset bound) — the named-only cause leaves adopted-tail starvation intact and therefore does not satisfy the stated causal contract at `template/src/pdca_harness/flow.py:1338`. |
| T1 Structure | PASS | Recovery and mid-run adoption both converge on the existing splice mechanism, so the shared scheduling/reporting invariants remain centralized at `template/src/pdca_harness/flow.py:1448` and `template/src/pdca_harness/flow.py:1503`. |
| T2 Shape | NEEDS-HUMAN | Decide whether rendered documentation and link shape remain valid — the asserted `run-docs-check.sh` is absent from the target and the available render tests all skipped because `copier` is unavailable, so the recorded green cannot be independently affirmed. |
| T3 Runtime | FAIL | On the patched CLI path with allowance 3 and two adopted child waves, the observed result was rc 1 with `500/601=COMPLETE` and `602=PLANNED`; the shipped test deliberately requires that undersized-pool outcome at `template/tests/test_flow_adopt_recovery.py:325`. |
| T4 Contribution | NEEDS-HUMAN | Decide whether contribution metadata and novelty are acceptable — affected-path `git log --all` confirmed merged/local history including #468/#472, but the contribution validator/artifacts and closed/rejected-work history were unavailable, so prior art is not mechanically settled. |
| T5 Judgment | NEEDS-HUMAN [impl] | Rebuild the test evidence so stdout failure is exercised without contradicting the budget criterion — the current test turns a specified live-wave success case into its expected failure at `template/tests/test_flow_adopt_recovery.py:335`. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the corrected recovery budget and operator-visible failure reporting fit real interrupted-run workflows — automation verifies focused mechanics but cannot settle operational fitness, and the present budget behavior violates the promised outcome. |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] C5 Causal adequacy — Rebuild the budget rule around every live wave (while retaining the non-reset bound) — the named-only cause leaves adopted-tail starvation intact and therefore does not satisfy the stated causal contract at `template/src/pdca_harness/flow.py:1338`.
- [ ] T2 Shape — Decide whether rendered documentation and link shape remain valid — the asserted `run-docs-check.sh` is absent from the target and the available render tests all skipped because `copier` is unavailable, so the recorded green cannot be independently affirmed.
- [ ] T4 Contribution — Decide whether contribution metadata and novelty are acceptable — affected-path `git log --all` confirmed merged/local history including #468/#472, but the contribution validator/artifacts and closed/rejected-work history were unavailable, so prior art is not mechanically settled.
- [ ] T5 Judgment — Rebuild the test evidence so stdout failure is exercised without contradicting the budget criterion — the current test turns a specified live-wave success case into its expected failure at `template/tests/test_flow_adopt_recovery.py:335`.
- [ ] Validation — fitness-to-purpose — Decide whether the corrected recovery budget and operator-visible failure reporting fit real interrupted-run workflows — automation verifies focused mechanics but cannot settle operational fitness, and the present budget behavior violates the promised outcome.

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
- Iteration delta (if iterating): Auto-iterate (round 1): rebuilding for the implementation-level findings — C5 Causal adequacy — Rebuild the budget rule around every live wave (while retaining the non-reset bound) — the named-only cause leaves adopted-tail starvation intact and therefore does not satisfy the stated causal contract at `template/src/pdca_harness/flow.py:1338`.; T2 Shape — Decide whether rendered documentation and link shape remain valid — the asserted `run-docs-check.sh` is absent from the target and the available render tests all skipped because `copier` is unavailable, so the recorded green cannot be independently affirmed.; T4 Contribution — Decide whether contribution metadata and novelty are acceptable — affected-path `git log --all` confirmed merged/local history including #468/#472, but the contribution validator/artifacts and closed/rejected-work history were unavailable, so prior art is not mechanically settled.; T5 Judgment — Rebuild the test evidence so stdout failure is exercised without contradicting the budget criterion — the current test turns a specified live-wave success case into its expected failure at `template/tests/test_flow_adopt_recovery.py:335`..
- By / date: auto-iterate / 2026-08-09

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
