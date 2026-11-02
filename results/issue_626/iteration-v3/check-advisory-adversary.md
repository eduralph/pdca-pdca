# Adversarial review: issue 626

I have three findings, and none breaks a parsed success criterion. Two are about advice that can send the user in a circle, and one is a gap between the brief's Goal and its criteria. The rest of the fix held up against the attacks listed below.

## Findings

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/flow.py:1341`: the held dependent's hint says "re-issue without {cause}" but leaves out the drop step (`DROP_PREREQ`, `template/src/pdca_harness/integrate.py:1485`) when the cause is an `Onto branch` or legacy `Stacks on:` record. I ran this case: P has an `Onto branch` record and was squash-merged, Q is built on P, and D has `Depends on: Q, P`. I updated Q and followed Q's line by re-issuing `Q, D`. D stays PLANNED, and `flow.py:836` tells the user "name issue_P in the same `pdca flow <ids>` command ... or wait until their PR merges into main". Naming P again brings back the hold that said to leave P out, and that PR will never count as merged into main, so the two messages send the user in a circle. P's own line does give the drop step, and the docs describe it as P's line, so only someone acting on Q's or D's line gets stuck. `test_the_way_out_of_an_onto_branch_record_drops_the_edge_too` asserts D is not built here but not what D's line says. Fix: add the drop step to Q's hint for those records, and make D's line stop advising a re-add for a squash-merged prerequisite.

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/flow.py:1307` compares only the record's `base`, but `merged.merged_into` also requires the record's `repo` to match (`template/src/pdca_harness/merged.py:112`). A `new-pr` record with the right base and a different `repo` string (say the repository was renamed or moved after publish) therefore gets no drop step, yet a D naming P is still held after "re-issue without P". The fold has the same gap (`template/src/pdca_harness/integrate.py:1445`). I found this by reading the code and did not run it. The shape is narrow, so fixing it together with the point above is enough.

- NEEDS-HUMAN [human] — `template/src/pdca_harness/publish.py:373`, `template/src/pdca_harness/publish.py:835`: the Goal says publish warns for every PR "a later wave or a dependent builds on", but the check covers only declared dependents. I ran this case: W has `Conflicts with: P`, and `waves.compute_waves` gives `[[issue_P], [issue_W]]`. W is in a later wave and is cut from a line holding P, yet P's publish prints no warning and makes no `gh repo view` call. A wave-0 bundle that shares a batch with a later wave but that nothing names behaves the same way. Criterion (d) requires this silence when there is "no dependent", so the code follows the criterion, and the Goal and the criterion disagree. The harm is small, because W warns at its own publish (d2) and the warning is about the whole repository. The maintainer should decide whether (d) or the "later wave" wording stands.

## What I tried that did not break it

- **Red→green evidence:** I reproduced it on copies of the target. `tests.test_stack_squash_merge` gives 53 tests OK with the patch. With `template/src` and `docs` put back to the base, 29 of them fail on their assertions, the same count as `gate-logs/C4-verify.log`. The failures come from assertions on real message text, not import errors.
- **Production path:** the tests call the real `publish.publish`, `integrate.fold` and `flow._drive_and_act` against real git. Only `gh`, the leaf build step (`_drive_wave`), `_publish_bundle` and `draft_texts` are replaced. The C5 gate only checks imports, so I checked this by reading the tests.
- **Mutations:** I made 12 changes to the patched code, covering the base check, the `_hold_all` keep, the chain cause, the head guard, the wave-mode guard, the `Onto branch` warning and the drop step. Ten failed tests. The two that survived both remove the `onto` / `ref[2]` half of `other_base`. They make no practical difference, because a real `Onto branch` record's base is always `<remote>/<branch>` (`integrate._published_ref`), which does not equal a target base name in any normal setup.
- **False "squash" naming:** I looked for a true merge-commit PR that would be named as a squash. The merge commit's parent is the head, so the head is on the base whenever the merge commit is, and the harness itself never asks for a shallow fetch. I found no such case, though I did not test a shallow checkout set up by hand, where the head could be missing.
- **Other scenarios I ran, all matching the docs:**
  - the way out through a finished bundle with no patch
  - a `Stacks on` plus `Depends on` dependent
  - a `Depends on (merged)` edge, which is not held
  - re-issuing the same batch after updating Q, which stays held
  - an earlier line that already has the squash commit but not P's head, which is held and named
- **The earlier rounds' findings:** the line-on-origin case, the "on the line" half, the way-out test, the `Onto branch` warning and the narrowed Known limits sentence are all fixed and tested. Removing the `_publish_stacked` warning fails a test, and the rest are covered by the mutations and scenarios above.

## Limits of this review

- A squash-merged PR whose branch still exists is not named by the fold. In my run, `fold` merged the branch and raised nothing. Criterion (b) covers only a gone branch, so this is not a defect, but the fold stays silent there.
- The `mergeCommit` and `headRefOid` answers come from a stub. The brief accepts this and leaves live GitHub validation to #625, so the real answer for a rebase merge is unconfirmed.
- I did not re-run the full suite or the docs gates. For those I relied on `gate-logs/T3-suite.log` (2750 tests OK, 2 skipped) and the T2 logs. T4 is deferred until publish, so it has not yet checked anything of substance.
- `check-gates.json` makes no claim I think is unwarranted. It holds gate results only, with no reviewer reasoning to challenge.

<!-- pdca:leaf-complete -->
