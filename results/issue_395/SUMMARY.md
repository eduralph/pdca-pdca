# Result — issue 395 / same-wave-conflict-refused-at-accept

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: see the issue: two real batches published same-wave PRs that conflict, found
  only at the post-publish fold.
- Success criterion: the union of the three children's criteria (each child is
  self-contained and gate-evaluable on its own).
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: see "Intended split". / out of scope: the last wave and one-wave runs;
  re-sequencing a refused bundle into a later wave of the same run and writing
  `Conflicts with` automatically; a conflict that also involves line work (#747
  `_held_by_line`); the issue's layer 1 (Plan-exit advisory over predicted files); the
  standalone `pdca signoff --accept`; merge mode; the advisory `_audit_wave_overlap`
  (flow.py:1586) behaviour beyond child 3's parser fix; documenting "accepted ⇒ PR" with
  its two existing exceptions (T4-failed texts, failed push).

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: new-feature
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — N/A — close disposition (no patch to verify)
- C3 Change: none — patch.diff
- C4 Verification (red→green): none — N/A — close disposition (no patch to verify)
- C5 Causal adequacy: none — reviewer + human sign-off

## 4. Conformance (Check — stack)
- T1 Structure: none — N/A — close disposition (no patch to verify)
- T2 Shape: none — N/A — close disposition (no patch to verify)
- T3 Runtime: none — N/A — close disposition (no patch to verify)
- T4 Contribution: none — N/A — close disposition (no patch to verify)
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

# Advisory review — SKIPPED (close disposition)

The reviewer leaf was skipped: this bundle's Plan concluded a close / no-fix disposition (split), so there is no patch to review.

- NEEDS-HUMAN — Confirm the close disposition 'split' (no patch was built). Override to a fix path (iterate-to-Do) if the close is wrong.


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] Confirm the close disposition 'split' (no patch was built). Override to a fix path (iterate-to-Do) if the close is wrong.

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
- By / date: Eduard Ralph / 2026-10-23

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
