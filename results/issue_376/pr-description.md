## Summary
**User impact:** After `make install`, the tool's command does not work in a fresh
terminal — it fails with "command not found" until the operator figures out the
missing last step themselves (activating the venv, prefixing the full path, or
hand-rolling a symlink). It also breaks the project's own checks that call the
tool by its bare name, so a freshly set-up project fails out of the box.

This PR makes `make install` finish the job: it idempotently links the installed
command into `~/.local/bin` when that directory exists and is on PATH, and
otherwise prints the exact `ln -s` command to run — it never edits shell
profiles and never overwrites a command it doesn't own.

Reported in [#376](https://github.com/eduralph/pdca-harness/issues/376).

## What to look at
The new PATH-link step in `template/scripts/bootstrap-tools.sh` (the console
script section) — in particular its safety branches: link only when
`~/.local/bin` exists and is on PATH, never overwrite an existing entry that
isn't this project's own, and a check-only mode that reports without creating
anything. To try it: render the template, run `make install`, then invoke the
CLI by bare name in the same shell; re-run `make install` (the row reports OK,
nothing changes) and `make install-check` (reports only).

## Root cause
`make install` delegates to `template/scripts/bootstrap-tools.sh`, whose
console-script section ends after `pip install -e` into `.venv/bin`
(`template/scripts/bootstrap-tools.sh:76–90` on `main`) — nothing puts the
script on PATH. Meanwhile gate rows spawn the CLI by bare name via `/bin/sh`
(the shipped contribcheck row, `template/pdca.toml.jinja:850`), so a fresh
render + `make install` fails command-not-found until the operator fixes PATH
by hand.

## Fix
One step appended to the console-script section (whose header now also prints
under `--check`, so the row has a home in both modes):

- **Name source:** `pyproject.toml [project.scripts]` keys, parsed with tomllib
  via `$PYTHON` — mirroring the script's existing `pdca_config` heredoc idiom.
  Every key is linked (the template renders exactly one). No python / no
  pyproject / no keys / no `$HOME` → one WARN row, never a hard fail.
- **Create** `~/.local/bin/<cli>` → `.venv/bin/<cli>` only when `~/.local/bin`
  exists **and** is on `$PATH`; otherwise one WARN row whose hint is the
  literal `ln -s "<venv path>" "<link path>"` command — shell profiles are
  never touched.
- **Idempotent / never-clobber:** a link already pointing at this venv → OK,
  nothing executed; a stale link into *this* repo's `.venv` is refreshed
  (`ln -sfn`); anything else at that path (another instance's default-name CLI,
  a foreign binary) is WARNed about with both paths named and left untouched.
- **Optional, not required:** every not-OK outcome counts as an optional miss —
  a host without `~/.local/bin` still bootstraps green.
- **`--check`** (`make install-check`) reports OK / MISSING-with-hint and
  creates nothing.

No venv activation is needed: pip console-script shebangs pin the venv
interpreter by absolute path, so the symlink alone makes bare-name spawns
resolve.

## Verification
- **Claim:** `make install` exposes the console script on PATH via an
  idempotent, never-clobbering `~/.local/bin` symlink; `--check` only reports;
  a host without `~/.local/bin` (or with it off PATH) sees one WARN naming the
  exact command and still bootstraps green.
- **Checked:** `template/scripts/bootstrap-tools.sh:76–90` on `main` — the
  console-script section previously stopped at `.venv/bin` with no PATH step;
  `template/pdca.toml.jinja:850` on `main` — the gate row that spawns the CLI
  by bare name, which motivated the fix; in the new step, all four not-OK
  branches record the miss as optional (never a required miss).
- **Test:** `template/tests/test_bootstrap.py` — a new `PathLink` class (six
  tests) extends the suite's existing sandbox harness
  (`template/tests/test_bootstrap.py:40–54` on `main`) with an injected
  `HOME`/`PATH` and a pre-seeded fake `.venv`, and runs the real production
  script. Covered: install creates the link + row; `--check` reports and
  creates nothing; missing `.local/bin` and off-PATH each WARN with the exact
  `ln -s` command and create nothing; a re-run reports OK and changes nothing
  (same inode + mtime); a foreign link is never clobbered. All six fail without
  the production change and pass with it (13/13 with the patch; the 7
  pre-existing tests are unaffected). Offline, no network, no sudo:
  `cd template && PYTHONPATH=src python -m unittest tests.test_bootstrap`.

Fixes #376
