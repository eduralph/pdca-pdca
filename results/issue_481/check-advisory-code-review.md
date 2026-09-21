# Check — advisory code review (issue #481)

Clean on both lenses. No correctness bugs found, and the patch's own reuse work is the kind this lens looks for (it removed rather than added duplication):

- **Reuse (already done right by the patch):** `template/src/pdca_harness/state.py:306-332` adds `iteration_archives`/`replan_archives` as the single reader of the `iteration-v<N>` archive shape, and `template/src/pdca_harness/size_signal.py:61,142-148` and `template/scripts/size-calibrate:9` (the removed `_ITERATION_DIR` at old line 9) both drop their private copies of that regex/glob logic in favor of the shared one. Confirmed no leftover `_ITERATION_DIR` definition outside `state.py` (`grep` across `template/src` and `template/scripts` turns up only the one in `state.py:303,317`). This is exactly the kind of duplicated-logic cleanup this lens flags when missing — here it's present.

- **`state()` reordering (`state.py:335-373`) is correct:** the "past Do" check (`patch.diff` or `CLOSE_MARKER`) now wraps the missing-brief and placeholder-brief checks instead of the old code returning `UNPLANNED`/`RESOLVED` before ever looking at `patch.diff`/`CLOSE_MARKER`. Traced by hand against all six shapes in `test_e_a_briefless_bundle_past_do_is_never_placed_before_plan` (`template/tests/test_split.py:504-535`) and the behavior matches for each. No regression for the brief-exists-and-placeholder-and-past-Do combination (unchanged path).

- **Transaction discipline in `split.accept` (`split.py:904-1011`) checked against both failure-injection tests** (`test_a_torn_brief_write_is_rolled_back_and_the_retry_completes`, `test_a_failure_after_the_brief_landed_takes_it_back_out`, `test_split.py:2029-2066`): the new-brief write sits second-to-last (after build-notes, before the close marker) on the forward path and is unconditionally (not gated on the write's own return value) unlinked on the rollback path, correctly handling the "write landed part of the file, then raised" case (a partial write left behind would otherwise be adopted by a retry as the parent's own brief).

- **`_parent_plan` (`split.py:756-806`) correctly reuses `handoff.check_planner(..., dependencies=False)`** rather than re-implementing the Plan-exit field checks, and the field values it copies (`slug`, `repo + branch target`) are only read after `check_planner` has confirmed they're non-empty and non-placeholder — so `_brief.whole_field`'s raw (unfiltered) return value can't leak a placeholder into the rebuilt brief.

- No circular-import risk from the new `size_signal → state` and `split → state` (pre-existing) imports — `state.py` imports only `brief` and `signoff`.

- Full offline suite (`gate-logs/T3-suite.log`) is green at 1907 tests, and `gate-logs/C4-verify.log` shows a genuine red leg (16 assertion failures with the production hunks reverted, not an import error), so the new test class exercises the fix rather than passing vacuously.

Nothing here needs a human's or the builder's attention beyond what the deterministic gates and the `reviewer` leaf already cover.
