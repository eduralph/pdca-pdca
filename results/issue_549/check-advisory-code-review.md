# Check — advisory code review (issue #549)

Lens: bugs the patch introduces, plus reuse/simplification/efficiency. Grounded on
`$PDCA_TARGET/template/src/pdca_harness/handoff.py` and
`$PDCA_TARGET/template/tests/test_handoff_reap.py`.

## Correctness

No bug found in the new code paths. Specifically checked and found sound:

- `template/src/pdca_harness/handoff.py:315-331` (`_changed_briefs`) only ever returns a
  bundle whose `brief.md` exists right now (`_brief_fingerprints` skips a path where
  `bp.exists()` is false), so the `allow_absent=True` kwarg that
  `stop_problems` (`handoff.py:674-683`) now applies uniformly to both the registered and
  the unregistered bundle lists can never actually fire on an unregistered entry — the
  "missing brief" branch of `check_planner` (`handoff.py:126-129`) is unreachable for
  anything `_changed_briefs` returns. Harmless in practice, and matches the brief's own
  "brief deleted during the session" out-of-scope note (`brief.md:89`).
  `test_a_broken_doctor_table_is_one_item_and_the_briefs_are_still_checked` and the
  `allow_absent` propagation are exercised together correctly.
- Session-start snapshot vs. reap-time re-fingerprint is symmetric: a brief that predates
  the session and errors the same way both times (`"unreadable (...)"` unchanged) is
  correctly excluded from `_changed_briefs`, matching the documented "fails to read the
  same way it did at spawn" rule (`handoff.py:320-324`) and covered by
  `test_a_session_that_changed_no_brief_is_judged_as_before`.
  A brief that goes from readable-at-spawn to unreadable-at-reap (or vice versa) does show
  up as changed and is correctly routed through the bundle-level
  `try/except` in `stop_problems` (`handoff.py:684-690`), landing as its own
  `could not check (...)` item — covered by
  `test_a_brief_that_cannot_be_read_is_its_own_item_and_hides_no_other`.
- `state = {**_read_json(path), **registered}` (`handoff.py:521`) already guaranteed the
  driver-captured `baseline` wins over anything the leaf process could rewrite into the
  scratch file; `_changed_briefs` reads `state["baseline"]`, so it inherits that
  protection for free. `test_a_session_cannot_blank_its_own_spawn_snapshot` actually
  exercises this (writes `{"baseline": {}}` into the scratch file mid-session and checks
  the reap still uses the real snapshot) — a genuine regression guard, not a decorative
  test.
- The `_brief_fingerprints`/`leaves._brief_snapshot` duplication is deliberate, not
  redundant: `leaves.py:59` imports `handoff` at module scope, so `handoff.py` importing
  `leaves` would be circular. The two intentionally differ (placeholders are fingerprinted
  here but excluded in `_brief_snapshot`), and that difference is spelled out in
  `session()`'s docstring (`handoff.py:461-464`) — reviewed and correct.

## Efficiency

- `_brief_fingerprints` (`handoff.py:293-312`) reads every `issue_*/brief.md` under
  `cfg.bundle_root` in full, twice per CSV/default batch Plan session (once at spawn,
  once at reap). That's O(bundle count) file reads on a path that already spawns an
  interactive agent session, so it's not a hot loop — not worth flagging as a performance
  problem, just noting it scales with bundle-root size the id-seeded/single-Plan paths
  don't pay.

## Reuse / simplification

Nothing to flag — the new helpers are small, single-purpose, and the one place that looks
like duplicated logic (vs. `leaves._brief_snapshot`/`_fresh_plan_briefs`) is justified by
a real circular-import constraint and is documented as intentionally non-identical.

## Overall

Diff is clean on both lenses. No NEEDS-HUMAN items.
