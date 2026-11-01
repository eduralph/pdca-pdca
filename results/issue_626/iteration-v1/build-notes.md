# Build notes — issue 626 (stack squash/rebase merge recognised and refused up front)

Built on `f5321ab` (the bundle's `stack-base-tip`, on `pdca-integration/main-re715db900335`).
The brief's line numbers are from an older main; the numbers below are this tree's, with the
patch applied. The brief's recommended option ("refuse, recognise and explain") is what is
built. Alternative A (support the merges) is not.

## What changed

- **Publish** (`template/src/pdca_harness/publish.py:372-374`, new `_has_dependent` at :831,
  wording at `_warn_if_squash_only` :848): warns also when `cfg.wave_mode == "stack"` and
  another bundle's brief names this id through `waves.declared_deps`. The results root is
  scanned inside `publish.publish`, so `pdca publish`, sign-off accept and the flow all get it
  with no new parameter. The scan runs before `gh`, so an independent PR costs no `gh` call.
- **Fold** (`template/src/pdca_harness/integrate.py:1452-1462`, new `_squash_merged` at :1473):
  a gone branch with its head on neither base nor line, and a merge commit on the base, raises
  a message that names the squash or rebase merge, the full oid and the step. Otherwise today's
  message, unchanged.
- **Carry** (`template/src/pdca_harness/flow.py:1283-1313` `_finished_head`, hints :1333-1342,
  cascade :1439-1442): same shape gets the `squashed` reason and hint. Dependents get
  `built_on_squashed`. They stay held.
- **Docs**: `docs/07-crosscutting.md`, the stack-mode bullet (:694-697), the gone-branch passage
  (:734-741), the carry passage (:814-819) and Known limits (:866). The module and function docstrings
  in `integrate.py`, `flow.py` and `merged.py` that said otherwise are corrected too.

## Decisions a reviewer of the brief might want to check

**1. The advice says "re-issue without issue_P". The brief does not say this, and I added it
because the advice is false without it.** The brief's text is "update the dependent ... and
re-issue". Followed literally with P still in the batch, the next run reads P as squash-merged
again, and Q's `Depends on: P` holds Q again with the same message, however Q was updated. So
that advice would loop forever. Leaving P out of the batch works with no new behaviour:
`_reached` does not follow an edge to an id outside the finished set (`flow.py:1388-1410`), and a
planned bundle's `Depends on: P` is then judged by `merged.merged_into`, which is true.
`test_the_way_out_the_hold_gives_works` follows it end to end: update Q, run `["Q", "D"]`, Q is
carried, D (`Depends on: Q, P`) is built on a line holding the squash commit.

Rejected alternative: release Q from the cascade once Q's head holds P's merge commit, so the
same batch works. It costs about 12 lines: `_cascade_not_clean` needs `repo`, `heads` and each
squashed id's oid passed in (3 more parameters and one `_carries` check in its loop), and
`_finished_head` must return the oid as well. It is also not enough: P stays in `held`, so a
planned D with `Depends on: P` is still held by `_runnable`, and D has nothing to update. That
case would still need "without issue_P", so the change would add a second way out without
removing the first. The brief's Impact section also says message text only, no behaviour change.
If the maintainer wants the same batch to work, that is a follow-up. The docs state the way out
as built.

Worth weighing at sign-off: the docs and hints go one step beyond the brief's wording here.

**2. A head no clone has counts as "on neither".** Today `_finished_head` returns "its PR head
... is not in <repo>" with the `open` hint before it looks at the merge state. A squash merge
with the branch deleted, from a clone that never had the head, would have hit that path and
told the human to re-open the PR, which is wrong. So the merge-commit check now runs first
(`flow.py:1301-1309`); `_carries` already treats a missing commit as "not in it". If the merge
commit is not on the base, the path falls through to the same `open` or `edge` result as today.
An empty head stays `open`: with no head reported, "on neither" cannot be known.

**3. A chain names the merged id.** With R on Q on P, today's walk would give R "get issue_Q
carried". `_cascade_not_clean` now gives the root P as the cause for a squash-rooted chain
(`flow.py:1439-1442`). Other causes keep the immediate id, as `test_flow_resume_stack_prereqs`
pins. A Q with two not-clean prerequisites gets whichever comes first in its brief, as it does
today; after that one is dealt with, the next run names the other.

**4. An existing test helper changed.** `_merged_heads`
(`template/tests/test_integrate_stack_bases.py:110`) now also patches `merged.merge_and_head` to
None. Without that, every `_merged_heads` case reaching the "base lacks the head" branch would
run the real `gh` against `example.test`. These cases failed closed anyway, so their assertions
do not depend on it; it keeps them offline. C4 runs that module too because it is in the patch:
62 tests, green on both legs, as expected for a helper change.

**5. `_finished_head` gained a leading `cfg` parameter**, because `merged.merge_and_head` needs
it. It has one caller (`flow.py:1531`) and no test calls it directly.

## What this does not cover

- **A later wave with no declared edge.** The Goal says "a later wave or a dependent", but the
  Success criterion defines the check as a declared-dependency scan, and (d) requires silence
  without one. So a wave-0 PR whose later wave comes only from `Conflicts with`, or from another
  chain on the same line, does not warn, even though the line carries it into that later wave's
  PR. I followed the criterion. Widening it would be a small change to `_has_dependent`.
- **`Onto branch` publishes** (`_publish_stacked`, called at `publish.py:227`) return before the
  warning, as today. They add a commit to an existing PR and open none.
- **`--dry-run`** returns before the warning, as today (`publish.py:355`).
- **`results/completed/`** is not scanned; the brief specifies `issue_*/brief.md` under the root.
- **The real GitHub shapes after a squash** are not checked here. The stub follows
  `merged.merge_and_head`'s documented contract, and the brief says #625 will confirm the live
  shapes and is not a prerequisite. If GitHub's `mergeCommit` read differently, this would fail
  closed to today's messages (c3), not misreport.

## Refuting my own test

- **(a) Genuine red? Yes.** `./engine/scripts/run-verify.sh` reverted the production hunks and
  kept the tests: `Ran 25 tests`, `FAILED (failures=15)`, across publish, fold and carry, then
  `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`. The 15 failures are 11 tests:
  one of them has 5 failing subtests. Failures are assertions, not import errors: the test
  imports only modules. The 14 tests green on the red leg are the negative legs (c2, c3 on the
  fold, c3's empty read on the carry, d, d2, e, and "no extra read"). They pin today's behaviour,
  so they should pass there.
- **(b) Production path? Yes.** The tests drive `publish.publish`, `integrate.fold` and
  `flow._drive_and_act`. Only `gh` is stubbed, at `subprocess.run`, with the same shape
  `test_flow_merged_prereq_on_line.py:111` uses. The build and publish leaves are stubbed in the
  carry cases as in that peer test; the carry and the fold under test are real.
- **(c) Fixture includes the fault? Yes.** A real `git merge --squash` is pushed to a bare
  origin, and the test asserts the head is not an ancestor of main. The branch is really deleted
  where the case needs it. The "clone never had the head" cases use an oid no repository holds.
  Negative cases use a real squash into a real `release` branch.

## Commit-readiness

No formatter or pre-commit config exists in the target (no `.pre-commit-config.yaml`, no
ruff/black settings); its checks are CI workflows. The docs check result is below.

`./engine/scripts/run-docs-check.sh`: exit 0, `lint_docs: OK`, site render and link audit clean.
`./engine/scripts/run-suite.sh`: exit 0, root suite `Ran 50 tests ... OK`, driver suite
`Ran 2722 tests ... OK (skipped=2)`. I did not check what the 2 skips are.

## A slip to report

While running the gate I redirected its log to `/tmp/pdca-626-verify.log`, outside the roots I
was given. It is a log only and nothing depends on it. I did not remove it, because cleanup is
the harness's job. Later logs went to the worktree's git-ignored `.cache/`
(`pdca626-docs.log`, `pdca626-suite.log`). I also briefly wrote a compare copy of the patch into
the bundle directory and moved it to `.cache/pdca626-patch-compare.diff`.
