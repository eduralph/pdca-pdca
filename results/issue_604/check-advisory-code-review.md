# Advisory code review — issue 604 (signoff-delta-cannot-forge-section6)

The patch is clean on both lenses. I found no correctness bugs and no NEEDS-HUMAN items. The notes below are minor and optional.

## Correctness

- `template/src/pdca_harness/signoff.py:296`: the fix is in the right place. `set_field` flattens `value` before the callable `repl` closes over it. So `Outcome`, `By / date` (`f"{by} / {date}"`) and `Iteration delta` all go through one rule, and the #529 callable-`repl` handling of backslashes is unchanged. A value with no line break is not touched.
- `template/src/pdca_harness/signoff.py:41`: the character class matches exactly the 10 characters `str.splitlines` splits on. I checked this by running the same enumeration the test uses, which returns 10. `\r\n` is a run, so it becomes one space. The `+` keeps runs together, and other whitespace (tabs, double spaces) is kept as-is, as the brief asks.
- The tests do exercise the fix. The CLI legs (`template/tests/test_signoff_verbatim.py:237`, `:258`, `:263`) go through `cli._signoff` on a bundle at `cfg.bundle(id)`. The positive control (`:268`) shows the retire step really runs on this fixture. `gate-logs/C4-verify.log` shows these tests fail without the fix and pass with it. The `:263` leg (a trailing break in `--by`) is a good extra case: without the fix it is the one that actually retires E1.

## Reuse / simplification / efficiency (optional, non-blocking)

- `template/tests/test_signoff_verbatim.py:280`: scanning all 0x110000 code points takes about 0.13 s per run. That's acceptable, and deriving the set from `splitlines` (rather than hard-coding it) keeps the test honest if Python's set ever changes. No change needed.
- `template/tests/test_signoff_verbatim.py:284`, `:294`: each subtest calls the existing `_bundle()` helper (`:63`). That helper makes a `tempfile.mkdtemp()` directory and never removes it, so this test leaves about 13 temp directories behind per run. Older tests in the file already use the same helper. An `addCleanup(shutil.rmtree, d, True)` would fix it if wanted. Cosmetic only.
- `template/tests/test_signoff_verbatim.py:211`: the method is named `_signoff_then_advance`, but it never calls `driver.advance`, because `cli._signoff` already drives the transition. The docstring explains this, so it isn't misleading, but a name like `_signoff_via_cli` would match what the method does.

No NEEDS-HUMAN findings.

<!-- pdca:leaf-complete -->
