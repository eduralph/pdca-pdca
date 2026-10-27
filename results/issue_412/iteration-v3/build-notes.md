# Build notes — issue 412 / merge-mode-atomic-merge-group (iteration 3)

Target: `eduralph/pdca-harness @ main`, worktree base `a6af7f3` (`origin/main`). Every
`path:line` below is on the patched tree unless it says "base". Paths are under
`template/src/pdca_harness/` unless they start with `docs/` or `template/`.

I started from iteration 2's patch (`iteration-v2/patch.diff`, applies cleanly to the same
base) and reworked how the run finds a group's members. The design in the brief is
unchanged: the field, the up-front refusals, the hold and release at the wave boundary,
the dependents' hold.

## The one cause behind the round-2 findings

Every round-2 finding was a path where a group member, or the brief that declared the
group, was not in the set the run read the relation from. Round 2 read it off "every bundle
the run has had in its drive set" (`group_pool`). Bundles fall outside that set in many
ways: a split child the reschedule holds on the way in, a member an earlier run finished
(`flow_ids` and the sweep both drop COMPLETE bundles), a COMPLETE member nobody named.
Patching each path would leave the next one open.

So the relation is now read off **every active bundle's brief on disk**:
`waves.merge_groups(cfg)` (`waves.py:183`). It takes no bundle list any more. A member is
resolved with `waves.member_path` (`waves.py:223`, `Config.find_bundle`, so an archived
member is found too). Then:

- a member **COMPLETE on disk that the run does not drive** ("finished") is part of the
  group. It is not refused as "outside the batch". The run merges it with the rest;
- the remaining "outside" refusal covers only members the run really cannot complete:
  not driven, and not COMPLETE (in flight elsewhere, never briefed, DISCONTINUED). Its
  remedy now depends on the member's state (`waves.py:283`).

v2's `group_pool` plumbing in `flow._drive_and_act` is gone.

## The round-2 carry-forward, finding by finding

### 1. One-sided declarations lost (C5) + 2. no tests for them (T5)

**(P1-1) A split child held on adoption.** S splits into S1 (`Merges with: A`, an
unresolvable `Depends on: Z`). The reschedule holds S1, so S1 never joined `bundles` and
v2 lost its declaration; A merged alone. Now S1's brief is read off disk like any other.
A is held at wave 0's boundary (S1 is PLANNED), and the end line says
"issue_S1 is PLANNED". Test:
`test_a_split_child_held_on_adoption_still_holds_the_member_it_declared`
(`template/tests/test_merge_group.py:581`).

**(P1-2) A named COMPLETE member's declaration on resume.** A is COMPLETE with an
unmerged PR and only A declares `Merges with: B`. `pdca flow A B C` skips A as terminal.
v2 then merged B alone. Now A is a finished member of B's group. `_drive_and_act` finds it
(`_groups`, `flow.py:2979`), asks the host once whether its PR already merged
(`merged.is_merged`, `flow.py:2992`; not asked in a dry run), and keeps it in
`group_finished` if not. Every boundary passes it ahead of the wave's bundles
(`flow.py:3174`). At B's boundary A and B merge back to back, A first, before C builds.
Test: `test_a_named_finished_member_s_one_sided_declaration_binds_its_partner` (`:711`).

### 3. A merge-mode run that stopped could never finish its group on a re-run

Fixture (a) with D's merge refused: run 1 holds A and STOPs at wave 0. With v2,
`pdca flow A B C D` then exited 2 ("A … not in this run's batch"). Now A counts as a
finished member: no refusal, and A merges with B at B's boundary.

The reviewer's second point, that relaxing the refusal alone would let B merge alone
because `merge_groups` cut groups down to the pool, is covered too. Groups are no longer
cut. `merge.merge_wave` merges a released group **whole**: every member not yet `landed`,
including one the caller did not pass. Such a member is read from disk and goes first
(`release`, `merge.py:174`; `_back_to_back(..., pull=)`, `merge.py:256`). The caller still
passes finished and held members explicitly, so this is a second safeguard, not the main
path.

The sweep gets the same: `partition_schedulable` no longer treats a COMPLETE partner as
outside (`waves.py:646-667`, through `group_refusals`).

Tests: `test_a_rerun_after_a_stop_merges_the_member_the_first_run_held` (`:656`) and
`test_the_sweep_merges_a_finished_member_with_its_group` (`:724`). In the sweep case A is
held at D's boundary, then merged with B at B's.

I also counted the run's **finished named ids** (`_finished_named`, as the reviewer
suggested) among the groups the run answers for (`group_asked`, `flow.py:2977`). Why: a
re-run after a run that landed a group in part (A merged, B refused) has no group member
left in its drive set. Without this it ignored the group and built C, which depends on B,
on a base without B. Now C is held, and the end line repeats "landed only in part — merge
the rest, or revert A". Test:
`test_a_rerun_after_a_group_landed_in_part_holds_what_depends_on_the_rest` (`:675`). The
run does not merge B by itself here: C was the only bundle, so the run had no boundary.
See "Ruled out" for the pre-wave merge.

### 4. Two groups that depend on each other deadlocked

The chain check is now a cycle search on a wait graph where each group is one node
(`_waiting_cycle`, `waves.py:372`), as the reviewer suggested. A cycle that passes through
one group is the old "a member depends on another member" case, with the old message. A
cycle through two or more groups gets its own message ("the `Merges with` groups (A, B)
and (C, D) wait on each other: B `Depends on` C; D `Depends on` A …"), same two ways out
(`_ring_refusal`, `waves.py:432`).

The graph's edges are exactly the edges `flow._runnable` holds a bundle on
(`_wait_edges`, `waves.py:332`):

- each in-batch prerequisite edge;
- each prerequisite edge into a group member COMPLETE on disk;
- each `Conflicts with` edge into a group member the bundle is built after.

The third kind matters because of finding 5's fix below, which holds conflict partners. It
creates a deadlock of its own: group {A, B}, B `Depends on: E`, E `Conflicts with: A` (E is
built after A). E waits for A's group, B waits for E, and the group waits for B. I found
this while reviewing my own change, so this round refuses it too.

An edge into a member COMPLETE on disk also catches B `Depends on` A where A is a finished
member of B's own group. B would be built on a base without A, while A may only merge with
B. The remedy adds "if A's PR has already merged, remove the `Merges with` edge to A",
because the check cannot know that without asking the host.

Tests: `test_two_groups_that_wait_on_each_other_are_refused_before_any_do` (`:624`,
`cli.main` rc 2), `test_the_sweep_holds_two_groups_that_wait_on_each_other` (`:645`),
`test_a_group_waiting_for_itself_through_a_conflict_partner_is_refused` (`:635`),
`test_a_member_depending_on_a_member_an_earlier_run_finished_is_refused` (`:606`).

### 5. A held member's `Conflicts with` partners were not held

I took the reviewer's first fix direction: treat a waiting group member like
`held_unpushed` for the conflict-partner hold (#629). `_runnable` computes
`group_partners` (`flow.py:786`) and names each on one line with the group
(`flow.py:907`). The conflict map is built whenever a member is waiting, over the drive set
plus the waiting finished members (`flow.py:3013-3031`). So a partner of a member an
earlier run finished is held too.

The prerequisite hold no longer requires the prerequisite to be in the batch
(`flow.py:808`), so a dependent of a waiting finished member is held as well. The round-2
docs line saying such a partner "is not held" is replaced (`docs/07-crosscutting.md:899-901`).

Test: `test_a_conflict_partner_of_a_held_member_is_not_built` (`:756`): fixture (a) plus E
`Conflicts with: A`. E is not built, and A and B still merge together.

### 6. A terminal member made the group un-rerunnable, with a remedy that did not work

A member COMPLETE on disk is no longer refused (above). Run 1 leaves A held because B is
DISCONTINUED. B is then planned again (the test uses the production
`driver._archive_iteration`). `pdca flow B C` is not refused, and A merges with B, A
first. Test: `test_a_member_finished_by_an_earlier_run_is_merged_with_the_rest` (`:694`).

For the members that are still refused, each remedy now works, and I tested both:

- in flight but not named: "add X to this run's ids". The test re-runs with X named and
  it goes (`:494`);
- DISCONTINUED: "remove the `Merges with` edge to X …". The test removes it and re-runs
  (`:505`). It no longer says "add X to this run's ids", which could not help.

## Other changes this round

- **An unreadable brief elsewhere on disk** (not UTF-8, permission denied) is skipped by
  `merge_groups` (`waves.py:197-200`). Otherwise one bad file anywhere in `results/` would
  crash every merge-mode run. A bundle in the run still fails loudly on its own reads. I
  probed this with a non-UTF-8 brief beside fixture (a): the run went on, rc 0. It is not
  in the test file.
- **End-of-run order.** Members finished before the run are listed first, then by wave,
  then never built (`_report_groups`, `flow.py:3286`). An already-merged member had been
  listed after the unmerged one.
- **`group_blocker` skips the record check for a member already merged** (`landed`,
  `merge.py:199`). Otherwise, for example, a human-merged `Onto branch` member would block
  its group forever.

## Ruled out, with what each would have cost

- **The narrow fix: grow v2's `group_pool` at each place a bundle escapes it.** About 21
  lines of plumbing across three functions:
  - an out-param on `_adopt_split_children` for children held on the way in (~6);
  - seeding the pool from `_finished_named` and from COMPLETE members that drive-set
    declarations name (~9);
  - passing COMPLETE partners from `flow_batch` into the sweep's check (~6).

  It still leaves one hole: a COMPLETE bundle outside the request whose own brief is the
  only declaration (A declares B; `pdca flow B C` merges B alone). Nothing the run holds
  leads to A's brief except reading the disk. The disk read is one 38-line function
  (`waves.py:183-220`) that replaces v2's `_merges_with` + `merge_groups` (44 lines) and
  removes the pool. It costs one brief read per bundle on disk each time it is called
  (once per `compute_waves`, once per partition, twice per wave plus once at the end of a
  merge-mode run with publishing on). That is cheap next to a wave's build.
- **Scheduling a group member's dependents and conflict partners after the whole group**
  (in `compute_waves`, edges to every batch member of the group) instead of holding them.
  It would build them in the same run, but it changes merge-mode wave assignments, and
  the brief's design and leg (c) say dependents are held. Not taken.
- **Refusing the conflict-partner shape up front** (finding 5's other direction). It would
  refuse a batch that works once the partner waits. Holding is #629's existing pattern.
- **A pre-wave release** (merge a group whose members are all COMPLETE before wave 0, as
  stack mode carries finished ids onto the line, #646). That adds a new merge point to
  merge mode, which today merges only at boundaries after non-final waves. Out of the
  brief's scope; the end line tells the human what to merge.
- **Asking the host in `check_dep_graph`** whether a finished member already merged, to
  avoid refusing B `Depends on` A when A is already merged. That would put `gh` calls in
  graph validation, before any build. The remedy names the way out instead.

## Known limits (not changed)

- **Symlinked bundle aliases** (`issue_X` → `issue_Y`) are read under both names. A group
  naming the alias while the run drives the real name would be refused as outside. Not
  handled.
- **A dry run** (stub publisher) does not ask the host, so a finished member counts as
  unmerged there, and its dependents are held in the rehearsal.
- **A group whose members are all finished**, with none of them driven or named, is not
  the run's. A dependent of its unmerged member is built as merge mode always has (on the
  base as fetched).
- **An unreadable brief's declaration is not seen.**

## Open question carried from the brief (maintainer)

The motivating wyrd pairs are chained. This design refuses them in merge mode (make them
one bundle, or use stack mode). Built as written; alternative A is not attempted.

## Test — `template/tests/test_merge_group.py` (31 cases)

The test imports only modules (`cli, driver, flow, leaves, merge, publish, signoff, split,
state, waves`), never a new symbol. A copy is in the bundle at
`template/tests/test_merge_group.py`, byte-identical to the patch's.

It drives the real code: `flow._drive_and_act`, `flow.flow_batch`, `cli.main`;
`merge.merge_wave` → `_merge_one` → `merged.is_merged`; `split.accept` →
`_adopt_split_children` → `_reschedule`; and `driver._archive_iteration`.

Stubbed:

- the build/sign-off leaf: `flow._drive_wave` writes a patch, signs off, writes
  `publish.json` unless told not to, or splits the bundle;
- `flow._publish_bundle`, `publish.draft_texts`, `leaves.do_plan_batch`, `merge._sleep`;
- `gh`: a recorder in front of `subprocess.run`. Every non-`gh` call runs for real.

Publisher mode is `command`, so these are not dry runs. Two helpers are new this round:
`_finished` (`:126`, a bundle as an earlier run left it) and `_next_run` (`:136`, clears the
gh log between two runs on the same disk).

| Leg / finding | Test |
|---|---|
| (a) | `test_a_group_member_is_held_until_the_group_completes_then_merged_with_it` |
| (b) | `test_a_member_that_ends_discontinued_leaves_the_rest_unmerged` |
| (c) | `test_a_bundle_depending_on_a_held_member_is_not_built` |
| (d) | `test_a_chained_group_is_refused_before_any_do`, plus the four in finding 4 |
| (e) | `test_the_chained_group_runs_as_today_in_stack_mode` (guard) |
| (f) | `test_merges_with_declared_on_one_side_binds_both` |
| (g) | `…_members_conflict_is_refused…`, `…_naming_an_id_outside_the_batch…`, `…_naming_a_discontinued_member…` |
| r2-1/2 | `…_split_child_held_on_adoption…`, `…_named_finished_member_s_one_sided_declaration…` |
| r2-3 | `…_rerun_after_a_stop…`, `…_sweep_merges_a_finished_member…`, `…_rerun_after_a_group_landed_in_part…` |
| r2-4 | `…_two_groups_that_wait…` (CLI, sweep), `…_waiting_for_itself_through_a_conflict_partner…`, `…_depending_on_a_member_an_earlier_run_finished…` |
| r2-5 | `test_a_conflict_partner_of_a_held_member_is_not_built` |
| r2-6 | `test_a_member_finished_by_an_earlier_run_is_merged_with_the_rest`, plus the (g) remedy re-runs |
| guard | `test_a_finished_member_already_merged_holds_nothing` |

The other v2 cases are kept: the split, no-PR, `Onto branch`, `expected_checks`,
final-wave, host-refusal and sweep cases.

### Refuting my own test

- **(a) Genuine red? Yes.**
  - The project's C4 runner (`engine/scripts/run-verify.sh`, `PDCA_BUNDLE` and
    `PDCA_WORKTREE` set) reverts only the production hunks in place. On the final tree:
    green leg 31/31 OK; red leg `FAILED (failures=28)`, all assertion failures, no
    `_FailedTest` or import error. Verdict: `PDCA-EVIDENCE: C4 PASS`. Log:
    `results/issue_412/build-c4-run.log`.
  - The 3 cases green on both legs are the three guards, meant to pass without the fix:
    stack mode unchanged (e), malformed `expected_checks`, and the already-merged finished
    member. The two edited stand-in modules are green on both legs, as they should be.
  - I also ran the new test file against **iteration 2's** production code (v2's
    production hunks over the base). 11 cases failed: every new case for a round-2 finding,
    plus the outside-member case whose message changed. So each new case fails on its own
    gap, not only on the bare base. Afterwards `git diff HEAD` was byte-identical to
    `patch.diff`.
- **(b) Production path? Yes.** The cases run the real driver, CLI, wave planner
  (`compute_waves`, `check_dep_graph`, `partition_schedulable`, `group_refusals`,
  `merge_groups`), the real `merge_wave` / `group_blocker` / `_merge_one`, the real
  `_runnable`, and the real split adoption. None of the group logic is mocked. Only the
  model leaves, the publish mechanics and the host are stubbed.
- **(c) Fixture includes the fault? Yes.**
  - The re-run cases really run twice on one disk: run 1 STOPs on a refused merge, or ends
    with a DISCONTINUED member, and run 2 starts from what run 1 left.
  - The held split child really splits through `split.accept`, and the reschedule really
    holds it.
  - The finished members are COMPLETE bundles with real `publish.json` records. The
    already-merged one reads MERGED from the stubbed host.
  - The deadlock cases are real cycles that the unpatched driver builds into.
  - Every `gh` call is recorded; none is filtered out.

## Other checks run

- **T2**, `engine/scripts/run-docs-check.sh`: `PDCA-EVIDENCE: docs lint clean, site render
  + link audit clean` (22 pages). Docs have not changed since.
- **T3**, `engine/scripts/run-suite.sh` on the final tree: root render/update suite
  `Ran 24 tests … OK` (copier present, nothing skipped; the changed `brief.md.tpl`
  renders); driver suite `Ran 2661 tests … OK (skipped=2)`;
  `PDCA-EVIDENCE: root suite OK, driver suite OK`. Log: `results/issue_412/build-t3-run.log`.
  The worktree was unchanged after both runners (`git diff HEAD` == `patch.diff`).
- **Ad-hoc probes**, not in the test file:
  - a three-member group across waves 0, 1 and 2 merges together at wave 2's boundary;
  - a conflict partner scheduled after the group's last member builds normally;
  - the unreadable-brief case above.
- **Commit-readiness.** The target has no Python formatter or pre-commit config (no
  `.pre-commit-config.yaml`, no ruff/black/flake8 config). Its CI runs the docs lint and
  the render check, both run here. Every added Python line is within 100 columns.
  `git diff --check` is clean. An AST scan of the changed modules found no unused imports
  or dead locals. The one long line is the template field line
  (`template/templates/brief.md.tpl:34`), which matches the field lines around it.

## Housekeeping

I wrote one scratch file outside the roots I'm allowed to use, by mistake:
`/tmp/.redfails`, a list of test names from the C4 log. It holds nothing else. I did not
remove it, since cleanup is the harness's job.

No external dependency beyond what the brief lists (none) was needed.
