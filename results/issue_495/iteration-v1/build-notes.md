# Build notes — issue 495 / copier-skip-tells-the-truth-and-is-never-silent

## What changed, and where (target branch: eduralph/pdca-harness @ main, HEAD `acb214a`)

- **New** `tests/_copier_probe.py` — the one shared probe. `probe_copier()` tries
  `from copier import run_copy, run_update` (injectable via `import_copier=`) and, on
  failure, calls `shutil.which("copier")` (injectable via `which=`) to report the
  proposition actually tested: "not importable in *this* interpreter" — naming the
  interpreter (`sys.executable`) and, if found, the `PATH` executable — rather than
  "not installed". `in_gate_context()` reads `$PDCA_BUNDLE` (the driver's own gate
  signal, cited in the brief at `gates.py:491` of the pdca-pdca instance).
  `classify(probe, gate=…)` returns `"run" | "skip" | "fail"`: available → run;
  unavailable + bare run → skip (honest, non-silent, matches today's behaviour
  otherwise); unavailable + gate run → fail, never skip. `unverifiable_message()`
  prefixes `"PDCA-UNVERIFIABLE: "` — the harness's own gate vocabulary the brief cites
  (`engine/README.md:44-68`), reused rather than invented.

- `tests/test_render_and_run.py:23-33,44-46` (was `:21-31` pre-patch) — replaced the
  `try: from copier import run_copy; HAVE_COPIER = True/except: False` probe and its
  `@unittest.skipUnless(HAVE_COPIER, "copier not installed")` with the shared probe;
  `@unittest.skipIf(_COPIER_VERDICT == "skip", _COPIER_PROBE.reason)`, and the test
  method now opens with `if _COPIER_VERDICT == "fail": self.fail(unverifiable_message(...))`.

- `tests/test_render_cli_name.py:44-64` (was `:44-52`) — identical shape of edit.

- `tests/test_update_compat.py:32-46,152,206,241,246-248` (was `:32-37`, `:232`) —
  identical probe/decorator swap, plus `setUpClass` now raises
  `AssertionError(unverifiable_message(...))` first when the verdict is `"fail"` (this
  class shares one `setUpClass` across 5 test methods, so the check lives there once
  rather than five times). One local rename was needed: the file already had an
  unrelated module-level `_PROBE` (the subprocess script text at old line 152) that
  collided with the new probe variable name — renamed to `_CONFIG_DUMP_SCRIPT`
  (`tests/test_update_compat.py:143` / new `_CONFIG_DUMP_SCRIPT` at line 152, used at
  line 206). No behavioural change to that script.

- **New test** `tests/test_copier_probe.py` — drives `probe_copier`, `in_gate_context`,
  `classify`, `unverifiable_message` directly with `import_copier=`/`which=`/dict
  `environ` all controlled (criterion iv), plus a source-level self-test that all three
  modules dropped the old literal `skipUnless(HAVE_COPIER, "copier not installed")` and
  reference `_copier_probe` (binds the invariant's "cannot be satisfied by fixing one
  module" note without importing copier or the three heavy modules).

## Why this shape, and what I ruled out

- **One shared probe module vs. three separate edits.** The brief calls the three sites
  "byte-identical in shape" and names unifying them as the composition. A trio of
  independent per-file reason-strings would (a) triple the surface for the reason to
  drift again and (b) make the "gate-context fail" decision three places to keep in
  sync instead of one. Cost of the alternative: same ~20-line reason/verdict block
  duplicated 3×, i.e. ~60 lines vs. the ~60-line shared module used 3× — no size win,
  strictly worse for drift, so I didn't consider it further.

- **`classify()` returning a 3-way string vs. two booleans.** I first tried
  `should_skip: bool` / `should_fail: bool` as two separate module-level values, but
  that lets `(True, True)` exist as a reachable-but-nonsensical state a future edit
  could produce silently. A single `"run"|"skip"|"fail"` enum-as-string makes the three
  outcomes mutually exclusive by construction; `classify()` is 6 lines and single-tested
  by `Classify` in the regression test.

- **Failing in `setUpClass`/first-test-line vs. failing at import time (module-level
  `raise`).** I considered raising at module import time when `_COPIER_VERDICT ==
  "fail"`, which would make the *whole module* fail to import under
  `python -m unittest discover` — collection-level failure, not a test failure. Rejected:
  that changes the "count of tests that ran" to zero for the module (`engine/README.md`'s
  own `0 tests ran → UNVERIFIABLE`, *never* the "this ran and failed" row), which is the
  wrong bucket — a wholesale skip becoming a wholesale collection failure is not "the run
  declares itself unverifiable/fails" in the sense the brief's gate-vocabulary citation
  means; it's a different failure mode with a different (and wrong) diagnosis attached.
  Failing inside `setUpClass`/the test body keeps the tests "ran" (reported as
  errors/failures, not zero), giving a correct non-zero exit **and** a correct positive
  test count.

- **Renaming the colliding `_PROBE` in `test_update_compat.py`.** First cut named the new
  shared-probe variable `_PROBE` (matching the module docstring's vocabulary), which
  silently shadowed the pre-existing `_PROBE = r"""...subprocess script..."""` — the
  clash produced `AttributeError: 'str' object has no attribute 'reason'` at collection,
  caught by actually running discovery (see red/green evidence below), not by inspection.
  Renamed the *new* symbol to `_COPIER_PROBE` everywhere and, since the old `_PROBE` name
  is genuinely a different thing (a subprocess script, not our dataclass), renamed that to
  `_CONFIG_DUMP_SCRIPT` for clarity rather than keep two same-named things in one module.

- **Out of scope, deliberately not touched:** rewriting the suites to drive the `copier`
  CLI as a subprocess (brief's explicit out-of-scope — a separate, much larger slice);
  `template/tests/`; `engine/scripts/run-suite.sh` and this instance's
  `[install].extra_bootstrap` (different repo per `docs/INTEGRATION.md` §2); making copier
  a hard dependency of the suite (that would flip a currently-optional-dev-dep gate).

## Gate posture (per brief's Falsifiability section — declared, not a gap)

The patch touches only `tests/*.py`. `engine/scripts/run-verify.sh:130-144` (in this
pdca-pdca instance, not the target) classifies any patch with zero non-`tests/*.py`
changed files as having "no behavioral production change to revert", and exits 77
`PDCA-UNVERIFIABLE` → SUMMARY §6 NEEDS-HUMAN, non-gating. That is the sanctioned route
for a test-only slice (issue #165 discipline, cited in the brief), and I did not invent a
production-file edit to dodge it, nor move the fix out of `tests/` — both explicitly
forbidden by the brief. The red→green evidence below is what the human adjudicates at
that §6 item.

## Red → green evidence (all runs from target root, this host)

**Pre-fix (fix reverted via `git stash` on the three modified test files, `_copier_probe.py`
and `test_copier_probe.py` kept):**
```
$ python3 -m unittest tests.test_copier_probe -v
...
FAILED (failures=3)
```
Three failures in `AllThreeModulesShareTheProbe.test_none_carry_the_old_bare_have_copier_probe`
(subTest per module) — the reverted modules still contain the literal string
`skipUnless(HAVE_COPIER, "copier not installed")` and don't reference `_copier_probe`.
Genuine RED: this is the production (test-module) source being read, not a stand-in.

**Post-fix, system `python3` (cannot import copier; `copier` 9.17.1 present on PATH at
`/home/eddie/.local/bin/copier`, this host's ambient posture per the brief's Repro):**
```
$ python3 -m unittest discover -s tests -v            # bare dev run
...
Ran 7 tests in 0.000s
OK (skipped=7)
```
— but skip reason is now e.g.
`"copier is not importable in this interpreter (/usr/bin/python3); a copier executable was
found on PATH at /home/eddie/.local/bin/copier — that is a pipx/venv-style install this
interpreter cannot see, not a missing copier. Run the suite with the interpreter copier is
installed into (e.g. .venv/bin/python3 in this project)."` — never claims "not installed".
```
$ PDCA_BUNDLE=/tmp/fakebundle python3 -m unittest discover -s tests; echo $?
...
FAILED (failures=2, errors=1)
1
```
Non-zero exit under the gate signal — the wholesale skip no longer reports as a pass.

**Post-fix, `.venv/bin/python3` (this pdca-pdca instance's venv, which has copier
importable — stands in for this repo's own `.venv`/CI posture per criterion iii):**
```
$ .venv/bin/python3 -m unittest discover -s tests -v      # bare
Ran 7 tests in 23.840s
OK
$ PDCA_BUNDLE=/tmp/fakebundle .venv/bin/python3 -m unittest discover -s tests -v   # gate
Ran 7 tests in 23.705s
OK
```
Same 7 tests, same result, in both gate and bare postures, when copier *is* importable —
no regression to the working case, no new dependency.

**New regression test, both discovery styles, importable-python irrelevant (fully
synthetic per criterion iv):**
```
$ python3 -m unittest discover -s tests -v   # (picks up test_copier_probe.py too)
...
Ran 18 tests in 0.001s
OK (skipped=7)
$ python3 -m unittest tests.test_copier_probe -v
...
Ran 11 tests in 0.000s
OK
```

Test runner used: the target repo's own documented offline-suite invocation,
`python3 -m unittest discover -s tests` from the target root (this is literally the
brief's Repro instruction and `AGENTS.md:26`'s sibling command for `template/`) — not a
hand-rolled runner. No container, no extra harness needed; this is plain `unittest`
against the target's own root.

## Self-refutation (forced questions)

**(a) Genuine red?** Yes — shown above: reverting the three modified test modules (while
keeping the new test + probe module, which is the whole patch here) makes
`tests.test_copier_probe` fail with 3 real failures, not an exception at collection and
not a vacuous pass.

**(b) Production path?** Yes — `test_copier_probe.py` imports and calls
`tests._copier_probe.probe_copier` / `classify` / `in_gate_context` / `unverifiable_message`
directly (the actual new production-side module, not a copy), and its
`AllThreeModulesShareTheProbe` test reads the actual `tests/test_render_and_run.py`,
`tests/test_update_compat.py`, `tests/test_render_cli_name.py` source files on disk — the
real files the fix edits, not fixtures standing in for them. Separately, the manual
red→green repro above ran the actual three suites (`test_render_and_run.py` etc.)
through `unittest discover`/`unittest tests.<name>`, i.e. the production test modules
themselves, in both the pipx-broken posture and the importable posture.

**(c) Fixture includes the fault?** Yes — the manual repro was run on *this host's own*
ambient pipx posture (system `python3` cannot import copier; `copier` 9.17.1 really is on
`PATH` at `/home/eddie/.local/bin/copier` with the documented pipx-style shebang), the
exact fault the brief names, not a healthy-only environment with that node excluded. The
regression test additionally drives the same fault synthetically (a `which=` stub
returning a fake path and an `import_copier=` stub that raises) so it doesn't depend on
this host's ambient state to stay deterministic on a different host.

## Formatter / commit hooks

No formatter/lint config was found scoped to the target repo's root `tests/` (checked:
no root `pyproject.toml`/`.flake8`/`ruff.toml`/`.pre-commit-config.yaml`; `template/`
has its own `pyproject.toml` but that governs the *rendered* package, not root tests).
`CONTRIBUTING.md:26` and `AGENTS.md:26` name only the offline-suite command, no
formatter step, for this class of file. Verified all 5 touched/added files compile
cleanly (`python3 -m py_compile`) and carry no trailing whitespace.
