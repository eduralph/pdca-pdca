# PR description

## Summary
**User impact:** when someone finishes one of the interactive working sessions
(planning, sign-off, publishing, or the retrospective), nothing checks that the
session actually produced what the next step needs. Simply closing the session
looks exactly like finishing the work, so a missing or half-written result is only
discovered much later, far from the person who could have fixed it on the spot —
and anything the session worked out but never wrote down is lost for good.

This PR gives every interactive session a checked exit: a `/handoff` command that
verifies the session's expected output and reports PASS/FAIL, a stop-time guard
that refuses to let a session end with its output missing or malformed (with a
typed "abandon with a reason" escape hatch), and live capture of the sign-off
discussion's rationale so it carries into the next attempt instead of being lost.

Reported in [#331](https://github.com/eduralph/pdca-harness/issues/331).

## What to look at
The heart of the change is one new module, `template/src/pdca_harness/handoff.py`
— all the per-session checks live there as plain, offline-testable Python. The new
`/handoff` command and the Stop guard (`template/.claude/hooks/handoff_guard.py`)
are both thin shells over it, so the two verdicts are single-sourced.

To try it in a rendered instance: run a sign-off session and end it without
writing the decision — the session is blocked with feedback naming what is
missing; `/handoff issue_<id>` shows the same verdict on demand, and
`python3 .claude/hooks/handoff_guard.py --abandon "<why>"` releases the session
deliberately, with the reason reported by the driver. Nothing new is ever written
into the result bundle: the verdict is exit status plus a printed report.

Design decisions carried in from the prototype (getwyrd/wyrd-pdca#166, four
review rounds): ids are required (no scan mode — a scan would judge old bundles
against a contract that postdates them), no verdict artifact in the bundle, and
brief fields are only required when the measured corpus of 85 real bundles
actually satisfies them.

## Root cause
`leaves._invoke` runs interactive sessions with `subprocess.run(argv + [seed],
...)` and no `check=` — the exit code is discarded and nothing else is captured
(`template/src/pdca_harness/leaves.py:252-257` on `main`), so session end and
contract discharge are indistinguishable. Separately, `flow._apply_decision`
flattens the sign-off rationale to a single line and then unlinks the decision
file (`template/src/pdca_harness/flow.py:181` and `:192`), destroying the only
structured copy before the iterate transition can read it.

## Fix
- **`template/src/pdca_harness/handoff.py`** (new): per-role contract checks —
  planner (authored brief, required fields read via `brief.whole_field` to survive
  multi-line values, plus the dependency probe shared with the pre-dispatch
  guard), sign-off (valid decision token + rationale for non-accept decisions),
  publisher (both contribution artifacts + the instance's deterministic lint),
  act (the session names the log entry it wrote, checked against a driver-supplied
  session-start baseline). Which contract is active derives from the render's
  `interactive = true` leaves, not a hardcoded list.
- **`template/.claude/commands/handoff.md.jinja`** + **`handoff_guard.py`**
  (new) and a `hooks.Stop` entry in `template/.claude/settings.json`: the command
  is ergonomics, the hook is enforcement; both call the same check. The hook is
  inert when no driver session is registered and fails open on bootstrap errors —
  a broken check must never trap a human.
- **`template/src/pdca_harness/cli.py`**: the lint core of `_contribcheck`
  (cli.py:1043 on `main`) is extracted into `contribution_problems()` with zero
  gate-behavior change, so the publisher contract reuses it rather than
  re-declaring the rules.
- **`flow.py` / `driver.py` / `state.py`**: `_apply_decision` captures the full
  rationale into `state.SESSION_CARRY` just before the unlink;
  `driver._carry_forward_into_brief` (driver.py:248 on `main`) merges it, deduped,
  with the §9 delta it already extracts, and archives it with its attempt.
- **`leaves.py`**: every command-mode interactive spawn runs inside
  `handoff.session(...)`, which supplies the role/state env and the act baseline.
  Stub modes are untouched, so offline flows and CI are unchanged.

The stop-time enforcement is Claude-family only (codex exposes no hook surface —
the same asymmetry the existing builder guard documents); the contract still
binds at the artifacts for every family, and `/handoff` works everywhere.

## Verification
- **Claim:** the driver's only completion signal for interactive leaves is
  process exit, with nothing captured.
  **Checked:** `template/src/pdca_harness/leaves.py:252-257` on `main` —
  `subprocess.run(argv + [seed], cwd=workdir, env=run_env)`, no `check=`, result
  discarded.
- **Claim:** the sign-off rationale's only structured copy is destroyed before an
  iterate can read it.
  **Checked:** `template/src/pdca_harness/flow.py:181` (flatten to one line) and
  `:192` (unlink) on `main`; `driver.py:248` reads recorded artifacts only.
- **Claim:** the publisher contract cannot drift from the contribution gate.
  **Checked:** `template/src/pdca_harness/cli.py:1043` on `main` — the gate's
  lint body was inline; now both call the one extracted `contribution_problems()`.
- **Test:** `template/tests/test_handoff.py` — fails pre-fix
  (`ImportError: cannot import name 'handoff' from 'pdca_harness'` with the
  production hunks reverted, tests kept), passes post-fix. Full runs: `make check`
  in `template/` → 1408 tests OK; repo-root `tests.test_render_and_run` (renders
  the template and runs the generated project's own suite),
  `tests.test_update_compat`, `tests.test_render_cli_name` → OK.
- **Manual (not covered offline):** Claude Code's dispatch of the project-level
  `hooks.Stop` is only exercisable interactively — the suites verify the
  registration and the verdict logic. One-minute check on a live run: end a
  sign-off session without the decision (blocked, with feedback), then
  `--abandon "test"` (released, reason reported).

Fixes #331
