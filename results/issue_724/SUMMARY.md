# Result — issue 724 / flow-builds-each-bundle-on-its-declared-prerequisites

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: In stack mode every runnable bundle is pointed at the run's one integration line (`_point_at_integration`, `template/src/pdca_harness/flow.py:890`, called at `:2549`). That line holds every earlier-wave bundle of the target, so a PR's branch carries unrelated bundles' work. Merging it lands work whose own PR the human closed (#630, moved onto #463).
- Success criterion: Real-git tests driving `flow._drive_and_act` through real folds on the `StackFoldGit` fixture, with build and sign-off stubbed and `_publish_bundle` cutting each PR branch from the recorded stack-base tip, as `template/tests/test_flow_same_wave_conflict.py:131` does:
  (1) **The #630 case.** `A`, `Z` (wave 0, unrelated, two commits each), `B` (`Depends on: A`). Every commit of `origin/main..fix/A` is on `fix/B`; no commit of `origin/main..fix/Z` is. All COMPLETE.
  (2) **Transitive.** `C` (`Depends on: B`): `fix/C` has `fix/A` and `fix/B`, not `fix/Z`.
  (3) **Conflict partner.** `E` (`Conflicts with: A`): `fix/E` has `fix/A`, not `fix/Z`.
  (4) **In-batch `Depends on (merged)`.** `G` (`Depends on (merged): A`): `fix/G` has `fix/A`, not `fix/Z`.
  (5) **Empty closure → real base.** `H` whose only edge is to an in-batch `N` that closed with no patch: stack base cleared; `fix/H` has neither `fix/A` nor `fix/Z`.
  (6) **Carried prerequisites (#646).** Carried clean `P`, `X`; planned `D` (`Depends on: P`), `E` (`Depends on: X`): `D`'s base has `fix/P` not `fix/X`, `E`'s the reverse. Both COMPLETE. Includes resume through a finished patchless bundle (the v2 reviewer's two repros, `iteration-v2/SUMMARY.md` §5).
  (7) **Carry defect: foreign ancestry.** Carried `P` cut from an old line holding carried `X`; `D` (`Depends on: P`): `D` stays PLANNED with no stack-base record; a `STOPPING` line names `issue_P` and `issue_X`.
  (8) **Carry defect: rewritten carried prerequisite (#633).** `fix/P` force-pushed after the carry: `D` stays PLANNED; a `STOPPING` line names `issue_P` and the rewrite.
  (9) **#655 judged on the base `D` gets.** Out-of-batch `P`'s PR merges into `main` after the first fold: `D` is not held; it is COMPLETE and its base contains `P`'s merge commit.
  (10) Existing suites stay green; assertions restated only in terms of content, never weaker.
- Repo + branch target: eduralph/pdca-harness @ main (PRs target `main`). Base: the run's line `pdca-integration/main-r547f8028520f` at `fcae4aa` (`489e5fb` + #723; #723's PR #726 is open, not merged). Anchors here are on `fcae4aa`.
- Scope (one logical fix) / out of scope: `template/src/pdca_harness/flow.py` (closure + per-bundle bases, carry handling, #655 removal), `merged.py` (remove `merge_and_head`), `integrate.py` rewrite-message wording, and the tests restated per (10). / out of scope: holds for base-build failures and cross-wave overlaps, and all stack-rule docs (#725); merge mode; wave scheduling; PR targets; per-bundle base cleanup.

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: split
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
- [x] T5 Judgment — Confirm merged-history and closed/rejected-work coverage by every affected file path before deciding this duplicates no prior solution — the brief lists flow.py history and a rejected attempt, but the supplied target has one synthetic base commit and no remotes, so the full check cannot be independently established; brief.md:27; review-prior-art.log:1.
- [x] **The tracker record is missing, so the problem statement can't be checked against the thread.** The cwd holds only `brief.md` and `dependency-state.json`. There is no `notes.json` and no `sources/`. The Invariant cites "#630's finding (the comment on #463, 2026-10-10)". The Repro cites "the #630 test from the issue comment". Prior-art cites `iteration-v1/patch.diff` and says the review "reproduced" (7) and (8) against it. None of these is in the inputs, so neither this review nor Check can confirm that (7) and (8) are what that review asked for. Either attach the thread and the v1 review, or quote the load-bearing lines in the brief.
- [x] **`Depends on: 723` points at a bundle that isn't built, and the brief treats its code as already on the base.** `dependency-state.json` says `"723": {"exists": true, "state": "PLANNED"}`. On the target there is no per-bundle base-build function: `integrate.py`'s top-level defs (`:99`–`:980`) contain none, and no file under `template/` mentions `723`. Yet the Falsifiability line says "with the production change reverted (#723's code stays, it is on the base) it loads and fails on assertions". The Scope says "a base built by #723's function", never naming that function. Against `main` as it stands (`Repo + branch target: eduralph/pdca-harness @ main`), Do would be calling an API that doesn't exist yet, and the red→green claim can't be tested. Options: gate this bundle on 723 reaching accepted/merged; or name the exact function and signature 723 must provide and the base this bundle builds on (723's branch versus `main`); or make the dependency a stack edge.
- [x] **The brief's anchors are from a different tree than the target.** The target worktree HEAD is `d6057ebc8c9b`, but the brief keeps saying "On `489e5fb`". Several cited lines don't match the target:
- [x] **Criterion (10) names suites that don't exist on the target, so as written it can't be checked.** These are absent from `template/tests/`:
- [x] **Criteria (7) and (8) depend on behaviour that belongs to the unbuilt prerequisite, and don't say what "reports" means.** "the run reports the foreign ancestry naming `P` and `X`" and "the run reports the rewrite naming `P`" don't say where (stderr, exit code, a bundle record) or which message. Scope says the failure comes "with the error #723 raises". So whether (7) and (8) pass is decided by 723's error text and exit behaviour, which aren't fixed anywhere in this brief. Pin the observable: for example, the run exits non-zero before the wave, D's state stays unbuilt, and the error text contains `P` and `X`. Otherwise the test can be made to pass loosely.
- [x] **The #655 rework is a second change bundled in.** Scope removes `_line_lacks_merge` (`flow.py:850`, called at `:792`) and `merged.merge_and_head` (`merged.py:149`), rewrites docstrings `merged.py:24` and `:188`, and flips the existing #655 hold tests (criterion 9). It is causally linked: once D isn't cut from the line, asking whether the line lacks P's merge is the wrong question. But it changes hold behaviour for every bundle ("by `merged.merged_into` alone for every bundle"), including bundles whose closure is empty. Meanwhile the brief defers every other doc and docstring change to #725, so deleting this code and editing these docstrings here is inconsistent with that deferral. The human should decide explicitly whether #655's flip belongs in this child or a sibling.

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
- issue_727: add `723` to its `Depends on` so the scheduler holds it until #723 (PR #726) is accepted — the split format could only carry it as an ordering note.
