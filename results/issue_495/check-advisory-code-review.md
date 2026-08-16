# Advisory code review — issue #495 (iteration 2)

Second lens: correctness bugs the patch introduces, and reuse/simplification/efficiency.
Grounded on target source at `$PDCA_TARGET`; cross-checked against `patch.diff` and the
frozen `gate-logs/`.

## Carry-forward defect from iteration 1 — verified fixed

The prior rejection (temp-dir leak in `UpdateCompat.setUpClass` on the pipx posture) is
resolved correctly: `import_copier()` (`tests/test_update_compat.py:251`) now runs before
`cls.tmp = Path(tempfile.mkdtemp())` (`:252`), matching the ordering already used at
`tests/test_render_and_run.py:37-38` and `tests/test_render_cli_name.py:57-58`. Traced the
`unittest.suite` mechanics by hand (`_classSetupFailed` short-circuits `tearDownClass` when
`setUpClass` raises `SkipTest`) and confirmed empirically that a class-level `setUpClass`
skip contributes 0 to `testsRun` and is recorded against a `unittest.suite._ErrorHolder`
(not a `TestCase` instance) — exactly what `tests/run_root_suite.py:190` filters on via
`isinstance(c, unittest.TestCase)`. No leak remains on this path.

The requested regression coverage for the leak was also added:
`tests/test_copier_availability.py:475-500`
(`test_a_skipped_run_leaves_no_temp_directory_behind`) allocates a real sandbox via
`tempfile.tempdir` patching, runs the three suites under the injected pipx posture, and
asserts the sandbox is empty afterward — plus asserts `UpdateCompat` actually reached
`setUpClass` (`:494-496`), so an empty sandbox can't pass by accident (the run never getting
that far). This is a real regression test, not a re-statement of the fix.

## `tests/run_root_suite.py` classify() — verified correct on the two invocation shapes

Manually reproduced `unittest`'s accounting for both a method-body `SkipTest` (counts in
`testsRun`, listed against the `TestCase` instance) and a `setUpClass`-raised `SkipTest`
(does not count in `testsRun`, listed against an `_ErrorHolder`) to confirm
`classify()`'s `executed = max(result.testsRun - len(ran_and_skipped), 0)`
(`tests/run_root_suite.py:190-191`) is not off-by-one on either shape, and that mixing a
passing regression case with a copier-skip in the same selection still routes to
`UNVERIFIABLE_RC` rather than being masked by the unrelated pass (`:201-208`), matching
criterion (iii)'s "no copier-dependent case executed" wording. Also verified by hand that
raising inside a meta-path `find_spec` (the test double at
`tests/test_copier_availability.py:314-320`) does propagate as `ModuleNotFoundError` out of
`import copier`, so the injected posture is a faithful stand-in for the real pipx failure
mode, not just a plausible-looking mock.

## No new findings

No correctness bugs introduced by this patch, and no reuse/duplication/efficiency issue
worth raising. The repeated `try: from copier_support import X / except ImportError: from
tests.copier_support import X` shape across five files (`tests/test_render_and_run.py:27-30`,
`tests/test_render_cli_name.py:48-51`, `tests/test_update_compat.py:32-35`,
`tests/test_copier_availability.py:297-301`, `tests/run_root_suite.py:158-161`) looks at
first glance like something to factor out, but it can't be: it exists precisely because the
two mandatory invocation shapes (`discover -s tests` vs. `-m unittest tests.<mod>`) put
different things on `sys.path`, so a shared helper would just relocate the same
try/except into one more file every caller still has to import under both shapes — no net
simplification. (Also already litigated in the brief's carry-forward note and correctly
left alone.)

The double `import_copier()` call per `UpdateCompat` run (once hoisted in `setUpClass`
at `tests/test_update_compat.py:251`, once inside `render_prior_edit_and_update` at `:207`)
is redundant work but not a bug: the second call only re-executes a `sys.modules` lookup
once copier is already imported, and the code says so at `:803-806`. Not worth a finding.

If the diff is clean on both lenses — it is.
