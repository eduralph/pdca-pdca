# Advisory code review: issue #842

No findings. The diff is clean on both lenses: no correctness bugs introduced, and no reuse, simplification or efficiency cleanup worth making. There are no NEEDS-HUMAN items.

What this conclusion rests on:

- `template/src/pdca_harness/config.py:737` does not raise on any TOML value type. The check is against a tuple, so it compares with `==` and does not need a hashable value. I loaded array, boolean, inline table, date, empty string and embedded-newline values through the real `Config.load`. Each printed one stderr line and gave `"stack"`.
- `template/src/pdca_harness/config.py:738` uses `!r` (Python's quoted form of the value), which keeps a trailing space visible and keeps a multi-line value on one line. This differs from `merge_requires` at `config.py:745-749` for a good reason, because that value is already normalized and always a string.
- `template/src/pdca_harness/config.py:736-740` covers the only place the value is read from `pdca.toml`. The downstream checks in `flow.py`, `waves.py` and `publish.py` only compare with `"merge"`, and `cli.py:1099` only prints the value, so they all accept the fallback. The tests that set `wave_mode` on `Config` directly skip the loader and are not affected.
- `template/tests/test_config_wave_mode.py:54-58` tests the fix properly. `gate-logs/C4-verify.log` shows all five unknown values failing without the fix. Each `shown` string can only match the printed value, not the fixed text of the message, so the `assertIn(shown, err)` check is meaningful.
- `gate-logs/T3-suite.log` shows the suite passing (2699 tests, 2 skipped), so no existing test or fixture relied on an unknown value being kept.

One limit on this check: I did not re-run the suite. I relied on the gate logs for that, and ran only the odd-value load above myself.

<!-- pdca:leaf-complete -->
