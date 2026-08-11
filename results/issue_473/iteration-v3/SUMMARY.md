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

Reviewing recovery of stranded split children, live-wave pass-pool resizing, and honest single-ID stdout reporting.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The acceptance contract is concrete and falsifiable through the public CLI path across recovery, starvation, and stdout/rc agreement (`template/tests/test_flow_adopt_recovery.py:1`). |
| C2 Reproduction (red pre-fix) | PASS | An isolated rerun kept the new test and reversed only the `cli.py`/`flow.py` production hunks: all 12 tests executed and 10 failed on the specified symptoms (`template/tests/test_flow_adopt_recovery.py:320`). |
| C3 Change | PASS | The change is confined to the requested recovery seed, splice-time budget, failure reporting, documentation, and tests, so no out-of-scope scheduler or lineage semantics are introduced (`template/src/pdca_harness/flow.py:1467`, `template/src/pdca_harness/cli.py:672`). |
| C4 Verification (red→green) | PASS | Independent red→green evidence is complete: 12 tests/10 failures without the production fix and 12/12 passing with it, including the named-ID starvation and failed-child stdout cases (`template/tests/test_flow_adopt_recovery.py:468`, `template/tests/test_flow_adopt_recovery.py:568`). |
| C5 Causal adequacy | PASS | The eager short-circuit, fixed pre-splice arithmetic, and partial results-map presentation are changed at their owning paths; no capability probe or downstream symptom guard is added (`template/src/pdca_harness/flow.py:1763`, `template/src/pdca_harness/flow.py:1535`, `template/src/pdca_harness/cli.py:672`). |
| T1 Structure | PASS | Recovery remains in the existing adoption/drive modules and its focused suite sits beside the established adoption tests, preserving the repository's structure (`template/src/pdca_harness/flow.py:1194`, `template/tests/test_flow_adopt_recovery.py:1`). |
| T2 Shape | PASS | Documentation shape is discharged: `lint_docs` passed and the rendered 22-page site reported no dangling links, including the recovery and resized-pool contract (`docs/07-crosscutting.md:275`). |
| T3 Runtime | NEEDS-HUMAN | Decide whether runtime compatibility can be accepted without a real Copier render/update run — `copier` is unavailable, so all 7 root compatibility tests skipped even though the 1,672-test driver suite passed with 2 unrelated skips (`template/agents/planner.md.jinja:170`). |
| T4 Contribution | NEEDS-HUMAN | Decide whether the contribution text is acceptable — the PR-body and commit-message inputs required by the checker are withheld, so its recorded green cannot be rerun; affected-path merged history plus the sole closed-unmerged PR (#4, README-only) found no duplicate (`template/src/pdca_harness/cli.py:1083`). |
| T5 Judgment | PASS | The evidence exercises `cli._flow` and production `split.accept` on production-shaped disk state, with cycle, no-op, failure, parity, and allowance boundaries, so no untested judgment assumption remains (`template/tests/test_flow_adopt_recovery.py:143`, `template/tests/test_flow_adopt_recovery.py:188`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether naming a terminal parent should recover its descendants and whether one allowance per finite live wave is the desired operator policy — automated evidence proves mechanics, not product-policy fitness (`docs/07-crosscutting.md:275`, `docs/07-crosscutting.md:332`). |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T3 Runtime — Decide whether runtime compatibility can be accepted without a real Copier render/update run — `copier` is unavailable, so all 7 root compatibility tests skipped even though the 1,672-test driver suite passed with 2 unrelated skips (`template/agents/planner.md.jinja:170`).
- [ ] T4 Contribution — Decide whether the contribution text is acceptable — the PR-body and commit-message inputs required by the checker are withheld, so its recorded green cannot be rerun; affected-path merged history plus the sole closed-unmerged PR (#4, README-only) found no duplicate (`template/src/pdca_harness/cli.py:1083`).
- [ ] Validation — fitness-to-purpose — Decide whether naming a terminal parent should recover its descendants and whether one allowance per finite live wave is the desired operator policy — automated evidence proves mechanics, not product-policy fitness (`docs/07-crosscutting.md:275`, `docs/07-crosscutting.md:332`).
- [ ] T5 Judgment — Decide and preserve landing order — prerequisite #472 remains outside `origin/main` (open draft PR #478), while this patch was verified on its folded integration content, so publishing it first would omit the adoption core it extends.

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
- Iteration delta (if iterating): Auto-iterate (round 3): rebuilding for the implementation-level findings — T3 Runtime — Decide whether runtime compatibility can be accepted without a real Copier render/update run — `copier` is unavailable, so all 7 root compatibility tests skipped even though the 1,672-test driver suite passed with 2 unrelated skips (`template/agents/planner.md.jinja:170`).; T4 Contribution — Decide whether the contribution text is acceptable — the PR-body and commit-message inputs required by the checker are withheld, so its recorded green cannot be rerun; affected-path merged history plus the sole closed-unmerged PR (#4, README-only) found no duplicate (`template/src/pdca_harness/cli.py:1083`).. 1 finding(s) needing human judgment were deferred to sign-off, not addressed here.
- By / date: auto-iterate / 2026-08-09

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
