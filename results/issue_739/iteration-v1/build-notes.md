# Build notes — #739 hold a cross-wave clash at the line fold

Target: eduralph/pdca-harness, built and verified on the folded line
`pdca-integration/main-r547f8028520f` at `9f7c446` (#738 folded on top of `75a886e`), the
worktree's base. `path:line` below: **base** = `9f7c446`, **new** = the patched tree. The
brief's anchors are on `75a886e`; they moved by a few lines with #738
(`_held_by` 1743 → 1747, `_clash` 1770 → 1774, `_partners` 1817 → 1821, the fold hold
638 → 642, `_carry_finished` 1259 → 1356, `_announce_conflict_holds` 1435 → 1532, the fold
block `flow.py:2862-2879` → `2977-2999`).

## What changed

### `template/src/pdca_harness/integrate.py`

- `fold` takes two new keywords (new 367-368; base 365): `on_line` (name → head of bundles
  the line carries that `accepted` does not list — the carry's finished ids) and `across`
  (filled with each cross-wave hold → its stranded partners). Docstring for `held_out`
  extended (base 471-484).
- The fold's conflict branch (base 641-648 → new 656-673): `_held_by` is tried first exactly
  as before (same-wave, #674). When it gives nothing — or no same-wave bundle was kept yet —
  `_held_on_line` is tried; a hold is recorded in the same `held_out` (so the flow's
  `held_conflict` and `_runnable` see it unchanged) and, when given, in `across`. The old
  condition `... and kept and ...` moved into the `_held_by` call so `_held_on_line` also runs
  for the first bundle of a wave (case 4's H, case 1 when Y sorts first).
- New `_held_on_line` (new 1801-1861), next to `_held_by`. The rule, by trial merges only:
  1. `head` must merge cleanly onto `<base_remote>/<base>` alone, else None → the fold stops
     (the brief's first condition).
  2. The bundles on the line = each `on_line` head the line actually carries (`_carries`)
     then `took` (merged by this fold or found on the line, merge order).
  3. `_clash` (unchanged, base 1774) on the commit where the line leaves the base
     (`_cut_point(wt, "HEAD", base_ref)`, base 1524), with `under` from `_built_on` (base
     1849) — the same three calls the carry makes (base 696-706). `"batch"` → its partners.
  4. Any kind but `"base"`: the "together" trial (root + every line bundle + head) conflicts
     at the head → all line bundles, as `_held_by` names all of `kept` (base 1771) — less any
     the head already holds (see "fix found by refutation" below).
  5. `stranded` = partners whose own head does not merge onto the real base alone
     (`_trial(base, [partner head])`, the brief's case-3 tell).
  Git failures inside give None (stop on the original conflict), tree errors re-raise —
  `_clash`'s own convention (base 1815-1818).
- `_held_by` docstring (base 1756-1760): it said the fold "stops on it as before"; now says
  the fold then tries `_held_on_line`. Code untouched.
- Module docstring (base 63-68): one clause added for #739. Not a function docstring, but
  it states what the fold does on a conflict and would be false otherwise.
- `_clash` and `_partners` are not touched: the #694 carry's contract is unchanged.

### `template/src/pdca_harness/flow.py`

- `_fold_lines` passes `on_line` / `across` through (base 1149-1191 → new 1150-1197).
- `_carry_finished` takes `on_line` and, only where it seeds `integ` / `folded_tips` (the
  line the run then builds on), records `{name: heads[name]}` for each id it carried (base
  1484-1485 → new 1497-1499). Every carried name is in `heads` (clean ⊆ state-clean).
- New `_line_hold` (new 1546-1595): the wording for a cross-wave hold, per partner group:
  stranded → "rebuild issue_A's branch on the new origin/main (update it from …)", without
  blaming the held bundle; a declared prerequisite (`waves.declared_deps`) → "rebuild
  issue_21's branch on issue_10's", no `Conflicts with` proposal; any other → the existing
  `_CONFLICT_STEP` proposal (base 1244), single-sourced.
- `_announce_conflict_holds` / `_report_conflict_holds` (base 1532 / 1545 → new 1598 /
  1620) take `cfg` and `across`; a name not in `across` prints exactly the old same-wave
  line. A cross-wave hold's announce line carries partners, files *and* the step (the brief's
  case 5 asserts all three on one line); the end-of-run line repeats it.
- `_drive_and_act`: `held_across` (new 2777) beside `held_conflict`; `finished_on_line` fed
  to the carry (new 2852-2857) and to the fold (new 3084); the report call (new 3123). The
  holds map is unchanged: a cross-wave hold is in `held_conflict`, so it reads `"conflict"`.
- Docstrings: `_drive_and_act` `holds` ("conflict" now covers #739), `_runnable`
  `conflict_held` (base 729-731). `Sequence` added to the `collections.abc` import.

## Why the cut point and not the current base (the one real design decision)

`_partners` names a partner only when `trial(X, [partner, head])` stops at the head
(base 1837-1839). Judged on the current `origin/main`, case 3's A never gets named: A itself
does not merge onto the moved main, so the trial stops at index 0, `_clash` returns `"line"`,
and the together trial also stops at A — the run would stop, the opposite of decision 2.
The brief's own text points the same way: it lists "a line bundle cut from the old `main`"
among the bundles `_partners` names, and tells case 3 apart by the partner's head not merging
onto "the *current* base". Judging on the commit the line was cut from (where every line
bundle was merged) is also `_held_by`'s stance (it judges on `pre`, the line's own ground).
Refutation M2 (below) shows case 3 goes red with `root = base_ref`.

The current base is still checked first (rule 1): case 5's 22 conflicts with the main the
fold took in, so it stops there; and a branch that clashes with both the base and a line
bundle stops too (new test 6; refutation M6 shows that without rule 1 it would be held,
blaming A for a clash with main).

## Tests

New `template/tests/test_flow_cross_wave_fold_holds.py` (copy in this bundle), real git on
`StackFoldGit`, loaded by path as `test_flow_same_wave_conflict.py:36-56` does, exit code via
`cli._results_rc(results, holds=holds)` (base `cli.py:707`):

| case | test | holds | rc |
|---|---|---|---|
| (1) in-batch earlier-wave partner | `test_a_clash_with_an_earlier_wave_bundle_holds_only_that_bundle` | `{Y: conflict}` | 3 |
| (2) finished F carried onto the line | `test_a_clash_with_a_finished_bundle_carried_onto_the_line_names_it` | `{Y: conflict}` | 3 |
| (3) line bundle stranded by moved main | `test_a_line_bundle_a_moved_base_strands_is_named_with_the_fix_for_its_owner` | `{B: base, W: conflict}` | 1 |
| (4) only both partners together | `test_a_clash_only_with_two_line_bundles_together_names_both` | `{H: conflict}` | 3 |
| kept stop: also clashes with base | `test_a_branch_that_also_clashes_with_the_base_itself_still_stops_the_run` | `{}` | 1 |

Fixture notes:
- Case 3 needs an unrelated bundle built *after* the fold. Once main moves, every patched
  wave-1 bundle built on a base of its own (or the real base) carries main's `a.txt` and
  clashes with A on the line, so an ordinary unrelated chain would be held too. The chain is
  R → S (`Stacks on: R`, a seam cut from the line, which has no main `a.txt`) → T; T
  completes in wave 2. `Stacks on` precedent: `test_flow_bundle_base_holds.py:526`.
- Case 4's "together" clash: P renames `shared.txt` → `moved.txt`, R rewrites 7 of its 10
  lines, H edits line 10. Each alone merges with H (git follows the rename; R's lines are not
  H's); after both, `moved.txt` is under git's 50% rename similarity, so H's edit is a
  modify/delete conflict. Checked by hand first in `.cache/` (git 2.53) and asserted in the
  test by real merges in the scratch clone (`_merges`). Region-based line merges cannot give
  a together-only conflict (the union of two separated hunks stays separated), hence the
  rename. H depends on K (on the line, held by H): K must not be named.
- Case 2: the `gh` stub answers OPEN with the branch tip (as `test_flow_bundle_base_holds.py:
  140-148`), which `_finished_head` needs to judge F clean.

### Tests that flip

Only the one the brief names. Baseline on `9f7c446`: 2610 tests OK (skipped 2). After:
2615 OK (skipped 2) = 2610 + the 5 new.

- `test_flow_same_wave_conflict.py::test_a_conflict_with_earlier_wave_work_still_stops_the_run`
  — **before:** asserted `wave 1 did not integrate`, `issue_21's branch`, `STOPPING`, no
  hold line for 21, 30 not built. **After:** renamed
  `test_a_conflict_with_its_own_prerequisite_on_the_line_holds_it_not_the_run`: no
  `did not integrate` / `STOPPING`; one hold line for 21 with `issue_10`,
  `(conflicts in shared.txt)` and `rebuild issue_21's branch on issue_10's`; no
  `Conflicts with: 10` on it or anywhere in stderr; 21's head not on the line; 30 not built,
  PLANNED; holds `{21: conflict}`; rc 1. To assert holds / rc, that file's `_run` now passes a
  `holds` collector and computes `self.rc` (it changes no other test's outcome).
- `test_a_conflict_only_with_a_base_taken_in_mid_wave_still_stops_the_run` — unchanged, still
  green (22 does not merge onto the moved main: rule 1).

Messages as printed (fix applied), for the human:
- (1) `flow: issue_Y held out of the integration fold — its change conflicts with issue_A's, already on the line (conflicts in shared.txt); bundles that depend on it or are its `Conflicts with` partners are held this run. Proposed, for you to confirm: declare `Conflicts with: A` in issue_Y's brief, then rebuild issue_Y on a base that holds issue_A.`
- (3) `flow: issue_W held out of the integration fold — issue_A's branch, already on the line, does not merge cleanly onto origin/main itself: origin/main moved since it was cut, and issue_W was built on the new origin/main (conflicts in a.txt); bundles that depend on it or are its `Conflicts with` partners are held this run. To fold it, rebuild issue_A's branch on the new origin/main (update it from origin/main and resolve the conflicts there), then re-run.`
- (5) `flow: issue_21 held out of the integration fold — its change conflicts with issue_10's, already on the line, and issue_10 is its own prerequisite, which its branch does not hold (conflicts in shared.txt); … To fold it, rebuild issue_21's branch on issue_10's, then re-run.`

## Refuting my own test

**(a) Genuine red? Yes.** `./engine/scripts/run-verify.sh` (the configured C4 gate, run with
`PDCA_BUNDLE` / `PDCA_WORKTREE` set) reverts only the production hunks: the flipped test and
cases 1–4 fail, each on `'did not integrate' unexpectedly found … STOPPING — later waves not
run`; with the fix all 13 tests of both files pass → `PDCA-EVIDENCE: C4 PASS`. The worktree
was byte-identical to patch.diff afterwards. Test 6 passes on both legs by design (it pins a
stop the fix keeps; its docstring says so). Each piece of the fix was also broken on its own
(script in the worktree's ignored `.cache/pdca739/mutate.py`, file restored after each), and
each went red: M1 carry records no heads → case 2; M2 `_clash` on the current base instead of
the cut point → case 3; M3 no together trial → case 4; M4 nothing stranded → case 3; M5 no
prerequisite wording → case 5; M6 no base-alone check → test 6; M7 `on_line` not passed to
the fold → case 2; M8 together naming keeps bundles the head holds → case 4.

**(b) Production path? Yes.** Every case drives `flow._drive_and_act` → the real
`integrate.fold` → `_held_on_line` → real `_clash` / `_partners` / `_trial` merges in the
real integration worktree; case 2 runs the real `_carry_finished` (stderr asserts
`carried issue_F … onto`), case 3 the real `build_bundle_base` (B's #738 hold line asserted).
Stubbed, as in `test_flow_same_wave_conflict.py` / `test_flow_bundle_base_holds.py`: the build
leaf (`_drive_wave`), `_publish_bundle` (pushes real branches to the bare origin),
`publish.draft_texts`, and `gh`. The `integrate.fold` wrapper only calls through, then runs the
case's after-fold hook.

**(c) Fixture includes the fault? Yes.** The clashing branches are real pushed branches; case
3 really moves origin's main after wave 0's fold and asserts W's base holds that commit; F is
really put on the line by the carry; case 4 asserts with real merges that each partner alone
merges and all together conflict at H; test 6 asserts Y really does not merge onto the moved
main.

## Fix found by refutation

M1 first showed a wording bug in my own first version: with F missing, the together trial
named *every* line bundle, including Y's prerequisite Q, and the message then said Q was "its
own prerequisite, which its branch does not hold" — false, Y is built on Q. A bundle whose head
the held branch already holds cannot be what it conflicts with, so the together naming now
leaves those out (`_in_line(..., of=head)`, new 1849-1850), and returns None if that leaves
nobody. Case 4 was changed to pin it: H's prerequisite K is a real patched bundle on the line
and must not be named (M8).

## Alternatives ruled out (with cost)

- **Judge everything on the current base** — not a cost question: case 3 stops (M2).
- **A 3-tuple `held_out` value `(partners, paths, stranded)`** instead of a separate `across`
  dict: changes the type every reader unpacks — `_runnable`'s `conflict_held` comprehension,
  `_announce_conflict_holds`, `_report_conflict_holds` (3 sites in flow.py) — and breaks
  `test_flow_same_wave_conflict.py::test_a_hold_leaves_the_integration_tree_clean_on_the_line`,
  which asserts the 2-tuple `{"issue_Q": (["issue_P"], ["shared.txt"])}`. `across` is one new
  keyword plus one dict, and leaves same-wave holds byte-for-byte as they were.
- **Pass the carried finished bundles in `accepted`** so they land in `took` by themselves:
  zero new fold keyword, but `carried.update(took)` (base 725) would put them in
  `carried_heads`, so the #633 mid-run rewrite check (`_carried_tips`), the #695 end-of-run
  check (`_report_late_rewrites(cfg, accepted, carried_heads, …)`, base 3036) and
  `build_bundle_base(excluded=carried_heads)` would all start judging finished ids — a
  behaviour change outside this slice. `on_line` only names.
- **Smallest partner set for the together case** (leave-one-out): n extra trials of up to n
  merges each, and the brief says the only new trial is the together fallback mirrored from
  `_held_by`, which names all of `kept`.
- **Together fallback inside `_clash`** — the brief forbids it (#694's contract).
- **Skipping rule 1's trial when root is the base** (it repeats `_clash`'s first trial when
  the base has not moved): saves one `git merge` in a detached worktree per conflict being
  classified, costs a `_rev` comparison branch (~3 lines). Kept the plain version.

## Known gaps (not in the brief's cases; left for the human)

- `_runnable`'s line for a `Conflicts with` partner of a held bundle (new `flow.py:857-864`)
  still says "wait until W is rebuilt on a base that holds issue_A". For a *stranded* hold the
  right step is A's rebuild; W needs no change. Fixing it means passing `across` into
  `_runnable` — not asked for.
- `cli._results_rc`'s docstring (base `cli.py:722-723`) still describes `"conflict"` as a
  same-wave hold only. cli.py is outside this slice's files; #740 (docs) can pick it up.
- A held bundle whose partner is stranded *and* whose own change also clashes with that
  partner gets only the "rebuild the partner on the new base" step; after that rebuild a later
  run reports the remaining clash. The brief's case-3 tell (partner does not merge onto the
  current base) cannot separate the two by trial alone.
- "Bases are not pinned to the run's start" — stated non-change, nothing pins them; case 3
  asserts only that W's base holds the moved main.

## Commit-readiness

The target has no formatter or lint config and no pre-commit hooks (no
`.pre-commit-config.yaml`; ruff / pyflakes not installed here). All four files compile; no
added line is over 100 columns (the files' existing width; the 3 longer lines in flow.py are
pre-existing); no tabs or trailing spaces in added lines. The publish commit needs a DCO
sign-off (`CONTRIBUTING.md`), which publish adds.

## Housekeeping

- One scratch file landed outside the roots by mistake: the baseline suite log at
  `/tmp/pdca739-baseline.txt`. Everything else scratch is under the worktree's git-ignored
  `.cache/pdca739/` (the git experiment for case 4, `show.py`, `mutate.py`). Not removed —
  cleanup is the harness's.
- After writing these notes I renamed one local in `fold` (`line` → `cross`: `fold` already
  binds `line` to origin's tip, read only before the merge loop, so nothing broke, but the
  reuse was a trap) and reflowed three docstring paragraphs. Everything below was re-run on
  that final tree.
- Final runs on the final tree: C4 (`./engine/scripts/run-verify.sh`) → `PDCA-EVIDENCE: C4
  PASS`, worktree byte-identical to patch.diff after it; T3 (`./engine/scripts/run-suite.sh`)
  → root suite 24 OK, driver suite 2615 OK (skipped 2), exit 0; refutations M1–M8 all red.
