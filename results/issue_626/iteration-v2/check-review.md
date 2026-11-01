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
