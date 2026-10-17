Review dependency-scoped stack bases so a bundle's PR carries its declared prerequisites without unrelated earlier-wave work, and rewrite warnings identify the affected bases and PRs.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The isolation invariant, four fallback seams, rewrite remedies, and exclusions are explicit and falsifiable with offline git; brief.md:3, brief.md:9, brief.md:18. |
| C2 Reproduction (red pre-fix) | PASS | With only the production fix stashed, 21 of 25 new tests fail; the original case finds both unrelated Z commits on fix/B, demonstrating the stated contamination; review-red.log:103, template/tests/test_flow_dependency_scoped_bases.py:263. |
| C3 Change | PASS | The changes stay within base selection, rewrite accounting, and supporting tests; the protected merge-check function is unchanged and only the permitted helper changes in its suite; review-scope.log:1, template/tests/test_flow_merged_prereq_on_line.py:191. |
| C4 Verification (red→green) | PASS | Restoring the fix makes all 220 tests in the eight changed suites pass after the independently observed red leg; production diff restoration matches patch.diff exactly; review-red.log:397, review-green.log:472, gate-logs/C4-verify.log:2840. |
| C5 Causal adequacy | PASS | Selecting the declared closure removes scheduling-derived contamination; real-git tests cover transitivity, patchless intermediates, conflict ordering, seams, and each PR's lost head; no optional-capability probe masks a load-time cause; template/src/pdca_harness/flow.py:913, template/tests/test_flow_dependency_scoped_bases.py:289, template/tests/test_flow_dependency_scoped_bases.py:743. |
| T1 Structure | PASS | Base planning reuses the existing git primitive, with explicit records for each base and line-cut PR; target selection and publication remain in their existing modules; template/src/pdca_harness/flow.py:961, template/src/pdca_harness/integrate.py:1050. |
| T2 Shape | PASS | Independent docs lint and the 22-page render/link audit pass, as does diff whitespace validation; frozen host-CI evidence agrees; review-docs-lint.log:1, review-docs-render.log:3, review-scope.log:3, gate-logs/host-ci-docs.log:10. |
| T3 Runtime | PASS | Independent offline discovery passes 2,581 tests with two skips; the frozen root-suite log also shows all 24 render/update tests passing; review-runtime.log:1817, gate-logs/T3-suite.log:54. |
| T4 Contribution | N/A | Contribution artifacts are intentionally absent during Check; the deferred gate explicitly requires the substantive contribution audit at publish; gate-logs/T4-contribution.log:10. |
| T5 Judgment | NEEDS-HUMAN | Confirm merged-history and closed/rejected-work coverage by affected flow.py and integrate.py paths — this snapshot has one synthetic commit, no remote, and none of the referenced rejected-attempt artifacts, so the brief's prior-art account cannot be independently confirmed; review-prior-art.log:1, review-prior-art.log:6, brief.md:24. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Accept the deliberately retained line-base fallbacks and confirm prerequisite PR #726 lands first — this fix isolates the in-batch cases, while the brief explicitly leaves carried/resumed and legacy seams on the shared line; brief.md:9, brief.md:13, template/src/pdca_harness/flow.py:1004. |

Source citations beginning with `template/` are relative to `$PDCA_TARGET`, the disposable patched copy of the expected fcae4aa base. The production files were stashed for the red leg and restored before the green leg; no implementation edits were made.

The production-path scanner was rerun successfully (`review-production-path.log:1`). The instance-scoped gate wrappers are not present here; their captured commands and outcomes were read from all six frozen logs. Local copier is unavailable, so root render/update coverage is supported by the frozen execution log, which shows those tests actually ran and passed, rather than by a local rerun. Python and real git exercised the regression and runtime tests without tool aliases or shims.

<!-- pdca:leaf-complete -->
