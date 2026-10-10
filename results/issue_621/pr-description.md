## Summary
**User impact:** in merge mode, the harness can merge a PR before all of its CI has
run. If a slow job (say an end-to-end suite) has not shown up on the PR yet, the harness
sees only the fast checks, sees them pass twice, and merges. The next wave then builds on
a base that was never fully tested. The same thing happens if the set of checks changes
between the two reads: the harness counts that as "still green" even though it never saw
the new checks pass twice.

This PR makes the harness compare *which* checks it saw, not just whether they passed, and
adds an optional `[driver].expected_checks` setting so an operator can name the checks a
PR must have before it can merge.

**This narrows #621; it does not close it for the default setup.** With nothing declared
in `expected_checks` (the default), a job that shows up more than one poll interval
(15 s) after the fast ones still gets through, because the harness cannot see a check
that does not exist yet. The full "refuse until every check has run" behaviour holds only
for operators who list their slow checks. Working out that list automatically (from branch
protection or workflow files) is out of scope here.

Reported in [#621](https://github.com/eduralph/pdca-harness/issues/621).

## What to look at
- The change is in the merge-mode wait loop: the second ("confirm") read now has to see
  the same checks as the first, and a missing declared check counts as "still running".
- The new setting is documented in the rendered `pdca.toml` comment block next to
  `merge_wait_secs`, and in the merge-mode paragraph of `docs/07-crosscutting.md`.
- To try it: set `expected_checks = ["dco", "e2e"]` under `[driver]` and run a merge wave
  on a PR where only `dco` has reported. The PR is not merged; it is put back to draft with
  a message naming `e2e`. Without the setting, the same PR merges as it does today.
- Behaviour with nothing declared and an unchanged check set is the same as before.

## Root cause
`_check_rollup` returned only `(verdict, detail)`, dropping the check names, so the
confirm added for #582 (b2740ea030ba3d2fd37abe6d1f5c9b3cf8a56545) could only compare two
verdicts. Its own docstring said so (`template/src/pdca_harness/merge.py:192-194` on
`main`): "This compares verdicts only, not check names: a slow job that has not
registered within one poll interval still gets through."

## Fix
- `template/src/pdca_harness/merge.py`
  - `_check_rollup` now also returns `names`: the sorted tuple of every reported check
    name, one entry per check, so `==` compares them as a multiset (`build` listed twice
    differs from `build` once).
  - New `_read_rollup(pr_url, expected)` wraps it: a green read that lacks a declared name
    is returned as `pending` with a detail like `expected check e2e not reported yet (1
    check reported)`. Since a green read holds only passed or skipped/neutral checks, a
    skipped declared check does not block.
  - `_wait_for_green` takes `expected=()`, routes every read (including the single read of
    `wait_secs <= 0`) through `_read_rollup`, and confirms only when the confirm read is
    green **and** lists the same names. A green over a different set becomes the new first
    green and goes through the existing budget rule (a confirm is a full poll interval
    later or not at all; never past `merge_wait_secs`).
  - `_merge_one` passes `cfg.expected_checks` to the wait, and refuses up front (before
    marking the PR ready) when the setting was malformed.
- `template/src/pdca_harness/config.py`: new `expected_checks` / `expected_checks_error`
  fields, parsed next to `merge_wait_secs`. A bare string is one name; a list of non-blank
  strings is stripped and de-duplicated; anything else warns on stderr and fails closed
  (every PR refused, naming the setting), the same way a bad `merge_requires` falls back
  to the stricter value rather than the weaker one.
- `template/pdca.toml.jinja`: a commented-out `expected_checks` block after
  `merge_wait_secs`, so the rendered default stays empty.
- `docs/07-crosscutting.md`: the merge-mode bullet describes the same-set confirm, the
  setting, and the remaining gap.

## Verification
- **Claim:** with `expected_checks = ["dco", "e2e"]`, reads of only `dco` never confirm
  green; the wait ends pending naming `e2e`, nothing is merged, and the PR goes back to
  draft. Once `e2e` passes, two matching reads merge it. A skipped `e2e` does not block.
  - **Checked:** `template/src/pdca_harness/merge.py:172-224` on `main` (`_wait_for_green`
    believes any second green read) and the refusal / undo-ready path at
    `merge.py:452-469`.
  - **Tests:** `test_declared_check_that_never_registers_never_reads_green`,
    `test_declared_check_missing_refuses_the_merge_and_undoes_ready`,
    `test_declared_check_that_registers_and_passes_merges_after_two_same_reads`,
    `test_declared_check_that_is_skipped_does_not_block`.
- **Claim:** the declared list also applies with `merge_wait_secs = 0` (single read).
  - **Checked:** `merge.py:201-203` on `main` returns the one read as-is.
  - **Test:** `test_declared_check_applies_to_the_single_read_of_wait_zero`.
- **Claim:** with nothing declared, a confirm read over a different set of checks (or the
  same name a different number of times) is not a confirmation; a later read over the
  same set confirms it.
  - **Checked:** `merge.py:220-224` on `main` (the confirm tests `verdict == "green"`
    only).
  - **Tests:** `test_confirm_read_over_a_different_set_is_not_a_confirmation`,
    `test_names_are_compared_as_a_multiset`.
- **Claim:** unchanged when nothing is declared and the set is stable (`dco` → `dco`
  still merges).
  - **Test:** `test_same_set_with_nothing_declared_still_confirms`; every existing
    `test_merge.py` test still passes.
- **Claim:** the setting parses from `pdca.toml`, defaults to empty, accepts a bare
  string, and a malformed value warns and refuses every PR instead of merging.
  - **Checked:** `template/src/pdca_harness/config.py:728-732` on `main` (the
    `merge_requires` fail-closed precedent) and `:737-746` (`merge_wait_secs` parsing).
  - **Tests:** `test_expected_checks_comes_from_the_driver_table`,
    `test_malformed_expected_checks_fails_closed_in_merge_mode`.
- **Red/green:** all ten tests are in `MergeConfirmRequiresCompleteRollup` in
  `template/tests/test_merge.py`. With the production changes reverted and the tests kept,
  the class fails (2 behaviour failures: `main` confirms `dco` → `dco, e2e` and `build` →
  `build, build`; 7 errors from the new parameter/setting not existing). With the change,
  all pass.
- **Wider suites:** root render + update-compat suite (24 tests) and the driver suite
  (2379 tests, 2 skipped) pass; the docs lint and link audit are clean.

Fixes #621
