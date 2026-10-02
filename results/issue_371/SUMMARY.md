# Result — issue 371 / gate-confirm-failed-gating-row

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: a single transient red on a gating gate row no longer parks the bundle as if the
  patch were broken. A failed gating row is re-run once; both verdicts are recorded; a
  fail→pass is recorded `pass` + `flaky` and routed to the human as a HUMAN §6 item.
- Success criterion: all hold in `template/tests/test_gate_confirm.py`, run by the C4
  gate, driving the real `gates._run_one` with small shell commands (e.g. a command that
  fails on its first run and passes on its second, using a marker file in a temp dir):
  (1) **fail → pass:** a gating row whose command exits non-zero, then 0 on the confirm run,
  is recorded `result = "pass"`, `flaky = true`, `attempts = ["fail", "pass"]`; the
  command ran exactly twice.
  (2) **fail → fail:** recorded `fail`, `attempts = ["fail", "fail"]`, no truthy `flaky`;
  the row's evidence (`path_line`) comes from the confirm run.
  (3) **fail → no pass:** when the confirm run times out (the row's `timeout_secs`),
  declares itself unverifiable, reports `deferred` (exit 0 + `PDCA-DEFERRED` on a
  deferrable row, `gates.py:795-798`), or raises an exception (`gates.py:599`), the first
  `fail` stands with the FIRST run's `path_line`, no truthy `flaky`; `attempts` records the
  second outcome as its own classification (`"unverifiable"`, `"deferred"`, `"error"` for the
  exception). Only a clean `pass` on the confirm run turns the row into `pass` + `flaky`.
  (4) **Bounds:** exactly one confirm run; a NON-gating failing row runs once; a passing row
  runs once (no cost on green); a `cmd_error` row (misconfigured delegation,
  `gates.py:508`) and a command that raised before producing an exit code
  (`gates.py:599`) are not confirmed; `[gates] confirm_gating_fail = false` in the project
  config turns confirmation off; a per-row `confirm_fail = false` turns it off for that row
  alone — honoured on a `[[gates.checks]]` entry AND on a `[gates] host_ci` entry (the key
  survives `_normalize_host_ci`, `config.py:860-890`; tested for both tables).
  (4b) **Check-time only:** confirmation runs only on the Check matrix — `run_gates` and its
  revalidate twin `run_gates_dry` (so a re-gate reproduces the frozen verdict). Every other
  `_run_one` caller runs a failing row exactly once and keeps today's behaviour: the publish
  host-CI gate (`publish.py:930`, a non-zero exit still refuses the push, the literal #311
  contract `config.py:870-871`), the between-waves integration re-gate
  (`gates.run_integration`), and the working-tree re-gate (`run_working_tree`). Tested: a
  fail→pass command driven through `publish`'s host-CI path (or `_run_one` with the
  confirm switch off, which is what those callers pass) records `fail` after ONE run.
  (5) **Evidence:** with a `log_dir`, the row's `gate-logs/<rule_id>.log` holds BOTH runs'
  output, each run under its own block with that run's attempt number, `# exit:` and
  `# outcome:` lines; the file's top-level `# outcome:` header (`gates.py:657-658`) shows
  the row's recorded (combined) result (the #370 contract: the full basis is readable from
  bundle files).
  (6) **Routing:** a row with truthy `flaky` becomes one §6 item via
  `assemble.collect_needs_human`, kind HUMAN (never IMPL, whatever its element), naming
  the check and both outcomes; `overall` counts the row as the pass it recorded.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: the confirm-once rule for failed gating rows in `gates._run_one`, switched on
  by an explicit keyword (default off) that only the Check path passes — `run_gates` and
  `run_gates_dry` via `_run_checks` (both its `[[gates.checks]]` rows and its host-CI rows,
  `gates.py:396`, `:425`); publish's host-CI gate, `run_integration` and
  `run_working_tree` do NOT confirm (clause 4b); the row keys
  `attempts` and `flaky`; the gate log carrying both runs; `[gates] confirm_gating_fail`
  (default true) in `config.py`; the per-row `confirm_fail` key; the §6 routing in
  `assemble.py` next to `_unverifiable_items`; documentation of both keys in
  `template/pdca.toml.jinja` `[gates]` and the gate docs (`docs/05-check.md`). / out of
  scope: re-sampling model leaves (reviewer, advisories); more than one confirm; retrying
  non-gating rows; confirming at publish, integration or working-tree re-gates (a red there
  blocks as today); any change to `size_signal.py` (it already reads a truthy `flaky` as
  environment-attributed, `size_signal.py:181-183`, and needs nothing new); changing the
  auto-iterate decision itself (#409).

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

Review issue #371: confirm failed gating rows once at Check, preserve both attempts, route fail→pass to human review, and keep publish/integration/working-tree failures single-run.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The acceptance criteria distinguish every second-attempt outcome, opt-outs, evidence retention, and Check-only scope; the carried-forward publish regression now has an executable boundary test (brief.md:7; target/template/tests/test_gate_confirm.py:392). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing production changes while retaining the new tests reproduces the missing confirmation: 27 tests, 11 assertion failures and 8 errors, including one run instead of two (review-red.log:150; target/template/tests/test_gate_confirm.py:109). |
| C3 Change | PASS | Scope and conservative outcome handling match the brief: only a clean second pass overrides red; other inconclusive outcomes preserve the first failure, while publish retains its original refusal boundary (target/template/src/pdca_harness/gates.py:686; target/template/src/pdca_harness/publish.py:930). |
| C4 Verification (red→green) | PASS | After stash restoration all 27 tests pass; the real publish test refuses the push after one run, and forcing confirmation makes that test fail at two runs, resolving the prior review concern (review-green.log:39; review-publish-mutation.log:18; target/template/tests/test_gate_confirm.py:402). |
| C5 Causal adequacy | PASS | Real gate commands exercise the production classification and human-routing paths; the publish fixture can exhibit the forbidden second run, and no capability probe masks a load-time cause (target/template/tests/test_gate_confirm.py:99; target/template/tests/test_gate_confirm.py:416; target/template/tests/test_gate_confirm.py:462). |
| T1 Structure | PASS | Command execution, attempt combination, evidence persistence, and human routing retain distinct responsibilities; caller-controlled confirmation preserves non-Check behavior (target/template/src/pdca_harness/gates.py:637; target/template/src/pdca_harness/gates.py:686; target/template/src/pdca_harness/assemble.py:341). |
| T2 Shape | PASS | Independently rerun docs lint and the 22-page render/link audit pass, as does diff whitespace validation; the user-facing defaults and opt-outs agree with the configuration behavior (review-lint.log:1; review-render.log:3; target/docs/05-check.md:450; target/template/src/pdca_harness/config.py:584). |
| T3 Runtime | PASS | Independent driver-suite run passes 2,162 tests with 2 skips; frozen evidence shows all 24 root tests, including real Copier update cases, passed; this host's root rerun exits 77 because Copier is not importable, so root verification rests on that frozen log (gate-logs/T3-suite.log:42; gate-logs/T3-suite.log:54; review-root.log:6). |
| T4 Contribution | N/A | Contribution artifacts are intentionally drafted after Check; the recorded deferred audit must run substantively at publish, so no contribution verdict is due now (gate-logs/T4-contribution.log:10). |
| T5 Judgment | NEEDS-HUMAN | Confirm merged and closed/rejected prior art for all six affected paths — the brief reports partial path-based history, but the supplied target has only one synthetic commit and no remotes, so absence of conflicting or rejected work cannot be independently established (brief.md:96; review-prior-art.log:1). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Accept the default-on tradeoff of one extra failed-gate execution and human assessment of fail→pass — a second pass alone cannot distinguish environmental flakiness from an intermittent patch defect, although both samples remain available and publish still refuses its first failure (target/docs/05-check.md:450; target/template/src/pdca_harness/assemble.py:595). |

No implementation defect was established. All source citations above refer to the supplied, patched target; no target-state mismatch was observed. The original patch was restored after the red leg and left unchanged. No builder notes were read.

Independent execution and frozen evidence:

- Red→green: `cd target/template && PYTHONPATH=src python3 -m unittest tests.test_gate_confirm`, with tracked changes stashed for red and restored for green. Full output is in `review-red.log` and `review-green.log`. Red includes substantive assertion failures, not merely missing new interfaces.
- Publish regression sensitivity: an in-memory wrapper forced `confirm=True` at the real gate runner while executing `PublishHostCiRunsOnce.test_fail_then_pass_command_refuses_the_push_after_one_run`. It failed with `2 != 1`; no target source was edited. The same test passes without the wrapper. This local bare-repository topology exercises the actual refusal/push boundary, rather than assuming the forbidden behavior cannot occur (`review-publish-mutation.log:18`).
- Runtime: `cd target/template && PYTHONPATH=src python3 -m unittest discover -s tests` passed 2,162 tests, with 2 skips (`review-suite.log`). The root command `python3 -m tests.run_root_suite` could not exercise Copier here (`review-root.log:6`). The frozen T3 log explicitly shows successful rendering and update cases, not just a green summary (`gate-logs/T3-suite.log:40`). This is a local toolchain caveat, not a patch failure or an undisclosed unmet feature dependency; the brief declares no external dependencies.
- Shape and host-CI parity: ran the target workflow's `python3 docs/publishing/tools/lint_docs.py` and `python3 docs/publishing/tools/render_site.py --check --out <sandbox>/review-site`; both passed. Frozen T2 and host-CI logs also show lint and link-audit success (`gate-logs/T2-docs.log:11`; `gate-logs/host-ci-docs.log:11`). `git -C target diff --check` passed.
- The instance-scoped C4/C5/T2/T3 wrappers are not supplied for direct execution. Their frozen logs were inspected; C4 is corroborated by the independent red→green run, and C5's import-only scanner evidence (`gate-logs/C5-prod-path.log:10`) is strengthened by executing the real production and publish paths. T4 remains deferred as required, not an unverified green.
- Prior-art investigation ran `git log --all -- <path>` for all six changed files: docs, template configuration, assemble, config, gates, and the new test. It found only the synthetic base for the existing files and no history for the new test; `git remote -v` is empty (`review-prior-art.log`). No `INTEGRATION.md` exists in the supplied target, so no additional project-specific human-only list was available. No other checkout was consulted.

### Advisory — code-review

# Advisory code review — issue 371 (confirm-once for a failed gating row)

No correctness bugs found. The gates are green (C4-verify, T3-suite, host-ci-docs all `pass` in `gate-logs/`). The iteration-1 blocker is fixed: `template/tests/test_gate_confirm.py:323-411` (`PublishHostCiRunsOnce`) now drives the real `publish.publish` against a toy bare origin and asserts one run, `rc == 1`, nothing pushed, and `host-ci.json` row `fail` with no `flaky`/`attempts`. Adding `confirm=True` at `template/src/pdca_harness/publish.py:930` would now turn it red. A control test (`test_control_the_same_row_is_confirmed_at_check`) proves the same row *is* confirmed at Check. The combine rule (`gates.py:686-703`), the confirm guard (`gates.py:588-589`: gating, `fail`, real exit code, both switches) and the log format (`gates.py:706+`) match clauses 1–5 of the brief.

Minor, optional items (none blocks):

- `template/src/pdca_harness/assemble.py:596-597` — on fail→pass the row's `path_line` is the *passing* run's evidence (`gates.py:700`), so the §6 line says "Confirm the red sample was environmental — <green evidence>". The red sample's own evidence line is only in `gate-logs/<id>.log`. If the log write failed (`log_error`), the first run's evidence is in no bundle file at all. A one-line improvement is to carry the first run's evidence into the item (e.g. an extra `first_evidence` row key), so the human sees what went red without opening the log. This is not required by the brief.
- `template/src/pdca_harness/gates.py:683` — a non-boolean per-row `confirm_fail` (e.g. `"false"`) silently turns confirmation off. The project-level key warns on stderr for the same mistake (`config.py` parse block added at ~`:582-588`). The fail direction is safe either way (off = today's behaviour); it's only an inconsistency in how loudly a typo is reported.
- `template/src/pdca_harness/assemble.py:592-597` — `r['log']`, `r['check']`, `r['path_line']`, `r['oracle']` are indexed directly. This matches `_unverifiable_items` just above (`assemble.py:567-570`), so it's consistent with existing code. The sign-off called it optional, and I agree.

The earlier "dead `rc`/`output` args to `_write_gate_log`" clean-up has already been done: the new signature takes `attempts` only, and the one caller is `gates.py:618`.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — Confirm merged and closed/rejected prior art for all six affected paths — the brief reports partial path-based history, but the supplied target has only one synthetic commit and no remotes, so absence of conflicting or rejected work cannot be independently established (brief.md:96; review-prior-art.log:1).
- [x] Validation — fitness-to-purpose — Accept the default-on tradeoff of one extra failed-gate execution and human assessment of fail→pass — a second pass alone cannot distinguish environmental flakiness from an intermittent patch defect, although both samples remain available and publish still refuses its first failure (target/docs/05-check.md:450; target/template/src/pdca_harness/assemble.py:595).
- [x] **A fail→pass outside Check reaches no human.** The scope makes confirmation apply "to every caller of `_run_one`: Check, host-CI rows, publish/close re-gates", but the only routing to a human (clause 6, `assemble.collect_needs_human`) is on the Check path. The publish host-CI gate calls `gates._run_one` (publish.py:930) and blocks only on `r["result"] != "pass"` (publish.py:934). With this change, a host-CI command that exits non-zero and then passes on the confirm run is recorded `pass` + `flaky`, and the push goes ahead with nothing surfacing the flake. That contradicts the literal #311 contract quoted in config.py:870-871 ("a command that exits non-zero blocks publish"). The same happens at the between-waves integration re-gate (`gates.run_integration`, flow.py:1813), where the brief does not even name the caller. The brief should decide one of two things: (a) limit confirmation to Check-time `run_gates`, or (b) say what happens to a flaky row at publish and integration (refuse, warn, or record in `host-ci.json`). It should also add a success clause for that path. Otherwise Do will pick a behaviour that no reviewer can check against the brief.
- [x] **The combine rule has gaps that the criterion does not pin.** Clauses 1-3 cover fail→pass, fail→fail and fail→timeout/unverifiable. `_run_one` can produce two other second outcomes:
- [x] **"Per-row `confirm_fail` on a `[[gates.checks]]` entry" leaves host-CI rows out.** Host-CI rows are a separate table, `[gates] host_ci`, normalised by `_normalize_host_ci` (config.py:860-890). That function uses `dict(entry)`, so the key would survive, but the brief documents and tests the opt-out only for `[[gates.checks]]`. Host-CI rows go through `_run_one` too (gates.py:425, publish.py:930). The brief should state whether `confirm_fail = false` is honoured on a `host_ci` entry (it has the same model-backed-row risk the owner raised) and cover it in clause 4. Otherwise it is untested surface.
- [x] **Default-on re-sampling of a model-backed row — the risk the owner flagged — is left to operators to prevent.** The owner's comment: a model-backed gate row that gets re-sampled "would … let a second, luckier sample overwrite real first-run blockers as a flaky pass". The brief's answer is "Instances with model-backed gate rows must set `confirm_fail = false`" (Impact section), with only an upgrade note. publish.py:813-815 shows such rows exist in practice ("three parallel model review passes"). For those rows, an existing instance that upgrades without reading the note loses its blockers. The brief should either justify default-on for existing instances (a `copier update` keeps their `pdca.toml`) or say that `flaky` is what keeps this safe. It is only partly safe: `flaky` still forces a C6 acknowledgement through §6 at Check, but not at publish (see the first finding).
- [x] **The `Depends on: 409` reason is not something this bundle's criterion checks.** The Ordering note justifies the dependency by auto-iterate *deferring* a HUMAN item, which is #409's behaviour. Clause 6 only asserts kind HUMAN, and that already holds on main today: HUMAN items exist and veto auto-iterate. The dependency is a real scheduling and file-overlap choice (409 exists, PLANNED), not a correctness prerequisite. If 409 stalls, this bundle stalls with it for no functional reason. The brief should say whether it could stack on main alone, or keep the dependency and state explicitly that it is only for ordering.

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
- By / date: Eduard Ralph / 2026-09-30

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 5 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
