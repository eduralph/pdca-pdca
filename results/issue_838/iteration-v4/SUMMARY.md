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

Review merge-mode diagnostics for blocked review remarks: report thread locations, preserve remarks and host signals in the bundle, and restore the PR to draft.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The offline acceptance criteria cover both merge policies, empty remarks, UNKNOWN polling, outdated lines, and requested changes; the latest carry-forward explicitly resolves the attribution scope (brief.md:4; brief.md:32). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing production changes reproduced the generic refusal instead of the required thread diagnosis: 28 tests ran with 54 assertion failures and no import errors (template/tests/test_merge_review_remarks.py:234; reviewer-red.log:221; reviewer-red.log:546). |
| C3 Change | PASS | Diagnosis occurs at the failed-merge boundary under both policies, preserving merge refusal and the existing draft rollback rather than changing merge eligibility (template/src/pdca_harness/merge.py:908; template/src/pdca_harness/merge.py:918; template/src/pdca_harness/merge.py:499). |
| C4 Verification (red→green) | PASS | After stash restoration, all 96 selected tests passed; the complete patch also passes reverse-application and whitespace checks, and matches the disposable target (reviewer-green.log:3; template/tests/test_merge_review_remarks.py:230; gate-logs/C4-verify.log:723). |
| C5 Causal adequacy | PASS | Production-path tests cover all requested legs and previous defects: later thread pages, stale-artifact removal, shared wait limits, unreadable threads, and preserved host signals; no capability-probe symptom guard was introduced (template/tests/test_merge_review_remarks.py:251; template/tests/test_merge_review_remarks.py:283; template/tests/test_merge_review_remarks.py:511; template/tests/test_merge_review_remarks.py:613; template/tests/test_merge_review_remarks.py:361). |
| T1 Structure | PASS | The diagnostic reuses the PR reader and refusal lifecycle, and archives its per-attempt artifact through the existing state list, keeping ownership and retry behavior coherent (template/src/pdca_harness/merge.py:533; template/src/pdca_harness/merge.py:731; template/src/pdca_harness/state.py:156). |
| T2 Shape | PASS | Independent docs lint, 22-page rendering/link audit, six checker tests, 458 relative-link checks, and the 12-ADR audit passed; the documented stop matches the accepted behavior (docs/07-crosscutting.md:887; reviewer-docs-render.log:3; reviewer-doc-checkers.log:9; reviewer-doc-links.log:1; reviewer-adr.log:1). |
| T3 Runtime | PASS | Independent driver discovery passed 2,675 tests with two skips; frozen evidence also records 50 passing root render/update tests, whose local rerun lacks importable copier (reviewer-suite.log:1819; gate-logs/T3-suite.log:80; reviewer-root.log:6). |
| T4 Contribution | N/A | Contribution artifacts are intentionally absent during Check; the deferred gate owes its substantive audit at publish (gate-logs/T4-contribution.log:10). |
| T5 Judgment | PASS | The human explicitly chose inferred blocker wording with visible counter-signals and cleared prior art; the new REVIEW_REQUIRED regression satisfies that decision without expanding into branch-rule discovery (brief.md:32; brief.md:39; template/tests/test_merge_review_remarks.py:361; template/src/pdca_harness/merge.py:643). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Complete the held real-GitHub read-only check and judge operational usefulness — real API payloads and host behavior were not exercised, so compatibility evidence rests on stub responses; BLOCKED plus remarks remains an inference about the actual rule blocking the merge (brief.md:39; template/src/pdca_harness/merge.py:606; template/src/pdca_harness/merge.py:662). |

Independent verification used `git stash push` for the two production files while retaining the tests, ran the new suite against the base, restored the stash, and ran the three affected test modules plus full driver discovery. The target was restored to the supplied patch; all source citations above resolve there. The tests import the target production package and call `merge.merge_wave`, corroborating `gate-logs/C5-prod-path.log:10`.

The local root-suite runner exited 77: 45 tests ran, three skipped, and no copier-dependent case executed because this interpreter cannot import copier (`reviewer-root.log:3`, `reviewer-root.log:6`). This is a reviewer-host limitation, not a patch failure. The frozen root-suite log explicitly shows render/update cases executing and the 50-test suite passing (`gate-logs/T3-suite.log:68`, `gate-logs/T3-suite.log:80`). The instance-scoped gate wrappers were adjudicated using their captured logs; documentation checks were independently run through the target's own tools.

Affected-file history inspection ran for all six changed paths, recorded in `reviewer-prior-art.log:4`. The target contains only one synthesized base commit, so it cannot independently reconstruct merged history or closed/rejected work. The explicit human clearance in `brief.md:39` is retained.

For the held live check, use an authenticated `gh` in a trusted checkout containing this patch, with a PR that has known unresolved threads. From the repository root, run:

```bash
export PR_URL='https://github.com/OWNER/REPO/pull/NUMBER'
PYTHONPATH=template/src python3 - <<'PY'
import json
import os
from pdca_harness import merge, merged
url = os.environ['PR_URL']
print('state:', json.dumps(merged._pr_view(
    url, 'mergeStateStatus,reviewDecision,latestReviews'), indent=2))
print('threads:', json.dumps(merge._review_threads(url), indent=2))
PY
```

These calls only read the PR. Confirm non-null responses, compare thread IDs/counts, authors, bodies, URLs and locations with GitHub, and include an outdated thread to check original-line reporting. Where available, exercise a PR with more than 100 total threads to check real cursor pagination. The offline REVIEW_REQUIRED-plus-open-thread case already passed; the human must assess the diagnostic's usefulness when the host's actual blocking rule differs from the named remarks.

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Code review (advisory): merge-mode-detect-review-remark-block

Two correctness findings, both small and both limited to uncommon conditions. I found no reuse or efficiency problem that needs a change beyond the helper named in the first finding. I reviewed by reading the code, the tests and the frozen gate logs; I ran nothing, and nothing was checked against real GitHub (the brief holds that live check for later).

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/merge.py:640`: a failed write can leave a torn `merge-remarks.json` behind a message saying it could not be written. `Path.write_text` truncates the file first, so running out of disk or being killed part-way leaves an empty or partial file. The `except OSError` reports the failure but leaves that file in the bundle, and it stays until the next merge attempt. Child-3 is meant to read this file, and a torn one is neither "no remarks" nor valid JSON. Fix: write a sibling temp file, then `os.replace`, and remove the temp on failure, as `leaves._replace_record` does (`template/src/pdca_harness/leaves.py:1168`) and `autoiterate._write_ledger` does (`template/src/pdca_harness/autoiterate.py:292`). `template/tests/test_merge_review_remarks.py:700` cannot catch this, because it mocks `Path.write_text` to fail before any file exists; its `assertFalse(exists)` at :710 passes regardless. Add a test where the write creates a partial file and then raises.
- NEEDS-HUMAN [impl] — `template/src/pdca_harness/merge.py:562`: `gh api graphql` is the one `gh` call in this flow that does not follow the PR URL's host. `gh pr view <url>`, `gh pr merge <url>` and the others take the host from the URL, while `gh api` defaults to `github.com` (or `GH_HOST`) unless `--hostname` is passed. On a GitHub Enterprise PR, the query would go to the wrong host and the read would fail or resolve to nothing. `_review_threads` then returns None, so a PR blocked by threads gets the generic refusal and no file, plus a "could not be read" line. The failure is safe (the PR still returns to draft) but the feature silently does not work there. I found no docs saying whether Enterprise hosts are supported, so this may never occur in practice. Fix if they are: pass `--hostname` with the host parsed from `pr_url`, and assert it in the `_Gh` stub (`template/tests/test_merge_review_remarks.py:120`).

Checked and found clean:

- **Thread paging:** it stops on a missing or repeated cursor, and any failed page returns None rather than a partial list.
- **Shared wait budget:** `_wait_for_green` returns its used time on every path, and a zero or negative remainder still reads the merge state once without sleeping.
- **Return to draft:** no path found between the failed merge and `_undo_ready` raises on bad `gh` output or a failed write.
- **Changed return shape:** the one production caller of `_wait_for_green`, the `test_merge.py` helper and the `test_merge_third_remote.py` stub were all updated.
- **Archive list:** adding the file to `DOWNSTREAM_OF_BRIEF` only affects bundles that already hold a `patch.diff`, so it does not change how they are classified (`template/src/pdca_harness/state.py:306`).
- **Gate evidence:** C4 is red for the right reason. Most of the new tests fail on their assertions in the red leg, with no import error, and all are green with the fix (`gate-logs/C4-verify.log`).

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] Validation — fitness-to-purpose — Complete the held real-GitHub read-only check and judge operational usefulness — real API payloads and host behavior were not exercised, so compatibility evidence rests on stub responses; BLOCKED plus remarks remains an inference about the actual rule blocking the merge (brief.md:39; template/src/pdca_harness/merge.py:606; template/src/pdca_harness/merge.py:662).
- [ ] `template/src/pdca_harness/merge.py:640`: a failed write can leave a torn `merge-remarks.json` behind a message saying it could not be written. `Path.write_text` truncates the file first, so running out of disk or being killed part-way leaves an empty or partial file. The `except OSError` reports the failure but leaves that file in the bundle, and it stays until the next merge attempt. Child-3 is meant to read this file, and a torn one is neither "no remarks" nor valid JSON. Fix: write a sibling temp file, then `os.replace`, and remove the temp on failure, as `leaves._replace_record` does (`template/src/pdca_harness/leaves.py:1168`) and `autoiterate._write_ledger` does (`template/src/pdca_harness/autoiterate.py:292`). `template/tests/test_merge_review_remarks.py:700` cannot catch this, because it mocks `Path.write_text` to fail before any file exists; its `assertFalse(exists)` at :710 passes regardless. Add a test where the write creates a partial file and then raises.
- [ ] `template/src/pdca_harness/merge.py:562`: `gh api graphql` is the one `gh` call in this flow that does not follow the PR URL's host. `gh pr view <url>`, `gh pr merge <url>` and the others take the host from the URL, while `gh api` defaults to `github.com` (or `GH_HOST`) unless `--hostname` is passed. On a GitHub Enterprise PR, the query would go to the wrong host and the read would fail or resolve to nothing. `_review_threads` then returns None, so a PR blocked by threads gets the generic refusal and no file, plus a "could not be read" line. The failure is safe (the PR still returns to draft) but the feature silently does not work there. I found no docs saying whether Enterprise hosts are supported, so this may never occur in practice. Fix if they are: pass `--hostname` with the host parsed from `pr_url`, and assert it in the `_Gh` stub (`template/tests/test_merge_review_remarks.py:120`).
- [x] size backstop — this slice is behaving oversized: 3 round(s) already spent (threshold 3). Recommend answering `iterate-plan` at sign-off and authoring the split in the re-plan (`pdca split`), rather than `iterate-do`: a slice that is too big yields implementation-shaped findings every round, and splitting authors briefs, which is Plan's beat.
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
- Iteration delta (if iterating): Human overrode the size backstop: this is one outcome, so do not split it. Keep the current approach and wording, and fix these two findings: - Half-written file (`template/src/pdca_harness/merge.py:640`): `Path.write_text` can leave a partial `merge-remarks.json` behind a message saying it could not be written. Write a sibling temp file, then `os.replace`, and remove the temp on failure, as `leaves._replace_record` and `autoiterate._write_ledger` do. Add a test where the write creates a partial file and then raises; the current test at `template/tests/test_merge_review_remarks.py:700` cannot catch this. - Wrong host (`template/src/pdca_harness/merge.py:562`): `gh api graphql` does not follow the PR URL's host. Pass `--hostname` with the host parsed from `pr_url`, and assert it in the `_Gh` stub (`template/tests/test_merge_review_remarks.py:120`). The live read-only GitHub check stays held for the rebuilt change; it is not build work.
- By / date: Eduard Ralph / 2026-10-30

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
