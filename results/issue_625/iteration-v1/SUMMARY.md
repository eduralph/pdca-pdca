# Result — issue 625 / stack-mode-live-github-check-tool

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: A standalone tool in pdca-harness, `tools/live/stack_mode_live.py` (stdlib only), with three steps: `setup` creates a private disposable GitHub repo (merge commits and squash allowed), pushes a base commit, and prepares a local checkout and bundle root with the scenario's briefs; `run` drives the scenario through the real driver code with the model leaves replaced by fixed patches (no model calls), real `git`, and real `gh`, merges PRs on GitHub, and records every observation as raw data in `observations.json`; `judge` reads `observations.json`, evaluates each named expectation, writes `report.md` + `report.json` (one line per check: id, PASS/FAIL, expected, observed), and exits 0 only if every check passes. `teardown` deletes the repo (`--keep` skips it). `judge` needs no network, so it can be tested offline and re-run on a saved `observations.json`.
- Success criterion: Binding (offline, C4): `tests/test_stack_mode_live_tool.py` runs `tools/live/stack_mode_live.py judge` as a subprocess on observation files it writes to a temp dir, and asserts: (1) observations matching every expectation below → exit 0 and `report.json` lists every check id as PASS; (2) observations where A's `gh pr view` after merge + branch delete has no `headRefOid` → non-zero exit and `report.json` marks check `E2` FAIL with the observed value; (3) observations where B's "Files changed" after "Update branch" still lists a file of A's → non-zero exit, `E1` FAIL; (4) a squash-merged S whose `headRefOid` is reported on the base → `E4` FAIL; (5) a PR whose `baseRefName` is the integration line → `E0` FAIL; (6) Q's files after P's merge listing a file of P's → `E1b` FAIL. **Hard sign-off condition (Validation, not optional):** before accept, the human runs `setup`, `run`, `judge`, `teardown` once against GitHub (e.g. from `pdca-pdca try 625`) and attaches `report.md` to the bundle and posts it on #625. This is what #625's "Done when" asks for, and it is the only check of `setup`/`run`/`teardown`. Sign-off records it as a §6 NEEDS-HUMAN item, open until the report is attached. A `run` that cannot drive the flow blocks accept. A FAIL in the report does not block accept: each FAIL is filed as its own bug, and with none, #625 closes.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: The tool (`setup` / `run` / `judge` / `teardown`), the offline test of `judge`, and a short section in `CONTRIBUTING.md` (or `docs/02-rehearse-offline.md`) on how to run it and what it costs. / out of scope: any change to `template/src/pdca_harness/` (a FAIL becomes its own bug); running the live check in CI; shipping the tool to rendered instances (it stays at the repo root, outside copier's `_subdirectory: template`, `copier.yml:13`); merge mode; model leaves (the scenario uses fixed patches).

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: new-feature
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: pass — C4 PASS — red without the fix, green with it
- C5 added test exercises production, not a copy: pass — no new driver-suite test in this patch — 1 added test file(s) out of scope

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

Review issue #625: add a reusable tool that exercises stack mode against GitHub and judges saved observations offline.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The six binding offline cases and separate mandatory live sign-off are explicit and falsifiable; brief.md:12. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing production files while retaining the test produced six assertion failures, exit 1; review-scratch/red.log:113; target/tests/test_stack_mode_live_tool.py:75. |
| C3 Change | PASS | The three affected files match the proposed tool, subprocess tests and contributor instructions; reverse-apply check confirms the supplied target matches patch.diff; target/tools/live/stack_mode_live.py:9; target/CONTRIBUTING.md:39. |
| C4 Verification (red→green) | PASS | Restoring the production stash independently changed six failing tests to six passes, exit 0; this verifies the binding offline judge criterion only; review-scratch/green.log:3; gate-logs/C4-verify.log:10. |
| C5 Causal adequacy | NEEDS-HUMAN [impl] | Require successful driver runs, all required PRs and confirmed branch deletion before claiming a complete observation — failed/held D still yields all PASS, and deletion failure is ignored; target/tools/live/stack_mode_live.py:273; target/tools/live/stack_mode_live.py:311; target/tools/live/stack_mode_live.py:368; target/tools/live/stack_mode_live.py:410; target/tools/live/stack_mode_live.py:240. |
| T1 Structure | PASS | Root-only tooling preserves rendered instances and uses the real flow/publisher with the two permitted model-leaf substitutions; target/tools/live/stack_mode_live.py:45; target/tools/live/stack_mode_live.py:265; brief.md:23. |
| T2 Shape | PASS | Independently reproduced docs lint, 22-page rendering/link audit and clean diff whitespace; captured docs and host-parity logs agree; review-scratch/docs-render.log:1; gate-logs/T2-docs.log:11; gate-logs/host-ci-docs.log:11. |
| T3 Runtime | PASS | Independently reran 2,630 driver tests and 25 root tests successfully; root update compatibility needs missing release tags here, but the frozen full-checkout log shows all 30 root tests passing; review-scratch/driver-suite.log:1819; review-scratch/root-suite-copier.log:5; gate-logs/T3-suite.log:60. |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the substantive contribution audit must rerun at publish; gate-logs/T4-contribution.log:10. |
| T5 Judgment | NEEDS-HUMAN | Approve the reusable tool's maintenance scope instead of the requested one-off run, and accept the prior-art search limits — path-based history/closed-work searches found no competing tool, but closed-PR text search cannot exhaust uncited patch paths; brief.md:69; review-scratch/prior-art.json:1. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Complete the real GitHub run and attach/post its report before acceptance — authenticated gh lacks delete_repo scope and no live report was supplied, so current behavioral evidence rests on curated judge inputs; brief.md:12; brief.md:21; target/CONTRIBUTING.md:50. |

Source citations under target/ were checked against $PDCA_TARGET. Its patch is present and reverse-applies cleanly; the production stash was restored and the target retains its original modified/untracked files. No production fixes were made.

Two implementation concerns require iteration:

- **A failed driver run can be certified as successful.** `_drive` records the driver return code, results and holds, but `scenario` never checks them and `cmd_run` fails only on exceptions (target/tools/live/stack_mode_live.py:278; target/tools/live/stack_mode_live.py:339). E0 checks only PRs that happen to be present, while E3 ignores run success and D's publication. Starting with the supplied good fixture, I set run 2 to rc=1, added a D hold and removed D's PR: `judge` exited 0 with all seven checks PASS (review-scratch/failed-drive-proof.json:2). Separately, a controlled scenario invocation returned normally when every `_drive` result had rc=1. A D publish failure after its build can therefore escape the live-run completion condition because subsequent scenario steps do not use D's PR. Preserve raw failure evidence, propagate incomplete driving through `run`, and add judge tests for failed/held runs and missing required PRs. Reproduce the saved false success with `python3 target/tools/live/stack_mode_live.py judge --workdir review-scratch/failed-drive`.
- **The squash-after-delete observation does not establish deletion.** `_merge` discards the DELETE request's exit status (target/tools/live/stack_mode_live.py:240). In a controlled invocation where the squash merge succeeded and DELETE returned a permission failure, `_merge` returned normally (review-scratch/delete-proof.json:2). Unlike A/C, S has no later gone-branch check; its retained branch can still satisfy E4's ancestry conditions (target/tools/live/stack_mode_live.py:422). Confirm deletion or record it as an execution error, and cover this failure case. These controlled invocations diagnose tool behavior; they are not live GitHub evidence.

All supplied gate logs were read. The production-path scanner explicitly excluded this root-suite test, so its green row is not independent driver coverage (gate-logs/C5-prod-path.log:10); inspection and the subprocess red→green rerun establish that the tests execute the actual tool. The system interpreter initially returned root-suite exit 77 because Copier was not importable; rerunning with `/home/eddie/.local/share/copier-venv/bin/python3` passed. The remaining root skip is the disposable checkout's missing release tags (target/tests/test_update_compat.py:245), not a patch defect. Frozen evidence covers the full root suite and update compatibility.

Prior-art investigation used GitHub commit history and closed-PR searches for each affected path: CONTRIBUTING.md, tools/live/stack_mode_live.py and tests/test_stack_mode_live_tool.py. Both new paths had no history or closed-search matches. CONTRIBUTING.md returned earlier license/process and truthful-Copier-evidence changes, with no competing stack live tool. Exact commands and results are saved in review-scratch/prior-art.json. Closed searches include merged and unmerged PRs but search indexed text, not every historical diff.

The maintainer's live validation remains concrete: from target/, use a token with repo and delete_repo scopes, create a fresh work directory inside the permitted workspace, then run `python3 tools/live/stack_mode_live.py setup --workdir DIR`, followed by `run`, `judge`, and `teardown` with that same argument (target/CONTRIBUTING.md:50). Confirm the scenario completed, inspect all E0/E1/E1b/E2/E3/E4/E5 observations, attach report.md to the bundle and post it on #625. Per brief.md:12, failure to drive the scenario prevents sign-off; completed observations that fail expectations become separate bugs. Scope approval and this live report remain human decisions.

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — issue 625 (stack-mode live GitHub check tool)

Lens: bugs the patch introduces, plus reuse/simplification. Lines are cited on `$PDCA_TARGET`.
The offline part (`judge` and its test) looks correct. The C4 red leg fails on assertions, not
on an import (`gate-logs/C4-verify.log`: "can't open file …/stack_mode_live.py", 6 failures).
Every driver API the tool calls exists with the signature it uses: `Config` fields
`base_remote` / `repo_checkouts` / `gates_checks` (`template/src/pdca_harness/config.py:155-162`),
`_drive_and_act(..., batch=, holds=)` (`flow.py:2709-2721`), `cli._results_rc(..., holds=)`
(`cli.py:707`), `publish.read_stack_base_tip` / `_publish_record` / `COMMIT_MSG` / `PR_BODY`
(`publish.py:40-41,644,698`), and `signoff.record` (`signoff.py:255`). The findings below are
all in the live `setup`/`run` path, which no gate runs.

- NEEDS-HUMAN [impl] — `tools/live/stack_mode_live.py:186-191`: `_on_base` treats every non-zero
  exit of `git merge-base --is-ancestor` as "not on base". Exit 1 means "not an ancestor", but
  exit 128 means "unknown commit" (for example, an object this clone never fetched). For `E4`,
  the expected value is `False` (`headRefOid` NOT on base, judged at `:422-423`), so a missing
  object would make `E4` PASS by accident: the one check #626 depends on. Return `True` on
  rc 0, `False` on rc 1, and `None` otherwise, so `judge` reports "not observed" instead of
  passing.
- NEEDS-HUMAN [impl] — `tools/live/stack_mode_live.py:240-242`: the branch delete after a merge
  runs with `check=False` and its result is never recorded. If the delete fails (wrong ref
  name, missing permission), `E2` is read "after delete" while the branch still exists, and
  run 2 never reaches `integrate._gone_branch` (`integrate.py:1406`). `E3` then FAILs with a
  misleading cause, and that FAIL would be filed as a driver bug. Either check the delete
  (allow 422 "Reference does not exist" in case GitHub auto-deleted the branch), or record
  whether the ref was gone in the observations.
- NEEDS-HUMAN [impl] — `tools/live/stack_mode_live.py:404-416` (E3): `gone` matches
  `"{branch} is gone and its PR merged"`. The same phrase begins the `IntegrationError`
  messages at `integrate.py:1443,1491,1503`, and on the carry path those errors are caught and
  turned into holds (`flow.py:1507-1520,1538`), not a `STOPPING` line. So `gone` and
  `not stopped` can both read true when the carry was refused. Today the `D_built_on_holds`
  term catches this, because a held D is never built. Still, the judge ignores `run2.rc`,
  `run2.holds` and `run2.results["D"]`, which `_drive` already records (`:278-279`) and the
  test fixture already fills in. Checking `rc == 0`, an empty `holds`, and D `COMPLETE` would
  make "no stop" mean what the brief says. Matching the success wording ("— taking" /
  "reaches … through", `integrate.py:1509`) would also be tighter than matching the shared
  prefix.
- `tools/live/stack_mode_live.py:115-117,139`: with `--reuse` and an existing workdir, only
  `checkout/` is wiped. `project/results/` keeps the previous run's bundles (accepted
  SUMMARYs, `publish.json` pointing at PRs that may be deleted), and `_drive` copies a brief
  only when one is missing (`:258-260`). A second run in the same workdir would then start
  run 1 with A, B and C already finished. Without `--reuse`, a fresh repo plus a leftover
  `checkout/` makes `checkout.mkdir()` raise *after* `gh repo create`, which leaves the repo
  behind. Suggest wiping `project/` along with `checkout/` on `--reuse`, and checking the
  workdir before creating the repo.
- `tools/live/stack_mode_live.py:224`: `_files` sleeps a fixed `--settle` time, then reads once.
  If GitHub is slow to recompute the PR diff, `E1` or `E1b` FAILs, and per the brief each FAIL
  is filed as its own bug. A short poll (re-read until two reads agree, or until a timeout)
  would cut false FAILs at little cost.
- Simplification, `tools/live/stack_mode_live.py:438` and `:462`: the overall pass/fail rule is
  computed twice, in `_report_md` and in `cmd_judge`. Pass `passed` into `_report_md` so the
  `.md` and `.json` reports cannot disagree. Also, `tests/test_stack_mode_live_tool.py:129`:
  `copy.deepcopy(_good())` does nothing, since `_good()` already returns a fresh dict. That
  makes the `copy` import unused.

No other correctness issues found in `judge` or the test. The six offline cases each check that
exactly one check fails and the rest pass, which is a meaningful test.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] C5 Causal adequacy — Require successful driver runs, all required PRs and confirmed branch deletion before claiming a complete observation — failed/held D still yields all PASS, and deletion failure is ignored; target/tools/live/stack_mode_live.py:273; target/tools/live/stack_mode_live.py:311; target/tools/live/stack_mode_live.py:368; target/tools/live/stack_mode_live.py:410; target/tools/live/stack_mode_live.py:240.
- [ ] T5 Judgment — Approve the reusable tool's maintenance scope instead of the requested one-off run, and accept the prior-art search limits — path-based history/closed-work searches found no competing tool, but closed-PR text search cannot exhaust uncited patch paths; brief.md:69; review-scratch/prior-art.json:1.
- [ ] Validation — fitness-to-purpose — Complete the real GitHub run and attach/post its report before acceptance — authenticated gh lacks delete_repo scope and no live report was supplied, so current behavioral evidence rests on curated judge inputs; brief.md:12; brief.md:21; target/CONTRIBUTING.md:50.
- [ ] `tools/live/stack_mode_live.py:186-191`: `_on_base` treats every non-zero exit of `git merge-base --is-ancestor` as "not on base". Exit 1 means "not an ancestor", but exit 128 means "unknown commit" (for example, an object this clone never fetched). For `E4`, the expected value is `False` (`headRefOid` NOT on base, judged at `:422-423`), so a missing object would make `E4` PASS by accident: the one check #626 depends on. Return `True` on rc 0, `False` on rc 1, and `None` otherwise, so `judge` reports "not observed" instead of passing.
- [ ] `tools/live/stack_mode_live.py:240-242`: the branch delete after a merge runs with `check=False` and its result is never recorded. If the delete fails (wrong ref name, missing permission), `E2` is read "after delete" while the branch still exists, and run 2 never reaches `integrate._gone_branch` (`integrate.py:1406`). `E3` then FAILs with a misleading cause, and that FAIL would be filed as a driver bug. Either check the delete (allow 422 "Reference does not exist" in case GitHub auto-deleted the branch), or record whether the ref was gone in the observations.
- [ ] `tools/live/stack_mode_live.py:404-416` (E3): `gone` matches `"{branch} is gone and its PR merged"`. The same phrase begins the `IntegrationError` messages at `integrate.py:1443,1491,1503`, and on the carry path those errors are caught and turned into holds (`flow.py:1507-1520,1538`), not a `STOPPING` line. So `gone` and `not stopped` can both read true when the carry was refused. Today the `D_built_on_holds` term catches this, because a held D is never built. Still, the judge ignores `run2.rc`, `run2.holds` and `run2.results["D"]`, which `_drive` already records (`:278-279`) and the test fixture already fills in. Checking `rc == 0`, an empty `holds`, and D `COMPLETE` would make "no stop" mean what the brief says. Matching the success wording ("— taking" / "reaches … through", `integrate.py:1509`) would also be tighter than matching the shared prefix.
- [ ] **The binding criterion tests the part with the least risk and leaves the deliverable #625 asks for unchecked.** #625's "Done when" is: "The scenarios above are run on a disposable GitHub repo … and the result (diffs shown, `gh` JSON shape) is recorded here." The brief makes that run "Supplementary (Validation, at sign-off)" and binds C4 to `judge` alone, a pure function over a JSON file that the test writes itself. `setup`, `run` and `teardown` hold all of the driver-integration and network risk, and no binding check covers them. C4 can go green while `run` cannot drive the flow at all. Either the Validation run must be a hard sign-off condition (not "supplementary"), or the criterion should include an offline smoke test of `run` (for example, against a local bare origin with `gh` stubbed, which is the peer's setup). Otherwise the only binding check is that the tool's own expectations agree with the test's own fixtures.
- [ ] **Scope grows from "run it once and record the result" into a new tool with a CLI, a test, and docs.** The thread asks for a single run whose result is recorded on the issue. The brief adds a new top-level `tools/` tree, four subcommands, repo-creation safety logic (`--owner/--repo/--reuse/--keep`, a prefix guard), a root test, and a CONTRIBUTING/docs section. The brief does justify this under Alternatives, but it is a maintainer decision (it also creates a new repo-root convention, since `tools/` does not exist on main). The human should accept it explicitly, not have it decided by default.
- [ ] **The cited peer for `run` stubs exactly the things the brief says will be real.** `template/tests/test_flow_same_wave_conflict.py:152-157` patches `subprocess.run` (the gh stub), `flow._drive_wave`, `flow._publish_bundle` and `publish.draft_texts`. Publishing in the peer is `self.fx._publish(...)` (`:131-142`), a fixture git push, and it never creates a PR. The brief says to mirror it "with … `gh` NOT stubbed" and with PRs opened for real. To do that, `run` has to call the real `flow._publish_bundle` → `publish.publish` (`flow.py:657-660`). That path drafts `commit-msg.txt`/`pr-description.md` through the publisher leaf when they are missing, and runs the T4 gate (`publish.py:69-108`, `_ensure_texts`). That conflicts with "no model calls", and the brief does not say how the texts are pre-supplied or how T4 is satisfied. The brief should name which stubs stay (`_drive_wave`, `draft_texts` or pre-written texts) and which are removed. It should also say how a root-level tool gets the `StackFoldGit` fixture, which lives in `template/tests/test_integrate_stack_bases.py` (`:36-39`), or that the tool does not use it.
- [ ] **The E3 expectation is not tied to any code path.** Run 2 is "a re-issue with `D` (`Depends on: B`) added", so the run is asked for a different id set. Per `docs/07-crosscutting.md:662-664`, the integration line's key "comes from the ids the run was asked to drive", so run 2 gets a new line, not run 1's. The brief does not show that the new run's fold will touch A's and C's gone branches (they are COMPLETE and merged, and `merged.merged_into`/`flow._runnable` may simply count them as merged and not fold them). If they are not folded, `integrate._gone_branch` (`integrate.py:1406-1455`) never runs and the "stderr names A's branch as gone and merged" message never appears. E3 would then FAIL against correct behaviour and file a false bug. The brief should cite the code path that makes run 2 hit `_gone_branch`, or reword E3.
- [ ] **E1 ignores the case the docs describe as expected.** `docs/07-crosscutting.md:655-661` says the PR diff is its own change once prerequisites merge *only when the line is a plain chain*; otherwise "Update branch" restores it. In the scenario, B depends on A and C from the same wave, so the fold creates a merge commit joining two branches, which is the non-plain case. E1 is checked only after "Update branch", which matches the docs. But the brief marks the before-state as "informational" and gives no expected value for a plain-chain control. The "Files changed" half of #625 ("inspect B's 'Files changed'") is therefore never actually judged against the docs' claim.
- [ ] **The brief ignores a load-bearing reference in the thread.** The issue says: "The round-1 reviewer's recipe is in `results/issue_593/iteration-v1/check-review.md` (pdca-pdca)." The brief's scenario and checks never mention it, so there is no statement on whether the A/C/B/D/S scenario covers that recipe or departs from it. The planner should reconcile with it or say why not.
- [ ] **A cited path is wrong.** The falsifiability section cites `engine/scripts/run-verify.sh`. On the target, the doctrine is referenced as `template/engine/scripts/run-verify.sh` (`tests/run_root_suite.py:14`). This is minor, but Do is told to "cite path:line on the target branch", and this citation will not resolve.
- [ ] **Target and dependencies check (no fault found).** The repo + branch target `eduralph/pdca-harness @ main` matches the issue URL. `Depends on: none` is consistent: no dependency-state.json was provided and none is needed. These citations resolve on the target: `merged.py:119-171` (`merged_head`/`merge_and_head`), `integrate.py:1406` (`_gone_branch`), `copier.yml:13` (`_subdirectory: template`) and `docs/07-crosscutting.md:646-661`. The brief also correctly replaces the thread's stale `merged.py:62-76` pointer.

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
- Iteration delta (if iterating): Auto-iterate (round 1): rebuilding for the implementation-level findings — C5 Causal adequacy — Require successful driver runs, all required PRs and confirmed branch deletion before claiming a complete observation — failed/held D still yields all PASS, and deletion failure is ignored; target/tools/live/stack_mode_live.py:273; target/tools/live/stack_mode_live.py:311; target/tools/live/stack_mode_live.py:368; target/tools/live/stack_mode_live.py:410; target/tools/live/stack_mode_live.py:240.; `tools/live/stack_mode_live.py:186-191`: `_on_base` treats every non-zero exit of `git merge-base --is-ancestor` as "not on base". Exit 1 means "not an ancestor", but exit 128 means "unknown commit" (for example, an object this clone never fetched). For `E4`, the expected value is `False` (`headRefOid` NOT on base, judged at `:422-423`), so a missing object would make `E4` PASS by accident: the one check #626 depends on. Return `True` on rc 0, `False` on rc 1, and `None` otherwise, so `judge` reports "not observed" instead of passing.; `tools/live/stack_mode_live.py:240-242`: the branch delete after a merge runs with `check=False` and its result is never recorded. If the delete fails (wrong ref name, missing permission), `E2` is read "after delete" while the branch still exists, and run 2 never reaches `integrate._gone_branch` (`integrate.py:1406`). `E3` then FAILs with a misleading cause, and that FAIL would be filed as a driver bug. Either check the delete (allow 422 "Reference does not exist" in case GitHub auto-deleted the branch), or record whether the ref was gone in the observations.; `tools/live/stack_mode_live.py:404-416` (E3): `gone` matches `"{branch} is gone and its PR merged"`. The same phrase begins the `IntegrationError` messages at `integrate.py:1443,1491,1503`, and on the carry path those errors are caught and turned into holds (`flow.py:1507-1520,1538`), not a `STOPPING` line. So `gone` and `not stopped` can both read true when the carry was refused. Today the `D_built_on_holds` term catches this, because a held D is never built. Still, the judge ignores `run2.rc`, `run2.holds` and `run2.results["D"]`, which `_drive` already records (`:278-279`) and the test fixture already fills in. Checking `rc == 0`, an empty `holds`, and D `COMPLETE` would make "no stop" mean what the brief says. Matching the success wording ("— taking" / "reaches … through", `integrate.py:1509`) would also be tighter than matching the shared prefix.. Deferred, not addressed here: 9 finding(s) that need human judgment, held in deferred-findings.json for the human at handover — not build work
- By / date: auto-iterate / 2026-10-23

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 8 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
