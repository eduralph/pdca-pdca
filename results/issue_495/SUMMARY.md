# Result — issue 495 / truthful-copier-skip-and-no-silent-green

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: On a host where copier is installed and working — but installed as a **CLI in its
  own venv** (pipx-style, the documented way to install it) — the three root test modules skip
  their entire render/update coverage, the suite reports `OK`, and the skip reason claims
  `copier not installed`. That is the only leg exercising a *rendered instance*, so a runtime
  gate can report success having verified nothing about rendering or `copier update`, and anyone
  reading the output is told to install a tool that is already there.
  Two distinct errors, both verified on the target base (`origin/main`, `acb214a`):
  **(a) the reason is false.** All three modules decide at *collection* time whether copier is
  **importable in the running interpreter**, then report that as **tool installation** —
  `tests/test_render_and_run.py:24-31` (`try: from copier import run_copy` → `HAVE_COPIER` →
  `@unittest.skipUnless(HAVE_COPIER, "copier not installed")`), `tests/test_render_cli_name.py:45-52`,
  `tests/test_update_compat.py:33-37` + `:232`. Those are different propositions: a pipx-style
  install puts an executable on `PATH` whose shebang points at a private venv.
  **Reproduced live on this host while writing this brief:** `which copier` →
  `/home/eddie/.local/bin/copier`, `copier --version` → `copier 9.17.1`, its shebang
  `#!/home/eddie/.local/share/copier-venv/bin/python3`; `/usr/bin/python3 -c 'import copier'` →
  `ModuleNotFoundError: No module named 'copier'`; and from the target root
  `/usr/bin/python3 -m unittest discover -s tests` → `Ran 7 tests in 0.000s` / `OK (skipped=7)`,
  every case `skipped 'copier not installed'`.
  **(b) a run with no evidence exits as success.** `Ran 7 tests … OK`, exit 0 — indistinguishable
  from a run in which the coverage actually executed. This is the same failure the repo has
  already treated as a bug once: `2946428` (#342) added `fetch-depth: 0` to
  `.github/workflows/render-check.yml` precisely because `test_update_compat` "would skip itself
  into a permanent green". The in-repo consumer is still exposed —
  `.github/workflows/render-check.yml:36-40` runs `python -m unittest tests.test_render_and_run`
  and `tests.test_update_compat`, and a wholesale skip there is a green job.
  Downstream cost, already paid: the misleading reason made a wrong diagnosis reasonable in
  **4 of the 5** cycles frozen for the 2026-08-10 Act review (`results/issue_413/SUMMARY.md:74`,
  `issue_458/SUMMARY.md:86`, `issue_459/SUMMARY.md:72`, `issue_472/SUMMARY.md:211`), each asking
  the human to "supply copier" — while `results/issue_472/gate-logs/T3-suite.log:24-26`
  (`Ran 7 tests in 21.468s`, `OK`) shows the tests had run. Four §6 items were noise.
- Success criterion: On an interpreter that cannot import copier while the `copier`
  executable is on `PATH` (the pipx posture reproduced above):
  (i) the reason recorded for each skipped render/update case names **the condition that
  actually stopped it** — that copier could not be imported by *this* interpreter — carrying the
  real import error and where the executable was found on `PATH`; it never asserts that copier is
  not installed;
  (ii) that reason is produced **because the operation failed where it is used**, not by a
  verdict reached before any test body runs: with copier importable, nothing in these modules
  decides availability at import/collection time;
  (iii) there is a way to run the root suite — named in `CONTRIBUTING.md` and used by the repo's
  own `render-check` workflow — for which a run where **no** copier-dependent case executed exits
  `77` with a line **starting** `PDCA-UNVERIFIABLE:` (the vocabulary and exit code at
  `template/src/pdca_harness/gates.py:83-86`, honoured at `:758-774`), while a run in which they
  did execute exits 0 on success and non-zero on a real failure, unchanged;
  (iv) `python3 -m unittest discover -s tests` — the bare developer run, and any ad-hoc run
  inside a leaf session — is **unchanged**: still skips rather than fails, still exits 0,
  still `OK (skipped=N)`. No environment variable and no ambient bundle context alters it;
  (v) on an interpreter that *can* import copier (this instance's `.venv`, and CI) all three
  modules run exactly as they do today — the same 7 tests, the same assertions, no new
  dependency;
  (vi) (i)–(iv) are exercised by the bundle's regression module with **the import outcome and
  the `PATH` lookup supplied by the test**, so the result does not depend on what the host
  happens to have installed, and neither verdict nor reason requires re-running the suite.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: How the target's root render/update suites decide that their coverage did not run,
  what they report when it did not, and what a run carrying no such evidence exits with. Three
  things must become true together: the reported reason names the condition that actually
  stopped the coverage rather than a different proposition settled at collection time; the
  coverage's absence is a consequence of the operation failing at the point of use, not a
  decision taken before any test body runs; and a run in which no copier-dependent case executed
  leaves the process carrying the repo's own no-evidence outcome instead of success. In scope
  with it: the two in-repo consumers that would otherwise keep reporting such a run as green —
  `.github/workflows/render-check.yml` (its two existing steps, keeping their current module
  selection) and the `CONTRIBUTING.md` command list, which today names only the offline driver
  suite (`CONTRIBUTING.md:26`) and no root-suite command at all. Shipping the no-evidence outcome
  with no in-repo caller would be a mechanism nobody invokes.
  **Out of scope:** rewriting the suites to drive the copier **CLI as a subprocess** so a pipx
  host regains the coverage (the issue's fuller option 1) — the modules use `run_copy` /
  `run_update` as a library against in-process fixtures, and re-plumbing that is a separate,
  much larger slice; file it if you want pipx-host coverage after this lands. Also out of scope:
  what the 7 render/update tests assert; `template/tests/` (the offline driver suite, which
  needs no copier); this instance's `engine/scripts/run-suite.sh` and `[install].extra_bootstrap`
  — a different repo (`docs/INTEGRATION.md` §2), and see the residual note under Citations; the
  `copier importable (.venv)` doctor row, which stays required; adding copier as a hard
  dependency of the suite.
  **Explicitly rejected — do not re-attempt:** the previous attempt (archived in
  `iteration-v1/`) made the modules **fail** (`self.fail(...)`, exit 1) when `$PDCA_BUNDLE` was
  set. Sign-off rejected it: `gates.py:729-733` honours the `PDCA-UNVERIFIABLE:` marker only at
  a non-failing exit (0 or 77) — a deliberate #329 hardening — so the row landed `fail`, and the
  bundle's own reviewer leaf read the result as genuine breakage. "Fail" is the wrong verdict
  for absent evidence, and `$PDCA_BUNDLE` is a bundle-identity variable, not a declaration that
  coverage is required. Neither an eager collection-time capability probe nor a failing test
  body is the treatment.

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: unverifiable — no behavioral production change to revert (test-only or docs-only patch)
- C5 added test exercises production, not a copy: pass — no new driver-suite test in this patch — 1 added test file(s) out of scope

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

Review of issue 495: make Copier-dependent root tests report import failures truthfully at point of use and prevent no-evidence runs from exiting successfully.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The contract distinguishes a CLI-only pipx install, a bare developer run, and a coverage-required process boundary, so the intended user-visible outcomes are decidable and bounded (`CONTRIBUTING.md:27`). |
| C2 Reproduction (red pre-fix) | PASS | With the patch stashed, the live pipx posture reproduced seven false `copier not installed` skips and exit 0; this is the exact condition the new truthful diagnostic must distinguish (`tests/copier_support.py:39`). |
| C3 Change | PASS | The patch stays within the three Copier suites and their two in-repo consumers, centralizing the truthful precondition and adding the required suite boundary without changing rendered-product behavior (`tests/copier_support.py:61`, `tests/run_root_suite.py:98`, `.github/workflows/render-check.yml:42`). |
| C4 Verification (red→green) | NEEDS-HUMAN | Human must accept the test-only red→green as sufficient evidence because the deterministic C4 verifier had no production hunk to revert: independently the base was false-green, while the patched 17-case regression passed and the real pipx runner returned marker + 77; the frozen importable-Copier run executed all render/update cases (`tests/test_copier_availability.py:316`). |
| C5 Causal adequacy | PASS | The causal choice is sound: eager collection-time probes are removed and the dependency is resolved at first real use before fixture allocation, so the added helper transforms the load-time cause rather than guarding a capability-present path (`tests/test_render_and_run.py:33`, `tests/test_update_compat.py:241`). |
| T1 Structure | PASS | Shared import diagnosis has one owner and no-evidence classification lives at the suite process boundary, keeping test modules and policy separate (`tests/copier_support.py:36`, `tests/run_root_suite.py:52`). |
| T2 Shape | PASS | The workflow preserves its two named module selections and full-history checkout while routing both through the documented runner; frozen docs/site audits were clean and `git diff --check` passed (`.github/workflows/render-check.yml:22`, `.github/workflows/render-check.yml:42`). |
| T3 Runtime | PASS | Runtime evidence covers both postures: the system-interpreter regression passed with truthful skips/77, and the frozen importable-Copier gate ran 24 root tests plus 1,758 offline-driver tests successfully (`tests/test_copier_availability.py:373`, `tests/run_root_suite.py:77`). |
| T4 Contribution | N/A | Contribution artifacts do not exist at Check by design; the frozen row is deferred, and the substantive PR-description audit is obligatorily rerun at publish. |
| T5 Judgment | PASS | No actionable defect or duplicate/rejected attempt was found: merged history was checked for every affected path and the sole closed-unmerged PR touched none; classifier failure, skip, empty, and success branches are independently asserted (`tests/test_copier_availability.py:316`, `tests/test_copier_availability.py:344`, `tests/test_copier_availability.py:364`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Human must decide whether exit 77 is the right maintainer-facing treatment for missing render/update evidence, because it intentionally stops CI while leaving ad-hoc `unittest discover` behavior unchanged (`.github/workflows/render-check.yml:36`, `CONTRIBUTING.md:32`). |

### Advisory — code-review

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

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] C4 Verification (red→green) — Human must accept the test-only red→green as sufficient evidence because the deterministic C4 verifier had no production hunk to revert: independently the base was false-green, while the patched 17-case regression passed and the real pipx runner returned marker + 77; the frozen importable-Copier run executed all render/update cases (`tests/test_copier_availability.py:316`).
- [x] Validation — fitness-to-purpose — Human must decide whether exit 77 is the right maintainer-facing treatment for missing render/update evidence, because it intentionally stops CI while leaving ad-hoc `unittest discover` behavior unchanged (`.github/workflows/render-check.yml:36`, `CONTRIBUTING.md:32`).
- [x] C4 fix verified: bundle test red pre-fix, green post-fix unverifiable — no behavioral production change to revert (test-only or docs-only patch)
- [x] leaf produced no usable verdict (needs a human) — plan-advisory leaf 'plan-reviewer' did not produce findings (produced no artifact); re-run it or adjudicate by hand.

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
- Plan advisory: 0 finding(s); brief revised: no (plan-advisory-*.md)
- (empty is the common case)
- After #495 lands: this instance's `engine/scripts/run-suite.sh` still calls the old root-suite path, so pdca-pdca's own T3 gate keeps the false-green the fix removes upstream — point it at `python3 -m tests.run_root_suite`.
