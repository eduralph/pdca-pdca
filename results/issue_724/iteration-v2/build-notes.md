# Build notes — #724, iteration 2: flow builds each bundle on its declared prerequisites

Base: the run's line `pdca-integration/main-r547f8028520f` at `fcae4aa` (= `489e5fb` + #723),
the worktree's HEAD. `patch.diff` is `git diff fcae4aa` with the new test file included; it
applies cleanly to `fcae4aa` (`git apply --cached --check` on a fresh index) and has no
whitespace errors (`git diff --check`). Below, "base:N" is a line on `fcae4aa`, "new:N" a line
after the patch.

This iteration starts from the first attempt's patch (`iteration-v1/patch.diff`) and reworks
the parts the review found wrong. Everything v1 did that the review accepted is kept.

## The carry-forward items, one by one

**1. A carried prerequisite built on a `Conflicts with` / in-batch `Depends on (merged)`
partner stopped a re-issue.** v1's `_closure` followed `Depends on (merged)` and `Conflicts
with` edges only between scheduled bundles. Now the edges of a bundle are worked out by
`_ordered_after` (template/src/pdca_harness/flow.py new:885-921):
- `Depends on (merged)` from a carried bundle to a carried bundle is followed (new:910-911).
  It is still not followed from a scheduled bundle to one the run does not schedule:
  `_runnable` requires that one merged into the base first (#186), so its work is on the
  real base. (A carried finished id counts as "out of batch" in `_runnable`'s sense,
  base:771.)
- `Conflicts with` between two carried bundles: the partner counts when the carried
  bundle's branch was cut from a base holding the partner's own work, read off git by
  `_cut_above` (new:924-952). It uses #723's ownership rule: the partner's own work is the
  non-merge commits its head reaches that neither the base nor its own cut point reaches; the
  bundle was built on it if its own cut point (`stack-base-tip`) reaches any of those.
  Cached per wave (new:989-994). A git failure, or nothing recorded, is "no": then #723
  refuses the base and names the partner, so the run stops (safe side).
- Tests: `test_a_carried_bundle_built_on_its_conflicts_with_partner_brings_it_along` and
  `…_depends_on_merged_partner_brings_it_along` (template/tests/test_flow_dependency_scoped_bases.py
  new:436, :439, helper `_carried_on_partner` :413). Two real runs, all history made by the
  patched code: run 1 builds P on K and D fails; run 2 re-issues for D and must build D on
  K + P. On v1's code both fail with exactly the review's message (`could not build
  issue_D's base from issue_P … It is in the published head of issue_K … STOPPING`).

**2. A drive-set bundle that `Conflicts with` a carried bundle was built without it.** v1
built the conflict map from the drive set only (`waves.conflict_map` drops names outside the
list it is given, template/src/pdca_harness/waves.py:136-153). Now `_bundle_bases` passes
the drive set plus the carried ids (flow.py new:985), and a scheduled bundle counts a carried
partner as built first (new:915-916): the carry comes before every wave, which is also what
the line gave it before #463. Test: `test_a_bundle_that_conflicts_with_a_carried_bundle_is_built_on_it`
(new:442): run 1 finishes only K; the re-issue drives P (`Conflicts with: K`, both write
`shared.txt`), D (`Depends on: K`, which triggers the carry) and W (`Depends on: D`). On v1's
code it fails exactly as the review said (`wave 0 did not integrate (issue_P's branch …
conflicts in shared.txt …) STOPPING`).

**3. The end-of-run rewrite check could not see what a bundle's own base took.**
- `integrate.build_bundle_base` gets one optional keyword, `merged_heads`
  (template/src/pdca_harness/integrate.py new:720), filled after a successful push with the
  head the build put on the branch for each member (new:867-868, docstring new:764-768),
  the way `fold` fills `carried` after its push (base:704-705). Default `None`, so #723's own
  callers and test are unchanged. (I first named it `took`, but the function already has a
  loop variable `took` at base:812; the name clash broke it, so it is `merged_heads`.)
- `_bundle_bases` puts those heads into the run's `carried_heads` right after each base is
  pushed (flow.py new:1017), and builds each later base of the wave with them (new:1007).
  So the next fold's #633 check, any later base's check, and the end-of-run #695 check all
  hold the branch to the newest head the run took.
- The end-of-run check now gets the carried finished ids too, not only the accepted ones
  (new:2829-2830): a carried id's head is in `carried_heads` only once a base took it, and
  then a PR of this run holds it.
- Tests: `test_a_head_a_base_took_is_checked_at_the_end_of_the_run` (new:496) is the review's
  exact case (fold takes h1, a fast-forward to h2, B's base takes h2, fix/A forced back to h1
  while B builds; the run must name A's rewrite with h2 and report `{"A": "rewritten"}`);
  `…_checked_by_the_next_fold` (new:533) adds C after B, so the fold after wave 1 must stop
  on it; `test_a_carried_head_a_base_took_is_checked_at_the_end_of_the_run` (new:506) is the
  carried variant. All three fail on v1's code.

**4. `_closure` walked on through a bundle that was never built.** The walk now follows a
reached bundle's edges only when it is a member (a published branch a base can carry), or,
for a bundle that is no member, only its prerequisite edges and only when it was reached by
a prerequisite edge (flow.py new:866-882; rule in the docstring new:855-865). So a `Conflicts
with` partner that never completed brings nothing along, while `Depends on` stays transitive
through a prerequisite with no patch (as the brief's Invariant says: "`Depends on` …,
transitively"). Tests: `test_a_conflicts_with_partner_that_never_completed_brings_nothing_along`
(new:356, the review's example: Q, A `Depends on: Q`, E `Conflicts with: A`, A fails; E must
be on the real base) fails on v1's code; `test_a_prerequisite_reached_through_one_with_no_patch_is_on_the_base`
(new:325) pins the transitive half (it passes on v1 too; it guards the new walk rule).

**5. `test_integrate_carried_rewrite_late.py:267` and `:297` changed their input.** v1 did
name this in its notes, but the reviewer could not see them. This time both: it is named
below (with before → after), and two cases keep the original line-push trigger and assert
what happens now:
- `test_a_rewrite_during_the_lines_fold_stops_the_run_at_the_dependents_base`
  (template/tests/test_integrate_carried_rewrite_late.py new:285): the rewrite fires on the
  first push, asserted to be the line's own push. B's base, built next, refuses it (#633):
  B stays PLANNED, the rewrite is named once, on the STOPPING line, nothing is unchecked,
  exit 1.
- `test_a_fetch_failing_after_the_lines_fold_stops_the_run_at_the_dependents_base`
  (new:348): every fetch fails once the line's push is done. B's base cannot fetch: B stays
  PLANNED, one STOPPING line names B and the fetch, exit 1.
- One paragraph added to that module's docstring (new:34-37) saying why the late cases now
  arm their fault on B's base push.

Not changed, on purpose: the code review's minor third point (a base-build stop sets
`line_stopped`, so the end-of-run check is skipped, flow.py new:2686). It was not carried
forward. Skipping matches what a stopped line fold does (#695: "Not after the loop stopped
on the line"), and when the stop is itself a rewrite refusal, running the check would name
the same rewrite twice. The run still exits 1 (the stopped wave stays PLANNED).

## The production change as a whole (vs `fcae4aa`)

`template/src/pdca_harness/flow.py`
- **What a bundle is built on.** Before the wave builds, `_bundle_bases` (new:955-1018)
  builds each runnable bundle's own base with #723's `integrate.build_bundle_base`, from the
  members of its closure: carried finished ids first (order asked), then accepted bundles
  (wave, then name), minus held ones, kept only if the fold carries them
  (`integrate._fold_candidates`, integrate.py base:230) and they are on the bundle's own
  target. `carried` = the carry's heads plus `carried_heads`; `excluded` = the same map
  (#723 drops members from it, integrate.py base:796-798). No members, or no target → no
  base. All bases of a wave are built before any record is written.
- **Recording it.** `_point_at_integration` (new:818-842) now takes keys that are bundle
  names (the flow's use) or `(repo, base)` targets (the older direct callers in
  `test_integrate.py:351,362` and `test_integrate_stack_bases.py` base:1079). Name wins;
  neither
  → clear. It is called once per wave as before (new:2691), so
  `test_flow_adopt_split.py:268-274`'s spy still sees one call per wave.
- **Stop on a base failure** (new:2676-2687): `flow: wave k — could not build issue_D's base
  from …: <#723's error>; STOPPING — wave k and later waves not run.`, `line_stopped`, break.
  Nothing of that wave is recorded. #725 turns this into a hold.
- **The line stays the integration check**: folded after each wave as before; nothing is cut
  from it. `integ` is gone (base:2406, :2549, :2660, :1208).
- **The carry's heads.** `_carry_finished` (new:1200) drops `integ` and gets an out-parameter
  `carried`: name → the head the pushed line took (None for a gone branch). It passes an
  empty dict as the fold's `carried` (new:1293, :1297), which checks nothing and records
  (integrate.py base:514, :704-705). `_drive_and_act` turns it into `carried_finished` and
  `carry_heads` (new:2591-2598). The stderr line no longer says "this run's … bundles build
  on it" (new:1324-1327); tests match only its `flow: carried issue_X (finished` prefix.
- **#655 removed** as the brief says: `_runnable` loses `lines` (base:688), the cache dicts
  (base:747-748), `off_line` (base:767), the line check (base:785-796) and its held line
  (base:814-825); a prerequisite merged into d's base is ready (new:776). `_line_lacks_merge`
  (base:850-887) is deleted; its docstring paragraph is replaced (new:734-738).
- Comments and docstrings next to code I changed: the `carried_heads` comment
  (new:2525-2529), the fold-block comment (new:2747-2752), the end-of-run comment
  (new:2822-2828), the holds-key comment (new:2832-2835: a carried id named "rewritten" is a
  key of the map `flow_ids` returns, which adds the ids it skipped, flow.py new:3138
  `skipped | _drive_and_act(…)`), `_fold_lines`' `carried` sentence (new:1038-1050),
  `_report_late_rewrites`' first paragraph (new:2846-2853).

`template/src/pdca_harness/merged.py`: `merge_and_head` (base:149-169) deleted (its only
caller was `_line_lacks_merge`); module docstring paragraph (base:24-26) and `_pr_view`'s
docstring (base:188, new:159-162) fixed.

`template/src/pdca_harness/integrate.py`: `merged_heads` (above), and one docstring sentence in
`fold` (new:449-451): the carry now passes an empty `carried`, which checks nothing and
records. Outside the brief's file list; the old sentence (base:449) became false. `merged_heads`
is outside it too: the review's finding 3 needs the head the build merged, and only the build
knows it (see the alternatives).

## Alternatives ruled out (with cost)

- **Orient a carried–carried `Conflicts with` pair by the scheduler's rule** (name order
  unless a dependency path orders them; `waves.compute_waves(cfg, carried)` and compare
  levels). About 4 lines, no git calls. Rejected: it guesses the order, while the branches
  record it. Failing case: run 1 finishes Z1; run 2 `[Z1, A1]` builds A1 (`Conflicts with:
  Z1`) on the carried Z1 (rule 2 above); run 3 `[Z1, A1, D]` (`D: Depends on A1`): name order
  puts A1 first, so Z1 is left out, and #723 refuses D's base for Z1's commits below A1's cut
  point. `_cut_above` reads that A1 was cut above Z1 and includes it.
- **Include every carried conflict partner of a carried member, both ways.** One line
  shorter. Rejected: when the partner was built on the member (not under it), the dependent's
  base silently holds the partner's work — #723 does not refuse (those commits are the
  partner's own) — which breaks the Invariant's "nothing else of the run".
- **Test only the partner's head** (`git merge-base --is-ancestor <partner head> <cut>`): one
  git call instead of two. Rejected: if the partner's branch moved forward after the member
  was cut from it, the head is not below the cut although its older commits are, and #723
  refuses the base.
- **Return the merged heads as a third value of `build_bundle_base`.** Rejected: changes
  #723's return shape; `test_integrate_bundle_base.py` unpacks `(branch, tip)` at 12 call
  sites (e.g. :172, :303, :502), which the brief says must stay green. The keyword with a
  `None` default changes no caller.
- **Read the members' heads in `flow` around the build** instead of `merged_heads`. About 3
  lines, no integrate.py change. Rejected: #723 reads each tip once after its own fetch and
  merges exactly that commit (integrate.py base:810); a separate read in flow can see a
  different commit if the branch moves between the two reads, and would record a head the
  base never took.
- **Keep the base's heads in a map of their own, checked only at the end.** Same size.
  Rejected: the next fold's #633 check would still use the line's older head, so a rewrite
  that keeps h1 but drops h2 passes the fold while B's PR holds h2. That is the v1 behaviour
  `test_a_head_a_base_took_is_checked_by_the_next_fold` catches (on v1 the run is only
  stopped later, at C's base, with "No bundle of the run owns it").
- **The first attempt's route (`integrate.fold(into=…)`, `results/issue_463/iteration-v1`)**:
  superseded; the brief names #723's `build_bundle_base`, which is on the base.

## The test — `template/tests/test_flow_dependency_scoped_bases.py` (19 cases)

Drives `flow._drive_and_act` through real folds and real `build_bundle_base` calls on the
`StackFoldGit` fixture (loaded by path, as `test_flow_same_wave_conflict.py:36-39` does).
Stubbed: the build/sign-off leaf (`_drive_wave`: writes a patch and accepts, or fails and
leaves the bundle PLANNED), `_publish_bundle` (cuts `fix/<id>` from the recorded stack-base
tip with real git), `draft_texts` and `gh`. It imports only modules. A re-issue drives only
the unfinished ids with `batch=` all of them, as `flow_ids` does (flow.py new:3138).

| Criterion | Test (line) |
|---|---|
| (1) #630 | `test_a_dependent_carries_its_prerequisite_and_nothing_of_an_unrelated_bundle` (:284) |
| (2) transitive | `test_the_base_carries_every_prerequisite_reached_through_another` (:310); `test_a_prerequisite_reached_through_one_with_no_patch_is_on_the_base` (:325) |
| (3) conflict partner | `test_an_earlier_wave_conflicts_with_partner_is_on_the_base` (:342) |
| (4) in-batch merged | `test_an_in_batch_depends_on_merged_prerequisite_is_on_the_base` (:378) |
| (5) empty closure | `test_a_bundle_whose_only_prerequisite_has_no_patch_is_built_on_the_real_base` (:393) |
| (6) carried | `CarriedPrerequisiteBases.test_a_carried_finished_prerequisite_is_on_its_dependents_base_alone` (:624) |
| (7) foreign ancestry | `…test_a_carried_prerequisite_cut_from_a_line_holding_another_stops_the_run` (:640) |
| (8) carried rewrite | `…test_a_carried_prerequisite_rewritten_after_the_carry_stops_the_run` (:679) |
| (9) #655 | `MergedPrerequisiteJudgedOnTheBase` (:717), plain and `(merged)` edge |
| review 1 | `…built_on_its_conflicts_with_partner_brings_it_along` (:436), `…depends_on_merged_partner…` (:439) |
| review 2 | `test_a_bundle_that_conflicts_with_a_carried_bundle_is_built_on_it` (:442) |
| review 3 | `test_a_head_a_base_took_is_checked_at_the_end_of_the_run` (:496), `test_a_carried_head_a_base_took_…` (:506), `…_checked_by_the_next_fold` (:533) |
| review 4 | `test_a_conflicts_with_partner_that_never_completed_brings_nothing_along` (:356) |
| extra | `test_a_branch_the_line_carried_rewritten_before_a_dependents_base_stops_the_run` (:547) |

How I read two criteria (unchanged from v1):
- **(7) "no branch holding X's commits is recorded as anyone's stack base".** P's own
  record must hold X: it is the earlier run's record (old line, its tip), and without it #723
  has no cut point below which X's commit counts as foreign. So "anyone" is read as every
  bundle of this run: D and X have no record, P's record is exactly the earlier run's, and no
  base branch for D reached origin.
- **(8) "the wording … the test reads from that error".** The test calls
  `integrate._carried_rewrite(…)` (#633's own wording) and checks that text is in the
  STOPPING line, and spies `build_bundle_base` (pass-through) to check its `carried` had
  `issue_P → took`.
- **"no commit of any other run bundle's branch"** is checked as that bundle's own work
  (`StackFoldGit._own`: its branch minus main minus its recorded cut point minus the closure
  heads), the rule #723 uses (integrate.py base:862). Also asserted: beyond main and the
  closure heads, the tip holds only merges on its own first-parent chain (`_beyond`).

## Red → green

All runs from `template/` with `PYTHONPATH=src` and the instance venv's python, under
`timeout`, default temp dir (a temp dir under the worktree path contains `.pdca-wt`, which
makes two unrelated tests misfire: `test_leaf_workspace_admission`, `test_sweep`).

- **Project C4 gate** (`engine/scripts/run-verify.sh` with `PDCA_BUNDLE` / `PDCA_WORKTREE`,
  under `timeout 1800`): `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`. Green
  leg: all 9 touched test files OK (new file 19/19). Red leg (production hunks reverted, #723
  kept): new file `FAILED (failures=19)`, no errors; late-rewrite 4, merged-prereq 6, resume
  1, same-wave 4, slice 2 failures. The script restored the tree; I checked the worktree
  diff equals `patch.diff` byte for byte afterwards.
- **Project T3 runner** (`engine/scripts/run-suite.sh`, under `timeout 3000`):
  `PDCA-EVIDENCE: root suite OK, driver suite OK` (root 24 tests; driver 2571 tests, 2
  skipped). Baseline before any change: 2552 driver tests, all OK.
- **Against v1's production code** (the rejected attempt, swapped in and restored):
  `test_flow_dependency_scoped_bases` + `test_integrate_carried_rewrite_late` →
  `FAILED (failures=7)`: exactly the seven review cases (items 1-4 above), each failing with
  the message the review described. The other new cases pass there (they pin behaviour v1
  already had and this iteration keeps).

## Self-refutation

- **(a) Genuine red?** Yes. With `template/src` reverted to `fcae4aa`, all 19 cases of the
  new file fail on assertions, none on import (C4 red leg above, and a separate run of the
  file alone). Against v1's code the seven review cases fail. Each fails on its claim:
  (1)-(4) find Z's commits on the dependent's branch; (5) and review 4 find a recorded base
  instead of the real one; (6) finds X's commit on D's base; (7)/(8)/extra find D or B built;
  (9) finds `issue_D held`; review 1/2 find the bundle built on the line (base) or a STOPPING
  line (v1); review 3 finds no report and no stop at the fold (v1, and the carried variant
  on the base). On the base the two in-run review-3 cases fail earlier, on their set-up
  check that B's branch holds h2: B is cut from the line, which has h1 only.
- **(b) Production path?** Yes. The tests call `flow._drive_and_act` itself; the real
  `_runnable`, `_carry_finished`, `_bundle_bases`, `_closure`, `_ordered_after`,
  `_cut_above`, `integrate.fold`, `integrate.build_bundle_base`, `_report_late_rewrites` and
  `publish.write_stack_base` / `clear_stack_base` run against real git repos. Only the leaf
  (build/sign-off), publish's text/PR steps and `gh` are stubbed; spies in (8) call through
  to the real function.
- **(c) Fixture includes the fault?** Yes. Z is a real two-commit bundle of the same wave and
  is on the line (asserted). The re-issue cases are built by two real runs of the patched
  code: P really is cut from a base holding K (asserted with `_built_on("P","K")` in run 1).
  In review 2, P and K really write the same file. In review 3, `fix/A` really moves forward,
  B's branch really holds h2 and `fix/A` really ends at h1 (asserted). In review 4, A's build
  really fails and Q is really on the line (asserted). In (7), P's branch really holds X; in
  (8) `fix/P` is really force-pushed after the real carry; in (9) P's merge is really on main
  and not on the line.

## Existing tests changed (criterion 10) — every change, before → after

**Assertions restated by content.** The helper `_built_on(iid, *closure)` replaces
`_built_on_line` / `base == self.line`: the record is non-empty; its tip is origin's tip of
that branch when the wave was driven; each closure head is on it; no other run bundle's own
work is on it; beyond main and those heads only the build's first-parent merges; COMPLETE.
Where an old assertion said an unrelated bundle was on the dependent's base (the #630
behaviour itself), that claim moves to the run's line, which still folds everything.

- `test_flow_same_wave_conflict.py`: `_built_on_line` (base:169) → `_built_on`. Test 1:
  `on21` held 10 and 12 → `_built_on("21","12")`; `on30` held 10, 12, 21 →
  `_built_on("30","21","12")`; 10, 12, 21 asserted on the line instead. Test 3: 20 and 21 each
  held 10, 11, 12 → `_built_on("20","11")`, `_built_on("21","12")`, all three on the line,
  `_built_on("30","21","12")`. Test 4: `on50` held 40 and 42 → `_built_on("50","42")`; 40, 42
  on the line, 41 on neither. Partner test: `_built_on("21","12")`. Mid-wave test:
  `_built_on("30","20","10")`; 20 on the line, 22 on neither.
- `test_flow_resume_stack_prereqs.py`: (1) `base == self._line([...])` → `_built_on("D","P")`
  + fix/P on the line. (2) `_built("D")[:2] == (line, old)` → line tip at D's drive == old,
  origin's line tip == old, `_built_on("D","P")`. (3) D/E on `(line, …)` →
  `_built_on("D","P")`, `_built_on("E","D","P")`; carried, fix/P, fix/D on the line after the
  wave-0 fold; the push count is of the line's pushes (2). (4c) → `_built_on("B","Q")` + Q on
  the line. Untrusted line, red re-gate, old line: `_built_on("W","U")`.
  Without-a-finished-prereq: `_built("E")[0] == self.line` → `_built_on("E","D")`.
  Beside-them: E and U on the line holding X → `_built_on("E","X")` and **U on the real base**
  (`_on_base("U")`): U declared no edge, so under the Invariant its base must not hold X; X is
  asserted on the line. `_carried_beside` (used by 7 #672 tests): all pushes == 1 → the line's
  pushes == 1, X on the line, returns `_built_on("E","X")`.
- `test_flow_merged_prereq_on_line.py` (#655 hold tests flip per (9)): `_held` /
  `_built_on_line` → `_built_on` / `_not_held`. (1)/(2) `…holds_…_dependent` →
  `…builds_…_dependent`: not held, `_built_on("D","W")`, merge on its tip. (3)/(4):
  `_built_on_line()` → `_built_on("D","W")`. Unreadable merge commit: held → built on a base
  with the merge (only the line check needed `mergeCommit`). Cannot-be-fetched: **held → the
  run stops before D** (D never built, PLANNED, no record, one STOPPING line naming issue_D
  and "could not fetch origin"), following the brief's "A base build failure stops the run"
  (#725 makes it a hold). Carried-prereq: D on the line at `old` → line still at `old`
  holding fix/P and not the merge; D on the real base (its `(merged)` edge names an id the run
  does not schedule, merged into main), COMPLETE; `_built_on("E","P")`.
  `test_the_way_out_is_to_delete_the_line_then_re_run` →
  `test_no_way_out_is_needed_the_dependent_is_built_in_the_first_run`.
- `test_flow_reissue_after_conflict_hold.py`: `_stacked_on_10`'s
  `seen["issue_12"][0] == self.line` → `self.line_under_12 = self._built_on("12","10")`.
- `test_flow_slice.py`: three-wave test: `cut_from["issue_EB"] == origin/<line>` →
  `_built_on("EB","EA")`, `_built_on("EC","EB","EA")`; `fix/issue_EB~1` in the line → the
  first fold's recorded tip `tips[0]` is in the line (append-only); merge count `log
  --merges` → `log --merges --first-parent` (EB's branch now brings the merge of EA its own
  base made; the line's own folds still merged EA once); push count → the line's pushes (2).
  ZB test renamed `…carries_every_earlier_wave_branch_not_only_its_prerequisite` →
  `…carries_only_its_prerequisite_not_every_earlier_wave_branch`: it asserted the #630
  defect (ZZ on ZB) → ZZ not on ZB, `_built_on("ZB","ZA")`, diffs `[ZA, ZB]` then `[ZB]` right
  after ZA merges, one merge base `[za]`. The now-unused `_update_from_main` helper is deleted.

**Test inputs / stubs changed — every one:**

1. *Declared edge (allowed by (10)).* `test_flow_reissue_after_conflict_hold.py`
   `test_one_the_fold_merges_after_it_is_named_too`: 21 `Depends on: 12` → `Depends on: 12,
   10` (new `twenty_one_on` parameter of `_held_for_10`, default `"12"`, so no other caller
   changes). Its premise "21's change on top of 10's" now needs the edge.
2. **Outside (10)'s literal allowance — please judge.** `test_flow_resume_stack_prereqs.py`
   `_publish_bundle`: before, `fx._publish(...)` rewrote brief.md through `_brief(d)` and
   dropped its `Depends on`; after, the brief is saved and restored around it, as
   `test_flow_same_wave_conflict.py` (base:138-140) and the late-rewrite stub already do.
   Real publish never edits brief.md. Without it, E's closure loses P (D's rewritten brief no
   longer names P) and #723 correctly refuses E's base on a corrupted input.
3. **Outside (10)'s literal allowance — please judge (review item 5).**
   `test_integrate_carried_rewrite_late.py`:
   - `test_a_rewrite_during_the_last_fold_is_reported_and_exits_1` (new:263): before, the
     rewrite fired on the first push (the line's fold, base:265); after, on the first push
     that is not the line's (B's own base, new:272).
   - `test_an_end_of_run_check_that_cannot_fetch_is_named_and_exits_1` (new:316): before,
     fetches failed after the first push (base:289-294); after, after B's base's push
     (`armed`, new:325-334), with the line's push count still asserted == 1 and B's base's
     == 1.
   Both premises are "the fault comes after the run's last read of fix/A, so only the
   end-of-run check can see it"; since #463 that last read is B's base, not the line's fold.
   Every assertion is unchanged. The original triggers are kept as two new cases (item 5
   above), which assert the new outcome: the run stops at B's base, exit 1.
4. *Stubs of the new git step, in tests that already stub git.*
   `test_flow_conflict_partner_hold.py` `_run(stub_fold=True)`: `flow._bundle_bases` stubbed
   to `({}, {})` (`create=True`) beside the existing `_fold_lines` stub; its temp dir has no
   checkout. `test_flow_slice.py` `_live(fold=…)`: `integrate.build_bundle_base` answered
   with `("pdca-integration/main-b<name>", "0"*40)` beside the fold spy.
5. *Fixture helpers added* (`test_integrate_stack_bases.py`): `StackFoldGit._beyond`,
   `StackFoldGit._own`. No existing assertion there changed.

## Left as is, on purpose (brief: out of scope, #725)

- Prose stating the old stack rule: `_drive_and_act`'s docstring (flow.py new:2438-2446),
  `_runnable`'s docstring (new:693-695, :715-723), `_adopt_split_children`'s docstring
  (new:1946), `config.py:359-360`, `integrate.py`'s module docstring, `publish.py`
  docstrings, `gates.py:535-539`, `drift.py:53`.
- Two user-facing messages that still say PRs were "cut from the line": the end-of-run
  "unchecked" remedy (flow.py new:2876-2878) and `integrate.rewritten_carried`'s text
  (integrate.py new:1140-1143). With item 3 they can now also report a head only a base took
  (the facts say "the commit the line took from it"). The remedy still points the right way
  (restore the branch, or rebuild the PRs built on that head). Worth folding into #725.

## Risks for sign-off

- **Any base build failure stops the whole run before the wave**, including bundles not
  involved (as the brief specifies; #725 makes it a hold).
- **Undeclared cross-wave overlaps hit the line fold more often**: a later bundle is no
  longer built on the line, so an overlap with an unrelated earlier-wave bundle conflicts at
  the line fold and stops the run. Deferred to #725 by the brief.
- **`_cut_above` reads git in the primary checkout as last fetched** (the carry's fetch and
  folds). It is only consulted for a `Conflicts with` edge between two carried bundles. On a
  git failure it answers "no", and #723 then refuses the base with its own message.
- **The end-of-run check now also runs in a run where only the carry folded, once a base
  took a carried head** (one fetch more at the end). That is what review item 3 asks for.
- **A non-member reached by a prerequisite edge** (patchless, held, no target) has only its
  prerequisite edges followed, not its `Conflicts with` partners: a bundle with no branch
  imposes nothing about what it conflicts with. A judgment the Invariant leaves open.
- Re-running a batch rebuilds bases with a force-push leased on the old tip; an origin with
  `receive.denyNonFastForwards` refuses it and the run stops with #723's message. Per-bundle
  base branches stay on origin (cleanup out of scope).

## Housekeeping

- No formatter, linter or commit hook is configured in the target (no `.pre-commit-config`,
  no ruff/black/flake8 config, no hooks in `.git/hooks`; CI runs docs checks and copier
  renders, `.github/workflows/render-check.yml`). By hand: no added line over 100 columns, no
  unused import in any touched file (checked with `ast`), `git diff --check` clean.
- Scratch logs and the temporary copies used to swap production files are in the worktree's
  gitignored `.cache/` (`.gitignore:11`). The swaps were restored and checked against
  `patch.diff` byte for byte.
- No external dependency was missing: Python 3, git, and copier from the instance venv for
  the root suite.
