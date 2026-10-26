Review issue #625: add a guarded tool that exercises stack mode on real GitHub and judges the recorded observations offline.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The offline outcomes, live sign-off condition, scope limits and iteration-6 settling correction are explicit and distinguish an observed mismatch from unavailable evidence (brief.md:13; brief.md:21; brief.md:56; brief.md:111). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing the production additions while retaining the test produced 46 assertion failures across 22 tests, exit 1; the subprocess actually ran against the absent tool (tests/test_stack_mode_live_tool.py:189; review-red.log:1). |
| C3 Change | NEEDS-HUMAN | Separately accept the STOP-policy exception for human-started tool merges and ready-marks — this changes governance and requires its own sign-off despite the implementation staying within the four authorized files (AGENTS.md:14; CONTRIBUTING.md:91; brief.md:13). |
| C4 Verification (red→green) | PASS | The binding offline criterion reproduced red→green: after restoring the identical patch, all 22 tests passed, exit 0; this establishes offline behavior only (tests/test_stack_mode_live_tool.py:220; review-green.log:3; gate-logs/C4-verify.log:10). |
| C5 Causal adequacy | NEEDS-HUMAN [impl] | Treat fresh, matching empty PR-file lists as observed mismatches — E1/E1b currently return INCOMPLETE/exit 3 instead of FAIL/exit 1, preventing a fully observed discrepancy from being filed as a bug (tools/live/stack_mode_live.py:1062; tools/live/stack_mode_live.py:1229; review-empty-lists.json:3). |
| T1 Structure | PASS | The tool remains outside the rendered template, uses the checkout's actual driver, and replaces only the two intended model leaves; no driver-source change or additional dependency is introduced (copier.yml:13; tools/live/stack_mode_live.py:280; tools/live/stack_mode_live.py:585). |
| T2 Shape | PASS | Independently reran docs lint and site rendering/internal-link audit: both clean, 22 pages rendered; tracked diff whitespace check also passed (gate-logs/T2-docs.log:10; gate-logs/host-ci-docs.log:10). |
| T3 Runtime | PASS | Independent driver rerun passed 2,630 tests with two skips; local root runner exited 77 for missing importable copier, while the frozen full gate explicitly records 46 root tests passing and 2,630 driver tests passing (review-driver-suite.log:1819; review-root-suite.log:6; gate-logs/T3-suite.log:76; gate-logs/T3-suite.log:1898). |
| T4 Contribution | N/A | Contribution artifacts are intentionally not drafted at Check; the frozen row is deferred and explicitly assigns the substantive audit to the mandatory publish rerun (gate-logs/T4-contribution.log:10). |
| T5 Judgment | NEEDS-HUMAN | Confirm path-based prior-art coverage of merged and closed/rejected work for all four affected files — the supplied history has one synthetic commit, and the brief's keyword search plus history of merged.py does not establish that coverage (review-prior-art.log:1; review-prior-art.log:13; brief.md:25). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Complete the authenticated sandbox run and attach its report — real token permissions, draft PR support and update-branch behavior were not exercised by these fake-gh/curated-observation tests, so their green result cannot close #625 (brief.md:13; brief.md:22; CONTRIBUTING.md:60; tests/test_stack_mode_live_tool.py:550). |

Source citations without a `target/` prefix resolve inside `$PDCA_TARGET` (`target/` in this sandbox); brief, gate-log and review-evidence citations resolve in the review cwd. The supplied target is readable and matches patch.diff: both new files match byte-for-byte and the tracked AGENTS.md/CONTRIBUTING.md diff matches. The production stash was restored. No implementation changes were made.

**F1 — observed empty file lists are misclassified (C5, builder-fixable).** At tools/live/stack_mode_live.py:1062, `not rd["files"]` conflates an observed empty list with an absent list. Two identical empty reads with the expected head/base or recomputed test-merge parents satisfy the freshness and agreement requirements, yet `settled_files` calls them missing evidence. An empty list disagrees with both checks' required one-file lists. This matters because INCOMPLETE requires repeating the live run and blocks sign-off, whereas FAIL is a complete observation to file as its own bug (CONTRIBUTING.md:79).

I reproduced this independently through the production CLI: start with the passing `_good()` observation document, replace every read's `files` in either `B_files_after_update` or `Q_files_after_P_merge` with `[]`, and preserve the commit identities, mergeability, parents, merge confirmations and `synced: true`. Both invocations exited 3 and classified the affected check INCOMPLETE. Full inputs and reports remain in `review-scratch/empty-E1/` and `review-scratch/empty-E1b/`; the extracted results are in `review-empty-lists.json`. Reproduce from the review cwd with:

```bash
python3 target/tools/live/stack_mode_live.py judge --workdir review-scratch/empty-E1
python3 target/tools/live/stack_mode_live.py judge --workdir review-scratch/empty-E1b
```

Accept an empty list as an observed list while retaining the existing commit/freshness checks, and add regression cases expecting the affected check FAIL and exit 1. Missing/non-list data must remain INCOMPLETE. The capability-probe smell-test found no load-time capability workaround related to the task; F1 concerns observation classification.

The iteration-6 positive and stale-data cases do pass: an unchanged PR base with fresh mergeability/test-merge parents can yield E1b FAIL for lingering P files, and stale parents, moved heads, missing mergeability and unsynced reads remain INCOMPLETE (tests/test_stack_mode_live_tool.py:276; tests/test_stack_mode_live_tool.py:355). The production-path scanner itself skipped this root-suite test as out of scope; its log is not evidence of production execution (gate-logs/C5-prod-path.log:10). The test's actual subprocess calls and the independent rerun supply that evidence.

The root-suite rerun's missing copier library is a local host limitation, not a patch defect. The frozen T3 log records substantive render/update coverage and a clean full-suite outcome. All six named gate logs were readable; no missing-oracle escalation is warranted. The only supplied INTEGRATION.md §4 is the rendered-template placeholder, whose human-only list is still TODO (template/docs/INTEGRATION.md.jinja:80); the brief explicitly supplies the live-run and policy sign-off obligations here.

For live validation, a human must run the following from a checkout containing this patch, with the assigned token file and private sandbox available. AGENTS.md:15 limits the merge exception to a tool “started by a human”; brief.md:13 assigns this run to sign-off, so this advisory review did not start remote mutations.

```bash
W="$PWD/live-check-625"
python3 tools/live/stack_mode_live.py preflight
python3 tools/live/stack_mode_live.py setup --workdir "$W"
python3 tools/live/stack_mode_live.py run --workdir "$W"
python3 tools/live/stack_mode_live.py judge --workdir "$W"
python3 tools/live/stack_mode_live.py teardown --workdir "$W"
```

Use a fresh work directory. If setup fails, follow its printed teardown command. Inspect all seven report rows E0/E1/E1b/E2/E3/E4/E5: no INCOMPLETE may remain; attach report.md to the bundle and post it on #625, filing every observed FAIL as its own bug. The earlier live-run account in the brief is evidence motivating this revision, not a completed live validation of this patch. Separately accept the policy wording and complete the affected-path prior-art audit; the latter was attempted locally and returned only the synthetic base history recorded in review-prior-art.log.

<!-- pdca:leaf-complete -->
