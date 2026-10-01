# Build notes — issue 408 / review-impl-tag-v-row (iteration 3)

Target: eduralph/pdca-harness, worktree `/home/eddie/pdca/pdca-harness.pdca-wt` at `4b329e4`
(pdca-integrate: issue_477 — the folded base carrying 409, 371 and 477 on top of `main` @
9405658). Every `path:line` below is on that tree with this patch applied, unless it says
"base" (= `4b329e4` unpatched) or "v2" (= the second attempt, `iteration-v2/patch.diff`).

## What this iteration does

It starts from v2's patch and changes only the review-table parser in
`template/src/pdca_harness/assemble.py` plus its tests. The prompts, role bodies, C5/T5
bounding, plan-advisory and primary-review bounding, V-row normalisation, and the iteration-1
fixes are carried over unchanged, as the sign-off asked.

### Sign-off change 1 — the Basis is found by its header

v2 found the Verdict column by header but still read the Basis as `cells[vi + 1]` (v2
`assemble.py:833`). With `| Item | Basis | Verdict |` that cell does not exist, so a promoted
T5 finding read `T5 Judgment` with no Basis.

- `_table_header` (`assemble.py:914`) returns the header cells of the table holding a line
  (first row, stripped of `*`, `_`, backticks, casefolded). It replaces v2's
  `_verdict_column`, which did the same walk but returned only the Verdict index.
- In `_needs_human_rows`, for a verdict-table row: Verdict column from the header
  (`assemble.py:841-842`); Basis column from the header when one is named `Basis`, else the
  cell after the Verdict (`:858`), exactly the fallback the sign-off described.
- Rows outside the mandated verdict table get `header = []`, so they are read as on base
  (`cells[vi + 1]`).

### Sign-off change 2 — a row that contradicts its verdict reaches §6 as HUMAN

v2 dropped a verdict-table row whose Verdict cell said PASS / FAIL / N/A even when another
cell mentioned NEEDS-HUMAN (v2 `assemble.py:824`). Now:

- Every `|` row that mentions NEEDS-HUMAN is an item again, as on base. When the Verdict
  column is known and filled, `vi` is that column (`assemble.py:848`), and
  `other = "needs-human" not in cells[vi]` (`:860`) marks the contradicting row.
- `other` rows are never STANDING (`:864`, `standing=is_v and not other`) and never IMPL:
  `_classify_finding` returns HUMAN for `verdict_other` before the tag, promotion and
  gate-element rules (`assemble.py:336`). That matters on gate cells: on base,
  `| C4 … | PASS | still NEEDS-HUMAN … |` was IMPL through the element rule (base
  `assemble.py:275`) and would have triggered a rebuild.
- `verdict_other` is applied for every artifact, not just the primary review
  (`assemble.py:375`): it can only turn IMPL into HUMAN, never the other way.
- `_needs_human_rows` now returns a small `_Row` NamedTuple (`assemble.py:768`) with the new
  `other` field, instead of v2's 3-tuple. `_needs_human` still returns `(text, standing)`
  pairs (`:765`), because `size_signal.py:330` unpacks it.

Decisions inside change 2 the human should check:

1. **A lone contradicting V row is HUMAN, not STANDING.** For example
   `| Validation — fitness-to-purpose | N/A | NEEDS-HUMAN at sign-off |`. Base made it
   STANDING. I followed the sign-off text ("a verdict-table row … should still reach the
   human as a HUMAN item") and the reason STANDING exists: the row is the template constant,
   and the constant's verdict is NEEDS-HUMAN. If you want base's behaviour for V, it is a
   one-token change at `assemble.py:864` (`standing=is_v`) plus flipping
   `test_a_v_row_contradicting_its_verdict_is_not_the_standing_row` (`test_autoiterate.py:2145`).
2. **A contradicting V row still counts for the fail-closed guard** (`assemble.py:861-863`,
   guard at `:876`). So a real V row plus a contradicting one grants STANDING to neither,
   which is what base did with those two rows. The "STANDING guards are unchanged" instruction
   is why I kept the guard's input set the same as base's, rather than counting only rows that
   end up STANDING. Not counting it would also open an order-dependent hole: two V rows with
   the same text merge in `add()`, and the first copy's `standing` wins.
3. **Text of a contradicting row** is `Item — Basis`, like every other row (for example
   `T5 Judgment — still NEEDS-HUMAN on scope`). It does not show the PASS / FAIL / N/A verdict.
   Adding it would be about 2 lines; I left the one text shape for all rows. Base usually lost
   the Basis on these rows (it took the cell after the NEEDS-HUMAN mention, base
   `assemble.py:723`), so there is no older format to keep.
4. Dedup: when two rows give the same text, the kept item is `other` if either copy was
   (`assemble.py:811-812`), next to v2's rule that `[impl]` survives only if both copies
   state it. Either order gives HUMAN.

### A regression in v2 I found while re-reading — fixed, one token

v2 normalised the Item cell of every table row for display (v2 `assemble.py:831`,
`if norm.casefold() in _CANONICAL_LABELS`). So a "## Concerns" table row
`| V — Validation — fitness-to-purpose | NEEDS-HUMAN | fitness is the human's call |`
rendered with exactly the standing row's text, and `add()` folded it into the STANDING item:
an objection waved through as the constant. On base the prefix was kept, so it stayed a
separate HUMAN item. Fix: normalise only inside the verdict table (`assemble.py:856`,
`if in_table and …`), which is also all the brief asks for (clause 2: the STANDING match and
the table detector). Pinned by `test_a_concerns_table_copy_of_the_v_row_is_not_folded_into_it`
(`test_autoiterate.py:2161`), which is green on base and red on v2.

## Tests (template/tests/test_autoiterate.py)

Renamed because their old names stopped being true, with their assertions changed:

- `test_a_basis_quoting_an_impl_verdict_under_pass_is_no_finding` →
  `test_a_basis_quoting_an_impl_verdict_under_pass_is_human_never_impl` (`:1929`). This is
  the test the sign-off named. It now asserts no IMPL item and the row as a HUMAN item with its
  full text (C5 and T5).
- `test_a_basis_quote_under_pass_does_not_auto_iterate` →
  `test_a_basis_quote_under_pass_reaches_section_6_and_does_not_auto_iterate` (`:1941`): also
  asserts the `- [ ]` row is in the assembled SUMMARY §6.
- `test_the_verdict_column_is_found_by_its_header` →
  `test_the_verdict_and_basis_columns_are_found_by_the_header` (`:1996`): asserts the FULL
  text (`T5 Judgment — Handle empty input`, the sign-off's example) for two layouts —
  `| Item | Basis | Verdict |`, and `| Item | Verdict | Severity | Basis |` (where "cell after
  the Verdict" would read Severity).

New:

- `test_a_row_contradicting_its_verdict_is_human_on_every_cell` (`:1949`): the sign-off's
  `| T5 Judgment | PASS | still NEEDS-HUMAN on scope |` shape on all 10 non-V cells × PASS /
  FAIL / N/A (30 sub-tests).
- `test_a_gate_row_contradicting_its_verdict_does_not_auto_iterate` (`:1965`): end to end
  through `flow._maybe_auto_iterate`; the C4 row is in §6, nothing is rebuilt.
- `test_a_row_contradicting_its_verdict_is_deferred_beside_real_work` (`:1973`): beside a C4
  IMPL finding the rebuild runs and the contradicting T5 row is in the deferral ledger (so it
  comes back at handover), not lost with the round.
- `test_duplicate_rows_disagreeing_on_the_verdict_are_human` (`:1982`): both orders.
- `test_with_no_basis_header_the_basis_is_the_cell_after_the_verdict` (`:2020`).
- `test_a_v_row_contradicting_its_verdict_is_not_the_standing_row` (`:2145`).
- `test_a_contradicting_second_v_row_still_trips_the_fail_closed_guard` (`:2153`).
- `test_a_concerns_table_copy_of_the_v_row_is_not_folded_into_it` (`:2161`).

New symbols are reached as `assemble.<name>`, never imported at module top (brief).

## Red→green evidence (project runner)

C4 gate, `engine/scripts/run-verify.sh` with `PDCA_BUNDLE` / `PDCA_WORKTREE` set (it keeps the
test file and reverts every other hunk):

```
== C4 green leg: bundle test(s) with the fix applied: template/tests/test_autoiterate.py
Ran 135 tests in 2.337s
OK
== C4 red leg: bundle test(s) with the production change reverted
Ran 135 tests in 1.537s
FAILED (failures=61, errors=2)
PDCA-EVIDENCE: C4 PASS — red without the fix, green with it
```

Against v2's `assemble.py` (the rejected version, swapped in with this iteration's tests, run
through the same gate script): exactly the 11 new or changed tests fail (43 failures with
sub-tests) and the other 124 pass. I then restored this iteration's file from `patch.diff` and
checked the worktree diff is byte-identical to it.

T3, `engine/scripts/run-suite.sh` on the final patch: root suite 24 tests OK; driver suite
2210 tests OK (2 skipped). T2, `engine/scripts/run-docs-check.sh`: lint clean, render + link
audit clean. C5 prod-path: "patch adds no new test file" (the tests are appended to an
existing module that imports `pdca_harness`).

## Self-refutation (forced)

- **(a) Genuine red?** Yes. The C4 red leg reverted the production hunks and the same module
  went 61 failures + 2 errors. 10 of the 11 new or changed tests fail on base. The 11th,
  `test_a_concerns_table_copy_of_the_v_row_is_not_folded_into_it`, passes on base by design:
  base never normalised labels, so it could not fold the copy in. It guards v2's regression
  instead, and it fails against v2's `assemble.py`, as do all 11.
- **(b) Production path?** Yes. The tests call `assemble._items_from_artifact` and
  `assemble._needs_human` (the production parser and classifier). The four end-to-end tests
  build real bundles, run `gates.run_gates` with real gate commands, `assemble.assemble_summary`,
  and `flow._maybe_auto_iterate` with stub leaves. No copies, no mocks of the parser.
- **(c) Fixture includes the fault?** Yes. The fixtures are the sign-off's own inputs:
  `| Item | Basis | Verdict |` with `T5 Judgment` / `Handle empty input` /
  `NEEDS-HUMAN [impl]`, `| T5 Judgment | PASS | still NEEDS-HUMAN on scope |`, and the
  iteration-1 reviewer's `| C5 Causal adequacy | PASS | Quoted NEEDS-HUMAN [impl] from an old
  review |` — each inside a complete 11-row verdict table with the standing V row, as
  production writes it.

## Alternatives I rejected (with cost)

- **Fixed Basis index (column 2).** Same size as the header lookup (one line), but it is the
  same mistake as v1's fixed Verdict index: wrong for any reordered or widened table. The
  widened sub-test of `test_the_verdict_and_basis_columns_are_found_by_the_header` fails
  under it.
- **Basis-by-header for every table, not only the verdict table.** One token less
  (`header = _table_header(lines, i)` unconditionally), but it changes how base reads any
  other table, which the brief says should parse the same.
- **Closing the base-era dedup hole for STANDING too** (`add()` keeping STANDING only if every
  copy is STANDING): one line, `standing=items[k].standing and standing`. Not done: the hole
  is on base unchanged (a bare-label copy with an identical Basis in a Concerns table, or a
  bullet with identical text, is folded into the standing row when the verdict table comes
  first), and the sign-off said the STANDING guards stay as they are. Worth a follow-up issue.

## Not done (noted for the human)

- The pre-existing base dedup hole just above.
- A self-contradicting row whose NEEDS-HUMAN mention sits in an extra column that is neither
  the Item nor the Basis (`| T5 | PASS | ok | NEEDS-HUMAN: scope |`) shows as `T5 Judgment —
  ok`: it reaches the human as HUMAN, but the text does not say why. Base lost the text the
  same way, and extra columns are ignored for every row.
- Carried from v2: `size_signal.py:313-317` docstring is stale (out of scope per the brief);
  `_ITEM_PREFIX_RE` (`assemble.py:124`) matches the element id case-sensitively (fails safe);
  `agents/code-review.md.jinja:36` still shows the untagged `- NEEDS-HUMAN — ` form (the brief
  names only the reviewer and adversary role bodies; `_advisory_prompt`, which wraps every
  advisory leaf, requires the tag, `leaves.py:3606`).
- `size_signal._review_findings` (`size_signal.py:332`) reads the same parser, so a
  contradicting row counts as a review finding again, as on base (v2 had dropped it).

## Unchanged from v2 (for reference)

`_PROMOTABLE_ELEMENTS` (`assemble.py:69`, mirroring `_GATE_ELEMENTS` at `:60`);
`_normalized_item_label` (`:127`) used by the STANDING compare (`:861`) and
`_verdict_table_lines` (`:906`); plan advisories parsed with `plan_advisory=True` (`:445`);
prompts at `leaves.py:2745`, `:2756`, `:3606`; role bodies at
`agents/reviewer.md.jinja:101`, `:114` and `agents/adversary.md.jinja:25`, `:55`, `:60`.

## Commit-readiness

The target has no `.pre-commit-config.yaml`, no installed git hooks, no `core.hooksPath`, and
no Python formatter or linter config or CI job (workflows: docs-check, docs, render-check,
require-linked-issue). `git diff --check` is clean; no added line is longer than 99 characters.

## Housekeeping

Gate output went to `.git-verify408.log`, `.git-verify408-v2swap.log` and `.git-suite408.log`
at the worktree root (untracked, not in `patch.diff`). The driver's `git clean -ffdxq` before
each gate pass clears them. The T2 gate rendered its site under `/tmp` through its own
`mktemp`.
