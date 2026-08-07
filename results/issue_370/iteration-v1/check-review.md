Task under review: persist full bundle-scoped gate output as per-rule `gate-logs/` evidence, add row metadata, and archive logs per iteration.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief defines a bounded evidence-retention defect and explicit success criteria for bundle logs, row keys, timeout partial output, archive retention, and unchanged repo-scoped behavior (`brief.md:10`). |
| C2 Reproduction (red pre-fix) | PASS | Red was reproduced on a base snapshot with the new test: assertions failed for missing `gate-logs`, missing `log`, and missing `state.GATE_LOGS_DIR`; literal stash was blocked by read-only git metadata, not by the patch (`template/tests/test_gate_logs.py:74`). |
| C3 Change | PASS | The changed surfaces match the requested data path: bundle `run_gates` passes a log directory, per-row execution writes evidence, and iteration archive handles directories (`template/src/pdca_harness/gates.py:146`; `template/src/pdca_harness/driver.py:390`). |
| C4 Verification (red→green) | NEEDS-HUMAN | Exact `C4-verify` cannot be affirmed here because the target verifier is still the skeleton that exits 1, while the independently run focused unittest is red on base and green with the patch (`template/engine/scripts/run-verify.sh:50`; `template/tests/test_gate_logs.py:97`). |
| C5 Causal adequacy | FAIL | Human must decide whether evidence persistence may be best-effort: a `gate-logs` path collision produced a passing gate row with no `log`/`duration_secs`, so the original "verdict without full basis" failure can still occur (`template/src/pdca_harness/gates.py:554`). |
| T1 Structure | PASS | The patch keeps one shared directory spelling in state and reuses the existing downstream archive list rather than adding a separate archive mechanism (`template/src/pdca_harness/state.py:53`). |
| T2 Shape | NEEDS-HUMAN | The configured docs gate could not be rerun because `run-docs-check.sh` is absent in this target checkout; the reported green row is provisional, not independently verified. |
| T3 Runtime | NEEDS-HUMAN | The configured `T3-suite` runner could not be rerun because `run-suite.sh` is absent here; available `python3 -m unittest discover -s template/tests` exited 0, but the reported T3 red remains environment/provenance-dependent. |
| T4 Contribution | NEEDS-HUMAN | `pdca-pdca contribcheck` is installed but cannot run in this source checkout without a rendered `pdca.toml`, so the contribution artifact check is provisional. |
| T5 Judgment | NEEDS-HUMAN | Human judgment is owed on whether the best-effort log-write behavior is acceptable despite the evidence-sufficiency invariant and the reproduced collision case (`template/src/pdca_harness/gates.py:557`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Human sign-off must decide whether the remaining operational gap is acceptable: ordinary focused tests pass, but exact harness gates were not reproducible in this target environment. |
