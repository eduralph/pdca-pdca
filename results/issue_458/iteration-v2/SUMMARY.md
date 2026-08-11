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
- C4 fix verified: bundle test red pre-fix, green post-fix: fail — C4 FAIL: bundle test red WITH the fix applied
- C5 Causal adequacy: none — reviewer + human sign-off

## 4. Conformance (Check — stack)
- T1 Structure: none — (no gate configured)
- T2 shape: docs lint + site render link audit: pass — render_site: link audit OK
- T3 runtime: render/update-compat + offline driver suites: fail — == T3: root suite FAILED (rc 1), driver suite FAILED (rc 1)
- T4 PR body has a user-impact opener + tracker id in both artifacts: pass — ./scripts/pdca contribcheck
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Task under review: make split-child size advice distinguish inherited sibling-conflict evidence from organic scope, while preserving the ordinary split escape hatch, built-bundle routing, prompt context, and unsplit output.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The acceptance decision is explicit for sibling-only, organic-only, shipped-stub, built, prompt, and no-lineage cases, with independently observable expectations at `template/tests/test_plan_policy_split_child.py:106`. |
| C2 Reproduction (red pre-fix) | PASS | On prerequisite ref `b4c924d` with the production hunks stashed, all 9 tests executed and the load-bearing ordinary-remedy assertion failed at `template/tests/test_plan_policy_split_child.py:122`. |
| C3 Change | PASS | The patch stays within the declared policy/prompt/process-doc scope, and the decision boundary leaves the built-bundle `iterate-plan` route intact at `template/src/pdca_harness/plan_policy.py:203`. |
| C4 Verification (red→green) | PASS | Against target-local prerequisite ref `b4c924d`, the same 9-test module was red with production stashed and green after stash-pop; the supplied target's missing #457 field is a stale-target caveat, not contrary patch evidence (`template/tests/test_plan_policy_split_child.py:117`). |
| C5 Causal adequacy | PASS | The remedy consumes #457's sibling-conflict count directly instead of lineage presence or model band, and introduces no optional-capability probe or try/fallback guard (`template/src/pdca_harness/plan_policy.py:189`). |
| T1 Structure | PASS | One shared prompt-note helper and one policy fork keep the provenance rule single-sourced without changing unrelated runtime modules (`template/src/pdca_harness/leaves.py:524`). |
| T2 Shape | PASS | Docs lint and the rendered-site link audit both passed, and the process diagram preserves the distinct pre-Do and built-bundle routes at `docs/07-crosscutting.md:50`. |
| T3 Runtime | PASS | The stacked tree passed 1,700 driver tests (2 expected skips) and all 7 render/update-compat tests under a real Copier environment, so the declared template dependency was exercised rather than skipped (`template/tests/test_plan_policy_split_child.py:189`). |
| T4 Contribution | NEEDS-HUMAN | Confirm the eventual commit/PR artifacts contain the user-impact opener and tracker id — those artifacts were not supplied, so the recorded `contribcheck` pass cannot be independently reproduced and contribution policy could still reject publication. |
| T5 Judgment | NEEDS-HUMAN | Decide whether the rejected iteration contains affected-path prior art that this patch still duplicates — merged history and closed-PR path searches ran, but the withheld `iteration-v1` artifacts are not mechanically inspectable, so recurrence risk cannot be fully settled. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether suppressing re-split whenever at least one sibling conflict remains is operationally preferable even with four organic conflicts — that policy choice controls whether mixed-evidence children can be under-split (`template/tests/test_plan_policy_split_child.py:148`). |

Target-state caveat: `$PDCA_TARGET` is at `36300ee`, the parent of prerequisite `b4c924d` (#457), so its direct run errors on the absent `SizeEstimate.sibling_conflicts`; verification used the target-local prerequisite ref plus `patch.diff`, and did not write to the target.

Prior-art investigation: merged history was checked with each affected path against `origin/main`; closed-PR path searches returned 2 hits for `plan_policy.py`, 15 for `leaves.py`, 8 for `docs/07-crosscutting.md`, and 0 for the new test path. GitHub has no PR for open issue #458, leaving the withheld rejected iteration as the unresolved portion recorded in T5.


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T4 Contribution — Confirm the eventual commit/PR artifacts contain the user-impact opener and tracker id — those artifacts were not supplied, so the recorded `contribcheck` pass cannot be independently reproduced and contribution policy could still reject publication.
- [ ] T5 Judgment — Decide whether the rejected iteration contains affected-path prior art that this patch still duplicates — merged history and closed-PR path searches ran, but the withheld `iteration-v1` artifacts are not mechanically inspectable, so recurrence risk cannot be fully settled.
- [ ] Validation — fitness-to-purpose — Decide whether suppressing re-split whenever at least one sibling conflict remains is operationally preferable even with four organic conflicts — that policy choice controls whether mixed-evidence children can be under-split (`template/tests/test_plan_policy_split_child.py:148`).
- [ ] C4 fix verified: bundle test red pre-fix, green post-fix FAILED (gating) — C4 FAIL: bundle test red WITH the fix applied
- [ ] external dependency: prerequisite #457 folded into the C4 base — this bundle has no `stack-base` marker, so `worktree._target` / `gates.py:379-397` reset the lane worktree to `origin/main`, where `SizeEstimate.sibling_conflicts` does not exist and the green leg dies with `AttributeError: 'SizeEstimate' object has no attribute 'sibling_conflicts'` (verified on an `origin/main` tree with this patch applied: `Ran 8 tests … FAILED (errors=5)`). The patch itself applies cleanly there (`git apply --check` rc=0). Red→green was earned on `origin/fix/457-sizing-ignores-sibling-conflicts` (= `origin/pdca-integration/main` + #457, PR #483 still open). Fix before re-gating: merge PR #483 into `pdca-integration/main` and re-fetch, **or** stamp the marker the wave driver would have written — `printf 'fix/457-sizing-ignores-sibling-conflicts\n' > results/issue_458/stack-base` — then re-run `pdca-pdca gates 458`.

## 7. Proven / not proven
- Proven by which oracle: gates overall = fail (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: iterated-to-Plan
- Iteration delta (if iterating): Patch content verified sound (reviewer C1-C5/T1-T3 PASS on b4c924d = pdca-integration/main + #457); rejected because the brief is wrong, not the code. The brief declares `Repo + branch target: ... @ main`, but the change hard-depends on #457 (`SizeEstimate.sibling_conflicts`), which is on pdca-integration/main (PR #483 merged 2026-08-10) and NOT on main — so the C4 gate verified against a base that cannot carry the fix, and publish would open the PR against the wrong branch. Re-plan must: (1) declare the branch target / PR base as pdca-integration/main; (2) record the #457 dependency so the wave driver writes `stack-base` and both C4 and publish resolve the right base; (3) carry the iteration-2 patch and its 9-test module (real `_stub_sizer`, no mocks) forward as the reference implementation — do not redesign; re-house the same change under the corrected brief.
- By / date: Eduard Ralph / 2026-08-10

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
