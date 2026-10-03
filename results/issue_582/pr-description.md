## Summary
**User impact:** With the auto-merge wave mode turned on, a PR can be merged before all
of its CI checks have even started. Right after a PR opens, only the fast checks have
reported. If those passed, the PR looks green and gets merged. A slower test job that
starts a few seconds later can then fail on the base branch, and every later wave builds
on that broken base. If the slow job is a required check, the host refuses the merge
instead and the run stops for no real reason.

This PR makes merge mode check a second time: a green result must still be green one poll
interval (15 s) later before the PR is merged.

Reported in [#582](https://github.com/eduralph/pdca-harness/issues/582).

## What to look at
- The whole behaviour change is in one function, the wait that runs before each merge in
  `merge.py`. The rest of the diff is two config comments, a docstring, and tests.
- How to try it: the new tests feed a fake `gh pr checks` a list of results, one per read.
  Feed it "DCO passed" and then "DCO passed, e2e failed". On `main` the PR merges after the
  first read. With this change it is refused, the failing check is named, and the PR goes
  back to draft.
- One behaviour change to weigh: a `merge_wait_secs` below 15 now refuses every PR under
  `merge_requires = "all"`, because there is never room for the second read. With exactly
  15, a rollup that turns green only after one wait is refused too. `merge_wait_secs = 0`
  (no waiting at all) is unchanged.
- Not fixed here: the second read compares only the overall result, not which checks are
  present. A slow job that has not shown up within 15 s still gets through. Closing that
  needs a check-name comparison or a configured list of expected checks, which would be a
  separate change. So this narrows #582 but does not fully close it.

## Root cause
`_wait_for_green` keeps re-reading the check rollup only while it is `pending` or `empty`,
and returns the first `green` it sees (`template/src/pdca_harness/merge.py:155-160` on
`main`). A rollup read early only covers the checks registered so far, so that first
`green` can be partial, and `_merge_one` merges on it (`merge.py:229-231` on `main`).

## Fix
- `_wait_for_green` (`template/src/pdca_harness/merge.py:148-193`): when a read is green,
  sleep one full poll interval and read again. Return green only if the second read is
  green. A `pending`/`empty` second read goes back into the bounded wait; `failing` or
  `unreadable` returns at once (`:174-193`).
- If less than one poll interval of budget is left when a green is first seen, the green
  is returned as `pending` with the detail `green first seen with Ns of wait budget left,
  too little to confirm it 15s later (…)` (`:185-188`). The confirm sleep is never
  shortened, and the existing refusal message in `_merge_one` (`:268-269`) reads correctly
  with this detail.
- `merge_wait_secs <= 0` returns its single read unchanged (`:171-172`).
- The module docstring (`merge.py:39-43`) and the operator-facing comments for
  `merge_wait_secs` (`template/src/pdca_harness/config.py:380-385`,
  `template/pdca.toml.jinja:151-155`) describe the confirm rule and the 1–14 s case.

## Verification
- **Claim:** merge mode merges only after two green reads exactly one poll interval apart.
  **Checked:** `merge.py:189-193` is the only `return "green"` path when waiting is on, and
  it comes right after `_sleep(poll_interval)` following a green read (`:180-181`).
  **Test:** `test_a_merge_always_follows_two_greens_one_poll_interval_apart` sweeps budgets
  1–300 (both sides of each 15 s step) against six rollup sequences and checks, from a
  recorded read/sleep/merge timeline, that every merge follows two green reads 15 s apart.
- **Claim:** a partial green followed by a failing check does not merge.
  **Test:** `test_partial_green_then_failing_does_not_merge`. Returns 1, names `e2e (fail)`,
  runs `gh pr ready --undo`. On `main` it fails with `0 != 1` (merged after one read).
- **Claim:** a pending second read resumes the wait; merge happens only after the 4th read.
  **Test:** `test_partial_green_then_pending_merges_only_after_the_fourth_read`.
- **Claim:** total wait never exceeds `merge_wait_secs`, and a green that cannot get a full
  15 s confirm is refused with a message saying so.
  **Checked:** `merge.py:175-178` (pending loop capped at the budget) and `:185-190` (confirm
  taken only with a full interval left).
  **Test:** `test_budget_under_one_poll_interval_never_confirms_a_green` (budget 1),
  `test_green_with_under_a_poll_interval_of_budget_left_is_not_believed` (budget 20),
  `test_green_with_no_budget_left_to_confirm_is_not_believed` (budget 15),
  `test_wait_never_exceeds_the_bound_while_green_flickers`.
- **Claim:** `merge_wait_secs = 0` is unchanged.
  **Test:** `test_wait_bound_zero_returns_a_single_green_read_as_is`, plus the existing
  zero-wait test, which passes unmodified.
- **Claim:** nothing else changes. Only two existing tests were edited, on purpose:
  `test_pending_then_green_merges` now expects 4 reads, and
  `test_all_green_readies_then_checks_then_merges` expects `[ready, checks, checks, merge]`
  (`template/tests/test_merge.py:318-320`, `:342-344`). `merge._sleep` is patched once in
  `MergeWave.setUp` (`:80-86`) so no test sleeps for real.
- **Red/green:** all new tests are in `template/tests/test_merge.py:437-628`. With the
  production changes reverted to `main`: 92 failures (9 tests plus 83 sweep sub-cases).
  With the change: 33 tests OK. Full offline suite: root 24 tests OK, driver 2224 tests OK
  (2 skipped), in about the same time as on `main`.

Fixes #582
