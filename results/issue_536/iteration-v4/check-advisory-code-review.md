# Advisory code review — correctness & reuse lens (issue #64 / #536, iteration 4)

Read the full diff against target `leaves.py`/`assemble.py`/`driver.py`/`state.py` plus
`template/tests/test_attempt_ownership.py`, ran that new file and the untouched
`test_leaf_resilience.py` directly against the checked-out patched tree (both green,
26/26 and 5/5), and re-read `gate-logs/C4-verify.log` (26 green with the fix, 19 fail +
4 error red with it reverted) and `gate-logs/T3-suite.log` (full driver suite green).

## Correctness

No new correctness bugs found in this iteration's mechanism. Specifically checked and
confirmed sound:

- `_invoke_leaf_resilient` (`leaves.py:673-780`): the ordering of quote-then-persist-
  then-withdraw (`:759-767`) closes the round-3 withdraw-before-persist window; the
  fail-closed re-flush on a refused withdrawal (`:768-769`) and the unconditional break
  on the last attempt (`:773`) are correct for every combination of `may_retry`/
  `recorded`/`owned` I traced by hand, including the terminal-attempt case where
  `_write_attempt_records` itself fails (the harvest sites' own `_settle_leaf_record`
  call after the placeholder acts as a backstop against a stale in-flight trailer in
  that case — verified by `test_a_failed_flush_leaves_no_stale_marker_beside_a_filed_failure`
  and its advisory/plan-advisory twin).
- `leaf_run_incomplete` / `_settle_leaf_record` (`leaves.py:898-972`): the whole-last-
  non-blank-line match is safe against a truncated `_residue_record` quote or a
  `_format_leaf_attempt` tail accidentally producing the exact marker text, because
  both quoting sites run through `_defang_in_flight` *before* truncation/embedding
  (`:1004-1011`, `:1046`) — I traced the truncation-boundary case (marker cut mid-string
  by `_RESIDUE_KEEP`) and it cannot reassemble into an exact match either.
- The three harvest sites (`:2837-2871`, `:3215-3232`, `:3520-3537`) are structurally
  identical in the ordering that matters (settle only after the placeholder that
  supersedes the log is filed) and match what the tests in
  `BothAdvisoryHarvestsAreAttemptAwareToo` actually drive.

One low-value, low-risk gap, not worth gating on: `_format_leaf_attempt`'s
"`(no output captured)`" fallback body (`leaves.py:1046` area, the `body = tail if tail
else f"(no output captured) {type(exc).__name__}: {exc}"` line) is **not** passed
through `_defang_in_flight` — only `tail` is. In practice this fallback fires for
harness-level plumbing exceptions (e.g. a `FileNotFoundError` from a misconfigured
`argv`), not leaf-controlled text, so it's outside the two channels criterion (iv)
actually names ("captured stderr" / "quoted artifact text") and I could not construct a
realistic path where `str(exc)` contains the literal marker. Noting it rather than
gating on it.

## Reuse / simplification

- The three harvest sites remain close to verbatim copies of each other (`err is not
  None` branch, `out.exists()` branch, the `_settle_leaf_record` calls) — a natural
  `_harvest_leaf(d, error_log, artifact, dest, unavailable_fn, ...)` extraction. This is
  already surfaced and explicitly deferred by iteration 3's carry-forward as an Act
  candidate ("prefer the minimal edit at each site over a refactor" — the diff is
  already large), so I'm not re-opening it as a fresh finding here, just confirming the
  duplication is still there and still intentional.
- The success-path re-flush in `_invoke_leaf_resilient` (`:745-746`) writes the exact
  same bytes (`records`, `in_flight=True`) that the immediately-preceding per-attempt
  flush already landed on disk — it's a no-op write on the happy/common path (harmless,
  and arguably a deliberate belt-and-suspenders against a torn read, but worth a
  one-line comment if Act ever revisits this function, since a future reader may assume
  it's load-bearing when the actual safety net is the earlier flush).

## Verdict

Diff is clean on both lenses to the depth I could check without vendor tooling. No
NEEDS-HUMAN findings.
