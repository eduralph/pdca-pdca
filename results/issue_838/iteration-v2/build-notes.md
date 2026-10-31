# Build notes — issue 838, iteration 2: merge mode names a block by review remarks

Target: eduralph/pdca-harness @ main, worktree base `3c11556` (= `origin/main`). "main :N"
is a line on that base; "post :N" is the line in the patched worktree. The brief's own line
numbers (`merge.py:438/453/536/620-631`) come from an older main; on `3c11556` the same code
is `_undo_ready` main :460, `_refuse` main :475, the `merge_requires` gate main :626 and the
failed-merge branch main :715-725.

## What the carry-forward asked for, and what I did

The previous attempt (iteration-v1) was sent back for two implementation findings. I
started from its patch (same base, applied cleanly) and changed only what those findings
and one small related defect needed. Its design calls are kept as they were (see "Kept
from v1" below).

### 1. Read every page of review threads

v1 asked for `reviewThreads(first: 100)` once. A PR whose first 100 threads were resolved
and whose 101st was not got the generic refusal and no file.

- `template/src/pdca_harness/merge.py` post :495-512 — `_THREADS_QUERY` now declares
  `$cursor: String`, asks `reviewThreads(first: 100, after: $cursor)` and
  `pageInfo { hasNextPage endCursor }`.
- post :535-580 — `_review_threads` loops: first request with no cursor (GraphQL `after:
  null` = first page), each next one with `-f cursor=<endCursor of the page before>`,
  until `hasNextPage` is false. Unresolved threads from every page are collected in
  order. Any failed or unreadable page makes the whole read `None` (v1's contract for a
  failed query), so a partial list is never reported as the full count.
- post :577-580 — loop guard: a page that claims a next page but gives no cursor, or a
  cursor already followed, returns `None`. Without it, a host repeating a cursor would
  hang the driver. `None` falls back to the generic refusal (still a refusal, ready-mark
  still undone), so the guard can only cost the precise message, never cause a merge.

Live check against the real API (read-only, `gh` is logged in as eduralph): I called the
production `merge._review_threads` on `https://github.com/eduralph/pdca-harness/pull/830`
(3 review threads, all resolved). With the shipped page size it made 1 request and
returned `[]`. With only `first: 100` replaced by `first: 1` in a throwaway process, it made
3 requests: no cursor, then `cursor=Y3Vy…q7A==`, then `cursor=Y3Vy…lBg==`, and stopped
when `hasNextPage` was false. So the query is valid against GitHub's real schema and the
cursor variable works through `gh api graphql -f`. The stubbed tests cannot show that.

### 2. Never leave a stale `merge-remarks.json`

v1 wrote the file and never removed it.

- post :713-717 — `_merge_one` removes `d / REMARKS_FILE` (`unlink(missing_ok=True)`) at
  the start of every real attempt: after the dry-run return (main :569-571) and before
  the `is_merged` skip (main :573). Only `_remarks_block` writes it again, for this
  attempt's own stop. Result: the file exists if and only if the bundle's latest merge
  attempt stopped on review remarks.
- Where I put it versus what the finding suggested. The finding offered "at the start of
  `_remarks_block`, or when `_merge_one` merges successfully". Counted:
  - start of `_remarks_block`: +1 line. Covers a later generic refusal at `gh pr merge`
    only.
  - after a successful merge (after main :725): +1 line. Covers a clean merge only.
  - both: +2 lines. Still leaves a stale file when the later attempt stops before
    `gh pr merge` (ready failing main :611, rollup red/pending main :675-692, update or
    base/head refusals main :634-711, target base main :589-594, malformed
    `expected_checks` main :579-583), and when the PR was merged by hand meanwhile
    (`is_merged` skip, main :573).
  - mine: +1 line (plus a 4-line comment), one place, covers all of those.
  The trade-off: an attempt that stops earlier for another reason (say a pending
  rollup) removes the record of remarks an earlier attempt saw, though they may still be
  open. I accept that: the file would otherwise describe a stop the latest run did not
  make, the threads stay visible on the PR, and the next attempt that reaches
  `gh pr merge` reads them again. A dry run (main :569) attempts nothing and leaves the
  file alone; the test pins that.
- Docs: `docs/07-crosscutting.md` post :887-891 (after main :885-886) — the v1 sentence
  gains "(the bundle's next merge attempt removes it first)", still one sentence.
- Module docstring `merge.py` post :52-60 — "every page" and the clearing rule.
- `_remarks_block` docstring post :583-591 — says who removes the file.

### 3. Small related fix in this bundle's own new code: threads with no line

A review thread on a whole file has `line: null` and `originalLine: null` and is not
outdated. v1 printed it as `src/x.py:None (outdated)`. Now:

- post :570 — `outdated` comes from `isOutdated` only (v1 used `line is None or
  isOutdated`, which marked every file-level thread outdated). An outdated line thread
  (leg iv) still has `isOutdated: true` and still reports `originalLine`.
- post :616-618 — the message prints `path` alone when there is no line. The JSON keeps
  `"line": null` for such a thread.

Not asked for by the carry-forward; 2 changed lines plus 3 test assertions. Easy to drop
if the human prefers v1's exact scope.

## Kept from v1 (judgment calls, unchanged, not build work)

- Detection only at the failed `gh pr merge` (`_merge_one` post :864-870, main :715-725),
  under both `merge_requires` values. No extra `gh` call on the success path.
- The `UNKNOWN` poll (`_merge_state` post :517-532) is bounded by `merge_wait_secs`, the
  knob the #462 rollup wait uses (`_wait_for_green`, main :226), through the same
  patchable `_sleep`. It is its own bounded wait after the rollup wait, not the
  leftover of it.
- `merge-remarks.json` is an object: `pr_url`, `mergeStateStatus`, `threads` (one object
  per thread: id, path, line, outdated, body, author, url), `changes_requested_by`.
- Peer callsites used as the brief cites: `merged._pr_view` (`merged.py:187`) for the
  `gh pr view` read, `merge._refuse` (main :475) for the stop, which calls
  `merge._undo_ready` (main :460).

Known limits, not changed:
- If the thread read fails but a CHANGES_REQUESTED review exists, the review is named
  and the file records `"threads": []` (v1 behaviour). With paging, a failed later page
  is also "read failed".
- `gh api graphql` asks the default host (github.com or `GH_HOST`). A PR on another host
  reads as `resource: null`, which is "read failed": generic refusal, nothing merged.
- `latestReviews` comes from `gh pr view` (gh's own page of it); `reviewDecision` is the
  fallback when no single CHANGES_REQUESTED author is found.

## Test — `template/tests/test_merge_review_remarks.py` (11 tests)

Imports only modules (`merge, merged, state`, plus `config` for `Config`/`LeafConfig`),
never a symbol this change adds, so the red leg imports and fails on assertions. Stubs
`subprocess.run` as `template/tests/test_merge.py` does, including `gh api graphql`; the
stub serves `reviewThreads` in pages and records the cursor of every request.

New in this iteration:
- `test_threads_past_the_first_page_are_read` (:192) — the reviewer's case: page 1 is 100
  resolved threads, page 2 has one unresolved among 99 resolved, page 3 has one more.
  Asserts requests with cursors `[None, "c1", "c2"]`, "blocked by 2 unresolved review
  thread(s)", both path:lines, the file holds exactly those 2, PR undone.
- `test_a_page_cursor_that_repeats_ends_the_read` (:212) — host repeats cursor `c1`:
  exactly 2 requests, generic refusal, no file. The stub fails after 10 requests, so a
  missing guard makes this fail instead of hanging the suite.
- `test_a_later_attempt_removes_the_file_it_no_longer_describes` (:224) — per subtest a
  real first attempt writes the file (asserted), then a second attempt on the same
  bundle: threads resolved and the merge succeeds (rc 0); threads resolved but BLOCKED by
  REVIEW_REQUIRED (generic refusal); rollup failing (refused before the merge); merged by
  hand meanwhile (`is_merged`). Each must leave no file.
- `test_a_dry_run_leaves_the_file_alone` (:247) — no `gh` call, file unchanged.
- `test_outdated_thread_reports_original_line` (:310) gained the file-level thread case.

Kept from v1: main case (:171), leg (i) `required` (:259), leg (ii) (:272), leg (iii) both
ways (:285, :294), leg (iv) (:310), leg (v) (:326).

## Runs

- C4 gate, the project's runner: `PDCA_BUNDLE=results/issue_838
  PDCA_WORKTREE=<worktree> engine/scripts/run-verify.sh` → `PDCA-EVIDENCE: C4 PASS — red
  without the fix, green with it`. Green leg: `Ran 11 tests … OK`. Red leg (production
  hunks reverted): `Ran 11 tests … FAILED (failures=13)`, no errors, no import failure.
  The one test green on main is leg (ii), by design: main already refuses generically
  and writes no file; it guards against the fix over-reaching. Log:
  `results/issue_838/c4-local.log`.
- Against the rejected v1 code (v1 patch applied, new test file): 7 failures, exactly
  the new cases — 4 stale-file subtests (`True is not false`), paging (`[None] != [None,
  'c1', 'c2']`), repeated cursor (`[None] != [None, 'c1']`), file-level thread
  (`src/whole.py:None (outdated)`). So the new tests bind the two findings, not just
  "no feature at all".
- Whole suite, `engine/scripts/run-suite.sh`: root suite `Ran 50 tests … OK`, driver
  suite `Ran 2658 tests … OK (skipped=2)`, `PDCA-EVIDENCE: root suite OK, driver suite
  OK` (log: `results/issue_838/suite-green.log`). 2658 = v1's 2654 − v1's 7 tests + 11.
  No existing test needed an edit: the removal at the start of an attempt is a no-op for
  a bundle without the file, and the new reads still run only after a failed merge.
- Docs, `engine/scripts/run-docs-check.sh`: `PDCA-EVIDENCE: docs lint clean, site render
  + link audit clean`.
- Formatter / commit hooks: the target configures none (no ruff/black/flake8 in its
  pyproject, no `.pre-commit-config.yaml`; CI is DCO, docs checks, render check). Python
  lines kept ≤ 100 like the file, docs lines ≤ 80 like the section. Publish adds the DCO
  sign-off at commit time.

## Self-refutation

- **(a) Genuine red?** Yes. `run-verify.sh` reverted the production hunks and re-ran:
  13 assertion failures in 10 of 11 tests, e.g. `'blocked by 2 unresolved review
  thread(s)' not found in '… did not merge — a conflict, no merge rights …'`, and for the
  dry-run test `False is not true` (main writes no file in the first attempt). Separately,
  going back to v1's code (this iteration's production changes undone) turns red the
  paging test, the repeated-cursor test, all 4 subtests of the rerun test, and the
  file-level case of the outdated test. The dry-run test passes on v1, which never
  removed the file; it guards against moving the removal above the dry-run return.
- **(b) Production path?** Yes. Every test calls `merge.merge_wave` → `_merge_one` → the
  real `_remarks_block` / `_merge_state` / `merged._pr_view` / `_review_threads` /
  `_refuse` / `_undo_ready`, and the real unlink at the start of the attempt. Only
  `subprocess.run` (the `gh`/`git` boundary), `state.state`, `merged.is_merged` and
  `_sleep` are patched. The live run above called the production `_review_threads`
  against GitHub itself.
- **(c) Fixture includes the fault?** Yes. The paging stub puts the unresolved threads
  behind a full page of 100 resolved ones, the reviewer's exact case, and only serves a
  later page to a request carrying the right cursor. The rerun test creates the stale file
  through a real first attempt rather than writing it by hand, then resolves the threads.
  Not modelled offline: GitHub computing `mergeStateStatus` live, and a PR with more than
  100 real threads (the live check forced paging with a page size of 1 instead).

## Housekeeping

- By mistake I wrote one log outside the harness roots: `/tmp/c4-838-v2.log` (an earlier
  C4 run's output). Later logs went into the bundle. I did not delete it (cleanup is the
  harness's).
- The worktree has the new test file registered intent-to-add (`git add -N`) so
  `git diff` includes it in `patch.diff`. Nothing committed, nothing pushed, no PR.
