# Result — issue 458 / split-child-remedy-and-hatch

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: `plan_policy.size_reasons` answers an oversized bundle with ``consider
  `pdca split` first`` (`plan_policy.py:140-141` on the target branch), and its
  `splittable` predicate (`plan_policy.py:134-136`) is true whenever *structural churn
  alone* fired — exactly the readout a split inflates. So every level of a recursion sees
  the same inputs and gives the same advice, and the planner prompt points at `pdca split`
  again. Make the advisory evidence-aware — keyed on the honest signal #457 now exposes
  (`sizing.py:215` `SizeEstimate.sibling_conflicts`, computed at `sizing.py:324-325`) —
  and keep the split recommendation **reachable**. Two failures reproduced against the
  first rejected attempt must not recur:
  1. **Keying on mere presence of lineage asserts something demonstrably false.** Child
     601 of a split of 500, re-planned with four *organic* conflicts and **zero** sibling
     conflicts, scored `oversized` and still printed "driven by inherited/sibling fields;
     prefer building over re-splitting" — contradicting its own evidence. The honest
     predicate is the sibling-conflict *count*, not lineage presence.
  2. **The escape hatch must work with the sizer this project ships.** Re-enabling the
     split remedy only when `est.model_band == sizing.OVERSIZED` is dead config on any
     offline instance: `[leaves.sizer]` ships `mode = "stub"` and `leaves._stub_sizer`
     (`leaves.py:1217-1224`) returns `{"band": "ok"}` unconditionally, so a bundle that
     ever carried lineage could never again be advised to split.
- Success criterion: (i) for a split child whose oversized score **is carried by** sibling conflicts,
      `size_reasons` emits an honest line naming the provenance ("scores large for a split
      child (child N of a split of #X, depth D) — driven by inherited/sibling fields;
      prefer building over re-splitting") and **not** ``consider `pdca split` first``;
  (ii) for a split child with **zero** sibling conflicts — its score carried by organic
      evidence — `size_reasons` emits the ordinary split remedy unchanged, and never the
      inherited-fields line;
  (iii) **(ii) still holds on an instance running the shipped stub sizer**: the test
      exercises the real `_stub_sizer` (`band: "ok"`), not a mock, proving the suppression
      is neither permanent nor conditional on buying a `mode = "command"` sizer;
  (iv) the `before_do=False` branch keeps its existing `iterate-plan` wording
      (`plan_policy.py:142-148`) — a bundle that already has a patch is still told to
      re-plan, not to `pdca split`;
  (v) the same one-sentence provenance context is injected into `leaves._plan_prompt`
      (`leaves.py:524`) and `leaves._split_prompt` (`leaves.py:1226`) when the bundle
      carries lineage, without otherwise rewording the existing split instructions;
  (vi) a bundle with **no** lineage produces byte-identical output to today.
- Repo + branch target: eduralph/pdca-harness @ pdca-integration/main
- Scope (one logical fix) / out of scope: the remedy selection in `template/src/pdca_harness/plan_policy.py`
  (`size_reasons`), the two prompt builders **only** in
  `template/src/pdca_harness/leaves.py` (`_plan_prompt` :524, `_split_prompt` :1226), and
  `docs/07-crosscutting.md` **restricted to `### The process`** (`:36-99` on the target
  branch: the `splittable?` decision nodes in the flowchart at `:50` and `:59`, the remedy
  node at `:52`, and the prose at `:83-98`). / out of scope: `sizing.py` (#457 owns the
  signal; this slice only consumes it), `split.py` and `cli.py` (#459), `docs/07-crosscutting.md`
  `### The estimate` (`:100-189`, #457's) and `### The split` (`:190+`, #459's), and
  making the size guard blocking — it stays advisory for the calibrated reason in its own
  docstring (`plan_policy.py:88-102`: 62% precision, `hold` unimplemented).

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
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

Reviewing issue #458: make split-child size advice evidence-aware, preserve the ordinary split escape hatch, and add lineage context to planner/splitter prompts.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The acceptance boundary is observable across sibling-carried, zero-sibling/stub, built-bundle, prompt, and no-lineage cases, so the intended compatibility and advice outcomes are decidable (`template/tests/test_plan_policy_split_child.py:106`, `template/tests/test_plan_policy_split_child.py:168`, `template/tests/test_plan_policy_split_child.py:189`). |
| C2 Reproduction (red pre-fix) | PASS | An independent base reconstruction kept the 9-test module while reversing production hunks: all 9 executed and the load-bearing old-remedy assertion failed (4 failures, 2 errors), grounding the defect at `template/tests/test_plan_policy_split_child.py:120`. |
| C3 Change | PASS | The patch is confined to the four brief-authorized paths, and the policy decision plus shared prompt context cover the user-visible surfaces without changing sizing ownership (`template/src/pdca_harness/plan_policy.py:189`, `template/src/pdca_harness/leaves.py:524`). |
| C4 Verification (red→green) | PASS | The same independently reconstructed module changed from 9 tests with 4 failures/2 errors to 9/9 passing after the production hunks were restored; the green leg also exercised the real stub-sizer artifact (`template/tests/test_plan_policy_split_child.py:189`). |
| C5 Causal adequacy | NEEDS-HUMAN | Decide whether any excluded sibling conflict truly entails that inherited fields caused the oversized result — the branch suppresses split advice on a nonzero count while the mixed case still has four scored organic conflicts, so a symptom guard may hide genuinely splittable new scope (`template/src/pdca_harness/sizing.py:205`, `template/src/pdca_harness/plan_policy.py:189`, `template/tests/test_plan_policy_split_child.py:148`). |
| T1 Structure | PASS | Decision formatting remains in the policy module and the two prompt builders share one lineage-note helper, keeping the behavioral fork and prompt presentation localized (`template/src/pdca_harness/plan_policy.py:88`, `template/src/pdca_harness/leaves.py:524`). |
| T2 Shape | PASS | `git diff --check`, documentation lint, and a full 22-page site render/link audit all passed, so the scoped flowchart/prose change is structurally publishable (`docs/07-crosscutting.md:50`, `docs/07-crosscutting.md:93`). |
| T3 Runtime | NEEDS-HUMAN | Rerun render and `copier update` compatibility with Copier importable — the driver suite passed, but Copier is absent and all seven root tests skipped, so the asserted template compatibility was not exercised (`tests/test_render_and_run.py:31`, `tests/test_update_compat.py:232`). |
| T4 Contribution | NEEDS-HUMAN | Confirm the eventual commit message and PR description retain the user-impact opener and issue #458 in both artifacts — those contribution artifacts were withheld, so the reported gate PASS cannot be independently reproduced here. |
| T5 Judgment | PASS | Affected-path merged-history and all closed-PR file searches found no competing remedy or test-path precedent; #483 is only the adjacent signal owner, and the target still equals remote `pdca-integration/main` (`template/src/pdca_harness/sizing.py:205`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Judge whether the actual operator wording steers a real split child appropriately — materialize the sibling-conflict case at `template/tests/test_plan_policy_split_child.py:110`, inspect `size_reasons`, remove the sibling IDs, and confirm the recovered ordinary remedy is clear despite the automated 9/9 green. |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] C5 Causal adequacy — Decide whether any excluded sibling conflict truly entails that inherited fields caused the oversized result — the branch suppresses split advice on a nonzero count while the mixed case still has four scored organic conflicts, so a symptom guard may hide genuinely splittable new scope (`template/src/pdca_harness/sizing.py:205`, `template/src/pdca_harness/plan_policy.py:189`, `template/tests/test_plan_policy_split_child.py:148`).
- [x] T3 Runtime — Rerun render and `copier update` compatibility with Copier importable — the driver suite passed, but Copier is absent and all seven root tests skipped, so the asserted template compatibility was not exercised (`tests/test_render_and_run.py:31`, `tests/test_update_compat.py:232`).
- [x] T4 Contribution — Confirm the eventual commit message and PR description retain the user-impact opener and issue #458 in both artifacts — those contribution artifacts were withheld, so the reported gate PASS cannot be independently reproduced here.
- [x] Validation — fitness-to-purpose — Judge whether the actual operator wording steers a real split child appropriately — materialize the sibling-conflict case at `template/tests/test_plan_policy_split_child.py:110`, inspect `size_reasons`, remove the sibling IDs, and confirm the recovered ordinary remedy is clear despite the automated 9/9 green.

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
- By / date: Eduard Ralph / 2026-08-10

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
