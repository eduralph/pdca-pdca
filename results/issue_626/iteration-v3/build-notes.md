# Build notes — issue 626, attempt 3 (stack squash/rebase merge recognised and refused up front)

Built on `f5321ab` (the bundle's `stack-base-tip`, on `pdca-integration/main-re715db900335`).
The brief's line numbers are from an older main; the numbers below are this tree's, with the
patch applied. The brief's recommended option ("refuse, recognise and explain") is what is
built. Alternative A (support the merges) is not.

This attempt started from `iteration-v2/patch.diff` and changes little: one docs sentence was the
carry-forward, and the rest is the same mistake elsewhere plus the smaller review findings. The 10
deferred findings are not build work and their behaviour is untouched.

## The carry-forward finding

**The Known limits line was too broad (`docs/07-crosscutting.md:882-884`).** It said any squash- or
rebase-merged prerequisite holds the dependents and is named. That is false when the head is already
on the line: `test_a_head_already_on_the_line_is_carried_with_its_branch_deleted_too`
(`template/tests/test_stack_squash_merge.py:656`) carries P and Q and builds D, and nothing names the
merge. It now reads "whose head is on neither your base nor the line", the fix the adversary named.
I added "unless its merge commit cannot be read", because then the prerequisite is held but not
named (criterion c3, `test_an_unreadable_merge_commit_keeps_the_edge_hint`, :834).

Rejected: going back to the original "with its branch deleted". That shape is the failing case
itself, so the original wording was wrong too.

## The same mistake elsewhere

I looked for other places that say more than the code does:

- `docs/07-crosscutting.md:877-879` said any squash-merged prerequisite keeps its reason under an
  untrusted line. With its head on the line it is clean, so it gets the plain line reason. It now
  says "named as". New test: `test_an_untrusted_line_names_no_merge_for_a_head_already_on_it` (:659).
- `publish.py:881` and its docstring (`publish.py:863`) said the next fold or re-issue "stops". It
  "can stop": not with the head on the line.
- The `_carry_finished` docstring (`template/src/pdca_harness/flow.py:1484-1488`) now gives the
  limit too.

The docs now also say what happens in the other shape (`docs/07-crosscutting.md:829-832`): clean,
carried, nothing named, and PRs keep showing the change until updated. The behaviour is unchanged.
The last part is pinned at `test_stack_squash_merge.py:650`. Whether silence is acceptable there is
still the deferred question below; the docs now state the fact rather than leave it out.

## Other review findings fixed, since this round rebuilds anyway

- **Advice that was false about a dependent (adversary, low severity).** The `built_on_squashed`
  hint said "{name}'s branch holds commits {base} never got" even for a Q already rebuilt from the
  base and merged. The hint is now general and conditional: "a branch built on it holds commits...
  update {name}'s branch... or rebuild {name}... if you have not" (`flow.py:1341-1344`). Test: :785,
  which rebuilds Q from main, merges it with a merge commit, and re-issues the same batch.

  Rejected: the adversary's other suggestion, separate wording when the dependent's head is on the
  base. That costs about 8 production lines: a fourth hint and its `_SQUASH_HINTS` entry, a loop
  after the cascade in `_carry_finished`, and one more git read per held id. This fix changes one
  string. The check would also miss a Q that was updated with "Update branch", whose head is not on
  the base, while "if you have not" covers it.
- **The misleading test name (code reviewer).** Now
  `test_those_records_keep_their_message_when_the_merge_commit_cannot_be_read` (:425), and it asserts
  the read happened. A mutant that skips the read for those records now fails.
- **The step written out by hand, with "re-drive" at the fold and "rebuild" at the carry (code
  reviewer, marked optional).** Now one constant, `integrate.SQUASH_STEP` (`integrate.py:1479`), used
  at `integrate.py:1454` and `flow.py:1339-1340`. `flow._SQUASH_STEP` is gone. `_assert_both_name_it`
  (:714-716) pins the same words at both sites. The brief's Design item 2 says "re-drive"; criterion
  (c) says "rebuild", and (b) fixes no word for the step. The docs follow (`docs/07-crosscutting.md:738-739`).
  The third text, in `built_on_squashed`, stays separate because it speaks of one named dependent.
- **Untested `OSError` branch in `_others_build_on` (adversary).** Test at :228: another bundle's
  `brief.md` is a directory, and a readable brief after it still counts.

## What the whole patch does

- **Publish** warns about a repo with no merge commits for a PR cut from a stack base and, in stack
  mode, for any bundle another bundle names as a prerequisite. `publish._others_build_on`
  (`publish.py:835`) does the results-root scan with `waves.declared_deps`. Callers: the new-PR path
  (`publish.py:373`) and the `Onto branch` path (`publish.py:535`).
- **Fold**: `integrate._gone_branch` (`integrate.py:1407`) names a squash or rebase merge, with the
  full merge commit and the step, when the head is on neither the base nor the line and the merge
  commit is on the base (`integrate.py:1445-1455`, helper `_squash_merged` at `integrate.py:1488`).
  Otherwise today's messages.
- **Carry**: `flow._finished_head` (`flow.py:1283`, the check at `flow.py:1301-1311`) gives that shape
  its own reason and hint (`flow.py:1339-1344`). The cascade gives dependents `built_on_squashed` and
  names the merged id all along a chain (`flow.py:1454-1457`). They stay held. `_hold_all`
  (`flow.py:1361`, used at `flow.py:1562` and `flow.py:1564`) keeps those reasons under an untrusted
  line or a failed read.
- **Docs**: `docs/07-crosscutting.md:694-698`, `:735-744`, `:818-832`, `:877-884`. Docstrings in
  `merged.py` and `integrate.py` follow. The fixture at `template/tests/test_integrate_stack_bases.py:115-120`
  makes the merge commit read as unknown, so its cases reach no real `gh`.

## For you to decide at sign-off

- **The hold is not enforced until the update (deferred).** The brief's Design item 4 says the
  prerequisite holds dependents "until they are updated from the base". As built, dropping P from the
  batch is what releases Q, updated or not. This is pinned (`test_the_run_does_not_check_the_update`,
  :924) and documented, not fixed. By attempt 1's count, enforcing it costs about 12 lines, and it
  would not remove the need for "without P".
- **The usual recovery run names nothing (deferred).** Re-issuing the same ids after a fold usually
  finds P's head on the line, so P is clean and the run is silent, while Q's PR keeps showing P's
  change. The brief's "head on neither" asks for exactly this, and
  `test_a_head_already_on_the_line_is_carried_with_no_read` (:653) pins that no merge commit is read.
  A warning here would need that read.
- **The advice goes beyond the brief's wording.** The brief says "update and re-issue". The patch says
  "re-issue without P", because with P still in the batch the hold repeats forever.
- **P's line can ask to drop an edge.** Criterion (c) bans the `edge` hint's text on P's line. For
  `Onto branch` and legacy records only, `integrate.DROP_PREREQ` (`integrate.py:1485`) asks for much
  the same thing in other words, because there it is true. Tell me if you read (c) as banning that too.
- **The sizer rated this brief "oversized"** (`sizing.json`), with proposed seams. I built it as one
  change, as the brief specifies. The patch is 82 KB across 7 files.

## What this does not cover

- A later wave with no declared edge. The Goal says "a later wave or a dependent", but the criterion
  defines the check as a declared-dependency scan and (d) requires silence without one.
- `--dry-run` never warns, on either path, as before.
- `results/completed/` is not scanned; the brief specifies `issue_*/brief.md` under the root.
- A squash-merged PR whose branch still exists: the fold merges the branch as it always did, since it
  only asks the host about a gone branch. The carry names it either way. Neither changed here.
- The real GitHub shapes after a squash or rebase. The stub follows `merged.merge_and_head`'s documented
  contract, and the brief says #625 confirms the live shapes and is not a prerequisite. If GitHub
  answered differently, this fails closed to today's messages (c3) and does not misreport.

No external dependency was missing; nothing here needs a row in `pdca.toml`.

## Refuting my own test

- **(a) Genuine red? Yes.** `./engine/scripts/run-verify.sh` on the final patch reverted the production
  hunks and kept the tests: `Ran 53 tests`, `FAILED (failures=29)`, then `PDCA-EVIDENCE: C4 PASS — red
  without the fix, green with it`. That is 25 tests failing, one of them with 5 failing subtests. All
  are assertion failures: 0 `ERROR:` lines and no `_FailedTest`. The other 28 stay green there because
  they pin behaviour that should not change (c2, c3, d, d2, e, no extra read, a head on the line).
- **(b) Production path? Yes.** The tests drive `publish.publish` (both paths), `integrate.fold` and
  `flow._drive_and_act`. Only `gh` is stubbed, in front of `subprocess.run` (`_gh_stub`, :78);
  `merged.merge_and_head` is not mocked. The build and publish leaves are stubbed in the carry cases, as
  in the peer test `template/tests/test_flow_merged_prereq_on_line.py`. One case mocks
  `integrate.foreign_commit` to raise (:618), because a real `git rev-list` failure cannot be forced on
  a healthy fixture; the code it drives is the real `except` branch.
- **(c) Fixture includes the fault? Yes.** A real `git merge --squash` or rebase is pushed to a bare
  origin, and the helper asserts the head is not an ancestor of the target (:131). The branch is really
  deleted where the case needs it. The line cases have a real line on origin, holding the old head or a
  foreign commit. "Clone never had the head" cases use an oid no repository holds. Negative cases use a
  real squash into a real `release` branch. Other record kinds are the `publish.json` shapes
  `_publish_stacked` writes, set by hand; the `Onto branch` publish tests run that path for real.

**Mutation check:** I broke the production code 42 small ways, each on a copy of `template/src` under
the worktree's git-ignored `.cache/`, and ran the test module against each. 41 turned it red, including
the round-1 mutant that ignored the line and one that restores the old `built_on_squashed` wording. The
survivor changes `if info.get("mergeCommitAllowed") is False` (`publish.py:877`) to `is not True`. This
patch does not change that line, so I left it. The only edit after this run was a comment and a docstring
rewrap in `flow.py`.

## Commit-readiness and gates

The target has no formatter or pre-commit config (no `.pre-commit-config.yaml`, no ruff/black settings,
no `core.hooksPath`, no active hooks); its checks are CI workflows. `pyflakes` is not installed here, so I
ran a small AST check for unused imports on the 6 changed Python files (none), which does not cover unused
local names. `git diff --check HEAD` is clean.

All on the final patch, with the worktree matching `patch.diff`:

- `./engine/scripts/run-verify.sh`: exit 0, C4 PASS.
- `./engine/scripts/run-docs-check.sh`: exit 0, `lint_docs: OK`, 64 pages rendered, link audit OK.
- `./engine/scripts/run-prod-path.py`: exit 0.
- `./engine/scripts/run-suite.sh`: exit 0. Root suite `Ran 50 tests`, OK. Driver suite `Ran 2750 tests`,
  `OK (skipped=2)`.

I did not re-run attempt 2's logging `gh` stand-in over the whole suite. This attempt adds no new `gh`
read, so its result (no existing test reaches the patch's new reads) should still hold, but that is
reasoning, not a fresh measurement.

## Slips to report

- Before `patch.diff` existed I ran the test module once by hand (`timeout 280 python3 -m unittest
  tests.test_stack_squash_merge`). The mutation run and a script that prints the real messages also went
  outside the project's runner, each with a timeout. The red-to-green evidence above comes only from
  `run-verify.sh`.
- My working files are in the worktree's git-ignored `.cache/` (`pdca626*`). I left them for the harness
  to reclaim. They are not in the patch.
