# Result — issue 629 / hold-conflicts-with-partner-of-unpushed-bundle

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: `waves.compute_waves` turns each `Conflicts with` pair into an ordering edge (the name-lower id builds first, `template/src/pdca_harness/waves.py:200-212`), so the second bundle is built in a later wave, on a line that is meant to hold the first. Since #593, an accepted bundle whose publish pushed no branch this run is left out of every fold and put in `held_unpushed` (`template/src/pdca_harness/flow.py:2285-2291`). `_runnable` then holds only bundles whose DECLARED prerequisites name it: it reads `waves.declared_deps` (`Depends on` / `Depends on (merged)` / `Stacks on`, `waves.py:39-48`; `flow.py:719`, `:751-754`) and never the conflict edge. Reproduced through `flow.flow_ids` by the #593 round-2 adversary review: wave 0 = {CA}, whose publish fails; wave 1 = {CJ}, `Conflicts with: CA`. CA is left out of the fold and CJ is NOT held: it is built and published on a base without CA, though the two edit the same resource. When CA is later published by hand, the two PRs collide on the target. Before #593 the fold carried CA's patch, so CJ was built on it.
- Success criterion: With the patch, through `flow.flow_ids` in stack mode with a non-stub publisher and publishing on (the offline harness of `template/tests/test_flow_out_of_batch_prereq_hold.py`: leaves stubbed, `gh` stubbed). Bundles: CA `701` and CJ `702`, each with a `Repo + branch target`, CJ's brief `- **Conflicts with:** 701`; `704` with no target and no edges; U `703` with no target and `- **Depends on:** 704`; and `705` with no target and `- **Depends on:** 702`. Waves: {701, 704}, then {702, 703}, then {705}. The test's drive stub accepts each bundle it is given (writes a non-empty `patch.diff`, records `accept` in §9), as the harness's `_drive_wave` does not. CA is accepted in wave 0, but its publish pushes no branch (`flow._publish_bundle` returns False). Then: (a) CJ is never built and stays PLANNED; (b) ONE stderr line contains `issue_702`, `issue_701`, `Conflicts with` and `pushed no branch` (a new line for this hold, not the "prerequisite(s) not ready" line at `flow.py:762-764`, which would wrongly call CA a prerequisite); (c) U `703`, in the SAME later wave as CJ, is built and COMPLETE, so the run goes on past the hold; (d) `705` (`Depends on: 702`) is not built (it cascades through the existing not-COMPLETE check, `flow.py:731-733`); (e) the announcement at `flow.py:2289-2291` now says the bundles that depend on CA or are its `Conflicts with` partners are held. Unchanged: when CA's publish pushes its branch, CJ is built in wave 1 as today. Pre-fix CJ is built in wave 1. That is the RED.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: Hold every bundle whose `Conflicts with` edge (either direction) ties it to an accepted bundle the fold left out because it pushed no branch this run (`held_unpushed`), with its own one-line report (criterion (b)). Partners of `held_finished` ids are not affected (conflict edges are drive-set only, `waves.conflict_map`, `waves.py:136-153`). The conflict relation must be computed from the run's live `bundles` list at each wave, not once before the loop, because split children adopted mid-run (`flow.py:2124`, `:2222`) add bundles and their `Conflicts with` edges. Update the announcement at `flow.py:2289-2291` (criterion (e)). Document the change where the issue asks, next to the hold in `docs/07-crosscutting.md:672-673`: replace "holds only the bundles that depend on it" with wording that includes `Conflicts with` partners. / out of scope: changing how `compute_waves` orients conflicts; `Conflicts with` partners of finished ids judged by the #646 carry; a partner of a partner (CK `Conflicts with: CJ`, where CJ is held by this fix): CK still builds, on a line without CJ. That is the same as today for a partner of any bundle that is not COMPLETE for another reason (a failed Check), so it is left as a known gap for the human to confirm at sign-off, not widened here; merge mode (no fold, no `held_unpushed`); a dry-run (holds nothing).

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

Review issue #629: hold conflict partners of accepted bundles that pushed no branch, preserve unrelated progress, and give safe rerun advice.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief defines an observable scheduling failure, both conflict directions, continued unrelated progress, dependent cascading, and live split adoption; the resulting contract is explicit at target/docs/07-crosscutting.md:676 (brief.md:15, brief.md:21). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing the tracked fix while retaining the new test produced three assertion failures because conflict partners were built, including the adopted child; target/template/tests/test_flow_conflict_partner_hold.py:196, review-red.log:1. |
| C3 Change | PASS | The change stays within the requested hold and recovery behavior; the two additional documentation surfaces synchronize the same contract rather than introduce functionality; target/template/src/pdca_harness/flow.py:730, target/template/PCDA/quality-cycle/09-parallel-lanes.md:69, target/template/pdca.toml.jinja:125. |
| C4 Verification (red→green) | PASS | Restoring the patch independently changed three failing cases to four passing tests, covering both declaration directions, same-wave progress, dependent cascading, split adoption, recovery wording, and the pushed-branch control; target/template/tests/test_flow_conflict_partner_hold.py:174, review-green.log:10. |
| C5 Causal adequacy | PASS | The previously omitted scheduling relation now prevents a partner from being admitted without the earlier work, using live bundles after adoption; this is an admission-rule correction, not a capability probe masking a load-time cause; target/template/src/pdca_harness/flow.py:787, target/template/src/pdca_harness/flow.py:2233. |
| T1 Structure | PASS | Reusing the symmetric batch conflict map keeps edge interpretation in its existing owner and preserves callers through optional parameters; target/template/src/pdca_harness/waves.py:136, target/template/src/pdca_harness/flow.py:681. |
| T2 Shape | PASS | Independent docs lint, 22-page site rendering/link audit, and git diff whitespace checks passed; the frozen host-parity log also reports successful lint and link audit; review-docs.log:1, gate-logs/host-ci-docs.log:10. |
| T3 Runtime | PASS | Independent driver discovery passed 2,427 tests with two skips; the frozen root-suite log shows 24 passing tests including render/update cases, although local repetition lacked importable Copier; review-suite.log:1814, gate-logs/T3-suite.log:38, review-root-suite.log:6. |
| T4 Contribution | N/A | Contribution artifacts are intentionally absent at Check; the deferred gate explicitly assigns the substantive contribution audit to publish; gate-logs/T4-contribution.log:10. |
| T5 Judgment | NEEDS-HUMAN | Confirm merged and closed/rejected prior art by every affected path before sign-off — the brief reports checks for flow.py and waves.py, but this one-commit target has no remotes or PR records and cannot independently substantiate them or cover the other changed paths; brief.md:26, review-prior-art.log:1. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether direct-partner protection and merge-before-rerun advice suffice despite excluded finished-id and partner-of-partner cases, and whether offline scheduling evidence is sufficient — real publishing/folding topology is not exercised by the focused fixture; target/template/src/pdca_harness/flow.py:730, target/template/tests/test_flow_conflict_partner_hold.py:148, review-boundary.log:3. |

Source citations prefixed with `target/` refer to the supplied `$PDCA_TARGET`; other citations refer to review inputs or captured evidence in this sandbox. The target was readable, the patch was present, and the original tracked changes were restored after the red leg. No production fix was edited.

Independent verification used `PYTHONPATH=src python3 -m unittest -v tests.test_flow_conflict_partner_hold` from `target/template`, first with tracked changes stashed and then after `git stash pop`. The new untracked test remained present for both legs. The red failures explicitly show `issue_702` and `issue_708` being built; the subsequent missing-checkout message in two red cases is not the failure relied on. The green assertions establish PLANNED holds, continued work on `703`, the hold of dependent `705`, one conflict-specific diagnostic, and advice to wait for merge. The original four tests and all 2,427 driver tests then passed. Temporary test files were confined under this sandbox using `TMPDIR`.

The frozen C4 log independently agrees with the rerun (gate-logs/C4-verify.log:10). The production-path scanner reports only that the new test imports the production package (gate-logs/C5-prod-path.log:10); inspecting and running the test additionally confirms that it invokes production `flow.flow_ids` and production split acceptance. Publishing and `gh` are stubbed; the no-push cases use the real empty fold, while the pushed-branch control stubs the fold. Consequently the evidence establishes scheduler admission behavior, not a real host push, merge, or collision recovery. The brief explicitly declares this offline scope (brief.md:23).

The root-suite rerun exited 77 because this Python cannot import Copier (review-root-suite.log:6). This is a local toolchain caveat, not a patch failure or an unfulfilled gate: the frozen log explicitly shows the render and update cases executing successfully (gate-logs/T3-suite.log:38). Both frozen docs logs contain actual lint and render/link-audit success, reproduced here. No missing instance-root wrapper was treated as a defect.

For the documented boundary, I added `706 Conflicts with: 702` to the existing fixture and ran production flow with `701` unpushed. Observed: `702` and `705` stayed PLANNED, while `706` was built and COMPLETE (review-boundary.log:1). This confirms the partner-of-partner gap the brief deliberately excludes (brief.md:21); it is a scope decision, not a new implementation finding. The revised diagnostic and docs now tell the operator to wait until the earlier PR merges into the base before rerunning (target/template/src/pdca_harness/flow.py:785, target/docs/07-crosscutting.md:683).

The supplied target contains only the unrendered integration template; its project-specific human-only list is TODO (target/template/docs/INTEGRATION.md.jinja:80). No additional instance-specific items can be inferred from that template. No builder-fixable defect was found within the stated scope.

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — issue 629 (hold `Conflicts with` partner of an unpushed bundle)

No correctness bug or reuse problem in this diff needs a human decision. The round-1 finding (advice that led straight back to the bug) is fixed. The held line now says to wait for the merge (`template/src/pdca_harness/flow.py:781-786`), and the test pins the exact advice text (`template/tests/test_flow_conflict_partner_hold.py:43`, `:187-188`). The C4 log shows 3 of 4 cases red without the fix; the 4th is the unchanged-behaviour control, which should pass both ways.

What I checked and found sound:

- The patch reuses `waves.conflict_map` (`template/src/pdca_harness/waves.py:136-153`) instead of re-reading `Conflicts with` from briefs, as the brief asked. It is rebuilt from the live `bundles` each wave (`template/src/pdca_harness/flow.py:2233-2237`). That costs nothing extra when no bundle is unpushed (`None` is passed then), and the split-child test (`template/tests/test_flow_conflict_partner_hold.py:225-245`) covers the live-list requirement.
- The symmetric map makes "either direction" work. A partner sitting in an earlier wave than the unpushed bundle has already been built, so the hold can only hit a bundle the scheduler placed after it. There are no false holds within a run.
- The cascade to `705` falls out of the existing not-COMPLETE check. No new code path was needed.
- `publish._resolve_target` now also runs for a bundle that has partners but no deps (`flow.py:737`). It only does that when there is a partner, so the hot path is unchanged.
- Every bundle in `held_unpushed` has a usable target (`integrate.unpublished` keeps only fold candidates, `template/src/pdca_harness/integrate.py:187-197`). So the advice to "`pdca publish <id>`" is always something the operator can actually do.

Minor notes (no action needed):

- `template/src/pdca_harness/flow.py:782` — the "wait until their PR merges into {base} ({repo})" text uses the HELD bundle's own target. If a `Conflicts with` pair spans two different targets, the unpushed partner's PR goes into a different repo/base than the line names. This is rare (a cross-target conflict edge does not share a line anyway), and the brief does not cover it.
- `template/src/pdca_harness/flow.py:774-786` — a bundle that both `Depends on` and `Conflicts with` the same unpushed bundle gets two stderr lines: the existing "prerequisite(s) not ready" line and the new conflict line. Both are accurate. Folding them into one line would be cosmetic only.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — Confirm merged and closed/rejected prior art by every affected path before sign-off — the brief reports checks for flow.py and waves.py, but this one-commit target has no remotes or PR records and cannot independently substantiate them or cover the other changed paths; brief.md:26, review-prior-art.log:1.
- [x] Validation — fitness-to-purpose — Decide whether direct-partner protection and merge-before-rerun advice suffice despite excluded finished-id and partner-of-partner cases, and whether offline scheduling evidence is sufficient — real publishing/folding topology is not exercised by the focused fixture; target/template/src/pdca_harness/flow.py:730, target/template/tests/test_flow_conflict_partner_hold.py:148, review-boundary.log:3.
- [x] **"U is built" proves nothing; it passes before and after the fix.** U (`703`) has no edges, so `compute_waves` puts it in wave 0 next to CA (`701`). Wave 1 is just {CJ}. U is built before CA's publish is even attempted, so this check cannot show that "the run goes on" after the hold. To test that claim, U would need to sit in a wave after the hold, for example `703` with `Depends on: 704` and an unrelated `704`, or a third wave. Otherwise the brief should drop "U is built" as evidence for the invariant.
- [x] **"CJ's own dependents are not built either" can't be checked with the fixture as given.** The criterion asserts this cascade, but the fixture lists only 701, 702 and 703. Nothing depends on CJ. As written, the reviewer has nothing to look at for this clause. Either add a `704` with `Depends on: 702` (a cascade through the not-COMPLETE check at `flow.py:731-733`) or remove the clause.
- [x] **The required stderr line conflicts with "the existing one-line report".** The criterion asks for ONE line naming CJ, CA *and the reason* ("CA pushed no branch this run, so the line CJ would build on lacks it"). The Scope says "with the existing one-line report", and Citations say to reuse the shape at `flow.py:762-764`. That line is `flow: {d} skipped — prerequisite(s) not ready ({unmet}); not built on a base missing them.` It gives no pushed-no-branch reason, and it calls CA a "prerequisite", which a conflict partner is not. Do will have to choose between reusing the line (and failing the criterion's reason clause) and writing a new one. The brief should say which, so the check can be decided either way.
- [x] **The announcement at `flow.py:2289-2291` becomes wrong, and the brief doesn't touch it.** It prints `"…bundles that depend on it are held this run."` After the fix, conflict partners are held too. The Repro instruction greps for this exact line (`issue_701 pushed no branch this run … held this run`). So the brief relies on the text but never says whether it changes. If it stays, it under-reports. If it changes, that edit is in scope and should be stated.
- [x] **The docs will contradict the code after this patch, by the brief's own choice.** `docs/07-crosscutting.md:672-673` says an unpushed bundle "holds **only** the bundles that depend on it". The brief cites this exact sentence as the source for the invariant, then puts editing it out of scope because of 623 (Scope, "out of scope"). So the merged result says "only dependents" in 07 while 03-plan says partners are held too. Also, the thread's Done-when mentions documenting only in `docs/07-crosscutting.md` "next to the hold". Moving the doc to `docs/03-plan.md:87-91` is a planner choice the human should confirm. A follow-up for 623 or this issue to fix the "only" should be recorded so the contradiction doesn't get dropped.
- [x] **The conflict map must be recomputed at each wave, and the brief doesn't say so.** `_runnable(cfg, wave, batch_names, *, held, requested, hold_unmerged)` (`flow.py:681-684`) gets no conflict map. Citations say to "reuse `waves.conflict_map`", but the only callers are `waves.py:205` (inside `compute_waves`, not returned) and `flow.py:569` (the beat pool). So Do has to add a new parameter or call, and has to choose the bundle set. `bundles` grows when split children are adopted (`flow.py:2124`, `:2222`). A map built once before the loop would miss adopted children's `Conflicts with` edges. The brief should name the set, for example the live `bundles` on each iteration, or explicitly accept the gap for adopted children.
- [x] **A partner of a partner is left unspecified.** After the fix CJ is skipped (PLANNED, not COMPLETE). Say a later-wave CK has `Conflicts with: CJ`. CK is not in `held_unpushed` and not a declared dependent, so it is built on a line without CJ. Then CJ, built later by hand on a line holding CA, collides with CK. That is the same class of collision this issue describes. The criterion covers only dependents of CJ. The brief should either cover the transitive case or list it as out of scope, so the gap is visible at sign-off.
- [x] **Some citations are off on the target checkout.** The orientation code is `waves.py:200-212` (lines 197-198 add declared-dep edges), not `:197-205`. The Invariant's quote "into a dependency edge so the two never share a wave" is at `waves.py:200`, not `:197-200`. `conflict_map` is `waves.py:136-153`, not `:135-151`. These are small, but the brief requires Do to cite `path:line` on the target branch, and they suggest the brief was checked against a slightly different tree than the claimed `b5f5c29`. Re-anchor them.
- [x] T5 Judgment — Confirm prior-art coverage for every affected path, including both documentation files — the brief records source-path history and closed PRs, but this sandbox has only a synthetic base commit and no remote or closed/rejected-work evidence to independently settle that coverage (brief.md:26; target/docs/07-crosscutting.md:672; target/template/PCDA/quality-cycle/09-parallel-lanes.md:69).

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
- Plan advisory: 8 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
