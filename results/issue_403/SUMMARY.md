# Result — issue 403 / gate-evidence-in-reviewer-sandbox

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: The reviewer is asked to independently reproduce every recorded gate result, but
  its sandbox is seeded with `REVIEWER_INPUTS = ["patch.diff", "brief.md", "check-gates.json"]`
  only (`template/src/pdca_harness/leaves.py:64,1887` and the advisory twin at `:2201`). Since
  #415 each gate row also carries `row["log"] = "gate-logs/<rule_id>.log"`
  (`template/src/pdca_harness/gates.py:529-545`) — the full captured output plus a header
  naming `cmd`, `cwd` and `PDCA_WORKTREE` (`gates.py:557-593`) — and that directory is **not**
  copied into the sandbox. So the one artifact that would let the reviewer adjudicate a row it
  cannot re-run is referenced by a path that does not resolve where it works, and #370's stated
  promise ("the verdict's whole basis must be reconstructable from bundle files alone",
  `gates.py:535-537`) does not hold for the leaf that most needs it. The reviewer's contract
  text compounds it: it is told to mark an unrepeatable gate NEEDS-HUMAN
  (`template/agents/reviewer.md.jinja`, "Can't re-run a gate? Say so") and is never told that
  the frozen evidence exists or that the wrappers are instance-root/`$PDCA_WORKTREE`-scoped and
  are not runnable from `$PDCA_TARGET` at all. Result, from the pdca-pdca instance's frozen
  bundles: T2/T3 rows escalate as *"the exact `./engine/scripts/run-docs-check.sh` oracle named
  in `check-gates.json` is absent in this target checkout"* (issue_331, 341, 368, 375, 380, 386,
  387) while the same gates cleared on issue_356 — same instance, same wrappers, different
  reviewer behaviour.
- Success criterion: With the patch applied, the reviewer's sandbox (and the advisory
  leaves' sandbox, which uses the same seeding) contains the round's `gate-logs/` directory, so
  every path a frozen `check-gates.json` row references resolves inside the leaf's cwd — while
  `build-notes.md` remains absent (the independence contract, asserted by
  `template/tests/test_driver_slice.py:62`). Demonstrable by C4-verify alone: the named test is
  red with the production hunks reverted and green with them applied.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: make the round's frozen gate evidence available to the reviewer and advisory
  leaves, and align the reviewer's contract text so a row it cannot re-run is adjudicated from
  that evidence — with the missing-oracle escalation reserved for a row that has none. Both
  seeding call sites must stay in step (`leaves.py:1887-1890` and `:2201-2204`), and the prompt
  sentence that enumerates the sandbox contents ("You have ONLY patch.diff, brief.md and
  check-gates.json in this directory", `leaves.py:1472-1476`) must stop being false. Keep the
  vendored role body (`template/agents/reviewer.md.jinja`) and the driver-side prompt saying
  the same thing.
  / **out of scope:** the sandbox-interior doctor preflight and any per-gate
  `reviewer_reproducible` declaration (the issue's second proposal — a separate slice; do not
  start it here); making `engine/scripts/run-*.sh` runnable from `$PDCA_TARGET` (they are
  instance-root scripts by design and the instance is not the reviewer's checkout); #419's
  read-only-index defect; any change to what a gate records or to §6/C6 routing.

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

Reviewing issue 403: make frozen `gate-logs/` evidence resolve inside reviewer and advisory sandboxes without exposing `build-notes.md`.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The owed behavior is explicit: every frozen gate-row log must resolve in the leaf sandbox while `build-notes.md` stays absent, so the review target is clear (`brief.md:24`). |
| C2 Reproduction (red pre-fix) | PASS | Red is reproducible without the `leaves.py` production hunk: in a temp copy, reversing only that hunk made the focused tests fail on unresolved `gate-logs/T3-log.log` and stale prompt text (`template/tests/test_driver_slice.py:459`). |
| C3 Change | PASS | The implementation covers the decision point: both reviewer and advisory sandboxes now seed `state.GATE_LOGS_DIR`, with best-effort failure handling and no change to `REVIEWER_INPUTS`/`build-notes.md` inclusion (`template/src/pdca_harness/leaves.py:1601`, `template/src/pdca_harness/leaves.py:1939`, `template/src/pdca_harness/leaves.py:2256`). |
| C4 Verification (red→green) | PASS | Direct rerun showed red→green: the temp-copy red leg failed 3/5 focused tests after reversing only `leaves.py`, and `cd template && PYTHONPATH=src python3 -m unittest tests.test_driver_slice` passed 84 tests with the patch applied (`template/tests/test_driver_slice.py:444`). |
| C5 Causal adequacy | PASS | The causal question is whether the sandbox receives the bundle-relative evidence that `gates.py` records; the fix copies that directory rather than adding a probe that masks an eager/load-time side effect (`template/src/pdca_harness/gates.py:544`, `template/src/pdca_harness/leaves.py:1623`). |
| T1 Structure | PASS | The change stays within the briefed surfaces: reviewer prompt, advisory prompt, sandbox seeding, docs, and tests; no unrelated files are touched (`brief.md:56`). |
| T2 Shape | NEEDS-HUMAN | Decide whether to rely on the recorded T2 pass without independent replay: `./engine/scripts/run-docs-check.sh` is absent from `$PDCA_TARGET`, no `gate-logs/` were bundled here, and the brief says target-local wrappers are out of scope (`brief.md:64`). |
| T3 Runtime | NEEDS-HUMAN | Decide how to treat the recorded non-gating T3 failure: I could run the direct Python suite green, but not the exact `./engine/scripts/run-suite.sh` oracle, and no row log was available to inspect (`brief.md:80`). |
| T4 Contribution | NEEDS-HUMAN | Decide whether the contribution artifacts satisfy the opener/tracker-id rule: the recorded contribcheck pass has no bundled log or PR artifacts in this review sandbox to re-run or inspect. |
| T5 Judgment | NEEDS-HUMAN | Human sign-off owes the overall contribution judgment: the patch appears scoped and causal, but final acceptability of the contract/prompt wording is a human review call (`template/agents/reviewer.md.jinja:52`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Human must confirm the product-level fit: seeded gate logs are gate evidence rather than builder rationale, so independence is preserved in practice for this workflow (`template/agents/reviewer.md.jinja:17`). |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T2 Shape — Decide whether to rely on the recorded T2 pass without independent replay: `./engine/scripts/run-docs-check.sh` is absent from `$PDCA_TARGET`, no `gate-logs/` were bundled here, and the brief says target-local wrappers are out of scope (`brief.md:64`).
- [x] T3 Runtime — Decide how to treat the recorded non-gating T3 failure: I could run the direct Python suite green, but not the exact `./engine/scripts/run-suite.sh` oracle, and no row log was available to inspect (`brief.md:80`).
- [x] T4 Contribution — Decide whether the contribution artifacts satisfy the opener/tracker-id rule: the recorded contribcheck pass has no bundled log or PR artifacts in this review sandbox to re-run or inspect.
- [x] T5 Judgment — Human sign-off owes the overall contribution judgment: the patch appears scoped and causal, but final acceptability of the contract/prompt wording is a human review call (`template/agents/reviewer.md.jinja:52`).
- [x] Validation — fitness-to-purpose — Human must confirm the product-level fit: seeded gate logs are gate evidence rather than builder rationale, so independence is preserved in practice for this workflow (`template/agents/reviewer.md.jinja:17`).

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
