# Build notes — issue 839, iteration 3

Line numbers are against the worktree, whose base is `f5321ab` (`main` with 838 stacked on
it). They run later than the brief's citations, which were taken before 838.

I started from the previous attempt's patch and changed what the carry-forward asked for. The
design is the same: a pre-wave merge step, `hold_unmerged` split from `own_bases`, the marker
written from `merge_wave`, and release decided only by `merged_into`.

## The findings, and what I did about each

**1. A patched prerequisite whose readable brief names no target built its dependent without it.**
In merge mode a plain edge now waits on every prerequisite, not just a fold candidate
(`template/src/pdca_harness/flow.py:806-809`). `merged_into` judges it by its record, and answers
"merged" with no `gh` call for one that ships nothing, so leg (4) still holds. This also replaced
the previous attempt's `briefless` special case, since a missing brief is now the same case.

**2. A `patch.diff` that is not valid UTF-8 ended the whole run.**
New `merged.has_patch` (`template/src/pdca_harness/merged.py:209`) answers True, False or None, and
None means it could not be read. It never raises.

- `merged_into` treats only False as "ships nothing" (`merged.py:97`), so an unreadable patch is
  judged by its record. A human's merge still releases the dependent, and a test follows that advice.
- The walk takes only True (`flow.py:1545`).
- The hold line says what happened (`flow.py:1501`).

**3. A closed marked PR still got ready and merge requests.**
The walk now takes only a PR that reads OPEN (`flow.py:1550`). That one read replaces its
`merged_into` call, so it costs no extra `gh` call.

- A closed PR holds the dependent, and the hold line tells the human to reopen it and merge it by
  hand, or to land the work and drop the edge (`flow.py:1491-1494`).
- This also fixes a gap I listed last time: an unmarked closed PR was told only to merge by hand.
- The test stub now refuses ready, update and merge on a PR that is not open, as the reviewer asked.

**4. The docs sentence "never merges a PR that could not release a dependent" was false.**
I reworded it, as the finding suggested: the walk judges each edge on its own
(`docs/07-crosscutting.md:913`). `test_each_edge_of_a_dependent_is_judged_on_its_own` pins this, and
`test_a_prereq_merges_though_its_dependent_never_builds_for_another_reason` covers a stop of another
kind. The reviewer guessed a `Conflicts with` hold could do this. It cannot in merge mode: `_runnable`
gets `conflicts` only when a stack-only set is non-empty.

**Advisory cleanup, also done.** `takes` remembers its answer per run (`flow.py:1541-1551`), so N
dependents of one prerequisite cost one read in the walk. A test counts the reads.

**Scope fix.** The previous attempt changed stack mode so a briefless prerequisite held instead of
crashing, and I had flagged that as a decision for you. The new merge-mode branch made that change
unnecessary, so I took it out, with its two tests. Stack mode's `_runnable` path now behaves as on
`main`. See "Follow-ups".

## Decisions for the human at sign-off

1. **An accepted rebuild that was never re-published can have its OLD head merged unattended.**
   This is the one I would look at first. I confirmed it with a probe: P is marked, then rebuilt and
   accepted with a new `patch.diff` and no re-publish. A later run merges P's old PR, and D's base has
   the old head's file and not the rebuilt one. It needs a publish that failed before its push, or a
   `--no-publish` run. `integrate.py:260` documents that the record survives in that state.

   The brief says the marker "survives an iterate", so I built that. `main` already has the same
   exposure at the wave boundary, where `merge_wave` reads the same record, but there it is the same
   run and the publish failure has just been printed.

   A guard would store a hash of `patch.diff` beside the marker and have the walk compare it: about
   1 line in `merge.py`, 2 in `flow.py`, one more branch in `_merge_way_out`, and about 10 lines of
   test. It changes what the brief calls binding, so it is your call.
2. **A marked member of a `Merges with` group can merge alone.** The brief puts groups out of scope
   (#778), and the docs line it asked me to qualify says marked PRs can be picked up one at a time.
   Reaching this needs the field added after the mark, because merge mode refuses to build a group
   member it can see. I read this and did not probe it. A guard would be about 1 line in `takes`, a
   way-out branch and a test.
3. **Siblings after a refusal stay unmarked.** `merge_wave` stops at the first refusal, so later
   bundles of that wave are never attempted or marked, and their dependents are told to merge by hand.
   This is safe but less automatic, and it can happen in the incident's chain shape. The brief makes
   `_merge_one` the writer, so I left it.
4. **A hold line now costs one more `gh pr view`.** `_merge_way_out` reads the state of a PR on
   record for this base, to spot a closed one. I chose that over passing the state out of
   `merged_into`, which would be about 6 lines across 3 signatures, because it only costs anything
   when a dependent is already held. The deferred C1 question about `--no-publish` and a `(merged)`
   edge is not settled by this, but that path now makes 2 reads instead of 1. No plain edge, and no
   run with nothing held, pays for it.
5. **The walk is stricter than the brief's rule in two ways.** It does not go past a prerequisite it
   may not merge (D → P unmarked → Q marked leaves Q alone), and it does not go past a PR merged into
   another base. A partial chain can still merge: with D → P → [Q marked, R unmarked], Q merges while
   P stays blocked. That matches "judged on its own".
6. **Leg (2b) now has three tests.** A PR that already reads MERGED on another base is no longer
   handed to `_merge_one` at all, because there is nothing left to merge and going past it could merge
   something useless. To keep "not released on rc 0" tested through the real `_merge_one`, two tests
   get a return code of 0 and still hold D: one where the PR merges elsewhere after the walk read it,
   and one where the host only queues the merge.
7. **I edited files the brief does not name.**
   - `template/docs/fork-discipline.md.jinja:74` (new this round) described the merge-mode exception
     as "at the wave boundary" only, and it ships to every instance.
   - `docs/11-troubleshooting.md:92` told readers to name the prerequisite in the same command, which
     is wrong advice in merge mode.
   - `template/tests/test_merge_review_remarks.py:759`: the fault makes every `Path.write_text` die,
     and the test counted one partial write. The marker write is now a second one, so I narrowed the
     count to the remarks file. This loosens an existing test, so please look at it.
8. **Two choices carried over.** The marker goes on before the `expected_checks` and `_target_base`
   refusals, earlier than the brief strictly needs (`merge.py:816`). A failed marker write warns and
   goes on, leaving the PR unmarked, which the brief calls the safe default.
9. **Sizing.** `sizing.json` rates this brief oversized and proposes a split between holding and
   merging. I built the whole brief as written. Whether to split is your call.

## What I ruled out

- **Making `integrate._has_patch` tolerate a bad patch.** It is shared with the stack path. If it read
  a bad patch as "no patch", the fold would silently drop that bundle, and stack mode is out of scope.
- **A `CLOSED` check inside `_merge_one`.** About 3 lines, but it would change wave-boundary behaviour,
  which the brief wants byte for byte. There is still a window: a human can close a PR after the walk
  reads it and before its merge, and in a long chain that can be minutes. A real host should then
  refuse the ready-mark, and that refusal holds the dependent. That is my reading of `gh`, not tested.
- **A broad `_isolate` around each dependent's walk.** After these fixes I could find nothing in the
  walk that raises, so it would be code no test can reach. A probe of 25 broken bundle states found no
  production crash. The 8 `KeyError`s it raised came from my stub, for `pr_url` values that are not
  URLs. I kept 10 of those states as a table test.
- **Fixing `publish._batch_branch_producer`** (`publish.py:825`). It raises when a sibling's record is
  JSON but not an object. That is on `main` and outside this bundle, and `_isolate` contains it on the
  new path. A test pins that, and the hold line names the error. It is worth an issue.

## Known gaps

- **Stack mode still crashes on a briefless prerequisite** on two paths: `_runnable`'s
  `_fold_candidates` call and `_carry_finished`. Both are on `main` and both deserve an issue. I
  confirmed them last round, and did not re-run them this round.
- **Split children adopted mid-run:** the pre-wave step runs once, so such a child's prerequisite is
  not merged for it. The child is held.
- **No live GitHub run.** `gh` is a stub, though it really merges the branch on the local `origin`.
  What the real host does for a closed PR, a merge queue or a draft is not exercised. The brief lists
  no external dependencies, and this is what the Validation row is for.

## Refutation

**(a) Genuine red? Yes.** `run-verify.sh` reverted the production hunks and reported
`C4 PASS — red without the fix, green with it`:

| Module | Green leg | Red leg |
|---|---|---|
| `test_merge_resume_stranded_prereq` | 89 tests, OK | `failures=126, errors=10` (counts include subtests) |
| `test_flow_out_of_batch_prereq_hold` | 31 tests, OK | `failures=1` (the rewrite the brief names) |
| `test_merge_review_remarks` | 30 tests, OK | 30 tests, OK (only its count was narrowed) |

76 of the 89 new tests go red. I read all 10 errors:

- 1 is the real `UnicodeDecodeError`.
- 2 are `WorktreeError`, because the dependent built when it should have been held.
- 3 are `ValueError` from `list.index`, because the merge never happened.
- 3 are `TypeError`, and 1 is `AttributeError`. These 4 fail on a missing parameter or a new function
  (`_merge_one(held=…)`, `merged.has_patch`), not on behaviour. The walk never reaches those refusals
  through the flow, and the other one is a unit test of the new function.

The 13 that stay green do so by design. They are legs (4) and (5), the no-out-of-batch half of (1c),
the wave-boundary text tests (which prove that text is unchanged), and guards against merging or
holding too much. One of them, `test_the_walk_stops_at_a_prereq_already_merged`, only binds against
code that merges, so it passes on plain `main`.

**The check that matters for this iteration:** against the **previous attempt's production code**, the
final tests fail on every finding. That is 6 `ERROR`s (5 of them the `UnicodeDecodeError` crash, plus
the unit test of the new function) and 31 `FAIL` lines, including the closed-PR and no-target tests.

**A mutation pass, new this round.** I broke 46 production decisions one at a time, and the two
changed test modules went red for 45. The first runs found real problems:

- 2 survivors showed redundant code, which I removed: the `batch_names` check (the drive set holds no
  COMPLETE bundle) and a `has_patch` check in `_runnable`.
- 3 survivors showed gaps in my edge-kind tests: chains below a prerequisite used only plain edges,
  though the brief says every edge kind, and nothing pinned that a `Stacks on` edge of the dependent
  starts no merge. Tests are added.
- 1 survivor showed that a broken sibling in my table test was masking later cases. Fixed.
- The last survivor, `not all(target)` in the walk, only matters if a record and a brief both have an
  empty repo, and `_merge_one` refuses that anyway. I kept the clearer form.

**(b) Production path? Yes.** The tests go through `flow.flow_ids` (and `flow_batch` once) into the real
`_drive_and_act`, `_merge_prereqs`, `_runnable`, `_merge_one`, `merged_into` and `worktree.ensure`. The
re-publish test runs the real `publish.publish`, so the marker dropping out of the record is now
proven, not just read. Only `gh`, the build leaf's work and the publish leaf are stubbed. Leg (2)
checks that the file is in the real worktree D would be built in.

**(c) Fixture includes the fault? Yes.** P is a real unmerged branch on a real bare `origin`, and leg
(2) first asserts P is not on `main`. Broken bundles have real deleted files and real non-UTF-8 bytes.
Refusals come from real gates: a red rollup, a failing `gh` call, a remote that does not exist, a head
or base really pushed to while checks are read. The stub refuses operations on a closed PR.

## What I ran

All through the project's own scripts, on the final patch:

| Check | Result |
|---|---|
| `engine/scripts/run-verify.sh` (C4) | pass |
| `engine/scripts/run-suite.sh` (T3) | root suite 50 tests OK, driver suite 2786 OK (skipped=2) |
| `engine/scripts/run-docs-check.sh` (T2) | docs lint, site render and link audit clean |
| `engine/scripts/run-host-ci.sh` | clean, run from the worktree |
| `engine/scripts/run-prod-path.py` (C5) | pass |
| `git diff --check` | clean |
| New module, 3 more runs to look for flakiness | OK each time |

**Not run:** T4 (`contribcheck`), which needs the publish texts and runs at publish.

**Formatter and hooks:** the target has no pre-commit or ruff config, and `docs/INTEGRATION.md` names no
formatter, so there was nothing to run. pyflakes is not installed, so I checked the changed Python files
for unused imports with a short `ast` script, and checked added lines for length. The DCO
`Signed-off-by` is for the commit at publish.

## Process notes

- **I read beyond the brief.** The carry-forward points at `iteration-v2/`, so I read that attempt's
  patch, notes and reviews. I also read `deferred-findings.json` and `sizing.json`. The deferred items
  are marked as not build work, and I did not act on them. To place the fix I read more of the target
  than the brief cites, such as `publish.py`, `state.py` and the docs.
- **The builder guard blocked one edit command**, because the script text had `gh pr` next to
  backticks. It ran nothing. I did not reword it to get past the check, and made the same edits with
  the Edit tool.
- **I changed production files temporarily, in the worktree only,** for the mutation pass and for the
  run against the previous attempt. Each time I confirmed the tree matched afterwards (`cmp` on the full
  diff), and `patch.diff` matches the tree.
- **Left behind:**
  - gitignored working files in the worktree's `.cache/`: gate logs, diffs, probes, the mutation script;
  - `git add -N` on the new test, so `git diff` includes it;
  - the empty `prod.tmp.diff` in the bundle and `/tmp/issue839-prod-before-revert.diff`, both from
    earlier attempts.

  This round wrote only to the worktree and the bundle. Nothing was committed or pushed.
- The bundle also holds a copy of the test file. The copy that counts is in `patch.diff`.
