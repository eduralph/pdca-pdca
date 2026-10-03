# Brief — issue 593 / stack-mode-append-only-fold-real-base-prs

> The Plan artifact (docs 02 §PLAN). Do reads ONLY this file.
> Iteration 2. The previous attempt is archived in `iteration-v1/`; its core direction was
> judged sound, and this brief settles the design questions Check raised (see the last section).

- **Slug:** stack-mode-append-only-fold-real-base-prs
- **Defect:** Two defects in `[driver].wave_mode = "stack"` (found by review of
  getwyrd/wyrd-pdca#262; related #463, #591, #185). Together they stop a multi-wave run, and so
  a whole milestone, from completing in one `pdca flow` as a PR stack the human merges afterwards.
  **1. Middle-wave PRs break within the same run.** `integrate.fold` rebuilds
  `pdca-integration/<base>` from `<base_remote>/<base>` on every call (`checkout -B branch
  <base_remote>/<base>`, `template/src/pdca_harness/integrate.py:209-210`). It then re-applies
  every accepted `patch.diff` as a NEW `pdca-integrate: <bundle>` commit (`integrate.py:211-223`)
  and force-pushes (`integrate.py:224-228`). An own-repo wave-1 bundle's PR is opened `--base`
  that branch (`publish.py:258-259`). After wave 1 is accepted, the next fold rebuilds the
  branch with waves 0..1 as new commits. The wave-1 PR's base now holds its own change as a
  different commit, so the PR goes empty, conflicting or DCO-red before anyone can merge it.
  Any batch with three or more waves hits this in one run.
  **2. Wave 1+ PRs never reach the target.** For an own-repo target, a wave>0 PR's `--base` is
  the integration branch (`publish.py:258-259`). Nothing retargets those PRs and nothing opens
  an integration → target PR, so merging them bottom-up merges into the integration branch;
  only wave 0 lands on the target. (The fork path already opens against the real base,
  `publish.py:248-259`. But its diff never shrinks, because the fold's commits are not the PR
  branches' commits. #185 documents that cost.)
- **Success criterion:** With the patch, under `wave_mode = "stack"`:
  (i) **Every wave PR targets the real base.** A wave>0 bundle (one with a recorded integration
  `stack-base`, `publish.py:601-605`) still cuts its branch from `origin/<integration branch>`
  (`publish.py:246`), so it carries its predecessors. But its PR is opened `--base <its target
  base>` (e.g. `--base main`), on the own-repo path too, and `publish.json` records that base.
  A hand-declared legacy `Stacks on:` parent keeps its PR-branch base (`--base fix/PARENT-…`;
  `tests/test_publish_slice.py:478-484` and `:1142-1160` keep passing), but only when the bundle
  has **no** recorded `stack-base`. When both are present the `stack-base` rule wins, as it
  already does for the branch choice (`publish._stack_base_branch`, `publish.py:639-641`). The
  fork path is unchanged (`tests/test_publish_slice.py:468-476`). A wave>0 PR still records
  `mode = "stacked-pr"` (`publish.py:383`), so `cli._publish_flag` keeps its `↑<base>` cue
  (now `↑main`). Only that function's comment (`cli.py:1058-1061`) changes. What the cue
  means changes, and that is accepted on purpose: it still appears only on stacked PRs
  (`new-pr` records show none), so it still says "part of a stack, merge bottom-up". It no
  longer names the branch the PR merges into ahead of the target, because there isn't one any
  more. Merge order comes from the briefs' `Depends on` / the wave order, not from the cue.
  The comment says this.
  (ii) **The fold carries the real PR commits.** After `integrate.fold`, every accepted, patched
  bundle's published branch tip is an **ancestor** of the integration branch tip: the
  predecessors' own commits (same SHAs), merged rather than re-applied. Merge commits carry a DCO
  `Signed-off-by` trailer (keeps `tests/test_integrate.py:176-185`'s intent). The published
  branch is resolved from `publish.json`. For a `"stacked-pr"` / `"new-pr"` record it is
  `origin/<branch>`. For a `"stacked"` record (a bundle published with the brief's
  `Onto branch:` field, `publish.py:440-456`, `:502-511`) it is the record's own `base` ref
  (`<remote>/<branch>`), fetched from that remote. The fold must never look up a same-named
  branch on `origin` for it. Merging the whole existing PR branch, other people's commits
  included, onto the line is accepted: later waves then carry that PR's commits until it merges.
  (iii) **Within one run the integration line is append-only, and only this run's.**
  `integrate.fold` gains a keyword-only parameter
  `folded_this_run: Mapping[tuple[str, str], str | None] | None = None`, mapping each
  `(repo, base)` target this run has already folded to the tip SHA its last fold pushed (`None`
  in a dry-run, where nothing is pushed).
  - A target **listed** continues from its pushed tip. If `origin/<integration branch>` after
    fetch is not that SHA, the fold raises `IntegrationError` naming the branch, both SHAs and
    the likely cause (another run on the same base, #591). It never builds on a line another
    run pushed.
  - A target **not listed** starts fresh from `<base_remote>/<base>` and force-pushes. This is
    the run's first fold of that target, and it replaces any previous run's line.
  - `None` (direct callers, existing tests) continues the integration branch if origin has
    it, else starts from the base. A dry-run cannot look at origin (it shells nothing,
    `tests/test_integrate.py:80-88`), so a `None` dry-run prints a third line: "continue
    `<branch>` if origin has it, else start fresh from `<base_remote>/<base>`".

  Every fold of a listed target is a fast-forward pushed **without** `--force`, so it succeeds
  against an origin with `receive.denyNonFastForwards = true`. A branch already in the line
  (an ancestor of its tip) is not merged again. The `fold` return shape is unchanged
  (`{(repo, base): (branch, worktree)}`). `flow` reads each target's pushed tip with
  `git -C <worktree> rev-parse HEAD` right after `fold` returns, before any re-gate. It keeps a
  per-run map, separate from `integ` and filled in dry-run too (value `None`), and passes it at
  the one call site (`flow.py:1844`). So the run's first fold gets `{}`, and every later fold
  gets every target folded so far. A new run's first fold that meets an old line on an origin
  refusing force-pushes is an `IntegrationError`. The docs say to delete the old integration
  branch or to allow force-push on `pdca-integration/*`.
  (iv) **A partial failure holds only what depends on it; it does not end the run.** An
  accepted bundle with a non-empty `patch.diff` and a usable target (`publish._resolve_target`
  gives a repo and base, the same test `integrate._targeted` uses at `integrate.py:121-129`)
  but no published branch (its publish texts
  failed draft/T4, `flow.py:1817-1822`, or publish failed, `flow.py:651-653`) is left out of
  the fold. Every bundle that declares it as a prerequisite, directly or through another
  bundle, is skipped with the existing "skipped — prerequisite(s) not ready (…)" line, which
  names the unpublished bundle. Mirror `flow._runnable` (`flow.py:660-690`): an unpublished
  in-batch prerequisite counts as not ready, and the skip cascades as it already does. Bundles
  that do not depend on it are still built, signed off, published and folded. A patched
  bundle with **no** target is not "unpublished": it publishes with rc 0 and no
  `publish.json` (`publish.py:178-184`, flow passes `skip_if_no_target=True`), `fold` already
  drops it, and its dependents keep building as `_runnable` lets them today. The hold applies
  only outside dry-run, because the stubbed publisher records no branch (`publish.py:311-324`
  returns before writing `publish.json`). `fold` itself stays fail-closed **outside
  dry-run**: called with a targeted, patched bundle that has no published branch, it raises
  `IntegrationError` naming it, before any git step. **Under `dry_run=True` that check is
  skipped**: a bundle with no `publish.json` is planned as merging `origin/<branch>`, where
  `<branch>` is `publish._branch_name(cfg, d, slug)` (`publish.py:568-576`, slug from
  `_resolve_target`), the branch a real publish would have pushed. So the existing bare-bundle
  dry-run tests (`tests/test_integrate.py:80-102`) keep passing, and (vii)'s merge lines
  always have a ref to name.
  Three things still **stop** the run, because they are integrity failures rather than partial
  ones: a branch that does not merge cleanly onto the line (an undeclared cross-wave overlap;
  `IntegrationError`, the pushed line left as it was, `tests/test_integrate.py:274-281`
  intent); the concurrent-run mismatch in (iii); and a git step failing.
  **Published branch gone** (its ref does not resolve after the fold's fetch; that fetch must
  prune, since `_prepare_worktree` on `main` fetches without `--prune`, `integrate.py:239-241`,
  and a stale tracking ref would hide a deleted branch): if the bundle
  reads as merged (`merged.is_merged(cfg, id)`, as `merge.py` uses it), it is skipped, since
  its work is in the base. Otherwise `IntegrationError` naming the bundle and the ref actually
  looked up.
  (v) **Diff shrink, stated truthfully.** For a single-predecessor chain (A in wave 0, B
  depending only on A), once A's PR is merged into the base with a merge commit, B's
  three-dot diff against the base (`git diff <base>...<B branch>`) holds only B's change. When
  a dependent sits on two or more same-wave siblings, the fold's merge commit joining them
  never reaches the base. After the siblings merge, the dependent has several merge bases, and
  one sibling's change can stay visible in its diff. The remedy is updating the dependent's
  branch from the base (GitHub's "Update branch", or merging the base into it), after which
  its diff is its own change only. The docs say exactly this, not an unconditional "shrinks".
  (vi) **Unchanged:** per-target grouping and sorted lock order (`integrate.py:163-179`,
  `tests/test_integrate.py:89-104, 214-243`); the per-target stack-base routing
  (`flow._point_at_integration`, `tests/test_integrate.py:284-330`); the lock covering fold +
  re-gate (`integrate.py:192-207`); dry-run touching nothing (`integrate.py:182-191`,
  `tests/test_integrate.py:80-88`), though its printed plan changes (see vii); the stack-base
  stamp and `$PDCA_VERIFY_BASE` (`tests/test_verify_base.py`); merge mode (`merge.py`,
  `publish._merge_base_refusal` `publish.py:650-686`).
  (vii) **Dry-run shows the real plan.** A dry-run fold prints, per target: either "start
  `<branch>` fresh from `<base_remote>/<base>`" with a force-push, or "continue `<branch>`
  from this run's tip" with an unforced push, or (only when `folded_this_run` is `None`) the
  "continue if origin has it, else start fresh" line from (iii); then one merge line per
  bundle, naming the branch ref it would merge (from `publish.json`, else the `_branch_name`
  fallback in (iv)). A dry-run flow of three or more waves therefore prints "start"
  for the first fold and "continue" for later ones.
  (viii) **The text agrees.** The module docstring (`integrate.py:1-19`), the publish
  comments (`publish.py:242-257`), the `_publish_flag` comment (`cli.py:1058-1061`), and the
  user docs that call stacked PRs `--base`d on the integration branch or the fork diff
  never-shrinking: `template/PCDA/quality-cycle/09-parallel-lanes.md:57,69`,
  `docs/07-crosscutting.md:642-647`, `template/pdca.toml.jinja:115-119` and `:176` (the sweep
  rationale "folds rebuild from the base every call"),
  `template/PCDA/quality-cycle/08-glossary.md:290-292`, `docs/05-check.md:813-816`. They say:
  every PR targets the real base; merge the stack bottom-up with a merge commit (not squash or
  rebase, which rewrite the SHAs dependents share); the diff behaviour in (v); folds continue
  the run's line, restarted at each run's first fold; and a partial failure holds its
  dependents rather than stopping the run (iv).
  The whole `template/tests` suite stays green. Existing fold tests are updated to give each
  bundle a published branch where the new contract needs one, and spies on `fold` are updated
  to accept the new keyword.
- **Falsifiability:** RED is reachable offline on the base toolchain (stdlib Python ≥ 3.11 +
  git); no network and no `gh` are needed. `tests/test_integrate.py:105-165` (`FoldGit`)
  already folds against a real bare `origin` + primary checkout. On `main`:
  - (ii)/(iii): publish A's branch, fold `[A]`, cut B's branch from the tip T1, publish it,
    fold `[A, B]` with no keyword. T1 and A's branch commit are not ancestors of the new tip,
    and with `receive.denyNonFastForwards true` on origin the second fold's force-push is
    refused.
  - The no-force rule (spy on the push arguments): `main` passes `--force` on every fold.
  - (v) chain shrink: after A's branch merges into origin's `main` with `--no-ff`, B (cut from
    the old fold's `pdca-integrate:` copy) still shows A's file in `main...B`.
  - (i): the dry-run publish helper (`tests/test_publish_slice.py:453-466`) with
    `publish.write_stack_base(d, "pdca-integration/main")` prints `--base pdca-integration/main`.
  - (iii)/(vii) flow-level: a spy on `integrate.fold` taking `**kwargs` sees no
    `folded_this_run` at all.
  - (iv) flow-level: a run with an unpublished wave-0 bundle stops at the fold
    ("did not integrate … STOPPING"), so an independent wave-1 bundle is never built.
- **Invariant to restore:** In stack mode, within one run, no integration-line push rewrites a
  commit that an open PR's base or head depends on, and every PR the harness opens targets a branch that reaches the real
  target when merged. So merging the PR stack bottom-up lands every wave on the target with no
  step outside the PRs. And within one run only that run's work enters its integration line.
  Source: internal project rule (Tier C), the stack-mode promise in
  `template/PCDA/quality-cycle/09-parallel-lanes.md:57,69` ("a dependent batch completes in one
  run as a reviewable PR stack the human merges bottom-up") and `docs/07-crosscutting.md:642-647`.
  Limits, stated so sign-off can check it: the run's first fold of a target replaces an earlier
  run's line (cross-run resume is #616), and publish's own `--force-with-lease` re-push of a
  rebuilt bundle's PR branch (`publish.py:289-296`, #108) is outside this invariant; both stay
  as they are;
  DCO on every commit a PR carries (#405, `integrate.py:218-222`). Self-test: neither half alone
  satisfies it. Retargeting PRs without folding the real branches leaves dependents with diffs
  that never shrink and lines rebuilt under them. Append-only folding without retargeting
  leaves wave 1+ merging into the integration branch.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Ordering note:** No `Depends on` / `Conflicts with`. This batch (582, 589, 593, 597) runs as
  ONE wave, because this very bug is in this instance's driver. #616 (filed at this Plan: a
  re-issued flow builds dependents of an earlier run's unmerged work on a base missing it)
  depends on 593 and is NOT in this batch; it runs after 593 lands. File overlap: 593 owns
  `integrate.py` and `publish.py`. It also edits `flow.py` at the fold call (`:1838-1860`), the
  publish loop's unpublished set (`:1800-1822`) and `_runnable` (`:660-690`). 597 edits
  `flow.py` only in the intake (`:1104-1108`, `:1925-1940`, `:2064-2104`) and 589 only
  `cli._flow` (`cli.py:637-660`), away from 593's `cli.py:1058-1061` comment. 582 edits
  `template/pdca.toml.jinja:144-151`; 593 edits `:115-119` and `:176`. All are separate hunks,
  and none falls in another bundle's region.
- **Surfaces:** data
- **Difficulty:** high
- **Scope:** Restore the invariant for stack mode, per (i)–(viii): wave>0 PRs open against the
  real target base while still cut from the integration line; the fold builds the line by
  merging the accepted bundles' published branches (resolved per record mode), append-only and
  unforced within a run, fresh from the base at the run's first fold, refusing a line another
  run moved; an unpublished accepted bundle holds only its dependents; docs and comments
  updated to the true diff behaviour. / out of scope: resuming a milestone across runs
  (folding an earlier run's COMPLETE, unmerged prerequisites, #616); concurrent runs beyond
  the mismatch refusal (#591); basing only declared dependents on the line (#463); holding,
  rather than stopping on, an undeclared fold overlap; retargeting PRs older versions opened
  against an integration branch; merge mode; squash/rebase-merge support; changing how the
  fold combines same-wave siblings (no fold shape fixes the sibling merge-base case, because
  the joining commit never reaches the base; document it, per v).
- **Repro instruction:** As in Falsifiability. The end-to-end shape the unit tests stand in for:
  a three-wave own-repo batch A → B → C (`Depends on` chain) under `wave_mode = "stack"`. After
  wave 1's fold, B's open PR (base `pdca-integration/main`) holds its own change as a different
  commit and goes empty/conflicting; and B's and C's PRs, merged bottom-up, land in
  `pdca-integration/main`, never in `main`.
- **External dependencies:** none for Do and the gates (git is in the base toolchain; no network,
  no `gh`). A live-host check is owed at sign-off and is not a Do dependency: on a disposable
  GitHub repo, put A and C in wave 0 and B on both; merge A and C with merge commits, look at
  B's Files changed, use "Update branch", then merge B; and check that a published prerequisite
  whose merged PR branch was deleted is skipped via the real `gh pr view` path.
- **Test file:** `template/tests/test_integrate_stack_bases.py` (new). Real-git cases on the
  `FoldGit` fixture shape (`tests/test_integrate.py:105-165`: bare origin, `git config
  user.email/user.name`, `commit.gpgsign false`), plus flow-level cases added to
  `template/tests/test_flow_slice.py`. Import modules only (`from pdca_harness import
  integrate, publish, flow`), never a symbol the fix adds: the C4 red leg reverts production
  hunks, and a module that fails to import is PDCA-UNVERIFIABLE, not red. Cases:
  1. Within-run append-only (fold `[A]`, then `[A, B]` with **no** keyword against a
     `denyNonFastForwards` origin): T1 and A's branch tip are ancestors of the new tip. This
     carries the red.
  2. No force on a continuing fold: wrap `integrate._git` and assert the second fold's push
     has no `--force` / `--force-with-lease`. The flag check is needed because
     `denyNonFastForwards` accepts a forced push that happens to fast-forward.
  3. A new run's first fold (`folded_this_run={}`) over an old-run line starts from
     `origin/main` (old tip not an ancestor). This passes the new keyword, so it errors on the
     red leg; that is accepted.
  4. Concurrent mismatch: fold with `folded_this_run={target: T1}` after origin's line was
     moved to another SHA → `IntegrationError`, origin untouched.
  5. `"stacked"` (`Onto branch`) record: commit on a second bare remote `upstream` branch
     `feat`, record `{"mode": "stacked", "branch": "feat", "base": "upstream/feat"}`, plus an
     unrelated `feat` on origin. The fold merges `upstream/feat`'s tip, not origin's.
  6. Gone branch: merged → skipped (`merged.is_merged` patched true); not merged →
     `IntegrationError` naming the ref.
  7. Unpublished bundle passed to `fold` → `IntegrationError` before any git step.
  8. Chain shrink (v): fold `[A]`, cut + publish B from the line, merge A's branch into
     origin's `main` with `--no-ff`; `git diff main...B --name-only` is only B's file (red on
     `main`).
  9. Siblings (v): A and C in wave 0, fold, cut B from the line, merge A and C into `main`.
     Assert `git merge-base --all main B` gives two commits (pins the documented limitation).
     Then merge `main` into B and assert `main...B` is only B's file.
  10. Publish (i): wave>0 dry-run prints `--base main`; with both `Stacks on:` and a
      `stack-base` it prints `--base main`; the fork case is unchanged.
  11. Flow, at least 3 waves, non-dry (publisher not stub; publish and `fold` spied, the spy
      taking `**kwargs` and returning a worktree that is a real git repo): the first fold gets
      `folded_this_run == {}`, the second gets `{(repo, base): <that worktree's HEAD SHA>}`.
  12. Flow, at least 3 waves, dry-run: the second fold gets the target listed (value `None`),
      and the output shows "start" then "continue".
  13. Flow hold (iv), non-dry: wave 0 = {U, I}; wave 1 = {D (Depends on U), J (Depends on I)};
      U's publish leaves no `publish.json`. Fold gets only I; D is skipped naming U; J is
      built; the run does not print "STOPPING".
  14. Flow, no-target is not held (iv), non-dry: wave 0 = {N} with a patch and no `Repo +
      branch target`; wave 1 = {M (Depends on N)}. M is built, not skipped.
  15. Dry-run fold (iv)/(vii): a bare bundle with no `publish.json` folds with `dry_run=True`
      without error and prints `origin/<publish._branch_name(...)>` as its merge ref; with
      `folded_this_run` omitted the output has the "continue if origin has it" line, and
      `subprocess.run` is never called.

  Existing tests in `test_integrate.py` that fold bare `patch.diff`s may be updated to the new
  contract. The gate runs every test module the patch touches, on both legs.
- **Citations expected:** Do must cite path:line on the target branch for every change. The
  changes centre on `integrate.fold` (`integrate.py:132-230`), `_prepare_worktree`
  (`integrate.py:232-246`, which must also fetch a `"stacked"` record's remote), the `pr_base`
  choice in `publish.publish` (`publish.py:258-259`), the fold call in `flow`
  (`flow.py:1838-1860`) and `flow._runnable` (`flow.py:660-690`). Peer callsites: read the
  published record the way `publish._stack_base_branch` reads a `Stacks on` parent's
  (`publish.py:632-647`, via `_publish_record` `:590-598`). Hold dependents by mirroring
  `_runnable`'s existing not-COMPLETE skip, which already cascades. Follow the signed-off
  commit convention at `integrate.py:218-222` / `publish.py:285-288` (`-s`) and the existing
  error shape at `integrate.py:211-216`.
- **Prior-art check (triage cycles):** By path, on origin/main `24c7f83` (unchanged since
  iteration 1). `git -C ../pdca-harness log --oneline origin/main -- template/src/pdca_harness/integrate.py`:
  `cb52d06` (#405, sign off the fold's commits, a patch over this defect's DCO symptom), then
  the #297 lock/sweep rounds. `publish.py`: `44e91d9`, `1e647be` (#411 merge-mode base
  refusal), `e79d109`, `9ecbb01`, `b5e58ba`; none changes the stack-mode PR base.
  Closed-unmerged PRs touching `integrate.py`/`publish.py`: none. No open PR. Iteration 1's
  attempt was not published (sent back to Plan). Related open issues: #591 (concurrent-run
  overwrite), #463 (stack only declared dependents), #616 (cross-run resume, depends on this).
  The fix is carried downstream on getwyrd/wyrd-pdca as an instance delta. Result: not fixed
  upstream, not in flight.
- **Disposition hint:** likely-fix

Plan-review response: findings 1, 2, 3, 5 and 6 are addressed in place: the dry-run skips the fail-closed check and falls back to `_branch_name` (iv, vii, test 15); a `None` dry-run prints a third "continue if present" line (iii, vii); "unpublished" now means targeted only (iv, test 14); the invariant is limited to one run, and publish's #108 re-push is named as outside it; the `↑main` cue's narrower meaning is stated plainly (i). Finding 4 (is (iv) in scope?): the brief stands. (iv) is not a separate feature. It is the failure policy for a failure mode this fix creates: once the fold merges published branches instead of re-applying `patch.diff`, an unpublished bundle can no longer be folded at all. Making the fold "simply fail closed" would mean one failed publish stops the whole milestone run, and the human rejected exactly that at this Plan (2026-10-02, Notes). It stays NEEDS-HUMAN for sign-off to confirm.

## Notes for the human (not parsed)

- Edits `template/PCDA/quality-cycle/09-parallel-lanes.md` and `08-glossary.md`, the vendored
  model spec, which is NEEDS-HUMAN at Check by this project's rule (INTEGRATION §4).
- Decisions made at this Plan, with the human (2026-10-02). The goal is one `pdca flow` per
  milestone, with sign-off as the only planned stop. Merge mode is rejected for that goal
  because one blocked PR stalls the run.
  - Unpublished accepted bundle: hold its dependents, keep the run going (reverses iteration
    1's stop-all).
  - `Onto branch` records: merge the real remote's PR branch, other people's commits included.
  - Concurrent run: refuse on a tip mismatch (the cheap guard); full support stays #591.
  - Sibling diff: narrow the docs and document "Update branch"; don't change the fold.
  - No split: both halves rewrite the same doc paragraphs and the PR-base half is ~5 lines.
  - Cross-run resume: filed as #616, `Depends on 593`, out of scope here.
- Still a stop, by choice: an undeclared fold overlap. Holding instead is a possible follow-up.

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.

## Iteration 1 — carry-forward, and where this brief answers it

1. Sibling waves don't shrink → (v): docs narrowed, remedy documented, test cases 8–9.
2. `Onto branch` regression → (ii) record-mode resolution + `_prepare_worktree` fetch, test 5;
   merging the whole PR branch is accepted.
3. Concurrent-run mixing → (iii) SHA-map guard, test 4.
4. Test gaps → tests 2 (push-argument spy) and 11 (≥3-wave non-dry flow).
5. Dry-run append-only path → (vii), test 12.
6. Split → not split (Notes).
Live-host validation → External dependencies (owed at sign-off).
Do NOT re-attempt iteration 1's patch unchanged: (iv)'s hold, (iii)'s SHA guard, (ii)'s
record-mode resolution and (v)'s docs differ from it.

## Iteration 2 — carry-forward (from the previous attempt)
- Sign-off rationale: The design (real-base PRs, append-only fold of the real PR commits, hold dependents of an unpublished bundle) is accepted — keep it. Rebuild only to fix these: 1. Regression — rejected attempt folded: "unpublished" is decided only from publish.json on disk (integrate.unpublished, used at flow.py:1855), and publish.json survives an iterate (state.py:116 DOWNSTREAM_OF_BRIEF does not list it). A bundle published in an earlier run, iterated, rebuilt and accepted, whose re-publish FAILS this run, is not held: fold merges its old rejected branch and its dependents build on it. Also hold any bundle whose publish failed THIS run (publish rc non-zero, or texts not ready at flow.py:1817-1822), in addition to the publish.json check. Add a flow test: published earlier, rebuilt, re-publish fails -> held, its dependents skipped, the old branch not in the fold. 2. Diff-shrink docs overclaim: if the base moves between a wave-0 publish and the run's first fold, a single-predecessor chain also gets two merge bases and keeps the predecessor's files in its diff. Narrow (v)'s wording in the docs/docstrings (docs/07-crosscutting.md:649, 09-parallel-lanes.md:69, integrate.py:17-19, publish.py:252-254) to cover this case with the same "Update branch" remedy; do not change the fold design. Add a test pinning the base-moved case and the remedy. 3. Optional cleanups from code review: resolve published refs in one helper shared by unpublished() and fold so the definition can't drift; treat `git merge-base --is-ancestor` rc 128 as a git-step failure, not an overlap. Out of scope this round (brief unchanged): holding a `Conflicts with` partner of an unpublished bundle — the brief's (iv) holds prerequisites only.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  The design (real-base PRs, append-only fold of the real PR commits, hold dependents of an unpublished bundle) is accepted — keep it. Rebuild only to fix these:
  1. Regression — rejected attempt folded: "unpublished" is decided only from publish.json on disk (integrate.unpublished, used at flow.py:1855), and publish.json survives an iterate (state.py:116 DOWNSTREAM_OF_BRIEF does not list it). A bundle published in an earlier run, iterated, rebuilt and accepted, whose re-publish FAILS this run, is not held: fold merges its old rejected branch and its dependents build on it. Also hold any bundle whose publish failed THIS run (publish rc non-zero, or texts not ready at flow.py:1817-1822), in addition to the publish.json check. Add a flow test: published earlier, rebuilt, re-publish fails -> held, its dependents skipped, the old branch not in the fold.
  2. Diff-shrink docs overclaim: if the base moves between a wave-0 publish and the run's first fold, a single-predecessor chain also gets two merge bases and keeps the predecessor's files in its diff. Narrow (v)'s wording in the docs/docstrings (docs/07-crosscutting.md:649, 09-parallel-lanes.md:69, integrate.py:17-19, publish.py:252-254) to cover this case with the same "Update branch" remedy; do not change the fold design. Add a test pinning the base-moved case and the remedy.
  3. Optional cleanups from code review: resolve published refs in one helper shared by unpublished() and fold so the definition can't drift; treat `git merge-base --is-ancestor` rc 128 as a git-step failure, not an overlap.
  Out of scope this round (brief unchanged): holding a `Conflicts with` partner of an unpublished bundle — the brief's (iv) holds prerequisites only.
- Full previous attempt preserved in `iteration-v2/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).

## Iteration 3 — carry-forward (from the previous attempt)
- Sign-off rationale: The design (real-base PRs, append-only fold of the real PR commits, hold dependents of an unpublished bundle) stays — no further replan. Rebuild only to fix these: 1. Bug (reviewer C3/C5, reproduced at sign-off): a prerequisite merged into the base and its branch deleted between folds is skipped (integrate.py ~:382, is_merged path) while the continuing fold keeps building on the old run tip, so its work never reaches the line and later waves build without it (repro: fold A, publish B from the tip, merge A+B into main, delete fix/B, fold [A,B] with folded_this_run={TARGET: tip} -> b.txt missing). When a gone branch is skipped as merged, the continuing line must still incorporate it — e.g. merge the fetched base into the line (unforced, no rewrite). Add a regression that performs a real merge between two folds and asserts the content is on the line (the current test_integrate_stack_bases.py:296 case deletes an unmerged branch, so it cannot catch this). 2. Diff-shrink docs still overclaim: the fold merges every accepted bundle of a target, so a dependent gets multiple merge bases whenever any earlier wave of that target had two or more bundles, not only when it depends on two siblings. Fix the wording in 09-parallel-lanes.md:69, docs/07-crosscutting.md:648-651, integrate.py:18-21, publish.py:252-254, 08-glossary.md:293 to say "every earlier-wave branch on the line", with the same "Update branch" remedy; also say a later PR carries those earlier bundles' commits. Pin it with a test (wave 0 = {A, Z}, B depends on A only). 3. Weak e2e test: test_a_three_wave_run_folds_append_only_onto_a_real_origin (test_flow_slice.py:1523-1542) passes even with fresh+--force every fold; assert exactly one `pdca-integrate: issue_EA` merge commit on the line. Optional (code review): distinguish a real merge conflict (unmerged paths) from other `git merge` failures instead of always reporting "undeclared overlap"; make the "stacked"-record ref fallback (integrate.py:120-122) return None.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  The design (real-base PRs, append-only fold of the real PR commits, hold dependents of an unpublished bundle) stays — no further replan. Rebuild only to fix these:
  1. Bug (reviewer C3/C5, reproduced at sign-off): a prerequisite merged into the base and its branch deleted between folds is skipped (integrate.py ~:382, is_merged path) while the continuing fold keeps building on the old run tip, so its work never reaches the line and later waves build without it (repro: fold A, publish B from the tip, merge A+B into main, delete fix/B, fold [A,B] with folded_this_run={TARGET: tip} -> b.txt missing). When a gone branch is skipped as merged, the continuing line must still incorporate it — e.g. merge the fetched base into the line (unforced, no rewrite). Add a regression that performs a real merge between two folds and asserts the content is on the line (the current test_integrate_stack_bases.py:296 case deletes an unmerged branch, so it cannot catch this).
  2. Diff-shrink docs still overclaim: the fold merges every accepted bundle of a target, so a dependent gets multiple merge bases whenever any earlier wave of that target had two or more bundles, not only when it depends on two siblings. Fix the wording in 09-parallel-lanes.md:69, docs/07-crosscutting.md:648-651, integrate.py:18-21, publish.py:252-254, 08-glossary.md:293 to say "every earlier-wave branch on the line", with the same "Update branch" remedy; also say a later PR carries those earlier bundles' commits. Pin it with a test (wave 0 = {A, Z}, B depends on A only).
  3. Weak e2e test: test_a_three_wave_run_folds_append_only_onto_a_real_origin (test_flow_slice.py:1523-1542) passes even with fresh+--force every fold; assert exactly one `pdca-integrate: issue_EA` merge commit on the line.
  Optional (code review): distinguish a real merge conflict (unmerged paths) from other `git merge` failures instead of always reporting "undeclared overlap"; make the "stacked"-record ref fallback (integrate.py:120-122) return None.
- Full previous attempt preserved in `iteration-v3/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).

## Iteration 4 — carry-forward (from the previous attempt)
- Sign-off rationale: The design (real-base PRs, append-only fold of the real PR commits, hold dependents of an unpublished bundle) stays — no replan. Sign-off cleared T5, validation and the six old plan-review items. Rebuild only to fix these (adversary/code-review findings, SUMMARY §6 items 3-7): 1. Late publish of a held wave>0 bundle ships later waves into main (most important). The stack-base records the integration BRANCH NAME, so a later `pdca publish <id>` cuts from origin/pdca-integration/<base> as it is now (publish.py ~:246, patch.diff:744) — which already holds later waves — and opens it --base main. Record the integration-line commit SHA the bundle was built/verified on and cut the PR branch from that SHA. Real-git regression: waves {A} -> {U, J} -> {K}; U's publish fails; fold [A,J], build+publish K, fold [A,J,K]; then publish U for real against a bare origin: assert K's tip is NOT an ancestor of fix/U and `git diff main...fix/U` holds only A's and U's files (red today: j.txt/k.txt present). 2. Hold keys on the wrong signal (flow.py:1835-1837). Holding on ANY non-zero publish rc also holds the "branch pushed, `gh pr create` failed" case (publish.py:369-407 writes a fresh publish.json then returns 1) — e.g. re-publishing an iterated bundle whose old draft PR is still open. Hold only when no fresh branch was pushed THIS run (texts not ready / T4 fail / host-CI fail / apply or push fail); a bundle whose branch was pushed this run is folded and its dependents build. Keep iteration 2's guard: a stale publish.json from an earlier run must still not count as published. Add a flow test for the pr-create-failed case (branch folded, dependents built) next to the existing stale-republish test. 3. Needless STOP on a gone-and-merged branch already on the line (integrate.py ~:376-377, :398-413). Take in the base only when the gone bundle's work is NOT already on the line (e.g. its `pdca-integrate: <bundle>` merge is in the line's first-parent history, or the flow passes the names already folded this run). Regression (real git, StackFoldGit): fold [A, C] -> T1; merge fix/A into main with a merge commit, delete fix/A; land an unrelated conflicting c.txt change on main; fold [A, C] with folded_this_run={TARGET: T1} -> must succeed without merging the base. 4. "stacked" (Onto branch) record on the merged-and-gone path (integrate.py ~:376-377): is_merged reads the other PR, which may target a different base, so the fold silently claims its work reaches <base_remote>/<base>. Take the merged-and-gone path only for "new-pr"/"stacked-pr" records (or check the merged PR's baseRefName); otherwise raise IntegrationError. 5. Stale text per (viii): gates.py:536-537 and publish.py :43, :611, :618, :644 still say wave PRs open against / build on the integration branch. Comment/docstring fixes only. Optional cleanups from code review: prune only remotes that hold PR branches (not base_remote); carry the slug through _fold_candidates instead of re-resolving; read _read_stack_base once in publish; strengthen the weak "gone branch merged is skipped" test (test_integrate_stack_bases.py:292-298) to assert the stderr line and the push. Out of scope (unchanged): basing only declared dependents on the line (#463).
- Sign-off session carry-forward (captured live, before §9 flattened it):
  The design (real-base PRs, append-only fold of the real PR commits, hold dependents of an unpublished bundle) stays — no replan. Sign-off cleared T5, validation and the six old plan-review items. Rebuild only to fix these (adversary/code-review findings, SUMMARY §6 items 3-7):
  1. Late publish of a held wave>0 bundle ships later waves into main (most important). The stack-base records the integration BRANCH NAME, so a later `pdca publish <id>` cuts from origin/pdca-integration/<base> as it is now (publish.py ~:246, patch.diff:744) — which already holds later waves — and opens it --base main. Record the integration-line commit SHA the bundle was built/verified on and cut the PR branch from that SHA. Real-git regression: waves {A} -> {U, J} -> {K}; U's publish fails; fold [A,J], build+publish K, fold [A,J,K]; then publish U for real against a bare origin: assert K's tip is NOT an ancestor of fix/U and `git diff main...fix/U` holds only A's and U's files (red today: j.txt/k.txt present).
  2. Hold keys on the wrong signal (flow.py:1835-1837). Holding on ANY non-zero publish rc also holds the "branch pushed, `gh pr create` failed" case (publish.py:369-407 writes a fresh publish.json then returns 1) — e.g. re-publishing an iterated bundle whose old draft PR is still open. Hold only when no fresh branch was pushed THIS run (texts not ready / T4 fail / host-CI fail / apply or push fail); a bundle whose branch was pushed this run is folded and its dependents build. Keep iteration 2's guard: a stale publish.json from an earlier run must still not count as published. Add a flow test for the pr-create-failed case (branch folded, dependents built) next to the existing stale-republish test.
  3. Needless STOP on a gone-and-merged branch already on the line (integrate.py ~:376-377, :398-413). Take in the base only when the gone bundle's work is NOT already on the line (e.g. its `pdca-integrate: <bundle>` merge is in the line's first-parent history, or the flow passes the names already folded this run). Regression (real git, StackFoldGit): fold [A, C] -> T1; merge fix/A into main with a merge commit, delete fix/A; land an unrelated conflicting c.txt change on main; fold [A, C] with folded_this_run={TARGET: T1} -> must succeed without merging the base.
  4. "stacked" (Onto branch) record on the merged-and-gone path (integrate.py ~:376-377): is_merged reads the other PR, which may target a different base, so the fold silently claims its work reaches <base_remote>/<base>. Take the merged-and-gone path only for "new-pr"/"stacked-pr" records (or check the merged PR's baseRefName); otherwise raise IntegrationError.
  5. Stale text per (viii): gates.py:536-537 and publish.py :43, :611, :618, :644 still say wave PRs open against / build on the integration branch. Comment/docstring fixes only.
  Optional cleanups from code review: prune only remotes that hold PR branches (not base_remote); carry the slug through _fold_candidates instead of re-resolving; read _read_stack_base once in publish; strengthen the weak "gone branch merged is skipped" test (test_integrate_stack_bases.py:292-298) to assert the stderr line and the push.
  Out of scope (unchanged): basing only declared dependents on the line (#463).
- Full previous attempt preserved in `iteration-v4/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).

## Iteration 5 — carry-forward (from the previous attempt)
- Sign-off rationale: Re-plan to settle basic design decisions. NOT a split: the slice stays one bundle and the size backstop is set aside on purpose. The core design stays (real-base PRs, append-only fold of the real PR commits within a run, hold dependents of an unpublished bundle). Why: five build rounds keep finding new holes in one path, a prerequisite merged and its branch deleted between folds. Iteration 5's two findings there (SUMMARY §6 items 3 and 4) pull against each other because "already on the line" is decided by matching the `pdca-integrate: <bundle>` commit message. That is a design gap Plan must close, not another Do patch. Decide in the brief before rebuilding: 1. How the fold knows a gone, merged prerequisite is already carried. Options: the flow passes the bundle names it folded this run; compare against the merged PR's head SHA (needs `gh` to return it, merged.py:46); or something else. The message match scoped to `<base_remote>/<base>..HEAD` breaks once a later-wave PR merges (reviewer + adversary repro: waves {A} -> {B dep A, C}, merge fix/A then fix/B, delete both, unrelated conflict on main -> needless STOP). That repro must become a regression test. 2. Are commits pushed straight onto a stack PR branch after the fold carried it in scope (§6 item 4)? State it either way. 3. Cross-run cases (§6 items 5 and 6: hand re-drive of a held bundle on the grown line; late publish after a later run reset the line): in scope here or handed to #616. State it either way.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  Re-plan to settle basic design decisions. NOT a split: the slice stays one bundle and the size backstop is set aside on purpose. The core design stays (real-base PRs, append-only fold of the real PR commits within a run, hold dependents of an unpublished bundle).
  Why: five build rounds keep finding new holes in one path, a prerequisite merged and its branch deleted between folds. Iteration 5's two findings there (SUMMARY §6 items 3 and 4) pull against each other because "already on the line" is decided by matching the `pdca-integrate: <bundle>` commit message. That is a design gap Plan must close, not another Do patch.
  Decide in the brief before rebuilding:
  1. How the fold knows a gone, merged prerequisite is already carried. Options: the flow passes the bundle names it folded this run; compare against the merged PR's head SHA (needs `gh` to return it, merged.py:46); or something else. The message match scoped to `<base_remote>/<base>..HEAD` breaks once a later-wave PR merges (reviewer + adversary repro: waves {A} -> {B dep A, C}, merge fix/A then fix/B, delete both, unrelated conflict on main -> needless STOP). That repro must become a regression test.
  2. Are commits pushed straight onto a stack PR branch after the fold carried it in scope (§6 item 4)? State it either way.
  3. Cross-run cases (§6 items 5 and 6: hand re-drive of a held bundle on the grown line; late publish after a later run reset the line): in scope here or handed to #616. State it either way.
- Full previous attempt preserved in `iteration-v5/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
