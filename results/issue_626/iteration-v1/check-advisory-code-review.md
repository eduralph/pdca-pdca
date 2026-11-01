# Advisory code review — issue 626

No correctness bug found in the fold, carry or publish code paths the brief specifies. One behaviour needs a human decision, and three small cleanups follow.

## Findings

- NEEDS-HUMAN [human] — `template/src/pdca_harness/flow.py:1338` and `docs/07-crosscutting.md:814-819`: the hold ends when P is dropped from the batch, whether or not the dependent was updated. The hint and the docs give two steps: update Q from the base, then re-issue without P. Only the second step is checked, because the cascade (`flow.py:1426-1444`) follows edges only between ids in the batch. I ran this with a throwaway subclass of `ReissueCarry`: squash-merge P, leave Q not updated, then run batch `["Q", "D"]`. The run printed `carried issue_Q`, built D to COMPLETE, and gave no warning about P. D's line held both P's old head and the squash commit, so Q's and D's PRs keep showing P's change. The brief's Design section says the prerequisite "holds its dependents until they are updated from the base", and the code does not enforce that. `test_the_way_out_the_hold_gives_works` (`template/tests/test_stack_squash_merge.py:472`) only runs the path with the update done, so it can't catch this. Decide whether to accept this as advice only and soften the docs wording, or to check at the carry that the dependent's branch has the base's merge commit. The second option is new scope.
- `template/tests/test_stack_squash_merge.py:475`: the comment says the re-issue has "no `Depends on: P` left to wait on", but D's brief still names P (`:479`, `"Q, P"`) and Q's brief does too. The run passes because P is out of the batch and already merged, not because the edge is gone. Fix the comment, since it misdescribes what the test proves.
- `template/tests/test_stack_squash_merge.py:155`: `test_an_unreadable_brief_is_skipped` has only one other brief, and it is the unreadable one, so it would still pass if `publish._has_dependent` (`template/src/pdca_harness/publish.py:831`) did `return False` instead of `continue`. Adding a readable brief that names P, sorted after the bad one, and asserting the warning would pin the `continue`.
- `template/src/pdca_harness/flow.py:1474` and `template/src/pdca_harness/integrate.py:413`: the patch's docstring rewraps left lines of 112 and 102 characters, where the surrounding text wraps at about 95. Cosmetic only; no lint gate failed on them.

## Checked, no finding

- `publish._has_dependent` reuses `waves.declared_deps`, and the warning stays behind the existing `dry_run` return (`publish.py:336`), so a dry run asks no host. The extra brief reads are small next to the `gh` call that follows.
- `flow._cascade_not_clean` (`flow.py:1439-1442`) carries the root cause through a chain correctly, and other `built_on` holds are unchanged.
- The new hints fill in correctly from the arguments `_carry_finished` passes (`flow.py:1595`).
- Merge mode cannot reach the carry (`flow.py:2912`), so "Stack mode needs merge commits" is not printed there through that path.
- I ran 298 tests (`test_stack_squash_merge`, `test_integrate_stack_bases`, `test_flow_merged_prereq_on_line`, `test_flow_slice`, plus the three flow and integrate files that stub PR reads and the revert-via-branch file) with `gh` replaced by a logging stand-in. All passed and the stand-in logged no calls, so none of them reached `gh` through the new `merge_and_head` read or the wider publish warning. This does not cover the other four files that stub PR reads; the T3 gate ran the full suite green, but without logging `gh` calls.
- Not tested against live GitHub. The `mergeCommit` and `headRefOid` values come from the stub, as the brief allows (#625).

<!-- pdca:leaf-complete -->
