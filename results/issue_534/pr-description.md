## Summary
**User impact:** in an interactive Plan, sign-off, publish or Act session, a question the
assistant asks you may never reach you. Until the session's required files are written,
every time the assistant finishes a turn it is sent a "you may not end yet" message and
keeps answering that instead of waiting for you. One sign-off session looped like this
twelve turns in a row, and the pressure is on the assistant to write the very file it is
waiting for you to decide — for sign-off, your accept/iterate decision.

This PR stops checking at every turn end. The session's required files are checked once,
when the session exits, and anything missing is printed for you to read; nothing is
blocked.

Reported in [#534](https://github.com/eduralph/pdca-harness/issues/534).

## What to look at
- The turn-end check is removed: the rendered project settings no longer register it, and
  the checking script does nothing when called the old way.
- A new end-of-session report in the handoff module: what it prints and the rules that
  stop it from hiding anything (an abandon reason never hides the problem list, one broken
  bundle never hides the others, a broken dependency table is reported, terminal escape
  characters are shown escaped).
- Text changes: the leaf prompts, the `/handoff` command and the render-and-integrate doc
  no longer claim a hook enforces the contract at turn or session end.

To try it: start an interactive sign-off session, ask the assistant a question before
writing a decision, and check that the turn comes back to you. Then quit without a
decision: the driver prints a `handoff: the signoff session ended; checking its exit
contract found …` report naming the bundle and the missing `signoff-decision`.

## Root cause
`handoff_guard.py` was registered as a Claude Code **Stop** hook, which fires each time the
main agent finishes a turn, not when the session ends; while the contract was open it
exited 2, and on exit 2 Claude Code feeds stderr back to the model rather than handing the
turn to the human. The Stop envelope's `stop_hook_active` flag was parsed and discarded, so
nothing bounded the loop.

## Fix
- **No turn-end hook.** The `hooks.Stop` entry is removed from
  `template/.claude/settings.json`. `_stop_verdict()` is removed from
  `template/.claude/hooks/handoff_guard.py`; the no-argument path returns 0 with no output,
  so an instance that kept the old registration through `copier update` cannot loop. An
  unknown mode now gets a usage error (exit 2) instead of falling through, so a typo like
  `--abandn` no longer silently records nothing.
- **Report at reap.** `handoff.session()`'s `finally` calls a new `report_at_reap()`, which
  prints the abandon reason (if any) and then every item `stop_problems()` finds, to stderr.
  It writes no bundle file, moves nothing, and never raises: output goes through `_emit`,
  which tolerates an unwritable stderr, and the scratch-file read and unlink are guarded
  (a deeply nested JSON scratch file used to raise `RecursionError` out of the `finally`).
- **The report hides nothing.**
  - `stop_problems()` no longer returns `[]` when `abandoned` is set; `_abandon_reason()`
    is the single reader, and a blank value is no reason.
  - Each bundle is checked in its own `try`, and a failure becomes
    `<bundle>: could not check (<error>)`.
  - `_doctor_table_problem()` reads `[[doctor.checks]]` once per planner reap. If the
    table is broken, or `pdca.toml` does not parse, the report gets one line naming the
    file, the table, the error, and that the dependency clause was not checked. Briefs are
    still checked with the new `check_planner(..., dependencies=False)`. `/handoff` still
    calls `check_bundle` without that keyword, so its behaviour is unchanged.
  - `_printable()` escapes every non-printable character in every reap line.
- **Text.** Prompts in `leaves.py` (`_plan_prompt`, `_plan_batch_prompt`, `_signoff_prompt`,
  `_signoff_batch_prompt`, `_publish_prompt`), comments in `run_signoff`,
  `run_signoff_batch`, `run_publish` and `do_plan_batch`, the `/handoff` command body, the
  `--abandon` reply and `docs/01-render-and-integrate.md` now say `/handoff` is the
  session's self-check and the driver reports an unmet contract when the session ends. The
  stale comment in `do_plan` (`leaves.py:916-917` on `main`) is left alone on purpose so
  the pending #480 change still applies; it is a developer comment, not text the model
  reads.
- **Tests.** New `template/tests/test_handoff_reap.py`. `test_handoff.py` inverts the
  "Stop hook is registered" and "abandon hides the list" assertions. Tests in
  `test_handoff.py`, `test_publish_slice.py` and `test_state_resolved.py` that end a session
  with an open contract now capture stderr, so the driver suite prints no `handoff:` lines.

Out of scope, tracked separately: re-reading the briefs a CSV/default batch Plan session
wrote (#549), `/handoff` in a rendered instance (#508), Act vs `/handoff` (#528).

## Verification
Line numbers on `main` are at `6ba00ba`; "after" means this branch.

- **Claim:** no turn end is intercepted, even with the old registration still in place.
  - **Checked:** `template/.claude/settings.json:60-71` on `main` held the Stop
    registration; `template/.claude/hooks/handoff_guard.py:48-73` on `main` returned 2 for
    an open contract, and the Stop envelope was discarded at `:53`. After: no `hooks` key;
    the no-argument path is `handoff_guard.py:77-79`.
  - **Test:** `test_handoff_reap.py` `NoTurnEndIsIntercepted` runs the hook in-process and
    once as a real subprocess, spelled the way the old registration ran it. It first
    confirms the contract check is live in that environment (`--check` exits 1), so a
    config that fails to load can't pass the test by accident. Fails on `main`, passes
    here.
- **Claim:** the contract is reported to the human when the session is reaped, and a
  discharged contract prints nothing.
  - **Checked:** `template/src/pdca_harness/handoff.py:306-311` on `main` printed only an
    abandon reason. After: `session()` `finally` at `handoff.py:396-412`,
    `report_at_reap()` at `:415-458`.
  - **Test:** `ReportedAtReap` covers a missing `signoff-decision`, `iterate-do` with no
    rationale, and a brief with an empty Success criterion. Fails on `main`, passes here.
- **Claim:** report only — nothing written, nothing raised.
  - **Checked:** `handoff.py:444-458` (one `try`), `_emit` at `:317-324`, scratch-file
    guards at `:403-412`.
  - **Test:** `ReportOnly` checks that the bundle is unchanged, that the leaf's own
    exception still passes through, and the nested-JSON and directory-scratch cases.
- **Claim:** the report hides nothing.
  - **Checked:** `handoff.py:374-375` on `main` returned `[]` for any abandon. After:
    `_abandon_reason` at `:282-292`; per-bundle `try` at `:556-561`; doctor-table read at
    `:327-350`, called from `stop_problems` at `:547-555`; `check_planner(dependencies=)`
    at `:102-141`.
  - **Test:** `ReportHidesNothing` covers the abandon-then-list order, a blank abandon, a
    non-UTF-8 decision file and a directory where a file belongs (in both registration
    orders), four broken-table shapes, an unparseable `pdca.toml`, and one table line
    across the id-batch, single-Plan and CSV sessions. It also confirms `/handoff` still
    fails as before on a broken table. Fails on `main`, passes here.
- **Claim:** session-written text cannot hide report lines with terminal escapes.
  - **Checked:** `_printable` at `handoff.py:303-314`, applied in `_emit`.
  - **Test:** `NothingPrintedRaw` uses an abandon reason carrying `ESC[8m`, a newline, a
    forged `- issue_7: all clear` item and U+202E, plus a dependency token with ESC quoted
    from a brief. Every reap in the file also asserts no raw control characters.
- **Claim:** model-facing text no longer promises hook enforcement.
  - **Test:** `ModelFacingTextPromisesNoEnforcement` runs one pattern over the `/handoff`
    command body, every contract-role prompt plus `_act_prompt`, and the hook's
    `--check`/`--abandon` replies. A self-check makes sure the pattern still matches every
    retired sentence word for word, plus four rewordings.
- **Claim:** `/handoff` and `--abandon` are unchanged apart from the reply text.
  - **Test:** `SelfCheckAndAbandonUnchanged`; `run_check` is untouched.
- **Suite:** the driver suite passes (1817 tests, 2 skipped) and its captured stderr has
  zero `handoff:` lines. The regression check was also run with the fix's non-test changes
  reverted: `test_handoff_reap` and `test_handoff` fail there and pass with the fix. The
  render/update-compat suites, the docs lint and the site link check all pass.

Fixes #534
