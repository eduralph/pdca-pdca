# Result — issue 655 / merged-prereq-gate-checks-the-line

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: In stack mode a dependent of an out-of-batch prerequisite P (a `Depends on (merged): P`, or since #647 a plain `Depends on: P` the run was not asked for) waits until P's PR has merged into the dependent's own target base: `flow._runnable` asks `merged.merged_into(cfg, dep, repo, base)` (`template/src/pdca_harness/flow.py:739-744`; `template/src/pdca_harness/merged.py:67-111`), which reads the PR's state from the host. It never asks whether the base the dependent will actually build on has that merge. Once this run has folded the target, the dependent is pointed at the run's integration line (`flow._point_at_integration`, `flow.py:770-790`, called at `:2209`). That line was cut from the base at the run's first fold (`integrate.fold` "fresh", `template/src/pdca_harness/integrate.py:429-431`), and every later fold continues it without taking the base in (`integrate.py:419-430`). So when P's PR merges into `main` mid-run, after the line was cut (or, on a resumed run, after the line the #646 carry continued was last updated from the base), a later-wave dependent passes the gate and is built, verified and published on a line without P's change, and nothing says so. Present since #186's `(merged)` path. #647's plain-edge hold reuses the same check.
- Success criterion: With the patch, on a real-git stack-mode run (bare `origin`, non-stub publisher, `gh` stubbed: the `StackFoldGit` fixture of `template/tests/test_integrate_stack_bases.py`, driven through `flow._drive_and_act` the way `template/tests/test_flow_resume_stack_prereqs.py` does):
  (1) **`Depends on (merged)`.** P is COMPLETE with a published branch and an OPEN PR, and is not in the batch. Drive set: `W` (wave 0) and `D` with `- **Depends on:** W` and `- **Depends on (merged):** P` (wave 1). After wave 0's fold has pushed the line, P's PR merges into `main` (`fx._merge_pr("P")`, and the `gh` stub now answers MERGED with P's head). `D` is not built, stays PLANNED, and ONE stderr line names `issue_D` and `issue_P`, says P's PR merged into `main` but the line `D` would build on (its short tip SHA) does not have that merge, and what to do (re-run). The wording must not claim this run cut the line: on a resumed run the line was continued from origin by the #646 carry (`flow.py:880-883`, `:943`), not cut.
  (2) **Plain `Depends on` (#647 edge).** The same with `D`'s edge to P being a plain `- **Depends on:** P` (P not requested): `D` is held the same way.
  (3) **Unchanged.** If P's merge is already on the line (P merged with a merge commit before the run's first fold, so the fresh line holds it), `D` is built on the line.
  (4) **Squash merge before the run.** As (3), but P's PR was SQUASH-merged into `main` before the run's first fold (in the scratch clone: `git merge --squash` P's branch, commit, push; the `gh` stub reports that commit as `mergeCommit`). `D` is built on the line: the check is on the commit the merge put on the base (`mergeCommit`), not on P's `headRefOid`, which a squash or rebase merge never puts on the base (`integrate.py:504-505`, `:533`).
  (5) **Unreadable.** If the merge commit cannot be read (the `gh` stub fails for P) or the checkout cannot be fetched, `D` is held (fail-closed, as #647's `merged_into` already is). If this run has not folded `D`'s target (no line, so `D` is cut from the freshly fetched base), `D` is built as today. Every existing test in `test_flow_out_of_batch_prereq_hold.py` passes.
  Pre-fix, (1) and (2) build `D` on a line whose tip does not contain P's merge. That is the RED. (4) is green before and after; it guards against a fix keyed on `headRefOid`.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: Make the out-of-batch "merged into the dependent's base" gate (both the `Depends on (merged)` edge and #647's plain-edge hold) answer for the base the dependent will actually be cut from: when the run has a line for that target (`folded_tips`), P's merge must be on that line, else the dependent is held and named. Design (chosen): "P's merge is on the line" means the commit P's PR merge put on the base (`gh pr view --json mergeCommit`, read in `merged.py` next to `merged_head`, `merged.py:114-143`, with the same fail-closed reading) is an ancestor of the line tip the run recorded. This holds for merge, squash and rebase merges alike. The ancestry question is answered in the checkout the #646 carry already reads from, `integrate.carry_view` (`integrate.py:185-193`, as `_carry_finished` calls it, `flow.py:910`): it fetches first, and it only reads, so it needs no integration lock. A fetch failure or an unreadable merge commit holds the dependent (criterion (5)). Update `docs/07-crosscutting.md:704-719` to say the dependent also waits when the run's line does not yet hold the prerequisite's merge. / out of scope: refreshing or re-cutting the line mid-run (declined at Plan); taking the base into the line (#623 covers what can go wrong there); merge mode (it merges the base forward itself; `_runnable`'s `hold_unmerged` is off there, `flow.py:2159-2160`); `merged.is_merged` and its other callers; a target with no line yet (unchanged, criterion (3)).

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

Review issue #655: prevent stack-mode dependents from building on an integration line that lacks a merged prerequisite, while preserving carried prerequisites and providing a working recovery path.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | Both dependency forms have falsifiable missing-merge cases, compatibility cases, and fail-closed requirements; the iteration explicitly requests carried-head compatibility and effective recovery advice (`brief.md:12`, `brief.md:44`; `target/template/tests/test_flow_merged_prereq_on_line.py:202`). |
| C2 Reproduction (red pre-fix) | PASS | Stashing the tracked fix while retaining the new test independently produced five assertion failures in nine tests, including both dependency forms building D without P's merge (`review-red.log:73`; `target/template/tests/test_flow_merged_prereq_on_line.py:202`, `target/template/tests/test_flow_merged_prereq_on_line.py:212`). |
| C3 Change | PASS | The four affected files address the specified readiness decision, host metadata, regression evidence and user recovery guidance; the carried-head exception and recovery revision are authorized by the iteration (`target/template/src/pdca_harness/flow.py:773`, `target/template/src/pdca_harness/merged.py:149`, `target/docs/07-crosscutting.md:745`; `brief.md:44`). |
| C4 Verification (red→green) | PASS | After stash pop, all nine new regressions and 55 adjacent tests passed; the failures were behavioral assertions, not import or tool failures, independently confirming the frozen C4 result (`review-red.log:75`, `review-green.log:4`; `gate-logs/C4-verify.log:10`). |
| C5 Causal adequacy | PASS | Checking the recorded build tip closes the demonstrated stale-line admission gap; real-git cases also establish squash compatibility, failure holds, carried-head admission, and successful recovery after deleting the old line (`target/template/src/pdca_harness/flow.py:860`; `target/template/tests/test_flow_merged_prereq_on_line.py:230`, `target/template/tests/test_flow_merged_prereq_on_line.py:269`, `target/template/tests/test_flow_merged_prereq_on_line.py:293`). |
| T1 Structure | PASS | Readiness remains in the flow gate, PR metadata stays in the merged module, and ancestry/fetch reuse existing integration helpers; no new dependency or unrelated subsystem is introduced (`target/template/src/pdca_harness/flow.py:831`, `target/template/src/pdca_harness/merged.py:184`, `target/template/src/pdca_harness/integrate.py:205`). |
| T2 Shape | PASS | Independent docs lint, 22-page site render/link audit, production-import scanner and diff whitespace check passed; frozen docs and host-CI-parity logs agree (`target/docs/07-crosscutting.md:745`; `gate-logs/T2-docs.log:10`, `gate-logs/host-ci-docs.log:10`, `gate-logs/C5-prod-path.log:10`). |
| T3 Runtime | PASS | Independent driver suite: 2,451 tests, OK with two skips; root render/update coverage rests on the frozen 24-test passing run because local Python lacks importable Copier, a reviewer-host limitation rather than a patch defect (`review-suite.log:1817`, `review-root.log:6`, `gate-logs/T3-suite.log:38`, `gate-logs/T3-suite.log:54`). |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the gate explicitly defers its substantive PR-body/tracker audit to the mandatory publish rerun (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Confirm the affected-path merged-history and closed/rejected-work review is complete — the brief records flow.py/merged.py history, but the supplied target has one synthetic commit and no remotes, preventing independent confirmation across all four affected paths (`brief.md:32`, `review-prior-art.log:1`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Accept holding dependent work until an operator deletes the old integration line after the run and reruns the batch — the recovery succeeds in real-git tests, but its operational suitability and ancestry-based prerequisite contract require human sign-off (`target/docs/07-crosscutting.md:745`, `target/template/tests/test_flow_merged_prereq_on_line.py:293`). |

Independent verification used the supplied disposable target only. `git stash push` removed the three tracked changes and left the new regression file available; `git stash pop` restored them before the green run. The target remains in its original patched state. Source citations above refer to that restored target; there was no stale-target or patch-application caveat.

Commands exercised from `target/template`, with `PYTHONPATH=src`, were `python3 -m unittest tests.test_flow_merged_prereq_on_line` for red, `python3 -m unittest tests.test_flow_merged_prereq_on_line tests.test_flow_out_of_batch_prereq_hold tests.test_flow_resume_stack_prereqs tests.test_merged` for green, and `python3 -m unittest discover -s tests` for the full driver suite. Logs are `review-red.log`, `review-green.log` and `review-suite.log`. Temporary fixture roots were confined to this review directory through `TMPDIR`.

From `target`, `python3 docs/publishing/tools/lint_docs.py` and `python3 docs/publishing/tools/render_site.py --check --out /tmp/pdca-review-ccrml598/review-site` passed. The reference production-path scanner, given this bundle and `PDCA_PROD_PACKAGE=pdca_harness`, confirmed that the new test imports production. `git diff --check` was clean. The instance-specific gate wrappers were not treated as target-checkout tools.

The root-suite attempt exited 77 because Copier is not importable by this interpreter; its local skipped run is not counted as verification. The frozen T3 log explicitly shows the render, CLI-name and update-compatibility cases running successfully, followed by 24 tests and OK. Likewise, the frozen host-CI log establishes local CI-command parity, not an observed hosted CI run.

The regression fixture uses real git repositories and production flow/integration logic, with GitHub responses and build/sign-off leaves stubbed as specified. It can exhibit the forbidden topology: the independent red run actually builds D without P's merge. Therefore this is not a fixture that structurally excludes the failure, and no required external dependency remains undischarged for the specified offline criterion. A live GitHub workflow was not exercised.

The C5 symptom-guard smell-test does not fire: this is a prerequisite-readiness predicate at the scheduling boundary, not a capability probe masking an eager/load-time side effect. The two prior implementation concerns are covered by passing tests: a carried PR head suffices even without main's merge commit, and rerunning alone retains the old line whereas deleting it before rerunning permits D to build. No additional builder-fixable concern was established.

Prior-art investigation ran by all four affected paths. `review-prior-art.log` records the single synthetic base commit and empty remote listing; the historical hashes and closed-PR dispositions in the brief cannot be independently checked from this artifact set. The available integration template leaves project-specific human-only items as TODO (`target/template/docs/INTEGRATION.md.jinja:80`), so it supplies no additional enumerated decision to adjudicate.

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — issue 655 (merged-prereq-gate-checks-the-line)

Lens: bugs the patch introduces, plus reuse/simplification/efficiency. Advisory only.

**Verdict: no correctness bugs found.** The gate fails closed in every path I traced, the cache keys are right, and the tests use real git and cover all five brief criteria plus the carried-head case from round 1. The C4 log shows 5 of 9 new tests red with the production hunks reverted (`gate-logs/C4-verify.log`, "FAILED (failures=5)"), and they are green with the fix. Only small cleanups below, none blocking.

## Correctness (checked, nothing found)

- `template/src/pdca_harness/flow.py:776-784` — the new check runs only when `merged_into` is already True, the target has a line, and the tip is recorded (not a dry run). `lacks` is keyed by `(prereq, repo, base)`, and `lines` has one entry per `(repo, base)`, so a cached answer can't be reused for a different line. A close/no-fix prereq is skipped through `integrate._has_patch`, which matches `merged_into`'s own short-circuit (`merged.py:93-95`).
- `template/src/pdca_harness/flow.py:831-868` (`_line_lacks_merge`) — fail-closed is correct: a fetch error, a `gh` failure (`merge_and_head` → None → both oids empty → "could not be read", False) and a git exit 128 from `_in_line` (`integrate.py:812-818`, caught as `IntegrationError`) all hold D. Accepting either `mergeCommit` or `headRefOid` on the tip fixes round 1's false hold without weakening criterion (4). A squash is still judged on `mergeCommit`, and a stale head simply isn't an ancestor.
- `template/src/pdca_harness/flow.py:2335-2336` — `lines` is built from `integ`, which is only filled on the stack-fold path (`flow.py:2480`, `:1094`). Merge mode is not affected, which matches the brief's scope.
- `template/src/pdca_harness/merged.py:172-200` — the `_pr_view` extraction keeps `pr_state`'s old behaviour: same None cases, and the same `state`-is-a-string check, now done after the `_pr_view` call at `merged.py:178`.

## Cleanups (optional)

- `template/src/pdca_harness/merged.py:117-146` — `merged_head` still runs its own `subprocess.run(["gh","pr","view",…,"state,headRefOid"])` + JSON parse, which is the body the patch just pulled into `_pr_view` (`merged.py:185`). It could call `_pr_view(str(pr_url), "state,headRefOid")` and keep its own stderr line on None. This is minor, and the brief doesn't require it.
- `template/src/pdca_harness/flow.py:773` + `:857` — for each held-or-checked prereq the PR is read from `gh` twice: once in `merged_into` (via `pr_state`, `merged.py:100`) and again in `merge_and_head` (`merged.py:164`). One `state,headRefOid,mergeCommit` read could serve both. It's cheap (one extra `gh` call per out-of-batch merged prereq per wave, and only when the target has a line), so leaving it is fine.
- `template/src/pdca_harness/flow.py:851-852` — on a fetch failure the held line embeds `_fetch`'s message, which ends "the fold cannot see the branches it merges" (`integrate.py:874-875`). That wording fits a fold, not this gate, so the stderr line reads a little oddly. Wording only.

## Recovery advice (for the human, not a code bug)

- NEEDS-HUMAN [human] — `template/src/pdca_harness/flow.py:809-814` and `docs/07-crosscutting.md:752-757` tell the operator to "delete {branch} on origin, then re-run". I checked whether this could close open PRs: in wave stack mode a bundle's PR targets the base, not the line (`publish.py:282`, `pr_base = … and not wave_stacked`), so it shouldn't close them. It does throw away the line's fold history, and the re-run rebuilds it through the #646 carry. The test proves this works for one W + D batch (`template/tests/test_flow_merged_prereq_on_line.py`, `test_the_way_out_is_to_delete_the_line_then_re_run`). Whether telling users to delete a remote branch is acceptable advice, instead of a harness-side option to re-cut the line, was declined at Plan as out of scope. It is still a product decision worth a look at sign-off.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — Confirm the affected-path merged-history and closed/rejected-work review is complete — the brief records flow.py/merged.py history, but the supplied target has one synthetic commit and no remotes, preventing independent confirmation across all four affected paths (`brief.md:32`, `review-prior-art.log:1`).
- [x] Validation — fitness-to-purpose — Accept holding dependent work until an operator deletes the old integration line after the run and reruns the batch — the recovery succeeds in real-git tests, but its operational suitability and ancestry-based prerequisite contract require human sign-off (`target/docs/07-crosscutting.md:745`, `target/template/tests/test_flow_merged_prereq_on_line.py:293`).
- [x] `template/src/pdca_harness/flow.py:809-814` and `docs/07-crosscutting.md:752-757` tell the operator to "delete {branch} on origin, then re-run". I checked whether this could close open PRs: in wave stack mode a bundle's PR targets the base, not the line (`publish.py:282`, `pr_base = … and not wave_stacked`), so it shouldn't close them. It does throw away the line's fold history, and the re-run rebuilds it through the #646 carry. The test proves this works for one W + D batch (`template/tests/test_flow_merged_prereq_on_line.py`, `test_the_way_out_is_to_delete_the_line_then_re_run`). Whether telling users to delete a remote branch is acceptable advice, instead of a harness-side option to re-cut the line, was declined at Plan as out of scope. It is still a product decision worth a look at sign-off.
- [x] **The planned "is P on the line" test produces false holds for squash and rebase merges, and the success criterion cannot see it.** The brief has Do check that "the head a PR merged with" (`merged.merged_head`, `merged.py:114-143`, which returns `headRefOid`) is on the line through `integrate._carries`. After a squash or rebase merge, `headRefOid` is never an ancestor of `main`, so it is never on a line cut from `main` either. The harness already knows this: `integrate.py:504-505` says "a squash or rebase merge never puts it on the base either", and `integrate.py:533` says the same. So if P squash-merged into `main` *before* the run, the fresh line does hold P's change, yet the new check holds `D`. Today `D` builds correctly in that case, so this is a regression on a common repo setting. Criterion (3) covers only the "merge commit" case: the fixture's `_merge_pr` is `--no-ff` (`test_integrate_stack_bases.py:180-185`), so the RED/GREEN cannot detect this. The brief needs to either (a) specify a merge-strategy-independent test (for example, whether the line holds the base commit that the PR's merge produced or that existed when P read MERGED — fetch the base and check `<base_remote>/<base>` ancestry against the line tip), or (b) state in Scope that squash/rebase-merged prerequisites are held, fail-closed, with a hint, and add a criterion leg (4) that pins that behavior.
- [x] **Which git clone answers "on the line" is unspecified, and lock scope is ignored.** `_runnable` (`flow.py:681-767`) does no git work today; it only reads bundle state and the `gh` PR state. `integrate._carries(wt, …)` (`integrate.py:539`) needs a worktree, and the only one is the integration worktree that `_fold_lines` uses under the integ lock (`flow.py:809-820`). That function's docstring says the lock exists so that "no gap exists in which another flow's publish-boundary sweep could remove the tree". The flow loop keeps only `folded_tips` and `integ` (branch names), not the worktree (`flow.py:2304-2307`). Do must therefore invent the plumbing: which repo, whether to fetch first, and whether to take the lock. That is review surface the brief leaves out. The brief should name the clone (for example `integrate.carry_view`, `integrate.py:185`, already used by `_carry_finished` at `flow.py:910`) and say whether a fetch or lock is required. It should also say what an unreadable clone means: hold, matching #647's fail-closed rule.
- [x] **The required stderr wording is wrong for a line this run did not cut.** Criterion (1) says the line must state that "P merged into `main` after this run's line was cut". But the line is not always cut by this run. `_carry_finished` *continues origin's existing line* from a prior run's tip, and seeds `integ`/`folded_tips` before wave 0 (`flow.py:880-883`, `:943`). The Defect sentence "That line was cut from the base at the run's first fold" (`integrate.py:429-431`) also leaves out the carry path. The gate logic is unaffected, since checking the line tip handles both paths. The fixed wording is not: on the carry path it would misstate the cause. Either word the criterion around "the line `D` would build on (`<tip>`) lacks P's merge", or add a carry-path leg to the criterion.
- [x] **The documented contract will become incomplete, and no doc surface is planned.** The brief cites `docs/07-crosscutting.md:704-719` as the source of the invariant. That text promises the dependent "waits until that prerequisite's PR merges into the dependent's own target base" and lists every case where nothing is held. After the fix there is a new hold: merged into the base, but not on this run's line. The doc does not describe it, and the brief lists `Surfaces: data` only. Either add the doc update to the scope explicitly, with a citation, or record that the doc change is deliberately left out. Otherwise Do will either add it unasked or leave the doc wrong.
- [x] T5 Judgment — Confirm the affected-file prior-art check, including docs and closed/rejected work — the brief records production-path triage, but the supplied target has only one synthetic base commit and cannot independently establish that history (`brief.md:32`; affected documentation at `target/docs/07-crosscutting.md:745`).

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
- Plan advisory: 4 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
- Plan-advisory findings already resolved in the brief revision should not be carried into Check §6 as NEEDS-HUMAN; the plan-review session is where they are cleared (issue_655 surfaced 4 such items).
- Follow-up (issue_655): add a built-in way to restart a stale stack-mode line from the base (or a `pdca` command that deletes it), instead of telling operators to delete the line on origin by hand before re-running.
