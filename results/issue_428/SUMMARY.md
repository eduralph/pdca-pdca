# Result — issue 428 / unverifiable-marker-provenance

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: `_classify` honours `PDCA-UNVERIFIABLE:` as a bare substring on **any** line of
  a gate's captured output (`template/src/pdca_harness/gates.py:614-618` on `origin/main`).
  On an exit-0 gate, a line printed by anything the gate ran — a test's stdout, an assertion
  diff, a source comment a test read back — that merely *contains* the literal converts the
  gate's real verdict into `unverifiable`. #329 closed only the `rc != 0` half. Frozen
  evidence, `results/issue_387/check-gates.json`: the **gating** C4 row records
  `"result": "unverifiable"` with the reason
  `` `<reason>` and exit 77\n# (-> SUMMARY §6 NEEDS-HUMAN, non-gating) instead of a red->green … ``
  — a fragment of `engine/scripts/run-verify.sh`'s *comment block*, not a declaration by any
  gate. `unverifiable` does not count toward `overall`, so a genuine green C4 stops being
  recorded as verified and a genuine red would equally be laundered into "defer to the human".
  Structural for any project whose tests exercise the gate machinery: the harness's own suite
  is exactly that (`template/tests/test_gates_unverifiable.py:28,32,103`,
  `template/tests/test_prod_path_gate.py:51-89`).
- Success criterion: With the patch applied, `_classify` records a gate that exits 0 and
  whose captured output contains the marker only **embedded inside a line the gate relayed**
  (e.g. `# … Emit \`PDCA-UNVERIFIABLE: <reason>\` and exit 77`) as its real verdict —
  `pass` — while a gate that **declares** unverifiable itself still records `unverifiable`:
  both the exit-77 channel and the documented exit-0 self-declaration keep working
  (`template/engine/scripts/run-verify.sh:49`, `template/scripts/checks/test_exercises_production.py:24`,
  `template/tests/test_gates_unverifiable.py:103,113`). Demonstrable by C4-verify alone: the
  named test module is red with the production hunk reverted and green with it applied.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: make the recorded `unverifiable` verdict follow the gate's own declaration
  rather than any occurrence of the literal in captured output, and align the normative
  statement of the contract wherever the repo states it
  (`template/PCDA/quality-cycle/04-validation-tooling.md:67,71`,
  `06-quality-cycle-guidelines.md:226`, `08-glossary.md:153`, the `gates.py` module docstring
  at `:19-20` and `_classify`'s own docstring). The discrimination rule is Do's to choose —
  the issue names candidates (marker at line start only · the gate's last output line only ·
  the dedicated exit-77 channel only) and any is acceptable if it satisfies the criterion
  above; state the chosen rule in the docs so gate authors can write to it.
  / **out of scope:** the *evidence line* rule (`output.strip().splitlines()[-1:]`, issue 402
  — a different defect in the same function, briefed separately and scheduled after this);
  the T4 default-open row status (issue 401); changing what `unverifiable` means downstream
  (`assemble._unverifiable_items` → §6 → C6 stays exactly as is); the `rc != 0` half (#329,
  already closed and must not regress).

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
- T3 runtime: render/update-compat + offline driver suites: fail — == T3: root suite OK, driver suite FAILED (rc 1)
- T4 PR body has a user-impact opener + tracker id in both artifacts: pass — pdca-pdca contribcheck
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Review of issue 428: restrict `PDCA-UNVERIFIABLE:` classification to gate-declared lines so relayed marker text no longer turns real gate results into `unverifiable`.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The decision is whether the intended contract is precise enough to test; the brief defines relayed mid-line marker output as `pass` while preserving prefix and rc-77 declarations (`brief.md:20`). |
| C2 Reproduction (red pre-fix) | PASS | The decision is whether the old behavior is actually exposed; with only `template/src/pdca_harness/gates.py` reversed, the added relay tests fail because rows are still classified `unverifiable` (`template/tests/test_gates_unverifiable.py:130`). |
| C3 Change | PASS | The decision is whether the patch changes the relevant contract surface only; the classifier now delegates marker recognition to a prefix-only declaration helper and updates the matching docs/tests (`template/src/pdca_harness/gates.py:599`, `template/PCDA/quality-cycle/04-validation-tooling.md:67`). |
| C4 Verification (red→green) | PASS | The decision is whether the fix, not the added tests alone, causes green; focused unittest was green with the patch and red after reversing the production hunk, with the passing behavior asserted at `template/tests/test_gates_unverifiable.py:136`. |
| C5 Causal adequacy | PASS | The decision is whether this removes the provenance bug rather than masking it; classification now treats only first-text marker lines as declarations and relayed mid-line occurrences fall through to the real exit-code verdict (`template/src/pdca_harness/gates.py:645`). |
| T1 Structure | PASS | The decision is whether ownership boundaries are respected; the change stays within gate classification, its existing test module, and the normative docs named by the brief (`template/src/pdca_harness/gates.py:617`). |
| T2 Shape | NEEDS-HUMAN | The decision owed is whether the rendered-project docs checker actually passed; `check-gates.json` names `./engine/scripts/run-docs-check.sh`, but that script is absent in `$PDCA_TARGET`, so I could not rerun the reported T2 gate. |
| T3 Runtime | NEEDS-HUMAN | The decision owed is whether the reported rendered-project T3 failure is relevant to this patch; `./engine/scripts/run-suite.sh` is absent in `$PDCA_TARGET`, while direct `PYTHONPATH=src python3 -m unittest discover -s tests` passed locally. |
| T4 Contribution | NEEDS-HUMAN | The decision owed is whether the contribution artifacts satisfy the project gate; `pdca_harness.cli contribcheck` cannot run here because this target is the template checkout without a rendered `pdca.toml`. |
| T5 Judgment | PASS | The decision is whether prior art or scope leaves an unresolved advisory concern; affected-path git history and `gh search issues "unverifiable marker"` found #329 plus this issue, with no separate provenance fix already closed. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | The decision owed is final human fitness-to-purpose sign-off: confirm prefix-only declarations are the desired compatibility boundary for real gate authors before accepting the contract change. |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T2 Shape — The decision owed is whether the rendered-project docs checker actually passed; `check-gates.json` names `./engine/scripts/run-docs-check.sh`, but that script is absent in `$PDCA_TARGET`, so I could not rerun the reported T2 gate.
- [x] T3 Runtime — The decision owed is whether the reported rendered-project T3 failure is relevant to this patch; `./engine/scripts/run-suite.sh` is absent in `$PDCA_TARGET`, while direct `PYTHONPATH=src python3 -m unittest discover -s tests` passed locally.
- [x] T4 Contribution — The decision owed is whether the contribution artifacts satisfy the project gate; `pdca_harness.cli contribcheck` cannot run here because this target is the template checkout without a rendered `pdca.toml`.
- [x] Validation — fitness-to-purpose — The decision owed is final human fitness-to-purpose sign-off: confirm prefix-only declarations are the desired compatibility boundary for real gate authors before accepting the contract change.

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
