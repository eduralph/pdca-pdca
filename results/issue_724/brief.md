- **Slug:** flow-builds-each-bundle-on-its-declared-prerequisites
- **Defect:** In stack mode every runnable bundle is pointed at the run's one integration line (`_point_at_integration`, `template/src/pdca_harness/flow.py:890`, called at `:2549`). That line holds every earlier-wave bundle of the target, so a PR's branch carries unrelated bundles' work. Merging it lands work whose own PR the human closed (#630, moved onto #463).
- **Success criterion:** Real-git tests driving `flow._drive_and_act` through real folds on the `StackFoldGit` fixture, with build and sign-off stubbed and `_publish_bundle` cutting each PR branch from the recorded stack-base tip, as `template/tests/test_flow_same_wave_conflict.py:131` does:
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
- **Falsifiability:** Offline, real git. On `fcae4aa`, `_point_at_integration` writes the run's line into every runnable bundle's `stack-base`, so `fix/B` holds `Z`; `_line_lacks_merge` holds `D` in (9).
- **Invariant to restore:** What a bundle is built on is decided by what it declares, not by when it was scheduled. Its base carries exactly the accepted work of the bundles it is ordered after by a declared edge (`Depends on` and in-batch `Depends on (merged)`, transitively; an earlier-wave `Conflicts with` partner) that this run built or carried, and nothing else of the run. Empty set → the real base. Source: #463 and #630's finding (`results/issue_463/notes.json`); `09-parallel-lanes.md:59-61`.
- **Repo + branch target:** eduralph/pdca-harness @ main (PRs target `main`). Base: the run's line `pdca-integration/main-r547f8028520f` at `fcae4aa` (`489e5fb` + #723; #723's PR #726 is open, not merged). Anchors here are on `fcae4aa`.
- **Depends on:** 723
- **Ordering note:** Calls #723's `integrate.build_bundle_base` (`integrate.py:716`).
- **Surfaces:** none (driver internals)
- **Difficulty:** high
- **Scope:** `template/src/pdca_harness/flow.py` (closure + per-bundle bases, carry handling, #655 removal), `merged.py` (remove `merge_and_head`), `integrate.py` rewrite-message wording, and the tests restated per (10). / out of scope: holds for base-build failures and cross-wave overlaps, and all stack-rule docs (#725); merge mode; wave scheduling; PR targets; per-bundle base cleanup.
- **Repro instruction:** On `fcae4aa`: `StackFoldGit`, publish `A` and `Z`, fold `[A, Z]`, publish `B` cut from `origin/<line>`; `fix/Z`'s tip is an ancestor of `fix/B`.
- **External dependencies:** none (Python 3.11+ standard library and git, the base toolchain).
- **Test file:** template/tests/test_flow_dependency_scoped_bases.py (new)
- **Citations expected:** path:line on `fcae4aa`.
- **Prior-art check (triage cycles):** #674, #655, #633, #629, #646 on `flow.py`; two rejected attempts in `iteration-v1/`, `iteration-v2/`.
- **Disposition hint:** split

## Split plan (decided with the human, 2026-10-17)

Iteration 2 was sent back to Plan as oversized (151 KB, 12 files; new implementation findings every round). Split into exactly three children, each leaving the tree no worse than before:

- **(a) in-batch dependency-scoped bases** — criteria (1)-(5) and the rewrite-message fix: record which head each bundle's own base took and feed it to the #633/#695 checks, and word those messages to name the bundle base that took the head and that bundle's PR (no PR is cut from the line any more). Seam rule: a bundle whose closure reaches a **carried** bundle, or a member `build_bundle_base` cannot take (an `Onto branch` member, a legacy `Stacks on` bundle, `integrate.py:880-925`), keeps today's line base unchanged; the #655 check (`_line_lacks_merge`) stays as it is (too cautious, not a regression).
- **(b) carried prerequisites** — criteria (6)-(8): carried bundles become base members with their carried heads; finished patchless bundles stay in the dependency graph so transitive edges survive a resume. `Depends on: (a)`.
- **(c) #655 rework** — criterion (9): `_runnable` judges an out-of-batch merged prerequisite by `merged.merged_into` alone; remove `_line_lacks_merge` (`flow.py:850`, call `:792`) and `merged.merge_and_head` (`merged.py:149`); flip the `test_flow_merged_prereq_on_line.py` hold cases. `Depends on: (a)`, `Conflicts with: (b)` (both edit `flow.py`'s `_runnable` / closure area).

Legacy `Stacks on` / `Onto branch` prerequisites: decided — keep the line base for such dependents (no regression); not otherwise addressed in this split.
