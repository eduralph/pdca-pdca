# PR description

## Summary
**User impact:** when one of a project's quality checks fails — including a failure
that blocks a change from moving forward — the run keeps only the last line of that
check's output, cut to 120 characters, and throws the rest away. Anyone investigating
afterwards has almost nothing to go on: in a real incident, a transient CI check
failure recorded only "xtask: … failed with exit status: 101", and which test had
failed was unrecoverable — the post-mortem had to be pieced together from reflog
stamps and file timestamps, and still could not name the test.

This PR saves each check's complete output to a small per-check log file stored with
the run's other records, so the full reason behind every verdict can be read after
the fact.

Reported in [#370](https://github.com/eduralph/pdca-harness/issues/370).

## What to look at
The heart of the change is in `template/src/pdca_harness/gates.py`: the spot where a
check's output was already being captured now also writes it to
`gate-logs/<rule_id>.log` inside the bundle, and a small helper formats the header.
To try it: configure any `[[gates.checks]]` entry, run a bundle through its Check
step, and open `results/issue_<id>/gate-logs/` — one log per check, header plus the
verbatim output. Or run the new test suite:
`cd template && PYTHONPATH=src python3 -m unittest tests.test_gate_logs`.

## Root cause
`_run_one` captures the command's combined stdout+stderr (gates.py:459 on main), but
`_classify` keeps only the last line (gates.py:479, :502) and the row truncates it to
120 characters (gates.py:475). `_finalize` (gates.py:516-520) writes only those rows
into `check-gates.json`/`check-gates.md`, so nothing anywhere retains the output that
decided the verdict.

## Fix
- `state.GATE_LOGS_DIR = "gate-logs"` names the directory once, next to the other
  bundle-artifact names, and joins `DOWNSTREAM_OF_BRIEF` so the iterate archive moves
  it per round — each `iteration-v<N>/` keeps the full basis of its own gate run.
- `run_gates` (bundle-scoped) passes `log_dir` into `_run_checks`; `_run_one` stamps
  start time + monotonic duration around the existing capture and writes
  `gate-logs/<rule_id>.log` via the new `_write_gate_log`: a header (cmd, cwd,
  `$PDCA_WORKTREE`, start, duration, exit/outcome) then the output verbatim. The
  previous run's `gate-logs/` is cleared first, so a check removed from config leaves
  no stale log masquerading as current evidence.
- Rows additively gain `log` (bundle-relative path) and `duration_secs`; `_row` and
  `render_md` are untouched, so every existing consumer of `check-gates.json` sees
  the same keys as before. The 120-char evidence line stays as the summary.
- On a timeout (the #368 bound) the partial capture up to the kill is logged with a
  header naming the timeout, so a hung check's log shows *where* it hung.
- A log-write failure never breaks the gate run or alters a verdict, but it is never
  silent: the row carries `log_error` with the reason and a stderr line names the
  check. A non-directory squatting on the `gate-logs` path is deliberately reported
  rather than deleted — the harness never creates that path as a file, so removing it
  would destroy data it does not own.
- Repo-scoped runs (`run_working_tree`) and dry re-gates (`run_gates_dry`, behind
  `pdca revalidate`) pass no `log_dir`: the former keeps today's behaviour, the
  latter must not overwrite the frozen evidence behind a frozen verdict.
- `driver._archive_iteration` now moves directory entries as well as files, which is
  what lets `gate-logs/` ride the existing archive list instead of a special case.

## Verification
- **Claim:** on current main a gate's full output is discarded. **Checked:**
  `template/src/pdca_harness/gates.py:459` on main — the capture is consumed by
  `_classify` (`:479`, `:502` keeps only the last line), truncated to 120 chars
  (`:475`), and `_finalize` (`:516-520`) writes only the rows; no other write exists.
- **Claim:** the new row keys are additive — no existing consumer changes.
  **Checked:** `template/src/pdca_harness/gates.py:525` (`_row`) and `:588`
  (`render_md`) on main — both untouched by the diff; the keys are set on the dict
  after `_row` returns.
- **Claim:** per-round retention rides the existing archive machinery. **Checked:**
  `template/src/pdca_harness/driver.py:392` on main (`if src.is_file():` — the
  archive step previously moved only files) and
  `template/src/pdca_harness/state.py:60` (`DOWNSTREAM_OF_BRIEF`, the single-sourced
  list the directory joins).
- **Claim:** the timeout case attaches the partial capture. **Checked:**
  `template/src/pdca_harness/gates.py:459-467` on main — on expiry
  `run_with_heartbeat` returns `TIMEOUT_RC` plus everything captured before the kill,
  so the same write path logs it with a timeout-naming header.
- **Test:** `template/tests/test_gate_logs.py` — 9 tests: header + verbatim
  multi-line body, additive row keys, stale-log clearing, write failure surfacing
  (`log_error` + stderr, verdict unchanged, recorded in `check-gates.json`), a real
  hanging command under a 1s bound logging its pre-hang output, repo-scoped runs
  unchanged, dry re-gate leaving the log byte-identical, and archive retention.
  With the production hunks reverted, 8 of 9 fail (the ninth asserts today's
  repo-scoped behaviour and must pass on both sides); with the patch, 9/9 pass.
  Full offline driver suite: 1438 tests OK (skipped=2); render/update-compat
  suites: 7 tests OK.

Fixes #370
