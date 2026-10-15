Review issue #695: detect carried-branch rewrites after the last integration fold, fail the run, and tolerate one transient fetch failure.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The observable contract distinguishes rewrites, fast-forwards, deletion, and persistent fetch failure, with explicit CLI exit precedence and exclusions; brief.md:11, brief.md:29; target contract at docs/07-crosscutting.md:675. |
| C2 Reproduction (red pre-fix) | PASS | With tracked fixes stashed and the new tests retained, nine tests executed and six failed on the expected missing reports/retry behavior, without import failures; review-red.log:106; template/tests/test_integrate_carried_rewrite_late.py:167. |
| C3 Change | PASS | The patch stays within the specified reporting/retry scope and extends the existing run-outcome channel, preserving bundle states and excluding merge/stub runs; template/src/pdca_harness/flow.py:2684; template/src/pdca_harness/cli.py:729. |
| C4 Verification (red→green) | PASS | Restoring the patch turned the same nine tests green, including the previously missing unchecked-fetch failure case and rewrite-over-hold precedence; review-green.log:12; template/tests/test_integrate_carried_rewrite_late.py:211. |
| C5 Causal adequacy | PASS | Real-git failures establish the missing final observation and one-shot fetch as the causes; independent Act-time and two-branch rewrite exercises also return 1 with the expected reports; review-extra.log:1; template/src/pdca_harness/flow.py:2673; template/src/pdca_harness/integrate.py:713. |
| T1 Structure | PASS | Ancestry judgment remains shared by fold-time and end-of-run checks, and the CLI retains one exit-code rule, limiting behavioral drift; template/src/pdca_harness/integrate.py:764; template/src/pdca_harness/cli.py:700. |
| T2 Shape | PASS | Independent docs lint, 22-page rendering/link audit, and diff whitespace checks passed; review-docs.log:2; the host-parity log independently records the same successful audit at gate-logs/host-ci-docs.log:11. |
| T3 Runtime | PASS | Independent driver discovery passed 2,522 tests with two skips, and all 78 targeted regression tests passed; root render/update coverage rests on the frozen successful gate because local Copier import is unavailable; review-driver-suite.log:1817; review-regression.log:103; gate-logs/T3-suite.log:54. |
| T4 Contribution | N/A | Contribution artifacts are intentionally absent at Check; the substantive PR-body/commit audit is deferred to its mandatory publish-time rerun; gate-logs/T4-contribution.log:10. |
| T5 Judgment | NEEDS-HUMAN | Confirm no path-matched closed work represents a rejection or superseding solution to this approach — merged-history and closed-PR file checks establish overlap, but cannot settle semantic equivalence or rejection rationale; review-prior-art.log:2; review-prior-art.log:72; brief.md:34. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Accept end-of-run detection and the stated recovery guidance for still-resolving branches — operators must restore/rebuild affected PRs, while deleted branches remain outside this check and the observation is not atomic with later remote changes; docs/07-crosscutting.md:675; template/src/pdca_harness/integrate.py:731. |

Source citations above are relative to `$PDCA_TARGET` (`target/`); brief and evidence-log citations are relative to this review directory. The disposable target contains the required predecessor changes and the applied patch. No stale-target caveat was needed. The tracked patch was restored after the red run, and a final reverse-application check against `patch.diff` passed.

Independent evidence:

- Red/green: in `target/template`, `PYTHONPATH=src python3 -m unittest -v tests.test_integrate_carried_rewrite_late`, first with tracked changes stashed, then after `git stash pop`. Red: six assertion failures among nine tests; green: all nine pass. This agrees with the frozen C4 log, including the end-of-run fetch failure added in this iteration.
- Regressions: `PYTHONPATH=src python3 -m unittest -v tests.test_integrate_stack_bases tests.test_flow_same_wave_conflict tests.test_flow_hold_exit_code` passed all 78 tests. Full `PYTHONPATH=src python3 -m unittest discover -s tests` passed 2,522 tests with two skips.
- Additional exercises used the shipped real-git fixture and production CLI: rewrite A from the Act callback; rewrite A and C while the last wave builds. Both passed; each affected branch was reported once and the CLI returned 1 (`review-extra.log:1`). These exercises did not modify the submitted tests or production source.
- The production-import scanner passed against `patch.diff`. Docs lint and `render_site.py --check --out ../review-site` passed, with 22 pages and a clean internal-link audit. The frozen C5 and host-CI logs corroborate those checks.

Local host caveat: `python3 -m tests.run_root_suite` exited 77 because `/usr/bin/python3` cannot import Copier; its three Copier-dependent suites skipped (`review-root-suite.log:6`). This is not a verified local root-suite pass or a patch defect. The frozen T3 evidence explicitly shows the real render and update-compat cases executing successfully, with 24 root tests passing (`gate-logs/T3-suite.log:38`, `gate-logs/T3-suite.log:54`). The fix's declared Python/git toolchain was present and exercised; no unsatisfied external dependency for the scoped behavior was identified.

Prior art was independently queried through the GitHub API by all five affected paths. Main-history counts were 38 for the documentation, 118 for CLI, 87 for flow, 18 for integration, and zero for the new test. All ten closed-unmerged PR file lists were inspected. Relevant overlaps include #649, #648, #639, #638, #637, #600, #599, and #598; the detailed per-file matches are in `review-prior-art.log`. The semantic disposition remains the T5 decision above.

The C5 capability-probe smell-test did not fire: the added conditions select applicable run outcomes, and no optional-capability probe masks a load-time side effect. The available integration document is the unrendered template; its project-specific human-only list is a TODO (`template/docs/INTEGRATION.md.jinja:80`), so it supplies no additional enumerated item. No builder-fixable defect was established by this review.

<!-- pdca:leaf-complete -->
