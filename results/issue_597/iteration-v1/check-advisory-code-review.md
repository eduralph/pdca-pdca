# Advisory code review — issue 597 (flow-never-drives-a-briefless-bundle)

Lens: bugs the patch introduces, plus reuse/simplification. I found no correctness bug. The
three intake paths call one shared helper (`_admit` → `_has_plan_artifact`), each one only
after the claim is taken. The helper reuses `split._parent_plan`, `split._split_parent_brief`,
`split.read_lineage` and `flow._lineage_children` rather than copying them, writes the brief
atomically (temp file + `replace`), and releases the claim on every skip. I checked that the
rebuilt parent stays BUILT, the same as the post-#481 control (brief + close marker, no
`check-gates.json` → `state.py:367-368`), so sending it into the drive set matches what the
control does. C4 log: 11 of 14 tests error with the reported `FileNotFoundError` before the
fix. The 3 that pass are the "nothing changes" / held-claim invariance tests, which is
expected. The points below are minor.

- NEEDS-HUMAN [impl] — template/src/pdca_harness/flow.py:1020 — `plan is None` can never be
  true here. `split._parent_plan` returns `None` only when `brief.md` exists
  (`split.py:805-806`), and `_has_plan_artifact` already returned `True` for that case at the
  top of the function. The dead condition shares a branch whose message blames the lineage
  record, so if it ever did fire, it would point the operator at the wrong file. Drop the
  `plan is None or` part.
- NEEDS-HUMAN [impl] — template/src/pdca_harness/flow.py:1017 — the skip message pastes the
  `SplitError` text in as-is. That text says "— refusing to split" and ends "…then re-run: a
  parent with its own brief.md keeps it as it is" (`split.py:807-814`, `:828-833`). In a
  `pdca flow` run nothing is being split, and the line then adds a second remedy (". Then
  `pdca flow N`"). The remedy is correct, but the message is confusing. Consider a short
  flow-side lead-in, or accept it as is.
- NEEDS-HUMAN [impl] — template/tests/test_flow_briefless_split_parent.py:266 —
  `test_the_sweep_repairs_then_drives` checks only `assertIsInstance(rc, int)` for the exit
  code, which every outcome passes. The named-id test compares against a control. The sweep
  test checks the brief bytes and that 654 left BUILT, which covers the fix, but the
  `rc` assertion adds nothing. Remove it or compare it against a control.
- NEEDS-HUMAN [impl] — template/tests/test_flow_briefless_split_parent.py:237 — claim release
  on a skipped bundle is tested only through `flow_ids`. The sweep (`flow.py:2030`) and
  adoption (`flow.py:1397`) paths rely on the same `_admit` release, but no test checks that
  another run can take the bundle after either path skips it. This is a small coverage gap
  against brief (ii)/(iii), not a defect: the code path is shared.
- template/tests/test_flow_briefless_split_parent.py:105 — `flow._drive_wave` is saved and
  restored but never replaced. It is only read through `self._orig[2]`. This is harmless, but
  the restore suggests a patch that does not exist. Cosmetic, no action needed.
