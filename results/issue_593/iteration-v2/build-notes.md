# Build notes — issue 593 / stack-mode-append-only-fold-real-base-prs (iteration 2)

Target: `eduralph/pdca-harness` @ `main` = `24c7f83`. All edits were made in the per-cycle
worktree `$PDCA_WORKTREE` = `/home/eddie/pdca/pdca-harness.pdca-wt-l1`. Line numbers below are
`base:line` on `24c7f83` and `new:line` in the patched tree. I read only `brief.md` (not
`iteration-v1/`, not the old test file in the bundle, which this build overwrote).

## What changed, per criterion

**(i) Every wave PR targets the real base.** `publish.py` base:258-259 → new:260-262.
`pr_base` is now `base` whenever the bundle has a recorded `stack-base`
(`wave_stacked = cfg.wave_mode != "merge" and bool(_read_stack_base(d))`, new:261). The branch
is still cut from `origin/<stack-base>` (`checkout_base`, unchanged, new:246). A legacy
`Stacks on:` parent with no stack-base keeps `--base <parent branch>` on own-repo. The fork path
gives `base` as before. The record still says `mode = "stacked-pr"` (base:383, unchanged), with
`base: "main"`. The dry-run label for an own-repo wave PR now reads "cumulative diff vs base until
its predecessors merge" (new:317-320); the legacy and fork labels are byte-identical.
Comments rewritten at new:243-259. `_warn_if_squash_only`'s docstring (base:701-706 →
new:707-713) said rebase-merge is fine, which contradicts (viii); fixed.
`cli._publish_flag` comment only (base:1058-1059 → new:1058-1061).

**(ii) The fold merges the real PR commits.** `integrate.fold` (base:132-230 → new:190-347).
The re-apply loop (base:211-223) is replaced by `_merge_published` (new:350-374): resolve the
published ref, skip it if it is already an ancestor of the line, else
`git merge --no-ff --no-edit --signoff -m "pdca-integrate: <bundle>" <sha>` (new:369). DCO kept:
every merge commit carries `Signed-off-by` (`tests/test_integrate.py:176-185` still passes).
`_published_ref` (new:99-117) reads `publish.json` through `publish._publish_record`, the same
reader `publish._stack_base_branch` uses (base:632-647 via :590-598): `"stacked"` → the record's
own `base` ref and its remote, never `origin/<branch>`; anything else → `origin/<branch>`.
`_prepare_worktree` (base:232-246 → new:377-397) now fetches the base remote, `origin` and every
`"stacked"` record's remote, each with `--prune`, and a failed fetch raises.

**(iii) Append-only within one run.** New keyword `folded_this_run` (new:192). The start mode is
picked at new:280-281: not listed → `fresh` (start at `<base_remote>/<base>`, `push --force`);
listed → `continue` (origin's line must equal the listed SHA, else `IntegrationError` naming the
branch, both SHAs and #591, new:316-325; then push without force); `None` → `auto` (continue if
origin has the line, else fresh; new:326). Push at new:332-346, with a hint on how to fix a refused push
(delete the old line / allow force on `pdca-integration/*`) for a fresh push. Return shape is
unchanged. `flow` keeps `folded_tips` (new flow.py:1687-1689), passes a copy at the one call
site (new:1868-1870), and records `integrate.pushed_tip(wt)` (new integrate.py:88-96,
`git rev-parse HEAD` in the worktree) straight after `fold` returns, before the re-gate
(new flow.py:1871-1875). Dry-run stores `None`.

**(iv) A partial failure holds only its dependents.** `integrate.unpublished` (new:120-126)
uses the same test as `_targeted` (patched, usable target) plus "no published ref". `flow`
calls it in the stack-mode fold branch, outside dry-run, for the wave just accepted
(new flow.py:1848-1859), adds the names to `unpublished` (new:1684), leaves them out of the fold
(new:1869), and passes the set to `_runnable` (new:1737). `_runnable` (base:660-691 →
new:660-697) treats an in-batch prerequisite in that set as not ready (new:690-691), so the
existing skip line names it and the skip cascades as before. A no-target bundle is not counted.
`fold` itself fails closed outside dry-run: a targeted, patched bundle with no published ref
raises before any git step (new:243-260). In dry-run a missing record is planned as
`origin/<publish._branch_name(...)>` (new:249-251). Published branch gone after the pruning
fetch: skipped if `merged.is_merged(cfg, id)` (as `merge.py:200` calls it), else
`IntegrationError` naming the bundle and the ref (new:355-363).

**(v)/(viii) Docs.** `integrate.py` module docstring (base:1-19 → new:1-27);
`09-parallel-lanes.md:57,59,69`; `08-glossary.md:284-294`; `docs/07-crosscutting.md:642-658`;
`docs/05-check.md:813-816`; `pdca.toml.jinja:115-123` and `:180-182`. They say: every PR targets
the real base; merge bottom-up with a merge commit, not squash or rebase; a chain dependent
shrinks once its prerequisite merges, a sibling dependent may need "Update branch"; the line
only grows within a run and restarts at each run's first fold; a failed publish holds only its
dependents. I also fixed the same "folds rebuild from the base every call" claim in
`sweep.py:18-19` (the docstring twin of `pdca.toml.jinja:176`), since it is now false.

**(vi) Unchanged:** grouping and sorted lock order, `_point_at_integration`, the lock spanning
fold + re-gate, dry-run shelling nothing, stack-base stamp / `$PDCA_VERIFY_BASE`, `merge.py`,
`publish._merge_base_refusal`. No hunk touches them; their tests pass.

## Decisions and what I ruled out

- **`--no-ff` merges, not fast-forwards.** Dropping `--no-ff` is a one-token change. With
  fast-forward, a fold of one bundle onto an untouched base creates no commit at all, so the
  `pdca-integrate: <bundle>` marker and the fold's own signed-off commit disappear in that case
  and `test_fold_commits_carry_a_dco_signoff` would be checking publish's commit instead. Cost
  of `--no-ff`: one extra signed merge commit per prerequisite in each dependent PR's commit
  list. Both variants pass the chain and sibling cases (I traced both).
- **Merge mode left exactly as it was.** The unconditioned rule
  (`wave_stacked = bool(_read_stack_base(d))`, one condition shorter) would stop
  `_merge_base_refusal` route 1 (base:675-678) from refusing an own-repo bundle with a stale
  stack-base under `wave_mode = "merge"`. The brief scopes (i) to stack mode and lists merge mode
  as unchanged, so I kept the `cfg.wave_mode != "merge"` guard.
- **"Unpublished" read from `publish.json`, not from publish return codes.** Tracking return
  codes means making `_publish_bundle` (base:641-653) return its rc and adding the texts-failed
  branch: about 8 changed lines, and a second definition of "unpublished" that can disagree with
  the fold's own fail-closed check (for example, rc 0 but no record would reach the fold and stop
  the run). `integrate.unpublished` is 7 lines and is the fold's own predicate.
- **Hold computed in the fold branch, not in the publish loop.** Placing it after the publish
  loop (the brief's region :1800-1822) printed "left out of the integration fold" for
  final-wave bundles, where no fold runs. In the fold branch (base region :1835-1847) it runs
  only when a fold follows: stack mode, non-final wave, not dry-run. I left the publish loop
  untouched. Hunk regions stay clear of 582/589/597's listed regions.
- **Fetch failures now raise** (base:239-241 ignored them). Without a good fetch the fold can't
  check the line SHA or see the branches; the brief counts a failed git step as a stop.
- **`flow` passes `dict(folded_tips)`, a copy.** Passing the live dict would let the next
  wave's update change what an earlier call received.
- **A listed target with value `None` outside dry-run raises** (the listed value isn't the
  origin SHA). That is fail-closed for a caller bug; `flow` never does it.

## Tests

New module `template/tests/test_integrate_stack_bases.py` (also copied into the bundle). It
imports only modules (`integrate`, `publish`, `signoff`). Brief case → test:

1 → `test_a_later_fold_appends_to_the_line_and_carries_the_pr_commits` (:187);
2 → `test_a_continuing_fold_pushes_without_force` (:204) and
`test_a_listed_target_continues_this_runs_tip_without_force` (:214, also checks a branch in the
line is not merged twice); 3 → `test_a_runs_first_fold_starts_fresh_over_an_earlier_runs_line`
(:230); 4 → `test_a_line_another_run_moved_is_refused` (:240); 5 →
`test_an_onto_branch_record_merges_that_remotes_branch_not_origins` (:255); 6 → `:293`, `:301`;
7 → `:310`; 8 → `:325`; 9 → `:333`; 10 → `StackPublishDryRun` (:372-429) plus a real, non-dry
publish of a wave bundle checking `publish.json` (`:350`); 15 →
`test_an_unpublished_bundle_is_planned_as_its_would_be_branch` (:455). Extra: dry-run
start/continue plan at fold level (:464) and a `"stacked"` record's plan (:474).

Flow cases in `template/tests/test_flow_slice.py`, class `StackModeFlow` (:1280): 11 → `:1356`;
12 → `:1373`; 13 → `:1399` (extended with a third-wave bundle to pin the cascade); 14 → `:1422`.
Extra: `:1433`, a three-wave run with the real fold against a real origin that refuses
non-fast-forwards.

Existing tests updated to the new contract: `test_integrate.py` `_bundle` now publishes a branch
(`_publish`, :163), the `aa` bundle in the lock-order test is published (:248), the overlap test
asserts the merge-conflict message and that nothing was pushed (:298), the lock test asserts the
lock message (:227). Fold spies take `**kwargs`: `test_flow_slice.py:1127`,
`test_flow_adopt_split.py:378`. `test_publish_flag_marks_stacked_pr` (:1263) now uses a
new-shape record (`↑main`) and checks a `new-pr` record shows no cue.

## Evidence

- C4, through the project's gate script
  (`PDCA_BUNDLE=… PDCA_WORKTREE=… ./engine/scripts/run-verify.sh`), on the final patch:
  green leg 29 + 103 + 14 + 19 tests OK; red leg (production hunks reverted)
  `test_flow_slice` FAILED (failures=4), `test_integrate` FAILED (failures=1),
  `test_integrate_stack_bases` FAILED (failures=13, errors=4), `test_flow_adopt_split` OK.
  Verdict: `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`.
- T3 (`./engine/scripts/run-suite.sh`): root suite 24 tests OK (copier present, so render and
  update-compat ran); driver suite 2239 tests OK (skipped=2).
- T2 (`./engine/scripts/run-docs-check.sh`): docs lint clean, site render + link audit clean.
- `git diff --check` clean; the patch applies to `24c7f83` (checked with a scratch index).
  No formatter or commit hook is configured in the target repo; publish adds the DCO sign-off.

## Refuting my own tests

**(a) Genuine red? Yes.** The C4 red leg reverts every production hunk and re-runs all four
touched modules. Red reasons are the defect itself, for example:
`test_a_wave_bundle_publishes_against_the_real_base`: `('stacked-pr', 'pdca-integration/main')
!= ('stacked-pr', 'main')`; `test_an_unpublished_bundle_holds_only_its_dependents`: the fold got
`['issue_HI', 'issue_HU']`; `test_a_later_fold_appends…` and the three-wave flow case: A's own
PR commit is not in the line. One nuance I found and wrote into the test comment: on the old
code the rebuilt line can come out byte-identical to T1 when both folds run in the same second,
so the old force-push is not always refused, but the "PR commit in the line" assertion fails
either way. The 4 errors are tests that pass `folded_this_run`, which the old `fold` rejects with
`TypeError`; the brief accepts that for case 3, and it applies equally to the other
keyword-passing cases. No module failed to import on the red leg.

**(b) Production path? Yes.** The tests call `integrate.fold`, `publish.publish` and
`flow.flow_ids` themselves. Stand-ins are only at boundaries that are not under test and would
otherwise need `gh` or a model: `publish.publish` / `publish.draft_texts` in the non-dry flow
cases (no PR, no publisher leaf), `integrate.fold` in cases 11 and 13 (it returns a real git
worktree so the real `pushed_tip` runs), `merged.is_merged` in the gone-branch cases (it calls
`gh`), and `flow._drive_wave` in the extra three-wave case only. The stub builder's placeholder
`patch.diff` can't be applied to a real checkout, so a full stub drive against real git fails
at Check's worktree rebuild. `_runnable`, `integrate.unpublished`, the publish loop and (in
case 12, case 14 and the extra case) the fold are all the real code.

**(c) Fixture includes the fault? Yes.** A real bare origin with
`receive.denyNonFastForwards true`; real pushed PR branches; a second remote whose `feat` must
win over a same-named decoy on origin; a branch deleted on origin while the primary still holds
a stale tracking ref (`fetch.prune false` pinned, so the fold's own `--prune` is what is
tested); a foreign force-push over the line (the #591 case); real `--no-ff` merges of the PR
branches into `main` for the diff cases; an unpublished bundle and a no-target bundle in real
flow runs.

## For the human at sign-off

- **Live-host check (owed at sign-off, per the brief; not a Do dependency).** On a disposable
  GitHub repo: put A and C in wave 0 and B on both; run the flow; merge A and C with merge
  commits; look at B's "Files changed"; use "Update branch"; merge B. Also check that a
  published prerequisite whose merged PR branch was deleted is skipped through the real
  `gh pr view` path (`merged.is_merged`). Offline tests can't cover GitHub's own diff view.
- The patch edits the vendored model spec (`template/PCDA/quality-cycle/09-parallel-lanes.md`,
  `08-glossary.md`), which is NEEDS-HUMAN at Check under INTEGRATION §4.
- (iv) is the run-keeps-going policy the brief marks NEEDS-HUMAN for sign-off to confirm.
- Behaviour changes a reader might not expect: a failed `git fetch` in the fold now stops the
  run (it was ignored before); the integration line now holds merge commits named
  `pdca-integrate: <bundle>` instead of re-applied commits with that name.
- Housekeeping: scratch logs are in the worktree's git-ignored `.cache/` (`pdca593-*.log`,
  `pdca593-base.idx`). I also wrote one log to `/tmp/claude-baseline-593.log` early on, outside
  the harness roots, by mistake; it is a baseline test log and I left it for the harness to
  reclaim.
