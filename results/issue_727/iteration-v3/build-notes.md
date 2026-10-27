# Build notes — issue 727 (flow-in-batch-dependency-scoped-bases), iteration 3

Base: `fcae4aa` (the run's line `pdca-integration/main-r547f8028520f`). "Base" line numbers
are on `fcae4aa`; "patched" line numbers are in the worktree with `patch.diff` applied.
Patch: 127,401 bytes (124.4 KiB; the size flag fires at 125 KiB, this instance's
`[driver.size_signal] patch_kb = 125`), 10 files: 2 production, 1 new test file, 7 test
suites touched.

This round starts from iteration-v2's patch and fixes the two implementation findings in
the carry-forward. Everything else is v2's, unchanged: the six restated existing suites are
byte-identical to v2's hunks (checked file by file), so v2's before/after list for them,
repeated under "Criterion (8)" below, still holds.

## The two carry-forward findings, and what answers each

### 1. C5 — the closure dropped what a finished patchless prerequisite was built on

**Cause.** v2's walk (iteration-v2 `flow.py:953` and `:963-964`) followed only
`Depends on` / `Depends on (merged)` edges out of a bundle that brought no branch to `d`'s
target, and never walked a `Conflicts with` partner that brought none. So with N
(`Conflicts with: A`, closed with no patch, built on a base holding A) and H
(`Depends on: N`), H got the real base and lost A.

**Fix.** `_closure_members` (patched `template/src/pdca_harness/flow.py:913-966`) now walks
every declared edge of every bundle it reaches, as long as this run built that bundle,
patch or no patch. v2's `every` flag and `walked` map are gone; `found` alone stops a
second walk (`flow.py:954`), which is safe because a bundle's edges no longer depend on
how it was reached. The guard that skips a partner built in the same or a later wave than
the bundle it is reached from stays (`flow.py:956-957`). Members are still only the
reached bundles the fold carries on `d`'s target (`flow.py:960`). The docstring
(`flow.py:917-932`) states the rule.

**Why a patchless *partner* is walked too, not only a patchless prerequisite** (the
reviewer named the prerequisite case). Criterion (6b) states the rule as "the closure walks
only through bundles this run built": its own example (E `Conflicts with: A`,
A `Depends on: Q`) expects Q on E's base whenever A was built. A partner with a patch
already brings its closure through its branch (v2 walks every edge of a member); a partner
that closed with no patch was built on the same closure. Treating the two differently would
make P's base depend on whether N happened to need a patch.

**Test.** `test_what_one_with_no_patch_was_built_on_is_on_the_base`
(`template/tests/test_flow_dependency_scoped_bases.py:274`). M (`Depends on: A`) and N
(`Conflicts with: A`) close with no patch. H (`Depends on: M`), J (`Depends on: N`, the
reviewer's case) and P (`Conflicts with: N`) must each be built on a base of their own that
holds all of A and nothing of Z; M's and N's own bases hold A too (the premise "N was built
on A" is asserted). This replaces v2's
`test_a_prerequisite_reached_through_one_with_no_patch_is_on_the_base`: H through M is
exactly that case, with the same assertions (H's branch holds all of A, none of Z, own base
holding A). Merging the two saved patch bytes without losing a case.

### 2. A base-build stop turned off the end-of-run check (#695)

**Cause.** v2 set `line_stopped = True` on any `_bundle_bases` error (iteration-v2
`flow.py:2708`), and `line_stopped` skips `_report_late_rewrites`. That is right after a
fold stop, because a fold checks every carried branch before any merge can fail
(`_carried_tips`, called at patched `integrate.py:529`, base `:514`). It is wrong after a
base-build stop: `build_bundle_base` checks only its own members' branches (patched
`integrate.py:839-845`). So with the adversary's input (wave 0 A, Z; wave 1 S
`Stacks on: Z`, B `Depends on: A`; wave 2 C `Depends on: B`; after the fold after wave 1,
fix/Z goes back a commit and main gains a file that clashes with A's), the run stopped at
C's base on the clash and never mentioned Z's rewrite, though S's open PR holds the lost
commit.

**Fix.** A base-build stop no longer sets `line_stopped`. The end-of-run check runs over
every accepted bundle except the one whose rewrite the stop already reported in full:

- `build_bundle_base` raises its rewrite refusal as `integrate._Rewritten` (new class,
  patched `integrate.py:126-133`; raised at `:844-845`), which carries the member's name.
  The text is v2's, unchanged (`_rewrite_stop`, `integrate.py:1129`).
- `_bundle_bases` no longer wraps the error in a new `IntegrationError` (that lost the
  class); it puts its "could not build X's own base from …" prefix on the same error and
  re-raises it (`flow.py:1002-1005`). The printed STOPPING line is word for word v2's.
- `_drive_and_act` records that name (`stop_named`, `flow.py:2631-2633`, filled at
  `:2706-2707`) and leaves it out of the end check (`flow.py:2852`). `line_stopped` is now
  set only by a fold error or a red re-gate (`flow.py:2814`, `:2830`), as on `fcae4aa`
  (base `:2651`, `:2667`).

This also settles the deferred item about `flow.py:2708` ("if a base build fails … turns
off the #695 end-of-run check"), which the code review asked the human to accept or track
under #725: it no longer happens.

**Test.** `test_a_base_that_stops_the_run_for_a_clash_leaves_the_end_check_on`
(`test_flow_dependency_scoped_bases.py:506`), the adversary's input: one STOPPING line
naming C's base and A, B (and not Z); then one line reporting Z's branch rewritten after the
line took it, naming `(issue_S)`; holds `{"Z": "rewritten"}`.

Two tests v2 added had pinned the old "nothing after the stop" behaviour; both are v2's own
tests (absent on `fcae4aa`), restated here:

- `_stopped_at_b` (`test_integrate_carried_rewrite_late.py:207`) no longer asserts "nothing
  left for the end of the run to check by hand" itself; each caller says what follows.
- (1d) `test_a_rewrite_during_the_lines_fold_stops_the_run_at_the_dependents_base` (`:295`):
  input unchanged; still exactly one line reports A's rewrite (the stop's; the end check
  skips A), and it now asserts no unchecked line.
- `test_a_fetch_failing_after_the_lines_fold_stops_the_run_at_the_dependents_base` (`:348`):
  input unchanged. Before (v2): stop at B's base naming the fetch, no unchecked line, 1 failed
  fetch. After: the same stop line, then the end check, which cannot fetch either, names
  A's branch and head to check by hand with the fetch as the cause (`_assert_unchecked`),
  and 3 failed fetches (B's base once, the end check's two tries). rc 1 both times. This is
  the point of the fix: nothing re-checked fix/A after the line took it.

## Alternatives ruled out (with cost)

- **Finding 2: "have the base build check every head in `taken` before it builds
  anything"** (the adversary's second option). Cost: a fetch and ancestry check of every
  carried branch at every wave that builds a base, beside the fold's own full check
  (about 15 lines in `_bundle_bases` or `build_bundle_base`). It also changes when a run
  stops: a rewrite of a branch no base of the wave uses would stop the run before the wave
  builds, where `fcae4aa` builds it and reports at the next fold or at the end — and only
  in waves that happen to build a base. Rejected.
- **Finding 2: run the end check after a base-build stop and skip nothing.** About 12 lines
  smaller (no `_Rewritten`, no `stop_named`), but a rewrite the stop named is then printed
  twice, by the stop line and by the end report. Mutation M4 below shows (1d) and
  `test_a_later_base_that_reads_the_rewrite_stops_naming_each_base_and_pr` catch exactly
  that.
- **Finding 2: keep v2's wrapping and read `exc.__cause__` in `_drive_and_act`.** Same size;
  rejected because the use site would test the chained cause instead of the error it caught.
- **Finding 1: walk through a patchless prerequisite only, keep v2's "a partner with no
  branch is not walked".** About 6 more lines than this walk (keep v2's `every`/`walked`,
  add a target lookup for patchless bundles). Rejected for the reason under finding 1.

## Behaviour change to weigh at sign-off (new this round)

- **The walk no longer looks at a reached bundle's target either.** v2 walked a bundle on
  another target with prerequisite edges only (it lumped "no patch" and "other target"
  together as "brought no branch to d's target"). Now every bundle this run built is walked
  the same way. The only effect is on an in-batch cross-target chain such as d (target T1)
  `Depends on` X (T2), X `Conflicts with` Y (T1, earlier wave): Y is now on d's base. On
  `fcae4aa` d sits on T1's line, which holds Y and everything else, so d never gets less
  than before. Members are still only bundles with a branch on d's own target. No test
  covers cross-target closures (v2 had none either). If you want v2's cross-target rule
  back, it is the "patchless prerequisite only" variant above.
- **After a base-build stop the end-of-run check runs.** The exit code is unchanged (1:
  the stopped wave's bundles are not COMPLETE). `holds` can now also name other branches
  `"rewritten"` / `"unchecked"`. After a base build that stopped because a fetch failed, the
  end check usually cannot fetch either and names the line's branches to check by hand (the
  restated fetch test).

## Refuting my own test (forced)

- **(a) Genuine red? Yes.** The project's C4 runner (`engine/scripts/run-verify.sh`, with
  `PDCA_BUNDLE` and `PDCA_WORKTREE` set) printed
  `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`. Green: 215 tests across
  the 8 touched test modules, all OK. Red (production hunks reverted to `fcae4aa`, tests
  kept): 16 of the 20 new tests fail on assertions, no module failed to load; the 4 that
  pass are the seam tests of criterion (6), which assert behaviour unchanged from
  `fcae4aa`, by design. Against iteration-v2's production code (v2's production hunks
  applied, this round's tests), exactly three tests fail: the two new ones and the restated
  fetch test. Mutations, each run and then restored:
  - M1: do not walk a partner with no patch → `test_what_one_with_no_patch_…` FAILS (P).
  - M2: walk a bundle with no patch without its `Conflicts with` edges → the same test
    FAILS (J and P).
  - M3: delete the partner-built-after guard (`flow.py:956-957`) →
    `test_a_members_partner_built_after_it_is_not_on_the_base` FAILS.
  - M4: never fill `stop_named` → (1d) and
    `test_a_later_base_that_reads_the_rewrite_stops_naming_each_base_and_pr` FAIL (the
    rewrite is reported twice).
  - M5: v2's `line_stopped = True` on a base-build stop → the new clash test and the
    restated fetch test FAIL.
- **(b) Production path? Yes.** Every case drives the real `flow._drive_and_act`, with the
  real `integrate.fold`, `integrate.build_bundle_base`, `_carry_finished` and
  `integrate.rewritten_carried`, on real git (a bare `origin`, a primary checkout, a
  scratch clone, from `StackFoldGit`). Stubbed only what the brief allows: the
  build/sign-off leaf (`_drive_wave`), `_publish_bundle` (cuts the PR branch from the
  recorded stack-base tip, as `test_flow_same_wave_conflict.py:131` does),
  `publish.draft_texts`, and `gh`.
- **(c) Fixture includes the fault? Yes.** Finding 1: M and N really close with no patch
  (close marker, no `patch.diff`, no publish) and are really built on their own bases
  holding A (asserted); Z is a real bundle the line folds. Finding 2: fix/Z is really
  forced back on origin (`git branch -f`) after the line and S's PR took its head; main
  really gains `a.txt`, C's base build really fails merging fix/A onto the freshly fetched
  main (the STOPPING line is asserted), and the real end-of-run check then finds Z's
  rewrite.

## Criterion (8): every restated existing assertion, before → after

Unchanged from v2 except where marked "this round". Every restatement says what a base
*contains*; no content check was dropped.

**`test_flow_merged_prereq_on_line.py`**: only `_built_on_line` (base :191-198). Before:
`base == self.line`, tip set, D COMPLETE. After: if this run built W (callers at base
:227, :235), `base == f"{self.line}-bD"` (D's `bundle_base_branch`), origin's tip of it is
the recorded tip, it holds `fix/W`, and `rev-list --no-merges tip --not main fix/W` is
empty. Otherwise (carried prerequisite: :285, :310) `base == self.line` as before. Callers,
hold tests and `:269` are untouched.

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
- :275-278 on50 on line with 40, 42, not 41 → on50 own base {42}; line at 50's build holds
  40, 42; 41 not on on50, and (added) not on the final line.
- :309 on21 on line → on21 own base {12}; 11 not on it (unchanged).
- :425-427 on30 on line with 20, not 22 → on30 own base {20, 10}; line at 30's build holds
  20; 22 not on on30, and (added) not on the final line.

**`test_flow_resume_stack_prereqs.py`**: new helper `_on_own_base` (patched :181).
- :281-284 W on the line, rejected not on that tip → W own base holding U; rejected not on
  it; `rejected` not on the line (:280) unchanged.
- :317 E's base == line → E own base holding D.
- :347-350 W on the line, P not on that tip → W own base holding U; P not on it; and P not
  on origin's line tip when W was built (the old check's commit, kept).
- :447-453 E and U on the line with X, not P/Q → E unchanged (carried X, a seam); U, which
  declares no edge, on the plain base; the line lacks P and Q (:455-456) unchanged.
- :475-479 W on the line, P/Q not on that tip → W own base holding U; P/Q on neither its
  base tip nor origin's line tip when W was built.

**`test_flow_reissue_after_conflict_hold.py`** (v1's C5 finding):
- `_held_for_10` (base :150) gains `on="12"` (default: every caller's input unchanged);
  docstring says 21 is built on a base holding what `on` names.
- `_carried_but_11` (base :196) gains `*also` (default: identical checks).
- `test_one_the_fold_merges_after_it_is_named_too` (base :240-252), **input unchanged**.
  Before: 11's line names 10 and 21 (`Conflicts with: 10, 21`); 10, 12, 21 carried. After:
  21 does not hold 10's change (asserted); 11's line names 10 alone with run 1's step
  (`_named_with_10`, which also asserts no `issue_21`); 21's own line names its conflict
  with 10 (shared.txt) and the step `declare Conflicts with: 10 in issue_21's brief, then
  rebuild issue_21 on a base that holds issue_10`; carried: 10, 12; 11 and 21 off the line.
- New `test_one_built_on_the_partner_the_fold_merges_after_it_is_named_too`: `on="12, 10"`,
  the old assertions, plus 21 holds 10's change.
- `test_one_built_on_the_partner_is_not_named_for_the_partners_change` (base :282-288):
  input and assertions unchanged; comment corrected; premise asserted (21 lacks 10).
- New `test_one_built_on_the_partner_by_its_own_base_is_not_named_for_its_change`:
  `on="12, 10"`; 21 holds 10's change (asserted); only 10 is named.
- `_stacked_on_10` (base :310-311): `seen["issue_12"][0] == self.line` →
  `== bundle_base_branch(…, "issue_12")`; `line_under_12` is the recorded tip, which (added)
  equals origin's tip of that base and holds 10's head. Later uses unchanged.
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
  first forced → the line's pushes only: 2, first forced.
- `test_a_dependent_carries_every_earlier_wave_branch_not_only_its_prerequisite` (base
  :1629-1661) renamed `…_carries_only_its_prerequisite_not_every_earlier_wave_branch`,
  input unchanged. It pinned the #630 defect itself, so it is inverted: ZB from its own
  base {ZA}; ZZ not on ZB; diff ZA, ZB; after ZA merges, ZB; after ZZ merges, one merge base
  (ZA) and diff ZB with no "Update branch".
- `test_a_held_bundle_published_later_is_cut_from_the_line_it_was_built_on` (base :1719):
  comment only. LU now gets its own base, which later waves never grow, so this test no
  longer tells "publish cuts from the recorded tip" from "publish cuts from the branch";
  that mechanism is unchanged code, unit-tested in `test_integrate_stack_bases.py` cases
  14, 14b and 15 (base :1003-1053), and the seam tests here assert a line-kept bundle's
  recorded tip equals origin's line tip then.

**`test_integrate_carried_rewrite_late.py`**:
- (1c) `test_a_rewrite_during_the_last_fold_is_reported_and_exits_1` (base :258-275):
  **input change** (v2). The rewrite fires just before B's base's push (since #727 the run's
  last read of fix/A), not the line's. Assertions unchanged.
- (1e) `test_an_end_of_run_check_that_cannot_fetch_is_named_and_exits_1` (base :279-306):
  **input change** (v2). Fetches fail after B's base's push; `len(pushed) == 1` → pushes ==
  [line, B's base]; the rest unchanged.
- The old trigger points stay covered by two tests v2 added — (1d) and the fetch variant —
  restated this round as described under finding 2.

**`test_flow_dependency_scoped_bases.py`** (new file; changes against v2's version, this
round): the new finding-1 test replaces v2's patchless-prerequisite test (same case kept,
see finding 1); the new finding-2 test; the (6b) test's comment now says E lacks Q because
this run never built A (it used to say "A brought no branch", which is no longer the
reason); the module docstring is shorter.

## Carried over from v2, still true

- A base that cannot be built stops the run with one STOPPING line, as a failed fold does;
  one refused for a rewrite names every PR holding a lost head. Holds instead of stops are
  #725's.
- Undeclared cross-wave overlaps now surface at the next fold, or at a re-issue's carry.
  That is the #725 hold.
- Per-bundle bases start from a freshly fetched `origin/main` (#723's
  `build_bundle_base`). Deferred, not changed here.
- PR shape (brief): until #726 merges, this PR's diff against `main` also shows #723; merge
  #726 first.

## Runs (all through the project's runners, bounded by `timeout`)

- C4 `engine/scripts/run-verify.sh`: `PDCA-EVIDENCE: C4 PASS — red without the fix, green
  with it`.
- T3 `engine/scripts/run-suite.sh`: `PDCA-EVIDENCE: root suite OK, driver suite OK` (root
  24 tests; driver 2,576 tests, 2 skipped, as on the base).
- During the work I also ran single modules with the runner's own per-module command
  (`cd template && PYTHONPATH=src python3 -m unittest tests.<module>`), always under
  `timeout`.
- After every run the worktree diff matched `patch.diff` byte for byte (`cmp`).

## Housekeeping

- No formatter, linter or commit hook is configured in the target (no pre-commit config,
  no ruff/flake8/black settings, only sample git hooks). `git diff --check` is clean, the
  longest added line is 98 characters (the base files run to 100 and 106), and the changed
  modules compile. The commit rule is the DCO sign-off, which publish adds.
- For the mutation runs I parked the work in a temporary local commit in the worktree
  (twice) and undid it each time with `git reset --mixed fcae4aa`. HEAD is `fcae4aa`, the
  changes are uncommitted, and the new test file is marked intent-to-add (`git add -N`) so
  `git diff` shows it. No untracked files are left in the worktree, and I wrote nothing
  outside the worktree and this bundle.
- External dependencies: none beyond Python 3.11+ and git (copier for the root suite is
  installed).
