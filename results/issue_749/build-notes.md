# Build notes — issue_749, re-plan after iteration 6 (one frame for both trials)

Target: eduralph/pdca-harness. Built in `$PDCA_WORKTREE` on the run's line
`pdca-integration/main-r547f8028520f` at `2d18208`. The worktree was clean at `2d18208` when
this beat started, so iteration 6's `patch.diff` was applied first, as the brief's starting
point. "Tip" anchors are on `2d18208`; "v6" anchors are on that tree with iteration 6's patch;
plain `integrate.py:N` / `test…:N` anchors are on the tree with this `patch.diff`.

`patch.diff` is `git diff --cached HEAD` from a scratch index built from `HEAD` (the real
index was not touched). `git apply --check -R patch.diff` passes on the worktree, so it is
exactly the worktree's change. `flow.py` and `test_flow_cross_wave_fold_holds.py` are
byte-for-byte iteration 6's (their hunks in this patch equal iteration 6's, checked with
`diff`).

## Decisions for sign-off (read these first)

1. **A narrow change to the brief's conflict rule, in the "after" trial only.** The brief's
   rule ("a region with hunks from both sides is a conflict unless both sides give it the
   same text") is used everywhere except one place: an "after" region that holds a hunk the
   partner's rebuild makes *over a move hunk*. There the two sides agree only when they are
   the same hunk (same lines of `S` replaced, same new lines), which is git's own test for
   one change made on both sides (its "eager" level). Text that lines up by itself across
   two different hunks does not settle the conflict there. Code: `_clashing`
   (`integrate.py:2029-2048`, the test at `:2044-2045`), fed by `_carried`'s third return
   value (`integrate.py:1967-1987`).

   Why: with the brief's rule exactly as written, the random probe of (14) finds shapes
   where the shape is **held while its reading twin is not judged**, the direction the
   human's line forbids ("it must not allow false ties"). Measured on 14,000 shapes (seeds
   101-110 and 201-210, 700 each, the same generator as the test), with the twin built as in
   decision 2:

   | after-trial rule | false-tie-direction mismatches | allowed-direction | decisions changed vs the brief's rule |
   |---|---|---|---|
   | the brief's, as written | 3 (seeds 109, 102, 203; one is kind I, two are outside R ∪ I) | 1 (seed 209, kind I) | — |
   | this patch ("eager" in rebuild-over-move regions) | 0 | 1 (the same seed-209 shape) | 3: exactly the 3 above, tied → not tied |
   | conflict whenever two-sided, in those regions only | 0 | 0 (first range) | 9 per 7,000: the 2 above plus 7 holds that are right (W and A make the identical change there) |
   | conflict whenever two-sided, in every after region | 0 | 0 (first range) | 44 per 7,000 |

   All three shapes have the same form: the move replaces a line, W's own change removes
   the move's line, and A removes the line next to it, which has the same text as the one
   the move replaced. So W's text and A's text agree over that region. In the "before"
   trial the region holds the move's hunk on W's side, so the agreement takes nothing out
   of "before" that "after" keeps. In the "after" trial the agreement removes W's removal
   of the move's line (key `("move", …)`) from "after" only, so "after" becomes a strict
   subset and W is held. In the twin (every line its own label) the region conflicts in
   both trials and W is not judged.

   Whether those three are *false* ties in substance can be argued: git's own merge also
   sees no conflict in that region, and the tie comes from another region where the move
   really is part of the clash. I chose the reading the brief's own test encodes (the twin
   is the oracle, and (ii) must hold), because that is the human's stated line. The change
   is three lines and costs nothing else measured: only those 3 of 14,000 decisions move,
   all toward a stop. **If you prefer the brief's rule exactly**, delete the two lines at
   `integrate.py:2044-2045`. The rest of the patch does not depend on them, and the
   regression test `test_lines_that_line_up_on_their_own_never_settle_a_conflict_the_rebuild_makes`
   (`test…:1696`) is the one test that goes red then (checked: with those lines disabled it
   fails on the first shape, `shape tied, twin not`).

   The brief says "If (ii) fails, Do does not widen the exemption". I did not widen it: R
   and I are exactly the brief's predicates (`test…:1760-1763`). The fix is in the frame,
   not in the test.

2. **The reading twin is built from the trimmed reading.** The brief prescribes "each hunk
   drops the equal lines at its start and end (the same trim on every diff)". Git's
   histogram diff does produce such hunks: seed 204 has the move read as `}`,`}`,`x` → `x`
   (`(1,3,1,1)`), which the trim turns into the deletion of the two `}`. A twin built from
   git's raw output then disagrees with the frame in 3 of 7,000 shapes (seeds 204, 209, 210),
   purely because of the trim. I read "every line relabelled by git's own reading of the
   three frame diffs" as the frame's diffs, trim included, so the test's `_reading`
   (`test…:1509`) trims exactly as `_hunks` does (`integrate.py:1927-1933`). With that
   reading, the 7,000 shapes of seeds 201-210 have no mismatch outside R ∪ I. The test
   still checks that git reads the twin as it reads the shape (`test…:1692-1693`).

3. **The rerere trial pin now really serves every trial.** The brief says iteration 6's
   `-c rerere.enabled=false` "stays where iteration 6 put it, in `_merge`'s trial path …
   That path serves every trial, so it reaches #747/#748's classifiers". In iteration 6 it
   did not: the pin was applied only with `stake` (v6 `integrate.py:1763-1764`), which
   `_trial` passed only to the last merge of the two stake trials (v6 `:2648-2649`, called
   at v6 `:2345`, `:2349`). The diff3 pin and the stake reading go away, so `stake` is gone.
   I kept the pin as the brief describes it: `_merge(…, trial=True)` (`integrate.py:1742`,
   pin `:1758`), passed by `_trial` on every merge it makes (`integrate.py:2630`). The real
   fold merge does not pass it and runs exactly as at tip `:1719`. `_merge_over` (the `wins`
   merges, `-X theirs`) is unchanged. The #747/#748 suites are green (below). If you want
   iteration 6's narrower scope instead, there is nothing left to scope it to: no trial
   reads conflict text any more.

4. **Two merge bases always stop, including the common "W depends on two line bundles"
   case.** This follows the brief ("a trial with more than one merge base: the run stops").
   But in the flow it is reached in an ordinary topology. W depends on Z and Q (both wave
   0), so W's base holds both heads; the "before" trial merges W onto A's head with Z's and
   Q's heads merged in first (`_own_change`). That commit and W have two merge bases (Z's
   head and Q's). Test (15)'s flow case is exactly this, and it stops with the named
   message (`test…:1443`). Iteration 6, which read git's index stages (git's own virtual
   merge base), held W there (seen in the C4 run with iteration 6's `integrate.py`, below).
   So this is a stop where iteration 6 held. It is safe, and it is what the brief asks for.
   Flagging it because it will be hit in practice.

## The change, against the brief's Scope

**Removed** (as Scope lists): `_conflicted` (v6 `:1780`), `_at_stake` (v6 `:1809`, with its
diff-algorithm read at v6 `:1844-1846`), `_side_hunks` (v6 `:1878`), `_marker_sizes` (v6
`:1888`), `_own_hunks` (v6 `:1931`, folded into `_hunks`), `_diff3_blocks` (v6 `:1952`),
`_side` (v6 `:1982`), `_placed` (v6 `:2000`), `_one_set` (v6 `:2051`), the
`merge.conflictStyle=diff3` pin, `_trial`'s `stake` keyword, and the `os` / `Counter`
imports they used. `_Unplaced` is renamed `_NotJudged` (`integrate.py:127`).

**The call boundary (named): `_stakes(wt, held, head, there, paths, algo)`**
(`integrate.py:1781`), called by `_held_by_move` (`integrate.py:2333`). It returns
`(before, after)` key sets or raises `_NotJudged`, and runs no merge. Compared with the
brief's list ("the git dir, the file path, the commits `O`, `S`, head, the partner on the
line, the rebuilt partner, the paths git's two trials left conflicting, and the diff
algorithm"):
- `O` is not passed in. The function computes it as `git merge-base --all head there`
  (`integrate.py:1819`). Test (15) requires the function itself to raise on two merge
  bases, which it cannot do if it is handed a single `O`.
- The rebuilt partner is not passed. The "after" partner side is the carry of the
  partner's change onto `S` ("It is not a fresh diff of S against the rebuilt commit"), so
  nothing reads the rebuilt commit.
- "The file path": the function judges every path in `paths` (the two trials' conflicting
  files). `_NotJudged.path` and its message name the file (`integrate.py:134-136`).
- `there`, "the partner as it is on the line", is the commit the "before" trial merges the
  head onto: the partner's head with `_own_change`'s revisions merged in first, exactly as
  iteration 6's single trial did (v6 `:2345`). `_held_by_move` now makes that commit with
  one trial (`integrate.py:2323-2326`), then merges the head onto it
  (`integrate.py:2327`). This makes `O` git's own merge base for that merge, and keeps
  the partner diff `O → there` free of what the head already holds of the line. Cost: one
  more trial per stranded partner, only when the head holds part of the line.

**The frame, bullet by bullet:**
- Three line diffs per conflicting file, each run once: `_hunks` (`integrate.py:1894`)
  called for the move (`O → S`), the own change (`S → head`) and the partner's change
  (`O → there`) (`integrate.py:1828`). Each passes `--diff-algorithm=<algo>`, with
  `--no-indent-heuristic`, `-U0`, `--inter-hunk-context=0`, `--no-ext-diff`, `--no-textconv`
  and `--no-color`, and then trims equal end lines (`:1927-1933`). Blobs and lines come from
  one `git cat-file --batch` per file (`_texts`, `integrate.py:1844`). An absent file is an
  empty one (the one-hunk case, no git call).
- The algorithm is read once per fold: `_diff_algorithm` (`integrate.py:1772`, the same
  read iteration 6 had at v6 `:1844-1846`: `diff.algorithm`, else histogram). `fold` reads
  it lazily, at most once per target group, when the first cross-wave conflict needs
  judging (`integrate.py:651`, `:690`). It goes down through `_held_by_line(…, algo=)` to
  `_held_by_move` to `_stakes`. No diff-algorithm pin is added to any merge.
- "Before" positions: `_chained` (`integrate.py:1948`) composes the move and the own change
  through their keep maps (`_keep`, `:1936`). A chained hunk whose old and new lines come
  out equal is dropped.
- "After" positions: base `S`, head side = the own change, partner side = `_carried`
  (`integrate.py:1967`). A partner hunk that meets no move hunk moves over unchanged; where
  partner and move hunks overlap or touch, the partner's version of the whole region wins.
- Regions: `_regions` (`integrate.py:2002`) joins hunks whose closed ranges `[a, a+b]`
  intersect, in one sweep. One diff's hunks are always at least one line apart (xdiff's
  change records are separated by an unchanged pair), so this equals git's
  overlap-or-touch join of opposite sides. `_clashing` (`integrate.py:2029`) is git's rule,
  with the one exception in decision 1.
- Keys: `(path, kind, n, i)`. `"head"`: a head line a head-side hunk in a conflict puts
  there. `"base"`: a removed line by its line number in `O` (after: an `S` line the move
  kept; `_came_from`, `integrate.py:1990`). `"move"`: an `S` line the move brought in,
  keyed by the move hunk and its offset. In the "before" trial every removed line is a line
  of `O`, keyed `"base"`. I tried keying a removed line inside a move hunk by that hunk on
  both sides of the move. It merges two different lines (the one the move replaced, the one
  it brought in) into one key, which the brief's "the same removed line has the same key"
  does not say. Measured: 667 more ties per 7,000 and 4 new mismatches. Reverted.
- Git decides whether each trial conflicts and in which files (`_trial`, unchanged apart
  from the pin). A clean trial has an empty stake. A conflicting file where the frame finds
  no conflict region raises `_NotJudged("the line diffs show no clash in it")`
  (`integrate.py:1838`), never an empty stake.
- The rule is unchanged: `if not after < before: return None` (`integrate.py:2334`, the
  same test as v6 `:2350`). `_pinned`, `_explains`, and the stranded / past split are
  iteration 6's.
- Not judged, named: binary (`_texts`, a NUL in the first 8,000 bytes as git's
  `buffer_is_binary` checks, `integrate.py:1870-1871`); a non-file entry (`:1868-1869`); git
  not diffing two different texts as lines (`:1923-1924`, e.g. over `core.bigFileThreshold`);
  more than one merge base (`:1821-1822`); no conflict region (`:1837-1838`). `_held_by_line`
  re-raises it (`integrate.py:2207`), and `fold` turns it into the named stop
  (`integrate.py:697-700`). The message is now whole by itself ("the conflict in X could not
  be judged line by line (why)", `integrate.py:134-136`), so the stop line reads "…; the
  conflict in logo.bin could not be judged line by line (it is a binary file), so the fold
  did not judge whether the moved base is part of the clash); STOPPING". `raise exc` is
  iteration 6's (`integrate.py:707`). No `raise … from` was added.
- Docstrings updated: `fold` (`integrate.py:503-516`), `BaseMove` (`:2118-2124`),
  `_held_by_line` (`:2185-2193`), `_held_by_move` (the tie bullet and the cost note), `_merge`
  (`:1743-1753`), `_trial` (`:2614-2616`).

**Size.** `integrate.py`: 2,786 lines / 172,179 bytes, against iteration 6's 2,805 / 173,777
(tip: 2,261 / 140,659), so smaller than iteration 6's, as the brief asks. `patch.diff`:
186,317 bytes (iteration 6: 160,337). The growth is the test file: 1,778 lines against
iteration 6's 1,328 (8 new tests, the probe and its helpers). The split was declined, so I
did not cut anything the brief asks for.

## The test file, against the Success criterion

**Kept.** Every iteration-6 line stays except the four places the brief allows. `diff -u`
of iteration 6's file against this one removes only: the deleted-file test's
`"could not be placed"` (`test…:1119`), the binary test's expected string (`test…:1139-1141`)
and its comment's last four lines, which described the old mechanism and stop wording
(`test…:1127-1130`; comment only), and the two `assertNotIn("could not be placed", …)`
(`test…:1313`, `:1334`). Each absence check now checks `"could not be judged line by line"`.
The binary test still names `logo.bin` and asserts one `STOPPING` line. All 27 iteration-6
tests pass unchanged. The module docstring gains one paragraph (inserted lines only), and
three imports were added (`random`, `shutil`, `tempfile`).

**New** (all real git; the flow ones through `flow._drive_and_act` on `StackFoldGit`):
- (11) `test_repeated_lines_read_one_way_for_both_trials_hold_as_two_files_do`
  (`test…:1377`): the adversary's shape, its two-file twin and its unique-lines version,
  through `_twins_hold_alike` twice (shape + twin, then unique + twin, so all three agree on
  holds, partners, `BaseMove`, exit code and masked lines). The advised steps fold W
  (`_steps_fold_w`). Fixture facts: git's histogram diff of W from the old base is
  `@@ -0,0 +1 @@`, `@@ -2,2 +3 @@`, and from the main W holds it is `@@ -1 +1 @@`.
- (12) `test_a_seven_character_underline_holds_as_an_eight_character_one_does`
  (`test…:1396`): both underlines run. Fact: git's diff3 output has the base side's
  `=======` right before git's own separator.
- (13a) `test_the_frame_reads_lines_with_the_diff_algorithm_the_merge_uses`
  (`test…:1422`): (5) and (11), each with `diff.algorithm` unset, myers, patience in the
  primary checkout's config (the fold's worktree shares it). The outcome tuples are equal.
- (13b) `test_the_frame_takes_the_diff_algorithm_the_merge_runs_with` (`test…:1585`): at
  the call boundary, the frame finds a region exactly when porcelain `git merge` conflicts,
  with the setting unset and with myers. Mutations: forcing histogram fails the myers
  setting (`'myers': (True, True)`); dropping `--diff-algorithm` (git diff's myers) fails
  the unset setting (`'': (False, False)`). I checked the shape with git 2.53 in a scratch
  repo first: unset → conflict, myers → clean, histogram → conflict, patience → clean,
  minimal → clean, myers config plus `-X diff-algorithm=histogram` → conflict;
  `merge-tree` conflicts whatever `-c diff.algorithm` says.
- (14) `test_a_random_probe_decides_each_shape_as_its_reading_twin` (`test…:1721`): seeds
  749, 750, 751 × 250 = 750 shapes, one plumbing-built repository per seed, trial outcomes
  from `git merge-tree --write-tree` (the rebuild with `-X theirs`, the "after" trial with
  `--merge-base=S`), and the decision from the production `_stakes`. It asserts at least 600
  shapes, more than 90% compared, (i) none outside R ∪ I, (ii) every exempt one
  `(not tied, tied)`, and (iii) at most 1% exempt. **Measured: 27.2 s** on this host when run
  alone (the count was not lowered). 737 of 750 compared, 0 outside, 0 exempt. **Positional
  twin: 17 mismatches of 703 compared** (counted only, as the brief asks).
- `test_lines_that_line_up_on_their_own_never_settle_a_conflict_the_rebuild_makes`
  (`test…:1696`): the three shapes of decision 1, each decided as its twin (both not tied).
  This is the test that pins decision 1. It is beyond the brief's list, added because the
  probe's seeds do not hold those shapes (seed 102's is shape 563 of its run).
- (15) `test_a_trial_with_more_than_one_merge_base_is_not_judged` (`test…:1615`): a
  criss-cross made with plumbing (`merge-base --all` gives `x1`, `y1`; `merge-tree`
  conflicts). `_stakes` raises `_NotJudged`, `.path == "f.txt"`, and the message is the full
  "could not be judged line by line" sentence. Flow side:
  `test_a_trial_with_two_merge_bases_is_not_judged_and_the_stop_names_the_file`
  (`test…:1443`), see decision 4.

The function-level tests reach `integrate._stakes`, `_NotJudged` and `_diff_algorithm` by
attribute at call time. The module imports modules only, so on the red leg it loads and
these tests error with `AttributeError` (not a load failure).

## Red and green (C4, the project's `engine/scripts/run-verify.sh`, under `timeout`)

Run from the instance root with `PDCA_BUNDLE` = a scratch copy of this bundle (brief +
this `patch.diff`) and `PDCA_WORKTREE` set. Log: `.cache/s7/c4-final.log`.

- Green leg: fold-holds 9 tests OK, stranded-holds 35 tests OK (60.8 s).
- Red leg (production hunks reverted to the tip): fold-holds 1 failure (#747's flipped
  test); stranded-holds 24 failures and 4 errors. Failing: every hold case — (1), (3a), (3b),
  (3c) overlap, (3d), both partner tests, the joint case, (5), (6), (7), (10), the deleted
  file (both subtests), the three deletion shapes, `}` dropped twice, marker size 9 — plus
  the binary test (no "could not be judged line by line"), (11), (12), (13a) (`STOPPING`),
  and (15)'s flow test (it stops, but without the message). Erroring (`AttributeError`, no
  stake function on the tip): (13b), (14), (15)'s criss-cross, and the lined-up regression
  test. Green both ways, as guards: (2), both take-back probes, the three-bundle probe, (8),
  (8b), (9), equal stakes.
- `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`.

**With iteration 6's `integrate.py` in place of the new one** (the brief's behaviour red; a
scratch bundle whose patch is this one with iteration 6's `integrate.py`; log
`.cache/s7/c4-v6.log`): the green leg fails with 5 failures and 4 errors, giving
`PDCA-EVIDENCE: C4 FAIL — bundle test red WITH the fix applied`:
- (11): `wave 1 did not integrate … (conflicts in shared.txt) … STOPPING`.
- (12): `wave 1 did not integrate … the conflict in README.md could not be placed on
  issue_W's own lines (its diff3 blocks do not fit …) … STOPPING`.
- (13a): `STOPPING` (its case-(11) run).
- (15) flow: iteration 6 *holds* W ("stranded + own"); the new frame stops (decision 4).
- binary: iteration 6's wording.
- errors: the four function-level tests (no `_stakes` in iteration 6).
- All 27 kept tests otherwise pass on iteration 6's code. Their assertions did not change.

Mutation checks (each mutate, run, restore, `cmp`):
- Per-trial "before" reading (git's own `O → head` diff instead of the chained one, the
  cause of the original defect): the probe fails, with 31 mismatches outside R ∪ I and 5
  exempt on its 750 shapes (9 of the 31 in the false-tie direction), and (11) fails.
- No trim: no effect on the probe's 750 shapes, so the probe does not pin the trim. The
  trim is the brief's prescription; seeds 204, 209 and 210 are where it matters.
- Eager test off: the lined-up regression test fails.

## Other gates run here

- T3, `engine/scripts/run-suite.sh` on the final tree: `PDCA-EVIDENCE: root suite OK, driver
  suite OK`. Root suite 24 tests OK; driver suite 2,660 tests OK, 2 skipped (iteration 6:
  2,652; the 8 more are this patch's). Log `.cache/s7/t3-final.log`.
- Before that, every `test_flow_cross_wave_*`, `test_flow_same_wave_conflict` and
  `test_integrate*` module: 198 tests OK (child-1's and child-2's suites included).

## Refute-your-own-test (forced)

- **(a) Genuine red?** Yes. C4 with the production hunks reverted: 1 + 24 failures and 4
  errors, every hold case failing on `STOPPING`, (15) failing on its missing message, the
  four function-level tests erroring for want of the function. With iteration 6's
  `integrate.py`, (11) and (12) fail on `STOPPING`, (12) with "could not be placed".
  Decision 1's test fails with the eager test disabled. The probe fails with a per-trial
  reading.
- **(b) Production path?** Yes. The flow tests drive `flow._drive_and_act` → `integrate.fold`
  → `_held_by_line` → `_held_by_move` → `_trial` (real `git merge`) → `_stakes` → `_texts` /
  `_hunks` (real `git cat-file` / `git diff`) → `_chained` / `_carried` / `_clashing`. The
  function-level tests call the production `_stakes` and `_diff_algorithm` on real
  repositories. Only the probe's trial outcomes come from `git merge-tree` instead of
  `_trial` (the brief's design, for speed). The probe's twin construction and R/I
  predicates are test code reading git's own diff output.
- **(c) Fixture includes the fault?** Yes. (11) asserts git really reads W's change one way
  from the old base and another way from the new one (the hunk headers). (12) asserts git
  writes the seven-`=` line right before its own separator. (13b) asserts the merge outcome
  flips with `diff.algorithm`. (15) asserts `merge-base --all` gives two (criss-cross, and
  Z's and Q's heads in the flow). Each probe twin is checked to read as its shape. The
  lined-up shapes are the ones that failed under the brief's literal rule. A really moves on
  origin in every flow case (`_merges(…, "A") == 0`).

## Known limits

- Two merge bases → named stop (decision 4).
- A head that holds a line bundle (`_own_change` revisions) which changed the conflicting
  file: "after" is read from `S`, which lacks that bundle's lines, so the own change carries
  them as hunks. That can add "after" keys, which gives a stop (the safe direction), never a
  hold.
- Paths git quotes in `git diff --name-only` (non-ASCII names, with `core.quotePath` on) do
  not resolve in `cat-file`, so such a file reads as absent everywhere and gets the named
  "no clash" stop. A clash across a rename is read by the merged path name, which mostly
  ends in the same stop. Symlinks are read as their target text. Submodules read as absent
  (named stop).
- Git version. The frame assumes, as the brief does, that porcelain `git merge` honours
  `diff.algorithm` (true on 2.53 here). On a git whose merge ignores it, a repository that
  sets it would be read one way by the merge and another by the frame. That mostly ends in
  a named stop, and (13a)/(13b) would fail there. The probe also needs `git merge-tree
  --write-tree` with `-X` and with `--merge-base` given trees. CI's render-check renders the
  template and runs this whole suite with the runner's git (locally that run passed: the
  root suite's `test_render_then_slice` runs the rendered project's tests, under a minimal
  environment with no `HOME`).
- Conflict style: I checked that it does not change *whether* a merge conflicts (0 of 3,000
  random three-way merges differ between `merge`, `diff3` and `zdiff3` with
  `git merge-file`), which supports dropping the diff3 pin.
- Carried from iteration 6, unchanged: the same-wave stranded partner (#756), the (3a)/(3c)
  advice gap (#757), the `past` hold, and (3c)'s silence.

## Commit-readiness

pdca-harness has no formatter, linter or commit hook: only `.sample` hooks, no
`core.hooksPath`, no ruff/black/flake8 config, and CI runs render-check on Python 3.12
(nothing here needs more than 3.11). `git diff --check` is clean, no changed line is over 100
columns (the file's existing limit), and an AST check found no unused import or private
helper. The DCO sign-off is publish's job.

## Scratch left in the worktree (not in the patch)

All under `.cache/s7/` (git-ignored by `/.cache/`, `.gitignore:11`): probe scripts
(`scripts/probe.py`, `variants.py`, `modes.py`, `compare.py`, `literal.py`,
`literal_detail.py`, `where.py`, `style_search.py`), their logs (`prod-*.log`, `var-*.log`,
`modes.log`, `compare.log`, `literal-*.log`), the C4 and T3 logs (`c4-final.log`,
`c4-v6.log`, `t3-final.log`), scratch bundles (`c4-bundle/`, `c4-v6-bundle/`), scratch
indexes, iteration 6's and the tip's `integrate.py` (`v6/`), a copy of the new one, and small
git repos (`probe1/`, `p13b/`, `r_*`, `cs`, `cs2`, `mf/`). Test runs also wrote ignored
`__pycache__/` under `template/`. Left for the harness to reclaim; nothing was removed.
