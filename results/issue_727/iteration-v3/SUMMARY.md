# Result — issue 727 / flow-in-batch-dependency-scoped-bases

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: 
- Success criterion: Real-git tests driving `flow._drive_and_act` through real folds on the `StackFoldGit` fixture, with build and sign-off stubbed and `_publish_bundle` cutting each PR branch from the recorded stack-base tip, as `template/tests/test_flow_same_wave_conflict.py:131` does:
  (1) **The #630 case.** `A`, `Z` (wave 0, unrelated, two commits each), `B` (`Depends on: A`). Every commit of `origin/main..fix/A` is on `fix/B`; no commit of `origin/main..fix/Z` is. All COMPLETE.
  (2) **Transitive.** `C` (`Depends on: B`): `fix/C` has `fix/A` and `fix/B`, not `fix/Z`.
  (3) **Conflict partner.** `E` (`Conflicts with: A`): `fix/E` has `fix/A`, not `fix/Z`.
  (4) **In-batch `Depends on (merged)`.** `G` (`Depends on (merged): A`): `fix/G` has `fix/A`, not `fix/Z`.
  (5) **Empty closure → real base.** `H` whose only edge is to an in-batch `N` that closed with no patch: stack base cleared; `fix/H` has neither `fix/A` nor `fix/Z`.
  (6) **Seam fallback is unchanged.** A bundle whose closure reaches a bundle this run does not drive (a carried bundle, or a finished patchless bundle on resume), an `Onto branch` member, or a legacy `Stacks on` bundle, or that declares `Conflicts with` a carried bundle, gets exactly the line base it gets on `fcae4aa` and is built (not stopped). One test per seam: carried `Depends on`, carried `Conflicts with`, `Onto branch`, legacy `Stacks on`.
  (6b) **Closure walks only through bundles this run built.** `E` (`Conflicts with: A`), `A` (`Depends on: Q`), and `A` ends DISCONTINUED: `fix/E` has no commit of `fix/Q` (E declared no edge to Q).
  (7) **Rewrite message.** `A` in wave 0; `B` and `C` (both `Depends on: A`) in wave 1, each on its own base; `S` (a seam-fallback bundle per (6), on the line) also in wave 1. `fix/A` is forced back to an older commit after both bases and the line took its newer head. The #633 (next fold) and #695 (end of run) reports name each of `issue_B` and `issue_C`, each one's own base branch (`integrate.bundle_base_branch`) and the head that base took, and tell the human to rebuild that bundle's PR; the line itself is still reported, with today's line-PR remedy naming the PRs cut from the line (`S`). For a per-bundle base the report does not say `the commit the line took` or `every PR this run cut from` (today's wording, `integrate.py:1131`, `flow.py:2713-2731`). The same split applies to the `unchecked` report (fetch failure, `flow.py:2722-2731`): one test where the check cannot fetch and `B`'s base is named with its own head.
  (8) Existing suites stay green; assertions restated only in terms of content, never weaker; `build-notes.md` lists each restated assertion with before and after. `_line_lacks_merge` is untouched. In its suite `test_flow_merged_prereq_on_line.py` only the `_built_on_line` helper (`:191-198`, which asserts `base == self.line`) may be restated: there `D` also `Depends on: W`, so after this change `D` is built on its own base holding `W`, and the helper asserts that plus the content checks its callers make. The hold tests (`:202`, `:212`, `:241`, `:249`, the held parts of `:293`) and the carried case `:269` (seam fallback, still the line) stay as they are.
- Repo + branch target: eduralph/pdca-harness @ main (PRs target `main`). Base: the run's line `pdca-integration/main-r547f8028520f` at `fcae4aa` (`489e5fb` + #723; #723's PR #726 is open, not merged). Anchors are on `fcae4aa` (re-checked at this revision with `git show fcae4aa:<file>`: `build_bundle_base` `integrate.py:716`, `bundle_base_branch` `:145`, rewrite wording `:1131`, `_point_at_integration` `flow.py:890` / `:2549`, `rewritten_carried` call `:2718`). `main` does not have #723's functions, so Do and the gate must use the line, not `main`. PR note for the human: until #726 merges, this PR's diff against `main` also shows #723's change (a declared edge, so allowed); merge #726 first.
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

Review #727: prevent unrelated earlier-wave work from entering an in-batch bundle’s PR, and report rewrites against the heads its own base actually took.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The declared-edge invariant, empty closure, seam exceptions and rewrite remedies are falsifiable through real-git ancestry checks; brief.md:3 and brief.md:18, grounded by template/tests/test_flow_dependency_scoped_bases.py:248. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing the two production files reproduced the unrelated Z commits on B and 16 assertion failures across 20 tests, with no import errors; template/tests/test_flow_dependency_scoped_bases.py:256; review-red.log:75. |
| C3 Change | PASS | The patch stays within base selection, rewrite accounting and corresponding tests; the protected merged-prerequisite hold function is AST-identical to the base, and the original undeclared-overlap topology remains covered separately from the added declared-edge case; template/src/pdca_harness/flow.py:850; template/tests/test_flow_reissue_after_conflict_hold.py:245. |
| C4 Verification (red→green) | PASS | The same 20 regression tests passed with the fix and failed 16 assertions without it; after stash restoration the full 2,576-test driver suite passed, confirming the fix was restored; template/tests/test_flow_dependency_scoped_bases.py:248; review-green.log:23; review-driver-suite.log:1817. |
| C5 Causal adequacy | PASS | The shared-base cause is removed for the agreed scope; real-git tests retain inherited work through patchless nodes and detect unrelated rewrites after a base-build clash, and removing the conflict-order guard makes its regression fail; template/src/pdca_harness/flow.py:956; template/tests/test_flow_dependency_scoped_bases.py:274 and :506; review-conflict-guard.log. |
| T1 Structure | PASS | Base construction reuses the existing locked git integration path, with closure selection and PR-head accounting kept in driver helpers; no extra service or runtime dependency is introduced; template/src/pdca_harness/flow.py:969; template/src/pdca_harness/integrate.py:732. |
| T2 Shape | PASS | Independent whitespace checking and docs lint passed; rendering produced 22 pages with a clean internal-link audit, consistent with both frozen docs gates; .github/workflows/docs-check.yml:35; review-docs-system.log:2; gate-logs/host-ci-docs.log:11. |
| T3 Runtime | PASS | Independent driver suite passed 2,576 tests (two skips); Copier-interpreter root suite passed 19 tests, with prior-release update checks skipped because this snapshot has no release tags; the frozen gate actually ran and passed all 24 root tests; gate-logs/T3-suite.log:54 and :1874; tests/test_update_compat.py:244. |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the gate ran and deferred its substantive audit to the mandatory publish-time rerun; gate-logs/T4-contribution.log:8. |
| T5 Judgment | NEEDS-HUMAN | Confirm affected-path prior art against merged history and closed/rejected work, and confirm prerequisite PR #726 lands first — this snapshot has only one local base commit and no remotes or rejection records, while the brief describes #726 as open; review-prior-art.log:1; brief.md:13 and :24. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Accept the limited in-batch rollout and retained seam fallback — carried/legacy/Onto closures still use the shared line and can inherit unrelated work, while resume and merged-hold follow-ups remain deferred; template/src/pdca_harness/flow.py:1009; brief.md:19. |

Source citations are relative to `/tmp/pdca-review-82t8jddm/target`; brief and evidence citations are relative to the review sandbox. The target’s sole commit records the expected pre-fix `fcae4aa` base. Reverse application of the complete patch passes its check; there is no stale-target caveat. No builder rationale was read, and no production or test source was edited by the reviewer.

Independent verification used `PYTHONDONTWRITEBYTECODE=1` and retained the new regression tests while stashing only `flow.py` and `integrate.py`. `review-green.log` records all 20 cases passing; `review-red.log` records 16 assertion failures, including the original commit leak; production changes were restored with `git stash pop`. The restored tree then passed `PYTHONPATH=src python3 -m unittest discover -s tests` (2,576 tests, two skips). The import scanner independently confirmed that the added test imports `pdca_harness`; inspection also confirmed that the fixture calls production `_drive_and_act`, `fold` and `build_bundle_base` with real local git repositories. The conflict-order mutation was applied in memory only, and its test rejected the mutation.

Docs lint and `render_site.py --check` passed independently. The default Python could not import Copier, so root verification was rerun with the installed Copier interpreter: 19 tests passed, and the update-compatibility class skipped for absent release tags. This is a snapshot limitation, not a patch defect; `gate-logs/T3-suite.log:38` through its 24-test result show the frozen gate exercised that class successfully. The initial renderer attempt under that interpreter lacked `markdown_it`; the subsequent default-Python renderer run passed. All six frozen gate logs were read; no row lacks its evidence, and the instance-scoped wrapper paths were not treated as target files.

The prior-art investigation ran `git log --all -- <path>` for every affected file and inspected available remotes. It found only the synthetic base commit, no history for the new test, and no remotes; the bundle contains no closed/rejected-work records beyond the brief’s summary. `review-prior-art.log` preserves those results. Human sign-off must therefore establish the path-scoped prior-art decision and prerequisite merge ordering, rather than treating the brief’s references as independently confirmed. The available INTEGRATION template leaves project-specific human-only items as TODO (template/docs/INTEGRATION.md.jinja:81); the target AGENTS.md:11 reserves PR ready-marking and merging for the maintainer.

No builder-fixable defect was established in this review. The two NEEDS-HUMAN rows are advisory decisions, and T4 remains deferred to publish.
<!-- pdca:leaf-complete -->

### Advisory — adversary

# Adversarial review — issue_727 (dependency-scoped bases)

## Evidence: re-run, holds

- Re-ran the proof myself on copies of `$PDCA_TARGET`. With the fix, `template/tests/test_flow_dependency_scoped_bases.py` gives 20/20 green. With `flow.py` and `integrate.py` reverted to `fcae4aa`, 16/20 go red. The 4 that stay green are the seam tests (criterion 6: carried `Depends on`, carried `Conflicts with`, `Onto branch`, `Stacks on`), which are meant to match `fcae4aa` behavior. So red→green is real and not a tautology. The tests drive the real `flow._drive_and_act` with real git folds and real `integrate.build_bundle_base`. The `_publish_bundle` stub cuts from the recorded `stack-base-tip`, which is what production publish does (`template/src/pdca_harness/publish.py:261-265`). The bundle's 9 suites (277 tests) are green with the fix.
- Mutation check on the closure walk. Each of these deletions turns at least one test red: the wave guard (`template/src/pdca_harness/flow.py:956`, the iteration-1 gap, now pinned by `test_a_members_partner_built_after_it_is_not_on_the_base`), the `finished` seam (`flow.py:951`), the legacy seam (`flow.py:945`), the built-on-the-line seam (`flow.py:964`) and `stop_named` (`flow.py:2707`). Both iteration-2 findings (closure through a patchless partner; end check left on after a non-rewrite base failure) have tests that fail when the fix is reverted.

## Refutations

- NEEDS-HUMAN [human] — **A cross-wave overlap nobody declared now stops a run that used to finish.** Concrete case: `A` (wave 0) adds `a.txt`; `Q` (wave 0) is unrelated; `Y` `Depends on: Q` and writes its own `a.txt`; `W` `Depends on: Y`. On `fcae4aa`, all four end COMPLETE, because `Y` was cut from the line holding `A`, so its edit sat on top of `A`'s. With this patch, `_closure_members` (`template/src/pdca_harness/flow.py:913-966`) gives `Y` a base holding only `Q`. The fold after wave 1 then fails at `template/src/pdca_harness/integrate.py:1325`: "wave 1 did not integrate (… an undeclared cross-wave overlap …); STOPPING". `W` is left PLANNED. I reproduced this on both trees with a real-git probe built on the bundle's own fixture. The stop is arguably more honest, since `Y`'s PR would conflict with `A`'s at merge time anyway. But it is a behavior change no criterion, test or brief line states. The brief only defers "holds for … cross-wave overlaps" to #725. The human should decide whether #727 may merge before #725, and the PR description should state this change.
- NEEDS-HUMAN [impl] — **The two `pushed` filters in `_heads_taken` (`template/src/pdca_harness/flow.py:1034` and `:1036`) have no test, and removing them changes the outcome.** With both filters removed, all 277 tests in the bundle's suites still pass. Concrete case that tells them apart: `A` (w0); `B` `Depends on: A` (w1, own base); `Q`→`Y`→`W` (a chain that forces a fold after wave 1). After the wave-0 fold, `fix/A` fast-forwards to `a2`, which `B`'s base takes. `B`'s publish then fails, so `B` has no PR. While `B` builds, `fix/A` goes back to `a1`. With the filters: the run finishes, holds `{B: unpushed}`, and `W` is COMPLETE. Without them: "wave 1 did not integrate (… issue_B's PR holds commits …)" stops the run over a PR that does not exist, and `W` stays PLANNED. Add this case as a test. In the same pass, the `Onto branch` member seam at `flow.py:962` can also be deleted with every test still green. In practice the brief check at `flow.py:945` hides it. It is reachable only when a member's `publish.json` is `"stacked"` and its brief no longer says `Onto branch`, and then `_member_cut_point` (`integrate.py:922-925`) would stop the run instead of falling back to the line. Either pin it with a test or drop it.

## Claims checked and not refuted

- I tried to break the closure through: a `Conflicts with` partner built after the member (guarded, with a test); a walk through a DISCONTINUED partner (6b, with a test); a patchless node built on the line (the walk hits the same seam reason again); members on another target (left out by `on_target`, the same as the per-target line); held prerequisites (`_runnable` holds the dependent before `_bundle_bases` runs); and `wave_of` key misses (it is filled together with `accepted`, `flow.py:2765-2766`). I could not find an input that gives a wrong base.
- I tried to break the #633/#695 wording against criterion (7): the base lines never use "the commit the line took" or "every PR this run cut from" (tests count them). The line keeps its line-PR remedy naming `issue_S`. The `unchecked` path splits line items from base items (`flow.py:2896-2925`). I could not find a wrong message.
- `check-gates.json` makes no claim I think is unwarranted. C4 and T3 match what I re-ran. C5's "imports the production package" is a weak check, but I confirmed separately that the test runs the production path.

## Notes (not NEEDS-HUMAN; scoped elsewhere by the brief)

- The patch makes two comments false: the module docstring at `template/src/pdca_harness/integrate.py:20-30` and the comment at `template/src/pdca_harness/publish.py:266-277` still say a later wave's PR "carries every earlier-wave branch on the line". The brief gives stack-rule docs to #725.
- The #655 hold message (`template/src/pdca_harness/flow.py:818-825`, "the line {d.name} would build on") now also fires for a bundle that would be built on a base of its own. That base starts from a freshly fetched base branch, which already has the merge, so the hold is stricter than it needs to be and its message is now wrong. The brief keeps these hold tests as they are and gives this to #729.

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — issue #727 (dependency-scoped bases)

Lens: bugs the patch adds, plus reuse / simpler / cheaper code. Grounded on the patched
tree at `$PDCA_TARGET`. Gates: C4 red→green, T3 suite OK (2576 tests), docs clean.

I found no correctness bug that needs a human or another build round. The closure walk
(`_closure_members`), base selection (`_bundle_bases`), the head bookkeeping
(`bases_took` / `line_cut` → `_heads_taken`) and the split rewrite / unchecked messages
check out against the brief. The guard flagged in round 1 (a partner built after the
member it is reached from) now has a test aimed at it
(`template/tests/test_flow_dependency_scoped_bases.py:303`). I read it but did not
re-run it with the guard deleted, so I have not confirmed it goes red without the guard. The round-2 points are
handled too: a patchless prerequisite is walked through
(`template/tests/test_flow_dependency_scoped_bases.py:274`), and a base build that stops
for a clash leaves the end-of-run check on
(`template/tests/test_flow_dependency_scoped_bases.py:506`). Small notes, none blocking:

- `template/src/pdca_harness/flow.py:1003` — the base-build error is renamed by assigning
  `exc.args` in place. That keeps the `_Rewritten` type, which the caller needs for
  `stop_named` (`flow.py:2706`). But `exc.cause` still holds the old text without the
  "could not build X's own base" prefix. Nothing reads `cause` on this path today
  (`flow.py:2704` prints `str(exc)`), so nothing breaks now. It is a trap if a later
  change reports `cause`. Optional fix: set `exc.cause` too, or add an `owner` field to
  the error.
- `template/src/pdca_harness/flow.py:996-1006` — every base in the wave is built and
  pushed before any bundle is pointed at one. So when a later base fails, the bases
  already pushed stay on origin and are not recorded in `bases_took`. No bundle is built
  on them (the loop breaks before `_drive_wave`), so no PR holds them and the end-of-run
  check does not need them. The only cost is leftover `pdca-integration/*` branches, and
  the brief puts per-bundle base cleanup out of scope. Recorded for context; nothing to do.
- `template/src/pdca_harness/integrate.py:1123-1125` — the in-run fold now also refuses
  a branch when only a head that some bundle's own base took is gone, even if the line's
  head is still on the branch. Example: a base took a fast-forward of the line's head,
  then the branch was rewritten back. That one PR is affected, but the whole run stops at
  the next fold. The brief asks for the #633 check to get each base's head and name it,
  so this is in scope. Calling it out because it adds a new reason a run can stop.
- Reuse nit: `template/src/pdca_harness/integrate.py:1148` (`_rewrite_stop`) and
  `template/src/pdca_harness/integrate.py:1287` (`_late_line_rewrite`) each build their
  own copy of the sentence "every PR this run cut from <line> after it took <head>
  (<owners>)". A small shared helper would keep the in-run and end-of-run wording from
  drifting apart. This is cosmetic.
- Efficiency: `_heads_taken` (`template/src/pdca_harness/flow.py:1030`) looks up the
  target of every accepted bundle each time it is called: once per wave, once per fold,
  and once at the end. Each lookup reads a brief file. That is cheap at batch sizes, so
  no change needed.

No NEEDS-HUMAN items.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T5 Judgment — Confirm affected-path prior art against merged history and closed/rejected work, and confirm prerequisite PR #726 lands first — this snapshot has only one local base commit and no remotes or rejection records, while the brief describes #726 as open; review-prior-art.log:1; brief.md:13 and :24.
- [ ] Validation — fitness-to-purpose — Accept the limited in-batch rollout and retained seam fallback — carried/legacy/Onto closures still use the shared line and can inherit unrelated work, while resume and merged-hold follow-ups remain deferred; template/src/pdca_harness/flow.py:1009; brief.md:19.
- [ ] **A cross-wave overlap nobody declared now stops a run that used to finish.** Concrete case: `A` (wave 0) adds `a.txt`; `Q` (wave 0) is unrelated; `Y` `Depends on: Q` and writes its own `a.txt`; `W` `Depends on: Y`. On `fcae4aa`, all four end COMPLETE, because `Y` was cut from the line holding `A`, so its edit sat on top of `A`'s. With this patch, `_closure_members` (`template/src/pdca_harness/flow.py:913-966`) gives `Y` a base holding only `Q`. The fold after wave 1 then fails at `template/src/pdca_harness/integrate.py:1325`: "wave 1 did not integrate (… an undeclared cross-wave overlap …); STOPPING". `W` is left PLANNED. I reproduced this on both trees with a real-git probe built on the bundle's own fixture. The stop is arguably more honest, since `Y`'s PR would conflict with `A`'s at merge time anyway. But it is a behavior change no criterion, test or brief line states. The brief only defers "holds for … cross-wave overlaps" to #725. The human should decide whether #727 may merge before #725, and the PR description should state this change.
- [ ] **The two `pushed` filters in `_heads_taken` (`template/src/pdca_harness/flow.py:1034` and `:1036`) have no test, and removing them changes the outcome.** With both filters removed, all 277 tests in the bundle's suites still pass. Concrete case that tells them apart: `A` (w0); `B` `Depends on: A` (w1, own base); `Q`→`Y`→`W` (a chain that forces a fold after wave 1). After the wave-0 fold, `fix/A` fast-forwards to `a2`, which `B`'s base takes. `B`'s publish then fails, so `B` has no PR. While `B` builds, `fix/A` goes back to `a1`. With the filters: the run finishes, holds `{B: unpushed}`, and `W` is COMPLETE. Without them: "wave 1 did not integrate (… issue_B's PR holds commits …)" stops the run over a PR that does not exist, and `W` stays PLANNED. Add this case as a test. In the same pass, the `Onto branch` member seam at `flow.py:962` can also be deleted with every test still green. In practice the brief check at `flow.py:945` hides it. It is reachable only when a member's `publish.json` is `"stacked"` and its brief no longer says `Onto branch`, and then `_member_cut_point` (`integrate.py:922-925`) would stop the run instead of falling back to the line. Either pin it with a test or drop it.
- [ ] **The tracker record is missing, so the problem statement could not be checked against the thread.** My sandbox holds only `brief.md` and `dependency-state.json`. There is no `notes.json` and no `sources/`. The brief's root cause and invariant cite #463, #630's finding (`results/issue_463/notes.json`), `09-parallel-lanes.md:59-61`, and the rejected attempts in `results/issue_724/iteration-v1/` and `iteration-v2/`. I could read none of them. So I could not test the brief for an ignored maintainer constraint or a failed prior attempt. Someone at sign-off needs to read the thread.
- [ ] **The brief points Do at the #724 attempts but never says why they were rejected.** Prior-art line: "parent #724's rejected attempts in `results/issue_724/iteration-v1/`, `iteration-v2/` (their in-batch closure code and tests are the starting point)". The brief doesn't record the rejection reasons. So Do is told to start from code that was turned down twice, with nothing to stop it repeating the faults that sank it. The brief should list the rejection findings and show which of criteria (1)-(8) answers each one.
- [ ] **The target checkout is not at the brief's anchor commit, so several cited lines cannot be checked.** The brief says "Anchors are on `fcae4aa`" (`489e5fb` + #723). `$PDCA_TARGET` has no `build_bundle_base` or `bundle_base_branch` anywhere (Grep over the whole tree finds nothing). Its `integrate.py` has `_carried_tips` at :697 and `rewritten_carried` at :755, and today's wording "every PR this run cut from" sits at `integrate.py:803`, not :1131. So `integrate.py:716` and `integrate.py:1131` can't be grounded here. The `flow.py` anchors do match this checkout: `_point_at_integration` at `flow.py:890`, its call at `:2549`, and the docstring at `:2713`. Either the driver resolved the wrong base for this bundle, or #723 is only on the run's line. In either case Do needs the line checked out at `fcae4aa`. A worktree on `main` lacks the function this fix calls.
- [ ] **"no PR is cut from the line any more" is false under the brief's own scope.** Criterion (6) and the Out-of-scope list keep the line base for every bundle whose closure reaches a carried bundle, an `Onto branch` member or a legacy `Stacks on`. That includes this bundle itself, which `Depends on: 723`, a carried prerequisite. Those PRs are still cut from the line. Yet the Defect line says the #633/#695 messages "must name that base and that bundle's PR, since no PR is cut from the line any more". Criterion (7) also forbids the phrase "every PR this run cut from". As written, Do may delete the line-PR remedy for bundles that still sit on the line. Criterion (7) should be split:
- [ ] **Criterion (7) tests only one dependent.** It checks one dependent (`B`) of one rewritten branch (`A`). With per-bundle bases, one rewritten `fix/A` can sit under several bases that each took a different head of A. Examples: `B` and `C` both `Depends on: A`, or a transitive `C` as in (2). The brief doesn't say whether the report names every such bundle. It also doesn't say whether the line itself (which still folds A) is still reported. One test with two dependents of A, both named, would make the criterion falsifiable for the general case.
- [ ] **Scope is two coupled changes, and only one of them is visibly bounded.** The first change, choosing each bundle's base, is well bounded by (1)-(6). The second reworks the rewrite detection behind #633/#695: today `rewritten_carried(cfg, accepted, carried, batch)` (`flow.py:2718`) is keyed on what a fold carried onto the line, and it would now have to be fed "the head that bundle's own base took". That changes what the check is fed, not just its wording, but Scope frames it as "`integrate.py` rewrite-message wording". The unchecked-branch text at `flow.py:2725-2731` ("rebuild on that branch every PR this run cut from the line") is the same kind of wording but isn't listed. The brief should state outright that the check's inputs change, and cover the `unchecked` path (fetch failure) for a per-bundle base too.
- [ ] **The target and dependency resolve, but the PR shape repeats the defect being fixed.** `dependency-state.json` lists `723` as `Depends on`, exists, COMPLETE, so that id resolves. But the brief says #723's PR #726 is open, not merged, while this bundle's PR targets `main`. Until #726 merges, this PR's branch will carry #723's work: that is the "PR carries another bundle's work" pattern the brief sets out to fix, here through a declared edge, so it is allowed. The brief should tell the human that #726 must merge first, or that this PR will show #723's diff.
- [ ] T5 Judgment — Confirm merged and closed/rejected prior art by both affected production paths — the target contains only one synthetic base commit, no remotes, and no #724 iteration archives, so the brief’s prior-art account cannot be independently settled (brief.md:24; template/src/pdca_harness/flow.py:913; template/src/pdca_harness/integrate.py:1198).
- [ ] Per-bundle bases start from a freshly fetched `origin/main`, so each dependent's branch brings mid-run main commits into the line. Before this change, the line never took those in (flow.py:738 states that the line does not follow the base). `build_bundle_base` fetches the base fresh (`integrate.py:829`) and starts the branch from it (`integrate.py:849`).
- [ ] Several restated tests change test inputs or test setup, not just assertions. The brief lists exactly this as a reason v1/v2 were rejected, and (8) requires each change to be in `build-notes.md`, which I cannot see.
- [ ] T5 Judgment — Confirm prior art by both affected production paths against merged history and closed/rejected work — the disposable repository exposes only one synthetic base commit, and the cited #724 rejection artifacts are outside this input bundle (template/src/pdca_harness/flow.py:913; template/src/pdca_harness/integrate.py:724; brief.md:24).
- [ ] If the base moves during a run, the whole run can now stop where `fcae4aa` finished it. A bundle's own base starts from `<base_remote>/<base>` as fetched at that moment (`integrate.py:841`), but the line never follows the base (#655).
- [ ] `template/src/pdca_harness/flow.py:2708`: if a base build fails (including on a rewrite it caught), the code sets `line_stopped = True`, which turns off the #695 end-of-run check (`flow.py:2855`). Bases and line PRs from earlier waves are then not checked again at the end, even though some may hold heads a branch has since lost. A failed fold already behaves this way, and the brief puts holds for base-build failures under #725, so this is consistent with today's behavior. Round 1 raised it, and it is still open. Decide whether to accept it here or track it under #725.
- [ ] `template/src/pdca_harness/integrate.py:1117` (reached through `_carried_tips`, `integrate.py:519`): an in-run fold now stops the whole run when any taker's head is lost, including when only a bundle's own base lost it and the line's head is still on the branch. Example: a base takes `fix/A` at H2, a fast-forward past the line's H1, and then `fix/A` is pushed back to H1. The line is fine, and the next fold would merge H1 cleanly. The only damage is the PR built on that base, yet the run stops with a "re-issue the run" remedy. The brief's (7) asks the #633 report to *name* each base. It does not say a base-only loss should stop the line. Confirm this is the behavior you want.

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
- Iteration delta (if iterating): Auto-iterate (round 3): rebuilding for the implementation-level findings — **The two `pushed` filters in `_heads_taken` (`template/src/pdca_harness/flow.py:1034` and `:1036`) have no test, and removing them changes the outcome.** With both filters removed, all 277 tests in the bundle's suites still pass. Concrete case that tells them apart: `A` (w0); `B` `Depends on: A` (w1, own base); `Q`→`Y`→`W` (a chain that forces a fold after wave 1). After the wave-0 fold, `fix/A` fast-forwards to `a2`, which `B`'s base takes. `B`'s publish then fails, so `B` has no PR. While `B` builds, `fix/A` goes back to `a1`. With the filters: the run finishes, holds `{B: unpushed}`, and `W` is COMPLETE. Without them: "wave 1 did not integrate (… issue_B's PR holds commits …)" stops the run over a PR that does not exist, and `W` stays PLANNED. Add this case as a test. In the same pass, the `Onto branch` member seam at `flow.py:962` can also be deleted with every test still green. In practice the brief check at `flow.py:945` hides it. It is reachable only when a member's `publish.json` is `"stacked"` and its brief no longer says `Onto branch`, and then `_member_cut_point` (`integrate.py:922-925`) would stop the run instead of falling back to the line. Either pin it with a test or drop it.. Deferred, not addressed here: 9 finding(s) that need human judgment, held in deferred-findings.json for the human at handover — not build work
- By / date: auto-iterate / 2026-10-15

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 7 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
