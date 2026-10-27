# Build notes — issue 412 / merge-mode-atomic-merge-group

Target: `eduralph/pdca-harness @ main`, worktree base `a6af7f3`. Every `path:line` below is
on the patched tree unless it says "base".

## What the change does

A brief can now declare `- **Merges with:** <id>[, <id>…]`. In `wave_mode = "merge"`:

1. **Field.** `brief.merges_with` (`template/src/pdca_harness/brief.py:227`) parses it the way
   `conflicts_with` does (base `brief.py:218`, ids via `_id_list`, base `brief.py:347`).
2. **Groups.** `waves._merges_with` (`waves.py:174`) reads the relation symmetrically, as
   `conflict_map` reads `Conflicts with` (base `waves.py:136`), and returns connected sets.
   `waves.merge_groups` (`waves.py:206`) maps each in-batch bundle to the other in-batch
   members of its group.
3. **Up-front refusal.** `waves.merge_group_refusals` (`waves.py:241`) finds the three shapes
   the brief names; `check_dep_graph` raises the first as `DependencyGraphError` only when
   `cfg.wave_mode == "merge"` (`waves.py:147-151`), after the cycle check. `cli._flow`
   already turns that into rc 2 with the `Ways out:` line (base `cli.py:673-679`); no CLI
   change was needed for it. The remedy always names "make … one bundle" and
   `wave_mode = "stack"`; the out-of-batch case also offers "add <id> to this run's ids".
4. **Hold and release.** `merge.merge_wave` (`merge.py:125`) takes `groups` and the run's
   `held` set. A COMPLETE member with a patch, whose group has a member not COMPLETE, is not
   passed to `_merge_one` (so no `gh pr ready`, no `gh pr merge`), and one stderr line names
   what it waits for — printed only the first time (`merge.py:151`). Released members merge
   back to back (`_back_to_back`, `merge.py:182`) in the order the caller gives (earlier
   waves first, then name). A member leaves `held` only once its own `_merge_one` returns 0.
   A failure after another member of the same group merged prints a "landed only in part"
   line naming both sides (`merge.py:165-176`), then returns the STOP rc as before.
   `groups=None` keeps the old loop exactly (all of `tests/test_merge.py` still passes).
5. **Run-scoped carry.** `flow._drive_and_act` keeps `held_group` (`flow.py:2942`), separate
   from `_runnable`'s `held` (#593) as the brief asks. At each merge-mode boundary the members
   held earlier are put back in front of the wave's `complete` list (`flow.py:3113-3116`).
6. **Dependents held.** `_runnable` gets `group_held` (`flow.py:691`); an in-batch
   prerequisite in it is not ready (`flow.py:801-803`), and the dependent gets its own stderr
   line naming the group (`flow.py:900-905`), not the #593 "pushed no branch" wording.
7. **End of run.** `_report_group_holds` (`flow.py:3219`) names each still-held member: either
   "can no longer land together" (a member is DISCONTINUED / never built / run stopped) or
   "all COMPLETE but no boundary merged it" (last member in the final wave). Each held member
   is added to `holds` as `"group"` (`flow.py:3214`) so `cli._results_rc` exits 3 when every
   bundle finished — the same treatment #693 gives a COMPLETE-but-held bundle.
8. **Template + docs.** `template/templates/brief.md.tpl:34` (next to `Conflicts with`),
   `docs/03-plan.md:97` and `:164`, `docs/07-crosscutting.md:888-916`. `cli._results_rc`'s
   docstring mentions the `"group"` reason (`cli.py:725-726`).

Stack mode: nothing reads the field except `check_dep_graph`/`partition_schedulable`, and both
only act when `wave_mode == "merge"`; `merge_wave` is only called in merge mode. So stack mode
is unchanged (leg (e)).

## Choices beyond the literal brief, and why

- **Transitive chain, not only a direct edge.** The brief says "one member `Depends on`
  another". A path through a non-member (B → X → A) deadlocks the same way: X depends on held
  A, so `_runnable` holds X, so B never builds. `_prereq_path` (`waves.py:220`) does a BFS on
  the in-batch dependency graph `check_dep_graph` already built, and the message names the
  bundles in between. Cost: ~20 lines. A direct-edge-only check would accept a batch that can
  never complete.
- **The resume sweep (`pdca flow --from-csv`) holds a refused group instead of crashing.**
  `flow_batch` calls `waves.partition_schedulable` and then `_drive_and_act` →
  `compute_waves` → `check_dep_graph`. The CLI's batch path catches only `PreflightError`
  (base `cli.py:649-655`), so without a mirror in `partition_schedulable` a bad group in
  merge mode would reach the operator as a traceback from the sweep — a crash this change
  would have introduced. `waves.py:478-491` holds every member of a refused group, then
  propagates to dependents, and repeats (a group with a member held for another reason now
  names a bundle outside the survivors, so it is caught next round; each round holds at least
  one more bundle, so it ends). ~15 lines, covered by
  `test_the_sweep_holds_a_refused_group_and_drives_the_rest`.
- **Exit 3 for a group hold.** Without it, a run whose non-final-wave member stays a draft
  exits 0, the same as a run where merge mode merged everything it should. #693 set the
  precedent (a COMPLETE bundle held out of the line → 3).
- **Hold line printed once.** Printing at every boundary repeats the same line for a long
  hold; the end-of-run line gives the final reason (e.g. the partner is now DISCONTINUED).
- **A no-patch member is never held.** It has nothing to merge (`_merge_one` returns 0 for
  it), and holding it would hold its dependents for nothing.
- **Dry run.** The hold still applies with a stub publisher, so a rehearsal shows the same
  holds a real run would make. It asks no host.

## Ruled out

- **Hold logic in `flow`, with `merge_wave` unchanged.** The brief says the member is "skipped
  by `merge_wave`" and that the held set is "passed into a later boundary's `merge_wave`
  call", so the decision sits in `merge_wave`; `flow` only owns the run-scoped set.
- **Changing `merge_wave`'s return type** to hand back the new held set: every existing caller
  and `tests/test_merge.py` read it as an int rc. An optional in/out `held` set keeps them all
  as they are.
- **Also holding a `Conflicts with` partner of a held member** (as #629 does for an unpushed
  bundle). Not in the brief's scope ("Dependents of a held member are held"). It would also
  make the refusal analysis depend on conflict orientation: a chain through a conflict edge
  into a member deadlocks, one through a conflict edge elsewhere does not, so the refusal
  would need `compute_waves`' oriented edge set factored out (base `waves.py:187-212`, ~30
  lines moved into a helper) plus a closure that only counts a conflict edge as the last hop
  (~15 lines), plus ~12 lines in `_runnable` and one in the `conflicts=` condition — roughly
  60 lines and a new over-refusal risk. Left out and documented instead
  (`docs/07-crosscutting.md:913-916`): such a bundle builds on a base without the held
  member, and its merge can stop the run (fail-closed, ready-mark undone) once the group
  lands. The doc tells the author to add a `Depends on` the member if it must wait. Worth a
  follow-up if it bites.
- **Teaching the planner prompt the field** (`template/agents/planner.md.jinja:44-58` lists
  "the two machine-parsed scheduling fields"). `Merges with` is not a scheduling field and the
  brief's file list does not include role prompts; left for a follow-up, along with the
  splitter (the brief already puts `pdca split` out of scope).
- **Treating finished named ids as in-batch for the out-of-batch check.** A member finished in
  an earlier run is not in `bundles`, so `merge_wave` cannot merge it; the brief says to refuse
  that, and the remedy says so.

## Open question carried from the brief (maintainer)

The motivating wyrd pairs are chained; this design refuses them in merge mode (one bundle, or
stack mode). Built as written; alternative A (build the consumer on the producer's unmerged
branch) is not attempted.

## Test — `template/tests/test_merge_group.py` (11 cases)

Imports only modules (`cli, flow, leaves, merge, publish, signoff, state, waves`), never a new
symbol. Fixture shape copied from `test_flow_out_of_batch_prereq_hold.py`: real
`flow._drive_and_act` / real `cli.main` / real `merge.merge_wave` and `_merge_one`; stubbed
are the build leaf (`flow._drive_wave` writes a patch, signs off, writes `publish.json`),
`flow._publish_bundle`, `publish.draft_texts`, and `gh` (a stub in front of
`subprocess.run` that records every call; non-`gh` calls run for real). Publisher mode is
`command`, so this is not a dry run. `merge_requires = "required"` keeps each merge to
`gh pr ready` + `gh pr merge`; the rollup gate is `test_merge.py`'s job.

| Criterion leg | Test |
|---|---|
| (a) | `test_a_group_member_is_held_until_the_group_completes_then_merged_with_it` |
| (b) | `test_a_member_that_ends_discontinued_leaves_the_rest_unmerged` |
| (c) | `test_a_bundle_depending_on_a_held_member_is_not_built` |
| (d) | `test_a_chained_group_is_refused_before_any_do` (via `cli.main`, rc 2, `Ways out:`) |
| (e) | `test_the_chained_group_runs_as_today_in_stack_mode` (via `cli.main`, rc 0) |
| (f) | `test_merges_with_declared_on_one_side_binds_both` |
| (g) | `test_a_group_whose_members_conflict_is_refused_before_any_do`, `test_a_group_naming_an_id_outside_the_batch_is_refused_before_any_do` (via `cli.main`) |
| design: final wave | `test_a_group_whose_last_member_completes_in_the_final_wave_stays_all_draft` |
| design: half landed | `test_a_member_refused_after_another_merged_names_what_landed` |
| sweep path | `test_the_sweep_holds_a_refused_group_and_drives_the_rest` |

### Refuting my own test

- **(a) Genuine red?** Yes. Ran the project's C4 runner (`engine/scripts/run-verify.sh`,
  `PDCA_BUNDLE`/`PDCA_WORKTREE` set), which reverts only the production hunks in place:
  green leg `Ran 11 tests … OK`; red leg `Ran 11 tests … FAILED (failures=10)`, all
  assertion failures, no import error; verdict `PDCA-EVIDENCE: C4 PASS — red without the fix,
  green with it`. Log: `results/issue_412/build-c4-run.log`. The one case green on both legs is
  (e), the stack-mode guard, which is meant to pass without the fix (stack mode must not
  change). Pre-fix the main case fails because A is readied and merged at the wave-0 boundary
  — the exact defect.
- **(b) Production path?** Yes. The cases call the real `flow._drive_and_act`,
  `flow.flow_batch`, `cli.main`, `waves.compute_waves`, and through them the real
  `merge.merge_wave` → `merge._merge_one` → `merged.is_merged`, which shell out to the `gh`
  stub. Nothing in the group logic is mocked; only the model leaves, publish mechanics and the
  host are stubbed.
- **(c) Fixture includes the fault?** Yes. The fixture is the brief's shape: the group split
  across waves by an unrelated `Depends on: D`, a later dependent `C`, a real DISCONTINUED
  sign-off for (b), a real `gh pr merge` refusal for the half-landed case, and the chained /
  conflicting / out-of-batch batches for (d)/(g). Every `gh` call is recorded, not filtered.

## Other checks run

- Full offline driver suite with the patch: `cd template && PYTHONPATH=src python3 -m
  unittest discover -s tests` (under `timeout`) → `Ran 2641 tests … OK (skipped=2)`.
- Docs: `engine/scripts/run-docs-check.sh` → `docs lint clean, site render + link audit clean`.
- T3 (`engine/scripts/run-suite.sh`: root render suite with copier + driver suite):
  root `Ran 24 tests … OK` (copier present, nothing skipped), driver `Ran 2641 tests … OK
  (skipped=2)`, `PDCA-EVIDENCE: root suite OK, driver suite OK`. Log:
  `results/issue_412/build-t3-run.log`. (A docstring-only reflow in `cli.py` landed while the
  render suite was running; C4 was re-run on the final `patch.diff` afterwards — still PASS.)
- Commit-readiness: the target has no formatter or pre-commit config (no
  `.pre-commit-config.yaml`, no ruff/flake8/black config); its CI runs the docs lint/render
  and the render suite, both run above. New Python lines stay within 100 columns; the one
  long line is the template field line, which matches its sibling field lines.

No external dependency beyond what the brief lists (none) was needed.
