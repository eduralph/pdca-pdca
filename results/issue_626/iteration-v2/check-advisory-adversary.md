# Adversarial review: issue 626, stack squash/rebase merges

I could not break any of the brief's criteria (a) to (e), and the red-to-green proof holds. I found one false docs sentence, one scope question for the maintainer, and one small piece of wrong advice.

## Findings

- NEEDS-HUMAN [impl] — `docs/07-crosscutting.md:877-878`: this patch dropped "with its branch deleted" from the Known limits line, so it now says every squash- or rebase-merged prerequisite "holds the dependents" and is "named". That is false when the head is already on the line. Failing case: `template/tests/test_stack_squash_merge.py:643` squash-merges P, deletes its branch and keeps its head on the line. P and Q are carried, D reaches COMPLETE, and nothing names the merge. I ran this shape and the only line was `flow: carried issue_P, issue_Q`. The old sentence was also wrong for this shape, but the patch rewrote it and made it broader. Fix: limit it to a prerequisite "whose head is on neither your base nor the line", the wording already used at `docs/07-crosscutting.md:818-820`.

- NEEDS-HUMAN [human] — `template/src/pdca_harness/flow.py:1301-1303`: on the recovery path the docs recommend, the merge is usually not recognised. The Goal says stack mode "recognises a squash or rebase merge by name when one happens", and the docs tell you to recover a stopped run by re-issuing the same `pdca flow <ids>`. In that run the line usually already holds P's head from the earlier fold, so P counts as clean and the run says nothing about the merge. In my run, `fix/Q` still differed from `main` by `p.txt` and `q.txt` after the squash, so its PR would keep showing P's change, with no message explaining why. The code does what the brief's design and criterion (c) ask ("head on neither"), so this is not a builder defect. The maintainer should decide whether silence is acceptable here or whether this shape deserves a warning, which needs a merge-commit read on this path. That read is what `test_stack_squash_merge.py:636` currently pins to zero.

- Low severity, not worth a rebuild alone — `template/src/pdca_harness/flow.py:1345-1348`: the `built_on_squashed` hint can state something false about a dependent that has already merged. Failing case, which I ran: P is squash-merged, Q is rebuilt from `main` and merged with a merge commit, then the same batch is re-issued. Q's line says "issue_Q's branch holds commits origin/main never got: update issue_Q's branch", although Q's PR is merged, its branch is deleted and its head is on `main`. The last step, "re-issue without issue_P", is still right. It only happens if someone re-issues P after being told not to. If this round rebuilds anyway, have the cascade at `flow.py:1458` use different wording for a dependent whose head is already on the base.

## The evidence

- **Red to green:** this holds. In my own copies, `tests.test_stack_squash_merge` gave 26 failures against the pre-fix source and 50 passes against the patched source, matching `gate-logs/C4-verify.log`. The red failures I read are assertion failures on message text or missing warnings, not import errors.
- **Production path:** the tests use the real one. They use real git and the real `publish.publish`, `integrate.fold` and `flow._drive_and_act`. Only `gh`, `_drive_wave`, `_publish_bundle` and `draft_texts` are stubbed. The C5 row only proves that a test imports the package, so I checked this by reading the test file.
- **Hidden `gh` calls:** none from the new read. The patch adds a `mergeCommit` read that older tests could have reached for real, so I ran the whole driver suite with a logging `gh` stand-in. It logged 26 `gh` calls and none of them read `mergeCommit`.
- **Suite failures:** two `test_settings_permissions` tests fail in my copies, on the unpatched source too. The patch does not touch that area, so I don't count them against the fix.
- **Mutations:** I tried 18 small breaks of the patch, and 15 made the new tests fail. That includes the round-1 mutant that ignored the line, and removing the warning on the `Onto branch` path. The three that survived don't matter:
  - Dropping `onto` from `integrate.py:1445` changes nothing, because a valid `Onto branch` record's `base` is always `<remote>/<branch>` (`integrate.py:237-241`) and so never equals the target base.
  - Dropping `ref[2]` from `flow.py:1307` changes nothing, for the same reason.
  - Not catching `OSError` in `_others_build_on` (`publish.py:835`) is a real untested branch, but it only skips a brief that cannot be read.

## Other attempts that did not break the fix

- **False squash label:** a true merge commit on the base always brings the head with it, so the label cannot fire for one. A merge commit the base lacks, or one that is empty or unreadable, falls back to the old messages at both sites (`integrate.py:1483`).
- **Chains and mixed causes:** Q naming both a squash-merged P and a closed E gets advice for whichever comes first, and E's own line is printed in the same run. Chains, including through a finished bundle with no patch, name the merged id.
- **Way out:** I ran re-issuing without P through a no-patch bundle and with only the dependent left in the batch. D reached COMPLETE both times.
- **Merge mode:** the new message saying stack mode needs merge commits cannot appear there, because the carry and the fold are gated on stack mode (`flow.py:2932`, `flow.py:3124`).
- **In-run fold:** the named stop reaches the user through `flow.py:3163-3169`, with no contrary advice added.
- **Warning gap:** `_others_build_on` (`publish.py:835`) reads declared edges only, so a wave-0 PR that a later wave builds on with no declared edge gets no warning at its own publish. From reading only, not run: that later wave's PR has a stack base, so it warns about the same repo (`publish.py:373`). A `Stacks on` or `Depends on (merged)` dependent is carried rather than held, as the brief and the docs define it.
- **Round-1 findings:** all five are addressed in this patch, and I re-checked them by test or mutation.

## What I could not verify

- **Rebase merges on real GitHub:** `tools/live/stack_mode_live.py:945` exercises a squash merge only, and I did not run it. What `gh` reports for a rebase merge comes only from the test stub, as the comment at `test_stack_squash_merge.py:696-697` admits, and the brief leaves this to #625. If GitHub reports no merge commit there, the stop falls back to the generic message, so nothing unsafe happens, but `docs/07-crosscutting.md:737` would be overstating it.
- **The reviewer's verdict:** it is not in my inputs, so I can only judge the gate rows. The only one that claims less than it appears to is C5, covered above.

<!-- pdca:leaf-complete -->
