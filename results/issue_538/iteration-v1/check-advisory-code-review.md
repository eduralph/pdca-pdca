# Check advisory — code review (correctness + reuse/efficiency lens)

Scope: only the hunks in `patch.diff` (progress.py + new tests/fixtures), grounded
against `template/src/pdca_harness/progress.py` and `leaves.py` at `$PDCA_TARGET`.

## Correctness

Traced the new retention path end-to-end (`_terminal_error` → `_note_terminal` →
the `terminal["text"]` append in `run_with_heartbeat`, `progress.py:192-199,
296-305,469-622`) against all four `run_with_heartbeat` call sites
(`leaves.py:657`, `leaves.py:752`, `gates.py:559`, `publish.py:833`) and the
precedence table (`_TERMINAL_PRECEDENCE`, `progress.py:482`). No bug found:

- The only caller that sets `stream_json=True` (`leaves.py:657-660`) never also sets
  `capture=True`, and the three `capture=True` callers never set `stream_json=True`,
  so the "skip the append under `capture`" branch (`progress.py:297`) is dead in
  production exactly as the docstring claims — and the patch's own test
  (`test_capture_returns_the_childs_raw_stdout_unmodified`, exercising that
  otherwise-impossible `capture=True, stream_json=True` combination directly
  against `run_with_heartbeat`) is the only place that combination is checked, which
  is the right way to cover an invariant no caller currently triggers.
- `_note_terminal`'s `<` comparison (`progress.py:571`) correctly lets an equal
  (same-shape) precedence overwrite — "newest wins within a shape" — while a
  strictly lower one is rejected in either arrival order; verified against all six
  `NearestRecordWins` cases and the precedence table by hand, no off-by-one.
- `terminal["shape"]` is only ever mutated from the single drain thread
  (`progress.py:194-196`), read from the main thread only after
  `reader.join(timeout=5)` (`:292`) — the same join-then-read pattern the
  pre-existing `produced` dict already uses, so this doesn't introduce a new race,
  just extends an existing one.
- `use_stream` / family-profile gating (`leaves.py:648-649`) confirms `_terminal_error`
  only ever sees `stream_format="claude-stream-json"` in production, matching its
  `fmt != "claude-stream-json"` degrade-to-`("", "")` guard (`progress.py:525`).

## Reuse / efficiency

- **Minor** — `progress.py:192-199`: the drain loop now calls `json.loads` on every
  stream line **three** times (`_is_session_event`, the new `_terminal_error`, then
  `_stream_tool_label`), each independently parsing and independently swallowing
  `(ValueError, TypeError)`. This was already 2x before the patch; the patch adds a
  third pass rather than parsing once and dispatching the parsed `dict` to the three
  classifiers. Given `_terminal_error` is explicitly written "in the same shape" as
  `_is_session_event" for symmetry, a shared one-parse-then-dispatch would have been
  a natural simplification here, and the stream drain is a genuine hot loop for a
  long session (thousands of lines). Not a correctness issue — each function
  degrades safely on a bad parse — just wasted repeated work.
  - NEEDS-HUMAN [impl] — worth asking the builder to parse once per line and pass
    the decoded event to all three classifiers, since the three now duplicate the
    exact same `json.loads` + `isinstance(ev, dict)` guard
    (`progress.py:194-199,528-532,629-633`).

## Tests

- `_run_leaf` / `_heartbeat` correctly drive the production path
  (`leaves._invoke_leaf_resilient` → `_invoke` → `progress.run_with_heartbeat`) with
  a `family="claude"` stub leaf, so `use_stream` is true and the new code actually
  executes (verified against `families.resolve("claude")`,
  `stream_argv`/`stream_format` at `families.py:91-92`). The C4 gate log confirms a
  genuine (non-vacuous) red: 10/29 cases fail on revert, not an import-time
  `PDCA-UNVERIFIABLE`, and fixtures are present so `PinnedVendorRecords` isn't
  trivially skipped.
- One small gap: `_terminal_error`'s "an error record with nothing to say is not
  evidence" branch (`progress.py:544-546`, a `result`/`is_error` event whose
  `_report_line` comes back empty) has no direct test — only the non-empty wrap-up
  path (`_WRAPUP`) is exercised. Low risk since the branch is a straightforward
  early-return, but it's the one line in the new retention logic without a red/green
  witness of its own.

## Summary

Clean on the correctness lens — no bugs found in the traced retention/precedence
path, and it degrades safely everywhere it's supposed to. One efficiency nit (the
now-3x per-line JSON parse) worth a quick builder pass, and one minor untested
branch (empty-text wrap-up). Neither blocks; both are cheap follow-ups.
