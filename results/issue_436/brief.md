# Brief — issue 436 / size-signal-attributable-rounds

> The Plan artifact (docs 02 §PLAN). Human-authored. Do reads ONLY this file.
> The field labels below are parsed by the driver — keep the `- **Label:** value`
> shape. The success criterion is the load-bearing field: it is the sentence
> Check tests "did this work" against.

- **Slug:** size-signal-attributable-rounds
- **Defect:** `size_signal`'s strongest rule counts ROUNDS (`rounds: 2` default,
  `template/src/pdca_harness/size_signal.py:78`) without asking what a round was spent
  on. `iteration_rounds` (`size_signal.py:121-146`) counts every `iteration-v*` archive
  after the last re-plan boundary — including rounds lost to environment faults (a stale
  host CLI, an absent oracle, a sandbox that can't bind loopback), which are churn
  evidence about the HOST, not the slice. Observed downstream (getwyrd/wyrd-pdca
  issue_652): a 66 KB / 4-file patch fired the backstop on the rounds rule alone and the
  §6 item recommended splitting the slice, when at least one round was demonstrably lost
  to a too-old `cargo-deny` (their #435); the human overrode it twice. The same
  contamination sits in the calibration corpus behind the 76% precision figure, so
  retuning the threshold cannot fix it (the issue's "measurement bug, not a threshold
  one").
- **Success criterion:** A round is excluded from `rounds` only when the archived
  evidence shows an environment fault was the SOLE recorded driver of that iterate —
  presence of an environmental result alone is not attribution, because a round can
  carry an `unverifiable` gating row AND an independent implementation finding, and that
  round is still slice churn. Concretely: `iteration_rounds` reads each counted
  archive's evidence (`check-gates.json` and the archived review/§6 record — both
  archived per round via `state.DOWNSTREAM_OF_BRIEF`,
  `template/src/pdca_harness/state.py:83-114`) and excludes a round iff (a) its gating
  rows contain NO plain gating `fail`, (b) at least one gating row is recorded
  `unverifiable` or flagged flaky (a `fail→pass` confirm-once record, the #371
  contract — see Scope), and (c) the archived review record shows no failing /
  implementation-shaped finding of its own driving the iterate. Ambiguous, missing, or
  unreadable archive evidence COUNTS the round (fail-safe: over-counting keeps the
  backstop; silent shrinkage is the failure mode `size_signal.current` already refuses).
  A round with any un-flagged gating `fail`, or all-green gates (reviewer-driven
  iterate), always counts. Because `scripts/size-calibrate` imports the same
  `iteration_rounds` (`size-calibrate:71-74,268` — ONE definition), the miner inherits
  the attribution with no second implementation. A synthetic-bundle test shows a bundle
  at 2 archives, one of them solely environment-attributed, does not fire the rounds
  rule — and a mixed-cause round (unverifiable gating row + implementation finding)
  still does.
- **Falsifiability:** RED is producible offline: a `test_size_signal.py` test builds a
  bundle with `iteration-v1/` and `iteration-v2/` where v1's archived `check-gates.json`
  records its only gating red as `unverifiable` (or `flaky`) — on current `main`
  `measure()` reports `rounds: 2` and `oversize_reasons` fires the rounds rule (verified:
  `iteration_rounds` never opens the archive's gate record, `0fbfa26`). Environment:
  plain python3 unittest, tmp-dir bundles.
- **Invariant to restore:** A signal must measure the quantity its calibration defined —
  rounds attributable to the slice, not rounds elapsed. Source: `size_signal.py:135-137`'s
  own doctrine ("the thresholds were calibrated on THIS definition, so a runtime counting
  anything else is measuring a different quantity"), and the issue's framing: a gating
  red recorded `unverifiable`, or a `fail→pass` on unchanged code, is by construction
  not a verdict on the patch.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Surfaces:** data
- **Difficulty:** medium
- **Scope:** attribution inside `iteration_rounds` (shared by the runtime backstop and
  the size-calibrate miner) + tests. IMPORTANT premise correction Do must honor: the
  issue says "#371 landed the confirm-once mechanism" — it has NOT (issue #371 is OPEN
  and no `flaky` key exists in the recorded rows at `0fbfa26`). So implement the
  consumer side of that contract defensively: treat a gating row bearing a truthy
  `flaky` key as environment-attributed (activating automatically when #371 lands its
  recorder side) and `result: "unverifiable"` as environment-attributed today; a round
  whose archive has no readable `check-gates.json` counts as before (missing evidence
  must not silently shrink the signal). The tracker's ask 2 has a report half that this
  brief dispositions rather than drops: Do MUST run `scripts/size-calibrate` before and
  after the change on the corpus locally available to it and record in `build-notes.md`
  whether (and how) the correlation/precision numbers move; the full cross-instance
  corpus (the 86 getwyrd/wyrd-pdca bundles behind the published 76%) is not reachable
  from this target checkout, so its re-derivation is explicitly deferred to #359's
  calibration loop and the PR description must say so. / out of scope: the recorder
  side of #371 (confirm-once re-run), any threshold retune (the issue explicitly
  declines it), re-mining the downstream instances' corpora (deferred to #359 as above),
  and the issue's ask 3 — the §6 text already names each fired rule with its count and
  threshold (`oversize_reasons`, `size_signal.py:240-260`), so no change is owed there.
- **Repro instruction:** In a scratch bundle create `iteration-v1/` holding a
  `check-gates.json` whose only gating red is `{"result": "unverifiable", "gating": true}`
  plus an archived review record with no failing finding (the sole-driver case), and
  `iteration-v2/` with a plain gating fail; on the target's `main` run
  `PYTHONPATH=template/src python3 -c "from pdca_harness import size_signal; print(size_signal.iteration_rounds(<bundle>))"`
  → `(2, 0)`: the environment-attributed round is charged to the slice.
- **External dependencies:** none
- **Test file:** template/tests/test_size_signal.py (append: exclusion of a round whose
  sole recorded driver is an unverifiable gating row, same for a flaky-flagged row;
  inclusion of a plain-fail round, of an all-green reviewer-driven round, AND of the
  decisive mixed case — an unverifiable/flaky gating row alongside an implementation
  finding in the archived review record; missing/garbled archive evidence counts the
  round as before. If the miner needs its own guard, extend
  template/tests/test_size_calibrate.py alongside — both ride the patch and the instance
  C4 contract runs every changed test module.)
- **Citations expected:** Do must cite path:line on the target branch for every change —
  `size_signal.py:121-146` (`iteration_rounds`), `size_signal.py:149-183` (`measure`),
  `state.py:83-114` (`check-gates.json` in `DOWNSTREAM_OF_BRIEF`, so each archive
  carries its round's gate record), `scripts/size-calibrate:71-74` and `:268` (the
  shared import), `gates.py` row vocabulary (`result` ∈ pass/fail/unverifiable/deferred).
- **Prior-art check (triage cycles):** `git -C ../pdca-harness log --oneline origin/main
  -- template/src/pdca_harness/size_signal.py template/scripts/size-calibrate` — #355/#324
  landed the brief-attribution boundary (`f616bc9`: "rounds are attributable to the
  CURRENT brief"), which is the re-plan boundary only; no environment-fault attribution
  exists. #371 (the flaky recorder) and #359 (the calibration loop) are OPEN; #435 (the
  doctor invocation-compat row) is OPEN and separate. No open PRs.
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: Auto-iterate (round 1): Check found implementation-level items only, no architectural judgment required — T3 Runtime — Decide whether the recorded driver-suite failure is a real integration regression — the referenced `./engine/scripts/run-suite.sh` is absent from the target, so its failure could not be reproduced, while the full available Python suite passed; this matters before treating the gate red as patch-caused (`template/src/pdca_harness/size_signal.py:234`).; T4 Contribution — Decide whether closed/rejected prior work duplicates this change — affected-path merged history was checked and contains only the earlier current-brief boundary, but the supplied artifacts provide no closed/rejected-work oracle; duplication would affect contribution fitness (`template/src/pdca_harness/size_signal.py:135`).
- Failing gate: T3 runtime: render/update-compat + offline driver suites (advisory) — == T3: root suite OK, driver suite FAILED (rc 1)
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).

## Iteration 2 — carry-forward (from the previous attempt)
- Sign-off rationale: Auto-iterate (round 2): Check found implementation-level items only, no architectural judgment required — T2 Shape — Decide whether to accept the supplied docs/link-audit result without an independent rerun — the configured `./engine/scripts/run-docs-check.sh` runner is absent from the target, so its green row remains provisional; this matters to release-shape confidence (`template/src/pdca_harness/size_signal.py:135`).; T3 Runtime — Decide whether the recorded driver-suite red is an integration regression or a runner-layout fault — `./engine/scripts/run-suite.sh` is absent, while all locally available Python tests passed; treating an unavailable runner as patch-caused would be unsound (`template/src/pdca_harness/size_signal.py:234`).; T4 Contribution — Decide whether closed/rejected work duplicates this contribution — affected-path merged history was checked and shows the earlier current-brief boundary but no environment attribution, while no closed/rejected-work oracle is available; duplication would change contribution fitness (`template/src/pdca_harness/size_signal.py:135`).
- Failing gate: T3 runtime: render/update-compat + offline driver suites (advisory) — == T3: root suite OK, driver suite FAILED (rc 1)
- Full previous attempt preserved in `iteration-v2/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
