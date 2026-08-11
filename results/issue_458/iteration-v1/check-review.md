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
