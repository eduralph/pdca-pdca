# Result — issue 459 / split-convergence-report

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: 
- Success criterion: (a) **both** acceptance paths emit the report before anything irreversible happens:
      `pdca split <id> --accept` (the auto-filing branch, which reaches `preflight` at
      `cli.py:733`) **and** `pdca split <id> --accept --ids a,b` (which calls
      `split.accept` directly at `cli.py:764` and never reaches `preflight` today). The
      `--ids` path is the one the docs call *required* for a tracker `pdca` cannot reach
      (`docs/07-crosscutting.md:192-197`) — i.e. the operator who has already paid for the
      issues by hand and most needs the verdict. Reproduced on the rejected attempt:
      `pdca split 500 --accept --ids 601,602` materialised both children and printed nothing
      but `issue_500 marked split; run `pdca flow 601 602``;
  (b) the report names, per staged child, its structural band against the parent's and which
      feature carries its score — `SizeEstimate.reasons` already carries this — and says
      plainly when the split does not lower the band for most children;
  (c) it is **not blinded by child-2's exclusion.** A `Conflicts with` edge *between*
      siblings is the splitter's statement that those two children edit a shared resource
      (`leaves.py:1274` calls those fields "the point"), so a proposal whose children all
      conflict pairwise is a split that separated nothing, and must be reported as NOT
      converged. The report therefore reads child-2's exposed sibling-conflict count rather
      than seeing an excluded 0 and reading the proposal as clean;
  (d) **its own output can never abort the acceptance.** A stderr that fails part-way — what
      `pdca split 500 --accept 2>&1 | head` produces — must not change the exit code or the
      set of bundles created. On the rejected attempt a `BrokenPipeError` from the second
      report line escaped `preflight` and produced either an unhandled traceback or the
      flatly *wrong* `split: issue_500 has no split-proposal.md — run `pdca split 500`
      first` with rc 1 on a bundle whose proposal was fine, because `cli.py:726-737` wraps
      `preflight` in an `except OSError` that means "no proposal". Guard these writes the way
      `cli.py:755-762` already guards
      its own (`except OSError: pass`), and cover it with a test that fails the stream;
  (e) it is **advisory and deterministic**: it never blocks, never prompts, and never
      changes what is filed or materialised — matching the size guard's warn-only stance and
      the same calibration argument (`plan_policy.py:88-102`).
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: 

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: Fixed
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: pass — C4 PASS: red without the fix, green with it
- C5 Causal adequacy: none — reviewer + human sign-off

## 4. Conformance (Check — stack)
- T1 Structure: none — (no gate configured)
- T2 shape: docs lint + site render link audit: pass — render_site: link audit OK
- T3 runtime: render/update-compat + offline driver suites: pass — == T3: root suite OK, driver suite OK
- T4 PR body has a user-impact opener + tracker id in both artifacts: pass — ./scripts/pdca contribcheck
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Task under review: make both `pdca split --accept` paths report whether staged children converge before filing or materialising them, without allowing advisory output failures to alter acceptance.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief defines both acceptance paths, per-child evidence, pairwise-conflict handling, advisory semantics, exact scope, and a runnable falsifier. |
| C2 Reproduction (red pre-fix) | PASS | With the shipped test retained on folded base `9bc0c94`, all 12 tests ran and the pre-fix leg was red (2 failures, 9 errors), including absence of the report on both paths (`template/tests/test_split_convergence.py:92`). |
| C3 Change | PASS | The patch is one scoped change: both CLI shapes reach preflight before filing/acceptance, and staged children use the production estimator (`patch.diff:36`; `patch.diff:126`). |
| C4 Verification (red→green) | FAIL | Although the asserted suite is 12 red → 12 green, a persistently broken stderr raises `OSError` after both bundles are created: the fake fails only once (`patch.diff:298`) and the later status write remains unguarded (`template/src/pdca_harness/cli.py:830`), so criterion (d)'s unchanged exit code is false. |
| C5 Causal adequacy | NEEDS-HUMAN | Decide whether folded dependency #457 must be required so the capability probe can be removed — the `getattr` fallback masks prerequisite/order drift in code intended to run with `sibling_conflicts` present (`patch.diff:166`). |
| T1 Structure | PASS | The target HEAD is stale relative to #457, but the patch applies cleanly to folded base `9bc0c94`; `py_compile` and whitespace checks pass, making this an ordering caveat rather than a patch-application defect. |
| T2 Shape | PASS | Docs lint and the 22-page site render/link audit pass for the new split contract (`docs/07-crosscutting.md:209`). |
| T3 Runtime | NEEDS-HUMAN | Provide importable `copier` and rerun the seven root render/update-compat tests — it was absent and all seven skipped, so the green evidence rests on the passing offline suite rather than a real template render (`tests/test_render_and_run.py:31`). |
| T4 Contribution | NEEDS-HUMAN | Confirm the final commit message and PR description carry the #459 reference and user-impact opener — those artifacts were not supplied, so the recorded contribcheck pass cannot be independently reproduced. |
| T5 Judgment | PASS | Affected-path checks across merged history and the closed/rejected PR corpus found no closed-unmerged or already-merged convergence implementation; issue #459 remains open and the patch stays within one logical fix. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether to iterate before shipping — the pre-filing warning addresses irreversible issue creation, but the confirmed persistent-pipe failure means the promised advisory-only behavior is not yet met. |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] C5 Causal adequacy — Decide whether folded dependency #457 must be required so the capability probe can be removed — the `getattr` fallback masks prerequisite/order drift in code intended to run with `sibling_conflicts` present (`patch.diff:166`).
- [ ] T3 Runtime — Provide importable `copier` and rerun the seven root render/update-compat tests — it was absent and all seven skipped, so the green evidence rests on the passing offline suite rather than a real template render (`tests/test_render_and_run.py:31`).
- [ ] T4 Contribution — Confirm the final commit message and PR description carry the #459 reference and user-impact opener — those artifacts were not supplied, so the recorded contribcheck pass cannot be independently reproduced.
- [ ] Validation — fitness-to-purpose — Decide whether to iterate before shipping — the pre-filing warning addresses irreversible issue creation, but the confirmed persistent-pipe failure means the promised advisory-only behavior is not yet met.

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: iterated-to-Do
- Iteration delta (if iterating): Reviewer C4 FAIL: criterion (d) is not fully met. A persistently broken stderr still raises OSError after both bundles are created — the later status write at template/src/pdca_harness/cli.py:830 is unguarded — so the advisory report can change the exit code. The shipped test masks this: its fake stderr fails only once (fail_at counter), while a real broken pipe raises on every write. Next attempt: guard ALL stderr writes on the acceptance path (cli.py:830 and any others) the same way as the existing except-OSError guards, and strengthen the test's fake stream to fail persistently (raise on every write from the first failure on), asserting the exit code and created-bundle set are unchanged.
- By / date: Eduard Ralph / 2026-08-10

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
