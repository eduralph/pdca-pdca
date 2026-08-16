# Result — issue 497 / single-id-rc-and-stdout-already-agree

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: As reported: `pdca flow <id>` could print `COMPLETE` and exit **1**, naming
  nothing that failed — `_report_single` printed only `results[iid]` while deriving the exit code
  from the **whole** results map, which since split adoption also carries children the single-id
  report never mentioned. An operator, or `pdca flow 500 && …` automation, read a success line
  and got a failure code with no way from stdout to learn which bundle caused it.
  **Verified against the target base: this defect is already fixed on `origin/main`, and the
  issue can be closed.** It was resolved by the #473 slice (PR #479, `flow: recover stranded
  split children; fund and report adopted waves`, merged 2026-08-10, commit `389bf1a`), which
  took the second of the two options the issue itself named — "keep the whole-map rc and report
  the adopted children on stdout now":
  * `cli._report_single` (`template/src/pdca_harness/cli.py:659-692`) now prints the named id
    first and then **every other entry in the map** in the identical `state<TAB>path` shape via
    `_report_entry` (`:644-657`), before returning `_results_rc(results, …)`. Its docstring names
    the exact failure this issue reports, including the recovery shape where the named id's
    `COMPLETE` was written by an earlier run.
  * Printing is unconditional, not failure-gated — deliberately, because a single-id run counts
    `AWAITING_SIGNOFF` as a successful end (`_results_rc`, `:630-641`), so a child waiting for
    the human would otherwise be invisible at rc 0.
  * The behaviour is pinned by three cases in `template/tests/test_flow_adopt_recovery.py`:
    `test_the_single_id_stdout_names_the_adopted_bundle_that_failed_the_run` (`:598`, asserts
    rc 1 **and** the full three-line stdout),
    `test_a_recovery_run_never_reports_an_earlier_runs_success_as_its_own` (`:620`),
    `test_stdout_names_an_adopted_child_left_waiting_for_the_human` (`:640`, the rc-0 shape, §6
    items included), with
    `test_a_single_id_run_that_adopts_nothing_still_prints_exactly_one_line` (`:667`) keeping the
    ordinary one-line contract. **Run at Plan on the current base:**
    `cd template && PYTHONPATH=src python3 -m unittest tests.test_flow_adopt_recovery` →
    `Ran 14 tests … OK`.
  The asymmetry the issue notes in passing — a **held** child leaves the run at rc 0 while an
  **adopted but unfinished** child makes it rc 1 — is now an explicit, uniformly applied rule
  rather than an accident: a child the run could not schedule is dropped from the results map
  and named on stderr with a resume hint, so the run neither claims it nor counts it
  (`test_flow_adopt_split.py:885-935`, "the run reports the work it did and nothing else"), while
  a bundle the run **drove** and left un-terminal does count. That is a coherent contract, it is
  documented where it is implemented, and both hold shapes were deliberately made to agree. If
  the human wants "this run created work it could not finish" to be a single verdict across both
  shapes, that is a **new** slice with a design decision in it — not this bug.
- Success criterion: At sign-off the human confirms, against `origin/main` of
  eduralph/pdca-harness, that (a) `_report_single` reports every entry of the results map in the
  documented `state<TAB>path` shape, (b) the exit code and stdout therefore answer for the same
  set of bundles, and (c) the three pinning cases above pass — and closes the tracker issue as
  fixed by PR #479 / `389bf1a`, recording the held-versus-adopted rc contract as intended
  behaviour rather than a residual defect. No patch is produced by this cycle.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: Confirm the fix on the target base and close the tracker issue with the evidence
  above. **Out of scope:** any code change (the code is correct); re-litigating the
  held-versus-adopted rc contract, which is a separate design slice if the human wants it;
  `_results_rc`'s single-id `AWAITING_SIGNOFF` allowance (#468, deliberate); the stdout contract
  for bundles the run never drove.

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-close
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — N/A — close disposition (no patch to verify)
- C3 Change: none — patch.diff
- C4 Verification (red→green): none — N/A — close disposition (no patch to verify)
- C5 Causal adequacy: none — reviewer + human sign-off

## 4. Conformance (Check — stack)
- T1 Structure: none — N/A — close disposition (no patch to verify)
- T2 Shape: none — N/A — close disposition (no patch to verify)
- T3 Runtime: none — N/A — close disposition (no patch to verify)
- T4 Contribution: none — N/A — close disposition (no patch to verify)
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

# Advisory review — SKIPPED (close disposition)

The reviewer leaf was skipped: this bundle's Plan concluded a close / no-fix disposition (likely-close), so there is no patch to review.

- NEEDS-HUMAN — Confirm the close disposition 'likely-close' (no patch was built). Override to a fix path (iterate-to-Do) if the close is wrong.


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] Confirm the close disposition 'likely-close' (no patch was built). Override to a fix path (iterate-to-Do) if the close is wrong.
- [x] leaf produced no usable verdict (needs a human) — plan-advisory leaf 'plan-reviewer' did not produce findings (produced no artifact); re-run it or adjudicate by hand.

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
- By / date: Eduard Ralph / 2026-08-15

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 0 finding(s); brief revised: no (plan-advisory-*.md)
- (empty is the common case)
- plan-reviewer produced no artifact in all 5 bundles of this sign-off batch (466/474/497/475/506) — systemic, not per-bundle: those briefs reached Do with no advisory pass, and each cost a human §6 adjudication. Act: find the leaf's failure mode, and decide whether a no-artifact plan advisory should hold Plan rather than pass through.
