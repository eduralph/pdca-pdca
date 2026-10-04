## Summary
**User impact:** If you re-run a bundle that was already split (to pick up its unfinished
child bundles) and in the same command name another bundle that depends on one of those
children, `pdca flow` refuses the whole command before doing anything, saying the
dependency is "neither in this batch nor an existing COMPLETE bundle". That is wrong: the
run would have picked up that child and built it first. Running the seed alone, or listing
every child by hand, works; naming the seed and the dependent together does not.

This PR makes the up-front check count the children the run will pick up from a named
seed, so the command runs and builds the child before the bundle that needs it.

Reported in [#590](https://github.com/eduralph/pdca-harness/issues/590).

## What to look at
The change is small: a quiet helper that lists the children a seed will pick up, and an
optional argument on the dependency check that treats those names as present. Nothing
else that uses the dependency check (`pdca waves`, the mid-run re-planning) passes it, so
they behave as before.

To try it: split bundle `500` into `601` and `602` (`602` depends on `601`), give bundle
`810` the line `- **Depends on:** 602`, and run `pdca flow 500 810 --no-publish`. Before:
exit code 2, nothing built. After: `601`, then `602`, then `810` are built, in that order.

Still refused up front, as before: a dependency on a bundle that is not one of the seed's
children, a dependency on a child that is already discontinued, resolved or has no brief,
`Stacks on:` any seed child, and any of these without the seed named.

**One deliberate behaviour change to review:** a dependency loop that runs through a
picked-up child (`810` depends on `602`, and `602` is re-planned to depend on `810`) used
to be refused up front with exit code 2. It now gets through the up-front check and is
caught by the mid-run re-planning instead: both `602` and `810` are held and named on
stderr, the rest of the request (`601`) still runs, and the command exits 1 because a
bundle you named was not built. A test pins this.

## Root cause
`flow_ids` moves an already-split parent out of the batch into a list of recovery seeds,
and `_drive_and_act` checks the named batch strictly (`compute_waves` → `check_dep_graph`)
*before* it adds the seeds' children to the schedule. At that point the child is neither in
the batch nor COMPLETE, so `check_dep_graph` raises, one statement before the child would
have been scheduled ahead of its dependent.

## Fix
- `waves.check_dep_graph` and `waves.compute_waves` take an optional keyword
  `offered: frozenset[str] = frozenset()`. A `Depends on` / `Depends on (merged)` edge to
  an offered name is accepted and adds no edge in the strict pass; the later seed splice
  re-levels the whole schedule with the child in place, and that is where the edge orders
  things. A `Stacks on` edge to an offered name falls through to the existing check and is
  refused. With the default the check is unchanged.
- New `flow._offered_by_seeds`: walks each seed's lineage record with the same reader
  adoption uses (`split.read_lineage` + `_lineage_children`), walks through children that
  are themselves split, and keeps a child only if it has a brief and is not terminal. It
  prints nothing and never raises, so adoption's own messages still appear exactly once.
- Only the strict call in `_drive_and_act` passes `offered`.
- The block comment just above that call (`flow.py:1868-1871` after the patch) still says
  the strict levelling is "exactly as before" and that "adoption never relaxes it"; the new
  lines below it explain the exception, but the older sentence could be reworded in review.

## Verification
- **Claim:** naming a split seed plus a bundle that depends on one of its in-flight
  children is no longer refused; the child is built in an earlier wave than its dependent.
  - **Checked:** `template/src/pdca_harness/flow.py:1830` and `:1836-1839` on `main`
    (`c67a14d`): the strict `compute_waves` call runs before the seed splice;
    `template/src/pdca_harness/waves.py:81-99` raises on the out-of-batch dependency.
  - **Fix at:** `flow.py:1743-1793` (`_offered_by_seeds`), `flow.py:1887-1889` (the strict
    call passes `offered`), `waves.py:65-66`, `:95-96`, `:172-173`, `:184` (patched tree).
  - **Test:** `test_a_named_id_depending_on_a_seeds_child_is_driven_after_it`, with
    `waves_driven == [["issue_601"], ["issue_602"], ["issue_810"]]`; and
    `test_a_seeds_grandchild_through_a_split_child_counts_as_offered`.
- **Claim:** `Depends on (merged)` behaves like `Depends on` here.
  - **Test:** `test_depends_on_merged_on_an_offered_child_resolves_like_depends_on`.
- **Claim:** everything the run will not schedule is still refused up front (exit 2,
  nothing built).
  - **Test:** `test_without_the_seed_or_off_its_lineage_the_edge_is_still_refused`,
    `test_a_child_not_offered_is_still_refused_up_front` (discontinued / resolved /
    no brief), `test_stacks_on_an_offered_child_is_still_refused_up_front` (alone, mixed
    with `Depends on`, and both fields on the same child).
- **Claim:** a child that is offered but not picked up (another live run holds it) leads to
  a hold, not a crash or an up-front refusal.
  - **Test:** `test_an_offered_child_another_run_holds_is_held_never_a_raise` (a real second
    process holds the claim).
- **Claim:** a loop through a picked-up child is held, named, and fails the run with exit 1.
  - **Test:** `test_a_loop_through_an_offered_child_is_held_never_a_raise`.
- **Red → green:** all in `template/tests/test_flow_adopt_recovery.py`. With the production
  hunks reverted and the tests kept, 6 fail (the main repro, grandchild, held-claim case,
  loop, `Depends on (merged)`, and the mixed `Stacks on` case, which the old code refused
  on `601` instead of `602`); with the patch all 22 pass. Full offline driver suite:
  2306 tests OK (2 skipped).

Fixes #590
