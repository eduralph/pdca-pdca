# build-notes — issue 376 / install-path-symlink

Target: eduralph/pdca-harness @ main (`2fbd613`), built in `$PDCA_WORKTREE`
(`pdca-harness.pdca-wt-l1`). All `path:line` below cite the worktree (base + patch
for new code; base for pre-existing code).

## What changed and why

**`template/scripts/bootstrap-tools.sh`** — one logical change, exactly where the
brief's Design section puts it (the "console script (.venv)" section, after the
`pip install -e` at base `:88`):

1. The section header now prints in **both** modes (patched `:76–77`). Rationale: the
   new step must run under `--check` too ("a `--check` branch that only reports"), and
   its rows need a section to live in — previously the whole section was inside
   `if [ "$CHECK_ONLY" = 0 ]` (base `:76`). The venv creation + `pip install -e`
   stay install-only, byte-identical (patched `:79–90`). No existing test asserts on
   `--check` *not* having this header (checked `template/tests/` + root `tests/`).

2. The PATH-link step (patched `:92–164`):
   - **Name source** — `pyproject_scripts()` (patched `:102–117`) parses
     `pyproject.toml` `[project.scripts]` keys with tomllib via `$PYTHON`, mirroring
     the `pdca_config` heredoc idiom (base `:104–141`) including the
     `2>/dev/null || true` swallow (py<3.11 / broken TOML → empty output, never a
     hard fail). Loops over **every** key (brief: "Link every [project.scripts] key").
   - **Degenerate skip** — no python / no pyproject / no keys / no `$HOME` → one
     WARN row, no `miss` (patched `:119–122`), matching the `leaf detection` WARN
     precedent (base `:154`). The `${HOME:-}` guard exists because the script runs
     `set -u` (base `:20`) — an unset HOME must degrade to a WARN, not kill bootstrap.
   - **Conditions** — creates only when `$HOME/.local/bin` exists AND is on `$PATH`,
     via the brief's own idiom `case ":$PATH:" in *":$LOCAL_BIN:"*` (patched
     `:124–126`, `:154–156`); otherwise WARN whose hint is the literal expanded
     command `ln -s "<root>/.venv/bin/<cli>" "<home>/.local/bin/<cli>"` (patched
     `:130`, `:155`). Never mkdirs, never touches shell profiles.
   - **Idempotence** — link already `-> $venv_bin` → OK, nothing executed (patched
     `:132–135`).
   - **Stale-but-ours** — a symlink whose target is under `"$ROOT/.venv/"` but not
     equal to `$venv_bin` is the one case the brief allows `ln -sfn` refresh
     ("only when the existing link already points into this repo's `.venv`",
     patched `:137–145`). A *relative* symlink target won't match the absolute-path
     case-glob and falls through to the collision WARN — deliberately fail-safe in
     the never-clobber direction (we only ever create absolute links, patched
     `:142`, `:161`).
   - **Collisions** — any other existing entry (foreign symlink or plain file) → WARN
     naming both paths, untouched (patched `:146–152`).
   - **Status semantics** — every not-OK outcome is `miss 0` at most (`opt_missing`),
     never `miss 1`: grep the step for `miss` — all four sites say `miss 0` (patched
     `:140`, `:147`, `:151`, `:155`, `:159`). A host without `~/.local/bin` still
     bootstraps green (exit 0), per the brief's status-semantics clause.

**`template/tests/test_bootstrap.py`** — the `PathLink` class (patched `:98–223`)
extends the `_run_check` sandbox idiom (base `:40–54`) exactly as the brief's
citations direct: env injection (`HOME`, `PATH`) and an install-mode variant
(`_run`, patched `:143–153`). Docstring line added at `:5–6`. Tests (a)–(e) map
1:1 to the Success criterion:

| brief | test (patched line) |
|---|---|
| (a) install creates link + row | `test_install_creates_the_symlink` `:160` |
| (b) `--check` reports, creates nothing | `test_check_reports_and_creates_nothing` `:170` |
| (c) no `.local/bin` → WARN + exact `ln -s`, nothing created | `test_no_local_bin_warns_with_exact_command` `:180` |
| (c) off-PATH variant | `test_local_bin_off_path_warns_and_creates_nothing` `:189` |
| (d) re-run → OK, changes nothing (inode+mtime equal) | `test_rerun_is_idempotent` `:198` |
| (e) foreign link WARNed, never clobbered | `test_foreign_link_never_clobbered` `:210` |

All assert on stdout rows + filesystem, never the exit code (brief: a sandbox host
may lack `gh`).

Sandbox specifics worth flagging:
- The fake `.venv/bin` is pre-seeded with a stub `pip` + `acmecli` (patched
  `:126–128` of the test) — this rides the brief-cited `[ ! -d "$ROOT/.venv" ]`
  skip (script base `:79`), so install mode runs end-to-end with no venv build,
  no network.
- Install mode runs the *whole* script, so tier 1 could otherwise call
  `sudo apt-get` (script base `:40–41` — a tty password prompt = a hung test) or
  `gh auth status` (base `:72` — network). The sandbox shadows `git`/`gh` (exit-0
  stubs) and `sudo` (exit-1 stub) via a PATH-prepended stub dir and passes
  `stdin=DEVNULL` (test patched `:131–137`, `:152`). This keeps the suite offline,
  fast, and hang-proof under the headless runner — while still executing the real
  production script.
- `HOME` is always overridden in the child env, so no test can ever write into the
  real `~/.local/bin`.

## Alternatives ruled out (per the brief, with the cost shown)

The brief's "Alternatives considered" already rejects shell-profile mutation,
`pip install --user`/pipx, path-hardcoded gate rows, and a Makefile home — I did not
revisit those. Decisions that were mine:

- **Grep the pyproject for the script name** instead of tomllib: ~5 lines shorter
  than the 16-line heredoc, but it re-introduces exactly the bug class the tier-2
  parser was rewritten to kill (script base `:99–103` — grep collects commented /
  structurally-wrong keys), and the brief mandates the tomllib idiom. Rejected.
- **A separate `== PATH link ==` section** instead of reusing the console-script
  section: same line count (±2), but the brief says the step slots into the
  console-script section, and one section keeps the `--check` output compact.
- **`ln -sfn` unconditionally** (3 lines shorter — drops the collision branch):
  violates the brief's never-clobber rule for the default-`pdca`-name multi-instance
  case. Rejected on correctness, not cost.

## Red→green evidence — via the project's runner

Runner: the instance's configured C4 gate cmd (`pdca.toml:826` →
`engine/scripts/run-verify.sh`), invoked once with `PDCA_BUNDLE`/`PDCA_WORKTREE`
exported, cwd = instance root, exactly as the driver does. It classifies
`bootstrap-tools.sh` PROD (`run-verify.sh:44`), keeps the test through the red leg
(`:72`), and runs `cd template && PYTHONPATH=src python -m unittest
tests.test_bootstrap` (`:60`). Result:

- **Green leg**: 13/13 pass (7 pre-existing + 6 new).
- **Red leg** (production hunks reverted, tests kept): 6 new tests fail
  (5 failures + 1 error — no `(PATH link)` row, no symlink on disk), 7 pre-existing
  still pass. `C4 PASS: red without the fix, green with it`.

## Forced self-refutation

- **(a) Genuine red?** **Yes** — the runner itself performed the revert
  (`git apply -R --exclude=tests/* --exclude=template/tests/*`) and re-ran: all six
  new tests went red (transcript above). Not a hand-wave; the gate's own red leg.
- **(b) Production path?** **Yes** — the tests execute the actual
  `template/scripts/bootstrap-tools.sh`: `SCRIPT` resolves to the production file
  (test base `:21`) and `setUp` copies *that file* into the sandbox at test time
  (patched `:121`), same mechanism as the pre-existing suite (base `:45`). No
  re-implementation, no mock of the behaviour under test.
- **(c) Fixture includes the fault?** **Yes** — real filesystem symlinks under a real
  (temp) `HOME`; the on-PATH condition is exercised through the script's actual
  `$PATH` string match, not a mocked predicate; the collision test plants a genuine
  foreign symlink and asserts it survives; the off-PATH test genuinely omits
  `.local/bin` from PATH. The only stubs (git/gh/sudo/pip) are *outside* the
  behaviour under test and exist to keep tier 1 offline/hang-proof — the link step
  itself runs unstubbed.

## Commit-readiness

The target repo ships no pre-commit config, no shellcheck/ruff/black wiring (checked
repo root + `.github/workflows/` — the only linters are Markdown docs checks, which
this patch doesn't touch). So "commit-ready" = the repo's CI: `render-check.yml`
renders the template and runs the generated project's `unittest discover -s tests`
(`tests/test_render_and_run.py:76–77`), which includes the rendered copy of
`test_bootstrap.py` — the new tests are sandbox-contained (own HOME/PATH/pyproject,
no new imports, no network) and pass there identically. `bash -n` passes on the
edited script; both files match the file's own style conventions.

## Out-of-scope confirmations

- `template/Makefile` untouched (brief scope).
- `scripts/install.ps1`, root render suites, T4 gate row untouched.
- No `[[doctor.checks]]` change (brief: install-check is the reporting surface).
- Existing `--check` tests unaffected: the sandbox has no `pyproject.toml`, so the
  new step emits only the `WARN PATH link skipped…` row — no `claude`/`codex`/
  `gemini` token appears (their `assertNotIn`s hold), verified by the green leg.

## External dependencies

None beyond the brief's base toolchain (bash, python3 ≥ 3.11, git). Nothing missing
to declare.
