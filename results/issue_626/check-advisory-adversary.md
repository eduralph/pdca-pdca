# Adversarial review: issue 626, attempt 6

The patch meets the brief's criteria, and the red→green evidence holds. I did refute the claim this round was rebuilt for, that "every printed message yields a correct build when followed". Two concrete cases still build D on an older line without the merge and print no warning. Both need an unusual batch, and the builder can fix both. I ran everything on a scratch copy of the patched target, using the test module's own fixture and `gh` stub.

## Refutations

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/flow.py:884`: `elif (unjudged and unmet) or carryable` assumes a bundle held for nothing else is built from the base once the edge is gone. That is false when D has a `Conflicts with` edge to a finished id, because that edge keeps D on the line (`_closure_members`, `flow.py:1070`). Failing case:
  - **Setup:** batch `R, E, D`. An older line on origin holds R. P has an `Onto branch` record and is squash-merged. E names R. D has `Depends on: P` and `Conflicts with: R`. The carry's fold fails, which I simulated by mocking `integrate.fold` to raise, as the patch's `test_a_fold_that_failed_leaves_the_line_not_checked` does.
  - **What it prints:** D's line says only "drop issue_P from issue_D's brief, then re-run". No line says to delete anything. R's line says to get its PR open.
  - **Result after following it:** the re-run carries R onto the older line and D reaches COMPLETE there. `git merge-base --is-ancestor` on P's merge commit and D's base says no, and the run names no merge.
  - **Controls:** when the carry succeeds, the same D is told to delete the line. Without the `Conflicts with` edge, D is built from the base and is correct. With R's PR closed instead of a failed fold, D's line is equally silent, but R's own line does say to delete that line, so someone reading both lines is safe.
  - **Why the tests miss it:** `template/tests/test_stack_squash_merge.py:1635` pins the plain message, and its comment ("once the edge is gone D is built from the base") is what this case disproves. `docs/07-crosscutting.md:932-934` also ties the "not checked" wording to being held for something else.
  - **Fix:** also give the "not checked" step when `d.name` is in `on_line` and no line was judged. Add this case as a test.

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/flow.py:1701` and `:1712`: `gone` is built separately for each target, and `template/src/pdca_harness/integrate.py:1462` passes only `[d.name]`, so the line named can be wrong when two merged ids are named in different places. `docs/07-crosscutting.md:832` says the steps name the line "for the batch without the merged prerequisite". Each message then names a batch that still holds the other id, which is a line nobody will use. Failing cases:
  - **Two targets (run through to the wrong build):** batch `P, O, R, S, D, E`. P and R target `main`, and O and S target `release`. P and O both have never-counting records and are squash-merged. An older line of `R, S, D, E` exists on each base. P's line names `main-r7ee5fd40abfc` and O's names `release-r5519663410a9`, but the re-issue both lines ask for continues `main-r573f15b4a530`. I dropped both edges, deleted the lines as named (neither exists) and re-issued `R, S, D, E`. D reached COMPLETE on the older line at `ad4360d37d9d`, without P's merge and with no warning.
  - **One target (wrong names confirmed, re-run not done):** P is held by the carry, and A's in-run fold stops on its own squash merge. P's line names the batch without P, and A's stop names the batch without A. Neither names `main-r75dfc0dcf477`, the line of the batch without both.
  - **Why the tests miss it:** `test_two_merges_name_the_line_of_the_batch_without_either` (`test_stack_squash_merge.py:1443`) covers only two ids on one target in the carry.
  - **Fix:** work out `gone` across all targets before printing any line, and pass the carry's `gone` into the fold's stop. If that is more than this slice should carry, narrow the docs sentence at `:832` to say the named line assumes one merged prerequisite per target.

## The evidence

- **Red→green holds.** With the four production modules restored to `HEAD` and the tests kept, `tests.test_stack_squash_merge` fails 82 of 117 on its assertions, not on an import. With the patch, all 117 pass. This matches `gate-logs/C4-verify.log`.
- **The tests run production code.** They drive `flow._drive_and_act`, `integrate.fold` and `publish.publish` over real git. Only `gh`, the leaves and the fixture's publish step are stubbed. C5's "1 added test imports the production package" proves little by itself, but reading the tests supports it.
- **The tests resist mutation.** I made 17 mutations of the patch's logic, including `reissue_line`'s filter, `gone`, both sides of the `:884` condition, the `batch` argument at both `_merge_published` call sites, `_hold_all`, the `counts` choice, the `on_line` check and the line half of "on neither". The new module failed for every one. So the two cases above are missing scenarios, not weak assertions.

## Tried, and could not refute

- **Message formatting:** the `{next_line}` and `{cause}` placeholders fill correctly on every hint path the tests reach, and ids written as `P` or `issue_P` give the same line.
- **Fail-closed criteria (b), (c2), (c3):** a merge commit that is empty, unreadable or not on the base keeps today's messages, and no extra read happens when the head is already on the base.
- **Other drop paths:** the fold's stop, Q's line and P's own line all give the delete step for a never-counting record, and following them from the first run builds on the merge (`test_stack_squash_merge.py:1353`, which I ran).
- **Reordering in `_gone_branch`:** moving the `on_base` check earlier changes no outcome for a merge-commit PR with an `Onto branch` or legacy record (`test_stack_squash_merge.py:1382`).

## Limits of this review

- **Verdict not reviewed:** no reviewer verdict is in my inputs, and `check-gates.json` has only gate rows. T4 is deferred until publish, so I have no specific verdict claim to dispute beyond the sign-off's wording quoted above.
- **Live GitHub not exercised:** the `gh` answers are stubbed, as attempt 4's ruling accepted (live validation belongs to #625).
- **Gates not re-run:** I ran only the new test module and my own scenarios. The full suite result (T3, 2814 tests OK) comes from the gate log.

<!-- pdca:leaf-complete -->
