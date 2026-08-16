## Summary
**User impact:** If you install copier the documented way — as a CLI in its own venv
(pipx-style) — the template's own render and `copier update` tests quietly skip themselves,
tell you `copier not installed` when copier is right there on your `PATH`, and the run still
finishes `OK` with exit 0. So the only checks that exercise a *rendered* instance can report
success having verified nothing, and the one message you get sends you off to install a tool
you already have.

This PR makes those tests say what actually stopped them — that *this interpreter* cannot
import copier — and gives the root suite an entry point that reports "could not tell" instead
of "passed" when none of that coverage ran.

Reported in [#495](https://github.com/eduralph/pdca-harness/issues/495).

## What to look at
Two things, and they are separable.

1. **The message.** The three copier-dependent suites no longer guess at availability when
   they are loaded; each one reaches copier at the moment it needs it, and if that fails the
   skip reason carries the real import error, the interpreter that failed, and where a
   `copier` executable was found on `PATH` — enough to tell "not installed" apart from
   "installed, but not importable from here". The logic lives in one new small helper
   (`tests/copier_support.py`) rather than being copy-pasted three times.
2. **The verdict.** A new runner (`tests/run_root_suite.py`) wraps the root suite and answers
   with three outcomes instead of two: passed, failed, or *no evidence* — the last one being
   exit `77` plus a `PDCA-UNVERIFIABLE:` line, the same convention this repo's own gates
   already ship. `CONTRIBUTING.md` names it and `render-check.yml` now runs it, so CI cannot
   go green on a job that rendered nothing.

To try it, use any interpreter that cannot `import copier` while a `copier` executable is on
`PATH` (a pipx install is exactly this):

```
python3 -m unittest discover -s tests   # unchanged: skips, exits 0 — but now says why
python3 -m tests.run_root_suite         # PDCA-UNVERIFIABLE: …, exit 77
```

With copier importable, both commands behave as they do today and the same seven render /
update cases run for real.

## Root cause
All three suites decide, at *collection* time, whether `import copier` works in the running
interpreter, and then report that answer as a statement about whether the tool is installed —
two different propositions, which come apart precisely on a CLI-only install. Separately,
`unittest`'s discovery exit has only two outcomes, so a run consisting entirely of skips is
indistinguishable from a run that verified the template: `Ran 7 tests … OK`, exit 0.

## Fix
The import probes and the `skipUnless` decorators they fed are removed; `tests/copier_support.py`
imports copier at the point of use and raises `unittest.SkipTest` with a reason built from the
real exception, `sys.executable` and `shutil.which("copier")`. In `UpdateCompat` the check runs
as the first thing in `setUpClass`, above the temp-dir allocation, because a skip raised out of
`setUpClass` means `tearDownClass` never runs. `tests/run_root_suite.py` judges a finished run by
two facts — did anything fail, and how many cases actually *executed* — and emits exit 77 with a
leading `PDCA-UNVERIFIABLE:` line when no copier-dependent case ran. `render-check.yml` routes
its two existing steps through it (same module selection, `fetch-depth: 0` untouched) and
`CONTRIBUTING.md` documents the command. The bare `unittest discover` path is deliberately
untouched; nothing is switched by an environment variable.

## Verification
- **Claim:** a skipped render/update case reports the condition that actually stopped it, and
  never asserts that copier is not installed.
  **Checked:** `tests/test_render_and_run.py:23-31`, `tests/test_render_cli_name.py:44-52`,
  `tests/test_update_compat.py:32-37` and `:232` on `main` — three byte-identical import probes,
  each reporting importability as installation; all three are gone here. On a pipx host the new
  reason reads:

  > copier is not importable by this interpreter (/usr/bin/python3): ModuleNotFoundError: No
  > module named 'copier'; a `copier` executable IS on PATH at /home/eddie/.local/bin/copier —
  > the tool is installed, but a CLI-only install (pipx-style, in its own venv) is not
  > importable from here. …

  It mirrors the voice this repo already uses for its other precondition at
  `tests/test_update_compat.py:239-241` on `main`.
- **Claim:** nothing decides availability before a test body runs, and no fixture is allocated
  ahead of the check.
  **Checked:** `tests/test_update_compat.py:232` on `main` is a class decorator evaluated at
  import, and `:242` allocates the temp dir before copier is ever reached; the check now runs
  first inside `setUpClass`. `test_a_skipped_run_leaves_no_temp_directory_behind` runs all three
  suites under an injected CLI-only posture, asserts `UpdateCompat` really reached `setUpClass`,
  and asserts the sandbox it owns is empty afterwards. Confirmed live too: `/tmp` entry count
  identical before and after a pipx-posture run.
- **Claim:** a run in which no copier-dependent case executed exits 77 with a leading
  `PDCA-UNVERIFIABLE:` line, while a run in which they did execute is unchanged.
  **Checked:** `template/src/pdca_harness/gates.py:85-86` on `main` defines that exit code and
  marker and `:762-775` honours it only at the start of a line and only on an exit of 0 or 77 —
  the new runner reuses both, printing the marker on the 77 path and nowhere else. The rule it
  applies is this repo's own, written at `template/engine/scripts/run-verify.sh:72-75`. Live:
  `/usr/bin/python3 -m tests.run_root_suite` → one `PDCA-UNVERIFIABLE:` line, exit 77 (also per
  module, for the two steps CI runs); `python3 -m tests.run_root_suite` with copier importable →
  `root suite OK: 24 executed, 0 skipped`, exit 0.
- **Claim:** the two in-repo consumers stop reporting such a run as green.
  **Checked:** `.github/workflows/render-check.yml:36-40` on `main` runs both modules through
  `python -m unittest`; both now go through the new entry point with the same per-module
  selection, and `fetch-depth: 0` at `:27` is left alone. `CONTRIBUTING.md:26` on `main` names
  only the offline driver suite; the root-suite command joins it there.
- **Claim:** the bare developer run is unchanged, and an importable copier changes nothing.
  **Checked:** `python3 -m unittest discover -s tests` on the patched tree still skips and still
  exits 0 (`OK (skipped=3)`) on the CLI-only posture, with no environment variable involved; with
  copier importable the suite runs 24 root cases (the 7 pre-existing render/update cases, same
  assertions, plus the new regression cases) — `OK` — alongside the offline driver suite's 1758
  tests. No new dependency.
- **Test:** `tests/test_copier_availability.py` (new, 17 cases) — fails pre-fix, passes
  post-fix. It imports and *runs* the three shipped suites and calls the shipped helper and
  runner rather than re-implementing them; only the postures are supplied by the test (a
  meta-path finder that makes `import copier` fail, a `shutil.which` answer), so the result does
  not depend on what the host has installed. It passes identically under an interpreter without
  copier and one with copier 9.17.0, and under both invocation shapes this repo uses
  (`discover -s tests` and `python3 -m unittest tests.<module>`).
- **Reverted-patch check:** at `acb214a`, `/usr/bin/python3 -m unittest discover -s tests -v` on
  the CLI-only posture prints `skipped 'copier not installed'` seven times, `Ran 7 tests in
  0.000s`, `OK (skipped=7)`, exit 0 — the defect verbatim — and `python3 -m tests.run_root_suite`
  does not exist.

Fixes #495
