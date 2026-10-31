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

Review merge-mode detection and recording of unresolved review threads or changes-requested reviews, including pagination and removal of stale remarks.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The offline acceptance contract distinguishes remarks from other merge blocks, requires draft restoration, and bounds UNKNOWN polling by the rollup budget; brief.md:4. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing the production fix reproduces the generic refusal and missing artifact through assertion failures, without import errors: 11 tests run, 13 failures including subtests; reviewer-verification.log:140. |
| C3 Change | PASS | The affected paths remain within merge refusal diagnostics, bundle evidence, regression coverage, and the requested documentation; template/src/pdca_harness/merge.py:868; docs/07-crosscutting.md:887. |
| C4 Verification (red→green) | PASS | Independent stash/pop reproduction changes the supplied regression suite from 13 assertion failures to all 11 tests passing, and the original target diff was restored; reviewer-verification.log:140; reviewer-verification.log:163. |
| C5 Causal adequacy | NEEDS-HUMAN [impl] | Preserve the shared merge-wait bound required by brief.md:4 — with a 20 s allowance, rollup confirmation plus persistent UNKNOWN waits 35 s, delaying refusal and draft restoration; template/src/pdca_harness/merge.py:868; reviewer-budget.log:10. |
| T1 Structure | PASS | The diagnostic path reuses the existing PR-field reader and refusal/draft-restoration boundary, keeping merge policy in its existing module; template/src/pdca_harness/merge.py:527; template/src/pdca_harness/merge.py:870. |
| T2 Shape | PASS | Independent docs lint, 22-page render/link audit, six checker tests, 458-link audit, ADR audit, production-import scanner, and diff whitespace check pass; docs/07-crosscutting.md:887; template/tests/test_merge_review_remarks.py:31; gate-logs/T2-docs.log:16. |
| T3 Runtime | PASS | Independently reran all 107 merge-related tests successfully; frozen full-suite evidence reports 50 root tests passing and 2,658 driver tests passing with two skips; gate-logs/T3-suite.log:80; gate-logs/T3-suite.log:1902. |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the substantive contribution audit is deferred to its mandatory publish-time rerun, not awaiting human clearance; gate-logs/T4-contribution.log:10. |
| T5 Judgment | NEEDS-HUMAN | Establish that merged and closed/rejected work does not already supersede these affected paths — the target contains one synthetic base commit and no remotes, while the supplied ordering note is not a path-based prior-art search; brief.md:12; template/src/pdca_harness/merge.py:676. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether offline evidence is sufficient for operational sign-off or require a human-controlled GitHub integration run — real gh/GraphQL responses and review-policy enforcement were not exercised; host behavior rests on stubbed responses; brief.md:9; template/tests/test_merge_review_remarks.py:98. |

All source citations above refer to the patched source under `$PDCA_TARGET`; brief, gate-log, and reviewer-log citations refer to this review directory. The target was readable and matched the supplied patch. No stale-target caveat applies. Instance-scoped gate wrappers are absent from this bundle; their frozen logs were inspected, and available target validators and affected tests were rerun directly. The full root/driver suite results above are frozen evidence, not a claim of an independent full-suite rerun. The integration template enumerates no concrete additional human-only checks (template/docs/INTEGRATION.md.jinja:80).

The remaining implementation concern is the combined timeout. `_wait_for_green` spends 15 s confirming an immediately green rollup; `_remarks_block` then receives the full 20 s again (template/src/pdca_harness/merge.py:819; template/src/pdca_harness/merge.py:868), and `_merge_state` starts its counter at zero (template/src/pdca_harness/merge.py:525). Driving the existing `_Gh(states=("UNKNOWN",))` through `MergeReviewRemarks._run(..., merge_wait_secs=20)` with the default merge requirements records sleeps `[15, 5, 5, 5, 5]`, then the generic refusal (reviewer-budget.log:3). This exceeds the shared allowance before returning the PR to draft. Carry the remaining allowance into state polling and add a combined-wait regression; the existing bounded test selects `merge_requires="required"`, so it cannot expose the earlier rollup expenditure (template/tests/test_merge_review_remarks.py:298).

The previous implementation findings are discharged within the exercised offline contract: the three-page regression finds both unresolved threads behind resolved threads, and subsequent successful, generic-refusal, early-refusal, and already-merged attempts remove the old artifact; dry runs preserve it (template/tests/test_merge_review_remarks.py:190; template/tests/test_merge_review_remarks.py:225; template/tests/test_merge_review_remarks.py:247). The patch introduces no capability probe or load-time symptom guard that triggers the C5 smell-test.

Prior-art investigation directly queried `git log --all --` for `docs/07-crosscutting.md`, `template/src/pdca_harness/merge.py`, and `template/tests/test_merge_review_remarks.py`: the only result was `fec42e7 pre-fix base 3c11556651da9741e35f704c0497a5bf326cbd42`. `git remote -v` returned nothing. No evidence of an affected-path search across closed/rejected work was supplied; this is a human evidence decision, not an inferred duplicate or patch defect.

The local `gh pr view --help` advertises all three requested JSON fields, but no live API or PR-changing command was run. Operational validation remains a human decision: on a human-controlled sandbox configured to require thread resolution, exercise a non-final merge-mode PR with an unresolved thread and then with a changes-requested review; verify the named stop, bundle remarks, and draft restoration, and repeat after resolution to verify artifact removal.

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — issue #838 (merge mode: detect a review-remark block)

Lens: bugs the patch introduces, plus reuse and simplification. The gates are green (C4 red-to-green passes, T3 suite OK). Both items from the round-1 carry-forward are fixed: every thread page is now read (`template/src/pdca_harness/merge.py:547-581`), and `merge-remarks.json` is removed at the start of each real attempt (`template/src/pdca_harness/merge.py:717`), with tests for both. What's left is small.

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/merge.py:595-607`: if the GraphQL thread read fails (`_review_threads` returns None) but a CHANGES_REQUESTED review exists, the code still writes `merge-remarks.json` with `"threads": []`, and the stderr message names only the review. The "threads could not be read" warning at :603-605 is printed only when there are no changes either. So the file says "no unresolved threads" when the truth is "threads unknown". Child-3 is meant to act on this file, so it would treat a partial read as complete. Fix: record the failed read in the file (for example `"threads": null` or `"threads_unreadable": true`) and say so in the message. Add a test with a failing `gh api graphql` plus a CHANGES_REQUESTED review.
- `template/src/pdca_harness/merge.py:592` and `:868`: `_remarks_block` gets a fresh, full `cfg.merge_wait_secs` to poll `UNKNOWN`, separate from whatever the update wait and rollup wait already used (`:806`, `:819` share one budget through `spent=`). In the worst case the PR stays marked ready for about twice `merge_wait_secs` before `_undo_ready` runs. The brief says "polled on the same budget as the #462 rollup wait", which can be read either way. Low impact, because a failed `gh pr merge` usually finds the state already computed. Mentioned only so the reading is a deliberate choice.
- `template/src/pdca_harness/merge.py:578` (pinned by `template/tests/test_merge_review_remarks.py:212`): if the host repeats a page cursor, the whole result is thrown away, including unresolved threads already collected, and the run falls back to the generic refusal. That fails safe (the run still stops and undoes the ready-mark), but it hides remarks it already knows about. Optional: return what was read and mark it as partial. Advisory only.
- `template/src/pdca_harness/merge.py:551`: `subprocess.run` for `gh api graphql` has no `except OSError`, while its peer `merged._pr_view` (`template/src/pdca_harness/merged.py:192-196`) has one. In practice this is unreachable, because `gh pr merge` has just run. Noted for consistency only.
- `template/src/pdca_harness/merge.py:564`: `[0] or {}` handles a null first comment but not one that isn't a dict (a non-dict would raise `AttributeError`, which nothing catches). The GitHub schema rules this out, so this is a nit, not a defect.

Reuse: `_merge_state` reuses `merged._pr_view`, refusals go through `_refuse` / `_undo_ready`, and the poll loop copies the `_wait_for_update` pattern (`template/src/pdca_harness/merge.py:445-467`) through the patchable `_sleep`. I found no duplicated helper worth pulling out. The tests drive `merge.merge_wave` end to end through the production path, as C5 confirms.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] C5 Causal adequacy — Preserve the shared merge-wait bound required by brief.md:4 — with a 20 s allowance, rollup confirmation plus persistent UNKNOWN waits 35 s, delaying refusal and draft restoration; template/src/pdca_harness/merge.py:868; reviewer-budget.log:10.
- [ ] T5 Judgment — Establish that merged and closed/rejected work does not already supersede these affected paths — the target contains one synthetic base commit and no remotes, while the supplied ordering note is not a path-based prior-art search; brief.md:12; template/src/pdca_harness/merge.py:676.
- [ ] Validation — fitness-to-purpose — Decide whether offline evidence is sufficient for operational sign-off or require a human-controlled GitHub integration run — real gh/GraphQL responses and review-policy enforcement were not exercised; host behavior rests on stubbed responses; brief.md:9; template/tests/test_merge_review_remarks.py:98.
- [ ] `template/src/pdca_harness/merge.py:595-607`: if the GraphQL thread read fails (`_review_threads` returns None) but a CHANGES_REQUESTED review exists, the code still writes `merge-remarks.json` with `"threads": []`, and the stderr message names only the review. The "threads could not be read" warning at :603-605 is printed only when there are no changes either. So the file says "no unresolved threads" when the truth is "threads unknown". Child-3 is meant to act on this file, so it would treat a partial read as complete. Fix: record the failed read in the file (for example `"threads": null` or `"threads_unreadable": true`) and say so in the message. Add a test with a failing `gh api graphql` plus a CHANGES_REQUESTED review.
- [ ] T5 Judgment — Establish prior art by affected file path before accepting the approach — the supplied target has only one synthetic base commit, no remotes, and no closed/rejected-work evidence, so merged-history and rejected alternatives remain unconfirmed; affected paths include `template/src/pdca_harness/merge.py:500` and `docs/07-crosscutting.md:887`.
- [ ] `template/src/pdca_harness/merge.py:582-601` — The message says the PR "is blocked by" the threads or the CHANGES_REQUESTED review whenever `mergeStateStatus` is `BLOCKED` and any exist. GitHub only blocks on unresolved threads when "require conversation resolution" is on, and only blocks on a CHANGES_REQUESTED review when reviews are required. So a PR blocked by a missing approval or a ruleset, which also happens to have an open thread, is reported as a remarks block, and the real cause is dropped (for example, `reviewDecision == "REVIEW_REQUIRED"` never shows up in the message). The brief accepts this guess, but the wording claims a cause the driver cannot confirm. Decide whether that is acceptable, or soften the wording to something like "BLOCKED; unresolved remarks: …" and include `reviewDecision`.

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
- Iteration delta (if iterating): Auto-iterate (round 2): rebuilding for the implementation-level findings — C5 Causal adequacy — Preserve the shared merge-wait bound required by brief.md:4 — with a 20 s allowance, rollup confirmation plus persistent UNKNOWN waits 35 s, delaying refusal and draft restoration; template/src/pdca_harness/merge.py:868; reviewer-budget.log:10.; `template/src/pdca_harness/merge.py:595-607`: if the GraphQL thread read fails (`_review_threads` returns None) but a CHANGES_REQUESTED review exists, the code still writes `merge-remarks.json` with `"threads": []`, and the stderr message names only the review. The "threads could not be read" warning at :603-605 is printed only when there are no changes either. So the file says "no unresolved threads" when the truth is "threads unknown". Child-3 is meant to act on this file, so it would treat a partial read as complete. Fix: record the failed read in the file (for example `"threads": null` or `"threads_unreadable": true`) and say so in the message. Add a test with a failing `gh api graphql` plus a CHANGES_REQUESTED review.. Deferred, not addressed here: 1 finding(s) that need human judgment, held in deferred-findings.json for the human at handover — not build work
- By / date: auto-iterate / 2026-10-30

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
