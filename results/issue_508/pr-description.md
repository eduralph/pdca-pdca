## Summary
**User impact:** In every project rendered from this template, typing `/handoff <id>`
during an interactive session fails straight away with a permission error, and the
check never runs. The session has no way to confirm it has finished its work before it
ends. Since the end-of-turn hook was retired, `/handoff` is the only check a session
can run on itself, so right now there is no working in-session check.

This PR changes `/handoff` so the session runs the check itself as an ordinary command,
which the permission check accepts. It also adds a test so no slash command can ship the
broken form again.

Reported in [#508](https://github.com/eduralph/pdca-harness/issues/508).

## What to look at
- The one file that changes behavior is the `/handoff` command text. A line that Claude
  Code used to run automatically before the prompt is replaced by an instruction telling
  the session to run the same check itself. The rest of the command (one required id, no
  claim that anything enforces the result) is unchanged.
- A new test file checks every slash command the template ships, so a command added
  later (such as the proposed `/abandon`, #404) can't bring the problem back.
- **To try it:** render the template, start an interactive session, and type
  `/handoff <id>`. Before this change you get
  `Error: Shell command permission check failed … Contains simple_expansion`. After it,
  the session runs the check and reports PASS/FAIL. This can only be seen in a live
  interactive session: `claude -p` does not show pre-execution output, so a headless run
  proves nothing either way.

## Root cause
`template/.claude/commands/handoff.md.jinja:13` ran the guard in a `!` pre-execution
block that contained two shell expansions, `$CLAUDE_PROJECT_DIR` and `$1`. Claude Code's
shell-permission checker refuses to match any allow-rule against a command that contains
an expansion, so `allowed-tools: Bash(python3:*)` (`:4`) cannot help: the block aborts
before the guard runs. The block came in with 900d63810caa75dc6c36dcdc38cf761c1c51573b
(#331). e9e59828dc6bc5e5914461a9c11a49f9c0914c10 (#534) retired the Stop hook and
reworded the text around the block, but left line 13 unchanged.

## Fix
- `template/.claude/commands/handoff.md.jinja:13`: the `!` block is replaced with four
  lines telling the session to run
  `python3 .claude/hooks/handoff_guard.py --check $1` with its Bash tool, from the project
  root. `$1` is filled in with the id before the session reads the text, so the command
  the session runs contains no expansion. This is the same form as the existing
  `--abandon` instruction (`:22-23`). It does not use `CLAUDE_PROJECT_DIR`, because a
  session's Bash tool does not receive that variable.
- `template/tests/test_slash_commands.py` (new): lists every file under
  `.claude/commands/`, finds each `!` block, and fails if one contains `$NAME`, `${…}`,
  `$1`/`$ARGUMENTS`, `$(…)` or a nested backtick. It resolves the directory from its own
  location, so it also runs inside a rendered project.
- Not changed: `handoff_guard.py`. Its `--check` docstring (`:9-10`, "used by the
  rendered `/handoff` command") is still accurate.

## Verification
- **Claim:** no `!` block in any shipped slash command contains a shell expansion.
  - **Checked:** `template/.claude/commands/` on `main` holds one file,
    `handoff.md.jinja`. Its only `!` block was line 13, which carried both expansions.
  - **Test:** `template/tests/test_slash_commands.py` fails on `main`
    (`'$CLAUDE_PROJECT_DIR'` found in the `!` block of `handoff.md.jinja`) and passes
    with this change.
- **Claim:** the relative path works from where interactive sessions start.
  - **Checked:** `template/src/pdca_harness/leaves.py:1001`, `:3539`, `:3688`, `:3758`
    start the planner, sign-off, Act and publish sessions with the project root as the
    working directory. `template/.claude/hooks/handoff_guard.py:38-39` finds the project
    root from the script's own location when `CLAUDE_PROJECT_DIR` is unset.
- **Claim:** `/handoff` still takes exactly one required id.
  - **Test:** `template/tests/test_handoff.py:121-132` (`argument-hint: <issue_id>`,
    "no scan mode", `$1` present, `handoff_guard.py` named) passes unchanged.
- **Claim:** the command text still makes no claim that a hook enforces the result.
  - **Test:** `ModelFacingTextPromisesNoEnforcement` in
    `template/tests/test_handoff_reap.py:727` passes unchanged.
- **Full offline suite:** `PYTHONPATH=src python3 -m unittest discover -s tests` in
  `template/`: 1895 tests OK (2 skipped, both existing Docker-only tests).
- **Not covered by tests:** the live permission-checker behavior. It can only be seen by
  typing `/handoff <id>` in an interactive session, as described under *What to look at*.
  The same form (the session running the guard with its Bash tool) already works in a
  downstream project on Claude Code 2.1.276.

Fixes #508
