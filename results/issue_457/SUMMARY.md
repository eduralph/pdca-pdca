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

Review task: stop split-generated sibling conflicts from inflating sizing churn while preserving organic/no-lineage behavior and exposing the excluded count to the estimator and calibrator.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | Acceptance is deterministic: the intended sibling exclusion, unchanged organic/no-lineage behavior, exposed count, and estimator/calibrator agreement are explicit and independently testable (`docs/07-crosscutting.md:129`). |
| C2 Reproduction (red pre-fix) | PASS | The decision rests on a genuine pre-fix symptom: with only production hunks reverted, 17 tests ran and the materialised child scored 9 against the cutoff of 7, failing the below-cutoff assertion (`template/tests/test_sizing_split_child.py:163`). |
| C3 Change | PASS | The scoped change is complete and preserves the failure contract: only string sibling ids are eligible for exclusion, while malformed lineage abstains and organic conflicts remain scored (`template/src/pdca_harness/sizing.py:277`, `template/src/pdca_harness/sizing.py:324`). |
| C4 Verification (red→green) | PASS | Acceptance has independently reproduced red→green evidence: the reverted-production copy failed with 10 failures/20 errors and the target passed all 17 focused tests; reverse-apply and Python compile checks also passed (`template/tests/test_sizing_split_child.py:151`). |
| C5 Causal adequacy | PASS | The root-cause choice is adequate because it subtracts only lineage-proven sibling ids from the weighted input and leaves non-sibling or unusable ids on the original scoring path; no capability-probe/runtime-guard smell is present (`template/src/pdca_harness/sizing.py:317`). |
| T1 Structure | PASS | The scope is coherent: the patch reverse-checks against the target, changes only the four allowed artifacts, and shares one exclusion helper between runtime and calibration rather than duplicating the rule (`template/scripts/size-calibrate:83`). |
| T2 Shape | PASS | Documentation shape is acceptable: the independent docs linter passed and a 22-page `render_site --check` build reported a clean link audit, grounding the new semantics where the weights are explained (`docs/07-crosscutting.md:118`). |
| T3 Runtime | PASS | The recorded red is a host-isolation caveat, not patch behavior: Copier 9.17.1 ran all seven render/update tests green and the full offline driver suite returned 0; the 11 failures reproduce only when `PDCA_VERIFY_BASE` is deliberately leaked into tests that require it unset (`template/tests/test_verify_base.py:126`). |
| T4 Contribution | NEEDS-HUMAN | Decide whether the PR opener, closing tracker reference, signed-off conventional commit, and validator result satisfy contribution policy — neither contribution artifacts nor the asserted `./scripts/pdca contribcheck` executable were supplied for independent rerun (`AGENTS.md:21`). |
| T5 Judgment | NEEDS-HUMAN | Decide whether closed/rejected work contains conflicting prior art — the affected-path `git log --all` showed merged lineage and earlier sizing/calibration work but no duplicate sibling-exclusion change, while closed/rejected tracker history was unavailable and therefore remains mechanically unsettled (`template/src/pdca_harness/sizing.py:238`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether treating split-authored sibling edges as non-organic matches the real corpus and preserves useful convergence judgment — red→green tests prove the mechanics, but operational calibration fitness remains a human sign-off decision (`docs/07-crosscutting.md:160`). |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T4 Contribution — Decide whether the PR opener, closing tracker reference, signed-off conventional commit, and validator result satisfy contribution policy — neither contribution artifacts nor the asserted `./scripts/pdca contribcheck` executable were supplied for independent rerun (`AGENTS.md:21`).
- [x] T5 Judgment — Decide whether closed/rejected work contains conflicting prior art — the affected-path `git log --all` showed merged lineage and earlier sizing/calibration work but no duplicate sibling-exclusion change, while closed/rejected tracker history was unavailable and therefore remains mechanically unsettled (`template/src/pdca_harness/sizing.py:238`).
- [x] Validation — fitness-to-purpose — Decide whether treating split-authored sibling edges as non-organic matches the real corpus and preserves useful convergence judgment — red→green tests prove the mechanics, but operational calibration fitness remains a human sign-off decision (`docs/07-crosscutting.md:160`).
- [x] size backstop — this slice is behaving oversized: 2 round(s) already spent (threshold 2). Recommend answering `iterate-plan` at sign-off and authoring the split in the re-plan (`pdca split`), rather than `iterate-do`: a slice that is too big yields implementation-shaped findings every round, and splitting authors briefs, which is Plan's beat.

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
- By / date: Eduard Ralph / 2026-08-08

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
