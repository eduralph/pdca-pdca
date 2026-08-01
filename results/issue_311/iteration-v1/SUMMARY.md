# Result — issue 311 / host-ci-gate

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: the harness can express "host CI jobs the delegated gate runner does not
  cover" — an instance declares host-only CI commands and the cycle runs them against
  the tree with `patch.diff` applied, before publish pushes anything, so a bundle can
  no longer pass Check green and open a PR that immediately fails a required status
  (observed four times in the wyrd instance, always the `typos` job: getwyrd/wyrd#595,
  #564, #569, #394).
- Success criterion: with a declared host-CI command configured, (a) a command that
  exits non-zero against the patched tree blocks publish — no branch is pushed, no PR is
  opened — and the failure is recorded with the command named; (b) a command that exits 0
  leaves publish behaviour unchanged; (c) an instance that declares nothing is
  byte-identical to today. Demonstrable by C4-verify: the shipped unit test asserts all
  three against a stub command, red on current `main` (publish today consults only
  `_t4_passes`, which runs with `cwd=cfg.root` *before* the patch is applied — verified at
  `template/src/pdca_harness/publish.py:101` and `:187-192`).
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: proposal 1 of the issue only — a declared list of host-only CI commands
  (instance config, e.g. a `[gates.host_ci]`-shaped table; exact key naming is Do's call)
  that the harness runs as a pre-publish gate against a tree with `patch.diff` applied
  (isolated worktree, the same machinery the verify leg / bundle-scoped gates already
  use), closing the T4 slot's pre-apply blindness. / out of scope: proposal 2 (the
  composition audit that parses the host's workflow files and warns about uncovered
  always-on jobs) — file it as its own follow-up if wanted; also out of scope: any change
  to the wyrd instance itself (already worked around host-side via getwyrd/wyrd#599).

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: new-feature
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
- T3 runtime: render/update-compat + offline driver suites: fail — /tmp/tmpo3p54blm/results/issue_500/split-proposal.md
- T4 PR body has a user-impact opener + tracker id in both artifacts: pass — pdca-pdca contribcheck
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Review task: add opt-in host-only CI commands that run against the patched tree and block publication before any branch or PR is pushed.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief gives falsifiable outcomes for failing, passing, and absent configuration and bounds the work to host-CI command execution. |
| C2 Reproduction (red pre-fix) | PASS | On exact target `HEAD`, the shipped regression test is red without the production hunks and becomes 18/18 green with the patch; its no-push oracle is grounded at `template/tests/test_host_ci.py:161`. |
| C3 Change | FAIL | Every declared non-zero command is required to block, but the shipped behavior deliberately publishes after exit 77 and also permits a failing `gating = false` row, reopening the promised blind spot (`template/tests/test_host_ci.py:200`, `template/src/pdca_harness/publish.py:780`). |
| C4 Verification (red→green) | FAIL | The configured C4 oracle independently exits 1 because it is still an explicit unimplemented skeleton, so its recorded green is not reproducible even though the test module itself is red→green (`template/engine/scripts/run-verify.sh:50`). |
| C5 Causal adequacy | FAIL | A warm gate worktree intentionally does not fetch, while publish fetches afterward; the reproduced remote-advance case passed host CI on the stale base but failed the same command on the fetched base plus patch, so the gate can certify a tree other than the one pushed (`template/src/pdca_harness/worktree.py:238`, `template/src/pdca_harness/publish.py:270`). |
| T1 Structure | PASS | The change remains localized to additive config normalization, gate orchestration, the pre-push seam, documentation, and one focused test module (`template/src/pdca_harness/config.py:657`). |
| T2 Shape | PASS | Python compilation, documentation lint, and the 22-page render/link audit all pass; the user-facing configuration shape is documented at `template/pdca.toml.jinja:854`. |
| T3 Runtime | NEEDS-HUMAN | Decide whether the recorded `run-suite.sh` red is a real clean-environment regression — that exact runner is absent at the target, while the available offline runtime suite passes 1,332/1,332, and the discrepancy affects release confidence (`template/Makefile:73`). |
| T4 Contribution | NEEDS-HUMAN | Decide whether the contribution opener and tracker references are acceptable — the required commit-message and PR-body artifacts were not supplied, so the recorded contribution result cannot be independently rerun (`template/pdca.toml.jinja:850`). |
| T5 Judgment | NEEDS-HUMAN | Confirm no closed/rejected prior work or project-specific human-only item conflicts — affected-path merged history contains no host-CI/#311 work, but remote review metadata and the referenced `INTEGRATION.md` §4 are unavailable, so duplication cannot be mechanically excluded. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether this policy actually closes the host-CI parity gap — non-zero bypasses and stale-base certification can still open a PR whose required host status fails, which defeats the intended operational outcome (`template/src/pdca_harness/publish.py:747`, `template/src/pdca_harness/worktree.py:238`). |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T3 Runtime — Decide whether the recorded `run-suite.sh` red is a real clean-environment regression — that exact runner is absent at the target, while the available offline runtime suite passes 1,332/1,332, and the discrepancy affects release confidence (`template/Makefile:73`).
- [ ] T4 Contribution — Decide whether the contribution opener and tracker references are acceptable — the required commit-message and PR-body artifacts were not supplied, so the recorded contribution result cannot be independently rerun (`template/pdca.toml.jinja:850`).
- [ ] T5 Judgment — Confirm no closed/rejected prior work or project-specific human-only item conflicts — affected-path merged history contains no host-CI/#311 work, but remote review metadata and the referenced `INTEGRATION.md` §4 are unavailable, so duplication cannot be mechanically excluded.
- [ ] Validation — fitness-to-purpose — Decide whether this policy actually closes the host-CI parity gap — non-zero bypasses and stale-base certification can still open a PR whose required host status fails, which defeats the intended operational outcome (`template/src/pdca_harness/publish.py:747`, `template/src/pdca_harness/worktree.py:238`).

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
- Iteration delta (if iterating): Rejected on the advisory findings (brief unchanged): 1. C5 — stale-base certification (the substantive defect): the publish-leg host-CI run reuses a warm gate worktree that deliberately does not fetch (worktree.py:238) while the push path fetches afterward (publish.py:270); reviewer reproduced host CI green on the stale base but red on fetched base + patch, so the gate can certify a tree other than the one pushed. Fix: the pre-push host-CI reconstruction must fetch/pin the same base commit the push will use, with a test covering the base-advanced-since-Check case. 2. C3 — non-zero bypasses: the brief's criterion (a) says a non-zero command blocks publish, but exit 77 and gating=false rows publish anyway (publish.py:780). The human did not bless these carve-outs this round; the rebuild should either make every non-zero declared command block publish per the brief's letter, or surface the carve-out question explicitly for sign-off rather than shipping it as a default. Note: the reviewer's C4 FAIL appears to be an oracle-path artifact (it ran the target's template skeleton run-verify.sh, not the instance's configured gate, and itself confirms the test module is red->green); the deterministic C4 gate passed.
- By / date: Eduard Ralph / 2026-07-31

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
