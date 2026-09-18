# Advisory code review — issue #534

Second-lens read of the diff (introduced-bug and reuse/efficiency lens), grounded on
the target checkout. The main mechanism — drop the Stop registration, make the hook's
no-arg path inert, judge the contract at `handoff.session`'s reap via
`report_at_reap`/`stop_problems`, abandon reason printed before (not instead of) the
problem list, per-bundle error isolation — reads correctly and matches the three
carry-forward fixes from prior iterations (blank-abandon handling in
`_abandon_reason`, per-bundle `try/except` in the loop, abandon no longer suppressing
the list). One finding below is a real gap the patch introduces; the rest are minor.

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/handoff.py:462-468` (target,
  `stop_problems`): for a planner session, the shared `_doctor.registered_ids(cfg)`
  pre-check runs unconditionally whenever `bundles` is non-empty, before the
  per-bundle loop — even when every bundle in the batch is legitimately unplanned
  (`allow_absent=True`, no `brief.md` written at all). In that case `check_planner`
  itself never touches the `doctor` module (it returns `[]` at the `if not bp.exists()`
  guard, `handoff.py:112-115`), so the shared pre-check is consulting an input none of
  the bundles actually need. If `pdca.toml`'s `[[doctor.checks]]` table happens to be
  malformed for a reason unrelated to this session, a batch-planner reap that would
  otherwise print nothing (every id correctly left unplanned) instead prints "could not
  check the planner session's exit contract (...) — nothing reported" — a false alarm
  at a report-only checkpoint, on the exact "leave it UNPLANNED" path the brief calls
  out as a legitimate outcome. This is new code (the pre-check didn't exist before this
  iteration's per-bundle-isolation fix); worth gating it behind "does any bundle in
  this batch actually have an authored `brief.md`" before spending the shared read, or
  moving it back inside the per-bundle `try` so an unrelated broken table only ever
  produces a per-bundle note. Not covered by any test in `test_handoff_reap.py` — the
  existing broken-config tests all use briefed bundles
  (`test_a_broken_config_is_one_line_for_the_whole_batch`).

- `template/src/pdca_harness/handoff.py:462-468` and `check_planner`
  (`handoff.py:99-129`): minor duplicate work, not a bug. The shared
  `_doctor.registered_ids(cfg)` call's result is discarded — it exists only to raise
  early — and every bundle in the loop still re-parses `pdca.toml` on its own via
  `check_planner` → `_doctor.unregistered_dependencies` (→ `registered_ids`) and
  `_doctor.failing_dependencies` (→ `current_doctor_checks`). So a planner reap over N
  bundles parses `pdca.toml` up to `1 + 2N` times instead of once. This only runs once
  per session's reap and the file is small, so it's not worth blocking on — flagging
  for awareness, not a fix demand.

No other correctness bugs found: the `session()` finally-block merge
(`{**_read_json(path), **registered}`, `handoff.py:342`) correctly re-asserts the
driver-registered `bundles`/`role`/`require_artifact`/`baseline` over whatever the leaf
wrote to its own scratch file while preserving `passed`/`abandoned`, matching the
"report the bundles the driver actually registered" test. `report_at_reap`'s own
`try/except` correctly prints an already-emitted abandon reason before the one-line
"could not check" note on a shared-check failure. The hook's no-argument path never
touches stdin and exits 0 unconditionally, satisfying the turn-end criterion regardless
of `PDCA_HANDOFF_ROLE`. The `test_publish_slice.py` edit that adds `redirect_stderr`
around `run_publish` is correctly scoped (that file already imports `io` and
`redirect_stderr`) and is the only pre-existing test call site this patch's new
reap-report chattiness required touching — the other `handoff.session`-driving test
file, `test_leaf_workspace_admission.py`, already wraps every leaf spawn in its own
`_quiet()` helper, so it needed no change.
