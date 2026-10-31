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

Review merge-mode diagnostics that name unresolved review remarks, preserve them in the bundle, and restore a blocked PR to draft.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The offline contract defines both merge policies, generic refusals, UNKNOWN polling, outdated lines, and changes-requested reviews, with explicit scope decisions; brief.md:4, brief.md:32, brief.md:44. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only the two production files leaves the new tests importable and produces 63 assertion failures across 30 tests, including the missing diagnostic; reviewer-red.log:272, reviewer-red.log:648; template/tests/test_merge_review_remarks.py:242. |
| C3 Change | PASS | The change stays within the approved diagnostic outcome and its artifact lifecycle; the human explicitly retained this scope despite size, and no new configuration or remark remediation appears; brief.md:44; template/src/pdca_harness/merge.py:931; template/src/pdca_harness/state.py:156. |
| C4 Verification (red→green) | PASS | Restoring the stash makes all 98 focused tests pass; the independent red leg fails on behavior rather than import or changed return arity, corroborating the frozen gate; reviewer-green.log:3; gate-logs/C4-verify.log:825; template/tests/test_merge_review_remarks.py:240. |
| C5 Causal adequacy | PASS | Production-path regressions cover pagination, stale records, shared wait limits, unknown thread reads, host selection, and partial writes; the approved inference retains the host's decision and error for interpretation; template/tests/test_merge_review_remarks.py:262, template/tests/test_merge_review_remarks.py:412, template/tests/test_merge_review_remarks.py:562, template/tests/test_merge_review_remarks.py:664, template/tests/test_merge_review_remarks.py:747. |
| T1 Structure | PASS | The helpers retain the existing refusal/draft-restoration path and reuse the existing atomic-record writer and archive registry; production-import scanning also passes; template/src/pdca_harness/merge.py:655, template/src/pdca_harness/merge.py:933, template/src/pdca_harness/state.py:156. |
| T2 Shape | PASS | Independently rerun docs lint, 64-page rendering/link audit, relative-link and ADR scanners, six checker tests, and diff whitespace checks pass; the new operational wording matches the approved inference; docs/07-crosscutting.md:929; gate-logs/T2-docs.log:11; gate-logs/host-ci-docs.log:14. |
| T3 Runtime | PASS | Independent driver discovery passes 2,697 tests (two skips); frozen evidence additionally shows 50 root tests including render/update compatibility passing, while this review host cannot import Copier; reviewer-suite.log:1819; gate-logs/T3-suite.log:80; reviewer-root-suite.log:6. |
| T4 Contribution | N/A | Contribution artifacts are intentionally absent at Check; the substantive audit must rerun at publish, as the deferred gate records; gate-logs/T4-contribution.log:10. |
| T5 Judgment | PASS | Prior art and the enlarged single-outcome scope were explicitly cleared by the human; the known ambiguity of BLOCKED is disclosed and the requested diagnostic signals are tested, so no new implementation concern remains; brief.md:39, brief.md:44; template/tests/test_merge_review_remarks.py:412. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether these diagnostics and records serve merge-mode operators, and discharge the held live read-only GitHub check — real gh/GraphQL was not exercised, so behavioral evidence rests on stubs; brief.md:49; template/tests/test_merge_review_remarks.py:89; template/src/pdca_harness/merge.py:574. |

Code citations resolve against `/tmp/pdca-review-49neea4v/target` (`$PDCA_TARGET`); input and evidence citations resolve against the review cwd. The disposable target contains the patch, and the stash/pop round-trip preserved every tracked patch hunk. No implementation edits were made.

Independent evidence: `reviewer-red.log` records the new regression module against the pre-fix production tree; `reviewer-green.log` records the three affected test modules after restoration. The full driver rerun is in `reviewer-suite.log`. The production-import scanner confirms the new tests import `pdca_harness`. Documentation checks found 623 relative links across 71 Markdown files with zero broken links, and 12 ADRs with zero index problems.

The root rerun exited 77 because `/usr/bin/python3` cannot import Copier; 45 tests ran with three skips (`reviewer-root-suite.log:3`). This is a review-host limitation, not a patch failure. The frozen T3 log explicitly shows actual render and update cases executing successfully (`gate-logs/T3-suite.log:38`, `gate-logs/T3-suite.log:66`) and a 50-test root run passing. Instance-scoped gate wrappers are unavailable here; all six named frozen logs were read, and their substantive output supports the recorded results. The deferred contribution row supplies no green claim.

Prior-art inspection by affected paths in the supplied target exposes only the synthetic base commit, so merged and closed/rejected history cannot be independently reconstructed locally. The explicit human clearance in `brief.md:39` discharges that decision; it is not presented as a newly reproduced history search. The scope override in `brief.md:44` likewise remains effective. No optional-capability probe masking an eager/load-time cause was introduced.

For the held external check, once the human proceeds, set `PR_URL` to an existing PR with known unresolved threads on the intended host and run the following from the target's `template/` directory. Both helpers only read host state:

```bash
PYTHONPATH=src python3 - <<'READONLY'
import json
import os
from pdca_harness import merge, merged
pr = os.environ["PR_URL"]
print(json.dumps(merged._pr_view(pr, "mergeStateStatus,reviewDecision,latestReviews"), indent=2))
print(json.dumps(merge._review_threads(pr), indent=2))
READONLY
```

Compare thread IDs, paths, current/original lines, first-comment bodies, authors and URLs with the PR, including a later page when available. A `null` thread result means the real query has not been validated. Judge diagnostic usefulness with the documented caveat: BLOCKED plus an open remark does not establish which branch rule actually prevented merging (`template/src/pdca_harness/merge.py:620`). This external check remains pending under the brief's explicit hold.

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — issue #838

I found no correctness bug in the normal paths of this patch, and nothing that needs a human or another build round. There are two minor findings below; neither is tagged NEEDS-HUMAN.

## Findings

- `template/src/pdca_harness/merge.py:67` (also `merge.py:65-66`, and the same claim at `:617-618`) — the docstring says `merge-remarks.json` "never outlives the stop it describes", but the removal at `merge.py:745-746` only runs when `_merge_one` is reached. `merge_wave` is called only for non-final waves (`template/src/pdca_harness/flow.py:3078-3081`). So if a stopped bundle lands in the final wave on a later run, or that run uses `--no-publish`, the old file stays beside a draft PR. This is narrow, and child-3 is the only planned reader, but it should not trust the file on this promise alone. A simple fix is to weaken the sentence to "removed by the next merge attempt", which is what `docs/07-crosscutting.md:935` already says. I traced this from the code and did not run it.
- `template/tests/test_merge_review_remarks.py:278` (also `:409`, `:626`, `:644`, `:689`, `:742`) — simplification: these lines repeat `json.loads((d / REMARKS).read_text(...))` although the `_remarks` helper at `:229-231` does the same read and also checks the file exists. Lines `:409` and `:626` also leave out `encoding="utf-8"`. This is cosmetic and does not change what the tests prove.

## Checked, no finding

- **PR left marked ready:** I went through the code between the failed `gh pr merge` and `_undo_ready`. `_review_threads` catches every error a bad answer can raise (`merge.py:602`), `merged._pr_view` handles a failed read, and the values `_remarks_block` formats and serializes all come from parsed JSON. I found no ordinary path that raises and skips the undo. The tests' `AssertionError` in the `_Gh` stub is not swallowed by that handler, so the `--hostname` check does fail the test.
- **Wait budget:** `waited` is set before the rollup branch and updated by the update and rollup waits. `cfg.merge_wait_secs - waited` cannot go below zero, and `_merge_state` reads once when nothing is left.
- **Changed return value:** `_wait_for_green` has one production caller (`merge.py:880`), and both test files that use it were updated.
- **Atomic write:** reusing `leaves._replace_record` (`merge.py:655`) avoids a second copy of that logic. Importing `leaves` into `merge` creates no import cycle: both modules import cleanly on their own in a fresh interpreter.
- **Archive list:** adding `MERGE_REMARKS` to `DOWNSTREAM_OF_BRIEF` (`state.py:153-156`) also affects `is_resolved` (`state.py:306`) and the split check (`split.py:978`). Both already see a finished bundle as having cycle output, so their behavior does not change.
- **Gate logs:** the T3 log ends with `Ran 2697 tests` and `OK (skipped=2)`. C4 reports red without the fix and green with it.

## Not checked

- `_THREADS_QUERY` (`merge.py:511-524`) and the `gh pr view` fields have only run against stubs. They match the GitHub schema as I know it, but I did not run them. The human has already held the live read-only check, so this is a reminder rather than a new finding.
- Paging stops on a missing or repeated cursor (`merge.py:599`), but not on a host that keeps returning new cursors, so the "never an endless read" wording at `merge.py:559` is slightly too strong. GitHub's real paging ends, so I did not count this as a finding.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] Validation — fitness-to-purpose — Decide whether these diagnostics and records serve merge-mode operators, and discharge the held live read-only GitHub check — real gh/GraphQL was not exercised, so behavioral evidence rests on stubs; brief.md:49; template/tests/test_merge_review_remarks.py:89; template/src/pdca_harness/merge.py:574.
- [x] size backstop — this slice is behaving oversized: 4 round(s) already spent (threshold 3). Recommend answering `iterate-plan` at sign-off and authoring the split in the re-plan (`pdca split`), rather than `iterate-do`: a slice that is too big yields implementation-shaped findings every round, and splitting authors briefs, which is Plan's beat.
- [x] `template/src/pdca_harness/merge.py:582-601` — The message says the PR "is blocked by" the threads or the CHANGES_REQUESTED review whenever `mergeStateStatus` is `BLOCKED` and any exist. GitHub only blocks on unresolved threads when "require conversation resolution" is on, and only blocks on a CHANGES_REQUESTED review when reviews are required. So a PR blocked by a missing approval or a ruleset, which also happens to have an open thread, is reported as a remarks block, and the real cause is dropped (for example, `reviewDecision == "REVIEW_REQUIRED"` never shows up in the message). The brief accepts this guess, but the wording claims a cause the driver cannot confirm. Decide whether that is acceptable, or soften the wording to something like "BLOCKED; unresolved remarks: …" and include `reviewDecision`.

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
- By / date: Eduard Ralph / 2026-10-30

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
