Review #738: hold a bundle whose own base cannot be built, continue independent work, and preserve run-level stops for a broken shared worktree or a rewrite at the next fold.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The isolation boundary, exit-code precedence, and three carry-forward corrections are explicit and testable (brief.md:17; brief.md:35). |
| C2 Reproduction (red pre-fix) | PASS | Reverting only production reproduces STOPPING on the moved-main case and 18 assertion failures across 56 collected tests; both shared-worktree guards pass (review-red.log:68; review-red.log:240; template/tests/test_flow_bundle_base_holds.py:301). |
| C3 Change | PASS | The change respects the specified local-versus-shared failure boundary and retains existing rewrite exit-1 expectations (template/src/pdca_harness/flow.py:1050; template/src/pdca_harness/cli.py:741; template/tests/test_integrate_carried_rewrite_late.py:323). |
| C4 Verification (red→green) | PASS | Independent production-only stash → red (18 failures) → restore → green (56 passing tests) confirms the claimed transition, including the carry-forward cases (review-red.log:242; review-green.log:59; template/tests/test_flow_bundle_base_holds.py:382; template/tests/test_flow_bundle_base_holds.py:587; template/tests/test_flow_bundle_base_holds.py:624). |
| C5 Causal adequacy | PASS | Real-git base-build failures reach the production exception boundary; independent work completes, affected edges remain unbuilt, and late rewrites retain failure precedence (template/tests/test_flow_bundle_base_holds.py:411; template/tests/test_flow_bundle_base_holds.py:499; template/tests/test_flow_bundle_base_holds.py:520; template/src/pdca_harness/flow.py:3036). |
| T1 Structure | PASS | Existing scheduling, late-rewrite reporting, and the single CLI exit-code rule carry the new hold through the established flow (template/src/pdca_harness/flow.py:2807; template/src/pdca_harness/flow.py:3044; template/src/pdca_harness/cli.py:707). |
| T2 Shape | PASS | Independently reran diff whitespace check, production-import scanner, docs lint, and 22-page site/link audit successfully; frozen host-CI evidence also shows clean lint and links (gate-logs/C5-prod-path.log:10; gate-logs/host-ci-docs.log:11). |
| T3 Runtime | PASS | Independent driver suite passed 2,610 tests with 2 skips; frozen root-suite evidence explicitly shows 24 render/update tests passing, including actual rendering and compatibility checks (review-suite.log:1817; gate-logs/T3-suite.log:38; gate-logs/T3-suite.log:54). |
| T4 Contribution | N/A | Contribution artifacts are drafted after Check; this deferred row owes its substantive audit to the mandatory publish-time rerun (gate-logs/T4-contribution.log:10). |
| T5 Judgment | NEEDS-HUMAN | Confirm merged-history and closed/rejected-work searches by affected file path — the supplied target has one synthetic base commit, no remote, and no prior-attempt archive, so the issue list alone cannot establish that audit (review-prior-art.log:1; brief.md:27). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Confirm that the offline real-git scenarios and cause-specific recovery instructions suffice for production batch operation — operators must distinguish held-only exit 3 from unfinished dependent or surviving-rewrite exit 1 (template/src/pdca_harness/cli.py:711; template/tests/test_flow_bundle_base_holds.py:411; template/tests/test_flow_bundle_base_holds.py:547). |

All source citations above resolve inside `$PDCA_TARGET`. Its five modified existing-file preimages match the patch's index hashes, grounding the review on the intended base.

The independent red/green command was `PYTHONPATH=src python3 -m unittest -v tests.test_flow_bundle_base_holds tests.test_flow_dependency_scoped_bases tests.test_integrate_carried_rewrite_late`, run from the target's `template/` directory. Only the three production files were stashed; all shipped tests remained present. The restored production patch passed all 56 tests, and the subsequent full driver discovery passed. Temporary files were confined beneath this review sandbox.

The three carry-forward outcomes were exercised: an entirely held wave emits no next-fold warning; a fetch hold is printed before a later shared-worktree STOPPING line; and failure to restore the base branch raises the real `_LineBroken` and stops without holding that bundle (template/tests/test_flow_bundle_base_holds.py:382; template/tests/test_flow_bundle_base_holds.py:624; template/tests/test_flow_bundle_base_holds.py:587).

Instance-root gate wrappers are unavailable in this target. Their frozen logs were read; target-side validators and the driver suite were rerun directly. The local interpreter lacks `copier`, so root render/update results rely on the frozen gate's explicit passing test output, not a local rerun (gate-logs/T3-suite.log:38). The supplied integration document is an unrendered template with a TODO for additional human-only items (template/docs/INTEGRATION.md.jinja:80).

No implementation defect was identified. The two NEEDS-HUMAN rows above are advisory sign-off obligations.

<!-- pdca:leaf-complete -->
