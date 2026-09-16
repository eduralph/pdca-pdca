# Check — advisory code review (issue #506 slice)

Scope: `template/src/pdca_harness/progress.py` (new terminal-error reader/classifier),
the four prose sites in `template/src/pdca_harness/leaves.py`, one comment in
`assemble.py`, and the new test/fixture files. Grounded against
`$PDCA_TARGET/template/src/pdca_harness/{progress,leaves}.py` (post-patch) and the
C4 gate log (genuine red→green: 20 failures pre-fix, `Ran 23 tests … OK` post-fix).

## Correctness

Traced the state machine end to end (`_terminal_error`, `_kind_is_transient`,
`_note_terminal`, `_is_main_session_work`, and the `produced["session"] and not
terminal["transient"]` fold at `progress.py:303`) against every case in
`test_terminal_error_classification.py`, plus several combinations the suite does
not exercise (WRAPUP-before-REPORT ordering, a REPORT/WRAPUP pair with `is_error`
False, a `kind=None` report, an interrupted `reader.join(timeout=5)`). No bug found:
the `if shape: … elif …` branch order at `progress.py:188-194` correctly prevents a
REPORT line from being read as its own "recovery" via `_is_main_session_work`, the
`_note_terminal` stickiness (`progress.py:412-414`) is scoped to the wrap-up shape
only (not "any later record"), and the newline/`capture` handling at `:295-301`
matches the pre-existing stderr-tail convention exactly (no double-newline, no
corruption of raw JSONL under `capture`). The two defects the brief calls out as
open against the rejected prior attempt (scope-blind clearing, wrap-up swallowing a
second report) are both closed and each has a dedicated regression test
(`test_a_trailing_subagent_line_does_not_clear_the_report`,
`test_a_second_marked_report_wins_outright`).

- No correctness bugs found in the new classification/retention logic.

## Reuse / simplification / efficiency

- `progress.py:186-197` (the claude-format branch of `_drain`): for every stream line
  of a `claude-stream-json` leaf, the drain thread now does up to **three** independent
  `json.loads` + dict-walks of the same line unconditionally (`_is_session_event`
  at `:419`, `_terminal_error` at `:555`ish, `_stream_tool_label` at `:688`), plus a
  fourth (`_is_main_session_work`) once a terminal report is pending. This was already
  a 2x-parse pattern before this patch (`_is_session_event` + `_stream_tool_label`);
  the patch's `_terminal_error` call adds a third unconditional parse per line, in
  the same shape as the existing classifiers (matches the brief's own composition
  cue to sit "beside `_is_session_event`, in the same shape"), so it is consistent
  with established style rather than a new anti-pattern. For an 18-minute session
  emitting thousands of lines (the incident this fix targets) the redundant
  re-parsing is measurable but not correctness-affecting — a `json.loads(line)` once
  per line, threaded through to each classifier, would avoid the repeat work. Not
  blocking; a straightforward follow-up if `_drain`'s per-line cost ever becomes
  the bottleneck.

No other duplicated logic, unreachable branches, or resource-leak concerns found in
the diff. The regex `_TRANSIENT_CAUSE_RE` (`progress.py` "unknown"-kind fallback)
is exercised only on text the CLI itself marked as its own API-error message, so its
breadth (bare `\btimeout\b`, `\b(?:…|500|502|503|504|…)\b`, etc.) is scoped tightly
enough that a false-positive match on unrelated leaf prose is not reachable — no
finding there.

## Summary

Diff is clean on both lenses I was asked to apply: no correctness bugs introduced,
and the one efficiency observation above (redundant per-line JSON parsing in the
stream drain) is minor, pre-existing in kind, and non-blocking.
