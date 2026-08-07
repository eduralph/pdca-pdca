# Build notes — issue 372 / straggler-sweep-on-normal-exit

Target: eduralph/pdca-harness @ main (built in `$PDCA_WORKTREE` at `881f988`;
`template/src/pdca_harness/progress.py` and `template/tests/test_progress.py` are
byte-identical between `881f988` and `origin/main`, and `patch.diff` was verified to
`git apply --check` cleanly on `main`). Line citations below are post-patch worktree
lines unless marked "base".

## What changed and why

The defect: `run_with_heartbeat` waited on the **direct** child and returned; under
`shell=True` (every gate) that child is only a shell, so backgrounded work survived
the call. #368 (folded in `main` via PR #400) sessionizes only when `timeout` is set
(base `progress.py:113`) and kills the group only on expiry (base `progress.py:169`)
— a normal exit, the overwhelmingly common path, was never swept, and unbounded
captured children were never sessionized at all.

Changes, mapped to the brief's criterion:

- **(a) Sessionization breadth** — `progress.py:126`:
  `sessionize = os.name == "posix" and (capture or stream_json or timeout is not None)`,
  passed as `start_new_session=sessionize` (`progress.py:130`). This is exactly the
  brief's formula; `tee_stderr`-only calls (stdout inherits the terminal) and fully
  interactive calls stay unsessionized, keeping the terminal's foreground group as
  today. Widens #368's condition **in place** rather than duplicating a mechanism.
- **(b) Normal-exit sweep** — `progress.py:216-224` call `_sweep_stragglers`
  (`progress.py:256-291`): probes the group, and only if a **live** member survives
  prints ONE stderr note naming the command, then SIGTERM → 2s polled grace →
  SIGKILL via `os.killpg` on `pgid == proc.pid` (the child was session leader).
- **(c) Kill-then-close order** — the sweep sits **before** the reader join
  (`progress.py:226`, base `progress.py:190-191`) and stream close (`progress.py:229`,
  base `progress.py:192-194`), mirroring the timeout path (`_terminate_group` runs
  inside the loop, before the join/close). A straggler that inherited the capture
  pipe keeps the drain thread blocked mid-read; closing the stream then waits on
  that blocked reader. Killed first, the last writer dies → EOF → join/close can't
  block. (The brief's peer-callsite line numbers — wait loop `:133`, join `:151` —
  are offset from what `main` actually holds: wait loop at base `:159`, join at
  base `:190-191`; the constructs are unambiguous and are the ones edited.)
- **(d) Widened abort sweep** — the wait loop is wrapped (`progress.py:181-214`);
  on Ctrl-C/abort (`except BaseException`, `progress.py:208`) the group is swept via
  `_terminate_group` when **sessionized** (`progress.py:213`), not only when bounded.
  On the folded base no interrupt-path sweep existed at all in `progress.py` (grep:
  the only `_terminate_group` caller was the expiry branch, base `:169`), so
  "widening" here means: the kill condition is `sessionize`, of which #368's
  `timeout is not None` is a strict subset. Re-raised — an interrupt stays an
  interrupt.
- **(e) POSIX gate** — the `os.name == "posix"` conjunct (`progress.py:126`) turns
  off both sessionization and every sweep site (`:213`, `:216`) off-POSIX. No
  regression relative to base: CPython's Windows `_execute_child` ignores
  `start_new_session` (its parameter is literally `unused_start_new_session`), so
  base already never truly sessionized there, and the expiry path's `os.killpg`
  was already broken-by-absence on Windows before this change (out of scope).
- **(f) Silence when clean** — `_sweep_stragglers` returns before printing anything
  when `_group_alive` is false (`progress.py:277-278`); asserted byte-identical
  stderr in `test_no_survivors_no_sweep_no_note`.

### Zombie-aware group probe (`_group_alive`, `progress.py:293-323`)

`killpg(pgid, 0)` counts an **unreaped zombie** as a group member. Under a
non-reaping PID 1 (a container where the test runner is init) a fully-dead group
would look alive forever → a phantom sweep note (and a burned 2s grace) on exits
that left nothing running — violating (f) exactly in the environment the brief
warns about. So on Linux the probe reads `/proc/<pid>/stat` (state field after the
last `)`, `Z` ≠ survivor) and falls back to the `killpg` probe only where `/proc`
does not exist (other POSIX). The same zombie-awareness is mirrored in the test's
liveness helper (`test_progress.py:258-276`), per the brief's explicit instruction
never to use bare `kill(pid, 0)`.

### Known limitation — zombie table entries (deferred to #383)

The swept grandchild is **not** this process's child, so it cannot be reaped here:
under a minimal-container init the group kill leaves a zombie table entry. This is
recorded in the `_sweep_stragglers` docstring (`progress.py:273-280`) and must be
carried into the PR prose. Per the brief's scope, **no global reaper thread was
added**: a naive `waitpid(-1)` reaper can steal exit statuses from concurrent lane
`Popen.wait()`s and corrupt a gate verdict — strictly worse than the zombie. The
subreaper design is #383 (milestone 0.60.0).

## Alternatives ruled out (with cost)

1. **Sessionize unconditionally** (drop the `capture or stream_json or timeout`
   guard; ~1 line shorter): breaks the interactive leaves — a session leader has no
   controlling terminal, so the interactive `claude` child loses terminal job
   control and the human's Ctrl-C no longer reaches it. Criterion (a) explicitly
   excludes them; `test_interactive_shaped_call_is_not_sessionized` pins it.
2. **Reuse `_terminate_group` for the normal-exit sweep** (save ~35 lines): it
   signals unconditionally and ends in `proc.wait()`. Folding in "probe first, note
   only when swept, don't wait on an already-reaped leader" means threading two
   behaviours through the #368 path — the same line count with the timeout
   semantics no longer byte-identical. A separate `_sweep_stragglers` keeps #368's
   path untouched.
3. **`killpg(pgid, 0)` probe instead of the `/proc` scan** (~14 lines shorter):
   zombie-blind — see above; fails (f) under a non-reaping PID 1.
4. **Global reaper thread**: forbidden by the brief's scope; see #383 note.

The brief names an **Invariant to restore** (no work outlives its cycle), so the
target was the smallest change restoring it across *all* captured/streamed/bounded
children — not the smallest diff; a gate-path-only sweep was never a candidate
(leaves leak identically through the same function, `leaves.py:274`).

## Test (template/tests/test_progress.py, class `StragglerSweep`, :241-361)

Extends the file the brief names; class-level `skipUnless(os.name == "posix")`.

- `test_captured_shell_straggler_is_swept_after_normal_exit` — real
  `shell=True` child backgrounds `sleep 300` with stdio detached (so the RED run
  fails in the test's own 8s bounded poll instead of hanging on the pipe), asserts
  the straggler is gone (zombie-aware), exactly one note, note names `sleep 300`.
  A cleanup SIGKILLs the pid regardless of outcome so a red run can't leak the
  very straggler under test.
- `test_sweep_precedes_the_capture_close_no_drain_hang` — the straggler
  (`sleep 10`) **inherits the capture pipe**; unswept, the call cannot return
  before the 5s reader join (base `:190-191`) + blocked close, so `elapsed < 4.0`
  is deterministic red (measured red: 10.0s) and green ~0.3s.
- `test_no_survivors_no_sweep_no_note` — clean exit ⇒ stderr byte-identical (`""`).
- `test_captured_and_streamed_children_are_sessionized` /
  `test_interactive_shaped_call_is_not_sessionized` — pgid==pid checks run inside
  the real spawned child.

## Red→green evidence (project runner: INTEGRATION.md §3, offline driver suite)

- Green (fix applied): `cd template && PYTHONPATH=src python3 -m unittest
  tests.test_progress` → `Ran 31 tests … OK` (6.3s).
- Red (production hunks reverted via `git checkout -- …progress.py`, tests kept):
  `FAILED (failures=3)` in 24.2s — `straggler 1566367 survived the normal exit`;
  `10.004… not less than 4.0 : call blocked on the straggler-held pipe`;
  `1 != 0 : capture=True must sessionize the child`. Deterministic, bounded.
- Fix re-applied: `OK` again; full offline driver suite:
  `Ran 1458 tests in 23.4s — OK (skipped=2)`. Root template-repo suite: 7 skips
  (needs copier — documented condition), no failures. No leaked `sleep` processes
  on the host after the runs (`pgrep` clean).

## Forced self-refutation

- **(a) Genuine red?** Yes — production hunks reverted, tests re-run through the
  project runner: 3 failures (quoted above), each failing the exact criterion
  clause it binds; restored → green.
- **(b) Production path?** Yes — the tests import `pdca_harness.progress` from
  `template/src` (the module the patch changes) and call `run_with_heartbeat`
  itself; no mocks, no re-implementation; real `/bin/sh` children, real signals.
- **(c) Fixture includes the fault?** Yes — the fixtures *are* the fault: a real
  backgrounded `sleep` surviving a real shell's exit, and in the ordering test the
  straggler genuinely holds the capture pipe's write end (that's what makes the
  red leg block for 10s). Nothing is curated out; the no-straggler case is a
  separate test asserting silence, not a substitute.

## Commit-readiness

The target repo has no formatter/linter hook config (no pre-commit/ruff/flake8
files; hooks dir is samples-only; DCO is a sign-off requirement handled at
publish). Both touched files `py_compile` clean; every line ≥91 chars flagged by a
width scan is pre-existing (`progress.py:343/:397` untouched; one reindented
comment at `:183` lands at 92, within the file's existing 92–97 range). Style
matches the surrounding file (stdlib-only, unittest, same comment voice).

## For the publisher

Carry the #383 zombie-limitation paragraph into the PR description (brief
requirement). Conflicts-with #370 is moot at this base: both bundles' changes are
present together in the lane worktree and the full suite is green.
