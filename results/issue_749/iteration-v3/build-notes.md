# Build notes — issue_749, iteration 3 (aim the fix at a line bundle stranded by a moved base)

Target: eduralph/pdca-harness. Built on the run's line `pdca-integration/main-r547f8028520f`
at `2d18208` (#738, #747, #748 folded; `stack-base-tip`). "Tip" anchors are on `2d18208`.
"Patched" anchors are on that tree with `patch.diff` applied. `patch.diff` applies cleanly
onto `2d18208`: I applied iteration 2's patch to the clean worktree, made the changes below,
and wrote the diff from a scratch index built from `HEAD` (the real index was not touched).

## The carry-forward, and what changed in this iteration

The one build finding: the "stranded plus own" hold line said "…: origin/main moved since
it was cut; and its change also conflicts with issue_A's". The nearest "it" is the partner,
A, so the line read as if A's change clashed with A's. This is the one moved hold that does
blame the held bundle, so it must name it.

1. **Fixed as asked.** Patched `flow.py:1640-1641`:
   `"; and {name}'s own change also conflicts with {_where(...)}"`, the same form the other
   branch already uses (patched `flow.py:1644`, "{name}'s own change does not clash with it").
2. **Two more "it"s in the same new lines, same problem. Also fixed.** Both lines are new in
   this patch, and in both the clause just before is about the partner's branch:
   - the hold line's tail, "…; rebuild issue_A's branch on the new origin/main; bundles that
     depend on **it** or are its `Conflicts with` partners are held this run." "It" reads as
     A's branch, so it looks as if A's dependents were held. Now "bundles that depend on
     {name}" (patched `flow.py:1685`, with a one-line comment at `:1683` so nobody
     "harmonises" it back to the ordinary line's "it").
   - the end-of-run line, "…and issue_W's own change does not clash with **it** (a.txt). To
     fold **it**, rebuild issue_A's branch…". The second "it" reads as A's branch. Now "To fold
     {name}" (patched `flow.py:1706`).
   I did not change the ordinary hold lines (`flow.py:1688-1691`, `:1710-1712`): there "it"
   follows "its change conflicts with …", so it reads right, and the wording is #674/#747's.
   I did not change `_runnable`'s `Conflicts with` partner line either (patched
   `flow.py:863-869`). Its "it"s follow #674's pattern, and the only new part, the
   parenthetical, now names the held bundle when it blames it (it reuses `_moved_hold`).
3. **Tests updated in both files** (the reviewer asked for both):
   - `template/tests/test_flow_cross_wave_stranded_holds.py`: case (1) (`:352`) now asserts
     "bundles that depend on issue_W or are its `Conflicts with` partners are held this run",
     "To fold issue_W, …", and that "depend on it" / "To fold it" are absent; (3b) (`:454`)
     asserts "To fold issue_V/Y, update …"; the P/R case (`:644`) asserts "and issue_W's own
     change also conflicts with issue_B's, issue_P's, issue_R's" and that "its change" is absent.
   - `template/tests/test_flow_cross_wave_fold_holds.py`, the flipped test (patched `:404`):
     "and issue_Y's own change also conflicts with issue_A's", "bundles that depend on issue_Y
     or are its `Conflicts with` partners", "To fold issue_Y, …", and "its change" absent.
4. **Nothing else changed.** `integrate.py` is byte-identical to iteration 2's (`cmp`). The
   approach and the fixtures are as they were. The deferred findings in
   `deferred-findings.json` (the `past` outcome, the (3c) reading, the same-file stop, the
   plan-level items) need the human's judgment and were not build work, so they are untouched.

Real output, the flipped test, before (iteration 2) and after:

> issue_A's branch, already on the line from an earlier wave, does not merge cleanly onto the
> origin/main issue_Y's branch holds: origin/main moved since it was cut; and **its change**
> also conflicts with issue_A's, already on the line from an earlier wave (conflicts in a.txt,
> shared.txt); rebuild issue_A's branch on the new origin/main; bundles that depend on **it**
> or are its `Conflicts with` partners are held this run.

> issue_A's branch, already on the line from an earlier wave, does not merge cleanly onto the
> origin/main issue_Y's branch holds: origin/main moved since it was cut; and **issue_Y's own
> change** also conflicts with issue_A's, already on the line from an earlier wave (conflicts
> in a.txt, shared.txt); rebuild issue_A's branch on the new origin/main; bundles that depend
> on **issue_Y** or are its `Conflicts with` partners are held this run.

End-of-run line after: "… (a.txt, shared.txt). To fold issue_Y, rebuild issue_A's branch on
the new origin/main. Proposed, for you to confirm: declare `Conflicts with: A` in issue_Y's
brief, then rebuild issue_Y on a base that holds issue_A."

**The updated tests bind this wording.** I ran both test modules against iteration 2's
production files in a scratch copy (`.cache/v2/template`, built with `git apply --cached`
of iteration 2's patch into a scratch index, so exactly that code). 4 of 19 fail, each on
the wording: case (1) (the tail), (3b) ("To fold issue_V"), the P/R case and the flipped
test. The last two fail on exactly the phrase the reviewer flagged ("…; and issue_W's own
change also conflicts with …" not found). The other 15 pass there. So these strings are
what pins the fix, not something nearby.

## What the patch does (as iteration 2, apart from the wording above)

**`integrate.py`**

- `fold` gets `moved: dict[str, BaseMove] | None` (patched :368). It is passed to
  `_held_by_line` at child-1's call site (tip :663-666, patched :672-675).
- `BaseMove` (patched :1805): `base`, `stranded`, `past`, `own`.
- `_held_by_line` (tip :1796, patched :1831) runs child-1's and child-2's rules through
  `_pinned`. Only when they name nobody, and the branch merges onto the base alone
  (`kind in ("batch", "line")`, so never for a base clash), does it call `_held_by_move`
  (patched :1883-1889).
- `_pinned` (patched :1897): tip :1841-1851 moved unchanged into a function that takes the
  base, `under`, and `stay`.
- `_held_by_move` (patched :1924-2024) is the re-try. `now` = the bundles whose own change
  fails on the current base, i.e. the ones child-1's rule (d) skips (tip `_partners` :2016,
  the `at != 1` skip at :2032-2034). `held` = `git merge-base head <remote>/main` (:1976),
  the brief's `S`. `lost` = the ones failing on `held` (:1978).
  - `lost` and `now` both empty → None: no move in the clash, so the run stops (:1979-1981).
  - `lost` empty, `now` not → rule (i): `_pinned` on `held` (:1982-1984), an ordinary hold.
  - Otherwise each lost bundle is rebuilt on `held` with `_trial(held, [its], wins=0,
    made=…)` (:1985-1990): a merge with its side winning, never a squash (`_trial`, tip
    :2079). child-2's `_own_change` (tip :1887) goes before the head in both tie trials (:1991).
  - Tie per lost bundle the head clashes with (:1993-2002). The head's clash with the bundle
    as it is on the line, against its clash with the bundle rebuilt on `held`. The bundle
    counts only if the first clash has a file the second does not. The two trials differ
    only in the bundle's base, so a file that drops out is one where the move is what
    clashes. A clash that loses no file → None.
  - The tied bundles split into `stranded` (they fail on the current base too) and `past`
    (they fit it). Both at once, or none tied → None (:2003-2006).
  - `past` (:2007-2012): held only if the head, updated from the base, merges onto the line.
  - `stranded` (:2013-2022): `_pinned` again on the rebuilt line with `stay=stranded`
    (:2015), or, with no one named, the outright check that the head merges onto that line
    (:2016-2020). An own partner that was rebuilt but not tied → None (:2021-2022).
- `_unfit` (patched :2027): the trials behind `now` and `lost`.
- `_explains` (tip :1859, patched :2047) gets a keyword `stay`. A bundle in it stays on the
  line and the head is tried rebuilt on it, as for a prerequisite
  (`own = _prerequisites(cfg, d) | set(stay)`, patched :2059). The default `()` leaves
  child-1's and child-2's calls unchanged.

**`flow.py`**

- `_moved_hold` (patched :1609) words a moved hold as `(what, step, wait)`.
- `_announce_conflict_holds` (tip :1569, patched :1664) and `_report_conflict_holds` (tip
  :1593, patched :1694) word a moved hold through it (patched :1681-1687, :1703-1709).
  Ordinary holds print byte for byte what they printed before (`_where`, patched :1590;
  `_overlap_step`, :1648).
- `_runnable`'s `Conflicts with` partner line (tip :856-863, patched :863-869) uses
  `_moved_hold`'s `what`/`wait` for a moved hold (case 3d).
- `_drive_and_act` keeps `held_moved` (patched :2855) beside `held_conflict` and passes it
  to `_runnable` (:2988), the fold (`moved=None if dry else held_moved`, :3163), both
  announce calls (:3168, :3176) and the report (:3203).

## Brief case → path taken (folded tip vs patched)

| Case | Tip `2d18208` | Patched |
|---|---|---|
| (1) stranded W (`:352`) | `wave 1 did not integrate … STOPPING`, T never built | tie: A clashes in `a.txt` as on the line, clean once rebuilt → stranded; `_pinned` names nobody; outright check clean → pure stranded hold. Exit 1 (V PLANNED) |
| (2) moved-on prerequisite K (`:380`) | held naming N only | unchanged: child-1 holds it in `_pinned` on the base; `_held_by_move` never runs (guard) |
| (3a) main moved twice (`:419`) | STOPPING | rule (i): A fails on main now (line 8) but fits `held` (m.txt only) → `_pinned(held)` names A, ordinary wording |
| (3b) main undid a commit (`:454`) | STOPPING on V, "declare the conflict / re-order" | `past` path, see below |
| (3c) Y does not hold the move (`:498`) | STOPPING | rule (i): `held` is the old main, A fits it → ordinary hold, `Conflicts with: A` |
| (3c) Y takes the move back out, other file (`:531`) | STOPPING | STOPPING (guard): no file drops out of the clash → None |
| (3c) Y takes the move back out, same file (`:557`) | STOPPING | STOPPING (guard): both trials conflict in `shared.txt` → None |
| (3d) X `Conflicts with: W` (`:586`) | STOPPING, X never reached | X held, waiting for "issue_A's branch is rebuilt on the new origin/main, and issue_W's PR merges" |
| P/R beside stranded A (`:644`) | STOPPING | hold: A stranded; B, P, R own (child-2's pair search on the rebuilt line) |
| three bundles beside stranded A (`:678`) | STOPPING | STOPPING (guard): nothing explains the rest → None |
| (4) base clash, `test_flow_same_wave_conflict.py:435` | STOPPING | STOPPING: `_clash` says `"base"`, `_held_by_move` never runs (patched :1884) |
| (4) child-1's flipped test (`test_flow_cross_wave_fold_holds.py`, tip :402) | STOPPING | **hold** (below) |

**Case (3b): the path it takes (the brief asks Do to say).** On the folded tip, rule (d)
does *not* fail in (3b): A merges onto `origin/main` as it is now (main dropped its `a.txt`
again), so child-1's `_partners` and child-2's `_together` name nobody, and the run stops on
V with the generic fold error ("an undeclared cross-wave overlap; declare the conflict /
re-order", seen in this iteration's C4 red leg). The (i)-(iii) re-try is never reached.
Patched, it takes the `past` branch: `now` is empty, `lost` = {A} on the main V holds, and
the tie holds (A clashes in `a.txt` as on the line, clean once rebuilt). The step is
trial-checked: V updated from `origin/main` merges onto the line (patched :2007-2012). The
test then takes the step (`StackFoldGit._update_branch("Y")`) and checks Y merges. This
branch goes beyond the brief's (i)-(iii). Both reviewers flagged it as a fourth outcome for
the human to accept (deferred). I kept it because the (3b) assertion ("their step is update
the branch from <remote>/main") cannot be met on a path that stops.

**Case (4) flip, recorded as the brief asks.** child-1's
`test_a_clash_with_a_partner_whose_head_no_longer_fits_the_base_still_stops`
(`template/tests/test_flow_cross_wave_fold_holds.py`, tip :402) is renamed
`test_a_clash_with_a_partner_whose_head_no_longer_fits_the_base_holds_it` (patched :404) and
asserts a hold. Y holds main's `a.txt` (the move: the tie holds, `a.txt` drops out once A is
rebuilt) and also changes `shared.txt` as A does (an own overlap, named by child-1's
`_partners` on the rebuilt line). The hold names A as stranded and, as of this iteration,
says "issue_Y's own change also conflicts with issue_A's"; the end-of-run line adds the
`Conflicts with: A` proposal. V is `Stacks on: W`, cut from the line, so V holds A's old
head; that is why the check keeps a stranded partner on the line (`stay`). The test checks
two more facts with plain git: V holds A, and with both steps taken (A rebuilt on main, Y
rebuilt on that) everything merges. Exit 3.

## What I tried and ruled out

This iteration:

- **Changing only the flagged line.** That was the literal ask: one f-string line (two once
  wrapped at 100 columns) and the expected strings of the two own-case tests. Ruled out
  because the same new lines have two more "it"s that read as the partner (above). What
  shipping all three costs, against iteration 2: `flow.py` +6/−4 lines (three f-strings and
  the comment), the stranded test file +16/−14, the fold-holds test file +9/−8.
- **Rewording the ordinary hold lines too**, for one style everywhere. Not done: their "it"
  reads right (see 2 above), the text is #674's/#747's, and other suites assert it.

Kept from iteration 2:

- **Taking every own partner off the line in the check** (child-1's model for any partner
  that is not a prerequisite). The flipped test cannot pass with it: V, left on the line,
  was built on A, so `_explains`'s "brings back" check (tip `integrate.py:1872-1874`) fails
  and the flip stays a stop. Iteration 2 checked this with `stay=()` in a scratch copy: 18
  of 19 tests pass and the flip test stops. `stay` costs 1 changed line, a keyword and 3
  docstring lines in `_explains`, and 2 passes in `_pinned`.
- **Comparing conflict hunks for the tie** instead of file sets. Not done. The tie stays a
  pair of `_trial` results, the house style ("decided by trial merges … never by which
  files or hunks clash", `_together`'s docstring, tip :1922-1923). Its known limit (below)
  errs toward a stop, never toward wrong advice. The adversary's same-file case is a
  deferred item for the human (see Known limits).
- **Calling the same-file probe an ordinary overlap** (naming A, `Conflicts with: A`).
  Ruled out: rule (i) needs every partner to merge onto `S` alone, and A does not; rule
  (iii) says anything else stops.
- **Iteration 1's line-wins trial, a squash, a second trial-worktree helper.** None used.
  The rebuild is `_trial`'s existing `wins`/`made`; `_trial` is unchanged.
- **Pinning bases to the run's start.** Not done (stated non-change). The tests assert only
  that the held bundle's base holds the moved main (`self.seen["issue_W"][1]`).

Cost of the re-try, per fold conflict no earlier rule pinned (n bundles on the line, k of
them failing on the base the branch holds): 2n trials (`_unfit` on the base and on `held`;
n when they are the same), then 3k (rebuild and two tie trials), then one `_pinned` pass
(1 + n + 1 trials, plus `_together`'s up to n + n(n−1)/2, plus at most 2 checks), or 1
outright check, or 2 for `past`. All of it runs only after a fold merge has already
conflicted, which today stops the run.

## Known limits (each stops the run, as today; none gives a wrong step)

- **File granularity of the tie.** When the move's clash with a partner and the branch's own
  clash with it are in the same file, no file drops out, so the partner is not shown to be
  stranded and the fold stops. Example (the adversary's, deferred for the human): A edits
  lines 2 and 8, main edits line 8, the branch keeps main's line 8 and edits line 2. The
  two-file version (the flipped test) holds. No test pins this stop on purpose: the human
  is to decide whether it should stay a stop or become a hold.
- **The branch changes a moved spot further** (main adds `a.txt`, the branch edits main's
  `a.txt`): both tie trials conflict in `a.txt`, so it stops. Right: whether A's rebuild
  fixes it depends on which side A's owner keeps.
- **Stranded and past bundles in one clash** → stop. So does a clash the move puts no bundle
  in, and a lost bundle an own trial names but the tie does not.
- **A stranded bundle the branch does not clash with** is rebuilt for the check (its owner's
  business) and never named.

## Refute-your-own-test (forced)

- **(a) Genuine red?** Yes. `engine/scripts/run-verify.sh` (PDCA_BUNDLE and PDCA_WORKTREE
  set, under `timeout`) reverts the production hunks: 7 tests fail and the gate prints
  `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`. The 7 are case (1), (3a),
  (3b), (3c), (3d), the P/R case, and child-1's flipped test. Each fails with `'did not
  integrate' unexpectedly found in "flow: wave 1 did not integrate (issue_<X>'s branch …
  STOPPING"`, the pre-fix stop. The four guards ((2), both take-the-move-back-out cases,
  the three-bundle case) pass both ways, as the brief expects for (2). For this iteration's
  change alone: against iteration 2's production code, the 4 wording tests fail (above).
- **(b) Production path?** Yes. Each test calls `flow._drive_and_act`, which runs the real
  `integrate.fold` → `_held_by_line` → `_held_by_move`, on real git (bare origin, primary
  checkout, scratch clone), with real base builds and the real exit-code rule
  `cli._results_rc`. The hold lines checked are the ones `_announce_conflict_holds` and
  `_report_conflict_holds` really print to stderr. Only the build leaf, publish's branch cut
  and `gh` are stubbed, as child-1's and child-2's suites do. The test imports modules only
  (`cli, flow, integrate, publish, state`), never a symbol the fix adds, so the red leg
  loads and runs.
- **(c) Fixture includes the fault?** Yes. `main` really moves on origin mid-run (after the
  first fold, or after a bundle publishes). The held branch's base really holds the move
  (checked by ancestry). The stranded bundle really fails to merge onto main
  (`_merges("origin/main", "A") == 0`). Each fact is checked by plain git in a separate
  clone after the run. In the same-file probe Y really restores line 8; (3b)'s undo is a
  real `git rm` pushed to main; (2)'s fixup is a real fast-forward push to `fix/K`. For the
  stranded and past holds, the fixture also takes the advised steps (A rebuilt on main,
  either side kept; Y rebuilt on that; Y updated from main) and checks the branch then
  merges.

## Gates run here

- C4 `engine/scripts/run-verify.sh`: **PASS**. Green leg: 9 + 10 tests OK. Red leg: 1 + 6
  failures. Log: `.cache/c4.log` in the worktree.
- T3 `engine/scripts/run-suite.sh` on the final tree (under `timeout`): `PDCA-EVIDENCE: root
  suite OK, driver suite OK`. Root suite: 24 tests OK. Driver suite: 2635 tests OK (2
  skipped), including child-1's, child-2's, the same-wave suite (case (4)'s base-clash stop)
  and this patch's two files. Log: `.cache/t3.log`.
- Iteration-2 cross-check (above): `.cache/v2-run.log`, 4 failures of 19, all wording.
- Real hold lines printed by the patched code: `.cache/show-lines.log`.

## Commit-readiness

pdca-harness has no formatter, linter or commit hook: no `.pre-commit-config.yaml`, no
ruff/flake8/black settings in `template/pyproject.toml.jinja` or the workflows, only
`.sample` hooks, no `core.hooksPath`. CONTRIBUTING.md asks for a DCO sign-off (publish adds
it) and green offline and root suites. `git diff --check` is clean, `py_compile` passes on
all four files, and no added line is over 100 columns (the three longer lines in `flow.py`
are on the tip already, tip :211, :3197, :3392).

## Scratch left in the worktree (not in the patch)

All under `.cache/` (git-ignored, `.gitignore:11`): `patch-index`, `check-index` and
`v2-index` (scratch git indexes), `v2/` (a copy of `template/` with iteration 2's
production files), `v2-test_flow_cross_wave_*.py` (iteration 2's two test files, for the
line counts above),
`show_lines.py` (prints the hold lines a test run saw), and the logs `c4.log`, `t3.log`,
`v2-run.log`, `show-lines.log`. `py_compile` also wrote ignored `__pycache__/` files under
`template/`. Left for the harness to reclaim; nothing was removed.
