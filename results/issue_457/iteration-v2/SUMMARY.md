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

Task under review: stop splitter-authored sibling conflicts from inflating child sizing churn while preserving organic-conflict scoring, excluded-count visibility, and calibrator agreement.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The acceptance boundary is falsifiable and decision-complete: sibling scheduling edges must stop affecting churn without changing organic or lineage-free scoring, while the excluded signal remains observable at `template/src/pdca_harness/sizing.py:195`. |
| C2 Reproduction (red pre-fix) | PASS | In an isolated pre-fix tree with the new test retained, 15 tests ran and exited 1; the materialised child scored 9 rather than below the cutoff of 7 at `template/tests/test_sizing_split_child.py:149`. |
| C3 Change | PASS | Malformed lineage now fails toward conservative pre-fix scoring rather than a crash or silent exclusion because only string sibling ids participate in matching at `template/src/pdca_harness/sizing.py:259`. |
| C4 Verification (red→green) | PASS | The same targeted module changed from exit 1 pre-fix to 15/15 passing with the patch, covering sibling exclusion, organic preservation, exposed count, malformed records, and calibration agreement at `template/tests/test_sizing_split_child.py:134`. |
| C5 Causal adequacy | PASS | The splitter-created input is removed before the weighted conflict feature is evaluated at `template/src/pdca_harness/sizing.py:299`; no capability probe or try-and-fallback symptom guard was introduced. |
| T1 Structure | PASS | Runtime and calibration share one exclusion helper rather than parallel definitions (`template/src/pdca_harness/sizing.py:228`, `template/scripts/size-calibrate:297`), and the guarded `AprioriBrief` surface was not widened. |
| T2 Shape | PASS | The repository's documented docs lint and site renderer both passed, including the link audit, and the edited explanation stays in the scoped estimate section at `docs/07-crosscutting.md:128`. |
| T3 Runtime | NEEDS-HUMAN | Decide whether to accept template compatibility only after running the seven root render/update tests with Copier installed — Copier is absent here so all seven skipped; the offline driver suite passed, and the reported 11 failures reproduce only when `PDCA_VERIFY_BASE` leaks into subprocesses expecting it unset at `template/tests/test_verify_base.py:126`. |
| T4 Contribution | NEEDS-HUMAN | Decide whether the PR opener and tracker references satisfy contribution policy after rerunning the bundle's validator — `./scripts/pdca` and the PR/commit artifacts were not supplied, so the asserted green could not be independently reproduced. |
| T5 Judgment | PASS | A path-by-path scan of all local history and every closed GitHub PR found only merged prior art (12 PRs) and no rejected/unmerged attempt touching the four affected paths; the resulting change remains confined to the estimator, calibrator, estimate docs, and focused tests (`template/src/pdca_harness/sizing.py:228`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether excluding scheduler-authored sibling edges improves real sizing decisions without obscuring non-convergent splits — mechanics are verified, but operational fitness and the value of the retained signal at `docs/07-crosscutting.md:135` require sign-off. |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T3 Runtime — Decide whether to accept template compatibility only after running the seven root render/update tests with Copier installed — Copier is absent here so all seven skipped; the offline driver suite passed, and the reported 11 failures reproduce only when `PDCA_VERIFY_BASE` leaks into subprocesses expecting it unset at `template/tests/test_verify_base.py:126`.
- [ ] T4 Contribution — Decide whether the PR opener and tracker references satisfy contribution policy after rerunning the bundle's validator — `./scripts/pdca` and the PR/commit artifacts were not supplied, so the asserted green could not be independently reproduced.
- [ ] Validation — fitness-to-purpose — Decide whether excluding scheduler-authored sibling edges improves real sizing decisions without obscuring non-convergent splits — mechanics are verified, but operational fitness and the value of the retained signal at `docs/07-crosscutting.md:135` require sign-off.

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
- Iteration delta (if iterating): Auto-iterate (round 1): Check found implementation-level items only, no architectural judgment required — T3 Runtime — Decide whether to accept template compatibility only after running the seven root render/update tests with Copier installed — Copier is absent here so all seven skipped; the offline driver suite passed, and the reported 11 failures reproduce only when `PDCA_VERIFY_BASE` leaks into subprocesses expecting it unset at `template/tests/test_verify_base.py:126`.; T4 Contribution — Decide whether the PR opener and tracker references satisfy contribution policy after rerunning the bundle's validator — `./scripts/pdca` and the PR/commit artifacts were not supplied, so the asserted green could not be independently reproduced.
- By / date: auto-iterate / 2026-08-08

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
