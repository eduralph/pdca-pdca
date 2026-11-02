## Summary
**User impact:** A bundle you sent back for re-planning with `pdca signoff <id>
--iterate-plan` can later be marked COMPLETE by `pdca flow` with no sign-off session at
all. It happens when an earlier `pdca flow` session's `accept` was refused (NEEDS-HUMAN
items still open) and you then used the standalone `pdca signoff` command instead. The old
`accept` stays on disk, and once the bundle has been rebuilt and its NEEDS-HUMAN list is
clear, the next `pdca flow` run applies that old `accept` to the new build. You end up
with an accepted, published-ready bundle that nobody looked at.

This PR makes the standalone `pdca signoff` delete the leftover decision file as soon as it
has recorded your decision, exactly as `pdca flow` already does.

Reported in [#780](https://github.com/eduralph/pdca-harness/issues/780).

## What to look at
- **The change is one line** in the `pdca signoff` command: after it writes your decision
  into `SUMMARY.md`, it removes the bundle's `signoff-decision` file. The flow path has done
  this for a long time; the standalone command simply never did.
- **Where the line sits matters.** It runs only after the decision was really recorded, so
  a refused accept (NEEDS-HUMAN still open) or a SUMMARY that cannot be written to still
  keeps the file, since nothing was consumed. And it runs before the state transition, so a
  transition that fails or is held cannot leave the stale file behind.
- **To reproduce on `main`:** in a scratch instance, take a bundle at AWAITING_SIGNOFF with
  an open NEEDS-HUMAN row, write `accept` into `results/issue_<id>/signoff-decision`, run
  `pdca signoff <id> --iterate-plan`, then `ls results/issue_<id>/signoff-decision`. The
  file is still there. Re-plan and rebuild; if the rebuilt SUMMARY has no open NEEDS-HUMAN
  row, `pdca flow` takes the bundle straight to COMPLETE without a session.

## Root cause
`cli._signoff` (`template/src/pdca_harness/cli.py:1504`) records the decision in §9
(`:1529-1537`) and drives the transition (`:1540`), but never deletes
`leaves.SIGNOFF_DECISION`. `flow._apply_decision` deletes it once it records
(`template/src/pdca_harness/flow.py:205`). A flow accept refused by C6 (`flow.py:177-179`)
therefore leaves `accept` on disk; after a standalone `--iterate-plan` archives and
rebuilds the bundle, the next wave's pre-apply (`flow.py:2516-2522`) reads the old `accept`
and, with §6 clear, finishes the rebuilt bundle with no session.

## Fix
`cli._signoff` deletes `(d / leaves.SIGNOFF_DECISION)` with `unlink(missing_ok=True)` after
the `signoff.record` try/except and before `driver.run_issue` (patched `cli.py:1538-1542`).
This mirrors the order in `flow._apply_decision` (`flow.py:205` → `:211`). No import change;
`leaves` was already imported (`cli.py:22`).

Not changed, on purpose: `flow._apply_decision` itself, the session carry-forward capture
(`flow.py:201-204`, the CLI takes its rationale from `--delta` instead), and
`state.DOWNSTREAM_OF_BRIEF`. Review note for a later PR: a shared "record and consume"
helper used by both paths would stop them drifting apart again.

## Verification
- **Claim:** after a standalone sign-off records a decision, `signoff-decision` is gone,
  for every recording action.
  - **Checked:** `cli.py:1529-1537` on `main` is the only recording path; the unlink is
    placed right after it.
  - **Test:** `template/tests/test_signoff_consumes_decision.py:103`
    (`--iterate-plan` with a stale `accept`) and `:111` (all four actions, with
    `signoff.record` wrapped to prove a decision was really recorded).
- **Claim:** end to end, a stale `accept` no longer finishes a rebuilt bundle; the next flow
  wave offers it a fresh session.
  - **Checked:** `flow.py:2516-2522` on `main` — the pre-apply applies whatever
    `signoff-decision` holds before `run_signoff_batch` is offered the bundle.
  - **Test:** `:126` — iterate-plan, rebuild to AWAITING_SIGNOFF, clear §6 and assert
    `open_needs_human == []` (so C6 would permit the stale accept), then one
    `_drive_wave` pass with `auto_iterate` off and a spying `run_signoff_batch`. Asserts
    not COMPLETE, still AWAITING_SIGNOFF, and the bundle was offered a session. On `main`
    this fails with `'COMPLETE' == 'COMPLETE'`.
- **Claim:** nothing is consumed when nothing was recorded.
  - **Checked:** the C6 refusal (`cli.py:1515-1520`) and the `ValueError` return
    (`cli.py:1532-1537`) both exit before the new line.
  - **Test:** `:154` (C6-refused accept keeps the file) and `:162` (`record` raising keeps
    the file). Both pass on `main` and on this branch; they guard against an over-eager fix.
- **Claim:** the file is gone before the transition runs, so a failed or held transition
  cannot leave it.
  - **Checked:** `cli.py:1540` (`driver.run_issue`) and `:1542-1549` (held path returns 1)
    on `main`; the unlink precedes both in the patch.
  - **Test:** `:171` (`run_issue` raises) and `:179` (`run_issue` returns a held state).
- **Red → green:** with only the `template/src/*` hunk reverted, the new test file reports
  `FAILED (failures=8)` (7 tests, 4 subtests); with it applied, `OK`. An independent
  reviewer repeated the revert and got the same result. Full offline driver suite
  post-fix: 2654 tests, OK (2 skipped). Docs lint and site render/link audit clean.

Fixes #780
