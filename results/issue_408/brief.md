# Design proposal — issue 408 / review-impl-tag-v-row

> Child slice of #332 (items 2, 3, 5), split during Plan. Reopened 2026-08-11: PR #410
> merged only a scaffold commit, so none of this reached `main`. The working shape is
> proven downstream in getwyrd/wyrd-pdca#168 (merged 2026-07-26); this cycle ports the
> child-1 part of it to the template. Sibling slice: #409.

- **Slug:** review-impl-tag-v-row
- **Kind:** enhancement (design proposal)
- **Goal:** the reviewer, not a taxonomy proxy, states whether a judgment-cell finding is
  builder-fixable; the classifier honours that statement only where the taxonomy allows it;
  and the reviewer's always-human Validation row is recognised as the constant STANDING row
  in all three forms production actually writes it.
- **Success criterion:** all four hold in `template/tests/test_autoiterate.py`, run by the
  C4 gate:
  (1) **Tag honoured, bounded by the taxonomy.** A primary-review verdict row on C5 or T5
  whose Verdict cell is `NEEDS-HUMAN [impl]` classifies IMPL. The promotable set is derived
  from `gates.canonical_elements()` as `kind == "judgment"` minus `V` (so exactly
  `{C5, T5}` today), the way `_GATE_ELEMENTS` is derived at `assemble.py:50`, and a test
  pins that derivation. An `[impl]` tag on an input cell (C1, C3) or on the V row is
  ignored (C1/C3 → HUMAN; V → STANDING, because the STANDING check runs BEFORE the tag
  check). An untagged C5/T5 row still classifies HUMAN. Only the Verdict cell carries the
  tag: an `[impl]` in the Basis cell of a C5/T5 row is ignored (row stays HUMAN; pinned by a
  test — existing Basis-cell `[impl]` fixtures sit on C4, which is IMPL through the
  gate-element rule anyway, `test_autoiterate.py:224`).
  (1b) **The tag is bounded on every PRIMARY-review path, not just rows.** Today the
  leading-`[impl]` rule in `_classify_finding` (`assemble.py:228-230`) runs for every
  artifact, including the primary review's legacy `- NEEDS-HUMAN` bullets
  (`assemble.py:576-593`). After this slice a primary-review bullet carrying `[impl]` is
  promoted only if its leading element id is promotable (C5/T5); otherwise the tag is
  stripped and the item is HUMAN. Tested: `- NEEDS-HUMAN [impl] — C1 Spec …` and
  `- NEEDS-HUMAN [impl] — Validation — fitness-to-purpose …` in `review.md` → HUMAN.
  (1c) **Plan advisories are never promoted.** Today a `[impl]` in a `plan-advisory-*.md`
  bullet classifies IMPL (same `_items_from_artifact` path, `assemble.py:304-306`); it stays
  HUMAN only because the plan prompt never emits the tag. This slice makes that structural:
  plan advisories are parsed with the tag stripped and ignored. Tested (red today):
  `- NEEDS-HUMAN [impl] — …` in a plan advisory → HUMAN. The other rows the driver builds
  itself (unverifiable gates, declared / refuted / unregistered dependencies, the size item)
  are already constructed as HUMAN directly and are unchanged.
  (2) **V row in all three forms.** The STANDING match accepts
  `Validation — fitness-to-purpose`, `V — Validation — fitness-to-purpose`, and
  `Validation -- fitness-to-purpose`, by normalising the Item cell (drop a leading
  `<element-id> —` / `<element-id> --` prefix ONLY when that id is the element whose
  canonical label follows — so `V —` before the Validation label, `C1 —` before `C1 Spec`;
  fold ASCII `--` to `—`, collapse whitespace) before an EXACT comparison. A mismatched
  prefix is kept, so the cell never equals a canonical label: `| C5 — Validation —
  fitness-to-purpose | NEEDS-HUMAN | … |` and the same with `T5 —` stay HUMAN (negative
  tests). The same normalisation is used by `_verdict_table_lines`
  (`assemble.py:615`, label compare `:640-641`), so a table written entirely in the prefixed form (`C1 — C1 Spec`, …)
  is still recognised as the verdict table. No prefix-matching of free text (the #294 rule):
  `Validation — fitness-to-purpose: patches the wrong layer` stays HUMAN. The
  `i in verdict_table` guard and the fail-closed "two STANDING rows → neither"
  guard (`assemble.py:610-611`) are unchanged and still pass their existing tests.
  (3) **Prompts carry the contract.** `_REVIEW_PROMPT` (`leaves.py:2723`) lists the element
  labels bare (not `{elem} — {label}`, `leaves.py:2743`, which is the source of the prefix
  form), says to write the Item cell exactly as listed, and instructs `NEEDS-HUMAN [impl]`
  on the C5/T5 rows only, for implementation defects. `_advisory_prompt`
  (`leaves.py:3583`) drops "when in doubt, OMIT '[impl]'" (`leaves.py:3601`) and requires
  every NEEDS-HUMAN bullet to carry `[impl]` or `[human]`; an untagged bullet still reads as
  HUMAN. `template/agents/reviewer.md.jinja` and `template/agents/adversary.md.jinja` state
  the same contract (they are the role bodies inlined for codex leaves).
  (4) A `[human]` tag on an advisory bullet is stripped from the §6 text the same way
  `[impl]` is, and classifies HUMAN.
- **Falsifiability:** RED today on this host, via the offline driver suite
  (`cd template && PYTHONPATH=src python3 -m unittest tests.test_autoiterate`) as run by the
  C4 gate `./engine/scripts/run-verify.sh` (gating). That gate keeps the test files and
  reverts only production hunks, so tests appended to the existing module earn their red.
  Per clause: (1) a C5 row `NEEDS-HUMAN [impl]` classifies HUMAN today —
  `_classify_finding` (`assemble.py:209`) only strips a leading `[impl]` from the item TEXT,
  and a table row's text starts with the Item cell, never the tag; (2) the prefix form fails
  the exact casefolded compare at `assemble.py:603`, so parameterising `_STANDING_ROW`
  (`test_autoiterate.py:41`) over the three forms goes red on two; (3)/(4) string
  assertions on `_REVIEW_PROMPT`, `_advisory_prompt(...)` and the two `.md.jinja` files fail
  on today's text. Do's tests must reach new symbols through the module
  (`assemble._PROMOTABLE_ELEMENTS`), not `from … import` at module top: the red leg removes
  new symbols, and an import error there reads as PDCA-UNVERIFIABLE, not red.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Conflicts with:** 409, 371
- **Ordering note:** 477 is named below only because the wave command was run over the
  whole four-issue batch; 408 has no file overlap and no dependency with 477, so it is not
  declared in either field. 409 edits `assemble.py` (§6 merge of deferred findings) and
  `test_autoiterate.py`; 371 edits `assemble.py` (a new §6 item for flaky gate rows). Shared
  files, no build-on dependency, so different waves. The scheduler orients 371↔408 as 371
  first (lower id), and 371 depends on 409, so this slice builds last, on top of all three;
  nothing here needs to land earlier. Computed batch order (`pdca-pdca waves 408 409 371 477`): [409] → [371, 477] → [408].
- **Scope:** issue #332 items 2, 3, 5 — the reviewer/advisory/role-prompt tag contract;
  tag honouring in `assemble.py` for C5/T5 only (rows and primary-review bullets);
  plan-advisory parsing that ignores `[impl]` (`assemble.py:304-306`); V-row normalisation in both the STANDING
  match and the verdict-table detector; prompt/role-prompt alignment; tests as in the
  success criterion. / out of scope: `eligible()`, round budgets, deferral, the ledger,
  `rationale()` (all #409); routing input-cell defects to `iterate-plan` (#332 follow-up);
  whether a NEEDS-HUMAN on a *gate* cell whose gate row is `deferred` should stay IMPL
  (see Open questions); any change to `autoiterate.py`, `config.py`, `state.py`,
  `driver.py`, `flow.py`, `size_signal.py`.
- **Difficulty:** medium
- **External dependencies:** none
- **Test file:** template/tests/test_autoiterate.py
- **Citations expected:** Do must cite path:line on the target branch for every change.
  Peer callsites on `main` @ 9405658 (this bundle builds on a later wave's folded base, so
  lines will have moved — locate by symbol): `_GATE_ELEMENTS` `assemble.py:50` (mirror its
  derivation for the promotable set); `_ELEMENT_RE` `:53`; `_IMPL_MARKER_RE` `:58`;
  `_V_LABEL` `:83`; `_CANONICAL_LABELS` `:86`; `_classify_finding` `:209`;
  `_items_from_artifact` `:239`; `_needs_human` `:536` (table-row branch `:595-604`, exact
  compare `:603`, dual-STANDING guard `:610-611`); `_verdict_table_lines` `:615` (label
  compare `:640-641`); `_REVIEW_PROMPT` `leaves.py:2723` (element list `:2743`);
  `_advisory_prompt` `leaves.py:3583` (OMIT instruction `:3598-3601`);
  `template/agents/reviewer.md.jinja:99` (bare label example row);
  `template/agents/adversary.md.jinja:59-66` (`[impl]` paragraph, "when in doubt, omit").
  Downstream reference implementation: getwyrd/wyrd-pdca#168 (`_normalized_item_label`,
  `_PROMOTABLE_ELEMENTS`, prompt wording) — port the shape, re-cut to this scope.
- **Prior-art check (triage cycles):** `git -C ../pdca-harness log --oneline origin/main
  -n 8 -- template/src/pdca_harness/assemble.py template/src/pdca_harness/leaves.py` →
  d61908d, 3371af4, 6e74e70, fcc21a7, f81c4a0, 10665d8, 2b447c6, 4050da2 — none touch the
  tag contract or the V match (`_PROMOTABLE`/normalisation absent; exact compare still at
  `assemble.py:603`; OMIT still at `leaves.py:3601`; re-verified 2026-09-30). PR #410
  (merged) carried only an integration-branch scaffold. Closed-unmerged PRs touching
  `assemble.py`/`autoiterate.py`/`gates.py`/`size_signal.py`/`config.py`/`state.py`: none.
  No open PRs.
- **Disposition hint:** new-feature

## Motivation

Builder-fixability of a §6 finding is inferred from which 5/5/1 cell it sits on. On the
230-attempt corpus behind #332, T5 appeared in 146 attempts and C5 in 66; every one
classified HUMAN even when its substance was a plain build defect, so auto-iterate could
not fire. The advisory prompt tells leaves "when in doubt, OMIT `[impl]`", and 139 advisory
findings arrived untagged. And 37 of 223 observed V rows were written as
`V — Validation — fitness-to-purpose` or with `--`, failed the exact match, and counted as a
real objection. The prefix form comes from the driver's own prompt, which lists
`{elem} — {label}` while the role prompt shows the bare label.

## Design

- `assemble.py`: a promotable-element set derived from `canonical_elements()`
  (`judgment` minus `V`). The table-row branch of `_needs_human` detects a `[impl]` marker
  in the Verdict cell and carries it out next to `standing`. `_classify_finding` checks
  STANDING first, then honours the tag only when the row's element is promotable, then the
  existing gate-element rule. The leading-`[impl]` rule stays unbounded only for CHECK
  advisory bullets (`check-advisory-*.md`); on the primary review it is bounded to C5/T5
  (clause 1b), and on plan advisories it is ignored (clause 1c). `[human]` is stripped and
  means HUMAN.
- One Item-cell normaliser (prefix dropped only when it names the label's own element),
  used by both the STANDING compare and `_verdict_table_lines`.
- `leaves.py` + the two role prompts: bare labels, the exact-label instruction, the C5/T5
  `[impl]` instruction, and the required `[impl]`/`[human]` tag for advisories.

## Alternatives considered

- Prefix-matching the V label: rejected by the #294 review. It lets a real objection that
  starts with the label pass as the constant row.
- Honouring `[impl]` on every cell: an input-cell (C1/C3) defect survives any rebuild
  against the same brief, and V is emitted every cycle, so neither can be promoted.

## Impact & compatibility

Old review artifacts parse the same way, except that prefixed V rows now count as STANDING.
Untagged findings stay HUMAN (fail-safe).

**Policy change for the human to accept at sign-off:** Check advisory `[impl]` is NOT bounded
by the taxonomy — a leaf can self-label any finding `[impl]`, including one about scope or
fitness-to-purpose, and it will be auto-iterated. That is true today too, but today's prompt
says "when in doubt, OMIT `[impl]`", so an unsure finding reaches the human. Clause 3 removes
that default and forces an `[impl]`/`[human]` choice on every bullet, as #332 asks, so more
advisory findings may be promoted. This is a deliberate trade (#332), not a risk-free
change; bounding advisory tags by element is left out because advisory bullets carry no
reliable element id. Changes to `template/agents/` are human-only
review items per this project's INTEGRATION §4.

## Open questions

- (For sign-off) Accept the advisory-tag policy change described under Impact, or keep
  "when in doubt, omit" in `_advisory_prompt` and the adversary role body.

- A reviewer NEEDS-HUMAN on a *gate* cell (e.g. T4) classifies IMPL via `_ELEMENT_RE`
  even when that cell's gate row is `deferred` (withheld by design). That is how issue_453
  spent auto-iterate rounds on an unfixable T4 row. Not in this slice. Worth a separate
  issue if it recurs now that the reviewer is told to write N/A for `deferred` rows.

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.

Plan-review response: all six findings addressed in the brief — primary-review bullets
bounded to C5/T5 (clause 1b); plan-advisory `[impl]` made structurally ignored and added to
Scope (clause 1c); V-row prefix stripped only when it names the label's own element, with
C5/T5-prefixed negative tests (clause 2); advisory-tag policy change stated plainly for the
human (Impact + Open questions); 477 in the ordering note explained; Basis-cell `[impl]`
pinned as ignored (clause 1).

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: Rebuild to fix the two regressions the reviewer found (both reproduced at sign-off): 1. assemble.py (_needs_human_rows, ~:814): the [impl] tag is read from cells[vi], where vi is the first cell containing "needs-human" anywhere in the row, not the Verdict column. So `| C5 Causal adequacy | PASS | Quoted NEEDS-HUMAN [impl] from an old review |` in the verdict table becomes an IMPL item and would trigger a needless auto-rebuild. Use the Verdict column for both NEEDS-HUMAN recognition and tag extraction; add a test (PASS verdict + Basis-only quote -> no IMPL item). 2. assemble.py (~:807 with add() dedup ~:772): a bare and a `V —`-prefixed Validation row with identical Basis now normalise to the same text, so add() drops the second before the "two STANDING rows -> neither" fail-closed guard (~:821) can count it. Count STANDING rows before text dedup; add a test with IDENTICAL Basis cells (the existing test uses different Basis). Keep everything else; the rest of the patch (T5 prompt/role changes, V-row normalisation, plan-advisory/primary-review bounding) was found fine at sign-off. Advisory-tag policy change (mandatory [impl]/[human] on every advisory bullet, "when in doubt, omit" removed) was explicitly ACCEPTED at sign-off — keep it as is.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  Rebuild to fix the two regressions the reviewer found (both reproduced at sign-off):
  1. assemble.py (_needs_human_rows, ~:814): the [impl] tag is read from cells[vi], where vi is the
     first cell containing "needs-human" anywhere in the row, not the Verdict column. So
     `| C5 Causal adequacy | PASS | Quoted NEEDS-HUMAN [impl] from an old review |` in the verdict
     table becomes an IMPL item and would trigger a needless auto-rebuild. Use the Verdict column
     for both NEEDS-HUMAN recognition and tag extraction; add a test (PASS verdict + Basis-only
     quote -> no IMPL item).
  2. assemble.py (~:807 with add() dedup ~:772): a bare and a `V —`-prefixed Validation row with
     identical Basis now normalise to the same text, so add() drops the second before the
     "two STANDING rows -> neither" fail-closed guard (~:821) can count it. Count STANDING rows
     before text dedup; add a test with IDENTICAL Basis cells (the existing test uses different Basis).
  Keep everything else; the rest of the patch (T5 prompt/role changes, V-row normalisation,
  plan-advisory/primary-review bounding) was found fine at sign-off.
  Advisory-tag policy change (mandatory [impl]/[human] on every advisory bullet, "when in doubt, omit" removed) was explicitly ACCEPTED at sign-off — keep it as is.
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).

## Iteration 2 — carry-forward (from the previous attempt)
- Sign-off rationale: Rebuild to fix one regression the reviewer found (reproduced at sign-off): assemble.py (_needs_human_rows, ~:833): the Verdict column is now found by its header (_verdict_column), but the Basis is still read as cells[vi + 1]. With a header ordered `| Item | Basis | Verdict |` the Basis is lost, so a promoted finding reads only `T5 Judgment` instead of `T5 Judgment — Handle empty input`, and the rebuild gets nothing to act on. Find the Basis column by its header too (fall back to the cell after the Verdict only when no Basis header exists), and make the reordered-column test assert the FULL finding text, not just the label and kind. Second change (human decision at sign-off): a verdict-table row whose Verdict cell says PASS / FAIL / N/A but whose other cells mention NEEDS-HUMAN must NOT be dropped from §6 (assemble.py ~:822-823). It must never become IMPL (no auto-rebuild), but it should still reach the human as a HUMAN item, which keeps the old fail-safe for self-contradicting rows like `| T5 Judgment | PASS | still NEEDS-HUMAN on scope |`. Update test_a_basis_quoting_an_impl_verdict_under_pass_is_no_finding: assert no IMPL item, and assert the row appears as a HUMAN item. The STANDING guards are unchanged. Keep everything else as is: the iteration-1 fixes (tag read from the Verdict column only; STANDING rows counted before dedup), the V-row normalisation, the C5/T5 bounding, the plan-advisory/primary-review bounding, and the prompt/role changes were all found fine. The advisory-tag policy change stays accepted.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  Rebuild to fix one regression the reviewer found (reproduced at sign-off):
  assemble.py (_needs_human_rows, ~:833): the Verdict column is now found by its header
  (_verdict_column), but the Basis is still read as cells[vi + 1]. With a header ordered
  `| Item | Basis | Verdict |` the Basis is lost, so a promoted finding reads only
  `T5 Judgment` instead of `T5 Judgment — Handle empty input`, and the rebuild gets nothing
  to act on. Find the Basis column by its header too (fall back to the cell after the
  Verdict only when no Basis header exists), and make the reordered-column test assert the
  FULL finding text, not just the label and kind.
  Second change (human decision at sign-off): a verdict-table row whose Verdict cell says
  PASS / FAIL / N/A but whose other cells mention NEEDS-HUMAN must NOT be dropped from §6
  (assemble.py ~:822-823). It must never become IMPL (no auto-rebuild), but it should still
  reach the human as a HUMAN item, which keeps the old fail-safe for self-contradicting rows
  like `| T5 Judgment | PASS | still NEEDS-HUMAN on scope |`. Update
  test_a_basis_quoting_an_impl_verdict_under_pass_is_no_finding: assert no IMPL item, and
  assert the row appears as a HUMAN item. The STANDING guards are unchanged.
  Keep everything else as is: the iteration-1 fixes (tag read from the Verdict column only;
  STANDING rows counted before dedup), the V-row normalisation, the C5/T5 bounding, the
  plan-advisory/primary-review bounding, and the prompt/role changes were all found fine.
  The advisory-tag policy change stays accepted.
- Full previous attempt preserved in `iteration-v2/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).

## Iteration 3 — carry-forward (from the previous attempt)
- Sign-off rationale: Rebuild to fix one regression the reviewer found (reproduced at sign-off): assemble.py (_needs_human_rows, add() ~:799-812): when two rows dedup to the same text, the merge AND-s `impl` and OR-s `other` but keeps the FIRST row's `standing`. So a verdict-table V row written `V — Validation — fitness-to-purpose` followed by a separate `## Concerns` table row `Validation — fitness-to-purpose` with the IDENTICAL Verdict and Basis collapses into one STANDING row, and the real objection disappears (pre-fix both reached §6 as HUMAN). Fix: merge standing fail-safe too (`standing = existing.standing and new.standing`), so any non-standing copy keeps the item a HUMAN finding. Add a test for this order (prefixed V row in the verdict table, bare-label copy with identical Basis in a Concerns table -> one HUMAN item, not STANDING) and keep the existing opposite-order test (test_a_concerns_table_copy_of_the_v_row_is_not_folded_into_it). Keep everything else as is: tag read from the Verdict column only, Verdict/Basis found by header, PASS rows mentioning NEEDS-HUMAN reach §6 as HUMAN, STANDING rows counted before dedup, V-row normalisation, C5/T5 bounding, plan-advisory/primary-review bounding, prompt/role changes, and the accepted advisory-tag policy. Do NOT restructure the review output format: replacing keyword parsing of free markdown with a structured verdict format is deliberately deferred to milestone 0.70 as its own issue.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  Rebuild to fix one regression the reviewer found (reproduced at sign-off): assemble.py (_needs_human_rows, add() ~:799-812): when two rows dedup to the same text, the merge AND-s `impl` and OR-s `other` but keeps the FIRST row's `standing`. So a verdict-table V row written `V — Validation — fitness-to-purpose` followed by a separate `## Concerns` table row `Validation — fitness-to-purpose` with the IDENTICAL Verdict and Basis collapses into one STANDING row, and the real objection disappears (pre-fix both reached §6 as HUMAN). Fix: merge standing fail-safe too (`standing = existing.standing and new.standing`), so any non-standing copy keeps the item a HUMAN finding. Add a test for this order (prefixed V row in the verdict table, bare-label copy with identical Basis in a Concerns table -> one HUMAN item, not STANDING) and keep the existing opposite-order test (test_a_concerns_table_copy_of_the_v_row_is_not_folded_into_it).
  Keep everything else as is: tag read from the Verdict column only, Verdict/Basis found by header, PASS rows mentioning NEEDS-HUMAN reach §6 as HUMAN, STANDING rows counted before dedup, V-row normalisation, C5/T5 bounding, plan-advisory/primary-review bounding, prompt/role changes, and the accepted advisory-tag policy. Do NOT restructure the review output format: replacing keyword parsing of free markdown with a structured verdict format is deliberately deferred to milestone 0.70 as its own issue.
- Full previous attempt preserved in `iteration-v3/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
