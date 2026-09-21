Review issue #498: prevent concurrent CLI flows from driving the same bundle and make split-accept instructions reflect whether a live flow will drive the children.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The refusal, implicit exclusion, lifetime, and hint requirements are falsifiable; the accepted scope explicitly leaves independent Plan writes unfenced (brief.md:17; brief.md:163; target/docs/07-crosscutting.md:484). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing the production changes produced 17 assertion failures in 22 tests, including a second process driving a held bundle and the incorrect in-flow instruction (target/template/tests/test_flow_single_driver.py:394; review-red.log). |
| C3 Change | FAIL | A split accepted after its parent's adoption read but before the wave is marked passed still promises automatic driving, leaving both children PLANNED; criterion (v) remains violated (target/template/src/pdca_harness/flow.py:1619; target/template/src/pdca_harness/drive_claim.py:328; review-hint-race.log:8). |
| C4 Verification (red→green) | PASS | The asserted regression suite independently changed from 17 failures to 22 passing tests after restoring the patch; this verifies the tested cases, but misses the additional C3 interleaving (review-green.log:3; gate-logs/C4-verify.log:10). |
| C5 Causal adequacy | PASS | Exclusive OS locks address concurrent driving itself, fail closed, and release on scope exit; the real-process regressions exercise that cause. No capability probe masking a load-time side effect was added (target/template/src/pdca_harness/drive_claim.py:183; target/template/src/pdca_harness/drive_claim.py:245; target/template/tests/test_flow_single_driver.py:394). |
| T1 Structure | PASS | Ownership has a run-scoped lifecycle and stays outside bundle state; existing lock primitives are reused, with claims threaded through all CLI drive routes (target/template/src/pdca_harness/cli.py:574; target/template/src/pdca_harness/flow.py:1271; target/template/src/pdca_harness/flow.py:1766). |
| T2 Shape | PASS | Independently rerun docs lint, 22-page site rendering/internal-link audit, and diff whitespace checks passed; frozen host-parity evidence agrees (target/.github/workflows/docs-check.yml:35; gate-logs/T2-docs.log:10; gate-logs/host-ci-docs.log:10). |
| T3 Runtime | PASS | Independent driver suite: 1,943 tests, two skips, success. Frozen root-suite evidence shows 24 passing tests including render/update cases; local root rerun lacked importable Copier, a host limitation rather than evidence of a defect (review-suite.log:1656; review-root.log:6; gate-logs/T3-suite.log:38). |
| T4 Contribution | N/A | Contribution artifacts are deliberately absent at Check; the substantive contribution audit is deferred to its mandatory publish rerun (gate-logs/T4-contribution.log:10). |
| T5 Judgment | NEEDS-HUMAN | Confirm the affected-path merged/closed/rejected-work comparison remains sufficient — the brief records that search, but this target contains only one synthetic base commit and no remote, so its semantic prior-art conclusion cannot be independently settled here (brief.md:139; target/template/docs/INTEGRATION.md.jinja:83). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether protection limited to CLI driving meets the operational need despite unfenced Plan/single-step writes and the reproduced false assurance in C3 — passing regressions alone do not establish safe operator guidance (target/docs/07-crosscutting.md:484; target/template/src/pdca_harness/cli.py:886; review-hint-race.log:8). |

**Finding — P2: the adoption hint stays affirmative after the parent's last adoption read.**

`_adopt_split_children` reads each parent at `target/template/src/pdca_harness/flow.py:1268`, but `_past_adoption` only stamps the wave after the entire adoption pass returns (`target/template/src/pdca_harness/flow.py:1619`). During that interval, a separate shell can accept a split of a parent already examined. Its claim remains locked and unmarked, so `drives_children` returns true (`target/template/src/pdca_harness/drive_claim.py:328`). The caller tells the operator not to start another flow, although this run will never revisit that parent for adoption. Processing other parents or rescheduling their children can extend this interval.

I reproduced this with the patch applied: a real `cli._flow` reaches the adoption pass after an unanswered sign-off; a wrapper calls the real `_adoptable`, then runs a real split-accept subprocess before returning its already-read result. The split succeeds and prints “will drive the children (601 602) — do not start another flow for them”; the flow subsequently returns with both children `PLANNED`. The wrapper controls scheduling only: it does not replace the claim, hint, split, or adoption decision. This is an in-scope cross-shell hint failure, not a request to fence all Plan writes.

Reproduce from this review directory:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/target/template/src" python3 review-hint-race.py
```

The runnable probe is `review-hint-race.py`; observed output is `review-hint-race.log:8` and `review-hint-race.log:10`. Coordinate the per-parent adoption boundary with the hint decision so a split accepted after that parent's last read cannot receive an automatic-driving promise; add this interleaving to the regression coverage.

Independent verification used the disposable target only. Production changes were stashed while the new tests remained, then restored successfully; reverse-apply validation confirms the supplied patch is still applied. There is no target-state caveat. The production-import scanner passed independently. The frozen C4 log reports the same 17-failure/22-pass result; the C5, T2, host-parity, T3, and deferred T4 logs were also inspected. The local missing-Copier result does not leave the dependency globally undischarged: the frozen T3 log explicitly records execution and success of those render/update tests.

The affected-path history investigation returned only `bdc913c pre-fix base 70ea12b0e60f6cea4c604a0c2777240760ba11f3`; `git remote -v` returned nothing. The brief documents path-based merged history and closed-unmerged PR checks, but supplies no independently inspectable closed/rejected-work record. The available INTEGRATION template leaves its project-specific human-only list as TODO (`target/template/docs/INTEGRATION.md.jinja:80`). No additional project-specific items can be inferred from that scaffold.

This review is advisory; it does not gate acceptance.
