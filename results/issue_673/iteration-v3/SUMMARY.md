# Result — issue 673 / fold-stops-on-a-revert-brought-by-a-bundle-branch

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: #623 made a fold stop before pushing when taking the base in would remove a bundle's work from the line. The check runs only for the base merge: `_take_in_base` (`template/src/pdca_harness/integrate.py:699-746`) calls `_undone_paths` (`:804-838`) after merging the base, and only `_gone_branch` reaches it (called from `_merge_published` at `:620`). A bundle's own branch is merged by `_merge_published` (`:608-635`) with no such check. So a later bundle whose branch was cut from (or updated from) a base that already holds a revert of work on the line brings that revert onto the line when it is folded, silently. Example: `A` is on the line; `A`'s PR merges into `main` (its branch kept) and the maintainer reverts it on `main`; `B` is then published cut from `main`. Folding `[A, B]` skips `A` (already in the line) and merges `B`. The merge base is `A`'s commit, `B`'s side deletes `a.txt`, so `a.txt` disappears from the line and the fold pushes. This is gap 2 of the issue.
  Gap 1 (detection is per file from the line's cut point, so a partial revert inside a file another change also touched, or a revert of work below the cut point, is not seen) is not fixed here; it is documented as an accepted limit (see Scope).
- Success criterion: Real-git tests with the `StackFoldGit` fixture of `template/tests/test_integrate_stack_bases.py:123-256` and its `_revert_on_main` helper (`:459-466`), calling `integrate.fold` directly:
  (1) **A bundle branch that brings a revert stops the fold.** `a = _publish("A", {"a.txt": "a\n"})`; `fold([a], folded_this_run={})` → line tip `T1`; `_merge_pr("A")` (branch kept); `_revert_on_main("-m", "1", "HEAD")`; `b = _publish("B", {"b.txt": "b\n"})` (cut from the reverted `origin/main`). `integrate.fold(cfg, [a, b], folded_this_run={TARGET: T1})` raises `IntegrationError`. Its message names `a.txt`, `issue_A` (whose work it would remove) and `issue_B` (whose branch brings the change), and the line on origin is still at `T1` (nothing pushed).
  (2) **Under the carry's `skipped` mode the bundle is skipped, not the fold.** Same history, `integrate.fold(cfg, [a, b], folded_this_run={TARGET: T1}, skipped=skipped)`: `skipped` has an entry for `issue_B` naming `a.txt`, the line is not reset below `T1`, and `a.txt` is still on the line's tip To show `skipped` skips one bundle and not the rest of the fold, add `d = _publish("D", {"d.txt": "d\n"}, cut_from=f"origin/{LINE}")` and fold `[a, b, d]`: assert `list(skipped) == ["issue_B"]`, `d.txt` and `a.txt` are both on the line's tip, and the revert commit on `main` is not an ancestor of the tip (the shape of the existing test at `test_integrate_stack_bases.py:585-602`).
  (2b) **A branch UPDATED from the reverted base stops the fold too.** `A` folded to `T1` as in (1); `b = _publish("B", {"b.txt": "b\n"})` cut from `origin/main` BEFORE the revert; then `_merge_pr("A")`, `_revert_on_main("-m", "1", "HEAD")`, then `fx._update_branch("B")` (`test_integrate_stack_bases.py:199-204`, GitHub's "Update branch": a merge commit on `fix/B` that brings the revert). `fold(cfg, [a, b], folded_this_run={TARGET: T1})` raises `IntegrationError` naming `a.txt`, `issue_A` and `issue_B`, and the line stays at `T1`. This pins that the "its own commits" exemption does not count a merge-from-base commit on the PR branch as `B`'s own deletion of `a.txt` (`_own_commits` counts merge commits made on the branch, `integrate.py:789-790`, so the exemption must judge the change a commit makes against its first parent, or an equivalent rule; say which in `build-notes.md`).
  (3) **A bundle's own change is not a revert.** `A` adds `a.txt` and is folded; `C` is published cut from the line (`cut_from=f"origin/{LINE}"`) and its own commit deletes `a.txt` (a dependent that removes the file on purpose). `fold([a, c], folded_this_run={TARGET: T1})` merges `C` and pushes; no error. The same for a branch that only edits `a.txt` with new content.
  (4) **Nothing else changes.** The existing #623 cases (`test_integrate_stack_bases.py:510-645`), whose assertions on the base-merge wording ("taking origin/main in would remove", `:523-524`, `:597`) stay byte-compatible: the base-merge message in `_take_in_base` is not reworded, and the new bundle-branch refusal has its own message. #633 cases and every test in `template/tests/test_flow_same_wave_conflict.py` and `template/tests/test_flow_resume_stack_prereqs.py` stay green.
  Pre-fix, (1), (2) and (2b) fail: the fold pushes a line without `a.txt`. That is the RED.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: Apply the #623 "would this merge remove work from the line" judgment to every bundle-branch merge of a fold as well as to the base merge, so a bundle merge that would undo a path the line changed (absent its own commits doing so) is undone and refused like the base case: it raises under the in-run fold, and under `skipped` only that bundle is skipped. The refusal names the path(s), the bundle(s) whose work it would remove, and the bundle whose branch brought the change. Document gap 1 as an accepted limit next to the existing #623 text in `docs/07-crosscutting.md` (`:680-684`) and in `integrate.py`'s module docstring (`:43-58`): a partial revert inside a file that the line also changed, and a revert of work below the line's cut point (already on the base), are not detected. / out of scope: detecting gap 1; the other two #623 limits (they fail safe); the #674 same-wave conflict path (`held_out`), which concerns textual conflicts; changing what the fold does with a gone branch; exit codes (693).

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

Review issue #673: stop a stack fold before a bundle branch imports a base revert that removes work already on the integration line, while allowing the bundle's own intentional changes.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The required refusal, carry continuation, intentional-change exemption, and accepted detection limits are explicit and testable; `brief.md:12`, `brief.md:26`, `target/docs/07-crosscutting.md:684`. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing the production fix while retaining the regression tests produces 11 assertion failures in 14 tests, including a missing refusal and an empty skip record; `review-red-green.log:7`, `review-red-green.log:140`, `review-red-green.log:152`. |
| C3 Change | PASS | The patch covers the previously unchecked successful bundle merge, preserves refusal rollback, and stays within the stated production/test/documentation scope; reverse-apply checking succeeds against the supplied target; `target/template/src/pdca_harness/integrate.py:697`, `target/template/src/pdca_harness/integrate.py:728`. |
| C4 Verification (red→green) | PASS | Restoring the patch changes the reproduced failures to green: all 111 focused tests pass, including the 14 new cases and the required existing stack/conflict/resume suites; `review-red-green.log:150`, `review-red-green.log:194`, `target/template/tests/test_integrate_revert_via_branch.py:162`. |
| C5 Causal adequacy | PASS | The inherited removal is checked before push, and exemption follows the commit responsible for the path's current state; independent probes also distinguish inherited existing-file content reversions from intentional restoration; no optional-capability/load-time guard smell found; `target/template/src/pdca_harness/integrate.py:728`, `target/template/src/pdca_harness/integrate.py:937`, `review-probes.log:1`. |
| T1 Structure | PASS | The existing fold/error boundaries contain the change; shared attribution and refusal formatting avoid divergent base-versus-branch decisions, and failed rollback stops even the carry; `target/template/src/pdca_harness/integrate.py:578`, `target/template/src/pdca_harness/integrate.py:853`, `target/template/src/pdca_harness/integrate.py:1009`. |
| T2 Shape | PASS | Independent docs lint and the 22-page render/link audit pass, as does whitespace checking; frozen host-parity output corroborates these checks; `review-docs.log:1`, `gate-logs/host-ci-docs.log:10`. |
| T3 Runtime | PASS | Independent offline discovery completes 2,490 tests with two skips and no failures; frozen root-suite evidence records 24 passing tests including actual render/update cases; `review-suite.log:1817`, `gate-logs/T3-suite.log:38`, `gate-logs/T3-suite.log:54`. |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; their substantive audit is deferred to the mandatory publish rerun, not treated as verified here; `gate-logs/T4-contribution.log:10`. |
| T5 Judgment | NEEDS-HUMAN | Accept or revise naming both bundles when their diverged branches share the relevant commit but neither contains the other's current tip — the refusal is safe, but the message can describe the incoming bundle as removing its own work; this is now an explicit tested attribution policy; `target/template/src/pdca_harness/integrate.py:962`, `target/template/tests/test_integrate_revert_via_branch.py:272`. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Confirm this protection is sufficient for the intended workflow with the Plan-accepted limits — partial-file reverts and work below the line's cut point remain undetected and require operator review; passing Git regressions cannot decide that operational tradeoff; `brief.md:6`, `target/docs/07-crosscutting.md:691`. |

No implementation defect was established. The ambiguous attribution above is a policy decision, not an implementation retry: the previous round explicitly allowed accepting and testing that behavior (`brief.md:48`), and the new regression pins it.

Independent verification used the disposable target only. The tracked fix was stashed, the unchanged new test file was run against the pre-fix production code, and the stash was restored before the green run. `git apply --reverse --check ../patch.diff` succeeds in `target`, so citations ground on the supplied patched source without a stale-target caveat. The target's source changes were preserved.

The additional real-Git probes changed an existing `base.txt`, then imported its full-content revert through both a newly cut branch and an updated branch: both were refused with the remote line unchanged. A dependent intentionally restoring the same file's original content merged successfully (`review-probes.log:1`). These exercise more than the added-file deletion histories in the new suite.

The instance-scoped gate wrappers were not used as target-local commands. Their frozen logs were inspected. Copier is not importable in this review interpreter, so the root render/update suite was adjudicated from the captured successful executions in `gate-logs/T3-suite.log:38`, rather than claimed as an independent rerun. The fix's stated Python/Git dependencies were exercised directly; no shim or code-read substituted for the red→green experiment. The contribution gate remains deferred.

Prior-art checking ran by affected path against GitHub's default-branch commit history, including the new test path, and inspected changed-file lists for unmerged PRs among the 100 most recently updated closed PRs. It corroborates the brief's related history: #623 supplied the base-merge check; the matching closed work (#637, #649, #648, #639, #600, #599, #598) concerns other changes. No duplicate fix or rejected version of this bundle-branch check was identified within that search scope (`review-prior-art.log:11`, `review-prior-art.log:27`, `review-prior-art.log:43`, `review-prior-art.log:44`). The supplied target contains only the unrendered integration template, whose project-specific human-only enumeration is still a TODO (`target/template/docs/INTEGRATION.md.jinja:80`); no additional project-specific decision was inferred from it.

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — issue 673 (correctness + reuse/simplification)

Both lenses come out mostly clean. The new check is wired in at the right place:
`_merge_published` reads the tip before the merge (`template/src/pdca_harness/integrate.py:693`)
and calls `_keep_merge` on a clean merge (`:698-700`). It reuses the #623 helpers
(`_undone_paths`, `_reset_line`) and does not copy them. The message builder that was
duplicated is now one helper, `_removed` (`:853-862`), so the base-merge wording stays
byte-identical (`:841-847`). The gates are green: C4 is red without the fix (11 of 14 new
tests fail) and green with it, and T3 ran 2490 tests OK. The "FAILED" lines in
`gate-logs/T3-suite.log` come from tests that simulate leaf failures, not from real failures.

I found no blocking correctness bug. Minor notes:

- `template/src/pdca_harness/integrate.py:727-731`: if `_undone_paths` hits a plain git
  read failure (`_out` at `:870`, or `_in_line` at `:1027`, both raise a plain
  `IntegrationError`), `_keep_merge` resets the line and re-raises. Under the carry's
  `skipped`, `fold` (`:578-583`) then records that bundle as skipped with a "could not
  read …" message instead of stopping the run. The line stays safe because the merge is
  undone. But a broken checkout can show up as a bundle quietly skipped, and every later
  bundle whose check fails the same way gets skipped too. `_take_in_base` (`:833-837`)
  already does this for the base merge. The patch extends it to every bundle merge, which
  makes it much more likely to come up. Raising `IntegrationTreeError` for these read
  failures would stop the carry instead. Low priority; leaving it as is matches the #623
  path.
- `template/src/pdca_harness/integrate.py:941-944`: `_own_removals` asks git which commit
  last set the path (`git rev-list -n 1 <head> -- <path>`, using git's default history
  simplification). An "evil" update merge (a conflict resolved to content neither parent
  had) or a merge that resolved a modify/delete conflict by hand to the deletion lands on
  the merge commit itself. That commit is in `own`, so the removal counts as the bundle's
  change. That is defensible (the branch's author made that choice), but no test pins it.
  If `last` comes back empty, the removal counts as not the bundle's own (fail-safe, a
  refusal). Not a defect; just noting the rule's edges.
- `template/src/pdca_harness/integrate.py:693-696`: `before` is read here, and `_merge`
  reads the same HEAD again (`:1040`). That costs one extra `rev-parse` per bundle. It
  could be folded in by having `_merge` return its `before`. Optional cleanup.
- Cost per bundle: every clean bundle merge now runs `_cut_point` plus two whole-tree
  `git diff --name-only` calls (`:969-974`) before it can return early. That is fine for
  normal batch sizes and runs only once per merge, so no change is needed.
- Tests (`template/tests/test_integrate_revert_via_branch.py`): they cover criteria (1),
  (2), (2b) and (3), plus the merge-from-base trap, a revert merged through a revert PR,
  the shared-commit naming, and a line that will not reset. They import only modules, so
  they fail on their assertions when the fix is removed (C4 confirms this). The
  `stuck` mock (test file `:633-636`) fails every `reset` except one whose last argument
  is `HEAD`. That is narrow but correct for today's `_reset_tree(wt, "HEAD")` at
  `integrate.py:529`. If that call ever changes, the test will fail and show it. No
  action needed.

No NEEDS-HUMAN items from this lens.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T5 Judgment — Accept or revise naming both bundles when their diverged branches share the relevant commit but neither contains the other's current tip — the refusal is safe, but the message can describe the incoming bundle as removing its own work; this is now an explicit tested attribution policy; `target/template/src/pdca_harness/integrate.py:962`, `target/template/tests/test_integrate_revert_via_branch.py:272`.
- [ ] Validation — fitness-to-purpose — Confirm this protection is sufficient for the intended workflow with the Plan-accepted limits — partial-file reverts and work below the line's cut point remain undetected and require operator review; passing Git regressions cannot decide that operational tradeoff; `brief.md:6`, `target/docs/07-crosscutting.md:691`.
- [x] **The "updated from" path is in the defect statement but no test covers it.** The Defect line says the bug hits a branch "cut from (or updated from) a base that already holds a revert". Criterion (1) only builds the "cut from" case (`b = _publish("B", …)` off `origin/main`). The "updated from" case is the one where the new "absent its own commits doing so" exemption can go wrong. `_own_commits` counts a merge commit made on the PR branch as the bundle's own work (docstring at `integrate.py:789-790`). GitHub's "Update branch" merge of the reverted `main` into `fix/B` is exactly such a commit, and it is the commit that brings the revert. If the implementation decides "B's own commits touched `a.txt`" in a way that counts that merge commit, the check is silently exempted. The fixture already has the helper for this (`StackFoldGit._update_branch`, `test_integrate_stack_bases.py:199-204`). Suggest adding a criterion: B is cut from the old `main`, then `_update_branch("B")` runs after the revert, and the fold raises naming `a.txt` / `issue_A` / `issue_B`.
- [x] **Part of criterion (2) cannot be checked as written.** It says "(a later bundle in the same call that brings no revert is still merged)", but the history it specifies is `fold(cfg, [a, b], …, skipped=skipped)`. That list has no bundle after `B`, so the clause cannot be asserted, and it is the only part of (2) that shows `skipped` skips one bundle rather than ending the fold. Suggest naming a third bundle, e.g. `d = _publish("D", {"d.txt": …}, cut_from=f"origin/{LINE}")` folded as `[a, b, d]`, and asserting `list(skipped) == ["issue_B"]`, `d.txt` and `a.txt` on the tip, and that the revert is not an ancestor of the tip. The existing test at `:585-602` does this.
- [x] **The brief says it builds on 672, but 672 is not declared as a dependency.** The Ordering note says "672 (wave 0) edits the fold's skip handling, so this slice builds on it". 672 appears only under `Conflicts with`, and the brief says it is "Verified against … `d6057eb`", where nothing references #672 (no `#672` anywhere in the target). No `dependency-state.json` was provided, so I could not check 672's state. Criterion (2) asserts the `skipped` semantics of `fold` (`integrate.py:537-539`), which is the code 672 changes. If 672 lands first, (2) and the `:5xx` line citations may no longer match. If building on 672 is required, it should be a `Depends on: 672` (so it is checked), not a conflict edge that only sets the order. Otherwise the note should say that (2) is written against pre-672 `skipped` behavior.
- [x] **One citation in the peer-callsite guidance points at the wrong lines.** "Citations expected" says to mirror `_take_in_base` at `integrate.py:719-746`: "record the tip before the merge, call `_undone_paths(…)`". On `d6057eb` the tip is recorded at `:713`, the merge is at `:716`, and `:719-725` is the conflict error message. The correct span is `:712-743`. The same field puts the bundle merge at `:626-635`, but the merge call itself is at `:624`, and the fix's hook point is the `rc == 0` return at `:625-626`. These are small, but Do must cite `path:line`, and Check will compare against these spans.
- [x] **Criterion (4) covers existing tests by line range, so it can miss changed message assertions.** The existing #623 tests assert the base-merge wording ("taking origin/main in would remove", `test_integrate_stack_bases.py:523-524`, `:597`). The brief asks the new refusal to also name "the bundle whose branch brought the change". If Do changes the shared message helper so both refusals use the new wording, these assertions break, and "stay green" will push Do to keep two message formats. It would help to state explicitly whether the base-merge message must stay byte-compatible.
- [x] T5 Judgment — Confirm the path-based prior-art conclusion against merged history and closed/rejected PRs — the brief records a search, but the supplied one-commit target has no remotes or historical objects to independently settle it; brief.md:31.
- [x] T5 Judgment — Confirm the recorded path-based merged-history and closed/rejected-work search is sufficient — the brief lists results, but this supplied target has one synthetic base commit and no remotes, so those historical conclusions cannot be independently settled from this bundle (`brief.md:31`, `review-prior-art.log:1`).

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
- Iteration delta (if iterating): Narrow rebuild — fix the refusal message only; detection logic, refuse/keep decisions, and the base-merge (#623) wording stay as they are. When attribution is ambiguous (two diverged branches share the commit and neither holds the other's current tip — test_integrate_revert_via_branch.py:272), the bundle-branch refusal currently says "merging issue_B's branch … would remove issue_A, issue_B's work", which reads as if B removes its own work. Reword so the incoming bundle is never described as removing its own work: name the bundle(s) whose work is removed, and when git cannot tell which branch made the shared commit, say so plainly (e.g. "work from issue_A or issue_B — git cannot tell which branch made it"). Update the pinned test to the new wording; keep all other tests and the base-merge message byte-compatible.
- By / date: Eduard Ralph / 2026-10-15

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 5 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
- Known limit (#673 gap 1, accepted at Plan): a partial revert inside a file the line also changed is not detected by the fold's revert check — file a follow-up issue so it isn't lost when #673 closes.
- Known limit (#673 gap 1, accepted at Plan): a revert of work below the line's cut point (already on the base) is not detected — file a follow-up issue so it isn't lost when #673 closes.
