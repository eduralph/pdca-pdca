# Advisory code review — issue #467 (split-children-inherit-release-metadata)

## Correctness bugs introduced by the patch

None found. Specifics checked and confirmed sound:

- `template/src/pdca_harness/split.py:1000-1019` (`_create_issue`) — new `milestone`/
  `labels` are keyword-only with safe defaults (`""`, `None`), so `triage.py:530-535`'s
  five-positional-arg call keeps working unchanged, as the brief requires.
- `template/src/pdca_harness/split.py:996-997` (`_gh_label_value`) — round-trips
  correctly against the pinned reader model in the new test file
  (`test_split_child_metadata.py:307-352`, `_gh_label_field`): a name with a comma, a
  bare `"`, or both, comes back as the one name it started as. Verified by hand for the
  `'"'`-only case and the comma+quote case; both match the test's expected output.
- `template/src/pdca_harness/split.py:1096-1131` (`file_children`) — the metadata lookup
  is gated on `parent_no` and happens once, before the loop, exactly per criterion (d);
  a `can_file` failure raises `TrackerUnavailable` before that point, so the `--ids` path
  and a non-GitHub tracker (criterion e) do zero lookups, confirmed against
  `split.py:930-944` (`can_file`) and `split.py:752` (`accept`, which never calls
  `file_children` at all on the `--ids` path).
- `template/src/pdca_harness/split.py:1039-1084` (`_parent_metadata`) — mirrors
  `sources.py:150-176` (`tracker_issue_reopened`) as claimed: non-zero exit, a raised
  exception, unparseable JSON, and a non-dict JSON value (`null`, `[]`) are all treated
  as "unknown," never crash `.get`, and the `bool` return correctly distinguishes "looked
  up fine, nothing to inherit" from "lookup failed" so the caller warns only in the
  second case.
- `template/tests/test_split_stub_guard.py` was **not** touched, despite the brief
  flagging its `_gh` fake (`:69-77`) as needing adaptation. Checked why: every test in
  that file asserts `self.calls == []` (`:133-134`, `:154`, `:163`) — the stub guard
  refuses before `file_children` is ever reached, and the `--ids` path does no lookup
  either. So that file never exercises a `gh issue view`/`create` pair for real, and
  leaving its fake as-is is correct, not an oversight.
- C4's red-run log (`gate-logs/C4-verify.log`) shows 13 real assertion failures pre-fix
  (missing `--milestone`, zero `gh issue view` calls, no warning line) rather than an
  import error, so the gate is grounded on the intended behavior, not a collection
  failure.

## Reuse / simplification / efficiency

Nothing to flag. The one place I looked for unjustified duplication —
`_parent_metadata` (`split.py:1039-1084`) re-implements the same
subprocess-run/guarded-json-parse pattern as `sources.tracker_issue_reopened`
(`sources.py:150-176`) instead of calling a shared helper — is deliberate and correctly
so: `sources._run_capture` (`sources.py:89-91`) calls `subprocess.run` through the
`sources` module's own reference, not `pdca_harness.split.subprocess`, which is the seam
every existing fake in `test_split.py` patches (per the brief's own citation). Reusing it
would reach past the offline fakes toward a real `gh`. The ~10-line duplication buys
keeping the test seam intact, which is the right trade here.

## Overall

Clean on both lenses. No findings requiring a human or a build iteration.
