# Advisory code review — issue #481

Scope: correctness bugs the patch introduces, and reuse/simplification opportunities.
Not re-litigating fix adequacy (that's the `reviewer` leaf's job).

## Findings

- NEEDS-HUMAN [impl] — `_ITERATION_DIR` (the `^iteration-v(\d+)$` regex) and the "find the
  highest-numbered `iteration-v<N>` that holds a `brief.md`" computation are now defined
  **twice**: `template/src/pdca_harness/split.py:756-774` (`_archived_brief`) duplicates
  `template/src/pdca_harness/size_signal.py:69-70,148-153` (`iteration_rounds`'s `boundary =
  max(replans, ...)` logic) almost line for line. The new code's own comment
  (`split.py:756-757`, "The same pattern `size_signal.iteration_rounds` reads its re-plan
  boundary with") shows the author noticed the overlap and duplicated anyway rather than
  factoring out a shared helper (e.g. `latest_replan_archive(d) -> Path | None` in `state.py`
  or `driver.py`, next to `_archive_iteration`). Two private copies of the same regex + max
  logic can drift silently if one is edited without the other — worth a follow-up extraction,
  not a blocker.

- NEEDS-HUMAN [impl] — `handoff.py:113-116`'s docstring for `check_planner`'s `dependencies`
  parameter says "Only the reap passes it" (`dependencies=False`). The patch adds a second
  caller — `split.py:810` (`_parent_plan`) — that also passes `dependencies=False`, for an
  unrelated reason (skipping the archived-brief's doctor-registered dependency check, since
  the rebuilt parent brief declares `External dependencies: none` itself and doesn't carry
  the archive's declarations forward). `handoff.py` isn't touched by this diff, so that
  comment is now stale/inaccurate about which code paths rely on the flag — a future reader
  chasing "who passes dependencies=False and why" will be misled. One-line docstring fix.

## Everything else checked and clean

- `_archived_brief`'s "latest re-plan" tie-break correctly parses the numeric suffix
  (`int(m.group(1))`) rather than sorting directory names as text, so `iteration-v10` beats
  `iteration-v2` as intended (`split.py:769-774`, exercised by
  `test_the_source_is_the_latest_re_plan_not_the_first_archive`).
- The rollback path added to `accept()` (`split.py:1010-1025`) removes a torn/partial
  `brief.md` write unconditionally (not gated on which write raised), which is the right
  call for the "write lands part of the file, then the disk fills" case — verified against
  `test_a_torn_brief_write_is_rolled_back_and_the_retry_completes`. The pre-existing gap
  where a failed `build-notes.md` write is never itself rolled back is unchanged by this
  patch (not introduced here) — out of scope.
- `_parent_plan` is invoked twice per accepted split (once from `preflight`, once from
  `accept`) rather than threading a single computed value through — a few extra small-file
  reads on an infrequent, human-gated path. Not worth flagging as a performance problem; it's
  the same "ask again right before the irreversible step" pattern the rest of `preflight`/
  `accept` already uses for the proposal and marker checks.
- Traced the resulting state machine through to sign-off: the freshly-written `brief.md`'s
  `Disposition hint: split` is irrelevant to routing once `state.CLOSE_MARKER` exists —
  `driver._close_class` (`driver.py:236-242`) reads the marker content directly and wins
  outright before ever consulting the brief, so `split` correctly staying out of
  `DEFAULT_CLOSE_DISPOSITIONS` (`config.py:32-36`) does not strand the parent. No new
  builder/reviewer invocation risk on a patch-less split parent.
- `state.py`'s reordering (check patch.diff/CLOSE_MARKER before brief.md) is scoped
  correctly: the placeholder-brief branch (`state.py:318-328`, issue #113) is still reached
  only pre-Do, so an in-flight PLANNED bundle with a placeholder brief keeps its existing
  UNPLANNED-on-placeholder behavior; only the past-Do branch changed.

No implementation defects beyond the two duplication/doc-drift items above; both are minor
and independently fixable without touching the fix's substance.
