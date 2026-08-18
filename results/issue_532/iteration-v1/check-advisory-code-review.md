# Check advisory — code review (2nd lens: correctness bugs + reuse/simplification)

Reviewed `patch.diff` against the target source under `$PDCA_TARGET`
(`template/src/pdca_harness/leaves.py:673-812, 1820-1994, 2620-2690, 2976-3020,
3280-3321`) and the two test files it touches. Traced every new code path by hand
(attempt-numbering, transient-vs-substantive classification, the artifact
disown/harvest sequencing, the Do exhausted-retry report vs. `state.state`/
`driver.advance`) and cross-checked against the frozen gate evidence
(`gate-logs/C4-verify.log`: red leg genuinely fails — 6 failures + 1 error, all in
the newly-appended assertions, no import error; green leg is clean, 14/14 in both
touched test files; `gate-logs/T3-suite.log`: full 1769-test driver+root suite green).

## Correctness

No bug introduced by this patch. Specifically checked and found sound:

- `_invoke_leaf_resilient` (`leaves.py:673-755`): the per-attempt flush
  (`_write_attempt_records`, `:742`) happens strictly before `time.sleep(delay)`
  (`:754`), so the "on disk before the next attempt" claim holds even for a run
  killed mid-backoff. The success path's `error_log.unlink` (`:732-737`) only ever
  removes a file the *failure* branch wrote, so a first-attempt success still does
  zero I/O on the error log, as documented.
- `_disown_artifact` (`:770-790`) is called once per attempt for every call site
  that passes `artifact=`, and only for those (the builder passes none, so its
  residue is correctly left untouched at `:1984-1992`/`:3979` region). The fail-closed
  branch (unlink when rename fails) prevents a residue that can't be set aside from
  staying harvestable, matching the stated invariant.
- `_report_exhausted_do_retries` (`leaves.py:1869-1898`) is only reached via
  `getattr(exc, "transient", False)` (`:1864`), and `LeafError.transient` is `True`
  only when `produced is False`; a setup failure (`worktree.ensure` → `WorktreeError`,
  no `.transient` attribute) correctly falls through to `False` and is never
  misreported as a transient/exhausted builder death. Its `"patch.diff" in residue`
  branch (`:1888`) matches `state.state`'s own BUILT test (`state.py:207-211`:
  keyed on `patch.diff`/`CLOSE_MARKER`, not `build-notes.md`), so the BUILT-vs-Check
  claim it prints is true of the real state machine (also asserted end-to-end by
  `test_leaf_resilience.py:657-680` against `state.state(d)`).
- `_memory_log_for(BUILD_ERROR_LOG)` (`:362-372`) derives `"build.memory.jsonl"`,
  identical to the `BUILD_MEMORY_LOG` constant the call site used to pass
  explicitly — dropping the explicit `memory_log=` kwarg at `:1984-1992` is a
  no-op behavior change, not a regression.
- All three harvest sites (`_run_review_sandboxed:2674-2687`,
  `_run_advisory_sandboxed:3006-3018`, plan-advisory `:3308-3319`) apply the
  `artifact=`/harvest-after-`err`-check pattern identically; none can adopt a dead
  attempt's file because the early `return` on `err is not None` happens before the
  `out.exists()` check.

## Reuse / simplification

- `_skip_backoff`/`_REAL_SLEEP` (`template/tests/test_build_error_log.py:34-45` and
  `template/tests/test_leaf_resilience.py:472-482`) are byte-for-byte duplicated
  across the two test files rather than factored into one shared test helper. Minor,
  test-only, no behavioral risk — not worth a round on its own, flagging only because
  the patch is what introduced the duplicate (it existed in neither file before).

No other duplication, needless hot-path work, or simpler-equivalent-available found;
the new helpers (`_write_attempt_records`, `_disown_artifact`, `_has_content`) are each
used at more than one call site or guard a genuinely new invariant, not a copy of
existing logic.

## Scope

Both findings are localized to lines this diff touches; nothing pre-existing outside
the diff's regions is cited.
