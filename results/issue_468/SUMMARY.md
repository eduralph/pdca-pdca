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

Reviewing issue #468's unification of single- and multi-ID `pdca flow` entry points around one total results-map drive path, including safe split-parent recovery guidance.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | Acceptance turns on CLI-level parity across the stated bundle states while preserving the intentional single-ID AWAITING_SIGNOFF stop semantics; the boundary and exception are directly executable (`template/tests/test_flow_entrypoint_parity.py:197`, `template/tests/test_flow_entrypoint_parity.py:388`). |
| C2 Reproduction (red pre-fix) | PASS | The production-only reversal reproduced the defect with 11 failures and one uncaught `PreflightError`, including the destructive split-parent `rm -rf` advice guarded by the regression at `template/tests/test_flow_entrypoint_parity.py:344`. |
| C3 Change | PASS | The change is acceptable because both arities now cross the same `flow_ids` call and consume only its returned map, while every requested terminal or unplanned ID receives a disposition (`template/src/pdca_harness/cli.py:613`, `template/src/pdca_harness/flow.py:1112`). |
| C4 Verification (red→green) | PASS | Independent replay moved the focused suite from red (11 failures, 1 error) to 11/11 green, including common PreflightError handling and the full state matrix (`template/tests/test_flow_entrypoint_parity.py:277`, `template/tests/test_flow_entrypoint_parity.py:302`). |
| C5 Causal adequacy | PASS | The root-cause decision is discharged: arity no longer selects a separate drive authority, the returned map is total, and the patch adds no optional-capability probe that could mask an eager/load-time cause (`template/src/pdca_harness/cli.py:613`, `template/src/pdca_harness/flow.py:1113`). |
| T1 Structure | PASS | Scope remains one logical flow-entrypoint change: CLI routing/presentation, flow result/hint semantics, and directly coupled tests; the legacy library driver is explicitly separated from the CLI contract (`template/src/pdca_harness/flow.py:377`). |
| T2 Shape | PASS | Contract-shape compatibility is supported by updated total-map callers plus independently green documentation lint and 22-page link audit (`template/tests/test_flow_slice.py:404`, `template/tests/test_state_resolved.py:145`). |
| T3 Runtime | PASS | Runtime compatibility is independently green: 11 focused tests, 1,633 offline driver tests (2 skips), and all 7 Copier render/update tests passed; the preserved single-ID output and rc behavior is exercised at `template/tests/test_flow_entrypoint_parity.py:388`. |
| T4 Contribution | NEEDS-HUMAN | Maintainer must verify the final commit's DCO/conventional subject and the PR's user-impact opener plus `Closes #468` — commit/PR artifacts were not supplied, so the recorded `contribcheck` PASS cannot be replayed and publishability depends on these rules (`AGENTS.md:21`, `AGENTS.md:25`). |
| T5 Judgment | PASS | Prior-art overlap is mechanically settled: affected-path merged history was inspected and GitHub's only closed-unmerged PR (#4) changes only `README.md`, not the reviewed CLI/flow seams (`template/src/pdca_harness/cli.py:558`, `template/src/pdca_harness/flow.py:1052`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Maintainer must decide whether the resulting messages and exit semantics fit real operator workflows — the hermetic suite proves mechanics without a live tracker/interactive topology; run single- and multi-ID `pdca flow` on the same real terminal split parent and confirm matching disposition/rc, child recovery, and no `rm -rf` advice (`template/tests/test_flow_entrypoint_parity.py:6`). |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T4 Contribution — Maintainer must verify the final commit's DCO/conventional subject and the PR's user-impact opener plus `Closes #468` — commit/PR artifacts were not supplied, so the recorded `contribcheck` PASS cannot be replayed and publishability depends on these rules (`AGENTS.md:21`, `AGENTS.md:25`).
- [x] Validation — fitness-to-purpose — Maintainer must decide whether the resulting messages and exit semantics fit real operator workflows — the hermetic suite proves mechanics without a live tracker/interactive topology; run single- and multi-ID `pdca flow` on the same real terminal split parent and confirm matching disposition/rc, child recovery, and no `rm -rf` advice (`template/tests/test_flow_entrypoint_parity.py:6`).
- [x] size backstop — this slice is behaving oversized: 2 round(s) already spent (threshold 2). Recommend answering `iterate-plan` at sign-off and authoring the split in the re-plan (`pdca split`), rather than `iterate-do`: a slice that is too big yields implementation-shaped findings every round, and splitting authors briefs, which is Plan's beat.

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
- By / date: Eduard Ralph / 2026-08-09

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
