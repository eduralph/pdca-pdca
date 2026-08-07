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

Review of issue 396: prevent a trailing optional-value CLI flag from consuming an interactive leaf's appended seed, and correct the shipped Remote Control guidance.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The acceptance boundary is unambiguous: document non-last optional-value flags and make Claude-family seed delivery argv-independent while preserving the bare positional for unverified families (`template/src/pdca_harness/families.py:85`). |
| C2 Reproduction (red pre-fix) | PASS | In an isolated `0fbfa26` base snapshot with only the new tests applied, the exact trailing-`--remote-control` case failed because the spawn lacked `--`, and the old flag-last documentation failed its assertion (`template/tests/test_seed_spill.py:213`, `template/tests/test_remote_control_docs.py:150`). |
| C3 Change | PASS | The decision boundary stays within the brief's two documentation surfaces, family profile, single interactive spawn, and focused tests; the headless stdin path is unchanged (`template/src/pdca_harness/leaves.py:384`). |
| C4 Verification (red→green) | PASS | Independently reconstructed red→green was rc 1→0 for 26 focused tests, and the patched full offline template suite exited 0; this directly verifies separator placement and family fallback (`template/tests/test_seed_spill.py:213`). |
| C5 Causal adequacy | PASS | The fix removes the argv ambiguity at the spawn boundary instead of adding a capability probe or symptom guard, so a trailing optional-value flag cannot consume the seed for the opted-in family (`template/src/pdca_harness/leaves.py:384`). |
| T1 Structure | PASS | The human decision is whether the family-specific CLI fact belongs in profile data; keeping it there localizes vendor syntax and leaves invocation generic (`template/src/pdca_harness/families.py:106`). |
| T2 Shape | NEEDS-HUMAN | Decide whether passing focused documentation tests is sufficient for release — the recorded site-render/link audit names `./engine/scripts/run-docs-check.sh`, which is absent from the target and could not be independently rerun (`template/tests/test_remote_control_docs.py:150`). |
| T3 Runtime | NEEDS-HUMAN | Decide whether argv-level and offline-suite proof is sufficient — Claude 2.1.223 is installed, but an enrolled interactive Remote Control session was not exercised, and the recorded failing `run-suite.sh` result cannot be reproduced because that script is absent (`template/tests/test_seed_spill.py:213`). |
| T4 Contribution | NEEDS-HUMAN | Confirm the contribution artifacts contain a user-impact opener and tracker reference before publish — those artifacts are deliberately outside the reviewer inputs, so the recorded pass cannot be independently checked. |
| T5 Judgment | NEEDS-HUMAN | Confirm no closed/rejected work duplicates or conflicts with this approach — local `git log --all` by each of the six affected paths found the known #313/#337/#386 history and no prior `seed_separator`, but closed/rejected review state is unavailable (`template/src/pdca_harness/leaves.py:384`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the resulting Remote Control workflow is fit for real operator use — automated red→green proves argv construction, but only an enrolled interactive session can confirm both Remote Control startup and visible seeded REPL behavior (`template/pdca.toml.jinja:557`). |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T2 Shape — Decide whether passing focused documentation tests is sufficient for release — the recorded site-render/link audit names `./engine/scripts/run-docs-check.sh`, which is absent from the target and could not be independently rerun (`template/tests/test_remote_control_docs.py:150`).
- [x] T3 Runtime — Decide whether argv-level and offline-suite proof is sufficient — Claude 2.1.223 is installed, but an enrolled interactive Remote Control session was not exercised, and the recorded failing `run-suite.sh` result cannot be reproduced because that script is absent (`template/tests/test_seed_spill.py:213`).
- [x] T4 Contribution — Confirm the contribution artifacts contain a user-impact opener and tracker reference before publish — those artifacts are deliberately outside the reviewer inputs, so the recorded pass cannot be independently checked.
- [x] T5 Judgment — Confirm no closed/rejected work duplicates or conflicts with this approach — local `git log --all` by each of the six affected paths found the known #313/#337/#386 history and no prior `seed_separator`, but closed/rejected review state is unavailable (`template/src/pdca_harness/leaves.py:384`).
- [x] Validation — fitness-to-purpose — Decide whether the resulting Remote Control workflow is fit for real operator use — automated red→green proves argv construction, but only an enrolled interactive session can confirm both Remote Control startup and visible seeded REPL behavior (`template/pdca.toml.jinja:557`).

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
- By / date: Eduard Ralph / 2026-08-06

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
