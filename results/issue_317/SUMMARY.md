# Result — issue 317 / pdca-record

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: a `pdca record [<ids>…]` verb that commits terminal result bundles to the
  instance repo (and, opt-in, opens one PR for the batch) — so a bundle's state stops
  living on one machine only. Observed: four wyrd bundles uncommitted for five days,
  including a DISCONTINUED one whose §9 was the sole provenance for an open upstream PR.
- Success criterion: (a) `pdca record` with no ids selects exactly the bundles whose
  `state.state` is terminal-finished — COMPLETE, DISCONTINUED, RESOLVED — and excludes
  UNPLANNED and AWAITING_SIGNOFF (halted-for-a-human) and every in-motion state;
  (b) the selected batch is staged and committed as one commit with the configured
  conventional subject; (c) `[records] mode = "pr"` additionally branches, pushes and
  opens one PR for the whole batch (git/gh stubbed in tests); (d) `mode = "off"` — the
  default — is byte-identical to today (no new behaviour anywhere, including for
  instances that do not version `results/`); (e) classification is `state.state`, not a
  re-implementation (asserted: the selection changes when the state files change,
  with no duplicated state-enumeration in the new module). Demonstrable by C4-verify;
  red on current `main` — no `record` subparser exists (verified against `cli.py`) and
  `HALTED` (`state.py:31`) has no consumer that commits bundles.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: the `record` verb (new engine module + `cli.py` wiring + `[records]` config:
  `mode = off|commit|pr` (default off), `branch`, `subject`, `issue = ask|<N>`);
  selection via `state.state` ∈ {COMPLETE, DISCONTINUED, RESOLVED}; batch-by-default
  (one commit / one PR per invocation); deterministic git/gh subprocesses in the
  `publish.py` shape, no model in the loop. If publish triggers recording, the call runs
  strictly *after* `publish()` writes `publish.json` — never mid-publish. / out of
  scope: any auto-commit of non-terminal bundles; changing what publish itself does;
  retiring wyrd's interim script.

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
- T3 runtime: render/update-compat + offline driver suites: fail — /tmp/tmpr2shjq_b/results/issue_500/split-proposal.md
- T4 PR body has a user-impact opener + tracker id in both artifacts: pass — pdca-pdca contribcheck
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Review task: add `pdca record [<ids>...]` to commit terminal-finished result bundles, optionally opening one batch PR.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief defines the selection, commit, PR, off-mode, and post-publish contracts clearly enough to judge implementation impact (`brief.md:7`). |
| C2 Reproduction (red pre-fix) | PASS | A temp copy with `patch.diff` reversed rejects `record` as an argparse invalid choice, so the pre-fix command surface is red (`template/src/pdca_harness/cli.py:396`). |
| C3 Change | PASS | The implementation adds the verb, config, state-owned terminal set, engine, publish hook, and tests within the requested surface (`template/src/pdca_harness/record.py:33`). |
| C4 Verification (red→green) | NEEDS-HUMAN | Decide whether the local red→green substitute is sufficient: exact `./engine/scripts/run-verify.sh` was unavailable at `$PDCA_TARGET` root and Git stash could not write the read-only worktree index, though `python3 template/tests/test_record.py` passed 15 tests (`template/tests/test_record.py:352`). |
| C5 Causal adequacy | PASS | The fix consumes `state.state` plus `state.TERMINAL`, so the safety predicate is centralized rather than re-enumerated in the new command (`template/src/pdca_harness/record.py:52`). |
| T1 Structure | PASS | The change is structured around one new engine module with narrow CLI/config/publish/state integration points, matching the existing command-module shape (`template/src/pdca_harness/cli.py:485`). |
| T2 Shape | NEEDS-HUMAN | Decide whether to accept shape without the configured docs wrapper: `./engine/scripts/run-docs-check.sh` was unavailable at `$PDCA_TARGET` root, so its recorded pass could not be independently re-run (`check-gates.json:29`). |
| T3 Runtime | NEEDS-HUMAN | Decide whether the recorded non-gating T3 failure is stale or material: local `python3 -m unittest discover -s template/tests` passed, but the exact `./engine/scripts/run-suite.sh` row was unavailable and `check-gates.json` reports a generated `split-proposal.md` failure (`check-gates.json:39`). |
| T4 Contribution | NEEDS-HUMAN | Decide prior-art/comtribution completeness beyond local history: affected-file `git log` and `--grep '#317'` found no record work, but the configured `pdca-pdca contribcheck` pass could not be re-run here (`check-gates.json:48`). |
| T5 Judgment | NEEDS-HUMAN | Decide the headless `issue = "ask"` behavior and best-effort post-publish recording scope: the implementation chooses commit-only fallback and never fails publish, which matches the brief's direction but is still policy-significant (`template/src/pdca_harness/record.py:95`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Human sign-off must decide whether batch-recording terminal bundles is the right operational answer for preventing local-only provenance, independent of the passing offline tests (`brief.md:7`). |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] C4 Verification (red→green) — Decide whether the local red→green substitute is sufficient: exact `./engine/scripts/run-verify.sh` was unavailable at `$PDCA_TARGET` root and Git stash could not write the read-only worktree index, though `python3 template/tests/test_record.py` passed 15 tests (`template/tests/test_record.py:352`).
- [x] T2 Shape — Decide whether to accept shape without the configured docs wrapper: `./engine/scripts/run-docs-check.sh` was unavailable at `$PDCA_TARGET` root, so its recorded pass could not be independently re-run (`check-gates.json:29`).
- [x] T3 Runtime — Decide whether the recorded non-gating T3 failure is stale or material: local `python3 -m unittest discover -s template/tests` passed, but the exact `./engine/scripts/run-suite.sh` row was unavailable and `check-gates.json` reports a generated `split-proposal.md` failure (`check-gates.json:39`).
- [x] T4 Contribution — Decide prior-art/comtribution completeness beyond local history: affected-file `git log` and `--grep '#317'` found no record work, but the configured `pdca-pdca contribcheck` pass could not be re-run here (`check-gates.json:48`).
- [x] T5 Judgment — Decide the headless `issue = "ask"` behavior and best-effort post-publish recording scope: the implementation chooses commit-only fallback and never fails publish, which matches the brief's direction but is still policy-significant (`template/src/pdca_harness/record.py:95`).
- [x] Validation — fitness-to-purpose — Human sign-off must decide whether batch-recording terminal bundles is the right operational answer for preventing local-only provenance, independent of the passing offline tests (`brief.md:7`).

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
