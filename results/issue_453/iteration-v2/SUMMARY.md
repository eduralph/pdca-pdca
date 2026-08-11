# Result — issue 453 / apply-orphaned-signoff-decision

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: the sign-off leaf writes `signoff-decision` durably, but the driver consumes
  it only **in-process**, in the same call that launched the session. If the run dies
  between the leaf's write and the driver's apply — a `^C` during the interactive session
  raises `KeyboardInterrupt`, which `_isolate` deliberately does not contain
  (`template/src/pdca_harness/flow.py:50-69`) — the decision is orphaned on disk with §9
  unrecorded. On every later pass and every later run the bundle is still
  AWAITING_SIGNOFF, so the queue re-presents it and the driver opens a **fresh interactive
  session for a bundle the human already judged**; the decision on disk is never read. The
  reporting instance saw the same decision made at 12:43, re-issued at 19:48 and
  re-affirmed a third time, none recorded (instance report: getwyrd/wyrd-pdca#211).
  Two aggravations: `_drive_wave`'s no-progress exit only fires when the pending queue is
  empty (`flow.py:668-685`), so a wave holding one such bundle re-runs the session every
  pass until `max_passes` runs out; and `autoiterate.write_decision` (`flow.py:271`) writes
  unconditionally, so an auto-iterate pass can silently clobber an orphaned human decision
  with one it did not author.
- Success criterion: on a bundle halted at AWAITING_SIGNOFF that already carries a
  valid `signoff-decision` written by an earlier session, BOTH drive paths — the batch
  `flow._drive_wave` and the single-issue `flow._signoff_and_apply` — record §9 and
  transition the bundle **without invoking any sign-off leaf**, and `_maybe_auto_iterate`
  declines (writes no decision, spends no auto-iterate budget) while such a file exists.
  The one exception: an `accept` that C6 refuses (§6 NEEDS-HUMAN still open) still falls
  through to a fresh session, because there the human genuinely must return. Demonstrable
  by C4-verify on the patch alone, via the offline driver suite.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: a decision already recorded for a bundle is applied **before** that bundle is
  offered a new sign-off session, on both drive paths, with the same apply-deferred
  semantics the post-session path already uses (`apply_now=False` in the wave sweep,
  `apply_now=True` single-issue); and auto-iterate never authors a decision for a bundle
  whose previous decision is still un-consumed. Each such apply is announced on stderr
  naming the bundle and the action, so a decision applied without a session is never
  silent. Mechanism is Do's — this states the property, not the shape.
  / out of scope: changing the decision grammar or `VALID_DECISIONS`
  (`leaves.py:78`); changing what C6 blocks or how §9 is written (`signoff.record`);
  making `_isolate` contain `KeyboardInterrupt` (the ^C must still stop the run — that is
  its documented contract, `flow.py:56-58`); the no-progress/`max_passes` accounting beyond
  what falls out of the pre-apply; any change to the interactive sign-off prompt.

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
- T3 runtime: render/update-compat + offline driver suites: pass — == T3: root suite OK, driver suite OK
- T4 PR body has a user-impact opener + tracker id in both artifacts: pass — ./scripts/pdca contribcheck
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Review of issue #453: resume an interrupted sign-off by consuming a valid persisted decision before opening another session, while preserving the C6 exception and auto-iterate budget.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The recovery contract is falsifiable across batch, single-issue, auto-iterate, and C6-refusal paths, and it protects the repository's filesystem-resumability invariant (`template/src/pdca_harness/state.py:1`). |
| C2 Reproduction (red pre-fix) | PASS | Against `HEAD` production with the new test retained, 7 tests executed and 5 failed specifically on reopened sessions or premature auto-iterate classification (`template/tests/test_signoff_orphan.py:103`). |
| C3 Change | PASS | The change stays within the three authorized decision-entry paths and leaves decision grammar, C6 recording, prompts, and `KeyboardInterrupt` containment untouched (`template/src/pdca_harness/flow.py:213`, `template/src/pdca_harness/flow.py:242`, `template/src/pdca_harness/flow.py:671`). |
| C4 Verification (red→green) | PASS | Independent execution produced 7 tests/5 failures on baseline production and 7/7 passing on the patched target, covering both drive modes, C6 refusal, public flow, and auto-iterate (`template/tests/test_signoff_orphan.py:82`). |
| C5 Causal adequacy | PASS | No capability probe or fallback masks the symptom: each asking/overwriting path now treats the durable decision as driver input before acting, directly restoring resumability (`template/src/pdca_harness/flow.py:231`, `template/src/pdca_harness/flow.py:270`, `template/src/pdca_harness/flow.py:729`). |
| T1 Structure | PASS | Decision interpretation remains in the existing flow coordinator and all new routes reuse the single C6-guarded `_apply_decision` transition rather than duplicating state logic (`template/src/pdca_harness/flow.py:132`). |
| T2 Shape | PASS | `git diff --check`, `compileall`, documentation lint, and the 22-page rendered-link audit all pass for the target; the new test is importable and collected (`template/tests/test_signoff_orphan.py:25`). |
| T3 Runtime | NEEDS-HUMAN | Decide whether the independently green 1,598-test offline-driver suite is sufficient without render/update coverage — `copier` is absent, so the root suite reported green while executing 0 of 7 tests (all skipped by guards such as `tests/test_render_and_run.py:31` and `tests/test_update_compat.py:232`). |
| T4 Contribution | NEEDS-HUMAN | Decide whether to rely on the frozen contribution-gate PASS — `commit-msg.txt`, `pr-description.md`, and the configured checker are outside the permitted reviewer inputs, so the tracker-id and user-impact-opener claims could not be independently reproduced (`template/src/pdca_harness/leaves.py:65`). |
| T5 Judgment | PASS | The affected-path audit found `origin/main` equal to target `b95aa58`, 0 open overlaps, and 0 rejected overlaps among all 212 closed PRs; merged history contains no prior pre-session consumption of a persisted decision (`template/src/pdca_harness/flow.py:231`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Confirm that automatically applying the prior human decision on restart, with a stderr notice and a fresh session only after C6 refusal, is the intended operator experience — red→green proves mechanics but cannot decide workflow fitness (`template/src/pdca_harness/flow.py:228`, `template/src/pdca_harness/flow.py:233`). |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T3 Runtime — Decide whether the independently green 1,598-test offline-driver suite is sufficient without render/update coverage — `copier` is absent, so the root suite reported green while executing 0 of 7 tests (all skipped by guards such as `tests/test_render_and_run.py:31` and `tests/test_update_compat.py:232`).
- [ ] T4 Contribution — Decide whether to rely on the frozen contribution-gate PASS — `commit-msg.txt`, `pr-description.md`, and the configured checker are outside the permitted reviewer inputs, so the tracker-id and user-impact-opener claims could not be independently reproduced (`template/src/pdca_harness/leaves.py:65`).
- [ ] Validation — fitness-to-purpose — Confirm that automatically applying the prior human decision on restart, with a stderr notice and a fresh session only after C6 refusal, is the intended operator experience — red→green proves mechanics but cannot decide workflow fitness (`template/src/pdca_harness/flow.py:228`, `template/src/pdca_harness/flow.py:233`).

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
- Iteration delta (if iterating): Auto-iterate (round 2): Check found implementation-level items only, no architectural judgment required — T3 Runtime — Decide whether the independently green 1,598-test offline-driver suite is sufficient without render/update coverage — `copier` is absent, so the root suite reported green while executing 0 of 7 tests (all skipped by guards such as `tests/test_render_and_run.py:31` and `tests/test_update_compat.py:232`).; T4 Contribution — Decide whether to rely on the frozen contribution-gate PASS — `commit-msg.txt`, `pr-description.md`, and the configured checker are outside the permitted reviewer inputs, so the tracker-id and user-impact-opener claims could not be independently reproduced (`template/src/pdca_harness/leaves.py:65`).
- By / date: auto-iterate / 2026-08-07

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
