# Adversarial review — issue 749 (iteration 6)

I tried to refute the evidence, the hunk/line-set rule, and the "one file and two files behave
the same" claim. The gates hold up when re-run. The rule does not fully hold up. I found two
concrete plain-text shapes where a one-file clash stops while the brief says it should be held.
Both fail safe: the run stops, and no wrong advice is printed.

## Findings

- NEEDS-HUMAN [human] — **Repeated lines still split one-file from two-file behaviour.** See
  `template/src/pdca_harness/integrate.py:2350` (`not after < before`), which is fed by
  `_own_hunks` (`integrate.py:1931`) through `_at_stake` (`integrate.py:1809`). The failing case:
  shared.txt is `}`, `}`, `line 3` … `line 7`. A changes line 2. After fold 1, main changes
  line 3, so A no longer merges onto main. W, built on that main, keeps main's line 3 and changes
  line 1. I ran it through `flow._drive_and_act` on `StackFoldGit`, using the bundle's own
  `_moved_run` / `_twins_hold_alike` helpers. The result is `wave 1 did not integrate … an
  undeclared cross-wave overlap … STOPPING`, with holds `{}`. Three controls behave differently.
  Its two-file twin (main adds a.txt, A adds one and changes line 2, W changes line 1) is held
  with the stranded-plus-own advice. The same one-file shape with unique lines is held. And the
  hold's two steps (`_on_main("A")`, then `_rebuilt("W")`) do fold W in the one-file run, so a
  hold would have been right. The cause: from the old base, git's diff lines up W's change as
  an insertion (`@@ -0,0 +1 @@ +W1`, then `@@ -2,2 +3 @@` for `}`+line 3 → main's line 3).
  From the main W holds, it is a one-line edit (`@@ -1 +1 @@`). So W's line 1 merges cleanly
  while A is on the line, and is at stake only after A is rebuilt. "After" gains a line, and the
  rule refuses to judge. The code does exactly what the brief's rule says. What is not supported
  is the brief's claim that the rule makes the outcome independent of layout, and case (10)'s
  title, "Repeated lines do not change the result": `test_flow_cross_wave_stranded_holds.py:1060`
  covers only one shape. In a random probe that drives the production `_trial(..., stake=)`, 4
  of about 210 shapes with repeated `}` / blank lines stopped this way, and 0 of 216 shapes with
  unique lines did. Human call: accept this as a known limit that fails safe (it stops), or
  change the frame. Any per-trial set of git's hunks lines up repeated lines differently
  against the two merge bases, so iterating inside the current rule will not close this.

- NEEDS-HUMAN [impl] — **A content line of exactly seven `=` signs inside a block's base side is
  read as git's separator.** See `integrate.py:1967-1972` in `_diff3_blocks`: once `|||||||`
  has been seen, any line equal to `=======` switches to the head side. The failing case:
  README.md with a Markdown heading `Install` underlined `=======`. The underline is seven
  characters, the same length as the title, which is a common habit. RST files also use
  underlines like this. A retitles it to `Setup` / `=====` and edits line 8. Main then edits
  line 8. W, on that main, changes `Install` to `Installing`. Through the real flow this gives
  `… the conflict in README.md could not be placed on issue_W's own lines (its diff3 blocks do
  not fit the lines the branch changed in exactly one way) … STOPPING`. The same shape with an
  eight-character underline is held with the stranded-plus-own advice. This contradicts the
  brief's statement that git's text output always places, and the stop message points the user
  toward binary files and merge drivers when the cause is neither. The builder can fix this by
  iterating. One option: also pin a long trial-only marker size, for example through a
  trial-only `-c core.attributesFile=…` holding `* conflict-marker-size=<large>`, passed to
  both the trial merge and the `check-attr` in `_marker_sizes`. That file sits below in-tree
  `.gitattributes`, so a repo's own setting still wins and is still read. Another option: let
  `_diff3_blocks` try the other ways to read a marker-like line, and keep the one that matches
  the stage blobs. Either way, add a real-git regression test for a 7-character underline.

## Attacks that did not land (checked, could not refute)

- **C4 red→green.** I re-ran all 27 tests of `test_flow_cross_wave_stranded_holds.py` on the
  patched tree, by inheriting them into my probe class, and all passed. The frozen red leg
  (`gate-logs/C4-verify.log`) shows (1), (3a), (3c), (3d), (5), (6), (7) and (10) failing with
  `STOPPING` when the fix is reverted, as the brief requires. The tests drive
  `flow._drive_and_act` on `StackFoldGit` with real git, not a copy of the code.
- **The mutation claims (carry-forward item 2, and (8b)).** I ran them on mutated copies of
  `integrate.py:2350` in my sandbox. Changing `<` to `<=` turns
  `test_the_same_stake_before_and_after_the_rebuild_still_stops` red. The weaker rule
  `before - after` turns (8b) red. Guard (8) stays green under both, as the brief says it will.
- **False ties, which would be the dangerous direction.** I could not build one. If A does not
  merge onto the main W holds, A clashes with that main's changes, and W carries those changes,
  so the move really is part of the clash. Also, `stranded` only names a bundle that does not
  merge onto `base_ref` either, so the "rebuild issue_A's branch" advice stays true.
- **Diff settings.** On git 2.53, `git merge` honours `diff.algorithm`: 28 of 150 random merges
  came out differently under histogram, myers and patience. So reading that setting in
  `_at_stake` is correct. Indent heuristic and inter-hunk context are pinned off, which matches
  how merges work.
- **The real fold merge is unchanged.** `integrate.py:1763` adds the diff3/rerere pin only when
  `stake` is given, and only `_trial` passes `stake`, for its last rev only.

<!-- pdca:leaf-complete -->
