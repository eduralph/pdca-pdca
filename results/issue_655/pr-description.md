## Summary
**User impact:** In stack mode, a fix that depends on another, already-merged fix could be built and published on top of code that does not contain that other fix, with no warning. This happens when the other fix's PR is merged into `main` while a run is already going (or before a resumed run that reuses an older integration branch). The result is a PR whose build and tests ran against the wrong base.

This PR makes the run check that the branch a dependent will actually be built on has the prerequisite's change. If it does not, the dependent is held, named on one line, and the message says how to get it built.

Reported in [#655](https://github.com/eduralph/pdca-harness/issues/655).

## What to look at
- The readiness check for a dependent in `flow.py` (`_runnable`), and the new helper next to it that asks "does this branch have the prerequisite's merge?".
- The new held message. It names the dependent, the prerequisite, the integration branch and its tip, and the way out: once the run ends, delete that integration branch on origin, then re-run. A plain re-run is not enough, because the resume step would continue the old branch and hold the dependent again.
- To reproduce: run `cd template && PYTHONPATH=src python3 -m unittest tests.test_flow_merged_prereq_on_line`. The tests use real git with a bare origin; only `gh` is stubbed. A prerequisite's PR is merged into `main` right after the run's first wave has pushed its integration branch. Before this change, the dependent in the next wave is built on that branch anyway.

This PR is stacked on the run's integration branch (it sits after #629, which also edits `_runnable`). Line numbers below are on this PR's branch.

## Root cause
The gate for an out-of-run prerequisite only asks the host whether its PR merged into the dependent's base (`merged.merged_into`). Once the run has folded that base, the dependent is pointed at the run's integration line, which was cut from the base earlier and never takes the base in again. So a merge that landed after the line was cut passes the gate but is missing from what the dependent is built on.

## Fix
- `template/src/pdca_harness/flow.py`
  - `_runnable` takes a new `lines=` map (target → integration branch and the tip the run recorded). After `merged_into` says yes, and only when the run has a line with a recorded tip for that target, it calls `_line_lacks_merge` (`flow.py:773-785`).
  - `_line_lacks_merge` (`flow.py:831-868`) reads the checkout through `integrate.carry_view` (fetches first, read-only, no lock) and asks whether the PR's merge commit or the PR's head is an ancestor of the recorded tip. The merge commit covers merge, squash and rebase merges. The head covers a prerequisite the resume carry already put on the line. A failed fetch, an unreadable merge commit or a git error holds the dependent (fail-closed).
  - Results are cached per call, so several dependents of one prerequisite cost one fetch and one extra `gh` call.
  - One stderr line per held dependent (`flow.py:803-814`). It does not claim the run cut the line, because on a resumed run the line may have been continued from origin.
  - The caller passes the same maps `_point_at_integration` uses to set the dependent's base (`flow.py:2334-2336`), so the check is on the exact commit the dependent would be cut from.
- `template/src/pdca_harness/merged.py`: new `merge_and_head()` (`merged.py:149-169`) reads `state,headRefOid,mergeCommit` in one `gh pr view` call. `pr_state()` and it now share a small `_pr_view()` helper (`merged.py:185-200`); `pr_state`'s behaviour is unchanged.
- `docs/07-crosscutting.md:745-759`: describes the new hold and the way out.

Not changed: merge mode (it never builds an integration line), a target with no line yet (the dependent is cut from the freshly fetched base, as before), and `merged.is_merged` and its other callers. Refreshing or re-cutting the line mid-run is out of scope.

## Verification
- **Claim:** a dependent with a `Depends on (merged)` prerequisite whose PR merged after the line was started is not built, and is named on one line.
  - **Checked:** gate at `template/src/pdca_harness/flow.py:773-785`, message at `:803-814`.
  - **Test:** `template/tests/test_flow_merged_prereq_on_line.py:202`. Fails before the fix (dependent built on a line without the merge), passes after.
- **Claim:** the same holds for a plain `Depends on` edge to a prerequisite the run was not asked for.
  - **Test:** `…:212`. Fails before, passes after.
- **Claim:** a merge already on the line still lets the dependent build. This includes a squash merge, whose PR head is never on `main`, so the check must use the merge commit.
  - **Checked:** `_line_lacks_merge` checks `mergeCommit` first, then the head (`flow.py:857-863`).
  - **Test:** `…:222` (merge commit) and `…:230` (squash). Pass before and after; `:230` would fail if the check used only the PR head.
- **Claim:** if the merge commit cannot be read, or the checkout cannot be fetched, the dependent is held.
  - **Test:** `…:241` and `…:249`. Fail before, pass after.
- **Claim:** a target with no line yet is unchanged.
  - **Test:** `…:257`. Passes before and after.
- **Claim:** on a resumed run where the line already has the prerequisite's PR head but not `main`'s merge commit, the dependent is still built. This is not a false hold.
  - **Test:** `…:269`. Passes before and after. With the check limited to the merge commit, this case fails, which confirms the head check is needed.
- **Claim:** the advice in the message works. A re-run with the line still on origin holds again; after deleting the line, a re-run builds the dependent on a new line that has the merge.
  - **Test:** `…:293`. Fails before, passes after.
- **Suites:** with the production change reverted, 5 of the 9 new cases fail on assertions; with it, all 9 pass. The full driver suite passes (2451 tests, 2 skipped), including `test_flow_out_of_batch_prereq_hold.py`, `test_flow_resume_stack_prereqs.py` and `test_integrate_stack_bases.py`. Docs lint and site link audit are clean.

Fixes #655
