# Result — issue 469 / flow-adopt-split-children

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: 
- Success criterion: exercised **through `cli._flow`** on byte-identical disk state,
  both CLI shapes: (1) a run whose Plan/re-plan beat splits a drive-set bundle drives
  that bundle's children to a terminal state within the same call — in a wave AFTER the
  parent's, honouring their `Depends on` / `Conflicts with`, counted against ONE
  run-wide `max_passes` budget, each adoption announced on stderr with the child's REAL
  wave index from the recomputed schedule; (2) a run handed an id whose bundle is
  ALREADY terminal on a split adopts its stranded children (recovery, #449 iteration-1
  RULING (b)) — no pre-run short-circuit swallows it; (3) both shapes produce the same
  child states, announcements and exit code. A child with an unresolvable dependency is
  held loudly, excluded from the results map, and the run continues — never aborts.
  Adoption is lineage-scoped and transitive (only descendants of the ids given), never a
  disk sweep; an adopted child that itself splits is re-adopted within the same shared
  budget — bounded, no recursion reset. Guards proven by test, not just present: a
  split-marked but NON-terminal parent (e.g. sign-off recorded `iterate-do`) does NOT
  have its children adopted; a lineage child id that escapes the bundle root (e.g.
  `"../../etc"`) is skipped with a report; an id already in the run's drive set is not
  adopted twice (dedup against the batch AND a duplicate id within one record).
  Demonstrable by C4-verify on the patch alone.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: adopt the children of a bundle that goes (or is found) `close-disposition =
  split` while in the drive set — detect (read `split.read_lineage`; a parent with the
  marker but no readable record is reported and skipped, never a crash), validate
  (`waves.partition_schedulable` tolerance; held children reported in the existing
  "held this run — <reason>; left in-flight" shape and EXCLUDED from the results map),
  splice (children join after the current wave; pointed at the same per-target
  integration branch via the existing `_point_at_integration`; one run-wide `max_passes`
  pool across original AND adopted waves; adopted children join the set
  `_warn_abandoned` / final sweep cover), report (real wave indices, identical on both
  CLI shapes) — on the unified drive path from child-1, so `flow`, `flow_ids` and
  `flow_batch`'s drive phase inherit it from one implementation.
  / out of scope: changing why recursive splits happen (#448's line — merely never
  enable an infinite one); a disk sweep in `flow_ids` (the distinction from the CSV
  sweep is deliberate and stays); the `--accept` hint printing `pdca flow <child-ids>`
  (still right for a split accepted outside a running flow); `waves.compute_waves` /
  `partition_schedulable` semantics (reused as-is); the split command, `split.accept`,
  or the lineage schema (#456 shipped it — independent optional edges, NO `role` field,
  `children` iff split); publish/fold semantics beyond the existing reconciliation; the
  pre-existing T3 red (`template/tests/test_verify_base.py` under inherited
  `PDCA_VERIFY_BASE` — verified pre-existing isolation fault, non-gating, expect it, do
  not chase it).

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
- By / date: Eduard Ralph / 2026-08-09

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
