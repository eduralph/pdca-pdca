# Result — issue 411 / merge-mode-wrong-base-fail-closed

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: In plain terms: with auto-merge turned on, a fix can be merged into another
  fix's branch instead of the real target branch — and nothing says so. The wave reports
  success, the next wave builds on a target branch that never received the work, and the
  change is quietly missing from where it was supposed to land.

  How it happens. When `[driver].wave_mode = "merge"`, the driver merges each accepted
  bundle's recorded PR wherever that PR happens to point
  (`template/src/pdca_harness/merge.py:59, 82-89`). It checks that the bundle is COMPLETE,
  has a patch, and has a recorded PR URL (`:46-57`) — it never looks at what branch the PR
  targets. That branch was decided earlier, at publish time
  (`pr_base = stack_branch if (stack_branch and own_repo) else base`,
  `template/src/pdca_harness/publish.py:257`, used at `gh pr create --base`, `:290`). Two
  separate routes point it at another bundle's branch:

  - **Route 1 — the old `Stacks on:` wiring.** `publish._stack_base_branch`
    (`publish.py:615-630`) uses the wave integration branch if one was recorded, and
    otherwise falls back to **the parent bundle's own fix branch**, read from that parent's
    `publish.json` (`:626-630`). In merge mode no integration branch is ever recorded:
    `flow` only fills `integ` on the stack path via `integrate.fold` (`flow.py:806-820`),
    while the merge path (`:807-811`) fills nothing, so `_point_at_integration`
    (`flow.py:568-580`) clears the marker for every bundle. The fallback is therefore live,
    and a dependent's PR opens against — then gets merged into — its predecessor's branch.
  - **Route 2 — a brief whose `Repo + branch target` names a predecessor's branch.** That is
    the documented practice for stack-mode chains. `publish._resolve_target`
    (`publish.py:531-544`) hands that branch back as the bundle's base, so the PR opens
    against it and the merge lands there.

  **Worth knowing: the issue's own suggested fix only covers route 1.** It proposes
  comparing the PR's base against the bundle's resolved target base and stopping on a
  mismatch. On route 2 those two are the *same string* — the brief's target base genuinely
  *is* the predecessor's branch — so the comparison sees nothing wrong and stays silent.
  That is exactly the situation the issue describes in its own real-world section
  (wyrd-pdca's re-slicing plan told every chained brief to name the previous slice's
  branch). A guard built to the issue's literal wording would ship, pass review, and still
  let route 2 through. The criterion below covers both.
- Success criterion: On `eduralph/pdca-harness` @ `main`, new tests appended to
  `template/tests/test_publish_slice.py` fail before the change and pass after it, checking
  that when `[driver].wave_mode = "merge"`, `publish.publish` **refuses** — returns non-zero,
  opens no PR, pushes nothing, and prints a message naming both the branch the PR would have
  targeted and the target base it should have used — in both routes:
  1. the PR base would come from the old `Stacks on:` fallback (route 1);
  2. the PR base equals the bundle's own resolved target base, but that base is a branch
     another bundle in this batch produced (route 2).

  Plus the two things that must not change: under the default `wave_mode = "stack"` a
  stacked PR still chains onto its parent branch exactly as today, and an ordinary bundle
  targeting a real base still publishes normally in either mode.

  All of it is provable by the C4 gate from the patch alone, offline, with git and `gh`
  stubbed.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: Make merge mode refuse to publish a PR that would land anywhere other than a
  base existing independently of this run, covering **both** routes in Defect above (a base
  that differs from the bundle's own resolved target, *and* a resolved target that is itself
  another batch bundle's produced branch). The refusal returns non-zero, pushes nothing,
  opens no PR, and names both branches.

  **The refusal belongs at publish time, not at merge time** (the human's call, recorded
  here so Do does not re-litigate it): the publisher is an interactive leaf with a person
  present who can correct the brief's branch target on the spot, whereas the wave merge runs
  unattended in the middle of a flow — a stop there is a stop nobody is at. Refusing to
  create the wrong-based PR also removes the cause rather than guarding the symptom: if the
  PR is never opened against another bundle's branch, the merge has nothing wrong to merge.

  Under `wave_mode = "merge"` the old `Stacks on:` branch wiring has no business choosing a
  PR base at all — wave order carries dependencies there — so a bundle reaching publish in
  merge mode with a stacked-PR base is one of the cases that gets refused.

  The refusal must behave like the ones already there: non-zero return, a clear message on
  stderr, nothing pushed.

  Out of scope: `merge.py` is not changed (see the known limitation below); `wave_mode =
  "stack"` — the default — is untouched in every respect, including the stacked-PR base
  chaining that is correct there; removing the legacy `Stacks on:` field or its stack-mode
  fallback (deprecating it is a separate decision); teaching the planner or `brief.md`
  anything new (this is a driver-side guard, and the instance-side documentation was already
  fixed in wyrd-pdca); repairing or retargeting a wrongly-based PR automatically — the
  contract is refuse, not self-heal.

  **Known limitation, accepted at Plan.** Because the refusal sits at publish time, it
  covers PRs this run publishes — which is the normal case, since `flow` publishes a wave
  and then merges it inside the same loop (`flow.py:764-797` then `:807`), and it is the
  reported scenario. It does **not** cover a PR published by an *earlier* run (for example
  under stack mode, before the project switched to merge mode) that a later merge-mode run
  then merges: that PR already exists with the wrong base and never passes through publish
  again. Narrower than the main case, but real. Left out deliberately rather than
  overlooked; raise it at sign-off if you want a merge-time backstop as well, and it becomes
  a follow-up issue.

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

Review of issue 411: make merge-mode publishing fail closed before a PR can target a branch produced by another bundle in the same run.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The acceptance boundary is decidable: both wrong-base routes must refuse before side effects, while ordinary merge-mode publishing and both stack-mode shapes remain valid (`template/tests/test_publish_slice.py:1004`). |
| C2 Reproduction (red pre-fix) | PASS | With only `template/src/pdca_harness/publish.py` reverted in an isolated copy, 62 tests ran and the two wrong-base cases failed on the public return-code assertion `0 != 1`, while the other 60 passed (`template/tests/test_publish_slice.py:1018`). |
| C3 Change | PASS | The change is confined to the documented merge-mode policy, its pre-side-effect decision point, and focused regression coverage; stack mode bypasses the refusal (`template/src/pdca_harness/publish.py:268`). |
| C4 Verification (red→green) | PASS | Independent rerun established a genuine red of exactly 2 assertion failures without production changes, then green with all 62 publish tests passing; the refusal precedes fetch/checkout/apply/push/PR work (`template/src/pdca_harness/publish.py:268`). |
| C5 Causal adequacy | PASS | Preventing creation of the wrongly based PR removes the normal same-run cause for both routes, and the patch adds no capability probe or try/fallback symptom guard (`template/src/pdca_harness/publish.py:673`). |
| T1 Structure | PASS | Production policy stays in publish, sibling-record detection is a private helper, regression tests remain in the existing publish slice, and user-facing behavior is documented on the wave-mode surface (`docs/07-crosscutting.md:353`). |
| T2 Shape | NEEDS-HUMAN | Decide whether the recorded docs-render pass is sufficient or rerun `./engine/scripts/run-docs-check.sh` in the gate environment — that runner is absent from both supplied artifacts and target, so its link audit could not be independently reproduced (`docs/07-crosscutting.md:353`). |
| T3 Runtime | NEEDS-HUMAN | Determine why the recorded `./engine/scripts/run-suite.sh` driver suite exited 1 — the runner/log is absent and therefore the red cannot be classified, although independent `unittest discover -s tests` passed the full available target suite (`template/tests/test_publish_slice.py:975`). |
| T4 Contribution | NEEDS-HUMAN | Confirm the contribution opener and tracker id from the actual commit/PR artifacts — neither those artifacts nor the `pdca-pdca contribcheck` runner was supplied, so the recorded pass cannot be independently reproduced. |
| T5 Judgment | NEEDS-HUMAN | Decide whether to accept publish-time coverage only or require a merge-time backstop — a wrongly based PR created by an earlier run still bypasses this guard, so switching an existing batch from stack to merge can retain the hazard (`template/src/pdca_harness/publish.py:268`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether fail-closed refusal plus corrective guidance is operationally preferable to automatic retargeting for real merge-mode batches — this determines whether the interaction restores the intended workflow without unacceptable interruption (`docs/07-crosscutting.md:353`). |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T2 Shape — Decide whether the recorded docs-render pass is sufficient or rerun `./engine/scripts/run-docs-check.sh` in the gate environment — that runner is absent from both supplied artifacts and target, so its link audit could not be independently reproduced (`docs/07-crosscutting.md:353`).
- [x] T3 Runtime — Determine why the recorded `./engine/scripts/run-suite.sh` driver suite exited 1 — the runner/log is absent and therefore the red cannot be classified, although independent `unittest discover -s tests` passed the full available target suite (`template/tests/test_publish_slice.py:975`).
- [x] T4 Contribution — Confirm the contribution opener and tracker id from the actual commit/PR artifacts — neither those artifacts nor the `pdca-pdca contribcheck` runner was supplied, so the recorded pass cannot be independently reproduced.
- [x] T5 Judgment — Decide whether to accept publish-time coverage only or require a merge-time backstop — a wrongly based PR created by an earlier run still bypasses this guard, so switching an existing batch from stack to merge can retain the hazard (`template/src/pdca_harness/publish.py:268`).
- [x] Validation — fitness-to-purpose — Decide whether fail-closed refusal plus corrective guidance is operationally preferable to automatic retargeting for real merge-mode batches — this determines whether the interaction restores the intended workflow without unacceptable interruption (`docs/07-crosscutting.md:353`).

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
- By / date: Eduard Ralph / 2026-08-05

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
- #411 follow-up: merge mode should try to retarget a wrong-based PR to the real shared base and only refuse if that retarget fails.
