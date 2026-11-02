# Build notes — issue 781 (diff-files-git-quoted-paths), iteration 2

Target: eduralph/pdca-harness @ main. Worktree `$PDCA_WORKTREE=/home/eddie/pdca/pdca-harness.pdca-wt-l1`,
detached at `3c11556` (= `origin/main`). All `path:line` below are in that worktree with the
patch applied. The brief cites `waves.py:329-350`; on this base the same code sat at
`waves.py:405-426` before the patch. The file grew after the brief's line numbers were taken. The
other citations still match: `flow.py:1586-1592`, `size_signal.py:406-407`,
`scripts/size-calibrate:344`, `tests/test_size_calibrate.py:339-343`.

## Carry-forward from iteration 1 — what was rejected and what changed

The rejection: leg (f) only checked `assertIsInstance(waves.diff_files(p), set)`. A helper that
returned a half-decoded path such as `x\q` would still have passed, even though the docstring
promises a malformed header is *skipped*.

Fixed in `test_waves_quoted_paths.py:187-209` (`test_malformed_quoted_header_is_skipped`). Each
of the 13 malformed lines now has two checks:
- `assertEqual(waves.diff_files(p), set())`. Skipped means no path at all.
- The same line followed by `diff --git a/ok.txt b/ok.txt` must give exactly `{"ok.txt"}`. Only
  the bad header is skipped, and parsing carries on after it.

Checked by mutation (I swapped `waves._unquote_c` for a careless version and ran the real test):
- a lenient decoder that keeps unknown or short escapes as written and accepts a missing closing
  quote: **caught**, 5 sub-case failures;
- a decoder that calls `int(…, 8)` on any backslash and so raises on `\q`: **caught**, 5
  sub-case errors;
- the real helper: passes.
The old `assertIsInstance` check would have passed the lenient decoder.

This test is green on `main` too, as the brief's Falsifiability line says for (f): on `main` the
regex can't match any of these lines.

## What changed in the source — `template/src/pdca_harness/waves.py`

- `:405` `_DIFF_GIT_RE` is unchanged. It still reads every header with no quoted side.
- `:406` `_DIFF_GIT`, the `"diff --git "` prefix.
- `:407-410` `_C_ESCAPES` and `_C_OCTAL`: the escapes Git's `quote.c` writes (`\a \b \t \n \v
  \f \r \" \\`), plus three-digit octal with a first digit of 0-3. That matches Git's own
  `unquote_c_style`, which only accepts `case '0'..'3'` as the first octal digit.
- `:413-439` `_unquote_c(s)` decodes one C-quoted string. It returns `(decoded, rest)`, or
  `None` for an unknown escape, a short octal (`\3`), an octal above one byte (`\477`), or no
  closing quote. Bytes are decoded as UTF-8 with `errors="replace"` (`:427`). That is the same
  handler the patch text is read with (`:493`), so the same file gets the same name whether Git
  quoted it or (`core.quotePath=false`) wrote the bytes raw.
- `:442-473` `_header_paths(line)`:
  - A quoted side is one that **starts the header, or follows the space between the sides**
    (`' "'`). A header with no quoted side goes to the old regex unchanged (`:455-457`).
  - With a quoted side, both sides must parse: valid quoting, the `a/` and `b/` prefixes, a
    non-empty path, and nothing after the second side. Otherwise the result is `[]` (`:471`).
  - A plain side next to a quoted one is taken exactly as written. It runs up to the `' "'`
    separator, or to the end of the line.
- `:476-498` `diff_files`: the docstring (`:477-489`) now covers quoted sides, the U+FFFD
  choice, the skip-on-malformed choice, and "patch content never makes this raise". The loop
  (`:493-497`) calls `_header_paths` for lines that start with `diff --git `.

Choices for leg (f), as the docstring states them:
- a **malformed** quoted header is **skipped**;
- octal bytes that are **not valid UTF-8** are **decoded with U+FFFD**, not skipped. The header
  is well-formed: Git writes `"a/x\377y.txt"` for a file named `b"x\xffy.txt"` (seen with git
  2.53). Skipping it would drop a real file from `patch_files` and from the overlap check, which
  is the same bug this issue fixes.

### Other source changes since iteration 1 (not asked for; listed so they are visible)

1. **Which `"` opens a quoted side.** Iteration 1 treated *any* `"` as an opener (Git's own
   `apply.c` reading). That changed `main`'s result for a hand-written plain header with a raw
   quote inside a name: `diff --git a/say"hi".txt b/say"hi".txt` gives `{'say"hi".txt'}` on
   `main` and gave `set()` in iteration 1. Brief leg (d) says unquoted headers behave as today,
   so the opener is now `' "'` or a leading `"`. Git never writes this header (it always quotes
   a `"`), so real patches are not affected either way. Pinned by
   `test_quote_inside_a_plain_name_reads_as_before` (`test:157-161`), which is green on both.
   It added no code: the `' "'` check replaced iteration 1's `rest[q - 1] != " "` check.
2. **Empty paths rejected** (`:471`), to match the regex's `(.+)`. In iteration 1,
   `diff --git "a/x" b/` returned `['x', '']`, so a malformed header still gave the path `x`.
   Now it gives `[]`. The `"a/" "b/"` case is one of the (f) sub-cases.
3. **Plain side not stripped.** Iteration 1 stripped the new side of a mixed header but not the
   old side. Both are now taken as written. For Git's output that is exact: Git does not quote
   spaces, so a name with a trailing space appears raw.

## Test — `template/tests/test_waves_quoted_paths.py` (new, 13 tests, unittest)

Real `git` in a `tempfile.TemporaryDirectory` (`setUp`, `:60-63`). `GIT_CONFIG_GLOBAL=/dev/null`,
`GIT_CONFIG_NOSYSTEM=1`, and a fixed identity (`:26-30`). Any inherited `GIT_*` variable is
dropped (`:33-38`), so a `GIT_DIR` set by a hook can't point these commands at the outer repo.
`_diff` pins `-c core.quotePath=true` and writes git's stdout **byte for byte** (`:52-56`). Every
real-git test also asserts the exact quoted header bytes are in the patch before it calls the
parser, so the fixture can't quietly stop quoting.

| Leg | Test | main | patched |
|---|---|---|---|
| a | `test_non_ascii_path` (`:80`) | red | green |
| b | `test_quote_backslash_tab_newline_paths` (`:89`): `"`, `\`, tab, newline, all real git | red | green |
| b+ | `test_rest_of_git_escape_table` (`:102`): `\a \b \v \f \r`, `\001`, `\177`, real git | red | green |
| c | `test_rename_plain_to_quoted` (`:116`), `test_rename_quoted_to_plain` (`:123`): real `git mv` + `diff --cached -M` | red | green |
| c+ | `test_rename_with_spaces_next_to_a_quoted_side` (`:130`): the "fix it only if free" space case, which is free for quoted and mixed headers | red | green |
| d | `test_plain_modify_add_delete` (`:144`): real git, asserts `--- /dev/null` / `+++ /dev/null` and no `"` | green | green |
| d | `test_quote_inside_a_plain_name_reads_as_before` (`:157`) | green | green |
| d | `test_missing_file_is_empty` (`:163`) | green | green |
| e | `test_overlap_audit_flags_shared_quoted_path` (`:167`): two bundle dirs whose real-git patches each edit `café.txt`, `flow._audit_wave_overlap` called directly with stderr captured, as `test_flow_slice.py:1188-1202` does | red | green |
| e | `test_overlap_audit_keeps_names_apart_that_differ_in_escaped_bytes` (`:175`): `café` vs `cafè`. A lossy decode would merge them into a false overlap. It also asserts each patch decodes, so it can't pass empty. | red | green |
| f | `test_malformed_quoted_header_is_skipped` (`:187`): 13 malformed lines, each `== set()`, and the next header still reads | green | green |
| f | `test_octal_bytes_not_valid_utf8_decode_with_replacement` (`:211`): real git, file `b"x\xffy.txt"`; skips itself only if the filesystem refuses a non-UTF-8 name | red | green |

One departure from the brief's Falsifiability line ("(d) and (f) are green on both"): the
invalid-UTF-8 test is **red on main**. With the U+FFFD choice, which the brief allows, there is
no way around this. On `main` the header is skipped, so the file is missing, which is the
defect. The "never raises" half of (f) is green on both, as the brief says.

The (e) fixture holds only the quoted path. The overlap can only be found by decoding it.

## Runs

The project's runners are `pdca.toml:1377`, the C4 gate `./engine/scripts/run-verify.sh`, and
`:1386`, the T3 gate `./engine/scripts/run-suite.sh`. Both were run from the instance root with
`PDCA_BUNDLE` / `PDCA_WORKTREE` set and wrapped in `timeout`.

- **C4 (`run-verify.sh`)**, exit 0, `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`.
  - Green leg: `Ran 13 tests … OK`, no skips.
  - Red leg (production hunk reverted by the script): `Ran 13 tests … FAILED (failures=9)`. The
    9 are a, b, b+, c ×2, c+, e ×2, and invalid-UTF-8. The 4 green on both are d ×3 and f.
  - After the run, the worktree diff matched `patch.diff` byte for byte (checked with `cmp`).
- **T3 (`run-suite.sh`)**, exit 0: `PDCA-EVIDENCE: root suite OK, driver suite OK`.
  - Root suite: `Ran 50 tests in 189.543s — OK`. That includes `test_render_then_slice`, which
    renders the template and runs the rendered project's whole suite (the new test with it) in
    the stripped environment, plus `test_update_compat`, which ran rather than skipped.
  - Driver suite: `Ran 2660 tests in 178.607s — OK (skipped=2)`.
  - I added the 13th malformed line while this run was going, so the run may have used the
    12-line version. I then re-ran the four directly affected modules on the final tree
    (`test_waves_quoted_paths`, `test_waves`, `test_size_calibrate`, `test_flow_slice`):
    `Ran 198 tests — OK`. That includes `test_size_calibrate.py:339-343` and the existing
    overlap-audit tests at `test_flow_slice.py:1188-1213`.
- Extra checks:
  - The new module with `-W error::ResourceWarning`: OK.
  - The new module under `env -i PYTHONPATH=src PATH=/usr/bin:/bin`, the stripped environment
    `tests/test_render_and_run.py:79` uses for the rendered project: OK.
- **Fuzz** (my own check, not shipped):
  - 200,000 random `diff --git` lines over `" \ a b / space 0 3 4 7 8 q n t x é U+FFFD tab`:
    no exception, and every line with no quoted side gave exactly the old regex's result.
  - 100,000 random byte-string names quoted with a re-implementation of Git's `quote_c_style`
    (quotePath on): all 96,156 headers with a quoted side decoded back to the right names, 6,518
    of them mixed.

## Refute-your-own-test

- **(a) Genuine red? Yes.** `run-verify.sh` itself ran `git apply -R` on the production hunk
  and the module went `FAILED (failures=9)`. It went back to `OK` with the patch applied. The
  red is spread across legs a, b, c and e, not a single brittle assertion. The two careless
  decoders above show leg (f)'s test now binds its own claim too.
- **(b) Production path? Yes.** The tests import `pdca_harness.flow` and `pdca_harness.waves`
  and call the real `waves.diff_files` and `flow._audit_wave_overlap`. There is no copy of the
  parser and no mock. The mutation check replaced the helper *only* to prove the test catches a
  bad one, and that is not shipped.
- **(c) Fixture includes the fault? Yes.** Every patch for a, b, c, e and the invalid-UTF-8 case
  is real `git diff` output with quoting forced on, written byte for byte. Each test asserts the
  quoted header bytes are present before calling the parser. In (e) both bundles hold only the
  quoted path. Hand-written lines are used only where git *cannot* produce the input: the 13
  malformed headers in (f), and the raw-quote plain header in (d).

## Ruled out

- **Falling back to the old regex whenever the quoted parse fails.** About 2 lines, and it
  would keep `main`'s output for every non-Git line. Rejected because of what it returns, not
  its size. A malformed *mixed* header can leak raw text through the regex:
  `diff --git a/x "b/x\q b/y"` gives `['x "b/x\q', 'y"']` (checked by running it). The
  shipped parser gives `[]`. That raw text is exactly the half-decoded path the carry-forward
  asked leg (f) to forbid.
- **`codecs.decode(…, "unicode_escape")` / `ast.literal_eval`.** These are Python escapes, not
  Git's. Octal becomes code points, not bytes: `\303\251` decodes to `Ã©`, not `é`. They also
  accept `\x`, `\u` and `\N{}`, and raise on bad input, which (f) forbids.
- **`surrogateescape` for non-UTF-8 bytes.** It keeps the exact bytes, but the patch text is
  read with `errors="replace"` (`:493`). The same file would then get two different names
  depending on `core.quotePath`. Replacement keeps them equal.
- **Out of scope, left alone:**
  - `splitlines()` (`:493`) also breaks lines at U+0085, U+2028 and U+2029, which Git writes
    raw under `core.quotePath=false`. With quoting on they are octal-escaped, so this is not a
    quoted-header problem.
  - `diff.mnemonicPrefix` / `--no-prefix` headers: dropped today, still dropped, because the
    same `a/` / `b/` requirement applies.
  - The space ambiguity in fully plain headers: still read by the old regex.

## Commit-readiness

The target has no formatter, linter or pre-commit setup:
- no `.pre-commit-config.yaml`;
- `core.hooksPath` is unset;
- `/home/eddie/pdca/pdca-harness/.git/hooks/` holds only `*.sample` files;
- there is no ruff/black/flake8 config, and no workflow lints Python.

Both files compile with `python3 -W error` and have no trailing whitespace. New lines are at
most 95 columns in `waves.py` (the file's existing maximum is 97) and at most 99 in the test
(`test_waves.py` goes to 100). Commits need a DCO sign-off and a conventional prefix
(`AGENTS.md:33-35`); that is the publisher's step.

## Housekeeping

Scratch output lives only in the worktree's git-ignored `.cache/` (`t3-suite.log`). As in
iteration 1, `results/issue_781/fix-only.tmp.diff` is left over from that attempt. Cleanup is
the harness's job, so I did not delete anything.
