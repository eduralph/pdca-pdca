Review issue #395: prevent same-wave textual conflicts from being published before non-final stack-mode folds, while preserving final-wave and merge-mode behavior.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The six observable acceptance cases distinguish textual conflict, ready-only participation, failed partner pushes, and final-wave compatibility; brief.md:11 and template/tests/test_flow_same_wave_prepublish.py:228. |
| C2 Reproduction (red pre-fix) | PASS | Stashing the tracked fix reproduced seven assertion failures in twelve new-module tests, including B reaching origin before its conflict hold; review-red.log:42 and template/tests/test_flow_same_wave_prepublish.py:234. |
| C3 Change | PASS | The publication decision precedes pushes and retains the specified stack/non-final boundary; source and restored patch agree under reverse-apply checking; template/src/pdca_harness/flow.py:3139. |
| C4 Verification (red→green) | PASS | After stash-pop, all 52 affected tests passed; the independent red leg failed behavior assertions without import errors; review-green.log:3, review-red.log:94, and template/tests/test_flow_same_wave_prepublish.py:169. |
| C5 Causal adequacy | NEEDS-HUMAN [impl] | Preserve conflict prevention when staging a trial commit fails — one injected git-add failure still pushed both conflicting branches and created both PRs because a failed candidate disappears from the trial; template/src/pdca_harness/integrate.py:890, template/src/pdca_harness/integrate.py:850, and review-trial-stage-failure.log:2. |
| T1 Structure | PASS | The trial shares publication's base-selection rule and the fold's conflict rule under sorted integration locks, avoiding a separate definition of a same-wave clash; template/src/pdca_harness/publish.py:826 and template/src/pdca_harness/integrate.py:803. |
| T2 Shape | PASS | Independent docs lint, 22-page site render/link audit, production-import scanner, and diff whitespace checks passed; docs/07-crosscutting.md:724, gate-logs/T2-docs.log:16, and gate-logs/host-ci-docs.log:15. |
| T3 Runtime | PASS | Independent driver suite passed 2,642 tests (two skips); root coverage is supported by the frozen log's executed render/update cases, since this interpreter lacks copier; review-suite.log:1819, gate-logs/T3-suite.log:42, and review-root-suite.log:6. |
| T4 Contribution | N/A | Contribution texts are absent by design during Check; the substantive contribution audit must rerun at publish, as the deferred gate records; gate-logs/T4-contribution.log:10. |
| T5 Judgment | NEEDS-HUMAN | Approve withholding otherwise independent siblings when a target's trial remains unavailable — publishing only the first bundle protects against unknown conflicts but delays accepted work beyond the brief's normal sibling-publication behavior; docs/07-crosscutting.md:731 and template/src/pdca_harness/integrate.py:827. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Accept this as a partial resolution of #395 with final-wave/one-wave conflicts still publishable, and require the C5 failure path to be corrected before relying on prevention; template/src/pdca_harness/flow.py:3142, template/tests/test_flow_same_wave_prepublish.py:354, and brief.md:19. |

Source citations above are relative to `$PDCA_TARGET`; review and gate evidence paths are relative to this report. The target was readable and matched the supplied patch. The stash was popped, and `git apply --reverse --check ../patch.diff` succeeded afterward. No production or test source was edited by the reviewer.

The C5 finding is an implementation defect, not an observed host failure. `_would_be` returns `None` for checkout, apply, staging, or commit failure, and `_same_wave_trial` silently omits that bundle. Consequently an integration-worktree failure does not enter the retry/untried path. The assumption that publishing must fail at the same step is false: publishing uses the primary checkout and runs later. In the independent experiment, the first integration `git add --all` returned 1, subsequent git operations ran normally, and both issue_10 and issue_11 reached the real bare origin with recorded PR-create calls. Only the later fold held issue_11, reproducing the original unwanted outcome (review-trial-stage-failure.log:1). Raise/propagate trial-construction failures into retry and conservative withholding, and add regression coverage for staging/commit failures as well as fetch failures. The existing fetch-failure cases at template/tests/test_flow_same_wave_prepublish.py:387 do not cover this path.

The experiment is reproducible from this sandbox root with the existing fixture (all temporary fixtures stay under the provided root):

```bash
TMPDIR="$PWD/review-tmp" PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH="$PWD/target/template/src:$PWD/target/template" python3 - <<'PYTEST'
from unittest import mock
from tests.test_flow_same_wave_prepublish import SameWavePrepublish, integrate
case = SameWavePrepublish()
case.setUp()
real_git = integrate._git
failed = []
def git(wt, *args):
    if args[:2] == ('add', '--all') and not failed:
        failed.append(True)
        return 1
    return real_git(wt, *args)
try:
    case._on_base({'shared.txt': 'x\n'})
    ids = case._pair({'shared.txt': 'ten\n'}, {'shared.txt': 'eleven\n'})
    with mock.patch.object(integrate, '_git', git):
        case._run(ids)
    print('injected:', bool(failed))
    for iid in ('10', '11'):
        print(iid, 'pushed:', case.fx._has(case._branch(iid)),
              'PR created:', case._pr_created(iid))
    print('holds:', case.holds)
finally:
    case.doCleanups()
PYTEST
```

Prior-art checking ran by all nine affected file paths: main-branch commit history plus file-list intersections across all 303 closed/merged PRs, with no truncated PR file lists (review-prior-art.log:10 and review-prior-art.log:139). Related merged #690 supplies the existing fold-time hold; closed-unmerged #638/#639/#648/#649/#598/#599/#600 concern other scheduling/gating work. No earlier pre-publish implementation was identified. This is a bounded prior-art conclusion, not proof of absence from every discussion. No `INTEGRATION.md` was present in the target to supply additional enumerated human-only items.

The frozen C4 log includes red-leg AttributeErrors from existing tests that mock the newly added helper. Those errors were not used as reproduction evidence: the independent red run selected the new module, which ran all twelve cases and failed seven assertions. The frozen runtime log explicitly shows root rendering and update compatibility executing successfully (gate-logs/T3-suite.log:38 and gate-logs/T3-suite.log:54); the local root rerun exited 77 because copier was not importable, so it supplies no additional render/update verification. This host caveat does not establish a patch defect or erase the frozen executed evidence. The brief declares no external dependencies, and the real-git acceptance topology was exercised as specified, with only GitHub responses stubbed.

<!-- pdca:leaf-complete -->
