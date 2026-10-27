# Advisory code review — issue #728 (iteration 3)

Lens: bugs the patch introduces, plus reuse and simplification. Line numbers are on the patched tree at `$PDCA_TARGET`.

**Summary:** I found no blocking correctness bug. All three findings from round 2 are fixed, and each has a test:

- `_cascade_not_clean` now walks through patchless nodes (`template/src/pdca_harness/flow.py:1268-1269`). Test: `test_flow_carried_prereq_bases.py:348`, which also checks that the unrelated `U` is built.
- A carried PR that was squash-merged, with its branch gone, is walked through but never made a member (`flow.py:1201-1217`, `:1471-1473`). Tests: `:513` and the merged-elsewhere case at `:535`.
- `_holds_work` now also checks that `base_ref` resolves (`flow.py:1087`). Test: `:487`.

The round-1 findings are also covered: the `Conflicts with` order between finished partners (`:423`, `:445`, `:466`) and a prerequisite reached only through a patchless node (`:307`, `:323`). The gates are green: C4 is red before the fix and green after, and T3 runs 2596 tests OK. The restated assertions in the existing suites check content (own base, holds or lacks the same commits) and are not weaker. The no-op-looking read and write-back of `brief.md` in `test_flow_resume_stack_prereqs.py:130-134` is correct: it undoes the fixture's `_publish` rewrite.

Findings:

- NEEDS-HUMAN [human] — `template/src/pdca_harness/flow.py:934-935` (the `_closure_members` docstring) now documents a gap the patch leaves open on purpose. Take an out-of-batch prerequisite `S` (for example a split child that an earlier run adopted, #647) that is reached only through a finished patchless node: `D Depends on: N`, `N` has no patch, `N Depends on: S`. `_runnable` does not wait for `S` to merge, and the walk leaves the graph at `S` (`flow.py:955`). So `D` is built on the real base without `S`, with no hold and no warning. This is the brief's "ships missing a transitive prerequisite" outcome, through a different kind of node. The brief keeps `_runnable` out of scope (#729 owns it), so this is a scope call. Either accept it and open a follow-up, or hold such a `D`.
- Not verified, low risk: the carry's trigger and the base walk follow different edges through a patchless node. The carry starts only from plain `Depends on` edges, reached through patchless nodes by `_plain_prereqs` (`flow.py:1395-1400`). `_closure_members` also follows `Depends on (merged)` and `Conflicts with` edges out of a patchless node (`flow.py:948-958`). If a patchless `N` reaches a finished, uncarried `K` only by `Conflicts with` (`K` built first and below `N`'s cut point), nothing carries `K`. `K` is then not in `graph`, so `D` (`Depends on: N`) silently gets a base without `K`. I did not reproduce this. It is an edge case and close to what the code did before the patch, so I have not tagged it NEEDS-HUMAN. A short test would settle it.
- Small reuse and efficiency nit: `_merged_on_base` (`flow.py:1212`) makes a second `gh pr view` call per carried id whose branch is gone, through `merged.merge_and_head`. `_finished_head` already asked the host for that PR's state a few lines earlier (`flow.py:1187`). It costs one extra network call per merged, branch-deleted carried id, and only on resume. Returning the merge commit from the first read would save that call. It is not worth a rebuild by itself.

<!-- pdca:leaf-complete -->
