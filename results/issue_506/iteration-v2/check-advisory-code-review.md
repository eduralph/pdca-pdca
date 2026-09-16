# Advisory code review — issue #506 (iteration 2)

Second lens: correctness bugs the patch introduces, and reuse/simplification/efficiency.
Grounded on `$PDCA_TARGET` (already carries the patch applied — `leaves.py` /
`progress.py` line numbers below are the post-patch target, matching `patch.diff`'s new
hunks).

The mechanism itself is sound on this reading: the retry-note / worktree-residue wiring
(`leaves.py:1855-1872`, `:1931-1934`), the `_has_content` guard so `do_build`'s outer
capture never clobbers the resilient wrapper's per-attempt log (`leaves.py:758-765`,
`:1812-1813`), the `capture`-exclusivity guard on the stream append
(`progress.py:409-415`), and the `memory_log=` kwarg drop (now derived, matching the
other three call sites) all read correctly against the iteration-1 carry-forward that
raised them. Two things worth a second look:

- NEEDS-HUMAN [impl] — `progress.py:529-535` (`_terminal_error`'s `result`-event branch).
  The iteration-1 review's "too broad" finding was fixed for the `assistant` branch by
  gating classification on a CLI-set marker (`is_api_error_message`/`isApiErrorMessage`,
  `progress.py:520-521`) before ever running `_TRANSIENT_CAUSE_RE` against free text — so
  a substantive failure whose text merely *reads like* an infra error (`_SUBSTANTIVE_LEAD`,
  `_QUOTES_THE_INCIDENT`) is correctly left un-marked and the regex never runs on it. The
  `result`-event branch has no equivalent CLI marker to gate on: any `result` event with
  `is_error` true and `subtype != "success"` — which covers non-infra endings too
  (`error_max_turns`, a permission/guardrail refusal, a tool's own execution error) — has
  its `result`/`error`/`errors` text run straight through the same broad
  `_TRANSIENT_CAUSE_RE` (`progress.py:533-534`), with only `is_error`/subtype as the gate.
  A tool failure whose own text happens to mention "timeout", echoes a "500"/"429" it
  received from *its own* subject matter, or reads "connection refused" from an unrelated
  log it was inspecting, would be reclassified transient and the builder retried 3× on a
  substantive death — reproducing the exact failure mode iteration 1 flagged, in the one
  shape iteration 1's fix didn't reach. Nothing in the appended suite exercises this
  branch at all: every stub script (`_TERMINAL_TRANSIENT`, `_INCIDENT_REPLAY`,
  `_UNCLASSIFIED_CAUSE`, `_PERMANENT_API_ERROR`, `_SUBSTANTIVE_LEAD_WORD`,
  `_QUOTES_THE_INCIDENT`, `_RECOVERED_THEN_FAILED` in
  `template/tests/test_leaf_resilience.py:34-40,834-887`) emits only `assistant` events
  via `event()`/`api_error()`; no test ever synthesises or replays a `result` event. The
  `assistant` shape now has two pinned-fixture tests plus two precision tests
  (`test_a_substantive_failure_opening_with_the_lead_word_is_not_retried`,
  `test_a_leaf_quoting_the_incident_line_is_not_retried`); the `result` shape has zero —
  so its precision is asserted nowhere, and per the brief's own falsifiability standard
  ("the classifier's contract with the real vendor stream is asserted, never observed")
  this half of it still isn't. Fixable by iterating: either add a precision test for a
  substantive `result`-event ending (and tighten the gate — e.g. restrict to the
  documented `error_during_execution` subtype plus `api_error_status`, rather than any
  non-success `is_error` result) or narrow the source of `texts` to a field the CLI itself
  marks as an infra cause.

- `progress.py:181-191` (the reader-thread loop) — `_is_session_event`, `_terminal_error`,
  `_is_work_event` and `_stream_tool_label` are four independent classifiers over the same
  `line`, and each does its own `json.loads(line)` (`progress.py:415`, `:515`, `:585`,
  `:595`). Pre-patch this loop already parsed each claude stream line twice (session +
  tool label); this patch adds a third unconditional parse (`_terminal_error`, called on
  every line regardless of family before its own `fmt` early-return) and, while a terminal
  report is pending, a fourth (`_is_work_event`). That's up to double the JSON-parsing
  work per line for the family (claude) this patch is actually about, in exactly the
  scenario the brief motivates the fix with — a long, event-heavy session (the incident
  ran ~18 minutes). Not a correctness bug (each function degrades safely and independently
  on a bad parse), but a straightforward reuse opportunity the "same shape as
  `_is_session_event`" composition cue (brief, Citations expected) invites: parse the line
  once per iteration and hand the same `ev` dict to all four classifiers, the way
  `_is_session_event`/`_terminal_error`/`_is_work_event`/`_stream_tool_label` already
  share the "best-effort JSON, degrade to today" *shape* but not the parse itself. Minor;
  flagging as an efficiency nit rather than NEEDS-HUMAN since it changes no observable
  behavior and nothing in the brief's scope requires closing it.

No other correctness issues found: the `_transient_do_death` branch selection
(`leaves.py:1841-1852`) is exercised by both the "no residue" and "partial patch.diff"
legs, the retry-note-from-attempt-2 wiring is asserted against the actual stdin the retried
child receives, and `_invoke_leaf_resilient`'s new `error_log.write_text` is wrapped in its
own `try/except OSError` (`leaves.py:740-744`) so a capture failure can't mask the leaf's
real exception — matching the "capture must never mask the failure" rule this bundle
otherwise reuses throughout.
