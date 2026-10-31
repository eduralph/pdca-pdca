## Summary
**User impact:** When a bundle's patch edits a file whose name contains a non-ASCII character (for example `café.txt`), a double quote, a backslash or a tab, the harness treats the patch as touching no file at all. Two bundles scheduled in the same wave that both edit such a file get no "undeclared conflict" warning, and the bundle's changed-file count (used by the size backstop, the wave scheduler and `size-calibrate`) comes out too low. A rename where only one side has such a name loses both names.

This PR teaches the patch-header reader to decode the quoted form Git uses for those names, so every file a patch touches is counted.

Reported in [#781](https://github.com/eduralph/pdca-harness/issues/781).

## What to look at
Git writes a path with non-ASCII bytes (under its default `core.quotePath=true`), a `"`, a `\` or a control character in C-quoted form: `diff --git "a/caf\303\251.txt" "b/caf\303\251.txt"`. The reader only knew the plain `diff --git a/x b/x` form. The change adds a small decoder for the quoted form and leaves the plain form on its existing path.

To reproduce on `main`:

```sh
git init t && cd t && echo x > café.txt && git add . && git commit -qm i
echo y > café.txt && git -c core.quotePath=true diff > p.diff
cd ../template && PYTHONPATH=src python3 -c \
  "from pathlib import Path; from pdca_harness import waves; print(waves.diff_files(Path('../t/p.diff')))"
```

`main` prints `set()`; with this PR it prints `{'café.txt'}`.

Two other copies of the same plain regex exist (`template/src/pdca_harness/registry.py:23`, `template/scripts/checks/test_exercises_production.py:27`) and have the same gap. They are not part of this issue and are left for a follow-up.

## Root cause
`waves.diff_files` matched every header against `^diff --git a/(.+) b/(.+)$` (`template/src/pdca_harness/waves.py:405`, used at `:421`). A quoted side starts with `"a/`, not `a/`, so the regex fails and the header is skipped. A mixed rename header (`a/plain.txt "b/caf\303\251.txt"`) fails for the same reason, dropping both names. The two readers of that set, `flow._audit_wave_overlap` (`template/src/pdca_harness/flow.py:1592`) and `size_signal.measure` (`template/src/pdca_harness/size_signal.py:406`; also `template/scripts/size-calibrate:344`), had no way to tell "no files" from "files it could not read".

## Fix
In `template/src/pdca_harness/waves.py`:

- `_unquote_c(s)` decodes one C-quoted string as Git's `quote.c` writes it: the one-letter escapes `\a \b \t \n \v \f \r \" \\` and three-digit octal byte escapes (first digit 0–3, matching Git's own `unquote_c_style`). Bytes are decoded as UTF-8 with `errors="replace"`, the same handler the patch text is read with, so a file gets the same name whether Git quoted it or wrote the bytes raw. Returns `None` on an unknown escape, a short or over-byte octal, or no closing quote.
- `_header_paths(line)` returns the two paths of one header. A header with no quoted side goes through the unchanged regex. With a quoted side, both sides must parse (valid quoting, `a/`/`b/` prefixes, non-empty paths, nothing after the second side), or the header yields `[]`. A plain side next to a quoted one is taken as written.
- `diff_files` calls `_header_paths` for every `diff --git ` line. Its docstring now states the two choices: a malformed quoted header is skipped, and octal bytes that are not valid UTF-8 decode with U+FFFD rather than dropping the file. Patch content never makes it raise, which matters because `_audit_wave_overlap` has no exception guard.

A quoted side is recognised only when it opens the header or follows the `' "'` separator between the sides. A hand-written plain header with a raw `"` inside a name (`a/say"hi".txt b/say"hi".txt`) therefore reads exactly as before. Git never writes that header, so real patches are unaffected either way.

## Verification
- **Claim (a):** a real-git patch editing `café.txt` yields `{"café.txt"}`.
  **Checked:** `template/src/pdca_harness/waves.py:405,421` on `main` — the regex requires a literal `a/` after `diff --git `, so the quoted header never matches.
  **Test:** `template/tests/test_waves_quoted_paths.py` `test_non_ascii_path` — red on `main`, green with the fix. The test asserts the exact quoted header bytes are in the patch before parsing it.
- **Claim (b):** names holding `"`, `\`, tab and newline, plus the rest of Git's escape table (`\a \b \v \f \r`, `\001`, `\177`), each come back decoded.
  **Test:** `test_quote_backslash_tab_newline_paths`, `test_rest_of_git_escape_table` — red → green, real git output.
- **Claim (c):** a rename between a quoted and an unquoted name returns both names, including names with spaces next to a quoted side.
  **Test:** `test_rename_plain_to_quoted`, `test_rename_quoted_to_plain`, `test_rename_with_spaces_next_to_a_quoted_side` — red → green, built with `git mv` and `git diff --cached -M`.
- **Claim (d):** unquoted headers, `/dev/null` sides and a missing file behave as before.
  **Checked:** the no-quote branch of `_header_paths` runs the same regex and `.strip()` as `main`'s loop at `waves.py:421-425`.
  **Test:** `test_plain_modify_add_delete`, `test_quote_inside_a_plain_name_reads_as_before`, `test_missing_file_is_empty` — green on both. Existing `template/tests/test_waves.py` and `template/tests/test_size_calibrate.py` (incl. `test_diff_files_are_counted`, `:339-343`) stay green.
- **Claim (e):** the overlap audit reports two bundles whose patches both edit `café.txt`, and does not merge names that differ only in escaped bytes (`café` vs `cafè`).
  **Checked:** `template/src/pdca_harness/flow.py:1586-1600` on `main` — the audit intersects the sets from `diff_files`, so an empty set hides the overlap.
  **Test:** `test_overlap_audit_flags_shared_quoted_path`, `test_overlap_audit_keeps_names_apart_that_differ_in_escaped_bytes` — red → green; `flow._audit_wave_overlap` is called directly with stderr captured, as `template/tests/test_flow_slice.py:1188-1202` does.
- **Claim (f):** a malformed quoted header never raises and is skipped, and parsing continues at the next header; well-formed octal that is not valid UTF-8 decodes with U+FFFD.
  **Checked:** `flow.py:1592` has no `try` around the call; `size_signal.py:407` guards only `OSError`/`UnicodeDecodeError`/`ValueError`.
  **Test:** `test_malformed_quoted_header_is_skipped` — 13 malformed lines, each `== set()` and each followed by a plain header that still reads as `{"ok.txt"}`; green on both (`main` skips them via the regex). Swapping in a lenient decoder (keeps unknown escapes, accepts a missing closing quote) or a careless one (`int(…, 8)` on any backslash) fails this test. `test_octal_bytes_not_valid_utf8_decode_with_replacement` — real git, file `b"x\xffy.txt"`; red on `main` (the file is dropped), green with the fix.
- **Suite:** `cd template && PYTHONPATH=src python3 -m unittest discover -s tests` — 2660 tests OK (2 pre-existing skips); root suite (template render + `copier update` compat) 50 tests OK. Docs lint and site render/link audit clean.

Fixes #781
