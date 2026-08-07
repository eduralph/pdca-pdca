# Result — issue 370 / gate-output-evidence-log

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: a gate's full output is discarded: `_run_one` captures the command's
  stdout+stderr (`gates.py:409`), `_classify` keeps only the last line
  (`gates.py:423,446`), the row truncates it to 120 characters (`gates.py:419` /
  `:365`), and nothing writes the rest anywhere. `check-gates.json` / `check-gates.md`
  are the only record a gate run leaves, so the entire evidence for a verdict —
  including a *gating* red that parks the bundle — is one truncated line. Measured
  (wyrd `issue_648`): a transient gating `C4-ci` red recorded only
  `xtask: … failed with exit status: 101`; which test failed is unrecoverable — the
  post-mortem had to be reconstructed from reflog stamps and target-dir mtimes and
  still could not name the test.
- Success criterion: (a) a bundle-scoped gate run writes `gate-logs/<rule_id>.log`
  into the bundle: a small header (command, cwd, `$PDCA_WORKTREE`, start time,
  duration, exit code / outcome) then the combined output verbatim; one file per rule
  id, overwritten per Check run; (b) the row gains `log` (bundle-relative path) and
  `duration_secs`, additively — existing keys and consumers unchanged; (c) the iterate
  archive moves `gate-logs/` alongside the round's other downstream artifacts, so each
  round keeps its own evidence; (d) on timeout (the #368 bound, prior wave), the
  partial capture is attached so a hung gate's log shows *where* it hung instead of
  nothing; (e) a repo-scoped run with no bundle (`pdca gates --working-tree`, the CI
  re-gate) keeps today's behaviour. The 120-char evidence line stays — it is the right
  summary; the defect is that it was also the entire record. Demonstrable by
  C4-verify: unit tests run a stub gate row bundle-scoped and assert the log file's
  header + verbatim body + row keys; an archive-step test asserts per-round retention.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: persist the evidence a bundle-scoped gate run already produces, as in the
  criterion. / out of scope: changing any verdict/classification logic; the timeout
  mechanism itself (#368, prior wave); straggler sweeping (#372); repo-scoped/CI runs.

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
- T3 runtime: render/update-compat + offline driver suites: fail — /tmp/tmp79ntqvkc/results/issue_500/split-proposal.md
- T4 PR body has a user-impact opener + tracker id in both artifacts: pass — pdca-pdca contribcheck
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Issue 370 fixes gate evidence loss by persisting full bundle-scoped gate output logs, adding row metadata, archiving those logs per iteration, and surfacing log-write failures.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The owed behavior is evidence reconstructability without changing gate classification; the brief requires bundle logs, additive row keys, archive retention, timeout partial output, and unchanged repo-scoped behavior (brief.md:16). |
| C2 Reproduction (red pre-fix) | PASS | The missing-evidence defect is real: in a copied target tree with only production hunks reversed, `PYTHONPATH=template/src python3 -m unittest template.tests.test_gate_logs` failed 2F/6E because logs/row keys/archive constants were absent, matching the falsifier (template/tests/test_gate_logs.py:78). |
| C3 Change | PASS | The patch addresses the intended surface: bundle `run_gates` passes `gate-logs` to `_run_checks`, while `run_gates_dry` and repo-scoped `run_working_tree` leave log writing off, preserving the scoped contract (template/src/pdca_harness/gates.py:148). |
| C4 Verification (red→green) | PASS | Manual red→green is reproduced: reversed-production copy failed the new tests, and patched target `PYTHONPATH=template/src python3 -m unittest template.tests.test_gate_logs` ran 9 tests OK, covering header/body, row keys, overwrite, write failure, timeout, repo-scope, dry re-gate, and archive retention (template/tests/test_gate_logs.py:78). |
| C5 Causal adequacy | PASS | The root cause is removed rather than guarded: `_run_one` now persists the captured combined output before returning the row, and write failure is visible through `log_error` plus stderr without changing the gate verdict (template/src/pdca_harness/gates.py:515). |
| T1 Structure | PASS | The structural decision is whether evidence state has one shared spelling and archival path; `state.GATE_LOGS_DIR` is included in `DOWNSTREAM_OF_BRIEF`, and `_archive_iteration` now moves directory artifacts as well as files (template/src/pdca_harness/state.py:53; template/src/pdca_harness/driver.py:390). |
| T2 Shape | NEEDS-HUMAN | The docs/render gate result is provisional: `check-gates.json` names `./engine/scripts/run-docs-check.sh`, but no `run-docs-check.sh` exists under the supplied target checkout, so the recorded pass could not be independently rerun (check-gates.json:60). |
| T3 Runtime | NEEDS-HUMAN | The runtime gate decision is owed because `check-gates.json` records `T3-suite` as fail, but `./engine/scripts/run-suite.sh` is absent in the supplied target checkout; the available fallback `PYTHONPATH=template/src python3 -m unittest discover -s template/tests` passed, so this is unresolved gate-environment evidence rather than a confirmed patch defect (check-gates.json:69). |
| T4 Contribution | NEEDS-HUMAN | The contribution gate is provisional: `pdca-pdca contribcheck 370` is installed but exits with “no pdca.toml found” in this target checkout, so the recorded T4 pass cannot be independently reproduced from the supplied artifacts (check-gates.json:78). |
| T5 Judgment | PASS | Reviewer judgment finds no grounded code defect: prior-art checks by affected paths found no committed `gate-logs`/`duration_secs`/`log_error` implementation in `HEAD`, and the patch avoids the C5 symptom-guard smell-test because it persists existing captured output instead of probing around a load-time side effect (template/src/pdca_harness/gates.py:538). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Human sign-off must decide whether best-effort evidence logs plus visible `log_error` are acceptable operationally when log persistence itself fails, because validation fitness-to-purpose is explicitly human-only even though the deterministic unit evidence is green (template/tests/test_gate_logs.py:129). |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T2 Shape — The docs/render gate result is provisional: `check-gates.json` names `./engine/scripts/run-docs-check.sh`, but no `run-docs-check.sh` exists under the supplied target checkout, so the recorded pass could not be independently rerun (check-gates.json:60).
- [x] T3 Runtime — The runtime gate decision is owed because `check-gates.json` records `T3-suite` as fail, but `./engine/scripts/run-suite.sh` is absent in the supplied target checkout; the available fallback `PYTHONPATH=template/src python3 -m unittest discover -s template/tests` passed, so this is unresolved gate-environment evidence rather than a confirmed patch defect (check-gates.json:69).
- [x] T4 Contribution — The contribution gate is provisional: `pdca-pdca contribcheck 370` is installed but exits with “no pdca.toml found” in this target checkout, so the recorded T4 pass cannot be independently reproduced from the supplied artifacts (check-gates.json:78).
- [x] Validation — fitness-to-purpose — Human sign-off must decide whether best-effort evidence logs plus visible `log_error` are acceptable operationally when log persistence itself fails, because validation fitness-to-purpose is explicitly human-only even though the deterministic unit evidence is green (template/tests/test_gate_logs.py:129).

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
- By / date: Eduard Ralph / 2026-08-01

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
- Reviewer sandbox lacks the instance's `engine/scripts` (T2/T3/T4 gate oracles), so deterministic gate results can't be independently re-run and recur as NEEDS-HUMAN — consider supplying the scripts (or the gate logs) to the reviewer sandbox.
