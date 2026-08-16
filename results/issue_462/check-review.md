Task under review: make merge-mode wave boundaries wait for pending or absent PR-check evidence within a configurable bound and restore draft state whenever a readied PR is not merged.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The observable contract is explicit about pending/empty resolution, timeout refusal, draft restoration, and the zero-wait escape hatch (`template/pdca.toml.jinja:142`). |
| C2 Reproduction (red pre-fix) | PASS | Independently retaining the patched tests against pre-fix production produced 7 failures/errors, including pending-to-green and ready-undo expectations (`template/tests/test_merge.py:271`). |
| C3 Change | FAIL | The configured safety bound must limit actual elapsed time, but the loop increments only requested sleep seconds and excludes every rollup-call duration, so it is not the promised wall-clock bound (`template/src/pdca_harness/merge.py:153`). |
| C4 Verification (red→green) | PASS | Independent re-run was red with pre-fix production and green 24/24 with the patch; the exercised production import and pending-to-green case are at `template/tests/test_merge.py:37` and `template/tests/test_merge.py:289`. |
| C5 Causal adequacy | PASS | The change removes the immediate-verdict behavior by re-reading pending/empty evidence and restores state on both refusal exits; it adds no capability probe or symptom guard (`template/src/pdca_harness/merge.py:153`, `template/src/pdca_harness/merge.py:248`). |
| T1 Structure | PASS | Waiting and ready-state rollback are isolated helpers with configuration passed through the existing merge boundary (`template/src/pdca_harness/merge.py:143`, `template/src/pdca_harness/merge.py:163`). |
| T2 Shape | PASS | Both frozen docs/host-CI lint-and-render logs are green, and the new scalar remains in the documented `[driver]` block (`template/pdca.toml.jinja:142`). |
| T3 Runtime | FAIL | A direct exercise with a 1s configured bound and 0.6s rollup latency measured 2.20s, confirming that slow `gh pr checks` calls can overrun the advertised limit (`template/src/pdca_harness/merge.py:153`). |
| T4 Contribution | N/A | The contribution gate was deferred because `pr-description.md` is intentionally drafted later; its substantive audit reruns at publish. |
| T5 Judgment | NEEDS-HUMAN | Confirm no merged, closed, or rejected prior work already covers these four affected paths — the disposable target has one synthetic base commit and no remote, so the brief's affected-path prior-art claim cannot be mechanically settled here. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the 300s default and 15s polling cadence fit the repository's real CI-registration latency and draft-governance expectations — that choice determines whether merge waves progress without premature STOPs (`template/src/pdca_harness/config.py:369`). |
