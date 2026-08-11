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

Reviewing issue #413: make merge-mode non-final waves merge only on a green full check rollup, while accurately documenting the driver’s ready/merge exception.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The acceptance decision is explicit about default full-rollup, empty/pending/failure, post-ready timing, and opt-in host-required semantics, with the operative policy grounded at `template/src/pdca_harness/merge.py:167` and `template/src/pdca_harness/config.py:361`. |
| C2 Reproduction (red pre-fix) | PASS | The defect is causally reproduced: with production/docs hunks reversed but all 21 tests retained, 21 tests ran and yielded 8 failures plus 2 errors, including red/pending/empty rollups reaching merge instead of STOP (`template/tests/test_merge.py:241`). |
| C3 Change | PASS | The scope decision is settled: the five affected files are exactly the configured merge policy, parser, merge boundary, tests, and discipline documentation named by the brief; no unrelated behavior or Plan re-entry is present (`template/src/pdca_harness/merge.py:66`, `template/docs/fork-discipline.md.jinja:46`). |
| C4 Verification (red→green) | PASS | Independent red→green is confirmed: the retained 21-test slice was red without production changes and 21/21 green with them; the complete offline suite, docs lint/render link audit, `git diff --check`, and Python compilation also exited 0 (`template/tests/test_merge.py:241`). |
| C5 Causal adequacy | PASS | The root-cause decision is satisfied: the merge boundary reads the full rollup after ready and refuses every non-green classification before `gh pr merge`, directly removing reliance on thin branch protection rather than adding an optional-capability probe (`template/src/pdca_harness/merge.py:167`). |
| T1 Structure | PASS | The policy remains localized as a small rollup classifier plus one merge-boundary guard, while config parsing is kept with peer driver settings (`template/src/pdca_harness/merge.py:66`, `template/src/pdca_harness/config.py:697`). |
| T2 Shape | PASS | Source and documentation shape are mechanically clean: `git diff --check`, Python compilation, docs lint, and a 22-page render/link audit passed; the public knob is documented alongside its merge-mode peers (`template/pdca.toml.jinja:126`). |
| T3 Runtime | PASS | Runtime compatibility is independently supported by 21/21 focused tests and the full offline suite; installed `gh` 2.97.0 exposes the five handled buckets, and upstream CLI behavior confirms an already-ready retry exits successfully (`template/src/pdca_harness/merge.py:44`, `template/tests/test_merge.py:297`). |
| T4 Contribution | NEEDS-HUMAN | Confirm `commit-msg.txt` and `pr-description.md` contain a user-impact opener and tracker reference `#413` — neither artifact was supplied, so the asserted contribution-gate PASS cannot be independently reproduced and release traceability depends on that check. |
| T5 Judgment | PASS | The prior-art decision is mechanically settled by affected path: merged history contains #279’s ready-before-merge work but no rollup gate, and the repository’s sole closed-unmerged PR touched only `README.md`, so no competing rejected implementation affects these files (`template/src/pdca_harness/merge.py:152`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether fail-closed `all` as the default and explicit `required` opt-out match real merge-mode operator expectations — this policy can intentionally STOP waves on empty or in-flight CI, so operational fitness remains a sign-off judgment (`template/pdca.toml.jinja:131`). |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T4 Contribution — Confirm `commit-msg.txt` and `pr-description.md` contain a user-impact opener and tracker reference `#413` — neither artifact was supplied, so the asserted contribution-gate PASS cannot be independently reproduced and release traceability depends on that check.
- [ ] Validation — fitness-to-purpose — Decide whether fail-closed `all` as the default and explicit `required` opt-out match real merge-mode operator expectations — this policy can intentionally STOP waves on empty or in-flight CI, so operational fitness remains a sign-off judgment (`template/pdca.toml.jinja:131`).

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
- Iteration delta (if iterating): Auto-iterate (round 2): Check found implementation-level items only, no architectural judgment required — T4 Contribution — Confirm `commit-msg.txt` and `pr-description.md` contain a user-impact opener and tracker reference `#413` — neither artifact was supplied, so the asserted contribution-gate PASS cannot be independently reproduced and release traceability depends on that check.
- By / date: auto-iterate / 2026-08-10

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
