Task under review: make `pdca split --accept` persist tolerant, mixed-role lineage records for every child and the parent without weakening split transactionality.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The contract is falsifiable across child, parent, mixed-role, tolerant-read, retention, and rollback outcomes, with executable assertions beginning at `template/tests/test_split_lineage.py:66`. |
| C2 Reproduction (red pre-fix) | PASS | On target HEAD with only the new test retained, all 14 tests error on absent `split.LINEAGE`/`split.read_lineage`, establishing the pre-fix gap through the module import at `template/tests/test_split_lineage.py:25`. |
| C3 Change | FAIL | A snapshot-read failure after child moves escapes the rollback block and leaves both children materialised while the parent remains open; the unprotected snapshot is at `template/src/pdca_harness/split.py:511`. |
| C4 Verification (red→green) | PASS | The focused module independently changed from 14 errors on target HEAD to 14 passes with the patch, exercising the acceptance path from `template/tests/test_split_lineage.py:68`. |
| C5 Causal adequacy | PASS | The missing provenance is addressed at its creation boundary by staging child records and merging the parent record, with no capability probe or symptom guard (`template/src/pdca_harness/split.py:426`). |
| T1 Structure | PASS | The change stays within the declared split module, one focused test module, and the existing split documentation section (`docs/07-crosscutting.md:217`). |
| T2 Shape | PASS | Docs lint and a 22-page site render/link audit both pass, and the documented mixed-role schema is grounded at `docs/07-crosscutting.md:220`. |
| T3 Runtime | NEEDS-HUMAN | Require a real Copier render/update-compat run before sign-off — `copier` is absent on this host, so all seven root tests skipped under guards such as `tests/test_render_and_run.py:31`, although the 1,613-test template suite passed with two unrelated skips. |
| T4 Contribution | NEEDS-HUMAN | Confirm the PR description and commit message carry the issue id and a user-impact opener — those contribution artifacts were not among the reviewer inputs, so the recorded green gate could not be independently reproduced. |
| T5 Judgment | NEEDS-HUMAN | Decide whether closed/rejected work contains preferable or conflicting prior art — affected-path merged history was checked and contains no earlier lineage implementation, but closed/rejected refs are unavailable locally. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether this independent-edge schema is the right durable interface for children 2–4 and #449 — mechanical behavior passes, but the intentionally out-of-scope consumers have not yet demonstrated fitness (`docs/07-crosscutting.md:223`). |
