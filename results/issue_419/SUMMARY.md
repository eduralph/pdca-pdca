# Result — issue 419 / reviewer-target-git-writable

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: The reviewer leaf is asked to independently re-run the C4 red→green
  (stash the patch, run the test pre-fix, unstash — the instance argv comment says so
  explicitly), but the target the harness grounds it on cannot support that: `git stash`
  fails because the git index is read-only in the reviewer's confinement. Root cause on
  the target's `main`: `_reviewer_target` (`template/src/pdca_harness/leaves.py:1650-1680`)
  hands the per-cycle worktree (or the human's sibling checkout) as `$PDCA_TARGET`, and
  `_run_review_sandboxed` grants it via the family's grounding flag
  (`leaves.py:2084-2090`, codex `--add-dir` "read+write", `families.py:101-102`). But a
  `git worktree add` worktree's git metadata — its index included — lives under the
  PRIMARY checkout's `.git/worktrees/<name>/` (`worktree.py:14-16`: "its ``.git`` is an
  absolute pointer"), outside both the sandbox cwd and the granted dir; and stash writes
  objects into the shared `.git/objects`. So every index-writing git op fails, and the
  C4 verification claim lands in §6 NEEDS-HUMAN every cycle instead of being
  mechanically re-checked (observed twice in this instance: issue_317 §6 C4 and
  issue_372 §6 C4, both 2026-08-01). Distinct from #403 (closed — missing gate ORACLES;
  this is git-writability even with oracles present).
- Success criterion: For a command-mode review of a bundle with a patch, the target
  the harness grounds the reviewer on supports the git operations the independent
  red→green re-run needs — restoring the pre-fix state and re-applying the patch (e.g.
  `git stash` / `git checkout`, or an equivalent pre-fix snapshot the harness supplies)
  succeed within the reviewer's confinement — while the primary checkout and its
  `.git` receive no writes. Demonstrable offline: with the primary checkout's `.git`
  made read-only (simulating the confinement), the reviewer-target materialization
  yields a target where the pre-fix restore op succeeds; on current `main` it fails.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: the defect to remove — the reviewer's grounded target cannot host the
  red→green re-run the review contract requires. The issue sketches two acceptable
  directions (a disposable git-self-contained copy the reviewer may write, keeping the
  real target read-only; or a harness-supplied pre-fix snapshot next to the patched
  target in the sandbox); the choice of mechanism is Do's. / out of scope: granting the
  reviewer write access into the primary checkout's `.git` (the confinement is correct —
  it is the target's shape that is wrong), the missing-oracle problem (#403, closed
  separately), instance-side config changes in pdca-pdca, and the builder/gate paths
  (C4's own `run-verify` runs outside the reviewer sandbox and is not the failing party).

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
- T3 runtime: render/update-compat + offline driver suites: fail — == T3: root suite OK, driver suite FAILED (rc 1)
- T4 PR body has a user-impact opener + tracker id in both artifacts: pass — pdca-pdca contribcheck
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Task under review: make command-mode reviewers receive a disposable, git-self-contained patched target so they can stash to the pre-fix state and restore the patch without writing the primary checkout's Git metadata.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The acceptance boundary is testable and preserves confinement: reviewers need an in-sandbox red→green target while the real checkout remains untouched (`template/src/pdca_harness/leaves.py:1696`). |
| C2 Reproduction (red pre-fix) | PASS | On an archived `HEAD` plus the new test, 3 tests executed and the two patched-target cases failed at `git stash` with `index.lock: Permission denied`, directly exhibiting the specified linked-worktree defect (`template/tests/test_reviewer_target_git.py:155`). |
| C3 Change | PASS | The chosen scope changes target materialization and both review consumers, while retaining real-target grounding for patchless bundles; no unrelated production subsystem is changed (`template/src/pdca_harness/leaves.py:1720`). |
| C4 Verification (red→green) | PASS | Independent focused rerun was red on base (2 expected failures of 3) and green with the patch (3/3), exercising stash, pre-fix tree restoration, stash-pop, and primary-tree/metadata immutability (`template/tests/test_reviewer_target_git.py:168`). |
| C5 Causal adequacy | PASS | The patch removes the external-Git-metadata dependency by rebuilding the base and patch in a sandbox-local repository; it adds no capability probe or runtime guard around the broken linked-worktree path (`template/src/pdca_harness/leaves.py:1738`). |
| T1 Structure | PASS | One materialization helper owns repository construction and is composed at both primary-review and advisory call sites, keeping the shared invariant centralized (`template/src/pdca_harness/leaves.py:1696`). |
| T2 Shape | NEEDS-HUMAN | Decide whether to accept shape evidence without the driver-side `./engine/scripts/run-docs-check.sh` — that recorded green gate cannot be independently rerun because the script is absent from the permitted target, although `git diff --check` passed. |
| T3 Runtime | NEEDS-HUMAN | Decide whether the frozen driver-wrapper failure requires remediation — `./engine/scripts/run-suite.sh` and its failure log are absent, while the available patched template suite exited 0 and the root suite ran 7 environment-dependent tests as skips (`template/tests/test_autoiterate.py:722`). |
| T4 Contribution | NEEDS-HUMAN | Decide whether the contribution opener and tracker reference satisfy policy — the recorded validator is green, but its contribution artifacts and `pdca-pdca contribcheck` context were withheld and cannot be independently reproduced. |
| T5 Judgment | NEEDS-HUMAN | Decide whether prior art is sufficiently discharged — affected-path `git log --all` and GitHub searches found related history and issue #419 but no duplicate fix, yet closed/rejected work cannot be mechanically filtered by affected file path from the permitted artifacts. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether a sandbox-local one-commit repository is the right operational reviewer experience — automated evidence proves the required Git operations and isolation, but fitness and maintenance tradeoffs remain the sign-off judgment (`template/src/pdca_harness/leaves.py:1710`). |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T2 Shape — Decide whether to accept shape evidence without the driver-side `./engine/scripts/run-docs-check.sh` — that recorded green gate cannot be independently rerun because the script is absent from the permitted target, although `git diff --check` passed.
- [x] T3 Runtime — Decide whether the frozen driver-wrapper failure requires remediation — `./engine/scripts/run-suite.sh` and its failure log are absent, while the available patched template suite exited 0 and the root suite ran 7 environment-dependent tests as skips (`template/tests/test_autoiterate.py:722`).
- [x] T4 Contribution — Decide whether the contribution opener and tracker reference satisfy policy — the recorded validator is green, but its contribution artifacts and `pdca-pdca contribcheck` context were withheld and cannot be independently reproduced.
- [x] T5 Judgment — Decide whether prior art is sufficiently discharged — affected-path `git log --all` and GitHub searches found related history and issue #419 but no duplicate fix, yet closed/rejected work cannot be mechanically filtered by affected file path from the permitted artifacts.
- [x] Validation — fitness-to-purpose — Decide whether a sandbox-local one-commit repository is the right operational reviewer experience — automated evidence proves the required Git operations and isolation, but fitness and maintenance tradeoffs remain the sign-off judgment (`template/src/pdca_harness/leaves.py:1710`).

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
- By / date: Eduard Ralph / 2026-08-06

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
