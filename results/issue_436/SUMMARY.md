# Result — issue 436 / size-signal-attributable-rounds

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: `size_signal`'s strongest rule counts ROUNDS (`rounds: 2` default,
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
- Success criterion: A round is excluded from `rounds` only when the archived
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
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: attribution inside `iteration_rounds` (shared by the runtime backstop and
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

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: pass — C4 PASS: red without the fix, green with it
- C5 Causal adequacy: none — reviewer + human sign-off

## 4. Conformance (Check — stack)
- T1 Structure: none — (no gate configured)
- T2 shape: docs lint + site render link audit: pass — render_site: link audit OK
- T3 runtime: render/update-compat + offline driver suites: fail — == T3: root suite OK, driver suite FAILED (rc 1)
- T4 PR body has a user-impact opener + tracker id in both artifacts: pass — pdca-pdca contribcheck
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Review of issue #436: count only iteration rounds attributable to the slice, excluding rounds whose archived evidence identifies an environment fault as the sole driver.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The acceptance boundary is decidable: exclude only sole environment-attributed rounds while counting mixed, green, plain-fail, and ambiguous evidence cases (`template/src/pdca_harness/size_signal.py:158`). |
| C2 Reproduction (red pre-fix) | PASS | In an isolated target copy with only the source fix reversed, the new focused tests failed on solely-unverifiable and flaky rounds (5 failures in `test_size_signal`, 1 in `test_size_calibrate`), reproducing the elapsed-round miscount at `template/tests/test_size_signal.py:590`. |
| C3 Change | PASS | The change stays within attribution and tests, and the miner continues to consume the shared counter rather than acquiring a divergent definition (`template/scripts/size-calibrate:74`). |
| C4 Verification (red→green) | PASS | Independent replay was red with the source fix removed, then green with it applied: 56/56 size-signal tests, 57/57 calibration tests, and the complete available Python discovery suite exited 0; the end-to-end threshold assertion is at `template/tests/test_size_signal.py:596`. |
| C5 Causal adequacy | PASS | The corrected measurement classifies archived causes, preserves plain-fail and mixed-cause rounds, and fails safe by counting unreadable evidence; no capability-probe/runtime-guard symptom smell is introduced (`template/src/pdca_harness/size_signal.py:185`). |
| T1 Structure | PASS | Attribution is factored into evidence-reading and review-driver helpers while the public shared `iteration_rounds` interface remains unchanged (`template/src/pdca_harness/size_signal.py:154`). |
| T2 Shape | NEEDS-HUMAN | Decide whether release-shape confidence can rely on the recorded link-audit green — `./engine/scripts/run-docs-check.sh` is absent from the target, so that gate could not be independently rerun; this matters before accepting its asserted coverage (`template/src/pdca_harness/size_signal.py:135`). |
| T3 Runtime | NEEDS-HUMAN | Decide whether the recorded driver-suite red is a real integration regression or an unavailable-runner fault — `./engine/scripts/run-suite.sh` is absent, while the complete locally available Python suite exited 0; this matters before attributing the red to the patch (`template/src/pdca_harness/size_signal.py:234`). |
| T4 Contribution | NEEDS-HUMAN | Decide whether closed/rejected work duplicates this contribution — affected-path merged history was checked and contains the earlier current-brief boundary but no environment attribution, while the supplied artifacts and target expose no closed/rejected-work oracle; duplication would change contribution fitness (`template/src/pdca_harness/size_signal.py:135`). |
| T5 Judgment | PASS | The conservative default is explicit and tested: absent, malformed, or incomplete archive evidence continues to count the round, preventing silent weakening of the backstop (`template/tests/test_size_signal.py:676`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether archived gate/review records are the right operational proxy for sole-driver attribution — this determines whether real-world environment-only rounds are excluded without hiding slice churn (`template/src/pdca_harness/size_signal.py:162`). |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T2 Shape — Decide whether release-shape confidence can rely on the recorded link-audit green — `./engine/scripts/run-docs-check.sh` is absent from the target, so that gate could not be independently rerun; this matters before accepting its asserted coverage (`template/src/pdca_harness/size_signal.py:135`).
- [x] T3 Runtime — Decide whether the recorded driver-suite red is a real integration regression or an unavailable-runner fault — `./engine/scripts/run-suite.sh` is absent, while the complete locally available Python suite exited 0; this matters before attributing the red to the patch (`template/src/pdca_harness/size_signal.py:234`).
- [x] T4 Contribution — Decide whether closed/rejected work duplicates this contribution — affected-path merged history was checked and contains the earlier current-brief boundary but no environment attribution, while the supplied artifacts and target expose no closed/rejected-work oracle; duplication would change contribution fitness (`template/src/pdca_harness/size_signal.py:135`).
- [x] Validation — fitness-to-purpose — Decide whether archived gate/review records are the right operational proxy for sole-driver attribution — this determines whether real-world environment-only rounds are excluded without hiding slice churn (`template/src/pdca_harness/size_signal.py:162`).
- [x] size backstop — this slice is behaving oversized: 2 round(s) already spent (threshold 2). Recommend answering `iterate-plan` at sign-off and authoring the split in the re-plan (`pdca split`), rather than `iterate-do`: a slice that is too big yields implementation-shaped findings every round, and splitting authors briefs, which is Plan's beat.

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: merged-wider
- Iteration delta (if iterating):
- By / date: Eduard Ralph / 2026-08-06

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
