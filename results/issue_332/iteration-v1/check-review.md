Task under review: implement issue #332 auto-iterate soft/hard budgets, reviewer `[impl]` promotion, deferred HUMAN ledger, Validation-row normalization, and the folded #335 ledger-retirement fix.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief defines the five required behaviours and folded #335 retirement invariant, with no blocking external dependency declared in `brief.md:10`. |
| C2 Reproduction (red pre-fix) | PASS | Reversed implementation plus patched tests failed 17 failures / 43 errors, including missing `soft_auto_iters`, `LEDGER_FILE`, and `budget_verdict`; patched regression coverage is grounded in `template/tests/test_autoiterate.py:947`. |
| C3 Change | PASS | The change covers the decision path from classification through budget gating and ledger persistence, so the human decision is whether this feature scope matches #332 rather than whether a named component is absent; see `template/src/pdca_harness/flow.py:270`. |
| C4 Verification (red->green) | PASS | Red was reproduced in `/tmp/pdca-review-red`; green was reproduced with `PYTHONPATH=src python3 -m unittest tests.test_autoiterate` and `tests.test_size_signal`, plus full `unittest discover`, with core checks at `template/tests/test_autoiterate.py:1033`. |
| C5 Causal adequacy | PASS | The fix removes the taxonomy-proxy veto and persists deferred human findings instead of guarding around a present capability, so the root-cause decision is covered by `template/src/pdca_harness/autoiterate.py:75`. |
| T1 Structure | PASS | The implementation keeps separate builder and human carry-forward channels, which is the structural decision that prevents deferred judgments from being handed to Do; see `template/src/pdca_harness/autoiterate.py:181`. |
| T2 Shape | NEEDS-HUMAN | The exact `./engine/scripts/run-docs-check.sh` wrapper is absent from `$PDCA_TARGET`, so the docs-render/link-audit PASS in `check-gates.json` is provisional despite `git diff --check` passing. |
| T3 Runtime | PASS | The frozen T3 non-gating failure was not reproduced: full `PYTHONPATH=src python3 -m unittest discover -s tests` passed against `$PDCA_TARGET`, with the #335 drain/protection cases at `template/tests/test_autoiterate.py:1116`. |
| T4 Contribution | NEEDS-HUMAN | The exact `pdca-pdca contribcheck` tool is absent from `$PDCA_TARGET`, so the tracker/PR-body PASS in `check-gates.json` needs human confirmation before relying on it. |
| T5 Judgment | PASS | Prior-art search by affected paths plus GitHub issue search found #332/#335 as the live requested work and older #293/#324/#334 as related prerequisites, not an already-landed duplicate; see `template/src/pdca_harness/state.py:113`. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Human sign-off must decide whether auto-deferring human findings is operationally acceptable, because even with green runtime tests this changes when reviewers are interrupted; see `template/src/pdca_harness/autoiterate.py:237`. |
