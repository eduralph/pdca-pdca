# Build notes — issue 616 / stack-resume-carries-unmerged-prereqs (iteration 2)

Target: `eduralph/pdca-harness` @ `main`. Written in the cycle worktree
`$PDCA_WORKTREE` = `/home/eddie/pdca/pdca-harness.pdca-wt`, HEAD `f594d8e`: the brief's
verified `origin/main` (`c67a14d`) with #531, #590 and #591 folded on top (bundle
`stack-base` = `pdca-integration/main`). Every `path:line` below is on that tree **with
the patch applied** unless it says "base". The brief's line numbers were taken before
#591 and had moved, as its ordering note warned; I re-resolved them all.

## What this iteration changes, against the iteration-1 sign-off

The sign-off kept the core fix (one fold of earlier runs' unmerged prerequisites before
wave 0, onto the run's own per-batch line) and asked for five fixes. I started from the
iteration-1 patch (it applied cleanly to `f594d8e`) and made these changes.

1. **Only `Depends on` starts a line; `Stacks on` keeps its pre-fix behaviour.**
   `_prereqs_to_carry` (`template/src/pdca_harness/flow.py:756-847`) now reads
   `brief.depends_on` and `brief.stacks_on` separately (`flow.py:828-829`) instead of
   `waves.declared_deps`. A target gets a line only if some plain `Depends on` edge on it
   has a prerequisite to carry (`lined`, `flow.py:834`). A `Stacks on` edge on a target
   with no line is skipped before it is judged (`flow.py:838-839`), so a run whose only
   out-of-batch edges are `Stacks on` folds nothing, re-points nothing and never asks
   `gh`: the bundle builds on the parent's branch (`worktree.py:96-98`) and, on an
   own-repo setup, opens its PR against it (`publish.py:236-238`, `:282`), as before.
   Test: `test_a_stacks_on_edge_keeps_building_on_its_parents_branch`
   (`template/tests/test_flow_resume_stack_prereqs.py:559`).

   **Judgment call for the human: the mixed case.** If a `Depends on` gives a target a
   line, every wave-0 bundle of that target is pointed at the line (the brief's `U` rule).
   A bundle `W` of that target with an out-of-batch `Stacks on: Q` would then build on a
   line without `Q` — worse than before the fix, where it built on `fix/Q`. So on a target
   that has a line, a `Stacks on` parent is judged like a `Depends on` one: carried onto
   the line, or `W` held if it cannot be (`flow.py:837-846`). `W` then builds on a base
   with `Q`, but its PR targets the real base instead of `fix/Q` (a recorded stack base
   wins, `publish.py:236-238`, `:282`). That is how a later-wave `Stacks on` bundle has
   behaved since #593. Test:
   `test_a_line_a_depends_on_starts_carries_a_stacks_on_parent_of_its_target` (`:582`).
   The alternative I did not take is in "Alternatives" below.

2. **Holds are per (dependent, prerequisite) pair.** `_prereqs_to_carry` returns, per
   held prerequisite, exactly the same-target dependents held on its account
   (`flow.py:843-846`). `_drive_and_act` turns them into `held_pairs` (`flow.py:2050`,
   `:2112`) and `_runnable` checks the pair, not the name (`flow.py:718-719`, new
   parameter `flow.py:683`). I put back the base `not out_of_batch` guard on the #593
   name hold (`flow.py:716-717`, as base `flow.py:712-713`), which iteration 1 had
   removed. A dependent of another target is never in a pair, so it builds as before,
   and the hold line lists exactly the held dependents (`flow.py:2111-2124`). Test:
   `test_a_hold_is_per_dependent_another_targets_dependent_still_builds` (`:413`) — `P`
   unpublished, `D` on `main` held and named alone, `D2` on `dev` built.

3. **A missing `gh` reads as "not merged".** `merged.is_merged` now wraps the `gh` call
   in `try/except OSError` (`template/src/pdca_harness/merged.py:51-55`), the same shape
   as `merged_head` (`merged.py:79-83`), and prints the same "could not read PR state …
   treating as not merged" line. I also changed `if rec else None` to
   `if isinstance(rec, dict) else None` (`merged.py:48`), as `merged_head` has it
   (`merged.py:76`): a `publish.json` that is valid JSON but not an object would
   otherwise raise `AttributeError`. That path is reachable now only in a dry run (outside
   one, `integrate.unpublished` screens such a record out first) and has no test of its
   own. Test for the guard: `test_no_gh_reads_as_not_merged_and_never_crashes_the_run`
   (`:522`).

4. **A possibly stale `publish.json` holds its dependents.** New
   `_record_predates_signoff` (`flow.py:850-865`): a record whose mtime is older than
   `SUMMARY.md` (where the accept is recorded) is "stale". `verdict` checks it after the
   no-branch check and before `merged.is_merged` (`flow.py:811-816`), so a stale record
   holds its dependents whatever its old PR's state, and costs no `gh` call. The hold
   line names the prerequisite, says why, and tells the operator to re-publish
   (`flow.py:2114-2124`). Not in a dry run, like every other hold. Test:
   `test_a_record_older_than_the_latest_sign_off_holds_its_dependents` (`:436`), which
   builds the real scenario: attempt 1 published, then archived to `iteration-v1/`,
   rebuilt, re-accepted, and the re-publish never happened (`_iterated`, `:202`).

   Why `SUMMARY.md`: it is the human's own example, and it is the boundary that matters.
   Publish refuses a bundle that is not COMPLETE (`publish.py:159-163`) and writes
   `publish.json` only after its push (`publish.py:419-431`), so the publish of the
   accepted attempt is always newer than the accept. An iterate does not archive
   `publish.json` (it is not in `state.DOWNSTREAM_OF_BRIEF`, `state.py:116-148`), which
   is how an old record survives. The codebase already trusts this file's mtime to tell
   a fresh record from an old one (`_publish_bundle`, `flow.py:656-665`). The comparison
   is strict (`<`), so equal timestamps count as fresh.

   Known false positive (it errs toward holding, which the sign-off asked for: "possibly
   stale"): a sign-off recorded again after the publish (`pdca signoff <id> --accept`
   does not refuse a COMPLETE bundle, `cli.py:1447-1474`), or a `git pull` that updates
   only `SUMMARY.md`. A fresh clone does not trigger it: git writes `SUMMARY.md` before
   `publish.json` (index order). The remedy the message gives — re-publish — clears it.

5. **Mid-run split children noted as out of scope** in `_prereqs_to_carry`'s docstring
   (`flow.py:795-798`).

Kept from iteration 1, unchanged in behaviour: the pre-wave fold
(`flow.py:2108-2135`), the shared fold step `_fold_onto_line` (`flow.py:868-906`, the
base in-run block `flow.py:2059-2097` moved out), and `carried +` in every later fold
(`flow.py:2274-2281`), which keeps the line through a wave that accepts nothing of its
target. Docstrings: `_runnable` (`flow.py:684-703`), `_drive_and_act`
(`flow.py:2005-2011`). Docs: the `"stack"` bullet, `docs/07-crosscutting.md:677-691`,
now also covers the stale-record hold and `Stacks on`.

## The test

`template/tests/test_flow_resume_stack_prereqs.py` (copied flat into the bundle too), 14
cases. Real git: a bare `origin`, a primary checkout and a scratch "human" clone, the
`StackFoldGit` shape (`test_integrate_stack_bases.py:115-138`), copied rather than
imported (no test module in `template/tests` imports another). It drives the production
`flow._drive_and_act` with `batch=` as a re-issued `pdca flow <ids>` does. Stand-ins:
`flow._drive_wave` (build/Check/sign-off: records each bundle's `stack-base`, its tip,
the line's commit on origin at that moment, and the ref Do's worktree branches off via
the production `worktree._target`; then makes the bundle COMPLETE),
`flow._publish_bundle` (cuts the branch where publish cuts it, using the production
`read_stack_base_tip` / `_stack_base_branch`, pushes it, then writes `publish.json`),
`publish.draft_texts`, and the `gh` binary (a fake `subprocess` namespace inside
`merged` only, so `is_merged` / `merged_head` run as shipped and `integrate` keeps real
git).

Fixture change from iteration 1: an earlier run's bundle is now accepted **before** its
`publish.json` is written, the order the cycle uses (`_earlier`, `:185`). Iteration 1
wrote the record first, which the new stale rule would have read as stale.

Red without the fix (8): the criterion (`:313`), line-outlives-a-wave (`:365`), (a)
no branch (`:394`), per-pair hold (`:413`), stale record (`:436`), (d) failing pre-wave
fold (`:499`), no `gh` (`:522`), `Stacks on` parent carried on a line (`:582`). Green on
both sides by design (6): (b) merged (`:458`), (c) no patch (`:475`),
`Depends on (merged)` (`:541`), `Stacks on` unchanged (`:559`), other target / no
brief (`:608`), no out-of-batch prerequisite (`:632`).

### Refuting my own test

- **(a) Genuine red? Yes.** The project's C4 gate (`engine/scripts/run-verify.sh`, run
  with `PDCA_BUNDLE` / `PDCA_WORKTREE` set) reverted the production hunks (`flow.py`,
  `merged.py`) and re-ran: `Ran 14 tests … FAILED (failures=8)`, all assertion failures,
  no import errors. Green leg `Ran 14 … OK`. Verdict: `PDCA-EVIDENCE: C4 PASS — red
  without the fix, green with it`. On top of that, five mutations, each run through the
  same script and each reverted afterwards (`git diff` then matched `patch.diff` byte for
  byte):
  - `Stacks on` also starts a line (`lined` without `not stacks`) → only
    `test_a_stacks_on_edge_keeps_building_on_its_parents_branch` fails.
  - holds keyed by prerequisite name (iteration 1's behaviour) → only
    `test_a_hold_is_per_dependent_another_targets_dependent_still_builds` fails.
  - stale check disabled → only
    `test_a_record_older_than_the_latest_sign_off_holds_its_dependents` fails.
  - `except OSError` removed from `is_merged` → only
    `test_no_gh_reads_as_not_merged_and_never_crashes_the_run` errors, with
    `FileNotFoundError: … 'gh'` out of the run.
  - `Stacks on` parents never carried → only
    `test_a_line_a_depends_on_starts_carries_a_stacks_on_parent_of_its_target` fails
    ("no Q under issue_D").
- **(b) Production path? Yes.** `_drive_and_act`, `_prereqs_to_carry`,
  `_record_predates_signoff`, `_fold_onto_line`, `_runnable`, `_point_at_integration`,
  `integrate.fold` (real git against the bare origin), `merged.is_merged` /
  `merged_head`, `publish.read_stack_base` / `_stack_base_branch` and `worktree._target`
  all run unmocked. Only the build/Check/sign-off leaf, text drafting, the publisher leaf
  and the `gh` binary are stand-ins; none of them is code this fix changes.
- **(c) Fixture includes the fault? Yes.** `P` is really outside the drive set (only in
  `batch`), really COMPLETE (a recorded sign-off), its branch really pushed to the bare
  origin, its PR reported OPEN. In the stale case the earlier attempt is really archived
  and re-accepted, and the record really predates the new sign-off. In the no-`gh` case
  the call raises `FileNotFoundError`, which is what `subprocess.run` raises for a
  missing executable. The cross-target case has a real `dev` branch on origin. In (d)
  `fix/P` is really deleted on origin, with a stale tracking ref for the fold's
  `--prune` to drop.

## Alternatives ruled out (with cost)

- **Mixed case: keep `W` off the line at wave 0** (it keeps building on `fix/Q` with its
  PR against `fix/Q`), instead of carrying `Q` onto the line. Sketch: `_prereqs_to_carry`
  also returns `keep_off` = same-target bundles whose only out-of-batch edges are
  carryable `Stacks on` ones (about 6 lines), `_drive_and_act` passes it to the wave-0
  `_point_at_integration` call (about 4 lines), which clears those bundles' stack bases
  instead of pointing them (about 3 lines). It does not replace the pull-along: a `W` in
  a later wave has in-batch prerequisites that only the line carries, so it must be on
  the line, and then `Q` must be too. So it is about 13 lines **on top of** the current
  rule, with `W` behaving differently in wave 0 and in later waves. I chose the single
  rule. If the human prefers `W`'s PR to keep targeting `fix/Q` in wave 0, this is the
  change to make.
- **Stale signal from `patch.diff`'s mtime** instead of `SUMMARY.md`'s. Same size (one
  path differs). It catches the same iterate case (a rebuild always writes a fresh
  `patch.diff`) and has a slightly different false positive (a `patch.diff` touched
  after publish instead of a `SUMMARY.md` touched after publish). I followed the
  sign-off's own example and the publish-after-accept rule above.
- **A content check** (record a hash of `patch.diff` in `publish.json` and compare it):
  two write sites in publish (`publish.py:419-431`, `:539-547`, about 4 lines), a reader
  (about 6 lines), and old records without the field would still need the mtime rule — two
  rules instead of one, plus a change to publish, which is not in this brief's scope.
- **Merge check inside `_runnable`** instead of the pre-wave classifier (kept from
  iteration 1): `test_flow_slice.py` pins that `_runnable` asks `gh` nothing for a plain
  out-of-batch `Depends on`, and `_runnable` runs per wave, so it would ask `gh` once per
  wave per edge instead of once per prerequisite per run.

## Things the human should know at sign-off

- **The mixed `Depends on` / `Stacks on` decision above** is the one place where a
  `Stacks on` bundle's PR target changes (to the real base): only on a target where an
  out-of-batch `Depends on` started a line in the same run. Documented in
  `docs/07-crosscutting.md:688-691`.
- **Re-publishing an iterated bundle loses its PR URL** (existing publish behaviour, not
  changed here): the old draft PR is still open, so `gh pr create` fails after the push
  and `publish.json` is rewritten with `pr_url: ""` (`publish.py:402-431`). After that,
  `merged.is_merged` can never say "merged" for it, so later runs keep carrying it, and
  once its branch is deleted after the merge the pre-wave fold stops the run (case (d)'s
  message: restore or re-publish the branch). Loud, never a wrong base, but a rough edge
  for the stale-record remedy. Worth its own issue.
- **Not covered:** a split child adopted mid-run (noted in the docstring, as asked); a
  `Stacks on` bundle in a later wave of a target with no out-of-batch `Depends on` line
  is pointed at the in-run line without its parent, as before this fix (the trigger
  stays `Depends on` only, as asked).
- **The line is created even if every dependent that needed it is then skipped for
  another reason** (e.g. it also waits on an unmerged `Depends on (merged)`). The other
  wave-0 bundles of that target still build on the line and their PRs show the carried
  changes until they merge. This follows the brief's one-fold-point rule.
- `--no-publish` and merge mode are unchanged.

## Checks run (all through the project's scripts in `pdca-pdca/engine/scripts/`)

- C4 `run-verify.sh`: PASS (above). Worktree restored afterwards; `git diff` matches
  `patch.diff` byte for byte.
- T3 `run-suite.sh`: root suite 24 tests OK, driver suite 2339 tests OK (2 skipped).
- T2 `run-docs-check.sh`: docs lint clean, 22 pages rendered, link audit clean.
- C5 `run-prod-path.py`: the added test imports `pdca_harness`.
- Commit-readiness: the target has no formatter, linter config or commit hooks (no
  `.pre-commit-config.yaml`, `core.hooksPath` unset, only `*.sample` hooks; CI runs the
  docs checks and the render suite, `.github/workflows/docs-check.yml:33-36`,
  `render-check.yml:43-46`, both green above). `git diff --check` is clean; no added line
  is over 100 characters (the test file's longest is 100; `flow.py`'s longest line, 106,
  is pre-existing).

## Housekeeping

I wrote one scratch log inside the bundle, `results/issue_616/.c4-run.log` (output of a
C4 run, nothing else). I did not delete it; cleanup is the harness's. The worktree index
has the new test as intent-to-add (`git add -N`), so `git diff` shows it; nothing else is
staged.
