# Advisory code review — issue #533 (a leaf's own terminal error is kept and read)

Scope: correctness bugs the patch introduces, and reuse/simplification/efficiency. Grounded
on `$PDCA_TARGET` (patch applied, working tree). Both blocking defects from the prior
sign-off appear genuinely fixed in this round, not just re-worded:

- **Main-session scoping (prior item 1)** is real: `_terminal_error` (`progress.py:455-462`)
  routes a marked report to `_REPORT` only when `parent_tool_use_id is None`, else to
  `_SUBAGENT_REPORT`; `_note_terminal` (`progress.py:518-520`) enforces
  `_TERMINAL_PRECEDENCE = {subagent:1, wrapup:2, report:3}` so neither a sub-agent report nor
  a wrap-up can overwrite a main-session `_REPORT`, while a **second** main-session report
  (same precedence) still wins — matches `test_a_trailing_subagent_report_does_not_overwrite_the_main_sessions`
  and `test_a_second_marked_report_wins_outright`, both of which I traced by hand against
  `_note_terminal`'s precedence table and confirm are correct.
- **`produced`'s contract on the success path (prior item 2)** is restored:
  `died_of_reported_infra = terminal["transient"] and rc not in (0, TIMEOUT_RC)`
  (`progress.py:268-269`) means `produced` is only forced False on a non-zero, non-timeout
  exit — `test_a_recovered_run_that_exits_zero_still_reports_produced` and
  `test_a_timed_out_run_is_not_reclassified_by_its_stream` both exercise this and pass.
- **Prior item 3** (the two extra restatement sites, `leaves.py:693` /
  `:724-726`-ish — `_invoke_leaf_resilient`'s docstring and its retry-backoff print) is no
  longer left contradictory: this patch updates both (`leaves.py:693-704`, `:728-730`) so the
  operator-facing "with no output (transient)" message and docstring no longer contradict the
  widened definition.

## Findings

- NEEDS-HUMAN — `leaves.py:693-704` and `:728-730` (the `_invoke_leaf_resilient` docstring
  and its retry-backoff print line) are two of the "fifth and sixth restatement" sites the
  prior sign-off flagged as an **unresolved scope question between this child and sibling
  child-1** (issue_532, which owns `_invoke_leaf_resilient`'s *body*, `do_build`, and the
  harvest sites per the brief's Ordering note). This patch has unilaterally taken prose
  ownership of those two lines without any visible coordination artifact in this bundle
  (build-notes.md is withheld from this leaf, so I can't confirm it was settled there
  either). The brief's own recommended merge order is child-1 first, then this one — if
  child-1's patch also touches these same lines (plausible, since they sit inside the
  function child-1 owns the body of), that is a foreseeable merge conflict at publish, not a
  bug in this diff standalone. This is exactly the item the prior sign-off said must be
  "settle[d]…before either lands"; nothing here demonstrates that settlement happened. Human
  call, not something Do can resolve by re-iterating this slice alone.

- Minor / non-blocking — `_kind_is_transient` (`progress.py:473-485`) falls back to the
  `_TRANSIENT_CAUSE_RE` regex for **any** kind that is in neither
  `_CLAUDE_TRANSIENT_ERROR_KINDS` nor `_CLAUDE_PERMANENT_ERROR_KINDS`, but its own docstring
  and the module's `# ----` banner comment (`progress.py:296-301`, `:478-480`) describe this
  path as reserved for kind `"unknown"` specifically. Today the two enums plus `"unknown"`
  exhaust the vendor's documented kind enum quoted in `fixtures/README.md`, so the two
  descriptions coincide in practice — but the code is written more permissively (silently
  regex-classifies any *future*, currently-unlisted kind) than the prose promises. No test
  exercises an unlisted-and-not-`"unknown"` kind. Worth a one-line docstring correction
  ("or any kind not yet in either set") the next time this file is touched; not worth
  reopening the slice for.

- Minor / non-blocking (efficiency) — the per-line stream drain (`progress.py:236-248`) now
  runs up to four independent `json.loads` calls on the same line
  (`_is_session_event`, `_terminal_error`, optionally `_is_main_session_work`, then
  `_stream_tool_label`), where two (`_is_session_event` + `_stream_tool_label`) already
  existed pre-patch. This is the shape the brief explicitly asked for ("beside
  `_is_session_event`, in the same shape") and stream lines are small/I-O bound rather than
  CPU-bound, so it's not a real hot-path concern — noting only because the lens asks for it,
  not as something to fix.

No other correctness issues found: `_note_terminal`'s precedence table, the `capture`
short-circuit (`progress.py:253`, verified `tee_err` is always true whenever `stream_json`
is true and terminal state could be populated, so no output is silently dropped), the
`_WORK_EVENT_TYPES` exclusion of `result`, and the `TIMEOUT_RC` carve-out all check out
against the new test suite and against the C4 gate's red leg (`gate-logs/C4-verify.log`),
which fails for the right reasons pre-fix (wrong/absent retention text, wrong transient
verdict) — not a vacuous red.
