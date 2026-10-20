# Result — issue 748 / name-the-joint-partners-of-a-cross-wave-fold-clash

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: 
- Success criterion: Real-git tests through `flow._drive_and_act` on `StackFoldGit`, loaded as in `test_flow_same_wave_conflict.py:36-56`, asserting the holds map, the named partners in stderr, and `cli._results_rc(results, holds=holds)`:
  (1) **Together only** (parent case 4). The path conflicts against `P` and `R` combined but against neither alone. The bundle is held naming both `issue_P` and `issue_R`. An unrelated chain completes. No `STOPPING`. Exit 3.
  (2) **Unrelated line bundle not named** (iteration-1 probe). Same as (1) plus an unrelated `X` on the line that touches other files. `issue_X` does not appear in the hold line or its proposed `Conflicts with`.
  (3) **Direct and joint on the same file** (iteration-3 `probe-same-file`). The head clashes directly with `A` and jointly with `P`+`R` in the same file. The hold names `A`, `P` and `R`. The proposed rebuild merges cleanly onto the line when tried.
  (4) **Several joint clashes at once** (iteration-2/3 probe-joint). Two separate joint pairs in different files. Both pairs are named, and nothing else.
  (5) **Still a stop.** `test_flow_same_wave_conflict.py::test_a_conflict_only_with_a_base_taken_in_mid_wave_still_stops_the_run` still prints `STOPPING`, unchanged: its clash is with base work the line took in, not with any line bundle, so either child-1 already stops it before this fallback runs or no S passes the acceptance check (the base work stays in every trial). One new guard: a clash only three line bundles cause together (no size-1 or size-2 set) still prints `STOPPING`. child-1's `test_a_clash_two_line_bundles_cause_only_together_still_stops` (in `test_flow_cross_wave_fold_holds.py`) flips to a hold, and `build-notes.md` records that flip.
  With the production change reverted, (1)-(4) print `STOPPING` and the unrelated bundle stays PLANNED. child-1's suite and the existing suites stay green, apart from the flipped guard.
- Repo + branch target: eduralph/pdca-harness @ main (PRs target `main`). Do builds and the gate verifies on the run's line, `pdca-integration/main-r547f8028520f` with #738 and child-1's accepted work folded on top (child-3 #749 builds after this one), exported as `$PDCA_VERIFY_BASE`. Anchors are on `9f7c446`. Do re-checks line numbers on the folded tip.
- Scope (one logical fix) / out of scope: 

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: new-feature
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

Review the cross-wave fold fallback that holds a conflicting bundle and names exactly its direct and two-bundle joint conflict partners, while preserving conservative stops.

Source paths below are relative to `target/`, the disposable `$PDCA_TARGET`; evidence paths are relative to this review directory.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The naming rule, removal acceptance check, and explicit three-bundle/stacked limits give falsifiable outcomes without expanding the carry contract; brief.md:2, brief.md:12. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only production code produced five assertion failures, including all four required new hold cases, with STOPPING visible; review-red.log:80, template/tests/test_flow_cross_wave_joint_holds.py:275. |
| C3 Change | PASS | The fallback stays in fold classification, retains the existing acceptance rule, and leaves the carry's classifier unchanged; template/src/pdca_harness/integrate.py:1841, template/src/pdca_harness/integrate.py:1969. |
| C4 Verification (red→green) | PASS | Restoring production code changed the same 14-test run from five failures to all passing; the frozen gate independently records that transition; review-green.log:3, gate-logs/C4-verify.log:10. |
| C5 Causal adequacy | PASS | Real git proves joint conflict and exact attribution rather than file overlap; the removal trial rejects unexplained clashes, and an additional advanced-prerequisite probe names only P/R; template/src/pdca_harness/integrate.py:1850, template/tests/test_flow_cross_wave_joint_holds.py:321, review-own-change.log:1. |
| T1 Structure | PASS | Existing trial/worktree restoration machinery is reused, the acceptance predicate is extracted coherently, and the quadratic search runs only after conflict; template/src/pdca_harness/integrate.py:1859, template/src/pdca_harness/integrate.py:1934. |
| T2 Shape | PASS | Independent whitespace, docs lint, and site render/link checks passed; the host-parity log also shows lint and link audit success; gate-logs/host-ci-docs.log:10, template/src/pdca_harness/integrate.py:1916. |
| T3 Runtime | PASS | Independently reran 2,624 driver tests successfully (two skipped); frozen evidence additionally shows 24 root render/update tests passing; review-suite.log:1817, gate-logs/T3-suite.log:54. |
| T4 Contribution | N/A | Contribution artifacts are intentionally absent at Check; the substantive contribution audit must run at publish; gate-logs/T4-contribution.log:10. |
| T5 Judgment | NEEDS-HUMAN | Confirm the affected-path prior-art search covers merged history and closed/rejected work before accepting this approach — the provided target has only one synthetic commit, no remote, and no such search evidence; review-prior-art.log:1, brief.md:18. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether holds with exit 3 and continued unrelated work, together with deliberate stops for three-way and stacked joint clashes and quadratic conflict-only cost, meet operator expectations; template/tests/test_flow_cross_wave_joint_holds.py:244, template/tests/test_flow_cross_wave_joint_holds.py:371, template/src/pdca_harness/integrate.py:1934. |

Independent reproduction used `git stash push -- template/src/pdca_harness/integrate.py`, retained both patched test files, ran `PYTHONPATH=src python3 -m unittest tests.test_flow_cross_wave_fold_holds tests.test_flow_cross_wave_joint_holds` from `target/template`, restored with `git stash pop`, and repeated the command. The production file was restored to the patch's expected blob (`25238c93c0e5abf95da9db43c250d4882c518a95`). The four new hold cases and flipped predecessor test fail without the fix; all 14 pass with it. The three-bundle stop guard remains green in both legs.

The full driver suite was independently rerun with `PYTHONPATH=src python3 -m unittest discover -s tests`. It includes the unchanged mid-wave-base stop regression at template/tests/test_flow_same_wave_conflict.py:435. Docs checks used the target workflow's lint and render commands, producing 22 pages with a clean link audit. The root render/update suite could not be rerun because this interpreter lacks copier; its frozen log explicitly records 24 executed, passing tests, rather than a skipped-only run (gate-logs/T3-suite.log:54). All supplied gate logs were inspected; no external dependency is declared or shown unexercised for the offline git fix.

The additional real-git probe cut H from K's old tip, advanced K, and combined the rename/rewrite pair P/R on the line. `_own_change` returned K's old shared tip, and `_together` returned exactly P/R (review-own-change.log:1). No capability-probe/load-time symptom guard was introduced. No implementation defect was established.

Prior-art investigation by all three affected file paths returned only the synthetic base commit, and `git remote -v` returned nothing (review-prior-art.log:1). The brief names earlier attempts but supplies no affected-path merged/closed/rejected search record. The unfilled project-human-items entry in template/docs/INTEGRATION.md.jinja:80 supplies no additional concrete human-only criteria.

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — issue #748 (joint partners of a cross-wave fold clash)

Lens: bugs the patch adds, plus reuse / simplification / efficiency. Grounded on the patched target at `$PDCA_TARGET`. Gates: C4 shows 4 of 5 new cases red before the fix and all green after (the three-bundle guard is green both times, as expected). T3 passes.

I found no correctness bug in the production change. The search does what the brief asks: size-1 names, pairs only among bundles that merged cleanly alone (so each named pair is minimal), stacked bundles left out of pairs, and the acceptance check reuses #747's rule through `_explains`. The `_explains` extraction is a straight move of the old inline code, with no change in behaviour. `_clash` and `_partners` are untouched, so the #694 carry contract holds.

- NEEDS-HUMAN [impl] — Nothing tests the own-change helper doing its job. `template/src/pdca_harness/integrate.py:1887` (`_own_change`) and its use at `:1939-1940` only matter when the held branch already holds part of a line bundle that touches the clashing files. In every new case, `H` is stacked on `K` (`template/tests/test_flow_cross_wave_joint_holds.py:270`), and `K` only adds `k.txt`. So the lead revs never change a trial's result. If `_own_change` returned `[]`, all five cases would still pass. Add a case where the held branch is built on a line bundle whose change is in the clashing file (for example, H stacked on P). That case should be named correctly with the helper and wrongly (or stopped) without it. Child-3 #749 will reuse this helper, so it should be tested before then.
- `template/src/pdca_harness/integrate.py:1940` — the early `return []` comment says "its own change does not merge even onto what it holds". But `_trial` returns the index of the first failing rev, so this branch also fires when two lead revs clash with each other (`at < len(lead)`), before `head` is ever merged. The result is the same (the run stops), so this is harmless. The comment is just imprecise. You could check `== len(lead)` if the two causes should be told apart.
- `template/src/pdca_harness/integrate.py:1848` — efficiency. The O(n²) pair search now also runs for every `"line"` clash, including ones caused by base work the line took in mid-wave (brief case 5), and when `_clash` falls back to `"line"` after a git step failed (`:2009-2010`). In those cases no set can pass the acceptance check, so every pair trial is wasted, and each trial checks out the worktree again. One cheap pre-check would skip it: run `_explains` with every cut-from-base bundle taken off, before the pair search. The brief accepts the cost, so this is a suggestion, not a defect.
- `template/src/pdca_harness/integrate.py:1900` — `_own_change` calls `subprocess.run` directly instead of the module's `_git` / `_out` helpers. This is justified: it needs both the exit code (1 means no common ancestor) and stdout, and neither helper gives both. No change needed. One small point: plain `git merge-base` picks one base when there is a criss-cross history. I did not check whether the branches this harness builds can have such a history.

Apart from the first bullet (a weak test, not a production bug), the diff is clean on both lenses.
<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T5 Judgment — Confirm the affected-path prior-art search covers merged history and closed/rejected work before accepting this approach — the provided target has only one synthetic commit, no remote, and no such search evidence; review-prior-art.log:1, brief.md:18.
- [ ] Validation — fitness-to-purpose — Decide whether holds with exit 3 and continued unrelated work, together with deliberate stops for three-way and stacked joint clashes and quadratic conflict-only cost, meet operator expectations; template/tests/test_flow_cross_wave_joint_holds.py:244, template/tests/test_flow_cross_wave_joint_holds.py:371, template/src/pdca_harness/integrate.py:1934.
- [ ] Nothing tests the own-change helper doing its job. `template/src/pdca_harness/integrate.py:1887` (`_own_change`) and its use at `:1939-1940` only matter when the held branch already holds part of a line bundle that touches the clashing files. In every new case, `H` is stacked on `K` (`template/tests/test_flow_cross_wave_joint_holds.py:270`), and `K` only adds `k.txt`. So the lead revs never change a trial's result. If `_own_change` returned `[]`, all five cases would still pass. Add a case where the held branch is built on a line bundle whose change is in the clashing file (for example, H stacked on P). That case should be named correctly with the helper and wrongly (or stopped) without it. Child-3 #749 will reuse this helper, so it should be tested before then.
- [ ] **None of the brief's code anchors resolve on the target source, and none of the code the fix is meant to extend is there.** The brief cites `_held_by` at `integrate.py:1747`/`:1771` and the `_clash` docstring at `:1777-1781`. On the target, `_held_by` is at `integrate.py:1261` (its "all of them" fallback is `:1285`), `_clash` is at `:1288`, and its #694 docstring is at `:1291-1315`. That is about 486 lines off. Nothing from #738 or child-1 (#747) is present either: a grep for `#738|#747|#739|#725` under `template/src/pdca_harness` finds nothing, and there is no "rule (e)" classification. The only conflict classification in `fold` is the same-wave `_held_by` call at `integrate.py:611` and the pre-wave `_clash` at `:672`. So I cannot verify the root cause ("child-1's rule (e) fails") or the planned call site from source. The brief does say "Do re-checks line numbers on the folded tip", but every load-bearing claim depends on code that does not exist yet. Either record `9f7c446` / the line ref as the authoritative grounding, or point the review target at the folded line.
- [ ] **The prerequisite is still PLANNED.** `dependency-state.json` gives `"747": {"exists": true, "state": "PLANNED"}`. The brief asks Do to build on "child-1's accepted work folded on top" and to flip "child-1's 'together still stops' guard". That guard is a test that does not exist yet, and its name and shape are unknown. Success criterion (5) and the "child-1's suite stays green apart from the flipped guard" clause cannot be checked until #747 lands. The declaration is correct, but the bundle must not be built before #747 is accepted.
- [ ] **"Merges more cleanly" is undefined, and under the obvious metric (conflicting paths) it makes case (3) fail.** The naming rule says a line bundle is named "only if base + the line without it + the head merges more cleanly than with it". `_trial` returns only `(index, paths)` (`integrate.py:1398-1404`). Take case (3): a direct clash with `A` and a joint clash with `P`+`R`, all in the same file. Leaving out `A` still conflicts in that file, and so does leaving out `P` or `R`, so the path set never changes and nothing is named. Case (3) expects `A`, `P` and `R`. The brief must state the comparison measure, for example conflict-hunk count or clean versus not clean per hunk, or the criterion cannot be falsified and the builder will make up a metric.
- [ ] **The leave-one-out rule ignores line bundles that stack on other line bundles.** Removing bundle `X` from "the line" does not remove `X`'s commits if a later line bundle was cut from `X`'s branch: merging that bundle brings `X` back. In that case leave-one-out cannot separate `X`. `_partners` handles this through `under`/`_built_on` and `_merge_over` (`integrate.py:1340-1358`, `:1363`). The brief limits the "own change only" rule to the *head* and puts `_partners` out of scope, but never says how a stacked line bundle is left out. Add a case, or state the limitation (it would fall through to `STOPPING`).
- [ ] **The cost comment the brief prescribes is probably wrong.** The brief says "O(n) trials per round". Each leave-one-out trial re-merges up to n−1 line bundles plus the head, so a round costs O(n²) merges. The acceptance trial and the case (4) search for several sets add more. Either correct the comment the builder is told to write, or say that "trial" means one multi-merge `_trial` call.
- [ ] **Scope depends on what happens to land first.** "If child-3 is already on the line, reuse its own-change helper" and "flow.py: only the announce wording … if child-1's line does not already cover it" make the patch differ depending on order. With `Conflicts with: 749` and no ordering, Do may build a second own-change helper that #749 later duplicates or clashes with. Pin the order, or say which bundle owns the own-change helper.
- [ ] **Case (5)'s "base-taken-in" clash is not defined for this cross-wave path.** On the target, `_held_by` returns None when the head merges onto `pre`+`kept`, which is the base-taken-in case (`integrate.py:1271-1274`). The new fallback runs after child-1's rule (e). The brief should name the concrete trial outcome that leaves "no set of line bundles explains it", for example that the acceptance check "base + line without the set + head merges cleanly" fails for every candidate set. Otherwise case (5) depends on how the leave-one-out search happens to end.

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
- Iteration delta (if iterating): Auto-iterate (round 1): rebuilding for the implementation-level findings — Nothing tests the own-change helper doing its job. `template/src/pdca_harness/integrate.py:1887` (`_own_change`) and its use at `:1939-1940` only matter when the held branch already holds part of a line bundle that touches the clashing files. In every new case, `H` is stacked on `K` (`template/tests/test_flow_cross_wave_joint_holds.py:270`), and `K` only adds `k.txt`. So the lead revs never change a trial's result. If `_own_change` returned `[]`, all five cases would still pass. Add a case where the held branch is built on a line bundle whose change is in the clashing file (for example, H stacked on P). That case should be named correctly with the helper and wrongly (or stopped) without it. Child-3 #749 will reuse this helper, so it should be tested before then.. Deferred, not addressed here: 8 finding(s) that need human judgment, held in deferred-findings.json for the human at handover — not build work
- By / date: auto-iterate / 2026-10-15

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 7 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
