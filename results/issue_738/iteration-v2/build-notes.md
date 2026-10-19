# Build notes — #738 (iteration 2): hold a bundle whose own base cannot be built

Base: `pdca-integration/main-r547f8028520f` at `75a886e` (the worktree's HEAD). "base:N" is a
line on `75a886e`; "now:N" is the same file with `patch.diff` applied. All paths are under
`template/`.

## Starting point

I applied iteration 1's `patch.diff` (`results/issue_738/iteration-v1/patch.diff`; it
applies cleanly to `75a886e`) and changed only what the carry-forward asks for, plus one
hole I found while doing it. Kept from iteration 1, unchanged: the catch-and-hold in
`_bundle_bases` (flow.py now:1040-1048, base:1019-1022 re-raised), the wave loop's hold
instead of `STOPPING` (now:2868-2879, base:2759-2770), `_runnable`'s `unbuilt` partner check
(now:690, now:770-771), `_results_rc`'s exemption for the `"base"` reason (cli.py now:702,
now:740-741; base:728), the extra fields on `_Rewritten` (integrate.py now:128-142), the
fetch wording in `build_bundle_base` (integrate.py now:847-854, base:835) and the
`checkout -B` wording (now:873-874, base:853), and iteration 1's edits to four older tests
that pinned the old `STOPPING`.

## The three carry-forward findings

**1. C5 — a no-fix bundle counted as a PR (exit 1 instead of 3).** Iteration 1 ran
`_built_on_lost_heads` right after pointing the wave's bundles, before they were built or
published, and put the member in the failure set right there. A bundle closed with no
patch publishes nothing (publish.py:175), so it has no PR. I removed `_built_on_lost_heads`
and split it in two:

- At hold time, `_note_base_rewrites` (flow.py now:1080) only records each rewrite a base
  refused: the branch, the heads it lost, the bundles held for it, and the PRs the refusal
  already named (`base_rewrites`, declared now:2793, filled now:2876).
- At the end of the run, `_report_stale_prs` (now:1092) reads what the run's PRs hold
  through `_heads_taken` (now:1129; base:1037), which keeps only bundles that pushed a
  branch this run. It names each PR on a lost head that the refusal did not already name,
  and returns the members that a PR holds a lost head of. Only those become `"rewritten"`
  (now:3030-3031, now:3045). It does not run after the loop stopped on the line
  (`line_stopped`), the same rule `_report_late_rewrites` has (base:2914-2916).

New test: `test_a_bundle_closed_with_no_patch_on_the_stale_line_is_no_pr`. S is closed with
no patch and goes through the production `flow._publish_bundle`. It asserts no publish
record, no `fix/S` on origin, no line naming S as a PR, `holds == {"B": "base"}`, exit 3.

**2. Hold lines that promised what the run does not do.**

- (a) The `Conflicts with` partner line (flow.py now:863-868) no longer says "the re-run
  builds issue_B first". It now follows #674's wording (base:846-853): "To build it, wait
  until issue_B is built, once what its hold line names is fixed, and its PR merges into
  main (org/repo), then re-run." That is true whatever ids the re-run names. I did not use
  "re-run the same ids", because that can fail too: if B is skipped in the re-run (say,
  the carry of A fails) or held by #647, X's partner check does not see B and X is built
  on the plain base. That gap is older than this patch. To fill in "into main (org/repo)",
  the target is now resolved for a bundle with an unbuilt partner too (now:777-778; base:768-769). It is one line per
  partner, as #674 does.
- (b) `_announce_base_holds` (now:1061-1071) now says: "issue_B is not built this run: a
  bundle that depends on it is skipped, one tied to it by `Conflicts with` is held, and the
  rest of this wave goes on." "Skipped" is the word `_runnable` uses for a dependent
  (base:835-837). Saying "this wave" instead of "the run" also keeps the line true in the
  deferred non-last-wave rewrite case below, where the next fold stops the run.

Every base-hold case asserts the new ending and the absence of "held with it" and "the rest
of the run goes on" (test helper `_base_held`).

**3. No test of a hold before the last wave.** New test:
`test_a_hold_before_the_last_wave_carries_over_two_folds`. It has four waves and B's fetch
fails in wave 1. It asserts three folds ran (after waves 0, 1 and 2). C (`Depends on: B`,
wave 2) and D (`Depends on: C`, wave 3) are skipped. X (`Depends on: V`, `Conflicts with:
B`, wave 3) is held two folds after B. V and U are built after the fold that followed B's
wave, and the line holds A, Z, W and V. No `STOPPING`, `holds == {"B": "base"}`, exit 1.

## A hole I closed beyond the carry-forward: a rewrite mended mid-run

B's hold line tells the user to restore the branch. If they do it before the next fold,
that fold re-checks every carried branch against the line and every published PR
(integrate.py `_carried_tips`, base:1089-1125) and goes on. With iteration 1's logic and
with my first version, the end of the run would still have named S's PR as stale, failed
the run, and kept A out of the end-of-run check, which could hide a second rewrite later.
So a fold that passes clears `base_rewrites` (flow.py now:2992-2995). The member is then
judged again at the end like any other branch. New test:
`test_a_rewrite_mended_before_the_next_fold_fails_nothing` asserts `holds == {"B": "base"}`,
exit 3, and no stale line. The brief's "excluded from the end-of-run check, as today" still
holds for the case that exists today (a refusal after the run's last fold). Before this
patch the run always stopped there, so there was no later fold.

## How the brief's cases map to tests (template/tests/test_flow_bundle_base_holds.py)

| Brief case | Test | Holds / exit |
|---|---|---|
| (1) moved base | `test_a_base_that_moved_under_a_prerequisite_holds_only_its_dependent` | `{B: base}` / 3 |
| (2) rewritten prereq | `test_a_prerequisite_rewritten_after_the_fold_holds_only_its_dependent` | `{B: base}` / 3 |
| (3) failed fetch | `test_a_fetch_that_fails_for_one_base_holds_only_that_bundle` | `{B: base}` / 3 |
| (4) refused push | `test_a_push_origin_refuses_holds_only_that_bundle` | `{B: base}` / 3 |
| (5) partner | `test_a_conflicts_with_partner_of_a_held_bundle_is_held` | `{B: base}` / 1 |
| (6) stale line | `test_a_pr_cut_from_the_stale_line_after_a_rewrite_hold_is_named` | `{B: base, A: rewritten}` / 1 |
| (6), own base built earlier in the wave | `test_a_base_built_before_the_rewrite_in_the_same_wave_is_named` | `{E: base, A: rewritten}` / 1 |
| (7) dependent | `test_a_dependent_of_a_held_bundle_is_skipped_and_fails_the_run` | `{B: base}` / 1 |
| finding 1 | `test_a_bundle_closed_with_no_patch_on_the_stale_line_is_no_pr` | `{B: base}` / 3 |
| finding 3 | `test_a_hold_before_the_last_wave_carries_over_two_folds` | `{B: base}` / 1 |
| mended rewrite | `test_a_rewrite_mended_before_the_next_fold_fails_nothing` | `{B: base}` / 3 |

Case (6)'s line now reads: "flow: issue_S is cut from <line> at <tip>, which holds <head>
from issue_A's branch origin/fix/A: that branch was rewritten without it, as the hold line
of issue_B above says, so issue_S's PR holds those old commits too. Restore origin/fix/A to
<head> or a commit that contains it; or rebuild issue_S's PR on the rewritten branch before
it merges."

One assertion was added to an older test:
`test_flow_dependency_scoped_bases.py` `test_a_later_base_that_reads_the_rewrite_holds_...`
now also asserts that no PR the hold named is named again at the end. Without it, mutant M6
below stayed green.

## Judgment calls the human should check

1. **Stale PRs are judged by what the refusal found.** `_report_stale_prs` takes a head as
   lost when the refusal judged it lost. It does not fetch again: the brief keeps the
   member out of the end-of-run check. If someone restores the branch after the run's last
   fold (while the last wave builds), the run still names those PRs and exits 1. That is a
   false failure, on the cautious side. The line is worded in the past tense ("was
   rewritten without it, as the hold line above says"), so it stays true. A fresh check
   would cost about 25-30 lines in `_report_stale_prs`: a fetch per target, an ancestry
   check per head, and an "unchecked" path when the fetch fails. I did not add it here.
2. **No stale report after the loop stopped on the line**, the same rule as the existing
   late-rewrite check. In the usual case (a rewrite hold before the last wave, then the
   next fold stops on that rewrite), the fold's `STOPPING` line names the same PRs
   (`_rewrite_stop`, integrate.py base:1145-1148). If the fold instead stops on something
   else (its fetch fails twice), a stale PR built after the hold is not named. The run
   exits 1 either way, and B's hold line already says to restore the branch.
3. **Exit 3 for case (2)** follows the brief ("(1)-(4) ... exits 3"). The `_results_rc`
   docstring now says so (cli.py now:709-716, now:722-725). Whether that rule or #695's
   "line holds commits no PR holds → 1" should win is still the deferred human item below.
   I only made the docstring match the code.
4. **`held_base` in `_runnable`'s `held=` set** (flow.py now:2808-2809) changes nothing today:
   a base-held bundle is never COMPLETE, so its dependents are already "not ready"
   (base:778-780). Mutant M7 shows no test can tell it apart. I kept it because the brief
   asks for a held set that `_runnable` honours for prerequisites. Removing it is a
   one-line change with the same behaviour.
5. **The fetch wording is unchanged from iteration 1.** "Check that remote (its URL, the
   network, credentials) and that checkout, then re-run" also covers a missing checkout or
   a worktree that cannot be created (the adversary called this minor). Telling those
   apart would need a `_FetchFailed` subclass in `_fetch` (about 8 lines). Both cases are
   rare: the fold before this wave used the same checkout and worktree.

## Deferred human findings — not changed

- A rewrite hold before the last wave: the next fold re-checks A and stops the run
  (`deferred-findings.json` items 2 and 4). I did not change that behaviour. The only thing
  I changed nearby is the hold line: it no longer promises "the rest of the run goes on".
- Exit 1 vs 3 for the same rewrite, depending on whether a dependent's base reads it (item
  3): exit 3 is kept, per the brief (see call 3).
- Items 1 and 5-10 (prior-art search, target confusion, `Depends on` for #723/#727-#729,
  tracker record, case (6) scope, success-criterion wording, red leg for case (2)) are about
  the plan or the review setup, not about this code.

## Alternatives ruled out

- **Print a warning when S is pointed, and decide the exit code after publish.** That
  gives two lines about one PR, and the first one can be about a PR that never exists (the
  no-fix case), which is the false claim the review flagged.
- **Report stale PRs right after each wave's publish.** In a wave before the last, the next
  fold stops on the same rewrite and names the same PRs, so they would be named twice. The
  end of the run matches the existing late-rewrite check.
- **Drop the exclusion and let the end-of-run check judge A** (1 line, at the filter
  now:3032). Ruled out by the brief: it names the line's rewrite a second time and turns
  case (2) into exit 1.

## Refute-your-own-test (forced)

- **(a) Genuine red? Yes.** The project's C4 gate (`engine/scripts/run-verify.sh`, run with
  `PDCA_BUNDLE`/`PDCA_WORKTREE` set, wrapped in `timeout`) passes on the final patch. Green
  leg: 11 + 25 + 15 tests OK. Red leg (production hunks reverted, tests kept): all 11 new
  tests FAIL, plus the 4 updated older tests. Each failure is
  `AssertionError: 'STOPPING' unexpectedly found` (no import failures):
  `PDCA-EVIDENCE: C4 PASS`. Red against iteration 1: with iteration 1's production code,
  all 11 fail. With iteration 1's code and only its two hold-line wordings swapped for the
  new ones, the no-patch case and the mended case still fail (iteration 1 names `issue_S`
  as a stale PR). That is the C5 finding, reproduced. Mutants, one at a time (each run with
  the gate's own `PYTHONPATH=src python3 -m unittest tests.<module>` and a timeout, file
  restored after; checksums matched):

  | Mutant | Tests that go red |
  |---|---|
  | M1 no `base_rewrites.clear()` after a passing fold | the mended case |
  | M2 every accepted bundle counted as a PR (no pushed filter) | the no-patch case |
  | M3 iteration 1's hold-line wording | all 11 base-hold cases |
  | M4 iteration 1's partner promise | (5) and the four-wave case |
  | M5 `unbuilt=frozenset()` | (5) and the four-wave case |
  | M6 also name PRs the hold already named | the updated #727 test |
  | M7 `held_base` out of `held=` | none (redundant, see call 4) |
  | M9 no stale-PR report | (6), (6) own base, the updated #727 test |

- **(b) Production path? Yes.** The tests call `flow._drive_and_act` and
  `cli._results_rc`. `integrate.build_bundle_base`, `_bundle_bases`, `_runnable`,
  `integrate.fold`, `_report_stale_prs`, `_report_late_rewrites` and every git step run for
  real against a bare origin. Stubbed: the build and sign-off leaves, publish's mechanics
  (a real cut and push with git), `gh`, and for one bundle only, the fetch (the real
  `_prepare_worktree` runs with its `git fetch` failing) and the push of one base branch
  (so `build_bundle_base`'s own refusal fires). The no-patch bundle goes through the
  production `flow._publish_bundle` and `publish.publish`. No stub touches the `except`
  the fix adds.
- **(c) Fixture includes the fault? Yes.** A real clashing `a.txt` pushed to `main`; a
  real force-push of `fix/A` after the line took it, or after B's base took it; a real
  `git fetch` failure inside the real `_prepare_worktree`; a real refused push path; a real
  restore of `fix/A` on origin before the fold. Git confirms S's and B's published heads
  hold the lost commit. The unrelated bundles (W, V, U) are in the same runs and must reach
  COMPLETE.

## Commit-readiness

The target configures no formatter, linter or commit hook: no `.pre-commit-config.yaml`,
no ruff/black/flake8 config, only `*.sample` files in `.git/hooks`, no `core.hooksPath`.
CONTRIBUTING.md asks for the DCO sign-off (publish adds it) and green suites.
`git diff --check` is clean, every added line is at most 100 columns (the file's style),
and all touched files compile. pyflakes/ruff are not installed. A small AST scan found no
unused imports in the new test file or in flow.py.

## Suite runs (final tree)

- C4 (`engine/scripts/run-verify.sh`): PASS, as above.
- T3 (`engine/scripts/run-suite.sh`): root suite 24 tests OK; driver suite 2605 tests OK
  (2 skipped). That is 3 more than iteration 1's 2602: three new cases.
- T2 (`engine/scripts/run-docs-check.sh`): docs lint clean, 22 pages rendered, link audit
  OK. The patch touches no docs.

## Housekeeping slips (mine)

- My first C4 run's output went to `/tmp/claude-738-c4.log`, outside the two roots I may
  write to. It holds only test output. I did not delete it (no `rm`). Later runs piped
  output straight to the terminal instead.
- To make `git diff` include the new test file I marked it intent-to-add (`git add -N`),
  then cleared that mark (`git reset -- <file>`). The worktree index is as I found it, and
  the test file is untracked, as iteration 1 left it.
