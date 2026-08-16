# Check — advisory code review (correctness + reuse/simplification), issue #507

Scope: `template/tests/test_families.py`, `template/tests/test_verify_base.py`,
`template/tests/test_verify_red_leg.py` (the only files this patch touches). Verified by
reading the patched target source and by actually running the suites (not just trusting
the frozen gate log):

- `cd template && PYTHONPATH=src python3 -m unittest tests.test_families
  tests.test_verify_red_leg tests.test_verify_base` → `Ran 71 tests … OK` (matches the
  brief's Success criterion command verbatim).
- Independently ran `tests.test_families` alone (35 tests, OK) and hand-simulated posture
  (v) (`ShippedPdcaTomlExamplePostures.test_two_active_headers_still_fails`) to confirm the
  *only* failure produced is `test_leaves_sandbox_is_declared_at_most_once_active` (not a
  loosely-worded test that happens to pass alongside unrelated breakage) —
  `template/tests/test_families.py:479-491`.
- Manually round-tripped the real `pdca.toml.jinja` commented block through
  `_sandbox_commented_block`/`_sandbox_example_parses`
  (`template/tests/test_families.py:340-354`) against `template/pdca.toml.jinja:833-835`;
  it parses to `{'unsandboxed_commands': [...], 'network_access': True}` as asserted.

## Correctness

No bugs found. Specifically checked and cleared:

- **Regex scoping** (`template/tests/test_families.py:337`): `^\[leaves\.sandbox\]\s*$`
  (no leading `#?`) matches only *active* headers, never the commented example — verified
  against the real `# [leaves.sandbox]` line at `template/pdca.toml.jinja:833`.
- **Posture-override plumbing**: `SOURCE_TEXT`/`SOURCE_RENDERED`
  (`test_families.py:375-376`), `SKELETON_TEXT`/`RENDERED`
  (`test_verify_base.py:88-89`, `test_verify_red_leg.py:84-85`) are class attributes read
  only by the one method/class each is scoped to; every other test method in
  `VerifyBaseExport` and every other class ignores them, confirmed by re-running the full
  71-test suite and by the per-class docstrings stating the scope explicitly.
- **`case.RENDERED = rendered` / `case.SOURCE_RENDERED = rendered`** rebinding on a
  per-instance basis before `suite.run()`/`case.run()` (`test_families.py:449-450`,
  `test_verify_base.py:349-350`, `test_verify_red_leg.py:191-192`) — no shared mutable
  state leaks between posture cases; each `_run()` builds a fresh `TestCase` instance per
  method name.
- **`class Foo: RENDERED: bool = RENDERED`** (module global read into a same-named class
  attribute, `test_verify_base.py:89`, `test_verify_red_leg.py:85`) — standard Python
  class-body scoping, RHS resolves to the module global at class-definition time; no
  NameError, confirmed by running.
- **`self.skipTest(...); raise AssertionError("unreachable")`**
  (`test_families.py:390-391`) — `skipTest` raises `unittest.SkipTest`, so the following
  line is genuinely dead code, but it is intentional (keeps the function's return type
  total for a type checker) and pre-existing style carried over from the code it replaces
  (old `return self.skipTest(...)` at the same site). Not a defect.
- **No new subprocess/tempdir/fork use** — the fork-storm constraint the brief calls out
  is honored throughout: every posture is built as in-memory synthetic text and driven via
  `unittest.TestSuite`/`TestCase.run(TestResult())` in-process, never `discover -s tests`.
  No resource leaks (temp dirs, sockets) introduced.

## Reuse / simplification

- The `_TOML = next((_TEMPLATE_ROOT / n for n in ("pdca.toml.jinja", "pdca.toml") if
  ...), None); RENDERED = ...` block is duplicated verbatim across
  `test_verify_base.py:61-63` and `test_verify_red_leg.py:40-42` (and a near-twin lives
  inside `test_families.py`'s `_source()`). This *looks* like a candidate for a shared
  helper, but there is no `tests/conftest.py` or util module in `template/tests/` today,
  and the identical inline idiom already exists pre-patch in
  `test_remote_control_docs.py:29-32` and `test_settings_permissions.py` — which the
  brief's own Citations section names as the pattern to mirror. This is established
  per-file convention in this codebase, not new debt introduced by this patch, so I'm not
  filing it as a finding.

## Summary

Clean on both lenses. No NEEDS-HUMAN items from this leaf.
