# Advisory code review — issue #538 (progress.py terminal-report retention)

Scope: correctness bugs introduced by this diff, and reuse/simplification/efficiency
opportunities. Grounded on `target/template/src/pdca_harness/progress.py` (patched) and
`target/template/tests/test_terminal_error_retention.py`.

## Correctness

No bugs found. Traced the mechanics the brief's five success-criterion clauses depend on
against the patched source, not just the tests:

- `_note_terminal` / `_TERMINAL_PRECEDENCE` (progress.py:580-603): the "nearest wins, in
  either arrival order" rule is `if precedence[new] < precedence.get(current, 0): return`
  — correctly lets same-or-nearer-shape records overwrite (including a second `_REPORT`
  replacing an older one, per the "newest wins within a shape" clause) while a farther
  shape arriving after OR before a nearer one never displaces it. Hand-traced against all
  the `NearestRecordWins` cases (progress.py:580-603, test file :319-364); matches.
- The `if shape:` guard at progress.py:201 correctly keeps an empty-text wrap-up
  (`_MUTE_WRAPUP`) from ever reaching `_note_terminal`, so it cannot displace an
  already-retained nearer/equal record by masquerading as "a record with nothing to say"
  — `_terminal_error` returns `("", "")` for that case (progress.py:572-576), not
  `("", _WRAPUP)`, so the guard is watertight rather than incidentally correct.
- `_stream_event`'s single-decode-per-line sharing (progress.py:423-447, 197-203) is
  transparent to the three callers: each still calls `_stream_event(ev)` on the
  already-decoded dict and short-circuits on `isinstance(line, dict)` — verified this
  doesn't reintroduce a second `json.loads` for the JSON-string path, consistent with the
  `OneDecodePerStreamLine` test's counted-`json.loads` assertions.
- `capture=True` short-circuits the whole retention path only at the append step
  (`terminal["text"] and not capture`, progress.py:303), but the drain still evaluates
  `_terminal_error` unconditionally whenever `stream_json` is set — dead work when both
  `capture` and `stream_json` are true together, but no caller in the tree currently
  passes both (confirmed against all four `run_with_heartbeat` call sites:
  gates.py:559-562, publish.py:833-836, leaves.py:752-754 pass `capture=True` alone;
  leaves.py:657-660 passes `stream_json=True` alone), so this is inert today, not a bug.
- The append block (progress.py:303-311) runs regardless of `rc`, so on a clean `rc == 0`
  exit it still formats and appends `terminal["text"]` into `output` — wasted string work
  the caller (`leaves._invoke`, which only inspects `output` inside `if rc != 0:`,
  leaves.py:661-670) discards immediately. Cosmetic only, not worth a fix.

## Reuse / simplification

Nothing to flag. The whitespace-flattening idiom in `_report_line` (progress.py:654,
`" ".join(text.split())`) duplicates the same one-liner already used independently in
`assemble.py:106`, `driver.py:349`/`:182`, `leaves.py:514` — but each of those is a
private local idiom already, not a shared helper this patch bypassed; not worth
introducing a cross-module dependency for a one-line built-in composition, and it doesn't
fall inside this patch's declared single-file scope (progress.py only) anyway.

The patch adds no other production file (fixtures + one new test file only, as scoped),
and the new helpers (`_stream_event`, `_terminal_error`, `_note_terminal`,
`_is_subagent_event`, `_claude_message_texts`, `_claude_result_texts`, `_report_line`)
are each single-purpose with no overlap with pre-existing `progress.py` code — the one
piece of duplication this patch explicitly *removes* (three independent `json.loads` +
"is it a dict" guards collapsing into one `_stream_event`) is itself the efficiency win
called out in the diff.

## Verdict

Diff is clean on both lenses. No NEEDS-HUMAN items.
