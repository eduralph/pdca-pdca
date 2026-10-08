# Adversarial review — issue 616 (stack-resume-carries-unmerged-prereqs)

The red→green evidence holds. Three inputs still break the fix. Each was reproduced with a
scratch test that reuses the shipped fixture (real git, bare `origin`, production
`flow._drive_and_act`); the tests are in `scratch/test_adversary{,2,3}.py` in this sandbox.

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/flow.py:871-872` (`wants` / `lined`) still
  starts the line for a dependent that `_runnable` will hold under its #186 gate
  (`flow.py:711-713`). `_prereqs_to_carry` drops `Depends on (merged)` ids (`flow.py:861`) and
  counts only its own five hold reasons. **Failing case:** D has `Depends on: P` (P from an
  earlier run, published, PR open) and `Depends on (merged): M` (M COMPLETE, PR open). U has
  the same target and no prerequisites. Result: "carrying … issue_P", a force-push of
  `pdca-integration/main-…`, then "issue_D skipped — prerequisite(s) not ready (M)". U is built
  on the line with P under it (`do_base: origin/pdca-integration/main-…`). Before the fix U
  built on plain `main`. This is the iteration-2 sign-off item that was not done ("start a line
  for a prerequisite only if some dependent that needs it is not held"). It also contradicts
  the patch's own claims at `docs/07-crosscutting.md:689` ("A held bundle starts no line") and
  `flow.py:809`. Fix: when deciding whether to start a line, treat an out-of-batch, unmerged
  `Depends on (merged)` prerequisite as a hold, and add the test.

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/flow.py:838` takes `pr_state == "MERGED"` to
  mean "its work is already the base" without checking where the PR merged. `integrate.py:474`
  already refuses to trust such a merge when the record's `base` is not the target base.
  **Failing case:** P0 is published with its PR open against `main`. P has `Stacks on: P0`;
  its `publish.json` has `base: fix/P0`, and its PR was merged into `fix/P0`, not `main`.
  D has `Depends on: P`. Result: no hold, no line, no stderr. D reaches COMPLETE built on
  `origin/main`, and P's head is not an ancestor of that commit. That breaks the brief's
  invariant ("built … on a base that carries all of its declared prerequisites"). Fix: count
  MERGED as "in the base" only when the record's `base` is the target base and the record is
  not an `Onto branch` one (`mode: stacked`). Otherwise carry the branch, or hold the
  dependent.

- NEEDS-HUMAN — the hold messages' advice can lead nowhere (`flow.py:903-908`).
  **Shown by test:** H comes from an earlier run of the same batch. It was accepted, its
  publish failed before the push, and it has a recorded stack base and tip on that batch's
  line. D has `Depends on: H`; D2 has `Depends on: P` (P can be carried). One wave. The run
  prints "Publish it (`pdca publish H`), then re-run". Its own pre-wave fold then starts the
  line fresh and force-pushes over it. After the run, `publish._line_tip_refusal` refuses H
  ("a commit origin's pdca-integration/main-… no longer holds … Re-drive it in a new run
  (#616)", `publish.py:725`). Before the fix, a re-issued run with one wave never folded, so H
  stayed publishable. `publish.py:696` names #616 as the issue that handles resuming across
  runs. **Reasoned from the code, not run:** the `_STALE` advice "Re-publish it" goes through
  publish's new-PR path, which never looks for an existing PR (`publish.py:330`, `:417`,
  `:421`). With P's PR still open, `gh pr create` should fail and the new record gets
  `pr_url: ""`, so the next run holds D again, this time as `_NO_PR`. A human should decide:
  should the pre-wave fold keep the earlier run's line instead of replacing it, or should the
  messages send the user to re-drive the bundle or add the PR URL by hand?

- Evidence (no finding): the C4 log shows 14 of 21 tests red with the production change
  reverted and 21 of 21 green with it. I re-ran the file on the patched target: `Ran 21 tests …
  OK`. The 7 tests that pass before the fix are no-change guards (merged, no-patch, other
  target, no out-of-batch prerequisite, `Depends on (merged)`, `Stacks on`). The tests use the
  production paths `_drive_and_act`, `integrate.fold`, `merged` (only `subprocess.run` faked)
  and `worktree._target`. One weak assertion: "D's PR branch carries P" (patch.diff:931)
  checks the test's own `_publish_bundle` stand-in, not `publish.publish`. It is still tied to
  the production-written `stack-base-tip`, so the impact is small.

- Tried and could not break: the E case (the fold after wave 0 continues the line without
  force); the line surviving a wave that accepts nothing of its target; `gh` missing or
  failing; a closed PR; per-pair holds across targets; dry run (no host call, no holds);
  fail-closed when the pre-wave fold or its re-gate fails. I also looked for false `_STALE`
  holds in the normal order. On the paths I found, nothing rewrites `SUMMARY.md` after
  publish writes `publish.json` (`signoff.record`; `accept_blockers` runs only at accept time).

Housekeeping: my first test run wrote git-ignored `__pycache__/` folders under
`target/template/src/pdca_harness/` and `target/template/tests/`. Later runs used a cache
folder in this sandbox. I did not remove anything.
