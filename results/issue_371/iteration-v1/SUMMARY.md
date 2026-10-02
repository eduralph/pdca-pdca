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

Review issue #371: confirm a failed gating row once at Check, retain both outcomes, and require human acknowledgment when the second attempt passes.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief defines falsifiable outcomes, opt-outs, and Check-only scope; the regression cases cover the specified decision boundaries (`brief.md:8`; `target/template/tests/test_gate_confirm.py:103`). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing tracked changes while retaining the new test produces 10 assertion failures and 6 errors across 25 tests, including the absent second execution (`review-red.log:199`; `target/template/tests/test_gate_confirm.py:105`). |
| C3 Change | PASS | The change stays within the approved confirmation, evidence, configuration, and human-routing scope; publish retains its one-attempt behavior (`target/template/src/pdca_harness/gates.py:587`; `target/template/src/pdca_harness/publish.py:930`). |
| C4 Verification (red→green) | PASS | Restoring the patch independently makes all 25 regression tests pass, including timeout, deferred, exception, opt-out, log, and routing cases (`review-green.log:40`; `target/template/tests/test_gate_confirm.py:128`). |
| C5 Causal adequacy | PASS | Real subprocess outcomes exercise the production decision that previously treated one transient red as final; only a clean second pass changes that verdict, with both samples retained; no capability-probe symptom guard is introduced (`target/template/src/pdca_harness/gates.py:690`; `target/template/tests/test_gate_confirm.py:94`). |
| T1 Structure | PASS | Shared attempt execution and combination keep the confirmation policy centralized, while callers outside Check default to one execution (`target/template/src/pdca_harness/gates.py:505`; `target/template/src/pdca_harness/gates.py:641`). |
| T2 Shape | PASS | Independent docs lint, 22-page render/link audit, and whitespace check passed; frozen docs and host-CI logs corroborate those results (`target/docs/05-check.md:451`; `gate-logs/T2-docs.log:10`; `gate-logs/host-ci-docs.log:10`). |
| T3 Runtime | PASS | Independent driver suite passed 2,160 tests with two skips; frozen evidence also shows all 24 root render/update tests passed, although local root reproduction lacks importable Copier (`gate-logs/T3-suite.log:38`; `gate-logs/T3-suite.log:54`; `review-root-suite.log:6`). |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the substantive artifact audit must run at publish (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Confirm prior-art clearance across all six affected paths, including merged and closed/rejected work — the brief records a path-based search, but this target has one synthetic base commit and no remote, so independent history verification is unavailable (`brief.md:98`; `review-prior-art.log:1`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether default-on confirmation and mandatory human acknowledgment provide the desired tradeoff between avoiding transient-red stalls and recognizing intermittent patch defects — a fail→pass alone cannot establish environmental causation (`target/docs/05-check.md:451`; `target/template/src/pdca_harness/assemble.py:589`). |

No implementation defect was found. This review is advisory; it does not authorize acceptance.

Independent verification used the supplied disposable target. `git stash push` restored the pre-fix tracked sources while leaving `template/tests/test_gate_confirm.py` present; `PYTHONPATH=src python3 -m unittest tests.test_gate_confirm` exited 1. After `git stash pop`, the identical command exited 0. The target's original patch was restored. Full captures are in `review-red.log` and `review-green.log`; the frozen C4 log independently records the same red/green distinction (`gate-logs/C4-verify.log:50`, `gate-logs/C4-verify.log:253`).

Additional independent checks: `PYTHONPATH=src python3 -m unittest discover -s tests` from `target/template` passed (see `review-suite.log`); `python3 docs/publishing/tools/lint_docs.py`, `python3 docs/publishing/tools/render_site.py --check --out ../review-site`, and `git diff --check` from `target` passed. The shipped production-import scanner, run with this bundle and `PDCA_PROD_PACKAGE=pdca_harness`, confirmed that the added test imports production; inspection and execution also confirm it reaches the real gate runner (`target/template/tests/test_gate_confirm.py:95`; frozen scanner evidence at `gate-logs/C5-prod-path.log:10`).

Local root-suite reproduction reported `PDCA-UNVERIFIABLE` because Copier is not importable by `/usr/bin/python3` (`review-root-suite.log:6`). This is a reviewer-host limitation, not a patch failure: the frozen log explicitly shows real render and update cases executing successfully (`gate-logs/T3-suite.log:38`). No external dependency is left undischarged by the combined evidence; the brief declares none (`brief.md:84`). Instance-scoped wrapper paths were adjudicated from their supplied logs rather than treated as missing target files.

The prior-art investigation ran `git log --all --oneline --` against every affected path and `git remote -v` inside the target. It returned only synthetic base commit `3c0446a` and no remotes (`review-prior-art.log:1`); it cannot establish what upstream merged or rejected. The supplied integration template leaves project-defined human-only items unenumerated (`target/template/docs/INTEGRATION.md.jinja:80`); no additional concrete item can be derived from it.

### Advisory — code-review

# Advisory code review — issue 371 (confirm-once for a failed gating row)

Lens: bugs the patch introduces, plus reuse / simplification. Advisory only. I found no correctness bug in the main logic. `_run_one` → `_attempt` → `_combine_attempts` matches brief clauses 1–4b. Only a clean `pass` on the confirm run turns the row green, and a timeout, unverifiable, deferred or error result leaves the first `fail` and its evidence in place. `cmd_error` returns before any run, and a first run that raised (`rc is None`) is never confirmed. The C4 log (`gate-logs/C4-verify.log`) shows 25 tests green with the fix and red without it. The findings below are small.

- NEEDS-HUMAN [impl] — `template/tests/test_gate_confirm.py:301-311` (`test_publish_host_ci_rows_run_once`) copies publish's call by hand (`gates._run_one(chk, cfg=…, cwd=…, bundle=…, runner=…, worktree_path=…)`) and never calls `publish`. So it checks that `_run_one` defaults to `confirm=False`, which `test_run_one_without_the_switch_runs_once` (`:292`) already covers. If someone later adds `confirm=True` at `template/src/pdca_harness/publish.py:930`, this test stays green. That is the exact regression clause 4b exists to prevent: a lucky second sample letting a push through. Either drive the real publish host-CI function, or at least assert that the `publish.py:930` call does not pass `confirm`.
- `template/src/pdca_harness/assemble.py:586-590` (`_flaky_items`) joins `attempts` into a string and then splits it again on `' → '` to get the first and last outcome. Reading `attempts[0]` and `attempts[-1]` from the list would be simpler and would not depend on the separator. The `or ["fail", "pass"]` fallback also makes up an attempt history for any row that has `flaky` but no `attempts`. Today the recorder always writes both keys together, so this is cosmetic, but a made-up "first run fail" in a §6 line is misleading if that ever stops being true.
- `template/src/pdca_harness/gates.py:617-624`: when there are two attempts, `_write_gate_log` still receives `rc=attempts[0]["rc"]` and `output=attempts[0]["output"]`, and the two-attempt branch (`gates.py:710` onward) ignores both. That is harmless but confusing to read. Passing `attempts` alone, and deriving the single-run case from `attempts[0]` inside `_write_gate_log`, would remove the dead arguments.
- `template/src/pdca_harness/gates.py:589-598` re-runs the same command with no reset between runs. That is right for read-only gates. A gate with side effects, such as a verifier that applies `patch.diff` to the worktree and then reverts it, could leave a run-1 failure half-applied, and run 2 then starts from a different tree. A fail→pass is still sent to the human as HUMAN §6 (`assemble.py:341`), so this cannot slip through silently. Still, the docs (`docs/05-check.md` hunk, `pdca.toml.jinja` hunk) only say "set `confirm_fail = false`" for model-backed rows. They could say the same for gates that change shared state and don't clean up after a failure. Advisory only, no action required.
- I found no efficiency problems. The extra run happens only on a gating red at Check (`run_gates` / `run_gates_dry`), and green rows still run once (`test_passing_row_runs_once`, `:194`).

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — Confirm prior-art clearance across all six affected paths, including merged and closed/rejected work — the brief records a path-based search, but this target has one synthetic base commit and no remote, so independent history verification is unavailable (`brief.md:98`; `review-prior-art.log:1`).
- [x] Validation — fitness-to-purpose — Decide whether default-on confirmation and mandatory human acknowledgment provide the desired tradeoff between avoiding transient-red stalls and recognizing intermittent patch defects — a fail→pass alone cannot establish environmental causation (`target/docs/05-check.md:451`; `target/template/src/pdca_harness/assemble.py:589`).
- [ ] `template/tests/test_gate_confirm.py:301-311` (`test_publish_host_ci_rows_run_once`) copies publish's call by hand (`gates._run_one(chk, cfg=…, cwd=…, bundle=…, runner=…, worktree_path=…)`) and never calls `publish`. So it checks that `_run_one` defaults to `confirm=False`, which `test_run_one_without_the_switch_runs_once` (`:292`) already covers. If someone later adds `confirm=True` at `template/src/pdca_harness/publish.py:930`, this test stays green. That is the exact regression clause 4b exists to prevent: a lucky second sample letting a push through. Either drive the real publish host-CI function, or at least assert that the `publish.py:930` call does not pass `confirm`.
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
- Outcome: iterated-to-Do
- Iteration delta (if iterating): The implementation is accepted as correct; only the clause-4b guard test is too weak. `template/tests/test_gate_confirm.py:301-311` (`test_publish_host_ci_rows_run_once`) hand-copies publish's `gates._run_one(...)` call instead of driving publish, so it only re-checks that `_run_one` defaults to `confirm=False` (already covered at `:292`). Adding `confirm=True` at `template/src/pdca_harness/publish.py:930` would leave it green — the exact regression clause 4b exists to prevent. Next attempt: make the test drive the real publish host-CI path with a fail→pass command and assert it records `fail` after ONE run (or, at minimum, assert the `publish.py:930` call does not pass `confirm`). Keep the rest of the patch as is; the minor code-review clean-ups (`_flaky_items` list indexing, dead `rc`/`output` args to `_write_gate_log`) are optional.
- By / date: Eduard Ralph / 2026-09-30

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 5 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
