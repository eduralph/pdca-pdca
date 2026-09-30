# Adversarial review — #537 (the builder retries like every other leaf)

I could not break the mechanism. The red→green proof holds and runs the real code path.
What sign-off has to weigh is what the fix does **not** cover.

## Findings

- NEEDS-HUMAN — **The incident behind this issue is still not retried.**
  `template/src/pdca_harness/progress.py:478` describes it: an escalated builder ran ~18
  minutes, then the API connection dropped mid-response and the CLI exited 1. Any
  `assistant`/`user`/`result` event sets `produced` (`progress.py:432`), so
  `LeafError.transient` is False (`leaves.py:106-109`) and the wrapper stops after attempt 1
  (`leaves.py:733` and the `break` below it). I ran that exact shape (an init event, a
  tool-use `assistant` event, an `is_api_error_message` event, exit 1) through the patched
  `leaves.do_build`: **1 invocation, no backoff, `LeafError transient=False`.** So the
  reported incident still costs a full cycle round. The brief scoped this out on purpose
  (#533/#510 own the classification), but the call-site comment at `leaves.py:2143-2144`
  ("no builder failure was ever retried — on the leaf where an attempt costs the most")
  reads as if the expensive case is now covered. It is not: only deaths **before the first
  work event** are absorbed, which are the cheap ones. The same cause makes criterion (ii)
  change nothing today. A retry only follows a death that did no tool work, so the retried
  builder sees exactly the bundle and worktree attempt 1 saw, plus `build.error.log`. The
  case the `_retry_notice` docstring gives as its reason (`leaves.py:2256-2258`: a retry
  reading "a partial patch.diff … as a finished build") can't happen under the current
  transient rule. Any build-notes.md or test file present at retry time was also there,
  unflagged, for attempt 1. The notice only starts to matter once #533/#510 widen what
  counts as transient. Sign-off should accept both points knowingly rather than read this
  patch as fixing the #506 incident.

- Test can't tell "attempts spent" from "the budget" (`template/tests/test_builder_retry.py:242`).
  I replaced `{spent}` with a literal `{3}` at `leaves.py:2191` and all 11 tests still
  pass. This isn't a defect: the wrapper only ends on a transient error when
  `attempt == attempts`, so the two numbers are always equal today. Criterion (iii)'s
  "N is the attempts actually spent" holds by construction, not because the test proves it.

- The retry prompt with a rubric configured is untested. `test_builder_retry.py:202` asserts
  `retry.startswith(first)`, which only holds with **no** rubric: with a rubric, `first` is
  task + rubric and the retry is task + notice + rubric. The production code is right
  (`leaves.py:2250` puts the notice before the rubric, and the rubric comes from the
  snapshot attempt 1 already wrote, so it's the same text). This is a coverage gap only.

- In-place mode leaves residue the report doesn't mention. `_do_residue` only lists bundle
  files (`leaves.py:2056-2061`). With `worktree = false`, or when `worktree.ensure` falls back
  to in-place, a substantive death that edited source leaves a dirty tree. The report still
  says "no patch.diff … was left in the bundle" and "a plain re-run starts Do again"
  (`leaves.py:2088-2092`), and the next builder builds on that tree without being told. With
  a real worktree this is fine, because the next Do resets it (`worktree.py:377-384`). Minor,
  but the retry notice already names in-place edits (`leaves.py:2269-2271`), so the report
  could name them too.

- The wrapper's retry progress line prints `workdir.name` (`leaves.py:755-757`). For the
  builder, that is the harness root or the lane worktree directory, not the bundle. In a
  run with several targets, the operator can't tell which Do is retrying. The brief says
  #533 owns the strings in that function, so this is not for this slice.

## Attempted and could not refute

- **Red→green.** I re-ran it in a sandbox copy. Red (production hunks of `leaves.py`
  reverted): 9 of the 11 new tests fail on assertions, none on imports. The 2 that pass are
  the no-regression guards (a substantive failure is not retried; a successful spawn keeps
  today's arguments). Green: 28 tests across `test_builder_retry`, `test_build_error_log` and
  `test_leaf_resilience` pass in 1.2 s. This matches `gate-logs/C4-verify.log`.
- **Production path, not a copy.** The tests drive the real `leaves.do_build` →
  `_invoke_leaf_resilient` → `_invoke` → a subprocess stub. Only pre-existing API is
  imported at module level.
- **(iv) overwrite guard** (`leaves.py:2042`). Without the retry-built log, the outer capture
  would write one record, and `test_both_attempts_are_still_in_the_log` checks for
  "first-death", so it would fail.
- **Unwritable settled record** (`leaves.py:766`, `2176-2183`). I changed `except OSError` to
  `except KeyError` and `test_build_error_log.py:163` errors, so the branch is covered (its
  `Path.write_text` mock reaches `_replace_record`'s temp-file write).
- **Attempt 1's prompt is byte-identical.** `leaves.py:2250` appends `""` when
  `dead_attempts == 0`, and `first` is built with the same `worktree_root=wt` as before.
- **#420 memory log.** `_memory_log_for` (`leaves.py:364-374`) derives `build.memory.jsonl`,
  the same file the old explicit argument named.
- **Wall-clock trap.** `test_build_error_log` runs in 0.23 s. No real backoff is slept, and
  the shipped defaults are untouched.
- **A stale log misread as this Do's record.** This can't happen. `do_build`'s unlink runs
  before the `try`, so a failing unlink raises before the new `error_log.exists()` guard.
- `_stub_build`, `select_builder` and the stale-log clear are untouched by the diff. T3 is
  green (`gate-logs/T3-suite.log`).
