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

Review of issue #419: make the reviewer’s patched target git-self-contained and writable for an isolated stash-based red→green rerun without writing the primary checkout.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The acceptance boundary is testable and scoped to restoring reviewer-side git operations while preserving the primary checkout; no external dependency is declared (`brief.md:25-55`). |
| C2 Reproduction (red pre-fix) | PASS | In an isolated copy with the test retained and only the production hunk reverted, 3 tests ran and 2 failed on the original read-only `.git/worktrees/.../index.lock` denial, grounding the defect exercised at `template/tests/test_reviewer_target_git.py:145`. |
| C3 Change | PASS | The patch confines the writable repository to the review sandbox and withholds the real-target grant when that copy exists, preserving the stated security boundary at `template/src/pdca_harness/leaves.py:2182`. |
| C4 Verification (red→green) | PASS | Independent rerun produced a real red (3 run, 2 failures) before the production change and green (3 run, 3 pass) after it; the assertions cover stash, pre-fix tree, pop, and restored patched tree at `template/tests/test_reviewer_target_git.py:145`. |
| C5 Causal adequacy | PASS | The decision is whether the inaccessible shared git metadata is eliminated rather than merely tolerated; the sandbox-local repository owns its index and objects and reads the source only through archive/revision operations at `template/src/pdca_harness/leaves.py:1738`. |
| T1 Structure | PASS | The materializer is shared by reviewer and advisory call paths, so the invariant is centralized rather than duplicated across leaf-specific implementations (`template/src/pdca_harness/leaves.py:1696`, `template/src/pdca_harness/leaves.py:2522`). |
| T2 Shape | PASS | Imports, helper placement, and the focused stdlib test module fit the existing Python structure; the recorded docs/link audit is green and the full test discovery collected successfully (`template/src/pdca_harness/leaves.py:36`, `template/tests/test_reviewer_target_git.py:1`). |
| T3 Runtime | NEEDS-HUMAN | Decide whether the frozen driver-suite failure requires remediation before sign-off — its command/log was not supplied and cannot be rerun exactly, while the available offline suite passed all 1,591 tests, so the recorded red is provisional rather than a confirmed patch defect (`check-gates.json:1`). |
| T4 Contribution | NEEDS-HUMAN | Decide whether the contribution artifacts satisfy the required user-impact opener and tracker reference — the recorded validator is green, but those artifacts were withheld and the result cannot be independently reproduced from the three review inputs (`check-gates.json:1`). |
| T5 Judgment | PASS | Path-scoped merged history plus an all-state GitHub search found related grant work (PR #230) but no prior self-contained-target implementation; the change remains focused on the brief’s reviewer/advisory target seam (`template/src/pdca_harness/leaves.py:1696`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether a disposable one-commit repository is an acceptable reviewer grounding model in real review sessions — tests establish isolation and stashability, but human sign-off owns whether reduced history and best-effort fallback preserve the intended review experience (`template/src/pdca_harness/leaves.py:1710`). |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T3 Runtime — Decide whether the frozen driver-suite failure requires remediation before sign-off — its command/log was not supplied and cannot be rerun exactly, while the available offline suite passed all 1,591 tests, so the recorded red is provisional rather than a confirmed patch defect (`check-gates.json:1`).
- [ ] T4 Contribution — Decide whether the contribution artifacts satisfy the required user-impact opener and tracker reference — the recorded validator is green, but those artifacts were withheld and the result cannot be independently reproduced from the three review inputs (`check-gates.json:1`).
- [ ] Validation — fitness-to-purpose — Decide whether a disposable one-commit repository is an acceptable reviewer grounding model in real review sessions — tests establish isolation and stashability, but human sign-off owns whether reduced history and best-effort fallback preserve the intended review experience (`template/src/pdca_harness/leaves.py:1710`).

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
- Iteration delta (if iterating): Auto-iterate (round 1): Check found implementation-level items only, no architectural judgment required — T3 Runtime — Decide whether the frozen driver-suite failure requires remediation before sign-off — its command/log was not supplied and cannot be rerun exactly, while the available offline suite passed all 1,591 tests, so the recorded red is provisional rather than a confirmed patch defect (`check-gates.json:1`).; T4 Contribution — Decide whether the contribution artifacts satisfy the required user-impact opener and tracker reference — the recorded validator is green, but those artifacts were withheld and the result cannot be independently reproduced from the three review inputs (`check-gates.json:1`).
- By / date: auto-iterate / 2026-08-06

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
