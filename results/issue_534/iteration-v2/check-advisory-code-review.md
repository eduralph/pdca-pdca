# Check — advisory code review (issue #534)

Reviewed `patch.diff` against target source at `$PDCA_TARGET`, focused on correctness
bugs the patch introduces and reuse/simplification opportunities.

## Correctness

- No bugs found. Both carry-forward findings from iteration 1 are actually fixed:
  - `handoff.py:269-278` (`_abandon_reason`) is now the single "was this abandoned"
    test, used by both `stop_problems` (`handoff.py:431`) and `report_at_reap`
    (`handoff.py:351`), so a whitespace-only `abandoned` value can no longer clear the
    problem list while also printing no reason. `test_a_blank_abandon_value_does_not_hide_the_report`
    (`template/tests/test_handoff_reap.py:301-323`) exercises exactly that case for
    `""`, `" "`, `"\n"`, `" \t\n"`.
  - `check_planner`'s docstring (`handoff.py:103-106`) no longer mentions the Stop
    boundary; it now describes the session-end check.
- `session()`'s merge at reap (`handoff.py:331`,
  `report_at_reap(cfg, role, {**_read_json(path), **registered})`) correctly protects
  `role`/`bundles`/`require_artifact`/`baseline` from being clobbered by a rewritten or
  lost scratch file, while still picking up `passed`/`abandoned` from the file — checked
  this against `test_the_report_names_the_bundles_the_driver_registered`
  (`test_handoff_reap.py:271-280`) and it holds.
- `report_at_reap` (`handoff.py:336-364`) only wraps the `_abandon_reason` /
  `stop_problems` call in `try/except`; the two `print(...)` calls after it are
  unguarded. That's fine in practice (they're plain string formatting to `sys.stderr`),
  but it means the docstring's "never raises" claim is not literally enforced end to
  end — a future edit that adds anything fallible to those print branches would not be
  caught by the existing exception net. Not a bug today, just a latent gap; not
  something this patch needs to fix.
- Verified the two intentionally-untouched "Stop hook" comments
  (`leaves.py:917`, `leaves.py:1107`) are both inside `do_plan` / `do_plan_batch`,
  exactly the functions the brief's Ordering note carves out for issue #480. No stray
  edits leaked into those functions or into `run_plan_advisory_batch`.
- `settings.json` diff is a clean removal of the `hooks.Stop` block; valid JSON, no
  other permission entries touched.
- `handoff_guard.py`'s new "unknown mode" branch (`handoff_guard.py:72-75`, returns 2
  for any argv it doesn't recognize) is a behavior change from the old fallthrough to
  `_stop_verdict()`, but it's consistent with the brief's scope (only `--check`,
  `--abandon`, and no-args are meaningful now) and is exercised by the no-args tests in
  `test_handoff_reap.py`.

## Reuse / simplification

- `_abandon_reason` (`handoff.py:269-278`) is exactly the kind of single-source helper
  that should have existed before iteration 1's fix; good factoring, no duplicate logic
  left behind.
- `report_at_reap` reasonably reuses `stop_problems` rather than re-implementing the
  per-role dispatch; no duplicated contract logic introduced.

## Gate evidence cross-check

- C4 log (`gate-logs/C4-verify.log`) shows the red leg failing for the right reasons
  pre-fix (Stop hook still registered, `_stop_verdict` returns 2 on an undischarged
  contract) and green post-fix, matching the brief's stated falsifiability trap.
- No other gate log surfaced anything relevant to this lens.

Nothing else stood out. The diff is clean on both lenses.
