<!-- pdca:split-proposal v1 -->
# Split proposal — issue 463

Written at Plan by the human and the planner, after #463's first attempt was sent back at
sign-off with `iterate-plan` (2026-10-15, Eduard Ralph): *"Oversized slice (165 KB, 15
files; backstop 125 KB) — split it at Plan rather than rebuild."* The full first attempt
(patch, build notes, reviews, the design proposal it built from) is kept in
`results/issue_463/iteration-v1/`. That design (`iteration-v1/brief.md`, Motivation /
Design / Alternatives) still holds. Every child below builds a part of it, with the
decisions the human made in this re-plan:

1. Three children, shaped as the sign-off suggested, but with **all doc changes in the last
   child**. With the docs in it, child 2 would be about 130 KB, over the limit. The doc
   wording on "an undeclared overlap STOPs the run" also depends on child 3's decision.
2. A per-bundle base that cannot be built, and an undeclared overlap at the line fold for a
   bundle not built on the line, **hold that bundle and its dependents and let the run go
   on**. Today's whole-run stop no longer applies to them (child 3).
3. The two carry defects the review reproduced go in child 2, each with a regression test.
   The checks they need are part of child 1's base-building function.
4. An in-batch `Depends on (merged)` edge **counts** toward the closure (the patch kept it;
   `template/PCDA/quality-cycle/09-parallel-lanes.md:61` documents it as a plain dependency).

All line references are on the run's integration line `pdca-integration/main-r547f8028520f`
@ `489e5fb` (`origin/main` @ `d6057eb` plus the accepted 672, 673, 693, 694, 695), the
base this run builds the children on. If those five merge first, lines may move: Do
re-checks each citation on the base it gets, and Check judges citations against that base.

## Why this slice is oversized

The first attempt worked: C4 went red on assertions (not imports) and green with the
patch, and the full suite stayed green. It was sent back because of breadth, and a rebuild
cannot fix breadth:

* **Three separately arguable changes in one patch.** (a) `integrate.fold` gains a new
  destination and push rules: an API change to the module every safeguard lives in.
  (b) The flow changes which base each bundle gets: a behaviour change, with eight existing
  test suites to restate. (c) What happens when one bundle's base can't be built. The
  review raised fifteen NEEDS-HUMAN items across all three, and two of them were real design
  questions (hold or stop) that had to be answered before the code was written.
* **The patch broke the size limit:** 165 KB, 15 files, 25 KB of that docs and vendored
  spec.
* **Each part has its own rollback.** The fold API can land and be reviewed with nothing
  calling it. The base switch can land with the old stop-on-failure behaviour. The holds
  and docs then finish the rule.

## Wave sketch

A strict chain: **child-1 → child-2 → child-3**, each in its own wave.

* child-1 needs the parent's prerequisites 672, 673, 693, 694, 695 (they edit
  `integrate.fold` and the carry, which child-1 extends). A child's ordering fields may name
  only siblings, so this is not a `Depends on:`. The run that adopts the children puts them
  in waves after #463's, on the run's line, which already holds all five. Driven
  standalone, the five must be merged first (child-1's Ordering note says so).
* child-2 depends on child-1: it calls the base-building function child-1 adds.
* child-3 depends on child-2: it changes how child-2's base-building failures are handled,
  and documents the rule child-2 puts in place.

None can run in parallel. Each edits code the previous one adds. Merge order for the human
is bottom-up. child-2 merged without child-3 is safe but strict: a base that can't be built
stops the run, as on the first attempt.

<!-- pdca:child child-1 -->
- **Slug:** fold-builds-a-per-bundle-base
- **Defect:** `integrate.fold` can only fold onto the run's one line per target. It works out its destination itself from `integration_branch(cfg, base, batch)` (`template/src/pdca_harness/integrate.py:126`, used by `fold` at `:327` onward) and returns one entry per `(repo, base)` target. So there is no way to build a branch that carries exactly a chosen set of accepted bundles, which #463's dependency-scoped bases need (design: `results/issue_463/iteration-v1/brief.md`, Design §3).
- **Success criterion:** Real-git tests on the `StackFoldGit` fixture (`template/tests/test_integrate_stack_bases.py:123`), with branches published to the fixture's origin as that file's tests do, show the new per-bundle base build doing all of this:
  (1) **Exact contents.** Wave 0 = `A`, `Z` (unrelated, each with TWO commits on its own files). Fold the run's line with both. Then build `B`'s base from members `[A]`. The branch it pushes is on origin, contains every commit of `origin/main..fix/A`, contains no commit of `origin/main..fix/Z`, starts from `origin/main` as fetched, and the run's line branch and its recorded tip are unchanged by the build.
  (2) **Name.** The branch name comes from the run's line name plus a fixed suffix carrying `B`'s id. It is not a path prefix of the line or of any other bundle's base name, and two different bundle ids never give the same name. Keep `integration_branch` and `_flatten_base` (`integrate.py:126`, `:154`) unchanged.
  (3) **Push rule.** Creating the branch is a plain push: an origin with `receive.denyNonFastForwards = true` accepts it. Re-building an existing one is a force-push. A refused push raises `integrate.IntegrationError` naming the branch and the remedy (delete it on origin, or allow force-pushes on `pdca-integration/*`).
  (4) **Every fold safeguard applies.** A member that doesn't merge cleanly raises `IntegrationError` naming both sides. A clash with the fetched base itself names `<remote>/<base>` and says to rebuild the member's branch on the new base, NOT "declare the conflict / re-order" (the wording at `integrate.py:842` stays for clashes between two bundles). A member whose branch is gone, or which brings in a revert of earlier work (#623 / 673's check), raises as the run's fold does.
  (5) **Rewritten carried member (#633).** Given a recorded head for a member, a member whose branch on origin no longer has that head raises `IntegrationError` naming the rewrite. Nothing is pushed.
  (6) **Foreign ancestry.** Given the published heads of the run's bundles that are NOT members, a build in which any commit of `<base>..<excluded head>` would end up on the result raises `IntegrationError` naming the excluded bundle and the member that brought it in. Nothing is pushed. Case: carried `P`'s branch was cut from an old line holding `X`; building `D`'s base from `[P]` with `X` excluded raises.
  (7) Every existing test in `template/tests/test_integrate_*.py` and `test_flow_*.py` stays green unchanged. This child changes no caller.
- **Falsifiability:** Offline, real git, as the existing `StackFoldGit` tests. Before the change there is no way to fold onto a named destination, so (1)–(6) fail. To make that a failure the C4 red leg counts, not an import error: the test imports only modules (`from pdca_harness import integrate`), and reaches the new entry point inside each test body (e.g. `getattr(integrate, …)` or a call with the new keyword), so with the production change reverted every test runs and fails on an error or an assertion. Do states in `build-notes.md` which red each case shows.
- **Invariant to restore:** The integrate module can build, for one bundle, a branch whose content is exactly the fetched base plus a given set of accepted bundles' published work, checked by the same safeguards as the run's line (clean merge, no revert, branch present, unrewritten carried heads), and refused, never silently widened, when a member would bring in work of a bundle outside the set. Source: #463 (Done when, #630's comment on the issue); `iteration-v1/brief.md` Design §3 and Scope; the sign-off carry-forward (2026-10-15) for (5)/(6).
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Ordering note:** No sibling prerequisite. It must still build on the parent's prerequisites 672, 673, 693, 694, 695 (672, 673 and 695 edit `integrate.fold` and the carry this child extends; 693 and 694 edit the end of `_drive_and_act` and its tests, which the later children build on). A split child may name only siblings here. In the run that adopts it, it lands in a wave after its parent's, and the pre-#463 rule builds every later-wave bundle on the run's line, which holds all five. If it is driven standalone later, those five must be merged into `main` first.
- **Surfaces:** none (driver internals; no CLI, config or template-question change)
- **Difficulty:** medium
- **Scope:** `template/src/pdca_harness/integrate.py` only: a way to build a per-bundle base (a new `fold` keyword or a sibling function that shares `fold`'s merge path; Do picks, and says why in `build-notes.md`). It takes the target, the destination bundle, the ordered member list, the members' recorded carried heads, and the excluded bundles' heads. It always starts fresh from the base as fetched. It runs under the same per-target `integ_lock` and worktree as the run's folds (`integrate.py:280`, `:538`) and resets the worktree as `fold` does. It returns its pushed tip without touching the run line's entry. Push rule and errors as in criteria (3)–(6). The test file. / out of scope: any caller (the flow does not use it yet; child 2); `publish.py`, `flow.py`, `gates.py`, `worktree.py`; docs and the `integrate.py` module docstring's statement of the stack rule (child 3); deleting per-bundle bases from origin (Open question 1 of the design: left for a follow-up).
- **Repro instruction:** n/a (new capability). Read `integrate.fold`'s signature (`integrate.py:327`) on `489e5fb`: no destination parameter.
- **External dependencies:** none (Python 3.11+ standard library and git, the base toolchain).
- **Test file:** template/tests/test_integrate_bundle_base.py (new; loads `StackFoldGit` by path as `template/tests/test_flow_same_wave_conflict.py:56` does, or subclasses it)
- **Citations expected:** Do must cite path:line on the target branch for every change. Peer callsites: the run's fold and its push / tip return (`integrate.fold`, `integrate.py:327` onward); the lock and worktree it takes (`integrate.py:280`, `:538`); the clean-merge check and its message (`_merge_published`, `integrate.py:810`, message `:842`); the carried-head bookkeeping #633 added (search `carried` in `fold`); the name scheme (`integration_branch` `:126`, `_flatten_base` `:154`).
- **Prior-art check (triage cycles):** Merged history for `integrate.py` on `origin/main`: `0c263a9` (#674), `11b9fc1`, `8a1f10e`/`6886d33` (#631), `9ae1036` (#623), `c1f2306` (#646), `4b54cbe` (#591), `b21f248` (#593), `acf9947` (#633). Accepted in this run: 672, 673, 695 (draft PRs #702, #707, #721). None adds a named destination. The first attempt's version is in `iteration-v1/patch.diff` (the `into` parameter); Do may read it for reference, and must add checks (5)–(6), which it lacked.
- **Disposition hint:** new-feature
<!-- pdca:end child-1 -->

<!-- pdca:child child-2 -->
- **Slug:** flow-builds-each-bundle-on-its-declared-prerequisites
- **Defect:** In stack mode every runnable bundle is pointed at the run's one integration line (`_point_at_integration`, `template/src/pdca_harness/flow.py:890`, called at `:2549`). That line holds every earlier-wave bundle of the target, so a PR's branch carries unrelated bundles' work. Merging it lands work whose own PR the human closed (#630, moved onto #463).
- **Success criterion:** Real-git tests driving `flow._drive_and_act` through real folds on the `StackFoldGit` fixture, with build and sign-off stubbed and `_publish_bundle` cutting each PR branch from the recorded stack-base tip, as `template/tests/test_flow_same_wave_conflict.py:131` does:
  (1) **The #630 case.** `A`, `Z` (wave 0, unrelated, two commits each), `B` (`Depends on: A`). Every commit of `origin/main..fix/A` is on `fix/B`; no commit of `origin/main..fix/Z` is. `B`'s recorded stack base is a branch on origin holding `fix/A`'s tip and not `fix/Z`'s, and `B` was built on it. All COMPLETE.
  (2) **Transitive.** Add `C` (`Depends on: B`). `fix/C` has `fix/A` and `fix/B`, not `fix/Z`.
  (3) **Conflict partner.** Add `E` (`Conflicts with: A`; the scheduler puts the name-higher id in the later wave, `waves.compute_waves`). `fix/E` has `fix/A`, not `fix/Z`.
  (4) **In-batch `Depends on (merged)`.** Add `G` (`Depends on (merged): A`). `fix/G` has `fix/A`, not `fix/Z`.
  (5) **Empty closure → real base.** Add `H` whose only edge is to an in-batch `N` that closed with no patch. `H`'s stack base is cleared (`publish.read_stack_base` empty); `fix/H` has neither `fix/A` nor `fix/Z`.
  (6) **Carried prerequisites (#646).** In `test_flow_resume_stack_prereqs.py`'s carry fixture: carried clean `P` and `X`, planned `D` (`Depends on: P`) and `E` (`Depends on: X`). `D`'s base has `fix/P`, not `fix/X`; `E`'s has `fix/X`, not `fix/P`. Both COMPLETE.
  (7) **Carry defect: foreign ancestry.** Carried `P` whose branch was cut from an old line holding `X` (also carried, not in `D`'s closure); `D` (`Depends on: P`). `D` is never built on a base holding `X`'s commits; the run reports the foreign ancestry naming `P` and `X`. (Until child 3 the run stops there; child 3 makes it a hold.)
  (8) **Carry defect: rewritten carried prerequisite (#633).** Carried `P`; after the carry, `fix/P` is force-pushed to a different commit; `D` (`Depends on: P`). `D` is not built on the rewritten branch; the run reports the rewrite naming `P`. The carry's recorded heads reach the per-bundle base build.
  (9) **#655 judged on the base `d` gets.** The set-up of `test_flow_merged_prereq_on_line.py` where out-of-batch `P`'s PR merges into `main` after the first fold: `D` is not held; it is built, COMPLETE, and its base contains `P`'s merge commit.
  (10) **Nothing else regresses.** The existing suites `test_integrate_stack_bases.py`, `test_flow_same_wave_conflict.py`, `test_flow_resume_stack_prereqs.py`, `test_flow_merged_prereq_on_line.py`, `test_flow_conflict_partner_hold.py`, `test_flow_reissue_after_conflict_hold.py`, `test_flow_hold_exit_code.py`, `test_integrate_carried_rewrite_late.py`, `test_flow_slice.py` and child 1's test stay green. An existing assertion may change ONLY by restating the base it checks in terms of content ("the recorded base contains the tip of each closure member, and no commit of any other run bundle's branch"), never by branch name and never weaker. The #655 hold tests flip per (9). Known to need it: `test_flow_same_wave_conflict.py` `_built_on_line` (`:169`); `test_flow_resume_stack_prereqs.py`'s `self._line([...])` / `self.line` assertions; `test_flow_merged_prereq_on_line.py`'s hold cases. A test INPUT may change only where its premise ("X is built on Y") now needs a declared edge, and `build-notes.md` names every such change with before and after.
  Pre-change, (1)–(8) fail (every wave>0 and carry dependent is on the line, which holds `Z` / `X`); (9) fails because `D` is held.
- **Falsifiability:** Offline, real git, same harness as the #674 tests. On `489e5fb`, `_point_at_integration` writes the run's line into every runnable bundle's `stack-base` and the stubbed publish cuts `fix/B` from that tip, which holds `Z`. The test imports only modules (never a symbol this child adds), so with the production change reverted (child 1's code stays, it is on the base) it loads and fails on assertions.
- **Invariant to restore:** What a bundle is built on is decided by what it declares, not by when it was scheduled. Its base carries exactly the accepted work of the bundles it is ordered after by a declared edge (`Depends on` and in-batch `Depends on (merged)`, transitively; an earlier-wave `Conflicts with` partner; a legacy `Stacks on` parent) that this run built or carried, and nothing else of the run. An empty set means the real base. Consequence the human relies on: closing a bundle's PR keeps its work off the target unless a PR built on it by a declared edge is merged. Source: #463 and #630's finding (the comment on #463, 2026-10-10); `09-parallel-lanes.md:59-61`.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Depends on:** child-1
- **Ordering note:** Calls child 1's per-bundle base build.
- **Surfaces:** none (driver internals)
- **Difficulty:** high
- **Scope:** `template/src/pdca_harness/flow.py`: compute each runnable bundle's closure per the Invariant (only accepted bundles whose branch the fold carries count, `integrate._fold_candidates` `integrate.py:217`; a patchless one adds nothing; a held one already holds `d` via `_runnable`). Give `d` an empty-closure `clear_stack_base`, or a base built by child 1's function with its members, their carried heads (from the pre-wave carry, `_carry_finished` `flow.py:1091`), and the other run bundles' heads as excluded. Record it with `publish.write_stack_base(d, branch, tip)` (`publish.py:647`); worktree, `$PDCA_VERIFY_BASE` and the PR cut already read that record. Keep the run's line, folded after each wave as today, as the integration check (re-gate, #674 holds, #646 carry); nothing is cut from it any more. #655: `_runnable` judges an out-of-batch merged prerequisite by `merged.merged_into` alone for every bundle; remove `_line_lacks_merge` (`flow.py:850`) and the now-unused `merged.merge_and_head` (`merged.py:149`), fixing the `merged.py` docstrings (`:24`, `:188`). A base build failure stops the run before the wave, with the error child 1 raises (child 3 turns it into a hold). Restate the existing tests per (10). / out of scope: holds for base-build failures and for cross-wave overlaps at the line fold (child 3); every doc, glossary and docstring stating the stack rule, including `integrate.py`'s module docstring, `publish.py:42-44`, `:252-277`, `:648-690`, `gates.py:535-539`, `drift.py:53`, `_adopt_split_children`'s docstring (child 3); merge mode; wave scheduling; PR targets (still the real base, #593); per-bundle base cleanup on origin.
- **Repro instruction:** On `489e5fb`, the #630 test from the issue comment: `StackFoldGit`, publish `A` and `Z`, fold `[A, Z]`, publish `B` cut from `origin/<line>`; `_ancestor(_tip("fix/Z"), _tip("fix/B"))` is true.
- **External dependencies:** none (Python 3.11+ standard library and git, the base toolchain).
- **Test file:** template/tests/test_flow_dependency_scoped_bases.py (new; loads `StackFoldGit` by path as `test_flow_same_wave_conflict.py:56` does)
- **Citations expected:** Do must cite path:line on the target branch for every change. Peer callsites: where the base is chosen today (`_point_at_integration`, `flow.py:890`, call `:2549`); the wave loop and its stops (`flow.py:2600-2670`); the run's fold and tip bookkeeping (`_fold_lines`, `flow.py:913`); the carry and its heads (`_carry_finished`, `flow.py:1091`; `_finished_named`, `:963`); the #655 check to remove (`_runnable` `flow.py:681`, docstring on `lines`; `_line_lacks_merge` `:850`); the stack-base record (`publish.py:647-690`, `_stack_base_branch` `:740`).
- **Prior-art check (triage cycles):** Merged history for `flow.py` on `origin/main`: `0c263a9`/`ca56153` (#674), `2cd332e` (#655), `7aca036` (#633), `0dc7af7` (#629), `c1f2306` (#646). Accepted in this run: 693, 694, 695. None scopes a base to declared prerequisites. The first attempt's flow changes are in `iteration-v1/patch.diff`, and its test is a starting point for this one; it lacked (7) and (8), which the review reproduced against it.
- **Disposition hint:** new-feature
<!-- pdca:end child-2 -->

<!-- pdca:child child-3 -->
- **Slug:** hold-a-bundle-whose-own-base-cannot-be-built
- **Defect:** After child 2, a failure that belongs to one bundle stops the whole run. Cases: its base can't be built (clash with a `main` that moved mid-run, conflict between two of its prerequisites, foreign ancestry, rewritten carried prerequisite, failed fetch, refused push). Or, once built on its own base, it hits an undeclared file overlap with an unrelated earlier-wave bundle at the line fold (`_held_by` holds only same-wave clashes, `integrate.py:1261`; anything else raises and `flow.py:2649` stops). Bundles with nothing to do with the failure stay PLANNED. The docs, glossary and docstrings still state the old rule ("a later wave's PR carries every earlier-wave branch on the line").
- **Success criterion:** Real-git tests in the same harness as child 2:
  (1) **Moved base.** `A` adds `a.txt`, `Z` adds two files, `B` (`Depends on: A`), `W` (`Depends on: Z`). After wave 0's fold, a different `a.txt` is pushed to `main`. `B` is held, named on one stderr line that names `<remote>/main` and says to rebuild `A`'s branch on the new base. `W` is built and COMPLETE. The run exits 3 (held, #693).
  (2) **Carry defects held, not stopped.** Child 2's cases (7) and (8) end with `D` held and named, and an unrelated planned bundle in the same wave COMPLETE.
  (3) **Cross-wave undeclared overlap at the line fold.** `A`, `Z` in wave 0 (`Z` adds `shared.txt`); `Y` (`Depends on: A`, also adds `shared.txt`); `C` (`Depends on: Y`); `W` (`Depends on: Z`). `Y` is held out of the line as #674 holds a same-wave clash, named with `Z`; `C` is held; `W` completes; the run does not print STOPPING.
  (4) **Fetch failure** for one bundle's base (made to fail for that bundle only, e.g. by stubbing the fetch of its base build) holds that bundle; the rest of the wave runs.
  (5) A conflict between two closure members is held the same way (Scope), but needs no test of its own: two members that both reached the line merged cleanly there in the same order, so it is reached only through the moved base, which (1) covers.
  (6) **Docs state the new rule.** No file in the target says a later wave's PR is built on, cut from, or carries every earlier-wave branch on the line. Checked by `git grep` for the phrases at `docs/05-check.md:814`, `docs/07-crosscutting.md:647-653`, `docs/index.yml:65`, `template/PCDA/quality-cycle/08-glossary.md:276-293`, `template/PCDA/quality-cycle/09-parallel-lanes.md:57-69`, `template/src/pdca_harness/integrate.py` module docstring (`:1-69`), `publish.py:42-44`, `:252-277`, `:648-690`, `:743`, `gates.py:535-539`, `drift.py:53`, and `_adopt_split_children`'s docstring (`flow.py:1830` onward); each is rewritten to the dependency-scoped rule and the hold behaviour. `09-parallel-lanes.md:69`'s "undeclared overlap STOPs the run" says which cases still stop (the line's re-gate going red; a line fold failure that is not a single bundle's clash).
  (7) Child 2's and child 1's tests, and every existing suite listed in child 2's (10), stay green; any test that asserted a STOPPING for these cases flips to the hold, named in `build-notes.md`.
  Pre-change, (1)–(4) fail on the whole-run stop.
- **Falsifiability:** Offline, real git, same harness. With the production change reverted (children 1 and 2 stay; they are on the base), each case ends with `STOPPING` and the unrelated bundle PLANNED, so the assertions fail. The test imports only modules. The doc criterion (6) is not part of the C4 red leg; T2 and the review judge it.
- **Invariant to restore:** A failure that belongs to one bundle's base holds that bundle and the bundles that declared they build on it, and nothing else; the run stops only for a failure of the run's shared line (re-gate red, a fold error that is not one bundle's clash). Every message names the cause and a fix that works for that cause. The docs state the rule the code follows. Source: the human's decision at this re-plan (2026-10-15); the hold model of #674 (`flow.py` held_conflict) and #655; the review findings in `iteration-v1/SUMMARY.md` §6 (moved-base clash, cross-wave overlap, wrong remedy text, stale docs).
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Depends on:** child-2
- **Ordering note:** Changes how child 2's base-building failures are handled and documents child 2's rule.
- **Surfaces:** none (driver internals and docs)
- **Difficulty:** high
- **Scope:** `template/src/pdca_harness/flow.py`: a per-bundle base failure puts `d` in a held set that `_runnable` already honours (as `held_unpushed` / `held_conflict` do), with one stderr line naming cause and fix; the wave goes on. At the line fold, a bundle not built on the line whose branch clashes with the line is held out the way #674's `held_conflict` is (extend `_held_by`'s use, `integrate.py:1261`, or the flow's handling of the fold error; Do picks and says why), so its dependents and partners are held through `_runnable`. Error wording in `integrate.py` where needed. Every doc, glossary and docstring in criterion (6). The vendored spec edits (`template/PCDA/quality-cycle/08-glossary.md`, `09-parallel-lanes.md`) are a human-only item at Check (INTEGRATION §4): Do drafts them, the human approves. / out of scope: which base a bundle gets (child 2); the fold API (child 1); merge mode; Plan-time overlap detection (#395); per-bundle base cleanup on origin.
- **Repro instruction:** After child 2, case (1) above: the run prints a `STOPPING` line before wave 1 and `W` stays PLANNED.
- **External dependencies:** none (Python 3.11+ standard library and git, the base toolchain).
- **Test file:** template/tests/test_flow_bundle_base_holds.py (new; same fixture as child 2)
- **Citations expected:** Do must cite path:line on the target branch for every change. Peer callsites: the #674 same-wave hold (`held_conflict`, declared `flow.py:2404`, used in the fold block `:2620-2660`; `_announce_conflict_holds` `:1250`; `integrate._held_by` `:1261`); the #593 unpushed hold (`held_unpushed`, declared `flow.py:2399`, set `:2625-2635`); how `_runnable` holds dependents of a held bundle (`flow.py:681` onward); the exit-3 rule for a run with holds (693, `test_flow_hold_exit_code.py`).
- **Prior-art check (triage cycles):** `0c263a9` (#674, same-wave hold), `2cd332e` (#655 hold), 693 (exit 3 on holds, accepted this run). No existing hold covers a per-bundle base. The first attempt stopped the run in all these cases (`iteration-v1/check-advisory-adversary.md`).
- **Disposition hint:** new-feature
<!-- pdca:end child-3 -->
