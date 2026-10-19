<!-- pdca:split-proposal v1 -->
# Split proposal — issue 725

<!-- Each child is a COMPLETE brief, not a sketch. A filled Slug alone makes `state.state`
     classify the materialised file as PLANNED, so `pdca flow` skips Plan and sends it
     straight to Do — a child missing `Repo + branch target` then builds successfully and
     has nowhere to publish. Fill every field. -->

<!-- Delimiters are HTML comments, not headings, DELIBERATELY: each child body is a full
     draft brief and may contain arbitrary headings and fenced code blocks, so anything
     that could also appear inside a child cannot be its boundary. `pdca split --accept`
     parses these markers; keep them exactly as written. -->

## Why this slice is oversized

The oversize here is this brief's own scope, not fields it inherited from #463. The first
attempt (`iteration-v1/`) came to 140 KB across 18 files (threshold 125 KB), and Check sent
it back to Plan with "re-plan and split". Revision 2 of the brief already records the
human's choice of three children, in this order: base-build holds → cross-wave fold holds →
docs. This proposal writes those three out as full briefs. It does not invent a new cut.

The three are separate outcomes, each with its own defect and its own check:

1. **Base-build holds.** When building one bundle's own base fails (moved `main`, a
   rewritten in-batch prerequisite, a failed fetch, a refused push of the per-bundle base
   branch), `_bundle_bases` re-raises (`flow.py:1019-1022`) and the wave loop stops
   (`flow.py:2765-2770`). The fix lives in the base-build path of `_drive_and_act` and in
   `_runnable`'s held sets. It also has to close the Check holes that belong to this path:
   a `Conflicts with` partner of a base-held bundle must be held too (iteration-v1 §6), and
   when a rewrite holds a bundle, any PR cut later from the stale line must be named.
2. **Cross-wave fold holds.** A bundle built on its own base can clash at the line fold
   with a bundle from an earlier wave. `_held_by` holds only same-wave clashes
   (`integrate.py:1743-1767`, called at `:640`), so anything else stops the run
   (`flow.py:2871-2877`). The fix lives in the fold path, in `integrate.py` and in the flow's
   fold block. It covers three partner kinds: an in-batch bundle, a finished bundle carried
   onto the line (iteration-v1 hole 2), and a line bundle that a moved `main` stranded
   (hole 3, human decision 2). It also covers decision 4: name every partner when a path
   clashes only with several of them together.
3. **Docs.** About 20 sites still state the old rule ("a later wave's PR carries every
   earlier-wave branch on the line"). Two of them are vendored spec files that need human
   approval (INTEGRATION §4). Check asked for this to be its own child so the spec approval
   does not block the behaviour fixes.

Children 1 and 2 split along a real line in the code: base build happens before Do, the
fold happens after accept. Each can be shown red→green with its own test file. Child 1's
moved-base case is tested where B's wave is the last one, so no fold runs after the hold.
The "moved base still breaks a later fold" case belongs to child 2 by its cause (a clash at
the fold). That keeps each child's test honest: neither has to fake the other's work.

I would not cut further. Splitting child 1 per cause (fetch vs push vs rewrite) would give
four children that share one handler and one held set, which costs four cycles for one
idea. Iteration-v1 showed the shared handler works for the in-batch cases. Its holes are
fixes on top, not new outcomes.

Out of all three children, as in the brief: which base a bundle gets (#727-#729); carried
prerequisites from an earlier run as base members, plus their failure cases (foreign
ancestry, two carried prerequisites that clash): #735; the fold API (#723); merge mode;
Plan-time overlap detection (#395); cleaning up per-bundle bases on origin.

## Wave sketch

All three stack in a straight line, three waves:

- **Wave 0: child-1.** It needs nothing from the others. It adds the base-hold set that
  `_runnable` honours, and the hold message.
- **Wave 1: child-2, `Depends on: child-1`.** There are two reasons. (a) Child 2's
  stranded-by-moved-main case needs the run to *get past* the base failure: B's base fails
  on the moved `main`, and the run must keep going so that W (whose base came from the new
  `main`) reaches the next fold. Without child 1, the run stops at B's base and the fold
  case can't be reached. (b) Both children edit the same block of `_drive_and_act`: the
  `_runnable` call at `flow.py:2702-2714` and the held sets declared near `:2584-2589`. If
  they ran in parallel lanes they would clash on fold. Stacking them gives child 2 a single
  held-set mechanism to reuse rather than a second copy (sizer seam 2).
- **Wave 2: child-3, `Depends on: child-1, child-2`.** The docs must describe the finished
  rule once, including which cases still stop the run. That text is only true after both
  behaviour children land. Child 3 also rewrites docstrings in `flow.py` and `integrate.py`
  that children 1 and 2 edit nearby, so it must build on their accepted result.

No `Conflicts with:` fields are needed. Every pair that touches the same code already has a
`Depends on:` edge, and that keeps them out of the same wave.

A note for the human on accept: #735 declares `Depends on: 725`. Its carried-prerequisite
failure cases need the base-hold mechanism, so `child-1` is the real prerequisite. Leaving
it on the parent #725 is still correct, only slower: it waits for the docs child too.

<!-- pdca:child child-1 -->
- **Slug:** hold-a-bundle-whose-own-base-cannot-be-built
- **Defect / goal:** On the run's line (after #723, #727, #728, #729), when building one bundle's own base fails, the whole run stops. `_bundle_bases` re-raises (`template/src/pdca_harness/flow.py:1019-1022` on `75a886e`) and the wave loop prints `STOPPING` (`flow.py:2765-2770`). The causes are: `main` moved mid-run and clashes with a prerequisite; an in-batch prerequisite was rewritten (#633); the fetch failed; the push of the per-bundle base branch was refused. Bundles that have nothing to do with the failure stay PLANNED. Goal: such a failure holds that bundle plus the bundles that declared `Depends on` or `Conflicts with` it, and nothing else. The rest of the wave completes. Each hold prints one stderr line naming the cause and a fix that works for that cause.
- **Success criterion:** Real-git tests through `flow._drive_and_act` on the `StackFoldGit` fixture (`template/tests/test_integrate_stack_bases.py:123`), loaded by path the way `template/tests/test_flow_same_wave_conflict.py:36-56` does. Every case asserts what is held (the holds map, or the bundle's state plus its stderr line) and the exit code. A test that passes on the red leg does not count. The cases:
  (1) **Moved base, last wave.** `A`, `Z` in wave 0; `B` (`Depends on: A`), `W` (`Depends on: Z`) in wave 1; after wave 0's fold, a different `a.txt` is pushed to `main`. `B` is held, and its line names `issue_A`, `<remote>/main` and the fix "rebuild issue_A's branch on the new <remote>/main". `W` is COMPLETE. No `STOPPING`.
  (2) **Rewritten in-batch prerequisite.** `A` is rewritten (force-pushed) after it lands on the line. `B` (`Depends on: A`) is held, naming A and the restore/rebuild fix. An unrelated bundle in the same wave is COMPLETE.
  (3) **Failed fetch** of a member when building `B`'s base: `B` is held, the unrelated bundle completes.
  (4) **Refused push** of `B`'s per-bundle base branch: same outcome.
  (5) **Conflicts-with partner** (iteration-v1 §6 hole 1). Take case (3)'s shape and add `X` with `Conflicts with: B`, scheduled in a later wave. `X` is held, not built on the plain base. Fix direction: `_runnable` must see the base-held set in its partner check, the way `unpushed` is passed (`flow.py:2702-2714`).
  (6) **Stale line after a rewrite hold** (hole 4). Take case (2)'s shape and add `S` (`Stacks on: A`) in B's wave. `S`'s PR carries A's old head, so a stderr line must name `issue_S` as cut from the stale line. The rewritten branch must not be dropped from the end-of-run check (`flow.py` near the old `d.name not in base_rewrites`).
  (7) **Dependent of a held bundle.** Add `C` (`Depends on: B`). `C` stays PLANNED and is reported as skipped. The exit code is 1 (human decision 3, same as #593/#674 holds today).
  In cases (1)-(4), where no dependent is left PLANNED, the run exits 3 (#693) and the held bundle is in the holds map under its own reason (not "unpushed"/"conflict").
  Pre-change, every case ends in `STOPPING` with the unrelated bundle PLANNED. Existing suites stay green: `test_integrate_bundle_base.py` (#723), `test_flow_dependency_scoped_bases.py` (#727), `test_flow_carried_prereq_bases.py` (#728), `test_flow_merged_prereq_dependency_base.py` (#729), `test_flow_same_wave_conflict.py`, `test_flow_conflict_partner_hold.py`, `test_flow_hold_exit_code.py`, `test_integrate_stack_bases.py`.
- **Repo + branch target:** eduralph/pdca-harness @ main (PRs target `main`). Do builds and the gate verifies on the run's line `pdca-integration/main-r547f8028520f` (tip `75a886e`, holding #723, #727, #728, #729), exported as `$PDCA_VERIFY_BASE`. `path:line` anchors are on `75a886e`.
- **Reproduction:** On `75a886e`: `A`, `Z` in wave 0; `B` (`Depends on: A`), `W` (`Depends on: Z`); after wave 0's fold, push a different `a.txt` to `main`. The run prints `could not build issue_B's own base … STOPPING` and `W` stays PLANNED.
- **Scope (one logical fix) / out of scope:** `template/src/pdca_harness/flow.py`: catch the per-bundle base failure in `_bundle_bases` / the wave loop. Put the bundle in a held set that `_runnable` honours for both prerequisites and `Conflicts with` partners (peer callsites: `held_unpushed` at `flow.py:2584`, set at `:2851-2852`; `held_conflict` at `:2589`; `_runnable`'s `held`/`unpushed`/`conflicts`/`conflict_held` at `:681-690`, called at `:2702-2714`; `_announce_conflict_holds` at `:1435`). Write one stderr line per hold naming cause and fix; error wording in `integrate.py` where the cause is raised; `cli.py`'s `_results_rc` (`cli.py:701`) so a base-held bundle is reported as held. Iteration-v1's `patch.diff` is prior art for the in-batch cases. Reuse it, fix the holes, and do not carry over its substitute tests (old 2a, 5). / Out of scope: any clash at the line fold, including a moved base that strands a line bundle at a later fold (child-2); docs, glossary and vendored spec text (child-3), apart from docstrings on functions this child adds; carried-from-an-earlier-run prerequisites as base members and their failure cases (#735); which base a bundle gets (#727-#729).
- **External dependencies:** none
- **Test file:** template/tests/test_flow_bundle_base_holds.py (new; C4 reverts the production change and keeps this file, so it earns its red; the fetch/push failures may be stubbed for one bundle only, everything else is real git)
- **Falsifiability:** Offline, real git, `StackFoldGit` on the run's line. With the production change reverted, every case prints `STOPPING` before the unrelated bundle builds, so its COMPLETE assertion fails. The test calls only existing module API (`flow._drive_and_act`), so the red leg imports cleanly.
- **Invariant to restore:** A failure building one bundle's own base holds that bundle and the bundles that declared `Depends on` / `Conflicts with` it, and nothing else; every hold message names the cause and a fix that works for that cause. Source: the human's decisions at the #463 re-plan (2026-10-15) and the #725 re-plan (2026-10-17); the hold model of #593 (`held_unpushed`), #629 (partner of an unpushed bundle), #674 (`held_conflict`), #693 (exit 3); `results/issue_725/iteration-v1/SUMMARY.md` §6/§9.
- **Citations expected:** Do must cite path:line on the base for every change. Peer callsites to mirror: the #629 partner hold — `_runnable(..., unpushed=held_unpushed, conflicts=...)` at `flow.py:2702-2714`; `held_unpushed` declared `flow.py:2584`, set `:2851-2852`; `_announce_conflict_holds` `flow.py:1435`; `_results_rc` `cli.py:701` and its "unpushed"/"conflict" reasons.
- **Prior-art check (triage cycles):** `f07eb75` (#629 partner of unpushed held), `0c263a9` (#674), `39feb88` (#693). No hold covers a per-bundle base. First attempt: `results/issue_725/iteration-v1/patch.diff` (in-batch cases red→green confirmed by the adversary review; holes 1 and 4 open).
- **Disposition hint:** new-feature
- **Ordering note:** First of three. #735 (carried prerequisites as base members) needs this child's hold mechanism; it declares `Depends on: 725`.
- **Difficulty:** high
<!-- pdca:end child-1 -->

<!-- pdca:child child-2 -->
- **Slug:** hold-a-cross-wave-clash-at-the-line-fold
- **Defect / goal:** A bundle built on its own base can clash at the line fold with a bundle that is already on the line from an earlier wave. `_held_by` holds only same-wave clashes (`template/src/pdca_harness/integrate.py:1743-1767`, called at `:640` on `75a886e`). Anything else raises, and `flow.py:2871-2877` prints `STOPPING`, so unrelated bundles stay PLANNED. Goal: a clash that is *one bundle's* is held like #674's `held_conflict`, naming its partners, and the run goes on. **Rule for "one bundle's clash":** the fold's merge of that bundle's own published branch conflicts, and every conflicting path is owned by a bundle branch already on the line (in-batch, carried finished, or a line bundle cut from the old `main`). A conflict with a commit the fold took in from the base (`test_flow_same_wave_conflict.py:399`), or any other fold error, belongs to the line and stops the run as it does today.
- **Success criterion:** Real-git tests through `flow._drive_and_act` on the `StackFoldGit` fixture (`template/tests/test_integrate_stack_bases.py:123`), loaded by path the way `test_flow_same_wave_conflict.py:36-56` does. Each case asserts the holds map, the named partners in the stderr line, and the exit code:
  (1) **In-batch earlier-wave partner.** `A` and `Q` in wave 0; `Y` (`Depends on: Q`, so wave 1, built on its own base from `Q` only); `A` and `Y` both add `shared.txt`; there is an unrelated chain `W→V→U`. `Y` is held naming `issue_A`, `U` is COMPLETE, no `STOPPING`.
  (2) **Finished bundle carried onto the line** (iteration-v1 hole 2). `F` finished in an earlier run and is carried before wave 0 by `_carry_finished`. `Y` clashes with `F` on `shared.txt`. `Y` is held naming `issue_F`, not "no bundle's own change accounts for …". Fix direction: include the carried finished heads in the partner set passed at `integrate.py` near `:640-675`.
  (3) **Line bundle stranded by a moved base** (hole 3, human decision 2). Child-1 case (1)'s shape plus `V` (`Depends on: W`), so a fold runs after wave 1. `W`'s own base came from the moved `main` and clashes with `A` on the line. `W` is held out of the line, and its line names `issue_A` and `<remote>/main` with the fix "rebuild issue_A's branch on the new <remote>/main". The message must not blame W or tell W's owner to update its branch. `V` is skipped; an unrelated bundle completes. Bases are not pinned to the run's start.
  (4) **Clash only with several partners together** (human decision 4). The path conflicts against two earlier bundles combined but against neither alone. The bundle is held naming both, as `_held_by` names all of `kept` (`integrate.py:1766`).
  (5) **Stays a stop.** `test_flow_same_wave_conflict.py:413` `test_a_conflict_only_with_a_base_taken_in_mid_wave_still_stops_the_run` (a conflict with a base the fold took in) still prints `STOPPING`. **Flips:** `:365` `test_a_conflict_with_earlier_wave_work_still_stops_the_run` (21 cut from the plain base, clashing with 10 on the line) becomes: 21 held and named with `issue_10`, 30 not built, no `STOPPING`. `build-notes.md` names every other test that flips, before and after.
  Exit code is 1 when a hold leaves a dependent PLANNED (decision 3). Pre-change, cases (1)-(4) end in `STOPPING` with the unrelated bundle PLANNED. Child-1's suite and the existing suites stay green.
- **Repo + branch target:** eduralph/pdca-harness @ main (PRs target `main`). Do builds and the gate verifies on the run's line, `pdca-integration/main-r547f8028520f` with child-1's accepted work folded on top, exported as `$PDCA_VERIFY_BASE`. Anchors are on `75a886e`; re-check them on the folded tip.
- **Reproduction:** On `75a886e`: `A` in wave 0 adds `shared.txt`; `Q` in wave 0; `Y` (`Depends on: Q`) adds its own `shared.txt`; unrelated `W→V→U`. The run prints `wave 1 did not integrate (issue_Y's branch … does not merge cleanly … (conflicts in shared.txt) …); STOPPING` and `U` stays PLANNED.
- **Scope (one logical fix) / out of scope:** `template/src/pdca_harness/integrate.py`: classify a cross-wave fold conflict as one bundle's clash by the rule above. Reuse `_clash` / `_partners` (`integrate.py:1817`) rather than adding a second classifier (iteration-v1 review: `_held_across` duplicated `_clash`). Name every partner, including carried finished heads and the "together" case. Word the stranded-by-moved-main message. `template/src/pdca_harness/flow.py`: in the fold block (`:2862-2879`), feed the held bundle into the same held set `_runnable` already honours (`held_conflict`, extended by child-1), so its dependents and partners are held. / Out of scope: base-build failures (child-1); docs and vendored spec (child-3), apart from docstrings on functions this child adds or changes; the fold API itself (#723); merge mode; Plan-time overlap detection (#395).
- **External dependencies:** none
- **Test file:** template/tests/test_flow_cross_wave_fold_holds.py (new; C4 reverts the production change and keeps this file, so it earns its red)
- **Falsifiability:** Offline, real git, `StackFoldGit` on the line with child-1 folded. With this child's production change reverted, cases (1)-(4) print `wave N did not integrate … STOPPING` and the unrelated bundle stays PLANNED. Case (3) needs child-1 on the base (otherwise the run stops earlier, at B's base); the verify base is the folded line, so it has it.
- **Invariant to restore:** A clash at the line fold that belongs to one bundle — every conflicting path is owned by bundle branches already on the line — holds that bundle and those that declared `Depends on` / `Conflicts with` it, names every partner, and gives a fix aimed at the bundle that can actually act; the run stops only for a failure of the shared line. Source: the human's decisions at the #725 re-plan (2026-10-17, decisions 2-4); the hold model of #674 (`held_conflict`, `_held_by`) and #694 (naming the partner); `results/issue_725/iteration-v1/SUMMARY.md` §6/§9 holes 2 and 3.
- **Citations expected:** Do must cite path:line on the base for every change. Peer callsites to mirror: `_held_by` (`integrate.py:1743`, the "all of `kept`" naming at `:1766`) and its use in `fold` (`integrate.py:636-643`, recording into `held_out`); `_partners` (`integrate.py:1817`) and `_clash` (`:1770`); the flow's fold block (`flow.py:2862-2879`) and `_announce_conflict_holds` (`flow.py:1435`); `_carry_finished` (`flow.py:1259`) for where the carried finished heads come from.
- **Prior-art check (triage cycles):** `0c263a9` (#674 same-wave hold), #694 (`e9e9926`, name the clashing bundle on re-issue). No hold covers a cross-wave clash. First attempt's `_held_across` (`results/issue_725/iteration-v1/patch.diff`) worked for in-batch partners; the code review asked to fold it into `_clash` rather than keep a second classifier.
- **Disposition hint:** new-feature
- **Ordering note:** Depends on child-1: case (3) is only reachable once a base failure no longer stops the run, and both edit the held sets and the `_runnable` call in `flow.py`.
- **Difficulty:** high
- **Depends on:** child-1
<!-- pdca:end child-2 -->

<!-- pdca:child child-3 -->
- **Slug:** document-the-dependency-scoped-base-and-hold-rule
- **Defect / goal:** The docs, glossary, config comments and docstrings still state the old stacking rule: a later wave's PR is built on, cut from, or carries every earlier-wave branch on the line. After #727-#729 and child-1/child-2, each bundle builds on a base scoped to its own dependencies. A failure that belongs to one bundle's base or one bundle's fold clash holds that bundle and its declared dependents and partners. The run stops only for a failure of the shared line (re-gate red, or a fold error that is not one bundle's clash). Goal: every tracked file states the rule the code follows.
- **Success criterion:** A wrap-aware search finds none of these literal patterns in any tracked file outside `CHANGELOG` and `results/`: `every earlier-wave branch on the line`, `integration branch the next wave builds on`, `cut each later wave's branches off it`, `cut from the line, carries every`, `carry the earlier waves' work`. How it works: for each file from `git ls-files`, strip each line's leading whitespace and comment leader (`#`, `//`, `*`), join the lines with single spaces, then search. Do pastes the short Python loop and its empty output into `build-notes.md`, plus the hit list it found before the change. Merge-mode wording ("the next wave builds on the genuinely-merged base", e.g. `pdca.toml.jinja:128`, `merge.py:2`) is correct and stays. The sites below are worded differently but state the same rule; review judges them. `09-parallel-lanes.md`'s "undeclared overlap STOPs the run" is rewritten to say which cases still stop and which hold. Per the brief this criterion is judged by T2 and review, not C4.
- **Repo + branch target:** eduralph/pdca-harness @ main (PRs target `main`). Do builds and the gate verifies on the run's line with child-1 and child-2 folded on top, exported as `$PDCA_VERIFY_BASE`.
- **Reproduction:** Run the wrap-aware search on the line tip. On `fcae4aa` it hit: `docs/05-check.md:814`, `docs/07-crosscutting.md:647`, `:653-654`, `docs/index.yml:65`, `template/PCDA/quality-cycle/08-glossary.md:276-277`, `:293`, `09-parallel-lanes.md:57`, `:69`, `template/pdca.toml.jinja:116`, `template/src/pdca_harness/config.py:359-360`, `flow.py:679`, `flow.py:2606-2607`, `integrate.py:22`, `publish.py:268-269`. Re-run it on the actual base, since those line numbers have moved.
- **Scope (one logical fix) / out of scope:** Rewrite to the dependency-scoped rule and the hold behaviour: `docs/05-check.md`, `docs/07-crosscutting.md:647-654`, `docs/index.yml`, `template/PCDA/quality-cycle/08-glossary.md:276-293` (incl. `:287`), `template/PCDA/quality-cycle/09-parallel-lanes.md:57-69`, `template/pdca.toml.jinja:113-131` (incl. the "Only a failure of the line itself stops the run" comment), `config.py:357-362`, the `integrate.py` module docstring, `publish.py:42-44`, `:252-277`, `:648-690`, `:743`, `gates.py:535-539`, `drift.py:53`, the `flow.py` comments/docstrings at `:679`, `:2606-2607` and `_adopt_split_children`'s docstring. The vendored spec edits (`08-glossary.md`, `09-parallel-lanes.md`) are a human-only item at Check (INTEGRATION §4): Do drafts them, the human approves. / Out of scope: any behaviour change; merge-mode text; `CHANGELOG` and `results/`.
- **External dependencies:** none
- **Test file:** none (docs only; the wrap-aware search script and its output go in `build-notes.md`, judged by T2 and review)
- **Falsifiability:** Docs-only, so C4 exits 77 `PDCA-UNVERIFIABLE` by construction (`engine/scripts/run-verify.sh:142-146`: no test shipped) and lands in §6 for the human, as #476 did. Do must not invent a production edit or a token test to make a red leg. What can fail: the gating `host-ci-docs` row (docs lint, site render, link audit on the patched tree); the wrap-aware search, which hits today and must come back empty; the T3 suite, since docstring edits in `.py` files must not break anything.
- **Invariant to restore:** Every tracked doc, glossary entry, config comment and docstring states the rule the code follows: a bundle's PR is built on a base scoped to what it declares, a failure that belongs to one bundle holds it and its declared dependents/partners, and only a failure of the shared line stops the run. Source: #727-#729 and this split's child-1/child-2; INTEGRATION §4 (vendored spec edits are a human-only item).
- **Citations expected:** Do cites path:line on the base for every rewritten site, and quotes the behaviour from child-1/child-2's merged code (the held-set and fold-hold code) that each new sentence describes.
- **Prior-art check (triage cycles):** The first attempt's docs hunks (`results/issue_725/iteration-v1/patch.diff`, the `docs/`, `08-glossary.md`, `09-parallel-lanes.md`, `pdca.toml.jinja`, `config.py`, `publish.py`, `gates.py`, `drift.py` parts) passed T2 and the search; reuse them, correcting `09-parallel-lanes.md:69`, which excluded base-hold partners (hole 1, now held by child-1).
- **Disposition hint:** new-feature
- **Ordering note:** Last: the docs describe the finished behaviour of child-1 and child-2, and touch docstrings in files they edit.
- **Difficulty:** medium
- **Depends on:** child-1, child-2
<!-- pdca:end child-3 -->
