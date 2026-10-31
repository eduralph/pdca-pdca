- **Slug:** standalone-signoff-consumes-decision
- **Kind:** bug
- **Defect / goal:** `pdca signoff <id> --accept|--iterate-do|--iterate-plan|--discontinue`
  (`cli._signoff`, `template/src/pdca_harness/cli.py:1504`) records the decision in §9
  (:1530) and drives the transition (:1540), but never deletes the bundle's
  `signoff-decision` file (`leaves.SIGNOFF_DECISION`). The flow's own apply,
  `flow._apply_decision`, deletes it once it records (`template/src/pdca_harness/flow.py:205`).
  So a decision left by an earlier flow session survives a standalone sign-off. The common
  case: a flow accept refused by C6 (flow.py:177-179) leaves `accept` on disk. The human
  runs `pdca signoff <id> --iterate-plan`, the bundle is archived, re-planned and rebuilt,
  and the next `pdca flow` run's pre-apply (`_drive_wave`, flow.py:2516-2522) reads the old
  `accept` and accepts the rebuilt bundle with no sign-off session. Goal: once
  `cli._signoff` has recorded a decision, the `signoff-decision` file is gone, as it is
  after `flow._apply_decision`.
- **Success criterion:**
  - (a) A bundle at AWAITING_SIGNOFF with `signoff-decision` = `accept` on disk. Run
    `cli._signoff` with `--iterate-plan` (leaves in stub mode). After it returns,
    `signoff-decision` does not exist in the bundle directory.
  - (b) End to end: after (a), bring the bundle back to AWAITING_SIGNOFF (stub Plan/Do/Check,
    or write a fresh SUMMARY) and CLEAR its §6 on the rebuilt SUMMARY (as
    `template/tests/test_signoff_orphan.py:171` does with `_clear_needs_human(d)`), so C6
    would permit a stale `accept`. Assert that precondition in the test
    (`signoff.open_needs_human(d / "SUMMARY.md") == []`) before driving. Then drive
    `flow._drive_wave(..., max_passes=1)` with `cfg.auto_iterate` off (the
    `_stub_config(..., auto_iterate=False)` pattern, `test_signoff_orphan.py:59`) and a
    stubbed `leaves.run_signoff_batch` that records the bundles it is offered and writes
    nothing. The bundle is still AWAITING_SIGNOFF, it is NOT COMPLETE, and
    `run_signoff_batch` was offered it (a fresh session). Red on `main`: the pre-apply
    (flow.py:2516-2522) applies the stale `accept` and the bundle reaches COMPLETE with no
    session. (With §6 left open the leg would pass on `main` too, via C6 — so §6 must be
    clear.)
  - (c) A standalone `--accept` refused by C6 (`cli.py:1515-1520`, returns before
    `signoff.record`) leaves `signoff-decision` untouched — nothing was recorded, so
    nothing is consumed. A `signoff.record` that raises `ValueError` (`cli.py:1532-1537`)
    also leaves it untouched.
  - (d) Each recording action (`accept`, `iterate-do`, `iterate-plan`, `discontinue`)
    removes the file. Parametrize.
  - (e) Ordering: with `driver.run_issue` patched to raise (and, separately, to return a
    held state so `_signoff` returns 1, `cli.py:1542-1549`), the `signoff-decision` file is
    already gone — it is deleted after `signoff.record` succeeds and BEFORE
    `driver.run_issue`, so a failed or held transition cannot leave the stale decision.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Reproduction:** in a scratch instance, put a bundle at AWAITING_SIGNOFF with an open §6
  row, write `accept` to `signoff-decision`, run `pdca signoff <id> --iterate-plan`, then
  `ls results/issue_<id>/signoff-decision` — the file is still there. Re-plan and rebuild;
  if the rebuilt SUMMARY's §6 is clear, re-running `pdca flow` takes the bundle straight to
  COMPLETE without a session (with §6 open, C6 refuses the stale accept and hides the bug).
- **Falsifiability:** RED on `main` at legs (a), (b) (with §6 cleared), (d) and (e): the file survives and the
  pre-apply accepts. Leg (c) is green on both sides and guards against an over-eager fix.
- **Invariant to restore:** a recorded sign-off decision is consumed by whichever route
  records it, so no decision outlives the attempt it was made about. Source: the C6
  accept-guard (an accept is never applied to a build nobody reviewed) and
  `flow._apply_decision`'s existing consume-on-record (flow.py:205).
- **Scope (one logical fix) / out of scope:** `cli._signoff` deletes
  `leaves.SIGNOFF_DECISION` after `signoff.record` succeeds and before `driver.run_issue`,
  matching `flow._apply_decision`. Only the success path. / Out of scope: the session
  carry-forward capture (`state.SESSION_CARRY`, flow.py:201-204) — do not add it to the CLI
  here; any change to `flow._apply_decision`; the same-wave trial (#395 core, a sibling
  child); adding `signoff-decision` to `state.DOWNSTREAM_OF_BRIEF`.
- **External dependencies:** none
- **Test file:** `template/tests/test_signoff_consumes_decision.py` (new). Import modules
  only (`from pdca_harness import cli, flow, leaves, signoff, state`), never a symbol this
  change adds, so the red leg imports and fails on assertions. For leg (b), drive
  `flow._drive_wave` the way `template/tests/test_signoff_orphan.py:131-204` does, with a
  stubbed `leaves.run_signoff_batch`.
- **Citations expected:** Do cites path:line on the target branch for every change.
- **Difficulty:** low
- **Disposition hint:** likely-fix
- **Prior-art check:** found as the sign-off finding on #395's iteration 7. That
  carry-forward section is preserved in the cumulative brief archived with iteration 9:
  `results/issue_395/iteration-v9/brief.md:121-122` (header "Iteration 7 — carry-forward",
  rationale "fix the stale-accept path … cli._signoff delete signoff-decision once it
  records a decision"). Hence the v9 path for an iteration-7 finding. No earlier fix on
  `main` (`cli.py:1525-1550` has no unlink).
Plan-review response: all four findings addressed. Provenance confirmed and the
iteration-7-vs-v9 wording explained (Prior-art check). Leg (b) now clears §6, pins
`max_passes=1` and `auto_iterate` off, and asserts the precondition. New leg (e) tests the
delete-before-`run_issue` ordering.
