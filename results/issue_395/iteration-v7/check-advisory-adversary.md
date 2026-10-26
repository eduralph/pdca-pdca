# Adversarial review — issue 395 / same-wave-conflict-refused-at-accept

Verdict: **partly refuted.** The red→green proof holds, and the conflict rule matches the
fold's. But the refusal's own recovery step leads to a bundle being accepted and published
with no human sign-off. I reproduced that on the real fixture.

## Refutation that landed

- NEEDS-HUMAN [impl] — **Following the refusal row's own step leaves a stale `accept` that
  auto-accepts the rebuilt attempt on the next run, with no sign-off session.** A trial
  refusal returns `"blocked"` and keeps the `accept` in `signoff-decision`
  (`template/src/pdca_harness/flow.py:205-207`). The row and the wave-end line tell the human
  to run ``pdca signoff <id> --iterate-plan`` (`flow.py:379`). That CLI path records the
  decision but never deletes `signoff-decision` (`template/src/pdca_harness/cli.py:1504-1543`;
  only `flow._apply_decision` deletes it, `flow.py:235`). The iterate archive doesn't move the
  file either: `signoff-decision` is not in `DOWNSTREAM_OF_BRIEF`
  (`template/src/pdca_harness/state.py:125-159`, read by `driver._archive_iteration`,
  `driver.py:457`). On the next run the re-planned, rebuilt bundle reaches AWAITING_SIGNOFF.
  Auto-iterate then declines because a decision is on disk (`flow.py:561-565`), and the
  pre-apply applies the old `accept` to an attempt nobody has reviewed (`flow.py:507-510`).
  **Concrete case, run on `StackFoldGit`** (probe kept in my sandbox,
  `exp/probe_stale_accept.py`): run (h)'s setup, so 11 is refused and parked. Then
  `cli._signoff(iterate_plan=True)` for 11 (rc 0, state UNPLANNED; `signoff-decision` still
  reads `accept`). Re-plan 11 with `Conflicts with: 10`, then re-run `drive=["11"]`. Result:
  stderr says `issue_11 — applied the 'accept' sign-off decision already recorded in the
  bundle; no new session`, the session count for 11 is 0, and 11 is COMPLETE with
  `fix/11` pushed. `--iterate-do` goes the same way. The CLI gap already exists for C6
  refusals on `main`. This diff is what sends the same-wave case into it: it creates the
  refused accept, and its printed step names the CLI command. After parking, the CLI command
  is the only route the run leaves open. Possible fixes: have `cli._signoff` delete
  `signoff-decision` once it records a decision (as `flow.py:235` does), or have the row's
  step point to the in-session iterate-plan. Add a test leg for this.

## Attempted to refute, could not

- **Red→green evidence.** I re-ran green on the target (13/13 OK). I also re-ran red myself:
  `flow/integrate/publish/state.py` taken from `HEAD` (the pre-fix base) into a sandbox copy,
  test kept. Result: 10 FAIL, 0 ERROR, the same set as `gate-logs/C4-verify.log`. The 3 that
  pass on both sides are the "unchanged behaviour" legs: (b) clean merge, plain C6, (g) last
  wave. Each red failure is on the real symptom (`COMPLETE != AWAITING_SIGNOFF`, no trial
  `apply` ever called), not on an import. Accepts go through the real
  `_drive_wave` → `_apply_decision` path; the only stub is `leaves.run_signoff_batch`, and
  there is no `signoff.record(...accept)`.
- **Does the trial mirror the fold?** Merge order is the fold's: name-sorted within the wave
  (`integrate.py:755`; fold `accepted` order at `flow.py:3303`). The start point matches:
  `tip or <base_remote>/<base>` (`integrate.py:806`) versus fold `fresh`/`continue`
  (`integrate.py:563-611`). Each would-be commit is built with publish's own steps on
  publish's own cut point, for both new-PR and `Onto branch` bundles (`publish.py:262`,
  `:296-309`, `:490-498`). The `_held_by` rule is reused, not copied (`integrate.py:926`).
  The `publish._checkout_base` refactor gives the same result as the old inline rule.
- **Waves after the first.** Every shipped leg runs the check in wave 0 only
  (`tests/test_flow_same_wave_accept_trial.py:172`). That leaves the `folded_tips` start and
  the #727 own-base cut points untested. I probed a wave-1 pair (both depending on wave-0
  bundle 12, plus a wave 2): 21 was refused naming 20 and `shared.txt`, 20 and 30 published,
  `holds` empty. A clean wave-1 pair was all published. It works; a wave-1 leg in the suite
  would pin it.
- **Fallback, broken tree, the one-more-session limit, a failed session, re-runs.** The
  ordering of the `except` clauses (`flow.py:303-319`), the counting after the session
  (`flow.py:2778-2783`), and the reset at wave start (`flow.py:2713-2714`) all hold for the
  cases I traced. The lock is never held while the fold's locks are, so there is no
  deadlock.
- **Not filed, because the human already ruled on it:** the hold-count rule can be fooled
  after an override. Example: 10 and 11 are accepted via an override, so the fold holds 11.
  A new 09 that conflicts only with 10 is then accepted, and the fold holds 10 instead.
  That is the "override loophole" accepted in the carry-forward (`brief.md:111`).

<!-- pdca:leaf-complete -->
