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

Review issue #631: make reused integration worktrees start clean and recover failed merges so later folds and carry bundles can proceed.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The four observable failure cases define an offline, falsifiable contract, with ignored caches explicitly excluded; brief.md:11 and brief.md:18. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing the production change while retaining the tests reproduced two failures and four errors, including blocked subsequent merges and carry contamination; reviewer-red.log:93; target/template/tests/test_integrate_clean_tree.py:146. |
| C3 Change | NEEDS-HUMAN | Confirm that deleting untracked nested repositories is authorized — the brief specifies `clean -fd` equivalence, while `clean -ffd` deliberately removes repositories that single-force cleaning preserves; brief.md:24; target/template/src/pdca_harness/integrate.py:622. |
| C4 Verification (red→green) | PASS | Restoring the same production patch turned the six failing cases green: all seven regression tests passed using real Git and production gate execution; reviewer-green.log:14; target/template/tests/test_integrate_clean_tree.py:134. |
| C5 Causal adequacy | PASS | The shared tree's dirty state is removed at the fold boundary and failed merges restore their prior commit; this addresses the cause for both fold and carry, without an optional-capability probe; target/template/src/pdca_harness/integrate.py:446 and target/template/src/pdca_harness/integrate.py:616. |
| T1 Structure | PASS | Cleanup remains inside the existing lifecycle lock, and an unrecoverable tree error escapes per-bundle skipping through the established IntegrationError hierarchy; target/template/src/pdca_harness/integrate.py:419 and target/template/src/pdca_harness/integrate.py:453. |
| T2 Shape | PASS | Independent docs lint, 22-page render/link audit, production-import scanner and whitespace check passed; the frozen docs and host-parity logs agree; gate-logs/T2-docs.log:11; gate-logs/host-ci-docs.log:11; target/template/tests/test_integrate_clean_tree.py:32. |
| T3 Runtime | PASS | Independent driver run passed 2,376 tests with two skips; the frozen root-suite log records all 24 tests passing, including render/update cases unavailable to the local interpreter; reviewer-suite.log:1801; gate-logs/T3-suite.log:36; reviewer-root.log:6. |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the deferred row explicitly requires its substantive audit at publish; gate-logs/T4-contribution.log:10. |
| T5 Judgment | NEEDS-HUMAN | Confirm the affected-path prior-art conclusion against upstream merged and closed/rejected work — the brief records that search, but the supplied target contains only a synthetic base commit and no remote, so it cannot independently establish that no competing fix was missed; brief.md:29. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether discarding non-ignored integration-tree contents while retaining ignored caches is the intended operational policy — passing real-Git regressions establish behavior, while ownership and cache policy require maintainer sign-off; brief.md:24; target/template/src/pdca_harness/integrate.py:620; target/template/tests/test_integrate_clean_tree.py:247. |

Independent evidence and limits:

- All source citations were checked in `$PDCA_TARGET`, the self-contained disposable target at `target/`. Its synthetic base identifies the brief's `b5f5c29` base, and the production diff matches `patch.diff`. No target-staleness caveat was needed. The patch was restored after the red run; no production or test edits were made.
- Reproduction command, from `target/template`: `TMPDIR=/tmp/pdca-review-bak130ls PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest -v tests.test_integrate_clean_tree`. Stashed only `template/src/pdca_harness/integrate.py`, ran the red leg, popped the stash, then reran green. The ignored-cache case passed both legs; the other six failed before the fix. Logs: `reviewer-red.log` and `reviewer-green.log`.
- Full driver command used the same environment with `python3 -m unittest discover -s tests`; exit 0, 2,376 tests, two skips (`reviewer-suite.log:1801`). Fault injection affects only the specified abort/reset failures; actual merges, conflicts, branch publication and gate-written output use real Git and shell commands.
- The previous iteration's test concern is discharged: the failed-reset case checks the `IntegrationTreeError` subclass, an empty skip map, and the unchanged published tip (`target/template/tests/test_integrate_clean_tree.py:227`). No builder-fixable C5/T5 concern was found.
- Reran the target's `docs/publishing/tools/lint_docs.py`, `docs/publishing/tools/render_site.py --check --out /tmp/pdca-review-bak130ls/reviewer-site`, `template/scripts/checks/test_exercises_production.py` with this bundle and `PDCA_PROD_PACKAGE=pdca_harness`, and `git diff --check`; all passed. The instance-scoped wrappers were adjudicated from their supplied logs and their available underlying target tools.
- Local `python3 -m tests.run_root_suite` exited 77 because Copier is not importable by `/usr/bin/python3` (`reviewer-root.log:6`). This is a local host caveat, not a patch failure or a verified local root run. Frozen evidence explicitly shows the real render/update cases executing and all 24 root tests passing (`gate-logs/T3-suite.log:36`, `gate-logs/T3-suite.log:54`); no missing external dependency is inferred for the fix from this local limitation.
- Prior-art investigation: `git log --all --oneline -- template/src/pdca_harness/integrate.py template/tests/test_integrate_clean_tree.py` yielded only `f1ee3b5 pre-fix base b5f5c29b31d93bb2e41a4692bc56affd1cfd72bb`; `git remote -v` was empty. The brief records merged-history and closed-PR checks for the existing affected production path, but supplies no independently inspectable history or closed-PR evidence. T5 preserves that decision for sign-off.
- The only supplied integration document is the unrendered template; its project-specific human-only list is still TODO (`target/template/docs/INTEGRATION.md.jinja:80`). No populated instance rules or prior deferred-findings artifact were supplied, so this report does not claim to resolve earlier human-only findings.

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — issue 631 (fold starts from a clean integration tree)

Lenses: correctness bugs the patch adds, and reuse / simplification / efficiency.
Paths are under `$PDCA_TARGET` (patched tree).

**Result: no blocking findings on either lens.** The fix does what the brief asks. The previous rounds' two items are handled: the class is now `IntegrationTreeError` (`template/src/pdca_harness/integrate.py:70`), and the test asserts that subclass and an empty `skipped` (`template/tests/test_integrate_clean_tree.py:223-230`). The C4 log shows 6 of 7 tests red before the fix and all green after. The one test that passes before the fix, `test_ignored_build_cache_is_kept` (`template/tests/test_integrate_clean_tree.py:247`), is meant to: it guards the "no `-x`" choice and is not a repro.

What I checked and found correct:

- `template/src/pdca_harness/integrate.py:446` — the reset before the fold runs inside the lifecycle lock and before `checkout -B`. A failure raises before any push, so the "nothing is pushed when a fold raises" order still holds.
- `template/src/pdca_harness/integrate.py:605-616` — `before` is read before the merge. Conflict paths are collected (`diff --diff-filter=U`) *before* `_reset_tree` wipes them, so the conflict message is unchanged. Both callers of `_merge` (`_merge_published` at `:490` and `_take_in_base` at `:570`) get the reset-on-failure behaviour, so the gone-branch path no longer leaves a mid-merge tree either.
- `template/src/pdca_harness/integrate.py:453` — `IntegrationTreeError` bypasses `skipped`. Since it subclasses `IntegrationError`, the flow's existing handlers still catch it. That matches criterion (3)'s "raise only if the reset fails".
- `template/src/pdca_harness/integrate.py:628` — `clean -ffd` with no `-x` matches the brief's invariant: ignored files are kept, and nested repos are removed (the extra test at `tests/test_integrate_clean_tree.py` covers the nested-repo case).
- Cost: each fold adds two git calls, and each merge adds one `rev-parse` (plus two calls on a failed merge). That is negligible next to the fetch and merge.

Minor, non-blocking notes (no action needed):

- `template/tests/test_integrate_clean_tree.py:192` — after the fix, production never calls `git merge --abort`, so the spy's abort branch only matters for the pre-fix (red) leg. That is intended: it makes the pre-fix code really leave a mid-merge tree. Post-fix, criterion (3)'s green leg is really testing "a failed merge is undone by reset", not "a failed abort is caught". It meets the brief, but a reader may find the test name `test_failed_abort_resets_the_tree_and_the_carry_goes_on` misleading against the new code path. Optional rename or comment.
- `template/src/pdca_harness/integrate.py:446` — the reset before the fold passes the literal `"HEAD"`, so if it fails the error says "could not reset … to HEAD", not a SHA. That is fine for an operator, just less specific than the in-merge case, which passes a SHA (`:616`). Optional.
- `template/src/pdca_harness/integrate.py:616` — the comment "a no-op when the merge never started" holds only because the tree was cleaned at fold start and every merge since then committed. `clean -ffd` is not a no-op in general. This is accurate in context, so no change is needed.

No NEEDS-HUMAN items.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] C3 Change — Confirm that deleting untracked nested repositories is authorized — the brief specifies `clean -fd` equivalence, while `clean -ffd` deliberately removes repositories that single-force cleaning preserves; brief.md:24; target/template/src/pdca_harness/integrate.py:622.
- [x] T5 Judgment — Confirm the affected-path prior-art conclusion against upstream merged and closed/rejected work — the brief records that search, but the supplied target contains only a synthetic base commit and no remote, so it cannot independently establish that no competing fix was missed; brief.md:29.
- [x] Validation — fitness-to-purpose — Decide whether discarding non-ignored integration-tree contents while retaining ignored caches is the intended operational policy — passing real-Git regressions establish behavior, while ownership and cache policy require maintainer sign-off; brief.md:24; target/template/src/pdca_harness/integrate.py:620; target/template/tests/test_integrate_clean_tree.py:247.
- [x] **Criterion (3) cannot go red in the default mode.** The brief says: "the fold raises `IntegrationError` instead of going on to merge another bundle into that tree, in the default mode and in the carry's `skipped` mode … Pre-fix … (3) continues." That is true only for `skipped` mode. In the default mode (`skipped is None`), any non-zero `_merge` makes `_merge_published` raise. It raises at `integrate.py:477-485`, and `fold` re-raises at `integrate.py:437-438`, whether or not the abort worked. So in the default mode the fold already raises `IntegrationError` before the patch. The default-mode leg is green before the patch and proves nothing, and the C4 revert-the-fix gate cannot show RED for it. The planner should do one of two things. Option A: limit the RED claim for (3) to `skipped` mode. Option B: state the real default-mode effect of a failed abort and test that. That effect is a mid-merge tree (`MERGE_HEAD` left in place) that the *next* fold inherits, and the reset-before-fold half of the fix is what covers it.
- [x] **Raising on a failed abort in `skipped` mode changes what the carry does, and the brief does not say so.** `skipped` exists so the #646 carry keeps going past a bundle that fails (`integrate.py:436-439`: "this bundle only; the merge was aborted"). Criterion (3) makes a failed abort stop the whole carry, so every later bundle in that carry is lost too. A `reset --hard HEAD` after a failed abort would also undo the half-done merge and keep the carry going. The brief picks "raise" and does not weigh the other option or say who decided it. That is a design decision for a human to make at sign-off, not something to settle in the test.
- [x] **The scope does not say which clean is required, and that affects the tests and other behaviour.** The scope says "start from a tree that holds exactly its start ref". The issue suggests "`git reset --hard` + `git clean -fdx`, or equivalent" or "the re-gate runs in a separate tree", but the brief does not pick one. Criterion (1) uses an untracked file that is *not* gitignored. A `git clean -fd` without `-x` would therefore pass (1) yet still leave ignored build output behind. That output can also block a merge when a later branch commits a path the base ignores, and then the brief's invariant ("Nothing left … can change what a fold does") is not met. If the invariant is meant to include ignored files, the brief should name `-x` or add a test case with a `.gitignore`d leftover. If it is not, the invariant should say ignored files are excluded.
- [x] **"crashed fold or carry" is in the invariant but no criterion tests it.** The invariant lists "an aborted or failed merge, a crashed fold or carry". Criteria (1)-(3) only cover leftovers from the re-gate and a failed abort inside a single fold. The case the invariant's self-test leans on ("an aborted merge or a crashed carry leaves the same state") has no red→green test: a fold that starts in a tree left mid-merge (`MERGE_HEAD` present) by an earlier fold. A cheap fix is to add a test that starts a fold in a tree with a merge left in progress. Without one, Check can only accept the "every user" claim on trust.
- [x] T5 Judgment — Confirm the affected-path merged and closed/rejected prior-art audit — the brief lists it, but this artifact-only checkout has one synthetic base commit and no remotes, so its historical conclusions cannot be independently settled here; brief.md:29, review-environment.log:9.
- [x] T5 Judgment — Confirm the affected-path merged-history and closed/rejected-work conclusions before accepting novelty — the brief records that search, but this one-commit target has no remote or historical PR evidence with which to independently settle it; brief.md:29; affected source target/template/src/pdca_harness/integrate.py:445.

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
- By / date: Eduard Ralph / 2026-10-10

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 4 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
