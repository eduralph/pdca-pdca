# Build notes — issue_749, iteration 6 (the four gaps of iteration 5)

Target: eduralph/pdca-harness. Built in `$PDCA_WORKTREE` on the run's line
`pdca-integration/main-r547f8028520f` at `2d18208` (#738, #747, #748 folded). Starting point:
iteration 5's `patch.diff`, applied cleanly on the clean worktree, as the carry-forward asks.
"Tip" anchors are on `2d18208`; "patched" anchors are on that tree with this `patch.diff`
applied. `patch.diff` is `git diff --cached HEAD` from a scratch index built from `HEAD` (the
real index was not touched); `git apply --check -R patch.diff` passes on the worktree, so it
is exactly the worktree's change.

Against iteration 5, `flow.py` and `test_flow_cross_wave_fold_holds.py` are byte-identical
(checked with `cmp` against a scratch copy of iteration 5's tree). Only `integrate.py` and the
stranded test file change. The hunk/line-set strict-subset rule is kept: the test is still
`not after < before` (patched `integrate.py:2350`), and every iteration-5 test is kept with
its assertions unchanged (the only edits to old test code are three helpers, `_edit`,
`_on_main` and `_steps_fold_w`, listed under "Decisions", and the module docstring).

## The four gaps, and what changed

### 1. A deleted line keeps its key in both trials (`integrate.py:1871-1874`)

Iteration 5 keyed a hunk `(a, b, c, d)` of the branch's diff as its lines `c+1..c+d`, or as
the place `c` only when it put no line there (`d == 0`). The two trials diff the branch from
different bases (the old base, then the base the branch holds), so the same deletion was
keyed one way in one trial and another way in the other. The adversary's shapes, observed
with real git through production `_trial(stake=…)` (scratch probe `.cache/s6/shapes.py`):

- (a) W's own deletion beside the move: before `{(7, line)}`, after `{(7, place)}`. Never
  comparable: STOPPING. Its two-file twin held.
- (b) the move is a deletion: before `{(7, line)}`, after `{(7, line)}`. Equal: STOPPING.
  Its twin held.

Fix: the stake is now a `collections.Counter`, and a hunk that drops `b` base lines puts
count `b` on every place from before its first line to after its last
(`(path, n, True)` for `n` in `c..c+d`), as well as its lines (`(path, n, False)`, count 1).
Git's hunk header does not say where among the hunk's lines a dropped line sat, so it is
counted at each place it could be. `after < before` is then Counter's multiset inclusion
(Python 3.10+; the package needs 3.11, `template/pyproject.toml.jinja:10`): every line and
every drop still at stake was at stake, and something left. This is the same as a plain set
of keys `(path, place, k)` for `k = 1..b`, held as counts so a big hunk costs O(d) entries,
not O(b·d).

Observed in the real flow (wrapper around `integrate._trial`, scratch
`.cache/s6/observe_test.py`, printing the Counter each stake trial filled):

| Case (test) | before | after | result |
|---|---|---|---|
| (a) one file `:1171` | g6:2, line 7, g7:2 | g7:1 | stranded + own |
| (a) twin | a.txt line 1, g7:1 | g7:1 | stranded + own |
| (b) one file `:1201` | g6:2, line 7, g7:2 | g6:1, line 7, g7:1 | stranded + own |
| (b) twin | a.txt deleted, g7:1, line 8, g8:1 | g7:1, line 8, g8:1 | stranded + own |
| Z one file `:1228` | g6:1, line 7, g7:1 | g6:1 | stranded + own |
| Z twin | a.txt line 1, g6:1 | g6:1 | stranded + own |

(`gN:k`: k dropped lines at the place after line N.) Checked against (7), (8), (8b) as the
carry-forward asks: (7) is g6:2, 7, g7:2, 8, g8:2 → g6:1, 7, g7:1 (held), (8) is {2} →
{2, 5} plus their drops (stop), (8b) is {2, 8} → {2, 5} plus drops (stop). All three
unchanged in outcome.

The new tests run each one-file shape beside its two-file twin through `_twins_hold_alike`
(`:1136`), which asserts the stranded-plus-own hold for both, takes the two advised steps
with real git (`_steps_fold_w`), and compares holds, partners, `BaseMove`, exit code and the
masked hold and end-of-run lines, as case (6) does. `_one_block` (`:1161`) checks the fixture
with plain git: one block, with the exact base and W sides, before and after A's rebuild.

The Z test is beyond the carry-forward's two shapes. I added it because nothing else pins
how a hunk counts its drops (see "Decisions" below): with only (a) and (b), counting only
the net drop (`b - d`) passes every test.

### 2. A test that reaches the equal-stakes stop (`:1255`)

The adversary's shape: A changes lines 2 and 8, main changes line 8, W on that main changes
line 2 and takes A's line 8. Observed: `_held_by_move` runs both stake trials, before and
after are both `{line 2, g1:1, g2:1}`, it returns None, and the run prints `STOPPING` with no
"rebuild issue_A's branch" advice. The test asserts that (`_stopped(1, "W")`), plus the
fixture facts: A does not merge onto main, and one block at line 2 in both trials.

C4 mutation run, `<` → `<=` at `integrate.py:2350`: the green leg fails on this test alone,
W held with "rebuild issue_A's branch on the new origin/main" (log `.cache/s6/mut-le.log`).

### 3. A line dropped twice is placed (`integrate.py:1982-1998`, `:2038`)

The adversary's shape `a1 } a3 } a5 } a7 a8 a9`: W drops both `}` (lines 4 and 6), A changed
line 4, and git puts only line 4's drop in a block. From W's side alone the two drops are
the same text at two places, so `_placed` found two fits and the file was "unplaced".

Fix, as the carry-forward suggests: the other side's stage. `_conflicted` (`:1780`) keeps
all three stages, `_diff3_blocks` (`:1952`) now returns each block's other side too, and
`_at_stake` diffs stage 1 → stage 2 the same way it diffs stage 1 → stage 3 (`_side_hunks`,
`:1878`). A candidate placement must also satisfy `_side(other, there, t, len(bs)) == ts`
(`:2038`): the other side has a hunk inside the block's base lines, none crossing either end,
and its text there is the block's other side. Git makes a conflict block only of changes on
both sides that overlap or touch, so the true placement always passes; the other `}` has no
change of A's near it, so it fails. The test (`:1277`) checks git's own diff3 output (two
blocks, line 6's drop merged cleanly), then the hold and both steps.

Stress test (scratch `.cache/s6/stress.py`, not shipped): random three-way merges from
alphabets of 3, 4 or 7 repeated lines (`}`, blank, `a`, `x`, …), merged by real `git merge`
with diff3. The ground truth is a scratch re-implementation of xdiff's `xdl_do_merge`
change combining (EAGER level, which git uses for diff3), fed git's own -U0 hunks; its
blocks are first checked equal to the blocks git wrote, which validates both the
re-implementation and the hunks. Results over 16 runs (6,300 merges: 4,379 conflicting,
1,921 clean; files of 3-25 lines, 1-8 edits of 1-3 lines per side): the re-implementation
matched git's blocks every time; the new placement agreed with the ground truth on all 4,379
and declined none; iteration 5's placement (kept in the script for comparison) declined 18,
the repeated-drop ambiguity, and never disagreed. `_at_stake` ran end to end on every one.

### 4. The conflict-marker size is honoured (`integrate.py:1888-1908`, `:1952-1979`)

`_diff3_blocks` takes the marker size; `_marker_sizes` reads `conflict-marker-size` for all
conflicted paths in one `git check-attr -z --stdin` call, parsed as git's `ll_merge` does
(`atoi`, then 7 for anything not above 0). Which attributes: I checked with real git
(`.cache/s6/attr_probe.sh`), putting `conflict-marker-size=9` only on ours, only on theirs,
or only in the base. `git merge` used 9, 7 and 9: it reads the side merged onto. A plain
`git check-attr` after the merge (worktree) and `--cached` both say 9 when only theirs has
it, which is wrong; `--source HEAD` is right in all three, and so is a plain `check-attr`
once the tree is reset to that side. So `_merge` now reads the conflicted index and git's
text before the reset (`_conflicted`, `:1772`) and computes the stake after it (`:1775-1776`),
when the checkout is the side the merge was onto. That works on any git; `--source` is a
newer option (git 2.40, as I recall its release notes; I did not check an older git here),
and the repo names no minimum git version. The test (`:1305`) puts the
attribute in the base, checks git wrote nine-character markers, and expects the case-(5)
hold.

## Unchanged, and what they feed (anchors the brief asks for)

- `_merge` (tip `:1708`, patched `:1742`): without `stake`, the git command is the tip's
  `:1719` line and nothing else runs (`seen` is None without a call). With `stake`, the pin
  (`:1763-1764`) is iteration 5's.
- `_trial` (tip `:2079`, patched `:2619`): only the `stake` type changed (a Counter).
- `_held_by_line` (tip `:1796`, patched `:2167`) and its call in `fold` (tip `:663`, patched
  `:691`); the `_Unplaced` stop (`:695-707`) is iteration 5's.
- `_explains` (tip `:1859`), `_own_change` (tip `:1887`), `_clash` (tip `:1969`), `_built_on`
  (tip `:2044`): unchanged. In the observed runs `_own_change` gives one lead rev (W holds
  Z's branch), which is why the stake trials conflict at index 1.
- `flow.py` is iteration 5's, byte for byte: `_moved_hold` (patched `flow.py:1609`) words
  the hold, `_announce_conflict_holds` / `_report_conflict_holds` (tip `:1569`, `:1593`;
  patched `:1665`, `:1695`) print it. No case needed new wording.
- Docstrings that described the rule: `fold`'s (`:506-509`), `BaseMove`'s (`:2143-2145`),
  `_held_by_move`'s tie bullet and cost note, `_merge`'s, `_trial`'s.

## Brief cases: what happens (C4 red leg = tip; iteration 5; this patch)

| Case | Tip | Iteration 5 | This patch |
|---|---|---|---|
| (1), (3a), (3b), (3c) overlap, (3d), both partner tests, joint | STOPPING | held | held (unchanged) |
| (2), both take-back probes, three-bundle, (8), (8b) | stop / guard | same | same |
| (5), (6), (7), (10), deleted file | STOPPING | held | held (unchanged) |
| binary | STOPPING (no "could not be placed") | named stop | named stop |
| (9) | ordinary hold | ordinary hold | ordinary hold |
| (a) own deletion, + twin | STOPPING | one-file STOPPING | both held alike |
| (b) move deletes, + twin | STOPPING | one-file STOPPING | both held alike |
| Z drop beside main's line, + twin | STOPPING | one-file STOPPING | both held alike |
| equal stakes | STOPPING | STOPPING | STOPPING (guard) |
| `}` dropped twice | STOPPING | STOPPING, could not be placed | held |
| marker size 9 | STOPPING | STOPPING, could not be placed | held |

The iteration-5 column is the C4 mutation run with iteration 5's `integrate.py` swapped in
(log `.cache/s6/mut-v5.log`): exactly the five new hold tests fail, the three one-file
shapes on `STOPPING` and the other two on `STOPPING` with "could not be placed". The
equal-stakes guard and all 21 earlier tests pass there.

**Case (9), recorded as the brief asks.** W is held for an ordinary overlap with A: hold
line "its change conflicts with issue_A's, already on the line from an earlier wave
(conflicts in shared.txt)", the `Conflicts with: A` proposal, holds `{W: conflict}`, exit 3,
no `BaseMove`, no "rebuild issue_A's branch". `_held_by_move` is never called (observed): A
still merges onto main, so #747's rule names it. Same on the tip (red leg: (9) passes) and on
iteration 4's code (file-rule run: (9) passes).

**Case (8) reaches the "not judged" branch** (observed in the real flow): both stake trials
run, before `{line 2, g1:1, g2:1}`, after adds `line 5, g4:1, g5:1`, `_held_by_move` returns
None, the run stops. (8b): before lines {2, 8}, after lines {2, 5}, None.

## C4 mutation runs (each: mutate, one `run-verify.sh` run, restore, `cmp`)

| Mutation | Tests that fail (green leg) |
|---|---|
| `<` → `<=` (carry-forward gap 2) | equal stakes only: W held |
| `not before - after` ("some line left") | (8b) only: W held |
| iteration 4's file rule (its `integrate.py`) | (5), (6), (7), (10), (a), (b), Z, `}` twice, marker 9: STOPPING; binary: held |
| iteration 5's `integrate.py` | (a), (b), Z: STOPPING; `}` twice, marker 9: STOPPING, could not be placed |
| drops counted as `b - d` (net) | Z only |
| drops not counted (count 1) | (b) only |
| a hunk's drops only at its end place | Z and (7) |
| a hunk's drops only at its start place | (a) only |

The brief's checks: the file rule alone stops (5), (7) and (10) (it also stops (6), the
new one-file shapes, and holds the binary shape); the weaker rule turns (8b) red. Logs:
`.cache/s6/mut-<name>.log`.

## Decisions beyond the brief's text

1. **Every line a hunk drops counts, at every place the hunk spans.** I compared three ways
   to count a hunk's drops; only this one meets the human's "a deleted line gives the same
   key in both trials" for all the shapes below:
   - net drops (`b - d`, nothing for a hunk of one line for one): shape (d) (main turns line
     7 into two lines, W deletes line 8) and Z: the old-base hunk shows no drop, the new one
     does, so the one-file run stops while its twin holds (scratch flow run; the `net`
     mutation turns the Z test red);
   - drops only at one end of the hunk: (a) or Z and (7) stop (the `spread-*` mutations);
   - all of them at every place (this patch): (a), (b), (c) (main deletes line 8, W also
     line 9), (d) and Z each hold in one file and in two, and the advised steps fold W (Z,
     (a), (b) in the shipped tests; (c), (d) in scratch flow runs, `.cache/s6/xshape_test.py`).
2. **Attributes read after the reset**, not with `check-attr --source HEAD` before it: same
   answer (checked on the three layouts), no git-version floor. Cost: `_merge` reads the
   conflicted index and text before the reset (`_conflicted`, 27 lines, mostly moved out of
   iteration 5's `_at_stake`) and computes after it.
3. **Test helper `_on_main` (`:329`) settles a file one side deleted** with that side's
   version, or none, when `merge -X` cannot. The (b) twin needs it: main deletes a.txt, A
   changed it, and `merge -X theirs` stops on the modify/delete. Its docstring already said
   "the branch's side winning every clash"; no existing test reaches the new branch (all
   their merges succeed). `_steps_fold_w` now returns the rebuild's name, and `_edit` drops
   a line given None. Existing callers are unaffected (all 21 earlier tests pass on
   iteration 5's code with this test file).

## What I tried and ruled out (with costs)

- **Telling a dropped old-base line from a dropped line the move added**, using the move's
  own diff (old base → the base the branch holds) per file. Sketch: `_held_by_move` passes
  the first trial's base blobs into the second `_trial` → `_merge` → `_at_stake`, which runs
  one more `git diff -U0` per conflicted file and keys drops of move-added lines apart (about
  25-35 lines; reasoned out from the keys, not built). Ruled out: it breaks the plain case
  where W changes a line the move changed (main line 7 → M7, W M7 → W7, plus a move line A
  clashes with): the second trial's hunk replaces a move-added line, so it would count as a
  new drop and the run would stop, while the two-file twin holds. It also needs state across
  the two trials, which the brief's per-trial set does not have.
- **`--source HEAD`** for the attributes: rejected above (newer git only).
- **Reading markers of any length from 7 up**, no attribute lookup (saves `_marker_sizes`,
  21 lines):
  a recursive merge's inner markers, or a file whose own text has longer marker-like lines,
  would be read as blocks. Rejected.
- **A fallback that places by text** for the `}` shape: forbidden by the brief, and case (10)
  shows why.

## Known limits

- **Shape X: W deletes a line the move added, right beside a line the move changed.** Main
  turns line 7 into `main's line 7` + `X`, W deletes `X`. In one file the old-base hunk is
  line 7 for line 7 (count 1 at places 6 and 7), and the drop of X (place 7) matches it, so W
  is held, stranded plus own; the advised steps do fold W. Its two-file twin (main changes
  a.txt, and adds X to shared.txt, which W deletes) stops: there the drop of X is at stake
  only after the rebuild. The same for X's mirror (X before main's line 7). All four
  observed in scratch flow runs (`.cache/s6/xshape_test.py`). Git's hunk headers cannot tell
  X from a Z shape, printed with production `_own_hunks`:
  - X and Zb (main adds a line before line 7, W deletes line 7): both `(6,1,6,1)` from the
    old base, `(7,1,7,0)` from the new one;
  - X's mirror and Za (main adds a line after line 7, W deletes line 7 — the shipped Z
    test): both `(6,1,6,1)`, then `(6,1,6,0)`.

  Yet X's twins stop and the Z twins hold (Za in the shipped test, Zb in a scratch run). No
  rule that reads hunk headers alone can match both, and the brief allows nothing else (no
  text matching). I kept the rule that satisfies the human's requirement (a deleted line
  keeps its key) and leaves X held with working advice, rather than one that stops Z and (d)
  in one file while their twins hold. This is a judgment for the human at sign-off.
- Carried from iteration 5, unchanged: binary files, custom merge drivers, symlinks and
  submodules are a named stop; an older git whose `git merge` ignores `diff.algorithm` could
  align differently (named stop); a clash whose conflicted path differs between the two
  trials (a rename) does not compare (generic stop); the same-wave stranded partner (#756),
  the `past` hold's acceptance, (3c)'s silence about A's rebuild and the (3a)/(3c) overlap
  gap (#757) are out of scope.

## Refute-your-own-test (forced)

- **(a) Genuine red?** Yes. C4 (`engine/scripts/run-verify.sh`, `PDCA_BUNDLE` = a scratch
  bundle holding this exact `patch.diff`, under `timeout`): `PDCA-EVIDENCE: C4 PASS — red
  without the fix, green with it`. Green leg: 9 + 27 tests OK. Red leg (production hunks
  reverted to the tip): 1 + 20 failures. Every hold case fails on `STOPPING` — (1), (3a),
  (3b), (3c) overlap, (3d), both partner tests, the joint case, (5), (6), (7), (10), the
  deleted-file test (both subtests), #747's flipped test, and the five new hold tests — and
  the binary test fails because its stop line lacks "could not be placed". Green both ways:
  (2), both take-back probes, the three-bundle probe, (8), (8b), (9), equal stakes. Log
  `.cache/s6/c4-final.log`. Against iteration 5's code the five new hold tests go red
  (mutation table), so they bind the four gaps, not only the tip.
- **(b) Production path?** Yes. Every test drives `flow._drive_and_act` → real
  `integrate.fold` → `_held_by_line` → `_held_by_move` → `_trial(stake=…)` → `_merge` →
  `_conflicted` / `_at_stake` / `_marker_sizes` / `_placed`, on real git (bare origin,
  primary checkout, scratch clone). The observed run prints the Counters production filled.
  Only the build leaf, publish's branch cut and `gh` are stubbed, as in child-1's and
  child-2's suites. The test imports modules only (`cli, flow, integrate, publish, state`),
  so the red leg loads and runs. The stress test calls production `_placed` and `_at_stake`.
- **(c) Fixture includes the fault?** Yes. Main really moves on origin after the first fold;
  W's head really holds the move (asserted in `_moved_run`); A really fails onto main
  (`_merges(…, "A") == 0` in every new test); each shape's blocks are checked with plain
  git's own diff3 output before and after A's rebuild (`_one_block`: one block, exact
  sides); the `}` test checks git left two blocks and merged line 6's drop cleanly; the
  marker test checks git wrote nine-character markers; the deletions are real (`_edit(…,
  lN=None)`, `git rm` on main). The advised steps are taken with real git and fold W.

## Gates run here

- C4 on this `patch.diff`: PASS (above).
- T3 `engine/scripts/run-suite.sh` on the final tree, under `timeout`: `PDCA-EVIDENCE: root
  suite OK, driver suite OK`. Root suite 24 tests OK; driver suite 2,652 tests OK, 2 skipped
  (iteration 5 had 2,646; the 6 more are this iteration's new tests). That includes child-1's
  and child-2's suites, the same-wave suite (case (4)'s base-clash stop) and both files of
  this patch. Log `.cache/s6/t3-final.log`.
- Narrower runs during the build: the two cross-wave files, then every
  `test_flow_cross_wave_*`, `test_flow_same_wave_conflict` and `test_integrate*` module
  (190 tests OK), which includes case (4)'s base-clash stop and child-1's flipped test.

## Patch size

`patch.diff` is 160,337 bytes, up from iteration 5's 140,571 (the size the human waived was
137 KB, over the 125 KB backstop). The growth, per file in the patch: `integrate.py`
40,591 → 46,349 bytes (+5.8 KB: the drop counts, `_conflicted`, `_side_hunks`,
`_marker_sizes`, `_side`, and their docstrings); the stranded test file 71,797 → 85,805
(+14.0 KB: six new tests, two small helpers, the `_on_main` settle step). `flow.py` and the
fold-holds test are unchanged. The sizing verdict for this bundle names gaps 3 and 4 as the
parts that could be cut into follow-ups; I kept them, as the sign-off asked for all four
gaps in this rebuild. Cutting them would remove `_side`, `_marker_sizes` and two tests,
about 8 KB.

## Commit-readiness

pdca-harness has no formatter, linter or commit hook: no `.pre-commit-config.yaml`, no
ruff/black/flake8/isort settings (`template/pyproject.toml.jinja` has none), no workflow
running one, no `core.hooksPath`, only `.sample` hooks. CONTRIBUTING.md asks for a DCO
sign-off (publish adds it). `git diff --check` is clean, all four files compile, and no added
line is over 100 columns.

## Scratch left in the worktree (not in the patch)

All under `.cache/s6/` (git-ignored, `.gitignore:11`): probes (`shapes.py`, `attr_probe.sh`,
`stress.py`, `xshape_test.py`, `observe_test.py`, `reasons.py`), mutation helpers
(`mutate.py`, `mutrun.sh`, `integrate.py.mine`), scratch trees of iterations 4 and 5
(`v4tree/`, `v5tree/`), scratch indexes, bundles (`dev-bundle/`, `final-bundle/`,
`mut-*/`), logs (`c4-dev.log`, `c4-final.log`, `mut-*.log`, `t3-final.log`) and scratch
repos (`repos/`). Test runs also wrote ignored `__pycache__/` under `template/`. Left for the
harness to reclaim; nothing was removed.
