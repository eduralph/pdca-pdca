# Check — advisory code review (issue #534)

Scope: correctness bugs the patch introduces, plus reuse/simplification/efficiency. Ground
truth is `$PDCA_TARGET` (post-patch tree). Both prior sign-off iteration findings (blank
abandon value, per-bundle error isolation) are fixed correctly and covered by new tests
(`_abandon_reason` in `handoff.py:269-278`, used by both `stop_problems` and
`report_at_reap`; the per-bundle `try/except` at `handoff.py:468-471`). Verified the new
test file passes standalone (`test_handoff_reap.py`, 20 tests) and together with the
updated `test_handoff.py` (55 tests, all green), matching the C4 gate log.

## Findings

- NEEDS-HUMAN [impl] — `template/tests/test_handoff.py:304-313` (`test_session_registers_env_and_cleans_up`)
  and `:320-326` (`test_act_session_carries_the_baseline`) open a `handoff.session(...)`
  whose contract is deliberately left undischarged (no `signoff-decision`, no act-log
  entry) and exit it without `redirect_stderr`. Before this patch `session()`'s `finally`
  only printed on a recorded abandon reason, so these two tests were silent. Now every
  exit runs `report_at_reap` (`handoff.py:295, 343-372`), which prints the full unmet-
  contract report to real stderr whenever the contract isn't discharged — confirmed by
  running the file directly (`-v` shows the "ended with its exit contract not
  discharged..." block printed mid-test for both). Both tests still pass — unittest
  doesn't fail on stray output — so this doesn't affect T3/C4, but it's noise the brief's
  own scope note ("Updating test_handoff.py to match is in scope") should have caught:
  every other test in the file that drives an undischarged session already wraps it in
  `redirect_stderr` (e.g. `:328-333`). A one-line fix: wrap those two `with` blocks in
  `redirect_stderr(io.StringIO())` the same way.

- No other findings. The `_abandon_reason` / `_error_text` helpers in `handoff.py:269-285`
  are new, single-purpose, and not duplicates of anything already in the module or of the
  `f"{type(exc).__name__}: {exc}"` pattern used elsewhere in the codebase (that pattern
  doesn't collapse embedded newlines the way `_error_text` does, which is what the "one
  line" contract in `report_at_reap`/`stop_problems` actually needs). The added
  `_doctor.registered_ids(cfg)` pre-check in `stop_problems` (`handoff.py:458-464`)
  duplicates a config read that `check_planner`'s own dependency checks also do per
  bundle, but that's a deliberate, tested tradeoff (one aggregate failure line instead of
  N per-bundle "could not check" lines for a shared input) — not a hot path, not worth
  changing. Scope carve-outs (`leaves.py:917`, `do_plan`/`do_plan_batch`/
  `run_plan_advisory_batch` left untouched) match the brief's explicit ordering note
  against issue #480 and don't leak into the diff.
