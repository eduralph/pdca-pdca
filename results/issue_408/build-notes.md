# Build notes — issue 408 / review-impl-tag-v-row (iteration 4)

Target: eduralph/pdca-harness, worktree `/home/eddie/pdca/pdca-harness.pdca-wt` at `4b329e4`
(pdca-integrate: issue_477, the folded base carrying 409, 371 and 477 on top of `main` @
9405658). Every `path:line` below is on that tree with this patch applied, unless it says
"base" (= `4b329e4` unpatched) or "v3" (= the previous attempt, `iteration-v3/patch.diff`).

## What changed since v3

I started from v3's patch unchanged and changed only `template/src/pdca_harness/assemble.py`
plus tests. `leaves.py`, both role bodies, the rest of `assemble.py` and all of v3's tests
are byte-identical to v3. The diff from v3's `assemble.py` is three code changes and their
comments:

1. **The fix the sign-off asked for.** When two rows dedup to one item, the item stays
   STANDING only if every copy is the standing row (`assemble.py:824`,
   `standing=items[k].standing and standing`). Comment at `:818-823`, docstring at
   `:800-802`.
2. **Not asked for — please confirm at sign-off.** The `[impl]` tag in a Verdict cell counts
   only when the whole cell is `NEEDS-HUMAN [impl]` (bold, italics or backticks allowed)
   (`assemble.py:81-85`, `fullmatch` at `:882`). v3 searched for it anywhere in the cell.
3. **Not asked for — please confirm at sign-off.** The tag promotes a row only when the
   row's Item cell, after `_normalized_item_label`, is a 5/5/1 label (`assemble.py:878-882`).
   v3 took the element from the text's leading id, so `C5 — Validation — fitness-to-purpose`
   counted as a C5 row.

Changes 2 and 3 break the "keep everything else as is" instruction, so they are the main
thing to check below. Each is a one-line revert, and both only turn a NEW IMPL into HUMAN.

## 1. The requested fix: a copy can no longer hide inside the standing row

The bug (v3 `assemble.py:799-812`): `add()` merged two rows with the same text, AND-ing
`impl`, OR-ing `other`, but keeping the first row's `standing`. A verdict-table row
`V — Validation — fitness-to-purpose` normalises to the bare label, so a bare-label copy with
the same Verdict and Basis in a `## Concerns` table produced the same text and was folded into
the standing row. The objection vanished. On base both rows reached §6 as HUMAN, because base
never normalised the label (base `assemble.py:726`, exact compare).

The same hole existed on base for the bare form: a bare V row followed by a copy with the same
text (another table, or a bullet) was folded in, because base's `add()` kept the first entry
(base `assemble.py:688-692`). The AND-merge closes that too.

Why this is enough: after the change, an item is STANDING only if every copy of it was a
verdict-table V row with a NEEDS-HUMAN verdict. Each such copy is counted in `standing_rows`
before the dedup (`assemble.py:876-877`), so two or more copies trip the fail-closed guard
(`:894`) and none is STANDING. So STANDING now always comes from exactly one source row: the
single V row of the verdict table. Any other row or bullet with the same text keeps the item
HUMAN, in either order. The guard itself is unchanged, as the sign-off asked.

What the human sees in §6 does not change: the merged item renders once, with the same text.
What changes is its kind. HUMAN means `autoiterate.deferrable` holds it in the ledger beside
IMPL work (`autoiterate.py:300`), where STANDING was dropped. The end-to-end test shows this.

## 2 and 3. Two more cases of the same kind — why I included them

After the fix I ran a throwaway probe (below) comparing base and the patched parser on 30,000
generated reviews. Apart from intended changes, it found two cases where the patch turns a row
into IMPL (an unattended rebuild) that base sent to the human. Both belong to the class the
iteration-1 sign-off rejected ("would trigger a needless auto-rebuild").

- **A Verdict cell that quotes the tag.** v3 used `_VERDICT_IMPL_RE.search`, so on C5/T5
  `PASS (was NEEDS-HUMAN [impl])` and `N/A — not NEEDS-HUMAN [impl]` became IMPL. Base: HUMAN.
  This is the iteration-1 case (a quote in the Basis) moved one cell left. Now the whole cell
  must be the verdict. Side effect: `NEEDS-HUMAN **[impl]**` now promotes (v3 missed it,
  because `\s*` did not allow `**`), and `NEEDS-HUMAN [impl] (minor)` no longer does — it goes
  to the human. The prompts already say the Verdict cell is the bare token and the reason goes
  in the Basis (`leaves.py:2747-2750`, `agents/reviewer.md.jinja:114-120`).
- **A row whose Item cell is not a clean label.** The row
  `| C5 — Validation — fitness-to-purpose | NEEDS-HUMAN [impl] | … |` became IMPL in v3:
  `_ELEMENT_RE` read `C5` off the front. That is
  the brief's own mismatched-prefix example (clause 2), which "is not the V row" — and with the
  tag it became a rebuild order for a fitness-to-purpose objection. Same for
  `C5 Causal adequacy: extra words` and a bare `T5`. Now the tag counts only on a row whose
  normalised Item cell is a canonical label, so the element is not in doubt. This is the same
  exact-match rule the STANDING check uses (the #294 rule: no prefix matching of free text).
  The prefixed and `--` forms of the label itself (`C5 — C5 Causal adequacy`,
  `T5 -- T5 Judgment`) still promote.

Why I did not leave them as notes: each review round so far found one parser case of this
kind and cost an iteration. These two are cheap (one condition each), and both are strictly
fail-safe: they only remove promotions this patch added. They cannot hide an objection or
create IMPL. If you want v3's behaviour back:

- change 2: `assemble.py:85` back to `re.compile(r"needs-human\s*\[impl\]", re.IGNORECASE)`
  and `:882` `.fullmatch` back to `.search`;
- change 3: drop `and norm.casefold() in _CANONICAL_LABELS` at `assemble.py:881`;
- and delete the matching tests (`test_autoiterate.py:1949`, `:1965`, `:1985`).

## The probe (exploration only, not a test)

`.cache/pdca-408/probe_fuzz.py` in the worktree (git-ignored, not in the patch). It loads base
`assemble.py` from `git show HEAD:` beside the patched module and generates complete verdict
tables, varying the Item form (bare, `E —`, `--`, mismatched prefix, upper case, extra words),
the Verdict cell (including quoted and emphasised tags), the Basis, the header (standard,
reordered, no Verdict column, an extra column), plus copies in Concerns tables, bullets and
duplicate rows, before or after the table. Each source carries a marker, and the probe flags
(a) a marker base showed as an objection but the patch shows only as STANDING or not at all,
and (b) a marker the patch makes IMPL where base did not. It runs each review as the primary
review, a Check advisory and a plan advisory.

Final result, after all three changes: every remaining flag is either the intended change (a
single V row written `V — …` or with `--`, which base read as HUMAN and the patch reads as
STANDING) or a text-only difference (a gate row base also made IMPL, but whose Basis base read
from the wrong cell, so the marker was missing from base's text). I checked examples of each
kind by hand. Plan advisories produced no flags.

## Tests (template/tests/test_autoiterate.py)

Five new test methods, appended to the existing classes. v3's tests are unchanged, including
`test_a_concerns_table_copy_of_the_v_row_is_not_folded_into_it` (`:2205`), the opposite
spelling arrangement the sign-off said to keep.

- `test_a_copy_with_the_v_rows_exact_text_stays_a_human_finding` (`:2218`): the sign-off's
  case — `V —` row in the verdict table, bare copy with the same Verdict and Basis in a
  `## Concerns` table → one HUMAN item. Run for all three V-row forms, with the copy as a
  Concerns row or a bullet, after or before the table (12 sub-tests). Also asserts the
  `_needs_human` pair is `(text, False)`, which `size_signal` reads.
- `test_a_copy_with_the_v_rows_exact_text_is_held_for_the_human_end_to_end` (`:2243`): real
  bundle, real gate, `flow._maybe_auto_iterate`. Beside C4 work the round fires and the
  objection is in the deferral ledger. Under v3 the ledger was empty.
- `test_only_a_verdict_cell_that_is_the_impl_verdict_promotes` (`:1949`): three quoted forms →
  HUMAN, five stated forms (plain, bold, backticks, bold tag, lower case) → IMPL, on C5 and T5.
- `test_the_impl_verdict_promotes_only_a_row_whose_item_is_the_label` (`:1965`): four doubtful
  Item cells → HUMAN; the prefixed and `--` label forms → IMPL.
- `test_a_verdict_cell_quote_under_pass_does_not_auto_iterate` (`:1985`): end to end, the
  `PASS (was NEEDS-HUMAN [impl])` row is in §6 and nothing is rebuilt.

New symbols are reached as `assemble.<name>`, never imported at module top (brief).

## Red→green evidence (project runner)

C4 gate, `engine/scripts/run-verify.sh` run from the instance root with `PDCA_BUNDLE` and
`PDCA_WORKTREE` set (it keeps the test file and reverts every other hunk):

```
== C4 green leg: bundle test(s) with the fix applied: template/tests/test_autoiterate.py
Ran 140 tests in 1.294s
OK
== C4 red leg: bundle test(s) with the production change reverted
Ran 140 tests in 1.406s
FAILED (failures=84, errors=2)
PDCA-EVIDENCE: C4 PASS — red without the fix, green with it
```

The 2 errors are v3 tests that reach a new symbol or text on base
(`test_promotable_set_is_derived_from_the_taxonomy`: `AttributeError`, as the brief expects;
`test_human_tag_on_an_advisory_bullet_is_stripped_and_human`: `KeyError`). My new tests all go
red by assertion: I switched two sub-tests to `kinds.get(...)` after a first run showed them
erroring with `KeyError` on base.

Against v3's `assemble.py` (rebuilt from `iteration-v3/patch.diff`, swapped into the worktree
with this iteration's tests, run through the same gate script — its green leg then runs the
tests against v3's code):

```
Ran 140 tests in 1.339s
FAILED (failures=20)
```

All 20 are sub-tests of the five new methods: the 6 "copy after the table" cases and the
end-to-end deferral (change 1); 8 Verdict-cell forms plus the end-to-end PASS-quote test
(change 2); 4 doubtful Item cells (change 3). Every older test passes against v3. I then put
this iteration's file back and checked `git diff` is byte-identical to `patch.diff`.

T3, `engine/scripts/run-suite.sh` on the final patch: root suite 24 tests OK; driver suite
2215 tests OK (2 skipped). That is v3's 2210 plus the 5 new methods. I did not re-run T2
(docs): this iteration changed no docs or role bodies, and v3's T2 run was clean.

## Self-refutation (forced)

- **(a) Genuine red?** Yes, twice over. With all production hunks reverted (C4 red leg),
  every new method fails except the PASS-quote end-to-end test, which passes on base by
  design: base never promoted a C5 row, so it is a guard against v3's regression. Against
  v3's `assemble.py`, all five new methods fail, 20 sub-tests in total, and nothing else does.
  The sign-off's exact case fails under v3 with `[("Validation — fitness-to-purpose — fitness
  is the human's call", True)] != [(..., False)]`, and the end-to-end test with `None != [...]`
  (nothing deferred).
- **(b) Production path?** Yes. The tests call `assemble._items_from_artifact` and
  `assemble._needs_human`, the production parser and classifier that `collect_needs_human`
  uses. The two end-to-end tests build real bundles, run `gates.run_gates` with a real gate
  command, `assemble.assemble_summary`, and `flow._maybe_auto_iterate` with stub leaves. No
  copy or mock of the parser.
- **(c) Fixture includes the fault?** Yes. The fixture is the sign-off's own input: a complete
  11-row verdict table with the V row written `V — Validation — fitness-to-purpose`, and a
  separate `## Concerns` table holding the bare label with the IDENTICAL Verdict
  (`NEEDS-HUMAN`) and Basis. The Verdict-cell fixtures use the literal quoted forms, and the
  Item-cell fixtures use the brief's own mismatched-prefix rows.

## Alternatives I rejected (with cost)

- **Stop rendering the normalised label in §6 text** (keep `V — Validation — …` as written,
  normalise only for the STANDING compare): about 3 lines at `assemble.py:864-871`. It avoids
  this one collision but not the base-era one (a bare V row plus a bare copy), it changes the
  §6 text v2's sign-off accepted, and the sign-off prescribed the AND-merge.
- **Never merge a standing row with anything** (keep both items): about 4 lines in `add()`.
  The human would see two identical lines, one STANDING and one HUMAN, and
  `autoiterate.deferrable` dedups by text anyway. The AND-merge is one token and gives one
  HUMAN line.
- **For change 2, match the tag at the start of the cell** (`^needs-human\s*\[impl\]`) instead
  of the whole cell: same size. It would still promote `NEEDS-HUMAN [impl]? or scope — unsure`.
  Whole-cell is the brief's wording ("whose Verdict cell is `NEEDS-HUMAN [impl]`").
- **For change 3, special-case only V-label prefixes** (reject `X — Validation — …`): about
  the same size, but it keeps `C5 Causal adequacy: extra words` and a bare `T5` promoting, and
  adds a second rule for "which element is this row" beside the one STANDING uses.

## For the human at sign-off

1. **Changes 2 and 3 above** go beyond "keep everything else as is". Accept them, or revert
   them with the lines given.
2. **Cost of change 2 and 3:** a reviewer who adds words to the Verdict cell
   (`NEEDS-HUMAN [impl] — minor`) or writes a non-exact Item cell gets no auto-rebuild; the
   finding goes to you as HUMAN. The reviewer prompt already asks for exact labels and the bare
   verdict token.
3. **Bullets are still bounded by their leading id** (brief clause 1b), so
   `- NEEDS-HUMAN [impl] — C5 — Validation — fitness-to-purpose: …` in the primary review
   still promotes. Rows and bullets now differ on this. Bullets are free prose with no label to
   match exactly; aligning them would mean changing the clause-1b rule.
4. **Not changed, same as base:** whether a row is a NEEDS-HUMAN row still depends on whether
   its Verdict cell *mentions* NEEDS-HUMAN (`assemble.py:874`). So
   `| C4 … | PASS (was NEEDS-HUMAN) | fixed |` is IMPL by the gate-element rule, and a V row
   with that verdict is STANDING — both exactly as on base. Requiring the cell to start
   with the NEEDS-HUMAN token is about 1 line, but it would also turn V rows like
   `N/A (NEEDS-HUMAN at sign-off)` from STANDING into HUMAN, which changes auto-iterate and
   size-signal counting for those reviews. Left for a separate decision.
5. **Carried from v3, still open:** a contradicting row whose NEEDS-HUMAN mention sits in an
   extra column shows the Basis, not the mention; the `size_signal.py:313-318` docstring
   describes `[impl]` as a leading text tag only (out of scope here); `_ITEM_PREFIX_RE`
   (`assemble.py:127`) matches the element id case-sensitively, which fails safe;
   `agents/code-review.md.jinja:36` still shows the untagged bullet form (the brief names only
   the reviewer and adversary role bodies; `_advisory_prompt` requires the tag for every
   advisory leaf, `leaves.py:3606`).

## Unchanged from v3 (for reference)

`_PROMOTABLE_ELEMENTS` (`assemble.py:69`, mirroring `_GATE_ELEMENTS` at `:60`);
`_normalized_item_label` (`:130`) used by the STANDING compare (`:875`) and
`_verdict_table_lines` (`:899`); `_table_header` (`:932`); `_classify_finding` (`:296`);
plan advisories parsed with `plan_advisory=True` (`:448`); prompts at `leaves.py:2743-2760`
and `:3606`; role bodies at `agents/reviewer.md.jinja:101`, `:114` and
`agents/adversary.md.jinja:25`, `:55`, `:60`.

## Commit-readiness

The target has no `.pre-commit-config.yaml`, no active git hooks (only `*.sample` in
`.git/hooks`), no `core.hooksPath`, and no Python formatter or linter config; its CI workflows
are docs-check, docs, render-check and require-linked-issue. `git diff --check` is clean and no
added line is longer than 99 characters.

## Housekeeping

Gate logs, the probe scripts, and a rebuilt copy of v3's `assemble.py` (with a scratch
`git init` used only to apply v3's patch to it) are under `.cache/pdca-408/` in the worktree.
`.cache/` is git-ignored (`.gitignore:11`), so none of it is in `patch.diff`; the harness
reclaims the worktree.
