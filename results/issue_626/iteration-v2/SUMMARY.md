# Result — issue 626 / stack-squash-rebase-merge-recognised-and-refused-up-front

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: Stack mode keeps requiring merge commits, but says so where it can still help, and recognises a squash or rebase merge by name when one happens: (1) publish warns about a repo that does not allow merge commits for EVERY stack-mode PR that a later wave or a dependent builds on (today only a wave>0 PR warns, so the prerequisite — the PR that actually gets squashed — never does); (2) the fold, meeting a gone branch whose PR merged by squash/rebase, says that is what happened and what to do, instead of the generic "merged somewhere other than <base>"; (3) the re-issue carry stops giving a finished dependent of a squash/rebase-merged prerequisite the `built_on` advice "get issue_P carried", which points the wrong way.
- Success criterion: All hold on the offline fixture. "Stack mode" here means `cfg.wave_mode == "stack"` (the config value, default `"stack"`, config.py:363), not "has a stack base". "Another bundle depends on it" means some bundle dir under the results root (`cfg.bundle(iid).parent`, `issue_*/brief.md`) declares this id in `Depends on` / `Depends on (merged)` / `Stacks on`, read with `waves.declared_deps` (`template/src/pdca_harness/waves.py:39`). `publish.publish` does that scan itself, so standalone `pdca publish <id>` (cli.py:495), accept at sign-off (cli.py:1555) and the flow (flow.py:657) all behave the same, with no new parameter. (a) a stack-mode publish of a bundle that another bundle names in `Depends on` (wave 0, no stack base) prints the "does not allow merge commits" warning when `gh repo view` reports `mergeCommitAllowed: false`; (b) `integrate.fold` over a bundle whose branch is gone and whose PR is MERGED with a `mergeCommit` the base HAS but a `headRefOid` neither the base nor the line has, raises an `IntegrationError` whose message names a squash or rebase merge, gives the merge commit's oid, and does NOT contain "merged somewhere other than"; a gone-branch PR whose merge commit the base does NOT have keeps today's "merged somewhere other than" message; (c) in a re-issue, a finished P that is MERGED with its head on neither the base nor the line but its merge commit on the base, and a finished Q whose `Depends on` names P: **Q is still held** (refused, not carried), and Q's hold line names P as squash- or rebase-merged, says to rebuild or "Update branch" Q from the base, and does not contain "get issue_P carried"; P's own line names the squash/rebase merge and does not contain "remove the `Depends on:`" (the `edge` hint, flow.py:1319); (c2) a MERGED P whose merge commit is NOT on the base keeps today's `edge` reason and hint; (c3) when `mergeCommit` reads "" or cannot be read (`merged.merge_and_head`, merged.py:171), the fold keeps today's "merged somewhere other than" message and the carry keeps `edge` — fail closed, as `test_flow_merged_prereq_on_line.py:263` does for the build path; (d) a stack-mode publish of a wave-0 bundle with no stack base and no dependent prints no such warning (no new noise for an independent PR); (d2) a stack-mode publish of a PR cut from a stack base with no dependent still warns, as today (publish.py:370-371, #123); (e) a `wave_mode = "merge"` publish of a depended-on bundle prints no such warning (merge mode picks its own method).
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: Recognise a squash/rebase merge of a stack prerequisite and report it by name at the fold and at the re-issue carry; stop the carry's cascade from giving the wrong advice for it; extend the existing merge-commit warning at publish to the PRs others build on; document the choice in `docs/07-crosscutting.md` (stack-mode bullet at :646-652, the gone-branch paragraph at :686-691, and the "Known limits" list at :809-811). / out of scope: actually supporting squash/rebase merges in stack mode (alternative A below); merge mode (`[driver].merge_method` already picks the method the driver itself uses); turning the publish warning into a refusal; reading the merge method of an already-merged PR from any source other than the `gh pr view --json mergeCommit,headRefOid` answer the code already reads (`merged.merge_and_head`, merged.py:151).

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: new-feature
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: pass — C4 PASS — red without the fix, green with it
- C5 added test exercises production, not a copy: pass — 1 added driver-suite test(s) import the production package 'pdca_harness'

## 4. Conformance (Check — stack)
- T1 Structure: none — (no gate configured)
- T2 shape: docs lint + site render link audit: pass — docs lint clean, site render + link audit clean
- T2 host CI parity: target docs-check.yml on the pushed tree: pass — host CI parity on the patched tree — docs lint clean, site render + link audit clean
- T3 runtime: render/update-compat + offline driver suites: pass — root suite OK, driver suite OK
- T4 PR body has a user-impact opener + tracker id in both artifacts: deferred — pr-description.md not drafted yet — the substantive T4 audit of the contribution artifacts runs at publish
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Review issue #626: warn before publishing stack prerequisites to a repository without merge commits, and diagnose squash/rebase merges at fold and reissue with usable recovery advice.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The offline criteria distinguish unsupported merges, other-base merges, unreadable metadata, independent PRs and merge mode, with explicit held-dependent outcomes; `brief.md:10`. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing production changes reproduced 26 assertion failures across 50 tests, including the missing warning and misleading carry advice, without import errors; `review-red.log:424`, `template/tests/test_stack_squash_merge.py:547`. |
| C3 Change | PASS | Both publishing paths and both merge-diagnosis sites address the specified cases while dependents remain held; the complete supplied patch reverse-checks cleanly against the restored target; `template/src/pdca_harness/publish.py:535`, `template/src/pdca_harness/integrate.py:1448`, `template/src/pdca_harness/flow.py:1304`. |
| C4 Verification (red→green) | PASS | Restoring the same production changes made all 50 focused tests pass independently; frozen C4 evidence agrees and also covers the 62 existing integration tests; `review-green.log:147`, `gate-logs/C4-verify.log:35`, `gate-logs/C4-verify.log:637`. |
| C5 Causal adequacy | NEEDS-HUMAN | Discharge the live GitHub metadata/settings dependency — real squash/rebase responses and publishing warnings were not exercised against the host, so their evidence rests on stubbed responses despite real Git ancestry tests; `template/tests/test_stack_squash_merge.py:78`, `review-live-preflight.log:3`. |
| T1 Structure | PASS | Existing dependency parsing and a shared merge-classification helper keep fold and carry consistent without introducing a parallel state model; `template/src/pdca_harness/publish.py:848`, `template/src/pdca_harness/integrate.py:1483`, `template/src/pdca_harness/flow.py:1305`. |
| T2 Shape | PASS | Independent docs lint, 64-page render/link audit, six checker tests, relative-link and ADR checks, and whitespace checks passed; frozen docs and host-parity logs agree; `review-docs.log:3`, `review-doc-checkers.log:9`, `gate-logs/host-ci-docs.log:15`. |
| T3 Runtime | PASS | Independently ran all 2,747 driver tests successfully with two skips; the frozen root-suite log records 50 passing tests including render/update compatibility, which cannot be rerun locally because copier is not importable; `review-suite.log:1962`, `gate-logs/T3-suite.log:80`. |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the logged deferred result explicitly owes the substantive audit to publish, so no human clearance is needed now; `gate-logs/T4-contribution.log:10`. |
| T5 Judgment | NEEDS-HUMAN | Confirm semantic upstream-isn't-ahead — affected-path main history and files/patches from all ten closed, unmerged PRs revealed no equivalent feature, but the final semantic prior-art judgment remains human; `brief.md:22`, `review-history.json:2`, `review-closed-patches.json:2`. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Approve the warning-and-hold policy and manual recovery burden — removing the merged prerequisite from the batch releases a dependent even without updating its branch, leaving the old PR diff visible; `docs/07-crosscutting.md:824`, `template/tests/test_stack_squash_merge.py:873`. |

Source citations are relative to `$PDCA_TARGET` (`/tmp/pdca-review-v6svc9uz/target`); input and evidence citations are relative to this review directory. The target was readable and matched the supplied patch. Production changes were restored after the red leg; no implementation was edited.

Independent verification used `PYTHONPATH=src python3 -m unittest discover -s tests -p test_stack_squash_merge.py` from the target's `template` directory before and after restoring production changes, then `PYTHONPATH=src python3 -m unittest discover -s tests`. All temporary test files were directed inside this review directory. The production-import scanner also passed. The instance-scoped gate wrappers were adjudicated from their frozen logs; their absence from the target is expected. The root-suite result is frozen evidence, not a claimed local rerun.

The previous iteration's implementation concerns are covered by passing cases for an older head on origin's line, a head already carried by the line, `Onto branch` warnings, and consistent diagnosis for legacy/onto records. Recovery now checks that the updated dependent contains the squash commit and shows only its own file in the PR diff (`template/tests/test_stack_squash_merge.py:841`). The separate unchanged-branch case explicitly establishes the recovery limitation. No builder-fixable defect was found. The symptom-guard check found state classification, not a capability probe masking a load-time cause.

The prior-art rerun queried main's commit history for all seven affected paths and enumerated all ten closed, unmerged PRs, then inspected the affected-file patches of the eight that intersect those paths. The closed-PR squash/stack search returned no results (`review-squash-search.json`). Local history contains only the harness's single base commit, so the remote read-only queries supplied that evidence; no other checkout was consulted.

The live preflight passed: the private sandbox is reachable and its token can push. It did not create or merge PRs and therefore does not discharge C5. `AGENTS.md:18` restricts the live-tool merge exception to a human-started run. A human can exercise the existing host-metadata scenario from the patched target with:

```bash
python3 tools/live/stack_mode_live.py setup --workdir "$PWD/live-review-626"
python3 tools/live/stack_mode_live.py run --workdir "$PWD/live-review-626"
python3 tools/live/stack_mode_live.py judge --workdir "$PWD/live-review-626"
```

Check E4 for the real squash merge's `mergeCommit` on the base and `headRefOid` absent from it (`tools/live/stack_mode_live.py:1278`). That existing scenario does not cover the new warning/carry paths or a real rebase merge. For those, use a configured sandbox instance with finished prerequisite P, finished Q built on P, and planned D depending on Q: publish P while merge commits are disabled and confirm the warning; then squash-merge P and delete its branch before its head reaches the batch's line. Run `./scripts/pdca flow P Q D`: P must name the squash/rebase merge, Q must name P and offer Update branch/rebuild advice, and D must stay held. Update Q from the base and run `./scripts/pdca flow Q D`: Q should carry and D should proceed, with Q's PR showing only Q's change. Repeat the merge case using GitHub's rebase method. For an onto/legacy P, also follow the reported step to drop P from dependent briefs. These are the outstanding host/manual observations, not results already established by the offline suite.

<!-- pdca:leaf-complete -->

### Advisory — adversary

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

### Advisory — code-review

# Advisory code review: issue 626

I found no correctness bugs in this patch, and nothing needs a human decision. There are two small cleanups below, and neither blocks.

## Findings

- `template/tests/test_stack_squash_merge.py:417`: the name `test_those_records_keep_their_message_with_no_merge_commit_read` is misleading. In both cases the merge commit is read: one read returns no commit and the other fails. The test also never asserts that the read happened, so a mutation that skips `_squash_merged` for these records would still pass here. Rename it (for example `..._when_the_merge_commit_cannot_be_read`) and assert `"A"` and `"B"` are in `merge_commit_reads`.
- `template/src/pdca_harness/integrate.py:1454` and `template/src/pdca_harness/flow.py:1328`: the way-out text is written out by hand in three places: the fold's message, `_SQUASH_STEP`, and the `built_on_squashed` hint (`flow.py:1345`). The wording has already drifted: the fold says "re-drive", the carry says "rebuild". `integrate.py` already holds the shared `DROP_PREREQ`, so the common part could live beside it. Optional, because the three messages address different readers.

## Checked and found correct

- `_hold_all` (`flow.py:1365`) reads `why`, which is set before the `try`, so a `carry_view` failure cannot raise `NameError`. `causes` is also set before `foreign_commit` can raise, so a kept `built_on_squashed` line still names its cause.
- `_cascade_not_clean` (`flow.py:1458-1460`): a chain resolves to the merged id in any order. The loop only uses an id already in `why`, and a chained id gets its `causes` entry in the same step.
- `_finished_head` (`flow.py:1301-1303`): a head missing from the clone counts as off both refs without an error, because `_carries` returns False. An empty head skips the extra `gh` read and keeps the `open` hint.
- `_gone_branch` (`integrate.py:1445-1447`): checking the base earlier does not change the result for other-base records. A head on the base still makes no extra read and still raises the old message.
- `_others_build_on` (`publish.py:835`): it skips the bundle's own brief, catches `UnicodeDecodeError` through `ValueError`, and keeps scanning past an unreadable brief. The `Onto branch` return at `publish.py:225-228` happens before line 373, so no publish warns twice, and both warnings come after the dry-run return.
- "Re-issue without P" works from the real entry point: `flow_ids` passes `batch=list(ids)` (`flow.py:3545`) with no prerequisite added back, so the tests' direct `_drive_and_act` calls match it.

## Not checked

I read the code and the gate logs and did not run anything. The C4 and T3 logs show the new tests red before the fix and green after it, and the full suite passing. What `gh` reports for a real squash or rebase merge is still stubbed. The brief leaves that to #625.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] C5 Causal adequacy — Discharge the live GitHub metadata/settings dependency — real squash/rebase responses and publishing warnings were not exercised against the host, so their evidence rests on stubbed responses despite real Git ancestry tests; `template/tests/test_stack_squash_merge.py:78`, `review-live-preflight.log:3`.
- [ ] T5 Judgment — Confirm semantic upstream-isn't-ahead — affected-path main history and files/patches from all ten closed, unmerged PRs revealed no equivalent feature, but the final semantic prior-art judgment remains human; `brief.md:22`, `review-history.json:2`, `review-closed-patches.json:2`.
- [ ] Validation — fitness-to-purpose — Approve the warning-and-hold policy and manual recovery burden — removing the merged prerequisite from the batch releases a dependent even without updating its branch, leaving the old PR diff visible; `docs/07-crosscutting.md:824`, `template/tests/test_stack_squash_merge.py:873`.
- [ ] `docs/07-crosscutting.md:877-878`: this patch dropped "with its branch deleted" from the Known limits line, so it now says every squash- or rebase-merged prerequisite "holds the dependents" and is "named". That is false when the head is already on the line. Failing case: `template/tests/test_stack_squash_merge.py:643` squash-merges P, deletes its branch and keeps its head on the line. P and Q are carried, D reaches COMPLETE, and nothing names the merge. I ran this shape and the only line was `flow: carried issue_P, issue_Q`. The old sentence was also wrong for this shape, but the patch rewrote it and made it broader. Fix: limit it to a prerequisite "whose head is on neither your base nor the line", the wording already used at `docs/07-crosscutting.md:818-820`.
- [ ] `template/src/pdca_harness/flow.py:1301-1303`: on the recovery path the docs recommend, the merge is usually not recognised. The Goal says stack mode "recognises a squash or rebase merge by name when one happens", and the docs tell you to recover a stopped run by re-issuing the same `pdca flow <ids>`. In that run the line usually already holds P's head from the earlier fold, so P counts as clean and the run says nothing about the merge. In my run, `fix/Q` still differed from `main` by `p.txt` and `q.txt` after the squash, so its PR would keep showing P's change, with no message explaining why. The code does what the brief's design and criterion (c) ask ("head on neither"), so this is not a builder defect. The maintainer should decide whether silence is acceptable here or whether this shape deserves a warning, which needs a merge-commit read on this path. That read is what `test_stack_squash_merge.py:636` currently pins to zero.
- [ ] **Criterion (a) needs a batch view that `publish` does not have, and the brief does not say where it comes from.** `publish.publish(cfg, issue_id, *, dry_run, open_pr, by, today, skip_if_no_target, pending_id, texts_prevalidated)` (publish.py:120-131) takes no batch or dependents argument. It has three callers (cli.py:495 for standalone `pdca publish <id>`, cli.py:1555 for accept at sign-off, and flow.py:491/:657), and none of them passes the batch. The Goal says "that a later wave or a dependent builds on". Criterion (a) says "a bundle that another bundle of the batch names in `Depends on`". Meeting that means either threading a new parameter through flow (and deciding what the two cli paths do), or scanning every bundle's brief for a reverse `Depends on`. Either one is a design choice with its own review surface, and it is missing from Scope and Citations. The brief should name the mechanism and the expected behaviour of standalone `pdca publish`, since a human publishing a wave-0 prerequisite by hand is the likeliest squash case.
- [ ] **Criterion (a) does not say what "stack mode" means at publish time.** Today "stack" in publish means `stack_branch` is set (publish.py:238, :370). The brief's new meaning is the config `[driver].wave_mode` (default `"stack"`, config.py:363), but the brief never says so. Without that, Do could gate the new warning on either `cfg.wave_mode != "merge"` or something else, and criterion (a)/(d) do not pin which. State it, and add a case: a `wave_mode = "merge"` publish of a depended-on bundle prints no warning. That case is a real distinction, because merge mode picks the method itself (see the brief's own out-of-scope line).
- [ ] **Criterion (d) can be read as removing an existing warning.** (d) says "a stack-mode publish of a bundle no other bundle depends on prints no such warning". But a wave>0 bundle with a stack base and no dependents warns today (publish.py:370-371), and Design §1 says "not only for a PR cut from a stack base", which keeps that warning. As written, (d) either contradicts Design §1 or quietly removes the #123 warning. Narrow (d) to "wave 0, no stack base, no dependent". Better, add the inverse pin: a stack-base PR with no dependent still warns.
- [ ] **Criterion (c) contradicts Design §3.** Design §3: "Whether the dependent is still held or now carried is Do's call". Criterion (c): "Q's hold line names P as squash- or rebase-merged". If Do carries Q, there is no hold line, and (c) cannot be met or is vacuous. Pick one outcome now: still held with corrected advice, or carried, which is how it was before #670 per the owner's comment ("Before #670, Q was carried"). Otherwise the red→green test cannot be written before Do. The owner listed both options ("Either an `edge` hold doesn't cascade, or the hold's advice says…"), so this is exactly the decision the design proposal exists to make.
- [ ] **P's own new hint is never pinned.** Design §3 gives P "its own reason and hint (not `edge`)". The `edge` hint today is "remove the `Depends on: {iid}` edge from the dependent's brief" (flow.py:1319). Criterion (c) only asserts on Q's line. Add an assertion that P's own line names the squash/rebase merge and no longer gives the `edge` advice. Also add a negative case: a MERGED P whose merge commit is *not* on the base keeps `edge`. Without that pair, the reclassification in `_finished_head` (flow.py:1301-1303) has no falsifiable pin.
- [ ] **The carry change reads a new field, and the brief does not say so.** `_finished_head` gets its state from `merged.pr_state` (flow.py:1293), which asks only for `state,headRefOid` (merged.py:180). To tell "merge commit on base" apart from "merged elsewhere", it must also call `merged.merge_and_head` (`mergeCommit`), which is one more `gh` call per finished MERGED bundle. The fold has the same issue: `_gone_branch` uses `merged.merged_head` (integrate.py:1427, headRefOid only, merged.py:133). The out-of-scope line allows `merge_and_head`, but neither path's "unreadable merge commit" behaviour is specified. What happens when `mergeCommit` comes back "" (merged.py:171)? It should fail closed to today's message or hint, as test_flow_merged_prereq_on_line.py:263 does for the build path. Add that as a criterion.
- [ ] **The docs are in scope, but there is no criterion for them.** Scope edits docs/07-crosscutting.md at three places (:646-652, :686-691, :809-811). The issue's "Done when" requires "Document the choice". No criterion or gate checks the docs, and the Known-limits line at :811 currently says such a prerequisite "holds the dependents". If Do carries Q (see the (c) finding), that line becomes false. Tie the docs change to the chosen outcome and have a reviewer check it, or the docs drift is unfalsifiable.
- [ ] T5 Judgment — Confirm or accept the brief's path-based merged-history and closed/rejected-work prior-art conclusion — this target has one synthetic commit and no remote, so the asserted upstream search cannot be independently confirmed from the supplied artifacts (brief.md:22; affected target/template/src/pdca_harness/integrate.py:1473).
- [ ] `template/src/pdca_harness/flow.py:1338-1341` and `docs/07-crosscutting.md:816-819`: the hold lasts only while P is in the batch, not until Q is updated. Brief Design item 4 says a squash-merged prerequisite "**holds** its dependents until they are updated from the base". Failing case: after the hold, skip "Update branch" and re-issue `Q, D`. Q is carried, D reaches COMPLETE, and `fix/Q` still lacks the squash commit (`_ancestor(oid, fix/Q)` is False). So Q's PR keeps showing P's diff, and only the wording asks for the update. The harness could check this, because the base's merge commit would be an ancestor of Q's head. Decide whether wording is enough or whether the carry should enforce the update. The patched docs avoid saying "until", so they are accurate; the gap is between the patch and the brief.
- [ ] `template/src/pdca_harness/flow.py:1338` and `docs/07-crosscutting.md:814-819`: the hold ends when P is dropped from the batch, whether or not the dependent was updated. The hint and the docs give two steps: update Q from the base, then re-issue without P. Only the second step is checked, because the cascade (`flow.py:1426-1444`) follows edges only between ids in the batch. I ran this with a throwaway subclass of `ReissueCarry`: squash-merge P, leave Q not updated, then run batch `["Q", "D"]`. The run printed `carried issue_Q`, built D to COMPLETE, and gave no warning about P. D's line held both P's old head and the squash commit, so Q's and D's PRs keep showing P's change. The brief's Design section says the prerequisite "holds its dependents until they are updated from the base", and the code does not enforce that. `test_the_way_out_the_hold_gives_works` (`template/tests/test_stack_squash_merge.py:472`) only runs the path with the update done, so it can't catch this. Decide whether to accept this as advice only and soften the docs wording, or to check at the carry that the dependent's branch has the base's merge commit. The second option is new scope.

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: iterated-to-Do
- Iteration delta (if iterating): Auto-iterate (round 2): rebuilding for the implementation-level findings — `docs/07-crosscutting.md:877-878`: this patch dropped "with its branch deleted" from the Known limits line, so it now says every squash- or rebase-merged prerequisite "holds the dependents" and is "named". That is false when the head is already on the line. Failing case: `template/tests/test_stack_squash_merge.py:643` squash-merges P, deletes its branch and keeps its head on the line. P and Q are carried, D reaches COMPLETE, and nothing names the merge. I ran this shape and the only line was `flow: carried issue_P, issue_Q`. The old sentence was also wrong for this shape, but the patch rewrote it and made it broader. Fix: limit it to a prerequisite "whose head is on neither your base nor the line", the wording already used at `docs/07-crosscutting.md:818-820`.. Deferred, not addressed here: 10 finding(s) that need human judgment, held in deferred-findings.json for the human at handover — not build work
- By / date: auto-iterate / 2026-10-30

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 7 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
