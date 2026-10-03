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

Review issue 593: make stack-mode waves preserve published commit ancestry, target the real base, and hold dependents of failed publishes while independent work continues.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief defines observable ancestry, PR-base, partial-failure and dry-run outcomes, with cross-run resume explicitly excluded; the latest carry-forward narrows diff-shrink expectations (brief.md:24, brief.md:188; target/template/src/pdca_harness/integrate.py:14). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing production changes reproduced lost PR ancestry, a predecessor remaining in the dependent diff, and the wrong PR base; these are assertion failures, not merely missing new APIs (review-red.log:663, review-red.log:779, review-red.log:797; target/template/tests/test_integrate_stack_bases.py:200). |
| C3 Change | PASS | No confirmed defect found: the tested behavior preserves the run tip, excludes stale failed republishes, and carries deleted merged prerequisites through the base (target/template/src/pdca_harness/integrate.py:335, target/template/src/pdca_harness/integrate.py:398, target/template/src/pdca_harness/flow.py:1835; target/template/tests/test_integrate_stack_bases.py:309). |
| C4 Verification (red→green) | PASS | Independent offline red→green: 175 tests yielded 25 failures and 7 new-API errors without production changes; restoring them passed 268 tests including publishing and verification-base coverage; live-host validation remains separate (review-red.log:854, review-green.log:557; gate-logs/C4-verify.log:2236). |
| C5 Causal adequacy | PASS | Real Git ancestry and merge-base tests show the identity-rewriting cause is removed; no added capability probe masks a load-time side effect, and the scanner confirms production imports (target/template/src/pdca_harness/integrate.py:384, target/template/tests/test_flow_slice.py:1591, target/template/tests/test_flow_slice.py:1596; review-prod-path.log:1). |
| T1 Structure | PASS | Published-reference resolution is shared by the hold and fold paths; target grouping and lock coverage remain intact, avoiding inconsistent admission or cross-target folding (target/template/src/pdca_harness/integrate.py:108, target/template/src/pdca_harness/integrate.py:130, target/template/src/pdca_harness/flow.py:1876). |
| T2 Shape | PASS | Independent whitespace check, docs lint and 22-page render/link audit passed; frozen host-CI evidence agrees (review-docs.log:1, review-docs.log:4; gate-logs/host-ci-docs.log:15; target/.github/workflows/docs-check.yml:36). |
| T3 Runtime | PASS | Independent full driver suite passed 2,249 tests with 2 skips; the frozen root-suite log shows 24 passing render/update tests, which could not be rerun here because Copier is not importable (review-suite.log:1775; gate-logs/T3-suite.log:54). |
| T4 Contribution | N/A | Contribution texts are deliberately absent during Check; the substantive contribution audit must rerun at publish (gate-logs/T4-contribution.log:10). |
| T5 Judgment | NEEDS-HUMAN | Confirm the vendored process-spec changes and prerequisite-only hold policy remain acceptable, and confirm path-based merged/closed/rejected prior art — these govern the workflow promise, while this one-commit snapshot cannot substantiate the brief's upstream-history claim (target/template/PCDA/quality-cycle/09-parallel-lanes.md:69; brief.md:271, brief.md:283, brief.md:287). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether cumulative review diffs and bottom-up merge-commit operation meet the milestone workflow, after live GitHub validation — GitHub Files changed, Update branch and real merged-PR lookup were not exercised; that part of the evidence rests on local Git and mocked merge-state responses (brief.md:208; target/template/tests/test_integrate_stack_bases.py:321; target/template/src/pdca_harness/merged.py:47). |

All source citations above refer to the supplied disposable target under `target/`; brief and evidence-log citations refer to this review directory. Its synthetic base identifies upstream `24c7f83`, consistent with the brief. Reverse-application checking of `patch.diff` passed after restoring the production stash. No source edits were made by the reviewer, and no stash remains.

Independent verification retained the patched tests while stashing only `template/src/pdca_harness`, then restored production with `git stash pop`. The red failures include the original contract: A's tip is not an ancestor, the chain diff is `a.txt, b.txt` instead of `b.txt`, and the recorded PR base is `pdca-integration/main` instead of `main`. Missing new parameters/helpers account for seven additional errors; they are not the basis for the reproduction verdict. The green selection includes all four changed test modules plus `test_publish_slice` and `test_verify_base`. The full suite independently exercises the real-Git deleted-branch recovery, three-wave push flags and single A integration merge, stale failed-republish exclusion, and unrelated earlier-wave branch inclusion.

The instance-scoped gate wrappers are not part of this snapshot. Their captured logs were read; available underlying tests, docs validators and production-import scanner were rerun directly. Copier is absent from this interpreter, so the root render/update verdict uses the frozen successful log, not a claim of an independent rerun. T4's deferred result is not an unmet gate or a human blocker.

Prior-art investigation: `git -C target log --oneline -- template/src/pdca_harness/integrate.py template/src/pdca_harness/publish.py template/src/pdca_harness/flow.py` returns only `2db527c pre-fix base 24c7f83...`; `git -C target remote -v` returns nothing. The brief records merged-history searches by affected integrate/publish paths and asserts no closed-unmerged PRs, but supplies no independently inspectable closed/rejected search output. Thus the historical conclusion remains a T5 decision. The instance-specific INTEGRATION §4 is not supplied; its vendored-spec human-only rule is explicitly reported in brief.md:287. The target's INTEGRATION template still has a TODO for that list (target/template/docs/INTEGRATION.md.jinja:80).

For live validation, use an authorized disposable GitHub repository and a rendered instance targeting it with `wave_mode = "stack"`. Brief A and C as independent file additions and B with `Depends on: A, C`; run `pdca flow A C B`. Confirm each recorded PR base is `main`. Merge A and C using merge commits, inspect B's Files changed, then run `gh pr update-branch <B-PR-URL>` or use Update branch; expect only B's own change afterwards, and merging B should land all three changes on main. Repeat with B depending only on A: C still rides on its branch because the fold includes every earlier-wave branch for the target. Local tests already reproduce both the multiple-merge-base condition and its remedy (target/template/tests/test_flow_slice.py:1596).

For the deletion check, use accepted, published A and B bundles in that disposable instance, with B's published branch carrying A, before either PR is merged. From the instance root start `PYTHONPATH=src python3`; import `Config` from `pdca_harness.config` and `integrate` from `pdca_harness`, then execute `cfg = Config.load(); a = cfg.find_bundle("A"); b = cfg.find_bundle("B"); first = integrate.fold(cfg, [a], folded_this_run={}); tips = {key: integrate.pushed_tip(wt) for key, (_, wt) in first.items()}`. Keep this interpreter open. In the host UI, merge A and B using merge commits and delete B's branch. Confirm `gh pr view <B-PR-URL> --json state` reports MERGED. Back in the interpreter execute `second = integrate.fold(cfg, [a, b], folded_this_run=tips)`. For the returned integration worktree, run `git -C <worktree> show HEAD:<B-file>` and `git -C <worktree> merge-base --is-ancestor <saved-tip> HEAD`: expect B's content and exit 0. This calls the real merged-state lookup without a mock. The equivalent local Git history and content test passed, but its `merged.is_merged` answer was mocked (target/template/tests/test_integrate_stack_bases.py:309). These steps are owed to the human; this advisory review did not create or merge live PRs.

### Advisory — adversary

# Adversarial review — issue 593 (stack-mode append-only fold, real-base PRs)

Bottom line: the red→green proof holds, and the core design (append-only fold of the real PR
commits, unforced pushes after a run's first fold, PRs opened against the real base) held up
against every attack below. I found one concrete case where the run stops when it doesn't
need to (reproduced with real git), two design consequences a human should rule on, and some
stale comments.

## Evidence (C4 / C5): attempted to refute, could not

- `gate-logs/C4-verify.log`: on the red leg the core cases fail for the right reasons, not
  because of an import error. On `main`, the second fold's force-push is refused by a
  `denyNonFastForwards` origin, so the flow prints "STOPPING"
  (`test_a_three_wave_run_folds_append_only_onto_a_real_origin`). The publish record base is
  `pdca-integration/main`, not `main` (`test_a_wave_bundle_publishes_against_the_real_base`).
  No dependent is held (`test_an_unpublished_bundle_holds_only_its_dependents`). Seven new
  cases error with a `TypeError` on the new keyword, which the brief accepts. Two red
  failures are about message wording only (`test_overlap_raises_integration_error`,
  `test_a_conflict_names_the_conflicting_paths`), but neither is the case that proves the
  fix. I re-ran `tests.test_integrate_stack_bases` and `tests.test_integrate` on the patched
  target: 40 OK.
- The e2e flow test (`template/tests/test_flow_slice.py`, `test_a_three_wave_run_…`) uses
  the real `integrate.fold` and a real origin. It now pins exactly one
  `pdca-integrate: issue_EA` merge and checks that only the first push is forced, so the old
  rebuild-and-force-push code cannot pass it. I found no case where a test passes against a
  copy of the production code instead of the code itself.
- Also tried and could not break: the "another run moved the line" check
  (`template/src/pdca_harness/integrate.py:338`), the unforced push for a continuing fold
  (`:355`), the `Onto branch` record resolving to the other remote's branch, and dry-run
  touching nothing.

## Findings

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/integrate.py:376-377` and `:398-413`:
  when a branch is gone and its PR is merged, the fold merges the base into the line. It
  does this even when that bundle's commits are **already on the line** from an earlier fold
  in this run. The flow passes the cumulative `accepted` list to every fold
  (`flow.py:1844`, `:1879`), so every wave-0 bundle is checked again at every later fold.
  If GitHub's "delete branch on merge" is on, this path runs as soon as a wave-0 PR merges
  mid-run. Concrete failing case, reproduced with real git on the `StackFoldGit` fixture
  (`scratch/exp_gone_in_line.py`):
  1. Fold `[A, C]` with `folded_this_run={}`. Call the pushed tip T1.
  2. The maintainer merges `fix/A` into `main` with a merge commit and deletes `fix/A`.
  3. A teammate lands an unrelated change to `c.txt` on `main`. C's PR is still open.
  4. Fold `[A, C]` with `folded_this_run={TARGET: T1}`.

  Result: `IntegrationError … origin/main, which carries its work, does not merge onto
  pdca-integration/main (conflicts in c.txt …)`, so the run STOPs. A's tip was an ancestor
  of T1, so nothing needed to be taken in. The control (`scratch/exp_not_deleted.py`) is
  identical except `fix/A` is kept: the fold succeeds. Whether the run stops therefore
  depends only on a host branch-deletion setting. This is not one of the three stop
  conditions the brief allows (iv). Fix idea: take in the base only when the gone bundle is
  not already on the line, for example by looking for its `pdca-integrate: <name>` merge in
  the line's first-parent history, or by having the flow pass the names it has already
  folded. Add this case as a test.
- NEEDS-HUMAN — `template/src/pdca_harness/flow.py:1835-1837` holds a bundle on **any**
  non-zero publish return code. The iteration-2 case this exists for ("published earlier,
  iterated, rebuilt, re-publish …") may in practice never get a zero return code. The
  re-publish's `--force-with-lease` push succeeds, and publish writes a fresh `publish.json`
  naming the new branch (`publish.py:391`). But `gh pr create` then fails because an open
  draft PR for the same head and `main` already exists, so publish returns 1
  (`publish.py:375-381`, `:407`). The result: every iterated bundle whose old PR is still
  open is held, and all its dependents are skipped for the run, even though a correct new
  branch was pushed this run. Before this patch, that return code was only reported and the
  dependents still built. I could not check this offline (it needs the real `gh`), so treat
  it as provisional. A human should decide whether the hold should key on "no branch pushed
  this run" rather than on the return code.
- NEEDS-HUMAN — a later `pdca publish` of a held wave>0 bundle now ships later waves' work
  into the real base. The flow tells the human to run `pdca publish <id>`
  (`flow.py:1840`). The bundle keeps its `stack-base`, so publish cuts it from the
  integration line **as it is now** (`publish.py:246`) and opens it `--base main`
  (`publish.py:264-265`). By then the line holds every bundle folded after the held one's
  wave. Concrete case: waves {A} → {U, J} → {K} → {L}, and U's publish fails. After the run,
  `pdca publish U` cuts from a line holding A, J and K. U's PR, opened against `main`, then
  carries J and K, and merging it (it is a wave-1 PR) lands K before K's own PR is
  reviewed. Before this patch, the same publish opened against the integration branch.
  Decide what base a late publish of a held bundle should use, for example the line commit
  it was built and verified on.
- NEEDS-HUMAN [impl] — some text still says wave PRs open against the integration branch,
  which (viii) says should now agree with the code. These are `gates.py:536-537` ("publish
  opens its PR against that branch") and, in `publish.py`, a file this diff already edits:
  `:43`, `:611` ("stacked PR base off the prior waves' folded work"), `:618` ("open its PR
  against an old integration branch") and `:644` ("builds + opens its PR on the prior waves'
  folded work"). These are comment and docstring fixes only.

## Where the verdict may have been too generous

- `check-gates.json` reports overall `pass`, with C4/C5 green. Those gates do not cover the
  "branch gone, PR merged" path when the bundle is already on the line (finding 1). The only
  test for that path (`test_a_merged_prerequisite_whose_branch_is_gone_still_reaches_the_line`)
  covers a bundle that was never folded. So the iteration-3 fix closed one gap and opened the
  needless stop above.

### Advisory — code-review

# Advisory code review — issue 593 (stack-mode append-only fold, real-base PRs)

Lens: bugs the patch introduces, plus reuse / simplification / efficiency. Advisory only.
All gates in check-gates.json pass (T4 deferred to publish). I found no blocking bug. The
core paths hold up on reading: resolve every ref before any git step, the tip-mismatch
refusal, unforced continue pushes, `_in_line` treating rc 128 as a git failure, and
conflict vs non-conflict merge errors. The new tests cover each brief case against real git.
The points below are small.

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/integrate.py:376-377`: when a published
  branch is gone and `merged.is_merged` is true, `_take_in_base` assumes the work is now in
  `<base_remote>/<base>`. For a `"stacked"` (`Onto branch`) record, `is_merged` reads the
  *other* PR's `pr_url` (`merged.py:42-53`), and that PR may have targeted a branch other
  than this fold's base. In that case the fold prints "its work reaches … through
  <base_remote>/<base>" (`integrate.py:414-415`) when it does not, and later waves build
  without it. Rare, but it is a silent miss. A simple guard: only take the merged-and-gone
  path for `"new-pr"` / `"stacked-pr"` records, or check the merged PR's `baseRefName`.
  Otherwise raise.
- `template/src/pdca_harness/integrate.py:458-461`: the fold now runs `fetch --prune` in the
  user's **primary** checkout for every remote it touches, including `base_remote`. Before,
  it ran a plain fetch. Gone-branch detection only needs pruning on `origin` and the
  `"stacked"` record remotes. Pruning the base remote too is harmless in practice (it only
  drops stale tracking refs), but it is a side effect the brief does not ask for. Optional:
  prune only the remotes that hold PR branches.
- `template/src/pdca_harness/integrate.py:268-270`: the dry-run fallback calls
  `publish._resolve_target(d)` again, though `_fold_candidates` already resolved it (and
  dropped the slug). Simplification, not a bug: carry the slug in the candidate tuple, or
  build the fallback ref inside `_fold_candidates`/`_published_ref` behind a `dry_run` flag.
- `template/src/pdca_harness/publish.py:264`: `wave_stacked` reads the `stack-base` file a
  second time, though `_stack_base_branch` (`publish.py:231`, `:648-650`) already read it to
  pick `stack_branch`. Correct as written. A small cleanup would be to read
  `_read_stack_base(d)` once and use it for both, so the "stack-base wins" rule lives in one
  place.
- `template/tests/test_integrate_stack_bases.py:292-298`: the "gone branch whose PR merged
  is skipped" case only asserts that `G.txt` is absent. That would also hold if the fold had
  skipped the bundle without the merged check, or pushed nothing at all. It is weak on its
  own, but `:309-330` covers the real behaviour (merged work reaches a continued line), so
  this is a nit. Asserting the "is gone and its PR is merged" stderr line and that `LINE`
  was pushed would make it pull its weight.

Nothing else found: the flow changes (`flow.py:1855-1885`, `_runnable` `flow.py:694-695`,
`_publish_bundle` return `flow.py:656`) are consistent with each other. `folded_tips` is
filled only from targets `fold` actually returned, and a `pushed_tip` failure is caught as
an `IntegrationError` and stops the run as the brief requires.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — Confirm the vendored process-spec changes and prerequisite-only hold policy remain acceptable, and confirm path-based merged/closed/rejected prior art — these govern the workflow promise, while this one-commit snapshot cannot substantiate the brief's upstream-history claim (target/template/PCDA/quality-cycle/09-parallel-lanes.md:69; brief.md:271, brief.md:283, brief.md:287).
- [x] Validation — fitness-to-purpose — Decide whether cumulative review diffs and bottom-up merge-commit operation meet the milestone workflow, after live GitHub validation — GitHub Files changed, Update branch and real merged-PR lookup were not exercised; that part of the evidence rests on local Git and mocked merge-state responses (brief.md:208; target/template/tests/test_integrate_stack_bases.py:321; target/template/src/pdca_harness/merged.py:47).
- [ ] `template/src/pdca_harness/integrate.py:376-377` and `:398-413`: when a branch is gone and its PR is merged, the fold merges the base into the line. It does this even when that bundle's commits are **already on the line** from an earlier fold in this run. The flow passes the cumulative `accepted` list to every fold (`flow.py:1844`, `:1879`), so every wave-0 bundle is checked again at every later fold. If GitHub's "delete branch on merge" is on, this path runs as soon as a wave-0 PR merges mid-run. Concrete failing case, reproduced with real git on the `StackFoldGit` fixture (`scratch/exp_gone_in_line.py`):
- [ ] `template/src/pdca_harness/flow.py:1835-1837` holds a bundle on **any** non-zero publish return code. The iteration-2 case this exists for ("published earlier, iterated, rebuilt, re-publish …") may in practice never get a zero return code. The re-publish's `--force-with-lease` push succeeds, and publish writes a fresh `publish.json` naming the new branch (`publish.py:391`). But `gh pr create` then fails because an open draft PR for the same head and `main` already exists, so publish returns 1 (`publish.py:375-381`, `:407`). The result: every iterated bundle whose old PR is still open is held, and all its dependents are skipped for the run, even though a correct new branch was pushed this run. Before this patch, that return code was only reported and the dependents still built. I could not check this offline (it needs the real `gh`), so treat it as provisional. A human should decide whether the hold should key on "no branch pushed this run" rather than on the return code.
- [ ] a later `pdca publish` of a held wave>0 bundle now ships later waves' work into the real base. The flow tells the human to run `pdca publish <id>` (`flow.py:1840`). The bundle keeps its `stack-base`, so publish cuts it from the integration line **as it is now** (`publish.py:246`) and opens it `--base main` (`publish.py:264-265`). By then the line holds every bundle folded after the held one's wave. Concrete case: waves {A} → {U, J} → {K} → {L}, and U's publish fails. After the run, `pdca publish U` cuts from a line holding A, J and K. U's PR, opened against `main`, then carries J and K, and merging it (it is a wave-1 PR) lands K before K's own PR is reviewed. Before this patch, the same publish opened against the integration branch. Decide what base a late publish of a held bundle should use, for example the line commit it was built and verified on.
- [ ] some text still says wave PRs open against the integration branch, which (viii) says should now agree with the code. These are `gates.py:536-537` ("publish opens its PR against that branch") and, in `publish.py`, a file this diff already edits: `:43`, `:611` ("stacked PR base off the prior waves' folded work"), `:618` ("open its PR against an old integration branch") and `:644` ("builds + opens its PR on the prior waves' folded work"). These are comment and docstring fixes only.
- [ ] `template/src/pdca_harness/integrate.py:376-377`: when a published branch is gone and `merged.is_merged` is true, `_take_in_base` assumes the work is now in `<base_remote>/<base>`. For a `"stacked"` (`Onto branch`) record, `is_merged` reads the *other* PR's `pr_url` (`merged.py:42-53`), and that PR may have targeted a branch other than this fold's base. In that case the fold prints "its work reaches … through <base_remote>/<base>" (`integrate.py:414-415`) when it does not, and later waves build without it. Rare, but it is a silent miss. A simple guard: only take the merged-and-gone path for `"new-pr"` / `"stacked-pr"` records, or check the merged PR's `baseRefName`. Otherwise raise.
- [x] **(iv) contradicts (vi)/(vii) in dry-run.** (iv) says "`fold` itself stays fail-closed: called with such a bundle [non-empty patch, no published branch], it raises `IntegrationError` naming it, before any git step". But (iv) also says the hold "applies only outside dry-run, because the stubbed publisher records no branch". A dry-run publish returns before writing `publish.json` (`publish.py:311-324`), so in a dry-run flow **every** bundle reaches `fold` unpublished. The existing tests (vi) keeps green also fold bare bundles with no `publish.json`: `tests/test_integrate.py:80-88` and `:89-102`. (vii) and test 12 then need the dry-run to print "one merge line per bundle, naming the branch ref it would merge", and that ref has no record to come from. The brief has to say whether the fail-closed check is skipped under `dry_run=True`, and where the dry-run ref comes from (e.g. `publish._branch_name`, `publish.py:568-576`). Without that, Do must guess, and either test 12 or `test_dry_run_shells_nothing` goes red.
- [x] **The `None` mode can't be honoured in dry-run.** (iii) says that with `folded_this_run=None`, the fold "continues the integration branch if origin has it, else starts from the base". (vii) requires dry-run to print "start" or "continue". But a dry-run must shell nothing: `test_dry_run_shells_nothing` asserts `subprocess.run` is never called (`tests/test_integrate.py:82-86`). So the dry-run cannot learn whether origin has the branch. The brief should say what a `None` dry-run prints, e.g. always "start", or a third "continue if present" line.
- [x] **(iv)'s "unpublished" test also catches non-contributing bundles.** The brief defines the held case as "an accepted bundle with a non-empty `patch.diff` but no published branch". A patched bundle with **no** `Repo + branch target` also matches that: it publishes with rc 0 and writes no `publish.json` (`publish.py:130-132`, `:182-184`, flow passes `skip_if_no_target=True` at `flow.py:649`), and `fold` already drops it (`integrate.py:121-129`). Read literally, (iv) would newly skip dependents of such a bundle. Today `_runnable` (`flow.py:684`) builds them. The brief should restrict "unpublished" to bundles that `_resolve_target` gives a target, and add a test that dependents of a no-target patched bundle still build.
- [x] **Scope: (iv) is a second behaviour change, not part of #593.** The issue thread (notes.json) asks for an append-only fold over the PR branches, a retarget to the real base, and signed-off merge commits. It says nothing about partial-failure policy. Today an unpublished bundle can't stop the run on its own: `fold` applies `patch.diff` whether or not the bundle was published. (iv) turns a new failure mode into a "hold dependents, keep going" policy that changes `_runnable`, the publish loop (`flow.py:1800-1822`) and the flow's stop semantics. The Notes record that this was a human decision ("reverses iteration 1's stop-all"). Even so, it is separable review surface, and it is behind two of the three findings above. The human should confirm it belongs in this bundle rather than in a follow-up where the fold simply fails closed.
- [x] **The invariant claims more than the scope delivers.** "In stack mode no harness push rewrites a commit that an open PR's base or head depends on" is stated without limits. But publish still re-pushes a bundle's PR branch with `--force-with-lease` on a rebuilt re-publish (`publish.py:289-296`, #108), and that rewrites commits a dependent's head (cut from the line) depends on. The brief treats the cross-run case as out of scope (#616). Unless the invariant is limited to "within one run", sign-off can't check it, and a reviewer can point to the publish path to show it is false.
- [x] **The `↑<base>` cue in (i) stops telling the reader anything.** (i) keeps `mode = "stacked-pr"` so that `cli._publish_flag` "keeps its `↑<base>` cue (now `↑main`)". That cue exists to say "this targets the integration branch, merge bottom-up" (`cli.py:1058-1061`). Once every PR targets `main`, `↑main` doesn't mark which PRs are stacked or which ones must merge first, and stacking was the reason for the cue. Either the cue should name the predecessor or stack (`publish.json` already records `stacks_on` only for `Stacks on` parents, `publish.py:392-393`), or the brief should say plainly that the cue's meaning is being given up. As written, "only the comment changes" hides a UX regression.

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: iterated-to-Do
- Iteration delta (if iterating): The design (real-base PRs, append-only fold of the real PR commits, hold dependents of an unpublished bundle) stays — no replan. Sign-off cleared T5, validation and the six old plan-review items. Rebuild only to fix these (adversary/code-review findings, SUMMARY §6 items 3-7): 1. Late publish of a held wave>0 bundle ships later waves into main (most important). The stack-base records the integration BRANCH NAME, so a later `pdca publish <id>` cuts from origin/pdca-integration/<base> as it is now (publish.py ~:246, patch.diff:744) — which already holds later waves — and opens it --base main. Record the integration-line commit SHA the bundle was built/verified on and cut the PR branch from that SHA. Real-git regression: waves {A} -> {U, J} -> {K}; U's publish fails; fold [A,J], build+publish K, fold [A,J,K]; then publish U for real against a bare origin: assert K's tip is NOT an ancestor of fix/U and `git diff main...fix/U` holds only A's and U's files (red today: j.txt/k.txt present). 2. Hold keys on the wrong signal (flow.py:1835-1837). Holding on ANY non-zero publish rc also holds the "branch pushed, `gh pr create` failed" case (publish.py:369-407 writes a fresh publish.json then returns 1) — e.g. re-publishing an iterated bundle whose old draft PR is still open. Hold only when no fresh branch was pushed THIS run (texts not ready / T4 fail / host-CI fail / apply or push fail); a bundle whose branch was pushed this run is folded and its dependents build. Keep iteration 2's guard: a stale publish.json from an earlier run must still not count as published. Add a flow test for the pr-create-failed case (branch folded, dependents built) next to the existing stale-republish test. 3. Needless STOP on a gone-and-merged branch already on the line (integrate.py ~:376-377, :398-413). Take in the base only when the gone bundle's work is NOT already on the line (e.g. its `pdca-integrate: <bundle>` merge is in the line's first-parent history, or the flow passes the names already folded this run). Regression (real git, StackFoldGit): fold [A, C] -> T1; merge fix/A into main with a merge commit, delete fix/A; land an unrelated conflicting c.txt change on main; fold [A, C] with folded_this_run={TARGET: T1} -> must succeed without merging the base. 4. "stacked" (Onto branch) record on the merged-and-gone path (integrate.py ~:376-377): is_merged reads the other PR, which may target a different base, so the fold silently claims its work reaches <base_remote>/<base>. Take the merged-and-gone path only for "new-pr"/"stacked-pr" records (or check the merged PR's baseRefName); otherwise raise IntegrationError. 5. Stale text per (viii): gates.py:536-537 and publish.py :43, :611, :618, :644 still say wave PRs open against / build on the integration branch. Comment/docstring fixes only. Optional cleanups from code review: prune only remotes that hold PR branches (not base_remote); carry the slug through _fold_candidates instead of re-resolving; read _read_stack_base once in publish; strengthen the weak "gone branch merged is skipped" test (test_integrate_stack_bases.py:292-298) to assert the stderr line and the push. Out of scope (unchanged): basing only declared dependents on the line (#463).
- By / date: Eduard Ralph / 2026-10-02

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 6 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
