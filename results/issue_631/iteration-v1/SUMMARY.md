# Result — issue 631 / fold-starts-from-a-clean-integration-tree

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: One integration worktree per target is reused by every fold of a run, by the #646 pre-wave carry, and by the optional between-waves re-gate (`[driver].regate_between_waves`). `integrate._prepare_worktree` (`template/src/pdca_harness/integrate.py:618-628`) only creates the tree when it is missing and otherwise reuses it as it is. `fold` then runs `git checkout -B <line> <start_ref>` (`integrate.py:431`) and `git merge` of each published branch (`_merge`, `integrate.py:583-595`). Nothing resets or cleans the tree in between. The re-gate runs the repo-scoped gates with that tree as cwd (`gates.run_integration`, `template/src/pdca_harness/gates.py:235-261`, called from `flow._fold_lines`, `template/src/pdca_harness/flow.py:816-819`). Build output it leaves (an untracked file a later branch adds, a modified tracked file) makes the next fold's `checkout -B` or `git merge` refuse, and the run stops with "did not integrate". Round 4 of #593 fixed only the message (`integrate.py:477-485`), not the cause. `_merge` also ignores the return code of `git merge --abort` (`integrate.py:594`), so a failed abort leaves a mid-merge tree that the carry's per-bundle `skipped` mode (`integrate.py:433-439`) merges the next bundle into. The template's own docs already claim the reset happens: "each fold resets its tree to a freshly fetched ref" (`template/pdca.toml.jinja:216`, `template/src/pdca_harness/sweep.py:18`).
- Success criterion: With the patch, on a real-git fixture (bare `origin`, published bundle branches, as in `template/tests/test_integrate_stack_bases.py`'s `StackFoldGit`):
  (1) **Leftover untracked output.** Fold [A] at `folded_this_run={}`. Then run `gates.run_integration(cfg, wt)` on the fold's worktree, with a repo-scoped gate whose command writes `out/build.txt` (untracked). Then fold [A, B] at `folded_this_run={TARGET: t1}`, where B's published branch adds `out/build.txt`. The second fold succeeds, and the line tip's `out/build.txt` holds B's content (not the gate's).
  (2) **Leftover modified tracked file.** The same, with the gate overwriting a tracked file that the next branch changes: A adds `a.txt`, the gate rewrites `a.txt` in the tree, and B's branch is cut from the line at `t1` and changes `a.txt`. The next fold succeeds, and the line tip's `a.txt` is B's committed content. (A dirty file the next merge does not touch does not make git refuse, so it would not show the defect.)
  (3) **A failed abort is not ignored (carry's `skipped` mode).** Fold [X, B] with `skipped={}`, where X's merge conflicts with the line and `git merge --abort` fails (`integrate._git` patched to fail only for `merge --abort`, so the tree is really left mid-merge). The fold puts the tree back to the line tip it had before X's merge (e.g. `git reset --hard` to it, which also drops `MERGE_HEAD`), records X in `skipped`, and then merges B: B is on the pushed line and not in `skipped`. Only if that reset also fails does the fold raise `IntegrationError`. This keeps the carry's contract, "this bundle only; the merge was aborted" (`integrate.py:436-439`), true.
  (4) **A fold starts clean from a tree left mid-merge.** Leave the worktree mid-merge (`MERGE_HEAD` present: start a conflicting `git merge` in it and do not abort), as a crashed fold or carry, or the default mode's failed abort, would leave it. The next fold [A, B] at `folded_this_run={TARGET: t1}` succeeds and the line holds B.
  Pre-fix, (1), (2) and (4) raise `IntegrationError` ("could not merge … `git merge` exited …" or "could not start …"), and in (3) B lands in `skipped` because git refuses to merge into a tree with `MERGE_HEAD`. That is the RED. In the default mode (no `skipped`) a failed merge already raises before and after the patch (`integrate.py:437-438`, `:477-485`), so there is no default-mode leg for (3); the default mode's real exposure is the mid-merge tree it leaves for the NEXT fold, which (4) covers.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: Make every fold of an integration worktree (the in-run fold and the #646 carry, both via `integrate.fold`) start from a tree that holds exactly its start ref, whatever the tree's previous user left behind, and make a failed merge abort leave no mid-merge tree behind (criterion (3)). Untracked files that are not ignored are removed (`git clean -fd`-equivalent, no `-x`); ignored files are kept (see Invariant). Keep the docs' "each fold resets its tree" claim true (fix the claim only if the behaviour chosen differs from it). / out of scope: the re-gate's own verdict and which gates it runs; the lane worktrees used by Do/Check (`worktree.py`); the footprint sweep's policy (`sweep_worktrees`); the lock scope (`integ_lock`, already covering fold and re-gate).

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: pass — C4 PASS — red without the fix, green with it
- C5 added test exercises production, not a copy: pass — 1 added driver-suite test(s) import the production package 'pdca_harness'

## 4. Conformance (Check — stack)
- T1 Structure: none — (no gate configured)
- T2 shape: docs lint + site render link audit: pass — docs lint clean, site render + link audit clean
- T2 host CI parity: target docs-check.yml on the pushed tree: pass — host CI parity on the patched tree — docs lint clean, site render + link audit clean
- T3 runtime: render/update-compat + offline driver suites: pass — root suite OK, driver suite OK
- T4 PR body has a user-impact opener + tracker id in both artifacts: deferred — pr-description.md not drafted yet — the substantive T4 audit of the contribution artifacts runs at publish
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Review issue #631: prevent reused integration worktree debris and unfinished merges from breaking subsequent folds or carry operations.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | Four falsifiable real-git scenarios define the failure and recovery contract, with ignored caches explicitly excluded and scope confined to integration worktrees; brief.md:11, brief.md:24. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing the production fix while retaining the regression tests reproduced three merge/checkout errors and two failed recovery assertions; target/template/tests/test_integrate_clean_tree.py:145, review-red.log:1. |
| C3 Change | PASS | The change addresses the specified integration lifecycle without broadening into lane or sweep policy; cleanup occurs under the existing lifecycle lock; target/template/src/pdca_harness/integrate.py:413, target/template/src/pdca_harness/integrate.py:442. |
| C4 Verification (red→green) | PASS | Restoring the production patch made all six tests pass with real git, including continued carry after conflict, stopping without a push when reset fails, and preserving ignored caches; target/template/tests/test_integrate_clean_tree.py:190, target/template/tests/test_integrate_clean_tree.py:205, review-green.log:1. |
| C5 Causal adequacy | PASS | Recovery removes the persistent dirty/mid-merge state at the shared lifecycle boundary; failure to recover escapes per-bundle skipping, and no optional-capability probe masks a load-time cause; target/template/src/pdca_harness/integrate.py:449, target/template/src/pdca_harness/integrate.py:612. |
| T1 Structure | PASS | A shared reset helper and specific IntegrationError subtype keep recovery consistent between fold startup and failed merges, with publication following successful recovery; target/template/src/pdca_harness/integrate.py:70, target/template/src/pdca_harness/integrate.py:459, target/template/src/pdca_harness/integrate.py:616. |
| T2 Shape | PASS | Independent docs lint, 22-page render/link audit, production-import scanner, and git diff whitespace check passed; frozen docs and host-parity logs agree; review-docs.log:2, gate-logs/T2-docs.log:10, gate-logs/host-ci-docs.log:10. |
| T3 Runtime | PASS | Independent integration discovery passed all 67 tests; the frozen full-suite evidence reports 24 root tests passing and 2,375 driver tests completing successfully with two skips; target/template/tests/test_integrate_clean_tree.py:145, gate-logs/T3-suite.log:54, gate-logs/T3-suite.log:1857. |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the substantive PR-body/tracker audit is owed at publish, as the deferred gate records; gate-logs/T4-contribution.log:10. |
| T5 Judgment | NEEDS-HUMAN | Confirm the affected-path merged and closed/rejected prior-art audit — the brief lists it, but this artifact-only checkout has one synthetic base commit and no remotes, so its historical conclusions cannot be independently settled here; brief.md:29, review-environment.log:9. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Accept discarding tracked edits and non-ignored build output in the disposable integration tree while preserving ignored caches — automated recovery is demonstrated, but suitability of that lifecycle policy remains the maintainer's sign-off decision; brief.md:24, target/template/src/pdca_harness/integrate.py:622. |

No implementation defect was established. Source citations above refer to the patched disposable `$PDCA_TARGET` copy; its base matches the brief's b5f5c29 snapshot. The production patch was restored after the red leg, and the supplied test was retained throughout.

Independent commands used `TMPDIR` inside this review sandbox and disabled Python bytecode writes. From `target/template`, the red and green legs ran `PYTHONPATH=src python3 -B -m unittest discover -s tests -p test_integrate_clean_tree.py -v`; the broader integration run selected `test_integrate*.py`. Full outputs are in `review-red.log`, `review-green.log`, and `review-integration.log`. Python and git were available and actually exercised; injected abort/reset failures exercise recovery rather than substitute for a missing external dependency.

The instance-scoped gate wrappers are outside the supplied target. Their absence is expected. The frozen logs were inspected for C4, C5, docs, host parity, runtime, and deferred contribution evidence. The complete root/driver suite was assessed from its frozen log; the independent runtime rerun covered the 67 integration tests. No claim of a fresh full-suite or remote CI execution is made. The target's `template/docs/INTEGRATION.md.jinja:80` contains a placeholder rather than additional enumerated human-only rules.

The prior-art investigation used `git log --all --oneline --` with both affected paths and `git remote -v`: only `9d7c229 pre-fix base b5f5c29...` was returned and no remote was configured. The brief records merged-history and closed-unmerged checks for `integrate.py`, but their underlying history/PR evidence is not in this bundle. This is a review-evidence limitation, not a stale-target or compilation defect.

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — issue 631 (fold starts from a clean integration tree)

Overall: no correctness bug found in the production change. The reset sits inside the integration lock, runs before `checkout -B`, and leaves the "nothing pushed when a fold raises" order alone. The C4 log shows all five behaviour cases red before the fix and green after it. The ignored-cache case passes either way, which is expected because it guards behaviour rather than reproducing the bug. The findings below are small cleanups. Only the first is worth sending back to Do.

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/integrate.py:70`: the new class is named `WorktreeError`, the same name as `worktree.WorktreeError` (`template/src/pdca_harness/worktree.py:62`). The two classes are unrelated. `cli.py:459`, `gates.py:377` and `publish.py:1028` all catch `worktree.WorktreeError`, so a reader could easily think those handlers also catch the new error. They don't. It works today only because the new class subclasses `IntegrationError`, which the flow already catches (`flow.py:915/922/934`). A distinct name such as `IntegrationTreeError` would remove the confusion. No behaviour change.
- `template/src/pdca_harness/integrate.py:451`: the comment `# this bundle only; the merge was aborted` no longer describes the code. `_merge` now resets to the pre-merge tip (`integrate.py:612`) and no longer runs `merge --abort`. The same applies to the older docstring line "failed merge is aborted, so the tree is clean for it" at `integrate.py:344`. Both are wording nits: the meaning (tree clean, this bundle only) is still true.
- `template/src/pdca_harness/integrate.py:622`: `git clean -fd` (no `-x`) does not remove an untracked directory that is itself a nested git repo, because git needs `-ff` for that. If a re-gate command clones or `git init`s inside the tree, the leftover could still block a later merge that adds files at that path. This is unlikely for today's gates and the brief does not require it, so it is noted only. If wanted, the fix is `clean -ffd`, which still keeps ignored files.
- `template/tests/test_integrate_clean_tree.py:211`: `assertRaises(integrate.IntegrationError)` in the "reset also fails" case would accept any `IntegrationError`, including an unrelated merge failure. Checking the message (for example, that it contains "could not reset the integration worktree") would pin it to the `_reset_tree` path while still loading against the pre-fix module. Minor.
- `template/tests/test_integrate_clean_tree.py:177-187`: after the fix, nothing calls `git merge --abort` any more, so the spy's "abort fails" branch never fires on the patched code. The test still proves the intended outcome (X in `skipped`, B merged, no `MERGE_HEAD`), and it was red before the fix per `gate-logs/C4-verify.log`. The name `_abort_fails` describes the old failure mode, not something the new code exercises. No action needed.
- Reuse/efficiency: clean. `_reset_tree` is one shared helper, used both at fold start (`integrate.py:442`) and on a failed merge (`integrate.py:612`). That also covers the gone-branch `_take_in_base` merge (`integrate.py:566`). The extra `rev-parse` per merge and the reset per fold are cheap next to the fetch and merge they sit beside.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T5 Judgment — Confirm the affected-path merged and closed/rejected prior-art audit — the brief lists it, but this artifact-only checkout has one synthetic base commit and no remotes, so its historical conclusions cannot be independently settled here; brief.md:29, review-environment.log:9.
- [ ] Validation — fitness-to-purpose — Accept discarding tracked edits and non-ignored build output in the disposable integration tree while preserving ignored caches — automated recovery is demonstrated, but suitability of that lifecycle policy remains the maintainer's sign-off decision; brief.md:24, target/template/src/pdca_harness/integrate.py:622.
- [ ] `template/src/pdca_harness/integrate.py:70`: the new class is named `WorktreeError`, the same name as `worktree.WorktreeError` (`template/src/pdca_harness/worktree.py:62`). The two classes are unrelated. `cli.py:459`, `gates.py:377` and `publish.py:1028` all catch `worktree.WorktreeError`, so a reader could easily think those handlers also catch the new error. They don't. It works today only because the new class subclasses `IntegrationError`, which the flow already catches (`flow.py:915/922/934`). A distinct name such as `IntegrationTreeError` would remove the confusion. No behaviour change.
- [ ] **Criterion (3) cannot go red in the default mode.** The brief says: "the fold raises `IntegrationError` instead of going on to merge another bundle into that tree, in the default mode and in the carry's `skipped` mode … Pre-fix … (3) continues." That is true only for `skipped` mode. In the default mode (`skipped is None`), any non-zero `_merge` makes `_merge_published` raise. It raises at `integrate.py:477-485`, and `fold` re-raises at `integrate.py:437-438`, whether or not the abort worked. So in the default mode the fold already raises `IntegrationError` before the patch. The default-mode leg is green before the patch and proves nothing, and the C4 revert-the-fix gate cannot show RED for it. The planner should do one of two things. Option A: limit the RED claim for (3) to `skipped` mode. Option B: state the real default-mode effect of a failed abort and test that. That effect is a mid-merge tree (`MERGE_HEAD` left in place) that the *next* fold inherits, and the reset-before-fold half of the fix is what covers it.
- [ ] **Raising on a failed abort in `skipped` mode changes what the carry does, and the brief does not say so.** `skipped` exists so the #646 carry keeps going past a bundle that fails (`integrate.py:436-439`: "this bundle only; the merge was aborted"). Criterion (3) makes a failed abort stop the whole carry, so every later bundle in that carry is lost too. A `reset --hard HEAD` after a failed abort would also undo the half-done merge and keep the carry going. The brief picks "raise" and does not weigh the other option or say who decided it. That is a design decision for a human to make at sign-off, not something to settle in the test.
- [ ] **The scope does not say which clean is required, and that affects the tests and other behaviour.** The scope says "start from a tree that holds exactly its start ref". The issue suggests "`git reset --hard` + `git clean -fdx`, or equivalent" or "the re-gate runs in a separate tree", but the brief does not pick one. Criterion (1) uses an untracked file that is *not* gitignored. A `git clean -fd` without `-x` would therefore pass (1) yet still leave ignored build output behind. That output can also block a merge when a later branch commits a path the base ignores, and then the brief's invariant ("Nothing left … can change what a fold does") is not met. If the invariant is meant to include ignored files, the brief should name `-x` or add a test case with a `.gitignore`d leftover. If it is not, the invariant should say ignored files are excluded.
- [ ] **"crashed fold or carry" is in the invariant but no criterion tests it.** The invariant lists "an aborted or failed merge, a crashed fold or carry". Criteria (1)-(3) only cover leftovers from the re-gate and a failed abort inside a single fold. The case the invariant's self-test leans on ("an aborted merge or a crashed carry leaves the same state") has no red→green test: a fold that starts in a tree left mid-merge (`MERGE_HEAD` present) by an earlier fold. A cheap fix is to add a test that starts a fold in a tree with a merge left in progress. Without one, Check can only accept the "every user" claim on trust.

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
- Iteration delta (if iterating): Auto-iterate (round 1): rebuilding for the implementation-level findings — `template/src/pdca_harness/integrate.py:70`: the new class is named `WorktreeError`, the same name as `worktree.WorktreeError` (`template/src/pdca_harness/worktree.py:62`). The two classes are unrelated. `cli.py:459`, `gates.py:377` and `publish.py:1028` all catch `worktree.WorktreeError`, so a reader could easily think those handlers also catch the new error. They don't. It works today only because the new class subclasses `IntegrationError`, which the flow already catches (`flow.py:915/922/934`). A distinct name such as `IntegrationTreeError` would remove the confusion. No behaviour change.. Deferred, not addressed here: 5 finding(s) that need human judgment, held in deferred-findings.json for the human at handover — not build work
- By / date: auto-iterate / 2026-10-10

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 4 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
