# Advisory code review — issue #495 (truthful-copier-skip-and-no-silent-green)

Scope: correctness bugs the patch introduces, and reuse/simplification/efficiency. Gate
adequacy and fix-scope judgment are the `reviewer` leaf's job, not this one.

## Findings

- NEEDS-HUMAN [impl] — `tests/test_update_compat.py:245-247` leaks a `tempfile.mkdtemp()`
  directory on the exact posture this bundle exists to exercise (copier on `PATH`, not
  importable by the running interpreter). Pre-patch, `UpdateCompat` carried
  `@unittest.skipUnless(HAVE_COPIER, "copier not installed")` at class scope, so on that
  posture `setUpClass` never ran and `cls.tmp = Path(tempfile.mkdtemp())` (line 245) was
  never reached. The patch removes that decorator (criterion ii — decide at point of use)
  and moves the copier check into `render_prior_edit_and_update` (`:210`, `copier =
  import_copier()`), called from `setUpClass` at `:247` — but `:245` still creates `cls.tmp`
  *before* `:247` is even entered, i.e. before the copier check the whole class now depends
  on. When `import_copier()` raises `unittest.SkipTest` (the unimportable posture), the
  exception propagates out of `setUpClass`; per `unittest.suite.TestSuite._handleClassSetUp`,
  a `SkipTest` there sets `_classSetupFailed = True` the same as any other exception, and
  `_tearDownPreviousClass` (`unittest/suite.py`) checks exactly that flag and skips calling
  `tearDownClass` — so the `shutil.rmtree(cls.tmp, ...)` at `:250-252` never runs and the
  directory from `:245` is orphaned. Verified directly against this interpreter's
  `unittest.suite` (reproduced with a 20-line standalone script: a `setUpClass` that
  `mkdtemp()`s then raises `SkipTest` leaves the directory on disk after
  `TestSuite.run()`). Every `python3 -m unittest discover -s tests` (or
  `tests.run_root_suite`) invocation on the documented pipx posture — the posture this brief
  reproduces as the normal, sanctioned install — now leaks one temp directory. Contrast with
  the two sibling call sites this patch also touches, `tests/test_render_and_run.py:37-38`
  and `tests/test_render_cli_name.py:57-58`, which both call `import_copier()` *before*
  `tempfile.mkdtemp()` — the ordering `UpdateCompat` was presumably meant to mirror but
  doesn't, because its `mkdtemp()` call sits in `setUpClass` one frame up from where
  `import_copier()` actually executes. Fix is local and small: call `import_copier()` (or
  hoist the check) before `cls.tmp = Path(tempfile.mkdtemp())`, e.g. as the first statement
  of `setUpClass`, or wrap `:245-247` in a `try`/`except unittest.SkipTest` that removes
  `cls.tmp` before re-raising. Not caught by the added regression suite:
  `NoVerdictBeforeATestBodyRuns.test_modules_import_and_collect_with_copier_unimportable`
  only checks `__unittest_skip__` without running `setUpClass`, and
  `BareDeveloperRunIsUnchanged`'s two cases *do* run it (via `run_suites`/
  `suites_under_pipx_posture`) but assert only pass/fail/skip-reason, never that no
  temp directory was left behind — so this leak fires quietly during the bundle's own T3
  gate run too (twice per invocation), just below anything that gate checks.

## Not flagged

- `tests/run_root_suite.py:classify()` — the `testsRun` vs. per-test-skip vs.
  setUpClass-skip accounting (`ran_and_skipped` filtered by `isinstance(c,
  unittest.TestCase)`) was checked against `unittest.suite`'s actual behavior (confirmed:
  a `setUpClass`-raised `SkipTest` is recorded via a non-`TestCase` `_ErrorHolder` and does
  **not** increment `testsRun`, while a per-test skip does) — the arithmetic is correct for
  both shapes exercised by this repo's three suites.
- The `try: from copier_support import X / except ImportError: from tests.copier_support
  import X` shape is repeated in five files rather than centralized. This looks like
  duplication but isn't a good target for a shared helper: the whole point is import-shape
  ambiguity itself (`tests/` on `sys.path` vs. `tests.<mod>` from the root), so any helper
  that resolved it would need the same dual try/except before it could be imported — the
  brief's own "two invocation shapes, both mandatory" note (composition cues) explains why
  this is inherent rather than needless.
- `run_root_suite.py`'s `-m unittest`-vs-bad-module-name behavior: an unknown module name
  passed to `loadTestsFromNames` surfaces as a `unittest`-internal `_FailedTest` error
  (`wasSuccessful() == False` → exit 1, the FAILED path), not the "no test was selected at
  all" 77 branch whose message says "wrong module name or start directory?" — that message
  in fact only fires for `discover()` finding nothing, or a module that imports cleanly but
  defines no `TestCase` (`rrs_empty`, exercised by
  `test_a_selection_with_nothing_in_it_is_unverifiable_too`). Mildly imprecise wording, not
  a functional defect, and out of this diff's stated scope (three sites converging + the
  no-evidence exit) — noting only for completeness, not filing.
