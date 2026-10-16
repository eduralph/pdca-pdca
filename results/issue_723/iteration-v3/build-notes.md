# Build notes — issue 723, iteration 3 (`build_bundle_base`)

Base: the run's line `pdca-integration/main-r547f8028520f` at `489e5fb`, in the worktree
`/home/eddie/pdca/pdca-harness.pdca-wt`. Lines marked "base" are on `489e5fb`; the rest are in
the patched files. Files touched: `template/src/pdca_harness/integrate.py` and the new
`template/tests/test_integrate_bundle_base.py` (a copy is in this bundle). No other file, and no
existing test, changes.

I started from the iteration-2 patch (`iteration-v2/patch.diff`). Its design was not rejected:
a sibling `build_bundle_base`, not a `fold` keyword. What was rejected is the rule that decides
whose work a shared commit is. That rule is replaced here. Everything else from iteration 2 is
kept, plus two small items the iteration-2 code review raised.

## The carry-forward finding: a refold made a member's commits look like C's

The iteration-2 rule (v2): an excluded bundle E's work was
`rev-list --no-merges E --not <base> <every other bundle head E holds>`. The heads were the
members' merged heads, their recorded heads (`carried`), and the other excluded heads. That only
works while E still holds a head of the member's branch. The reviewer's probe broke it: C is cut
from the run's line (so it holds A's `a2`), A gets `a3`, and the run folds again, so the record
moves to `a3` too. Now neither of A's heads is in C's history, nothing is subtracted, A's `a1`
and `a2` count as C's work, and building B's base from `[A]` is refused. Any rule built on "which
heads E holds" has this hole, because heads go stale as soon as a branch moves on.

### The new rule: read the first-parent chains

`_foreign_work` (`integrate.py:907`). A first-parent chain is the list of commits a branch was
built along: start at its head and keep taking the first parent, down to the base. In this
harness every fold merge is `git merge --no-ff` made on the line (base `integrate.py:1211`), so
the line's first parent is the line and the bundle comes in as the second parent. A branch cut
from the line therefore has the line's merges on its chain, and the bundles' commits off it.

For each excluded head E:

1. `work` = `rev-list --no-merges E --not <base> <other heads that lie on E's chain>`
   (`:947`). This is `foreign_commit`'s shape (base `:252`). The heads subtracted are only
   those on E's own chain: E was cut from that bundle's branch there, so what is under that
   head is that bundle's.
2. A commit of `work` counts as E's when it is on E's chain, or when it is on no other bundle's
   chain (`:949`). So a commit that came into E through a merge belongs to whichever bundle has
   it on its own chain. A commit on E's own chain always stays E's.
3. "Other bundles" are the members' merged heads, the members' recorded heads (`carried`), and
   the other excluded heads (`:939`, `:944`). Each chain is one
   `rev-list --first-parent <head> --not <base>` (`:940`), the same command `_cut_point` uses
   (base `:1045`).

Why it fixes the probe: C's chain is `c1` plus the line's merge commits. A's `a1`/`a2` are not
on it, and they are on A's chain (`a3 → a2 → a1`). So they are A's, whatever A's head or record
is. No head needs to still be held.

Every case the brief names still comes out right:

- Red case (P cut from an old line holding X): X's commits are on X's chain, and P's chain has
  only `p1` and the line's merges. So they stay X's, and the build is refused, naming X and P.
- Must-not-raise case (C cut from the line after wave 0): C owns only `c1`, which is not on
  B's base. The build succeeds.

### Tests for the finding

- `test_a_member_refolded_after_it_moved_on_keeps_its_work` (`test_integrate_bundle_base.py:352`):
  the reviewer's probe. It runs a real second `fold` (with `folded_this_run`), which takes `a3`
  and rewrites the record. The test asserts the record now holds `a3` and that `a3` is not in
  C's history. Then the build succeeds and B's base holds A's three commits and nothing of C or Z.
- `test_a_member_that_moved_on_keeps_its_work_with_no_record_at_all` (`:366`): the same with no
  record passed. The rule no longer needs the record for the line case.
- `test_a_member_that_moved_on_since_an_excluded_bundle_was_cut_keeps_its_work` (`:341`): the
  iteration-1 finding (record still at `a2`), kept.

Shared set-up: `_c_cut_from_the_line_then_a_moves_on` (`:118`), checked by `_assert_a_only`
(`:131`).

Extra probes run in memory (not shipped, same fixture, real git), all passing: refold with
`[A]` only and with `[A, Z]`; C updated from a moved `main` ("Update branch") after the refold;
A updated from `main` (its head a merge commit) then refolded; and a member Y cut from the line
with D built from `[A, Y]`, refused naming Z and Y.

## Other changes (from the iteration-2 code review)

- **Names are compared as bundle names.** v2 dropped an excluded name only if it matched a
  member exactly, so `"A"` and `"issue_A"` counted as two bundles, and a member listed under its
  plain id was judged as excluded. That was a false refusal (v2 refused, as shown below). Now
  `_bundle_name` (`integrate.py:717`) normalises the names in `excluded` and `carried`, and
  members are matched against all member paths (`:798-800`), including ones with no patch.
  Test: `test_a_member_also_listed_as_excluded_is_a_member` (`:475`).
- **`_member_clash` reuses `_held_by`.** The reviewer noted it repeated `_held_by`'s
  partner search (base `:1261`). It now calls `_held_by(wt, branch, head, base_ref, merged_in)`
  (`integrate.py:896`) and keeps only its own wording. The base-clash check still comes first,
  with its own message (`:888-894`). Cost: on the error path only, `_held_by` repeats the one
  base trial merge. The existing clash tests (`:228`, `:235`) pass unchanged.

## Criterion (6): the rule versus the brief's wording (the C1 item for the human)

The brief's literal argv, `rev-list --no-merges <excluded head> --not <base> <member heads…>`,
can never fire on a branch started fresh from the base. Every non-merge commit on such a
branch is reachable from the base or from a member head, so subtracting all member heads
leaves nothing that is on the branch. In the brief's own red case, P's head reaches X's commit,
so `--not <P's head>` removes it. The brief allows "reuse it or its rule". I kept the shape (the
same `rev-list --no-merges <head> --not <base> <heads…>`) but changed which heads are subtracted,
and added the chain test. The human should confirm this reading at sign-off. It is deferred
finding "C1 Spec" in `deferred-findings.json`.

## Known limits (each checked on real git, in memory)

- **Cut from a member's middle commit, no matching record: refused (the safe side).** E is cut
  from `fix/M` at `m1`, then M moves to `m2`, and there is no record of `m1`. `m1` is on both
  chains and neither branch was cut from the other's current head, so it counts for both and
  the build is refused. This is the mirror of a case that must refuse (P cut from X's `x1`,
  X then at `x2`: test `:405`), and git cannot tell the two apart. With the run's record at
  `m1`, E was cut from M's recorded head and the build succeeds (test `:387`). The
  iteration-2 code review already accepted this trade-off.
- **A fast-forward onto a branch cut from it: let through (the one silent case).** H is cut from
  E at `e1`, then E's author fast-forwards `fix/E` onto H's head and adds `e2`. E's chain then
  passes H's head, so `e1` is credited to H, and building D from `[H]` holds `e1`. Git cannot
  tell this from E simply being cut from H's head (the case at `:374`, which must succeed). It is
  written in `_foreign_work`'s docstring. It needs an author to fast-forward their own PR branch
  onto a branch that was itself cut from theirs. No harness step does that.
- **A member whose head is a "reverse" merge.** If a member's author ran `git merge` on `main`
  and pushed that onto the PR branch (so `main` is the first parent), the member's own commits
  are off its chain. After a refold, a bundle cut from the line would claim them, and the build
  is refused. GitHub's "Update branch" merges the other way round (probe above: it passes).
- **Mutual history: refused.** P is cut from X at `x1`, then X merges P back. v2 subtracted P's
  head (held by X), dropped `x1`, and built D's base from `[P]` with X's `x1` on it (checked in
  memory against v2's rule). The new rule keeps `x1` as X's, because it is on X's chain. Test:
  `test_an_excluded_branch_that_merged_a_member_back_still_owns_its_commits` (`:420`).

## Rejected alternatives (with costs)

- **Keep v2's rule and pass every head the run ever recorded for a member.** This needs
  `carried` to hold a list per bundle instead of one head. `fold` overwrites it
  (`carried.update(took)`, base `:692`), and `_carried_tips` (base `:697-736`) and
  `rewritten_carried` (base `:755-807`) read one head per bundle, so all three would change.
  That is a fold and caller change, out of scope ("changes no caller"; fold's body changes only
  where a helper is factored out). It also still fails the no-record case and the mutual case.
- **#673's walk: `_own_commits` with the run's line chain as the stop set** (base `:1134-1143`,
  `:1157`). It is about the same size: read the line tip, `_cut_point`, the stop set, one walk
  per head, about 6 lines against this rule's 4 (`:940-946`). But it judges only bundles cut
  from the line as it is now. A bundle cut from an earlier line of the same batch, which a
  run's fresh first fold replaces (module docstring `:30-32`), or from a per-bundle base (what
  #724 will cut from), walks through those old merges and claims the members' commits again.
- **Subtract `merge-base(E, other head)`.** One line, but wrong. It fails the brief's red case:
  when P holds X, `merge-base(X, P)` is X's head, so all of X's work is subtracted.
- **Chain only (a commit is E's only if it is on E's chain).** Simpler, but merged-in work never
  counts. An excluded bundle whose change is a topic branch merged into its PR branch (a shape
  the existing suite supports, `test_integrate_stack_bases.py:544`) would slip through. Pinned
  by `test_an_excluded_bundles_work_merged_into_its_branch_is_still_its_work` (`:308`).

## Which red each case shows

23 cases in `template/tests/test_integrate_bundle_base.py`. Only `pdca_harness.integrate` is
imported. Every case reaches `integrate.build_bundle_base` / `bundle_base_branch` inside its
body. The `StackFoldGit` fixture is loaded by path and used as a helper object, as
`test_flow_same_wave_conflict.py:56` does.

- **Production change reverted (the C4 red leg):** `engine/scripts/run-verify.sh`: `Ran 23 tests
  … FAILED (errors=23)`. All 23 are
  `AttributeError: module 'pdca_harness.integrate' has no attribute 'build_bundle_base'`, with
  0 load failures (`_FailedTest`), so the module loads and every case runs. Green leg: `Ran 23 …
  OK`. Verdict: `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`
  (`.c4-local.log` in this bundle).
- **Iteration-2 behaviour** (its ownership rule and raw name matching swapped in, in memory)
  fails 4 cases: the refold case and the no-record case (`… which is issue_C's work`, the
  reviewer's finding), the mutual case (built with X's commit on it), and the by-id names case
  (`… which is A's work`). Before I added the last 4 cases, I also ran the file against the
  real iteration-2 code (its patch applied, unchanged): 19 ran, and exactly the refold,
  no-record and names cases failed.
- **Mutations of the new code** (each swapped in memory; the file was never edited for this).
  Every one turns at least one case red:

| mutation | cases that go red |
|---|---|
| `own = all work` (no chain test) | the 4 line-topology must-not-raise cases + mutual |
| drop "on its own chain" | cut from X's branch (`:405`), mutual (`:420`) |
| chain only (merged-in work never counts) | topic merged into X's branch (`:308`) |
| drop "under another head on the chain" | cut from M's branch (`:374`), from M's recorded head (`:387`) |
| drop `h != head` | E committed onto M's branch (`:439`) |
| recorded heads not passed | cut from M's recorded head (`:387`) |
| names compared raw | member listed by id (`:475`) |
| `_keep_merge` a no-op (no revert check) | revert brought by B (`:251`) |
| no missing-head check | excluded head the clone lacks (`:449`) |
| no carried-rewrite check | rewritten carried member (`:284`) |
| no foreign-work check | the 6 refusal cases of (6) |
| base clash worded as a bundle clash | clash with the base (`:235`) |
| always force-push | create pushes without force (`:195`) |
| the iteration-2 rule | refold (`:352`), no record (`:366`), mutual (`:420`) |

| case (line) | criterion | post-fix assertion |
|---|---|---|
| `…holds_its_members_and_nothing_else` (:151) | (1) | branch `<line>-bB` on origin at the returned tip; both A commits in, both Z commits out; `tip^1` is `main`; line tip and the run's record unchanged |
| `…line_plus_b_and_the_flattened_id` (:175) | (2) | exact `pdca-integration/main-r<key>-b12`; `12`/`1-2`/`1/2` → `-b12`/`-b1-h2`/`-b1-s2`, distinct, no `/` after `pdca-integration/` |
| `…creating_pushes_without_force_and_rebuilding…` (:195) | (3) | `_pushes` argv: create has no `--force…` and no `+`; the rebuild has `--force…` and does not hold origin's old copy |
| `…refused_force_push_names_the_branch_and_the_remedy` (:213) | (3) | `denyNonFastForwards` plus a non-ancestor at the name: raises naming the branch, `delete`, `pdca-integration/*`; origin unchanged |
| `…two_members_that_clash_are_both_named` (:228) | (4) | names `issue_Y`, `issue_A`, `c.txt`, "declare the conflict"; no push |
| `…clash_with_the_base_says_rebuild_not_reorder` (:235) | (4) | names `origin/main`, "Rebuild"; no "declare the conflict"/"re-order"; no push |
| `…gone_member_not_known_merged…` (:244) | (4) | `_gone_branch`'s message; no push |
| `…brings_a_revert_of_an_earlier_members_work…` (:251) | (4) | #673 refusal for D's base, and the same refusal from the run's fresh fold; no push |
| `…rewritten_carried_member…before_any_merge` (:284) | (5) | names the rewrite, the recorded head, D's base; no `merge`, no `push` |
| `…cut_from_an_old_line_cannot_bring…` (:298) | (6) red | X's commit named as `issue_X`'s work, brought by `issue_P`; no push |
| `…work_merged_into_its_branch_is_still_its_work` (:308) | (6) red | X's topic commit named as `issue_X`'s work, brought by `issue_P` |
| `…cut_from_the_line_does_not_claim_a_members_work` (:330) | (6) must-not-raise | builds; A in, C and Z out |
| `…moved_on_since…keeps_its_work` (:341) | (6), iteration-1 finding | builds; A's three commits in, C and Z out |
| `…refolded_after_it_moved_on_keeps_its_work` (:352) | (6), iteration-2 finding | builds after a real refold took `a3`; same assertions |
| `…moved_on_keeps_its_work_with_no_record_at_all` (:366) | (6) | builds with no record; same assertions |
| `…cut_from_a_members_branch_does_not_claim_its_work` (:374) | (6) must-not-raise | E cut from `fix/M`: builds; M in, E out |
| `…cut_from_a_members_recorded_head_does_not_claim_it` (:387) | (6) must-not-raise | E cut from M at the recorded head, M moved on: builds |
| `…cut_from_an_excluded_bundles_branch_cannot_bring_it_in` (:405) | (6) red | P cut from X at `x1`, X moved on: `x1` named as X's work, brought by P |
| `…merged_a_member_back_still_owns_its_commits` (:420) | (6) red | X merged P back: `x1` still X's work |
| `…committed_onto_a_members_branch_is_refused` (:439) | (6) red | one branch for M and E: E's commit named, brought by M |
| `…excluded_head_this_clone_lacks…` (:449) | (6) | refused before any merge, naming the missing head; once fetched, refused as X's work |
| `…member_also_listed_as_excluded_is_a_member` (:475) | members exact | ids without `issue_`: A is a member, the build succeeds |
| `…patch_but_no_target…` (:487) | members exact | refused before any git step |

## Refute-your-own-test

- **(a) Genuine red? Yes.** `run-verify.sh` reverted the production hunks in place and re-ran
  all 23 cases. All 23 errored on the missing `build_bundle_base`, none failed to load, and the
  script then restored the tree (`git apply --check -R patch.diff` passes on it afterwards).
  Beyond that whole-function red, the iteration-2 behaviour fails the 4 cases above, and each of
  the 14 mutations in the table turns at least one case red.
- **(b) Production path? Yes.** Every case calls the shipped `integrate.build_bundle_base` /
  `bundle_base_branch` (and real `integrate.fold` where the scenario needs the run's line) against
  real git: a bare `origin`, a primary checkout, the real integration worktree
  (`_prepare_worktree`), and real fetch, merge and push. Only two things are patched:
  `merged.merged_head` / `is_merged`, in the gone-member case only (the host's PR state; there
  is no `gh` offline; the fixture's `_merged_heads`); and `integrate._git`, wrapped by a spy that
  records each argv and then calls the real function (`_refused` `:73`, `_pushes`).
- **(c) Fixture includes the fault? Yes.** The refold case runs a real second fold and asserts
  the record moved to `a3` and that `a3` is not in C's history. The moved-on cases really push
  `a3` after C was cut. The stacked cases really cut `fix/E` / `fix/P` from `fix/M` / `fix/X`.
  The mutual case really merges `fix/P` back into `fix/X`. The topic case really merges a topic
  branch into `fix/X`. The missing-head case pushes to a bare repo the primary never fetches.
  The revert case really merges and reverts on `next`. The refused push really sets
  `receive.denyNonFastForwards` and puts a non-ancestor at the name.

## Criterion (7): the existing suites

`engine/scripts/run-suite.sh` (the T3 runner) on the final patched worktree: root suite
`Ran 24 tests … OK`; driver suite `Ran 2549 tests … OK (skipped=2)` (`.t3-local.log`). That is
iteration 2's 2540, minus its 14 cases of this file, plus these 23. Every `test_integrate_*.py`
and `test_flow_*.py` module is in that run, and `git diff --stat 489e5fb -- template/tests/`
lists no tracked test file. `fold`'s body changes only where `_owners` was factored out
(`integrate.py:581`, base `:568-575`).

## Commit-readiness

The target has no formatter, linter or commit hook: no pre-commit config, only git's sample
hooks, and the CI workflows are docs, render and issue-linking. It requires Python 3.11 or newer
(`template/pyproject.toml.jinja:10`), and the only interpreter here is 3.14. So I checked with the
tokenizer that no f-string field reuses its quote, holds a backslash or holds a comment (3.12-only
syntax), after testing that the check flags such a line. Also checked: no line over 100 columns,
no trailing whitespace, no unused imports (AST), and both files compile. The commit needs a DCO
sign-off (`git commit -s`), which publish adds.

## Housekeeping (left in place: no deletes, per the harness rules)

- `.c4-local.log` and `.t3-local.log` in this bundle: my final local runs of the C4 and T3
  runners (they overwrite iteration 2's copies).
- The new test file is untracked in the worktree, as before. I used `git add -N` only to produce
  `patch.diff`, then `git reset` it.
- The mutation and probe runs were Python fed on stdin, so no scratch files were written. Their
  repos are the fixture's own temp dirs, removed by its `tearDown`.
