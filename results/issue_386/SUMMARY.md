# Result — issue 386 / remote-control-test-holds-in-both-postures

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: `template/tests/test_remote_control_docs.py:69-75`
  (`test_it_stays_off_by_default`) walks every line of `pdca.toml` and asserts each line
  containing `--remote-control` starts with `#`. That is right for the **unrendered template**,
  where the flag ships as a commented example. But this suite renders into every instance — it
  is explicitly written to run in both postures (`:19-24` picks `pdca.toml.jinja` or
  `pdca.toml` and derives `RENDERED`; `:45` already skips a rendered-only case) — so an
  instance that **enables** the seam, which is the entire point of documenting it (#337),
  inherits a permanently red test and must carry a local test delta forever. getwyrd/wyrd-pdca
  runs Remote Control on all four interactive leaves (its #176) and had to adapt this test
  during the v0.56.0 template update (its #195). The test pins a template-only *default* as if
  it were a universal invariant.
- Success criterion: with the patch, `template/tests/test_remote_control_docs.py`
  (a) passes on the unrendered template, where the flag is commented; (b) passes on a rendered
  instance whose `pdca.toml` carries an **uncommented** `--remote-control` in the argv of
  `interactive = true` leaves (planner / signoff / publisher / act) — this is the case that is
  red today; and (c) still **fails** on a rendered instance whose `pdca.toml` carries an
  uncommented `--remote-control` in a **headless** leaf's argv (builder / reviewer / any
  advisory leaf), because that flag starts an interactive session with no human to reach and
  hangs the flow. The existing doc-phrase assertions (`APPEND`, "do not add a second",
  `CLAUDE-ONLY`, "headless builder/reviewer must NOT carry it") and the duplicate-argv check
  keep passing unchanged in both postures.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: make the shipped assertion posture-correct — the off-by-default property is
  asserted where it holds, and the property that holds in every posture (the flag rides only
  `interactive = true` leaves, never a headless argv) is asserted in both. / out of scope:
  changing `pdca.toml.jinja`'s Remote Control guidance or its doc phrases in any way (issue
  #396 is open against that block — leave it alone so the two can land independently);
  enabling or disabling the seam anywhere; the other assertions in this module; any driver or
  engine code.

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: unverifiable — no behavioral production change to revert (test-only or docs-only patch)
- C5 Causal adequacy: none — reviewer + human sign-off

## 4. Conformance (Check — stack)
- T1 Structure: none — (no gate configured)
- T2 shape: docs lint + site render link audit: pass — render_site: link audit OK
- T3 runtime: render/update-compat + offline driver suites: fail — /tmp/tmpoya7yqw4/results/issue_500/split-proposal.md
- T4 PR body has a user-impact opener + tracker id in both artifacts: pass — pdca-pdca contribcheck
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Review of issue 386: make `test_remote_control_docs.py` posture-correct so rendered instances may enable `--remote-control` only on interactive leaves while headless leaves remain forbidden.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The owed behavior is explicit: unrendered default stays commented, rendered interactive enrollment passes, and rendered headless enrollment fails, so the patch has a concrete oracle to satisfy (`brief.md:17`). |
| C2 Reproduction (red pre-fix) | PASS | I reproduced the base rendered-interactive failure with `HEAD:template/tests/test_remote_control_docs.py` and a synthetic `[leaves.planner]` argv carrying `--remote-control`; it fails the old universal off-by-default assertion (`template/tests/test_remote_control_docs.py:143`). |
| C3 Change | PASS | The human decision is whether the changed test surface matches the spec; the diff scopes the default assertion to the unrendered template and adds a posture-independent offender check plus rendered posture regressions (`template/tests/test_remote_control_docs.py:53`, `template/tests/test_remote_control_docs.py:130`, `template/tests/test_remote_control_docs.py:194`). |
| C4 Verification (red→green) | NEEDS-HUMAN | Formal C4 remains human-owned because the bundle is test-only and `check-gates.json` reports `PDCA-UNVERIFIABLE`; I did verify the focused patched command `cd template && PYTHONPATH=src python3 -m unittest tests.test_remote_control_docs` is green, but the driver red→green gate could not be rerun here (`check-gates.json:33`). |
| C5 Causal adequacy | PASS | The fix removes the overbroad invariant rather than adding a capability probe; the remaining decision turns on whether `interactive = true` is the intended boundary for allowing the flag, which the new offender check enforces (`template/tests/test_remote_control_docs.py:64`). |
| T1 Structure | PASS | Scope is limited to the defect test file named in the brief, with no template guidance, engine, or driver edits to create issue #396 overlap (`brief.md:57`). |
| T2 Shape | NEEDS-HUMAN | `check-gates.json` reports docs/link audit pass, but this target checkout has no `run-docs-check.sh` at the reported path, so the human must decide whether the rendered gate output is acceptable evidence (`check-gates.json:60`). |
| T3 Runtime | NEEDS-HUMAN | `check-gates.json` reports a runtime-suite failure at an issue_500 artifact, but this target checkout has no `run-suite.sh` at the reported path, so I cannot confirm whether that failure is related to this patch (`check-gates.json:69`). |
| T4 Contribution | NEEDS-HUMAN | `pdca-pdca contribcheck` is installed but cannot run in this source-template target because there is no rendered `pdca.toml`, so the PR/tracker artifact claim needs human or driver-context confirmation (`check-gates.json:78`). |
| T5 Judgment | PASS | Prior-art by affected path is not fixed or in flight: local history shows only `a641742`, GitHub search shows #337/#386/#396, and open PR list is empty; #396 is a different-file collision left out of scope (`brief.md:86`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Required human sign-off: decide whether synthetic rendered configs plus the focused unittest are sufficient fitness evidence for shipped-instance behavior, especially because the formal C4 gate is intentionally unverifiable for this test-only bundle (`brief.md:36`). |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] C4 Verification (red→green) — Formal C4 remains human-owned because the bundle is test-only and `check-gates.json` reports `PDCA-UNVERIFIABLE`; I did verify the focused patched command `cd template && PYTHONPATH=src python3 -m unittest tests.test_remote_control_docs` is green, but the driver red→green gate could not be rerun here (`check-gates.json:33`).
- [x] T2 Shape — `check-gates.json` reports docs/link audit pass, but this target checkout has no `run-docs-check.sh` at the reported path, so the human must decide whether the rendered gate output is acceptable evidence (`check-gates.json:60`).
- [x] T3 Runtime — `check-gates.json` reports a runtime-suite failure at an issue_500 artifact, but this target checkout has no `run-suite.sh` at the reported path, so I cannot confirm whether that failure is related to this patch (`check-gates.json:69`).
- [x] T4 Contribution — `pdca-pdca contribcheck` is installed but cannot run in this source-template target because there is no rendered `pdca.toml`, so the PR/tracker artifact claim needs human or driver-context confirmation (`check-gates.json:78`).
- [x] Validation — fitness-to-purpose — Required human sign-off: decide whether synthetic rendered configs plus the focused unittest are sufficient fitness evidence for shipped-instance behavior, especially because the formal C4 gate is intentionally unverifiable for this test-only bundle (`brief.md:36`).
- [x] C4 fix verified: bundle test red pre-fix, green post-fix unverifiable — no behavioral production change to revert (test-only or docs-only patch)

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
- Reviewer re-runs gates from `$PDCA_TARGET` instead of the instance root with `PDCA_WORKTREE=`, so T2/T3/T4 land as NEEDS-HUMAN (cleared on 356, not on 380/386/387).
