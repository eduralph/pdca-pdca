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
