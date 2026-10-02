# Advisory code review — issue_408 (review-impl-tag-v-row)

Both fixes from the sign-off carry-forward are in and tested: the tag is read only from the
Verdict column (`assemble.py:816-839`), and STANDING rows are counted before dedup
(`assemble.py:834-835`, guard at `:847`). Gates pass: C4 is red without the fix and green with
it, and the T3 suite ran 2202 tests OK. I found no bug that makes the patch wrong. The points
below are edge cases and small cleanups.

- NEEDS-HUMAN [human] — `template/src/pdca_harness/assemble.py:822-823`: when the verdict table
  has a Verdict column and that cell says PASS / FAIL / N/A, the row is now **dropped from §6
  entirely**, even if another cell says NEEDS-HUMAN. Before the patch, that row reached the
  human as a HUMAN item. The carry-forward only asked for "no IMPL item". Dropping the row
  goes further and gives up the old fail-safe for a self-contradicting row (for example
  `| T5 Judgment | PASS | still NEEDS-HUMAN on scope |`). `test_a_basis_quoting_an_impl_verdict_under_pass_is_no_finding`
  pins the drop on purpose. The human should confirm that "the Verdict cell wins outright" is
  the policy they want, rather than "no IMPL, but still HUMAN".
- `template/src/pdca_harness/size_signal.py:330` (file not touched by the patch; out of scope
  per the brief): `_review_findings` spots a reviewer `[impl]` only as a tag at the start of
  the text (`_IMPL_MARKER_RE`). It cannot see the new Verdict-cell `NEEDS-HUMAN [impl]` on
  C5/T5, because those items start with the label. The only effect is that a C5 `[impl]` row
  on a C5 element whose gate row is `deferred` could be discounted as "not slice churn".
  The impact is small, but the docstring at `size_signal.py:302-303` ("a finding tagged
  `[impl]` … counts the round") is no longer fully true. This is worth a follow-up issue.
  It is not a blocker.
- `template/src/pdca_harness/assemble.py:77` vs `:80`: `_IMPL_MARKER_RE` is now used only by
  `size_signal.py:330`, and `_TAG_MARKER_RE` covers the same prefix. A comment on
  `_IMPL_MARKER_RE` saying it is kept for `size_signal` would stop someone deleting it as dead
  code, or "fixing" one regex and not the other.
- `template/src/pdca_harness/assemble.py:124` (`_ITEM_PREFIX_RE`): the element-id match is
  case-sensitive (`v — Validation — fitness-to-purpose` keeps its prefix), but the label
  compare after it is casefolded. This fails safe (the row stays HUMAN), so it is only a
  consistency nit.
- `template/src/pdca_harness/assemble.py:885-897` (`_verdict_column`): it walks back up to the
  table header once for every NEEDS-HUMAN row, which costs O(rows²) per table. Verdict tables
  have about 11 rows, so this doesn't matter in practice. It would be simpler to find the
  column once per block inside `_verdict_table_lines`, but that is not needed.

Nothing else: the classifier order (STANDING, then `[human]`/ignored, then the Verdict-cell
tag bounded to C5/T5, then the text tag, then the gate element) matches the brief, and
`_PROMOTABLE_ELEMENTS` is derived the same way `_GATE_ELEMENTS` is.
