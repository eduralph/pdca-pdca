# Advisory code review — issue #533 (terminal-error classification), round 3

Second lens: correctness bugs the patch introduces, plus reuse/simplification/efficiency.
Grounded on `$PDCA_TARGET` (target/), not build-notes.md.

## Findings

- NEEDS-HUMAN [impl] — `target/template/src/pdca_harness/assemble.py:85` (`_LEAF_STATUS_LABEL[LEAF_STATUS_INFRA]`)
  still reads `"leaf did not run (transient infra — safe to re-run)"`. This is the exact
  string prefixed onto every §6 item for a placeholder carrying the `infra-empty` marker
  (`_items_from_artifact`, `assemble.py:168-173`) — it is what the human actually reads at
  sign-off. The patch widens `LEAF_STATUS_INFRA` (via `_failure_class`/`LeafError.transient`,
  `leaves.py:106-108`, `2549-…`) to also cover a leaf that *did* run substantively — the
  brief's own headline case, an 18-minute builder whose stream ended on the CLI's own marked
  transient report (`progress.died_of_reported_infra`, `progress.py:358-360`). For that exact
  leaf the §6 row will now read "leaf did not run (transient infra — safe to re-run) — …",
  which is false: the leaf ran, at length, and the death is legible in the retained report a
  few lines below it. The patch already rewrote the *comment* directly above this dict
  (`assemble.py:80`, "ran, died of infra it reported") and the in-body prose
  `_unavailable_classification` builds for the placeholder itself (`leaves.py:2611-2616`,
  "having produced nothing, or ending on its own report…") — but missed this dict two lines
  further down, which is the fifth downstream restatement of the definition the brief's own
  invariant warns will "go stale the moment it widens" (only four were enumerated in
  Citations expected, plus this dict). `template/tests/test_leaf_status.py:135,188` pins the
  stale string, so nothing in the suite would catch the mismatch — it is silent, not
  gate-visible. One-line fix (e.g. `"leaf failed on transient infra — safe to re-run"`),
  but it needs a human/builder decision on the exact wording since it's user-facing prose,
  not a logic change.

- `target/template/src/pdca_harness/leaves.py:2520` — the comment above the reviewer's
  `_invoke_leaf_resilient` call, `"A transient (no-output) reviewer failure is retried with
  backoff…"`, is the same stale, narrower definition (developer-facing only, not
  operator-facing like the finding above, so lower stakes — no `[impl]` tag warranted on its
  own, noting it here since it's the same class of drift the invariant calls out and it sits
  right next to the fifth-site item above).

## Everything else checked and found sound

- `progress._note_terminal`'s precedence table (`_TERMINAL_PRECEDENCE`, `progress.py:...`)
  correctly lets a same-shape record overwrite newest-wins while blocking a farther-shape
  record (wrap-up, sub-agent) from burying a nearer one; traced through all the ordering
  permutations the test suite exercises (report→wrapup, report→subagent→wrapup,
  subagent→report) and the logic matches.
- `is_signal_death`'s dual-spelling boundary (`rc < 0` vs. shell `128+signum`) correctly
  excludes `TIMEOUT_RC` (-1001) without a special case, and `died_of_reported_infra`
  correctly gates on `rc not in (0, TIMEOUT_RC)` — the success-path (`rc == 0`) restoration
  of `produced`'s documented contract (iteration-1's defect #2) holds: `terminal` state can
  be left set at `rc == 0` and it is provably inert there.
  - `_kind_is_transient` now matches its own docstring: an absent `error` key is
    distinguished from the literal `"unknown"` (`kind = raw_kind if isinstance(raw_kind, str)
    and raw_kind.strip() else None`), and the free-text regex only ever runs for
    `kind == "unknown"` — iteration-2's defect #1 is closed, confirmed by reading the branch,
    not just the tests.
- `_is_subagent_event` is the single predicate used on both sides (classify / clear), so the
  stream spelling (`parent_tool_use_id`) and the persisted-transcript spelling
  (`isSidechain`) can't drift apart — iteration-1's main-session-scoping defect and
  iteration-2's transcript-spelling defect both check out against the current source.
- `_WORK_EVENT_TYPES` excludes `result` (`progress.py:465`), so a wordless `is_error` result
  can't silently clear a report via the "main session carried on" branch — iteration-2's
  defect #4 — and the drain's `if shape: ... elif ...:` structure keeps a report-bearing line
  from also being read as a clearing line.
- No new resource leak or concurrency bug: `terminal` is mutated only by the single drain
  thread and read by the caller after `reader.join()`, the same pattern the pre-existing
  `produced` / `latest_tool` dicts already use. The test helper `_fd1_parked`
  (`test_terminal_error_classification.py`) opens then closes the sink file *after*
  `dup2`-ing it onto fd 1 — correct idiom (the duplicate keeps the description alive), not a
  leak, despite looking suspicious at a glance.
- Re-parsing the same stream line's JSON across `_is_session_event` / `_terminal_error` /
  `_is_main_session_work` / `_stream_tool_label` is redundant, but it is the pre-existing
  shape of this module (`_is_session_event` and `_stream_tool_label` already each re-parse
  independently) and the brief explicitly directs the new reader to sit "beside it, in the
  same shape" — not a new inefficiency this patch introduces, and not hot enough (one leaf's
  own stdout) to be worth a refactor here.
- C4's red/green legs (`gate-logs/C4-verify.log`) are genuine: the red leg fails on the
  production assertions (`self.assertFalse(produced)`, retained-text `assertIn`s), not on an
  import/collection error, so the new test file is exercising the real code path, not a copy.
