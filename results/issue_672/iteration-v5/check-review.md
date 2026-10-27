Review issue #672: prevent a pre-wave carry from adding a fold-skipped bundle’s commits through another finished bundle, before its single push, and report the hold cause.

Source citations below resolve within `$PDCA_TARGET` (`target/`); evidence and brief citations resolve in this review directory. The disposable target matches the supplied patch and identifies base `d6057eb`; no stale-target caveat applies. This review is advisory.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief defines the excluded commit set, single-push invariant, six reproducible cases, and accepted limits precisely enough to assess the change; `brief.md:29`, `brief.md:35`. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only the two production files, retaining the new tests, reproduced all six assertion failures in 24 tests; `review-red.log:93`, `template/tests/test_flow_resume_stack_prereqs.py:521`. |
| C3 Change | PASS | The four changed files stay within the carry, fold, regression suite, and documented limits specified by the brief; `template/src/pdca_harness/flow.py:1116`, `docs/07-crosscutting.md:728`. |
| C4 Verification (red→green) | PASS | Restoring production yielded 94 passing carry/stack-base/same-wave tests after the six red assertions; the supplied C4 log independently agrees for all 24 carry cases; `review-green.log:25`, `gate-logs/C4-verify.log:107`. |
| C5 Causal adequacy | NEEDS-HUMAN [impl] | Correct incomplete hold-cause attribution: a conflicting Q containing P’s earlier commit but not its current tip omits P and gives the generic PR-open hint, contrary to the holder rule; reproduced against `template/src/pdca_harness/integrate.py:1064` in `review-shared-history.log:9`. |
| T1 Structure | PASS | The rebuild stays inside the existing integration lock, terminates by dropping bundles, and reaches the existing push only after filtering; ordinary folds do no work-set computation; `template/src/pdca_harness/integrate.py:581`, `template/src/pdca_harness/integrate.py:616`. |
| T2 Shape | PASS | Independently rerun docs lint, 22-page site rendering/internal-link audit, and diff whitespace check passed; the frozen host-parity log agrees; `review-docs-lint.log:1`, `review-docs-render.log:3`, `gate-logs/host-ci-docs.log:14`. |
| T3 Runtime | PASS | Independently ran 2,465 driver tests successfully (two skips); frozen evidence records 24 successful root tests, while the local root rerun lacked importable Copier; `review-driver-suite.log:1817`, `gate-logs/T3-suite.log:54`, `review-root-suite.log:6`. |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the substantive audit is deferred to the mandatory publish rerun, not cleared here; `gate-logs/T4-contribution.log:10`. |
| T5 Judgment | NEEDS-HUMAN | Confirm the affected-path prior-art review, including merged history and closed/rejected work: the brief lists it, but this single-commit copy has no remote/history evidence to independently corroborate it; `brief.md:40`, `review-prior-art.log:1`. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Accept the intentionally broader holds of unrelated/shared-history bundles and the continued-line exception: these trade throughput for preventing newly added skipped work and leave previously pushed work intact; `brief.md:43`, `docs/07-crosscutting.md:748`. |

The C5 finding is a diagnostic contract defect, not an observed commit leak. The independent real-git case creates P’s `p1`, branches Q from it without a dependency edge, then adds P’s `p2` changing `base.txt` and Q’s change to `other.txt`. Main independently changes both files. `git merge-tree --write-tree` confirms P and Q merge cleanly with each other, so the brief’s exceptions for mutually conflicting bundles or conflicts caused by later-dropped bundles do not cover this case. Both instead conflict with main. The carry correctly holds D, keeps `p1` off the line, carries X, builds E, and pushes once. However, Q’s message names only its own conflict and says to get Q’s PR open; it never names P. `_built_on_skipped` checks only whether P’s complete current tip is in Q’s work, missing the shared earlier commit (`template/src/pdca_harness/integrate.py:1063`). The brief explicitly requires the cause even when the holder itself conflicts (`brief.md:35`). Extend cause attribution to this case with a regression while preserving acyclic explanations.

The reproducer is retained as `review-shared-history.py`; from this directory run:

```bash
TMPDIR="$PWD/review-tmp" PYTHONPATH="$PWD/target/template/src:$PWD/target/template" PYTHONDONTWRITEBYTECODE=1 python3 review-shared-history.py
```

It currently fails one assertion; `review-shared-history.log:16` records that P and Q merge cleanly with each other. The supplied criterion-(5) test uses a Q containing P’s entire tip and therefore misses this case (`template/tests/test_flow_resume_stack_prereqs.py:592`).

The production-path scanner’s frozen PASS is explicitly a no-op because no new test file was added (`gate-logs/C5-prod-path.log:10`). I instead checked the existing fixture’s delegation to real `integrate.fold` and `_drive_and_act` (`template/tests/test_flow_resume_stack_prereqs.py:133`, `template/tests/test_flow_resume_stack_prereqs.py:152`) and exercised it above. No capability-probe/load-time symptom guard was introduced.

All configured gate logs were available. Instance-root wrappers were adjudicated from their frozen logs and underlying commands rerun where available. The local root-suite exit 77 is a host limitation, not a patch failure or an unmet fix dependency: the frozen root run actually exercised rendering and update compatibility (`gate-logs/T3-suite.log:38`), and the fix’s Python/git dependency was exercised directly. The only supplied integration §4 is an unfilled template, with no additional enumerated human-only checks (`template/docs/INTEGRATION.md.jinja:35`). Production files were restored after the red leg; the final target diff is unchanged. No builder rationale was consulted.

<!-- pdca:leaf-complete -->
