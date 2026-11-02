# Result — issue 839 / merge-mode-resume-or-hold-out-of-batch-prerequisite

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: 
- Success criterion: Over the `StackFoldGit` real-git fixture (`template/tests/test_integrate_stack_bases.py`) with `gh` stubbed, `wave_mode = "merge"`, runs driven through `flow.flow_ids`:
  (1) **bug leg, its own red test:** an out-of-batch COMPLETE, unmerged plain-`Depends on` prerequisite P with no marker — the dependent D is held, the hold line names P and D's base and contains neither "line of this run" nor "carries them", D is not built, and `gh` was asked only for P's PR state; (1b) the same with P NAMED in the command (`pdca flow P D`): D is held the same way (today it builds); (1c) merge mode records no `stack-base` for any bundle and `_base_plans` / `_bundle_bases` do not run (no per-bundle base is built), in (1) and in a run with no out-of-batch prerequisite;
  (2) a prerequisite that carries the marker, is unmerged, and passes `_merge_one`'s gates as they stand on the build base (rollup green; `gh pr ready` + `gh pr merge` called for it before wave 0) is merged, and the dependent then builds on the merged base (the fixture's `origin/main` has P's commit; D's worktree base has it) — for a plain `Depends on` and for a `Depends on (merged)` edge; the release happens through `merged_into`, so (2b) a marked P whose PR reads MERGED but whose record `base` is not D's base holds D (not released on rc 0);
  (3) a marked prerequisite that `_merge_one` refuses (red rollup) holds the dependent with a line naming P and saying the merge gates refused it; the run continues (an independent bundle of the same run builds and publishes); no "STOP: later waves are NOT run" is printed; `cli._results_rc` reflects a held dependent as on `main` for a `(merged)` hold;
  (3b) a COMPLETE draft PR with no marker (a final-wave or single-bundle PR waiting for the human, `merge.py:605-607`) gets no `gh pr ready` and no `gh pr merge` call, and its dependent is held, naming it and saying to merge it by hand;
  (3c) chain: marked P depends on unmarked, unmerged Q; D depends on P. P is not merged; D is held naming P and Q;
  (3d) a marked PR the driver returned to draft after a refusal is readied and merged on the next run once its rollup is green;
  (4) a close/no-fix prerequisite (COMPLETE, empty patch) releases its dependent with no `gh` call;
  (5) dry run (stub publisher) and `--no-publish`: no merge, no hold, no `gh` call — the existing `test_a_dry_run_asks_no_host_and_holds_nothing` and `test_no_publish_holds_nothing` stay green unchanged;
  (6) `template/tests/test_flow_out_of_batch_prereq_hold.py:350-356` (`test_merge_mode_holds_nothing`) pins the behaviour leg (1) reverses (D built, no `gh` call); it is rewritten to pin (1) — named here so a reviewer reads the change as this bundle's deliberate reversal of the #647 merge-mode exemption, not as weakening a guard.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: 

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: bug-fix
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

Review #839: in merge mode, merge eligible previously published prerequisites before wave 0, hold dependents safely otherwise, and prevent a rebuilt patch from inheriting an older attempt's merge permission.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The binding design defines eligibility, dependent-base safety, refusal isolation and marker lifetime; iteration 3 explicitly requires patch identity without changing the accepted scope (brief.md:62; template/src/pdca_harness/flow.py:1554). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing the three production changes makes both out-of-batch and named-prerequisite cases build D without P: two assertion failures, rather than import failures (review-red.log:3; review-red.log:16; template/tests/test_merge_resume_stranded_prereq.py:317). |
| C3 Change | PASS | The target exactly matches the supplied patch (`git apply --reverse --check` passes); the accepted scope includes the patch-hash check and keeps stack bases confined to stack mode (template/src/pdca_harness/flow.py:1557; template/src/pdca_harness/flow.py:3100). |
| C4 Verification (red→green) | PASS | After restoring the production stash, all 168 focused tests pass again, including real-git dependent-base checks and the stale-attempt regression; frozen C4 evidence agrees (review-green-after.log:8; gate-logs/C4-verify.log:2537; template/tests/test_merge_resume_stranded_prereq.py:1274). |
| C5 Causal adequacy | PASS | The changed scheduling path enforces merge readiness on the dependent's base, while permission is tied to the current patch; real flow tests observe both the forbidden merge being withheld and P's actual content reaching D's base (template/src/pdca_harness/merged.py:118; template/src/pdca_harness/merged.py:243; template/tests/test_merge_resume_stranded_prereq.py:360). |
| T1 Structure | PASS | Host mutations remain in a single pre-wave step and reuse the existing merge gates; readiness remains a separate decision, with failures isolated to waiting dependents (template/src/pdca_harness/flow.py:1604; template/src/pdca_harness/flow.py:3105). |
| T2 Shape | PASS | Independent whitespace, docs lint, 64-page rendering/link audit, six checker tests, 623 relative-link checks and ADR-index checks pass; both frozen docs gate logs also show clean results (review-doc-checkers.log:9; gate-logs/T2-docs.log:14; gate-logs/host-ci-docs.log:14; docs/07-crosscutting.md:905). |
| T3 Runtime | PASS | Independently reran 2,804 driver tests (two skips) and 45 root tests with Copier; local release-update cases lack tags, so that coverage rests on the frozen 50-test root run, which includes them (review-driver-suite.log:1824; review-root-suite-copier.log:5; gate-logs/T3-suite.log:80; tests/test_update_compat.py:244). |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the substantive audit must rerun at publish (gate-logs/T4-contribution.log:10). |
| T5 Judgment | NEEDS-HUMAN | Confirm no merged or closed/rejected work already addresses the affected paths — the path-scoped history investigation found only the synthetic base and no remote, and no prior-art evidence was supplied (review-prior-art.log:2; review-prior-art.log:6; template/src/pdca_harness/flow.py:1515). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the documented unattended-merge permission and manual recovery paths fit operations — real local git was exercised, but GitHub ready/merge, permissions and CI were simulated rather than exercised live (template/tests/test_merge_resume_stranded_prereq.py:22; docs/07-crosscutting.md:908; docs/07-crosscutting.md:925). |

No builder-fixable defect was established. The added checks inspect persisted bundle state and patch identity; they do not probe an optional capability on a path that requires it, so the C5 symptom-guard trigger does not apply.

Independent verification used the supplied disposable target, with temporary test files confined to `review-runtime/` under this sandbox. Only the three production files were stashed for the red leg; tests stayed present. The stash was popped and the patch was checked again afterward. `review-green-before.log` and `review-green-after.log` each record 168 passing tests; `review-red.log` records both original assertion failures.

The full driver command was `cd target/template && PYTHONPATH=src python3 -m unittest discover -s tests`. For the root suite, default Python exited 77 because Copier was not importable (`review-root-suite.log:6`); rerunning `python -m tests.run_root_suite` with the installed Copier venv interpreter succeeded (`review-root-suite-copier.log:8`). The synthetic target has no release tags, so its update-compatibility class skipped; the frozen gate explicitly records all five update-compatibility tests passing (`gate-logs/T3-suite.log:67`). This is a local snapshot limitation, not a patch failure.

The gate wrappers belong to the original instance and are unavailable here. I read all six supplied gate logs, reran the available underlying validators and production tests, and independently checked the new test's AST imports and calls to `flow.flow_ids`, `flow.flow_batch`, `merge.merge_wave` and `publish.publish`. The T4 deferral requires no human clearance at Check. The only supplied INTEGRATION document is the template; its human-only enumeration is a placeholder (`template/docs/INTEGRATION.md.jinja:80`), not an additional project-specific checklist.

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — issue 839, iteration 3

I read the code and did not run any probes for these findings. The gates I can see are green (C4, T3, C5, T2). T4 is deferred to publish.

- NEEDS-HUMAN [human] — `template/src/pdca_harness/merge.py:171-172`: the old-head risk rejected at sign-off is closed on the pre-wave walk but still open at the wave boundary in the same run. If P is rebuilt in a non-final wave and its re-publish fails before the push, `mark` is False, but `mark` only controls the marker. `_merge_one` still readies and merges the PR on the old record, and the next wave builds on that older attempt. `flow.py:3282` still calls `merge_wave` in that state. The test helper at `template/tests/test_merge_resume_stranded_prereq.py:1361` says the wave "attempts the old PR" and that only the red rollup stops the merge. A green rollup would merge it. This behaviour predates the patch, and the sign-off said "change nothing else", so it needs a ruling: skip that bundle at the wave boundary, and STOP or hold, the way stack mode uses `integrate.unpublished` (`flow.py:3296`), or file it separately.

- NEEDS-HUMAN [impl] — `template/docs/fork-discipline.md.jinja:74`: "A non-final wave's PR that did not merge stays marked" is false in two cases. `merge_wave` returns at the first refusal (`template/src/pdca_harness/merge.py:173-174`), so in a wave `[A, B]` with A refused, B is pushed but never attempted and never marked. A PR whose re-publish failed is also not marked (`merge.py:172`). `template/pdca.toml.jinja:131` ("Each PR it tries is marked") has the second problem. In both cases the dependents hold and are told to merge by hand, so this is safe, but a reader who trusts the docs expects a later run to pick the PR up. `docs/07-crosscutting.md` ("marks each PR it pushes and then tries to merge") is accurate, so copy that wording. I found no test for the unattempted sibling. Add one that pins B unmarked, so the behaviour is deliberate.

No other correctness bugs turned up in the iteration's change, which is the patch hash written in `_merge_one` (`merge.py:824-826`), checked in `takes` (`flow.py:1556-1557`), and reported by `_merge_way_out`. A missing or unreadable hash counts as not marked, so that PR holds its dependents. The `pushed` argument uses the same record-write check as stack mode.

No reuse, simplification or efficiency changes are worth making. `merged.has_patch` overlaps `integrate._has_patch` (`integrate.py:194`), but only `has_patch` separates an unreadable patch from an empty one, so the overlap is justified.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — Confirm no merged or closed/rejected work already addresses the affected paths — the path-scoped history investigation found only the synthetic base and no remote, and no prior-art evidence was supplied (review-prior-art.log:2; review-prior-art.log:6; template/src/pdca_harness/flow.py:1515).
- [x] Validation — fitness-to-purpose — Decide whether the documented unattended-merge permission and manual recovery paths fit operations — real local git was exercised, but GitHub ready/merge, permissions and CI were simulated rather than exercised live (template/tests/test_merge_resume_stranded_prereq.py:22; docs/07-crosscutting.md:908; docs/07-crosscutting.md:925).
- [x] `template/src/pdca_harness/merge.py:171-172`: the old-head risk rejected at sign-off is closed on the pre-wave walk but still open at the wave boundary in the same run. If P is rebuilt in a non-final wave and its re-publish fails before the push, `mark` is False, but `mark` only controls the marker. `_merge_one` still readies and merges the PR on the old record, and the next wave builds on that older attempt. `flow.py:3282` still calls `merge_wave` in that state. The test helper at `template/tests/test_merge_resume_stranded_prereq.py:1361` says the wave "attempts the old PR" and that only the red rollup stops the merge. A green rollup would merge it. This behaviour predates the patch, and the sign-off said "change nothing else", so it needs a ruling: skip that bundle at the wave boundary, and STOP or hold, the way stack mode uses `integrate.unpublished` (`flow.py:3296`), or file it separately.
- [x] `template/docs/fork-discipline.md.jinja:74`: "A non-final wave's PR that did not merge stays marked" is false in two cases. `merge_wave` returns at the first refusal (`template/src/pdca_harness/merge.py:173-174`), so in a wave `[A, B]` with A refused, B is pushed but never attempted and never marked. A PR whose re-publish failed is also not marked (`merge.py:172`). `template/pdca.toml.jinja:131` ("Each PR it tries is marked") has the second problem. In both cases the dependents hold and are told to merge by hand, so this is safe, but a reader who trusts the docs expects a later run to pick the PR up. `docs/07-crosscutting.md` ("marks each PR it pushes and then tries to merge") is accurate, so copy that wording. I found no test for the unattempted sibling. Add one that pins B unmarked, so the behaviour is deliberate.
- [x] **The problem statement cannot be checked against the tracker, and the brief admits its reproduction is unconfirmed.** This sandbox has no `notes.json`, `sources/` or `dependency-state.json`; only `brief.md` is present. So I could not test the defect, any failed prior attempt or any maintainer constraint against the thread. The brief also says "**Before building:** confirm with the human which edge type the getwyrd/wyrd #772 chain used and which harness version ran it", so its link to the real incident is an open question. Grep finds no `has_contribution` under `template/`, which fits the brief's claim that the mechanism is not on main (I could not run `git log -S`). Resolve the edge type and version at sign-off, before Do. If the chain used `has_contribution` on another version, the framing of leg (a) may not describe the reported failure.
- [x] **Criterion (2) requires "threads resolved", but nothing on main reads threads and the brief excludes that work.** The criterion says a prerequisite that is "clean (threads resolved, rollup green) is merged through `_merge_one`'s gates". `_merge_one` (`merge.py:535-732`) has no thread gate, and grep finds no `reviewThreads` or `isResolved` under `template/`. The scope line puts "reading review threads (child-1)" out of scope, and the brief declares no `Depends on` for child-1. As written, a PR with unresolved threads and a green rollup would be auto-merged, and the "threads resolved" clause is untestable. Choose one: declare the child-1 dependency, or drop the clause and state that a stranded PR can merge over unresolved threads. `Conflicts with` only orders work; it does not supply the gate.
- [x] **The fix leaves unmerged any stranded PR that predates the marker, possibly including the incident's chain.** The brief scopes out "PRs published before the marker existed (they hold...)". Any PR already open from the chain carries no marker, so after this change the `(merged)` edge still holds with no step that merges it, which is gap (b) again, now with a different explanation. The human needs to decide whether a manual merge or backfill path is acceptable, and the docs and hold line should name it. The current text (`flow.py:836-841`) only says to wait.
- [x] **Leg (1) misses a route that still builds on a base without the prerequisite: naming it in the command.** Hold candidates require `p.name not in asked` (`flow.py:795-797`). In merge mode `_carry_finished` is skipped (`flow.py:2888`) and `held_finished` stays empty, so with `pdca flow P D` the code computes no `cand`, does not reach `unmet` at `flow.py:831-834`, and D builds without P. The stack-mode hold message makes this worse: "name X in the same `pdca flow <ids>` command so the run's line carries them" (`flow.py:836-837`). In merge mode there is no line, so following that advice releases the hold and reproduces the bug. Add a named-prerequisite case to the criterion, and require a merge-mode-specific hold message.
- [x] **The obvious fix for leg (1) drags in a second behaviour.** `own_bases = hold_unmerged` (`flow.py:2905`) and that flag also gates `_base_plans` and `_bundle_bases` (`flow.py:2924-2927`, `2994-3000`). Enabling `hold_unmerged` for merge mode by removing `cfg.wave_mode != "merge"` would also switch on per-bundle bases, which the comment at `flow.py:2903-2904` reserves for "where the line folds for real". The brief cites `hold_unmerged` as a peer callsite without this warning. State that the two flags must be separated, and add a check that merge mode still does not use own bases.
- [x] **An existing test pins the behaviour leg (1) reverses, and the brief does not mention it.** `template/tests/test_flow_out_of_batch_prereq_hold.py:350-356`, `test_merge_mode_holds_nothing`, sets merge mode with an OPEN prerequisite and asserts `_built("D", "U")` and `gh_calls == []`. The brief's "RED offline" section and test file imply a purely additive change, but this test must be deliberately rewritten. Holding also requires a `gh` read (`merged.merged_into`), so the no-`gh` assertion cannot survive. Name this reversal of the #647 merge-mode exemption in scope so a reviewer does not read it as weakening a guard. Check the thread for whether the exemption was deliberate.
- [x] **Criterion (3) implies an unscoped refactor of `_merge_one`.** It requires the dependent to be held "with the refusal reason", but `_merge_one` returns only an `int` and prints each reason directly to stderr (for example `merge.py:549`, `559-566`, `591-594`, `684-692`, `718-725`). Those messages also say "STOP: later waves are NOT run", which is false if the new path holds one dependent and continues. Surfacing the reason means changing the signature or return of every refusal site, or capturing stderr. Either way it is a second change that scope omits. The brief must specify the mechanism, and whether a refusal holds only the dependent or stops the run as `flow.py:3081-3084` does. The criterion is ambiguous on that second point.
- [x] **The marker is not specified well enough for leg (3b), its guard against over-merging, to mean anything.** The brief says it is written "when a merge-mode run publishes or merges a non-final wave PR" and "at publish/merge time", which are two different designs:
- [x] **Chains and run modes have no criterion, though the incident is described as a chain.**
- [x] **The brief says nothing about a network-blocking merge inside a decision function.** Scope places the merge call in the `flow._runnable` decision. That function currently only reads state and prints holds, and it runs for every wave before the pass-budget check (`flow.py:2931`, `2950`). One `_merge_one` can wait up to about `merge_wait_secs` for the update and rollup (`merge.py:660-674`) and mutates the host (`gh pr ready`, `update-branch`). It could also run for a dependent that the budget check then abandons. Say whether the merge belongs in a pre-wave step instead, as `_carry_finished` does at `flow.py:2888-2891`. That choice changes the size of the review surface.
- [x] **Three `merge.py` citations and the `Conflicts with` note do not resolve.**
- [x] **The docs change is under-scoped.** The brief names only the merge-mode bullet from `docs/07-crosscutting.md:858` and the "this run's PRs" rule. `docs/07-crosscutting.md:902-904` also says of the final wave that "a later merge-mode run can still pick up its open PRs one at a time", which contradicts leg (3b), where unmarked final-wave PRs are never merged. The comments and error text at `merge.py:553-554` and `merge.py:603-608` ("the final wave never reaches here"), and the `hold_unmerged` docstring at `flow.py:711`, also go stale. Add them to scope.
- [x] size backstop — this slice is behaving oversized: patch is 148 KB (threshold 125 KB); 3 round(s) already spent (threshold 3). Recommend answering `iterate-plan` at sign-off and authoring the split in the re-plan (`pdca split`), rather than `iterate-do`: a slice that is too big yields implementation-shaped findings every round, and splitting authors briefs, which is Plan's beat.
- [x] T5 Judgment — Establish whether merged or closed/rejected work on the affected paths duplicates or rules out this approach — the path-based history search exposes only one synthetic base commit, no remote, and no closed/rejected evidence, so prior art remains unconfirmed (review-scratch/prior-art.log:1; template/src/pdca_harness/flow.py:1453).
- [x] C1 Spec — Decide whether the no-hold/no-host-call promise excludes `Depends on (merged)` — brief.md:12 and brief.md:21 promise it without qualification, but the existing stricter hold is deliberately retained by template/tests/test_merge_resume_stranded_prereq.py:761; the independent probe confirms one host read and D held.
- [x] T5 Judgment — Establish prior-art coverage by affected file path across merged history and closed/rejected work — the supplied repository has only one synthetic base commit, no remote, and no closed/rejected-work evidence, so overlap or an earlier rejection cannot be settled here (brief.md:30; template/src/pdca_harness/flow.py:1495).

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
- Iteration delta (if iterating): rebuild on main with #626 merged (#858; the old patch conflicts with it in flow.py and merged.py); take each prerequisite's claim in _merge_prereqs before judging or ready/merge, and hold its dependents when another run holds the claim (Codex on #859)
- By / date: Eduard Ralph / 2026-11-02

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 12 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
- issue_839 follow-up to file: wave boundary can still ready+merge an old PR head in the same run when a non-final wave's re-publish fails before its push and the rollup is green (`merge.py:171-172`, `flow.py:3282`); pre-existing; ~5 lines + test now that `merge_wave` receives `pushed`.
- issue_839 follow-up to file: `merged_into` does not check `merge_eligible_patch`, so an old PR already merged by hand releases a dependent after the prerequisite is rebuilt and never re-published; pre-existing.
- issue_839 doc wording: `fork-discipline.md.jinja:74` and `pdca.toml.jinja:131` overstate when a PR is marked (unattempted sibling after a refusal; failed re-publish); align with `07-crosscutting.md` ("marks each PR it pushes and then tries to merge") and pin the unattempted sibling with a test.
