## Summary
**User impact:** When you re-run a stacked batch of fixes and one of the earlier fixes was closed without a patch (a "no fix needed" outcome), any fix that depends on work *behind* that closed one can be built without that work and still be reported as done. If that earlier work was rejected (its PR closed), the dependent fix is not held back, and the rejected work can end up on the shared line. You get no warning either way.

This PR makes the re-run treat a bundle closed with no patch as a link in the dependency chain, so work reached through it is carried, and the dependents are held when that work is rejected.

Reported in [#728](https://github.com/eduralph/pdca-harness/issues/728).

**Depends on #727** (draft PR #733). This change builds on #727's dependency-scoped bases and should be merged after it.

## What to look at
The change is in one place: the step that runs at the start of a re-issued stack run and decides which already-finished fixes to bring along. Before this PR it only followed a fix's direct dependencies. Now it also follows dependencies through finished fixes that have no patch.

To see it: finish fix A, close fix N with no patch where N depends on A, then plan fix D that depends on N, and re-issue the run for A, N and D. Before this PR, D is built on plain `main` without A. After it, A is carried and D is built on top of it. If A's PR is closed, D now waits instead of being built.

The new test file `template/tests/test_flow_carried_prereq_bases.py` sets up each of these cases with real git.

## Root cause
A finished bundle with no patch is never a fold candidate, so the re-issue carry (`_carry_finished`) built its dependents map, its "not clean" spread (`_cascade_not_clean`) and its held set only from direct `Depends on` edges between patched bundles. Any edge that ran through a no-patch bundle was lost. The in-run closure walk from #727 already counts such a bundle as a node, but the carry did not.

## Fix
All in `template/src/pdca_harness/flow.py`:

- New helper `_reached`: from a bundle, follow plain `Depends on` edges, stop at a fold candidate, and keep going only through finished bundles with no patch. It is breadth first and keeps a `seen` set, so a cycle between no-patch bundles still ends. With direct edges only, it returns the same ids in the same order as the old loops.
- `_carry_finished` builds its dependents map with `_reached`, so `D → N → A` records D under A and A is carried.
- `_cascade_not_clean` takes the no-patch bundles and reads each bundle's prerequisites with `_reached`, so `P → N → A` with A not clean makes P not clean, with A named as the cause. Through a no-patch bundle the reason reads "its `Depends on` reaches issue_A, whose work its branch carries, through issue_N (finished with no patch)". The existing `built_on` hint is reused.
- After the per-target loop, a no-patch bundle that reaches a held candidate is added to `held`. `_runnable` already holds a bundle whose plain `Depends on` names a held id, so its dependents wait with no change there. The no-patch bundle prints no line of its own. The held candidate's existing "is not carried … holding …" line lists the dependents it holds through it.
- The docstrings of `_cascade_not_clean` and `_carry_finished` say all this.

`_runnable`, `_closure_members` / `_bundle_bases` and `integrate.py` are unchanged.

Not covered here, filed as follow-ups: an out-of-batch prerequisite reached only through a no-patch bundle (#734), and carried bundles as members of a dependent's own base (#735).

## Verification
Line numbers are on this PR's branch (#727's result plus this patch).

- **Claim:** work reached through a no-patch finished bundle is carried, and the dependent is built on it.
  **Checked:** `template/src/pdca_harness/flow.py:1182-1204` (`_reached`), `:1291-1295` (no-patch set and dependents map).
  **Test:** `test_a_prerequisite_reached_through_a_patchless_id_is_carried`, `test_a_chain_of_patchless_ids_is_walked_through` (two no-patch bundles, batch in reverse order). Both fail before the fix (no carry, D on plain `main`) and pass after.
- **Claim:** a dependent that reaches rejected work through a no-patch bundle waits, unrelated work still builds, and the no-patch bundle prints no line of its own.
  **Checked:** `flow.py:1386-1387` (hold), `flow.py:803` (`_runnable`'s existing hold on a held prerequisite, unchanged).
  **Test:** `test_a_closed_prerequisite_reached_through_a_patchless_id_holds_the_dependent`. It fails before the fix (D is built) and passes after.
- **Claim:** "not clean" spreads through a no-patch bundle, so a finished bundle built on rejected work is not carried.
  **Checked:** `flow.py:1207-1234` (`_cascade_not_clean`), call at `:1324`.
  **Test:** `test_one_built_on_a_closed_id_through_a_patchless_id_is_not_carried`. It fails before the fix (P is carried with A's closed-PR commit) and passes after.
- **Claim:** clean resumes are not falsely stopped or marked not clean.
  **Test:** `test_a_clean_resume_through_a_patchless_id_carries_both_and_stops_nothing`, `…_continues_the_earlier_line` (runs the foreign-commit check against a real earlier line), `test_a_dependent_through_a_patchless_id_beside_one_naming_the_prerequisite`, and the existing `test_a_prerequisite_without_a_patch_carries_nothing`. All pass before and after.
- **Claim:** a dry run still asks no host and holds nothing.
  **Test:** `test_a_dry_run_through_a_patchless_id_prints_the_plan_and_holds_nothing`. It fails before the fix (no plan printed) and passes after.
- **Red/green:** with only the `flow.py` changes reverted, 5 of the 8 new tests fail on their assertions (the module loads). With the patch, all 8 pass.
- **No regressions:** `cd template && PYTHONPATH=src python3 -m unittest discover -s tests` gives 2589 tests OK (2 skipped). The root template suite gives 24 OK. No existing test file is changed.
- **Mutation check:** breaking each part on its own (dependents map, cascade, hold, an over-eager walk) makes at least one of the new tests fail.

Fixes #728
