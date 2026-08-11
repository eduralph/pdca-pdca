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

Task under review: consume an orphaned durable `signoff-decision` before opening a new sign-off session in batch and single-issue flows, while preserving C6 refusal and auto-iterate ownership.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The acceptance decision is bounded to observable resumability across batch, single-issue, C6-refusal, and auto-iterate paths, with each outcome encoded independently at `template/tests/test_signoff_orphan.py:67`, `template/tests/test_signoff_orphan.py:98`, `template/tests/test_signoff_orphan.py:118`, and `template/tests/test_signoff_orphan.py:144`. |
| C2 Reproduction (red pre-fix) | PASS | On an isolated export of the target's exact `b95aa58` HEAD with only the new test added, 4 tests executed and 3 defect-specific assertions failed at `template/tests/test_signoff_orphan.py:91`, `template/tests/test_signoff_orphan.py:112`, and `template/tests/test_signoff_orphan.py:157`, so red was behavioral rather than an import or collection failure. |
| C3 Change | PASS | The human decision is preserved at all three overwrite-risk boundaries without changing decision grammar or C6 semantics: single-issue pre-apply at `template/src/pdca_harness/flow.py:228`, auto-iterate refusal at `template/src/pdca_harness/flow.py:261`, and batch pre-apply at `template/src/pdca_harness/flow.py:720`. |
| C4 Verification (red→green) | PASS | Literal stashing was blocked by the target's read-only Git index, but the equivalent exact-HEAD red leg ran 4 tests with 3 failures, the patched target ran all 4 green, reverse-apply and compile checks passed, the batch C6 exception was exercised successfully, and the full offline suite passed 1595 tests with 2 skips; focused expectations are grounded at `template/tests/test_signoff_orphan.py:91` and `template/tests/test_signoff_orphan.py:162`. |
| C5 Causal adequacy | PASS | The defect is loss of filesystem durability across a process boundary, and the patch restores that invariant by consuming the durable input through the existing guarded transition rather than adding a capability probe or parallel transition path (`template/src/pdca_harness/state.py:1`, `template/src/pdca_harness/flow.py:231`, `template/src/pdca_harness/flow.py:727`). |
| T1 Structure | PASS | The change stays within the existing sign-off orchestration module and one focused offline slice, while both callers continue to centralize recording and transition in `_apply_decision` (`template/src/pdca_harness/flow.py:132`, `template/src/pdca_harness/flow.py:231`, `template/src/pdca_harness/flow.py:727`). |
| T2 Shape | PASS | Direct re-runs of the documentation linter and site renderer completed with 22 pages and a clean link audit, and the production diff passed whitespace and Python compile checks. |
| T3 Runtime | NEEDS-HUMAN | Decide whether the independently green focused and offline-driver coverage is sufficient without `copier` — the driver suite passed 1595 tests, but the root render/update suite executed zero tests (all 7 skipped) because `copier` is unavailable, so the recorded root-suite green was not independently reproduced. |
| T4 Contribution | NEEDS-HUMAN | Decide whether to rely on the frozen contribution-gate result — `commit-msg.txt`, `pr-description.md`, and the configured `scripts/pdca` checker were not among the permitted inputs or target files, so the tracker-id and user-impact-opener assertions could not be independently checked. |
| T5 Judgment | PASS | Contribution remains warranted: remote `main` exactly matched target `b95aa58`; merged history by both affected paths contained no equivalent pre-apply; the complete closed/unmerged corpus had 1 PR with 0 affected-path matches; and there were 0 open PRs. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether automatically consuming a prior human decision after interruption is the intended operator experience — automated red→green evidence proves the state transitions and no-clobber behavior, but product fitness and sign-off authority remain a human judgment. |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T3 Runtime — Decide whether the independently green focused and offline-driver coverage is sufficient without `copier` — the driver suite passed 1595 tests, but the root render/update suite executed zero tests (all 7 skipped) because `copier` is unavailable, so the recorded root-suite green was not independently reproduced.
- [ ] T4 Contribution — Decide whether to rely on the frozen contribution-gate result — `commit-msg.txt`, `pr-description.md`, and the configured `scripts/pdca` checker were not among the permitted inputs or target files, so the tracker-id and user-impact-opener assertions could not be independently checked.
- [ ] Validation — fitness-to-purpose — Decide whether automatically consuming a prior human decision after interruption is the intended operator experience — automated red→green evidence proves the state transitions and no-clobber behavior, but product fitness and sign-off authority remain a human judgment.

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
- Iteration delta (if iterating): Auto-iterate (round 1): Check found implementation-level items only, no architectural judgment required — T3 Runtime — Decide whether the independently green focused and offline-driver coverage is sufficient without `copier` — the driver suite passed 1595 tests, but the root render/update suite executed zero tests (all 7 skipped) because `copier` is unavailable, so the recorded root-suite green was not independently reproduced.; T4 Contribution — Decide whether to rely on the frozen contribution-gate result — `commit-msg.txt`, `pr-description.md`, and the configured `scripts/pdca` checker were not among the permitted inputs or target files, so the tracker-id and user-impact-opener assertions could not be independently checked.
- By / date: auto-iterate / 2026-08-07

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
