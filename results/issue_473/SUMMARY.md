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

Task under review: recover stranded descendants from already-terminal split parents, resize the flow pass pool as adoption adds waves, and keep single-id stdout consistent with whole-run outcomes.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The acceptance contract is concrete and bounded across recovery, live-wave budgeting, and stdout/exit-code agreement, with no external dependency or ambiguous scope. |
| C2 Reproduction (red pre-fix) | PASS | The independent base-tree run executed all 14 focused tests and failed 12, including the recovery, starvation, and reporting assertions at `template/tests/test_flow_adopt_recovery.py:332`, `template/tests/test_flow_adopt_recovery.py:514`, and `template/tests/test_flow_adopt_recovery.py:608`. |
| C3 Change | PASS | The target matches patch-applied HEAD on all six affected paths, and the scoped production changes converge at the existing adoption splice, live pool read, and result-map report at `template/src/pdca_harness/flow.py:1471`, `template/src/pdca_harness/flow.py:1492`, and `template/src/pdca_harness/cli.py:688`. |
| C4 Verification (red→green) | PASS | The configured wrapper is absent from the target, but the required direct rerun is conclusive: 14 tests ran with 12 failures on the production-reverted tree and all 14 passed on the byte-identical patch-applied tree at `template/tests/test_flow_adopt_recovery.py:143`. |
| C5 Causal adequacy | PASS | The cause is changed rather than probed or guarded: terminal split parents enter the existing adoption path and the pool derives from the live schedule; no capability-probe/runtime-guard smell was added at `template/src/pdca_harness/flow.py:1471` and `template/src/pdca_harness/flow.py:1492`. |
| T1 Structure | PASS | The six-file change is cohesive—flow/CLI behavior, focused regression coverage, and matching operator/planner documentation—with no unrelated subsystem change; `git diff --check` is clean. |
| T2 Shape | PASS | Independent docs lint and a 22-page rendered-site audit both passed with no dangling links, and the documented recovery/report/budget contracts align at `docs/07-crosscutting.md:259`, `docs/07-crosscutting.md:289`, and `docs/07-crosscutting.md:344`. |
| T3 Runtime | PASS | The patched target passed all 1,674 offline driver tests (2 unrelated unrendered-template skips) and all 7 real Copier render/update compatibility tests; the focused runtime enters `cli._flow` at `template/tests/test_flow_adopt_recovery.py:143`. |
| T4 Contribution | NEEDS-HUMAN | Decide whether the contribution text is acceptable—`pr-description.md` and `commit-msg.txt` are absent, so the substantive checker cannot be rerun and explicitly defers at `template/src/pdca_harness/cli.py:1106`; affected-path merged history plus the sole closed-unmerged PR (README-only #4) found no duplicate. |
| T5 Judgment | PASS | The evidence exercises production `cli._flow` and `split.accept`, compares mid-run/recovery parity, and tests real failure and waiting outcomes rather than only happy-path helper behavior at `template/tests/test_flow_adopt_recovery.py:143`, `template/tests/test_flow_adopt_recovery.py:192`, and `template/tests/test_flow_adopt_recovery.py:450`. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether automatic recovery, per-live-wave spending, and multi-line single-id output are acceptable operator semantics—the automated evidence establishes behavior, but product fitness and compatibility remain sign-off judgments at `docs/07-crosscutting.md:259`, `docs/07-crosscutting.md:289`, and `docs/07-crosscutting.md:344`. |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T4 Contribution — Decide whether the contribution text is acceptable—`pr-description.md` and `commit-msg.txt` are absent, so the substantive checker cannot be rerun and explicitly defers at `template/src/pdca_harness/cli.py:1106`; affected-path merged history plus the sole closed-unmerged PR (README-only #4) found no duplicate.
- [x] Validation — fitness-to-purpose — Decide whether automatic recovery, per-live-wave spending, and multi-line single-id output are acceptable operator semantics—the automated evidence establishes behavior, but product fitness and compatibility remain sign-off judgments at `docs/07-crosscutting.md:259`, `docs/07-crosscutting.md:289`, and `docs/07-crosscutting.md:344`.
- [x] size backstop — this slice is behaving oversized: 3 round(s) already spent (threshold 3). Recommend answering `iterate-plan` at sign-off and authoring the split in the re-plan (`pdca split`), rather than `iterate-do`: a slice that is too big yields implementation-shaped findings every round, and splitting authors briefs, which is Plan's beat.
- [x] T5 Judgment — Decide and preserve landing order — prerequisite #472 remains outside `origin/main` (open draft PR #478), while this patch was verified on its folded integration content, so publishing it first would omit the adoption core it extends.

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: merged-wider
- Iteration delta (if iterating):
- By / date: Eduard Ralph / 2026-08-09

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
