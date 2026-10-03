Review issue #593: make stack-mode PRs target the real base and carry published commits forward without rewriting the integration line, while holding dependents of failed publishes.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief defines testable ancestry, PR-target, failure-isolation and diff-shrink contracts, including the iteration corrections; target/template/src/pdca_harness/integrate.py:235 and target/docs/07-crosscutting.md:642 ground the intended behavior. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only production changes leaves 170 tests runnable and produces 22 assertion failures plus 5 expected missing-API errors, including wrong PR bases and lost ancestry; review-red.log:747, review-red.log:804, review-red.log:815. |
| C3 Change | FAIL | A prerequisite merged and deleted between folds can disappear from the next wave's base: continuing from the old tip and skipping the deleted branch never incorporates the updated target; target/template/src/pdca_harness/integrate.py:352 and target/template/src/pdca_harness/integrate.py:382; reproduced in review-deleted-merged.log:3. |
| C4 Verification (red→green) | PASS | Restoring production changes independently turns the same 170 tests green; this confirms the shipped regression coverage, not the additional failing scenario below; review-green.log:474, gate-logs/C4-verify.log:2187. |
| C5 Causal adequacy | FAIL | Replacing copied commits addresses the original cause, but “merged into the target” does not establish “present in the continuing integration line”; the deleted-branch test never actually merges its fixture, leaving this incorrect assumption untested; target/template/src/pdca_harness/integrate.py:382, target/template/tests/test_integrate_stack_bases.py:296. |
| T1 Structure | PASS | Shared candidate/ref resolution keeps failure holding aligned with folding, and sorted target locks still cover folding plus re-gating; target/template/src/pdca_harness/integrate.py:119, target/template/src/pdca_harness/integrate.py:302, target/template/src/pdca_harness/flow.py:1882. |
| T2 Shape | PASS | Independently reran docs lint, the 22-page render/link audit, the production-import scanner and git diff whitespace checks, all successfully; review-scanners.log:1; frozen host-parity output agrees at gate-logs/host-ci-docs.log:10. |
| T3 Runtime | PASS | Independent driver suite: 2,244 tests, 2 skips, no failures; root render/update suite could not be rerun because copier is not importable locally, but its frozen log explicitly reports 24 tests with no skips and OK; review-suite.log:1775, gate-logs/T3-suite.log:54. |
| T4 Contribution | N/A | Contribution artifacts are intentionally absent at Check; their substantive audit must rerun at publish, as recorded in gate-logs/T4-contribution.log:10. |
| T5 Judgment | NEEDS-HUMAN | Confirm the vendored-model edits and hold-only-dependents policy, and independently settle path-based merged/closed-rejected prior art—these affect process semantics and duplication risk; target/template/PCDA/quality-cycle/09-parallel-lanes.md:69, target/template/src/pdca_harness/flow.py:1860, brief.md:271, brief.md:287. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the stack is usable on the live host: GitHub Files changed/Update branch and the real gh merged-PR lookup were not exercised, so that evidence remains local Git plus mocked host responses; target/docs/07-crosscutting.md:649, target/template/src/pdca_harness/merged.py:46, brief.md:208. |

One concrete defect remains (P2): preserve merged prerequisites when their branches disappear between folds. Publish A, fold A and record T1; publish B from T1; merge A and B into main with merge commits and delete B's branch; then fold [A, B] with this run's recorded T1. Fetch sees the new main, but checkout continues T1. The missing-branch path returns successfully because B is merged. The fold pushes the unchanged T1, so C, depending on B, builds without B. This occurs within one run; it is not the excluded cross-run-resume case.

The independent real-Git experiment observed:

```text
main files: ['a.txt', 'b.txt', 'base.txt']
integration files: ['a.txt', 'base.txt']
B carried into next wave: False
integration remained at first-fold tip: True
```

The full observation is in review-deleted-merged.log:1. Only the host's merged-status answer was mocked; the branches were actually published, merged and deleted in local Git. Before skipping a deleted merged branch, the implementation needs to ensure its contribution is carried by the continuing line, incorporating the appropriate merged history without rewriting that line. Add a regression with an actual merge between two folds; the current target/template/tests/test_integrate_stack_bases.py:296 case deletes an unmerged branch and asserts its file is absent, so it cannot establish this invariant.

Reproduce from target/template with TMPDIR pointing inside this review directory and PYTHONPATH=src:

```python
from tests.test_integrate_stack_bases import StackFoldGit, TARGET, LINE, _git
from pdca_harness import integrate
from unittest import mock

case = StackFoldGit()
case.setUp()
a = case._publish("A", {"a.txt": "a\n"})
first = integrate.fold(case.cfg, [a], folded_this_run={})
tip = integrate.pushed_tip(first[TARGET][1])
b = case._publish("B", {"b.txt": "b\n"}, cut_from=f"origin/{LINE}")
case._merge_pr("A")
case._merge_pr("B")
_git(case.origin, "branch", "-D", "fix/B")
with mock.patch("pdca_harness.merged.is_merged", return_value=True):
    folded = integrate.fold(case.cfg, [a, b], folded_this_run={TARGET: tip})
assert (folded[TARGET][1] / "b.txt").exists()  # fails on the supplied patch
```

The production stash was popped successfully. A reverse-application check of patch.diff passes against the restored target, and the stash list is empty. No production fixes were made. The C5 capability-probe smell-test found no added optional-capability probe masking a load-time cause; the C5 failure above is the separately demonstrated ancestry assumption.

For prior art, the brief reports searches by integrate.py and publish.py across merged history and closed-unmerged PRs. My path-scoped git log investigation returns only the harness's synthetic base commit, `95e965c pre-fix base 24c7f83...`; the disposable target has no remotes or closed-PR evidence. Thus that upstream/closed-rejected conclusion cannot be independently confirmed from this bundle. The provided INTEGRATION file is a template with TODO human-only entries; the explicit vendored-model human-review requirement is supplied by brief.md:287 and is retained above.

To discharge live-host validation, use a disposable GitHub repository and a rendered instance configured with wave_mode = "stack" and that repository as the briefs' target. Create A and C as independent wave-0 changes and B with Depends on: A, C; run `pdca flow A C B --no-act` using their actual issue IDs. Check that all PRs target main. Merge A and C with merge commits, inspect B's Files changed, use Update branch to merge main into B, and verify that only B's change remains before merging B. Separately exercise an A → B → C run with B merged and its branch deleted before the second fold: let the real `gh pr view <B-PR-URL> --json state` report MERGED, and verify that the integration tip still contains B before C builds. The current patch fails that last content check in the local reproduction above. These are human execution steps, not actions taken by this review.
