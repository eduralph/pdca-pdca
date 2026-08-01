# Brief — issue 372 / straggler-sweep-on-normal-exit

> The Plan artifact (docs 02 §PLAN). Do reads ONLY this file.

- **Slug:** straggler-sweep-on-normal-exit
- **Defect:** `run_with_heartbeat` (`progress.py:25`) waits on the direct child and
  returns; nothing ever looks at what that child *spawned*. Under `shell=True` (every
  gate) the direct child is only a shell, so surviving work is the rule, not the edge
  case. Measured: a single leaked test process from a *prior cycle's* patched tree
  burned ~100% of a core for 21 hours, reparented to the user manager, its test
  function existing in no current tree. Worse than the CPU: cross-cycle interference —
  a straggler still holds ports, file locks and fixtures when the next cycle's gates
  run in the same lane worktree, the class of one-off never-reproducible gate red
  measured in wyrd `issue_648`. The #368 work (prior wave) sweeps the group only on
  the timeout/interrupt paths and only sessionizes a *bounded* child; a normal exit —
  the overwhelmingly common case — leaves the group unswept, and unbounded children
  are not sessionized at all.
- **Success criterion:** on POSIX: (a) every child whose stdio the harness owns is
  sessionized — `start_new_session = capture or stream_json or timeout is not None` —
  while the interactive leaves (no capture, no stream, no bound) keep the terminal
  exactly as today; (b) after a normal `proc.wait()` returns, surviving group members
  are swept: SIGTERM → short grace → SIGKILL, with one stderr note naming the swept
  command (the straggler is a signal, not just a mess); (c) the sweep runs **before**
  the capture streams close, mirroring the timeout path's kill-then-close order (the
  measured deadlock: a straggler inheriting the capture pipe keeps the drain thread
  blocked, and closing a file mid-read waits on the reader — two ~5-minute hangs
  before the reorder); (d) the existing Ctrl-C/abort sweep condition widens from
  "bounded" to "sessionized"; (e) on non-POSIX (`os.name != "posix"`), sessionization
  and sweep are skipped and behaviour is pre-existing; (f) a child that exits leaving
  no survivors ⇒ no sweep, no note — byte-identical. Demonstrable by C4-verify: unit
  tests spawn a captured `shell=True` command that backgrounds a `sleep`-child and
  assert the child is gone (and the note printed) promptly after return — the liveness
  assertion must be ZOMBIE-AWARE (read the process state from `/proc/<pid>/stat`, or
  treat state `Z` as gone; never bare `kill(pid, 0)`, which reads an unreaped zombie as
  alive under a non-reaping PID 1, e.g. a container where the test runner is init); a
  no-straggler case asserts silence; an interactive-shaped call asserts no
  sessionization.
- **Falsifiability:** the offline driver suite on this host (POSIX). RED now: on
  current `main` (with 368's accepted result folded in), the backgrounded child
  survives the captured parent's normal exit — the "child is gone" assertion fails
  deterministically within the test's own bounded wait.
- **Invariant to restore:** no work outlives its cycle: when a harness-owned child
  exits — by any path: normal, timeout, interrupt — no process it spawned survives
  into the next beat or cycle; process lifetime is bounded by the invocation that paid
  for it. Quantified over every captured/streamed/bounded child, not just gates — a
  fix that swept only the gate path would fail this (leaves leak identically). Source:
  internal rule — per-cycle isolation is the harness's own worktree doctrine (docs 03 /
  lane isolation), Tier C per docs/principles.md §5; structural/lifecycle defect, so
  this invariant outranks diff-minimalism (principles §1.2).
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Depends on:** 368
- **Conflicts with:** 370
- **Ordering note:** depends on 368 — `_kill_tree` from that change resolves the group
  id and escalates correctly; the normal-exit sweep shares it, and the "widen the
  abort-sweep condition" clause edits code 368 introduces. Conflicts with 370 (both
  touch `progress.py`'s capture handling) — different waves.
- **Surfaces:** data
- **Difficulty:** high
- **Scope:** the unswept-normal-exit defect, as in the criterion — sessionization
  breadth, the post-wait group sweep with the kill-then-close ordering, the widened
  abort condition, the POSIX gate. / out of scope: the subreaper design (the
  maintainer's second comment: on minimal-container inits the group kill leaves a
  zombie table entry; a naive `waitpid(-1)` reaper can steal exit statuses from
  concurrent lane `Popen.wait()`s and corrupt a gate verdict — strictly worse than a
  zombie; it needs its own scoped design and was deliberately deferred from the
  instance staging — now filed as its own issue, #383, milestone 0.60.0). Do MUST
  record the zombie limitation in build-notes/PR prose citing #383, and MUST NOT add
  a global reaper thread in this change.
- **Repro instruction:** on the target checkout, `grep -rn
  "start_new_session\|killpg" template/src/pdca_harness/progress.py` — empty on the
  pre-368 base; with 368 folded, the sweep exists only on the timeout/interrupt path.
  Run a captured `run_with_heartbeat("sleep 300 & echo done", shell=True, capture=True)`
  and observe the `sleep` survive the call. The named test automates this → red
  pre-fix, green post-fix.
- **External dependencies:** none (the shipped test must run on POSIX — CI is
  ubuntu-latest — and skip itself on non-POSIX)
- **Test file:** template/tests/test_progress.py
- **Citations expected:** Do must cite path:line on the target branch (with 368's
  result folded) for every change. Peer callsites: the wait loop — `progress.py:133`;
  the capture-drain join — `progress.py:151` (`reader.join(timeout=5)`) — the sweep
  must precede the close that this join guards; 368's `_kill_tree` and its
  sessionization condition as the mechanism to widen rather than duplicate.
- **Prior-art check (triage cycles):** `git -C ../pdca-harness log --oneline origin/main
  -- template/src/pdca_harness/progress.py` — no sessionization/sweep commits; commit
  grep `#372` empty; the staging exists only in the wyrd instance. Not fixed, not in
  flight upstream.
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.
