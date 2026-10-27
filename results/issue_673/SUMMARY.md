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

Review issue #673: stop a fold when a bundle branch imports a revert of work on the integration line, while allowing intentional branch changes and explaining ambiguous ownership accurately.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The required refusal, carry continuation, intentional-change exemption, and accepted detection limits are explicit and testable; the latest revision requires truthful ownership wording (brief.md:13, brief.md:26, brief.md:52; target/template/tests/test_integrate_revert_via_branch.py:275). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only the production fix leaves all 15 tests runnable and produces 12 assertion failures, including missing refusal and missing carry exclusion, rather than import/tool failures (review-red.log:4, review-red.log:139, review-red.log:158). |
| C3 Change | PASS | The change addresses the unprotected successful branch merge and its refusal message, with documentation and real-git regressions within the agreed scope; ambiguous ownership no longer describes the incoming bundle as removing its own work (target/template/src/pdca_harness/integrate.py:697, target/template/src/pdca_harness/integrate.py:866, target/template/tests/test_integrate_revert_via_branch.py:290). |
| C4 Verification (red→green) | PASS | Restoring the stashed production fix makes all 15 regression tests pass; the independent result matches the frozen gate's actual red→green output (review-red.log:160, review-green.log:4; gate-logs/C4-verify.log:10). |
| C5 Causal adequacy | PASS | Real git distinguishes inherited removal from an intentional own-commit removal, and refusal preserves the pushed tip; extra probes cover existing-file content as well as deletion, with no capability-probe/load-time workaround introduced (target/template/src/pdca_harness/integrate.py:728, target/template/src/pdca_harness/integrate.py:945; review-probes.log:1, review-probes.log:3). |
| T1 Structure | PASS | The new check uses the existing merge/reset/error flow, preserves the base refusal formatter, and tests production through a composed fixture rather than duplicating its suite (target/template/src/pdca_harness/integrate.py:713, target/template/src/pdca_harness/integrate.py:853; target/template/tests/test_integrate_revert_via_branch.py:47, target/template/tests/test_integrate_revert_via_branch.py:61). |
| T2 Shape | PASS | Independent docs lint, 22-page site render/internal-link audit, and git diff whitespace check pass; the frozen host-parity log also records successful lint and link audit (review-docs-lint.log:1, review-docs-render.log:2; gate-logs/host-ci-docs.log:10). |
| T3 Runtime | PASS | Independent offline suite passes 2,491 tests with two skips; frozen evidence records 24 root tests including actual copier render/update cases, while the local root rerun exits 77 for missing importable copier (review-driver.log:1817; gate-logs/T3-suite.log:38, gate-logs/T3-suite.log:54; review-root.log:6). |
| T4 Contribution | N/A | Contribution artifacts are intentionally absent at Check; the frozen deferred row explicitly assigns the substantive PR-description audit to publish (gate-logs/T4-contribution.log:10). |
| T5 Judgment | NEEDS-HUMAN | Confirm the affected-path prior-art search covers merged and closed/rejected work — the brief records that search, but this one-commit target has no remote or closed-PR evidence with which to independently settle it (brief.md:31; review-history.log:1). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the observed refusal/recovery wording and documented per-file/cut-point limits are sufficient for operators — partial reverts and work already below the cut point remain outside detection by the agreed scope (target/docs/07-crosscutting.md:687, target/docs/07-crosscutting.md:693; target/template/tests/test_integrate_revert_via_branch.py:290, target/template/tests/test_integrate_revert_via_branch.py:306). |

No implementation defect was established. This is advisory review, not acceptance.

The target is the supplied disposable checkout, with the patch applied over its synthetic base commit. I stashed only `template/src/pdca_harness/integrate.py`, retained the regression tests for the red leg, and restored the stash before the green leg and full suite. Production, documentation, and test changes remain as supplied. All source citations above refer to this target, not the brief's older line numbers.

The independent runs exercised real local git repositories and the production `integrate.fold` path. The 15 regression tests cover cut-from-base and updated-from-base histories, carry continuation, moved/shared owner tips, the incoming branch's own earlier work, intentional deletions/edits, and reset failure. Two additional real-git probes showed that an inherited revert of `base.txt` content is refused without pushing, while an intentional own-commit restoration of that content is merged (`review-probes.log:1`). Thus the evidence is not limited to file deletion or a topology incapable of exhibiting the bug.

For the revised message, the executed ambiguous-owner test requires `a.txt (work from issue_A or issue_B — git cannot tell which branch made it)` and rejects `issue_B's work`; the incoming-owner case requires `issue_A's earlier work, which its branch no longer has`. The existing base-merge wording test also passes (`target/template/tests/test_integrate_revert_via_branch.py:290`, `target/template/tests/test_integrate_revert_via_branch.py:306`, `target/template/tests/test_integrate_revert_via_branch.py:327`). No visual/manual-only outcome is being asserted.

The instance-scoped wrapper scripts are not supplied as runnable target oracles. Their frozen logs were read: C4 contains the actual 15-test green run and 12-failure red run; C5 records a production-package import; both T2 logs record clean lint and link audits; T3 records successful root and driver suites; T4 explicitly defers to publish. Independent commands reproduced the available underlying checks. The local root runner's missing copier library is a reviewer-host limitation, not a patch failure or a claim that those tests ran locally: the frozen root log explicitly shows render and update cases executing successfully. The brief's Python/git dependency was exercised without a shim.

The affected-path history command returned only `5b7342a pre-fix base ebef78cdddcc42bf6b4513d6daade3327b3b53b8` (`review-history.log:1`), so it cannot independently corroborate the brief's named merged commits and closed PRs. That narrow decision is retained in T5. The supplied `target/template/docs/INTEGRATION.md.jinja:80` contains a TODO rather than additional enumerated project-specific human-only items.

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — issue 673 (round 4)

Overall: no correctness bug found in this round's change. It was scoped to the refusal wording (`_branch_removed`) and the `_reset_line` message. Detection and the keep/refuse decisions match what the earlier rounds signed off on. Gate evidence agrees: C4 shows 12 of the 15 new tests red without the fix (the 3 that pass pre-fix are the criterion (3) "own change is merged" cases, which should pass either way), and T3 ran 2491 tests OK. The notes below are minor. None of them blocks.

## Correctness

- `template/src/pdca_harness/integrate.py:876-887` — `_branch_removed` checked by hand against each kind of `groups`. Only single-bundle groups other than `incoming` go through `_removed`, so `incoming` can never be named as `"<incoming>'s work"`. A shared group is worded as "work from X or Y — git cannot tell…", and a group that is only `incoming` is worded as "earlier work, which its branch no longer has". A path with no owner groups falls back to `note on branch`, because `whose == [""]` filters to empty. A 3-way share reads "work from A, B or C". Tests `test_integrate_revert_via_branch.py:785-819` pin the two new wordings. No bug.
- `template/src/pdca_harness/integrate.py:1039-1046` — `_reset_line` now names what it was undoing (`merged_in`). Both callers pass it: `:730`/`:734` for a bundle branch, `:836`/`:839` for the base. The round-1 finding (the message blamed the base for a bundle-branch reset) is fixed, and `test_integrate_revert_via_branch.py:874-898` covers it, including that `skipped` stays empty because `_LineBroken` is re-raised at `:578-580`.
- `template/src/pdca_harness/integrate.py:962-969` — `_own_removals` only treats the base given by `base_ref` (`{cfg.base_remote}/{base}`, `:700`) as "not the branch's own". The `skip` set (`:1005-1006`) is the line's chain plus that base's first-parent chain. Suppose a branch picked up a revert from somewhere else, for example a different upstream branch it was updated from, or an `Onto branch` parent PR. Then the revert commit looks like the branch's own, and the removal is merged without a word. This fails open, but it is narrower than the case the brief targets, and the brief limits the scope to "cut from, or updated from, the base". Recorded for awareness only, no action asked.

## Reuse / simplification

- `template/src/pdca_harness/integrate.py:1008` and `:1024` — the name `mine` is bound twice in `_undone_paths` with different types: first a set of paths (from `_own_removals`), then a set of commit ids inside the owners loop. Nothing breaks, because the first binding is not used after `:1009`, but it reads as if they were the same thing. Renaming the first one (e.g. `own_paths`) would make it clearer. Cosmetic.
- `template/src/pdca_harness/integrate.py:881` — `whose = [", ".join(...)]` builds a one-item list holding a possibly empty string, and `:886` then filters it out again with `if w`. A plain `solo = [...]` list joined once at the end would say the same thing more directly. Cosmetic.
- `template/src/pdca_harness/integrate.py:833-847` / `:727-742` — `_take_in_base` and `_keep_merge` now run the same "try `_undone_paths`; on error reset and re-raise; on a hit reset and raise" steps. The shared message pieces already moved into `_removed`. The rest is about eight lines repeated twice, with different messages each time. A shared helper would not save much, so leaving it as is seems fine.

## Efficiency

- `template/src/pdca_harness/integrate.py:693-700` — every clean bundle merge now also costs one `rev-parse`, one `rev-list` (`_cut_point`), two `git diff --name-only` calls and, with no cut point, one `hash-object`. The extra walks (`_own_removals`, the owner walks, and the pairwise `_in_line` at `:1025-1026`, which grows with the square of the number of owners) run only when a path was actually undone. That is reasonable for a fold of a few bundles.

No NEEDS-HUMAN items.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — Confirm the affected-path prior-art search covers merged and closed/rejected work — the brief records that search, but this one-commit target has no remote or closed-PR evidence with which to independently settle it (brief.md:31; review-history.log:1).
- [x] Validation — fitness-to-purpose — Decide whether the observed refusal/recovery wording and documented per-file/cut-point limits are sufficient for operators — partial reverts and work already below the cut point remain outside detection by the agreed scope (target/docs/07-crosscutting.md:687, target/docs/07-crosscutting.md:693; target/template/tests/test_integrate_revert_via_branch.py:290, target/template/tests/test_integrate_revert_via_branch.py:306).
- [x] **The "updated from" path is in the defect statement but no test covers it.** The Defect line says the bug hits a branch "cut from (or updated from) a base that already holds a revert". Criterion (1) only builds the "cut from" case (`b = _publish("B", …)` off `origin/main`). The "updated from" case is the one where the new "absent its own commits doing so" exemption can go wrong. `_own_commits` counts a merge commit made on the PR branch as the bundle's own work (docstring at `integrate.py:789-790`). GitHub's "Update branch" merge of the reverted `main` into `fix/B` is exactly such a commit, and it is the commit that brings the revert. If the implementation decides "B's own commits touched `a.txt`" in a way that counts that merge commit, the check is silently exempted. The fixture already has the helper for this (`StackFoldGit._update_branch`, `test_integrate_stack_bases.py:199-204`). Suggest adding a criterion: B is cut from the old `main`, then `_update_branch("B")` runs after the revert, and the fold raises naming `a.txt` / `issue_A` / `issue_B`.
- [x] **Part of criterion (2) cannot be checked as written.** It says "(a later bundle in the same call that brings no revert is still merged)", but the history it specifies is `fold(cfg, [a, b], …, skipped=skipped)`. That list has no bundle after `B`, so the clause cannot be asserted, and it is the only part of (2) that shows `skipped` skips one bundle rather than ending the fold. Suggest naming a third bundle, e.g. `d = _publish("D", {"d.txt": …}, cut_from=f"origin/{LINE}")` folded as `[a, b, d]`, and asserting `list(skipped) == ["issue_B"]`, `d.txt` and `a.txt` on the tip, and that the revert is not an ancestor of the tip. The existing test at `:585-602` does this.
- [x] **The brief says it builds on 672, but 672 is not declared as a dependency.** The Ordering note says "672 (wave 0) edits the fold's skip handling, so this slice builds on it". 672 appears only under `Conflicts with`, and the brief says it is "Verified against … `d6057eb`", where nothing references #672 (no `#672` anywhere in the target). No `dependency-state.json` was provided, so I could not check 672's state. Criterion (2) asserts the `skipped` semantics of `fold` (`integrate.py:537-539`), which is the code 672 changes. If 672 lands first, (2) and the `:5xx` line citations may no longer match. If building on 672 is required, it should be a `Depends on: 672` (so it is checked), not a conflict edge that only sets the order. Otherwise the note should say that (2) is written against pre-672 `skipped` behavior.
- [x] **One citation in the peer-callsite guidance points at the wrong lines.** "Citations expected" says to mirror `_take_in_base` at `integrate.py:719-746`: "record the tip before the merge, call `_undone_paths(…)`". On `d6057eb` the tip is recorded at `:713`, the merge is at `:716`, and `:719-725` is the conflict error message. The correct span is `:712-743`. The same field puts the bundle merge at `:626-635`, but the merge call itself is at `:624`, and the fix's hook point is the `rc == 0` return at `:625-626`. These are small, but Do must cite `path:line`, and Check will compare against these spans.
- [x] **Criterion (4) covers existing tests by line range, so it can miss changed message assertions.** The existing #623 tests assert the base-merge wording ("taking origin/main in would remove", `test_integrate_stack_bases.py:523-524`, `:597`). The brief asks the new refusal to also name "the bundle whose branch brought the change". If Do changes the shared message helper so both refusals use the new wording, these assertions break, and "stay green" will push Do to keep two message formats. It would help to state explicitly whether the base-merge message must stay byte-compatible.
- [x] size backstop — this slice is behaving oversized: 3 round(s) already spent (threshold 3). Recommend answering `iterate-plan` at sign-off and authoring the split in the re-plan (`pdca split`), rather than `iterate-do`: a slice that is too big yields implementation-shaped findings every round, and splitting authors briefs, which is Plan's beat.

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
- By / date: Eduard Ralph / 2026-10-15

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 5 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
