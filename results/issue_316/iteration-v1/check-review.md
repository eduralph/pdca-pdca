Reviewing issue #316: add `pdca triage` to ingest external PR-review findings, classify and route them, and register recurrence signals in the Act ledger.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The contract is bounded to one verb with observable pull, four-class classification, routing, registration, and recurrence outcomes, and the shipped oracle exercises those outcomes at `template/tests/test_triage.py:137`. |
| C2 Reproduction (red pre-fix) | PASS | A clean `HEAD` snapshot with only the shipped test fails at the triage import (`template/tests/test_triage.py:28`), establishing the absent-command baseline. |
| C3 Change | FAIL | The required “register every finding” outcome is not recoverable: after a held Act lock, the prescribed rerun returns on “no new findings” before registration, leaving the ledger permanently empty (`template/src/pdca_harness/triage.py:448`). |
| C4 Verification (red→green) | PASS | Independently reproduced red on clean `HEAD` and green with the patch: all 15 shipped triage tests pass, including the command-level path at `template/tests/test_triage.py:288`. |
| C5 Causal adequacy | FAIL | “Every finding” is not closed for large PRs: each endpoint is requested once with `per_page=100` and without pagination, so later reviews/comments are silently omitted (`template/src/pdca_harness/triage.py:422`). |
| T1 Structure | PASS | The additive engine is isolated behind the existing CLI, Config, split, rubric, and Act boundaries, with production behavior kept in `template/src/pdca_harness/triage.py:405`. |
| T2 Shape | PASS | Docs lint and the 22-page link audit rerun cleanly, and the optional model hook remains disabled by default at `template/src/pdca_harness/config.py:350`. |
| T3 Runtime | FAIL | Despite 1,329 offline tests and all 7 Copier render/update tests passing, a direct lock-contention run returns 1 then 0 while the ledger stays absent because the recovery path is unreachable (`template/src/pdca_harness/triage.py:497`). |
| T4 Contribution | NEEDS-HUMAN | Confirm no closed/rejected PR touching the five affected paths already implements this feature — merged `origin/main` path/history searches were clear and the contribution gate passed, but invalid `gh` authentication prevented the required closed/rejected-work check, so duplicate contribution risk remains. |
| T5 Judgment | NEEDS-HUMAN | Approve whether class-plus-first-keyword is a sufficiently stable recurrence identity — synonyms such as `crash` and `crashes` create distinct signals (`template/src/pdca_harness/triage.py:76`), which can hide a semantically repeated miss. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the four-way heuristic precedence and proposed routes fit the project’s operational review policy — live GitHub API/auth and irreversible tracker filing were not exercised, so evidence rests on the canned topology around `template/tests/test_triage.py:34`. |
