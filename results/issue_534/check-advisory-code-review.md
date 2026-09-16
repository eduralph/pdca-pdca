# Advisory code review — issue #534

Second-lens pass (bugs the patch introduces; reuse/simplification/efficiency). Traced
the reap path end to end against the target tree: `session()`'s `finally` block, the
`registered`/`state` merge, `report_at_reap`, `stop_problems`, `_doctor_table_problem`,
`_printable`/`_emit`, and `handoff_guard.py`'s new no-argument/`--abandon`/`--check`
dispatch. No correctness bug found in this diff — the exception handling around each
new failure mode (deeply-nested JSON on the scratch file, a directory in an artifact's
place, a non-UTF-8 artifact, a structurally-broken `pdca.toml`, an unparseable
`pdca.toml`) is exercised by `test_handoff_reap.py` and matches what the target source
actually does; I did not find a case the tests miss. Two minor, non-blocking
observations, neither rising to something a human needs to decide:

- `template/src/pdca_harness/handoff.py:340-349` (`_doctor_table_problem`) parses
  `pdca.toml` twice on a planner reap when the table *is* readable: the explicit
  `tomllib.loads` call, then again inside `_doctor.registered_ids(cfg)` →
  `Config.current_doctor_checks()` (`template/src/pdca_harness/config.py:547-551`),
  which re-reads and re-parses the same file. This isn't redundant by accident —
  `current_doctor_checks()` swallows `TOMLDecodeError` and falls back to the run's
  snapshot, so the explicit parse is what lets the reap catch that case (confirmed by
  `test_a_pdca_toml_that_does_not_parse_is_a_broken_table_too`,
  `test_handoff_reap.py:1373-1389`) — but it is a double read+parse of the same small
  file, once per planner-role reap. Cheap in absolute terms (reap runs once per
  session, not in a loop), so not worth a round on its own; worth folding into one
  parse if this function gets touched again.
- `template/.claude/hooks/handoff_guard.py:73-76` adds a new "unknown mode" branch
  (any argv other than `--check`/`--abandon`, e.g. a typo, now exits 2 with a message
  instead of silently falling through to the old `_stop_verdict()`, which returned 0
  when `PDCA_HANDOFF_ROLE` was unset). This is a reasonable tightening — it only
  matters for a human/session invoking the script directly with a bad flag, not the
  retired Stop path, which always invokes with empty argv — but it has no direct test
  in either `test_handoff.py` or `test_handoff_reap.py`. Not required by the brief's
  criteria, so not a gap in this bundle's success criterion.

Scope check: the `leaves.py` edit at criterion (g)'s named exception (the stale "Stop
hook" comment at `leaves.py:916-917`) is confirmed still untouched in the target tree,
and the comment fix at the old `:1104-1108` location (now `leaves.py:1105-1109`) sits
between, not inside, the two `do_plan_batch` ranges the brief reserves for #480
(`:1070-1078`/`:1126-1136` old numbering) — no encroachment found.

No reuse/duplication issue found: `_printable` (`handoff.py:303-314`) is genuinely new
logic with no existing escaping helper elsewhere in `template/src` it should have
called instead.
