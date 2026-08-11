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

Reviewing issue #413: make non-final merge-mode PRs pass the full post-ready check rollup before merge, while documenting the explicit host-required-checks opt-out and the automation exception.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The acceptance boundary is decision-complete: protect later waves with a post-ready full-rollup gate, define empty/pending/skipping semantics, and preserve host-only behavior solely by explicit opt-in (`template/src/pdca_harness/merge.py:121`). |
| C2 Reproduction (red pre-fix) | PASS | A direct drive against the exact base returned 0, made zero rollup reads, and invoked merge despite a failing-rollup stub, reproducing the unsafe path that the added refusal case targets (`template/tests/test_merge.py:208`). |
| C3 Change | PASS | The default now fails closed before merge for every non-green classification, while the parser constrains the only compatibility escape hatch to `required`, so deployment policy cannot become loose through an unknown value (`template/src/pdca_harness/merge.py:136`; `template/src/pdca_harness/config.py:701`). |
| C4 Verification (red→green) | PASS | Base production plus patched tests ran 18 and errored because the required config field was absent; patched production passed all 18 merge tests and the full driver suite, while the direct base drive separately proved the unsafe merge symptom (`template/tests/test_merge.py:208`). |
| C5 Causal adequacy | PASS | The change removes reliance on thin host branch protection by reading the full rollup at the merge boundary itself; it adds no capability probe or eager-load fallback that would trigger the symptom-guard smell test (`template/src/pdca_harness/merge.py:136`). |
| T1 Structure | PASS | Policy parsing remains in `Config`, rollup classification and enforcement remain in the merge module, and behavioral coverage remains in the existing merge suite, with no duplicate execution path (`template/src/pdca_harness/config.py:361`; `template/src/pdca_harness/merge.py:63`; `template/tests/test_merge.py:206`). |
| T2 Shape | PASS | Independent docs lint and a 22-page render/link audit passed, and the corrected exception plus operator knob are placed at the existing discipline and driver-policy seams (`template/docs/fork-discipline.md.jinja:44`; `template/pdca.toml.jinja:126`). |
| T3 Runtime | PASS | After installing `copier` in an isolated temporary environment, all 7 render/update-compat tests, all 18 targeted merge tests, and the complete offline driver suite passed; the real config-loader coverage reaches the new policy (`template/tests/test_merge.py:361`). |
| T4 Contribution | NEEDS-HUMAN | Confirm the commit and PR artifacts contain a user-impact opener and tracker reference for #413 — those artifacts and the rendered `contribcheck` entry point were not supplied, so the asserted gate result cannot be independently reproduced. |
| T5 Judgment | PASS | Affected-path history found no earlier rollup implementation, GitHub reported no open PRs, and the sole closed-unmerged PR touched only `README.md`, so no prior or competing contribution changes this patch's disposition (`template/src/pdca_harness/merge.py:63`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether default refusal on empty or in-flight rollups, with an explicit host-required-only opt-out, is the right availability-versus-safety policy for merge-mode deployments — this determines whether the restored invariant fits real operator expectations (`template/src/pdca_harness/config.py:361`). |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T4 Contribution — Confirm the commit and PR artifacts contain a user-impact opener and tracker reference for #413 — those artifacts and the rendered `contribcheck` entry point were not supplied, so the asserted gate result cannot be independently reproduced.
- [ ] Validation — fitness-to-purpose — Decide whether default refusal on empty or in-flight rollups, with an explicit host-required-only opt-out, is the right availability-versus-safety policy for merge-mode deployments — this determines whether the restored invariant fits real operator expectations (`template/src/pdca_harness/config.py:361`).

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
- Iteration delta (if iterating): Auto-iterate (round 1): Check found implementation-level items only, no architectural judgment required — T4 Contribution — Confirm the commit and PR artifacts contain a user-impact opener and tracker reference for #413 — those artifacts and the rendered `contribcheck` entry point were not supplied, so the asserted gate result cannot be independently reproduced.
- By / date: auto-iterate / 2026-08-10

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
