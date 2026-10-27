# Build notes — issue 727 (flow-in-batch-dependency-scoped-bases), iteration 2

Base: `fcae4aa` (the run's line `pdca-integration/main-r547f8028520f`). "Base" line numbers
are on `fcae4aa`; "patched" line numbers are in the worktree with `patch.diff` applied.
Patch: 124,782 bytes (121.9 KiB; the size flag fires at 125 KiB, `size_signal.py:490`),
10 files: 2 production, 1 new test file, 7 restated suites.

This iteration starts from iteration-v1's patch (`iteration-v1/patch.diff`) and fixes the
five implementation findings in the carry-forward. The closure walk and the per-bundle base
selection are unchanged from v1 apart from one efficiency cleanup.

## The five carry-forward findings, and what answers each

1. **C5: the original undeclared-overlap case lost its coverage**
   (`test_flow_reissue_after_conflict_hold.py`). v1 changed the existing test's input
   (`21` gained `Depends on: 10`). Now the existing test
   `test_one_the_fold_merges_after_it_is_named_too` (patched :245) keeps its original input
   (`21` declares only `12`), and its assertions say what now happens: 21 is built without
   10, so the carry's fold skips it too, naming 10 and the step for 21; 11 is named with 10
   alone; only 10 and 12 are carried. The declared-edge scenario is a separate new test,
   `test_one_built_on_the_partner_the_fold_merges_after_it_is_named_too` (patched :265),
   which carries the original assertions. While checking for the same problem elsewhere I
   found a second test whose premise had silently changed:
   `test_one_built_on_the_partner_is_not_named_for_the_partners_change` (base :282) still
   passed, but its comment ("21 is cut from the line that holds 10 and 12") was no longer
   true, so it no longer tested what its name says. Its input is kept, the premise is now
   asserted (21 does not hold 10), and a new declared-edge test keeps the original coverage
   (`..._by_its_own_base_is_not_named_for_its_change`, patched :319).
2. **The line's report named too few PRs** (`had.get(name) == took`, v1 `flow.py:1042`). A
   PR cut from the line is now recorded with the head of each branch the line held when it
   was cut (`_heads_taken`, patched `flow.py:1027`), and every check judges each of those
   heads on its own (`integrate._lost`, patched `integrate.py:1066`). A PR is named when its
   own head is lost, so a PR cut at an older head is named when that head is lost
   (`test_a_pr_cut_from_the_line_at_an_older_head_is_named_when_it_is_lost`, :535) and
   not named when the branch still holds it
   (`test_a_pr_cut_from_the_line_at_a_head_still_on_the_branch_is_not_named`, :547). Both
   cover "a branch the line takes twice". The "no PR this run cut from L holds them" text
   (patched `integrate.py:1273`) is now accurate: it is printed only when no line-cut PR
   holds a lost head.
3. **A later bundle's base build caught a rewrite with the line-only remedy.**
   `build_bundle_base` now takes the same `bases` / `line_prs` the fold takes (patched
   `integrate.py:723-729`, passed at patched `flow.py:1004-1006`) and judges every head the
   run's PRs hold for each member branch. Its refusal is built by the same function as the
   fold's stop (`_rewrite_stop`, patched `integrate.py:1117`): it names each line-cut PR
   and each base holding a lost head and tells the human to rebuild them. Test:
   `test_a_later_base_that_reads_the_rewrite_stops_naming_each_base_and_pr` (:492). The
   end-of-run check is still skipped after that stop (`line_stopped`, patched
   `flow.py:2708`), the same as after a fold's stop: the stop line now carries the whole
   report, and running the end check too would report the rewrite twice, which #695's
   `test_a_rewrite_the_next_fold_stops_on_is_reported_once` rules out for folds. The new
   test asserts the end-of-run report is absent.
4. **The closure guard had no test** (patched `flow.py:960`: a member's `Conflicts with`
   partner built after it is not followed). New test
   `test_a_members_partner_built_after_it_is_not_on_the_base` (:307): A; E (`Conflicts
   with: A`); Y (`Depends on: A`); D (`Depends on: Y`). D's base holds A and Y and none of
   E's own commits. With the guard deleted the test fails (mutation run below).
5. **The same `_line_prs` filter, from the code review.** It suggested naming every
   line-cut PR whose snapshot has the branch at all (`name in had`). I did not take that
   form: it over-names. If the branch is reset to the older head a1, a PR cut at a1 still
   holds everything it holds, but `name in had` would name it as holding lost commits. The
   per-head judgment names exactly the PRs that lost something. The mutation run shows
   `name in had` fails test :547.

Also from the code review (untagged): `_closure_members` no longer re-reads every built
bundle's `publish.json` once per runnable bundle. `_bundle_bases` computes the fold
candidates once per wave and passes them in (patched `flow.py:992`). The clumsy "(none)"
/ "(issue_S after issue_A's)" unchecked wording is replaced: with line-cut PRs it names
them in one list; without, it says no PR cut from the line holds such a commit (patched
`flow.py:2906-2916`).

## What changed (production)

### `template/src/pdca_harness/flow.py`

- `_closure_members` (patched :913). Unchanged from v1 except that it takes `cands`. It
  walks `Depends on` and `Depends on (merged)` (transitively) and `Conflicts with`
  partners built in an earlier wave, only through bundles this run built. It returns the
  members, `[]` (the real base), or a seam reason: a walked bundle declaring `Stacks on` /
  `Onto branch` (:949), an edge to a finished named id (:957), a member published as an
  `Onto branch` commit (:967), or a member built on the line (:969).
- `_bundle_bases` (patched :974). Builds every base of the wave with
  `integrate.build_bundle_base` (base `integrate.py:716`) before pointing anything. The
  base gets `carried`, `excluded`, `merged_heads`, and now `bases` / `line_prs`. Then each
  bundle is pointed: own base (`publish.write_stack_base`), real base (`clear_stack_base`),
  or, at a seam, `_point_at_integration` exactly as on `fcae4aa` (base `flow.py:890`). It
  records what each PR holds (`bases_took`, `line_cut`).
- `_heads_taken` (patched :1027). Replaces v1's `_line_prs`. It returns published bases
  and, per branch, `[(PR owner, the head the line held when it was cut)]` in cut order,
  filtered to pushed PRs on the branch's own target.
- Call sites in `_drive_and_act`: base `flow.py:2549` (`_point_at_integration`) becomes
  patched :2695-2711, where own bases are used only when the line folds for real
  (`own_bases = hold_unmerged`, patched :2630) and a base error stops the run. The fold
  gets `bases` / `line_prs` (patched :2802-2809). The end-of-run check gets the same
  (patched :2852-2855).
- `_report_late_rewrites` (base :2701, patched :2867). Prints one line per report. The
  line's unchecked line keeps today's text, then either names the line-cut PRs or says
  none holds such a commit. Bases whose head could not be judged get a line of their own
  per cause.

### `template/src/pdca_harness/integrate.py`

- `_carried_rewrite` (base :1067) is **unchanged**. Every head is now judged with it
  (`_lost`, patched :1066), each distinct head once; its words are used for the line's
  head. v1 had split it into `_holds_took` + `_line_rewrite`. Keeping it removes that churn
  and keeps one judgment function, as before.
- `Taker`, `Bases`, `LinePrs` type aliases and `_takers` (patched :1041-1063). For each
  branch they list the line's head, each line-cut PR's head (cut order), then each base's
  head.
- `_carried_tips` (base :1025, patched :1078). Judges every head for each branch and
  raises `_rewrite_stop` on any lost one.
- `_rewrite_stop` (patched :1117). The single stop message for the fold (`onto=None`) and
  the base build (`onto=branch`). When only the line's head is lost and no PR is named, the
  fold's text is byte-for-byte the text on `fcae4aa` (base :1057-1063), and the base
  build's is byte-for-byte #723's (base :815-821).
- `build_bundle_base` (base :716, patched :723). Gains `merged_heads` (v1) and
  `bases` / `line_prs`. The rewrite check (base :811-821, patched :827-833) uses `_lost`
  + `_rewrite_stop`.
- `rewritten_carried` (base :1083, patched :1188). Returns lists of reports and of
  `(ref, why, head, taker)` items. The line's report (`_late_line_rewrite`, patched :1265)
  keeps today's wording (base :1129-1134), adding `(issue_S, …)` after "after it took H"
  for the PRs holding a lost head. With none, it says so instead of the vacuous "every PR
  this run cut from …". A base's report (`_base_rewrite`, patched :1177) never says "the
  commit the line took" or "every PR this run cut from" (criterion 7).

Untouched: `_line_lacks_merge`, `merged.merge_and_head`, `merged.py` (#729); all docs
(#725).

## Alternatives ruled out (with cost)

- **Finding 3, option "keep the line-only refusal and do not set `line_stopped` on a
  base-build error"** (so the end-of-run check names everything). One line in `flow.py`.
  Rejected: the stop line would still give only the line's remedy, and the rewrite would
  be reported twice (stop line plus end-of-run lines). The fold path forbids that, and the
  new test asserts against it.
- **Finding 3, option "a pre-check in `flow._bundle_bases` before calling
  `build_bundle_base`".** Rejected: `build_bundle_base` fetches and reads each tip itself
  under its lock (base `integrate.py:809-810`), so a rewrite between the pre-check and that
  read would still produce the line-only message. The check has to sit at the read.
- **Finding 2, option `name in had`** (code review): rejected above; over-names PRs.
- **Finding 1, option "keep v1's input change and add the original input as a new
  test"**: same coverage, but the reviewer asked for the original input in the original
  test. I followed that. For `test_integrate_carried_rewrite_late.py` (1c)/(1e) I kept
  v1's structure: the trigger moved with "the run's last read" (now B's base build), and
  the old trigger points stay covered by two new tests (1d and the fetch variant). No
  input there is lost. The adversary judged those changes justified and left them for you
  to confirm; they are listed below.
- **A seam-variant copy of `test_a_held_bundle_published_later_is_cut_from_the_line_it_
  was_built_on`** (test_flow_slice.py, base :1719). In that test LU now gets its own base,
  which later waves never grow, so it no longer tells "publish cuts from the recorded tip"
  apart from "publish cuts from the branch". That mechanism is unchanged code and is
  unit-tested in `test_integrate_stack_bases.py` cases 14, 14b and 15 (base :1003-1053).
  The seam tests here assert a line-kept bundle's recorded tip equals origin's line tip
  then. A flow-level copy would add about 2 KB to a patch already close to the size flag,
  so I only corrected the comment and pointed it at those cases.

## Refuting my own test (forced)

- **(a) Genuine red? Yes.** The project's C4 runner (`engine/scripts/run-verify.sh` with
  `PDCA_BUNDLE`/`PDCA_WORKTREE`) printed `PDCA-EVIDENCE: C4 PASS — red without the fix,
  green with it`. Red leg (production hunks reverted, tests kept): 15 of the 19 new tests
  FAIL on assertions; no module failed to load. The 4 that pass on `fcae4aa` are the seam
  tests (criterion 6: "unchanged"), as designed. To show those 4 bind the seam rule, I
  removed each seam return in turn: removing "declares `Stacks on`/`Onto branch`" fails
  the Stacks-on test; removing "edge to a finished id" fails both carried tests. Removing
  the published-as-`Onto branch` member check alone fails nothing, because the brief check
  catches the same bundle first (the v1 adversary noted the double guard). Mutation runs
  for this iteration's fixes, each restored after:
  - delete the partner-after-member guard (patched `flow.py:960`) → test :307 FAILS;
  - name PRs by the latest head only (v1's rule) → test :535 FAILS with exactly the
    adversary's symptom ("no PR this run cut from … holds them" while S holds a lost head);
  - name every line-cut PR (`name in had`) → test :547 FAILS;
  - stop passing `bases`/`line_prs` to `build_bundle_base` → test :492 FAILS.
  Against v1's production code the new finding-2 and finding-3 tests (:492, :535, :547)
  and the reworded unchecked test (:584) fail. :307 passes there, because v1 had the guard.
- **(b) Production path? Yes.** Every new case drives the real `flow._drive_and_act` with
  the real `integrate.fold`, `integrate.build_bundle_base`, `_carry_finished` and
  `integrate.rewritten_carried`, on real git (bare `origin`, primary checkout, scratch
  clone from `StackFoldGit`). Stubbed only what the brief allows: the build/sign-off leaf
  (`_drive_wave`), `_publish_bundle` (cuts from the recorded stack-base tip, as
  `test_flow_same_wave_conflict.py:131` does), `publish.draft_texts`, and `gh`.
- **(c) Fixture includes the fault? Yes.** `Z` and `E` are real bundles the line really
  folds (asserted on the line) and that the old code really put on the dependent. Every
  rewrite is a real `git branch -f` or force-push on origin after the line and the bases
  took the head. In the finding-3 test the rewrite lands after the fold that follows wave
  1, so D's base build really reads the rewritten branch. The fetch fault is a real failing
  `integrate._git("fetch")`, armed by B's base's real push. Carried bundles are carried by
  the real `_carry_finished` (asserted `flow: carried …`).

## Criterion (8): every restated existing assertion, before → after

Every restatement says what a base *contains*. No content check was dropped; where one
moved from "on the dependent's base" (true only because that base was the line) it is now
asserted on the line itself, at the commit the old assertion looked at.

**`test_flow_merged_prereq_on_line.py`**: only `_built_on_line` (base :191-198). Before:
`base == self.line`, tip set, D COMPLETE. After: if this run built W (callers at base
:227, :235), `base == f"{self.line}-bD"` (D's `bundle_base_branch`), origin's tip of it is
the recorded tip, it holds `fix/W`, and `rev-list --no-merges tip --not main fix/W` is
empty. Otherwise (carried prerequisite: :285, :310) `base == self.line` as before.
Callers, hold tests and `:269` are untouched.

**`test_flow_same_wave_conflict.py`**: `_run` stores `self.ids`. `_built_on_line(iid)`
(base :169-178: base == line, tip == line tip) becomes `_built_on(iid, *closure)`: base ==
`bundle_base_branch`, tip == origin's tip of it, holds each closure head, nothing else
beyond main but merges. New `_on_line(at, *ids)`: origin's line tip recorded when `at` was
built (the `seen` entry the old helper compared against) holds each id.
- :208-210 on21 on line with 10, 12 → on21 own base {12}; line at 21's build holds 10, 12;
  11 not on on21 (unchanged).
- :215-217 on30 on line with 10, 12, 21 → on30 own base {21, 12}; line at 30's build holds
  10, 12, 21; 11 checks unchanged.
- :253-257 20, 21 on line with 10, 11, 12; 30 on line → 20 own base {11}, 21 own base {12};
  the line at 20's and 21's build holds 10, 11, 12; 30 own base {21, 12}.
- :275-278 on50 on line with 40, 42, not 41 → on50 own base {42}; line at 50's build
  holds 40, 42; 41 not on on50, and (added) not on the final line.
- :309 on21 on line → on21 own base {12}; 11 not on it (unchanged).
- :425-427 on30 on line with 20, not 22 → on30 own base {20, 10}; line at 30's build
  holds 20; 22 not on on30, and (added) not on the final line.

**`test_flow_resume_stack_prereqs.py`**: new helper `_on_own_base` (patched :181).
- :281-284 W on the line, rejected not on that tip → W own base holding U; rejected not on
  it; `rejected` not on the line (:280) unchanged.
- :317 E's base == line → E own base holding D.
- :347-350 W on the line, P not on that tip → W own base holding U; P not on it; and P
  not on origin's line tip when W was built (the old check's commit, kept).
- :447-453 E and U on the line with X, not P/Q → E unchanged (carried X, a seam); U, which
  declares no edge, on the plain base; the line lacks P and Q (:455-456) unchanged.
- :475-479 W on the line, P/Q not on that tip → W own base holding U; P/Q on neither its
  base tip nor origin's line tip when W was built.

**`test_flow_reissue_after_conflict_hold.py`** (finding 1):
- `_held_for_10` (base :150) gains `on="12"` (default: every caller's input unchanged);
  docstring says 21 is built on a base holding what `on` names.
- `_carried_but_11` (base :196) gains `*also` (default: identical checks).
- `test_one_the_fold_merges_after_it_is_named_too` (base :240-252), **input unchanged**.
  Before: 11's line names 10 and 21 (`Conflicts with: 10, 21`); 10, 12, 21 carried. After:
  21 does not hold 10's change (asserted); 11's line names 10 alone with run 1's step
  (`_named_with_10`, which also asserts no `issue_21`); 21's own line names its conflict
  with 10 (shared.txt) and the step `declare Conflicts with: 10 in issue_21's brief, then
  rebuild issue_21 on a base that holds issue_10`; carried: 10, 12; 11 and 21 off the
  line.
- New `test_one_built_on_the_partner_the_fold_merges_after_it_is_named_too`: `on="12,
  10"`, the old assertions, plus 21 holds 10's change.
- `test_one_built_on_the_partner_is_not_named_for_the_partners_change` (base :282-288):
  input and assertions unchanged; comment corrected; premise asserted (21 lacks 10).
- New `test_one_built_on_the_partner_by_its_own_base_is_not_named_for_its_change`:
  `on="12, 10"`; 21 holds 10's change (asserted); only 10 is named.
- `_stacked_on_10` (base :310-311): `seen["issue_12"][0] == self.line` →
  `== bundle_base_branch(…, "issue_12")`; `line_under_12` is the recorded tip, which
  (added) equals origin's tip of that base and holds 10's head. Later uses unchanged.
- Comments only (base :295, :334, :368, :386, :402): "built on the line holding 10" →
  "built on a base holding 10"; "not from the line" → "not from its base".

**`test_flow_conflict_partner_hold.py`**: fixture only. With `stub_fold=True` (no git
checkout in the temp dir) `build_bundle_base` is stubbed too (base :149-151). Assertions
unchanged.

**`test_flow_slice.py`**:
- `_live(fold=…)` (base :1333) stubs `build_bundle_base` beside a fake fold. The 3
  spy-fold tests' assertions are unchanged.
- `_update_from_main` (base :1572) removed (no caller left); `_own_base` added (patched
  :1576).
- `test_a_three_wave_run_folds_append_only_onto_a_real_origin` (base :1580-1627): EB cut
  from the line → EB from its own base holding EA alone, EC from its own base holding EB
  and EA. "EB~1 (the first fold's tip) is on the line" → the first fold's tip (recorded by
  the fold spy) is on the line. EA merged once on `git log --merges line` → once on the
  line's `--first-parent` chain (EB's branch brings its own base's merge of EA). 2 pushes,
  first forced → the line's pushes only: 2, first forced. A rebuilt line is still caught,
  by the first fold's tip being on the line and by the push checks.
- `test_a_dependent_carries_every_earlier_wave_branch_not_only_its_prerequisite` (base
  :1629-1661) renamed `…_carries_only_its_prerequisite_not_every_earlier_wave_branch`,
  input unchanged. It pinned the #630 defect itself, so it is inverted: ZB from its own
  base {ZA}; ZZ not on ZB; diff ZA, ZB; after ZA merges, ZB; after ZZ merges, one merge
  base (ZA) and diff ZB with no "Update branch".
- `test_a_held_bundle_published_later_is_cut_from_the_line_it_was_built_on` (base :1719):
  comment only (see "Alternatives").

**`test_integrate_carried_rewrite_late.py`** (unchanged from v1; please confirm):
- (1c) `test_a_rewrite_during_the_last_fold_is_reported_and_exits_1` (base :258-275):
  **input change**. The rewrite fires just before B's base's push (since #727 the run's
  last read of fix/A), not the line's. Assertions unchanged.
- New (1d) `…_during_the_lines_fold_stops_the_run_at_the_dependents_base`: the old
  trigger. The run stops at B's base on one STOPPING line naming B's base, the rewrite and
  A's head; rc 1.
- (1e) `test_an_end_of_run_check_that_cannot_fetch_is_named_and_exits_1` (base :279-306):
  **input change**. Fetches fail after B's base's push; `len(pushed) == 1` → pushes ==
  [line, B's base]; the rest unchanged.
- New `test_a_fetch_failing_after_the_lines_fold_stops_the_run_at_the_dependents_base`:
  the old arming. Stop at B's base naming the fetch; rc 1.

## Behaviour changes you should know about

- **A base that cannot be built stops the run** with one STOPPING line, as a failed fold
  does. One refused for a rewrite names every PR holding a lost head. Holds instead of
  stops are #725's.
- **Undeclared cross-wave overlaps now surface.** A bundle no longer built on unrelated
  earlier-wave work can conflict with it at the next fold, or at a re-issue's carry (the
  restated reissue test shows the carry naming such a pair). That is the #725 hold.
- **Seams are conservative.** Any edge from a walked bundle to a finished named id keeps
  the line, and so does any walked bundle declaring `Stacks on` / `Onto branch`.
- **Per-bundle bases start from a freshly fetched `origin/main`** (#723's
  `build_bundle_base`, base `integrate.py:829`). Deferred finding, not changed here:
  mid-run main commits now reach the line through a dependent's branch. Whether to start
  bases from the line's start commit instead is your decision (it would change #723).
- **PR shape** (brief): until #726 merges, this PR's diff against `main` also shows #723.

## Runs (all through the project's runners, bounded)

- C4 `engine/scripts/run-verify.sh`: `PDCA-EVIDENCE: C4 PASS — red without the fix,
  green with it` (green: 214 tests across the 8 touched test modules, all OK).
- T3 `engine/scripts/run-suite.sh`: `root suite OK (24), driver suite OK (2575, 2
  skipped, as on the base)`.
- After each run the worktree diff still matches `patch.diff` byte for byte (`cmp`).

## Housekeeping

- No formatter, linter or commit hook is configured in the target (no pre-commit config,
  no ruff/flake8/black settings, only sample git hooks; CI runs docs checks only).
  `git diff --check` is clean and no added line is over 100 characters. The commit rule
  is the DCO sign-off, which publish adds.
- Files I left that are not part of the patch: `/tmp/x.diff` (a stray redirect, written
  outside the allowed roots by mistake, 23 KB of diff text); in the worktree, the
  untracked `.bases-probe.txt` (emptied), `template/.orig-tests-probe/` (empty dir) and
  `template/tests/zz_orig_test_*.py` (base copies of 7 suites, used once to see which fail
  unrestated; their names do not match unittest's `test*.py` pattern, so no runner
  collects them). I cannot remove them (no `rm`); the harness reclaims the worktree. The
  new test file is marked intent-to-add in the worktree index (`git add -N`) so
  `git diff` shows it; nothing is committed.
- External dependencies: none beyond Python 3.11+ and git.
