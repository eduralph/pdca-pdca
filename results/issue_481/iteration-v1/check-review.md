Review issue #481: restore a Plan artifact for iterated split parents and prevent Do-era bundles from deriving UNPLANNED.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The six success criteria distinguish restoring the parent artifact from correcting state derivation, and explicitly require rollback after failed acceptance; brief.md:24, brief.md:75; target/template/src/pdca_harness/state.py:41. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only the production changes while retaining the regression tests produced 4 assertion failures and 1 missing-brief error across 103 tests; review-red.log:57; target/template/tests/test_split.py:1816. |
| C3 Change | FAIL | A partial parent-brief write escapes rollback, and retry accepts the surviving truncated brief, violating the required recoverable transaction; target/template/src/pdca_harness/split.py:931, target/template/src/pdca_harness/split.py:967; review-rollback.log:2. |
| C4 Verification (red→green) | PASS | Restoring the production patch made all 103 split tests pass, independently confirming the asserted normal-path red→green; this suite does not cover the partial-write defect; review-green.log:5; target/template/tests/test_split.py:1833. |
| C5 Causal adequacy | PASS | The ordinary failure's two causes are addressed: lost parent Plan evidence and state ordering; the tests exercise real archive, accept, state and handoff APIs, and no optional-capability probe masks a load-time cause; target/template/tests/test_split.py:1821, target/template/src/pdca_harness/state.py:314. |
| T1 Structure | PASS | The change stays in the specified split/state modules and regression file, reusing the existing brief parser and transaction boundary; target/template/src/pdca_harness/split.py:734, target/template/src/pdca_harness/split.py:906. |
| T2 Shape | PASS | Independent docs lint, 22-page render/link audit and git diff whitespace check pass; the frozen host-parity log confirms the same docs checks; review-docs.log:2, gate-logs/host-ci-docs.log:10. |
| T3 Runtime | PASS | Independent offline execution passes 1,901 tests with 2 skips; frozen evidence additionally shows all 24 root render/update tests passed, including actual Copier execution; review-suite.log:1656, gate-logs/T3-suite.log:54. |
| T4 Contribution | N/A | The contribution artifacts are intentionally absent at Check; the deferred gate's substantive audit must rerun at publish; gate-logs/T4-contribution.log:10. |
| T5 Judgment | PASS | The scope follows the stated invariant; independent path-filtered merged-history checks and the sole closed-unmerged PR's file list reveal no competing fix in the checked evidence; review-history-split.log:1, review-history-state.log:1, review-history-tests.log:1, review-rejected-files.log:1. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the generated parent summary and its requirement that every child reach COMPLETE provide the intended sign-off contract for a recovered split parent — passing artifact/state tests cannot establish that operational policy; target/template/src/pdca_harness/split.py:783. |

**Finding: P2 — include failed partial writes in parent-brief rollback.** At `target/template/src/pdca_harness/split.py:931`, `Path.write_text` can create/truncate the destination and then raise, for example on disk exhaustion. `wrote_parent_brief` becomes true only after that call returns (`:933`), so the exception handler skips removal (`:967`). The children and marker are rolled back, but the new broken brief remains. On retry, `parent_had_brief` is true (`:839`), so acceptance preserves the truncated file and completes with an invalid Plan artifact.

I reproduced this against the patched source using the regression fixture's real archive/accept path. A fault injected only into the parent brief write persisted 40 characters and raised ENOSPC. The failed accept left that file behind; retry reached BUILT while `handoff.check_planner` rejected the brief. See `review-rollback.log:1` and the runnable `review-rollback.py`. This violates the explicit requirement at `brief.md:75`. Track cleanup responsibility before attempting the write, or publish the brief atomically with equivalent rollback, and cover partial-write failure plus retry.

Reproduce from this review directory:

```sh
TMPDIR="$PWD/review-tmp" PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=target/template/src:target/template/tests \
  python3 review-rollback.py
```

**Evidence and limits.** The target is the supplied self-contained patched checkout; no stale-target caveat applies. Production files were stashed for the red run and restored before the green run. The final tracked diff still contains only the three supplied changed files. Regression and suite commands were `PYTHONPATH=src python3 -m unittest discover -s tests -p test_split.py` and `PYTHONPATH=src python3 -m unittest discover -s tests`, respectively, from `target/template`, with temporary files confined under this review directory.

All six frozen gate logs were read. The C5 scanner's pass means only “no new test file,” not positive production-path verification (`gate-logs/C5-prod-path.log:10`); the independent regression supplies that evidence. Instance-scoped wrappers were not available here, so I reran their accessible underlying checks. Copier is unavailable in this review interpreter, preventing a fresh root render/update suite; the frozen log explicitly records those cases executing and passing (`gate-logs/T3-suite.log:38`, `:54`). This is a local rerun limitation, not an undischarged external dependency: the brief declares none and the captured original run exercised Copier. T4 remains deferred, not a missing-evidence finding.

The local target intentionally has one synthetic base commit. I therefore checked GitHub's main-branch commit history by each of the three affected paths and enumerated all closed-unmerged PRs via the API. The recent path histories corroborate the brief's cited work; the only closed-unmerged PR is #4, touching README.md alone (`review-unmerged.log:1`, `review-rejected-files.log:1`). No other checkout was consulted. The supplied target's integration template has no enumerated project-specific human-only items beyond its TODO (`target/template/docs/INTEGRATION.md.jinja:80`).

This review is advisory; it does not alter deterministic gate results or gate acceptance.
