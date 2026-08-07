# Result — issue 315 / prepublish-review-stage

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: a native pre-publish review stage in `publish.py` — N parallel review passes
  over the bundle's full diff, unioned/deduped, with BUG-class findings re-entering Do
  under the existing bounded iterate budgets — so the serialized-review-depth churn
  measured on external reviews (~1 new real finding per re-review round; extreme case 13
  rounds on one PR) is paid *before* the draft PR opens, not after.
- Success criterion: with the stage enabled: (a) publish runs N (configurable,
  default 3) review passes over the bundle's diff between the T4 gate passing and the
  first git step; (b) findings are unioned and deduped, and classes the instance rubric
  explicitly rejects are dropped; (c) BUG-class findings feed the brief's carry-forward
  block and trigger a bounded re-entry to Do (the `autoiterate.py` budget shape — never
  open-ended); (d) publish proceeds only when a pass completes with every finding fixed
  or recorded-rejected; (e) stage disabled (the default) ⇒ publish byte-identical to
  today. Demonstrable by C4-verify with stubbed review leaves
  (`PDCA_LEAVES_MODE=stub`-style stubbing as the existing leaf tests do).
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: the pre-publish review stage in the engine: N parallel passes via the
  existing family machinery (`codex exec --sandbox read-only` for a codex reviewer —
  reuse `leaves.run_review`'s invocation path, do not build a second model-runner),
  union+dedup, rubric-rejected-class drop, bounded BUG re-entry via the
  carry-forward + auto-iterate budget shape, and the triaged-fixpoint proceed condition.
  Config-gated, off by default. / out of scope: the rubric *key/format* itself (the
  companion issue owns it — where no rubric is configured, skip the rubric-drop step);
  ingesting post-publish external PR reviews (#316); any change to the wyrd stopgap
  (`scripts/review-branch`).

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
- T3 runtime: render/update-compat + offline driver suites: fail — /tmp/tmp0ma641kh/results/issue_500/split-proposal.md
- T4 PR body has a user-impact opener + tracker id in both artifacts: pass — pdca-pdca contribcheck
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Task under review: add an optional pre-publish review stage to `publish.py` that runs configurable parallel reviewer passes before any git/PR publish step and boundedly re-enters Do for BUG-class findings.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The decision is whether the patch targets the requested publish-boundary stage; the implementation is wired after T4 and before git mechanics at `template/src/pdca_harness/publish.py:222`, with config parsed at `template/src/pdca_harness/config.py:635`. |
| C2 Reproduction (red pre-fix) | PASS | The decision is whether the old code lacked the stage; reversing `patch.diff` made `tests.test_prepublish_review` unavailable/red, while the applied patch's test states the missing seam at `template/tests/test_prepublish_review.py:23`. |
| C3 Change | PASS | The decision is whether one coherent feature was added without unrelated churn; the diff adds config, reviewer-pass leaf reuse, publish-stage orchestration, docs, and focused tests around `template/src/pdca_harness/publish.py:886`. |
| C4 Verification (red→green) | NEEDS-HUMAN | The exact C4 gate is not independently reproducible here: `template/engine/scripts/run-verify.sh` is a skeleton that exits 1, although direct reversal/reapply ran red then 15 green `unittest` cases from `template/tests/test_prepublish_review.py:185`. |
| C5 Causal adequacy | NEEDS-HUMAN | The decision owed is whether the added `getattr` capability probe should remain or the config invariant should make it unnecessary; the probe is at `template/src/pdca_harness/publish.py:800` and triggers the C5 symptom-guard review. |
| T1 Structure | PASS | The decision is whether the feature sits in existing ownership boundaries; reviewer invocation is shared through `template/src/pdca_harness/leaves.py:1788` and publish policy stays in `template/src/pdca_harness/publish.py:886`. |
| T2 Shape | NEEDS-HUMAN | The docs/shape gate could not be rerun from this checkout because the asserted `run-docs-check.sh` wrapper is absent; inspect the generated docs/check environment before relying on the claimed T2 pass. |
| T3 Runtime | NEEDS-HUMAN | The runtime suite row is already red in `check-gates.json`, but I could not reproduce the suite because `run-suite.sh` is absent and `python3 -m pytest` is unavailable; `compileall` passed for `template/src` and `template/tests/test_prepublish_review.py`. |
| T4 Contribution | NEEDS-HUMAN | The decision owed is whether the contribution artifacts satisfy the project contribcheck; the asserted `pdca-pdca contribcheck` pass was not runnable from the provided artifacts, so the green row remains provisional. |
| T5 Judgment | NEEDS-HUMAN | The decision owed is whether to accept with provisional wrapper evidence and the C5 probe question unresolved; affected-file prior art checked `origin/main -- template/src/pdca_harness/publish.py` and no `#315` commit was found. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Human sign-off must decide whether the configured review stage is fit for the project despite stubbed/offline reviewer evidence and unavailable live wrapper gates. |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] C4 Verification (red→green) — The exact C4 gate is not independently reproducible here: `template/engine/scripts/run-verify.sh` is a skeleton that exits 1, although direct reversal/reapply ran red then 15 green `unittest` cases from `template/tests/test_prepublish_review.py:185`.
- [ ] C5 Causal adequacy — The decision owed is whether the added `getattr` capability probe should remain or the config invariant should make it unnecessary; the probe is at `template/src/pdca_harness/publish.py:800` and triggers the C5 symptom-guard review.
- [ ] T2 Shape — The docs/shape gate could not be rerun from this checkout because the asserted `run-docs-check.sh` wrapper is absent; inspect the generated docs/check environment before relying on the claimed T2 pass.
- [ ] T3 Runtime — The runtime suite row is already red in `check-gates.json`, but I could not reproduce the suite because `run-suite.sh` is absent and `python3 -m pytest` is unavailable; `compileall` passed for `template/src` and `template/tests/test_prepublish_review.py`.
- [ ] T4 Contribution — The decision owed is whether the contribution artifacts satisfy the project contribcheck; the asserted `pdca-pdca contribcheck` pass was not runnable from the provided artifacts, so the green row remains provisional.
- [ ] T5 Judgment — The decision owed is whether to accept with provisional wrapper evidence and the C5 probe question unresolved; affected-file prior art checked `origin/main -- template/src/pdca_harness/publish.py` and no `#315` commit was found.
- [ ] Validation — fitness-to-purpose — Human sign-off must decide whether the configured review stage is fit for the project despite stubbed/offline reviewer evidence and unavailable live wrapper gates.

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: discontinued
- Iteration delta (if iterating):
- By / date: Eduard Ralph / 2026-08-01

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
