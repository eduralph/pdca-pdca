# Brief — issue 593 / stack-mode-append-only-fold-real-base-prs

> The Plan artifact (docs 02 §PLAN). Do reads ONLY this file.

- **Slug:** stack-mode-append-only-fold-real-base-prs
- **Defect:** Two defects in `[driver].wave_mode = "stack"` for an own-repo target (found
  by review of getwyrd/wyrd-pdca#262; related #463, #591, #185):
  **1. Middle-wave PRs break within the same run.** `integrate.fold` rebuilds
  `pdca-integration/<base>` from `origin/<base>` on every call (`checkout -B branch
  origin/<base>`, `template/src/pdca_harness/integrate.py:209-210`), re-applies every accepted
  `patch.diff` as a NEW `pdca-integrate: <bundle>` commit (`integrate.py:211-223`), and
  force-pushes (`integrate.py:224-228`). A wave-1 bundle's PR is opened `--base` that
  branch (own repo: `publish.py:258-259`, `:307`). After wave 1 is accepted, the next fold
  rebuilds the branch with waves 0..1 as new commits, so the wave-1 PR's base now contains
  its own change as a different commit: the PR goes empty, conflicting or DCO-red before
  anyone can merge it. Any batch with three or more waves hits this in one run.
  **2. Wave 1+ PRs never reach the target.** For an own-repo target a wave>0 PR's `--base`
  is the integration branch (`publish.py:258-259`). Nothing retargets those PRs and nothing
  opens an integration → target PR, so merging them bottom-up merges into the integration
  branch only; only wave 0 lands on the target. (The fork path already opens against the
  real base, `publish.py:248-259`, but its diff never shrinks because the fold's commits
  are not the PR branches' commits — the cost #185 documents.)
- **Success criterion:** With the patch, on an own-repo target (`base_remote = "origin"`):
  (i) **Every wave PR targets the real base.** A wave>0 bundle (one with a recorded
  integration `stack-base`, `publish.py:601-605`) still cuts its branch from
  `origin/<integration branch>` (`publish.py:246`) — so it carries its predecessors — but its
  PR is opened `--base <its target base>` (e.g. `--base main`), not the integration branch;
  `publish.json` records that base. A hand-declared legacy `Stacks on:` parent keeps its
  PR-branch base (`--base fix/PARENT-…`, `tests/test_publish_slice.py:478-484` and
  `:1142-1160` keep passing) — but only when the bundle has **no** recorded `stack-base`.
  **When both are present, the `stack-base` rule wins**, as it already does for the branch
  choice (`publish._stack_base_branch`, `publish.py:639-641`): such a bundle is cut from the
  integration line and opens `--base main`. (In a flow run, `Stacks on` becomes a dependency
  edge, `waves.py:48`, `:63-65`, so the bundle lands in wave>0 and gets a `stack-base`
  stamp.) A test covers a bundle with both a `Stacks on:` line and a `stack-base` and
  asserts `--base main`. The fork path is unchanged (`--base main`,
  `tests/test_publish_slice.py:468-476`).
  (ii) **The fold carries the real PR commits.** After `integrate.fold`, every accepted
  patched bundle's published branch tip (`publish.json` `branch`) is an **ancestor** of the
  integration branch tip — the predecessors' own commits (same SHAs), not re-applied copies.
  Merges carry a DCO `Signed-off-by` trailer (a DCO check reading every PR commit sees them;
  keeps `tests/test_integrate.py:176-185`'s intent).
  (iii) **Within one run the integration branch is append-only.** Mechanism (decided here,
  not left to Do): `integrate.fold` gains a keyword-only parameter
  `folded_this_run: Collection[tuple[str, str]] | None = None`. A target listed in it
  continues from its pushed tip; a target NOT listed is started fresh from `origin/<base>`.
  `None` (direct callers, existing tests) means "continue any target whose integration
  branch already exists on origin, else start from the base". `flow` passes the targets it
  has already folded this run — the keys of its existing per-run `integ` map
  (`flow.py:1677`, reassigned from `folded` at `:1850`) — at the one call site
  (`flow.py:1844`), so the run's first fold passes an empty set. Each fold after the run's
  first is a fast-forward of the tip the previous fold pushed: no commit an earlier fold of
  the same run pushed is ever rewritten, and those pushes are made **without** force — they
  succeed against an origin with `receive.denyNonFastForwards = true`. A branch already in
  the integration line (an ancestor of its tip) is not merged twice. The run's first fold
  starts the line from the current `origin/<base>` — a new run never builds on a previous
  run's integration branch (it would carry work that may have been abandoned since, and miss
  newer base commits). That first fold **does** force-push (it replaces a previous run's
  line); only the folds after it are unforced. An origin that refuses non-fast-forwards on
  `pdca-integration/*` therefore refuses a new run's first fold when an old line exists —
  that is an `IntegrationError` (fail-closed), and the docs say to delete the old
  integration branch or allow force-push on that namespace.
  (iv) **Fail-closed where the old fold was.** A branch that does not merge cleanly onto the
  line (an undeclared cross-wave overlap) raises `integrate.IntegrationError` and leaves the
  pushed branch as it was (`tests/test_integrate.py:274-281` intent). An accepted bundle with
  a non-empty `patch.diff` but no published branch (no `publish.json` / no `branch`) also
  raises `IntegrationError` naming it — the next wave cannot build on a prerequisite that has
  no PR. Bundles with no patch (close/no-fix) are skipped as today (`integrate.py:59-62`).
  **Consequence, stated and accepted:** a bundle whose publish texts failed draft/T4 is
  still added to `accepted` (`flow.py:1817-1822`) but has no published branch, so in stack
  mode the next fold raises and **every later wave stops**, including waves that do not
  depend on it. #295's isolation still holds *inside* the wave (siblings publish); it does
  not extend across waves in stack mode. Folding that bundle from its `patch.diff` instead
  would bring back the re-applied commits this issue removes. The stop message names the
  bundle and the remedy (`pdca publish <id>`, then re-run). A test covers it.
  **Published branch gone from origin** (`origin/<publish.json branch>` does not resolve
  after fetch): if the bundle reads as merged (`merged.is_merged(cfg, id)`, the check
  `merge.py` already uses — its work is in the base), it is skipped; otherwise
  `IntegrationError` naming the bundle and the branch. A branch published by an older
  version (cut from a `pdca-integrate:*` line) gets no special handling: it is merged like
  any other, and a conflict is the ordinary overlap `IntegrationError`.
  (v) **Unchanged:** per-target grouping and sorted lock order (`integrate.py:163-179`,
  `tests/test_integrate.py:89-104, 214-243`), the per-target stack-base routing
  (`flow._point_at_integration`, `tests/test_integrate.py:284-330`), the lock covering fold + re-gate
  (`integrate.py:192-207`), dry-run printing a plan and touching nothing (`integrate.py:182-191`,
  `tests/test_integrate.py:80-88`; update its printed steps to the new ones), the stack-base
  stamp and `$PDCA_VERIFY_BASE` (`tests/test_verify_base.py`), and merge mode
  (`wave_mode = "merge"`, `merge.py`, `publish._merge_base_refusal` `publish.py:650-686`).
  (vi) **The text agrees.** The module docstring (`integrate.py:1-19`), the publish comments
  (`publish.py:242-257`), the `_publish_flag` comment (`cli.py:1058-1061`), and the user docs
  that describe stacked PRs as `--base`d on the integration branch and the fork diff as never
  shrinking — `template/PCDA/quality-cycle/09-parallel-lanes.md:69`, `docs/07-crosscutting.md:642-647`,
  `template/pdca.toml.jinja:115-119`, the glossary entry
  `template/PCDA/quality-cycle/08-glossary.md:290-292` ("increment-only stacked PR `--base`d
  on the branch", fork "cumulative" diff), `docs/05-check.md:813-816` ("each dependent opens a
  stacked draft PR"), and the sweep rationale `template/pdca.toml.jinja:176` ("folds rebuild
  from the base every call") — say what now happens: every PR targets the real base;
  a dependent's diff shows its predecessors' changes until they merge, then shrinks to its
  own; merge bottom-up with a merge commit (not squash or rebase, which rewrite the SHAs the
  dependents share); folds continue the run's line, which is restarted at each run's first
  fold. `cli._publish_flag`'s **behaviour** stays as is: a wave>0 PR still records
  `mode = "stacked-pr"` (`publish.py:383`), so it still shows `↑<base>` — now `↑main` —
  which keeps the "merge this stack bottom-up" cue; only its comment (`cli.py:1058-1059`)
  changes, to stop saying the PR targets the integration branch.
  The whole `template/tests` suite stays green (existing fold tests updated to give each
  bundle a published branch where the new contract needs one).
  Shown by the named test going red on `main` (the second fold rewrites the first fold's tip
  / is refused by a no-force origin; the predecessor's branch commit is not an ancestor of
  the integration tip; the wave>0 dry-run prints `--base pdca-integration/main`) and green
  with the fix.
- **Falsifiability:** RED is reachable offline on the base toolchain (stdlib Python ≥ 3.11 +
  git), no network, no `gh`: `tests/test_integrate.py:105-165` (`FoldGit`) already folds
  against a real bare `origin` + primary checkout. For (ii)/(iii): create bundle A's PR
  branch on origin (commit A's patch on a branch cut from `main`, push it, write A's
  `publish.json` with that `branch`), fold `[A]`, record the tip T1; cut B's branch from T1,
  commit + push it, write B's `publish.json`, fold `[A, B]`. On `main`: T1 is not an ancestor
  of the new tip, A's branch commit is not an ancestor either, and with
  `git -C origin.git config receive.denyNonFastForwards true` set before the second fold the
  force-push is refused → `IntegrationError`. For (i): the dry-run publish helper
  `tests/test_publish_slice.py:453-466` with `publish.write_stack_base(d,
  "pdca-integration/main")` instead of `Stacks on:` — on `main` it prints
  `--base pdca-integration/main`.
- **Invariant to restore:** In stack mode no harness push ever rewrites a commit that an
  open PR's base or head depends on, and every PR the harness opens targets a branch that
  reaches the real target when merged — so merging the PR stack bottom-up lands every wave
  on the target, with no step outside the PRs. Source: internal project rule (Tier C) — the
  stack-mode promise in `template/PCDA/quality-cycle/09-parallel-lanes.md:57,69` ("a
  dependent batch completes in one run as a reviewable PR stack the human merges
  bottom-up") and `docs/07-crosscutting.md:642-647`; DCO on every commit a PR carries
  (#405, `integrate.py:218-222`). Self-test: neither half alone satisfies it — retargeting
  PRs without folding the real branches leaves dependents with diffs that never shrink;
  append-only folding without retargeting leaves wave 1+ merging into the integration branch.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Ordering note:** No `Depends on` / `Conflicts with`: this batch (582, 589, 593, 597) runs
  as ONE wave — this very bug is in the v0.58.0 instance driver, so a multi-wave run here
  would break its own middle-wave PRs. File overlap: 593 owns `integrate.py` and
  `publish.py`. It also edits (a) `flow.py` at the one fold call (`:1844`, passing
  `folded_this_run`) — 597 edits `flow.py` too, but only the intake (`:1104-1108`,
  `:1925-1940`, `:2064-2104`), hundreds of lines away; (b) `cli._publish_flag`'s comment
  (`cli.py:1058-1059`), far from 589's `cli._flow` hunk (`:637-660`); (c)
  `template/pdca.toml.jinja:115-119` and `:176`, while 582 edits `:144-151` of the same
  file — separate hunks with more than 20 lines between them. Separate hunks fold cleanly.
- **Surfaces:** data
- **Difficulty:** high
- **Scope:** Restore the invariant for own-repo stack mode, per (i)–(vi): wave>0 PRs open
  against the real target base while still cut from the integration line; the fold builds the
  integration line from the accepted bundles' published branches (merged, not re-applied),
  append-only and unforced within a run, fresh from the base at the run's first fold (the
  `folded_this_run` parameter and its one `flow.py` call site, per (iii)); docs and comments
  updated. / out of scope: concurrent runs on one base overwriting each other's
  integration branch (#591 — separate); basing only declared dependents on the integration
  line instead of every wave>0 bundle (#463); retargeting or repairing PRs that older
  versions already opened against an integration branch; merge mode; squash/rebase-merge
  support; the fork path's branch/base choice (its diff starts shrinking for free once the
  fold carries the real commits — document it, don't redesign it).
- **Repro instruction:** As in Falsifiability. End-to-end shape the unit tests stand in for:
  a three-wave own-repo batch A → B → C (`Depends on` chain) under `wave_mode = "stack"`; after
  wave 1's fold, B's open PR (base `pdca-integration/main`) contains its own change as a
  different commit and goes empty/conflicting; and B's and C's PRs, merged bottom-up, land in
  `pdca-integration/main`, never in `main`.
- **External dependencies:** none (git is part of the base toolchain; no network, no `gh`).
- **Test file:** `template/tests/test_integrate_stack_bases.py` (new) — real-git cases for
  (ii)–(iv) on the `FoldGit` fixture shape (`tests/test_integrate.py:105-165`: bare origin,
  `git config user.email/user.name`, `commit.gpgsign false`), plus the publish dry-run case
  for (i) on the `test_publish_slice.py` fixture. Import modules only (`from pdca_harness
  import integrate, publish`), never a symbol the fix adds: the C4 red leg reverts production
  hunks, and a module that fails to import is PDCA-UNVERIFIABLE, not red. The within-run
  append-only test calls `fold` **without** the new keyword (fold `[A]`, then `[A, B]`
  against a no-force origin), so its red leg fails for the right reason, not a
  `TypeError`. Also cover: a new run's first fold (`folded_this_run=set()`) over an existing
  old-run `pdca-integration/main` starts from `origin/main` (the old tip is not an ancestor
  of the new one) — this case passes the new keyword, so on the red leg it errors rather than
  fails; that is acceptable, because it guards the new restart rule and the within-run test
  carries the red; the unpublished-bundle stop (iv); the missing-remote-branch case (iv); and
  the `Stacks on` + `stack-base` publish case (i). Existing tests in
  `test_integrate.py` that fold bare `patch.diff`s without a published branch may be updated
  to the new contract; the gate runs every test module the patch touches on both legs.
- **Citations expected:** Do must cite path:line on the target branch for every change. The
  changes centre on `integrate.fold` (`integrate.py:132-230`) and the `pr_base` choice in
  `publish.publish` (`publish.py:258-259`). Peer callsites: the published branch is read the
  way `publish._stack_base_branch` reads a `Stacks on` parent's (`publish.py:632-647`, via
  `_publish_record`); the signed-off commit convention is `integrate.py:218-222` /
  `publish.py:285-288` (`-s`); the existing fold's error shape is `integrate.py:211-216`.
- **Prior-art check (triage cycles):** Merged history by path —
  `git -C ../pdca-harness log --oneline origin/main -n 5 -- template/src/pdca_harness/integrate.py`:
  `cb52d06` (#405, sign off the fold's commits — a patch over this defect's DCO symptom),
  `87ed36e`, `6c40f8c`, `41f1fad`, `dd73b45` (#297 lock/sweep rounds). `publish.py`:
  `1e647be` (#411, merge-mode base refusal), `44e91d9`, `e79d109`, `9ecbb01`, `b5e58ba` — none
  change the stack-mode PR base. Closed-unmerged PRs touching `integrate.py`/`publish.py`:
  none (only #598–#600, which touch `cli.py`/`flow.py` and are unrelated). No open PR. Related
  open issues: #591 (concurrent-run overwrite, 0.59.0) and #463 (stack only declared
  dependents, 0.60.0) — both touch the same code but are separate fixes. The fix is carried
  downstream on getwyrd/wyrd-pdca as an instance delta. Result: not fixed upstream, not in
  flight.
- **Disposition hint:** likely-fix

## Notes for the human (not parsed)

- Changes `template/PCDA/quality-cycle/09-parallel-lanes.md` — the vendored model spec,
  NEEDS-HUMAN at Check by this project's rule (INTEGRATION §4).
- (Plan review) Three more calls are this brief's, for the human to confirm at sign-off: the
  `folded_this_run` mechanism in (iii); fail-closed across waves for an unpublished bundle
  in (iv), which narrows #295's per-bundle isolation in stack mode; and skip-if-merged for a
  deleted published branch in (iv). The glossary (08) is also vendored spec (INTEGRATION
  §4 → NEEDS-HUMAN at Check), like 09.
- Two points go beyond the issue text and are this brief's calls: (a) "start at the base only
  the first time" is read as the run's first fold, not "only when the branch has never
  existed" — continuing an earlier run's branch would carry abandoned work and miss newer
  base commits; (b) an accepted, patched bundle with no published branch stops the fold
  (fail-closed) instead of being folded from its `patch.diff`.

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.

Plan-review response: all seven findings accepted — `stack-base` beats `Stacks on` (stated +
tested); the first-fold signal is decided (`folded_this_run`, one `flow.py` call site) with a
red-leg-safe test plan; the new-run restart half has a test and its force-push is stated;
the cross-wave fail-closed consequence is stated and tested; missing-remote-branch handling
is decided; the docs list is completed and `_publish_flag` behaviour is pinned as unchanged;
citations corrected against `origin/main` 24c7f83.

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: The core direction (real-base PR targets, fold from the published PR commits, append-only within a run) was judged sound, but Check surfaced design questions the brief must settle before another build: 1. Sibling waves don't shrink (C5 / adversary): with two independent wave-N PRs A and C and a dependent B, the fold's sibling merge commit never reaches main, so after A and C merge B has two merge bases and its diff still shows C's change. Decide: narrow the docs/criterion to "shrinks for a single-predecessor chain", or change how the fold combines siblings — and add a test that merges the siblings into main and inspects the dependent's diff. 2. `Onto branch:` regression: the fold always resolves origin/<publish.json branch>, but stacked-mode records push to the brief's <remote> (publish.py:452, :507-511) — a bundle onto upstream/feat now stops the run with a wrong "gone from origin" error (worked before), or merges an unrelated same-named origin branch. The brief must cover `Onto branch` (resolve the record's base ref / fetch that remote) and say whether merging the whole existing PR branch onto the line is acceptable. 3. Concurrent-run mixing: a continuing fold adopts whatever origin's line is, so a second run's force-push gets silently built on (was a loud break before). Decide whether this fix carries the cheap guard (fold returns the pushed SHA, flow passes it back, refuse on mismatch) or it is deferred to #591. 4. Test gaps to name in the brief: a >=3-wave non-dry flow test asserting the second fold gets {(repo, base)}; a no-force test that spies on push args (denyNonFastForwards accepts a --force fast-forward). 5. Dry-run must show the append-only path (integ is only recorded when not dry, flow.py:1853). 6. Consider whether "PR targets real base" and "append-only fold" should be split into two bundles (pdca-pdca split) — they are near-separate outcomes sharing integrate/publish. Live-host validation (reviewer's recipe: A,C in wave 0, B on both; merge A,C; inspect B; and a deleted-merged-branch skip via real `gh pr view`) remains owed.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  The core direction (real-base PR targets, fold from the published PR commits, append-only
  within a run) was judged sound, but Check surfaced design questions the brief must settle
  before another build:
  1. Sibling waves don't shrink (C5 / adversary): with two independent wave-N PRs A and C and
     a dependent B, the fold's sibling merge commit never reaches main, so after A and C merge
     B has two merge bases and its diff still shows C's change. Decide: narrow the docs/criterion
     to "shrinks for a single-predecessor chain", or change how the fold combines siblings —
     and add a test that merges the siblings into main and inspects the dependent's diff.
  2. `Onto branch:` regression: the fold always resolves origin/<publish.json branch>, but
     stacked-mode records push to the brief's <remote> (publish.py:452, :507-511) — a bundle
     onto upstream/feat now stops the run with a wrong "gone from origin" error (worked before),
     or merges an unrelated same-named origin branch. The brief must cover `Onto branch` (resolve
     the record's base ref / fetch that remote) and say whether merging the whole existing PR
     branch onto the line is acceptable.
  3. Concurrent-run mixing: a continuing fold adopts whatever origin's line is, so a second run's
     force-push gets silently built on (was a loud break before). Decide whether this fix
     carries the cheap guard (fold returns the pushed SHA, flow passes it back, refuse on
     mismatch) or it is deferred to #591.
  4. Test gaps to name in the brief: a >=3-wave non-dry flow test asserting the second fold gets
     {(repo, base)}; a no-force test that spies on push args (denyNonFastForwards accepts a
     --force fast-forward).
  5. Dry-run must show the append-only path (integ is only recorded when not dry, flow.py:1853).
  6. Consider whether "PR targets real base" and "append-only fold" should be split into two
     bundles (pdca-pdca split) — they are near-separate outcomes sharing integrate/publish.
  Live-host validation (reviewer's recipe: A,C in wave 0, B on both; merge A,C; inspect B; and
  a deleted-merged-branch skip via real `gh pr view`) remains owed.
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
