Review of issue #475: ensure a C6-refused recorded accept never promises “no new session,” while truthful no-session notices and state transitions remain intact.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The operator-facing invariant is bounded and falsifiable: C6 refusal returns `"blocked"`, while only that outcome reopens sign-off (`template/src/pdca_harness/flow.py:176`, `template/src/pdca_harness/flow.py:263`). |
| C2 Reproduction (red pre-fix) | PASS | With the new test hunks retained and only production reverted, both single and batch assertions fail on the base’s false no-session claim (`template/tests/test_signoff_orphan.py:186`, `template/tests/test_signoff_orphan.py:262`; `gate-logs/C4-verify.log:16`). |
| C3 Change | FAIL | The change must distinguish a successfully applied action from repair outcomes: `REASSEMBLE`/`None` mean the decision was not recorded, but the broad non-`"blocked"` branch calls it “applied” (`template/src/pdca_harness/flow.py:127`, `template/src/pdca_harness/flow.py:253`). |
| C4 Verification (red→green) | PASS | Independent production-only stash/reapply reproduced two red failures then eight green tests, preserving fresh-session and state assertions on both drive paths (`template/tests/test_signoff_orphan.py:183`, `template/tests/test_signoff_orphan.py:258`; `gate-logs/C4-verify.log:52`). |
| C5 Causal adequacy | PASS | The contested cause is removed by deciding before announcing, with no capability probe or eager-load symptom guard; C6’s authoritative `"blocked"` result now suppresses the premature promise (`template/src/pdca_harness/flow.py:252`). |
| T1 Structure | PASS | The delta stays within the existing shared decision boundary and its existing owning test module, so both callers retain one outcome path (`template/src/pdca_harness/flow.py:223`, `template/tests/test_signoff_orphan.py:118`). |
| T2 Shape | PASS | Independent `git diff --check` is clean, and both frozen shape runs show clean docs lint/render/link audits (`gate-logs/T2-docs.log:16`, `gate-logs/host-ci-docs.log:15`). |
| T3 Runtime | PASS | Pure-stdlib compilation and the target’s full driver suite pass independently; frozen runtime evidence also records 1,758 passing tests with two skips (`gate-logs/T3-suite.log:1123`). |
| T4 Contribution | N/A | Contribution artifacts do not exist at Check by design; the substantive, non-skippable T4 audit reruns at publish (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | FAIL | Operator-facing truthfulness is not yet acceptable: a repair reports “decision not recorded” and the patched caller immediately reports “applied,” yielding mutually exclusive guidance (`template/src/pdca_harness/flow.py:127`, `template/src/pdca_harness/flow.py:254`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Human must decide whether the final post-outcome wording earns operator trust across successful, blocked, and repair paths — automated red→green evidence cannot own that product decision (`template/src/pdca_harness/flow.py:238`). |

Prior-art check: affected-path GitHub history identifies the recorded-decision work as the origin of these files, and a complete current scan of open plus closed-unmerged PR file lists found no competing or rejected attempt touching either affected path.
