# issue_728 — build notes (Do, iteration 4)

## Base

Worktree `$PDCA_WORKTREE` = `/home/eddie/pdca/pdca-harness.pdca-wt`, detached at `c423f9d`
("pdca-integrate: issue_727"): #727's accepted result folded onto
`pdca-integration/main-r547f8028520f`, matching this bundle's `stack-base` /
`stack-base-tip` (`c423f9dc…`). `$PDCA_VERIFY_BASE` was not set in my environment; the
worktree was already on that fold. Below, "base" means `c423f9d`, "v3" means iteration 3's
`patch.diff` on `c423f9d`, and "patched" means `c423f9d` + this `patch.diff`. All `path:line`
citations are on the patched tree unless marked "base".

`patch.diff` applies cleanly to `c423f9d` (`git apply --cached` on a scratch index read from
`HEAD`), and base + `patch.diff` is byte-identical to the worktree I tested (blob hashes of
all six files compared, before and after the C4 gate ran).

I started from v3's `patch.diff` (it still applied cleanly) and changed it for the three
implementation findings of the iteration-3 carry-forward, plus one guard that the first of
those fixes needs (below). Production: `template/src/pdca_harness/flow.py`, and one small
change in `template/src/pdca_harness/integrate.py` (its own section below). `_runnable`
(`flow.py:681-847`), including its merged-prerequisite branch (#729's), is unchanged. The
three restated test files are byte-identical to v3's.

## The iteration-3 findings, and what changed for each

All three are the same kind of failure. Since v1, a carried bundle is a member of its
dependent's own base, so #723's base check (`integrate._unowned_work`) now judges what a
carried branch brings in. That check counted as owned only each member's own work above
its recorded cut point. A carried member's branch can legitimately bring work from below
its cut point that no member of this run owns. The check then refused the base, and a
refused base stops the run (`flow.py:2973-2979`). On the base the dependent kept the line
and was built.

### Finding 1 — squash-merging the bottom of a stack stopped the run

Repro (the adversary's, now `test_the_rest_of_a_stack_whose_bottom_was_squash_merged_is_built`,
`template/tests/test_flow_carried_prereq_bases.py:563`): run 1 `[A, P, D, U]`, P (`Depends
on: A`) built on a base of its own holding A, D (`Depends on: P`) and U fail; A's PR is
squash-merged into main and `fix/A` deleted; re-issue driving D, U. v3 output (my run):

> flow: wave 0 — could not build issue_D's own base from issue_P: …-bD would hold
> 883ed8a86f40, which is not origin/main's and not any member's own work: issue_P's branch
> origin/fix/P brings it in from below f086ef148913, … It is in the published head of
> issue_A, which issue_D does not build on. … add issue_A to issue_D's members, or rebuild
> issue_P's branch … STOPPING — wave 0 and later waves not run.

On the base, D was built on the line and COMPLETE.

Fix: the base check is told which work beyond the members' own is D's to hold
(`flow.py:1077-1107`, `_owned_work`), through a new `owned` argument of
`integrate.build_bundle_base` (`integrate.py:738`, used at `:871`, counted in
`_unowned_work` at `:1013-1016`). Two sources:

1. **A member cut from a base of its own** (`_own_base_cut`, `flow.py:1125-1140`): its
   recorded stack base is `integrate.bundle_base_branch` for that member on its target base,
   from any batch. `build_bundle_base` pushed that base only after checking it held nothing
   but the base's work and its members' own, and its members were what the member is
   ordered after. So all the work below its cut point is the work of bundles D is ordered
   after too. `owned[member] = its cut point` (`flow.py:1103-1106`). This alone fixes the
   adversary's repro.
2. **A carried bundle whose work is on the base** (`on_base`: PR merged, branch gone, the
   merge on the base): the head the carry took (`flow.py:1099-1101`). A squash or rebase
   merge puts that work on main under new commits, so the original commits a member brings
   in are A's work, and main already has it. This covers the same repro when P was cut from
   an old *line* rather than a base of its own (as every stack bundle was before #727),
   where source 1 does not apply: `test_a_member_cut_from_a_line_whose_prerequisite_was_squash_merged_is_built`
   (`:593`).

Result now: no `STOPPING`; D on its own base (main, which has A's squash commit, plus
`fix/P`, which brings A's original commit and P's); U on the real base.

### Finding 2 — a re-issue that leaves out a carried bundle's prerequisite stopped the run

Repro (`test_a_carried_member_whose_prerequisite_the_re_issue_leaves_out_is_built`, `:622`):
run 1 `[A, P, D, U]` as above (A's PR open); re-issue `[P, D, U]`. A is neither built nor
carried. v3 output:

> flow: wave 0 — could not build issue_D's own base from issue_P: …-bD would hold
> 2d38d94a69c2, … issue_P's branch origin/fix/P brings it in from below 612d61978a50, …
> No bundle of the run owns it. … rebuild issue_P's branch on a base without that work
> (re-publish it), then re-run; STOPPING — wave 0 and later waves not run.

On the base, D was built on the line, holding P and A, COMPLETE.

Fix: source 1 above. P was cut from a base of its own, which held A. D's base now holds A
and P (both checked), and U is built. No line fallback and no hold.

### Finding 3 — a carried PR merged after the carry stopped the run

Repro (`test_a_carried_prerequisite_squash_merged_after_the_carry_is_on_the_base`, `:645`):
run 1 `[P, D, U]`, D and U fail; on the re-issue a hook squash-merges P's PR and deletes
`fix/P` right after the carry's fold. v3 output:

> flow: wave 0 — could not build issue_D's own base from issue_P: issue_P's branch
> origin/fix/P is gone and its PR … merged at a57c53b0…, a commit neither …-bD nor
> origin/main has: … (… or a squash or rebase merge) … STOPPING — wave 0 and later waves
> not run.

On the base, D was built on the line, COMPLETE.

Fix: `_build_own_base` (`flow.py:1043-1074`). When a build fails, each carried member not yet
in `on_base` whose branch the build's own fetch found gone and whose PR merged into the base
(`_merged_since`, `flow.py:1143-1149`, which uses v3's `_merged_on_base`, `:1319-1335`) goes
into `on_base`. The base is then built again without it, its head owned as in finding 1
(`flow.py:1063-1069`). Any other failure raises as before. `on_base` is the run's set
(`flow.py:2875`), so later waves see it too. The build's fetch prunes into the primary
checkout (`integrate._prepare_worktree` → `_fetch(repo, …)`, `integrate.py:2059-2064`;
the integration worktree shares its refs), so the re-check reads what the build saw.
Result now: D on main (which has P's squash commit), U built, no `STOPPING`.

### A guard the fix needs: a closed PR's work stays unowned

Source 1 trusts what a member's own base held when it was built. A bundle on that base may
have had its PR closed since. If the member reached it by a plain `Depends on`, the carry
already holds the member (#652's cascade, `flow.py:1400-1429`). But if it reached it by a
`Conflicts with` or `Depends on (merged)` edge, which the cascade does not follow, the
member is carried, and source 1 would own the closed work.

Probe (now `test_a_carried_member_built_on_a_partner_whose_pr_closed_stops_its_dependent`,
`:670`): run 1 builds K, then P (`Conflicts with: K`) on a base of its own holding K, D fails;
K's PR is closed; re-issue. Without the guard, D was built on its own base **holding K's
closed work** (`fix/D` had K's commit). That is also what the base does (D on the line,
which holds K through P's branch). v3 refused it (no member owned K's commit) and stopped.

Guard: the carry records the head a CLOSED PR reports when it resolves (`_finished_head`,
`flow.py:1307-1310`, filled through `_carry_finished`'s new `closed`, `:1461`, `:1541`,
and `_drive_and_act`, `flow.py:2876-2882`, `:2970`). Source 1 is skipped for a member whose cut
point holds any of that closed bundle's own work (`_holds_rejected`, `flow.py:1110-1122`,
reusing v3's `_holds_work`). Result: as v3, D is not built, and one `STOPPING` line names P
and the closed commit. I chose the brief's "stop the dependent instead of building it on a
wrong base" over the base's silent inclusion. Only CLOSED counts as rejected; the other
not-clean reasons (no PR on record, state unreadable, merged at a head neither the base nor
the line has) say nothing about the work itself.

## `integrate.py` changed outside the three named functions — why

The brief allows changes only in `_unowned_work` / `_foreign_refusal` / `_carried_rewrite`,
with `build-notes.md` saying why. `_unowned_work` is where the owned set grows
(`integrate.py:1013-1016`, 4 lines; plus its docstring). It is called only from
`build_bundle_base` (`integrate.py:871`), which builds the `own` list from its members.
Nothing else in that function's arguments reaches it: `excluded` only feeds the refusal's
wording (`_foreign_refusal`). So the data has to come in through `build_bundle_base`: one
keyword argument `owned` (`integrate.py:738`), passed on unchanged (`:871`), and 4 lines in
its docstring (`:768`, `:780-783`). No other line of `build_bundle_base` changed. The
default `None` keeps every existing caller and test as it was.

Rejected: doing it in `_member_cut_point` (also outside the list), for example by returning
no cut point for a member cut from a base of its own. That covers neither source 2 (A is not
a member) nor the closed-PR guard (the carry's PR states are not visible there).

## Decisions and rejected alternatives

**Findings 1 and 2: own the work, rather than keep the line (a seam) or hold D.** The
reviewer offered "fall back to the line (a seam) or hold D". Cost of each, against this
patch's `_owned_work` / `_holds_rejected` / `_own_base_cut` (`flow.py:1077-1140`, 64 lines
with docstrings) and `integrate.py`'s 19 added / 7 removed lines (9 / 3 of them code):

- A seam: about 4 lines in `_closure_members` (return a seam string when the walk takes a
  prerequisite edge from a finished bundle to an id outside the graph, or to one in
  `on_base`). But the brief narrows the carried-closure fallback to `Onto branch` / `Stacks
  on` only, and the line holds every carried bundle. With an unrelated carried X, D would
  hold X again: criterion (1)'s defect, back for these closures.
- A hold: about 15 lines (take D out of `runnable` with a stderr line), and holds belong to
  #725. It also leaves D unbuilt although a correct base exists.
- Owning each out-of-batch prerequisite's work through its own head (resolve `origin/fix/A`,
  walk its brief, own its work above its own cut point): about 25 lines, and it still
  refuses when A's branch moved or was rewritten after P was built on it. Source 1 needs no
  head of A at all.

**Finding 3: re-check after a failed build, rather than before every build.** A pre-check
would fetch each target with a carried member before every wave's builds (one more network
fetch per wave on every resumed run, about the same 10 lines). The re-check costs nothing
unless a build fails, and it reads exactly the fetch that failed. The reviewer suggested it:
"re-check `_merged_on_base` for gone carried members inside `_bundle_bases`, after its fetch".

**The guard: a stop, not a hold.** Holding P (a not-clean cascade by commit, so P's
dependents wait) would be the better outcome, but it changes #652's documented edge rule
(about 25 lines). It would also newly hold a P built on a partner whose PR was squash-merged
(not clean as "merged at a head neither the base nor the line has" once the line is gone),
which the base builds. The stop is v3's outcome, and its advice ("rebuild issue_P's branch on
a base without that work") fits a closed partner.

**Only carried members get the re-check.** #727's own built members have the same race (a
PR squash-merged mid-run, between its fold and a dependent's base build). Covering them is
one condition less in `flow.py:1064-1065`, but the reviewer called it #727's existing
hazard and the brief is about carried bundles, so I left it.

## Everything production changes (vs base)

`template/src/pdca_harness/flow.py`:

1. `_closure_members` (base `:913-958` → `:913-964`): parameter `built` → `graph`, plus
   `after`. The `finished` seam is gone (base `:947-949`). Edges to names outside `graph`
   are not followed (`:955`). Members: those reached and in `on_target`. Remaining seams: a
   walked `Stacks on` / `Onto branch` bundle, and a member pointed at a seam itself. That is
   the brief's "narrowing #727's carried-closure fallback". Docstring rewritten (`:917-941`).
2. `_bundle_bases` (base `:961-1012` → `:967-1039`): graph = carried finished ids plus
   patchless finished ids with a brief, at wave -1, then this run's bundles (`:1008-1010`).
   Member candidates exclude `on_base` (`:1013`). `heads = {**carried, **carried_heads}` is
   passed as both `carried=` and `excluded=` (`:1060`): criterion (5) through
   `_lost`/`_carried_rewrite`, criterion (4) through `_unowned_work`/`_foreign_refusal`. New
   in iteration 4: `on_base` is mutable (`:1003`), `closed` → `rejected` (`:1004-1005`), and
   the builds go through `_build_own_base` (`:1026-1029`).
3. New in iteration 4: `_build_own_base` (`:1043-1074`, finding 3), `_owned_work`
   (`:1077-1107`, findings 1 and 2), `_holds_rejected` (`:1110-1122`, the guard),
   `_own_base_cut` (`:1125-1140`), `_merged_since` (`:1143-1149`).
4. `_finished_after` (`:1152-1190`) and `_holds_work` (`:1193-1205`): unchanged from v3
   (iteration-1 and -2 findings).
5. `_finished_head` (base `:1097` → `:1290`): new `closed` out-parameter (`:1291`,
   `:1307-1310`).
6. `_merged_on_base` (`:1319-1335`): from v3; docstring now says "as last fetched (by the
   carry, or by a base build)".
7. `_cascade_not_clean` (`:1400-1429`) and `_plain_prereqs` (`:1432-1453`): unchanged from v3.
8. `_carry_finished` (base `:1212` → `:1456`): v3's changes, plus `closed` (`:1461`,
   docstring, call at `:1541`).
9. `_drive_and_act`: `carry_closed` (`:2876`), passed to the carry (`:2882`) and to
   `_bundle_bases` (`:2970`); comments (`:2867-2872`).

`template/src/pdca_harness/integrate.py`: `build_bundle_base` gains `owned`
(`:738`, docstring `:768`, `:780-783`, call `:871`); `_unowned_work` counts it
(`:992-1016`).

Not touched, per the brief's scope: `_runnable` (`flow.py:681-847`) incl. its
merged-prerequisite branch and `_line_lacks_merge` (#729); `_member_cut_point`,
`_gone_branch`, `fold`; the stack-rule docs (#725).

## Restated assertions and other test changes (before → after)

Unchanged since iteration 2. The three files' diffs are byte-identical to v3's, so these line
numbers are v3's and still right (re-checked against the patched tree). "Own base": the
recorded stack base is `integrate.bundle_base_branch(…, "issue_<id>")` (never the line), the
recorded tip is origin's tip of it, and the bundle is COMPLETE.

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
D's own base starts from freshly fetched main, which has the merge. The line facts are kept
as line facts (`:296-298`). The excluded-work check is stronger than before: "beyond main,
nothing but merges and fix/P". In this test P's branch is kept, so P is still a member.

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

## The new test — `template/tests/test_flow_carried_prereq_bases.py` (21 tests)

Real git on `StackFoldGit` through `flow._drive_and_act`, as #727's suite does. Briefs are
kept as written. `gh` answers OPEN unless a case sets `self.gh[id]`; after a case deletes a
branch, it also reports the head the branch had (`gh_heads`) and the merge commit
(`merge_oid`). Only modules are imported. New in iteration 4: the five tests marked ★ (the
three finding repros, source 2's case, and two guards).

"base" / "v3" come from swapping that `flow.py` (and, for base, `integrate.py`) in and running
the module. "Ablation" means the patched code with one part switched off. Script:
`$PDCA_WORKTREE/.scratch-728/ablate.py` (through `swap.py`, which restores both files
byte-identical after every run, checked by sha1).

| Test (line) | For | base | v3 | Ablation that turns it red |
|---|---|---|---|---|
| `…holds_only_its_own_prerequisite` `:267` | criterion (1) | red | green | — |
| `…patchless_bundle_carries_its_prerequisite` `:290` | criterion (2) | red | green | — |
| `…reached_only_through_a_patchless_bundle_is_carried` `:310` | iteration 1 | red | green | — |
| `…held_prerequisite_reached_through_a_patchless_bundle_holds_the_dependent` `:326` | iteration 1 | red | green | — |
| `…built_through_a_patchless_bundle_on_a_held_one_is_held` `:351` | iteration 2 | red | green | — |
| `…patchless_bundle_is_not_stopped` `:386` | criterion (3) | red | green | — |
| `…no_brief_declares_no_edge_to_walk` `:409` | guard (#597) | green | green | — |
| `…partner_built_before_a_carried_member_is_on_the_base` `:426` | iteration 1 | red | green | — |
| `…partner_built_after_a_carried_member_is_not_on_the_base` `:448` | iteration 1 | red | green | — |
| `…patchless_partner_built_before…` `:469` | iteration 1 | red | green | — |
| `…partners_on_a_base_the_checkout_lacks_stop_nothing` `:490` | iteration 2 (guard) | green | green | — |
| `…squash_merged_with_its_branch_gone_is_on_the_base` `:516` | iteration 2 | red | green | — |
| `…merged_elsewhere_with_its_branch_gone_is_not_on_it` `:538` | iteration 2 (guard); also the re-check not swallowing a branch merged elsewhere | red | green | — |
| ★ `…the_rest_of_a_stack_whose_bottom_was_squash_merged_is_built` `:563` | finding 1 | red (D on the line) | red (STOP) | both sources off |
| ★ `…member_cut_from_a_line_whose_prerequisite_was_squash_merged_is_built` `:593` | finding 1, source 2 | red | red (STOP) | source 2 off |
| ★ `…whose_prerequisite_the_re_issue_leaves_out_is_built` `:622` | finding 2 | red | red (STOP) | source 1 off |
| ★ `…squash_merged_after_the_carry_is_on_the_base` `:645` | finding 3 | red | red (STOP) | re-check off |
| ★ `…built_on_a_partner_whose_pr_closed_stops_its_dependent` `:670` | the guard | red (D built, holding K) | green (v3 stops too) | guard off |
| `…cut_from_a_line_holding_another_stops_its_dependent` `:702` | criterion (4) | red | green | — |
| ★ `…cut_from_another_bundles_base_stops_its_dependent` `:722` | source 1's precision: a base vouches only for the bundle it was built for | red | green | source 1 accepting any bundle's own base |
| `…rewritten_after_the_carry_stops_its_dependent` `:743` | criterion (5), a guard per the brief | red | green | — |

Totals from the last run of `ablate.py` on the final code: base 19 failing (all but the two
guards that pass on the base too); v3 4 failing (the four finding tests); each single
ablation exactly 1 failing, the test named above; "no owned at all" 3 (the three tests that
need source 1 or 2).

## Refuting my own test

- **(a) Genuine red?** Yes. The project's C4 gate (`engine/scripts/run-verify.sh`, with
  `PDCA_BUNDLE`/`PDCA_WORKTREE`, under `timeout 2400`) reverted the production hunks of both
  `flow.py` and `integrate.py`. The new file went 19 of 21 red. The two that stayed green are
  the guards that pass on the base too (no brief, and a base the checkout lacks). The
  restated files went 2 + 2 + 14 red. Output: `PDCA-EVIDENCE: C4 PASS — red without the fix,
  green with it`. Afterwards all six files were byte-identical to base + `patch.diff`.
  Against v3's `flow.py`, the four finding tests fail with the exact stops the reviewers
  reported (quoted above). Each part of the fix switched off alone turns its own test red
  (table).
- **(b) Production path?** Yes. Every case drives `flow._drive_and_act`. That runs the real
  carry (`_carry_finished`, a real `integrate.fold`, `_finished_head` with its `closed`
  record, `_merged_on_base` with a real `merged.merge_and_head` behind the `gh` stub), real
  `_runnable`, and real `_bundle_bases` → `_build_own_base` → `_owned_work` /
  `_own_base_cut` / `_holds_rejected` / `_merged_since`. Below those it runs real
  `integrate.build_bundle_base` → `_member_cut_point` / `_merge_published` / `_gone_branch` /
  `_unowned_work`, pushing real branches to a bare origin. Stubbed, as in #727's suite: the
  build/sign-off leaf (`flow._drive_wave` writes a patch, a close marker, or nothing, and
  accepts), `flow._publish_bundle` (cuts and pushes `fix/<id>` from the recorded stack-base
  tip, as publish does), `gh` (state, head, merge commit), and `publish.draft_texts`.
- **(c) Fixture includes the fault?** Yes.
  - Finding 1: a real first run builds P on a base of its own holding A (asserted on P's
    record). A's PR is then really squash-merged into main by the scratch clone (asserted:
    main lacks A's head), and `fix/A` really deleted on the bare origin. The carry and the
    builds see it gone through their real pruning fetches. The source-2 case really cuts P
    from an earlier run's real line holding A.
  - Finding 2: the re-issue really asks for a different batch (`[P, D, U]`), so A is really
    neither built nor carried (asserted: no `flow: carried issue_A`).
  - Finding 3: the squash merge and the branch deletion really happen after the carry's
    fold (the `after_line_fold` hook, asserted to have run once) and before D's base build.
  - The guard: K's PR reads CLOSED, and P's real base from run 1 really holds K (asserted).
  - The precision case: P's record really names X's real base of its own from a real
    first run, which holds Y (asserted).

## Gates run (the project's runners)

- `engine/scripts/run-verify.sh` (C4; `PDCA_BUNDLE` / `PDCA_WORKTREE` set; `timeout 2400`)
  on the final `patch.diff`: green leg 21 + 25 + 9 + 27 tests OK; red leg 19 + 2 + 2 + 14
  failures; `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`.
- `engine/scripts/run-suite.sh` (T3; same environment; `timeout 3000`) on the final tree:
  root suite `Ran 24 … OK`; driver suite `Ran 2602 … OK (skipped=2)` (iteration 3: 2596;
  the 6 new tests account for the difference); `PDCA-EVIDENCE: root suite OK, driver suite
  OK`.
- `engine/scripts/run-docs-check.sh` (T2): `PDCA-EVIDENCE: docs lint clean, site render +
  link audit clean`. The patch touches no docs.
- Formatter / commit hooks: the target has no pre-commit config, no Python formatter or
  linter config, and no installed hooks (only `.sample` files; `core.hooksPath` unset). Its
  CI (`.github/workflows/`) runs only docs and render checks. By hand: no added line is over
  99 columns (`flow.py` has 5 such lines on the base and still 5; `integrate.py` 2 and 2;
  the test files none); `git diff --check` is clean; all six files compile; an `ast` check
  finds no unused imports.
- Probes for claims below (scratch, not in the patch): `.scratch-728/probe_728.py`.

## Residuals for sign-off

- **A carried PR that no longer merges onto the fetched base stops the run.** Probe: run 1
  `[P, D, U]`; main then changes P's file; re-issue → "issue_P's branch origin/fix/P does not
  merge cleanly onto origin/main itself (conflicts in p.txt) … Rebuild issue_P's branch on
  the new origin/main (update it from origin/main and resolve the conflicts there), then
  re-run; STOPPING", and U is not built. On the base, D was built on the old line and
  COMPLETE (its PR would then conflict with main). v3 does the same as this patch. This is
  #727's rule for any member (a base starts fresh from the base), now applied to carried
  ones, as the brief asks. I kept it rather than fall back to the line, because the line here
  is stale and the brief prefers a stop to a wrong base. Following the advice works: after a
  merge-style "Update branch" of `fix/P` from main, the re-issue builds D on its own base
  and U on main (probed). That it stops the whole run, not just D, is the deferred [human]
  item about #725.
- **A carried P cut from an old *line* (before #727), whose prerequisite the re-issue leaves
  out, still stops.** Source 1 does not vouch for a line (it may hold unrelated work:
  criterion (4)), and A is in no carried bundle's head (probed: "No bundle of the run owns
  it … STOPPING"). The base built D on the line. This is the deferred [human] item about
  bundles built before #727. Re-issuing with A in the batch builds D (A carried, a member).
- **Rebasing P onto main after A's squash merge**: the carry holds P (run 1's line still has
  P's pre-rebase commit, "delete … on origin"), and once that line is deleted it holds P as
  built on A, which is then merged at a head neither main nor the line has. Both as on the
  base (probed). Not changed here.
- **Source 1 trusts the earlier build.** A member built on an old version of a prerequisite
  brings that old version (as the line did before #728). A prerequisite rewritten since,
  and also a member, may then clash on D's base (a stop naming both).
- **The guard covers only CLOSED PRs whose head the checkout has.** Another reason a
  finished id is not clean does not stop source 1, and neither does a CLOSED PR whose
  reported head this clone lacks (its branch deleted before it was ever fetched).
- **#727's built members still have the squash-merge race** (finding 3's shape for a bundle
  built this run). Not changed (see Decisions).
- **No end-of-run rewrite check for carried branches** (true before this change too):
  `rewritten_carried` judges only the run's `accepted` bundles.
- **Docs:** `docs/07-crosscutting.md:747-752` still says the carry "points that target's
  bundles at" the line. The brief puts stack-rule docs in #725, so I did not edit them.
- **Housekeeping:** my scratch scripts, logs and `flow.py` variants are in
  `$PDCA_WORKTREE/.scratch-728/` (untracked, outside `template/`, not in the patch). I
  removed nothing; the harness reclaims the worktree. The fixtures' temp dirs are cleaned by
  their `tearDown`.
