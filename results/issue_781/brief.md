- **Slug:** diff-files-git-quoted-paths
- **Kind:** bug
- **Defect / goal:** `waves.diff_files` (`template/src/pdca_harness/waves.py:332`) parses
  `diff --git` headers with `_DIFF_GIT_RE = r"^diff --git a/(.+) b/(.+)$"` (:329). Git
  quotes a path that holds non-ASCII bytes, a double quote, a backslash or a control
  character (`core.quotePath`): `diff --git "a/caf\303\251.txt" "b/caf\303\251.txt"`. The
  regex does not match that line, so the path is missing from the result. A mixed header
  (one side quoted, e.g. a rename `diff --git a/plain.txt "b/caf\303\251.txt"`, checked
  with real git) does not match either, so BOTH paths are dropped — there is no
  stray-quote baseline to assert. Callers on `main`: the advisory `_audit_wave_overlap`
  (`template/src/pdca_harness/flow.py:1586-1592`, no exception guard), which then misses
  an overlap between two same-wave bundles that both edit such a file; and the size
  backstop's `patch_files` count, `template/src/pdca_harness/size_signal.py:406` (wrapped
  in `except (OSError, UnicodeDecodeError, ValueError)` at :407; its docstring at :390-392
  says the backstop and scheduler must agree on this count) and
  `template/scripts/size-calibrate:344`. The fix raises `patch_files` for a patch that
  touches a quoted path — intended: the count becomes correct. Goal:
  `diff_files` returns the real repo-relative path for quoted headers, decoding Git's
  C-style escapes (octal byte escapes as UTF-8, `\"`, `\\`, `\t`, `\n`).
- **Success criterion:**
  - (a) A real-git patch (made with `git -c core.quotePath=true diff` in a temp repo —
    pinned, so a machine with `core.quotePath=false` in its global config cannot make
    this leg green on `main`) that edits `café.txt` → `diff_files` returns `{"café.txt"}`.
  - (b) Paths with a double quote, a backslash and a tab in the name each come back
    decoded.
  - (c) A rename between a quoted and an unquoted name returns both names.
  - (d) Unquoted headers, `/dev/null` sides and a missing file behave as today (existing
    `template/tests/test_waves.py` stays green, and so does
    `template/tests/test_size_calibrate.py`, e.g. `test_diff_files_are_counted` at
    :339-343).
  - (e) `_audit_wave_overlap` reports an overlap for two bundles whose patches both edit
    `café.txt` (drive it as the existing overlap-audit tests do). Red on `main`.
  - (f) A malformed quoted header never raises: a bad escape (e.g. a lone `\3`, `\q`),
    an unterminated quote, and octal bytes that are not valid UTF-8 each return without
    an exception (the path is skipped or decoded with replacement — Do's choice, stated in
    the docstring). `_audit_wave_overlap` has no guard, so a raise here would turn an
    advisory miss into a flow crash. Green on `main` (the regex just skips the line);
    guards against a careless helper.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Reproduction:** `git init t && cd t && echo x > café.txt && git add . && git commit -m i
  && echo y > café.txt && git diff > p.diff`, then
  `python -c "from pathlib import Path; from pdca_harness import waves; print(waves.diff_files(Path('p.diff')))"`
  → `set()`.
- **Falsifiability:** RED on `main` at (a), (b), (c) and (e); (d) and (f) are green on
  both.
- **Invariant to restore:** `diff_files` returns the paths a patch touches, for every path
  Git can write in a header. Source: its own docstring (waves.py:333-340).
- **Scope (one logical fix) / out of scope:** the header parser in `waves.py` (regex and/or
  a small unquote helper) and its docstring. / Out of scope: making the audit a hard gate;
  what the audit does with an unparsable patch beyond today's behaviour; the ambiguous
  unquoted-path-with-a-space case the docstring already admits (fix it only if the quoted
  parser handles it for free); the #395 same-wave trial (a sibling child, which no longer
  reads `diff_files`).
- **External dependencies:** none
- **Test file:** `template/tests/test_waves_quoted_paths.py` (new). Import modules only
  (`from pdca_harness import flow, waves`), `unittest` style like
  `template/tests/test_waves.py` (no pytest fixtures). Build patches with real `git` in a
  `tempfile.TemporaryDirectory`; no network. For (e), call `flow._audit_wave_overlap` on two
  bundle directories and capture stderr.
- **Citations expected:** Do cites path:line on the target branch for every change.
- **Difficulty:** low
- **Disposition hint:** likely-fix
- **Prior-art check:** found as the sign-off finding on #395's iteration 8, preserved in the
  cumulative brief archived with iteration 9: `results/issue_395/iteration-v9/brief.md:126-127`
  (header "Iteration 8 — carry-forward", item 1 "Quoted diff paths (C5): waves.diff_files
  (waves.py:329) cannot parse Git-quoted headers"). No earlier fix on `main`
  (`waves.py:329-350` still has the plain regex).
Plan-review response: all five findings addressed. Provenance confirmed (Prior-art check).
The size_signal / size-calibrate callers are now listed, with test_size_calibrate kept
green. New leg (f) requires that a malformed header never raises. The mixed-header framing
is corrected (checked with real git). Leg (a) pins `core.quotePath=true`.

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: Auto-iterate (round 1): rebuilding for the implementation-level findings — `template/tests/test_waves_quoted_paths.py:130`: leg (f) only checks `assertIsInstance(..., set)`. The docstring at `template/src/pdca_harness/waves.py:481-482` promises that a malformed quoted header is *skipped*, but the test never checks that. Each malformed line in the test resolves to `[]` today, so `assertEqual(waves.diff_files(p), set())` would pin the stated behaviour. Without it, a change that returns a half-decoded path, such as `"a/x\\q"`, would still pass.. Deferred, not addressed here: 7 finding(s) that need human judgment, held in deferred-findings.json for the human at handover — not build work
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
