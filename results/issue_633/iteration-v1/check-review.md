Review issue #633: stop an in-run stack fold from carrying a rewritten PR branch while preserving fast-forward updates, pre-wave carry, and deleted-branch handling.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The accepted scope defines falsifiable ancestry and unchanged-origin outcomes, preserves existing carry behavior, and explicitly accepts stopping on rebases; brief.md:12, brief.md:26. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only the production changes reproduced silent acceptance, the misleading overlap diagnosis, and missing flow state: 3 failures among 52 tests; target/template/tests/test_integrate_stack_bases.py:390, review-red.log:28. |
| C3 Change | PASS | The four changed files stay within the chosen fold, flow-state, regression-test, and documentation scope; target/template/src/pdca_harness/flow.py:2103, target/template/src/pdca_harness/integrate.py:281, target/docs/07-crosscutting.md:666. |
| C4 Verification (red→green) | PASS | Restoring the production changes made all 52 tests pass; the independent result agrees with the frozen gate, but does not cover the additional C5 race; review-green.log:25, gate-logs/C4-verify.log:64. |
| C5 Causal adequacy | NEEDS-HUMAN [impl] | Close the checked-head/merged-head race for multiple bases sharing one checkout — a later fetch can replace an already-checked ref and silently push both old and rewritten commits; target/template/src/pdca_harness/integrate.py:398, target/template/src/pdca_harness/integrate.py:529, review-multibase.log:1. |
| T1 Structure | PASS | Per-run state stays owned by the flow and is recorded only after a successful push; existing callers can omit it without changing carry semantics; target/template/src/pdca_harness/flow.py:2304, target/template/src/pdca_harness/integrate.py:492. |
| T2 Shape | PASS | Independent docs lint, 22-page render/link audit, and git diff --check passed; both frozen docs gates agree; target/docs/07-crosscutting.md:666, gate-logs/T2-docs.log:11, gate-logs/host-ci-docs.log:11. |
| T3 Runtime | PASS | Independent driver suite passed 2,375 tests with 2 skips; frozen evidence separately shows 24 root tests passing, including real Copier render/update cases; review-suite.log:1797, gate-logs/T3-suite.log:38, gate-logs/T3-suite.log:54. |
| T4 Contribution | N/A | Contribution artifacts are intentionally drafted after Check; their substantive audit remains mandatory at publish; gate-logs/T4-contribution.log:10. |
| T5 Judgment | NEEDS-HUMAN | Confirm merged and closed/rejected prior art for every affected path — the brief reports integrate.py/publish.py history, but not flow.py, docs, or tests, and this target contains only a synthetic base commit with no remote; brief.md:31, review-prior-art.log:1. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether stopping and requiring branch restoration or a fresh run is operationally suitable for live stacks after the C5 defect is fixed — the selected behavior also rejects contributor rebases; brief.md:26, target/docs/07-crosscutting.md:668. |

The C5 finding is independently reproduced with real Git. Run `PYTHONDONTWRITEBYTECODE=1 python3 review-race-repro.py` from this report's directory. The script uses the target's existing fixture and production fold; its only interception schedules a real force-push before the second real fetch. It does not fake ancestry, merging, or push outcomes.

1. Publish A for `main` and C for `zbase` in the same checkout; fold both with the same `carried` mapping.
2. In the next fold, let the main group's preflight fetch and ancestry check succeed.
3. Before the zbase group's fetch, force-push `fix/A` to a non-descendant commit adding `a2.txt`.
4. That fetch refreshes the shared checkout's `origin/fix/A`. The merge resolves this mutable ref again, without comparing the new head to the recorded head.
5. Observed: fold returns successfully, origin's main integration line moves, both A histories are ancestors of it, and `carried['issue_A']` is replaced by the rewritten head (`review-multibase.log:2`).

The `fetched` set is keyed by `(repo, base)`, although remote-tracking refs are shared across bases in that checkout (`target/template/src/pdca_harness/integrate.py:391`). Consequently, suppressing the group's own later fetch does not preserve its checked snapshot. Keep the actual merge tied to an ancestry-validated immutable head, with every relevant check completed before any target merges or pushes; add this real-Git multi-base interleaving as a regression. A check introduced only inside each merge would not preserve the promised all-target preflight boundary.

The capability-probe smell test does not independently trigger: the added signature probe is confined to the red-leg test adapter (`target/template/tests/test_integrate_stack_bases.py:371`), and the production ancestry check enforces the explicitly chosen invariant rather than masking a load-time capability side effect. The existing production-path scanner was vacuous because no new test file was added (`gate-logs/C5-prod-path.log:10`); direct inspection and the independent runs confirm these tests exercise production.

Evidence limits: the disposable target was readable and the patch was present; its final diff matches `patch.diff` byte-for-byte after stash restoration. Instance-only gate wrappers were adjudicated from their supplied logs and their available underlying checks were rerun. This interpreter cannot import Copier, so the local root-suite attempt reports no Copier evidence (`review-root-suite.log:6`); the frozen log explicitly shows the real render/update cases running successfully, so this local host limitation is not a patch failure or an undischarged patch dependency. The target's integration template enumerates no additional human-only items beyond a TODO (`target/template/docs/INTEGRATION.md.jinja:80`). No source fix was made. This review is advisory.

<!-- pdca:leaf-complete -->
