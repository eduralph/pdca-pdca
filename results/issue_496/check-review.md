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
