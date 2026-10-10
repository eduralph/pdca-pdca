# Brief — issue 630 / wave-pr-lands-unapproved-earlier-wave-work

> The Plan artifact (docs 02 §PLAN). Do reads ONLY this file.
> CLOSE brief: decided by the human at Plan. #630's only real fix is #463's, so its
> reproducing test moves to #463 and #630 is closed as a duplicate of it. #630's body calls
> #463 "about PR bases, not about unapproved content reaching the base", but #463's own
> Proposal covers content: "A bundle that does declare one bases on a branch carrying its
> **transitive prerequisites only** — not the whole cumulative set" (#463 body, Proposal,
> second bullet, read 2026-10-10). A #463 fix limited to the `--base` flag would NOT fix
> #630, which is why the criterion below requires #463's text to carry the test. Verified against
> `eduralph/pdca-harness` `origin/main` @ `b5f5c29`. Every `path:line` below is on that commit.

- **Slug:** wave-pr-lands-unapproved-earlier-wave-work
- **Defect:** Since #593 (PR #619: commit `b21f248`, merged into main by `a8405ae`) a wave>0 PR opens against the real base (`pr_base = base` when the bundle has a recorded stack base, `template/src/pdca_harness/publish.py:282`) and is cut from the run's integration line (`publish.py:261-265`). That line holds EVERY earlier-wave bundle of the target, not only the PR's declared prerequisites (`template/src/pdca_harness/integrate.py:21-24`; `docs/07-crosscutting.md:648-650`). So merging any wave>0 PR lands every earlier-wave bundle on the base, including one whose own PR the human closed. Reproduced with the real fold by the #593 round-3 adversary review: wave 0 = {A, Z} (Z unrelated); B `Depends on: A` only. B's PR carries Z's commits, and merging B lands Z on `main` even if Z's own PR was rejected.
- **Success criterion:** At sign-off the human confirms all of: (a) #463's issue body is edited to add a "Done when" that includes #630's reproducing test: "real git, stack mode: wave 0 = {A, Z}, Z unrelated; B `Depends on: A` only. After the run, B's PR branch must not contain any commit of Z's branch, so closing Z's PR keeps Z's work off `main` whatever happens to B." (a comment alone is not enough: #463's Plan reads its body); (b) the human has chosen, explicitly, how the delay is handled, since #630 is a `bug` that breaks the approval invariant and #463 sits in milestone 0.60.0: either move #463 to the milestone #630 is in, or keep #630 open as the blocking bug linked to #463 instead of closing it; (c) if (b) chose to close, #630 is closed as a duplicate of #463 with a comment pointing at the edited Done-when. Nothing is built in this bundle.
- **Falsifiability:** Not applicable to a close: nothing is built. The test above goes RED on main today (B's branch, cut from the line, contains Z's commit), which is the evidence #463 will need. It belongs to #463's brief.
- **Invariant to restore:** (For #463, recorded here.) A PR can land on the base only the work it was reviewed as carrying: its own change and its declared prerequisites. Closing a bundle's PR keeps that bundle's work off the base. Source: the STOP discipline that the human approves each contribution (`docs/07-crosscutting.md:644-648`).
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Ordering note:** No scheduling edges: a close bundle builds nothing, and nothing in this batch depends on it.
- **Surfaces:** data
- **Difficulty:** low
- **Scope:** Close #630 as a duplicate of #463 and move its reproducing test there. / out of scope: any code change in this bundle. Alternatives weighed: (1) "merge/publish refuses while a carried bundle's PR is closed", rejected at Plan: in stack mode the human merges, not the harness, and a carried bundle's PR is typically closed after the dependent's PR was opened, so publish cannot see it. (2) Restore the line as the own-repo `pr_base` (pre-#593 behaviour; today `pr_base` is `base` whenever `wave_stacked`, `publish.py:282`). This makes #630 a regression from #593 ("Before #593, an own-repo wave>0 PR targeted the line and could not reach `main`", #630 body). Rejected: #593 moved away from it because "a PR merged into it never reaches the target" (`publish.py:266-268`), and it would not help fork PRs, which can never `--base` a branch on origin (`publish.py:279-280`). Only #463's dependency-scoped line fixes both.
- **Repro instruction:** For #463: in `template/tests/test_integrate_stack_bases.py`'s `StackFoldGit`, publish A and Z, fold [A, Z], publish B cut from the line (`cut_from=f"origin/{LINE}"`), then check `self._ancestor(self._tip("fix/Z"), self._tip("fix/B"))`. It is true on main.
- **External dependencies:** none
- **Test file:** none (close disposition; the test moves to #463)
- **Citations expected:** Do must cite path:line on the target branch for every change (none expected: close disposition).
- **Prior-art check (triage cycles):** Merged history on `origin/main` for `template/src/pdca_harness/publish.py` and `integrate.py`: `c1f2306` (#646), `4b54cbe` (#591), `b21f248` (#593, wave PRs against the real base: the source of this behaviour). The round-3 sign-off of #593 fixed only the docs. Open PRs: none. Closed-unmerged PRs touching these paths: #639, #648, both landed via integration commits. Open related issue: #463 ("stack mode bases every PR in a wave on every other — only declared dependencies need a stacked base", milestone 0.60.0).
- **Disposition hint:** duplicate

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.

Plan-review response: Revised for all five findings. (1) The brief now quotes #463's Proposal ("transitive prerequisites only"), which covers line content, and says a base-only #463 fix would not fix #630. (2) The criterion now requires #463's body (Done-when) to be edited, not just commented. (3) The milestone trade-off is now an explicit human choice in the criterion: move #463, or keep #630 open as the blocking bug. (4) The "line as `pr_base`" remedy and why it was rejected are now recorded. (5) The hashes are both right: `b21f248` is #593's commit and `a8405ae` is the merge of PR #619; the Defect line now says so.
