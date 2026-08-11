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

Task under review: make `pdca flow` recover stranded descendants of already-terminal split parents, fund every live adopted wave, and keep single-ID stdout consistent with the run’s exit status.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The acceptance decision is concrete and falsifiable across recovery, budget, and stdout/exit behavior, with each outcome exercised through `cli._flow` at `template/tests/test_flow_adopt_recovery.py:299`, `template/tests/test_flow_adopt_recovery.py:436`, and `template/tests/test_flow_adopt_recovery.py:519`. |
| C2 Reproduction (red pre-fix) | PASS | In an isolated clean-base tree with the new test retained, all 10 tests executed and 9 failed on the asserted recovery, budget, and stdout symptoms, including the stranded-child assertion at `template/tests/test_flow_adopt_recovery.py:310`. |
| C3 Change | PASS | The patch stays within the specified recovery, budget, reporting, documentation, and test surfaces; the entry-point change is confined to terminal split seeds at `template/src/pdca_harness/flow.py:1750`. |
| C4 Verification (red→green) | PASS | The isolated red leg ran 10 tests with 9 assertion failures, while the patched target ran the same 10 tests green, including named-id completion and failure-output assertions at `template/tests/test_flow_adopt_recovery.py:453` and `template/tests/test_flow_adopt_recovery.py:537`. |
| C5 Causal adequacy | PASS | The failures map directly to the terminal pre-filter, frozen pool, and single-ID result presentation; the patch changes those causes at `template/src/pdca_harness/flow.py:1750`, `template/src/pdca_harness/flow.py:1454`, and `template/src/pdca_harness/cli.py:670`, with no capability probe or runtime guard smell. |
| T1 Structure | PASS | Recovery reuses the existing adoption seam and isolates pool arithmetic in one helper rather than creating a parallel drive path at `template/src/pdca_harness/flow.py:1100` and `template/src/pdca_harness/flow.py:1259`. |
| T2 Shape | PASS | Independent docs lint and the 22-page rendered-site link audit passed, and the changed recovery and budget links resolve from `docs/07-crosscutting.md:257` and `docs/07-crosscutting.md:328`. |
| T3 Runtime | PASS | The full driver suite passed 1,670 tests (2 unrelated skips), all 7 Copier render/update tests passed under Copier 9.17.1, and the recovery module’s runtime cases passed at `template/tests/test_flow_adopt_recovery.py:299`. |
| T4 Contribution | NEEDS-HUMAN | Decide whether the contribution text is acceptable — affected-path history plus the sole closed-unmerged PR (which touched only README.md) found no duplicate, but `pr-description.md` and `commit-msg.txt` are outside reviewer inputs, so the substantive checker defined at `template/src/pdca_harness/cli.py:1081` could not be reproduced. |
| T5 Judgment | NEEDS-HUMAN | Decide and preserve landing order — prerequisite #472 remains outside `origin/main` (open draft PR #478), while this patch was verified on its folded integration content, so publishing it first would omit the adoption core it extends. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the operator-facing recovery, per-wave funding, and failure-reporting policy is fit for purpose — automated fixtures establish mechanics and boundedness at `template/tests/test_flow_adopt_recovery.py:350`, but policy acceptance remains the human sign-off. |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T4 Contribution — Decide whether the contribution text is acceptable — affected-path history plus the sole closed-unmerged PR (which touched only README.md) found no duplicate, but `pr-description.md` and `commit-msg.txt` are outside reviewer inputs, so the substantive checker defined at `template/src/pdca_harness/cli.py:1081` could not be reproduced.
- [ ] T5 Judgment — Decide and preserve landing order — prerequisite #472 remains outside `origin/main` (open draft PR #478), while this patch was verified on its folded integration content, so publishing it first would omit the adoption core it extends.
- [ ] Validation — fitness-to-purpose — Decide whether the operator-facing recovery, per-wave funding, and failure-reporting policy is fit for purpose — automated fixtures establish mechanics and boundedness at `template/tests/test_flow_adopt_recovery.py:350`, but policy acceptance remains the human sign-off.

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
- Iteration delta (if iterating): Auto-iterate (round 2): rebuilding for the implementation-level findings — T4 Contribution — Decide whether the contribution text is acceptable — affected-path history plus the sole closed-unmerged PR (which touched only README.md) found no duplicate, but `pr-description.md` and `commit-msg.txt` are outside reviewer inputs, so the substantive checker defined at `template/src/pdca_harness/cli.py:1081` could not be reproduced.. 1 finding(s) needing human judgment were deferred to sign-off, not addressed here.
- By / date: auto-iterate / 2026-08-09

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
