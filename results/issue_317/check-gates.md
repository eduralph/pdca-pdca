# Check gates — issue_317

**Overall (gating): pass**

The Check 5/5/1: 5 correctness · 5 conformance · 1 validation.

## Correctness (5)

| Check | Result | Oracle | Rule | Evidence | Gating |
|---|---|---|---|---|---|
| C1 Spec | none | brief.md | — | — | no |
| C2 Reproduction (red pre-fix) | none | (no gate configured) | — | — | no |
| C3 Change | none | patch.diff | — | — | no |
| C4 fix verified: bundle test red pre-fix, green post-fix | pass | ./engine/scripts/run-verify.sh | C4-verify | C4 PASS: red without the fix, green with it | yes |
| C5 Causal adequacy | none | reviewer + human sign-off | — | — | no |

## Conformance (5)

| Check | Result | Oracle | Rule | Evidence | Gating |
|---|---|---|---|---|---|
| T1 Structure | none | (no gate configured) | — | — | no |
| T2 shape: docs lint + site render link audit | pass | ./engine/scripts/run-docs-check.sh | T2-docs | render_site: link audit OK | no |
| T3 runtime: render/update-compat + offline driver suites | fail | ./engine/scripts/run-suite.sh | T3-suite | /tmp/tmpr2shjq_b/results/issue_500/split-proposal.md | no |
| T4 PR body has a user-impact opener + tracker id in both artifacts | pass | pdca-pdca contribcheck | T4-contribution | — | yes |
| T5 Judgment | none | reviewer + human sign-off | — | — | no |

## Validation (1)

| Check | Result | Oracle | Rule | Evidence | Gating |
|---|---|---|---|---|---|
| Validation — fitness-to-purpose | none | human at sign-off | — | — | no |
