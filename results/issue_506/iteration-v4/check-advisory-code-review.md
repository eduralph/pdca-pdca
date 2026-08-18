# Advisory code review — correctness + reuse/simplification lens (issue #506)

Scope: only the hunks in `patch.diff`, grounded on `$PDCA_TARGET`. The core mechanism
(sticky terminal-report classification, the `is_api_error_message`/`result` split, the
attempt-by-attempt error-log flush, the builder's `_BUILD_RETRY_NOTE`, `_has_content`) is
sound and matches what C4 (`gate-logs/C4-verify.log`: 30 failures pre-fix, `OK` on both
touched test files post-fix) and the full suite (`gate-logs/T3-suite.log`: 1780 tests OK)
actually exercised. Iteration-1/2's four carried-forward defects (narrow/broad matcher,
false resume message, unwarned retry-into-residue, unpinned vendor contract) are genuinely
fixed and tested against real fixture bytes (`tests/fixtures/`), not a synthesised shape.

## Findings

- NEEDS-HUMAN — The widened transient signal now makes the **reviewer/advisory** leaves
  retryable after they have already produced partial work (they share
  `_invoke_leaf_resilient` with the builder, `leaves.py:680-754`), but unlike the builder
  they get no `retry_note` (`leaves.py:2641-2648`, `leaves.py:2975-2981` — no `retry_note=`
  kwarg), and the sandbox `tempfile.TemporaryDirectory` that holds the leaf's own output
  is opened ONCE and reused across all internal retry attempts
  (`_run_review_sandboxed`/`_run_advisory_sandboxed`, `leaves.py:2597-2648` and
  `:2948-2981`). A dying attempt 1 can leave a partial `check-review.md` /
  `check-advisory-<id>.md` on disk in that sandbox (`REVIEWER_INPUTS`, `leaves.py:68`,
  never includes those output names, so nothing clears them between attempts); harvest is
  attempt-blind — `if produced.exists(): shutil.copy2(...)` (`leaves.py:2653-2657`,
  `:2986-2989`) — with no check that the copied file is from the attempt that actually
  succeeded. This is exactly item 5 the previous sign-off's carry-forward flagged as SCOPE
  ("necessary but not sufficient… a truncated check-review.md from a dead attempt 1 can be
  copied into the bundle as the reviewer's verdict") and explicitly deferred, asking that
  any non-closure be recorded in `build-notes.md`. That file is withheld from this lens, so
  a human should confirm at sign-off that the deferral is actually documented there (or
  that this round closed it in a way not visible from the diff alone).

- The stream drain (`progress.py:182-194`) now runs up to four independent
  `json.loads(line)` calls per stream line inside the hot per-leaf drain thread:
  `_is_session_event` (`:183`), `_terminal_error` (`:185`), conditionally `_is_work_event`
  (`:188`), and `_stream_tool_label` (`:192`) each re-parse the same JSON. This follows the
  codebase's pre-existing per-classifier-reparse convention (`_is_session_event` +
  `_stream_tool_label` already did this before the patch), so it's not a new pattern, but
  the patch does add two more re-parses per line to what was already redundant work. Not
  perf-material at typical CLI line rates, but a follow-on could parse once and pass the
  dict to each classifier rather than widening the existing duplication further.

- `_record_loop_attempt` (`leaves.py:1906`, called once per `do_build`) still records one
  `loop-telemetry.json` entry per iterate-do attempt, unaware that `_invoke_leaf_resilient`
  may now spawn the builder up to 3 times underneath it for a single recorded attempt
  (`leaves.py:1953-1962`). Not a defect against this brief's scope (telemetry wasn't in
  scope, and the brief explicitly says not to add new knobs), but worth surfacing: anyone
  reading `loop-telemetry.json` for cost/attempt accounting will now undercount actual
  builder invocations on a bundle that hit a transient retry.

## Not re-flagged (already closed this round, verified against target source)

- The matcher precision fix (`_terminal_error` gating `_TRANSIENT_CAUSE_RE` only on
  CLI-marked `is_api_error_message` text, `progress.py:580-586`) and the `result`-branch
  narrowing to `subtype == "success"` + `api_error_status` (`progress.py:587-593`) both
  match the "kind/status, not prose" requirement and are pinned by
  `test_the_cli_error_kind_classifies_a_report_whose_text_says_nothing` and
  `test_a_result_ending_the_cli_did_not_mark_is_explained_but_not_retried`.
- Sticky terminal-report semantics (`_note_terminal`, `progress.py:597-618`) correctly
  survive a same-shape `result` wrap-up and are cleared only by a real work event
  (`_is_work_event`, `progress.py:661-672`), verified by
  `test_the_wrap_up_result_does_not_overturn_the_report_that_named_the_cause`.
- `_write_attempt_records` flushing after every attempt (`leaves.py:757-765`), making
  `_BUILD_RETRY_NOTE`'s pointer at `BUILD_ERROR_LOG` true for every retried attempt, is
  exercised end-to-end from inside the child by
  `test_a_retried_builder_can_actually_read_that_account`.
- `capture` vs `stream_json` classification stays mutually exclusive on OUTPUT bytes while
  the classification itself still runs under `capture=True` (`progress.py:141-151`,
  `:292-298`), verified by `test_a_capturing_caller_still_gets_verbatim_stream_bytes`.
