# Result — issue 458 / split-child-remedy-and-hatch

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: 
- Success criterion: (i) for a split child whose oversized score **is carried by** sibling conflicts,
      `size_reasons` emits an honest line naming the provenance ("scores large for a split
      child (child N of a split of #X, depth D) — driven by inherited/sibling fields; prefer
      building over re-splitting") and **not** `consider `pdca split` first`;
  (ii) for a split child with **zero** sibling conflicts — its score carried by organic
      evidence — `size_reasons` emits the ordinary split remedy unchanged, and never the
      inherited-fields line;
  (iii) **(ii) still holds on an instance running the shipped stub sizer**: the test
      exercises the real `_stub_sizer` (`band: "ok"`), not a mock, proving the suppression
      is neither permanent nor conditional on buying a `mode = "command"` sizer. The
      previous attempt's only hatch test mocked the stub away and passed on the red leg too,
      so nothing in the evidence would have surfaced the defect;
  (iv) the `before_do=False` branch keeps its existing `iterate-plan` wording
      (`plan_policy.py:142-149`) — a bundle that already has a patch is still told to
      re-plan, not to `pdca split`;
  (v) the same one-sentence provenance context is injected into `leaves._plan_prompt`
      (`leaves.py:524-591`) and `leaves._split_prompt` (`leaves.py:1222-1268`) when the
      bundle carries lineage, without otherwise rewording the existing split instructions;
  (vi) a bundle with **no** lineage produces byte-identical output to today.
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
- T3 runtime: render/update-compat + offline driver suites: pass — == T3: root suite OK, driver suite OK
- T4 PR body has a user-impact opener + tracker id in both artifacts: pass — ./scripts/pdca contribcheck
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Task under review: make split-child size advice distinguish sibling-carried churn from organic oversizing while preserving the shipped stub-sizer escape hatch, post-Do routing, and prompt context.

Target-state caveat: `$PDCA_TARGET` is readable but pinned to `origin/main` and lacks declared prerequisite #457 (open PR #483), so dependency-sensitive findings were grounded on `patch.diff` and exercised in a temporary target-derived folded tree.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 — C1 Spec | PASS | The decision boundary is falsifiable across sibling-carried, organic-only, shipped-stub, post-Do, prompt, and no-lineage cases against the existing remedy split at `template/src/pdca_harness/plan_policy.py:134`. |
| C2 — C2 Reproduction (red pre-fix) | PASS | The target-base production revert retained and ran all 5 tests, with exactly the load-bearing sibling-provenance assertion red at `template/tests/test_plan_policy_split_child.py:94`. |
| C3 — C3 Change | FAIL | Reject until the required #457 base is handled: it makes the sibling fixture patch-only, so the decision at `template/src/pdca_harness/plan_policy.py:134` bypasses the new branch at `template/src/pdca_harness/plan_policy.py:151`. |
| C4 — C4 Verification (red→green) | FAIL | The reconstructed prerequisite-folded green leg ran 5 tests but failed criteria (i) and (iv), including the required iterate-plan assertion at `template/tests/test_plan_policy_split_child.py:168`; the recorded gate green is not reproducible. |
| C5 — C5 Causal adequacy | FAIL | The fix must consume prerequisite #457's exposed sibling-conflict signal before remedy selection; re-reading lineage only after `splittable` is chosen leaves the actual stacked failure intact at `template/src/pdca_harness/plan_policy.py:138`. |
| T1 — T1 Structure | FAIL | The prerequisite establishes one sibling-count source, but this policy re-derives it from lineage and brief data at `template/src/pdca_harness/plan_policy.py:151`, creating drift and the observed integration break. |
| T2 — T2 Shape | PASS | Docs lint, `git diff --check`, and the 22-page render/link audit reran cleanly; the edited flow remains structurally valid at `docs/07-crosscutting.md:50`. |
| T3 — T3 Runtime | NEEDS-HUMAN | Decide whether to accept runtime compatibility without the required Copier exercise — Copier is absent, so all 7 render/update root tests skipped via `tests/test_render_and_run.py:31`, while the driver suite completed 1679 tests with 2 skips. |
| T4 — T4 Contribution | NEEDS-HUMAN | Decide whether the recorded contribution pass is sufficient — this reviewer received neither commit message nor PR description, so the configured two-artifact check at `template/pdca.toml.jinja:985` could not be independently rerun. |
| T5 — T5 Judgment | FAIL | Affected-path history found the declared open prerequisite (#483) and no unmerged closed duplicate, but the reconstructed stack fails its own focused tests, so the change is not ready to advance (`template/tests/test_plan_policy_split_child.py:82`). |
| V — Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the eventual sibling-provenance remedy matches operator intent — it changes whether an oversized split child is built or split again, a workflow consequence represented at `docs/07-crosscutting.md:93`. |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T3 — T3 Runtime — Decide whether to accept runtime compatibility without the required Copier exercise — Copier is absent, so all 7 render/update root tests skipped via `tests/test_render_and_run.py:31`, while the driver suite completed 1679 tests with 2 skips.
- [ ] T4 — T4 Contribution — Decide whether the recorded contribution pass is sufficient — this reviewer received neither commit message nor PR description, so the configured two-artifact check at `template/pdca.toml.jinja:985` could not be independently rerun.
- [ ] V — Validation — fitness-to-purpose — Decide whether the eventual sibling-provenance remedy matches operator intent — it changes whether an oversized split child is built or split again, a workflow consequence represented at `docs/07-crosscutting.md:93`.

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
- Iteration delta (if iterating): Rebuild and verify against the real base: pdca-integration/main, which now carries prerequisite #457. The recorded gate green was earned against origin/main without #457; the reviewer's #457-folded tree showed criteria (i) and (iv) fail when stacked — the sibling fixture becomes patch-only and the remedy decision at plan_policy.py:134 bypasses the new branch at :151. Cause: the patch re-derives the sibling-conflict count from lineage + brief instead of consuming the single sibling-conflict signal #457 exposes. Consume #457's exposed signal as the one source before remedy selection; earn the red→green on the #457-carrying base.
- By / date: Eduard Ralph / 2026-08-10

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
