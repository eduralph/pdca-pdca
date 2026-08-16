# Build notes — issue 495 / truthful-copier-skip-and-no-silent-green (iteration 3)

Target: `eduralph/pdca-harness` @ `main`, base `acb214a`. All edits in `$PDCA_WORKTREE`
(`/home/eddie/pdca/pdca-harness.pdca-wt-l1`); every `path:line` below is on the patched tree
unless it says "on the base".

## 1. What this iteration changed, and why only this

The sign-off rejected iteration 2 on one verified defect and explicitly said to keep the rest:

> `tests/test_update_compat.py:245-247` leaks a `tempfile.mkdtemp()` directory on exactly the
> pipx posture this slice exists to serve … Hoist the copier check above the temp-dir creation …
> Close the coverage gap that let it through … Keep as-is — do not re-do this part.

So iteration 3 = iteration 2's patch + exactly the two things it asked for + the two comments
that would otherwise have gone stale. The whole delta against `iteration-v2/patch.diff`:

| Where (patched tree) | Change | Lines |
|---|---|---|
| `tests/test_update_compat.py:248-252` | hoist `import_copier()` (:251) above `cls.tmp = Path(tempfile.mkdtemp())` (:252), with the reason | +5 |
| `tests/test_copier_availability.py:216-241` | new case `test_a_skipped_run_leaves_no_temp_directory_behind` | +26 |
| `tests/test_copier_availability.py:264-277` | same discipline in this module's own `setUpClass`: `mkdtemp` moved below the `assert` that can raise | +2/-1 |
| `tests/test_update_compat.py:208-212` | comment at `render_prior_edit_and_update` refreshed — it claimed *this* call was what skipped the class | +5/-2 |
| `tests/copier_support.py:11-15` | module docstring now states the ordering rule (reach copier above whatever the use allocates) and why | +5/-3 |

Nothing else moved: `git diff` between this patch and `iteration-v2/patch.diff` is confined to
those five places.

### The defect, mechanically

`unittest/suite.py::_handleClassSetUp` catches anything out of `setUpClass`, sets
`currentClass._classSetupFailed = True`, and `_tearDownPreviousClass` returns early on that
flag — so `tearDownClass` never runs. `SkipTest` is an ordinary `Exception`, so a skip raised
*from inside* `setUpClass` takes that path too. Iteration 2 removed the class-level
`@unittest.skipUnless` (right, criterion ii) but left the copier check downstream of the
allocation: base `:242` `mkdtemp()` → `:244` `render_prior_edit_and_update` → `import_copier()`
→ `SkipTest` → no `tearDownClass` → one `/tmp/tmpXXXX` per invocation, forever, on the pipx
posture.

The fix is ordering, not cleanup: `tests/test_update_compat.py:251` settles the precondition,
`:252` allocates. That is the order the two sibling call sites in this same patch already use —
`tests/test_render_and_run.py:37-38` and `tests/test_render_cli_name.py:57-58` — so all three
copier-dependent suites now read the same way, which is the point of the slice (one answer, not
three edits).

### Rejected alternatives, with their actual cost

1. **`try/except SkipTest` around `:252-254` that `rmtree`s `cls.tmp` before re-raising** — the
   sign-off's own second option. +5 lines and it *keeps* the wrong order, so it removes the
   directory instead of never creating it, and the next person adding a second precondition
   below `mkdtemp` gets no signal. Rejected as symptom-guarding where the cause (one statement
   in the wrong place) is a 1-line move.
2. **Replace `tearDownClass` with `cls.addClassCleanup(shutil.rmtree, cls.tmp, ignore_errors=True)`**
   (`:255-258` deleted, one line added at `:253` — net **-5/+1**). This is genuinely more than a
   wash: `doClassCleanups()` *is* called on the setUpClass-failure path, so it would also close
   the *pre-existing* leak when `run_copy`/`run_update` raise a real error mid-`setUpClass`
   (identical on the base: `:242` allocate, `:244` raise, no teardown). I still rejected it here:
   that error path is unchanged from the base — this slice neither introduced nor is judged on
   it — and swapping the teardown mechanism edits a path the brief's `Scope` does not name while
   the invariant at stake ("a skip states the condition that stopped it; a run with no evidence
   is not success") is restored by the hoist alone. It is a two-line hygiene issue worth its own
   issue; I did not smuggle it in under this one.
3. **Make the leak assertion "`mkdtemp` was never called"** (spy on `tempfile.mkdtemp`, +8 lines,
   about the same size). Rejected as under-specified in the other direction: it pins *the
   mechanism* rather than the outcome, so it would go red on a future fixture that legitimately
   creates and removes a directory, and stay green on a leak produced by `TemporaryDirectory`,
   `mkstemp`, or a stray `os.mkdir`. The shipped case points `tempfile.tempdir` at a sandbox it
   owns and asserts the sandbox is **empty afterwards** — outcome, any mechanism.

## 2. Why the rest of iteration 2 stands (kept deliberately, re-verified here)

- `tests/copier_support.py:61` `import_copier()` — the import happens at the point of use and
  raises `unittest.SkipTest(unimportable_reason(exc))`; `:39-58` builds the reason from the real
  exception, `sys.executable`, and `shutil.which("copier")`. Live on this host it prints:
  `copier is not importable by this interpreter (/usr/bin/python3): ModuleNotFoundError: No
  module named 'copier'; a `copier` executable IS on PATH at /home/eddie/.local/bin/copier — …`
  (criterion i). Mirrors the repo's own voice at base `tests/test_update_compat.py:237-241`.
- `tests/run_root_suite.py:52` `classify()` / `:98` `main()` — the third answer at the process
  boundary, in the repo's own vocabulary (`:44-45` mirror
  `template/src/pdca_harness/gates.py:83-86`, asserted structurally by
  `tests/test_copier_availability.py:385`). Both consumer constraints are honoured: the marker is
  printed only at the start of a line (#428) and only on the 77 path, never on the failure path
  (#329 — `template/src/pdca_harness/gates.py:758-774` ignores it on a failing exit, which is what
  sank iteration 1's `self.fail()` design).
- `.github/workflows/render-check.yml:36-46` and `CONTRIBUTING.md:27-34` — the two in-repo
  consumers, same module selection, `fetch-depth: 0` untouched at `render-check.yml:27`.
- No `$PDCA_BUNDLE`/env switch anywhere (iteration 1's rejected approach): criterion (iv) is
  asserted at `tests/test_copier_availability.py:243`.

## 3. Evidence — red → green (all commands run from the worktree root)

**RED, whole slice vs. the base.** Fix stashed, `tests/test_copier_availability.py` kept:

```
$ /usr/bin/python3 -m unittest tests.test_copier_availability
ImportError: cannot import name 'copier_support' from 'tests' (unknown location)
Ran 1 test … FAILED (errors=1)                                    exit=1
$ /usr/bin/python3 -m unittest discover -s tests
Ran 8 tests … FAILED (errors=1, skipped=7)                        exit=1
```

**RED, the base defect verbatim** (test file stashed too — clean `acb214a`):

```
$ /usr/bin/python3 -m unittest discover -s tests -v
… skipped 'copier not installed'   (×7)
Ran 7 tests in 0.000s / OK (skipped=7)                            exit=0
$ /usr/bin/python3 -m tests.run_root_suite
/usr/bin/python3: No module named tests.run_root_suite            exit=1
```

**RED, this iteration's specific defect** — the new case against iteration 2's code, through the
configured T3 gate (`./engine/scripts/run-suite.sh`):

```
FAIL: test_a_skipped_run_leaves_no_temp_directory_behind
AssertionError: Lists differ: ['tmprn579h2k'] != []
 … left a temp directory behind — a fixture was allocated before the precondition was checked
Ran 24 tests in 23.995s / FAILED (failures=1)
PDCA-EVIDENCE: root suite FAILED (rc 1), driver suite OK
```

**GREEN, importable-copier posture** (criterion v), same runner, after the hoist:

```
$ PDCA_WORKTREE=… ./engine/scripts/run-suite.sh
== T3: template-repo suite (render + update-compat)   Ran 24 tests in 24.078s  OK
== T3: offline driver suite (template/tests …)        Ran 1758 tests in 47.966s  OK (skipped=2)
PDCA-EVIDENCE: root suite OK, driver suite OK
```

24 = the 7 original render/update cases (all executed for real) + 17 regression cases. The 7
assert exactly what they asserted on the base.

**GREEN, pipx posture** (`copier 9.17.1` on PATH via `/home/eddie/.local/share/copier-venv`;
`/usr/bin/python3` cannot import it):

```
$ /usr/bin/python3 -m unittest discover -s tests        Ran 19 tests  OK (skipped=3)   exit=0
                                                        /tmp entries before=29913 after=29913
$ /usr/bin/python3 -m tests.run_root_suite              exactly 1 line starting PDCA-UNVERIFIABLE:
                                                                                      exit=77
$ /usr/bin/python3 -m tests.run_root_suite tests.test_render_and_run   PDCA-UNVERIFIABLE: …  exit=77
$ /usr/bin/python3 -m tests.run_root_suite tests.test_update_compat    PDCA-UNVERIFIABLE: …  exit=77
$ .venv/bin/python3 -m tests.run_root_suite   root suite OK: 24 executed, 0 skipped  exit=0
```

The `/tmp` count is the live proof of the fix on the real posture, not only the injected one.

**Both mandatory invocation shapes** (brief, `Test file`): `discover -s tests` (bare sibling
imports) and `-m unittest tests.<name>` from the repo root (namespace-package imports) — the
regression module passes under both, on both interpreters:
`/usr/bin/python3 -m unittest tests.test_copier_availability` → `Ran 17 tests … OK`.

**Other gates, run here:** T2 `./engine/scripts/run-docs-check.sh` → `docs lint clean, site
render + link audit clean`. C4 `./engine/scripts/run-verify.sh` → `PDCA-UNVERIFIABLE: no
behavioral production change to revert (test-only or docs-only patch)`, exit 77 — exactly the
posture the brief declared (`Falsifiability`): every touched path is `tests/*.py`, `.github/*`
or `*.md`, so `PROD` is empty at `engine/scripts/run-verify.sh:130-143`. Non-gating → §6
NEEDS-HUMAN; the human adjudicates the two RED/GREEN command pairs above.

## 4. Forced refutation of my own test

- **(a) Genuine red?** Yes, twice over, actually reverted and re-run — not reasoned about.
  Against the base (fix stashed, test kept) the module errors out: `ImportError: cannot import
  name 'copier_support'`, exit 1. Against **iteration 2's code** (the only thing this iteration
  changes) the new case fails with `Lists differ: ['tmprn579h2k'] != []`. Restoring the stash was
  verified byte-exact: the regenerated diff compared equal to `patch.diff`.
- **(b) Production path?** Yes. The cases import the three shipped suites themselves
  (`tests/test_copier_availability.py:86-99` `importlib.import_module` + `reload` of
  `tests.test_render_and_run` / `…_cli_name` / `…_update_compat`) and **run** them
  (`:108-113` `loadTestsFromModule` + `suite.run`), so `UpdateCompat.setUpClass` — the production
  statement that leaked — actually executes. The truthful-reason cases call the shipped
  `copier_support.import_copier()`; the classification cases call the shipped
  `run_root_suite.main()` / `.classify()`. Nothing is re-implemented in the test; the only
  stand-ins are the *postures* (a meta-path finder that fails `import copier`, a `shutil.which`
  answer, a `prior_release_ref` answer), which is criterion (vi)'s explicit requirement so the
  result cannot depend on what the host has installed. Confirmed by the module passing
  identically under `/usr/bin/python3` (no copier) and `.venv/bin/python3` (copier 9.17.0).
- **(c) Fixture includes the fault?** Yes. `test_a_skipped_run_leaves_no_temp_directory_behind`
  (`:216`) runs all three suites under the pipx posture and asserts, *before* looking at the
  sandbox, that a skip was recorded against `UpdateCompat` (`:235-237`) — i.e. that `setUpClass`
  was actually reached — so an empty sandbox cannot pass by never getting there. The sandbox is
  `tempfile.tempdir` for the duration, so the leaking allocation lands *inside* what the case
  inspects rather than being curated out; that is precisely why it went red on iteration 2's
  code and green after the hoist.

## 5. Commit-readiness

The target has no formatter, linter or lint CI for Python and no committed git hooks (`.git`
carries only `*.sample`; no `pyproject.toml` / `ruff.toml` / `.pre-commit-config.yaml` at the
root — checked). De-facto style is stdlib-only, 4-space, ≤ ~100 cols: the new files peak at 98
(`run_root_suite.py`), 96 (`test_copier_availability.py`), 94 (`copier_support.py`) against 92-94
in the base `tests/*.py` and 106 in `template/src/pdca_harness/gates.py`. All six touched Python
files byte-compile under both `/usr/bin/python3` (3.14.4) and the instance venv. Markdown/CI
changes pass the target's own checkers via the T2 gate. `tests/` gains no `__init__.py`; the two
new modules are not `test*.py`, so `unittest discover` does not collect them as suites, and both
are importable under both invocation shapes (verified above).

Not touched, per the brief: this instance's `engine/scripts/run-suite.sh` (the residual T3
opt-in), `template/tests/`, the `copier importable (.venv)` doctor row.

**External dependencies:** none missing. The pipx red posture and the `.venv` green posture were
both available on this host; nothing was stubbed, aliased or read-instead-of-run. No NEEDS-HUMAN
external dependency to declare.
