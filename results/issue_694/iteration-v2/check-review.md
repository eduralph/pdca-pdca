Review issue #694: make re-issued conflict holds name the responsible finished bundle and give actionable rebuild advice instead of asking to reopen an already-open PR.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The required partner/base/other-line distinctions and unchanged carry behavior are falsifiable with real Git; brief.md:11 and brief.md:23. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only the production changes leaves all 12 regression tests failing on advice assertions, including the base-conflict case; review-red.log:145; target/template/tests/test_flow_reissue_after_conflict_hold.py:351. |
| C3 Change | PASS | The patch stays within carry diagnostics, shared remedy wording, documentation, and regression coverage; the supplied target matches the patch, including its stacked base; target/template/src/pdca_harness/flow.py:1161. |
| C4 Verification (red→green) | PASS | Restoring the production changes makes all 12 regression tests pass, reproducing the frozen gate's result; review-green.log:3; gate-logs/C4-verify.log:10. This verifies those cases, not the uncovered cases below. |
| C5 Causal adequacy | NEEDS-HUMAN [impl] | Correct partner attribution before prescribing rebuilds: inherited delete conflicts falsely blame unrelated stacked work, and hold propagation leaves removed partners in the advice; target/template/src/pdca_harness/integrate.py:1186 and :615; review-deletion.log:5; review-dropped-partner.log:4. |
| T1 Structure | PASS | Diagnosis uses the existing locked trial-merge machinery and optional carry-specific output; ordinary folds retain their existing mode; target/template/src/pdca_harness/integrate.py:434 and :1233. |
| T2 Shape | PASS | Independent docs lint, 22-page render/link audit, and diff whitespace checks pass; frozen T2 and host-parity logs corroborate those checks; gate-logs/T2-docs.log:11; gate-logs/host-ci-docs.log:11. |
| T3 Runtime | PASS | Independent driver suite passes 2,503 tests with two skips, and related conflict/carry selections pass 24/27 tests; review-suite.log:1817; root render/update coverage is supported by the frozen 24-test passing run, gate-logs/T3-suite.log:54, with the local interpreter caveat below. |
| T4 Contribution | N/A | Contribution artifacts are intentionally drafted after Check; their substantive audit must run at publish; gate-logs/T4-contribution.log:10. |
| T5 Judgment | NEEDS-HUMAN | Confirm the path-based prior-art conclusion, including merged docs history and closed/rejected work — the brief reports the search, but this synthetic single-commit target has no original history or remote with which to corroborate it; brief.md:28. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the corrected advice gives operators a sufficient recovery path without unnecessary conflict declarations or rebuilds — the observed attribution errors below undermine that purpose despite passing regression gates; target/docs/07-crosscutting.md:777. |

Two implementation findings remain:

1. **Inherited deletion incorrectly implicates an unrelated stacked bundle.** In a real repository, issue_10 deletes `shared.txt`; issue_12 builds on issue_10 and adds only `unrelated.txt`; issue_11 changes `shared.txt` from the base. Both 10 and 12 are on the integration line. Calling production `_clash` reports both as conflicting partners, although 12 never changes the conflicting file (`review-deletion.log:1`). At `target/template/src/pdca_harness/integrate.py:1186`, the isolation trial stops while merging issue_11 into its inherited base: `-X theirs` cannot resolve modify/delete conflicts. Because it never reaches issue_12's own change, the unconditional attribution at `:1191` falls back to the inherited conflict. This contradicts `target/docs/07-crosscutting.md:779` and can prescribe an unnecessary `Conflicts with: 12`. Attribute only demonstrated own changes; add a modify/delete regression and avoid treating an incomplete isolation trial as proof against the stacked bundle.

2. **A partner removed by hold propagation still appears in the final advice.** A real `integrate.fold` with 10/11 conflicting on `a.txt`, 12 built on 11 but resolving `a.txt` as 10 and changing `b.txt`, and 13 changing `b.txt`, carries only 10. It holds 12 because it contains skipped 11's work, yet returns 13's clash as `issue_12` (`review-dropped-partner.log:2`). Attribution runs at `target/template/src/pdca_harness/integrate.py:615`, before `_hold_work` at `:627` removes 12. The next pass skips already-dropped 13 and never refreshes its attribution. `target/template/src/pdca_harness/flow.py:1175` then consumes that stale partner, proposing a rebuild on a bundle the carry itself excluded. Recompute or reconcile all conflict diagnoses against the final retained line after hold propagation; cover this interaction with a regression. Retrying the held merge itself remains outside this slice's scope.

Both reviewer reproductions are retained and runnable from this review directory; each currently exits 1 on its explicit assertion:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=target/template/src python3 review-deletion.py
TMPDIR="$PWD" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=target/template/src python3 review-dropped-partner.py
```

Evidence boundaries: all source citations above were checked in `$PDCA_TARGET`; no stale-target caveat applies. The production stash was restored and `git apply --reverse --check ../patch.diff` succeeds from the target. The production-import scanner also passes (`review-prod-path.log:1`). No optional-capability/load-time symptom guard was introduced. The real-Git fixtures can exhibit the forbidden conflicts; Git and Python were exercised without tool substitutes. No live host service is required by the brief.

The local root-suite rerun exits 77 because this interpreter cannot import Copier (`review-root-suite.log:6`). This is a reviewer-host limitation, not a patch failure or an undischarged gate dependency: the frozen root-suite log explicitly shows its render/update cases executing and all 24 tests passing (`gate-logs/T3-suite.log:45` and `:54`). The instance-scoped wrapper paths were not treated as target files. T4 remains deferred, not unverifiable. The available INTEGRATION template enumerates no additional concrete human-only items (`target/template/docs/INTEGRATION.md.jinja:80`).
<!-- pdca:leaf-complete -->
