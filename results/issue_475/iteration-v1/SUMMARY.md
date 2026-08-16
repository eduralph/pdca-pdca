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

Review of issue #475: ensure a C6-refused recorded accept never promises “no new session,” while truthful no-session notices and state transitions remain intact.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The operator-facing invariant is bounded and falsifiable: C6 refusal returns `"blocked"`, while only that outcome reopens sign-off (`template/src/pdca_harness/flow.py:176`, `template/src/pdca_harness/flow.py:263`). |
| C2 Reproduction (red pre-fix) | PASS | With the new test hunks retained and only production reverted, both single and batch assertions fail on the base’s false no-session claim (`template/tests/test_signoff_orphan.py:186`, `template/tests/test_signoff_orphan.py:262`; `gate-logs/C4-verify.log:16`). |
| C3 Change | FAIL | The change must distinguish a successfully applied action from repair outcomes: `REASSEMBLE`/`None` mean the decision was not recorded, but the broad non-`"blocked"` branch calls it “applied” (`template/src/pdca_harness/flow.py:127`, `template/src/pdca_harness/flow.py:253`). |
| C4 Verification (red→green) | PASS | Independent production-only stash/reapply reproduced two red failures then eight green tests, preserving fresh-session and state assertions on both drive paths (`template/tests/test_signoff_orphan.py:183`, `template/tests/test_signoff_orphan.py:258`; `gate-logs/C4-verify.log:52`). |
| C5 Causal adequacy | PASS | The contested cause is removed by deciding before announcing, with no capability probe or eager-load symptom guard; C6’s authoritative `"blocked"` result now suppresses the premature promise (`template/src/pdca_harness/flow.py:252`). |
| T1 Structure | PASS | The delta stays within the existing shared decision boundary and its existing owning test module, so both callers retain one outcome path (`template/src/pdca_harness/flow.py:223`, `template/tests/test_signoff_orphan.py:118`). |
| T2 Shape | PASS | Independent `git diff --check` is clean, and both frozen shape runs show clean docs lint/render/link audits (`gate-logs/T2-docs.log:16`, `gate-logs/host-ci-docs.log:15`). |
| T3 Runtime | PASS | Pure-stdlib compilation and the target’s full driver suite pass independently; frozen runtime evidence also records 1,758 passing tests with two skips (`gate-logs/T3-suite.log:1123`). |
| T4 Contribution | N/A | Contribution artifacts do not exist at Check by design; the substantive, non-skippable T4 audit reruns at publish (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | FAIL | Operator-facing truthfulness is not yet acceptable: a repair reports “decision not recorded” and the patched caller immediately reports “applied,” yielding mutually exclusive guidance (`template/src/pdca_harness/flow.py:127`, `template/src/pdca_harness/flow.py:254`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Human must decide whether the final post-outcome wording earns operator trust across successful, blocked, and repair paths — automated red→green evidence cannot own that product decision (`template/src/pdca_harness/flow.py:238`). |

Prior-art check: affected-path GitHub history identifies the recorded-decision work as the origin of these files, and a complete current scan of open plus closed-unmerged PR file lists found no competing or rejected attempt touching either affected path.

### Advisory — code-review

# Advisory code review — issue #475 (no-new-session-notice-waits-for-the-guard)

## Findings

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/flow.py:252-256`. The new gate
  `if outcome != "blocked":` is broader than "the decision was actually applied." It also
  admits the two other non-`"blocked"` failure outcomes of `_apply_decision`:
  - `None` from the "no SUMMARY.md" drop (`flow.py:161-165`, which already prints
    `"... skipping record, will re-drive"` on the line immediately before),
  - `REASSEMBLE`/`None` from `_repair_unsignable` (`flow.py:114-130`, reached via
    `unrecordable()` at `:173-175` or the `ValueError` repair at `:186-192`, which already
    prints `"decision '<action>' not recorded (...); ... bundle returned to ... to reassemble"`).
  In both cases the decision was explicitly **not** recorded — the code just printed a message
  saying so — yet `_apply_recorded_decision` now prints, on the very next line,
  `"flow: <bundle> — applied the '<action>' sign-off decision already recorded in the bundle;
  no new session"`. That is a definite, past-tense claim ("applied") of a result that the
  preceding line just said did not happen; it is the same "notice claims a result a downstream
  step can still withdraw" defect the brief is fixing, reappearing one guard downstream of the
  one this patch targeted (C6). The old wording ("applying …", printed before the call) was at
  least ambiguous about success; the new wording is unambiguous and, for these two outcomes,
  false. The condition should gate on genuine success — e.g. `if outcome == action:` — not
  merely `!= "blocked"`. This path is reachable in exactly the scenario the fix is about: an
  orphaned decision already on disk (issue #453) whose bundle also lost/mangled its
  `SUMMARY.md` between the session and the driver's next pass — plausible, and structurally
  identical to `test_signoff_survives_a_leaf_that_reset_the_bundle`
  (`template/tests/test_flow_slice.py:316-336`), except reached via
  `_apply_recorded_decision` rather than a live session, which no test in this diff or the
  existing suite exercises. C4's red/green pair only covers the `"blocked"` case and the
  ordinary successful applies (`test_signoff_orphan.py:168,241,121,219`), so this gap passes
  every gate in `check-gates.json` undetected.

- `template/src/pdca_harness/flow.py:245-247` (docstring). "`'blocked'` is the one outcome
  where a session follows … so it is the one outcome that must not get this notice" restates
  the same over-generalization as the code bug above — it conflates "not blocked" with
  "successfully applied." Worth correcting alongside the code fix so the docstring doesn't
  keep asserting the same false dichotomy once the condition above is narrowed.

- `template/tests/test_signoff_orphan.py:186-189` and `:262-265` — minor reuse nit, not a
  defect. Both new assertions re-derive, inline, exactly what `_Base._announced`
  (`test_signoff_orphan.py:111-115`) already computes (lines matching both `d.name` and a
  substring); `self.assertFalse(self._announced(d, "no new session"), ...)` would say the same
  thing without duplicating the list comprehension across two test classes.

## Scope note

Both C6-guard-adjacent behaviours the brief targets — the announce-before-decide reordering
and the C6-refused case staying silent on "no new session" — are correctly fixed and covered
by `C4-verify` (log confirms red pre-fix on both drive paths, green post-fix). The first
finding above is the only correctness concern found in this diff; it sits just past the
brief's stated out-of-scope boundary (`_apply_decision`'s repair paths, `:161-192`) but is
introduced by the same edited condition/wording, so it is flagged as an implementation
narrowing rather than a new scope item.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] Validation — fitness-to-purpose — Human must decide whether the final post-outcome wording earns operator trust across successful, blocked, and repair paths — automated red→green evidence cannot own that product decision (`template/src/pdca_harness/flow.py:238`).
- [ ] `template/src/pdca_harness/flow.py:252-256`. The new gate
- [ ] leaf produced no usable verdict (needs a human) — plan-advisory leaf 'plan-reviewer' did not produce findings (produced no artifact); re-run it or adjudicate by hand.

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
- Iteration delta (if iterating): Rejected on the findings both review lenses agree on (reviewer C3/T5 + advisory code-review): the new notice gate `if outcome != "blocked":` (flow.py:252-256) is broader than "the decision was actually applied". It also admits the two outcomes where the decision was explicitly NOT recorded -- `None` from the missing-SUMMARY.md drop (flow.py:161-165) and `REASSEMBLE`/`None` from `_repair_unsignable` (flow.py:114-130). On those paths the run prints "decision '<action>' not recorded (...); bundle returned to ... to reassemble" and then, on the very next line, "applied the '<action>' sign-off decision ...; no new session". That is the same announce-a-result-a-downstream-step-can-withdraw defect this slice exists to remove, reappearing one guard downstream of the C6 one it targeted. What to change next: - Gate on genuine success -- e.g. `if outcome == action:` -- not `!= "blocked"`. - Fix the docstring at flow.py:245-247, which restates the same false dichotomy (it conflates "not blocked" with "successfully applied"). - Add the missing red case: an orphaned recorded decision whose bundle also lost or mangled SUMMARY.md, reached via `_apply_recorded_decision` rather than a live session. C4's current red/green covers only the "blocked" case and the ordinary successful applies, which is why this passed every gate undetected. - Minor, optional: the two new assertions re-derive inline what `_Base._announced` (test_signoff_orphan.py:111-115) already computes. Keep as-is -- do not re-do this part: the targeted announce-before-decide reordering and the C6-refused case staying silent on "no new session" are correct and covered on both drive paths (single `_signoff_and_apply` and the batch sweep).
- By / date: Eduard Ralph / 2026-08-15

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 0 finding(s); brief revised: no (plan-advisory-*.md)
- (empty is the common case)
- plan-reviewer produced no artifact in all 5 bundles of this sign-off batch (466/474/497/475/506) — systemic, not per-bundle: those briefs reached Do with no advisory pass, and each cost a human §6 adjudication. Act: find the leaf's failure mode, and decide whether a no-artifact plan advisory should hold Plan rather than pass through.
