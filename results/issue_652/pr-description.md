## Summary
**User impact:** When you re-issue a stack run, work whose pull request was closed
(rejected) can still end up under new bundles. If a bundle finished in an earlier run
was built on top of the closed one, the run carries it onto the integration line anyway,
and the closed work comes along inside its branch. The bundles that depend on it are then
built on top of rejected code, and the run says nothing about it.

This PR makes "not clean" spread to every finished bundle built on a not-clean one. Those
bundles are not carried, and the bundles that depend on them are held and named, with
the cause and what to do. The rest of the run goes on as before.

Reported in [#652](https://github.com/eduralph/pdca-harness/issues/652). It also covers
#624, the same gap one level further down (a held bundle → a bundle finished before the
run → its dependent).

## What to look at
- The new step that spreads "not clean" from one finished bundle to the finished bundles
  built on it, and where the carry calls it: before the check that decides whether an
  earlier run's line on origin can be trusted.
- The new held-line advice, which names the bundle it was built on.
- The docs paragraph on carrying finished prerequisites, which now states the rule and
  its one limit.

To try it: in a stack run, finish `P` and close its PR. Finish `Q` with
`Depends on: P` and its branch cut from `P`'s branch, and keep `Q`'s PR open. Plan `D`
with `Depends on: Q`, then re-issue `P Q D`. Before this change `Q` is carried and `D` is
built on a line holding `P`. After it, `D` is held, with one line like:

```
flow: issue_Q (finished in an earlier run) is not carried onto pdca-integration/main-…: its `Depends on` names issue_P, whose work its branch carries — holding issue_D this run; issue_Q was built on issue_P, which is not carried (see its line): get issue_P carried, or re-drive issue_Q on a base without it, then re-issue.
```

## Root cause
Before wave 0 the carry judges each finished id alone, from its own PR state and head
(`_finished_head`, `template/src/pdca_harness/flow.py:836-857` on main), and a held id
holds only the drive-set bundles whose plain `Depends on` names it (`flow.py:751-754`).
Nothing looks at the edges between finished ids, so a clean `Q` built on a closed `P`
is folded, and the fold merges `Q`'s branch tip with `P`'s commits in it
(`template/src/pdca_harness/integrate.py:461-475`).

## Fix
- New `_cascade_not_clean` (`flow.py:871-898` on the PR branch): reads each finished id's
  plain `Depends on`, keeps edges to other finished ids of the same target, and loops to
  a fixed point so a not-clean id makes every id built on it not clean, through a chain
  of any length and in any request order.
- `_carry_finished` runs it right after the per-id judgment and before
  `integrate.foreign_commit` (`flow.py:960-964`). That check now counts only the heads of
  ids that are still clean, so a cascaded `Q` can no longer vouch for `P`'s commit on an
  earlier run's line. The fold still only gets `clean`, so a cascaded id is never merged.
- New `_CARRY_HINTS["built_on"]` advice (`flow.py:866-867`); the held-line `.format`
  passes the cause (`flow.py:996-997`).
- The `_carry_finished` docstring (`flow.py:915-923`) and `docs/07-crosscutting.md:690-699`
  now say a not-clean finished id also holds the finished ids built on it and their
  dependents.

Not changed, and now documented: a bundle that passes the pre-fold check but whose merge
fails *during* the fold does not spread. A finished bundle built on it that merges in the
same fold still brings its commits onto the line. Handling that needs pruning inside the
fold, which is a larger change.

## Verification
- **Claim:** a finished bundle built (through plain `Depends on`) on a not-clean one is
  not carried; its drive-set dependents are held and named on one line with the cause;
  unrelated bundles still build.
  - **Checked:** `flow.py:946`, `:960-964`, `:971` on the PR branch: the cascade fills
    `why` before the fold, and only ids not in `why` are folded.
  - **Test:** `test_a_finished_id_built_on_a_closed_one_is_not_carried` — `D` held, one
    line naming `issue_Q`, `issue_D`, `issue_P` with the new advice (not "get its PR
    open"), no line created, unrelated `U` built and COMPLETE.
- **Claim (#624):** a hold reaches through a bundle finished before the run.
  - **Test:** `test_a_hold_cascades_through_a_dependent_finished_before_the_run`
    (`U` closed ← `D` finished ← `E` planned: `E` held).
- **Claim:** it spreads through any chain, in any order.
  - **Test:** `test_not_clean_spreads_through_a_chain_of_finished_ids` (`P` ← `Q` ← `R`
    ← `D`, requested from the far end).
- **Claim:** a clean finished bundle beside them is still carried, and the line it makes
  holds none of the closed work.
  - **Test:** `test_a_clean_finished_id_beside_them_is_still_carried`.
- **Claim:** a cascaded bundle's head does not make an earlier run's line holding the
  closed work look trustworthy.
  - **Checked:** `flow.py:960-964` (heads filtered by `why`); `integrate.py:472-473` on
    main shows the fold would otherwise skip a branch already on the line, so nothing
    else would remove it.
  - **Test:** `test_a_held_ids_head_does_not_vouch_for_an_old_line`.
- **Claim:** existing behaviour is unchanged — a clean `Q` on a clean `P` is carried, a
  closed `P` with no finished dependents holds only its own dependents.
  - **Test:** all 13 existing tests in `template/tests/test_flow_resume_stack_prereqs.py`
    pass, including `:176` and `:226`.

All five new tests in `template/tests/test_flow_resume_stack_prereqs.py` fail with the
production change reverted (each shows the dependent built on a line holding the closed
bundle's commit) and pass with it. Full offline suite: 2374 tests OK (2 skipped); docs
lint and render link audit OK.

Fixes #652
