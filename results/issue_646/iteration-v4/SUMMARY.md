# Result — issue 646 / stack-reissue-continues-batch-line

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: In stack mode the recovery for a run that stopped part-way (an integrity stop,
  the pass budget, a crash, Ctrl-C) is to re-issue the same `pdca flow <ids>`. That resumed
  run builds a dependent on a base missing its prerequisite, when the prerequisite finished
  in the earlier run:
  - the finished id is skipped as already terminal (`template/src/pdca_harness/flow.py:2320-2325`),
    so it is not in the drive set and never enters `accepted` or the fold
    (`flow.py:2031`, `:2067-2070`);
  - `_runnable` sees it as out-of-batch (`batch_names` is the drive set, `flow.py:706`) and
    accepts it as ready because it is COMPLETE (`flow.py:710`) — COMPLETE only means a draft
    PR was opened;
  - nothing has been folded yet, so `_point_at_integration` clears the dependent's stack base
    (`flow.py:736-742`) and it is cut from the plain target base.
  The dependent is built, C4-verified and published without its prerequisite. Nothing
  reports it. The earlier run's line is usually still on `origin` under the same name (#591:
  the batch key comes from the ids as asked for, skipped ones included, `flow.py:2357-2363`,
  `integrate.py:67-83`), holding the prerequisite — but the resumed run never uses it, and
  its first in-run fold force-replaces it (`integrate.py:344-345`, `:401`), which strands any
  accepted-but-unpublished bundle whose recorded line tip was on it
  (`publish._line_tip_refusal`, `publish.py:691-726`).
- Success criterion: With the patch, in stack mode with publishing on (non-stub publisher),
  real git against a bare `origin`, a run driven as `flow._drive_and_act(cfg, [D], …,
  batch=["P", "D"])` (the shape `flow_ids` produces when `P` is skipped as finished) where
  `P` is COMPLETE, has a non-empty `patch.diff`, a resolvable target, a `publish.json` naming
  a pushed branch and an OPEN PR, and `D` has `- **Depends on:** P`:
  (1) before `D`'s wave is driven, origin's line `integrate.integration_branch(cfg, "main",
  ["P", "D"])` contains `P`'s branch head, and `D`'s recorded stack base
  (`publish.read_stack_base`) names that line and its tip (`publish.read_stack_base_tip`)
  is the line's tip. Pre-fix `D`'s stack base is cleared and no such line holds `P` — RED.
  (2) **Continue, never replace:** when origin already has that line (the earlier run's,
  holding `P` and an accepted-but-unpublished `H` whose recorded `stack-base-tip` is a commit
  on it), the run continues it: the old tip stays an ancestor of the new tip, no force-push
  happens, and after the run `publish._line_tip_refusal` for `H` returns `""`.
  (3) **Append-only across waves:** with a second driven bundle `E` (`Depends on: D`), the
  fold after wave 0 continues the same line without force and without `IntegrationError`;
  it then holds `P` and `D`, and `E`'s stack base names it.
  (4) **Holds, per prerequisite, named on stderr, rest of the run goes on:** each case below
  leaves `P` out of the fold, holds exactly `P`'s dependents in the drive set (they stay
  PLANNED, are not built), prints one line naming `P`, the held dependents and the reason
  with advice that works under (2), and lets an unrelated bundle `U` build:
  (a) `P` has no branch on record; (c) `P`'s PR state is
  CLOSED (not merged); (d) `P`'s PR state cannot be read (no `pr_url`, a `gh` failure, or
  `gh` missing — an `OSError` — never a traceback).
  (5) **Nothing to carry:** `P` COMPLETE with an empty or missing `patch.diff` ⇒ nothing is
  folded, `D` is not held and builds on the base as today. `P`'s PR MERGED ⇒ `P` is handed to
  the fold like an open one; the fold already decides it (`integrate._gone_branch`,
  `integrate.py:442-490`: line has the merged head ⇒ skip; base has it ⇒ take base in;
  otherwise raise).
  (6) **Fail closed:** the pre-wave fold raising `IntegrationError` stops the run before
  wave 0: nothing is driven, stderr names the failure the way the in-run fold's
  "did not integrate; STOPPING" line does (`flow.py:2076-2079`), no traceback.
  (7) **Unchanged:** a run with no named-but-finished id that a drive-set bundle's plain
  `Depends on` names behaves exactly as today (no pre-wave fold, stale stack bases cleared);
  `Stacks on` and `Depends on (merged)` edges do not trigger the carry and keep their
  behaviour (#123, #186); a dry-run (stub publisher) asks no host, holds nothing, and only
  prints the plan; `--no-publish` and merge mode are untouched.
  (8) **Unrelated bundle on a carried line:** when the carry happens, an unrelated wave-0
  bundle `U` (no dependency on `P`) has its stack base pointed at the same line and tip as
  `D` (`publish.read_stack_base` / `read_stack_base_tip`), and its published PR still targets
  the real base `main` (#593) — the same outcome a later-wave `U` gets today. Pre-fix `U`'s
  stack base is cleared.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: Make a re-issued stack-mode `pdca flow <ids>` carry the named ids that are
  already finished (COMPLETE, patched, targeted) onto its batch's integration line before
  wave 0, CONTINUING origin's line when it exists (append-only, no force) and starting it
  fresh only when it does not; then point the run's bundles at it exactly as later waves
  already are. The carry happens only when some bundle in the drive set names such an id in
  its plain `Depends on`; when it happens, every carryable finished named id is carried (the
  line is the batch's line, as the in-run fold carries every accepted bundle), and every
  same-target runnable wave-0 bundle — including an unrelated `U` — is pointed at it
  (`_point_at_integration`, `flow.py:722-742`; its PR shows the carried changes until they
  merge, as any later-wave PR does). A dependent held for some other reason (a
  `Depends on (merged)` wait, another held prerequisite) does not cancel the carry: the line
  is the batch's own, not that dependent's. A finished named id that cannot be carried
  (criterion 4a, 4c, 4d) holds only its own dependents — the same `held_unpushed` path the in-run
  fold uses (`flow.py:2052-2058`, `:712-713`) — and the hold message's advice must be one that
  works now the line is kept (e.g. "publish it with `pdca publish <id>`, then re-issue the
  same command"; for a closed PR, "re-open it or re-drive <id>"; for an unreadable state,
  say what could not be read). A failing pre-wave fold stops the run before wave 0. Update
  the stack-mode paragraph in `docs/07-crosscutting.md:658-677`, the "resuming across runs
  is #616" wording in `publish.py:345`, `:696`, `:726`, and the "known cross-run limit (#616)"
  docstring in `drift.py:58-61` so they describe the kept line. Existing tests pin the old
  wording — `template/tests/test_integrate_stack_bases.py:834-852` (asserts `"#616"` and
  `"re-drive it in a new run"`) and `:1012` (asserts `"#616"`): update those assertions to the
  new advice text in the same patch (they are in Do's review surface, and C4 keeps
  `tests/*.py`, so they must pass post-fix).
  / out of scope: a prerequisite that is NOT one of the requested ids, including the
  `flow_batch` sweep path (child-2); `merged.is_merged`'s "merged where" rule (child-2);
  `Depends on (merged)` semantics (#186, unchanged); `Stacks on` (unchanged); merge mode
  (#531); split children adopted mid-run by an earlier run (name the gap in a docstring);
  rebuilding the line from scratch; a line on origin that an outside party rewrote (the
  continued fold merges onto whatever origin has — say so in the docstring); pruning old
  integration branches (#454).

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
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

Review #646: resume a stack-mode batch on its existing integration line so dependents retain finished prerequisites without silently inheriting rejected work.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The prerequisite-preservation invariant and later recovery requirements are falsifiable; the expanded recovery behavior is explicitly authorized by the brief's carry-forward instructions (brief.md:217; target source: template/tests/test_flow_resume_stack_prereqs.py:384). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing production changes while retaining tests produced 38 assertion failures across 85 tests, including the missing prerequisite base, without import errors (reviewer-red.log:1101; template/tests/test_flow_resume_stack_prereqs.py:384). |
| C3 Change | PASS | No confirmed defect found: resumed lines preserve prerequisite ancestry, reject unaccounted-for commits, and handle recovered PR identity and deleted squash-merged branches; corresponding real-Git cases pass (template/src/pdca_harness/integrate.py:572; template/src/pdca_harness/merged.py:124; template/tests/test_flow_resume_stack_prereqs.py:928). |
| C4 Verification (red→green) | PASS | Restoring the production stash made all 85 focused tests pass; this independently reproduces the frozen C4 result for the offline contract, with live-host coverage limited as noted under Validation (reviewer-green.log:273; gate-logs/C4-verify.log:1400). |
| C5 Causal adequacy | PASS | The fix repairs the missing pre-wave carry and preserves the existing line, rather than masking the missing prerequisite; the production-import scanner also passes, and no capability probe hiding a load-time cause was introduced (template/src/pdca_harness/flow.py:798; template/tests/test_flow_resume_stack_prereqs.py:53). |
| T1 Structure | PASS | Sharing the fold, lock, tip read and re-gate prevents carry and later-wave behavior from diverging; Git ancestry and host lookup remain in their existing modules (template/src/pdca_harness/flow.py:754; template/src/pdca_harness/integrate.py:572; template/src/pdca_harness/merged.py:145). |
| T2 Shape | PASS | Independent docs lint, 22-page rendering, internal-link audit and whitespace check passed; frozen host-CI parity evidence agrees (docs/07-crosscutting.md:662; gate-logs/T2-docs.log:10; gate-logs/host-ci-docs.log:10). |
| T3 Runtime | PASS | Independent driver suite passed 2,364 tests with two skips; root render/update coverage is supported by the frozen log's 24 passing tests, since this review interpreter lacks importable Copier (reviewer-suite.log:2046; gate-logs/T3-suite.log:40; reviewer-root.log:6). |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the substantive contribution audit must rerun at publish, as the deferred gate states (gate-logs/T4-contribution.log:10). |
| T5 Judgment | NEEDS-HUMAN | Confirm merged and closed/rejected prior art across all affected paths — the brief records a path-based check for three modules, but this target has only one synthetic base commit and no remote, so independent completeness cannot be established (brief.md:167; template/src/pdca_harness/merged.py:145). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Accept the recovery policy and discharge live GitHub compatibility — real Git exercised the failure topologies, but PR lookup/state/merge metadata came from a stub, so host recovery remains unexercised; assess whether whole-target holds and deleting an unverifiable line with dependent rebuilds fit operations (template/tests/test_flow_resume_stack_prereqs.py:125; template/src/pdca_harness/flow.py:957; template/src/pdca_harness/integrate.py:547). |

Source citations above are relative to `$PDCA_TARGET`; brief and log citations identify review inputs or independent evidence in the scratch directory. The target is readable and contains the needed prerequisite APIs. After the stash/pop rerun, `git apply --reverse --check ../patch.diff` succeeded; the supplied patch remains applied and unchanged.

Independent verification used `PYTHONPATH=src python3 -m unittest tests.test_flow_resume_stack_prereqs tests.test_integrate_stack_bases` from the target's `template/`, first with production changes stashed, then restored. Logs are `reviewer-red.log` and `reviewer-green.log`. The complete driver run used `PYTHONPATH=src python3 -m unittest discover -s tests`, recorded in `reviewer-suite.log`. All temporary test roots were directed inside this review sandbox.

The root-suite rerun exited 77: 19 tests ran, three Copier-dependent classes skipped, and the runner explicitly reported missing importable Copier. This is a review-host limitation, not a patch failure. The frozen T3 log explicitly records successful render, CLI render and update-compatibility cases; that evidence supports T3 without claiming an independent root-suite pass. All six frozen gate logs were available. Instance-only wrappers were adjudicated through their logs and available target-side equivalent checks. The contribution deferral requires no human clearance at Check.

The regression cases exercise append-only continuation, late-publish ancestry, later-wave fixups, rejected/rebuilt commits, unknown deleted heads, missing PR URLs, replacement PRs, squash recovery, and a real red integration re-gate. The Git fixtures can exhibit the forbidden failures; the red rerun demonstrates this. The remaining external boundary is GitHub: `_GhTable` supplies its responses and publishing uses `open_pr=False`. Although the brief lists no external dependencies, that boundary has not been validated against the live service.

For the Validation decision, use existing PRs in a test instance to compare `gh pr view <recorded-url> --json state,headRefOid,mergeCommit` and `gh pr list --repo <owner/repo> --head <branch> --state all --json number,url,state,headRefOid,mergeCommit,headRefName,headRepositoryOwner` with the recovered identity. Cover an empty recorded URL with a merged/deleted branch and a closed PR replaced by an open PR. Reissue `pdca flow <P> <D>` in that test instance: D should use the continued line containing P, with its previous tip still an ancestor. Separately assess the documented refusal/rebuild policy; do not delete a production integration line merely to validate this review.

Prior-art investigation ran `git log --all --oneline -- <all nine affected paths>` in the supplied target and returned only synthetic commit `85f8a68` (labelled pre-fix base `12405dc952a556b710993014cc55d374a74c60f8`); `git remote -v` returned nothing. The brief records merged commits and closed PRs but supplies no independently searchable history. The available `template/docs/INTEGRATION.md.jinja:80` leaves project-defined human-only items as TODO; no populated instance integration document was supplied.

No confirmed patch defect was found. These verdicts are advisory; fitness-to-purpose and the identified evidence limits remain sign-off decisions.

### Advisory — adversary

# Adversarial review — issue_646 (stack-reissue-continues-batch-line), iteration 4

Advisory only. Every path:line is on `$PDCA_TARGET` (patch applied). The attack scripts ran
in this leaf's scratch dir against the patched tree. I also ran them against a copy of the
tree with the production hunks reverted (`git apply -R` of the `template/src/` hunks), which
gives the pre-fix comparison.

## What I tried and could not break

- **Red→green evidence holds.** Re-ran the green leg: `tests.test_flow_resume_stack_prereqs`
  plus `tests.test_integrate_stack_bases` gives 85 tests, OK. In the C4 log's red leg, 34 of
  the 39 new tests fail. The 5 that pass on both legs are `test_5_an_empty_patch…`,
  `test_5_a_missing_patch…` and the three `test_7_*`. All five check "unchanged" behaviour,
  so they are expected to pass both ways. No test of the new behaviour passes without the fix.
- **The tests use production code.** The real `flow._drive_and_act`, `integrate.fold`,
  `_runnable`, `publish.publish` (with `open_pr=False`) and real git against a bare origin.
  Only the build/sign-off step (`flow._drive_wave`) and `gh` (`merged.subprocess`) are
  stubbed. The re-gate test runs the real `gates.run_integration`.
- **`_vouch` / `_own` (integrate.py `_vouch`, `_own`).** I tried each of these cases and
  could not get a wrong vouch or a wrong refusal:
  - a wave>0 bundle whose branch was cut from the line;
  - "Update branch" (main merged into a carried PR branch);
  - a prerequisite merged with a merge commit and its branch deleted, where the base now
    holds its commits;
  - a squash-merged prerequisite whose head this clone has;
  - a fork setup. `origin` is always fetched with `--prune`
    (`integrate.py:719-722`), so stale refs can't make a deleted branch vouch.
- **`integ.update` replacing `integ = {...}`.** For a run with no carry the two behave the
  same: the in-run fold passes the cumulative accepted set, so a target never drops out of a
  later fold.

## Findings

- NEEDS-HUMAN [impl] — **The carry fires on a finished id that has nothing to carry, and
  then carries unrelated finished ids** (`template/src/pdca_harness/flow.py:852-861`). The
  trigger checks `finished`, which means COMPLETE only. It should check finished ids that are
  also patched and targeted, as the brief's Scope says ("names *such an id*" — "COMPLETE,
  patched, targeted"). `_fold_candidates` is only applied afterwards, at `:861`.
  Concrete case: batch `["P","Q","D"]`. P is a close/no-fix outcome (CLOSE_MARKER, no patch,
  COMPLETE). Q is an unrelated finished id with a patch, and the earlier run folded it. D has
  `- **Depends on:** P` only.
  - (a) Q's PR is OPEN. Output is `flow: carried issue_Q … so what depends on them builds on
    them`, and D's stack base is set to the line holding Q. Criterion (5) says that with P
    having nothing to carry, "nothing is folded … D builds on the base as today".
  - (b) Q's PR is CLOSED. Output is `flow: not continuing origin's … Holding issue_D`. D, whose
    only prerequisite has nothing to carry, is not built at all. On the pre-fix copy the same
    run builds D (COMPLETE).
  The test for criterion (5) (`template/tests/test_flow_resume_stack_prereqs.py:885-905`)
  never has a second finished id, so it cannot catch this. Fix: build the `any(dependents…)`
  trigger from `integrate._fold_candidates(finished)`, and add a test with an unrelated
  finished Q.

- NEEDS-HUMAN — **Two finished ids that conflict make every re-issue stop before wave 0,
  with advice that doesn't work** (`template/src/pdca_harness/flow.py:919-941`, advice text
  from `template/src/pdca_harness/integrate.py:497`). The carry folds every carryable
  finished id, including one the earlier run's own fold could not merge.
  Concrete case:
  1. P and Q both edit `same.txt`, are both finished, and both have OPEN PRs.
  2. The earlier run's first fold raised `issue_Q's branch … does not merge cleanly … declare
     the conflict / re-order, then re-run` and stopped.
  3. I followed that advice: added `- **Depends on:** P` to Q's brief.
  4. I then re-issued `["P","Q","D"]` twice (D depends on P only).
  Both re-issues print `flow: the finished prerequisite(s) issue_P, issue_Q did not integrate
  (… declare the conflict / re-order, then re-run); STOPPING — no wave run.` and drive
  nothing. Q is COMPLETE, so a re-issue never rebuilds it, and re-ordering cannot help. On the
  pre-fix copy the same re-issue went on and built D (without P — the original bug).
  This is the same pattern sign-off rejected in iteration 3 item 2: "a re-issue must not stop
  forever with advice that doesn't work". The ways out that do work are never printed: close
  Q's PR (Q is then held, and P alone carries), or reject/iterate Q so the run rebuilds it on
  the line.
  This needs a policy decision:
  - hold the finished id that does not merge, plus its plain dependents, and go on; or
  - keep stopping, but name the conflicting finished id and print advice that works.

### Advisory — code-review

# Advisory code review — issue_646 (stack-reissue-continues-batch-line)

Lens: correctness bugs the patch introduces, plus reuse / simplification / efficiency.
Advisory only. All gates in `check-gates.json` pass (C4 red→green per `gate-logs/C4-verify.log`,
T3 suite green). Lines below are on the patched tree at `$PDCA_TARGET`.

I found no correctness bug that blocks the success criterion. The shared
`flow._fold_and_regate` helper (`template/src/pdca_harness/flow.py:754-795`) removes the
duplicated fold + lock + tip-read + re-gate block, as the iteration-2 carry-forward asked.
Switching the in-run fold from `integ = {...}` to `integ.update(...)` is safe: the in-run
fold is cumulative and now always includes `carried`, so no target can drop out of `integ`.
The `_runnable` widening (`flow.py:719`) only affects out-of-batch ids that the carry put in
`held` and that are named in a plain `Depends on`, which matches the brief.

Smaller findings, none of which gate:

- `template/src/pdca_harness/integrate.py:527` and `:549` — `_gone_branch` calls
  `merged.merged_head` and then `merged.merge_commit`. Each one calls `merged.pr_state`
  again, which can be up to two `gh` calls each (`gh pr view` plus `gh pr list --head` when
  the recorded PR is CLOSED or `pr_url` is empty). So a squash-merged, deleted-branch
  prerequisite costs up to four host round trips per fold. The carry has already asked the
  same question at `flow.py:892`, and every later wave's fold repeats it because `carried`
  rides every fold. A simpler version calls `merged.pr_state` once in `_gone_branch` and
  reads `.head` / `.merge` from the result. This is about speed, not correctness: every
  answer comes from the same function, so they can't disagree.
- `template/src/pdca_harness/flow.py:863` — the dry-run branch of `_carry_finished` lists
  every fold candidate as "would carry", including one with no branch on record
  (`ref is None`). A real run would hold that one instead (`flow.py:886-890`). This fits
  criterion (7) ("asks no host, holds nothing"), but the plan it prints can name an id that
  the real run won't carry. Filtering on `ref is not None` here would make the plan match
  the real run without asking any host. Cosmetic.
- `template/src/pdca_harness/merged.py:171` — `_by_branch` compares
  `headRepositoryOwner.login` to the owner parsed from the checkout's remote URL, and the
  comparison is case-sensitive. This copies the existing `publish._existing_pr` rule
  (`publish.py:581-582`), so it isn't new debt in kind. But the patch now uses it in a place
  where a miss has a new effect: an owner whose case differs (for example `Eduralph` in the
  remote URL) would read as `"NONE"`, and the run would hold the dependents and say "open
  its PR by hand" even though the PR exists. Low likelihood; consider `.lower()` on both
  sides. Not filed as NEEDS-HUMAN.
- `template/src/pdca_harness/flow.py:995` and `:2223` — `stuck` (the bundles named as held
  for a blocked target) is computed once, at carry time, from the drive set as it was then.
  The wave filter at `:2223` also drops bundles that split adoption adds later. Today
  adoption can't add bundles of a blocked target, because its bundles are never driven, so
  this can't happen yet. If adoption ever reaches across targets, those bundles would be
  dropped without being named. Note only.

No NEEDS-HUMAN items from this lens.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T5 Judgment — Confirm merged and closed/rejected prior art across all affected paths — the brief records a path-based check for three modules, but this target has only one synthetic base commit and no remote, so independent completeness cannot be established (brief.md:167; template/src/pdca_harness/merged.py:145).
- [ ] Validation — fitness-to-purpose — Accept the recovery policy and discharge live GitHub compatibility — real Git exercised the failure topologies, but PR lookup/state/merge metadata came from a stub, so host recovery remains unexercised; assess whether whole-target holds and deleting an unverifiable line with dependent rebuilds fit operations (template/tests/test_flow_resume_stack_prereqs.py:125; template/src/pdca_harness/flow.py:957; template/src/pdca_harness/integrate.py:547).
- [ ] **The carry fires on a finished id that has nothing to carry, and then carries unrelated finished ids** (`template/src/pdca_harness/flow.py:852-861`). The trigger checks `finished`, which means COMPLETE only. It should check finished ids that are also patched and targeted, as the brief's Scope says ("names *such an id*" — "COMPLETE, patched, targeted"). `_fold_candidates` is only applied afterwards, at `:861`. Concrete case: batch `["P","Q","D"]`. P is a close/no-fix outcome (CLOSE_MARKER, no patch, COMPLETE). Q is an unrelated finished id with a patch, and the earlier run folded it. D has `- **Depends on:** P` only.
- [ ] **Two finished ids that conflict make every re-issue stop before wave 0, with advice that doesn't work** (`template/src/pdca_harness/flow.py:919-941`, advice text from `template/src/pdca_harness/integrate.py:497`). The carry folds every carryable finished id, including one the earlier run's own fold could not merge. Concrete case:
- [ ] **The declared target is not the code the brief was written against, and the success criterion can't run there.** The brief says `Repo + branch target: eduralph/pdca-harness @ main` (brief:87), but it says its own line numbers come from `origin/pdca-integration/main @ f594d8e` and that "#591's batch-scoped line name is REQUIRED by this fix and exists only there until PR #639 merges" (brief:4-7). The target checkout I was given (`$PDCA_TARGET`) is the `main` shape, and it lacks everything the criterion calls:
- [ ] **The rewording it plans breaks existing tests that the brief doesn't list.** The scope rewrites the "resuming across runs is #616" text at `publish.py:345`, `:696` and `:726` (brief:114-115). Existing tests check that text word for word:
- [ ] **The problem statement can't be checked against the tracker.** The bundle has no `notes.json` and no `sources/` directory; the cwd holds only `brief.md`. I can't confirm that the #616 thread frames the defect as "re-issued `pdca flow <ids>` builds a dependent without its finished prerequisite". I also can't check the claim that iterations v1-v3 were rejected for "fresh line + carry of any out-of-batch prerequisite" (brief:158-159), or whether a maintainer constraint came with that rejection. The human should confirm the thread before sign-off. The code side does support the hazard: the `_runnable` docstring says so at `flow.py:692-698`, and the out-of-batch COMPLETE acceptance is at `flow.py:706-711`.
- [ ] **Hidden second behaviour change: unrelated bundles get rebased onto the carried line.** The scope points "every same-target runnable wave-0 bundle — including an unrelated `U`" at the carried line, and accepts that "its PR shows the carried changes until they merge" (brief:103-106). That changes how bundles with no dependency on `P` are published. Today such a bundle's wave-0 stack base is cleared (`flow.py:736-742`). None of criteria (1)-(7) covers `U`'s PR diff, so it is unreviewed. Only (4) mentions `U`, and only to say it builds. Either justify it as part of the one fix or make it a criterion.
- [ ] **New PR-state hold policy is close to a second change.** Criteria (4b)-(4d) add new gating logic:
- [ ] size backstop — this slice is behaving oversized: patch is 149 KB (threshold 125 KB); 3 round(s) already spent (threshold 3). Recommend answering `iterate-plan` at sign-off and authoring the split in the re-plan (`pdca split`), rather than `iterate-do`: a slice that is too big yields implementation-shaped findings every round, and splitting authors briefs, which is Plan's beat.

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: iterated-to-Plan
- Iteration delta (if iterating): Rejected at sign-off (attempt 4): four rounds have each added special cases for another combination of PR state (open/closed/merged/replaced/no pr_url) x branch state (deleted/force-pushed/squash-merged) x what the earlier run's line holds (rejected commits, conflicting finished ids). The adversary finds the next combination every round; patch is 149 KB, over the size backstop. Root cause: the brief never fixed a policy for the non-clean case, so Do invents one per scenario. Re-plan #646 around ONE rule written into the brief: - Carry a finished prerequisite only in the clean case: PR OPEN (or MERGED and already reachable), branch head resolvable, and it merges cleanly onto the line. - Anything else, for any reason, holds only that prerequisite's plain-`Depends on` dependents, names the id + reason on stderr, and the rest of the run goes on. Never stop the whole run because of an earlier run's leftovers. - The carry triggers only on a finished id that is itself carryable (patched + targeted), not merely COMPLETE (adversary finding 1). - Two finished ids that do not merge together: the one that fails is held with its dependents, not a run-wide stop (adversary finding 2). Optionally split the per-case recovery advice (how to get unstuck for each hold reason) into its own child. Keep the criteria to the rule, not an enumeration of host scenarios. Note: #639 (#591) is still OPEN, not merged to main.
- By / date: Eduard Ralph / 2026-10-04

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 5 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
