# PR description

## Summary
**User impact:** if one configured gate command hangs — a wedged test suite, a
stuck container — the whole review pass never finishes. The progress heartbeat
keeps printing "… still working", so the run looks alive while nothing is
happening; in practice a hung *optional* check held a run for over 19 hours
until a human noticed and killed it by hand.

This PR lets a project put a wall-clock limit on gate commands (per check, or
one default for all): when the limit expires, the command and everything it
spawned are killed, and the check is reported as "could not be verified" for
the human to weigh — never as a pass or fail the command didn't actually reach.

Reported in [#368](https://github.com/eduralph/pdca-harness/issues/368).

## What to look at
The bound itself lives in `template/src/pdca_harness/progress.py`
(`run_with_heartbeat` plus a new group-terminate helper); the configuration
keys and the "could not be verified" recording live in
`template/src/pdca_harness/gates.py` and `config.py`, documented in the
`[gates]` section of `template/pdca.toml.jinja`. To try it: give a
`[[gates.checks]]` row `cmd = "sleep 60"` and `timeout_secs = 5` (or set
`[gates] default_timeout_secs`) and run the gates — the row is killed at the
bound and surfaces at sign-off as unverifiable. Or run the tests:
`cd template && PYTHONPATH=src python3 -m unittest tests.test_progress`.

## Root cause
`gates._run_one` invokes every gate command through
`progress.run_with_heartbeat` (`gates.py:436-439` on main), whose signature has
no timeout parameter (`progress.py:25-37` — `interval` is only the heartbeat
tick), and whose wait loop (`proc.wait(timeout=interval)`, `progress.py:133`)
only re-arms the heartbeat, so it can wait forever. No `[[gates.checks]]`
schema field existed either, so no configuration could bound a row.

## Fix
- `run_with_heartbeat` gains a keyword-only `timeout: int | None = None`. The
  child is started with `start_new_session` **only when a bound exists** (its
  pgid then equals its pid, so `os.killpg` reaches the shell's grandchildren);
  the `timeout=None` path takes the exact pre-fix branch.
- On expiry `_terminate_group` SIGTERMs the group, escalates to SIGKILL after a
  2s grace, and reaps the child (no zombie). The returncode slot carries the
  sentinel `TIMEOUT_RC = -1001` — outside 0..255 and any `-signum` a real child
  can produce — so the `tuple[int, str, bool]` return shape is unchanged for
  the four existing callers, and an unaware caller sees a nonzero rc (at worst
  a fail, never a silent pass).
- `gates._gate_timeout` resolves a row's bound: the row's `timeout_secs` wins
  over the `[gates] default_timeout_secs` fallback; `0`/negative means
  explicitly unbounded (one long row can opt out of a configured default);
  non-numeric is treated as unconfigured rather than crashing the gate run.
- A `TIMEOUT_RC` return is recorded `unverifiable` with the evidence line
  `gate exceeded its {N}s timeout` — it bypasses exit-code classification (a
  timeout is not an exit code), stays out of the gating verdict, and rides the
  existing unverifiable channel to sign-off.
- `Config.gates_default_timeout_secs` (default `None`) parses the new `[gates]`
  key; unset / 0 / negative / non-numeric all mean unbounded.

## Verification
- **Claim:** on main there is no bound anywhere in the chain. **Checked:**
  `template/src/pdca_harness/progress.py:25-37` on main — no `timeout` in
  `run_with_heartbeat`'s signature; `template/src/pdca_harness/gates.py:436-439`
  — `_run_one` passes none; `progress.py:133` — the wait loop only paces the
  heartbeat.
- **Claim:** a timed-out row stays out of the gating verdict and reaches the
  human. **Checked:** `template/src/pdca_harness/gates.py:488` on main — only
  `result == "fail"` on a gating row fails `overall`;
  `template/src/pdca_harness/assemble.py:353` — every `unverifiable` row is
  lifted into the sign-off summary's NEEDS-HUMAN list. Recording expiry as
  `unverifiable` rides both existing paths untouched.
- **Claim:** killing only the shell would orphan the real work. **Checked:** by
  test — the `shell=True` case spawns a background grandchild, echoes both
  pids, and asserts both are gone after expiry (polled `os.kill(pid, 0)` →
  `ProcessLookupError`): no surviving group member.
- **Claim:** nothing configured ⇒ behaviour unchanged. **Checked:**
  sessionization is `start_new_session=timeout is not None`, and the
  `timeout=None` wait path is the pre-fix branch; the "no timeout configured"
  and "unexpired bound" tests pass even without the fix (they pin the unchanged
  behaviour), and every other test in the module exercises the default path.
- **Test:** `template/tests/test_progress.py` — 7 new tests: the plain and
  `shell=True` expiry cases (bounded within ~2s, group verified dead), an
  unexpired bound returning the real exit code, and four `[[gates.checks]]`
  rows driven through the production `run_gates` chain (`timeout_secs`,
  `default_timeout_secs` fallback, `timeout_secs = 0` opt-out, nothing
  configured). Fails pre-fix **without any hang**: 3 ×
  `TypeError: unexpected keyword argument 'timeout'`, 2 ×
  `AssertionError: 'pass' != 'unverifiable'`. Passes post-fix (26 tests, ~6s).
  Full offline driver suite: 1380 tests OK; the template render check
  (`tests.test_render_and_run`) passes with the edited `pdca.toml.jinja`.

Fixes #368
