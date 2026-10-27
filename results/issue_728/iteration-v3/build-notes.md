# issue_728 — build notes (Do, iteration 3)

## Base

Worktree `$PDCA_WORKTREE` = `/home/eddie/pdca/pdca-harness.pdca-wt`, detached at `c423f9d`
("pdca-integrate: issue_727"): #727's accepted result folded onto
`pdca-integration/main-r547f8028520f`. That matches this bundle's `stack-base` /
`stack-base-tip` files (`c423f9dc…`). `$PDCA_VERIFY_BASE` was not set in my environment; the
worktree was already on that fold. Below, "base" means `c423f9d`, "v2" means iteration 2's
`patch.diff` on `c423f9d`, and "patched" means `c423f9d` + this `patch.diff`. All `path:line`
citations are on the patched tree unless marked "base".

`patch.diff` applies cleanly to `c423f9d` (`git apply --cached --check` on a scratch index
read from `HEAD`), and base + `patch.diff` is byte-identical to the worktree I tested (sha1 of
all five files compared).

I started from iteration 2's `patch.diff` (it still applied cleanly) and changed it for the
three implementation findings the iteration-2 carry-forward lists. Production stays
`template/src/pdca_harness/flow.py` only. `integrate.py` is unchanged, and so is `_runnable`
(`flow.py:681-847`), including its merged-prerequisite branch (#729's).

## The iteration-2 findings, and what changed for each

### Finding A — a held prerequisite behind a patchless node, below a carried bundle, stopped the whole run

Repro (adversary's, reproduced on the new fixture): run 1 `[A, N, P, D, U]`, `N Depends on: A`
closes with no patch, `P Depends on: N` is built on a base holding A, `D Depends on: P` and the
unrelated `U` fail; then A's PR is closed and run 1's line deleted; re-issue driving `D, U`.
v2's `_cascade_not_clean` read only P's direct `Depends on` (N, not a fold candidate), so P
stayed clean and was carried with A's closed commit. D's base then refused that commit as
work no member owns, and the run stopped: `U` was never built. v2 output, from my run of the
new test against v2's `flow.py`:

> flow: wave 0 — could not build issue_D's own base from issue_P: …-bD would hold 78d5bc84ad15,
> which is not origin/main's and not any member's own work: issue_P's branch origin/fix/P
> brings it in from below 34e79b9e401f, … No bundle of the run owns it. … STOPPING — wave 0
> and later waves not run.

On the base, P was carried the same way and D was built on that line, with A's closed work.

Fix:
- `_cascade_not_clean` takes `through` (finished ids with no patch) and builds each id's
  prerequisites with `_plain_prereqs` (`flow.py:1281-1310`; call at `flow.py:1428`). So P,
  whose `Depends on` reaches A through N, is not clean (#652), and its dependents wait. This
  is the reviewer's suggested fix.
- One addition beyond the reviewer's sketch: the held line must not say P's brief names A,
  because it does not. `_plain_prereqs` now returns name → the name `d`'s own brief gives on
  the way (itself, or the patchless id it went through) (`flow.py:1313-1334`), and the
  reason reads "its `Depends on` names issue_N, which has no patch and depends on issue_A,
  whose work its branch carries" (`flow.py:1303-1307`). The direct case keeps #652's exact
  wording ("its `Depends on` names issue_A, whose work …"). Its other two callers iterate the
  keys only (`flow.py:1398`, `flow.py:1494-1495`), so they are unchanged in effect.
- Docstrings: `_cascade_not_clean` (`flow.py:1283-1292`) and the #728 paragraph of
  `_carry_finished` (`flow.py:1380-1385`).

Result now: P's line says it is not carried (cause A, through N), "holding issue_D this
run"; "flow: issue_D skipped — prerequisite(s) not ready (P)"; U is built on the real base;
no `STOPPING`. Test: `test_a_finished_id_built_through_a_patchless_bundle_on_a_held_one_is_held`
(`template/tests/test_flow_carried_prereq_bases.py:348`).

### Finding B — a carried prerequisite squash-merged, its branch deleted, stopped the whole run

Repro (adversary's): run 1 `[P, D, U]`, D (`Depends on: P`) and U fail; P's PR is then
squash-merged into main and `fix/P` deleted; `gh` reports MERGED with the old head; re-issue
driving `D, U`. The carry accepts P (run 1's line holds its head) and its fold skips the gone
branch for the same reason, so v2 made P a member of D's base. That base starts at
`origin/main`, which after a squash merge has P's work but not P's head, and
`integrate._gone_branch` (`integrate.py:1405-1412`) refused it. v2 output, from my run:

> flow: wave 0 — could not build issue_D's own base from issue_P: issue_P's branch
> origin/fix/P is gone and its PR … merged at 1392d64e…, a commit neither …-bD nor
> origin/main has: it merged somewhere other than origin/main (…, or a squash or rebase
> merge) … STOPPING — wave 0 and later waves not run.

On the base, D was built on the run's line (a #727 seam), and D and U were both COMPLETE.

Fix: a carried bundle whose published branch is gone and whose PR's merge is on the base is
walked through but never a member, the way a patchless one is.
- New `_merged_on_base` (`flow.py:1201-1217`): False while the branch resolves in the
  checkout as the carry fetched it (that fetch prunes, `integrate.py:2033-2035`). Otherwise
  it asks `merged.merge_and_head` (`merged.py:149-169`) and checks, by commit, whether
  `origin/<base>` has the commit the merge put on the base or the head it merged (a squash
  or rebase merge has only the first). Fail-closed: no answer, or a git error, gives False,
  so the bundle stays a member and `build_bundle_base` refuses the gone branch with its own
  message, as in v2.
- `_carry_finished` gets an optional out-param `on_base` (`flow.py:1337-1341`), filled
  right after `took` for the ids just carried (`flow.py:1473-1475`); docstring
  `flow.py:1387-1392`.
- `_bundle_bases` takes `on_base` (`flow.py:969`) and leaves those names out of the member
  candidates (`flow.py:1003`). They stay in the walk's graph (they are carried), so the walk
  still goes through them to what they were built on. Docstring `flow.py:982-984`.
- `_drive_and_act` keeps `carry_on_base` beside `carry_took` (`flow.py:2746-2756`) and
  passes it (`flow.py:2843`).
- One `gh pr view` call per carried bundle whose branch is gone; none otherwise. The resume
  suite's `gh_calls == []` checks are unaffected.

Result now: "flow: carried issue_P …", D and U built on the real base (main, which holds
P's squash commit), no `STOPPING`. Test:
`test_a_carried_prerequisite_squash_merged_with_its_branch_gone_is_on_the_base` (`:513`).
Precision guard: `test_a_carried_prerequisite_merged_elsewhere_with_its_branch_gone_is_not_on_it`
(`:535`): P's PR merged into another branch (a base edited on the host), branch gone. Main
does not have P's work, so P stays a member and D's base is refused, naming the gone branch.
D is never built on main without P. That test goes red under two ablations: "any gone
branch counts as on the base", and "decide by `publish.json`'s record" (`return
merged.merged_into(…)` in place of the commit check).

### Finding C — `_holds_work` did not check that the base ref exists

`flow.py:1087`: `base_ref` is added to the `_rev` guard, so a checkout that lacks
`<base_remote>/<base>` gives "not below" instead of a `git rev-list` failure that stops the
run. Docstrings: `_holds_work` (`flow.py:1082-1086`), `_finished_after` (`flow.py:1053-1056`).
Before, from my run of the new guard test against v2:

> flow: wave 0 — could not read the work of issue_N below issue_M's recorded cut point
> 3e2614736845 in /tmp/…/repo — `git rev-list` exited 128; … STOPPING — wave 0 and later
> waves not run.

Test: `test_finished_partners_on_a_base_the_checkout_lacks_stop_nothing` (`:487`): two
finished patchless partners on `org/repo @ gone` (a base origin no longer has), each with a
recorded cut point, and an unrelated D on main. It is green on the base (which never reads
cut points), red on v2, green now. A guard, not part of the red leg against the base.

### Docstring the deferred list called wrong

The deferred item "An out-of-batch prerequisite behind a patchless node is still skipped
silently" quoted v2's `_closure_members` docstring ("an out-of-batch prerequisite, on the
real base once merged (`_runnable`)"). That claim was false for an edge reached through a
patchless node. The behaviour is `_runnable`'s, which the brief leaves to #729, so I did not
change it. The docstring now says what happens (`flow.py:929-935`): `_runnable` waits for
that merge only for an edge of the bundle's own brief, never for one reached through a
finished id with no patch. It also says only a finished id the carry judged not clean is
held; one no plain `Depends on` edge reaches is neither carried nor held.

## Decisions and rejected alternatives

**B: "branch gone" as the condition, rather than "PR merged into the base" alone.** The
reviewer's wording was "a carried id whose PR has merged into the base is not a member".
That variant is two lines shorter (drop the early return at `flow.py:1210-1211`). I rejected it
because it newly stops a run v2 builds:
- P squash-merged into main with its branch kept, carried Q (`Depends on: P`, open) built
  on P's pre-squash commits, D `Depends on: Q`. With P not a member, Q's branch brings P's
  pre-squash commits from below Q's cut point, no member owns them, and `_unowned_work`
  refuses D's base. With the branch-gone rule, P stays a member there (as in v2) and owns
  them. Probed: with this patch D is COMPLETE on its own base; with the variant, D is
  PLANNED and the run stops (`.scratch-728/variant-x.log`).
- It would also change the restatement of the brief's own anchor
  `test_flow_merged_prereq_on_line.py:269` (now `:294`; P merged with a merge commit, branch
  kept) from "own base holding P" to "the real base". That is outside the brief's expected
  restatement. Probed: under the variant that test fails.

The branch-gone rule changes a v2 outcome in only two ways: a stop becomes a build (squash or
rebase merge into the base), or a member whose merge was a no-op becomes no member (merge
commit, branch gone: the same tip either way). Its cost is the residual "squash-merged,
branch kept, main later changes the same lines" below, which v2 has too.

**B: decided by commit, not by `merged.merged_into`'s record rule.** `merged_into`
(`merged.py:70-114`) trusts `publish.json`'s `base`. It cannot see a PR whose base was edited
on the host and that merged elsewhere. It would then say "merged into main", P would be
dropped, and D would be built on main without P's work: silently wrong. Checking the merge
commit against the fetched base costs the same one `gh` call. With the record-based check
swapped in, the precision guard goes red (ablation `on-base-by-record`). This is how
`_line_lacks_merge` (#655, `flow.py:850-887` base) and `_gone_branch` decide too.

**B: a stop, not a hold, for "merged elsewhere, branch gone".** In that corner no own base
can take P's work (its branch is gone, the base lacks it), so D's base is refused and the run
stops, as in v2. #727 built D on the line there instead. A hold would mean judging P not
clean before the fold (about 10 lines plus a new hint). That also makes P's commits on an
earlier run's line count as foreign (`integrate.foreign_commit`), so the whole target's line
is distrusted and every finished id on it is held. That is a broader change for a rare
corner. Turning base-build stops into holds is #725's.

**A: edge-based, not commit-based.** A commit-based cascade (a finished id whose head reaches
a not-clean id's work is not clean, as #672 does inside the fold) would also cover
`Conflicts with` partners and edgeless cases. It needs the not-clean id's head even when its
PR is CLOSED (`_finished_head` returns only a reason then), a `rev-list` per pair, and a
change to #652's documented edge rule. That is much more than the finding. I kept #652's edge
rule and only let it pass through patchless nodes, as the reviewer suggested.

**C:** the reviewer's one-token fix, nothing else.

**Not done (code review, optional):** computing `_finished_after` once per run instead of
per wave. Its inputs do not change after the carry, but finished partner pairs are rare and
each costs at most two `rev-list` calls.

## Everything production changes (`template/src/pdca_harness/flow.py`, vs base)

1. `_closure_members` (base `:913-958` → `:913-964`): parameter `built` → `graph`, plus
   `after`. The `finished` seam is gone (base `:947-949`: `if n in finished: return "…
   finished in an earlier run"`). Edges to names outside `graph` are not followed (`:955`).
   Members are those reached and in `on_target`. The remaining seams are a walked `Stacks
   on` / `Onto branch` bundle, and a member pointed at a seam itself. That is the brief's
   "narrowing #727's carried-closure fallback". Docstring rewritten (`:917-941`).
2. `_bundle_bases` (base `:961-1012` → `:967-1036`): graph = carried finished ids plus
   patchless finished ids that have a brief, at wave -1, then this run's bundles
   (`:998-1000`). Member candidates exclude `on_base` (`:1003`). `heads = {**carried,
   **carried_heads}` (`:1001`) goes to `integrate.build_bundle_base` as both `carried=` and
   `excluded=` (`:1019`; base `:995` passed `carried_heads` only). So:
   - a carried member rewritten after the carry is refused by #723's existing check
     (`integrate.py:838-844` → `_lost` `:1077` → `_carried_rewrite` `:1172`, raising
     `_Rewritten`): criterion (5);
   - a carried member whose branch brings work from below its recorded cut point is refused
     by `_unowned_work` (`integrate.py:988`, called at `:867`) → `_foreign_refusal`
     (`:1008`, raised at `:869`), which names the carried owner: criterion (4).
3. Briefless guard (`:997-999`): a patchless finished bundle with no `brief.md` (a pre-#481
   split parent, #597) stays out of the graph; else `brief.stacks_on` raises
   `FileNotFoundError` out of the run.
4. `_finished_after` (`:1039-1077`) and `_holds_work` (`:1080-1092`): which of two
   finished `Conflicts with` partners an earlier run built first, read off the recorded cut
   points (iteration 1's finding). `_holds_work` now also guards `base_ref` (finding C).
5. `_merged_on_base` (`:1201-1217`): new (finding B).
6. `_cascade_not_clean` (base `:1182-1209` → `:1281-1310`): `through` and the via-name
   reason (finding A).
7. `_plain_prereqs` (`:1313-1334`): new in v2; now returns name → via (finding A).
8. `_carry_finished` (base `:1212` → `:1337`):
   - `through` + `dependents` via `_plain_prereqs` (`:1395-1400`): a prerequisite reached
     only through a patchless node triggers the carry (iteration 1);
   - the cascade gets `through` (`:1428`, finding A);
   - out-params `took` (`:1340`, filled `:1471-1472`) and `on_base` (`:1341`, filled
     `:1473-1475`, finding B);
   - a patchless finished id whose plain `Depends on` reaches a held id is held too
     (`:1493-1495`), so `_runnable` holds its dependents (iteration 1);
   - the "carried" stderr line: "this run's … bundles build on it" → "bundles ordered after
     them build on a base that holds them" (`:1476-1479`). Every test that reads this line
     matches its unchanged prefix `flow: carried issue_X (finished`;
   - docstring: the #728 paragraphs (`:1380-1392`).
9. `_drive_and_act`: `carry_took` / `carry_on_base` filled by the carry (`:2749-2756`) and
   passed to `_bundle_bases` (`:2843`); comments (`:2746-2748`, `:2836-2838`).

Not touched, per the brief's scope: `integrate.py`; `_runnable` (`flow.py:681-847`) incl.
its merged-prerequisite branch and `_line_lacks_merge` (#729); the stack-rule docs (#725).

## Restated assertions and other test changes (before → after)

Unchanged since iteration 2; line numbers re-checked against the hunk headers of this
`patch.diff` (base → patched). "Own base": the recorded stack base is
`integrate.bundle_base_branch(…, "issue_<id>")` (never the line), the recorded tip is
origin's tip of it, and the bundle is COMPLETE.

### `template/tests/test_flow_resume_stack_prereqs.py` (the brief's `:183`, `:262`, `:449`, `:538` anchors on `fcae4aa`)

| Base | Before | Patched | After |
|---|---|---|---|
| `:15-17` module docstring | "the run still pushes once (#672)" | `:15-21` | "pushes its line once"; new paragraph: since #728 a dependent of a carried id is on its own base, and the line still carries every carried id |
| `:122-128` `_publish_bundle` (fixture, not an assertion) | `fx._publish` rewrites the brief, dropping `Depends on` | `:126-135` | the brief is restored after `fx._publish`. Real publish never writes the brief (`publish.py` writes only `publish.json` and the stack-base files), and #727's own fixture leaves it alone (`test_flow_dependency_scoped_bases.py:135-164`). Without this, test (3)'s E walked to D but not on to P, and stopped on P's commit as unowned |
| `:197` test name | `…_is_on_the_line_its_dependent_builds_on` | `:204` | `…_is_on_the_base_its_dependent_builds_on` |
| `:202-207` test (1) | `base == line`, `line_tip` not None, `tip == line_tip`, fix/P on `line_tip`, D COMPLETE | `:210-213` | `_on_own_base("D", …, "P")` (own base, tip = origin tip, fix/P on it, COMPLETE); `line_tip` not None and fix/P on it, kept |
| `:221`, `:225` test (2) | `_built("D")[:2] == (line, old)`; D COMPLETE | `:227-228` | `_on_own_base("D", …, "P")`; the line D was built beside is still at `old`. Kept: `old` ancestor of the line, pushes non-empty, no `--force` |
| `:229` test (3) comment | "E builds on a line holding P and D" | `:235-236` | "D and E are each built on a base of their own: D's holds P, E's P and D" |
| `:235-243` test (3) | D `(line, carried)`; `len(pushes) == 2`; `pushes[1]` not forced; E `(line, e_line)`; `carried`, fix/P, fix/D on `e_line`; E COMPLETE | `:243-254` | `_on_own_base("D", batch, "P")`; `carried` = the line tip then; pushes to the line are exactly 2 and the second is not forced; the other pushes are exactly D's then E's own bases, in that order; `_on_own_base("E", batch, "P", "D")`; `carried`, fix/P, fix/D on `e_line`, kept |
| `:275-279` test (4c), the brief's `:262` | B `(line, line_tip)`; fix/Q on `line_tip`; fix/P not on the line; B COMPLETE | `:286-289` | `_on_own_base("B", …, "Q")`; fix/P not on B's base (the excluded one, now checked on the base); fix/Q on the line tip then, kept; fix/P not on the line, kept |
| `:458-463` `…_clean_finished_id_beside_them…`, the brief's `:449` | E `(line, line_tip)`; fix/X on tip; fix/P, fix/Q not on tip; E COMPLETE | `:468-471` | `_on_own_base("E", …, "X")`; fix/P, fix/Q not on E's base tip, kept |
| `:538-551` `_carried_beside`, the brief's `:538` | `len(pushes) == 1`; one carried line naming X; E `(line, line_tip)`; fix/X on tip; E COMPLETE; returns the line tip | `:546-558` | pushes are exactly `[line, E's own base]` (the line once, no fix-up push); same carried-line checks; returns `_on_own_base("E", batch, "X")`. Its six callers' `_off_the_line(commit, e_tip)` now check the line and E's own base |

The brief's `:348` anchor (test (8), W) was already an own base on `c423f9d` (#727: W
`Depends on: U`, built this run). Unchanged here.

### `template/tests/test_flow_merged_prereq_on_line.py` (the brief's `:269` anchor)

| Base | Before | Patched | After |
|---|---|---|---|
| `:191-210` helper `_built_on_line()` | if W was built this run: own base `{line}-bD`, tip = origin tip, fix/W on it, nothing beyond main but merges and fix/W; else (a carried prerequisite) `base == line` | `:191-205` `_built_on_own_base(prereq)` | always own base `{line}-bD`, tip = origin tip, fix/`<prereq>` on it, nothing beyond main but merges and fix/`<prereq>`; D COMPLETE |
| `:239` caller (test 3) | `_built_on_line()` (W built: own base) | `:235` | `_built_on_own_base("W")`, the same checks |
| `:247` caller (test 4) | `_built_on_line()` (W built: own base) | `:243` | `_built_on_own_base("W")`, the same checks |
| `:285-286` comment | "D … is cut from that line" | `:281-283` | "judged on that line …, on a base of its own holding the carried P (#728), which starts at main and so has the merge" |
| `:297-300`, the brief's `:269` (`tip == old`) | `_built_on_line()` (base == line); `tip == old`; fix/P on tip; merge commit not on tip | `:294-298` | `_built_on_own_base("P")`; the merge commit is on D's tip; the line is still at `old`; fix/P on `old`; merge commit not on `old` |
| `:309` comment | "D is built on it" | `:307-308` | "D is built — on a base of its own holding W (#728), which starts at main too" |
| `:322` caller (way-out test, 3rd run: W carried) | `_built_on_line()` → else-branch, `base == line` | `:321` | `_built_on_own_base("W")`. Kept: tip ≠ `old`, merge commit and fix/W on tip |

The one assertion whose truth value flips is "merge commit on D's tip" (base `:300`). It was
a fact about the line D was cut from (the line #655's gate judged, which lacks P's merge).
D's own base starts from freshly fetched main, which has the merge. The line facts are kept as
line facts (`:296-298`). The excluded-work check is stronger than before: "beyond main,
nothing but merges and fix/P". In this test P's branch is kept, so P is still a member under
finding B's rule.

### `template/tests/test_flow_dependency_scoped_bases.py` (#727's suite; not in the brief's list)

| Base | Before | Patched | After |
|---|---|---|---|
| `:373` header | `(6) seams keep the line, exactly as before, and are built` | `:373`, `:405` | new header `(6a) a bundle the run carried is a member like one it built (#728)` over the two tests below; the `(6)` header moves down to `:405`, above the unchanged `Onto branch` / `Stacks on` seam tests |
| `:375-390` `test_a_dependent_of_a_carried_bundle_keeps_the_line` | `_on_line("D")`; every commit of P's and X's branches on that tip | `:375-388` `…_is_built_on_a_base_holding_it` | `_own_base("D", "P", "X")`: own base, tip = origin tip, every commit of P's and X's branches, COMPLETE |
| `:392-407` `test_a_conflicts_with_partner_that_was_carried_keeps_the_line` | `_on_line("D")`; K's and X's commits on it | `:390-403` `…_carried_is_on_the_base` | `_own_base("D", "K", "X")` |

These two tests pinned exactly the fallback the brief removes. Their comments changed to
match (`:377-378`, `:392`).

Unchanged: every assertion in `test_integrate_carried_rewrite_late.py`, and every other
existing test file.

## The new test — `template/tests/test_flow_carried_prereq_bases.py` (15 tests)

Real git on `StackFoldGit` through `flow._drive_and_act`, as #727's suite does. Briefs are kept
as written. `gh` answers OPEN unless a case sets `self.gh[id]`; after a case deletes a
branch, the head it had (`gh_heads`) and the merge commit (`merge_oid`) (`:95-107`). Only
modules are imported. New in iteration 3: the `gh` stub's two fields, `_merged_and_deleted`
(`:187-206`), `_on_real_base` (`:243-247`), and four tests marked ★.

"Red on base" / "red on v2" come from swapping that `flow.py` in and running the module
(script below); "ablation" means v3 with one part of the fix switched off.

| Test (line) | For | Base | v2 | Ablation that turns it red |
|---|---|---|---|---|
| `…holds_only_its_own_prerequisite` `:264` | criterion (1) | red: fix/D holds X (D on the line) | green | — |
| `…patchless_bundle_carries_its_prerequisite` `:287` | criterion (2) | red: D's recorded base is the line | green | — |
| `…reached_only_through_a_patchless_bundle_is_carried` `:307` | iteration 1 (no W) | red: nothing carried, D on main | green | — |
| `…held_prerequisite_reached_through_a_patchless_bundle_holds_the_dependent` `:323` | iteration 1 | red: D built on main | green | — |
| ★ `…built_through_a_patchless_bundle_on_a_held_one_is_held` `:348` | finding A | red: P carried with A's closed commit, D on that line | red: STOP, U unbuilt | cascade direct only |
| `…patchless_bundle_is_not_stopped` `:383` | criterion (3) | red: D's recorded base is the line | green | — |
| `…no_brief_declares_no_edge_to_walk` `:406` | guard (#597) | green | green | — |
| `…partner_built_before_a_carried_member_is_on_the_base` `:423` | iteration 1 | red: W, Y on the line | green | — |
| `…partner_built_after_a_carried_member_is_not_on_the_base` `:445` | partner-rule precision | red: W on the line, holding L | green | — |
| `…patchless_partner_built_before…` `:466` | partner rule, patchless partner | red: W on the line | green | — |
| ★ `…partners_on_a_base_the_checkout_lacks_stop_nothing` `:487` | finding C (guard) | green | red: `git rev-list` exited 128, STOP | no `base_ref` in the guard |
| ★ `…squash_merged_with_its_branch_gone_is_on_the_base` `:513` | finding B | red: D on the line | red: STOP, D and U unbuilt | `on_base` never filled |
| ★ `…merged_elsewhere_with_its_branch_gone_is_not_on_it` `:535` | finding B precision | red: D built on the line | green (v2 also refuses) | any gone branch counts as on the base; or decide by `merged.merged_into` (the record) |
| `…cut_from_a_line_holding_another_stops_its_dependent` `:560` | criterion (4) | red: D on the line | green | — |
| `…rewritten_after_the_carry_stops_its_dependent` `:580` | criterion (5), a guard per the brief | red too: D on the line, nothing checks it | green | — |

Ablation script: `$PDCA_WORKTREE/.scratch-728/ablate.py` swaps `flow.py` for each variant,
runs the module, prints the failing tests, and restores v3 (checked byte-identical after each
run). Its output on the final code (`.scratch-728/ablate-final.log`): base 13 failing; v2
3 failing (exactly the three ★ finding tests A, B, C); each of the five ablations exactly 1
failing, the test named above.

## Refuting my own test

- **(a) Genuine red?** Yes. The project's C4 gate (`engine/scripts/run-verify.sh`, with
  `PDCA_BUNDLE`/`PDCA_WORKTREE`, under `timeout 2400`) reverted the production hunks. The new
  file went 13 of 15 red: every test but the two guards that are green on the base too (the
  briefless guard and finding C's guard). The restated files went 2 + 2 + 14 red. It printed
  `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`, and afterwards `flow.py`
  was byte-identical to the patched one. Against v2's `flow.py`, the three ★ finding tests
  fail with the exact stops the reviewers reported (quoted above), and each fix part switched
  off alone turns its own test red (table).
- **(b) Production path?** Yes. Every case drives `flow._drive_and_act`: the real carry
  (`_carry_finished`, a real `integrate.fold`, `_cascade_not_clean`, `_merged_on_base` with a
  real `merged.merge_and_head` behind the `gh` stub), real `_runnable`, real `_bundle_bases` /
  `_finished_after` / `_holds_work`, and real `integrate.build_bundle_base` /
  `_gone_branch`, pushing real branches to a bare origin. Stubbed: the build/sign-off leaf
  (`flow._drive_wave` writes a patch, a close marker, or nothing, and accepts),
  `flow._publish_bundle` (cuts and pushes `fix/<id>` from the recorded stack-base tip, as
  publish does), `gh` (state, head, merge commit), and `publish.draft_texts`. That is the
  same set of stubs #727's suite uses.
- **(c) Fixture includes the fault?** Yes.
  - Finding A: a real first run builds P on a base holding A, through the patchless N (the
    test asserts P's recorded cut point holds A). A's PR is then really closed (`gh` CLOSED)
    and the line really deleted, so the carry really judges A not clean.
  - Finding B: P's PR is really squash-merged into main by the scratch clone (main gets a new
    commit, and the test asserts main lacks P's head), and `fix/P` is really deleted on the
    bare origin. The carry and the fold see it gone through their real pruning fetch. The
    precision guard really merges into another branch (`release`), so main lacks the merge
    commit.
  - Finding C: the target `org/repo @ gone` really does not exist in the checkout (the test
    asserts `rev-parse origin/gone` fails), and the two partners have real recorded cut
    points that resolve there. That is hand-built state, not a first run. Producing it
    through a run would need a base branch created and then deleted on origin between runs,
    and the fault is the same: a base the checkout lacks.
  - The rest is as in iteration 2: patchless nodes and carried ids come from real first
    runs; criterion (4) really cuts P from a real earlier line holding X; criterion (5)
    really force-pushes `fix/P` after the carry's fold.

## Gates run (the project's runners)

- `engine/scripts/run-verify.sh` (C4; `PDCA_BUNDLE` / `PDCA_WORKTREE` set; `timeout 2400`)
  on the final `patch.diff`: green leg 15 + 25 + 9 + 27 tests OK; red leg 13 + 2 + 2 + 14
  failures; `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`. Afterwards
  `flow.py` was byte-identical to the patched one.
- `engine/scripts/run-suite.sh` (T3; same environment; `timeout 3000`) on the final tree:
  root suite `Ran 24 … OK`; driver suite `Ran 2596 … OK (skipped=2)` (iteration 2: 2592; the
  4 new tests account for the difference); `PDCA-EVIDENCE: root suite OK, driver suite OK`.
- `engine/scripts/run-docs-check.sh` (T2): `docs lint clean, site render + link audit
  clean`. The patch touches no docs.
- Formatter / commit hooks: the target has no pre-commit config, no Python formatter or
  linter config, and no installed hooks (only `.sample` files; `core.hooksPath` unset). Its
  CI (`.github/workflows/`) runs only docs and render checks. No Python linter is installed
  here. By hand: no added line over 99 columns (`flow.py` had 5 such lines on the base and
  still has 5; the four test files have none); `git diff --check` is clean; all five files
  compile; an `ast` check finds no unused imports.
- Probes for the claims in "Decisions" and "Residuals" (scratch, not in the patch):
  `.scratch-728/probe_728.py`, run on the final code and, for the rejected variant, by
  `.scratch-728/variant_x.py` (log `variant-x.log`).

## Residuals for sign-off

- **Users will see this:** a re-issued run whose carried bundle was cut from a line that also
  held unrelated work (before #727, or at a seam) now stops that bundle's dependent, naming
  the bundle and the owner of the work (criterion 4). Before, the dependent was built on the
  line holding everything. The same holds for a carried bundle whose cut point cannot be
  trusted (`integrate._member_cut_point`: stacked with no record, or no recorded tip): its
  dependent now stops with "Re-publish …". A base-build failure stops the whole run, not
  only the dependent (`flow.py:2848-2853`). Turning that into a hold is #725's.
- **Stops that remain where #727 built the dependent on the line** (all rare, all need a
  merge the stack workflow advises against, or a host-side base edit):
  - a carried PR merged into a branch other than the base, its branch deleted: no own base
    can take its work (pinned by the precision guard above);
  - a carried PR squash-merged with its branch kept, after which main changed the same
    lines: merging that branch onto D's base conflicts (`_member_clash`: "does not merge
    cleanly onto origin/main itself"). v2 has this too; dropping merged ids as members fixes
    it (probed: D on the real base) but stops the stacked case in "Decisions";
  - a carried PR squash-merged with its branch deleted, and another carried bundle stacked
    on its pre-squash commits: those commits are no member's own work. v2 stopped here too,
    with a different message. The refusal names the merged bundle as one "issue_D does not
    build on", which is not accurate here; its other remedy, rebuild the stacked branch on
    the new base, is the right one.
- **`Conflicts with` is not followed by the "not clean" cascade (#652's rule, unchanged).** A
  finished K built after a closed A it `Conflicts with` is still carried with A's commits.
  Its dependent's own base then refuses them as work no member owns, and the run stops, so
  an unrelated U is not built either (probed). On the base, the dependent was built on the
  line, holding A's closed work. This is criterion (4)'s refusal working on rejected work.
  Making #652's cascade follow `Conflicts with` partners by cut point (as `_finished_after`
  does) would hold K instead: about 15 lines in `_carry_finished` / `_cascade_not_clean`
  plus a test. I left it out: it changes #652's documented edge rule and is outside the
  three findings. A candidate follow-up, or for #725's holds.
- **Not covered: an out-of-batch prerequisite, or a `Depends on (merged)` edge, reached
  through a patchless node.** `_runnable` judges only a bundle's own edges, and it is #729's.
  So D → N → A (A not asked for, unmerged) is still built without A, as before this change.
  The `_closure_members` docstring now says so (`flow.py:933-935`). This is the deferred
  [human] item; it needs a follow-up on #729's side.
- **No end-of-run rewrite check for carried branches** (true before this change too).
  `rewritten_carried` judges only the run's `accepted` bundles. The new check runs only when a
  later base takes that member (criterion 5).
- **Docs:** `docs/07-crosscutting.md:749-752` still says the carry "points that target's
  bundles at" the line. Stack-rule docs are #725's per the brief, so I did not edit them.
- **Housekeeping:** my scratch scripts, logs and `flow.py` variants are in
  `$PDCA_WORKTREE/.scratch-728/` (untracked, not in the patch, outside `template/`). I
  removed nothing; the harness reclaims the worktree. (One command began with `rm -f` on a
  scratch index path of mine in that folder; the file did not exist yet.) The fixtures' own
  temp dirs are cleaned by their `tearDown`.
