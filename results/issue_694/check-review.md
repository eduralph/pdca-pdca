Review issue #694: make re-issued conflict holds name the responsible finished bundles and give actionable recovery advice instead of telling operators to reopen an already-open PR.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The partner/base/unaccounted-work cases and unchanged hold behavior are falsifiable and bounded; brief.md:10, brief.md:23; target/template/tests/test_flow_reissue_after_conflict_hold.py:210. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing the production fix while retaining the new tests reproduces 22 assertion failures, including the incorrect reopen/cross-wave advice; review-red.log:259; target/template/tests/test_flow_reissue_after_conflict_hold.py:210. |
| C3 Change | PASS | The four affected files address carry diagnostics, shared recovery wording, documentation and regression coverage; merge eligibility remains unchanged; target/template/src/pdca_harness/flow.py:1189, target/template/src/pdca_harness/integrate.py:632. |
| C4 Verification (red→green) | PASS | Independently reproduced 22 red tests before the fix and 22 green after restoring it; this verifies the supplied cases, not the additional C5 case; review-red.log:259, review-green.log:3; gate-logs/C4-verify.log:10. |
| C5 Causal adequacy | NEEDS-HUMAN [impl] | Correct recovery advice when a later carried bundle removes the conflict — current attribution still demands a declaration/rebuild although a plain re-issue completes; target/template/src/pdca_harness/integrate.py:1231; review-final-line.log:1. |
| T1 Structure | PASS | Attribution runs under the existing fold lock and trial merges restore the integration branch; presentation stays in flow and in-run reporting shares its recovery wording; target/template/src/pdca_harness/integrate.py:640, target/template/src/pdca_harness/integrate.py:1341, target/template/src/pdca_harness/flow.py:1004. |
| T2 Shape | PASS | Independent docs lint, 22-page rendering/link audit and whitespace check pass; frozen host-CI evidence agrees; review-scanners.log:1, gate-logs/host-ci-docs.log:10; target/docs/07-crosscutting.md:767. |
| T3 Runtime | PASS | Independent driver suite passes 2,513 tests with two skips; frozen root suite passes 24 tests, while this interpreter lacks Copier (host caveat, not a patch defect); review-suite.log:1817, gate-logs/T3-suite.log:54, review-root.log:6. |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; their substantive audit must rerun at publish; gate-logs/T4-contribution.log:10. |
| T5 Judgment | NEEDS-HUMAN | Confirm the path-scoped merged and closed/rejected prior-art account before sign-off — the brief records it, but the supplied synthetic history and absent PR records cannot independently substantiate it; brief.md:28, review-prior-art.log:1. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the recovery instructions are sufficient for stack-mode operators after the C5 correction — real-git tests establish observable behavior, while operational suitability remains a human decision; target/docs/07-crosscutting.md:767, target/template/src/pdca_harness/flow.py:1017. |

**C5 finding — unnecessary rebuild after a later merge resolves the conflict (P2).** At target/template/src/pdca_harness/integrate.py:1231, `_clash` returns `batch` when a pairwise partner trial conflicts, before testing the branch against the final line at :1234. A historical pairwise clash can therefore override the fact that the final line accepts the branch. This also contradicts the retry behavior described at target/docs/07-crosscutting.md:792.

I exercised the production flow with real git using the supplied fixture: the base has `shared.txt = x`; finished 10 writes `ten`; finished 11 writes `eleven`; finished 12 is cut from 10 and restores `x`; 20 depends on 11. The carry merges 10, skips 11, then merges 12. Nothing is taken back off the line. Its pushed tree has `x`, yet the diagnostic says 11 does not merge cleanly and proposes `Conflicts with: 10` plus a rebuild. Without changing a brief or rebuilding any bundle, a plain re-issue carries 11 and completes 20. The observed output is in review-final-line.log:1; the successful re-issue is at :3. The additional assertion requiring retry advice fails at :17.

The correction should distinguish conflicts that remain on the final line from ones removed by a later carried merge before selecting the declaration/rebuild remedy, while preserving the separately tested removed-bundle cases. Add this case alongside target/template/tests/test_flow_reissue_after_conflict_hold.py:649; its existing later-merge case starts from unaccounted-for work, so it does not exercise the early return for a named partner. The brief pins pairwise attribution, but the demonstrated defect is the recovery advice and present-tense claim about the final line, not the historical observation that 10 and 11 conflict.

Reproduce from the review cwd with:

```bash
TMPDIR="$PWD/review-tmp" PYTHONDONTWRITEBYTECODE=1 python3 review-final-line.py
```

**Evidence and limits.** The disposable target contains the patch and its prerequisite base; no stale-target limitation was encountered. The production changes were stashed and restored, and a final reverse-apply check confirms the supplied patch remains intact. The new tests genuinely call production code: the independent import scanner passes at review-scanners.log:10, and real git exhibits the forbidden failure in the red leg. Python and git were exercised directly; the PR-state stub is the one specified by the brief and does not prevent the conflict from occurring. No capability probe guarding a load-time side effect was introduced.

The instance-scoped wrappers were adjudicated using their frozen logs and available underlying commands. Local root-suite execution exits 77 because Copier is not importable, rather than falsely claiming those tests ran. gate-logs/T3-suite.log:54 records the actual successful 24-test root run, so the local limitation does not establish an unmet dependency in the round's evidence. Both frozen documentation checks show successful rendering and link audits, independently reproduced here. T4 remains deferred to publish, not a missing-evidence finding.

The affected-path history investigation is recorded in review-prior-art.log:1: the scratch repository has only its synthetic base commit and no remotes. The brief names merged history for both production files and closed-unmerged PRs touching those files and the documentation, but the underlying history/PR records are not supplied. No other checkout was consulted. The available INTEGRATION template has only a TODO for project-specific human-only items (target/template/docs/INTEGRATION.md.jinja:80), so it supplies no additional enumerated decision.

<!-- pdca:leaf-complete -->
