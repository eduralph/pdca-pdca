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

Review issue #673: stop a fold before a bundle branch imports a base revert that removes work already on the integration line, while preserving intentional branch changes and documenting the accepted detection limits.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief specifies observable refusal, carry continuation, intentional-change acceptance, and bounded exclusions; the documented partial-file and below-cut-point limits match that scope (`brief.md:10`, `brief.md:26`, `target/docs/07-crosscutting.md:684`). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing the tracked fix while retaining the new tests produced eight assertion failures across 11 tests, including the inherited-revert and carry histories; tests loaded and exercised real git (`review-rerun.log:22`, `review-rerun.log:115`, `review-rerun.log:134`). |
| C3 Change | PASS | The three affected files stay within the specified fold behavior, regression coverage, and documentation; the existing base-refusal wording remains intact (`target/template/src/pdca_harness/integrate.py:698`, `target/template/src/pdca_harness/integrate.py:841`, `target/template/tests/test_integrate_revert_via_branch.py:156`). |
| C4 Verification (red→green) | PASS | Restoring the same fix made all 11 regression tests pass, and 97 existing stack-base, same-wave-conflict, and resume-prerequisite tests passed independently; this reproduces the frozen C4 evidence (`review-rerun.log:138`, `review-rerun.log:171`, `review-rerun.log:202`, `gate-logs/C4-verify.log:10`). |
| C5 Causal adequacy | PASS | The previously unchecked successful merge is now judged before push, and removal provenance distinguishes inherited reverts from intentional changes; historical-touch regressions and three additional real-git probes pass, including whole-file restoration and a topic's intentional deletion (`target/template/src/pdca_harness/integrate.py:696`, `target/template/src/pdca_harness/integrate.py:939`, `target/template/tests/test_integrate_revert_via_branch.py:214`, `review-probes.log:1`). |
| T1 Structure | PASS | The branch and base paths share removal detection and attribution; refusals restore the pre-merge tip, and reset failure still stops the carry, preventing a damaged line from being pushed (`target/template/src/pdca_harness/integrate.py:727`, `target/template/src/pdca_harness/integrate.py:832`, `target/template/src/pdca_harness/integrate.py:1000`, `target/template/src/pdca_harness/integrate.py:577`). |
| T2 Shape | PASS | Independent whitespace checking, docs lint, and rendering all 22 pages with the internal-link audit passed; the frozen docs and host-CI parity logs agree (`review-docs.log:1`, `review-docs.log:8`, `gate-logs/T2-docs.log:10`, `gate-logs/host-ci-docs.log:10`). |
| T3 Runtime | PASS | The independently executed 108 relevant tests and three additional real-git probes pass; the frozen full-suite log separately records 24 root tests passing and 2,487 driver tests passing with two skips (`review-rerun.log:171`, `review-rerun.log:202`, `review-probes.log:1`, `gate-logs/T3-suite.log:54`, `gate-logs/T3-suite.log:1874`). |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the frozen gate explicitly defers its substantive PR-body/tracker audit to the mandatory publish rerun (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Confirm the recorded path-based merged-history and closed/rejected-work search is sufficient — the brief lists results, but this supplied target has one synthetic base commit and no remotes, so those historical conclusions cannot be independently settled from this bundle (`brief.md:31`, `review-prior-art.log:1`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Accept the remaining partial-file and below-cut-point blind spots for the intended workflow — the tested histories now preserve line work, but those explicitly accepted classes still require operator review (`brief.md:7`, `target/docs/07-crosscutting.md:691`). |

Independent checks used the provided disposable target only. The tracked fix was stashed for the red leg and restored before the green leg; no production or test source was edited. Source citations above refer to the patched target, which contains the preceding #672 carry handling; the brief's older line numbers were re-grounded rather than treated as patch defects.

The regression command was `PYTHONPATH=src python3 -m unittest discover -s tests -p test_integrate_revert_via_branch.py -v` from `target/template`. Existing coverage used `PYTHONPATH=src python3 -m unittest tests.test_integrate_stack_bases tests.test_flow_same_wave_conflict tests.test_flow_resume_stack_prereqs`. Temporary fixtures stayed under this review directory. The production-import scanner also passed independently (`review-scanner.log:2`); inspection and the red leg establish that the tests execute production behavior, beyond that scanner's import heuristic.

The instance-scoped gate wrappers are not part of this target. Their frozen logs were read; equivalent focused checks were run directly where available. The full root/render-update and driver-suite results above are frozen evidence, not claimed as independent full-suite reruns. Python and real git exercised the defect topology without a replacement tool or an unmet external dependency. The reset-failure case intentionally injects a failed reset to verify error handling. No capability probe or load-time fallback was introduced, so the C5 symptom-guard trigger does not apply. The supplied integration template enumerates no additional project-specific human-only items (`target/template/docs/INTEGRATION.md.jinja:80`).

No implementation defect was established. Prior-art adjudication and fitness-to-purpose remain human decisions; this review is advisory.

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — issue 673

Lens: bugs the patch adds, plus reuse / simplification / efficiency. Line numbers are on the
patched target (`$PDCA_TARGET`). The gates I can see all pass: C4 shows red before the fix
(8 of 11 fail) and green after, and the full suite runs green (T3: 2487 tests OK).

I found no blocking correctness bug. The own-removal rule (`git rev-list -n 1 <head> -- <path>`,
which follows the parent a merge took the path from, checked against `_own_commits`) handles
every history in the brief. That includes the case iteration 1 got wrong: a branch that touched
a.txt earlier but whose current a.txt came from the base. The `_reset_line` wording finding
from iteration 1 is fixed (`integrate.py:1000-1007`), and a test covers it
(`test_integrate_revert_via_branch.py`, the "will not go back" case).

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/integrate.py:988`: a bundle's walk now stops
  only at a commit that *equals* another owner's current tip (`skip | {t for t in tips.values() if t != tip}`).
  Suppose B was cut from `fix/A`, and A later got another commit pushed. Then A's current tip
  is not in B's history. B's walk goes past it into A's commits, and B gets named as an owner
  of a.txt too. The bundle-branch refusal would then say "a.txt (issue_A, issue_B)" and
  "issue_A, issue_B's work", which wrongly blames B for removing its own work. This only
  affects the error message: the refuse/keep decision does not change. The same change also
  affects the #623 base-merge message, because `_undone_paths` is shared. Possible fix:
  stop the walk at any commit reachable from another owner's tip (the
  `merge-base --is-ancestor` check, or one `rev-list` per other tip), or accept this and add
  a test that pins the current behavior. No test covers an advanced `fix/A`.
- `template/src/pdca_harness/integrate.py:726-730`: if a git read inside the new check fails,
  `_out` raises a plain `IntegrationError` (`:864-872`). Under the carry's `skipped`, `fold`
  then records that bundle as skipped (`:577-582`) instead of stopping, the same as a real
  refusal. `_take_in_base` (`:832-836`) already behaves this way, but it only runs for a gone
  branch. This check runs on every clean bundle merge, so a passing git glitch is now more
  likely to drop a good bundle quietly. The fix would be to wrap the failure in
  `IntegrationTreeError`, which `fold` re-raises even under `skipped`. Low risk, so I left it
  advisory and did not tag it.
- `template/src/pdca_harness/integrate.py:965-970` (efficiency): every clean bundle merge now
  pays for `_cut_point` plus two full diffs from the cut point (`old`→`before`,
  `old`→`HEAD`). Within one fold the cut point never changes. Only paths the merge itself
  changed can have been undone, so checking `_changed(wt, before, "HEAD")` first (usually
  small) would skip most of the work. This is cheap for today's line sizes, and the suite
  time did not get worse. It's an optional cleanup.
- Reuse: pulling the message builder out into `_removed` (`integrate.py:852-861`) and making
  `_reset_line` name what it undid (`:1000`) removes the duplication between `_take_in_base`
  and `_keep_merge`. The base-merge wording ("taking … in would remove", `:842`) is unchanged,
  as criterion (4) requires. Nothing more to merge here.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T5 Judgment — Confirm the recorded path-based merged-history and closed/rejected-work search is sufficient — the brief lists results, but this supplied target has one synthetic base commit and no remotes, so those historical conclusions cannot be independently settled from this bundle (`brief.md:31`, `review-prior-art.log:1`).
- [ ] Validation — fitness-to-purpose — Accept the remaining partial-file and below-cut-point blind spots for the intended workflow — the tested histories now preserve line work, but those explicitly accepted classes still require operator review (`brief.md:7`, `target/docs/07-crosscutting.md:691`).
- [ ] `template/src/pdca_harness/integrate.py:988`: a bundle's walk now stops only at a commit that *equals* another owner's current tip (`skip | {t for t in tips.values() if t != tip}`). Suppose B was cut from `fix/A`, and A later got another commit pushed. Then A's current tip is not in B's history. B's walk goes past it into A's commits, and B gets named as an owner of a.txt too. The bundle-branch refusal would then say "a.txt (issue_A, issue_B)" and "issue_A, issue_B's work", which wrongly blames B for removing its own work. This only affects the error message: the refuse/keep decision does not change. The same change also affects the #623 base-merge message, because `_undone_paths` is shared. Possible fix: stop the walk at any commit reachable from another owner's tip (the `merge-base --is-ancestor` check, or one `rev-list` per other tip), or accept this and add a test that pins the current behavior. No test covers an advanced `fix/A`.
- [ ] **The "updated from" path is in the defect statement but no test covers it.** The Defect line says the bug hits a branch "cut from (or updated from) a base that already holds a revert". Criterion (1) only builds the "cut from" case (`b = _publish("B", …)` off `origin/main`). The "updated from" case is the one where the new "absent its own commits doing so" exemption can go wrong. `_own_commits` counts a merge commit made on the PR branch as the bundle's own work (docstring at `integrate.py:789-790`). GitHub's "Update branch" merge of the reverted `main` into `fix/B` is exactly such a commit, and it is the commit that brings the revert. If the implementation decides "B's own commits touched `a.txt`" in a way that counts that merge commit, the check is silently exempted. The fixture already has the helper for this (`StackFoldGit._update_branch`, `test_integrate_stack_bases.py:199-204`). Suggest adding a criterion: B is cut from the old `main`, then `_update_branch("B")` runs after the revert, and the fold raises naming `a.txt` / `issue_A` / `issue_B`.
- [ ] **Part of criterion (2) cannot be checked as written.** It says "(a later bundle in the same call that brings no revert is still merged)", but the history it specifies is `fold(cfg, [a, b], …, skipped=skipped)`. That list has no bundle after `B`, so the clause cannot be asserted, and it is the only part of (2) that shows `skipped` skips one bundle rather than ending the fold. Suggest naming a third bundle, e.g. `d = _publish("D", {"d.txt": …}, cut_from=f"origin/{LINE}")` folded as `[a, b, d]`, and asserting `list(skipped) == ["issue_B"]`, `d.txt` and `a.txt` on the tip, and that the revert is not an ancestor of the tip. The existing test at `:585-602` does this.
- [ ] **The brief says it builds on 672, but 672 is not declared as a dependency.** The Ordering note says "672 (wave 0) edits the fold's skip handling, so this slice builds on it". 672 appears only under `Conflicts with`, and the brief says it is "Verified against … `d6057eb`", where nothing references #672 (no `#672` anywhere in the target). No `dependency-state.json` was provided, so I could not check 672's state. Criterion (2) asserts the `skipped` semantics of `fold` (`integrate.py:537-539`), which is the code 672 changes. If 672 lands first, (2) and the `:5xx` line citations may no longer match. If building on 672 is required, it should be a `Depends on: 672` (so it is checked), not a conflict edge that only sets the order. Otherwise the note should say that (2) is written against pre-672 `skipped` behavior.
- [ ] **One citation in the peer-callsite guidance points at the wrong lines.** "Citations expected" says to mirror `_take_in_base` at `integrate.py:719-746`: "record the tip before the merge, call `_undone_paths(…)`". On `d6057eb` the tip is recorded at `:713`, the merge is at `:716`, and `:719-725` is the conflict error message. The correct span is `:712-743`. The same field puts the bundle merge at `:626-635`, but the merge call itself is at `:624`, and the fix's hook point is the `rc == 0` return at `:625-626`. These are small, but Do must cite `path:line`, and Check will compare against these spans.
- [ ] **Criterion (4) covers existing tests by line range, so it can miss changed message assertions.** The existing #623 tests assert the base-merge wording ("taking origin/main in would remove", `test_integrate_stack_bases.py:523-524`, `:597`). The brief asks the new refusal to also name "the bundle whose branch brought the change". If Do changes the shared message helper so both refusals use the new wording, these assertions break, and "stay green" will push Do to keep two message formats. It would help to state explicitly whether the base-merge message must stay byte-compatible.
- [ ] T5 Judgment — Confirm the path-based prior-art conclusion against merged history and closed/rejected PRs — the brief records a search, but the supplied one-commit target has no remotes or historical objects to independently settle it; brief.md:31.

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
- Iteration delta (if iterating): Auto-iterate (round 2): rebuilding for the implementation-level findings — `template/src/pdca_harness/integrate.py:988`: a bundle's walk now stops only at a commit that *equals* another owner's current tip (`skip | {t for t in tips.values() if t != tip}`). Suppose B was cut from `fix/A`, and A later got another commit pushed. Then A's current tip is not in B's history. B's walk goes past it into A's commits, and B gets named as an owner of a.txt too. The bundle-branch refusal would then say "a.txt (issue_A, issue_B)" and "issue_A, issue_B's work", which wrongly blames B for removing its own work. This only affects the error message: the refuse/keep decision does not change. The same change also affects the #623 base-merge message, because `_undone_paths` is shared. Possible fix: stop the walk at any commit reachable from another owner's tip (the `merge-base --is-ancestor` check, or one `rev-list` per other tip), or accept this and add a test that pins the current behavior. No test covers an advanced `fix/A`.. Deferred, not addressed here: 6 finding(s) that need human judgment, held in deferred-findings.json for the human at handover — not build work
- By / date: auto-iterate / 2026-10-15

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 5 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
