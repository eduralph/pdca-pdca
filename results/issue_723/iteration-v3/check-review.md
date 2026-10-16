Review the new per-bundle integration-base builder: publish exactly the fetched base plus selected bundles while preserving the run line and its safeguards.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The sibling API, destination naming, push policy, safeguards, and caller exclusion have concrete real-git acceptance cases; `brief.md:3`, `brief.md:17`, `target/template/tests/test_integrate_bundle_base.py:149`. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing the production change made all 23 tests execute and error at the absent entry point, rather than fail module import; `reviewer-red.log:14`, `reviewer-red.log:336`, `target/template/tests/test_integrate_bundle_base.py:66`. |
| C3 Change | PASS | The patch stays within the integration module and one new test file; the existing fold changes only by extracting its owner lookup, with no caller changes; `target/template/src/pdca_harness/integrate.py:581`, `patch.diff:303`. |
| C4 Verification (red→green) | PASS | Restoring the production patch independently changed the same 23 tests from red to green; this confirms the shipped cases, with the additional missed case recorded under C5; `reviewer-red.log:338`, `reviewer-green.log:3`, `gate-logs/C4-verify.log:10`. |
| C5 Causal adequacy | NEEDS-HUMAN [impl] | Correct ownership of member commits brought through topic merges and add a regression: an independent real-git probe rejects a valid A-only base as containing excluded C's work, so ordinary merge history can stop dependency builds; `target/template/src/pdca_harness/integrate.py:946`, `target/template/src/pdca_harness/integrate.py:949`, `reviewer-extra-probes.log:5`. |
| T1 Structure | PASS | The new builder uses the existing per-target lock, worktree, and production merge safeguards, preserving the established integration boundary; `target/template/src/pdca_harness/integrate.py:802`, `target/template/src/pdca_harness/integrate.py:839`. |
| T2 Shape | PASS | Independent docs lint, site rendering/link audit, and patch whitespace checks passed; both frozen docs gates also report clean results; `gate-logs/T2-docs.log:11`, `gate-logs/host-ci-docs.log:11`. |
| T3 Runtime | PASS | Independently ran all 480 integration/flow tests successfully; frozen evidence additionally records 24 root tests and 2,549 driver tests passing, with two driver skips; `reviewer-runtime.log:498`, `gate-logs/T3-suite.log:54`, `gate-logs/T3-suite.log:1874`. |
| T4 Contribution | N/A | Contribution artifacts are intentionally drafted after Check; the substantive contribution audit must run at publish, as the deferred gate records; `gate-logs/T4-contribution.log:10`. |
| T5 Judgment | NEEDS-HUMAN | Confirm path-based merged and closed/rejected prior art for both affected files before accepting novelty: the brief lists prior integration history, but the supplied target has only one snapshot commit and no remotes, so the closed/rejected-work check cannot be confirmed; `brief.md:22`, `reviewer-prior-art.log:1`. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether this standalone API and its ancestry-ownership contract are suitable for the later dependency-scoped flow after C5 is resolved; no caller is changed in this child, so passing API tests cannot establish end-to-end fitness; `brief.md:17`, `target/template/src/pdca_harness/integrate.py:723`. |

The C5 finding is a reproduced implementation defect. A publishes its own commit and merges an independently authored topic branch with `--no-ff`. The run folds A; C then branches from that run line and adds its own unrelated commit. Building B from `[A]`, with A's actual recorded head and C excluded, should succeed: C's own commit is absent from A, and every requested commit belongs to A. Instead the build reports A's topic commit as C's work and pushes nothing (`reviewer-extra-probes.log:1`).

`_foreign_work` subtracts other heads only when those heads lie on the excluded branch's first-parent chain (`target/template/src/pdca_harness/integrate.py:947`). Here A entered C's history through the run's merge, so that subtraction does not apply. The remaining filter recognizes other bundles' first-parent chains only; A's topic commit is off A's first-parent chain and is consequently misattributed to C (`target/template/src/pdca_harness/integrate.py:940`, `target/template/src/pdca_harness/integrate.py:949`). The shipped tests cover an excluded bundle's topic merge and a member's ordinary commits separately, but miss this combination (`target/template/tests/test_integrate_bundle_base.py:308`, `target/template/tests/test_integrate_bundle_base.py:330`). Preserve the existing contamination refusals while correcting this case.

Re-run the independent probe from this review directory:

```sh
TMPDIR="$PWD/reviewer-tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/target/template/src" python3 reviewer-extra-probes.py
```

Evidence boundaries: the disposable target matches the supplied patch (`git apply --reverse --check` passed), and the patch was restored after the red leg. Python and real git were exercised without tool substitutions. The instance-scoped gate wrappers are not supplied here; their frozen logs were read, and available underlying tests, docs tools, and the production-import scanner were run directly. The full root/driver totals above are frozen-log evidence, not an independent full-suite claim. The production-import scanner passed, but its import heuristic does not discharge C5. No optional-capability/load-time guard smell was found. The supplied target contains only the generic `template/docs/INTEGRATION.md.jinja`, whose human-only list is an unfilled placeholder, rather than a populated instance ruleset.

<!-- pdca:leaf-complete -->
