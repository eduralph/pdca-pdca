Task under review: retain a Claude leaf's marked terminal-error account in its post-mortem output without changing retry classification, raw capture, or ownership attribution.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The acceptance boundary is explicit and falsifiable: preserve marked evidence with correct ownership and precedence while leaving retry and capture semantics unchanged (`template/tests/test_terminal_error_retention.py:218`). |
| C2 Reproduction (red pre-fix) | PASS | Reverting only the production hunk independently produced 23 behavioral failures, including the missing-report artifact assertion at `template/tests/test_terminal_error_retention.py:221`. |
| C3 Change | PASS | Scope stays within the stipulated stream reader plus its new tests/fixtures, so the diagnostic reaches the existing failure-output contract without altering downstream classification (`template/src/pdca_harness/progress.py:302`). |
| C4 Verification (red→green) | PASS | Independent execution was red with 23 failures before the production change and green with all 34 focused tests after restoration; the broader offline suite also passed 1,792 tests (`template/tests/test_terminal_error_retention.py:221`). |
| C5 Causal adequacy | PASS | The drain now retains the already-read marked event directly, with no capability probe, fallback guard, or retry-policy change that could mask an eager upstream cause (`template/src/pdca_harness/progress.py:197`). |
| T1 Structure | PASS | Decode, extraction, precedence, ownership, and bounded formatting are separated into focused helpers, keeping the hot-loop state transition auditable (`template/src/pdca_harness/progress.py:423`). |
| T2 Shape | PASS | `git diff --check`, docs lint, rendered-site link audit, and host-CI parity are clean, so the patch introduces no formatting or repository-shape defect (`template/src/pdca_harness/progress.py:530`). |
| T3 Runtime | PASS | Focused red→green, the complete offline suite, retry-count guards, raw-capture checks, and alternate-family degradation all pass (`template/tests/test_terminal_error_retention.py:368`). |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the substantive contribution audit is explicitly deferred to the mandatory publish-time rerun. |
| T5 Judgment | PASS | The affected-file prior-art record covers merged `progress.py` history and the closed/rejected #533/#506 attempts, with no unresolved overlap or semantic upstream lead for this isolated slice (`template/src/pdca_harness/progress.py:35`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether a real failed Claude leaf's retained main/sub-agent wording is truthful and operationally useful in `*.error.log` — offline red→green and binary-field confirmation establish mechanics, not post-mortem fitness (`template/tests/fixtures/README.md:48`). |
