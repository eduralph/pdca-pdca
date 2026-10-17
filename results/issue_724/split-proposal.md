<!-- pdca:split-proposal v1 -->
# Split proposal — issue_724

<!-- Each child is a COMPLETE brief, not a sketch. A filled Slug alone makes `state.state`
     classify the materialised file as PLANNED, so `pdca flow` skips Plan and sends it
     straight to Do — a child missing `Repo + branch target` then builds successfully and
     has nowhere to publish. Fill every field. -->

<!-- Delimiters are HTML comments, not headings, DELIBERATELY: each child body is a full
     draft brief and may contain arbitrary headings and fenced code blocks, so anything
     that could also appear inside a child cannot be its boundary. `pdca split --accept`
     parses these markers; keep them exactly as written. -->

## Why this slice is oversized

This proposal writes up the split the human already decided in Plan on 2026-10-17
(`brief.md` §"Split plan"). It is a split of #724's own new scope, not of inherited
sibling fields: #724 is the #463 child that changes how stack bases are chosen, and
iteration 2 came back at 151 KB across 12 files, with new implementation findings every
round. The v2 reviewer's last finding, finished patchless bundles dropping out of the
graph on resume (`iteration-v2/SUMMARY.md` §5), sat at the line between in-batch and
carried bundles, like most of the round-1 findings.

The sizer (`sizing.json`) called this one outcome and argued against two of these seams.
The human's plan answers both objections with one seam rule, which is what makes each
child shippable alone:

- **In-batch vs. carried.** The sizer worried this ships a "mixed rule". The rule here is
  that a bundle whose closure (the set of bundles it is ordered after, followed
  transitively) reaches a **carried** bundle, or a member `build_bundle_base` cannot take
  (an `Onto branch` member, a legacy `Stacks on` bundle, `integrate.py:880-925`), keeps
  today's line base, unchanged. So after child-1 every bundle is either correct under the
  new rule or exactly as it is on `fcae4aa`. Nothing regresses, and the #646 suites keep
  asserting what they assert today for carried dependents.
- **#655 rework.** The sizer said the core change regresses without it. That is only true
  if child-1 drops `_line_lacks_merge`. Child-1 keeps it. On a dependency-scoped base it
  asks about a tree the bundle no longer uses, so it is **too cautious** (it may hold a
  bundle that could run). It does not ship wrong work. Child-3 then removes it and judges
  out-of-batch merged prerequisites by `merged.merged_into` alone.

That leaves three outcomes, each with its own defect, criteria and test: (1) in-batch
bundles stop carrying unrelated work; (2) carried prerequisites join the new rule;
(3) the #655 hold stops firing on a tree the bundle does not build on. The split stops at
three because the human decided "exactly three" and because no child has a clean
sub-seam left. Child-1 is still the largest and is still high difficulty.

## Wave sketch

- **Wave 0: child-1** (in-batch dependency-scoped bases). It adds the closure walk and the
  per-bundle base recording that the other two build on.
- **Wave 1: child-2** (carried prerequisites). `Depends on: child-1`: it extends child-1's
  closure and base code to carried members, and narrows child-1's carried fallback.
- **Wave 2: child-3** (#655 rework). `Depends on: child-1`: it is only correct once
  bundles are no longer cut from the line. `Conflicts with: child-2`: both edit
  `flow.py`'s `_runnable` / closure area, so they must not build blind on the same base
  and collide at fold, even though neither needs the other's result. Declaring the
  conflict means `compute_waves` puts them in different waves. Which one goes first does
  not matter for correctness. Child-2 is listed first because it closes the larger
  remaining gap: the carry fallback still leaks unrelated work, while the #655 hold is
  only too cautious.

The conflict is declared on both children so neither side depends on the scheduler
reading a one-sided edge.

**Out-of-batch ordering, for the human to check after `--accept`:** all three children
build on #723's `integrate.build_bundle_base` (`integrate.py:716`). #723's PR #726 is
open, not merged, so the base is the run's line `pdca-integration/main-r547f8028520f` at
`fcae4aa`. The split parser accepts only sibling labels in `Depends on:`, so `723` cannot
be written there. Each child carries an `Ordering note` naming it. After acceptance, add
`723` to child-1's `Depends on` if the scheduler should hold it until #723 is accepted.
Children 2 and 3 get it through child-1.

<!-- pdca:child child-1 -->
- **Slug:** flow-in-batch-dependency-scoped-bases
- **Defect / goal:** In stack mode every runnable bundle is pointed at the run's one integration line (`_point_at_integration`, `template/src/pdca_harness/flow.py:890`, called at `:2549`). That line holds every earlier-wave bundle of the target, so a PR's branch carries unrelated bundles' work. Merging it lands work whose own PR the human closed (#630, moved onto #463). Goal: a bundle whose declared-prerequisite closure is entirely **in-batch** and buildable by `integrate.build_bundle_base` (`integrate.py:716`) gets a base holding exactly that closure's accepted work and nothing else of the run. The #633/#695 rewrite checks must then be fed the head that bundle's **own** base took, and their messages must name that base and that bundle's PR, since no PR is cut from the line any more.
- **Success criterion:** Real-git tests driving `flow._drive_and_act` through real folds on the `StackFoldGit` fixture, with build and sign-off stubbed and `_publish_bundle` cutting each PR branch from the recorded stack-base tip, as `template/tests/test_flow_same_wave_conflict.py:131` does:
  (1) **The #630 case.** `A`, `Z` (wave 0, unrelated, two commits each), `B` (`Depends on: A`). Every commit of `origin/main..fix/A` is on `fix/B`; no commit of `origin/main..fix/Z` is. All COMPLETE.
  (2) **Transitive.** `C` (`Depends on: B`): `fix/C` has `fix/A` and `fix/B`, not `fix/Z`.
  (3) **Conflict partner.** `E` (`Conflicts with: A`): `fix/E` has `fix/A`, not `fix/Z`.
  (4) **In-batch `Depends on (merged)`.** `G` (`Depends on (merged): A`): `fix/G` has `fix/A`, not `fix/Z`.
  (5) **Empty closure → real base.** `H` whose only edge is to an in-batch `N` that closed with no patch: stack base cleared; `fix/H` has neither `fix/A` nor `fix/Z`.
  (6) **Seam fallback is unchanged.** A bundle whose closure reaches a carried bundle, an `Onto branch` member or a legacy `Stacks on` bundle gets exactly the line base it gets on `fcae4aa`.
  (7) **Rewrite message.** `A` in wave 0, `B` (`Depends on: A`); `fix/A` is forced back to an older commit after `B`'s base took its newer head. The #633 (next fold) and #695 (end of run) reports name `issue_B`, `B`'s own base branch (`integrate.bundle_base_branch`) and the head that base took, and tell the human to rebuild `B`'s PR. They do not say `the commit the line took` or `every PR this run cut from` (today's wording, `integrate.py:1131`, `flow.py:2713-2728`).
  (8) Existing suites stay green; assertions restated only in terms of content, never weaker. `_line_lacks_merge` and its suite `test_flow_merged_prereq_on_line.py` are untouched.
- **Repo + branch target:** eduralph/pdca-harness @ main (PRs target `main`). Base: the run's line `pdca-integration/main-r547f8028520f` at `fcae4aa` (`489e5fb` + #723; #723's PR #726 is open, not merged). Anchors are on `fcae4aa`.
- **Ordering note:** Calls #723's `integrate.build_bundle_base` (`integrate.py:716`); needs #723 (not expressible in the sibling-only `Depends on` field — add `723` after acceptance if wanted).
- **Reproduction:** On `fcae4aa`: `StackFoldGit`, publish `A` and `Z`, fold `[A, Z]`, publish `B` cut from `origin/<line>`; `fix/Z`'s tip is an ancestor of `fix/B`.
- **Falsifiability:** Offline, real git. On `fcae4aa`, `_point_at_integration` writes the run's line into every runnable bundle's `stack-base`, so `fix/B` holds `Z` and (1)-(4) fail.
- **Invariant to restore:** What an in-batch bundle is built on is decided by what it declares, not by when it was scheduled. Its base carries exactly the accepted work of the bundles it is ordered after by a declared edge (`Depends on` and in-batch `Depends on (merged)`, transitively; an earlier-wave `Conflicts with` partner) that this run built, and nothing else of the run. Empty set → the real base. Source: #463 and #630's finding (`results/issue_463/notes.json`); `09-parallel-lanes.md:59-61`.
- **Scope (one logical fix) / out of scope:** `template/src/pdca_harness/flow.py` (closure walk over in-batch edges, per-bundle base selection replacing `_point_at_integration` for in-scope bundles, recording which head each base took and feeding it to the #633/#695 checks), `integrate.py` rewrite-message wording, and the restated existing suites. / Out of scope: carried bundles as base members, and the finished-patchless-node-on-resume case (child-2: such closures keep the line base here); `_line_lacks_merge` / `merged.merge_and_head` / #655 (child-3); legacy `Stacks on` / `Onto branch` prerequisites beyond keeping the line base; holds for base-build failures and cross-wave overlaps, and all stack-rule docs (#725); merge mode; wave scheduling; PR targets; per-bundle base cleanup.
- **External dependencies:** none (Python 3.11+ standard library and git, the base toolchain).
- **Surfaces:** none (driver internals)
- **Test file:** template/tests/test_flow_dependency_scoped_bases.py (new)
- **Citations expected:** path:line on `fcae4aa`.
- **Prior-art check (triage cycles):** #674, #655, #633, #629, #646 on `flow.py`; parent #724's rejected attempts in `results/issue_724/iteration-v1/`, `iteration-v2/` (their in-batch closure code and tests are the starting point).
- **Difficulty:** high
<!-- pdca:end child-1 -->

<!-- pdca:child child-2 -->
- **Slug:** flow-carried-prerequisites-in-dependency-bases
- **Defect / goal:** After child-1, a bundle whose closure reaches a **carried** bundle (one finished in an earlier run and carried into this one, #646) still falls back to the run's integration line, so its PR branch still carries unrelated carried work. On resume, a finished bundle with no patch is dropped from the dependency graph, so edges through it are lost: the dependent either ships missing a transitive prerequisite or is wrongly stopped as holding foreign work (`results/issue_724/iteration-v2/SUMMARY.md` §5, two repros). Goal: carried bundles become base members with their carried heads, finished patchless bundles stay in the dependency graph for traversal (but never as base members), and carry defects stop the dependent instead of building it on a wrong base.
- **Success criterion:** Real-git tests on the `StackFoldGit` fixture driving `flow._drive_and_act`, as child-1's suite does:
  (1) **Carried prerequisites (#646).** Carried clean `P`, `X`; planned `D` (`Depends on: P`), `E` (`Depends on: X`): `D`'s base has `fix/P` not `fix/X`, `E`'s the reverse. Both COMPLETE.
  (2) **Resume through a finished patchless bundle (missing-work repro).** Run `[A, N, D, W]`, `N Depends on A` closed with no patch, `D Depends on N`, `W Depends on A`; fail `D`, `W`; reissue driving `D`, `W`: `D` is COMPLETE and contains `A`.
  (3) **Resume through a finished patchless bundle (false-stop repro).** Run `[A, N, P, D]`, `P Depends on N`, `D Depends on P`; fail `D`; reissue driving `D`: `D` is COMPLETE and contains `A` and `P`; no `STOPPING` line.
  (4) **Carry defect: foreign ancestry.** Carried `P` cut from an old line holding carried `X`; `D` (`Depends on: P`): `D` stays PLANNED with no stack-base record; a `STOPPING` line names `issue_P` and `issue_X`.
  (5) **Carry defect: rewritten carried prerequisite (#633).** `fix/P` force-pushed after the carry: `D` stays PLANNED; a `STOPPING` line names `issue_P` and the rewrite.
  (6) Existing suites stay green (including `test_flow_resume_stack_prereqs.py`, `test_integrate_carried_rewrite_late.py`); assertions restated only in terms of content, never weaker.
- **Repo + branch target:** eduralph/pdca-harness @ main (PRs target `main`). Base: the accepted result of child-1, folded onto the run's line `pdca-integration/main-r547f8028520f` (from `fcae4aa`).
- **Ordering note:** Builds on child-1's closure walk and per-bundle base recording; needs #723 through child-1.
- **Reproduction:** With child-1 applied: carried clean `P`, `X`, planned `D` (`Depends on: P`); `D` keeps the line base (child-1's seam fallback), so `fix/X`'s tip is an ancestor of `fix/D`. For (2)/(3), run the v2 reviewer's script (`results/issue_724/iteration-v2/SUMMARY.md` §5) against child-1's suite.
- **Falsifiability:** Offline, real git. With child-1 alone, (1) fails (`D` holds `X`); with the v2 patch's graph, (2) and (3) fail as recorded in `review-carried-patchless.log` / `review-carried-patchless-member.log`.
- **Invariant to restore:** Same as child-1's, extended to bundles this run **carried**: a base carries exactly the accepted work of the declared closure the run built or carried, and nothing else. A bundle with no patch is still a node in the graph its dependents' edges pass through.
- **Scope (one logical fix) / out of scope:** `template/src/pdca_harness/flow.py` (carry candidates as base members with carried heads; keeping finished patchless bundles in the traversal graph; narrowing child-1's carried-closure fallback to just the `Onto branch` / legacy `Stacks on` cases), carry-defect stop paths in `integrate.py` where needed, and restated existing suites. / Out of scope: #655 / `_line_lacks_merge` / `merged.merge_and_head` (child-3); legacy `Stacks on` / `Onto branch` prerequisites (keep the line base); base-build-failure and cross-wave-overlap holds and stack-rule docs (#725); merge mode; wave scheduling; PR targets.
- **External dependencies:** none (Python 3.11+ standard library and git, the base toolchain).
- **Surfaces:** none (driver internals)
- **Test file:** template/tests/test_flow_carried_prereq_bases.py (new)
- **Citations expected:** path:line on child-1's accepted result.
- **Prior-art check (triage cycles):** #646, #633, #674 on `flow.py`; parent #724 `iteration-v2/SUMMARY.md` §5 (the patchless-resume finding).
- **Difficulty:** high
- **Depends on:** child-1
- **Conflicts with:** child-3
<!-- pdca:end child-2 -->

<!-- pdca:child child-3 -->
- **Slug:** flow-merged-prereq-judged-by-merged-into
- **Defect / goal:** `_runnable` holds a bundle whose out-of-batch prerequisite has merged into `main` unless the run's integration line already contains that merge (`_line_lacks_merge`, `template/src/pdca_harness/flow.py:850`, called at `:792`, using `merged.merge_and_head`, `merged.py:149`). After child-1 a bundle is no longer cut from the line; it is built on its own base from the real base, which already holds anything merged into `main`. So the check asks about a tree the bundle does not use and holds it for no reason (#655). Goal: `_runnable` judges an out-of-batch merged prerequisite by `merged.merged_into` alone; remove `_line_lacks_merge` and `merged.merge_and_head`.
- **Success criterion:**
  (1) **#655 judged on the base the bundle gets.** Real-git test on `StackFoldGit` driving `flow._drive_and_act`: out-of-batch `P`'s PR merges into `main` after the first fold; `D` is not held; it is COMPLETE and its base contains `P`'s merge commit. Both edge types: `Depends on (merged): P`, and a plain `Depends on: P` with `P` not in the batch (#647).
  (2) A prerequisite NOT merged into `main` still holds its dependent (the #647 rule, `merged.merged_into`).
  (3) `_line_lacks_merge` and `merged.merge_and_head` no longer exist and nothing references them; `merged.py`'s module docstring (`:24-26`) and `_pr_view`'s docstring (`:190`) no longer describe them.
  (4) In `template/tests/test_flow_merged_prereq_on_line.py` (on `fcae4aa`): `:202` and `:212` flip from held to built, with the base containing the merge; `:241` (unreadable merge commit) and `:249` (fetch failure) test only the removed check, so they flip to built or are removed, and `build-notes.md` names each with before and after. The rest stay green.
  (5) Existing suites stay green; assertions restated only in terms of content, never weaker.
- **Repo + branch target:** eduralph/pdca-harness @ main (PRs target `main`). Base: the accepted result of child-1 (and child-2, whichever wave folded first), on the run's line `pdca-integration/main-r547f8028520f` (from `fcae4aa`).
- **Ordering note:** Only correct once child-1 has moved bundles off the line base; needs #723 through child-1.
- **Reproduction:** With child-1 applied: out-of-batch `P` merges into `main` after the first fold; `_line_lacks_merge` sees the line lacks `P`'s merge and holds `D`, although `D`'s own base (from `main`) contains it.
- **Falsifiability:** Offline, real git. With child-1 alone, `_line_lacks_merge` holds `D` in (1).
- **Invariant to restore:** Whether a bundle may run is judged on the base it will actually be built on, not on a tree it no longer uses.
- **Scope (one logical fix) / out of scope:** `template/src/pdca_harness/flow.py` (`_runnable`'s merged-prerequisite check; delete `_line_lacks_merge`), `template/src/pdca_harness/merged.py` (delete `merge_and_head`, fix the docstrings in (3)), `template/tests/test_flow_merged_prereq_on_line.py` (flip hold cases). / Out of scope: closure and base selection (child-1, child-2); carried prerequisites; base-build-failure and cross-wave-overlap holds and stack-rule docs (#725); merge mode; wave scheduling; PR targets.
- **External dependencies:** none (Python 3.11+ standard library and git, the base toolchain).
- **Surfaces:** none (driver internals)
- **Test file:** template/tests/test_flow_merged_prereq_dependency_base.py (new)
- **Citations expected:** path:line on child-1's accepted result (anchors above are on `fcae4aa`).
- **Prior-art check (triage cycles):** #655 (introduced `_line_lacks_merge`), #629 on `flow.py` / `merged.py`; parent #724 brief plan-review note (f).
- **Difficulty:** medium
- **Depends on:** child-1
- **Conflicts with:** child-2
<!-- pdca:end child-3 -->
