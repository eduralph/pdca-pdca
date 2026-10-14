## Summary
**User impact:** when you run a batch with `wave_mode = "merge"`, the run can mark ready
and merge a pull request it never opened. If one of the issues in the batch was set up to
add its fix as an extra commit on an existing PR (the brief's `Onto branch` field), that
whole PR, including someone else's work on it and whatever base it targets, gets merged
with no human approving it.

This PR makes merge mode stop at such an issue instead: it leaves the existing PR alone,
halts the remaining waves, and tells you why and what to do (run the batch in the default
`stack` mode, or take that issue out of the merge-mode batch).

Reported in [#658](https://github.com/eduralph/pdca-harness/issues/658).

## What to look at
The change is one early refusal in the per-PR merge step of merge mode, plus test updates.
It fires before anything touches the PR, so a dry run prints no merge for it and a PR that
already shows as merged is refused the same way. PRs the run opened itself are not
affected.

To try it: make a bundle that is accepted, has a patch, and has a `publish.json` of
`{"mode": "stacked", "branch": "feat", "base": "other/feat", "pr_url": "https://gh/pr/1",
"repo": "org/repo"}`, then call `merge.merge_wave(cfg, [b], method="merge")` with `gh`
stubbed. Before this change the stub records `gh pr ready https://gh/pr/1` and later
`gh pr merge`; after it, no `gh pr` call is made and the call returns non-zero with the
explanation on stderr. `template/tests/test_merge_onto_branch.py` does exactly this.

This deliberately reverses part of #650 (298503116ecebf81d3198ac6b71f9e38a8f2104a, merged
in #669): that change taught merge mode to fetch the remote an `Onto branch` record
names so it could go on to merge that PR. The fetch code is kept, but merge mode no
longer reaches it for these records.

## Root cause
`publish.publish` hands an `Onto branch` bundle to `_publish_stacked` before the merge-mode
base guard from #411 runs, and records the existing PR with `"mode": "stacked"`.
`merge._merge_one` then reads `pr_url` from that record and readies and merges it without
ever checking `mode`, while the merged-check and the fold already refuse to trust such a
record.

## Fix
- `template/src/pdca_harness/merge.py`, `_merge_one`: right after the "no recorded PR"
  check, if `rec.get("mode") == "stacked"`, print a STOP message to stderr and return 1.
  It sits above the dry-run return and the "already merged" skip, so both cases are
  refused too. The shape follows the existing `expected_checks_error` refusal: no `gh`
  call, nothing to undo. `merge_wave` already stops at the first non-zero, so `flow`
  prints its usual "wave k did not merge; STOPPING" line.
- The message names the bundle and PR URL, says it is an `Onto branch` commit on an
  existing PR that merge mode does not ready or merge, and offers `wave_mode = "stack"` or
  removing the bundle from the batch. It does not suggest merging the PR by hand, since a
  hand-merged record is refused the same way and would not let the run continue.
- Comments in `merge.py` (module docstring, `_remotes` docstring, the #650 inline comment)
  now say `_merge_one` refuses a `"stacked"` record before reading the head.
- `template/tests/test_merge_third_remote.py`: the cases that expected a `"stacked"` record
  to be readied, waited on or merged now assert the refusal. The cases about fetching a
  third remote and naming a missing head call `merge._base_read` directly with the record's
  `pub`, so that code stays tested. A positive case for "head found on the third remote"
  was added at that level. The `new-pr` cases are unchanged.

## Verification
- **Claim:** merge mode makes no `gh` call for a `"stacked"` record and stops the wave
  with a message saying why.
  - **Checked:** `template/src/pdca_harness/merge.py:463-494` on `main` (41210bc): `pr_url`
    read from the record at `:463`, then `gh pr ready` at `:493-494` with no `mode` check
    in between. The new refusal goes right after the `pr_url` check at `:465-468`.
  - **Test:** `test_merge_onto_branch.py::test_stacked_record_is_refused_before_any_gh_call`
    fails before the fix (returns 0 after readying and merging), passes after.
- **Claim:** a PR that already reads merged is still refused, not skipped.
  - **Checked:** `template/src/pdca_harness/merge.py:475-476` (the `is_merged` skip that
    the refusal now sits above); `template/src/pdca_harness/merged.py:104-110`
    (`merged_into` never counts a `"stacked"` record as merged).
  - **Test:** `…::test_stacked_record_already_merged_is_still_refused`, red before, green
    after.
- **Claim:** a dry run prints no merge plan for it.
  - **Checked:** `template/src/pdca_harness/merge.py:471-473` (the dry-run return the
    refusal now sits above).
  - **Test:** `…::test_stacked_record_dry_run_prints_no_merge_plan`, red before, green
    after. `…::test_wave_stops_at_the_stacked_member` also checks a later PR in the same
    wave is left alone.
- **Claim:** the record reaches merge mode without passing the #411 base guard.
  - **Checked:** `template/src/pdca_harness/publish.py:225-228` (dispatch to
    `_publish_stacked` before the guard at `:294`), `:549` (the `"mode": "stacked"`
    record); `template/src/pdca_harness/flow.py:2317-2318` (non-final merge-mode wave
    calls `merge.merge_wave`).
- **Claim:** PRs the run opened itself merge exactly as before.
  - **Test:** `…::test_new_pr_and_modeless_records_still_merge` (ready, then merge pinned
    to the head); `template/tests/test_merge.py` unchanged and passing; the `new-pr` cases
    in `test_merge_third_remote.py` unchanged and passing.
- **Suite:** full project suite passes with the fix (2427 tests, OK, 2 skipped). With the
  `merge.py` changes reverted and the tests kept, the four `"stacked"` cases in the new
  file and the refusal cases in `test_merge_third_remote.py` fail, and the `new-pr` case
  passes.

Fixes #658
