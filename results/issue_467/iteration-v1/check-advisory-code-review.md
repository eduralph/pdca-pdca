# Check — advisory code review (issue #467)

Lens: correctness bugs the patch introduces, plus reuse/simplification/efficiency. Grounded
on `$PDCA_TARGET/template/src/pdca_harness/split.py` and the two test files the diff touches.

## Findings

Nothing rises to a defect. Specific things I checked and ruled out:

- `_parent_metadata` (`split.py:1025-1061`) is called exactly once before the filing loop
  (`split.py:1097-1101`), not per child — matches the brief's efficiency requirement (d), and
  C4's log confirms the red leg fails 7/11 new tests with the fix reverted while the green leg
  passes all 96+11, so the new test file genuinely exercises the change.
- `_create_issue`'s new `milestone`/`labels` params are keyword-only with defaults
  (`split.py:986-987`), so `triage.py:530-535`'s five-positional-arg call is untouched — verified
  by reading that call site directly, it passes exactly 5 positional args.
- The `--ids` path (`accept`, `split.py:752`) never calls `file_children` at all, so it does no
  lookup — matches criterion (e), and `can_file` failing for a non-GitHub tracker raises before
  `_parent_number`/the lookup ever run, so that path also does no lookup.
- `test_split_stub_guard.py`'s `_gh` fake (`:69-77`) was **not** adapted, unlike the brief's scope
  note flagged as expected — but that's correct, not an oversight: every test in that file either
  hits the stub-guard refusal before `can_file`/`file_children` run at all (asserts
  `self.calls == []`), or exercises the `--ids` path, which per (e) never reaches
  `_parent_metadata`. So there is no `gh issue view` call that fake needed to answer, and the
  T3 suite log confirms all 1799 tests including this file pass unmodified.
- `_parent_metadata`'s error handling (bare `except Exception`, guarded `json.loads`, dict-type
  check on the top-level result and on each label) mirrors `sources.tracker_issue_reopened`
  (`sources.py:150-176`) as the brief asked, including the same non-object-JSON-is-unknown guard
  (`sources.py:173-175`). It doesn't reuse a shared helper (`sources._run_capture`) — but
  `_create_issue` right above it (`split.py:1006-1007`) already inlines its own `subprocess.run`
  rather than sharing one, so the new function matches this file's existing pattern rather than
  introducing new duplication.
- Every `_is_metadata_lookup` check inserted into the existing `test_split.py` fakes runs
  *before* `self.calls.append(...)` in each case, so the pre-existing call-count-indexed
  assertions (`fail_at`, `numbers[n - 1]`, etc.) are not shifted by the new `gh issue view` call.

No `NEEDS-HUMAN` items — the diff is clean on both lenses.
