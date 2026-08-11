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

Task under review: report split convergence for both `--accept` paths before irreversible work, without allowing advisory output failures to alter acceptance.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The decision point is explicit: operators must see child-versus-parent size evidence before either acceptance shape becomes irreversible, while acceptance remains advisory (`docs/07-crosscutting.md:209`). |
| C2 Reproduction (red pre-fix) | PASS | With the test retained and production hunks absent, 19 tests executed and failed (4 failures, 15 errors), including both pre-irreversibility path assertions and persistent broken-stream escapes (`template/tests/test_split_convergence.py:167`, `template/tests/test_split_convergence.py:317`). |
| C3 Change | PASS | The scoped change centralizes both paths through preflight before filing, stages estimates outside the instance, and guards all acceptance-path output; no unrelated production area changed (`template/src/pdca_harness/cli.py:767`, `template/src/pdca_harness/split.py:344`). |
| C4 Verification (red→green) | PASS | On the dependency-complete base, the same 19 tests went red→green and the full offline suite passed 1,719 tests; the set target and persisted integration ref are stale around #457, a target-state caveat rather than a patch failure (`template/tests/test_split_convergence.py:317`). |
| C5 Causal adequacy | NEEDS-HUMAN | Decide whether integration must guarantee #457 and remove the `getattr` capability fallback, or retain proposal-derived behavior when the prerequisite is absent — the probe can mask a broken dependency fold and change which sibling edges are trusted (`template/src/pdca_harness/split.py:387`). |
| T1 Structure | PASS | Temporary staging reuses the production materializer and the regression proves no instance artifact remains, preserving the preflight boundary (`template/src/pdca_harness/split.py:367`, `template/tests/test_split_convergence.py:381`). |
| T2 Shape | PASS | Documentation lint and the 22-page rendered-site link audit both passed, and the operator contract is placed in the existing split section (`docs/07-crosscutting.md:209`). |
| T3 Runtime | NEEDS-HUMAN | Install/import Copier and rerun the seven root render/update tests — 1,719 offline tests passed, but the root suite skipped every test, so rendered-template and `copier update` compatibility remain unexercised (`tests/test_render_and_run.py:31`, `tests/test_update_compat.py:232`, `tests/test_render_cli_name.py:52`). |
| T4 Contribution | NEEDS-HUMAN | Inspect or rerun `contribcheck` after `commit-msg.txt` and `pr-description.md` are available — those artifacts are not reviewer inputs, so the claimed opener and tracker-id result cannot be independently reproduced (`template/src/pdca_harness/cli.py:1101`). |
| T5 Judgment | PASS | Affected-path merged history was inspected and a paginated closed-PR file query found no unmerged/rejected PR touching any of the four affected paths, so no prior-art decision remains outstanding. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the report wording and fallback semantics give operators enough reliable evidence to reconsider a split at the last reversible point — this determines whether the advisory changes real acceptance decisions (`template/src/pdca_harness/split.py:444`). |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] C5 Causal adequacy — Decide whether integration must guarantee #457 and remove the `getattr` capability fallback, or retain proposal-derived behavior when the prerequisite is absent — the probe can mask a broken dependency fold and change which sibling edges are trusted (`template/src/pdca_harness/split.py:387`).
- [x] T3 Runtime — Install/import Copier and rerun the seven root render/update tests — 1,719 offline tests passed, but the root suite skipped every test, so rendered-template and `copier update` compatibility remain unexercised (`tests/test_render_and_run.py:31`, `tests/test_update_compat.py:232`, `tests/test_render_cli_name.py:52`).
- [x] T4 Contribution — Inspect or rerun `contribcheck` after `commit-msg.txt` and `pr-description.md` are available — those artifacts are not reviewer inputs, so the claimed opener and tracker-id result cannot be independently reproduced (`template/src/pdca_harness/cli.py:1101`).
- [x] Validation — fitness-to-purpose — Decide whether the report wording and fallback semantics give operators enough reliable evidence to reconsider a split at the last reversible point — this determines whether the advisory changes real acceptance decisions (`template/src/pdca_harness/split.py:444`).

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
- By / date: Eduard Ralph / 2026-08-10

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
