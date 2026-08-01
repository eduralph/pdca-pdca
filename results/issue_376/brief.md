# Design proposal — issue 376 / install-path-symlink

> The Plan artifact for a design-proposal-shaped enhancement. Authored at Plan
> (planner + human). Do reads ONLY this file and implements it; Check runs the
> regular gated check on the code. The `- **Label:** value` lines are parsed by
> the driver; the prose `##` sections are the design rationale.

- **Slug:** install-path-symlink
- **Kind:** enhancement (design proposal)
- **Goal:** `make install` (i.e. `template/scripts/bootstrap-tools.sh`) exposes the
  installed console script on PATH: idempotently symlink `.venv/bin/<cli_name>` →
  `~/.local/bin/<cli_name>` when `~/.local/bin` exists and is on PATH, reported as one
  `OK|INSTALLED` row; a WARN naming the exact `ln -s` command when `~/.local/bin` is
  absent or off PATH (never guessing at shell profiles); `--check`
  (`make install-check`) reports the row without creating anything. Closes the gap
  where every instance operator invents the last hop themselves — and where the
  shipped T4 gate row (`{{ cli_name }} contribcheck`, `template/pdca.toml.jinja:850`)
  spawns the CLI by bare name via /bin/sh and fails command-not-found on a fresh
  render + `make install` (the pdca-pdca instance hit exactly this on its first
  offline cycle).
- **Success criterion:** tests appended to `template/tests/test_bootstrap.py` go
  red→green against the script alone (the existing `_run_check`-style sandbox — temp
  root, synthetic `pdca.toml`/`pyproject.toml`, faked `HOME` and `PATH` passed via the
  subprocess env): (a) an install-mode run with a pre-seeded fake `.venv/bin` (stub
  `pip` + a `<cli>` script file) and a faked `HOME` whose `.local/bin` exists and is
  on the injected PATH creates the symlink `~/.local/bin/<cli>` → `.venv/bin/<cli>`
  and prints its row; (b) `--check` in the same setup reports the row and creates no
  symlink; (c) `HOME` without `.local/bin` (or with it off PATH) → WARN containing the
  exact `ln -s` command and no symlink created; (d) a re-run with the symlink already
  in place reports OK and changes nothing (idempotent); (e) an existing
  `~/.local/bin/<cli>` pointing somewhere OTHER than this venv is left untouched and
  WARNed about, never clobbered. Assert on stdout rows and the filesystem, not on the
  script's exit code (a sandbox host may legitimately lack `gh`, which is an unrelated
  required-miss).
- **Falsifiability:** goes RED on this instance's C4 gate
  (`engine/scripts/run-verify.sh`): the production hunk is
  `template/scripts/bootstrap-tools.sh` (classified PROD — matches the `*)` arm at
  run-verify.sh:44), the test lands in `template/tests/test_bootstrap.py` (kept
  through the red leg's `--exclude=template/tests/*`; run as
  `cd template && PYTHONPATH=src python -m unittest tests.test_bootstrap`,
  run-verify.sh:60). Red leg: script reverted → no symlink step exists → the row-name
  / filesystem assertions fail → red. Green leg: patch applied → green. Environment:
  bash + python3 + git only (base toolchain); the tests fake `HOME`/`PATH`/`.venv`
  themselves, so no sudo, apt, network, or real install is needed for the assertions.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Ordering note:** independent of issue 375 in this batch — disjoint file sets (375
  edits `.jinja` sources + a new root `tests/` file; this bundle edits
  `template/scripts/bootstrap-tools.sh` + `template/tests/test_bootstrap.py`). No
  `Depends on` / `Conflicts with`; both may run in the same wave.
- **Scope:** one logical change to `template/scripts/bootstrap-tools.sh` (a PATH-link
  step in the console-script section) + the appended tests. / out of scope: editing
  `template/Makefile` (its closing message stays name-agnostic; the new row is the
  communication), shell-profile mutation of any kind (the WARN prints the command,
  per the issue), Windows (`scripts/install.ps1` — separate surface), the root-level
  render suites (the offline driver suite is the home for this test), and changing
  the T4 gate row itself (its bare-name spawn is by design once the script is on PATH).
- **Difficulty:** low
- **External dependencies:** none — bash, python3 ≥ 3.11 (tomllib), git are the base
  toolchain; the tests construct their own temp `HOME`, `PATH`, and fake `.venv`.
- **Test file:** `template/tests/test_bootstrap.py` (appended to the existing suite —
  this instance's C4 contract reverts the production change and KEEPS the briefed
  test, so an appended test earns its red; verified against
  `engine/scripts/run-verify.sh:71–81`).
- **Citations expected:** Do must cite path:line on origin/main of
  eduralph/pdca-harness for every change. Composition peers Do MAY open:
  `template/scripts/bootstrap-tools.sh:104–141` — `pdca_config`, the established
  tomllib-via-`$PYTHON` heredoc parse to mirror for reading `pyproject.toml`
  `[project.scripts]`; `:31–33` — the `say`/`miss` row idiom every step reports
  through; `:76–90` — the console-script section the new step slots into (note `:79`
  `[ ! -d "$ROOT/.venv" ]` — a pre-seeded fake `.venv` skips venv creation, which is
  what makes the install-mode test cheap); `template/tests/test_bootstrap.py:40–54` —
  the `_run_check` sandbox harness the new tests extend (add env injection for
  `HOME`/`PATH` and an install-mode variant).
- **Disposition hint:** new-feature

## Motivation

`make install` puts the console script on `.venv/bin/` and stops; its closing message
tells the operator to run it from there (`template/Makefile:47`). Every instance
operator then invents the last step (activate the venv, prefix the path, hand-roll a
symlink). It bites twice: (1) gate commands spawn the CLI by bare name — the shipped
T4 row `{{ cli_name }} contribcheck` (`template/pdca.toml.jinja:850`) runs via /bin/sh
and fails command-not-found on a fresh render until the operator fixes PATH (the
pdca-pdca instance hit this on its first offline cycle); (2) `cli_name` namespacing
exists precisely so several instances share one machine (`copier.yml:92–97`) — the
design already assumes instances coexist on one PATH, but nothing ships that last hop.

## Design

- **Where:** a new step in `bootstrap-tools.sh`'s "console script (.venv)" section
  (after the `pip install -e` at `:88`), plus a `--check` branch that only reports.
  It must run under BOTH modes: `--check` reports (`OK` if the symlink exists and
  points at this venv, `MISSING` + the exact `ln -s` hint otherwise); install mode
  creates it (`ln -sfn` semantics only when the existing link already points into
  this repo's `.venv`; see collisions below).
- **The name:** parse `pyproject.toml` `[project.scripts]` keys with tomllib via
  `$PYTHON` — the authoritative single source of the console-script name
  (`template/pyproject.toml.jinja:16–17`; `template/Makefile:9–10` says exactly this).
  Mirror the existing `pdca_config` heredoc idiom (`:104–141`). Link every
  `[project.scripts]` key (the template renders exactly one). No
  pyproject / no keys / no python → skip with a WARN row, never a hard fail.
- **Conditions:** create only when `~/.local/bin` exists AND is on `$PATH`
  (`case ":$PATH:" in *":$HOME/.local/bin:"*`). Absent or off PATH → one WARN row
  whose hint is the literal command, e.g.
  `ln -s "$ROOT/.venv/bin/<cli>" ~/.local/bin/<cli>` — never mutate shell profiles.
- **Collisions:** an existing `~/.local/bin/<cli>` that is not a symlink into this
  repo's `.venv` (another instance with a literal `pdca` cli_name, or a foreign
  binary) is never overwritten — WARN naming both paths. A symlink already pointing
  at this venv → `OK` (idempotent no-op). The namespaced-name case is collision-free
  by construction; this rule covers the default-name case.
- **Status semantics:** the row participates in the existing `opt_missing`
  accounting at most (a missing PATH link is an optional nicety, `level` WARN) — it
  must never set `req_missing`; a host without `~/.local/bin` still bootstraps green.
- **Verified shape** (from the issue, re-confirmed on this instance): a symlink
  suffices with no venv activation — pip console-script shebangs pin the venv
  interpreter by absolute path, so a bare `sh -c '<cli> contribcheck'` (the T4 gate
  path) resolves through it.

## Alternatives considered

- **Mutate the operator's shell profile** (append PATH in `.bashrc`/`.zshrc`) —
  rejected by the issue itself: guessing at shell profiles is invasive and
  non-idempotent across shells; the WARN-with-exact-command keeps the operator in
  control.
- **`pip install --user` / pipx** — changes the install model wholesale (the venv is
  load-bearing for `extra_bootstrap` deps) for a problem one symlink solves.
- **Have gate commands reference `.venv/bin/<cli>` by path** — fixes only this
  repo's rows, not the operator's own terminal use, and hardcodes a layout the
  Makefile deliberately keeps name-agnostic.
- **Do it in the Makefile instead of the bootstrap script** — the script is the
  single bootstrap home (`make install` merely delegates, `Makefile:53–55`) and is
  what `--check` already reports through; splitting the step would fork the
  `OK|INSTALLED` reporting idiom.

## Impact & compatibility

Additive: no existing row changes meaning; a host without `~/.local/bin` sees one
WARN and behaves as today. Idempotent like every other bootstrap step (re-run → OK).
The script ships verbatim from the template (not `.jinja`), so this lands for every
instance on `copier update` with no answers change. A literal `pdca` cli_name still
just works single-instance; two default-name instances hit the collision WARN, not a
clobber. No `[[doctor.checks]]` template change needed — `install-check` is the
reporting surface.

## Open questions

None blocking. (If the maintainer prefers linking only when `[project.scripts]` has
exactly one key, tighten in review — the template renders exactly one either way.)

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.
