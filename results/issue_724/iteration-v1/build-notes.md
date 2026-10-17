# Build notes — #724 flow builds each bundle on its declared prerequisites

Base: the run's line `pdca-integration/main-r547f8028520f` at `fcae4aa` (= `489e5fb` + #723),
the worktree's HEAD. `patch.diff` is `git diff fcae4aa` plus the new test file; it applies
cleanly to that base (`git apply --cached --check`). "base:N" below means a line on `fcae4aa`,
"new:N" a line after the patch.

## What changed (production)

`template/src/pdca_harness/flow.py`

- **The base each bundle is built on.** The wave loop no longer points every runnable bundle
  at the run's line. Before: `_point_at_integration(integ, runnable, folded_tips)` (base:2549),
  with `integ` filled from every fold (base:2660) and by the carry (base:1208). After: before
  the wave builds, `_bundle_bases` (new:888) builds each bundle's own base and
  `_point_at_integration(bases, runnable, base_tips)` (new:2604) records it, or clears the
  record when the bundle has nothing to carry. `integ` is gone (base:2406).
- **`_closure`** (new:845): the names of the bundles `d` is ordered after by a declared edge,
  followed transitively from every bundle reached: plain `Depends on` and legacy `Stacks on`
  to a scheduled or carried bundle; `Depends on (merged)` to a scheduled bundle only (an
  out-of-batch one must be merged into the base already, `_runnable` #186); a `Conflicts with`
  partner (either side declared it, `waves.conflict_map`) in an earlier wave. Following from
  every member matters: a member's branch was cut from a base holding *its* closure, so a
  base without that work holds commits that are no member's own, and #723 refuses it.
- **`_bundle_bases`** (new:888): members = closure ∩ (carried finished ids first, in the
  order asked, then `accepted`, wave then name order) − held, filtered by
  `integrate._fold_candidates` (base integrate.py:230: a patch and a target) and to `d`'s own
  `(repo, base)`. No members → nothing (real base). Otherwise
  `integrate.build_bundle_base(cfg, d, members, batch=…, carried=heads, excluded=heads)`
  (base integrate.py:716), where `heads` = the carry's heads + the in-run folds'
  `carried_heads`. Every base of the wave is built before any record is written. An
  `IntegrationError` is re-raised naming `d` and its members.
- **Stop on a base failure** (new:2589-2600): the loop prints
  `flow: wave {k} — could not build issue_D's base from …: <#723's error>; STOPPING — wave {k}
  and later waves not run.`, sets `line_stopped` (as a line-fold stop does, so no end-of-run
  rewrite check runs on top) and breaks. Nothing of that wave is recorded. The dependent stays
  PLANNED, so the run exits 1 (`cli._results_rc`, cli.py:701).
- **`_point_at_integration`** (new:818): keys may now be a bundle name (the flow's use) or a
  target tuple (the older direct callers in `test_integrate.py:351,362`,
  `test_integrate_stack_bases.py:1079`). Name wins; neither → clear. Kept rather than replaced
  so `test_flow_adopt_split.py:274`'s spy, which asserts every wave goes through this one call,
  still sees every wave.
- **The carry's heads** (`_carry_finished`, new:1115): the `integ` parameter is removed; a
  new out-parameter `carried` gets name → the head the pushed line took from each carried id.
  The carry now passes an empty dict as the fold's `carried` (new:1208-1213), so the fold
  (base integrate.py:514, :704-705) checks nothing (empty) and fills it after its push;
  `_drive_and_act` (new:2503-2511) turns it into `carried_finished` (members) and
  `carry_heads` (for #723's rewrite check). The carry's stderr line no longer says "this
  run's … bundles build on it" (false now); it says each bundle ordered after them is built
  on a base that holds them. Tests match only its `flow: carried issue_X (finished` prefix.
- **#655 removed.** `_runnable` loses `lines`, `views`, `lacks`, `off_line` and the hold line
  (base:688, :747-748, :767, :785-796, :814-825); an out-of-batch prerequisite merged into
  `d`'s base (`merged.merged_into`) is ready, full stop (new:776). `_line_lacks_merge`
  (base:850-887) is deleted. The `lines` docstring paragraph is replaced (new:734-738).
- Comment updates next to code I changed: the fold-block comment (new:2660-2665),
  `_fold_lines`' `carried` sentence (new:952-957).

`template/src/pdca_harness/merged.py`: `merge_and_head` (base:149-169) deleted — its only
caller was `_line_lacks_merge`; module docstring paragraph (base:24-26) and `_pr_view`'s
docstring (base:188) fixed.

`template/src/pdca_harness/integrate.py`: one docstring sentence in `fold` (new:449-451): the
carry now passes an empty `carried` mapping, which checks nothing and records. Outside the
brief's file list, but the old sentence ("`None` (the pre-wave carry…) checks and records
nothing") became false; no code change in integrate.py.

## Alternatives ruled out (with cost)

- **Carry heads from the carry's PR heads (`heads`, flow.py base:1148) instead of the fold's
  `took`.** Same size (one dict comprehension). Rejected: the PR head comes from `gh`, read
  before the fold; the fold merges the branch tip it reads after its fetch. If the branch
  moved forward in between, recording the older PR head lets a later rewrite that keeps that
  head but drops the newer commits pass #633's check. `took` is exactly what the line holds.
- **Merge the carry's heads into the run's `carried_heads`.** Same size. Rejected: the
  end-of-run check is gated on `if carried_heads` (new:2742) and the in-run folds read it;
  merging would start that fetch in runs where only the carry folded. A separate
  `carry_heads` leaves #695's behaviour as it was.
- **Write each record as its base is built.** Saves one dict, about 3 lines. Rejected: a stop
  on the second base of a wave would leave the first bundle recorded on a base it was never
  built on. Criterion (7) also says no new record may hold X's commits.
- **Replace `_point_at_integration` with a new name-keyed function.** About 10 lines either
  way, but it breaks `test_flow_adopt_split.py:274-276` (it spies `_point_at_integration` and
  asserts `[["issue_500"], ["issue_601"], ["issue_602"]]`) and the three direct test callers.
  Generalising the key costs 3 changed body lines.
- **The first attempt's route (`integrate.fold(into=…)`, `results/issue_463/iteration-v1`).**
  Superseded: the brief names #723's `build_bundle_base`, which is on the base. Its
  `_closure` shape is reused; its `_bundle_bases` is rewritten around `build_bundle_base`.

## The test — `template/tests/test_flow_dependency_scoped_bases.py`

It drives `flow._drive_and_act` through real folds and real `build_bundle_base` calls on the
`StackFoldGit` fixture (loaded by path, as `test_flow_same_wave_conflict.py:36-39`). It
stubs only the build/sign-off leaf, `_publish_bundle` (cuts `fix/<id>` from the recorded
stack-base tip with real git), `draft_texts` and `gh`. It imports only modules.

| Criterion | Test (line) |
|---|---|
| (1) #630 | `test_a_dependent_carries_its_prerequisite_and_nothing_of_an_unrelated_bundle` (:254) — A, Z two commits each; every commit of `main..fix/A` on `fix/B`, none of `main..fix/Z`; B's record is an origin branch holding A's tip, not Z's; recorded tip = that branch's tip at drive time = where `fix/B` was cut; all COMPLETE |
| (2) | `test_the_base_carries_every_prerequisite_reached_through_another` (:280) |
| (3) | `test_an_earlier_wave_conflicts_with_partner_is_on_the_base` (:297) |
| (4) | `test_an_in_batch_depends_on_merged_prerequisite_is_on_the_base` (:313) |
| (5) | `test_a_bundle_whose_only_prerequisite_has_no_patch_is_built_on_the_real_base` (:328) — record cleared, `fix/H` cut from main, no commit of A or Z |
| (6) | `CarriedPrerequisiteBases.test_a_carried_finished_prerequisite_is_on_its_dependents_base_alone` (:428) |
| (7) | `…test_a_carried_prerequisite_cut_from_a_line_holding_another_stops_the_run` (:444) |
| (8) | `…test_a_carried_prerequisite_rewritten_after_the_carry_stops_the_run` (:483) |
| (9) | `MergedPrerequisiteJudgedOnTheBase` (:521), plain and `(merged)` edge |
| extra | `test_a_branch_the_line_carried_rewritten_before_a_dependents_base_stops_the_run` (:351) — the in-run `carried_heads` reach `build_bundle_base` |

Notes on reading the criteria:

- **(7) "no branch holding X's commits is recorded as anyone's stack base".** P's own record
  must hold X: it is the earlier run's record (old line, its tip), and without it #723 has no
  cut point below which X's commit counts as foreign. With no record and `new-pr`, X's commit
  would count as P's own and the base would hold it; with no record and `stacked-pr`, #723
  refuses without naming X. So the test reads "anyone" as every bundle of this run. It
  asserts D and X have no record, P's record is exactly the earlier run's (untouched), and no
  base branch for D reached origin.
- **(8) "the wording … the test reads from that error".** The test calls
  `integrate._carried_rewrite(origin, "issue_P", "origin/fix/P", took, rebuilt, line)` (base
  integrate.py:1067, #633's own wording) and asserts that text is in the STOPPING line. It
  also spies `integrate.build_bundle_base` with a pass-through and asserts its `carried`
  kwarg had `issue_P → took`. That is the direct proof that the carry's head reached it.
- **"No commit of any other run bundle's branch"** is checked as that bundle's *own* work:
  `fix/<o>` minus main minus the commit its branch was cut from (its recorded
  `stack-base-tip`) minus the closure heads (`StackFoldGit._own`). A literal reading fails on
  any bundle built on top of `d` (30's branch contains 21's base). That is the same ownership
  rule #723 uses (`_member_cut_point`, base integrate.py:862). The helpers also assert
  `_beyond(tip, main, heads) == []`: beyond the base and the closure heads, the tip holds only
  merges on its own first-parent chain. That is stronger than the criterion's wording.

## Red → green (run with `cd template && PYTHONPATH=src python3 -m unittest …` under `timeout`)

- **Green**, full patch: the new file has 11 tests, OK. Criterion (10) suites
  (`test_integrate_stack_bases`, `test_flow_same_wave_conflict`,
  `test_flow_resume_stack_prereqs`, `test_flow_merged_prereq_on_line`,
  `test_flow_conflict_partner_hold`, `test_flow_reissue_after_conflict_hold`,
  `test_flow_hold_exit_code`, `test_integrate_carried_rewrite_late`, `test_flow_slice`,
  `test_integrate_bundle_base`) all OK. The whole driver suite `discover -s tests` ran 2563
  tests, OK (skipped=2). The project's T3 runner (`engine/scripts/run-suite.sh`, under
  `timeout 3000`) printed `PDCA-EVIDENCE: root suite OK, driver suite OK` (root 24 tests,
  copier from the instance venv).
- **Red**, `git checkout -- template/src` (tests kept): `FAILED (failures=11)`, 0 errors.
  Each fails on its claim. (1)-(4): `_none_of(fix/<x>, "Z")` finds Z's commits. (5): record
  is the line, not `("", "")`. (6): `_holds_none_of(tip, "X")` finds X's commit on D's base.
  (7), (8), extra: D/B is in `seen` (built on the line). (9): an `issue_D held` line is
  printed. Then `git apply` of the saved production diff, and it was green again.

## Self-refutation

- **(a) Genuine red?** Yes. With `template/src` reverted to `fcae4aa`, all 11 fail on
  assertions (above), none on import. #723's code stays, as the brief says.
- **(b) Production path?** Yes. The tests call `flow._drive_and_act` itself. The real
  `_runnable`, `_carry_finished`, `_bundle_bases`, `_closure`, `integrate.fold`,
  `integrate.build_bundle_base`, `publish.write_stack_base` and `clear_stack_base` all run
  against real git repos. In (8), `_carry_finished` and `build_bundle_base` are wrapped by
  spies that call the real function. No copy or re-implementation.
- **(c) Fixture includes the fault?** Yes. Z is a real two-commit bundle of the same wave and
  is on the line (asserted). In (5) the line holds A and Z (asserted). In (6) X is carried on
  the line. In (7) P's branch really is cut from a line holding X, and X is carried. In (8)
  `fix/P` is really force-pushed after the real carry (asserted not a fast-forward). In (9)
  P's merge is really on main and really absent from the line (asserted). In the extra case
  `fix/A` is really force-pushed after the line's fold.

## Existing tests changed (criterion 10) — every change, before → after

**Assertions restated by content** (the helper `_built_on(iid, *closure)` replaces
`_built_on_line` / `base == self.line`). Its check: the record is non-empty; the recorded tip
is origin's tip of that branch when the wave was driven; each closure head is on it; no other
run bundle's own work is on it; nothing beyond main and those heads except the build's
first-parent merges; COMPLETE. Where an old assertion said an *unrelated* bundle was on the
dependent's base (the #630 behaviour itself), that claim moves to the run's line, which
still folds everything.

- `test_flow_same_wave_conflict.py`: `_built_on_line` (:169) → `_built_on`. Test 1:
  `on21` held 10 and 12 → `_built_on("21","12")`; `on30` held 10, 12, 21 →
  `_built_on("30","21","12")`; 10, 12, 21 are asserted on the line instead. Test 3: 20 and 21
  each held 10, 11, 12 → `_built_on("20","11")`, `_built_on("21","12")`, and 10, 11, 12 are
  on the line. `_built_on("30","21","12")`. Test 4: `on50` held 40 and 42 →
  `_built_on("50","42")`; 40 and 42 on the line, 41 on neither. Partner test:
  `_built_on("21","12")`. Mid-wave test: `_built_on("30","20","10")`; 20 on the line, 22 on
  neither.
- `test_flow_resume_stack_prereqs.py`: (1) `base == self._line([...])` → `_built_on("D","P")`
  + fix/P on the line. (2) `_built("D")[:2] == (line, old)` → line tip at D's drive == old,
  origin's line tip == old, `_built_on("D","P")`. (3) D/E on `(line, …)` →
  `_built_on("D","P")`, `_built_on("E","D","P")`; carried, fix/P and fix/D are on the line
  after the wave-0 fold; push count is now of the line's pushes (2). (4c) →
  `_built_on("B","Q")` + Q on the line. Untrusted line, red re-gate, old line:
  `_built_on("W","U")`. Without-a-finished-prereq: `_built("E")[0] == self.line` →
  `_built_on("E","D")`. Beside-them: E and U built on the line holding X →
  `_built_on("E","X")`, and **U on the real base** (`_on_base("U")`). U declared no edge, so
  under the Invariant its base must not hold X; X is asserted on the line. `_carried_beside`
  (used by 7 #672 tests): all pushes == 1 → the line's pushes == 1, X on the line, return
  `_built_on("E","X")`.
- `test_flow_merged_prereq_on_line.py` (the #655 hold tests flip per (9)): `_held` and
  `_built_on_line` are replaced by `_built_on` and `_not_held`. Tests (1)/(2)
  `…holds_…_dependent` → `…builds_…_dependent`: not held, `_built_on("D","W")`, merge on its
  tip. (3)/(4): `_built_on_line()` → `_built_on("D","W")`. Unreadable merge commit: held →
  built on a base with the merge (only the line check needed `mergeCommit`).
  Cannot-be-fetched: **held → the run stops before D** (D never built, PLANNED, no record,
  one STOPPING line naming issue_D and "could not fetch origin"). This follows the brief's
  "A base build failure stops the run" (#725 makes it a hold). Carried-prereq: D on the line
  at `old` → line still at `old` holding fix/P and not the merge; D on the real base (its
  `(merged)` edge names an id the run does not schedule, merged into main), COMPLETE;
  `_built_on("E","P")`. `test_the_way_out_is_to_delete_the_line_then_re_run` →
  `test_no_way_out_is_needed_the_dependent_is_built_in_the_first_run` (D built in run 1 on a
  base with the merge and W, not the line; no "delete the line" advice printed).
- `test_flow_reissue_after_conflict_hold.py`: `_stacked_on_10`'s
  `seen["issue_12"][0] == self.line` → `self.line_under_12 = self._built_on("12","10")`.
- `test_flow_slice.py`: three-wave test. `cut_from["issue_EB"] == origin/<line>` →
  `_built_on("EB","EA")`, `_built_on("EC","EB","EA")`. `fix/issue_EB~1` in the line → the
  first fold's recorded tip `tips[0]` is in the line (append-only). The merge count
  `log --merges` → `log --merges --first-parent` (EB's branch now brings the merge of EA its
  own base made, so the old count is 2; the line's own folds still merged EA once). Push count
  → the line's pushes (2). ZB test renamed
  `…carries_every_earlier_wave_branch_not_only_its_prerequisite` →
  `…carries_only_its_prerequisite_not_every_earlier_wave_branch`. It asserted the #630
  defect: ZZ on ZB → **ZZ not on ZB**, `_built_on("ZB","ZA")`, diffs `[ZA, ZB]` then
  `[ZB]` right after ZA merges, one merge base `[za]`. The now-unused `_update_from_main`
  helper is deleted.

**Test inputs / stubs changed** — every one:

1. *Declared edge (allowed by (10)).* `test_flow_reissue_after_conflict_hold.py`
   `test_one_the_fold_merges_after_it_is_named_too`: 21 `Depends on: 12` → `Depends on: 12, 10`
   (via a new `twenty_one_on` parameter of `_held_for_10`, default `"12"`, so every other
   caller is unchanged). The premise "21's change on top of 10's" now needs the edge. Without
   it, 21 is built without 10 and the carry names only 10 (the failure seen before the
   change).
2. **Outside (10)'s literal allowance — please check.** `test_flow_resume_stack_prereqs.py`
   `_publish_bundle`. Before: `fx._publish(...)`, which rewrites brief.md through `_brief(d)`
   and drops its `Depends on`. After: the brief is saved and restored around it, as
   `test_flow_same_wave_conflict.py` (base:138-140) and `test_integrate_carried_rewrite_late.py`'s
   stub already do. Real publish never edits brief.md. Without this,
   `test_the_fold_after_wave_0_continues_the_carried_line` stops: D's brief (rewritten) no
   longer names P, so E's closure is `{D}`, and #723 refuses E's base for P's commit below
   D's cut point. That is correct behaviour on a corrupted input. (I added the same restore
   to `test_flow_merged_prereq_on_line.py` at first, found it was not needed, and removed it.)
3. **Outside (10)'s literal allowance — please check.** `test_integrate_carried_rewrite_late.py`.
   `test_a_rewrite_during_the_last_fold_is_reported_and_exits_1`: the rewrite was triggered
   on the first push (the line's fold); now on the first push that is not the line's (B's
   base, the run's new last read of `fix/A`). `test_an_end_of_run_check_that_cannot_fetch_…`:
   fetches failed after the first push; now after B's base push (`armed`), with the line's
   push count still asserted == 1 and B's base push == 1. Both premises are "the fault comes
   after the run's last read of fix/A, so only the end-of-run check can see it". With the
   old trigger the fault now lands *before* B's base build, which correctly stops the run.
   The new extra test pins exactly that case.
4. *Stub of the new git step, in tests that already stub git.*
   `test_flow_conflict_partner_hold.py` `_run(stub_fold=True)`: `flow._bundle_bases` stubbed
   to `({}, {})` (`create=True`) beside the existing `_fold_lines` stub; the temp dir has no
   checkout. `test_flow_slice.py` `_live(fold=…)`: `integrate.build_bundle_base` answered with
   `("pdca-integration/main-b<name>", "0"*40)` beside the fold spy.
5. *Fixture helpers added* (`test_integrate_stack_bases.py`): `StackFoldGit._beyond`,
   `StackFoldGit._own`. No existing assertion there changed.

## Left as is, on purpose (brief: out of scope, #725)

- Prose stating the old stack rule: `_drive_and_act` docstring (new flow.py:2359),
  `_runnable` docstring (new:693-694, :721), `_adopt_split_children` docstring (new:1883),
  `config.py:359-360`, `integrate.py`'s module docstring, `publish.py` docstrings,
  `gates.py:535-539`, `drift.py:53`.
- Two user-facing messages that still say PRs were "cut from the line": the end-of-run
  report's remedy (new flow.py:2783) and `integrate.rewritten_carried`'s text (new
  integrate.py:1132). The remedy (rebuild PRs that took that commit) still points the right
  way, but names the old mechanism. Worth folding into #725.

## Risks for sign-off

- **Any base build failure stops the whole run before the wave**, including bundles unrelated
  to it (a conflict between two members, one with the moved base, a fetch failure). This is
  as the brief specifies; #725 makes it a hold.
- **Undeclared cross-wave overlaps now hit the line fold more often.** A later bundle is no
  longer built on the line, so an overlap with an unrelated earlier-wave bundle conflicts at
  the line fold and stops the run (`integrate.py` `_held_by` only holds same-wave clashes).
  Deferred to #725 by the brief. No existing suite has this case.
- **Re-running a batch rebuilds bases with a force-push leased on the old tip.** An origin
  with `receive.denyNonFastForwards` refuses that, and the run stops with #723's message
  ("delete it there or allow force-pushes"). The line's first fold has the same need already.
- Per-bundle base branches stay on origin (cleanup out of scope).
- `Conflicts with` naming a carried finished id is not a member: the Invariant counts only
  earlier-wave partners, and a carried id is in no wave. Before, such a bundle sat on the line
  that held the carried id.
- A carried id whose branch is gone (the fold judged it by its merge; no head recorded) is
  still a member, and `build_bundle_base` judges it through `_gone_branch`. No test covers
  this path.

## Housekeeping

- No formatter, linter or commit hook is configured in the target (no `.pre-commit-config`,
  no ruff/black config, no hooks in `.git/hooks`; CI runs docs checks and copier renders). I
  kept new lines at 100 characters or fewer, as the files do, and checked with `ast` that no
  import in a touched file is unused.
- By mistake I wrote one baseline log to `/tmp/claude-baseline.log` before switching to the
  worktree's ignored `.cache/`. The harness can reclaim it; nothing reads it.
- No external dependency was missing: Python 3 and git only; copier from the instance venv
  for the root suite.
