# Build notes — issue 652 (also covers #624), iteration 2

Target: `eduralph/pdca-harness` `main` @ `b5f5c29`, worktree `pdca-harness.pdca-wt-l1`.
Line numbers are on the patched tree unless marked "main".

## What changed

- `template/src/pdca_harness/flow.py:866-867`: a new `_CARRY_HINTS["built_on"]` entry. The
  text is the brief's Scope example, word for word: "{name} was built on {cause}, which is
  not carried (see its line): get {cause} carried, or re-drive {name} on a base without it,
  then re-issue".
- `flow.py:871-898`: a new `_cascade_not_clean(cfg, ids, why)`. It reads each finished id's
  plain `Depends on` (`brief.depends_on`, resolved with `cfg.bundle(dep).name`, the same
  way the carry builds `dependents` at `flow.py:931-935`) and keeps only edges to other
  finished ids of the same target. It then loops until nothing changes: an id whose edge
  names an id already in `why` goes into `why` with the `built_on` hint. It returns
  name → direct cause.
- `flow.py:946` and `flow.py:960-964`: `_carry_finished` runs the cascade right after the
  per-id state judgment (`_finished_head`) and **before** the foreign-commit check. That
  check now counts only the heads of ids that are still clean. The fold only ever gets
  `clean` (`flow.py:971`, unchanged), so a cascaded id's branch is never merged.
- `flow.py:968-970`: the untrusted-line reason now says "a **clean** finished
  prerequisite's PR" (one word added; the line is rewrapped to stay ≤ 100 chars).
- `flow.py:996-997`: the held-line `.format(...)` gets `cause=`. The other hints ignore the
  extra keyword.
- `flow.py:915-923`: the `_carry_finished` docstring. "so only its plain `Depends on`
  dependents wait" becomes the cascade rule, limited to ids judged not clean BEFORE the
  fold, plus a sentence saying a fold-time merge failure does not spread.
- `docs/07-crosscutting.md:690-699`: the second sentence of the carry paragraph, updated
  the same way and with the same limit. The rest of the paragraph is unchanged: line 699
  only gained a leading "If" that moved down from the old line 691.

The cascaded id's held line keeps the existing shape (`flow.py:991-1001`, one line per
finished id naming its drive-set dependents), so the existing `_held()` helper reads it.
Holding the dependents needs no new code: the cascaded id is in `held`, and `_runnable`
already holds plain `Depends on` dependents of a held id (`flow.py:751-754`, main).

## The iteration-1 carry-forward, item by item

1. **T5: narrow the docs/docstring promise.** Both now say the cascade applies to an id
   judged not clean *before the fold, from its PR state and head*. Both also say that a
   prerequisite whose merge fails only during the fold does not hold the finished ids
   built on it, and that one which merges in the same fold is still carried with the
   failed one's commits (docs `:696-698`, docstring `:921-923`). This is the reviewer's
   observed residual (`iteration-v1/check-review.md:19`) and the brief's out-of-scope
   item. Runtime scope is unchanged for that case, as the reviewer asked.
2. **Typo `clean =[`.** Gone. This patch no longer touches that line: `flow.py:971` is
   byte-identical to main `flow.py:927`.
3. **Vacuous `_not_on_the_line`.** The helper is removed. Instead:
   - Clauses 1–3 now assert `self.assertFalse(self.fx._has(self.line))`. That is a real
     check, not a vacuous one: pre-fix the line exists (the carry pushes Q, D or R/Q onto
     it). Post-fix nothing is folded and the run has a single wave, so no line is made.
   - New `test_a_clean_finished_id_beside_them_is_still_carried` (`:429`): the reviewer's
     mixed target. P is CLOSED, Q is built on P, and X is a clean, unrelated finished id
     with a planned dependent E, plus an unrelated U. X **is** carried ("flow: carried
     issue_X (finished…"), so the line exists. E and U are built on it, the tip they were
     built on holds X, and neither that tip nor origin's final line holds P's or Q's
     commit. D is held on Q's line, with the cause.

## One more gap found while re-reading, and fixed

In round 1 the cascade ran *after* `integrate.foreign_commit` (main `flow.py:921`). That
check decides whether an earlier run's line on origin can be continued: every commit on
it must be reachable from the base or from a state-clean id's PR head. A cascaded Q is
state-clean (its PR is OPEN), so its head still "accounted for" P's closed commit on an
old line. The common re-issue case: run 1 folded P and Q, then stopped; P's PR was closed
since; run 2 re-issues with a clean X too. Round 1 then continued the old line, which
holds P via Q, folded X onto it, and built X's dependents on it. P's closed work, unnamed,
under the dependents: the same defect, through the old line rather than Q's branch. It
breaks the brief's invariant ("every bundle that would build on a not-clean finished id
… is held and named"). `_merge_published` skips a branch already on the line
(`integrate.py:472-473`, main), so nothing in the fold removes it either.

The fix moves the cascade call above the check and filters its heads (`flow.py:960-964`).
That is 2 changed lines compared with round 1. The old line then counts as untrusted, as
it already does for a CLOSED P with no Q (the docs' existing known limit, "an old line
that still holds a prerequisite whose PR was closed since"). Nothing is carried onto it,
and the operator gets the existing "delete <line> on origin … then re-issue" advice. Test:
`test_a_held_ids_head_does_not_vouch_for_an_old_line` (`:450`). The earlier run's line is
made with the real `integrate.fold([p, q])`. D and E are held with the `line`/delete
advice, the carry pushes nothing (U's recorded line tip is the old tip), U builds on the
base, and W (depends on U) builds on the line that the run's first fold replaced, which
holds neither P nor Q.

The "clean" word in the untrusted-line reason belongs to this fix. Without it, Q's own
line would say Q's own commit is not accounted for by "a finished prerequisite's PR",
which reads as false because Q's PR is open and holds it.

## Ruled out

- **Pruning inside `integrate.fold`** (skip a later bundle whose `Depends on` names one
  skipped in the same fold). That is the fold-time residual the brief puts out of scope.
  `fold` gets bundles, not edges, so it would need the edge map passed in, a check in the
  per-bundle loop at `integrate.py:433-439` (main), and a choice about what to do with a
  later bundle that *already* merged. It would also change every in-run fold, not only
  the carry.
- **An ancestry check** (`git merge-base --is-ancestor <P head> <Q head>`) instead of
  brief edges. The brief defines clean over plain `Depends on` edges. A CLOSED PR's branch
  is often deleted on origin, so there may be no P head to test, while the edge in Q's
  brief is always there. It would also cost one git call per (not-clean, finished) pair.
- **Keeping round 1's order** (cascade after the foreign check). See above. A mutation
  run confirms the new test pins this: with the heads filter disabled (cascaded heads
  vouch again), only `test_a_held_ids_head_does_not_vouch_for_an_old_line` fails.
- **Listing the finished ids P holds on P's own line.** P's line still says "holding no
  bundle this run" when only finished ids depend on it, and so does a middle id in a
  chain (Q in P ← Q ← R ← D). Each cascaded line names its direct cause with "(see its
  line)", so the chain can be followed from the dependent's line back to the root. It
  would also put Q and D's names on more than one line, which the brief's "ONE stderr
  line names issue_Q and issue_D" check rules out for P's line naming D. The brief does
  not ask for it. Cosmetic, left for the human.
- **Round 1's reason text** ("it was built on issue_P (its `Depends on`), which is not
  carried"). The hint right after it says "was built on issue_P, which is not carried"
  again. The reason is now "its `Depends on` names issue_P, whose work its branch
  carries". The line says *why* Q is not carried, and the hint says what to do.

Sample held line (clause 1, captured from the test run):

```
flow: issue_Q (finished in an earlier run) is not carried onto pdca-integration/main-rd88f097e6d3a: its `Depends on` names issue_P, whose work its branch carries — holding issue_D this run; issue_Q was built on issue_P, which is not carried (see its line): get issue_P carried, or re-drive issue_Q on a base without it, then re-issue.
```

## Tests

`template/tests/test_flow_resume_stack_prereqs.py`, section (9), `:371-472`, appended to
`ResumeStackPrereqs`:

- `_finished_on` (`:373`): publishes `iid` cut from `origin/fix/<prereq>`, then writes
  `Depends on: <prereq>` into its brief (after `_publish`, which rewrites the brief, as the
  brief's Repro says), accepts it, and asserts the prereq's tip is an ancestor of its
  branch.
- `_not_carried` (`:387`): the one "flow: issue_X (finished in an earlier run) is not …"
  line for an id.
- `test_a_finished_id_built_on_a_closed_one_is_not_carried` (`:394`), clause 1: D held,
  with ONE line naming issue_Q, issue_D, issue_P and "built on". It is not the `open` hint
  ("get issue_Q's PR open" is absent) and it is the new hint ("get issue_P carried, or
  re-drive issue_Q on a base without it"). P's line says CLOSED, nothing is carried, no
  line exists, and U is built on the base and COMPLETE.
- `test_a_hold_cascades_through_a_dependent_finished_before_the_run` (`:409`), clause 2
  (#624): U CLOSED ← D ← E. E is held and named on one line with issue_D and issue_U, and
  no line exists.
- `test_not_clean_spreads_through_a_chain_of_finished_ids` (`:418`), clause 3: P ← Q ← R
  ← D, **asked for from the far end** (`["R", "Q", "P", "D"]`), so the cascade needs more
  than one pass. D is held on R's line (cause issue_Q), Q's line names issue_P, and no
  line exists. Mutation: a single-pass cascade fails this test, and only this one.
- `test_a_clean_finished_id_beside_them_is_still_carried` (`:429`): carry-forward item 3.
- `test_a_held_ids_head_does_not_vouch_for_an_old_line` (`:450`): the old-line gap above.
- Clause 4: all 13 existing tests in the file pass unchanged, including `:176` and `:226`.

## Runs (the project's own runners, each under `timeout`)

C4, `engine/scripts/run-verify.sh` with `PDCA_BUNDLE=…/results/issue_652`
`PDCA_WORKTREE=…/pdca-harness.pdca-wt-l1`, final tree:

```
== C4 green leg: … Ran 18 tests in 1.891s  OK
== C4 red leg: bundle test(s) with the production change reverted
FAIL: test_a_clean_finished_id_beside_them_is_still_carried
FAIL: test_a_finished_id_built_on_a_closed_one_is_not_carried
FAIL: test_a_held_ids_head_does_not_vouch_for_an_old_line
FAIL: test_a_hold_cascades_through_a_dependent_finished_before_the_run
FAIL: test_not_clean_spreads_through_a_chain_of_finished_ids
Ran 18 tests in 1.919s  FAILED (failures=5)
PDCA-EVIDENCE: C4 PASS — red without the fix, green with it
```

The red-leg failures are the brief's RED: e.g. "'issue_D' unexpectedly found in seen …
flow: carried issue_Q (finished in an earlier run) onto pdca-integration/main-r…", and
for #624 "flow: carried issue_D … onto …" with E built on it.

T3, `engine/scripts/run-suite.sh`: root suite `Ran 24 tests … OK`, driver suite
`Ran 2374 tests … OK (skipped=2)`, `PDCA-EVIDENCE: root suite OK, driver suite OK`.

T2, `engine/scripts/run-docs-check.sh`: `lint_docs: OK`, `render_site: link audit OK`.

C5, `engine/scripts/run-prod-path.py`: "patch adds no new test file — nothing to assert",
the same as round 1. The tests are in an existing file and drive production (see (b)).

After both mutation runs the code was restored, and `git diff | diff - patch.diff` is
empty.

## Refuting my own test

- **(a) Genuine red?** Yes. The C4 red leg reverts the production hunks and keeps the
  tests. All five new tests then fail on assertions, not on import (the file imports only
  modules, and the helpers are test-side). In each one D or E is built on a line the carry
  pushed holding the closed bundle's commit. Two mutation runs also go red on exactly one
  test each: cascaded heads vouching for an old line again → the old-line test; a
  single-pass cascade → the chain test.
- **(b) Production path?** Yes. Every test calls the real `flow._drive_and_act`, which runs
  the real `_carry_finished`, `_cascade_not_clean`, `_finished_head`,
  `integrate.carry_view`, `integrate.foreign_commit`, `integrate.fold` (via `_fold_lines`)
  and `_runnable` against real git (a bare origin plus a checkout). Only the build and
  sign-off leaf (`_drive_wave`), `_publish_bundle`, `publish.draft_texts` and `gh pr view`
  are stubbed, the same as the 13 existing tests in this file.
- **(c) Fixture includes the fault?** Yes. P (or U) has a CLOSED PR state from the `gh`
  stub. Q (or D, R) has a real branch cut from `origin/fix/<prereq>`, and `_finished_on`
  asserts the prereq's commit is an ancestor of it, so the commits that must not reach
  the line are really there to leak. In the old-line test the earlier line is built by the
  real `integrate.fold([p, q])`, so P's commit is really on origin's line. In the mixed
  test X is really folded (the test asserts the line exists and holds X).

## Commit-readiness

The target has no Python formatter or linter config (no `pyproject.toml` at the root),
`core.hooksPath` is unset, and the only git hooks are samples. Its CI runs the docs
linter and render check (both clean, above) and the root suite (OK, above). Commits need
a DCO `Signed-off-by` trailer, which publish adds. Every added line is ≤ 100 chars (code
and tests) or ≤ 80 (docs, matching the paragraph), and `git diff --check` is clean.

## For the human at sign-off

- **Known residual (out of scope, now documented):** a finished id that is state-clean but
  whose merge fails *during* the carry's fold. A later finished id built on it can still
  merge in the same fold and bring its commits onto the line. The reviewer reproduced
  this in round 1. Docs `:696-698` and the docstring `:921-923` now say so.
- The 6 deferred findings in `deferred-findings.json` were not touched (not build work).
- **Filesystem slip:** I wrote the T3 suite's output to
  `/tmp/issue652-builder-suite.log` (about 130 KB), outside the roots I was given. I left
  it in place rather than run a delete. It is safe to remove.
- No external dependency was missing. No NEEDS-HUMAN marker.
