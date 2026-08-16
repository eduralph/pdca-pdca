# Result — issue 507 / shipped-suites-assert-only-sanctioned-postures

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: Three assertions the template ships **into** every rendered instance pin the
  template's own *default* posture, so an instance that follows the template's published
  instructions inherits permanently red tests in its T3 gate.
  **(a) The sandbox pair — an outright contradiction.**
  `template/tests/test_families.py:353` (`ShippedPdcaTomlExamples.test_leaves_sandbox_is_declared_exactly_once`)
  counts `[leaves.sandbox]` headers *including commented ones* (`^#?\s*\[leaves\.sandbox\]\s*$`)
  and requires exactly one; `:359` (`test_the_commented_example_parses_when_uncommented`)
  requires a **commented** header to exist. Enabling the seam is the sanctioned #277/#287
  opt-in that the block's own comment invites (`template/pdca.toml.jinja:821-827`, "uncomment
  only the lines you need"), and an instance that takes the invitation has no green option:
  drop the example and `:359` fails; keep it beside the now-active table and `:353` fails
  (two headers). Verified by evaluating both regexes over the three postures — default
  PASS/PASS, active-without-example PASS/**FAIL**, active-with-example **FAIL**/PASS — and
  observed live in this instance (enabled at its 2026-08-01 Act review so the codex reviewer's
  prior-art check could reach `api.github.com`; see Repro (a)). It is the instance's only
  remaining `make check` failure across 1730 tests.
  **(b) The C4-skeleton wording assertions — satisfiable, but they contradict the template's
  own instructions.** `template/tests/test_verify_red_leg.py:65-141` (`C4RedLegVerdictRule`,
  7 cases) string-matches sentences of the **skeleton** `engine/scripts/run-verify.sh`
  ("JUDGE EVERY LEG BY TWO FACTS", its ASCII verdict table, the exit-77 vocabulary), and
  `template/tests/test_verify_base.py:293-301` (`VerifyBaseExport.test_the_c4_skeleton_names_the_export_as_the_last_rung`)
  asserts that file contains "Resolve as: $PDCA_BASE > $PDCA_VERIFY_BASE > your own override
  > $PDCA_BRIEF_BASE". But `run-verify.sh` is the one file every instance is *told* to replace
  — `template/engine/scripts/run-verify.sh:2` ("SKELETON. Fill this in for your project."),
  `template/engine/README.md.jinja:31` ("a skeleton for this — fill it in") and `:84`
  ("Replace the skeleton(s) here with your real runners"). An instance with a filled-in gate
  gets exactly **8 failures** the moment it updates to v0.57.0 (the 7 above + the base-ladder
  case), while `EngineReadmeExplainsTheRule` (`test_verify_red_leg.py:144-173`) stays green —
  reproduced, see Repro (b). This instance papered over it by restoring the skeleton's contract
  verbatim above its own implementation (`engine/scripts/run-verify.sh:15-27`, marked TEMPORARY
  pending this issue) — defensive, not necessary.
  This is #386 in two more suites; that issue's resolution (PR #426, commit `75294d1`) is the
  model.
- Success criterion: With the patch, one offline run of
  `cd template && PYTHONPATH=src python3 -m unittest tests.test_families tests.test_verify_red_leg tests.test_verify_base`
  is green, and the cases it contains prove all of the following (each non-current posture
  constructed by the cases themselves as synthetic file text in a temp dir, since the modules
  today read only their own checkout):
  (i) the **unrendered template checkout** — today's green, unchanged;
  (ii) a **rendered instance with an ACTIVE `[leaves.sandbox]` table and no commented example**
  (this instance's posture) is green — red today;
  (iii) a **rendered instance with an active table that kept the commented example beside it**
  is green — red today;
  (iv) a **rendered instance whose `engine/scripts/run-verify.sh` is a filled-in project gate
  that does not quote the skeleton's wording** is green — 8 failures today;
  (v) **still RED:** a rendered instance whose `pdca.toml` declares **two ACTIVE**
  `[leaves.sandbox]` headers — the PR #292 defect (`tomllib` refuses the file, so the driver
  will not start at all) must stay caught in every posture;
  (vi) the template-checkout-only properties keep being asserted **where they hold**: the
  commented sandbox example is present and round-trips to valid TOML when uncommented, and the
  skeleton still publishes the two-facts rule, its four-outcome table and the base ladder;
  (vii) `EngineReadmeExplainsTheRule` and every other case in the three modules are untouched
  and still bind every instance.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: Make the three shipped modules assert each property in the posture where it holds.
  (i) The sandbox pair — the property that binds every instance is that `pdca.toml` stays
  loadable: no more than **one active** `[leaves.sandbox]` table, and any commented example
  that is present round-trips to valid TOML under one table with an unquoted boolean. "A
  commented example is still present" is the template's default and binds the template
  checkout. (ii) The `run-verify.sh` wording — what the harness *publishes* in its skeleton
  binds the template checkout, because every instance is instructed to replace that file; the
  instance-binding half of the two-facts rule is already carried in parallel by
  `EngineReadmeExplainsTheRule` against `engine/README.md`, which ships to every render and is
  not a fill-in file, and stays exactly as it is. Every case's docstring must state which
  posture it binds. **Out of scope:** `template/pdca.toml.jinja` — its sandbox guidance, its
  defaults, and the fact that it ships the example commented all stay unchanged, and the seam
  is neither enabled nor disabled anywhere; `template/engine/scripts/run-verify.sh` and
  `template/engine/README.md.jinja` — no wording changes at all, and in particular do **not**
  add the base ladder to the README to "restore" a parallel home (see Citations: it was never
  there; a follow-up if wanted); `EngineReadmeExplainsTheRule` and every other case in the three
  modules; any `src/`, driver, engine or `copier.yml` change; this instance's own
  `engine/scripts/run-verify.sh:15-27` temporary block, which is pdca-pdca's repo and comes out
  separately once this lands (`docs/INTEGRATION.md` §2 keeps instance changes outside the cycle).

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: unverifiable — no behavioral production change to revert (test-only or docs-only patch)
- C5 added test exercises production, not a copy: pass — patch adds no new test file — nothing to assert

## 4. Conformance (Check — stack)
- T1 Structure: none — (no gate configured)
- T2 shape: docs lint + site render link audit: pass — docs lint clean, site render + link audit clean
- T2 host CI parity: target docs-check.yml on the pushed tree: pass — host CI parity on the patched tree — docs lint clean, site render + link audit clean
- T3 runtime: render/update-compat + offline driver suites: pass — root suite OK, driver suite OK
- T4 PR body has a user-impact opener + tracker id in both artifacts: deferred — pr-description.md not drafted yet — the substantive T4 audit of the contribution artifacts runs at publish
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Task under review: make shipped template suites accept every sanctioned rendered-instance posture while retaining template-only wording checks and duplicate-sandbox protection.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief defines all five positive/negative postures, preserves the two-active-table protection, and declares no external dependency. |
| C2 Reproduction (red pre-fix) | PASS | With the patch stashed, the active/no-example and active/kept-example fixtures each produced one failure and the filled-in gate produced all eight expected failures; the patched fixtures are grounded at `template/tests/test_families.py:462`, `template/tests/test_families.py:471`, and `template/tests/test_verify_red_leg.py:204`. |
| C3 Change | FAIL | Broaden active-header recognition before shipping — `^\[leaves\.sandbox\]` ignores TOML-valid leading whitespace, so the shipped suite is green for two indented active tables while `tomllib` rejects that same file as a duplicate declaration (`template/tests/test_families.py:337`). |
| C4 Verification (red→green) | NEEDS-HUMAN | Decide whether the independent synthetic red→green is sufficient for this test-only change — the project C4 gate exited 77 because there is no behavioral production hunk to revert (`gate-logs/C4-verify.log:10`). |
| C5 Causal adequacy | PASS | The causal approach scopes replaceable-skeleton assertions to the template posture while retaining the instance-level README contract, rather than probing or guarding an optional capability (`template/tests/test_verify_red_leg.py:73`, `template/tests/test_verify_red_leg.py:223`). |
| T1 Structure | PASS | The patch remains confined to the three brief-listed shipped test modules, with posture helpers and regressions colocated with the assertions they exercise (`template/tests/test_families.py:330`, `template/tests/test_verify_base.py:55`, `template/tests/test_verify_red_leg.py:32`). |
| T2 Shape | PASS | Independent `git diff --check`, docs lint, and site render/link audit were clean, matching the frozen shape evidence (`gate-logs/T2-docs.log:16`). |
| T3 Runtime | PASS | The targeted run passed 71 tests, the full offline suite passed independently, and the frozen render/update-compat plus driver suites report green (`gate-logs/T3-suite.log:1612`). |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check and the mandatory publish-time audit owns the substantive verdict (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | PASS | The change is one logical, brief-scoped test-posture correction; affected-path commit history and open/closed PR searches found no competing or rejected implementation, with merged PR #426 serving only as the established precedent. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether template-default assertions should be scoped out of rendered instances while preserving only cross-posture protections — this policy changes what every generated project treats as a shipped invariant (`template/tests/test_families.py:363`). |

### Advisory — code-review

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

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] C4 Verification (red→green) — Decide whether the independent synthetic red→green is sufficient for this test-only change — the project C4 gate exited 77 because there is no behavioral production hunk to revert (`gate-logs/C4-verify.log:10`).
- [x] Validation — fitness-to-purpose — Decide whether template-default assertions should be scoped out of rendered instances while preserving only cross-posture protections — this policy changes what every generated project treats as a shipped invariant (`template/tests/test_families.py:363`).
- [x] C4 fix verified: bundle test red pre-fix, green post-fix unverifiable — no behavioral production change to revert (test-only or docs-only patch)

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: merged-wider
- Iteration delta (if iterating):
- By / date: Eduard Ralph / 2026-08-15

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
