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

Review issue #593: make stack-mode folds preserve published commit ancestry within a run, target wave PRs at the real base, and hold dependents of unpublished bundles while independent work continues.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The within-run invariant, legacy/fork exceptions, partial-failure policy, and sibling-diff limitation have falsifiable outcomes and explicit boundaries; brief.md:26, brief.md:163, brief.md:191. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing production changes reproduced wrong PR bases, lost commit ancestry, forced continuation, and missing dependency holds: 165 tests, 18 assertion failures and four new-keyword errors; review-red.log:517, review-red.log:602, review-red.log:745; target/template/tests/test_integrate_stack_bases.py:325. |
| C3 Change | PASS | The inspected paths satisfy the specified real-base routing, published-remote selection, run-tip ownership, and partial-failure contract without a confirmed regression; target/template/src/pdca_harness/publish.py:260, target/template/src/pdca_harness/integrate.py:112, target/template/src/pdca_harness/flow.py:1854. |
| C4 Verification (red→green) | PASS | Restoring the production stash made all 231 selected tests pass, including the four changed test modules plus publish compatibility; the red leg contained behavioral assertion failures, not merely unsupported-keyword errors; review-green.log:523, review-red.log:602; target/template/tests/test_flow_slice.py:1433. |
| C5 Causal adequacy | PASS | Real Git demonstrates preserved PR ancestry and chain-diff shrink, addressing the commit-copying cause; no added optional-capability probe masks a load-time cause, and the production-import scanner passed; target/template/src/pdca_harness/integrate.py:350, target/template/tests/test_integrate_stack_bases.py:325, review-prod-path.log:1. |
| T1 Structure | PASS | Per-target grouping, sorted lock acquisition, and locks spanning fold plus re-gate remain intact, while per-run tip state is separate from routing state; target/template/src/pdca_harness/integrate.py:262, target/template/src/pdca_harness/flow.py:1689, target/template/src/pdca_harness/flow.py:1860. |
| T2 Shape | PASS | Independent docs lint and rendering passed the internal-link audit for 22 pages; whitespace checking passed, and the host-CI log records the same successful audit; review-docs-lint.log:1, review-docs-render.log:2, gate-logs/host-ci-docs.log:10; target/.github/workflows/docs-check.yml:32. |
| T3 Runtime | PASS | Independent driver suite: 2,239 tests, two skips; selected publish/fold/flow checks also passed. Root render/update coverage is supported by the frozen 24-test success, since local Python lacks importable Copier; review-suite.log:1775, gate-logs/T3-suite.log:38, gate-logs/T3-suite.log:54, review-root-suite.log:6. |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; their substantive audit must rerun at publish, as the deferred gate explicitly records; gate-logs/T4-contribution.log:10. |
| T5 Judgment | NEEDS-HUMAN | Confirm the partial-failure policy and vendored-spec edits are appropriate to this cycle, and settle path-based merged/closed/rejected prior art—these affect scope and upstream suitability; only the brief reports history, while this target has one synthetic commit and no remotes; brief.md:271, brief.md:283, brief.md:287; target/template/PCDA/quality-cycle/09-parallel-lanes.md:69. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the stack is usable on the live host: GitHub Files changed/Update branch and the real gh lookup for a deleted merged PR branch were not exercised, so evidence rests on local Git plus a mocked merge-state response; brief.md:208; target/template/tests/test_integrate_stack_bases.py:293, target/template/tests/test_integrate_stack_bases.py:333. |

No confirmed patch defect found. These verdicts are advisory and do not authorize acceptance, publication, or merge.

Independent verification used the disposable target only. Production changes were stashed while the patched tests remained, then restored before the green run. The red command ran `tests.test_flow_adopt_split`, `tests.test_flow_slice`, `tests.test_integrate`, and `tests.test_integrate_stack_bases`; the green command added `tests.test_publish_slice`. Both used `PYTHONPATH=src python3 -m unittest` from `target/template`. The full driver rerun used `PYTHONPATH=src python3 -m unittest discover -s tests`. Temporary test files stayed under this review directory through `TMPDIR`. The submitted source patch remains restored.

The instance-scoped gate wrappers are not present here. Their frozen logs were inspected, and available underlying checks were run directly: the production-import scanner, docs lint, site renderer/link audit, changed tests, and full driver suite. `python3 -m tests.run_root_suite` exited 77 because Copier is not importable by this interpreter; this is a reviewer-host limitation, not a patch failure. The frozen root log explicitly shows both rendering cases and five update-compatibility cases executing successfully. No gate log is missing. Host-CI parity means the logged workflow commands passed; it does not establish live PR behavior.

Prior-art investigation: `git -C target log --oneline --all -- template/src/pdca_harness/integrate.py template/src/pdca_harness/publish.py` returns only `22cf0c8 pre-fix base 24c7f83...`; `git -C target remote -v` returns nothing. The brief records an affected-path merged-history and closed-unmerged check for those two files, but the review bundle cannot independently establish that result or extend it to every other affected path. Human confirmation should cover all paths in `patch.diff`, including flow and the vendored specification. The supplied `target/template/docs/INTEGRATION.md.jinja:80` leaves project-specific human-only items as TODO; the concrete vendored-spec requirement is recorded in brief.md:287 and is retained here.

For live validation, use a disposable GitHub repository and an instance containing this patch:

1. Set `[driver].wave_mode = "stack"`. Prepare A and C as independent wave-0 briefs with disjoint file changes; B declares both as prerequisites. Run `pdca flow <A-id> <C-id> <B-id>` through the normal human sign-offs. Inspect each PR with `gh pr view <PR-URL> --json baseRefName,headRefName`; all must target the real base.
2. The human merges A and C using merge commits. Inspect B's Files changed, then use GitHub's Update branch action (merge the base into B). Confirm only B's change remains, and have the human merge B. Local reruns already confirmed the two-merge-base sibling case and the successful base-update remedy at target/template/tests/test_integrate_stack_bases.py:333.
3. Delete A's merged PR branch through the host UI. From the disposable instance root, substitute A's actual issue ID and run `PYTHONPATH=src python3 -c 'from pdca_harness.config import Config; from pdca_harness import integrate; c = Config.load(); integrate.fold(c, [c.find_bundle("A")], folded_this_run={})'`. This deliberately writes only that disposable repository's integration line. Expect the pruning fetch and real `gh pr view` lookup to report A as merged and skip its deleted branch without an IntegrationError. Confirm A's change remains in the resulting tree. The automated deleted-branch case currently mocks `merged.is_merged`; it cannot discharge this host check.

### Advisory — adversary

# Adversarial review — issue 593 (stack-mode append-only fold, real-base PRs)

**Evidence (could not refute).** I re-ran both legs. With the patch,
`tests.test_integrate_stack_bases tests.test_integrate tests.test_flow_slice
tests.test_flow_adopt_split` gives 165 tests, OK. On a copy in my sandbox with the five
production files reset to `HEAD` (`cli.py flow.py integrate.py publish.py sweep.py`), 21 of
the 24 new cases fail (17 FAIL, 4 ERROR). The 4 errors are the expected TypeError on the new
`folded_this_run` keyword. The tests call the real `integrate.fold`, `publish.publish` and
`flow.flow_ids` against a real bare origin, not a copy of the code. The red case
(`test_integrate_stack_bases.py:187-202`) cannot pass for the wrong reason: even if the old
force-push landed, the PR branches' own commits would not be ancestors of the tip. The
no-force check (`:204-212`) looks at the push arguments, so a forced push that happens to
fast-forward cannot slip through.

**The fix: three concrete cases break it.**

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/integrate.py:99-126` (`_published_ref` / `unpublished`), used at `template/src/pdca_harness/flow.py:1855`: "unpublished" is judged by whether `publish.json` exists on disk. That file is **not** archived when a bundle is iterated (`state.py:116` `DOWNSTREAM_OF_BRIEF` doesn't list it). And `publish.py:292-299` (#108) is built for exactly this case: re-publishing a rebuilt bundle onto its old branch. **Failing case** (reproduced against the patched code): A was published in an earlier run, then sent back with `signoff --iterate-do`. In this run A is rebuilt and accepted with a new `patch.diff`, but its re-publish fails (T4 text, host CI, push). `integrate.unpublished([A])` returns `[]`, so nothing is held. `fold` merges `origin/fix/A`, the **old, rejected attempt** (the line's `a.txt` reads `OLD attempt`). Every wave-1 dependent of A then builds and opens its PR on top of the rejected code. Before the patch, the fold re-applied the current `patch.diff`, so this case is a regression. This is the partial-failure case (iv) was written for. The flow already knows which bundles failed to publish *this run* (`_publish_bundle`'s rc, the `ready` map at `flow.py:1799-1830`), and it should hold based on that, not on an on-disk record. The flow tests (`test_flow_slice.py` `_live`, `fail_publish`) only cover a failing publish that leaves **no** `publish.json`, so they miss this case.

- NEEDS-HUMAN — `template/src/pdca_harness/flow.py:683-690`: the hold follows only `waves.declared_deps` (`waves.py:48`: `Depends on` / `Depends on (merged)` / `Stacks on`). But `compute_waves` also puts a `Conflicts with` pair into separate waves (`waves.py:177`), so the second bundle builds *on* the first. **Failing case** (reproduced through `flow.flow_ids`): wave 0 = {CA}, whose publish fails. Wave 1 = {CJ}, which has `Conflicts with: CA`. CA is left out of the fold (the fold gets `[]`), and CJ is **not** held. It is built and published on a base without CA, though the two edit the same resource. When the human later publishes CA by hand, CA's and CJ's PRs collide on the target. Before the patch, the fold carried CA's patch, so CJ was built on it. The brief limits the hold to prerequisites, so whether a conflict partner should be held too is a scope call.

- NEEDS-HUMAN — `template/src/pdca_harness/integrate.py:326-327` together with the docs at `docs/07-crosscutting.md:649`, `template/PCDA/quality-cycle/09-parallel-lanes.md:69`, `integrate.py:17-19`, `publish.py:252-254`: the claim "once its only prerequisite merges, its diff is its own change" only holds if the base did not move between A's publish (A's branch is cut from `<base_remote>/<base>` at that moment) and the run's first fold (which starts fresh from the *newly fetched* base). **Failing case** (reproduced with the real fold): A is published off `main@base0`. Any other commit lands on `main`. `fold([A], folded_this_run={})` starts from `main@base1`. B is cut from the line. A's PR merges with a merge commit. Now `git merge-base --all main fix/B` gives **2** commits, and `main...fix/B` still lists `a.txt` and `b.txt`. This is the same shape as the documented sibling case, but it hits a single-predecessor chain. On a busy repo, or when wave 0's publish takes minutes (host CI per bundle), it will be common. Two ways to resolve it: (a) narrow the docs/brief (v) to "unless the base moved before the first fold; then Update branch", or (b) start the fresh line from the PR branches' own fork point instead of the newest base, which means later waves build on an older base. Either is a design call. Test 8 (`test_integrate_stack_bases.py:325-331`) only covers the case where the base did not move.

**Not a refutation, stated as a limit.** The same-run guard (`integrate.py:317-325`) only runs at the *next fold*. Wave k+1's Do and publish cut from whatever `origin/pdca-integration/<base>` is at that moment (`publish.py:246`), not from the recorded tip. If another run's first fold force-pushes in between, this run has already opened wave k+1 PRs that carry the other run's line before the guard stops it. The brief leaves full concurrency to #591, so I am not filing this as a finding. But the docs' "a line another run moved meanwhile STOPs the run" catches it one wave late.

**Tried and could not refute:** the no-keyword and listed-target append paths (an already-merged branch is not merged twice, `integrate.py:364-365`); the push to a `denyNonFastForwards` origin; the concurrent-tip refusal leaving origin untouched; `Onto branch` records fetching the record's own remote and never origin's same-named branch; a gone branch with a merged PR being skipped while a gone branch with an open PR stops naming the ref; the fail-closed check before any git step; the dry-run fallback to `_branch_name` without calling `subprocess`; a no-target bundle not holding its dependents; the multi-target sorted lock order being unchanged; `pushed_tip` recorded before the re-gate. I found no wrong claim in `check-gates.json`. C4 and C5 match what I re-ran. T4 is honestly marked deferred.

### Advisory — code-review

# Advisory code review — issue 593 (stack-mode append-only fold, real-base PRs)

Lenses: correctness bugs the patch adds; reuse / simplification / efficiency.
Grounded on the patched tree at `$PDCA_TARGET`. Gates: C4 and T3 pass (gate-logs). I found
no blocking correctness bug. The new code does what the brief's (i)–(vii) ask: the
fresh/continue/auto start choice, the tip-mismatch refusal, no `--force` on a continuing
push, the pruning fetch of every remote a record names, merge-abort on conflict, and the
`_runnable` hold that cascades. Findings, most important first:

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/integrate.py:120-126` (`unpublished`) and
  `integrate.py:99-117` (`_published_ref`) decide "published" from whether a `publish.json`
  with a `branch` is on disk, not from whether publish worked **this run**. If a bundle was
  published in an earlier run and is driven again (re-opened / iterated), and this run's
  publish fails (`flow.py:651-653`) or its texts fail draft/T4 (`flow.py:1817-1822`), the old
  `publish.json` stays. The bundle is then not held. The fold merges the old PR branch (old
  content) and its dependents build on it. The brief's (iv) means "publish failed this run",
  so this is a missed case. A simple fix: have the flow add a bundle to `unpublished` when
  its publish rc is non-zero or its texts were not ready, on top of the `publish.json` check.
- `template/src/pdca_harness/integrate.py:244-259` (the `refs` / `missing` loop in `fold`)
  does the same work as `unpublished()` at `integrate.py:120-126`, plus a dry-run fallback.
  Both call `_published_ref` for each targeted bundle. Small cleanup, not a bug: have
  `unpublished()` drive the outside-dry-run error, or move the ref resolution (with the
  `_branch_name` fallback) into one helper that both use, so the definition of
  "unpublished" can't drift between flow and fold.
- `template/src/pdca_harness/integrate.py:364` — `git merge-base --is-ancestor` returns 1
  for "not an ancestor" and 128 for an error. The code treats both as "go ahead and merge".
  An error then shows up as a misleading "does not merge cleanly … undeclared cross-wave
  overlap" message (`integrate.py:372-374`) instead of a git-step failure. The result is
  still safe (fail-closed, nothing pushed); only the message is wrong. Low priority.
- `template/src/pdca_harness/integrate.py:355-362` — when a published branch is gone, the
  fold calls `merged.is_merged`, which runs `gh pr view` (`merged.py:46`) while the
  integration lock is held. A `gh` failure counts as "not merged" (`merged.py:48-51`), so a
  flaky network turns a merged, deleted branch into a run-stopping `IntegrationError`. That
  is fail-closed and matches the brief. The brief already owes a live-host check of this
  path at sign-off. Noted, no change asked.
- Test coverage, `template/tests/test_integrate.py:292-300`
  (`test_overlap_raises_integration_error`): it checks the error and that nothing was
  pushed. It does not check that `_merge_published`'s `merge --abort`
  (`integrate.py:371`) leaves the reused integration worktree clean. A dirty tree would make
  the next `checkout -B` fail on a re-run. A one-line `git status --porcelain` check on the
  worktree would pin this. Optional.
- `template/tests/test_integrate.py:194-202` (`test_fold_commits_carry_a_dco_signoff`) checks
  the trailer on the tip commit only. With a single bundle the tip is the `--no-ff` merge
  commit, so it does cover the new merge-commit signoff. No action needed; noted because the
  test's subject changed from a re-applied commit to a merge commit without a rename.

Nothing in the publish change (`publish.py:261-262`) looks wrong: `wave_stacked` only flips
`pr_base` for a recorded stack-base outside merge mode, and the legacy `Stacks on:` and fork
paths are untouched, which the new tests pin.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T5 Judgment — Confirm the partial-failure policy and vendored-spec edits are appropriate to this cycle, and settle path-based merged/closed/rejected prior art—these affect scope and upstream suitability; only the brief reports history, while this target has one synthetic commit and no remotes; brief.md:271, brief.md:283, brief.md:287; target/template/PCDA/quality-cycle/09-parallel-lanes.md:69.
- [ ] Validation — fitness-to-purpose — Decide whether the stack is usable on the live host: GitHub Files changed/Update branch and the real gh lookup for a deleted merged PR branch were not exercised, so evidence rests on local Git plus a mocked merge-state response; brief.md:208; target/template/tests/test_integrate_stack_bases.py:293, target/template/tests/test_integrate_stack_bases.py:333.
- [ ] `template/src/pdca_harness/integrate.py:99-126` (`_published_ref` / `unpublished`), used at `template/src/pdca_harness/flow.py:1855`: "unpublished" is judged by whether `publish.json` exists on disk. That file is **not** archived when a bundle is iterated (`state.py:116` `DOWNSTREAM_OF_BRIEF` doesn't list it). And `publish.py:292-299` (#108) is built for exactly this case: re-publishing a rebuilt bundle onto its old branch. **Failing case** (reproduced against the patched code): A was published in an earlier run, then sent back with `signoff --iterate-do`. In this run A is rebuilt and accepted with a new `patch.diff`, but its re-publish fails (T4 text, host CI, push). `integrate.unpublished([A])` returns `[]`, so nothing is held. `fold` merges `origin/fix/A`, the **old, rejected attempt** (the line's `a.txt` reads `OLD attempt`). Every wave-1 dependent of A then builds and opens its PR on top of the rejected code. Before the patch, the fold re-applied the current `patch.diff`, so this case is a regression. This is the partial-failure case (iv) was written for. The flow already knows which bundles failed to publish *this run* (`_publish_bundle`'s rc, the `ready` map at `flow.py:1799-1830`), and it should hold based on that, not on an on-disk record. The flow tests (`test_flow_slice.py` `_live`, `fail_publish`) only cover a failing publish that leaves **no** `publish.json`, so they miss this case.
- [ ] `template/src/pdca_harness/flow.py:683-690`: the hold follows only `waves.declared_deps` (`waves.py:48`: `Depends on` / `Depends on (merged)` / `Stacks on`). But `compute_waves` also puts a `Conflicts with` pair into separate waves (`waves.py:177`), so the second bundle builds *on* the first. **Failing case** (reproduced through `flow.flow_ids`): wave 0 = {CA}, whose publish fails. Wave 1 = {CJ}, which has `Conflicts with: CA`. CA is left out of the fold (the fold gets `[]`), and CJ is **not** held. It is built and published on a base without CA, though the two edit the same resource. When the human later publishes CA by hand, CA's and CJ's PRs collide on the target. Before the patch, the fold carried CA's patch, so CJ was built on it. The brief limits the hold to prerequisites, so whether a conflict partner should be held too is a scope call.
- [ ] `template/src/pdca_harness/integrate.py:326-327` together with the docs at `docs/07-crosscutting.md:649`, `template/PCDA/quality-cycle/09-parallel-lanes.md:69`, `integrate.py:17-19`, `publish.py:252-254`: the claim "once its only prerequisite merges, its diff is its own change" only holds if the base did not move between A's publish (A's branch is cut from `<base_remote>/<base>` at that moment) and the run's first fold (which starts fresh from the *newly fetched* base). **Failing case** (reproduced with the real fold): A is published off `main@base0`. Any other commit lands on `main`. `fold([A], folded_this_run={})` starts from `main@base1`. B is cut from the line. A's PR merges with a merge commit. Now `git merge-base --all main fix/B` gives **2** commits, and `main...fix/B` still lists `a.txt` and `b.txt`. This is the same shape as the documented sibling case, but it hits a single-predecessor chain. On a busy repo, or when wave 0's publish takes minutes (host CI per bundle), it will be common. Two ways to resolve it: (a) narrow the docs/brief (v) to "unless the base moved before the first fold; then Update branch", or (b) start the fresh line from the PR branches' own fork point instead of the newest base, which means later waves build on an older base. Either is a design call. Test 8 (`test_integrate_stack_bases.py:325-331`) only covers the case where the base did not move.
- [ ] `template/src/pdca_harness/integrate.py:120-126` (`unpublished`) and `integrate.py:99-117` (`_published_ref`) decide "published" from whether a `publish.json` with a `branch` is on disk, not from whether publish worked **this run**. If a bundle was published in an earlier run and is driven again (re-opened / iterated), and this run's publish fails (`flow.py:651-653`) or its texts fail draft/T4 (`flow.py:1817-1822`), the old `publish.json` stays. The bundle is then not held. The fold merges the old PR branch (old content) and its dependents build on it. The brief's (iv) means "publish failed this run", so this is a missed case. A simple fix: have the flow add a bundle to `unpublished` when its publish rc is non-zero or its texts were not ready, on top of the `publish.json` check.
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
- Iteration delta (if iterating): The design (real-base PRs, append-only fold of the real PR commits, hold dependents of an unpublished bundle) is accepted — keep it. Rebuild only to fix these: 1. Regression — rejected attempt folded: "unpublished" is decided only from publish.json on disk (integrate.unpublished, used at flow.py:1855), and publish.json survives an iterate (state.py:116 DOWNSTREAM_OF_BRIEF does not list it). A bundle published in an earlier run, iterated, rebuilt and accepted, whose re-publish FAILS this run, is not held: fold merges its old rejected branch and its dependents build on it. Also hold any bundle whose publish failed THIS run (publish rc non-zero, or texts not ready at flow.py:1817-1822), in addition to the publish.json check. Add a flow test: published earlier, rebuilt, re-publish fails -> held, its dependents skipped, the old branch not in the fold. 2. Diff-shrink docs overclaim: if the base moves between a wave-0 publish and the run's first fold, a single-predecessor chain also gets two merge bases and keeps the predecessor's files in its diff. Narrow (v)'s wording in the docs/docstrings (docs/07-crosscutting.md:649, 09-parallel-lanes.md:69, integrate.py:17-19, publish.py:252-254) to cover this case with the same "Update branch" remedy; do not change the fold design. Add a test pinning the base-moved case and the remedy. 3. Optional cleanups from code review: resolve published refs in one helper shared by unpublished() and fold so the definition can't drift; treat `git merge-base --is-ancestor` rc 128 as a git-step failure, not an overlap. Out of scope this round (brief unchanged): holding a `Conflicts with` partner of an unpublished bundle — the brief's (iv) holds prerequisites only.
- By / date: Eduard Ralph / 2026-10-02

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 6 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
