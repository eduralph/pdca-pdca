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
