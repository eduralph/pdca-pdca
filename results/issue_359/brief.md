# Design proposal — issue 359 / act-sizing-calibration

> Plan artifact (design-proposal form). Do reads ONLY this file.

- **Slug:** act-sizing-calibration
- **Kind:** enhancement (design proposal)
- **Goal:** keep the sizing thresholds honest as the corpus grows: a sizing column
  (estimate vs outcome) in the Act index, a documented retuning procedure for
  `[driver.sizing]` from a fresh `size-calibrate` run, and `model_weight` as a
  config value revisited at Act cadence rather than a constant. The prerequisite
  (#324's Check-time backstop / `size-signal.json`) is merged on target main
  (`cad9601`; `size_signal.py` + `template/scripts/size-calibrate` exist).
- **Success criterion:** (a) `pdca act index` renders a sizing column per frozen bundle
  — the a-priori estimate beside the measured outcome (from the bundle's recorded size
  signal), with a graceful blank for bundles predating the signal; (b) a documented
  retuning procedure exists (docs/ or the config comment block) walking
  `size-calibrate` output back into `[driver.sizing]`; (c) `model_weight` is read from
  `[driver.sizing]` config (defaulting to current behaviour) with its Act-cadence
  review noted where it is defined; (d) the PR reports whether mining archived
  `iteration-v*/brief.md` files changes the correlations, or records an explicit
  decision not to. (a)–(c) demonstrable by C4-verify via the offline driver suite; (d)
  is a PR-prose obligation checked at sign-off, not by a gate.
- **Falsifiability:** the offline driver suite on this host. RED now: a test building a
  frozen bundle with a recorded size signal and asserting the rendered index carries
  the estimate-vs-outcome column fails on current `main` — `act.render_index`
  (`act.py:554`) renders only §6/§7/§10 lines, and `grep model_weight
  template/src/pdca_harness/config.py template/src/pdca_harness/sizing.py` is empty.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Depends on:** none
- **Conflicts with:** none
- **Ordering note:** the issue's stated dependency #324 is already merged upstream, so
  this schedules freely in the batch. Sole heavy file is `act.py`, which no other
  bundle in this batch modifies.
- **Difficulty:** medium
- **Scope:** the three deliverables + the PR-reported mining decision, as in the
  criterion. The *retuning itself* (changing shipped default weights) is explicitly not
  in scope — the corpus that would justify new numbers accumulates per instance; this
  change builds the loop that keeps them honest. / out of scope: #355-class feature
  work (landed, `767da25`); any change to the sizer's estimate computation or the
  Check-time backstop.
- **External dependencies:** none
- **Test file:** template/tests/test_act_index_sizing.py
- **Citations expected:** Do must cite path:line on the target branch for every change.
  Peer callsites: `act.index` (`act.py:530`) and `render_index` (`act.py:554`)
  for the column; `size_signal.py` for what a bundle records (the outcome side);
  `sizing.py` DEFAULT_* + `config.py:319-322` (`[driver.sizing]` dict passthrough) for
  where `model_weight` lands; `template/scripts/size-calibrate` for the procedure the
  docs describe.
- **Prior-art check (triage cycles):** `git -C ../pdca-harness log --oneline origin/main
  -- template/src/pdca_harness/act.py template/src/pdca_harness/sizing.py
  template/src/pdca_harness/size_signal.py` — #320/#321/#324/#355 landed (estimator,
  guard, backstop, a-priori features); no sizing column in `act.py`, no `model_weight`
  key, no retuning docs. Not fixed, not in flight.
- **Disposition hint:** new-feature

## Motivation

0.56 demonstrated the failure this prevents: published precision moved 67%→62% because
a parsing fix changed what the estimator measured — an artifact number nobody would have
caught without a manual re-derivation. A number that only moves when someone re-derives
it by hand will be wrong for a long time before anyone finds out; the Act index is where
cross-cycle patterns are already reviewed.

## Design

See criterion. The estimate side comes from the brief-derived a-priori estimate, the
outcome side from the recorded size signal (#324); the column is a join on the bundle.

## Alternatives considered

- Leaving it to `size-calibrate` runs by hand: exactly the drift-goes-unnoticed mode the
  0.56 episode showed.
- Shipping retuned weights now: tuning against a mostly-empty corpus — rejected by the
  issue itself.

## Impact & compatibility

Additive column + config key with today's behaviour as default. No estimator behaviour
change.

## Open questions

- Whether the mining of `iteration-v*/brief.md` (corpus-quality note) is worth doing in
  this change or explicitly deferred — the PR must state the decision either way (DoD).

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a draft PR
MAY happen during the cycle. The PR MUST NOT be marked ready before sign-off accepts.

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: Rejected on the advisory findings (brief unchanged, deliverables (a)-(d) otherwise met and verified): 1. T3 — Act-index abort on a pathological recorded value: _num() guards int() conversion, but a valid astronomically large patch_bytes then raises uncaught OverflowError in the "/ 1024" float formatting (act.py:755), so one garbled size-signal.json aborts the whole index instead of the criterion's graceful blank. Fix: extend the guard to cover the division/format (render blank or clamp on overflow) and add a test with an overflowing recorded value. 2. C5 — model_weight retuning is blind: the index omits the stored sizer verdict (import-cycle rationale accepted) and size-calibrate has no model-verdict feature, so escalation-to-outcome correlation is unobservable. Fix within scope: make the gap observable or explicitly named — at minimum add the model-verdict caveat to the documented retuning walk (config block + docs) so an Act-cadence review knows it cannot yet justify changing model_weight; a calibrator model-verdict feature is acceptable if small, not required.
- Failing gate: T3 runtime: render/update-compat + offline driver suites (advisory) — /tmp/tmpnk1tnj37/results/issue_500/split-proposal.md
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
