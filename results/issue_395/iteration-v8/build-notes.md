# Build notes — issue 395 / same-wave-conflict-refused-at-accept (iteration 8)

Target: `eduralph/pdca-harness @ main`, worktree base `a6af7f3` (the brief's origin/main).
Line numbers are in the patched worktree (`$PDCA_WORKTREE`) unless marked "base", which
means the unpatched `a6af7f3`.

Inputs read: `brief.md` with its Iteration 6 and 7 carry-forward blocks. The Iteration 7
block keeps the design and names `iteration-v7/` as the previous attempt, so I read
`iteration-v7/patch.diff` (the base of this attempt), `iteration-v7/build-notes.md`,
`iteration-v7/session-carry-forward`, the adversary report the carry-forward cites
(`iteration-v7/check-advisory-adversary.md`) and the v7 SUMMARY §6, to see which rows were
still open. Not opened: `iteration-v5/patch.diff` (v6 already took its mechanics) and the
stray `test_flow_same_wave_prepublish.py` (not in the patch).

## What this iteration changes

The sign-off kept the design and asked for one fix: the stale accept. I applied the v7
patch to `a6af7f3` (it applied cleanly) and changed only what that fix needs: the CLI,
one shared helper, a comment, two docs sentences and one test leg.

### The bug, traced

1. A trial refusal returns `"blocked"` and leaves `accept` in `signoff-decision`, as a C6
   refusal does (flow.py:206-207).
2. The refusal row and the wave-end line name the step
   `pdca signoff <id> --iterate-plan` (flow.py:394).
3. `cli._signoff` recorded the decision (base cli.py:1530) and ran the transition
   (base cli.py:1540) but never deleted the file. Only `flow._apply_decision` did
   (base flow.py:205).
4. An iterate does not archive the file. `driver._archive_iteration` (base driver.py:457)
   moves `state.DOWNSTREAM_OF_BRIEF` (base state.py:116), which does not list it.
5. On the next run the re-planned, rebuilt bundle reaches AWAITING_SIGNOFF. Auto-iterate
   declines because a decision is on disk (flow.py:576-580). The pre-apply
   (flow.py:2782, `_apply_recorded_decision` at :488) applies the old `accept`, and the
   bundle is accepted and published with no session.

I reproduced it with the new leg and only the CLI fix reverted (see "Refuting my own
test"): stderr says `issue_11 — applied the 'accept' sign-off decision already recorded in
the bundle; no new session`.

### The fix: the CLI deletes the file once it records a decision

- New `flow.consume_decision(d)` (flow.py:243-257) deletes `signoff-decision` and the
  same-wave refusal record (`state.SAME_WAVE_REFUSAL`). It is the one rule for "a decision
  is now recorded in §9", called by both routes that record one.
- `flow._apply_decision` calls it where it used to delete the decision file
  (flow.py:233; base flow.py:205). This also replaces v7's separate delete of the refusal
  record (v7 flow.py:222-223). The flow route deletes the same two files as in v7; the
  refusal record now goes after the session carry-forward capture (flow.py:229-232)
  instead of before it. The two do not touch the same file.
- `cli._signoff` calls it right after `signoff.record` succeeds and before
  `driver.run_issue` (cli.py:1538-1549). Before the transition, so the iterate's archive
  never runs with the file still there, and a hold or a failure in the transition still
  finds it gone. Only after a recorded decision: an `--accept` that C6 refuses
  (cli.py:1515-1520) or a SUMMARY that cannot be written to (cli.py:1532-1537) records
  nothing and deletes nothing, so the decision stays for the run to offer again.
- When the deleted file held a different decision from the one the CLI records, the CLI
  says so on stderr (cli.py:1547-1549), for example
  `signoff: issue_11 — deleted the 'accept' decision a sign-off session left in the bundle,
  which was never applied; this records 'iterate-plan'`. The read is guarded
  (cli.py:1542-1545): §9 is already written at that point, so an unreadable file must not
  crash the command before the transition. It is deleted all the same.
- This also closes the same gap for a plain C6 refusal on `main` (the adversary pointed
  out it existed there), because the CLI route is the same.
- `state.py:62-70`: the record's comment now names the helper and both routes.
- Docs: `docs/05-check.md:196-202` (the four CLI dispositions) says recording any of them
  deletes a decision a flow session left unapplied. `docs/07-crosscutting.md:733-735`,
  right after the refusal's step, says the iterate-plan deletes the refused accept, in the
  session or with the CLI, so the rebuilt bundle waits for a session of its own.

### Why this, and not the alternatives

1. **Point the row's step at the in-session iterate-plan instead** (the carry-forward's
   other option). Not done; the step still names the CLI command (flow.py:394).
   - It would leave the cause in place. The CLI would still record and keep the file, so
     anyone who uses `pdca signoff <id> --iterate-plan` (documented at
     `docs/05-check.md:190-193`), or does so after a plain C6 refusal, still gets an
     unreviewed accept on the next run.
   - Once the bundle is parked, the run offers it no more sessions, so the CLI command is
     the only route left until a re-run.
   - An in-session iterate-plan does not do what the brief's recovery wants. It is applied
     at once, even in the batch sweep (flow.py:238), and the next pass's Plan pre-pass
     re-plans it (flow.py:781). The waves are fixed when the run starts, so the re-planned
     bundle is rebuilt in the same wave beside the partner it conflicts with, and the trial
     refuses it again unless the new plan changed the conflicting lines. The brief's
     recovery is "the next run schedules the bundle after its partner"; the CLI route
     after the run is that.
   - With the CLI fixed, both routes are safe, and the docs say so.
2. **Add `signoff-decision` to `state.DOWNSTREAM_OF_BRIEF`** so an iterate archives it.
   Cost: 2 lines in state.py (a literal, as state cannot import leaves). Rejected: it
   covers iterates only, so a CLI `--accept` or `--discontinue` would still leave the file
   in a frozen bundle; it files a decision that was never applied into the archive of an
   attempt whose §9 says something else; and the two routes would still handle the file
   differently (the flow at record time, the CLI only at an archive). One helper on both
   routes is the same pattern as `accept_blockers` (flow.py:260-283), shared for C6 for
   the same reason: a CLI check of its own drifted from the flow's.
3. **Delete only on the CLI's iterate actions.** Rejected: `_apply_decision` deletes the
   file for every recorded decision, and the rule should be the same on both routes.

Considered and left alone:

- `cleanup._discontinue` (cleanup.py:154) records a discontinue with `signoff.record` and
  does not delete the file. A DISCONTINUED bundle is final and never offered sign-off
  again, so a file left there is never read.
- If the CLI's action matches the file's (a session wrote `iterate-plan` with a multi-line
  rationale, the run died before applying it, and the human then ran
  `pdca signoff <id> --iterate-plan`), the file's rationale is deleted without going into
  `session-carry-forward`, which the flow route captures (flow.py:229-232). On `main` the
  CLI never captured it either: the file stayed and was applied again to the next
  attempt. The CLI's own `--delta` is what it records. Capturing it would be a #331
  enhancement, not this fix.

## Test → success criterion

`template/tests/test_flow_same_wave_accept_trial.py` (copy in the bundle,
byte-identical). Same fixture and stubs as v6/v7: real git (`StackFoldGit`), `gh`
stubbed, publisher in `command` mode, every accept through the real
`flow._drive_and_act` → `_drive_wave` → `_apply_decision`. The test never calls
`signoff.record(... "accept")` and does not stub `_drive_wave`. Only modules are imported,
plus `types.SimpleNamespace` from the standard library; the new leg uses no symbol this
patch adds (`cli._signoff`, `leaves.signoff_decision` and `state` all exist on base).

New leg, the one the carry-forward asks for:
`test_iterate_plan_from_the_cli_leaves_the_rebuilt_bundle_to_a_new_session` (line 504).

1. Leg (h)'s setup: wave 0 is 10 and 11 (same line of `shared.txt`) and 12; wave 1 is 20.
   Each session writes `accept`. 11 is refused and parked, not published. The leg checks
   the refused `accept` is really on disk.
2. `cli._signoff(cfg, SimpleNamespace(issue_id="11", iterate_plan=True, …))`, the
   `pdca signoff 11 --iterate-plan` handler. rc 0, 11 is UNPLANNED (its brief archived).
3. Re-plan: 11's brief is written again with `Conflicts with: 10`.
4. Re-run the same ids, driving 11 alone (`flow_ids` skips the finished ones),
   `max_passes=1`. 11's session stub records the state and decision it finds, and writes
   nothing (the human reads the new attempt and decides later).
5. Asserts: 11 was rebuilt; its session opened once, on AWAITING_SIGNOFF with no decision
   on disk; no "applied the 'accept'" line; 11 is not published (still AWAITING_SIGNOFF,
   no `fix/11` on origin, no `gh pr create` for it, not held); the CLI's stderr named the
   deleted `'accept'`.

All other legs are v7's, unchanged:

| Leg | Test (line) |
|---|---|
| (a) | `test_a_conflicting_accept_is_refused_and_its_sibling_published` (234) |
| (b) | `test_a_shared_file_that_merges_cleanly_is_accepted` (256) |
| (c) | `test_the_refusal_does_not_depend_on_which_accept_comes_first` (272) |
| (d) | `test_ticking_the_row_accepts_it_and_the_fold_holds_it` (292) |
| (e) | `test_a_trial_that_cannot_run_refuses_only_a_bundle_sharing_a_file` (307) |
| v7 fix 3 | `test_a_check_that_breaks_the_tree_refuses_and_names_it` (332) |
| (f) | `test_a_reassembled_summary_drops_the_row_and_the_next_accept_refuses_again` (390) |
| (h) | `test_a_refused_bundle_gets_one_more_session_then_the_wave_ends` (419) |
| v7 fix 1 | `test_a_session_that_fails_is_not_the_one_more_session` (441) |
| re-run | `test_a_later_run_offers_the_refused_bundle_a_session_again` (465) |
| v7 fix 2 | `test_a_later_run_parks_the_refused_bundle_after_one_session_too` (479) |
| **v8 (new)** | `test_iterate_plan_from_the_cli_leaves_the_rebuilt_bundle_to_a_new_session` (504) |
| plain C6 | `test_a_plain_c6_refusal_is_still_offered_a_session_every_pass` (541) |
| (g) | `test_on_the_last_wave_both_are_accepted_and_published` (555) |

## Refuting my own test

- **(a) Genuine red? Yes.**
  - C4 through the project's gate (`engine/scripts/run-verify.sh`, `PDCA_BUNDLE` /
    `PDCA_WORKTREE` set, under `timeout`): green leg 14 ran, OK. Red leg (every production
    hunk reverted, test kept): 14 ran, 11 FAIL, no import failure →
    `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`. The new leg fails there
    at its first check (on `main` nothing refuses 11: `'COMPLETE' != 'AWAITING_SIGNOFF'`).
    The 3 green on both sides are (b), plain C6 and (g), by design.
  - The leg binds this iteration's fix, not only the whole feature: with only the CLI
    hunk reverted (cli.py byte-identical to base, the rest of the patch in place), the
    same wrapper ran 14, exactly 1 FAIL, the new leg:
    `AssertionError: Lists differ: [] != [('AWAITING_SIGNOFF', '')]` (no session offered),
    with stderr `flow: issue_11 — applied the 'accept' sign-off decision already recorded in
    the bundle; no new session` (the adversary's finding). Wrapper verdict
    `PDCA-EVIDENCE: C4 FAIL — bundle test red WITH the fix applied`. I restored the hunk
    and checked `git diff` against `patch.diff`: byte-identical.
- **(b) Production path? Yes.** The real `cli._signoff` (the `pdca signoff` handler, minus
  argparse), real `signoff.record`, real `flow.consume_decision`, real `driver.run_issue`
  → `_carry_forward_into_brief` → `_archive_iteration`; then the real `_drive_and_act` →
  `_drive_wave` → `_apply_recorded_decision` → `_apply_decision`. Stubbed: Do/Check
  (`_build_all`), the sign-off leaf, publish's mechanics and `gh`, none of which this
  change touches.
- **(c) Fixture includes the fault? Yes.** The stale `accept` is the one the real trial
  refusal left in the first run (the leg asserts it is on disk before the CLI call), and
  the re-run drives the rebuilt bundle through the same pre-apply that applied it.

## Suites and commit readiness

All three were run last on the final `patch.diff` (C4 after T3 had finished, as C4
reverts production code in the same worktree T3 tests):

- T3 (`engine/scripts/run-suite.sh`, both target suites, under `timeout`): root suite
  24 tests OK, driver suite 2644 tests OK (skipped=2), v7's 2643 plus the new leg;
  `PDCA-EVIDENCE: root suite OK, driver suite OK`, rc=0.
- T2 (`engine/scripts/run-docs-check.sh`): `lint_docs: OK`, `render_site: link audit OK`
  (22 pages), `PDCA-EVIDENCE: docs lint clean, site render + link audit clean`, rc=0.
- C4 (`engine/scripts/run-verify.sh`): green 14 OK, red 14 ran / 11 FAIL,
  `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`, rc=0; the worktree was
  byte-identical to `patch.diff` afterwards.
- `git diff --check` clean; no added line over 100 columns.
- The target configures no formatter, linter or commit hook: no `.pre-commit-config.yaml`,
  no ruff/flake8/black/mypy config (only `template/pyproject.toml.jinja`, the rendered
  project's), no `core.hooksPath`, only sample hooks. Its CI runs the docs check and the
  suites (T2/T3 cover them) plus `.github/triage` tests, which this patch does not touch.
- `git diff HEAD` in the worktree is byte-identical to `patch.diff`, and the patch
  reverse-applies cleanly there, so it applies to `a6af7f3` as is.

One slip to report: the first C4 run wrote its log to `/tmp/claude-c4-v8.log`, outside
the roots I was given. Later runs kept their output in the shell. The file is not part of
the patch or the bundle.

## Known limits

- Unchanged from v7: the split-during-last-wave case is a follow-up, and the hold-count
  rule's override loophole is accepted, both per the human's decisions.
- Seen while writing the new leg, not changed: the step's recovery (re-plan with
  `Conflicts with: 10`, re-run the same ids) builds the rebuilt 11 on the base without
  10's work. A re-run skips the finished 10, and the carry starts only from a plain
  `Depends on` (`_carry_finished` docstring, flow.py:1673-1676; `docs/07-crosscutting.md:715-717`
  says the same for a held `Conflicts with` partner). Until 10's PR merges into the base,
  the rebuilt 11's PR can still conflict with 10's. The brief fixes the step's wording
  ("declare `Conflicts with: <partner>` in its brief, then `iterate-plan`"), so I left it.
  The human may want the step or the docs to add "re-run it once <partner>'s PR has
  merged into your base", as the fold's own held-partner advice does. The new leg does not
  accept the rebuilt 11, so this does not affect it.
- The PR should say `refs #395`, not `closes`: this is a partial fix (brief, Goal).
