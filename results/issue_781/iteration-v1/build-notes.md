# Build notes — issue 781 (diff-files-git-quoted-paths)

Target: eduralph/pdca-harness @ main (worktree base `3c11556`). Line numbers below are
in the patched worktree (`$PDCA_WORKTREE=/home/eddie/pdca/pdca-harness.pdca-wt-l2`).
The brief cited `waves.py:329-350`; on this base the same code sat at `waves.py:405-426`
(the file has grown since the brief's line numbers were taken). Same code, new lines.

## What changed

`template/src/pdca_harness/waves.py`

- `:405` `_DIFF_GIT_RE` is kept unchanged and is still used for headers that hold no
  `"` at all, so unquoted behaviour is byte-for-byte what it was (leg d).
- `:406` `_DIFF_GIT_PREFIX`, `:408` `_C_ESCAPES` — the escape table Git's `quote.c`
  writes (`\a \b \t \n \v \f \r \" \\`) plus three-digit octal.
- `:411-440` `_unquote_c` — decodes one C-quoted string; returns `None` on a bad escape,
  a short/out-of-range octal (`\3`, `\477`), or no closing quote. Bytes are decoded as
  UTF-8 with `errors="replace"` (`:424`), so invalid UTF-8 gives U+FFFD and never raises.
- `:443-471` `_header_paths` — splits a header into old/new sides, each plain or quoted,
  mixed allowed. It uses one fact about Git: an unquoted path never contains `"`
  (Git quotes such a name), so the first `"` in an unquoted header must start the
  quoted second side. Both sides must carry the `a/` and `b/` prefixes. If anything is
  malformed it returns `[]`, so the line is skipped.
- `:474-495` `diff_files` — the docstring now covers quoted paths, the replacement choice
  and the skip-on-malformed choice (the brief's leg f asks for this to be stated). The loop
  calls `_header_paths` (`:491`).

Choice for leg (f), as stated in the docstring: a malformed quoted header is **skipped**.
Octal bytes that are not valid UTF-8 are **decoded with replacement**, not skipped. That
way the file still counts toward `patch_files` and still shows up for the overlap check.

## Test — `template/tests/test_waves_quoted_paths.py` (new, 10 tests, unittest style)

Real `git` in a `TemporaryDirectory`, with `GIT_CONFIG_GLOBAL=/dev/null`,
`GIT_CONFIG_NOSYSTEM=1` and `-c core.quotePath=true`. That pins quoting on, so a host
with `quotePath=false` cannot make leg (a) pass on main. Each real-git test also asserts
that the quoted form is actually in the patch, so the fixture can't quietly stop quoting.

| Leg | Test |
|---|---|
| a | `test_non_ascii_path_from_real_git` |
| b | `test_quote_backslash_tab_paths_from_real_git` (real git), `test_newline_escape_decodes` (hand-written header: a newline in a filename made by git is awkward to create portably) |
| c | `test_mixed_rename_returns_both_names` (real `git mv` + `diff --cached -M`, asserts the `a/plain.txt "b/caf\303\251.txt"` header), `test_mixed_header_quoted_first` |
| d | `test_unquoted_header_unchanged`, `test_missing_file_is_empty`, and the existing `test_waves.py` / `test_size_calibrate.py` / `test_flow_slice.py` (green) |
| e | `test_overlap_audit_flags_shared_quoted_path` — two bundle dirs whose real-git patches each edit `café.txt`, `flow._audit_wave_overlap` called directly with stderr captured, the same way `test_flow_slice.py:1188-1202` drives it |
| f | `test_malformed_quoted_headers_never_raise` (9 subtests: `\3`, `\q`, unterminated first side, unterminated second side, `\477`, a trailing backslash that eats the quote, no separator, trailing junk, wrong prefix) and `test_invalid_utf8_octal_decodes_with_replacement` |

## Runs (target's documented runner, `cd template && PYTHONPATH=src python3 -m unittest`, wrapped in `timeout`)

`pdca.toml` in this instance has no active `[[gates.checks]]` rows and no wrapper
script, so I used the command from the target's `CONTRIBUTING.md:26` / `AGENTS.md:37`,
wrapped in `timeout`.

- Pre-fix: `FAILED (failures=7)`. Failing: a, b, both c tests, the newline test, e, and the
  invalid-UTF-8 test. That last one is red on main because main skips the line; it pins
  my replacement choice. The malformed-never-raise test and the two (d) tests are green
  on both, as the brief expects.
- Post-fix: `Ran 10 tests ... OK`.
- Full offline suite post-fix: `Ran 2657 tests in 196.128s — OK (skipped=2)`.

## Refute-your-own-test

- **(a) Genuine red?** Yes. I saved the source half of the diff, ran
  `git checkout -- template/src/pdca_harness/waves.py`, and the new test went
  `FAILED (failures=7)`. After `git apply` it went back to `OK`.
- **(b) Production path?** Yes. The tests call the real `waves.diff_files` and the real
  `flow._audit_wave_overlap`, imported from `pdca_harness`. There is no mock and no copy
  of the parser.
- **(c) Fixture includes the fault?** Yes. The patches come from real `git diff` with
  quoting forced on, and the test asserts the quoted header (`"a/caf\303\251.txt"`) is in
  the file before it calls the parser. In the (e) fixture, both bundles' patches hold only
  the quoted path, so the overlap can only be found by decoding it.

## Ruled out

- **Swapping the regex for one that also accepts quotes, then decoding afterwards.** The
  mixed case gets ambiguous fast. A hand scan of about 30 lines (`_header_paths`) is
  easier to read and easier to make never raise.
- **`codecs.decode(..., "unicode_escape")` / `ast.literal_eval`.** Python escapes are not
  Git's. `unicode_escape` takes `\x..`, `\u....` and `\N{}` and treats octal as code
  points, not bytes, so `\303\251` would become `Ã©` and not `é`. It also raises on bad
  input, which leg (f) forbids.
- **Fixing the unquoted-path-with-a-space ambiguity.** Out of scope per the brief, and the
  quoted parser does not fix it for free (unquoted headers still go through the old regex).

## Commit-readiness

The target has no pre-commit config and no formatter or linter, either in `.github/workflows`
or in `template/pyproject.toml`. I followed the file's own style instead: no line in the
new code or the test is over 100 columns, while `flow.py` already has lines up to 106.

## Housekeeping

Two scratch files ended up outside the three artifacts. I did not delete either, because
cleanup belongs to the harness.
- `results/issue_781/fix-only.tmp.diff` holds the source-only half of `patch.diff`. I used
  it to revert and re-apply the fix for the red check.
- `/tmp/x` holds a stray `git diff` redirect that I wrote by mistake while checking line
  lengths. It is a copy of the diff and nothing reads it.
