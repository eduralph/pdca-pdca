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
