# Build notes — issue 646 (stack-reissue-carries-clean-finished-prereqs), re-plan iteration 5

Target: `eduralph/pdca-harness`, built in `$PDCA_WORKTREE` on `pdca-integration/main` @ `12405dc`
(the bundle's `stack-base`), as the brief says. "Base" line numbers below are on `12405dc`;
"new" line numbers are in the patched tree.

## Result

- `patch.diff` — 8 files, +722 / −77, 60.8 KB (v4 was 149 KB). Production part: `flow.py`
  +214/−48, `integrate.py` +70/−20, `merged.py` +25, `publish.py` +6/−4, `drift.py` +2/−1,
  docs +25. Test: 373 lines / 19 KB (ceiling: ~700 lines / 30 KB). 12 criterion tests + 1
  `fold(skipped=…)` unit test, exactly the closed list.
- C4 gate (`engine/scripts/run-verify.sh`, run with `PDCA_BUNDLE`/`PDCA_WORKTREE` set):
  `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`. Green leg: 13/13 new tests
  and 46/46 `test_integrate_stack_bases` pass. Red leg (production hunks reverted, tests
  kept): 10 of 13 new tests FAIL on assertions (no import errors); the 3 that stay green are
  the "unchanged behaviour" guards (6a, 6b, 7a), which must pass both ways.
- T3 (`engine/scripts/run-suite.sh`): root suite 24/24 OK, driver suite 2338 OK (2 skipped).
- T2 docs: `lint_docs.py` OK, `render_site.py --check` link audit OK.
- C5 (`run-prod-path.py`): the added test imports `pdca_harness`.
- The target repo has no formatter or pre-commit config (no `.pre-commit-config.yaml`, no
  ruff/black config); CI runs only the docs lint/render and the render suites. I checked:
  no added line over 99 chars, `py_compile` clean, `git diff --check` clean.

## What changed and why (one rule, one path)

The brief fixes the policy: carry only the clean case; anything else holds only that id's
plain-`Depends on` dependents, with one stderr line, and the run goes on. I built exactly
that and nothing for the known limits.

1. **Shared fold path** — `_fold_lines` (`flow.py:752`, new). ONE `integrate.fold` under ONE
   `ExitStack` passed as `locks`, then the tip read (`pushed_tip`), then the optional re-gate
   with `hold_lock=False`, all inside the stack. This is the body of the old in-run block
   (base `flow.py:2059-2097`) moved into a function. The in-run block now calls it
   (new `flow.py:2241-2263`) and keeps its result handling: IntegrationError ⇒ print + `break`,
   red re-gate ⇒ print + `break`, same messages. The re-gate still stops at the first red
   target (`next(...)` replaces `any(...)`), so the number of re-gates run is unchanged.
   One deliberate change in the in-run block: `integ = {...}` became `integ.update(...)`
   (new `flow.py:2256`). Today the two are equivalent, because `accepted` is cumulative and
   every fold re-folds every earlier target. With a carry they are not: a target only the
   carry folded must keep its line when an in-run fold touches other targets only.
2. **Finished named ids** — `_finished_named` (`flow.py:782`): ids in `batch` that are
   COMPLETE and not in the drive set, de-duplicated (`500`/`issue_500` normalised the way
   `integrate.batch_key` does), in requested order.
3. **The carry** — `_carry_finished` (`flow.py:828`), called once before the wave loop when
   publishing in stack mode (new `flow.py:2100-2107`; inserted before base `flow.py:1926`).
   - Carryable = `integrate._fold_candidates(finished)` (the ONE definition, base
     `integrate.py:158`).
   - Trigger (criterion 6): only targets of carryable finished ids that some drive-set
     bundle names in its plain `Depends on` (`brief.depends_on`, not `declared_deps`, so
     `Stacks on` / `Depends on (merged)` never trigger). Every carryable finished id of a
     triggered target is judged, in requested order.
   - Dry-run (stub publisher): prints one line plus `integrate.fold(..., dry_run=True)`'s
     plan, asks no host, holds nothing, seeds nothing.
   - State check — `_finished_head` (`flow.py:795`): PR OPEN, or MERGED with the head on
     the base or the line, and the head resolves locally. Head = `headRefOid` from one
     `gh pr view --json state,headRefOid` (`merged.pr_state`, `merged.py:96`, new; the
     missing-`gh` guard copied from `merged.merged_head`, base `merged.py:73-80`).
     No `publish.json` branch or no `pr_url` ⇒ not clean.
   - Trust check (criterion 5) — `integrate.carry_view` (`integrate.py:185`) fetches the
     target as a fold does and reads origin's line tip `T`; `integrate.foreign_commit`
     (`integrate.py:196`) is one `git rev-list --no-merges T --not <base> <state-clean
     heads>`. Any output ⇒ the whole target is held with the "delete the line" hint, as
     the brief says ((5) wins over (4)).
   - Fold: ONE `_fold_lines` call per target with the state-clean ids, `skipped={}`, and
     `folded_this_run={target: T}` when the line exists (continue, unforced, refused if
     origin moved) or `{}` when it does not (fresh).
   - Result handling: per-id `skipped` entries, a whole-target IntegrationError, or a red
     re-gate all land in the same `why` map. Every id in `why` is added to `held` and gets
     ONE stderr line: reason + one of the three prescribed hints (`_CARRY_HINTS`,
     `flow.py:819`). The hint is picked by kind ("open" / "edge" / "line"); there is no
     per-reason code path. A target is seeded into `integ` / `folded_tips` only when at
     least one id was carried and the re-gate is not red.
4. **Holding dependents** — `_runnable` (base `flow.py:712-713`, new `flow.py:708`,
   `:717-720`): a dep in `held` is unmet when it is in the batch (unchanged, #593) or when it
   is out of batch and named in the dependent's plain `Depends on` (#646). A `Stacks on`
   edge to a held finished id is not held, per the brief. The wave loop passes
   `held_unpushed | held_finished` (base `flow.py:1932`, new `flow.py:2114`). Carried ids
   never enter `accepted`, so `integrate.unpublished(accepted, pushed=…)` never reports them.
5. **`integrate.fold(skipped=…)`** (signature base `integrate.py:243-247`, new `:275`;
   docstring new `:334-341`; loop base `:394-395`, new `:435-441`): a per-bundle
   `IntegrationError` from `_merge_published` (including `_gone_branch`) is recorded and the
   loop moves on (`_merge` already aborts a failed merge, base `integrate.py:548`); a target
   whose every bundle was skipped pushes nothing and gets no entry. `skipped=None` raises as
   before. Everything else (lock, worktree, moved line, push, the up-front "no published
   branch" refusal) still raises.
6. **`_fetch`** (new `integrate.py:598`): the fetch half of `_prepare_worktree` (base
   `integrate.py:552-573`) moved into its own function so the carry can read origin's line
   and the PR heads before it folds, without creating the integration worktree outside the
   integration lock. `_prepare_worktree` (new `:618`) calls it; behaviour unchanged.
7. **Wording** — fold's moved-line refusal (base `integrate.py:385-389`, new `:422-428`) now
   says "the tip this run last pushed (or checked, for a carried line)" (the brief allowed
   this; no behaviour change, no test pins it). `integrate.py` module docstring (base
   `:30-34`, new `:34-37`) names the carried-line exception. `publish.py:345`, `:696`
   (new `:696-698`), `:726` (new `:727-728`): "#616" dropped, "re-drive it in a new run"
   kept, and the docstring/message say a re-issue continues the line only when it carries
   a finished prerequisite. `drift.py:58-61` (new `:61-62`) likewise. `docs/07-crosscutting.md`
   gets a second paragraph in the stack-mode bullet (new `:679-702`) describing the carry,
   the hold rule, the untrusted-line advice and every known limit from the brief.
8. **Existing assertions** — `test_integrate_stack_bases.py` base `:834`, `:844`, `:852`,
   `:1012` (new `:834-836`, `:846-847`, `:855`, `:1015`): "#616" replaced by the new wording
   ("re-drive it in a new run", "only when it carries a finished prerequisite").

## Alternatives ruled out (with the cost)

- **One `fold` per id** — forbidden by the brief: `integ_lock` reopens the `.lock` file
  (base `integrate.py:213`), so a second call under a shared stack blocks on the process's
  own flock.
- **Refactor `merged.merged_head` onto the new reader** — `merged_head` is silent on
  unparseable output but prints on a `gh` failure (base `merged.py:80-87`). A shared helper
  would need a three-way result or would make it print on bad JSON. The separate
  `pr_state` costs 23 lines (`merged.py` +25 incl. 2 docstring lines) and leaves
  `merged_head` byte-identical.
- **Judge state/trust inside `fold`, under the lock** — would add PR states and heads to
  `fold`'s parameters and per-id verdicts to its result; the brief allows ONE new keyword.
  The race it would close is already closed: in continue mode the fold re-reads origin's
  line under the lock and refuses if it is not `T` (base `integrate.py:380-389`).
- **Reuse `_prepare_worktree` for the pre-fold read** — it creates the integration worktree,
  and doing that outside `integ_lock` defeats the lock's purpose (the sweeper). Extracting
  `_fetch` costs a moved docstring: the region shows −14/+18 lines in the diff
  (hunks `-552,14 +598,10` and `+616,8`).
- **Unforced first push when the line is absent** — the fold force-pushes every fresh start
  (base `integrate.py:401`). Changing that also changes the in-run fresh fold, which the
  brief says must stay "exactly as today" when `skipped` is None; a second keyword is not
  allowed. So in criterion (1) (no line on origin) the carry's push carries `--force`. It
  creates the branch and replaces nothing. Criterion (2) (line exists) and the in-run fold
  of (3) are asserted to push without `--force`.
- **Subclass `StackFoldGit`** — would inherit its 31 `test_*` methods into this module and
  run them a second time. The fixture is loaded by path (`importlib`) and used as a helper
  object (`sb.StackFoldGit()`; `setUp`/`tearDown` called explicitly). Loading by path works
  under both `python -m unittest tests.x` (C4) and `discover -s tests` (T3). Nothing is copied.

## Refute-your-own-test (forced)

- **(a) Genuine red? Yes.** The C4 gate reverted every production hunk (`git apply -R
  --exclude=tests/* --exclude=template/tests/*`) and re-ran the test: 10/13 FAIL, all on
  assertions. Each red is the defect itself: (1)(2)(3) `D`'s stack base is `''` (cleared) instead
  of the line; (4a)(4b)(4c)(5)(8) the dependent that must be held was built (`'issue_D'
  unexpectedly found in seen`); (7b) the carry's dry-run plan is absent; the unit test's
  `skipped` parameter is absent (`assertIn` on the signature, so an assertion, not a
  TypeError). I reordered (4b) so its first failing assertion is the hold, not the `gh` call.
- **(b) Production path? Yes.** The tests call the real `flow._drive_and_act` with
  `batch=[all requested ids]` and the drive set without the finished ids — the exact shape
  `flow_ids` passes (base `flow.py:2360-2363`). Real code under test: `_carry_finished`,
  `_finished_head`, `_runnable`, `_point_at_integration`, `_fold_lines`, `integrate.fold`,
  `carry_view`, `foreign_commit`, `merged.pr_state`, real git against a bare origin.
  Stubbed only: `_drive_wave` (build + sign-off leaves; it records what each bundle was
  built on), `_publish_bundle` (replaced by the fixture's `_publish`, which cuts the branch
  from the recorded tip, pushes it, and writes `publish.json`), `publish.draft_texts`, and
  `gh` (a stub in front of `subprocess.run` that answers `gh pr view` and passes every git
  call through). For (8), `gates.run_integration` is stubbed to go red exactly when the
  integration tree's HEAD contains P's head (decided by git). Outside the shipped test, I
  also ran one scratch end-to-end check through the real `flow.flow_ids(["P","D","E"])`
  (file in the worktree's git-ignored `.cache/`, not shipped): P is skipped as terminal,
  carried before wave 0, and D and E both build on a line holding P.
- **(c) Fixture includes the fault? Yes.** P really is COMPLETE, requested, and absent from
  the drive set; its branch is really on origin. (2) has a real earlier line holding P,
  with `receive.denyNonFastForwards=true` on origin. (4a) the PR reads CLOSED; (4b) `gh`
  raises `FileNotFoundError` (an `OSError`) at `subprocess.run`; (4c) P and Q really
  conflict (both add `c.txt`), and Q is requested first, so name order would pick the
  wrong one; (5) a real rejected commit sits on origin's line; (8) the re-gate is really red
  on the carried line and green on the replacement.

Mutation checks I ran (each reverted afterwards; the final tree is byte-identical to
`patch.diff`):
- carry folds fresh instead of continuing ⇒ (2) goes red (origin refuses the forced
  rebuild, P is held, D is never built). This first showed up as a `KeyError`, so I added the
  `_built()` helper; it now fails as an assertion that prints the run's stderr.
- finished ids tried in name order instead of requested order ⇒ (4c) goes red.
- in-run `integ.update` turned back into `integ = {...}` ⇒ **no test goes red.** It only
  matters with two targets: the carry seeds target T1, wave 0 holds only bundles of T2, and
  a wave-1 bundle of T1 depends on P. With a replace, that wave-1 bundle would lose T1's
  carried line and build on the plain base. The brief's closed test list has no two-target
  case, so this is a **review item**, not covered by a test.

## Things the reviewer and sign-off should know

- **Criterion (1) and `--force`.** See "unforced first push" above. In (1) the line does not
  exist, so the carry's fresh fold pushes `--force` to create it. The brief's own mechanism
  ("leave the target out, so `fold` starts fresh") produces this. Nothing is replaced. If
  sign-off reads "a force-push in (1)-(3) is a regression" literally, this is the one place
  it differs.
- **Trust check runs before the lock.** `carry_view` fetches and reads `T` without
  `integ_lock`. Continue mode re-checks `T` under the lock (refuse ⇒ every id of the target
  held, run goes on). Fresh mode (no line at check time) would force-push over a line
  another run created in the gap. That is today's one-run rule for a first fold.
- **`foreign_commit` uses `--no-merges`.** A merge commit that carries its own content
  changes is not inspected. The brief puts "a line an outside party rewrote beyond what
  (5) detects" out of scope.
- **"(5) wins".** When the line is untrusted, every carryable id of that target gets the
  untrusted-line reason and hint, even one whose PR is also closed. After the line is
  deleted and the run re-issued, the closed PR is reported on its own. Two steps, one
  path each.
- **Base risk (from the brief's Ordering note).** Built and verified on
  `pdca-integration/main` (`12405dc` = `origin/main` `c67a14d` + #531, #590, #591). The PR
  targets `main`. Until those merge, it carries their commits; if PR #639 (#591) is
  reworked before merging, this bundle must be rebuilt. For sign-off to accept explicitly.
- **Housekeeping slip.** One of my shell commands redirected output to `/tmp/.unused` and
  then removed it. That file was outside the roots I was given; it is gone and nothing
  depended on it. All other scratch output (gate logs, the end-to-end script) is in the
  worktree's git-ignored `.cache/`.

No external dependency was missing: git, python3 3.14 and the docs deps
(`markdown-it-py`, `PyYAML`) were present, and the tests need no network and no real `gh`.
