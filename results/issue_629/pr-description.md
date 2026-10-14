## Summary
**User impact:** In a multi-bundle `pdca flow` run (stack mode), if a bundle is accepted but its publish fails to push a branch, any bundle marked as `Conflicts with` it is still built and published, on a base that does not contain the first bundle's change. The two touch the same files, so when you later publish the first one by hand, the two PRs collide on the target and one has to be redone.

This PR holds that partner bundle for the rest of the run, the same way a bundle that depends on the failed one is already held. It prints one line saying which bundle is held, why, and to wait for the other bundle's PR to merge before re-running. The rest of the run carries on.

Reported in [#629](https://github.com/eduralph/pdca-harness/issues/629).

## What to look at
- The scheduling change is small and sits in `flow._runnable` (the per-wave "is this bundle ready to build?" check) and the one place the wave loop calls it.
- The new held line's advice: it says to wait for the merge rather than "publish, then re-run", because a quick re-run would build the partner without the other bundle's work and hit the same collision.
- To try it: run `cd template && PYTHONPATH=src python3 -m unittest tests.test_flow_conflict_partner_hold`. It drives `flow.flow_ids` offline (leaves and `gh` stubbed) with bundle 702 declaring `Conflicts with: 701`, and 701's publish pushing nothing.
- Also touched, one clause each, so no shipped text contradicts the code: `docs/07-crosscutting.md`, `template/PCDA/quality-cycle/09-parallel-lanes.md`, `template/pdca.toml.jinja`. Drop the last two if you'd rather keep the PR narrower.

## Root cause
`waves.compute_waves` turns each `Conflicts with` pair into an ordering edge, so the second bundle builds in a later wave on a line meant to hold the first (`template/src/pdca_harness/waves.py:200-212`). Since b21f24883b36c10dd70c408905db8c18a5327845, a bundle that pushed no branch is left out of the fold (`held_unpushed`), but `_runnable` only holds bundles whose *declared* prerequisites (`Depends on` / `Stacks on`) name it, and never looks at the conflict edge, so the partner was built anyway.

## Fix
- `_runnable` takes two optional keyword arguments: `unpushed` (the run's `held_unpushed`) and `conflicts` (a name → names map). A bundle with a conflict partner in `unpushed` is left out and gets its own stderr line, which never calls the partner a "prerequisite". Defaults leave every other caller unchanged.
- The wave loop builds the map with the existing `waves.conflict_map` from the run's **current** bundle list on each wave, so split children adopted mid-run are covered. It only does this when something is actually in `held_unpushed`, so normal runs read no extra briefs.
- The partner's own dependents are skipped by the existing "prerequisite not COMPLETE" check, so the hold cascades with no extra code.
- The "pushed no branch" announcement now says conflict partners are held too.

Known gaps, left as they are: a partner of a partner (CK conflicts with CJ, which is held here) still builds, same as today for a partner of any bundle that isn't complete. A bundle with both a `Depends on` and a `Conflicts with` edge to the same unpushed bundle prints both lines.

## Verification
- **Claim:** a `Conflicts with` partner (declared on either side) of an accepted bundle that pushed no branch is not built, stays PLANNED, and is named on one stderr line; an unrelated bundle in the same wave is still built, and the partner's dependents are skipped.
  - **Checked:** `template/src/pdca_harness/flow.py:681-788` (`_runnable`: new arguments, partner lookup, held line, runnable test) and `flow.py:2231-2237` (the call, with the map rebuilt per wave), on this branch.
  - **Test:** `template/tests/test_flow_conflict_partner_hold.py` cases 1 and 2. With the production change reverted, both fail: 702 is built, and the real fold then stops the run trying to merge its branch.
- **Claim:** the conflict relation follows bundles added mid-run.
  - **Checked:** `flow.py:2228-2237` calls `waves.conflict_map(cfg, bundles)` inside the wave loop (`waves.py:136-153`: symmetric, limited to the bundles in the run).
  - **Test:** case 3 splits 706 into 707/708 through the real `split.accept`; 707 pushes nothing, 708 is held. It fails pre-fix, and it also fails if the map is built once before the loop.
- **Claim:** the advice doesn't lead back to the bug.
  - **Checked:** `flow.py:779-785` ends with "wait until their PR merges into <base> (<repo>), then re-run".
  - **Test:** cases 1–3 check that ending. Putting the old "publish them, then re-run" wording back fails all three.
- **Claim:** unchanged when the first bundle's branch is pushed.
  - **Test:** case 4 builds all five bundles, 701 before 702, with no hold text. It passes before and after the fix.
- **Suites:** the full offline suite passes (driver suite: 2427 tests OK, 2 skipped), and so do the docs lint and link check.

Fixes #629
