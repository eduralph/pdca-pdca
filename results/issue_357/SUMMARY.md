# Result — issue 357 / state-machine-consolidation-superseded-by-migration-steps

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: #357 asks to make the bundle state machine explicit and single-sourced: (1) a written spec checked against the code, (2) name the HELD state, (3) one definition per question ("is this finished?", "did a cycle run?", "what does an iterate archive?", "does this take the close path?"), (4) one dispatch boundary as a tested invariant, (5) transition guards as data. It was filed before the 2026-10-15 approach review. That review's accepted proposal (`docs/design/proposals/accepted/0002-target-architecture.md`) and roadmap (`docs/design/architecture/09-build-order-and-roadmap.md:34-41`) now schedule this work as migration step 4 (#713, 0.70: "`state(records) -> State` and `next(state, records, config) -> Action`, no I/O … collapses `flow.flow` and `flow_ids` … the transition-table test is generated from the state diagram") and step 5 (#714, 0.67: Policy protocol — sizing, plan policy, dependency halt etc. behind "records in, Hold or Proceed out"; every phase returns `Ok / Held(reason) / FailedInfra`). The state diagram itself is already written (`docs/design/architecture/06-runtime-view.md:13-38`). Doing #357 separately in 0.60 would build a second consolidation of the same machine ahead of the planned one.
- Success criterion: (1) #357 is closed as a duplicate (GitHub "not planned") with a closing comment that maps each of its five goals to where it now lives: (1) spec → #713 (transition-table test generated from the diagram) + `06-runtime-view.md` §6.1; (2) HELD → #714 (`Held(reason)` outcome); (3) one definition per question → not named in either, carried to #713 (below); (4) one dispatch boundary → #713 (one loop, `flow.flow` deleted) — the "tested invariant across all four entry paths" half is not in #713's exit gate, so it is carried to #713 explicitly (below); (5) guards as data → #714 (Policy protocol). The closing comment also names the one piece of #357 evidence that is not a goal — "a state reached without its predecessor" (BUILT from `brief.md` + `patch.diff` with no gate record; the #321 gating) — as **not carried: a behaviour change, to be filed separately if still wanted**, as #357 itself says. (2) A comment on **#713** and a comment on **#714**, each linking #357 and asking that step to check #357 for any input it does not cover yet before its design starts — the text is in "Tracker comments" below. The #713 comment also lists goal (3)'s open examples, so they are not lost. The maintainer confirmed this close in the Plan session (2026-10-23); that confirmation is not in notes.json, so sign-off must re-record it in §9, including explicit acceptance that the work moves from #357's 0.60 to 0.67 (#714) / 0.70 (#713), against the thread's "schedule it now" argument.
- Repo + branch target: eduralph/pdca-harness @ main (no patch)
- Scope (one logical fix) / out of scope: Close #357 as superseded, with the goal-by-goal mapping; comment on #713 and #714 asking each to check #357 for missing input, carrying goal (3) onto #713. / out of scope: any code or doc change; changing the milestones of #713/#714; re-opening the design of steps 4–5.

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: duplicate
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

The reviewer leaf was skipped: this bundle's Plan concluded a close / no-fix disposition (duplicate), so there is no patch to review.

- NEEDS-HUMAN — Confirm the close disposition 'duplicate' (no patch was built). Override to a fix path (iterate-to-Do) if the close is wrong.


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] Confirm the close disposition 'duplicate' (no patch was built). Override to a fix path (iterate-to-Do) if the close is wrong.
- [x] **Goal (4) loses its "tested invariant" half.** #357 goal 4: "make that a stated invariant with a test, so the next guard is not proposed for `flow.py` again", across **four** paths ("`flow.flow`, the zero-id sweep, `flow.flow_ids` and `pdca run`"). The brief maps it to "#713 (one loop, `flow.flow` deleted)". But #713's exit gate is only "`flow.flow` deleted; `_drive_and_act` under 120 lines" (`09-build-order-and-roadmap.md:39`), and the proposal only "Replaces the `flow.flow` / `flow_ids` pair" (`0002-target-architecture.md:46`). Neither names the zero-id sweep, `pdca run`, or a test asserting a single dispatch boundary. Fix: add goal 4's invariant-test request to the #713 carry-over comment, the same way goal 3 is carried. Otherwise it is a goal with no explicit home, which the brief's own Falsifiability line calls the forbidden state.
- [x] **Goal (1)'s "cannot silently drift" depends on an unverified quote.** The brief cites #713 for "the transition-table test is generated from the state diagram". That wording is not in the repo docs: the roadmap exit gate (`09-…:39`) and the proposal (`0002-…:46`, "makes the transition table testable without disk") say nothing about generating the test from the diagram. Also, the diagram the brief points to (`06-runtime-view.md:18-38`) has no HELD state and no guards, so a test generated from it today would not cover goals 2 and 5. Sign-off must read #713's body to confirm the quote before closing. If the quote is not in #713, carry goal 1 explicitly in the #713 comment as well.
- [x] **The "held? is answered twice" example misses a same-named third predicate.** `drive_claim.held(cfg, d)` (`template/src/pdca_harness/drive_claim.py:254`) is a different question: whether another live run holds the drive claim (#566). It shares the name with `driver.held(final)` (`driver.py:207`). The same expression also appears inline in `run_issue`'s loop (`driver.py:197`). This name collision is exactly the "one definition per question / named callers" hazard #357 goal 3 describes. The #713 carry-over comment should list it so the step-4 design does not merge or confuse them.
- [x] **One evidence item from the thread is dropped without a home.** #357's "A state reached without its predecessor" (BUILT derived from `brief.md` + `patch.diff` with no gate record, never re-entering PLANNED, and the #321 gating that "dragged a paid model call onto a beat where its advice cannot be acted on") is not mentioned in the closing comment or in either carry-over comment. It is evidence, not one of the five goals, so the brief's goal-level falsifiability check does not catch it. #357 itself says behaviour changes "should be its own issue". The closing comment should name where that lives, either an existing issue or "none; file separately", so the close does not silently drop it.
- [x] **The maintainer confirmation has no record in the inputs.** The brief says "The maintainer confirmed this close in the Plan session (2026-10-23)". notes.json has only the issue body and the automated-triage comment. The thread also argues against waiting: "it should be scheduled now, because every further increment makes the eventual consolidation larger". The superseding steps land at 0.67 (#714) and 0.70 (#713) (`09-…:43-45`), roughly ten milestones after #357's 0.60 target. The human at sign-off should explicitly accept that delay, since the thread does not record it.

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
- Plan advisory: 5 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
