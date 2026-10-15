Review issue 672: prevent a finished bundle skipped during the pre-wave carry from reaching the integration line through another finished branch, before the carry's sole push.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The requested invariant, declared/undeclared containment cases, push count, and exclusions are falsifiable; the base-relative invariant remains the review standard (`brief.md:10`, `brief.md:16`, `brief.md:22`). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only the production changes leaves the new tests executable and produces 14 assertion failures in 36 tests, including both specified leak cases (`review-red.log:227`; `target/template/tests/test_flow_resume_stack_prereqs.py:532`). |
| C3 Change | PASS | The four changed files address carry admission, fold behavior, its documentation, and regression coverage; ordinary folds retain their first-failure behavior (`target/template/src/pdca_harness/integrate.py:586`, `target/template/src/pdca_harness/flow.py:1121`). |
| C4 Verification (red→green) | PASS | Restoring the production patch passes all 36 carry tests, independently matching the frozen red→green evidence; this verifies the shipped tests, not the uncovered case below (`review-green.log:3`, `gate-logs/C4-verify.log:10`). |
| C5 Causal adequacy | NEEDS-HUMAN [impl] | Preserve a skipped bundle's own earlier work when its recorded build line contains that work, and add a regression — subtracting that entire line lets skipped P's original commit reach a fresh line through Q and lets D build (`target/template/src/pdca_harness/integrate.py:983`, `review-recorded-base.log:12`, `review-recorded-base.log:17`). |
| T1 Structure | PASS | Containment decisions and local retries occur under the existing integration lock before the push; each retry permanently excludes another previously merged bundle, bounding termination (`target/template/src/pdca_harness/integrate.py:500`, `target/template/src/pdca_harness/integrate.py:616`, `target/template/src/pdca_harness/integrate.py:660`). |
| T2 Shape | PASS | Independently rerun docs lint, 22-page render/link audit, and diff whitespace check pass; the frozen host-CI parity log corroborates the same docs checks (`review-docs-lint.log:1`, `review-docs-render.log:3`, `gate-logs/host-ci-docs.log:10`). |
| T3 Runtime | PASS | The independent offline suite passes 2,477 tests with two skips; root render/update coverage is supported by the frozen 24-test pass, since this interpreter lacks Copier (`review-suite.log:1817`, `gate-logs/T3-suite.log:54`, `review-root-suite.log:6`). |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the substantive audit is deferred to its required publish-time rerun (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Accept or revise the conservative holds for shared history, including whole-target holds on an existing line, and confirm path-based merged/closed-work prior art — these affect recovery and duplicate-work risk; the disposable target contains only a synthetic base commit and no remote (`target/docs/07-crosscutting.md:750`, `review-prior-art.log:1`, `brief.md:27`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the eventual corrected behavior and its recovery costs satisfy resumed-stack users — the shipped examples pass, but the independently reproduced earlier-work leak prevents treating the stated invariant as established (`target/docs/07-crosscutting.md:729`, `review-recorded-base.log:12`, `review-recorded-base.log:17`). |

The C5 finding is an observed leak of P's own work, not merely an attribution disagreement about another prerequisite's commits. The reproduction uses the existing real-git fixture and its recorded-line publication helper (`target/template/tests/test_flow_resume_stack_prereqs.py:725`):

1. Publish P's original commit `p1` and fold P onto an earlier integration line L.
2. Rebuild P on L with a later change to `base.txt`; publish Q on L with an unrelated file. Both record L as their build base.
3. Change `base.txt` differently on main, then delete the earlier integration line so the carry starts fresh.
4. Request P, Q, and D, where D depends on Q. P conflicts and is skipped. Q merges with `p1`, D builds, and the carry pushes once. `p1` is absent from main but present on the resulting line.

`_work` removes every ancestor of the recorded cut, explicitly including the same bundle's earlier head (`target/template/src/pdca_harness/integrate.py:978`). Consequently `p1` never enters the excluded-work set. This contradicts `brief.md:16`, which excludes every commit of the skipped branch over the base; the new documentation narrows that invariant at `target/docs/07-crosscutting.md:731`. Retain the bundle's own earlier contribution in that set, or obtain an explicit Plan-level revision of the invariant; documenting the exemption alone does not satisfy the current brief.

Run the independent failing probe from this review directory:

```bash
TMPDIR="$PWD/review-tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/target/template/src" python3 review-recorded-base.py
```

It exits 1 on the fresh-line assertion. Its continued-line control carries P successfully and is not a defect; the finding is the fresh-line case beginning at `review-recorded-base.log:10`.

The production-path scanner was rerun, but it only checks newly added test files; this patch extends an existing file, so its success is vacuous (`gate-logs/C5-prod-path.log:10`). Direct inspection and execution establish that the tests invoke real `flow._drive_and_act` and `integrate.fold`, with real git repositories and merges (`target/template/tests/test_flow_resume_stack_prereqs.py:123`). The host PR responses and build leaves are stubbed; the forbidden git topology itself is exercised and demonstrably fails before the fix. No missing git/Python dependency or capability-probe symptom guard was found.

The local root-suite limitation is a host caveat, not a patch failure: its runner correctly exits 77 for unavailable Copier library coverage. The frozen log actually executes the render/update cases successfully. Prior-art evidence is less complete: the brief names merged and closed-unmerged work by production/docs paths, but no independently inspectable history or closed-PR evidence is supplied, and its entry does not cover the changed test file. The T5 decision therefore remains open. The supplied integration template's human-only list is unfilled (`target/template/docs/INTEGRATION.md.jinja:80`), so it supplies no additional enumerated decision.

The target was restored after the stash/pop experiment, and its final binary diff matches `patch.diff` byte for byte. No production or test source was edited. All independent evidence and the probe reside in the harness review directory.

<!-- pdca:leaf-complete -->
