Review the reusable stack-mode GitHub scenario tool for #625, including its offline judge and revised handling of incomplete observations.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The offline judge criteria and live sign-off obligation are explicit and separable; the seven named checks cover the stated scenario (`target/tests/test_stack_mode_live_tool.py:138`, `target/CONTRIBUTING.md:72`; brief.md, Success criterion). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing production while retaining the test executes 12 tests and produces 14 assertion failures because the tool is absent; this establishes the enhancement's pre-fix absence (`review-red.log:294`, `target/tests/test_stack_mode_live_tool.py:110`). |
| C3 Change | PASS | The three changed paths stay within the proposed repository-root tool, test and documentation scope; no driver source or rendered-instance behavior changes (`patch.diff:1`, `patch.diff:59`, `patch.diff:314`, `target/tools/live/stack_mode_live.py:53`). |
| C4 Verification (red→green) | PASS | The binding offline criterion independently goes red with production stashed and green after restoration: 12 subprocess tests pass; the frozen C4 log agrees (`review-red.log:294`, `review-green.log:15`, `gate-logs/C4-verify.log:298`, `target/tests/test_stack_mode_live_tool.py:110`). |
| C5 Causal adequacy | PASS | The earlier false-PASS cases now require recorded PRs, successful run outcomes and confirmed deletion; unknown ancestry stays unknown, with a real-git helper replay confirming exit 0/1/128 → True/False/None (`target/tools/live/stack_mode_live.py:206`, `target/tools/live/stack_mode_live.py:344`, `target/tools/live/stack_mode_live.py:565`, `target/tools/live/stack_mode_live.py:615`; `review-ancestry.log:1`). |
| T1 Structure | PASS | Recording and offline judgment have separate entry points; the scenario uses the real flow/publisher with the two model-leaf substitutions the brief allows, without importing a test fixture (`target/tools/live/stack_mode_live.py:175`, `target/tools/live/stack_mode_live.py:274`, `target/tools/live/stack_mode_live.py:545`). |
| T2 Shape | PASS | Independently rerun documentation lint and site render/link audit pass, producing 22 pages; both frozen shape logs show the same substantive checks, and git diff --check is clean (`gate-logs/T2-docs.log:10`, `gate-logs/host-ci-docs.log:10`, `target/CONTRIBUTING.md:39`). |
| T3 Runtime | PASS | Independent driver replay passes 2,630 tests with two skips; frozen evidence also shows 36 root tests passing. Reviewer render replay exits 77 for missing importable Copier, so root-render coverage rests on the frozen log (`review-driver-suite.log:1819`, `gate-logs/T3-suite.log:66`, `review-root-render.log:6`). |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the deferred row explicitly owes the substantive audit to publish (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Approve maintaining a reusable four-command tool for an issue requesting one recorded run, and settle prior-art equivalence beyond keyword-indexed closed-work searches — scope and duplication affect the maintenance commitment (`target/tools/live/stack_mode_live.py:720`, `target/CONTRIBUTING.md:39`; brief.md, Open questions). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Complete the real GitHub run and attach/post its report before sign-off — authenticated repo creation/deletion, real PR topology and host JSON behavior were not exercised; available verification uses curated offline observations (`target/tests/test_stack_mode_live_tool.py:73`, `target/CONTRIBUTING.md:51`, `target/CONTRIBUTING.md:57`; brief.md, External dependencies and Success criterion). |

The target is a readable, self-contained base snapshot with the patch applied. After the stash/pop replay, both added source files match patch.diff exactly; no source fix was made. C4 demonstrates the offline judge contract. It supplies no observation of setup, live publishing/merging or teardown. The production-path scanner's frozen log explicitly excludes the new root-suite test (`gate-logs/C5-prod-path.log:10`); its PASS is not evidence of live driver coverage. The test itself invokes the actual tool by subprocess. The C5 capability-probe smell-test found no optional-capability probe masking an eager/load-time cause.

Independent commands executed: `python3 -m unittest tests.test_stack_mode_live_tool -v` before stashing and after restoration; the same command with only production/docs stashed for red; `python3 docs/publishing/tools/lint_docs.py`; `python3 docs/publishing/tools/render_site.py --check --out ../review-site`; and, from template/, `PYTHONPATH=src python3 -m unittest discover -s tests`. Temporary files were directed inside this review workspace. The selected root render/update replay explicitly reported missing importable Copier and exit 77 (`review-root-render.log:6`); the frozen log shows those cases actually executed and passed (`gate-logs/T3-suite.log:38`, `gate-logs/T3-suite.log:55`). This is a reviewer-host limitation, not a patch failure or an additional unresolved gate.

Prior-art investigation ran by all three affected paths. GitHub commit-history queries returned no history for tools/live/stack_mode_live.py or tests/test_stack_mode_live_tool.py; CONTRIBUTING.md returned the Copier-verification and licensing changes (aefdb5484d7f and d6f478673931). Closed-work searches for each exact path returned zero tool/test matches and four CONTRIBUTING.md matches: #525, #68, #439 and #424, concerning Copier, licensing, verification and leaf scratch discipline. Their descriptions do not establish an equivalent live-stack tool. The local target has only its synthetic base commit, and GitHub issue/PR text search does not exhaust unmentioned closed/rejected PR diffs; that remaining semantic prior-art decision is included in T5. [Issue #625](https://github.com/eduralph/pdca-harness/issues/625) remains open and asks for the actual host observations.

For human Validation, use a fresh work directory and an authenticated gh account with repo and delete_repo permissions. From the patched repository root, run:

```bash
W="$PWD/../live-stack-625-validation"
python3 tools/live/stack_mode_live.py setup --workdir "$W"
python3 tools/live/stack_mode_live.py run --workdir "$W"
python3 tools/live/stack_mode_live.py judge --workdir "$W"
python3 tools/live/stack_mode_live.py teardown --workdir "$W"
```

Inspect observations.json and report.md for all seven PRs and E0/E1/E1b/E2/E3/E4/E5, particularly confirmed branch deletion, run 2's rc/holds/D result, and a known squash head's ancestry. Attach report.md to the bundle and post it on #625. Per the brief, an INCOMPLETE run must be repaired and rerun before sign-off; FAIL rows from a completed run become separate bugs and do not themselves prevent accepting the tool.

The live commands were not executed here: the scenario marks drafts ready and merges PRs (`target/tools/live/stack_mode_live.py:328`), while the applicable [AGENTS.md](target/AGENTS.md) expressly says “Never merge a pull request” and “Never mark a draft pull request ready” (`target/AGENTS.md:13`, `target/AGENTS.md:15`). The brief expressly assigns this live run to the human at sign-off.

<!-- pdca:leaf-complete -->
