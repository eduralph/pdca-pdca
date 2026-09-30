Review of issue #541: prevent dead-attempt artifacts from being harvested as live work and prevent completed reports that quote status markers from being misclassified as placeholders.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The contract makes closure positive and position-bound while leaving absence inert, so legacy and non-cooperating leaves retain their existing classification (`template/src/pdca_harness/assemble.py:101`). |
| C2 Reproduction (red pre-fix) | PASS | With the new oracle retained and production changes stashed, the independent run failed with 12 failures and 5 errors at the three-reader reproduction; restoring production passed all 23 tests (`template/tests/test_attempt_harvest.py:561`). |
| C3 Change | PASS | Attribution has one owner used by all three harvest sites, and classification changes once at the shared reader, avoiding divergent per-site decisions (`template/src/pdca_harness/leaves.py:809`, `template/src/pdca_harness/assemble.py:126`). |
| C4 Verification (red→green) | PASS | Independent red→green was reproduced locally, the patch reverse-checks cleanly, and the focused post-fix oracle passes 23/23 (`template/tests/test_attempt_harvest.py:267`). |
| C5 Causal adequacy | PASS | Failed-attempt residue is withdrawn before retry and a completed artifact is recognized by an exact final-line stamp; this removes both attribution causes without a capability probe or symptom-only fallback (`template/src/pdca_harness/leaves.py:746`, `template/src/pdca_harness/assemble.py:138`). |
| T1 Structure | PASS | The scoped production files plus one net-new regression suite form one coherent change, and all three call sites route through the sole harvest implementation (`template/src/pdca_harness/leaves.py:2945`, `template/src/pdca_harness/leaves.py:3311`, `template/src/pdca_harness/leaves.py:3616`). |
| T2 Shape | PASS | Independent diff/compile checks and docs lint/render/link audit are clean, while one loop pins all prompt, stub, and placeholder trailer shapes (`template/tests/test_attempt_harvest.py:669`). |
| T3 Runtime | PASS | The independent full offline suite passed 1,826 tests with two expected skips, including the unmodified legacy leaf-status contract and the 23 new production-path cases (`template/tests/test_attempt_harvest.py:267`). |
| T4 Contribution | N/A | Contribution artifacts are intentionally drafted after Check; the deferred gate reports that its substantive PR-description audit reruns at publish. |
| T5 Judgment | NEEDS-HUMAN | Confirm that prerequisite #540 will be published ahead and that the affected-path prior-art search remains collision-free — this synthetic one-commit target has no remotes or rejected-work archives, so ordering and closed/in-flight overlap cannot be mechanically settled here. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether cooperative final-line closure with inert absence is operationally fit — a finished leaf that omits the trailer and quotes a recognized status remains conservatively subject to legacy misclassification (`template/src/pdca_harness/assemble.py:107`). |

<!-- pdca:leaf-complete -->
