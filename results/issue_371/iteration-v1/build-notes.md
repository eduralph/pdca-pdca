# Build notes — issue 371 / gate-confirm-failed-gating-row

Target: eduralph/pdca-harness, built in `$PDCA_WORKTREE` on `00dc958` ("pdca-integrate:
issue_409", stack-base `pdca-integration/main`) — i.e. on 409's folded result as the
brief's ordering note asks. Line numbers below are on that tree with the patch applied.

## What changed

**`template/src/pdca_harness/gates.py`**
- `_run_one` (`:505-508`) gets a keyword `confirm: bool = False`. After the first run, if
  `confirm` and the row is gating and the first run classified `fail` with a real exit
  code (`rc is not None`) and `_confirm_enabled(chk, cfg)`, it runs the command once more
  (`:586-598`). The `cmd_error` early return (`:515-522`) is unchanged, so a misconfigured
  delegation is never confirmed.
- The single run was pulled out of `_run_one` into `_attempt` (`:641-671`) unchanged in
  behaviour (same heartbeat call, same timeout → `unverifiable`, same `_classify`, same
  exception → `fail` with the exception as output). Each call returns
  `{rc, output, result, evidence, started, duration}`.
- `_attempt_outcome` (`:674`): the per-sample label for `attempts`; `rc is None` → `"error"`.
- `_confirm_enabled` (`:680`): `cfg.gates_confirm_gating_fail is True and
  chk.get("confirm_fail", True) is True` — only absent/literal `true` enables, so a
  malformed value falls back to today's one-run behaviour.
- `_combine_attempts` (`:690`): one sample → itself; fail→pass → `pass`, confirm-run
  evidence, flaky; fail→fail → `fail`, confirm-run evidence; anything else → `fail`, first-run
  evidence.
- Row keys `attempts` and `flaky` are only added when a confirm actually ran (`:606-612`),
  so every other row is byte-identical to before (keeps `test_gate_logs`' "no new keys"
  contract for no-bundle runs).
- `_write_gate_log` (`:710`) takes optional `attempts` + `flaky`. One run → exactly the old
  format. Two runs → top-level header with `# outcome: <combined>`, `# flaky:`,
  `# attempts:`, then one `# ==== attempt N of 2 ====` block per run with its own
  `# start:`, `# duration_secs:`, `# exit:`, `# outcome:` and verbatim output. The exit
  text was moved into `_exit_line` (`:771`) so both formats share it. Still one file.
- Callers: `_run_checks` gains `confirm=False` (`:344`) and passes it to both the
  `[[gates.checks]]` loop (`:407`) and the host-CI loop (`:435`). Only `run_gates`
  (`:198`) and `run_gates_dry` (`:277`) pass `confirm=True`. `run_working_tree`,
  `run_integration` and publish's host-CI gate (`publish.py:930`, untouched) keep the
  default, so they run a failing row once (clause 4b).

**`template/src/pdca_harness/config.py`** — field `gates_confirm_gating_fail: bool = True`
(`:275-280`, beside `gates_default_timeout_secs`), parsed at `:582-588` (absent ⇒ True; a
non-boolean ⇒ False with a stderr line, the `dependency_halt` pattern), passed to the
constructor at `:839`. `_normalize_host_ci` already copies every key of a table entry, so
`confirm_fail` survives it with no code change; only its docstring now says so (`:882-883`).
The test proves the survival through `Config.load`.

**`template/src/pdca_harness/assemble.py`** — `_flaky_items` (`:574`) next to
`_unverifiable_items`, wired into `collect_needs_human` at `:341` as
`NeedsHumanItem(t, HUMAN)`. HUMAN regardless of element (a C4 row would otherwise be IMPL
in `_failed_gating_items`). I left `no_verdict` at its default False on purpose: both
samples are real verdicts on this round's tree, and the issue's promise is that auto-iterate
*defers* the flaky item (#409), which `no_verdict=True` would prevent. `overall` needs no
change: `_finalize` counts only gating `fail`, and the row records `pass`.

**Docs** — `template/pdca.toml.jinja:1005-1018` (comment block before `[gates]`, with the
upgrade note for model-backed rows; comment-only, so no `copier update` conflict on a
registered line) and `docs/05-check.md:451-465` (new bullet in "Three properties every row
has").

Not touched (out of scope per brief): `size_signal.py` (its docstring still says "the
recorder has not landed" at `size_signal.py:167`; that's now stale but the brief says no
change there — worth a follow-up), `publish.py`, auto-iterate logic.

## Test — `template/tests/test_gate_confirm.py` (25 tests)

Drives the real `gates.run_gates` / `run_gates_dry` / `run_working_tree` /
`run_integration` / `_run_checks` / `_run_one` and `assemble.collect_needs_human`, with
shell commands that count their own runs in a marker file. Only two tests patch anything:
the "exception" cases wrap `progress.run_with_heartbeat` to raise on a chosen call (the
real function runs on the others) — a shell command can't make the subprocess layer raise.

Clause map: (1) `test_fail_then_pass_records_pass_flaky_after_two_runs`; (2)
`test_fail_then_fail_…`; (3) timeout / unverifiable / deferred / exception tests, each
checking `path_line == "evidence-run-1"`; (4) `Bounds.*` incl. TOML parse and host_ci
`confirm_fail` via `Config.load`; (4b) `CheckTimeOnly.*`; (5) `Evidence.*`; (6) `Routing.*`.

For the publish host-CI path I used the brief's allowed substitute — `_run_one` called
exactly as `publish.py:930` calls it (no confirm switch). Driving `publish._host_ci_gate`
itself needs a git remote and a pinned base; not worth it when the call shape is identical.

## Runs (through the instance's own gate scripts)

- `engine/scripts/run-verify.sh` (C4): green leg `Ran 25 tests … OK`; red leg (production
  hunks reverted) `Ran 25 tests … FAILED (failures=10, errors=6)`; verdict
  `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`.
- `engine/scripts/run-suite.sh` (T3): template-repo suite 24 OK; driver suite 2160 OK
  (2 skipped). So `test_gate_logs`, `test_update_compat`, etc. still pass.
- `engine/scripts/run-docs-check.sh` (T2): lint OK, render + link audit OK.
- Formatter / hooks: the target repo has no pre-commit config, ruff/black config, or
  formatter step in CONTRIBUTING; nothing to run. Lines kept under the file's existing width.

## Refute-your-own-test

- **(a) Genuine red?** Yes. `run-verify.sh` reverts the production hunks and re-runs: 10
  assertion failures (the core ones are `AssertionError: 1 != 2` — the command ran once,
  not twice; the log has no attempt blocks; `overall` is `fail`) plus 6 errors
  (`_run_checks() got an unexpected keyword argument 'confirm'`,
  `'Config' object has no attribute 'gates_confirm_gating_fail'`). No import failure, so
  not read as UNVERIFIABLE.
- **(b) Production path?** Yes. Every test calls the production entry points named above;
  the commands are real subprocesses through `progress.run_with_heartbeat`. No copy of the
  combine logic exists in the test.
- **(c) Fixture includes the fault?** Yes. The fault is "a gating command that fails once
  then passes"; the marker-file command really does that, and the timeout case really
  sleeps past a real `timeout_secs = 1`.

## Alternatives ruled out

- Wrapping the confirm in `_run_checks` instead of `_run_one`: would need the log writing
  and row building duplicated there (~40 lines) and wouldn't let `_write_gate_log` put both
  runs in one file without passing raw outputs out of `_run_one`. The brief also scopes it
  to `_run_one`.
- Always emitting `attempts` (even `["pass"]`): changes every row of every gate run and
  breaks the "no new keys" contract in `tests/test_gate_logs.py` for no-bundle runs.
- `no_verdict=True` on the flaky §6 item: rejected, see assemble note above.

## Housekeeping

I redirected the T3 suite output to `/tmp/suite371.log` while reading it — outside the
roots I'm meant to write to. Harmless (a text log), but noting it since I can't clean it up.
