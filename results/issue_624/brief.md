# Brief — issue 624 / hold-cascade-through-finished-dependent

> The Plan artifact (docs 02 §PLAN). Do reads ONLY this file.
> CLOSE brief: decided by the human at Plan to fold this issue into #652. Verified against
> `eduralph/pdca-harness` `origin/main` @ `b5f5c29`. Every `path:line` below is on that commit.

- **Slug:** hold-cascade-through-finished-dependent
- **Defect:** As filed (against the #593 branch, before #646 and #647 landed): `_runnable` skips a direct dependent D of a held bundle U but does not add D to `held`. If D was already COMPLETE when the run started, a later E (`Depends on: D`) passes and builds on a line that has neither U nor D. On main the shape has changed. A bundle COMPLETE at run start is never in the drive set (`flow_ids` skips it as terminal, `template/src/pdca_harness/flow.py:2537-2564`, and `flow_batch` never sweeps it, `flow.py:2377-2380`), so D is an out-of-batch prerequisite of E:
  - not one of the requested ids: E is held until D's PR merges into E's base (#647, `flow.py:734-750`, `:755-761`);
  - a requested id: D is a finished named id judged by the #646 pre-wave carry (`flow._carry_finished`, `flow.py:869-956`). There the held U is a finished id judged NOT clean (`flow.py:947-956`), and D, judged clean on its own, is carried with U's commits on its branch. That is exactly #652 ("not clean does not cascade across finished ids").
  The one remaining shape, stated exactly so a re-filer can match it: U is in the run's drive set and not yet accepted or held this run (`held_unpushed`, `flow.py:2285-2291`, or simply not COMPLETE); D (`Depends on: U`) is COMPLETE at run start and is one of the requested ids, so the #646 carry judges it clean on its own and folds D's branch, which holds U's commits, onto the line before wave 0; E (`Depends on: D`) is in the drive set. D can only be COMPLETE ahead of U if it was driven by hand (`pdca run` checks no dependencies) or U was reopened (iterated) after D completed. No other path is known, but none was ruled out by a test. Judged too rare to brief; the human accepts it as a known residual at sign-off.
- **Success criterion:** At sign-off the human confirms that #652's brief covers this issue. Its clause (2), as checked on 2026-10-10 against the revised `results/issue_652/brief.md`, reads: "(2) **#624.** `U` finished with its PR CLOSED (not clean). `D` finished, PR OPEN, `Depends on: U`, its branch cut from `origin/fix/U`. `E` in the drive set with `Depends on: D`. Batch `["U", "D", "E"]`. `E` is never built, stays PLANNED, and is named on one stderr line with `issue_D`. No commit of `U`'s branch is on the line." Tracker actions: (a) now, a comment on #624 quoting that clause, naming #652 and the residual shape above; (b) #624 is closed only when #652's PR merges with that clause's test green (#652's PR body carries `Fixes #624`), not at this bundle's sign-off. If #652 is descoped, split or discontinued, #624 stays open.
- **Falsifiability:** Not applicable to a close: nothing is built. The behaviour is made falsifiable in #652, whose clause (2) goes RED on main in `template/tests/test_flow_resume_stack_prereqs.py` (E is built on a line holding U's commit).
- **Invariant to restore:** Same as #652: a bundle that would build on work the run has judged not ready (directly or through another finished bundle) is held and named. Source: #652's carry contract, the first sentence of `docs/07-crosscutting.md:686-691` ("Only a clean prerequisite is carried"). The doc's second sentence ("holds only the bundles whose plain `Depends on` names it", `:689-691`) and the `_runnable` docstring (`flow.py:711-714`) describe today's non-cascading behaviour, which is the bug; #652's scope now includes updating that sentence and the `_carry_finished` docstring, so this close leaves no doc contradicting the fix.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Ordering note:** No scheduling edges: a close bundle builds nothing, and nothing depends on it. Its fix ships with 652.
- **Surfaces:** data
- **Difficulty:** low
- **Scope:** Record that #624 is fixed by #652's bundle, comment now, and close it as a duplicate when #652's PR merges. / out of scope: any code change in this bundle; the hand-driven residual (D made COMPLETE with `pdca run` ahead of an in-flight U that then fails to push), which can be re-filed if it is ever seen.
- **Repro instruction:** See #652's brief, success criterion clause (2), and its repro instruction.
- **External dependencies:** none
- **Test file:** none (close disposition; the regression test ships with #652)
- **Citations expected:** Do must cite path:line on the target branch for every change (none expected: close disposition).
- **Prior-art check (triage cycles):** Merged history on `origin/main` for `template/src/pdca_harness/flow.py`: `1b6831b` (#647), `c1f2306` (#646), `4b54cbe`, `29a7943`, `c67a14d`. #646 and #647 changed this issue's shape as described above. Open PRs: none. Closed-unmerged PRs touching `flow.py`: #648, #649, #638, #639, all landed via integration commits. Duplicate of #652 (open, same milestone 0.60.0), which names #624 as "the same gap in a different place".
- **Disposition hint:** duplicate

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.

Plan-review response: Revised for findings 1-4. (1) #652's clause (2) is quoted verbatim with the date it was checked. (2) The close now waits for #652's PR to merge (`Fixes #624` in its body); this bundle only comments. (3) The invariant now cites only the doc's first sentence; the second sentence is the bug, and #652's revised scope updates it. (4) The residual shape is stated exactly. Finding 5: the target checkout is at `b5f5c29` (`git -C pdca-harness log -1` shows the merge of PR #657), so the pin holds.
