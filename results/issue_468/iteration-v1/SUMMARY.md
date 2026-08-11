# Result — issue 468 / flow-entrypoint-parity

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: 
- Success criterion: exercised **through `cli._flow`** (never hand-picked `flow.*`
  calls) on byte-identical disk state, the single-id and multi-id shapes agree by
  construction: for every bundle state in {in-flight, COMPLETE, DISCONTINUED, RESOLVED,
  terminal-with-`close-disposition = split`}, both shapes report the same per-bundle
  disposition for the shared id and derive their exit code from the same results-map
  rule, and an error meant to abort a run (e.g. `flow.PreflightError`) produces the same
  rc on both shapes. A terminal split parent (lineage record with a `children` key) is
  never told `rm -rf`; its message names the recovery (`pdca flow <child-ids>`).
  Preserved single-id presentation, derived from the map: the AWAITING_SIGNOFF listing
  of open §6 items and its rc-0 stop-for-the-human semantics. Demonstrable by C4-verify
  on the patch alone.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: route both CLI shapes through one drive path returning one results map
  (e.g. `flow.flow` becomes a thin wrapper over `flow_ids`, or `cli._flow` routes
  `len(ids) == 1` through the batch machinery — Do's call, provided the parity is
  by construction); move the pre-run terminal checks (`cli.py:604-637`, COMPLETE
  short-circuit + RESOLVED revalidation) so the DECISION lives once on the shared path
  (RESOLVED revalidation already exists in `flow_ids` at `flow.py:1005-1016` — do not
  duplicate it); make the terminal-split-parent message lineage-aware (`rm -rf` advice
  is destructive there); keep the single-id presentation (needs-human listing, rc 0 at
  AWAITING_SIGNOFF, `state<TAB>path` line) as a presentation of the shared map.
  / out of scope: split-child ADOPTION (child-2 — this slice makes the ground safe for
  it; children of a split parent stay PLANNED here); any change to `_drive_and_act`'s
  wave/fold/budget semantics, `waves.py`, `split.py`, publish or Act; the batch shapes'
  `_report_batch` exit rule for multi-id sets (rc 0 iff all COMPLETE/RESOLVED — stays);
  the pre-existing T3 red (11 failures in `template/tests/test_verify_base.py` under an
  inherited `PDCA_VERIFY_BASE` — verified pre-existing isolation fault, non-gating,
  expect it, do not chase it).

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
- T3 runtime: render/update-compat + offline driver suites: pass — == T3: root suite OK, driver suite OK
- T4 PR body has a user-impact opener + tracker id in both artifacts: pass — ./scripts/pdca contribcheck
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Reviewing issue #468: unify single- and multi-id `flow` CLI execution on one results-map path while preserving single-id presentation and giving split parents safe recovery guidance.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The acceptance decision is concrete and falsifiable across routing, state parity, error handling, sign-off presentation, and split recovery, with the shared call seam grounded at `template/src/pdca_harness/cli.py:607`. |
| C2 Reproduction (red pre-fix) | PASS | With all 8 focused tests retained and only production hunks reverted, 8 tests ran and produced 4 failures plus 1 error, including the single-route assertion at `template/tests/test_flow_entrypoint_parity.py:181` and split-parent case at `template/tests/test_flow_entrypoint_parity.py:275`. |
| C3 Change | FAIL | The change must preserve tolerant lineage handling: `children = 7` makes `cli._flow` raise `TypeError` because the new formatter joins an unvalidated value at `template/src/pdca_harness/flow.py:670`, contradicting the nonfatal-malformation contract at `template/src/pdca_harness/split.py:376`. |
| C4 Verification (red→green) | PASS | The focused module ran 8 real tests red without the production fix and all 8 green with it, directly exercising the shared route and preserved presentation from `template/tests/test_flow_entrypoint_parity.py:181`. |
| C5 Causal adequacy | PASS | The asymmetry is removed at its cause: both nonempty CLI shapes obtain one `flow_ids` results map before presentation at `template/src/pdca_harness/cli.py:607`, with no capability probe or downstream symptom guard. |
| T1 Structure | PASS | The routing consolidation is localized to one call seam and one recovery helper, and both `git diff --check` and `compileall` passed; the shared presentation boundary is at `template/src/pdca_harness/cli.py:614`. |
| T2 Shape | PASS | Independent docs lint, 22-page render, and link audit all passed, so no documentation-shape decision remains for this code-only patch. |
| T3 Runtime | NEEDS-HUMAN | Whether render/update compatibility remains intact must be decided after installing Copier and rerunning those checks — Copier is absent and all 7 root render/update tests skipped, so that portion of the recorded T3 green is provisional; the independently reproduced lineage crash is recorded under C3/T5. |
| T4 Contribution | NEEDS-HUMAN | Whether the contribution has the required impact opener and tracker references must be decided from the actual commit message and PR body — neither artifact nor the instance-level `contribcheck` wrapper is among the supplied review inputs, so the recorded green cannot be rerun. |
| T5 Judgment | FAIL | Do not accept until malformed lineage degrades only the hint rather than aborting `flow`: the target promises that behavior at `template/src/pdca_harness/split.py:373`, but the join at `template/src/pdca_harness/flow.py:674` crashes; a path-based audit of merged and closed PRs found no closed-unmerged/rejected duplicate touching the five affected files. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | The maintainer must decide whether moving single-id operation onto batch-wave semantics preserves the intended operator experience — especially interactive sign-off and terminal output at `template/src/pdca_harness/cli.py:614` — because fitness-to-purpose remains human-only even after the runtime defect is corrected. |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T3 Runtime — Whether render/update compatibility remains intact must be decided after installing Copier and rerunning those checks — Copier is absent and all 7 root render/update tests skipped, so that portion of the recorded T3 green is provisional; the independently reproduced lineage crash is recorded under C3/T5.
- [ ] T4 Contribution — Whether the contribution has the required impact opener and tracker references must be decided from the actual commit message and PR body — neither artifact nor the instance-level `contribcheck` wrapper is among the supplied review inputs, so the recorded green cannot be rerun.
- [ ] Validation — fitness-to-purpose — The maintainer must decide whether moving single-id operation onto batch-wave semantics preserves the intended operator experience — especially interactive sign-off and terminal output at `template/src/pdca_harness/cli.py:614` — because fitness-to-purpose remains human-only even after the runtime defect is corrected.

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
- Iteration delta (if iterating): Auto-iterate (round 1): Check found implementation-level items only, no architectural judgment required — T3 Runtime — Whether render/update compatibility remains intact must be decided after installing Copier and rerunning those checks — Copier is absent and all 7 root render/update tests skipped, so that portion of the recorded T3 green is provisional; the independently reproduced lineage crash is recorded under C3/T5.; T4 Contribution — Whether the contribution has the required impact opener and tracker references must be decided from the actual commit message and PR body — neither artifact nor the instance-level `contribcheck` wrapper is among the supplied review inputs, so the recorded green cannot be rerun.
- By / date: auto-iterate / 2026-08-09

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
