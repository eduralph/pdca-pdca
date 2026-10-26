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

Review issue #625: add a reusable tool that exercises stack mode on disposable GitHub repositories and judges recorded observations offline.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The six binding offline cases and separate mandatory live sign-off make success falsifiable; reusable-tool scope remains a human decision under T5 (brief.md:12; target/tests/test_stack_mode_live_tool.py:171). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing production while retaining the test produced 30 assertion failures across 21 tests, including the missing-tool subprocess failure (review-red.log:563; target/tests/test_stack_mode_live_tool.py:138). |
| C3 Change | PASS | The patch stays within the tool, root tests and contributor instructions; the added source files match the applied target byte-for-byte and no driver source changes are present (review-probes.json:29; target/CONTRIBUTING.md:39). |
| C4 Verification (red→green) | PASS | Restoring the production stash made all 21 tests pass, including the six required oracle cases; this verifies offline judgment, not the live GitHub scenario (review-green.log:3; target/tests/test_stack_mode_live_tool.py:184; gate-logs/C4-verify.log:10). |
| C5 Causal adequacy | PASS | The reviewed evidence supports distinguishing incomplete measurements from driver findings: real-git unknown ancestry stays unknown, stale samples are polled, and a raised run 2 is rejected; no capability-probe symptom guard was introduced (review-probes.json:3; review-probes.json:28; target/tools/live/stack_mode_live.py:895). |
| T1 Structure | PASS | The repository-root location keeps live infrastructure out of rendered instances, and only the two specified model leaves are replaced during flow execution (target/copier.yml:13; target/tools/live/stack_mode_live.py:380). |
| T2 Shape | PASS | Independent docs lint, 22-page rendering and internal-link audit passed; both frozen docs gates show the same substantive checks passing (review-docs.log:2; gate-logs/T2-docs.log:10; gate-logs/host-ci-docs.log:10). |
| T3 Runtime | PASS | Independently passed 2,630 driver tests with two skips and 40 root tests with one missing-release-history skip; frozen evidence additionally shows all 45 root tests passing (review-driver-suite.log:1819; review-root-copier.log:5; gate-logs/T3-suite.log:75). |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the substantive contribution audit is deferred to its mandatory publish rerun (gate-logs/T4-contribution.log:10). |
| T5 Judgment | NEEDS-HUMAN | Approve replacing the requested one-off validation with a maintained four-command tool, and resolve prior-art uncertainty: path-based merged-history and closed-PR searches found no equivalent but cannot exclude rejected work whose text omits those paths (brief.md:69; target/tools/live/stack_mode_live.py:993; target/CONTRIBUTING.md:39). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Complete the required live GitHub run and attach/post its report before sign-off: create/delete-capable credentials and the real host scenario were not exercised, so current evidence rests on curated observations and a fake gh/local-remotes setup; the available token lacks delete_repo (brief.md:12; brief.md:21; target/tests/test_stack_mode_live_tool.py:90; target/tests/test_stack_mode_live_tool.py:404). |

All source citations above ground on the applied disposable target at `$PDCA_TARGET`; input and evidence citations refer to this review bundle. No stale-target or patch-application defect was found. Production changes were restored after the red leg. No builder-fixable defect was established by this review.

Independent verification used `TMPDIR` beneath this review directory and disabled Python bytecode writes. The commands and their evidence were:

- Red: `git stash push --include-untracked -- CONTRIBUTING.md tools/live/stack_mode_live.py`, then `python3 -m unittest tests.test_stack_mode_live_tool`: 21 tests executed, 30 assertion failures; `git stash pop` restored production.
- Green: `python3 -m unittest tests.test_stack_mode_live_tool`: all 21 passed (`review-green.log`).
- Driver: from `target/template`, `PYTHONPATH=src python3 -m unittest discover -s tests`: 2,630 tests passed, two skipped (`review-driver-suite.log`).
- Root: the default interpreter returned 77 because Copier was not importable (`review-root-suite.log`). Using the existing Copier interpreter `/home/eddie/.local/share/copier-venv/bin/python3 -m tests.run_root_suite` passed 40 tests with one skip (`review-root-copier.log`). The skip is the release-update class requiring vX.Y.Z tags, absent from this synthetic single-commit target (target/tests/test_update_compat.py:245). The frozen run passed 45 root tests and 2,630 driver tests, with two driver skips (gate-logs/T3-suite.log:75; gate-logs/T3-suite.log:1897). This local history limitation is not a patch defect.
- Shape: `python3 docs/publishing/tools/lint_docs.py` passed; `python3 docs/publishing/tools/render_site.py --check --out /tmp/pdca-review-43qojnd_/review-site` rendered 22 pages and passed the link audit (`review-docs.log`). `git diff --check` passed.
- Extra probes exercised actual tool methods without changing source: an existing commit returned ancestor=true; an unknown object returned null; polling consumed two stale lists followed by two changed lists; `_require_driven` rejected a raised run 2 (`review-probes.json`). Virtual time and predetermined file responses in the polling probe do not establish GitHub behavior.

The instance-scoped gate wrappers were not present as runnable instance commands here. Every named frozen log was readable and inspected. `C4-verify` independently agrees with the red/green rerun. `C5-prod-path` explicitly says the new root test is outside its driver-package scanner scope; that scanner result is not affirmative production-path coverage (gate-logs/C5-prod-path.log:10). The test's subprocess invocation and independent production-stash experiment supply the relevant connection instead (target/tests/test_stack_mode_live_tool.py:138). Both docs logs and the runtime log contain substantive successful output. `T4-contribution` is deferred, not missing or green. The project's integration template enumerates no additional concrete human-only checks; its list remains TODO (target/template/docs/INTEGRATION.md.jinja:80).

Prior-art investigation ran against each affected path. The disposable target's `git log --all -- <affected paths>` contains only its synthetic base. GitHub commit-history API queries by exact path returned no commits for `tools/live/stack_mode_live.py` or `tests/test_stack_mode_live_tool.py`; for `CONTRIBUTING.md` they returned the Copier-skip fix aefdb548 and license/contribution introduction d6f47867. Closed-PR searches scoped to `eduralph/pdca-harness`, using each new file's exact path, and `"CONTRIBUTING.md" "stack"`, returned empty arrays. These checks cover merged path history and search closed/rejected work by path, but PR text search does not inspect every historical changed-file list. T5 therefore retains a human prior-art decision instead of treating an empty search as proof of absence.

For the outstanding live validation, a human should use the applied target and a fresh work directory. The token currently has `repo` but not `delete_repo`; `gh auth refresh -s delete_repo` obtains the missing scope interactively. This reviewer did not create a remote repository or run the merge steps: the project's explicit agent STOP rule reserves PR merge/ready actions to the maintainer (target/AGENTS.md:9), and the brief explicitly assigns the live run to human sign-off (brief.md:12).

```bash
cd "$PDCA_TARGET"
gh auth refresh -s delete_repo
LIVE_WORKDIR="$PWD/../live-check-625"
python3 tools/live/stack_mode_live.py setup --workdir "$LIVE_WORKDIR"
python3 tools/live/stack_mode_live.py run --workdir "$LIVE_WORKDIR"
python3 tools/live/stack_mode_live.py judge --workdir "$LIVE_WORKDIR"
python3 tools/live/stack_mode_live.py teardown --workdir "$LIVE_WORKDIR"
```

Inspect `observations.json`, `report.json` and `report.md` in that directory: verify the scenario actually completed, inspect E0/E1/E1b/E2/E3/E4/E5 and their recorded observations, and confirm teardown deleted the disposable repository. Attach `report.md` to the bundle and post it on #625. An INCOMPLETE report or an undrivable run leaves the hard sign-off condition unmet; a complete report with FAIL checks follows the brief's instruction to file each finding as a separate bug. Resolve the maintained-tool scope and prior-art decision separately before accepting the expanded deliverable.

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — issue 625 (round 4)

Scope: `tools/live/stack_mode_live.py`, `tests/test_stack_mode_live_tool.py`, the `CONTRIBUTING.md` section. I checked the tool's calls into the driver against the target source: `flow.flow_ids` keywords (`template/src/pdca_harness/flow.py:3370-3382`), `cli._results_rc(results, holds=)` (`cli.py:707`), `signoff.record` (`signoff.py:255`), `publish.COMMIT_MSG` / `PR_BODY` / `_publish_record` / `read_stack_base_tip` (`publish.py:40-41,644,698`), every `Config` field the tool passes (all exist, and all required ones are given), and the `origin/<branch>` ref shape `_gone_and_merged` expects (`integrate.py:241`). The em-dash wording in the E3 regexes matches `integrate.py:1434-1435` and `:1509-1511` byte for byte. Gates: C4 is red without the tool and green with it (`gate-logs/C4-verify.log`), and the T3 suite is green.

I found no correctness bug the patch introduces, and nothing that needs a human. The three fixes carried forward from earlier rounds are in place:
- `_is_ancestor` returns None for git's exit 128 (`tools/live/stack_mode_live.py:284-291`).
- The branch delete is checked, with `ls-remote --exit-code` confirming it (`:470-492`).
- A run 2 that raises is INCOMPLETE and makes `run` exit 1 (`:413-429`, `:601-607`). The file-list poll stops on stability alone, never on the expected value (`:686-691`).

Minor notes. None of them block, and none needs a human:

- `tools/live/stack_mode_live.py:740-747` — E3 relies on regexes that copy the prose of `integrate.py:1434-1436` and `:1509-1511`. The offline test copies the same strings by hand (`tests/test_stack_mode_live_tool.py:66-70`), so if that wording ever changes, both stay green while a live E3 reads `"gone and merged": null`. That is a complete-observation FAIL that would be filed as a driver bug. The run 2 stderr in `observations.json` shows the real cause, so the risk is low. A cheap guard would be a test that compiles the tool's patterns against lines built from the `integrate.py` format strings.
- `tools/live/stack_mode_live.py:340-360`, `:686-691` — when a PR's file list really does not change after an event (for example, B already shows only `b.txt` before "Update branch"), `_files` polls for the full `--settle-max` window (180 s by default) before it records the list. The result is correct, only slow. The docstring at `:37-43` already says this.
- `tools/live/stack_mode_live.py:481-490` — on the failure path, the `for … else` loop sleeps once more after the last `ls-remote` try before it raises (up to 10 s). This is harmless and only costs time.
- The `run` path (`Live`, `:245-575`) has no offline test. The brief accepts this, because the live run at Validation is the only check of `setup`/`run`/`teardown` and is a hard sign-off condition. So none of the driver wiring above has actually run yet.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T5 Judgment — Approve replacing the requested one-off validation with a maintained four-command tool, and resolve prior-art uncertainty: path-based merged-history and closed-PR searches found no equivalent but cannot exclude rejected work whose text omits those paths (brief.md:69; target/tools/live/stack_mode_live.py:993; target/CONTRIBUTING.md:39).
- [ ] Validation — fitness-to-purpose — Complete the required live GitHub run and attach/post its report before sign-off: create/delete-capable credentials and the real host scenario were not exercised, so current evidence rests on curated observations and a fake gh/local-remotes setup; the available token lacks delete_repo (brief.md:12; brief.md:21; target/tests/test_stack_mode_live_tool.py:90; target/tests/test_stack_mode_live_tool.py:404).
- [ ] **The binding criterion tests the part with the least risk and leaves the deliverable #625 asks for unchecked.** #625's "Done when" is: "The scenarios above are run on a disposable GitHub repo … and the result (diffs shown, `gh` JSON shape) is recorded here." The brief makes that run "Supplementary (Validation, at sign-off)" and binds C4 to `judge` alone, a pure function over a JSON file that the test writes itself. `setup`, `run` and `teardown` hold all of the driver-integration and network risk, and no binding check covers them. C4 can go green while `run` cannot drive the flow at all. Either the Validation run must be a hard sign-off condition (not "supplementary"), or the criterion should include an offline smoke test of `run` (for example, against a local bare origin with `gh` stubbed, which is the peer's setup). Otherwise the only binding check is that the tool's own expectations agree with the test's own fixtures.
- [ ] **Scope grows from "run it once and record the result" into a new tool with a CLI, a test, and docs.** The thread asks for a single run whose result is recorded on the issue. The brief adds a new top-level `tools/` tree, four subcommands, repo-creation safety logic (`--owner/--repo/--reuse/--keep`, a prefix guard), a root test, and a CONTRIBUTING/docs section. The brief does justify this under Alternatives, but it is a maintainer decision (it also creates a new repo-root convention, since `tools/` does not exist on main). The human should accept it explicitly, not have it decided by default.
- [ ] **The cited peer for `run` stubs exactly the things the brief says will be real.** `template/tests/test_flow_same_wave_conflict.py:152-157` patches `subprocess.run` (the gh stub), `flow._drive_wave`, `flow._publish_bundle` and `publish.draft_texts`. Publishing in the peer is `self.fx._publish(...)` (`:131-142`), a fixture git push, and it never creates a PR. The brief says to mirror it "with … `gh` NOT stubbed" and with PRs opened for real. To do that, `run` has to call the real `flow._publish_bundle` → `publish.publish` (`flow.py:657-660`). That path drafts `commit-msg.txt`/`pr-description.md` through the publisher leaf when they are missing, and runs the T4 gate (`publish.py:69-108`, `_ensure_texts`). That conflicts with "no model calls", and the brief does not say how the texts are pre-supplied or how T4 is satisfied. The brief should name which stubs stay (`_drive_wave`, `draft_texts` or pre-written texts) and which are removed. It should also say how a root-level tool gets the `StackFoldGit` fixture, which lives in `template/tests/test_integrate_stack_bases.py` (`:36-39`), or that the tool does not use it.
- [ ] **The E3 expectation is not tied to any code path.** Run 2 is "a re-issue with `D` (`Depends on: B`) added", so the run is asked for a different id set. Per `docs/07-crosscutting.md:662-664`, the integration line's key "comes from the ids the run was asked to drive", so run 2 gets a new line, not run 1's. The brief does not show that the new run's fold will touch A's and C's gone branches (they are COMPLETE and merged, and `merged.merged_into`/`flow._runnable` may simply count them as merged and not fold them). If they are not folded, `integrate._gone_branch` (`integrate.py:1406-1455`) never runs and the "stderr names A's branch as gone and merged" message never appears. E3 would then FAIL against correct behaviour and file a false bug. The brief should cite the code path that makes run 2 hit `_gone_branch`, or reword E3.
- [ ] **E1 ignores the case the docs describe as expected.** `docs/07-crosscutting.md:655-661` says the PR diff is its own change once prerequisites merge *only when the line is a plain chain*; otherwise "Update branch" restores it. In the scenario, B depends on A and C from the same wave, so the fold creates a merge commit joining two branches, which is the non-plain case. E1 is checked only after "Update branch", which matches the docs. But the brief marks the before-state as "informational" and gives no expected value for a plain-chain control. The "Files changed" half of #625 ("inspect B's 'Files changed'") is therefore never actually judged against the docs' claim.
- [ ] **The brief ignores a load-bearing reference in the thread.** The issue says: "The round-1 reviewer's recipe is in `results/issue_593/iteration-v1/check-review.md` (pdca-pdca)." The brief's scenario and checks never mention it, so there is no statement on whether the A/C/B/D/S scenario covers that recipe or departs from it. The planner should reconcile with it or say why not.
- [ ] **A cited path is wrong.** The falsifiability section cites `engine/scripts/run-verify.sh`. On the target, the doctrine is referenced as `template/engine/scripts/run-verify.sh` (`tests/run_root_suite.py:14`). This is minor, but Do is told to "cite path:line on the target branch", and this citation will not resolve.
- [ ] **Target and dependencies check (no fault found).** The repo + branch target `eduralph/pdca-harness @ main` matches the issue URL. `Depends on: none` is consistent: no dependency-state.json was provided and none is needed. These citations resolve on the target: `merged.py:119-171` (`merged_head`/`merge_and_head`), `integrate.py:1406` (`_gone_branch`), `copier.yml:13` (`_subdirectory: template`) and `docs/07-crosscutting.md:646-661`. The brief also correctly replaces the thread's stale `merged.py:62-76` pointer.
- [ ] size backstop — this slice is behaving oversized: 3 round(s) already spent (threshold 3). Recommend answering `iterate-plan` at sign-off and authoring the split in the re-plan (`pdca split`), rather than `iterate-do`: a slice that is too big yields implementation-shaped findings every round, and splitting authors briefs, which is Plan's beat.
- [ ] T5 Judgment — Approve the reusable tool's maintenance scope instead of the requested one-off run, and accept the prior-art search limits — path-based history/closed-work searches found no competing tool, but closed-PR text search cannot exhaust uncited patch paths; brief.md:69; review-scratch/prior-art.json:1.
- [ ] T5 Judgment — Approve maintaining a reusable four-command tool for an issue requesting one recorded run, and settle prior-art equivalence beyond keyword-indexed closed-work searches — scope and duplication affect the maintenance commitment (`target/tools/live/stack_mode_live.py:720`, `target/CONTRIBUTING.md:39`; brief.md, Open questions).
- [ ] `tools/live/stack_mode_live.py:328,331`: the tool runs `gh pr ready` and `gh pr merge`. `AGENTS.md` ("STOP discipline") says an agent must never merge a PR or mark one ready, "no path". The brief makes merging on the disposable repo part of the design and has the human run the tool. But the brief also suggests running it from `pdca-pdca try 625`, so an agent might start it. The maintainer should decide whether that counts as an allowed exception (disposable `pdca-live-stack-*` repo only) and, if so, say it in `CONTRIBUTING.md` or `AGENTS.md`. Otherwise the tool should refuse to run unless a human starts it.
- [ ] T5 Judgment — Decide whether the maintenance cost of a reusable four-command tool is justified for an issue asking for one live run — the brief explicitly reserves that scope expansion for the maintainer; affected-path history and closed-PR searches found no competing live tool (brief.md:69; target/CONTRIBUTING.md:39).
- [ ] `tools/live/stack_mode_live.py:391` and `:395`: `run` calls `gh pr ready` and `gh pr merge`. The repo's `AGENTS.md` ("STOP discipline") forbids an agent from doing either "no path, regardless". These calls only touch the disposable `pdca-live-stack-*` repo, and the brief has a human run the tool, so this is not a real breach. Still, if an agent ever runs the tool (for example from `pdca-pdca try 625`), it would break that rule as written. The maintainer should decide whether `AGENTS.md` (or the CONTRIBUTING section this patch adds) needs a line saying the rule covers the project's own PRs and not this tool's throwaway repo, or that only a human may run `run`.

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
- Iteration delta (if iterating): Live run blocked: the tool creates/deletes its own GitHub repo, but the assigned sandbox token (~/.config/pdca/sandbox-gh-token, fine-grained) cannot create repos ("Resource not accessible by personal access token" on createRepository). Re-plan so the tool uses the assigned sandbox token (read from that file, not the ambient gh login) and runs against the existing, pre-provisioned sandbox repo, which needs no setup (confirm its owner/name with the human in Plan). setup must not create the repo or change its settings; teardown must not delete it (decide in Plan whether it cleans up the run's branches/PRs so the repo can be reused). Also resolve the open plan-review items while re-planning: E3's code path to _gone_branch, the publish/T4 stubbing plan for "no model calls", the #593 round-1 recipe, the run-verify.sh path, and the STOP-rule exception for merges on the sandbox repo. Size backstop hit (3 rounds): consider splitting judge + offline test from the live run.
- By / date: Eduard Ralph / 2026-10-23

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 8 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
