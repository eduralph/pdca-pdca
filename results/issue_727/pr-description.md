## Summary
**User impact:** When `pdca flow` runs several fixes for the same repo in stack mode,
each pull request it opens also contains the changes of other, unrelated fixes from
earlier in the run. Merging one PR quietly lands work the reviewer never looked at in
that PR, including work whose own PR the human had closed.

This PR builds each fix's branch on only the fixes it says it depends on (or conflicts
with), so its PR contains its own change plus exactly those, and nothing else from the
run.

Reported in [#727](https://github.com/eduralph/pdca-harness/issues/727).

**Merge order:** this builds on #723 (PR #726, still open). Until #726 merges, this PR's
diff against `main` also shows #723's change. Please merge #726 first; this diff then
shrinks to this change alone.

## What to look at
- **The new rule:** a fix that depends on fix A gets a branch holding A and nothing else.
  If an unrelated fix Z ran in the same earlier wave, Z is no longer in the PR. A fix with
  no dependencies starts from the real base.
- **What stays the same:** a fix whose dependencies reach something this run did not
  build (a fix carried in from an earlier run, an `Onto branch` or legacy `Stacks on`
  fix) still builds on the shared integration line, as before.
- **Messages when a dependency is force-pushed mid-run:** these now name the affected
  fix's own base branch and its PR to rebuild, rather than telling you to rebuild every
  PR cut from the shared line.
- **To try it:** run the new test module (below). The first test is the reported case:
  A and Z in wave 0, B depends on A. B's branch holds A's commits and none of Z's.

## Root cause
Before each wave, `_point_at_integration` wrote the run's single integration line into
every runnable bundle's stack base. That line accumulates every earlier wave's bundles for
the target, so what a bundle was built on depended on when it was scheduled, not on what
it declared.

## Fix
- `template/src/pdca_harness/flow.py:913` `_closure_members`: walks a bundle's declared
  edges (`Depends on`, in-batch `Depends on (merged)`, transitively, plus earlier-wave
  `Conflicts with` partners) through bundles this run built. It returns `None` at a seam
  (carried bundle, `Onto branch`, legacy `Stacks on`, carried conflict partner).
- `flow.py:961` `_bundle_bases`: for each runnable bundle, builds its own base with
  `integrate.build_bundle_base` (from #723) from those members. An empty set clears the
  stack base. A seam falls back to `_point_at_integration` (`flow.py:1005`). Wired in at
  `flow.py:2685-2699`. A base that cannot be built stops the run with one line, as a
  failed fold does.
- `flow.py:1015` `_heads_taken`: records which prerequisite head each base and each
  line-cut PR took. Only bundles that actually pushed a branch count.
- `template/src/pdca_harness/integrate.py:1199` `rewritten_carried`, with `_takers`
  (`:1062`), `_rewrite_stop` (`:1128`), `_base_rewrite` (`:1188`) and
  `_late_line_rewrite` (`:1276`), plus `flow.py:2855` `_report_late_rewrites`: the
  force-push checks at the next fold and at the end of the run compare each base against
  the head *it* took. For a bundle on its own base, the message names that base
  (`bundle_base_branch`, `integrate.py:155`), that head, and that bundle's PR. The line
  keeps today's report and names only the PRs cut from it. The "cannot fetch" path is
  split the same way.

## Verification
Line numbers are on this PR's branch (`fcae4aa` with the patch applied).

- **Claim:** a dependent holds its prerequisite and nothing of an unrelated bundle (the
  reported case). **Checked:** `flow.py:913-1013`. **Test:**
  `template/tests/test_flow_dependency_scoped_bases.py:263`.
- **Claim:** prerequisites reached through another prerequisite are on the base.
  **Test:** `:278`.
- **Claim:** an earlier-wave `Conflicts with` partner is on the base, and a partner built
  after the member is not. **Tests:** `:309`, `:318`.
- **Claim:** an in-batch `Depends on (merged)` prerequisite is on the base. **Test:**
  `:333`.
- **Claim:** a bundle whose only prerequisite produced no patch is built on the real
  base. **Test:** `:344`.
- **Claim:** the walk goes only through bundles this run built (a partner that never
  completed brings nothing of its own prerequisite). **Test:** `:359`.
- **Claim:** seams keep the line, unchanged: carried `Depends on`, carried
  `Conflicts with`, `Onto branch`, legacy `Stacks on`. **Tests:** `:375`, `:392`,
  `:409`, `:422`.
- **Claim:** force-push reports name each own base, the head it took, and its PR. The line
  is still reported with the line-PR remedy. **Checked:** `integrate.py:1128-1291`,
  `flow.py:2855-2919`. **Tests:** `:467` (end of run), `:485` (next fold), `:503` (a later
  base build), `:665` (cannot fetch), plus `:576-640` for heads taken more than once and
  several lost heads.
- **Claim:** a bundle that pushed no branch is never named and never stops the run; a
  bundle on another target is neither a member nor named. **Tests:** `:729`, `:743`,
  `:756`.
- **Red → green:** with the production changes reverted and the tests kept, 21 of the 25
  new tests fail on assertions. The 4 that pass are the seam tests, which check that the
  old behaviour is kept. All pass with the fix.
- **Existing suites:** green (driver suite 2,581 tests). Seven suites that asserted "built
  on the line" were restated to say what the base *contains*, never weaker. One test,
  `test_flow_slice.py` `test_a_dependent_carries_every_earlier_wave_branch_…`, pinned the
  bug itself and is inverted to
  `…_carries_only_its_prerequisite_not_every_earlier_wave_branch` with the same input.

## For the reviewer to weigh
- Per-bundle bases start from a freshly fetched `origin/main` (as #723's builder does),
  so a commit that lands on `main` mid-run can enter a dependent's PR even though the line
  does not follow it.
- `regate_between_waves` re-gates only the line's tip, not these per-bundle bases.
- The patch is about 132 KiB, mostly tests (the new test module alone is 42 KB).

Fixes #727
