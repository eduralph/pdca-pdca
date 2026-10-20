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

Review whether cross-wave fold clashes caused jointly by two line bundles hold the affected bundle, name exactly its necessary partners, and let unrelated work continue.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The acceptance rule distinguishes attributable size-1/2 clashes from unsupported triple/stacked clashes and specifies observable holds, advice and exit codes; brief.md:2. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only the production fix left six new tests runnable: five failed because the run printed STOPPING, reproducing the lost unrelated work; reviewer-red.log:15, target/template/tests/test_flow_cross_wave_joint_holds.py:270. |
| C3 Change | PASS | The change stays within fold classification, its own-change helper and regression coverage; the carry's existing clash contract remains intact; target/template/src/pdca_harness/integrate.py:1841, target/template/src/pdca_harness/integrate.py:1969. |
| C4 Verification (red→green) | PASS | Restoring the stashed fix made all 15 cross-wave tests pass, including the formerly failing five and the conservative stop cases; reviewer-green.log:3, gate-logs/C4-verify.log:10. |
| C5 Causal adequacy | PASS | The new ancestry case detects the prior coverage gap: replacing _own_change with an empty result wrongly names unrelated X, while the real helper passes; reviewer-own-change-mutation.log:16, target/template/tests/test_flow_cross_wave_joint_holds.py:408. |
| T1 Structure | PASS | The fallback reuses existing locked trial merges and the extracted acceptance check; rejection preserves the stop behavior and trials restore the line; target/template/src/pdca_harness/integrate.py:1848, target/template/src/pdca_harness/integrate.py:2079. |
| T2 Shape | PASS | Independent diff whitespace check, docs lint and 22-page render/link audit passed; the frozen host-parity log also shows both docs checks succeeding; reviewer-docs.log:2, gate-logs/host-ci-docs.log:10. |
| T3 Runtime | PASS | Independent integration/same-wave/reissue regressions passed 176 tests; frozen full-suite output records 24 root tests and 2,625 driver tests passing, with two driver skips; reviewer-regressions.log:29, gate-logs/T3-suite.log:54, gate-logs/T3-suite.log:1874. |
| T4 Contribution | N/A | Contribution artifacts are intentionally absent during Check; the substantive contribution audit reruns at publish; gate-logs/T4-contribution.log:10. |
| T5 Judgment | NEEDS-HUMAN | Confirm semantic non-duplication and the disposition of #739's rejected approach — affected-path merged-history and closed/unmerged-PR checks ran, but cannot settle human design intent; reviewer-prior-art-paths.log:1, brief.md:18. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Accept the bounded attribution policy and quadratic trial cost for actual batch sizes — triple-only and stacked-line joint clashes intentionally remain stops despite unrelated work; target/template/src/pdca_harness/integrate.py:1929, target/template/src/pdca_harness/integrate.py:1934. |

Independent evidence:

- Red: `git -C target stash push -- template/src/pdca_harness/integrate.py`, then unittest discovery for `test_flow_cross_wave_joint_holds.py` with the target's production package on `PYTHONPATH`: six executed, five assertion failures, one unchanged triple-clash guard passing. `git -C target stash pop` restored the production change before green verification.
- Green: the same discovery with `-p 'test_flow_cross_wave*holds.py'`: 15 tests passed. Additional discovery covered `test_integrate*.py`, `test_flow_same_wave_conflict.py`, `test_flow_reissue_after_conflict_hold.py` and `test_flow_conflict_partner_hold.py`: 176 tests passed. This includes the existing mid-wave-base STOPPING guard at target/template/tests/test_flow_same_wave_conflict.py:435.
- Mutation: ran the ancestry case with an in-memory mock returning `[]` from `_own_change`. It failed specifically because the hold named X alongside P and R (reviewer-own-change-mutation.log:16), demonstrating that the new case exercises the helper's effect rather than merely its presence.
- Independently ran the repository docs linter, site renderer with `--check`, `git diff --check`, and an AST check confirming the new test imports production modules and calls `flow._drive_and_act` (reviewer-prod-path.log:1). Output and temporary fixtures remained inside this review root.
- Instance-scoped gate wrappers are absent from this target copy. Their frozen logs were read: C4 contains actual green and assertion-failing red runs; C5 records the production import check; both docs logs show lint/render success; T3 records the root and full driver suites. Full-suite figures above are frozen evidence, not claimed as independent reruns.
- Prior art: queried GitHub merged history and closed PRs separately for all three affected paths (reviewer-prior-art-paths.log). The production path returned 22 commits including the #674 predecessor; both new test paths returned no merged commits or closed PR matches. Read the three unmerged closed matches, #639, #648 and #649: they concern integration-line isolation and prerequisite readiness, not this joint-attribution rule (reviewer-prior-art-rejected.log). This establishes the searches performed; semantic disposition remains the T5 decision above.

The target was readable and contained the prerequisite classification code; no stale-target caveat was needed. All source citations above were checked against that target. Git merges used the real executable and exercised both forbidden false attribution and required conservative stops; no external dependency is outstanding for the brief's offline criterion. No capability-probe symptom guard was introduced, and no builder-fixable defect was found.

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — issue #748 (joint partners of a cross-wave fold clash)

Lenses: correctness bugs the patch adds, and reuse / simplification / efficiency. Lines are cited on `$PDCA_TARGET` (the patched tree).

**Result: no correctness bug found, nothing needs a human.** The notes below are minor and none blocks.

## Correctness

- `template/src/pdca_harness/integrate.py:1842-1856` — the new control flow in `_held_by_line` is sound. A `"batch"` result that `_explains` accepts returns as before. `"base"`, `"off"` and `"moved"` still return None. `"line"` and a failed `"batch"` fall through to `_together`. The check `set(joint) == set(partners)` skips re-running `_explains` on a set that already failed it. `partners` is a dict there, and `set()` of it gives its names, which is what we want. `IntegrationError` raised by the new trials still becomes None (a stop), and tree errors still raise. `_clash` itself (`:1969-2013`) is unchanged, as the brief requires.
- `template/src/pdca_harness/integrate.py:1944-1955` — the index checks are right. A single bundle is named only when `head` is the merge that fails (`at == len(lead) + 1`). A pair counts only when `head` fails after both (`len(lead) + 2`). If a candidate fails against `lead` itself, it is neither named nor put in a pair, which is the safe outcome. Only bundles that merge cleanly alone go into the pair search, which matches the brief's minimal-set rule.
- `template/src/pdca_harness/integrate.py:1940` — small edge case, safe. `lead` can hold several merge-bases, one per line bundle that `head` shares commits with. They are merged one after another, and two of them could in principle conflict with each other even though `head` reconciles them. `_trial` would then return an index below `len(lead)`, and `_together` returns `[]`, so the run stops. It never names the wrong bundle, so this only costs a hold that could have been made. Not worth a change unless it shows up in practice.
- `template/src/pdca_harness/integrate.py:1943` — a stacked line bundle (non-empty `under`) is named at size 1 from `partners`, which `_partners` worked out on the full head, not on the head's own change. This is the brief's stated limit ("judged as `_partners` judges it"), and `_partners` already keeps what the bundle was built on on both sides. It is a note, not a defect.

## Tests

- `template/tests/test_flow_cross_wave_joint_holds.py:797-825` (case 6) answers the iteration-1 finding. I traced it by hand: if `_own_change` returned `[]`, the size-1 trial `[X, H]` would conflict at index 1, so X would be named. `_explains` would then accept `{P, R, X}`, because L, W and H merge cleanly. The `unrelated=("L", "X", …)` check would then fail. So the helper is now tested in a way that can fail. The C4 gate (`gate-logs/C4-verify.log`) only reverts the whole fix: 5 of 6 tests go red, and case (5), the stop guard, stays green as expected. So the helper-only revert is my hand trace, not a gate result.
- The flipped child-1 guard (`template/tests/test_flow_cross_wave_fold_holds.py:363-400`) now checks the hold, the proposal and the exit code 3, and checks that K, W and V are not named. That is a real flip, not a weaker assertion.

## Reuse / efficiency

- `template/src/pdca_harness/integrate.py:1944-1951` vs `:2031-2033` — when `lead` is empty (a head cut from the base, as in cases 1-5), the size-1 loop in `_together` runs exactly the `[its, head]` trials onto `base_ref` that `_partners` has just run inside `_clash`. That is n repeated merges. They only run on the failure path, after a fold merge has already conflicted, so the cost is small. Sharing the results would mean changing `_partners`'s return shape, which the brief puts out of scope. Leave it.
- `template/src/pdca_harness/integrate.py:1859-1884` — moving rule (e) out into `_explains` so the single-bundle path and the joint path both call it is a good reuse. The logic is moved over unchanged from the old body of `_held_by_line`.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — Confirm semantic non-duplication and the disposition of #739's rejected approach — affected-path merged-history and closed/unmerged-PR checks ran, but cannot settle human design intent; reviewer-prior-art-paths.log:1, brief.md:18.
- [x] Validation — fitness-to-purpose — Accept the bounded attribution policy and quadratic trial cost for actual batch sizes — triple-only and stacked-line joint clashes intentionally remain stops despite unrelated work; target/template/src/pdca_harness/integrate.py:1929, target/template/src/pdca_harness/integrate.py:1934.
- [x] **None of the brief's code anchors resolve on the target source, and none of the code the fix is meant to extend is there.** The brief cites `_held_by` at `integrate.py:1747`/`:1771` and the `_clash` docstring at `:1777-1781`. On the target, `_held_by` is at `integrate.py:1261` (its "all of them" fallback is `:1285`), `_clash` is at `:1288`, and its #694 docstring is at `:1291-1315`. That is about 486 lines off. Nothing from #738 or child-1 (#747) is present either: a grep for `#738|#747|#739|#725` under `template/src/pdca_harness` finds nothing, and there is no "rule (e)" classification. The only conflict classification in `fold` is the same-wave `_held_by` call at `integrate.py:611` and the pre-wave `_clash` at `:672`. So I cannot verify the root cause ("child-1's rule (e) fails") or the planned call site from source. The brief does say "Do re-checks line numbers on the folded tip", but every load-bearing claim depends on code that does not exist yet. Either record `9f7c446` / the line ref as the authoritative grounding, or point the review target at the folded line.
- [x] **The prerequisite is still PLANNED.** `dependency-state.json` gives `"747": {"exists": true, "state": "PLANNED"}`. The brief asks Do to build on "child-1's accepted work folded on top" and to flip "child-1's 'together still stops' guard". That guard is a test that does not exist yet, and its name and shape are unknown. Success criterion (5) and the "child-1's suite stays green apart from the flipped guard" clause cannot be checked until #747 lands. The declaration is correct, but the bundle must not be built before #747 is accepted.
- [x] **"Merges more cleanly" is undefined, and under the obvious metric (conflicting paths) it makes case (3) fail.** The naming rule says a line bundle is named "only if base + the line without it + the head merges more cleanly than with it". `_trial` returns only `(index, paths)` (`integrate.py:1398-1404`). Take case (3): a direct clash with `A` and a joint clash with `P`+`R`, all in the same file. Leaving out `A` still conflicts in that file, and so does leaving out `P` or `R`, so the path set never changes and nothing is named. Case (3) expects `A`, `P` and `R`. The brief must state the comparison measure, for example conflict-hunk count or clean versus not clean per hunk, or the criterion cannot be falsified and the builder will make up a metric.
- [x] **The leave-one-out rule ignores line bundles that stack on other line bundles.** Removing bundle `X` from "the line" does not remove `X`'s commits if a later line bundle was cut from `X`'s branch: merging that bundle brings `X` back. In that case leave-one-out cannot separate `X`. `_partners` handles this through `under`/`_built_on` and `_merge_over` (`integrate.py:1340-1358`, `:1363`). The brief limits the "own change only" rule to the *head* and puts `_partners` out of scope, but never says how a stacked line bundle is left out. Add a case, or state the limitation (it would fall through to `STOPPING`).
- [x] **The cost comment the brief prescribes is probably wrong.** The brief says "O(n) trials per round". Each leave-one-out trial re-merges up to n−1 line bundles plus the head, so a round costs O(n²) merges. The acceptance trial and the case (4) search for several sets add more. Either correct the comment the builder is told to write, or say that "trial" means one multi-merge `_trial` call.
- [x] **Scope depends on what happens to land first.** "If child-3 is already on the line, reuse its own-change helper" and "flow.py: only the announce wording … if child-1's line does not already cover it" make the patch differ depending on order. With `Conflicts with: 749` and no ordering, Do may build a second own-change helper that #749 later duplicates or clashes with. Pin the order, or say which bundle owns the own-change helper.
- [x] **Case (5)'s "base-taken-in" clash is not defined for this cross-wave path.** On the target, `_held_by` returns None when the head merges onto `pre`+`kept`, which is the base-taken-in case (`integrate.py:1271-1274`). The new fallback runs after child-1's rule (e). The brief should name the concrete trial outcome that leaves "no set of line bundles explains it", for example that the acceptance check "base + line without the set + head merges cleanly" fails for every candidate set. Otherwise case (5) depends on how the leave-one-out search happens to end.
- [x] T5 Judgment — Confirm the affected-path prior-art search covers merged history and closed/rejected work before accepting this approach — the provided target has only one synthetic commit, no remote, and no such search evidence; review-prior-art.log:1, brief.md:18.

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
- Plan advisory: 7 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
