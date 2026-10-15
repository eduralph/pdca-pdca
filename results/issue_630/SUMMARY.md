# Result — issue 630 / wave-pr-lands-unapproved-earlier-wave-work

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: Since #593 (PR #619: commit `b21f248`, merged into main by `a8405ae`) a wave>0 PR opens against the real base (`pr_base = base` when the bundle has a recorded stack base, `template/src/pdca_harness/publish.py:282`) and is cut from the run's integration line (`publish.py:261-265`). That line holds EVERY earlier-wave bundle of the target, not only the PR's declared prerequisites (`template/src/pdca_harness/integrate.py:21-24`; `docs/07-crosscutting.md:648-650`). So merging any wave>0 PR lands every earlier-wave bundle on the base, including one whose own PR the human closed. Reproduced with the real fold by the #593 round-3 adversary review: wave 0 = {A, Z} (Z unrelated); B `Depends on: A` only. B's PR carries Z's commits, and merging B lands Z on `main` even if Z's own PR was rejected.
- Success criterion: At sign-off the human confirms all of: (a) #463's issue body is edited to add a "Done when" that includes #630's reproducing test: "real git, stack mode: wave 0 = {A, Z}, Z unrelated; B `Depends on: A` only. After the run, B's PR branch must not contain any commit of Z's branch, so closing Z's PR keeps Z's work off `main` whatever happens to B." (a comment alone is not enough: #463's Plan reads its body); (b) the human has chosen, explicitly, how the delay is handled, since #630 is a `bug` that breaks the approval invariant and #463 sits in milestone 0.60.0: either move #463 to the milestone #630 is in, or keep #630 open as the blocking bug linked to #463 instead of closing it; (c) if (b) chose to close, #630 is closed as a duplicate of #463 with a comment pointing at the edited Done-when. Nothing is built in this bundle.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: Close #630 as a duplicate of #463 and move its reproducing test there. / out of scope: any code change in this bundle. Alternatives weighed: (1) "merge/publish refuses while a carried bundle's PR is closed", rejected at Plan: in stack mode the human merges, not the harness, and a carried bundle's PR is typically closed after the dependent's PR was opened, so publish cannot see it. (2) Restore the line as the own-repo `pr_base` (pre-#593 behaviour; today `pr_base` is `base` whenever `wave_stacked`, `publish.py:282`). This makes #630 a regression from #593 ("Before #593, an own-repo wave>0 PR targeted the line and could not reach `main`", #630 body). Rejected: #593 moved away from it because "a PR merged into it never reaches the target" (`publish.py:266-268`), and it would not help fork PRs, which can never `--base` a branch on origin (`publish.py:279-280`). Only #463's dependency-scoped line fixes both.

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
- [x] **The duplicate claim contradicts the thread.** The issue body says outright that #463 is a different problem: "#463 (only declared dependencies need a stacked base) is the nearest issue, but it is about PR bases, not about unapproved content reaching the base." The brief's opening note recasts #463 as "the integration line carries only a PR's declared prerequisites". By its own title, quoted in the brief's Prior-art line, #463 is only about which *base* a PR stacks on. Fixing bases does not change what a PR carries. B is cut from the line (`publish.py:261-265`), and the line holds every earlier-wave branch (`integrate.py:21-23`). So a #463 fix limited to bases would leave B carrying Z, with #630 already closed. #463's own text is not in `sources/` (there is no `sources/` dir in this bundle), so nothing here backs the claim that #463's scope covers line content. The planner should either cite #463's body or Done-when showing it covers this, or make the close conditional on amending #463's Done-when (see the next finding).
- [x] **The success criterion checks the comments, not the hand-off.** The brief line is: "the closing tracker comment on #630, plus a comment on #463, carries #630's reproducing test". A comment on #463 does not put the test into #463's Done-when or its brief. #463's eventual Plan can pass without it, and the defect is silently dropped. The criterion should require #463's issue body (its Done-when) to be edited to include the {A, Z} → B "B's branch contains no commit of Z" test, and the human should confirm that edit at sign-off.
- [x] **A STOP-discipline bug is parked behind a later milestone.** #630 is labelled `bug`, and it breaks the invariant the brief itself quotes ("Closing a bundle's PR keeps that bundle's work off the base", `docs/07-crosscutting.md:644-648`). The brief places #463 in milestone 0.60.0. Closing #630 as a duplicate therefore pushes an approval-bypass bug back to whenever #463 ships, and the brief does not name that trade-off. The human should decide it explicitly, for example by moving #463's milestone or keeping #630 open as the blocking bug linked to #463.
- [x] **Thread context the brief leaves out.** The thread says: "Before #593, an own-repo wave>0 PR targeted the line and could not reach `main`." That makes this a regression from #593. It also points to a third remedy the brief never weighs: for own-repo runs, restore the line as `pr_base` (`publish.py:282` currently sets `base` whenever `wave_stacked`). The brief rejects only the "merge/publish refuses" alternative. The trade-off is real, because `publish.py:266-268` explains why #593 moved away from line bases. Still, the brief should record that this option was considered and why it was rejected. As written it reads as though #463 is the only fix.
- [x] **The #593 commit hash is inconsistent and can't be checked.** The Defect line says #593 was "merged as `a8405ae`". The Prior-art line gives "`b21f248` (#593, wave PRs against the real base: the source of this behaviour)". At most one of these is right. The target checkout has no `.git`, so neither hash, nor the pinned `b5f5c29`, could be checked here. The planner should fix the brief to give one hash.

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
