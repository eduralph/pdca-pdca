# Build notes — #739 hold a cross-wave clash at the line fold (iteration 3)

Target: eduralph/pdca-harness, built and verified on the folded line
`pdca-integration/main-r547f8028520f` at `9f7c446` (#738 folded on top of `75a886e`), the
worktree's base. In `path:line` below, **base** means `9f7c446` and **new** means the
patched tree. The brief's anchors are on `75a886e`; with #738 folded they moved:
`_held_by` 1743 → base 1747, `_clash` 1770 → 1774, `_partners` 1817 → 1821, the fold's hold
636-643 → base 641-648, `_carry_finished` 1259 → 1356, `_announce_conflict_holds` 1435 →
1532, the fold block `flow.py:2862-2879` → base 2977-2999, `cli._results_rc` 701 → 707.

This iteration starts from iteration 2's patch (`iteration-v2/patch.diff`) and fixes the
three implementation findings in its carry-forward. The findings in
`deferred-findings.json` are for the human and were not worked on as such (see "Known
gaps" for the two this change settles as a side effect).

## What changed this iteration (the carry-forward)

### 1. Two independent "together" clashes stopped the run

Before (v2 `_together`): a bundle was named only if leaving it out made the head merge
cleanly *as a whole*. With two joint clashes in two files (the reviewer's probe: P1+R1 in
`first.txt`, P2+R2 in `second.txt`), leaving any one out still left the other file's
clash, so nobody was named and the run stopped.

Now (new `integrate.py:1901-1953`, `_together`): each conflicting file is judged on its
own. The together trial gives the files the head conflicts in (`want`, new 1927-1931). A
bundle is named for a file when leaving it out removes that file from the conflict list
(`needed`, new 1933-1938); a clean merge counts for every file; a trial that stops before
the head names nothing. The own-change pass and the carried-change pass are v2's, now
per file (new 1940-1952). The result is name → the files it is needed for.

The same change covers a mixed clash: one file pinned on a single bundle by `_partners`,
another only together. v2 took `_clash`'s `"batch"` answer and never looked further, so it
named only the single partner. Now `_held_on_line` runs `_together` for every file of the
fold's conflict that the `"batch"` partners do not account for (`told`, new
`integrate.py:1860-1865`), and names both sets, in merge order (new 1866).

### 2. The stranded check blamed the base move for an ordinary overlap

Before (v2): a partner was "stranded" whenever its own change did not merge onto the
current base. Nothing checked that this was why the held bundle clashed with it, and the
message said the held bundle "was built on the new origin/main" without checking.

Now a partner is stranded only when all three hold (new `integrate.py:1870-1879`):

1. The held bundle's head holds a commit of the base that the line's cut point lacks: it
   was built on a newer base than the line (`_holds_newer`, new 1891-1898, judged on the
   merge bases of head and base — every shared commit is under one of them).
2. The partner's own change, tried after what it was built on, does not merge onto the
   base (v2's trial, kept).
3. That failure is in a file the head conflicts with the partner in (`files[n]`: the
   `_partners` files, or the files `_together` named it for).

And a stranded partner can now also be an `own` partner (new 1880-1883): the head is tried
again on the partner "rebuilt" on the base — base, what the partner was built on, the
partner with its side winning every clash (`_merge_over`, base 1707), then the head. If
the head still conflicts, the held bundle's own change also overlaps the partner, so it
gets the `Conflicts with` proposal too. A partner of a together-clash is always `own`
(see M6 below). `fold`'s `across` now records `(stranded, own)` (new 368, 674).

The wording (new `flow.py:1560-1618`, `_line_hold`) says "was built on a newer
origin/main than the line" — which is exactly what check 1 proves — instead of "was built
on the new origin/main". A partner can appear in both groups; the second group's text then
says "its change also conflicts with …".

This also settles two deferred findings, as a side effect of the same rule: deferred item 1
("a stranded partner hides a real overlap", probe A) is the new "both steps" test, and
deferred item 12 (the code review's x.txt/shared.txt shape) is covered by the same two
checks (the "both steps" test when the head carries the move in x.txt, the two-moves test
when it does not).

### 3. A `Conflicts with` partner of a stranded hold got the opposite advice

`_runnable` (base `flow.py:856-863`) worded every partner of a fold hold as "its change
conflicts with …, wait until W is rebuilt on a base that holds A". Now `_runnable` takes
`across` (new `flow.py:691`, passed at new 2936) and, for a cross-wave hold, prints the
held bundle's own reason and a matching wait (new 865-871): for case (3)'s X, "it
`Conflicts with` issue_W, which this run's fold held out of the line (issue_A's branch,
already on the line, does not merge cleanly onto origin/main itself: …), … wait until
issue_A's branch is rebuilt on the new origin/main, and issue_W's PR merges into main
(org/repo)". `_line_hold` returns that `wait` as a third value (new 1600, 1617). A
same-wave hold's partner line is unchanged.

Cosmetic, from the v2 code review: partner lists in `_line_hold` now use
`_conflict_partners` (", ") everywhere instead of " and " in two places.

## The whole change

`template/src/pdca_harness/integrate.py`
- Module docstring (base 63-68 → new 63-69): one clause for #739.
- `fold`: `on_line` and `across` parameters (new 367-368); `held_out` docstring (base
  471-484 → new 474-502); the conflict branch (base 641-648 → new 660-676): `_held_by`
  first, as before, only when a same-wave bundle was kept; then `_held_on_line`. A hold
  goes into the same `held_out` the flow reads as `held_conflict`.
- `_held_by` docstring (base 1756-1764 → new 1784-1794): the fold now tries
  `_held_on_line` before it stops. Code unchanged.
- `_held_on_line` (new 1804-1888), `_holds_newer` (new 1891-1898), `_together` (new
  1901-1953). `_clash` and `_partners` are reused unchanged, so `_clash`'s contract for the
  #694 carry (base 1777-1801) is unchanged; the together fallback lives outside it, as the
  brief requires.

`template/src/pdca_harness/flow.py`
- `_runnable`: `across` parameter, docstring, partner line (new 691, 729-747, 865-871;
  base 681-690, 729-740, 856-863).
- `_fold_lines`: passes `on_line` / `across` (new 1174-1175, docstring 1187-1201, call
  1211-1212).
- `_carry_finished`: `on_line` records each carried finished id's head (new 1380,
  1430-1432, 1512-1513).
- `_line_hold` (new 1560-1618), `_announce_conflict_holds` / `_report_conflict_holds`
  (new 1621-1641 / 1644-1661; base 1532-1554) take `cfg` and `across`; a same-wave hold
  prints exactly the old lines.
- `_drive_and_act`: `holds` docstring (new 2759-2765), `held_across` (new 2799-2803),
  `finished_on_line` (new 2876-2883), the `_runnable` call (new 2936, base 2820), the fold
  block's comment, fold call and announce calls (new 3097-3121, base 2978-2999), the
  end-of-run report (new 3149, base 3026).

`template/tests/test_flow_same_wave_conflict.py`: the case-(5) flip, and `_run` collects
`holds` and computes `self.rc` with `cli._results_rc` (new 148, 162-164). Unchanged this
iteration.

## Tests (real git, `StackFoldGit`, through `flow._drive_and_act`)

`template/tests/test_flow_cross_wave_fold_holds.py` (copy in this bundle), loaded by path
like `test_flow_same_wave_conflict.py:36-39`; exit code via
`cli._results_rc(results, holds=holds)` (base `cli.py:707`).

| case | test (new line) | holds | rc |
|---|---|---|---|
| (1) in-batch earlier-wave partner | `test_a_clash_with_an_earlier_wave_bundle_holds_only_that_bundle` (256) | `{Y: conflict}` | 3 |
| (2) finished F carried onto the line | `test_a_clash_with_a_finished_bundle_carried_onto_the_line_names_it` (287) | `{Y: conflict}` | 3 |
| (3) stranded by moved main, **+ X `Conflicts with: W`** | `test_a_line_bundle_a_moved_base_strands_is_named_with_the_fix_for_its_owner` (315) | `{B: base, W: conflict}` | 1 |
| (3b) partner stranded only by what it is built on | `test_a_partner_built_on_a_stranded_branch_is_not_told_to_rebuild_on_the_base` (372) | `{W: conflict}` | 1 |
| (3c) **new**: same, partner's own change also in the file | `test_a_partner_whose_own_base_does_not_merge_is_not_called_stranded` (410) | `{W: conflict}` | 1 |
| **new**: the adversary's probe (bundle built before main moved) | `test_a_bundle_built_before_the_base_moved_is_told_its_own_fix` (443) | `{Y: conflict}` | 3 |
| **new**: same file, separate lines, built before the move | `test_a_bundle_built_before_the_base_moved_is_never_said_to_hold_the_move` (477) | `{Y: conflict}` | 3 |
| **new**: main moves twice, clash not in the moved file | `test_a_base_move_the_clash_is_not_in_is_not_blamed_for_it` (510) | `{Y: conflict}` | 3 |
| **new**: stranded partner the bundle also overlaps (probe A) | `test_a_stranded_partner_whose_change_the_bundle_also_overlaps_gets_both_steps` (547) | `{Y: conflict}` | 3 |
| (4) two partners together, plus unrelated X | `test_a_clash_only_with_two_line_bundles_together_names_both` (584) | `{H: conflict}` | 3 |
| (4b) together, partners carried by dependents | `test_a_clash_together_names_whose_change_it_needs_not_who_carries_it` (619) | `{H: conflict}` | 3 |
| **new**: the reviewer's probe, two together-clashes in two files | `test_two_clashes_only_together_in_two_files_name_all_four` (653) | `{H: conflict}` | 3 |
| **new**: a single-partner clash beside a together-clash | `test_a_clash_with_one_bundle_beside_one_only_together_names_all_three` (694) | `{H: conflict}` | 3 |
| kept stop: also clashes with the base | `test_a_branch_that_also_clashes_with_the_base_itself_still_stops_the_run` (728) | `{}` | 1 |
| (5) flip | `test_flow_same_wave_conflict.py::test_a_conflict_with_its_own_prerequisite_on_the_line_holds_it_not_the_run` (367) | `{21: conflict}` | 1 |
| (5) stays a stop | `test_flow_same_wave_conflict.py::test_a_conflict_only_with_a_base_taken_in_mid_wave_still_stops_the_run` (427) | — (unchanged) | — |

Case (3)'s message assertions changed with the wording ("was built on a newer origin/main
than the line"); (3b) asserts "its change also conflicts with issue_P2's". The test helpers
gained `_ten` / `_rewrite` (used by the old and new together cases) and `conflicts_with`
in `_plan`.

### Tests that flip, before and after

Only the one the brief names. Driver suite on the base `9f7c446`: 2610 OK, 2 skipped
(iteration 2's count, same base). Patched: 2624 OK, 2 skipped = 2610 + the 14 new cases;
no test that passed on the base fails now.

- `test_flow_same_wave_conflict.py::test_a_conflict_with_earlier_wave_work_still_stops_the_run`
  — **before:** asserted `wave 1 did not integrate`, `issue_21's branch`, `STOPPING`, no
  hold line for 21, 30 not built. **After:** renamed
  `test_a_conflict_with_its_own_prerequisite_on_the_line_holds_it_not_the_run` (new 367):
  no `did not integrate` / `STOPPING`; one hold line for 21 with `issue_10`,
  `(conflicts in shared.txt)` and `rebuild issue_21's branch on issue_10's`; no
  `Conflicts with: 10` anywhere; 21's head not on the line; 30 not built and PLANNED;
  holds `{21: conflict}`; rc 1.
- `test_a_conflict_only_with_a_base_taken_in_mid_wave_still_stops_the_run` — unchanged
  and still green (22 does not merge onto the moved main, so the base-alone check stops
  it).

### Messages as printed (fix applied; from a scratch run of every case)

- (1) `flow: issue_Y held out of the integration fold — its change conflicts with issue_A's, already on the line (conflicts in shared.txt); bundles that depend on it or are its `Conflicts with` partners are held this run. Proposed, for you to confirm: declare `Conflicts with: A` in issue_Y's brief, then rebuild issue_Y on a base that holds issue_A.`
- (3) W: `… — issue_A's branch, already on the line, does not merge cleanly onto origin/main itself: origin/main moved since it was cut, and issue_W was built on a newer origin/main than the line (conflicts in a.txt); … To fold it, rebuild issue_A's branch on the new origin/main (update it from origin/main and resolve the conflicts there), then re-run.`
- (3) X: `flow: issue_X held — it `Conflicts with` issue_W, which this run's fold held out of the line (issue_A's branch, already on the line, does not merge cleanly onto origin/main itself: origin/main moved since it was cut, and issue_W was built on a newer origin/main than the line), so no line of this run holds that work; not built on a base missing it. To build it, wait until issue_A's branch is rebuilt on the new origin/main, and issue_W's PR merges into main (org/repo), then re-run.`
- Adversary's probe, and the two-moves case: the same text as (1) — `Conflicts with: A`, no stranded wording.
- Probe A: `… issue_A's branch, already on the line, does not merge cleanly onto origin/main itself: origin/main moved since it was cut, and issue_Y was built on a newer origin/main than the line; its change also conflicts with issue_A's, already on the line (conflicts in a.txt, shared.txt); … To fold it, rebuild issue_A's branch on the new origin/main (…), then re-run. Proposed, for you to confirm: declare `Conflicts with: A` in issue_Y's brief, then rebuild issue_Y on a base that holds issue_A.`
- Two files: `… its change conflicts with issue_P1's, issue_P2's, issue_R1's, issue_R2's, already on the line (conflicts in first.txt, second.txt); … declare `Conflicts with: P1, P2, R1, R2` in issue_H's brief …`
- Mixed: `… its change conflicts with issue_A's, issue_P's, issue_R's, already on the line (conflicts in first.txt, shared.txt); … `Conflicts with: A, P, R` …`
- (5) `flow: issue_21 held out of the integration fold — its change conflicts with issue_10's, already on the line, and issue_10 is its own prerequisite, which its branch does not hold (conflicts in shared.txt); … To fold it, rebuild issue_21's branch on issue_10's, then re-run.`

## Refuting my own test

**(a) Genuine red? Yes.** `./engine/scripts/run-verify.sh` (the configured C4 gate, run
with `PDCA_BUNDLE` / `PDCA_WORKTREE` under `timeout`) reverts only the production hunks.
Red leg: 14 failures — the case-5 flip and every new-file case except the kept stop — each
`'did not integrate' unexpectedly found … wave N did not integrate`. No import or load
failure. Green leg: all 22 tests of both files pass. `PDCA-EVIDENCE: C4 PASS`; the
worktree matched `patch.diff` byte for byte afterwards.

Against **iteration 2's code** (the same gate script, with v2's production files as the
"reverted" side, built in `.cache/v2check/`; the 11-case test file of that moment, before
the three cases added last): 6 failed, each with the reviewers' symptom — the adversary's probe printed "issue_Y was
built on the new origin/main … rebuild issue_A's branch" with no `Conflicts with`; the
mixed case named only `issue_A`; the two-file case stopped (`wave 1 did not integrate`);
case (3), (3b) and probe A failed on the reworded text. Case (3)'s X line is pinned
separately by M7 below, since on v2 the test fails earlier, on the wording.

Each rule was also broken on its own (`.cache/mut/run_mut.py`; each mutant run through
the same gate script as the "reverted" side; the worktree checked byte-identical and the
worktree root unchanged after each run):

| mutation | breaks | red |
|---|---|---|
| M1 | together: a file counts only when the whole merge is clean (v2's rule) | two files, mixed |
| M2 | together not run beside a single-partner clash | mixed |
| M3 | no newer-base check | same file, separate lines |
| M4 | no same-file check | two moves |
| M5 | no rebuild trial (a stranded single partner never `own`) | probe A |
| M6 | a together-partner not always `own` | **none — not caught** |
| M7 | `_runnable` not given `across` | case (3) (X's line) |
| M8 | no prerequisite wording | (5) flip |
| M9 | no base-alone check | kept stop |
| M10 | no carried-change pass | (4b) |
| M11 | carry records no finished heads | (2) |
| M12 | stranded: whole head onto the base (v1's rule) | (3c) |
| M13 | judged on the fetched base, not the line's cut point | 7 stranded-rule cases |

M3 and M12 were first masked by the new same-file check in every case; the cases at new
410 and 477 were added to isolate them (both now red under their mutation). M6 is not
caught: it needs a together-clash whose partner is also stranded in the same file, which
with git's text merge takes a rename-versus-rename or rename-versus-delete clash with the
moved base. I did not build that fixture. The rule it pins is the conservative one: a
partner of a together-clash keeps the `Conflicts with` proposal even when it is also told
to rebuild on the base, because a rebuild trial of that partner alone says nothing about
a clash that needs it together with others.

**(b) Production path? Yes.** Every case drives `flow._drive_and_act` → the real
`integrate.fold` → `_held_on_line` → real `_clash` / `_partners` / `_together` /
`_holds_newer` / `_trial` merges in the real integration worktree; case (2) runs the real
`_carry_finished`; the stranded cases run real `build_bundle_base` on a really moved
origin main (case (3) asserts B's #738 hold line); case (3)'s X goes through the real
`_runnable`. Stubbed, as in `test_flow_same_wave_conflict.py`: the build leaf
(`_drive_wave`), `_publish_bundle` (pushes real branches to the bare origin),
`publish.draft_texts`, and `gh`. The `integrate.fold` wrapper only calls through, then
runs the case's after-fold hook.

**(c) Fixture includes the fault? Yes.** The clashing branches are real pushed branches.
The stranded cases really move origin's main (once or twice) and assert, by ancestry,
whether the held bundle's head or base tip holds each move; they assert by real merges
that the partner does or does not merge onto the moved main and that the held bundle
does. The together cases assert by real merges that each partner alone merges with H,
that the combination conflicts at H, and (two files) that leaving any one of the four
out still conflicts. F is really put on the line by the carry.

## Alternatives ruled out

- **For finding 1, a greedy search when no bundle is needed for a file** (drop bundles one
  by one while the file still conflicts; forward and reverse, union). It would name
  partners in an "any two of three" clash, where leave-one-out names nobody. Cost: about
  20 lines and 2·(n − named) trials of up to n+1 merges per such file. Not built: the
  answer depends on the order; the only way I found to make such a clash with git's text
  merge is two bundles making the identical change, so I had no honest fixture for it;
  and the brief's default for an unpinned clash is to stop. Gap recorded below.
- **For finding 2, the reviewer's path-only form** (stranded = newer ∧ same file; `own`
  for the leftover files). Kept its two checks, and used a rebuild trial instead of
  "leftover files" for `own`: the leftover-file rule misses a held bundle whose own change
  overlaps the partner in the same file the base clashes in. Cost of the trial: one
  trial (base + partner's base + partner + head) per stranded single partner, only on the
  conflict path.
- **For finding 3, a precomputed text map** passed to `_runnable` beside `conflict_held`
  instead of `across`: the same number of lines in `_runnable`, plus a second map in
  `_drive_and_act` built each wave. `_runnable` already has `cfg`, so it calls
  `_line_hold` itself and both hold lines come from one function.
- Carried from v2, still valid: plain leave-one-out without the carried-change pass
  (M10 shows (4b) needs it); a cascade leave-out (names W when V's own change is needed);
  changing `_held_by`'s "all of `kept`" (out of scope); a 3-tuple `held_out` value
  (changes the type three flow readers unpack and breaks
  `test_a_hold_leaves_the_integration_tree_clean_on_the_line`); putting carried finished
  bundles into `accepted` (they would enter `carried_heads`, the #633 / #695 checks and
  `build_bundle_base(excluded=…)`).

## Trial cost (conflict path only)

`_held_on_line`: 1 base trial, `_clash`'s trials, then per partner: 1 stranded trial when
the head is newer, plus 1 rebuild trial when the partner is stranded, plus 1 `merge-base
--all` and up to k `--is-ancestor` calls once. `_together` (only when some file is not
accounted for): 1 together trial + n own-change trials + at most n carried-change trials,
each of up to n+1 merges, and up to n² ancestry checks — v2's count, now per file in the
same trials (the conflict list of each trial is read once for all files).

## Known gaps (left for the human)

- **M6 untested** (above).
- **A file whose clash needs some combination with no single bundle needed** ("any two of
  three", or two bundles making the identical change): leave-one-out names nobody for that
  file. If no file of the clash names anyone, the run stops, as before; if another file
  does, the bundle is held naming those, and the unpinned file shows only in "(conflicts
  in …)". Where every combination needs one bundle and the rest are interchangeable
  ("A and (B or C)"), only that one is named.
- **Deferred findings.** Items 1 and 12 are covered by this iteration's stranded rule (see
  §2). Item 2 ("a stranded line bundle holds every later bundle, after building it") is
  unchanged and needs the human's call; the "both steps" case uses `Stacks on: W` for V so
  that V is not one more such hold. The rest are plan-level and untouched.
- A needed bundle whose change reaches the line only through a dependent that is itself
  named for its own change is not named separately (v2's gap, unchanged).
- `cli._results_rc`'s docstring (base `cli.py:722-723`) still describes `"conflict"` as a
  same-wave hold only; cli.py is outside this slice (#740 can take it).

No external dependency was missing: git, the instance `.venv` Python and copier were all
present; nothing was stubbed in place of a tool.

## Commit-readiness

The target has no formatter, linter config or commit hooks (no `.pre-commit-config.yaml`,
no ruff/flake8/black config, `core.hooksPath` unset, `.git/hooks` only samples); CI runs
the docs check and the render suite. All four files compile; `git diff --check` is clean;
no tabs; no added line over 99 characters (the files already go to 100-106). T2 docs gate
(`run-docs-check.sh`): lint clean, 22 pages rendered, link audit OK. T3: below. The
publish commit needs a DCO sign-off (`CONTRIBUTING.md`), which
publish adds. `patch.diff` applies cleanly to the base index (`git apply --cached --check`)
and reproduces the worktree byte for byte.

T3 (`run-suite.sh`, on the final tree): root suite 24 OK; driver suite 2624 OK (2
skipped); `PDCA-EVIDENCE: root suite OK, driver suite OK`.

## Housekeeping

Scratch files, all under the worktree's git-ignored `.cache/`: `v2check/` (v2's production
files and the v2→v3 patch), `mut/` (the mutation script, one directory per mutation with
its patch and gate log, `summary-final.txt`), `show.py` / `show.out` (the printed lines
above), `base.idx` (a scratch index of `9f7c446` for the apply check), and the logs
`c4-run*.log`, `c4-final.log`, `t2.log`, `t3.log`, `t3-final.log`.

One mishap: the first mutation script wrote patch headers with absolute paths, so the gate
script's reverse-apply moved `flow.py` into a new directory tree `home/eddie/…` at the
worktree root instead of patching it; its restore moved the file back and left only empty
directories (no files; git ignores them). That run's results were discarded. I moved the
empty tree into `.cache/stray-empty-dirs-from-bad-mutation-patch/` (a move, not a
delete), fixed the script (relative paths, a header check, a `git apply -R --check`
before each run, and a check that the worktree root is unchanged after it), and reran.
The worktree root now holds only tracked content and `.cache/`.

Nothing was removed; cleanup is the harness's. I wrote nothing outside the worktree and
this bundle (the T2 gate script makes its own `/tmp` dir). No push, no PR.
