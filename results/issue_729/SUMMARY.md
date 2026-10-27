# Result — issue 729 / flow-merged-prereq-judged-by-merged-into

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: 
- Success criterion: (1) **#655 judged on the base the bundle gets.** Real-git test on `StackFoldGit` driving `flow._drive_and_act`: `W` and `D` (`Depends on: W`) as in `test_flow_merged_prereq_on_line.py`; out-of-batch `P`'s PR merges into `main` after the first fold; `D` is not held; it is COMPLETE, built on its own base, and that base contains `P`'s merge commit. Both edge types: `Depends on (merged): P`, and a plain `Depends on: P` with `P` not in the batch (#647).
  (2) A prerequisite NOT merged into `main` still holds its dependent (the #647 rule, `merged.merged_into`).
  (3) **The line check stays for line-based bundles.** A `D` that still gets the line base (#727's seam fallback, e.g. with an `Onto branch` or legacy `Stacks on` prerequisite) whose out-of-batch `P` merges after the first fold is still held with today's #655 message. `_runnable`'s docstring (`flow.py:735-744`), `merged.py`'s module docstring (`:24-26`) and `_pr_view`'s docstring (`:188`) say the check applies only to a bundle built on the line. The `lines=` plumbing (`flow.py:688`, `:2503-2505`) stays, used only for those bundles; no unused parameter or bookkeeping is left behind.
  (4) **`template/tests/test_flow_merged_prereq_on_line.py` becomes the line-based suite** (anchors on `fcae4aa`; #727 will have restated its `_built_on_line` helper). `:202`, `:212`, `:241`, `:249` and `:293` keep their held assertions, but their `D` is re-pointed to a line-based `D` as in (3), since a `D` on its own base is no longer held; the module docstring (`:1-12`) is rewritten to say the rule covers only bundles built on the line. `:222`, `:230`, `:257` and `:269` stay as #727/#728 left them; `:269` (a carried `P`) is #728's to restate, not this bundle's. The own-base cases live only in the new test file (one home each). `build-notes.md` names every changed test with before and after.
  (5) Existing suites stay green; assertions restated only in terms of content, never weaker.
- Repo + branch target: eduralph/pdca-harness @ main (PRs target `main`). Base: the accepted result of #727 on the run's line `pdca-integration/main-r547f8028520f` (from `fcae4aa`), as the driver exports it (`$PDCA_VERIFY_BASE`). `Conflicts with: 728` puts #728 in a different wave; if it lands first, its result is on this base too. The criteria hold either way: none of them depends on how carried bundles are based. **Precondition from #727, checked by Do on its base before building:** each bundle's own base is built when its wave starts, from the base fetched then (`integrate.build_bundle_base`, which "always starts fresh from the base as fetched", `integrate.py:719-729` on `fcae4aa`), or is the real base for an empty closure. If #727's result instead snapshots the base once per run, stop and report it: then (1) is false and the line check must stay for all bundles.
- Scope (one logical fix) / out of scope: 

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: Fixed
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

Review #729: judge merged out-of-batch prerequisites against each dependent’s actual build base, retaining integration-line holds for dependents built on that line.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The invariant, both dependency types, unmerged guard, and line fallback are falsifiable; the fresh-per-wave base precondition is present and exercised (brief.md:4; template/src/pdca_harness/integrate.py:748; template/tests/test_flow_merged_prereq_dependency_base.py:101). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only production changes leaves three intended assertion failures for late merges, while the nine existing cases and two unmerged guards pass (review-red.log:1; template/tests/test_flow_merged_prereq_dependency_base.py:93). |
| C3 Change | PASS | Readiness and construction consume the same closure-derived plan, preserving seam semantics; this is one logical fix, and the prior iteration’s misleading helper call is absent (template/src/pdca_harness/flow.py:986; template/src/pdca_harness/flow.py:2695; template/tests/test_flow_merged_prereq_dependency_base.py:90). |
| C4 Verification (red→green) | PASS | Independent production-only stash/pop rerun changes three failures to all 14 focused tests passing; own-base assertions establish both P’s merge and W’s head are ancestors of D’s recorded base (review-red.log:1; review-green.log:3; template/tests/test_flow_merged_prereq_dependency_base.py:100). |
| C5 Causal adequacy | PASS | The stale-line decision is removed precisely where fresh-base construction supplies the prerequisite; actual git reproduces the failure, and unchanged line/unmerged holds remain covered; no optional-capability probe is introduced (template/src/pdca_harness/flow.py:795; template/src/pdca_harness/flow.py:1026; template/tests/test_flow_merged_prereq_dependency_base.py:131). |
| T1 Structure | PASS | Closure membership and seam selection remain single-sourced; extracting planning permits the readiness decision without duplicating base-selection policy or leaving unused line plumbing (template/src/pdca_harness/flow.py:970; template/src/pdca_harness/flow.py:2711; template/src/pdca_harness/flow.py:2761). |
| T2 Shape | PASS | Independent docs lint, 22-page render and internal-link audit pass, as does git diff --check; frozen host-parity output also records lint/render success (gate-logs/T2-docs.log:11; gate-logs/host-ci-docs.log:11). |
| T3 Runtime | PASS | Independent driver suite passes 2,594 tests with two skips; frozen root-suite evidence shows 24 passing tests, including render/update compatibility; local root rerun exits 77 because Copier is not importable (review-suite.log:1817; gate-logs/T3-suite.log:39; gate-logs/T3-suite.log:54; review-root-suite.log:6). |
| T4 Contribution | N/A | Contribution artifacts are absent by design during Check; the substantive contribution audit must rerun at publish, exactly as the deferred gate states (gate-logs/T4-contribution.log:10). |
| T5 Judgment | NEEDS-HUMAN | Confirm affected-path prior art across merged history and closed/rejected work — this checkout has one synthetic commit, no remotes, and no closed/rejected search evidence, so the brief’s issue references cannot discharge that check (review-prior-art.log:1; review-prior-art.log:4; brief.md:19). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Accept the retained line-only hold policy and decide whether offline host evidence suffices — live gh/GitHub was not exercised; PR-state evidence uses a stub while git history/base construction is real, so live host integration remains unvalidated (brief.md:24; template/tests/test_flow_merged_prereq_on_line.py:111; template/tests/test_flow_merged_prereq_on_line.py:162). |

All source citations above are relative to `$PDCA_TARGET` (`target/` here), inspected with the patch applied. Its supplied base contains dependency-scoped base construction; no stale-target caveat was needed. After the independent red leg, stash pop restored production changes; `git apply --reverse --check ../patch.diff` confirmed the final target still matches the supplied patch. No implementation changes were made.

Independent execution used Python 3.14.4 and git 2.53.0. The focused command was `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest tests.test_flow_merged_prereq_on_line tests.test_flow_merged_prereq_dependency_base` from `target/template`; the full driver command was `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests`. Reviewer evidence is in `review-red.log`, `review-green.log`, and `review-suite.log`.

The instance-root wrappers are not supplied here. I read every configured gate’s frozen evidence instead of treating missing wrappers as defects. The production-path scanner’s limited claim (an added test imports production) is supported by `gate-logs/C5-prod-path.log:10`; independently, the new test imports production at `template/tests/test_flow_merged_prereq_dependency_base.py:30`, invokes production flow through `template/tests/test_flow_merged_prereq_on_line.py:171`, and retains the real fold at `template/tests/test_flow_merged_prereq_on_line.py:154`. The local Copier limitation is a reviewer-host caveat: the frozen gate actually exercised those root cases successfully. No gate log is missing, and no patch defect was identified.

The prior iteration’s implementation concern is resolved: the new own-base helper keeps explicit branch/tip/ancestor/COMPLETE assertions without calling the ambiguously named `_built_on_line` helper (template/tests/test_flow_merged_prereq_dependency_base.py:90). No builder-fixable C5/T5 concern remains. The human decisions above remain advisory and do not gate acceptance.

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — issue #729 (flow-merged-prereq-judged-by-merged-into)

**Verdict: no correctness bugs found, and nothing a human needs to decide.** The three notes below are small cleanups. None of them gates anything.

What I checked:

- **The production change is right.** `_runnable` now reads the line only when the bundle is in `on_line` (`template/src/pdca_harness/flow.py:795-796`). `on_line` is built from the same `_base_plans` answer that `_bundle_bases` later uses to point the bundle (`flow.py:2695-2698`, `:2761`). So the predicate is called, not copied, as the brief asks. I moved the plan computation from inside `_bundle_bases` to the top of the wave loop and checked that nothing it reads changes in between: `accepted`, `finished`, `bundles` and `line_cut` are not touched by `_runnable`, the budget check or the preflight. `_closure_members` (`flow.py:922-967`), `_fold_candidates` (`integrate.py:240`) and `waves.conflict_map` only read state, so running them on the whole wave (not only `runnable`) changes no results.
- **The iteration-1 finding is fixed.** The own-base test no longer calls `_built_on_line()`. It checks the base branch, the tip, P's merge commit and W's tip directly (`template/tests/test_flow_merged_prereq_dependency_base.py:90-102`).
- **The old suite is re-pointed as criterion (4) asks.** The held cases now pass `on_line=True` (`Stacks on: W`, a seam), via `template/tests/test_flow_merged_prereq_on_line.py:56` and `:177-180`. Their held assertions are unchanged.
- **Gates.** C4 is red before the fix (D held with the #655 message) and green after (`gate-logs/C4-verify.log`). T3 ran 2594 tests, all OK.

Minor notes (not NEEDS-HUMAN):

- `template/src/pdca_harness/flow.py:2697-2698`: in the run loop, the `if own_bases else None` branch can never change a result. `own_bases` is the same value as `hold_unmerged` (`flow.py:2680`), and when `hold_unmerged` is false `_runnable` never reaches the merged-prerequisite line check. The `None` default ("every bundle is on the line") only matters for direct callers of `_runnable` in tests (`test_flow_slice.py:1984`, `test_flow_out_of_batch_prereq_hold.py:156`), which pass no `lines`. This is harmless and the docstring explains it, so I'd leave it.
- `template/src/pdca_harness/flow.py:2695`: `_base_plans` now runs for every wave in stack mode, before `_runnable`. It also runs for waves where nothing turns out runnable, and for bundles that end up held. Before, it ran only for runnable bundles. The cost is brief reads plus one `conflict_map` per wave, so it is not worth changing.
- `template/tests/test_flow_merged_prereq_dependency_base.py:125-126`: in the real-base case, `read_stack_base(d) == ""` repeats the `seen == ("", "")` check on line 124. `_ancestor(merge_oid["P"], "main")` checks the test setup, not D. Neither weakens the test, since the real base is `main` and line 124 already shows D had no stack base. You could drop both lines or merge them into one.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — Confirm affected-path prior art across merged history and closed/rejected work — this checkout has one synthetic commit, no remotes, and no closed/rejected search evidence, so the brief’s issue references cannot discharge that check (review-prior-art.log:1; review-prior-art.log:4; brief.md:19).
- [x] Validation — fitness-to-purpose — Accept the retained line-only hold policy and decide whether offline host evidence suffices — live gh/GitHub was not exercised; PR-state evidence uses a stub while git history/base construction is real, so live host integration remains unvalidated (brief.md:24; template/tests/test_flow_merged_prereq_on_line.py:111; template/tests/test_flow_merged_prereq_on_line.py:162).
- [x] **Criterion (4) is wrong about which tests stay green.** It flips only `:202`, `:212`, `:241` and `:249` and says "The rest stay green". But in `template/tests/test_flow_merged_prereq_on_line.py`, `test_the_way_out_is_to_delete_the_line_then_re_run` (`:293`) calls `self._held("does not have that merge")` at `:302` and `self._held(..., "may continue it")` at `:306`. Both assert that D is held by the check this brief deletes, so the test goes red. Also, `_built_on_line` (`:191-198`) asserts `base == self.line` (`:195`). Three tests use it: `:222`, `:230` and `:269`. The brief's premise is that "after #727 a bundle is no longer cut from the line", so all three should fail too, or #727 already rewrote them and the `fcae4aa` anchors are stale. `:269` also asserts `tip == old` and that `P`'s merge commit is *not* in D's base (`:286`, `:288`), which contradicts criterion (1)'s "its base contains P's merge commit". The criterion needs to list every test whose assertion changes, with a before and after for each. As written, a correct patch would break the brief's own "rest stay green" clause.
- [x] **The root cause rests on #727, which is still PLANNED.** `dependency-state.json` gives `"727": {"exists": true, "state": "PLANNED"}`. The whole defect ("After #727 a bundle is no longer cut from the line; it is built on its own base from the real base, which already holds anything merged into `main`") describes code that does not exist yet. Today D is cut from the line: `flow.py:735-740`, and `flow.py:2503-2505` passes `lines=` "The line each target's bundles are cut from". So the claim cannot be checked against the target. It also hides an assumption: if #727 snapshots the base tip once per run instead of fetching it per bundle, a merge that lands after the first fold is still missing from D's base. In that case `_line_lacks_merge` is still guarding something real, and deleting it reopens #655. The brief should state the #727 property it relies on (when D's base is fetched, and from what) as a checkable precondition. As it stands, "Falsifiability: With #727 alone, `_line_lacks_merge` holds `D`" cannot be checked at plan time.
- [x] **The base and dependency declarations don't fully resolve.** The target says "Base: the accepted result of #727 (and #728, whichever wave folded first)", but the brief declares `Conflicts with: 728` and does not declare a dependency on it. Whether #728's changes are in the base therefore depends on scheduling. The Ordering note says "needs #723 through #727", but only `727` is declared, and `dependency-state.json` lists only 727. Unless #723–#726 reach this bundle only through #727, they are phantom prerequisites. Either declare them, or drop the claim and drop the #728 clause from the base.
- [x] **Leftover dead code is left open, and its removal is a second change the scope doesn't name.** Deleting `_line_lacks_merge` leaves several pieces with nothing to do: the `lines` parameter of `_runnable` (`flow.py:688`) and its only use at `:787`; the `off_line` / `lacks` / `views` bookkeeping (`:747-748`, `:767`, `:790-796`); the held-message block at `:814-825`; the `_runnable` docstring paragraph at `:735-744`, which names `_line_lacks_merge`; and the caller's `lines=` argument at `:2503-2505`. Criterion (3) checks only that the names are gone and that the two docstrings in `merged.py` are fixed. A patch could leave `lines` plumbed through with nothing using it, or remove it at the call site, and neither outcome is in Scope. Add an explicit criterion for these leftovers. Separately, the `_pr_view` docstring citation is off: the mention of `merge_and_head` is at `merged.py:188`, not `:190`, which is the `subprocess.run` line.
- [x] **The new test file duplicates the flipped tests.** Criterion (1) adds `test_flow_merged_prereq_dependency_base.py` (new), with the same scenario on both edge types: P merges after the first fold, under `Depends on (merged)` and plain `Depends on`. Criterion (4) flips `:202` and `:212` of the existing file to exactly that scenario. That is two tests for one behavior, and the existing file's module docstring (`:1-12`, "counts only when the run's line has its work") would then describe a rule that no longer exists. Pick one home, or require the old file's docstring to be rewritten.
- [x] **There is no tracker record to check the brief against.** This sandbox has no `notes.json` and no `sources/`; only `brief.md` and `dependency-state.json` are present. I could not test the problem statement against the thread, or look for a maintainer constraint or a failed earlier attempt, including the cited "parent #724 brief plan-review note (f)". The human should confirm the #655 and #724 thread content before signing off.
- [x] T5 Judgment — Complete the affected-path comparison against merged history and closed/rejected work before concluding no equivalent or rejected solution exists — the path-based investigation found only one synthetic base commit, no remotes, and no closed-review evidence; named issue references alone cannot settle this (review-prior-art.log:1; review-prior-art.log:9; brief.md:19).

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
- Plan advisory: 6 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
