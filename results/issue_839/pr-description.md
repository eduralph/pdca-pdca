## Summary
**User impact:** In merge mode, when you run `pdca flow` on a bundle whose prerequisite was finished and published by an earlier run but whose PR has not merged yet, the run gets it wrong both ways. With a plain `Depends on` (or with the prerequisite named in the same command), it builds the dependent on a base that does not contain the prerequisite's change, so you get a PR built against the wrong code and only notice when you read it. With `Depends on (merged)`, it holds the dependent forever: nothing ever merges the prerequisite, and the hold message tells you to do something that only works in stack mode. Either way, a multi-bundle chain stalls or ships a PR on the wrong base.

This PR makes a merge-mode run merge, before it builds anything, the prerequisite PRs that an earlier merge-mode run opened as a non-final wave — through the same gates it already uses between waves — and hold the dependent, with the reason and a way out, for anything else that is still unmerged.

Reported in [#839](https://github.com/eduralph/pdca-harness/issues/839) (a child of the chain incident in #547).

## What to look at
The change has three parts a reviewer can read in order:

1. **The mark.** When a merge-mode run merges a non-final wave, it now writes `"merge_eligible": true` into each attempted PR's `publish.json`, plus a hash of the `patch.diff` that PR was published from. The mark means "a later merge-mode run may ready and merge this PR unattended once its gates pass, as long as the bundle still holds that patch." A PR waiting for a human (final wave, single bundle) never gets the mark. Writer: `merge_wave` → `_merge_one(mark=True)` in `template/src/pdca_harness/merge.py`.
2. **The pre-wave merge.** Before wave 0, a merge-mode run walks down from each bundle it drives, along its dependency edges, and merges marked, open PRs that target the dependent's base — deepest first, each through the full `_merge_one` gate sequence. It claims each prerequisite before reading it, so two runs cannot both touch one PR. New function `_merge_prereqs` in `template/src/pdca_harness/flow.py`, called from `_drive_and_act` next to the existing stack-mode pre-wave step.
3. **The hold.** The readiness check (`_runnable`) now holds a merge-mode dependent on any unmerged prerequisite, named or not, plain edge or `(merged)` edge, and prints a merge-mode way out instead of the stack-mode "name it in the same command" advice. The advice depends on what the record actually allows (`_merge_way_out`): merge by hand, reopen, fix `pdca.toml`, re-publish, or land the work and drop the edge.

**To try it** (offline, no GitHub needed): run the new test module —
`cd template && PYTHONPATH=src python3 -m unittest tests.test_merge_resume_stranded_prereq`. It drives real `pdca flow` runs over a real-git fixture with `gh` stubbed, and checks that the dependent's worktree base actually contains the prerequisite's commit after the merge, and that it is not built when it should hold.

Behaviour changes worth knowing about:
- The #647 merge-mode exemption from the unmerged-prerequisite hold is reversed on purpose. `test_merge_mode_holds_nothing` pinned the old behaviour and is rewritten to pin the new one.
- The merge rule widens from "only PRs this run opened" to "PRs a merge-mode run opened as a non-final wave (marked)". Unmarked PRs, including every PR published before this change, are never readied or merged by the driver; the hold line tells you to merge them by hand.
- A refusal by the merge gates before wave 0 holds only the dependents and the run goes on; the same refusal at a wave boundary still stops the run, with its existing text unchanged.

## Root cause
`hold_unmerged` was explicitly switched off in merge mode (`template/src/pdca_harness/flow.py:3039-3040` on `main`), and the same flag also controlled per-bundle stack bases (`own_bases = hold_unmerged`, `flow.py:3043`), so the hold could not simply be turned on. In `_runnable` (`flow.py:681`) a prerequisite named in the command was never a hold candidate, and the merge-mode pre-wave carry (`_carry_finished`, `flow.py:1552`, called at `flow.py:3027`) is skipped in merge mode, so `pdca flow P D` with P already COMPLETE built D without P. For the `(merged)` edge the hold worked, but no code path merged an out-of-run PR — `_merge_one` refused anything but "the PRs this run opened" (`merge.py:756`) — and the hold text (`flow.py:867`) was stack-mode advice.

## Fix
- `flow.py`: `hold_unmerged` is on whenever publishing is on and it is not a dry run; `own_bases` is split off and stays stack-only. New `_merge_prereqs` runs once before wave 0 in merge mode: walks each drive-set bundle's `Depends on` / `Depends on (merged)` edges, takes a prerequisite only if it is COMPLETE, has a readable non-empty patch, carries the mark for that exact patch, has a PR on record for the dependent's repo, targets the dependent's base, and reads OPEN; merges taken prerequisites deepest-first via `merge._merge_one`, but only when their own prerequisites are all merged into that base. Returns per-prerequisite notes for the hold line. `_runnable` gains `merge_notes` / `merge_busy`: in merge mode every unmerged prerequisite holds, the hold line is merge-mode text, and a prerequisite another live run holds is held on its own line with no `gh` read. New `_own_target` and `_merge_way_out` read the record and brief to give advice that `merged.merged_into` will honour. The dependent is released only through `merged_into` (record says merged into the dependent's base), never on the merge's return code.
- `merge.py`: `merge_wave` passes `mark=` for each PR this run pushed; `_merge_one` writes `merge_eligible` + `merge_eligible_patch` atomically before the first `gh pr ready`, so a PR refused later in the sequence is still marked. All refusal messages go through `_next(held, wave_text, todo)`: unchanged at a wave boundary, "<dependent> is held; <what clears it>" before wave 0 — including distinct advice for a malformed `expected_checks` (fix `pdca.toml`, not the PR).
- `merged.py`: `has_patch` (True / False / None-unreadable), `patch_hash`, `marked_for_this_patch`; `merged_into` uses `has_patch` so an unreadable patch no longer raises.
- `drive_claim.py`: `Run.holds(d)` so the walk releases only claims it took, not the run's own drive-set claims (an alias shares its bundle's claim, so name matching would be wrong).
- Tests: new `template/tests/test_merge_resume_stranded_prereq.py` (128 tests); `test_merge_mode_holds_nothing` rewritten as `test_merge_mode_holds_a_dependent_of_an_unmerged_prereq`; one assertion in `test_merge_review_remarks.py` narrowed to the remarks file because `publish.json` is now written the same way.
- Docs: `docs/07-crosscutting.md` merge-mode bullet and claim paragraph, `docs/11-troubleshooting.md`, `template/docs/fork-discipline.md.jinja`, `template/pdca.toml.jinja` merge-mode comment.

## Verification
All line references are on `main` at `b72698d8b2bcae97da54f21d5bd181970cd9e4ec`; the patch applies cleanly there.

- **Claim:** an out-of-run COMPLETE, unmerged plain-`Depends on` prerequisite with no mark holds the dependent in merge mode; the hold line names the prerequisite and the base and gives merge-mode advice; the dependent is not built; `gh` is asked only for the PR's state.
  **Checked:** `template/src/pdca_harness/flow.py:3039-3043` — the exemption and the shared `own_bases` flag this splits. `flow.py:867` — the stack-mode hold text this path no longer prints.
  **Test:** `test_flow_out_of_batch_prereq_hold.py::test_merge_mode_holds_a_dependent_of_an_unmerged_prereq` (replaces `test_merge_mode_holds_nothing`, `template/tests/test_flow_out_of_batch_prereq_hold.py:350`); `test_merge_resume_stranded_prereq.py::test_1_*`, `test_1b_*` (named prerequisite), `test_1c_*` (no stack bases built in merge mode). Red pre-fix: D appears in the built set. Green post-fix.
- **Claim:** a marked, open prerequisite whose gates pass is readied and merged before wave 0, and the dependent then builds on a base containing it — for both edge kinds; release goes through `merged_into`, so a marked PR merged into another base still holds.
  **Checked:** `template/src/pdca_harness/merge.py:731` (`_merge_one`), `merge.py:756` ("only the PRs this run opened" — the rule this widens), `merge.py:809` ("the final wave never reaches here" — still true for unmarked PRs); `template/src/pdca_harness/merged.py:76` (`merged_into`), `merged.py:121` (`counts_into`).
  **Test:** `test_2_*` — asserts `gh pr ready` + `gh pr merge` were called for P before wave 0, `origin/main` in the fixture contains P's commit, and D's worktree base contains it; `test_2b_*` holds on a record for another base and on a return code of 0 alone.
- **Claim:** a refusal before wave 0 holds only the dependents, says who is held, never prints "STOP: later waves are NOT run", and the rest of the run builds and publishes; wave-boundary refusals keep today's text byte for byte.
  **Checked:** `merge.py:496` (`_refuse`) and each refusal site in `_merge_one` (`merge.py:731-`).
  **Test:** `test_3_*`, `test_refusals_say_who_is_held_and_what_clears_it_before_wave_0`, `test_refusals_keep_the_wave_text_at_the_wave_boundary`, `test_merge_wave_marks_before_the_ready_mark_and_a_refusal_still_stops`.
- **Claim:** an unmarked PR is never readied or merged; a marked PR with unmerged prerequisites of its own is not merged and the dependent's line names both; a PR returned to draft after a refusal is merged by the next run; a closed PR is left alone; a marked PR whose bundle was rebuilt (patch hash differs) is not merged.
  **Test:** `test_3b_*`, `test_3c_*`, `test_3d_*`, `test_a_closed_marked_pr_*`, `test_a_rebuild_accepted_with_no_publish_holds_its_dependent`, `test_an_unmarked_prereq_costs_the_walk_no_gh_read`.
- **Claim:** two runs never ready or merge one PR together; a prerequisite another live run holds is not read and holds its dependents, naming that run's pid.
  **Checked:** `template/src/pdca_harness/drive_claim.py` (the claim scope from `fe8208f098556c8c3955aedec0c9f56cae2441dd`).
  **Test:** `test_a_prereq_another_run_holds_is_not_touched_and_holds_its_dependent`, `test_another_process_holding_a_prereq_is_named_with_its_pid` (a real second process), `test_two_runs_reaching_one_marked_pr_never_both_touch_it` (a second run starts during the first run's `gh pr ready`), `test_the_walk_never_lets_go_of_what_the_run_drives`.
- **Claim:** a close/no-fix prerequisite releases its dependent with no `gh` call; dry runs and `--no-publish` merge nothing, hold nothing, call `gh` never.
  **Checked:** `template/tests/test_flow_out_of_batch_prereq_hold.py:343` and `:358` — the two existing tests, unchanged and still green.
  **Test:** `test_4_*`, `test_5_*`.
- **Claim:** a prerequisite with no `brief.md`, a brief with no target, or an unreadable `patch.diff` holds only that dependent instead of crashing the run or building without it.
  **Test:** `test_a_prereq_with_no_brief_*`, `test_a_prereq_with_no_target_*`, `test_a_prereq_whose_patch_cannot_be_read_*`.
- **Red/green:** with the production hunks reverted, `test_flow_out_of_batch_prereq_hold` fails 1 and `test_merge_resume_stranded_prereq` fails on 109 of 128 tests (behaviour assertions: the dependent built, or no merge attempted); with the patch, all three touched modules pass (31 + 128 + 30). An independent reviewer reproduced the red leg by stashing the four production files: D builds without P.
- **Suite:** full offline driver suite 2945 tests OK (2 skipped); root render/update-compat suite 50 OK; docs lint, site render and link audit clean; `git diff --check` clean.
- **Not exercised:** a live GitHub host. `gh` is a recording stub in every test; the merge on `origin` is a real git merge in the fixture. Real authorization and check-rollup timing are unchanged code paths from the wave-boundary merge.

Known limits, filed separately: a refusal in `merge_wave` returns on the first failed PR, so the rest of that wave's PRs stay unmarked and will need a manual merge (#879); the mark is tied to the local `patch.diff`, not to the PR's head commit, so commits pushed to the PR branch after the mark are judged only by the gates at merge time (#880).

Fixes #839
