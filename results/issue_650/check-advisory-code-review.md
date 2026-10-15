# Advisory code review — issue 650 (merge mode reads head from its own remote)

The patch is clean on both lenses. I found no correctness bug and nothing that needs a human or another build round. The notes below are informational only, and none is tagged NEEDS-HUMAN.

**Correctness: checked and OK**

- `template/src/pdca_harness/merge.py:298-302`: `_have` treats exit 1 from `git cat-file -e` as "commit not here" and any other exit as a git failure. I checked this against real git: a well-formed 40-hex SHA that is missing exits 1, and a malformed name (`not-a-commit`, or a short SHA it can't resolve) exits 128. So the split is right, and the "missing" message only fires for a real, well-formed SHA. The host reports full SHAs (`headRefOid`), so that is the normal case.
- `template/src/pdca_harness/merge.py:265-273`: `_remotes` keeps the old fetch order (`base_remote`, `origin`) and adds the record's remote last, with duplicates removed. A `new-pr`/`stacked-pr` record (remote `origin`) or a record that names no remote (`None`) fetches exactly what it fetched before. This matches brief criteria (3) and (2b). The test at `template/tests/test_merge_third_remote.py:292` checks the exact `git fetch` argv list, including the case where `base_remote == "origin"`.
- `template/src/pdca_harness/merge.py:303-309`: last round's finding was that the refusal blamed a remote that had actually been fetched. That is fixed. The message now says only what was checked: the commit, the checkout, the remotes fetched, and either where the record puts the branch or that the record names no remote. The refspec case and the `new-pr`-head-not-on-origin case each have a test that pins the wording.
- `template/src/pdca_harness/merge.py:376`: in `_wait_for_update`, `_fetch(...) or _have(...)` runs `_have` only after a successful fetch. A missing head refuses before `_contains` runs, so this stays fail-closed.
- `template/src/pdca_harness/merge.py:481`: `pub` is read once and passed to all three reads (first read, update wait, read after green). The record's remote is fetched every time, and the test at `test_merge_third_remote.py` (`..._green_merges_pinned_...`) asserts this.
- `template/tests/test_merge.py:825`: the fake host's new `cat-file -e` branch answers from the same `self.local` set that the `merge-base` fake already uses (`:830`). Existing tests keep their behavior, and the suite passed (T3 log: 2379 tests OK).
- The C4 gate log shows the new tests failing on the unpatched code with the old `git failed … exited 128` message. That is a real behavioral RED, not a `TypeError` from a changed signature. The patched code passes.

**Reuse / simplification / efficiency: nothing to act on**

- `template/src/pdca_harness/merge.py:481` against `:428`: `integrate._published_ref(d)` reads `publish.json` again, even though `_merge_one` already holds `rec`. This is one extra small file read per bundle. The brief asks for exactly this reuse, so the record is parsed the same way the fold parses it. Not worth changing.
- `template/src/pdca_harness/merge.py:304`: `_have` calls `_remotes` again to build its message. The function is pure and cheap and gives the same answer `_fetch` used, so this is fine.
- `template/tests/test_merge_third_remote.py:281`: this test doesn't assert `rc`. It doesn't need to, because the point is "not refused up front" and `self.waited == [self.feat]` already proves the rollup wait was reached.

No findings for SUMMARY §6.

<!-- pdca:leaf-complete -->
