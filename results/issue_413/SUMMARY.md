# Result — issue 413 / merge-mode-full-check-rollup

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: Two-part, one discipline. (Code) `merge._merge_one`
  (`template/src/pdca_harness/merge.py:42-96`) relies on `gh pr merge` to fail closed on
  "a failing required check" (`merge.py:86-88`) — which only covers checks the HOST repo
  marks required in branch protection. A host with thin protection lets a non-final wave
  PR ready+merge (`merge.py:73-82`) while its real gates are red or still running: a red
  non-required CI job or an unfinished run does not stop the merge, so the next wave
  builds on a base that never went green. (Docs) `template/docs/fork-discipline.md.jinja:46-47`
  states flatly that the automation "never marks a PR ready and never merges" — false
  under the harness's own `wave_mode = "merge"` (#279, `merge.py:73` and `merge.py:82`
  do both for non-final waves), so instances that enable merge mode inherit a discipline
  doc that no longer describes their system.
- Success criterion: `_merge_one` merges only a PR whose FULL check rollup is green
  at merge time: the rollup is read (also) AFTER `gh pr ready` and immediately before
  `gh pr merge` — marking a draft ready can itself trigger `ready_for_review` CI, so a
  rollup observed only pre-ready cannot guarantee green-at-merge. The gate refuses
  (non-zero return, STOP, `gh pr merge` never invoked) on any failing check and on any
  pending/queued check (wait-or-STOP, never merging past an in-flight run); refusing
  after ready is safe because a re-run resumes idempotently (`merge.py:63-65`). Rollup
  edge semantics are defined, not left to chance: an EMPTY rollup (no checks reported)
  refuses under the default — absence of evidence is not green — while skipped/neutral
  checks count as completed non-failures and do not block. A config knob
  (`merge_requires = "all" | "required"`, default `"all"`, parsed from `[driver]`)
  restores host-config semantics — including merging with an empty rollup — only on
  explicit opt-in. The fork-discipline template scopes the never-ready/never-merge
  claim: it binds the model leaves unconditionally and every final-wave PR; under
  `wave_mode = "merge"` the deterministic driver readies+merges non-final waves at the
  wave boundary, guarded by per-bundle human sign-off before publish and the check-rollup
  gate. Shipped tests assert the refusal paths.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: the rollup gate in `_merge_one` (+ the `merge_requires` knob in config.py
  and its `[driver]` documentation in pdca.toml.jinja) and the scoped §2 claim in
  fork-discipline.md.jinja / out of scope: any change to the final-wave path (drafts stay
  the human's to ready), the instance-side INTEGRATION.md wording (already fixed
  downstream, getwyrd/wyrd-pdca#198), watching/polling for pending checks to clear
  (refusing is enough; re-run resumes idempotently per `merge.py:63-65`).

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: pass — C4 PASS: red without the fix, green with it
- C5 Causal adequacy: none — reviewer + human sign-off

## 4. Conformance (Check — stack)
- T1 Structure: none — (no gate configured)
- T2 shape: docs lint + site render link audit: pass — render_site: link audit OK
- T3 runtime: render/update-compat + offline driver suites: pass — == T3: root suite OK, driver suite OK
- T4 PR body has a user-impact opener + tracker id in both artifacts: pass — ./scripts/pdca contribcheck
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Reviewing issue #413: require a post-ready full-check-rollup gate before merge-mode advances a wave, add the explicit host-required escape hatch, and correct the fork-discipline claim.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The acceptance boundary distinguishes the default full-rollup policy from the explicit host-required opt-in and defines fail, pending, empty, skipped, and post-ready semantics, so expected merge safety is decidable (`template/pdca.toml.jinja:126`). |
| C2 Reproduction (red pre-fix) | PASS | A clean `HEAD` snapshot with only the new tests applied produced 8 failures and 2 errors, including red, pending, empty, and post-ready-triggered checks merging, so the original host-protection gap is independently reproduced (`template/tests/test_merge.py:241`, `template/tests/test_merge.py:297`). |
| C3 Change | FAIL | The operator must not be told that every merge-mode boundary requires a full-green rollup while the supported `merge_requires = "required"` setting skips that gate; the fork-discipline promise is therefore contradictory and can overstate safety (`template/docs/fork-discipline.md.jinja:51`, `template/docs/fork-discipline.md.jinja:57`, `template/pdca.toml.jinja:138`). |
| C4 Verification (red→green) | PASS | The focused suite changed from 8 failures plus 2 errors on base-with-new-tests to 21/21 green on the patch, the full driver suite passed 1,685 tests, and live read-only probes classified real GitHub rollups green and failing without reaching merge (`template/src/pdca_harness/merge.py:87`, `template/tests/test_merge.py:241`). |
| C5 Causal adequacy | PASS | The host branch-protection assumption is removed at the actual ready-to-merge boundary, with the rollup read ordered between ready and merge; no capability probe or symptom guard was introduced (`template/src/pdca_harness/merge.py:158`, `template/src/pdca_harness/merge.py:175`, `template/src/pdca_harness/merge.py:196`). |
| T1 Structure | PASS | The policy is narrowly separated into a rollup classifier and one merge-boundary branch, while configuration defaults and loading remain centralized, limiting the safety rule to its owning module (`template/src/pdca_harness/merge.py:66`, `template/src/pdca_harness/config.py:703`). |
| T2 Shape | PASS | The docs renderer produced 22 pages with a clean link audit, and the configuration template presents both policy values next to the existing merge controls (`template/pdca.toml.jinja:123`, `docs/07-crosscutting.md:491`). |
| T3 Runtime | NEEDS-HUMAN | Supply `copier` and decide whether render/update compatibility is green—the entire 7-test root suite skipped because that dependency was absent, which matters because the most instance-edited template file changes here (`tests/test_update_compat.py:15`, `template/pdca.toml.jinja:126`). |
| T4 Contribution | NEEDS-HUMAN | Confirm `commit-msg.txt` and `pr-description.md` contain a user-impact opener and tracker reference `#413`—neither artifact nor the asserted runner was supplied, and Check-time code explicitly says those publish artifacts do not yet exist, so release traceability is not independently established (`template/src/pdca_harness/publish.py:753`). |
| T5 Judgment | NEEDS-HUMAN | Decide whether the added repository-level process exposition is acceptable beyond the brief's scoped template docs—it changes the process baseline (`docs/07-crosscutting.md:491`); affected-path auditing found no open or rejected competing PR and no merged `gh pr checks` implementation. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Approve unattended-merge fitness only after a disposable real PR is readied with a `ready_for_review` job still pending, a non-required failure, and then no checks, confirming STOP/no merge under `all` and the intentional bypass under `required`; live probes covered green and failing rollups but not those merge-time topologies (`template/src/pdca_harness/merge.py:167`). |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T3 Runtime — Supply `copier` and decide whether render/update compatibility is green—the entire 7-test root suite skipped because that dependency was absent, which matters because the most instance-edited template file changes here (`tests/test_update_compat.py:15`, `template/pdca.toml.jinja:126`).
- [x] T4 Contribution — Confirm `commit-msg.txt` and `pr-description.md` contain a user-impact opener and tracker reference `#413`—neither artifact nor the asserted runner was supplied, and Check-time code explicitly says those publish artifacts do not yet exist, so release traceability is not independently established (`template/src/pdca_harness/publish.py:753`).
- [x] T5 Judgment — Decide whether the added repository-level process exposition is acceptable beyond the brief's scoped template docs—it changes the process baseline (`docs/07-crosscutting.md:491`); affected-path auditing found no open or rejected competing PR and no merged `gh pr checks` implementation.
- [x] Validation — fitness-to-purpose — Approve unattended-merge fitness only after a disposable real PR is readied with a `ready_for_review` job still pending, a non-required failure, and then no checks, confirming STOP/no merge under `all` and the intentional bypass under `required`; live probes covered green and failing rollups but not those merge-time topologies (`template/src/pdca_harness/merge.py:167`).

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
- By / date: Eduard Ralph / 2026-08-10

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
