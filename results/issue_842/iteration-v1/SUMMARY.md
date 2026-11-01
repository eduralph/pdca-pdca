# Result — issue 842 / wave-mode-unknown-value-note

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: 
- Success criterion: `Config.load` with `wave_mode = "bogus"` prints one stderr line naming the bad value and the allowed values, and gives `cfg.wave_mode == "stack"`. `"stack"`, `"merge"` and an absent key print nothing and keep their value. `"Merge"`, `"merge "` (trailing space), `"none"` and a non-string value such as `1` count as unknown: each prints the note, falls back to `"stack"`, and raises nothing. Matching stays exact on purpose — no `.lower()` and no `.strip()`: today neither `"Merge"` nor `"merge "` enables merge mode (the checks compare with `==`), and folding case or whitespace would start merging PRs for that instance. `"none"` is an unknown value in this bundle: it gets the note and the fallback like any other; the sibling 843 then adds it to the allowed set (that is what 843 depends on this bundle for), and `pdca.toml` has no `"none"` today (`config.py:733` documents `stack | merge`).
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: 

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
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

Review the fix for silently accepted unknown `[driver].wave_mode` values: warn once on stderr and fall back to `stack`, preserving exact `stack`/`merge` matching.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The contract makes typo handling, non-string input, silence for valid/default values, and exact matching falsifiable without expanding merge behavior (brief.md:5; template/src/pdca_harness/config.py:733). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing the production change produced five assertion failures for bogus, case, whitespace, none, and integer inputs; valid/default inputs still passed (template/tests/test_config_wave_mode.py:45; review-evidence/red.log:1). |
| C3 Change | PASS | The two-file patch stays within loader validation and its regression coverage; neighboring merge policy and downstream execution retain their existing semantics (template/src/pdca_harness/config.py:736; template/tests/test_config_wave_mode.py:30). |
| C4 Verification (red→green) | PASS | Restoring the stash made both real-loader tests pass, including one-line diagnostics and unchanged valid/default values; the independent result agrees with the frozen red/green evidence (template/tests/test_config_wave_mode.py:54; review-evidence/green.log:1; gate-logs/C4-verify.log:79). |
| C5 Causal adequacy | PASS | Rejecting unknown values at the configuration boundary removes the silent-invalid-state cause; this is input validation, with no optional-capability probe or load-time side-effect workaround (template/src/pdca_harness/config.py:737; template/tests/test_config_wave_mode.py:27). |
| T1 Structure | PASS | The existing loader owns this policy, the test imports production directly, and no new dependency or architectural boundary is introduced (template/src/pdca_harness/config.py:736; template/tests/test_config_wave_mode.py:15). |
| T2 Shape | PASS | Independent diff whitespace, docs lint, 64-page render/link audit, checker tests, relative-link scan, and ADR-index scan passed; frozen docs and host-parity logs agree (review-evidence/environment.log:8; review-evidence/docs-render.log:1; review-evidence/docs-checkers.log:1; gate-logs/host-ci-docs.log:10). |
| T3 Runtime | PASS | Independent driver discovery passed all 2,699 tests with two skips; frozen evidence also records 50 root render/update tests passing, which could not be repeated here because Copier is absent (review-evidence/driver-suite.log:1819; gate-logs/T3-suite.log:80; review-evidence/environment.log:17). |
| T4 Contribution | N/A | Contribution artifacts are intentionally absent during Check; the deferred gate explicitly requires the substantive contribution audit at publish (gate-logs/T4-contribution.log:10). |
| T5 Judgment | NEEDS-HUMAN | Confirm no merged or closed/rejected prior fix by affected file path before contribution — the brief reports config-path history but only a keyword-based closed-PR search, and this target has one synthetic commit and no remote to settle the remaining duplication question (brief.md:13; review-evidence/environment.log:1). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Accept warning plus stack fallback as sufficient operator feedback, including treating none as unknown until sibling #843 — automated checks establish behavior, while the operational policy remains a sign-off decision (brief.md:5; template/src/pdca_harness/config.py:738; template/tests/test_config_wave_mode.py:49). |

The independent red/green run used the supplied disposable target: only the tracked production change was stashed, leaving the regression test available for the red leg, and the stash was restored before green. All source citations above were checked against that target; no target staleness was observed. The instance-scoped oracle wrappers were adjudicated from their frozen logs, and their available underlying checks were rerun directly. The production-import scan was independently confirmed from the test AST (template/tests/test_config_wave_mode.py:15; gate-logs/C5-prod-path.log:10).

The brief declares no external dependency (brief.md:10), and the actual configuration loader was exercised without a tool alias or curated replacement for its input boundary. Missing local Copier limits independent repetition of the root suite; the frozen root log explicitly shows render and update cases executing successfully (gate-logs/T3-suite.log:38; gate-logs/T3-suite.log:65). The supplied target contains only the uninstantiated integration template, whose project-defined human-only list is still a placeholder (template/docs/INTEGRATION.md.jinja:80).

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review: issue #842

No findings. The diff is clean on both lenses: no correctness bugs introduced, and no reuse, simplification or efficiency cleanup worth making. There are no NEEDS-HUMAN items.

What this conclusion rests on:

- `template/src/pdca_harness/config.py:737` does not raise on any TOML value type. The check is against a tuple, so it compares with `==` and does not need a hashable value. I loaded array, boolean, inline table, date, empty string and embedded-newline values through the real `Config.load`. Each printed one stderr line and gave `"stack"`.
- `template/src/pdca_harness/config.py:738` uses `!r` (Python's quoted form of the value), which keeps a trailing space visible and keeps a multi-line value on one line. This differs from `merge_requires` at `config.py:745-749` for a good reason, because that value is already normalized and always a string.
- `template/src/pdca_harness/config.py:736-740` covers the only place the value is read from `pdca.toml`. The downstream checks in `flow.py`, `waves.py` and `publish.py` only compare with `"merge"`, and `cli.py:1099` only prints the value, so they all accept the fallback. The tests that set `wave_mode` on `Config` directly skip the loader and are not affected.
- `template/tests/test_config_wave_mode.py:54-58` tests the fix properly. `gate-logs/C4-verify.log` shows all five unknown values failing without the fix. Each `shown` string can only match the printed value, not the fixed text of the message, so the `assertIn(shown, err)` check is meaningful.
- `gate-logs/T3-suite.log` shows the suite passing (2699 tests, 2 skipped), so no existing test or fixture relied on an unknown value being kept.

One limit on this check: I did not re-run the suite. I relied on the gate logs for that, and ran only the odd-value load above myself.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T5 Judgment — Confirm no merged or closed/rejected prior fix by affected file path before contribution — the brief reports config-path history but only a keyword-based closed-PR search, and this target has one synthetic commit and no remote to settle the remaining duplication question (brief.md:13; review-evidence/environment.log:1).
- [ ] Validation — fitness-to-purpose — Accept warning plus stack fallback as sufficient operator feedback, including treating none as unknown until sibling #843 — automated checks establish behavior, while the operational policy remains a sign-off decision (brief.md:5; template/src/pdca_harness/config.py:738; template/tests/test_config_wave_mode.py:49).
- [ ] **The brief has no tracker record behind it, and no issue id.** This leaf received only `brief.md`: there is no `notes.json`, `sources/` or `dependency-state.json`, and the brief names no issue number. So I could not check the defect against a thread, or look for a prior failed attempt, a maintainer constraint or a "fixed in" hint. The planner's own rule covers this case: "If you need the discussion and it's absent, ask the human… don't guess the thread" (`.claude/agents/planner.md:76-79`). There is also a downstream cost: `.github/workflows/require-linked-issue.yml:3-16` is a required check on `main` that fails a PR not tied to an issue. Revise the brief to name the issue id, or have the human confirm which issue this PR will link.
- [ ] **The "none" exclusion contradicts the success criterion, and the brief does not explain it.** Scope says "out of scope: the `"none"` value". No `wave_mode` value `"none"` exists in the target: `config.py:733` documents `stack | merge`, and a repo-wide search found no `wave_mode` "none". So under the criterion `"none"` is an ordinary unknown value: it prints the note and falls back to `"stack"`. That is a behaviour for `"none"`, so it is not out of scope, and a builder could read the line as "exempt it from the note". The prior-art query (`"wave_mode none"`, finding #619 and #484) suggests some earlier discussion of this value, which the brief never describes. I could not read either PR. Revise the brief to state what `"none"` does after the fix, and either add it as a test case or say why it was excluded.
- [ ] **The criterion does not pin the whitespace half of "exact" matching.** The brief tells the builder to mirror `config.py:738-742` "without its `.strip().lower()`", but the only cases it lists are `"Merge"` and `1`. A patch that drops `.lower()` and keeps `.strip()` passes every listed case, yet `"merge "` would then enable merge mode. Today that value does not (`flow.py:3080` and `publish.py:295` compare with `==`). This is the same hazard the brief gives for rejecting case folding: "would start merging PRs for that instance". Add `"merge "` to the listed unknown values, with the expected note and `cfg.wave_mode == "stack"`.
- [ ] **The prior-art check is narrower than the brief template requires, and its result is overstated.** The template asks for a search "by file path — merged history / open PRs / closed PRs" (`templates/brief.md.tpl:89`), and the planner asks for "affected file path" (`.claude/agents/planner.md:37`). The brief ran a commit-message grep (`log -i --grep=wave_mode`) and one search with `--state closed`. It ran no path search on `config.py` and no open-PR or open-issue search, so an in-flight duplicate would go unseen. "Result: no prior art" is stronger than that evidence supports. Re-run the check with those searches added. I could not run them here.
- [ ] **The neighbouring `merge_method` is not explicitly excluded.** `config.py:734`, the line right after the cited one, has the same flaw: `merge_method` is read with no validation and passed through to `merge.merge_wave` (`flow.py:3081`). The brief's out-of-scope list does not mention it, so a builder may add it as a drive-by, or a reviewer may flag its absence. Either one spends review surface. Add `merge_method` to the out-of-scope list, ideally with a follow-up issue.

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: iterated-to-Plan
- Iteration delta (if iterating): Rejected at sign-off: note-plus-fallback is the wrong policy. A mis-configured `pdca.toml` must produce a message AND a failure — `Config.load` must not continue with a substituted value. Rewrite the success criterion: unknown `wave_mode` (incl. `"Merge"`, `"merge "`, `"none"`, non-string) → one stderr line naming the bad value and the allowed values, then a raise / non-zero exit; no fallback. Keep exact matching, keep "stack"/"merge"/absent silent. Drop "raises nothing". Decide and state the failure form (which exception, or `sys.exit`) and how the CLI surfaces it. The existing patch and test are a good shape to adapt; only the fallback line and the `cfg.wave_mode == "stack"` assertions change. Prior-art (T5) was re-checked at sign-off against origin/main by path and by open/merged/closed PRs: no duplicate — carry that forward, no need to re-run.
- By / date: Eduard Ralph / 2026-10-30

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 5 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
- Policy (sign-off 842): a mis-configuration in `pdca.toml` must fail with a message, never fall back silently or with a note. Audit existing note-and-fallback sites (`merge_requires`, config.py:745–749) and unvalidated keys (`merge_method`, config.py:734); #843 inherits the fail-not-fallback rule.
