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

Reviewing issue 384: make `publish --no-issue` waive only the missing tracker-id rule while preserving all other T4 blockers and restoring the immediate T4-run announcement.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The required decision boundary is explicit: pending-id mode may omit only the tracker trailer, while malformed contribution artifacts must still block (`template/src/pdca_harness/publish.py:198`). |
| C2 Reproduction (red pre-fix) | PASS | In an isolated target copy with only production hunks reverted, the retained regression suite failed with 6 failures and 1 error, including the malformed-body refusal at `template/tests/test_publish_slice.py:389`. |
| C3 Change | PASS | The change is confined to deriving the per-run gate mode, enforcing every residual T4 failure, restoring operator feedback, and matching tests/docs; no unrelated production behavior was found (`template/src/pdca_harness/publish.py:207`). |
| C4 Verification (red→green) | PASS | The same 77-test pair was red after production-only reversion and green on the patched target, directly exercising narrow amnesty, ambient-env scrubbing, and announcement ordering (`template/tests/test_publish_slice.py:423`; `template/tests/test_t4_publish_gate.py:127`). |
| C5 Causal adequacy | PASS | The blanket post-failure amnesty is removed and the checker receives the actual run mode before evaluating rules, so the erroneous decision point is corrected rather than guarded downstream (`template/src/pdca_harness/cli.py:1096`; `template/src/pdca_harness/publish.py:798`). |
| T1 Structure | PASS | Mode derivation remains in the publish gate runner and rule selection remains in the contribution checker, preserving the existing ownership boundary (`template/src/pdca_harness/publish.py:781`; `template/src/pdca_harness/cli.py:1101`). |
| T2 Shape | PASS | `git diff --check` and Python compilation pass, and the shipped-row contract is exercised without rewriting the registered command shape (`template/tests/test_publish_slice.py:431`). |
| T3 Runtime | NEEDS-HUMAN | Copier must be provided and all 7 root render/update tests rerun—they skipped because Copier and the declared `.venv` are absent, so rendered-instance and update compatibility remain unexercised (`tests/test_update_compat.py:1`). |
| T4 Contribution | NEEDS-HUMAN | The original contribution bundle must be supplied to `pdca-pdca contribcheck`—the scanner exists locally but its required commit/PR artifacts are not among the three reviewer inputs, so the recorded green cannot be independently reproduced. |
| T5 Judgment | NEEDS-HUMAN | A maintainer must decide whether closed/rejected work overlaps these affected paths—merged history was checked by path and open PRs were empty, but GitHub search cannot mechanically settle closed/rejected work by file path (`template/src/pdca_harness/publish.py:198`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Sign-off must decide whether the verified narrow tracker-id amnesty and restored pre-run feedback satisfy real publish operations, because fitness-to-purpose remains a human acceptance judgment (`template/src/pdca_harness/publish.py:825`). |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T3 Runtime — Copier must be provided and all 7 root render/update tests rerun—they skipped because Copier and the declared `.venv` are absent, so rendered-instance and update compatibility remain unexercised (`tests/test_update_compat.py:1`).
- [x] T4 Contribution — The original contribution bundle must be supplied to `pdca-pdca contribcheck`—the scanner exists locally but its required commit/PR artifacts are not among the three reviewer inputs, so the recorded green cannot be independently reproduced.
- [x] T5 Judgment — A maintainer must decide whether closed/rejected work overlaps these affected paths—merged history was checked by path and open PRs were empty, but GitHub search cannot mechanically settle closed/rejected work by file path (`template/src/pdca_harness/publish.py:198`).
- [x] Validation — fitness-to-purpose — Sign-off must decide whether the verified narrow tracker-id amnesty and restored pre-run feedback satisfy real publish operations, because fitness-to-purpose remains a human acceptance judgment (`template/src/pdca_harness/publish.py:825`).

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
- T3 `driver suite FAILED (rc 1)` was recorded for issue_384 AND issue_396 at the same second (13:18, concurrent flow runs) yet is unreproducible in 5 sign-off reruns incl. the exact oracle — find where it came from (concurrent-check interference?); the failing test name is unrecoverable because of the #402 last-line-only evidence stopgap.
