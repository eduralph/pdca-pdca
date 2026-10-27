Review dependency-scoped stack bases so each bundle carries its declared prerequisites without unrelated bundles’ commits.

Source citations below resolve under `$PDCA_TARGET`; brief and evidence citations resolve in this review directory. The target includes #723 and matches the supplied patch (`git apply --reverse --check` passed); there is no target-state caveat.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The offline ancestry contract distinguishes declared work, unrelated work, carry failures and merged prerequisites with falsifiable outcomes; `brief.md:3`, `brief.md:16`, `brief.md:24`. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only the three production changes left the tests runnable and produced 19 assertion failures, including unrelated Z commits reaching B; `review-red.log:172`, `review-red.log:354`; test assertion: `template/tests/test_flow_dependency_scoped_bases.py:296`. |
| C3 Change | PASS | The patch addresses base selection and the obsolete merge-on-line check, with head bookkeeping needed by the prior iteration; it applies exactly to the supplied target and passes whitespace checking; `template/src/pdca_harness/flow.py:2678`, `template/src/pdca_harness/integrate.py:867`, `brief.md:33`. |
| C4 Verification (red→green) | PASS | After stash restoration, the same 19 tests passed independently; the frozen C4 log also records all affected suites green and the production-reverted leg red; `review-green.log:3`, `gate-logs/C4-verify.log:10`, `gate-logs/C4-verify.log:976`, `gate-logs/C4-verify.log:2636`. |
| C5 Causal adequacy | NEEDS-HUMAN [impl] | Preserve transitive edges through finished patchless prerequisites on resume — two independent real-git cases show either COMPLETE with missing prerequisite commits or an unjustified STOPPING; the graph excludes those nodes at `template/src/pdca_harness/flow.py:2597` and `template/src/pdca_harness/flow.py:983`, then drops their edges at `template/src/pdca_harness/flow.py:909`; `review-carried-patchless.log:8`, `review-carried-patchless-member.log:5`. |
| T1 Structure | PASS | Closure calculation and base construction remain in the flow/integration boundary, and base records are assigned before build leaves start; no additional structural defect found; `template/src/pdca_harness/flow.py:955`, `template/src/pdca_harness/flow.py:2691`. |
| T2 Shape | PASS | Independently reran docs lint and the host workflow’s renderer/link audit: both clean, 22 pages rendered; whitespace check clean; frozen docs and host-parity logs agree; `gate-logs/T2-docs.log:11`, `gate-logs/host-ci-docs.log:11`, `.github/workflows/docs-check.yml:36`. |
| T3 Runtime | PASS | Independent driver-suite run passed 2,573 tests (two skips); local root runner returned 77 for unavailable Copier, while frozen evidence explicitly records all 24 root tests executed and passed; `review-suite.log:1817`, `review-root-suite.log:6`, `gate-logs/T3-suite.log:54`. |
| T4 Contribution | N/A | Contribution artifacts are intentionally drafted after Check; the deferred gate owes its substantive audit to publish and is not a reproduced green; `gate-logs/T4-contribution.log:10`. |
| T5 Judgment | NEEDS-HUMAN | Confirm prior art by affected file path across merged history and closed/rejected work — this snapshot has one synthetic base commit and no remotes, while the brief documents selected flow history and an earlier rejection but not a complete closed-work search; `brief.md:27`; affected paths include `template/src/pdca_harness/flow.py:845` and `template/src/pdca_harness/integrate.py:716`. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether dependency-only PR ancestry with a retained combined integration check and whole-run stops fits the intended operator workflow — real-git tests establish offline behavior, but the resume defect below must be addressed before judging completeness; `brief.md:16`, `brief.md:22`, `template/tests/test_flow_dependency_scoped_bases.py:27`. |

**Implementation finding: finished patchless nodes sever the dependency graph on resume.**

`_carry_finished` admits only bundles with a patch into its carry candidates (`template/src/pdca_harness/flow.py:1243`; `template/src/pdca_harness/integrate.py:237`). The caller then passes only those actually carried to `_bundle_bases` (`template/src/pdca_harness/flow.py:2597`). Its `paths` graph contains scheduled bundles and carried bundles, so a finished patchless N is absent (`template/src/pdca_harness/flow.py:983`). `_ordered_after` discards the edge to N before `_closure` can traverse N’s prerequisites (`template/src/pdca_harness/flow.py:907`). This contradicts the transitivity already tested for a scheduled patchless N (`template/tests/test_flow_dependency_scoped_bases.py:325`).

I exercised two histories entirely through the patched production flow, using the supplied real-git fixture and its specified leaf/publish stubs:

- Run `[A, N, D, W]`, with `N Depends on A` and closed without a patch, `D Depends on N`, and `W Depends on A`. Initially fail D and W; reissue the same batch driving D and W. The carry takes A. D becomes COMPLETE on the real base and contains none of A, while W correctly contains A (`review-carried-patchless.log:1`).
- Run `[A, N, P, D]`, with patchless N depending on A, P depending on N, and D depending on P. Initially fail D after P is successfully built on A; reissue driving D. The carry takes A and P, but D’s members contain P alone. The run wrongly stops, calling A’s declared transitive work foreign (`review-carried-patchless-member.log:1`). No external rewrite or foreign branch was introduced.

Keep finished patchless bundles available for dependency traversal while retaining the clean-candidate restriction on actual base members. Add resume coverage for both the missing-work and false-stop outcomes. This is one implementation concern with two observed effects; the existing passing gates do not cover it. The fix removes the original integration-line cause rather than adding a capability probe; the symptom-guard smell-test does not fire.

The following reproduces both cases from this review directory with the patch applied. It writes fixture data only below the existing `review-tmp` directory:

```bash
cd "$PDCA_TARGET/template"
TMPDIR="$PDCA_TARGET/../review-tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 - <<'PYCODE'
from tests.test_flow_dependency_scoped_bases import DependencyScopedBases, TWO
from pdca_harness import state

outcomes = []
for through_member in (False, True):
    c = DependencyScopedBases()
    c.setUp()
    try:
        c._plan('A', TWO)
        c._plan('N', depends_on='A')
        c.close.add('N')
        if through_member:
            ids = ['A', 'N', 'P', 'D']
            c._plan('P', depends_on='N')
            c._plan('D', depends_on='P')
            c.failing.add('D')
            drive = ['D']
        else:
            ids = ['A', 'N', 'D', 'W']
            c._plan('D', depends_on='N')
            c._plan('W', depends_on='A')
            c.failing.update({'D', 'W'})
            drive = ['D', 'W']
        c._run(ids)
        c.failing.clear()
        c._run(ids, drive=drive)
        complete = c.results['D'] == state.COMPLETE
        has_a = complete and c.fx._ancestor(c._head('A'), c._head('D'))
        print('through_member:', through_member, 'results:', c.results,
              'D contains A:', has_a)
        print(c.err)
        outcomes.append(complete and has_a)
    finally:
        c.doCleanups()
assert all(outcomes), 'Resume must preserve the declared transitive A prerequisite'
PYCODE
```

The production stash was restored before all green and supplemental runs. Instance-scoped gate wrappers were not invoked from another checkout: production-import evidence was corroborated by the actual import and real flow calls (`template/tests/test_flow_dependency_scoped_bases.py:58`, `template/tests/test_flow_dependency_scoped_bases.py:210`), and frozen logs supplied the root-suite and deferred-contribution evidence. The brief’s required Python/git dependencies were exercised; Copier’s local absence is a reviewer-host limitation, not a patch defect or an unmet dependency for the ancestry tests.

<!-- pdca:leaf-complete -->
