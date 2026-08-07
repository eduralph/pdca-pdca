# Result — issue 396 / trailing-flag-swallows-interactive-seed

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: The template's REMOTE CONTROL doc (`template/pdca.toml.jinja:548-552`) and
  `template/docs/INTEGRATION.md.jinja:156-157` both instruct "APPEND the flag to the
  argv line", with the example showing `--remote-control` as the LAST argv token. But
  the driver seeds every interactive leaf as `subprocess.run(argv + [seed])`
  (`template/src/pdca_harness/leaves.py:379`, via `_seed_positional`,
  `leaves.py:183-216`, #313) — the prompt is the FINAL positional — and
  `--remote-control` takes an optional `[name]` value. Following the doc verbatim makes
  the flag consume the entire seed prompt as the RC session name: Remote Control fails to
  start ("check the debug log") and the REPL opens with no seed. Hit in practice on this
  instance the first time the flow reached a planner after enabling RC
  (eduralph/pdca-pdca#19; worked around there by moving the flag before `--agent`).
- Success criterion: (1) Docs: the example in pdca.toml.jinja and the INTEGRATION
  template place the flag NON-last and say why — any flag with an optional value must
  never sit last in an interactive leaf's argv, because the seed is appended as a
  positional after it. (2) Driver: when seeding an interactive leaf of a family whose CLI
  supports an end-of-options separator, the driver appends the seed after it
  (`argv + ["--", seed]`), declared as a families-profile bit (claude: `--`; a family
  without the bit keeps the current bare-positional spawn) — so NO trailing
  optional-value flag can ever swallow the seed, whatever an instance puts in its argv.
  A shipped test asserts the interactive claude-family spawn carries the separator
  between the configured argv and the seed.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: the two doc examples + the interactive-seed separator (families-profile bit
  in `families.py`, applied at the one spawn site in `leaves.py`) / out of scope: the
  headless stdin path (`leaves.py:384+`, not affected — the prompt rides stdin there),
  any change to `_seed_positional`'s spill logic, enabling Remote Control by default,
  non-claude families' separator support (ship the bit unset for them unless Do can
  verify a vendor's CLI accepts `--`).

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
- T3 runtime: render/update-compat + offline driver suites: fail — == T3: root suite OK, driver suite FAILED (rc 1)
- T4 PR body has a user-impact opener + tracker id in both artifacts: pass — pdca-pdca contribcheck
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Review of issue #396: prevent a trailing optional-value flag from consuming an interactive leaf's appended seed, and correct the Remote Control guidance.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The acceptance boundary is falsifiable and separates Claude's verified separator behavior from unchanged families and the out-of-scope stdin path (`template/src/pdca_harness/families.py:103`, `template/src/pdca_harness/leaves.py:382`). |
| C2 Reproduction (red pre-fix) | PASS | With the new tests retained and only production/docs reversed, 26 tests ran and the old tree produced three failures plus one error at the defect assertions (`template/tests/test_seed_spill.py:220`, `template/tests/test_remote_control_docs.py:140`). |
| C3 Change | PASS | The patch stays within the six briefed profile/spawn, documentation, and test files; the human need not approve a scope expansion (`template/src/pdca_harness/leaves.py:378`, `template/pdca.toml.jinja:548`). |
| C4 Verification (red→green) | PASS | Independent rerun changed the retained-test result from 3 failures + 1 error pre-fix to 26 passing/skipped tests post-fix, directly covering separator insertion and non-separator compatibility (`template/tests/test_seed_spill.py:213`, `template/tests/test_seed_spill.py:225`). |
| C5 Causal adequacy | PASS | The invariant is restored at the sole interactive spawn boundary through profile data, rather than by a capability probe or a runtime guard around Remote Control (`template/src/pdca_harness/families.py:82`, `template/src/pdca_harness/leaves.py:385`). |
| T1 Structure | PASS | Family-specific parsing knowledge remains in `FamilyProfile` and `_invoke` consumes it once, preserving the existing generic-family behavior (`template/src/pdca_harness/families.py:82`, `template/src/pdca_harness/leaves.py:382`). |
| T2 Shape | NEEDS-HUMAN | Decide whether the passing documentation unit coverage is sufficient or the exact site-render/link audit must be rerun — `./engine/scripts/run-docs-check.sh` is not present in the target, so the asserted audit was not independently reproducible (`template/tests/test_remote_control_docs.py:128`). |
| T3 Runtime | NEEDS-HUMAN | Decide whether argv-level proof is enough for release — 1,567 offline tests pass, but the mocked spawn cannot demonstrate that installed Claude 2.1.223 starts Remote Control and preserves the seed with `--remote-control -- <seed>` (`template/tests/test_seed_spill.py:201`). |
| T4 Contribution | NEEDS-HUMAN | Confirm the user-impact opener and tracker reference in the contribution artifacts before publish — those artifacts are intentionally absent from the reviewer inputs, so the reported gate pass cannot be rerun from this sandbox. |
| T5 Judgment | PASS | Affected-path history found the prior Remote Control and seed work, no open PRs exist, and the sole closed-unmerged PR changes only `README.md`; no competing implementation was found (`template/tests/test_remote_control_docs.py:128`, `template/tests/test_seed_spill.py:185`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether non-last documentation plus a Claude-only separator is the right operational policy — this determines whether sanctioned interactive argv configurations are adequately protected in real use (`template/docs/INTEGRATION.md.jinja:156`, `template/pdca.toml.jinja:557`). |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T2 Shape — Decide whether the passing documentation unit coverage is sufficient or the exact site-render/link audit must be rerun — `./engine/scripts/run-docs-check.sh` is not present in the target, so the asserted audit was not independently reproducible (`template/tests/test_remote_control_docs.py:128`).
- [ ] T3 Runtime — Decide whether argv-level proof is enough for release — 1,567 offline tests pass, but the mocked spawn cannot demonstrate that installed Claude 2.1.223 starts Remote Control and preserves the seed with `--remote-control -- <seed>` (`template/tests/test_seed_spill.py:201`).
- [ ] T4 Contribution — Confirm the user-impact opener and tracker reference in the contribution artifacts before publish — those artifacts are intentionally absent from the reviewer inputs, so the reported gate pass cannot be rerun from this sandbox.
- [ ] Validation — fitness-to-purpose — Decide whether non-last documentation plus a Claude-only separator is the right operational policy — this determines whether sanctioned interactive argv configurations are adequately protected in real use (`template/docs/INTEGRATION.md.jinja:156`, `template/pdca.toml.jinja:557`).

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
- Iteration delta (if iterating): Auto-iterate (round 1): Check found implementation-level items only, no architectural judgment required — T2 Shape — Decide whether the passing documentation unit coverage is sufficient or the exact site-render/link audit must be rerun — `./engine/scripts/run-docs-check.sh` is not present in the target, so the asserted audit was not independently reproducible (`template/tests/test_remote_control_docs.py:128`).; T3 Runtime — Decide whether argv-level proof is enough for release — 1,567 offline tests pass, but the mocked spawn cannot demonstrate that installed Claude 2.1.223 starts Remote Control and preserves the seed with `--remote-control -- <seed>` (`template/tests/test_seed_spill.py:201`).; T4 Contribution — Confirm the user-impact opener and tracker reference in the contribution artifacts before publish — those artifacts are intentionally absent from the reviewer inputs, so the reported gate pass cannot be rerun from this sandbox.
- By / date: auto-iterate / 2026-08-06

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
