# Result — issue 506 / decomposed-into-two-shippable-outcomes

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: Issue 506 reports one incident — an escalated builder ran ~18 minutes, the API
  connection dropped mid-response, the attempt was burned and `build.error.log` recorded only
  `(no output captured)` — but names **three** weaknesses that live in two layers meeting
  only at `LeafError`: the stream reader never reads or retains the CLI's own terminal error
  report and classifies "transient" by the proxy *did the child produce any event*
  (`template/src/pdca_harness/progress.py:147-158`, `:255`, `:365-377`); and the
  leaf-invocation layer never puts the builder on the resilient path at all
  (`leaves.py:1824` vs `:2507` / `:2840` / `:3142`), reports an exhausted death as an argv
  plus an exit status, and harvests artifacts without asking which attempt wrote them
  (`:2519-2523`, `:2851-2854`, `:3152-3155`). Built as ONE slice it reached 92,086 bytes
  against an 80 KB backstop over four rounds, each round's mechanism independently confirmed
  and each round's findings implementation-shaped — the signature of a slice too large to
  converge. The iteration-4 sign-off rejected it on **slicing, not mechanism**
  (`iteration-v4/SUMMARY.md` §9) and directed the split into this beat.
- Success criterion: This bundle ships **no patch**. It is discharged when issue 506 is
  decomposed into children that are each one shippable outcome with its own red, filed as
  tracker sub-issues of 506 with a materialised bundle each, and the parent is marked
  `close-disposition = split` so the run drives the children instead of rebuilding the
  rejected slice. Observable: `results/issue_506/split-lineage.json` names both children;
  each child bundle holds an authored `brief.md`; both tracker issues exist as sub-issues of
  #506. The substantive criteria of #506 now live in the children — child-1 (i)-(vi),
  child-2 (i)-(iv) — and Check judges them there, one bundle at a time.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: Decompose issue 506 into its two shippable outcomes and hand them to the run:
  author a complete brief per child, file each as a tracker sub-issue, materialise a bundle
  each, and mark this parent split. **Out of scope:** building any part of the fix here (the
  children own it); re-litigating the mechanism the four archived rounds established (it was
  endorsed — `iteration-v4/SUMMARY.md` §9 says KEEP ALL OF IT — and both child briefs carry
  it forward as requirements); a third child for the attempt-blind harvest (folded into
  child-1: same invariant, same file, and a third child costs a third full cycle).

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-close
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
- By / date: Eduard Ralph / 2026-08-16

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
