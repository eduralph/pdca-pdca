# Result — issue 593 / stack-mode-append-only-fold-real-base-prs

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: Two defects in `[driver].wave_mode = "stack"` (found by review of
  getwyrd/wyrd-pdca#262; related #463, #591, #185). Together they stop a multi-wave run, and so
  a whole milestone, from completing in one `pdca flow` as a PR stack the human merges afterwards.
  **1. Middle-wave PRs break within the same run.** `integrate.fold` rebuilds
  `pdca-integration/<base>` from `<base_remote>/<base>` on every call (`checkout -B branch
  <base_remote>/<base>`, `template/src/pdca_harness/integrate.py:209-210`), re-applies every
  accepted `patch.diff` as a NEW `pdca-integrate: <bundle>` commit (`integrate.py:211-223`) and
  force-pushes (`integrate.py:224-228`). An own-repo wave-1 PR is opened `--base` that branch
  (`publish.py:258-259`). After wave 1 is accepted, the next fold rebuilds the branch with waves
  0..1 as new commits, so the wave-1 PR's base holds its own change as a different commit and
  the PR goes empty, conflicting or DCO-red before anyone can merge it. Any batch with three or
  more waves hits this in one run.
  **2. Wave 1+ PRs never reach the target.** For an own-repo target a wave>0 PR's `--base` is
  the integration branch (`publish.py:258-259`). Nothing retargets those PRs and nothing opens an
  integration → target PR, so merging them bottom-up lands only wave 0 on the target. (The fork
  path already opens against the real base, `publish.py:248-259`, but its diff never shrinks,
  because the fold's commits are not the PR branches' commits; #185.)
- Success criterion: With the patch, under `wave_mode = "stack"`:
  **(i) Every wave PR targets the real base.**
  (i-a) A wave>0 bundle (one with a recorded integration `stack-base`, `publish.py:601-605`) is
  cut from the integration line, so it carries its predecessors, but its PR is opened `--base
  <its target base>` (e.g. `--base main`), on the own-repo path too, and `publish.json` records
  that base. It is cut from the **line tip SHA recorded when its stack-base was written** (flow
  records the tip of the fold it was pointed at: `write_stack_base(d, branch, tip)`), not from
  the branch as it is now, so a late `pdca publish` of a held bundle never carries later waves.
  **Tip storage:** a NEW sibling file `stack-base-tip` (one SHA line) next to `stack-base`.
  `write_stack_base(d, branch, tip: str | None = None)` writes `stack-base` exactly as today and
  writes `stack-base-tip` when `tip` is given, else removes it; `clear_stack_base` removes both;
  a NEW reader `read_stack_base_tip(d) -> str` returns the SHA or `""`. `stack-base` keeps its
  one-line format and `read_stack_base` / `_read_stack_base` keep returning **only the branch**,
  so `gates.py:567` (`$PDCA_VERIFY_BASE`), `drift._resolve_base` (`drift.py:61-63`) and
  `tests/test_verify_base.py:221` are untouched. A tip file without a `stack-base` is ignored.
  **The tip SHA is `checkout_base` itself** (`publish.py:246`), not a later rewrite of the
  `checkout -B` step: that way the `[gates] host_ci` path, which fetches and pins
  `checkout_base` (`_host_ci_passes`, `publish.py:344-346`) and then replaces the `checkout -B`
  step with the pinned commit (`_pin_checkout`, `publish.py:349-350`, `:868-877`), pins the
  same tip, and `record["host_ci_base"]` equals it. The fetch step stays `origin`.
  With no recorded tip (older marker, or dry-run) it cuts from `origin/<stack-base>` as today. A
  hand-declared legacy `Stacks on:` parent keeps its PR-branch base (`--base fix/PARENT-…`;
  `tests/test_publish_slice.py:478-484`, `:1142-1160` keep passing), but only when the bundle
  has **no** recorded `stack-base`; when both are present the `stack-base` rule wins, as it
  already does for the branch choice (`publish._stack_base_branch`, `publish.py:639-641`). The
  fork path is unchanged (`tests/test_publish_slice.py:468-476`). A wave>0 PR still records
  `mode = "stacked-pr"` (`publish.py:383`), so `cli._publish_flag` keeps its `↑<base>` cue (now
  `↑main`); only its comment (`cli.py:1058-1061`) changes, saying plainly that the cue now means
  "part of a stack, merge bottom-up" and no longer names an intermediate branch.
  (i-b) **NEW — late publish after the line was reset refuses.** Before cutting from a recorded
  tip, publish fetches `origin` and checks the tip is an ancestor of `origin/<stack-base>`
  (`git merge-base --is-ancestor`; rc 1, or the commit not existing locally, = not on the line;
  any other rc = git failure). If it is not on the line (a later run's first fold force-pushed a
  fresh line, or the branch is gone), publish **refuses** before any push with rc ≠ 0 and a
  message naming the bundle, the recorded tip, the branch and #616 ("re-drive it in a new run").
  It never cuts from an orphaned tip.
  **(ii) The fold carries the real PR commits.** After `integrate.fold`, every accepted, patched
  bundle's published branch tip is an **ancestor** of the integration tip: the PRs' own commits
  (same SHAs), joined by `git merge --no-ff --signoff` merge commits, never re-applied. DCO keeps
  `tests/test_integrate.py:176-185`'s intent. The published branch is resolved from
  `publish.json` in ONE helper shared by the fold and the flow's hold (iv): for `"stacked-pr"` /
  `"new-pr"` it is `origin/<branch>`; for a `"stacked"` (`Onto branch`) record it is the record's
  own `base` ref (`<remote>/<branch>`, `publish.py:440-456`, `:502-511`), fetched from that
  remote, never a same-named branch on `origin`. Merging the whole existing PR branch, other
  people's commits included, is accepted. A branch already in the line (`--is-ancestor` rc 0) is
  not merged again; rc 128 is a git failure, not "not in line". A failed merge is aborted and
  reported as an undeclared overlap only when it left conflicting paths
  (`diff --name-only --diff-filter=U`); otherwise as a failed git step. A branch that moved
  since the last fold (commits pushed onto it after the fold carried it) has its new tip merged:
  **commits pushed straight onto a stack PR branch are in scope.**
  (ii-b) **Published branch gone** (its ref does not resolve after the fold's fetch; remotes that
  hold PR branches are fetched with `--prune`, `base_remote` is not, since `_prepare_worktree`
  fetches without it today, `integrate.py:239-241`). This path is **decided by commit SHA, never
  by commit message**:
  1. Ask the host for the bundle's PR state and merged head SHA through a NEW function in
     `merged.py`, e.g. `merged_head(cfg, id) -> str | None`: `gh pr view <pr_url> --json
     state,headRefOid` (the existing call is `merged.py:46`). It returns the `headRefOid` only
     when `state == "MERGED"`, else `None`; any `gh` failure or unparseable output returns `None`
     (fail-closed, as `is_merged` is). **`is_merged` is unchanged**: it has other callers
     (`flow.py:682`, `cli.py:1076`, `merge.py:200`).
  2. `None` (not merged, or unknown): raise `IntegrationError` naming the bundle and the ref
     looked up.
  3. Merged, and the merged head SHA **is an ancestor of the line** being built: the line
     already carries all of it. Skip it, print one stderr line saying so, and do **not** merge
     the base in. This holds no matter how the base has moved since: no step reads a
     `<base>..HEAD` range or a commit subject. (Round 5's `_merges_past` subject scan is
     removed.)
  4. Merged, and the head SHA is **not** an ancestor (the fold never carried that head, e.g. a
     fixup pushed after the fold; or the commit is not in the local clone at all, which is
     "not an ancestor", not an error): for a `"new-pr"` / `"stacked-pr"` record, merge
     `<base_remote>/<base>` into the line (signed off, unforced, a fast-forward for the push;
     skip if the base is already in the line), because the base now holds that work. A conflict
     there raises `IntegrationError` naming the conflicting paths. For a `"stacked"` (`Onto
     branch`) record, raise instead: that PR may have merged into a different base.
  **(iii) Within one run the integration line is append-only, and only this run's.**
  `integrate.fold` takes a keyword-only `folded_this_run: Mapping[tuple[str, str], str | None] |
  None = None`, mapping each `(repo, base)` this run already folded to the tip its last fold
  pushed (`None` in a dry-run).
  - **Listed** target: continue from its pushed tip; if `origin/<integration branch>` after fetch
    is not that SHA, raise `IntegrationError` naming the branch, both SHAs and the likely cause
    (another run on the same base, #591). Push **without** `--force`.
  - **Not listed**: the run's first fold of that target. Start fresh from `<base_remote>/<base>`
    and force-push, replacing any earlier run's line.
  - **`None`** (direct callers, existing tests): continue the branch if origin has it, else
    start from the base.
  A refused force-push on the fresh path names the remedy (delete the old line or allow
  force-push on `pdca-integration/*`). The `fold` return shape is unchanged
  (`{(repo, base): (branch, worktree)}`). `flow` reads each target's pushed tip right after
  `fold` returns (before any re-gate), keeps a per-run map separate from `integ` (filled in
  dry-run too, value `None`), passes it at the one call site (`flow.py:1844`), and passes the
  tip to `write_stack_base` for the next wave's bundles (i-a). That goes through
  `flow._point_at_integration` (`flow.py:694-707`), the only `write_stack_base` caller: it gains
  a `tips: Mapping[tuple[str, str], str | None]` argument and calls `write_stack_base(d, branch,
  tips.get(target))`. Its routing rule (own target only; clear a stale marker) is unchanged.
  **(iv) A partial failure holds only what depends on it; it does not end the run.** An accepted
  bundle with a non-empty `patch.diff` and a usable target (`publish._resolve_target` gives repo
  and base, the test `integrate._targeted` uses at `integrate.py:121-129`) for which **no branch
  was pushed in this run** is held: left out of the fold, and every bundle that depends on it,
  directly or through another, is skipped with the existing "skipped — prerequisite(s) not
  ready (…)" line naming it (mirror `flow._runnable`, `flow.py:660-690`, whose skip already
  cascades). "No branch pushed this run" covers: texts not ready / T4 failed
  (`flow.py:1817-1822`), publish failed before or at its push (`flow.py:651-653`), and a
  `publish.json` left from an earlier run (it survives an iterate; `state.py:116`
  `DOWNSTREAM_OF_BRIEF` does not list it). A bundle whose branch **was** pushed this run but
  whose `gh pr create` then failed (`publish.py:369-407` writes a fresh `publish.json` and
  returns 1) is NOT held: it is folded and its dependents build. An exception thrown after the
  push but before `publish.json` is written may hold a pushed bundle; that errs safe and is
  accepted. **The signal:** `_publish_bundle` (`flow.py:641-653`) returns `True` iff, after the
  call, `publish.json` exists and either did not exist before the call or its
  `os.stat().st_mtime_ns` changed (both publish paths write it only after every step, the push
  included, succeeded: `publish.py:394`, `:510`); else `False` (an exception logged by `_isolate`
  is `False`). Flow keeps a run-scoped set of bundle names that got `True` and holds every
  targeted, patched, accepted bundle not in it; a bundle whose texts were not ready
  (`flow.py:1817-1822`) is never added. Tests set a stale record's mtime back with `os.utime`
  so the comparison is not timing-dependent. Unrelated bundles still build, sign off, publish
  and fold. A patched bundle with
  **no** target is not held (it publishes rc 0 with no `publish.json`, `publish.py:178-184`;
  `fold` already drops it). The hold applies outside dry-run only. `fold` itself stays
  fail-closed outside dry-run: a targeted, patched bundle with no `publish.json` branch raises
  `IntegrationError` before any git step. Under `dry_run=True` that check is skipped and such a
  bundle is planned as merging `origin/<publish._branch_name(cfg, d, slug)>`
  (`publish.py:568-576`). Three things still **stop** the run: an undeclared overlap (a branch
  that does not merge cleanly; the pushed line left as it was, `tests/test_integrate.py:274-281`
  intent), the concurrent-run mismatch in (iii), and a git step failing.
  **(v) Diff shrink, stated truthfully.** A later wave's PR, cut from the line, carries **every
  earlier-wave branch on the line** (not only its prerequisites') and shows their changes until
  they merge. Once they have all merged with merge commits, its three-dot diff against the base
  is only its own change **when the line is a plain chain**: one branch per earlier wave, no base
  movement between the wave-0 publishes and the run's first fold, and no base merged in by
  (ii-b). Otherwise a fold merge commit joined histories the base got separately; that commit
  never reaches the base, the PR has several merge bases, and it can keep showing an
  already-merged change. The remedy is updating its branch from the base (GitHub's "Update
  branch"), after which its diff is its own change only. The docs say exactly this.
  **(vi) Unchanged:** per-target grouping and sorted lock order (`integrate.py:163-179`,
  `tests/test_integrate.py:89-104, 214-243`); the per-target stack-base routing RULE
  (`tests/test_integrate.py:284-330` keep passing; `_point_at_integration` gains only the
  `tips` argument, iii); the lock covering fold +
  re-gate (`integrate.py:192-207`); dry-run touching nothing (`integrate.py:182-191`,
  `tests/test_integrate.py:80-88`), though its printed plan changes (vii); the `stack-base`
  file format, `read_stack_base`, and `$PDCA_VERIFY_BASE` (`tests/test_verify_base.py`); merge mode (`merge.py`,
  `publish._merge_base_refusal` `publish.py:650-686`); `merged.is_merged`.
  **(vii) Dry-run shows the real plan.** Per target: "start `<branch>` fresh from
  `<base_remote>/<base>`" with a force-push, or "continue `<branch>` from this run's tip" with an
  unforced push, or (only when `folded_this_run` is `None`) "continue `<branch>` if origin has
  it, else start fresh from `<base_remote>/<base>`"; then one `git merge --no-ff --signoff <ref>`
  line per bundle (ref from `publish.json`, else the `_branch_name` fallback in iv). A dry-run
  flow of three or more waves prints "start" for the first fold and "continue" after.
  **(viii) The text agrees.** The module docstring (`integrate.py:1-19`), the publish comments
  and docstrings (`publish.py:43`, `:242-257`, and the stack-base helpers near `:611-647`), the
  `_publish_flag` comment (`cli.py:1058-1061`), `gates.py:535-538`, the `drift._resolve_base`
  docstring (`drift.py:50-56`, which says it resolves "exactly as publish does": make it say
  that publish cuts from the recorded tip while drift checks the line as it is now, a known
  cross-run limit, #616), and the user docs that call stacked PRs `--base`d on the integration
  branch or say the fork diff never shrinks:
  `template/PCDA/quality-cycle/09-parallel-lanes.md:57,69`, `docs/07-crosscutting.md:642-647`,
  `template/pdca.toml.jinja:115-119` and `:176` (the sweep rationale "folds rebuild from the base
  every call"), `template/PCDA/quality-cycle/08-glossary.md:290-292`, `docs/05-check.md:813-816`.
  They say: every PR targets the real base; merge the stack bottom-up with a merge commit (not
  squash or rebase, which rewrite the SHAs dependents share); the diff behaviour in (v); folds
  continue the run's line and restart at each run's first fold; a partial failure holds its
  dependents (iv).
  The whole `template/tests` suite stays green. Existing fold tests are updated to give each
  bundle a published branch where the new contract needs one; spies on `fold` accept the new
  keyword.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: Restore the invariant for stack mode per (i)–(viii): wave>0 PRs open against the
  real base, cut from the recorded line tip, and a late publish refuses an orphaned tip; the
  fold builds the line by merging the accepted bundles' published branches (resolved per record
  mode), append-only and unforced within a run, fresh at the run's first fold, refusing a line
  another run moved; a merged, deleted branch is judged carried or not by the merged PR's head
  SHA; an unpublished accepted bundle holds only its dependents; docs and comments match.
  Commits pushed onto a stack PR branch after a fold are in scope (ii, ii-b.4). / out of scope
  (to #616 unless noted): resuming a milestone across runs; a held bundle re-driven by hand
  being built/verified on the grown line (`worktree.py:96-98`, `gates.py:568-570`,
  `drift.py:49-64` still read the moving branch; only the drift docstring changes here);
  concurrent runs beyond the mismatch refusal (#591); basing only declared dependents on the
  line (#463); holding a `Conflicts with` partner of an unpublished bundle; holding, rather than
  stopping on, an undeclared fold overlap; retargeting PRs older versions opened against an
  integration branch; merge mode; squash/rebase-merge support; changing how the fold joins
  same-wave siblings (document it, per v); fetching a merged PR's deleted head by
  `refs/pull/N/head` (the base merge in ii-b.4 carries that work instead).

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

Review issue #593: keep stack-mode integration append-only within a run, preserve real PR commits, target the real base, and hold unpublished prerequisites without stopping unrelated work.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The contract distinguishes within-run ancestry, late publication, deleted branches and partial publication failures, with explicit exclusions for cross-run recovery and squash/rebase support; brief.md:28, brief.md:233. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing production changes while retaining the regression tests produced 27 failures and 27 errors across 191 tests, including wrong PR base and lost commit ancestry; review-red.log:1014, review-red.log:1089; target/template/tests/test_integrate_stack_bases.py:246. |
| C3 Change | PASS | The reviewed paths satisfy the bounded contract without a confirmed patch defect: real-base publication, commit-identity folding and run-scoped publication holds address the two reported failures; target/template/src/pdca_harness/publish.py:282, target/template/src/pdca_harness/integrate.py:348, target/template/src/pdca_harness/flow.py:1889. |
| C4 Verification (red→green) | PASS | Restoring the production changes made the same 191 tests pass; this confirms the offline regression contract, while live-host behavior remains a separate validation decision; review-green.log:495; target/template/tests/test_integrate_stack_bases.py:364, target/template/tests/test_integrate_stack_bases.py:691. |
| C5 Causal adequacy | PASS | Preserving PR commit identity and directing PRs to the real base removes the causes; the new ancestry refusal enforces a lifecycle invariant rather than masking a load-time capability problem, and tests import production modules; target/template/src/pdca_harness/integrate.py:395, target/template/src/pdca_harness/publish.py:282, target/template/tests/test_integrate_stack_bases.py:39. |
| T1 Structure | PASS | Fold eligibility and publication-reference resolution share one definition, while target grouping, ordered locks and the existing stack-base reader contract remain intact; target/template/src/pdca_harness/integrate.py:133, target/template/src/pdca_harness/integrate.py:309, target/template/src/pdca_harness/publish.py:675. |
| T2 Shape | PASS | Independently rerun docs lint, 22-page render/internal-link audit and diff whitespace check passed; the frozen host-CI log agrees; review-lint.log:1, review-render.log:2, gate-logs/host-ci-docs.log:10. |
| T3 Runtime | PASS | Independently rerun driver suite passed all 2,265 tests with two skips; frozen evidence also records 24 passing root render/update tests, which this review host could not reproduce because its Python lacks Copier; gate-logs/T3-suite.log:54, review-root-suite.log:7. |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the deferred gate owes its substantive audit to the mandatory publish-time rerun, so there is no current contribution verdict to reproduce; gate-logs/T4-contribution.log:8. |
| T5 Judgment | NEEDS-HUMAN | Approve the vendored process-model changes, reconfirm the recorded no-split waiver, and confirm the affected-path prior-art search covers merged and closed/rejected work—the supplied target has one synthetic commit and no remotes, so that historical conclusion cannot be independently established here; target/template/PCDA/quality-cycle/09-parallel-lanes.md:69, brief.md:342, brief.md:368, brief.md:379, review-prior-art.log:1. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the documented merge-commit/Update-branch workflow meets the milestone goal and complete its live GitHub check—real host PR rendering and deleted-head metadata were not exercised; current evidence uses real local Git with mocked gh responses; brief.md:255, target/template/tests/test_integrate_stack_bases.py:611, target/template/src/pdca_harness/merged.py:76. |

No confirmed patch defect was found. Source citations above refer to the supplied patched target under `target/`; the target was readable and matched the patch. Production changes were restored after the red leg, and no implementation changes were made.

Independent evidence:

- Red→green: from `target/template`, with production changes temporarily stashed, then restored, ran `PYTHONPATH=src:tests python3 -m unittest test_flow_adopt_split test_flow_slice test_integrate test_integrate_stack_bases`. Both legs collected 191 tests. The red leg included behavioral assertion failures, not merely missing-new-API errors; the green leg passed. Full outputs: `review-red.log` and `review-green.log`.
- Runtime: `PYTHONPATH=src python3 -m unittest discover -s tests` from `target/template` passed 2,265 tests, two skipped (`review-suite.log`). `python3 -m tests.run_root_suite` from `target` exited 77 because `/usr/bin/python3` cannot import Copier (`review-root-suite.log:7`). This is a review-host limitation, not a patch failure: the frozen root-suite log explicitly shows the render/update cases executing successfully (`gate-logs/T3-suite.log:36`, `gate-logs/T3-suite.log:54`). No shim or substituted tool was used to claim root coverage.
- Shape: from `target`, ran `python3 docs/publishing/tools/lint_docs.py` and `python3 docs/publishing/tools/render_site.py --check --out ../review-site`; both passed. `git diff --check` also passed. The production-import scan independently found the regression module importing the real package (`review-prod-path.log:1`). Instance-scoped wrapper scripts were adjudicated through their supplied logs and their available underlying checks, not treated as missing target files.
- Prior art: the brief reports an affected-path history search and no closed-unmerged work. A local history query covering every patched path returned only the synthetic base commit; `git remote -v` returned nothing (`review-prior-art.log`). The bundle therefore does not independently establish the merged/closed/rejected-work conclusion. Confirm it against the canonical repository before sign-off.

For the human live-host validation, use a disposable GitHub repository with merge commits enabled and a configured harness whose target/base is that repository's `main` and whose `driver.wave_mode` is `stack`. Brief A and C as independent file additions; brief B with `Depends on: A, C` and its own file addition. Run `pdca flow A C B`, completing the normal sign-offs, and confirm each draft PR targets `main`. Human-merge A and C using merge commits, inspect B's Files changed, update B from `main` using Update branch, and confirm only B's own change remains before human-merging B. This exercises the sibling topology rather than only the simpler one-parent chain.

Also check the actual host response after merging and deleting a prerequisite branch: run `gh pr view "$A_PR" --json state,headRefOid`, expect `MERGED` and the original head SHA, then exercise a subsequent fold in the same run. If that SHA is already carried, the fold must report “already carries” and skip it without taking unrelated base changes; if a fixup was merged after the previous fold, the next fold must carry its content through the base. The offline real-Git versions of these scenarios passed (`target/template/tests/test_integrate_stack_bases.py:364`, `target/template/tests/test_integrate_stack_bases.py:392`), but the real GitHub metadata path remains untested.

### Advisory — adversary

# Adversarial review — issue 593 (stack-mode append-only fold, real-base PRs)

Advisory only. Sources: the patched tree at `$PDCA_TARGET`, `brief.md`, `check-gates.json`, `gate-logs/`.
I re-ran the green leg myself: `tests.test_integrate_stack_bases` and `tests.test_integrate` give 54 tests, all OK.
The red leg in `gate-logs/C4-verify.log` matches the brief. One refutation landed. The other attacks failed (listed at the end).

## Findings

- NEEDS-HUMAN — `template/src/pdca_harness/integrate.py:457-475` (`_take_in_base`), reached from `:436-445` (`_gone_branch`).
  When a gone branch's merged head is not on the line, the fold merges `<base_remote>/<base>` into the line and prints "the merged work reaches … through origin/main". It never checks that the base actually holds that head, even when the head is in the clone and the check costs one `merge-base --is-ancestor`. The only guard is the base string in `publish.json` (`:437`), which the host can change after publish.
  **Reproduced** (scratch test, real git, FoldGit shape):
  1. Fold A.
  2. Push a fixup onto fix/A.
  3. Merge fix/A with `--no-ff` into `release` instead of `main` (for example, the PR's base was edited on the host), then delete fix/A.
  4. Have `merged_head` return the fixup SHA, then fold [A, B] with `{TARGET: T1}`.

  Result: the fold succeeds and prints the "reaches … through origin/main" line, but the line's `a.txt` is still `"a\n"`. The fixup is missing, and `main` does not have it either. In the never-carried variant (case-9 shape, merged into `release`), `a.txt` is not on the line at all. The next wave then builds on a base that is missing its prerequisite, with no STOP. That is exactly the failure this fold exists to prevent.
  The same path also opens on fork targets through fetch order. `_prepare_worktree` fetches `base_remote` before `origin` (`integrate.py:520`, `dict.fromkeys((base_remote, "origin", …))`). A PR that is merged, and its fork branch deleted, between those two fetches leaves a base snapshot without the merge.
  Suggested fix:
  - When `cat-file -e <head>` succeeds, require `<head>` to be an ancestor of `<base_ref>` (or of the line after the base merge), and raise otherwise.
  - Fetch the base remote last.

  This needs a human call rather than `[impl]`. Brief (ii-b) step 4 states "the base now holds that work" as a given, and the check changes the out-of-scope squash case from "merge the base" to "raise". The docs repeat the unchecked claim at `template/PCDA/quality-cycle/09-parallel-lanes.md:69` ("the base, which holds that work, is merged in").

- (Informational, not a refutation.) On the red leg, the required cases 7, 8 (deleted branch), 14b, 15 and 16/17 error with `TypeError: fold() got an unexpected keyword argument 'folded_this_run'`, `AttributeError: … merged_head` or `write_stack_base() takes 2 positional arguments` (`gate-logs/C4-verify.log:1995-2270`). They go red because the new API is missing, not because the old behaviour was observed. The brief allows this (errors in the test, not at import). The green-leg assertions are specific, not tautological:
  - `tests/test_integrate_stack_bases.py:415` checks the tip equals t2 and that the base was not merged.
  - `:383` checks the fixup content.
  - `:719` checks no `fix/U-u` branch was pushed.
  - `:702` checks `host_ci_base == t1`.

  So the C4 PASS stands.

## Attacks that did not land

- **Test realism.** The fold tests hand-write `publish.json` (`tests/test_integrate_stack_bases.py:138-160`) instead of calling the real publish. The `"base": "main"` value that `_gone_branch` relies on is tied to production by `test_a_wave_bundle_publishes_against_the_real_base` (`:649-660`, real `publish.publish`). Not a gap.
- **Tip guard false pass (`publish.py:691-727`).** A recorded tip can become an ancestor of a later run's fresh line, through a merged wave>0 PR whose branch contains that tip. In that case the late PR's diff against main is still only its own change, so the guard's permissiveness is harmless. I found no case where it lets an orphaned tip through.
- **Hold signal (`flow.py:642-665`, `:1890`).** I tried coarse mtime, a publish that fails before or at the push, `gh pr create` failing after the push, an exception after the `publish.json` write, and the no-target and dry-run paths. Every one ends up held, folded or skipped as the brief says. The exception case errs toward holding, which the brief accepts.
- **Recorded tip vs re-gate.** `pushed_tip` is read right after `fold` returns, before the re-gate (`flow.py:1906-1911`). The next fold starts from that tip with `checkout -B`, and `--is-ancestor` exit 128 raises instead of being read as "not in line" (`integrate.py:478-488`). I found no in-run push that moves the line between folds and could trip the #591 mismatch check by mistake.
- **Multi-target, dry-run and lock order.** Unchanged in substance. Dry-run never touches git.

### Advisory — code-review

# Advisory code review — issue 593 (stack-mode append-only fold, real-base PRs)

Lens: bugs the patch introduces, plus reuse / simplification / efficiency. Grounded on the
patched tree at `$PDCA_TARGET`. I found no correctness bug that needs a human or a Do
iteration. The fold, gone-branch, publish-guard and hold paths match the brief's contract.
The required cases (7, 8, 14b, 15) are real-git tests that check commit identity and pushes,
not just output text. C4 shows them red on the base and green with the fix, and T3 shows the
full suite green (2265 tests). Low-priority notes:

- `template/src/pdca_harness/publish.py:691` (`_line_tip_refusal`) repeats the
  "commit exists? then `merge-base --is-ancestor` → 0 yes / 1 no / anything else is a git
  failure" logic already in `template/src/pdca_harness/integrate.py:448` (`_carries`) and
  `:478` (`_in_line`). A direct import isn't possible (integrate imports publish, so the
  reverse would be circular). A small shared helper in a neutral module, or one in publish
  that integrate calls, would keep the two rc readings in sync. Optional cleanup, not a bug.
- `template/src/pdca_harness/merged.py:62` (`merged_head`) copies `is_merged`'s
  `gh pr view` call, its stderr message and its fail-closed parsing (`merged.py:32-57`),
  changing only the `--json` fields. A private `_pr_view(pr_url, fields) -> dict | None`
  used by both would remove the copy. The brief says `is_merged` must stay unchanged, so
  leaving the copy is defensible. The two functions also handle a missing `gh` binary
  differently: only the new one catches `OSError`.
- `template/src/pdca_harness/integrate.py:425` passes `d.name.removeprefix("issue_")` to
  `merged_head`, which looks the bundle up again with `cfg.find_bundle`, even though the
  caller already has `d`. It gives the same result. Mentioned only because a
  `merged_head(cfg, d)` signature would skip the lookup round-trip.
- Efficiency, minor: a real wave>0 publish now fetches `origin` up to three times before
  pushing: the tip guard (`publish.py:706`, `--prune`), `_host_ci_passes` when host CI is
  declared, and the plan's own `fetch` step (`publish.py:299`). This only matters on a
  slow remote. Clearer than reordering it.
- Side effect to be aware of: the fold (`integrate.py:522`) and the publish tip guard
  (`publish.py:706`) now run `git fetch --prune origin` in the user's primary target
  checkout. Before, it was a plain `fetch`. Stale remote-tracking refs (the local copies of
  branches deleted on origin) get dropped from that checkout. The brief asks for the prune
  ((ii-b)) and it is harmless in normal use. It is listed only because it changes the
  user's clone outside the harness's own worktree.
- `template/src/pdca_harness/flow.py:665`: the "pushed this run" signal compares
  `publish.json`'s `st_mtime_ns`. On a filesystem with coarse timestamps (FAT, some network
  mounts), a rewrite in the same tick as an earlier write would read as "not pushed". That
  errs toward holding the bundle, and a stale record always comes from an earlier run, so
  the window is effectively zero. No action needed.

No NEEDS-HUMAN items from this lens.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — Approve the vendored process-model changes, reconfirm the recorded no-split waiver, and confirm the affected-path prior-art search covers merged and closed/rejected work—the supplied target has one synthetic commit and no remotes, so that historical conclusion cannot be independently established here; target/template/PCDA/quality-cycle/09-parallel-lanes.md:69, brief.md:342, brief.md:368, brief.md:379, review-prior-art.log:1.
- [x] Validation — fitness-to-purpose — Decide whether the documented merge-commit/Update-branch workflow meets the milestone goal and complete its live GitHub check—real host PR rendering and deleted-head metadata were not exercised; current evidence uses real local Git with mocked gh responses; brief.md:255, target/template/tests/test_integrate_stack_bases.py:611, target/template/src/pdca_harness/merged.py:76.
- [ ] `template/src/pdca_harness/integrate.py:457-475` (`_take_in_base`), reached from `:436-445` (`_gone_branch`). When a gone branch's merged head is not on the line, the fold merges `<base_remote>/<base>` into the line and prints "the merged work reaches … through origin/main". It never checks that the base actually holds that head, even when the head is in the clone and the check costs one `merge-base --is-ancestor`. The only guard is the base string in `publish.json` (`:437`), which the host can change after publish. **Reproduced** (scratch test, real git, FoldGit shape):
- [x] **(i-a) "cut from the recorded tip" is undone whenever `[gates] host_ci` is declared, and the brief never mentions this path.** In publish, `_host_ci_passes(cfg, d, repo, "origin" if stack_branch else base_remote, checkout_base)` (`publish.py:344-346`) re-fetches and pins `checkout_base`, which is `origin/<stack-base>` at `publish.py:246`, the moving branch. Then `_pin_checkout` (`publish.py:349-350`, `:868-877`) **replaces** the `checkout -B` step with that pinned commit. If Do changes only the `checkout -B` step at `:277`, as the brief's citation range `publish.py:242-259` suggests, then on any instance with host CI a late publish is still cut from the branch as it is now. That carries later waves, which (i-a) says must never happen, and the CI gate certifies a different tree than the recorded tip. Case 14 ("K's tip is not an ancestor of fix/U") does not declare `host_ci_checks`, so it cannot catch this. The fix to the brief: make `checkout_base` itself the recorded tip SHA (so the pin and the `record["host_ci_base"]` agree with it), cite `publish.py:318-350`, and add a case-14 variant with `host_ci_checks` set.
- [x] **(iii)/(i-a) contradict (vi), and nothing says where the tip is stored.** (iii) says flow "passes the tip to `write_stack_base` for the next wave's bundles" (`write_stack_base(d, branch, tip)`). The only caller is `flow._point_at_integration` (`flow.py:694-707`), whose input is `integ: dict[tgt, str]` (branch only, built at `flow.py:1850`). Yet (vi) lists "per-target stack-base routing (`flow._point_at_integration`, …)" as **unchanged**. The Ordering note's list of `flow.py` hunks (`:1838-1860`, `:1800-1822`, `:660-690`) also leaves out `:694-707`. The brief also does not say how the tip is stored. Today `stack-base` is one line (`publish.py:604`), and three readers expect exactly the branch:
- [x] **(iv) gives the outcome of "no branch was pushed in this run" but no observable signal for it, and the existing signals cannot tell the cases apart.** The brief requires two things. A bundle with a stale `publish.json` from an earlier run whose re-publish fails before the push must be **held**. A bundle whose push succeeded but whose `gh pr create` failed must be **folded**. Both return rc 1 from `publish.publish` (`publish.py:361`, `:399-400`). `_publish_bundle` throws the rc away (`flow.py:647-653`, returns `None`). The record's only time field is `"date": today` (`publish.py:385`), which is day-granular, so a same-day earlier run looks fresh. Unless the brief names the mechanism, Do will invent one; candidates are a run-scoped set that `_publish_bundle` fills, or comparing `publish.json` before and after the call. Case 18's variants then test whatever Do chose rather than an agreed contract. The fix to the brief: state the signal, and that `_publish_bundle` must return or record it. That is another `flow.py` hunk (`:641-653`) missing from the Ordering note's overlap list.
- [ ] **Scope is several logical changes, not one fix, and the planned split stop is waived.** Reading criteria (i-a), (i-b), (ii), (ii-b), (iii), (iv), (vii) and (viii), the brief bundles six things: a publish retarget, a new publish refusal guard (i-b), a rewrite of the fold to merge real branches, a new `merged.merged_head` host query, a flow-level partial-failure hold that changes STOP semantics, and a doc sweep across 7 files including the vendored model spec. The Notes record "No split, by the human's choice … patch ~148 KB, threshold 125 KB". The "Self-test" justifies coupling retarget with append-only folding. It does not justify carrying (iv) (hold instead of STOP) or (i-b) in the same patch: each could land after the core and be tested on its own. I raise this only so the human re-confirms the waiver knowing that (iv) and (i-b) can be separated. The planner cannot resolve it alone.
- [ ] size backstop — this slice is behaving oversized: patch is 174 KB (threshold 125 KB). Recommend answering `iterate-plan` at sign-off and authoring the split in the re-plan (`pdca split`), rather than `iterate-do`: a slice that is too big yields implementation-shaped findings every round, and splitting authors briefs, which is Plan's beat.

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
- Iteration delta (if iterating): Rejected for one gap (adversary §6 item 3): when a published branch is gone and its merged head is not on the line, `_take_in_base` (integrate.py:457-475, via `_gone_branch` :436-445) merges `<base_remote>/<base>` in and claims the base carries the work without checking. A PR merged into another branch (e.g. its base edited to `release` on the host) silently drops the prerequisite. Change next: before merging the base in, run `git merge-base --is-ancestor <merged head> <base_ref>`. rc 0 → merge the base as today. rc 1, or the head commit not in the clone → raise IntegrationError naming the bundle, PR, head SHA and base ("merged somewhere other than <base>"). Any other rc → git-step failure (as `_in_line`). Squash/rebase merges now stop here too; that is fine (out of scope). Also fetch the base remote LAST in `_prepare_worktree` (integrate.py:520) so a merge+delete between fetches can't leave a stale base snapshot. Update 09-parallel-lanes.md:69 to say the base is checked to hold the merged head, else the fold stops. Add regression tests from the adversary repro: (a) fixup pushed to fix/A, fix/A merged --no-ff into `release` not main, deleted → fold raises, nothing pushed; (b) case-9 never-carried shape merged into `release` → raises. Existing merged-into-main cases must stay green. Keep everything else from this round as is; the rest of the review passed. Already settled this round: T5 judgment approved (vendored model edits, prior art); live GitHub validation deferred to a follow-up (§10).
- By / date: Eduard Ralph / 2026-10-02

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 4 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
- issue_593: live GitHub validation of the stack workflow (sibling A+C→B, merge commits, Update branch, `gh pr view --json state,headRefOid` after merge+delete) deferred to a follow-up.
