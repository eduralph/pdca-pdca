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

Review of issue 495: make Copier-dependent skips truthful and prevent a no-render/no-update root-suite run from silently succeeding.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The acceptance boundary distinguishes interpreter importability, bare-developer compatibility, and the guarded no-evidence outcome, so each user-visible contract is independently decidable (`CONTRIBUTING.md:27`). |
| C2 Reproduction (red pre-fix) | PASS | With the patch stashed, `/usr/bin/python3 -m unittest discover -s tests -v` reproduced 7/7 skips saying `copier not installed` at exit 0; retaining the regression oracle while reverting the three suite changes produced 14 failures at the assertions that reject collection-time verdicts and the false reason (`tests/test_copier_availability.py:172`). |
| C3 Change | PASS | The scoped change reaches all three affected use sites and both repository consumers, so neither an unchanged module nor an unchanged CI invocation can preserve the silent green (`tests/test_render_and_run.py:33`, `tests/test_render_cli_name.py:54`, `tests/test_update_compat.py:205`, `.github/workflows/render-check.yml:42`). |
| C4 Verification (red→green) | NEEDS-HUMAN | Decide whether the independently reproduced test-only red→green is sufficient — the oracle moved from 14 failures to 16 passes and the guarded real-host run exited 77, but the mandatory verifier reports no behavioral production hunk to revert and therefore exits 77 UNVERIFIABLE (`gate-logs/C4-verify.log:10`; `tests/test_copier_availability.py:344`). |
| C5 Causal adequacy | PASS | The former eager collection verdict is removed and import is performed lazily at each real use; the try/import is therefore the cause transformation expressly exempted from the symptom-guard trigger, while no-evidence is judged at the process boundary (`tests/copier_support.py:59`, `tests/run_root_suite.py:52`). |
| T1 Structure | PASS | One support module owns the skip diagnosis and one entry point owns run-level classification, preserving both supported import shapes without duplicating policy across the three suites (`tests/copier_support.py:34`, `tests/run_root_suite.py:98`). |
| T2 Shape | PASS | The patched workflow parses as YAML, all test modules parse as Python, `git diff --check` is clean, and both frozen docs/link audits passed (`.github/workflows/render-check.yml:36`; `gate-logs/T2-docs.log:16`; `gate-logs/host-ci-docs.log:15`). |
| T3 Runtime | PASS | The real importable-Copier dependency was exercised: the frozen run executed all 23 root cases, including the same 7 render/update cases, then passed 1,758 offline cases; independently, the system-interpreter regression passed 16/16 and the two workflow-shaped commands returned 77 when evidence was absent (`gate-logs/T3-suite.log:36`, `gate-logs/T3-suite.log:52`, `gate-logs/T3-suite.log:1148`, `tests/run_root_suite.py:77`). |
| T4 Contribution | N/A | Contribution artifacts do not exist during Check by design, and the frozen row records that their substantive audit will rerun at publish (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | PASS | Upstream affected-path history contains only earlier merged work (not this availability/process-boundary treatment), while the complete open-PR set and the sole closed-unmerged PR have no affected-path match; no prior-art collision or scope re-entry remains to decide. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether exit 77 plus the detailed interpreter/PATH diagnosis is the right contributor and CI experience — the reviewer observed bare `unittest` remain exit 0 and the documented guarded entry point emit a leading `PDCA-UNVERIFIABLE:` line at exit 77, but fitness of that policy remains a sign-off judgment (`CONTRIBUTING.md:27`, `tests/copier_support.py:37`, `tests/run_root_suite.py:81`). |

### Advisory — code-review

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

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] C4 Verification (red→green) — Decide whether the independently reproduced test-only red→green is sufficient — the oracle moved from 14 failures to 16 passes and the guarded real-host run exited 77, but the mandatory verifier reports no behavioral production hunk to revert and therefore exits 77 UNVERIFIABLE (`gate-logs/C4-verify.log:10`; `tests/test_copier_availability.py:344`).
- [ ] Validation — fitness-to-purpose — Decide whether exit 77 plus the detailed interpreter/PATH diagnosis is the right contributor and CI experience — the reviewer observed bare `unittest` remain exit 0 and the documented guarded entry point emit a leading `PDCA-UNVERIFIABLE:` line at exit 77, but fitness of that policy remains a sign-off judgment (`CONTRIBUTING.md:27`, `tests/copier_support.py:37`, `tests/run_root_suite.py:81`).
- [ ] `tests/test_update_compat.py:245-247` leaks a `tempfile.mkdtemp()`
- [ ] C4 fix verified: bundle test red pre-fix, green post-fix unverifiable — no behavioral production change to revert (test-only or docs-only patch)
- [ ] leaf produced no usable verdict (needs a human) — plan-advisory leaf 'plan-reviewer' did not produce findings (produced no artifact); re-run it or adjudicate by hand.

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: iterated-to-Do
- Iteration delta (if iterating): Rejected on the advisory code-review's NEEDS-HUMAN [impl] finding, which is verified rather than suspected: `tests/test_update_compat.py:245-247` leaks a `tempfile.mkdtemp()` directory on exactly the pipx posture this slice exists to serve (copier on PATH, not importable by the running interpreter). Removing the class-level `@unittest.skipUnless` was right for criterion (ii), but it left `cls.tmp = Path(tempfile.mkdtemp())` (:245) executing BEFORE the copier check now reached via `render_prior_edit_and_update` (:247, :210). When `import_copier()` raises `SkipTest` out of `setUpClass`, `unittest.suite` sets `_classSetupFailed` and `tearDownClass` is never called, so the `shutil.rmtree` at :250-252 does not run. This fires twice per invocation during the bundle's own T3 gate run, just below what that gate inspects. What to change next: - Hoist the copier check above the temp-dir creation in `UpdateCompat.setUpClass` — call `import_copier()` as the first statement, or wrap :245-247 in try/except SkipTest that removes `cls.tmp` before re-raising. Mirror the ordering the two sibling call sites in this same patch already use: `tests/test_render_and_run.py:37-38` and `tests/test_render_cli_name.py:57-58` both import before `mkdtemp()`. - Close the coverage gap that let it through. `NoVerdictBeforeATestBodyRuns. test_modules_import_and_collect_with_copier_unimportable` only inspects `__unittest_skip__` and never runs `setUpClass`; `BareDeveloperRunIsUnchanged`'s two cases do run it but assert only pass/fail/skip-reason. Add an assertion that the pipx-posture run leaves no temp directory behind — that is what turns this from an invisible leak into a caught regression. Keep as-is — do not re-do this part: the diagnosis and the no-evidence outcome are both right and independently confirmed. The lazy point-of-use import in `tests/copier_support.py`, the truthful reason carrying the real ImportError plus the PATH lookup, the `tests/run_root_suite.py` process-boundary classification (its testsRun / per-test-skip / setUpClass-skip accounting was checked against `unittest.suite` and is correct for both shapes this repo produces), the exit-77 `PDCA-UNVERIFIABLE:` contract, the untouched bare-`unittest` behaviour (criterion iv), and both in-repo consumers (`render-check.yml`, `CONTRIBUTING.md`) are all correct. The repeated try/except import shape across five files is inherent to the two mandatory invocation shapes, not duplication to factor out. This is one statement in the wrong order plus the assertion that would have caught it.
- By / date: Eduard Ralph / 2026-08-15

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 0 finding(s); brief revised: no (plan-advisory-*.md)
- (empty is the common case)
- A `mkdtemp()` before a `SkipTest`-raising check in `setUpClass` leaks silently (`tearDownClass` is suppressed once `_classSetupFailed` is set) — no gate or lens catches this class; only the advisory code-review found it, by hand. Worth a lens or a T3 check for temp-dir residue after a suite run.
