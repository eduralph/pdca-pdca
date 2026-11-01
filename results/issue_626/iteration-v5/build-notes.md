# Build notes — issue 626, attempt 5 (stack squash/rebase merge recognised and refused up front)

Built on `f5321ab` (the bundle's `stack-base-tip`, on `pdca-integration/main-re715db900335`), starting
from `iteration-v4/patch.diff`. Line numbers below are this tree's, with the patch applied.

You rejected attempt 4 for two findings and said to change nothing else. This round changes D's hold
line, two docstrings, one comment, one docs paragraph and the test file. The rest of attempt 4 is
byte-for-byte what you accepted, and your rulings are untouched.

## The two findings

**1. The drop could build D on a line older than the merge.** Fixed in
`template/src/pdca_harness/flow.py:840-847` (the check) and `flow.py:863-881` (the line). When D's line
would be cut from a line of this run, it now calls `_line_lacks_merge` (`flow.py:994`), the same check and
the same cache a record that counts uses. If the line has neither P's merge commit nor P's head, the step
gains the delete. The real line, from your reviewer's case:

> flow: issue_D held — prerequisite(s) issue_P (merge commit c6f08bc12c41): their PR was squash- or
> rebase-merged into main (org/repo), but their publish record (publish.json) never counts as merged into
> main, so waiting for a merge will not build it. To build it, drop issue_P from issue_D's brief and, once
> this run ends, delete pdca-integration/main-ref1376602881 on origin, then re-run: the line issue_D would
> build on, pdca-integration/main-ref1376602881 at a254982537ae, does not have the merge of issue_P, and
> with the edge gone nothing checks that. A re-run that finds the line on origin may continue it and build
> issue_D without that merge, and one that does not starts from main, which has the merge commit.

Docs: `docs/07-crosscutting.md:920-927`. Tests in `template/tests/test_stack_squash_merge.py`:

| Case | Test |
| --- | --- |
| Your reviewer's case, for 3 record kinds and a `Depends on (merged)` edge | `:1200-1229` |
| Both steps followed: D is built on a line with the merge commit | `:1231` |
| The drop alone: D reaches COMPLETE at a tip without the merge, silently (why both steps are needed) | `:1246` |
| No delete step: the line has P's head (`:1278`) or the merge commit (`:1301`) | |
| No delete step: D is built from the base (`:1313`, a real run followed to the end; `:1367`) | |
| No delete step: no line, no recorded tip, or another target's line | `:1356` |
| The line cannot be checked: fails closed, says "is not known to have", gives the reason | `:1329` |
| Two to drop, only one missing from the line: only that one is named as missing | `:1340` |
| Two dependents share the one read for the line | `:1375` |

`_assert_told_to_drop` (`:1038`) now also fails on any delete step the case did not ask for, so every older
case of D's line checks that too.

**2. D's line said the base had the PR's work.** `flow.py:879-880` now says "their PR was squash- or
rebase-merged into {base} ({repo}), but their publish record ...". The sentence "so {base} has the PR's
work" is gone. The delete step's last clause says "which has the merge commit" for the same reason. The
revert cases are real `git revert` commits pushed to a bare origin, with `main` checked to no longer hold
`p.txt`: `:1391`, and with an older line `:1402`. `_assert_told_to_drop` bans the wording on every case.

I fixed the same claim in two places no line prints: the `_uncounted_squash` docstring (`flow.py:937-941`)
and the comment above `SQUASH_STEP` (`template/src/pdca_harness/integrate.py:1477`). The docs add what the
check cannot see (`docs/07-crosscutting.md:918-920`).

## For you to decide at sign-off

- **The same wrong build is still reachable by following P's own line.** Finding 1 names D's line, so that
  is what I changed. But P's line, for a record that never counts, asks for the drop up front ("re-issue
  without issue_P, after dropping issue_P from the brief of any bundle that names it"). Follow that with an
  older line for the re-issued batch on origin, and no run ever sees D naming P, so nothing mentions the line:
  D reaches COMPLETE on a tip without the merge. I ran this: `:1261` pins it. You said to change nothing
  else, so the only changes are that test and one docs sentence telling you to look for such a line
  (`docs/07-crosscutting.md:925-927`). To close it, P's and Q's hints could add a clause such as "and delete
  any line on origin that batch would continue": about 2 lines in `integrate.DROP_PREREQ`, and that test
  flips. It would be unconditional text, since P's line does not know the next batch. Naming the exact line
  means working out the batch without P and reading origin, which I estimate at about 10 lines.
- **Both steps on one line, or one at a time?** I put both on one line, as you asked ("give the delete-the-line
  step too"). That still lets someone do only the drop, and D then builds on the old line (`:1246`). The other
  way: while the line lacks the merge, D's line gives only the delete, and the next run, on a fresh line,
  gives the drop. Doing only the drop is then much harder, because the line does not offer it until the old
  line is gone. It is about the same amount of code, and costs one more run for each such D.
- **After a revert, the drop still builds D without the change.** The line no longer claims the base has the
  work, and the docs say the check cannot see a revert, but the printed step is the same. `:1411` pins it. I
  read your fix as wording only, so nothing looks for the revert.

## Rejected alternatives

- **Save the second `gh` read by reusing the first answer.** A hold with a line now makes two
  `gh pr view --json ...mergeCommit` reads where attempt 4 made one (`:1329` pins `["P", "P"]`). A hold with no
  line stays at one (`:1356`). You ruled to keep "its one extra `gh` read on a hold", and I read that as
  keeping the read, not as a cap; tell me if you meant a cap. Saving it means `_squash_merged` must hand back
  the head as well as the merge commit, `_uncounted_squash` must return a pair, and `_line_lacks_merge` must
  take an optional pair: I estimate about 8 changed lines across 3 functions, one of them shared with the fold
  and the carry, to save one read on a path already stopped for a person. For scale, a record that counts makes
  one `merged_into` read and one `_line_lacks_merge` read here; this path makes those two plus
  `_uncounted_squash`'s.
- **Make a later run check the line with no edge.** That removes the cause, but after the drop nothing ties D
  to P, so a run would need a stored record of dropped prerequisites. I rejected it on your rulings ("keep
  drop the edge", and no enforcement), not on cost, so I did not size it.

## What this does not cover

- The delete step is advice. Nothing stops a run on the old line once the edge is gone (`:1246`), per your
  rulings.
- "Update branch" after a reverted squash keeps the reverted change: your accepted limit, not touched.
- `--no-publish`, merge mode and dry-runs have no line here, or never reach this line, so none gets the step.
- The live GitHub shapes after a squash or rebase: #625's, per your ruling.
- `deferred-findings.json` is not touched. It is held for you at handover.

No external dependency was missing; nothing here needs a row in `pdca.toml`.

## Refuting my own test

- **(a) Genuine red? Yes**, measured twice, both through `./engine/scripts/run-verify.sh`:
  - Against the base (the real C4 run): `Ran 95 tests`, `FAILED (failures=62)`, then `PDCA-EVIDENCE: C4 PASS
    — red without the fix, green with it`. That is 56 tests failing, some with several failing subtests. 0
    `ERROR:` lines and no `_FailedTest`, so all are assertion failures. The other 39 stay green because they
    pin behaviour that should not change.
  - Against attempt 4's production code, to prove the tests bind this round's findings: I pointed the wrapper
    at a patch holding only the attempt 4 to attempt 5 diff (`.cache/pdca626-v4-vs-v5/patch.diff`). `Ran 95
    tests`, `FAILED (failures=25)`, 23 distinct tests, 0 `ERROR:` lines.
  - **What that second run does not show by itself:** 20 of those 23 fail first on the old wording ("main
    has"), which hides whether they would also catch the missing delete. The small-break checks below settle
    that: with the new wording kept and the line check removed, 9 tests fail; with only the delete removed
    from the step, 8 fail.
- **(b) Production path? Yes.** The new cases drive `flow._drive_and_act` and, for variants, `flow._runnable`
  directly. Only `gh` is stubbed, in front of `subprocess.run` (`_gh_stub`, `:87`), and the build and publish
  leaves in the carry cases, as in the peer test `template/tests/test_flow_merged_prereq_on_line.py`.
  `_line_lacks_merge`, `_squash_merged` and `merged.merge_and_head` run for real. This round adds no mocks.
- **(c) Fixture includes the fault? Yes.** A real older line sits on a bare origin, folded by a real
  `integrate.fold` before a real `git merge --squash`, and `_line_older_than_the_merge` (`:1185`) asserts it
  has neither the merge commit nor the head. The revert is a real `git revert`, and `:1391` asserts `main` lost
  the file. The record kinds are the `publish.json` shapes `_publish_stacked` writes, set by hand (`_record`,
  `:150`), as in attempt 4.

**Small-break checks:** I broke the new code 19 small ways in place and ran `run-verify.sh` on each. A break
counts as caught when the wrapper reports "red WITH the fix applied". On the final tree all 19 were caught. On
the first pass one was badly written (its search text matched two places), so I fixed it before this run.
`flow.py` was restored after each, and its hash after the last run is the one the final patch carries
(`1a80c9e4eb15df31...`). The script is `.cache/pdca626_mutate.py`. These breaks cover only this round's new
code; attempt 4's 55 are not repeated.

## Commit-readiness and gates

The target has no formatter or pre-commit config: no `.pre-commit-config.yaml`, no `core.hooksPath`, no active
hooks, and none of ruff, flake8, black, isort or pre-commit appears in `template/pyproject.toml.jinja`,
`copier.yml` or `.github/workflows/`. Its checks are CI workflows. `git diff --check HEAD` is clean, and no added
line in `docs/` or `template/src/` is over 100 columns, nor any line of the two test files. This round adds no
imports.

All on the final tree, with `patch.diff` checked to match it byte for byte:

- `./engine/scripts/run-verify.sh`: exit 0, C4 PASS (numbers above).
- `./engine/scripts/run-docs-check.sh`: exit 0, "docs lint clean, site render + link audit clean".
- `./engine/scripts/run-prod-path.py`: exit 0, "1 added driver-suite test(s) import the production package".
- `./engine/scripts/run-suite.sh`: exit 0. Root suite `Ran 50 tests`, OK. Driver suite `Ran 2792 tests`,
  `OK (skipped=2)`.

I did not repeat attempt 4's check that no other test reaches a real `gh`. The new read sits behind
`_uncounted_squash` returning a merge commit, which only the stubbed cases in this module can do, so it opens
no new route. I reasoned that and did not measure it this round.

The sizer still rates this brief "oversized" (`sizing.json`). I built it as one change, as the brief specifies.

## Slips to report

- One inline edit script was refused by the builder guard hook, because its text held the words of a `gh pr`
  command. Nothing in it ran. I redid those edits with the edit tool.
- `.cache/pdca626_show.py` ran outside the project's runner, with a 120-second timeout, only to print the real
  hold lines quoted above. All red and green evidence here comes from the wrappers.
- `run-verify.sh` has no timeout of its own, so I wrapped each call in `timeout`.
- My working files are in the worktree's git-ignored `.cache/` (`pdca626*`). They are not in the patch. The
  worktree's index was not touched this round: I built `patch.diff` with a temporary index.
