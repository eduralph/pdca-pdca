# PR description

## Summary
**User impact:** After a command run by the harness finishes, work it started in
the background can silently live on. One leaked test process burned ~100% of a CPU
core for 21 hours after its run had ended — and a survivor that still holds ports,
locks or test fixtures when the *next* run starts causes one-off, never-reproducible
failures that nobody can trace back to their source.

This PR makes the harness clean up everything a finished command left running — on
every exit path, not just timeouts — printing a single warning line naming what it
swept.

Reported in [#372](https://github.com/eduralph/pdca-harness/issues/372).

## What to look at
`run_with_heartbeat` in `template/src/pdca_harness/progress.py`: which children get
their own process group (the `sessionize` condition), the new post-exit sweep
(`_sweep_stragglers`), and the ordering — the sweep must run *before* the captured
output streams are closed. To see the old behaviour, run a captured `shell=True`
command such as `sleep 300 & echo done` and watch the `sleep` outlive the call; the
new tests in `template/tests/test_progress.py` (class `StragglerSweep`) automate
exactly that.

## Root cause
`run_with_heartbeat` waits on the direct child and returns; under `shell=True`
(every gate) the direct child is only a shell, so anything it backgrounded survives
the call. 228e80b750a1f5595b4d45580baa751d5152ac52 (#368) sessionizes a child only
when a timeout is set (`progress.py:113` on `main`) and kills the group only when
that timeout expires (`progress.py:169`) — a normal exit, the overwhelmingly common
path, was never swept, and unbounded captured children were never sessionized at
all.

## Fix
- **Sessionization breadth:** on POSIX, `start_new_session` is now
  `capture or stream_json or timeout is not None` — every child whose stdio the
  harness owns, or whose wall clock is bounded, leads its own process group.
  Interactive calls (no capture, no stream, no bound) stay unsessionized and keep
  the terminal's foreground group exactly as today.
- **Normal-exit sweep:** after `proc.wait()` returns, a new `_sweep_stragglers`
  probes the group and, only if a live member survives, prints one stderr note
  naming the command, then SIGTERM → 2 s polled grace → SIGKILL via `os.killpg`.
  No survivors ⇒ no signal, no note — the clean common case is byte-identical.
- **Kill-then-close order:** the sweep runs before the reader join and stream
  close, mirroring the timeout path. A straggler that inherited the capture pipe
  keeps the drain thread blocked mid-read, and closing the stream then waits on
  that blocked reader; killed first, the last writer dies, the drain sees EOF, and
  neither the join nor the close can block.
- **Widened abort sweep:** on Ctrl-C/abort mid-wait the group is killed whenever
  the child was sessionized, not only when it was bounded, then the interrupt is
  re-raised.
- **Zombie-aware probe:** the group-liveness check reads `/proc/<pid>/stat` on
  Linux (state `Z` counts as gone) rather than `killpg(pgid, 0)`, which reads an
  unreaped zombie as alive — under a non-reaping PID 1 (e.g. a container) that
  would produce a phantom sweep note on every clean exit.
- **Non-POSIX:** sessionization and every sweep site are skipped; behaviour is
  pre-existing.

**Known limitation (deferred to #383):** a swept grandchild is not this process's
child, so it cannot be reaped here — under a non-reaping init the group kill leaves
a zombie table entry. No global reaper thread is added in this change: a naive
`waitpid(-1)` reaper can steal exit statuses from concurrent `Popen.wait()` calls
and corrupt a gate verdict, which is strictly worse than the zombie. The subreaper
design is scoped separately in #383.

## Verification
- **Claim:** on current `main`, a backgrounded child survives a captured command's
  normal exit. **Checked:** `template/src/pdca_harness/progress.py:113` and `:169`
  on `main` — sessionization only when `timeout` is set, group kill only on expiry;
  the normal `proc.wait()` return (`:173`) flows straight to the join/close with no
  sweep.
- **Claim:** the sweep must precede the stream close or a straggler holding the
  capture pipe blocks the return. **Checked:**
  `template/src/pdca_harness/progress.py:191` on `main` — the 5 s reader join
  (then close) that a straggler-held pipe blocks; the sweep is inserted before it.
- **Test:** `template/tests/test_progress.py` (`StragglerSweep`, 5 tests) — fails
  pre-fix, passes post-fix. With the production change reverted, 3 deterministic
  failures: the straggler survives the normal exit; the call blocks ~10 s on the
  straggler-held pipe (asserted < 4 s); `capture=True` does not sessionize. With
  the fix applied, `Ran 31 tests … OK`, and the no-survivor case asserts stderr is
  byte-identical (empty), the interactive-shaped case asserts no sessionization.

Fixes #372
