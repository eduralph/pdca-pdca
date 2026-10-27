# Build notes — issue 727 (flow-in-batch-dependency-scoped-bases), iteration 4

Base: `fcae4aa` (the run's line `pdca-integration/main-r547f8028520f`). "Base" line numbers
are on `fcae4aa`; "patched" line numbers are in the worktree with `patch.diff` applied.
Patch: 134,909 bytes (131.7 KiB), 10 files: 2 production, 1 new test file, 7 touched test
suites. That is over the 125 KiB size flag; see "Size" below.

This round starts from iteration-v3's patch and fixes the two findings in the round-3
carry-forward. This is also the last automatic round (`max_auto_iters = 3`,
`auto-iterate.json` count 3), so after that I ran a mutation sweep over every guard in the
production diff. Each guard is now either pinned by a test or removed, where no input can
reach it. The six restated suites are byte-identical to v3's hunks (checked file by file);
only `test_integrate_carried_rewrite_late.py` gained one assertion.

## The two carry-forward findings, and what answers each

### 1. The two `pushed` filters in `_heads_taken` had no test

The filters: a line-cut PR counts only if its bundle pushed a branch (patched
`template/src/pdca_harness/flow.py:1025`), and so does an own base (`flow.py:1027`).

The test is the adversary's case, as a pair sharing one helper, `_a2_on_bs_base_alone`
(`template/tests/test_flow_dependency_scoped_bases.py:701`). A and Q are in wave 0. B
(`Depends on: A`, own base), S (`Stacks on: A`, the line) and Y (`Depends on: Q`) are in wave
1. W (`Depends on: Y`) is in wave 2. The fold after wave 0 takes a1. Then fix/A
fast-forwards to a2, which B's base takes. While B builds, fix/A goes back to a1. While W
builds, it is force-pushed to a3.

- `test_a_bundle_that_pushed_no_branch_is_held_to_nothing_and_never_named` (`:743`): B and S
  push nothing. The run goes on (no STOPPING). W is built on its own base holding Q and Y.
  The end check reports the line's lost a1 with "no PR this run cut from <line> holds them".
  Nothing names B's base. holds == `{B: unpushed, S: unpushed, A: rewritten}`.
  - With the bases filter (`:1027`) deleted, the fold after wave 1 stops on a2, which only
    B's base took. That is the adversary's "stops the run over a PR that does not exist",
    and the test fails on "no STOPPING".
  - With the line-cut filter (`:1025`) deleted, the end report names S ("(issue_S)"), which
    has no PR, and the test fails on "no PR this run cut from".
  The adversary's input on its own pinned only the first filter: with fix/A back at a1, S's
  head is intact. The a3 rewrite while W builds is what pins the second.
- `test_a_head_only_a_published_base_took_stops_the_next_fold_for_that_base` (`:729`): the
  same input, every publish succeeding. The fold after wave 1 stops on one line. That line
  starts with B's base's facts (no line facts, since the line's a1 is intact), asks to
  rebuild B's PR, and names neither the line's rewrite nor S. W is not built. This is the
  other half of the pair: what the filters let through when the PR exists. It also pins
  the behaviour deferred item 16 asks the human about ("an in-run fold now stops the whole
  run when ... only a bundle's own base lost it"). If the human decides a base-only loss
  should not stop the run, this is the test to change.

### 2. The `Onto branch` member seam (v3 `flow.py:962`): dropped

v3's `_closure_members` checked each member's publish record for an `Onto branch` commit
(`"stacked"`). By then the walk had already checked every walked bundle's brief for
`Onto branch` (patched `flow.py:939-942`). Every member is walked, so the brief check fires
first whenever the brief says `Onto branch`, and a bundle built this run is published from
that same brief. So the record check fired only when a member's record said `"stacked"` and
its brief did not: a brief edited mid-run, between the member's publish and a later wave.

I dropped it rather than pin it with a test that edits a brief mid-run. In that state the
run now stops at the base build with `_member_cut_point`'s refusal (base
`template/src/pdca_harness/integrate.py:896-899`, patched `:921-924`): "Re-publish <m> as a PR
of its own (no `Onto branch` in its brief), then re-run". That is the right remedy for a
record that no longer matches its brief. A member whose brief says `Onto branch` still keeps
the line, pinned by `test_a_dependent_of_an_onto_branch_bundle_keeps_the_line` (`:409`).

## Every other guard: the mutation sweep

Method: delete or flip one guard, run the 9 touched or fixture suites (plus
`test_integrate_bundle_base` for the base-build guards), restore the file, repeat. On v3's
code, my first sweep found 10 of 11 sampled guards survive deletion; only the "member on the
line" seam was killed (by `test_flow_resume_stack_prereqs.py:227`). Where each one stands
now:

| Guard (patched line) | What deleting it does | Now |
|---|---|---|
| bases filter, `flow.py:1027` | stops a run over a PR that does not exist | pinned, `:743` (new) |
| line-cut filter, `flow.py:1025` | names a PR that does not exist | pinned, `:743` (new) |
| members only on d's target, `flow.py:956` | a cross-target prerequisite becomes a member; `build_bundle_base` refuses it and the run stops | pinned, `test_a_bundle_on_another_target_is_neither_a_member_nor_named` (`:756`, new) and 4 existing tests |
| line-cut heads only of d's target, `flow.py:1006` (v3: `target.get(name) == tgt` in `_heads_taken`) | a PR cut from one target's line is named for another target's branch | pinned, `:756` (new) |
| unchecked items skip line-cut PRs, `integrate.py:1242` | the unchecked report calls S "issue_S's own base None" | pinned: `:695` now asserts S is not in the base line |
| report loop skips line-cut PRs, `integrate.py:1259` | an extra report, "issue_S's own base None took …" | pinned: `_a_taken_twice` (`:573`) asserts no "issue_S's own base" |
| line report names an unjudged line-cut PR, `integrate.py:1266` | S, which may hold a lost head, is not named when git cannot judge its head | pinned, `:600` (new) |
| rewritten wins over unchecked, `flow.py:2913` | holds says "unchecked" for a branch with a reported loss | pinned, `:600` (new; the helper's holds check) |
| several lost heads, `integrate.py:1154` | "Restore to <first head> or a commit that contains it" when two different heads are lost | pinned, `:623` (new) |
| unchecked line with no line-cut PR, `flow.py:2903` | the "no PR" wording swaps for the PR wording | pinned: one assertion added, `test_integrate_carried_rewrite_late.py:340` |
| line facts only when the line lost its head, `integrate.py:1136` | the stop line starts "None Only commits that extend …" | pinned: `:729` asserts the line starts with B's base's facts |

Removed (no input reaches them; deleting each left every test green, and each is now gone):

- v3's `n == d.name` in the walk. `d` is runnable, so it is never accepted, and
  `n not in built` (patched `flow.py:950`) already skips it.
- v3's exclusion of `held_unpushed | held_conflict` from `built` (v3 `flow.py:2694`).
  `_runnable` holds every bundle with a declared edge to such a bundle (base `flow.py:803`
  for prerequisites, `:752` and `:755` for `Conflicts with`). So no runnable bundle has an
  edge to one, and neither does any bundle built after it was held. A partner built later
  than the bundle it is reached from is cut by the wave guard. The docstring says so
  (patched `flow.py:927-929`).
- v3's `if integ.get(target)` before recording a seam's line heads. When the target has no
  line, no fold has carried a branch of it, so the record (now filtered to d's target,
  patched `flow.py:1006`) is empty and adds no PR. What changes: such a bundle now counts as
  a seam for its dependents (`seams`, patched `flow.py:957`). In production that changes
  nothing either, because a dependent's walk goes through the same edges and hits the same
  seam. The seams check is still pinned, by `test_flow_resume_stack_prereqs.py:227`, where
  it matters only because that fixture's publish rewrites the brief without its edges
  (`template/tests/test_integrate_stack_bases.py:156`).
- v3's `(carried or bases)` in `fold` and `(carried_heads or taken[0])` at the end of the
  run. A base's members are built bundles of an earlier wave, never held (above), so the
  fold after their wave recorded a head for each in `carried` (base `integrate.py:640`,
  `:705`) before any base could take one. Back to the base's own conditions (patched
  `integrate.py:529-530`, `flow.py:2843`).
- v3's `in takers` in `_carried_tips` and `rewritten_carried`. Back to the base's
  `in carried` (patched `integrate.py:1111`, `:1230`), for the same reason: every head a PR
  holds is of a branch in `carried`.
- v3's `if not bp.exists()` in the walk. `_bundle_bases` reads each runnable bundle's target
  first (patched `flow.py:982`), which raises on a missing brief, as base
  `_point_at_integration` already does for every runnable bundle (base `flow.py:905`,
  `publish.py:594`, `brief.py:26`). Every built bundle has a brief.

Also simplified: `_heads_taken` no longer reads every accepted bundle's brief on each call
(the code reviewer's efficiency note). The per-target filter moved to where a seam's line
heads are recorded (patched `flow.py:983`, `:1006`), and the `accepted` parameter is gone.

Survivors I left, and why:

- `n in found` (patched `flow.py:950`): a visited set. Deleting it only walks a bundle twice.
  The walk still ends, because prerequisite edges are acyclic and the wave guard makes
  partner edges point to earlier waves only.
- `>=` in the wave guard (patched `flow.py:952`): `>` survives because declared
  `Conflicts with` partners are never scheduled in the same wave, so no input tells them
  apart.
- `sorted(...)` in `_takers` (patched `integrate.py:1071`): it only fixes the order bases are
  named in, and bases are already built in name order.
- `if tip else []` in `build_bundle_base` (patched `integrate.py:841`): #723's own guard
  (base `integrate.py:813`, `if tip and took`), same meaning: a gone member branch is judged
  by `_gone_branch`, not by the rewrite check. #723's suite tests gone members, though
  without a carried head.

## Alternatives ruled out (with cost)

- Finding 1, record `bases_took` / `line_cut` only after a bundle's push succeeds, instead
  of filtering in `_heads_taken`. That moves the same two conditions into `_drive_and_act`'s
  publish loop (about +6 lines there, −2 in `_heads_taken`) and needs the same test. No gain.
- Finding 2, keep the record check and pin it. That keeps 4 lines and adds a test that edits
  a member's brief between its publish and the next wave (about 20 lines). Rejected: it
  would pin a state no run produces, and the fallback without the check (stop with
  `_member_cut_point`'s remedy) is a sound answer to that state.
- Pinning `n in found` or `>=`: no input tells them apart (above).
- Cutting the patch under 125 KiB: that needs about 7 KB out. The new test file's comments
  and docstrings total about 8.9 KB (4.9 + 4.0) and the production diff's comment lines
  about 1.4 KB, so it would mean dropping tests or most of the explanation. Not done.

## Behaviour changes to weigh at sign-off

New this round:

- A member whose publish record is `"stacked"` but whose brief no longer says
  `Onto branch` stops the run at the base build, with `_member_cut_point`'s remedy, instead
  of falling back to the line (finding 2). No run reaches this state without a brief edited
  mid-run.
- Nothing else. The removed guards change no reachable outcome (argued above; every suite
  is green).

From v3, still true:

- The walk goes through every bundle this run built, whatever its target; members are only
  those on d's own target. Example: d (target T1) `Depends on` X (T2), X `Conflicts with` Y
  (T1, earlier wave): Y is on d's base. On `fcae4aa` d sits on T1's line, which holds Y and
  everything else, so d never gets less than before. The members-on-d's-target rule now has
  a test (`:756`); a closure that crosses targets and comes back does not.
- After a base-build stop, the end-of-run check still runs. The exit code is unchanged (1).
  holds can also name other branches `"rewritten"` / `"unchecked"`.
- A base that cannot be built stops the run with one STOPPING line, as a failed fold does.
  Holds instead of stops are #725's.
- Undeclared cross-wave overlaps now surface at the next fold, or at a re-issue's carry (the
  adversary's round-3 note). That is the #725 hold.
- Per-bundle bases start from a freshly fetched `origin/main` (#723's `build_bundle_base`).
  Deferred, not changed here.
- PR shape (brief): until #726 merges, this PR's diff against `main` also shows #723. Merge
  #726 first.

## Refuting my own test (forced)

- **(a) Genuine red? Yes.** The C4 runner (`engine/scripts/run-verify.sh`, `PDCA_BUNDLE` and
  `PDCA_WORKTREE` set) printed `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`.
  Green: 220 tests across the 8 touched modules. Red (production hunks reverted, tests
  kept): 21 of the 25 tests in the new module fail on assertions, all 5 new ones among them,
  plus 29 in the restated suites; no module failed to load. The 4 that pass are criterion
  (6)'s seam tests, which assert `fcae4aa`'s behaviour by design. Stronger evidence for this
  round's findings: each new test fails when its one guard is deleted with the rest of the
  fix in place (the table above). I ran each of those mutations, then restored the file.
- **(b) Production path? Yes.** Every case drives the real `flow._drive_and_act`, with the
  real `integrate.fold`, `integrate.build_bundle_base` and `integrate.rewritten_carried`, on
  real git (a bare `origin`, a primary checkout, a scratch clone, and for `:756` a second
  checkout of its own). Stubbed only what the brief allows: the build and sign-off leaf
  (`_drive_wave`), `_publish_bundle`, `publish.draft_texts` and `gh`. `_publish_bundle` cuts
  the PR branch from the recorded stack-base tip, as `test_flow_same_wave_conflict.py:131`
  does, or, for an id in `unpushed`, returns False before any push, which is what the
  production one returns when publish fails before its push. Two tests wrap `integrate._git`
  to inject a failure (every fetch after B's base's push; one ancestry check). That is fault
  injection on the real calls, not a replacement.
- **(c) Fixture includes the fault? Yes.** B and S really push nothing, and the flow's own
  `pushed` and `held_unpushed` bookkeeping runs on them. fix/A really moves to a2 on origin,
  B's base really takes it (asserted), and fix/A is really moved back and later
  force-pushed. The second target is a real second checkout with its own line on origin
  (base `zbase`), and fix/Z is really force-pushed.

## Criterion (8): every restated existing assertion, before → after

Unchanged from v3 except where marked "this round". Every restatement says what a base
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
  [line, B's base]; the rest unchanged. **This round, one assertion added** (patched :340):
  the unchecked line says "no PR this run cut from the line holds a commit of these
  branches" (B was not cut from the line). Nothing removed.
- `_stopped_at_b` (patched :207) no longer asserts "nothing left for the end of the run to
  check by hand" itself; each caller says what follows (v3; v2's own helper).
- (1d) `test_a_rewrite_during_the_lines_fold_stops_the_run_at_the_dependents_base` (patched
  :295, a v2 test): input unchanged; still exactly one line reports A's rewrite (the stop's;
  the end check skips A), and it asserts no unchecked line (v3).
- `test_a_fetch_failing_after_the_lines_fold_stops_the_run_at_the_dependents_base` (patched
  :348, a v2 test): input unchanged. Before (v2): stop at B's base naming the fetch, no
  unchecked line, 1 failed fetch. After (v3): the same stop line, then the end check, which
  cannot fetch either, names A's branch and head to check by hand with the fetch as the
  cause, and 3 failed fetches. rc 1 both times.

**`test_flow_dependency_scoped_bases.py`** (new file). This round: `_plan` takes a `target`
and writes the brief itself (the fixture's `_brief` hard-codes `org/repo @ main`);
`unpushed` and `_second_target` added; `_a_taken_twice` takes `git` and asserts S is never
reported as a base; the unchecked test asserts S is not in the base line; 5 new tests
(`:600`, `:623`, `:729`, `:743`, `:756`).

## Size

134,909 bytes (131.7 KiB) against `[driver.size_signal] patch_kb = 125` (bytes / 1024).
Round 3 was 127,401 bytes. Per file, this round against round 3: `flow.py` −729,
`integrate.py` −159, the new test file +7,972, the late-rewrite suite +419. The other six
are byte-identical. The rounds leg of the same signal (3 rounds against a threshold of 3)
fires this round whatever the size. Why I did not cut it: see "Alternatives ruled out".

| bytes | file |
|---|---|
| 22,130 | template/src/pdca_harness/flow.py |
| 24,687 | template/src/pdca_harness/integrate.py |
| 42,029 | template/tests/test_flow_dependency_scoped_bases.py |
| 12,156 | template/tests/test_flow_reissue_after_conflict_hold.py |
| 10,179 | template/tests/test_flow_slice.py |
| 8,155 | template/tests/test_integrate_carried_rewrite_late.py |
| 6,697 | template/tests/test_flow_same_wave_conflict.py |
| 5,863 | template/tests/test_flow_resume_stack_prereqs.py |
| 1,714 | template/tests/test_flow_merged_prereq_on_line.py |
| 1,294 | template/tests/test_flow_conflict_partner_hold.py |

## Runs (through the project's runners, bounded by `timeout`)

- C4 `engine/scripts/run-verify.sh` on the final `patch.diff`:
  `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`.
- T3 `engine/scripts/run-suite.sh` on the final `patch.diff`:
  `PDCA-EVIDENCE: root suite OK, driver suite OK` (root 24 tests; driver 2,581 tests,
  2 skipped; round 3 had 2,576, plus this round's 5).
- Mutation sweeps and single-module runs used the runner's own per-module command
  (`cd template && PYTHONPATH=src python3 -m unittest tests.<module>`), each run under a
  900 s subprocess timeout and each sweep under `timeout`.
- After every runner, the worktree diff matched `patch.diff` byte for byte (`cmp`).

## Housekeeping

- No formatter, linter or commit hook is configured in the target (no pre-commit config, no
  ruff/flake8/black settings, only sample git hooks; CI lints docs only). `git diff --check`
  is clean, the longest added line is 98 characters, the changed modules compile, and they
  import nothing unused. The commit rule is the DCO sign-off, which publish adds.
- While running mutations I parked the round-3 state in a temporary local commit in the
  worktree, then undid it with `git reset --mixed fcae4aa`. HEAD is `fcae4aa`, the changes
  are uncommitted, and the new test file is marked intent-to-add (`git add -N`) so
  `git diff` shows it. No untracked files are left in the worktree (`.cache/` is
  gitignored and was there before this round).
- One slip: I wrote one file outside the worktree and this bundle, `/tmp/c4-727-v4.log`
  (the first C4 run's output). I left it in place, since cleanup is the harness's.
  Nothing else was written outside the worktree and this bundle.
- External dependencies: none beyond Python 3.11+ and git (copier for the root suite is
  installed).
