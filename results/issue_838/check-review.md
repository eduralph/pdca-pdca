Review merge-mode diagnostics that name unresolved review remarks, preserve them in the bundle, and restore a blocked PR to draft.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The offline contract defines both merge policies, generic refusals, UNKNOWN polling, outdated lines, and changes-requested reviews, with explicit scope decisions; brief.md:4, brief.md:32, brief.md:44. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only the two production files leaves the new tests importable and produces 63 assertion failures across 30 tests, including the missing diagnostic; reviewer-red.log:272, reviewer-red.log:648; template/tests/test_merge_review_remarks.py:242. |
| C3 Change | PASS | The change stays within the approved diagnostic outcome and its artifact lifecycle; the human explicitly retained this scope despite size, and no new configuration or remark remediation appears; brief.md:44; template/src/pdca_harness/merge.py:931; template/src/pdca_harness/state.py:156. |
| C4 Verification (red→green) | PASS | Restoring the stash makes all 98 focused tests pass; the independent red leg fails on behavior rather than import or changed return arity, corroborating the frozen gate; reviewer-green.log:3; gate-logs/C4-verify.log:825; template/tests/test_merge_review_remarks.py:240. |
| C5 Causal adequacy | PASS | Production-path regressions cover pagination, stale records, shared wait limits, unknown thread reads, host selection, and partial writes; the approved inference retains the host's decision and error for interpretation; template/tests/test_merge_review_remarks.py:262, template/tests/test_merge_review_remarks.py:412, template/tests/test_merge_review_remarks.py:562, template/tests/test_merge_review_remarks.py:664, template/tests/test_merge_review_remarks.py:747. |
| T1 Structure | PASS | The helpers retain the existing refusal/draft-restoration path and reuse the existing atomic-record writer and archive registry; production-import scanning also passes; template/src/pdca_harness/merge.py:655, template/src/pdca_harness/merge.py:933, template/src/pdca_harness/state.py:156. |
| T2 Shape | PASS | Independently rerun docs lint, 64-page rendering/link audit, relative-link and ADR scanners, six checker tests, and diff whitespace checks pass; the new operational wording matches the approved inference; docs/07-crosscutting.md:929; gate-logs/T2-docs.log:11; gate-logs/host-ci-docs.log:14. |
| T3 Runtime | PASS | Independent driver discovery passes 2,697 tests (two skips); frozen evidence additionally shows 50 root tests including render/update compatibility passing, while this review host cannot import Copier; reviewer-suite.log:1819; gate-logs/T3-suite.log:80; reviewer-root-suite.log:6. |
| T4 Contribution | N/A | Contribution artifacts are intentionally absent at Check; the substantive audit must rerun at publish, as the deferred gate records; gate-logs/T4-contribution.log:10. |
| T5 Judgment | PASS | Prior art and the enlarged single-outcome scope were explicitly cleared by the human; the known ambiguity of BLOCKED is disclosed and the requested diagnostic signals are tested, so no new implementation concern remains; brief.md:39, brief.md:44; template/tests/test_merge_review_remarks.py:412. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether these diagnostics and records serve merge-mode operators, and discharge the held live read-only GitHub check — real gh/GraphQL was not exercised, so behavioral evidence rests on stubs; brief.md:49; template/tests/test_merge_review_remarks.py:89; template/src/pdca_harness/merge.py:574. |

Code citations resolve against `/tmp/pdca-review-49neea4v/target` (`$PDCA_TARGET`); input and evidence citations resolve against the review cwd. The disposable target contains the patch, and the stash/pop round-trip preserved every tracked patch hunk. No implementation edits were made.

Independent evidence: `reviewer-red.log` records the new regression module against the pre-fix production tree; `reviewer-green.log` records the three affected test modules after restoration. The full driver rerun is in `reviewer-suite.log`. The production-import scanner confirms the new tests import `pdca_harness`. Documentation checks found 623 relative links across 71 Markdown files with zero broken links, and 12 ADRs with zero index problems.

The root rerun exited 77 because `/usr/bin/python3` cannot import Copier; 45 tests ran with three skips (`reviewer-root-suite.log:3`). This is a review-host limitation, not a patch failure. The frozen T3 log explicitly shows actual render and update cases executing successfully (`gate-logs/T3-suite.log:38`, `gate-logs/T3-suite.log:66`) and a 50-test root run passing. Instance-scoped gate wrappers are unavailable here; all six named frozen logs were read, and their substantive output supports the recorded results. The deferred contribution row supplies no green claim.

Prior-art inspection by affected paths in the supplied target exposes only the synthetic base commit, so merged and closed/rejected history cannot be independently reconstructed locally. The explicit human clearance in `brief.md:39` discharges that decision; it is not presented as a newly reproduced history search. The scope override in `brief.md:44` likewise remains effective. No optional-capability probe masking an eager/load-time cause was introduced.

For the held external check, once the human proceeds, set `PR_URL` to an existing PR with known unresolved threads on the intended host and run the following from the target's `template/` directory. Both helpers only read host state:

```bash
PYTHONPATH=src python3 - <<'READONLY'
import json
import os
from pdca_harness import merge, merged
pr = os.environ["PR_URL"]
print(json.dumps(merged._pr_view(pr, "mergeStateStatus,reviewDecision,latestReviews"), indent=2))
print(json.dumps(merge._review_threads(pr), indent=2))
READONLY
```

Compare thread IDs, paths, current/original lines, first-comment bodies, authors and URLs with the PR, including a later page when available. A `null` thread result means the real query has not been validated. Judge diagnostic usefulness with the documented caveat: BLOCKED plus an open remark does not establish which branch rule actually prevented merging (`template/src/pdca_harness/merge.py:620`). This external check remains pending under the brief's explicit hold.

<!-- pdca:leaf-complete -->
