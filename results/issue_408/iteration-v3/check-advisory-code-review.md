# Advisory code review — issue 408 (round 3)

No correctness bug found that needs a rebuild. Both sign-off fixes are in place and tested:
the Basis column is now found by its header, and a row whose Verdict says PASS / FAIL / N/A
but mentions NEEDS-HUMAN elsewhere is now a HUMAN item instead of being dropped. The earlier
fixes are still there too: the tag is read only from the Verdict column, and STANDING rows
are counted before dedup. What I checked and found sound:

- `template/src/pdca_harness/assemble.py:841-866` — the header lookup only runs for
  verdict-table rows. A row with an empty or missing Verdict cell falls back to the old
  "first cell mentioning NEEDS-HUMAN" read, and no tag is read on that path
  (`impl=col is not None and …`). So a malformed row can reach §6 but can never become IMPL.
- `assemble.py:800-809` — when the same text shows up twice, the dedup merge fails safe:
  `impl` is AND-ed and `other` is OR-ed, so if either copy is untagged or contradicts
  itself, the item drops to HUMAN. The fail-closed guard counts raw V rows
  (`standing_rows`), not deduped items.
- `assemble.py:293-341` (`_classify_finding`) — STANDING is checked before any tag, `[human]` / plan-advisory /
  `verdict_other` are checked before the gate-element rule, and an unhonoured `[impl]` on
  the primary review falls through to the untagged classification. This matches the brief
  (1)/(1b)/(1c)/(4).

Small, non-blocking notes (none needs a human decision):

- `template/src/pdca_harness/size_signal.py:330` (not touched by this diff; the brief puts
  `size_signal.py` out of scope) still finds `[impl]` with `assemble._IMPL_MARKER_RE` on the
  `_needs_human` text. A reviewer's new Verdict-cell `NEEDS-HUMAN [impl]` never shows up in
  that text, and its docstring (`size_signal.py:315-318`, "the pattern
  `assemble._classify_finding` strips") is now out of date, because `_classify_finding` uses
  `_TAG_MARKER_RE` (`assemble.py:80`). As far as I can tell this has no effect on behaviour:
  a C5/T5 `[impl]` row comes back as a non-STANDING IMPL item from
  `_items_from_artifact`, so the round is still counted. It is worth a follow-up note on
  #409 / #477 so the two readers don't drift apart.
- `assemble.py:77` — `_IMPL_MARKER_RE` is now used only by `size_signal.py`, and
  `_TAG_MARKER_RE` (`assemble.py:80`) covers what it matches. Its comment ("An advisory leaf
  tags…") reads as if it still drives classification. A one-line comment saying it is kept
  for `size_signal` would prevent confusion. Optional.
- `assemble.py:841` / `assemble.py:914-926` — `_table_header` walks back to the top of the
  table again for every NEEDS-HUMAN row, so the cost grows with the square of the number of
  rows. Verdict tables have about 11 rows, so this costs nothing in practice. Working out the
  header once per block in `_verdict_table_lines` would be the simpler version if this code
  is touched again. Optional.
- Gate note: `gate-logs/C5-prod-path.log` passes with "patch adds no new test file —
  nothing to assert", so the prod-path gate checked nothing this round. By reading the
  tests instead: the new tests in `template/tests/test_autoiterate.py:1816-2212` call
  production code through the module (`assemble._items_from_artifact`,
  `assemble.collect_needs_human`, `leaves._REVIEW_PROMPT`, `leaves._advisory_prompt`) and
  copy none of its logic, so they do test the real code.
