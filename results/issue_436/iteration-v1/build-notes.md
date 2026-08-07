# Build notes — issue 436 / size-signal-attributable-rounds

Target: eduralph/pdca-harness @ main (`0fbfa26`), built in `$PDCA_WORKTREE`
(`/home/eddie/pdca/pdca-harness.pdca-wt-l0`). All `path:line` cites below are against
that tree with the patch applied.

## What changed and why

`iteration_rounds` counted every `iteration-v*` archive past the last re-plan boundary
(`size_signal.py:121-146` on main) without ever opening the archive's own evidence, so a
round demonstrably lost to an environment fault (a gating red the gate itself recorded
`unverifiable`) was charged to the slice and fired the rounds rule (`rounds: 2`,
`size_signal.py:78`). The fix teaches the ONE shared counter the attribution the brief
specifies; the miner inherits it through its existing import
(`template/scripts/size-calibrate:74` and `:268` — unchanged, no second implementation).

- `template/src/pdca_harness/size_signal.py:121-156` — `iteration_rounds` now filters
  the counted archives through `_environment_attributed`; the re-plan boundary
  (#355/#324, `f616bc9`) is applied FIRST, so attribution only refines rounds already
  charged to the current brief (pinned by
  `test_a_replan_boundary_still_wins_over_attribution`, tests:669).
- `size_signal.py:158-192` — `_environment_attributed`: excludes a round iff, on the
  archive's own record, (a) no plain gating `fail` (a `fail` bearing a truthy `flaky`
  key is a confirm-once fail→pass record — the #371 contract, consumer side, per the
  brief's premise correction that #371 has NOT landed; the key simply never appears
  until its recorder ships), (b) at least one gating row is `unverifiable` or flaky,
  and (c) the archived review drove nothing of its own. Any other combination — plain
  fail, all-green (reviewer-driven), mixed cause — counts.
- `size_signal.py:195-209` — `_archived_gating_rows`: reads the archive's
  `check-gates.json` (archived per round by `state.DOWNSTREAM_OF_BRIEF`,
  `state.py:82-114`); returns `None` (≠ `[]`) on missing/unreadable/malformed so "no
  evidence" can never read as "no gating rows". Scoped to GATING rows because the
  brief's (a)/(b) both say "gating row", and only a gating row can have mechanically
  driven the iterate; an advisory oracle that could not answer blocks nothing
  (pinned, tests:645).
- `size_signal.py:212-245` — `_review_drove_the_iterate`: True (count) unless the file
  is a REAL review artifact whose only finding is the standing Validation row. Findings
  are read through `assemble._items_from_artifact(…, allow_standing=True)` — the same
  parser feeding §6 and auto-iterate — deliberately reused rather than re-derived: two
  parsers for the same artifact is the #294 defect class. STANDING is the one kind that
  is not a driver (`assemble.py:26-36`: emitted every cycle, carries no signal); any
  other NEEDS-HUMAN finding, a FAIL verdict cell (`_has_fail_verdict_cell`,
  `size_signal.py:248-256`; the reviewer's mandated vocabulary is PASS/FAIL/NEEDS-HUMAN,
  `leaves.py:1624`), a leaf-status placeholder (`assemble.leaf_status` — nothing
  reviewed the attempt), or a missing/unreadable file all count the round. Lazy import
  of `assemble`, same cycle-avoidance pattern `measure` documents
  (`size_signal.py:222-224`; assemble imports size_signal at `assemble.py:17`).
- `size_signal.py:288-289` — measure()'s `rounds` comment updated to name the second
  attribution boundary.
- `template/tests/test_size_signal.py:540-676` — the new class, covering every case the
  brief's Test-file field lists (sole-driver unverifiable, flaky-flagged, plain fail,
  all-green, the decisive mixed case, missing/garbled evidence) plus the FAIL-cell,
  non-gating-row, and replan-boundary edges, and the success-criterion end-to-end
  assertion that the excluded round keeps `oversize_reasons` quiet at the default
  threshold (tests:596).

The miner needs no guard of its own: it calls the same `iteration_rounds`, and
`test_the_calibrator_uses_THIS_definition` (tests:524) already locks the single-import
invariant. `test_size_calibrate.py` is untouched (its `iteration_rounds` cases at
:240-250 use bare archives — missing evidence — which the fail-safe direction preserves
byte-for-byte).

## Design decisions / what I ruled out

1. **Where "sole driver" is decided.** Ruled out deciding it at Check time (e.g.
   `driver._size_backstop` writing an "attributed rounds" figure into
   `size-signal.json`): the calibration corpus is mined from *archives* by
   `size-calibrate`, so a runtime-only fix leaves the miner counting the contaminated
   quantity — the exact "measurement bug" the issue names. Cost sketch of that
   alternative: a second counter in `driver.py` (~40 lines) + a mirrored one in
   `size-calibrate` (~40 lines) + a new recorded key every consumer of the signal file
   must learn — vs. this patch's one function-set inside the module both already share.
   The invariant to restore is "the signal measures the quantity its calibration
   defined" (`size_signal.py:135-137`'s own doctrine), and only the shared
   `iteration_rounds` restores it for both readers at once.
2. **How strict the review test is.** I chose "any finding other than the STANDING row
   counts the round", which is stricter than the brief's minimum (it counts even a
   situational HUMAN finding, e.g. a real C5 objection). Rationale: a reviewer that
   found *anything* of its own may have driven the iterate, and the brief's stated
   failure direction is asymmetric — "over-counting keeps the backstop; silent
   shrinkage is the failure mode `current` already refuses". A consequence worth naming
   for the human: a review that merely MIRRORS the unverifiable gate as its own C4
   NEEDS-HUMAN row will keep that round counted (over-counting). Distinguishing "the
   reviewer echoed the gate" from "the reviewer found something" is textual guesswork;
   ambiguity counts, per the brief.
3. **Reusing `assemble._items_from_artifact` (module-private).** Ruled out copying its
   NEEDS-HUMAN/verdict-table parsing into size_signal (~90 lines duplicated:
   `assemble.py:435-518`) — a second parser is precisely what let a real objection wear
   the template's clothes in #294. Also ruled out promoting it to a public name in this
   patch: an API rename touches assemble + its tests for zero behaviour change; the
   in-package private use is the smaller, honest diff (Python package-internal use, one
   call site, justified in the docstring at `size_signal.py:238-241`).
4. **`flaky` semantics.** A truthy `flaky` on any gating row is environment-attributed
   AND exempts that row from being a "plain fail" — both halves from the brief's Scope
   ("treat a gating row bearing a truthy `flaky` key as environment-attributed") and
   Success criterion ("a round with any un-flagged gating `fail` … always counts"). No
   `flaky` key exists in recorded rows at `0fbfa26` (verified by grep over
   `gates.py:797-801` `_row` — the writer), so today the branch is dormant and activates
   automatically when #371 lands its recorder.

## Miner before/after (the brief's ask-2 report half)

Ran `PYTHONPATH=template/src python3 template/scripts/size-calibrate --root
/home/eddie/pdca/pdca-pdca` (the only corpus locally reachable: 27 settled bundles, 30
measurable) before and after the patch, with `--csv` for the per-bundle table.

**Result: every number is identical** — summary text, all Spearman correlations, and
the per-bundle `rounds`/`replans` columns (diff of before/after CSV: no change). Reason,
verified per bundle: all five one-round bundles here (issues 311, 316, 359, 370, 420)
archived all-green gating rows (`pass` on C4-verify and T4-contribution), i.e.
reviewer-driven iterates, which condition (b) correctly refuses to exclude. This is
direct evidence the exclusion is as narrow as specified — it moved nothing on a corpus
with no environment-lost rounds.

The published 76% rounds-rule precision rests on the 86-bundle getwyrd/wyrd-pdca corpus
(with the contaminated issue_652 round), which is NOT reachable from this checkout; its
re-derivation is deferred to #359's calibration loop, and the PR description must say so
(brief Scope — please carry this into publish).

## Refutation record (forced self-check)

- **(a) Genuine red?** Yes — reverted only the production file (`git stash push --
  template/src/pdca_harness/size_signal.py`) and re-ran
  `PYTHONPATH=src python3 -m unittest tests.test_size_signal`: 4 failures, exactly the
  exclusion-side tests (`…solely_unverifiable…`, `…excluded_round_keeps_the_rounds_rule…`,
  `…flaky_flagged_fail…`, `…replan_boundary_still_wins…`); restored, all 54 pass. The
  inclusion/fail-safe tests are green on both sides *by design* — they pin behaviour the
  fix must preserve, and the four red ones bind the objective.
- **(b) Production path?** Yes — the tests call `size_signal.iteration_rounds` /
  `measure` / `oversize_reasons` from `template/src/pdca_harness` (the module the patch
  edits); no copy, no mock. The miner leg is bound by the existing import assertion
  (tests:524) against the real `template/scripts/size-calibrate`.
- **(c) Fixture includes the fault?** Yes — every fixture bundle carries the
  environment-faulted round itself (`iteration-v1` with the `unverifiable`/flaky gating
  row **plus** a second, plainly-failing round `iteration-v2`), so the assertions
  discriminate the excluded round from the counted one inside the same bundle rather
  than curating the fault out. The brief's exact Repro (v1 unverifiable-only + clean
  review, v2 plain fail) was also run standalone: `(2, 0)` on main → `(1, 0)` patched.

## Runner + commit-readiness

- Offline driver suite (the target's documented runner, CONTRIBUTING.md:26 /
  instance INTEGRATION.md §3): `cd template && PYTHONPATH=src python3 -m unittest
  discover -s tests` → **1573 tests, OK (skipped=2)**.
- Repo-root suite: `python3 -m unittest discover -s tests` → 7 skipped in this env
  (copier not importable here; the instance's T3 gate runs it in its venv via
  `engine/scripts/run-suite.sh`).
- The target repo configures no formatter/pre-commit hooks (no `.pre-commit-config`,
  no root `pyproject`); checked the touched files for trailing whitespace (none) and
  >100-col lines (only the pre-existing `size_signal.py:36`, untouched).
- No external dependencies hit; none declared by the brief; nothing pushed, no PR.
