## Summary
**User impact:** In a stacked `pdca flow` run, if a PR branch the run has already
folded is rewritten while the run is going (most often by running `pdca publish <id>`
for that bundle in another terminal, which force-pushes), the next wave quietly builds
on a line that holds both the old and the new version of that work. Or it fails with a
conflict that wrongly blames an overlap between bundles. Nothing tells you a branch was
rewritten, and every later wave builds on the bad line.

This PR makes the run stop at the next fold, before anything is merged or pushed. The
message names the bundle and branch and says how to recover.

Reported in [#633](https://github.com/eduralph/pdca-harness/issues/633).

## What to look at
- The crux is a new check at the start of each in-run fold. For every branch this run
  already put on the line, the branch must still contain the commit the line took from
  it. A branch that only moved forward (new commits on top, or GitHub's merge-style
  "Update branch") is merged as before. A branch whose history was replaced stops the
  run.
- **Behaviour change:** a contributor who updates a carried PR branch with "Update with
  rebase" or a force-push during a run now stops that run. Before, the rewrite was
  merged in silently.
- Unchanged: the pre-wave carry of finished prerequisites, and branches deleted after
  their PR merged.
- To try it: start a stacked flow run. After wave 0 folds, force-push one of its PR
  branches to a commit cut from `main`. The fold after the next wave stops with
  `issue_<id>'s branch origin/fix/<…> was rewritten after this run folded it …`.
  The new tests below do this offline with real git.

## Root cause
The fold merges each published branch's *current* tip and skips it only when that tip
is already in the line (`integrate._merge_published`, `template/src/pdca_harness/integrate.py:494-502`
on `main`). `publish` re-publishes with `git push --force-with-lease`
(`template/src/pdca_harness/publish.py:310-319`, needed for #108), and the single-step
`pdca publish` takes no drive claim (#573). So a rewritten branch's new tip is not in the
line and gets merged on top of the old commits.

## Fix
- `integrate.fold` takes an optional `carried` mapping (bundle → the head a fold of this
  run put on the line). It is filled in place, like `skipped`, and only after that
  target's push succeeds.
- A new `_carried_tips` runs before any target merges or pushes. It fetches, reads each
  carried branch's tip once, and requires the recorded head to be that tip or an
  ancestor of it. The check uses ancestry only, never a commit message, and a git
  failure raises (the existing `_in_line`). The tip it read is the exact commit merged,
  and `_merge_published` now receives it instead of reading the branch again. So a
  later fetch for another base in the same checkout, or a push from that checkout,
  cannot swap in a commit that was never checked.
- The fold's own fetch still runs under the integration lock. A line moved by another
  run is still refused with the #591 "moved" message.
- `flow._drive_and_act` creates one mapping per run and passes it through `_fold_lines`
  to the in-run fold. The pre-wave carry (#646) passes none, so it behaves as before.
- Module and `IntegrationError` docstrings, plus the matching sentence in
  `docs/07-crosscutting.md`, now say that only commits that extend a carried branch
  reach the line.

## Verification
Line numbers are on `main` @ `41210bcd18e0b6d1b77fd5fe6e29c2bbebb6fa57` ("base") or in
the patched tree, which applies cleanly onto it.

- **Claim:** a carried branch rewritten mid-run stops the fold before any merge or push.
  The line stays at its previous tip, and the message contains `issue_A`, `fix/A`,
  `rewritten` and how to recover.
  - **Checked:** `template/src/pdca_harness/integrate.py:414` (check before the per-target
    loop), `:526-563` (`_carried_tips`).
  - **Test:** `test_a_carried_branch_rewritten_mid_run_stops_the_fold`
    (`template/tests/test_integrate_stack_bases.py:1185`). It fails before the fix
    (`IntegrationError not raised`) and passes after. A spy confirms that no
    `git merge`/`git push` ran.
- **Claim:** a rewrite that conflicts is reported as a rewrite, not as a cross-wave
  overlap.
  - **Test:** `test_a_conflicting_rewrite_is_named_a_rewrite_not_an_overlap` (`:1210`).
    Before the fix it got the old "undeclared cross-wave overlap" message. It passes
    after.
- **Claim:** the commit checked is the commit merged, even when another base's fetch in
  the same checkout refreshes the branch mid-fold.
  - **Checked:** `integrate.py:492` (merge uses the checked SHA) and the
    `_merge_published` signature change (base `:494-502`).
  - **Test:** `test_a_rewrite_between_two_targets_fetches_never_reaches_the_line`
    (`:1275`). It injects a real force-push between two real fetches. The rewrite never
    reaches the line, and the next fold refuses it. Fails before the fix, passes after.
- **Claim:** the record is shared across a real run's folds.
  - **Checked:** `template/src/pdca_harness/flow.py:2148`, `:2352`, `:817`.
  - **Test:** `test_a_run_stops_when_a_branch_it_carried_is_rewritten` (`:1343`). A real
    `flow._drive_and_act` runs three waves, and fix/A is re-published during wave 1.
    The run stops after wave 1 and wave 2 never runs. Fails before the fix, passes
    after.
- **Claim:** these paths are unchanged:
  - fast-forward fixups are still merged and recorded (`:1224`, plus the existing
    `test_a_fixup_pushed_onto_a_live_branch_is_merged_by_the_next_fold`);
  - the pre-wave carry with no record merges as before (`:1244`);
  - deleted branches are still judged as gone (`:1255`);
  - a line moved before the lock is taken still gets the #591 refusal (`:1315`).
  - **Test:** all of the above pass with and without the fix. Mutation runs confirmed
    that the two-base test catches a fold that re-reads the branch, and the moved-line
    test catches a fold that skips its own fetch under the lock.
- **Suite:** with the fix, `test_integrate_stack_bases` runs 62 tests OK. With the
  production hunks reverted (test kept), it fails 4, all on assertions. The full offline
  suite passes (2431 driver tests, 24 root tests). The docs check is clean.

**Known limits:** the new up-front fetch runs outside the integration lock (fail-closed:
a ref-lock clash stops the fold with "could not fetch"). A rewrite that lands *during* a
fold is caught at the next fold, so one that lands during the run's last fold is not
caught by that run.

Fixes #633
