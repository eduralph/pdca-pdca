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

Review scope: unify single- and multi-ID `pdca flow` on one results-map path while preserving disposition/exit semantics and giving split parents safe recovery guidance.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The required invariant is concrete and falsifiable: every named bundle state must affect both presentations and the shared exit rule at `template/src/pdca_harness/cli.py:612`. |
| C2 Reproduction (red pre-fix) | PASS | Against an exported clean `f7876f2` base with the new test retained, all 9 tests executed and the module failed (8 failures, 1 error), including the route and abort-path reproductions at `template/tests/test_flow_entrypoint_parity.py:183` and `template/tests/test_flow_entrypoint_parity.py:209`. |
| C3 Change | FAIL | A skipped DISCONTINUED id is removed at `template/src/pdca_harness/flow.py:1100`, so DISCONTINUED alone returns rc 1 but the same disk state plus a completing filler returns rc 0 and reports `1/1 complete`; the promised multi-ID rule is still violated. |
| C4 Verification (red→green) | FAIL | The asserted module is genuinely red→green (9 executed tests), but it leaves the batch code in `_rc2` unasserted at `template/tests/test_flow_entrypoint_parity.py:264`; a focused patched run reproduced rc 1 versus rc 0, so the success criterion is not green. |
| C5 Causal adequacy | FAIL | Arity-dependent authority remains: single-ID reporting reconstructs a filtered terminal result from disk at `template/src/pdca_harness/cli.py:654`, while batch reporting sees only the incomplete map, so parity is not by construction. |
| T1 Structure | FAIL | The decision still has two inputs—the returned map and a single-only disk fallback at `template/src/pdca_harness/cli.py:649`—which permits the observed exit-rule divergence. |
| T2 Shape | PASS | Docs lint, 22-page render/link audit, `git diff --check`, and Python compilation all passed; the changed call-site mocks match the shared entry point at `template/tests/test_flow_slice.py:1711`. |
| T3 Runtime | FAIL | The full offline driver suite and all 7 Copier render/update tests passed, but the directly exercised DISCONTINUED matrix case still changes rc by CLI shape; the missing batch assertion is visible at `template/tests/test_flow_entrypoint_parity.py:260`. |
| T4 Contribution | NEEDS-HUMAN | Maintainer must verify the final commit sign-off/conventional subject and PR user-impact opener plus `Closes #468` — neither contribution artifact is supplied and the independent `contribcheck` therefore deferred; these rules affect publishability (`AGENTS.md:21`). |
| T5 Judgment | FAIL | Affected-path prior art was checked across `origin/main` history and GitHub's complete closed/unmerged corpus (1 PR, no affected-path hit), but the test's claim that DISCONTINUED uses the same rule is contradicted by its unexamined `_rc2` at `template/tests/test_flow_entrypoint_parity.py:264`. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Maintainer must decide whether the corrected terminal-set report and exit semantics fit operator/automation expectations — the current rc 1/rc 0 split changes automation outcomes for the same DISCONTINUED bundle (`template/tests/test_flow_entrypoint_parity.py:260`). |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T4 Contribution — Maintainer must verify the final commit sign-off/conventional subject and PR user-impact opener plus `Closes #468` — neither contribution artifact is supplied and the independent `contribcheck` therefore deferred; these rules affect publishability (`AGENTS.md:21`).
- [ ] Validation — fitness-to-purpose — Maintainer must decide whether the corrected terminal-set report and exit semantics fit operator/automation expectations — the current rc 1/rc 0 split changes automation outcomes for the same DISCONTINUED bundle (`template/tests/test_flow_entrypoint_parity.py:260`).

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
- Iteration delta (if iterating): Auto-iterate (round 2): Check found implementation-level items only, no architectural judgment required — T4 Contribution — Maintainer must verify the final commit sign-off/conventional subject and PR user-impact opener plus `Closes #468` — neither contribution artifact is supplied and the independent `contribcheck` therefore deferred; these rules affect publishability (`AGENTS.md:21`).
- By / date: auto-iterate / 2026-08-09

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
