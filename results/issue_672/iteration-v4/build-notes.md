# Build notes — issue 672 / carry-keeps-a-fold-time-skip-off-the-line (iteration 4)

Target: `eduralph/pdca-harness` `main` @ `d6057eb`, built in `$PDCA_WORKTREE`
(`pdca-harness.pdca-wt-l1`). Every `path:line` below is on the patched worktree unless it
says "base".

## The two round-3 findings, and what this round does about them

1. **C5 [impl]: recirculation leak.** P published p1, Q was cut from P, then P merged Q's
   branch back and added p2, which conflicts with the base. Round 3's rule (a) said "a
   bundle whose whole tip the skipped branch holds was built under it", so it dropped all
   of Q's history from P's work, p1 included. Q was carried with p1.
2. **Advisory [impl]: stale conflict skips after a restart.** Round 3 never tried a skipped
   bundle again once the fold started over, so a bundle that only conflicted with the one
   the restart removed stayed skipped, with wrong advice.

What changed, and why it is a different approach, not a patch on round 3:

- **The work rule no longer guesses from branch shapes.** A skipped bundle's work is now
  every commit its branch adds over the base, merge commits included, minus only what lies
  under the line commit its stack base records (`_work`,
  `template/src/pdca_harness/integrate.py:971-987`). Round 3's rules (a) "tips it holds
  whole" and (b) "what its `Depends on` names" are gone. Reason, with a concrete pair of
  histories: (H1) P = base→p1→q1→p2 where p1 is P's and Q = base→p1→q1 was cut from it,
  then P fast-forwarded to Q and added p2; (H2) Q = base→p1→q1 is all Q's, and P was cut
  from Q's tip and added p2. The commit graph is identical in both. In H1 p1 is P's work
  and Q must be held; in H2 it is Q's and Q could be carried. Any rule that reads only the
  graph gives one answer for both, so a rule precise for H2 leaks in H1 (that is exactly
  round 3's leak, in its merge form). The brief forbids the leak, so a shared commit now
  counts for both branches. The one exception is the recorded line commit: the run writes
  it (`flow.py:_point_at_integration`, base `flow.py:890-910`) right before it builds the
  bundle, and publish cuts the branch from it (base
  `template/src/pdca_harness/publish.py:261-263`, `:300`). That is a record of what the
  bundle was built on, not a guess, so it breaks the tie.
- **Every skip is tried again on each pass.** Skips are per pass now (`left`,
  `integrate.py:555`); only bundles merged before a later failure that hold its work are
  left out for good (`out`, `integrate.py:546`; added at `:609-618`). Termination: each
  extra pass adds at least one name to `out` (the names in `again` are merged ones, never
  already in `out`), so there are at most n+1 passes.
- **The mirror of finding 2 is handled too.** A bundle left out for good whose cause then
  merges on the next pass would otherwise be held with a false cause. There is no state in
  the requested order where both are carried (merging it first makes the cause fail), so it
  stays out, and its message says what happened: "with Q merged before it, P could not be
  carried onto <line>, and without Q it is, so Q is left out" (`integrate.py:638-649`),
  with the existing `open` hint. Pinned by
  `test_one_holding_a_later_ones_commit_is_held_when_they_conflict`.
- **Holds are judged per pass, after the bundle's own merge.** A bundle whose own merge
  fails is reported for that failure (its root cause). One that merges but holds work of a
  bundle left out is undone (reset to the tip before it, as a failed merge is, #631) and
  skipped with that cause (`integrate.py:569-606`). A bundle held this way is judged again
  on the next pass, so it gets carried when a restart lets its cause merge
  (`test_one_held_only_while_its_cause_was_skipped_is_carried_once_that_merges`).

## What changed, file by file

1. `template/src/pdca_harness/integrate.py`
   - `:99-103` new `SkippedWorkOnLine(IntegrationError)`, so the carry can give the
     existing `line` hint.
   - `:315` new keyword `skip_causes` on `fold`.
   - `:377-403` the `skipped` paragraph of `fold`'s docstring, rewritten (the brief asks for
     this when the behaviour changes).
   - `:540-650` the merge loop: tips read once (`:542`); `while True` pass loop (`:550`);
     per-pass skips and holds (`:555-557`); hold check before the merge, merge, undo on a
     hold (`:569-602`); the skipped bundle's work recorded (`:603-606`); restart when a
     merged bundle holds work of a later skip (`:609-622`); after the loop, the gone-branch
     check (`:624-630`), origin's-line check (`:631-637`), final reasons for bundles left
     out for good (`:638-649`), then `skipped` / `skip_causes` filled (`:650-652`).
     `held_out` (#674) is still filled in place, so the in-run fold's error path still
     announces holds; on a restart its entries from the abandoned pass are removed
     (`:619-621`). No caller passes both `skipped` and `held_out`.
   - `:971-1020` helpers `_work`, `_gone_work`, `_holding`, `_holds_why`.
   - With `skipped=None` (every in-run fold) the loop runs one pass and computes nothing
     new: `excl` stays empty, so `_holding`, `before` and `_work` are never called.
2. `template/src/pdca_harness/flow.py`
   - `_fold_lines`: `:919` parameter, `:934-936` docstring, `:946` pass-through.
   - `_CARRY_HINTS`: `:1003-1005` new `holds` hint (see "hint wording" below).
   - `_carry_finished`: docstring `:1059-1071` (the residual sentence at base `:1052-1054`
     replaced); body `:1118-1135`: pass `skip_causes`; a bundle held for holding a skipped
     id's work gets the `holds` hint and its cause in `causes`, the way
     `_cascade_not_clean` records a pre-fold cause (`:1009-1036`, unchanged);
     `SkippedWorkOnLine` gets the existing `line` hint.
3. `docs/07-crosscutting.md:728-758`: the residual sentence (base `:728-730`) replaced with
   the new behaviour and the rule; three known limits added (see below).
4. Test: `template/tests/test_flow_resume_stack_prereqs.py:474-909`, 18 cases and 5
   helpers, appended. Only the file's existing helpers and module imports are used.

Unchanged, as the brief requires: `_cascade_not_clean` and its hint text, the red re-gate
path, the in-run folds, the requested fold order, "of two independent conflicting ids the
one asked for first is carried", and the Q-before-P no-op (`test_a_branch_folded_before_
the_one_it_holds_whole_carries_both`).

## The rule, stated once

When the carry's fold skips S (its merge fails, or it is held), S's work is each commit
S's tip adds over `origin/<base>`, merge commits included, except those under the line
commit S's stack base records, when S's tip holds it. No commit of that work is reachable
from the pushed tip: every merged bundle's tip is checked against it (`:570`, `:609-610`),
and so is a continued line's start (`:631`). Fold merge commits are new, and base commits
are excluded by definition, so nothing else can bring that work in.

**Where this departs from the brief's literal "Precisely" sentence.** The literal reading
("no commit that id's branch adds over the base") also covers what lies under the
recorded line commit. Read that way, one failing wave-1 id holds every wave-0 id it was
built on, named as built on the failed one (backwards), and every sibling cut from the same
line. Concretely: with the recorded-line-commit exclusion removed, 4 cases go red, among
them `test_a_sibling_cut_from_the_same_line_is_still_carried` (X and Z held because P
failed) and `test_a_line_holding_a_prerequisites_old_head_is_still_carried_onto` (every
bundle of the target held). I followed the brief's first sentence ("never puts onto the line
work its own fold skipped") and its Scope ("a fold-time-skipped id's work"). This is a
narrower departure than round 3's: only the harness's own exact record is trusted, never a
branch shape or a brief's edge. The human should confirm it (it is the deferred T5 item).

## Hint wording

A held bundle gets a new `holds` hint, not `built_on`: "X's branch holds commits of P's
branch, and P is not carried (see its line): get P carried, or re-drive X on a base without
them, then re-issue" (`flow.py:1003-1005`). Reason: with a shared commit counted for both
branches, the held bundle may be the one the failed bundle was cut from (the documented
hand-cut limit), and `built_on`'s "X was built on P" would then be backwards. The new text is
true in both directions, and both remedies work (a re-driven X gets a new commit P does not
hold). `built_on` and `_cascade_not_clean` are untouched. 694 edits these hold lines, so
this is one more line it rebases over.

## Why inside `integrate.fold`, not in the carry before the push

The brief left this to Do. Doing it in the carry needs, at least: a no-push mode on `fold`
(about 4 lines in the push block, `integrate.py:653-671`), a way to return the tips and the
skips' work (about 6), the pass loop moved to `flow.py` (about 15), and the same helpers
(about 45 lines, as now, just in `flow.py`). That is no smaller than this patch's loop
change. What it adds: every extra call runs `_prepare_worktree` again, which fetches origin
and the base remote (`_fetch`, two `git fetch` per call), and a branch can move between the
judging call and the pushing call unless the tips are threaded through as well, which is
the window #633 closed. Inside `fold`, each tip is read once (`:542`), the commit judged is
the commit merged, and it all happens under one lock. Pushing and then repairing with a
force-push is out: the brief forbids it and the tests pin `len(pushes) == 1`.

## What I ruled out

- **Round 3's rules (a) and (b)**, or any repair of them from the graph alone: the H1/H2 pair
  above shows no graph-only rule can be both leak-free and precise there. Against round 3's
  production code, this test file fails 10 cases (7 on behaviour: the recirculation leak,
  the trusted `Depends on` (partial form), the stale skip, the stale hold, the gone branch,
  the hand-cut prerequisite now held, the stale-skip mirror; 3 only on the new hint text).
- **The literal rule** (no recorded-line-commit exclusion): see above, 4 cases red.
- **Keeping skips across passes** (round 3): mutation run, 3 cases red, including the
  advisory's exact shape (`test_a_skip_that_starting_over_makes_stale_is_merged_again`).
- **Checking holds before the merge** (round 3): a bundle that both conflicts and holds a
  left-out bundle's work was reported as "built on" the other one instead of its own
  conflict; mutation run, 4 cases red.
- **Trusting a `Depends on` edge to exclude commits**: a false or stale edge leaks.
  `test_a_depends_on_never_vouches_for_a_skipped_ids_work` uses the partial form (Q cut
  from P's first commit, P's brief names Q); round 3's code carries Q there.
- **Spreading a fold-time skip along declared `Depends on` edges to finished ids that do
  not hold the work**: not needed for the invariant, and the brief keeps the pre-fold
  cascade as it is.

## Known limits (each fails closed)

Documented in `docs/07-crosscutting.md:750-758`:

- **Hand-cut pairs.** A commit two branches share counts for each unless the run built one of
  them on its line. So when one finished prerequisite was cut from another's branch by hand
  and either one's merge fails, both are held, and on a continued line that holds such a
  commit, every finished prerequisite of the target is held. Pinned by
  `test_a_prerequisite_cut_from_by_hand_is_held_with_the_one_that_fails` and
  `test_a_shared_commit_the_run_cannot_give_to_either_holds_both_and_the_old_line`. This is
  a deliberate over-hold: it is the price of no leak in the H1 case.
- **Order.** A prerequisite built on a line holding an earlier commit of one asked for after
  it is held when their changes conflict, so that the later one is carried (the only
  leak-free state in the requested order).
- **Branch deleted mid-run.** A skipped bundle whose branch is gone has its work read from
  the head its PR merged with (`_gone_work`, `:990-998`; nothing when the base holds it).
  When the host names no merged head (an open PR whose branch was deleted between the
  carry's check and its fold), the fold pushes nothing for that target if anything else
  would be pushed (`:624-630`). Round 3 left this as a possible leak.

Not documented in the user docs, recorded here:

- A bundle a run re-drove onto a line that already held its own earlier head has that head
  under its recorded line commit, so the old head does not count as its work. That needs a
  `signoff --iterate-do` on a folded bundle plus a carry continuing the old line. Stated in
  `_work`'s docstring (`:977-979`).
- On a restart, `_gone_branch` runs again for a gone branch, so its `integrate:` stderr line
  prints twice and `gh` is asked twice. Only when a restart happens and a branch is gone.
- `SkippedWorkOnLine` replaces each held id's reason with the line message (as the pre-fold
  untrusted-line path does); the message names the skipped id. Hold wording is 694's area.
- The deferred human item from round 3 stands unchanged: when origin's line already holds
  a skipped id's own earlier head (the common re-issue shape), the whole target is held with
  the `line` hint. That is what the invariant requires (the line handed to wave 0 must not
  hold that work, and it is never rewritten); whether to relax it is the human's call.

## Red → green, through the project's runner

C4 gate, `engine/scripts/run-verify.sh` with `PDCA_BUNDLE` / `PDCA_WORKTREE` set, run from
the instance root under `timeout 1500`, on the final `patch.diff`:

- Green leg: `Ran 36 tests ... OK`.
- Red leg (production hunks reverted with `git apply -R --exclude=tests/* ...`, test kept):
  `Ran 36 tests ... FAILED (failures=14)`, all assertion failures, no load error. Each one
  shows the defect: D (or E) built on a line holding the skipped id's commit, a push where
  none is allowed, or the wrong id held.
- `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`.

The other 4 new cases pass on `main` on purpose; they guard what the fix must not break:
base history is no one's work (round 1's advisory), Q before P carries both (the brief's
"not changed" case), a sibling cut from the same line is carried, and a continued line
holding a prerequisite's old head is carried onto without force (round 2's advisory).

**Mutation checks.** A scratch script broke one mechanism at a time, ran the same gate
script (its green leg is the test module), and restored the files byte for byte (checked
by hash, then `git diff` compared equal to `patch.diff`). All ten went red:

| Mutation | Cases that failed |
|---|---|
| merge commits left out of the work (round 2's rule) | 1: the merge-commit case |
| recorded line commit ignored (the literal rule) | 4: sibling, old-head line, later wave, stale-hold |
| no restart | 5, incl. partial containment (round 1's finding) |
| skips kept across passes (round 3) | 3, incl. the stale-skip case (round 3's advisory) |
| holds judged before the merge (round 3) | 4 |
| no per-pass hold check (every hold permanent) | 1: held-only-while-its-cause-was-skipped |
| no check of origin's line | 2 |
| gone branch with unread work ignored | 1 |
| left-out bundle's cause never re-read | 2 |
| carry ignores `skip_causes` (no `holds` hint) | 4, incl. criteria (1) and (2) |

Other gates, through their wrapper scripts:

- T2 `run-docs-check.sh`: `lint_docs: OK`, 22 pages rendered, link audit OK.
- T3 `run-suite.sh` (the final tree): root suite `Ran 24 tests ... OK`; driver suite
  `Ran 2477 tests ... OK (skipped=2)`. The driver suite includes
  `tests/test_integrate_stack_bases.py` and `tests/test_flow_same_wave_conflict.py`, and the
  carry suite's 18 existing cases pass in the C4 green leg (36 = 18 existing + 18 new):
  criterion (3).

## Refutation (forced)

- **(a) Genuine red? Yes.** The C4 gate reverts the production hunks and keeps the test:
  14 cases fail on assertions, none on import. For criterion (1), the red failure is
  `'issue_D' unexpectedly found in {'issue_D': ...}` with stderr `flow: carried issue_Q,
  issue_X ...`: D was built on a line holding P's commit. Restoring the hunks makes all 36
  pass.
- **(b) Production path? Yes.** Every case drives `flow._drive_and_act` →
  `_carry_finished` → `_fold_lines` → the real `integrate.fold`, against a real bare origin
  and a real primary checkout. Only `gh`, the build leaf and publish are stubbed, as in the
  file's existing cases. The push count is the fixture's spy around the real
  `integrate._git`. The later-wave case runs a real earlier run too (waves 0-2, including
  `_point_at_integration` writing the recorded line commit). The gone-branch case wraps
  `flow._fold_lines` only to delete the branch on origin first, then calls the real one.
- **(c) Fixture includes the fault? Yes.** The failing merges really fail (the base or
  another branch changes the same file), and `-X ours` really resolves it on `fix/Q`. Each
  case checks its shape before the run where the shape is the point: `fix/P` and `main`
  are ancestors of `fix/Q` for the criteria; Q's tip is inside P's for the recirculation
  case; P's branch has no non-merge commit of its own for the merge-commit case; R's branch
  holds P's commit for the later-wave case. Criterion (2) rewrites Q's brief with no edge,
  and the `Depends on` case gives P a false edge, so no declared edge can be what decides.

## Commit-readiness

The target has no formatter, linter or pre-commit hook (no `.pre-commit-config.yaml`, no
ruff/black/flake8 config, no active hooks in the git hooks directory, none in
`.claude/settings.json`, and its CI runs only the docs checks and the render suite).
`git diff --check` is clean, no added line is over 100 columns, and `patch.diff` is
`git diff` of the worktree against `d6057eb`.

## Interactions

- **673** (edits `fold`'s per-bundle merge loop) will conflict textually: this patch puts
  that loop inside `while True:` (one more indent level). The brief orders 672 first.
- **694** (hold wording in `_carry_finished`) touches `flow.py:1115-1135` and now also sees
  the new `holds` key in `_CARRY_HINTS`.
- **463** depends on this; the only interface change is the keyword-only `skip_causes`.

## Housekeeping

- No external dependency beyond git and Python 3.11+ was needed.
- Scratch files live in the worktree's git-ignored `.cache/pdca-672/`: `show_err.py` (prints
  a case's captured stderr), `mutate.py` (the mutation table) and `against_v3.py` (runs this
  test file on round 3's production code). Not part of the patch. The driver's gate rebuild
  cleans ignored files.
