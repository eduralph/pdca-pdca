## Summary
**User impact:** A run in `wave_mode = "merge"` stops almost every time it reaches a
wave boundary. The wave's PRs are opened and then merged seconds later, before CI has
reported anything, so the run sees "no check has finished yet", treats that as a
failure, refuses to merge and stops — leaving the PR it was about to merge marked
ready-to-merge (a readiness nobody granted) and every later fix in the wave untouched.
Nothing was actually wrong: the evidence had simply not arrived yet.

This makes the merge boundary wait for the checks to report, bounded by a new
`[driver].merge_wait_secs` (default 300s; `0` keeps today's behaviour), and return any
PR it declines to merge back to draft before it stops.

Reported in [#462](https://github.com/eduralph/pdca-harness/issues/462).

## What to look at
Two behaviours, both at the wave-merge boundary in `template/src/pdca_harness/merge.py`:

- **The wait** — a new `_wait_for_green` re-reads the PR's check rollup while it is
  pending or empty, until it resolves or the configured budget is spent. Waiting is what
  makes "the checks have not reported *yet*" distinguishable from "the checks say no".
- **The undo** — every path that declines to merge a PR it had already marked ready now
  marks it back to draft first, so a stopped run leaves the PRs as it found them.

You can exercise both offline — no `gh` binary, no network, no merge rights — from
`template/`:

    PYTHONPATH=src python3 -m unittest tests.test_merge -v

The suite stubs every `gh` call and asserts the exact sequence of commands the boundary
shells, so "pending, pending, then green ⇒ merged" and "declined ⇒ returned to draft"
are ordinary assertions that run instantly.

Worth a maintainer's opinion: the default budget (300s) and the fixed 15s poll cadence —
whether those match how long this repo's checks really take to register on a fresh PR.

## Root cause
`_merge_one` runs `gh pr ready`, the check-rollup gate and `gh pr merge` back to back
with no wait anywhere (`template/src/pdca_harness/merge.py:158-204` on `main`), so a PR
created seconds earlier is judged on a rollup that is still `pending` (queued or running)
or `empty` (nothing registered yet); the run returns non-zero and later waves never run —
absence of evidence recorded as a verdict. Separately, the ready-mark at
`template/src/pdca_harness/merge.py:158-159` precedes both refusal paths (`:192`, `:204`)
and is never reversed, so declining to merge also leaves the PR non-draft.

## Fix
- **`_wait_for_green`** re-reads the rollup while the verdict is `pending`/`empty`,
  polling until it resolves or `[driver].merge_wait_secs` is exhausted. The
  classification itself (`_check_rollup`) is untouched — the wait keys off the buckets it
  already produces. Sleeps go through a module-level `_sleep`, so tests drive the loop at
  zero wall-clock cost. `merge_wait_secs = 0` performs exactly one read: today's
  behaviour, kept as a documented opt-out.
- **`_undo_ready`** runs `gh pr ready --undo` on every path that declines to merge a PR
  it readied — the rollup refusal (failing, unreadable, or still unresolved at the bound)
  and a failing `gh pr merge`. Paths that never readied anything (dry-run, already merged,
  a `gh pr ready` that itself failed) undo nothing. A failed undo is reported and never
  masks the real reason the run stopped.
- The two "evidence never arrived" refusals now say `within <N>s`; `a check is FAILING`
  is unchanged. A red check remains an immediate stop — nothing retries a failing check.
- `[driver].merge_wait_secs` is plumbed through `Config` exactly as `merge_requires` is
  (`template/src/pdca_harness/config.py:367-368`, `:703-707`, `:813` on `main`) and
  documented beside it in the `[driver]` block of `template/pdca.toml.jinja`. A
  malformed or negative value warns and falls back to the 300s default rather than to
  `0`, so a typo cannot silently restore the old race.

One nuance for the reviewer: the budget accumulates the time the loop spends sleeping
rather than reading a monotonic deadline, so a very slow `gh pr checks` can overshoot the
configured limit by the cumulative latency of its own calls. Bounded, but not to the
second; a deadline-based variant is a small follow-up if that matters here.

## Verification
- **Claim:** a rollup that is pending only because CI has not reported yet is waited on,
  and the PR merges once it turns green.
  **Checked:** `template/src/pdca_harness/merge.py:176-192` on `main` — the single
  `_check_rollup` read whose result fed straight into the refusal branch; it now goes
  through the bounded wait.
  **Test:** `template/tests/test_merge.py` — `test_pending_then_green_merges` (rollup
  pending, pending, then green ⇒ `gh pr merge` runs, no undo). Fails pre-fix.
- **Claim:** a rollup that never reports within the budget — and a failing or unreadable
  one — still refuses, still stops the run, and says which of the two happened.
  **Checked:** `template/tests/test_merge.py:252-258` on `main` — the existing
  `test_pending_check_refuses`, which asserted the immediate refusal that *is* the bug;
  it now asserts the refusal after the bound, and the `within <N>s` wording.
  **Test:** `test_pending_check_refuses`, `test_wait_bound_zero_performs_no_wait`,
  `test_failing_check_refuses_and_never_merges`. All fail pre-fix.
- **Claim:** no PR is left marked ready when the run declines to merge it.
  **Checked:** `template/src/pdca_harness/merge.py:158-204` on `main` — the ready-mark at
  `:158-159` and the two post-ready returns at `:192` and `:204`; `gh pr ready --undo`
  appears nowhere in the file on `main`.
  **Test:** the undo assertions in `test_pending_check_refuses`,
  `test_failing_check_refuses_and_never_merges`, `test_merge_failure_stops` and
  `test_check_triggered_by_the_ready_mark_is_caught`; `test_pending_then_green_merges`
  asserts the converse — a successful merge undoes nothing.
- **Claim:** the new setting actually reaches the merge boundary and fails safe.
  **Checked:** `template/src/pdca_harness/config.py:367-368`, `:703-707`, `:813` on
  `main` — the `merge_requires` plumbing this mirrors.
  **Test:** `test_merge_wait_secs_comes_from_the_driver_table` drives the real config
  loader: a set value arrives, an unset one defaults to 300, and an unparseable or
  negative one warns and falls back to 300 (never 0).
- **Claim:** the rest of merge mode is unchanged — dry-run shells nothing, a skipped or
  already-merged PR is untouched, a PR-less entry still fails closed, and
  `merge_requires = "required"` still skips the rollup gate.
  **Checked:** the remaining cases in `template/tests/test_merge.py` are unmodified.
  **Test:** `tests.test_merge` — 6 failures with `merge.py` reverted and the tests kept,
  24/24 green with the patch (0.014s, no real sleeping either way); the full offline
  driver suite (1761 tests) is `OK (skipped=2)`.

Fixes #462
