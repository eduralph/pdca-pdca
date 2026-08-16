# Check — advisory code review (issue #466)

Scope: `template/src/pdca_harness/{cli.py,leaves.py,split.py}` and the new
`template/tests/test_split_stub_guard.py`, as touched by patch.diff.

## Correctness

No bugs introduced by this diff.

- `template/src/pdca_harness/split.py:56` — `_STUB_RE` (`<!--\s*pdca:split-proposal-stub\s*-->`)
  cannot collide with `_VERSION_RE` (`<!--\s*pdca:split-proposal\s+v(\d+)\s*-->`): "stub" is not
  "v<digits>" and both markers are written on separate lines by `_stub_split`
  (`leaves.py:1619,1624`). Verified `_VERSION_RE` does not match the stub line and vice versa.
  `parse()`/`_scan()` are unaffected — the stub marker sits before the first
  `<!-- pdca:child -->` and is never mistaken for one.
- `template/src/pdca_harness/cli.py:784` — the `is_stub_proposal` check is correctly scoped
  inside `if not ids:` (cli.py:778), so `--ids` (criterion c) is untouched, matching the brief's
  citation of `cli.py:777-796` as the filing-only branch. The refusal happens before
  `split.file_children` (and therefore before `can_file` and any `gh issue create`), matching
  criterion (b)/(e).
- `template/src/pdca_harness/leaves.py:1594-1603` — the stderr announcement sits in the `else`
  branch guarding `_stub_split`, so `mode == "command"` prints nothing extra (test
  `test_command_mode_prints_no_stub_notice` locks this) and every non-`"command"` mode (not
  just literal `"stub"`) gets the notice — consistent with the pre-existing fallthrough the brief
  itself documents, not a new edge case introduced by the patch.
- Refactor at `cli.py:768-769` (splitting the single `read_text()` call into a `proposal_text`
  local reused by both `split.parse` and the new `is_stub_proposal` check) preserves the original
  single-read behaviour — no extra I/O, no change in exception shape (`OSError` still propagates
  from the same call site).
- C4 gate log confirms the new suite's red leg fails for the expected reasons (missing
  `is_stub_proposal` attribute, rc 0 where non-zero was expected, empty stderr) rather than an
  unrelated import error — the red is real, not `PDCA-UNVERIFIABLE` masquerading as red.

## Reuse / simplification

- `cli.py:785-790` reuses the existing `split.advisory(...)` + `return 1` shape used by the
  neighbouring `TrackerUnavailable` handler (`cli.py:795-802`), exactly as the brief's citations
  call for — no new error-reporting path was invented.
- `template/tests/test_split_stub_guard.py` duplicates (rather than imports) the `Config`/fake-`gh`
  setup pattern already present in `test_split.py`'s `Accepting` class. This is a style choice
  each test module in this suite already makes independently (no shared base class exists to
  reuse), and the brief only asked to "reuse that harness" in the sense of shape/approach, not
  necessarily via inheritance — not flagging this as a defect.

No findings need human or builder follow-up; the diff is clean on both lenses.
