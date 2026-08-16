# Result — issue 475 / no-new-session-notice-waits-for-the-guard

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: `flow._apply_recorded_decision`
  (`template/src/pdca_harness/flow.py:223-249`) announces the outcome **before** the outcome is
  decided. It prints, at `:247-248`:
  `flow: <bundle> — applying the '<action>' sign-off decision already recorded in the bundle;
  no new session` — and only then calls `_apply_decision` (`:249`), where the C6 accept-guard
  runs: an `accept` with §6 NEEDS-HUMAN still open prints
  `flow: <bundle> — cannot accept, §6 NEEDS-HUMAN still open (C6)` and returns `"blocked"`
  (`:176-178`). `"blocked"` is the one outcome that deliberately falls through
  (`_signoff_and_apply`, `:258-262`; the batch path, `:1366-1379`), so a **fresh sign-off
  session is opened immediately** — the very thing the operator was just told would not happen.
  The operator reads a promise and its withdrawal one line apart, on the path where they are
  being asked to come back and look. Confirmed on the target base: the notice is
  unconditional, and nothing between `:247` and the guard can suppress it.
  Surfaced as a §10 Act candidate on this instance's issue_453 cycle and routed upstream at the
  2026-08-09 Act review (`process/act-log.md`).
- Success criterion: With the patch, on a bundle carrying a recorded `accept` that C6
  refuses (§6 NEEDS-HUMAN still open), the run's stderr **does not claim that no new session
  will be opened** — while the C6 refusal message, the fall-through to a fresh session, the
  return value `"blocked"` and every state transition stay exactly as they are; and on a
  decision that **is** applied without a session (an `accept` that C6 permits, and every
  `iterate-do` / `iterate-plan` / `discontinue`), the operator is still told, in the same terms,
  that the recorded decision was applied with no new session. Both drive paths — the single-issue
  `_signoff_and_apply` and the batch sweep — behave identically, since both call the same
  function. Demonstrable by C4-verify on the existing offline slice.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: The announce-before-decide pair in `flow._apply_recorded_decision` — one function,
  one message, no behaviour change beyond what is printed and when. **Out of scope:** the C6
  guard itself and its message (`flow.py:176-178`), which is correct; the fall-through contract
  for `"blocked"` (`:258-262`, `:1366-1379`), which is the documented and intended behaviour;
  `_apply_decision`'s repair paths (`:161-192`); anything about §9 recording, the carry-forward
  channel, or the auto-iterate decline; the interactive sign-off leaf's own output.

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: pass — C4 PASS — red without the fix, green with it
- C5 added test exercises production, not a copy: pass — patch adds no new test file — nothing to assert

## 4. Conformance (Check — stack)
- T1 Structure: none — (no gate configured)
- T2 shape: docs lint + site render link audit: pass — docs lint clean, site render + link audit clean
- T2 host CI parity: target docs-check.yml on the pushed tree: pass — host CI parity on the patched tree — docs lint clean, site render + link audit clean
- T3 runtime: render/update-compat + offline driver suites: pass — root suite OK, driver suite OK
- T4 PR body has a user-impact opener + tracker id in both artifacts: deferred — pr-description.md not drafted yet — the substantive T4 audit of the contribution artifacts runs at publish
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Task under review: delay the recorded sign-off “no new session” notice until the decision is genuinely recorded, while preserving successful, C6-blocked, dropped-record, and repair-path behavior.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The required operator-visible distinction is falsifiable across every `_apply_decision` outcome, and the existing outcome contract identifies exactly what may proceed or fall through (`template/src/pdca_harness/flow.py:133`, `template/src/pdca_harness/flow.py:176`). |
| C2 Reproduction (red pre-fix) | PASS | With only the production hunk stashed, the retained tests independently failed four times on the false notice: both C6 drive paths and both not-recorded paths (`template/tests/test_signoff_orphan.py:191`, `template/tests/test_signoff_orphan.py:328`). |
| C3 Change | PASS | The operator claim is now conditioned on the authoritative application result, so blocked, dropped, and repaired outcomes cannot be reported as successful while genuine decisions retain the notice (`template/src/pdca_harness/flow.py:256`). |
| C4 Verification (red→green) | PASS | Independent execution produced 4/10 intended failures without the production change and 10/10 passes after restoration; the complete offline suite, compilation, and diff check also passed (`template/tests/test_signoff_orphan.py:212`, `template/tests/test_signoff_orphan.py:353`). |
| C5 Causal adequacy | PASS | The change removes the announce-before-decision cause by using `_apply_decision`'s returned action, not a capability probe or symptom fallback; valid actions cannot collide with its sentinels (`template/src/pdca_harness/flow.py:243`, `template/src/pdca_harness/flow.py:256`). |
| T1 Structure | PASS | The production delta stays inside the owning helper and the regression coverage stays in the existing sign-off-orphan module, with no parallel mechanism or unrelated file introduced (`template/src/pdca_harness/flow.py:223`, `template/tests/test_signoff_orphan.py:316`). |
| T2 Shape | PASS | Python compilation and whitespace checks passed, and independent runs of the repository's docs lint plus 22-page render/link audit were clean; the edited control flow is direct and idiomatic (`template/src/pdca_harness/flow.py:253`). |
| T3 Runtime | PASS | Both shared callers exercise production `_apply_recorded_decision`; their successful, blocked, dropped, and repaired behaviors pass in the targeted slice and the full offline driver suite (`template/tests/test_signoff_orphan.py:130`, `template/tests/test_signoff_orphan.py:241`). |
| T4 Contribution | N/A | `pr-description.md` is absent by design at Check, and the frozen contribution gate defers its substantive tracker/opener audit to the mandatory publish-time rerun. |
| T5 Judgment | PASS | The patch is scoped to the stated operator-message defect, resolves the prior iteration's sentinel mistake, and an exhaustive affected-file PR query found only merged prior art—no open or closed-unmerged attempt—while upstream `main` still has the defect (`template/src/pdca_harness/flow.py:246`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the resulting stderr timing and wording communicate the sign-off outcome appropriately to operators across successful and refused/repair flows — this is the final product judgment despite complete automated behavioral coverage (`template/src/pdca_harness/flow.py:257`). |

### Advisory — code-review

# Advisory code review — issue #475 (no-new-session-notice-waits-for-the-guard)

## Correctness

- No bug introduced. `flow.py:256-259` (`if outcome == action:`) is the minimal, correct
  gate: `_apply_decision` returns the action string only on genuine success (`flow.py:211`),
  and every withdrawal path returns a distinct sentinel (`None`, `flow.REASSEMBLE`,
  `"blocked"`) that can never equal a member of `leaves.VALID_DECISIONS`
  (`leaves.py:84`), so `outcome == action` cannot false-positive. This directly fixes the
  prior iteration's rejected `outcome != "blocked"` gate, which admitted the drop
  (`flow.py:161-165`) and repair (`flow.py:114-130`, `_repair_unsignable`) outcomes.

- `_apply_recorded_decision`'s two callers on the drop/repair paths were already reading
  `outcome` correctly before this patch (`_signoff_and_apply` at `flow.py:270`, and the
  batch sweep) — the patch only changes when the notice is printed, not the return value —
  so no downstream caller needed to change, matching the brief's stated scope.

## Test coverage

- The two new regression cases (`NotRecorded.test_a_dropped_decision_is_not_announced_as_applied`,
  `test_a_repaired_unsignable_summary_is_not_announced_as_applied`,
  `template/tests/test_signoff_orphan.py:328-384`) are exactly the gap the carried-forward
  sign-off rejection asked for, and they exercise the real production path
  (`flow._signoff_and_apply`, not a re-implementation of the guard logic). `gate-logs/C4-verify.log`
  confirms all four new/changed assertions (the two C6 cases plus the two new `NotRecorded`
  cases) genuinely red pre-fix and green post-fix.

## Reuse / simplification

- The generalized `_Base._announced(d, needle)` (`test_signoff_orphan.py:122-128`, was
  `_announced(d, action)`) is reused as-is by every new assertion rather than re-deriving the
  stderr-scan inline — exactly what the carry-forward's "keep as-is" note asked for. No
  duplicated logic introduced.

No other findings. The diff is a tightly scoped, single-condition fix plus proportionate
test coverage; nothing here needs human adjudication.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] Validation — fitness-to-purpose — Decide whether the resulting stderr timing and wording communicate the sign-off outcome appropriately to operators across successful and refused/repair flows — this is the final product judgment despite complete automated behavioral coverage (`template/src/pdca_harness/flow.py:257`).
- [x] leaf produced no usable verdict (needs a human) — plan-advisory leaf 'plan-reviewer' did not produce findings (produced no artifact); re-run it or adjudicate by hand.

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
- By / date: Eduard Ralph / 2026-08-15

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 0 finding(s); brief revised: no (plan-advisory-*.md)
- (empty is the common case)
