# Result — issue 747 / hold-a-single-partner-cross-wave-clash-at-the-line-fold

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: 
- Success criterion: Real-git tests through `flow._drive_and_act` on the `StackFoldGit` fixture (`template/tests/test_integrate_stack_bases.py:123`), loaded by path the way `test_flow_same_wave_conflict.py:36-56` does. Each case asserts the holds map, the partners named in the stderr line, and the exit code from `cli._results_rc(results, holds=holds)` (`cli.py:707`). Holds alone → 3; a PLANNED dependent → 1.
  (1) **In-batch earlier-wave partner.** `A` and `Q` in wave 0. `Y` (`Depends on: Q`, so wave 1, built on its own base from `Q` only). `A` and `Y` both add `shared.txt`. An unrelated chain `W→V→U`. `Y` is held naming `issue_A`, `U` is COMPLETE, no `STOPPING`. Exit 3. Advice (A is not Y's prerequisite): the fold-time line says Y's change conflicts with `issue_A's`, already on the line from an earlier wave (it must NOT say "same wave"), and the end-of-run line proposes `Conflicts with: A` as `_CONFLICT_STEP` does today.
  (2) **Finished bundle carried onto the line.** `F` finished in an earlier run and is carried before wave 0 by `_carry_finished` (`flow.py:1356`) because an unrelated drive-set bundle `Z` declares `Depends on: F`. `Y` does NOT depend on `F` (so `F` is not Y's prerequisite and Y's base lacks it); `Y` clashes with `F` on `shared.txt`. `Y` is held naming `issue_F`, not "no bundle's own change accounts for …"; advice as in (1) (`Conflicts with: F`); `Z` is COMPLETE. Exit 3. Route (fixed here): today the in-run fold only sees `accepted` (`flow.py:2985-2990`; `accepted` grows only by `complete`, `:2947`), and `_carry_finished` records no head for it (`_fold_lines` docstring: "the carry passes none"). So `_carry_finished` also records each finished id it carried with the head it folded, into a run-level `{name: head}` map, and the in-run fold passes it through `_fold_lines` to `fold` as a new keyword-only argument used ONLY as extra partner candidates for rules (c)-(e). Those heads are never merged by the in-run fold, never enter `took` or `carried`, so the #633/#695 rewrite checks are unchanged. Do not route `F` through the fold's bundle list.
  (3) **Stays a stop.** `test_flow_same_wave_conflict.py::test_a_conflict_only_with_a_base_taken_in_mid_wave_still_stops_the_run` still prints `STOPPING`, unchanged. Two more stop guards in the new file, with these exact names so the siblings can flip them: `test_a_clash_two_line_bundles_cause_only_together_still_stops` (fails rule (e); child-2 #748 flips it) and `test_a_clash_with_a_partner_whose_head_no_longer_fits_the_base_still_stops` (fails rule (d); child-3 #749 flips it). Each docstring names the child that will flip it.
  (4) **Flip.** `test_flow_same_wave_conflict.py::test_a_conflict_with_earlier_wave_work_still_stops_the_run` (21, `Depends on: 10`, cut from the plain base, clashing with 10 on the line) is renamed and now checks: 21 held; its fold-time stderr line contains `issue_10` and `(conflicts in shared.txt)` and tells issue_21's owner to rebuild its branch on issue_10's; the WHOLE stderr (fold-time line and end-of-run `_report_conflict_holds` line) does NOT contain `Conflicts with: 10` (10 is 21's own prerequisite) and does not say "same wave"; 30 not built; no `STOPPING`; exit 1. `build-notes.md` lists every other test that flips, before and after.
  Before the change, cases (1), (2) and (4) end in `STOPPING` with the unrelated bundle PLANNED. The existing suites stay green.
- Repo + branch target: eduralph/pdca-harness @ main (PRs target `main`). Do builds and the gate verifies on the run's line, `pdca-integration/main-r547f8028520f` with #738's accepted work folded on top (`9f7c446`), exported as `$PDCA_VERIFY_BASE`. `path:line` anchors are on `9f7c446` (the line tip with #738 folded). Tests are pinned by name, and Do re-checks line numbers on the folded tip.
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

Review #747: hold a bundle whose cross-wave fold conflict is fully explained by named line partners, continue unrelated work, and retain every specified stop boundary.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The offline success cases and rules (a)–(e) define an actionable hold/stop boundary, including the explicit stop for a remaining bundle built on a partner; brief.md:2 and brief.md:23. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only the two production files yields three assertion failures with the specified STOPPING symptom across 12 tests; review-red.log:38; template/tests/test_flow_cross_wave_fold_holds.py:266. |
| C3 Change | FAIL | The required stop boundary is violated when a remaining line head contains a named partner: excluding that head from the trial permits an unsupported hold and continued execution; template/src/pdca_harness/integrate.py:1829. |
| C4 Verification (red→green) | PASS | Stash/pop rerun independently reproduces three failures before and all 12 supplied tests passing after restoration; review-red.log:38 and review-green.log:3; the additional rule-(e) failure is recorded under C5. |
| C5 Causal adequacy | NEEDS-HUMAN [impl] | Restore the required stop when a remaining bundle inherits a partner and add regression coverage — the independently exercised A→P topology incorrectly holds Y and completes U instead of stopping; template/src/pdca_harness/integrate.py:1830; review-rule-e.log:24. |
| T1 Structure | PASS | Attribution remains within the fold's conflict handling and reuses the existing trial/classifier machinery; classification-only carried heads do not enter the in-run rewrite map; template/src/pdca_harness/integrate.py:664 and template/src/pdca_harness/flow.py:1498. |
| T2 Shape | PASS | Independently reran production-import scanner, docs lint, 22-page render/link audit, and git diff --check successfully; frozen host-CI parity also records a clean audit at gate-logs/host-ci-docs.log:14. |
| T3 Runtime | PASS | Independent offline suite passes 2,614 tests with two skips; root rerun exits 77 because this interpreter lacks copier, while the frozen log shows all 24 root cases actually passed; gate-logs/T3-suite.log:54 and gate-logs/T3-suite.log:1874. |
| T4 Contribution | N/A | Contribution artifacts are drafted after Check; the deferred audit must rerun substantively at publish; gate-logs/T4-contribution.log:10. |
| T5 Judgment | NEEDS-HUMAN | Confirm prior-art review by affected file across merged history and closed/rejected work — the supplied target has only one synthetic base commit, so the historical claims cannot be independently settled; review-prior-art.log:1 and brief.md:17. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Approve the operator-facing hold/continue policy and prerequisite-versus-conflict advice after the rule-(e) correction — these determine which unrelated work proceeds and which rebuild action owners take; template/src/pdca_harness/flow.py:1555. |

One reproduced implementation defect: rule (e) rejects a line remainder built on a named partner, but `template/src/pdca_harness/integrate.py:1829` removes such bundles from the trial instead. With A adding shared.txt, P depending on A and adding p.txt, and Y depending on unrelated Q and adding its own shared.txt, P remains on the line and contains A. The patched run names only A, holds Y, completes the unrelated chain through U, and exits 3. The brief requires a stop and exit 1. Actual git trials confirm A is an ancestor of P, base + P + Y conflicts, and base + Y merges cleanly (review-rule-e.log:25). This is a missed case in otherwise passing supplied tests, not an environment failure.

Reproduce with `PYTHONDONTWRITEBYTECODE=1 python3 review-rule-e.py` from this review directory; it exits 1 on the required-stop assertion through the production `flow._drive_and_act`. Preserve the nonpartner remainder when applying rule (e), and reject attribution when its recorded build ancestry would reintroduce a partner, as the brief requires. The builder can correct this without expanding into child-2's joint attribution.

The disposable target matches the declared pre-fix base 9f7c446 and was restored after the independent red leg. All source citations above resolve under `$PDCA_TARGET`; no target-staleness caveat applies. Frozen gate logs were read for every configured row. Local root-render coverage was unavailable because copier is not importable by /usr/bin/python3 (review-root-suite.log:6); its frozen gate evidence explicitly shows real render/update cases executed successfully, rather than a shim or code-read substitute. No unsatisfied external dependency is declared in the brief. INTEGRATION.md's human-only list is an unconfigured template placeholder at template/docs/INTEGRATION.md.jinja:80.

The affected-file history query covered all four patch paths and returned only the synthetic snapshot (review-prior-art.log:1). The supplied artifacts contain no closed/rejected-work archive; the prior-art decision remains for the human. This review annotates the defect and sign-off decisions; it does not gate acceptance.

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — issue_747 (cross-wave clash hold at the line fold)

Lenses: correctness bugs the patch introduces, and reuse / simplification. Anchors are on the patched target (`$PDCA_TARGET`).

- NEEDS-HUMAN [human] — `template/src/pdca_harness/integrate.py:1829-1832`: rule (e) does not follow the brief. The brief says that if any remaining line bundle was built on a partner, "(e) counts as failed and the run stops (child-2 may refine this)". The patch does the opposite. It drops each such bundle from `rest` and can still hold. It also detects "built on" by checking whether the bundle's head contains the partner's head (`_in_line(..., of=h)`), not through `_built_on`'s `under` as the brief defines it. The relaxation is needed for case (4) to pass: in `test_a_conflict_with_its_own_prerequisite_on_the_line_holds_it`, 20 is `Depends on: 10`, so it is built on the partner 10. Under the brief's literal rule that case would stop, not hold. So the brief contradicts itself, and the builder chose one side without saying so in the diff. The cost of that choice: a dropped dependent's own change is never trial-merged together with `head` in (e). `_partners` only clears it pairwise, so a clash that needs that dependent plus another line bundle can be held and blamed on the named partners alone. Child-2 owns exactly that kind of joint clash. No test covers it. A human should decide whether this relaxation is the intended rule (and record it in the brief / for #748), or whether case (4) should be reworded.
- `template/src/pdca_harness/integrate.py:1800-1835` (reuse, OK): `_line_partners` reuses `_clash` / `_partners` / `_built_on` / `_trial` as the brief asks, and adds no second classifier. Rule (d) gets no explicit trial. That is sound: `_partners` names a bundle only when `_trial(base, [its, head])` fails at index 1, so the partner's own head already merged cleanly onto the base. The docstring says so. `test_a_clash_with_a_partner_whose_head_no_longer_fits_the_base_still_stops` covers it, but only through `_clash` falling to kind `"line"`, never through a separate (d) check. That is fine for now, but child-3 will need to know (d) is implicit.
- `template/src/pdca_harness/flow.py:1566-1569` (minor wording, not blocking): `whence` takes the "same wave" wording only when *every* partner is in `wave`, and the "carried" wording only when every partner is a finished id. A hold whose partners mix a same-wave bundle with an earlier-wave one, or with a carried finished one, is worded "already on the line from an earlier wave". That is wrong for the same-wave partner. Child-2's joint attribution makes mixed sets more likely. One phrase per partner group would be more accurate.
- `template/src/pdca_harness/flow.py:1545-1552` (minor): `_own_prereqs` looks only at the held bundle's *direct* declared deps. A partner that is a transitive prerequisite (Y → Q → A) gets the `Conflicts with: A` proposal rather than the rebuild step. In stack mode Y's base normally already holds A, so this is unlikely to come up. Mentioned for completeness, not filed.

Gate evidence: C4 is red before the fix (cases 1, 2 and the flip fail on `_not_stopped` / the hold asserts) and green after it. T3 passes, with 2614 tests OK. The carry's switch from `carried=None` to `carried=put` (`flow.py`, `_carry_finished`) is safe: an empty mapping skips `_carried_tips` (`integrate.py:547`, `if carried and ...`), and `carried.update(took)` runs only after a push. I found no other correctness bug or resource issue in the diff.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] C5 Causal adequacy — Restore the required stop when a remaining bundle inherits a partner and add regression coverage — the independently exercised A→P topology incorrectly holds Y and completes U instead of stopping; template/src/pdca_harness/integrate.py:1830; review-rule-e.log:24.
- [ ] T5 Judgment — Confirm prior-art review by affected file across merged history and closed/rejected work — the supplied target has only one synthetic base commit, so the historical claims cannot be independently settled; review-prior-art.log:1 and brief.md:17.
- [ ] Validation — fitness-to-purpose — Approve the operator-facing hold/continue policy and prerequisite-versus-conflict advice after the rule-(e) correction — these determine which unrelated work proceeds and which rebuild action owners take; template/src/pdca_harness/flow.py:1555.
- [ ] `template/src/pdca_harness/integrate.py:1829-1832`: rule (e) does not follow the brief. The brief says that if any remaining line bundle was built on a partner, "(e) counts as failed and the run stops (child-2 may refine this)". The patch does the opposite. It drops each such bundle from `rest` and can still hold. It also detects "built on" by checking whether the bundle's head contains the partner's head (`_in_line(..., of=h)`), not through `_built_on`'s `under` as the brief defines it. The relaxation is needed for case (4) to pass: in `test_a_conflict_with_its_own_prerequisite_on_the_line_holds_it`, 20 is `Depends on: 10`, so it is built on the partner 10. Under the brief's literal rule that case would stop, not hold. So the brief contradicts itself, and the builder chose one side without saying so in the diff. The cost of that choice: a dropped dependent's own change is never trial-merged together with `head` in (e). `_partners` only clears it pairwise, so a clash that needs that dependent plus another line bundle can be held and blamed on the named partners alone. Child-2 owns exactly that kind of joint clash. No test covers it. A human should decide whether this relaxation is the intended rule (and record it in the brief / for #748), or whether case (4) should be reworded.
- [ ] **The thread could not be checked: there is no `notes.json` or `sources/` in the bundle.** The only input present is `brief.md`. So none of these can be verified against the tracker: the problem statement, the "human's decisions at the #725 re-plan (2026-10-17, decisions 2-4)", the "#739 iteration-v4 split decision" (Invariant line), and the prior-art claims about `iteration-v1/patch.diff` and `_held_on_line`. Before sign-off, a human should confirm the thread backs rule (a)-(e). In particular, check that someone decided "partners fully explain the clash" (rule e) rather than "any partner conflicts".
- [ ] **None of the brief's anchors match the target source.** The brief says "`path:line` anchors are on `9f7c446` (the line tip with #738 folded)". The `$PDCA_TARGET` I was given is a different tree:
- [ ] **The brief gives three different line ranges for the flow's fold block.** Scope says "in the fold block (`:2862-2879`)". Citations say "the flow's fold block (`flow.py:2980-2999`)". Defect says `STOPPING` is at "`flow.py:2991-2997`". On one commit these cannot all be the same block. Do will be told to edit at one range and to mirror at another. Pin a single range, or pin a function and comment instead.
- [ ] **Case (2) needs a change to the fold API, which the brief puts out of scope.** The brief scopes "the fold API (#723)" out, but case (2) cannot be met without new plumbing:
- [ ] **Case (4)'s negative assertion conflicts with the scope.** Case (4) requires the output "does NOT contain `Conflicts with: 10`". But every hold in `held_conflict` gets a second line at the end of the run from `_report_conflict_holds` (`flow.py:1263-1272`, called at `:2681`), built from `_CONFLICT_STEP = "declare \`Conflicts with: {ids}\` …"` (`flow.py:1004-1005`). The existing tests assert on the whole stderr (`self.err`, e.g. `test_flow_same_wave_conflict.py:362-366, 411`). So either:
- [ ] **Case (2)'s fixture is underspecified, and may land in case (4)'s wording.** `_carry_finished` only carries a finished id when "a drive-set bundle's plain `Depends on` names one the fold can carry" (`flow.py:1096-1098`). If F is carried because Y declares `Depends on: F`, then F is Y's own prerequisite, and the brief's partner-is-a-prerequisite wording (case 4) applies, not a plain hold. The brief should name which bundle depends on F, and which advice case (2) expects.
- [ ] **Rule (e) is not defined when a remaining line bundle was built on a partner.** "base + the line *without* them + the head merges cleanly" does not say how to build "the line without them" when another bundle on the line was cut from a partner's branch, and so carries its commits. `_partners` already deals with exactly this through `under` / `_built_on` (`integrate.py:1340-1358`). Rule (e) as written would put the partner's commits back, fail, and stop. That is safe, but it is an extra stop the brief doesn't list, and child-2 will inherit the ambiguity. State whether (e) replays bundle heads, or uses `under`.
- [ ] **"Depends on" is undeclared even though the brief relies on #738's work.** The brief has no `Depends on` / `Stacks on` field and there is no `dependency-state.json`. Yet the Ordering note says this child builds on #738's accepted work folded at `9f7c446`, and edits the same held sets and `_runnable` call. If #738's state changes (re-opened, re-folded), nothing records this child's dependence on it. Declare it, or confirm the run's line is pinned.

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
- Iteration delta (if iterating): Auto-iterate (round 1): rebuilding for the implementation-level findings — C5 Causal adequacy — Restore the required stop when a remaining bundle inherits a partner and add regression coverage — the independently exercised A→P topology incorrectly holds Y and completes U instead of stopping; template/src/pdca_harness/integrate.py:1830; review-rule-e.log:24.. Deferred, not addressed here: 10 finding(s) that need human judgment, held in deferred-findings.json for the human at handover — not build work
- By / date: auto-iterate / 2026-10-15

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 8 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
