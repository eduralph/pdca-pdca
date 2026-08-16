Review of the docs-only correction aligning the split-lineage reader contract with its actual handling of unusable `depth` values.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The required reader-versus-arithmetic contract and one-paragraph scope are decidable against `template/src/pdca_harness/split.py:583` and `template/src/pdca_harness/split.py:615`. |
| C2 Reproduction (red pre-fix) | PASS | With the patch stashed, the base prose claimed a non-numeric depth returns `None` while an executable probe returned the parsed record, matching `template/src/pdca_harness/split.py:612` and the regression at `template/tests/test_split_lineage.py:236`. |
| C3 Change | FAIL | The required abstention contract includes valid-JSON non-object payloads, but the patched enumeration omits that case even though the reader rejects it, leaving the contract incomplete at `docs/07-crosscutting.md:278` versus `template/src/pdca_harness/split.py:610`. |
| C4 Verification (red→green) | NEEDS-HUMAN | The maintainer must decide whether the reproduced prose contradiction, corrected semantic probe, and existing regression are sufficient for this docs-only change — the configured verifier produced no mechanical bundle red→green and exited 77 (`gate-logs/C4-verify.log:7`; `template/tests/test_split_lineage.py:247`). |
| C5 Causal adequacy | PASS | Correcting the normative sentence removes the source of false review findings directly, with no capability probe or runtime guard introduced at `docs/07-crosscutting.md:278`. |
| T1 Structure | PASS | The change remains confined to the lineage paragraph and preserves its surrounding split and transaction narrative at `docs/07-crosscutting.md:270`. |
| T2 Shape | PASS | Independently rerun docs lint and site/link rendering passed, corroborating both frozen docs checks (`gate-logs/T2-docs.log:10`; `gate-logs/host-ci-docs.log:10`). |
| T3 Runtime | PASS | All 23 lineage tests passed independently, including the non-numeric-depth behavior at `template/tests/test_split_lineage.py:236`, and the frozen full runtime suite also passed (`gate-logs/T3-suite.log:7`). |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the deferred row says their substantive audit reruns at publish (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | PASS | Affected-path commit history plus all closed/merged PR file lists found only merged predecessors (latest #504), no closed-unmerged attempt, and the current open-PR query was empty, so no prior-art collision requires judgment. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | The maintainer must decide whether the reader-facing explanation is complete and clear after resolving C3 — lint, rendering, and runtime tests cannot judge documentation fitness at `docs/07-crosscutting.md:278`. |
