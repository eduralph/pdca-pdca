Review merge-mode diagnostics for blocked review remarks: report thread locations, preserve remarks and host signals in the bundle, and restore the PR to draft.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The offline acceptance criteria cover both merge policies, empty remarks, UNKNOWN polling, outdated lines, and requested changes; the latest carry-forward explicitly resolves the attribution scope (brief.md:4; brief.md:32). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing production changes reproduced the generic refusal instead of the required thread diagnosis: 28 tests ran with 54 assertion failures and no import errors (template/tests/test_merge_review_remarks.py:234; reviewer-red.log:221; reviewer-red.log:546). |
| C3 Change | PASS | Diagnosis occurs at the failed-merge boundary under both policies, preserving merge refusal and the existing draft rollback rather than changing merge eligibility (template/src/pdca_harness/merge.py:908; template/src/pdca_harness/merge.py:918; template/src/pdca_harness/merge.py:499). |
| C4 Verification (red→green) | PASS | After stash restoration, all 96 selected tests passed; the complete patch also passes reverse-application and whitespace checks, and matches the disposable target (reviewer-green.log:3; template/tests/test_merge_review_remarks.py:230; gate-logs/C4-verify.log:723). |
| C5 Causal adequacy | PASS | Production-path tests cover all requested legs and previous defects: later thread pages, stale-artifact removal, shared wait limits, unreadable threads, and preserved host signals; no capability-probe symptom guard was introduced (template/tests/test_merge_review_remarks.py:251; template/tests/test_merge_review_remarks.py:283; template/tests/test_merge_review_remarks.py:511; template/tests/test_merge_review_remarks.py:613; template/tests/test_merge_review_remarks.py:361). |
| T1 Structure | PASS | The diagnostic reuses the PR reader and refusal lifecycle, and archives its per-attempt artifact through the existing state list, keeping ownership and retry behavior coherent (template/src/pdca_harness/merge.py:533; template/src/pdca_harness/merge.py:731; template/src/pdca_harness/state.py:156). |
| T2 Shape | PASS | Independent docs lint, 22-page rendering/link audit, six checker tests, 458 relative-link checks, and the 12-ADR audit passed; the documented stop matches the accepted behavior (docs/07-crosscutting.md:887; reviewer-docs-render.log:3; reviewer-doc-checkers.log:9; reviewer-doc-links.log:1; reviewer-adr.log:1). |
| T3 Runtime | PASS | Independent driver discovery passed 2,675 tests with two skips; frozen evidence also records 50 passing root render/update tests, whose local rerun lacks importable copier (reviewer-suite.log:1819; gate-logs/T3-suite.log:80; reviewer-root.log:6). |
| T4 Contribution | N/A | Contribution artifacts are intentionally absent during Check; the deferred gate owes its substantive audit at publish (gate-logs/T4-contribution.log:10). |
| T5 Judgment | PASS | The human explicitly chose inferred blocker wording with visible counter-signals and cleared prior art; the new REVIEW_REQUIRED regression satisfies that decision without expanding into branch-rule discovery (brief.md:32; brief.md:39; template/tests/test_merge_review_remarks.py:361; template/src/pdca_harness/merge.py:643). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Complete the held real-GitHub read-only check and judge operational usefulness — real API payloads and host behavior were not exercised, so compatibility evidence rests on stub responses; BLOCKED plus remarks remains an inference about the actual rule blocking the merge (brief.md:39; template/src/pdca_harness/merge.py:606; template/src/pdca_harness/merge.py:662). |

Independent verification used `git stash push` for the two production files while retaining the tests, ran the new suite against the base, restored the stash, and ran the three affected test modules plus full driver discovery. The target was restored to the supplied patch; all source citations above resolve there. The tests import the target production package and call `merge.merge_wave`, corroborating `gate-logs/C5-prod-path.log:10`.

The local root-suite runner exited 77: 45 tests ran, three skipped, and no copier-dependent case executed because this interpreter cannot import copier (`reviewer-root.log:3`, `reviewer-root.log:6`). This is a reviewer-host limitation, not a patch failure. The frozen root-suite log explicitly shows render/update cases executing and the 50-test suite passing (`gate-logs/T3-suite.log:68`, `gate-logs/T3-suite.log:80`). The instance-scoped gate wrappers were adjudicated using their captured logs; documentation checks were independently run through the target's own tools.

Affected-file history inspection ran for all six changed paths, recorded in `reviewer-prior-art.log:4`. The target contains only one synthesized base commit, so it cannot independently reconstruct merged history or closed/rejected work. The explicit human clearance in `brief.md:39` is retained.

For the held live check, use an authenticated `gh` in a trusted checkout containing this patch, with a PR that has known unresolved threads. From the repository root, run:

```bash
export PR_URL='https://github.com/OWNER/REPO/pull/NUMBER'
PYTHONPATH=template/src python3 - <<'PY'
import json
import os
from pdca_harness import merge, merged
url = os.environ['PR_URL']
print('state:', json.dumps(merged._pr_view(
    url, 'mergeStateStatus,reviewDecision,latestReviews'), indent=2))
print('threads:', json.dumps(merge._review_threads(url), indent=2))
PY
```

These calls only read the PR. Confirm non-null responses, compare thread IDs/counts, authors, bodies, URLs and locations with GitHub, and include an outdated thread to check original-line reporting. Where available, exercise a PR with more than 100 total threads to check real cursor pagination. The offline REVIEW_REQUIRED-plus-open-thread case already passed; the human must assess the diagnostic's usefulness when the host's actual blocking rule differs from the named remarks.

<!-- pdca:leaf-complete -->
