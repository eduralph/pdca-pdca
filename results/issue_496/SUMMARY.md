# Result — issue 496 / pin-split-never-aborts-flow

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: The rule "a split must never be able to abort the flow that caused it" (`template/src/pdca_harness/flow.py:1087-1088`) is only partly held by tests. The production code is correct today; this is a missing-test defect, and **no production change is wanted**. Measured on `origin/main` @ `f33a23f` by applying each mutant from the issue to a scratch copy and running the offline suite (`cd template && PYTHONPATH=src python3 -m unittest …`): (1) **Mutant 3 survives everything** — make `_real` (`flow.py:868-878`) re-raise instead of returning `None`; the full offline suite gives the same result as the unmutated tree. With that mutant, a child bundle whose path will not resolve ends `pdca flow 500` with an uncaught `OSError` out of `_warn_stranded_split_children` (`flow.py:1542`). (2) **Mutants 1 and 2 are killed only by accident** — always take the splice branch at `flow.py:1286` (`if tail is None:`), and narrow `_reschedule`'s `except Exception` at `flow.py:1098` to `except ZeroDivisionError`. Since the issue was filed, #565 (`fe8208f`) added `test_children_a_failed_reschedule_leaves_in_flight_are_let_go` (`template/tests/test_flow_single_driver.py:824`), which fails under both. But that test is about releasing claims across two processes: it checks one stderr line of a paused child process and nothing else. Nothing asserts the run's exit code, the `flow: could not re-wave the run after a split (…)` line (no test anywhere matches that string), the absence of a traceback, or that the work of the other bundles in the run is still reported. The adoption suite itself (`tests.test_flow_adopt_split` + `tests.test_flow_adopt_recovery`) still passes under all three mutants.
- Success criterion: New tests in `template/tests/test_flow_adopt_split.py` pass on the unmodified target tree, and each of the three mutants below, applied alone, makes at least one of the NEW tests fail when only that module is run (`cd template && PYTHONPATH=src python3 -m unittest tests.test_flow_adopt_split`). The tests drive the run through `cli._flow` (the suite's existing `self._cli([...])` helper), never a direct `flow.*` call. **(A) Failed reschedule, with work still to do after it:** run `pdca flow 500 7 8` where bundle 8's brief carries `Depends on: 7` (so 500 and 7 share wave 0 and 8 waits in wave 1), 500 splits into 601 and 602 mid-run, and the levelling raises `RuntimeError` on the post-split reschedule. Injection seam: replace `waves.partition_schedulable` with a wrapper that raises only when the bundle list it is given contains `issue_601`, and restore it at cleanup. Assert: the wrapper raised exactly once, on a list that also contained `issue_8`, and bundle 8 was still `PLANNED` at that moment (this is what proves the run had work left when the reschedule failed); rc is 0; stderr contains `flow: could not re-wave the run after a split (RuntimeError: ` and `the children of issue_500 could not be scheduled; they are left in-flight`; stderr does not contain `Traceback`; 601 and 602 are still `PLANNED` and are not in the run's results map; bundles 7 and 8 both reach `COMPLETE`, with 8 driven in a wave of its own after the failure; 500, 7 and 8 all appear as `COMPLETE` in the run's results map. **(B) Unresolvable child path:** run `pdca flow 500` where 500 splits into 601 and 602 and resolving `issue_601`'s path raises `OSError`. Injection seam: `pathlib.Path.resolve`, replaced (from the fixture's `after_split` hook, restored at cleanup) by a wrapper that raises `OSError` only for a path whose `.name` is `issue_601` and calls the real method otherwise. **Do not inject at `flow._real`** — that replaces the very function M3 mutates, so the test would pass with or without the mutant. Assert: the wrapper was reached at least once; rc is 0; stderr contains `ignoring child id '601'`; stderr does not contain `Traceback` or `split adoption failed`; 602 is adopted and reaches `COMPLETE`; 601 is still `PLANNED`, has no `patch.diff`, and is not in the results map. **The three mutants** (each must be killed by A or B): M1 — `flow.py:1286` `if tail is None:` → `if False:`; M2 — `flow.py:1098` `except Exception as exc:` → `except ZeroDivisionError as exc:`; M3 — `flow.py:876-878`, the `return None` in `_real`'s handler → `raise`.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: Add tests to `template/tests/test_flow_adopt_split.py` that hold the "a split never aborts the flow" rule for the two failure paths above (scenarios A and B), so that M1, M2 and M3 each fail the adoption suite on their own. Test-only. / out of scope: any change under `template/src/` (the code is correct — if Do finds it is not, stop and say so in `build-notes.md` rather than fixing it here); changing or moving `test_children_a_failed_reschedule_leaves_in_flight_are_let_go` in `test_flow_single_driver.py`; the other broad `except Exception` sites in `flow.py` (`_isolate`, `_is_split_parent`, teardown) — they are not among the three mutants; new test helpers in a shared module.

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

Pin the rule that split adoption cannot abort its originating flow, using tests for failed rescheduling and an unresolvable child path without changing production code.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The observable contract covers continued work, truthful results, diagnostics and child isolation; both scenarios exercise the existing no-abort guarantee at `template/src/pdca_harness/flow.py:1087` and `template/src/pdca_harness/flow.py:869`. |
| C2 Reproduction (red pre-fix) | PASS | Independently reproduced the coverage gap: all three mutants survive the original 27-test module, while each fails a new test; mutation sites ground at `template/src/pdca_harness/flow.py:1286`, `:1098` and `:878`; replay evidence is recorded below. |
| C3 Change | PASS | Both requested failure paths are covered within the authorized test-only boundary, including pending bundle 8 and rejection of child 601 without losing 602; `template/tests/test_flow_adopt_split.py:1241`, `:1298`. |
| C4 Verification (red→green) | NEEDS-HUMAN | Accept the independently reproduced mutation evidence as sufficient for this test-only change and complete the brief's sign-off replay — the standard gate cannot revert a production fix here (exit 77, `gate-logs/C4-verify.log:10`), although M1–M3 each fail and restored production passes all 29 tests (`review-evidence/restored.log:7`). |
| C5 Causal adequacy | PASS | The new assertions detect the actual failure-containment regressions through `cli._flow`, including work in a later wave; fault injection leaves `_real` under test, and no production capability probe or symptom guard is introduced; `template/tests/test_flow_adopt_split.py:155`, `:1274`, `:1313`. |
| T1 Structure | PASS | Existing fixtures and production result capture preserve the module's architecture; both injected functions register restoration, avoiding cross-test contamination; `template/tests/test_flow_adopt_split.py:276`, `:1269`, `:1322`. |
| T2 Shape | PASS | Independent whitespace check, docs lint and 22-page render/link audit pass; frozen docs and host-parity logs corroborate these results (`gate-logs/T2-docs.log:16`, `gate-logs/host-ci-docs.log:15`). |
| T3 Runtime | PASS | Independent patched-target run passes 2,073 tests with two skips; frozen evidence additionally demonstrates 24 root tests passing (`gate-logs/T3-suite.log:54`, `:1713`); the local Copier limitation is documented below. |
| T4 Contribution | N/A | Contribution artifacts are intentionally drafted after Check; the substantive contribution audit must rerun at publish (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Confirm the brief's explicit choice of two scenarios rather than the issue's suggested single test — omitting the second leaves M3 undetected, as independent replay confirms; `brief.md:24`, `template/tests/test_flow_adopt_split.py:1298`. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether protection against these two adoption failures sufficiently serves the operator's uninterrupted-flow requirement — the CLI-driven evidence demonstrates containment and remaining-wave completion, but does not establish immunity to every possible split failure; `template/tests/test_flow_adopt_split.py:1279`, `:1294`, `:1330`. |

No patch defect found. Source citations above are relative to `$PDCA_TARGET`; its disposable base identifies `f33a23f342f0304f726ddbd314a515b83d1d86d7`, and the supplied patch matches its sole tracked change. No target-state caveat was needed. Production source and the submitted patch were not edited.

Independent replay used Python 3.14.4 and a copy under this reviewer sandbox. Since there is no production fix to stash, the pre-fix test file was obtained from the disposable target's `HEAD`; production mutations were applied individually in the copy. Every run used `PYTHONPATH=src python3 -B -m unittest tests.test_flow_adopt_split`.

| Variant | Independently observed result |
|---------|-------------------------------|
| Original tests, unchanged production | 27 tests pass (`review-evidence/base.log:7`). |
| Original tests, M1 / M2 / M3 individually | 27 tests pass for each (`review-evidence/base-M1.log:7`, `review-evidence/base-M2.log:7`, `review-evidence/base-M3.log:7`). |
| Patched tests, unchanged production | 29 tests pass (`review-evidence/patched.log:7`). |
| M1: `if tail is None:` → `if False:` | New reschedule test errors with `TypeError: must assign iterable to extended slice` (`review-evidence/patched-M1.log:7`). |
| M2: `_reschedule` catches `ZeroDivisionError` instead of `Exception` | New reschedule test errors with injected `RuntimeError: levelling blew up` (`review-evidence/patched-M2.log:7`). |
| M3: `_real` handler re-raises instead of returning `None` | New unresolvable-child test errors with `OSError` escaping `_warn_stranded_split_children` (`review-evidence/patched-M3.log:7`). |
| Extra mutant: discard remaining waves in the failed-reschedule branch | New reschedule test fails on rc 1 rather than 0 (`review-evidence/patched-M4-tail.log:7`). |
| Production restored | 29 tests pass (`review-evidence/restored.log:7`). |

For sign-off replay, use the exact edits recorded at `template/tests/test_flow_adopt_split.py:1233`, apply each alone in a disposable copy, run the module command above, and restore production between runs. Expect the failures listed here and a final 29-test pass. The complete replay procedure is preserved in `review-evidence/replay.py`.

The independent full offline run is captured in `review-evidence/offline-suite.log`. The local root-suite attempt exited 77 because `/usr/bin/python3` cannot import Copier (`review-evidence/root-suite.log:9`); that is a reviewer-host limitation, not a patch defect. The frozen T3 log actually shows the render and update-compatibility cases executing successfully, followed by 24 tests / OK (`gate-logs/T3-suite.log:35`, `:54`). Thus those checks were exercised in the round, rather than inferred from a CLI shim or code inspection. The brief declares no external dependencies. The C5 scanner log only establishes that there is no new test file (`gate-logs/C5-prod-path.log:10`); production-path coverage was established independently by the replay and fixture inspection above.

Prior-art investigation was rerun against GitHub by both affected paths. Main history matches the brief, including `fe8208f` for the existing claim-release coverage; the test file's latest change is `389bf1a`. Across all 252 closed PRs, the one unmerged PR touched neither path; there are no open PRs (`review-evidence/prior-art.log:1`, `:12`, `:15`). No unresolved prior-art conflict was found. The target's available integration document is the unfilled template, whose human-only list remains TODO (`template/docs/INTEGRATION.md.jinja:80`); no additional project-specific item can be inferred from it.

### Advisory — code-review

# Advisory code review — issue 496 / pin-split-never-aborts-flow

**Verdict: the diff is clean on both lenses.** I found no correctness bugs. The only cleanups are two optional nits. The patch changes tests only (`template/tests/test_flow_adopt_split.py`), and nothing under `template/src/` changes, which matches the brief.

## Mutants replayed (scratch copy of `$PDCA_TARGET/template`, Python 3.14.4)

Command: `PYTHONPATH=src python3 -m unittest tests.test_flow_adopt_split`

- Unmutated: `Ran 29 tests … OK`. Run 3 more times together with `test_flow_adopt_recovery` and `test_flow_single_driver`: OK each time, so no flakiness and no leaked monkeypatch was seen.
- M1 (`template/src/pdca_harness/flow.py:1286` `if tail is None:` → `if False:`): `test_a_failed_reschedule_after_a_split_never_aborts_the_run` ERROR, `TypeError: must assign iterable to extended slice`.
- M2 (`template/src/pdca_harness/flow.py:1098` → `except ZeroDivisionError`): same test ERROR, `RuntimeError: levelling blew up`.
- M3 (`template/src/pdca_harness/flow.py:878` `return None` → `raise`): `test_a_child_whose_path_will_not_resolve_never_aborts_the_run` ERROR, `OSError: cannot resolve …/issue_601`.
- Plan review's 4th mutant (`wave_list[k + 1:] = []` added inside the `if tail is None:` branch): the reschedule test FAILs. It fails at `template/tests/test_flow_adopt_split.py:1279` (`1 != 0` on rc), which is earlier than the `'PLANNED' != 'COMPLETE'` the brief predicted. Either way the mutant is caught.

All three required mutants are killed, each by a new test, when only that module runs. That meets the success criterion.

## Findings

- `template/tests/test_flow_adopt_split.py:1321-1322` — correctness looks fine. `Path.resolve` is patched on the class for the whole process. The cleanup is registered right after the patch, inside `after_split`, so it runs even if `_cli` raises. The wrapper only raises for `.name == "issue_601"` and passes every other call to the real method, so other tests and the fixture's `shutil.rmtree` cleanup are not affected. Injecting at `pathlib.Path.resolve` rather than at `flow._real` is what lets M3 be seen, and the replay confirms it. No action.
- `template/tests/test_flow_adopt_split.py:32` (nit, optional) — the new `import pathlib` is redundant, because `Path` is already imported and is the same class object. `real_resolve = Path.resolve` / `setattr(Path, "resolve", …)` would do the same thing. Keeping `pathlib.Path.resolve` does make the patch site match the brief's wording word for word, so leaving it is also fine.
- `template/tests/test_flow_adopt_split.py:1225-1238` (nit, optional) — the new comment block and docstrings cite `flow.py` line numbers (`:1087-1088`, `:1092`, `:1098`, `:1286`, `:876-878`, `:1649`). The brief asks for this so the mutants can be replayed, but these numbers will drift with any edit to `flow.py`. Naming the function next to each line number (it mostly does already) makes the replay notes easier to maintain. No action needed for this cycle.

No NEEDS-HUMAN items from this lens. The C4 `unverifiable` result (`gate-logs/C4-verify.log`) is the expected outcome for a test-only patch, as the brief says. The mutant replay above is the evidence that stands in for it.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] C4 Verification (red→green) — Accept the independently reproduced mutation evidence as sufficient for this test-only change and complete the brief's sign-off replay — the standard gate cannot revert a production fix here (exit 77, `gate-logs/C4-verify.log:10`), although M1–M3 each fail and restored production passes all 29 tests (`review-evidence/restored.log:7`).
- [x] T5 Judgment — Confirm the brief's explicit choice of two scenarios rather than the issue's suggested single test — omitting the second leaves M3 undetected, as independent replay confirms; `brief.md:24`, `template/tests/test_flow_adopt_split.py:1298`.
- [x] Validation — fitness-to-purpose — Decide whether protection against these two adoption failures sufficiently serves the operator's uninterrupted-flow requirement — the CLI-driven evidence demonstrates containment and remaining-wave completion, but does not establish immunity to every possible split failure; `template/tests/test_flow_adopt_split.py:1279`, `:1294`, `:1330`.
- [x] C4 fix verified: bundle test red pre-fix, green post-fix unverifiable — no behavioral production change to revert (test-only or docs-only patch)
- [x] **Scenario A cannot show "the run carries on"; its bundle 7 is finished before the failure happens.** The brief's invariant says "the run carries on and exits as it would have without the split", and `flow.py:1088-1089` promises a failed reschedule "leaves the caller with today's waves … rather than a half-spliced run". But in `pdca flow 500 7` with a *mid-run* split, 500 and 7 have no edge, so they share wave 0; adoption runs only after that wave is driven (`flow.py:1728` then `:1736`), and `remaining = wave_list[k+1:]` (`flow.py:1284`) is empty. "Bundle 7 reaches COMPLETE" is therefore true before `_reschedule` is ever called, and nothing is left to carry on to. A mutant that clobbers the tail in the `tail is None` branch (e.g. `wave_list[k + 1:] = []`) passes every Scenario A assertion. The existing test the brief calls "accidental" is actually stronger on this axis: there 500 is a pre-split seed, so the failure happens at `k=-1` and run A "goes on to drive 7" afterwards (`test_flow_single_driver.py:826-832`, `:845`). Revision: give Scenario A a bundle in a wave *after* 500's (e.g. an id with `Depends on: 7`) and assert it is driven after the two stderr lines.
- [x] **The "C4 reports PDCA-UNVERIFIABLE (exit 77)" claim is not supported by the target, and the opposite outcome would gate the bundle red.** The brief cites `engine/scripts/run-verify.sh` and `docs/INTEGRATION.md` §4 ("test-only bundles — you judge them by reading"). In the target, `template/engine/scripts/run-verify.sh:86-93` is an unimplemented skeleton that exits 1; its header only describes the 77 path for a patch whose "only non-test change is a NON-BEHAVIORAL file" (`:79-85`); and its verdict table says a test that passes on the red leg is "C4 FAIL (green without the fix)" (`:63`). The quoted INTEGRATION phrase appears nowhere in `template/docs/INTEGRATION.md.jinja`. These are presumably the *instance's* filled-in copies, which are not among the inputs — but the brief does not say so, and does not say the 77 branch was actually exercised for a test-only patch. If the instance script takes the `:63` row instead, Check goes red on a correct bundle and Do is pushed toward exactly the production change the brief forbids. Revision: cite the instance file and line that takes the exit-77 branch for a patch with zero production hunks, or state that it was run.
- [x] **The success criterion's load-bearing half (each mutant kills a new test) is verified by no gate, and the brief leaves one seam open that decides it.** Green-on-unmodified is a command; the mutant kills are hand-replay only (brief: "The human (and the reviewer) replay M1–M3 by hand"). For Scenario B the brief says only "resolving `issue_601`'s path raises `OSError`" / "inject the resolution failure for that one path". If Do injects at `flow._real` rather than at `pathlib.Path.resolve`, the injection replaces the mutated function: every Scenario B assertion passes on the clean tree and M3 becomes unkillable — detectable only by the manual replay. Revision: name the seam (`Path.resolve`, keyed on the `issue_601` path, restored at cleanup; `_real` is its only caller for that path on this run — `flow.py:875`, `:1035`, `:1542`) and say who replays the mutants at Check, since no gate will.
- [x] **Repro note (a), listed as "checked at Plan", cites a line that is not on this run's path.** It says the levelling "may be called before the split as well (e.g. `flow.py:1904` at run start)… otherwise the run dies before the split". `flow.py:1904` is inside `flow_batch` (the `--from-csv` sweep, `flow.py:1839`); `pdca flow 500 7` goes through `flow_ids` (`flow.py:1946-2064`) and `_drive_and_act`, which level with `waves.compute_waves` (`flow.py:1649`) and reach `partition_schedulable` only at `flow.py:1092`. The existing fixture patches it unconditionally on the ids path and the run still drives 7 (`test_flow_single_driver.py:285-288`). The conditional injection is harmless, but the stated reason is wrong for the scenario specified; correct it or drop the citation so Do does not chase a pre-split call that does not exist.
- [x] **Scope is wider than the issue's own suggested fix; confirm that is intended.** The issue asks for "One test: force `_reschedule` to return `None` … assert the rc, both stderr lines, and `assertNotIn("Traceback", err)`" — that covers M1 and M2 only. The brief adds Scenario B (a second failure path, a second injection seam) to kill M3. This is defensible — the issue title counts three mutants, and by the brief's own account M3 is the only one still surviving the full suite — but it is a second test on a different code path (`_real` / `_warn_stranded_split_children`), not the one test the thread proposed. No drive-by production change or refactor found; the out-of-scope list is explicit.

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
- By / date: Eduard Ralph / 2026-09-30

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 5 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
