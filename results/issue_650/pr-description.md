## Summary
**User impact:** In merge mode, a PR published with `Onto branch` to a remote other than
the base remote or `origin` can never be merged once it falls behind its base. The run
stops with a bare "git failed … exited 128" message that does not say what is actually
wrong. Nothing gets merged wrongly; the PR just gets stuck.

This PR makes merge mode fetch the remote the PR was actually pushed to. If the head
commit is still missing after that, the run now says so plainly and names the commit.

Reported in [#650](https://github.com/eduralph/pdca-harness/issues/650).

## What to look at
- The change is in merge mode's "is this PR behind its base?" check. Before reading, it
  now also fetches the remote the bundle's publish record says the branch was pushed to.
- A new, clearer refusal for a head commit the checkout still doesn't have after the
  fetches. It lists the remotes fetched and where the record says the branch lives,
  and does not guess why the commit is missing.
- Nothing changes for normal PRs (branch on `origin`). They fetch exactly what they did
  before, and a test pins that.
- To reproduce: set up three bare repos as remotes (`origin`, `upstream`, `other`) on one
  checkout with `base_remote = "upstream"`, push a `feat` commit only to `other`, and
  write a `"stacked"` publish record with `"base": "other/feat"`. On `main`, merge mode
  refuses with "git failed … exited 128". With this PR it gets to the CI-wait step. The
  new test file does exactly this with real git and a scripted `gh`.

## Root cause
`_fetch` (`template/src/pdca_harness/merge.py:256-263` on `main`) fetched only
`base_remote` and `origin`. An `Onto branch` bundle is pushed to the remote in its brief
(`publish.py:465`, `:476-485`) and recorded as `{"mode": "stacked", "base":
"<remote>/<branch>", …}` (`publish.py:539-547`), so when that remote is a third one, the
head commit is never fetched. `_contains` (`merge.py:266-273`) then fails with exit 128
and `_git_failed` (`merge.py:250-253`) reports it as a plain git failure.

## Fix
- New `_remotes(cfg, pub)` (`merge.py:265-273`, after the patch) returns `base_remote`,
  `origin`, and the remote from the publish record, deduplicated in that order. The
  record is read with `integrate._published_ref` (`integrate.py:139-158`), the same rule
  the stack-mode fold already uses, so `publish.json` is not parsed a second way.
- `_fetch` (`:276-284`) loops over `_remotes`. A failed fetch of any of them, including the
  record's remote, is still a refusal.
- New `_have` (`:287-309`) runs `git cat-file -e <head>`. Exit 0: present. Exit 1:
  refuse with the commit, the checkout, the remotes fetched, and either "its publish
  record puts its branch at `<remote>/<branch>`, and fetching `<remote>` did not bring
  that commit in" or "its publish record does not say which remote its branch is on".
  Any other exit is reported as a git failure, not as "missing". The message lists only
  facts the code checked. Possible causes (a fetch refspec that skips the branch, a
  branch moved after the host read, a record naming the wrong remote) look the same at
  run time, so they are listed in the docstring, not in the message.
- `_merge_one` reads the record once (`:481`) and passes it to all three reads: the
  first behind-base read (`:482`), the wait after `gh pr update-branch` (`:498`, which
  is what lets a behind PR's new merge commit on the third remote be found), and the
  re-read before merging (`:534`). `_merge_one`'s signature is unchanged.
- `merge` now imports `integrate`. This adds no import cycle: `integrate` imports only
  `merged`, `publish` and `config` at module level (`integrate.py:59-60`).
- `tests/test_merge.py`: the fake git host now answers `cat-file -e` (2 lines). Without
  that, 14 existing tests fail with "unexpected git call".

## Verification
- **Claim:** a stacked PR whose head is only on a third remote is read correctly and
  reaches the CI wait, both when it is up to date and when it is behind and gets updated
  on that remote.
  - **Checked:** `merge.py:265-284` and `:481-534` (after the patch) on `main` @
    `b5f5c29`: the record's remote is fetched on every read.
  - **Test:** `test_stacked_head_on_third_remote_reaches_rollup_wait`,
    `test_stacked_head_behind_is_updated_on_third_remote_and_reaches_wait`,
    `test_stacked_green_merges_pinned_to_the_head_on_third_remote` (the merge is pinned
    with `--match-head-commit` to the head read on the third remote).
- **Claim:** a head commit still missing after the fetches is refused by name, without
  blaming a remote that was in fact fetched.
  - **Checked:** `merge.py:287-309` (after the patch).
  - **Test:** `test_head_in_no_fetched_remote_is_named`,
    `test_record_remote_fetched_without_the_head_is_not_blamed_as_left_out` (the remote
    has the head per `ls-remote`, but the checkout's fetch refspec skips it),
    `test_new_pr_head_not_on_origin_says_origin_was_fetched`,
    `test_a_head_git_cannot_read_is_a_git_failure_not_a_missing_commit`.
- **Claim:** a stacked record that names no remote fetches what `main` fetches, is not
  refused up front, and gets the named refusal if the head is still missing.
  - **Checked:** `integrate.py:150-157` on `main` (returns `None` for such a record);
    `_remotes` then adds nothing.
  - **Test:** `test_stacked_record_naming_no_remote_fetches_as_today_then_names_head`,
    `test_stacked_record_naming_no_remote_is_not_refused_up_front`.
- **Claim:** unchanged behaviour for a `new-pr` record: the `git fetch` calls are exactly
  `[base_remote, origin]`, deduplicated, as on `main` (`merge.py:259`).
  - **Test:** `test_new_pr_record_fetches_exactly_base_remote_then_origin` (also with
    `base_remote = "origin"`, where `origin` is fetched only once).
- **Regression test:** `template/tests/test_merge_third_remote.py` (new) uses real git
  with three bare remotes; only `gh` is scripted. With the `merge.py` changes reverted
  and the tests kept, 8 of 10 tests fail on behaviour (e.g. "git failed: `git merge-base
  --is-ancestor …` exited 128"); the 2 unchanged-behaviour guards pass on both. With the
  fix, all 10 pass. The full template suite passes (2379 tests, 2 skipped), including
  all 49 existing `test_merge.py` tests.

**Not in this PR:** whether an `Onto branch` bundle should be allowed in merge mode at
all. It currently skips the merge-mode base guard from #411; that would be a separate
issue.

Fixes #650
