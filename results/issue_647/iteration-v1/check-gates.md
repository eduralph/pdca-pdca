# Check gates — issue_647

**Overall (gating): fail**

The Check 5/5/1: 5 correctness · 5 conformance · 1 validation.

## Correctness (5)

| Check | Result | Oracle | Rule | Evidence | Gating |
|---|---|---|---|---|---|
| C1 Spec | none | brief.md | — | — | no |
| C2 Reproduction (red pre-fix) | none | (no gate configured) | — | — | no |
| C3 Change | none | patch.diff | — | — | no |
| C4 Verification (worktree mismatch) | fail | worktree reconstruction (base + patch.diff) | worktree-mismatch | issue_647: lane pdca-harness.pdca-wt is busy (another Do or gate run holds it) — refusing to reconstruct under a live run; retry when it finishes. | yes |
| C5 Causal adequacy | none | reviewer + human sign-off | — | — | no |

## Conformance (5)

| Check | Result | Oracle | Rule | Evidence | Gating |
|---|---|---|---|---|---|
| T1 Structure | none | (no gate configured) | — | — | no |
| T2 Shape | none | (no gate configured) | — | — | no |
| T3 Runtime | none | (no gate configured) | — | — | no |
| T4 Contribution | none | (no gate configured) | — | — | no |
| T5 Judgment | none | reviewer + human sign-off | — | — | no |

## Validation (1)

| Check | Result | Oracle | Rule | Evidence | Gating |
|---|---|---|---|---|---|
| Validation — fitness-to-purpose | none | human at sign-off | — | — | no |
