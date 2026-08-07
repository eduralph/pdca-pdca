# Build notes — issue 332 / autoiterate-soft-hard-defer (folds #335)

Builder rationale — withheld from the reviewer; for the human at sign-off.

Target: eduralph/pdca-harness @ main (base `710ec54`), built in the worktree
`/home/eddie/pdca/pdca-harness.pdca-wt-l1`. All `path:line` cites below are against that
tree with the patch applied (pre-patch cites say "was").

## What was built — the five criterion clauses + the #335 fold

### (1) Soft/hard round budgets

- `config.py:276-285` — `soft_auto_iters: int | None = None`; parsed + clamped at
  `config.py:610-622` (`[driver].soft_auto_iters`, `PDCA_SOFT_AUTO_ITERS` override,
  clamped into `[1, max_auto_iters]` *after* the hard budget's own clamps). Unset ⇒
  `None` ⇒ soft == hard (`autoiterate.soft_budget`, `autoiterate.py:134-146`), so a
  rendered instance reproduces today's behaviour byte-for-byte — locked by
  `ConfigPlumbing.test_soft_auto_iters_unset_defaults_to_the_hard_budget` and
  `SoftHardRounds.test_soft_unset_reproduces_the_hard_only_behaviour`.
- `auto-iterate.json` extended to `{"count": n, "impl_counts": [...]}`:
  `autoiterate.bump` (`:124-131`) records the per-round open-IMPL count;
  `autoiterate.impl_counts` (`:111-121`) and `count` (`:102-108`) are tolerant of the
  old `{"count": n}` shape (test: `test_bump_records_per_round_impl_counts_and_count_stays_tolerant`).
- The rule itself is one function, `autoiterate.budget_verdict` (`:149-179`), consumed by
  `flow._maybe_auto_iterate` (`flow.py:270-277`): hard cap first; inside the soft window a
  round fires only if the current IMPL count did not increase over the last recorded one.
  The worked example (soft 3 / hard 5: n≤3 always; 3<n≤5 iff not increased; n>5 never) is
  table-driven in `SoftHardRounds.test_worked_example_soft3_hard5`.
  **Fail-toward-human choice:** an old-shape file inside the soft window has no history to
  prove convergence, so it declines (`budget_verdict`'s `prev is None` branch) rather than
  guessing — the bundle halts at AWAITING_SIGNOFF exactly like an exhausted budget.

### (2) Reviewer-stated `[impl]` on judgment cells

- `assemble._PROMOTABLE_ELEMENTS` (`assemble.py:51-63`) = judgment-kind minus V, derived
  from `gates.canonical_elements()` exactly the way `_GATE_ELEMENTS` is (brief cite
  `assemble.py:50`) — resolves to `{C5, T5}`, asserted against the matrix in
  `ImplTagPromotion.test_promotable_set_is_judgment_minus_v_from_the_canonical_matrix`.
- `_needs_human` now returns `(text, standing, impl_tag)`; the tag is read from the
  **verdict cell** (`assemble.py:519` — `"[impl]" in cells[vi].casefold()`).
- `_classify_finding(…, impl_tag=)` (`assemble.py:168-210`): STANDING is checked **before**
  the tag (`:201-202` before `:207-208`), so a tagged V row stays STANDING
  (`test_a_tagged_v_row_stays_standing`); tag on C1/C3 ignored (element not promotable);
  untagged bullets/rows classify HUMAN unchanged (fail-safe). A `[human]` marker
  (`_HUMAN_MARKER_RE`, `:74`) is stripped and classifies HUMAN — the explicit spelling of
  the fail-safe the prompts now require.
- Never-promotable deterministic items: unverifiable gates / declared deps / unregistered
  deps / size item are constructed `HUMAN` outright and never pass the tag parse
  (`collect_needs_human`, `assemble.py:230-301`) — pinned by
  `ImplTagPromotion.test_deterministic_items_are_never_promotable`.

### (3) `eligible()` = "≥1 IMPL", deferral ledger

- `autoiterate.eligible` (`autoiterate.py:75-100`): `any(IMPL)`, HUMAN no longer vetoes;
  empty §6 and HUMAN-only still halt. **One deliberate carve-out the brief does not name:
  the size backstop item (#324) still vetoes** (`:96-98`). Deferring it would invert
  #324 (the backstop is evidence that *further rebuilds are the wrong move*, not a finding
  to file for later), and the target's own suite pins that invariant
  (`test_size_signal.py::DisqualifiesAutoIterate` — "the backstop must STOP the rebuild
  loop, not feed it"). The carve-out preserves those tests verbatim; the only size-signal
  test edited is `test_an_ordinary_human_finding_declines_without_the_extra_line`, whose
  premise (an ordinary HUMAN finding beside IMPL declines) is exactly what #332
  re-specifies — it is now the HUMAN-only silent decline.
- Ledger: `deferred-human.json` (`autoiterate.LEDGER_FILE`, `:62-69`). Written by
  `write_decision` (`:339-352`) → `defer` (`:237-250`) for HUMAN-kind items only (STANDING is re-emitted
  every cycle; IMPL goes to the builder). NOT in `DOWNSTREAM_OF_BRIEF`; added to
  `state.CYCLE_EVIDENCE_ONLY` (`state.py:94-113`) with the archive-vs-evidence rationale —
  both pinned by `DeferredFindings.test_ledger_is_cycle_evidence_and_never_archived`.
- Merge into §6: `collect_needs_human` appends `autoiterate.deferred_items(d, …)`
  (`assemble.py:288-296`; dedupe normalized in `autoiterate.py:253-259`) — so every
  deferred finding is a `- [ ]` under the C6 guard at handover
  (`test_round_one_human_finding_still_in_section6_at_handover`,
  `test_deferred_finding_survives_the_archive_and_reenters_section6`). Local import in
  `collect_needs_human` because `autoiterate` imports `assemble` at module level (cycle
  otherwise) — same pattern as the existing `dependency_halt` local import at
  `assemble.py:249`.
- `rationale` (`autoiterate.py:181-201`): names IMPL texts, states the deferral as a
  **count** only. The two clauses of criterion (3) — "states what was deferred" and
  "carries IMPL items only into the builder's carry-forward" — conflict if the deferred
  *texts* appear, because the rationale line IS what
  `driver._carry_forward_into_brief` folds into the brief (§9 delta). Count-not-texts
  satisfies both and preserves the #294 property; asserted end-to-end in
  `test_deferred_texts_never_reach_the_builder_carry_forward` (brief contains the C4
  finding and "Deferred 1 human finding(s)", never "guards the symptom").
- `test_empty_section6_halts_and_never_auto_accepts` passes byte-unchanged, as required.

### (4) The V-row match, three production forms

- `assemble._normalize_item_label` (`assemble.py:88-100`): strip an optional leading
  `<element-id> —` prefix (`—` or ASCII `--` as separator), fold `--`→`—`, collapse
  whitespace, casefold — comparison **exact after** normalization (#294's rule intact:
  any suffix still makes the row a real objection —
  `VRowForms.test_comparison_is_exact_after_normalization_never_prefix_matching`).
- Applied at *both* comparison sites, deliberately: the row match (was the casefolded
  exact match at `assemble.py:438-439`, now `:516-518`) *and* the mandated-table
  detection `_verdict_table_lines` (`:556-558`) — a fully prefixed table (the shape the
  prompt's own "`<id> — <label>`" listing induces) must still be recognised as the
  mandated table or its V row could never be STANDING
  (`test_a_fully_prefixed_table_is_still_the_mandated_table`). The fail-closed
  dual-STANDING guard (was `:445-447`) is untouched.
- Why (4) matters *more* under (3): a mis-read constant no longer halts — it would be
  **deferred into the ledger forever**. `test_no_production_form_is_ever_deferred_to_the_ledger`
  pins that interaction.
- Prompts aligned in the same pass: `_REVIEW_PROMPT` (`leaves.py:1418-1465`, the tag at `:1435-1441`) now states
  the exact Item-cell forms tolerated **and** the C5/T5 `NEEDS-HUMAN [impl]` verdict tag;
  `_advisory_prompt` (`leaves.py:2017-2038`) replaces "when in doubt, OMIT '[impl]'" with
  the required `[impl]`/`[human]` pair + untagged→HUMAN fail-safe; role prompt bodies
  `template/agents/reviewer.md.jinja`, `adversary.md.jinja`, `code-review.md.jinja`
  updated in step (the `.claude/agents/*.jinja` wrappers `{% include %}` these bodies, so
  the #274 sync guard is satisfied by construction).

### (5) The #335 fold — retirement, exact-first two-tier

- `autoiterate.retire_cleared` (`autoiterate.py:281-337`), invoked from the driver's
  ITERATE_DO / ITERATE_PLAN transitions **before** the archive moves SUMMARY.md
  (`driver.py:119-131`, `driver._retire_deferred` `:270-283`, best-effort — never breaks
  the transition; an auto round never ticks a box, so it retires nothing by construction,
  `test_an_auto_round_never_retires_anything`).
- Exactly the instance shape (getwyrd/wyrd-pdca@e4fdf3b): a `protected: set[int]`
  computed once before the tick loop (`:315-322`); the tick guard is
  `len(hits) == 1 and hits[0] not in protected` (`:326-330`). Protection assignment is
  exact-first two-tier: an open row verbatim-equal (normalized-exact) to an entry
  protects that entry ALONE; an edited open row (verbatim owner of nothing) protects
  every `_same_finding` match — even against an exact tick. Tick side stays exact-first
  fuzzy-fallback, ambiguity fail-closed.
- `_same_finding` (`autoiterate.py:209-219`): normalized equality or containment — ONE
  relation shared verbatim by both sides, which is what test (b) pins.
- The three mandated tests + extras ship in `LedgerRetirement`:
  (a) `test_335_repro_an_annotated_open_row_protects_its_entry`;
  (b) `test_matcher_drift_guard_every_tick_shape_also_protects_when_open` (four edit
  shapes × both sides);
  (c) `test_an_edited_open_row_matching_two_near_twins_protects_both`;
  plus `test_an_exact_tick_beats_an_open_near_twin` (the drain property) and
  `test_an_ambiguous_tick_retires_nothing`.
- **Both rejected shapes demonstrated red** (run in this session, then reverted to the
  correct implementation):
  - symmetric-fuzzy variant (`any(_same_finding(entry, o) for o in still_open)`):
    FAILS `test_an_exact_tick_beats_an_open_near_twin` (1 failure) — the
    permanently-unclearable pair;
  - pre-fix instance shape (fuzzy select / exact-text exclude): FAILS the (a) repro,
    both "open" sides of (b) with annotation shapes, and (c) (4 failures).
  No variant passes both families — the falsifiability clause holds literally.

## Alternatives considered / ruled out

- **Deferring the size-backstop item like any HUMAN finding** (the literal reading of
  criterion (3) with no carve-out): rejected — it inverts #324 by design intent (the
  comments at `size_signal.py:39-49` and `assemble.py` say the veto *is* the mechanism)
  and goes red on 4+ existing assertions in `test_size_signal.py`
  (`DisqualifiesAutoIterate`, `ReachesSectionSix`). Cost of the carve-out: 2 lines in
  `eligible()` plus one test each side. Cost of the alternative: rewriting ~6 tests to
  assert the backstop *feeds* the loop it exists to stop.
- **Retirement at sign-off apply (`flow._apply_decision`) instead of the driver's
  iterate transition**: rejected — `pdca run` on an ITERATE_DO bundle would then archive
  ticks without retiring (the transition is reachable without flow), and the driver
  transition is where SUMMARY is last readable pre-archive. Cost: same line count either
  way; the driver placement covers both entry points.
- **A 2-tuple `_needs_human` with the tag smuggled into the text** (avoiding the
  signature change): rejected — it would re-create the "two sources of truth" bug class
  #294 fixed (the classifier re-deriving caller facts from text); the 3-tuple change
  touches 6 unpack sites, all in one file + tests.
- **Raising `max_auto_iters` alone / prefix-matching the V row**: already rejected by
  the brief's own alternatives section; not revisited.

## Verification (the three forced questions)

- **(a) Genuine red?** YES. With all source changes stashed (tests kept), the named test
  file fails: `Ran 95 tests … FAILED (failures=17, errors=43)` — failures/errors span all
  five clauses (soft-budget API missing, tag not promoted, deferral fires nothing, V
  forms not standing, `retire_cleared`/ledger absent). With the patch: `Ran 95 … OK`.
  Additionally the two wrong retirement shapes were substituted in and each goes red on
  the exact tests the brief predicts (see (5) above), then the correct shape was restored
  and the suite re-ran green.
- **(b) Production path?** YES. The tests drive the real `pdca_harness` modules —
  `flow._maybe_auto_iterate` → `assemble.collect_needs_human` → `autoiterate.*` →
  `driver.run_issue`/`advance` — through the project's own runner
  (`cd template && PYTHONPATH=src python3 -m unittest …`, the same
  `python -m unittest discover -s tests` the template Makefile's `check` target runs).
  No stand-ins; the only mocks are the pre-existing fixture patterns of this suite
  (stubbed leaves, per the file's own convention).
- **(c) Fixture includes the fault?** YES. The deferral tests build bundles whose §6
  actually contains the vetoing HUMAN finding beside the IMPL one (the 13.5% blocker
  shape); the #335 tests construct the exact field-report fixtures (annotated-unticked
  row + similar ticked new finding; near-twin pair; edited row matching two entries) —
  the failing element is in the fixture, not curated out.

Full offline suite: `python3 -m unittest discover -s tests` → `Ran 1463 tests … OK
(skipped=2)` (the two skips are the render-only guards that always skip in the template
checkout). Docs lint (the host CI's `docs-check`): `python3
docs/publishing/tools/lint_docs.py` → OK (docs/07-crosscutting.md was edited). All four
edited `.jinja` templates parse under Jinja2. No pre-commit hooks / formatter config
exist in the target repo (checked `.git/hooks`, `core.hooksPath`, no
pyproject/ruff/flake8); CI = docs lint (run, green) + the unittest suites (run, green) +
render-check (`copier` is not installed on this host — see limitation below).

## Limitations / notes for sign-off

- **render-check not run locally**: the host lacks `copier`, so
  `tests/test_render_and_run.py` / `test_update_compat.py` (the render CI) could not be
  executed here. Risk is confined to the four `.jinja` files, whose edits are prose /
  TOML comments and which parse cleanly under Jinja2; the draft-PR CI will run the real
  check. Not raised as a NEEDS-HUMAN external dependency: it blocks no gate of *this*
  project's Check config and the evidence gap is covered by PR CI before merge.
- The deferral means a leaf-status placeholder item ("leaf did not run …") deferred
  beside an IMPL finding can linger in §6 after a later round's leaf ran fine — the
  loss-proof direction (lingering visible > lost); the human ticks it at handover and
  retirement drains it.
- Scope note: `autoiterate.DECISION` remains the single `iterate-do` token; input-cell
  routing to `iterate-plan` stays the issue's declared follow-up, untouched.
