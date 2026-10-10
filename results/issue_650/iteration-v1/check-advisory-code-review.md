# Advisory code review — issue_650 (merge-mode-reads-head-from-its-own-remote)

Lens: bugs the patch introduces, plus reuse and simplification. All gates pass. I found no correctness bug that blocks the fix. Two small wording/test points and some notes follow.

## Findings

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/merge.py:287-289`: the `_have` refusal always ends with "the remote its branch was pushed to is not among them (or its publish record does not name it)". For a `new-pr` / `stacked-pr` record, the branch's remote (`origin`) *is* in the fetched list. A missing head there means something else, such as a force-push between the `gh pr view` read and the fetch, or a host reporting a commit no remote has yet. So the second clause is wrong for that case and sends the operator looking in the wrong place. Fix: add that clause only when `integrate._published_ref(d)` returned None or named a remote outside `remotes`, or reword it neutrally, e.g. "none of these remotes has it".
- `template/tests/test_merge_third_remote.py:120-122` (patch lines 336-338): the `_wait` stub records `self.head`, the value the `gh` stub will return next. It does not record a head that `_merge_one` read. In `test_stacked_head_behind_is_updated_on_third_remote_and_reaches_wait`, `self.waited == [merged_head]` therefore proves less than it seems. What does prove that the merge commit was fetched from `other` is that the wait was reached at all, because `_wait_for_update` (`merge.py:354-363`) only returns once `_have` and `_contains` succeed on the new head. The test still catches the regression and the C4 log shows red/green, so this is a clarity note, not a defect. It is optional to assert on the `--match-head-commit` argv or on stdout's "updated: head <sha>" line instead.

## Checked and clean

- Import cycle: `merge.py:86` now imports `integrate` at top level. `integrate.py:59-60` imports only `merged`, `publish` and `config`, and nothing under them imports `merge`; only `flow.py:31` does. No cycle.
- Reuse: `_remotes` (`merge.py:260-267`) uses `integrate._published_ref` as the brief asked, instead of parsing `publish.json` again. It reads the record a second time (`_merge_one` already holds `rec`, `merge.py:407`). That costs one small file read per bundle. It is not worth changing, because `_published_ref` takes a bundle path.
- Fail-closed: a failed fetch of the record's remote is a refusal (`merge.py:270-277`). `publish._publish_stacked` fetches and pushes that same remote from the same `repo_checkouts` checkout (`publish.py:467`, `:477`, `:485`), so the remote always exists where merge mode reads. This adds no new way to fail.
- Order and dedup: `dict.fromkeys((base_remote, "origin", record_remote))` (`merge.py:267`) keeps `[base_remote, "origin"]` exactly as before for `new-pr` records. Criterion (3) is covered by the argv test at patch lines 413-417.
- `_have` runs after the base tip resolves and before `_contains` (`merge.py:325-327`), and in the update poll (`merge.py:354`). Both `_base_read` calls, before and after the green read (`merge.py:463`, `:519`), use the same `remotes`.
- `test_merge.py:824-825`: the new `cat-file -e` branch in the `_Host` stub checks the same `self.local` set that its `merge-base` branch uses (`test_merge.py:830`), so existing tests keep their old behaviour. The T3 suite log is green.

<!-- pdca:leaf-complete -->
