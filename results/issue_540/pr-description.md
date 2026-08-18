## Summary
**User impact:** When a run is killed while the harness is retrying a failing leaf — a
Ctrl-C, an out-of-memory kill, a closed session — the run leaves nothing behind
explaining what went wrong. Every attempt's captured error output was held in memory and
written out only once the retries were over, so an interrupted run has no post-mortem to
read at all, and anything inspecting the directory while a later attempt is still running
sees no trace of the earlier ones.

This change writes each failed attempt's record as that attempt fails, and makes "this
leaf ran and exhausted its retries" something the harness *states* in the file rather than
something inferred from the file merely existing.

Reported in [#540](https://github.com/eduralph/pdca-harness/issues/540).

## What to look at
Two halves that only work together. The first is small: the retry wrapper in the leaf
runner now saves the attempts so far before sleeping into the next attempt, and clears
them again if a retry succeeds. The second is the reason the first was not done long ago —
the *presence* of an error log was how the engine recognised a leaf that had run and
failed, and four places relied on that. Two of them decide whether a leaf still needs to
be run, so a file appearing mid-retry would have made them retire a reviewer that had only
been interrupted — and a bundle can then reach sign-off with no review of the diff at all.
That sentence now lives in one predicate that every one of the four asks, and a record
counts as finished only when the harness has closed it.

To exercise it: point a leaf at a command that fails the way a transient infrastructure
error fails (exit non-zero with nothing on stdout) and interrupt the run during the
backoff between attempts. Before: no `*.error.log` exists. After: the log holds every
attempt so far, and the next `advance` re-runs the leaf instead of treating it as
finished. Let the same leaf exhaust its attempts and the old behaviour is unchanged — the
log is closed, and the leaf is not re-run.

## Root cause
`template/src/pdca_harness/leaves.py:720` (`_invoke_leaf_resilient`) accumulated each
attempt's record in memory and wrote the whole file once, after the retry loop had
finished — so mid-loop there was no file, and a death in that window discarded every
record. Flushing earlier was not possible on its own because the file's existence *was*
the failed-leaf discriminator at four independent sites — `leaves.py:2104`
(`review_never_ran`), `leaves.py:2801` (`run_advisory_leaves(only_missing=True)`),
`assemble.py:417` (the §6 wording split) and `driver.py:144-171`
(`_resume_interrupted_check`) — each testing `.exists()`, so an early flush would have
made all four read "ran and FAILED" for a leaf that was still retrying.

## Fix
- **Per-attempt flush.** `_invoke_leaf_resilient` writes the records so far before the
  backoff sleep, so attempt 1's account is on disk before attempt 2 starts; a retry that
  succeeds removes the log again, so a leaf that worked still leaves nothing behind.
- **One point of truth, asserted positively.** `state.ATTEMPTS_SPENT_MARKER` closes a
  spent leaf's record, and `state.leaf_ran_and_failed(log)` — "the last non-blank line is
  that marker" — replaces the four `.exists()` tests. Every ambiguous shape (absent,
  empty, unreadable, unfinished, torn by a dead write, written by an older version)
  answers False and the leaf is re-run: one extra leaf run, versus losing the review.
  The operator-facing wording in `assemble._missing_review_text` and
  `driver._resume_interrupted_check` now names both shapes it recovers, not just one.
- **All-or-nothing writes.** `_replace_record` writes a sibling temp and `os.replace()`s
  it in, so a write that dies part-way (ENOSPC, a quota, a killed run) leaves the previous
  complete record untouched and never a half-written one; the temp is removed on failure.
- **The retry contract is not narrowed.** A flush that fails warns and keeps the records
  in hand — attempt count, transient rule and backoff schedule are as shipped, and the
  final write raises exactly as the `write_text` it replaces did.
- **A leaf cannot close its own record.** `state.neutralize_leaf_text` rewrites (never
  drops) a captured line that *is* the marker, and the marker is recognised only as a
  whole final line — never as a substring, never mid-line.

## Verification
- **Claim:** each failed attempt's record is on disk before the next attempt starts.
  **Checked:** `template/src/pdca_harness/leaves.py:705-721` on `main` — the loop's only
  write is `:720`, after the loop.
  **Test:** `template/tests/test_attempt_ownership.py` —
  `test_attempt_two_finds_attempt_ones_account` (the stub leaf copies the log aside from
  inside the production retry loop, so the fixture is byte-for-byte what a kill leaves);
  fails pre-fix, passes post-fix.
- **Claim:** an unfinished record recovers its leaf exactly as an absent one does, at
  every reader.
  **Checked:** `leaves.py:2104`, `leaves.py:2801`, `assemble.py:417` and
  `driver.py:144-171` on `main` — four independent `.exists()` tests.
  **Test:** `test_a_mid_retry_record_recovers_its_leaf`,
  `test_a_torn_or_empty_record_recovers_its_leaf` and
  `test_a_settled_record_still_means_ran_and_failed` drive `review_never_ran`,
  `run_advisory_leaves(only_missing=True)` and `_missing_review_text` unmocked.
- **Claim:** a record whose write dies part-way still leaves a whole one, and recovers its
  leaf.
  **Checked:** measured on both trees under `RLIMIT_FSIZE=600` with `SIGXFSZ` ignored —
  `main` leaves a 600-byte truncated log that retires the leaf; patched keeps attempt 1's
  complete 428-byte record, re-runs the leaf, leaves no stray sibling, 3 attempts either
  way.
  **Test:** `test_a_record_a_dying_write_cut_off_leaves_the_last_whole_one` (same
  scenario, in a child process since the limit is process-wide).
- **Claim:** a leaf's own output cannot settle the harness's account of that leaf's run.
  **Checked:** `leaves.py:727` on `main` embeds the captured stderr tail verbatim.
  **Test:** `test_only_the_harness_can_close_a_record_with_that_line`,
  `test_a_torn_record_carrying_that_line_still_recovers_its_leaf`,
  `test_the_line_is_recognised_only_whole_and_last` — the impostor line is read off the
  production record, never named in the test.
- **Claim:** the shipped resilience contract is unchanged.
  **Checked:** `leaves.py:698-702` (staleness clear) and the backoff/print block are
  byte-identical; `template/tests/test_leaf_resilience.py` is untouched.
  **Test:** `test_a_leaf_that_recovers_on_retry_leaves_no_record_behind` and
  `test_an_unwritable_record_does_not_narrow_the_retry_contract` (both green on `main`
  too — they pin what must NOT change). Full offline suite: 1802 tests OK; three fixture
  lines in `template/tests/test_check_resume.py` now build their "ran and failed" log with
  the production writer instead of a hand-written stand-in, no assertion changed.

Fixes #540
