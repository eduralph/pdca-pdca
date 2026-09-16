Task under review: make retrying reviewer and advisory leaves persist attempt-owned records and harvest only the successful attempt's artifact while preserving interrupted-run recovery.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The retry, dead-artifact, impersonation, and recovery outcomes are falsifiable offline against the resilient wrapper at `template/src/pdca_harness/leaves.py:673`. |
| C2 Reproduction (red pre-fix) | PASS | With the four production files stashed and the new behavioral test retained, the independent base run produced 17 failures and 1 error, including the missing pre-retry record assertion at `template/tests/test_attempt_ownership.py:204`. |
| C3 Change | FAIL | A dead attempt's text must survive interruption, but withdrawal unlinks it at `template/src/pdca_harness/leaves.py:986` before the caller first persists that record at `template/src/pdca_harness/leaves.py:760`, leaving an avoidable evidence-loss window. |
| C4 Verification (red→green) | PASS | Independent stash/restore reproduced red (17 failures, 1 error) then green (22/22), and the restored patch also passed its unchanged resilience and memory-log suites (44/44 total) plus reverse-apply checking. |
| C5 Causal adequacy | FAIL | Attempt accountability remains incomplete when the harness dies between destructive residue withdrawal and record persistence at `template/src/pdca_harness/leaves.py:753`; that ordering can recreate the exact no-artifact/no-account state the fix is meant to eliminate. |
| T1 Structure | PASS | The work remains one accountability slice centered on the retry wrapper and its three harvest/recovery consumers, with the production boundary anchored at `template/src/pdca_harness/leaves.py:673`. |
| T2 Shape | PASS | `git diff --check` and reverse-apply checking pass, and the frozen docs lint, site link audit, and host-CI parity logs all show green. |
| T3 Runtime | FAIL | Although the independent full offline suite passed 1,780 tests, a forced kill immediately after `artifact.unlink()` at `template/src/pdca_harness/leaves.py:986` observed `runs=1 bundle_artifact=False error_log=False`, losing both the dead verdict and its account. |
| T4 Contribution | N/A | `pr-description.md` is absent by design at Check; `gate-logs/T4-contribution.log` records that the substantive contribution audit reruns at publish. |
| T5 Judgment | NEEDS-HUMAN | Confirm no overlapping merged or closed/rejected work for every affected path — the disposable target contains one synthetic base commit and no remotes, so the brief's prior-art claim cannot be mechanically re-derived here and overlap would affect contribution safety. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the operational post-mortem guarantee is acceptable only after the withdrawal-before-persistence kill window is resolved — the normal suite is green but misses a core process-death boundary. |
