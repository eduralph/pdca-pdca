# Build notes — issue_749, iteration 4 (aim the fix at a line bundle stranded by a moved base)

Target: eduralph/pdca-harness. Built on the run's line `pdca-integration/main-r547f8028520f`
at `2d18208` (#738, #747, #748 folded; `stack-base-tip`; the worktree HEAD). "Tip" anchors
are on `2d18208`. "Patched" anchors are on that tree with `patch.diff` applied. I applied
iteration 3's patch to the clean worktree (it applied cleanly), made the changes below, and
wrote `patch.diff` from a scratch git index built from `HEAD` (the real index was not
touched). `patch.diff` applies cleanly onto `2d18208`.

## The carry-forward, and what changed in this iteration

The one build finding (iteration 3's code review): two wordings in `_moved_hold` that a
`Conflicts with` partner sees were never tested. (1) The `past` wait text,
"{name}'s branch is updated from {base}" (patched `flow.py:1632`), which reaches
`_runnable`'s partner line (patched `flow.py:863-869`). (2) The stranded-plus-own wait text
(iteration 3's `flow.py:1642`, now `:1643`). Case (3d) only covered a stranded hold with an
empty `own`.

1. **A partner test for (1)**, the shape the reviewer suggested: case (3b) plus an X that
   declares `Conflicts with: V`.
   `test_a_conflicts_with_partner_of_a_past_hold_waits_for_the_branch_update`
   (`template/tests/test_flow_cross_wave_stranded_holds.py:638`). (3b)'s setup moved,
   unchanged, into `_undone_run(with_x)` (`:468`), the same pattern as case (1)'s
   `_stranded_run(with_x)` (`:334`). The (3b) test (`:500`) calls it with `with_x=False` and
   keeps every assertion it had. X needs no `Depends on`: the scheduler orders a
   `Conflicts with` pair by name, lower id first (`waves.py:205-212`), so X goes in wave 2,
   after the fold that holds V. The test checks X's one line: V's reason (the `past` clause)
   and "To build it, wait until issue_V's branch is updated from origin/main, and issue_V's
   PR merges into main (org/repo), then re-run." It also checks that the line has none of
   "its change", "rebuild issue_A's branch", "issue_V is rebuilt", "a base that holds",
   "Conflicts with: A" or "issue_Y". Then it takes the step X waits for
   (`StackFoldGit._update_branch("V")`) and checks that V then merges onto the line.
2. **A partner test for (2)**:
   `test_a_conflicts_with_partner_of_a_stranded_hold_with_an_own_clash_waits_for_both`
   (`:668`). It is #747's flipped case (`test_flow_cross_wave_fold_holds.py:404`) plus Z,
   which declares `Conflicts with: Y`. I used Z, not X, because of the same name rule:
   `issue_X < issue_Y`, so X would build first (wave 0), before Y is held, and never reach
   the partner line. The test checks Z's one line: Y's reason (stranded clause plus "and
   issue_Y's own change also conflicts with issue_A's, already on the line") and "To build
   it, wait until issue_A's branch is rebuilt on the new origin/main, issue_Y is rebuilt on a
   base that holds issue_A, and issue_Y's PR merges into main (org/repo), then re-run." It
   also checks two fixture facts with plain git. A rebuilt on main alone does not fold Y
   (`_merges(..., rebuilt, "Y") == 1`), which is why Z must wait for Y's rebuild too. With
   both steps taken (Y rebuilt on A's rebuild) everything merges. The new helper `_rebuilt`
   (`:319`) is a copy of child-1's (`test_flow_cross_wave_fold_holds.py:276`), as these test
   files each keep their own helpers.
3. **The wording nit from the same review, fixed**, because test 2 pins exactly that text.
   Z's line used to read "wait until issue_A's branch is rebuilt on the new origin/main,
   **and** issue_Y is rebuilt on a base that holds issue_A, **and** issue_Y's PR merges",
   two "and"s in a row. Now it is a plain list: "…on the new origin/main, issue_Y is rebuilt
   on a base that holds issue_A, and issue_Y's PR merges…". The change is one word removed
   at patched `flow.py:1643`, plus a one-line comment at `:1642` saying why there is no
   "and" (`_runnable` adds the last item). Only `_runnable` reads the wait text:
   `_announce_conflict_holds` and `_report_conflict_holds` drop it (`_wait`, patched
   `flow.py:1683`, `:1705`). So no hold line and no end-of-run line changes, and no other
   test asserted the old text (grep for "is rebuilt on a base that holds" in `template/`).
4. **Docstring.** The test module's docstring now lists both partner cases (`:22-26`).
5. **Nothing else changed.** `integrate.py` and `test_flow_cross_wave_fold_holds.py` are
   byte-identical to iteration 3's (same blob ids). Against iteration 3, `flow.py` is +2/−1
   and the stranded test file +116/−10. The deferred findings in `deferred-findings.json`
   need the human's judgment and are not build work, so they are untouched.

Real partner lines from this iteration's run (the patched code):

> flow: issue_X held — it `Conflicts with` issue_V, which this run's fold held out of the
> line (issue_A's branch, already on the line, does not merge cleanly onto the origin/main
> issue_V's branch holds, but does onto origin/main as it is now: origin/main has moved on
> since issue_V's branch was built), so no line of this run holds that work; not built on a
> base missing it. To build it, wait until issue_V's branch is updated from origin/main, and
> issue_V's PR merges into main (org/repo), then re-run.

> flow: issue_Z held — it `Conflicts with` issue_Y, which this run's fold held out of the
> line (issue_A's branch, already on the line, does not merge cleanly onto the origin/main
> issue_Y's branch holds: origin/main moved since it was cut; and issue_Y's own change also
> conflicts with issue_A's, already on the line), so no line of this run holds that work;
> not built on a base missing it. To build it, wait until issue_A's branch is rebuilt on the
> new origin/main, issue_Y is rebuilt on a base that holds issue_A, and issue_Y's PR merges
> into main (org/repo), then re-run.

**The new tests bind the code the finding names**, checked three ways:

- **Against iteration 3's production code** (C4 runner on a dev patch with only the new
  tests added): 11 of 12 stranded tests pass, and test 2 fails on exactly the double "and".
  Its real line was "…on the new origin/main, and issue_Y is rebuilt on a base that holds
  issue_A, and issue_Y's PR merges…". Test 1 passes there, as it should: it pins wording
  iteration 3 already had. Log: `.cache/pre-nit.log` in the worktree.
- **With `_runnable`'s moved-hold branch switched off** (patched `flow.py:863` changed to
  `if False and …` for one C4 run, then restored; `cmp` with a saved copy confirms the
  restore). Exactly three tests fail: (3d) and both new ones. Everything else passes. The
  partner then gets the ordinary line, which blames the wrong owner: "issue_X held — it
  `Conflicts with` issue_V, which this run's fold held out of the line (its change
  conflicts with issue_A's) … wait until issue_V is rebuilt on a base that holds issue_A and
  its PR merges", and the same for Z and Y. Log: `.cache/mutation-runnable.log`.
- **With the whole production change reverted** (the C4 red leg): both new tests fail on
  the old stop, `'did not integrate' unexpectedly found in "flow: wave 1 did not integrate
  (issue_V's branch … (conflicts in a.txt) … STOPPING"` (for Z's test: issue_Y's branch,
  conflicts in a.txt, shared.txt).

What I left as it is, and why:

- **The own list is joined with plain commas** (`', '.join(move.own)`), as the ordinary
  partner line does (patched `flow.py:874`). With several own partners the list runs into
  the ", and …'s PR merges" tail: "…a base that holds issue_B, issue_P, issue_R, and
  issue_W's PR merges". The ordinary line has the same shape ("…holds issue_B, issue_P,
  issue_R and its PR merges"). The reviewer called the join consistent. Changing both means
  rewording #674's line and the suites that assert it, which is not this round's finding.
- **`lead` computed twice** (`integrate.py:1991` repeats the `_own_change` call inside
  `_unfit`). The reviewer said to leave it unless `_unfit` changes; it does not.

## What the patch does (as iteration 3, apart from the wording above)

**`integrate.py`** (byte-identical to iteration 3)

- `fold` gets `moved: dict[str, BaseMove] | None` (patched :368). It is passed to
  `_held_by_line` at child-1's rule-(d) call site (tip :663-666, patched :672-675).
- `BaseMove` (patched :1805): `base`, `stranded`, `past`, `own`.
- `_held_by_line` (tip :1796, patched :1831) runs child-1's and child-2's rules through
  `_pinned`. Only when they name nobody, and the branch merges onto the base alone
  (`kind in ("batch", "line")`, so never for a base clash), does it call `_held_by_move`
  (patched :1883-1889).
- `_pinned` (patched :1897): tip :1841-1851 moved unchanged into a function that takes the
  base, `under`, and `stay`.
- `_held_by_move` (patched :1924-2024) is the re-try. `now` = the bundles whose own change
  fails on the current base, i.e. the ones child-1's rule (d) skips (tip `_partners` :2016).
  `held` = `git merge-base head <remote>/main` (:1976), the brief's `S`. `lost` = the ones
  failing on `held` (:1978).
  - `lost` and `now` both empty → None: no move in the clash, so the run stops (:1979-1981).
  - `lost` empty, `now` not → rule (i): `_pinned` on `held` (:1982-1984), an ordinary hold.
  - Otherwise each lost bundle is rebuilt on `held` with `_trial(held, [its], wins=0,
    made=…)` (:1985-1990): a merge with its side winning, never a squash (`_trial`, tip
    :2079, patched :2269). child-2's `_own_change` (tip :1887, patched :2077) goes before
    the head in both tie trials (:1991).
  - Tie per lost bundle the head clashes with (:1993-2002): the head's clash with the
    bundle as it is on the line, against its clash with the bundle rebuilt on `held`. The
    bundle counts only if the first clash has a file the second does not. A clash that loses
    no file → None.
  - The tied bundles split into `stranded` (they fail on the current base too) and `past`
    (they fit it). Both at once, or none tied → None (:2003-2006).
  - `past` (:2007-2012): held only if the head, updated from the base, merges onto the line.
  - `stranded` (:2013-2022): `_pinned` again on the rebuilt line with `stay=stranded`
    (:2015), or, with no one named, the outright check that the head merges onto that line
    (:2016-2020). An own partner that was rebuilt but not tied → None (:2021-2022).
- `_unfit` (patched :2027): the trials behind `now` and `lost`.
- `_explains` (tip :1859, patched :2047) gets a keyword `stay` (a bundle in it stays on the
  line, as a prerequisite does). The default `()` leaves child-1's and child-2's calls as
  they were.

**`flow.py`**

- `_moved_hold` (patched :1609) words a moved hold as `(what, step, wait)`; the `past` wait
  at :1632, the stranded wait at :1638, its own-clash part at :1639-1643 (this iteration's
  change at :1642-1643).
- `_announce_conflict_holds` (tip :1569, patched :1665) and `_report_conflict_holds` (tip
  :1593, patched :1695) word a moved hold through it. Ordinary holds print byte for byte
  what they printed before (`_where`, patched :1590; `_overlap_step`, :1649).
- `_runnable`'s `Conflicts with` partner line (tip :856-863, patched :861-869) uses
  `_moved_hold`'s `what`/`wait` for a moved hold (cases (3d) and this iteration's two).
- `_drive_and_act` keeps `held_moved` (patched :2856) beside `held_conflict` and passes it
  to `_runnable` (:2989), the fold (`moved=None if dry else held_moved`, :3164), both
  announce calls (:3169, :3177) and the report (:3204).

## Brief case → path taken (folded tip vs patched)

| Case | Tip `2d18208` | Patched |
|---|---|---|
| (1) stranded W (`:366`) | `wave 1 did not integrate … STOPPING`, T never built | tie: A clashes in `a.txt` as on the line, clean once rebuilt → stranded; `_pinned` names nobody; outright check clean → pure stranded hold. Exit 1 (V PLANNED) |
| (2) moved-on prerequisite K (`:394`) | held naming N only | unchanged: child-1 holds it in `_pinned` on the base; `_held_by_move` never runs (guard) |
| (3a) main moved twice (`:433`) | STOPPING | rule (i): A fails on main now (line 8) but fits `held` (m.txt only) → `_pinned(held)` names A, ordinary wording |
| (3b) main undid a commit (`:500`) | STOPPING on V, "declare the conflict / re-order" | `past` path, see below |
| (3c) Y does not hold the move (`:525`) | STOPPING | rule (i): `held` is the old main, A fits it → ordinary hold, `Conflicts with: A` |
| (3c) Y takes the move back out, other file (`:558`) | STOPPING | STOPPING (guard): no file drops out of the clash → None |
| (3c) Y takes the move back out, same file (`:584`) | STOPPING | STOPPING (guard): both trials conflict in `shared.txt` → None |
| (3d) X `Conflicts with: W` (`:613`) | STOPPING, X never reached | X held, waiting for "issue_A's branch is rebuilt on the new origin/main, and issue_W's PR merges" |
| **new:** X `Conflicts with: V`, a `past` hold (`:638`) | STOPPING on V, X never reached | X held, waiting for "issue_V's branch is updated from origin/main, and issue_V's PR merges" |
| **new:** Z `Conflicts with: Y`, stranded plus own (`:668`) | STOPPING on Y, Z never reached | Z held, waiting for "issue_A's branch is rebuilt on the new origin/main, issue_Y is rebuilt on a base that holds issue_A, and issue_Y's PR merges" |
| P/R beside stranded A (`:750`) | STOPPING | hold: A stranded; B, P, R own (child-2's pair search on the rebuilt line) |
| three bundles beside stranded A (`:784`) | STOPPING | STOPPING (guard): nothing explains the rest → None |
| (4) base clash, `test_flow_same_wave_conflict.py:435` | STOPPING | STOPPING: `_clash` says `"base"`, `_held_by_move` never runs (patched `integrate.py:1884`) |
| (4) child-1's flipped test (`test_flow_cross_wave_fold_holds.py`, tip :402) | STOPPING | **hold** (below) |

**Case (3b): the path it takes (the brief asks Do to say).** On the folded tip, rule (d)
does *not* fail in (3b): A merges onto `origin/main` as it is now (main dropped its `a.txt`
again), so child-1's `_partners` and child-2's `_together` name nobody, and the run stops on
V with the generic fold error ("an undeclared cross-wave overlap; declare the conflict /
re-order", seen in this iteration's C4 red leg). The (i)-(iii) re-try is never reached.
Patched, it takes the `past` branch: `now` is empty, `lost` = {A} on the main V holds, and
the tie holds (A clashes in `a.txt` as on the line, clean once rebuilt). The step is
trial-checked: V updated from `origin/main` merges onto the line (patched
`integrate.py:2007-2012`). The (3b) test takes the step for Y, and this iteration's partner
test takes it for V; each then merges. This branch goes beyond the brief's (i)-(iii). Both
iteration-3 reviewers flagged it as a fourth outcome for the human to accept (deferred). I
kept it because the (3b) assertion ("their step is update the branch from <remote>/main")
cannot be met on a path that stops.

**Case (4) flip, recorded as the brief asks.** child-1's
`test_a_clash_with_a_partner_whose_head_no_longer_fits_the_base_still_stops`
(`template/tests/test_flow_cross_wave_fold_holds.py`, tip :402) is renamed
`test_a_clash_with_a_partner_whose_head_no_longer_fits_the_base_holds_it` (patched :404) and
asserts a hold. Y holds main's `a.txt` (the move: the tie holds, `a.txt` drops out once A is
rebuilt) and also changes `shared.txt` as A does (an own overlap, named by child-1's
`_partners` on the rebuilt line). The hold names A as stranded and says "issue_Y's own change
also conflicts with issue_A's"; the end-of-run line adds the `Conflicts with: A` proposal. V
is `Stacks on: W`, cut from the line, so V holds A's old head; that is why the check keeps a
stranded partner on the line (`stay`). The test checks with plain git that V holds A, and
that with both steps taken (A rebuilt on main, Y rebuilt on that) everything merges. Exit 3.
This iteration's Z test is the same shape with a partner added.

## What I tried and ruled out

This iteration:

- **Adding only the `past` partner test** (the reviewer's one concrete suggestion). Ruled
  out: the finding names two untested wordings, and the stranded-plus-own wait is the one
  hold that does blame the held bundle, so its partner line is the one most worth pinning.
  Cost of the second test: the test itself (48 lines, `:668-715`) and the 12-line
  `_rebuilt` helper it uses (`:319-330`), each with a blank line; nothing in production.
- **Putting the Z test in child-1's file**, next to the flipped test, to reuse its fixture
  code directly. Not done: the brief names the stranded file as this child's test file, and
  the setup is 10 lines, so copying it costs less than splitting #749's partner tests over
  two files.
- **Using X for the second partner, as the other partner tests do.** It cannot work:
  `waves.compute_waves` orients a `Conflicts with` pair so the name-lower id builds first
  (`waves.py:205-212`), and `issue_X < issue_Y`, so X would be built in wave 0, before the
  fold that holds Y. Z sorts after Y.
- **Leaving the double "and" and pinning it as it was.** Ruled out: the new test would then
  lock in wording the reviewer had already called clumsy. The fix is one word.
- **Rewording the list so the own ids cannot run into the tail** (for example "Y is
  rebuilt on a base that holds A; then Y's PR merges"). Not done: `_runnable` builds the
  tail the same way for every partner line (patched `flow.py:867-868`, `:873-875`, and #629
  / #738's lines), so a change there is a wording change across #674's and #738's lines and
  their suites, beyond this finding.

Kept from iterations 2 and 3:

- **Taking every own partner off the line in the check** (child-1's model for any partner
  that is not a prerequisite). The flipped test cannot pass with it: V, left on the line,
  was built on A, so `_explains`'s "brings back" check (tip `integrate.py:1872-1874`) fails
  and the flip stays a stop. `stay` costs 1 changed line, a keyword and 3 docstring lines in
  `_explains`, and 2 passes in `_pinned`.
- **Comparing conflict hunks for the tie** instead of file sets. Not done. The tie stays a
  pair of `_trial` results, the house style ("decided by trial merges … never by which
  files or hunks clash", `_together`'s docstring, tip :1922-1923). Its known limit (below)
  errs toward a stop, never toward wrong advice.
- **Iteration 1's line-wins trial, a squash, a second trial-worktree helper.** None used.
  The rebuild is `_trial`'s existing `wins`/`made`; `_trial` is unchanged.
- **Pinning bases to the run's start.** Not done (stated non-change). The tests assert only
  that the held bundle's base holds the moved main (`self.seen["issue_W"][1]`).

Cost of the re-try, per fold conflict no earlier rule pinned (n bundles on the line, k of
them failing on the base the branch holds): 2n trials (`_unfit` on the base and on `held`;
n when they are the same), then 3k (rebuild and two tie trials), then one `_pinned` pass
(1 + n + 1 trials, plus `_together`'s up to n + n(n−1)/2, plus at most 2 checks), or 1
outright check, or 2 for `past`. All of it runs only after a fold merge has already
conflicted, which on the tip stops the run.

## Known limits (each stops the run, as today; none gives a wrong step)

- **File granularity of the tie.** When the move's clash with a partner and the branch's own
  clash with it are in the same file, no file drops out, so the partner is not shown to be
  stranded and the fold stops. Example (iteration 3's adversary, deferred for the human): A
  edits lines 2 and 8, main edits line 8, the branch keeps main's line 8 and edits line 2.
  The two-file version (the flipped test, and this iteration's Z test) holds. No test pins
  the one-file stop on purpose: the human is to decide whether it stays a stop.
- **The branch changes a moved spot further** (main adds `a.txt`, the branch edits main's
  `a.txt`): both tie trials conflict in `a.txt`, so it stops. Right: whether A's rebuild
  fixes it depends on which side A's owner keeps.
- **Stranded and past bundles in one clash** → stop. So does a clash the move puts no bundle
  in, and a lost bundle an own trial names but the tie does not.
- **A stranded bundle the branch does not clash with** is rebuilt for the check (its owner's
  business) and never named.

## Refute-your-own-test (forced)

- **(a) Genuine red?** Yes. `engine/scripts/run-verify.sh` (PDCA_BUNDLE and PDCA_WORKTREE
  set, under `timeout`) reverts the production hunks: 9 tests fail and the gate prints
  `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`. The 9 are case (1), (3a),
  (3b), (3c), (3d), both new partner tests, the P/R case, and child-1's flipped test. Each
  fails with `'did not integrate' unexpectedly found in "flow: wave 1 did not integrate
  (issue_<X>'s branch … STOPPING"`, the pre-fix stop. The four guards ((2), both
  take-the-move-back-out cases, the three-bundle case) pass both ways, as the brief expects
  for (2). For this iteration's change on its own: against iteration 3's production code
  the Z test fails on the double "and"; with `_runnable`'s moved-hold branch switched off,
  (3d) and both new tests fail (above).
- **(b) Production path?** Yes. Each test calls `flow._drive_and_act`, which runs the real
  `integrate.fold` → `_held_by_line` → `_held_by_move`, then the real `_runnable` for the
  next wave, on real git (bare origin, primary checkout, scratch clone), with real base
  builds and the real exit-code rule `cli._results_rc`. The partner lines checked are the
  ones `_runnable` really prints to stderr. Only the build leaf, publish's branch cut and
  `gh` are stubbed, as child-1's and child-2's suites do. The test imports modules only
  (`cli, flow, integrate, publish, state`), never a symbol the fix adds, so the red leg
  loads and runs.
- **(c) Fixture includes the fault?** Yes. `main` really moves on origin mid-run (after the
  first fold, or after a bundle publishes), and the held branch's base really holds the
  move (checked by ancestry). In the X test main's undo is a real `git rm` pushed to main,
  and A really fits main as it is now but not the main V holds. In the Z test A really fails
  onto main, and A rebuilt on main really still clashes with Y. The partners are real
  bundles with real `Conflicts with` lines in their briefs, scheduled by the real
  `waves.compute_waves`. Each fact is checked by plain git in a separate clone after the
  run, and both tests take the step the partner waits for and check that the held branch
  then merges.

## Gates run here

- C4 `engine/scripts/run-verify.sh`: **PASS**. Green leg: 9 + 12 tests OK. Red leg: 1 + 8
  failures. Log: `.cache/c4.log` in the worktree.
- T3 `engine/scripts/run-suite.sh` on the final tree (under `timeout`): `PDCA-EVIDENCE: root
  suite OK, driver suite OK`. Root suite: 24 tests OK. Driver suite: 2637 tests OK (2
  skipped; iteration 3 had 2635, the 2 more are this iteration's tests), including child-1's,
  child-2's, the same-wave suite (case (4)'s base-clash stop) and this patch's two files.
  Log: `.cache/t3.log`.
- Against iteration 3's production code: `.cache/pre-nit.log` (11 of 12 pass; the Z test
  fails on the double "and").
- `_runnable` moved-hold branch switched off: `.cache/mutation-runnable.log` (3 fail).

## Commit-readiness

pdca-harness has no formatter, linter or commit hook: no `.pre-commit-config.yaml`, no
ruff/flake8/black settings in `template/pyproject.toml.jinja` or the workflows, only
`.sample` hooks, no `core.hooksPath` (checked again this iteration). CONTRIBUTING.md asks for
a DCO sign-off (publish adds it) and green offline and root suites. `git diff --check` and
`git apply --check --whitespace=error-all` are clean, `py_compile` passes on all four files,
and no added line is over 100 columns.

## Scratch left in the worktree (not in the patch)

All under `.cache/` (git-ignored, `.gitignore:11`): the scratch git indexes `dev-index`,
`mut-index`, `v3-index`; `dev-bundle/patch.diff` and `mut-bundle/patch.diff` (the patches
the C4 runner read for the dev and mutation runs); `flow.py.keep` (the copy the mutation was
restored from); `now.diff`; and the logs `pre-nit.log`, `c4.log`, `mutation-runnable.log`,
`t3.log`. `py_compile` and the test runs also wrote ignored `__pycache__/` files under
`template/`. Left for the harness to reclaim; nothing was removed.
