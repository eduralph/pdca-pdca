# Result — issue 434 / red-leg-zero-tests-unverifiable

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: In plain terms: the check that is supposed to prove a fix works can pass
  when the test never ran at all.

  Here is how. Every project's C4 gate proves a fix twice. Once with the fix in — the test
  must pass. Once with the fix taken back out — the test must now fail, which is what proves
  the test is really catching this bug and not something else. That second run is the one at
  issue.

  To decide whether that second run "failed", the gate looks at the exit code of the test
  runner. But a test runner exits non-zero for two very different reasons: the test ran and
  failed (good — that is the proof we want), or the test never built and so never ran at
  all (no proof of anything). The gate cannot tell those apart, so it treats both as "the
  test failed without the fix" and reports **PASS**. A bundle whose test never even compiled
  gets recorded as proof that its test catches the bug.

  Four possible outcomes; only the last one is wrong:

  | test runner exited | tests that actually ran | verdict today | verdict it should give |
  |---|---|---|---|
  | 0 | none | UNVERIFIABLE | UNVERIFIABLE (already right) |
  | 0 | some | FAIL — passes without the fix | FAIL (already right) |
  | non-zero | some | PASS | PASS (already right) |
  | **non-zero** | **none** | **PASS** | **UNVERIFIABLE** |

  This is not a hypothetical corner. Taking the fix back out also removes any new function
  the fix added — so if the test calls one of those new functions, it cannot build, and we
  land in the bad row. That is an everyday shape for a fix. It already happened for real:
  getwyrd/wyrd-pdca recorded "PASS — red without the fix" for a bundle whose test never
  compiled, and had to patch its own copy of the gate on 2026-08-02.

  **One thing the issue gets wrong, worth knowing before you read the rest.** The issue says
  the buggy script is shipped by the harness and so every project has the same bug. Half
  right. The file *is* copied into every project untouched (`copier.yml:14` sets
  `_templates_suffix: .jinja`, so a file without that suffix is copied as-is). But what the
  harness copies is an **empty outline** — it prints "not yet implemented for this project"
  and stops (`template/engine/scripts/run-verify.sh:53-60`). Each project writes the real
  gate itself, following the written instructions in that outline's header comment
  (`:35-52`). Those instructions never mention "did any test actually run?", so every
  project that follows them writes the same bug. So the thing to fix here is the
  **instructions**, not a script. That is a different fix from the one the issue imagines —
  see Scope, and §Settled at Plan at the bottom.
- Success criterion: On `eduralph/pdca-harness` @ `main`, a new test file
  `template/tests/test_verify_red_leg.py` fails before the change and passes after it. What
  it checks: the instructions in `template/engine/scripts/run-verify.sh` now tell a project
  to decide the second run's verdict from **two** things — the runner's exit code *and*
  whether any test actually ran — and say plainly that if no test ran, the answer is
  `PDCA-UNVERIFIABLE` / exit 77 (which sends it to SUMMARY §6 for a human to look at),
  never PASS. That holds whether the runner exited 0 or non-zero.

  Everything the criterion needs is inside `template/`, so the C4 gate can prove it from the
  patch alone. No fork CI, no whole-suite run.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: Fix the instructions the harness publishes so a project following them cannot
  report PASS for a run in which no test executed. The instructions must:
  - decide the verdict from both the runner's exit code and whether any test ran;
  - say explicitly that "runner exited non-zero **and** no test ran" is
    `PDCA-UNVERIFIABLE` (exit 77), not PASS;
  - keep that case distinguishable from "runner exited 0 and no test ran" — the two have
    different causes and need different things from the human reading §6;
  - live where someone writing their gate will actually read them, and be held in place by
    a test so the wording cannot quietly rot.

  `template/engine/README.md.jinja` §"The two gate shapes that matter" can carry the longer
  explanation.

  **How** a project ends up enforcing this — wording alone, or wording plus a small reusable
  snippet under the `engine/scripts/lib/` convention the README already documents
  (`template/engine/README.md.jinja:16-21`) — is Do's call; the criterion works either way.
  Either way the `.sh` file has to be a real part of the diff (see Falsifiability).

  Out of scope: writing an actual working gate inside the outline (it stays an outline —
  that is the point of it); touching `gates.py`'s exit-77 handling (already correct,
  #329/#428); auditing or fixing **this** project's own copy of `engine/scripts/run-verify.sh`
  — different repository, and per `docs/INTEGRATION.md` §2 that is an ordinary pdca-pdca PR
  outside the cycle; fixing getwyrd/wyrd-pdca (already done there — this is the fix being
  routed upstream).

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: unverifiable — ` marker -> §6 NEEDS-HUMAN, non-gating — the
- C5 Causal adequacy: none — reviewer + human sign-off

## 4. Conformance (Check — stack)
- T1 Structure: none — (no gate configured)
- T2 shape: docs lint + site render link audit: pass — render_site: link audit OK
- T3 runtime: render/update-compat + offline driver suites: fail — == T3: root suite OK, driver suite FAILED (rc 1)
- T4 PR body has a user-impact opener + tracker id in both artifacts: pass — pdca-pdca contribcheck
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Review of issue #434: prevent verification instructions from treating a non-zero runner exit with zero executed tests as a valid red-leg PASS.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The acceptance decision is unambiguous: every verification leg must distinguish runner status from executed-test count, with either zero-test outcome routed to unverifiable; the target publishes that complete four-outcome contract at `template/engine/scripts/run-verify.sh:47`. |
| C2 Reproduction (red pre-fix) | PASS | The reproduction earns evidence rather than an import/collection accident: in a disposable target copy with only the two changed published files reverted, all 11 retained regression tests executed and failed on assertions beginning at `template/tests/test_verify_red_leg.py:90`. |
| C3 Change | PASS | The scope decision remains the Plan-settled instructional fix: the patch changes the shipped outline and its explanatory README, while the outline remains deliberately non-executable at `template/engine/scripts/run-verify.sh:84`. |
| C4 Verification (red→green) | PASS | Independent focused runs executed 11 tests in both states: all 11 failed without the two published-wording changes and all 11 passed with them, grounding the criterion in `template/tests/test_verify_red_leg.py:100`; the recorded gate's unverifiable row is not treated as affirmative evidence. |
| C5 Causal adequacy | PASS | The root-cause decision is adequately discharged because the contract now requires an independently parsed execution count rather than adding a capability probe or runtime symptom guard (`template/engine/scripts/run-verify.sh:47`). |
| T1 Structure | PASS | The structural decision matches the repository's existing contract-test pattern: the new standard-library test locates the shipped outline and rendered/template README variants at `template/tests/test_verify_red_leg.py:32`. |
| T2 Shape | NEEDS-HUMAN | Decide whether the recorded docs-lint/link-audit PASS is sufficient for sign-off — its project-specific `run-docs-check.sh` oracle was not present in the supplied review environment, so I could not independently reproduce that gate; the Markdown table itself is well-formed at `template/engine/README.md.jinja:54`. |
| T3 Runtime | NEEDS-HUMAN | Decide whether the recorded advisory driver-suite failure is unrelated/pre-existing or must be resolved — the exact `run-suite.sh` oracle was unavailable, while the independently runnable full template unittest discovery passed, including the new test at `template/tests/test_verify_red_leg.py:65`. |
| T4 Contribution | NEEDS-HUMAN | Decide whether to rely on the recorded contribution PASS — the PR-body artifacts and contribcheck oracle were not among the reviewer inputs, so tracker/opener compliance could not be independently reproduced; issue linkage is present in the test at `template/tests/test_verify_red_leg.py:2`. |
| T5 Judgment | PASS | The acceptance judgment has no unresolved implementation defect: affected-path history contains no prior implementation of the zero-tests verdict rule, tracker search found only complementary merged/closed work, and the decisive no-evidence invariant is explicit at `template/engine/scripts/run-verify.sh:72`. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether instructional enforcement is sufficient for real project authors and runners — the automated checks prove the published contract's wording, but only human sign-off can judge whether it will reliably prevent projects from converting zero executed tests into acceptance evidence (`template/engine/README.md.jinja:44`). |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T2 Shape — Decide whether the recorded docs-lint/link-audit PASS is sufficient for sign-off — its project-specific `run-docs-check.sh` oracle was not present in the supplied review environment, so I could not independently reproduce that gate; the Markdown table itself is well-formed at `template/engine/README.md.jinja:54`.
- [x] T3 Runtime — Decide whether the recorded advisory driver-suite failure is unrelated/pre-existing or must be resolved — the exact `run-suite.sh` oracle was unavailable, while the independently runnable full template unittest discovery passed, including the new test at `template/tests/test_verify_red_leg.py:65`.
- [x] T4 Contribution — Decide whether to rely on the recorded contribution PASS — the PR-body artifacts and contribcheck oracle were not among the reviewer inputs, so tracker/opener compliance could not be independently reproduced; issue linkage is present in the test at `template/tests/test_verify_red_leg.py:2`.
- [x] Validation — fitness-to-purpose — Decide whether instructional enforcement is sufficient for real project authors and runners — the automated checks prove the published contract's wording, but only human sign-off can judge whether it will reliably prevent projects from converting zero executed tests into acceptance evidence (`template/engine/README.md.jinja:44`).
- [x] C4 fix verified: bundle test red pre-fix, green post-fix unverifiable — ` marker -> §6 NEEDS-HUMAN, non-gating — the

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
- By / date: Eduard Ralph / 2026-08-05

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
- Sync this project's `src/pdca_harness/gates.py` with upstream: its marker scan (`:443`) still matches `PDCA-UNVERIFIABLE:` mid-line, so relayed child output overrides a real verdict — fixed upstream by #428 (declaration must start the line); it turned #434's rc-0 C4 PASS into a false `unverifiable`.
