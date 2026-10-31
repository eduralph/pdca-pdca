## Summary
**User impact:** In merge mode, a wave's PR can have every check green and still not merge because a reviewer left an unresolved comment or asked for changes. Today the run just stops with the generic "did not merge — a conflict, no merge rights …" message and leaves nothing in the bundle. The operator has to open the PR on GitHub to find out that a review remark is the real block, and nothing in the bundle records which remarks they were.

This PR makes the driver name that block: the stop lists each unresolved review thread with its file and line (and any reviewer who requested changes), shows the PR's review decision, and writes the remarks to `merge-remarks.json` in the bundle. The PR is returned to draft as before.

Reported in [#838](https://github.com/eduralph/pdca-harness/issues/838).

## What to look at
The change is in the failure branch of the merge step: when `gh pr merge` fails, the driver now asks GitHub for the PR's merge state and, if it is `BLOCKED`, for its unresolved review threads and latest reviews. Everything else about the merge step is unchanged. Three things are worth a look:

- **The stop message and the file.** The wording is `blocked by N unresolved review thread(s) — path:line by author; …` plus `a CHANGES_REQUESTED review by <login>`, followed by `reviewDecision: …` and where the file was written. The file holds one object per thread (`id`, `path`, `line`, `body`, `author`, `url`), the reviewers who requested changes, the `reviewDecision`, and the host's own merge error.
- **What it does not claim.** `BLOCKED` does not say which branch rule blocks the merge, and the driver does not read the host's rules. So a PR that is short of an approval and also has an open thread is named as blocked by the thread. The review decision and the merge error are shown and recorded so a reader can check that. A `BLOCKED` PR with no open thread and no changes-requested review keeps the generic refusal and writes no file. Threads that could not be read are `null` in the file, never an empty list.
- **Nothing stale, nothing torn.** Each merge attempt deletes `merge-remarks.json` before it starts, an iterate archives it with its attempt, and the file is written through a temp file so a failed write leaves nothing behind.

To try it offline: run `PYTHONPATH=src python -m unittest tests.test_merge_review_remarks` from `template/`. Every test stubs `gh` in front of `subprocess.run` (as `tests/test_merge.py` does), including the GraphQL call, so no network is needed. To try it live: on a sandbox repo with "require conversation resolution" on, open a PR with one unresolved line comment and run it as a non-final merge-mode wave; the stop should name the `path:line`, the file should appear in the bundle, and the PR should be a draft again. Resolve the thread and re-run: it merges and the file is gone.

## Root cause
`_merge_one` (`template/src/pdca_harness/merge.py:535`) never reads the PR's `mergeStateStatus` or its review threads. A green rollup says nothing about review-based branch rules, so when `gh pr merge` fails on such a PR (`merge.py:716`) the only outcome is the generic refusal at `merge.py:718`, with nothing written. Under `merge_requires = "required"` the rollup gate is skipped altogether (`merge.py:626`), so the failed merge is the only place the block can show at all.

## Fix
All in `template/src/pdca_harness/merge.py` unless noted.

- **`_remarks_block(d, pr_url, wait_secs, merge_error)`** (new) is called from the `gh pr merge` failure branch. It reads `mergeStateStatus,reviewDecision,latestReviews` through `merged._pr_view` (`merged.py:187`), and when the state is `BLOCKED` reads the unresolved threads. If there are threads or a changes-requested review, it writes `merge-remarks.json` and returns the reason; the caller refuses through `_refuse` (`merge.py:475`), which undoes the ready-mark through `_undo_ready` (`merge.py:460`). An empty reason keeps the generic refusal. A merge state that could not be read, or stayed `UNKNOWN`, is reported on stderr as "not checked", so that cannot be mistaken for "no remarks".
- **`_merge_state`** (new) polls `UNKNOWN` through the patchable `_sleep`, bounded by what the update and rollup waits left of `merge_wait_secs`. `_wait_for_green` (`merge.py:226`) now also returns how much of the budget it used, so the PR is never marked ready longer than that one bound on these waits. Its two callers in tests are updated for the third return value.
- **`_review_threads`** (new) runs `gh api graphql` with `resource(url:)` on the PR URL, follows every page of `reviewThreads` (GitHub serves 100 a page; an unresolved thread can sit behind a full page of resolved ones), and passes `--hostname` with the host parsed from the PR URL, because `gh api` asks `gh`'s default host otherwise. It returns `None` on any failure, including a repeated page cursor, an unparseable URL, or an answer of the wrong shape; it never raises, because it runs while the PR is marked ready. An outdated thread has `line: null`, so its `originalLine` is reported.
- **The file is written through `leaves._replace_record`** (`leaves.py:1168`): a sibling temp file then `os.replace`, with the temp removed on failure. A write that fails is reported in the stop message rather than raised, so the PR still goes back to draft.
- **`_merge_one` removes `merge-remarks.json`** at the start of every non-dry-run attempt. `state.MERGE_REMARKS` names the file, and it is added to `state.DOWNSTREAM_OF_BRIEF` (`state.py:116`) so an iterate archives it with its attempt.
- **Docs:** the merge-mode bullet of `docs/07-crosscutting.md` (after line 927) gains one sentence on the new stop and file.

## Verification
- **Claim:** With `wave_mode = "merge"`, a PR whose rollup is green, whose `mergeStateStatus` is `BLOCKED`, and which has N unresolved threads makes `merge_wave` return non-zero with "blocked by N unresolved review thread(s)" and each thread's `path:line` on stderr, writes `merge-remarks.json` with one object per thread, and returns the PR to draft.
  **Checked:** `merge.py:716-718` on `main` (`333990e`) — the failure branch prints only the generic refusal and `_merge_one` (`merge.py:535` onward) reads neither `mergeStateStatus` nor review threads.
  **Test:** `template/tests/test_merge_review_remarks.py::test_blocked_by_threads_is_named_and_written`.
- **Claim:** Detection runs under `merge_requires = "required"` too, where the rollup gate is skipped.
  **Checked:** `merge.py:626` — the gate is conditional on `merge_requires != "required"`; the new check sits in the `gh pr merge` failure branch, which both settings reach.
  **Test:** `test_required_mode_detects_it_at_the_failed_merge`.
- **Claim:** `BLOCKED` with no open thread and no changes-requested review keeps the generic refusal, never says "0 unresolved", and writes no file.
  **Test:** `test_blocked_without_remarks_keeps_generic_refusal`.
- **Claim:** `UNKNOWN` right after `gh pr ready` is polled on what the update and rollup waits left of `merge_wait_secs`, then treated as not blocked by remarks; the bound is never overrun.
  **Checked:** `merge.py:226` (`_wait_for_green`) and its call at `merge.py:673` — the budget was previously not returned to the caller.
  **Tests:** `test_unknown_is_polled_then_read`, `test_unknown_to_the_end_is_not_a_remarks_block`, `test_the_poll_gets_only_what_the_rollup_wait_left`, `test_an_update_wait_is_charged_to_the_same_budget`, `test_with_no_budget_left_the_state_is_read_once`.
- **Claim:** Every page of threads is read; a repeated cursor ends the read as unknown.
  **Tests:** `test_threads_past_the_first_page_are_read`, `test_a_page_cursor_that_repeats_ends_the_read`.
- **Claim:** The GraphQL query goes to the host in the PR URL (lowercase, no port); a URL with no host is not queried and never raises.
  **Tests:** `test_threads_are_read_on_the_host_in_the_pr_url`, `test_a_pr_url_with_no_host_to_ask_is_not_read`. The `_Gh` stub raises `AssertionError` on any GraphQL request that does not name the expected host, so every test that reaches the query also checks the flag. Also checked against the real `gh` 2.103.3 binary offline (hosts under `.invalid`, dummy token): `gh pr view` on `https://GHE.invalid:8443/…` asks `ghe.invalid`, and the new code asks the same host, where the old code asked `gh`'s default.
- **Claim:** An outdated thread reports `originalLine`; a thread on a whole file is reported by path alone.
  **Test:** `test_outdated_thread_reports_original_line`.
- **Claim:** A CHANGES_REQUESTED review with no threads is named as such, with the reviewer's login.
  **Test:** `test_changes_requested_without_threads_is_named`.
- **Claim:** `reviewDecision` and the host's merge error are shown in the stop and recorded in the file, including a `REVIEW_REQUIRED` PR with an open thread.
  **Tests:** `test_review_required_with_an_open_thread_shows_the_real_signals`, `test_every_remarks_stop_shows_the_review_decision`, `test_the_file_records_the_merge_error_as_it_was_printed`.
- **Claim:** Threads that could not be read beside a changes-requested review are `null` in the file and the stop says so.
  **Test:** `test_threads_that_cannot_be_read_are_unknown_not_none`.
- **Claim:** A write that fails part-way leaves no file (under any name) and the PR still goes back to draft.
  **Checked:** `leaves.py:1168` — `_replace_record` writes a sibling temp, `os.replace`s it, and removes the temp on failure.
  **Test:** `test_a_write_that_fails_leaves_no_file_and_still_returns_the_pr_to_draft` — its stand-in for `Path.write_text` really writes half the file to disk and then raises `ENOSPC`; the test asserts the half was on disk and that the bundle listing is unchanged afterwards. A second subtest fails `os.replace`. Also run once under a real `RLIMIT_FSIZE` of 64 bytes: nothing left in the bundle, stop says "could not be written (File too large)", PR undone.
- **Claim:** A later attempt removes a stale file whatever it then ends on; a dry run leaves it alone; an iterate archives it with its attempt.
  **Checked:** `state.py:116` (`DOWNSTREAM_OF_BRIEF`).
  **Tests:** `test_a_later_attempt_removes_the_file_it_no_longer_describes`, `test_a_refusal_on_the_publish_record_removes_the_file_too`, `test_a_dry_run_leaves_the_file_alone`, `test_an_iterate_archives_the_file_with_its_attempt`.
- **Red/green:** with the production hunks reverted, `test_merge_review_remarks` fails with 63 assertion failures (e.g. `'blocked by 2 unresolved review thread(s)' not found in '… did not merge — a conflict, no merge rights …'`); with the patch, 30 tests pass. Full offline suite: root 50 OK, driver 2697 OK (2 skipped). Docs lint, site render and link audit clean.
- **Not covered:** a real `BLOCKED` PR on GitHub, a real failed `gh pr merge`, and `--hostname` on a host that answers have not gone through this code; every run above uses a stubbed `gh` or a real `gh` that could not reach any host. A live read-only check on a sandbox repo is planned before this leaves draft. GitHub Enterprise itself is not exercised.

Fixes #838
