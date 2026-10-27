# Build notes — issue 723 / fold-builds-a-per-bundle-base (iteration 5)

Target: eduralph/pdca-harness @ `main`. `$PDCA_VERIFY_BASE` was unset, and the driver's
worktree (`$PDCA_WORKTREE` = `/home/eddie/pdca/pdca-harness.pdca-wt`) sits on `489e5fb`
(`pdca-integration/main-r547f8028520f`). `git diff --stat origin/main HEAD -- template/src
template/tests` is empty (origin/main = `2ff8f3b`), so every "base `:N`" below holds on
`main` too. "new `:N`" is the line after the patch.

Files: `template/src/pdca_harness/integrate.py` (+329 / −1) and the new
`template/tests/test_integrate_bundle_base.py` (582 lines, 26 tests). Nothing else.

**`fold`'s body untouched.** No helper was moved out of it. Every step the new function
needs was already module-level and is called directly. `integration_branch` (base `:126`)
and `_flatten_base` (base `:154`) are unchanged. The module docstring is unchanged (its stack
rule is #725's).

## What the patch adds (integrate.py)

| new line | what | why |
|---|---|---|
| `:81` | `from . import brief, merged, publish` (was `merged, publish`) | `brief.stacks_on` for case (6)(iv). `brief` is already loaded through `publish`, so this adds no import cycle |
| `:145` | `bundle_base_branch(cfg, base, batch, name)` | the name rule of (2). A separate function because (2)'s id `1/2` cannot be a bundle dir: `cfg.bundle("1/2")` is `results/issue_1/2`, whose `.name` is `2` |
| `:710` | `_bundle_name` | `500` / `issue_500` are one bundle, as `batch_key` (base `:145`) counts them; used for `carried` / `excluded` keys |
| `:716` | `build_bundle_base(cfg, d, members, *, batch, carried, excluded) -> (branch, tip)` | the contract #724 calls; no keyword dropped, renamed or added |
| `:862` | `_member_cut_point` | the recorded cut point, and the four fail-closed cases of (6) |
| `:929` | `_member_clash` | (4)'s clash messages: base clash vs member clash |
| `:963` | `_unowned_work` | (6)'s rule |
| `:983` | `_foreign_refusal` | (6)'s message |

### `build_bundle_base`, step by step, with the peer each step reuses

1. No-git checks first (new `:766`–`:792`): `d`'s target via `publish._resolve_target`; the
   members via `_fold_candidates` (base `:217`), so a member with no patch adds nothing, as
   in a fold. A member with a patch but no target, on another target, or unpublished raises
   before any git step. The member checks are the same as v4's, which the brief marks as
   reviewed sound for (1)–(5).
2. Lock and worktree (new `:803`, `:809`): `integ_lock(_integ_worktree(repo, base))`, the
   same per-target lock and tree a fold takes (base `:280`, used at `:538`), failing closed
   if it is not taken (same wording as base `:542`). Then `_prepare_worktree` (base `:1565`),
   which runs `_fetch` (base `:1533`): origin pruned, base remote last.
3. Each member's tip read once (new `:810`), as a fold reads it (base `:594`–`:597`). That
   one commit is used for the carried check, the cut-point check, the merge and the
   ownership rule.
4. #633 carried check (new `:811`–`:821`): `_carried_rewrite` (base `:739`) against the
   run's line name, exactly as `_carried_tips` (base `:726`) calls it. Before any merge.
5. Cut-point trust (new `:822`–`:826`, `_member_cut_point` new `:862`): only for members
   whose branch resolves. Before any merge.
6. Fresh start (new `:827`–`:830`): note origin's copy of the branch, `_reset_tree(wt, "HEAD")`
   (base `:1513`) then `checkout -B <branch> <base_remote>/<base>`, as a fresh fold does
   (base `:565`–`:567`).
7. Merge each member (new `:832`–`:841`) with `_merge_published` (base `:810`), so a gone
   branch goes to `_gone_branch` (base `:882`) and every clean merge to `_keep_merge` (base
   `:850`, the #673 revert check). A `_Conflict` becomes `_member_clash`.
8. Ownership (new `:842`–`:846`): `pushed_tip` (base `:186`) reads the result, then
   `_unowned_work` and `_foreign_refusal`.
9. Push (new `:847`–`:858`): plain `push origin <branch>` when origin had no such branch,
   else `push --force-with-lease=<branch>:<tip fetched> origin <branch>`. Mirrors the fold's
   fresh/continue split (base `:681`–`:690`) with its message shape and remedy.
10. Returns `(branch, tip)`. `carried` is read only. The run's line is never checked out,
    reset or pushed.

### The ownership rule — criterion (6), as the human decided it at Plan

- Cut point (new `:900`–`:912`): `publish.read_stack_base_tip(m)` (publish.py `:690`) when
  `publish.read_stack_base(m)` (publish.py `:679`) is non-empty, else none.
- Own work (new `:976`–`:979`): `git rev-list --no-merges <head> --not <base_remote>/<base>
  [<cut>]`. Same shape as `foreign_commit` (base `:252`–`:263`), with the cut point next to
  the base.
- Rule (new `:972`–`:980`): every commit of `git rev-list --no-merges --topo-order <result>
  --not <base>` must be in some member's own work. Otherwise refuse before the push.
- Message (`_foreign_refusal`, new `:983`): the first such commit (and how many more), the
  first member in member order whose head reaches it (`_in_line`, base `:1186`), and each
  `excluded` bundle whose head is in the clone and reaches it. Otherwise it says "No bundle
  of the run owns it". It also notes any excluded head the clone lacks. `excluded` never
  decides: it is read only after the refusal is already decided (new `:844`–`:846`).
- No `pdca-integration/*` ref is read for ownership. The only origin ref read at all is
  `origin/<this bundle's base>` (new `:827`), and only to choose plain push or force push,
  which (3) requires.
- Fail closed (`_member_cut_point`), naming the member and "Re-publish <member> …":
  (iii) `onto` from `_published_ref` (base `:195`, new `:896`); (i) stack base but no tip
  (new `:902`–`:906`); (ii) tip not an ancestor of the head, or missing from the clone
  (`_carries`, base `:934`, new `:907`); (iv) no stack base but `publish.json` `"mode":
  "stacked-pr"` (written at publish.py `:429`) or `brief.stacks_on` non-empty (brief.py
  `:227`) (new `:913`–`:925`). (iv) reads only the bundle's own files.

## Readings and judgment calls (for the human)

1. **"declare the conflict / re-order" in a member-vs-member clash.** Criterion (4) says
   that wording (base `:842`) "stays for clashes between two bundles, and the new code never
   shows it for a base build". "base build" can mean "a clash with the base" or "any build
   of a bundle base". I wrote messages that satisfy both readings. The base clash names
   `origin/main` and says to rebuild the member's branch on it. The member clash names both
   members and the files, and says "Plan one of them to build on the other and re-drive it",
   without the literal phrase. `_merge_published`'s own message is never passed through
   (new `:941`–`:960`). The fold still shows it, unchanged. If the human wants the fold's
   exact wording for member clashes, that is a one-line change in `_member_clash`.
2. **Gone members skip the cut-point checks** (new `:825`). (4) says a gone member is judged
   as the fold judges it. On a base started from `<base_remote>/<base>`, `_gone_branch`
   either skips the member (the branch already has its merged head, base `:909`–`:913`) or
   raises: `_take_in_base` (base `:931`) needs a head the base has and the branch lacks, and
   the branch contains the base. So a gone member never adds work, and refusing it for its
   cut point would only be a false refusal. Its own work is empty. If its merged head
   reaches the result only through another member's cut point, that work counts as nobody's
   and the build refuses (fail closed, accepted).
3. **Owners named by the #623/#673 messages are the members** (new `:836`, `owners=tuple(mine)`),
   not the batch as in the fold (base `:572`–`:575`). On a fresh bundle base, the only work
   above the base is the members', so nobody else can own a path the check finds. This
   also keeps `fold`'s body untouched (v4 moved those lines out into `_owners`).
4. **(e)(i) is pinned by its message.** A member really published from a no-tip stack base
   gets `publish.json` `"mode": "stacked-pr"` (publish.py `:238`, `:429`). So a build that
   detects the record only through `read_stack_base_tip` still refuses, via (iv). The test
   keeps that realistic record and asserts the (i) reason ("has a recorded stack base (…)
   but no recorded tip"), so the tip-only build goes red on the message (experiment 3
   below). It also goes red against a build with no ownership check (experiments 1 and 2).
5. **(e)(iv-b) writes `"mode": "new-pr"`**, so that only the brief's `Stacks on: X` shows
   the member was stacked. A real legacy `Stacks on:` publish writes `stacked-pr`, which
   (iv-a) already covers. This isolates the second condition. The test's comment says so.
6. **(h)'s "Q's own base built from [Q]"**: built as M's base, `build_bundle_base(cfg, M,
   [Q])` (branch `…-bM`). M is cut from it, with that tip recorded as M's cut point. Q is
   "wave 0" here in the sense that matters: published from `origin/main`, no stack base.
7. **The shared integration worktree is left on the bundle base** after a build, as a fold
   leaves it on the line. The next fold resets it (base `:565`–`:566`), and test (1) runs
   the run's continuing fold right after a build to show that. A caller that re-gates the
   run's line must do so under the fold's lock, as `flow._fold_lines` already does. That
   is #724's to respect when it calls this.

## Rejected alternatives (cost shown)

- **v4's `_foreign_work`** (first-parent chains plus a fence over every
  `refs/remotes/origin/pdca-integration/*`). Rejected by the brief. Its answer depends on
  refs that exist on origin, which is exactly what (6)(b) (line rebuilt) and (6)(c)
  (excluded branch fast-forwarded through the member) change. The cut-point rule is
  `rev-list` over recorded SHAs only: `_unowned_work` is 18 lines against v4's 77-line
  `_foreign_work`.
- **Moving the `owners` loop out of `fold`** (v4's `_owners`): 8 lines out of `fold` (base
  `:568`–`:575`) plus a new 12-line helper, that is, an edit to `fold`'s body, which the
  brief says not to make by default. Not needed (reading 3).
- **Running (i)/(iii)/(iv) before the fetch, for every member, gone ones too.** This would
  refuse before any git step, but it breaks (4) for a gone stacked member that the fold
  would skip (reading 2). It gains no safety. The checks cost one extra `rev-parse` per
  member after a fetch that has to run anyway.
- **Adding a `locks=` keyword like `fold`'s.** No caller needs it yet (#724 may add it). Not
  part of the contract.

## Evidence (all real git, all offline)

### C4 — the project's gate script, as configured in `pdca.toml`

`PDCA_BUNDLE=…/results/issue_723 PDCA_WORKTREE=…/pdca-harness.pdca-wt ./engine/scripts/run-verify.sh`
→ exit 0, `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`. Green leg:
`Ran 26 tests … OK`. Red leg (production hunks reverted): `Ran 26 tests … FAILED (errors=26)`,
26 × `AttributeError: module 'pdca_harness.integrate' has no attribute 'build_bundle_base'`,
each raised inside a test body (the module loads; no `_FailedTest`). Afterwards the worktree
was checked to match `patch.diff` exactly.

### Stub experiments (temporary edits in the worktree, run with the documented module command, then reverted; worktree re-checked byte-identical to patch.diff)

1. **Ownership check skipped** (`_member_cut_point` → `None`, `_unowned_work` → `[]`):
   11 FAIL, each `AssertionError: IntegrationError not raised`: 6a, 6b, 6c, 6d, 6e_i, 6e_ii,
   6e_iii, 6e_iv_a, 6e_iv_b, 6h-without-Q, excluded-head-unchecked. The other 15 pass.
2. **Only the trust checks skipped** (`_member_cut_point` → `read_stack_base_tip(m) or None`,
   foreign check live): 5 FAIL, `IntegrationError not raised`: 6e_i, 6e_ii, 6e_iii,
   6e_iv_a, 6e_iv_b. In each, the build pushes a base holding X's work.
3. **Tip-only stack-base detection** (`read_stack_base` → `read_stack_base_tip`): 1 FAIL,
   6e_i, on its message (`'issue_P has a recorded stack base (…) but no recorded tip' not
   found in 'issue_P was published stacked (its publish.json records "mode":
   "stacked-pr"…'`).
4. **Revert check skipped** (`_keep_merge` → `return`): 1 FAIL, the (4) revert test,
   `IntegrationError not raised`. The revert check does fire on a fresh base. With it
   skipped, B's merge drops `a.txt` and the ownership rule does not catch it: the revert
   commit and A's commit both count as B's own work.

### Which red each case shows

| test (line in the test file) | criterion | pre-fix red | red with the check stubbed |
|---|---|---|---|
| `test_a_bundle_base_holds_exactly…` (`:167`) | (1) | AttributeError | — |
| `test_the_name_is_the_line_then_b…` (`:194`) | (2) | AttributeError | — |
| `test_creating_pushes_plainly…` (`:225`) | (3) | AttributeError | — |
| `test_a_refused_force_push…` (`:242`) | (3) | AttributeError | — |
| `test_two_members_that_clash…` (`:257`) | (4) | AttributeError | — |
| `test_a_clash_with_the_base…` (`:266`) | (4) | AttributeError | — |
| `test_a_gone_member_not_known_merged…` (`:281`) | (4) | AttributeError | — |
| `test_a_gone_member_whose_pr_merged…` (`:294`) | (4) | AttributeError | — |
| `test_a_member_that_brings_in_a_revert…` (`:313`) | (4) | AttributeError | exp. 4: not raised |
| `test_a_rewritten_carried_member…` (`:345`) | (5) | AttributeError | — |
| `test_6a_…` (`:360`) | (6)(a) | AttributeError | exp. 1: not raised |
| `test_6b_…` (`:376`) | (6)(b) | AttributeError | exp. 1: not raised |
| `test_6c_…` (`:390`) | (6)(c) | AttributeError | exp. 1: not raised |
| `test_6d_…` (`:408`) | (6)(d) | AttributeError | exp. 1: not raised |
| `test_6e_i_…` (`:421`) | (6)(e)(i) | AttributeError | exp. 1, 2: not raised; exp. 3: wrong reason |
| `test_6e_ii_…` (`:431`) | (6)(e)(ii) | AttributeError | exp. 1, 2: not raised |
| `test_6e_iii_…` (`:445`) | (6)(e)(iii) | AttributeError | exp. 1, 2: not raised |
| `test_6e_iv_a_…` (`:461`) | (6)(e)(iv-a) | AttributeError | exp. 1, 2: not raised |
| `test_6e_iv_b_…` (`:476`) | (6)(e)(iv-b) | AttributeError | exp. 1, 2: not raised |
| `test_6f_…` (`:494`) | (6)(f) must-not-raise | AttributeError | stays green |
| `test_6g_…` (`:508`) | (6)(g) must-not-raise | AttributeError | stays green |
| `test_6h_a_member_cut_from…` (`:520`) | (6)(h) must-not-raise | AttributeError | stays green |
| `test_6h_without_the_member…` (`:532`) | (6) extra: (h)'s rule binds | AttributeError | exp. 1: not raised |
| `test_an_excluded_head_this_clone_lacks…` (`:548`) | (6) `excluded` only names | AttributeError | exp. 1: not raised |
| `test_a_member_also_listed_as_excluded…` (`:560`) | contract | AttributeError | — |
| `test_a_member_with_a_patch_but_no_target…` (`:569`) | contract | AttributeError | — |

### Criterion (7) — existing tests

The project's T3 script, with the patch applied:
`PDCA_WORKTREE=…/pdca-harness.pdca-wt ./engine/scripts/run-suite.sh` → exit 0, and
`PDCA-EVIDENCE: root suite OK, driver suite OK`. Root suite: `Ran 24 tests in 71.830s OK`.
Offline driver suite: `Ran 2552 tests in 113.552s OK (skipped=2)`. That is the existing 2526
plus these 26 (v4's run of the same suite had 2526 + its 32). Every
`test_integrate_*.py` and `test_flow_*.py` is in that run, unchanged. No caller changed.

## Refuting my own test (the three forced questions)

- **(a) Genuine red?** Yes. With the production change reverted (the C4 gate's red leg),
  all 26 tests run and fail with `AttributeError` raised in the test body. With only the
  ownership check stubbed, every (6)(a)–(e) refusal test fails with `IntegrationError not
  raised`. With only the trust checks stubbed, each (e) sub-case fails the same way. With
  the revert check stubbed, the (4) revert test fails.
- **(b) Production path?** Yes. Every case calls `integrate.build_bundle_base` itself, and
  `integrate.fold` for the comparisons, against real git: a bare `origin`, the primary
  checkout, the real integration worktree and lock. Nothing in `integrate` is mocked. The
  only patches are the fixture's `merged.merged_head` / `merged.is_merged` answers (the
  host's word on a merged PR, `sb._merged_heads`) in the two gone-member tests, and a
  spy that wraps `integrate._git` and calls the real one, to see the push argv and the
  absence of pushes.
- **(c) Fixture includes the fault?** Yes. Each refusal case builds the dangerous history
  for real: a member branch cut from a line commit that really holds X's commit, pushed to
  the bare origin; the line really force-rebuilt without X (6b); X's branch really
  fast-forwarded through P's head (6c); a real stray commit (6d); real `stack-base` /
  `stack-base-tip` files written by `publish.write_stack_base` / `clear_stack_base`; a real
  `Onto branch` record whose branch carries the other PR's commit; `next` really merging
  and reverting A on origin, with B really updated from it, while main has neither, so the
  revert check fires on the fresh base. The must-not-raise cases hold the risky shapes too:
  C, outside the set, really holds A's commits (6f); A really has main and a topic merged
  in by hand (6g); M really sits on a base built by `build_bundle_base` (6h).

## Commit-readiness

The target configures no formatter, linter or pre-commit hook: no `.pre-commit-config.yaml`,
no ruff / flake8 / black config, no `core.hooksPath`; CI runs only render-check, docs-check
and docs. Both files keep the module's 100-column limit (`awk 'length > 100'` finds
nothing) and parse. The commit needs a DCO sign-off (CONTRIBUTING.md), which publish adds
(`commit -s`, publish.py `:311`).

## One slip to report

I wrote one file outside the harness roots: `/tmp/claude-c4-723.log`, the captured output
of the C4 run above. It is plain test output. I left it in place: cleanup is the harness's
job, and I did not want to run `rm`. Every later run was piped, with no file written.

No external dependency was missing: Python 3.14 and git 2.53, offline. Nothing here needs
a display. No NEEDS-HUMAN item from Do, beyond the wording choice in reading 1.
