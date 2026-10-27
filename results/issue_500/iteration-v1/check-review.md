Review issue #500: make merge mode retarget a PR to its bundle’s resolved target, or refuse before marking it ready, while rejecting batch-produced targets.

Source citations below are relative to `$PDCA_TARGET` (`/tmp/pdca-review-efjn2umm/target`); evidence files are relative to this review directory. This report is advisory.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The intended target, refusal order, unchanged ready state on refusal, and both merge policies have falsifiable acceptance cases; source placement agrees with the brief at template/src/pdca_harness/merge.py:558 and template/tests/test_merge_retarget.py:126. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only the production changes reproduced the unsafe pre-fix behavior: five new tests ran with ten assertion failures, including merging despite a failed retarget and a batch-produced target; reviewer-red.log:1, template/tests/test_merge_retarget.py:147. |
| C3 Change | PASS | The patch stays within the specified merge-time behavior, documentation, and fixture adjustments; existing target parsing and producer detection remain the authorities at template/src/pdca_harness/merge.py:478 and template/src/pdca_harness/publish.py:808. |
| C4 Verification (red→green) | PASS | Restoring the stashed production changes made all 84 merge-related tests pass independently; this confirms the specified offline cases, with the additional invariant gap recorded under C5; reviewer-green.log:4, template/tests/test_merge_retarget.py:127. |
| C5 Causal adequacy | NEEDS-HUMAN [impl] | Close the observed base-change gap before relying on the target invariant — after successful retargeting, a base change during check reads is observed by the final read yet still merges into the wrong branch; template/src/pdca_harness/merge.py:567, template/src/pdca_harness/merge.py:668; reproduced in reviewer-base-race.log:2. |
| T1 Structure | PASS | The check shares publish’s target parser and batch ownership rule, and its refusal precedes ready-state mutation under both policies; template/src/pdca_harness/merge.py:478, template/src/pdca_harness/merge.py:487, template/src/pdca_harness/merge.py:567. |
| T2 Shape | PASS | Independent whitespace checking, docs lint, site render with link audit, and production-import scanning passed; the two frozen docs gates agree; gate-logs/T2-docs.log:16, gate-logs/host-ci-docs.log:15. |
| T3 Runtime | PASS | Independent focused coverage passed 84 tests; the readable frozen suite log records 24 root tests passing and 2,635 driver tests passing with two skips, rather than an unexercised-suite success; gate-logs/T3-suite.log:54, gate-logs/T3-suite.log:1876. |
| T4 Contribution | N/A | Contribution artifacts are deliberately drafted after Check; the deferred row explicitly assigns their substantive audit to publish, so there is no missing verification to clear here; gate-logs/T4-contribution.log:10. |
| T5 Judgment | NEEDS-HUMAN | Approve unattended retargeting as a reversal of the previous promise, or choose the brief’s refuse-only fallback — changing a base can enlarge the PR’s contribution; docs/07-crosscutting.md:887 and docs/07-crosscutting.md:905, publish policy at template/src/pdca_harness/publish.py:288. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether merging after retarget without fresh CI for the new base is acceptable — live GitHub retarget/check provenance was not exercised, so evidence rests on a stub that always reports green; template/tests/test_merge_retarget.py:83, template/src/pdca_harness/merge.py:642; the brief’s “External dependencies: none” does not discharge that hosted behavior. |

Independent verification used `TMPDIR` inside this review directory. The production changes were stashed for the red run and restored before the green run; the submitted source remains unchanged. The green command was `PYTHONPATH=target/template/src python3 -m unittest discover -s target/template/tests -p 'test_merge*.py'`. Gate wrappers belong to the originating instance and are absent here as expected; all six supplied logs were readable. Broad-suite results above are from the frozen log, not an independently repeated full suite. The production-import scanner confirms an import, not live host behavior.

The C5 counterexample used the existing test host with one additional behavior: on `gh pr checks`, change its base back from `main` to `fix/old-parent`. With `merge_requires="all"`, successive PR views reported `fix/old-parent`, `main` (retarget confirmation), `main`, then `fix/old-parent` (the final read). The driver returned 0 and called `gh pr merge` while the host base was `fix/old-parent`, with no stderr. Both branches may legitimately have the same tip; an unchanged head and successful ancestry check cannot establish branch identity. The final `_base_read` discards that identity before the merge. This is an already-observed mismatch, not merely an edit racing after the final read. Preserve and compare the resolved target on later base reads and add a regression that changes the host base during check polling.

To independently repeat that probe from this directory, reuse the submitted offline fixture (all host operations remain stubbed):

```sh
TMPDIR="$PWD/review-tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=target/template/src python3 - <<'PYPROBE'
import importlib.util
import tempfile
from pathlib import Path
spec = importlib.util.spec_from_file_location("retarget", "target/template/tests/test_merge_retarget.py")
t = importlib.util.module_from_spec(spec)
spec.loader.exec_module(t)
class ChangingHost(t._Host):
    def __call__(self, cmd, **kw):
        if cmd[:3] == ["gh", "pr", "checks"]:
            self.base = "fix/old-parent"
        return super().__call__(cmd, **kw)
with tempfile.TemporaryDirectory() as root:
    cfg = t._cfg(Path(root), merge_requires="all")
    test = t.MergeRetargetsToTheTargetBase()
    host = ChangingHost("fix/old-parent")
    rc, err = test._run(cfg, host, test._bundle(cfg, "500"))
    print("rc:", rc, "final base:", host.base, "stderr:", repr(err))
    print("merge calls:", [c for c in host.calls if c[:3] == ["gh", "pr", "merge"]])
PYPROBE
```

Prior art was independently checked by **all seven affected file paths** through GitHub commit history (up to 15 commits per path, including all ten commits returned for `merge.py`) and by intersecting those paths with the file lists of **all ten closed, unmerged PRs** (no further page or truncated file list). Relevant closed work includes #637, #648, #639, and #679; no equivalent merge-time retarget implementation appeared. The captured responses and queried paths are in reviewer-prior-art.json. This confirms a path-based check beyond the brief’s claim; it does not settle the policy reversal.

For the hosted validation decision, in a maintainer-owned disposable repository use a draft PR with green CI against an old base and a head already containing the intended target. Run `gh pr edit "$PR_URL" --base "$TARGET"`, then `gh pr view "$PR_URL" --json baseRefName,headRefOid,statusCheckRollup` and `gh pr checks "$PR_URL" --json name,bucket`. Inspect the linked workflow runs’ tested merge/base provenance and whether fresh runs were created. Decide whether results from the old base suffice when the new base changes the contribution; no ready-mark or merge is necessary for that investigation.

<!-- pdca:leaf-complete -->
