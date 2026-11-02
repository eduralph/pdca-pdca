# Build notes: issue 842, validate `[driver].wave_mode` at load

## Change

- `template/src/pdca_harness/config.py:733-740`: replaces the old one-line read at `:733`.
  A value other than exactly `"stack"` or `"merge"` now prints one stderr line and becomes
  `"stack"`. The comment is updated as the brief asks.
- `template/tests/test_config_wave_mode.py` (new): loads a real `pdca.toml` through
  `Config.load`, the way `template/tests/test_merge.py:679-697` does.

## Why this shape

- Follows the peer at `config.py:745-749` after the patch (`merge_requires`, `:738-742` on
  main): print a note, fall back. It leaves out the peer's `str(...).strip().lower()`, as the
  brief requires. Folding would turn `"Merge"` and `"merge "` into merge mode.
- The note prints the value with `!r` where the peer uses `'{value}'`. Without the quotes
  from `!r`, `"merge "` would read as `merge`, and the note would seem to reject a valid value.
- `not in` on a tuple compares with `==`, so non-strings, including lists and tables, raise
  nothing. The test only runs `1`, the case the brief names. Lists and tables follow from how
  `in` works on a tuple and are not tested.

## Ruled out

- A shared validation helper: there would be one caller, and the brief limits this to one site.
- Validating `merge_method` and adding `"none"`: both out of scope in the brief (follow-up
  issue and 843).

## Refuting the test

- **(a) Genuine red? Yes.** I ran the test before changing `config.py`:
  `cd template && PYTHONPATH=src python3 -m unittest tests.test_config_wave_mode` gave
  `FAILED (failures=5)`, one per unknown value, with messages such as
  `AssertionError: 1 != 'stack'` and `'none' != 'stack'`. The known-values test passed before
  the fix, which is right: that behaviour must not change. After the fix: `Ran 2 tests`, `OK`.
- **(b) Production path? Yes.** The test calls the real `Config.load` on a `pdca.toml` written
  to disk. Nothing is mocked.
- **(c) Fixture includes the fault? Yes.** The fixtures hold the bad values themselves:
  `"bogus"`, `"Merge"`, `"merge "`, `"none"` and `1`.

## Other checks

- Driver suite: `cd template && PYTHONPATH=src python3 -m unittest discover -s tests` gave
  `Ran 2699 tests`, `OK (skipped=2)`.
- Commit readiness: the target has no `.pre-commit-config.yaml`, no installed git hooks, no
  `core.hooksPath`, and no `ruff`, `black`, `flake8` or `pre-commit` reference in `.github`,
  `CONTRIBUTING.md` or `AGENTS.md`. So there was no formatter to run. `git diff --check` is clean.
- `template/pyproject.toml.jinja` has no `ruff`, `black` or `flake8` settings either.
- Root suite: `python3 -m unittest discover -s tests` gave `Ran 45 tests`, `OK (skipped=3)`.
