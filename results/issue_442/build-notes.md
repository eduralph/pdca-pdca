# Build notes — issue 442 / gates-doc-stale-one-marker-claim

Target: eduralph/pdca-harness @ main (`0fbfa26`), built in `$PDCA_WORKTREE`
(`/home/eddie/pdca/pdca-harness.pdca-wt-l1`).

## The change

One false sentence, corrected in place. The evidence-marker paragraph of the
`gates.py` module doc claimed ``PDCA-UNVERIFIABLE`` "stays the one marker that
can change a ``result``" (`template/src/pdca_harness/gates.py:38` pre-fix) —
false since #401 introduced ``PDCA-DEFERRED`` twenty lines below in the same
docstring (the deferred paragraph at `gates.py:52-63` pre-fix / `gates.py:53-64`
post-fix; `DEFERRED_MARKER` constant at `gates.py:98` pre-fix / `gates.py:99`
post-fix), a second marker that changes a `result` (to `deferred`).

Replaced with the brief's suggested wording:

> …the exit code alone decides pass/fail, and only the ``PDCA-UNVERIFIABLE``/
> ``PDCA-DEFERRED`` declarations can change a ``result``.

(`template/src/pdca_harness/gates.py:38-39` post-fix — the sentence rewraps to
two lines to stay inside the file's prose width.) Nothing else in the docstring
touched; no behavioral change; the size_signal.py stale comment explicitly out
of scope per the brief.

## The test

Appended to the #401 suite the brief names,
`template/tests/test_gate_deferred.py` (new class
`ModuleDocNamesEveryResultChangingMarker`, `template/tests/test_gate_deferred.py:281-305`):

- `test_the_exclusivity_claim_is_gone` — `"the one marker"` absent from
  `gates.__doc__`;
- `test_the_result_changing_claim_names_both_declarations` — the corrected
  claim ("only the ``PDCA-UNVERIFIABLE``/``PDCA-DEFERRED`` declarations can
  change a ``result``") present in `gates.__doc__`.

Design choices, in the suite's own house style:

- Assertions run over `" ".join(gates.__doc__.split())` so they span the
  docstring's hard-wrap points instead of pinning the current line layout — the
  wrap of the fixed sentence across lines 38-39 must not be what the test pins.
- The marker *names* in the expected claim are composed from the production
  constants (`gates.UNVERIFIABLE_MARKER` / the module's existing `_D =
  getattr(gates, "DEFERRED_MARKER", …)` alias, `test_gate_deferred.py:49,56`)
  with the trailing colon stripped — no second spelling in the test that can
  drift from the constants, matching the suite's existing #428 discipline
  (never emit a marker at a declaring position in captured output; the composed
  names are colon-free and the normalized doc is one line, so no line in the
  test's output ever *starts* with a marker).

## Alternatives ruled out

- **Standalone doc-test file** (e.g. `template/tests/test_gates_doc.py`): the
  brief explicitly says append to the #401 suite, and the brief's rationale
  holds — an appended module is what the instance's C4 script selects and
  re-runs (`run-verify.sh` maps each changed `template/tests/*.py` to a module,
  `engine/scripts/run-verify.sh:57-62`), so the test earns its red under the
  shipped C4 contract with zero new files. No cost argument needed; the brief
  decides it.
- **Rewording the surrounding paragraph** (e.g. reconciling "the exit code
  alone decides pass/fail" with the marker family): out of scope per the
  brief's Scope line ("any rewording of the rest of the docstring" excluded).
  The one-sentence fix restores the brief's invariant (a normative exclusivity
  claim must match the set it describes) with the smallest change that does so.

## Red→green evidence (project runner)

Runner: the target's own documented invocation for the offline driver suite —
`cd template && PYTHONPATH=src python3 -m unittest …` (the module docstring's
own run line, `test_gate_deferred.py:31`, and the identical per-module command
the C4 gate uses, `engine/scripts/run-verify.sh:60`), with the instance venv's
python.

- **Green leg** (full patch applied): `tests.test_gate_deferred` → `Ran 19
  tests … OK` (17 pre-existing + 2 new).
- **Red leg** (production hunks reverted exactly as C4 does: `git apply -R
  --exclude='tests/*' --exclude='template/tests/*' patch.diff`, per
  `run-verify.sh:72-75`): → `Ran 19 tests … FAILED (failures=2)` — precisely
  the two new doc tests, everything else green. Patch re-applied cleanly after.
- **Whole offline driver suite** (green leg): `Ran 1565 tests … OK (skipped=2)`
  — no regression elsewhere.

## Self-refutation record (forced questions)

- **(a) Genuine red?** Yes — actually reverted the production hunk with the C4
  script's own exclude-reverse-apply and re-ran: `FAILED (failures=2)`, both
  failures the new assertions, failure message showing the stale "stays the one
  marker" doc. Restored, re-ran: `OK`.
- **(b) Production path?** Yes — the test imports the production module
  (`from pdca_harness import … gates`, `test_gate_deferred.py:46`) and asserts
  over `gates.__doc__`, the live docstring of the shipped module — no copy, no
  fixture text.
- **(c) Fixture includes the fault?** Yes — the "fixture" *is* the production
  docstring itself; the fault (the stale exclusivity sentence) is exactly what
  the reverted-production red leg restores and what the assertions bind on.

## Commit-readiness

The target repo has no pre-commit config, formatter, or lint config
(no `.pre-commit-config.yaml`, no ruff/black/flake8 sections in
`template/pyproject.toml.jinja`, none at the root). Kept house style manually:
prose wrapped within the file's existing width (`gates.py`'s longest existing
line is 106 chars; the new lines are shorter), test code matches the suite's
existing conventions (stdlib unittest, constant-composed markers, docstringed
classes). Both changed files compile (`python -m unittest` imports them) and
the full suite is green.

## External dependencies

None needed, none missing (matches the brief's `External dependencies: none`).
No NEEDS-HUMAN items.
