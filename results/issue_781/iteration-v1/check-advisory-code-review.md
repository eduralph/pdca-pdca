# Advisory code review — issue_781 (diff-files-git-quoted-paths)

Advisory only. Gates: C4 passes (red before the fix, green after); T3 suite passes.

## Correctness

I found no correctness bugs in the patch. I probed `_header_paths` by hand against the
patched `template/src/pdca_harness/waves.py:443-471`:

- Plain headers still go through the old regex and behave as before.
- Quoted sides, mixed renames in both orders, an unquoted old path with a space next to a
  quoted new path, and a trailing `\r` all decode correctly.
- Bad input returns `[]` and never raises. That covers a short octal, `\400`, an unknown
  escape, no closing quote, a lone `"`, a double space between sides, and a tab separator.
- The escape table at `waves.py:409` matches Git's `quote.c`.
- Octal bytes are collected into a `bytearray` and decoded as UTF-8 once at the closing
  quote. That is right for multi-byte names.

## Findings

- NEEDS-HUMAN [impl] — `template/tests/test_waves_quoted_paths.py:130`: leg (f) only checks
  `assertIsInstance(..., set)`. The docstring at `template/src/pdca_harness/waves.py:481-482`
  promises that a malformed quoted header is *skipped*, but the test never checks that.
  Each malformed line in the test resolves to `[]` today, so `assertEqual(waves.diff_files(p),
  set())` would pin the stated behaviour. Without it, a change that returns a half-decoded
  path, such as `"a/x\\q"`, would still pass.
- `template/src/pdca_harness/waves.py:450`: small cleanup. The unquoted branch adds
  `_DIFF_GIT_PREFIX` back onto `rest` just so `_DIFF_GIT_RE` can match it. A
  prefix-free regex (`r"a/(.+) b/(.+)$"`) would avoid building the string twice. Also, the
  unquoted old side in the mixed case (`waves.py:460`) is not `.strip()`ped, while the regex
  branch strips both sides. That is harmless today because Git never writes trailing
  whitespace before the separator. Not blocking.
- NEEDS-HUMAN [human] — Reuse and a follow-up scope question. Two other copies of the old
  plain regex keep the same quoted-path bug and do not use the new helper:
  - `template/src/pdca_harness/registry.py:23` (`touched_paths`). This feeds the
    `registry-check` *gate* (`registry.py:78`, `template/src/pdca_harness/cli.py:477`). A
    patch that edits `café.txt` gets no touched path for that file, so a registry line
    naming it could be flagged wrongly.
  - `template/scripts/checks/test_exercises_production.py:27`. This misses a new test file
    whose name Git quotes.

  The brief scopes the fix to `waves.py`, so this is not a defect in the patch. A human
  should decide whether to file a follow-up that has these callers share
  `waves._header_paths`, or a public version of it.

<!-- pdca:leaf-complete -->
