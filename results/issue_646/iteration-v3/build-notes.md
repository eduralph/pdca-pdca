# Build notes — issue #646 (stack-reissue-continues-batch-line), attempt 3

Withheld from the reviewer. For the human at sign-off.

## Base I built on

The worktree (`$PDCA_WORKTREE` = `/home/eddie/pdca/pdca-harness.pdca-wt`) is at
`origin/pdca-integration/main` @ `12405dc` (`origin/main` @ `c67a14d` plus the folds of #531,
#590, #591), the same base as attempts 1 and 2; the bundle's `stack-base` file says
`pdca-integration/main`. All `path:line` below are on the patched worktree (`12405dc` +
`patch.diff`).

**For the human (same as before):** the brief says not to build until #639 (#591) is merged
into `main`. On my local refs `origin/main` is still `c67a14d`, so it is not merged there, but
the worktree has #591 through the integration line, so the `TypeError` concern behind that
rule does not apply. The PR is a stacked PR off the integration line; until #531/#590/#591
merge, its diff against `main` shows their changes too.

## What changed since attempt 2, by sign-off item

I kept attempt 2's approach and its four earlier fixes, and changed how the line is checked.
Attempt 2 asked "is this one closed bundle on the line?" (a blacklist). It could not answer
for a head it could not resolve, for bundles it did not look at, or for an old version of a
bundle. Now the fold asks the opposite question: **can every commit on the line be vouched
for?**

1. **Unresolvable head = unknown, not absent.** The check is positive, inside the fold:
   `integrate._vouch` (`template/src/pdca_harness/integrate.py:564-586`). Every commit the
   line holds beyond the base must be either a merge commit on the line's first-parent chain
   (the folds' own) or the work of a bundle carried now, at the head it has now (`_own`,
   `integrate.py:589-596`). A bundle whose head this clone lacks accounts for nothing, so its
   commits stay unaccounted and the line is refused (`LineRefused`, `integrate.py:74-95`).
   The stderr line then says "it may hold issue_P … the run cannot tell", with no "is not
   carried" (`flow.py:953-1001`). Regression test: the reviewer's C3 case,
   `test_4c_a_closed_pr_whose_head_this_clone_lacks_is_unknown_not_absent`
   (`template/tests/test_flow_resume_stack_prereqs.py:712`). The same rule covers a bundle
   the run *does* carry (a squash-merged PR whose branch was deleted after an unfetched
   fixup): `test_4c_a_carried_pr_whose_head_this_clone_lacks_is_not_vouched_for` (`:736`).
2. **Every requested id is checked, and old versions are caught.** Because the check vouches
   for the whole line, anything that is not current carried work refuses it. That covers a
   drive-set bundle the earlier run folded and that was since iterated, a finished bundle
   whose branch was force-pushed with a rebuild, any other requested id's commits, and an
   adopted split child's. For the message, `integrate.holds` (`integrate.py:599-615`) checks
   each requested id of the target by commit, so the line names who it holds. Tests:
   `test_2_a_line_holding_a_rebuilt_bundles_earlier_version_is_not_built_on` (`:447`) and
   `test_2_a_line_holding_an_earlier_version_of_a_re_pushed_bundle_is_not_built_on` (`:473`).
3. **An empty `pr_url` is not a dead end.** `merged.pr_state` (`merged.py:98-149`) now looks
   the PR up by its branch when `publish.json` has no `pr_url`: `gh pr list --head <branch>
   --state all`, matched on branch and owner as `publish._existing_pr` matches, preferring
   OPEN, then MERGED, then CLOSED. A PR the human opened by hand (which publish tells them to
   do) is found, so the bundle is carried. If there is no PR at all, the state is `"NONE"`
   and the advice is the exact command (`flow.py:899-907`):
   `gh pr create --draft --repo <repo> --base <base> --head <owner>:<branch>`. The owner
   comes from a new one-line helper, `publish._pr_head` (`publish.py:834-839`), now also
   used by publish itself (`publish.py:324`), so there is one definition. Tests:
   `test_4d_an_empty_pr_url_is_looked_up_by_its_branch` (`:602`) and
   `test_4d_a_line_holding_a_bundle_with_no_pr_says_how_to_open_one_and_that_works`
   (`:621`). The second one follows the printed advice (opens the PR) and re-issues the same
   command, and the run then carries P and builds. Also
   `test_4d_no_pr_for_its_branch_holds_its_dependents_and_says_how_to_open_one` (`:580`),
   where another fork's same-named branch is ignored.
4. **Optional cleanup, done.** One helper, `_fold_and_regate` (`flow.py:754-795`), does fold →
   tip read → `integ` update → re-gate in one lock scope. The carry (`flow.py:868`, `:918`)
   and the fold after every wave (`flow.py:2352`) both call it. The in-run stop messages are
   byte-identical to before.

Also from attempt 2's code review (minor item): the carried ids now ride every later fold
(`flow.py:2352-2355`, `carried` at `:2147`), so a fixup pushed onto a carried PR's branch
mid-run reaches the line, as the docs say. Test:
`test_3_a_fixup_pushed_onto_a_carried_branch_reaches_the_line_at_the_next_fold` (`:524`).
They stay out of `accepted`, so `integrate.unpublished` never reports them (brief's
requirement).

## Design decisions you should know about

- **The check lives inside `integrate.fold`, under its lock.** It is enabled by a new `vouch=`
  argument (`integrate.py:278`, `:445-451`) and runs after the fold's own fetch, before any
  merge or push. The carry now calls the fold in the brief's own start mode,
  `folded_this_run=None` ("continue if origin has it, else fresh",
  `integrate.py:302-304`). Attempt 2's separate `read_lines` and its `{target: tip}`
  handoff are gone, and so is the gap where a line created between the read and the fold
  got force-replaced.
- **One fold call per target in the carry** (`flow.py:915-942`). A refusal of one target
  must not lose another target's push, so each target gets its own lock scope (fold, tip and
  re-gate together). They are taken one after the other, so there is no nesting and no
  deadlock risk.
- **Every target of a finished id is checked, even one with nothing to carry.** Attempt 2
  did this too (its `find` path). A target whose finished ids are all held, but whose line
  holds their work, is refused. If that line is clean, it is kept and continued, not
  replaced (`integrate.py:383-384`, `:445-448`). That keeps "within a batch the line only
  grows" true in a re-issued run.
- **Fixes are offered only when they would clear the refusal** (`flow.py:990`). Every named
  bundle must have a fix, and the named bundles must explain every stray commit (or one is
  "may hold"). Otherwise the only advice is "delete the line and re-issue". For example, a
  rebuilt drive-set bundle's old commit can only be removed that way.
- **The merge subject is shown, never used.** The refusal line lists the first-parent
  commits that brought in the stray commits, as `sha12 "subject"`. That is how you see
  `"pdca-integrate: issue_P"` for an old version of P, which by commit cannot be tied to P's
  current branch. No decision reads a commit message.
- **Wording vs attempt 2.** The "carried … onto <line>" line is now printed only after that
  target's fold succeeded (`flow.py:938-941`). Before, "carrying" was printed and then the
  line was refused.

## Alternatives ruled out (with cost)

- **Extend attempt 2's blacklist instead.** For item 2b a blacklist needs the *old* commit
  of a re-pushed bundle, and nothing on disk has it. The two ways to get it:
  - (a) parse the fold's merge subjects. That is about 6 lines, but it breaks the module's
    "by commit, never by message" rule (#593).
  - (b) have the fold write each bundle's folded head to a new per-bundle file. That is
    about +15 lines in fold and +10 in flow, plus a new on-disk record, and lines folded
    before it existed have no record. Either way it would still be unknown → refuse.

  The whitelist is about +35 lines (`_vouch` + `_own`), needs no new state, and covers items
  1, 2a and 2b with one rule.
- **Keep the check outside the fold (attempt 2's `read_lines`).** It cost +45 lines plus the
  `_fetch` split, and left the read-to-fold gap. In-fold costs +8 lines in fold's group
  loop. Removing `read_lines` and the split also shrank the diff.
- **Item 3 via `pdca publish <id>` recovering the PR.** Publish's new-PR path always re-cuts
  the branch (`checkout -B` + a new commit + force-with-lease, `publish.py:298-320`). A
  re-publish therefore creates a *new* commit, the line's copy becomes an old version, and
  the new check rightly refuses it. Making publish skip the re-cut when the branch is
  already pushed would be about +25 lines in its step list and record write. It still would
  not find a PR the human opened by hand. The lookup is +35 lines in `merged.py` and handles
  both.
- **Not done, cosmetic code-review notes:** `merged_head` as a thin wrapper of `pr_state`.
  It prints on failure and sits on the fold's gone-branch path, so I left it alone. The
  duplicate lock block went away with `read_lines`. `_resolve_target` caching: still one
  brief parse per bundle per wave while a target is blocked (`flow.py:2218-2219`), which is
  cheap.

## Known limits (named, not fixed)

- Criterion (7) stands: a re-issued run where no driven bundle plainly `Depends on` a
  finished id carries nothing, and its first fold starts the line fresh. Docs and messages
  say so.
- A legacy `Stacks on` child S is cut from its parent P's branch, so S's own commits include
  P's. If P's PR is closed but S's is open and carried, S vouches for P's commits. S's PR
  carries them anyway.
- A split child an earlier run adopted is not a requested id. Its work on the line is not
  vouched for, so that target is refused and the advice is "delete the line". This is
  fail-closed, and named in the `_carry_finished` docstring.
- The check trusts merge commits on the first-parent chain as the fold's own. An outside
  party could imitate one (stated in the `fold` docstring).
- With `gh` broken, every finished id with a branch is unreadable. If the line holds them,
  the target is refused with "fix what kept … from being read".
- Behavior change to know about: a carried PR closed with its branch deleted *during* the
  run now stops the run at the next in-run fold (`_gone_branch`: not merged → raise),
  exactly as for an accepted in-run bundle. Before, it was not re-folded, so nobody noticed.
- `merged.is_merged` still has no `OSError` guard (pre-existing, child-2's area).

## Self-refutation (forced)

- **(a) Genuine red? Yes.** I ran the project's C4 runner (`engine/scripts/run-verify.sh`,
  which reverts only the production hunks) on the final `patch.diff`. Green: 31/31 new tests
  and 46/46 in `test_integrate_stack_bases`. Red: `FAILED (failures=26)` of the 31 new tests
  (assertion failures, no import errors), plus the 2 updated wording tests. The 5 that pass
  on both legs are the "unchanged" guards, which must: `test_5_an_empty_patch…`,
  `test_5_a_missing_patch…`, `test_7_no_dependency…`, `test_7_stacks_on_and_depends_on_merged…`
  and `test_7_no_publish_and_merge_mode…`. Verdict: `PDCA-EVIDENCE: C4 PASS`.

  I also ran the new tests against **attempt 2's production code**. I swapped hunks with
  `git apply` (no stash, nothing written to the object store) and restored; `git diff | cmp`
  against `patch.diff` matched. 11 of 31 fail there:
  - 7 on behavior: item 1 (C3 case), items 2a and 2b, the three item-3 cases, and the fixup
    case;
  - 1 on outcome: the carried-head case. The old code also failed closed there, but by
    stopping the whole run instead of refusing the target and naming P;
  - 3 on wording only: attempt 2 printed "it already holds", the tests read "it holds".
- **(b) Production path? Yes.** The tests drive the real `flow._drive_and_act` with
  `batch=[…]`, the shape `flow_ids` passes. Real code inside: `_runnable`,
  `_carry_finished`, `_fold_and_regate`, `_say_refused`, `_point_at_integration`, and
  `integrate.fold` with `_vouch`/`_own`/`holds` against real git (a bare `origin`). Also
  real: `integ_lock` (wrapped only to log), `pushed_tip`, `merged.pr_state`, `merged_head`
  and `is_merged`, `gates.run_integration` running a real repo-scoped gate command, and
  `publish.publish` (`open_pr=False`). Stubbed: `flow._drive_wave` (build/sign-off),
  `publish.draft_texts`, `publish._warn_if_squash_only`, and `gh` itself, answered at
  `merged`'s `subprocess` boundary for both `gh pr view` and `gh pr list`.
- **(c) Fixture includes the fault? Yes.**
  - P is only in `batch`, never in the drive set, just as `flow_ids` skips it.
  - The earlier run's line is made by the real fold under the same batch key.
  - C3 case: a fixup is pushed from a second clone and the branch deleted, and the test
    asserts this clone never has the fixup (`cat-file -e` fails).
  - Rebuilt case: X's patch, gates and SUMMARY are really archived, so it is PLANNED and in
    the drive set while its old branch is on the line.
  - Re-push case: a non-descendant commit is really force-pushed to `fix/P`.
  - Empty-`pr_url` cases: the record has `"pr_url": ""`, and `gh pr list` answers include
    another fork's same-named branch.
  - Squash case: P really is squash-merged into `main` and its branch deleted.

## Commands run (the project's runners, each under `timeout`)

- C4: `PDCA_BUNDLE=… PDCA_WORKTREE=… ./engine/scripts/run-verify.sh` → `C4 PASS` (final
  `patch.diff`).
- T3: `PDCA_WORKTREE=… ./engine/scripts/run-suite.sh` → root suite OK (24), driver suite OK
  (2356, 2 skipped).
- T2: `./engine/scripts/run-docs-check.sh` → docs lint clean, site render + link audit clean;
  `engine/scripts/run-host-ci.sh` from the worktree → clean.
- Commit-readiness: the target has no formatter, linter config or installed hooks (no
  `.pre-commit-config.yaml`, no `core.hooksPath`, no non-sample hooks, no ruff/black/flake8
  config; CI runs only the docs checkers and the root render suite). I parsed every touched
  `.py` with `ast.parse(feature_version=(3, 10)/(3, 11))` (requires-python is `>=3.11`): OK.
  No unused imports (ast scan), added Python lines are ≤ 96 columns, and `git diff --check`
  is clean. The DCO sign-off is added by publish (`git commit -s`).
- Patch size: 125,731 bytes = 122.8 KiB, under the instance's `patch_kb = 125`
  (`size_signal` divides by 1024). Most of it is the test file (992 lines, 31 tests).

## Housekeeping I owe you

- Scratch files left in the worktree, untracked and not in `patch.diff`, not deleted (no
  `rm`): `.t3-646.log`, `.c4-646.log`, `.v2-vs-new-646.log` at the worktree root, and
  `template/tests/_peek_646.py` (a message-printing helper; `unittest discover`'s `test*.py`
  pattern skips it).
- The new test file is marked intent-to-add (`git add -N`) in the worktree's index, so
  `git diff` includes it.
- The bundle copy of the test is at `results/issue_646/template/tests/test_flow_resume_stack_prereqs.py`
  (identical to the worktree file, checked with `cmp`).

No external dependency was missing.
