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

Review issue #593: make stack-mode PRs target the real base and carry published commits forward without rewriting the integration line, while holding dependents of failed publishes.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief defines testable ancestry, PR-target, failure-isolation and diff-shrink contracts, including the iteration corrections; target/template/src/pdca_harness/integrate.py:235 and target/docs/07-crosscutting.md:642 ground the intended behavior. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only production changes leaves 170 tests runnable and produces 22 assertion failures plus 5 expected missing-API errors, including wrong PR bases and lost ancestry; review-red.log:747, review-red.log:804, review-red.log:815. |
| C3 Change | FAIL | A prerequisite merged and deleted between folds can disappear from the next wave's base: continuing from the old tip and skipping the deleted branch never incorporates the updated target; target/template/src/pdca_harness/integrate.py:352 and target/template/src/pdca_harness/integrate.py:382; reproduced in review-deleted-merged.log:3. |
| C4 Verification (red→green) | PASS | Restoring production changes independently turns the same 170 tests green; this confirms the shipped regression coverage, not the additional failing scenario below; review-green.log:474, gate-logs/C4-verify.log:2187. |
| C5 Causal adequacy | FAIL | Replacing copied commits addresses the original cause, but “merged into the target” does not establish “present in the continuing integration line”; the deleted-branch test never actually merges its fixture, leaving this incorrect assumption untested; target/template/src/pdca_harness/integrate.py:382, target/template/tests/test_integrate_stack_bases.py:296. |
| T1 Structure | PASS | Shared candidate/ref resolution keeps failure holding aligned with folding, and sorted target locks still cover folding plus re-gating; target/template/src/pdca_harness/integrate.py:119, target/template/src/pdca_harness/integrate.py:302, target/template/src/pdca_harness/flow.py:1882. |
| T2 Shape | PASS | Independently reran docs lint, the 22-page render/link audit, the production-import scanner and git diff whitespace checks, all successfully; review-scanners.log:1; frozen host-parity output agrees at gate-logs/host-ci-docs.log:10. |
| T3 Runtime | PASS | Independent driver suite: 2,244 tests, 2 skips, no failures; root render/update suite could not be rerun because copier is not importable locally, but its frozen log explicitly reports 24 tests with no skips and OK; review-suite.log:1775, gate-logs/T3-suite.log:54. |
| T4 Contribution | N/A | Contribution artifacts are intentionally absent at Check; their substantive audit must rerun at publish, as recorded in gate-logs/T4-contribution.log:10. |
| T5 Judgment | NEEDS-HUMAN | Confirm the vendored-model edits and hold-only-dependents policy, and independently settle path-based merged/closed-rejected prior art—these affect process semantics and duplication risk; target/template/PCDA/quality-cycle/09-parallel-lanes.md:69, target/template/src/pdca_harness/flow.py:1860, brief.md:271, brief.md:287. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the stack is usable on the live host: GitHub Files changed/Update branch and the real gh merged-PR lookup were not exercised, so that evidence remains local Git plus mocked host responses; target/docs/07-crosscutting.md:649, target/template/src/pdca_harness/merged.py:46, brief.md:208. |

One concrete defect remains (P2): preserve merged prerequisites when their branches disappear between folds. Publish A, fold A and record T1; publish B from T1; merge A and B into main with merge commits and delete B's branch; then fold [A, B] with this run's recorded T1. Fetch sees the new main, but checkout continues T1. The missing-branch path returns successfully because B is merged. The fold pushes the unchanged T1, so C, depending on B, builds without B. This occurs within one run; it is not the excluded cross-run-resume case.

The independent real-Git experiment observed:

```text
main files: ['a.txt', 'b.txt', 'base.txt']
integration files: ['a.txt', 'base.txt']
B carried into next wave: False
integration remained at first-fold tip: True
```

The full observation is in review-deleted-merged.log:1. Only the host's merged-status answer was mocked; the branches were actually published, merged and deleted in local Git. Before skipping a deleted merged branch, the implementation needs to ensure its contribution is carried by the continuing line, incorporating the appropriate merged history without rewriting that line. Add a regression with an actual merge between two folds; the current target/template/tests/test_integrate_stack_bases.py:296 case deletes an unmerged branch and asserts its file is absent, so it cannot establish this invariant.

Reproduce from target/template with TMPDIR pointing inside this review directory and PYTHONPATH=src:

```python
from tests.test_integrate_stack_bases import StackFoldGit, TARGET, LINE, _git
from pdca_harness import integrate
from unittest import mock

case = StackFoldGit()
case.setUp()
a = case._publish("A", {"a.txt": "a\n"})
first = integrate.fold(case.cfg, [a], folded_this_run={})
tip = integrate.pushed_tip(first[TARGET][1])
b = case._publish("B", {"b.txt": "b\n"}, cut_from=f"origin/{LINE}")
case._merge_pr("A")
case._merge_pr("B")
_git(case.origin, "branch", "-D", "fix/B")
with mock.patch("pdca_harness.merged.is_merged", return_value=True):
    folded = integrate.fold(case.cfg, [a, b], folded_this_run={TARGET: tip})
assert (folded[TARGET][1] / "b.txt").exists()  # fails on the supplied patch
```

The production stash was popped successfully. A reverse-application check of patch.diff passes against the restored target, and the stash list is empty. No production fixes were made. The C5 capability-probe smell-test found no added optional-capability probe masking a load-time cause; the C5 failure above is the separately demonstrated ancestry assumption.

For prior art, the brief reports searches by integrate.py and publish.py across merged history and closed-unmerged PRs. My path-scoped git log investigation returns only the harness's synthetic base commit, `95e965c pre-fix base 24c7f83...`; the disposable target has no remotes or closed-PR evidence. Thus that upstream/closed-rejected conclusion cannot be independently confirmed from this bundle. The provided INTEGRATION file is a template with TODO human-only entries; the explicit vendored-model human-review requirement is supplied by brief.md:287 and is retained above.

To discharge live-host validation, use a disposable GitHub repository and a rendered instance configured with wave_mode = "stack" and that repository as the briefs' target. Create A and C as independent wave-0 changes and B with Depends on: A, C; run `pdca flow A C B --no-act` using their actual issue IDs. Check that all PRs target main. Merge A and C with merge commits, inspect B's Files changed, use Update branch to merge main into B, and verify that only B's change remains before merging B. Separately exercise an A → B → C run with B merged and its branch deleted before the second fold: let the real `gh pr view <B-PR-URL> --json state` report MERGED, and verify that the integration tip still contains B before C builds. The current patch fails that last content check in the local reproduction above. These are human execution steps, not actions taken by this review.

### Advisory — adversary

# Adversarial review — issue 593 (stack-mode append-only fold, real-base PRs)

**Evidence.** The red→green proof holds. In `gate-logs/C4-verify.log` the red leg fails the key cases on
assertions, not import errors: the line not carrying `fix/A` / `fix/B`, the pushes passing `--force`, `--base
pdca-integration/main`, and `main...B` showing `a.txt`. The `TypeError` reds are the new-keyword cases the brief
accepted (test 3). The integrate cases call the real `integrate.fold` against real git. The publish case calls
the real `publish.publish`. I re-ran `tests.test_integrate_stack_bases` and `tests.test_integrate` on the patched
tree: 36 OK.

**Attacks that did not land:** the no-`--force` push on a continuing fold; the tip-mismatch refusal; rc 128 from
`--is-ancestor` treated as a git failure; gone branch → `is_merged` → skip or raise; `--prune` on every fetch;
the DCO trailer on merge commits; dry-run shelling nothing; resolving an `Onto branch` record to its own remote;
the hold cascading through `_runnable`; sorted per-target lock order (unchanged).

Findings:

- NEEDS-HUMAN [impl] — **The diff-shrink docs still overclaim, the same way last round's carry-forward #2 did.**
  The fold merges *every* accepted bundle of a target onto the line, not just a dependent's declared
  prerequisites. So the "two merge bases" case hits every later-wave PR whenever an earlier wave of that target
  had two or more bundles. That is the common case, not an edge case. I reproduced it with the real `fold`
  (`scratch/exp_unrelated_sibling.py`): wave 0 = {A, Z} with Z unrelated, and B `Depends on` A only. After A
  merges with a merge commit, `main...B` shows `['b.txt', 'z.txt']`. After Z merges too, `git merge-base --all`
  gives **2** bases and `main...B` shows `['a.txt', 'b.txt']`: B's *only* prerequisite, already merged. Neither
  documented exception covers this (B is not on two siblings, and the base did not move). Wrong text, which
  should say "every earlier-wave branch on the line":
  - `template/PCDA/quality-cycle/09-parallel-lanes.md:69` ("Once its only prerequisite merges … its own change —
    with two exceptions … a dependent that sits on two or more same-wave siblings")
  - `docs/07-crosscutting.md:648-651` ("shows its prerequisites' changes … usually its own change")
  - `template/src/pdca_harness/integrate.py:18-21`
  - `template/src/pdca_harness/publish.py:252-254`
  - `template/PCDA/quality-cycle/08-glossary.md:293`

  A case like the experiment above would pin it.

- NEEDS-HUMAN — **Merging any wave>0 PR now lands every earlier-wave PR of that target on the real base, including
  unrelated ones the human never approved or has closed.** This follows from the experiment above: B's PR
  (`--base main`, `publish.py:265`) carries Z's commits. Merge B and Z lands on `main` even if Z's own PR was
  rejected. Before this patch an own-repo wave>0 PR targeted the line, so this could not happen. Only the fork path
  carried the cumulative diff (#185). The docs say "merge the stack bottom-up" but never say that a PR carries
  non-prerequisite siblings, or that closing a lower PR does not keep it off the target. This is the #463 scope
  line. The human should confirm it is acceptable at sign-off, and the docs should say it.

- NEEDS-HUMAN — **The new publish-failed hold catches the sign-off's own iterate scenario even when only PR
  creation "failed".** The new-PR path always runs `gh pr create` (`publish.py:375-388`). `gh` exits non-zero when
  an open PR for that head branch already exists, which is the usual state of an iterated, still-draft bundle.
  By then the rebuilt branch has been force-pushed (`publish.py:295-302`), and `publish.json` is rewritten naming
  it with `pr_url: ""` (`publish.py:390-408`, rc 1). `flow.py:1838-1840` then marks the bundle failed, it is
  held, and every dependent is skipped. So a rebuilt bundle with an open PR always holds its dependents. The
  milestone needs another run, and that run then hits #616 (the dependent builds on a base missing the
  prerequisite). The new test models a different shape: its fake publish returns 1 with nothing pushed
  (`tests/test_flow_slice.py:1341`, used by `:1544`). Whether "branch pushed, PR already exists" counts as
  unpublished for the hold is a policy call. (Provisional: I could not run `gh` here.)

- NEEDS-HUMAN — **The tip-mismatch guard protects the line but not the PRs, and the PRs are what reach `main`
  now.** Publish cuts a wave>0 branch from `origin/<integration branch>` (`publish.py:246`) without checking it
  against the run's recorded tip. The final wave never folds (`flow.py:1853`, `k < len(wave_list) - 1`), so
  nothing checks it there. Concrete case: run 2 starts on the same base while run 1 is in its final wave, and
  run 2's first fold force-pushes a fresh line (`integrate.py:361`). Run 1's final-wave PRs then open against
  `main` carrying run 2's unmerged bundles, with no refusal. The same happens to a later manual `pdca publish
  <id>`, which the flow's own message suggests (`flow.py:1843`), because the `stack-base` marker persists after the
  run. Before this patch such a PR targeted the line and could not reach `main`. #591 is out of scope, but the
  invariant "every PR … reaches the real target" now means "reaches it with whatever is on the line when
  publish ran".

- NEEDS-HUMAN [impl] — **The end-to-end flow test `test_a_three_wave_run_folds_append_only_onto_a_real_origin`
  (`tests/test_flow_slice.py:1523-1542`) cannot tell "continue unforced" from "start fresh and `--force` every
  fold".** I re-ran it with `integrate.fold` wrapped to pass `folded_this_run={}` on every call (fresh +
  `--force` each time; `scratch/exp_e2e_weak.py`) and it still **passes**. `denyNonFastForwards` accepts a forced
  push that happens to fast-forward, and a fresh fold that merges EB still has T1 as an ancestor. Line 1542
  (`fix/issue_EB~1` in the line) is already implied by line 1540. The behaviour is still pinned elsewhere (the
  kwargs spy at `:1358-1372` and the push-argument spy at `tests/test_integrate_stack_bases.py:207-231`), so this
  is a weak test, not a coverage gap. To make it go red on that bug, assert exactly one `pdca-integrate:
  issue_EA` merge commit is in the line: an always-fresh fold makes two.

### Advisory — code-review

# Advisory code review — issue 593 (stack-mode append-only fold, real-base PRs)

Lens: correctness bugs the patch introduces, plus reuse / simplification / efficiency.
Advisory only; none of these gate.

**Bottom line:** I found no correctness bug that blocks the fix. The fold logic (fresh vs
continue vs auto, the tip-mismatch refusal, the unforced push on continue, the gone-branch
skip, the rc-128 split) matches the brief. The flow's hold (`publish_failed` +
`integrate.unpublished`, `_runnable`'s new `unpublished` check) also closes iteration 2's
regression, where an old `publish.json` stood in for a failed re-publish. The tests run the
real fold against real git, on an origin that refuses non-fast-forwards. They include the
failed re-publish case (`template/tests/test_flow_slice.py`, `StackModeFlow`), and they
check the push flags directly. All gates passed; T4 is deferred to publish. The items below
are small.

## Correctness

- `template/src/pdca_harness/integrate.py:402-407`: every non-zero `git merge` is reported
  as "an undeclared cross-wave overlap". The same patch takes care to keep a failed
  `merge-base --is-ancestor` (rc 128) from being reported as an overlap (`:392-398`), but
  `merge` gets no such check. One way this can happen: the optional re-gate runs in this
  same worktree (`flow.py:1905`, `gates.run_integration`) and nothing cleans the tree
  afterwards. The next continuing fold then does `checkout -B` (`:353`) with that build
  output still present. An untracked file in the way makes `git merge` refuse, and the
  operator is told to "declare the conflict / re-order", which is the wrong fix. The run
  stops either way, so the risk is a misleading message, not wrong state. Possible fix:
  tell a real conflict apart (unmerged paths present, e.g.
  `git diff --name-only --diff-filter=U`) from any other failure. Or reset/clean the
  integration tree before `checkout -B`. Also, the `merge --abort` return code at `:404` is
  ignored. If the abort fails, the next fold fails later at "could not start …", which is
  still fail-closed.
- `template/src/pdca_harness/integrate.py:120-122`: the `"stacked"` record fallback
  `ref.partition("/")[0]` cannot trigger with today's writer. `publish.py:437`/`:511`
  always record `base` as `f"{remote}/{branch}"`. If a record ever disagreed, the fallback
  would quietly merge `base`, a ref other than the recorded `branch`. Returning `None`
  instead fails closed (the bundle is then treated as unpublished) and is simpler.

## Simplification / efficiency / nits

- `template/src/pdca_harness/integrate.py:422-425`: `fetch --prune origin` runs in the
  human's **primary** checkout (`publish._checkout_path`). It prunes every stale `origin/*`
  tracking ref there, not just the published branches the fold needs. This is harmless in
  practice and is what the brief asks for (iv). A narrower option is to prune only the
  `refs/remotes/origin/<branch>` refs the fold merges. Separately, a failing fetch of
  `base_remote` now stops the fold; before, its exit code was ignored (`_git(repo, "fetch",
  base_remote)` with no check). This is intended and documented, but it is a behaviour
  change for flaky networks.
- `template/src/pdca_harness/integrate.py:273-276`: the dry-run fallback calls
  `publish._resolve_target(d)` a second time for the slug. `_targeted` (`:203-211`) already
  resolved it and threw the slug away. This is trivial; carrying the slug through
  `_fold_candidates` would avoid the second brief parse.
- `template/src/pdca_harness/integrate.py:308`: the dry-run header still says
  `fold N patch(es)`, but the plan now merges published branches (`:316`). Cosmetic.
- Test gap (minor), `template/tests/test_integrate_stack_bases.py:243-254`: the
  concurrent-mismatch test covers a line *moved* by another run. No test covers a listed
  target whose origin line was *deleted* mid-run (`line is None`,
  `integrate.py:344`, message "(absent)"). The same condition guards both, so the risk is
  low.

No item here needs a human decision. Nothing is tagged NEEDS-HUMAN.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T5 Judgment — Confirm the vendored-model edits and hold-only-dependents policy, and independently settle path-based merged/closed-rejected prior art—these affect process semantics and duplication risk; target/template/PCDA/quality-cycle/09-parallel-lanes.md:69, target/template/src/pdca_harness/flow.py:1860, brief.md:271, brief.md:287.
- [ ] Validation — fitness-to-purpose — Decide whether the stack is usable on the live host: GitHub Files changed/Update branch and the real gh merged-PR lookup were not exercised, so that evidence remains local Git plus mocked host responses; target/docs/07-crosscutting.md:649, target/template/src/pdca_harness/merged.py:46, brief.md:208.
- [ ] **The diff-shrink docs still overclaim, the same way last round's carry-forward #2 did.** The fold merges *every* accepted bundle of a target onto the line, not just a dependent's declared prerequisites. So the "two merge bases" case hits every later-wave PR whenever an earlier wave of that target had two or more bundles. That is the common case, not an edge case. I reproduced it with the real `fold` (`scratch/exp_unrelated_sibling.py`): wave 0 = {A, Z} with Z unrelated, and B `Depends on` A only. After A merges with a merge commit, `main...B` shows `['b.txt', 'z.txt']`. After Z merges too, `git merge-base --all` gives **2** bases and `main...B` shows `['a.txt', 'b.txt']`: B's *only* prerequisite, already merged. Neither documented exception covers this (B is not on two siblings, and the base did not move). Wrong text, which should say "every earlier-wave branch on the line":
- [ ] **Merging any wave>0 PR now lands every earlier-wave PR of that target on the real base, including unrelated ones the human never approved or has closed.** This follows from the experiment above: B's PR (`--base main`, `publish.py:265`) carries Z's commits. Merge B and Z lands on `main` even if Z's own PR was rejected. Before this patch an own-repo wave>0 PR targeted the line, so this could not happen. Only the fork path carried the cumulative diff (#185). The docs say "merge the stack bottom-up" but never say that a PR carries non-prerequisite siblings, or that closing a lower PR does not keep it off the target. This is the #463 scope line. The human should confirm it is acceptable at sign-off, and the docs should say it.
- [ ] **The new publish-failed hold catches the sign-off's own iterate scenario even when only PR creation "failed".** The new-PR path always runs `gh pr create` (`publish.py:375-388`). `gh` exits non-zero when an open PR for that head branch already exists, which is the usual state of an iterated, still-draft bundle. By then the rebuilt branch has been force-pushed (`publish.py:295-302`), and `publish.json` is rewritten naming it with `pr_url: ""` (`publish.py:390-408`, rc 1). `flow.py:1838-1840` then marks the bundle failed, it is held, and every dependent is skipped. So a rebuilt bundle with an open PR always holds its dependents. The milestone needs another run, and that run then hits #616 (the dependent builds on a base missing the prerequisite). The new test models a different shape: its fake publish returns 1 with nothing pushed (`tests/test_flow_slice.py:1341`, used by `:1544`). Whether "branch pushed, PR already exists" counts as unpublished for the hold is a policy call. (Provisional: I could not run `gh` here.)
- [ ] **The tip-mismatch guard protects the line but not the PRs, and the PRs are what reach `main` now.** Publish cuts a wave>0 branch from `origin/<integration branch>` (`publish.py:246`) without checking it against the run's recorded tip. The final wave never folds (`flow.py:1853`, `k < len(wave_list) - 1`), so nothing checks it there. Concrete case: run 2 starts on the same base while run 1 is in its final wave, and run 2's first fold force-pushes a fresh line (`integrate.py:361`). Run 1's final-wave PRs then open against `main` carrying run 2's unmerged bundles, with no refusal. The same happens to a later manual `pdca publish <id>`, which the flow's own message suggests (`flow.py:1843`), because the `stack-base` marker persists after the run. Before this patch such a PR targeted the line and could not reach `main`. #591 is out of scope, but the invariant "every PR … reaches the real target" now means "reaches it with whatever is on the line when publish ran".
- [ ] **The end-to-end flow test `test_a_three_wave_run_folds_append_only_onto_a_real_origin` (`tests/test_flow_slice.py:1523-1542`) cannot tell "continue unforced" from "start fresh and `--force` every fold".** I re-ran it with `integrate.fold` wrapped to pass `folded_this_run={}` on every call (fresh + `--force` each time; `scratch/exp_e2e_weak.py`) and it still **passes**. `denyNonFastForwards` accepts a forced push that happens to fast-forward, and a fresh fold that merges EB still has T1 as an ancestor. Line 1542 (`fix/issue_EB~1` in the line) is already implied by line 1540. The behaviour is still pinned elsewhere (the kwargs spy at `:1358-1372` and the push-argument spy at `tests/test_integrate_stack_bases.py:207-231`), so this is a weak test, not a coverage gap. To make it go red on that bug, assert exactly one `pdca-integrate: issue_EA` merge commit is in the line: an always-fresh fold makes two.
- [ ] **(iv) contradicts (vi)/(vii) in dry-run.** (iv) says "`fold` itself stays fail-closed: called with such a bundle [non-empty patch, no published branch], it raises `IntegrationError` naming it, before any git step". But (iv) also says the hold "applies only outside dry-run, because the stubbed publisher records no branch". A dry-run publish returns before writing `publish.json` (`publish.py:311-324`), so in a dry-run flow **every** bundle reaches `fold` unpublished. The existing tests (vi) keeps green also fold bare bundles with no `publish.json`: `tests/test_integrate.py:80-88` and `:89-102`. (vii) and test 12 then need the dry-run to print "one merge line per bundle, naming the branch ref it would merge", and that ref has no record to come from. The brief has to say whether the fail-closed check is skipped under `dry_run=True`, and where the dry-run ref comes from (e.g. `publish._branch_name`, `publish.py:568-576`). Without that, Do must guess, and either test 12 or `test_dry_run_shells_nothing` goes red.
- [ ] **The `None` mode can't be honoured in dry-run.** (iii) says that with `folded_this_run=None`, the fold "continues the integration branch if origin has it, else starts from the base". (vii) requires dry-run to print "start" or "continue". But a dry-run must shell nothing: `test_dry_run_shells_nothing` asserts `subprocess.run` is never called (`tests/test_integrate.py:82-86`). So the dry-run cannot learn whether origin has the branch. The brief should say what a `None` dry-run prints, e.g. always "start", or a third "continue if present" line.
- [ ] **(iv)'s "unpublished" test also catches non-contributing bundles.** The brief defines the held case as "an accepted bundle with a non-empty `patch.diff` but no published branch". A patched bundle with **no** `Repo + branch target` also matches that: it publishes with rc 0 and writes no `publish.json` (`publish.py:130-132`, `:182-184`, flow passes `skip_if_no_target=True` at `flow.py:649`), and `fold` already drops it (`integrate.py:121-129`). Read literally, (iv) would newly skip dependents of such a bundle. Today `_runnable` (`flow.py:684`) builds them. The brief should restrict "unpublished" to bundles that `_resolve_target` gives a target, and add a test that dependents of a no-target patched bundle still build.
- [ ] **Scope: (iv) is a second behaviour change, not part of #593.** The issue thread (notes.json) asks for an append-only fold over the PR branches, a retarget to the real base, and signed-off merge commits. It says nothing about partial-failure policy. Today an unpublished bundle can't stop the run on its own: `fold` applies `patch.diff` whether or not the bundle was published. (iv) turns a new failure mode into a "hold dependents, keep going" policy that changes `_runnable`, the publish loop (`flow.py:1800-1822`) and the flow's stop semantics. The Notes record that this was a human decision ("reverses iteration 1's stop-all"). Even so, it is separable review surface, and it is behind two of the three findings above. The human should confirm it belongs in this bundle rather than in a follow-up where the fold simply fails closed.
- [ ] **The invariant claims more than the scope delivers.** "In stack mode no harness push rewrites a commit that an open PR's base or head depends on" is stated without limits. But publish still re-pushes a bundle's PR branch with `--force-with-lease` on a rebuilt re-publish (`publish.py:289-296`, #108), and that rewrites commits a dependent's head (cut from the line) depends on. The brief treats the cross-run case as out of scope (#616). Unless the invariant is limited to "within one run", sign-off can't check it, and a reviewer can point to the publish path to show it is false.
- [ ] **The `↑<base>` cue in (i) stops telling the reader anything.** (i) keeps `mode = "stacked-pr"` so that `cli._publish_flag` "keeps its `↑<base>` cue (now `↑main`)". That cue exists to say "this targets the integration branch, merge bottom-up" (`cli.py:1058-1061`). Once every PR targets `main`, `↑main` doesn't mark which PRs are stacked or which ones must merge first, and stacking was the reason for the cue. Either the cue should name the predecessor or stack (`publish.json` already records `stacks_on` only for `Stacks on` parents, `publish.py:392-393`), or the brief should say plainly that the cue's meaning is being given up. As written, "only the comment changes" hides a UX regression.

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
- Iteration delta (if iterating): The design (real-base PRs, append-only fold of the real PR commits, hold dependents of an unpublished bundle) stays — no further replan. Rebuild only to fix these: 1. Bug (reviewer C3/C5, reproduced at sign-off): a prerequisite merged into the base and its branch deleted between folds is skipped (integrate.py ~:382, is_merged path) while the continuing fold keeps building on the old run tip, so its work never reaches the line and later waves build without it (repro: fold A, publish B from the tip, merge A+B into main, delete fix/B, fold [A,B] with folded_this_run={TARGET: tip} -> b.txt missing). When a gone branch is skipped as merged, the continuing line must still incorporate it — e.g. merge the fetched base into the line (unforced, no rewrite). Add a regression that performs a real merge between two folds and asserts the content is on the line (the current test_integrate_stack_bases.py:296 case deletes an unmerged branch, so it cannot catch this). 2. Diff-shrink docs still overclaim: the fold merges every accepted bundle of a target, so a dependent gets multiple merge bases whenever any earlier wave of that target had two or more bundles, not only when it depends on two siblings. Fix the wording in 09-parallel-lanes.md:69, docs/07-crosscutting.md:648-651, integrate.py:18-21, publish.py:252-254, 08-glossary.md:293 to say "every earlier-wave branch on the line", with the same "Update branch" remedy; also say a later PR carries those earlier bundles' commits. Pin it with a test (wave 0 = {A, Z}, B depends on A only). 3. Weak e2e test: test_a_three_wave_run_folds_append_only_onto_a_real_origin (test_flow_slice.py:1523-1542) passes even with fresh+--force every fold; assert exactly one `pdca-integrate: issue_EA` merge commit on the line. Optional (code review): distinguish a real merge conflict (unmerged paths) from other `git merge` failures instead of always reporting "undeclared overlap"; make the "stacked"-record ref fallback (integrate.py:120-122) return None.
- By / date: Eduard Ralph / 2026-10-02

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 6 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
