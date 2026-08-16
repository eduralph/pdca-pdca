# Check — advisory code review (issue #495)

Second lens: correctness bugs the patch introduces, and reuse/simplification/efficiency.
Grounded on `$PDCA_TARGET` (target/); adequacy of the fix itself is the `reviewer` leaf's job.

## Verification performed

Live-reproduced both postures against the patched target with the system interpreter
(`/usr/bin/python3`, copier not importable, `copier` on `PATH` at
`/home/eddie/.local/bin/copier` — this host's actual pipx posture):

- Bare dev run (`python3 -m unittest discover -s tests`): `OK (skipped=7)`, with the truthful
  per-case reason naming the interpreter and the found executable (`tests/test_render_and_run.py:40`,
  `tests/test_render_cli_name.py:60`, `tests/test_update_compat.py:241` — the `skipIf` sites).
- Gate run (`PDCA_BUNDLE=/tmp/fake python3 -m unittest discover -s tests`): exit 1,
  `FAILED (failures=2, errors=1)` — `RenderAndRun`/`RenderCliName` each fail their single test via
  `self.fail(unverifiable_message(...))` (`tests/test_render_and_run.py:43-44`,
  `tests/test_render_cli_name.py:63-64`); `UpdateCompat.setUpClass` raises `AssertionError`
  (`tests/test_update_compat.py:247-248`), which unittest reports as one class-level `ERROR`
  covering all 5 of its test methods (hence "Ran 13 tests" not 18 — standard unittest
  `setUpClass`-failure accounting, not a bug in this patch).

Both match brief criteria (i)–(iii) exactly as specified; no correctness bug found in the
gate-vs-dev-run branching, the `PDCA_BUNDLE`-empty-string edge case, or the probe's
dependency-injection seams.

## Findings

No correctness bugs introduced by this patch. Two minor, non-blocking reuse/simplification
observations, neither worth routing back:

- `tests/test_render_and_run.py:37`, `tests/test_render_cli_name.py:57`,
  `tests/test_update_compat.py:46` — each module still computes
  `HAVE_COPIER = _COPIER_VERDICT == "run"`, but nothing in any of the three modules reads
  `HAVE_COPIER` any more (the `skipIf`/`fail` branches now key off `_COPIER_VERDICT` directly).
  It's dead code left over from the pre-patch convention; grepping the rest of the tree
  (`template/`, `docs/`) turns up no external reader of `<module>.HAVE_COPIER` either. Harmless,
  but removable.
- `tests/test_render_and_run.py:25-28`, `tests/test_render_cli_name.py:45-48`,
  `tests/test_update_compat.py:34-37` each still do their own top-level
  `try: from copier import run_copy [, run_update] / except Exception: ... = None` to bind the
  symbol the test body calls, independently of `_copier_probe._default_import_copier`
  (`tests/_copier_probe.py:26-27`), which imports the same names again to decide availability.
  Two independent "is copier importable" attempts per module, evaluated at collection time.
  Harmless — `sys.modules` caching makes the second import free, and both attempts import the
  identical name set today — but it is duplicated logic an existing helper (the probe) already
  performs; if the probe's import list ever diverges from the module-level one (e.g. a future
  module needs a name the probe doesn't try) the two could disagree about availability. Not
  worth blocking on for a 3-module test-only slice.

Everything else — the shared-probe composition across the three call sites, the
gate/dev-run classification, the dependency-injection seams the regression test drives, and the
self-test guarding against a partial per-module fix (`tests/test_copier_probe.py:243-254`) — is
sound and matches the brief's success criteria and falsifiability demonstration.
