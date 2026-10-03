# Result — issue 593 / stack-mode-append-only-fold-real-base-prs

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: Two defects in `[driver].wave_mode = "stack"` for an own-repo target (found
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
- Success criterion: With the patch, on an own-repo target (`base_remote = "origin"`):
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
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: Restore the invariant for own-repo stack mode, per (i)–(vi): wave>0 PRs open
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

Review issue #593: preserve real PR commits in append-only stack-mode folds and open wave PRs against the real target base so every wave can land bottom-up.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief defines falsifiable ancestry, PR-base, restart, and fail-closed contracts; the real-base choice and per-run continuation are grounded at `target/template/src/pdca_harness/publish.py:277` and `target/template/src/pdca_harness/flow.py:1847`; the unconditional diff-shrink promise is challenged below. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing production changes reproduces rewritten ancestry, refused non-fast-forward pushes, and integration-targeted PRs; these are assertion failures, not merely new-keyword errors (`target/template/tests/test_integrate_stack_bases.py:129`, `review-evidence/red.log:587`, `review-evidence/red.log:642`). |
| C3 Change | FAIL | A wave containing sibling PRs still leaves already-merged sibling content in a dependent's three-dot diff, contradicting the promised review behavior; production folding reproduced two merge bases and `b.txt` plus `c.txt` instead of only `b.txt` (`target/template/src/pdca_harness/integrate.py:309`, `target/docs/07-crosscutting.md:645`, `review-evidence/sibling-diff.log:4`). |
| C4 Verification (red→green) | PASS | The asserted regression is independently red→green: 243 focused tests yield 10 failures/2 errors without production changes and all pass after restoration; this verifies the covered contracts, not the sibling diff-shrink claim (`target/template/tests/test_integrate_stack_bases.py:147`, `review-evidence/red.log:685`, `review-evidence/green.log:549`). |
| C5 Causal adequacy | NEEDS-HUMAN | Decide whether to narrow the promised diff behavior or revisit the Plan to support sibling-wave histories — preserving predecessor SHAs fixes rewritten ancestry but does not yield one shared merge base after independent sibling merges (`target/template/src/pdca_harness/integrate.py:192`, `target/template/src/pdca_harness/integrate.py:309`, `review-evidence/sibling-diff.log:4`). |
| T1 Structure | PASS | Per-target grouping, sorted lock acquisition, and the lock spanning fold plus re-gate remain intact; the run state enters through the existing fold call (`target/template/src/pdca_harness/integrate.py:227`, `target/template/src/pdca_harness/integrate.py:274`, `target/template/src/pdca_harness/flow.py:1842`). |
| T2 Shape | PASS | Independently rerun docs lint, 22-page rendering/internal-link audit, and diff whitespace checks pass; frozen host-parity output agrees (`target/.github/workflows/docs-check.yml:35`, `review-evidence/docs-lint.log:1`, `review-evidence/docs-render.log:3`, `gate-logs/host-ci-docs.log:10`). |
| T3 Runtime | PASS | The independent driver suite passes 2,224 tests with two skips; the frozen root-suite log records 24 passing render/update tests, while this reviewer interpreter cannot import copier (a local host limitation, not a patch defect; `review-evidence/driver-suite.log:1767`, `gate-logs/T3-suite.log:54`, `review-evidence/root-suite.log:6`). |
| T4 Contribution | N/A | Contribution artifacts are intentionally absent at Check; the substantive contribution audit must rerun at publish, as the deferred gate explicitly records (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Approve the vendored-spec and operational policy changes, and confirm affected-path merged/closed/rejected prior art — restarting with force, stopping all later waves for unpublished work, and skipping deleted merged branches affect operators; the isolated snapshot cannot corroborate the brief's historical claims (`target/template/PCDA/quality-cycle/09-parallel-lanes.md:69`, `target/template/PCDA/quality-cycle/08-glossary.md:290`, `brief.md:185`, `brief.md:199`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether this behavior meets the intended multi-wave review workflow, including the reproduced sibling-diff limitation; live host PR behavior and deleted-branch PR-state lookup were not exercised, so that evidence rests on publish dry-runs and a mocked `merged.is_merged`, despite the brief declaring no external dependencies (`target/template/tests/test_integrate_stack_bases.py:222`, `target/template/tests/test_integrate_stack_bases.py:275`, `target/template/src/pdca_harness/merged.py:46`). |

**Finding — P2: the unconditional diff-shrink guarantee does not hold for sibling waves.** The merge at `target/template/src/pdca_harness/integrate.py:309` produces an integration-only merge commit joining sibling branches A and C. A dependent B inherits that commit. Merging A and C separately into main with merge commits preserves both PR SHAs, but main does not contain the integration merge. A and C remain two incomparable best common ancestors of main and B. Consequently, `git diff main...fix/B` chooses one and still includes the other sibling's change. This contradicts `target/docs/07-crosscutting.md:645`, `target/template/PCDA/quality-cycle/09-parallel-lanes.md:69`, and the production docstring at `target/template/src/pdca_harness/integrate.py:192`.

I exercised this with the applied production `integrate.fold`, real published branches, a bare origin, and separate local `--no-ff` merges simulating bottom-up PR merges. `git merge-base --all main fix/B` returned two SHAs; the three-dot diff listed `b.txt` and `c.txt`, while the direct tree diff listed only `b.txt`. Merging B still succeeded and main then contained A, B, and C. Thus this finding concerns the promised review diff, not loss of contributions or failure to land the stack. The new sibling test verifies ancestry and sign-off but never merges the siblings into main or inspects the dependent diff (`target/template/tests/test_integrate_stack_bases.py:160`). Add that topology to the regression coverage and either establish the stronger behavior or explicitly qualify the docs and success criterion through Plan review.

Reproduce entirely inside this review sandbox:

```bash
python3 review-evidence/sibling-diff-repro.py
```

The recorded graph and results are in `review-evidence/sibling-diff.log` and `review-evidence/sibling-diff-confirm.log`. This reproducer changes only disposable local fixture repositories; it performs no host PR operations.

**Verification and evidence limits.** I stashed only `template/src/pdca_harness` in the supplied disposable target, retained the patched tests for the red leg, popped the stash, and reran the same six modules: `test_integrate_stack_bases`, `test_integrate`, `test_flow_slice`, `test_flow_adopt_split`, `test_publish_slice`, and `test_verify_base`. Both legs ran 243 tests. The two red-leg keyword errors are supplemental; the ancestry, push, and PR-base assertions independently demonstrate the original defects. Reverse-application checking confirms the patch remains applied, and `git diff --check` is clean. No target-staleness caveat applies.

The C5 frozen scanner reports a production-package import (`gate-logs/C5-prod-path.log:10`); independent AST inspection confirms the imports at `target/template/tests/test_integrate_stack_bases.py:27`, and the real-git tests actually invoke production folding. No added optional-capability/load-time guard triggers the symptom-guard rule: these branch-existence checks concern legitimately absent runtime data. C5 needs a human because the stated multi-parent causal conclusion is incomplete.

The instance-root gate wrappers are not supplied as runnable instance tooling here. I ran their available underlying suites and docs checks and inspected the frozen outputs. The local root runner exits 77 because `/usr/bin/python3` cannot import copier; the frozen log explicitly shows the actual render and update-compatibility cases executing successfully (`gate-logs/T3-suite.log:37`, `gate-logs/T3-suite.log:54`). This does not justify a verification FAIL or a missing-log escalation.

**Human decisions.** The brief records a prior-art search by `integrate.py` and `publish.py` path, including merged history and closed-unmerged work. My path-filtered history query returns only the harness's synthetic base commit `f65f5e4` (original base `24c7f83`); the target has no remotes. No frozen prior-art query output is supplied, and the additional affected documentation/test/flow paths have no independent historical evidence here. Confirm the affected-path merged and closed/rejected check before treating novelty as established. The project-specific INTEGRATION §4 is not supplied as an instantiated policy; the target has a generic template with TODO conformance rows, while `brief.md:199` explicitly identifies glossary and parallel-lanes spec edits as human-only. Those decisions remain in T5.

For the remaining live-host validation, use a disposable configured instance/target: run a stack-mode flow with independent A and C in wave 0 and B depending on both; confirm all PR bases are the real base; merge A and C with merge commits and inspect B's Files changed; then merge B and confirm all three changes land. Separately exercise a published prerequisite whose merged PR branch was deleted and confirm the real `gh pr view --json state` path authorizes the skip. The supplied test instead forces `merged.is_merged` true without actually merging A (`target/template/tests/test_integrate_stack_bases.py:227`), so it demonstrates branch selection, not satisfaction of that host dependency.

This review is advisory. The reproduced mismatch and human decisions do not alter deterministic gate results or authorize acceptance.

### Advisory — adversary

# Adversarial review — issue 593 (stack-mode append-only fold, real-base PRs)

Verdict: the core fix holds up. The red→green evidence is genuine. I found one concrete
regression the builder can fix, one doc/fitness claim that is false for a common batch
shape, one new concurrency behaviour for the human to weigh, and a test gap.

## Findings

- NEEDS-HUMAN [impl] — **`Onto branch:` bundles in a non-final wave now stop the run.**
  `template/src/pdca_harness/integrate.py:295-303` always looks up `origin/<publish.json branch>`.
  But `publish._publish_stacked` pushes to the brief's `<remote>` (`publish.py:452`,
  `git push <remote> HEAD:<branch>`) and records a bare `branch` plus `base: "<remote>/<branch>"`
  (`publish.py:507-511`). Failing case, reproduced against the patched `fold` with a scratch
  origin + upstream: a bundle with `- **Onto branch:** upstream/feat` (the documented shape,
  `brief.py:281-296`) whose commit sits on `upstream/feat` → `IntegrationError: issue_ON's
  published branch feat is gone from origin and its PR is not merged`. The message is wrong
  (the branch was never on origin), and before this patch the fold just applied `patch.diff`,
  so this case used to work. If `origin` happens to hold an unrelated branch with the same name,
  the fold merges the wrong branch without warning. Fix: for `mode == "stacked"` records, resolve
  the record's `base` ref (and fetch that remote in `_prepare_worktree`, `integrate.py:340-344`),
  and add a test. Heads-up for the human: once fixed, the fold merges the **whole** existing PR
  branch (other people's commits) onto the line. That follows from "carry the real commits", but
  the brief never mentions `Onto branch`.

- NEEDS-HUMAN — **"then shrinks to its own" is false when a wave has two or more siblings.**
  The fold fast-forwards to the first sibling and makes a merge commit M for each later one
  (`integrate.py:309-310`). A dependent cut from M, after the human merges both siblings into
  main with merge commits, has **two** merge bases with main (sibling A's tip and sibling C's
  tip). Reproduced with plain git: `git merge-base --all main fixB` → `A`, `C`, and
  `git diff main...fixB` prints `warning: multiple merge bases` and still lists `c.txt` next to
  `b.txt`. So the dependent's diff keeps showing a predecessor's change until the dependent itself
  merges, which is the #185 cost this patch claims to remove. I have not checked how GitHub
  handles more than one merge base, so treat this as a claim to verify on a real host.
  Unwarranted as written: `template/PCDA/quality-cycle/09-parallel-lanes.md:69`,
  `docs/07-crosscutting.md:644-646`, `integrate.py:13-14` / `:192`, `publish.py:250-252`, and
  brief success criterion (ii)'s rationale. Single-predecessor chains do shrink. The human
  decides: reword the docs ("shrinks for a single-predecessor chain; with several siblings a
  sibling's change can stay visible until the dependent merges"), or change how the fold
  combines siblings.

- NEEDS-HUMAN — **A continuing fold adopts whatever line origin has, not the tip this run
  pushed.** `integrate.py:285-293` checks out `origin/<line>` after a fetch with no check that it
  is the SHA this run's previous fold pushed. The flow passes only target keys, not SHAs
  (`flow.py:1848`, `:1854`). Failing case: run R1 folds T1; a concurrent run R2 on the same base
  does its first fold and force-pushes T1'; R1's next fold continues from T1', merges R1's wave-1
  branches (cut from T1) with a merge commit, and pushes a clean fast-forward. R1's later-wave PRs
  now silently carry R2's commits. Before this patch the per-fold rebuild kept each run's PRs to
  its own work (R2's PRs broke instead). The "it moved since this run's last fold" error at
  `integrate.py:322-324` only fires if origin moves between this fold's fetch and its push.
  Concurrent runs are #591 and out of scope, but this diff changes that failure from "overwrite"
  to "silent mixing". A cheap guard: have `fold` return the pushed SHA, have `flow` pass it back,
  and refuse when `origin/<line>` differs. Scope call for the human.

- NEEDS-HUMAN [impl] — **Two test gaps let a regression to "always rebuild and force" pass.**
  (a) The only flow-level check is `folded_before == [set()]` (`tests/test_flow_slice.py:1140`)
  in a stub-publisher run, where `integ` is never filled (`flow.py:1853`, `if folded and not dry`).
  Hard-coding `folded_this_run=set()` at `flow.py:1848` passes every test, yet makes every fold a
  fresh force-pushed rebuild. That rewrites T1's sibling merge commit, the exact defect this issue
  fixes. Add a test with three or more waves and a non-dry fold that asserts the second fold
  receives `{(repo, base)}`. (b) `test_later_folds_push_without_force`
  (`tests/test_integrate_stack_bases.py:147`) proves the push is a fast-forward, not that it is
  unforced: `receive.denyNonFastForwards` accepts a `--force` push that happens to be a
  fast-forward, so reverting `integrate.py:320-321` to always `--force` still passes. Spy on
  `_git` for the push arguments, or move origin's line between the two folds and assert the
  refusal.

## What I tried that did not break the fix

- **Evidence.** In `gate-logs/C4-verify.log` the red leg fails for the right reasons: the
  append-only test fails on its ancestry assertion, the no-force test on the refused force-push,
  and both publish tests on `--base pdca-integration/main`. Only
  `test_a_new_runs_first_fold_restarts_from_the_base` fails with a `TypeError` on the red leg,
  which the brief allows. The tests call the real `integrate.fold` / `publish.publish`; there is
  no copy of production code. I re-ran `tests.test_integrate_stack_bases` and
  `tests.test_integrate` on the patched target: 23 tests OK. The T3 log shows 2224 driver tests
  OK.
- **Merge-mode guard (#411).** The PR base is changed only after `_merge_base_refusal`
  (`publish.py:269-278`), so that guard behaves as before.
- **Fork path.** `pr_base` for a fork is unchanged (`publish.py:258`).
- **Overlap.** On a conflict the fold runs `merge --abort` and raises before any push
  (`integrate.py:309-315`); the test confirms origin's line is untouched.
- **Stale tracking ref after a host deletes a merged branch.** Handled by `fetch --prune`
  (`integrate.py:344`) and covered by a test.
- **Unpublished bundle.** It is caught before any git step runs (`integrate.py:233-235`).
- **Multi-target runs.** The `integ` keys and `fold`'s group keys are the same `(repo, base)`
  tuple, and `accepted` is cumulative, so a target folded once stays in every later fold
  (`flow.py:1822`, `:1854`).

### Advisory — code-review

# Advisory code review — issue 593 (stack-mode append-only fold, real-base PRs)

Lens: bugs the patch introduces, plus reuse/simplification. Line numbers are from the patched tree under `target/`.

No correctness bug found in the core change. `fold` checks every bundle for a published branch before any git step (`integrate.py:234`), runs `merge --abort` and leaves origin alone when a merge conflicts (`integrate.py:309-315`), skips branches already in the line, and only force-pushes on a run's first fold (`integrate.py:320-330`). The `pr_base` retarget is applied after the merge-mode guard, so #411's behaviour is unchanged (`publish.py:278`). The new tests check the right things: ancestry by SHA, a no-force origin, the signed-off merge commit, the missing-branch case and stack-base beating `Stacks on`. Gates C4 and T3 are green in `gate-logs/`.

Smaller points:

- NEEDS-HUMAN [impl] — The dry-run plan never shows the append-only path from `flow`. `integ` is only updated when `not dry` (`template/src/pdca_harness/flow.py:1853`), so every later dry-run fold gets `folded_this_run=set()` and prints `checkout -B … origin/main` plus `git push --force` (`template/src/pdca_harness/integrate.py:253-266`). An offline rehearsal of a run with three or more waves therefore shows the old rebuild-and-force behaviour that this issue removes. A fix is to also record `integ` in dry-run (`_point_at_integration` would then see it too, so check that is wanted), or to pass the folded keys separately.
- `template/src/pdca_harness/integrate.py:260` — the dry-run prints `git merge --ff --signoff origin/<branch>`, but the real call adds `--no-edit -m "pdca-integrate: merge …"` (`integrate.py:309-310`). This is cosmetic, but the dry-run test pins the shorter text (`template/tests/test_integrate.py:599`), so keep the two in sync if the real call changes.
- `template/src/pdca_harness/integrate.py:85-108` — `_published_branch` and `_expected_branch` both read `publish._publish_record(d).get("branch")`. `_expected_branch` could call a small shared reader and fall back to `_branch_name`. Minor duplication, no behaviour change.
- `template/src/pdca_harness/integrate.py:344` — `fetch --prune origin` now runs in the user's primary checkout, not just the throwaway integration worktree. It deletes every stale `origin/*` tracking ref there, not only PR branches. This is needed for the gone-branch detection and is usually harmless. It is still a side effect on a checkout the harness doesn't own, so it may deserve a line in the docs.
- `template/src/pdca_harness/integrate.py:309` — when two siblings in one wave both branch off `main`, the second lands as a `pdca-integrate: merge …` commit. Every later-wave PR carries that commit until the later-wave PR itself merges, because merging the siblings' own PRs never puts that merge commit on `main`. The *diff* still shrinks as the brief says, but the PR's commit list keeps showing harness merge commits. This is expected from the design, not a bug. It's worth knowing when reading the docs' "shrinks to its own" wording.
- The new contract depends on a published PR branch's SHAs staying fixed within a run. `publish` still force-pushes with lease when a bundle is re-published (`template/src/pdca_harness/publish.py:300`). If a folded bundle were re-published mid-run, its old commits would stay on the line and the next fold would merge the new branch on top (duplicate or conflicting content). Nothing in one `flow` run does this today, and a new run restarts the line, so this is a note only.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] C5 Causal adequacy — Decide whether to narrow the promised diff behavior or revisit the Plan to support sibling-wave histories — preserving predecessor SHAs fixes rewritten ancestry but does not yield one shared merge base after independent sibling merges (`target/template/src/pdca_harness/integrate.py:192`, `target/template/src/pdca_harness/integrate.py:309`, `review-evidence/sibling-diff.log:4`).
- [ ] T5 Judgment — Approve the vendored-spec and operational policy changes, and confirm affected-path merged/closed/rejected prior art — restarting with force, stopping all later waves for unpublished work, and skipping deleted merged branches affect operators; the isolated snapshot cannot corroborate the brief's historical claims (`target/template/PCDA/quality-cycle/09-parallel-lanes.md:69`, `target/template/PCDA/quality-cycle/08-glossary.md:290`, `brief.md:185`, `brief.md:199`).
- [ ] Validation — fitness-to-purpose — Decide whether this behavior meets the intended multi-wave review workflow, including the reproduced sibling-diff limitation; live host PR behavior and deleted-branch PR-state lookup were not exercised, so that evidence rests on publish dry-runs and a mocked `merged.is_merged`, despite the brief declaring no external dependencies (`target/template/tests/test_integrate_stack_bases.py:222`, `target/template/tests/test_integrate_stack_bases.py:275`, `target/template/src/pdca_harness/merged.py:46`).
- [ ] **`Onto branch:` bundles in a non-final wave now stop the run.** `template/src/pdca_harness/integrate.py:295-303` always looks up `origin/<publish.json branch>`. But `publish._publish_stacked` pushes to the brief's `<remote>` (`publish.py:452`, `git push <remote> HEAD:<branch>`) and records a bare `branch` plus `base: "<remote>/<branch>"` (`publish.py:507-511`). Failing case, reproduced against the patched `fold` with a scratch origin + upstream: a bundle with `- **Onto branch:** upstream/feat` (the documented shape, `brief.py:281-296`) whose commit sits on `upstream/feat` → `IntegrationError: issue_ON's published branch feat is gone from origin and its PR is not merged`. The message is wrong (the branch was never on origin), and before this patch the fold just applied `patch.diff`, so this case used to work. If `origin` happens to hold an unrelated branch with the same name, the fold merges the wrong branch without warning. Fix: for `mode == "stacked"` records, resolve the record's `base` ref (and fetch that remote in `_prepare_worktree`, `integrate.py:340-344`), and add a test. Heads-up for the human: once fixed, the fold merges the **whole** existing PR branch (other people's commits) onto the line. That follows from "carry the real commits", but the brief never mentions `Onto branch`.
- [ ] **"then shrinks to its own" is false when a wave has two or more siblings.** The fold fast-forwards to the first sibling and makes a merge commit M for each later one (`integrate.py:309-310`). A dependent cut from M, after the human merges both siblings into main with merge commits, has **two** merge bases with main (sibling A's tip and sibling C's tip). Reproduced with plain git: `git merge-base --all main fixB` → `A`, `C`, and `git diff main...fixB` prints `warning: multiple merge bases` and still lists `c.txt` next to `b.txt`. So the dependent's diff keeps showing a predecessor's change until the dependent itself merges, which is the #185 cost this patch claims to remove. I have not checked how GitHub handles more than one merge base, so treat this as a claim to verify on a real host. Unwarranted as written: `template/PCDA/quality-cycle/09-parallel-lanes.md:69`, `docs/07-crosscutting.md:644-646`, `integrate.py:13-14` / `:192`, `publish.py:250-252`, and brief success criterion (ii)'s rationale. Single-predecessor chains do shrink. The human decides: reword the docs ("shrinks for a single-predecessor chain; with several siblings a sibling's change can stay visible until the dependent merges"), or change how the fold combines siblings.
- [ ] **A continuing fold adopts whatever line origin has, not the tip this run pushed.** `integrate.py:285-293` checks out `origin/<line>` after a fetch with no check that it is the SHA this run's previous fold pushed. The flow passes only target keys, not SHAs (`flow.py:1848`, `:1854`). Failing case: run R1 folds T1; a concurrent run R2 on the same base does its first fold and force-pushes T1'; R1's next fold continues from T1', merges R1's wave-1 branches (cut from T1) with a merge commit, and pushes a clean fast-forward. R1's later-wave PRs now silently carry R2's commits. Before this patch the per-fold rebuild kept each run's PRs to its own work (R2's PRs broke instead). The "it moved since this run's last fold" error at `integrate.py:322-324` only fires if origin moves between this fold's fetch and its push. Concurrent runs are #591 and out of scope, but this diff changes that failure from "overwrite" to "silent mixing". A cheap guard: have `fold` return the pushed SHA, have `flow` pass it back, and refuse when `origin/<line>` differs. Scope call for the human.
- [ ] **Two test gaps let a regression to "always rebuild and force" pass.** (a) The only flow-level check is `folded_before == [set()]` (`tests/test_flow_slice.py:1140`) in a stub-publisher run, where `integ` is never filled (`flow.py:1853`, `if folded and not dry`). Hard-coding `folded_this_run=set()` at `flow.py:1848` passes every test, yet makes every fold a fresh force-pushed rebuild. That rewrites T1's sibling merge commit, the exact defect this issue fixes. Add a test with three or more waves and a non-dry fold that asserts the second fold receives `{(repo, base)}`. (b) `test_later_folds_push_without_force` (`tests/test_integrate_stack_bases.py:147`) proves the push is a fast-forward, not that it is unforced: `receive.denyNonFastForwards` accepts a `--force` push that happens to be a fast-forward, so reverting `integrate.py:320-321` to always `--force` still passes. Spy on `_git` for the push arguments, or move origin's line between the two folds and assert the refusal.
- [ ] The dry-run plan never shows the append-only path from `flow`. `integ` is only updated when `not dry` (`template/src/pdca_harness/flow.py:1853`), so every later dry-run fold gets `folded_this_run=set()` and prints `checkout -B … origin/main` plus `git push --force` (`template/src/pdca_harness/integrate.py:253-266`). An offline rehearsal of a run with three or more waves therefore shows the old rebuild-and-force behaviour that this issue removes. A fix is to also record `integ` in dry-run (`_point_at_integration` would then see it too, so check that is wanted), or to pass the folded keys separately.
- [x] **A `Stacks on:` bundle in a real wave run is ambiguous under (i).** In a flow run, `waves.py:48` and `:63-65` turn `Stacks on` into a dependency edge. That puts the bundle in a wave>0, and `flow._point_at_integration` (`flow.py:702-707`) stamps a `stack-base` on it. That stamp beats `Stacks on` at `publish.py:640-642`. So (i)'s two rules cover the same bundle: "a wave>0 bundle (one with a recorded integration stack-base) … `--base main`" and "a hand-declared legacy `Stacks on:` parent keeps its PR-branch base". The tests the brief cites for the legacy rule (`test_publish_slice.py:453-466`, `:478-484`, `:1142-1160`) never write a `stack-base`, so they pass either way and decide nothing. The issue says "A hand-declared `Stacks on:` parent (#123) keeps its PR-branch base". The brief should say which rule wins when both are present and name a test that has both.
- [x] **The "first fold of this run" signal is a required design change, but the brief treats it as optional.** `fold()` takes no run identity. Each wave it gets the cumulative `accepted` list (`flow.py:1676`, `:1822`, `:1844`). So it cannot tell "the run's first fold, start fresh from `origin/<base>`" from "a later fold, fast-forward the pushed tip", and (iii) needs exactly that distinction. The Ordering note says Do touches `flow.py:1835-1870` "only if Do needs a 'first fold of this run' signal". In practice Do will need it, either as a flow-side flag or a new `fold` parameter. That is a second module change, and the brief's claim that it doesn't overlap with 597's hunks rests on it not happening. It also hits the Test-file rule: if the signal is a new `fold` keyword, a test that passes it gets a `TypeError` on the red leg. That is the same PDCA-UNVERIFIABLE trap the brief already warns about for imports. The brief should choose the mechanism and make sure the red test works with it.
- [x] **(iii)'s "new run starts fresh" half has no test.** The Falsifiability recipe only proves the within-run half (fold `[A]`, then fold `[A, B]` against a no-force origin). Nothing checks that a later run ignores an existing `pdca-integration/main` and starts again from `origin/main`, or that the first fold may (and must) force-push over a previous run's branch. A no-force origin would refuse that push, which (iii) doesn't mention. As written, this half is not falsifiable.
- [x] **(iv)'s fail-closed rule changes how a single bundle's publish failure is handled, and the brief doesn't say so.** At `flow.py:1811-1822`, a bundle whose texts failed draft or T4 is "NOT published this run" (`:1818-1820`) but still goes into `accepted` (`:1822`). Today the fold applies its `patch.diff`. Under (iv), that one bundle's T4 failure raises `IntegrationError` and stops every later wave, including waves that don't depend on it. That undoes #295's isolation ("one bundle's weak texts block only that bundle", `flow.py:1791-1793`). Notes-for-human (b) frames fail-closed as the brief's own call but never names this consequence. It should be stated and adjudicated, and probably tested.
- [x] **(ii) and (iv) don't say what happens when the published branch is gone from origin.** The new fold merges `origin/<publish.json branch>`. A resumed flow can reach that branch after the human has merged the PR and the host deleted the branch (GitHub's "delete branch on merge"). It can also reach a branch an older version published, cut from a v0.58 `pdca-integrate:*` line. The brief only defines failure for "no `publish.json` / no `branch`". It should say whether a missing remote ref is an `IntegrationError` or a skip (the work is already in the base), and whether old-line branches are acceptable. Otherwise Do will decide this on its own.
- [x] **(vi)'s list of text to update is incomplete, so "the text agrees" can't be signed off as written.** These places also describe the old behaviour and are not listed:
- [x] **Some citations are off.** (iv) cites `tests/test_integrate.py:274-302` for the overlap test, but `test_overlap_raises_integration_error` is `:274-281`. Lines `:284-302` are the `PointAtIntegration` class. (v) cites `:304-315` as fold grouping, but that is `flow._point_at_integration` routing, not `fold`. Do is told to cite `path:line` for every change, so wrong anchors here will carry into Check.

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
- Iteration delta (if iterating): The core direction (real-base PR targets, fold from the published PR commits, append-only within a run) was judged sound, but Check surfaced design questions the brief must settle before another build: 1. Sibling waves don't shrink (C5 / adversary): with two independent wave-N PRs A and C and a dependent B, the fold's sibling merge commit never reaches main, so after A and C merge B has two merge bases and its diff still shows C's change. Decide: narrow the docs/criterion to "shrinks for a single-predecessor chain", or change how the fold combines siblings — and add a test that merges the siblings into main and inspects the dependent's diff. 2. `Onto branch:` regression: the fold always resolves origin/<publish.json branch>, but stacked-mode records push to the brief's <remote> (publish.py:452, :507-511) — a bundle onto upstream/feat now stops the run with a wrong "gone from origin" error (worked before), or merges an unrelated same-named origin branch. The brief must cover `Onto branch` (resolve the record's base ref / fetch that remote) and say whether merging the whole existing PR branch onto the line is acceptable. 3. Concurrent-run mixing: a continuing fold adopts whatever origin's line is, so a second run's force-push gets silently built on (was a loud break before). Decide whether this fix carries the cheap guard (fold returns the pushed SHA, flow passes it back, refuse on mismatch) or it is deferred to #591. 4. Test gaps to name in the brief: a >=3-wave non-dry flow test asserting the second fold gets {(repo, base)}; a no-force test that spies on push args (denyNonFastForwards accepts a --force fast-forward). 5. Dry-run must show the append-only path (integ is only recorded when not dry, flow.py:1853). 6. Consider whether "PR targets real base" and "append-only fold" should be split into two bundles (pdca-pdca split) — they are near-separate outcomes sharing integrate/publish. Live-host validation (reviewer's recipe: A,C in wave 0, B on both; merge A,C; inspect B; and a deleted-merged-branch skip via real `gh pr view`) remains owed.
- By / date: Eduard Ralph / 2026-10-02

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 7 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
