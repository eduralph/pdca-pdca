## Summary
**User impact:** when you drive a batch of fixes and two fixes that run side by
side both change the same lines, the whole run stops partway through. Every fix
scheduled after that point is never built, even ones that have nothing to do with
the clash, and the error names only one of the two fixes and calls it a
"cross-wave" problem, so you can't easily tell what clashed with what.

This PR keeps the run going: only the later fix of the clashing pair (and the fixes
that depend on it) is set aside for this run. The run says which two fixes clash
and in which files, and at the end it suggests how to sort it out.

Reported in [#674](https://github.com/eduralph/pdca-harness/issues/674).

**Stacked on open PRs.** This branch is cut from the integration line that already
holds #683, #684, #685, #686 and #687 (it builds on #684's hold for `Conflicts with`
partners and on #685's `carried=` fold argument). Until those merge, the diff
against `main` also shows their changes; review the last commit.

## What to look at
- The fold now tests, one bundle at a time in its usual name order, whether a
  failed merge is a clash with the wave's own earlier bundles or with older work.
  Only the first kind is held; the second still stops the run, as today.
- To try it: drive a stack-mode batch with three independent bundles `10`, `11`,
  `12`, where `10` and `11` change the same line of one file, plus a second wave
  with `20` (`Depends on: 11`) and `21` (`Depends on: 12`). Before: "wave 0 did not
  integrate … STOPPING" and `21` is never built. After: `11` is held, `20` is
  skipped, `10`, `12` and `21` complete, and stderr names `issue_10`, `issue_11` and
  the file twice (before wave 1 builds, and at the end).
- The new test file runs this and seven related cases against real git with no
  host: `template/tests/test_flow_same_wave_conflict.py`.

## Root cause
The fold merges each accepted bundle's published branch onto the integration line
and treated any merge conflict as a reason to stop the run. Two bundles of the same
wave are built from the same base, so nothing checks them against each other until
the fold, and the fold could not tell a clash between them from a clash with
earlier work.

## Fix
- `integrate.fold` takes `held_out=` and `wave=`. It records the line's tip before
  the wave's first merge (`pre`) and the wave's bundles it has kept so far. When a
  wave bundle's merge raises the new `_Conflict` (a textual conflict, split out from
  other merge failures), `_held_by` decides the hold on trial merges:
  - the branch must merge cleanly onto `pre` (otherwise it clashes with earlier
    work, and the fold stops as before);
  - it must conflict when merged onto `pre` plus the kept bundles, in order
    (otherwise it clashes with something else the line took in, such as a newer
    base merged in for a PR that merged and deleted its branch, and the fold stops
    as before);
  - the partners named are the kept bundles it conflicts with one-on-one, or all of
    them if it only conflicts with several together; the files are the ones left
    conflicting by that trial.
- `_trial` runs those merges on a detached HEAD in the integration worktree, under
  the fold's lock, and always puts the tree back clean on the line's tip (raising
  if it cannot).
- `flow._drive_and_act` keeps a `held_conflict` record for the whole run, leaves
  those bundles out of every later fold, and passes them to `_runnable`, which
  holds their dependents and (new `conflict_held=` argument) their `Conflicts with`
  partners with a line saying why. Two stderr reports are added: one right after
  the wave's fold, one at the end of the run with the proposed `Conflicts with:`
  line. No brief is written.
- `_audit_wave_overlap`'s file-level warning is unchanged.
- Docs: `docs/07-crosscutting.md` and `template/PCDA/quality-cycle/09-parallel-lanes.md`
  describe the new hold and the cases that still stop.

## Verification
Line numbers are on this PR's branch.

- **Claim:** a same-wave clash holds only the later bundle and its dependents, for
  the whole run, and the run goes on.
  **Checked:** `template/src/pdca_harness/integrate.py:521-544` (wave bundles
  tracked, `_held_by` called only for a `_Conflict` of a wave bundle with at least
  one kept bundle); `template/src/pdca_harness/flow.py:2221`, `:2312-2316`,
  `:2445-2465` (run-wide `held_conflict`, excluded from every fold, passed to
  `_runnable`).
  **Test:** `test_a_same_wave_conflict_holds_the_later_bundle_and_the_run_goes_on`
  (three waves, so the second fold must also leave `11` out).
- **Claim:** a bundle is judged against bundles actually kept, not pair by pair.
  **Checked:** `integrate.py:884-908` (`_held_by`), `:911-941` (`_trial`).
  **Test:** `test_of_a_three_way_chain_only_the_bundle_that_conflicts_is_held`
  (A–B and B–C clash, A–C clean: only B held).
- **Claim:** sharing a file without a real conflict holds nothing.
  **Test:** `test_a_shared_file_that_merges_cleanly_holds_nothing`.
- **Claim:** the clash is named by pair and file, before the next wave and at the
  end, and no brief is edited.
  **Checked:** `flow.py:1079-1100` (`_announce_conflict_holds`,
  `_report_conflict_holds`), `:2490`.
  **Test:** asserted in the first case above.
- **Claim:** a `Conflicts with` partner of a held bundle is held too.
  **Checked:** `flow.py:740`, `:798-806`.
  **Test:** `test_a_conflicts_with_partner_of_a_held_bundle_is_held_too`.
- **Claim:** clashes with earlier-wave work, or only with a base merged in
  mid-wave, still stop the run.
  **Checked:** `integrate.py:884-908`.
  **Tests:** `test_a_conflict_with_earlier_wave_work_still_stops_the_run`,
  `test_a_conflict_only_with_a_base_taken_in_mid_wave_still_stops_the_run`,
  `test_a_base_taken_in_mid_wave_does_not_stop_a_same_wave_hold`.
- **Claim:** the integration worktree is left clean on the line after a hold.
  **Test:** `test_a_hold_leaves_the_integration_tree_clean_on_the_line`.
- **Red / green:** with the production changes reverted and the test kept, 5 of
  the 8 cases fail (the run stops with "did not integrate", or `fold()` rejects
  `held_out`); the 3 that pass are the "still stops" and "holds nothing" guards.
  With the change, all 8 pass. Full offline suites: root 24 tests OK, driver 2450
  tests OK (2 skipped). Docs lint and link audit OK.

## Known limits (left for follow-up)
- If the earlier bundle of a clashing pair has its PR merged and its branch
  deleted between publish and fold, it reaches the line through the base, so the
  clash still stops the run as before. This needs a draft PR merged within
  minutes, and the docs say so.
- A run whose only problem is a held bundle with no dependents exits 0, the same
  as the existing hold for a bundle that pushed no branch. The stderr lines are the
  only signal.
- Re-issuing the batch after a hold reaches the existing carry message, which
  still calls the clash "cross-wave" and suggests re-opening an already-open PR.

Fixes #674
