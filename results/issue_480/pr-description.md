## Summary
**User impact:** if you turn on the optional plan review, it is meant to check every brief a
Plan session writes before anything gets built from it. But when a Plan session for one
issue splits that issue into child issues, the children's briefs are never reviewed. They
go straight on to be built. Instead, the review either grades the parent's old brief, which
nobody will build now that the issue is closed as split, or it does nothing at all. The
first case still writes a review file, so it looks like the review ran. This happened twice
on a real project, and checking the children by hand afterwards found real errors in their
briefs both times.

This PR makes the review after a Plan session cover exactly the briefs that session wrote
or changed, including the children of a split. It never reviews an issue that is already
closed.

Reported in [#480](https://github.com/eduralph/pdca-harness/issues/480).

## What to look at
The change is in how the driver picks which briefs to send to review once a Plan session
ends. Before, a session for one issue reviewed only that issue. A session for several
issues already compared briefs before and after the session. Both kinds of session now
use that before/after comparison, through the same helper. Separately, the review step now
skips any issue marked closed, whichever path called it.

To try it offline: set up a plan reviewer in stub mode, create a parent issue with a brief,
and run a single-issue Plan whose session writes briefs for two new child issues and marks
the parent closed as split. On `main`, only the parent gets a `plan-advisory-*.md` file. If
you delete the parent's brief first, nobody gets one. With this PR, both children get the
review file and the benefit record, and the parent gets neither. The new test file does
exactly this by swapping in a fake planner.

## Root cause
`do_plan` ended with `run_plan_advisory(d, cfg)`, which reviews only the bundle it was
handed (`template/src/pdca_harness/leaves.py:927` on `main`). A split accepted during that
session writes briefs into new bundles `do_plan` never sees, and marks `d` closed. So the
pass either reviewed `d`'s superseded brief or, with `d`'s brief gone, dropped it at the
filter (`leaves.py:3364-3365`). The children come out of the split already `PLANNED`, so
`flow._plan_if_unplanned` returns early for them and never reaches the review
(`template/src/pdca_harness/flow.py:367-368`). `do_plan_batch` already chose bundles by a
before/after hash of their briefs (`leaves.py:1073-1075`, `:1129-1133`), but it had no
check for closed bundles. A parent that was briefed and then split in the same batch
session counted as fresh and got reviewed.

## Fix
- **`_brief_snapshot(cfg)`** (new, `leaves.py:3360-3369` on the PR branch): the
  before-session hash of every non-placeholder brief in the bundle root. This code used to
  sit inline in `do_plan_batch`.
- **`_fresh_plan_briefs(cfg, briefed_before)`** (new, `leaves.py:3372-3389`): every
  bundle whose brief is new or has changed since the snapshot. This also used to be inline
  in `do_plan_batch`.
- **`do_plan`** takes the snapshot before the planner runs (`leaves.py:923`). Afterwards
  it calls `run_plan_advisory_batch(cfg, _fresh_plan_briefs(...))` instead of
  `run_plan_advisory(d, cfg)` (`leaves.py:939`).
- **`do_plan_batch`** uses the same two helpers (`leaves.py:1085`, `:1139`). Its behaviour
  does not change.
- **`run_plan_advisory_batch`** adds `and not (d / state.CLOSE_MARKER).exists()` to its
  existing filter (`leaves.py:3405-3407`). Every Plan path goes through this function, so
  one check covers both. It also covers a closed bundle whose brief changed in the same
  session, which the hash comparison alone would let through.

`run_plan_advisory` is unchanged and still used directly by the existing tests. No prompt
text, no `handoff.session(...)` block, and nothing in `split.py` or `flow.py` changes.

Not in this PR: children of a split accepted outside a Plan session, from a sign-off
session or a shell. They never enter Plan, so they still get no plan review. That is a
separate gap.

A small known cost: `do_plan` now takes the snapshot even when no plan reviewer is
configured, which means reading and hashing every brief in the bundle root once per call.
That took about 2.5 ms for 61 briefs. Skipping the snapshot when no reviewer is configured
would be a one-line follow-up. It is left out here to keep this PR to one change.

## Verification
- **Claim:** after a single-issue Plan session that splits, every child gets a plan review
  and a benefit record, and the parent gets neither. This holds whether the parent keeps
  its brief or has none.
  - **Checked:** `template/src/pdca_harness/leaves.py:923` (snapshot) and `:939` (review
    of what the session wrote), on the PR branch.
  - **Test:** `test_shape1_parent_keeps_brief_children_reviewed_parent_is_not` and
    `test_shape2_parent_has_no_brief_children_still_reviewed`
    (`template/tests/test_plan_advisory_split_children.py:66`, `:81`).
- **Claim:** a closed bundle is never reviewed on either Plan path, even if its brief
  changed.
  - **Checked:** `leaves.py:3405-3407` (the filter both paths go through). The marker is
    the one `split.py` writes (`template/src/pdca_harness/split.py:862` on `main`;
    `state.py:44`). A separate check also ran a multi-issue session that created two
    children and freshly briefed a parent that was then closed. Only the children were
    reviewed.
  - **Test:** `test_terminal_bundle_is_never_reviewed_even_if_its_brief_changed` (`:97`).
- **Claim:** single-issue sessions now choose briefs the way multi-issue sessions do. An
  unchanged brief elsewhere is skipped, a rewritten one is reviewed, and a placeholder is
  never reviewed.
  - **Checked:** `leaves.py:3360-3389` (the shared helpers).
  - **Test:** `test_single_bundle_path_selects_like_the_batch_path` (`:111`). This one
    passes before the fix too. It guards behaviour that was already right and does not
    reproduce the bug.
- **Red/green:** `template/tests/test_plan_advisory_split_children.py` (new, 4 tests).
  With the `leaves.py` change reverted to `main`, 3 tests fail with real assertion
  errors, not import or setup errors: the children get no review, and the closed bundle
  gets reviewed. With the fix, all 4 pass. An independent rerun that stashed and then
  restored the fix gave the same result.
- **Nothing else broke:** the existing `template/tests/test_plan_advisory.py` passes
  unchanged (29 tests across both files). That includes
  `test_default_off_leaves_the_plan_beat_untouched`, so Plan still does no review when no
  reviewer is configured. The full driver suite passes (1,792 tests, 2 skipped), and so do
  the root render/update suite and the docs lint.
- **Not covered:** no live interactive model session was run. The tests stand in for the
  planner with a fake that writes the same files a real split does.

Fixes #480
