# Build notes — issue 723, iteration 4 (`build_bundle_base`)

Base: the run's line `pdca-integration/main-r547f8028520f` at `489e5fb`, in the worktree
`/home/eddie/pdca/pdca-harness.pdca-wt`. "base `:N`" means `template/src/pdca_harness/integrate.py:N`
on `489e5fb`. A bare `integrate.py:N` or `test :N` is the patched file. Files touched:
`template/src/pdca_harness/integrate.py` and the new `template/tests/test_integrate_bundle_base.py`
(a copy is in this bundle). No other file changes, and no existing test changes.

## Starting point

I started from the iteration-3 patch (`iteration-v3/patch.diff`, which applies cleanly to
`489e5fb`). Its design was not rejected, and all of this is unchanged here:

- the sibling `build_bundle_base` (`integrate.py:723`) and the name helper `bundle_base_branch`
  (`:145`; `integration_branch` and `_flatten_base`, base `:126`, `:154`, untouched);
- `_owners` factored out of `fold` (`:703`, called from `fold` at `:581`; base `:568-575`),
  the only change to `fold`'s body;
- the lock and worktree (`:805`, `:811`, as `fold` takes them at base `:538`, `:546`), the
  tree reset (`:834`), the #633 check (`:813-822`), the missing-head refusal (`:823-832`), the
  merge loop through `_merge_published` (`:839-848`), the clash wording (`_member_clash`,
  `:876`), and the push rule (`:862-872`).

What the carry-forward rejected is the rule in `_foreign_work` that decides whose work a commit
is. Every C5 finding over the last three rounds was about that rule. It is replaced
(`integrate.py:910-986`), and the one bullet of `build_bundle_base`'s docstring that describes
it is reworded (`:752-762`).

## The carry-forward finding, reproduced

Round 3's probe: A's author merges a topic branch into `fix/A` with `--no-ff`, the run folds A,
C is cut from the line, and building B's base from `[A]` with C excluded is refused ("… which is
issue_C's work"). I wrote it as `test_a_topic_merged_into_a_members_branch_is_its_work_not_an_excluded_ones`
(test `:416`) and ran it against the iteration-3 code through the C4 runner: it failed with that
exact message. The cause: the iteration-3 rule gave a commit to another bundle only if it was on
that bundle's first-parent chain. A topic commit is on no first-parent chain, so it fell to C.

All three earlier rules asked "whose is this commit?" from the excluded bundle's side, by matching
heads or chains against it. Each broke on one more ordinary history shape: a member moving on
(round 1), a refold moving the record (round 2), a topic merge (round 3).

## The new rule (`_foreign_work`, `integrate.py:910`)

It asks from the members' side instead, in `foreign_commit`'s shape (base `:252-263`):

1. A bundle's **own branch** is its first-parent chain (`rev-list --first-parent <head> --not
   <base>`, the call `_cut_point` uses at base `:1045`), cut at the first commit on it that is
   another bundle's head: a member's merged head, a member's recorded head (`carried`), or
   another excluded head (`integrate.py:958-964`). The cut handles a branch cut straight from
   another bundle's branch.
2. The **harness branches** are every ref under `refs/remotes/origin/pdca-integration/`: the
   run's line (`integration_branch`) and every bundle base. Their first-parent chains are fold
   merges and belong to no bundle (`:966-972`).
3. **What the members reach**: commits reachable from a member's merged head without passing
   through an excluded bundle's own branch or a harness branch. This reuses `_own_commits`
   (base `:1061-1079`, the #673 walk) with those commits as its stop set (`:973-974`).
4. A non-merge commit on the built base (`rev-list --no-merges --topo-order <tip> --not <base>`,
   `:954`) that the members do not reach is **foreign** (`:975`).
5. A foreign commit is **refused** when an excluded bundle reaches it from its own head without
   passing through what the members reach, another excluded bundle's own branch, or a harness
   branch (`:978-980`). It is named for the first such bundle by name. The member named is the
   first whose head reaches it (`:984-985`, as in iteration 3).

Why this fixes all the findings at once: a member's commits are found by walking from the
member's own head. Nothing depends on the excluded side still holding a current or recorded head
of the member, or on the member's history having a particular shape.

- Round 1 (excluded head not fetched): the refusal before any merge is kept (`:823-832`).
- Round 2 (a refold moves the record): A's walk from its own head reaches all of A's commits.
- Round 3 (topic merged into a member): A's walk follows its own merge into the topic.
- The brief's red case (P cut from a line holding X): P's walk stops at the line's merges, so
  X's commit is foreign, and X's own walk reaches it. Refused, naming X and P.
- The brief's must-not-raise case (C cut from the line): A reaches its own commits, so nothing on
  B's base is foreign.

### Why the harness-branch fence (step 2) is there

My first version had steps 1, 3, 4 and 5 only. It passed every test, both suites and the
probes. Reviewing it, I found a silent case. X is folded onto the line and P is cut from the
line. Then X's author merges `fix/X` into the base "the other way round" and pushes that as
`fix/X` (a fast-forward of it, with the base as the new head's first parent). X's own commit is
now off X's first-parent chain, so it is not fenced, and P's walk reaches it through the line's
merge: D's base from `[P]` holds X's commit and nothing refuses. That breaks the brief's
invariant ("refused, never silently widened"). Real git, `N1` in the mutation table below.

The fence makes the member side the mirror of the must-not-raise case: an excluded bundle cut
from the line holds the members only through the line's merges, and now a member cut from the
line, or from a bundle base, holds the bundles on it only through those merges too. Cost: two
git calls (`for-each-ref`, then one `rev-list --first-parent` over all those refs) and 7 lines
(`:966-972`), plus `lines` added to two stop sets. It fences all of `pdca-integration/`, not just
this batch's line, because #724's members will be cut from bundle bases (`N3` below). Fencing
another batch's line costs nothing: nothing of this run is on it. The namespace string
`pdca-integration/` is the one `integration_branch` uses (base `:141`); if that ever changes,
`:968` has to change with it.

One effect of the fence: a commit on a harness branch that is no member's and no excluded
bundle's (a bundle the caller did not name) is foreign but claimed by nobody, so it is not
refused (`:981-982`). That matches the brief's scope ("the run's bundles that are NOT members").
The iteration-3 rule would only have refused such a commit by blaming the wrong bundle.

## Criterion (6): the rule versus the brief's wording (the deferred C1 item)

The brief's literal argv, `rev-list --no-merges <excluded head> --not <base> <member heads…>`,
can never fire on a branch started from the base: every non-merge commit on it is reachable from
a member head. In the brief's own red case P's head reaches X's commit, so `--not <P's head>`
removes it. The new rule keeps the shape and reads "reachable from a member's head" as
"reachable from a member's head without passing through an excluded bundle's own branch or a
harness branch". With that reading both of the brief's examples come out as the brief says. The
human should confirm this reading at sign-off (deferred finding "C1 Spec").

## Known limits (each run on real git)

- **Gets through: an excluded branch fast-forwarded onto a member's head.** P is cut from X at
  `x1`; X's author then fast-forwards `fix/X` onto P's head and adds `x2`. X's chain now passes
  P's head, so `x1` counts as P's, and D's base from `[P]` holds it. Git cannot tell this from X
  simply being cut from P's head, which must build (test `:571`). Unchanged from iteration 3; it
  is the deferred code-review finding, for the human to decide.
- **Gets through: an excluded bundle merged the other way, after a member was cut from a line
  that was later replaced.** The fence covers the harness branches on origin now. A line
  replaced by a later run's fresh fold (module docstring, base `:30-32`) is gone, so a member cut
  from the old line reaches the excluded commit through merges no longer fenced. It needs both a
  replaced line and a reverse merge. Without the reverse merge the same build is refused.
- **Refused where git cannot tell: an excluded branch cut from a member's middle commit, with no
  record of it.** E is cut from M at `m2`; M moves on to `m3` and the run's record moves with
  it. `m2` is on both chains, and the mirror case (a member cut from an excluded bundle's middle
  commit, test `:602`) has the same shape and must refuse. The message then calls `m2` E's work.
  With the record at `m2` it builds (test `:584`).
- **Out of scope by contract:** a bundle not named in `excluded` is not looked for. The caller
  (#724) names every non-member bundle of the run.

Probes run in memory (same fixture, real git, not shipped), all as expected: a member that merged
the line holding Z (refused, Z); an excluded Z that merged member A (builds); a member cut from
an excluded head (refused); a member rewritten with no record (builds, new commits only); a
member cut from an excluded E that was cut from the line (refused, E); an excluded bundle cut
from member P (builds); an excluded C updated from the base (builds); an excluded C that merged
A's newer head (builds); members across two waves with C cut from the line later (builds), and
the same with Z left out (refused, Z); a member cut from its own bundle base built on a member
(builds) or on an excluded X (refused, X); an excluded C cut from its own base on member A,
then A moving on (builds); the three limits above.

## Rejected alternatives (with costs)

- **Keep the excluded-side rule and only fix topic merges** (walk from each excluded head,
  stopping at other heads and at members' first-parent chains, instead of checking commit by
  commit). About the same size: one chain read and one walk per excluded bundle. Run against
  the final tests it fails 3: it refuses `test_a_member_whose_branch_was_merged_the_other_way_keeps_its_work`
  (`:470`) and `test_a_topic_a_member_and_an_excluded_bundle_both_merged_is_the_members_work`
  (`:485`), and it names C instead of X in `:537`. In those cases the commit is off every chain
  and the excluded bundle reaches it too, so that rule can only refuse. The member-side rule
  with the fence gets all three right.
- **Count as not E's anything another bundle reaches without entering E's own branch.** Fixes
  round 3 too, but a topic two excluded bundles both merged then belongs to neither, and a
  member cut from a line holding one of them brings it in with no refusal. Fails `:500` (run).
- **Read each bundle's recorded cut point (`publish.read_stack_base_tip`).** Exact for wave>0
  bundles cut from the line, but it reads a bundle file for every member, and a legacy
  `Stacks on` bundle has no record. More surface for what the fence already does.
- **Name bundles from the fold merges' messages ("pdca-integrate: issue_A").** Would attribute
  exactly, but this module decides by commit, never by message (`_cut_point`, base `:1041`;
  `_carried_tips`, base `:712`).
- **Fence only this batch's line, not the bundle bases.** One pattern narrower, same cost, but
  misses members cut from bundle bases, which is what #724 produces (`N3` goes red).
- **Fence the members' walk only and let the excluded side's claim walk pass the harness
  branches.** One `| lines` fewer, but a bundle cut from the line then claims what the line
  holds of another excluded bundle and the message names the wrong one (`N2` goes red).

## Which red each case shows

32 cases in `template/tests/test_integrate_bundle_base.py`. Only `pdca_harness.integrate` is
imported. Every case reaches `integrate.build_bundle_base` / `bundle_base_branch` inside its
body. `StackFoldGit` is loaded by path and used as a helper object, as
`test_flow_same_wave_conflict.py:56` does.

- **Production change reverted (C4 red leg):** `engine/scripts/run-verify.sh`: green leg
  `Ran 32 tests … OK`; red leg `Ran 32 tests … FAILED (errors=32)`, all 32
  `AttributeError: module 'pdca_harness.integrate' has no attribute 'build_bundle_base'`, 0 load
  failures (`_FailedTest`). Verdict: `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`
  (`.c4-local.log` in this bundle).
- **The iteration-3 rule** (its `_foreign_work` swapped in, in memory): 4 red, `:416` (the
  reviewer's probe, same message), `:434`, `:470`, `:485`.
- **Mutations of the new code** (each swapped in memory; the file was never edited for this).
  Each turns at least one case red:

| mutation | red cases (test line) |
|---|---|
| N1 no harness fence (my first version) | `:537`, `:557` |
| N2 harness fence for the members' walk only | `:537` (names C, not X) |
| N3 this batch's line only, no bundle bases | `:557` |
| M1 no cut at another bundle's head | `:571`, `:584` |
| M2 recorded heads are not cut points | `:584` |
| M5 name the first excluded head that reaches the commit | `:520`, `:537` |
| M7 a bundle's own head counts as a cut | `:602`, `:617`, `:636` |
| M8 own branch = the head only | `:602`, `:617` |
| M9 no excluded fences | `:602`, `:617`, `:636` |
| M10 own branch = all the excluded head reaches | `:485`, `:571`, `:584`, `:617` |
| M11 merge commits kept in the built list | `:355`, `:500` |
| the iteration-3 rule | `:416`, `:434`, `:470`, `:485` |
| excluded-side walk (first alternative above) | `:470`, `:485`, `:537` |
| "anything another bundle reaches" (second alternative) | `:500` |

| case (test line) | criterion | post-fix assertion |
|---|---|---|
| `…holds_its_members_and_nothing_else` (:198) | (1) | `<line>-bB` on origin at the returned tip; both A commits in, both Z commits out; `tip^1` is `main`; line tip and the run's record unchanged |
| `…line_plus_b_and_the_flattened_id` (:222) | (2) | exact `pdca-integration/main-r<key>-b12`; `12`/`1-2`/`1/2` → `-b12`/`-b1-h2`/`-b1-s2`, distinct, no `/` after `pdca-integration/` |
| `…creating_pushes_without_force_and_rebuilding…` (:242) | (3) | `_pushes` argv: create has no `--force…`, no `+`; the rebuild has `--force…` and does not hold origin's old copy |
| `…refused_force_push_names_the_branch_and_the_remedy` (:260) | (3) | `denyNonFastForwards` plus a non-ancestor at the name: raises naming the branch, `delete`, `pdca-integration/*`; origin unchanged |
| `…two_members_that_clash_are_both_named` (:275) | (4) | names `issue_Y`, `issue_A`, `c.txt`, "declare the conflict"; no push |
| `…clash_with_the_base_says_rebuild_not_reorder` (:282) | (4) | names `origin/main`, "Rebuild"; no "declare the conflict"/"re-order"; no push |
| `…gone_member_not_known_merged…` (:291) | (4) | `_gone_branch`'s message; no push |
| `…brings_a_revert_of_an_earlier_members_work…` (:298) | (4) | #673 refusal for D's base, and the same refusal from the run's fresh fold; no push |
| `…rewritten_carried_member…before_any_merge` (:331) | (5) | names the rewrite, the recorded head, D's base; no `merge`, no `push` |
| `…cut_from_an_old_line_cannot_bring…` (:345) | (6) red | X's commit named as `issue_X`'s work, brought by `issue_P`; no push |
| `…work_merged_into_its_branch_is_still_its_work` (:355) | (6) red | X's topic commit named as X's, brought by P |
| `…cut_from_the_line_does_not_claim_a_members_work` (:372) | (6) must-not-raise | builds; A in, C and Z out |
| `…moved_on_since…keeps_its_work` (:383) | (6), round-1 finding | builds; A's three commits in, C and Z out |
| `…refolded_after_it_moved_on_keeps_its_work` (:394) | (6), round-2 finding | builds after a real refold took `a3` |
| `…moved_on_keeps_its_work_with_no_record_at_all` (:408) | (6) | builds with no record |
| `…topic_merged_into_a_members_branch…` (:416) | (6), round-3 finding | builds; the topic commit, `a1` and the merge in; C and Z out |
| `…members_topic_stays_its_work_after_it_moved_on_and_was_refolded` (:434) | (6), rounds 2+3 | builds after a refold took `a3` |
| `…updated_from_the_base_and_refolded…` (:454) | (6) | GitHub "Update branch" on A, refolded: builds on the moved base |
| `…member_whose_branch_was_merged_the_other_way…` (:470) | (6) | A's head has the base as first parent, refolded: builds |
| `…topic_a_member_and_an_excluded_bundle_both_merged…` (:485) | (6) | builds; the shared topic in, X's own commit out |
| `…topic_two_excluded_bundles_merged_is_refused…` (:500) | (6) red | the topic named as X's, brought by P |
| `…excluded_bundle_on_the_line_is_named…` (:520) | (6) red | X's commit named as X's (not C's), brought by P |
| `…merged_the_other_way_is_still_refused_from_the_line` (:537) | (6) red | X's commit off its chain: named as X's (not C's), brought by P |
| `…merged_the_other_way_is_still_refused_from_a_bundle_base` (:557) | (6) red | P cut from its own base on X: X's commit named, brought by P |
| `…cut_from_a_members_branch_does_not_claim_its_work` (:571) | (6) must-not-raise | E cut from `fix/M`: builds; M in, E out |
| `…cut_from_a_members_recorded_head_does_not_claim_it` (:584) | (6) must-not-raise | E cut from M at the recorded head, M moved on: builds |
| `…cut_from_an_excluded_bundles_branch_cannot_bring_it_in` (:602) | (6) red | P cut from X at `x1`, X moved on: `x1` named as X's, brought by P |
| `…merged_a_member_back_still_owns_its_commits` (:617) | (6) red | X merged P back: `x1` still X's |
| `…committed_onto_a_members_branch_is_refused` (:636) | (6) red | one branch for M and E: E's commit named, brought by M |
| `…excluded_head_this_clone_lacks…` (:646) | (6) | refused before any merge, naming the missing head; once fetched, refused as X's work |
| `…member_also_listed_as_excluded_is_a_member` (:672) | members exact | ids without `issue_`: A is a member, the build succeeds |
| `…patch_but_no_target…` (:684) | members exact | refused before any git step |

## Refute-your-own-test

- **(a) Genuine red? Yes.** `run-verify.sh` reverted the production hunks in place and re-ran
  all 32 cases: all 32 errored on the missing `build_bundle_base`, none failed to load, and the
  script restored the tree (`git apply --check -R patch.diff` passes on it afterwards). Beyond
  that whole-function red, the iteration-3 rule fails 4 cases (the reviewer's probe among them),
  my own first version fails 2, and every mutation in the table turns at least one case red.
- **(b) Production path? Yes.** Every case calls the shipped `integrate.build_bundle_base` /
  `bundle_base_branch` (and real `integrate.fold` where the scenario needs the run's line)
  against real git: a bare `origin`, a primary checkout, the real integration worktree
  (`_prepare_worktree`), real fetch, merge and push. Only two things are patched:
  `merged.merged_head` / `is_merged` in the gone-member case only (the host's PR state; there is
  no `gh` offline; the fixture's `_merged_heads`), and `integrate._git`, wrapped by a spy that
  records each argv and then calls the real function (`_refused`, test `:80`; `_pushes`).
- **(c) Fixture includes the fault? Yes.** The round-3 case really merges a topic into `fix/A`
  with `--no-ff` and asserts C holds the topic commit. The refold cases run a real second fold
  and assert the record moved. The "Update branch" case really moves `main` and merges it into
  `fix/A`. The "other way" cases really push a merge whose first parent is `main` and assert it.
  The bundle-base case really builds P's base with `build_bundle_base` and cuts `fix/P` from it.
  The refused push really sets `receive.denyNonFastForwards` and puts a non-ancestor at the name.
  The missing-head case pushes to a bare repo the primary never fetches.

## Criterion (7): the existing suites

`engine/scripts/run-suite.sh` (the T3 runner) on the final worktree: root suite `Ran 24 tests …
OK`; driver suite `Ran 2558 tests … OK (skipped=2)` (`.t3-local.log` in this bundle). That is
iteration 3's 2549, minus its 23 cases of this file, plus these 32. Every `test_integrate_*.py`
and `test_flow_*.py` module is in that run, and `git diff --name-only 489e5fb -- template/tests/`
lists no tracked file.

## Commit-readiness

The target has no formatter, linter or commit hook: only git's sample hooks, no pre-commit
config, and the CI workflows are docs, render and issue-linking (`.github/workflows/`). It needs
Python 3.11 or newer (`template/pyproject.toml.jinja:10`), and the only interpreter here is 3.14.
So I checked with the tokenizer that no f-string field reuses its quote, holds a backslash or
holds a comment (3.12-only syntax), after checking that the check flags such a line. Also: no
line over 100 columns, no trailing whitespace, no unused imports, both files parse, and
`git diff --check` is clean. The commit needs a DCO sign-off (`git commit -s`,
`CONTRIBUTING.md`), which publish adds.

## Housekeeping (left in place: no deletes, per the harness rules)

- My mistake: one development run of the C4 runner redirected its output to `/tmp/c4-run1.log`,
  outside the roots I may write. It holds only that run's test output. Every later log went into
  this bundle.
- `.c4-local.log` and `.t3-local.log` in this bundle: my final runs of the C4 and T3 runners
  (they overwrite iteration 3's copies).
- The new test file is untracked in the worktree, as before. I used `git add -N` only to produce
  `patch.diff`, then `git reset` it. `patch.diff` matches the worktree byte for byte.
- The probe and mutation runs were Python fed on stdin, so they wrote no scratch files. Their
  repos are the fixture's own temp dirs, removed by its `tearDown`.
