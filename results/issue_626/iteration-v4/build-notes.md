# Build notes — issue 626, attempt 4 (stack squash/rebase merge recognised and refused up front)

Built on `f5321ab` (the bundle's `stack-base-tip`, on `pdca-integration/main-re715db900335`).
The brief's line numbers are from an older main; the numbers below are this tree's, with the
patch applied. The brief's recommended option ("refuse, recognise and explain") is what is
built. Alternative A (support the merges) is not.

This attempt started from `iteration-v3/patch.diff`. The carry-forward named two findings, both
about the drop step: when a run without P still holds a bundle naming P. The 9 deferred findings
are not build work, and their behaviour is untouched.

## The carry-forward findings

**1. Q's and D's lines sent you in a circle.** With P on an `Onto branch` or legacy `Stacks on:`
record, squash-merged, Q built on it and D naming `Q, P`: Q's line said "re-issue without P" with no
drop step, and the re-issued `Q, D` held D with "name issue_P in the same `pdca flow <ids>` command
... or wait until their PR merges into main". Naming P brings its hold back, and that PR never counts
as merged. Fixed in two places:

- Q's hint now carries the drop step when the cause's record never counts
  (`built_on_squashed_drop`, `template/src/pdca_harness/flow.py:1388`). `_SQUASH_HINTS` is now a map
  from a hint to the one its dependents get (`flow.py:1402-1404`, used at `flow.py:1500`), so R built
  on Q gets the same step and names P. Test: `template/tests/test_stack_squash_merge.py:821`.
- D gets its own line (`flow.py:850-857`), decided by `_uncounted_squash` (`flow.py:911`, called at
  `flow.py:832`): the record does not count, and the base has the merge commit without the head. It
  names the merge commit and says to drop P from D's brief. It offers neither the re-add nor the wait.
  Tests: `:970` (the finding's own case followed to the end, for three record kinds, and D is built
  once the edge is gone) and `:1056-1069`.

`_squash_merged` now checks the head against the base itself (`integrate.py:1497-1502`). D's path has
no earlier read of the head, and with the check inside, all three sites use one definition.

**2. The record rule was written twice, and differently.** `flow.py:1307` and `integrate.py:1445`
compared only the record's `base`; `merged.merged_into` also compares `repo`. A record for a renamed
repository got no drop step, yet D stayed held. There is now one function, `merged.counts_into`
(`template/src/pdca_harness/merged.py:121`), used by `merged_into` (`merged.py:112`), the fold
(`integrate.py:1455`), the carry (`flow.py:1347`) and D's line (`flow.py:923`). Tests: `:787`,
`:1000`, `:1062`. The fold's own rule for taking the base in stays as it was (`integrate.py:1457`),
since only the drop step goes by `repo`. Test: `:444`.

## The same mistake elsewhere

- **`Depends on (merged)` had the same false "wait".** Same line now, with `--no-publish` too. Test: `:1069`.
- **The step's word order.** "then re-issue without P, and drop P from the brief..." read as drop
  after re-issuing, which is the wrong order. It now says "after dropping" (`integrate.py:1486`).
- **"main has that work" claimed too much for an `Onto branch` record.** The evidence is about the PR,
  and P's commit could have been removed from it. D's line says "the PR's work" (`flow.py:853-854`).
- **The docs said only "its line and the fold's stop".** They now include the line of each one held for
  it, and name the repository case (`docs/07-crosscutting.md:826-831`). The out-of-batch paragraph
  describes D's line (`:912-918`, `:921`).

## Rejected alternatives

- **Count such a P as merged instead of asking for a brief edit.** This removes the cause, and it is
  cheaper. Sketch: `if merged.merged_into(...) or _uncounted_squash(...):` at `flow.py:806`, D then
  also gets the existing line check, and `DROP_PREREQ`, two hint rows, two map rows, the `squashed`
  list and its print all go, about 25 production lines and about 100 test lines fewer. I rejected it
  on behaviour, not cost. The brief says refuse, and puts support out of scope. #647 says an `Onto
  branch` record is never trusted, because the PR's merge does not prove P's commit was still in it.
  This option would build D on that evidence with no person looking. The finding also asks for the
  drop. It is your call below.
- **Read `gh` before fetching in `_uncounted_squash`.** This saves one `git fetch` per `_runnable`
  call, for a dependent of an out-of-batch prerequisite whose record does not count and whose PR is not
  merged. It costs about 6 lines, to split `_squash_merged` into a read and a check. `_base_lacks_merge`
  and `_line_lacks_merge` already fetch first, so I kept that order.

## What the whole patch does

- **Publish** warns about a repo with no merge commits for a PR cut from a stack base and, in stack
  mode, for any bundle another bundle names as a prerequisite (`publish._others_build_on`,
  `template/src/pdca_harness/publish.py:835`; callers `publish.py:373` and `publish.py:535`).
- **Fold**: `integrate._gone_branch` (`integrate.py:1407`) names a squash or rebase merge, with the full
  merge commit and the step (`integrate.py:1447-1456`, step text at `:1480-1487`, helper at `:1490`).
  Otherwise today's messages.
- **Carry**: `flow._finished_head` (`flow.py:1323`, the check at `:1341-1350`) gives that shape its own
  reason and hint (`:1385-1388`). The cascade gives dependents the matching hint and names the merged id
  along a chain (`:1500-1502`). They stay held. `_hold_all` (`:1407`) keeps those reasons under an
  untrusted line or a failed read.
- **Readiness**: D's line, above.
- **Docs**: `docs/07-crosscutting.md:694-698`, `:735-744`, `:818-836`, `:879-888`, `:912-921`.
  Docstrings in `merged.py` and `integrate.py` follow. The fixture at
  `template/tests/test_integrate_stack_bases.py:115-120` makes the merge commit read as unknown, so its
  cases reach no real `gh`.

## For you to decide at sign-off

- **Drop the edge, or count the merge?** See the first rejected alternative. As built, a person edits
  D's brief. The other option needs no edit, but builds D on the PR's merge commit alone.
- **D's line goes beyond the brief's criteria.** The brief names the fold and the carry. The finding
  asked for this line. It costs one extra `gh` read and up to one fetch, only for an out-of-batch
  prerequisite whose record does not count.
- **The hold is not enforced until the update (deferred).** The brief's Design item 4 says the
  prerequisite holds dependents "until they are updated from the base". As built, dropping P from the
  batch is what releases Q, updated or not. Pinned (`test_the_run_does_not_check_the_update`, `:1187`)
  and documented, not fixed.
- **The usual recovery run names nothing (deferred).** Re-issuing the same ids after a fold usually finds
  P's head on the line, so P is clean and the run is silent, while Q's PR keeps showing P's change.
  Pinned (`:696`).
- **P's and Q's lines can ask to drop an edge.** Criterion (c) bans the `edge` hint's text on P's line.
  For a record that never counts, `integrate.DROP_PREREQ` asks for much the same thing in other words,
  because there it is true. Tell me if you read (c) as banning that too.
- **The sizer rated this brief "oversized"** (`sizing.json`), with proposed seams. I built it as one
  change, as the brief specifies. The patch is 107 KB across 7 files, most of it the test file.

## What this does not cover

- **After the edge is dropped, nothing checks that D's line has the PR's work.** A line already on origin
  for that batch, started before the merge, and with nothing carried holding P's commits, would build D
  without them. With a record that counts, `_line_lacks_merge` holds D there. I reasoned this out and did
  not run it. It needs a stale line and a D whose other prerequisites do not build on P.
- A later wave with no declared edge. The Goal says "a later wave or a dependent", but the criterion
  defines the check as a declared-dependency scan and (d) requires silence without one.
- `--dry-run` never warns on publish, as before. A dry-run keeps D's plain line and fetches nothing
  (test `:1159`).
- `results/completed/` is not scanned for dependents; the brief specifies `issue_*/brief.md` under the root.
- A squash-merged PR whose branch still exists: the fold merges the branch as it always did, since it only
  asks the host about a gone branch. The carry names it either way.
- A merged `Onto branch` record whose head IS on the base keeps D's plain line (test `:1112`). Nothing was
  squashed there, so this patch leaves it.
- The real GitHub shapes after a squash or rebase. The stub follows `merged.merge_and_head`'s documented
  contract, and the brief says #625 confirms the live shapes and is not a prerequisite. If GitHub answered
  differently, all three sites fall back to today's messages (c3) and do not misreport.

No external dependency was missing; nothing here needs a row in `pdca.toml`.

## Refuting my own test

- **(a) Genuine red? Yes.** `./engine/scripts/run-verify.sh` on the final patch reverted the production hunks
  and kept the tests: `Ran 77 tests`, `FAILED (failures=44)`, then `PDCA-EVIDENCE: C4 PASS — red without
  the fix, green with it`. That is 40 tests failing, one of them with 5 failing subtests. All are assertion
  failures: 0 `ERROR:` lines and no `_FailedTest`. The other 37 stay green there because they pin behaviour
  that should not change (c2, c3, d, d2, e, no extra read, a head on the line). I also ran the new tests
  against attempt 3's production code, to check they bind this round's findings: 18 of 77 fail. The finding
  cases fail on what they should, for example "'dropping issue_P ...' not found in 'flow: issue_Q ...'"
  and D's line still offering the re-add. Three others fail only on the reworded step, and four because they
  assert the new read happened.
- **(b) Production path? Yes.** The tests drive `publish.publish` (both paths), `integrate.fold`,
  `flow._drive_and_act` and, for D's line variants, `flow._runnable` directly. Only `gh` is stubbed, in front
  of `subprocess.run` (`_gh_stub`, `:84`); `merged.merge_and_head` is not mocked. The build and publish leaves
  are stubbed in the carry cases, as in the peer test `template/tests/test_flow_merged_prereq_on_line.py`.
  Three mocks stand in for failures a healthy fixture cannot produce: `integrate.foreign_commit` (`:667`),
  `integrate.carry_view` (`:1138`) and `integrate._carries` (`:1146`). The code they drive is the real
  `except` branch. `:1163` patches `carry_view` only to assert it is not called.
- **(c) Fixture includes the fault? Yes.** A real `git merge --squash` or rebase is pushed to a bare origin,
  and the helper asserts the head is not an ancestor of the target (`:142`). The branch is really deleted
  where the case needs it. The line cases have a real line on origin. Negative cases use a real squash into a
  real `release` branch and a real merge commit. Other record kinds are the `publish.json` shapes
  `_publish_stacked` writes, set by hand (`_record`, `:145`); the `Onto branch` publish tests run that path
  for real.

**Mutation check:** I broke the production code 55 small ways, each on a copy of `template/src` under the
worktree's git-ignored `.cache/`, and ran the test module against each. The first run left 4 alive. Each one
led to a new test or assertion: the mode alone (`:1065`), the fold's own rule on another repo (`:444`), an
untrusted line replacing other reasons (`:622`), and no read after a failed fetch (`:1142`). The re-run killed
all 55. The only edit after it was the wording of D's line ("the PR's work").

## Commit-readiness and gates

The target has no formatter or pre-commit config (no `.pre-commit-config.yaml`, no `core.hooksPath`, no active
hooks); its checks are CI workflows. I ran a small AST check for unused imports on the 6 changed Python files
(none), which does not cover unused local names. `git diff --check HEAD` is clean, and no added line in the
changed production files is over 100 columns.

All on the final patch, with the worktree matching `patch.diff` (`git diff HEAD | diff - patch.diff`):

- `./engine/scripts/run-verify.sh`: exit 0, C4 PASS.
- `./engine/scripts/run-docs-check.sh`: `lint_docs: OK`, link audit OK.
- `./engine/scripts/run-prod-path.py`: "1 added driver-suite test(s) import the production package".
- `./engine/scripts/run-suite.sh`: exit 0. Root suite `Ran 50 tests`, OK. Driver suite `Ran 2774 tests`,
  `OK (skipped=2)`.

This attempt adds a new `gh` read (D's line), so I re-measured what attempt 3 only reasoned about. With a
logging `gh` stand-in first on `PATH`, the whole suite logged 26 `gh` calls and none asked for `mergeCommit`,
so no existing test reaches the new reads.

## Slips to report

- I wrote one log to `/tmp/pdca626-verify.log`, outside the roots I was given. I moved to `.cache/` after that
  and left the file for you, since cleanup is not mine to do.
- Several runs went outside the project's runner, each with a timeout: the mutation runs, the run against attempt
  3's code, and a script that prints the real messages. One hand run of the test module had a bad `PYTHONPATH`
  and failed to import, so it measured nothing. The red-to-green evidence above comes only from `run-verify.sh`.
- `git add -N` put the new test file in the worktree's index, so `git diff HEAD` could include it.
- My working files are in the worktree's git-ignored `.cache/` (`pdca626*`). They are not in the patch.
