## Summary
**User impact:** In merge mode, a chain of dependent bundles stalls or builds on the wrong base when an earlier run finished and published a prerequisite but its PR is still open. On a plain `Depends on` edge, or when the prerequisite is named in the same `pdca flow` command, the dependent is built without the prerequisite's change, so its PR carries a patch that was never tested against the work it depends on. On a `Depends on (merged)` edge the dependent is held, but nothing ever merges the prerequisite, so the chain is dead until someone merges by hand, and the hold message tells you to do something ("name it in the same command so the line carries it") that only works in stack mode.

This PR makes a merge-mode run merge, before wave 0, the prerequisites the run's bundles are waiting for, through the same gates a wave merge uses, and hold the dependent, with a reason and a way out, on anything it may not merge.

Reported in [#839](https://github.com/eduralph/pdca-harness/issues/839) (child of #547, from the five-bundle chain in getwyrd/wyrd#793).

## What to look at
The crux is a small marker and a pre-wave step:

- A PR that a merge-mode run pushed and tried to merge as a non-final wave gets `"merge_eligible": true` in the bundle's `publish.json`, with a hash of the `patch.diff` it was published from. That mark is the only licence for a later unattended ready + merge. Publish never writes it, so a re-publish clears it. A final-wave or single-bundle PR is never marked and stays yours to merge.
- Before wave 0, a publishing merge-mode run walks down from each dependent and merges the marked, open PRs on its base, deepest first. Everything else that is unmerged holds the dependent and the run goes on with the rest.

To try it: with `wave_mode = "merge"`, finish a bundle P in a non-final wave of one run so it is marked but refused (say, a red rollup), then run `pdca flow D` where D depends on P. Before wave 0 you see `flow: before wave 0, merging issue_P: it is marked and unmerged, and issue_D waits for it.` and the `gh pr ready` / `gh pr merge` calls; D then builds on the merged base. With P unmarked (or closed, or published for another patch), D is held and one line names P, D's base and the way out, for example `merge the PR by hand, then re-run`.

## Root cause
`hold_unmerged` was switched off in merge mode (`template/src/pdca_harness/flow.py:2901-2902`), so `_runnable` (`flow.py:786-841`) never held a plain-edge dependent there, and a named id was never a hold candidate (`flow.py:795-797`). For a `(merged)` edge the hold fired, but no code path merges an out-of-batch PR: `merge_wave` runs only at a wave boundary over this run's PRs (`merge.py:756-757`, `:808-810`), and the hold text was stack mode's (`flow.py:836-841`).

## Fix
- **`merge.py`** — `merge_wave` takes `pushed` (the bundles whose branch this run pushed) and `_merge_one` takes `mark`: before its first `gh pr ready`, it writes `merge_eligible` and `merge_eligible_patch` (sha256 of `patch.diff`) into the record, in one atomic replace; a record already marked keeps its hash. A bundle whose publish failed before its push is not marked, since its PR still holds the older head. Every refusal's trailing text goes through a new `_next(held, wave_text, todo)`: at a wave boundary it is byte for byte today's "STOP: later waves are NOT run …"; before wave 0 it says `<dependent> is held; <what clears it>`, and a refusal that is not the PR's problem (a malformed `expected_checks`, a failed fetch) says so rather than "resolve at the PR".
- **`merged.py`** — `has_patch` (does the bundle ship anything, and can the patch be read), `patch_hash`, `marked_for_this_patch`, and the `MARKED_PATCH` key. `merged_into` uses `has_patch` so an unreadable patch is judged by the record, not treated as a close/no-fix.
- **`flow.py`** — `_merge_prereqs`, the pre-wave step (the merge-mode analogue of `_carry_finished`): walks from each drive-set bundle's `Depends on` / `Depends on (merged)` edges, takes a COMPLETE prerequisite only when its record is marked for the patch it holds now, its PR is on record for the dependent's repo, its own brief targets the dependent's base, and the PR reads OPEN; it does not go past a prerequisite already merged, a closed PR, or anything it may not merge. Each taken prerequisite is merged when its own declared prerequisites are each `merged_into` the base, else the dependent's hold line names both. A refusal or an internal error becomes a note for that dependent's hold line. `_merge_way_out` reads the record and the brief to give advice that `merged_into` can act on (an `Onto branch` record or a PR for another base can never count, so the way out is to land the work and drop the edge). `_runnable` gets `merge_notes`: in merge mode every plain-edge prerequisite waits, asked for or not, and the hold line is merge mode's. `hold_unmerged` is on in merge mode; `own_bases` is split off it and stays stack-only.
- **Docs** — `docs/07-crosscutting.md` merge-mode bullet (the merge rule widens from "this run's PRs" to marked PRs; the marker's meaning and lifetime; every hold case and its way out), `docs/11-troubleshooting.md`, `template/docs/fork-discipline.md.jinja`, `template/pdca.toml.jinja`.

Dry runs and `--no-publish` are unchanged: no merge, no hold, no `gh` call.

## Verification
- **Claim:** an unmarked, unmerged, COMPLETE prerequisite holds its dependent in merge mode, on a plain edge and when named in the command; `gh` is asked only for its state.
  **Checked:** `flow.py:2901-2905` (the exemption) and `:786-841` (the hold) on `main`.
  **Test:** `test_merge_resume_stranded_prereq.py::test_1_*`, `::test_1b_*`; the rewritten `test_flow_out_of_batch_prereq_hold.py::test_merge_mode_holds_a_dependent_of_an_unmerged_prereq` (was `test_merge_mode_holds_nothing`, `main:350-356`, pinning the behaviour this PR reverses).
- **Claim:** merge mode builds no per-bundle base (`_base_plans` / `_bundle_bases` stay stack-only).
  **Test:** `::test_1c_*` (two cases).
- **Claim:** a marked prerequisite that passes the gates is readied and merged before wave 0, and the dependent builds on the merged base; release goes through `merged.merged_into` (`merged.py:72`), never a return code.
  **Test:** `::test_2_*` (plain, `(merged)`, named, chain, retargeted), `::test_2b_*` (a merge into another base, or one only queued, does not release).
- **Claim:** a refusal holds only the dependent; the run continues; no "STOP: later waves are NOT run" is printed; the wave-boundary text is unchanged.
  **Checked:** every STOP message in `merge.py:731-940` on `main`.
  **Test:** `::test_3_*`, `::test_refusals_say_who_is_held_and_what_clears_it_before_wave_0`, `::test_refusals_keep_the_wave_text_at_the_wave_boundary`, `::test_an_internal_error_is_not_blamed_on_the_pr`, `::test_a_malformed_setting_is_not_blamed_on_the_pr`.
- **Claim:** an unmarked draft PR gets no `gh pr ready` / `gh pr merge` (final-wave PRs stay the human's, `merge.py:808-810`); a marked PR with an unmerged prerequisite is not merged and the hold names both; a refused PR returned to draft is merged by the next run.
  **Test:** `::test_3b_*`, `::test_3c_*`, `::test_3d_*`, `::test_the_final_wave_is_not_marked`, `::test_merge_one_alone_does_not_mark`.
- **Claim:** the marker is tied to the patch its PR was published from: a rebuilt bundle that never re-published (publish failed before its push, or `--no-publish`) holds its dependent instead of merging the old head; the wave boundary does not mark a PR whose re-publish failed.
  **Test:** `::test_a_marked_pr_published_for_another_patch_is_not_merged`, `::test_a_rebuild_*`, `::test_a_wave_does_not_mark_a_pr_whose_re_publish_failed`, `::test_the_marker_a_wave_wrote_licenses_*`. These go through the real iterate and the real `publish.publish`, including a real `git apply` failure.
- **Claim:** a prerequisite with no brief, a brief with no target, a patch that cannot be read, a closed PR, or a record for another base/repo holds only its dependent, with a way out that works.
  **Test:** `::test_a_prereq_with_no_brief_*`, `::test_a_prereq_with_no_target_*`, `::test_a_prereq_whose_patch_cannot_be_read_*`, `::test_a_closed_*`, `::test_an_onto_branch_record_*`, `::test_a_pr_merged_into_another_base_*`.
- **Claim:** a close/no-fix prerequisite releases with no `gh` call (`merged.py:95`); dry run and `--no-publish` merge nothing, hold nothing, call `gh` nothing.
  **Test:** `::test_4_*`, `::test_5_*`; `test_flow_out_of_batch_prereq_hold.py::test_a_dry_run_asks_no_host_and_holds_nothing` and `::test_no_publish_holds_nothing` unchanged and green.
- **Red → green:** with the production hunks reverted, `test_merge_resume_stranded_prereq` fails 93 of 107 cases (`failures=146, errors=11`, counting subtests; the 11 errors are a merge that never happened, a dependent built when it should have been held, and attributes the fix adds), and the rewritten test in `test_flow_out_of_batch_prereq_hold` fails. With the patch: 107 and 31 pass. The 14 cases green on both sides are the ones that pin unchanged behaviour (legs 4 and 5, the wave-boundary text, guards against merging too much). A mutation pass that broke 17 production decisions one at a time was caught by the module each time.
- **Suite:** driver suite 2804 passed (2 skipped), root suite 50 passed; docs lint, site render and link audit clean; `git diff --check` clean. All tests use real git (`StackFoldGit`: a bare `origin` and a checkout) and the real `_merge_one`, `_runnable`, `_drive_and_act` and `worktree.ensure`; only `gh` and the build/publish leaves are stubbed.

## Not in this PR (known, pre-existing, to file separately)
- The wave boundary can still merge an old PR head in the same run as a failed re-publish when the rollup is green; only the later-run path is guarded here. Now that `merge_wave` receives `pushed`, a refusal there is about five lines plus a test.
- `merged_into` does not check `merge_eligible_patch`, so an old PR already merged by hand releases a dependent after the prerequisite is rebuilt and never re-published.
- Reading review threads before merging is #838's gate; "passes the gates" here means `_merge_one`'s gates as they stand on the base this builds on.
- Remark rounds (#840), merging a `Merges with` group (#778), stack mode, and a backfill of the marker onto PRs published before it existed (they hold; the hold line says to merge them by hand).

Fixes #839
