# Adversarial review — issue_646 (stack-reissue-continues-batch-line), iteration 4

Advisory only. Every path:line is on `$PDCA_TARGET` (patch applied). The attack scripts ran
in this leaf's scratch dir against the patched tree. I also ran them against a copy of the
tree with the production hunks reverted (`git apply -R` of the `template/src/` hunks), which
gives the pre-fix comparison.

## What I tried and could not break

- **Red→green evidence holds.** Re-ran the green leg: `tests.test_flow_resume_stack_prereqs`
  plus `tests.test_integrate_stack_bases` gives 85 tests, OK. In the C4 log's red leg, 34 of
  the 39 new tests fail. The 5 that pass on both legs are `test_5_an_empty_patch…`,
  `test_5_a_missing_patch…` and the three `test_7_*`. All five check "unchanged" behaviour,
  so they are expected to pass both ways. No test of the new behaviour passes without the fix.
- **The tests use production code.** The real `flow._drive_and_act`, `integrate.fold`,
  `_runnable`, `publish.publish` (with `open_pr=False`) and real git against a bare origin.
  Only the build/sign-off step (`flow._drive_wave`) and `gh` (`merged.subprocess`) are
  stubbed. The re-gate test runs the real `gates.run_integration`.
- **`_vouch` / `_own` (integrate.py `_vouch`, `_own`).** I tried each of these cases and
  could not get a wrong vouch or a wrong refusal:
  - a wave>0 bundle whose branch was cut from the line;
  - "Update branch" (main merged into a carried PR branch);
  - a prerequisite merged with a merge commit and its branch deleted, where the base now
    holds its commits;
  - a squash-merged prerequisite whose head this clone has;
  - a fork setup. `origin` is always fetched with `--prune`
    (`integrate.py:719-722`), so stale refs can't make a deleted branch vouch.
- **`integ.update` replacing `integ = {...}`.** For a run with no carry the two behave the
  same: the in-run fold passes the cumulative accepted set, so a target never drops out of a
  later fold.

## Findings

- NEEDS-HUMAN [impl] — **The carry fires on a finished id that has nothing to carry, and
  then carries unrelated finished ids** (`template/src/pdca_harness/flow.py:852-861`). The
  trigger checks `finished`, which means COMPLETE only. It should check finished ids that are
  also patched and targeted, as the brief's Scope says ("names *such an id*" — "COMPLETE,
  patched, targeted"). `_fold_candidates` is only applied afterwards, at `:861`.
  Concrete case: batch `["P","Q","D"]`. P is a close/no-fix outcome (CLOSE_MARKER, no patch,
  COMPLETE). Q is an unrelated finished id with a patch, and the earlier run folded it. D has
  `- **Depends on:** P` only.
  - (a) Q's PR is OPEN. Output is `flow: carried issue_Q … so what depends on them builds on
    them`, and D's stack base is set to the line holding Q. Criterion (5) says that with P
    having nothing to carry, "nothing is folded … D builds on the base as today".
  - (b) Q's PR is CLOSED. Output is `flow: not continuing origin's … Holding issue_D`. D, whose
    only prerequisite has nothing to carry, is not built at all. On the pre-fix copy the same
    run builds D (COMPLETE).
  The test for criterion (5) (`template/tests/test_flow_resume_stack_prereqs.py:885-905`)
  never has a second finished id, so it cannot catch this. Fix: build the `any(dependents…)`
  trigger from `integrate._fold_candidates(finished)`, and add a test with an unrelated
  finished Q.

- NEEDS-HUMAN — **Two finished ids that conflict make every re-issue stop before wave 0,
  with advice that doesn't work** (`template/src/pdca_harness/flow.py:919-941`, advice text
  from `template/src/pdca_harness/integrate.py:497`). The carry folds every carryable
  finished id, including one the earlier run's own fold could not merge.
  Concrete case:
  1. P and Q both edit `same.txt`, are both finished, and both have OPEN PRs.
  2. The earlier run's first fold raised `issue_Q's branch … does not merge cleanly … declare
     the conflict / re-order, then re-run` and stopped.
  3. I followed that advice: added `- **Depends on:** P` to Q's brief.
  4. I then re-issued `["P","Q","D"]` twice (D depends on P only).
  Both re-issues print `flow: the finished prerequisite(s) issue_P, issue_Q did not integrate
  (… declare the conflict / re-order, then re-run); STOPPING — no wave run.` and drive
  nothing. Q is COMPLETE, so a re-issue never rebuilds it, and re-ordering cannot help. On the
  pre-fix copy the same re-issue went on and built D (without P — the original bug).
  This is the same pattern sign-off rejected in iteration 3 item 2: "a re-issue must not stop
  forever with advice that doesn't work". The ways out that do work are never printed: close
  Q's PR (Q is then held, and P alone carries), or reject/iterate Q so the run rebuilds it on
  the line.
  This needs a policy decision:
  - hold the finished id that does not merge, plus its plain dependents, and go on; or
  - keep stopping, but name the conflicting finished id and print advice that works.
