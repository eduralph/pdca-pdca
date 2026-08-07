# Result — issue 380 / settings-write-env-deny-never-matches

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: the shipped Claude Code permission config declares two file-permission deny
  rules in a form the permission checker never matches. `template/.claude/settings.json:53-54`
  carries `"Write(.env)"` / `"Write(.env.*)"` beside the correct `"Edit(.env)"` /
  `"Edit(.env.*)"` (`:51-52`); the repo's own `.claude/settings.json:82-83` carries the
  identical pair. Claude Code matches file-permission rules only through `Edit(path)` — Edit
  rules cover all file-editing tools, Write included — so the two rows deny nothing the Edit
  rows do not already deny, and Claude Code prints two red validation warnings at the end of
  **every leaf session in every rendered instance**:
  `Permission deny rule (.claude/settings.json): Write(.env) is not matched by file permission
  checks — only Edit(path) rules are. Use Edit(.env) instead (Edit rules cover all file-editing
  tools).` (idem for `Write(.env.*)`). Introduced together with the correct rows in `0103877`
  ("Settings hygiene: drop gramps-specific perms; add generic guardrails to the template"),
  never removed since; observed on the pdca-pdca self-hosting instance during its first real
  cycles (eduralph/pdca-pdca#11, fixed locally by dropping the two rows).
- Success criterion: no `.claude/settings.json` this repo ships — the template's
  (`template/.claude/settings.json`) or the repo's own (`.claude/settings.json`) — contains a
  **file-path** permission rule written as `Write(<path>)` in any of its `allow` / `ask` /
  `deny` lists, while the `.env` protection is unchanged (the `Read(.env)`, `Read(.env.*)`,
  `Edit(.env)`, `Edit(.env.*)` rows all remain byte-identical). Demonstrable by C4-verify: the
  named test asserts this over the settings file(s) reachable from the suite and goes red on
  the pre-fix tree, green with the patch.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: remove the unmatchable file-permission rules from every `.claude/settings.json`
  this repo ships, and pin the invariant with a test that runs in both the template checkout
  and a rendered instance. / out of scope: any change to *what* is protected (the `Read(...)`
  and `Edit(...)` rows stay exactly as they are); the `Bash(...)` deny rows and the `ask` list;
  the `.claude/settings.json` of any other instance (they converge on `copier update`); adding
  new guardrails of any kind.

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
- T3 runtime: render/update-compat + offline driver suites: fail — /tmp/tmp02bdzheb/results/issue_500/split-proposal.md
- T4 PR body has a user-impact opener + tracker id in both artifacts: pass — pdca-pdca contribcheck
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Task under review: remove unmatched Claude Code `Write(<path>)` permission rules from shipped `.claude/settings.json` files while preserving the real `.env` `Read`/`Edit` protections.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The owed decision is whether the scope is concrete enough to judge: it requires eliminating every shipped file-path `Write(<path>)` rule while keeping `.env` `Read`/`Edit` protections unchanged, which is falsifiable by the named unittest (`brief.md:20`). |
| C2 Reproduction (red pre-fix) | PASS | The owed decision is whether the pre-fix failure is real: in a temp copy with only the settings hunks reversed and the new test retained, `PYTHONPATH=src python3 -m unittest tests.test_settings_permissions` failed on `Write(.env)`, `Write(.env.*)`, and `Write(**)` as asserted (`template/tests/test_settings_permissions.py:70`). |
| C3 Change | PASS | The owed decision is whether all shipped dead file-path `Write(...)` rules are gone without weakening `.env`: target settings retain `Read(.env)`, `Read(.env.*)`, `Edit(.env)`, and `Edit(.env.*)` and `rg 'Write\\([^)]*\\)'` finds no live settings hits (`.claude/settings.json:73`, `template/.claude/settings.json:45`). |
| C4 Verification (red→green) | NEEDS-HUMAN | The owed decision is whether to accept the driver C4 row despite local harness non-reproduction: the named unittest is red→green locally, but the recorded oracle `./engine/scripts/run-verify.sh` is absent at target root and the only found script is a driver skeleton requiring `PDCA_BUNDLE` (`check-gates.json:33`, `template/engine/scripts/run-verify.sh:48`). |
| C5 Causal adequacy | PASS | The owed decision is whether this is root-cause removal or a symptom guard: the patch removes the unmatchable permission rows and adds no capability probe/runtime fallback smell (`patch.diff:9`, `patch.diff:33`). |
| T1 Structure | PASS | The owed decision is whether the test is placed and scoped to the shipped surfaces: it lives under `template/tests/`, resolves template vs rendered posture, and covers the repo-local settings only in template posture (`template/tests/test_settings_permissions.py:30`). |
| T2 Shape | NEEDS-HUMAN | The owed decision is whether the docs/site-shape gate result should stand: `check-gates.json` records `render_site: link audit OK`, but `./engine/scripts/run-docs-check.sh` is not present in this target, so I could not rerun it (`check-gates.json:60`). |
| T3 Runtime | NEEDS-HUMAN | The owed decision is whether the recorded runtime-suite failure is environmental/unrelated or release-relevant: `check-gates.json` reports a non-gating fail at `/tmp/tmp02bdzheb/results/issue_500/split-proposal.md`, but `./engine/scripts/run-suite.sh` is not present in this target to reproduce (`check-gates.json:69`). |
| T4 Contribution | NEEDS-HUMAN | The owed decision is whether contribution metadata actually satisfies the project gate: `check-gates.json` records `pdca-pdca contribcheck` PASS, but this artifact bundle contains no PR/commit artifacts and no `pdca` executable was available for a local rerun (`check-gates.json:78`). |
| T5 Judgment | PASS | The owed decision is whether advisory checks found scope creep, prior art, or root-cause ambiguity: affected-path history shows no newer merged fix and `gh search issues "settings deny"` plus open PR listing returned no rows (`brief.md:83`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | The owed decision is final product fitness: a human must confirm that removing these settings rows is acceptable for real Claude Code sessions, especially because runtime warning disappearance was not manually exercised here (`brief.md:33`). |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] C4 Verification (red→green) — The owed decision is whether to accept the driver C4 row despite local harness non-reproduction: the named unittest is red→green locally, but the recorded oracle `./engine/scripts/run-verify.sh` is absent at target root and the only found script is a driver skeleton requiring `PDCA_BUNDLE` (`check-gates.json:33`, `template/engine/scripts/run-verify.sh:48`).
- [x] T2 Shape — The owed decision is whether the docs/site-shape gate result should stand: `check-gates.json` records `render_site: link audit OK`, but `./engine/scripts/run-docs-check.sh` is not present in this target, so I could not rerun it (`check-gates.json:60`).
- [x] T3 Runtime — The owed decision is whether the recorded runtime-suite failure is environmental/unrelated or release-relevant: `check-gates.json` reports a non-gating fail at `/tmp/tmp02bdzheb/results/issue_500/split-proposal.md`, but `./engine/scripts/run-suite.sh` is not present in this target to reproduce (`check-gates.json:69`).
- [x] T4 Contribution — The owed decision is whether contribution metadata actually satisfies the project gate: `check-gates.json` records `pdca-pdca contribcheck` PASS, but this artifact bundle contains no PR/commit artifacts and no `pdca` executable was available for a local rerun (`check-gates.json:78`).
- [x] Validation — fitness-to-purpose — The owed decision is final product fitness: a human must confirm that removing these settings rows is acceptable for real Claude Code sessions, especially because runtime warning disappearance was not manually exercised here (`brief.md:33`).

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
- By / date: Eduard Ralph / 2026-08-02

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
