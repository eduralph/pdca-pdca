# Check advisory — code review (correctness + reuse/simplification)

Scope: `template/src/pdca_harness/{leaves,driver,assemble,state}.py` and the new
`template/tests/test_attempt_ownership.py`, as touched by this patch (issue #506,
iteration 2). Grounded on `$PDCA_TARGET` (patch already applied there).

## Correctness

No bugs introduced by this patch were found. Specifically verified, against the target
source, not just the diff:

- **Retry/withdraw/flush interaction** (`leaves.py:723-764`): `may_retry` is
  `transient and attempt < attempts and owned`, and the loop only continues if
  `_write_attempt_records` also returned `True` (`:756-758`). Every path that can reach
  the success branch has therefore already durably flushed its predecessor's record, so
  the "kept in-flight" re-write on a silent success (`:737-738`) is provably writing
  content identical to the last mid-loop flush — redundant but harmless, not a
  correctness gap (traced by hand across the 1-of-3-attempts and 2-of-3-attempts cases;
  matches what `AttemptRecordsLandBeforeTheNextAttemptStarts` and
  `DeadAttemptOutputIsNeverHarvested` in the new test file exercise).
- **`_empty_run_class`** (`leaves.py:2812-2825`): only reachable with `error_log.exists()`
  actually true when a withdrawal happened in *this* invocation, because the wrapper
  clears any stale log before the loop starts (`:716`) and only a same-run withdrawal can
  leave one behind on a `None` return. So classifying "log survives a success ⇒ infra
  death" needs no extra state check — confirmed correct, not merely asserted by the
  tests.
- **`_settle_leaf_record` ordering** (`leaves.py:2780-2783`, `:3132-3135`,
  `:3436-3439`): called unconditionally after either harvest branch (copy or
  placeholder), and is a documented no-op on an absent/settled/unreadable log — verified
  that on the `produced.exists()` branch the log has already been unlinked by the wrapper
  by construction, so the call there is inert as designed, not accidentally so.
- **Whole-line, defanged marker match** (`leaf_run_incomplete`, `leaves.py:853-871`,
  `_defang_in_flight`, `:777-785`): every place that embeds leaf-controlled text into the
  log (`_format_leaf_attempt` tail, `_withdraw_residue` residue) routes through
  `_defang_in_flight` before it reaches `records`, so there is no path by which raw
  leaf-authored text can land in the log un-defanged.
- Three call sites of `_invoke_leaf_resilient` (`:2759`, `:3119`, `:3423`) all now pass
  `artifact=`; grepped for any other caller — there are none, so nothing was missed.
- The three places that used to read `REVIEW_ERROR_LOG`/advisory-error-log existence
  bluntly (`assemble.py:425`, `leaves.py:2352` `review_never_ran`, `leaves.py:3080`
  `run_advisory_leaves`) all now route through `_leaf_ran_and_failed`; grepped the rest of
  `template/src/pdca_harness` for other bare `.exists()` reads of these paths — none
  found, so the "three readers must agree" invariant is actually closed, not just
  claimed.
- `test_leaf_resilience.py` is untouched by the diff (only named in the new file's
  docstring) — confirmed via `grep -c` on the patch; C4's gate log
  (`gate-logs/C4-verify.log`) shows a genuine red→green on `test_attempt_ownership.py`
  alone (19 tests, 17 fail on the reverted production hunks, all for the reasons the
  brief predicts), and T3's 1777-test run is green.

One pre-existing, explicitly-deferred behavior worth restating for the record (not a new
finding — it's the carried-forward item the prior sign-off told this round to leave
alone): the staleness clear at `leaves.py:716` still unconditionally unlinks a prior
in-flight log — including one holding a preserved dead-attempt verdict — the moment a
recovery re-run of the same leaf starts. Correctly out of scope per criterion (vi) and
the carry-forward's item 1 note; flagging only so it isn't mistaken for something this
review missed.

## Reuse / simplification (minor, non-blocking)

- `_atomic_write_text` (`leaves.py:788-816`) reimplements the temp-sibling +
  `os.replace` idiom that `act.py` already inlines three times (`act.py:324-326`,
  `:367-369`, `:722-724`). The repo evidently prefers inlining this idiom per call site
  rather than factoring it, so this isn't a deviation from house style, but a fourth
  copy is a candidate for a shared one-line helper (e.g. in `state.py`, imported by both
  modules) next time either module touches this idiom again.
- `_leaf_ran_and_failed` (`leaves.py:874-877`) calls `error_log.exists()` and then
  `leaf_run_incomplete(error_log)`, which itself does a second `.read_text()` open. Since
  `leaf_run_incomplete` already treats an absent file as `False` (`:868-869`), the
  `.exists()` guard is redundant with the `try/except OSError` inside it — could be
  simplified to `not leaf_run_incomplete(error_log)`-only plus tracking "did it exist" if
  ever needed, dropping one syscall per call. Cold path (called once per bundle per
  discriminator check, not in a retry loop), so this is a nit, not a performance concern.

Neither item rises to a human-adjudication or builder-iteration finding; both are
optional polish for a future touch of this code.
