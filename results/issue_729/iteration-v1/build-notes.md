# Build notes — issue_729 (flow-merged-prereq-judged-by-merged-into)

Target: eduralph/pdca-harness, worktree `$PDCA_WORKTREE` at `f10beed` (the run line
`pdca-integration/main-r547f8028520f`, which holds #727 = `c423f9d` and #728 = `f10beed`).
All `path:line` below are on that tree with the patch applied unless marked `fcae4aa`.

## Precondition from #727 (checked before building)

Holds. `integrate.build_bundle_base` (`integrate.py:732`) "always starts fresh from the base
as fetched" (`integrate.py:748`) and is called once per wave per bundle from
`flow._bundle_bases` (`flow.py:1015-1017`), which the wave loop calls each wave
(`flow.py:2758`). A bundle with an empty closure gets `publish.clear_stack_base`
(`flow.py:1033`, the `else` branch), so it builds from the real base. No per-run snapshot of the base. So
criterion (1) is true and the line check can be dropped for those bundles.

## What changed

1. `flow.py:968-986` — new `_base_plans(cfg, ds, built, finished, bundles, seams)`: the
   per-bundle plan loop that was inline in `_bundle_bases` (on `c423f9d`, the
   `conflicts = …` / `cands = …` / `for d in runnable: … _closure_members(…)` block),
   moved out unchanged. It still *calls* #727's `_closure_members` (`flow.py:920`), which
   returns a str exactly when the bundle sits at a seam (stays on the line). That is the
   "called, not copied" predicate the brief asks for.
2. `flow.py:1006` — `_bundle_bases` now calls `_base_plans` instead of the inline loop. Same
   inputs (`seams=line_cut`), same output, so how bases are chosen does not change.
3. `flow.py:2689-2697` — the wave loop builds `built` once per wave and computes `on_line`
   = names of the wave's bundles whose plan is a seam (only when `own_bases`; else `None`
   = every bundle, which is exactly the pre-#727 pointing via `_point_at_integration`).
   `flow.py:2710` passes it to `_runnable`; `flow.py:2758` reuses `built` for
   `_bundle_bases`. Between the two calls nothing they read changes (`accepted`,
   `wave_of`, `finished`, `bundles`, `line_cut` are only updated after the wave drives), so
   `_runnable` and `_bundle_bases` see the same answer for each bundle.
4. `flow.py:689` — `_runnable` gets `on_line: Collection[str] | None = None`.
   `flow.py:794-795` — the #655 line lookup now happens only when
   `on_line is None or d.name in on_line`. For any other bundle `line` is `None`, so the
   existing `continue` at `flow.py:796-797` runs: `merged.merged_into` (`flow.py:789`) alone
   decides. `_line_lacks_merge` and `merged.merge_and_head` are untouched.
5. Docstrings: `_runnable` (`flow.py:735-748`), the comment at `flow.py:790-792`,
   `merged.py` module docstring (`merged.py:24-28`), `_pr_view` (`merged.py:188-191`).

`lines=` stays and is still used (for seam bundles and for runs with no own bases). No
parameter or bookkeeping was left unused. Default `on_line=None` keeps every direct caller
of `_runnable` (other unit suites) on today's behaviour.

## Alternatives considered and ruled out

- **Delete `_line_lacks_merge` entirely.** Ruled out by the brief: seam bundles (`Stacks
  on`, `Onto branch`, an edge to a finished/carried id) are still cut from the line
  (`flow.py:1025-1027`), so for them the line check guards something real.
- **Copy the seam test into `_runnable`** (re-read `Stacks on` / `Onto branch` and the
  finished set there). Rejected: the brief requires calling #727's predicate, and a copy
  would drift from `_closure_members` (it also has the "member pointed at a seam itself"
  rule, `flow.py:964-965`, which a copy would have to repeat).
- **Have `_bundle_bases` run before `_runnable` and return the plans.** Would move base
  building (which pushes branches) ahead of the readiness filter, so a held bundle would
  get a base pushed for it. Bigger behaviour change, out of scope (#727's territory).
- **Pass the plans dict into `_bundle_bases` instead of recomputing.** Saves one
  `conflict_map` + `_fold_candidates` per wave, but `_bundle_bases` is called with
  `runnable` (a subset of `wave`), and threading a precomputed dict adds a parameter to it
  for no behaviour gain. Recomputing keeps `_bundle_bases`'s signature unchanged; the extra
  cost is one parse of the wave's briefs.

## Tests

### New: `template/tests/test_flow_merged_prereq_dependency_base.py`

Uses `tests/test_flow_merged_prereq_on_line.py`'s class as a helper object (loaded by
path, as that file loads `StackFoldGit`), so the real-git fixture, the `gh` stub and the
stubbed leaves are not copied. Drives `flow._drive_and_act`.

- `test_a_merge_after_the_first_fold_builds_a_depends_on_merged_dependent` — criterion (1),
  `Depends on (merged): P`.
- `test_a_merge_after_the_first_fold_builds_a_plain_depends_on_dependent` — criterion (1),
  plain `Depends on: P`, P not in the batch (#647).
  Both assert: W COMPLETE; the line lacks P's merge commit and P's head (so this is the
  #655 situation); no `issue_D held` line; D COMPLETE; D's stack base is
  `<line>-bD` (its own base, not the line); that base's tip has P's merge commit and
  W's branch.
- `test_an_unmerged_depends_on_merged_prerequisite_still_holds_the_dependent` and
  `test_an_unmerged_plain_depends_on_prerequisite_still_holds_the_dependent` — criterion
  (2): P's PR stays OPEN, D is PLANNED, never built, one `issue_D held … issue_P … not
  merged into main` line.

### Changed: `template/tests/test_flow_merged_prereq_on_line.py` (criterion (4))

Brief's line numbers are on `fcae4aa`; mapping to current names:

| `fcae4aa` | test | before | after |
|---|---|---|---|
| `:1-12` | module docstring | rule stated for every dependent | rule stated for a dependent built on the line; own-base case pointed at the new file |
| `:202` | `test_a_merge_after_the_line_was_started_holds_a_depends_on_merged_dependent` | D `Depends on: W` + `(merged): P` (own base after #727), held | same edges + `Stacks on: W` (a seam → on the line), held; same assertions |
| `:212` | `…_holds_a_plain_depends_on_dependent` | D `Depends on: W, P`, held | + `Stacks on: W`, held; same assertions |
| `:241` | `test_an_unreadable_merge_commit_holds_the_dependent` | own-base D, held | + `Stacks on: W`, held; same assertions |
| `:249` | `test_a_checkout_that_cannot_be_fetched_holds_the_dependent` | own-base D, held | + `Stacks on: W`, held; same assertions |
| `:293` | `test_the_way_out_is_to_delete_the_line_then_re_run` | own-base D, held twice then built | + `Stacks on: W`; held twice then built on the line; same assertions |
| `:222`, `:230` | merge/squash already on the line | unchanged (as #727 left them) | unchanged |
| `:257` | target with no line | unchanged | unchanged |
| `:269` | carried P | unchanged (#728's) | unchanged |

Mechanism: new constant `ON_LINE = "- **Stacks on:** W\n"` (`test_…_on_line.py:55`) and
`_wd(edge, *, on_line=False)` (`:176-179`); the five held cases pass `on_line=True`
(`:227`, `:237`, `:267`, `:275`, `:321`). `Stacks on: W` is kept *beside* `Depends on: W`
(not instead of it) because the way-out test's re-run needs W carried, and the carry
(`_carry_finished`) only starts from a plain `Depends on` edge. `Stacks on` is a legacy
field `_closure_members` treats as a seam (`flow.py:946-949`), the same seam #727's own
suite uses (`test_flow_dependency_scoped_bases.py:422`). No assertion was removed or
weakened; only the brief of D gained one line.

Why the re-pointing is required, not optional: with the fix, an own-base D in those five
cases is no longer held (that is exactly criterion (1)), so their held assertions would go
red. Re-pointing keeps each held assertion meaningful by giving it a D that is still built
on the line.

## Red → green (project runner: `engine/scripts/run-verify.sh`)

Run with `PDCA_BUNDLE=results/issue_729 PDCA_WORKTREE=<worktree>`:

- green leg: new file 4/4 OK; `test_flow_merged_prereq_on_line` 9/9 OK.
- red leg (production hunks reverted): new file FAILED (failures=2) — both criterion (1)
  cases, at `assertNotIn("does not have that merge", …)`, with the exact #655 message
  `flow: issue_D held — prerequisite(s) issue_P (merge commit …): their PR merged into main
  (org/repo), but the line issue_D would build on, pdca-integration/main-r… at …, does not
  have that merge`. The two (2) guards stay green; the line-based suite stays 9/9 green
  (criterion (3) guard holds before and after).
- verdict line: `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`.

Full suite (`engine/scripts/run-suite.sh`, both roots, patch applied): root suite 24 tests OK; driver suite 2593 tests OK (skipped=2). Verdict: `PDCA-EVIDENCE: root suite OK, driver suite OK`.

## Refute-your-own-test

- **(a) Genuine red?** Yes. `run-verify.sh`'s red leg reverts only `flow.py`/`merged.py`
  and the two (1) tests fail with the #655 hold message quoted above.
- **(b) Production path?** Yes. The tests call `flow._drive_and_act`, which runs the real
  `_runnable`, `_base_plans`/`_closure_members`, `_bundle_bases` and
  `integrate.build_bundle_base` + `integrate.fold` against real git repos. Only the
  build/sign-off leaves, `_publish_bundle` (replaced by the fixture's real-git publish) and
  `gh` (answered from a dict) are stubbed — none of them is code this patch changes.
- **(c) Fixture includes the fault?** Yes. P's PR is really merged into origin's `main`
  (`fx._merge_pr`) *after* the first real fold, so the line genuinely lacks the merge; the
  test asserts that (`assertFalse(_ancestor(merge_oid, line))`) before asserting D is
  built, and asserts D's own base really contains the merge commit.

## Commit-readiness

The target has no formatter config and no commit hooks (no `.pre-commit-config.yaml`, no
`core.hooksPath`; CI runs docs lint and render checks only). CONTRIBUTING.md asks only for a
DCO `Signed-off-by`, which publish adds. New lines stay within the file's 100-column style;
the three lines over 100 in `flow.py` (`:211`, `:3003`, `:3198`) are pre-existing.

## Housekeeping

The full-suite log was written to `/tmp/issue729-suite.log` (outside the harness roots, by
mistake; harmless, not cleaned up per the no-`rm` rule).
