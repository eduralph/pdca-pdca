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

Review issue #593: preserve real PR commits on append-only stack integration lines, target the real base, and refuse deleted prerequisites whose merged head is absent from that base.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The carry-forward explicitly requires refusing a wrong-base merge and fetching the base last; it supersedes the earlier missing-head fallback and gives falsifiable outcomes (brief.md:397; target/template/tests/test_integrate_stack_bases.py:474). |
| C2 Reproduction (red pre-fix) | PASS | Stashing production changes while retaining all four affected test modules reproduces 27 assertion failures and 31 errors in 195 tests, including lost PR ancestry and the wrong PR base (reviewer-evidence/red.log:1127; target/template/tests/test_integrate_stack_bases.py:262). |
| C3 Change | PASS | A deleted prerequisite cannot silently lose work through an unrelated base: ancestry is checked before the base is taken in, with bundle, PR, head and base in the refusal; branch remotes are fetched before the base (target/template/src/pdca_harness/integrate.py:451; target/template/src/pdca_harness/integrate.py:538). |
| C4 Verification (red→green) | PASS | Restoring production makes all 195 affected-module tests pass; the two wrong-base cases assert the remote line remains unchanged, and independently bypassing only the new check makes both fail (reviewer-evidence/green.log:495; reviewer-evidence/base-check-causality.log:27; target/template/tests/test_integrate_stack_bases.py:493). |
| C5 Causal adequacy | PASS | Commit ancestry establishes whether the selected base actually carries the missing prerequisite; this corrects the false inference from merged status, without an optional-capability probe or load-time workaround (target/template/src/pdca_harness/integrate.py:437; target/template/src/pdca_harness/integrate.py:451; reviewer-evidence/production-scan.log:1). |
| T1 Structure | PASS | Shared candidate/ref resolution keeps the publish hold aligned with what the fold carries; sorted target locking and the fold/re-gate lock scope remain intact (target/template/src/pdca_harness/integrate.py:132; target/template/src/pdca_harness/integrate.py:310; target/template/src/pdca_harness/flow.py:1900). |
| T2 Shape | PASS | Independent docs lint, 22-page render/link audit and git diff whitespace check pass; the user contract describes wrong-base refusal and the multi-merge-base diff limitation (reviewer-evidence/docs-lint.log:1; reviewer-evidence/docs-render.log:3; target/docs/07-crosscutting.md:651; target/docs/07-crosscutting.md:664). |
| T3 Runtime | PASS | Independent offline suite: 2,269 tests pass, two skipped; frozen root-suite evidence: 24 tests pass. Local root-suite execution lacks importable Copier, so its skipped cases supply no additional verification (reviewer-evidence/suite.log:1796; gate-logs/T3-suite.log:54; reviewer-evidence/root-suite.log:6). |
| T4 Contribution | N/A | The contribution gate is deferred because PR text is drafted after Check; its substantive audit is required at publish (gate-logs/T4-contribution.log:10). |
| T5 Judgment | NEEDS-HUMAN | Carry forward the recorded approval of vendored-model edits, the no-split scope decision and path-based prior art — those remain human judgments; this one-commit target cannot independently establish merged and closed/rejected PR history (brief.md:342; brief.md:368; brief.md:397; target/template/PCDA/quality-cycle/09-parallel-lanes.md:69). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Retain or discharge the explicitly deferred live-GitHub follow-up — real gh metadata and GitHub Files changed/Update branch behavior were not exercised, so host behavior rests on mocked responses and local Git topologies (brief.md:255; brief.md:397; target/template/src/pdca_harness/merged.py:76). |

No grounded patch defect found. This review is advisory; the human-only rows do not change deterministic acceptance gates. The brief records that T5 was already approved and live-host validation deferred to a follow-up; these rows preserve those decisions and their evidence limits, rather than claiming fresh host verification.

Independent verification used the disposable target supplied by the harness. I stashed only `template/src`, retained the four changed test modules for the red leg, restored the stash, and reran the same tests. Both tracked changes and the new test file match the supplied patch after restoration. The focused counterfactual changed behavior only in memory: returning true for the new target-base ancestry check yields two assertion failures and zero errors. The normal implementation passed those cases in both the affected-module and full-suite runs. No implementation was edited.

The independent test commands were `PYTHONPATH=target/template/src:target/template/tests python3 -m unittest test_flow_adopt_split test_flow_slice test_integrate test_integrate_stack_bases`, and, from `target/template`, `PYTHONPATH=src python3 -m unittest discover -s tests`. Temporary files were confined through `TMPDIR` under `reviewer-evidence/`. I also reran the production-import scanner and the docs workflow's lint/render commands. All six frozen gate logs were read, including the deferred contribution row. The unavailable instance-scoped wrappers are not treated as missing evidence. Copier is unavailable to the local interpreter, but the frozen log explicitly records executed render/update tests and a passing 24-test root suite; this is a local toolchain limitation, not a patch failure.

The prior-art section records searches by affected source path, merged-history results and no closed-unmerged work. A fresh path-scoped `git log --all` on the supplied target returned only its synthetic pre-fix snapshot, and `git remote -v` returned no remotes. Therefore that historical conclusion is carried from the brief's recorded human approval, not presented as independently reproduced.

For the deferred live-host follow-up, use a disposable GitHub repository with merge commits enabled:

1. Configure a rendered instance for that repository with `wave_mode = "stack"`; brief independent A and C, then B with `Depends on: A, C`. Run `pdca flow A C B`. Confirm each PR's `baseRefName` is the real base using `gh pr view <url> --json baseRefName,state,headRefOid`.
2. Merge A and C with merge commits as the human maintainer. Inspect B's Files changed, use Update branch, and confirm only B's intended change remains before merging B. Local Git tests already exercise this multiple-merge-base topology; the remaining observation is GitHub's presentation and update behavior.
3. Exercise a later fold after a prerequisite receives a fixup, merges and has its branch deleted. Verify the real `gh pr view <url> --json state,headRefOid` response and preservation of the fixup. Repeat with that PR merged into `release` instead of `main`: the fold must refuse, name the bundle/PR/head/base and leave the remote integration tip unchanged. The offline regressions at `target/template/tests/test_integrate_stack_bases.py:474` and `:495` already verify the latter refusal using real Git and mocked host metadata.

### Advisory — adversary

# Adversarial review — issue 593, iteration 7 (round-6 carry-forward)

Scope: this round's change. That is the base-ancestry check before `_take_in_base`
(`template/src/pdca_harness/integrate.py:451-459`), fetching the base remote last
(`integrate.py:537-542`), the doc line (`template/PCDA/quality-cycle/09-parallel-lanes.md:69`),
and regression tests (a)/(b). The rest of the patch passed review last round, and I did not
re-attack it.

## What I tried and could not break

- **Evidence is real, not a tautology.** C4's red leg only reverts to `main`, where every new
  test errors because `merged_head` is missing. That alone does not prove the new tests catch
  round 6's bug. So I removed only the new base check (`integrate.py:451-458`) in a scratch copy:
  `test_a_fixup_merged_into_another_branch_stops_the_fold` (a),
  `test_a_branch_never_carried_and_merged_into_another_branch_stops_the_fold` (b),
  `test_a_failing_base_check_is_a_git_step_failure` and
  `test_a_merged_head_missing_from_the_clone_is_not_carried` all go red. Next I put the base
  remote back first in the fetch loop (`integrate.py:538`):
  `test_a_pr_merged_and_deleted_between_the_folds_fetches_is_still_carried` goes red with
  "merged somewhere other than upstream/main". Both changes have tests that fail without them,
  and the tests run the production `integrate.fold` against a real bare origin.
- **Extra real-git cases (my own, not in the suite), all behave correctly:** a fixup merged into
  `release` that later reaches `main` folds and carries the fixup. A fork (`base_remote =
  upstream`) whose PR merged upstream takes `upstream/main` in. A fork PR merged into the fork's
  own `main` instead of upstream stops the fold and pushes nothing.
- **Error shape matches the carry-forward:** the message names the bundle, PR URL, full head SHA
  and `<base_remote>/<base>` (`integrate.py:452-458`). A non-0/1 exit from `--is-ancestor` is a
  git-step failure through `_in_line` (`integrate.py:497-503`).
- **Gates:** T3's log shows 2269 driver tests OK. I re-ran `test_integrate`, `test_flow_slice`,
  `test_flow_adopt_split`, `test_verify_base` and `test_integrate_stack_bases` here: all green.

## Findings

- NEEDS-HUMAN — `template/src/pdca_harness/integrate.py:451-459` (and the docs at
  `template/PCDA/quality-cycle/09-parallel-lanes.md:69`, `integrate.py:36-37`): the check proves
  the base has the merged head **by ancestry**, not that the base still has the work. Concrete
  case, reproduced on real git: fold [A] → T1; push a fixup to fix/A; merge fix/A into `main`;
  delete fix/A; then `git revert -m 1` that merge on `main`; fold [A, B] with `{TARGET: T1}`. The
  fold passes the check, merges `main` in, and the pushed line ends up with
  `['b.txt', 'base.txt']`. **A's original change is gone too**, not only the fixup. B, which
  depends on A, then builds without A, and stderr says "the merged work reaches
  pdca-integration/main through origin/main", which is false. The builder did exactly what the
  carry-forward asked (`merge-base --is-ancestor`), so this is not an implementation slip. It is
  a scope question: is "the human reverted the prerequisite on the base" a case the fold should
  stop on (for example, by checking that the line before the base merge and the line after it
  agree on the bundle's own paths), or accepted and documented? The same thing happens when a
  base merge brings in a revert of any *other* bundle already on the line. Low likelihood, but
  it is the same failure class as round 6 §6 item 3 (a prerequisite silently dropped), and the
  stderr line misreports it.

- Not a defect, noted for the record — `integrate.py:443-450`: a gone branch whose record `base`
  is not the fold's base (a legacy `Stacks on:` PR, `base = fix/P-…`) stops the fold **before**
  the new base check runs. Now that the base check exists, this early stop only adds false stops.
  Example: L merged into fix/P, fix/P then merged into `main`, fix/L deleted. `main` has L's head,
  but the fold still raises "a PR against fix/P…, not main". It stops safely rather than losing
  work, and stack mode reaches it only for a wave-0 bundle stacked on an earlier run's parent. I
  can't tell from my inputs whether an earlier round settled this, so I am not routing it.

- Not a defect, noted for the record — `integrate.py:466-467`: `_carries` reads any non-zero
  `git cat-file -e` exit as "this clone does not have the commit". Git returns 128 both for a
  missing commit and for a broken repo or worktree (checked here). So a real git failure at that
  step is reported as "merged somewhere other than <base>" instead of "a git step failed". The
  fold still stops and pushes nothing, and earlier git steps in the same worktree would normally
  have failed first. Only the wording is wrong.

## Verdict

I tried to refute the round-6 fix three ways: tests that would pass without it, a fetch-order
race, and fork vs own-repo base mix-ups. I could not. The only concrete hole I found is the
revert-on-base case above, and that is a gap in the contract as written, not in how it was built.

### Advisory — code-review

# Advisory code review — issue 593 (stack-mode append-only fold, real-base PRs)

Lens: correctness bugs the patch adds, plus reuse / simplification / efficiency. Grounded on
the patched tree at `$PDCA_TARGET`. Gates: C4 red→green, T3 suite green (2269 tests), docs
gates clean.

The round-6 carry-forward is done as asked. `_gone_branch` now checks that the base has the
merged head before taking the base in (`template/src/pdca_harness/integrate.py:451-458`). Git
exit codes other than 0/1 are raised as failed git steps (`integrate.py:497-503`). The base
remote is fetched last (`integrate.py:537-542`). The two `release` repro tests exist and check
that nothing was pushed (`template/tests/test_integrate_stack_bases.py:474-511`). The
fetch-order test would fail if the order were reversed (`test_integrate_stack_bases.py:541-585`).
I found no correctness bug in the fold, the publish cut-point/guard, or `merged_head`. Findings
are minor:

- NEEDS-HUMAN [impl] — The hold does not always cascade "through another" bundle, as brief (iv)
  requires. `template/src/pdca_harness/flow.py:712-713` skips a direct dependent D of a held
  bundle U, but D is not added to `held`. The cascade then relies on D never reaching COMPLETE
  (`flow.py:710`). If D was already COMPLETE on disk when the run started (a resumed batch), a
  later E that depends on D passes `_runnable` and builds on a line that has neither U nor D.
  The not-COMPLETE skip already had this narrow gap, but the new `held` path inherits it. Fix:
  add each bundle `_runnable` skips for a held prerequisite to `held_unpushed`, or check `held`
  through the whole dependency chain. A flow test for U → D(pre-COMPLETE) → E would pin it.
- Reuse (minor, no action needed): `_gone_branch` passes `d.name.removeprefix("issue_")` to
  `merged.merged_head` (`integrate.py:431`), which looks the bundle up again through
  `cfg.find_bundle` and re-reads `publish.json` (`merged.py:71`). `_gone_branch` then reads the
  same record a third time (`integrate.py:442`). Passing the record or path through would be
  simpler. `merged_head`'s `gh pr view` / fail-closed body (`merged.py:72-91`) also copies
  `is_merged`'s (`merged.py:46-58`). The brief froze `is_merged`, so a shared `_pr_view` helper
  can wait.
- Efficiency (minor): a wave>0 publish with `host_ci_checks` now fetches `origin` three times
  before pushing: the guard's `fetch --prune` (`publish.py` `_line_tip_refusal`), then
  `_pinned_base` (`publish.py:956`), then the plan's own fetch step. This is harmless and keeps
  each step self-contained. Noted only.

Nothing else found on either lens.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — Carry forward the recorded approval of vendored-model edits, the no-split scope decision and path-based prior art — those remain human judgments; this one-commit target cannot independently establish merged and closed/rejected PR history (brief.md:342; brief.md:368; brief.md:397; target/template/PCDA/quality-cycle/09-parallel-lanes.md:69).
- [x] Validation — fitness-to-purpose — Retain or discharge the explicitly deferred live-GitHub follow-up — real gh metadata and GitHub Files changed/Update branch behavior were not exercised, so host behavior rests on mocked responses and local Git topologies (brief.md:255; brief.md:397; target/template/src/pdca_harness/merged.py:76).
- [x] `template/src/pdca_harness/integrate.py:451-459` (and the docs at `template/PCDA/quality-cycle/09-parallel-lanes.md:69`, `integrate.py:36-37`): the check proves the base has the merged head **by ancestry**, not that the base still has the work. Concrete case, reproduced on real git: fold [A] → T1; push a fixup to fix/A; merge fix/A into `main`; delete fix/A; then `git revert -m 1` that merge on `main`; fold [A, B] with `{TARGET: T1}`. The fold passes the check, merges `main` in, and the pushed line ends up with `['b.txt', 'base.txt']`. **A's original change is gone too**, not only the fixup. B, which depends on A, then builds without A, and stderr says "the merged work reaches pdca-integration/main through origin/main", which is false. The builder did exactly what the carry-forward asked (`merge-base --is-ancestor`), so this is not an implementation slip. It is a scope question: is "the human reverted the prerequisite on the base" a case the fold should stop on (for example, by checking that the line before the base merge and the line after it agree on the bundle's own paths), or accepted and documented? The same thing happens when a base merge brings in a revert of any *other* bundle already on the line. Low likelihood, but it is the same failure class as round 6 §6 item 3 (a prerequisite silently dropped), and the stderr line misreports it.
- [x] The hold does not always cascade "through another" bundle, as brief (iv) requires. `template/src/pdca_harness/flow.py:712-713` skips a direct dependent D of a held bundle U, but D is not added to `held`. The cascade then relies on D never reaching COMPLETE (`flow.py:710`). If D was already COMPLETE on disk when the run started (a resumed batch), a later E that depends on D passes `_runnable` and builds on a line that has neither U nor D. The not-COMPLETE skip already had this narrow gap, but the new `held` path inherits it. Fix: add each bundle `_runnable` skips for a held prerequisite to `held_unpushed`, or check `held` through the whole dependency chain. A flow test for U → D(pre-COMPLETE) → E would pin it.
- [x] **(i-a) "cut from the recorded tip" is undone whenever `[gates] host_ci` is declared, and the brief never mentions this path.** In publish, `_host_ci_passes(cfg, d, repo, "origin" if stack_branch else base_remote, checkout_base)` (`publish.py:344-346`) re-fetches and pins `checkout_base`, which is `origin/<stack-base>` at `publish.py:246`, the moving branch. Then `_pin_checkout` (`publish.py:349-350`, `:868-877`) **replaces** the `checkout -B` step with that pinned commit. If Do changes only the `checkout -B` step at `:277`, as the brief's citation range `publish.py:242-259` suggests, then on any instance with host CI a late publish is still cut from the branch as it is now. That carries later waves, which (i-a) says must never happen, and the CI gate certifies a different tree than the recorded tip. Case 14 ("K's tip is not an ancestor of fix/U") does not declare `host_ci_checks`, so it cannot catch this. The fix to the brief: make `checkout_base` itself the recorded tip SHA (so the pin and the `record["host_ci_base"]` agree with it), cite `publish.py:318-350`, and add a case-14 variant with `host_ci_checks` set.
- [x] **(iii)/(i-a) contradict (vi), and nothing says where the tip is stored.** (iii) says flow "passes the tip to `write_stack_base` for the next wave's bundles" (`write_stack_base(d, branch, tip)`). The only caller is `flow._point_at_integration` (`flow.py:694-707`), whose input is `integ: dict[tgt, str]` (branch only, built at `flow.py:1850`). Yet (vi) lists "per-target stack-base routing (`flow._point_at_integration`, …)" as **unchanged**. The Ordering note's list of `flow.py` hunks (`:1838-1860`, `:1800-1822`, `:660-690`) also leaves out `:694-707`. The brief also does not say how the tip is stored. Today `stack-base` is one line (`publish.py:604`), and three readers expect exactly the branch:
- [x] **(iv) gives the outcome of "no branch was pushed in this run" but no observable signal for it, and the existing signals cannot tell the cases apart.** The brief requires two things. A bundle with a stale `publish.json` from an earlier run whose re-publish fails before the push must be **held**. A bundle whose push succeeded but whose `gh pr create` failed must be **folded**. Both return rc 1 from `publish.publish` (`publish.py:361`, `:399-400`). `_publish_bundle` throws the rc away (`flow.py:647-653`, returns `None`). The record's only time field is `"date": today` (`publish.py:385`), which is day-granular, so a same-day earlier run looks fresh. Unless the brief names the mechanism, Do will invent one; candidates are a run-scoped set that `_publish_bundle` fills, or comparing `publish.json` before and after the call. Case 18's variants then test whatever Do chose rather than an agreed contract. The fix to the brief: state the signal, and that `_publish_bundle` must return or record it. That is another `flow.py` hunk (`:641-653`) missing from the Ordering note's overlap list.
- [x] **Scope is several logical changes, not one fix, and the planned split stop is waived.** Reading criteria (i-a), (i-b), (ii), (ii-b), (iii), (iv), (vii) and (viii), the brief bundles six things: a publish retarget, a new publish refusal guard (i-b), a rewrite of the fold to merge real branches, a new `merged.merged_head` host query, a flow-level partial-failure hold that changes STOP semantics, and a doc sweep across 7 files including the vendored model spec. The Notes record "No split, by the human's choice … patch ~148 KB, threshold 125 KB". The "Self-test" justifies coupling retarget with append-only folding. It does not justify carrying (iv) (hold instead of STOP) or (i-b) in the same patch: each could land after the core and be tested on its own. I raise this only so the human re-confirms the waiver knowing that (iv) and (i-b) can be separated. The planner cannot resolve it alone.
- [x] size backstop — this slice is behaving oversized: patch is 184 KB (threshold 125 KB). Recommend answering `iterate-plan` at sign-off and authoring the split in the re-plan (`pdca split`), rather than `iterate-do`: a slice that is too big yields implementation-shaped findings every round, and splitting authors briefs, which is Plan's beat.

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: merged-wider
- Iteration delta (if iterating):
- By / date: Eduard Ralph / 2026-10-02

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 4 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
