# Adversarial review — issue_724 (dependency-scoped bases, #463)

The red→green evidence holds up. I re-ran the new file and every suite named in criterion (10), plus `test_integrate_bundle_base.py`, on the patched tree: 308 tests, all OK. `gate-logs/C4-verify.log:1335-1337` shows all 19 new cases failing with the production change reverted, and they fail on assertions, not on import. The tests go through the real `flow._drive_and_act`, real folds and the real `integrate.build_bundle_base`; only build, sign-off, publish and `gh` are stubbed, which the brief allows. I found no tautology: `_built_on` compares ancestry against origin, and `_beyond`/`_own` (`tests/test_integrate_stack_bases.py:219-238`) do real rev-list checks.

I could not break `_closure` / `_ordered_after` on these cases:
- transitive edges through a bundle with no patch;
- a `Conflicts with` partner that never completed;
- carried partners found through `_cut_above`;
- held prerequisites in `held_unpushed`, `held_conflict` and `held_finished` (`_runnable` holds the dependent first in each case);
- members on another target;
- a same-wave newer head picked up through `carried_heads`.

The removal of the #655 check is clean: there are no callers left of `_line_lacks_merge` or `merge_and_head`. Two findings are left.

- NEEDS-HUMAN [impl] — **The rewrite reports now give the wrong commit and the wrong PRs.** The patch feeds heads that a bundle's own base took into the #633/#695 checks (`template/src/pdca_harness/flow.py:1017`, `carried_heads.update(took)`). But the messages still say the head is "the commit the line took" (`template/src/pdca_harness/integrate.py:1087-1090`). They also say the line "still carries the old commits, and so does every PR this run cut from {line}" (`integrate.py:1139-1144`), and the "unchecked" message says the same (`flow.py:2870-2877`). Since this patch, no PR is cut from the line. Concrete case: I ran the fixture from `test_a_head_a_base_took_is_checked_at_the_end_of_the_run` (`tests/test_flow_dependency_scoped_bases.py:495-505`) in a probe. The line tip holds h1 and **does not** hold h2. B's stack base is `pdca-integration/main-r…-bB`, not the line, and `fix/B` holds h2. Yet the report says h2 is "the commit the line took", that the line "still carries the old commits", and tells the human to rebuild "every PR this run cut from pdca-integration/main-r…". That set is empty. The PR that actually holds the dropped commit is B's, and the message never names it. The fold-time stop in `test_a_head_a_base_took_is_checked_by_the_next_fold` uses the same wrong wording through `_carried_rewrite`. The tests only check the message prefix and the sha (`:501-503`), so they miss it. Fix: record which bundle's base took each head, and say "B's base (`…-bB`) took h2; rebuild B's PR". Drop "cut from the line". These are runtime messages, not the docs or docstrings the brief defers to #725.

- NEEDS-HUMAN [human] — **A dependent of a legacy `Stacks on` or `Onto branch` prerequisite now stops the whole run, where before it was built.** Neither case appears in the brief's scope or out-of-scope list, and no test covers them. I checked both against a pre-fix copy of the tree:
  - *Legacy `Stacks on`, parent outside the batch:* B has `Stacks on: A` (A finished in an earlier run, not in the batch), and C has `Depends on: B`. A is not in `paths`, so B's closure is empty. `_point_at_integration` then clears B's stack-base record (`flow.py:842`). At wave 1, #723 refuses B as C's member because B "declares `Stacks on`" but has no record (`integrate.py:927-935`). Result: `STOPPING`, C PLANNED. Pre-fix, B and C are both COMPLETE.
  - *`Onto branch` prerequisite:* A is published with `Onto branch: upstream/feat`, and B has `Depends on: A`. `_member_cut_point` refuses any `Onto branch` member (`integrate.py:906-908`). Result: `STOPPING` at wave 1, B PLANNED. Pre-fix, B is COMPLETE. The line fold explicitly supports `Onto branch` bundles (`tests/test_integrate_stack_bases.py:354-376`, `:842-870`).

  Under #723's ownership rule, C's or B's base can never be built without commits that belong to no member. So writing a record will not fix this; it needs a decision. The options: support these as base members, hold the dependent (#725), or declare both edges unsupported in stack mode and refuse them at plan time. Until then, one such bundle stops every other bundle in its wave and every later wave.

Not filed, because the brief already accepts or defers them:
- Base-build failures, including a transient fetch failure (`test_flow_merged_prereq_on_line.py`'s fetch case), now stop the run instead of holding one bundle.
- A carried prerequisite built on a line from before this change, holding unrelated work, stops a re-issued run (criterion 7).
- Cross-wave text conflicts at the line fold now stop runs, because later bundles are no longer built on the line (#725).

Not checkable here, since `build-notes.md` is withheld: criterion (10) requires every test-input change to be listed in `build-notes.md` with before and after. Three input changes need checking:
- `tests/test_flow_reissue_after_conflict_hold.py`: 21's edge goes from `Depends on: 12` to `12, 10`.
- `tests/test_flow_resume_stack_prereqs.py`: `_publish_bundle` now restores the brief.
- `tests/test_integrate_carried_rewrite_late.py`: the race trigger moved to B's base push. The old line-push race is kept as the new case (1d).

<!-- pdca:leaf-complete -->
