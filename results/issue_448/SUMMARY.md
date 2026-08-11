# Result — issue 448 / sizing-split-ratchet-decomposed

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: 
- Success criterion: issue 448 lands **no patch**, and its four asks are wholly
  carried by four bundles that exist on disk with an authored `brief.md` and a filed
  GitHub sub-issue of #448 — verified at Plan and re-checkable by inspection at sign-off:
  1. **456** `split-lineage-record` — ask 1 (record lineage at materialisation; owns the
     schema decision the other three read).
  2. **457** `sizing-ignores-sibling-conflicts` — ask 2 (stop the estimator scoring the
     split's own scheduling metadata).
  3. **458** `split-child-remedy-and-hatch` — ask 3 (depth-/evidence-aware remedy in
     `size_reasons` + the prompts).
  4. **459** `split-convergence-report` — ask 4 (convergence check before `--accept` files
     irreversible issues).
  The four child briefs carry the wave order **456 → 457 → {458 ∥ 459}** with
  `458 Conflicts with 459`, so no two of them are built blind on the same base. Nothing
  from ask 1–4 is left unowned by this bundle, and the `max_split_depth` cap the issue
  explicitly holds in reserve is claimed by none of them (correctly — the issue defers it).
- Repo + branch target: eduralph/pdca-harness @ main — of record only. This bundle
  publishes no PR (`close: no PR`, as split parent #332 did); the four children publish
  against this target individually.
- Scope (one logical fix) / out of scope: record the decomposition of issue 448 and carry it to sign-off for
  confirmation. / **out of scope:** every code change — all four asks belong to 456–459;
  re-opening the rejected single-slice implementation preserved in `iteration-v1/`
  (an `iterate-do` at sign-off archives the close marker and re-enables the full Do+Check
  band, which is the escape hatch if you reject the split); the `max_split_depth` cap
  (issue 448 defers it deliberately, and no child claims it).

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-close — the parent is terminal. The hint is documentation
  only: the driver honours the existing `split` **marker** outright and never consults the
  hint here, and `split` is deliberately absent from the close-disposition vocabulary
  because `close_class` substring-matches (`config.py:31-35`).
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
- By / date: Eduard Ralph / 2026-08-07

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
