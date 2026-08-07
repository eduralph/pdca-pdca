# Result — issue 368 / gate-timeout

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: a gate command has no bound anywhere in the chain: `gates._run_one`
  invokes the command through `progress.run_with_heartbeat` (`gates.py:409`) and
  `run_with_heartbeat` has no `timeout` parameter in its signature
  (`progress.py:25-37`, verified on main — `interval` is only the heartbeat tick), and
  the `[[gates.checks]]` schema has no per-gate timeout field. A hung gate stalls the
  Check beat indefinitely — measured: an advisory (`gating = false`) `C5-mutants` row
  held a wyrd Check beat for 19h 16m until a human interrupted it, while the heartbeat
  printed `… still working` — the mechanism built so a slow gate would not look hung is
  what stopped a genuinely hung gate from looking hung.
- Success criterion: (a) `run_with_heartbeat` accepts `timeout: int | None = None`;
  on expiry the child process **group** is terminated (gates run under `shell=True` —
  killing only the shell orphans the real work) and a distinguishable timed-out outcome
  is returned; `timeout=None` is byte-identical to today. (b) A `[[gates.checks]]` row
  may carry `timeout_secs`, with a `[gates] default_timeout_secs` fallback; a row that
  times out is recorded **`unverifiable`**, not `fail` — kept out of the gating verdict,
  surfaced at sign-off — with an evidence line naming the bound (e.g. "gate exceeded its
  3600s timeout"). (c) No timeout configured anywhere ⇒ gate behaviour unchanged.
  Demonstrable by C4-verify: unit tests drive `run_with_heartbeat` with a
  sleep-and-spawn command and a 1–2s bound, and drive a stub gate row through
  `run_gates` asserting the `unverifiable` outcome + evidence line.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: the missing bound: `run_with_heartbeat` timeout + group termination on
  expiry, the `timeout_secs` / `default_timeout_secs` schema keys, and the
  `unverifiable` recording with the bound named in the evidence line. The escalating
  heartbeat wording (proposal item 4) MAY ship if trivial, else is explicitly dropped.
  / out of scope: sweeping stragglers of a *normally exiting* child (#372); persisting
  full gate output (#370); the target project's deadlocked test suite (filed there).

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
- T3 runtime: render/update-compat + offline driver suites: fail — /tmp/tmp3ia87kpd/results/issue_500/split-proposal.md
- T4 PR body has a user-impact opener + tracker id in both artifacts: pass — pdca-pdca contribcheck
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Review: issue 368 adds configured wall-clock bounds for gate commands, killing timed-out process groups and recording timed-out gates as unverifiable.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The owed behavior is explicit: bound configured gates, kill the child process group, and route expiry to `unverifiable`, so acceptance can be judged against a concrete oracle (`brief.md:15`). |
| C2 Reproduction (red pre-fix) | PASS | The pre-fix failure is reproduced by retaining the new tests while reverse-applying the production changes: `run_with_heartbeat(..., timeout=1)` errors and timeout gate rows stay pass, grounding the missing-bound symptom (`template/tests/test_progress.py:211`). |
| C3 Change | PASS | The patch changes the bounded execution path and gate schema surface only; the decision is whether these are the right control points for a hung gate, and they are the callsite and parser named by the brief (`template/src/pdca_harness/gates.py:459`). |
| C4 Verification (red→green) | PASS | Red→green is independently reproduced: reverse-production copy failed `tests.test_progress` with 3 errors/2 failures, while patched `$PDCA_TARGET` passed `PYTHONPATH=src python3 -m unittest tests.test_progress` with 26 tests (`template/tests/test_progress.py:281`). |
| C5 Causal adequacy | PASS | The fix removes the unbounded wait by adding a deadline and process-group termination, not a capability probe or symptom guard; timeout rows become `unverifiable` rather than pass/fail (`template/src/pdca_harness/progress.py:157`). |
| T1 Structure | N/A | No T1 gate is configured, and this patch does not introduce a new structural artifact boundary that needs a separate structure decision (`check-gates.json:51`). |
| T2 Shape | NEEDS-HUMAN | The T2 wrapper named in the frozen gates (`./engine/scripts/run-docs-check.sh`) is absent in the target checkout, so the human must decide whether the recorded docs-link pass is sufficient or stale (`check-gates.json:60`). |
| T3 Runtime | NEEDS-HUMAN | The exact T3 wrapper (`./engine/scripts/run-suite.sh`) is absent and the frozen row reports an advisory fail, while direct `PYTHONPATH=src python3 -m unittest discover -s tests` passed; decide whether the stale/missing wrapper failure matters for this patch (`check-gates.json:69`). |
| T4 Contribution | NEEDS-HUMAN | The contribution artifacts needed to re-run `pdca-pdca contribcheck` are not among the provided review inputs, so the recorded pass cannot be independently confirmed (`check-gates.json:78`). |
| T5 Judgment | NEEDS-HUMAN | Human sign-off must decide whether adding timeout knobs to the template gate policy is an acceptable contribution shape for instances, since no deterministic T5 gate is configured (`template/pdca.toml.jinja:866`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | The human must decide whether the shipped timeout semantics satisfy the real 19h hung-gate operational problem without over-scoping into #370/#372 behavior (`brief.md:47`). |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T2 Shape — The T2 wrapper named in the frozen gates (`./engine/scripts/run-docs-check.sh`) is absent in the target checkout, so the human must decide whether the recorded docs-link pass is sufficient or stale (`check-gates.json:60`).
- [x] T3 Runtime — The exact T3 wrapper (`./engine/scripts/run-suite.sh`) is absent and the frozen row reports an advisory fail, while direct `PYTHONPATH=src python3 -m unittest discover -s tests` passed; decide whether the stale/missing wrapper failure matters for this patch (`check-gates.json:69`).
- [x] T4 Contribution — The contribution artifacts needed to re-run `pdca-pdca contribcheck` are not among the provided review inputs, so the recorded pass cannot be independently confirmed (`check-gates.json:78`).
- [x] T5 Judgment — Human sign-off must decide whether adding timeout knobs to the template gate policy is an acceptable contribution shape for instances, since no deterministic T5 gate is configured (`template/pdca.toml.jinja:866`).
- [x] Validation — fitness-to-purpose — The human must decide whether the shipped timeout semantics satisfy the real 19h hung-gate operational problem without over-scoping into #370/#372 behavior (`brief.md:47`).

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
