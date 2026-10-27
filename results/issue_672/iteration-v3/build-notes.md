# Build notes — issue 672 / carry-keeps-a-fold-time-skip-off-the-line (iteration 3)

Target: `eduralph/pdca-harness` `main` @ `d6057eb`, built in `$PDCA_WORKTREE`
(`pdca-harness.pdca-wt-l1`). Every `path:line` below is on the patched worktree unless it
says "base".

## The two carry-forward findings, and what this attempt does about them

Round 2's approach was: a skipped bundle's work is its non-merge commits over the base,
less the commits of the bundles it was built on; check each bundle before it merges; fold
again before the push if an earlier-merged bundle holds that work. Two findings:

1. **C5 [impl]: work inside a merge commit leaked.** Round 2 left every merge commit out
   of a skipped bundle's work (`--no-merges`). A merge can hold a change of its own (a
   resolved conflict, an edit made while merging), so a bundle whose only change lives in
   a merge had no tracked work, and a branch holding that merge was carried.
2. **Advisory [impl]: a false hold of the whole target on a continued line.** Origin's
   line holds X's old head `x1`; X's branch moved on to `x2`; P was cut from that line and
   names no `Depends on: X`; P fails. Round 2 counted `x1` as P's work, so X was held, and
   since the line held `x1`, every finished id of the target was held. The docs understated
   this.

What changed in the rule (`_own_work`, `template/src/pdca_harness/integrate.py:930-958`;
`_commits`, `:922-927`):

- **Merge commits count as work** (`:926`, no `--no-merges`). That closes finding 1.
- **What the run recorded a bundle was built on is not its work.** When the bundle's
  stack base records a line commit (`publish.read_stack_base_tip`) and the bundle's branch
  still holds it, every commit under that line commit is left out of its work
  (`:945-948`). Publish cuts a stacked bundle's branch from exactly that commit
  (base `template/src/pdca_harness/publish.py:261-263`, `:300`). That closes finding 2 for
  any bundle the harness built on its line, which is the stack-mode case the finding
  describes. It is also what lets merge commits count without a new false hold: two
  siblings cut from the same old line share that line's fold merges, and those are under
  the recorded line commit.
- For a bundle cut from another branch by hand (no recorded line commit), the shared
  commits that no rule explains still count as the failing one's work (fail closed). The
  docs now state that limit accurately, including that the whole target is held when the
  old line holds such a commit (`docs/07-crosscutting.md:746-750`), and a test pins it.

I did not re-submit round 2's rule. The check-before-merge, fold-again and one-push
structure is kept, because neither review found a fault in it (round 2's reviewer:
"each retry removes a previously taken carrier, bounding the loop by the bundle set").

## What changed

1. `template/src/pdca_harness/integrate.py`
   - `:68` imports `brief` (a leaf module: only `re` and `pathlib`, so no import cycle).
   - `:99-103` new `SkippedWorkOnLine(IntegrationError)`.
   - `:315` new keyword `skip_causes` on `fold`.
   - `:381-398` the `skipped` paragraph of `fold`'s docstring, rewritten (the brief asked
     for this if behaviour changed).
   - `:535-603` the merge loop:
     - `:537-538` each branch tip is read once, before any merge, so every pass merges
       and judges the same commit (a carried branch still uses its `checked` tip, #633).
       Nothing fetches between bundles of one target, so this reads what the old per-bundle
       read did.
     - `:543` `while True:` around the existing per-bundle loop. One pass normally; another
       only when a bundle merged in this pass holds skipped work.
     - `:558-563` before merging, a bundle whose tip holds a skipped bundle's work is
       skipped. It raises a plain `IntegrationError` inside the existing `try`, so it takes
       the one existing skip path.
     - `:573`, `:579` skipped or held-out names are never merged again (skips only grow).
     - `:580-583` the cause goes into `skip_causes`; a newly skipped bundle's own work is
       computed.
     - `:589` the in-run folds (`skipped=None`) and a fold with no skip leave after one
       pass, with no extra git call.
     - `:591-596` continue mode: when origin's line (the start) already holds skipped work,
       raise `SkippedWorkOnLine` before anything is pushed.
     - `:597-603` the earlier-carrier check, then the reset of the line to its start.
   - `:922-971` helpers `_commits`, `_own_work`, `_skipped_work`.
2. `template/src/pdca_harness/flow.py`
   - `_fold_lines`: `:919` parameter, `:934-936` docstring, `:946` pass-through.
   - `_carry_finished`: `:1056-1068` docstring (the residual sentence at base `:1052-1054`
     replaced); `:1115-1132`: pass `skip_causes`; a bundle held for holding skipped work
     gets the existing `built_on` hint (`_CARRY_HINTS`, `:995-1003`) and its cause in
     `causes`, the same way `_cascade_not_clean` records a pre-fold cause (`:1006-1033`,
     unchanged). `SkippedWorkOnLine` gets the existing `line` hint, like the pre-fold
     untrusted-line path. Any other error keeps today's behaviour (every id held, `open`).
3. `docs/07-crosscutting.md:728-753`: the residual sentence (base `:728-730`) replaced with
   the new behaviour and the rule for whose work a commit is; the untrusted-line sentence
   now also covers a line that already holds skipped work; one new "Known limits" entry.
4. Test: `template/tests/test_flow_resume_stack_prereqs.py:474-783`, 14 cases and 6
   helpers, appended. They use only the file's existing helpers and module imports
   (`publish.write_stack_base` / `read_stack_base_tip` already exist on base).

Unchanged, as the brief requires: `_cascade_not_clean` and its hint text, the red re-gate
path, the in-run folds, the fold order, and "of two conflicting ids, the one asked for
first is carried".

## The rule for "whose work is a commit", stated once

A skipped bundle S's work is every commit S's tip adds over `origin/<base>`, merge commits
included, except the commits under:

- (r) the line commit S's stack base records, when S's tip holds it;
- (a) the tip of any other bundle of the fold that S's tip holds whole;
- (b) the tip of any other bundle S's plain `Depends on` names, unless that bundle's
  branch holds S's tip (then it was built on S, whatever S's brief says).

Any bundle whose tip holds a commit of that work is skipped too, by ancestry, whatever its
own brief declares. It is then a skipped bundle in turn, so the rule chains.

**Where this departs from the brief's literal "Precisely" sentence.** The brief says "no
commit that id's branch adds over the base". Read literally, that includes the commits
of whatever S was built on. Example: X is clean, P was cut from X, P conflicts; the
literal reading would hold X and everything that depends on X, and in stack mode one
failing wave-1 id would hold all of wave 0 (every wave-1 branch holds the whole line).
Today X is carried in that case. I followed the brief's first sentence ("never puts onto
the line work its own fold skipped, directly or through another finished bundle's
branch") and its Scope ("a fold-time-skipped id's work"). This is the same question as
the deferred T5 item in `deferred-findings.json`; the human should confirm it at
sign-off. Tests that pin this choice:
`test_the_prerequisite_a_skipped_id_was_cut_from_is_still_carried`,
`test_a_declared_prerequisite_that_moved_on_since_is_still_carried`,
`test_a_sibling_cut_from_the_same_line_is_still_carried`,
`test_a_line_holding_a_prerequisites_old_head_is_still_carried_onto`.

**What the rule trusts.** Rules (r), (a) and (b) each settle a case git alone cannot.
When two branches share a commit and neither tip holds the other, git cannot tell which
bundle made it. Each rule assumes "S was built on that one", so any leak left needs S to
have been built partly on its own earlier work, a cycle:

- (a): B was cut from S's early commit, then S merged B's branch back in;
- (b): S's brief names B, but B's branch holds an early commit of S's;
- (r): the line S was rebuilt on already held S's own older head (S folded, then
  re-driven onto that line).

None of these happens in a normal run: a bundle is folded only after it is accepted, and
an accepted bundle is terminal. They are written into `_own_work`'s docstring
(`integrate.py:940-942`).

## Why inside `integrate.fold`, not in the carry before the push

The brief left this to Do. The deciding cost is correctness, not size.

- **Carry-side version**, sketched: a `push=False` mode on `fold` (about 6 lines around the
  push block, `integrate.py:606-622`), a way to return the tips it read (about 4), the
  same three helpers moved to `flow.py` (about 50), a second fold of the survivors that
  pushes (about 8), and the tips judged by the first fold passed into the second (about 6).
  About 75 lines, against this patch's roughly 70 lines of loop change plus 50 of helpers.
  The sizes are about the same.
- **What it costs that this does not:** the second fold runs `_prepare_worktree` again,
  which fetches origin and the base remote again (`integrate.py:1096`, two fetches per
  target). Without the extra plumbing, a branch can move between the judgement and the
  merge, which is the window #633 closed by reading each tip once. Inside `fold`, each tip
  is read once, the commit judged is the commit merged, and it all happens under one lock.
- **Rejected outright:** push, then repair with a force-push. The brief forbids it, and
  the tests pin `len(pushes) == 1`.

## What I ruled out, and why

- **Round 2's rule (merges left out).** Leaks a skipped bundle's merge-only work: finding
  1. `test_work_a_skipped_id_did_in_a_merge_commit_stays_off_the_line` fails on round 2's
  code (checked: round 2's production hunks applied, this test file, 2 failures, this one
  and the continued-line one).
- **Counting only merges whose tree differs from an automatic re-merge** (`git merge-tree
  --write-tree`). Precise, but it needs git 2.38 or newer, a requirement the project does
  not state anywhere, and it does not fix finding 2 (the shared commit there is a plain
  commit, not a merge). The recorded line commit fixes both, with base git.
- **"A commit on origin's line that a carried bundle's tip also holds is not the skipped
  one's work"** (round 2's advisory suggested this). It leaks: if origin's line holds P's
  old head and a carried C was cut from it, C "accounts for" it and P's old work stays on
  the line. The recorded line commit covers the same realistic case (a bundle the harness
  cut from its line) without that hole.
- **Dropping rule (b)** (fail closed on declared edges too). It closes the (b) cycle
  above. But then a prerequisite whose branch moved on after another was cut from it by
  hand is held and named as "built on" the failing one, which is backwards for the user.
  Rule (b) matches how the carry already trusts `Depends on` (`_cascade_not_clean`).
- **Also spreading a fold-time skip along declared `Depends on` edges to finished ids that
  do not hold the work.** It is not needed for the invariant (they put none of the work on
  the line), and in a harness-built stack a declared dependent holds the work anyway, so
  containment catches it (`test_a_later_wave_built_on_a_line_holding_a_skipped_ids_work_is_held`).
  The brief keeps the pre-fold cascade as it is and asks for containment here.
- **Retrying merge-failure skips on a second pass.** It can change which of two
  conflicting ids is carried (out of scope) and can go back and forth. Skips only grow,
  so each extra pass leaves out at least one more bundle: at most n+1 passes.

## Known limits (each fails closed unless marked)

- **Over-hold, documented** (`docs/07-crosscutting.md:746-750`, pinned by
  `test_a_shared_commit_the_run_cannot_give_to_either_holds_both_and_the_old_line`): two
  finished ids share a commit no rule explains (one cut by hand from the other's branch,
  which moved on, with no `Depends on`). When one fails, the other is held too; on a
  continued line that holds that commit, every finished id of the target is held.
- **Over-hold:** a bundle skipped only because it conflicted with an earlier carrier that
  the second pass later drops stays skipped, because skips only grow.
- **Not covered (possible leak), rare:** a skipped id whose branch is gone (`head is None`).
  The fold has no tip, so it cannot compute that id's work. This needs an open PR whose
  branch was deleted; GitHub closes a PR when its head branch is deleted, so in practice it
  takes a race between the carry's `gh` check and its fetch.
- **Not covered (possible leak), contradictory topologies only:** the three cycles above.
- **Cosmetic:** on a second pass, `_gone_branch` / `_take_in_base` run again for a
  merged-and-deleted branch, so their `integrate:` line prints twice and `gh` is asked
  twice. Only when an earlier carrier forces the second pass.
- `SkippedWorkOnLine` overwrites every held id's reason with the line message, so the
  failing id's own conflict reason is not shown. The pre-fold untrusted-line path does the
  same. Hold wording is 694's area.
- `fold` given both `skipped` and `held_out` (no caller does): a held-out bundle from pass
  1 stays out in pass 2. That holds more, never less.

## Red → green (the project's runner)

C4 gate, `engine/scripts/run-verify.sh` with `PDCA_BUNDLE` / `PDCA_WORKTREE` set, run from
the instance root under `timeout`, on the final `patch.diff`:

- Green leg: `Ran 32 tests ... OK`.
- Red leg (production hunks reverted, tests kept): `Ran 32 tests ... FAILED (failures=8)`,
  all assertion failures, no load error: criterion 1, criterion 2, the contradicted
  `Depends on`, the earlier partial carrier, the merge-commit work, the later-wave branch
  built on a line holding P, the line already holding skipped work, and the documented
  over-hold.
- `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`.

The other 6 new cases pass on `main` on purpose. They guard what the fix must not break:
base history is not work (round 1's advisory case), a prerequisite stays carried (two
variants), a sibling on the same line stays carried, a continued line holding a
prerequisite's old head is still carried onto (round 2's advisory case), and Q folded
before P carries both (the brief's "not changed" fold-order case).

**Against round 2's code.** Round 2's production hunks with this final test file: `Ran 32
tests ... FAILED (failures=2)`, exactly the two cases for the two findings
(`test_work_a_skipped_id_did_in_a_merge_commit_stays_off_the_line`,
`test_a_line_holding_a_prerequisites_old_head_is_still_carried_onto`). This attempt: all
32 pass.

**Mutation checks.** Each mechanism broken on purpose, one at a time, in a scripted run
that restored `integrate.py` byte for byte after each one (checked by hash and against the
saved diff). All nine went red:

| Mutation | Test that failed |
|---|---|
| drop the recorded line commit rule (r) | `test_a_sibling_cut_from_the_same_line_is_still_carried`, `test_a_line_holding_a_prerequisites_old_head_is_still_carried_onto` |
| leave merge commits out (round 2's rule) | `test_work_a_skipped_id_did_in_a_merge_commit_stays_off_the_line` |
| drop the ancestry rule (a) | `test_the_prerequisite_a_skipped_id_was_cut_from_is_still_carried` |
| ignore `Depends on` (b) | `test_a_declared_prerequisite_that_moved_on_since_is_still_carried` |
| trust a contradicted `Depends on` | `test_a_depends_on_the_branches_contradict_does_not_carry_the_work` |
| measure work from the line's start, not the base (round 1's bug) | `test_base_history_two_branches_share_is_no_skipped_ids_work` |
| no second pass | `test_a_branch_merged_before_the_skip_with_part_of_its_work_is_left_out` |
| no check of origin's line | `test_a_line_already_holding_a_skipped_ids_work_is_not_carried_onto` |
| no check before a merge, and no second pass | `test_a_finished_id_built_on_one_the_fold_skipped_is_held` |

The last row is paired on purpose. With only the check before each merge removed, the
fold never ends: the second pass merges the same bundle again and repeats. That run hung
until its 600 s timeout. So the loop ending depends on that check, as the termination
argument above says: a repeat only happens when a merged tip holds skipped work, and the
next pass skips that same tip before merging it.

**End-to-end through the real flow** (scratch, not shipped): an earlier `_run` builds X,
then P and Z on the line (the flow records their line commit, the fixture's publish cuts
from it); the re-issued run then finds P conflicting. Checked with a continued line (X's
fixup conflicts with P), a fresh line (base conflicts with P), and a wave-2 R built on a
line holding P. All behaved as designed. The wave-2 case is shipped as
`test_a_later_wave_built_on_a_line_holding_a_skipped_ids_work_is_held`.

Other gates, through their wrapper scripts:

- T2 `run-docs-check.sh`: `lint_docs: OK`, 22 pages rendered, link audit OK.
- T3 `run-suite.sh`: root suite `Ran 24 tests ... OK`; driver suite
  `Ran 2473 tests ... OK (skipped=2)`.
- C5 `run-prod-path.py`: "patch adds no new test file" (cases are appended, as expected).
- The brief's three named modules: `Ran 102 tests ... OK`.

## Refutation (forced)

- **(a) Genuine red? Yes.** The C4 gate reverts the production hunks with
  `git apply -R --exclude=tests/* --exclude=template/tests/*` and keeps the test. 8 cases
  failed on assertions (for example D built and recorded in `self.seen`, or a push where
  none is allowed), with no import error. Restoring the hunks makes all 32 pass. I also
  reverted by hand with `git apply -R` of the production diff, with the same 8 failures.
- **(b) Production path? Yes.** Every case drives `flow._drive_and_act` →
  `_carry_finished` → `_fold_lines` → the real `integrate.fold`, against a real bare
  origin and a real primary checkout. Only `gh`, the build leaf and publish are stubbed,
  as in the file's existing cases. The push count is the fixture's spy around the real
  `integrate._git`. The later-wave case also runs the real earlier run (waves 0-2),
  including `_point_at_integration` recording the line commit.
- **(c) Fixture includes the fault? Yes.** The failing merges really fail (the base and P
  change the same file), and `-X ours` really resolves it on `fix/Q`. Each case checks its
  shape before the run: `fix/P` an ancestor of `fix/Q` and main an ancestor of `fix/Q` for
  the criteria; P's branch having no non-merge commit of its own for the merge-work case;
  R's branch holding P's commit for the later-wave case. Criterion 2 rewrites Q's brief
  with no edge, so the declared edge cannot be what catches it.

## Commit-readiness

The target has no formatter, linter or pre-commit hook: no `.pre-commit-config.yaml`, no
ruff/black/flake8 config, no hooks in `.claude/settings.json`, no active hooks in
`.git/hooks`. Its CI runs the docs checks and the copier render suite, the same as T2 and
T3 above, both green. `git diff --check` is clean. No added line is over 100 columns.
`patch.diff` applies cleanly to `d6057eb` (checked with `git apply --cached --check` on a
scratch index), and it reverse-applies on the worktree, so it matches what was tested.

## Interactions

- **673** (edits `fold`'s per-bundle merge loop) will conflict textually: this patch
  re-indents that loop one level, inside `while True:`. 673 needs a rebase onto this one,
  which is the order the brief gives (672 first).
- **694** (hold wording in `_carry_finished`) touches `flow.py:1113-1132`.
- **463** depends on this (per the brief); nothing here changes its interface beyond the
  new keyword-only `skip_causes`.

## Housekeeping

- No external dependency beyond git and Python 3.11+ was needed.
- My mistake: my first T3 run used a temp directory inside the worktree
  (`.cache/pdca-672-tmp`, git-ignored). The root suite copies the whole worktree, so the
  copy recursed into itself, and two driver tests saw the worktree's `.pdca-wt` name in
  their temp paths. That run failed for those reasons only; the re-run with the default
  temp directory is the green one above. It left about 1.2 GB in that ignored folder. I
  did not delete it (no `rm`, per the harness rules). The driver's gate rebuild runs
  `git clean -ffdxq`, which removes ignored files (`src/pdca_harness/worktree.py:260` in
  the instance), so Check starts without it.
- The green T3 run used the default temp directory, as the gate does; the project's own
  tests leave some temp folders there as they normally do.
- Also in that ignored `.cache/`: my mutation and end-to-end scripts, gate logs, a saved
  copy of the production diff, and a scratch git index. None are part of the patch.
