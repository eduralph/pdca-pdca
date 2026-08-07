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
- T3 runtime: render/update-compat + offline driver suites: fail — /tmp/tmpwh2crglt/results/issue_500/split-proposal.md
- T4 PR body has a user-impact opener + tracker id in both artifacts: pass — pdca-pdca contribcheck
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Task under review: persist full bundle-scoped gate output as per-rule `gate-logs/` evidence, add row metadata, and archive logs per iteration.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief defines a bounded evidence-retention defect and explicit success criteria for bundle logs, row keys, timeout partial output, archive retention, and unchanged repo-scoped behavior (`brief.md:10`). |
| C2 Reproduction (red pre-fix) | PASS | Red was reproduced on a base snapshot with the new test: assertions failed for missing `gate-logs`, missing `log`, and missing `state.GATE_LOGS_DIR`; literal stash was blocked by read-only git metadata, not by the patch (`template/tests/test_gate_logs.py:74`). |
| C3 Change | PASS | The changed surfaces match the requested data path: bundle `run_gates` passes a log directory, per-row execution writes evidence, and iteration archive handles directories (`template/src/pdca_harness/gates.py:146`; `template/src/pdca_harness/driver.py:390`). |
| C4 Verification (red→green) | NEEDS-HUMAN | Exact `C4-verify` cannot be affirmed here because the target verifier is still the skeleton that exits 1, while the independently run focused unittest is red on base and green with the patch (`template/engine/scripts/run-verify.sh:50`; `template/tests/test_gate_logs.py:97`). |
| C5 Causal adequacy | FAIL | Human must decide whether evidence persistence may be best-effort: a `gate-logs` path collision produced a passing gate row with no `log`/`duration_secs`, so the original "verdict without full basis" failure can still occur (`template/src/pdca_harness/gates.py:554`). |
| T1 Structure | PASS | The patch keeps one shared directory spelling in state and reuses the existing downstream archive list rather than adding a separate archive mechanism (`template/src/pdca_harness/state.py:53`). |
| T2 Shape | NEEDS-HUMAN | The configured docs gate could not be rerun because `run-docs-check.sh` is absent in this target checkout; the reported green row is provisional, not independently verified. |
| T3 Runtime | NEEDS-HUMAN | The configured `T3-suite` runner could not be rerun because `run-suite.sh` is absent here; available `python3 -m unittest discover -s template/tests` exited 0, but the reported T3 red remains environment/provenance-dependent. |
| T4 Contribution | NEEDS-HUMAN | `pdca-pdca contribcheck` is installed but cannot run in this source checkout without a rendered `pdca.toml`, so the contribution artifact check is provisional. |
| T5 Judgment | NEEDS-HUMAN | Human judgment is owed on whether the best-effort log-write behavior is acceptable despite the evidence-sufficiency invariant and the reproduced collision case (`template/src/pdca_harness/gates.py:557`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Human sign-off must decide whether the remaining operational gap is acceptable: ordinary focused tests pass, but exact harness gates were not reproducible in this target environment. |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] C4 Verification (red→green) — Exact `C4-verify` cannot be affirmed here because the target verifier is still the skeleton that exits 1, while the independently run focused unittest is red on base and green with the patch (`template/engine/scripts/run-verify.sh:50`; `template/tests/test_gate_logs.py:97`).
- [ ] T2 Shape — The configured docs gate could not be rerun because `run-docs-check.sh` is absent in this target checkout; the reported green row is provisional, not independently verified.
- [ ] T3 Runtime — The configured `T3-suite` runner could not be rerun because `run-suite.sh` is absent here; available `python3 -m unittest discover -s template/tests` exited 0, but the reported T3 red remains environment/provenance-dependent.
- [ ] T4 Contribution — `pdca-pdca contribcheck` is installed but cannot run in this source checkout without a rendered `pdca.toml`, so the contribution artifact check is provisional.
- [ ] T5 Judgment — Human judgment is owed on whether the best-effort log-write behavior is acceptable despite the evidence-sufficiency invariant and the reproduced collision case (`template/src/pdca_harness/gates.py:557`).
- [ ] Validation — fitness-to-purpose — Human sign-off must decide whether the remaining operational gap is acceptable: ordinary focused tests pass, but exact harness gates were not reproducible in this target environment.

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
- Iteration delta (if iterating): Advisory C5 FAIL upheld by the human: the gate-log write failure must NOT be silent. Today `_write_gate_log` returns None on OSError and the row is emitted with no `log`/`duration_secs` and no other signal — the feature's own promise ("full basis reconstructable from bundle files alone") can silently not happen, echoing the original #370 defect. Keep the builder's invariant that evidence persistence never breaks the gate run or alters a verdict; but on a write failure, surface it visibly — e.g. an additive row key (`log_error` with the reason) and a stderr line — and cover the reproduced collision case (a file squatting on the `gate-logs` path) with a test. Everything else in the patch stood up well (C4 red→green, C1/C2/C3/T1 advisory PASS); this is a targeted rebuild, not a redesign.
- By / date: Eduard Ralph / 2026-08-01

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
