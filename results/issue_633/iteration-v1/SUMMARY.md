# Result — issue 633 / fold-refuses-a-rewritten-carried-branch

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: The stack fold carries each published PR branch onto the run's integration line by merging the branch's CURRENT tip (`integrate._merge_published`, `template/src/pdca_harness/integrate.py:461-485`). It skips a tip already in the line (`:472-473`) and otherwise merges it, so a fast-forward fixup reaches the line at the next fold (intended: `integrate.py:39-40`, `docs/07-crosscutting.md:665-666`). But `publish` force-pushes when a bundle is re-published (`git push --force-with-lease -u origin <branch>`, `template/src/pdca_harness/publish.py:312-319`; needed for #108). The single-step `pdca publish <id>` takes no drive claim (`template/src/pdca_harness/cli.py:487-488`; #573), so nothing stops it from running in another terminal while a flow run is live. When a bundle already folded this run is re-published that way, its branch is REWRITTEN. The old commits stay on the line, the new tip is not in the line, and the next fold merges it on top: duplicate or conflicting content on the line every later wave builds on, and no error.
- Success criterion: With the patch, on the real-git fixture of `template/tests/test_integrate_stack_bases.py` (`StackFoldGit`):
  (1) **Rewrite refused.** `a = self._publish("A", {"a.txt": "a\n"})`; `integrate.fold(cfg, [a], folded_this_run={})`; `t1 = self._tip(LINE)`. `fix/A` is then force-pushed to a commit cut from `origin/main` that does not contain the folded tip and does not touch `a.txt` (`self._push_from_human({"a2.txt": "a, rebuilt\n"}, to="fix/A", force=True)`, so merging it would not conflict). `b = self._publish("B", …)`. `integrate.fold(cfg, [a, b], folded_this_run={TARGET: t1})` raises `integrate.IntegrationError` before merging anything. The message contains `issue_A`, `fix/A` and the word `rewritten`, and says what to do (see Scope). Origin's line is still at `t1`. Both folds pass the same `carried={}` mapping (see Scope). (1b) When the rewritten commit DOES conflict with what the line holds (it rewrites `a.txt`), the refusal still contains `rewritten`, and does NOT contain `cross-wave overlap`.
  (2) **Fast-forward still carried.** `test_a_fixup_pushed_onto_a_live_branch_is_merged_by_the_next_fold` (`test_integrate_stack_bases.py:351-366`) and every other test in the file still pass. A branch that only moved forward from what the line holds is merged as today.
  (2b) **Carry unaffected.** A fold called with `skipped={}` and no `carried` mapping (as the #646 pre-wave carry calls it, `flow.py:931-933`) behaves as today.
  (3) **Gone branch unchanged.** A branch deleted after its PR merged is still judged by `_gone_branch` as today (the existing gone-branch tests pass).
  Pre-fix, (1) succeeds and the line tip holds both A's old commit and the rebuilt one, and (1b) is blamed on a cross-wave overlap (`integrate.py:477-481`). That is the RED.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: Make the in-run fold detect that a branch it already carried onto the line this run was rewritten (its current tip no longer contains the head the line took from it) and stop with a message naming the bundle, before any merge or push. Design (chosen, so Check judges one shape): `integrate.fold` takes an optional `carried: dict[str, str] | None` mapping, filled in place like `skipped` (bundle name → the head the fold merged, or found already in the line, for that bundle). The flow creates one mapping per run and passes it to every in-run fold through `_fold_lines` (`flow.py:800-820`, the in-run call at `:2296-2299`); this `flow.py` plumbing is part of this bundle. Before merging anything (next to the up-front `refs` resolution, `integrate.py:347-360`, so it is outside the per-bundle `skipped` net), the fold checks every bundle with a recorded head H whose branch still resolves: H must be the branch's current tip or an ancestor of it (`_in_line`-style ancestry, fail-closed on a git error); otherwise it raises. Never decided by a commit message (`integrate.py:41`). The #646 carry passes no mapping, so the check never fires there (criterion (2b)); it runs before any in-run fold, so there is nothing of this run to compare. Behaviour change, accepted: a carried PR branch updated with "Update with rebase", or force-pushed by a contributor mid-run, also stops the run; only fast-forward updates (including GitHub's merge-style "Update branch") are carried. The message says so and tells the operator to restore the branch to a descendant of the carried head, or let the run stop and re-issue. Update the docstring at `integrate.py:39-40` and the sentence at `docs/07-crosscutting.md:665-666` to say commits pushed onto a carried branch reach the line only when they extend it (fast-forward). / out of scope: making `pdca publish` take a drive claim or refuse while a run is live (#573); changing `publish`'s `--force-with-lease` re-publish (#108 needs it); the #646 pre-wave carry's judgment of an origin line left by an earlier run (`integrate.foreign_commit` already refuses a commit it cannot account for, `integrate.py:196-207`); a gone (deleted) branch (`_gone_branch`, unchanged); #653 (which head the carry folds).

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: pass — C4 PASS — red without the fix, green with it
- C5 added test exercises production, not a copy: pass — patch adds no new test file — nothing to assert

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

Review issue #633: stop an in-run stack fold from carrying a rewritten PR branch while preserving fast-forward updates, pre-wave carry, and deleted-branch handling.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The accepted scope defines falsifiable ancestry and unchanged-origin outcomes, preserves existing carry behavior, and explicitly accepts stopping on rebases; brief.md:12, brief.md:26. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only the production changes reproduced silent acceptance, the misleading overlap diagnosis, and missing flow state: 3 failures among 52 tests; target/template/tests/test_integrate_stack_bases.py:390, review-red.log:28. |
| C3 Change | PASS | The four changed files stay within the chosen fold, flow-state, regression-test, and documentation scope; target/template/src/pdca_harness/flow.py:2103, target/template/src/pdca_harness/integrate.py:281, target/docs/07-crosscutting.md:666. |
| C4 Verification (red→green) | PASS | Restoring the production changes made all 52 tests pass; the independent result agrees with the frozen gate, but does not cover the additional C5 race; review-green.log:25, gate-logs/C4-verify.log:64. |
| C5 Causal adequacy | NEEDS-HUMAN [impl] | Close the checked-head/merged-head race for multiple bases sharing one checkout — a later fetch can replace an already-checked ref and silently push both old and rewritten commits; target/template/src/pdca_harness/integrate.py:398, target/template/src/pdca_harness/integrate.py:529, review-multibase.log:1. |
| T1 Structure | PASS | Per-run state stays owned by the flow and is recorded only after a successful push; existing callers can omit it without changing carry semantics; target/template/src/pdca_harness/flow.py:2304, target/template/src/pdca_harness/integrate.py:492. |
| T2 Shape | PASS | Independent docs lint, 22-page render/link audit, and git diff --check passed; both frozen docs gates agree; target/docs/07-crosscutting.md:666, gate-logs/T2-docs.log:11, gate-logs/host-ci-docs.log:11. |
| T3 Runtime | PASS | Independent driver suite passed 2,375 tests with 2 skips; frozen evidence separately shows 24 root tests passing, including real Copier render/update cases; review-suite.log:1797, gate-logs/T3-suite.log:38, gate-logs/T3-suite.log:54. |
| T4 Contribution | N/A | Contribution artifacts are intentionally drafted after Check; their substantive audit remains mandatory at publish; gate-logs/T4-contribution.log:10. |
| T5 Judgment | NEEDS-HUMAN | Confirm merged and closed/rejected prior art for every affected path — the brief reports integrate.py/publish.py history, but not flow.py, docs, or tests, and this target contains only a synthetic base commit with no remote; brief.md:31, review-prior-art.log:1. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether stopping and requiring branch restoration or a fresh run is operationally suitable for live stacks after the C5 defect is fixed — the selected behavior also rejects contributor rebases; brief.md:26, target/docs/07-crosscutting.md:668. |

The C5 finding is independently reproduced with real Git. Run `PYTHONDONTWRITEBYTECODE=1 python3 review-race-repro.py` from this report's directory. The script uses the target's existing fixture and production fold; its only interception schedules a real force-push before the second real fetch. It does not fake ancestry, merging, or push outcomes.

1. Publish A for `main` and C for `zbase` in the same checkout; fold both with the same `carried` mapping.
2. In the next fold, let the main group's preflight fetch and ancestry check succeed.
3. Before the zbase group's fetch, force-push `fix/A` to a non-descendant commit adding `a2.txt`.
4. That fetch refreshes the shared checkout's `origin/fix/A`. The merge resolves this mutable ref again, without comparing the new head to the recorded head.
5. Observed: fold returns successfully, origin's main integration line moves, both A histories are ancestors of it, and `carried['issue_A']` is replaced by the rewritten head (`review-multibase.log:2`).

The `fetched` set is keyed by `(repo, base)`, although remote-tracking refs are shared across bases in that checkout (`target/template/src/pdca_harness/integrate.py:391`). Consequently, suppressing the group's own later fetch does not preserve its checked snapshot. Keep the actual merge tied to an ancestry-validated immutable head, with every relevant check completed before any target merges or pushes; add this real-Git multi-base interleaving as a regression. A check introduced only inside each merge would not preserve the promised all-target preflight boundary.

The capability-probe smell test does not independently trigger: the added signature probe is confined to the red-leg test adapter (`target/template/tests/test_integrate_stack_bases.py:371`), and the production ancestry check enforces the explicitly chosen invariant rather than masking a load-time capability side effect. The existing production-path scanner was vacuous because no new test file was added (`gate-logs/C5-prod-path.log:10`); direct inspection and the independent runs confirm these tests exercise production.

Evidence limits: the disposable target was readable and the patch was present; its final diff matches `patch.diff` byte-for-byte after stash restoration. Instance-only gate wrappers were adjudicated from their supplied logs and their available underlying checks were rerun. This interpreter cannot import Copier, so the local root-suite attempt reports no Copier evidence (`review-root-suite.log:6`); the frozen log explicitly shows the real render/update cases running successfully, so this local host limitation is not a patch failure or an undischarged patch dependency. The target's integration template enumerates no additional human-only items beyond a TODO (`target/template/docs/INTEGRATION.md.jinja:80`). No source fix was made. This review is advisory.

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — issue 633 (fold refuses a rewritten carried branch)

No correctness bugs found that block the fix. The check runs before any merge or push. It decides by ancestry and stops if git fails (`_in_line`). It skips gone branches, and it only fires for in-run folds that pass `carried`. C4 shows 3 tests red without the fix and green with it (`gate-logs/C4-verify.log`). Two small notes below; neither needs a human.

- NEEDS-HUMAN [impl] — The up-front fetch now runs **outside** the integration lock. `template/src/pdca_harness/integrate.py:392-399` fetches every target that has a carried head before `integ_lock` is taken at `:439`. Then `_prepare_worktree(..., fetch=False)` at `:447-449` skips the fetch that used to run under the lock. As a result, the `origin/{branch}` read at `:450`, the "moved line" check at `:451-460`, and the merged refs all come from a snapshot taken before the lock. Before the patch, every fold fetched while holding the lock. This only matters for "continue" folds, since a run's first fold has no carried heads, so the forced push at `:482` never uses the early snapshot. It still fails closed: if another holder moves the line, our unforced push is rejected at `:483`. But the operator then sees the generic "could not push" error instead of the #591 "origin's line moved" message. Two `git fetch` runs in the same checkout can also now overlap and fail on ref locks. A simple fix: keep the early check, drop the `fetched` skip (let `_prepare_worktree` fetch again under the lock), and call `_refuse_rewritten` again for that group's carried bundles after that fetch. That restores the old locking guarantee, and the merge then uses the same snapshot the check passed. The cost is one extra fetch per fold that has carried heads.
- `template/tests/test_integrate_stack_bases.py:470-489` (the flow plumbing test): the Z1–Z3 bundles have no `patch.diff`, so `fold` returns at `integrate.py:360-361` before it records anything. The test proves the flow passes the same dict object to every in-run fold (`flow.py:2103`, `:2307`). The comment says "a later fold sees what an earlier one recorded", but that is only shown through object identity. Recording itself is covered by `test_a_fast_forward_of_a_carried_branch_is_still_merged` (`:439-440`), so nothing is missing. This is a wording note on the comment only.

Reuse and simplification: no duplicated logic found. `_refuse_rewritten` (`integrate.py:498-518`) reuses `_rev` and `_in_line`. The `carried` out-mapping copies the existing `skipped` pattern. The new `fetch=` keyword on `_prepare_worktree` (`:680-686`) is the smallest change that avoids a second fetch, though see the first bullet for a reason to accept that second fetch.
<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] C5 Causal adequacy — Close the checked-head/merged-head race for multiple bases sharing one checkout — a later fetch can replace an already-checked ref and silently push both old and rewritten commits; target/template/src/pdca_harness/integrate.py:398, target/template/src/pdca_harness/integrate.py:529, review-multibase.log:1.
- [ ] T5 Judgment — Confirm merged and closed/rejected prior art for every affected path — the brief reports integrate.py/publish.py history, but not flow.py, docs, or tests, and this target contains only a synthetic base commit with no remote; brief.md:31, review-prior-art.log:1.
- [ ] Validation — fitness-to-purpose — Decide whether stopping and requiring branch restoration or a fresh run is operationally suitable for live stacks after the C5 defect is fixed — the selected behavior also rejects contributor rebases; brief.md:26, target/docs/07-crosscutting.md:668.
- [ ] The up-front fetch now runs **outside** the integration lock. `template/src/pdca_harness/integrate.py:392-399` fetches every target that has a carried head before `integ_lock` is taken at `:439`. Then `_prepare_worktree(..., fetch=False)` at `:447-449` skips the fetch that used to run under the lock. As a result, the `origin/{branch}` read at `:450`, the "moved line" check at `:451-460`, and the merged refs all come from a snapshot taken before the lock. Before the patch, every fold fetched while holding the lock. This only matters for "continue" folds, since a run's first fold has no carried heads, so the forced push at `:482` never uses the early snapshot. It still fails closed: if another holder moves the line, our unforced push is rejected at `:483`. But the operator then sees the generic "could not push" error instead of the #591 "origin's line moved" message. Two `git fetch` runs in the same checkout can also now overlap and fail on ref locks. A simple fix: keep the early check, drop the `fetched` skip (let `_prepare_worktree` fetch again under the lock), and call `_refuse_rewritten` again for that group's carried bundles after that fetch. That restores the old locking guarantee, and the merge then uses the same snapshot the check passed. The cost is one extra fetch per fold that has carried heads.
- [ ] **The brief never says where "the commit the line took from it" comes from, and nothing records it today.** The Scope and Invariant depend on comparing a branch's current tip with "the commit the line took from it". The issue goes further: "its **recorded** head is no longer an ancestor of the branch". No per-bundle head is recorded anywhere:
- [ ] **It is unspecified whether the new refusal goes inside `_merge_published`, and that decides whether the #646 pre-wave carry stops or quietly skips.**
- [ ] **The brief does not mention a behaviour change that hits legitimate use: a rebase-style "Update branch" on a carried PR will now stop the run.**
- [ ] **The ordering is declared without a resolvable dependency.**
- [ ] **Criterion (1)'s message check is loose.** "says its branch was rewritten since this run folded it, with what to do" can only be verified by a reviewer, not by the test. Assert concrete substrings: `issue_A`, `fix/A`, and the word "rewritten". Also assert that the text does *not* contain "cross-wave overlap" in (1b). The test then fails on a regression in wording, not only on a missing raise.

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
- Iteration delta (if iterating): Auto-iterate (round 1): rebuilding for the implementation-level findings — C5 Causal adequacy — Close the checked-head/merged-head race for multiple bases sharing one checkout — a later fetch can replace an already-checked ref and silently push both old and rewritten commits; target/template/src/pdca_harness/integrate.py:398, target/template/src/pdca_harness/integrate.py:529, review-multibase.log:1.; The up-front fetch now runs **outside** the integration lock. `template/src/pdca_harness/integrate.py:392-399` fetches every target that has a carried head before `integ_lock` is taken at `:439`. Then `_prepare_worktree(..., fetch=False)` at `:447-449` skips the fetch that used to run under the lock. As a result, the `origin/{branch}` read at `:450`, the "moved line" check at `:451-460`, and the merged refs all come from a snapshot taken before the lock. Before the patch, every fold fetched while holding the lock. This only matters for "continue" folds, since a run's first fold has no carried heads, so the forced push at `:482` never uses the early snapshot. It still fails closed: if another holder moves the line, our unforced push is rejected at `:483`. But the operator then sees the generic "could not push" error instead of the #591 "origin's line moved" message. Two `git fetch` runs in the same checkout can also now overlap and fail on ref locks. A simple fix: keep the early check, drop the `fetched` skip (let `_prepare_worktree` fetch again under the lock), and call `_refuse_rewritten` again for that group's carried bundles after that fetch. That restores the old locking guarantee, and the merge then uses the same snapshot the check passed. The cost is one extra fetch per fold that has carried heads.. Deferred, not addressed here: 6 finding(s) that need human judgment, held in deferred-findings.json for the human at handover — not build work
- By / date: auto-iterate / 2026-10-10

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 5 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
