# Fix: `split --accept` tells you to start a second flow over children a live run may drive

## Summary
**User impact:** Accept a split while a `pdca flow` run is still going and the last
line you read is "run `pdca flow <child-ids>` to drive the children". Follow it and
you start a second run over bundles the first run is about to drive itself. The
opposite case is silent: if the running flow never gets to the split's children —
nobody answered the parent's sign-off, or the split was accepted from another shell
after the run had moved on — the run ends without a word about them. The children
sit planned and undriven, and nothing tells you they exist or how to pick them up.

This PR makes that last line say only what is true when it prints, and makes every
run name, right before it ends, the split children it left unfinished, with the
command that resumes them.

Reported in [#566](https://github.com/eduralph/pdca-harness/issues/566).

## What to look at
Two behaviours, both small on the surface.

**The closing line of `pdca split <id> --accept`.** While a live run holds the parent,
or a live `pdca flow --from-csv` batch has not yet decided what it drives, it now reads:

> issue_500 marked split; a running `pdca flow` holds issue_500 and drives its
> children (601 602) if it reaches them — it lists any it did not drive when it ends.
> After that run ends, drive any left with `pdca flow 601 602`

It is a condition, never a promise: nothing at accept time can know whether the run
gets that far. In every other case — a standalone accept, an accept after the run has
ended, a parent the run has already let go — the line is exactly what it was.

**A new line at the end of a run.** For each split parent among the bundles the run
drove or was handed, it names the children still in flight that it did not drive:

> flow: issue_7 split; this run did not drive all of its children — 701, 702 left
> in-flight; drive them with `pdca flow 701 702`

Finished children are not named, so the command never points at work that is done. A
child that is itself split is not named either, but its own children are. No such
children, no line. The exit code does not change.

To try it: brief bundles 7 and 8 with 8 declaring `Conflicts with: 7`, run
`pdca flow 7 8`, and leave 7's sign-off unanswered. While the run drives 8, run
`pdca split 7 --accept` from a second shell. Before this change the second shell is
told to run `pdca flow 701 702` and the first run ends without mentioning 701 or 702.
After it, the second shell gets the conditional line and the first run ends by naming
both.

`template/tests/test_split_hint_live_run.py` (11 cases, new) is the readable statement
of all of this. Where a case needs "another shell", the other run is a real second
process, not a thread.

**Stacking:** this builds on #565 (PR #569, one live driver per bundle) and reads the
claim it adds. It should merge after #569. Line numbers below are on `main` with #569
applied.

## Root cause
The closing line was unconditional (`template/src/pdca_harness/cli.py:881-882`). It
predates split adoption: a run now drives the children of a parent it drove or was
handed (`flow.py:1546`, `:1626`), and a CSV batch sweeps every in-flight bundle after
its Plan session (`flow.py:1753-1763`), so "run `pdca flow <ids>`" became wrong
whenever such a run was live. Separately, adoption looks at a parent only in the wave
it was driven or recovered in, so a split that lands after that point is never looked
at again, and the run's tail (`flow.py:1713-1718`) reported nothing about it.

## Fix
- `cli._split` picks the closing line by asking whether a live run holds the parent's
  drive claim, or holds a marker a CSV batch keeps while it has not finished deciding
  what it drives. Held: the conditional line. Not held: the old line, byte for byte.
- `drive_claim.held()` answers that question by taking and at once releasing the same
  lock a run's claim uses — the OS has no way to look at a file lock without taking
  it, and a second lock beside #565's claim would be one more thing to keep in step. If it cannot open or lock the file it
  answers "not held", so an environment that cannot record claims still prints the
  old line rather than claim a run it cannot see.
- Because that check can collide with a real claim attempt, `Run.take` now retries a
  contended lock up to five times, a millisecond or so apart, before it reports the
  bundle held. A real holder keeps the lock for its whole run, so it is still
  reported; a check is gone before the second attempt.
- `flow._warn_stranded_split_children`, called from the tail of `_drive_and_act` (so
  named-id runs and CSV batches both get it), walks each split parent's recorded
  children. It skips a child the run drove, walks through a child that is itself
  split, skips a child that is finished, and names the rest. The "is it split?" test
  comes before the "is it finished?" test on purpose: a confirmed split parent is
  itself finished, so the other order would stop the walk above the very children it
  exists to reach. This is the same order and the same "finished" set
  (`flow.py:687`) that adoption already uses (`_adoptable`, `flow.py:933`).
- The planner prompt (`template/agents/planner.md.jinja:155`, `:182`), the planner seed
  text (`leaves.py:1119`) and `docs/07-crosscutting.md:342` now describe the new line,
  when it prints, and the end-of-run report.

Two known limits, both looked at in review and left as they are:
- A CSV batch keeps its marker for the whole batch, not only until its sweep has
  claimed its bundles. So while a CSV batch is running, any `split --accept` in that
  instance prints the conditional line, including for a parent the batch will not
  reach. The line stays true (it is a condition, and the end-of-run report covers the
  rest); it is more cautious than it strictly needs to be.
- The retry in `Run.take` is bounded. Five back-to-back collisions with a check would
  still produce a false "held by another run". A check holds the lock for
  microseconds, so this needs five separate accepts to land on five consecutive
  attempts.

## Verification
- **Claim:** an accept made while a live run holds the parent prints the conditional
  line and not the old one — from the run's own Plan session and from another shell.
  - **Checked:** `template/src/pdca_harness/cli.py:881-882` on `main` + #569 prints
    the old line with no condition of any kind.
  - **Test:** `test_in_run_accept_from_the_runs_own_plan_session_is_conditional` and
    `test_accept_from_another_shell_while_a_live_run_holds_the_parent_is_conditional`
    (the holding run is a real subprocess, paused while it holds the claim) — fail
    pre-fix, pass post-fix.
- **Claim:** an accept inside a CSV batch's Plan session, before the batch has claimed
  anything, also prints the conditional line.
  - **Checked:** `flow.py:1753-1763` — the Plan session runs first, and the sweep
    after it takes every in-flight bundle, a freshly split parent's children included.
  - **Test:** `test_csv_batch_not_yet_swept_is_conditional` — fails pre-fix, passes
    post-fix.
- **Claim:** with no live run in reach, the line is byte-identical to before.
  - **Checked:** the `else` branch in the diff reproduces `cli.py:881-882` exactly.
  - **Test:** `test_standalone_accept_prints_todays_line_unconditionally`,
    `test_accept_after_the_run_has_ended_prints_todays_line`,
    `test_accept_on_a_named_id_the_run_already_let_go_prints_todays_line` — each
    compares the last stderr line by equality. The third runs while a flow is alive
    and driving another bundle: a live run alone is not enough, it has to hold this
    parent.
- **Claim:** a run that ends without reaching a split's children names them with the
  command that drives them.
  - **Checked:** `flow.py:1546` and `:1626` are the only two points that look at a
    parent for adoption; the tail at `flow.py:1713-1718` prints nothing about splits.
  - **Test:** `test_end_of_run_report_names_split_children_the_run_never_reached` —
    the `pdca flow 7 8` scenario above. Pre-fix the run ends with 701/702 planned and
    no line naming them.
- **Claim:** finished children are never named, and the walk still goes through a
  split child to the children below it.
  - **Checked:** `flow.py:687` is the "finished" set adoption already uses; the new
    walk applies it after the split test, in `_adoptable`'s order (`flow.py:933`).
  - **Test:** `test_end_of_run_report_is_silent_when_every_split_child_is_finished`,
    `…_walks_through_a_split_child_to_its_own_children`,
    `…_walks_through_a_child_terminal_on_a_split_of_its_own`
    (`template/tests/test_split_hint_live_run.py:482-570`). Checked one branch at a
    time: delete the finished-child skip and two cases fail (`601, 602 left
    in-flight` for finished work); delete the walk-through and two fail; swap the two
    tests and the third fails, because nothing is printed where `pdca flow 801 802`
    should be.
- **Claim:** asking whether a bundle is held never makes a run refuse a bundle nobody
  holds.
  - **Checked:** `template/src/pdca_harness/drive_claim.py:158-168` on `main` + #569
    makes one lock attempt and reports "held by another live `flow` run" on any
    contention.
  - **Test:** `test_take_retries_past_a_forced_peek_collision_instead_of_a_false_refusal`
    — the collision is forced on a fixed schedule (the retry hook itself releases the
    competing lock), not left to timing. Pre-fix it is a false refusal.
- **Claim:** nothing else changes.
  - **Checked:** the diff touches no other line of `cli._split`, and none of the
    existing adoption report lines in `flow.py`.
  - **Test:** the existing `test_flow_adopt_split.py`, `test_flow_adopt_recovery.py`
    and `test_flow_single_driver.py` pass unchanged.
- **Suites:** offline driver suite, `PYTHONPATH=src python3 -m unittest discover -s
  tests` from `template/` — 1966 tests, OK (2 pre-existing skips, unrelated); root
  render / `copier update` suite, 24 tests, OK; docs lint and site render + link
  audit clean. With only the production hunks reverted and the new test file kept,
  the file goes red (6 assertion failures, plus 1 error for the retry hook that does
  not exist yet); with the fix, 11/11.

Fixes #566
