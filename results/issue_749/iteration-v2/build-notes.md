# Build notes — issue_749, iteration 2 (aim the fix at a line bundle stranded by a moved base)

Target: eduralph/pdca-harness, built on the run's line `pdca-integration/main-r547f8028520f`
at `2d18208` (#738, #747, #748 folded). "Tip" anchors below are on `2d18208`; "patched"
anchors are on the tree with `patch.diff` applied. `patch.diff` applies cleanly onto
`2d18208` (`git apply --check --cached` against a fresh index of that commit).

## What iteration 1 got wrong, and what changed

The carry-forward named four implementation findings. All four are fixed. Findings 1, 2 and
4 each have a test that fails on iteration 1's production code. I ran the new test file
against iteration-v1's `integrate.py`/`flow.py` in a scratch copy: the three new probes fail
there for exactly the reasons the reviewers gave, and the (1), (3d) and flip tests fail on
the old wording. Finding 3 removes a check that could never fire, so there is no behavior
to test.

1. **C5, same-file blame.** Iteration 1 tied a stranded partner to the clash by file name
   (`clash & set(files)`, v1 patched `integrate.py:1968`). Replaced by a trial pair per
   partner (patched `integrate.py:1993-2002`): the held branch's clash with the partner
   *as it is on the line* (`_trial(its, [*lead, head])`, :1996) against its clash with the
   partner *rebuilt on the base the branch holds*, partner's side winning
   (`_trial(rebuilt[name], [*lead, head])`, :1999). The partner counts only when the first
   clash has a file the second does not. The two trials differ in nothing but the
   partner's base, so a file that drops out is one where the move is what clashes. A
   partner the branch clashes with whose clash loses no file stops the fold (:2000-2001).
   The reviewer's probe is now
   `test_a_branch_that_takes_the_move_back_out_in_the_file_it_clashes_in_still_stops`: Y
   undoes main's line-8 change, so its clash with A is line 2 only; both trials conflict in
   `shared.txt` → stop, as before #749. On iteration 1 that test fails (Y was held, "rebuild
   issue_A's branch").
2. **Adversary: the "own" sub-case had no acceptance check.** Iteration 1 named `own` from
   single-bundle trials and returned (v1 `integrate.py:1989-2005`). Now the stranded path
   runs child-1's and child-2's rules again, unchanged, on the base the branch holds and on
   a line where every bundle that fails there is rebuilt on it (`_pinned` on `on_held`,
   patched `integrate.py:2013-2015`). That means `_partners`, then `_together` (pairs), each
   held to `_explains`, the "explains the whole clash" trial. With no partner named, the
   branch must merge onto that rebuilt line outright (`_explains(..., (), ...)`, :2016-2020),
   else stop. The adversary's P/R probe is now
   `test_a_stranded_partner_beside_a_clash_two_line_bundles_make_together_names_all`: the
   hold names A (stranded) and B, P, R (own), and the facts show the advice folds W. A
   three-bundle variant
   (`test_a_stranded_partner_beside_a_clash_three_line_bundles_make_still_stops`) pins the
   acceptance check: nothing names the rest, so the run stops. On iteration 1 both fail
   (W held naming only A and B).
3. **Dead guard.** `_trial(held, [*lead, head])` (v1 `integrate.py:1975-1976`) is gone. The
   brief's rule-(ii) condition "`_trial(S, [head])` clean" is true by construction (`S` is
   `git merge-base head <remote>/main`, an ancestor of head), so it is not run. The
   docstring says so (patched `integrate.py:1936-1937`). What separates stranded from an
   ordinary overlap is the trial pair in 1 and the acceptance in 2.
4. **Wording.** "does not merge cleanly onto origin/main, which issue_W's branch holds" →
   "does not merge cleanly onto the origin/main issue_W's branch holds" (patched
   `flow.py:1635-1637`), matching the `past` wording at :1629.

Deferred findings (12, `deferred-findings.json`) are not build work and were left as they
were. Two touch this code: the `past` outcome (kept, see (3b) below), and the (3c) reading
"not only A's rebuild" (still: no A rebuild is proposed when the branch does not hold the
move). Both are for the human.

## What changed (patched anchors)

**`integrate.py`**

- `fold` gets `moved: dict[str, BaseMove] | None` (patched :368), passed to
  `_held_by_line` at the child-1 call site (tip :663, patched :672-675). Docstring
  (patched :489-499).
- `BaseMove` (patched :1805): `base`, `stranded`, `past`, `own`.
- `_held_by_line` (tip :1796, patched :1831): computes `under` as before (tip :1839), runs
  child-1/child-2's rules through `_pinned`, and only when they name nobody and the branch
  merges onto the base alone (`kind in ("batch", "line")`, so never for child-1's base
  clash) calls `_held_by_move` (patched :1884-1889).
- `_pinned` (patched :1897): tip :1841-1851 moved unchanged into a function that takes the
  base, `under`, and `stay`.
- `_held_by_move` (patched :1924-2024): the re-try. `now` = bundles whose own change fails
  on the current base (child-1's rule (d) fails for them, tip `_partners` :2032-2034);
  `held` = `git merge-base head <remote>/main`; `lost` = those failing on `held`.
  - `lost` empty, `now` empty → None (no move in the clash; stop).
  - `lost` empty, `now` not → rule (i): `_pinned` on `held` (:1979-1984). Ordinary hold.
  - else: each lost bundle rebuilt on `held` by `_trial(held, [its], wins=0, made=…)`
    (:1985-1990), a merge with its side winning, never a squash (`_trial` tip :2079,
    `_merge_over` tip :1729). Own-change revs from child-2's `_own_change` (tip :1887) go
    before the head in both tie trials (:1991-1999).
  - tie per lost bundle the head clashes with (:1993-2002); none tied → None.
  - tied bundles split into `stranded` (fail on the current base too) and `past` (fit it);
    both at once → None (:2003-2006).
  - `past`: held only if head updated from the base merges onto the real line (:2007-2012,
    same acceptance as iteration 1).
  - `stranded`: `_pinned` on the rebuilt line with `stay=stranded` (:2013-2015), or the
    outright acceptance (:2016-2020); a lost bundle named in `own` that is not tied → None
    (:2021-2022).
- `_unfit` (patched :2027): as iteration 1, but returns names only (the files were only
  used by the dropped intersection).
- `_explains` (tip :1859, patched :2047): new keyword `stay`. A partner in it stays on the
  line and the head is tried rebuilt on it, exactly as for a prerequisite
  (`own = _prerequisites(cfg, d) | set(stay)`, patched :2059). Default `()`, so child-1's
  and child-2's calls are unchanged.

**`flow.py`** (structure as iteration 1; only the wording changed)

- `_moved_hold` (patched :1609) words a moved hold: `(what, step, wait)`.
- `_announce_conflict_holds` (tip :1569, patched :1663) and `_report_conflict_holds` (tip
  :1593, patched :1692) word a `moved` hold through it. Ordinary holds print byte-for-byte
  what they printed before (`_where`, patched :1590; `_overlap_step`, :1647).
- `_runnable`'s `Conflicts with` partner line (tip :856-863, patched :863-869) uses
  `_moved_hold`'s `what`/`wait` for a moved hold (case 3d).
- `_drive_and_act` keeps `held_moved` (patched :2853) beside `held_conflict` and passes it
  to `_runnable`, the fold (`moved=None if dry else held_moved`), both announce calls and
  the report.

## Brief case → path taken (folded tip vs patched)

| Case | Tip `2d18208` | Patched |
|---|---|---|
| (1) stranded W | `wave 1 did not integrate … STOPPING`, T never built | tie: A conflicts in `a.txt` as on the line, clean rebuilt → stranded; `_pinned` names nobody; outright acceptance clean → pure stranded hold. Exit 1 (V PLANNED) |
| (2) moved-on prerequisite K | held naming N only | unchanged: child-1 holds it in `_pinned` on the base; `_held_by_move` never runs (guard) |
| (3a) main moved twice | STOPPING | rule (i): A fails on main now (line 8) but fits `held` (m.txt only) → `_pinned(held)` names A, ordinary wording |
| (3b) main undid a commit | STOPPING on V, "declare the conflict / re-order" | `past` path, see below |
| (3c) Y does not hold the move | STOPPING | rule (i): `held` = the old main, A fits it → ordinary hold, `Conflicts with: A` |
| (3c) Y takes the move back out, other file | STOPPING | STOPPING (guard): A's clash files are `shared.txt` as on the line, `x.txt, shared.txt` rebuilt → no file lost → None |
| (3c) Y takes the move back out, same file (new) | STOPPING | STOPPING (guard): both trials conflict in `shared.txt` → None |
| (3d) X `Conflicts with: W` | STOPPING, X never reached | X held, waiting for "issue_A's branch is rebuilt on the new origin/main, and issue_W's PR merges" |
| P/R beside stranded A (new) | STOPPING | hold: A stranded; B, P, R own (child-2's pair search on the rebuilt line) |
| three-bundle beside stranded A (new) | STOPPING | STOPPING (guard): `_pinned` → partners {B}, `_explains` fails, `_together` adds nothing → None |
| (4) base clash, `test_a_conflict_only_with_a_base_taken_in_mid_wave_still_stops_the_run` | STOPPING | STOPPING: `_clash` says `"base"`, `_held_by_move` never runs (patched :1884) |
| (4) child-1's `…_whose_head_no_longer_fits_the_base_still_stops` | STOPPING | **flipped to a hold** (below) |

**Case (3b): the path it takes (the brief asks Do to state it).** On the folded tip, rule
(d) does *not* fail in (3b). A merges onto `origin/main` as it is now (main dropped its
`a.txt` again), so child-1's `_partners` names nobody and child-2's `_together` names nobody.
The run stops on V with the generic fold error ("an undeclared cross-wave overlap; declare
the conflict / re-order", tip `integrate.py:1347-1351`). The (i)–(iii) re-try never reaches
it. Patched, it takes the `past` branch: `now` is empty, `lost` = {A} on the main V holds,
and the tie holds (A conflicts in `a.txt` as on the line, clean rebuilt). The step is
trial-checked: V updated from `origin/main` merges onto the line (:2007-2012). The test then
performs the step (`StackFoldGit._update_branch("Y")`) and checks Y merges. This branch
widens the brief's gate. Both reviewers flagged it as a fourth outcome for the human to
accept (deferred items 2 and 3); I kept it unchanged because the (3b) assertion ("their step
is update the branch from <remote>/main") cannot be met on a path that stops.

**Case (4) flip — recorded as the brief asks.** child-1's
`test_a_clash_with_a_partner_whose_head_no_longer_fits_the_base_still_stops`
(`template/tests/test_flow_cross_wave_fold_holds.py`, tip line 402) is renamed
`test_a_clash_with_a_partner_whose_head_no_longer_fits_the_base_holds_it` (patched line 404)
and asserts a hold. Y holds main's `a.txt` (the move: tie holds, `a.txt` drops out once A
is rebuilt) and also changes `shared.txt` as A does (own overlap, named by child-1's
`_partners` on the rebuilt line). The hold names A as stranded and says "its change also
conflicts with issue_A's"; the end-of-run line adds the `Conflicts with: A` proposal. V is
`Stacks on: W`, cut from the line, so V holds A's old head. That is why the acceptance
keeps a stranded partner on the line (`stay`) instead of taking it off. I added two fixture
facts: V holds A, and with both steps taken (A rebuilt on main, Y rebuilt on that)
everything merges. Exit 3.

## What I tried and ruled out

- **Taking every own partner off the line in the acceptance (child-1's model for any
  non-prerequisite partner).** Ruled out because the flip test cannot pass with it. V,
  left on the line, was built on A, so `_explains`'s "brings back" check (tip
  `integrate.py:1872-1874`) fails and the flip stays a stop. Checked by a scratch run with
  `stay=()` in both stranded-path calls (`.cache/nostay/`): 18 of the 19 tests in the two
  files still pass, and the flip test fails with `wave 1 did not integrate … STOPPING`. So
  `stay` matters for exactly the case where the stranded partner is also an own partner.
  It costs 1 changed line (`own = _prerequisites(cfg, d) | set(stay)`) plus a keyword and 3
  docstring lines in `_explains`, and 2 passes in `_pinned`. It models the step the hold
  gives: the stranded partner stays (rebuilt by its owner) and the held branch is rebuilt
  on it.
- **Hunk-level comparison for the tie** (parse conflict regions instead of comparing file
  sets). Not done. The tie stays a yes/no-plus-files result of two `_trial` calls, the
  house style ("decided by trial merges … never by which files or hunks clash",
  `_together`'s docstring, tip :1922-1923). The cost of the file-level choice is a known
  limit, below. It errs toward a stop, never toward wrong advice.
- **Calling the same-file probe an ordinary overlap hold** (naming A, `Conflicts with: A`)
  instead of stopping. Ruled out: the brief's rule (i) needs every partner to merge onto
  `S` alone, and A does not; rule (iii) says anything else stops.
- **Iteration 1's line-wins trial** (`_trial(held, [*lead, tip, head], wins=len(lead))`).
  Dropped. It could say "the move explains everything" but could not attribute the rest,
  which is finding 2. The `_pinned` re-run on the rebuilt line covers both.
- **A squash, or a second trial-worktree helper.** Not used, as the brief requires. The
  rebuild is `_trial`'s existing `wins`/`made`. No change to `_trial`.
- **Pinning bases to the run's start.** Not done (stated non-change). The tests assert only
  that the held bundle's base holds the moved main (`self.seen["issue_W"][1]`).

Cost of the re-try, per fold conflict that no earlier rule pinned (n bundles on the line, k
of them failing on the base the branch holds): 2n trials (`_unfit` on the base and on
`held`; n when `held` is the base), then 3k (rebuild and two tie trials). After that, one
`_pinned` pass (1 + n + 1 trials, plus `_together`'s up to n + n(n−1)/2, plus at most 2
acceptance trials), or 1 outright acceptance, or 2 for `past`. All of it runs only after a
fold merge has already conflicted, which today stops the run.

## Known limits (each stops the run, as today; none gives a wrong step)

- **File granularity of the tie.** When the move's clash with a partner and the branch's own
  clash with it fall in the same file, no file drops out, so the partner is not shown to be
  stranded and the fold stops. Example: A edits lines 2 and 8, main edits line 8, the
  branch keeps main's line 8 and edits line 2. The different-file version (the flip test)
  holds.
- **The branch changes a move spot further** (main adds `a.txt`, the branch edits main's
  `a.txt`). Both tie trials conflict in `a.txt`, so it stops. Right: whether A's rebuild
  fixes it depends on which side A's owner keeps.
- **Stranded and past bundles in one clash** → stop. So does a clash the move puts no
  bundle in (`tied` empty), and a lost bundle that an own trial names but the tie does not.
- **A stranded bundle the branch does not clash with** is rebuilt for the acceptance (its
  owner's business) and never named.

## Refute-your-own-test (forced)

- **(a) Genuine red?** Yes. `engine/scripts/run-verify.sh` (PDCA_BUNDLE and PDCA_WORKTREE
  set) reverts the production hunks: 7 tests fail and the gate reports
  `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`. The 7 are case (1), (3a),
  (3b), (3c), (3d), the P/R case, and child-1's flipped test. Every failure is
  `'did not integrate' unexpectedly found in "flow: wave 1 did not integrate (issue_<X>'s
  branch … STOPPING"`, the pre-fix stop. The four guards — (2), both take-the-move-back-out
  cases, and the three-bundle case — pass both ways, as the brief expects for (2). Against
  iteration 1's production code instead, the same-file, three-bundle and P/R tests fail.
  So they pin the C5 and adversary findings, not just this tree.
- **(b) Production path?** Yes. Each test calls `flow._drive_and_act` with the real
  `integrate.fold` → `_held_by_line` → `_held_by_move`, real git (bare origin, primary
  checkout, scratch clone), real base builds, and the real exit-code rule `cli._results_rc`.
  Only the build leaf, publish's branch cut and `gh` are stubbed, exactly as child-1's and
  child-2's suites do. The test imports modules only (`cli, flow, integrate, publish,
  state`), never a symbol the fix adds, so the red leg loads and runs.
- **(c) Fixture includes the fault?** Yes. `main` really moves on origin mid-run (after the
  first fold, or after a bundle publishes). The held branch's base really holds the move
  (asserted by ancestry). The stranded bundle really fails to merge onto main
  (`_merges("origin/main", "A") == 0`). Each fact is checked by plain git in a separate
  clone after the run. Y really restores line 8 in the same-file probe; (3b)'s undo is a
  real `git rm` pushed to main; (2)'s fixup is a real fast-forward push to `fix/K`. For the
  stranded and past holds, the fixture also performs the advised steps (A rebuilt on main,
  either side kept; Y rebuilt on that; Y updated from main) and checks the branch then
  merges.

## Gates run here

- C4 `engine/scripts/run-verify.sh`: **PASS** (green 9 + 10 tests OK; red 1 + 6 failures).
- T3 `engine/scripts/run-suite.sh` on the final tree: `PDCA-EVIDENCE: root suite OK, driver
  suite OK`. Root suite: 24 tests OK. Driver suite: 2635 tests OK (2 skipped), including
  child-1's, child-2's and the same-wave suites.
- During development I ran single modules with the runner's own invocation
  (`cd template && PYTHONPATH=src python3 -m unittest tests.<module>`) under a `timeout`.
  95 tests across the stranded, child-1, child-2, same-wave and stack-bases suites: OK.
- Scratch probes, not shipped (`.cache/probe/template/tests/probe_749.py`), on the patched
  code:
  - The branch edits main's version of the moved file: stops.
  - Two stranded partners: one hold, "issue_A1's, issue_A2's branches … do not merge
    cleanly onto the origin/main issue_W's branch holds: origin/main moved since they were
    cut".
  - Stranded A plus an ordinary overlap with Q: a hold naming A stranded and Q, with
    `Conflicts with: Q`.
  - A line bundle built on the stranded one (P2 on P1): a hold naming P1 only.
  - The same-file mixed case from the limits above: stops.

## Commit-readiness

pdca-harness has no formatter or linter config and no commit hook: no
`.pre-commit-config.yaml`, no ruff/flake8/black settings in `template/pyproject.toml.jinja`,
only `.sample` hooks, no `core.hooksPath`. CONTRIBUTING.md asks for a DCO sign-off (publish
adds it) and green offline and root suites. `git diff --check` is clean, and no added line
is over 100 columns, the same as the surrounding code.

## Scratch left in the worktree (not in the patch)

All under `.cache/` (git-ignored, `.gitignore:11`): `v1/`, `red/`, `nostay/` and `probe/`
(copies of `template/` with iteration 1's production files, the folded tip's, this patch
with `stay` off, and this patch plus the scratch probes, used for the cross-checks above),
`new_held_by_move.py.txt`, `verify-index`, `c4.log`, `t3.log`, `after-c4.diff`.
Left for the harness to reclaim. One slip to own: before writing a fresh scratch index I ran
`rm -f .cache/verify-index` on a scratch index file there (possibly iteration 1's, which its
notes list). Nothing else was removed.
