# Build notes — issue 723, iteration 2 (`build_bundle_base`)

Base: the run's line `pdca-integration/main-r547f8028520f` at `489e5fb`, in the worktree
`/home/eddie/pdca/pdca-harness.pdca-wt`. Line numbers marked "base" are on `489e5fb`; the
rest are in the patched file. Files touched: `template/src/pdca_harness/integrate.py` and the
new `template/tests/test_integrate_bundle_base.py` (copy in this bundle).

I started from the v1 patch (`iteration-v1/patch.diff`, which the carry-forward did not
reject as a design) and changed what the three implementation findings and the smaller
advisory notes asked for. The design is the brief's: a sibling `build_bundle_base`, not a
`fold` keyword.

## The three carry-forward findings

### 1. C5: an excluded head this clone lacks let the build push foreign work

v1's `_foreign_work` dropped an excluded head it could not find ("a head this clone does not
have adds nothing"). The reviewer pushed X's newer head to a bare repo the checkout never
fetches, and the build pushed a base that held X's commit.

Fix: before anything is merged, every excluded head must be a commit in the clone after the
fetch; otherwise the build raises, naming each missing head, and pushes nothing
(`integrate.py:806-815`). A falsy head counts as missing. `_foreign_work` now states that it
only ever sees present heads (`integrate.py:891-900`).

Test: `test_an_excluded_head_this_clone_lacks_stops_the_build_before_any_merge`
(`test_integrate_bundle_base.py:306`). It is the reviewer's topology: X folded onto the line,
P cut from the line, X's newer head `x2` pushed to `elsewhere.git`, which the primary never
fetches. The build is refused before any `git merge` runs. The same test then fetches
`elsewhere.git` into the primary (the reviewer's "fetched-head control") and shows that the
identical call is now refused as foreign work, naming X's first commit and P. So the first
refusal is about the missing head, not about something else.

Rejected: also fetching the remotes the excluded bundles' records name (as `fold` fetches
its members'). That is about 4 lines: `cfg.find_bundle(n)` plus `_published_ref` per
excluded name, and their remotes added to `_prepare_worktree(remotes=…)` at
`integrate.py:794`. But it adds a new way to fail. An unreachable remote of a bundle that
`d` does not build on would stop `d`'s build, even when the head is already in the clone.
Failing closed refuses only when the head really is missing. In #724's flow the heads come
from this checkout (the run's `carried` record, or a tip read after a fetch), so they are
present. The reviewer accepted either ("fail closed … or fetch and verify it").

### 2. False refusal when a member moved on after an excluded bundle was cut

v1 subtracted another bundle's head from an excluded bundle's work only when the excluded
head holds it. With C (excluded) cut from the line after wave 0 and A (member) then given a
third commit `a3`, C holds A's old head `a2`, not `a3`. So A's `a1`/`a2` counted as C's work,
and the build raised "… which is issue_C's work".

Fix: the heads the run recorded for members (`carried`, as the line took them) also count
as heads a bundle's work can be credited to. `build_bundle_base` passes each member's
recorded head that is in the clone (`integrate.py:833-835`). `_foreign_work` subtracts any
member, recorded or excluded head that the excluded head holds (`integrate.py:917-921`).
`a2` is an ancestor of C, so A's commits are A's. This is the fix the reviewer suggested.

Test: `test_a_member_that_moved_on_since_an_excluded_bundle_was_cut_keeps_its_work`
(`:287`). The record comes from a real `fold(…, carried=record)`, as #724 will pass it.

Known limit (the same rule `_undone_paths` uses, base `integrate.py:1159-1164`): without a
record, a member that moved on still has its old commits counted as the excluded bundle's,
so the build refuses. That is the conservative side ("refused, never silently widened"), and
#463's carry-forward already asks #724 to record the pre-wave carry's heads too.

### 3. The revert-check test could not fail

v1's revert test compared the bundle base with a fresh fold of the run, and neither refused
anything. The new test, `test_a_member_that_brings_a_revert_of_an_earlier_members_work_stops_the_build`
(`:219`), makes the #673 check fire on a bundle base. A adds `a.txt`. A second branch on
origin, `next`, merges A's PR and then reverts it. B's author merges `next` into `fix/B`.
Built fresh on `main` (which has neither the merge nor the revert), A puts `a.txt` on D's
base, and B's merge would take it off again. The commit that gives `fix/B` its `a.txt`
state is not one of B's own (history simplification follows B's own first parent, which
never had the file). So `_keep_merge` (base `integrate.py:850`) undoes the merge and raises
`merging issue_B's branch origin/fix/B would remove issue_A's work from <D's base>: a.txt
(issue_A) would go back …`. Nothing is pushed. The run's fresh `fold` of `[A, B]` refuses
with the same words for its line, which is the "raises as the run's fold does" part of
criterion (4).

Mutation check: with `integrate._keep_merge` replaced by a no-op, this test fails
("IntegrationError not raised"). So the test needs the check.

Why `next` and not `main`: a revert on the fetched base itself sits below the point where a
fresh base starts. A's head is then already in the base and the merge is skipped, which is
the limit #673 documents (base `integrate.py:1131-1133`). On a base that starts fresh from
`main`, the check can only fire when the revert reaches a member's branch from somewhere
other than `main`. A branch updated from another integration branch is the plain case of
that. The reviewer's own probe (a revert reached from `main` itself) does not refuse, on the
bundle base or on the run's fresh fold. That is the documented limit, not new behaviour.

## Smaller advisory items, also addressed

- **Rewrite message named the run's line.** The #633 check now calls `_carried_rewrite` (base
  `integrate.py:739`, the shared judgment `_carried_tips` and `rewritten_carried` both use)
  under the lock, right after the one fetch (`integrate.py:796-805`). The message ends
  "…would put the old and the rewritten commits on `<D's base>` together. Nothing was merged
  or pushed. Restore `<ref>` to `<head>` …, then re-run". `_carried_tips` (base `:697`)
  fetched a second time, outside the lock, and its words point at the line and say to
  re-issue the run, so the bundle base no longer calls it. Each member's tip is read once
  (`:796`), and that commit is the one checked and merged (`:823`), as #633 requires.
  Neither `_carried_tips` nor `_carried_rewrite` changed.
- **Empty branch slot when no member could be named.** The message now says "a member's
  branch" (`integrate.py:838`), and `_foreign_work` returns `None` for the member (`:925-927`).
  This cannot happen on a branch started from the base: every non-merge commit on it comes
  from the base or a member head.
- **A patched member with no target was dropped without a word.** It now raises before any
  git step (`integrate.py:761-768`). Test `test_a_member_with_a_patch_but_no_target_stops_the_build`
  (`:332`), which asserts no `git` step ran. A patchless member still adds nothing (design
  §1: close-disposition bundles contribute nothing).
- **v1's "nothing pushed" check was empty.** In v1 the list stayed `[]` whenever the call
  raised, because `pushes = self.fx._pushes(…)` never assigned it. The new `_refused` helper
  (`:66`) records every `integrate._git` step, failed ones too, then asserts no `push` ran and
  that origin has no base for the bundle. The rewrite and missing-head cases also assert no
  `merge` ran.
- **`_member_clash`'s fallback** (return the original `_Conflict` when no partner can be
  named) is kept, now with a docstring saying it cannot be reached: on a branch started from
  the base, the branch IS the base until a member merges (`integrate.py:859-868`).

## Criterion (6): the ownership rule (the C1 spec item is still open for the human)

The brief's literal argv, `rev-list --no-merges <excluded head> --not <base> <member heads…>`,
finds nothing in the brief's own red case. `P` was cut from a line holding `X`, so P's head
reaches X's commit and `--not <P's head>` subtracts it. Every non-merge commit of a built
base is reachable from the base or a member head, so the literal rule can never fire.
`foreign_commit` (base `integrate.py:252`) is the right rule for the carry, where the heads
are the ones being kept. Here, the question is whose work a shared commit is.

The rule implemented keeps `foreign_commit`'s shape (non-merges, `--not <base> <heads…>`)
and changes which heads are subtracted. An excluded bundle E's work is
`rev-list --no-merges <E> --not <base> <every other bundle head E holds>`, where "other
bundle heads" means member heads as merged, member heads the run recorded, and other
excluded heads (`integrate.py:917-921`). It is the ownership rule `_undone_paths` already
uses for #673 (base `integrate.py:1159-1164`): a branch that holds another bundle's head
does not own that bundle's commits.

- Red case: X holds no other head. X's commit is X's work, it reaches the base through P,
  and the build raises naming `issue_X` and `issue_P`.
- Must-not-raise case: C holds A's head (and Z's), so their commits are theirs. C's own
  commit is not on B's base, so the build succeeds.
- A commit two heads share while neither holds the other counts for both, so it is refused.
  Example: P cut from X at x1, X later at x2. That is conservative.
- Known gap: the rule cannot see mutual ancestry. If a member was built on E's early commit
  and E later merged that member's head, E's early commit is credited to the member. No
  normal flow does this (a wave-0 branch does not merge a later wave's), and `_undone_paths`
  has the same gap.

## Which red each case shows

`template/tests/test_integrate_bundle_base.py`, 14 cases. Only `pdca_harness.integrate` is
imported. Each case reaches `integrate.build_bundle_base` / `integrate.bundle_base_branch`
inside its body. The `StackFoldGit` fixture is loaded by path and used as a helper object,
as `test_integrate_revert_via_branch.py:48-63` does.

- **Production change reverted** (the C4 red leg, `engine/scripts/run-verify.sh`): `Ran 14
  tests … FAILED (errors=14)`. Every case fails with `AttributeError: module
  'pdca_harness.integrate' has no attribute 'build_bundle_base'` (or `bundle_base_branch`).
  The module loads, and all 14 run. Green leg: `Ran 14 … OK`. Verdict:
  `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`.
- **v1's production code with this test file** (proof the new cases cover the findings):
  4 cases fail.
  - `…moved_on…keeps_its_work`: ERROR, `IntegrationError: … would hold 9e9c2cf8f90e, which
    is issue_C's work` (finding 2).
  - `…excluded_head_this_clone_lacks…`: FAIL, "IntegrationError not raised". v1 built and
    pushed (finding 1).
  - `…rewritten_carried_member…`: FAIL, the message named the run's line, not the base.
  - `…patch_but_no_target…`: FAIL, "IntegrationError not raised".
- **Mutations of the new code**:
  - `_keep_merge` as a no-op: the revert case fails.
  - `recorded=[]` passed to `_foreign_work`: the moved-on case fails, and the plain
    must-not-raise case still passes. So the record matters only when the member moved on.
  - `*under` removed from the work `rev-list` (`integrate.py:920`): both must-not-raise
    cases fail. The red cases still pass.

| case (line) | criterion | post-fix assertion |
|---|---|---|
| `…holds_its_members_and_nothing_else` (:119) | (1) | branch is `<line>-bB` on origin at the returned tip; both A commits in, both Z commits out; `tip^1` is `main`; the line tip and the run's `carried` record unchanged (the record is passed in) |
| `…line_plus_b_and_the_flattened_id` (:143) | (2) | exact `pdca-integration/main-r<key>-b12`; `12`/`1-2`/`1/2` → `-b12`/`-b1-h2`/`-b1-s2`, distinct, no `/` after `pdca-integration/`; `issue_12` gives the same name |
| `…creating_pushes_without_force_and_rebuilding_starts_fresh_and_forces` (:163) | (3) | `_pushes` argv: create has no `--force…` and no `+`; after origin's copy moved, the rebuild has `--force…` and does not hold the old copy |
| `…refused_force_push_names_the_branch_and_the_remedy` (:181) | (3) | `denyNonFastForwards` plus a non-ancestor at the name: raises, naming the branch, `delete` and `pdca-integration/*`; origin unchanged |
| `…two_members_that_clash_are_both_named` (:196) | (4) | names `issue_Y`, `issue_A`, `c.txt`, keeps "declare the conflict"; no push |
| `…clash_with_the_base_says_rebuild_not_reorder` (:203) | (4) | names `origin/main`, `Rebuild`; no "declare the conflict" or "re-order"; no push |
| `…gone_member_not_known_merged…` (:212) | (4) | `_gone_branch`'s message; no push |
| `…brings_a_revert_of_an_earlier_members_work…` (:219) | (4) | the #673 refusal for D's base, and the same refusal from the run's fresh fold; no push |
| `…rewritten_carried_member…before_any_merge` (:252) | (5) | names the rewrite, the recorded head and D's base; no `merge` and no `push` ran |
| `…cut_from_an_old_line_cannot_bring_an_excluded_bundle_in` (:266) | (6) red | names X's commit as `issue_X`'s work and `issue_P`'s branch; no push |
| `…excluded_bundle_cut_from_the_line_does_not_claim_a_members_work` (:276) | (6) must-not-raise | builds; A in, C and Z out |
| `…member_that_moved_on…keeps_its_work` (:287) | (6) must-not-raise, finding 2 | builds; A's three commits in, C and Z out |
| `…excluded_head_this_clone_lacks…` (:306) | (6), finding 1 | refused before any merge, naming the missing head; after a fetch, refused as X's work |
| `…patch_but_no_target…` (:332) | members are exact | refused before any git step |

## Refute-your-own-test

- **(a) Genuine red? Yes.** `run-verify.sh` reverted the production hunks in place and re-ran:
  14 ran, 14 errors (the entry point is gone), then it restored the tree. I checked
  afterwards that `git diff 489e5fb` matched `patch.diff` byte for byte. Beyond that
  whole-function red, v1's code fails the 4 new cases, and the three mutations above each
  turn the case that guards them red.
- **(b) Production path? Yes.** Every case calls `integrate.build_bundle_base` /
  `integrate.bundle_base_branch` from the shipped module, against real git: a bare origin, a
  primary checkout, the real integration worktree (`_prepare_worktree`), and real fetch,
  merge and push. Two things are patched. `merged.merged_head` / `is_merged` go through the
  fixture's `_merged_heads`, in the gone-member case only (the host's PR state; there is no
  `gh` offline). And `integrate._git` gets a spy in `_refused` / `_pushes` that records argv
  and calls the real function.
- **(c) Fixture includes the fault? Yes.** The clash cases commit real conflicting files.
  The base-clash case moves origin's `main`. The gone case deletes `fix/A` on origin. The
  rewrite case force-pushes a rewritten `fix/A`. The refused-push case sets
  `receive.denyNonFastForwards` and puts a non-ancestor commit at the branch name. The red
  case cuts P from a real line that holds X. The moved-on case pushes `a3` onto `fix/A`
  after C was cut. The missing-head case pushes X's new head to a bare repo the checkout
  never fetches. The revert case has `next` really merge and revert A, and `fix/B` really
  updated from it.

## Criterion (7): the existing suites

`engine/scripts/run-suite.sh` (the T3 runner) on the patched worktree, run again after my
last edit: root suite `Ran 24 tests … OK`; driver suite `Ran 2540 tests … OK (skipped=2)`
(v1 had 2537 with 11 cases of this file; the 3 new cases account for the difference).
`PDCA-EVIDENCE: root suite OK, driver suite OK`. Every `test_integrate_*.py` and
`test_flow_*.py` module is in that run, and no existing test file is changed by the patch.
`fold`'s body changes only where `_owners` was factored out (`integrate.py:581`; base
`:568-575`).

The C4 gate (`engine/scripts/run-verify.sh`) was also re-run on the final `patch.diff`:
green `Ran 14 … OK`, red `Ran 14 … FAILED (errors=14)`, `C4 PASS`.

## Commit-readiness

The target has no formatter config and no pre-commit hooks. There is no
`.pre-commit-config.yaml`, and the CI workflows are docs, render and issue-linking only.
`requires-python = ">=3.11"`, and the only interpreter here is 3.14, so I checked the
f-strings with the tokenizer: no replacement field reuses its f-string's quote and none has
a backslash (PEP 701 syntax would break on 3.11). Also checked: no line over 100 columns
(the file's convention), no trailing whitespace, no unused imports (AST scan), and both
files `py_compile`. The commit itself needs the DCO sign-off (`git commit -s`), which
publish adds.

## Housekeeping (left in place, per the harness rules: no deletes)

- `/tmp/.cmp-ignored`: a copy of the diff I wrote by mistake while comparing the worktree to
  `patch.diff`. It is outside the allowed roots. It is harmless, but I could not remove it.
- `results/issue_723/.c4-local.log` and `.t3-local.log`: my local runs of the C4 and T3
  scripts.
- The worktree index has an intent-to-add entry (`git add -N`) for the new test file, so that
  `git diff 489e5fb` includes it. I removed it at the end (`git reset -q -- <test file>`), so
  the file is untracked again, as v1 left it.
