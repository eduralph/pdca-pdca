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

Review merge mode’s diagnosis and bundle capture of unresolved review threads or CHANGES_REQUESTED reviews after a host-refused merge (#838).

Source citations below are relative to `$PDCA_TARGET` (`/tmp/pdca-review-z64abggz/target`); input and evidence citations are relative to this review sandbox.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The offline acceptance contract distinguishes review blocks from other BLOCKED states, covers both merge policies, and requires draft restoration; `brief.md:4`, `template/tests/test_merge_review_remarks.py:144`. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing the tracked fix produced six assertion failures among seven tests, including the missing thread diagnosis, without import failures; `review-red.log:1`, `template/tests/test_merge_review_remarks.py:148`. |
| C3 Change | PASS | The three affected files stay within the failed-merge diagnosis, bundle evidence, regression tests, and corresponding documentation scope; `template/src/pdca_harness/merge.py:842`, `docs/07-crosscutting.md:887`. |
| C4 Verification (red→green) | PASS | After stash pop, all seven specified tests passed and the tracked diff matched its original bytes; this verifies the stubbed contract, with the collection gap recorded under C5; `review-green.log:1`, `gate-logs/C4-verify.log:10`. |
| C5 Causal adequacy | NEEDS-HUMAN [impl] | Collect every thread page and add a pagination regression — a BLOCKED PR with 100 resolved threads followed by an unresolved thread still gets the generic refusal and no artifact; `template/src/pdca_harness/merge.py:500`, `template/src/pdca_harness/merge.py:582`. |
| T1 Structure | PASS | The diagnosis uses the existing PR reader and refusal/draft-restoration path, keeping the merge decision in its existing module; `template/src/pdca_harness/merged.py:187`, `template/src/pdca_harness/merge.py:483`, `template/src/pdca_harness/merge.py:844`. |
| T2 Shape | PASS | Independently rerun docs lint, 22-page render/link audit, six checker tests, relative-link check, ADR index check, and diff whitespace check all passed; `docs/07-crosscutting.md:887`, `gate-logs/T2-docs.log:10`, `gate-logs/host-ci-docs.log:10`. |
| T3 Runtime | PASS | All 103 merge-related tests passed locally; the frozen full-suite output records 50 root tests passing and 2,654 driver tests passing with two skips; `template/tests/test_merge_review_remarks.py:129`, `gate-logs/T3-suite.log:80`, `gate-logs/T3-suite.log:1902`. |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the substantive audit must rerun at publish, as the deferred gate explicitly states; `gate-logs/T4-contribution.log:10`. |
| T5 Judgment | NEEDS-HUMAN | Establish prior art by affected file path before accepting the approach — the supplied target has only one synthetic base commit, no remotes, and no closed/rejected-work evidence, so merged-history and rejected alternatives remain unconfirmed; affected paths include `template/src/pdca_harness/merge.py:500` and `docs/07-crosscutting.md:887`. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether offline evidence suffices for the intended GitHub workflow — real GitHub/gh review-block behavior was not exercised, so evidence rests on curated subprocess responses despite the brief declaring no external dependencies; `brief.md:9`, `template/tests/test_merge_review_remarks.py:82`, `template/src/pdca_harness/merge.py:536`. |

**Builder-fixable finding (P2): thread collection silently stops at 100.** The query at `template/src/pdca_harness/merge.py:500` requests `reviewThreads(first: 100)` without `pageInfo` or a cursor. Resolved threads consume that limit before local filtering at `template/src/pdca_harness/merge.py:549`. Consequently a remaining blocker can be invisible, or the count and artifact can omit remarks on later pages. This violates the unbounded N-thread criterion and the documented promise to list each thread (`brief.md:4`, `docs/07-crosscutting.md:889`).

I exercised the patched public `merge_wave` path using the shipped test fixture with a paginated GraphQL stand-in: page one contained 100 resolved threads and advertised another page; page two held unresolved `src/missed.py:101`. Observed: exit 1, exactly one GraphQL request, no `src/missed.py:101` in stderr, no `merge-remarks.json`, and successful draft restoration. The generic refusal remained. Follow `hasNextPage`/`endCursor`, aggregate unresolved threads across all pages, and cover both this hidden-blocker case and an unresolved count spanning pages. The existing stand-in at `template/tests/test_merge_review_remarks.py:82` returns the complete collection in one response and does not exercise pagination.

Independent verification used `git stash push` on the tracked fix, ran `PYTHONPATH=src python3 -m unittest tests.test_merge_review_remarks` in `target/template`, restored with `git stash pop`, and reran the same command. Test temporary files were confined to this sandbox with `TMPDIR`. The patch was restored unchanged. Further checks used `python3 -m unittest discover -s tests -p 'test_merge*.py'`, the actual docs lint/renderer and `.github/docs-check` tools, and `template/scripts/checks/test_exercises_production.py` with this bundle and `PDCA_PROD_PACKAGE=pdca_harness`; the production-import heuristic passed. No capability probe or guard masking a load-time cause was introduced.

All six frozen gate logs were inspected. Instance-scoped wrappers were not available here; their absence is not a defect. The broad root/driver suite verdict relies on the captured test summaries rather than a local full-suite rerun. The host-CI log proves a local lint/render parity run, not an observed hosted CI execution. The deferred contribution row is not an outstanding human approval item.

For prior art, `git log --all --oneline -- docs/07-crosscutting.md template/src/pdca_harness/merge.py template/tests/test_merge_review_remarks.py` returned only `9ec438a pre-fix base 3c11556651da9741e35f704c0497a5bf326cbd42`; `git rev-list --all --count` returned 1 and `git remote -v` was empty. The bundle supplies no path-based closed/rejected-work search. The target is readable and matches the supplied patch; this is an evidence limitation, not target staleness or a verification failure.

The available integration document is the unfilled template (`template/docs/INTEGRATION.md.jinja:80`), so it supplies no additional concrete project-specific human-only items. Fitness-to-purpose and the unexercised GitHub dependency remain for human sign-off. A read-only live check can begin with `gh pr view <blocked-pr-url> --json mergeStateStatus,reviewDecision,latestReviews`, comparing the real payload and review-thread query results against the tested assumptions; the offline runs establish no live host outcome.

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — issue #838 (merge mode: name a block by review remarks)

Overall: the patch matches the brief. It reuses `merged._pr_view`, `_refuse`, `_undo_ready` and `_sleep` instead of copying them, and the tests drive the real `merge.merge_wave` path through a stubbed `gh`. No blocking bugs found. Findings, most important first:

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/merge.py:588` — `merge-remarks.json` is written but never removed. If a later run of the same bundle stops on a generic refusal (leg ii) or merges cleanly, the old file from an earlier run is still in the bundle and describes remarks that may already be resolved. Child-3 is meant to act on this file, so stale contents are a real hazard. Fix: unlink `d / REMARKS_FILE` (with `missing_ok=True`) at the start of `_remarks_block`, or when `_merge_one` merges successfully. Add a test that reruns after the threads are resolved.
- NEEDS-HUMAN [human] — `template/src/pdca_harness/merge.py:582-601` — The message says the PR "is blocked by" the threads or the CHANGES_REQUESTED review whenever `mergeStateStatus` is `BLOCKED` and any exist. GitHub only blocks on unresolved threads when "require conversation resolution" is on, and only blocks on a CHANGES_REQUESTED review when reviews are required. So a PR blocked by a missing approval or a ruleset, which also happens to have an open thread, is reported as a remarks block, and the real cause is dropped (for example, `reviewDecision == "REVIEW_REQUIRED"` never shows up in the message). The brief accepts this guess, but the wording claims a cause the driver cannot confirm. Decide whether that is acceptable, or soften the wording to something like "BLOCKED; unresolved remarks: …" and include `reviewDecision`.
- `template/src/pdca_harness/merge.py:500` — `reviewThreads(first: 100)` has no paging. A PR with more than 100 threads (resolved ones count toward the 100) silently reports fewer remarks than it has, and could report zero, which falls back to the generic refusal. This is rare. A `pageInfo { hasNextPage }` check plus a "(list truncated)" note would make it visible.
- `template/src/pdca_harness/merge.py:588` — If the `write_text` raises an `OSError`, the exception escapes `_merge_one` before `_refuse` → `_undo_ready` runs, so the PR stays marked ready. That is the exact state #462 guards against. The risk is low (the bundle dir is normally writable), but a `try/except OSError` that still returns the reason would close it.
- `template/src/pdca_harness/merge.py:536-539` — When `gh api graphql` fails, its stderr is thrown away. Only the fixed "could not be read" line (:583-585) is printed, so an auth or scope error (for example, a token without access to the repo) cannot be diagnosed from the run output. Printing `r.stderr` there would help. The `subprocess.run` also has no `OSError` guard, unlike `merged._pr_view`. That is harmless here because `gh pr merge` has already run.
- `template/tests/test_merge_review_remarks.py:191-197` — The "UNKNOWN then BLOCKED" test does not check that the sleeps stay within `merge_wait_secs`, and does not call `_assert_undone`. Its sibling at :199 covers the budget, so this is only a small gap.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] C5 Causal adequacy — Collect every thread page and add a pagination regression — a BLOCKED PR with 100 resolved threads followed by an unresolved thread still gets the generic refusal and no artifact; `template/src/pdca_harness/merge.py:500`, `template/src/pdca_harness/merge.py:582`.
- [ ] T5 Judgment — Establish prior art by affected file path before accepting the approach — the supplied target has only one synthetic base commit, no remotes, and no closed/rejected-work evidence, so merged-history and rejected alternatives remain unconfirmed; affected paths include `template/src/pdca_harness/merge.py:500` and `docs/07-crosscutting.md:887`.
- [ ] Validation — fitness-to-purpose — Decide whether offline evidence suffices for the intended GitHub workflow — real GitHub/gh review-block behavior was not exercised, so evidence rests on curated subprocess responses despite the brief declaring no external dependencies; `brief.md:9`, `template/tests/test_merge_review_remarks.py:82`, `template/src/pdca_harness/merge.py:536`.
- [ ] `template/src/pdca_harness/merge.py:588` — `merge-remarks.json` is written but never removed. If a later run of the same bundle stops on a generic refusal (leg ii) or merges cleanly, the old file from an earlier run is still in the bundle and describes remarks that may already be resolved. Child-3 is meant to act on this file, so stale contents are a real hazard. Fix: unlink `d / REMARKS_FILE` (with `missing_ok=True`) at the start of `_remarks_block`, or when `_merge_one` merges successfully. Add a test that reruns after the threads are resolved.
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
- Iteration delta (if iterating): Auto-iterate (round 1): rebuilding for the implementation-level findings — C5 Causal adequacy — Collect every thread page and add a pagination regression — a BLOCKED PR with 100 resolved threads followed by an unresolved thread still gets the generic refusal and no artifact; `template/src/pdca_harness/merge.py:500`, `template/src/pdca_harness/merge.py:582`.; `template/src/pdca_harness/merge.py:588` — `merge-remarks.json` is written but never removed. If a later run of the same bundle stops on a generic refusal (leg ii) or merges cleanly, the old file from an earlier run is still in the bundle and describes remarks that may already be resolved. Child-3 is meant to act on this file, so stale contents are a real hazard. Fix: unlink `d / REMARKS_FILE` (with `missing_ok=True`) at the start of `_remarks_block`, or when `_merge_one` merges successfully. Add a test that reruns after the threads are resolved.. Deferred, not addressed here: 2 finding(s) that need human judgment, held in deferred-findings.json for the human at handover — not build work
- By / date: auto-iterate / 2026-10-30

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
