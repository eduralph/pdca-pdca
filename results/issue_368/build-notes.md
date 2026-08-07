# Build notes — issue 368 / gate-timeout

Target: eduralph/pdca-harness @ main (built in `$PDCA_WORKTREE =
/home/eddie/pdca/pdca-harness.pdca-wt-l1`, base `abd6f1e`). All `path:line`
citations below are against that tree.

## What changed and why

The defect: no bound anywhere in the chain — `gates._run_one` invoked
`progress.run_with_heartbeat` with no timeout (`gates.py:409` on main), and
`run_with_heartbeat`'s signature had none (`progress.py:25-37` on main; `interval`
is only the heartbeat tick). A hung advisory gate held a Check beat 19h while the
heartbeat printed "… still working". Invariant to restore: no gate may consume
unbounded wall-clock; an expired bound is "the oracle did not answer"
(`unverifiable`, the #46 outcome), never a pass/fail verdict.

### 1. `template/src/pdca_harness/progress.py` — the bound itself

- `run_with_heartbeat` gains keyword-only `timeout: int | None = None`
  (`progress.py:47` post-fix) — criterion (a).
- `TIMEOUT_RC = -1001` (`progress.py:26-32`): the distinguishable timed-out
  outcome, returned in the returncode slot. Chosen outside anything a real child
  can produce (0..255 on exit, −signum ≤ −1 ≥ −64 on a signal death — and the
  group kill itself would yield −15/−9, which an unrelated external kill could
  also produce; a dedicated constant can't be confused with either). Keeping the
  `tuple[int, str, bool]` shape means zero churn at the four existing callsites
  (`gates.py:436`, `leaves.py:273`, `leaves.py:355`, `publish.py:749`).
- `Popen(..., start_new_session=timeout is not None)` (`progress.py:108-113`):
  sessionize **only** when a bound exists, so `timeout=None` is byte-identical to
  today (criterion a/c). The new session makes the child the leader of its own
  process group (pgid == pid), which is what expiry must kill: gates run
  `shell=True`, so the real work is a grandchild — killing only the shell orphans
  it, still burning the wall-clock the bound caps.
- The expiry check joins the existing wait loop (`proc.wait(timeout=interval)`,
  the brief's cited `progress.py:133`): a `deadline` is computed once, each pass
  waits `min(interval, remaining)`, and on `remaining <= 0` the group is
  terminated and the loop exits (`progress.py:155-176` post-fix). The
  `timeout=None` path takes the exact pre-fix branch (wait_for == interval, no
  deadline arithmetic beyond one `None` check).
- `_terminate_group` (`progress.py:200-218`): `os.killpg(SIGTERM)` → `wait(2s
  grace)` → `os.killpg(SIGKILL)` → `wait()` (reap; no zombie). Signals are
  best-effort (`ProcessLookupError`/`PermissionError` suppressed — the group may
  already be gone).

### 2. `template/src/pdca_harness/gates.py` — the schema keys + recording

- `_gate_timeout(chk, default)` (`gates.py:383-397`): the row's `timeout_secs`
  wins, else the `[gates] default_timeout_secs` fallback, else `None` (unbounded,
  unchanged). `0`/negative = explicitly unbounded, so one long row can opt out of
  a configured default. Non-numeric → `None` rather than crashing a gate run
  (consistent with `promotion_candidates`' tolerant `int()` at `gates.py:117-120`).
- `_run_one` gains `default_timeout` (`gates.py:400-402`, bound resolved at
  `gates.py:452`) and passes `timeout=bound` into `run_with_heartbeat`
  (`gates.py:459-462`); a `TIMEOUT_RC` return is recorded **`unverifiable`** with
  the evidence line `gate exceeded its {bound}s timeout` (`gates.py:463-467`) —
  criterion (b), the bound named. `_classify` is not touched: a timeout is not an
  exit code, so it must not flow through exit-code classification (`gates.py:469`).
- Both `_run_one` callsites (`gates.py:326-328`, the [[gates.checks]] loop, and
  `gates.py:352-355`, the host-CI parity rows) pass
  `default_timeout=cfg.gates_default_timeout_secs`.
- No change needed for the §6 routing: `unverifiable` already stays out of
  `_finalize`'s gating verdict (`gates.py:517` — only `fail` counts) and
  `assemble._unverifiable_items` (`assemble.py:353-359`) already routes every
  `unverifiable` row into SUMMARY §6 NEEDS-HUMAN, where C6 blocks accept — the
  #46/#165 discipline the brief's citations point at. The timed-out row rides the
  existing channel; that is the point of recording it as `unverifiable`.

### 3. `template/src/pdca_harness/config.py` — `[gates] default_timeout_secs`

- New `Config.gates_default_timeout_secs: int | None = None` field
  (`config.py:237-241`) — defaulted, so every synthetic `Config(...)` in the test
  suite keeps constructing.
- Parsed in `Config.load` (`config.py:460-467`, wired at `config.py:666`): unset / 0 / negative /
  non-numeric ⇒ `None` (unbounded — criterion (c), behaviour unchanged when
  nothing is configured).

### 4. `template/pdca.toml.jinja` — schema documentation (Surfaces: data)

- A TIMEOUTS comment block in the [gates] section (`pdca.toml.jinja:866-875`)
  documenting `timeout_secs`, `default_timeout_secs`, the `unverifiable`
  recording, and the `timeout_secs = 0` opt-out — the keys are instance-facing
  config, and an undocumented key is one an instance cannot discover (the same
  rationale `test_size_signal.TheShippedExampleMatchesTheDefaults` enforces for
  size-signal keys).

### Explicitly dropped / out of scope (per the brief)

- **Escalating heartbeat wording (proposal item 4)** — the brief allows it only
  "if trivial, else explicitly dropped". Dropped: any wording change to the
  heartbeat line is asserted nowhere and invites bikeshed at review, and the
  bound now yields an *incidental* improvement anyway — a bounded gate's final
  tick fires at the deadline remainder, so the timeout path is visibly active.
- Sweeping stragglers of a normally-exiting child (#372), persisting full gate
  output (#370) — those bundles `Depends on` this one and reuse the
  sessionization + `TIMEOUT_RC` seam shipped here.

## Alternatives ruled out

- **Raise an exception on expiry instead of returning `TIMEOUT_RC`.**
  `gates._run_one` wraps the call in `except Exception → "fail"` (`gates.py:469-470`);
  an exception would either be misclassified as `fail` (violating the invariant:
  a timeout is not a verdict) or force a new `except HeartbeatTimeout` arm at
  every current and future callsite. The brief also says "a distinguishable
  timed-out outcome is **returned**". Cost of the exception route: a new
  exception class + try/except at 4 callsites (~15 lines) *and* a behavioural
  trap for any future caller that forgets the arm; the sentinel is 6 lines and
  fail-safe (an unaware caller sees a nonzero rc — at worst a `fail`, never a
  silent pass).
- **Widen the return tuple to carry a `timed_out` flag.** Breaks all four
  existing unpack sites (`rc, output, _ = …`) for zero information the sentinel
  doesn't carry — a 4-line-per-callsite churn (~16 lines) with no gain.
- **`subprocess.run(timeout=…)` / `proc.kill()`.** Both kill only the direct
  child; under `shell=True` the real work is a grandchild and survives — the
  exact orphaning failure the brief's success criterion names. The group kill
  requires sessionization, hence `start_new_session` gated on `timeout is not None`.
- **Always sessionize (unconditional `start_new_session=True`).** Simpler, but
  the brief demands `timeout=None` byte-identical to today, and unconditional
  sessionization changes signal semantics for the *leaves* too (a Ctrl-C at the
  terminal would no longer reach an interactive child's group). Out of this
  bundle's scope; #372 ("reuses its process-group kill + sessionization") is
  where broader sessionization is decided.

## Test design (`template/tests/test_progress.py` — the brief's named file)

- `HeartbeatTimeout` (progress level, the brief's repro instruction):
  - `["sleep", "60"], timeout=1` → `TIMEOUT_RC` within the bound (elapsed
    asserted < 10s vs. the 60s the child wanted — generous for loaded hosts;
    post-fix it measures ~1.1s).
  - the `shell=True` variant spawns a background grandchild (`sleep 60 &`) and
    echoes `$$` and `$!` before blocking, then asserts **both** pids are gone
    (polled `os.kill(pid, 0)` → `ProcessLookupError`) — "no surviving group
    member", the orphaning failure made observable.
  - an unexpired `timeout=30` returns the real exit code (the bound changes
    nothing until it expires); every other test in the file exercises the
    `timeout=None` default path unchanged.
- `GateTimeoutRow` (schema level, through the production `gates.run_gates`
  chain, mirroring `test_gates_unverifiable.py`'s stub-config construction):
  - `timeout_secs = 1` on a `sleep 5` row → `unverifiable`, evidence contains
    `exceeded its 1s timeout`, `overall == "pass"` (kept out of the gating
    verdict).
  - `[gates] default_timeout_secs` fallback → same outcome with no per-row key.
  - `timeout_secs = 0` opts a row out of a configured default (runs to
    completion → `pass`).
  - no timeout anywhere → gate unchanged (`pass`).
  Pre-fix these go red **without any hang** (the brief's falsifiability shape):
  the progress tests error with `TypeError: unexpected keyword 'timeout'`, and
  the gate rows run their short `sleep 5` to completion, `pass`, and fail the
  `unverifiable` assertion in ~5s.

## Runner + evidence (red→green through the project's runner)

Runner: the offline driver suite the brief names and CONTRIBUTING.md documents —
`cd template && PYTHONPATH=src python3 -m unittest tests.test_progress`.

- **RED** (production hunks stashed, test in place): `FAILED (failures=2,
  errors=3)` — 3 × `TypeError: run_with_heartbeat() got an unexpected keyword
  argument 'timeout'`, 2 × `AssertionError: 'pass' != 'unverifiable'`.
  (The two "unchanged behaviour" tests pass pre-fix by design — they pin
  criterion (c), not the defect.)
- **GREEN** (fix restored): `Ran 26 tests … OK` (~6s).
- **Full offline suite**: `Ran 1380 tests … OK (skipped=2)` (~20s; the 2 skips
  are pre-existing environment skips, present on main).
  - First full-suite run caught a real interaction: `test_size_signal.py:446-468`
    regex-scans commented `# key = int` lines after `[driver.size_signal]` in
    `pdca.toml.jinja`, and my bare example line `#   default_timeout_secs = 3600`
    matched it. Fixed by giving the example line a trailing comment (which takes
    it out of that regex's `$` anchor) — the shipped doc block is intact.
- **Template render check** (`tests.test_render_and_run`, the root-suite job the
  repo's render-check.yml CI runs, via the instance venv's python which has
  copier): `Ran 1 test … OK` — the edited `pdca.toml.jinja` still renders and
  the generated project's slice runs.

No formatter / pre-commit hooks are configured in the target repo (no
`.pre-commit-config`, no pyproject/ruff/flake8 config, `core.hooksPath` unset);
the offline suite + render CI are the commit bars, both green.

## Forced self-refutation (a)/(b)/(c)

- **(a) Genuine red?** Yes — actually reverted and re-run: with
  `git stash push -- template/src template/pdca.toml.jinja` the named test module
  fails 5 ways (3 errors + 2 failures, verbatim above); with the stash popped it
  is green. The test binds the objective, not an adjacent check.
- **(b) Production path?** Yes — the tests import `pdca_harness.progress` and
  `pdca_harness.gates` from `template/src` (PYTHONPATH=src), and `GateTimeoutRow`
  drives the full production chain `run_gates → _run_checks → _run_one →
  run_with_heartbeat` with a real subprocess; nothing is mocked or re-implemented.
- **(c) Fixture includes the fault?** Yes — the fixture *is* the fault: children
  that genuinely outlive the bound (`sleep 60`, `sleep 5`), including the
  `shell=True` grandchild case that reproduces the orphaning hazard, and the
  tests assert the killed group members are actually dead by probing their pids,
  not by trusting the return value.

## External dependencies

None beyond the brief's declaration (`External dependencies: none`) — stdlib
`os.killpg`/`signal` only (POSIX, like the harness's existing `flock`/worktree
machinery). Nothing to declare NEEDS-HUMAN.
