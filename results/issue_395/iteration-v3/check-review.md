Review issue #395: prevent publishing a non-final stack-wave bundle that the fold would hold for a same-wave textual conflict.

Source citations are relative to `$PDCA_TARGET` (`target/`); reviewer evidence paths are relative to this directory. The target was readable, matched the patch, and was restored after the production-only stash/reapply check.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The observable contract distinguishes same-wave conflicts, existing-line conflicts, T4 failures, failed partner pushes, and final waves; `brief.md:11` defines six falsifiable cases. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing the production fix left all 17 new tests runnable and produced 12 assertion failures, including an unwanted pushed sibling branch; `review-red.log:174`, `template/tests/test_flow_same_wave_prepublish.py:252`. |
| C3 Change | PASS | The publish decision covers ready bundles on precisely the scoped non-final stack waves, retaining conflict versus unpushed bookkeeping and the fold backstop; `template/src/pdca_harness/flow.py:3166`, `template/src/pdca_harness/flow.py:3237`. |
| C4 Verification (red→green) | PASS | Independently reproduced assertion-red, restored the patch, and passed the complete 2,647-test driver suite (2 skips); the dedicated patched run passed all 17 new tests; `review-red.log:174`, `review-suite.log:1819`, `review-green.log:20`. |
| C5 Causal adequacy | NEEDS-HUMAN [impl] | Make recovery achievable when only some partners close unmerged — the hold correctly remains, but its advice still requires a discarded partner that the carry cannot supply; `template/src/pdca_harness/flow.py:1390`, `template/src/pdca_harness/flow.py:1568`, `review-mixed-closed.log:3`. |
| T1 Structure | PASS | A shared publish-base rule and the fold's existing clash rule keep trial semantics aligned, under the integration lock; `template/src/pdca_harness/publish.py:797`, `template/src/pdca_harness/integrate.py:824`, `template/src/pdca_harness/integrate.py:893`. |
| T2 Shape | PASS | Independent whitespace check, docs lint, 22-page render, and internal-link audit passed; frozen host-CI parity shows the same checks passing; `review-docs.log:1`, `review-docs.log:4`, `gate-logs/host-ci-docs.log:15`. |
| T3 Runtime | PASS | Independent driver suite passed; local root-suite rerun could not exercise Copier, while the frozen log explicitly records all 24 root render/update tests passing; `review-suite.log:1821`, `review-root-suite.log:6`, `gate-logs/T3-suite.log:54`. |
| T4 Contribution | N/A | Contribution artifacts are absent by design; substantive T4 auditing is deferred to the mandatory publish-time rerun, as the frozen gate records; `gate-logs/T4-contribution.log:10`. |
| T5 Judgment | PASS | Prior-art checks ran by every affected path against main history and all 303 closed PRs (128 path matches); predecessors address fold/carry behavior, and the independent red leg establishes the missing pre-publish behavior; `review-history.log:1`, `review-prior-art-summary.log:1`, `review-prior-art-summary.log:14`. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether this partial prevention meets operational needs — final/one-wave runs still publish conflicting siblings, automatic re-sequencing is excluded, and persistent trial failure conservatively publishes only one bundle per target; `brief.md:19`, `docs/07-crosscutting.md:732`, `template/tests/test_flow_same_wave_prepublish.py:382`. |

The remaining implementation concern is recovery after mixed partner closure. The real-git probe first holds issue_13 for conflicts with issues 10 and 12. It then closes 10's PR unmerged, deletes 10's remote branch and the old integration line, leaves 12's PR open, and reissues the dependent issue_20. Only issue_12 is carried, but the emitted step still says “rebuild issue_13 on a base that holds issue_10, issue_12”; issue_20 remains PLANNED (`review-mixed-closed.log:1`, `review-mixed-closed.log:3`, `review-mixed-closed.log:4`). Removing the old line ensures this result does not depend on a stale integration line.

Keep the hold for surviving partners, but exclude confirmed closed-unmerged partners from the required rebuild base and conflict declaration. The test currently requires the stale advice at `template/tests/test_flow_same_wave_prepublish.py:605`; revise it to verify an actionable step for the surviving partner. Replay the probe from this directory with:

```bash
TMPDIR="$PWD/review-tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/target/template/src" python3 review-probe-mixed-closed.py
```

The trial now retries transient fetch/staging failures and withholds candidates it cannot build; the production tests exercise those paths with real git. Production imports were independently checked, confirming the limited claim in `gate-logs/C5-prod-path.log:10`. The added capability probes are confined to test fixtures that deliberately run against pre-fix code; no production capability probe masks a load-time cause.

The root-suite limitation belongs to this reviewer environment: Copier is not importable here. Its frozen gate evidence shows executed render/update coverage, so this is not an unmet patch dependency. GitHub calls in the new regression fixture are stubbed as the brief explicitly requires; branch creation, merging, pushing, and push refusal execute against real repositories.

<!-- pdca:leaf-complete -->
