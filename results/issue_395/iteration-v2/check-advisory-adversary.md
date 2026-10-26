# Adversarial review — issue 395 (same-wave conflict caught before publish)

I re-ran the proof and three probe cases against the patched tree at `$PDCA_TARGET`. The
probe scripts are in `scratch/probes/` in this sandbox. The red→green evidence holds up.
The fix does what the brief asks for the plain case. I found two gaps where a stated
claim is false, and one case where the run gives a step nobody can follow.

## Findings

- NEEDS-HUMAN [human] — **"the wave never opens two PRs that conflict with each other" is false for a bundle that conflicts with a sibling AND with the line.** `docs/07-crosscutting.md:728` and the comment at `template/src/pdca_harness/flow.py:3134` both claim it. The trial only asks `_held_by` (`template/src/pdca_harness/integrate.py:864-867`). The fold also asks `_held_by_line`, and passes it the same-wave bundles it already merged (`integrate.py:663-668`). Probe (`scratch/probes/probe_mixed.py`): wave 0 is 10 (line 2 of `shared.txt`) and 12; wave 1 is 20 (line 8, depends on 12) and 21 (lines 2 and 8, depends on 12); 30 depends on 20, so a fold follows wave 1. Result: `fix/20` and `fix/21` are both pushed and both get `gh pr create`. Then the fold holds 21, saying it "conflicts with issue_20's, merged before it in the same wave 1, and issue_10's". `main` does the same, so nothing regressed. But the patch leaves exactly the two-conflicting-PRs case the docs say can't happen. The brief limits the trial to the #674 rule, so this is a scope call: either widen the trial to the fold's `_held_by_line` when its partners include a same-wave bundle, or narrow the docs and comment to the #674 case.

- NEEDS-HUMAN [human] — **When the trial can't run, it also holds siblings that can't conflict, plus everything that depends on them.** `template/src/pdca_harness/integrate.py:827` marks every member after the first as "untried", whatever files it touches. Probe (`scratch/probes/probe_395.py`): the test's own `_pair` fixture (10 and 11 change the same line, 12 has a file of its own, 20 depends only on 12), with the trial's two fetches failing. Result: holds are `{11: unpushed, 12: unpushed}`, `fix/12` is never pushed, 20 is never built, exit code 1. On `main`, with the fold's fetch working, 12 publishes and folds, 20 builds, and the exit code is 3. So the brief's "Its siblings publish as before" fails on this path. There is a cheaper fallback that still never lets two conflicting PRs out: hold only the bundles whose patch shares a file with an earlier ready bundle. A textual conflict needs a shared path, and `waves.diff_files` already gives the file list (`flow.py:1614`). This failure policy came out of the round-1 iterate, so the human should pick it.

- NEEDS-HUMAN [impl] — **A pre-publish hold record outlives its partner, and the re-issue then gives a step that can't be done.** `template/src/pdca_harness/flow.py:1515-1525` and `:1546` let `conflict-hold.json` override every other verdict ("whatever else below is wrong"). Probe (`scratch/probes/probe_stale.py`): after `_held_11_with_20_on_it`, issue_10's PR is closed without merging, then a re-issue drives 20. 11 is still told "rebuild issue_11 on a base that holds issue_10", which can't happen because 10 will never land. The message never mentions `pdca publish 11`, the step that would actually unblock 20. The hold no longer protects anything once no partner has an open or merged PR. Fix: when no partner named in the record is a clean finished id, fall back to the normal judgement (the "open" hint), or add the publish step to the advice.

## Checked, not a refutation

- The red leg's 24 errors in `template/tests/test_flow_reissue_after_conflict_hold.py` are `AttributeError`s from `mock.patch.object(flow, "_held_before_publish", ...)` (line 127) on the reverted tree (`gate-logs/C4-verify.log:38-659`). They show the symbol is missing, not that any behavior changed. The real red is the 7 assertion failures in the new file (fix/11 or fix/21 pushed before the fix, `C4-verify.log:713-804`) plus 3 in `test_flow_same_wave_conflict.py` (`:661-711`). That is enough for C4 to pass on merit.
- I tried to break these and could not:
  - **Production path.** The new tests use the real `publish.publish`, real git, a bare origin, and a `pre-receive` hook for the failed push. Only `_drive_wave`, `draft_texts` and `gh` are stubbed. I re-ran the green leg here: 20 tests OK.
  - **Same base as publish.** The `_checkout_base` refactor (`publish.py:804`) gives the same result as the old `wave_stacked and bool(wave_tip)` (`publish.py:251`), so the trial and publish cut each branch from the same commit.
  - **Same order and rule as the fold.** The trial merges in the fold's name order, starts from the same place (this run's folded tip, else `<base_remote>/<base>`), and uses the same `_held_by`.
  - **Exceptions.** `_LineBroken` and `IntegrationTreeError` both subclass `IntegrationError` (`integrate.py:103`, `:112`), so the retry catches them and nothing escapes as a traceback.
  - **Tests that pass before the fix.** Legs (d) and (f) pass on the reverted tree, but they would catch a trial with no `ready` filter, or one that also ran on the last wave.
  - **Locks.** Taken in sorted target order on one `ExitStack`, the same way the fold takes them.

<!-- pdca:leaf-complete -->
