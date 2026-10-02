# Design proposal — issue 477 / size-signal-discount-human-class-rounds

- **Slug:** size-signal-discount-human-class-rounds
- **Kind:** enhancement (design proposal)
- **Goal:** the size backstop's rounds rule stops charging a slice for a round whose only
  recorded drivers are things no rebuild can change: an environment fault (already handled
  by #446) or a reviewer finding on a gate the harness deliberately deferred. Any
  builder-actionable or ambiguous evidence still counts the round, so the backstop can only
  warn less on noise, never go quiet on real churn.
- **Success criterion:** all hold in `template/tests/test_size_signal.py` (appended to the
  #446 class `RoundsAreAttributedToTheSliceNotTheEnvironment`, `:540`), run by the C4 gate,
  through `size_signal.iteration_rounds`:
  (1) **Deferred-gate finding is not slice churn.** An archive whose gating rows are all
  `pass` except a `deferred` row for element T4, and whose primary review
  (`check-review.md`) raises NEEDS-HUMAN only on the T4 row and the standing Validation row,
  is NOT charged (the two-round bundle reads `(1, 0)`, not `(2, 0)`). The match is by
  element: the §6 item text's leading element id, read with `assemble._ELEMENT_RE`
  (`assemble.py:54`, `^(C[1-5]|T[1-5]|V)\b` on `NeedsHumanItem.text`), equals the
  `element` of an archived gate row whose `result` is `deferred`. Fixture rows use the
  Item-cell form the reviewer writes, starting with the id (`| T4 Contribution … |
  NEEDS-HUMAN | … |`); a NEEDS-HUMAN row whose Item cell has no leading id keeps the round
  charged (tested). The deferred-element set is read from ALL archived gate rows, gating or
  not (a withheld row is withheld either way); the `fail` / `unverifiable` / `flaky` checks
  stay on gating rows only, as today (`size_signal.py:202`). Tested: a non-gating
  `deferred` T4 row still discounts.
  (2) **Still counted — every one of these keeps the round charged:** a plain gating
  `fail`; a review NEEDS-HUMAN on any element whose gate row is not `deferred` (e.g. T3,
  C5, T5); a FAIL verdict cell; a review placeholder or missing/unreadable review; missing
  or malformed `check-gates.json`; a review whose ONLY NEEDS-HUMAN item is the standing
  Validation row with no environment row and no deferred-gate finding (nothing recorded
  explains the round, so it counts — V is a constant, not a driver; see Open questions, this
  is a choice the human must confirm); and any archived advisory artifact
  (`check-advisory-*.md`) that carries an IMPL-kind item (as classified by
  `assemble._items_from_artifact`, so it follows the tag contract whatever #408 lands) or is
  a leaf-status placeholder. A plain `- NEEDS-HUMAN — …` advisory bullet (HUMAN kind) does
  NOT charge the round (tested on both the new path and a #446 round).
  (3) **One rule, applied to #446 rounds too.** The advisory check in (2) applies to
  environment-attributed rounds as well: an archive with a solely-`unverifiable` gating red
  and a clean review, but an advisory `- NEEDS-HUMAN [impl] — …` finding, is now CHARGED;
  the same archive with only a plain `- NEEDS-HUMAN — …` advisory bullet is still
  discounted (so #446 keeps working on instances that configure advisories).
  This is a deliberate tightening in the safe direction (today it is discounted because
  `_review_drove_the_iterate`, `size_signal.py:205`, reads only `check-review.md`).
  (4) Every existing test in `test_size_signal.py` passes unchanged, including the #446
  class (`:540-700`) and `test_the_calibrator_uses_THIS_definition` (`:524`) — the
  calibrator keeps sharing `iteration_rounds`.
- **Falsifiability:** RED today on this host. Clause 1: `_environment_attributed`
  (`size_signal.py:151`) requires an `unverifiable` or `flaky` gating row (`:183`), so an
  all-pass-plus-deferred round is charged and the test reads `(2, 0)`. Clause 3: the
  advisory file is never read, so that round is discounted today and the test reads
  `(1, 0)` instead of `(2, 0)`. Suite:
  `cd template && PYTHONPATH=src python3 -m unittest tests.test_size_signal`, run by
  `./engine/scripts/run-verify.sh` (gating C4; keeps the appended tests, reverts production
  hunks). Tests go through `size_signal.iteration_rounds` only (existing API), so the red
  leg can never fail at import.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Conflicts with:** 409
- **Ordering note:** 409 adapts fixtures in `test_size_signal.py` (the #324 composition), a
  shared file with no build-on dependency, so different waves; the scheduler puts 409 first.
  408 builds after this slice; once it lands, a prefixed V row (`V — Validation — …`) reads
  as STANDING here too, because `_review_drove_the_iterate` goes through
  `assemble._items_from_artifact`. Until then such a row keeps the round counted (the safe
  direction), so no dependency is needed. The only file overlap with 371 is
  `template/pdca.toml.jinja`, in separate sections (the size-signal comment here, `[gates]`
  there), which the wave fold merges hunk by hunk; so the two share a wave. Computed batch order (`pdca-pdca waves 408 409 371 477`): [409] → [371, 477] → [408].
- **Scope:** the round-attribution rule in `size_signal.py` (`_environment_attributed` /
  `_review_drove_the_iterate` or their replacement: one function that decides whether an
  archived round's recorded drivers were all non-slice), its module/function docstrings,
  and the `[driver.size_signal]` comment in `template/pdca.toml.jinja` if it describes what
  is discounted. / out of scope: how `assemble` classifies a NEEDS-HUMAN on a deferred gate
  cell for auto-iterate (today IMPL via `_ELEMENT_RE`; see Open questions); treating a T3
  NEEDS-HUMAN about a missing host tool as environmental (not decidable from the archive —
  it keeps counting); threshold defaults; the calibrator script (it shares the function).
- **Difficulty:** medium
- **External dependencies:** none
- **Test file:** template/tests/test_size_signal.py
- **Citations expected:** Do must cite path:line on the target branch for every change.
  Peer callsites on `main` @ 9405658 (this bundle builds on a later wave's folded base, so
  lines will have moved — locate by symbol): `iteration_rounds` `size_signal.py:116`;
  `_environment_attributed` `:151` (conditions `:181`, `:183`, `:185`);
  `_archived_gating_rows` `:188` (returns gating rows only — the deferred lookup needs the
  row's `element` and `result`; T4-contribution is gating on this project);
  `_review_drove_the_iterate` `:205` (reads through `assemble._items_from_artifact`, one
  parser — keep it that way, and read advisories the same way `collect_needs_human` does,
  `assemble.py:269-277`); `_has_fail_verdict_cell` `:241`; the `deferred` result contract
  `gates.py:47-60`. Test fixtures to extend: `CLEAN_REVIEW`, `_row`, `_archive`,
  `_two_round_bundle` in `test_size_signal.py:555-590` (`_archive` needs an optional
  advisory file).
- **Prior-art check (triage cycles):** `git -C ../pdca-harness log --oneline origin/main
  -n 8 -- template/src/pdca_harness/size_signal.py` → 5ced9bd, 363ac72 (#446, the
  environment discount this extends), f616bc9, 7fe6aa0, 40c3e1c, 4fe57ff, cad9601 (#324).
  No discount for deferred-gate findings on main. Related: 07766ed records the Check-time
  T4 row `deferred`, and the reviewer prompt tells it to write N/A for deferred rows
  (`leaves.py:2735-2740`); that removes much of the noise at the source, and this slice
  covers the reviewer that still raises it. Closed-unmerged PRs touching `size_signal.py`:
  none. No open PRs.
- **Disposition hint:** new-feature

## Motivation

On pdca-pdca, the rounds rule fired on 4 of 6 cycles frozen 2026-08-06..09 (issues 453,
456, 457, 468), each at rounds = 2 / threshold 2, and each slice merged without a split.
Checked against their archives (`results/issue_4xx/iteration-v*/`): every archived round
had all gating rows `pass`, and the review's NEEDS-HUMAN rows were T4 (contribution
artifacts withheld from the reviewer by design), Validation, and often T3 (a missing
`copier`). None was an implementation finding. #446 discounts only rounds with a recorded
environment fault, so these were all charged.

These archives predate 07766ed, so their T4 row reads `pass`, not `deferred`. This change
will therefore not re-classify them; it applies to rounds recorded from now on.

**Expected real-world effect — measured, and small.** Across the 82 archived rounds in
pdca-pdca `results/` (2026-09-30), 39 have a `deferred` gate row and no other gating
failure. In none of them (0 of 39) did the reviewer raise NEEDS-HUMAN on the deferred
element: since 07766ed the prompt tells it to write N/A there, and it does. So the new
deferred-gate path is a **defensive rule** for a reviewer that ignores its prompt, not a
fix that will lower today's counts. What those 39 rounds do carry: 20 are T5 + Validation,
12 are Validation only, the rest mix in C1/C3/C4/T1. The 12 Validation-only rounds are the
ones the issue's "at minimum the always-human validation row" would discount; this brief
keeps charging them (see Open questions). The T3
rows keep counting on purpose, because nothing in the archive proves they were
environmental.

## Design

A round is not charged iff all hold:
(a) no plain gating `fail` (unchanged);
(b) at least one recorded non-slice driver: an `unverifiable` or `flaky` gating row
(unchanged), OR a primary-review NEEDS-HUMAN on an element whose archived gate row is
`deferred` (new);
(c) every primary-review finding is either the STANDING row or on a deferred-gate element;
no FAIL verdict cell; the review is a real artifact (tightened from "only STANDING");
(d) no archived advisory carries an IMPL-kind item or is a placeholder (new).
Anything missing, unreadable or malformed counts the round.

## Alternatives considered

- Discount every round whose review has only V + gate-cell findings: too wide. A T3 or C4
  NEEDS-HUMAN can be a real slice problem.
- Key on the row's Basis text ("withheld", "not among the permitted inputs"): prose
  matching, which the #294 rule forbids.
- Discount a round whose only review finding is the standing Validation row (the issue's
  "at minimum" suggestion): not taken by default. With all gates green and only V raised,
  nothing recorded explains why the round was iterated — it was a human `iterate-*` on
  reasons outside the archive, which may be real slice churn (V's Basis cell can hold a
  genuine fitness-to-purpose objection). Counting is the fail-safe. It is, though, the only
  variant that would change real counts today (12 of 39 rounds above), so the human decides.
- Charge on ANY advisory NEEDS-HUMAN: rejected. Advisory prompts tell leaves to use plain
  `- NEEDS-HUMAN —` bullets for anything a human must judge, so most rounds on an instance
  with advisories would carry one, which would cancel both this discount and #446.
- Leave advisories unread: then a round driven by an advisory `[impl]` finding would be
  discounted under the new rule (b), which is exactly the under-warning the issue forbids.

## Impact & compatibility

The rounds count can go down (deferred-gate noise) or up (advisory findings on a
previously discounted #446 round). `scripts/size-calibrate` shares the function, so a
re-calibration after this lands measures the new quantity. That is the intent: one
definition.

## Open questions

- DECIDED (human, Plan, 2026-09-30): keep charging Validation-only rounds, as clause (2)
  states. Measured stake noted: 12 of 39 recent all-green archived rounds stay charged.
- Whether (3), the tightening of #446 rounds, is wanted. It is the safe direction and
  keeps one rule; the alternative is to apply the advisory check to the new path only.
- The upstream cause of issue_453's wasted rounds was auto-iterate treating the T4
  NEEDS-HUMAN row as IMPL (T4 is a gate cell). That classification is not in this slice;
  see the note on #408.

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.

Plan-review response: findings addressed in the brief — V-only rounds now an explicit
Alternative and Open question for the human, with the measured stake (12 of 39 rounds);
the real-world effect of the deferred-gate path measured (0 of 39 rounds) and stated as a
defensive rule (Motivation); rule (d) narrowed to IMPL-kind advisory items plus
placeholders, with tests that a plain advisory bullet does not charge a new-path or #446
round (clauses 2, 3, Design); deferred lookup reads all rows, gating or not, pinned by a
test (clause 1); element match via `_ELEMENT_RE` on item text with the fixture format and
a no-id negative case pinned (clause 1).

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: Keep the design; fix the implementation so it honours its own fail-safe ("anything missing, unreadable or malformed counts the round"). These cases are most likely on a new machine where a dependency has not been captured yet, so gate records can come out incomplete or odd — exactly when the backstop must NOT go quiet. 1. Malformed gate-row results (reviewer C3 FAIL): `_environment_attributed` only rejects the literal `fail`, so a gating row whose `result` is missing, `null` or an unknown string is ignored, and a deferred-T4 finding then discounts the round (2,0) → (1,0). Validate every gating row's `result` against the known set (`pass` / `deferred` / `unverifiable`, or `fail` with truthy `flaky`); anything else counts the round. Add tests for missing, null and unknown-string results beside a deferred T4 finding. 2. Element keyed too loosely (code-review §6 item, `size_signal.py:204-210`): an element counts as deferred only if NONE of its rows (gating or not) is `fail` / `unverifiable` / malformed — a deferred row must not shelter a live failing sibling of the same element (e.g. T2-docs vs host-ci-docs). Add a test for an element whose rows disagree. Optional, low stakes: a primary-review `- NEEDS-HUMAN [impl] — T4 …` bullet should keep the round charged, as the advisory path does; `_review_drove_the_iterate` is now test-only — document or remove it.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  Keep the design; fix the implementation so it honours its own fail-safe ("anything missing,
  unreadable or malformed counts the round"). These cases are most likely on a new machine where
  a dependency has not been captured yet, so gate records can come out incomplete or odd — exactly
  when the backstop must NOT go quiet.
  1. Malformed gate-row results (reviewer C3 FAIL): `_environment_attributed` only rejects the
     literal `fail`, so a gating row whose `result` is missing, `null` or an unknown string is
     ignored, and a deferred-T4 finding then discounts the round (2,0) → (1,0). Validate every
     gating row's `result` against the known set (`pass` / `deferred` / `unverifiable`, or `fail`
     with truthy `flaky`); anything else counts the round. Add tests for missing, null and
     unknown-string results beside a deferred T4 finding.
  2. Element keyed too loosely (code-review §6 item, `size_signal.py:204-210`): an element counts
     as deferred only if NONE of its rows (gating or not) is `fail` / `unverifiable` / malformed —
     a deferred row must not shelter a live failing sibling of the same element (e.g. T2-docs vs
     host-ci-docs). Add a test for an element whose rows disagree.
  Optional, low stakes: a primary-review `- NEEDS-HUMAN [impl] — T4 …` bullet should keep the round
  charged, as the advisory path does; `_review_drove_the_iterate` is now test-only — document or
  remove it.
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
