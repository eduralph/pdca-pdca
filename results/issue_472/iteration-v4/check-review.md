Review of the mid-run split-adoption core: make one `pdca flow` call schedule, drive, budget, and report newly split children without widening beyond the driven lineage.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The behavioral boundary is decidable: adopt only mid-run lineage children, keep terminal-parent recovery out of scope, and preserve loud held-child continuation (`docs/07-crosscutting.md:243`). |
| C2 Reproduction (red pre-fix) | PASS | With only production hunks reversed, all 25 tests executed and 24 failed, including children remaining non-terminal where the criterion requires COMPLETE (`template/tests/test_flow_adopt_split.py:333`). |
| C3 Change | PASS | The patch stays within the adoption core and its declared documentation/test cleanup: it re-waves only the un-driven tail and explicitly preserves the terminal-parent boundary (`template/src/pdca_harness/flow.py:1105`). |
| C4 Verification (red→green) | PASS | After restoring the patch, all 25 focused tests passed; the 1,658-test offline driver suite passed (2 skipped), all 7 Copier render/update tests passed, and the docs link audit passed (`template/tests/test_flow_adopt_split.py:322`). |
| C5 Causal adequacy | PASS | The frozen-schedule cause is removed by splicing the recomputed tail into the live list iterator, with no capability probe or downstream symptom guard (`template/src/pdca_harness/flow.py:1114`). |
| T1 Structure | PASS | Adoption is composed once into the shared `_drive_and_act` path, so every CLI shape inherits the same scheduling, integration, publishing, and budget machinery (`template/src/pdca_harness/flow.py:1256`). |
| T2 Shape | PASS | `git diff --check` and the rendered-site link audit passed, and the operator contract consistently describes lineage scope, held children, and the shared pool (`docs/07-crosscutting.md:257`). |
| T3 Runtime | PASS | Independent execution passed the focused 25 tests, the full 1,658-test driver suite, and all 7 root render/update-compat tests under the Copier interpreter (`template/tests/test_flow_adopt_split.py:346`). |
| T4 Contribution | NEEDS-HUMAN | Release-text approval is owed — `commit-msg.txt` and `pr-description.md` were not supplied, so the recorded checker pass cannot be rerun and the user-impact opener plus #472 linkage remain unaudited (`template/pdca.toml.jinja:960`). |
| T5 Judgment | PASS | The contribution remains one logical feature and affected-path checks found prerequisite PR #470 already merged at the target, with no open or closed-unmerged competing implementation (`template/src/pdca_harness/flow.py:787`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Ship-or-iterate approval is owed — the human must decide whether same-call lineage adoption with loud, results-excluded holds is the right operator contract because that product trade-off determines fitness (`docs/07-crosscutting.md:257`). |
