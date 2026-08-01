# Result — issue 340 / dependency-probe-at-plan-exit

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: the Plan-exit dependency guard actually *runs* the detect commands. Since
  #333 landed (`b0bc575`, `plan_policy.py`) an **unregistered** token holds the bundle —
  but a registered row is never executed: `registered_ids` only requires a non-empty
  `cmd`, and `plan_policy.py` contains no subprocess call (verified on main). A planner
  can discharge every existing check on a machine where the dependency is absent; Do
  then dispatches into the silently-worked-around case whose only detector is the
  builder's own self-report — the actor the planner prompt identifies as prone to
  concealing it.
- Success criterion: (a) a brief whose `External dependencies` names a backticked
  token matching a registered `[[doctor.checks]]` row whose detect `cmd` exits
  **non-zero** is held before Do dispatches, quoting that row's `hint`; (b) a passing
  detect ⇒ behaviour unchanged; (c) ONLY the rows the brief's tokens name are executed —
  a registered row the brief does not name is not run (asserted in a test, per the
  issue's definition of done); (d) `(no-check: …)`-annotated and plain-prose
  dependencies yield no token and are not probed; (e) the guard works at `lanes = 1`
  (the path with today zero preflight); (f) rows are read from disk
  (`Config.current_doctor_checks`, `config.py:391`) so a row added during the Plan beat
  counts in the same pass; (g) the probe runs *after* the #333 registration check — an
  unregistered token holds for that reason first; (h) `[driver].dependency_guard`
  keeps its existing modes with `off` byte-identical to today and `warn` printing
  without holding. Demonstrable by C4-verify via the offline driver suite (stub rows
  with `true`/`false` as detect cmds).
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: layer B of the issue only — the deterministic Plan-exit probe in the
  driver: execute the detect `cmd` of exactly the rows named by
  `brief.external_dependency_tokens` (`brief.py:250`) ∩ registered rows, hold on
  non-zero via the existing `PolicyHold` mechanism, honour the mode config, document
  that detect cmds must stay cheap and side-effect-free (they now run every beat the
  policy is consulted). / out of scope: layer A (the `/handoff` session-contract
  clause — #331 owns it and depends on this probe); #341 (reusing the probe at Do
  exit); container-provisioned gates (`[install].extra_bootstrap` keeps its own
  provisioning); weakening the default to `warn` (rejected in the issue: this is an
  exit code, not a heuristic — the existing default stands).

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
- T3 runtime: render/update-compat + offline driver suites: fail — /tmp/tmptzpitogb/results/issue_500/split-proposal.md
- T4 PR body has a user-impact opener + tracker id in both artifacts: pass — pdca-pdca contribcheck
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Reviewing issue 340: make the Plan-exit dependency guard execute exactly the brief-named registered detect commands before Do dispatch.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The acceptance boundary is decidable—named rows only, non-zero holds, and existing modes remain distinct—and the target documents that contract at `docs/03-plan.md:244`. |
| C2 Reproduction (red pre-fix) | PASS | In a disposable target clone with the production fix removed but the regression retained, the failing-command case returned no reason and failed at `template/tests/test_dependency_guard.py:324`. |
| C3 Change | PASS | The supplied diff exactly matches the target worktree and forms one dependency-guard change: detect execution is centralized at `template/src/pdca_harness/doctor.py:356` and consumed by the existing policy at `template/src/pdca_harness/plan_policy.py:209`. |
| C4 Verification (red→green) | PASS | Independent red→green reproduced (pre-fix test exit 1, patched exit 0), and all nine probe cases pass, including the pre-Do hold asserted at `template/tests/test_dependency_guard.py:329`. |
| C5 Causal adequacy | NEEDS-HUMAN | Decide whether a per-beat capability probe is the intended causal boundary or downstream dependency use should instead become lazy/structurally impossible—`subprocess.run` at `template/src/pdca_harness/doctor.py:395` triggers the mandated symptom-guard smell test and determines whether this fixes cause or policy symptom. |
| T1 Structure | PASS | The patch is confined to the existing doctor/policy/config/test/documentation seams, and fresh-on-disk row ownership remains with `Config.current_doctor_checks` at `template/src/pdca_harness/config.py:398`. |
| T2 Shape | PASS | Docs lint, site rendering/link audit, and `git diff --check` all pass; the operational cheap/read-only command constraint is present at `template/pdca.toml.jinja:713`. |
| T3 Runtime | PASS | The reported suite failure did not reproduce: 1,323 offline driver tests and all 7 Copier render/update tests pass, with passing/off/warn and selective execution covered at `template/tests/test_dependency_guard.py:334`. |
| T4 Contribution | NEEDS-HUMAN | Confirm the user-impact opener and issue-340 linkage in the actual contribution artifacts—the supplied inputs omit those artifacts, so the available `pdca-pdca contribcheck` cannot independently reproduce the asserted pass and convention compliance remains provisional. |
| T5 Judgment | NEEDS-HUMAN | Confirm no closed or rejected PR already implements these affected paths—merged history was checked path-by-path, but the GitHub closed-PR query could not reach `api.github.com`, so duplication risk is not mechanically settled. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether executing configured shell probes on every policy consultation is worth the earlier failure detection and side-effect/latency exposure described at `docs/03-plan.md:247`; this ship/iterate judgment is human-only by design. |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] C5 Causal adequacy — Decide whether a per-beat capability probe is the intended causal boundary or downstream dependency use should instead become lazy/structurally impossible—`subprocess.run` at `template/src/pdca_harness/doctor.py:395` triggers the mandated symptom-guard smell test and determines whether this fixes cause or policy symptom.
- [x] T4 Contribution — Confirm the user-impact opener and issue-340 linkage in the actual contribution artifacts—the supplied inputs omit those artifacts, so the available `pdca-pdca contribcheck` cannot independently reproduce the asserted pass and convention compliance remains provisional.
- [x] T5 Judgment — Confirm no closed or rejected PR already implements these affected paths—merged history was checked path-by-path, but the GitHub closed-PR query could not reach `api.github.com`, so duplication risk is not mechanically settled.
- [x] Validation — fitness-to-purpose — Decide whether executing configured shell probes on every policy consultation is worth the earlier failure detection and side-effect/latency exposure described at `docs/03-plan.md:247`; this ship/iterate judgment is human-only by design.

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
- By / date: Eduard Ralph / 2026-07-31

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
- T3 gate red across the whole wave traces to a pre-existing `issue_500/split-proposal.md` suite case — fix or quarantine it in the instance suite.
- Reviewer environment cannot reach api.github.com, so the closed/rejected-PR originality check lands in §6 every cycle — provision gh/API access for the reviewer leaf.
