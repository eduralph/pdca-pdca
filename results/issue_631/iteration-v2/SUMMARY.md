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

Review issue #631: prevent leftover build output and interrupted merges in the shared integration worktree from blocking subsequent folds or carry bundles.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The four observable failure scenarios, ignored-cache exception, and carry recovery contract define a falsifiable, bounded fix; brief.md:11 and brief.md:24. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only the production change reproduced three errors and two failures across six tests, including the healthy carry bundle being skipped; reviewer-red.log:75; target/template/tests/test_integrate_clean_tree.py:146. |
| C3 Change | PASS | Changes stay within integration-tree lifecycle and regression coverage; cleanup remains under the existing lock and the iteration's error-name ambiguity is resolved; target/template/src/pdca_harness/integrate.py:70, target/template/src/pdca_harness/integrate.py:416. |
| C4 Verification (red→green) | PASS | Restoring the same production patch makes all six real-git tests pass, covering all four success criteria plus failed recovery and cache retention; reviewer-green.log:12; target/template/tests/test_integrate_clean_tree.py:189. |
| C5 Causal adequacy | PASS | Removing dirty and mid-merge state at the shared fold boundary addresses every specified producer; failed recovery cannot be absorbed as a bundle-only skip, and no capability probe masks the cause; target/template/src/pdca_harness/integrate.py:445, target/template/src/pdca_harness/integrate.py:452, target/template/src/pdca_harness/integrate.py:615. |
| T1 Structure | PASS | One integration-specific error and one shared reset helper preserve existing caller handling and centralize recovery without introducing another subsystem; target/template/src/pdca_harness/integrate.py:70, target/template/src/pdca_harness/integrate.py:619. |
| T2 Shape | PASS | Independent diff whitespace check, documentation lint, 22-page rendering/link audit, and production-import scanner pass; frozen docs/host-parity logs corroborate the results; gate-logs/T2-docs.log:11, gate-logs/host-ci-docs.log:11; target/template/tests/test_integrate_clean_tree.py:31. |
| T3 Runtime | PASS | Independent driver run passes 2,375 tests with two skips; frozen root-suite evidence shows all 24 tests passing, including actual render/update cases; reviewer-suite.log:1800, gate-logs/T3-suite.log:38, gate-logs/T3-suite.log:54; local root rerun limitation is detailed below. |
| T4 Contribution | N/A | Contribution artifacts are deliberately absent at Check; the substantive contribution audit must rerun at publish, as the deferred gate states; gate-logs/T4-contribution.log:10. |
| T5 Judgment | NEEDS-HUMAN | Confirm the affected-path merged-history and closed/rejected-work conclusions before accepting novelty — the brief records that search, but this one-commit target has no remote or historical PR evidence with which to independently settle it; brief.md:29; affected source target/template/src/pdca_harness/integrate.py:445. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Accept the specified integration-tree disposal policy for operational use — tracked edits and ordinary untracked output are discarded while ignored caches survive, and unrecoverable cleanup stops the fold; target/template/src/pdca_harness/integrate.py:619; brief.md:24. |

Evidence and limits:

- The supplied target is a self-contained base snapshot identified as `b5f5c29`, with the patch applied. I stashed only `template/src/pdca_harness/integrate.py`, retained the new tests, ran the red leg, popped the stash, and ran the green leg. Both source and test were checked against `patch.diff` afterward and match exactly. Source citations above refer to this target, not another checkout.
- Independent reproduction command, run from `target/template`: `TMPDIR=/tmp/pdca-review-bfvoir00/reviewer-tmp PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p test_integrate_clean_tree.py -v`. Removing the test-name filter ran the complete driver suite. The tests exercise real git repositories and the real integration gate path; only the specified abort/reset failure injection is mocked.
- I reran `lint_docs.py`, `render_site.py --check`, `git diff --check`, and the shipped production-import scanner. All passed. Instance-scoped gate wrappers were adjudicated from their supplied logs; their absence from this target is expected.
- The independent root-suite command exited 77 because this interpreter cannot import Copier (`reviewer-root-suite.log:6`), so that local run does not establish render/update coverage. The frozen gate log explicitly shows the real render and update cases executing successfully (`gate-logs/T3-suite.log:38` through its 24-test result). This is a reviewer-host limitation, not a patch defect or an unmet dependency in the recorded gate run. Python and git needed for the fix's red→green were available and exercised.
- The affected-path history investigation returned only snapshot commit `7b2b3d5`; `git remote -v` returned nothing. The brief records merged history and closed-unmerged work by path, but the supplied evidence cannot independently confirm those conclusions. The target's integration document is a template with unfilled human-only items (`target/template/docs/INTEGRATION.md.jinja:80`), so it supplies no additional concrete project-specific item.

No implementation-level finding was established. This review is advisory; fitness and prior-art decisions remain with human sign-off.
<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — issue 631 (fold starts from a clean integration tree)

I found no correctness bugs that block this patch. The reset-then-clean helper is right. Both places that reuse the tree go through it: the start of each fold (`integrate.py:445`) and every failed merge in `_merge` (`integrate.py:615`). That second path also covers `_take_in_base`'s merge (`integrate.py:569`). The lock sidecar sits next to the tree, not inside it (`integrate.py:249`), so `git clean -fd` cannot delete it. C4 shows 5 of the 6 new tests red before the fix and green after. The ignored-cache test is green both ways, which is expected: it guards against a future `-x`. The findings below are small.

- `template/src/pdca_harness/integrate.py:625` — `git clean -fd` (one `-f`) skips untracked directories that hold their own `.git`. If a re-gate command clones or `git init`s something into the tree (for example a vendored tool checkout), that directory survives the reset. A later branch that adds the same path would hit the same "did not integrate" refusal this issue fixes. `clean -ffd` closes that gap and keeps ignored files. This is an edge case, not a regression.
- NEEDS-HUMAN [impl] — `template/tests/test_integrate_clean_tree.py:211-213` — `test_failed_abort_and_failed_reset_stops_the_fold` asserts the base class `integrate.IntegrationError`. It should check for the new `integrate.IntegrationTreeError`, which is what criterion (3) and `integrate.py:452` promise. Any other `IntegrationError` raised along this path would pass the test too. Asserting the subclass, and that `issue_X` is not recorded as an ordinary skip, would pin the "raise only if the reset fails" rule. Reaching it through the module attribute (`integrate.IntegrationTreeError`) keeps the file's "only modules are imported" rule. Before the fix it would fail with an AttributeError, which still counts as red.
- `template/src/pdca_harness/integrate.py:454` — the inline comment still says "the merge was aborted". The patch replaced the abort with a reset (`integrate.py:615`), and the docstring at `:345` was updated to match, but this comment wasn't. It's a wording nit with no behaviour impact.
- `template/src/pdca_harness/integrate.py:605-608` — `_merge` now runs an extra `git rev-parse HEAD` before every merge, including ones that succeed. The cost is trivial (one subprocess per bundle). I mention it only to record that I checked it and found no efficiency problem. No change needed.

On reuse: `_reset_tree` is the only reset/clean helper in `integrate.py`. I found nothing existing that it duplicates, and replacing `merge --abort` with it in `_merge` simplifies the code.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T5 Judgment — Confirm the affected-path merged-history and closed/rejected-work conclusions before accepting novelty — the brief records that search, but this one-commit target has no remote or historical PR evidence with which to independently settle it; brief.md:29; affected source target/template/src/pdca_harness/integrate.py:445.
- [ ] Validation — fitness-to-purpose — Accept the specified integration-tree disposal policy for operational use — tracked edits and ordinary untracked output are discarded while ignored caches survive, and unrecoverable cleanup stops the fold; target/template/src/pdca_harness/integrate.py:619; brief.md:24.
- [ ] `template/tests/test_integrate_clean_tree.py:211-213` — `test_failed_abort_and_failed_reset_stops_the_fold` asserts the base class `integrate.IntegrationError`. It should check for the new `integrate.IntegrationTreeError`, which is what criterion (3) and `integrate.py:452` promise. Any other `IntegrationError` raised along this path would pass the test too. Asserting the subclass, and that `issue_X` is not recorded as an ordinary skip, would pin the "raise only if the reset fails" rule. Reaching it through the module attribute (`integrate.IntegrationTreeError`) keeps the file's "only modules are imported" rule. Before the fix it would fail with an AttributeError, which still counts as red.
- [ ] **Criterion (3) cannot go red in the default mode.** The brief says: "the fold raises `IntegrationError` instead of going on to merge another bundle into that tree, in the default mode and in the carry's `skipped` mode … Pre-fix … (3) continues." That is true only for `skipped` mode. In the default mode (`skipped is None`), any non-zero `_merge` makes `_merge_published` raise. It raises at `integrate.py:477-485`, and `fold` re-raises at `integrate.py:437-438`, whether or not the abort worked. So in the default mode the fold already raises `IntegrationError` before the patch. The default-mode leg is green before the patch and proves nothing, and the C4 revert-the-fix gate cannot show RED for it. The planner should do one of two things. Option A: limit the RED claim for (3) to `skipped` mode. Option B: state the real default-mode effect of a failed abort and test that. That effect is a mid-merge tree (`MERGE_HEAD` left in place) that the *next* fold inherits, and the reset-before-fold half of the fix is what covers it.
- [ ] **Raising on a failed abort in `skipped` mode changes what the carry does, and the brief does not say so.** `skipped` exists so the #646 carry keeps going past a bundle that fails (`integrate.py:436-439`: "this bundle only; the merge was aborted"). Criterion (3) makes a failed abort stop the whole carry, so every later bundle in that carry is lost too. A `reset --hard HEAD` after a failed abort would also undo the half-done merge and keep the carry going. The brief picks "raise" and does not weigh the other option or say who decided it. That is a design decision for a human to make at sign-off, not something to settle in the test.
- [ ] **The scope does not say which clean is required, and that affects the tests and other behaviour.** The scope says "start from a tree that holds exactly its start ref". The issue suggests "`git reset --hard` + `git clean -fdx`, or equivalent" or "the re-gate runs in a separate tree", but the brief does not pick one. Criterion (1) uses an untracked file that is *not* gitignored. A `git clean -fd` without `-x` would therefore pass (1) yet still leave ignored build output behind. That output can also block a merge when a later branch commits a path the base ignores, and then the brief's invariant ("Nothing left … can change what a fold does") is not met. If the invariant is meant to include ignored files, the brief should name `-x` or add a test case with a `.gitignore`d leftover. If it is not, the invariant should say ignored files are excluded.
- [ ] **"crashed fold or carry" is in the invariant but no criterion tests it.** The invariant lists "an aborted or failed merge, a crashed fold or carry". Criteria (1)-(3) only cover leftovers from the re-gate and a failed abort inside a single fold. The case the invariant's self-test leans on ("an aborted merge or a crashed carry leaves the same state") has no red→green test: a fold that starts in a tree left mid-merge (`MERGE_HEAD` present) by an earlier fold. A cheap fix is to add a test that starts a fold in a tree with a merge left in progress. Without one, Check can only accept the "every user" claim on trust.
- [ ] T5 Judgment — Confirm the affected-path merged and closed/rejected prior-art audit — the brief lists it, but this artifact-only checkout has one synthetic base commit and no remotes, so its historical conclusions cannot be independently settled here; brief.md:29, review-environment.log:9.

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
- Iteration delta (if iterating): Auto-iterate (round 2): rebuilding for the implementation-level findings — `template/tests/test_integrate_clean_tree.py:211-213` — `test_failed_abort_and_failed_reset_stops_the_fold` asserts the base class `integrate.IntegrationError`. It should check for the new `integrate.IntegrationTreeError`, which is what criterion (3) and `integrate.py:452` promise. Any other `IntegrationError` raised along this path would pass the test too. Asserting the subclass, and that `issue_X` is not recorded as an ordinary skip, would pin the "raise only if the reset fails" rule. Reaching it through the module attribute (`integrate.IntegrationTreeError`) keeps the file's "only modules are imported" rule. Before the fix it would fail with an AttributeError, which still counts as red.. Deferred, not addressed here: 5 finding(s) that need human judgment, held in deferred-findings.json for the human at handover — not build work
- By / date: auto-iterate / 2026-10-10

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 4 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
