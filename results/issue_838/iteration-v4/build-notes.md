# Build notes — issue 838, iteration 4: merge mode names a block by review remarks

Target: eduralph/pdca-harness @ main, worktree base `3c11556` (= `origin/main`). "main :N" is a
line on that base; "post :N" is the line in the patched worktree. Unless a path is given, lines
are in `template/src/pdca_harness/merge.py`. The brief's own line numbers
(`merge.py:438/453/536/620-631`) come from an older main; on `3c11556` the same code is
`_undo_ready` main :460, `_refuse` main :475, the `merge_requires` gate main :626 and the failed
merge main :715-725.

I started from the iteration-v3 patch, which still applies cleanly. This round adds what the
sign-off asked for (section 1) and fixes the smaller findings from the v3 code review (section 2).
Its other design calls are unchanged (section 3).

## 1. What the sign-off asked for

The concern: any open thread or CHANGES_REQUESTED review on a `BLOCKED` PR is named as the block,
even when something else (a missing approval) is the real one. The human's call: keep the detection
and the wording, and make the real signals visible.

| Asked for | Where |
|---|---|
| Keep the detection and "blocked by N unresolved review thread(s)" | unchanged, post :656 |
| Save `reviewDecision` in the file | read post :628-629, written post :643 |
| Save the failed `gh pr merge` error in the file | taken post :909, passed post :916, written post :644 |
| Show `reviewDecision` in the stop message | post :662-663 |
| Tests, including BLOCKED + REVIEW_REQUIRED + open thread | section 4 |
| Do not read the host's branch rules | not read |
| Live read-only check is not build work | not run this round (section 6) |

The stop for that case, from the production path with `gh` stubbed:

```
GraphQL: Pull request is not mergeable: the base branch policy prohibits the merge. (mergePullRequest)

!!! merge: issue_838 (https://github.com/org/repo/pull/7) was NOT merged — the host blocks its
merge: it is blocked by 1 unresolved review thread(s) — src/a.py:12 by alice. reviewDecision:
REVIEW_REQUIRED. The remarks are written to <root>/results/issue_838/merge-remarks.json. STOP:
later waves are NOT run; resolve at the PR, then re-run (the run resumes idempotently).
```

And the file:

```json
{
  "pr_url": "https://github.com/org/repo/pull/7",
  "mergeStateStatus": "BLOCKED",
  "reviewDecision": "REVIEW_REQUIRED",
  "merge_error": "GraphQL: Pull request is not mergeable: ... (mergePullRequest)",
  "threads": [{"id": "T1", "path": "src/a.py", "line": 12, "outdated": false, "body": "Nit.",
               "author": "alice", "url": "https://github.com/org/repo/pull/7#T1"}],
  "changes_requested_by": []
}
```

Choices made:

- **`merge_error` is the same text the run prints** (`(r.stderr or r.stdout).strip()`, main :717,
  post :909-910), in full and across several lines. The file keeps the host's own words, which may
  name the real block, for whatever reads it later.
- **The stop message does not repeat that error.** It is printed on the line above the stop
  (post :910), so showing it twice adds nothing. The sign-off asked only for `reviewDecision` there.
- **`reviewDecision` in the file is always a string**: what the host reports, or `""` when it
  reports none or something that is not text (post :628-629). The message says `none` for that case.
  One field then has one type, matching a thread's `author`.
- **The generic refusal does not show `reviewDecision`.** Leg (ii) says it stays generic, and the
  concern was the stop that names a cause. `_assert_generic_refusal` pins this.
- **A review that does not count is still named**, as the sign-off said to keep the detection. It now
  shows beside `reviewDecision: APPROVED`, which is what lets a reader see the mismatch.

Docs: the sentence at `docs/07-crosscutting.md:887-893` stops saying "because of" and says why the
decision and error are there. It is still one sentence, as the brief scopes it, though a long one.

## 2. Smaller findings from the v3 code review, also fixed

None of these is in the carry-forward. The human said the live check waits until the change is free
of bugs, and each of these would likely come back as a finding, so I fixed them. Each is small, has a
test, and is easy to drop if the human wants a tighter scope.

- **A merge state that was not checked now says so** (post :621-626, 4 lines). A failed `gh pr view`,
  or an `UNKNOWN` that outlasted the budget, used to fall back to the generic refusal in silence, so a
  reader could not tell "not blocked by remarks" from "could not check". A state the host did report,
  such as `DIRTY`, adds no line. Leg (iii) still holds: `UNKNOWN` to the end is the generic refusal
  and no file.
- **An unknown author is written one way in the file** (post :631-633, :657-659). `changes_requested_by`
  used `"?"` where a thread's `author` used `""`, and a reader could take `"?"` for a login. It is now
  `""`. When only `reviewDecision` says changes were requested, the list is `[]`, since there is no
  login to record. `"?"` stays in the message only.
- **The file is removed before anything can stop an attempt** (post :725-731, moved from after the
  dry-run plan to above the publish-record read, main :543-544). The reviewer asked for a comment fix,
  because the comment claimed "before it decides anything" while two refusals (no recorded PR, a
  `"stacked"` record) came first. Fixing only the comment costs 0 lines of code and leaves a real gap:
  those refusals could leave an old file beside a stop that has nothing to do with it. Moving the
  unlink costs 1 extra line (`if not dry_run:`) and closes the gap, so I moved it. A dry run still
  leaves the file alone.
- **An iterate archives the file with its attempt** (`state.py:53-56`, `state.py:153-156`). Otherwise
  a rebuilt attempt sits beside remarks its new patch may already answer, until its next merge attempt.
  The reviewer put this as "if child-3 will read it", and the brief says child-3 acts on these remarks.
  This is the one change outside `merge.py`. It costs 9 lines, 6 of them comments. `state` cannot
  import from `merge` (main `merge.py:115` imports `state`, so that would be a cycle), so the name
  moved to `state.MERGE_REMARKS`, the way `DEPENDENCY_ADJUDICATION` is defined (main `state.py:51`). As
  far as I can see, a COMPLETE bundle only reaches this path if someone re-signs it as an iterate
  (`driver.py:131-137`), so this is low risk either way.

## 3. Ruled out or left unchanged

- **Softer wording ("BLOCKED; unresolved remarks: …"):** the sign-off says keep the required wording.
- **Reading the host's branch rules:** the sign-off rules it out.
- **Detection only at the failed `gh pr merge`** (post :907-918), under both `merge_requires` values, is
  unchanged. It adds no `gh` call to a merge that succeeds. It rests on `gh pr merge` refusing a
  `BLOCKED` PR when not given `--admin` (`_merge_one` never passes it, main :568). That comes from my
  memory of `gh`, and I did not check it against a live `BLOCKED` PR.
- **A repeated cursor or a failed later page still discards threads already read** (post :547-591).
  It fails safe. Keeping them would need a `(threads, complete)` return, a third state in the file and
  "at least N" wording: about 10 lines. `null` for any failed read stays simpler.
- **No `--hostname` on `gh api graphql`** (post :562). On a host other than `gh`'s default, `resource`
  reads null and the read counts as "could not be read", which fails safe and says so. Passing it costs
  about 3 lines (a URL parse, an import, two arguments). I left it out because `gh pr create --repo
  org/repo` (`publish.py:332`) names no host either, so such a setup already depends on `gh`'s default
  host. That `gh` behaviour is from my memory, not checked.
- **Other docs that describe `merge_wait_secs`** (`template/pdca.toml.jinja:186-188`,
  `template/docs/fork-discipline.md.jinja:64-65`, `config.py:378-385`): none is false, and the brief
  scopes docs to the one sentence.

## 4. Test — `template/tests/test_merge_review_remarks.py` (28 tests)

Imports only modules (`driver, merge, merged, state`, plus the existing `config.Config` /
`LeafConfig`), never a symbol this change adds, so the red leg imports and fails on assertions. The
brief lists `merge, merged, state`; `driver` is added for the real `_archive_iteration`. `gh` and `git`
are stubbed in front of `subprocess.run`, as `template/tests/test_merge.py` does.

New this round:

- `test_review_required_with_an_open_thread_shows_the_real_signals` (:361) — the case the sign-off
  named, under both `merge_requires` values: wording kept, decision shown, decision and error in the
  file, PR back to draft.
- `test_every_remarks_stop_shows_the_review_decision` (:385) — seven subtests, including a review that
  does not count (`APPROVED`), threads unread beside a review, and an empty, null or non-text decision.
- `test_the_file_records_the_merge_error_as_it_was_printed` (:417) — on stderr over several lines, on
  stdout alone, stderr preferred, and nothing at all.
- `test_a_merge_state_that_cannot_be_read_is_reported_as_not_checked` (:450) — four failed reads: says
  so, generic refusal, no file, threads not asked for.
- `test_a_state_the_host_reports_is_not_reported_as_not_checked` (:469) — guards against over-reporting.
- `test_a_decision_with_no_listed_review_names_no_one` (:599).
- `test_a_refusal_on_the_publish_record_removes_the_file_too` (:306).
- `test_an_iterate_archives_the_file_with_its_attempt` (:326) — the real `driver._archive_iteration`.

Changed: `test_an_author_that_is_not_an_object_is_no_author` (:679) now expects `""` in the file and
also has a known reviewer beside the unknown one. `_assert_generic_refusal` also asserts no
`reviewDecision`. `test_unknown_to_the_end_is_not_a_remarks_block` (:494),
`test_changes_requested_without_threads_is_named` (:579),
`test_threads_that_cannot_be_read_are_unknown_not_none` (:613) and
`test_a_file_that_cannot_be_written_still_returns_the_pr_to_draft` (:696) assert the new signals too.

## 5. Runs

All on the final tree. Logs: `results/issue_838/c4-local.log`, `results/issue_838/suite-green.log`.

- **C4**, `engine/scripts/run-verify.sh` → `PDCA-EVIDENCE: C4 PASS — red without the fix, green with
  it`.
  - Green leg: `test_merge` 59 OK, `test_merge_review_remarks` 28 OK, `test_merge_third_remote` 9 OK.
  - Red leg: `test_merge_review_remarks` `FAILED (failures=54)`, 0 errors, 26 of 28 tests red. The two
    that stay green on main do so by design, because main already refuses generically and writes no
    file: `test_blocked_without_remarks_keeps_generic_refusal` and
    `test_a_state_the_host_reports_is_not_reported_as_not_checked`.
  - Red leg, the other two modules: `test_merge` errors=7 and `test_merge_third_remote` errors=2. The
    gate runs them only because this patch edits a line in each, and they raise `ValueError` because
    the reverted `_wait_for_green` returns two values. They say nothing about behaviour. The real red
    is the 54 assertion failures above.
- **New tests against the rejected v3 code** (v3's production files swapped in, `python3 -m unittest`
  under `timeout`, then restored and confirmed with `cmp` against `patch.diff`): `FAILED (failures=27,
  errors=4)`, 12 of 28 tests, and each item is one of the behaviours in sections 1 and 2. The 4 errors
  are `KeyError: 'merge_error'`, because v3's file has no such key.
- **Whole suite**, `engine/scripts/run-suite.sh`: root `Ran 50 tests … OK`, driver `Ran 2675 tests … OK
  (skipped=2)`, `PDCA-EVIDENCE: root suite OK, driver suite OK`. 2675 = v3's 2667 + 8 new tests.
- **Docs**, `engine/scripts/run-docs-check.sh`: `PDCA-EVIDENCE: docs lint clean, site render + link
  audit clean`.
- **C5**, `engine/scripts/run-prod-path.py`: `1 added driver-suite test(s) import the production package
  'pdca_harness'`.
- **Not run by me:** `run-host-ci.sh` (it runs the same two docs checkers as above; it needs the publish
  worktree to be meaningful) and T4 (Check and publish run it).
- **Formatter / commit hooks:** the target has none to run: no `.pre-commit-config.yaml`, no
  `core.hooksPath`, no active git hooks, no ruff/black/flake8/isort in `template/pyproject.toml.jinja`.
  Checked by hand: `git diff --check` clean, new Python lines ≤ 100, new docs lines ≤ 80. The patch
  applies cleanly to `3c11556` in a clean index. Publish adds the DCO sign-off at commit time.

## 6. What stays unproven

Everything above runs against a stubbed `gh`. A real `BLOCKED` PR, a real failed `gh pr merge` and a
real unresolved thread have not gone through this code. The sign-off holds the live read-only check
until the change is bug free and says it is not build work, so I did not run it. `_THREADS_QUERY` and
`_review_threads` are byte-identical to v3, whose builder called them against GitHub once: PR #830 gave
`[]`, and a PR that does not exist gave `None`. That did not exercise a real unresolved thread.

Steps for the human once that check is released, on a sandbox repo with "require conversation
resolution" on (the `sandbox-gh-token` doctor row in `pdca.toml` names `eduralph/pdca-stack-sandbox`):

1. Read-only, on any PR with an open thread: `gh pr view "$PR_URL" --json
   mergeStateStatus,reviewDecision,latestReviews`, then from `template/`, `PR_URL="$PR_URL"
   PYTHONPATH=src python3 -c 'import json,os; from pdca_harness import merge;
   print(json.dumps(merge._review_threads(os.environ["PR_URL"]), indent=2))'`. Compare with the PR.
2. Open a PR with one unresolved line comment and run it as a non-final merge-mode wave. Expect: the
   stop names `path:line` and `reviewDecision`, `merge-remarks.json` holds the decision and the host's
   error, and the PR is a draft again.
3. Resolve the thread and re-run. Expect: it merges and the file is gone.
4. Require an approval, leave a thread open and do not approve. Expect: the same named stop, with
   `reviewDecision: REVIEW_REQUIRED`, and the host's error in the file. Check whether that error names
   the real block. If it does not, the file gives a later reader less than this design assumes.

## 7. Self-refutation

- **(a) Genuine red? Yes.** `run-verify.sh` reverted the production hunks and re-ran: 54 assertion
  failures across 26 of the 28 tests, e.g. `'blocked by 2 unresolved review thread(s)' not found in '…
  did not merge — a conflict, no merge rights …'`. Separately, v3's production code turned 12 tests red
  (31 items), so the new tests catch this round's changes and not merely "no feature at all".
- **(b) Production path? Yes.** Every test calls `merge.merge_wave` → `_merge_one` → the real
  `_wait_for_green`, `_wait_for_update`, `_remarks_block`, `_merge_state`, `merged._pr_view`,
  `_review_threads`, `_refuse`, `_undo_ready`. The archive test also calls the real
  `driver._archive_iteration`. Only `subprocess.run` (the `gh`/`git` boundary), `state.state`,
  `merged.is_merged`, `_sleep` and, in one test, `Path.write_text` are patched.
- **(c) Fixture includes the fault? Yes, within the stub.** The sign-off's case uses the exact state
  the concern describes: `BLOCKED`, `REVIEW_REQUIRED`, one open thread, `gh pr merge` exiting 1 with a
  host-style error. The stub models a draft reading `DRAFT`, so a read after the undo would turn these
  tests red. Not modelled: GitHub computing `mergeStateStatus` live, and whether the host's real error
  text names the real block (section 6, step 4).

## 8. Housekeeping

- **The builder guard blocked one of my commands**, and I did not try to get around what it protects.
  It was a Python script editing files whose text contained `gh pr` in backticks. Nothing ran, and I
  made those edits with the Edit tool. No `gh pr ready` or `gh pr merge` ran outside the stubs.
- **Reading beyond the brief:** the `iteration-v3/` artifacts the carry-forward points at, the cited
  peers, `state.py`, `driver._archive_iteration` and `split.py:978` (the users of the archive list),
  and `engine/scripts/` to find the project's runners. One ad-hoc run printed the sample stop in section
  1, through the test module's stub, inside `tempfile.TemporaryDirectory()`.
- **Files I left behind on purpose:** the worktree has the new test file registered intent-to-add
  (`git add -N`) so `git diff` includes it in `patch.diff`, and `.cache/issue838-*` (throwaway git
  indexes and line lists from the checks above, in an ignored directory). The bundle's
  `test_merge_review_remarks.py`, `c4-local.log` and `suite-green.log` are refreshed from this round.
  Nothing committed, nothing pushed, no PR.
- **The `rounds` size signal may fire at Check:** this is the fourth attempt and `pdca.toml` sets
  `rounds = 3`. Measured against v3, this round's production change is +61/−35 in `merge.py`, about
  half of it docstrings and comments, and +9 in `state.py`. The whole patch is 63 KB, under the 125 KB
  limit.
