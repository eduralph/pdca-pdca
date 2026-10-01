# Build notes — issue 408 / review-impl-tag-v-row

Target: eduralph/pdca-harness, worktree `/home/eddie/pdca/pdca-harness.pdca-wt` at
`4b329e4` (pdca-integrate: issue_477 — the folded base carrying 409, 371, 477 on top of
`main` @ 9405658). All `path:line` below are on that tree with the patch applied.

## What changed

### `template/src/pdca_harness/assemble.py`

- `_PROMOTABLE_ELEMENTS` (`assemble.py:69`) — `kind == "judgment"` minus `V` from
  `canonical_elements()`, mirroring `_GATE_ELEMENTS` (`assemble.py:60`). Equals `{C5, T5}`.
- `_TAG_MARKER_RE` (`assemble.py:80`) — leading `[impl]` or `[human]`. `_VERDICT_IMPL_RE`
  (`assemble.py:82`) — `NEEDS-HUMAN [impl]` in a Verdict cell. `TAGS_FREE / TAGS_BOUNDED /
  TAGS_IGNORED` (`assemble.py:89-91`) — how a leading tag is weighed, per artifact type.
- `_normalized_item_label` (`assemble.py:127`) with `_ELEMENT_OF_LABEL` (`:122`) — folds
  `--` to `—`, collapses whitespace, drops `<id> —` only when the label after it is that
  id's own label. The caller still does an exact compare.
- `_classify_finding` (`assemble.py:293`) — order is now STANDING → tag strip → `[human]`
  or plan-advisory ⇒ HUMAN → Verdict-cell `[impl]` on C5/T5 ⇒ IMPL → leading `[impl]`
  (free, or bounded to C5/T5) ⇒ IMPL → gate element ⇒ IMPL → HUMAN. Default `tags` is
  FREE, so every existing caller (`_classify_finding("[IMPL] — bug")` etc.) is unchanged.
- `_items_from_artifact` (`assemble.py:344`, policy at `:367`) — `allow_standing=True`
  (the primary review) ⇒ BOUNDED and reads the Verdict-cell tag; new `plan_advisory=True`
  ⇒ IGNORED; otherwise FREE (Check advisories).
- `collect_needs_human` passes `plan_advisory=True` for `plan-advisory-*.md`
  (`assemble.py:439`).
- `_needs_human` (`assemble.py:730`) is now a thin wrapper over the new
  `_needs_human_rows` (`assemble.py:761`), which also returns the Verdict-cell `[impl]`
  flag (`:814`, only for rows inside the mandated verdict table). The V compare uses the
  normalised label (`:807`); the `i in verdict_table` guard and the fail-closed dual-STANDING
  guard are kept as they were.
- `_verdict_table_lines` compares normalised labels (`assemble.py:851`).
- A canonical-but-prefixed Item cell renders in §6 in its normalised spelling
  (`C5 — C5 Causal adequacy` → `C5 Causal adequacy — …`), so all forms of a row read the
  same to `autoiterate._same_finding` / `FINDING_LABELS`. Non-canonical cells are kept as
  written.

### `template/src/pdca_harness/leaves.py`

- `_REVIEW_PROMPT` (`leaves.py:2743-2763`) lists bare labels (was `{elem} — {label}`),
  says to write the Item cell EXACTLY as listed, and tells the reviewer to use
  `NEEDS-HUMAN [impl]` on the C5/T5 rows only. The C5/T5 label names come from
  `assemble._PROMOTABLE_ELEMENTS` (`leaves.py:2756`) so the prompt and classifier share one
  source.
- `_advisory_prompt` (`leaves.py:3606`) drops "when in doubt, OMIT '[impl]'" and requires
  every NEEDS-HUMAN bullet to carry `[impl]` or `[human]`; untagged reads as `[human]`.

### Role prompts

- `template/agents/reviewer.md.jinja:101` — exact Item cell, no id prefix.
  `:114` — the C5/T5 `NEEDS-HUMAN [impl]` paragraph.
- `template/agents/adversary.md.jinja:60` — `[impl]` / `[human]` required, "when in doubt,
  omit" removed. `:25` and `:54-56` — the two places that showed the untagged
  `- NEEDS-HUMAN — ` form now show the tagged form, so the role body does not contradict
  itself.

## Why `_needs_human` keeps its 2-tuple shape

`size_signal.py:330` unpacks `for t, _standing in assemble._needs_human(text)`, and existing
tests (`test_autoiterate.py` `Classification`) do too. `size_signal.py` is out of scope per
the brief. Adding `_needs_human_rows` and keeping `_needs_human` as a wrapper is 3 lines; the
alternative (change the tuple, edit `size_signal.py:330` and 5 test unpack sites) touches an
out-of-scope file.

`size_signal` keeps working: its primary-review read goes through `_items_from_artifact(text,
allow_standing=True)` (`size_signal.py:332`), so it follows the bounded contract with no edit.

## Judgment calls the reviewer/human may want to look at

1. **Bounded `[impl]` on a primary-review bullet whose element is a gate cell** (e.g.
   `- NEEDS-HUMAN [impl] — C4 …`). Brief clause 1b says "otherwise the tag is stripped and
   the item is HUMAN". I read "stripped/ignored" as "classify as if untagged", so a C4 bullet
   stays IMPL (the gate-element rule), the same as the untagged C4 bullet always was. The
   literal reading would make adding `[impl]` *demote* a C4 finding to HUMAN, which looks
   unintended. Both brief-named examples (C1, Validation) give HUMAN either way and are
   tested. `test_size_signal.py:910` (a tagged T4 review bullet) is unaffected either way.
2. **`[human]` overrides the gate-element rule** — a `[human]`-tagged bullet on any
   artifact is HUMAN even if it starts with `C4`. Fail-safe direction.
3. **Plan advisories are HUMAN outright**, not just tag-ignored: an untagged plan bullet
   starting `C4 …` was IMPL via the gate rule before this patch; it is now HUMAN. That is
   what makes "plan advisories are never promoted" structural, as the code comment at
   `assemble.py:427-436` always claimed.
4. **The Verdict-cell tag is read only on rows of the mandated verdict table** (same guard as
   STANDING). An `[impl]` Verdict in a stray "concerns" table stays HUMAN.
5. **Check advisory tables** (an advisory leaf writing a table with `NEEDS-HUMAN [impl]`)
   are not read for the Verdict-cell tag — the brief scopes that to the primary review.

## Not done (out of scope, noted for the human)

- `template/agents/code-review.md.jinja:36` is another advisory role body still showing the
  plain `- NEEDS-HUMAN — ` form (no "when in doubt" text, though). The brief names only
  `reviewer` and `adversary`; the driver-side `_advisory_prompt` that wraps every advisory
  leaf does now require the tag. Worth a follow-up if the code-review role should match.
- The advisory-tag policy change (Impact section of the brief) is implemented as written;
  it is the sign-off Open question.

## Red→green evidence (project runner)

Run through the project's C4 gate `engine/scripts/run-verify.sh` (with `PDCA_BUNDLE` and
`PDCA_WORKTREE` set; it keeps test files and reverts production hunks, including the
`.md.jinja` role bodies):

```
== C4 green leg: … template/tests/test_autoiterate.py
Ran 119 tests  OK
== C4 red leg: … production change reverted
Ran 119 tests  FAILED (failures=15, errors=2)
PDCA-EVIDENCE: C4 PASS — red without the fix, green with it
```

Full T3 suite (`engine/scripts/run-suite.sh`): root suite 24 tests OK; driver suite 2194
tests OK (2 skipped). No regressions.

The first gate run went red on the green leg because of my own assertion (`_ledger(d) == []`;
the ledger file is absent, i.e. `None`, when nothing is deferred). Fixed to `assertFalse`.

## Self-refutation (forced)

- **(a) Genuine red?** Yes. The C4 gate reverted the production hunks and re-ran the same
  test module: 15 failures + 2 errors, by clause — (1) C5/T5 Verdict-cell `[impl]` →
  HUMAN today (`test_impl_verdict_on_c5_or_t5_classifies_impl` ×2,
  `test_impl_verdict_on_c5_auto_iterates_end_to_end`); `_PROMOTABLE_ELEMENTS` missing
  (`test_promotable_set_is_derived_from_the_taxonomy`, AttributeError inside the test — not a
  load failure; reached via `assemble.` attribute, as the brief requires); (1b) C1/Validation
  `[impl]` bullets → IMPL today (`test_primary_review_bullets_promote_only_c5_t5`); (1c) plan
  advisory `[impl]` → IMPL today (`test_plan_advisory_impl_is_never_promoted`); (2) the
  prefixed and `--` V forms not STANDING (`test_every_form_of_the_v_row_is_standing` ×2,
  `test_every_form_lets_an_impl_only_review_auto_iterate` ×2 — the V row gets deferred to
  the ledger), prefixed table not recognised (×2), two V rows in different forms → one wrongly
  STANDING (`test_two_v_rows_in_different_forms_are_neither_standing`); (3) the three prompt
  tests; (4) `[human]` not stripped (`test_human_tag_on_an_advisory_bullet_is_stripped_and_human`,
  KeyError on the stripped text). Pins that are green on both legs by design: untagged C5/T5
  HUMAN, C1/C3/V `[impl]` ignored on rows, Basis-cell `[impl]` ignored, mismatched `C5 —`/`T5 —`
  prefix HUMAN, free text after the label HUMAN.
- **(b) Production path?** Yes. Tests call `assemble._items_from_artifact` /
  `assemble._needs_human` / `assemble._verdict_table_lines` directly, and
  `assemble.collect_needs_human` + `flow._maybe_auto_iterate` end to end on real bundles
  (stub leaves, real gate commands, real `assemble_summary`). Prompt tests read the real
  `leaves._REVIEW_PROMPT`, `leaves._advisory_prompt(...)` and the real `.md.jinja` files.
  No copies or mocks.
- **(c) Fixture includes the fault?** Yes. The review fixture `_full_review`
  (`test_autoiterate.py:1826`) is a complete 11-row verdict table with the V row
  NEEDS-HUMAN, as production writes it, and the V-row tests substitute each of the three
  observed forms into that same table. The plan-advisory test writes a real
  `plan-advisory-*.md` into a real bundle and reads it through `collect_needs_human`.

## Commit-readiness

The target repo has no `.pre-commit-config.yaml`, no installed git hooks, and no
formatter/linter in `.github/workflows/`. `git diff --check` is clean; no added line is over
100 columns (the file already has a few pre-existing longer lines).

## Housekeeping

During the second gate run I redirected its output to `/tmp/verify408.log`, which is outside
the worktree and bundle roots. I did not remove it (cleanup is the harness's job); it is a
plain log of the gate output and nothing reads it.
