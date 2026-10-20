# Build notes — #739 hold a cross-wave clash at the line fold (iteration 4)

Target: eduralph/pdca-harness, built and verified on the folded line
`pdca-integration/main-r547f8028520f` at `9f7c446` (#738 folded on top of `75a886e`), the
worktree's base. Below, **base** means `9f7c446` and **new** means the patched tree. The
brief's anchors are on `75a886e`; with #738 folded they moved: `_held_by` 1743 → base 1747,
`_clash` 1770 → 1774, `_partners` 1817 → 1821, the fold's hold 636-643 → base 641-648,
`_carry_finished` 1259 → 1356, `_announce_conflict_holds` 1435 → 1532, the fold block
`flow.py:2862-2879` → base 2977-2999, `cli._results_rc` 701 → 707.

This iteration keeps iteration 3's shape (the fold's conflict branch, `held_out` /
`held_conflict`, `across`, `_line_hold`, the carry's finished heads, the `_runnable`
partner line) and replaces the two parts the carry-forward found wrong: how a partner is
judged "stranded" (now on the base the held branch actually holds), and how the "together"
partners are found (now a search checked against the advice itself). The deferred findings
are for the human and were not worked on as such (see "Known gaps").

## The carry-forward, finding by finding

### 1. C5: a directly explained file hid a joint clash in the same file

Iteration 3's `_together` judged each file on its own and skipped every file a single
partner already explained (`told`). The reviewer's probe — A edits line 10 of shared.txt,
P renames the file, R rewrites most of it, H edits line 10 — named only A, and H rebuilt on
A still clashed with P + R.

Now (new `integrate.py:1921-1967`, `_together`): no file is skipped. The search runs on the
line rebuilt on the base the held branch holds (every bundle merged with its side winning,
`_trial(wins=…)`, so only the held branch can conflict). Each round:

1. builds the held branch **rebuilt on every partner named so far** (`_rebuilt`, new
   `integrate.py:2120-2155`: their heads merged onto the base, then the held branch's
   change on top with its side winning — one way its owner's rebuild could go);
2. merges it last onto that rebuilt base plus every bundle not named yet;
3. if it still conflicts, finds one smallest set of those bundles it conflicts with
   (each dropped, latest first, while it still conflicts without it) and names it.

The search ends only when the held branch, rebuilt on everything named, merges cleanly
after the whole line. So the advice the hold gives is checked by trial before it is given.
For the reviewer's probe: `_partners` names A; round 1 rebuilds H on A, which still
conflicts, and finds {P, R}; round 2 rebuilds H on A, P and R, which merges cleanly. Test:
`test_a_clash_with_one_bundle_and_with_two_together_in_one_file_names_all_three` (new test
file :957), which also asserts the reviewer's own fixture fact (H rebuilt on A, its side
winning, still conflicts after A, P, R; it merges after A alone).

The same mechanism closes a related gap that iteration 3's code had too (on it, this test
names only A) and that my first draft this iteration still had: a bundle built on a named
partner whose **own** change is part of a clash together with another bundle. B (built
on A) renames shared.txt, P rewrites it, A and H both edit line 10. Leaving A's dependents
out of the search (my first draft; iteration 3's `on_it` rule) names only A; the rebuild
check names A, P and B. Test:
`test_the_own_change_of_a_bundle_built_on_a_partner_is_judged_too` (:992).

### 2. Main moved twice: the stranded check blamed the base for an ordinary overlap

Iteration 3 set `newer` when the held branch held *any* base commit the line's start
lacked, then tried the partner on the *current* tip of `base_ref`. With one unrelated main
commit before Y's base was built and a line-8 change after Y published, A was called
stranded for Y although A merges cleanly onto the main Y holds.

Now (new `integrate.py:1882-1897`): the partner's own change is tried on `held`, the
newest commit of `base_ref` the held branch holds (`git merge-base head base_ref`), with
what it was built on rebuilt there first (`wins`). Only when it fails there, in a file the
held branch conflicts with it in, is the base the held branch carries what clashes with it.
And the check is skipped when the line already holds `held` (new :1884): then nothing on
the line can fail on it. Test:
`test_a_base_move_the_branch_does_not_hold_is_not_blamed_in_the_file_it_moved` (:570) — the
reviewer's probe, with V `Stacks on: W` so that no branch merged before Y already brings
the first move onto the line (with V on its own base, as in the probe, the line holds
`held` through V and the shortcut alone decides it; the outcome is the same, but then the
case would not pin the rule — found by mutation M3, below).

### 3. Main undid a commit: a stale base commit was called the bundle's own change

When main later deletes the a.txt it had added, A merges onto main *now*, so iteration 3
put A in `own` and proposed `Conflicts with: A` to Y and V, which never touch a.txt.

Now a partner that fails on `held` but merges onto `base_ref` now is `past` (new
`integrate.py:1895-1897`): the held branch is told to update from the base, and no
`Conflicts with` is proposed. `LineClash` (new :1799-1823) carries `stranded`, `past`,
`own`, `older`; `_line_hold` (new `flow.py:1562-1636`) words `past` as "issue_A's branch,
already on the line, does not merge cleanly onto the origin/main issue_V's branch holds,
but does onto origin/main as it is now: origin/main moved on since issue_V's branch was
built … To fold it, update issue_V's branch from origin/main, then re-run." Test:
`test_a_clash_with_a_base_commit_main_has_since_undone_is_for_the_branch_to_update` (:728),
which also runs the step (GitHub's "Update branch" on fix/Y) and shows Y then merges onto
the line.

### 4. "…which its branch does not hold" when the branch holds an older tip

`older` (new `integrate.py:1904-1912`): an `own` partner whose own commits — from its head,
not reachable from `base_ref`, the line's start, or what it was built on — the held branch
holds some of. `_line_hold` says "its branch holds an older tip of issue_A's branch" and
gives "rebuild issue_Y's branch on issue_A's", no `Conflicts with`. "…its own prerequisite,
which its branch does not hold" is now said only for a declared prerequisite that is not
`older` (so the branch provably holds none of its own commits). Tests:
`test_a_branch_holding_an_older_tip_of_its_prerequisite_is_told_so` (:778), and the case-5
flip now also asserts the "does not hold" reason
(`test_flow_same_wave_conflict.py:387-388`).

### Found while building: the first rebuild check was nondeterministic

The mutation baseline failed once on the finding-1 test above, naming H's own prerequisite K.
Cause: the rebuilt branch was a merge commit sharing four independent merge bases with the
trial line (A, K, P, R), so git built a virtual merge base whose content depended on their
order, which changes with commit timestamps. Measured on that one case: **10 of 25 runs
failed**. Fix (new `integrate.py:2142-2150`): the rebuilt branch is committed as one change
whose only parent is the rebuilt base (`git commit-tree HEAD^{tree} -p start`), and each
trial starts from that base, so its last merge has exactly one merge base. After the fix:
**0 of 25** on that case, and the two test modules (28 cases then) ran 10 times in a row
clean, 280 case runs; the final 29-case modules passed in every run since (the direct run,
the mutation baseline, C4's green leg, T3).

## The whole change

`template/src/pdca_harness/integrate.py`
- Module docstring (base 63-68 → new 63-70): one clause for #739. `NamedTuple` import
  (new 82).
- `fold`: `on_line` / `across` parameters (new 369-370); `held_out` docstring (base 478-484
  → new 484-497); the conflict branch (base 641-648 → new 654-671): `_held_by` first, as
  before, when a same-wave bundle was kept; then `_held_on_line`. A hold goes into the same
  `held_out` the flow reads as `held_conflict`; `across` gets its `LineClash`.
- `_held_by` docstring (base 1756-1764 → new 1778-1789): the fold now tries
  `_held_on_line` before it stops. Code unchanged; its #738 caller `_member_clash` (base
  982) is untouched.
- `LineClash` (new 1799-1823), `_held_on_line` (new 1826-1918), `_together` (new
  1921-1967). `_clash` and `_partners` are reused unchanged for the single partners, so
  `_clash`'s contract for the #694 carry (base 1777-1801) is unchanged; the "together"
  fallback lives outside it, as the brief requires (case 4).
- `_trial`: `wins` takes several indices (base 1885, 1892-1894, 1905 → new 2081,
  2088-2091, 2102); one int behaves as before (#694's `_partners` still passes one).
- `_rebuilt` (new 2120-2155).

`template/src/pdca_harness/flow.py`
- `Sequence` import (new 27).
- `_runnable`: `across` parameter (new 691), docstring (base 729-733 → new 730-741), the
  `Conflicts with` partner line of an across-hold (new 865-871): the held bundle's own
  reason and what to wait for, from `_line_hold`. A same-wave hold's partner line is
  unchanged.
- `_fold_lines`: `on_line` / `across` (new 1174-1175, docstring 1184-1201, call 1212-1213).
- `_carry_finished`: `on_line` (new 1381, docstring 1431-1433); the carry's fold now gets an
  empty `carried` mapping of its own (`put`, new 1485, 1490) to learn the head it put on the
  line for each finished id (an empty mapping checks nothing: `integrate.fold` runs
  `_carried_tips` only for a non-empty one, base `integrate.py:533-534`), recorded into
  `on_line` (new 1514-1515). Iteration 3 recorded the PR head instead; the code review
  noted the two can differ.
- `_line_hold` (new 1562-1636), `_announce_conflict_holds` / `_report_conflict_holds` (new
  1639-1659 / 1662-1678; base 1532-1554) take `cfg` and `across`; a same-wave hold prints
  exactly the old lines. The base ref comes from the fold (`LineClash.base`), not rebuilt
  in flow (the iteration-3 code review's cleanup note).
- `_drive_and_act`: `holds` docstring (new 2778-2781), `held_across` (new 2816-2819),
  `finished_on_line` (new 2892-2899), the `_runnable` call (new 2952), the fold block's
  comment, fold call and announce calls (new 3113-3137, base 2977-2999), the end-of-run
  report (new 3163-3165, base 3025-3026).

`template/tests/test_flow_same_wave_conflict.py`: iteration 3's case-(5) flip and `_run`
collecting `holds` / `self.rc` via `cli._results_rc` (new 148, 162-164), plus the "does
not hold" assertion (new 387-388).

## Tests (real git, `StackFoldGit`, through `flow._drive_and_act`)

`template/tests/test_flow_cross_wave_fold_holds.py` (copy in this bundle), loaded by path
like `test_flow_same_wave_conflict.py:36-39`; exit code via
`cli._results_rc(results, holds=holds)` (base `cli.py:707`). 21 cases; new this iteration
marked ★ (5 for the carry-forward, 2 found while building).

| case | test (new line) | holds | rc |
|---|---|---|---|
| (1) earlier-wave partner | `…_earlier_wave_bundle_holds_only_that_bundle` (280) | `{Y}` | 3 |
| (2) finished F carried | `…_finished_bundle_carried_onto_the_line_names_it` (311) | `{Y}` | 3 |
| (3) stranded A, + X `Conflicts with: W` | `…_moved_base_strands_is_named_with_the_fix_for_its_owner` (339) | `{B: base, W}` | 1 |
| (3b) partner built on a stranded branch | `…_built_on_a_stranded_branch_is_not_told_…` (395) | `{W}` | 1 |
| (3c) same, its own change in the file too | `…_own_base_does_not_merge_is_not_called_stranded` (433) | `{W}` | 1 |
| built before main moved | `…_built_before_the_base_moved_is_told_its_own_fix` (466) | `{Y}` | 3 |
| same file, separate lines | `…_is_never_said_to_hold_the_move` (500) | `{Y}` | 3 |
| two moves, clash not in the moved file | `…_the_clash_is_not_in_is_not_blamed_for_it` (533) | `{Y}` | 3 |
| ★ two moves, clash in the moved file (finding 2) | `…_does_not_hold_is_not_blamed_in_the_file_it_moved` (570) | `{Y}` | 3 |
| ★ branch takes the move back (file filter) | `…_the_branch_takes_back_is_not_blamed_for_its_clash` (613) | `{Y}` | 3 |
| probe A: stranded + own overlap | `…_also_overlaps_gets_both_steps` (649) | `{Y}` | 3 |
| ★ stranded + needed for a clash together | `…_needed_for_a_clash_together_gets_both_steps` (684) | `{Y}` | 3 |
| ★ main undid the commit (finding 3) | `…_main_has_since_undone_is_for_the_branch_to_update` (728) | `{V, Y}` | 1 |
| ★ older tip of a prerequisite (finding 4) | `…_older_tip_of_its_prerequisite_is_told_so` (778) | `{Y}` | 3 |
| (4) two together, + unrelated X | `…_only_with_two_line_bundles_together_names_both` (815) | `{H}` | 3 |
| (4b) together, carried by dependents | `…_names_whose_change_it_needs_not_who_carries_it` (850) | `{H}` | 3 |
| two together-clashes in two files | `test_two_clashes_only_together_in_two_files_name_all_four` (884) | `{H}` | 3 |
| one alone beside two together | `…_beside_one_only_together_names_all_three` (925) | `{H}` | 3 |
| ★ one alone and two together, one file (finding 1) | `…_and_with_two_together_in_one_file_names_all_three` (957) | `{H}` | 3 |
| ★ own change of a bundle built on a partner | `test_the_own_change_of_a_bundle_built_on_a_partner_is_judged_too` (992) | `{H}` | 3 |
| kept stop: clashes with the base itself | `…_also_clashes_with_the_base_itself_still_stops_the_run` (1031) | `{}` | 1 |
| (5) flip | `test_flow_same_wave_conflict.py::test_a_conflict_with_its_own_prerequisite_on_the_line_holds_it_not_the_run` (367) | `{21}` | 1 |
| (5) stays a stop | `test_flow_same_wave_conflict.py::test_a_conflict_only_with_a_base_taken_in_mid_wave_still_stops_the_run` (429) | — | — |

Changed from iteration 3's file: the stranded wording in case (3) and probe A ("was built
on a newer origin/main than the line" → "issue_W's branch holds that move"; case (3)'s
blame list drops the bare "issue_W's branch", which the new wording contains as a fact,
and keeps "its change", "rebuild issue_W", "update issue_W", "Conflicts with: A"); the
"wrong" lists of the three "built before the move" cases also reject "update issue_Y's
branch"; two fixture helpers, `_drop_from_main` (148) and `_rebuilt` (159).

### Tests that flip, before and after

Only the one the brief names. Driver suite on the base `9f7c446`: 2610 OK, 2 skipped
(iteration 3's count, same base). Patched: 2631 OK, 2 skipped = 2610 + the 21 new cases; no
test that passed on the base fails now.

- `test_flow_same_wave_conflict.py::test_a_conflict_with_earlier_wave_work_still_stops_the_run`
  — **before:** asserted `wave 1 did not integrate`, `issue_21's branch`, `STOPPING`, no
  hold line for 21, 30 not built. **After:** renamed
  `test_a_conflict_with_its_own_prerequisite_on_the_line_holds_it_not_the_run` (new 367):
  no `did not integrate` / `STOPPING`; one hold line for 21 with `issue_10`,
  `(conflicts in shared.txt)`, `issue_10 is its own prerequisite, which its branch does
  not hold` and `rebuild issue_21's branch on issue_10's`; no `Conflicts with: 10` anywhere;
  21's head not on the line; 30 not built and PLANNED; holds `{21: conflict}`; rc 1.
- `test_a_conflict_only_with_a_base_taken_in_mid_wave_still_stops_the_run` — unchanged and
  still green (22 does not merge onto the moved main, so the base-alone check stops it).

### Messages as printed (fix applied; `.cache/i739/show.out` in the worktree)

- (1) `flow: issue_Y held out of the integration fold — its change conflicts with issue_A's, already on the line (conflicts in shared.txt); bundles that depend on it or are its `Conflicts with` partners are held this run. Proposed, for you to confirm: declare `Conflicts with: A` in issue_Y's brief, then rebuild issue_Y on a base that holds issue_A.`
- (3) W: `… — issue_A's branch, already on the line, does not merge cleanly onto origin/main itself: origin/main moved since it was cut, and issue_W's branch holds that move (conflicts in a.txt); … To fold it, rebuild issue_A's branch on the new origin/main (update it from origin/main and resolve the conflicts there), then re-run.`
- (3) X: `flow: issue_X held — it `Conflicts with` issue_W, which this run's fold held out of the line (issue_A's branch, already on the line, does not merge cleanly onto origin/main itself: origin/main moved since it was cut, and issue_W's branch holds that move), so no line of this run holds that work; not built on a base missing it. To build it, wait until issue_A's branch is rebuilt on the new origin/main, and issue_W's PR merges into main (org/repo), then re-run.`
- Undo: `flow: issue_V held out of the integration fold — issue_A's branch, already on the line, does not merge cleanly onto the origin/main issue_V's branch holds, but does onto origin/main as it is now: origin/main moved on since issue_V's branch was built (conflicts in a.txt); … To fold it, update issue_V's branch from origin/main, then re-run.`
- Older tip: `… — its change conflicts with issue_A's, already on the line: its branch holds an older tip of issue_A's branch (conflicts in shared.txt); … To fold it, rebuild issue_Y's branch on issue_A's, then re-run.`
- Stranded + together: `… — issue_A's branch, … and issue_Y's branch holds that move; its change also conflicts with issue_A's, issue_R's, already on the line (conflicts in a.txt, shared.txt); … To fold it, rebuild issue_A's branch on the new origin/main (…), then re-run. Proposed, for you to confirm: declare `Conflicts with: A, R` in issue_Y's brief, then rebuild issue_Y on a base that holds issue_A, issue_R.`
- One alone + two together, one file: `… its change conflicts with issue_A's, issue_P's, issue_R's, already on the line (conflicts in shared.txt); … `Conflicts with: A, P, R` …`
- (5) `flow: issue_21 held out of the integration fold — its change conflicts with issue_10's, already on the line: issue_10 is its own prerequisite, which its branch does not hold (conflicts in shared.txt); … To fold it, rebuild issue_21's branch on issue_10's, then re-run.`

## Refuting my own test

**(a) Genuine red? Yes.** `./engine/scripts/run-verify.sh` (the configured C4 gate; run
from the instance root with `PDCA_BUNDLE` / `PDCA_WORKTREE` under `timeout 1800`) reverts
only the production hunks. Red leg: 20 of 21 cases in the new file fail (all but the kept
stop, which is meant to stop both before and after) and the case-5 flip fails — every one
on `'did not integrate' unexpectedly found … wave 1 did not integrate … STOPPING`. No
import or load failure. Green leg: 21 + 8 OK. `PDCA-EVIDENCE: C4 PASS`. Afterwards the
worktree matched base + `patch.diff` byte for byte (checked through a scratch index).

Against **iteration 3's code** (base + `iteration-v3/patch.diff` in a scratch clone, this
test file): 8 fail. Five on the behaviour the carry-forward reported — finding 1 (names
only A), finding 2 (calls A stranded), finding 3 (`Conflicts with: A`), finding 4 ("which
its branch does not hold"), and the own change of a bundle built on a partner (names only
A). Three on the reworded stranded clause only (case 3, probe A, stranded + together).

**Each rule broken on its own** (`.cache/i739/mutate.py`: one textual mutation at a time
in a scratch clone of base + patch, both modules run, the clone restored byte for byte
after each; summary in `.cache/i739/mutations-summary.txt`):

| mutation | breaks | red |
|---|---|---|
| M1 | no together search (single partners only) | 8 cases |
| M2 | together: leave a named partner's dependents out instead of the rebuild check | own change of a bundle built on a partner |
| M3 | stranded judged on the base tip now (iteration 3's rule) | finding-2 case, undo case |
| M4 | no `past` (moved past → stranded) | undo case |
| M5 | no older-tip check | older-tip case |
| M6 | no prerequisite wording | case-5 flip |
| M7 | `_runnable` not given `across` | case (3) (X's line) |
| M8 | no base-alone check | kept stop |
| M9 | carry records no finished heads | case (2) |
| M10 | moved check without rebuilding what the partner is built on | (3c) |
| M11 | together: earliest first instead of latest first | (4b), both stranded + own cases |
| M12 | `held` = the line's start, not the base the branch holds | 6 stranded/undo cases |
| M13 | together judged on the line's start | case (3), undo, stranded + together |
| M14 | no file-overlap filter in the moved check | branch-takes-back case |
| M15 | `newer` shortcut off (always try) | **none** |

M15 is a shortcut, not a rule: when the line already holds `held`, every bundle on it
merged cleanly with it (before `held` came in, through that merge; after, onto a line
holding it), so the trial it skips cannot fail. No case can make it red; it saves one
trial per single partner when the base did not move, and it keeps a non-compositional
3-way result from producing a "stranded" the line itself contradicts.

**(b) Production path? Yes.** Every case drives `flow._drive_and_act` → the real
`integrate.fold` → `_held_on_line` → real `_clash` / `_partners` / `_together` /
`_rebuilt` / `_trial` merges in the real integration worktree; case (2) runs the real
`_carry_finished`; the stranded cases run real `build_bundle_base` on a really moved origin
main (case (3) asserts B's #738 hold line); case (3)'s X goes through the real
`_runnable`. Stubbed, as in `test_flow_same_wave_conflict.py`: the build leaf
(`_drive_wave`), `_publish_bundle` (pushes real branches to the bare origin),
`publish.draft_texts`, and `gh`. The `integrate.fold` wrapper only calls through, then runs
the case's after-fold hook. C5 prod-path gate: `1 added driver-suite test(s) import the
production package 'pdca_harness'`.

**(c) Fixture includes the fault? Yes.** The clashing branches are real pushed branches.
The moved-base cases really move origin's main (once, twice, or add then delete) and assert
by ancestry what each branch holds; they assert by real merges that the partner does or
does not merge onto the main the held branch holds and onto main now. The together cases
assert by real merges that each partner alone merges with H and the combination does not,
and the finding-1 and own-change cases rebuild H on A in the scratch clone (its side
winning) and show that the rebuild alone still conflicts. The undo case runs the advised
step ("Update branch") and shows Y then merges onto the line. F is really put on the line
by the carry; A's fixup is a real fast-forward push the fold really takes.

## Alternatives ruled out

- **Iteration 3's per-file leave-one-out.** Rejected by finding 1, and it cannot see two
  joint clashes in one file either. Cost of the replacement, per held bundle: with single
  partners only, one `_rebuilt` (k+1 merges) and one trial (up to n merges) — the case-1
  hold costs 2 merges to rebuild and 4 in the trial, on top of `_partners`; with a joint
  clash, per round one `_rebuilt`, one trial, and up to n trials of up to n+1 merges for
  the smallest set (n = bundles on the line, k = named). Iteration 3's `_together`: 1 + n
  own-change trials + up to n carried-change trials, each up to n+1 merges, plus up to n²
  ancestry checks. Same order; this one stops after one trial when the singles explain
  everything.
- **Leaving a named partner's dependents out of the search** (my first draft; iteration
  3's `on_it` rule). Misses the own change of a bundle built on a named partner (M2).
  Cost of the rebuild check instead: one `_rebuilt` per round, k+1 merges.
- **The rebuilt branch as a merge commit** (my second draft). Nondeterministic, measured
  10 of 25 failures (above). The single-parent commit costs one `git commit-tree`.
- **Judging the stranded check on `base_ref`'s tip** (iteration 3). Rejected by findings 2
  and 3 (M3).
- **Judging it on every merge base (`git merge-base --all`).** The base commits a branch
  holds are a prefix of the base's history, so there is one newest one unless the base's
  own history criss-crosses; `--all` would add a loop for that case only.
- **A ddmin-style (binary-split) search for the smallest set.** O(k log n) trials instead
  of O(n) per set; about 15 more lines and an order-dependent result that is harder to
  state. Batches here are tens of bundles at most; not built.
- **Stopping the run when a partner is stranded** (the code review's question, the sizing
  file's proposed seam). Case (3) of the brief requires a hold.
- Carried from iteration 3, still valid: a 3-tuple `held_out` value (would change the type
  three flow readers unpack and break
  `test_a_hold_leaves_the_integration_tree_clean_on_the_line`); putting carried finished
  bundles into `accepted` (they would enter `carried_heads`, the #633 / #695 checks and
  `build_bundle_base(excluded=…)`); changing `_held_by`'s "all of `kept`" (out of scope).

## Known gaps (left for the human)

- **Scope versus the brief's wording.** The brief says "the only new trial is the
  'together' fallback". This patch also has the stranded/past trials (`fails_on`), the
  older-tip reads (two `rev-list`s, not trials) and `_rebuilt`. The brief's own case 3
  defines a stranded trial; the rest answer the carry-forward findings of iterations 1-3.
  `_clash` / `_partners` are reused unchanged for the single partners.
- **The rebuild check assumes the held branch's side wins** every clash with the named
  partners. A real owner may resolve differently; the check proves "a rebuild exists that
  merges", not "every rebuild merges".
- **One smallest set per round.** Where a clash takes any two of three bundles, the set
  found depends on merge order; the rebuild check still guarantees the named sets are
  enough, but an interchangeable bundle is not named. I found no git text clash of that
  shape that a single bundle does not already account for.
- **A change that reaches the line only through a named bundle built on it** (W under a
  named V, both needed) is not named separately — iteration 3's listed gap, unchanged in
  the naming. The advice still works: H rebuilt on V takes W along, and the rebuild check
  passes.
- **`_clash` returns `"line"` after a failed git step** (iteration 3's code review). Then
  no single partner is found that time, so a stranded partner is missed; the together
  search either names own partners or the run stops. Unchanged.
- **Deferred item 2** (a stranded line bundle holds every later bundle built on the moved
  base, after building it) is unchanged and needs the human's call. The undo case shows it
  (V and Y both held); the other stranded cases use `Stacks on` for the unrelated chain.
- **Cost** grows with the line's length times the number of partner sets; only on the
  conflict path, under the fold's lock.
- `cli._results_rc`'s docstring (base `cli.py:722-723`) still describes `"conflict"` as a
  same-wave hold only; cli.py is outside this slice (#740 can take it).

No external dependency was missing: git, the instance `.venv` Python and copier were all
present; nothing was stubbed in place of a tool.

## Commit-readiness

The target has no formatter, linter config or commit hooks (no `.pre-commit-config.yaml`,
no ruff/flake8/black config; CI runs the docs check, the render suite and the linked-issue
check; no linter is installed locally either). All four files compile; `git diff --check`
is clean; no tabs; the longest added line is 99 characters (the files already reach
100-106). T2 (`run-docs-check.sh`): lint clean, 22 pages rendered, link audit OK. T3
(`run-suite.sh`): root suite 24 OK; driver suite 2631 OK (2 skipped); `PDCA-EVIDENCE: root
suite OK, driver suite OK`. The publish commit needs a DCO sign-off (`CONTRIBUTING.md`),
which publish adds. `patch.diff` applies cleanly to the base (`git apply --cached --check`
on a scratch index) and reproduces the worktree byte for byte.

## Housekeeping

Scratch files, all under the worktree's git-ignored `.cache/i739/`: `swc-from-v3.diff`
(iteration 3's same-wave test hunks, applied as the starting point), `v3repo/` (a clone at
base + iteration 3's patch, for the comparison), `mut/` (a clone at base + this patch, for
the mutation and repeat runs), `mutate.py`, `mutations/` and `mutations-summary.txt`,
`show.py` / `show.out` (the printed lines above), `patch*.idx` (scratch indexes),
`patch.diff` / `patch-now.diff`, and the logs `t3-run1.log`, `t3-final.log`, `c4.log`,
`t2.log`, `v3-vs-final.log`. The clones were made with `git clone` into that folder, so the
host repository's worktree list is untouched. Nothing was removed; cleanup is the
harness's. I wrote nothing outside the worktree and this bundle (the gate scripts make
their own `/tmp` dirs). No push, no PR.
