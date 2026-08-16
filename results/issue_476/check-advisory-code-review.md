# Advisory code review — issue #476 (lineage-reader-doc-matches-the-reader)

## Scope of this diff
Single-file, prose-only change: `docs/07-crosscutting.md:277-289` (12 insertions, 4
deletions). No production code, no test file, no other doc paragraph touched — matches
`brief.md`'s declared scope exactly.

## Correctness (fact-checked against target source, not just against the brief)

Verified every factual claim in the rewritten paragraph directly against
`template/src/pdca_harness/split.py` on `$PDCA_TARGET`:

- "absent, unreadable, malformed JSON, a non-object payload and an unrecognised `version`
  all return `None`" — matches `read_lineage`'s `try/except Exception: return None`
  (`split.py:606-609`) plus `if not isinstance(data, dict) or data.get("version") !=
  LINEAGE_VERSION: return None` (`split.py:610-611`). All five failure modes are present
  and none are invented.
- "The first three cover *any* way of failing to parse the file at all... the last two
  parse cleanly and are turned away on shape and version" — correctly distinguishes the
  blanket `except Exception` (parse-time) from the `isinstance`/`version` checks
  (post-parse, shape/version). This is the exact distinction the iteration-1 sign-off
  demanded (carry-forward point 2) and it is drawn correctly.
- "the depth arithmetic one layer down absorbs the value it can't compute with, counting
  it as unknown (`0`) so the child lands at depth 1" — matches `_recorded_depth`
  (`split.py:615-631`): non-int, bool, or negative `depth` values fall through to `return
  0`, and the caller adds 1 for the child.
- "The parent's own record keeps `"one"` verbatim by a separate route: the merge copies an
  existing `depth` through rather than recomputing it" — matches
  `_merge_parent_lineage` (`split.py:643-657`), which calls `read_lineage(parent)` and
  copies `existing["depth"]` through the `for key in ("parent", "siblings", "depth")` loop
  without ever calling `_recorded_depth`. This correctly resolves the false causal link
  the iteration-1 sign-off flagged (carry-forward point 4: parent-record survival and
  child-depth fallback are stated as two independent mechanisms, not one).
- Cross-checked against the pinned test,
  `template/tests/test_split_lineage.py:236-251`
  (`test_accept_survives_a_parent_whose_recorded_depth_is_not_a_number`): child depth is
  asserted `== 1`, parent's `depth` is asserted `== "one"` verbatim. The corrected prose
  states exactly this outcome and no more.

No factual claim in the diff is unsupported by the code it describes, and no residual
gap from the iteration-1 rejection (missing "non-object" enumeration, the parse/shape
conflation, the implied causal link) is still present.

## Gate evidence sanity-check
- `C4-verify` → exit 77 `PDCA-UNVERIFIABLE` is the classification `run-verify.sh` gives
  any docs-only patch with no test; consistent with the brief's declared Falsifiability
  and not a false red.
- `T2-docs` and `host-ci-docs` both pass (`lint_docs: OK`, `render_site` link audit OK),
  confirming the rewritten paragraph doesn't break Obsidian syntax or internal links —
  the two mechanical checks this class of change can actually fail.

## Reuse / simplification / efficiency
Not applicable in the usual sense — this is a one-file prose edit with no code, no new
helper, and no hot path. The prose itself reuses the wording already present in
`read_lineage`'s own docstring (`split.py:586-587`, "absent, unreadable, malformed JSON,
a non-object payload and an unrecognised `version` all return `None`") rather than
re-deriving new phrasing, which is exactly what the iteration-1 sign-off asked for
(carry-forward point 3). No duplicated logic, no simpler equivalent, nothing to flag.

## Findings
None. The diff is clean on both lenses: no correctness bug is introduced (every claim
in the corrected paragraph checks out against the source it documents and against the
pinned test), and there is no reuse/simplification/efficiency opportunity being missed
(the patch already reuses the existing docstring wording rather than duplicating it).
