# Result — issue 395 / same-wave-conflict-refused-at-accept

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: In a `pdca flow` run in stack mode, a bundle is not accepted if its branch would textually conflict with a bundle of its own wave that is already accepted. This covers the waves the fold runs after: `k < len(wave_list) - 1`, `do_publish`, publisher not `stub` — the same condition as `flow.py:3078` plus the fold's non-dry `held_out` (flow.py:3115). "Would conflict" means the fold's own #674 rule, in the fold's order. When an accept (from a session, or a decision already recorded in the bundle) would add such a bundle, the driver refuses it the way C6 refuses an accept today. The bundle gets an open §6 NEEDS-HUMAN row naming the partner(s), the conflicting file(s) and the step (declare `Conflicts with: <partner>` in its brief, then `iterate-plan`). It stays AWAITING_SIGNOFF. Its siblings are accepted and published as before. So, in those waves, a run no longer accepts two same-wave bundles whose branches conflict, and it never opens two such PRs. A bundle the trial refuses is never COMPLETE without a PR. The last wave, a one-wave run, single-issue `flow`, `--no-publish`, merge mode, a dry run and the standalone `pdca signoff --accept` do not change. This is a partial fix of #395: the PR says `refs #395`, not `closes`.
- Success criterion: These run on the real-git `StackFoldGit` fixture with `gh` stubbed and the publisher in `command` mode. Every accept goes through the real `flow._drive_wave` → `flow._apply_decision` path: Do+Check are stubbed, the decision is written to the bundle (`leaves.SIGNOFF_DECISION`), and nothing calls `signoff.record(... "accept")` directly. A later wave exists in every case except (g), so the fold condition holds.
  - (a) A and B are in wave 0, with no `Conflicts with` between them. Their patches change the same lines of a shared file, and both carry `accept`. After the run: A is COMPLETE, its branch is pushed and `gh pr create` is called for it. B is AWAITING_SIGNOFF (`state.state`). B's SUMMARY §6 has an open row naming `issue_A` (or A's id) and the shared file. `signoff.open_needs_human` returns that row. B's branch is not on origin and no `gh pr create` names B. The run's `holds` has no entry for B. `cli._results_rc` is 1 (B did not finish). A wave-1 bundle that depends on neither still builds and completes.
  - (b) A and B change different lines of the same file (no textual conflict). Both are COMPLETE and both are published. Neither §6 gains a row.
  - (c) The refusal does not depend on which accept is applied first. With B's decision applied before A's (for example, B carries a recorded decision, which the pre-apply at flow.py:2516-2522 applies first, and A's is written by the stubbed session), A is the one refused, and the accepted one publishes. Either way, exactly one of the pair is COMPLETE and the fold holds nothing (`holds` empty).
  - (d) Override, in the SAME run (not a re-run — on a re-run A is finished and skipped, so B is no longer A's same-wave sibling and the #674 same-wave hold does not apply). Leg (a)'s setup, but the stubbed sign-off session offered to B after its refusal ticks B's new row and writes `accept` again. B is then accepted and published in that run. The fold, still running over wave 0 with A and B both accepted, holds B as `"conflict"` exactly as on `main` (#674): `holds` has B with reason `"conflict"`. The row is not added a second time (`signoff.ensure_needs_human_item` leaves a ticked row alone, `signoff.py:177-207`).
  - (e) The trial cannot run for the target: inject a failure of its git step (a fetch or a commit build). B, which shares a file path with the already-accepted A, is refused with a §6 row saying the check could not run and naming A and the file. C, accepted in the same wave with no file shared with an accepted sibling, is accepted and published.
  - (f) The row lives only in SUMMARY §6. It is NOT added to `assemble.collect_needs_human` (`assemble.py:389`) or to any Check artifact, so it has no IMPL/HUMAN kind and auto-iterate never sees it (do not add a new artifact source). A reassembly of B's SUMMARY (an iterate-do or auto-iterate rebuild) drops the row and any tick on it; that is intended, because the next accept runs the trial again. Test it: after B is refused as in (a), reassemble B's SUMMARY with the driver's own assembly step, write `accept` again, and drive another pass. B is refused again and the row is back, unticked. (Red on `main`: B is accepted.)
  - (h) A trial refusal does not spin the wave until the pass budget runs out. With `max_passes = 20` and the session stub for B writing nothing after the refusal, B is offered at most ONE sign-off session after the pass that refused it (`leaves.run_signoff_batch` calls naming B ≤ 2 in total). The wave then ends with B still AWAITING_SIGNOFF. The stderr line about B names the conflict, the partner and the step (`Conflicts with: <partner>` then `iterate-plan`). It does NOT say "raise [driver].max_passes". A plain C6 refusal (an open §6 row from Check, no trial involved) keeps today's behaviour; this leg does not change it.
  - (g) Last wave: the same conflicting A/B as the only wave of a run. Both are accepted and both are published, with the same exit code as on `main`.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: In a flow run's stack-mode non-final waves (the condition in Goal), an accept that would add a same-wave textual conflict, judged as the fold judges one, is refused. The bundle stays AWAITING_SIGNOFF with an open HUMAN §6 row. That covers every accept route inside `_drive_wave`. A trial-refused bundle is offered one more sign-off session, then the wave stops re-offering it and its wave-end message names the conflict step instead of the pass-budget hint (leg h). When the check cannot run for a target, refuse only a candidate whose patch shares a file path with an already-accepted sibling of the wave on that target. Every other candidate is accepted. The fold keeps its own #674 hold as the last line of defence (overrides, branches that move after the accept). Update `docs/07-crosscutting.md`: the same-wave paragraph (:719-731) gets the new behaviour, the override, and the fact that a line-plus-sibling conflict (#747 `_held_by_line`) is still caught only at the fold, after publish. The exit-code paragraph (:734-745) says a refused bundle is unfinished (exit 1). / out of scope: the last wave and one-wave runs (follow-up); re-sequencing a refused bundle into a later wave of the same run, and writing `Conflicts with` into its brief automatically (follow-up; the issue's layer-2 re-sequence half); a conflict that also involves work already on the line (#747) — the fold still catches it after publish (follow-up); the issue's layer 1, a Plan-exit advisory over briefs' predicted files (follow-up; briefs have no structured file list); the standalone `pdca signoff --accept` (no wave context); merge mode; documenting the assumption that every target repo has a PR setup and that accepted ⇒ PR, with its two existing exceptions (T4-failed texts, failed push) (follow-up, human-requested); the advisory `_audit_wave_overlap` warning (flow.py:1586), which stays as it is.

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

Review issue #395: refuse conflicting same-wave accepts before publishing in stack-mode non-final waves, leaving the refused bundle AWAITING_SIGNOFF.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The accept-order rule, override, overlap-only fallback, and excluded modes are explicit and falsifiable; brief.md:19, brief.md:21, brief.md:37. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing the production fix leaves the regression suite runnable and produces 11 assertion failures, including COMPLETE instead of AWAITING_SIGNOFF; target/template/tests/test_flow_same_wave_accept_trial.py:234; review-red.log:232. |
| C3 Change | NEEDS-HUMAN | Approve broadening the failure policy to refuse disjoint bundles after integration-tree errors — the brief promises acceptance without shared paths, but the new exception branch refuses regardless; brief.md:37; target/template/src/pdca_harness/flow.py:321; target/template/tests/test_flow_same_wave_accept_trial.py:332. |
| C4 Verification (red→green) | PASS | Independently restored the stashed fix and reran all 14 regression tests successfully, reproducing the frozen gate's transition; review-green.log:3; gate-logs/C4-verify.log:249; target/template/tests/test_flow_same_wave_accept_trial.py:234. |
| C5 Causal adequacy | NEEDS-HUMAN [impl] | Fix quoted-path parsing and add a real-git regression — with café.txt and an injected trial failure, the fallback sees no paths and both conflicting bundles become COMPLETE and publish; target/template/src/pdca_harness/integrate.py:874; target/template/src/pdca_harness/waves.py:329; review-quoted-path.log:1. |
| T1 Structure | PASS | Acceptance precedes recording on both flow routes, and trial/publish base selection and the fold's clash rule share production helpers; target/template/src/pdca_harness/flow.py:206; target/template/src/pdca_harness/flow.py:2783; target/template/src/pdca_harness/flow.py:2801; target/template/src/pdca_harness/publish.py:767; target/template/src/pdca_harness/integrate.py:947. |
| T2 Shape | PASS | Independently reran docs lint, 22-page rendering and internal-link audit successfully; frozen host-CI parity also captures both checks passing, and git diff --check is clean; gate-logs/T2-docs.log:11; gate-logs/host-ci-docs.log:11; target/.github/workflows/docs-check.yml:33. |
| T3 Runtime | PASS | Independently reran 2,644 driver tests (two skips) and 19 root tests (prior-release class skipped without tags); frozen evidence additionally shows the full 24-test root suite passing; review-driver-suite.log:1819; review-root-suite-copier.log:5; gate-logs/T3-suite.log:54. |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the captured deferred result explicitly requires the substantive audit at publish; gate-logs/T4-contribution.log:10. |
| T5 Judgment | NEEDS-HUMAN | Confirm merged and closed/rejected prior art by every affected path — this target has one synthetic base commit and no remotes, while the brief reports merged history for the earlier test and closed work for flow/integrate only; review-prior-art.log:1; brief.md:46; target/template/src/pdca_harness/cli.py:1546. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether non-final-wave-only protection and the exercised publishing model meet the intended workflow — last-wave conflicts remain allowed, and gh plus publishing mechanics were stubbed, so live GitHub PR behavior was not exercised; target/docs/07-crosscutting.md:761; target/template/tests/test_flow_same_wave_accept_trial.py:117; target/template/tests/test_flow_same_wave_accept_trial.py:138. |

The C5 finding is independently reproduced in review-quoted-path.log:1–8. Git generates `diff --git "a/caf\303\251.txt" "b/caf\303\251.txt"`; the advisory regex in target/template/src/pdca_harness/waves.py:329 cannot match it. Promoting that parser into the accept fallback at target/template/src/pdca_harness/integrate.py:874 treats an unparsed footprint as proof of no overlap. Using the existing real-git fixture, conflicting edits to that file, and the same failed-apply injection as the added fallback test yields: both COMPLETE, B's branch pushed, one mocked PR-create call for B, no open refusal row, and B held only after publication. The existing fallback test uses an ASCII shared.txt fixture (target/template/tests/test_flow_same_wave_accept_trial.py:307), so its green result does not discharge this case. Decode Git-quoted paths reliably, distinguish unknown footprints from disjoint ones, and cover this failure with Git-generated diffs.

Reproduce from this review directory with `TMPDIR="$PWD/review-tmp" PYTHONDONTWRITEBYTECODE=1 python3 review-quoted-path.py`. This exercises the patched production accept path and real Git operations; only the trial failure and existing publisher/gh stubs are injected.

All supplied gate logs were available. Instance-scoped wrapper scripts were not treated as target requirements: their frozen logs were read, and available underlying suites and docs checks were rerun. The default Python could not import Copier (review-root-suite.log:6); rerunning with the installed Copier environment exercised rendering successfully (review-root-suite-copier.log:8). Prior-release compatibility could not be rerun without release tags (target/tests/test_update_compat.py:245); its frozen full-suite evidence is gate-logs/T3-suite.log:38–56. This is a snapshot limitation, not a patch compile/apply defect. The target patch was restored after the red leg; no production edits were made. No capability-probe/load-time symptom guard was introduced.

<!-- pdca:leaf-complete -->

### Advisory — adversary

# Adversarial review: issue 395, same-wave conflict refused at accept (iteration 8)

**Verdict: no refutation of what this round fixes.** The red→green proof holds up. The `cli.py` fix that this round was asked for is real, and each of the three earlier fixes is pinned by its own test. I have one design-level finding, which comes from the step the refusal row tells the human to take. The other bullets are low-severity notes.

## Evidence, re-run (scratch copy of `$PDCA_TARGET`, Python 3.14)

- Green: `tests.test_flow_same_wave_accept_trial` passes, 14/14. That matches `gate-logs/C4-verify.log`. In the red leg, 11 tests fail and 3 pass. The 3 that pass are the "nothing changes" legs: (b) clean merge, the plain C6 refusal, and (g) last wave. That is correct, not a sign of weak tests.
- **The C4 red leg alone does not prove the `cli.py` hunk.** In the red log, `test_iterate_plan_from_the_cli_leaves_the_rebuilt_bundle_to_a_new_session` fails at its first run's `_not_published("11")`, because the trial is reverted too. It never reaches the CLI assertion. So I reverted only `template/src/pdca_harness/cli.py:1538-1549` and kept the rest of the patch. That leg then goes red at `found == [(AWAITING_SIGNOFF, "")]`: the stale accept is applied and no session is offered. With the hunk back, it is green. The iteration-7 fix is verified.
- Mutants (each a scratch copy with one fix undone; every one went red on its own leg):
  - `_sessions_reset` turned into a no-op (`flow.py:434-441`): both re-run legs fail.
  - `_session_offered` moved back to before the session runs (`flow.py:2793-2798`): `test_a_session_that_fails_is_not_the_one_more_session` fails.
  - The tree-error branch dropped, so tree errors fall back like a failed fetch (`flow.py:321-323`): `test_a_check_that_breaks_the_tree_refuses_and_names_it` fails.
  - The hold-count rule changed to "refuse only if `d` itself is held" (`integrate.py:836`): leg (c) fails.
- Production path: every leg goes through the real `flow._drive_and_act` → `_drive_wave` → `_apply_decision`. No test stubs `_drive_wave`. Do, Check, the session leaf and the push stub are stubbed, as the brief allows. I found no tautology.
- Extra probe, a case the new tests don't cover: the conflicting pair placed in a **middle wave** (12 in wave 0; 10 and 11 depend on 12; 20 depends on 10). There the trial starts from `folded_tips` and each sibling's own base (#727). Result: 11 is refused and named, 10 and 12 publish, `holds` is empty, rc 1. The trial works when `folded_tips` is non-empty, even though no committed test covers it.

## Findings

- NEEDS-HUMAN [human] — **Following the refusal's own step inside the session wastes a full re-plan and rebuild in the same run, which is then refused again.** The row and the wave-end line say "declare `Conflicts with: 10` in issue_11's brief, then iterate-plan it" (`template/src/pdca_harness/flow.py:388-395`). Inside a flow sign-off session, the natural way to do that is to write `iterate-plan` into the decision file. `_apply_decision` applies an iterate-plan at once, even in the batch sweep (`flow.py:238-239`). The wave's next pass then runs the interactive Plan pre-pass and rebuilds the bundle (`flow.py:2734`, `flow.py:771-781`). That rebuild happens **in the same wave, on the same base, still without 10's change**, because waves and stack bases are fixed at the start of the run. So the rebuilt 11 conflicts again and is refused again. The run then parks it with the same advice to declare `Conflicts with: 10`, which its new brief already declares. I reproduced this with a scratch probe: the session writes `iterate-plan` + rationale, and the stubbed Plan step re-plans with `conflicts_with="10"`. Result: `built == ['issue_10','issue_11','issue_12','issue_11','issue_20']`, 11 ends AWAITING_SIGNOFF, and the stderr shows a second "cannot accept: … conflicts with issue_10's" after the "iterate-to-Plan — archiving" line. In a real run, that costs one interactive Plan session, a Do run, a Check run and another sign-off session, all for nothing in this run. The brief's design says recovery comes "the next run", and it lists same-run re-sequencing as a follow-up. It does not say whether a trial-refused bundle's iterate-plan should be held back until the next run (parked at UNPLANNED for the rest of this wave), or whether the step text should warn that it only helps on the next run. That is a scope call. Once it is made, the builder should also stop the parked line from telling the human to declare a `Conflicts with` the brief already carries.
- **A "tree" refusal is raised even when the tree was put back.** This is low severity and matches the human's iteration-6 ruling ("re-raise those two"). In `integrate.py:832-834`, the outer `_back_on(..., first=exc)` puts the tree back and then re-raises the inner `_LineBroken`. The test pins exactly this: `test_a_check_that_breaks_the_tree_refuses_and_names_it` asserts both the `_LineBroken` and `_on_the_line_at_base("12")`. So a single failed `git checkout` refuses bundle 12, which shares no file with 10, and the row says the tree is "in a state it could not put back" when the tree is verifiably clean on the line. This fails closed and costs one human tick. I am noting it, not asking for a change.
- **The fallback treats an advisory heuristic as a hard refusal.** This is low severity. `integrate.same_wave_overlap` (`integrate.py:863-885`) uses `waves.diff_files`, whose own docstring says it is "a best-effort heuristic … never a hard gate" (`waves.py:332-340`) and that it can misread paths that contain spaces. When the trial cannot run, a shared path with a space in it can be missed, and the bundle is then accepted. The fold's #674 hold still catches the conflict after publish, so this only matters in the rare case where the trial fails *and* such a path is involved. Not raised as NEEDS-HUMAN.

## Claims I tried to break and could not

- Fold-order and key match. The trial sorts by name as `complete` does (`flow.py:3318`), and it reads `folded_tips[(repo_spec, base)]` with the same key the fold groups by (`integrate.py:542-564`).
- Self-deadlock on the integration lock. `_fold_lines` releases its `ExitStack` before the next `_drive_wave` (`flow.py:1495-1509`), so the trial's `integ_lock` never meets a lock its own process still holds.
- No-§6 summary. If §6 is missing, `ensure_needs_human_item` adds nothing, and `_refuse` would then fall through to accept. But `signoff.unrecordable` runs first in `_apply_decision` (`flow.py:197-199`) and refuses that shape, so this case cannot be reached.
- Other routes that could keep a stale accept alive. Auto-iterate declines when a decision is on disk (`flow.py:576-580`). The repair path deletes the decision file (`flow.py:127`). Both routes that record a decision now call `consume_decision`. I found no third route that archives an attempt and keeps `signoff-decision`.
- The `publish._checkout_base` refactor (`publish.py:767-776`) behaves the same as the inline code it replaces.

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — issue 395 (same-wave conflict refused at accept)

Lenses: correctness bugs the patch introduces, and reuse / simplification / efficiency.
Grounded on the patched target at `$PDCA_TARGET`.

**Correctness: no blocking defect found.** I traced the accept paths and the session bound
by hand, and they behave as the brief asks:

- Pre-apply refusal, then a session, then a C6 block: 2 sessions, then parked.
- Post-session refusal: one more session, then parked.
- A session that raises is not counted (`flow.py:2790-2798`).
- The count goes back to 0 at wave start (`flow.py:2729`).
- The override needs the row ticked. The `open_needs_human` test in `_refuse` is only
  right because C6 passed just before it, and it did.
- The CLI now deletes the decision file (`cli.py:1546`).
- Tree errors are caught before the general `IntegrationError` fallback
  (`flow.py:321-323`).
- The `_back_on` reset runs on every exit of `same_wave_clash`, raising exits included.
  Errors are chained with `raise … from`.
- The `publish._checkout_base` refactor gives the same result as the old inline
  `wave_stacked and bool(wave_tip)` rule.
- The trial condition at `flow.py:3304-3307` matches the fold's own condition (`dry` is
  `publisher.mode == "stub"`, `flow.py:3366`).

The new test file drives the real `_drive_wave` → `_apply_decision` path and covers every
leg in the brief, plus the three iteration-6 legs and the iteration-7 CLI leg. C4 shows
11 of 14 red before the fix. The 3 green ones are the controls that should be green on
`main`: (b), (g), and the plain C6 case.

Findings (all minor, none gating):

- `template/src/pdca_harness/integrate.py:812` / `:829-831` — efficiency. Every accept on
  a non-final wave runs a full `_fetch` of origin and the base remote. It rebuilds every
  accepted sibling's would-be commit and runs the merge chain twice (`alone` and `held`),
  with `_held_by` trials on top. For a wave of N bundles accepted one by one, that is N
  fetches and about N² commit builds. This is fine for today's wave sizes. If waves grow,
  two things could be cached per wave: `alone` (it only changes on an override) and the
  built commits keyed by bundle. Not worth doing in this slice.
- `template/src/pdca_harness/flow.py:317` with `integrate.py:793` — small duplication.
  `_refused_for_wave` resolves the target only to look up `folded_tips`, and
  `same_wave_clash` resolves it again. Passing `folded_tips` (or the resolved tip) down
  once would drop the second call. Cosmetic.
- `template/src/pdca_harness/integrate.py:807` — simplification. An `ExitStack` that holds
  one lock adds nothing over `with integ_lock(wt) as got:`. The brief asked to follow
  `_fold_lines`, which needs the stack because it holds one lock per target. Here there is
  only one target. Cosmetic.
- `template/src/pdca_harness/state.py:159` — adding `SAME_WAVE_REFUSAL` to
  `DOWNSTREAM_OF_BRIEF` almost never does anything. Both decision routes call
  `consume_decision` (`flow.py:233`, `cli.py:1546`), and that deletes the record before an
  iterate archives the attempt. So it is archived only on an iterate that records no
  decision (a reassemble or an auto-iterate). That is harmless and arguably correct. I note
  it only so no one relies on the archive copy existing.
- `template/src/pdca_harness/flow.py:474` — wording. The wave-end line says the session
  "recorded nothing new". It also prints when the session wrote `accept` again without
  ticking the row (C6 then blocks it). "recorded nothing that settled it" would be
  accurate in both cases. Cosmetic.

No NEEDS-HUMAN items.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] C3 Change — Approve broadening the failure policy to refuse disjoint bundles after integration-tree errors — the brief promises acceptance without shared paths, but the new exception branch refuses regardless; brief.md:37; target/template/src/pdca_harness/flow.py:321; target/template/tests/test_flow_same_wave_accept_trial.py:332.
- [ ] C5 Causal adequacy — Fix quoted-path parsing and add a real-git regression — with café.txt and an injected trial failure, the fallback sees no paths and both conflicting bundles become COMPLETE and publish; target/template/src/pdca_harness/integrate.py:874; target/template/src/pdca_harness/waves.py:329; review-quoted-path.log:1.
- [x] T5 Judgment — Confirm merged and closed/rejected prior art by every affected path — this target has one synthetic base commit and no remotes, while the brief reports merged history for the earlier test and closed work for flow/integrate only; review-prior-art.log:1; brief.md:46; target/template/src/pdca_harness/cli.py:1546.
- [x] Validation — fitness-to-purpose — Decide whether non-final-wave-only protection and the exercised publishing model meet the intended workflow — last-wave conflicts remain allowed, and gh plus publishing mechanics were stubbed, so live GitHub PR behavior was not exercised; target/docs/07-crosscutting.md:761; target/template/tests/test_flow_same_wave_accept_trial.py:117; target/template/tests/test_flow_same_wave_accept_trial.py:138.
- [ ] **Following the refusal's own step inside the session wastes a full re-plan and rebuild in the same run, which is then refused again.** The row and the wave-end line say "declare `Conflicts with: 10` in issue_11's brief, then iterate-plan it" (`template/src/pdca_harness/flow.py:388-395`). Inside a flow sign-off session, the natural way to do that is to write `iterate-plan` into the decision file. `_apply_decision` applies an iterate-plan at once, even in the batch sweep (`flow.py:238-239`). The wave's next pass then runs the interactive Plan pre-pass and rebuilds the bundle (`flow.py:2734`, `flow.py:771-781`). That rebuild happens **in the same wave, on the same base, still without 10's change**, because waves and stack bases are fixed at the start of the run. So the rebuilt 11 conflicts again and is refused again. The run then parks it with the same advice to declare `Conflicts with: 10`, which its new brief already declares. I reproduced this with a scratch probe: the session writes `iterate-plan` + rationale, and the stubbed Plan step re-plans with `conflicts_with="10"`. Result: `built == ['issue_10','issue_11','issue_12','issue_11','issue_20']`, 11 ends AWAITING_SIGNOFF, and the stderr shows a second "cannot accept: … conflicts with issue_10's" after the "iterate-to-Plan — archiving" line. In a real run, that costs one interactive Plan session, a Do run, a Check run and another sign-off session, all for nothing in this run. The brief's design says recovery comes "the next run", and it lists same-run re-sequencing as a follow-up. It does not say whether a trial-refused bundle's iterate-plan should be held back until the next run (parked at UNPLANNED for the rest of this wave), or whether the step text should warn that it only helps on the next run. That is a scope call. Once it is made, the builder should also stop the parked line from telling the human to declare a `Conflicts with` the brief already carries.
- [ ] **Leg (f) is vacuous, or it hides a second change.** The brief says: "The new row is a HUMAN-kind item (`assemble.HUMAN`). On its own it does not make `autoiterate.eligible` true." But the row is written with `signoff.ensure_needs_human_item`, which only splices a plain `- [ ] {item}` line into SUMMARY.md (`signoff.py:213`). It has no kind. Auto-iterate never reads SUMMARY §6. `_maybe_auto_iterate` classifies `assemble.collect_needs_human(d, cfg)` (`flow.py:340`), which rebuilds items from `check-gates.json`, `check-review.md` and `check-advisory-*.md` (`assemble.py:389-413`). So the row can never be "HUMAN-kind", and it cannot affect `eligible` at all. As written, (f) is green before and after the change: it cannot be falsified. A Do that tries to make it meaningful would have to add a new artifact source to `collect_needs_human`, which is a hidden second change. A related gap: if B also has an IMPL finding, an auto-iterate or iterate-do rebuild reassembles §6 from artifacts and drops the refusal row (and any tick on it). The brief does not say whether that is intended. Revise (f) to assert something observable, or drop it.
- [ ] **Leg (d) "a re-run" does not reach the #674 same-wave hold it asserts.** Leg (a) leaves A COMPLETE. On a re-run, finished ids are skipped (`07-crosscutting.md:747-749`), so A is no longer a same-wave sibling of B. B is then judged against the line, not the wave. The docs say that case is either #747's line rule or "still stops the run" (`07-crosscutting.md:730`). The carry only starts from a plain `Depends on` (:716), so A may not be on the line at all. If no later wave follows, no fold runs. Then "The fold then holds B as `"conflict"` exactly as on `main` (#674)" is not what happens. Pin the override to the same run: the next pass's session ticks the row and re-accepts (`_drive_wave` re-offers C6-refused bundles, `flow.py:2521`). Or state the exact re-run topology and the expected fold outcome.
- [ ] **The brief contradicts itself about Do's inputs.** Line 3 says "Do reads ONLY this file". Line 41 then tells Do to reuse mechanics from `/home/eddie/pdca/pdca-pdca/results/issue_395/iteration-v5/patch.diff`, an absolute path outside the target and the bundle, and to fix "two open findings on it". Line 36 tells Do to ignore a stray `test_flow_same_wave_prepublish.py` "in this bundle directory". Either Do may read the v5 patch, and the "ONLY" line is wrong, or it may not, and the two v5 findings (the discarded retry result, and the build loop outside `try/finally`) are guidance Do cannot act on. The stray rejected-design test should also be removed or named as excluded from the C4 gate. Otherwise a red/green run may pick it up. I could not check this: the bundle directory is not among my inputs.
- [ ] **The cost of a refused bundle is understated: the wave drives B until its whole pass allowance is spent.** C6 refusal returns `"blocked"` before the decision file is unlinked (`flow.py:177-179` vs :205). So each later pass re-applies the stale accept, is refused again, and queues B for another sign-off session (`flow.py:2516-2532`). B is never terminal, so `_drive_wave` only exits on budget (`flow.py:2533-2543`; default `max_passes = 20`, `config.py:309`). Then it prints "raise [driver].max_passes", which is wrong advice for a conflict refusal. The brief's Design calls this "existing C6 behaviour … not changed here". But this change makes the state reachable without any human-visible finding: an undeclared conflict, two accepts. The criterion should pin how many sessions B is offered and what B's wave-end message says (it should name the conflict step, not the pass budget). Otherwise the human sees up to 20 re-prompts and a misleading hint, and no leg would catch it.

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
- Iteration delta (if iterating): Keep the design; fix two things from this round's reviews: 1. Quoted diff paths (C5): waves.diff_files (waves.py:329) cannot parse Git-quoted headers such as `diff --git "a/caf\303\251.txt" "b/caf\303\251.txt"`, so when the trial cannot run, the same_wave_overlap fallback (integrate.py:874) sees no paths and accepts a conflicting bundle. Decode Git-quoted paths, and treat an unparsable/unknown footprint as "may overlap" (refuse), not as "disjoint". Add a real-git regression leg with a non-ASCII file name and an injected trial failure. 2. Refused bundle re-plan must wait until the next run (adversary finding): an iterate-plan on a trial-refused bundle inside a flow session currently re-plans and rebuilds it in the same wave, on the same base, where it conflicts and is refused again — a wasted Plan+Do+Check+sign-off cycle. Hold that bundle's re-plan back for the rest of this run (park it, no Plan/Do/Check in this wave) so it is re-planned on the next run, and make the row / wave-end text say so; do not tell the human to declare a `Conflicts with` the brief already carries. Add a test leg: refused B, session writes iterate-plan, B is not rebuilt in the same run.
- By / date: Eduard Ralph / 2026-10-23

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 4 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
