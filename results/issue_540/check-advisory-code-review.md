# Advisory code review — issue #540 (per-attempt record + one error-log meaning)

Scope: correctness bugs introduced by this diff, and reuse/simplification/efficiency.
Grounded on `$PDCA_TARGET` (base `acb214a` + patch). C4 gate log confirms a genuine
red→green (production hunks reverted: 15 failures + 3 errors; applied: 11+10 tests OK).

Traced all four named readers (`leaves.review_never_ran`,
`leaves.run_advisory_leaves(only_missing=True)`, `assemble._missing_review_text`,
`driver._resume_interrupted_check`) plus the two other, unnamed callers of
`_invoke_leaf_resilient` (`_run_advisory_sandboxed` for plan-advisory leaves, and the
`_unavailable_classification` display helper) — none was left speaking the old
"presence == ran-and-failed" sentence, and no fifth semantic reader was missed. The
carried-forward round-1 BLOCKING/SECONDARY findings (torn-write safety, fail-towards-
re-running default) are both present and each has a pinning test
(`test_a_record_a_dying_write_cut_off_leaves_the_last_whole_one`,
`test_a_torn_or_empty_record_recovers_its_leaf`) that fails on the reverted tree per the
C4 log.

No blocking correctness bug found. Two small, non-blocking observations:

- `leaves.py:778` (`_replace_record`) names its sibling temp file
  `.{error_log.name}.partial` with no per-writer discriminator (pid, etc.). The repo's
  existing atomic-write idiom for exactly this shape — `act.py:266-268,324` (`mark_reviewed`)
  and its `.tmp.{os.getpid()}` siblings at `act.py:324,369,724` — deliberately pid-suffixes
  the temp name "so one writer's `os.replace` can never consume another's" when two
  processes can overlap. `_invoke_leaf_resilient` has no equivalent exclusivity guard of
  its own (nothing in `leaves.py`/`driver.py` locks a bundle against a second concurrent
  invocation), so if the same `error_log` is ever targeted by two processes at once (e.g.
  an operator re-running Check while a prior session is still alive, not merely killed),
  one process's in-flight `tmp.write_text` could be truncated by the other's, and the
  `os.replace` that follows could publish a mixed/short record — the exact failure mode
  `_replace_record`'s docstring says it exists to prevent. Whether concurrent invocation
  of the same leaf/bundle is actually reachable (vs. already excluded by driver/worktree
  exclusivity elsewhere) isn't answerable from this diff alone.
  - NEEDS-HUMAN — confirm whether two live processes can ever target the same bundle's
    error log concurrently; if so, `_replace_record` should pid-suffix its temp name like
    `act.py` already does, for the same reason.

- `leaves.py:706` clears only `error_log` at the top of `_invoke_leaf_resilient`
  ("clear any stale tail from a prior cycle run"); it doesn't clear a stray
  `.{name}.partial` sibling. `_replace_record`'s own except-block cleans up the temp file
  when the *process is alive* to catch the failure (verified by the torn-write test's
  `stray == []` assertion), but a process killed in the narrow window between
  `tmp.write_text` succeeding and `os.replace` running — the same "killed mid-retry"
  class of event this whole slice defends against — would leave that `.partial` file
  behind, and nothing ever unlinks it on the next invocation. It's inert litter (no reader
  consults `.partial`, so `state.leaf_ran_and_failed` and friends are unaffected), so this
  is not a correctness bug in the fix's tracked contract, just a minor gap against the
  "a partial sibling is never left in the bundle" claim in `_replace_record`'s own
  docstring (`leaves.py:775`).
  - NEEDS-HUMAN [impl] — optionally have `_invoke_leaf_resilient` also unlink
    `error_log.with_name(f".{error_log.name}.partial")` alongside its existing
    `error_log.unlink(missing_ok=True)` at `leaves.py:706`, so a stray temp from an
    earlier kill doesn't linger indefinitely.

Everything else checked out: `_replace_record`'s all-or-nothing write directly satisfies
the round-1 BLOCKING finding (sibling temp + `os.replace`, same-directory so no EXDEV
risk); `state.leaf_ran_and_failed`/`_last_nonblank` fail towards re-running for every
ambiguous shape (absent, unreadable, empty, torn, unfinished) per the round-1 SECONDARY
finding; `neutralize_leaf_text` only rewrites a line that IS the marker (whitespace
aside), never a substring, so the #420 memory-telemetry text riding `output` survives
untouched unless it happens to equal the marker outright; the unsettled state's lifetime
is correctly scoped inside `_invoke_leaf_resilient` (settled on failure, discarded via
`error_log.unlink` on a recovering success at `leaves.py:722-723`) with no caller change;
and the retry contract (attempt count, transient rule, backoff schedule) is unchanged —
`_flush_attempt_records` is `except OSError`-only and best-effort, matching criterion 5.
No reuse/duplication or efficiency concern beyond the temp-naming point above.
