# Result — issue 449 / flow-adopt-split-children

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: a split that happens *inside* a driven flow no longer strands its own
  children. When a bundle in the drive set reaches `close-disposition = split`, the run
  enumerates that bundle's children from its lineage record, validates them with the
  tolerance the resume path already uses, splices them into the remaining waves, and says
  so — instead of ending with the parent terminal, the children sitting PLANNED, and the
  operator restarting by hand with `pdca flow <child-ids>`. Both CLI shapes (`pdca flow
  <parent>` and `pdca flow <parent> <other>`) do the same thing to the same disk and
  report it the same way — **by construction**, not by per-divergence patching.
- Success criterion: on byte-identical disk state (a parent terminal on
  `close-disposition = split` with PLANNED children carrying a valid
  `split-lineage.json`, or a parent whose Plan/re-plan beat splits it mid-run),
  `pdca flow <parent>` and `pdca flow <parent> <other-id>` — exercised **through
  `cli._flow`**, not hand-picked `flow.*` calls — drive the children to a terminal state
  within the same call, in a wave AFTER the parent's, honouring their `Depends on` /
  `Conflicts with`, counted against one run-wide `max_passes` budget, each adoption
  announced on stderr with the child's REAL wave index; and both invocations produce the
  same child states, the same adoption announcements, and the same exit code. A child
  with an unresolvable dependency is held loudly (excluded from the results map) and the
  run continues. An explicit-id flow adopts only lineage descendants of the ids it was
  given (transitively, bounded by the run budget) and never widens into a disk sweep.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: adopt the children of a bundle that goes (or is found) `close-disposition =
  split` while it is in the drive set — detect via `split.read_lineage`, validate via
  `waves.partition_schedulable`, splice after the current wave, report with real wave
  indices — with entry-point parity restructured to hold by construction (single results-map
  path through `cli._flow`).
  / out of scope: changing *why* recursive splits happen (448's line — this slice must
  merely not enable an infinite one; adoption shares the run's iteration budget); a disk
  sweep in `flow_ids` (the distinction from the CSV sweep is deliberate and stays); the
  `--accept` hint printing `pdca flow <child-ids>` (still right for a split accepted
  outside a running flow); `waves.compute_waves` / `partition_schedulable` semantics
  (reused as-is); the split command, `split.accept`, or the lineage schema (456 shipped
  it; note it has **independent optional edges and no `role` field** — detection is
  `read_lineage(d)` returning a dict with a `children` key, `split.py:392-395`);
  publish/fold semantics beyond pointing an adopted child at the same per-target
  integration branch through the existing `_point_at_integration` (`flow.py:621`); the
  pre-existing T3 red (11 failures in `template/tests/test_verify_base.py` under an
  inherited `PDCA_VERIFY_BASE` — a verified harness test-isolation fault, non-gating,
  expect it again, do not chase it).

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
- [ ] Confirm the close disposition 'split' (no patch was built). Override to a fix path (iterate-to-Do) if the close is wrong.

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: discontinued
- Iteration delta (if iterating):
- By / date: unknown / 2026-08-11

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
