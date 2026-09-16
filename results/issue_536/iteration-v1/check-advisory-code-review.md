# Check advisory — code review (correctness bugs + reuse/simplification)

Read against target `template/src/pdca_harness/leaves.py` / `driver.py` (issue #536,
attempt-owned leaf records and harvests). Traced the wrapper (`_invoke_leaf_resilient`,
`leaves.py:673-761`), the new helpers (`_write_attempt_records`, `leaf_run_incomplete`,
`_leaf_ran_and_failed`, `_withdraw_residue`, `_defang_in_flight`, `:764-898`), all three
harvest sites (`:2678-2705`, `:3023-3039`, `:3325-3341`) and the two recovery
discriminators (`review_never_ran` `:2261-2278`, `run_advisory_leaves` `:2965-2986`), plus
`driver.py`'s comment-only changes at `:112-119` / `:150-163`. Cross-checked against
`gate-logs/C4-verify.log` (genuine 7/10-fail red → 10/10-pass green) and
`gate-logs/T3-suite.log` (1768 tests OK, `test_leaf_resilience.py` unmodified and still
green in the full run). No correctness bug in the shipped logic was found; two are
advisory-only nits below.

- The `owned=False` fail-closed branch of `_withdraw_residue` (`leaves.py:875-883` —
  `artifact.unlink()` raising `OSError`, which forces `may_retry = False` and stops the
  retry loop at `leaves.py:752`) is never exercised by
  `template/tests/test_attempt_ownership.py`. The symmetric OSError-on-write branch of
  `_write_attempt_records` *is* covered
  (`test_a_retry_never_starts_without_its_predecessors_account_on_disk`, mocking
  `Path.write_text`), but nothing mocks `Path.unlink` to drive the artifact-can't-be-
  withdrawn path, so the fail-closed guarantee the docstring claims at
  `leaves.py:860-862` ("the caller stops retrying rather than run another attempt over a
  path it no longer owns") is asserted in prose only. A test mirroring the existing
  `refuse_the_log` pattern against `Path.unlink` would close this.
  NEEDS-HUMAN [impl] — add a test that exercises `_withdraw_residue`'s unlink-failure
  branch, the one asymmetric leg of the two documented "fail closed" contingencies.

- Minor duplication: the "report to stderr, but never let a broken pipe mask the
  leaf's own failure" guard (`with contextlib.suppress(OSError): print(...)`) is
  written out twice, structurally identically, in `_write_attempt_records`
  (`leaves.py:806-808`) and `_withdraw_residue` (`leaves.py:878-881`) — both new in
  this patch. A tiny `_report(msg: str) -> None` helper would collapse both call sites
  to one line each; not worth blocking on, since the two messages differ enough that
  inlining is defensible, but it's a straightforward simplification if this file is
  touched again.

- Minor observational nit, not a bug: when retries stop because `_withdraw_residue`
  could not remove a dead attempt's artifact (`owned=False`, `leaves.py:752`), the
  exception returned to the caller is still the underlying `LeafError` with its
  original `.transient` flag intact. `_failure_class` (`leaves.py:2716-2731`) reads
  that flag and classifies the placeholder as `_FAIL_TRANSIENT` ("safe to re-run"),
  even though the actual reason this attempt was the last one is an unwithdrawable
  file on disk — a condition a plain re-run over the same sandbox lane would likely hit
  again. Narrow (requires an OS-level `unlink` failure on the sandbox artifact) and not
  worth gating on, but worth a human's awareness since it's a slightly misleading
  operator-facing message in that corner.

No dead code, resource leak, off-by-one, or API misuse found; the per-attempt flush,
withdrawal, defang, and the two discriminator updates are consistent with each other
and with the brief's six success-criterion legs, and `test_leaf_resilience.py` is
untouched and stays green per the full-suite gate log.
