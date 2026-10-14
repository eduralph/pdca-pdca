# Result — issue 658 / merge-mode-never-merges-an-onto-branch-pr

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: Under `[driver].wave_mode = "merge"`, merge mode readies and merges a pull request the run did not open. A bundle whose brief has an `Onto branch` field is published by `publish._publish_stacked`, which adds one commit to an EXISTING open PR (possibly someone else's, with any base) and records that PR in `publish.json` with `"mode": "stacked"` (`template/src/pdca_harness/publish.py:549`). `publish.publish` dispatches to `_publish_stacked` at `publish.py:225-228`, before the merge-mode base guard from #411 (`_merge_base_refusal`, called at `publish.py:294`, defined at `:761`), so that guard never sees it. Then, for a non-final wave, `flow` calls `merge.merge_wave` (`template/src/pdca_harness/flow.py:2317-2318`), and `merge._merge_one` (`template/src/pdca_harness/merge.py:453`) reads `pr_url` from the record (`merge.py:463`), runs `gh pr ready` on it (`merge.py:493-494`), and then `gh pr merge` into whatever base that PR has. `merge.py` never looks at the record's `mode`. An unattended run can therefore merge a pre-existing PR, with everything else on it, without anyone approving that. The rest of the harness already refuses to trust such a record: the fold treats an `Onto branch` record as possibly merged into another base (`template/src/pdca_harness/integrate.py:555-556`, `_gone_branch`), and `merged.merged_into` never counts one as merged (`template/src/pdca_harness/merged.py:104-110`).
- Success criterion: With the patch, merge mode never readies or merges the PR behind a `"stacked"` publish record, and says why. Concretely, driving `merge.merge_wave(cfg, [b], dry_run=False, method="merge")` (the call `flow.py:2318` makes for a non-final merge-mode wave) on a bundle `b` that is COMPLETE, has a non-empty `patch.diff`, and has `publish.json` = `{"mode": "stacked", "branch": "feat", "base": "other/feat", "pr_url": "<url>", "repo": "org/repo"}`, with `subprocess.run` in `merge` recorded by a stub:
  (1) no `gh pr ready <url>`, no `gh pr ready <url> --undo`, no `gh pr update-branch`, and no `gh pr merge` call is made, and `merge_wave` returns non-zero (the wave stops, so `flow` prints its existing "wave k did not merge; STOPPING" line);
  (2) stderr names the bundle (`issue_<id>`), the PR URL, and says the bundle is an `Onto branch` commit on an existing PR that merge mode does not ready or merge, and what the operator can do instead: run the batch in the default `wave_mode = "stack"`, or take the bundle out of this merge-mode batch. The message must NOT suggest merging that PR by hand as a way to unblock the run: by criterion (3) a hand-merged `"stacked"` PR is still refused, so a re-run would stop the same way. (It may say the PR itself is the human's to ready or merge, as long as it says that does not let this merge-mode run continue.);
  (3) the same holds when the PR already reads `MERGED` (`merged.is_merged` patched to return `True`): the record is still refused, not skipped as "already merged" (consistent with `merged.merged_into`, `merged.py:104-110`);
  (4) with `dry_run=True` the plan prints no `gh pr merge … <url>` line for that bundle and `merge_wave` returns non-zero. Why this matters, stated accurately: a dry-run publish of an `Onto branch` bundle writes no `publish.json` (`_publish_stacked`'s dry-run branch, `publish.py:496-509`, returns before the write at `:556`; the stub publisher records none either, `integrate.py:340`), so a fresh offline rehearse of an `Onto branch` bundle already stops at the "no recorded PR" check (`merge.py:465-468`). This branch is reached by a dry run over a `"stacked"` record left on disk by an earlier real publish; such a dry run must not print a merge plan for it;
  (5) a bundle whose record is `"new-pr"` (or has no `mode`) is merged exactly as today: the existing `template/tests/test_merge.py` cases and the `new-pr` cases of `template/tests/test_merge_third_remote.py` pass unchanged.
  Pre-fix, (1) fails (`gh pr ready <url>` is called), and (3) returns 0 without a refusal. That is the RED.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: Make merge mode refuse a bundle whose publish record is `"stacked"` before it calls `gh` for that PR at all (no ready, no update, no merge, no undo), stopping the wave with a message per criterion (2), in both real and dry runs. Placement: the refusal goes in `_merge_one` right after the `pr_url` check (`merge.py:465-468`), ABOVE the `dry_run` early return (`merge.py:471-473`) and the `merged.is_merged` short-circuit (`merge.py:475-476`); placed later (e.g. beside the peer refusal at `:477-485`), it fails criteria (3) and (4). Update the comments in `merge.py` that would otherwise describe a path `_merge_one` no longer takes for `"stacked"` records: the module docstring paragraph at `merge.py:76-83`, `_remotes`' docstring at `merge.py:299-306`, and the inline #650 comment at `merge.py:521-523`. Each should say that `_merge_one` refuses a `"stacked"` record before it reads the head, and that the record-named remote is kept for a caller passing such a `pub` directly (it is not reached from `_merge_one`). Update the existing tests that assume the opposite: in `template/tests/test_merge_third_remote.py` the `STACKED` cases are split by what they test, so the code this brief keeps stays tested. (a) Cases whose point is that a `"stacked"` record reaches the ready-mark, the rollup wait or the merge (`:156`, `:165`, `:189`, and `:281`, which pins "not refused up front") are changed to assert the refusal, or removed where one refusal case already covers them. (b) Cases whose point is the fetch / missing-head logic of `_remotes`, `_fetch`, `_have` and `_base_read` with a third remote or a record naming no remote (`:203`, `:216`, `:249`, `:266`) are kept, but call `merge._base_read(cfg, repo, pub, url)` (or `_have` / `_remotes`) directly with the `pub` tuple `integrate._published_ref` would give for the `STACKED` record, instead of going through `merge_wave`. Their assertions on the refusal text stay. The module docstring is updated to say this. The `new-pr` cases (`:235`, `:292`) stay as they are, as do any cases in `template/tests/test_merge.py`. / out of scope: a publish-time or schedule-time refusal of `Onto branch` + `wave_mode = "merge"` (the issue's other option; a possible follow-up, not needed for the invariant); removing #650's third-remote fetch code or `_have`; any change to stack mode, the fold, `merged.py`, or `publish._publish_stacked`; the `"stacked-pr"` mode (a PR this run opened).

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
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

Review issue #658: prevent merge mode from readying or merging an existing PR identified by an `Onto branch` (`"stacked"`) publish record, including resumed and dry runs.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief defines observable refusal, recovery guidance, already-merged and dry-run behavior, and compatibility; the intentional reversal of #650 is recorded as approved (brief.md:3; target/template/src/pdca_harness/merge.py:486). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only the production change produces 8 assertion failures across 73 tests, including unwanted PR actions and successful returns for forbidden records; no import failure substitutes for reproduction (reviewer-red.log:3; reviewer-red.log:114; target/template/tests/test_merge_onto_branch.py:114). |
| C3 Change | PASS | The change stays within the approved merge refusal and associated tests/comments; refusal precedes both bypasses and identifies the bundle, PR, and viable recovery options (target/template/src/pdca_harness/merge.py:486; target/template/src/pdca_harness/merge.py:497). |
| C4 Verification (red→green) | PASS | After restoring the production change, the same 73 tests pass, covering real/dry/already-merged refusal, wave stopping, and existing merge behavior; frozen C4 evidence agrees (reviewer-green.log:3; gate-logs/C4-verify.log:10; target/template/tests/test_merge_onto_branch.py:124). |
| C5 Causal adequacy | PASS | The defect is unauthorized treatment of an existing PR as the run's own; refusal at the shared merge entry removes that action path, including records already on disk, without a capability probe or load-time workaround (target/template/src/pdca_harness/publish.py:548; target/template/src/pdca_harness/merge.py:486; target/template/tests/test_merge_onto_branch.py:90). |
| T1 Structure | PASS | The existing per-bundle return contract propagates refusal to stop the wave, and retained third-remote helpers remain tested directly with real Git; no new dependency or parallel implementation is introduced (target/template/src/pdca_harness/merge.py:119; target/template/tests/test_merge_third_remote.py:159). |
| T2 Shape | PASS | Independent whitespace check, docs lint, and 22-page render/link audit pass; frozen host-parity evidence shows the same docs checks passing (reviewer-lint.log:1; reviewer-render.log:2; gate-logs/host-ci-docs.log:10). |
| T3 Runtime | PASS | Independent driver suite passes 2,427 tests with 2 skips; root render/update coverage is supported by the frozen log's 24 passing tests, while the local root attempt exits 77 because Copier is not importable (reviewer-suite.log; gate-logs/T3-suite.log:38; gate-logs/T3-suite.log:54; reviewer-root.log:6). |
| T4 Contribution | N/A | Contribution artifacts are intentionally absent at Check; the deferred gate explicitly owes the substantive PR-body/tracker audit to publish (gate-logs/T4-contribution.log:10). |
| T5 Judgment | NEEDS-HUMAN | Confirm prior-art coverage by all three affected file paths, including merged and closed/rejected test changes — the brief records merge.py/publish.py history, but this one-commit snapshot has no remote or historical PR evidence to settle the remaining coverage (brief.md:35; target/template/tests/test_merge_third_remote.py:179; target/template/tests/test_merge_onto_branch.py:1). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Accept the operational outcome that an Onto-branch member stops a merge-mode batch even after its PR is manually merged, requiring stack mode or removal from the batch — the executable checks establish behavior, while its suitability remains the sign-off decision (target/template/src/pdca_harness/merge.py:487; target/template/tests/test_merge_onto_branch.py:124). |

All source citations above refer to the supplied `$PDCA_TARGET` copy under `target/`; evidence citations refer to this review's inputs or captured reruns. Its synthetic base identifies `41210bcd18e0b6d1b77fd5fe6e29c2bbebb6fa57`, matching the brief. After the stash/pop experiment, `git apply --reverse --check ../patch.diff` succeeds and the original three-file change remains present. No stale-target caveat or implementation defect was found.

Independent reproduction used `PYTHONPATH=src python3 -m unittest tests.test_merge_onto_branch tests.test_merge_third_remote tests.test_merge` from `target/template`, first with only `template/src/pdca_harness/merge.py` stashed, then after restoration. Output is retained in `reviewer-red.log` and `reviewer-green.log`. The full driver rerun used `PYTHONPATH=src python3 -m unittest discover -s tests`; output is in `reviewer-suite.log`. Temporary test paths were confined to this sandbox through `TMPDIR`.

The production-import scanner was rerun successfully (`reviewer-prod.log:1`). Docs lint and site rendering with `--check` were also rerun successfully. The instance-scoped wrappers themselves are outside this bundle; their frozen logs were read. The local root-suite limitation is a reviewer-host caveat, not a patch failure: the frozen T3 log explicitly shows real Copier render/update cases executing successfully. No unmet dependency is inferred from the intentional `gh` test double: the claimed invariant concerns whether the subprocess is invoked at all, and the pre-fix run demonstrably exhibits the forbidden invocation. No live PR was readied or merged.

The path-history investigation returned only synthetic base commit `3846822` for the affected paths; `git remote -v` returned no remotes. The brief documents the #650 policy reversal and closed-unmerged PR dispositions, but independent historical confirmation is unavailable in these artifacts. The supplied integration template lists project-defined human-only items as TODO rather than enumerating additional decisions (target/template/docs/INTEGRATION.md.jinja:80).

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — issue 658 (merge mode never merges an `Onto branch` PR)

**Verdict: no correctness bugs found in this diff.** The findings below are small test cleanups. None needs a human.

## Correctness

- `template/src/pdca_harness/merge.py:486-494`: the refusal is placed right. It comes after the `pr_url` check (`:475-478`), so `rec` is never `None` when `rec.get("mode")` runs. It also comes before the dry-run return, the `is_merged` skip and every `gh` call. It returns `1` without calling `_undo_ready`, which is correct because nothing has been readied yet. `merge_wave` (`merge.py:124-127`) stops at the first non-zero result, so later bundles are not touched. The mode test (`== "stacked"`) matches the one in `merged.merged_into`, so `"stacked-pr"` and records with no mode still merge (`test_merge_onto_branch.py` case (5)). The message is written inline instead of going through `_refuse` (`merge.py:453`). That is the right call: `_refuse` would tell the operator to "resolve at the PR", which loops under criterion (3), and it also calls `_undo_ready`, which is not needed here.
- Gate evidence matches. C4 (the gate that checks the new tests fail without the fix and pass with it) shows them red without the fix: the stacked record goes to `gh pr ready`, `view`, `ready --undo`. They are green with the fix. T3 (the full test suite) is OK: 2427 tests, 2 skipped.

## Reuse / simplification (optional)

- `template/tests/test_merge_onto_branch.py:94-100`: in `_assert_no_pr_action`, the check on line 99 (no `gh pr …` call at all) already covers the specific `ready` / `ready --undo` / `update-branch` / `merge` checks above it. The specific checks could go, or stay as documentation. Cosmetic.
- `template/tests/test_merge_onto_branch.py:141-157`: `test_wave_stops_at_the_stacked_member` copies the stub setup from `_wave` (same `run` recorder, same three patches). If `_wave` took a list of bundles, this case could reuse it. Cosmetic.
- `template/tests/test_merge_onto_branch.py:120`: `self.assertEqual(b.name, "issue_658")` tests the fixture's naming, not the fix. It is harmless but could be removed.
- `template/tests/test_merge_third_remote.py:183`: the `for verdict in (failing, green)` loop has no effect. The refusal happens before `_wait_for_green` is reached, so both subtests run the same path. One case is enough. Keeping both is harmless.
- Coverage note, not a defect: the old `test_stacked_head_behind_is_updated_on_third_remote_and_reaches_wait` was removed and not turned into a direct `_base_read` case. That means `_base_read` returning `behind=True` for a third-remote head is no longer tested. This matches the brief's Scope (a), since that case was about `update-branch` and reaching the rollup wait, which is code inside `_merge_one`. The kept direct-read cases cover the fetch and the missing-head logic.

No NEEDS-HUMAN items.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — Confirm prior-art coverage by all three affected file paths, including merged and closed/rejected test changes — the brief records merge.py/publish.py history, but this one-commit snapshot has no remote or historical PR evidence to settle the remaining coverage (brief.md:35; target/template/tests/test_merge_third_remote.py:179; target/template/tests/test_merge_onto_branch.py:1).
- [x] Validation — fitness-to-purpose — Accept the operational outcome that an Onto-branch member stops a merge-mode batch even after its PR is manually merged, requiring stack mode or removal from the batch — the executable checks establish behavior, while its suitability remains the sign-off decision (target/template/src/pdca_harness/merge.py:487; target/template/tests/test_merge_onto_branch.py:124).
- [x] **Criteria (2) and (3) contradict each other: the suggested remedy leaves the run stuck.** Criterion (2) has stderr tell the operator to "merge that PR by hand". Criterion (3) then requires the record to be refused even when `merged.is_merged` returns `True`, so a re-run after the operator follows that advice STOPs again in exactly the same way. Only `wave_mode = "stack"` (or dropping or iterating the bundle) actually lets the run continue. Either take "merge that PR by hand" out of the required message, or have it say clearly that merging by hand will not unblock this merge-mode run. Otherwise Check will be grading a message that sends operators into a loop.
- [x] **Criterion (4) rests on a premise the source contradicts.** The brief says dry-run must return non-zero "so an offline rehearse shows the same stop a real run would hit". But the stub publisher writes no `publish.json` at all: `_publish_stacked` returns at `publish.py:496-509` before the write at `:556`, and `integrate.py:340` says "no `publish.json` (the stub records none)". So in a real rehearse an `Onto branch` bundle has no `"stacked"` record, and `_merge_one` already returns 1 at `merge.py:465-468` ("no recorded PR"). The new dry-run branch is only reachable with a stale record left over from an earlier real run. The unit test can still be checked, but the stated reason is false. Also, the refusal has to sit above the `dry_run` early return at `merge.py:471-473` and the `is_merged` short-circuit at `:475-476`. The brief's peer callsite (`:477-485`) comes after both, so copying its position would fail (3) and (4). The brief should say where the refusal goes: right after the `pr_url` check at `:465-468`.
- [x] **The brief leaves the #650 documentation unaddressed, and it becomes false.** The fix edits `merge.py`, but the module docstring (`merge.py:76-83`: "an `Onto branch` bundle's `"stacked"` record names the remote it pushed to … So the fetch covers that remote too") and the inline comment at `merge.py:521-523` will describe a path `_merge_one` can no longer reach for `"stacked"` records. Scope rules out removing the code, but says nothing about these comments. Do will either leave false documentation in a file it touched or make an unlisted drive-by edit. State which. The same goes for `_remotes`' docstring (`merge.py:299-306`), which still promises an "`Onto branch` record's remote, possibly a third one".
- [x] **Rewriting `test_merge_third_remote.py` drops coverage of code the brief keeps.** `merge.py:321-343` (`_have`) and the third-remote branch of `_remotes` (`merge.py:307`) are kept on purpose, yet nearly every case that exercises them uses the `STACKED` record: `test_merge_third_remote.py:156,165,189,203,216,249,266,281`. `test_stacked_record_naming_no_remote_is_not_refused_up_front` (`:281`) even pins the opposite design. If Scope turns all of these into refusal assertions, the head-named-by-record refusal that `_have` builds (`:342-343`) is no longer tested by anything, and that code stays shipped. Decide whether those cases move to a direct `_base_read` / `_have` call or are dropped. If dropped, that is a strong argument for removing the code too, rather than leaving it untested.
- [x] **Reversing #650 is a design decision the brief only partly hands to the human.** The header says "the human confirms this at sign-off". But sign-off comes after Do has spent its budget rewriting #650's test module. #650 (closed, merged as `2985031`) was opened specifically so that merge mode *could* merge these records (`test_merge_third_remote.py:1-10`). That conflict should be settled at plan sign-off, before Do starts. The issue itself offers the publish-time refusal as an equal alternative ("Fix, one of: … at publish … or … `_merge_one`"), and the brief puts that alternative out of scope without saying who chose.

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: merged-wider
- Iteration delta (if iterating):
- By / date: Eduard Ralph / 2026-10-14

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 5 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
