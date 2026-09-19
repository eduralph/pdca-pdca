## Summary
**User impact:** if a bundle's first attempt is sent back to Plan and you then split it
into child bundles during that Plan session, the parent bundle gets stuck for good. Every
`pdca flow` on it opens a Plan session with nothing to decide, gets no brief back and
stops. The parent never reaches sign-off, never gets a `SUMMARY.md` and never freezes.
This is the common way a split happens: a first attempt shows the slice is too big, it
goes back to Plan, and Plan splits it. Seen on a real instance with two parents stuck this
way; parents split on their first attempt were fine.

This PR makes accepting a split give such a parent a short brief that describes the split
and names its children, and stops a finished bundle from being read as "never planned"
just because it has no `brief.md`. The parent now goes straight to sign-off.

Reported in [#481](https://github.com/eduralph/pdca-harness/issues/481).

## What to look at
- **The split accept** (`split.py`): when the parent has no `brief.md`, it now writes one
  just before the close marker. Slug and repo + branch target are copied from the brief
  archived by the latest re-plan; the rest says the slice was split, names every child
  bundle and points at the archived original. A parent that still has its own brief is not
  touched.
- **The state check** (`state.py`, `state()`): "has this bundle got past Do?" is now asked
  before "does it have a brief?".
- **One shared reader of the `iteration-v<N>` archives** in `state.py`, used by the split
  and by the size backstop, replacing two private copies.

To try it: in a bundle with a complete brief, send it back to Plan (the brief moves to
`iteration-v1/`), write a two-child `split-proposal.md`, and run
`pdca split <id> --accept`. On `main` the parent then reads `UNPLANNED` and has no
`brief.md`; with this change it has a brief naming both children, and `pdca flow <id>`
takes it to sign-off.

**Behaviour changes to be aware of:**
- A split is now refused, before any child tracker issue is filed, when the parent has no
  brief and no archived brief to rebuild one from, or when the archived brief is missing
  its slug, success criterion or repo + branch target. Before, these "succeeded" into the
  stuck state. The error says which field is missing and how to fix it.
- Parents already stuck from an older version no longer reopen Plan. They now stop at
  summary assembly with an error naming the missing `brief.md`. To repair one, copy its
  `iteration-v<N>/brief.md` back to `brief.md` and run it again. `pdca split --accept`
  cannot repair them because it refuses a parent that is already marked.

## Root cause
Sending a bundle back to Plan archives its brief (`driver.py:140`,
`_archive_iteration(..., include_brief=True)`), and `split.accept` then writes the close
marker (`split.py:862`) but never a parent brief. `state()` returned `UNPLANNED` for any
bundle without `brief.md` (`state.py:304-307`) before it ever looked at `patch.diff` or the
close marker (`state.py:310`), so a finished parent read as never planned.

## Fix
- **`state.state()`**: the "past Do?" test (a `patch.diff` or the close marker) now comes
  first, and the missing-brief → `UNPLANNED`/`RESOLVED` branch only applies to bundles
  that are not past Do. The only answer that changes is for "no brief + a Do artifact",
  which now derives what the same bundle with a brief derives. It was never `RESOLVED`
  before either: `is_resolved` already counted both files as cycle evidence.
- **`split._parent_plan`**: returns `None` when the parent has its own `brief.md` (it is
  never opened). Otherwise it takes the latest re-plan archive's brief, checks it with
  `handoff.check_planner(..., dependencies=False)` (slug, success criterion, repo + branch
  target), and raises `SplitError` before any write if there is no archive, it cannot be
  read, or a field is unfilled. `preflight` calls it too, so the CLI refuses before
  `file_children` files real tracker issues.
- **`split._split_parent_brief` / `_field`**: render the new brief. Slug and target are
  copied so that `brief.whole_field` reads them back unchanged; Defect, Success criterion
  and Scope describe the split and name every child; `External dependencies: none`,
  `Disposition hint: split`.
- **`split.accept`**: renders the brief in the pre-write phase next to the lineage
  snapshot, writes it as the last write before the close marker, and on any failure
  removes it after the marker's own cleanup. The removal is not tied to the brief write
  having returned, because a write can create the file, land part of it and then raise
  (a full disk). A torn brief left behind would be kept by the retry as the parent's own.
- **Shared archive reader**: `state.iteration_archives` (every `iteration-v<N>` directory,
  sorted by N as a number, so `iteration-v10` comes after `iteration-v2`) and
  `state.replan_archives` (those holding a `brief.md`). `size_signal.iteration_rounds` now
  uses them and drops its own regex; results are unchanged. The unused copy of the pattern
  in `scripts/size-calibrate` is removed. `state.py` was chosen because both callers
  already import it and it already holds the archive definitions.
- **Docstring**: `handoff.check_planner` now names both callers that pass
  `dependencies=False` and why the split does.

Not in this PR: hand-repairing already-stuck bundles; the convergence report in
`preflight` still sizes a briefless parent as 0 (advisory only, same as on `main`);
`template/PCDA/quality-cycle.md:60-68` still shows the simplified "no brief.md →
UNPLANNED" ladder for an ordinary bundle.

## Verification
Line numbers on `main` are at `4050da2`; "after" means this branch.

- **Claim:** a parent split after a re-plan is not read as never planned, and gets a brief
  that passes the Plan exit check and names every child.
  - **Checked:** on `main`, `split.py:836-838` archives with `include_brief=False` and
    `:862` writes the marker with no brief. After: `_parent_plan` at `split.py:756-806`,
    `_split_parent_brief` at `:817-854`, rendered at `:909-911`, written at `:978-979`
    just before the marker at `:980`.
  - **Test:** `template/tests/test_split.py`, class `SplitParentKeepsAPlanArtifact`
    (`:1781`). The parent is built through the driver's own `_archive_iteration` call,
    not by hand-placing files. `test_a_…` (`:1857`), `test_b_…` (`:1863`), `test_c_…`
    (`:1874`), `test_d_…` (`:1885`). Fail on `main`, pass here.
- **Claim:** the parent now reaches sign-off, with the split described in its summary.
  - **Test:** `test_the_iterated_parent_is_driven_to_sign_off_not_back_to_plan`
    (`:1914`) runs `driver.run_issue` with the build and review steps wired to fail if
    called; it ends at `AWAITING_SIGNOFF` with both children named in `SUMMARY.md`.
- **Claim:** any bundle with a Do artifact and no brief is never placed before Plan,
  however it got that way.
  - **Checked:** `state.py:304-307` on `main` returned early for a missing brief. After:
    `state.py:347-351`.
  - **Test:** `test_e_…` (`:1935`) builds six shapes directly (marker alone, the exact
    stuck file set from the report, a tracker-resolved record, gates recorded, summary
    assembled, `patch.diff`) and checks each derives the same state as its twin with a
    brief. Fails on `main`, passes here.
- **Claim:** a parent that still has its own brief keeps it byte for byte.
  - **Test:** `test_f_…` (`:1970`): a first-attempt parent with a bare brief, and an
    iterated parent re-briefed before splitting. All earlier tests in `test_split.py` stay
    green.
- **Claim:** a failed accept leaves no new brief behind, and the retry completes.
  - **Checked:** rollback at `split.py:1002-1010`.
  - **Test:** `test_a_torn_brief_write_…` (`:1989`) lands 40 characters then raises
    `ENOSPC`; `test_a_failure_after_the_brief_landed_…` (`:2016`) fails the marker write
    after the full brief landed. Both check the retry succeeds.
- **Claim:** nothing authored to rebuild from means a refusal before any write or
  tracker filing.
  - **Checked:** `preflight` calls `_parent_plan` at `split.py:325`.
  - **Test:** `test_an_archived_brief_with_an_unfilled_field_…` (`:2042`),
    `test_a_parent_never_briefed_at_all_…` (`:2054`),
    `test_the_cli_refuses_before_filing_a_single_tracker_issue` (`:2063`).
- **Claim:** the split and the size backstop read the same latest re-plan.
  - **Checked:** `size_signal.py:69-70` and `:147-154` on `main` held their own copy.
    After: `state.py:303-332`, used at `size_signal.py:145-147` and `split.py:781-787`.
  - **Test:** `test_the_source_is_the_latest_re_plan_not_the_first_archive` (`:1892`)
    builds ten rounds with re-plans at 2 and 10; the brief is rebuilt from
    `iteration-v10`, and `iteration_rounds` returns `(0, 2)`. Sorting archives as text
    instead of by number fails it with `(8, 2) != (0, 2)`.
- **Suite:** `test_split.py` runs 109 tests: all pass with the fix, and 16 fail on
  assertions (no import errors) with the fix's non-test changes reverted. Reverting only
  `split.py` or only the `state()` reorder fails the matching subset. The offline driver
  suite passes (1907 tests, 2 skipped), including `test_size_signal.py` and
  `test_size_calibrate.py`; the render/update-compat suite, docs lint and site link check
  pass.

Fixes #481
