# Result — issue 401 / deferred-gate-row-for-default-open-t4

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: A bundle-scoped gate that ran its **default-open** path at Check — the audit it
  performs has no subject yet, because the artifacts it lints are drafted later — is recorded
  distinguishably from a substantive pass, so the Check matrix stops asserting a green nobody
  can reproduce and the reviewer stops escalating a by-design condition to §6 on every cycle.
- Success criterion: With the patch applied, a Check-time run of the T4 row on a bundle that
  has `patch.diff` but no `pr-description.md` records a result that is **not** `pass` and **not**
  `unverifiable` — a `deferred` row that (a) does not count toward `overall`, (b) is **not**
  lifted into `SUMMARY.md` §6 NEEDS-HUMAN, and (c) names in its evidence that the substantive
  audit runs at publish; while the same row on a bundle whose artifacts **are** drafted still
  records the substantive `pass`/`fail` exactly as today, and `publish._t4_passes` still hard-
  gates before any push (unchanged). Demonstrable by C4-verify alone: the named test module is
  red with the production hunks reverted and green with them applied.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: one logical change — add `deferred` to the gate-result vocabulary as a
  gate-declared, non-gating, non-§6 state, emit it from `contribcheck`'s default-open path, and
  render/consume it consistently (matrix, `overall`, §6 lift, revalidate comparison, the
  reviewer's contract text, the spec docs and the `pdca.toml.jinja` comment that currently
  promises "default-open … so Check-time gates pass").
  / **out of scope:** the publish-time T4 semantics under `--no-issue` (issue 384, wave 0 — do
  not touch `publish.publish`'s relax branch or `_t4_passes`); a general `phase` property for
  gate rows (the larger change #339 records for later — deferral here is declared by the
  checker, not modelled as a new scope); the `unverifiable` marker rule (428) and the evidence
  line (402); any change to what `publish` enforces before a push.

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

Task under review: add a `deferred` gate result for Check-time T4 contribution rows whose publish artifacts do not exist yet, without turning that by-design absence into a PASS or §6 item.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief defines the data-model goal and success criteria for `deferred`, including non-`overall`, non-§6 routing, and unchanged publish hard-gating (`brief.md:15`). |
| C2 Reproduction (red pre-fix) | NEEDS-HUMAN | The owed decision is whether to accept unreproduced red evidence: the named C4 wrapper could not be rerun here because the target script is a skeleton requiring driver state, so the old PASS-with-empty-evidence symptom remains asserted by the brief and supplied gate record rather than independently replayed (`brief.md:23`, `check-gates.json:33`). |
| C3 Change | PASS | The patch implements a first-class `deferred` marker, limits it to rows re-gated later, emits it from `contribcheck` before PR artifacts exist, and keeps it out of §6 while leaving `unverifiable` lifted (`template/src/pdca_harness/gates.py:92`, `template/src/pdca_harness/gates.py:690`, `template/src/pdca_harness/cli.py:1088`, `template/src/pdca_harness/assemble.py:361`). |
| C4 Verification (red→green) | NEEDS-HUMAN | The owed decision is whether focused green tests are enough without the official red→green gate: `PYTHONPATH=src python3 -m unittest tests.test_gate_deferred tests.test_publish_slice.ContribCheck.test_default_open_before_artifacts_are_drafted` passed 18 tests, but `template/engine/scripts/run-verify.sh` is not implemented and exits before proving red→green (`template/engine/scripts/run-verify.sh:55`). |
| C5 Causal adequacy | PASS | The fix changes the recorded verdict vocabulary and downstream routing instead of adding a capability probe or symptom-only fallback; deferral is honoured only when `publish.publish_gates` will rerun the same row (`template/src/pdca_harness/gates.py:690`, `template/src/pdca_harness/gates.py:765`). |
| T1 Structure | PASS | The change is scoped to gate classification, contribution checking, assembly/reviewer contracts, docs, and focused tests for the new result class, matching the brief’s declared surfaces (`brief.md:47`, `template/tests/test_gate_deferred.py:14`). |
| T2 Shape | FAIL | The human must decide whether stale contract text is acceptable: the module docstring still says `PDCA-UNVERIFIABLE` is the one marker that can change a `result`, contradicting the new `PDCA-DEFERRED` result-changing marker (`template/src/pdca_harness/gates.py:37`). |
| T3 Runtime | NEEDS-HUMAN | The owed decision is whether to proceed with an unreproduced runtime gate: `check-gates.json` records T3 fail, but the named oracle `./engine/scripts/run-suite.sh` is absent in this target checkout, so I could not confirm whether the failure is host/state or patch behavior (`check-gates.json:69`). |
| T4 Contribution | NEEDS-HUMAN | The owed decision is whether to accept the stale recorded T4 green: `check-gates.json` still records a PASS with empty evidence, while the patched contract expects this Check-time condition to be `deferred`/N/A until publish (`check-gates.json:78`, `template/src/pdca_harness/cli.py:1088`). |
| T5 Judgment | NEEDS-HUMAN | Prior-art and ordering need human sign-off: local history shows related marker/evidence work on affected files, and live `gh` search found open PRs #431/#432 plus #430 while the brief’s prior-art note says no open PRs, so the stacked target state must be reconciled before accepting (`brief.md:76`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | The human owes final fitness-to-purpose: this is a normative gate-result vocabulary change that removes a recurring §6 item, so sign-off must decide whether that hand-off preserves the intended human review guard (`brief.md:3`). |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] C2 Reproduction (red pre-fix) — The owed decision is whether to accept unreproduced red evidence: the named C4 wrapper could not be rerun here because the target script is a skeleton requiring driver state, so the old PASS-with-empty-evidence symptom remains asserted by the brief and supplied gate record rather than independently replayed (`brief.md:23`, `check-gates.json:33`).
- [x] C4 Verification (red→green) — The owed decision is whether focused green tests are enough without the official red→green gate: `PYTHONPATH=src python3 -m unittest tests.test_gate_deferred tests.test_publish_slice.ContribCheck.test_default_open_before_artifacts_are_drafted` passed 18 tests, but `template/engine/scripts/run-verify.sh` is not implemented and exits before proving red→green (`template/engine/scripts/run-verify.sh:55`).
- [x] T3 Runtime — The owed decision is whether to proceed with an unreproduced runtime gate: `check-gates.json` records T3 fail, but the named oracle `./engine/scripts/run-suite.sh` is absent in this target checkout, so I could not confirm whether the failure is host/state or patch behavior (`check-gates.json:69`).
- [x] T4 Contribution — The owed decision is whether to accept the stale recorded T4 green: `check-gates.json` still records a PASS with empty evidence, while the patched contract expects this Check-time condition to be `deferred`/N/A until publish (`check-gates.json:78`, `template/src/pdca_harness/cli.py:1088`).
- [x] T5 Judgment — Prior-art and ordering need human sign-off: local history shows related marker/evidence work on affected files, and live `gh` search found open PRs #431/#432 plus #430 while the brief’s prior-art note says no open PRs, so the stacked target state must be reconciled before accepting (`brief.md:76`).
- [x] Validation — fitness-to-purpose — The human owes final fitness-to-purpose: this is a normative gate-result vocabulary change that removes a recurring §6 item, so sign-off must decide whether that hand-off preserves the intended human review guard (`brief.md:3`).

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
- By / date: Eduard Ralph / 2026-08-02

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
- T2: `gates.py:38` still calls `PDCA-UNVERIFIABLE` "the one marker that can change a `result`" — stale once `PDCA-DEFERRED` lands; fix the sentence in a follow-up.
