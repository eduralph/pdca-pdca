# Build notes — issue 593, iteration 3 (stack-mode-append-only-fold-real-base-prs)

Target: eduralph/pdca-harness @ main, base commit `24c7f83`. Worktree:
`/home/eddie/pdca/pdca-harness.pdca-wt-l0`. Line numbers below are in the patched tree
unless marked "base".

## What I started from, and why

The iteration-2 sign-off accepted the design (real-base PRs, append-only fold of the real
PR commits, hold dependents of an unpublished bundle) and asked to "rebuild only to fix"
three items. So I applied the previous attempt's `iteration-v2/patch.diff` to the clean
worktree as the starting point and changed only what the carry-forward names. This is
the one place I read past `brief.md`: the carry-forward block points at `iteration-v2/`
and says to keep that design, and re-deriving it from scratch risked drifting from what
was accepted. I did not read the v2 build-notes, review or SUMMARY files.

## Carry-forward item 1 — a failed re-publish with a surviving record (the regression)

Problem: v2 decided "unpublished" only from `publish.json` on disk. An iterate keeps
`publish.json` (`state.py:116` `DOWNSTREAM_OF_BRIEF` on base does not list it), so a
bundle published by an earlier run, then iterated, rebuilt and accepted, whose
re-publish fails this run, still had its old record. The fold merged the old, rejected
branch and its dependents built on it.

Fix, as the carry-forward prescribes (hold on a failure THIS run, in addition to the
on-disk check):

- `flow._publish_bundle` now returns whether publish completed (rc 0):
  `template/src/pdca_harness/flow.py:641-656` (base `flow.py:641-653`, returned None).
- `_drive_and_act` keeps a per-run `publish_failed` set (`flow.py:1686-1690`), filled in
  the publish loop when the texts are not ready (`flow.py:1841-1845`, base `:1817-1820`)
  or publish returns non-zero / raises (`flow.py:1838-1840`, base `:1816`).
- At the fold, the hold set is `integrate.unpublished(accepted, failed=publish_failed)`
  (`flow.py:1861-1875`). It is computed over the cumulative `accepted` list and prints
  once per newly held bundle. The fold gets `accepted` minus the held names
  (`flow.py:1884-1886`), so a held bundle's old branch never enters the line, and
  `_runnable` (`flow.py:663-700`, base `:660-690`) skips its in-batch dependents; the skip
  cascades through the existing not-COMPLETE rule.
- `integrate.unpublished` gained `failed=` (`template/src/pdca_harness/integrate.py:137-151`).
  A name in `failed` only counts for a bundle the fold would carry at all (patch + usable
  target), so a no-target bundle is still never held (brief (iv), test 14).
- Still outside dry-run only (`flow.py:1869`), per brief (iv).

A publish that returns 1 after `gh pr create` fails (publish.py:396-400 on base: branch
pushed and record written, but no PR) is also held. That is deliberate: no PR was
opened, so the stack the human merges would not contain it, and building dependents on
it would break the "merge bottom-up lands everything" invariant.

Alternative rejected: archive `publish.json` on iterate (add it to
`state.DOWNSTREAM_OF_BRIEF`, a 1-line change in base `state.py:116-148`). It removes the cause
for the on-disk check, but (1) it does not cover the `gh pr create`-failed case above,
where the record is fresh but there is no PR; (2) it changes three other readers of the
record after every iterate: `cli._publish_flag` (base `cli.py:1042-1061`) would show
`[unpublished]` for a bundle whose PR is still open, `merged.is_merged` (base
`merged.py:42-45`) would return False for an iterated bundle whose PR already merged
(blocking out-of-batch `Depends on (merged)` dependents), and the merge-mode guard's
`_batch_branch_producer` (base `publish.py:687-698`) would stop seeing that branch; (3) the
carry-forward asked for the flow-level hold. So I kept the record and track failures in
the run instead.

New tests (both fail under v2's on-disk-only rule — I checked by patching
`integrate.unpublished` to ignore `failed` and running them: both FAIL):
- `test_a_failed_re_publish_is_held_though_an_earlier_record_survives`
  (`template/tests/test_flow_slice.py:1544`): REAL fold against a real bare origin with
  `receive.denyNonFastForwards`; RP's old branch is on origin and its old `publish.json`
  in the bundle; RP's re-publish fails. Asserts RD (on RP) is skipped naming RP, RJ (on
  RI) completes, no STOPPING, RP's old branch was not re-pushed, RI's commit is in the
  line and the old RP commit is NOT.
- `test_texts_not_ready_hold_the_bundle_though_an_earlier_record_survives`
  (`test_flow_slice.py:1424`): same shape for the draft/T4-failed path, with a fold spy.

I refactored the v2 end-to-end test's git setup into `_real_origin` / `_accept_wave` /
`_push_branch` helpers (`test_flow_slice.py:1464-1521`) so both real-git flow tests share
it; the v2 test's assertions are unchanged.

## Carry-forward item 2 — the diff-shrink docs overclaimed

If the base moves between a wave-0 publish and the run's first fold, the first fold
starts the line from the newer base and merges the prerequisite (cut from the older
base) onto it. That joining merge commit never reaches the base, so after the
prerequisite's PR merges, a single-predecessor dependent has two merge bases with the
base (the moved base tip and the prerequisite's tip). With git 2.53, `git diff
main...B` then showed `a.txt b.txt` (the predecessor's file plus B's); after "Update
branch" (merge main into B) it showed `b.txt` only. The fold design is unchanged, as
asked.

Narrowed wording (same "Update branch" remedy, now covering both cases — same-wave
siblings and the moved base):
- `template/src/pdca_harness/integrate.py:15-25` (module docstring; carry-forward said
  :17-19 of the v2 post-image)
- `template/src/pdca_harness/publish.py:247-262`, the narrowed sentence at `:252-258`
  (carry-forward said :252-254)
- `docs/07-crosscutting.md:648-656` (carry-forward said :649)
- `template/PCDA/quality-cycle/09-parallel-lanes.md:69`
- `template/PCDA/quality-cycle/08-glossary.md:292-294` (its "shows its prerequisites'
  changes until they merge" implied an unconditional shrink; now points at 09 for the two
  cases)
- `publish.py:322` dry-run label: v2's "(cumulative diff vs base until its predecessors
  merge)" also overclaimed; now "(cumulative diff vs base)".
- `publish.py:710-715` `_warn_if_squash_only` docstring: "until its branch is rebuilt" →
  "until its branch is updated from the base" (updating also clears it).

New test `test_a_chain_on_a_moved_base_keeps_a_second_merge_base_until_updated`
(`template/tests/test_integrate_stack_bases.py:374`): publish A, move origin's main,
fold, cut B from the line, merge A with `--no-ff`; asserts `merge-base --all main B` is
exactly {moved main, A's tip}, the three-dot diff shows more than `b.txt`, and after
"Update branch" it is `b.txt` only. I kept the "more than b.txt" assertion loose rather
than pinning `a.txt`: which of two merge bases git picks is not specified.

## Carry-forward item 3 — optional cleanups (both done)

- One definition shared by the fold and the hold: `integrate._fold_candidates`
  (`integrate.py:126-134`) returns `(bundle, repo, base, published_ref)` for every bundle
  the fold carries; `fold` (`integrate.py:265-292`) and `unpublished`
  (`integrate.py:137-151`) both read it. `test_an_unpublished_bundle_stops_the_fold_before_any_git_step`
  now also asserts `unpublished()` names exactly the bundle the fold refuses.
  `_published_ref` also now returns None for a `publish.json` that is valid JSON but not an
  object (`integrate.py:115-117`) instead of raising inside the flow.
- `git merge-base --is-ancestor` rc: 0 = already in the line (skip), 1 = merge it, any
  other code (128) raises `IntegrationError` as a failed git step, never an overlap
  (`integrate.py:389-398`). Test: `test_a_failing_ancestry_check_is_a_git_step_failure_not_an_overlap`
  (`test_integrate_stack_bases.py:328`) injects rc 128 through a spy on `integrate._git`
  and asserts the message says "exited 128" / "git step failed", not "does not merge
  cleanly", and nothing was pushed. On v2 this fell through to the merge and succeeded.

I did not reclassify a failing `git merge` (it is still reported as an overlap, as in v2):
the sign-off said "rebuild only to fix these", and the run stops either way.

## The carried v2 design (unchanged this round), for reference

- (i) PR base: `publish.py:264-265` (base `:258-259`) — a recorded stack-base opens `--base
  <target base>` on own-repo too; a legacy `Stacks on:` parent keeps its branch base only
  without a stack-base; merge mode is untouched (`wave_mode != "merge"`).
- (ii)/(iii) fold: `integrate.py:214-372` (base `:132-230`) — resolves each bundle's
  published ref (`_published_ref`, `:105-123`; `"stacked"` records use their own
  `<remote>/<branch>`), fetches every needed remote with `--prune`
  (`_prepare_worktree`, `:410-430`, base `:233-246`), starts fresh / continues / auto per
  `folded_this_run`, refuses a moved line, merges with `--no-ff --signoff`
  (`_merge_published`, `:375-407`), pushes `--force` only when fresh.
- flow passes `folded_this_run=dict(folded_tips)` and records `integrate.pushed_tip(wt)`
  right after the fold, before any re-gate (`flow.py:1884-1891`, base `:1844`).
- docs/comments: `docs/05-check.md:813-819`, `docs/07-crosscutting.md:642-662`,
  `template/pdca.toml.jinja:115-123` and `:180-182`, `cli.py:1058-1061`, `sweep.py:16-19`.

## Verification (all through the project's runners, each under `timeout`)

- C4 gate, the project's red→green runner:
  `PDCA_BUNDLE=results/issue_593 PDCA_WORKTREE=<worktree> ./engine/scripts/run-verify.sh`
  → `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`. Green leg: all four
  touched test modules OK (29 + 105 + 14 + 22 tests). Red leg (production hunks
  reverted): test_flow_adopt_split 29 OK (spy change only); test_flow_slice 6 failures
  (all StackModeFlow, incl. both new hold tests); test_integrate 1 failure (overlap
  message); test_integrate_stack_bases 15 failures + 5 errors. The 5 errors are tests
  that pass `folded_this_run=` (TypeError on base, accepted by the brief for test 3) or
  call `integrate.unpublished` (AttributeError on base); no module failed to import.
  The gate's trap restored the full patch (checked with `git apply -R --check`).
- Offline driver suite (`cd template && PYTHONPATH=src python3 -m unittest discover -s
  tests`): 2244 tests OK, 2 skipped.
- Root suite (`python3 -m tests.run_root_suite`, what render-check.yml runs, copier from
  the instance venv): 24 executed, 0 skipped, OK.
- Docs gate (`./engine/scripts/run-docs-check.sh`, mirrors docs-check.yml): lint clean,
  site render + link audit clean.
- Commit-readiness: the target has no formatter or pre-commit hook (no
  `.pre-commit-config.yaml`, no `core.hooksPath`, no installed hooks; CONTRIBUTING.md asks
  only for a DCO sign-off, which publish adds with `commit -s`). No linter is installed
  here, so I ran an AST check for unused imports over every changed .py file: none. Added
  lines stay within each file's existing maximum line length.
- `patch.diff` applies to `24c7f83` (checked by reverse-applying it to the worktree).
  Size 115 KB (instance `patch_kb = 125`).

## Refuting my own test

- (a) Genuine red? Yes. The C4 gate reverted the production hunks and the bundle's tests
  went red (counts above). Separately, both new hold tests FAIL when
  `integrate.unpublished` is patched back to v2's on-disk-only rule, so they bind the
  iteration-3 regression, not only the base defect.
- (b) Production path? Yes. The tests drive `integrate.fold`, `integrate.unpublished`,
  `publish.publish` (one real non-dry publish against real git:
  `test_a_wave_bundle_publishes_against_the_real_base`) and `flow.flow_ids` (the real
  wave loop, publish loop, hold, `_runnable` and fold). Stand-ins are limited to what is
  not under test: the model leaves, `publish.draft_texts`, `publish.publish` in the flow
  tests (replaced by a function that pushes a branch the way publish does), and
  `flow._drive_wave` in the two real-git flow tests (accepts each bundle with a real
  patch).
- (c) Fixture includes the fault? Yes. Origins run with `receive.denyNonFastForwards true`;
  the re-publish test puts the real old branch on origin and the real stale record in the
  bundle (the element v2 mishandled); the base-moved test pushes a real commit to main
  between publish and fold; the gone-branch tests delete the branch on origin while the
  primary keeps a stale tracking ref. The one injected fault is rc 128, through a spy on
  `integrate._git`, because a real git rc 128 at exactly that call is not reproducible on
  demand; the code that interprets the rc is the production code.

## Limits and what sign-off still owns

- The live-host check the brief lists under External dependencies (disposable GitHub
  repo: siblings A and C, B on both; merge with merge commits; "Update branch"; a merged
  prerequisite whose branch was deleted, through the real `gh pr view`) is still owed at
  sign-off. Plan registered it, so it is not a missing dependency.
- Out of scope this round, per the carry-forward: holding a `Conflicts with` partner of a
  held bundle. A later bundle that conflicts with a held one builds without it.
- (iv) itself (hold vs stop) stays NEEDS-HUMAN for sign-off, per the brief's plan-review
  response.
- The edits to `template/PCDA/quality-cycle/08-glossary.md` and `09-parallel-lanes.md`
  (the vendored model spec) are NEEDS-HUMAN at Check by INTEGRATION §4.

## Housekeeping

- I wrote one log outside the harness roots by mistake: `/tmp/claude-v2-baseline.log`
  (output of the v2-baseline test run). It is harmless; I did not delete it because
  cleanup is the harness's job.
- The C4 run's log is at `<worktree>/.cache/c4-verify.log` (git-ignored, inside the
  worktree).
- Nothing was pushed and no PR was opened.
