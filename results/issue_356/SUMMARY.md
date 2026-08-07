# Result — issue 356 / loop-telemetry-records-the-effective-tier

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: `_record_loop_attempt` (`template/src/pdca_harness/leaves.py:1214-1238`) records
  each Do attempt as `label = builder.argv[0] if builder.argv else builder.mode` plus
  `builder.family` (`:1232-1233`). For an escalation ladder that climbs **within one vendor** —
  the shape both the docs and the shipped `[[leaves.builder_escalation]]` example suggest
  (sonnet/high → opus/xhigh → opus/max) — every tier writes the identical
  `{"builder": "claude", "family": "claude"}`, so `loop-telemetry.json` cannot say which tier a
  bundle actually passed on. That is the one question the file exists to answer: its own
  docstring calls the attempt count "the go/no-go metric for adopting a cheaper local executor"
  (`:1215-1219`) and `pdca.toml.jinja`'s `builder_escalation` comment promises "which backend
  ran each pass". Cross-**vendor** ladders are distinguishable today; same-vendor ones are not.
  Found by a Codex review on the gramps-testbed-v2 instance (eduralph/gramps-testbed-v2#334).
- Success criterion: each entry `_record_loop_attempt` appends to `loop-telemetry.json`
  names the tier that **actually ran** the attempt, additively: alongside today's `n`,
  `builder`, `family` it records the effective model and the effective effort, resolved with
  **argv precedence** —
  (a) when the selected builder's argv already carries the family's model flag / effort mapping
  (`--model sonnet`, `-m opus`, `-c model_reasoning_effort=low`, and the `=`-joined `--model=…`
  form), the recorded values are those **argv** values;
  (b) when argv is silent, they are the leaf's `model` / `effort` keys;
  (c) when neither is set, they are empty strings — never a guessed CLI default;
  (d) the probe that decides (a) matches the flag token **exactly**, so a family whose model
  flag is `-m` does not match inside an unrelated `--model-info`-style argument.
  `n`, `builder` and `family` keep their existing shape and meaning (`_resolved_builder_family`,
  #200, reads `family`), and the sidecar stays best-effort — nothing here may raise out of Do.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: make the recorded attempt name the effective backend tier, including within one
  vendor. / out of scope: changing or reinterpreting `n` / `builder` / `family` (readers depend
  on them, #200); the ladder and selection logic (`select_builder`, `[[leaves.builder_variant]]`
  / `[[leaves.builder_escalation]]` semantics); telemetry for the reviewer, advisory or any
  other leaf; new `pdca.toml` keys; any change to `_mapped_argv`'s own behaviour; consumers /
  reporting of `loop-telemetry.json`.

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
- T3 runtime: render/update-compat + offline driver suites: fail — /tmp/tmpy3l4odvi/results/issue_500/split-proposal.md
- T4 PR body has a user-impact opener + tracker id in both artifacts: pass — pdca-pdca contribcheck
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Review of issue 356: make `loop-telemetry.json` identify the effective builder tier, including same-vendor escalation ladders.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The owed behavior is explicit enough to judge: telemetry must distinguish the tier that actually ran while preserving `n`/`builder`/`family`, matching `_mapped_argv` argv precedence at `template/src/pdca_harness/leaves.py:150`. |
| C2 Reproduction (red pre-fix) | PASS | The reproduced red leg matters because base source plus the new test file fails with missing `model`/`effort` and the old 3-arg writer contract, while the test asserts the new tier fields at `template/tests/test_loop_escalation.py:215`. |
| C3 Change | PASS | The change addresses the judged surface directly: `_effective_tier` derives model/effort from argv first and falls back to leaf keys, then `_record_loop_attempt` writes them additively at `template/src/pdca_harness/leaves.py:1232` and `template/src/pdca_harness/leaves.py:1286`. |
| C4 Verification (red→green) | PASS | Re-ran `/home/eddie/pdca/pdca-pdca/engine/scripts/run-verify.sh` with this bundle: green with patch, red with production hunks reverted, proving `template/tests/test_loop_escalation.py:118` captures the defect. |
| C5 Causal adequacy | PASS | The root-cause decision is not contested: the old sidecar could only record identical same-vendor `builder`/`family`, and the patch records the effective tier using the same precedence as the invocation mapper at `template/src/pdca_harness/leaves.py:150`. |
| T1 Structure | PASS | The scope decision is contained to the telemetry writer, its caller, its direct tests, and the shipped config comment; no unrelated module boundary is crossed beyond the caller that now passes `cfg` at `template/src/pdca_harness/leaves.py:1340`. |
| T2 Shape | PASS | Re-ran docs lint and site render/link audit with `PDCA_WORKTREE=$PDCA_TARGET`; both passed, and the changed template comment remains coherent at `template/pdca.toml.jinja:396`. |
| T3 Runtime | PASS | Re-ran the driver runtime suite with `PDCA_WORKTREE=$PDCA_TARGET`; it exited 0 locally, so the frozen advisory T3 failure in `check-gates.json` was not reproduced against this target state. |
| T4 Contribution | NEEDS-HUMAN | Contribution artifacts were withheld from this reviewer, so the human must decide whether the frozen T4 pass is sufficient before publication. |
| T5 Judgment | PASS | Prior-art check by affected paths found the existing telemetry writer/caller history and no separate open PR from `gh pr list`; the human-facing decision is only whether to accept the additive sidecar fields as the right published contract. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Human sign-off must decide whether recording empty strings for CLI defaults is fit for telemetry consumers, because final product semantics are intentionally outside deterministic gates. |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T4 Contribution — Contribution artifacts were withheld from this reviewer, so the human must decide whether the frozen T4 pass is sufficient before publication.
- [x] Validation — fitness-to-purpose — Human sign-off must decide whether recording empty strings for CLI defaults is fit for telemetry consumers, because final product semantics are intentionally outside deterministic gates.

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
