# Build notes — issue 582 / merge-wait-confirms-green

Target: eduralph/pdca-harness @ main (worktree base `24c7f83`). Line numbers below are in
the patched worktree unless marked "main".

## What changed

- `template/src/pdca_harness/merge.py:147-187` — `_wait_for_green` (main `:143-160`).
  - `:167-169` one read; `wait_secs <= 0` returns it as-is (criterion iv, unchanged).
  - `:171-176` the old bounded pending/empty loop, now inside an outer loop.
  - `:177-178` anything not green (failing/unreadable, or pending/empty at the bound)
    returns at once.
  - `:179-181` green with `waited >= wait_secs` → `("pending", "green first seen with no
    wait budget left to confirm it (<n> checks)")` (criterion iii). `_merge_one`'s existing
    `pending` message (`merge.py:262-263`) then reads "a check has not finished within Ns —
    green first seen with no wait budget left to confirm it (2 checks)".
  - `:182-187` confirm: sleep `min(poll_interval, remaining)`, charged to `waited`, re-read.
    Green → return it. Anything else falls back to the top of the outer loop: pending/empty
    re-enter the wait, failing/unreadable return at once (criterion ii).
  - Bound: every `_sleep` is `min(poll_interval, wait_secs - waited)` and is added to
    `waited`, so the sum of sleeps never exceeds `wait_secs`. The outer loop terminates
    because every pass either returns or sleeps a positive step (`waited < wait_secs` is
    guaranteed at each sleep).
  - Docstring `:148-166` and module docstring `:36-45` updated, including the residual
    (verdicts are compared, not check names).
- `template/src/pdca_harness/config.py:375-385` — `merge_wait_secs` comment (main `:375-381`).
- `template/pdca.toml.jinja:144-155` — operator comment (main `:144-151`); 4 added lines,
  all above `merge_wait_secs = 300`, so #593's hunk near main `:176` stays separate.
- `_check_rollup`, `_merge_one`, the `merge_requires = "required"` skip and the ready-undo
  are untouched (criterion v).

## Test — `template/tests/test_merge.py`

- `setUp` (`:80-86`) patches `merge._sleep` for the whole class via `mock.patch.object`
  + `addCleanup(stop)`. Without it four tests would sleep a real 15 s each after the fix.
  Driver-suite wall time: 46.1 s pre-fix, 47.2 s post-fix (noise), so no real sleep.
- Updated on purpose (only these two): `test_pending_then_green_merges` (`:296`, now 4
  reads) and `test_all_green_readies_then_checks_then_merges` (`:338`, now
  `[ready, checks, checks, merge]`).
- New cases (`:437-546`), all through `merge.merge_wave` with `subprocess.run` patched:
  - `test_partial_green_then_failing_does_not_merge` — the brief's repro: `green(dco)` →
    `failing(e2e)` → no merge, rc 1, "e2e (fail)" named, `gh pr ready --undo` called, only
    2 reads.
  - `test_partial_green_then_pending_merges_only_after_the_fourth_read` — (i)/(ii) probe;
    asserts the full gh sequence `ready, checks×4, merge`.
  - `test_confirm_read_unreadable_returns_at_once` — (ii).
  - `test_green_with_no_budget_left_to_confirm_is_not_believed` — (iii) with
    `merge_wait_secs = 15`: refused, stderr has "not finished within 15s" and the exact
    detail text, slept ≤ 15.
  - `test_wait_never_exceeds_the_bound_while_green_flickers` — (iii) bound with
    green/pending alternating, budget 100.
  - `test_wait_bound_zero_returns_a_single_green_read_as_is` — (iv) for green (the existing
    `:325` test covers pending). This one passes pre-fix too; it is a guard, not a red.
- Only existing API used (`merge.merge_wave`, `merge._sleep`); no new module-level imports.

## Red → green (project runner `engine/scripts/run-suite.sh`, under `timeout 900`)

- Pre-fix (tests applied, `merge.py` at main): driver suite `FAILED (failures=7)` — the 6
  new/updated binding tests plus `test_all_green_readies_then_checks_then_merges`; the root
  suite's `test_render_then_slice` also failed because it runs the rendered template's
  suite, which includes the same file.
- Post-fix: `PDCA-EVIDENCE: root suite OK, driver suite OK` (2221 tests, OK, skipped=2).

## Refutation

- **(a) Genuine red?** Yes. The pre-fix run above is exactly "fix reverted": tests in
  place, production `merge.py`/`config.py`/`pdca.toml.jinja` at main. Seven failures,
  including the brief's repro (`test_partial_green_then_failing_does_not_merge`: on main
  rc was 0 and `gh pr merge` was called after one read).
- **(b) Production path?** Yes. Every new test calls the public `merge.merge_wave`, which
  runs the real `_merge_one` → `_wait_for_green` → `_check_rollup` (real JSON parsing and
  bucket classification). Only the process boundary (`subprocess.run`), `_sleep`, bundle
  state and the merged-lookup are patched, the same as the existing tests.
- **(c) Fixture includes the fault?** Yes. The fault is a partial rollup that is green on
  the fast check only; the fixtures feed exactly that (`[dco pass]`) followed by the slow
  check's real outcome (`e2e fail` / `e2e pending`), not a curated all-green rollup.

## Alternatives ruled out

- Comparing check names/counts between reads, or a configured expected-check list: out of
  scope per the brief. Residual stays: `green(dco)` → `green(dco)` still merges if the slow
  job has not registered within one poll interval. Check should not count the issue as
  fully closed.
- Requiring the confirm to be a full `poll_interval` even when less budget remains: would
  break the "sum of sleeps ≤ merge_wait_secs" bound in (iii). Used
  `min(poll_interval, remaining)` instead, the same rule the existing loop uses.

## Commit-readiness

The target has no formatter or pre-commit config (no ruff/black/flake8 in
`template/pyproject.toml.jinja`, `template/Makefile`, `.github/workflows/`, no
`.pre-commit-config.yaml`). `git diff --check` is clean; no new line exceeds 100 columns
(the only one in the touched files is pre-existing, `config.py:809` on main).

Housekeeping: the pre-fix suite log was written to `/tmp/pdca582-red.log` (my mistake —
outside the given roots); the post-fix log is `results/issue_582/.suite-green.log`.
