# Advisory code review — issue 408 (review-impl-tag-v-row)

No correctness bugs found in the patch. I traced the classifier order in
`_classify_finding` (`template/src/pdca_harness/assemble.py:318-339`): STANDING first, then
`[human]` / plan-advisory → HUMAN, then the Verdict-cell tag bounded to C5/T5, then the
leading-text tag (free for Check advisories, bounded for the primary review), then the
gate-element rule. This matches clauses 1, 1b, 1c and 4 of the brief. The fail-closed
"two STANDING rows → neither" guard keeps the impl bit and still grants STANDING to
neither row. A V row tagged `[impl]` and caught by that guard falls through to HUMAN,
because "Validation …" never matches `_ELEMENT_RE`. The other readers of these helpers in
`size_signal.py` (`:330`, `:332`, `:370`) still behave safely: a C5/T5 Verdict-cell
`[impl]` row is now a non-STANDING IMPL item, so `_review_findings` still counts the round
through its returned list. The C4 log shows the new tests red before the fix
(15 failures, 2 errors) and green after. The C5 prod-path gate asserted nothing ("patch
adds no new test file"), but the new tests do call production code directly
(`assemble._items_from_artifact`, `collect_needs_human`, `leaves._REVIEW_PROMPT`,
`leaves._advisory_prompt`).

Minor cleanups. None needs a human decision or a rebuild:

- `template/src/pdca_harness/size_signal.py:313-317,330` — the patch makes this docstring
  stale. It says the `[impl]` read uses "the pattern `assemble._classify_finding` strips"
  (`_IMPL_MARKER_RE`). `_classify_finding` now strips `_TAG_MARKER_RE`
  (`assemble.py:83`), and the reviewer's main `[impl]` statement now sits in the Verdict
  cell, where line 330 cannot see it. Behaviour is still right, since the item list catches
  it. Still, the comment and the now nearly unused `_IMPL_MARKER_RE`
  (`assemble.py:77`, which duplicates half of `_TAG_MARKER_RE`) are worth tidying: use
  `_needs_human_rows`' impl bit or `_TAG_MARKER_RE`, and update the docstring.
- `template/src/pdca_harness/assemble.py:124` — `_ITEM_PREFIX_RE` matches the element id
  case-sensitively, but the label compare after it is casefolded. So
  `validation — fitness-to-purpose` counts as STANDING, while `v — validation —
  fitness-to-purpose` does not. This fails safe (the row stays HUMAN), and production has
  not been seen writing a lowercase id. Adding `re.IGNORECASE` and upper-casing
  `group(1)` before the `_ELEMENT_OF_LABEL` lookup would close the gap if you want it fully
  symmetric.
- `template/src/pdca_harness/assemble.py:805-808` — the comment says a canonical label "is
  rendered in the matrix's own spelling". `_normalized_item_label` only folds `--` to `—`,
  collapses whitespace and drops the prefix; it keeps the reviewer's casing. Either reword
  the comment or map `norm` to the canonical label (for example, by keeping the original
  label in a casefold→label dict) so §6 text really is uniform.
