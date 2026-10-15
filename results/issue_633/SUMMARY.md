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

Review issue #633: stop an in-run stack fold when a previously carried PR branch is rewritten, while preserving fast-forward updates and existing carry/deleted-branch behavior.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief defines observable refusal, unchanged-line, fast-forward, carry and deleted-branch outcomes, and explicitly chooses fold-time refusal with no external dependency beyond Python/git; brief.md:12, brief.md:26, brief.md:28. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only the production fix produced four behavioral failures, including a silently accepted rewrite and a conflicting rewrite misreported as overlap; review-red.log:25, review-red.log:34, target/template/tests/test_integrate_stack_bases.py:1187. |
| C3 Change | PASS | The four changed files implement the agreed fold contract, flow plumbing, documentation and regression coverage without changing publishing or pre-wave carry policy; target/template/src/pdca_harness/flow.py:805, target/template/src/pdca_harness/integrate.py:367, target/docs/07-crosscutting.md:666. |
| C4 Verification (red→green) | PASS | Restoring the production fix made all 62 regression tests pass after the four expected red failures; the restored target diff exactly matches patch.diff, and the independent result agrees with the frozen gate; review-red.log:61, review-green.log:25, gate-logs/C4-verify.log:10. |
| C5 Causal adequacy | PASS | Ancestry refusal precedes merges and uses the same immutable SHA later merged, preventing a subsequent fetch from substituting a rewritten tip; real-git rewrite/race and flow-stop cases pass, and ancestry errors remain fail-closed; target/template/src/pdca_harness/integrate.py:414, target/template/src/pdca_harness/integrate.py:492, target/template/src/pdca_harness/integrate.py:550, target/template/src/pdca_harness/integrate.py:807. |
| T1 Structure | PASS | One run-owned mapping reaches each in-run fold, advances only after a successful push, and leaves the existing lock and pre-wave carry boundaries intact; target/template/src/pdca_harness/flow.py:2148, target/template/src/pdca_harness/flow.py:2352, target/template/src/pdca_harness/integrate.py:451, target/template/src/pdca_harness/integrate.py:520. |
| T2 Shape | PASS | Independent docs lint, 22-page rendering/internal-link audit and diff whitespace checks passed; frozen docs and host-CI-parity logs agree; target/docs/07-crosscutting.md:666, review-static.log:10, gate-logs/T2-docs.log:10, gate-logs/host-ci-docs.log:10. |
| T3 Runtime | PASS | Independently ran all 2,431 driver tests successfully with two skips; the frozen root-suite log shows 24 passing tests including actual render/update cases, which this reviewer cannot rerun because copier is not importable locally; review-suite.log:1814, gate-logs/T3-suite.log:38, gate-logs/T3-suite.log:54. |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the substantive audit is deferred to the mandatory publish-time rerun, not an unresolved verification failure; gate-logs/T4-contribution.log:10. |
| T5 Judgment | NEEDS-HUMAN | Complete/confirm merged-history and closed/rejected-work review by all four affected paths — the brief documents integrate.py/publish.py only, while this disposable copy has one synthetic commit and no remote, leaving prior decisions for flow.py, the regression file and docs unconfirmed; brief.md:31, review-static.log:1. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Confirm that the tested stop-and-reissue behavior meets operators’ recovery needs — a mid-run rebase or re-publish deliberately stops later waves, and passing mechanics alone cannot establish operational fitness; target/docs/07-crosscutting.md:668, target/template/tests/test_integrate_stack_bases.py:1343. |

Independent verification used the supplied disposable target, whose patched diff exactly matched patch.diff. I stashed only template/src/pdca_harness/flow.py and template/src/pdca_harness/integrate.py, retained the regression tests, ran `PYTHONPATH=src python3 -m unittest discover -s tests -p test_integrate_stack_bases.py` from target/template, restored the stash, and repeated that command. The four red failures were assertions about behavior, not missing imports or parameters. The patch was restored unchanged. Test temporary directories were confined to this review sandbox through TMPDIR.

The broader rerun was `PYTHONPATH=src python3 -m unittest discover -s tests` from target/template. It passed 2,431 tests with two skips. The instance-scoped gate wrappers are not part of this target; their frozen logs were inspected, and available underlying commands were run directly. Docs lint and site rendering with `--check` passed. The reference production-import scanner also ran, but its new-file-only heuristic has nothing substantive to assert for this edited test file (gate-logs/C5-prod-path.log:10); the independent red→green tests provide the production-path evidence instead. The root render/update suite is supported by its frozen execution log, not claimed as independently rerun. Its dependency was exercised there, so the local absence of copier does not establish an unmet patch dependency.

The previous checked-head/merged-head race is addressed by retaining the checked SHA (target/template/src/pdca_harness/integrate.py:492). The under-lock fetch is restored through _prepare_worktree (target/template/src/pdca_harness/integrate.py:459, target/template/src/pdca_harness/integrate.py:883); the moved-line regression at target/template/tests/test_integrate_stack_bases.py:1315 passes. A rewrite arriving after the checked snapshot is excluded from that fold and detected by the next fold, as exercised at target/template/tests/test_integrate_stack_bases.py:1275. No production capability probe or load-time fallback was added, so the C5 symptom-guard smell-test does not trigger.

Prior-art investigation returned only synthetic base commit 1df9c0c and no configured remote (review-static.log:1). The outstanding path coverage is template/src/pdca_harness/flow.py, template/tests/test_integrate_stack_bases.py and docs/07-crosscutting.md; the brief supplies the integrate.py history and closed-PR account. This limitation is not a stale-target defect or a C4 failure. The supplied INTEGRATION template enumerates no additional concrete human-only items (target/template/docs/INTEGRATION.md.jinja:80).

No builder-fixable defect was found in this round. The two NEEDS-HUMAN rows are advisory decisions, and T4 remains deferred to publish.
<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — issue 633 (fold refuses a rewritten carried branch)

No correctness bugs found in the patch. The notes below are small cleanups and one wording nit. None of them blocks.

What I checked and found sound:
- The check runs before any target takes its lock or merges (`template/src/pdca_harness/integrate.py:414`), and it is skipped when `carried` is empty or this is a dry run. So the run's first fold and the #646 carry (`template/src/pdca_harness/flow.py:981`, which passes no mapping) behave as before.
- The commit that gets merged is the one that was checked (`integrate.py:491-493`). The fetch under the lock still runs (`_prepare_worktree`, `integrate.py:449`), so the earlier round's finding is fixed. The "origin's line moved" (#591) refusal reads a fresh fetch again, and a test pins this.
- The record is updated only after that target's push succeeds (`integrate.py:520-521`). Gone branches (tip `None`) keep their old record and fall through to `_gone_branch` unchanged (`integrate.py:549-550`, `:577-579`).
- The ancestry test keeps `_in_line`'s fail-closed reading: a git error raises, it is never read as "rewritten" (`integrate.py:550-551`, `:807-818`).
- The flow creates one mapping per run and passes it only to the in-run fold (`flow.py:2148`, `:2349-2352`).
- C4 log: the new tests fail without the fix (4 failures, including the 1b "cross-wave overlap" message) and pass with it.

Findings:

- `template/src/pdca_harness/integrate.py:540-545` — `_carried_tips` calls `_fetch` once per target group. When several bases share one checkout (the multi-base case the new race test sets up), it fetches the same checkout once per group, and each group then fetches again under its lock (`:449`). That makes 2N full fetches of origin for N targets in one checkout. Fetching once per distinct checkout here would give the same result with fewer network round trips. This is efficiency only, so no tag needed.
- `template/src/pdca_harness/integrate.py:543` — that up-front fetch runs outside any integration lock, in a checkout another flow's fold may be fetching into at the same time. Two git fetches in one repo can fail on ref locks. `_fetch` would then raise and stop the run with a misleading "fetch failed". Folds of different bases in one checkout could already overlap like this before the patch, so the risk is not new. But the patch adds one more unlocked fetch per fold that has carried bundles. Low likelihood. Mentioned so the human knows it exists; no change requested.
- `template/src/pdca_harness/integrate.py:560-561` — the refusal says "Restore {ref} to …", and `ref` is the remote-tracking name (`origin/fix/A`). The operator restores the branch `fix/A` on the remote, not `origin/fix/A`. Saying "restore branch fix/A on origin" would be clearer. This is a wording nit; the test only checks for "Restore" and "fix/A", so it would still pass.
- `template/tests/test_integrate_stack_bases.py:1279-1299` (`test_a_rewrite_between_two_targets_fetches_never_reaches_the_line`) — the rewrite fires before the 2nd `fetch`. With both groups carried, that 2nd fetch is `_carried_tips`'s own fetch for `zbase` (`integrate.py:543`), not the lock-time fetch the comment describes. The test still proves the point: fix/A is rewritten after its tip was checked, and the 3rd fetch (under main's lock) makes the stale tip visible before the merge. But the comment "the fetch for zbase also refreshes fix/A" does not match which fetch it is. The test depends on fetch order (`len(fetches) == 2`), so a future change to the fetch count would quietly move the race point. Clarifying the comment or matching on the call site would make it sturdier. Test clarity only; no tag needed.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — Complete/confirm merged-history and closed/rejected-work review by all four affected paths — the brief documents integrate.py/publish.py only, while this disposable copy has one synthetic commit and no remote, leaving prior decisions for flow.py, the regression file and docs unconfirmed; brief.md:31, review-static.log:1.
- [x] Validation — fitness-to-purpose — Confirm that the tested stop-and-reissue behavior meets operators’ recovery needs — a mid-run rebase or re-publish deliberately stops later waves, and passing mechanics alone cannot establish operational fitness; target/docs/07-crosscutting.md:668, target/template/tests/test_integrate_stack_bases.py:1343.
- [x] **The brief never says where "the commit the line took from it" comes from, and nothing records it today.** The Scope and Invariant depend on comparing a branch's current tip with "the commit the line took from it". The issue goes further: "its **recorded** head is no longer an ancestor of the branch". No per-bundle head is recorded anywhere:
- [x] **It is unspecified whether the new refusal goes inside `_merge_published`, and that decides whether the #646 pre-wave carry stops or quietly skips.**
- [x] **The brief does not mention a behaviour change that hits legitimate use: a rebase-style "Update branch" on a carried PR will now stop the run.**
- [x] **The ordering is declared without a resolvable dependency.**
- [x] **Criterion (1)'s message check is loose.** "says its branch was rewritten since this run folded it, with what to do" can only be verified by a reviewer, not by the test. Assert concrete substrings: `issue_A`, `fix/A`, and the word "rewritten". Also assert that the text does *not* contain "cross-wave overlap" in (1b). The test then fails on a regression in wording, not only on a missing raise.
- [x] T5 Judgment — Confirm merged and closed/rejected prior art for every affected path — the brief reports integrate.py/publish.py history, but not flow.py, docs, or tests, and this target contains only a synthetic base commit with no remote; brief.md:31, review-prior-art.log:1.

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
- By / date: Eduard Ralph / 2026-10-14

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 5 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
