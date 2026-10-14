## Summary
**User impact:** When you resume a stacked run, a prerequisite fix finished in an
earlier run can bring along a commit nobody reviewed. If someone pushed to its branch
after the PR was approved or merged, that commit quietly ends up under every fix that
depends on it, and nothing tells you.

This PR makes the run check that the branch is still at the PR head it reviewed. If it
is not, the run holds the dependent fixes, prints one line saying which commit is where
and what to do, and goes on with the rest.

Reported in [#653](https://github.com/eduralph/pdca-harness/issues/653).

## What to look at
The change is one extra check in the step that decides whether a finished prerequisite
is safe to carry, plus a new piece of advice text for when it is not. A merged branch
that later took in the base branch ("Update branch" on GitHub) is also held. That is on
purpose: it fails safe instead of guessing which commits are harmless.

To try it: finish a fix `P`, merge its PR, push one more commit to its branch, then
resume a run with `P`, a fix `D` that depends on `P`, and an unrelated fix `U`. Before
this change `D` is built on top of the extra commit. After it, `D` is held with a
message naming both commits, and `U` is still built. The two new tests in
`template/tests/test_flow_resume_stack_prereqs.py` do exactly this against real git.

## Root cause
`flow._finished_head` judges a prerequisite clean from the PR's `headRefOid`, but the
fold then merges `origin/<branch>`, the branch's current tip. Nothing compared the two,
so any commit past the judged head was carried without review.

## Fix
- `flow._finished_head`: as the last check, resolve the published branch ref (the same
  ref the fold merges) in the carry's own fetched checkout. If it resolves and is not the
  judged head, return a not-clean reason naming the branch, its tip and the judged head.
  This goes through the same `(reason, hint)` path as every other not-clean case, so
  there is no new control flow. A branch that no longer exists after a merge is
  unchanged.
- `_CARRY_HINTS["tip"]`: new advice: reset or delete the branch to the judged head, or
  open a PR for the commits after it, then re-issue. The hint string carries the judged
  head as `tip:<sha>`, and the `.format(...)` call passes it through.
- `docs/07-crosscutting.md`: the "Only a clean prerequisite is carried" rule now says
  the branch must still be at the PR head, including the "Update branch" case.

Not covered: a push that lands in the few seconds between the carry's read and the
fold's own fetch is still merged. Closing that would mean passing the expected head into
the fold.

## Verification
- **Claim:** a finished prerequisite is carried only when its branch tip is the PR head
  that was judged; otherwise its dependents are held and named, and the run goes on.
- **Checked:** `template/src/pdca_harness/flow.py:836-857` on `main` (`_finished_head`):
  every existing not-clean case returns `(reason, hint)`, and none compares the branch
  tip with `head`. The new check sits after the MERGED check at `:857`.
- **Checked:** `template/src/pdca_harness/integrate.py:494-502` on `main`
  (`_merge_published`): the fold resolves and merges the branch ref, not the PR head.
  That is the gap.
- **Checked:** `template/src/pdca_harness/integrate.py:154` (`_published_ref`) and
  `:200` (`carry_view`) on `main`: the new check compares against the same ref the fold
  merges, resolved in the checkout the carry already fetched.
- **Checked:** `template/src/pdca_harness/flow.py:860` and `:995` on `main`: the hint
  table and the `.format(...)` call that print the held line.
- **Checked:** `docs/07-crosscutting.md:690` on `main`: the user-facing rule for what
  is carried, now updated to match.
- **Test:** `template/tests/test_flow_resume_stack_prereqs.py`
  - `test_a_merged_prerequisite_pushed_to_after_the_merge_is_not_carried`
  - `test_an_open_prerequisite_whose_head_moved_since_the_read_is_not_carried`

  Both fail without the fix (`D` is built on a line holding the extra commit) and pass
  with it. They check that `D` is held with one message naming both commits and the
  advice, that no integration line on origin holds the extra commit, and that `U` is
  still built. Every existing test in the file still passes, including the plain carry
  case where the tip is the reported head. The full offline suite passes, and so do the
  docs lint and render checks.

Fixes #653
