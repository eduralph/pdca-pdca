# Result — issue 500 / merge-mode-retarget-wrong-based-pr

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: Under `[driver].wave_mode = "merge"`, before the driver readies and merges a wave's PR, it checks the PR's base on the host against the bundle's resolved target base, and checks that the target base is not itself a branch another bundle of this batch produced (#411 route 2). A batch-produced target refuses with no `gh pr edit` call. When the host base differs from a good target, it retargets the PR (`gh pr edit <pr> --base <target>`), reads the base again, and goes on only if the host now reports the target base. If the retarget fails or does not take, it refuses with a message that names both branches, and the run stops as merge mode does for any refusal.
- Success criterion: With `wave_mode = "merge"` and a COMPLETE bundle whose PR the host reports with `baseRefName` ≠ the bundle's resolved target base: (a) when `gh pr edit --base` succeeds and the next read reports the target base, the PR is merged with the normal gates and no `gh pr merge` call is made before the retarget; (b) when `gh pr edit --base` fails, or the re-read still reports the wrong base, `merge.merge_wave` returns non-zero, no `gh pr merge` is called for that PR, the PR is not left marked ready (no `gh pr ready` without a matching `--undo`), and stderr names both the PR's base and the target base; (c) both hold under `merge_requires = "all"` AND `merge_requires = "required"` (the second path skips the base read today: the read sits inside `if cfg.merge_requires != "required":`, merge.py:536-618); (d) a PR whose base already equals the target makes no `gh pr edit` call; (e) when the bundle's resolved target base is a branch a sibling bundle of the batch published (#411 route 2, `publish._batch_branch_producer`), `_merge_one` refuses whether or not the host base equals it — no `gh pr edit`, no `gh pr ready`, no `gh pr merge` call, stderr names the producing bundle; (f) the check runs after the `expected_checks_error` refusal (merge.py:507-511): with a malformed `expected_checks` and a wrong-based PR, no `gh pr edit` is called. In (b) and (e) **no `gh pr ready` call is made at all** for that PR (the check runs before the ready-mark), and no `gh pr ready --undo` either: the refusal leaves the PR's draft/ready state as it found it.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: A merge-time check of the PR's host-side base against the bundle's resolved target base in `merge._merge_one`, with a retarget attempt before refusing; covers both `merge_requires` values; updates the merge-mode bullet of `docs/07-crosscutting.md` (:858 onward) AND the #411 paragraph at :888-897, whose "the harness never retargets a PR for you" becomes false; updates the #411 comment at publish.py:288-290 ("Refuse here rather than at merge time") so it no longer says no merge-time check exists. / out of scope: the publish-time #411 guard (`publish._merge_base_refusal`, publish.py:770) — unchanged, it stays the first line of defence; stack mode; retargeting a `"stacked"` (`Onto branch`) record — merge mode already refuses those first (merge.py:483-494, #658), keep that order; resolving the target any way other than the one parser publish uses.

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: new-feature
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: pass — C4 PASS — red without the fix, green with it
- C5 added test exercises production, not a copy: pass — 1 added driver-suite test(s) import the production package 'pdca_harness'

## 4. Conformance (Check — stack)
- T1 Structure: none — (no gate configured)
- T2 shape: docs lint + site render link audit: pass — docs lint clean, site render + link audit clean
- T2 host CI parity: target docs-check.yml on the pushed tree: pass — host CI parity on the patched tree — docs lint clean, site render + link audit clean
- T3 runtime: render/update-compat + offline driver suites: pass — root suite OK, driver suite OK
- T4 PR body has a user-impact opener + tracker id in both artifacts: deferred — pr-description.md not drafted yet — the substantive T4 audit of the contribution artifacts runs at publish
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

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

### Advisory — code-review

# Advisory code review — issue 500 (merge-mode retarget of a wrong-based PR)

Lenses: bugs the patch introduces, and reuse / simplification / efficiency. Advisory only.

No correctness bug found in the main path. The new check sits where the brief asks: after the
`"stacked"` refusal, the `is_merged` skip and the `expected_checks_error` refusal, and before
`gh pr ready` (`template/src/pdca_harness/merge.py:567`). Its refusal is a plain STOP plus
`return 1`, not `_refuse`, so no spurious `gh pr ready --undo` is sent. It runs under both
`merge_requires` values. Route 2 (`publish._batch_branch_producer`) is checked before any host
call (`merge.py:489`). The target comes from `publish._resolve_target(d)[:2]` (`merge.py:480`),
as the brief requires. The C4 log shows the new tests failing on assertions before the fix and
passing after it, and T3 (2635 tests) passes. The findings below are small.

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/merge.py:483-486` copies, word for word, the
  `fix` hint string from `publish._merge_base_refusal` (`template/src/pdca_harness/publish.py:792-795`),
  leaving off only the final period. Two copies of the same user-facing text will drift apart.
  Move it to one module-level constant in `publish` and use it from both places.
- NEEDS-HUMAN [impl] — `template/src/pdca_harness/merge.py:500-503` and `:504-509`: when
  `gh pr edit --base` fails (for example, no permission to edit the PR, or a network error) or
  the host ignores it, the refusal still adds the `fix` hint "Point the brief's `Repo + branch
  target` at the shared base, or use … stack". That hint fits the route-2 case. In these two
  cases the brief is usually correct and the PR is what needs fixing, so the hint sends the
  operator the wrong way. Say instead to retarget the PR on the host (or check `gh` rights),
  then re-run.
- `template/src/pdca_harness/merge.py:475-482`: a COMPLETE bundle with no `brief.md`, or no
  usable target, now refuses at merge time where it used to merge. This is the correct
  fail-closed choice, and it is why five test fixtures needed a `brief.md` added. But it is a
  new hard requirement on every merge-mode bundle, and the merge-mode docs bullet
  (`docs/07-crosscutting.md:887`) doesn't mention it. Low risk, because real bundles always
  carry a brief. Noted only, no action needed.
- `template/src/pdca_harness/merge.py:491`: under `merge_requires = "all"` the PR is now read
  with `gh pr view` once here and again inside `_base_read` (`merge.py:378`), with no step in
  between that could change it (unless a retarget happened). The brief allows reusing that
  read ("Do may reuse it"). The cost is one extra API call per PR, which is fine at wave
  scale. Optional cleanup, not a defect.
- `template/src/pdca_harness/merge.py:480`/`:489`: route 2 is looked up using the brief's
  `repo_spec`, while the PR's repo comes from the publish record (`merge.py:525`). The patch
  doesn't check that the two match. Publish writes the record from the same brief, so they
  should agree, and this would only matter if someone edited one by hand. Noted, no action
  needed.
- Tests: `template/tests/test_merge_retarget.py` covers legs (a) through (f). It covers both
  `merge_requires` values for (a), (b), (d) and (e). It asserts that no `gh pr ready` or
  `gh pr merge` call is made on refusal, and that the base is read again between the edit and
  the ready-mark. Leg (f) is tested only under the default `"all"` setting. That is enough,
  since the `expected_checks_error` refusal comes before the `merge_requires` branch. One gap:
  no test covers a bundle whose PR is retargeted and then refused later (for example, a red
  rollup). The PR then keeps its new base while its ready-mark is undone. That is the correct
  outcome, but a test would pin it down. Optional.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] C5 Causal adequacy — Close the observed base-change gap before relying on the target invariant — after successful retargeting, a base change during check reads is observed by the final read yet still merges into the wrong branch; template/src/pdca_harness/merge.py:567, template/src/pdca_harness/merge.py:668; reproduced in reviewer-base-race.log:2.
- [ ] T5 Judgment — Approve unattended retargeting as a reversal of the previous promise, or choose the brief’s refuse-only fallback — changing a base can enlarge the PR’s contribution; docs/07-crosscutting.md:887 and docs/07-crosscutting.md:905, publish policy at template/src/pdca_harness/publish.py:288.
- [ ] Validation — fitness-to-purpose — Decide whether merging after retarget without fresh CI for the new base is acceptable — live GitHub retarget/check provenance was not exercised, so evidence rests on a stub that always reports green; template/tests/test_merge_retarget.py:83, template/src/pdca_harness/merge.py:642; the brief’s “External dependencies: none” does not discharge that hosted behavior.
- [ ] `template/src/pdca_harness/merge.py:483-486` copies, word for word, the `fix` hint string from `publish._merge_base_refusal` (`template/src/pdca_harness/publish.py:792-795`), leaving off only the final period. Two copies of the same user-facing text will drift apart. Move it to one module-level constant in `publish` and use it from both places.
- [ ] `template/src/pdca_harness/merge.py:500-503` and `:504-509`: when `gh pr edit --base` fails (for example, no permission to edit the PR, or a network error) or the host ignores it, the refusal still adds the `fix` hint "Point the brief's `Repo + branch target` at the shared base, or use … stack". That hint fits the route-2 case. In these two cases the brief is usually correct and the PR is what needs fixing, so the hint sends the operator the wrong way. Say instead to retarget the PR on the host (or check `gh` rights), then re-run.
- [ ] **The check would retarget a PR onto a batch-produced branch, which is the exact hazard #411 blocks.** #411 has two refusal routes. The brief carries over only route 1 (`pr_base != base`). Route 2 refuses when the brief's resolved target base is itself a branch another bundle in the batch produced (publish.py:781-785, 798-802, via `_batch_branch_producer`). The issue says its trigger is "switching an existing batch from stack mode to merge mode", and chained `Repo + branch target`s are "the documented stack-mode practice" (publish.py:782-783). In that case the brief's design would either merge a PR into a predecessor's fix branch with no stop (host base == target, step 2 "continue exactly as today"), or actively `gh pr edit --base` a correctly-based PR *onto* that branch. The invariant as worded ("merges … only into that bundle's resolved target base") does not rule this out. Revise the invariant, scope and criterion so the merge-time check applies route 2 (`_batch_branch_producer`, or reuse `_merge_base_refusal` whole) before any retarget. Add a criterion leg: a target that is a sibling bundle's published branch refuses, with no `gh pr edit` call.
- [ ] **The brief reverses a recorded design decision and a documented user contract without saying so.** The #411 comment that the brief cites (publish.py:283-292) goes on to say: "Refuse here rather than at merge time: the publisher is an interactive step with a human present" (publish.py:288-290). The brief quotes lines 286-287 and leaves this part out. The user docs also promise: "the harness never retargets a PR for you" (docs/07-crosscutting.md:897). That paragraph is at :888-897, not in the :858 bullet the Scope names. As written, Do updates the :858 bullet and leaves :897 contradicting the new behavior. The Scope should name docs :888-897, and Motivation should state that the merge-time-check / auto-retarget decision is being reversed. That reversal is a maintainer call, not something Do should settle by default.
- [ ] **This is two changes (a missing safety guard plus an enhancement), and the issue's premise is wrong.** The issue assumes a merge-time check already exists: "When the merge-mode base check finds `baseRefName != resolved target base`" and "stop with the existing message … The refusal path stays exactly as #411 shipped it". Triage graded it `sev:minor` because "Current fail-closed behaviour is safe" (notes.json comment). The brief itself finds there is no merge-time stop at all, so a wrong-based PR merges silently (Motivation, "this also closes a silent wrong-merge"). So the bundle adds (1) a fail-closed refusal that does not exist today, which is a bug fix on the invariant, and (2) the retarget the issue asked for. Each has its own review surface and risk. The human should decide whether to split them (refuse-only floor first, retarget stacked on it) and whether to re-grade sev/priority. The triage's basis for P3 is false according to the brief's own reading.
- [ ] **The Open-questions answer depends on a claim the code does not back.** "under `"all"` the rollup gate re-verifies the new combination" is only partly true. After a retarget, `_base_read` asks whether the head contains the *new* base's tip (merge.py:384, 393). Only a behind head gets `gh pr update-branch` and so a new head SHA with new CI (merge.py:556-572). If the head already contains the target tip (the usual stack→merge case: old base was a predecessor branch on top of main), no update happens. `_wait_for_green` then reads the existing rollup for that head SHA, earned against the *old* base, and a base edit by itself does not normally re-run CI. Either add a criterion leg for that case (e.g. require a fresh rollup after a retarget, or refuse when the old base held commits the target lacks), or state in the brief that the residual risk is accepted.
- [ ] **The brief contradicts itself on where the refusal happens.** Design step 1/3 puts the check *before* `gh pr ready` ("the PR is still a draft, so there is nothing to undo"). Citations expected says "refuse through `merge._refuse` … when the PR is already readied, so the ready-mark is undone". `_refuse` always calls `_undo_ready` (merge.py:453-460), so using it pre-ready sends a spurious `gh pr ready --undo`. Criterion (b)'s "no `gh pr ready` without a matching `--undo`" is satisfied whether or not `ready` is ever called, so it does not pin which design Do built. Pick one placement and make (b) assert it, e.g. "no `gh pr ready` call at all for that PR". "Still a draft" is also not guaranteed for a PR from an earlier run or one a human readied, which is another reason to pin this down.
- [ ] **The placement relative to the existing pre-ready refusal is unspecified.** Design step 1 says "after the `"stacked"` refusal and the `is_merged` skip". It does not say whether the check goes before or after the `expected_checks_error` refusal (merge.py:507-511). If it goes before that refusal, a malformed config still lets the driver edit a PR's base on the host before stopping, which is a host-side mutation on a run that was going to refuse anyway. State the order: after merge.py:511.

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: iterated-to-Do
- Iteration delta (if iterating): Auto-iterate (round 1): rebuilding for the implementation-level findings — C5 Causal adequacy — Close the observed base-change gap before relying on the target invariant — after successful retargeting, a base change during check reads is observed by the final read yet still merges into the wrong branch; template/src/pdca_harness/merge.py:567, template/src/pdca_harness/merge.py:668; reproduced in reviewer-base-race.log:2.; `template/src/pdca_harness/merge.py:483-486` copies, word for word, the `fix` hint string from `publish._merge_base_refusal` (`template/src/pdca_harness/publish.py:792-795`), leaving off only the final period. Two copies of the same user-facing text will drift apart. Move it to one module-level constant in `publish` and use it from both places.; `template/src/pdca_harness/merge.py:500-503` and `:504-509`: when `gh pr edit --base` fails (for example, no permission to edit the PR, or a network error) or the host ignores it, the refusal still adds the `fix` hint "Point the brief's `Repo + branch target` at the shared base, or use … stack". That hint fits the route-2 case. In these two cases the brief is usually correct and the PR is what needs fixing, so the hint sends the operator the wrong way. Say instead to retarget the PR on the host (or check `gh` rights), then re-run.. Deferred, not addressed here: 7 finding(s) that need human judgment, held in deferred-findings.json for the human at handover — not build work
- By / date: auto-iterate / 2026-10-23

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 6 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
