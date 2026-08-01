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
- T3 runtime: render/update-compat + offline driver suites: fail — /tmp/tmpqyo8kh_t/results/issue_500/split-proposal.md
- T4 PR body has a user-impact opener + tracker id in both artifacts: pass — pdca-pdca contribcheck
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Task under review: add opt-in host-only CI commands that run against the reconstructed base plus `patch.diff` and block publication before any push on every non-zero result.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The acceptance boundary is explicit: opted-in commands judge the patched tree before push, while an absent declaration preserves existing behavior (`template/pdca.toml.jinja:854`). |
| C2 Reproduction (red pre-fix) | PASS | The added test module fails against pre-fix production because its required host-CI normalizer is absent, while its failure/no-push assertions exercise the intended observable boundary (`template/tests/test_host_ci.py:43`, `template/tests/test_host_ci.py:188`). |
| C3 Change | FAIL | A fresh pre-push failure is written only to `host-ci.json`, but §6 collection reads gates/reviews/dependencies and never that record; the bundle can therefore remain signed off without the new failure reaching the required human decision point (`template/src/pdca_harness/publish.py:826`, `template/src/pdca_harness/assemble.py:176`). |
| C4 Verification (red→green) | PASS | Independent isolated runs were red with the test on pre-fix production and green with the patch (22/22 focused tests), including no-push, exit-77, stale-base, late-base, and certified-parent cases (`template/tests/test_host_ci.py:188`, `template/tests/test_host_ci.py:396`). |
| C5 Causal adequacy | PASS | The prior stale-base cause is removed by fetching and resolving a commit SHA, testing base-plus-patch at that SHA, and pinning checkout to the same SHA; no capability-probe or present-capability runtime guard was added (`template/src/pdca_harness/publish.py:762`, `template/src/pdca_harness/publish.py:784`). |
| T1 Structure | PASS | Configuration normalization, Check execution, publish enforcement, and tree materialization remain in their existing owning modules with a focused integration test (`template/src/pdca_harness/config.py:658`, `template/src/pdca_harness/worktree.py:535`). |
| T2 Shape | PASS | Docs lint and the 22-page link audit reran green, and a real Copier prior-release update preserved parseable config and instance edits around the changed gates table (`tests/test_update_compat.py:204`, `template/pdca.toml.jinja:823`). |
| T3 Runtime | PASS | The asserted manifest red was not reproduced: the full offline template suite exited 0 and all seven Copier render/update tests passed with the installed Copier interpreter (`tests/test_update_compat.py:232`, `template/tests/test_host_ci.py:472`). |
| T4 Contribution | NEEDS-HUMAN | Re-run the contribution gate with `commit-msg.txt` and `pr-description.md` — those required inputs were not supplied, so the recorded green cannot be independently confirmed before it controls publish (`template/pdca.toml.jinja:834`). |
| T5 Judgment | NEEDS-HUMAN | Decide whether closed/rejected work duplicates this affected publish seam — local merged/all-ref history by affected path showed no `#311`/host-CI implementation, but the GitHub closed-work query could not run because network access was unavailable (`template/src/pdca_harness/publish.py:796`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether a real instance’s declared host-CI commands and sign-off recovery workflow are operationally fit — toy real-git tests prove mechanics, but the reproduced publish-time §6 visibility gap affects how humans discover and clear a late failure (`template/tests/test_host_ci.py:417`, `template/src/pdca_harness/assemble.py:195`). |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T4 Contribution — Re-run the contribution gate with `commit-msg.txt` and `pr-description.md` — those required inputs were not supplied, so the recorded green cannot be independently confirmed before it controls publish (`template/pdca.toml.jinja:834`).
- [x] T5 Judgment — Decide whether closed/rejected work duplicates this affected publish seam — local merged/all-ref history by affected path showed no `#311`/host-CI implementation, but the GitHub closed-work query could not run because network access was unavailable (`template/src/pdca_harness/publish.py:796`).
- [x] Validation — fitness-to-purpose — Decide whether a real instance’s declared host-CI commands and sign-off recovery workflow are operationally fit — toy real-git tests prove mechanics, but the reproduced publish-time §6 visibility gap affects how humans discover and clear a late failure (`template/tests/test_host_ci.py:417`, `template/src/pdca_harness/assemble.py:195`).

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
- By / date: Eduard Ralph / 2026-07-31

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
- T3 suite gate evidence leaked a different bundle's /tmp artifact (issue_500 split-proposal) into issue_311's gate record — check T3 runner isolation / cross-bundle contamination.
- Correction to previous bullet: issue_500 is a test fixture inside the driver suite, not a real bundle — actual Act items: (a) non-reproducible T3 red (flaky/environmental; two independent reruns green), (b) T3 gate's evidence extractor captured arbitrary fixture stdout as its evidence line.
