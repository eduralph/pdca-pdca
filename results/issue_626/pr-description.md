## Summary
**User impact:** In stack mode, if you merge one of the stack's PRs with "Squash and merge" or "Rebase and merge" instead of a merge commit, the next `pdca flow` run stops with a vague message ("merged somewhere other than main") and a later re-issue holds every PR built on it with advice that cannot work ("get issue_P carried" — P is already merged). Nothing warned you beforehand: the "does not allow merge commits" warning fired only for PRs cut from a stack base, never for the first PR of the stack, which is the one most likely to be squashed.

This PR keeps the rule (stack mode needs merge commits) but says so where it can still help: publish now warns for any PR other bundles build on, and when a squash or rebase merge has already happened, the fold and the re-issue carry name it, give the merge commit, and tell you the way out — update or rebuild each branch built on it from the base, then re-issue without it.

Reported in [#626](https://github.com/eduralph/pdca-harness/issues/626).

## What to look at
- `template/src/pdca_harness/integrate.py` — `_gone_branch` now asks `_squash_merged` (new) before the generic "merged somewhere other than" stop, and `SQUASH_STEP` / `DROP_PREREQ` / `reissue_line` hold the shared advice text so the fold and the carry say the same thing.
- `template/src/pdca_harness/flow.py` — `_finished_head` returns a `squashed` / `squashed_drop` reason instead of `edge` for this shape; `_cascade_not_clean` passes a matching hint down to dependents; `_runnable` gains a `squashed` branch for a dependent whose prerequisite was squash-merged under a record that will never count as merged.
- `template/src/pdca_harness/publish.py` — `_others_build_on` (new) scans the results root for a brief that names this bundle, and both the new-PR path and the `Onto branch` path warn when it does.
- `template/src/pdca_harness/merged.py` — `counts_into` (new) is the one definition of "this record's merge counts for this base", used by `merged_into` and the new code alike.

To see it: with `wave_mode = "stack"`, publish P and a Q whose brief says `Depends on: P`, squash-merge P's PR on GitHub, delete its branch, then re-run `pdca flow P Q`. Before: Q is held with "remove the `Depends on` edge" / "get issue_P carried". After: P's line says it was squash- or rebase-merged, names the merge commit, and both P's and Q's lines say to update Q from `main` and re-issue without P. The offline tests below do the same on a bare `origin` with `gh` stubbed.

## Root cause
Since the fold began judging a gone branch by ancestry of its merged head (`integrate._gone_branch`), a squash or rebase merge — which leaves no such ancestor on the base — was indistinguishable from a PR merged into another branch, so both got the same generic stop. The pre-wave carry (`flow._finished_head`) classified the same shape as `edge`, and its cascade spread "not carried" to every finished dependent with the `built_on` hint, whose advice assumes the prerequisite can still be carried. The merge-commit warning at publish was keyed on "has a stack base", not on "something builds on this PR".

## Fix
- **Recognise the shape.** `integrate._squash_merged` reads `mergeCommit` through `merged.merge_and_head` and returns the oid when the base has it. It is read only for a MERGED PR whose head is on neither the base nor the line, so an open PR or an ordinary merge costs no extra `gh` call. An empty or unreadable merge commit, or one the base lacks, returns "" and every site keeps today's behaviour (fail closed).
- **Fold.** `_gone_branch` raises a stop naming the merge, the merge commit, and `SQUASH_STEP`. A merge commit the base lacks keeps the generic message; `Onto branch` and legacy `Stacks on:` records keep their "restore the branch" stop unless they were squashed as above.
- **Carry.** `_finished_head` returns `squashed` (or `squashed_drop` when `merged.counts_into` says the record can never count as merged into the base). `_cascade_not_clean` maps those to `built_on_squashed` / `built_on_squashed_drop` and names the merged id as the cause all along a chain. The dependent stays held. `_hold_all` keeps those reasons when an untrusted line or a failed read would otherwise overwrite every entry.
- **Records that never count.** `DROP_PREREQ` adds two steps to P's line, each line held for it, and the fold's stop: drop P from the briefs of the re-issued batch that name it, and delete the line that batch would continue on origin (`reissue_line` names it). Without the edge nothing checks that line for the merge, so a re-run that found it would build there without P's change. `_runnable` gives a dependent of such a record the same steps (`_uncounted_squash`) instead of "wait for the merge", and adds the delete step when the run's line lacks the merge or was not checked.
- **Publish.** `_others_build_on` scans `issue_*/brief.md` under the results root with `waves.declared_deps`; `publish` and `_publish_stacked` warn when it is true, in stack mode only. The warning text now says what a squash costs.
- **Docs.** `docs/07-crosscutting.md` states the rule, both messages and the way out, and narrows the Known-limits entry to "a prerequisite squash- or rebase-merged whose head is on neither your base nor the line".

## Verification
All source citations are on `main` at 381a78d85f33e20d104934e7e395e0e02833fd88, which the patch applies to cleanly. The new tests are in `template/tests/test_stack_squash_merge.py` (117 tests, real git on a bare `origin`, `gh` stubbed); 82 of them fail on the unpatched tree and all pass with it.

- **Claim (a): a wave-0 PR another bundle depends on gets the merge-commit warning.**
  Checked: `template/src/pdca_harness/publish.py:372-373` — warns only `if stack_branch`.
  Test: `PublishWarning.test_a_wave_0_pr_another_bundle_depends_on_warns` (`:188`); the `Onto branch` path at `:250`.
- **Claim (d, d2, e): no new noise.** No warning for an independent wave-0 PR (`:208`), a PR cut from a stack base still warns with no dependent (`:289`, pins #123), merge mode never warns (`:299`), a `gh` failure is silent (`:316`).
- **Claim (b): the fold names a squash or rebase merge.**
  Checked: `template/src/pdca_harness/integrate.py:1447-1453` — the generic stop lists "a squash or rebase merge" as one of two guesses.
  Test: `FoldOfAGoneBranch.test_a_squash_merge_is_named_with_its_merge_commit_and_the_step` (`:346`) asserts the message names the merge, gives the oid, and does not contain "merged somewhere other than".
- **Claim (b, negative): a merge commit the base lacks keeps the generic stop.** `:369`; an empty merge commit `:384`; an unreadable one `:392`; a merge with a merge commit never reads `mergeCommit` (`:400`).
- **Claim (c): the carry holds the dependent with the right advice.**
  Checked: `template/src/pdca_harness/flow.py:1301-1303` — the shape returns `edge`; `flow.py:1319` the `edge` hint ("remove the `Depends on` edge"); `flow.py:1322-1323` the `built_on` hint ("get {cause} carried"); `flow.py:1395` the cascade that spreads it.
  Test: `ReissueCarry.test_a_squash_merged_prerequisite_is_named_and_its_dependent_stays_held` (`:659`): Q is held, Q's line names P as squash- or rebase-merged, says to update or rebuild Q from the base, and does not contain "get issue_P carried"; P's line does not contain "remove the `Depends on:`".
- **Claim (c2, c3): fail closed.** A merge commit not on the base keeps the `edge` hint (`:965`); an unreadable one (`:978`) and an empty one (`:989`) too. A head already on the line is carried with no extra read (`:772`, `:775`).
- **Claim: the way out works when followed.** `:1022` updates Q from the base and re-issues without P: Q is carried, D is built, and the tip has the squash commit. `:1333` follows the drop and delete-the-line steps from a run with an older line on origin and asserts D's tip has the merge; `:1353` runs the same from a real first run and checks the file itself is in D's tip.
- **Claim: fold and carry agree.** `:845`–`:880` assert both sites name the merge for a new PR, a PR cut from a stack base, a rebase merge, an `Onto branch` record and a legacy `Stacks on:` PR, and that neither names a merge commit the base lacks.
- **Extra read is bounded.** `:1010` — an open PR or one merged with a merge commit never reads `mergeCommit`.
- Suites: the target's offline driver suite passes with the patch (2814 tests, 2 skipped); docs lint, site render and link audit clean; host CI parity clean. Tests ran on the bundle's build base (f5321ab294bf630984f31d6bbd0bbe11ef028019); the patch applies cleanly to `main` at the hash above.

## Known limits
The hold is advice, not enforcement: a dependent left as it was is still carried once P is out of the batch, and its PR keeps showing P's change until "Update branch". The squash check goes by the merge commit, so it cannot see a later revert of that commit on the base. The line named in the drop step assumes one merged prerequisite per target and the batch being re-issued as named; a different batch, or a second merge on another target of the same batch, gets the clause without a usable name. A follow-up issue will collect these. Live GitHub shapes for `mergeCommit` / `headRefOid` after a squash are #625's; the offline stub follows `merged.merge_and_head`'s documented contract.

Fixes #626
