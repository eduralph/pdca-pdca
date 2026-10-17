# Build notes — issue_729 (flow-merged-prereq-judged-by-merged-into), iteration 2

Target: eduralph/pdca-harness. Worktree `$PDCA_WORKTREE` = `/home/eddie/pdca/pdca-harness.pdca-wt`,
detached at `f10beed` = the run's line `pdca-integration/main-r547f8028520f` (matches the
bundle's `stack-base` / `stack-base-tip`). That line holds #727 (`c423f9d`) and #728
(`f10beed`). Every `path:line` below is on that tree **with this patch applied**, unless
marked `fcae4aa`.

## Precondition from #727 — checked, holds

- Own base: `integrate.build_bundle_base` (`integrate.py:732`) "always starts fresh from the
  base as fetched" (`integrate.py:748`). It calls `_prepare_worktree` (`integrate.py:835`),
  which fetches on every call (`integrate.py:2052`), then starts the branch from the
  just-fetched `<base_remote>/<base>` (`integrate.py:852`). It is called per bundle, per
  wave, from `flow._bundle_bases` (`flow.py:1016`), which the wave loop calls each wave
  (`flow.py:2761`). No once-per-run snapshot.
- Empty closure: `_bundle_bases` clears the stack base (`flow.py:1034`), so Do's worktree
  fetches (`worktree.py:364`) and branches off `<base_remote>/<base>` (`worktree.py:93-99`):
  the real base as fetched when the bundle is built.
- Both fetches happen after `_runnable` has judged the prerequisite merged, so both trees
  hold that merge. Criterion (1) is true; no stop condition.

## The carry-forward item — addressed

Last round's own-base test called `h._built_on_line()` and then repeated its checks by
hand, and the line `tip = h._built_on_line()  # D built; on its own base` read as the
opposite of what it checked. This round the new file does **not** call `_built_on_line`
at all. `_built_on_its_own_base_with_the_merge`
(`template/tests/test_flow_merged_prereq_dependency_base.py:90-103`) states each fact once:
D is in `seen`; its stack base is `integrate.bundle_base_branch(cfg, "main", ["W", "D"],
"issue_D")` (D's own base, not the line); origin's tip of that branch is the tip D was
built on; that tip holds P's merge commit and W's branch; D is COMPLETE. Same facts as last
round, none weaker, no duplicates.

## Two more changes, taken from last round's advisory code review

These were not required by the carry-forward. I made them because each one closes a gap
the reviewer named, and I record them so they are not a surprise at sign-off.

1. **One plan per wave, shared by `_runnable` and `_bundle_bases`.** Last round extracted
   `_base_plans` and called it twice per wave: once on the whole wave for `on_line`, then
   again inside `_bundle_bases` on `runnable`. The two answers agreed only because nothing
   between the calls changes `accepted`, `wave_of`, `finished`, `bundles` or `line_cut`.
   Now the wave loop calls `_base_plans` once (`flow.py:2694-2696`), derives `on_line` from
   it (`flow.py:2697-2698`), and passes the same dict to `_bundle_bases` (`flow.py:2761`).
   So the bundles judged on the line are, by construction, the bundles pointed at the line.
   That is the brief's invariant ("judged on the base it will actually be built on") held
   by the code's shape, not by two call sites staying in step.
2. **A real-base test.** The reviewer noted that no test drove the second "not on the line"
   case, `_closure_members` returning `[]`. The new
   `test_a_merge_after_the_first_fold_builds_a_dependent_on_the_real_base`
   (`…dependency_base.py:112-127`) does: see Tests below.

## What changed (production)

1. `flow.py:689` — `_runnable` gets `on_line: Collection[str] | None = None`: the names of
   the wave's bundles built on the run's line. `None` means every bundle (the behaviour
   before this patch); it is the default, so the direct `_runnable(` callers in other
   suites (`test_flow_slice.py:1984-2005`, `test_flow_out_of_batch_prereq_hold.py:156`)
   keep today's rule. None of them passes `lines=`, so the line check never ran there.
2. `flow.py:795-796` — the #655 line lookup now runs only when
   `on_line is None or d.name in on_line`. For any other bundle `line` is `None`, so the
   existing `continue` (`flow.py:797-798`) runs and `merged.merged_into`
   (`flow.py:790`) alone decides. `_line_lacks_merge` (`flow.py:859`) and
   `merged.merge_and_head` (`merged.py:151`) are unchanged.
3. `flow.py:970-989` — new `_base_plans`: the plan loop that was inline in `_bundle_bases`
   (`flow.py:978-986` on `c423f9d`), moved out unchanged except that it iterates `ds` and
   takes `seams` (the caller passes `line_cut`, as before). It **calls** #727's
   `_closure_members` (`flow.py:922`), which returns a str exactly when the bundle sits at a
   seam (`Stacks on` / `Onto branch` at `flow.py:948-951`, a finished id, or a member at a
   seam). That is the "called, not copied" seam-fallback predicate the brief asks for.
4. `flow.py:992-999` (docstring `:1000-1002`) — `_bundle_bases` takes `plans` instead of
   `built`, `finished` and `bundles` (used only to build the plans). Its body after the plan loop is unchanged; it
   reads `plans[d.name]` (`flow.py:1011`, `:1025`) for each runnable `d`. It has no caller
   outside `flow.py` (grep over the repo: only `flow.py:2761`).
5. Wave loop `flow.py:2690-2698`, `:2711-2713`, `:2761` — compute `built`, `plans`,
   `on_line` once per wave; pass `on_line` to `_runnable` beside `lines=`, and `plans` to
   `_bundle_bases`. When `own_bases` (`flow.py:2680`) is false, `plans = {}` and
   `on_line = None`, which is exactly the old pointing (`_point_at_integration` for all).
6. Docstrings / comments (criterion (3)): `_runnable` `flow.py:736-750`, the comment at
   `flow.py:791-794`, `merged.py` module docstring `merged.py:24-28`, `_pr_view`
   `merged.py:190-191`, plus `_base_plans` and `_bundle_bases`' first sentence.

Criterion (3) leftovers: `lines=` stays and is still read (`flow.py:795`) for the bundles in
`on_line`; `views`, `lacks`, `off_line` and the #655 message block are still used for them.
`_bundle_bases` lost the three parameters it no longer needs. Nothing unused is left.

Why plan the whole wave before `_runnable` is safe: a bundle `_runnable` holds always has a
brief (it read deps from it, or `_resolve_target` read it for a partner,
`flow.py:768-769`); `waves.conflict_map` skips missing briefs (`waves.py:145-147`);
`_closure_members`, `_fold_candidates` and `publish._resolve_target` only read files and
raise no `IntegrationError`. A bundle's plan depends only on that bundle and on inputs
`_runnable` does not change, so `_bundle_bases` gets the same answers as when it computed
them itself.

## Alternatives considered

- **Last round's shape (call `_base_plans` twice).** Cost, measured: last round's `flow.py`
  hunk was +52/−23; this round's is +62/−31 (`git apply --numstat`), i.e. 18 more changed
  lines. They come from `_bundle_bases`' signature (three params swapped for `plans`) and its
  first docstring sentence, plus slightly longer wording in the `_runnable` docstring and
  the wave-loop comment. In exchange: one `waves.conflict_map` (reads every brief of
  `bundles` + `finished`), one `_fold_candidates` and one closure walk per bundle per wave
  instead of two, and the invariant holds by construction. Since the brief names an
  invariant, I took the shape that holds it structurally.
- **Delete `_line_lacks_merge`.** Ruled out by the brief: seam bundles (`Stacks on`,
  `Onto branch`, an edge to a finished/carried id) are still cut from the line
  (`flow.py:1026-1028`), so the check still guards something real for them. The mutation
  check below shows the suite would catch this.
- **Re-derive the seam test inside `_runnable`** (read `Stacks on` / `Onto branch` / the
  finished set there). Rejected: the brief says call #727's predicate, and a copy would also
  have to repeat the "member pointed at a seam itself" rule (`flow.py:966-967`).
- **Run `_bundle_bases` before `_runnable`.** Would build and push bases for bundles that
  are then held. A behaviour change in #727's territory; out of scope.

## Tests

### New: `template/tests/test_flow_merged_prereq_dependency_base.py` (class `MergedPrereqOffTheLine`)

Loads `tests/test_flow_merged_prereq_on_line.py` by path and uses its class as a helper
object (real-git `StackFoldGit` fixture, `gh` stub, stubbed build/publish leaves), so
nothing of that fixture is copied. Drives `flow._drive_and_act`. Unittest discovery does
not collect the helper class from this module (it is reached only as `ol.…`): the driver
suite runs 2594 tests now against 2593 last round, whose version of this file had 4 tests
(this one has 5).

Shared check `_merged_after_the_first_fold` (`:48-61`): W COMPLETE; the run's line exists on
origin and holds W's branch (added this round — without it, "the line lacks P's merge"
would pass vacuously if no line had been made); the line lacks P's merge commit and P's
head.

- `test_a_merge_after_the_first_fold_builds_a_depends_on_merged_dependent` (`:105`) —
  criterion (1), `Depends on (merged): P`.
- `test_a_merge_after_the_first_fold_builds_a_plain_depends_on_dependent` (`:108`) —
  criterion (1), plain `Depends on: P`, P not in the batch (#647).
  Both: no `issue_D held` / `issue_D skipped` line; D's stack base is its own base branch;
  origin's tip of it equals the recorded tip; that tip holds P's merge commit and W; D
  COMPLETE.
- `test_a_merge_after_the_first_fold_builds_a_dependent_on_the_real_base` (`:112`) — W
  (unrelated, gives D's target a line), N (closes with no patch, publishes nothing — built
  the way #727's suite builds one, `test_flow_dependency_scoped_bases.py:121-122`), D
  (`Depends on: N` + `Depends on (merged): P`). D's closure has no member with work, so its
  plan is `[]`: not held, no stack base recorded (`seen == ("", "")`, `stack-base` absent),
  main has P's merge, D COMPLETE. The no-patch behaviour is a test-local wrapper around the
  helper's two stubs (`_closes_with_no_patch`, `:68-86`); it does not touch production.
- `test_an_unmerged_depends_on_merged_prerequisite_still_holds_the_dependent` (`:142`) and
  `test_an_unmerged_plain_depends_on_prerequisite_still_holds_the_dependent` (`:145`) —
  criterion (2): P's PR stays OPEN; D never built, PLANNED, one `issue_D held … issue_P …
  not merged into main` line. Guards: green before and after.

### Changed: `template/tests/test_flow_merged_prereq_on_line.py` (criterion (4))

The brief's anchors are on `fcae4aa`. On the base (`f10beed`) every test sits 12 lines lower
(#727 restated `_built_on_line`, now `:201-220`, unchanged by this patch), and this patch
moves them 10 more (docstring, `ON_LINE`, `_wd`'s docstring). "now" is the patched file.

| `fcae4aa` | now | test | before | after |
|---|---|---|---|---|
| `:1-12` | `:1-17` | module docstring | rule stated for every dependent | rule stated only for a dependent built on the line (a seam: here `Stacks on: W`, or a carried prerequisite); own-base / real-base case pointed at the new file |
| — | `:54-56` | `ON_LINE` constant | — | `"- **Stacks on:** W\n"` |
| `:169` | `:177-180` | `_wd` | `_wd(edge)` | `_wd(edge, *, on_line=False)`; `on_line=True` adds `ON_LINE` to D's brief |
| `:202` | `:224` | `…_holds_a_depends_on_merged_dependent` | D `Depends on: W` + `(merged): P` (own base after #727), held | same + `Stacks on: W` (line-based), held; assertions unchanged |
| `:212` | `:234` | `…_holds_a_plain_depends_on_dependent` | D `Depends on: W, P`, held | + `Stacks on: W`, held; unchanged |
| `:241` | `:263` | `test_an_unreadable_merge_commit_holds_the_dependent` | own-base D, held | + `Stacks on: W`, held; unchanged |
| `:249` | `:271` | `test_a_checkout_that_cannot_be_fetched_holds_the_dependent` | own-base D, held | + `Stacks on: W`, held; unchanged |
| `:293` | `:315` | `test_the_way_out_is_to_delete_the_line_then_re_run` | own-base D, held twice then built | + `Stacks on: W`; held twice, then built on the line; unchanged |
| `:222`, `:230` | `:244`, `:252` | merge / squash already on the line | as #727 left them | unchanged |
| `:257` | `:279` | target with no line | as #727 left it | unchanged |
| `:269` | `:291` | carried P | as #727/#728 left it (#728's) | unchanged |

Only `_wd` calls changed in the five held tests (`:228`, `:238`, `:268`, `:276`, `:322`). No
assertion was removed or weakened. `Stacks on: W` is added *beside* `Depends on: W`, not
instead of it: the way-out test's re-run needs W carried, and the carry starts only from a
plain `Depends on` edge. `Stacks on` is a seam to `_closure_members` (`flow.py:948-951`), the
same seam #727's own suite uses (`test_flow_dependency_scoped_bases.py:422`).

## Red → green (project runner `engine/scripts/run-verify.sh`, C4)

Run from the instance root with `PDCA_BUNDLE=results/issue_729`,
`PDCA_WORKTREE=/home/eddie/pdca/pdca-harness.pdca-wt`, on the final patch:

- green leg: `test_flow_merged_prereq_on_line` 9/9 OK; new file 5/5 OK.
- red leg (the script reverts `flow.py` and `merged.py` only): line-based suite still 9/9 OK
  (criterion (3) guard green before and after); new file FAILED (failures=3) — the two
  own-base cases and the real-base case, each at `_not_held` with the exact #655 hold:
  `flow: issue_D held — prerequisite(s) issue_P (merge commit …): their PR merged into main
  (org/repo), but the line issue_D would build on, pdca-integration/main-r… at …, does not
  have that merge; …`. They fail after the line-exists / W-on-line / line-lacks-merge checks
  pass, so the fault really is present. The two criterion (2) guards pass.
- verdict: `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`. The script's trap
  restored the tree; I confirmed the worktree diff is byte-identical to `patch.diff`.

### Mutation check for criterion (3)

To check that the line-based suite would catch a patch that stopped judging *every* bundle
on the line, I temporarily passed `on_line=set()` at `flow.py:2713` and ran that one module
with the runner's own command (`cd template && PYTHONPATH=src .venv python -m unittest
tests.test_flow_merged_prereq_on_line`, under `timeout 300`): `FAILED (failures=5)`,
exactly the five re-pointed held cases. Restored, then re-verified the worktree equals
`patch.diff`.

### Full suite (`engine/scripts/run-suite.sh`, T3, final tree)

Root suite: `Ran 24 tests … OK`. Driver suite: `Ran 2594 tests … OK (skipped=2)`. Verdict
`PDCA-EVIDENCE: root suite OK, driver suite OK`.

## Refute-your-own-test

- **(a) Genuine red?** Yes. C4's red leg reverts only the production hunks; all three
  criterion (1) tests fail with the #655 hold message quoted above. The mutation check
  shows the five re-pointed line-based cases fail when the line check is dropped for all.
- **(b) Production path?** Yes. The tests call `flow._drive_and_act`, which runs the real
  `_base_plans` → `_closure_members`, `_runnable`, `_line_lacks_merge`, `_bundle_bases` →
  `integrate.build_bundle_base`, and `integrate.fold`, against real git repos (bare origin,
  primary checkout, maintainer clone). Stubbed: the build/sign-off leaf (`_drive_wave`),
  `_publish_bundle` (replaced by the fixture's real-git publish), `publish.draft_texts`, and
  `gh` (answered from a dict). None of those is code this patch changes.
- **(c) Fixture includes the fault?** Yes. P's PR is really merged into origin's `main`
  (`fx._merge_pr`) *after* the run's first real fold, so the real line lacks the merge. The
  tests assert the line exists, holds W, and lacks P's merge commit and head before
  asserting D is built; the own-base tests assert the base D was built on really contains
  P's merge commit.

## Commit-readiness

The target has no formatter or linter config and no commit hooks: no
`.pre-commit-config.yaml`, no `core.hooksPath`, only `*.sample` files in the common hooks
dir. CI runs the root suite (`render-check.yml`) and the docs checkers (`docs-check.yml`),
neither of which this patch can trip outside the suites run above. CONTRIBUTING.md asks for a
DCO `Signed-off-by`, which publish adds. `git diff --check` is clean; the longest added line
is 99 columns (the files' style keeps to 100).

## For the human at sign-off

- The brief's plan-review response asks the human to confirm the narrowed goal: keep the
  #655 line check for line-based (seam) bundles, drop it only for bundles on their own or
  the real base. This patch builds exactly that.
- The seven deferred findings in `deferred-findings.json` are plan / prior-art / tracker
  questions, not build work; none was touched here.
- No files were written outside the worktree and this bundle (test fixtures use their own
  `tempfile` dirs and remove them).
