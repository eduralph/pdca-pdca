<!-- pdca:split-proposal v1 -->
# Split proposal — issue 739

<!-- Each child is a COMPLETE brief, not a sketch. A filled Slug alone makes `state.state`
     classify the materialised file as PLANNED, so `pdca flow` skips Plan and sends it
     straight to Do — a child missing `Repo + branch target` then builds successfully and
     has nowhere to publish. Fill every field. -->

<!-- Delimiters are HTML comments, not headings, DELIBERATELY: each child body is a full
     draft brief and may contain arbitrary headings and fenced code blocks, so anything
     that could also appear inside a child cannot be its boundary. `pdca split --accept`
     parses these markers; keep them exactly as written. -->

## Why this slice is oversized

This split is driven by this brief's own scope, not by inherited sibling fields. The
human decided it at the iteration-v4 sign-off (outcome iterated-to-Plan) after four build
rounds. The core result was right in every probe: who is held, the run goes on, the exit
code. But each round found another case where the *advice* was wrong (which partner is
named, and whose owner is told to rebuild). The patch grew to about 438 production lines.
It added a second classifier (`_held_on_line`, `_together`, `_rebuilt`), which the brief's
scope rule forbids.

`sizing.json` found three outcomes. Each can ship alone, because each leaves today's
`STOPPING` in place for the cases it does not cover. A stop is never wrong advice.

1. **Core cross-wave hold** (cases 1, 2, 5 and the case-5 flip). One rule and one code
   path: the fold's conflict branch, `_clash` / `_partners`, carried finished heads added
   to the partner set, and the held bundle fed into `held_conflict` for `_runnable`. If no
   single partner explains the clash, or a partner's own head does not merge onto the base,
   the run still stops.
2. **Joint ("together") attribution** (case 4). This turns the core's "no single bundle
   explains it" stop into a hold that names exactly the bundles that cause the clash
   together, and no unrelated line bundle. It has its own probes from rounds 1-3: an
   unrelated X named, probe-joint, probe-same-file.
3. **Stranded-by-moved-base diagnosis** (case 3). This turns the core's "partner's own head
   no longer merges onto the base" stop into a hold whose fix is aimed at the partner's
   owner. It needs #738's behaviour and a mid-run `main` move in its fixture. Most of the
   round-2/3 rejections were here, and so is the iteration-4 adversary finding (a
   prerequisite whose branch moved on is named as a partner).

Cases (1), (2) and the (5) flip are not split further. Carried finished heads only widen
the partner set. The flip is the same hold seen from a dependent.

## Wave sketch

- **Wave A — child-1 alone.** Both other children replace one of child-1's
  "still stops" branches with a hold, so they need its fold-branch classification and its
  `held_conflict` wiring on the line first.
- **Waves B and C — child-2 and child-3, one after the other, in either order.** Neither
  needs the other's result, so neither has `Depends on` the other. But both edit the same
  spot: the fold's conflict-classification branch in `integrate.py` (next to `_held_by`,
  `integrate.py:640-647` on `9f7c446`), plus the announce wording in `flow.py`. Built in
  parallel on the same base, they would clash at the fold — the very failure this work is
  about. So they declare `Conflicts with` each other, and the second one builds on the
  first one's accepted work. That costs one extra wave. The other choice would be a merge
  conflict in the main classifier.
- **#738** is not a child of this proposal, so it cannot go in the ordering fields (the
  parser accepts only `child-N`). It is already accepted and folded on the run's line
  (`pdca-integration/main-r547f8028520f` @ `9f7c446`), and every child builds and verifies
  on that line. Each brief says so in its `Ordering note`. child-3 is the one that truly
  needs #738 (its case is unreachable without it). child-1 needs it only because both edit
  the held sets and the `_runnable` call in `flow.py`.

<!-- pdca:child child-1 -->
- **Slug:** hold-a-single-partner-cross-wave-clash-at-the-line-fold
- **Defect / goal:** A bundle built on its own base can clash at the line fold with a bundle already on the line from an earlier wave. `_held_by` holds only same-wave clashes (`template/src/pdca_harness/integrate.py:1747-1771`, called at `:644` on `9f7c446`). Anything else raises, and `flow.py:2991-2997` prints `STOPPING`, so unrelated bundles stay PLANNED. Goal: when the clash is clearly *one bundle's* and specific partners already on the line explain it, hold that bundle like #674's `held_conflict`, name the partners, and keep the run going. **Rule (decided by trial merges, never by which branch touched a path):** all of these must hold. (a) The fold's merge of the bundle's head raised `_Conflict`. (b) Its head merges cleanly onto the base alone. (c) `_clash` returns kind `"batch"`, with `_partners` naming at least one bundle on the line: in-batch, a carried finished head, or a line bundle cut from the old `main`. (d) Every named partner's own head merges cleanly onto the current base alone (`_trial(base, [partner head])`). (e) The named partners explain the whole clash: base + the line *without* them + the head merges cleanly. Anything else stops the run as today: `_clash` kinds `"base"`, `"line"`, `"moved"`, `"off"`, a failed (d) or (e), or any non-`_Conflict` fold error. Siblings later turn the (e) stop into a hold (child-2: joint attribution) and the (d) stop into a hold (child-3: stranded by a moved base). This child must never give advice those cases need.
- **Success criterion:** Real-git tests through `flow._drive_and_act` on the `StackFoldGit` fixture (`template/tests/test_integrate_stack_bases.py:123`), loaded by path the way `test_flow_same_wave_conflict.py:36-56` does. Each case asserts the holds map, the partners named in the stderr line, and the exit code from `cli._results_rc(results, holds=holds)` (`cli.py:707`). Holds alone → 3; a PLANNED dependent → 1.
  (1) **In-batch earlier-wave partner.** `A` and `Q` in wave 0. `Y` (`Depends on: Q`, so wave 1, built on its own base from `Q` only). `A` and `Y` both add `shared.txt`. An unrelated chain `W→V→U`. `Y` is held naming `issue_A`, `U` is COMPLETE, no `STOPPING`. Exit 3.
  (2) **Finished bundle carried onto the line.** `F` finished in an earlier run and is carried before wave 0 by `_carry_finished` (`flow.py:1356`). `Y` clashes with `F` on `shared.txt`. `Y` is held naming `issue_F`, not "no bundle's own change accounts for …". Exit 3. Fix direction: add the carried finished heads to the partner set the fold classifies against (`fold`'s conflict branch, `integrate.py:640-647`).
  (3) **Stays a stop.** `test_flow_same_wave_conflict.py::test_a_conflict_only_with_a_base_taken_in_mid_wave_still_stops_the_run` still prints `STOPPING`, unchanged. Two more stop guards in the new file: a clash two line bundles cause only *together* (fails rule (e)) still prints `STOPPING`; and a clash with a partner whose own head no longer merges onto the base (fails rule (d)) still prints `STOPPING`. Each stop guard names the sibling child that will flip it.
  (4) **Flip.** `test_flow_same_wave_conflict.py::test_a_conflict_with_earlier_wave_work_still_stops_the_run` (21, `Depends on: 10`, cut from the plain base, clashing with 10 on the line) is renamed and now checks: 21 held; its stderr line contains `issue_10` and `(conflicts in shared.txt)` and tells issue_21's owner to rebuild its branch on issue_10's; it does NOT contain `Conflicts with: 10` (10 is 21's own prerequisite); 30 not built; no `STOPPING`; exit 1. `build-notes.md` lists every other test that flips, before and after.
  Before the change, cases (1), (2) and (4) end in `STOPPING` with the unrelated bundle PLANNED. The existing suites stay green.
- **Repo + branch target:** eduralph/pdca-harness @ main (PRs target `main`). Do builds and the gate verifies on the run's line, `pdca-integration/main-r547f8028520f` with #738's accepted work folded on top (`9f7c446`), exported as `$PDCA_VERIFY_BASE`. `path:line` anchors are on `9f7c446` (the line tip with #738 folded). Tests are pinned by name, and Do re-checks line numbers on the folded tip.
- **Reproduction:** On `75a886e`: `A` in wave 0 adds `shared.txt`; `Q` in wave 0; `Y` (`Depends on: Q`) adds its own `shared.txt`; unrelated `W→V→U`. The run prints `wave 1 did not integrate (issue_Y's branch … does not merge cleanly … (conflicts in shared.txt) …); STOPPING` and `U` stays PLANNED.
- **Scope (one logical fix) / out of scope:** `template/src/pdca_harness/integrate.py`: in `fold`'s conflict branch, classify a cross-wave conflict by rules (a)-(e). Reuse `_clash` / `_partners` (`integrate.py:1774`, `:1821`). Do not add a second classifier. The only new trials are the single-head check (d) and the without-partners check (e). Name every partner, carried finished heads included. Word the partner-is-a-prerequisite message (flip case). `template/src/pdca_harness/flow.py`: in the fold block (`:2862-2879`), feed the held bundle into the held set `_runnable` already honours (`held_conflict`, as extended by #738), so its dependents and partners are held; extend `_announce_conflict_holds` (`flow.py:1532`) for the new line. / Out of scope: joint ("together") attribution and leave-one-out naming (child-2); the stranded-by-moved-base diagnosis, partner-aimed advice, and any squash/rebuild of the head for trials (child-3); base-build failures (#738); docs and vendored spec (#740), apart from docstrings on functions this child adds or changes; the fold API (#723); merge mode; Plan-time overlap detection (#395).
- **External dependencies:** none
- **Test file:** template/tests/test_flow_cross_wave_fold_holds.py (new; C4 reverts the production change and keeps this file, so it earns its red). Keep only cases (1)-(4) above; the iteration-v4 copy in the bundle also holds case (3)/(4)-of-the-parent tests that belong to child-2 and child-3.
- **Falsifiability:** Offline, real git, `StackFoldGit` on the line with #738 folded. With this child's production change reverted, cases (1), (2) and the flip print `wave N did not integrate … STOPPING` and the unrelated bundle stays PLANNED.
- **Invariant to restore:** A clash at the line fold that belongs to one bundle, and that named partners on the line fully explain, holds that bundle and those that declared `Depends on` / `Conflicts with` it, names every partner, and gives a fix aimed at the bundle that can act. Every case the rule cannot attribute stays a stop. Source: the human's decisions at the #725 re-plan (2026-10-17, decisions 2-4) and the #739 iteration-v4 split decision; the hold model of #674 (`held_conflict`, `_held_by`) and #694 (naming the partner).
- **Citations expected:** Do cites path:line on the base for every change. Peer callsites to mirror: `_held_by` (`integrate.py:1747`) and its use in `fold` (`integrate.py:640-647`, recording into `held_out`); `_partners` (`integrate.py:1821`) and `_clash` (`:1774`); the flow's fold block (`flow.py:2980-2999`) and `_announce_conflict_holds` (`flow.py:1532`); `_carry_finished` (`flow.py:1356`).
- **Prior-art check (triage cycles):** `0c263a9` (#674 same-wave hold), #694 (`e9e9926`, name the clashing bundle on re-issue). `results/issue_739/iteration-v1/patch.diff` got the in-batch hold right. Its code review asked to fold `_held_across` into `_clash`. iteration-v4's `_held_on_line` is the oversized form this split exists to avoid.
- **Disposition hint:** new-feature
- **Ordering note:** #738 is accepted and folded on the line this child builds on. Both edit the held sets and the `_runnable` call in `flow.py`. child-2 and child-3 both build on this child.
- **Difficulty:** medium
<!-- pdca:end child-1 -->

<!-- pdca:child child-2 -->
- **Slug:** name-the-joint-partners-of-a-cross-wave-fold-clash
- **Defect / goal:** After child-1, a cross-wave fold clash that no single line bundle explains still stops the run (child-1's rule (e) fails). Example: the head conflicts with two earlier bundles combined but with neither alone. Goal: hold the bundle and name *exactly* the bundles that cause the clash together, and never a line bundle the clash does not need. The naming rule is leave-one-out, by trial merge: a bundle on the line is named only if base + the line without it + the head merges more cleanly than with it. A named set is accepted only if base + the line without the whole set + the head merges cleanly. If no such set is found, the run still stops. The fallback lives in the fold's classification next to `_held_by`, NOT inside `_clash`, so `_clash`'s contract for its #694 caller (the pre-wave carry, `_clash` docstring `integrate.py:1777-1781`) does not change. The trial tip for this rule is the head's *own* change only. Do not squash the head onto its start (the iteration-v4 `_rebuilt` bug that named a prerequisite whose branch had moved on). If child-3 is already on the line, reuse its own-change helper.
- **Success criterion:** Real-git tests through `flow._drive_and_act` on `StackFoldGit`, loaded as in `test_flow_same_wave_conflict.py:36-56`, asserting the holds map, the named partners in stderr, and `cli._results_rc(results, holds=holds)`:
  (1) **Together only** (parent case 4). The path conflicts against `P` and `R` combined but against neither alone. The bundle is held naming both `issue_P` and `issue_R`. An unrelated chain completes. No `STOPPING`. Exit 3.
  (2) **Unrelated line bundle not named** (iteration-1 probe). Same as (1) plus an unrelated `X` on the line that touches other files. `issue_X` does not appear in the hold line or its proposed `Conflicts with`.
  (3) **Direct and joint on the same file** (iteration-3 `probe-same-file`). The head clashes directly with `A` and jointly with `P`+`R` in the same file. The hold names `A`, `P` and `R`. The proposed rebuild merges cleanly onto the line when tried.
  (4) **Several joint clashes at once** (iteration-2/3 probe-joint). Two separate joint pairs in different files. Both pairs are named, and nothing else.
  (5) **Still a stop.** A clash no set of line bundles explains (the base-taken-in case) still prints `STOPPING`. child-1's "together still stops" guard flips to a hold, and `build-notes.md` records that flip.
  With the production change reverted, (1)-(4) print `STOPPING` and the unrelated bundle stays PLANNED. child-1's suite and the existing suites stay green, apart from the flipped guard.
- **Repo + branch target:** eduralph/pdca-harness @ main (PRs target `main`). Do builds and the gate verifies on the run's line, `pdca-integration/main-r547f8028520f` with #738 and child-1's accepted work folded on top (and child-3's, if it went first), exported as `$PDCA_VERIFY_BASE`. Anchors are on `9f7c446`. Do re-checks line numbers on the folded tip.
- **Reproduction:** On the line with child-1 folded: base has a nine-line `shared.txt`; `P` (wave 0) edits line 2; `R` (wave 0) edits line 3; `Y` (wave 1, `Depends on` an unrelated wave-0 bundle) rewrites lines 2-3. `Y` merges onto base + P alone and onto base + R alone, but not onto base + P + R. The run prints `STOPPING`. (Do confirms the exact edit shape that makes the pair conflict only together; iteration-v4's tests have a working one.)
- **Scope (one logical fix) / out of scope:** `template/src/pdca_harness/integrate.py`: a joint-attribution fallback in the fold's conflict classification, called where child-1's rule (e) fails. Mirror `_held_by`'s "together" trial (`integrate.py:1771`), narrowed by leave-one-out. Trials use the head's own change only. Add a short comment on the cost: O(n) trials per round, run only after a fold merge has already conflicted. `template/src/pdca_harness/flow.py`: only the announce wording for a hold with several partners, if child-1's line does not already cover it. / Out of scope: `_clash` / `_partners` themselves; the stranded-by-moved-base diagnosis and partner-aimed advice (child-3); anything child-1 already does; docs (#740), apart from docstrings on functions this child adds or changes.
- **External dependencies:** none
- **Test file:** template/tests/test_flow_cross_wave_joint_holds.py (new)
- **Falsifiability:** Offline, real git. Revert this child's production change, keep the test file: cases (1)-(4) end in `STOPPING` (child-1's behaviour), so the file goes red.
- **Invariant to restore:** A fold clash that line bundles cause together holds the bundle and names exactly those bundles, never one the clash does not need. Source: the human's #725 re-plan decision 4 and the #739 iteration-v4 split decision; findings from #739 iterations 1-3 (unrelated X named, probe-joint, probe-same-file).
- **Citations expected:** `_held_by` and its "all of `kept`" naming (`integrate.py:1747`, `:1771`); `_clash` docstring (`:1777-1781`) to show its contract did not change; child-1's classification call site in `fold` (Do cites the line on the folded tip); `results/issue_739/iteration-v3/review-evidence/probe-same-file.log` for case (3)'s shape.
- **Prior-art check (triage cycles):** #674 (`0c263a9`) "together" naming in `_held_by`. `_together` in `results/issue_739/iteration-v4/patch.diff` (`integrate.py:1921-1967` there) ran a greedy smallest-set search on a squashed head. It is a reference for the probes, not code to copy. The squash is the bug the adversary found.
- **Disposition hint:** new-feature
- **Ordering note:** Builds on child-1. Shares the fold classification branch with child-3, so the two never build in the same wave.
- **Difficulty:** medium
- **Depends on:** child-1
- **Conflicts with:** child-3
<!-- pdca:end child-2 -->

<!-- pdca:child child-3 -->
- **Slug:** aim-the-fix-at-a-line-bundle-stranded-by-a-moved-base
- **Defect / goal:** After child-1, a fold clash where the named partner on the line no longer merges onto the current base alone still stops the run (child-1's rule (d) fails). This happens when `main` moved mid-run and a line bundle was cut from the old `main`. The clash is the partner's problem, not the held bundle's. But a plain hold would tell the wrong owner to rebuild. Goal: tell "the partner is stranded by a moved base" apart from an ordinary overlap, by trial merge. The case is `_trial(base, [partner head])` conflicting while the bundle's own change merges onto the base. Then hold the bundle out of the line, name the partner and `<remote>/main`, and aim the fix at the partner: "rebuild issue_A's branch on the new <remote>/main". Never blame the held bundle or tell its owner to update its branch. `Conflicts with` partners of that hold must not get the opposite advice either. Also fix the iteration-4 adversary finding: a bundle the head holds through its base (a prerequisite, a transitive prerequisite, or the `Stacks on` line) whose branch has since moved on (a fast-forward fixup, which the fold takes, `integrate.py:1329-1331` on the iteration-v4 tip) must not be named as a partner. Build every trial tip from the head's *own* change only: merge into the trial start what the head already holds of each line bundle (`git merge-base head <its head>`) so the old copy is on both sides. Do not squash the head onto its start. "Bases are not pinned to the run's start" is a stated non-change. No code pins them, and the tests assert only that the bundle's base holds the moved `main`.
- **Success criterion:** Real-git tests through `flow._drive_and_act` on `StackFoldGit`, as in child-1, asserting the holds map, stderr, and `cli._results_rc(results, holds=holds)`:
  (1) **Stranded partner** (parent case 3). child-1's case (1) shape plus `V` (`Depends on: W`), so a fold runs after wave 1. `main` moves mid-run. `W`'s own base came from the moved `main` and clashes with `A` on the line. `W` is held out of the line. Its line names `issue_A` and `<remote>/main` with the fix "rebuild issue_A's branch on the new <remote>/main", and does not blame `W` or tell W's owner to update its branch. `V` is skipped, an unrelated bundle completes, `W`'s base holds the moved `main`. Exit 1.
  (2) **Moved-on prerequisite not named** (iteration-4 adversary probe). Base has a nine-line `shared.txt`. `K` (wave 0) adds `k.txt`. `N` (wave 0) edits line 2. `Y` (`Depends on: K`) edits line 2. Unrelated `W→V→U`. After `Y` publishes, K's owner pushes a fixup to `fix/K` that changes only `k.txt`. `Y` is held naming `issue_N` only. The line does not contain "conflicts with issue_K's" or "rebuild issue_Y's branch on issue_K's", and no K rebuild is proposed.
  (3) **Iteration-2/3 stranded probes**, one test each. The stranded trial runs on the base the head actually holds (`git merge-base head <remote>/main`), NOT on the current tip of `<remote>/main` (iteration-v3 SUMMARY §6, "main has moved twice"). (a) **`main` moved twice:** A edits lines 2 and 8 of a nine-line `shared.txt`; Y (`Depends on: Q`) edits line 2; an unrelated `m.txt` commit lands on main after the first fold, so Y's base holds it; after Y publishes, main edits line 8. A is NOT called stranded (it merges onto the base Y holds); Y gets the ordinary overlap hold naming `issue_A` with a `Conflicts with` proposal, and no "rebuild issue_A's branch on the new <remote>/main". (b) **`main` undid a commit:** A adds `a.txt`; main adds its own `a.txt` after the first fold; Y (adds `y.txt` only) and V (adds `v.txt` only) are built on that main; then main deletes `a.txt` again. Neither Y nor V is told to declare `Conflicts with: A`; their step is "update the branch from <remote>/main". (c) **Stranded check tied to the clash:** a partner counts as stranded only when the base move is what makes the head clash with it (the iteration-v2 finding: A edits `a.txt` and `shared.txt`, main later edits `a.txt`, Y edits `shared.txt` and does not hold that main commit) — Y gets the overlap advice, not only A's rebuild. (d) The `Conflicts with` partner `X` of a stranded hold gets no advice blaming the held bundle or waiting for its rebuild.
  (4) **Still a stop.** A clash with the base itself (the base-taken-in test) still prints `STOPPING`. child-1's "partner's own head fails onto the base" guard flips to a hold, and `build-notes.md` records that flip.
  With the production change reverted, (1) and (3) print `STOPPING` (child-1's behaviour), so the file goes red. (2) fails only if child-2 went first with a squashed trial; otherwise it is a guard for the own-change rule. Say which in `build-notes.md`. child-1's suite, child-2's (if folded) and the existing suites stay green, apart from the flipped guard.
- **Repo + branch target:** eduralph/pdca-harness @ main (PRs target `main`). Do builds and the gate verifies on the run's line, `pdca-integration/main-r547f8028520f` with #738 and child-1's accepted work folded on top (and child-2's, if it went first), exported as `$PDCA_VERIFY_BASE`. Anchors are on `9f7c446`. Do re-checks line numbers on the folded tip.
- **Reproduction:** On the line with child-1 folded, run case (1)'s shape. The fold after wave 1 prints `wave N did not integrate … STOPPING`, and the unrelated bundle stays PLANNED.
- **Scope (one logical fix) / out of scope:** `template/src/pdca_harness/integrate.py`: the stranded check where child-1's rule (d) fails, plus one helper that builds a trial tip from the head's own change only. If child-2 is already on the line, switch its joint trials to that helper. `template/src/pdca_harness/flow.py`: the partner-aimed hold message in `_announce_conflict_holds` (`flow.py:1532`), and the advice for `Conflicts with` partners of a stranded hold. / Out of scope: pinning bases to the run's start (stated non-change); joint attribution itself (child-2); base-build failures (#738); docs (#740), apart from docstrings on functions this child adds or changes.
- **External dependencies:** none
- **Test file:** template/tests/test_flow_cross_wave_stranded_holds.py (new)
- **Falsifiability:** Offline, real git, `StackFoldGit` on the line with #738 and child-1 folded. Case (1) needs #738 on the base (without it the run stops earlier, at the base build). The verify base has it. With the production change reverted, (1) and (3) end in `STOPPING`.
- **Invariant to restore:** When a fold clash comes from a line bundle that no longer fits the moved base, the bundle that can act (the partner) gets the fix, the held bundle is not blamed, and no bundle is named that the head's own change does not clash with. Source: the human's #725 re-plan decision 2 (hole 3, `results/issue_725/iteration-v1/SUMMARY.md` §6/§9); the #739 iteration-v4 split decision; the iteration-v4 adversary finding (`results/issue_739/iteration-v4/check-advisory-adversary.md`).
- **Citations expected:** `_trial` and its setup/teardown (iteration-v4 tip `integrate.py:2080-2117`; Do re-anchors). Share one detached-worktree context manager between `_trial` and the new own-change helper, so the copy-paste from iteration-v4's `_rebuilt` is not repeated. Cite the fast-forward take in the fold, `_announce_conflict_holds` (`flow.py:1532`), and child-1's rule-(d) call site on the folded tip.
- **Prior-art check (triage cycles):** `_held_on_line`'s stranded/past/own/older branches and `_rebuilt` in `results/issue_739/iteration-v4/patch.diff`. The probes there are worth reusing. The squash in `_rebuilt` is the adversary's bug and must not come back. Iteration-v2/v3 SUMMARY §6 list the stranded-message rejections this child's case (3) covers.
- **Disposition hint:** new-feature
- **Ordering note:** Builds on child-1. Needs #738 (accepted and folded on the line) for case (1) to be reachable. Shares the fold classification branch with child-2, so the two never build in the same wave.
- **Difficulty:** high
- **Depends on:** child-1
- **Conflicts with:** child-2
<!-- pdca:end child-3 -->
