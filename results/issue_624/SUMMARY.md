# Result — issue 624 / hold-cascade-through-finished-dependent

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: As filed (against the #593 branch, before #646 and #647 landed): `_runnable` skips a direct dependent D of a held bundle U but does not add D to `held`. If D was already COMPLETE when the run started, a later E (`Depends on: D`) passes and builds on a line that has neither U nor D. On main the shape has changed. A bundle COMPLETE at run start is never in the drive set (`flow_ids` skips it as terminal, `template/src/pdca_harness/flow.py:2537-2564`, and `flow_batch` never sweeps it, `flow.py:2377-2380`), so D is an out-of-batch prerequisite of E:
  - not one of the requested ids: E is held until D's PR merges into E's base (#647, `flow.py:734-750`, `:755-761`);
  - a requested id: D is a finished named id judged by the #646 pre-wave carry (`flow._carry_finished`, `flow.py:869-956`). There the held U is a finished id judged NOT clean (`flow.py:947-956`), and D, judged clean on its own, is carried with U's commits on its branch. That is exactly #652 ("not clean does not cascade across finished ids").
  The one remaining shape, stated exactly so a re-filer can match it: U is in the run's drive set and not yet accepted or held this run (`held_unpushed`, `flow.py:2285-2291`, or simply not COMPLETE); D (`Depends on: U`) is COMPLETE at run start and is one of the requested ids, so the #646 carry judges it clean on its own and folds D's branch, which holds U's commits, onto the line before wave 0; E (`Depends on: D`) is in the drive set. D can only be COMPLETE ahead of U if it was driven by hand (`pdca run` checks no dependencies) or U was reopened (iterated) after D completed. No other path is known, but none was ruled out by a test. Judged too rare to brief; the human accepts it as a known residual at sign-off.
- Success criterion: At sign-off the human confirms that #652's brief covers this issue. Its clause (2), as checked on 2026-10-10 against the revised `results/issue_652/brief.md`, reads: "(2) **#624.** `U` finished with its PR CLOSED (not clean). `D` finished, PR OPEN, `Depends on: U`, its branch cut from `origin/fix/U`. `E` in the drive set with `Depends on: D`. Batch `["U", "D", "E"]`. `E` is never built, stays PLANNED, and is named on one stderr line with `issue_D`. No commit of `U`'s branch is on the line." Tracker actions: (a) now, a comment on #624 quoting that clause, naming #652 and the residual shape above; (b) #624 is closed only when #652's PR merges with that clause's test green (#652's PR body carries `Fixes #624`), not at this bundle's sign-off. If #652 is descoped, split or discontinued, #624 stays open.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: Record that #624 is fixed by #652's bundle, comment now, and close it as a duplicate when #652's PR merges. / out of scope: any code change in this bundle; the hand-driven residual (D made COMPLETE with `pdca run` ahead of an in-flight U that then fails to push), which can be re-filed if it is ever seen.

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: duplicate
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — N/A — close disposition (no patch to verify)
- C3 Change: none — patch.diff
- C4 Verification (red→green): none — N/A — close disposition (no patch to verify)
- C5 Causal adequacy: none — reviewer + human sign-off

## 4. Conformance (Check — stack)
- T1 Structure: none — N/A — close disposition (no patch to verify)
- T2 Shape: none — N/A — close disposition (no patch to verify)
- T3 Runtime: none — N/A — close disposition (no patch to verify)
- T4 Contribution: none — N/A — close disposition (no patch to verify)
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

# Advisory review — SKIPPED (close disposition)

The reviewer leaf was skipped: this bundle's Plan concluded a close / no-fix disposition (duplicate), so there is no patch to review.

- NEEDS-HUMAN — Confirm the close disposition 'duplicate' (no patch was built). Override to a fix path (iterate-to-Do) if the close is wrong.


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] Confirm the close disposition 'duplicate' (no patch was built). Override to a fix path (iterate-to-Do) if the close is wrong.
- [x] **The success criterion depends on an artifact this bundle cannot see or pin.** Brief:12 says "the human confirms that #652's brief (`results/issue_652/brief.md`) covers this issue: its success criterion clause (2) pins U … → D … → E". That file is not among this bundle's inputs. There is no `dependency-state.json`, and the brief declares no `Depends on` on 652 (Brief:16: "No scheduling edges"). Nothing checks that clause (2) exists in the stated form, or that it will still exist after #652's own plan review and revision. The criterion is "a human reads another brief", and that brief can change under it. Suggested revision: quote clause (2) verbatim in this brief, and record which #652 brief revision was checked. Better still, make the close conditional on #652's regression test going green (the brief already names `template/tests/test_flow_resume_stack_prereqs.py`), not on #652's plan text.
- [x] **Closing #624 now closes the issue's "Done when" on a promise.** The thread's exit condition is concrete: "A flow test pins U (held) → D (COMPLETE before the run) → E: E is skipped and named." On main there is no such test yet. The only `held` cases in `template/tests/test_flow_resume_stack_prereqs.py` are single-hop P→D/A (`:224-270`, `:337`), with no U→D→E chain. Closing as a duplicate before #652 merges means that if #652 is descoped, split or discontinued, #624's gap is lost. Suggested revision: comment "fixed by #652 clause (2)" now, and close only when #652's PR merges (or use "Fixes #624" in #652's PR), not at this bundle's sign-off.
- [x] **The cited invariant source says the opposite of the invariant.** Brief:14 states "held and named (directly or through another finished bundle)" and cites `docs/07-crosscutting.md:686-691` as its source. The doc actually reads "A finished prerequisite that is not clean holds **only the bundles whose plain `Depends on` names it**" (`docs/07-crosscutting.md:689-691`). That is direct dependents only, the non-cascading behaviour #652/#624 report as the bug. The `_runnable` docstring has the same wording: "a bundle whose plain `Depends on` names it is not ready" (`flow.py:711-713`). It then relies on "the skip cascades" (`flow.py:713-714`), and that is exactly the reasoning that fails when D is already COMPLETE. The doc line is a load-bearing statement that #652's fix must change. The close comment should not present it as the source of the invariant. The human should also confirm that #652's scope includes updating `docs/07-crosscutting.md:689-691`, so this close does not leave a doc that contradicts the fix.
- [x] **The thread's U is not #652's U, and the residual is asserted rather than shown.** The thread's U is an *in-batch* bundle held by #593 ("held" = COMPLETE but this run pushed no branch, `flow.py:691-694`; `held_unpushed` at `flow.py:2164`). #652's clause (2), as the brief describes it, pins a *finished, not-clean* U (`held_finished`). Those are two different `held` sources fed into the same `_runnable` call (`flow.py:2164`). The brief argues that the in-batch-U shape needs D to have been driven to COMPLETE by hand (Brief:11). The only evidence given is that `pdca run` checks no dependencies. It does not show that no other path (a state reset or rework of U after D completed, an adoption, or a split child) can leave U in the drive set while D is COMPLETE. The human should accept that residual knowingly. Alternatively, the close comment could list the exact shape left out (in-batch #593-held U, D COMPLETE at start), so a re-filer can match it. "The hand-driven residual" alone is too vague to match.
- [x] **The repo/branch target and verification commit could not be checked.** Brief:4-5 pins `origin/main @ b5f5c29`. The target checkout here has no `.git` directory visible to Glob, so I could not confirm that the grounding tree is that commit. The line citations match this tree, so any drift is probably harmless. For a close disposition with no code, this is low risk.

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
- Plan advisory: 5 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
- #652 publish: make sure its PR body carries `Fixes #624` — #624's duplicate close depends on it (nothing in #652's bundle pins it yet).
