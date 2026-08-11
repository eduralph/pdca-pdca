# Result — issue 457 / sizing-ignores-sibling-conflicts

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: 
- Success criterion: (a) for a bundle carrying child lineage, `Conflicts with` entries naming its own
      `siblings` are excluded from the conflict count — a materialised child whose churn
      features are N sibling conflicts plus an inherited `Difficulty: high` plus inherited
      external-dependency tokens scores **below** the `oversized` cutoff of 7, where it
      scores ≥ 7 today;
  (b) **organic** conflicts — any id not in `siblings` — still score at full weight, and a
      bundle with no lineage scores byte-identically to today (assert against an existing
      fixture, not only a synthetic one);
  (c) the sibling-conflict **count is exposed** on the estimate (e.g. a field on
      `SizeEstimate`). This is not decoration: child-3 must key its wording on whether
      sibling conflicts actually carry the score rather than on mere presence of lineage,
      and child-4's convergence report must still be able to *see* a proposal whose children
      all conflict pairwise — which is the splitter's own statement that the split separated
      nothing, and would otherwise be scored as a clean split by the very report that exists
      to detect non-convergence;
  (d) **`sizing.estimate` and `template/scripts/size-calibrate` agree on what
      `conflicts_with` means.** The calibrator mines `len(set(brief.conflicts_with(ap)))`
      raw (`size-calibrate:300`), so after (a) a *shared* feature name denotes two different
      quantities, and any Act-cadence retune of the weight (#324/#359 — the loop this
      change explicitly leaves the weights to) would fit it on a value the engine no longer
      uses for split children. Resolve it here rather than deferring: either mine the same
      excluded count, or mine both under distinct names. A test asserts the agreement.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: 

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: Fixed
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
- T3 runtime: render/update-compat + offline driver suites: fail — == T3: root suite OK, driver suite FAILED (rc 1)
- T4 PR body has a user-impact opener + tracker id in both artifacts: pass — ./scripts/pdca contribcheck
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Reviewing issue #457: stop split-child sibling scheduling conflicts from inflating sizing churn while preserving organic-conflict scoring and calibration visibility.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief defines falsifiable sibling-only, organic-conflict, no-lineage, exposed-count, and calibrator-agreement outcomes against the estimator contract at `template/src/pdca_harness/sizing.py:255`. |
| C2 Reproduction (red pre-fix) | PASS | With only production hunks reversed in a copy of the target, all 9 tests executed and the materialised child scored 9 against the cutoff 7, failing the assertion at `template/tests/test_sizing_split_child.py:87`. |
| C3 Change | FAIL | A malformed lineage list member such as `"siblings": [[]]` now raises `TypeError` while building the set at `template/src/pdca_harness/sizing.py:251`, so the required abstain-not-crash behavior is not preserved. |
| C4 Verification (red→green) | PASS | The focused oracle independently ran 9 tests red without the production hunks and 9/9 green with them; the agreement assertion exercises both estimator and calibrator at `template/tests/test_sizing_split_child.py:217`. |
| C5 Causal adequacy | PASS | The change removes sibling ids from the scored quantity at `template/src/pdca_harness/sizing.py:293` and retains organic conflicts, rather than adding a capability probe or downstream symptom guard. |
| T1 Structure | PASS | One helper owns sibling classification and the calibrator imports it at `template/scripts/size-calibrate:70`; model combination preserves the exposed count at `template/src/pdca_harness/sizing.py:526`. |
| T2 Shape | PASS | Documentation lint and a 22-page site render/link audit independently passed; the documented organic/excluded distinction is grounded at `docs/07-crosscutting.md:129`. |
| T3 Runtime | FAIL | Although the full offline suite, 124 focused regression tests, and compile checks passed, the malformed-lineage runtime case crashes at `template/src/pdca_harness/sizing.py:251` despite the total-reader contract at `template/src/pdca_harness/split.py:373`. |
| T4 Contribution | NEEDS-HUMAN | Human/publish must confirm the PR body opener and tracker id in both contribution artifacts — those artifacts were not supplied, so the recorded green cannot be independently rerun against the rules at `template/src/pdca_harness/cli.py:1061`. |
| T5 Judgment | NEEDS-HUMAN | Human must confirm issue #456 lands before this integration-based patch and that no closed/rejected affected-path work changes the approach — merged history includes #456, but closed/rejected prior art was not mechanically available; the dependency surface begins at `template/src/pdca_harness/split.py:373`. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Human must run the render and `copier update` compatibility suites with real `copier` installed and judge release fitness — `copier` was absent here, so the green offline suite did not exercise that external dependency. |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T4 Contribution — Human/publish must confirm the PR body opener and tracker id in both contribution artifacts — those artifacts were not supplied, so the recorded green cannot be independently rerun against the rules at `template/src/pdca_harness/cli.py:1061`.
- [ ] T5 Judgment — Human must confirm issue #456 lands before this integration-based patch and that no closed/rejected affected-path work changes the approach — merged history includes #456, but closed/rejected prior art was not mechanically available; the dependency surface begins at `template/src/pdca_harness/split.py:373`.
- [ ] Validation — fitness-to-purpose — Human must run the render and `copier update` compatibility suites with real `copier` installed and judge release fitness — `copier` was absent here, so the green offline suite did not exercise that external dependency.

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
- Iteration delta (if iterating): Rejected on the reviewer's C3 finding only; the approach (sibling-conflict exclusion, shared helper, exposed count) is accepted in principle — keep it. 1) C3: `sibling_conflict_count` does `set(siblings)` on raw lineage JSON — a malformed record like `"siblings": [[]]` (unhashable member) passes the isinstance-list guard and raises TypeError at `template/src/pdca_harness/sizing.py:251`. The brief's constraint is abstain-not-crash: harden the helper (e.g. keep only `str` ids before building the set) and add the malformed-lineage case to `template/tests/test_sizing_split_child.py`. 2) The T3 gate red (11 failures in `template/tests/test_verify_base.py`, `PDCA_VERIFY_BASE` leaking into its subprocesses) is a pre-existing harness test-isolation fault affecting every stacked bundle — it is NOT this patch's defect and is out of scope. Do not chase it; expect the same non-gating red on the rebuild.
- By / date: Eduard Ralph / 2026-08-08

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
