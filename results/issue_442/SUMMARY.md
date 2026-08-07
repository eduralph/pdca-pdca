# Result — issue 442 / gates-doc-stale-one-marker-claim

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: The evidence-marker paragraph of the `gates.py` module doc
  (`template/src/pdca_harness/gates.py:38` on the target's `main`) still claims
  "``PDCA-UNVERIFIABLE`` stays the one marker that can change a ``result``." Twenty lines
  below, the same docstring introduces ``PDCA-DEFERRED`` (issue #401, `gates.py:55-68`,
  constant at `gates.py:98`) — a second marker that changes a `result` (to `deferred`).
  The sentence predates #401 and is now false; pdca-pdca's issue_401 cycle flagged it
  (SUMMARY §10: "stale once PDCA-DEFERRED lands; fix the sentence in a follow-up") and
  the follow-up never happened.
- Success criterion: The module doc's evidence-marker paragraph no longer claims
  exclusivity for ``PDCA-UNVERIFIABLE``: it names both ``PDCA-UNVERIFIABLE`` and
  ``PDCA-DEFERRED`` as the declarations that can change a ``result`` (e.g. the issue's
  suggested wording "…and only the ``PDCA-UNVERIFIABLE``/``PDCA-DEFERRED`` declarations
  can change a ``result``"). A shipped test reads `gates.__doc__` and fails against the
  stale sentence, passes against the corrected one.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: correct the one false sentence in the `gates.py` module docstring (and ship
  the doc-consistency assertion that pins it) / out of scope: any behavioral change to
  gates.py, any rewording of the rest of the docstring, the stale "rounds rule ships
  disabled" comment in size_signal.py (separate defect, not this issue).

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: unverifiable — <reason>``; leading whitespace ignored) **while exiting 0 or 77** — the marker lets a gate that did NOT fail defer to th
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

Review of issue #442: correct the stale gates module-doc claim so both result-changing declarations are named, with a regression test that proves the clean-base failure and patched success.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The acceptance boundary is unambiguous: accuracy of the normative evidence-marker claim, with behavior explicitly out of scope; the implemented contract identifies the two result-changing declarations at `template/src/pdca_harness/gates.py:38`. |
| C2 Reproduction (red pre-fix) | PASS | Against clean target HEAD `0fbfa26`, the two shipped assertions independently fail because the old doc retains “the one marker” and omits the two-declaration claim; the assertions are grounded at `template/tests/test_gate_deferred.py:295` and `template/tests/test_gate_deferred.py:301`. |
| C3 Change | PASS | The scope decision is satisfied: only the inaccurate sentence and its focused regression coverage change, with no runtime behavior or unrelated documentation affected (`template/src/pdca_harness/gates.py:38`, `template/tests/test_gate_deferred.py:281`). |
| C4 Verification (red→green) | PASS | Independent execution produced 2 failures against clean HEAD plus patched tests, then 2 passes against the patched target; this directly verifies the criterion at `template/tests/test_gate_deferred.py:295`. |
| C5 Causal adequacy | PASS | Correcting the false normative source and pinning both inclusion and removal addresses the documentation defect itself; no capability probe or runtime symptom guard was introduced (`template/src/pdca_harness/gates.py:38`, `template/tests/test_gate_deferred.py:295`). |
| T1 Structure | PASS | The maintainability decision has low risk: the regression is isolated in a named `unittest.TestCase` beside the existing deferred-marker suite and derives marker spellings from production constants (`template/tests/test_gate_deferred.py:281`). |
| T2 Shape | NEEDS-HUMAN | Decide whether the recorded docs-render/link result is sufficient for sign-off — `run-docs-check.sh` is absent from the supplied target/review sandbox, so its green gate could not be independently reproduced; the edited prose itself is well-formed at `template/src/pdca_harness/gates.py:38`. |
| T3 Runtime | PASS | The reported driver-suite red is not reproducible: the project-prescribed `PYTHONPATH=src python3 -m unittest discover -s tests` completed with exit 0 on the patched target, and the change does not alter executable code (`template/src/pdca_harness/gates.py:38`). |
| T4 Contribution | NEEDS-HUMAN | Decide whether to rely on the recorded contribution PASS — the required contribution artifacts/runner were not supplied, so that green result cannot be rerun; affected-path prior-art searches found merged work (including #401) and no closed/rejected matching PR. |
| T5 Judgment | PASS | The review judgment favors acceptance because the patch is narrowly causal, independently red→green, and the only unresolved points concern unavailable auxiliary gate evidence rather than a demonstrated defect (`template/tests/test_gate_deferred.py:301`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether naming both current declarations is the durable wording desired for the public module contract — this determines whether future marker additions should require updating the enumerated claim (`template/src/pdca_harness/gates.py:38`). |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T2 Shape — Decide whether the recorded docs-render/link result is sufficient for sign-off — `run-docs-check.sh` is absent from the supplied target/review sandbox, so its green gate could not be independently reproduced; the edited prose itself is well-formed at `template/src/pdca_harness/gates.py:38`.
- [x] T4 Contribution — Decide whether to rely on the recorded contribution PASS — the required contribution artifacts/runner were not supplied, so that green result cannot be rerun; affected-path prior-art searches found merged work (including #401) and no closed/rejected matching PR.
- [x] Validation — fitness-to-purpose — Decide whether naming both current declarations is the durable wording desired for the public module contract — this determines whether future marker additions should require updating the enumerated claim (`template/src/pdca_harness/gates.py:38`).
- [x] C4 fix verified: bundle test red pre-fix, green post-fix unverifiable — <reason>``; leading whitespace ignored) **while exiting 0 or 77** — the marker lets a gate that did NOT fail defer to th

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
- By / date: Eduard Ralph / 2026-08-06

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
