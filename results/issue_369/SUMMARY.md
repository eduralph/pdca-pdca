# Result — issue 369 / checked-trapdoor-lost-review

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: `check-gates.json` *is* the CHECKED marker (`state.py:171-176`, verified
  on main), but the BUILT branch runs gates → reviewer → advisory leaves as one
  indivisible step (`driver.py:75-92`) while CHECKED dispatches to `assemble` alone
  (`driver.py:93-95`). Any death in the window between the gate write and the reviewer
  leaf (Ctrl-C, OOM, killed session) lands the bundle in CHECKED with no review; on
  resume, `assemble_summary` fills `_missing_review_text()` and the reviewer can never
  run again for that round — no flag or subcommand reaches it; the only escape is
  hand-deleting `check-gates.json` and re-paying the entire gate run. Observed for real
  (wyrd `issue_635`, after the #368 19-hour hang was interrupted). Sharp edge: the
  record cannot distinguish a reviewer that *never ran* from one that *ran and failed*.
- Success criterion: (a) a bundle in CHECKED whose `check-review.md` is absent AND
  whose `check-review.error.log` is absent (the engine's existing failed-leaf
  discriminator, #138) gets the reviewer leaf run on the next `advance` before
  `assemble_summary` — the paid gate record is preserved, the missing leaf is
  recovered; same recovery for the configured advisory leaves' artifacts; (b) a
  reviewer that ran and failed (error log present) is NOT re-run — today's behaviour;
  (c) §6 distinguishes the two cases in its wording, so a skipped reviewer never reads
  like a failed one; (d) an uninterrupted cycle is byte-identical to today.
  Demonstrable by C4-verify: unit tests build the trap-door bundle state on disk
  (brief + patch + `check-gates.json`, no review artifacts) and assert `advance` runs
  the (stubbed) reviewer, and build the ran-and-failed state and assert it does not.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: the trap door: CHECKED must recover a never-ran reviewer/advisory leaf
  (the issue's Option A — resume the missing leaf, preserving the expensive gate
  artifact) and §6 must state skipped vs failed distinctly. / out of scope: Option B
  (moving the marker / re-running gates — rejected in the issue as the expensive
  half); the gate timeout itself (#368); any change to what a *failed* leaf does.

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
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
- T3 runtime: render/update-compat + offline driver suites: fail — /tmp/tmpxmqhtjxl/results/issue_500/split-proposal.md
- T4 PR body has a user-impact opener + tracker id in both artifacts: pass — pdca-pdca contribcheck
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Issue 369 fixes a CHECKED-state trap door where an interrupted Check beat could preserve `check-gates.json` but permanently skip the reviewer/advisory leaves.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The owed behavior is explicit and bounded: recover never-ran review/advisory leaves while preserving paid gates and leaving ran-and-failed leaves alone, with no external dependency named in `brief.md`. |
| C2 Reproduction (red pre-fix) | PASS | The old base was directly reproduced: a bundle with `check-gates.json` and no review artifacts stayed without `check-review.md` after `advance`, and `SUMMARY.md` used the missing-review placeholder; the new test asserts that trap-door path at `template/tests/test_check_resume.py:76`. |
| C3 Change | PASS | The change reaches the CHECKED transition before assembly and decides whether the human needs a recovered leaf or the existing failure record, which is the state-machine point that controls the defect impact at `template/src/pdca_harness/driver.py:116`. |
| C4 Verification (red→green) | PASS | Red→green was independently reproduced with a base-copy manual trap-door run red, then patched target green; the focused regression suite also passes 10 tests and covers reviewer recovery, failed-leaf non-rerun, wording, advisory selection, and no-model stand-ins at `template/tests/test_check_resume.py:76`. |
| C5 Causal adequacy | PASS | The human decision turns on whether Option A is adequate for the invariant; the patch recovers absent artifacts before summary assembly instead of hiding them, and uses the existing error-log discriminator at `template/src/pdca_harness/leaves.py:1495`. |
| T1 Structure | PASS | The structural choice is localized to the state transition and leaf artifact predicates, with deterministic close/dependency-halt stand-ins kept out of model review at `template/src/pdca_harness/driver.py:144`. |
| T2 Shape | NEEDS-HUMAN | The exact `./engine/scripts/run-docs-check.sh` oracle named in `check-gates.json` is absent in this target checkout, so the docs/render shape result rests on the prior gate record rather than an independently rerun scanner. |
| T3 Runtime | NEEDS-HUMAN | The exact `./engine/scripts/run-suite.sh` oracle named in `check-gates.json` is absent and its recorded non-gating failure was not reproduced by `cd template && PYTHONPATH=src python3 -m unittest discover -s tests` (1463 tests OK, skipped 2), so the human must decide whether the stale row path is an environment/fixture artifact. |
| T4 Contribution | NEEDS-HUMAN | The owed decision is whether the contribution artifacts satisfy project policy; `commit-msg.txt` / `pr-description.md` were not provided to this reviewer and `pdca-pdca contribcheck` could not be rerun from the artifact set. |
| T5 Judgment | NEEDS-HUMAN | Overall contribution judgment remains human-only: decide whether the recovery behavior, extra close/dependency-halt coverage, and comments are an acceptable maintenance tradeoff for this lifecycle fix. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Standing human sign-off is required: confirm the recovered CHECKED resume flow matches the real interrupted Check workflow and avoids silently skipped reviews in practice. |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T2 Shape — The exact `./engine/scripts/run-docs-check.sh` oracle named in `check-gates.json` is absent in this target checkout, so the docs/render shape result rests on the prior gate record rather than an independently rerun scanner.
- [x] T3 Runtime — The exact `./engine/scripts/run-suite.sh` oracle named in `check-gates.json` is absent and its recorded non-gating failure was not reproduced by `cd template && PYTHONPATH=src python3 -m unittest discover -s tests` (1463 tests OK, skipped 2), so the human must decide whether the stale row path is an environment/fixture artifact.
- [x] T4 Contribution — The owed decision is whether the contribution artifacts satisfy project policy; `commit-msg.txt` / `pr-description.md` were not provided to this reviewer and `pdca-pdca contribcheck` could not be rerun from the artifact set.
- [x] T5 Judgment — Overall contribution judgment remains human-only: decide whether the recovery behavior, extra close/dependency-halt coverage, and comments are an acceptable maintenance tradeoff for this lifecycle fix.
- [x] Validation — fitness-to-purpose — Standing human sign-off is required: confirm the recovered CHECKED resume flow matches the real interrupted Check workflow and avoids silently skipped reviews in practice.

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
- By / date: Eduard Ralph / 2026-08-01

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
