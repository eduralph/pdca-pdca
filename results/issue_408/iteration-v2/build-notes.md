# Build notes — issue 408 / review-impl-tag-v-row (iteration 2)

Target: eduralph/pdca-harness, worktree `/home/eddie/pdca/pdca-harness.pdca-wt` at `4b329e4`
(pdca-integrate: issue_477 — the folded base carrying 409, 371 and 477 on top of `main` @
9405658). Every `path:line` below is on that tree with this patch applied, unless it says
"base" (= `4b329e4` unpatched) or "v1" (= the first attempt, `iteration-v1/patch.diff`).

## What this iteration does

It starts from the first attempt's patch, unchanged except in the table-row parser
(`_needs_human_rows`), and fixes the two regressions the sign-off reproduced. Everything the
sign-off called fine (T5 prompt/role changes, V-row normalisation, plan-advisory and
primary-review bounding, the advisory-tag policy) is carried over as it was.

### Finding 2 of the review — the tag was read from whichever cell said NEEDS-HUMAN

v1 picked `vi` as the first cell in the row containing "needs-human" (v1 `assemble.py:802`)
and read `[impl]` from `cells[vi]` (v1 `:814`). So `| C5 Causal adequacy | PASS | Quoted
NEEDS-HUMAN [impl] from an old review |` became an IMPL item and would trigger a rebuild.

Fix, as the sign-off asked ("use the Verdict column for both NEEDS-HUMAN recognition and tag
extraction"):

- `_verdict_column` (`assemble.py:885`) returns the index of the column headed `Verdict` in
  the table holding a line, read off that table's first row (cell text stripped of spaces,
  `*`, `_`, backticks; compared case-insensitively). `None` when no header cell says
  `Verdict`.
- In `_needs_human_rows`, for a row of the mandated verdict table (`assemble.py:817-824`):
  the row is a finding only when its Verdict cell mentions NEEDS-HUMAN (`:824`), and the
  `[impl]` flag is read only from that cell (`:837-838`, `impl=col is not None and …`).
- Fallback, fail-safe (`:819-822`): a table whose header names no Verdict column, or a row
  whose Verdict cell is empty or missing, is read the old way (first cell mentioning
  NEEDS-HUMAN, base `assemble.py:720`) and never carries the tag. So a row we can't read a
  verdict from still reaches §6, and never as IMPL.
- Tables other than the mandated one are read exactly as before (`in_table` is False ⇒
  `col` is None).

### Finding 1 of the review — two V rows deduped into one before the guard counted

With normalisation, a bare V row and a `V —` V row with the same Basis give the same §6 text,
so `add()` dropped the second (v1 `:772`) and the "two STANDING rows → neither" guard (v1
`:821`) counted one.

Fix: `standing_rows` (`assemble.py:774`) counts every row that qualifies as STANDING before
`add()` dedups (`:834-836`); the guard tests `standing_rows > 1` (`:847`). The guard's
effect is unchanged: every item loses STANDING.

### Same flaw, applied to the `[impl]` flag (my extension — not in the sign-off text)

The dedup had the same hole for the new flag: `| C5 Causal adequacy | NEEDS-HUMAN [impl] | x |`
followed by `| C5 — C5 Causal adequacy | NEEDS-HUMAN | x |` normalises to one text, the
first row wins, and the row that withholds `[impl]` is silently dropped → IMPL. `add()` now
keeps an index per text (`assemble.py:773`) and a later duplicate that does not state
`[impl]` clears the flag on the kept item (`:786-789`). Either order now gives HUMAN. Cost: 6
lines. I added it because it is exactly the shape the reviewer found for V (normalisation +
dedup hiding a disagreeing copy), and the next review would likely find it too.

## Behaviour changes the human should know about

The brief's Impact section says old artifacts parse the same "except that prefixed V rows now
count as STANDING". After this iteration there are two more exceptions, both from the
sign-off's own instructions:

1. **A verdict-table row whose Verdict cell holds another verdict (PASS / FAIL / N/A) is no
   longer a §6 item, even if its Basis mentions NEEDS-HUMAN.** On base such a row became a
   HUMAN item showing only the label (the Basis was lost, because base took the cell after
   the NEEDS-HUMAN mention, `assemble.py:723` base, which was past the end of the row). This
   also reaches `size_signal._review_findings` (`size_signal.py:332`), which reads the same
   parser: such a row no longer marks a round as review-driven. That is the "same parser"
   rule that function documents, so I did not touch `size_signal.py` (out of scope).
2. **Two byte-identical bare V rows now fail closed (neither STANDING).** On base the dedup
   merged them into one STANDING item. The guard's own comment names "a duplicated row" as a
   case it exists for, and the sign-off asked to count before dedup, so this follows.

Tables whose header does not name a `Verdict` column (`| Element | Result | Reason |`, or no
header row) never get the tag honoured. The mandated header is `| Item | Verdict | Basis |`
(`leaves.py:2746`, `agents/reviewer.md.jinja:87`), so this only hits a reviewer that departs
from it, and it fails to HUMAN.

## Alternatives I rejected

- **Fixed column index 1 instead of the header lookup.** Saves the 14-line `_verdict_column`
  (with its docstring). Rejected on safety, not cost: for `| Item | Basis | Verdict |` it
  reads the Basis as the verdict, so a Basis quoting `NEEDS-HUMAN [impl]` is promoted, and the
  real NEEDS-HUMAN verdicts — including the V row — vanish from §6.
  `test_the_verdict_column_is_found_by_its_header` fails under that variant (it expects
  exactly `[T5 IMPL, V STANDING]`; fixed-index gives `[C5 IMPL]`).
- **Keep "any cell" recognition, read the tag only from the Verdict column.** Satisfies "no
  IMPL item" but not the sign-off's "both recognition and tag extraction": the PASS row would
  stay a HUMAN §6 item with no Basis text, which blocks accept (C6) until the human ticks a
  row the reviewer passed. Same diff size as the chosen fix (the `vi` choice is the only
  difference), so the deciding point was the sign-off instruction.
- **Verdict-column recognition with no fallback for an empty/missing Verdict cell.** Two lines
  shorter (`assemble.py:819-820`), but a malformed row that mentions NEEDS-HUMAN would vanish
  from §6 — fail-open. `test_a_row_with_no_verdict_in_the_column_still_reaches_the_human`
  pins the fallback.
- **For finding 1: make the dedup key include the raw Item cell instead of counting first.**
  Two §6 items would then show the same text, and byte-identical copies would still dedup to
  one STANDING item, so the invariant ("the constant occurs once") stays broken for copies.
  Counting first is 3 lines and covers both.

## Kept from v1, unchanged (summary — the sign-off found these fine)

- `_PROMOTABLE_ELEMENTS` (`assemble.py:69`): `judgment` minus `V` from
  `canonical_elements()`, mirroring `_GATE_ELEMENTS` (`:60`); equals `{C5, T5}`.
- `_TAG_MARKER_RE` / `_VERDICT_IMPL_RE` / `TAGS_*` (`assemble.py:80`, `:82`, `:89-91`).
- `_normalized_item_label` (`assemble.py:127`) used by the STANDING compare (`:830`, `:834`)
  and `_verdict_table_lines` (`:877`).
- `_classify_finding` (`assemble.py:293`): STANDING first, then tag strip; `[human]` or plan
  advisory ⇒ HUMAN; Verdict-cell `[impl]` on C5/T5 ⇒ IMPL; leading `[impl]` free (Check
  advisory) or bounded to C5/T5 (primary review); then the gate-element rule.
- `_items_from_artifact` policy (`assemble.py:367`); plan advisories parsed with
  `plan_advisory=True` (`:439`).
- `_needs_human` stays a 2-tuple wrapper (`assemble.py:730`) because `size_signal.py:330`
  unpacks it.
- Prompts: `leaves.py:2743-2763` (bare labels, exact Item cell, C5/T5 `[impl]`; the C5/T5
  label names come from `assemble._PROMOTABLE_ELEMENTS` at `:2756`), `leaves.py:3606`
  (every advisory bullet must carry `[impl]` or `[human]`). Role bodies:
  `agents/reviewer.md.jinja:101`, `:114`; `agents/adversary.md.jinja:25`, `:55`, `:60`.
- v1's judgment calls still hold: a primary-review bullet `[impl] — C4 …` stays IMPL via the
  gate rule (the tag is ignored, not a demotion); `[human]` beats the gate rule; plan
  advisories are HUMAN outright.

## Tests (template/tests/test_autoiterate.py)

New in this iteration, 8 tests:

- `ReviewerImplTag` (`:1842`):
  `test_a_basis_quoting_an_impl_verdict_under_pass_is_no_finding` (`:1927`, C5 and T5 — the
  reviewer's exact input; the only item left is the STANDING V row),
  `test_a_basis_quote_under_pass_does_not_auto_iterate` (`:1938`, end to end through
  `flow._maybe_auto_iterate`: halts, nothing deferred),
  `test_the_verdict_column_is_found_by_its_header` (`:1944`, reordered columns),
  `test_a_header_naming_no_verdict_column_reads_no_tag` (`:1955`),
  `test_a_row_with_no_verdict_in_the_column_still_reaches_the_human` (`:1965`),
  `test_duplicate_rows_disagreeing_on_the_tag_are_human` (`:1976`: the `[impl]` row first —
  the order v1 got wrong — then the same finding untagged, as an exact copy and in the
  prefixed form).
- `ValidationRowForms` (`:1989`):
  `test_a_second_v_row_with_the_same_basis_is_neither_standing` (`:2045`, IDENTICAL Basis,
  second row in each of the three forms, including a byte-identical copy),
  `test_a_duplicated_v_row_is_held_for_the_human_end_to_end` (`:2059`: beside C4 work the V
  text is deferred to the ledger as a HUMAN finding, not waved through as STANDING).

New symbols are reached as `assemble.<name>`, never imported at module top (brief).

## Red→green evidence (project runner)

C4 gate, `engine/scripts/run-verify.sh` with `PDCA_BUNDLE` / `PDCA_WORKTREE` set (it keeps the
test file and reverts every other hunk, `.md.jinja` included):

```
== C4 green leg: bundle test(s) with the fix applied: template/tests/test_autoiterate.py
Ran 127 tests in 1.388s
OK
== C4 red leg: bundle test(s) with the production change reverted
Ran 127 tests in 1.247s
FAILED (failures=22, errors=2)
PDCA-EVIDENCE: C4 PASS — red without the fix, green with it
```

Against v1's `assemble.py` (the rejected version; this iteration's tests kept): exactly the
8 new tests fail (13 failures with sub-tests), all 119 older tests pass. With this
iteration's `assemble.py`: 127/127 pass.

T3 suite, `engine/scripts/run-suite.sh`: root suite 24 tests OK; driver suite 2202 tests OK
(2 skipped). T2, `engine/scripts/run-docs-check.sh`: lint clean, render + link audit clean.

## Self-refutation (forced)

- **(a) Genuine red?** Yes. The C4 gate reverted the production hunks and re-ran the same
  module: 22 failures + 2 errors. Of the 8 new tests, 4 are red on base
  (`…_under_pass_is_no_finding` ×2 sub-tests, `…_found_by_its_header`,
  `…_same_basis_is_neither_standing` ×3, `…_held_for_the_human_end_to_end`). The other 4 are
  green on base by design — base never honoured a tag, so it cannot promote — and they bind
  the regressions instead: I swapped v1's `assemble.py` back in and all 8 went red (13 with
  sub-tests), then restored this iteration's file from `patch.diff` and confirmed the
  worktree diff is byte-identical to it.
- **(b) Production path?** Yes. The tests call `assemble._items_from_artifact`,
  `assemble._needs_human`, and `assemble.collect_needs_human` on real bundles, and the two
  end-to-end tests drive `flow._maybe_auto_iterate` with stub leaves, real gate commands and
  real `assemble_summary`. No copies, no mocks.
- **(c) Fixture includes the fault?** Yes. Both fixtures are the reviewer's own reproduction
  inputs (`iteration-v1/check-review.md:27-30`): `_full_review({'C5': ('PASS', 'Quoted
  NEEDS-HUMAN [impl] from an old review')})` and `_full_review()` plus `| V — Validation —
  fitness-to-purpose | NEEDS-HUMAN | fitness is the human's call |` — inside a complete
  11-row verdict table with the V row NEEDS-HUMAN, as production writes it.

## Commit-readiness

The target has no `.pre-commit-config.yaml`, no installed git hooks (none in the common git
dir's `hooks/`, no `core.hooksPath`), and no Python formatter or linter in
`.github/workflows/` (docs-check, docs, render-check, require-linked-issue only).
`git diff --check` is clean; no added line is over 100 characters.

## Not done (noted for the human)

- `size_signal.py:313-317` docstring is stale since v1 (it says the `[impl]` read uses the
  pattern `_classify_finding` strips; that is now `_TAG_MARKER_RE`, and the reviewer's main
  `[impl]` lives in the Verdict cell). Behaviour is right — the item list catches the IMPL
  row — but the file is out of scope per the brief. Worth a follow-up.
- `_ITEM_PREFIX_RE` (`assemble.py:124`) matches the element id case-sensitively, so
  `v — validation — fitness-to-purpose` stays HUMAN. Fails safe; left as v1 had it.
- `agents/code-review.md.jinja:36` still shows the untagged `- NEEDS-HUMAN — ` form (no
  "when in doubt" text). The brief names only the reviewer and adversary role bodies; the
  driver-side `_advisory_prompt` that wraps every advisory leaf does require the tag.
- The comment the code-review advisory flagged (v1 `:805`, "rendered in the matrix's own
  spelling") is reworded to say what the code does (`assemble.py:827-829`); casing is still
  kept as written.

## Housekeeping

Gate output went to `.git-verify408.log` at the worktree root (untracked, not in
`patch.diff`). I did not remove it; the driver's `git clean -ffdxq` before each gate pass
(`pdca-pdca src/pdca_harness/worktree.py:260`) clears it. The T2 gate rendered its site under
`/tmp` through its own `mktemp`; that is the gate script's doing, not a file I created.
