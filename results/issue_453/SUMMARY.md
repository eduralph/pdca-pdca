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

Review of issue #453: consume a durable orphaned `signoff-decision` before re-opening sign-off, while preserving the C6 re-prompt exception and protecting auto-iterate.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The contract is falsifiable across both drive paths, auto-iterate, deferred/immediate application, and the C6 exception, so acceptance does not depend on an unstated behavior (`template/src/pdca_harness/flow.py:132`). |
| C2 Reproduction (red pre-fix) | PASS | On an isolated `origin/main` tree with the new test retained and production hunks absent, all 8 tests executed and 6 failed on the intended session-reopen/decision-clobber behavior (`template/tests/test_signoff_orphan.py:121`). |
| C3 Change | PASS | The required behavior is covered at every decision-request boundary: single-issue pre-apply, auto-iterate preservation, and wave queue filtering (`template/src/pdca_harness/flow.py:257`, `template/src/pdca_harness/flow.py:291`, `template/src/pdca_harness/flow.py:751`). |
| C4 Verification (red→green) | PASS | Independent red→green ran 8 tests on each leg (red: 6 intended failures; green: 8 passes), and the patched offline suite also passed 1,599 tests with 2 unrelated skips (`template/tests/test_signoff_orphan.py:118`). |
| C5 Causal adequacy | PASS | The fix restores durable state as the source of truth before asking, rather than probing an optional capability or masking a load-time side effect, and delegates transition semantics to the existing C6-guarded path (`template/src/pdca_harness/flow.py:222`). |
| T1 Structure | PASS | One shared pre-apply helper feeds the existing `_apply_decision` authority, avoiding a second record/transition implementation across callers (`template/src/pdca_harness/flow.py:222`, `template/src/pdca_harness/flow.py:248`). |
| T2 Shape | FAIL | The C6 exception is operator-misleading: stderr promises “no new session” before the blocked result deliberately opens one, obscuring that fresh human interaction is required (`template/src/pdca_harness/flow.py:246`, `template/src/pdca_harness/flow.py:258`). |
| T3 Runtime | PASS | With Copier provisioned in the disposable verifier, all 7 render/update tests ran and passed (not skipped); docs lint plus the 22-page link audit passed, and the patched offline driver suite passed 1,599 tests (`tests/test_render_and_run.py:31`, `tests/test_update_compat.py:232`). |
| T4 Contribution | NEEDS-HUMAN | Decide whether to rely on the frozen T4 PASS — its required `commit-msg.txt` and `pr-description.md` subjects are deliberately outside the reviewer inputs, so their tracker-id and user-impact-opener compliance cannot be independently reproduced (`template/src/pdca_harness/cli.py:1061`, `template/src/pdca_harness/leaves.py:65`). |
| T5 Judgment | PASS | Current upstream is exactly the reviewed base (`b95aa58`); affected-path merged history and every closed/rejected PR path were checked, with no earlier equivalent consumption fix or in-flight collision found (`template/src/pdca_harness/flow.py:222`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether durable prior human decisions should outrank a fresh session while C6-refused accepts alone re-prompt — automation proves this policy works mechanically, not that it is the right product policy (`template/src/pdca_harness/flow.py:254`). |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T4 Contribution — Decide whether to rely on the frozen T4 PASS — its required `commit-msg.txt` and `pr-description.md` subjects are deliberately outside the reviewer inputs, so their tracker-id and user-impact-opener compliance cannot be independently reproduced (`template/src/pdca_harness/cli.py:1061`, `template/src/pdca_harness/leaves.py:65`).
- [x] Validation — fitness-to-purpose — Decide whether durable prior human decisions should outrank a fresh session while C6-refused accepts alone re-prompt — automation proves this policy works mechanically, not that it is the right product policy (`template/src/pdca_harness/flow.py:254`).
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
- By / date: Eduard Ralph / 2026-08-07

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
- `flow._apply_recorded_decision` prints "no new session" before the C6 check, so a C6-refused accept contradicts it one line later — move or reword the notice.
- Size backstop counts rounds without cause: issue_453's 2 rounds were a missing `copier` in the verifier plus permanently-human T4/Validation items, not implementation-shaped findings — consider discounting those from the round count.
