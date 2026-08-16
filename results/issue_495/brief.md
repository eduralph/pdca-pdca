# Brief — issue 495 / truthful-copier-skip-and-no-silent-green

> The Plan artifact (docs 02 §PLAN). Do reads ONLY this file.

- **Slug:** truthful-copier-skip-and-no-silent-green
- **Defect:** On a host where copier is installed and working — but installed as a **CLI in its
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
- **Success criterion:** On an interpreter that cannot import copier while the `copier`
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
- **Falsifiability:** RED is reachable and was produced on this host during Plan — no
  provisioning needed. `copier` is on `PATH` (9.17.1, pipx shebang) and `/usr/bin/python3`
  cannot import it, so (i)/(ii)/(iv) go red pre-fix with the exact output quoted in Repro
  step 2. The *green* posture is equally available: `.venv/bin/python3` imports copier 9.17.0
  (verified). The regression module must not *depend* on either ambient posture — it supplies
  both (criterion vi) — so it is deterministic on a host of either shape.
  **Gate posture — declared, not a gap.** Every file this slice touches is classified
  non-production by the C4 verifier: `tests/*.py` → the test set, `.github/*` and `*.md` →
  non-behavioural (`engine/scripts/run-verify.sh:130-137`). With no production hunk to revert
  the verifier exits 77 `PDCA-UNVERIFIABLE` at `:143` → SUMMARY §6 NEEDS-HUMAN, non-gating —
  the sanctioned path for this class (issue #165; `docs/INTEGRATION.md` §4 names an
  UNVERIFIABLE C4 — "docs-only / test-only bundles — you judge them by reading" — as a
  project-defined human-only item). **Do must not invent a production edit to manufacture a red
  leg, and must not move the fix out of `tests/` to earn one.** The red→green evidence the human
  adjudicates in §6 is the command pair in Repro, run with the system interpreter. The
  importable-interpreter green comes from the advisory `T3-suite` row, which runs both suites
  with `.venv/bin/python3` inside the patched worktree, and from `render-check.yml` on the draft
  PR.
- **Invariant to restore:** A suite may report a skip only on the proposition that actually
  stopped it, and a run that produced no evidence is never a success. Two edges of one rule,
  stated over the category rather than these three modules. The second edge needs somewhere to
  live: a process has three possible answers here — it passed, it failed, it could not tell —
  and `unittest`'s discovery exit gives two, so **the third belongs at the suite's own process
  boundary**, not bolted into test bodies that can only pass or fail. Source: the target's own
  written gate doctrine — `template/engine/scripts/run-verify.sh:73-74` ("a step in which no
  test ran is UNVERIFIABLE … never a pass and never a fail. A gate never turns 'no evidence'
  into a verdict"), `template/engine/README.md.jinja:56,68`, and the classifier that consumes
  it, `template/src/pdca_harness/gates.py:83-86, 758-774`. Internal project invariant (Tier C),
  cited from the repo that authors the doctrine. Self-test: it cannot be satisfied by fixing one
  module — all three carry the same conflation, and the no-evidence edge is a property of the
  run as a whole. (`docs/principles.md` §5/§6 are unfilled scaffolds in this instance, so no §6
  category gate applies; the Plan-exit shape gate was run by hand — see the closing note.)
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Ordering note:** No `Depends on` / `Conflicts with`, deliberately. This bundle is one of the
  nine ids of run 2 of the 0.60 bug phase, sequenced by the human as a **single wave**
  (`plan-0.60-bug-order.md`): declaring an ordering field would split the run into waves and
  trigger stacking, which issue 474 (also in this run) false-reds. Ordering lives in the run
  boundaries. This slice is the only one in the run that touches the target's **root** `tests/`,
  `.github/`, or `CONTRIBUTING.md` — every other bundle works in `template/` or `docs/` — so it
  is file-disjoint from all eight wave-mates. It is front-loaded on purpose: it cleans the review
  signal every later bundle is judged by.
- **Surfaces:** data
- **Difficulty:** medium
- **Scope:** How the target's root render/update suites decide that their coverage did not run,
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
- **Repro instruction:** On a clean checkout of the target base (`origin/main` of
  eduralph/pdca-harness), from the target root, with the **system** interpreter (not `.venv`):
  1. `which copier && copier --version && head -1 "$(which copier)"` → `/home/eddie/.local/bin/copier`,
     `copier 9.17.1`, `#!/home/eddie/.local/share/copier-venv/bin/python3`;
     `/usr/bin/python3 -c 'import copier'` → `ModuleNotFoundError: No module named 'copier'`.
  2. `/usr/bin/python3 -m unittest discover -s tests -v` → every case
     `skipped 'copier not installed'`, then `Ran 7 tests in 0.000s` and `OK (skipped=7)`.
     That is the whole defect in two lines of output: a reason that is false, and a green that
     tested nothing.
  3. Post-fix, same interpreter, the same command must still print `OK (skipped=…)` and exit 0
     (criterion iv) — with a truthful reason — while the root-suite entry point named in
     `CONTRIBUTING.md` exits 77 with a leading `PDCA-UNVERIFIABLE:` line (criterion iii).
  4. Contrast / green posture: `/home/eddie/pdca/pdca-pdca/.venv/bin/python3 -m unittest discover
     -s tests` runs the same 7 tests for real (copier 9.17.0 importable there) — which is what
     `results/issue_472/gate-logs/T3-suite.log:24-26` recorded while
     `results/issue_472/SUMMARY.md:211` concluded the opposite.
- **External dependencies:** `copier importable (.venv)` — already a required row; it is what
  gives the gate the *green* posture of criterion (v). The *red* posture needs an interpreter
  that cannot import copier while the `copier` executable is on `PATH` (no-check: an
  interpreter/`PATH` combination, not a package a detect command can probe — and the regression
  module supplies both postures itself, so nothing must be provisioned). Nothing else beyond the
  base toolchain.
- **Test file:** `tests/test_copier_availability.py` (new, in the target's **root** `tests/`,
  beside the three modules it is about). It must drive both the truthful-reason path and the
  no-evidence classification with the import outcome and the `PATH` lookup injected
  (criterion vi), so it is deterministic whether or not the host has copier. Gate shape,
  checked: this project's C4 is the *revert-the-production-hunks* variant
  (`engine/scripts/run-verify.sh:128-143` classifies, then reverts the `PROD` set), so a new
  file is not required to earn a red — but with `PROD` empty this bundle exits 77 UNVERIFIABLE
  regardless of the path chosen (see Falsifiability). Discovery pattern note: `unittest
  discover` collects `test*.py`, so any non-`test`-prefixed module this fix adds under `tests/`
  is not itself collected — keep the regression cases in the named file.
  **Two invocation shapes, both mandatory** — the gates use different ones, and a module that
  imports cleanly under only one of them silently stops being evidence:
  `engine/scripts/run-suite.sh:31` runs `discover -s tests`, which puts `tests/` on `sys.path`
  as the top-level dir (sibling modules import as bare names), while
  `engine/scripts/run-verify.sh:178-184` and `.github/workflows/render-check.yml:37,40` run
  `python3 -m unittest tests.<name>` from the repo root (sibling modules import as
  `tests.<name>`, via the implicit namespace package — `tests/` has **no** `__init__.py` on the
  base, and this slice has no reason to add one). Whatever this fix adds under `tests/` must be
  importable under both. Nothing here is behind a `cfg`/feature/env flag, so both gate
  invocations really do compile and execute the named cases — no vacuous green.
- **Citations expected:** Do must cite path:line on the target branch for every change.
  Composition cues:
  * **the truthful skip, in this repo's own voice** — `tests/test_update_compat.py:237-241` is
    the peer: `setUpClass` discovers a missing precondition at the point it is needed and raises
    `unittest.SkipTest("no vX.Y.Z tags in this checkout (shallow clone? needs fetch-depth: 0)")`
    — the condition that actually stopped it, plus what to do about it. Mirror that voice *and*
    that placement (at use, not at import) for the copier case. Note `UpdateCompat` already
    reaches copier from `setUpClass` via `render_prior_edit_and_update` (`:209`, `:219`), while
    `RenderAndRun` (`:45`) and `RenderCliName` (`:66`) reach it inside their single test body;
  * **the three sites that must converge** — `tests/test_render_and_run.py:24-31`,
    `tests/test_render_cli_name.py:45-52`, `tests/test_update_compat.py:33-37` + `:232`. They
    are byte-identical in shape, which is why one answer rather than three edits. Both leftovers
    the last review found go with them: `HAVE_COPIER` must not survive as a computed-but-unread
    name, and no module should keep a second, independent copier import that could drift from
    the one that decides availability;
  * **the no-evidence vocabulary is the repo's own, not a new one** —
    `template/src/pdca_harness/gates.py:83-86` (`UNVERIFIABLE_RC = 77`, `UNVERIFIABLE_MARKER =
    "PDCA-UNVERIFIABLE:"`) and `:758-774` (the classifier). Two constraints from that code: the
    marker counts only at the **start of a line** (#428), and only on an exit that is **0 or
    77** (#329);
  * **the runner shape to mirror** — `template/engine/scripts/run-verify.sh:47-74` is this
    repo's written pattern for a runner that judges a leg by *two* facts (exit status **and**
    how many tests actually ran) and prints distinguishable reasons for the two "nothing ran"
    cases. The root-suite entry point is the same shape applied to the suite that *supplies*
    the gate its evidence;
  * **the in-repo consumers** — `.github/workflows/render-check.yml:36-40` (two steps; keep
    their current per-module selection, and keep `fetch-depth: 0` at `:27` — #342) and
    `CONTRIBUTING.md:26` (the command list, which names the offline suite only).
  **Residual, deliberately not in this slice:** this instance's `engine/scripts/run-suite.sh:31`
  runs `discover -s tests` and would have to opt into the new entry point for the T3 row to
  change here. That is a one-line pdca-pdca edit outside the cycle (`docs/INTEGRATION.md` §2),
  not a pdca-harness contribution. Do must not touch it.

  **Path convention in this brief:** every `tests/…`, `template/…`, `docs/…`, `.github/…` and
  `CONTRIBUTING.md` path is on the **target branch** (eduralph/pdca-harness @ main) — those are
  the files Do reads and edits. Every `engine/…`, `pdca.toml`, `plan-0.60-bug-order.md` and
  `results/…` path is in **this pdca-pdca instance**; they are cited only to explain how the
  gates will judge this patch, and Do must not edit them.
- **Prior-art check (triage cycles):** By file path on `origin/main` (`git -C ../pdca-harness log
  --oneline -- tests/test_render_and_run.py tests/test_update_compat.py
  tests/test_render_cli_name.py`): `f918fd8`, `df99e9e`, `f0f1f9d`, `a641742`, `71463ad`,
  `2946428`, `82514e0`, `30262c2` — the `HAVE_COPIER` import probe has been there since the
  files were created and has never been revisited; the two later modules copied it. Closest
  prior art is `2946428` (#342), which fixed a *different* silent-skip (shallow clone → no tags)
  in CI config rather than in the suite — precedent that this repo treats "skips itself into a
  permanent green" as a bug, not that this one was attempted. `gh pr list -R
  eduralph/pdca-harness --state open` → **no open PRs**. Closed PRs searched for `copier`: #374,
  #343, #381, #258, #444, #77, #209 — all merged, none touching the availability decision; no
  rejected path match. Open issues mentioning copier / skip / suite: #517 (`template/tests/`
  spawn hygiene — different test root), #496, #474 — none is this. Closed issues searched for
  the symptom: only #165 (the C4 test-only false-fail already cited under Falsifiability). Not
  previously attempted upstream, not rejected. This instance's Act log routed it upstream on
  2026-08-10.
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.

## Iteration 2 — carry-forward (from the previous attempt)
- Sign-off rationale: Rejected on the advisory code-review's NEEDS-HUMAN [impl] finding, which is verified rather than suspected: `tests/test_update_compat.py:245-247` leaks a `tempfile.mkdtemp()` directory on exactly the pipx posture this slice exists to serve (copier on PATH, not importable by the running interpreter). Removing the class-level `@unittest.skipUnless` was right for criterion (ii), but it left `cls.tmp = Path(tempfile.mkdtemp())` (:245) executing BEFORE the copier check now reached via `render_prior_edit_and_update` (:247, :210). When `import_copier()` raises `SkipTest` out of `setUpClass`, `unittest.suite` sets `_classSetupFailed` and `tearDownClass` is never called, so the `shutil.rmtree` at :250-252 does not run. This fires twice per invocation during the bundle's own T3 gate run, just below what that gate inspects. What to change next: - Hoist the copier check above the temp-dir creation in `UpdateCompat.setUpClass` — call `import_copier()` as the first statement, or wrap :245-247 in try/except SkipTest that removes `cls.tmp` before re-raising. Mirror the ordering the two sibling call sites in this same patch already use: `tests/test_render_and_run.py:37-38` and `tests/test_render_cli_name.py:57-58` both import before `mkdtemp()`. - Close the coverage gap that let it through. `NoVerdictBeforeATestBodyRuns. test_modules_import_and_collect_with_copier_unimportable` only inspects `__unittest_skip__` and never runs `setUpClass`; `BareDeveloperRunIsUnchanged`'s two cases do run it but assert only pass/fail/skip-reason. Add an assertion that the pipx-posture run leaves no temp directory behind — that is what turns this from an invisible leak into a caught regression. Keep as-is — do not re-do this part: the diagnosis and the no-evidence outcome are both right and independently confirmed. The lazy point-of-use import in `tests/copier_support.py`, the truthful reason carrying the real ImportError plus the PATH lookup, the `tests/run_root_suite.py` process-boundary classification (its testsRun / per-test-skip / setUpClass-skip accounting was checked against `unittest.suite` and is correct for both shapes this repo produces), the exit-77 `PDCA-UNVERIFIABLE:` contract, the untouched bare-`unittest` behaviour (criterion iv), and both in-repo consumers (`render-check.yml`, `CONTRIBUTING.md`) are all correct. The repeated try/except import shape across five files is inherent to the two mandatory invocation shapes, not duplication to factor out. This is one statement in the wrong order plus the assertion that would have caught it.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  Rejected on the advisory code-review's NEEDS-HUMAN [impl] finding, which is verified rather
  than suspected: `tests/test_update_compat.py:245-247` leaks a `tempfile.mkdtemp()` directory
  on exactly the pipx posture this slice exists to serve (copier on PATH, not importable by the
  running interpreter). Removing the class-level `@unittest.skipUnless` was right for criterion
  (ii), but it left `cls.tmp = Path(tempfile.mkdtemp())` (:245) executing BEFORE the copier check
  now reached via `render_prior_edit_and_update` (:247, :210). When `import_copier()` raises
  `SkipTest` out of `setUpClass`, `unittest.suite` sets `_classSetupFailed` and `tearDownClass`
  is never called, so the `shutil.rmtree` at :250-252 does not run. This fires twice per
  invocation during the bundle's own T3 gate run, just below what that gate inspects.

  What to change next:
  - Hoist the copier check above the temp-dir creation in `UpdateCompat.setUpClass` — call
    `import_copier()` as the first statement, or wrap :245-247 in try/except SkipTest that
    removes `cls.tmp` before re-raising. Mirror the ordering the two sibling call sites in this
    same patch already use: `tests/test_render_and_run.py:37-38` and
    `tests/test_render_cli_name.py:57-58` both import before `mkdtemp()`.
  - Close the coverage gap that let it through. `NoVerdictBeforeATestBodyRuns.
    test_modules_import_and_collect_with_copier_unimportable` only inspects `__unittest_skip__`
    and never runs `setUpClass`; `BareDeveloperRunIsUnchanged`'s two cases do run it but assert
    only pass/fail/skip-reason. Add an assertion that the pipx-posture run leaves no temp
    directory behind — that is what turns this from an invisible leak into a caught regression.

  Keep as-is — do not re-do this part: the diagnosis and the no-evidence outcome are both right
  and independently confirmed. The lazy point-of-use import in `tests/copier_support.py`, the
  truthful reason carrying the real ImportError plus the PATH lookup, the `tests/run_root_suite.py`
  process-boundary classification (its testsRun / per-test-skip / setUpClass-skip accounting was
  checked against `unittest.suite` and is correct for both shapes this repo produces), the exit-77
  `PDCA-UNVERIFIABLE:` contract, the untouched bare-`unittest` behaviour (criterion iv), and both
  in-repo consumers (`render-check.yml`, `CONTRIBUTING.md`) are all correct. The repeated
  try/except import shape across five files is inherent to the two mandatory invocation shapes,
  not duplication to factor out. This is one statement in the wrong order plus the assertion that
  would have caught it.
- Full previous attempt preserved in `iteration-v2/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
