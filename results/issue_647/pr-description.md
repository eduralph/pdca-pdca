## Summary
**User impact:** In stack mode, `pdca flow` could build a bundle on top of a base
that was missing the very fix it depends on. If the prerequisite had been finished in
an earlier run (its draft PR opened but not merged), the dependent was built anyway,
so its patch and tests ran against code without the prerequisite. This hits every
`--from-csv` sweep and any dependent driven in a different command from its
prerequisite. A related problem: if `gh` was missing, the run crashed with a traceback.

This PR makes that dependent wait until the prerequisite's PR has merged into the
dependent's own target branch. The run says so in one line, says what to do, and
builds the rest of the batch.

Reported in [#647](https://github.com/eduralph/pdca-harness/issues/647).

> **Stacked:** this builds on #648 (#646) and the changes under it on
> `pdca-integration/main` (#637, #638, #639). Review after those, or read only the
> top commit.

## What to look at
- The readiness check in `flow.py` (`_runnable`): what makes a dependent wait, and
  the one-line message it prints.
- The new `merged_into` in `merged.py`: when a prerequisite counts as "merged into
  this dependent's base". A PR merged into an integration branch, an `Onto branch`
  commit, or a PR in another repo does not count.
- To try it: create a finished bundle `P` with an open PR, and a bundle `D` with
  `- **Depends on:** P`, both targeting `main`. Run `pdca flow D U` in stack mode.
  Before: `D` is built. After: `D` stays planned, and stderr shows
  `flow: issue_D held — prerequisite(s) issue_P not merged into main (…) … name issue_P in the same `pdca flow <ids>` command … or wait until their PR merges into main, then re-run.`
  `U` builds as before.

## Root cause
`_runnable` accepted a prerequisite from outside the run as soon as it was COMPLETE.
COMPLETE only means "a draft PR was opened", and nothing in the run carries such a
prerequisite onto the line the dependent builds on. Separately, `merged.is_merged`
counted any MERGED PR, whatever branch it merged into, and called `gh` without
catching `OSError`.

## Fix
- `merged.merged_into(cfg, dep_id, repo, base)` (new, beside `is_merged`): same
  early answers as `is_merged` (not COMPLETE ⇒ no; empty or no patch ⇒ yes; no PR ⇒
  no). A MERGED PR counts only when its publish record's `repo` and `base` match the
  dependent's target and its mode is not `"stacked"`. This is the same rule the fold
  already uses for a deleted branch. It reads the PR through the guarded `pr_state`,
  so a missing or failing `gh` means "not merged", with a message. With no target to
  compare against, any merge counts, as before.
- `_runnable` now checks the state first for every edge, so a prerequisite that is
  not COMPLETE always gets the old "not ready" line. Then, for an out-of-batch
  prerequisite, it asks `merged_into` against the dependent's resolved target. This
  applies to `Depends on (merged)`, and to a plain `Depends on` when holding is on and
  a fold would carry that prerequisite. A dependent that fails the check is held and
  named on one line. The advice to name the prerequisite in the run appears only
  where that would put it on the dependent's line.
- `_drive_and_act` turns holding on only in stack mode with publishing, and not in a
  dry-run. It passes the ids the run was asked for, so a prerequisite named in the
  run is still left to #646's carry.
- `merged.is_merged` and its callers (merge mode's resume check, `status`) are
  unchanged.
- Docs: a new paragraph in the stack-mode section of `docs/07-crosscutting.md`.
- One existing test (`RunnableMergeGate` in `test_flow_slice.py`) now mocks
  `merged_into` and makes its prerequisite COMPLETE, as its own comment describes.

**Known limits.** A prerequisite that targets another repo or branch holds its
dependent until the edge is removed, because its record can never match the
dependent's target. This is what #647 asks for. A publish record with no `repo` key
does not match either. If a prerequisite's PR merges into `main` during a run, a
later-wave dependent on the run's line can still be let through without it. #186's
`(merged)` path already had that gap.

## Verification
Line numbers are on `pdca-integration/main` (`c1f2306`) with this patch applied.

- **Claim:** a dependent of an unrequested, unmerged prerequisite is held with a
  `not merged into main` line, from both entry points, and unrelated bundles still
  build.
  - **Checked:** `template/src/pdca_harness/flow.py:736-743` (hold decision),
    `:758` (message), `:2159-2161` (when holding is on, and the requested ids).
  - **Test:** `test_flow_ids_holds_a_dependent_of_an_unrequested_open_prereq` and
    `test_flow_batch_sweep_holds_a_dependent_of_a_finished_open_prereq`
    (`template/tests/test_flow_out_of_batch_prereq_hold.py:201`, `:207`).
- **Claim:** a merge counts only into the dependent's repo and branch, and not
  through an `Onto branch` commit.
  - **Checked:** `template/src/pdca_harness/merged.py:67-111`, the rule at `:104`.
    It matches the fold's rule in `template/src/pdca_harness/integrate.py:520`.
  - **Test:** `test_merged_into_an_integration_line_does_not_count` (`:236`) uses
    the real shape of a `"stacked-pr"` record against `pdca-integration/main`. The
    `Onto branch`, other-repo and `Depends on (merged)` cases follow it.
- **Claim:** a missing or failing `gh` holds the dependent, without a traceback.
  - **Checked:** `template/src/pdca_harness/merged.py:146-155` (`pr_state` catches
    `OSError`).
  - **Test:** `test_gh_missing_holds_the_dependent_without_a_traceback` (`:304`),
    plus the `(merged)` and `gh exits 1` cases.
- **Claim:** existing behaviour is unchanged where it should be: a requested
  prerequisite, `Stacks on`, `--no-publish`, merge mode, a dry-run, a dependent with
  no target, a not-ready `(merged)` prerequisite, and `is_merged` itself.
  - **Checked:** `merged.is_merged` is untouched at `merged.py:37`, and its callers
    at `template/src/pdca_harness/merge.py:387` and `template/src/pdca_harness/cli.py:1084`
    are untouched too. The state check comes first at `flow.py:731`.
  - **Test:** `test_is_merged_still_answers_true_for_a_merged_onto_branch_record`
    (`:366`), `test_a_dependent_with_no_target_field_is_not_held` (`:377`),
    `test_a_planned_depends_on_merged_prereq_is_not_ready` (`:425`), and the other
    "unchanged" cases.
- **Red → green:** `cd template && PYTHONPATH=src python3 -m unittest tests.test_flow_out_of_batch_prereq_hold`
  runs 31 cases. With only the production changes reverted, 13 fail: 11 failures
  (the dependent is built, or gets the wrong reason) and 2 errors (`FileNotFoundError: 'gh'`
  escapes the run). With the patch, all 31 pass. A separate independent run got the
  same red/green split.
- **Suites:** the full offline driver suite passes (2369 tests, 2 skipped). The root
  render and update-compat suite passes (24 tests). The docs lint and the site render
  link check are clean.

Fixes #647
