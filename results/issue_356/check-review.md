Review of issue 356: make `loop-telemetry.json` identify the effective builder tier, including same-vendor escalation ladders.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The owed behavior is explicit enough to judge: telemetry must distinguish the tier that actually ran while preserving `n`/`builder`/`family`, matching `_mapped_argv` argv precedence at `template/src/pdca_harness/leaves.py:150`. |
| C2 Reproduction (red pre-fix) | PASS | The reproduced red leg matters because base source plus the new test file fails with missing `model`/`effort` and the old 3-arg writer contract, while the test asserts the new tier fields at `template/tests/test_loop_escalation.py:215`. |
| C3 Change | PASS | The change addresses the judged surface directly: `_effective_tier` derives model/effort from argv first and falls back to leaf keys, then `_record_loop_attempt` writes them additively at `template/src/pdca_harness/leaves.py:1232` and `template/src/pdca_harness/leaves.py:1286`. |
| C4 Verification (red→green) | PASS | Re-ran `/home/eddie/pdca/pdca-pdca/engine/scripts/run-verify.sh` with this bundle: green with patch, red with production hunks reverted, proving `template/tests/test_loop_escalation.py:118` captures the defect. |
| C5 Causal adequacy | PASS | The root-cause decision is not contested: the old sidecar could only record identical same-vendor `builder`/`family`, and the patch records the effective tier using the same precedence as the invocation mapper at `template/src/pdca_harness/leaves.py:150`. |
| T1 Structure | PASS | The scope decision is contained to the telemetry writer, its caller, its direct tests, and the shipped config comment; no unrelated module boundary is crossed beyond the caller that now passes `cfg` at `template/src/pdca_harness/leaves.py:1340`. |
| T2 Shape | PASS | Re-ran docs lint and site render/link audit with `PDCA_WORKTREE=$PDCA_TARGET`; both passed, and the changed template comment remains coherent at `template/pdca.toml.jinja:396`. |
| T3 Runtime | PASS | Re-ran the driver runtime suite with `PDCA_WORKTREE=$PDCA_TARGET`; it exited 0 locally, so the frozen advisory T3 failure in `check-gates.json` was not reproduced against this target state. |
| T4 Contribution | NEEDS-HUMAN | Contribution artifacts were withheld from this reviewer, so the human must decide whether the frozen T4 pass is sufficient before publication. |
| T5 Judgment | PASS | Prior-art check by affected paths found the existing telemetry writer/caller history and no separate open PR from `gh pr list`; the human-facing decision is only whether to accept the additive sidecar fields as the right published contract. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Human sign-off must decide whether recording empty strings for CLI defaults is fit for telemetry consumers, because final product semantics are intentionally outside deterministic gates. |
