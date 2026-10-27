Review issue #625: add a repeatable GitHub stack-mode validation tool and ensure stale PR file-list observations are reported as INCOMPLETE.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The offline acceptance cases, live sign-off obligation, sandbox boundary and policy decision are explicit and distinguish host observations from driver failures (brief.md:13, brief.md:21, brief.md:102). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing production changes left the subprocess tests executable: 21 tests produced 40 assertion failures because the tool was absent, with no import errors (reviewer-red.log:621; target/tests/test_stack_mode_live_tool.py:34). |
| C3 Change | PASS | The four affected paths fit the approved tool/test/documentation scope; driver implementation remains untouched, and the subprocess exercises the actual standalone tool (patch.diff:1; target/tests/test_stack_mode_live_tool.py:169; target/tools/live/stack_mode_live.py:260). |
| C4 Verification (red→green) | PASS | After stash restoration, the same 21 tests passed with zero skips, independently reproducing the offline contract; this does not establish live GitHub behavior (reviewer-green.log:3; gate-logs/C4-verify.log:10). |
| C5 Causal adequacy | PASS | Identical stale reads can no longer substantiate E1/E1b: both final reads must match the expected base/head and the poll must be synced; regression cases cover false sync and stale commit identities (target/tools/live/stack_mode_live.py:993; target/tests/test_stack_mode_live_tool.py:308). |
| T1 Structure | PASS | Offline judgment is separate from remote orchestration, imports resolve to this checkout's driver, and only model-leaf boundaries are replaced during flow execution (target/tools/live/stack_mode_live.py:260; target/tools/live/stack_mode_live.py:566; target/tools/live/stack_mode_live.py:1055). |
| T2 Shape | PASS | Independent docs lint and site render/link audit passed for 22 pages; git diff --check was clean, consistent with both frozen documentation gates (gate-logs/T2-docs.log:11; gate-logs/host-ci-docs.log:11). |
| T3 Runtime | PASS | Independent offline driver suite passed 2,630 tests with two skips; the frozen root-suite log records 45 passing render/update tests, which I could not rerun because copier is not importable here (reviewer-driver-suite.log; gate-logs/T3-suite.log:75; gate-logs/T3-suite.log:1897). |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the deferred gate explicitly requires the substantive PR/commit audit at publish (gate-logs/T4-contribution.log:10). |
| T5 Judgment | NEEDS-HUMAN | Accept the STOP-policy exception separately — it authorizes human-started guarded tool merges/ready-marks and changes the project's maintainer-only boundary (target/AGENTS.md:14; target/CONTRIBUTING.md:88; brief.md:13). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Complete and accept the real sandbox run/report — the assigned token, PR permissions, draft support and live GitHub topology were not exercised; current evidence rests on curated observations and fake gh, so issue #625's live obligation remains open (brief.md:22; target/tests/test_stack_mode_live_tool.py:121; target/tests/test_stack_mode_live_tool.py:404; target/CONTRIBUTING.md:58). |

No confirmed implementation defect was found. All source citations above were checked against the patched disposable target at `$PDCA_TARGET`; it was readable and consistent with the patch. The C5 capability-probe smell-test found no probe masking a load-time capability dependency.

Independent evidence: production/documentation changes were stashed while retaining the new test, the red leg ran, the stash was popped, and the green leg ran. The target's original patch state was restored. The command was `python3 -m tests.run_root_suite tests.test_stack_mode_live_tool`. The full driver rerun used `PYTHONPATH=src python3 -m unittest discover -s tests` from `target/template`. Temporary files and render output were confined to this review directory.

The C5 scanner's frozen log reports the root test out of scope, rather than proving production-path coverage (gate-logs/C5-prod-path.log:10). I checked that coverage directly: the test launches the production script through subprocess, rather than importing or copying its judgment implementation (target/tests/test_stack_mode_live_tool.py:169). Instance-scoped gate wrappers were adjudicated through their captured logs and the underlying checks available here.

Prior art was checked by all four affected file paths using the upstream main commit-history API and closed-PR searches, including merged and unmerged results. Neither new tool/test path returned history or matching closed PRs; the documentation paths returned existing policy/test-infrastructure work, including merged PR #390 establishing STOP discipline. Results are preserved in reviewer-prior-art.log:1 and reviewer-prior-art.log:13. The local target itself contains only the harness's single base commit, so that local history alone would not have established prior art.

For the live sign-off, from the reviewed repository root, choose a fresh directory and run the documented sequence with the assigned sandbox token:

```bash
W="$PWD/stack-mode-live-signoff-$(date -u +%Y%m%d-%H%M%S)"
python3 tools/live/stack_mode_live.py preflight --repo eduralph/pdca-stack-sandbox
python3 tools/live/stack_mode_live.py setup --workdir "$W" --repo eduralph/pdca-stack-sandbox
python3 tools/live/stack_mode_live.py run --workdir "$W" --repo eduralph/pdca-stack-sandbox
python3 tools/live/stack_mode_live.py judge --workdir "$W"
python3 tools/live/stack_mode_live.py teardown --workdir "$W" --repo eduralph/pdca-stack-sandbox
```

The default token file is `~/.config/pdca/sandbox-gh-token`; use `--token-file` on the remote subcommands if needed. Confirm that report.md contains E0, E1, E1b, E2, E3, E4 and E5 with complete observations. An INCOMPLETE run requires correcting its cause and rerunning in a fresh directory; file each complete FAIL as its own bug. Attach report.md to the bundle and post it on #625, explicitly recording the accepted persistent-sandbox departure from the original disposable-repository wording (brief.md:12). This review did not perform the human-started live writes.

<!-- pdca:leaf-complete -->
