# Brief — issue 419 / reviewer-target-git-writable

> The Plan artifact (docs 02 §PLAN). Human-authored. Do reads ONLY this file.
> The field labels below are parsed by the driver — keep the `- **Label:** value`
> shape. The success criterion is the load-bearing field: it is the sentence
> Check tests "did this work" against.

- **Slug:** reviewer-target-git-writable
- **Defect:** The reviewer leaf is asked to independently re-run the C4 red→green
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
- **Success criterion:** For a command-mode review of a bundle with a patch, the target
  the harness grounds the reviewer on supports the git operations the independent
  red→green re-run needs — restoring the pre-fix state and re-applying the patch (e.g.
  `git stash` / `git checkout`, or an equivalent pre-fix snapshot the harness supplies)
  succeed within the reviewer's confinement — while the primary checkout and its
  `.git` receive no writes. Demonstrable offline: with the primary checkout's `.git`
  made read-only (simulating the confinement), the reviewer-target materialization
  yields a target where the pre-fix restore op succeeds; on current `main` it fails.
- **Falsifiability:** RED is producible offline on Do's plain Linux checkout: a test
  builds a tiny git repo, creates the per-cycle worktree the way `worktree.ensure` does,
  **applies a tracked modification in the worktree** (the patched state the reviewer is
  asked to stash away — a clean `git stash` exits 0 with "No local changes to save" and
  exercises no index write, so the dirty state is what makes the red deterministic),
  chmods the primary `.git` tree read-only (restoring permissions in teardown), and runs
  the pre-fix-restore op in whatever `_reviewer_target`/the sandbox setup hands the
  reviewer — on `main` (verified at `0fbfa26`) that is the linked worktree, whose index
  writes land in the read-only primary `.git/worktrees/<name>/`, so the op fails. No
  vendor sandbox is needed to exhibit the red; read-only primary git metadata reproduces
  the same denial deterministically.
- **Invariant to restore:** Independent re-verification at Check must be executable
  within the reviewer's confinement: every operation the review contract asks the
  reviewer to perform against `$PDCA_TARGET` must be one the granted environment can
  actually perform, without write access to the primary checkout's git metadata.
  Source: the reviewer contract (`agents/reviewer.md` / the instance's
  `[leaves.reviewer]` rationale: re-runs red/green evidence, "git stash/unstash", on
  `$PDCA_TARGET`) and the worktree module's own doctrine that the primary checkout is
  never touched (`worktree.py:1-20`). SELF-TEST: not satisfiable by guarding one module
  — detecting the failure and falling back to §6 is the current behavior, i.e. the
  symptom.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Conflicts with:** 396
- **Ordering note:** conflicts-with 396 because both patch
  `template/src/pdca_harness/leaves.py` (this bundle the reviewer-sandbox/target seam at
  ~1650-2110, 396 the interactive spawn at ~380) — schedule into different waves rather
  than build blind on the same base. 396 declares the same conflict.
- **Surfaces:** data
- **Difficulty:** medium
- **Scope:** the defect to remove — the reviewer's grounded target cannot host the
  red→green re-run the review contract requires. The issue sketches two acceptable
  directions (a disposable git-self-contained copy the reviewer may write, keeping the
  real target read-only; or a harness-supplied pre-fix snapshot next to the patched
  target in the sandbox); the choice of mechanism is Do's. / out of scope: granting the
  reviewer write access into the primary checkout's `.git` (the confinement is correct —
  it is the target's shape that is wrong), the missing-oracle problem (#403, closed
  separately), instance-side config changes in pdca-pdca, and the builder/gate paths
  (C4's own `run-verify` runs outside the reviewer sandbox and is not the failing party).
- **Repro instruction:** On any checkout of the target: create a repo with a commit,
  `git worktree add` a linked worktree, **modify a tracked file in the worktree** (so
  there is something to stash — a clean stash no-ops successfully), then
  `chmod -R a-w <repo>/.git` and in the worktree run `git stash` → "unable to write new
  index file" / read-only failure (the index lives under the primary
  `.git/worktrees/<name>/`). This is the reviewer's situation:
  `leaves.py:2084-2090` grants only the worktree path, never its external git dir.
  Frozen instance evidence: `results/issue_317/SUMMARY.md` §6 C4 and
  `results/issue_372/SUMMARY.md` §6 C4 (both fell back to manual red→green).
- **External dependencies:** none
- **Test file:** template/tests/test_reviewer_target_git.py (new file: with the patch
  applied — a dirty worktree, the state the reviewer must stash away — the materialized
  reviewer target supports the pre-fix restore + re-apply with the primary `.git`
  read-only, and the primary checkout's tree + git metadata are byte-identical
  before/after. The instance C4 contract classifies `template/tests/*.py` as tests and
  reverts only production hunks, so a new file earns its red fine.)
- **Citations expected:** Do must cite path:line on the target branch for every change —
  `leaves.py:1650-1680` (`_reviewer_target`), `leaves.py:2055-2110`
  (`_run_review_sandboxed`, esp. the grounding block at 2084-2090), `families.py:101-102`
  (the read+write intent of the codex grounding flag), `worktree.py:14-16` (the absolute
  `.git` pointer that makes a copied/granted worktree git-incomplete). Peer callsite MAY
  be opened for composition: `_seed_sandbox_gate_logs` (`leaves.py:1733-1762`) is the
  existing pattern for materializing per-round evidence into the sandbox.
- **Prior-art check (triage cycles):** `git -C ../pdca-harness log --oneline origin/main
  -- template/src/pdca_harness/leaves.py` — #403 seeded the gate-logs (evidence made
  READABLE, `f262fb0` era) and #75/#120/#94 shaped `_reviewer_target`, but no commit
  addresses git-writability of the granted target; `gh search issues "reviewer stash"`
  finds nothing else open. No open PRs.
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: Auto-iterate (round 1): Check found implementation-level items only, no architectural judgment required — T3 Runtime — Decide whether the frozen driver-suite failure requires remediation before sign-off — its command/log was not supplied and cannot be rerun exactly, while the available offline suite passed all 1,591 tests, so the recorded red is provisional rather than a confirmed patch defect (`check-gates.json:1`).; T4 Contribution — Decide whether the contribution artifacts satisfy the required user-impact opener and tracker reference — the recorded validator is green, but those artifacts were withheld and the result cannot be independently reproduced from the three review inputs (`check-gates.json:1`).
- Failing gate: T3 runtime: render/update-compat + offline driver suites (advisory) — == T3: root suite OK, driver suite FAILED (rc 1)
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
