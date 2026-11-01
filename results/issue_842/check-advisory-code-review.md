# Advisory code review: issue 842, wave_mode refusal

No correctness bugs found in the patch. There are no NEEDS-HUMAN items. The one finding below is an optional cleanup.

- Simplification (optional): `template/src/pdca_harness/config.py:739` — the `isinstance(wave_mode, str)` test changes nothing, because membership in a tuple compares with `==` and never hashes. I ran `['merge'] in ("stack", "merge")`, and the same check on a dict, an int, a bool and a date. All return `False` with no `TypeError`, so `if wave_mode not in ("stack", "merge"):` refuses the same values. The comment at `config.py:737` ("The type comes first so that every TOML value is refused the same way") implies the type test is needed. The `TypeError` risk only applies to a set, which the patch does not use. The brief asks for the type test explicitly, so keeping it conforms to the brief and does no harm. The type test would only matter if someone later changed the tuple to a set.

## What was checked and found clean

- Message stays on one line: `!r` escapes any newline in a TOML string, so `template/src/pdca_harness/cli.py:452-454` still prints a single line.
- Callers: `cli.py:448` and `template/scripts/size-calibrate:599-601` both catch `ValueError`. `template/.claude/hooks/handoff_guard.py:45` does not, and the brief rules it out of scope.
- Existing configs in the repo: every `wave_mode` line in a TOML template or test uses `stack` or `merge`. The other tests set the attribute directly on a `Config`, which skips the new check. The full driver suite passes (`gate-logs/T3-suite.log`: 2700 tests, OK, 2 skipped).
- Tests: `template/tests/test_config_wave_mode.py` goes through the real loader and the real CLI, and restores the working directory before the temp directory is removed. The C4 log shows the tests fail without the fix and pass with it. I re-ran the new test file on the target and all 3 tests passed.

<!-- pdca:leaf-complete -->
