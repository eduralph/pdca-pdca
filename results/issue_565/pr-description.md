# Fix: two `pdca flow` runs can drive the same bundle at once

## Summary
**User impact:** Start a second `pdca flow` while the first one is still running and
both can end up driving the same issue. Nothing warns you. The two runs write the
same bundle's brief, patch, review and sign-off files in whatever order they happen
to reach them, so one run's build lands on top of the other's, and the bundle is
left in the state of whichever writer was last. It is easy to hit without trying:
naming an id someone else is already driving, running a CSV batch whose in-flight
sweep picks up a leftover another run has in hand, or following the `pdca flow
<child-ids>` line a split prints while the run that printed it is still going.

This PR makes a bundle belong to one live run at a time: a run claims each bundle
before it drives it, and a second run over a claimed bundle is told so instead of
driving it anyway.

Reported in [#565](https://github.com/eduralph/pdca-harness/issues/565).

## What to look at
One new module, `template/src/pdca_harness/drive_claim.py`, plus its wiring: `cli.py`
opens one claim scope for the whole run and claims every id you named before anything
touches the disk, and `flow.py` claims each bundle the run reaches on its own (the
CSV sweep, the children of a split) and gives a claim back at every point where the
run decides not to drive that bundle after all.

The behaviour splits along how the bundle was reached. Ask for it **by name** and a
run that may not drive it stops with exit 1, names the bundle and touches nothing —
you asked for that bundle, so quietly doing the rest would answer a question you did
not ask. Reach it **implicitly** and it is named and skipped, and the rest of the run
continues — a batch that aborts because one unrelated leftover is busy would be worse
than one that drives the rest.

To try it: brief a bundle, start `pdca flow N`, and while it is mid-build run
`pdca flow N` from a second shell. Before this change the second run drives the
bundle to completion under the first one. After it, the second run prints
`flow: issue_N is held by another live 'flow' run (pid …) — refusing to start a second
driver over it; no bundle was touched.` and exits 1. Kill the first run with
`kill -9` and the next run proceeds — the claim dies with the process.

`template/tests/test_flow_single_driver.py` (23 cases, new) is the readable statement
of all of this; the competing run in it is a real second process, not a thread.

## Root cause
A bundle's whole state is the files in `results/issue_<id>/` — "nothing is hidden in
a database" — so two runs writing one bundle have nothing to serialize on. No drive
path took any ownership: `cli._flow` (`cli.py:558`) dispatched straight into
`flow.flow_ids` / `flow.flow_batch` with no check on who else was driving, and the
only cross-process claim in the driver was Act's session lock over its own shared
resource (`act.py:125-159`). The race is also why following `split --accept`'s printed
`pdca flow <child-ids>` inside a live run went wrong (#498).

## Fix
`drive_claim.py` holds an exclusive, non-blocking advisory lock (the cross-platform
helpers Act's session already uses, `act.py:29-62`) on one file per bundle, keyed by
the bundle's resolved path. `cli._flow` opens the scope in the process that drives —
after `main`'s keep-awake re-exec, which a claim taken earlier would not survive —
and claims every named id before the first write; `flow.py` claims each swept bundle
and each adopted child where it is reached, and releases at the seven points where a
run stops driving a bundle (a named id it skips, a split parent once its adoption
pre-pass has read it, a swept bundle the scheduler holds, children a reschedule
drops or retracts). The lock lives on the open handle, so the OS drops every claim
when the run ends — a return, an exception, `SIGKILL` — and there is no stale-claim
cleanup to get wrong; it also means a run never refuses itself, and a bundle it
adopts becomes its own under the same rule. A claim that cannot be recorded at all
fails closed. The claim files sit in `process/.drive-claims/`, outside every bundle
and gitignored in the render. The resume line a run prints for a bundle it walked
away from but still holds now says the command applies once that run has ended.

Deliberately not covered, and written down where an operator meets it
(`docs/07-crosscutting.md`): the single-step verbs (`pdca run` / `signoff` /
`publish`) take no claim, and a CSV batch's Plan session runs before the batch claims
anything, so the planner — or a `pdca split --accept` it launches — can still rewrite
or split a bundle another live run holds.

## Verification
- **Claim:** a second run whose *named* ids include a bundle a live run holds exits
  non-zero before it changes any bundle's state.
  - **Checked:** `template/src/pdca_harness/flow.py:1747-1756` (the RESOLVED
    revalidation) and `:1758-1766` (the Plan pre-pass) on `main` (base `70ea12b`) are
    the first writes on the named-id path, and both sit below `cli.py:558` with no
    ownership check anywhere above them.
  - **Test:** `template/tests/test_flow_single_driver.py` —
    `test_a_second_flow_over_a_bundle_a_live_run_holds_is_refused` and
    `test_a_named_id_list_is_refused_whole_before_its_plan_pre_pass` fail pre-fix
    (`0 != 1 : a second driver ran while another process held 7`), pass post-fix. The
    competing run is a real subprocess, and "nothing was touched" is asserted by
    fingerprinting every path under `results/` (size, mtime, sha256), not a curated
    subset.
- **Claim:** a bundle reached only implicitly is skipped with a line naming it, and
  the rest of the run continues.
  - **Checked:** the CSV batch's in-flight sweep at `flow.py:1678-1692` and split
    adoption at `flow.py:1119` on `main` — both hand every bundle they find straight
    to the driver.
  - **Test:** `test_the_csv_sweep_skips_a_bundle_another_live_run_holds`,
    `test_split_adoption_skips_a_child_another_live_run_holds` (plus the two
    unclaimable variants) — fail pre-fix, pass post-fix.
- **Claim:** a claim lives exactly as long as its run, including when the run raises
  or is killed.
  - **Checked:** `act.py:125-159` on `main` is the peer this follows — a lock on an
    open handle, released by the OS with the process.
  - **Test:** `test_a_run_that_raises_leaves_nothing_behind` and
    `test_a_killed_run_holds_nothing_and_blocks_nothing`, which really sends `SIGKILL`
    to the holding process and then drives the bundle from a fresh run.
- **Claim:** a claim that cannot be recorded refuses rather than driving unclaimed.
  - **Checked:** `act.py:143-151` on `main`, which reports and skips when its own lock
    cannot be opened — the same fail-closed shape.
  - **Test:** `test_a_run_that_cannot_open_its_claim_refuses_rather_than_drive_unclaimed`
    and `test_a_run_whose_filesystem_cannot_lock_refuses_rather_than_drive_unclaimed`.
- **Claim:** every bundle the run decides not to drive is let go at that decision, so
  the resume command printed for it is not refused by the run that printed it.
  - **Checked:** the decision points on `main` — `flow.py:1774-1777` (no brief),
    `:1778-1798` (already terminal, and the split-parent seed handed to the adoption
    pre-pass at `:1482-1484`), `:1692-1697` (a swept bundle the scheduler holds,
    including the "nothing schedulable" return) and `:1242-1270` (children a
    reschedule drops or retracts).
  - **Test:** one case per release point (`…_with_no_brief_is_let_go_at_the_skip`,
    `…_already_terminal…`, `…_split_parent_seed…`, the two swept-bundle cases,
    `…_failed_reschedule…`, `…_reschedule_holds…`, `…_later_reschedule_retracts…`).
    These are green pre-fix by construction, so each was checked by deleting exactly
    its release line and re-running: every deletion turns its own case red and no
    other.
- **Claim:** a run that walks away from a bundle mid-flight but keeps going tells the
  truth about when the resume command works.
  - **Checked:** `flow.py:777` on `main` printed an unqualified "resume with
    `pdca flow N`" for a bundle the run still holds and goes on to sweep and publish.
  - **Test:** `test_a_resume_line_for_a_bundle_the_run_still_holds_says_when_it_applies`.
    One existing expectation in `test_flow_adopt_recovery.py:490` asserts that line by
    equality and is updated with it.
- **Claim:** nothing else changes.
  - **Checked:** `cli.py:843-844` (`split --accept`'s closing line) is untouched by the
    diff; claim files are confined to `process/.drive-claims/`, so `state.state` never
    sees one.
  - **Test:** `test_a_single_run_with_no_second_driver_says_nothing_about_claims` and
    `test_claims_live_outside_every_bundle_and_are_gitignored_in_the_render`.
- **Suites:** offline driver suite `PYTHONPATH=src python3 -m unittest discover -s
  tests` from `template/` — 1955 tests, OK (2 pre-existing skips, unrelated); root
  render/`copier update` suites OK; docs lint + site render/link audit clean. With only
  the production hunks reverted and the tests kept, 14 of the 23 new cases fail on real
  assertions (no import errors); with the fix, 23/23.

Fixes #565
