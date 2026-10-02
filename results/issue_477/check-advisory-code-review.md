# Advisory code review — issue 477 (size-signal: discount deferred-gate rounds)

No correctness bugs found in this diff. I traced the new round rule in
`_environment_attributed` against the gate writer (`gates.py:813-830`, `:866-887`) and the
review parser (`assemble.py:248-304`, `:626`), and re-ran `tests.test_size_signal` and
`tests.test_attempt_harvest` on the patched target: 94 tests, all pass. The gate logs
agree: C4 is red without the fix and green with it, and T3 (2149 tests) is OK. Both
carry-forward items are fixed and tested: malformed `result` values count the round, and a
deferred row no longer covers for a failing row of the same element. The optional `[impl]`
item is fixed too. The notes below are small and none of them blocks.

- `template/src/pdca_harness/size_signal.py:272` — `_deferred_elements` treats only a
  non-string `element` as "could be anyone's". An empty string `""` (what `gates.py:514`
  and `:606` write for a check with no `tier`) goes into `live` as the element `""`, so a
  failing row like that does not stop the T4 deferral. This can't happen today:
  `_assemble_matrix` (`gates.py:873-878`) drops element-less rows before writing
  `check-gates.json`. It only matters for a hand-edited or future archive. If you want it
  closed, change the check to `if not isinstance(element, str) or not element:` and the
  fail-safe also covers that case.
- `template/src/pdca_harness/size_signal.py:330` — the `[impl]` check runs
  `assemble._needs_human(text)` a second time, because `_items_from_artifact` on the next
  line runs it again internally. That costs nothing at these input sizes, and the docstring
  explains why the raw text is needed (classifying strips the tag). It does create a second
  reader of `assemble` private names (`_IMPL_MARKER_RE`, `_needs_human`). If #408 changes
  how the tag is written, this line has to change with it. A small public helper in
  `assemble` (for example "items with their raw-tag flag") would keep it to one parser,
  which is the rule the docstring itself cites.
- `template/src/pdca_harness/size_signal.py:336` — `_review_drove_the_iterate` is no longer
  called by production code. It stays only because `tests/test_attempt_harvest.py:593` and
  `:684` call it. The docstring says this, as the carry-forward asked. A simpler option is to
  point those two tests at `_review_findings` (asserting `== []` / `is None`) and delete the
  wrapper. Optional.
- `template/src/pdca_harness/size_signal.py:370` — an advisory bullet that is not tagged
  but starts with a gate element id (for example `- NEEDS-HUMAN — T4 PR body lacks the
  tracker id`) is classified IMPL by `assemble._classify_finding` (`assemble.py:274-276`),
  so it charges the round. The same text in the primary review, on a deferred T4, is
  discounted. The brief asks for exactly this ("IMPL-kind as classified by
  `_items_from_artifact`"), and it errs toward counting, so this is a note, not a defect. No
  test covers this case.

Nothing here needs a human decision. The design questions about scope (the #446
tightening, Validation-only rounds) are in the brief's Open questions, and they belong to
the reviewer leaf, not this lens.
