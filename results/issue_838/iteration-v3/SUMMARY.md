# Result — issue 838 / merge-mode-detect-review-remark-block

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: 
- Success criterion: With `wave_mode = "merge"` and `gh` stubbed: a PR whose rollup reads green, whose `gh pr view --json mergeStateStatus` is `BLOCKED`, and which has N unresolved threads from the GraphQL `reviewThreads` query (`gh api graphql`) makes `merge.merge_wave` return non-zero, with stderr containing "blocked by N unresolved review thread(s)" and each thread's path:line; `merge-remarks.json` is written into the bundle with one object per thread (id, path, line, body, author, url); the PR is returned to draft through `merge._undo_ready` and is not left marked ready. Legs: (i) with `merge_requires = "required"` the rollup gate is skipped (`merge.py:536`) and the block only shows as a failed `gh pr merge` (`merge.py:620-631`) — detection runs there too and gives the same message and file; (ii) `BLOCKED` with zero unresolved threads and no CHANGES_REQUESTED review (REVIEW_REQUIRED, required approvals, a ruleset) keeps the generic refusal, never "blocked by 0 thread(s)", and writes no `merge-remarks.json`; (iii) `mergeStateStatus = UNKNOWN` right after `gh pr ready` is polled on the same budget as the #462 rollup wait, then treated as not blocked by remarks; (iv) an outdated thread (`line: null`) reports `originalLine`; (v) a CHANGES_REQUESTED review with no threads is named as such in the message.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: 

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

Review issue #838: identify review remarks blocking non-final merge-mode PRs, report their locations, persist them in the bundle, and restore the PR to draft.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief defines an observable offline contract for both merge policies and the five edge cases, with explicit exclusions; the principal assertion checks the message, thread fields, artifact, and draft restoration (`template/tests/test_merge_review_remarks.py:210`). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing the tracked fix and running the unchanged new module produced 33 assertion failures across 20 tests, including missing remarks and the generic refusal, with no import errors (`template/tests/test_merge_review_remarks.py:214`, `template/tests/test_merge_review_remarks.py:220`). |
| C3 Change | PASS | The changes stay within merge diagnostics, associated wait accounting, documentation, and necessary tests; detection follows a failed merge under either policy and retains the existing refusal/draft-restoration path (`template/src/pdca_harness/merge.py:901`, `template/src/pdca_harness/merge.py:488`, `docs/07-crosscutting.md:887`). |
| C4 Verification (red→green) | PASS | After stash restoration, independently running the three affected modules passed all 88 tests; the new module's red leg failed on assertions, establishing the required behavior change (`template/tests/test_merge_review_remarks.py:210`; frozen corroboration: `gate-logs/C4-verify.log:10`). |
| C5 Causal adequacy | NEEDS-HUMAN | Decide whether open remarks alongside BLOCKED justify a definitive causal diagnosis — an independently exercised BLOCKED + REVIEW_REQUIRED + unresolved-thread case reports a thread block without establishing which host rule prevented merging; resolving those remarks may leave the actual block intact (`template/src/pdca_harness/merge.py:607`, `template/src/pdca_harness/merge.py:609`, `template/src/pdca_harness/merge.py:640`). |
| T1 Structure | PASS | The change reuses the existing host-read and refusal interfaces; the altered wait return contract has its sole production consumer and affected test doubles updated, with no new package/configuration surface (`template/src/pdca_harness/merge.py:237`, `template/src/pdca_harness/merge.py:841`, `template/src/pdca_harness/merged.py:187`, `template/tests/test_merge_third_remote.py:147`). |
| T2 Shape | PASS | Independent whitespace checking, docs lint, and rendering of 22 pages with internal-link audit all passed; the documented behavior matches artifact lifetime and draft restoration (`docs/07-crosscutting.md:887`; frozen docs and host-parity corroboration: `gate-logs/T2-docs.log:10`, `gate-logs/host-ci-docs.log:10`). |
| T3 Runtime | PASS | Independent focused execution passed 88 tests; the frozen full-suite output shows 50 root tests passing and 2667 driver tests passing with two skips, rather than only an unsupported green marker (`template/tests/test_merge_review_remarks.py:210`; `gate-logs/T3-suite.log:80`, `gate-logs/T3-suite.log:1902`). |
| T4 Contribution | N/A | The contribution gate deliberately deferred because publish artifacts do not exist yet; its substantive audit must rerun at publish, so this is neither a reproduced green nor a missing-evidence finding (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Confirm affected-file prior art across merged history and closed/rejected work before accepting a repeat approach — the local path-filtered history search returned only the synthetic pre-fix commit, and the supplied artifacts contain no closed/rejected-PR corpus or completed prior-art check (`docs/05-check.md:523`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the offline diagnostic/artifact contract is sufficient for operational use — real GitHub behavior and permissions were not exercised, so host compatibility rests on subprocess fixtures; approve the diagnostic certainty and the nullable-threads contract for downstream consumers (`template/tests/test_merge_review_remarks.py:16`, `template/src/pdca_harness/merge.py:601`). |

Independent verification used the disposable `$PDCA_TARGET` supplied by the harness. From its `template/`, I ran `PYTHONPATH=src python3 -m unittest tests.test_merge_review_remarks tests.test_merge tests.test_merge_third_remote` (88 passing), stashed the tracked changes, ran `PYTHONPATH=src python3 -m unittest tests.test_merge_review_remarks` (20 tests, 33 assertion failures), restored the stash, and reran the three modules (88 passing). All temporary test data stayed under this review's cwd. The original patched working-tree state was restored. Every printed ready/merge operation in these tests was intercepted by the subprocess stub; no live PR was changed.

The independently passing regressions cover threads beyond 100 resolved threads, removal of a previous attempt's artifact, all three waits sharing one allowance, and failed/incomplete GraphQL reads remaining unknown rather than empty (`template/tests/test_merge_review_remarks.py:231`, `template/tests/test_merge_review_remarks.py:263`, `template/tests/test_merge_review_remarks.py:349`, `template/tests/test_merge_review_remarks.py:432`). The C5 capability-probe smell test found no optional-capability guard masking a load-time cause. The separate C5 attribution investigation returned exit 1, wrote the remarks artifact, restored draft, and printed “blocked by 1 unresolved review thread(s)” for a fixture whose review decision was REVIEW_REQUIRED. That demonstrates the inference, not proof of the host's actual reason for refusal. This is a scope/diagnostic decision, not an established builder-fixable failure of the stated offline success criterion.

I independently ran `python3 docs/publishing/tools/lint_docs.py`, `python3 docs/publishing/tools/render_site.py --check -o /tmp/pdca-review-q4q6owz_/reviewer-scratch/site`, and `git diff --check`; all passed. Instance-scoped gate wrappers are not supplied here: I read their captured outputs for C4, production-path scanning, docs/host parity, full runtime suites, and deferred contribution checking. The full runtime suites and production-path scanner were adjudicated from those logs rather than claimed as independently rerun. The new tests import the production package and exercise `merge.merge_wave` (`template/tests/test_merge_review_remarks.py:33`, `template/tests/test_merge_review_remarks.py:189`).

For host compatibility sign-off, a human can perform read-only checks on an existing ready, blocked PR: run `gh pr view "$PR_URL" --json mergeStateStatus,reviewDecision,latestReviews`; then, from the target's `template/`, run `PR_URL="$PR_URL" PYTHONPATH=src python3 -c 'import json,os; from pdca_harness import merge; print(json.dumps(merge._review_threads(os.environ["PR_URL"]), indent=2))'`. Compare the returned unresolved threads, pagination totals, original lines, authors, and URLs with that PR's review threads; inspect its rules to distinguish a review-resolution requirement from another block. These reads do not ready or merge a PR. The available integration document is a template with human-only items still TODO, not a completed instance policy (`template/docs/INTEGRATION.md.jinja:80`).

The affected-path prior-art investigation ran `git log --all --oneline -- docs/07-crosscutting.md template/src/pdca_harness/merge.py template/tests/test_merge.py template/tests/test_merge_review_remarks.py template/tests/test_merge_third_remote.py`; its only result was `c7cd2fa pre-fix base 3c11556651da9741e35f704c0497a5bf326cbd42`. `git remote -v` returned nothing. This establishes the supplied history's limitation, not that upstream lacks prior art. No source finding depends on another checkout or a stale target.

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — issue #838

No crash or draft-restore bug found: every new read that runs while the PR is marked ready fails safely, and `_refuse` returns the PR to draft. The gates pass (`C4-verify` and `T3-suite` in `check-gates.json`). There are four findings. The first is the only one that needs a decision.

- NEEDS-HUMAN [human] — `template/src/pdca_harness/merge.py:606-615`: the stop can blame the wrong cause. `BLOCKED` has many possible causes, and the patch treats any unresolved thread or CHANGES_REQUESTED review on a `BLOCKED` PR as the reason. Nothing checks that the host actually requires resolved threads. For example, take a PR on a repo that does not require conversation resolution, with one open bot comment, that is really blocked by a missing required approval or (under `merge_requires = "required"`) a failed required check. It reports "blocked by 1 unresolved review thread(s)", drops the generic refusal that lists the other causes, and writes `merge-remarks.json`. A CHANGES_REQUESTED review from someone whose review does not count has the same effect: `latestReviews` is checked first, so it is named even when `reviewDecision` is `APPROVED`. Child-3 is meant to act on this file, so it could work on remarks that are not the real block. The `gh pr merge` error is still printed at `merge.py:885`, but the file does not record it. Decision needed: accept this as "remarks present on a blocked PR", or soften the wording and store the merge error in the file, or read the host's branch rules to confirm the cause (more calls and permissions, likely beyond this brief's scope).

- `template/src/pdca_harness/merge.py:731-735`: the comment says each attempt removes the file "before it decides anything", and `merge.py:60-61` says much the same, but the unlink comes after three early returns (`:698-699` not COMPLETE, `:706-709` no recorded PR, `:717-725` stacked record). `merge-remarks.json` is also not in `state.DOWNSTREAM_OF_BRIEF` (`state.py:116`) or `DOWNSTREAM_GLOBS` (`state.py:155`), so `_archive_iteration` (`driver.py:457`) would leave it at the top level. If a bundle that holds the file ever leaves COMPLETE and is rebuilt, the old file stays beside the new attempt. I did not confirm that a COMPLETE bundle can reach that path, so treat this as low risk. Cheapest fix: correct the comment, and add the file to the archive list if child-3 will read it.

- `template/src/pdca_harness/merge.py:606-608`: a failed merge-state read (`_pr_view` returned None) falls back to the generic refusal without saying so. A failed thread read does print a warning (`:616-618`). An operator cannot tell "not blocked by remarks" from "could not check". One `stderr` line, matching the thread warning, would fix it.

- `template/src/pdca_harness/merge.py:610-614`: an unknown author is written two ways in the same file. Threads use `""` (`_login`), while `changes_requested_by` uses the placeholder `"?"`, and `test_merge_review_remarks.py` (`test_an_author_that_is_not_an_object_is_no_author`) locks both in. Anything reading the file could take `"?"` for a login. Keep `"?"` for the printed message only, and write `""` or `null` to the file. Child-3 is the first reader, so this is cheapest to change now.

Reuse and simplification: nothing to flag. The patch uses `merged._pr_view`, `_refuse` and `_undo_ready` as the brief asks, and the extra `waited` value from `_wait_for_green` has one source caller (`merge.py:841`), with the test stubs updated.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] C5 Causal adequacy — Decide whether open remarks alongside BLOCKED justify a definitive causal diagnosis — an independently exercised BLOCKED + REVIEW_REQUIRED + unresolved-thread case reports a thread block without establishing which host rule prevented merging; resolving those remarks may leave the actual block intact (`template/src/pdca_harness/merge.py:607`, `template/src/pdca_harness/merge.py:609`, `template/src/pdca_harness/merge.py:640`).
- [x] T5 Judgment — Confirm affected-file prior art across merged history and closed/rejected work before accepting a repeat approach — the local path-filtered history search returned only the synthetic pre-fix commit, and the supplied artifacts contain no closed/rejected-PR corpus or completed prior-art check (`docs/05-check.md:523`).
- [ ] Validation — fitness-to-purpose — Decide whether the offline diagnostic/artifact contract is sufficient for operational use — real GitHub behavior and permissions were not exercised, so host compatibility rests on subprocess fixtures; approve the diagnostic certainty and the nullable-threads contract for downstream consumers (`template/tests/test_merge_review_remarks.py:16`, `template/src/pdca_harness/merge.py:601`).
- [ ] `template/src/pdca_harness/merge.py:606-615`: the stop can blame the wrong cause. `BLOCKED` has many possible causes, and the patch treats any unresolved thread or CHANGES_REQUESTED review on a `BLOCKED` PR as the reason. Nothing checks that the host actually requires resolved threads. For example, take a PR on a repo that does not require conversation resolution, with one open bot comment, that is really blocked by a missing required approval or (under `merge_requires = "required"`) a failed required check. It reports "blocked by 1 unresolved review thread(s)", drops the generic refusal that lists the other causes, and writes `merge-remarks.json`. A CHANGES_REQUESTED review from someone whose review does not count has the same effect: `latestReviews` is checked first, so it is named even when `reviewDecision` is `APPROVED`. Child-3 is meant to act on this file, so it could work on remarks that are not the real block. The `gh pr merge` error is still printed at `merge.py:885`, but the file does not record it. Decision needed: accept this as "remarks present on a blocked PR", or soften the wording and store the merge error in the file, or read the host's branch rules to confirm the cause (more calls and permissions, likely beyond this brief's scope).
- [x] T5 Judgment — Establish prior art by affected file path before accepting the approach — the supplied target has only one synthetic base commit, no remotes, and no closed/rejected-work evidence, so merged-history and rejected alternatives remain unconfirmed; affected paths include `template/src/pdca_harness/merge.py:500` and `docs/07-crosscutting.md:887`.
- [ ] `template/src/pdca_harness/merge.py:582-601` — The message says the PR "is blocked by" the threads or the CHANGES_REQUESTED review whenever `mergeStateStatus` is `BLOCKED` and any exist. GitHub only blocks on unresolved threads when "require conversation resolution" is on, and only blocks on a CHANGES_REQUESTED review when reviews are required. So a PR blocked by a missing approval or a ruleset, which also happens to have an open thread, is reported as a remarks block, and the real cause is dropped (for example, `reviewDecision == "REVIEW_REQUIRED"` never shows up in the message). The brief accepts this guess, but the wording claims a cause the driver cannot confirm. Decide whether that is acceptable, or soften the wording to something like "BLOCKED; unresolved remarks: …" and include `reviewDecision`.
- [x] T5 Judgment — Establish that merged and closed/rejected work does not already supersede these affected paths — the target contains one synthetic base commit and no remotes, while the supplied ordering note is not a path-based prior-art search; brief.md:12; template/src/pdca_harness/merge.py:676.

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
- Iteration delta (if iterating): The stop can blame the wrong cause: any open thread or CHANGES_REQUESTED review on a BLOCKED PR is named as the block, even when the real block is something else (for example a missing approval). Keep the detection and the wording the brief requires ("blocked by N unresolved review thread(s)"), and make the real signals visible: - Save `reviewDecision` and the failed `gh pr merge` error in `merge-remarks.json`. - Show `reviewDecision` in the stop message. - Add tests for both, including a BLOCKED + REVIEW_REQUIRED + open thread case. Do not read the host's branch rules: that needs more calls and permissions and is beyond this brief. Prior art is cleared by the human. The live read-only check against GitHub (real `gh api graphql` query) is held until the rebuilt change is bug free; it is not build work.
- By / date: Eduard Ralph / 2026-10-30

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
