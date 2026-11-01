## Summary
**User impact:** A typo in the `wave_mode` setting of `pdca.toml` (for example `"Merge"`, `"merge "` with a trailing space, or `"bogus"`) was accepted without a word. The instance then ran as if the setting were `"stack"`, so an operator who thought they had turned on merge mode got stacked pull requests and no warning. The only hint was `pdca waves` echoing the odd word in its summary line.

This PR makes `pdca` refuse any `wave_mode` other than exactly `"stack"` or `"merge"`: every subcommand stops with one line on stderr naming the key, the bad value and the allowed values, and exits 2 until the file is fixed.

Reported in [#842](https://github.com/eduralph/pdca-harness/issues/842). The issue body still describes an earlier criterion (print a note and fall back to `"stack"`); that was built, rejected at sign-off on 2026-10-30, and replaced by the fail-outright ruling recorded in the comment on the issue. This PR implements the ruling.

## What to look at
The change is one check in the config loader plus a new test file. To try it: in any rendered instance, set `[driver] wave_mode = "bogus"` in `pdca.toml` and run `pdca status`. Before: it runs normally in stack mode. After:

```
pdca: invalid pdca.toml — [driver].wave_mode 'bogus' is not one of stack | merge
```

and exit code 2. `"stack"`, `"merge"` and a missing key behave as before.

Two deliberate choices a reviewer may want to weigh:

- **Exact match, no case or whitespace folding.** Neither `"Merge"` nor `"merge "` enables merge mode today, so folding would silently start merging PRs for such an instance. Refusing is the safer direction.
- **Fail, do not fall back.** The neighbouring `[driver]` keys (`merge_requires`, `merge_wait_secs`, …) still print a note and substitute a default. After this PR `wave_mode` is the one key that hard-fails. That inconsistency is accepted for this slice; applying the same ruling to the other keys is a separate follow-up.

Behaviour change to expect: an instance that today has a typo in `wave_mode` will stop working on upgrade until the file is corrected. The message says what to write.

## Root cause
`Config.load` read `wave_mode` and kept whatever it found (`template/src/pdca_harness/config.py:733` on `main`). Every consumer tests `cfg.wave_mode == "merge"` or `!= "merge"` (`flow.py:2888`, `:2901`, `:3080`; `waves.py:149`, `:379`; `publish.py:251`, `:295`), so any value that is not the exact string `"merge"` behaves as stack mode. Nothing between the loader and those checks validated the value.

## Fix
`template/src/pdca_harness/config.py`: after reading `wave_mode`, raise `ValueError(f"[driver].wave_mode {wave_mode!r} is not one of stack | merge")` unless the value is a `str` and one of `("stack", "merge")`. The `isinstance` test runs first and membership is against a tuple, so an array or inline table (unhashable) is refused with the same `ValueError` rather than escaping as a `TypeError`. `!r` keeps the trailing space in `'merge '` and the brackets in `['merge']` visible in the message. The comment on the line records why matching is exact and why there is no fallback.

No CLI change: `cli.py:452-454` already catches `ValueError` from `Config.load` and prints `pdca: invalid pdca.toml — <message>` with return code 2. The loader itself prints nothing, so the line appears once.

Out of scope, knowingly: `template/.claude/hooks/handoff_guard.py:45` calls `Config.load` without a `try` and would show a traceback for a bad value — it has the same gap for any malformed `pdca.toml` today, and a bad file stops `pdca` before a leaf session can start, so it is left for its own issue. Adding `"none"` to the allowed set is a separate change that builds on this check.

## Verification
- **Claim:** every value other than exactly `"stack"` / `"merge"` makes `Config.load` raise `ValueError` whose message names `wave_mode`, the value as given, and `stack | merge`, with nothing printed by the loader.
  **Checked:** `template/src/pdca_harness/config.py:733` on `main` — the single unguarded read that the patch replaces.
  **Test:** `template/tests/test_config_wave_mode.py::test_unknown_values_raise` — 8 cases: `"bogus"`, `"Merge"`, `"merge "`, `"none"`, `1`, `true`, `["merge"]`, `{ mode = "merge" }`. Pre-fix: 8 failures (`ValueError not raised`). Post-fix: pass.
- **Claim:** the CLI reports it as one stderr line, no traceback, exit 2, without any CLI change.
  **Checked:** `template/src/pdca_harness/cli.py:446-454` on `main` — the `except ValueError` handler that prints `pdca: invalid pdca.toml — {exc}` and returns 2; it covers the new raise.
  **Test:** `template/tests/test_config_wave_mode.py::test_cli_reports_one_line_and_exits_2` — drives the real `cli.main(["status"])` from a temp directory holding `wave_mode = "bogus"`. Pre-fix: `0 != 2`. Post-fix: pass. Also run as real processes through the console entry point for `"bogus"`, `"merge "`, `["merge"]`, an inline table, a multi-line string and a TOML date: each exits 2 with exactly one stderr line and no traceback; `waves`, `doctor`, `flow`, `run` and the bare command behave the same.
- **Claim:** `"stack"`, `"merge"` and an absent key are unchanged — kept as given, nothing printed, no exception.
  **Checked:** `flow.py:2888`, `:2901`, `:3080`; `waves.py:149`, `:379`; `publish.py:251`, `:295` on `main` — all compare against the exact string `"merge"`, so the two accepted values are the only ones that ever changed behaviour.
  **Test:** `template/tests/test_config_wave_mode.py::test_known_values_and_absent_key_are_silent_and_kept` — green before and after the patch, as intended.
- **Claim:** an unhashable TOML value cannot escape as a `TypeError`.
  **Checked:** a variant with a bare `not in {"stack", "merge"}` set test was run against the same tests: the array and inline-table cases error with `TypeError`. The tuple-plus-`isinstance` form passes all 8.
- **Suite:** both target suites green with the patch applied — template-repo suite (render + update-compat) 50 tests OK; offline driver suite (`template/tests`, `PYTHONPATH=src`) 2700 tests OK, 2 skipped. No existing test or fixture relied on an unknown `wave_mode`.
- **Prior art:** `git log origin/main -- template/src/pdca_harness/config.py` (head `f40c149`) has no commit validating `wave_mode`; no open, merged or closed PR touching that path does either.

Fixes #842
