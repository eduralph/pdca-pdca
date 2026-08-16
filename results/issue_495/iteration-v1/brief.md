# Brief — issue 495 / copier-skip-tells-the-truth-and-is-never-silent

> The Plan artifact (docs 02 §PLAN). Do reads ONLY this file.

- **Slug:** copier-skip-tells-the-truth-and-is-never-silent
- **Defect:** On a host where copier is installed and working — but installed as a **CLI in its
  own venv** (pipx-style, the documented way to install it) — the three root test modules skip
  their entire render/update coverage, the suite reports `OK`, and the skip reason claims
  `copier not installed`. That is the only leg exercising a *rendered instance*, so the T3
  runtime gate can pass having verified nothing about rendering or `copier update`, and anyone
  reading the output is told to install a tool that is already there.
  All three gate on **library importability in the running interpreter** and then report it as
  **tool installation** — verified on the target base:
  `tests/test_render_and_run.py:21-31` (`try: from copier import run_copy` → `HAVE_COPIER` →
  `@unittest.skipUnless(HAVE_COPIER, "copier not installed")`), `tests/test_update_compat.py:32-37`
  and `:232`, `tests/test_render_cli_name.py:44-52`. Those are different propositions: a
  pipx-style install puts an executable on `PATH` whose shebang points at a private venv.
  **Reproduced on this host** (see Repro): `copier 9.17.1` at `/home/eddie/.local/bin/copier`,
  shebang `#!/home/eddie/.local/share/copier-venv/bin/python3`, while `python3 -c 'import copier'`
  raises `ModuleNotFoundError` — and `python3 -m unittest discover -s tests` answers
  `Ran 7 tests in 0.000s` / `OK (skipped=7)`.
  The gate leg here is green *only* because this instance works around it:
  `engine/scripts/run-suite.sh` runs the root suite with `.venv/bin/python3` and
  `[install].extra_bootstrap` pip-installs copier into that venv. Remove either and the gate is
  green-by-skip. The reviewer leaf has no such workaround — it re-runs with the host interpreter —
  so it reports the coverage as absent, and this landed as a §6 NEEDS-HUMAN item in **4 of the 5**
  cycles frozen for the 2026-08-10 Act review: `results/issue_413/SUMMARY.md:74`,
  `issue_458/SUMMARY.md:86`, `issue_459/SUMMARY.md:72`, and `issue_472/SUMMARY.md:211`, which
  concluded from it that *the gate environment* lacked copier — disproved by that same bundle's
  `results/issue_472/gate-logs/T3-suite.log:24-26` (`Ran 7 tests in 21.468s`, `OK`). The
  misleading skip reason is what made the misdiagnosis reasonable, and four §6 items were noise.
- **Success criterion:** With the patch, on an interpreter that cannot import copier while the
  `copier` executable is on `PATH` (the pipx posture reproduced below):
  (i) the skip reason **states the proposition actually tested** — that copier is not importable
  in *this interpreter* — and names where the executable was found, so the reader is never told
  to install a tool that is present;
  (ii) a run in which **every** render/update test skips is **not** reported as an ordinary
  pass when the suite is running as a gate (`$PDCA_BUNDLE` set, or an explicit flag): the leg
  declares itself unverifiable / fails, so the row lands as evidence-absent rather than as a
  silent green;
  (iii) outside a gate context (a bare developer run) the modules still skip rather than fail,
  and on an interpreter that *can* import copier — this instance's `.venv`, and CI — all three
  modules run exactly as they do today, with the same 7 tests and no new dependency;
  (iv) the probe's verdict and its reason are obtainable **without re-running the suite**, so
  the regression test can drive both postures against a synthetic environment rather than the
  ambient one.
- **Falsifiability:** RED is reachable, and this host is the environment that shows it: `copier`
  is on `PATH` (9.17.1, pipx-style shebang) and the system `python3` cannot import it, so both
  legs of the pipx posture are producible without provisioning anything. The regression test must
  not *depend* on that ambient posture, though — it drives the probe with the import and the
  `PATH` lookup both controlled, so it is deterministic on a host of either shape.
  **Gate posture — declared, not a gap.** This slice's patch is confined to the target's root
  `tests/*.py`, which `engine/scripts/run-verify.sh:130-144` classifies as test files: with no
  behavioural production change to revert, C4-verify exits 77 `PDCA-UNVERIFIABLE` → SUMMARY §6
  NEEDS-HUMAN, non-gating, rather than a false red. That is the sanctioned path for this class
  (issue #165 discipline; `docs/INTEGRATION.md` §4 names an UNVERIFIABLE C4 — "docs-only /
  test-only bundles — you judge them by reading" — as a project-defined human-only item), and
  it is the route this instance's issue_507 bundle took for the same reason. **Do must not
  invent a production edit to manufacture a red leg, and must not move the fix out of `tests/`
  to earn one.** The red→green evidence the human adjudicates in §6 is the pair of commands in
  Repro below, run with the host interpreter: pre-fix `OK (skipped=7)` with the false reason;
  post-fix a truthful reason, and a non-pass under `$PDCA_BUNDLE`. Green-with-fix on the
  *importable* interpreter comes from the bundle-scoped advisory `T3-suite` row, which runs both
  suites with `.venv/bin/python3` inside the patched worktree.
- **Invariant to restore:** A test may skip only on the proposition it reports, and a wholesale
  skip is never a pass in a gate. Two edges of one rule, stated over the category rather than
  these three modules: (a) a skip reason is evidence a human acts on, so it must name the
  condition actually probed — "not importable in this interpreter" is not "not installed"; (b)
  "no test ran" is not a verdict — the same rule `engine/README.md:44-68` and
  `engine/scripts/run-verify.sh:63-91` already state for every verification leg ("a step in
  which no test ran is UNVERIFIABLE … never a pass and never a fail. A gate never turns 'no
  evidence' into a verdict"), applied to the suite that *supplies* the gate its evidence.
  Self-test: it cannot be satisfied by fixing one module — all three carry the same probe, and
  the gate-context rule is about the run as a whole. Source: internal project invariant (Tier C),
  cited from the target's own written gate doctrine above. `docs/principles.md` §5/§6 are
  unfilled scaffolds in this instance, so no §6 category gate applies.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Ordering note:** No `Depends on` / `Conflicts with` on purpose. This bundle is one of the
  nine ids of run 2 of the 0.60 bug phase, sequenced by the human as a **single wave**
  (`plan-0.60-bug-order.md`): declaring an ordering field would split the run into waves, and a
  wave > 0 bundle in this instance is what issue 474 (also in this run) false-reds. Ordering
  lives in the run boundaries. This slice is the only one in the run that touches the target's
  **root** `tests/` — every other bundle works in `template/` or `docs/` — so it is file-disjoint
  from all eight of its wave-mates. The run plan front-loads it deliberately: it cleans the
  review signal every later bundle is judged by.
- **Surfaces:** data
- **Difficulty:** medium
- **Scope:** The copier availability probe shared by the three root modules and what a wholesale
  skip reports under a gate: make the reported reason true, make the reason and verdict drivable
  by a test, and make an all-skipped render/update leg visible instead of silent when the suite
  runs as a gate. **Out of scope:** rewriting the suites to drive the copier **CLI as a
  subprocess** so a pipx host regains the coverage (the issue's fuller option 1) — the modules
  use `run_copy` / `run_update` as a library with in-process fixtures, and re-plumbing them is a
  separate, much larger slice with its own risk; file it if the human wants pipx-host coverage
  after this lands. Also out of scope: what the 7 render/update tests assert; `template/tests/`;
  `engine/scripts/run-suite.sh` and this instance's `[install].extra_bootstrap` workaround (a
  different repo — `docs/INTEGRATION.md` §2 — and both stay as they are); the `copier importable
  (.venv)` doctor row, which stays required; adding copier as a hard dependency of the suite.
- **Repro instruction:** On a clean checkout of the target base (`origin/main` of
  eduralph/pdca-harness), on this host, with the **system** interpreter (not `.venv`):
  1. `which copier && copier --version` → `/home/eddie/.local/bin/copier`, `copier 9.17.1`;
     `head -1 /home/eddie/.local/bin/copier` → `#!/home/eddie/.local/share/copier-venv/bin/python3`;
     `python3 -c 'import copier'` → `ModuleNotFoundError: No module named 'copier'`.
  2. From the target root: `python3 -m unittest discover -s tests -v 2>&1 | tail -8` →
     every case `skipped 'copier not installed'`, then `Ran 7 tests in 0.000s` and `OK
     (skipped=7)`. That is the whole defect in one line of output: a green that tested nothing,
     with a reason that is false.
  3. Contrast: `.venv/bin/python3 -m unittest discover -s tests` from this instance's root runs
     the same 7 tests for real — which is what
     `results/issue_472/gate-logs/T3-suite.log:24-26` recorded while
     `results/issue_472/SUMMARY.md:211` was concluding the opposite.
- **External dependencies:** none that must be installed — the slice builds and its regression
  test runs on the base toolchain. The red→green demonstration needs an interpreter that cannot
  import copier while the copier executable is on PATH, which is this host's ordinary posture
  (no-check: an interpreter/PATH combination, not a package a detect command can probe; the
  registered copier doctor row covers the opposite condition the gate needs).
- **Test file:** `tests/test_copier_probe.py` (new, in the target's **root** `tests/`, beside the
  three modules it is about — a root module is what the T3 gate's first leg discovers, and
  `engine/scripts/run-verify.sh:182-185` runs a root test as `python3 -m unittest tests.<name>`
  from the target root). It must drive the probe directly with the import and the `PATH` lookup
  controlled (criterion (iv)), so it is deterministic whether or not the host has copier. See
  Falsifiability for why C4 records this bundle UNVERIFIABLE regardless of the file chosen.
- **Citations expected:** Do must cite path:line on the target branch for every change.
  Composition cues:
  * the three probe sites to unify are `tests/test_render_and_run.py:21-31`,
    `tests/test_update_compat.py:32-37` + `:232`, `tests/test_render_cli_name.py:44-52` — they
    are byte-identical in shape, which is why one shared, drivable probe is the composition
    rather than three edits;
  * the vocabulary for (ii) is the harness's own gate vocabulary, not a new one:
    `PDCA-UNVERIFIABLE:` + exit 77 as defined in `engine/README.md:44-68` and used throughout
    `engine/scripts/run-verify.sh`; `$PDCA_BUNDLE` is the environment variable the driver exports
    to every gate command (`gates.py:491`), and is what distinguishes a gate run from a
    developer run;
  * `template/tests/test_remote_control_docs.py:11-17` is the precedent for a suite that must
    behave correctly in more than one sanctioned posture — the same care applies to a probe that
    must not turn a developer's bare run into a failure.
  The new test must not import a symbol this patch introduces **at module level** if that symbol
  could vanish on a revert; here the whole patch is test-side, so C4 will report UNVERIFIABLE
  either way — but keep the import at the top of the module honest and self-contained so the T3
  leg never breaks on collection.

  **Path convention in this brief:** every `template/…`, `tests/…` and `docs/…` path is on the
  **target branch** (eduralph/pdca-harness @ main) — those are the files Do reads and edits. Every
  `engine/…`, `pdca.toml` and `results/…` path is in **this pdca-pdca instance** (the verification
  engine and the bundles that run the cycle); they are cited to explain how the gates will judge
  this patch, and Do must not edit them.
- **Prior-art check (triage cycles):** By file path on `origin/main`:
  `tests/test_render_and_run.py` — `a641742` (#337 docs), `82514e0`, `30262c2`, `3ca179a`: the
  `HAVE_COPIER` import probe has been there since the initial harness commit and has never been
  revisited; `tests/test_update_compat.py` and `tests/test_render_cli_name.py` copied it.
  `gh pr list -R eduralph/pdca-harness --state open` → **no open PRs**. Open issues searched for
  `copier`: #385 (update-compat misses non-marker merge failures — about what those tests
  *assert*, not whether they run), #441 (nothing checks that every configured gate has a
  runner), #422, #477 — none is this. This instance's own Act log routed it upstream on
  2026-08-10. Not previously attempted, not rejected.
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: Rejected on SLICING. Criterion (i) — the truthful skip reason — is delivered and was live-verified on this host's real pipx posture; it alone removes the misdiagnosis that cost four cycles of §6 noise. Criterion (ii) is not met, and cannot be met inside the scope this brief declared. WHY (ii) IS UNREACHABLE AS SCOPED Criterion (ii) requires an all-skipped render/update leg to land as EVIDENCE-ABSENT under a gate. The only channel that produces that row is the process EXIT CODE the classifier reads. `gates.py:729-733` is explicit, and it is a deliberate hardening from issue #329: "The marker is honoured only for an exit code that is not a failure — 0, or the dedicated UNVERIFIABLE_RC. A gate that exits non-zero FAILED, whatever its output happens to contain, and saying otherwise masked real red." The patch emits the `PDCA-UNVERIFIABLE:` marker via `self.fail(unverifiable_message(...))`, which exits 1 — so the marker is ignored BY DESIGN and the row lands as `fail`. The patch adopts the harness's evidence-absent vocabulary on a channel the harness deliberately refuses to read at that exit code. That is not a build mistake. `python3 -m unittest discover` exits 0 or 1 and nothing in `tests/` can make the process exit 77, while the brief puts `engine/scripts/run-suite.sh` — the only in-reach place that could map an all-skipped leg onto UNVERIFIABLE_RC — explicitly OUT OF SCOPE. The brief demanded an outcome and scoped out the sole means of producing it; its own "declares itself unverifiable / fails" slash then licensed the half that was reachable. A rebuild against this brief hits the same wall. EVIDENCE THAT "fails" IS THE WRONG HALF This bundle's own reviewer leaf ran the patched tree in the pipx posture, got 2 failures + 1 error / exit 1, and filed T3 FAIL calling it "a false red rather than the intended unverifiable runtime result". The first real consumer of the new behaviour misread it as genuine breakage. Shipping as-is converts intermittent §6 confusion into a recurring stream of FALSE FAIL verdicts from the reviewer leaf on any pipx host — louder than the silent green, and no more truthful. WHAT TO AUTHOR AT PLAN — pick one, do not leave it to the builder A. Widen scope to include the suite-runner boundary, so an all-skipped render/update leg under `$PDCA_BUNDLE` maps to UNVERIFIABLE_RC (77) and the row lands evidence-absent as #329 intends. Note the runner lives in this instance, not the target repo (`docs/INTEGRATION.md` §2) — the brief must say which repo carries the change, which is the question that pushed it out of scope in the first place. B. Split: land the truthful-reason half (criterion (i) plus the shared probe and its regression test — all sound, keep this attempt's `tests/_copier_probe.py` and `tests/test_copier_probe.py`) as its own bundle, and raise the silent-green half separately once A's repo-boundary question is answered. Either way the child brief must resolve the open C5 question rather than inherit it: whether an eager capability probe is the right treatment at all, or whether copier should be imported lazily on first real use so capability detection stops standing in for execution. Also fold in the two dead-code observations, both harmless but free to fix: `HAVE_COPIER` is now computed in all three modules and read by none, and each module still runs its own top-level copier import alongside the probe's, so the two could drift about availability.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  Rejected on SLICING. Criterion (i) — the truthful skip reason — is delivered and was
  live-verified on this host's real pipx posture; it alone removes the misdiagnosis that
  cost four cycles of §6 noise. Criterion (ii) is not met, and cannot be met inside the
  scope this brief declared.

  WHY (ii) IS UNREACHABLE AS SCOPED

  Criterion (ii) requires an all-skipped render/update leg to land as EVIDENCE-ABSENT under
  a gate. The only channel that produces that row is the process EXIT CODE the classifier
  reads. `gates.py:729-733` is explicit, and it is a deliberate hardening from issue #329:
  "The marker is honoured only for an exit code that is not a failure — 0, or the dedicated
  UNVERIFIABLE_RC. A gate that exits non-zero FAILED, whatever its output happens to
  contain, and saying otherwise masked real red."

  The patch emits the `PDCA-UNVERIFIABLE:` marker via `self.fail(unverifiable_message(...))`,
  which exits 1 — so the marker is ignored BY DESIGN and the row lands as `fail`. The patch
  adopts the harness's evidence-absent vocabulary on a channel the harness deliberately
  refuses to read at that exit code.

  That is not a build mistake. `python3 -m unittest discover` exits 0 or 1 and nothing in
  `tests/` can make the process exit 77, while the brief puts `engine/scripts/run-suite.sh`
  — the only in-reach place that could map an all-skipped leg onto UNVERIFIABLE_RC —
  explicitly OUT OF SCOPE. The brief demanded an outcome and scoped out the sole means of
  producing it; its own "declares itself unverifiable / fails" slash then licensed the half
  that was reachable. A rebuild against this brief hits the same wall.

  EVIDENCE THAT "fails" IS THE WRONG HALF

  This bundle's own reviewer leaf ran the patched tree in the pipx posture, got 2 failures +
  1 error / exit 1, and filed T3 FAIL calling it "a false red rather than the intended
  unverifiable runtime result". The first real consumer of the new behaviour misread it as
  genuine breakage. Shipping as-is converts intermittent §6 confusion into a recurring
  stream of FALSE FAIL verdicts from the reviewer leaf on any pipx host — louder than the
  silent green, and no more truthful.

  WHAT TO AUTHOR AT PLAN — pick one, do not leave it to the builder

  A. Widen scope to include the suite-runner boundary, so an all-skipped render/update leg
     under `$PDCA_BUNDLE` maps to UNVERIFIABLE_RC (77) and the row lands evidence-absent as
     #329 intends. Note the runner lives in this instance, not the target repo
     (`docs/INTEGRATION.md` §2) — the brief must say which repo carries the change, which is
     the question that pushed it out of scope in the first place.

  B. Split: land the truthful-reason half (criterion (i) plus the shared probe and its
     regression test — all sound, keep this attempt's `tests/_copier_probe.py` and
     `tests/test_copier_probe.py`) as its own bundle, and raise the silent-green half
     separately once A's repo-boundary question is answered.

  Either way the child brief must resolve the open C5 question rather than inherit it:
  whether an eager capability probe is the right treatment at all, or whether copier should
  be imported lazily on first real use so capability detection stops standing in for
  execution. Also fold in the two dead-code observations, both harmless but free to fix:
  `HAVE_COPIER` is now computed in all three modules and read by none, and each module still
  runs its own top-level copier import alongside the probe's, so the two could drift about
  availability.
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
