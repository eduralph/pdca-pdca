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

Review #727: give in-batch stack-mode bundles dependency-scoped bases and report rewritten prerequisite heads against each affected base and PR.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The required isolation, seam fallback, rewrite remedies, and exclusions are falsifiable and bounded (brief.md:4, brief.md:9, brief.md:18). |
| C2 Reproduction (red pre-fix) | PASS | With only the two production files stashed, the unchanged new suite runs 19 tests and fails 15, including B carrying unrelated Z (review-red.log:43, review-red.log:288; template/tests/test_flow_dependency_scoped_bases.py:256). |
| C3 Change | PASS | Source changes stay within base selection and rewrite accounting; `_line_lacks_merge` is AST-identical to the base, and the merged-prerequisite suite changes only its permitted helper (template/src/pdca_harness/flow.py:850; template/tests/test_flow_merged_prereq_on_line.py:191). |
| C4 Verification (red→green) | PASS | After stash-pop, all 2,575 driver tests pass, including the 19-test suite that failed pre-fix; the separate 58-test targeted run also passes (review-red.log:290; review-driver-suite.log:1817; target/review-green.log:3). |
| C5 Causal adequacy | NEEDS-HUMAN [impl] | Preserve the declared closure through a completed patchless prerequisite — N conflicts with A and H depends on N, yet H drops A although N was built on A; all four bundles become COMPLETE, violating the accepted-work invariant (template/src/pdca_harness/flow.py:953, template/src/pdca_harness/flow.py:964; brief.md:18; review-patchless-conflict.log:1). |
| T1 Structure | PASS | Base construction reuses the existing integration lock, fetched worktree, and merge validation; head ownership has a shared representation across both rewrite checks (template/src/pdca_harness/integrate.py:818, template/src/pdca_harness/integrate.py:1040). |
| T2 Shape | PASS | Independent docs lint and rendering audit pass for all 22 pages, and `git diff --check` passes; frozen host-parity evidence agrees (review-docs.log:1; gate-logs/host-ci-docs.log:10). |
| T3 Runtime | PASS | Independent driver run passes 2,575 tests with two skips; frozen root evidence shows all 24 render/update tests passed, while this interpreter cannot import copier (review-driver-suite.log:1817; gate-logs/T3-suite.log:39; review-root-suite.log:6). |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the deferred row explicitly requires the substantive audit at publish (gate-logs/T4-contribution.log:10). |
| T5 Judgment | NEEDS-HUMAN | Confirm prior art by both affected production paths against merged history and closed/rejected work — the disposable repository exposes only one synthetic base commit, and the cited #724 rejection artifacts are outside this input bundle (template/src/pdca_harness/flow.py:913; template/src/pdca_harness/integrate.py:724; brief.md:24). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the scoped isolation and retained line-based seam behavior satisfy the intended workflow, and honor the prerequisite merge order (#726 first) — green offline checks do not settle that product acceptance (brief.md:9, brief.md:13; template/src/pdca_harness/flow.py:1014). |

All source citations above resolve within `$PDCA_TARGET` (`target/`). The supplied patch reverse-checks cleanly against that tree; there is no target-state mismatch. The production stash was popped successfully, and no reviewed source was edited.

The C5 finding is independently exercised through real git and production `flow._drive_and_act`, using the brief's prescribed fixture and build/publish stubs. A and unrelated Z publish first; N declares `Conflicts with: A` and completes without a patch; H declares `Depends on: N`. The observed result is `A=N=H=Z=COMPLETE`, A is an ancestor of N's recorded base, and A is not an ancestor of `fix/H` (`review-patchless-conflict.log:1`). N is completed in this run, so neither the discontinued-node exclusion nor the resumed-patchless seam applies. At `flow.py:964`, visiting N with `every=False` removes its conflict edges at `flow.py:953`. The existing transparent-patchless test covers only `Depends on` (`template/tests/test_flow_dependency_scoped_bases.py:284`); add the conflict-edge counterpart while retaining the empty-closure and discontinued-node cases.

Reproduce from this review directory:

```bash
TMPDIR="$PWD/review-tmp" PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=target/template/src:target/template \
  python3 review-patchless-conflict.py
```

The earlier iteration's concrete concerns have regression coverage now: the original undeclared-overlap topology remains separate from its declared-edge variant (`template/tests/test_flow_reissue_after_conflict_hold.py:245`); older line-cut heads and a later base detecting a rewrite have production-flow tests (`template/tests/test_flow_dependency_scoped_bases.py:536`, `template/tests/test_flow_dependency_scoped_bases.py:492`). Removing the conflict-wave guard in memory makes its new regression fail on unwanted E commits, confirming that test detects the previously untested condition (`review-guard-mutation.log`; `template/tests/test_flow_dependency_scoped_bases.py:307`). This mutation did not alter source files.

All six frozen gate logs were inspected. The instance-scoped wrappers are not present here; their absence is expected. The production-import scanner's captured output establishes an import of `pdca_harness`, not causal sufficiency (`gate-logs/C5-prod-path.log:10`); the real-git reruns supply the latter evidence and expose the C5 gap. Local root-suite execution returns 77 because copier is not importable; this is a reviewer-host limitation, not a patch failure or an undischarged gate dependency: the frozen root log explicitly records successful render and update cases (`gate-logs/T3-suite.log:39`, `gate-logs/T3-suite.log:54`). No extra project human-only items are enumerated in the available integration template (`template/docs/INTEGRATION.md.jinja:80`).

Prior-art investigation ran `git log --all -- template/src/pdca_harness/flow.py template/src/pdca_harness/integrate.py`; its sole result was `ad488e2 pre-fix base fcae4aaee0233103ea0dac73c66c8811c713850c`. The brief summarizes prior rejected approaches, but does not supply their actual corpus. That limitation remains a human judgment under T5.

<!-- pdca:leaf-complete -->

### Advisory — adversary

# Adversarial review: issue_727 (dependency-scoped bases)

Verdict: the red→green evidence holds up, and I could not refute it. For the inputs the brief lists, the fix does what criteria (1)–(7) ask. I found two concrete inputs where a run now ends worse than on `fcae4aa`. One is a gap the builder can fix. The other is a scope call for the human.

## The evidence (attempted, could not refute)

- I re-ran C4 myself on sandbox copies of the target. For the pre-fix copy I took `flow.py` and `integrate.py` from HEAD `fcae4aa`. `tests.test_flow_dependency_scoped_bases` fails 15 of 19 before the fix and passes 19 of 19 after. The 4 that pass before the fix are the four seam tests for (6) (`template/tests/test_flow_dependency_scoped_bases.py:364-423`), which by design assert that behavior is unchanged from `fcae4aa`. The others fail for the right reason. For example, (1) fails at `:266` because `fix/B` holds Z's commits.
- The test runs the production code. `flow._drive_and_act`, `integrate.fold` and `integrate.build_bundle_base` are all real and run against a real git origin. Only `_drive_wave`, `_publish_bundle`, `draft_texts` and `gh` are stubbed. The `_publish_bundle` stub (`:130-159`) cuts the PR branch from the same commit real publish uses (the recorded stack-base tip, `template/src/pdca_harness/publish.py:261-263`). It also records the same `mode` (`publish.py:429`). So it does not hide a difference that `_member_cut_point` would see (`integrate.py:928`).
- Mutation check: I deleted each of the following, one at a time, and each deletion made at least one test fail:
  - the wave guard that drops a member's partner built after it (`flow.py:960`). Last round said nothing tested it. `test_a_members_partner_built_after_it_is_not_on_the_base` now covers it.
  - the finished-bundle seam (`flow.py:955`)
  - the legacy `Stacks on` / `Onto branch` seam (`flow.py:948`)
  - the list of PRs cut from the line (`flow.py:1041`)
  - `bases` in each of the three rewrite checks: `rewritten_carried`, `build_bundle_base` (`integrate.py:827`), and the fold's `_carried_tips` (`integrate.py:519`)
- I tried more closure inputs, and all came out right:
  - Diamond: `D` (`Depends on: B, C`), where B and C both depend on A, and Z is unrelated. D's base holds A, B and C, and no Z.
  - A member's earlier-wave partner: `Y` (`Conflicts with: A`), `D` (`Depends on: Y`). D's base holds A and Y, and no Z.
  - `main` gaining an unrelated commit mid-run is taken into the base without a refusal.

## Findings

- NEEDS-HUMAN [impl] — When a base build stops the run for any reason other than a rewrite, the end-of-run check (#695) is turned off. A rewrite of a branch that is not one of that base's members then goes unreported.
  - **Code path:** the `_bundle_bases` error sets `line_stopped = True` (`template/src/pdca_harness/flow.py:2708`), and that skips `_report_late_rewrites` (`flow.py:2855`). But `build_bundle_base` only checks its own members' heads (`integrate.py:828-833`). A fold is different: its check covers every carried branch before any merge can fail (`integrate.py:519`).
  - **Concrete case (run on both trees):** wave 0 has `A` and `Z` (Z has two commits). Wave 1 has `S` (`Stacks on: Z`, a seam, so built on the line) and `B` (`Depends on: A`). Wave 2 has `C` (`Depends on: B`). After the fold that follows wave 1, `fix/Z` is forced back one commit, and `main` gets a commit that clashes with A's file.
    - On `fcae4aa`: C is built. The run reports `issue_Z's branch origin/fix/Z was rewritten…` and names S's PR, with `holds={'Z': 'rewritten'}`.
    - With the patch: the run stops at C's base because A clashes with main, and Z's rewrite is never mentioned. S's open PR holds a commit that `fix/Z` no longer has, and nothing tells the human.
  - **The test pins this as intended:** `template/tests/test_integrate_carried_rewrite_late.py:215` (`_stopped_at_b`) asserts there is "nothing left for the end of the run to check by hand". That is true in its two-bundle run, where no other PR holds A's head. It is not true in general.
  - **Fix:** either still run the #695 check after a `_bundle_bases` stop (skipping the branch the stop already named), or have the base build check every head in `taken` before it builds anything.

- NEEDS-HUMAN [human] — If the base moves during a run, the whole run can now stop where `fcae4aa` finished it. A bundle's own base starts from `<base_remote>/<base>` as fetched at that moment (`integrate.py:841`), but the line never follows the base (#655).
  - **Concrete case:** wave 0 has `A` and `Z`, and wave 1 has `B` (`Depends on: A`). After the fold that follows wave 0, someone pushes a commit to `main` that touches A's file.
    - On `fcae4aa`: B is built on the line and the run completes.
    - With the patch: the run prints `flow: wave 1 — could not build issue_B's own base from issue_A: issue_A's branch origin/fix/A does not merge cleanly onto origin/main itself … STOPPING — wave 1 and later waves not run.` (`integrate.py:962`, `flow.py:2706`).
  - Every other bundle in wave 1 and later is dropped too, even ones with no tie to A.
  - The brief moves "holds for base-build failures" to #725, but it does not name this trigger, and on a busy repo it is the likely one.
  - You can argue the stop is an early warning, since A's own PR conflicts with main as well. Still, the human should decide what is acceptable until #725 lands: stopping the whole run, holding just B, or building B on the line.

- (Known and already out of scope, so no tag.) An overlap between waves that no edge declares now stops the run at the next fold. Example: `B` (`Depends on: A`) and an unrelated wave-0 `Z` both write `shared.txt`, and a wave 2 follows B. `fcae4aa` completes this run. The patch stops it with `… does not merge cleanly onto pdca-integration/… — an undeclared cross-wave overlap` (`integrate.py:1313`). This is #463's design working as intended: B's base no longer hides the overlap. The brief puts holds for this case in #725. I mention it only so sign-off knows it stops the run rather than holding one bundle.

- Reviewer's verdict: C5 in `check-gates.json` ("1 added driver-suite test(s) import the production package") only proves an import, not that the test runs production code. I checked that separately (see above), and it does. I found no other claim in `check-gates.json` that the evidence does not support. T4 is `deferred` to publish, so nobody has yet checked the PR text, which must tell the human to merge #726 first (brief line 13).

What I tried and could not refute: the red→green proof; that the test runs the production code; the closure walk on transitive, diamond, no-patch, discontinued-partner and partner-built-after-member inputs; the seam fallbacks; and the split in wording between a bundle's own base and the line in the #633, #695 and unchecked messages.

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — issue_727 (flow-in-batch-dependency-scoped-bases)

Lens: bugs this patch adds, and reuse / simplification / efficiency. Grounded on the patched tree at `$PDCA_TARGET`. I found no logic bug that gives a wrong base or a wrong report for the cases the brief lists. All five round-1 findings are fixed: the `>= wave` guard has a test (`test_a_members_partner_built_after_it_is_not_on_the_base`); the line's PR list now covers every head the line took, not just the latest (`_heads_taken`, `_lost`, and `test_a_pr_cut_from_the_line_at_an_older_head_is_named_when_it_is_lost`); the "no PR … holds them" wording now shows only when that is true; a base build that hits a rewrite names each base and PR (`_rewrite_stop(..., onto=)`); and the original undeclared-overlap input of `test_flow_reissue_after_conflict_hold.py` is kept, with the declared-edge case added as a separate test. Gates: C4 and T3 are green in `gate-logs/`; the red runs in `C4-verify.log` are the expected pre-fix runs.

The points below are advisory.

- NEEDS-HUMAN [human] — `template/src/pdca_harness/flow.py:2708`: if a base build fails (including on a rewrite it caught), the code sets `line_stopped = True`, which turns off the #695 end-of-run check (`flow.py:2855`). Bases and line PRs from earlier waves are then not checked again at the end, even though some may hold heads a branch has since lost. A failed fold already behaves this way, and the brief puts holds for base-build failures under #725, so this is consistent with today's behavior. Round 1 raised it, and it is still open. Decide whether to accept it here or track it under #725.
- NEEDS-HUMAN [human] — `template/src/pdca_harness/integrate.py:1117` (reached through `_carried_tips`, `integrate.py:519`): an in-run fold now stops the whole run when any taker's head is lost, including when only a bundle's own base lost it and the line's head is still on the branch. Example: a base takes `fix/A` at H2, a fast-forward past the line's H1, and then `fix/A` is pushed back to H1. The line is fine, and the next fold would merge H1 cleanly. The only damage is the PR built on that base, yet the run stops with a "re-issue the run" remedy. The brief's (7) asks the #633 report to *name* each base. It does not say a base-only loss should stop the line. Confirm this is the behavior you want.
- `template/src/pdca_harness/flow.py:1011`: `_bundle_bases` builds and pushes every base of the wave before it points any bundle. If a later bundle's base fails, the bases already pushed in that loop are left on origin, unrecorded and unused. Per-bundle base cleanup is out of scope in the brief, so this is only a note: the leftover `pdca-integration/*` branches are force-pushed over on the next build (`integrate.py:859-860`), so they do no harm beyond clutter.
- `template/src/pdca_harness/flow.py:913` / `flow.py:2855`: small efficiency nit. Each wave calls `_heads_taken` twice (before `_bundle_bases` and before the fold), and the end of the run calls it once more. `_resolve_target` re-reads briefs in `_closure_members`, `_bundle_bases` and `_heads_taken`. Batches are small, so this is not worth changing now.

No [impl] findings: I found nothing the builder needs to fix in another round.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] C5 Causal adequacy — Preserve the declared closure through a completed patchless prerequisite — N conflicts with A and H depends on N, yet H drops A although N was built on A; all four bundles become COMPLETE, violating the accepted-work invariant (template/src/pdca_harness/flow.py:953, template/src/pdca_harness/flow.py:964; brief.md:18; review-patchless-conflict.log:1).
- [ ] T5 Judgment — Confirm prior art by both affected production paths against merged history and closed/rejected work — the disposable repository exposes only one synthetic base commit, and the cited #724 rejection artifacts are outside this input bundle (template/src/pdca_harness/flow.py:913; template/src/pdca_harness/integrate.py:724; brief.md:24).
- [ ] Validation — fitness-to-purpose — Decide whether the scoped isolation and retained line-based seam behavior satisfy the intended workflow, and honor the prerequisite merge order (#726 first) — green offline checks do not settle that product acceptance (brief.md:9, brief.md:13; template/src/pdca_harness/flow.py:1014).
- [ ] When a base build stops the run for any reason other than a rewrite, the end-of-run check (#695) is turned off. A rewrite of a branch that is not one of that base's members then goes unreported.
- [ ] If the base moves during a run, the whole run can now stop where `fcae4aa` finished it. A bundle's own base starts from `<base_remote>/<base>` as fetched at that moment (`integrate.py:841`), but the line never follows the base (#655).
- [ ] `template/src/pdca_harness/flow.py:2708`: if a base build fails (including on a rewrite it caught), the code sets `line_stopped = True`, which turns off the #695 end-of-run check (`flow.py:2855`). Bases and line PRs from earlier waves are then not checked again at the end, even though some may hold heads a branch has since lost. A failed fold already behaves this way, and the brief puts holds for base-build failures under #725, so this is consistent with today's behavior. Round 1 raised it, and it is still open. Decide whether to accept it here or track it under #725.
- [ ] `template/src/pdca_harness/integrate.py:1117` (reached through `_carried_tips`, `integrate.py:519`): an in-run fold now stops the whole run when any taker's head is lost, including when only a bundle's own base lost it and the line's head is still on the branch. Example: a base takes `fix/A` at H2, a fast-forward past the line's H1, and then `fix/A` is pushed back to H1. The line is fine, and the next fold would merge H1 cleanly. The only damage is the PR built on that base, yet the run stops with a "re-issue the run" remedy. The brief's (7) asks the #633 report to *name* each base. It does not say a base-only loss should stop the line. Confirm this is the behavior you want.
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
- Iteration delta (if iterating): Auto-iterate (round 2): rebuilding for the implementation-level findings — C5 Causal adequacy — Preserve the declared closure through a completed patchless prerequisite — N conflicts with A and H depends on N, yet H drops A although N was built on A; all four bundles become COMPLETE, violating the accepted-work invariant (template/src/pdca_harness/flow.py:953, template/src/pdca_harness/flow.py:964; brief.md:18; review-patchless-conflict.log:1).; When a base build stops the run for any reason other than a rewrite, the end-of-run check (#695) is turned off. A rewrite of a branch that is not one of that base's members then goes unreported.. Deferred, not addressed here: 11 finding(s) that need human judgment, held in deferred-findings.json for the human at handover — not build work
- By / date: auto-iterate / 2026-10-15

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 7 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
