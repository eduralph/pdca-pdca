# Advisory code review — issue #475 (no-new-session-notice-waits-for-the-guard)

## Correctness

- No bug introduced. `flow.py:256-259` (`if outcome == action:`) is the minimal, correct
  gate: `_apply_decision` returns the action string only on genuine success (`flow.py:211`),
  and every withdrawal path returns a distinct sentinel (`None`, `flow.REASSEMBLE`,
  `"blocked"`) that can never equal a member of `leaves.VALID_DECISIONS`
  (`leaves.py:84`), so `outcome == action` cannot false-positive. This directly fixes the
  prior iteration's rejected `outcome != "blocked"` gate, which admitted the drop
  (`flow.py:161-165`) and repair (`flow.py:114-130`, `_repair_unsignable`) outcomes.

- `_apply_recorded_decision`'s two callers on the drop/repair paths were already reading
  `outcome` correctly before this patch (`_signoff_and_apply` at `flow.py:270`, and the
  batch sweep) — the patch only changes when the notice is printed, not the return value —
  so no downstream caller needed to change, matching the brief's stated scope.

## Test coverage

- The two new regression cases (`NotRecorded.test_a_dropped_decision_is_not_announced_as_applied`,
  `test_a_repaired_unsignable_summary_is_not_announced_as_applied`,
  `template/tests/test_signoff_orphan.py:328-384`) are exactly the gap the carried-forward
  sign-off rejection asked for, and they exercise the real production path
  (`flow._signoff_and_apply`, not a re-implementation of the guard logic). `gate-logs/C4-verify.log`
  confirms all four new/changed assertions (the two C6 cases plus the two new `NotRecorded`
  cases) genuinely red pre-fix and green post-fix.

## Reuse / simplification

- The generalized `_Base._announced(d, needle)` (`test_signoff_orphan.py:122-128`, was
  `_announced(d, action)`) is reused as-is by every new assertion rather than re-deriving the
  stderr-scan inline — exactly what the carry-forward's "keep as-is" note asked for. No
  duplicated logic introduced.

No other findings. The diff is a tightly scoped, single-condition fix plus proportionate
test coverage; nothing here needs human adjudication.
