# Build notes — issue_749, iteration 5 (hunk-level tie in one frame)

Target: eduralph/pdca-harness. Built on the run's line `pdca-integration/main-r547f8028520f`
at `2d18208` (#738, #747, #748 folded; the worktree HEAD). "Tip" anchors are on `2d18208`.
"Patched" anchors are on that tree with this `patch.diff` applied. Starting point: iteration
4's `patch.diff`, applied cleanly to the clean worktree. `patch.diff` is `git diff` against
`HEAD` (`2d18208`), written from a scratch git index built from `HEAD` (the real index was
not touched); `git apply --check -R` confirms it is exactly the worktree's change.

Against iteration 4, `flow.py` and `test_flow_cross_wave_fold_holds.py` are byte-identical
(checked with `cmp`). Only `integrate.py` and the stranded test file change.

## What changed, and why

The brief replaces iteration 4's file-name tie (`not set(files) - set(after)`, iteration-4
patched `integrate.py:2000`) with a line-set rule in one frame: the lines of the folded
branch's own files at stake in its clash with the partner, before and after the partner is
rebuilt on the base the branch holds. The move is part of the clash exactly when
`after < before` (strict subset).

**`integrate.py`** (patched anchors)

- `_held_by_move`'s tie loop, `:2244-2255`. Each of the two trials passes a set to `_trial`
  (`stake=before`, `stake=after`), and the test is `not after < before` (`:2253`). Everything
  else in the loop is iteration 4's: the head must be the merge that fails in the first trial
  (`at != len(lead)`), the second trial either merges or fails on the head, and the stranded /
  past split, `_pinned` / `_explains` acceptance and the rest of `_held_by_move` are unchanged.
- `_trial` (tip `:2079`, patched `:2522`) gets a keyword `stake`. Only the last rev's merge
  gets it (`:2552`): the tie trials merge `lead` first, and a lead rev that conflicts already
  means "not judged", so its blocks are never read.
- `_merge` (tip `:1708`, patched `:1740`) gets a keyword `stake` that only `_trial` passes.
  With it, the merge runs as `git -c merge.conflictStyle=diff3 -c rerere.enabled=false merge
  …` (`:1759-1761`), and on a conflict `stake` gets `_at_stake(wt)` before `_reset_tree`
  (a `try/finally`, so the tree is reset even when `_at_stake` raises). Without `stake`
  (every fold merge, every other trial) the git command is byte-identical to the tip's
  `:1719` line and the steps after it are the same.
- `_at_stake` (`:1775`): reads the conflicted index (`git ls-files -u -z`), and per file:
  - stage 3 is the folded branch's own version: the frame. Stage 1 is the base.
  - both sides have the file (stages 2 and 3): parse git's diff3 blocks from the working-tree
    file (`_diff3_blocks`, `:1885`), take the hunks of `git diff -U0` from stage 1 to stage 3
    (`_own_hunks`, `:1864`), and place each block on a run of hunks (`_placed`, `:1913`). A
    line is at stake when a block holds the hunk that changed it. No stage 1 (both sides added
    the file): the base is empty, as git merges it, so the one hunk is the whole file
    (`:1818`).
  - one side deleted the file (no blocks at all): the whole file is the clash. If the branch
    deleted it, the place it left, `(path, 0, True)` (`:1811`); if the other side did, every
    line the branch changed.
  - a file it cannot place raises `_Unplaced` (`:128`): no diff3 blocks (binary, custom merge
    driver), not a plain file (symlink, submodule), unreadable, blocks that do not fit the
    hunks in exactly one way, or no line at stake.
  - Positions are `(path, line, False)` for a line of the branch's version (from 1) and
    `(path, n, True)` for the place after its line `n` where it deleted lines ("a head-side
    deletion counts as the position it leaves").
- `_own_hunks` runs `git diff -U0 --no-color --no-ext-diff --no-textconv
  --no-indent-heuristic --inter-hunk-context=0 --diff-algorithm=<algo>` on the two blob ids.
  `<algo>` is `diff.algorithm` from the config, else `histogram`. Why each flag:
  - `git merge` uses histogram unless `diff.algorithm` is set (git-merge(1): "ort defaults to
    diff-algorithm=histogram"). I confirmed with git 2.53 that `git merge` also honors
    `diff.algorithm` when it is set: a case where myers and histogram disagree conflicts with
    a one-line base side by default and a two-line base side under `-c diff.algorithm=myers`
    (`.cache/scratch/probe3.py`). `git diff` alone defaults to myers, so it must be told.
  - `git merge` does not use the indent heuristic: in a case where the heuristic moves an
    insertion away from the other side's change, the merge still conflicted
    (`.cache/scratch/probe3.py`). `git diff` uses it by default, so it is switched off.
  - `--inter-hunk-context=0` and `--no-color` stop a user's `diff.interHunkContext` or
    `color.ui=always` from joining hunks or breaking the header parse.
- `_placed` / `_one_set` (`:1913`, `:1958`): blocks take runs of hunks in file order. For a
  run, the block's head side must equal the branch's text at the run's positions and its base
  side the base's text there, allowing unchanged lines before and after (where the other
  side's change reaches further). The extension is why "checked at those positions only"
  needs more than the hunk lines themselves: in case (7)'s second trial the block's head side
  is `W's line 7, main's line 8` but the branch changed only line 7. The neighbouring hunks
  must be outside the block, and the line counts must balance. Only hunk positions are
  candidates, so repeated text elsewhere is never matched. If two placements hold different
  hunks, only placements with an unchanged base line between the block and the hunks outside
  it count, since git joins a change that touches a conflict to it. If it is still not
  exactly one, the result is None and the file is unplaced.
- `fold` (tip `:663`, patched `:688-705`): `_held_by_line` lets `_Unplaced` through (`:2134`).
  `fold` catches it, rebinds `exc` to a `_Conflict` whose message adds "the conflict in X
  could not be placed on issue_W's own lines (why), so the fold did not judge whether the
  moved base is part of the clash", and the existing re-raise becomes `raise exc` (`:705`).
  The flow prints it on the stop line (`flow.py:3170`, unchanged). Real line from the binary
  test: `flow: wave 1 did not integrate (issue_W's branch origin/fix/W does not merge cleanly
  onto pdca-integration/main-r823c3464b38c (conflicts in logo.bin) — an undeclared cross-wave
  overlap; declare the conflict / re-order, then re-run; the conflict in logo.bin could not be
  placed on issue_W's own lines (no diff3 conflict blocks in it: a binary file, or one a
  custom merge driver merges), so the fold did not judge whether the moved base is part of
  the clash); STOPPING — later waves not run.`
- Docstrings that described the file rule now describe the line rule: `fold`'s (`:503-515`),
  `BaseMove`'s (`:2046`, "trial-checked, never read off the files" → "judged on the lines at
  stake in trial merges … however they are spread over files"), `_held_by_move`'s tie bullet
  and cost note, `_held_by_line`'s last paragraph.

**Unchanged, and what they feed** (anchors the brief asks for)

- `_own_change` (tip `:1887`, patched `:2330`): its merge bases (`lead`) still go before the
  head in both tie trials, so the head's merge is the one whose blocks are read.
- `_explains` (tip `:1859`, patched `:2300`) and `_pinned` judge the rest of the clash on the
  rebuilt line, unchanged. Only the tie result they see is new.
- `_clash` (tip `:1969`): says "base" for a head that does not merge onto the base alone, so
  `_held_by_move` never runs for case (4)'s base clash.
- `_built_on` (tip `:2044`): says what S (`Stacks on: R`) was built on, which holds A. That is
  why case (9) avoids a stacked bundle (below).
- `flow.py` is byte-identical to iteration 4. `_moved_hold` (patched `flow.py:1609`) words a
  moved hold. `_announce_conflict_holds` and `_report_conflict_holds` (tip `flow.py:1569`,
  `:1593`) print it. The stranded-plus-own lines of (5), (6), (7) and (10) use the wording
  the flipped test already pins, and the file list is the only part that depends on the
  files, which is why (6)'s masked lines can be compared word for word.

**`test_flow_cross_wave_stranded_holds.py`**

- `_run` (`:217`) now keeps the `held_out` and `moved` dicts the flow passes to the fold
  (`:230`), so case (6) can compare partners and who can act. It reads them from the fold's
  keyword arguments; nothing imports a symbol the fix adds.
- New helpers: `_diff3` (`:350`, plain git in the scratch clone, a fixture fact),
  `_moved_run` (`:835`, case (1)'s fixture on other files), `_one_file_run`, `_two_file_run`,
  `_stranded_and_own` (the stranded-plus-own assertions), `_steps_fold_w` (the two advised
  steps with real git).
- New tests: (5) `:915`, (6) `:927`, (7) `:947`, (8) `:965`, (8b) `:983`, (9) `:1003`,
  (10) `:1043`, the deleted-file test `:1062`, the binary (cannot place) test `:1096`.
- Module docstring updated (rule, cases, guards).

## Brief case → what happens (tip `2d18208` / iteration 4 / this patch)

Observed with wrappers around `integrate._at_stake` and `integrate._held_by_move` that call
through (`.cache/scratch/observe.py`), plus the C4 runs below.

| Case | Tip | Iteration 4 | This patch (sets: before → after) |
|---|---|---|---|
| (5) `:915` | STOPPING | STOPPING | {2, 8} → {2}: stranded + own hold |
| (6) `:927` | STOPPING both | one-file STOPPING, twin held | both held, same holds / partners / BaseMove / rc / masked lines |
| (7) `:947` | STOPPING | STOPPING | {7, 8} → {7} (one block both times): stranded + own hold |
| (8) `:965` | STOPPING | STOPPING | {2} → {2, 5}: not judged, STOPPING |
| (8b) `:983` | STOPPING | STOPPING | {2, 8} → {2, 5}: not judged, STOPPING |
| (9) `:1003` | ordinary hold | ordinary hold | ordinary hold; `_held_by_move` never called |
| (10) `:1043` | STOPPING | STOPPING | {5, 11} → {5}: stranded + own hold |
| deleted file `:1062` | STOPPING | held | {(f.txt, 0, gap)} → {} and {(f.txt, 1)} → {}: held |
| binary `:1096` | STOPPING (generic) | held | `_Unplaced`: STOPPING, file named |
| iteration 4's cases | as iteration 4 | as built | unchanged, all pass |

**Case (8) reaches the "not judged" branch.** The observed run shows `_held_by_move(issue_W)`
running both tie trials with `before = {(shared.txt, 2)}` and `after = {(shared.txt, 2),
(shared.txt, 5)}`, then returning None. The fold re-raises, and the run prints `STOPPING`.

**Case (9): the outcome, recorded as the brief asks.** W is held for an ordinary overlap with
A. The hold line is "its change conflicts with issue_A's, already on the line from an earlier
wave (conflicts in shared.txt)", and the end line gives W's owner the `Conflicts with: A`
proposal. There is no BaseMove, no "rebuild issue_A's branch" advice, holds `{W: conflict}`,
and exit 3. The run is the same on the tip (C4 red leg: (9) passes) and on iteration 4's code
(file-rule run: (9) passes).
The flow never reaches the tie for this shape. A only changes line 2, so it still merges onto
main. #747's rule names it on the base as it is (`_pinned`, patched `:2141`), and
`_held_by_move` is not called. If the tie trials ran, the sets would be equal: production
`_trial(stake=…)` on this shape in a scratch repo gives {2} and {2}, which is not judged
(`.cache/scratch/stake_probe.py`). Equal sets are only reached in the flow when the branch
edits a moved spot further (probe: {8} → {8}).
Fixture choice: (9) does not use `_moved_run`. That fixture has S `Stacks on: R`, cut from the
line, so S holds A. #747's `_explains` then refuses to take A off the line (rule (e), tip
`:1872-1874`). `_held_by_move` sees no unfit bundle and returns None at patched `:2232`, so
the run stops on the tip, on iteration 4 and with this patch alike. The stop would come from
rule (e), not from anything about the move. I used (3a)'s shape instead (no bundle cut from
the line), so the case shows the move being ignored.

**Case (4) and the probes.** `test_flow_same_wave_conflict.py`'s base-clash guard still prints
`STOPPING` (driver suite green; `_clash` says "base", so `_held_by_move` never runs). Child-1's
flipped test stays flipped (`test_flow_cross_wave_fold_holds.py`, byte-identical to iteration
4, green; it fails on the C4 red leg as before). Both take-the-move-back-out probes and the
three-bundle probe still stop.

## Decisions beyond the brief's text

1. **A file one side deleted is placed as one whole-file block, not "cannot place".** The
   brief says a file left conflicting "without readable diff3 blocks" is unplaceable. Its
   examples are binary files and custom merge drivers, and it says the branch "covers binary
   files and custom merge drivers". A modify/delete conflict also has no blocks, but its
   content is fully known: one side has no file. The brief's own definitions (the frame is the
   branch's version of each file; "a head-side deletion counts as the position it leaves")
   place it directly.
   Following the literal text would regress iteration 4: "main deletes a file A changed, W
   holds the deletion" is a real stranded clash that iteration 4 held (the file drops out),
   and it would become a stop. It would also add a misleading "could not be placed" note to
   case (3c)'s other-file probe, whose second trial has W's deletion of x.txt.
   Cost: the 3-line `"3" not in st` branch (`:1811-1813`); the other direction uses the shared
   hunk loop. The deleted-file test (`:1062`, both directions) pins it so the reviewer can see
   it. Both directions hold on iteration 4 too (file-rule run: that test passes there).
2. **The binary test (`:1096`).** The brief says the "cannot place" branch has no case, but it
   also requires that "the stop line on stderr names the file and says its conflict could not
   be placed". A binary file reaches that branch, so I tested the stop line. This is a
   behaviour change from iteration 4, which held the binary shape (file-rule run: this test
   fails there because W is held). The brief prescribes the change: "Binary files and custom
   merge drivers fall into the named 'cannot place' stop."
3. **The tie-break among placements** (`:1946-1955`). It only applies when more than one
   placement fits. It came from a randomized stress test (below), where one case had two
   fits; one of them depended on a hunk touching the block, which git never leaves outside a
   block (it joins touching changes into the conflict). It is not applied as a hard rule,
   because git does leave a change outside a block when both sides made the same change
   (xdiff's EAGER level skips identical changes).

## What I tried and ruled out (with costs)

- **Placing by searching the branch's file for a block's text.** The brief forbids it, and
  case (10) shows it fails. W's line 5 text equals main's line 11 text and the file's line 1,
  so both blocks of the first trial would map to line 1 and the sets would look equal (not
  judged), while git's hunks put them at 5 and 11.
- **Using the other side's stage too, to settle the remaining ambiguity.** That ambiguity is
  two identical changes (same base text, same new text, room around both) where only one
  conflicts; only the other side's file can tell which. Sketch: `_diff3_blocks` also returns
  the ours side (+3 lines), `_at_stake` reads stage 2 and runs a second `_own_hunks` (+3
  lines, +1 `cat-file` and +1 `git diff` per conflicted file), and `_placed` carries each
  run's base start and requires the ours-side run to start at the same base line (about +15
  lines, with the DP keyed on (run, base start)). About 20-25 lines plus two git calls per
  file, for 3 declines in about 880 conflicting random merges with a 4-line alphabet. The
  brief also prescribes the head and base stages only. Not done: those cases stop with the
  named message, which is safe.
- **Raising the amended `_Conflict` straight from the `except _Unplaced` handler in `fold`**
  (3 lines) instead of rebinding `exc` and changing `raise` to `raise exc` (the same 3 lines
  plus 1 changed line). The direct raise would skip `fold`'s `skipped` path for a caller that
  passes both `held_out` and `skipped`. No caller does: `flow._fold_lines` passes its
  arguments through (`flow.py:1208-1213`), the in-run folds pass `held_out` only and the carry
  `skipped` only. Rebinding keeps one exit path for 1 extra changed line.
- **Pinning `diff.algorithm` in the trial merge** instead of reading it. The brief limits the
  trial pins to the conflict style and rerere. Pinning the algorithm would also make the trial
  merge differ from the real fold merge for a user who sets `diff.algorithm`. Reading it costs
  one `git config --get` per conflicting tie trial.
- **iteration 1's file-name intersection and iteration 4's file drop-out test.** Both are
  replaced. Case (9) keeps iteration 1's counterexample (unrelated move → not tied), and all
  of iteration 4's guards pass. Parent #739's `_rebuilt` squash is not back: the rebuild is
  still `_trial(held, [its], wins=0, made=…)`, a merge with the partner's side winning
  (unchanged `:2236-2241`).

## Known limits (each stops the run with the named message; none gives a wrong step)

- **Identical changes at two places, one conflicting.** Placement is ambiguous from the head
  and base stages alone. Seen in 3 of about 880 conflicting random merges built from a 4-line
  alphabet (`.cache/scratch/stress.py`); none in the 150 conflicting merges from a 7-line one.
- **Binary files, custom merge drivers, a custom `conflict-marker-size`, symlink or submodule
  conflicts.** Cannot place, so a named stop. Iteration 4 held the binary shape.
- **An older git whose `git merge` ignores `diff.algorithm`**, with that setting on: the diff
  may align differently from the merge, placement then fails, and the run stops with the named
  message.
- **A clash whose conflicted path differs between the two trials** (a rename one side made):
  the sets do not compare, so it is not judged and the run stops (generic message).
- **Same-wave stranded partner** (#756), the `past` hold's acceptance, case (3c)'s silence
  about A's rebuild, and the (3a)/(3c) overlap gap (#757): out of scope, unchanged.

## Stress test of the placement (not in the patch)

`.cache/scratch/stress.py` builds random three-way merges with real `git merge` (diff3) from
alphabets full of repeated lines (`}`, blank, `a`, `x`), runs production `_at_stake`, and
compares it with an independent method. The cross-check replaces each block with its head
side, diffs the branch's file against that, and maps each head side back through the diff's
hunks. Results:
- 7-line alphabet, 300 merges: 150 conflicting, all agree.
- 4-line alphabet, seeds 2-6, 400 merges each: about 880 conflicting, 0 disagreements, 3
  production declines. All three are the identical-change ambiguity above.
- Before the tie-break there was one more decline (seed 2), now placed and agreeing.

## Refute-your-own-test (forced)

- **(a) Genuine red?** Yes, checked four ways:
  - C4 (`engine/scripts/run-verify.sh`, `PDCA_BUNDLE` = this bundle, under `timeout`) reverts
    the production hunks (back to tip `2d18208`): `PDCA-EVIDENCE: C4 PASS — red without the
    fix, green with it`. Red leg: 15 failures in the stranded file and 1 in child-1's file (the
    flipped test). Every hold case fails on `'did not integrate' unexpectedly found in "flow:
    wave 1 did not integrate (…) STOPPING"`. That covers (1), (3a), (3b), the (3c) overlap
    case, (3d), both partner tests, the joint case, (5), (6), (7), (10) and the deleted-file
    test. The binary test fails because the stop line lacks "could not be placed". Green both
    ways: (2), both take-the-move-back-out probes, the three-bundle probe, (8), (8b), (9).
    Log: `.cache/c4-final.log`.
  - With only iteration 4's file rule (iteration 4's `integrate.py` swapped in, my tests kept;
    one C4 run, then restored and checked with `cmp`): the green leg fails on exactly (5),
    (6), (7) and (10), each `wave 1 did not integrate (issue_W's branch … (conflicts in
    shared.txt)) … STOPPING`, plus the binary test (iteration 4 holds W). Everything else
    passes, (8), (8b), (9) and the deleted-file test included. Log:
    `.cache/mutation-file-rule.log`.
  - With the rule weakened to "some line left" (`not before - after`; one C4 run, then
    restored and checked with `cmp`): only (8b) fails. W is held ("issue_A's branch … does not
    merge cleanly … and issue_W's own change also conflicts …") instead of `STOPPING`. (8)
    still passes, since {2} − {2, 5} is empty. Log: `.cache/mutation-weaker.log`.
- **(b) Production path?** Yes. Each test calls `flow._drive_and_act`, which runs the real
  `integrate.fold` → `_held_by_line` → `_held_by_move` → `_trial(stake=…)` → `_merge` →
  `_at_stake`, on real git (bare origin, primary checkout, scratch clone), with real base
  builds and the real `cli._results_rc`. The observed run shows the real sets being computed.
  Only the build leaf, publish's branch cut and `gh` are stubbed, as in child-1's and
  child-2's suites. The test imports modules only (`cli, flow, integrate, publish, state`), so
  the red leg loads and runs. The stress test also calls production `_at_stake`.
- **(c) Fixture includes the fault?** Yes. `main` really moves on origin after the first fold.
  W's head really holds the move (ancestry asserted in `_moved_run`), A really fails onto main
  (`_merges(…, "A") == 0`), and W really merges onto main alone. Case (7)'s single block over
  lines 7-8 is checked in both trials with plain git (`_diff3`). (5), (7) and (10) take the
  advised steps with real git: A rebuilt on main does not fold W alone, and with W rebuilt on
  that, the line takes every bundle. The binary file has a NUL byte, and the deletions are a
  real `git rm` on main and a real deletion on A's branch.

## Gates run here

- C4 on this bundle's `patch.diff`: **PASS** (green 9 + 21 OK; red 1 + 15 failures). Log:
  `.cache/c4-final.log` in the worktree.
- T3 `engine/scripts/run-suite.sh` on the final tree (under `timeout`): `PDCA-EVIDENCE: root
  suite OK, driver suite OK`. Root suite: 24 tests OK. Driver suite: 2646 tests OK (2
  skipped; iteration 4 had 2637, and the 9 more are this iteration's new tests). That
  includes child-1's and child-2's suites, the same-wave suite (case (4)'s base-clash stop)
  and both files of this patch. Log: `.cache/t3-final.log`.
- Mutation runs: `.cache/mutation-file-rule.log`, `.cache/mutation-weaker.log`.
- Observed sets: `.cache/scratch/observe.py`. Probes: `.cache/scratch/probe*.py`,
  `.cache/scratch/stake_probe.py`. Stress test: `.cache/scratch/stress.py`.

## Commit-readiness

pdca-harness has no formatter, linter or commit hook: no `.pre-commit-config.yaml`, no
ruff/black/flake8 settings (`template/pyproject.toml.jinja` has only
`[tool.setuptools.packages.find]`), no workflow running one, only `.sample` hooks and no
`core.hooksPath`. CONTRIBUTING.md asks for a DCO sign-off (publish adds it). `git diff
--check` is clean, `py_compile` passes on all four files, and no added line is over 100
columns.

## Scratch left in the worktree (not in the patch)

All under `.cache/` (git-ignored, `.gitignore:11`):
- scratch indexes `dev-index`, `mut-index`, `v4-index`
- `dev-bundle/`, `mut-file-rule/`, `mut-weaker/` (the patches the C4 runs read)
- `v4/` (iteration 4's files, extracted for the file-rule run) and `integrate.py.mine` (the
  copy each mutation was restored from)
- `scratch/` (probes, stress test, observe script, temp repos)
- logs `c4-dev.log`, `c4.log`, `c4-final.log`, `mutation-file-rule.log`,
  `mutation-weaker.log`, `t3.log`, `t3-final.log`

Test runs also wrote ignored `__pycache__/` under `template/`. Left for the harness to
reclaim; nothing was removed.
