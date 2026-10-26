# Result — issue 395 / same-wave-conflict-caught-before-publish

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: In stack mode, on every wave the fold runs after (not the last wave — the same `k < len(wave_list) - 1 and do_publish` condition as `flow.py:3078`), before that wave's accepted bundles are published, the driver finds which of them would be held at the fold for a textual conflict with a bundle of the same wave merged before it (the #674 rule, same order), and does not publish those. Each is held exactly as the fold holds it today — recorded as a `"conflict"` hold, named on stderr with the partner(s), the files, and the step (declare `Conflicts with`, rebuild on a base that holds the partner) — but no branch is pushed and no PR is opened for it. Its siblings publish as before. So a non-final wave no longer ends with two open PRs that conflict with each other. The last wave (and so a one-wave run) is unchanged by this change: nothing folds after it today, so nothing holds there today, and adding a hold there is a separate decision (follow-up, see Scope). This is a partial fix of #395: the PR says `refs #395`, not `closes`.
- Success criterion: On the real-git fixture with `gh` stubbed and the publisher in `command` mode: (a) A and B in one wave, no `Conflicts with` between them, patches that change the same lines of a shared file — after both are accepted, A's branch is pushed and its `gh pr create` is called; B's branch is NOT pushed to origin and no `gh pr create` is called for B; B is reported in the run's `holds` as `"conflict"` (not `"unpushed"`), and stderr names A and the shared file; a bundle of a later wave that depends on neither still builds; (b) A and B that touch the same file on different lines (no textual conflict) are both published and neither is held (no false hold); (c) a bundle whose conflict is only with work already on the line (not a same-wave sibling): its branch is pushed and `gh pr create` is called for it, and its outcome at the fold is the same as on `main` — held by #747 (`_held_by_line`, hold kind `"conflict"`) or the run stops, whichever `main` does for the same fixture; (d) the trial covers only bundles whose publish texts passed draft + T4 (`ready[d.name]` True): with A's texts failing T4, B is published and not held; (e) if the trial holds B for A and A's push then fails, B stays held (A is still accepted work and will be re-published; B would conflict with it), B's stderr line still names A, and A is reported as `"unpushed"`; (f) on the last wave of a run, the same A/B pair are both published and neither is held — no new hold and the same exit code as on `main`.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: Stack mode only, non-final waves only: a pre-publish trial of the wave's `ready` accepted work in fold order that decides the #674 same-wave conflict holds before anything is pushed; those bundles are not published and are held under the existing `"conflict"` hold; the fold keeps its own #674 check as the last line of defence; update the same-wave paragraph of `docs/07-crosscutting.md` (:719 onward). / out of scope: the last wave (follow-up issue, filed at publish); layer 1 of the issue (a Plan-exit advisory comparing briefs' predicted file sets — briefs have no structured file-list field to compare); re-sequencing a held bundle into a later wave of the same run automatically, and writing the discovered `Conflicts with` into the brief (issue layer 2's re-sequence half — follow-up issue; it would need an iterate and a rebuild on the line — see Open questions); conflicts with work already on the line (#747 handles those at the fold); merge mode; the advisory `_audit_wave_overlap` warning (flow.py:1586), which stays.

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

### Advisory — adversary

# Adversarial review — issue 395 (same-wave conflict caught before publish)

I re-ran the proof and three probe cases against the patched tree at `$PDCA_TARGET`. The
probe scripts are in `scratch/probes/` in this sandbox. The red→green evidence holds up.
The fix does what the brief asks for the plain case. I found two gaps where a stated
claim is false, and one case where the run gives a step nobody can follow.

## Findings

- NEEDS-HUMAN [human] — **"the wave never opens two PRs that conflict with each other" is false for a bundle that conflicts with a sibling AND with the line.** `docs/07-crosscutting.md:728` and the comment at `template/src/pdca_harness/flow.py:3134` both claim it. The trial only asks `_held_by` (`template/src/pdca_harness/integrate.py:864-867`). The fold also asks `_held_by_line`, and passes it the same-wave bundles it already merged (`integrate.py:663-668`). Probe (`scratch/probes/probe_mixed.py`): wave 0 is 10 (line 2 of `shared.txt`) and 12; wave 1 is 20 (line 8, depends on 12) and 21 (lines 2 and 8, depends on 12); 30 depends on 20, so a fold follows wave 1. Result: `fix/20` and `fix/21` are both pushed and both get `gh pr create`. Then the fold holds 21, saying it "conflicts with issue_20's, merged before it in the same wave 1, and issue_10's". `main` does the same, so nothing regressed. But the patch leaves exactly the two-conflicting-PRs case the docs say can't happen. The brief limits the trial to the #674 rule, so this is a scope call: either widen the trial to the fold's `_held_by_line` when its partners include a same-wave bundle, or narrow the docs and comment to the #674 case.

- NEEDS-HUMAN [human] — **When the trial can't run, it also holds siblings that can't conflict, plus everything that depends on them.** `template/src/pdca_harness/integrate.py:827` marks every member after the first as "untried", whatever files it touches. Probe (`scratch/probes/probe_395.py`): the test's own `_pair` fixture (10 and 11 change the same line, 12 has a file of its own, 20 depends only on 12), with the trial's two fetches failing. Result: holds are `{11: unpushed, 12: unpushed}`, `fix/12` is never pushed, 20 is never built, exit code 1. On `main`, with the fold's fetch working, 12 publishes and folds, 20 builds, and the exit code is 3. So the brief's "Its siblings publish as before" fails on this path. There is a cheaper fallback that still never lets two conflicting PRs out: hold only the bundles whose patch shares a file with an earlier ready bundle. A textual conflict needs a shared path, and `waves.diff_files` already gives the file list (`flow.py:1614`). This failure policy came out of the round-1 iterate, so the human should pick it.

- NEEDS-HUMAN [impl] — **A pre-publish hold record outlives its partner, and the re-issue then gives a step that can't be done.** `template/src/pdca_harness/flow.py:1515-1525` and `:1546` let `conflict-hold.json` override every other verdict ("whatever else below is wrong"). Probe (`scratch/probes/probe_stale.py`): after `_held_11_with_20_on_it`, issue_10's PR is closed without merging, then a re-issue drives 20. 11 is still told "rebuild issue_11 on a base that holds issue_10", which can't happen because 10 will never land. The message never mentions `pdca publish 11`, the step that would actually unblock 20. The hold no longer protects anything once no partner has an open or merged PR. Fix: when no partner named in the record is a clean finished id, fall back to the normal judgement (the "open" hint), or add the publish step to the advice.

## Checked, not a refutation

- The red leg's 24 errors in `template/tests/test_flow_reissue_after_conflict_hold.py` are `AttributeError`s from `mock.patch.object(flow, "_held_before_publish", ...)` (line 127) on the reverted tree (`gate-logs/C4-verify.log:38-659`). They show the symbol is missing, not that any behavior changed. The real red is the 7 assertion failures in the new file (fix/11 or fix/21 pushed before the fix, `C4-verify.log:713-804`) plus 3 in `test_flow_same_wave_conflict.py` (`:661-711`). That is enough for C4 to pass on merit.
- I tried to break these and could not:
  - **Production path.** The new tests use the real `publish.publish`, real git, a bare origin, and a `pre-receive` hook for the failed push. Only `_drive_wave`, `draft_texts` and `gh` are stubbed. I re-ran the green leg here: 20 tests OK.
  - **Same base as publish.** The `_checkout_base` refactor (`publish.py:804`) gives the same result as the old `wave_stacked and bool(wave_tip)` (`publish.py:251`), so the trial and publish cut each branch from the same commit.
  - **Same order and rule as the fold.** The trial merges in the fold's name order, starts from the same place (this run's folded tip, else `<base_remote>/<base>`), and uses the same `_held_by`.
  - **Exceptions.** `_LineBroken` and `IntegrationTreeError` both subclass `IntegrationError` (`integrate.py:103`, `:112`), so the retry catches them and nothing escapes as a traceback.
  - **Tests that pass before the fix.** Legs (d) and (f) pass on the reverted tree, but they would catch a trial with no `ready` filter, or one that also ran on the last wave.
  - **Locks.** Taken in sorted target order on one `ExitStack`, the same way the fold takes them.

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — issue_395 (same-wave conflict caught before publish)

Lens: bugs the patch adds, plus reuse and simplification. All refs are to the patched tree at `$PDCA_TARGET`.

Bottom line: I found no correctness bug that breaks a success-criterion leg. The trial copies the fold's order and its clash rule (`integrate._held_by`). It starts from the same line tip as the fold (`folded_tips`, which the pre-wave carry also fills at `flow.py:1582`). It cuts each would-be commit from the same base as publish, and the `_checkout_base` refactor matches the old inline logic exactly. Every git failure inside the trial is a subclass of `IntegrationError` (`integrate.py:103`, `:112`), so the retry-then-fail-closed path catches it and nothing escapes to crash the run. The two items from round 1 are fixed: the fail-closed path is tested (`template/tests/test_flow_same_wave_prepublish.py:1187`), and `create=True` is gone (`template/tests/test_flow_reissue_after_conflict_hold.py:121`).

## Findings

- NEEDS-HUMAN [human] — `template/src/pdca_harness/integrate.py:362-366` with `template/src/pdca_harness/flow.py:3152-3153`: when the trial can't run (lock not taken, or both tries fail at a git step), every ready bundle of that target except the first is held as `"unpushed"`. That happens whether or not they touch the same files. In a wave of N bundles on one repo, two fetch failures in a row leave N-1 accepted bundles unpublished, hold all their dependents, and make the run exit non-zero. This is a deliberate fail-closed choice made after round 1's finding, and it is documented (`docs/07-crosscutting.md:730-734`). Still, it is a large blast radius for a short-lived failure. The other option is fail-open (publish all, then let the fold's #674 check hold the loser), which round 1 rejected. Which trade-off to keep is a fitness call for the human.
- `template/src/pdca_harness/integrate.py:427-431`: `_would_be` is a third hand-written copy of publish's apply → add → commit steps (`template/src/pdca_harness/publish.py:298-308` and `:494-498`). Right now the flags match: plain `git apply`, then `add --all`. The trial commit skips hooks (`--no-verify`, and no `-s`). So if the target repo has a pre-commit hook that rewrites files, the trial tree can differ from the tree publish pushes. If publish's apply flags ever change (say to `--3way`), the trial drifts with no warning, and a would-be commit that silently fails to build simply drops out of the trial (`integrate.py:389-390`), so it holds nothing. The fold's own check still catches it, so this is a cleanup, not a bug. A small shared helper in `publish` returning the git steps would keep the two in step.
- `template/src/pdca_harness/publish.py:466`, `:474` and `template/src/pdca_harness/flow.py:1514`: the conflict-hold record is cleared only when publish pushes, and moved aside only when the bundle is rebuilt (`state.py:156`). Suppose a later run drives the same COMPLETE bundle again without a rebuild, and this time the trial doesn't hold it, but it still doesn't get pushed (texts fail T4, or the push fails). Then the old `conflict-hold.json` stays. A re-issue's carry will then say it "conflicts with … of its own wave" even if the partner has since merged. This is narrow and only affects the wording of the advice. Optional fix: clear the record when a later trial covers the bundle and doesn't hold it (around `flow.py:3146-3148`).
- `template/src/pdca_harness/flow.py:3133-3135` and `:3245`: each non-final wave now locks and fetches the integration checkout twice (once in the trial, once in the fold) and does several extra `_trial` merges per conflicting bundle. That is fine for normal wave sizes. I'm noting it only because this code runs on every stack-mode wave, not because it needs a change.

The tests cover every success-criterion leg (a)–(f), the retry, the fail-closed path, and both re-issue paths. Each test drives real publish against a bare origin, so the assertions on branches and PRs check real behaviour, not a stub.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] C5 Causal adequacy — Preserve conflict prevention when staging a trial commit fails — one injected git-add failure still pushed both conflicting branches and created both PRs because a failed candidate disappears from the trial; template/src/pdca_harness/integrate.py:890, template/src/pdca_harness/integrate.py:850, and review-trial-stage-failure.log:2.
- [ ] T5 Judgment — Approve withholding otherwise independent siblings when a target's trial remains unavailable — publishing only the first bundle protects against unknown conflicts but delays accepted work beyond the brief's normal sibling-publication behavior; docs/07-crosscutting.md:731 and template/src/pdca_harness/integrate.py:827.
- [ ] Validation — fitness-to-purpose — Accept this as a partial resolution of #395 with final-wave/one-wave conflicts still publishable, and require the C5 failure path to be corrected before relying on prevention; template/src/pdca_harness/flow.py:3142, template/tests/test_flow_same_wave_prepublish.py:354, and brief.md:19.
- [ ] **"the wave never opens two PRs that conflict with each other" is false for a bundle that conflicts with a sibling AND with the line.** `docs/07-crosscutting.md:728` and the comment at `template/src/pdca_harness/flow.py:3134` both claim it. The trial only asks `_held_by` (`template/src/pdca_harness/integrate.py:864-867`). The fold also asks `_held_by_line`, and passes it the same-wave bundles it already merged (`integrate.py:663-668`). Probe (`scratch/probes/probe_mixed.py`): wave 0 is 10 (line 2 of `shared.txt`) and 12; wave 1 is 20 (line 8, depends on 12) and 21 (lines 2 and 8, depends on 12); 30 depends on 20, so a fold follows wave 1. Result: `fix/20` and `fix/21` are both pushed and both get `gh pr create`. Then the fold holds 21, saying it "conflicts with issue_20's, merged before it in the same wave 1, and issue_10's". `main` does the same, so nothing regressed. But the patch leaves exactly the two-conflicting-PRs case the docs say can't happen. The brief limits the trial to the #674 rule, so this is a scope call: either widen the trial to the fold's `_held_by_line` when its partners include a same-wave bundle, or narrow the docs and comment to the #674 case.
- [ ] **When the trial can't run, it also holds siblings that can't conflict, plus everything that depends on them.** `template/src/pdca_harness/integrate.py:827` marks every member after the first as "untried", whatever files it touches. Probe (`scratch/probes/probe_395.py`): the test's own `_pair` fixture (10 and 11 change the same line, 12 has a file of its own, 20 depends only on 12), with the trial's two fetches failing. Result: holds are `{11: unpushed, 12: unpushed}`, `fix/12` is never pushed, 20 is never built, exit code 1. On `main`, with the fold's fetch working, 12 publishes and folds, 20 builds, and the exit code is 3. So the brief's "Its siblings publish as before" fails on this path. There is a cheaper fallback that still never lets two conflicting PRs out: hold only the bundles whose patch shares a file with an earlier ready bundle. A textual conflict needs a shared path, and `waves.diff_files` already gives the file list (`flow.py:1614`). This failure policy came out of the round-1 iterate, so the human should pick it.
- [ ] **A pre-publish hold record outlives its partner, and the re-issue then gives a step that can't be done.** `template/src/pdca_harness/flow.py:1515-1525` and `:1546` let `conflict-hold.json` override every other verdict ("whatever else below is wrong"). Probe (`scratch/probes/probe_stale.py`): after `_held_11_with_20_on_it`, issue_10's PR is closed without merging, then a re-issue drives 20. 11 is still told "rebuild issue_11 on a base that holds issue_10", which can't happen because 10 will never land. The message never mentions `pdca publish 11`, the step that would actually unblock 20. The hold no longer protects anything once no partner has an open or merged PR. Fix: when no partner named in the record is a clean finished id, fall back to the normal judgement (the "open" hint), or add the publish step to the advice.
- [ ] `template/src/pdca_harness/integrate.py:362-366` with `template/src/pdca_harness/flow.py:3152-3153`: when the trial can't run (lock not taken, or both tries fail at a git step), every ready bundle of that target except the first is held as `"unpushed"`. That happens whether or not they touch the same files. In a wave of N bundles on one repo, two fetch failures in a row leave N-1 accepted bundles unpublished, hold all their dependents, and make the run exit non-zero. This is a deliberate fail-closed choice made after round 1's finding, and it is documented (`docs/07-crosscutting.md:730-734`). Still, it is a large blast radius for a short-lived failure. The other option is fail-open (publish all, then let the fold's #674 check hold the loser), which round 1 rejected. Which trade-off to keep is a fitness call for the human.
- [ ] **The brief does not say whether the change covers the final wave, and the success criterion never tests it.** The fold that "the #674 rule, same order" copies only runs when `k < len(wave_list) - 1 and do_publish` (`flow.py:3078`). So on the last wave, including a single-wave run, nothing holds a same-wave conflict today: both PRs publish. The Goal says "before a wave's accepted bundles are published", which reads as every wave. If that is the intent, the change adds a new hold (and a new exit-3 case per `docs/07-crosscutting.md:734-741`) on a path with no fold to mirror, and possibly no integration line to trial onto. If it is not the intent, the motivation ("a wave no longer ends with two open PRs that conflict") stays false for the last wave. Criterion (a) always includes "a bundle of a later wave", so it cannot tell the two readings apart. The brief should pick one and add a criterion leg for a one-wave run or the last wave.
- [ ] **The trial set is undefined when a partner then fails to publish.** Design §1 runs the trial "after … drafted and T4-gated", over "the wave's accepted work". It does not say whether bundles with `ready[d.name]` False (`flow.py:3054-3058`) are in the trial. If they are, B can be held for clashing with an A that is never pushed (A becomes `held_unpushed` at `flow.py:3094-3100`). Then neither PR exists, and B is held for a partner that is not on the line. A push failure after the trial (`_publish_bundle` returns False, `flow.py:642-665`) has the same problem. The brief should limit the trial to `ready` bundles and say what happens to a conflict-held B when its partner A fails to push. Release B to publish, or keep the hold? Add a criterion leg for it.
- [ ] **The main design decision is left to Do.** Design §2 says: "How to build it is Do's call; it must match what publish will push, or the trial and the fold can disagree." Whether the trial gives the same answer as the fold is the whole feature, and `_held_by` judges merges of commits onto `pre` (`integrate.py:1803-1808`). So "match" needs a precise meaning: same parent commit (the line commit the bundle was built on, or its own base under `#738`'s `own_bases`, `flow.py:2994-3016`) and the same tree as the branch publish cuts (`docs/07-crosscutting.md:712-713`: "its PR branch is cut from the line commit it was built on"). The brief should set that rule. As written, criterion (b) (no false hold) is only as strong as an implementation choice nobody has made. Also say which worktree is used: the fold's shared integration tree (`integrate.py:609-613`) is reset by every user and guarded by the `#297` lock scope (`flow.py:3101`). A pre-publish trial there needs the same lock, and the brief does not mention it.
- [ ] **Criterion (c), "handled as today (this change does not move that case)", is not something a test can assert.** Today a branch that conflicts with the line is either held by `#747` (`_held_by_line`, `integrate.py:663-668`) or stops the run (`integrate.py:671-673`). The criterion should name the observable result: the bundle is pushed, `gh pr create` is called for it, and its hold kind or stop is the same as on `main`. Otherwise Check cannot prove the leg false.
- [ ] **The issue asked for re-sequencing, and the brief defers it without saying so.** The thread's layer 2 says: "On failure, re-sequence: move the bundle to a later wave / record the discovered conflict in the brief, rather than publishing it as a sibling". The owner's comment puts the payoff as later bundles getting built. The brief scopes out both re-sequencing and writing the discovered `Conflicts with` into the brief. That is a reasonable cut, but it means this change does not close #395. Mark the brief as a partial fix (e.g. "refs #395", with a follow-up issue for re-sequence and the Plan-exit advisory) so publish does not auto-close the issue.
- [ ] **The `Conflicts with: 464` declaration cannot be checked from this bundle.** There is no `dependency-state.json` and no `sources/` directory in the inputs, so I cannot confirm that a 464 bundle exists in this batch or what state it is in. The ordering note (464 "gates this same publish/fold block") is a real file overlap, so if 464 is in the same batch, the declaration is right. Confirm the id resolves before sign-off.
- [ ] **Criterion (e) holds strictly more work than `main` when the partner's publish fails for a reason the trial cannot see.** The trial runs after T4 but before checks that live inside publish: the host-CI gate (publish.py:379-383), the line-tip refusal (publish.py:364-367), and commit hooks (publish.py:309; the trial commits with `--no-verify`, integrate.py:846). Example: A's host CI is red. A pushes nothing, B is held for A with no PR, and B's dependents and `Conflicts with` partners are held too. On `main`, B would have been published and folded cleanly, because the unpushed A is left out of the fold (flow.py:3169), and its dependents would have been built. The brief asks for this behaviour on purpose (criterion e: "A is still accepted work and will be re-published"), so it is a scope call for sign-off, not a bug.

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
- Iteration delta (if iterating): Auto-iterate (round 2): rebuilding for the implementation-level findings — C5 Causal adequacy — Preserve conflict prevention when staging a trial commit fails — one injected git-add failure still pushed both conflicting branches and created both PRs because a failed candidate disappears from the trial; template/src/pdca_harness/integrate.py:890, template/src/pdca_harness/integrate.py:850, and review-trial-stage-failure.log:2.; **A pre-publish hold record outlives its partner, and the re-issue then gives a step that can't be done.** `template/src/pdca_harness/flow.py:1515-1525` and `:1546` let `conflict-hold.json` override every other verdict ("whatever else below is wrong"). Probe (`scratch/probes/probe_stale.py`): after `_held_11_with_20_on_it`, issue_10's PR is closed without merging, then a re-issue drives 20. 11 is still told "rebuild issue_11 on a base that holds issue_10", which can't happen because 10 will never land. The message never mentions `pdca publish 11`, the step that would actually unblock 20. The hold no longer protects anything once no partner has an open or merged PR. Fix: when no partner named in the record is a clean finished id, fall back to the normal judgement (the "open" hint), or add the publish step to the advice.. Deferred, not addressed here: 10 finding(s) that need human judgment, held in deferred-findings.json for the human at handover — not build work
- By / date: auto-iterate / 2026-10-23

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 6 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
