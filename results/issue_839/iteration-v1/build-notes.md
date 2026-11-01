# Build notes — issue 839

Line numbers are against the worktree, whose base is `f5321ab` (`main` with 838 stacked on
it). They run later than the brief's citations, which were taken before 838.

## What changed

- `template/src/pdca_harness/flow.py:1453` — new `_merge_prereqs`, the pre-wave step. It is
  called once at `flow.py:3015`, before the wave loop, not from `_runnable`.
- `flow.py:3006-3015` — `hold_unmerged` is now on in merge mode. `own_bases` is split off it
  and stays off in merge mode.
- `flow.py:3044-3045` — merge mode passes `requested=frozenset()`, so a finished named id is
  a hold candidate (leg 1b). There is no line to carry it.
- `flow.py:839` and `flow.py:1435` (`_merge_way_out`) — the merge-mode hold text.
- `template/src/pdca_harness/merge.py:806` — the marker, written only when `merge_wave`
  passes `mark=True` (`merge.py:167`).
- `merge.py:506` (`_next`) — the refusal text parameter. `held=None` keeps the wave-boundary
  text byte for byte. The test pins the ready, rollup, merge and `_refuse` texts.
- Docs and comments as the brief lists: `docs/07-crosscutting.md`, `template/pdca.toml.jinja`,
  the `merge.py` module docstring and comments, the `_runnable` docstring, and the
  `merged_into` docstring.
- `test_merge_mode_holds_nothing` is rewritten as
  `test_merge_mode_holds_a_dependent_of_an_unmerged_prereq`, as leg (6) asks.

## For the human to check at sign-off

1. **I edited a test the brief does not name.** In
   `template/tests/test_merge_review_remarks.py`, the fault in
   `test_a_write_that_fails_leaves_no_file_and_still_returns_the_pr_to_draft` makes every
   `Path.write_text` die, and the test counted one partial write. The marker write is now a
   second one. I narrowed the count to the remarks file. Its assertions on the remarks
   contents and on the bundle directory being unchanged are untouched. This loosens an
   existing test, so please look at it.
2. **The marker goes on earlier than the brief strictly needs.** The brief says before the
   first `gh pr ready`. I write it right after the already-merged check, also before the
   `expected_checks` and `_target_base` refusals. Otherwise a brief `gh pr view` failure in
   `_target_base` would leave the PR unmarked, and the only way out would be a manual merge.
   The marker grants nothing by itself, since the gates run on every attempt.
3. **A marker write that fails does not stop the merge.** It warns and goes on, leaving the
   PR unmarked, which the brief calls the safe default. The write is atomic
   (`leaves._replace_record`). I tried plain `write_text` first, and the #838 fault showed
   it can tear `publish.json`.
4. **My reading of "the same base":** a prerequisite whose own target differs from the
   dependent's is not merged, because that would not put it on the dependent's base. The
   dependent is held with "it does not target main". The brief does not spell this case out.
5. **A close/no-fix prerequisite ends the walk.** Its own prerequisites are not merged for
   the dependent, which matches `merged_into` answering True for it.
6. **The rollup refusal on the pre-wave path drops the `merge_requires` and
   `merge_wait_secs` hints**, because the brief makes the trailing instruction the
   parameter. The "why" still says which check is failing or pending.

## Known gaps, left as they are

- **Siblings after a refusal stay unmarked.** `merge_wave` stops at the first refusal, so
  later bundles of that wave are never attempted and never marked. Their dependents hold and
  are told to merge by hand. This is safe but less automatic, and it can happen in the chain
  shape from the incident. Marking the whole wave up front would change where the marker is
  written (the brief says `_merge_one`), so I left it.
- **Split children adopted mid-run:** the pre-wave step runs once, so such a child's
  prerequisite is not merged for it. The child is held instead.
- **Re-publish drops the marker:** checked by reading only, not by a test.
  `publish.py:436-450` and `publish.py:559-566` each build a fresh record. A real publish
  run in a test would need the whole publish path.
- **No live GitHub run.** `gh` is a stub, though it does really merge the branch on the local
  `origin`. The real host's behaviour after `gh pr merge` (for example how soon state reads
  MERGED) is not exercised.

## Refutation

- **(a) Genuine red? Yes.** I reverse-applied only the `template/src/pdca_harness` diff and
  ran the new module plus `test_flow_out_of_batch_prereq_hold`: `FAILED (failures=19,
  errors=7)` of 57. Restored: `OK`. Legs (4), (5), `test_merge_one_alone_does_not_mark` and
  the no-out-of-batch half of (1c) pass both ways, by design: they guard against the fix going
  too wide. With the fix, the full `template/tests` suite ran twice: 2723 tests, `OK
  (skipped=2)` each time.
- **(b) Production path? Yes.** The tests go through `flow.flow_ids` into the real
  `_drive_and_act`, `_merge_prereqs`, `_runnable`, `_merge_one`, `merged_into` and
  `worktree.ensure`. Only `gh`, the build leaf's work and the publish leaf are stubbed. Leg
  (2) checks the file is in the real worktree that D would be built in.
- **(c) Fixture includes the fault? Yes.** P is a real unmerged branch on a real bare
  `origin`. Leg (2) first asserts P is not on `main`. Refusals come from a red rollup or a
  failing `gh` call, handled by the real gates. Leg (2b) spies on `_merge_one` to confirm it
  returned 0 and D was still held.

## What I ran, and what I did not

- Tests: the offline-suite command from `docs/INTEGRATION.md` §3 (`cd template &&
  PYTHONPATH=src python3 -m unittest ...`), under `timeout`. I did not run
  `engine/scripts/run-verify.sh`, since it expects the driver's environment; Check runs it.
- Also passing: `python3 docs/publishing/tools/lint_docs.py`, `tests.test_workflows`,
  `git diff --check`.
- **Not run:** the root suites (`tests/`: template render and `copier update`). The patch
  changes a comment in `template/pdca.toml.jinja` and adds a test file, so they should be
  unaffected, but that is unproven until Check runs them.
- Formatter and hooks: I found no pre-commit or ruff config in the target and no formatter
  named in `docs/INTEGRATION.md` §8, so there was nothing to run. The DCO `Signed-off-by` is
  for the commit at publish.

## Process notes

- A flaky test of mine surfaced during the work: `_refusal` republished one branch per
  subtest, and the push only succeeded if both commits landed in the same second. Each call
  now gets its own bundle.
- The builder guard blocked my first edit command, because the script text had `gh pr` next
  to backticks. It ran nothing. I did not reword it to pass the check; I made the same edits
  with the Edit tool.
- Left behind: an empty `prod.tmp.diff` in this bundle (my red-check scratch file; cleanup is
  the harness's job), and `git add -N` on the new test in the worktree so `git diff` includes
  it. Nothing was committed or pushed.
- The bundle also holds a copy of the test file. The copy that counts is in `patch.diff`.
