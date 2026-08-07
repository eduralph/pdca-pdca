# Result — issue 384 / no-issue-mode-into-the-t4-gate

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: `publish()` relaxes a **failed** T4 contribution gate to a printed flag whenever
  it runs under `--no-issue` (`template/src/pdca_harness/publish.py:195-206`). The premise is
  that the one thing legitimately missing is the not-yet-assigned tracker id — but the gate is
  never told which mode it ran in (`_t4_passes` exports only `PDCA_BUNDLE`,
  `publish.py:713-718`), so the amnesty covers the **whole** checker: a PR body with no
  `**User impact:**` opener, an opener that falls after Root cause, a broken commit message —
  everything `contribcheck` would have caught (`template/src/pdca_harness/cli.py:1086-1117`) is
  waved through as "pending id" and pushed. The checker already has the narrow mode
  (`contribcheck --no-issue` → `contribution_problems(d, no_issue=True)` drops *only* the
  tracker-id requirement, `cli.py:228-229,1110-1116`); publish simply never uses it.
  Secondary defect in the same function, from the #338 rework: the immediate pre-run announce
  line was dropped in favour of the heartbeat alone, so publish's first action after its guards
  is silent until the first tick — the very "reads as a hang" finding of #181. The peer gate
  runner still announces (`template/src/pdca_harness/gates.py:504`).
- Success criterion: With the patch applied, under `--no-issue` a bundle whose contribution
  artifacts fail T4 for **any reason other than the missing tracker id** (e.g. no
  `**User impact:**` opener) is REFUSED — publish returns non-zero and pushes nothing — while a
  bundle whose only T4 problem is the absent tracker id proceeds; and in the default (id-known)
  mode the tracker-id requirement is still enforced. The mode reaches the checker as
  `$PDCA_PENDING_ID` derived from the flag on each run, never inherited from the ambient
  environment (an inherited value is scrubbed, not honoured), and the shipped gate row consumes
  it as `contribcheck --no-issue`. Demonstrable by C4-verify alone: the named test module is red
  with the production hunks reverted and green with them applied.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: one logical change — the publish-time T4 verdict must be evaluated in the mode the
  run is actually in, so the pending-id path relaxes only the tracker-id requirement and the
  blanket relax branch is deleted outright; plus the restored pre-run announce for the first
  T4 gate (with the heartbeat label unprefixed, since the announce already says "T4 gate").
  The mode must reach the shipped checker through the registered gate row in
  `template/pdca.toml.jinja`, so a rendered instance gets the behaviour without editing its own
  config. Keep the `id_pending` recording and the "add the id and re-gate before ready"
  discipline (`publish.py:369,388,489,497`) exactly as they are.
  / **out of scope:** how a *Check-time* default-open T4 row is recorded in the gate matrix
  (issue 401 — briefed separately, later wave); the `at_publish` selection rules (#339);
  any change to `contribution_problems`' lint rules themselves; the `texts_prevalidated`
  pre-pass path (`publish.py:185-190`), which must keep skipping T4 exactly as it does now.

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

Review of issue 384: narrow `publish --no-issue` T4 amnesty to the missing tracker ID while preserving all other contribution gates and restoring the pre-run announcement.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The acceptance boundary is decidable: pending-ID publication may omit only the tracker trailer, while malformed contribution content must still stop before push (`template/src/pdca_harness/publish.py:198`). |
| C2 Reproduction (red pre-fix) | PASS | In a disposable target copy with only production hunks reverted, 6 selected tests ran and produced 5 failures plus 1 error, including the former blanket-amnesty behavior (`template/tests/test_publish_slice.py:395`). |
| C3 Change | PASS | The change is confined to publish/checker mode propagation, the T4 decision, its operator announcement, tests, and matching user-facing template text; the blocking decision remains at `template/src/pdca_harness/publish.py:207`. |
| C4 Verification (red→green) | PASS | Independent red was 6/6 failing or erroring without production hunks; with the patch, both focused modules ran 77 tests green, covering narrow amnesty and default enforcement at `template/tests/test_publish_slice.py:423`. |
| C5 Causal adequacy | PASS | The blanket post-failure bypass is removed and the checker receives run-derived mode before deciding which single rule applies, so the cause is transformed rather than hidden behind a capability/runtime guard (`template/src/pdca_harness/cli.py:1101`, `template/src/pdca_harness/publish.py:798`). |
| T1 Structure | PASS | Mode derivation remains in the publish runner and rule selection remains in the contribution checker, preserving the existing gate boundary (`template/src/pdca_harness/publish.py:781`, `template/src/pdca_harness/cli.py:1108`). |
| T2 Shape | PASS | The patch is syntactically/import structurally sound: the complete offline template suite passed, and the announcement contract is asserted before runner invocation at `template/tests/test_t4_publish_gate.py:127`. |
| T3 Runtime | NEEDS-HUMAN | Copier must be provided and the 7 root render/update tests rerun — all were skipped because Copier is not installed, so rendered-instance and update compatibility were not exercised despite the offline runtime suite passing. |
| T4 Contribution | PASS | The recorded contribution gate is green, and an independent closed-PR query by every affected path plus merged-history inspection found prior related work but no competing implementation of this narrow mode contract; the shipped-row behavior is exercised at `template/tests/test_publish_slice.py:423`. |
| T5 Judgment | PASS | The human need only weigh the documented Copier caveat: the behavioral change is narrowly causal, offline red→green is reproduced, and no ambiguous scope expansion or symptom guard remains (`template/src/pdca_harness/publish.py:198`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether real pending-ID publish behavior and the immediate terminal announcement are acceptable in an actual rendered instance — automated dry-run tests establish mechanics but cannot own release fitness (`template/tests/test_t4_publish_gate.py:127`, `template/tests/test_publish_slice.py:423`). |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T3 Runtime — Copier must be provided and the 7 root render/update tests rerun — all were skipped because Copier is not installed, so rendered-instance and update compatibility were not exercised despite the offline runtime suite passing.
- [ ] Validation — fitness-to-purpose — Decide whether real pending-ID publish behavior and the immediate terminal announcement are acceptable in an actual rendered instance — automated dry-run tests establish mechanics but cannot own release fitness (`template/tests/test_t4_publish_gate.py:127`, `template/tests/test_publish_slice.py:423`).

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
- Iteration delta (if iterating): Auto-iterate (round 1): Check found implementation-level items only, no architectural judgment required — T3 Runtime — Copier must be provided and the 7 root render/update tests rerun — all were skipped because Copier is not installed, so rendered-instance and update compatibility were not exercised despite the offline runtime suite passing.
- By / date: auto-iterate / 2026-08-06

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
