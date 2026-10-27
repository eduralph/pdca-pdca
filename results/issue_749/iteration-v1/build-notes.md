# Build notes — issue_749 (aim the fix at a line bundle stranded by a moved base)

Target: eduralph/pdca-harness, built on the run's line `pdca-integration/main-r547f8028520f`
at `2d18208` (#738, #747, #748 folded). Line anchors below are on `2d18208` unless marked
"patched" (the tree with `patch.diff` applied).

## What changed

**integrate.py**

- `_held_by_line` (2d18208 `integrate.py:1796`; patched `:1827`) is split. Its two rules
  (child-1's #747 rules, child-2's #748 joint search) move unchanged into `_pinned`
  (patched `integrate.py:1891`), which takes the base as a parameter, so they can be run
  again on another base. `_held_by_line` builds `on` as before, calls `_pinned` on the
  current base, and only when that names nobody **and** the branch merges onto the base
  alone (`kind in ("batch", "line")`, i.e. not child-1's base clash at 2d18208
  `integrate.py:1845`) calls the new `_held_by_move`.
- `_held_by_move` (patched `integrate.py:1914`) is the re-try the brief asks for:
  - `now` = line bundles whose own change does not merge onto the current
    `<remote>/main` (child-1's rule (d) fails for these). Found by the new `_unfit`
    (patched `integrate.py:2008`), which runs child-2's `_own_change` (2d18208
    `integrate.py:1887`) first, then what the bundle was built on (`_built_on`,
    `integrate.py:2044`), then its head, all through `_trial` (`integrate.py:2079`).
  - `held` = `S = git merge-base <head> <remote>/main`; `lost` = `_unfit` on `S`.
  - **(i)** `lost` empty and `now` not empty → `_pinned` on `S`: the ordinary overlap,
    worded as child-1 words it (case 3a, 3c).
  - `lost` and `now` both empty → None: stop, as today.
  - **(ii)** a bundle in `lost ∩ now` → stranded. Hold naming it and `<remote>/main`, fix
    aimed at that bundle's owner.
  - a bundle in `lost − now` (fails on `S`, fits the current base) → "past": the step is
    the held bundle's, "update <its> branch from <remote>/main" (case 3b, see below).
  - **(iii)** anything else → None, the fold stops as today.
- `BaseMove` (patched `integrate.py:1803`): the record the flow words the hold from
  (`base`, `stranded`, `past`, `own`). `fold` gets a `moved` out-parameter (patched
  `integrate.py:368`) and passes it to `_held_by_line` (patched `integrate.py:673`).

**flow.py**

- `_announce_conflict_holds` (2d18208 `flow.py:1569`; patched `:1663`) and
  `_report_conflict_holds` (2d18208 `flow.py:1593`; patched `:1692`) word a `moved` hold
  through the new `_moved_hold` (patched `flow.py:1609`). The "where is the partner"
  grouping child-1 wrote inline moved into `_where` (patched `flow.py:1590`); the end-of-run
  step child-1 wrote inline moved into `_overlap_step` (patched `flow.py:1647`). Ordinary
  holds print byte-for-byte what they printed before (child-1's and child-2's suites pin
  the strings and stay green).
- `_runnable`'s line for a `Conflicts with` partner (2d18208 `flow.py:856`; patched `:863`)
  uses `_moved_hold`'s `what`/`wait` for a moved hold, so X waits for A's rebuild and is
  never told W's change clashes or that W is to be rebuilt (case 3d).
- `_drive_and_act` keeps `held_moved` beside `held_conflict` (patched `flow.py:2853`) and
  passes it to `_runnable` (`:2986`), the fold (`:3161`), both announce calls (`:3166`,
  `:3174`) and the report.

## Brief case → path taken (patched tree)

| Case | Folded tip (before) | With the patch |
|---|---|---|
| (1) stranded W | `wave 1 did not integrate (issue_W's …) STOPPING` | (ii): `A` fails on `S = M1` and on main, in `a.txt` (the clash's file); line-winning trial is clean → pure stranded hold |
| (2) moved-on prerequisite K | held, naming `issue_N` only | unchanged: child-1 holds it in `_pinned` before `_held_by_move` runs (a guard) |
| (3a) main moved twice | STOPPING | (i): `A` fails on main now (line 8) but fits `S` (m.txt only) → `_pinned(S)` names `A`, ordinary wording |
| (3b) main undid a commit | STOPPING on `V`, "declare the conflict / re-order" | "past" branch, see below |
| (3c) Y does not hold the move | STOPPING | (i): `S = M0`, `A` fits it → ordinary hold, `Conflicts with: A` |
| (3c) second test, Y takes the move back out | STOPPING | still STOPPING (a guard): `A` fails on `S` only in `x.txt`, Y's clash is only `shared.txt` → "not in this clash" → None |
| (3d) X `Conflicts with: W` | STOPPING, X never reached | X held, waiting for "issue_A's branch is rebuilt on the new origin/main" |
| (4) base clash (`test_a_conflict_only_with_a_base_taken_in_mid_wave_still_stops_the_run`) | STOPPING | STOPPING: `_clash` says `"base"`, `_held_by_move` never runs |
| (4) child-1's `test_a_clash_with_a_partner_whose_head_no_longer_fits_the_base_still_stops` | STOPPING | **flipped to a hold** (see below) |

**Case (3b), the path it takes (the brief asks Do to state it).** On the folded tip, rule
(d) does *not* fail in 3b: `A` merges cleanly onto `origin/main` as it is now (main
dropped its `a.txt` again), so child-1 names nobody (`_partners` 2d18208
`integrate.py:2033`: `A` + V merge onto main cleanly) and child-2's `_together`
(`integrate.py:1950`) names nobody either. The run stops on V with the generic fold error
("declare the conflict / re-order"), never reaching Y. So the brief's (i)–(iii) re-try,
gated on rule (d) failing, would not reach 3b at all. To give V and Y the step the brief
asks for, `_held_by_move` also runs when a line bundle fails on `S` though not on the
current base (`lost − now`): that is the "past" branch (patched `integrate.py:1977`).
It is held only after a trial proves the step: `head` updated from `<remote>/main`
(`_trial(head, [base_ref], made=…)`), then merged onto the actual line, merges cleanly.
The test then performs the step (`StackFoldGit._update_branch("Y")`) and checks Y merges
onto the pushed line. This branch is a widening of the brief's gate; I kept it because the
brief's own 3b assertion ("their step is update the branch from <remote>/main") cannot be
met on any path that stops.

**Case (4) flip — recorded as the brief asks.** child-1's
`test_a_clash_with_a_partner_whose_head_no_longer_fits_the_base_still_stops`
(`template/tests/test_flow_cross_wave_fold_holds.py`, 2d18208 line 402) is renamed
`test_a_clash_with_a_partner_whose_head_no_longer_fits_the_base_holds_it` and now asserts a
hold. Its shape has Y's *own* change also clashing with A's (`shared.txt`), besides the
base-move clash (`a.txt`). The test proves that by fixture fact: A rebuilt on main (its side
winning) merges, and Y merged after it still conflicts (`_merges(..., "A-on-main", "Y") ==
1`). So the hold names A as stranded ("rebuild issue_A's branch on the new origin/main")
**and** says "its change also conflicts with issue_A's", and the end-of-run line adds the
ordinary `Conflicts with: A` proposal. Exit 3 (U completes, Y is the only hold).

## Why this shape — what I tried and ruled out

1. **Literal (ii) only (partner-aimed hold, no further check).** It gets case (1) and the
   flip to a hold. But on the flip shape it tells A's owner to rebuild and says nothing to
   Y's owner, whose own `shared.txt` edit still clashes after the rebuild. That is the
   iteration-v2 §6 finding "A stranded partner hides a real overlap" (and v3 §6, same text),
   which the flip test's own docstring shape reproduces. Ruled out. The fix I chose costs:
   one trial (`_trial(S, [*lead, line tip, head], wins=len(lead))`, patched
   `integrate.py:1987`) to see whether the move explains the whole clash; only when it does
   not, `_partners` on `S` over the bundles that fit `S` (n trials) plus one trial per
   stranded bundle (its side winning over `S`, then `head`). Both kinds of result are kept
   only if they conflict in a file of the actual clash.
2. **Verifying a mixed hold by replaying the line without the overlap partners** (child-1's
   rule (e) on `S`). Ruled out because it cannot flip the case-(4) test, which the brief
   requires: there V is `Stacks on: W`, cut from the line, so V holds A; child-1's
   `_explains` (2d18208 `integrate.py:1859`, the `_in_line` check over `under`) returns False
   whenever a bundle left on the line holds a partner taken off. The flip would stay a
   stop. So a mixed hold names the own-overlap partners found by trial but does not prove
   they explain every remaining conflict. A mixed hold with nothing attributable stops
   (iii).
3. **Stranded = "fails on S" with no tie to the clash.** The brief's (3c) rule says a
   partner counts as stranded only when the move is what makes the head clash with it. The
   `S`-based judgement handles the brief's example (Y does not hold the move, so `S` is the
   old main). It does not handle a branch that holds the move but deletes what the move
   added (the iteration-v4 probe "a base move the branch takes back"): A fails on `S` in
   `x.txt`, but Y's clash is only `shared.txt`. Without a tie, Y got "rebuild issue_A's
   branch …" plus an overlap. I tie it to the files: every bundle in `lost` must fail on `S`
   in a file of the fold's conflict (`exc.paths`), else None (patched `integrate.py:1968`).
   Cost: no extra trial (the files come from `_unfit`'s trials). That probe is now the second
   (3c) test, a guard: it stops before and after.
4. **A second trial-worktree helper or a squash of `head` (iteration-v4's `_rebuilt`).** Not
   used, as the brief requires. Every new trial goes through `_trial` with child-2's
   `_own_change` revs first; "rebuilt on S" is `_trial`'s existing single `wins` index,
   never a squash. The one trial that needs the whole line's side to win uses the line tip
   as a single rev with `wins`, so `_trial` needed no change (no multi-index `wins`).
5. **Pinning bases to the run's start.** Not done (stated non-change). The tests only
   assert that W's base holds the moved main (`self.seen["issue_W"][1]`).

## Limits I know of (all stop the run, as today — none gives a wrong step)

- A line bundle built on a stranded one, whose own change the head overlaps (iteration-v4's
  "P2 built on P1"): `_unfit` cannot judge P2 (what it was built on fails on `S`), and the
  per-stranded trial on P1 is clean → nothing attributable → STOPPING. Probed by hand.
- Stranded and past bundles in one clash → STOPPING.
- A bundle the move strands in files the clash is not in → STOPPING (the second 3c test).
- Every bundle built on the moved main is held one by one, each naming the stranded
  partner (iteration-v2 §6 "a stranded line bundle holds every later bundle"). This is the
  hold decision 2 asked for; not changed here.

Probes I ran by hand (scratch, not in the patch): stranded partner plus an ordinary overlap
with another bundle Q → hold naming A stranded and Q as overlap, `Conflicts with: Q`; two
stranded partners → "issue_A1's, issue_A2's branches … do not merge … they were cut".

## Refute-your-own-test (forced)

- **(a) Genuine red?** Yes. With the production hunks reverted
  (`git apply -R --exclude='template/tests/*' patch.diff`, as `run-verify.sh` does), 5 of the
  7 new tests fail — (1), (3a), (3b), (3c), (3d) — and child-1's flipped test fails. Every
  failure is the same assertion: `'did not integrate' unexpectedly found in "flow: wave 1 did
  not integrate (issue_<X>'s branch … STOPPING"`, i.e. the pre-fix stop. The two guards —
  (2) and the second (3c) — pass both ways, as the brief expects for (2).
  `engine/scripts/run-verify.sh` reports `PDCA-EVIDENCE: C4 PASS — red without the fix,
  green with it`.
- **(b) Production path?** Yes. Each test calls `flow._drive_and_act` with the real
  `integrate.fold`, real git (bare origin, primary checkout, scratch clone), the real base
  builds, and the real exit-code rule `cli._results_rc`. Only the build leaf, publish's
  branch cut and `gh` are stubbed, exactly as child-1's and child-2's suites do. The test
  imports only modules (`cli, flow, integrate, publish, state`), never a symbol the fix adds,
  so it loads on the red leg. C5 (`run-prod-path.py`): "1 added driver-suite test(s) import
  the production package".
- **(c) Fixture includes the fault?** Yes. `main` really moves on origin mid-run (after the
  first fold, or after a bundle publishes), the held branch's base really holds that move
  (asserted by ancestry), and the stranded line bundle really fails to merge onto main
  (`_merges("origin/main", "A") == 0`) — each stated as a fixture fact in a separate clone.
  For 3b the undo is a real `git rm` pushed to main; for (2) the fixup is a real
  fast-forward push to `fix/K`.

## Gates run here

- C4 `engine/scripts/run-verify.sh` (PDCA_BUNDLE, PDCA_WORKTREE set): **PASS**.
- C5 `engine/scripts/run-prod-path.py`: imports production.
- Offline driver suite, before writing the final test file (`unittest discover -s tests` in
  `template/`): 2631 tests, 1 failure — child-1's guard, before I flipped it.
- T3 `engine/scripts/run-suite.sh` on the final tree: `PDCA-EVIDENCE: root suite OK,
  driver suite OK` — root 24 tests OK; driver 2632 tests OK (2 skipped), child-1's,
  child-2's and the same-wave suites included.

## Commit-readiness

pdca-harness has no formatter, linter config or commit hook (no `.pre-commit-config.yaml`,
no ruff/flake8/black config, only `.sample` hooks); CONTRIBUTING.md asks for DCO sign-off
(publish adds it) and a green offline suite. New lines are ≤ 100 columns, as the files
around them. `patch.diff` applies cleanly onto `2d18208` (`git apply --check --cached`
against a fresh index of that commit).

## Scratch left in the worktree (not in the patch)

`template/tests/_probe_flip.py` (untracked; not matched by `discover`'s `test*.py`),
`.cache/verify-index`, `.cache/t3.log` (`.cache` is git-ignored). Left for the harness to
reclaim.
