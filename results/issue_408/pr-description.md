## Summary
**User impact:** when a reviewer flags a plain build mistake under "causal adequacy" (C5)
or "judgment" (T5), the harness never sends it back to the builder for an automatic
retry. Every one of those findings lands on the human's desk instead. On top of that, the
always-present "Validation — fitness-to-purpose" line is sometimes written in a slightly
different form, and then it shows up as an extra open objection the human has to clear by
hand.

This PR lets the reviewer say explicitly that a C5/T5 finding is a fix for the builder, and
recognises the Validation line in every form it is actually written in.

Reported in [#408](https://github.com/eduralph/pdca-harness/issues/408).

## What to look at
- **The rule:** a C5 or T5 row whose Verdict cell is exactly `NEEDS-HUMAN [impl]` goes back
  to the builder. The tag is ignored everywhere else (input cells, the Validation row, the
  Basis column, a verdict that only quotes the tag), so those still go to the human.
- **The Validation line:** `Validation — fitness-to-purpose`,
  `V — Validation — fitness-to-purpose` and `Validation -- fitness-to-purpose` are all the
  same constant line now. A different prefix (`C5 — Validation — …`) or extra words after
  the label still count as a real objection.
- **Prompts:** the reviewer prompt lists bare labels and explains the C5/T5 tag; advisory
  reviewers must now tag every finding `[impl]` or `[human]` (the old "when in doubt, omit
  `[impl]`" default is removed — a deliberate policy change, accepted for #332).
- **To try it:** `cd template && PYTHONPATH=src python3 -m unittest tests.test_autoiterate`.
- **Merge order:** this branch builds on #409 and #371 (same files, no logic dependency).
  Line numbers below are on this branch.

## Root cause
Whether a finding can be fixed by the builder was inferred only from which cell it sits on,
and C5/T5 are judgment cells, so they always classified as human; the leading-`[impl]` rule
only read the start of the finding text, which for a table row is the Item cell, never the
tag. The Validation row was matched with an exact string compare, and the driver's own
review prompt listed elements as `{elem} — {label}`, which produced the prefixed form that
failed that compare.

## Fix
- `template/src/pdca_harness/assemble.py`
  - `_PROMOTABLE_ELEMENTS` (`:69`): judgment cells minus `V` from `canonical_elements()`,
    derived the same way as `_GATE_ELEMENTS` (`:60`).
  - `_VERDICT_IMPL_RE` (`:85`): the Verdict cell must be the whole `NEEDS-HUMAN [impl]`
    token (bold/backticks allowed).
  - `_normalized_item_label` (`:130`): drops an `<id> —` / `<id> --` prefix only when the id
    is the label's own element, folds `--` to `—`, collapses whitespace. Used by the standing
    match and by `_verdict_table_lines` (`:899`).
  - `_needs_human_rows` (`:780`): finds the Verdict and Basis columns by header, reads the tag
    from the Verdict cell only, promotes only when the normalised Item cell is a canonical
    label, counts standing rows before deduplication (fail-closed guard at `:894`), and merges
    duplicates fail-safe — standing only if every copy is (`:824`).
  - `_classify_finding` (`:296`): standing check first, then the tag (bounded to C5/T5 for the
    primary review), then the existing gate-element rule; `[human]` is stripped and stays
    human. Plan advisories are parsed with the tag ignored (`:448`).
- `template/src/pdca_harness/leaves.py`: review prompt lists bare labels and the C5/T5 tag
  instruction (`:2743-2761`); advisory prompt requires `[impl]`/`[human]` (`:3606-3608`).
- `template/agents/reviewer.md.jinja`, `template/agents/adversary.md.jinja`: same contract
  in the role bodies.

## Verification
- **Claim:** a `NEEDS-HUMAN [impl]` verdict on C5/T5 is sent back to the builder, and the
  promotable set is derived from the taxonomy.
  **Checked:** `assemble.py:69`, `:85`, `:780-894`.
  **Test:** `test_promotable_set_is_derived_from_the_taxonomy`,
  `test_impl_verdict_on_c5_or_t5_classifies_impl`,
  `test_impl_verdict_on_c5_auto_iterates_end_to_end` (`test_autoiterate.py:1850-1870`).
- **Claim:** the tag is ignored on input cells, the Validation row, the Basis cell, quoted
  verdicts and non-exact Item cells; primary-review bullets promote only C5/T5; plan
  advisories never promote.
  **Checked:** `assemble.py:296`, `:448`, `:878-882`.
  **Test:** `test_autoiterate.py:1877-1992` (input cell / V row, Basis cell, bullets, plan
  advisory, quoted verdicts, non-label Item cells, PASS rows that mention the tag).
- **Claim:** all three Validation-row forms are the standing row; a mismatched prefix or
  extra words are still objections; two Validation rows, or a copy with identical text,
  are never standing.
  **Checked:** `assemble.py:130`, `:805-824`, `:894`, `:899`.
  **Test:** `test_autoiterate.py:2112-2266`, including
  `test_a_copy_with_the_v_rows_exact_text_stays_a_human_finding` and its end-to-end twin.
- **Claim:** prompts and role bodies carry the contract; `[human]` is stripped.
  **Checked:** `leaves.py:2743-2761`, `:3606-3608`.
  **Test:** `test_autoiterate.py:1914`, `:2267-2290`.
- **Red/green:** with the production changes reverted and the tests kept, the module fails
  (140 tests, 84 failures, 2 errors); with the patch, 140 tests pass. Full offline driver
  suite: 2215 tests OK (2 skipped).

Fixes #408
