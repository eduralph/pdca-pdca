# PR description

## Summary
**User impact:** A slice can be accused of being oversized for time it never
wasted. When an iteration round is lost to a broken environment — a stale tool on
the host, a checker that could not run — the size backstop still counts that round
against the slice, tells the human the work is too big, and recommends splitting
it. Downstream, a modest 4-file fix triggered that recommendation twice on rounds
demonstrably lost to an outdated host tool, and the human had to override it both
times.

This PR makes the rounds count charge a round to the slice only when the archived
evidence shows the slice actually caused it — a round whose sole recorded driver
was an environment fault is no longer counted.

Reported in [#436](https://github.com/eduralph/pdca-harness/issues/436).

## What to look at
One function set in one module: the shared round counter in
`template/src/pdca_harness/size_signal.py` now reads each archived round's own
gate and review records and skips a round only when an environment fault was the
sole recorded driver. The exclusion is deliberately narrow — a round with a real
failure, a real review finding, or any ambiguous/missing evidence still counts,
so the backstop can only over-warn, never silently under-warn.

To try it: in a scratch bundle, create `iteration-v1/` whose `check-gates.json`
records its only gating red as `unverifiable` alongside a clean review, and
`iteration-v2/` with a plain gating fail; run
`PYTHONPATH=template/src python3 -c "from pdca_harness import size_signal; print(size_signal.iteration_rounds(<bundle>))"`.
On `main` this prints `(2, 0)` and fires the rounds rule; with this patch it
prints `(1, 0)` and the backstop stays quiet.

## Root cause
`iteration_rounds` (`template/src/pdca_harness/size_signal.py:121-146` on `main`)
counts every `iteration-v*` archive past the last re-plan boundary without ever
opening the archive's evidence, so rounds lost to host faults are charged to the
slice. The rounds threshold (`size_signal.py:78`, default 2, the published 76%
precision) was calibrated on that elapsed-rounds definition, so the same
contamination sits in the calibration corpus — a measurement bug, which is why
the issue declines a threshold retune.

## Fix
- `iteration_rounds` filters counted archives through a new
  `_environment_attributed` predicate (`size_signal.py:121-156` patched). The
  re-plan boundary from `f616bc9cedef34faeeac9dc334fa19d8008bab99` applies
  first — attribution only refines rounds already charged to the current brief.
- `_environment_attributed` (`size_signal.py:158-192`) excludes a round iff:
  (a) its gating rows contain no plain gating `fail`; (b) at least one gating row
  is recorded `unverifiable` or bears a truthy `flaky` key — the consumer side of
  the #371 confirm-once contract, implemented defensively since the recorder has
  not landed (it activates the day it ships), and keyed on the marker, not the
  result the re-run settled on; (c) the archived review drove nothing of its own.
- `_archived_gating_rows` (`size_signal.py:195-209`) reads the archive's own
  `check-gates.json` (archived per round via `state.DOWNSTREAM_OF_BRIEF`,
  `state.py:83-114`) and returns `None` — not `[]` — on missing/garbled records,
  so "no evidence" never reads as "no gating rows".
- `_review_drove_the_iterate` (`size_signal.py:212-245`) reuses the same parser
  that feeds sign-off (`assemble._items_from_artifact`), avoiding a second parser
  for the same artifact; any finding beyond the standing always-human row, any
  FAIL verdict cell, a placeholder, or an unreadable file counts the round.
- Because `scripts/size-calibrate` imports the same `iteration_rounds`
  (`template/scripts/size-calibrate:71-74`, call site `:268`), the miner inherits
  the attribution with no second implementation.

Calibration report (the issue's ask 2): `size-calibrate` was run before and after
on the locally reachable corpus (30 settled bundles) — every number is unchanged
and the per-bundle CSV is byte-identical, because that corpus contains zero
gating rows recorded `unverifiable` or flagged flaky: direct evidence the
exclusion is as narrow as specified. The cross-instance 86-bundle corpus behind
the published 76% figure is not reachable from this checkout; re-deriving it is
left to the calibration loop #359 landed via
`abd6f1ec5ffba69991eaacb264e74a8c9c38112e`, which retunes the thresholds as each
instance's own corpus accumulates post-fix.

## Verification
- **Claim:** a round is excluded from `rounds` only when archived evidence shows
  an environment fault was the sole recorded driver; mixed-cause, plain-fail, and
  all-green rounds still count, and ambiguous/missing evidence counts the round.
- **Checked:** `template/src/pdca_harness/size_signal.py:158-192` (the three
  conditions), `:195-209` (fail-safe `None` on unreadable evidence), `:121-156`
  (boundary-then-attribution ordering) — all on this branch; pre-fix behavior
  confirmed on `main` at `0fbfa26daf77b3cab95275f78d9f788ef9a7ac05` (the counter
  never opens the archive's gate record).
- **Test:** `template/tests/test_size_signal.py`
  (`RoundsAreAttributedToTheSliceNotTheEnvironment`, lines 540-687) — the
  brief's repro, the end-to-end backstop assertion, both #371 marker shapes
  (flaky on `fail` and on `pass`), the decisive mixed-cause round (counted, and
  still fires the rule), plain-fail / all-green / non-gating rows (counted), five
  missing-or-garbled-evidence cases (counted), and re-plan boundary precedence.
  `template/tests/test_size_calibrate.py:253-270` pins the miner inheriting the
  attribution end-to-end through the loaded script. Six of these fail pre-fix
  and pass post-fix; the full offline suite (1576 tests) is green with the patch.

Fixes #436
