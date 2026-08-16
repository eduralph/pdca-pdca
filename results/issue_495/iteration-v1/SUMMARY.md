# Result — issue 495 / copier-skip-tells-the-truth-and-is-never-silent

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: On a host where copier is installed and working — but installed as a **CLI in its
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
- Success criterion: With the patch, on an interpreter that cannot import copier while the
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
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: The copier availability probe shared by the three root modules and what a wholesale
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

Review of issue #495: make Copier-dependent root tests report importability truthfully and prevent an all-skipped gate run from appearing green.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The acceptance boundary is mechanically decidable: import availability, gate context, and run/skip/fail classification are separate propositions, matching the target gate vocabulary at `tests/_copier_probe.py:38` and `tests/_copier_probe.py:72`. |
| C2 Reproduction (red pre-fix) | PASS | With the patch stashed, the real pipx posture (`copier` on PATH, system Python unable to import it) reproduced all 7 cases skipping as `copier not installed` and exiting 0 under `PDCA_BUNDLE`; the controlled regression posture is grounded at `tests/test_copier_probe.py:46`. |
| C3 Change | FAIL | An unavailable-Copier gate run raises unittest failures at `tests/test_render_and_run.py:43` and `tests/test_update_compat.py:247`, producing exit 1; the shipped classifier treats every non-77 nonzero exit as `fail`, not evidence-absent, at `template/src/pdca_harness/gates.py:729`, so the required unverifiable outcome is not implemented. |
| C4 Verification (red→green) | NEEDS-HUMAN | The human must accept defect-specific pre/post evidence in lieu of behavioral-production red→green — the deterministic verifier correctly found only a test-side patch and exited 77 (`gate-logs/C4-verify.log:7`, `gate-logs/C4-verify.log:10`), so it cannot discharge C4. |
| C5 Causal adequacy | NEEDS-HUMAN | Decide whether retaining an eager capability probe is the right root-cause treatment or whether Copier should be imported lazily on first real use — the probe at `tests/_copier_probe.py:26` still guards module behavior at `tests/test_render_and_run.py:35`, so this choice determines whether capability detection can continue to replace execution. |
| T1 Structure | PASS | One shared helper owns the availability and gate-context policy, and all three affected modules consume it; this keeps the invariant category-wide (`tests/_copier_probe.py:83`, `tests/test_update_compat.py:39`). |
| T2 Shape | PASS | Both package and discovery import shapes are supported by the regression module (`tests/test_copier_probe.py:18`); independent `compileall` and diff checks were clean, while both frozen shape audits passed (`gate-logs/T2-docs.log:16`, `gate-logs/host-ci-docs.log:15`). |
| T3 Runtime | FAIL | The importable worktree run is green and the frozen tagged suite ran 18 root plus 1,758 driver tests (`gate-logs/T3-suite.log:39`, `gate-logs/T3-suite.log:1135`), but the real unavailable-Copier gate posture produced 2 failures + 1 error and exit 1, which is a false red rather than the intended unverifiable runtime result (`template/src/pdca_harness/gates.py:762`). |
| T4 Contribution | N/A | The contribution artifacts do not exist by design at Check; the frozen row explicitly defers their substantive audit to publish (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | PASS | Closed-PR searches by each affected path found only unrelated merged work (#251, #258, #343, #348, #381, #444), no rejected path match, and exact-symptom searches found no prior implementation, so prior art does not change the judgment. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | The human must decide whether the corrected gate UX is fit after the exit semantics are fixed — run `PDCA_BUNDLE=x python3 -m unittest discover -s tests -v` in a pipx posture and require a truthful evidence-absent outcome under `template/src/pdca_harness/gates.py:773`, not the currently observed unittest FAIL/ERROR result. |

### Advisory — code-review

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

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] C4 Verification (red→green) — The human must accept defect-specific pre/post evidence in lieu of behavioral-production red→green — the deterministic verifier correctly found only a test-side patch and exited 77 (`gate-logs/C4-verify.log:7`, `gate-logs/C4-verify.log:10`), so it cannot discharge C4.
- [ ] C5 Causal adequacy — Decide whether retaining an eager capability probe is the right root-cause treatment or whether Copier should be imported lazily on first real use — the probe at `tests/_copier_probe.py:26` still guards module behavior at `tests/test_render_and_run.py:35`, so this choice determines whether capability detection can continue to replace execution.
- [ ] Validation — fitness-to-purpose — The human must decide whether the corrected gate UX is fit after the exit semantics are fixed — run `PDCA_BUNDLE=x python3 -m unittest discover -s tests -v` in a pipx posture and require a truthful evidence-absent outcome under `template/src/pdca_harness/gates.py:773`, not the currently observed unittest FAIL/ERROR result.
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
- Outcome: iterated-to-Plan
- Iteration delta (if iterating): Rejected on SLICING. Criterion (i) — the truthful skip reason — is delivered and was live-verified on this host's real pipx posture; it alone removes the misdiagnosis that cost four cycles of §6 noise. Criterion (ii) is not met, and cannot be met inside the scope this brief declared. WHY (ii) IS UNREACHABLE AS SCOPED Criterion (ii) requires an all-skipped render/update leg to land as EVIDENCE-ABSENT under a gate. The only channel that produces that row is the process EXIT CODE the classifier reads. `gates.py:729-733` is explicit, and it is a deliberate hardening from issue #329: "The marker is honoured only for an exit code that is not a failure — 0, or the dedicated UNVERIFIABLE_RC. A gate that exits non-zero FAILED, whatever its output happens to contain, and saying otherwise masked real red." The patch emits the `PDCA-UNVERIFIABLE:` marker via `self.fail(unverifiable_message(...))`, which exits 1 — so the marker is ignored BY DESIGN and the row lands as `fail`. The patch adopts the harness's evidence-absent vocabulary on a channel the harness deliberately refuses to read at that exit code. That is not a build mistake. `python3 -m unittest discover` exits 0 or 1 and nothing in `tests/` can make the process exit 77, while the brief puts `engine/scripts/run-suite.sh` — the only in-reach place that could map an all-skipped leg onto UNVERIFIABLE_RC — explicitly OUT OF SCOPE. The brief demanded an outcome and scoped out the sole means of producing it; its own "declares itself unverifiable / fails" slash then licensed the half that was reachable. A rebuild against this brief hits the same wall. EVIDENCE THAT "fails" IS THE WRONG HALF This bundle's own reviewer leaf ran the patched tree in the pipx posture, got 2 failures + 1 error / exit 1, and filed T3 FAIL calling it "a false red rather than the intended unverifiable runtime result". The first real consumer of the new behaviour misread it as genuine breakage. Shipping as-is converts intermittent §6 confusion into a recurring stream of FALSE FAIL verdicts from the reviewer leaf on any pipx host — louder than the silent green, and no more truthful. WHAT TO AUTHOR AT PLAN — pick one, do not leave it to the builder A. Widen scope to include the suite-runner boundary, so an all-skipped render/update leg under `$PDCA_BUNDLE` maps to UNVERIFIABLE_RC (77) and the row lands evidence-absent as #329 intends. Note the runner lives in this instance, not the target repo (`docs/INTEGRATION.md` §2) — the brief must say which repo carries the change, which is the question that pushed it out of scope in the first place. B. Split: land the truthful-reason half (criterion (i) plus the shared probe and its regression test — all sound, keep this attempt's `tests/_copier_probe.py` and `tests/test_copier_probe.py`) as its own bundle, and raise the silent-green half separately once A's repo-boundary question is answered. Either way the child brief must resolve the open C5 question rather than inherit it: whether an eager capability probe is the right treatment at all, or whether copier should be imported lazily on first real use so capability detection stops standing in for execution. Also fold in the two dead-code observations, both harmless but free to fix: `HAVE_COPIER` is now computed in all three modules and read by none, and each module still runs its own top-level copier import alongside the probe's, so the two could drift about availability.
- By / date: Eduard Ralph / 2026-08-15

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 0 finding(s); brief revised: no (plan-advisory-*.md)
- (empty is the common case)
