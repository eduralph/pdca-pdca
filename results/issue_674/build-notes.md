# Build notes — issue 674 / same-wave-conflict-holds-one-bundle-not-the-run (iteration 3)

## Base

The worktree (`$PDCA_WORKTREE`) is the stack base `pdca-integration/main-r8bf6d15b2de3` at
`420f8b4` (the bundle's `stack-base-tip`). It already holds #605, #629, #633, #651 and #658
on top of the brief's `41210bc`, so line numbers differ from the brief's. A "base" line
below is on `420f8b4`; an "after" line is in the patched worktree. `patch.diff` applies to
`420f8b4` (I regenerated it from the tree and checked the tree byte-for-byte against it
with `git diff | cmp - patch.diff`). It does not apply to plain `origin/main`, because
#633's `carried=` lines are part of its context.

I started from iteration 2's patch (it still applied cleanly) and changed only what the
carry-forward asks for, plus the comments and docs that state the rule.

## The finding, and what I changed

The finding: when no single kept bundle conflicts with `head` on its own, `_held_by` fell
back to naming every kept bundle. That fallback also fired when the line had changed after
`pre` for a reason that is not a kept bundle. A same-wave bundle whose PR merged right after
publish, with its branch deleted, has `head is None`. It goes through `_gone_branch` →
`_take_in_base` (after `integrate.py:687`, `:699`; base `:645`, `:657`), which merges the
base into the line, but it is never added to `kept` (after `:541-544`). A later same-wave
bundle that conflicts only with that new base content then merged cleanly onto `pre` and
onto `pre` + each kept bundle, so the fallback held it and blamed an innocent partner, with
a wrong `Conflicts with:` proposal. Before #674 the run stopped there.

I reproduced it before fixing: with iteration 2's production code and the new test, the
new case fails like this (run through `run-verify.sh`, see "Red → green"):

```
FAIL: test_a_conflict_only_with_a_base_taken_in_mid_wave_still_stops_the_run
AssertionError: "wave 1 did not integrate (issue_22's branch origin/fix/22 does not merge cleanly" not found in
"… integrate: issue_21's branch origin/fix/21 is gone and its PR merged at c5a9b00daa35 … through origin/main.
flow: issue_22 held out of the integration fold — its change conflicts with issue_20's, merged before it in the
same wave 1 (conflicts in shared.txt) …
flow: issue_22 was held … Proposed, for you to confirm: declare `Conflicts with: 20` in issue_22's brief …"
```

So 20 is blamed and a wrong `Conflicts with: 20` is proposed, exactly as the finding says.

The fix, in `template/src/pdca_harness/integrate.py`:

- `_held_by` (after `:884-908`) now decides the hold on `pre` plus the kept bundles, on every
  path, not only before the fallback. It returns `(partners, paths)` or `None`:
  1. `head` must merge cleanly onto `pre` (unchanged: otherwise it is an earlier-wave
     conflict, and the fold stops).
  2. New: `head` must conflict when merged onto `pre` + all kept heads, in order
     (`_trial(wt, branch, pre, [*kept_heads, head])` returns index `len(kept)`). If it does
     not, its conflict on the real line is with something else the line took in after
     `pre` (the base, for a gone branch), so `None`, and the fold raises the original
     `_Conflict`, as it did before #674. This is the guard the reviewer proposed
     (`_trial(...) == len(kept)`), applied before the partner search instead of only before
     the fallback.
  3. Partners as before: each kept bundle that conflicts with `head` on its own; if none
     does, all of them (the conflict needs several together).
  4. New: `paths` are the files left conflicting by the trial in step 2, not the files of
     the failed merge onto the real line.
- `_trial` (after `:911-941`) returns `(index, paths)` instead of just the index:
  `return i, conflicts` (after `:935`) and `return None, []` (after `:936`).
- `fold` (after `:533-535`) stores what `_held_by` returns: `clash = _held_by(...)`,
  `held_out[d.name] = clash`. The variable is `clash`, not `held`, because `held` already
  names the lock result in `fold` (base `:451`).
- `_Conflict` (after `:93-96`) loses its `paths` attribute and `__init__`, which nothing
  reads any more. It stays as a marker class, so the fold still tells a textual conflict
  from any other failed merge. `_merge_published` raises it with the message only (after
  `:628-631`, base `:586-589`); the message text is unchanged.
- Docstrings say the rule as the code now applies it: the module docstring (after
  `:53-56`), `fold`'s `held_out` paragraph (after `:392-405`), `_held_by`, `_trial`.

Wording only, in `template/src/pdca_harness/flow.py`: the `_fold_lines` docstring (after
`:851-854`) and the comment above the in-run fold (after `:2445-2448`) said "conflicts only
with one of its own wave merged before it". They now say "conflicts with ones of its own
wave merged before it (and not with the line as the wave found it)". No flow logic changed
in this iteration.

Docs:

- `docs/07-crosscutting.md` (after `:698-709`): the hold rule is stated as "merges cleanly
  onto the line as the wave found it, but not on top of the ones of its wave merged before
  it", and the closing sentence adds that a branch that conflicts only with a newer base
  the fold merged in during the wave still stops the run.
- `template/PCDA/quality-cycle/09-parallel-lanes.md:69`: same rule, same words; "named with
  the bundle it conflicts with" → "named with the bundles it conflicts with".

## Why this shape, and what I ruled out

The Invariant to restore says a bundle is held "exactly when it does not merge cleanly onto
the line plus the same-wave bundles already kept, yet does merge cleanly onto the line
without them". `pre` is "the line" (the line the wave found) and `pre` + kept heads is "the
line plus the same-wave bundles already kept". Step 1 and step 2 above are those two
conditions, word for word, so the hold is now defined by the Invariant's own test and not
by the state of the real line.

- **The reviewer's guard, on the fallback only (about 3 more lines than iteration 2).**
  Not taken as-is, though my change contains it. On that shape, a bundle is held whenever
  one kept bundle conflicts with it alone, even if `pre` + all kept heads + `head` merges
  cleanly. That can happen only with an unusual merge history: kept bundles that replay
  onto `pre` only with the base taken in between them, or a three-way merge that is not
  monotone. When it does happen, the hold is not what the Invariant defines. Applying the
  check on every path costs one more trial per held bundle (one `checkout --detach`, then
  `len(kept) + 1` merges, then the reset) and no extra code: `_held_by`'s body is 5
  statements either way (7 lines here; 8 for the fallback-only guard, which needs an `if
  partners: return partners` before the check). The reported files would also stay those
  of the failed merge onto the real line. If the bundle conflicts with a kept bundle in `a.txt` and with the base taken in in
  `b.txt`, the report would say "conflicts with issue_20's (a.txt, b.txt)", but `b.txt` is
  not 20's. Taking `paths` from the step-2 trial fixes that. It also makes
  `_Conflict.paths` unused, so I removed it (−4 lines).
- **Replay the base taken in inside the "without them" trial (about 12 more lines).**
  This would stop a bundle that conflicts both with a kept bundle and with the base taken
  in, instead of holding it. It needs `fold` to know what `_take_in_base` merged, which
  means a return value threaded through three functions. Sketch: `_take_in_base` returns
  the base commit it merged (or None); `_gone_branch` and `_merge_published` change `->
  None` to `-> str | None` and `return` it; `fold` keeps a `took_in` list for `ours`
  bundles; `_held_by` gets `took_in` and prepends it to both trials. About 12 changed lines
  over 4 functions. Not taken, for the behaviour, not the size. In that compound case
  the named partner is real (it does conflict on `pre`), the bundle is out of the line, and
  the run goes on. That is the Invariant's "costs only the bundles that conflict … never the
  run". The base conflict shows up when the human rebuilds the bundle on a base that holds
  the partner, since that base also holds the newer content. The docs sentence is written
  to match: "conflicts **only** with a newer base … still stops the run".
- **A "the line took something in" flag that turns off holds for the rest of the fold
  (about 6 lines: read the tip before and after `_merge_published` for an `ours` bundle
  with `head is None`, set `moved` when it changed, add `and not moved` to the hold
  condition).** Not taken. It is simple and never worse than before #674, but it also
  stops the run when a bundle conflicts only with a kept bundle and the base taken in has
  nothing to do with it. The second new test case (`22` conflicts only with `20`, and main
  was taken in before it) pins that this hold still happens.
- **Name the gone bundle itself when the conflict is with its own merged work.** A
  same-wave bundle whose PR merged mid-run reaches the line only through the base, so it is
  not in `kept`, and a conflict with its work now stops the run (as before #674) instead of
  holding. Adding it to `kept` with its merged head would need the head returned from
  `_gone_branch`. Not done: the finding asks for the old stop in this case, and it needs a
  PR merged between publish and fold.

Iteration 1 and 2 reasons stand and are unchanged in the code. Short version: I reused
`fold`'s merge-in-order loop rather than `skipped=` as-is, because `skipped` swallows every
per-bundle error, including ones that must still stop, and `fold` pushes before returning.
The "merges onto the line without them" test needs `pre`, which only the loop knows. The
`Conflicts with` partners of a held bundle are held through `_runnable(conflict_held=…)`.
`git merge-tree --write-tree` (git ≥ 2.38) is not used, so **no new git feature or minimum
git version** is added. The tie-break is the fold's name order, as the brief confirms.

## The test

`template/tests/test_flow_same_wave_conflict.py` (a copy is in this bundle under
`template/tests/`). Two new cases share one setup, `_a_pr_of_the_wave_merges_before_the_fold`
(`:370-397`):

- Wave 0 is `10`. Wave 1 is `20` (line 2 of a nine-line `shared.txt`), `21` (its own file)
  and `22`, each `Depends on: 10`. `30` depends on `20`, so wave 1 folds.
- Right after `22` publishes (the wave's last), `21`'s PR is merged into main with a merge
  commit and its branch is deleted (the fixture's `_merge_pr` and `_delete`), and someone
  else changes line 8 of `shared.txt` on main (`_push_from_human`). The `gh` stub answers
  `gh pr view` for 21's PR with `MERGED` and its head, so the real `merged.merged_head`
  returns it.
- The setup asserts that the fold really took main in for 21 ("issue_21's branch
  origin/fix/21 is gone and its PR merged" on stderr), so the fault is in the fixture.

`test_a_conflict_only_with_a_base_taken_in_mid_wave_still_stops_the_run` (`:399-412`):
`22` changes line 8. Expected, and asserted: "wave 1 did not integrate (issue_22's branch
origin/fix/22 does not merge cleanly", STOPPING, no hold line for 22, no end-of-run line,
no `Conflicts with: 20`, and `30` never built. This is the finding's case.

`test_a_base_taken_in_mid_wave_does_not_stop_a_same_wave_hold` (`:414-429`): `22` changes
line 2, as `20` does. Expected, and asserted: no stop; one hold line for 22 naming
`issue_20's` and "(conflicts in shared.txt)", and not 21; `30` built on the line, which has
20 and not 22; the `Conflicts with: 20` proposal; no brief edited. This pins that the new
guard does not refuse a real same-wave hold just because the line took the base in.

Supporting test changes: `_gh_stub` (`:108-117`) answers `MERGED` for the PRs in
`self.merged_prs`, any other `OPEN` as before. `_publish_bundle` runs
`self.after_publish[<id>]` once that bundle has published (`:141`). New `setUp` fields
(`:65-66`) and the `Callable` import (`:29`). The six earlier cases are unchanged.

## Red → green (project runners)

C4, through `./engine/scripts/run-verify.sh` (from the pdca-pdca root, with
`PDCA_BUNDLE` / `PDCA_WORKTREE` set, under `timeout 900`), on the final `patch.diff`:

```
== C4 green leg: bundle test(s) with the fix applied: template/tests/test_flow_same_wave_conflict.py
Ran 8 tests in 2.230s
OK
== C4 red leg: bundle test(s) with the production change reverted
ERROR: test_a_hold_leaves_the_integration_tree_clean_on_the_line … TypeError: fold() got an unexpected keyword argument 'held_out'
FAIL: test_a_base_taken_in_mid_wave_does_not_stop_a_same_wave_hold … 'did not integrate' unexpectedly found …
  "integrate: issue_21's branch origin/fix/21 is gone and its PR merged at 334089fe19cc … through origin/main.
   flow: wave 1 did not integrate (issue_22's branch origin/fix/22 does not merge cleanly … (conflicts in shared.txt) …"
FAIL: test_a_conflicts_with_partner_of_a_held_bundle_is_held_too … 'did not integrate' unexpectedly found …
FAIL: test_a_same_wave_conflict_holds_the_later_bundle_and_the_run_goes_on … "flow: wave 0 did not integrate (issue_11's branch origin/fix/11 does not merge cleanly … (conflicts in shared.txt) …"
FAIL: test_of_a_three_way_chain_only_the_bundle_that_conflicts_is_held … 'did not integrate' unexpectedly found …
Ran 8 tests in 1.546s
FAILED (failures=4, errors=1)
PDCA-EVIDENCE: C4 PASS — red without the fix, green with it
```

On the red leg (all of #674 reverted), three cases pass, as expected: the clean-merge case
(3), the earlier-wave stop case, and the new stop case. Each one checks that the run still
stops, or holds nothing, where it did before #674. The red leg's `ERROR` is a runtime
`TypeError` inside one case, not a load failure: the module imports only modules, and all
8 cases ran.

This iteration's own red: I put iteration 2's production code back (`git apply -R
--exclude='template/tests/*'` of this patch, then `git apply --exclude='template/tests/*'`
of `iteration-v2/patch.diff`), kept the new test, and ran the same runner. Its green leg
(which here runs iteration 2's code) failed only on the new stop case, with the output
quoted in "The finding" above: `Ran 8 tests … FAILED (failures=1)`. Then I reversed both
applies and checked that the tree matches `patch.diff` byte-for-byte.

T2 through `./engine/scripts/run-docs-check.sh`: `lint_docs: OK`, `render_site: link audit
OK`.

T3 through `./engine/scripts/run-suite.sh` (both suites, under `timeout 2400`): root
suite `Ran 24 tests … OK`, driver suite `Ran 2450 tests in 60.528s … OK (skipped=2)`,
`PDCA-EVIDENCE: root suite OK, driver suite OK`. That is two more driver tests than
iteration 2 (2448), the two new cases. The full log is in this bundle as
`build-t3-suite.log`.

## Refute-your-own-test (forced)

- **(a) Genuine red? Yes, at two levels.** With all of #674 reverted (the C4 red leg), the
  cases for criteria (1), (2) and (4), the partner case and the new hold-with-base case fail
  because the run stops ("did not integrate"). With only this iteration's change reverted
  (iteration 2's code plus the new test), the new stop case fails because 22 is held and 20
  is blamed (output above). That second red is the defect the carry-forward names, so the
  new case binds this iteration's change, not just "the run goes on".
- **(b) Production path? Yes.** Both new cases call `flow._drive_and_act` with the
  publisher in `command` mode. The fold is the real `integrate.fold` → `_merge_published` →
  `_gone_branch` → `_take_in_base` for 21, then `_merge_published` → `_held_by` / `_trial`
  for 22, against real git: a bare `origin`, the primary checkout, the real integration
  worktree, real pushes. `merged.merged_head` is the real function, reading a `gh pr view`
  answer from the stub in front of `subprocess.run`. Stubbed: the build and sign-off leaves
  (`flow._drive_wave`), `publish.draft_texts`, `flow._publish_bundle` (replaced by a real
  git cut, commit and push from the recorded line tip), and `gh`. The fix changes none of
  those.
- **(c) Fixture includes the fault? Yes.** 21's PR is really merged into origin's main with
  a merge commit, and its branch is really deleted on origin, so the fold's pruning fetch
  sees it gone. The line-8 change is a real commit on origin's main. The setup asserts the
  fold's own "is gone and its PR merged … through origin/main" line, so the base was
  actually taken in mid-wave before 22 was merged. All five bundles are in the batch and
  driven; nothing is left out.

## Commit-readiness

The target has no formatter, linter config, pre-commit config or installed git hooks: no
`.pre-commit-config.yaml` or `pyproject.toml` at its root, `core.hooksPath` unset, only
`*.sample` files in hooks. Its CI runs the docs checks (green above) and the root render
suite (green in T3). No linter is installed here (no `ruff`, no `pyflakes`), so I compiled
the three changed Python files and checked them for unused imports with a short `ast` scan:
clean. Every added Python line is at most 100 columns. The only long added line is the
`09-parallel-lanes.md` paragraph, which is one Markdown line in the original too. The DCO
`Signed-off-by` belongs to the publish commit, not the patch.

## For the human

- The deferred findings in `deferred-findings.json` are not addressed here, and I did not
  act on them. The carry-forward marks them as human judgement, not build work.
- Known limit, in the docs: a same-wave bundle whose PR merges mid-run reaches the line
  through the base, so a conflict with its work stops the run as before #674, rather than
  holding the later bundle and naming it.
- Housekeeping: to generate the diff I marked the new test file intent-to-add (`git add -N`)
  in the worktree index, then put the index back (`git reset -q -- <file>`). The file is
  untracked again, as earlier iterations left it. I first pointed the T3 log at a file
  inside the worktree (`.git-suite-run.log`) by mistake; after the run I moved it into this
  bundle as `build-t3-suite.log`, so the worktree holds only the patch's files. No files
  were written outside the worktree and this bundle.
