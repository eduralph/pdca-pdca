# Advisory code review — issue #539 (transient leaf death, decided once)

Lens: correctness bugs the patch introduces, plus reuse / simplification / efficiency.
Grounded on the patched target at `$PDCA_TARGET`.

**Summary: no blocking correctness bug found.** The classification logic, the drain wiring
and the signal predicate do what the brief asks. The three guards the brief names (main-session
`user` work, the `_TRANSIENT_STATUSES` set, the `subtype == "success"` wrap-up guard) each have a
test that fails if the guard is removed. The iteration-1 carry-forward items (typed cause before
the kind shortcut, the `apiError` spelling, the anchored status regex with no bare `timeout`,
the `assemble.py:95` comment) are all in. What follows are low-severity notes, none gating.

## Correctness

- `template/src/pdca_harness/progress.py:265-272` — the verdict follows only the record
  `_note_terminal` *keeps*, and clearing only happens on non-report main-session work. I walked
  through the orderings: sub-agent report then main report; main report then wrap-up; main
  report, then work, then a wrap-up with a 5xx; main report, then work, then a new main report.
  Each gives the intended verdict. The one-way "cleared stays cleared until a nearer-or-equal
  record" rule is correct because `_TERMINAL_PRECEDENCE` (`progress.py:592`) puts `_REPORT`
  highest. No bug.
- `template/src/pdca_harness/progress.py:393` — `rc not in (0, TIMEOUT_RC)` keeps exit 0 and the
  harness's own timeout unchanged, as criteria (iii) and (vi) require. A signal-killed leaf that
  had reported a transient cause still comes back `produced=False` here, but
  `LeafError.transient` (`leaves.py:116`) rejects it on `is_signal_death`, and
  `test_the_kill_outranks_a_transient_report` pins that. The split is correct but spread across
  two modules. The docstring at `progress.py:98` says so; no action needed.
- `template/src/pdca_harness/progress.py:42-59` (`is_signal_death`) — any exit code 129–192 is
  treated as a signal death, even from a direct child that chose that code itself.
  `test_a_bare_exit_137_is_read_as_the_same_death` pins this on purpose, and the only cost is
  "not retried". That is acceptable, but the price is that a CLI which ever exits 129–192 for
  its own reasons (not a signal) loses its retry. Noted, not a defect.
- `template/src/pdca_harness/progress.py:871` (`_typed_causes`: `ev.get(key) is not None`) —
  an empty-string typed cause (`"api_error": ""`) counts as "typed" and so turns a stamped
  `server_error` / `overloaded` report into not-transient. This fails safe (no retry), and the
  CLI is not known to emit an empty string, so it is only a nit. A truthiness check
  (`if ev.get(key)`) would treat `""` as untyped and let the kind decide.
- `template/src/pdca_harness/progress.py:372-373` — `died_of` is read after
  `reader.join(timeout=5)`, so if a drain thread is still running after 5 s the verdict could be
  stale. This is the same existing limit child-1's `terminal` state already has, not a new
  hazard. Mentioned only because the patch adds a second reader of that state.

## Reuse / simplification / efficiency

- Hot-loop cost is fine. `_reports_transient_cause` runs only when a marked record is kept
  (rare), and `_is_main_session_work` only while a transient verdict is pending. Both reuse the
  drain's single decode through `_stream_event`'s dict pass-through (`progress.py:502-514`). No
  duplicated helper: `_is_main_session_work` is different from `_is_session_event` on purpose
  (it leaves out `result`), and it reuses `_is_subagent_event`.
- The two-shape wording ("before emitting any work, or on its own report of a transient API
  error") is now copied into about eight prose sites (`leaves.py:97-102`, `:110-115`,
  `:711-719`, `:768`, `:2202`, `:2932`, `:2958`, `:3036-3040`; `assemble.py:104`, `:112`). Each
  site agrees today, which is what criterion (iv) asks for. The copies can still drift apart the
  same way the old single-shape wording did, and only the operator-facing strings (the label,
  the retry line, the builder line) are pinned by tests. A shared constant for the runtime
  strings would stop that drift. This is optional and lies outside the brief's "strings only"
  limit for `leaves.py`, so it is not filed as a finding.

## Consequence to confirm (not a code defect)

- NEEDS-HUMAN — `template/src/pdca_harness/leaves.py:758-770` together with the builder path
  (`leaves.py:2158`, #537): a leaf that worked for minutes and then lost the API is now re-run
  **from scratch** up to `attempts - 1` more times, each with its full timeout. For the reviewer
  this is the goal (criterion i). For the builder, stacked on #537, it means a fresh builder
  starts on a worktree still holding the dead attempt's partial edits, and worst-case wall-clock
  for one Do grows to about `attempts × leaf timeout`. The brief calls this a consequence to
  record, not a reason to widen the slice. Confirm at sign-off that the retry budget and the
  dirty-worktree restart are acceptable for the builder, or track it as a follow-up.

## Gate evidence

C4 is red→green: `gate-logs/C4-verify.log` shows 40 of 52 failing on the red leg and green with
the fix. The red failures are behavioural assertions (for example `human-empty != infra-empty`,
`retry 1/2` missing), not import errors. T3 passes: 2033 tests, 2 skips, both in unrelated
modules. The pinned vendor fixtures are present, so the fixture-replay cases actually ran
rather than skipping.
