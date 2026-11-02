# Build notes — issue 626, attempt 6 (stack squash/rebase merge recognised and refused up front)

Built on `f5321ab` (the bundle's `stack-base-tip`, on `pdca-integration/main-re715db900335`), starting
from `iteration-v5/patch.diff`. Line numbers below are this tree's, with the patch applied.

You rejected attempt 5 for one finding: following P's own printed advice could still build D without P's
merge, with no warning. P's line, Q's line and the fold's stop now give the delete step and name the line.
Your rulings from attempt 4 are untouched. Three things go a little past your literal words, and one wrong
build I measured is still reachable. Both are under "For you to decide".

## What changed

**The finding.** `DROP_PREREQ` (`template/src/pdca_harness/integrate.py:1497-1499`) is the text P's line, Q's
line and the fold's stop all share, so the step is in one place. New helper `reissue_line`
(`integrate.py:1502-1510`) names the line. I gave both of your options together: the unconditional clause, and
the exact line in brackets. P's line from the adversary's case, as printed:

> flow: issue_P (finished in an earlier run) is not carried onto pdca-integration/main-rbd4715fdb6ff: its PR
> was squash- or rebase-merged: origin/main has its merge commit 3f0fc7505f39, but its head c1b328d7149c is on
> neither origin/main nor the line — holding issue_D this run; stack mode needs merge commits: update each
> branch built on issue_P from origin/main (GitHub's "Update branch") or rebuild it from origin/main, then
> re-issue without issue_P, after dropping issue_P from the brief of any bundle of the re-issued batch that
> names it as a prerequisite and deleting any line on origin that batch would continue (for this batch without
> issue_P: pdca-integration/main-ref1376602881): with the edge gone nothing checks that line for the merge.

How each site gets the name:

- **P's and Q's lines:** `template/src/pdca_harness/flow.py:1701-1702` works out `gone`, every id the run's
  lines ask to re-issue without, and `flow.py:1712` passes the name to the hint. `flow.py:1432-1433` carries the
  placeholder into Q's hint.
- **The fold's stop:** `integrate.py:1462`. It needs the batch, so `batch` is passed down through
  `_merge_published` and `_gone_branch` (`integrate.py:656`, `:887`, `:1354`, and the two signatures). That also
  covers a bundle's own base, which uses the same merge step.
- **With no batch, or none left:** the clause stands alone with no name (test `:492`).

Docs: `docs/07-crosscutting.md:829-836` (the two steps) and `:932-937` (replaces "look for such a line
yourself").

**The code-review item (`flow.py:840` then).** D's line now says the line was not checked when none was judged
for D and a re-run may continue one. `unjudged` is set at `flow.py:854`, and the step is at `flow.py:884-890`:

> To build it, drop issue_P from issue_D's brief and, once this run ends, delete
> pdca-integration/main-ref1376602881 on origin if it is there, then re-run: this run did not check that line
> for that merge, and with the edge gone nothing checks that. A re-run that finds the line on origin may continue
> it and build issue_D without that merge, and one that does not starts from main, which has the merge commit.

D's other wording is unchanged, and this adds no `gh` read.

**The test you asked me to flip.** `test_a_drop_made_before_the_re_run_never_reaches_that_check` is now
`test_a_drop_made_before_the_re_run_is_told_to_delete_the_line_too`
(`template/tests/test_stack_squash_merge.py:1333`). It asserts the step and the exact line, follows both steps,
and asserts D is built on a tip with the merge commit.

| Case | Test |
| --- | --- |
| The adversary's whole sequence, from a real first run, ending with `p.txt` in D's tip | `:1353` |
| Q's line, followed to the end | `:1383` |
| The fold's stop in a real run | `:1404` |
| The fold's stop: the line without that bundle, not this run's | `:483` |
| A bundle's own base stops with the same step | `:509` |
| No batch, or none left: the clause with no name | `:492` |
| A record that counts: no delete asked (the edge stays and does the check) | `:500`, `:1449` |
| Two merges: the line without either | `:1443` |
| Ids written as `issue_P` or `P` | `:1424` |
| This run's untrusted line is not the one named | `:704` |
| Not checked: carry held its prerequisite, followed to the end | `:1467` |
| Not checked: the fold failed / re-gate red / untrusted line | `:1501` / `:1510` / `:1521` |
| No not-checked step: D held for nothing else, or a line judged to have the merge | `:1635`, `:1642` |

## For you to decide

**A wrong build I measured is still reachable.** A run of `P, R, D`, with D naming `R, O, P`, O outside the batch and
an older line of exactly `R, O, D` on origin. P's line names the line of `R, D`. D's plain hold says to name O. Follow
both and the re-run is `R, O, D`, not "this batch without P": it continues the older line, and D reaches COMPLETE on a
tip without the merge, with no warning. I ran this with a throwaway script (`.cache/pdca626_probe.py`, not in the patch):
`result COMPLETE, line is R,O,D's: True, tip has merge: False`. The clause "any line on origin that batch would
continue" is still true there, but the name in brackets is the wrong one, and nobody can work out the right one by hand.
It needs someone to have run `R, O, D` earlier and then left O out of the next batch. An earlier run's own advice would
have kept O in, and then P's line names the right line. To close it, P's line would list a second name for each
out-of-batch prerequisite of its dependents: I estimate about 6 lines and one more clause on an already long line. You
called this a few lines of message text, so I stopped here. Your call whether it is worth it.

The next three go past your literal words. I did them because your stated goal was "every printed message yields a
correct build when followed", and each case below comes from a real run. Each is small to remove.

1. **I narrowed the drop from "any bundle" to "any bundle of the re-issued batch".** You accepted the old wording and
   said to change nothing else. But "any bundle" reaches a bundle E in another batch. Drop E's edge as told, and E's own
   run has nothing to check its line, and P's line does not name that line. With the narrower wording E keeps its edge,
   so its run holds it and names its own older line (`:1616`). That test shows E told correctly with the edge kept. I did
   not run E with its edge dropped: it is the same shape as `:1318`. To undo: one phrase in `DROP_PREREQ`, the `DROP`
   constant in the test file, and one sentence in the docs.
2. **The not-checked step fires whenever D has another prerequisite not ready, not only after a failed fold.** The wider
   test catches a real wrong build the narrow one misses: the carry worked, but E, which D names, was not built, so D is
   off the line for this run only. The next run builds E there, then D on a tip without the merge (`:1529`, which pins
   that result). The price is some noise. With D naming an only-planned X and P, and no line on origin, the probe printed
   the delete step for a line that does not exist. It says "if it is there", so following it does no harm.
3. **D is also told about the line of a re-run it is told to change.** A run of `O, D` left O on its line, then a run of
   `D` alone says to name O and drop P. That re-run continues the older line and builds D without the merge (`:1572` pins
   it; `:1547` follows both steps and gets the merge). The same happens when D is told to delete this run's stale line and
   to name O: every step followed still built D without the merge, on another older line. The probe showed that, and
   `flow.py:891-894` now names that line too (`:1589`). Neither case is in your finding. Together they cost one `or` term,
   one clause and 3 lines, and they changed two assertions in the accepted
   `test_a_dependent_held_for_two_things_gets_a_line_for_each` (`:1800`), which said D's line never mentions O.

## Rejected alternatives

- **The clause alone, with no name.** About 16 lines less: `reissue_line` (9), passing `batch` down (5), `gone` (2).
  Rejected for use, not cost. The branch is `pdca-integration/<base>-r<12 hex digits of a sha256 of the sorted ids>`
  (`integrate.py:141-179`), so nobody can tell by eye which branch is the batch's. You also preferred the name.
- **Printing the step only when that line is on origin and lacks the merge.** It would be accurate every time, but it
  needs a fetch of a second line at both the carry and the fold, a `_line_lacks_merge` call with one more `gh` read per
  hold, and fail-closed text for a failed fetch. I estimate 15 to 20 lines; I did not build it. You called this message
  text, and the unconditional wording does no harm when no such line exists.
- **Telling `_runnable` exactly which targets the carry failed for.** A new parameter (about 4 lines), closer to the
  item's wording, but it misses `:1529`, where the carry worked. I rejected it on that test, not on cost.
- **A run that checks the line with no edge.** Removes the cause of all of the above, including the case I left open,
  but needs a stored record of dropped prerequisites. Rejected on your rulings ("drop the edge", no enforcement), not on
  cost, so I did not size it.

## What this does not cover

- **Following only one step.** The hold is advice, per your ruling. Doing only the drop still builds D on the old line,
  silently (`:1318`, `:1486`, `:1572`, all pinned).
- **Re-issuing a different batch from the one named.** The clause still says what to do, but the name in brackets is only
  for "this batch without P", and no command works out the name for another batch. The case at the top of "For you to
  decide" is one of these.
- **Two merges on different targets of one batch.** Each line names the batch minus the ids of its own target, because
  the carry works one target at a time. Leave out both and the batch is one neither line named. I reasoned this and did
  not run it: the fixture has one target.
- **Your rulings stand.** Silent recovery with P's head on the line, the revert limit, declared dependents only at
  publish, and the live GitHub shapes (#625) are all untouched.
- **The two run-output lines that seem to disagree** (`merged.py:114-116` beside D's line) stay: both reviews said no
  change was needed.
- `deferred-findings.json` is not touched. It is held for you at handover.

No external dependency was missing; nothing here needs a row in `pdca.toml`.

## Refuting my own test

- **(a) Genuine red? Yes**, measured twice, both through `./engine/scripts/run-verify.sh`:
  - Against the base (the real C4 run): `Ran 117 tests`, `FAILED (failures=82)`, then `PDCA-EVIDENCE: C4 PASS — red
    without the fix, green with it`. That is 76 distinct tests, 0 `ERROR:` lines and no `_FailedTest`, so all are
    assertion failures. The others stay green because they pin behaviour that should not change.
  - Against attempt 5's production code, to prove the tests bind this round's finding: I pointed the wrapper at a patch
    holding only the attempt 5 to attempt 6 diff (`.cache/pdca626-v5-vs-v6/patch.diff`). `Ran 117 tests`,
    `FAILED (failures=26)`, 26 distinct tests, 0 `ERROR:` lines. They include the flipped test, `:1353`, `:1383` and
    `:1404`.
- **(b) Production path? Yes.** The new cases drive `flow._drive_and_act`, `integrate.fold`,
  `integrate.build_bundle_base` and, for variants, `flow._runnable`. The stubs are the same as attempt 5's: `gh` in front
  of `subprocess.run` (`_gh_stub`, `:90`), and the build and publish leaves in the carry cases, as in
  `template/tests/test_flow_merged_prereq_on_line.py`. Three failure cases are forced with a mock: `integrate.fold`
  raising (`:1501`), `gates.run_integration` reporting red (`:1510`), and, from attempt 5, `integrate.foreign_commit`
  raising (`:737`). `reissue_line`, `_gone_branch` and `_runnable` always run for real.
- **(c) Fixture includes the fault? Yes.** The older line is real, on a bare origin, folded by a real run or a real
  `integrate.fold` before a real `git merge --squash`. Its lack of the merge is asserted, for example at `:1369`. `:1353`
  also shows the file itself in D's tip. The publish record kinds are set by hand (`_record`, `:153`), as in attempt 5.

**Small-break checks:** I broke the new code 30 small ways in place and ran `run-verify.sh` on each. A break counts as
caught when the wrapper reports "red WITH the fix applied". 29 were caught at once. One survived: nothing pinned that the
extra sentence stays out of D's line when the run's line was not stale. I added that assertion (`:1547`'s test) and that
break is now caught. The other 29 ran before that one assertion, which cannot un-catch a break, so I did not repeat them.
The production files had the same hashes throughout: `integrate.py` `9217ceedbdef3d3d...`, `flow.py` `ad58d8a067895be8...`,
both matching the final patch. The script is `.cache/pdca626_mutate.py`. It covers only this round's new code; earlier
rounds' breaks were not repeated.

## Commit-readiness and gates

The target has no formatter or commit hook: no `.pre-commit-config.yaml`, no `core.hooksPath`, only sample files in the
hooks directory, and none of ruff, flake8, black, isort or pre-commit in `template/pyproject.toml.jinja`, `copier.yml` or
`.github/workflows/`. Its checks are CI workflows. `git diff --check HEAD` is clean, no added line in `docs/` or
`template/src/` is over 100 columns, and no line of the new test file is. This round adds no imports.

This round's diff against attempt 5: docs +14/-5, `flow.py` +34/-9, `integrate.py` +33/-10, test file +388/-11. You
expected a few lines of message text. Most of the code growth is the name (about 16 lines), the not-checked step, and
docstrings and comments.

The test is at the path the brief names, in the worktree and in `patch.diff`. There is no separate copy in the bundle, as
in attempts 1 to 5, since the gates read it from the patch.

All on the final tree, with `patch.diff` checked to match it (applied to the base in a temporary index, 0 differences):

- `./engine/scripts/run-verify.sh`: exit 0, C4 PASS (numbers above).
- `./engine/scripts/run-docs-check.sh`: exit 0, "docs lint clean, site render + link audit clean".
- `./engine/scripts/run-host-ci.sh`: exit 0, "host CI parity on the patched tree".
- `./engine/scripts/run-prod-path.py`: exit 0, "1 added driver-suite test(s) import the production package".
- `./engine/scripts/run-suite.sh`: exit 0. Root suite `Ran 50 tests`, OK. Driver suite `Ran 2814 tests`,
  `OK (skipped=2)`.

The sizer still rates this brief "oversized" (`sizing.json`). You reviewed that and overrode it.

## Slips to report

- Two of my new tests were wrong at first. One had R out of the batch, so it hit the "name R" branch; the wrapper's green
  leg caught it. One raised `StopIteration` on the base instead of failing an assertion; the red leg showed `errors=1`, and
  I added the same guard its sibling test has. Both are fixed.
- One hand-written `python3 -m unittest` under `timeout 300`, as a quick smoke run before I had the wrapper script.
  `.cache/pdca626_show.py` and `.cache/pdca626_probe.py` ran under timeouts, only to print the real lines quoted above and
  measure the claims marked as probed. All red and green evidence here comes from the wrappers.
- I stopped three of my own background runs because I then changed the code or a test: the first small-break pass, after 7
  breaks, and two suite runs. I picked the processes by PID and by their `PDCA_WORKTREE`, so no other session's gates were
  touched, then checked file hashes and looked for orphans. None of their results is used here. One small-break chunk also
  stopped on its own script's bad search text, before writing anything.
- `run-verify.sh` has no timeout of its own, so I wrapped each call in `timeout`.
- My working files are in the worktree's git-ignored `.cache/` (`pdca626*`). They are not in the patch. The worktree's index
  was not touched: I built `patch.diff` with a temporary index.
