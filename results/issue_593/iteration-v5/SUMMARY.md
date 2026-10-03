# Result — issue 593 / stack-mode-append-only-fold-real-base-prs

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: Two defects in `[driver].wave_mode = "stack"` (found by review of
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
- Success criterion: With the patch, under `wave_mode = "stack"`:
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
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: Restore the invariant for stack mode, per (i)–(viii): wave>0 PRs open against the
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

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: pass — C4 PASS — red without the fix, green with it
- C5 added test exercises production, not a copy: pass — 1 added driver-suite test(s) import the production package 'pdca_harness'

## 4. Conformance (Check — stack)
- T1 Structure: none — (no gate configured)
- T2 shape: docs lint + site render link audit: pass — docs lint clean, site render + link audit clean
- T2 host CI parity: target docs-check.yml on the pushed tree: pass — host CI parity on the patched tree — docs lint clean, site render + link audit clean
- T3 runtime: render/update-compat + offline driver suites: pass — root suite OK, driver suite OK
- T4 PR body has a user-impact opener + tracker id in both artifacts: deferred — pr-description.md not drafted yet — the substantive T4 audit of the contribution artifacts runs at publish
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Review issue #593: make stack-mode folds append-only within a run, preserve published commits, target the real base, and hold dependents when no fresh branch was published.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief defines observable ancestry, PR-base, publication-failure, and run-isolation requirements, including the latest carry-forward corrections; `brief.md:26`, `brief.md:342`. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing production changes while retaining regression tests yields 27 assertion failures and 10 errors across 179 tests, including ancestry and PR-base failures; `reviewer-red.log:828`, `reviewer-red.log:894`, `reviewer-red.log:903`. |
| C3 Change | FAIL | A later stacked PR merged into main hides earlier fold markers from the moving-base history range, so an already-carried deleted prerequisite unnecessarily imports main and can stop unrelated work; `target/template/src/pdca_harness/integrate.py:414`, `target/template/src/pdca_harness/integrate.py:431`; reproduced at `reviewer-gone-history.log:9`. |
| C4 Verification (red→green) | PASS | Restoring the same production patch makes all 179 affected-module tests pass; this independently confirms the asserted regression evidence, while C3 records an additional uncovered case; `reviewer-red.log:905`, `reviewer-green.log:481`, `gate-logs/C4-verify.log:2284`. |
| C5 Causal adequacy | PASS | Real-commit ancestry and real-base targeting address both specified causes, and tests exercise production against real Git; no optional-capability probe masks a load-time cause; `target/template/tests/test_integrate_stack_bases.py:187`, `target/template/src/pdca_harness/integrate.py:375`, `target/template/src/pdca_harness/publish.py:274`; C3 identifies the remaining edge defect. |
| T1 Structure | PASS | Publication eligibility shares one candidate/ref resolver, while flow owns run-local tips and publication holds; the changes fit existing integration/publishing boundaries; `target/template/src/pdca_harness/integrate.py:127`, `target/template/src/pdca_harness/flow.py:1710`. |
| T2 Shape | PASS | Independently rerun docs lint, 22-page rendering/link audit, and whitespace checks pass; frozen host-CI parity agrees; `reviewer-docs.log:1`, `reviewer-render.log:3`, `gate-logs/host-ci-docs.log:15`. |
| T3 Runtime | PASS | Independent driver suite: 2,253 tests, two skips, zero failures; frozen root-suite evidence shows 24 tests passed, while the local root rerun lacks importable Copier; `reviewer-suite.log:1782`, `gate-logs/T3-suite.log:54`, `reviewer-root-suite.log:36`. |
| T4 Contribution | N/A | Contribution texts are intentionally drafted after Check; the substantive contribution audit must rerun at publish; `gate-logs/T4-contribution.log:10`. |
| T5 Judgment | NEEDS-HUMAN | Confirm the supplied path-based prior-art claims and applicability of the prior approval to the vendored-spec edits: this synthetic target cannot establish merged/closed history, and the brief identifies those edits as human-only; `reviewer-prior-art.log:4`, `brief.md:271`, `brief.md:287`, `target/template/PCDA/quality-cycle/09-parallel-lanes.md:69`. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the workflow is fit after resolving C3 and completing live-host validation: GitHub Files changed/Update branch and the real merged-PR lookup were not exercised, so those outcomes rest on local Git and mocked host state; `brief.md:208`, `target/template/tests/test_integrate_stack_bases.py:319`. |

**Finding — P2: the moving base erases evidence that a deleted prerequisite is already carried.**

`target/template/src/pdca_harness/integrate.py:430` queries first-parent subjects in `<base_remote>/<base>..HEAD`. After a later stacked PR merges, its ancestry carries earlier integration merge commits into the base. Those subjects disappear from this range even though the integration line still contains them. Consequently the check at line 414 fails and line 424 imports the current base unnecessarily. An unrelated conflicting base change then raises `IntegrationError`, stopping subsequent waves. This is the unnecessary STOP the latest carry-forward explicitly asks to avoid, rather than an overlap between accepted bundle branches.

Independent reproduction, runnable from this review directory with `python3 reviewer-repro.py`:

1. Publish A and C, then fold them to T1.
2. Publish B and D from T1, then fold A/C/B/D to T2.
3. Merge A, C, then B into main with actual Git merge commits; delete A's branch. Add a conflicting `d.txt` change to main.
4. Fold A/C/B/D again with this run's recorded T2.

Observed: A's published tip **is an ancestor** of T2; its fold subject is present in the full first-parent history but absent from the base-relative range. The fold fails on `d.txt` while processing A (`reviewer-gone-history.log:1`, `:5`, `:8`, `:9`). The remote line remains unchanged. All branch operations and merges are real Git against a local bare origin; only the GitHub `is_merged` lookup is replaced with the true state established by those merges. Preserve evidence of previously folded work independently of the moving target base, and add this topology to the regression coverage.

**Evidence and limits.** Production changes were stashed only in the supplied disposable target and restored successfully; regression tests stayed in place for both legs. No target source was edited. The production-import scanner also passed (`reviewer-prod-path.log:1`). The red leg contains substantive assertion failures, not merely errors from newly introduced APIs. The target matches the supplied patch; no stale-target caveat applies.

The local root runner returned 77 because Copier is not importable by `/usr/bin/python3`; this is a reviewer-host limitation, not a patch failure. Its frozen log reports the render/update suite actually passed (`gate-logs/T3-suite.log:54`). All six frozen gate logs were available. T4's deferred result is intentionally N/A. The instance-specific wrappers were adjudicated through their logs and, where available, their underlying tools were independently rerun.

The prior-art investigation against the supplied target found only synthetic base commit `df21c9a` and no remotes (`reviewer-prior-art.log:1`). The brief reports merged and closed-unmerged searches by `integrate.py`/`publish.py` path; it supplies no independently inspectable search output or equivalent coverage for the other affected paths. No other checkout was consulted. The available `target/template/docs/INTEGRATION.md.jinja:80` leaves the project-specific human-only list as TODO; the vendored-spec requirement is therefore taken from the explicit brief, not inferred from that template. Earlier sign-off decisions recorded in the brief are acknowledged; no redesign or scope re-entry is requested.

**Live-host validation owed.** In a disposable configured GitHub repository, prepare A and C in wave 0 and B depending on both, each changing a distinct file, and run `pdca flow A C B`. Inspect each URL with `gh pr view <URL> --json baseRefName,headRefName` and confirm the real target base. Have the human merge A and C with merge commits, inspect `gh pr diff <B-URL> --name-only`, use GitHub's “Update branch,” and confirm only B's change remains before merging B. In a separate run paused at a later wave's sign-off, merge and delete a prerequisite branch, then resume and confirm the real `gh pr view` lookup recognizes the merge and the continuing integration line retains the prerequisite's content. These live-host outcomes have not been observed by this reviewer.

This review is advisory; it does not change acceptance or gate results.

### Advisory — adversary

# Adversarial review — issue 593 (iteration 5)

I went after the red→green evidence, the iteration-4 carry-forward fixes, and the new
"was a branch pushed this run?" signal. Two real-git probes broke the merged-and-gone path
in `_gone_branch`. Everything else held up. The probes ran on `$PDCA_TARGET` with the
`StackFoldGit` fixture (python3 + git were available, so nothing here is provisional).

- NEEDS-HUMAN [impl] — **The fix for the needless STOP (iteration-4 item 3) misses the normal bottom-up merge.**
  `template/src/pdca_harness/integrate.py:414` decides "this line already carries it" by
  looking for `pdca-integrate: <bundle>` in `_merges_past`, and `integrate.py:427-431` limits
  that scan to `<base_remote>/<base>..HEAD`. Every wave≥1 PR is cut from the line, so it
  carries the earlier fold merge commits. Once one of those PRs merges into the base, those
  merge commits can be reached from the base and drop out of the scan. The check then misses
  a bundle that *is* on the line and falls through to `_take_in_base` (`integrate.py:424`,
  `:439-451`), which merges the base in and STOPs on any unrelated conflict.
  **Failing case (reproduced):** waves {A} → {B (Depends on A), C}. Fold [A] → T1. Publish B
  and C off the line. Fold [A,B,C] with `{TARGET: T1}` → T2. The maintainer merges fix/A and
  then fix/B into main and deletes both branches. Someone lands an unrelated `c.txt` change on
  main. Fold [A,B,C] with `{TARGET: T2}` (is_merged true) → `IntegrationError: issue_A's
  branch origin/fix/A is gone and its PR is merged, but origin/main … conflicts in c.txt`.
  A's merge commit is an ancestor of T2. An `Onto branch` record hits the same miss and
  raises at `integrate.py:418-423` instead. The pinning test
  (`template/tests/test_integrate_stack_bases.py:305-324`) merges only fix/A, never a
  wave-1 PR, so it cannot see this. Fix direction: limit the scan by where this run's line
  started (or have the flow pass in the bundle names it already folded), not by the base.
  Add the case above as a regression test.

- NEEDS-HUMAN — **"Already on the line" trusts a commit subject, not the merged head, so it can drop a merged PR's later commits.**
  `integrate.py:414-417` skips a gone, merged bundle once *any* `pdca-integrate: <bundle>`
  merge is on the line. If the PR got more commits after the fold carried it (say a reviewer
  pushes a fixup to fix/A), and it then merged with its branch deleted, the skip leaves those
  commits off the line, and the next wave builds and verifies without them.
  **Failing case (reproduced):** fold [A] → T1. Push a fixup to fix/A (`a.txt` → "a, after
  review"). Merge fix/A into main and delete it. Fold [A,B] with `{TARGET: T1}`. The line has
  `a.txt` = "a", main has "a, after review". With "delete branch on merge" off, the same fold
  would merge fix/A's new head. So the result depends on a repo setting. This partly reopens
  iteration-3 item 1. A tight fix needs the merged PR's head SHA (`merged.py:46` asks `gh` only
  for `state`), and it pulls against the finding above. A human should decide whether
  commits pushed straight onto a stack PR branch are in scope. The subject-match approach
  came from sign-off's own suggestion.

- NEEDS-HUMAN — **Only publish reads the recorded line tip. Do, the verify gate and drift still read the moving branch.**
  `publish.py:254-255` cuts the PR branch from the recorded tip. `worktree.py:96-98` (Do
  worktree), `gates.py:568-570` (`PDCA_VERIFY_BASE`) and `drift.py:49-64` still use
  `origin/pdca-integration/<base>` as it is *now*. `drift._resolve_base` even says it
  resolves "exactly as publish does", which is no longer true. Within one run the two agree.
  But a held bundle that is re-driven by hand (iterate-do, then drive, not a new flow) gets
  rebuilt and verified on the grown line, which now holds later waves, and then published
  from the old tip. Either the tested tree is not the pushed tree, or `git apply` fails with
  a misleading "rebase against origin/main" hint (`publish.py:375`). `pdca drift` on a
  late-published PR checks it against the grown line and can falsely report needs-rebase.
  This is a scope call (manual re-drive of a held bundle, close to #616), not a bug inside
  the flow.

- Tried and failed to refute:
  - **C4 red→green.** Confirmed in `gate-logs/C4-verify.log`. On the red leg,
    test_integrate_stack_bases had 17 failures + 9 errors, and test_flow_slice had 9 + 1.
    `test_a_held_bundle_published_later_…` goes red at a setup assertion
    (`test_flow_slice.py:1721`), not at its key check. So I re-ran it with publish ignoring
    the recorded tip (patched `publish._stack_marker`). It then fails at `:1731` ("LU's PR
    branch carries LK"), so it does guard the recorded-SHA part.
  - **The `_record_stamp` push signal** (`flow.py:655-675`). I checked every return path in
    `publish.py:157-429` and `:432-538`. `publish.json` is written only after the push, so an
    earlier run's record cannot pass as fresh. The one gap I found errs toward holding: an
    exception from `gh pr create` after the push (e.g. `gh` missing) holds a bundle that was
    pushed. That is the safe direction.
  - **Within-run behaviour:** the append-only unforced push, the refusal when another run
    moved the line, the hold cascade through `_runnable` (`flow.py:712-713`), the fork and
    dry-run plans, and `Onto branch` remote resolution. I found no input that breaks them.

### Advisory — code-review

# Advisory code review — issue 593 (stack mode: append-only fold, real-base PRs)

Lens: bugs this patch introduces, plus reuse / simplification / efficiency. Advisory only.
All `path:line` refs are on the patched target at `$PDCA_TARGET`.

Overall: the fold rewrite (`integrate.py:211-509`), the publish base choice and the flow hold
read as correct for the in-run cases the brief covers. Iteration 4's carry-forward items are all
handled: the tip-pinned cut, the hold keyed on "pushed this run", the gone-and-merged skip when
the line already carries it, the `Onto branch` refusal, and the stale text. The optional cleanups
are also done: one `_fold_candidates` helper, prune only on branch remotes, a single
`_stack_marker` read, and the stronger gone-branch test. I found no blocking correctness bug. Notes:

- NEEDS-HUMAN — `template/src/pdca_harness/publish.py:254-255`: the recorded line tip is used
  to cut the PR branch with no check that it is still on origin's line. Within one run that is
  right, because the line is append-only. But a held bundle can be published late, which the
  flow tells the human to do. If a **later run's first fold** has meanwhile force-pushed a fresh
  `pdca-integration/<base>` (`integrate.py:359`), that tip is no longer on any remote branch.
  The late publish then cuts from the old run's line. That line carries that run's fold merges
  and its other bundles' branches, some possibly rejected since, and they would ride into a PR
  against `main`. If the old commit has been garbage-collected, the publish fails with a
  generic "step failed" (`publish.py:374-378`). A cheap guard would refuse (or warn) when
  `git merge-base --is-ancestor <tip> origin/<stack-base>` fails. This sits on the cross-run
  boundary the brief scopes out (#616), so I have not marked it `[impl]`: a human should decide
  whether to guard now or leave it to #616.
- `template/src/pdca_harness/flow.py:663-664`: when `publish.publish` raises (so `_isolate`
  returns `None`) **after** the push but before `publish.json` is written, the bundle is held
  even though its branch is on origin. One way this happens: `gh` is missing, so
  `subprocess.run(pr_cmd)` raises `FileNotFoundError` (`publish.py:386`). This errs safe, since
  the bundle is held and its dependents are skipped loudly. It does differ from the stated rule
  "a branch pushed this run is folded" (`flow.py:1887-1888`). No change needed. Noting it so
  the docstring at `flow.py:649-654` is not read as exact.
- `template/tests/test_flow_slice.py:1503-1505`: the flow tests' fake publisher cuts from
  `origin/<stack-base>`, not the recorded tip. So none of the in-run flow cases covers the
  production `checkout_base = wave_tip` path (`publish.py:254-255`) for a normal wave>0 publish.
  Only the late-publish test (`test_flow_slice.py:1703-1732`) runs the real `publish.publish`
  on a tip-bearing marker. The two cut points give the same commit within a run, so this is a
  coverage gap, not a wrong assertion. Optional fix: have `_push_branch` read
  `publish._stack_marker(d)[1]` when it is set.
- Reuse / efficiency: nothing to flag. `_fold_candidates` (`integrate.py:127-135`) is now the
  one definition behind both `fold` and `unpublished`. The per-wave repeat of
  `_resolve_target` (once in `flow.unpublished`, once in `fold`) reads small brief files and
  is negligible. `_record_stamp` (`flow.py:667-674`) reads the whole `publish.json`, which is
  a few hundred bytes.

Gate evidence: C4 (red before the fix, green after), host-CI docs and T3 (root + driver suites)
pass per `check-gates.json`. T4 is deferred to publish, as expected at this stage.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T5 Judgment — Confirm the supplied path-based prior-art claims and applicability of the prior approval to the vendored-spec edits: this synthetic target cannot establish merged/closed history, and the brief identifies those edits as human-only; `reviewer-prior-art.log:4`, `brief.md:271`, `brief.md:287`, `target/template/PCDA/quality-cycle/09-parallel-lanes.md:69`.
- [ ] Validation — fitness-to-purpose — Decide whether the workflow is fit after resolving C3 and completing live-host validation: GitHub Files changed/Update branch and the real merged-PR lookup were not exercised, so those outcomes rest on local Git and mocked host state; `brief.md:208`, `target/template/tests/test_integrate_stack_bases.py:319`.
- [ ] **The fix for the needless STOP (iteration-4 item 3) misses the normal bottom-up merge.** `template/src/pdca_harness/integrate.py:414` decides "this line already carries it" by looking for `pdca-integrate: <bundle>` in `_merges_past`, and `integrate.py:427-431` limits that scan to `<base_remote>/<base>..HEAD`. Every wave≥1 PR is cut from the line, so it carries the earlier fold merge commits. Once one of those PRs merges into the base, those merge commits can be reached from the base and drop out of the scan. The check then misses a bundle that *is* on the line and falls through to `_take_in_base` (`integrate.py:424`, `:439-451`), which merges the base in and STOPs on any unrelated conflict. **Failing case (reproduced):** waves {A} → {B (Depends on A), C}. Fold [A] → T1. Publish B and C off the line. Fold [A,B,C] with `{TARGET: T1}` → T2. The maintainer merges fix/A and then fix/B into main and deletes both branches. Someone lands an unrelated `c.txt` change on main. Fold [A,B,C] with `{TARGET: T2}` (is_merged true) → `IntegrationError: issue_A's branch origin/fix/A is gone and its PR is merged, but origin/main … conflicts in c.txt`. A's merge commit is an ancestor of T2. An `Onto branch` record hits the same miss and raises at `integrate.py:418-423` instead. The pinning test (`template/tests/test_integrate_stack_bases.py:305-324`) merges only fix/A, never a wave-1 PR, so it cannot see this. Fix direction: limit the scan by where this run's line started (or have the flow pass in the bundle names it already folded), not by the base. Add the case above as a regression test.
- [ ] **"Already on the line" trusts a commit subject, not the merged head, so it can drop a merged PR's later commits.** `integrate.py:414-417` skips a gone, merged bundle once *any* `pdca-integrate: <bundle>` merge is on the line. If the PR got more commits after the fold carried it (say a reviewer pushes a fixup to fix/A), and it then merged with its branch deleted, the skip leaves those commits off the line, and the next wave builds and verifies without them. **Failing case (reproduced):** fold [A] → T1. Push a fixup to fix/A (`a.txt` → "a, after review"). Merge fix/A into main and delete it. Fold [A,B] with `{TARGET: T1}`. The line has `a.txt` = "a", main has "a, after review". With "delete branch on merge" off, the same fold would merge fix/A's new head. So the result depends on a repo setting. This partly reopens iteration-3 item 1. A tight fix needs the merged PR's head SHA (`merged.py:46` asks `gh` only for `state`), and it pulls against the finding above. A human should decide whether commits pushed straight onto a stack PR branch are in scope. The subject-match approach came from sign-off's own suggestion.
- [ ] **Only publish reads the recorded line tip. Do, the verify gate and drift still read the moving branch.** `publish.py:254-255` cuts the PR branch from the recorded tip. `worktree.py:96-98` (Do worktree), `gates.py:568-570` (`PDCA_VERIFY_BASE`) and `drift.py:49-64` still use `origin/pdca-integration/<base>` as it is *now*. `drift._resolve_base` even says it resolves "exactly as publish does", which is no longer true. Within one run the two agree. But a held bundle that is re-driven by hand (iterate-do, then drive, not a new flow) gets rebuilt and verified on the grown line, which now holds later waves, and then published from the old tip. Either the tested tree is not the pushed tree, or `git apply` fails with a misleading "rebase against origin/main" hint (`publish.py:375`). `pdca drift` on a late-published PR checks it against the grown line and can falsely report needs-rebase. This is a scope call (manual re-drive of a held bundle, close to #616), not a bug inside the flow.
- [ ] `template/src/pdca_harness/publish.py:254-255`: the recorded line tip is used to cut the PR branch with no check that it is still on origin's line. Within one run that is right, because the line is append-only. But a held bundle can be published late, which the flow tells the human to do. If a **later run's first fold** has meanwhile force-pushed a fresh `pdca-integration/<base>` (`integrate.py:359`), that tip is no longer on any remote branch. The late publish then cuts from the old run's line. That line carries that run's fold merges and its other bundles' branches, some possibly rejected since, and they would ride into a PR against `main`. If the old commit has been garbage-collected, the publish fails with a generic "step failed" (`publish.py:374-378`). A cheap guard would refuse (or warn) when `git merge-base --is-ancestor <tip> origin/<stack-base>` fails. This sits on the cross-run boundary the brief scopes out (#616), so I have not marked it `[impl]`: a human should decide whether to guard now or leave it to #616.
- [ ] **(iv) contradicts (vi)/(vii) in dry-run.** (iv) says "`fold` itself stays fail-closed: called with such a bundle [non-empty patch, no published branch], it raises `IntegrationError` naming it, before any git step". But (iv) also says the hold "applies only outside dry-run, because the stubbed publisher records no branch". A dry-run publish returns before writing `publish.json` (`publish.py:311-324`), so in a dry-run flow **every** bundle reaches `fold` unpublished. The existing tests (vi) keeps green also fold bare bundles with no `publish.json`: `tests/test_integrate.py:80-88` and `:89-102`. (vii) and test 12 then need the dry-run to print "one merge line per bundle, naming the branch ref it would merge", and that ref has no record to come from. The brief has to say whether the fail-closed check is skipped under `dry_run=True`, and where the dry-run ref comes from (e.g. `publish._branch_name`, `publish.py:568-576`). Without that, Do must guess, and either test 12 or `test_dry_run_shells_nothing` goes red.
- [ ] **The `None` mode can't be honoured in dry-run.** (iii) says that with `folded_this_run=None`, the fold "continues the integration branch if origin has it, else starts from the base". (vii) requires dry-run to print "start" or "continue". But a dry-run must shell nothing: `test_dry_run_shells_nothing` asserts `subprocess.run` is never called (`tests/test_integrate.py:82-86`). So the dry-run cannot learn whether origin has the branch. The brief should say what a `None` dry-run prints, e.g. always "start", or a third "continue if present" line.
- [ ] **(iv)'s "unpublished" test also catches non-contributing bundles.** The brief defines the held case as "an accepted bundle with a non-empty `patch.diff` but no published branch". A patched bundle with **no** `Repo + branch target` also matches that: it publishes with rc 0 and writes no `publish.json` (`publish.py:130-132`, `:182-184`, flow passes `skip_if_no_target=True` at `flow.py:649`), and `fold` already drops it (`integrate.py:121-129`). Read literally, (iv) would newly skip dependents of such a bundle. Today `_runnable` (`flow.py:684`) builds them. The brief should restrict "unpublished" to bundles that `_resolve_target` gives a target, and add a test that dependents of a no-target patched bundle still build.
- [ ] **Scope: (iv) is a second behaviour change, not part of #593.** The issue thread (notes.json) asks for an append-only fold over the PR branches, a retarget to the real base, and signed-off merge commits. It says nothing about partial-failure policy. Today an unpublished bundle can't stop the run on its own: `fold` applies `patch.diff` whether or not the bundle was published. (iv) turns a new failure mode into a "hold dependents, keep going" policy that changes `_runnable`, the publish loop (`flow.py:1800-1822`) and the flow's stop semantics. The Notes record that this was a human decision ("reverses iteration 1's stop-all"). Even so, it is separable review surface, and it is behind two of the three findings above. The human should confirm it belongs in this bundle rather than in a follow-up where the fold simply fails closed.
- [ ] **The invariant claims more than the scope delivers.** "In stack mode no harness push rewrites a commit that an open PR's base or head depends on" is stated without limits. But publish still re-pushes a bundle's PR branch with `--force-with-lease` on a rebuilt re-publish (`publish.py:289-296`, #108), and that rewrites commits a dependent's head (cut from the line) depends on. The brief treats the cross-run case as out of scope (#616). Unless the invariant is limited to "within one run", sign-off can't check it, and a reviewer can point to the publish path to show it is false.
- [ ] **The `↑<base>` cue in (i) stops telling the reader anything.** (i) keeps `mode = "stacked-pr"` so that `cli._publish_flag` "keeps its `↑<base>` cue (now `↑main`)". That cue exists to say "this targets the integration branch, merge bottom-up" (`cli.py:1058-1061`). Once every PR targets `main`, `↑main` doesn't mark which PRs are stacked or which ones must merge first, and stacking was the reason for the cue. Either the cue should name the predecessor or stack (`publish.json` already records `stacks_on` only for `Stacks on` parents, `publish.py:392-393`), or the brief should say plainly that the cue's meaning is being given up. As written, "only the comment changes" hides a UX regression.
- [ ] size backstop — this slice is behaving oversized: patch is 148 KB (threshold 125 KB); 3 round(s) already spent (threshold 3). Recommend answering `iterate-plan` at sign-off and authoring the split in the re-plan (`pdca split`), rather than `iterate-do`: a slice that is too big yields implementation-shaped findings every round, and splitting authors briefs, which is Plan's beat.

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: iterated-to-Plan
- Iteration delta (if iterating): Re-plan to settle basic design decisions. NOT a split: the slice stays one bundle and the size backstop is set aside on purpose. The core design stays (real-base PRs, append-only fold of the real PR commits within a run, hold dependents of an unpublished bundle). Why: five build rounds keep finding new holes in one path, a prerequisite merged and its branch deleted between folds. Iteration 5's two findings there (SUMMARY §6 items 3 and 4) pull against each other because "already on the line" is decided by matching the `pdca-integrate: <bundle>` commit message. That is a design gap Plan must close, not another Do patch. Decide in the brief before rebuilding: 1. How the fold knows a gone, merged prerequisite is already carried. Options: the flow passes the bundle names it folded this run; compare against the merged PR's head SHA (needs `gh` to return it, merged.py:46); or something else. The message match scoped to `<base_remote>/<base>..HEAD` breaks once a later-wave PR merges (reviewer + adversary repro: waves {A} -> {B dep A, C}, merge fix/A then fix/B, delete both, unrelated conflict on main -> needless STOP). That repro must become a regression test. 2. Are commits pushed straight onto a stack PR branch after the fold carried it in scope (§6 item 4)? State it either way. 3. Cross-run cases (§6 items 5 and 6: hand re-drive of a held bundle on the grown line; late publish after a later run reset the line): in scope here or handed to #616. State it either way.
- By / date: Eduard Ralph / 2026-10-02

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 6 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
