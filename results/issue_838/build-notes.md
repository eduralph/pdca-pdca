# Build notes — issue 838, iteration 5: merge mode names a block by review remarks

Target: eduralph/pdca-harness @ main, worktree base `333990e` (= `origin/main`). "main :N" is a
line on that base; "post :N" is the line in the patched worktree; "v4 :N" is the line in the
rejected attempt. Unless a path is given, lines are in `template/src/pdca_harness/merge.py`. The
brief's own line numbers (`merge.py:438/453`) come from an older main; on `333990e` the same code is
`_undo_ready` main :460, `_refuse` main :475 and `_merge_one` main :535.

I started from the v4 patch. It still applies cleanly, and `merge.py`, `leaves.py` and `state.py` are
identical between v4's base `3c11556` and this one (`git diff --quiet`). The sign-off said to keep the
approach and wording and fix two findings, so those two fixes are the only production changes this
round: 76 changed lines in `merge.py` compared with v4, most of them from re-indenting
`_review_threads` and re-wrapping docstrings. The hunks for `state.py`, `test_merge.py` and
`test_merge_third_remote.py` are byte-identical to v4's. The docs hunk has the same text; it only sits
lower because the file grew on the new base (`docs/07-crosscutting.md:929-935`, was :887-893).

## 1. Half-written file (v4 :640)

**The change.** `_remarks_block` now writes through `leaves._replace_record` instead of
`Path.write_text` (post :655, import post :134). That helper writes a sibling temp file
(`.merge-remarks.json.partial`), calls `os.replace`, and removes the temp on failure
(`template/src/pdca_harness/leaves.py:1168-1188`). A failed write now leaves no file in the bundle,
the stop says it could not be written, and the PR still goes back to draft. An older file cannot
survive beside that message either, because `_merge_one` removes it when the attempt starts (post :746).

**Why call it rather than copy it.** The sign-off named both `leaves._replace_record` and
`autoiterate._write_ledger` as the pattern. `_replace_record` is the one that does all of what it asked:
`_write_ledger` does not remove its temp on failure (`autoiterate.py:296-299`). The costs:

| Option | Cost |
|---|---|
| Call `leaves._replace_record` (chosen) | 1 word in the import, 2 changed lines at the call |
| Copy it into `_remarks_block`, using the `try` already there | 6 more lines (the temp's path, `os.replace`, the `suppress` + `unlink` pair, imports of `os` and `contextlib`), and a fourth copy of this pattern (`leaves`, `autoiterate`, `act`) |

`merge` already loads `leaves` through `publish` (`publish.py:34`) and already calls private helpers in
other modules (`merged._pr_view`, `publish._publish_record`). `leaves` does not import `merge`. Each of
`merge`, `leaves`, `publish`, `merged`, `driver`, `cli`, `integrate` and `state` imports cleanly on its
own in a fresh interpreter, so the new import creates no cycle problem.

**Left as is.** A hard kill in the middle of the write leaves `.merge-remarks.json.partial` behind,
because nothing can run after that. Nothing reads it, and the next attempt that writes the file
overwrites it. `leaves` accepts the same limit for its own logs. Sweeping it at attempt start would cost
1 line but would spell out the temp's name a second time, outside `leaves`, so I left it.

## 2. Wrong host (v4 :562)

**The change.** `_review_threads` parses the host out of `pr_url` (post :570) and passes it on every
page's query as `--hostname` (post :574). `urlsplit(...).hostname` gives lowercase with no port, which is
what `gh` itself takes from such a URL (table below). A URL with no host returns None with no query sent
(post :571-572): unknown, as for any other failed read.

**Why the `try` moved.** `urlsplit` raises `ValueError` on a URL such as `https://[host/...`, and this
function promises never to raise, because it runs while the PR is marked ready. I widened the existing
`try` to cover the whole read (post :569-605) rather than add a second one. The widened `try` is why the
diff against v4 looks large; the only new logic is the 3 lines at post :570-572 and the flag.

**Ruled out:** leaving the flag off when there is no host. It would send a query that cannot resolve to
`gh`'s default host, for the same outcome (None) and one more request.

**Checked against the real `gh` binary (2.103.3), offline.** I ran production `_review_threads` with only
`subprocess.run` wrapped to show `gh`'s `GH_DEBUG=api` output. Every host is under `.invalid`, which cannot
resolve, the token is a dummy, and `GH_HOST=default.invalid` stands in for a default host. Nothing reached
GitHub or any other host, so this is not the held live check.

| Code | URL | `gh` tried | Result |
|---|---|---|---|
| v4 | `https://GHE.invalid:8443/org/repo/pull/7` | `https://default.invalid/api/graphql` (the fault: the URL's host is ignored) | exit 1, None |
| this round | same | `https://ghe.invalid/api/graphql` (the URL's host, overriding `GH_HOST`) | exit 1, None |
| this round | `org/repo#7` | no request | None |

`gh pr view https://GHE.invalid:8443/org/repo/pull/7` also tried `https://ghe.invalid/api/graphql`, which is
why the test expects lowercase and no port. `gh pr merge <url>` following the URL the same way is from my
memory of `gh`, not checked.

## 3. Test — `template/tests/test_merge_review_remarks.py` (30 tests)

Imports only modules (`driver, merge, merged, state`, plus the existing `config.Config` / `LeafConfig`),
never a symbol this change adds, so the red leg imports and fails on assertions.

- **The `_Gh` stub asserts the host (:134-136).** A GraphQL request that does not name the stub's `host`
  (default `github.com`) raises `AssertionError`, which no handler in production catches, so every test that
  reaches the query also checks the flag. This is what the sign-off asked for at v4's test :120.
- **`test_threads_are_read_on_the_host_in_the_pr_url` (:294), new.** An Enterprise host, one with a port
  and one in capitals, each over two pages. Without it the stub's default could not tell a parsed host from
  a hardcoded `github.com`.
- **`test_a_pr_url_with_no_host_to_ask_is_not_read` (:316), new.** A shorthand, a bare number, no authority
  and a URL the parser rejects: no request, the "could not be read" line, the generic refusal, no file, PR
  back to draft.
- **`test_a_write_that_fails_leaves_no_file_and_still_returns_the_pr_to_draft` (:747)** replaces the test the
  reviewer said could not catch this (v4's test :700). Its stand-in for `Path.write_text` really writes half
  the text to the path it was called on, then raises `ENOSPC`, the disk-full error (:755-758). The test confirms that half was on
  disk and does not parse (:784-786), so the fault cannot pass unnoticed. It compares the whole bundle listing
  before and after, so a temp under any name is caught. A second subtest fails `os.replace` instead.
- **`test_blocked_by_threads_is_named_and_written` (:249)** now also checks that a good write leaves the one
  file and no temp.

## 4. Runs

Logs in the bundle: `c4-local.log`, `suite-green.log`.

- **C4**, `engine/scripts/run-verify.sh` → `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`.
  - Green leg: `test_merge` 59 OK, `test_merge_review_remarks` 30 OK, `test_merge_third_remote` 9 OK.
  - Red leg: `test_merge_review_remarks` `FAILED (failures=63)`, 0 errors. `test_merge` errors=7 and
    `test_merge_third_remote` errors=2 are the same as v4: the gate runs them only because this patch edits a
    line in each, and they raise `ValueError` because the reverted `_wait_for_green` returns two values. They
    say nothing about behaviour. The real red is the 63 assertion failures.
- **Whole suite**, `engine/scripts/run-suite.sh`: root `Ran 50 tests … OK`, driver `Ran 2697 tests … OK (skipped=2)`,
  `PDCA-EVIDENCE: root suite OK, driver suite OK`. 2697 = v4's 2675 + 2 new tests here + 20 test methods that came with
  the moved base (`git diff 3c11556 HEAD -- template/tests`).
- **Docs**, `engine/scripts/run-docs-check.sh`: `PDCA-EVIDENCE: docs lint clean, site render + link audit
  clean`.
- **C5**, `engine/scripts/run-prod-path.py`: `1 added driver-suite test(s) import the production package
  'pdca_harness'`.
- **Not run by me:** `run-host-ci.sh` (the same two docs checkers, and it needs the publish worktree to mean
  anything) and T4 (Check and publish run it).
- **Formatter / commit hooks:** the target has none to run: no `.pre-commit-config.yaml`, no `core.hooksPath`,
  only `.sample` git hooks, no ruff/black/flake8/isort in `template/pyproject.toml.jinja`. By hand: `git diff
  --check` clean, new lines ≤ 100 columns. Publish adds the DCO sign-off at commit time.

**The new tests against broken copies of production.** These go beyond the gate, which only compares against
main. Each copy sits in the git-ignored `.cache/`, and each run used `python -m unittest` under a timeout,
because the project's runner cannot point at another tree.

| Copy | Result | Went red |
|---|---|---|
| v4's `merge.py` as it was | `failures=54` | 24 tests; every test that reaches the query stops on `asked --hostname None` |
| Only the write put back as v4 had it, flag kept | `failures=2` | the write test alone: `merge-remarks.json` left in the bundle, and "could not be written" missing from the stop |
| Flag removed | `failures=50` | 23 tests |
| Host hardcoded to `github.com` | `failures=3` | the host test alone |
| `netloc` instead of `hostname` | `failures=2` | the host test alone: `ghe.example.com:8443`, `GHE.Example.COM` |
| No check for a missing host | `failures=3` | the no-host test alone |
| URL parsed outside the `try` | `errors=1` | the no-host test alone: `ValueError` escapes while the PR is marked ready |
| `_replace_record` not removing its temp | `failures=2` | the write test alone |
| Write failure raised, not reported | `errors=2` | the write test alone |

The second row is the one that matters for the first finding. In the first row the stub's host assertion fires
before the write, so that row alone would not show the write test catching a torn file.

**A real write failure, no stand-in.** Because the test's write failure is a stand-in, I also ran `merge_wave`
once under a real file-size limit (`RLIMIT_FSIZE` = 64 bytes, in a throwaway process, with `gh` stubbed), so the
kernel cut the write off:

| Code | Left in the bundle | Stop says | PR undone |
|---|---|---|---|
| Write as in v4 | `merge-remarks.json`, 64 bytes, does not parse | could not be written (`File too large`) | yes |
| This round | nothing | could not be written (`File too large`) | yes |

I did not ship this as a test. `RLIMIT_FSIZE` applies to the whole process, so it needs a child process, as
`test_attempt_ownership.py:72-113` does: that file's driver string alone is 34 lines, before the test that runs
it. The stand-in above does the same thing on disk, runs on any platform, and is the test the sign-off described.

## 5. What stays unproven

Everything above runs against a stubbed `gh`, or against a real `gh` that could not reach any host. A real
`BLOCKED` PR, a real failed `gh pr merge`, a real unresolved thread and `--hostname` on a host that answers have
not gone through this code. The sign-off holds the live read-only check for the rebuilt change and says it is not
build work, so I did not run it. Enterprise itself is not exercised: I have no such host.

Steps for the human once that check is released, on a sandbox repo with "require conversation resolution" on (the
`sandbox-gh-token` doctor row in `pdca.toml` names `eduralph/pdca-stack-sandbox`):

1. Read-only, on any PR with an open thread: `gh pr view "$PR_URL" --json
   mergeStateStatus,reviewDecision,latestReviews`, then from `template/`, `PR_URL="$PR_URL" PYTHONPATH=src python3 -c
   'import json,os; from pdca_harness import merge;
   print(json.dumps(merge._review_threads(os.environ["PR_URL"]), indent=2))'`. Compare with the PR. A non-null answer
   also shows `--hostname github.com` works where it counts.
2. Open a PR with one unresolved line comment and run it as a non-final merge-mode wave. Expect: the stop names
   `path:line` and `reviewDecision`, `merge-remarks.json` holds the decision and the host's error, and the PR is a
   draft again.
3. Resolve the thread and re-run. Expect: it merges and the file is gone.
4. Require an approval, leave a thread open and do not approve. Expect: the same named stop, with `reviewDecision:
   REVIEW_REQUIRED`, and the host's error in the file. Check whether that error names the real block. If it does not,
   the file gives a later reader less than this design assumes.

## 6. Self-refutation

- **(a) Genuine red? Yes.** `run-verify.sh` reverted the production hunks and re-ran: 63 assertion failures, e.g.
  `'blocked by 2 unresolved review thread(s)' not found in '… did not merge — a conflict, no merge rights …'`.
  Separately, each of this round's two fixes was reverted on its own in section 4, and the tests written for it went
  red: the write put back gives `['brief.md', 'merge-remarks.json', 'patch.diff', 'publish.json'] != ['brief.md',
  'patch.diff', 'publish.json']`, and the flag removed gives `gh api graphql asked --hostname None, not github.com`.
- **(b) Production path? Yes.** Every test calls `merge.merge_wave`, which runs the real `_merge_one` and, on the paths
  that reach them, the real `_remarks_block`, `_merge_state`, `merged._pr_view`, `_review_threads`,
  `leaves._replace_record`, `_refuse` and `_undo_ready`. Only `subprocess.run` (the `gh`/`git` boundary), `state.state`,
  `merged.is_merged`, `_sleep` and, in the write test, `Path.write_text` or `os.replace` are patched.
- **(c) Fixture includes the fault? Yes, within the stub.** The write test puts a real partial file on disk and then
  raises, and it asserts that this happened; a real `RLIMIT_FSIZE` run shows the same result without the stand-in.
  The host test uses an Enterprise URL, and the stub refuses any request not naming that host; a real `gh` run shows
  the fault it stands for. Not modelled: a real Enterprise host answering, and `gh`'s own auth for such a host.

## 7. Housekeeping

- **The builder guard blocked one of my commands**, and I did not try to get around what it protects. It was a script
  in a heredoc whose text had `gh pr` inside backticks. Nothing ran, and I made those edits with the Edit tool. No `gh
  pr ready` or `gh pr merge` ran outside the stubs.
- **Reading beyond the brief:** the `iteration-v4/` artifacts the carry-forward points at, the two peers it names
  (`leaves._replace_record`, `autoiterate._write_ledger`), the existing torn-write test
  (`test_attempt_ownership.py:72-113`), `merged._pr_view`, and `engine/scripts/` to find the project's runners.
- **Files I left behind on purpose:** the worktree has the new test file registered intent-to-add (`git add -N`) so
  `git diff` includes it in `patch.diff`, and `.cache/issue838-*` (the throwaway scripts and source copies above, in a
  git-ignored directory). The bundle's `test_merge_review_remarks.py`, `c4-local.log` and `suite-green.log` are refreshed
  from this round. Nothing committed, nothing pushed, no PR.
- **The `rounds` size signal will likely fire again at Check:** this is the fifth attempt and `pdca.toml:406` sets `rounds =
  3`. The human already overrode it for this outcome ("do not split it"). The patch is 69 KB, under `patch_kb = 125`
  (`pdca.toml:404`).
