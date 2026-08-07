# Result — issue 372 / straggler-sweep-on-normal-exit

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: `run_with_heartbeat` (`progress.py:25`) waits on the direct child and
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
- Success criterion: on POSIX: (a) every child whose stdio the harness owns is
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
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: the unswept-normal-exit defect, as in the criterion — sessionization
  breadth, the post-wait group sweep with the kill-then-close ordering, the widened
  abort condition, the POSIX gate. / out of scope: the subreaper design (the
  maintainer's second comment: on minimal-container inits the group kill leaves a
  zombie table entry; a naive `waitpid(-1)` reaper can steal exit statuses from
  concurrent lane `Popen.wait()`s and corrupt a gate verdict — strictly worse than a
  zombie; it needs its own scoped design and was deliberately deferred from the
  instance staging — now filed as its own issue, #383, milestone 0.60.0). Do MUST
  record the zombie limitation in build-notes/PR prose citing #383, and MUST NOT add
  a global reaper thread in this change.

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: pass — C4 PASS: red without the fix, green with it
- C5 Causal adequacy: none — reviewer + human sign-off

## 4. Conformance (Check — stack)
- T1 Structure: none — (no gate configured)
- T2 shape: docs lint + site render link audit: pass — render_site: link audit OK
- T3 runtime: render/update-compat + offline driver suites: fail — /tmp/tmpe0zhgc0z/results/issue_500/split-proposal.md
- T4 PR body has a user-impact opener + tracker id in both artifacts: pass — pdca-pdca contribcheck
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Task: fix POSIX `run_with_heartbeat` so harness-owned children are sessionized and normal-exit stragglers are swept before capture streams close.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The owed behavior is explicit: captured/streamed/bounded POSIX children must not leave live group members behind, while interactive-shaped calls stay unsessionized and non-POSIX skips the new path. |
| C2 Reproduction (red pre-fix) | PASS | Pre-fix source plus patched tests fails as expected: straggler survival and drain-hang assertions trip for the normal-exit cases covered at `template/tests/test_progress.py:299` and `template/tests/test_progress.py:314`. |
| C3 Change | PASS | The change addresses the lifecycle handle and cleanup point: sessionization is widened at `template/src/pdca_harness/progress.py:126`, normal-exit sweep runs before reader joins at `template/src/pdca_harness/progress.py:216`, and zombie-aware group liveness is defined at `template/src/pdca_harness/progress.py:293`. |
| C4 Verification (red→green) | NEEDS-HUMAN | Decide whether the manual red→green evidence substitutes for the configured C4 gate: `python3 -m unittest tests.test_progress.StragglerSweep` fails 3/5 with pre-fix `progress.py` and passes 5/5 patched, but the target `run-verify.sh` is a skeleton at `template/engine/scripts/run-verify.sh:50` and git stash could not run because this worktree's git index is read-only. |
| C5 Causal adequacy | PASS | The fix removes the normal-exit lifetime gap rather than adding a symptom-only guard: the owned process group is created before launch and swept on normal return, timeout, and abort paths at `template/src/pdca_harness/progress.py:126` and `template/src/pdca_harness/progress.py:208`. |
| T1 Structure | PASS | The implementation stays in the shared subprocess lifecycle helper and its existing unit-test file, matching the defect surface rather than adding gate-specific cleanup. |
| T2 Shape | NEEDS-HUMAN | Decide whether to rely on the recorded docs-check result: `check-gates.json` reports T2 pass, but no `run-docs-check.sh` exists in this target checkout to rerun the link audit here. |
| T3 Runtime | NEEDS-HUMAN | Decide whether the recorded suite failure is unrelated or actionable: `check-gates.json` reports T3 fail at an unavailable `/tmp/.../issue_500/split-proposal.md`, while local `make check PYTHON=python3` passes and `make test` fails only because this template checkout has no rendered `pdca.toml`. |
| T4 Contribution | NEEDS-HUMAN | Decide whether contribution metadata was checked elsewhere: `pdca-pdca contribcheck 372` cannot run in the review dir or target template because both lack a rendered `pdca.toml`. |
| T5 Judgment | PASS | Affected-file prior-art history does not show a merged or in-flight `#372`/straggler/sweep fix for `template/src/pdca_harness/progress.py`; remaining sign-off questions are captured in the NEEDS-HUMAN rows. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Human sign-off must decide fitness to purpose for real lane isolation, especially whether the zombie limitation intentionally deferred to #383 is acceptable for production use. |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] C4 Verification (red→green) — Decide whether the manual red→green evidence substitutes for the configured C4 gate: `python3 -m unittest tests.test_progress.StragglerSweep` fails 3/5 with pre-fix `progress.py` and passes 5/5 patched, but the target `run-verify.sh` is a skeleton at `template/engine/scripts/run-verify.sh:50` and git stash could not run because this worktree's git index is read-only.
- [x] T2 Shape — Decide whether to rely on the recorded docs-check result: `check-gates.json` reports T2 pass, but no `run-docs-check.sh` exists in this target checkout to rerun the link audit here.
- [x] T3 Runtime — Decide whether the recorded suite failure is unrelated or actionable: `check-gates.json` reports T3 fail at an unavailable `/tmp/.../issue_500/split-proposal.md`, while local `make check PYTHON=python3` passes and `make test` fails only because this template checkout has no rendered `pdca.toml`.
- [x] T4 Contribution — Decide whether contribution metadata was checked elsewhere: `pdca-pdca contribcheck 372` cannot run in the review dir or target template because both lack a rendered `pdca.toml`.
- [x] T5 Judgment
- [x] Validation — fitness-to-purpose — Human sign-off must decide fitness to purpose for real lane isolation, especially whether the zombie limitation intentionally deferred to #383 is acceptable for production use.

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: merged-wider
- Iteration delta (if iterating):
- By / date: Eduard Ralph / 2026-08-01

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
