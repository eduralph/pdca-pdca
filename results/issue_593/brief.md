# Brief — issue 593 / stack-mode-append-only-fold-real-base-prs

> The Plan artifact (docs 02 §PLAN). Do reads ONLY this file.
> Iteration 6, re-planned after round 5 (archived in `iteration-v5/`). The core design has been
> accepted at sign-off since round 2 and stays. This brief merges everything rounds 2–5 settled
> into one contract, and settles the three design questions round 5's sign-off sent back
> (section "Round-5 design decisions" below). **Start from `iteration-v5/patch.diff`**: it is
> correct apart from the gone-branch path, which (ii-b) replaces, and the publish guard (i-b),
> which is new.

- **Slug:** stack-mode-append-only-fold-real-base-prs
- **Defect:** Two defects in `[driver].wave_mode = "stack"` (found by review of
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
- **Success criterion:** With the patch, under `wave_mode = "stack"`:
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
- **Falsifiability:** RED is reachable offline on the base toolchain (stdlib Python ≥ 3.11 +
  git; no network, no `gh`, whose calls are patched). `tests/test_integrate.py:105-165`
  (`FoldGit`) already folds against a real bare `origin` + primary checkout, and round 5's C4
  went red on this gate with the same test file (`iteration-v5/gate-logs/C4-verify.log`). On
  `main`: the fold re-applies patches and force-pushes every time, so ancestry (ii/iii), the
  no-force push (iii), chain shrink (v), the hold (iv; `main` stops at the fold with "did not
  integrate … STOPPING") and the `--base main` publish (i-a; `main` prints `--base
  pdca-integration/main`) are all red. The new (ii-b) and (i-b) cases are red on `main` too,
  because `main`'s fold has no gone-branch path and its publish has no recorded tip. They are
  also red against round 5's patch: the (ii-b) repro gets a needless STOP and the fixup case
  loses the fixup, as reproduced at round-5 Check (`iteration-v5/SUMMARY.md` §6 items 3–4).
- **Invariant to restore:** In stack mode, within one run, no integration-line push rewrites a
  commit an open PR's base or head depends on; every PR the harness opens targets a branch that
  reaches the real target when merged; and the line carries each accepted bundle's PR as it
  finally merged or currently stands, decided by commit identity, never by message text. So
  merging the PR stack bottom-up lands every wave on the target with no step outside the PRs,
  and within one run only that run's work enters its line. Source: internal project rule
  (Tier C), the stack-mode promise in `template/PCDA/quality-cycle/09-parallel-lanes.md:57,69`
  ("a dependent batch completes in one run as a reviewable PR stack the human merges
  bottom-up") and `docs/07-crosscutting.md:642-647`; DCO on every commit a PR carries (#405,
  `integrate.py:218-222`). Limits, stated so sign-off can check them: the run's first fold of a
  target replaces an earlier run's line (cross-run resume is #616); publish's
  `--force-with-lease` re-push of a rebuilt bundle's branch (`publish.py:289-296`, #108) is
  outside the invariant. Self-test: neither half alone satisfies it. Retargeting without
  folding the real branches leaves dependents' diffs that never shrink, on lines rebuilt under
  them; append-only folding without retargeting leaves wave 1+ merging into the integration
  branch.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Ordering note:** No `Depends on` / `Conflicts with`. This batch (582, 589, 593, 597) runs as
  ONE wave, because this very bug is in this instance's driver; 582, 589 and 597 are already
  through Check and `main` is still `24c7f83`. #616 (cross-run resume) depends on 593 and is not
  in this batch. File overlap: 593 owns `integrate.py`, `publish.py` and `merged.py` (new
  function only). It edits `flow.py` at the fold call (`:1838-1860`), the publish loop
  (`:1800-1822`), `_publish_bundle` (`:641-653`), `_runnable` (`:660-690`) and
  `_point_at_integration` (`:694-707`); 597 edits `flow.py` only in the intake
  (`:1104-1108`, `:1925-1940`, `:2064-2104`); 589 only `cli._flow` (`cli.py:637-660`), away from
  593's `cli.py:1058-1061` comment; 582 edits `template/pdca.toml.jinja:144-151`, 593 `:115-119`
  and `:176`; 593's `drift.py` / `gates.py` edits are docstring/comment only. Separate hunks
  throughout.
- **Surfaces:** data
- **Difficulty:** high
- **Scope:** Restore the invariant for stack mode per (i)–(viii): wave>0 PRs open against the
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
- **Repro instruction:** As in Falsifiability. End-to-end shape the unit tests stand in for: a
  three-wave own-repo batch A → B → C (`Depends on` chain) under `wave_mode = "stack"`. After
  wave 1's fold, B's open PR (base `pdca-integration/main`) holds its own change as a different
  commit and goes empty/conflicting, and B's and C's PRs merged bottom-up land in
  `pdca-integration/main`, never in `main`.
- **External dependencies:** none for Do and the gates (git is in the base toolchain; no network;
  `gh` is patched in every test). A live-host check is owed at sign-off and is not a Do
  dependency: on a disposable GitHub repo, put A and C in wave 0 and B on both; merge A and C
  with merge commits, look at B's Files changed, use "Update branch", then merge B; and confirm a
  merged prerequisite whose branch was deleted is recognised through the real `gh pr view
  --json state,headRefOid` path.
- **Test file:** `template/tests/test_integrate_stack_bases.py` (new), with flow-level cases in
  `template/tests/test_flow_slice.py`. Round 5's versions of both are the starting point: keep
  their passing cases, replace the subject-match cases. Real-git cases use the `FoldGit` shape
  (`tests/test_integrate.py:105-165`: bare origin, `git config user.email/user.name`,
  `commit.gpgsign false`). Import modules only (`from pdca_harness import integrate, publish,
  flow, merged`), never a symbol the fix adds; patch new functions with
  `mock.patch.object(merged, "merged_head", create=True)` so the red leg fails or errors in the
  test, never at import (a module that fails to import is PDCA-UNVERIFIABLE, not red). Cases
  that must exist (numbering is for the build notes only):
  1. Within-run append-only: fold `[A]`, then `[A, B]` with no keyword against a
     `receive.denyNonFastForwards` origin; T1 and A's tip are ancestors of the new tip.
  2. No force on a continuing fold (spy `integrate._git`; no `--force` / `--force-with-lease`).
  3. A new run's first fold (`folded_this_run={}`) over an old line starts from `origin/main`.
  4. Concurrent mismatch → `IntegrationError`, origin untouched.
  5. `"stacked"` record merges `upstream/feat`, not origin's same-named `feat`.
  6. Unpublished bundle passed to `fold` (not dry-run) → `IntegrationError` before any git step.
  7. **Reviewer/adversary repro (round 5 §6 item 3), required:** waves {A} → {B dep A, C}. Fold
     [A] → T1; publish B and C from T1; fold [A,B,C] with `{TARGET: T1}` → T2. Merge fix/A, then
     fix/B into origin's main with `--no-ff`, delete both branches, land an unrelated
     conflicting `c.txt` change on main. `merged_head` patched to return each branch's real
     merged tip. Fold [A,B,C] with `{TARGET: T2}` succeeds, does not merge the base, and prints
     the "already carries" line for A and B.
  8. **Fixup after fold (round 5 §6 item 4), required:** fold [A] → T1; push a fixup to fix/A
     (`a.txt` → "a, after review"); merge fix/A into main, delete it; `merged_head` returns the
     fixup SHA. Fold [A, B] with `{TARGET: T1}`: the line's `a.txt` is "a, after review".
     Same with fix/A NOT deleted: the fold merges its new tip.
  9. Merged-and-gone, never carried (`folded_this_run={TARGET: T}` where T lacks A): the base is
     merged in and A's content is on the line.
  10. Gone, `merged_head` returns `None` → `IntegrationError` naming the ref. Gone `"stacked"`
      record whose head is not on the line → `IntegrationError`; whose head is on the line →
      skipped.
  11. Merged head SHA not present in the local clone → treated as not carried (base merged in),
      no exception.
  12. Chain shrink (v): fold [A], cut + publish B from the line, merge A into main with `--no-ff`;
      `git diff main...B --name-only` is only B's file.
  13. Multiple merge bases (v): wave 0 = {A, Z}, B depends on A only; after A and Z merge,
      `git merge-base --all main B` gives two commits; after merging main into B, `main...B` is
      only B's file. Same pinned for the base-moved-before-first-fold case.
  14. Publish (i-a): wave>0 dry-run prints `--base main`; with both `Stacks on:` and a
      `stack-base` → `--base main`; fork unchanged; a real publish cuts from the recorded tip
      (waves {A} → {U, J} → {K}, U's publish fails, later publish of U: K's tip is not an
      ancestor of fix/U). **14b, required:** the same late publish of U with `host_ci_checks`
      declared (a command that exits 0): fix/U's parent is the recorded tip, K's tip is not an
      ancestor of fix/U, and `publish.json`'s `host_ci_base` equals the recorded tip.
      **14c:** `write_stack_base(d, br, tip)` then `read_stack_base(d) == br` and
      `read_stack_base_tip(d) == tip`; `write_stack_base(d, br)` removes a prior tip file;
      `clear_stack_base` removes both.
  15. **Publish guard (i-b), required:** record a tip, then force-push a fresh unrelated line to
      `origin/<stack-base>`; a real `publish.publish` refuses with rc ≠ 0, names #616, and
      pushes nothing (origin has no `fix/<U>` branch).
  16. Flow, ≥ 3 waves, non-dry: the first fold gets `folded_this_run == {}`, the second gets
      `{(repo, base): <that worktree's HEAD>}`; on a real origin the line has exactly one
      `pdca-integrate: <first bundle>` merge commit.
  17. Flow, ≥ 3 waves, dry-run: second fold gets the target listed (value `None`); output shows
      "start" then "continue".
  18. Flow hold (iv): wave 0 = {U, I}, wave 1 = {D dep U, J dep I}, U pushes no branch → fold gets
      only I, D skipped naming U, J built, no "STOPPING". Variants: U has a stale
      `publish.json` from an earlier run and its re-publish fails → held, old branch not folded;
      U's branch pushed but `gh pr create` failed → folded, D built (both variants on the same
      day's `today`, the stale record's mtime set back). A no-target patched bundle is not held.
  19. Dry-run fold of a bare bundle (no `publish.json`): no error, prints
      `origin/<publish._branch_name(...)>`; with `folded_this_run` omitted prints the "continue
      if origin has it" line; `subprocess.run` never called.
  20. `merged.merged_head`: `gh` returns `{"state":"MERGED","headRefOid":"abc"}` → `"abc"`;
      `OPEN` → `None`; non-zero rc or bad JSON → `None`; `is_merged` unchanged.

  Existing `test_integrate.py` tests that fold bare `patch.diff`s may be updated to the new
  contract. The gate runs every test module the patch touches, on both legs.
- **Citations expected:** Do must cite path:line on the target branch for every change. Centre:
  `integrate.fold` (`integrate.py:132-230`), `_prepare_worktree` (`integrate.py:232-246`), the
  `pr_base` and cut-point choice in `publish.publish` (`publish.py:242-259`) and the host-CI pin
  that must agree with it (`publish.py:318-350`, `_pin_checkout` `:868-877`), the stack-base
  helpers (`publish.py:598-647`), `_point_at_integration` (`flow.py:694-707`), `_publish_bundle`
  (`flow.py:641-653`), `merged.py:28-55` (new `merged_head` next to `is_merged`), the
  fold call and publish loop in `flow` (`flow.py:1800-1860`), `flow._runnable`
  (`flow.py:660-690`). Peer callsites: read a published record the way
  `publish._stack_base_branch` reads a `Stacks on` parent's (`publish.py:632-647`, via
  `_publish_record` `:590-598`); call `gh` and fail closed exactly as `merged.is_merged` does
  (`merged.py:46-55`); hold dependents by mirroring `_runnable`'s not-COMPLETE skip, which
  already cascades; signed-off commits as at `integrate.py:218-222` / `publish.py:285-288`;
  error shape as at `integrate.py:211-216`.
- **Prior-art check (triage cycles):** By path, on origin/main `24c7f83` (unchanged since
  iteration 1, re-checked 2026-10-03). `git -C ../pdca-harness log --oneline origin/main --
  template/src/pdca_harness/integrate.py`: `cb52d06` (#405, signs off the fold's commits, a
  patch over this defect's DCO symptom), then the #297 lock/sweep rounds. `publish.py`:
  `44e91d9`, `1e647be` (#411), `e79d109`, `9ecbb01`, `b5e58ba`; none changes the stack-mode PR
  base. `merged.py`: only asks `gh` for `state`. Closed-unmerged PRs on these paths: none. No
  open PR. Rounds 1–5 were not published. Related open issues: #591, #463, #616 (depends on
  this). The fix is carried downstream on getwyrd/wyrd-pdca as an instance delta. Result: not
  fixed upstream, not in flight.
- **Disposition hint:** likely-fix

## Round-5 design decisions (settled with the human, 2026-10-03)

1. **How the fold knows a merged, deleted prerequisite is already carried:** by the merged PR's
   head SHA (`gh pr view --json state,headRefOid`), tested for ancestry against the line (ii-b).
   No commit-message matching and no `<base>..HEAD` range anywhere. Rejected: "the flow passes
   the names it folded this run" — it answers this question but not (2), and drops a fixup.
2. **Commits pushed straight onto a stack PR branch after the fold carried it:** in scope. A
   live branch's new tip is merged on the next fold; a merged-and-deleted one whose final head
   is not on the line brings its work in through the base (ii-b.4).
3. **Cross-run cases:** a late publish whose recorded tip is no longer on the line **refuses**
   here (i-b). Building/verifying a hand-re-driven held bundle on the grown line goes to #616;
   only the drift docstring is corrected here (viii).

## Notes for the human (not parsed)

- Edits `template/PCDA/quality-cycle/09-parallel-lanes.md` and `08-glossary.md`, the vendored
  model spec, which is NEEDS-HUMAN at Check by this project's rule (INTEGRATION §4).
- Earlier Plan decisions (2026-10-02) stand: the goal is one `pdca flow` per milestone with
  sign-off as the only planned stop; unpublished accepted bundle → hold its dependents, keep
  going; `Onto branch` records merge the real remote's PR branch; concurrent run → refuse on tip
  mismatch (#591 for the rest); sibling diff → document "Update branch", don't change the fold.
- **No split**, by the human's choice at round-5 sign-off; the size backstop (patch ~148 KB,
  threshold 125 KB) is set aside on purpose.

Plan-review response: findings 1–3 (host-CI pin, tip storage + `_point_at_integration`, the
"pushed this run" signal) are fixed above in (i-a), (iii), (iv), (vi), cases 14b/14c/18,
Citations and the Ordering note. Finding 4 (split waiver): the brief stands. The no-split call
is the human's, made at round-5 sign-off; the reviewer is right that (i-b) and (iv) could land
on their own, and that is recorded here for the human to re-confirm, not decided by Plan.
- Add to #616: "a held bundle re-driven by hand is built and verified on the grown line
  (`worktree.py:96-98`, `gates.py:568-570`, `drift.py:49-64` read the moving branch) while
  publish cuts from the recorded tip".
- `results/issue_593/test_integrate_stack_bases.py` at the bundle root is round 5's briefed-test
  copy (the Do contract: "the test the brief names"), identical to the one in
  `iteration-v5/patch.diff`. The iterate archive leaves it in place; this round's Do overwrites it.
- Still a stop, by choice: an undeclared fold overlap.

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.

## Iteration 6 — carry-forward (from the previous attempt)
- Sign-off rationale: Rejected for one gap (adversary §6 item 3): when a published branch is gone and its merged head is not on the line, `_take_in_base` (integrate.py:457-475, via `_gone_branch` :436-445) merges `<base_remote>/<base>` in and claims the base carries the work without checking. A PR merged into another branch (e.g. its base edited to `release` on the host) silently drops the prerequisite. Change next: before merging the base in, run `git merge-base --is-ancestor <merged head> <base_ref>`. rc 0 → merge the base as today. rc 1, or the head commit not in the clone → raise IntegrationError naming the bundle, PR, head SHA and base ("merged somewhere other than <base>"). Any other rc → git-step failure (as `_in_line`). Squash/rebase merges now stop here too; that is fine (out of scope). Also fetch the base remote LAST in `_prepare_worktree` (integrate.py:520) so a merge+delete between fetches can't leave a stale base snapshot. Update 09-parallel-lanes.md:69 to say the base is checked to hold the merged head, else the fold stops. Add regression tests from the adversary repro: (a) fixup pushed to fix/A, fix/A merged --no-ff into `release` not main, deleted → fold raises, nothing pushed; (b) case-9 never-carried shape merged into `release` → raises. Existing merged-into-main cases must stay green. Keep everything else from this round as is; the rest of the review passed. Already settled this round: T5 judgment approved (vendored model edits, prior art); live GitHub validation deferred to a follow-up (§10).
- Sign-off session carry-forward (captured live, before §9 flattened it):
  Rejected for one gap (adversary §6 item 3): when a published branch is gone and its merged head is not on the line, `_take_in_base` (integrate.py:457-475, via `_gone_branch` :436-445) merges `<base_remote>/<base>` in and claims the base carries the work without checking. A PR merged into another branch (e.g. its base edited to `release` on the host) silently drops the prerequisite.
  Change next: before merging the base in, run `git merge-base --is-ancestor <merged head> <base_ref>`. rc 0 → merge the base as today. rc 1, or the head commit not in the clone → raise IntegrationError naming the bundle, PR, head SHA and base ("merged somewhere other than <base>"). Any other rc → git-step failure (as `_in_line`). Squash/rebase merges now stop here too; that is fine (out of scope).
  Also fetch the base remote LAST in `_prepare_worktree` (integrate.py:520) so a merge+delete between fetches can't leave a stale base snapshot.
  Update 09-parallel-lanes.md:69 to say the base is checked to hold the merged head, else the fold stops.
  Add regression tests from the adversary repro: (a) fixup pushed to fix/A, fix/A merged --no-ff into `release` not main, deleted → fold raises, nothing pushed; (b) case-9 never-carried shape merged into `release` → raises. Existing merged-into-main cases must stay green.
  Keep everything else from this round as is; the rest of the review passed. Already settled this round: T5 judgment approved (vendored model edits, prior art); live GitHub validation deferred to a follow-up (§10).
- Full previous attempt preserved in `iteration-v6/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
