# Result — issue 725 / hold-a-bundle-whose-own-base-cannot-be-built

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: On the run's line (after #723, #727, #728, #729), a failure that belongs to one bundle stops the whole run. (a) Building a bundle's own base fails — `main` moved mid-run and clashes with a prerequisite, a rewritten in-batch prerequisite (#633), a failed fetch, a refused push of the per-bundle base branch: `_bundle_bases` re-raises (`template/src/pdca_harness/flow.py:1019-1022` on `75a886e`) and the wave loop prints `STOPPING` (`flow.py:2765-2770`). (b) A bundle built on its own base clashes at the line fold with a bundle from an EARLIER wave: `_held_by` holds only same-wave clashes (`integrate.py:1743-1767`, called at `:640`), anything else raises and `flow.py:2871-2877` stops. Unrelated bundles stay PLANNED. The docs, glossary and docstrings still state the old rule ("a later wave's PR carries every earlier-wave branch on the line").
- Success criterion: Real-git tests through `flow._drive_and_act` on the `StackFoldGit` fixture (`template/tests/test_integrate_stack_bases.py:123`), loaded by path as `template/tests/test_flow_same_wave_conflict.py:36-56` does. Per child (split-proposal.md): child 1 — moved base (last wave), rewritten in-batch prerequisite, failed fetch, refused push each hold one bundle and its dependents/partners, the rest of the wave completes; child 2 — a cross-wave clash at the line fold (with an in-batch bundle, a finished bundle carried onto the line, or a bundle the moved base stranded) holds the incoming bundle naming its partners, the run does not stop; child 3 — no tracked file states the old rule. Pre-change, every behaviour case ends in `STOPPING` with the unrelated bundle PLANNED.
- Repo + branch target: eduralph/pdca-harness @ main (PRs target `main`). Do builds and the gate verifies on the run's line `pdca-integration/main-r547f8028520f` (tip `75a886e`, holding #723, #727, #728, #729), exported as `$PDCA_VERIFY_BASE`. `path:line` anchors are on `75a886e`.
- Scope (one logical fix) / out of scope: see the three children in `split-proposal.md`. Human decisions recorded here: (1) three children, docs last; (2) a bundle whose own base came from a moved `main` and clashes at the fold with a line bundle cut from the old `main` is HELD out of the line, named with that bundle and `<remote>/main`, fix "rebuild <that bundle>'s branch on the new <remote>/main" — bases are not pinned to the run's start; (3) exit code stays 1 when a hold leaves a dependent PLANNED (as #593/#674 holds do today); (4) when a path clashes only with several earlier bundles together, all of them are named (as `_held_by` does, `integrate.py:1766`). / out of scope: which base a bundle gets (#727-#729); carried-from-an-earlier-run prerequisites as base members and their failure cases (#735); the fold API (#723); merge mode; Plan-time overlap detection (#395); per-bundle base cleanup on origin.

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
- By / date: Eduard Ralph / 2026-10-15

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
