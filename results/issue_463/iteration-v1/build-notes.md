# Build notes — issue 463 / dependency-scoped stack bases

Target: `eduralph/pdca-harness` `main`. Built in the per-cycle worktree on the stacked base
**`489e5fb`** (`pdca-integration/main-r547f8028520f`, which carries 672, 673, 693, 694 and 695
on top of `d6057eb`). "base:" citations are `path:line` on `489e5fb`; "now:" citations are on
the patched tree (`489e5fb` + `patch.diff`). Every brief citation was re-checked on `489e5fb`:
`_point_at_integration` moved from `flow.py:890-910` (d6057eb) to `flow.py:890-910` (same),
its call from `:2442` to **`:2549`**; the run's fold block is `flow.py:2605-2668`; `_fold_lines`
`:913-960`; `fold`'s signature `integrate.py:327-338` (brief: `:300-333`) and its destination
`:510` (brief: `:449`); `integration_branch` `:126-142`; `_flatten_base` `:154-163`;
`write_stack_base`/`clear_stack_base` `publish.py:647-670`; `_stack_base_branch` `:740-749`;
`_runnable`'s #655 hold `flow.py:735-744`, `:784-796`, `:814-825`.

## What changed, and why

**The invariant restored:** a bundle's base carries exactly the accepted work of the bundles
it was ordered after by a declared edge, and nothing else of the run. Before: every runnable
bundle of every wave was pointed at the run's one line (base: `flow.py:2549` →
`_point_at_integration`, `:904-910`), which holds every bundle an earlier wave accepted.

### `integrate.py`
- **`bundle_base(cfg, base, batch, name)`** (now: `integrate.py:154-164`). The name is the
  run's line name + `-d` + the bundle id, flattened with `_flatten_base`. Batch-scoped like the
  line; injective in (base, batch, id) because the line name ends in the 12-hex batch key (or,
  unscoped, the flattened base, which never contains `-d`/`-r`), and a flattened id has no `/`,
  so no ref is a path prefix of another (git refuses `x` beside `x/y`).
- **`fold(..., into=None)`** — the API change the brief puts in scope (now: signature `:360`,
  docstring `:491-504`):
  - destination is `into` instead of `integration_branch(...)` (now: `:553`);
  - always starts fresh from `<base_remote>/<base>` as fetched (now: `:555-556`);
  - one target only, else `ValueError` (now: `:532-535`) — a caller bug, never reached from the
    flow, which filters members to the bundle's own target;
  - push rule (now: `:729-747`): plain `git push origin <into>` when origin lacks it;
    `--force-with-lease=<into>:<tip fetched>` when re-building it. A refused push raises
    `IntegrationError` naming the branch with the line's remedy (delete the old branch, or
    allow force-pushes on `pdca-integration/*`);
  - `carried` is still **checked** (#633, `_carried_tips`, now: `:542-543`) but never
    **written** (now: `:752`): that record is "what the run's line carries";
  - merge commits say which branch they build: `pdca-integrate: <bundle> onto <into>`
    (`_merge_published`, now: `:879-905`). Without this, the line's history (which takes
    in each dependent's base via its branch) would hold two merges titled
    `pdca-integrate: issue_EA`, and nothing tells a reviewer which base a merge built;
  - same `integ_lock` and same per-target worktree as the line's folds (unchanged code path,
    base: `:536-547`), so folds of one target stay serialised and the tree is reset as today.
- `_carried_tips(..., into=)` (now: `:758-800`): the #633 refusal wording for a bundle base
  ("building <into> on <tip> would cut a bundle from commits <line> does not hold…") instead
  of claiming the old and new commits would meet on it (they would not: it starts fresh).
- `rewritten_carried`'s end-of-run message (now: `:870-873`): "every PR of this run built on a
  base that took <head>" replaces "every PR this run cut from <line>", which is no longer true.
- Module docstring (now: `:1-46`): states the two kinds of branch and the new rule.

### `flow.py`
- **`_closure`** (now: `flow.py:843-880`): the in-run prerequisite closure, transitively.
  Followed edges: plain `Depends on` and legacy `Stacks on` to any in-run bundle (drive set +
  carried finished ids); `Depends on (merged)` to a bundle **of the schedule** (see deviation
  1); `Conflicts with` (either side, `waves.conflict_map` of the live bundles) to a bundle of
  the schedule in an earlier wave than the one it is followed from.
- **`_bundle_bases`** (now: `:883-940`): for each runnable bundle, members = closure ∩
  (carried finished ids first, then `accepted` in wave/name order) − held, filtered by
  `integrate._fold_candidates` (patch, target, published branch) and to the bundle's own
  `(repo, base)`. Non-empty → ONE `integrate.fold(..., into=bundle_base(...))`, tip read under
  the same lock stack (as `_fold_lines` does, base: `flow.py:947-953`). Empty → nothing (real
  base). An `IntegrationError` is re-raised naming the bundle and its base.
- **`_drive_and_act`** (now: `:2584-2607`, replacing base: `:2544-2549`): builds the bases
  where the line folds for real (`build_bases`, now: `:2526-2529`: stack mode, publishing on,
  not a dry-run), then `_point_at_integration(bases, runnable, base_tips)`. A base that cannot
  be built prints `flow: wave k — could not build issue_X's base … ; STOPPING` and stops the
  run before the wave builds, as a fold of the line does (`line_stopped = True`, like base:
  `:2646-2652`).
- **`_point_at_integration`** (now: `:817-840`): its first argument may be keyed by bundle name
  (the flow's use now) or by target (the old use). Kept, not replaced, because three tests
  call it directly by target (`test_integrate.py:351,362`, `test_integrate_stack_bases.py:1079`)
  and `test_flow_adopt_split.py:263-274` spies on it per wave with a positional-only spy.
- **`_carry_finished`** (now: `:1118-1258`) returns the ids it carried (they join closures);
  its `integ` parameter is gone (see below). A test patches it with `lambda *a, **k: None`
  (`test_flow_out_of_batch_prereq_hold.py:332`), so the caller takes `… or ()` (now: `:2512`).
- **Design §6 (#655)**: `_runnable` no longer takes `lines`; a prerequisite `merged_into`
  d's base is enough (now: `:734-737`, `:775`). Removed with it: `_line_lacks_merge` (base:
  `:850-887`), the `views`/`lacks`/`off_line` state and the held line (base: `:747-748`,
  `:767`, `:784-796`, `:814-825`). The call site no longer passes `lines` (base: `:2503-2505`).
- `integ` (base: `:2406`, `:2474`, `:2504`, `:2549`, `:2658-2660`) was only read by the two
  removed uses; after the change it was write-only, so it is removed.
- Docstrings/comments that stated the old rule: `:678-679`, `:721-722`, `:2357-2367`,
  `:2664-2669`, `:2786` (the "rebuild every PR this run cut from the line" advice).

### `publish.py`, `config.py`
- Comment `publish.py:252-277` (brief: `:265-277`), `write_stack_base` `:647-657`,
  `_read_stack_base` `:674-675`, `read_stack_base` `:680-683`, `_stack_base_branch` `:742-751`:
  text only, no code change. Everything downstream reads the record as before.
- `config.py:358-363`: the `wave_mode` comment stated the old rule.

### Docs
- `docs/07-crosscutting.md:643-679` (the brief's `:645-660`), plus three passages that still
  described bundles cut from the line: `:724-733` (late publish), `:764-769` (the carry
  "points that target's bundles at it"), `:861-865` (the #655 hold paragraph — replaced,
  since Design §6 removes the hold).
- `template/PCDA/quality-cycle/09-parallel-lanes.md:57, :59-61, :69` (the brief's range) and
  `:89` (same file, same stale phrase). **Human-only Check item** per INTEGRATION §4.
- `engine/scripts/run-docs-check.sh`: `docs lint clean, site render + link audit clean`.

## Deliberate readings of the brief (please check these)

1. **In-batch `Depends on (merged)` is in the closure.** Design §1 says "`Depends on (merged)`
   and out-of-batch prerequisites are not in it: their work is on the real base (#647 holds d
   until it is)". That reason holds for a prerequisite the run does not drive (`_runnable`,
   base: `flow.py:780-800`, holds d until it merges). It does not hold for one **in** the drive
   set: `_runnable` lets d through at COMPLETE (base: `flow.py:694-696`), nothing merges it, so
   excluding it would build d on a base without its declared prerequisite — a regression
   against today. So the closure follows `Depends on (merged)` only to bundles of the schedule
   (now: `flow.py:871-872`). Pinned by `test_an_in_batch_depends_on_merged_prerequisite_is_on_the_base`
   (new file `:303-316`). A `Depends on (merged)` to a carried finished id is NOT followed
   (that id is outside the schedule, so #186 gates it): see the restated
   `test_a_carried_prerequisite_whose_head_is_on_the_line_counts` below.
2. **`Conflicts with` to a carried finished id is not followed.** Design §1 and the Invariant
   say "a `Conflicts with` edge to a bundle in an earlier wave"; a carried id is in no wave
   (the scheduler and `conflict_map` see only the drive set). Followed literally.
3. **Transitive edges are followed through any in-run bundle, then filtered.** E.g. H →
   N (close, no patch) → A: H's closure holds A. "Reachable … transitively" first, "only
   accepted bundles whose branch the fold can carry count" second.
4. **Every base-build failure stops the run**, not only a refused push (the brief names the
   push case and says "as for any fold error"). The run stops before the wave builds, so no
   bundle of the wave is built on a partial set of bases.
5. **Force push is `--force-with-lease=<branch>:<fetched tip>`**, not plain `--force`: still a
   force push, but it refuses if another run moved the branch since this fold fetched it.
6. **Dry-run builds no bases** (no `integrate.fold` call): the dry-run already pointed nothing
   at the line (base: `integ` stayed empty, `:2658`), so every bundle built on its base; a
   dry-run fold call per bundle would also break `test_integrate_stack_bases.py:1133`
   ("every fold of a run: one line").

## Alternatives considered (with cost)

- **A separate entry point (`integrate.fold_base`) calling a shared private body**, so
  existing `integrate.fold` spies would not see base builds. Rejected: the brief makes this
  "an API change to `fold`". Cost of the chosen route is the spy filters below (≈ 12 test
  lines over 4 files: `test_flow_slice.py:1315-1327`, `test_flow_resume_stack_prereqs.py:140-141`,
  `test_flow_slice.py:1605-1617`, `test_integrate_carried_rewrite_late.py:288-297`).
- **Keep `_runnable(lines=…)` and `_line_lacks_merge`, just stop passing `lines`.** 1 line
  instead of −73 in `flow.py`, but it leaves a parameter and docstring describing a bundle
  "cut from that line", which no longer happens. Removed. `merged.merge_and_head`
  (`merged.py:149-169`) now has no caller; left in place (separate module, own docstring) —
  follow-up.
- **Cut a single-prerequisite bundle straight from its prerequisite's branch** — rejected in
  the brief (Alternatives); not built.

## Criterion (5): every existing test assertion that changed, before → after

All "built on the line" checks are replaced by content checks through one shared helper,
`StackFoldGit._beyond(tip, base, heads)` (`test_integrate_stack_bases.py:219-229`): the
commits `tip` holds beyond `base` (origin's `main` when the bundle was built) and the members'
branch tips, other than merges on `tip`'s own first-parent chain, must be **none**. Each
module's `_built_on(iid, *closure)` also asserts the recorded tip equals origin's tip of the
recorded branch at drive time (the base it was built on). This is stronger than "no commit of
any other run bundle's branch", and the literal wording would be wrong where branches
legitimately share a prerequisite's commits (e.g. `fix/22` and `fix/30` both hold `fix/10`'s
commit in `test_a_base_taken_in_mid_wave_does_not_stop_a_same_wave_hold`).

`test_flow_same_wave_conflict.py` — `_built_on_line(iid)` (base `:169-178`, "base ==
self.line") → `_built_on(iid, *closure)` (now `:173-197`):
- `…holds_the_later_bundle_and_the_run_goes_on`: `on21` held 10, 12, not 11 → `on21 =
  _built_on("21","12")` (no 10/11). `on30` held 10, 12, 21, not 11 → `_built_on("30","21","12")`;
  "10, 12, 21 on the line" moved to `self.line` (now `:221-229`).
- `…shared_file_that_merges_cleanly…`: 20/21 held 10, 11, 12 → `_built_on("20","11")`,
  `_built_on("21","12")`, `_built_on("30","21","12")`; "10, 11, 12 on the line" (now `:264-268`).
- `…three_way_chain…`: on50 held 40, 42 → `_built_on("50","42")`; 40/42 on, 41 off the line
  (now `:286-290`).
- `…partner_of_a_held_bundle…`: `_built_on("21","12")` (now `:321`).
- `…base_taken_in_mid_wave_does_not_stop…`: `_built_on("30","20","10")`; 20 on, 22 off the
  line (now `:437-440`).

`test_flow_resume_stack_prereqs.py` (brief: `:176-219`, `:290-310`, plus the other `(base,
tip) == (self.line, …)` sites the brief did not list):
- (1) `:213-214`: `base == line`, P on line_tip → `_built_on("D","P")`, P on the line.
- (2) `:228-234`: `_built("D")[:2] == (line, old)` → line tip still `old` (continued, not
  replaced) + `_built_on("D","P")`. Unforced pushes only — the base's plain push included.
- (3) `:243-252`: D/E on line → `_built_on("D","P")`, `_built_on("E","D","P")`; `len(pushes)==2`
  now counts the line's pushes (base pushes filtered out); `carried`, P, D asserted on the
  line instead of E's line tip.
- (4c) `:283-285`, (5) `:302-304`, (8) `:367-369`, held-ids `:492-496`: `(base, tip) ==
  (line, line_tip)` → `_built_on(<iid>, <closure>)`; the "gone" commits are checked on the base
  tip and, where the old check was really about the line, on the line.
- (7) `:337`: `_built("E")[0] == self.line` → `_built_on("E","D")`. The `events` spy counts line
  folds only (`:140-141`), so `["wave:issue_D","fold","wave:issue_E"]` is unchanged.
- clean-beside `:466-470`: E and **U** on the line → `_built_on("E","X")`; **U flips to the
  real base** (`_on_base("U")`): U declares nothing, so by the Invariant it carries nothing.
- `_carried_beside` `:550-557`: `len(pushes)==1` counts the line's pushes; E →
  `_built_on("E","X")`, X on the line.

`test_flow_merged_prereq_on_line.py` (brief: `:202-219`, `:293`; Design §6 flips):
- (1) `…holds_a_depends_on_merged_dependent` → `…builds_…` (now `:200-211`): `_held(...)` →
  `_built_on("D","W")` + merge commit on D's tip; the two "line lacks P" assertions kept.
- (2) **criterion (7)** `…holds_a_plain_depends_on_dependent` → `…builds_…` (now `:213-221`).
- (3)/(4) `_built_on_line()` → `_built_on("D","W")` (now `:229`, `:237`).
- (5a) `…unreadable_merge_commit_holds…` → `…no_longer_holds…` (now `:243-252`): the hold came
  only from `_line_lacks_merge`; `merged_into` reads `state` alone (`merged.py:70-114`).
  **Not on the brief's list**; same Design §6 flip.
- (5b) `…checkout_that_cannot_be_fetched_holds…` → `…stops_the_run_before_the_dependent`
  (now `:254-266`). **Not on the brief's list, and not a "built" flip**: with origin
  unreachable, D's own base cannot be fetched, so the run stops before D is built (deviation 4).
  Still fail-closed: D is never built on an unchecked base. Asserted: D unbuilt, PLANNED, one
  `STOPPING` line naming issue_D and "could not fetch origin".
- carried head `:296-306`: **not on the brief's list.** D (`Depends on (merged): P`, P a carried
  finished id) was asserted built on the line at `old` without P's merge commit. Under
  deviation 1, that edge is not followed (P is outside the schedule; #186 gates it), so D's
  closure is empty → real base, which has P's merge. The line facts (`tip == old`, P's head on
  it, merge commit not on it) are asserted on the line; D on the real base; E (plain edge to P)
  `_built_on("E","P")`.
- way-out `:308-319` → `test_no_way_out_is_needed_the_dependent_is_built_in_the_first_run`:
  the re-run/delete legs exited a hold that no longer arises; the flip asserts D built in the
  first run on a base with the merge and W, not the line's tip, and no "delete … on origin"
  advice. (The re-run legs would re-publish a COMPLETE D through the fixture's plain push,
  which is not a fast-forward: they cannot run as-is.)
- The unused `_held` helper and the module docstring (it described the hold) were updated.

`test_flow_slice.py` (not on the brief's list):
- `_spy_fold` (now `:1315-1327`) answers `into=` calls without recording them, so the three
  tests asserting the line's fold sequence keep their assertions unchanged.
- `test_a_three_wave_run_folds_append_only_onto_a_real_origin` (now `:1605-1660`):
  `cut_from["issue_EB"] == "origin/<line>"` → `_built_on("EB","EA")`; "fix/EB~1 in the line"
  (it was the first fold's tip) → `tips[0]` (the line's tip after its first fold, recorded by the
  fold wrapper) is in the line; `len(pushes)==2` counts the line's pushes.
- `test_a_dependent_carries_every_earlier_wave_branch_not_only_its_prerequisite` →
  `test_a_dependent_carries_only_its_prerequisite_not_every_earlier_wave_branch` (now
  `:1662-1690`): **this test pinned the #630 behaviour the brief reverses.** ZZ ⊂ fix/ZB →
  ZZ ⊄ fix/ZB; diff `[ZA, ZB, ZZ]` → `[ZA, ZB]`; after ZA merges `[ZB, ZZ]` → `[ZB]`; two merge
  bases `[za, zz]` → one `[za]`, no "Update branch" needed. `_update_from_main` became unused
  and was removed.

`test_flow_reissue_after_conflict_hold.py` (694's test):
- `_stacked_on_10` `:314-315`: `seen["issue_12"][0] == self.line` → `_built_on("12","10")`
  (borrowed from `SameWaveConflict`, `:60`).
- `test_one_the_fold_merges_after_it_is_named_too` `:244-248`: **set-up change, no assertion
  change.** The test needs 21's edit to `shared.txt` to sit "on top of 10's"; before, that
  happened only because 21 (`Depends on: 12`) was cut from the line holding 10. Under the
  Invariant it is built on 12 alone, so its edit conflicts with 10's and the carry skips it.
  21 now declares the edge it relies on (`Depends on: 12, 10`, via a new `twenty_one_on`
  parameter of `_held_for_10`, `:151-158`).

`test_integrate_carried_rewrite_late.py` (695's test):
- `test_a_rewrite_during_the_last_fold_is_reported_and_exits_1` `:258-276` and
  `test_an_end_of_run_check_that_cannot_fetch_is_named_and_exits_1` `:280-309`: **fault
  injection moved, assertions unchanged.** Both target "the run's last fold"; with this change
  that is B's base build, which runs after the line's fold after wave 0. Injected at the line's
  push (the old timing), the rewrite is now caught by B's base fold (#633 applies to bases, as
  the brief requires) and the run stops — a different path, now pinned in the new file
  (`test_a_carried_branch_rewritten_before_a_dependents_base_is_built_stops_the_run`). The spies
  now inject at the base's push (`args[-1] != line`) and keep `pushed` = the line's pushes.
  Side effect: on the C4 red leg these two fail (no base fold exists to inject into) — they
  are coupled to the new fold schedule by construction.

`test_flow_conflict_partner_hold.py` `:151-156`: the control case stubs `_fold_lines` because
its temp dir has no git checkout; 702 (`Conflicts with: 701`, earlier wave) now gets a base,
which needs one. `flow._bundle_bases` is stubbed the same way (`create=True`, so the test still
loads and runs with the fix reverted).

## The new test file — `template/tests/test_flow_dependency_scoped_bases.py`

| criterion | test (line) |
|---|---|
| (1) #630: B carries every commit of fix/A, none of fix/Z (two-commit branches); B's recorded base is a branch on origin with A's tip and not Z's; it is the base B was built on and its PR branch's cut | `test_a_dependent_carries_its_prerequisite_and_nothing_of_an_unrelated_bundle` (`:224`) |
| (2) transitive: fix/C ⊇ fix/A, fix/B; ∌ fix/Z | `test_the_base_carries_every_prerequisite_reached_through_another` (`:250`) |
| (3) `Conflicts with` partner, later wave by name order | `test_an_earlier_wave_conflicts_with_partner_is_on_the_base` (`:267`) |
| (4) H → N (close, no patch): stack base cleared, fix/H ∌ A, Z | `test_a_bundle_whose_only_prerequisite_has_no_patch_is_built_on_the_real_base` (`:282`) |
| (6) carried P, X: D ∋ P ∌ X, E ∋ X ∌ P, both COMPLETE — on the resume fixture (`_finished`, `_planned`, `_run`) loaded by path | `test_a_carried_finished_prerequisite_is_on_its_dependents_base_alone` (`:318`) |
| (7) | the flipped `test_a_merge_after_the_line_was_started_builds_a_plain_depends_on_dependent` (`test_flow_merged_prereq_on_line.py:213`) |
| deviation 1 | `test_an_in_batch_depends_on_merged_prerequisite_is_on_the_base` (`:303`) |
| #633 on bases | `test_a_carried_branch_rewritten_before_a_dependents_base_is_built_stops_the_run` (`:338`) |
| push rule (plain on create, leased force on rebuild, refusal names the branch + remedy, line untouched) | `test_a_bundle_base_is_pushed_plain_when_new_and_forced_only_to_rebuild_it` (`:365`) |
| name scoping / injectivity | `test_a_bundle_base_name_is_scoped_to_the_batch_and_injective` (`:400`) |

Only modules are imported. The two tests that touch new API guard it with assertions first
(`inspect.signature(integrate.fold)` has `into`; `hasattr(integrate, "bundle_base")`), so with
the fix reverted they fail on an assertion, not a `TypeError`/`AttributeError`.

## Refuting my own test (forced)

- **(a) Genuine red? Yes.** `engine/scripts/run-verify.sh` (the project's C4 runner) on the
  final patch: green leg all 9 touched modules OK; red leg (production hunks reverted, tests
  kept): `test_flow_dependency_scoped_bases` **9/9 FAIL** (all `FAIL:`, none `ERROR:`, no
  `_FailedTest`), plus 6 in `test_flow_merged_prereq_on_line`, 4 in `test_flow_same_wave_conflict`,
  2 in `test_flow_slice`, 2 in `test_integrate_carried_rewrite_late`, 1 in
  `test_flow_resume_stack_prereqs`. Verdict line: `PDCA-EVIDENCE: C4 PASS — red without the
  fix, green with it`. The worktree was byte-identical to `patch.diff` afterwards.
  Read from a red run of three of them: (1) fails at `:236`, `_none_of("fix/B", "Z")`, listing
  both of Z's commits on fix/B; (4) fails at `:295`, H's recorded base is the run's line
  `pdca-integration/main-r…` instead of empty; (6) fails at `:333`, D's base holds fix/X.
- **(b) Production path? Yes.** Every case drives the real `flow._drive_and_act` →
  `_runnable` → `_bundle_bases` → real `integrate.fold` (real git merges, real pushes to a bare
  origin, real `integ_lock`/worktree) → `publish.write_stack_base`; only the build/sign-off
  leaves, `_publish_bundle` (a real cut/commit/push from the recorded tip) and `gh` are stubbed,
  exactly as the brief's peer (`test_flow_same_wave_conflict.py:53-163`) does. The push-rule
  test calls the production `integrate.fold` directly.
- **(c) Fixture includes the fault? Yes.** The unrelated bundle Z is in the batch, in the same
  wave as A, with two commits, published and folded onto the run's line (asserted: both A and
  Z are on the line at the end). The close-disposition N really is accepted with no patch. The
  carried P and X are both really carried (asserted from the carry's own stderr line). The
  rewrite case really force-pushes fix/A after the line's fold carried it.

## What I ran (all through the project's runners, with timeouts)

- `engine/scripts/run-verify.sh` (C4) — PASS, twice (provisional and final patch).
- `engine/scripts/run-suite.sh` (T3) — root suite **24 OK**; driver suite **2535 OK** (2526 +
  9 new; 2 skipped, as before).
- `engine/scripts/run-docs-check.sh` (T2) — lint clean, render + link audit clean.
- The target has no formatter or commit hook (no `.pre-commit-config.yaml`, no
  `core.hooksPath`, no linter config; CI runs only the docs check, the render check and the
  suites). No new unused imports (stdlib AST check over every changed `.py`); line lengths do
  not exceed each file's existing maximum. Publish commits with `-s` (DCO).

## Follow-ups (not in this slice)

- Other docs that still state the old rule (outside the brief's list): `docs/05-check.md:814`,
  `template/PCDA/quality-cycle/08-glossary.md:287-293` (vendored, human-only),
  `template/agents/planner.md.jinja:43`, `template/pdca.toml.jinja:116` (the brief says no
  template change, so the rendered config comment is left), `template/docs/fork-discipline.md.jinja`.
- `merged.merge_and_head` (`merged.py:149-169`) has no caller now.
- Open question 1 of the brief: per-bundle bases are left on origin (`pdca-integration/*-d<id>`);
  a `pdca sweep`/`cleanup` rule for them is a follow-up.
- `_line_tip_refusal`'s hint (`publish.py:735-739`) still says "a re-issued run continues the
  line only when it carries a finished prerequisite"; for a bundle base the re-issued run
  rebuilds it. The refusal itself is right (the tip is checked against the recorded branch).

## Process note

I wrote a scratch log to `/tmp/pdca463-suite.log` twice while running the suite, outside the
roots the harness gives me. It holds only unittest output. Per the rules I did not delete it;
later runs piped output instead.
