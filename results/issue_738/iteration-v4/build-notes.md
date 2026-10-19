# Build notes — #738 (iteration 4): hold a bundle whose own base cannot be built

Base: `pdca-integration/main-r547f8028520f` at `75a886e` (the worktree's HEAD). "base:N" is a
line on `75a886e`; "now:N" is the same file with `patch.diff` applied; "v3:N" is iteration 3's
tree. All paths are under `template/`.

## Starting point

I applied iteration 3's `patch.diff` (`results/issue_738/iteration-v3/patch.diff`; it applies
cleanly to `75a886e`) and changed only what the round-3 carry-forward asks for. Everything
else from iteration 3 is kept unchanged: the catch-and-hold in `_bundle_bases` (flow.py
now:1043, base:1019-1022 re-raised), the wave loop's hold instead of `STOPPING` (now:2896-2907,
base:2759-2770), `_runnable`'s `unbuilt` partner check (now:2848), `_announce_base_holds`
(now:1061), `_results_rc`'s exemption for `"base"` (cli.py now:742), the two fetch-failure
classes and their steps (integrate.py now:144-152, now:857-872), `lost_now` (integrate.py
now:1315), `base_rewrites.clear()` (flow.py now:3023), and the edits to the two older test
files.

Size of this round, production only, against iteration 3's tree: cli.py +2 -2, flow.py +55
-54, integrate.py +12 -14 (69 insertions, 66 deletions). The logic change is two filter
conditions removed (flow.py now:1125, now:1127). The rest is wording, docstrings, and the
removal of a field that the fix makes unused.

## The round-3 findings

**1. C5: after a second rewrite, a stale PR was not named.** Iteration 3's `_report_stale_prs`
(flow.py v3:1117-1121) checked only the PR heads that the refusal had already found lost
(`if h in lost`). The member is also left out of `_report_late_rewrites` (the brief requires
that: flow.py now:3061, base:2914). So a PR on a head the branch still had at the refusal,
and lost after it, was checked by nothing. That is the reviewer's probe: S is cut from the
line at a1, the refusal (D's) finds only a2 lost, then fix/A is force-pushed again and loses
a1 too.

The same filter missed a second route, which I found while working on the first one. B's own
base takes a2, newer than the line's a1 (fix/A was fast-forwarded after the fold). E's base,
built later in the same wave, refuses a rewrite and judges only the line's a1, because B was
not published yet. Its hold line says "Restore origin/fix/A to a1 or a commit that contains
it". If the human does exactly that, the line is whole again, but B's PR holds a2, which
fix/A no longer has. Iteration 3 never looked at a2, so it named nothing, and the run exited
3.

Fix: `_report_stale_prs` (flow.py now:1091-1153) now builds its list from every head of the
member that a PR of the run holds: all of `line_prs[m]` and every own base holding `m`
(now:1123-1127). It reads the branch again once (`integrate.lost_now`, now:1133), then:

- every PR on a head lost now makes the member `"rewritten"` (exit 1);
- a PR that no refusal named gets one stderr line (now:1147-1152);
- a PR that a refusal named gets no second line.

The guard `if not on: continue` (now:1128) stays. With no PR on any head of the member, the
branch is not read again (case (2) stays exit 3, with no extra fetch).

**Why the line is not checked again.** Every base refusal of a carried member already names
the line. That holds by construction:

- A fold checks each carried branch's tip against every taker (the line's head and every PR
  head in `taken`; `_carried_tips`, integrate.py base:1108, :1122) and raises if one is lost.
- The fold then merges that same tip (base:529, :624) and records it as the line's head
  (`took[d.name] = head`, base:656; `carried.update(took)`, base:721).
- So the line's head contains every PR head published before the last fold. A refusal can
  only see PRs published before the last fold (`taken` is built before the wave's bases,
  flow.py now:2901).
- `build_bundle_base` judges the line's head among the takers (base:837-843). If any PR head
  is lost, the line's head is lost too, so the refusal always names the line, and its
  "Restore … to <line head> or a commit that contains it" covers every older head the line
  holds.

The docstring says this in two sentences (now:1109-1112).

**Wording.** The stale-PR line is now one neutral sentence that is true for all three routes
(head lost before the refusal, lost after it, or never judged by it): "issue_S is cut from
<line> at <tip>, which holds <h> from issue_A's branch origin/fix/A, and that branch does not
contain <h> now: the hold line of issue_D above names it rewritten, so issue_S's PR holds
commits it no longer has. Restore … or rebuild issue_S's PR …". Iteration 3's "as the hold
line says, and still lacks it" is false for the second and third routes. The "could not read
again" line dropped "to see whether it was restored" for the same reason (now:1137-1141).

**Dead data removed.** `_Rewritten.lost` (integrate.py v3:140) and the `lost` field of
`_BaseRewrite` were only read by the filter I removed. I removed both (integrate.py
now:128-141, :880-882; flow.py now:1074-1088) instead of keeping state nothing reads.

**2. `base_rewrites.clear()` was not pinned by a test** (flow.py now:3023). New test
`test_a_rewrite_after_the_fold_that_found_it_mended_is_named_at_the_end` (test :717). It is
the adversary's P1: fix/A is rewritten after fold 0 (B held), restored before fold 1 (the
fold goes on and clears), and rewritten again after fold 1 in the last wave. It asserts the
end-of-run check names it ("No fold of this run ran after the rewrite"), with
`holds == {"B": "base", "A": "rewritten"}` and exit 1. Replacing `clear()` with `pass` makes
it fail (holds `{"B": "base"}`, exit 3).

**3. `if not on: continue` was not pinned** (flow.py now:1128). New test
`test_a_branch_no_pr_holds_a_commit_of_is_not_read_again_at_the_end` (test :673). It is the
adversary's P3: case (2)'s shape, with every fetch failing once W is published. It asserts no
"could not read issue_A's branch" line, that the late check's unchecked line names Z and not
A (which also pins the exclusion the brief requires), and
`holds == {"B": "base", "Z": "unchecked"}`, exit 1. Without the guard the run adds
`"A": "unchecked"` and prints the line with an empty PR list.

## How the brief's cases map to tests (template/tests/test_flow_bundle_base_holds.py)

| Brief case | Test (line) | Holds / exit |
|---|---|---|
| (1) moved base | `test_a_base_that_moved_under_a_prerequisite_holds_only_its_dependent` (:346) | `{B: base}` / 3 |
| (2) rewritten prereq | `test_a_prerequisite_rewritten_after_the_fold_holds_only_its_dependent` (:361) | `{B: base}` / 3 |
| (3) failed fetch | `test_a_fetch_that_fails_for_one_base_holds_only_that_bundle` (:379) | `{B: base}` / 3 |
| (3), missing checkout | `test_a_checkout_missing_while_one_base_is_built_holds_only_that_bundle` (:392) | `{B: base}` / 3 |
| (3), worktree | `test_a_worktree_that_cannot_be_made_for_one_base_holds_only_that_bundle` (:406) | `{B: base}` / 3 |
| (4) refused push | `test_a_push_origin_refuses_holds_only_that_bundle` (:426) | `{B: base}` / 3 |
| (5) partner | `test_a_conflicts_with_partner_of_a_held_bundle_is_held` (:440) | `{B: base}` / 1 |
| (6) stale line | `test_a_pr_cut_from_the_stale_line_after_a_rewrite_hold_is_named` (:462) | `{B: base, A: rewritten}` / 1 |
| (6), restored before the end | `test_a_rewrite_restored_while_the_last_wave_builds_fails_nothing` (:490) | `{B: base}` / 3 |
| (6), cannot read again | `test_a_rewritten_branch_that_cannot_be_read_again_names_each_pr_to_check` (:512) | `{B: base, A: unchecked, Z: unchecked}` / 1 |
| (6), no-patch bundle | `test_a_bundle_closed_with_no_patch_on_the_stale_line_is_no_pr` (:537) | `{B: base}` / 3 |
| (6), own base built earlier | `test_a_base_built_before_the_rewrite_in_the_same_wave_is_named` (:557) | `{E: base, A: rewritten}` / 1 |
| (6), newer head, line restored (**new**) | `test_a_newer_head_a_base_took_is_named_once_the_branch_is_put_back_for_the_line` (:586) | `{E: base, A: rewritten}` / 1 |
| (6), rewritten again (**new**, reviewer's probe) | `test_a_pr_on_a_head_the_branch_kept_at_the_refusal_is_named_once_it_is_lost` (:624) | `{D: base, A: rewritten}` / 1 |
| (6), no PR, no re-read (**new**, P3) | `test_a_branch_no_pr_holds_a_commit_of_is_not_read_again_at_the_end` (:673) | `{B: base, Z: unchecked}` / 1 |
| mended before the next fold | `test_a_rewrite_mended_before_the_next_fold_fails_nothing` (:693) | `{B: base}` / 3 |
| rewritten after that fold (**new**, P1) | `test_a_rewrite_after_the_fold_that_found_it_mended_is_named_at_the_end` (:717) | `{B: base, A: rewritten}` / 1 |
| (7) dependent | `test_a_dependent_of_a_held_bundle_is_skipped_and_fails_the_run` (:748) | `{B: base}` / 1 |
| hold before the last wave | `test_a_hold_before_the_last_wave_carries_over_two_folds` (:761) | `{B: base}` / 1 |

Three older tests in this file changed only their wording assertions, to the new sentences:
:462 (case 6), :512 (cannot read again) and :557 (own base built earlier).
`test_flow_dependency_scoped_bases.py:524` now looks for "and that branch does not contain",
the new stale line's own phrase. The old phrase would never match again and would leave that
"none is named again" assertion empty.

## Judgment calls the human should check

1. **More end-of-run fetches, so "unchecked" can now happen in more runs.** The re-read now
   runs whenever some PR of the run holds any head of a refused member, not only a head the
   refusal found lost. If that fetch fails, the member is `"unchecked"` and the run exits 1.
   That matches #695: the end-of-run check fetches every carried branch and fails the run when
   it cannot. A run where no PR holds the member's commits (case (2)) still does no fetch and
   stays exit 3 (pinned by the P3 test).
2. **The "could not read again" line lists every PR on a head of the member.** That includes
   PRs on heads the refusal found held, since a second rewrite could have taken those too.
3. **A PR a refusal named, on a head still lost, gets no second line, but still fails the
   run** (as in iteration 3). The hold line already named it, with the same fix.
4. Carried over, unchanged: a branch deleted after the refusal is left alone at the end of
   the run (`lost_now` returns nothing, integrate.py now:1334-1335, as `rewritten_carried`
   does at base:1247); exit 3 for case (2), per the brief.

## Deferred human findings — not changed

The deferred items (`deferred-findings.json`) are not build work, and I did not touch them.
They are: a rewrite hold in a non-last wave stops the run at the next fold; exit 1 vs 3 for the
same rewrite depending on whether a base reads it; and the plan, review-setup and prior-art
items. The test file's docstring still says plainly that a rewrite not restored, or a moved
`main`, can stop the run at the next fold (test :13-20).

## Alternatives ruled out

- **Keep iteration 3's filter, and add a second pass for heads not in `lost`.** This would
  need a second loop and a second message. It costs about 15 more lines than removing the
  filter, and gives no case a different answer.
- **Keep two wordings** ("as the hold line says, and still lacks it" when the head was in
  `lost`, "rewritten again" otherwise). This keeps the `lost` field (5 lines across
  integrate.py and flow.py) plus an `if` with a second string. "Rewritten again" is also false
  for the newer-head route (`:586`): there one rewrite lost both heads, and the refusal judged
  only the line's. One neutral sentence is true in all three routes.
- **Also re-check the line, and name it when no refusal did.** By the construction argument
  above, a refusal of a carried member always names the line, so this branch can never run.
  It would be about 10 lines (a `carried` parameter, a judgment, a `_late_line_rewrite` call)
  of dead code.
- **Drop the exclusion and let `_report_late_rewrites` re-read the member** (1 line,
  flow.py now:3061). The brief rules it out for case (6) ("the name is Do's choice, the
  behaviour is not"). It would also name the rewrite a second time, and turn case (2) into
  exit 1.

## Refute-your-own-test (forced)

- **(a) Genuine red? Yes.** I ran the project's C4 gate (`engine/scripts/run-verify.sh`, with
  `PDCA_BUNDLE`/`PDCA_WORKTREE` set, under `timeout`) on the final `patch.diff`. Green leg:
  19 + 25 + 15 tests OK. Red leg (production hunks reverted, tests kept): 19/19 new tests
  FAIL, plus 2 + 2 updated older tests. Every one of the 23 fails on
  `AssertionError: 'STOPPING' unexpectedly found` (no import errors). Result:
  `PDCA-EVIDENCE: C4 PASS`.

  Red against iteration 3 (its `flow.py`, this round's tests): the two new tests for the
  reviewer's finding fail on the behaviour itself (`0 != 1`: no line names S, or B). Three
  older tests fail only on the changed wording. The P1 and P3 tests pass there, as they
  should, since iteration 3 already had those two lines. They are pinned by mutation instead.

  Mutants, one at a time, each run on all three modules, with the file restored after each
  (byte-compared):

  | Mutant | Tests that go red |
  |---|---|
  | M1 `base_rewrites.clear()` → `pass` (flow.py now:3023) | P1 test (:717) |
  | M2 drop `if not on: continue` (now:1128) | P3 test (:673) |
  | M3 put back iteration 3's `if h in lost` filters (now:1125, :1127) | newer-head test (:586), reviewer's probe (:624) |
  | M4 name a PR a refusal already named (`if o not in named` → `if True`, now:1147) | reviewer's probe (:624), `test_flow_dependency_scoped_bases.py:503` |
  | M5 drop the exclusion from the end-of-run check (`list(accepted)`, now:3061) | 7 tests: case (2) (:361), case (6) (:462), no-patch (:537), reviewer's probe (:624), P3 (:673), `test_flow_dependency_scoped_bases.py:503`, `test_integrate_carried_rewrite_late.py:298` (1d) |

- **(b) Production path? Yes.** The tests call `flow._drive_and_act` and `cli._results_rc`.
  The real `_bundle_bases`, `_runnable`, `integrate.build_bundle_base`, `_prepare_worktree`,
  `_fetch`, `integrate.fold`, `_report_stale_prs`, `integrate.lost_now` and
  `_report_late_rewrites` all run against a bare origin.

  Stubbed: the build and sign-off leaves, publish's mechanics (a real cut and push with git),
  and `gh`. For one bundle only: the fetch (the real `_prepare_worktree` runs with `git fetch`
  failing) and the push of one base branch. Late in two cases: every integrate fetch. No stub
  touches the `except` blocks the fix adds.
- **(c) Fixture includes the fault? Yes.** All of these are real git, in the bare origin or
  the human's clone:
  - the fast-forward of fix/A to a2;
  - its reset to a1 (`git branch -f`);
  - the force-push to a commit holding neither;
  - the restore to the line's head after B publishes.

  Git itself confirms each fact the tests rely on: S holds a1 and not a2, B holds a2, and fix/A
  holds neither at the end. The unrelated bundles (W, V) are in the same runs and must reach
  COMPLETE.

## Commit-readiness

The target configures no formatter, linter or commit hook:

- no `.pre-commit-config.yaml`;
- no ruff/black/flake8 config;
- no `core.hooksPath`, and only `*.sample` hooks;
- no linter in `.github/workflows`.

CONTRIBUTING.md asks for the DCO sign-off (publish adds it) and a green offline suite.
`git diff --check` is clean with the new file included. No added line is over 100 columns.
Every touched file compiles. ruff and pyflakes are not installed. `patch.diff` applies cleanly
to `75a886e` (`git apply --cached --check` against an index equal to HEAD).

## Suite runs (final tree)

- C4 (`engine/scripts/run-verify.sh`): PASS, as above.
- The eight suites the brief names, plus `test_integrate_carried_rewrite_late` and the new
  file: 180 tests OK.
- T2 (`engine/scripts/run-docs-check.sh`): docs lint clean, 22 pages rendered, link audit OK.
  The patch touches no docs.
- T3 (`engine/scripts/run-suite.sh`): root suite 24 tests OK; driver suite 2613 tests OK (2
  skipped). That is 4 more than iteration 3's 2609: the four new cases.

## Housekeeping

My working files are in `.pdca-scratch/` at the worktree root: the C4 and T3 logs, copies of
`flow.py` used to restore it after each swap or mutation, and two diffs. They are not in
`patch.diff`, which lists its six paths explicitly, and copier renders only `template/`. I
did not delete them (no `rm`). To include the new test file in `git diff` I marked it
intent-to-add and cleared the mark each time. The index is as I found it (equal to HEAD), and
the test file is untracked, as before.

One slip, fixed: for M5 my first attempt restored `flow.py` from a copy saved before the
round's last cleanup edits. Its guard `cmp` failed, so no mutation ran, but the restore after
it still copied the old file in. I put the final file back from `patch.diff`, checked that the
worktree matches `patch.diff` byte for byte again, made a fresh copy, then ran M5. C4, T2 and
T3 had all run before the slip, on that same byte-identical tree, and the 180 focused tests
pass again on the restored tree.
