# Result — issue 359 / act-sizing-calibration

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: keep the sizing thresholds honest as the corpus grows: a sizing column
  (estimate vs outcome) in the Act index, a documented retuning procedure for
  `[driver.sizing]` from a fresh `size-calibrate` run, and `model_weight` as a
  config value revisited at Act cadence rather than a constant. The prerequisite
  (#324's Check-time backstop / `size-signal.json`) is merged on target main
  (`cad9601`; `size_signal.py` + `template/scripts/size-calibrate` exist).
- Success criterion: (a) `pdca act index` renders a sizing column per frozen bundle
  — the a-priori estimate beside the measured outcome (from the bundle's recorded size
  signal), with a graceful blank for bundles predating the signal; (b) a documented
  retuning procedure exists (docs/ or the config comment block) walking
  `size-calibrate` output back into `[driver.sizing]`; (c) `model_weight` is read from
  `[driver.sizing]` config (defaulting to current behaviour) with its Act-cadence
  review noted where it is defined; (d) the PR reports whether mining archived
  `iteration-v*/brief.md` files changes the correlations, or records an explicit
  decision not to. (a)–(c) demonstrable by C4-verify via the offline driver suite; (d)
  is a PR-prose obligation checked at sign-off, not by a gate.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: the three deliverables + the PR-reported mining decision, as in the
  criterion. The *retuning itself* (changing shipped default weights) is explicitly not
  in scope — the corpus that would justify new numbers accumulates per instance; this
  change builds the loop that keeps them honest. / out of scope: #355-class feature
  work (landed, `767da25`); any change to the sizer's estimate computation or the
  Check-time backstop.

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: new-feature
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
- T3 runtime: render/update-compat + offline driver suites: fail — /tmp/tmpnk1tnj37/results/issue_500/split-proposal.md
- T4 PR body has a user-impact opener + tracker id in both artifacts: pass — pdca-pdca contribcheck
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Reviewing issue #359: add estimate-versus-recorded-outcome sizing to the Act index, document calibration retuning, and make the sizer model weight configurable at Act cadence.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The enhancement has falsifiable Act-column, retuning-documentation, config-default, and sign-off-prose outcomes with retuning the shipped defaults explicitly out of scope. |
| C2 Reproduction (red pre-fix) | PASS | The new focused oracle was independently carried onto base `dfd0427`: all 9 cases were red (1 failure, 8 errors), including the absent index join and absent model-weight API at `template/tests/test_act_index_sizing.py:92` and `template/tests/test_act_index_sizing.py:129`. |
| C3 Change | PASS | The requested implementation seams are present and localized: Act extracts/renders the joined column at `template/src/pdca_harness/act.py:542` and `template/src/pdca_harness/act.py:581`, while config reaches the model score at `template/src/pdca_harness/sizing.py:419`. |
| C4 Verification (red→green) | PASS | Independent rerun reproduced 9/9 red on the base and 9/9 green with the patch; the patched offline driver suite also passed 1323 tests (2 unrelated skips), grounding the main join assertion at `template/tests/test_act_index_sizing.py:99`. |
| C5 Causal adequacy | FAIL | Act-cadence review cannot presently justify changing `model_weight`: the index deliberately omits the stored sizer verdict at `template/src/pdca_harness/act.py:730`, while the calibrator has no model-verdict feature at `template/scripts/size-calibrate:237`, so escalation-to-outcome correlation is unobservable. |
| T1 Structure | PASS | The column reuses the established estimator and recorded-signal reader rather than duplicating either contract (`template/src/pdca_harness/act.py:725`, `template/src/pdca_harness/size_signal.py:217`). |
| T2 Shape | PASS | Documentation lint and 22-page link-audited site render passed, and all 7 Copier render/update-compat tests passed with the retuning block in its valid sub-table position at `template/pdca.toml.jinja:173`. |
| T3 Runtime | FAIL | A direct runtime probe with a valid large JSON integer for `patch_bytes` raises `OverflowError` in the float conversion at `template/src/pdca_harness/act.py:755`, so one recorded bundle can abort the whole Act index instead of rendering gracefully. |
| T4 Contribution | NEEDS-HUMAN | Sign-off must record whether mining archived `iteration-v*/brief.md` changes the correlations or is explicitly deferred — no PR body/contribution artifacts were supplied, and the current miner expressly excludes those briefs at `template/scripts/size-calibrate:479`. |
| T5 Judgment | NEEDS-HUMAN | Originality against closed/rejected work remains to be decided before contribution: affected-path `git log --all` found no existing #359 implementation in available refs, but `api.github.com` was unreachable, leaving the required closed-PR half at `docs/05-check.md:462` unsettled. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | The human must decide whether the change is fit to ship given the unobservable model-retuning signal and Act-index overflow failure — these affect whether the promised calibration loop stays trustworthy. |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T4 Contribution — Sign-off must record whether mining archived `iteration-v*/brief.md` changes the correlations or is explicitly deferred — no PR body/contribution artifacts were supplied, and the current miner expressly excludes those briefs at `template/scripts/size-calibrate:479`.
- [ ] T5 Judgment — Originality against closed/rejected work remains to be decided before contribution: affected-path `git log --all` found no existing #359 implementation in available refs, but `api.github.com` was unreachable, leaving the required closed-PR half at `docs/05-check.md:462` unsettled.
- [ ] Validation — fitness-to-purpose — The human must decide whether the change is fit to ship given the unobservable model-retuning signal and Act-index overflow failure — these affect whether the promised calibration loop stays trustworthy.

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: iterated-to-Do
- Iteration delta (if iterating): Rejected on the advisory findings (brief unchanged, deliverables (a)-(d) otherwise met and verified): 1. T3 — Act-index abort on a pathological recorded value: _num() guards int() conversion, but a valid astronomically large patch_bytes then raises uncaught OverflowError in the "/ 1024" float formatting (act.py:755), so one garbled size-signal.json aborts the whole index instead of the criterion's graceful blank. Fix: extend the guard to cover the division/format (render blank or clamp on overflow) and add a test with an overflowing recorded value. 2. C5 — model_weight retuning is blind: the index omits the stored sizer verdict (import-cycle rationale accepted) and size-calibrate has no model-verdict feature, so escalation-to-outcome correlation is unobservable. Fix within scope: make the gap observable or explicitly named — at minimum add the model-verdict caveat to the documented retuning walk (config block + docs) so an Act-cadence review knows it cannot yet justify changing model_weight; a calibrator model-verdict feature is acceptable if small, not required.
- By / date: Eduard Ralph / 2026-07-31

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
