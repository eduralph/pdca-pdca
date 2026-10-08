# Adversarial review — issue 646 (stack re-issue carries finished prerequisites)

Evidence re-run at `$PDCA_TARGET`: the new file passes 13/13 with the patch. With only the
production hunks backed out (scratch copy), 10/13 fail on assertions. The 3 that pass pre-fix
are the two (6) cases and the (7) no-trigger case, which assert "unchanged" behaviour, so that
is expected. The tests drive the real `flow._drive_and_act` → `integrate.fold` against real
git (bare origin). Only the build/sign-off leaves, `_publish_bundle` and `gh` are stubbed. The
C4 claim in `check-gates.json` holds. Three scenarios outside the closed test list break the fix:

- NEEDS-HUMAN — **A closed prerequisite's code still reaches a dependent through a stacked
  finished id.** `template/src/pdca_harness/flow.py:870-879` judges each finished id only on
  its own PR state. `foreign_commit` (`template/src/pdca_harness/integrate.py:196-207`) then
  counts every commit reachable from a state-clean head as "accounted for". Case (reproduced
  on the fixture): the earlier run folded `P` (wave 0), then published `Q` (`Depends on: P`)
  cut from that line and folded it. The run stopped before `D` (`Depends on: Q`). `P`'s PR
  was then closed. Re-issue `[P, Q, D]`: the carry prints `issue_P … its PR is CLOSED —
  holding no bundle`, carries `Q`, and builds `D` on a line whose history holds `P`'s head.
  The same happens after following the hint and deleting the old line: `Q`'s own head brings
  `P`'s commits in. This contradicts the brief's own rule at `brief.md:65-68` ("When origin
  DOES have an earlier line holding a not-clean id's commits … rule (5) wins … Building `P`'s
  dependent on a line that still holds a closed PR's code would ship that code"). The brief's
  (5) wording ("reachable … from the head of a STATE-clean finished named id") allows it, so
  this is a spec gap, not a builder slip. A human has to decide whether "not clean" cascades
  across finished ids: a finished id whose plain `Depends on` names a not-clean finished id
  is itself not clean, the way `_runnable`'s skip cascades.

- NEEDS-HUMAN — **The commit the carry approves is not the commit it folds.**
  `_finished_head` (`template/src/pdca_harness/flow.py:805-816`) checks the PR's
  `headRefOid`. The fold then merges the branch's *current* tip
  (`template/src/pdca_harness/integrate.py:468`, `head = _rev(wt, ref)`). Case (reproduced):
  `P`'s PR is MERGED at `H` (on `main`), then someone pushes `X` onto `fix/P`. GitHub allows
  this, and `X` is in no PR. The carry reports `P` clean, merges `X` onto the line, and `D`
  is built on unreviewed `X`. The same split exists for an OPEN PR whose branch moves between
  the `gh` read and the fold. No test covers the MERGED path: the `gh` stub
  (`template/tests/test_flow_resume_stack_prereqs.py:690-701`) always reports head == branch
  tip. Possible fixes: fold the approved head, or call branch tip ≠ PR head "not clean". The
  in-run fold merges branch tips on purpose (#593), so a human should pick which.

- NEEDS-HUMAN — **A continued line keeps the earlier run's base, so dependents build on an
  old `main`.** Continuing starts from origin's old tip (`template/src/pdca_harness/integrate.py:430`
  with `folded_this_run={tgt: tip}` from `flow.py:889-891`). Nothing brings in commits that
  landed on `main` since the earlier run. Case (reproduced): earlier line = `main@B0 + P`, then
  a commit `M` lands on `main`. On re-issue, `D` is built and C4-verified on a base without
  `M`. Pre-fix, `D` had `M` but not `P`. Now it has `P` but not `M`. Criterion (2) requires
  this trade-off, but a run that resumes days later makes it much larger than within one run.
  It is not among the known limits in `docs/07-crosscutting.md:695-702`. Sign-off should
  accept it explicitly, or the docs should name it.

Attempted and could not refute:
- the per-id `skipped=` path leaves a clean tree: every failure in `_merge` / `_take_in_base`
  aborts first (`integrate.py:583-594`);
- `integ.update` replacing `integ = {…}` (`flow.py:2256`) changes nothing for a run without a
  carry: `accepted` is cumulative, so a folded target never drops out;
- `_runnable`'s `dep in plain_deps` (`flow.py:717`) parses the same `_id_list` as
  `declared_deps`, so no id-format mismatch lets a held prerequisite through;
- request order is kept (`_finished_named` reads the raw `batch`, not the sorted `run_batch`);
- one `fold` per target under one `ExitStack`: no self-deadlock;
- the trust read in `carry_view` (`integrate.py:185-193`) happens outside the lock, but the
  fold re-checks origin's tip under the lock and refuses on a move. A concurrent fetch in the
  same checkout can at worst fail closed (ids held with a git error).
