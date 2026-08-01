# Design proposal — issue 340 / dependency-probe-at-plan-exit

> Plan artifact (design-proposal form). Do reads ONLY this file.

- **Slug:** dependency-probe-at-plan-exit
- **Kind:** enhancement (design proposal)
- **Goal:** the Plan-exit dependency guard actually *runs* the detect commands. Since
  #333 landed (`b0bc575`, `plan_policy.py`) an **unregistered** token holds the bundle —
  but a registered row is never executed: `registered_ids` only requires a non-empty
  `cmd`, and `plan_policy.py` contains no subprocess call (verified on main). A planner
  can discharge every existing check on a machine where the dependency is absent; Do
  then dispatches into the silently-worked-around case whose only detector is the
  builder's own self-report — the actor the planner prompt identifies as prone to
  concealing it.
- **Success criterion:** (a) a brief whose `External dependencies` names a backticked
  token matching a registered `[[doctor.checks]]` row whose detect `cmd` exits
  **non-zero** is held before Do dispatches, quoting that row's `hint`; (b) a passing
  detect ⇒ behaviour unchanged; (c) ONLY the rows the brief's tokens name are executed —
  a registered row the brief does not name is not run (asserted in a test, per the
  issue's definition of done); (d) `(no-check: …)`-annotated and plain-prose
  dependencies yield no token and are not probed; (e) the guard works at `lanes = 1`
  (the path with today zero preflight); (f) rows are read from disk
  (`Config.current_doctor_checks`, `config.py:391`) so a row added during the Plan beat
  counts in the same pass; (g) the probe runs *after* the #333 registration check — an
  unregistered token holds for that reason first; (h) `[driver].dependency_guard`
  keeps its existing modes with `off` byte-identical to today and `warn` printing
  without holding. Demonstrable by C4-verify via the offline driver suite (stub rows
  with `true`/`false` as detect cmds).
- **Falsifiability:** the offline driver suite on this host
  (`template/tests/test_dependency_guard.py` already exercises the #333 hold — append
  there). RED now: a test registering a row with `cmd = "false"`, naming its token in
  the brief, and asserting a hold fails on current `main` — `plan_policy` reports only
  `unregistered-dependency` (`_BLOCKING`, `plan_policy.py:62`) and never executes the
  command, so the bundle proceeds.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Depends on:** none
- **Conflicts with:** none
- **Ordering note:** #333 (the stated prerequisite) is already merged on target main,
  so this schedules freely. 331 and 341 *depend on* this bundle (they reuse the probe) —
  they land in later waves; that is expressed in their briefs.
- **Difficulty:** medium
- **Scope:** layer B of the issue only — the deterministic Plan-exit probe in the
  driver: execute the detect `cmd` of exactly the rows named by
  `brief.external_dependency_tokens` (`brief.py:250`) ∩ registered rows, hold on
  non-zero via the existing `PolicyHold` mechanism, honour the mode config, document
  that detect cmds must stay cheap and side-effect-free (they now run every beat the
  policy is consulted). / out of scope: layer A (the `/handoff` session-contract
  clause — #331 owns it and depends on this probe); #341 (reusing the probe at Do
  exit); container-provisioned gates (`[install].extra_bootstrap` keeps its own
  provisioning); weakening the default to `warn` (rejected in the issue: this is an
  exit code, not a heuristic — the existing default stands).
- **External dependencies:** none
- **Test file:** template/tests/test_dependency_guard.py
- **Citations expected:** Do must cite path:line on the target branch for every change.
  Peer callsites: the hold path to extend — `plan_policy.py:62`
  (`_BLOCKING = frozenset({"unregistered-dependency"})`), the mode handling at
  `plan_policy.py:174-180`, `PolicyHold` at `:65`; the token source —
  `brief.external_dependency_tokens` (`brief.py:250`); the row readers —
  `doctor.registered_ids` (`doctor.py:306`) and `Config.current_doctor_checks`
  (`config.py:391`); the cheap-subprocess pattern doctor itself uses to run a row's
  `cmd`.
- **Prior-art check (triage cycles):** `git -C ../pdca-harness log --oneline origin/main
  -- template/src/pdca_harness/plan_policy.py template/src/pdca_harness/doctor.py` —
  #321/#333 landed (registration hold, sizing guard); no commit executes a detect cmd
  at Plan exit; `grep -n subprocess plan_policy.py` empty. Not fixed, not in flight.
- **Disposition hint:** new-feature

## Motivation

The harm is fabricated evidence, not just wasted cost: an unmet dependency at Do tends
to be silently worked around (a code-read instead of a compile), faking the red→green.
Every check today forces *registration* of a detect command; nothing runs it. The probe
is machine-scoped and the builder runs on this same host, so probing the driver host
against the target checkout is the correct scope, not a compromise.

## Design

As in the criterion. The verdict stays recomputed per beat, never cached (the
`plan_policy.py` module docstring's own rule) — install the tool or fix the row and the
next beat proceeds.

## Alternatives considered

- Full `pdca doctor` sweep at Plan exit: slow, and holds bundles on tooling they do not
  need — scope to the brief's own tokens instead.
- `warn` default: rejected; an exit code is not a heuristic, and the host probed is the
  host the builder runs on.

## Impact & compatibility

`off` byte-identical to today; `hold` (default) gains the probe on top of the existing
registration check. Detect commands now run per policy evaluation — the cheapness
expectation moves into the config comment.

## Open questions

- None blocking; the issue's definition of done is the contract.

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a draft PR
MAY happen during the cycle. The PR MUST NOT be marked ready before sign-off accepts.
