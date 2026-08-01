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
- T3 runtime: render/update-compat + offline driver suites: fail — /tmp/tmpt64quk1y/results/issue_500/split-proposal.md
- T4 PR body has a user-impact opener + tracker id in both artifacts: pass — pdca-pdca contribcheck
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Task under review: add estimate-versus-recorded-outcome sizing to the Act index, document the calibration loop, and make the sizer model weight configurable without changing the default behavior.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief gives separable criteria for the index, retuning procedure, configurable default, and the sign-off-only archive-mining decision, with retuning shipped defaults explicitly out of scope. |
| C2 Reproduction (red pre-fix) | PASS | An isolated base snapshot plus the added test produced 11/11 failures, including the missing Act join and absent configurable weight exercised at `template/tests/test_act_index_sizing.py:95` and `template/tests/test_act_index_sizing.py:170`. |
| C3 Change | PASS | The patch stays within the declared loop: the index reads the frozen record at `template/src/pdca_harness/act.py:725`, the instance-facing retuning walk is at `template/pdca.toml.jinja:179`, and production sizing callers receive config at `template/src/pdca_harness/cli.py:780`. |
| C4 Verification (red→green) | PASS | The same isolated 11-test slice changed from 11 failures on base to 11 passes patched, and the patched full offline suite also passed; the prior overflow case is exercised at `template/tests/test_act_index_sizing.py:131`. |
| C5 Causal adequacy | FAIL | Retuning must be made causal: `model_weight=5` is asserted to yield score 8 while preserving `watch` at `template/tests/test_act_index_sizing.py:179`, because the band is fixed before the score update at `template/src/pdca_harness/sizing.py:460`; operational holds inspect only that unchanged band at `template/src/pdca_harness/plan_policy.py:121`, so the new weight cannot alter a sizing decision. |
| T1 Structure | PASS | Config flows through all production combination seams without introducing an import cycle, including queue display at `template/src/pdca_harness/cli.py:818` and Plan policy at `template/src/pdca_harness/plan_policy.py:119`. |
| T2 Shape | PASS | Independent Markdown lint and site rendering/link audit both passed against the patched snapshot; the rendered documentation surface begins at `docs/07-crosscutting.md:154`. |
| T3 Runtime | PASS | The recorded advisory red did not reproduce: the complete patched offline driver suite, rendered-template slice, and update-compat suite all passed, including the pathological recorded-value case at `template/tests/test_act_index_sizing.py:131`. |
| T4 Contribution | NEEDS-HUMAN | Confirm the PR prose records the required archived-`iteration-v*` mining decision and satisfies the claimed contribution checks — `pr-description.md` and `commit-msg.txt` were not supplied, so the reported T4 green cannot be independently rerun. |
| T5 Judgment | NEEDS-HUMAN | Confirm no closed or rejected work duplicates/conflicts with this change — affected-path history on target shows no merged implementation, but closed/rejected review artifacts are unavailable locally, so prior art is only partially discharged. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether this is fit for real Act calibration after C5 is resolved — mechanical green cannot establish that reviewers can make an evidence-based model retune while the documented blind spot remains at `docs/07-crosscutting.md:167`. |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T4 Contribution — Confirm the PR prose records the required archived-`iteration-v*` mining decision and satisfies the claimed contribution checks — `pr-description.md` and `commit-msg.txt` were not supplied, so the reported T4 green cannot be independently rerun.
- [x] T5 Judgment — Confirm no closed or rejected work duplicates/conflicts with this change — affected-path history on target shows no merged implementation, but closed/rejected review artifacts are unavailable locally, so prior art is only partially discharged.
- [x] Validation — fitness-to-purpose — Decide whether this is fit for real Act calibration after C5 is resolved — mechanical green cannot establish that reviewers can make an evidence-based model retune while the documented blind spot remains at `docs/07-crosscutting.md:167`.

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
- By / date: Eduard Ralph / 2026-07-31

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
