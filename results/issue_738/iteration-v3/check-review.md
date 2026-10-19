Review whether a failure building one bundle's own base holds that bundle and affected successors while unrelated work continues, with accurate recovery guidance and exit codes (#738).

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The seven real-git scenarios distinguish isolated holds, skipped dependents, stale PRs, and exit 3 versus 1; the later line-fold failure is explicitly excluded (brief.md:3, brief.md:16; template/tests/test_flow_bundle_base_holds.py:340). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing the three production changes reproduced STOPPING: all 15 new cases and four updated assertions failed, with clean imports (review-red.log:72, review-red.log:315). |
| C3 Change | PASS | The six affected files stay within base-failure isolation, recovery messages, exit classification, and regression coverage; the hold is collected at the failing base operation (template/src/pdca_harness/flow.py:1040; template/src/pdca_harness/cli.py:742). |
| C4 Verification (red→green) | PASS | Restoring the production stash changed the same 55 tests from 19 assertion failures to all passing; this confirms the asserted regression evidence, while C5 records a separate uncovered defect (review-red.log:317; review-green.log:58). |
| C5 Causal adequacy | NEEDS-HUMAN [impl] | Fix the omitted stale-PR warning after successive rewrites — a real-git probe leaves S holding h1 absent from A without naming S, so recovery guidance misses an affected PR (template/src/pdca_harness/flow.py:1119, template/src/pdca_harness/flow.py:3056; review-probe.log:4). |
| T1 Structure | PASS | Failure isolation stays in the flow coordinator, git diagnosis stays in integrate, and the CLI retains the centralized exit rule; existing real-git fixtures provide coverage (template/src/pdca_harness/flow.py:2891; template/src/pdca_harness/integrate.py:860; template/src/pdca_harness/cli.py:742). |
| T2 Shape | PASS | Independently reran docs lint, site render with internal-link audit (22 pages), and git diff --check; all passed, consistent with both frozen shape logs (gate-logs/T2-docs.log:16; gate-logs/host-ci-docs.log:15). |
| T3 Runtime | PASS | Independent offline driver run passed 2,609 tests with two skips; frozen root evidence additionally shows 24 passing render/update tests (review-driver-suite.log:1817; gate-logs/T3-suite.log:54). |
| T4 Contribution | N/A | Contribution artifacts are drafted after Check; the substantive contribution audit must rerun at publish, as the deferred gate explicitly records (gate-logs/T4-contribution.log:10). |
| T5 Judgment | NEEDS-HUMAN | Confirm merged and closed/rejected prior art by each affected file path — the supplied target has one synthetic commit and no remote, so the brief's commit references cannot establish that search (review-prior-art.log:1; brief.md:22). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the hold/skip exit policy and recovery guidance fit batch operations, with later line-fold failures left to #739 — automated git scenarios support behavior but cannot grant operational acceptance (brief.md:11; template/tests/test_flow_bundle_base_holds.py:15). |

All production and test source citations above are grounded in the patched `$PDCA_TARGET` (`target/`), whose single base commit identifies the expected verification base `75a886e9370d7b51567c9f6803d827c66a4fac48`. No stale-target caveat applies. The original production changes were restored after the red leg; no source was patched by this review.

**Implementation finding: an additional rewrite can hide another affected PR.** At `template/src/pdca_harness/flow.py:1119` and `:1121`, the final check selects only heads already lost when the base was refused. The ordinary late-rewrite check then excludes that member at `:3056`. Re-reading its branch therefore cannot discover losses of heads that were still present at the refusal.

The independent probe uses the existing `DependencyScopedBases` real-git fixture and production `flow._drive_and_act`:

1. Wave 0 publishes A at h1 and Z. After its fold, A fast-forwards to h2.
2. Wave 1 publishes B (`Depends on: A`) on h2, S (`Stacks on: A`) on the earlier line holding h1, and W (`Depends on: Z`). The next fold takes h2.
3. After that fold, A is reset to h1. In wave 2, D (`Depends on: B`) is held because A lost h2. Its hold correctly names B; S still holds a valid h1 at that instant.
4. While unrelated V (`Depends on: W`) builds, A is force-pushed again to a branch containing neither h1 nor h2. At run end S is now stale, but no stderr line names it.

Observed: S contains h1, current A does not contain h1, and `S named in stderr: False` (`review-probe.log:4`, `:6`, `:8`). The run correctly exits 1 and names B; the defect is the missing S warning and corresponding recovery guidance. This window is the same long-running-wave window that motivated the previous iteration's restored-branch recheck.

Reproduce from this review directory:

```sh
TMPDIR="$PWD/review-tmp" PYTHONDONTWRITEBYTECODE=1 python3 review-probe.py
```

The assertion fails on the applied patch (`review-probe.log:17`). Recheck every head of the refused member held by a published PR at run end, including heads still present at the refusal, and add this sequence as a regression alongside the restored-branch case at `template/tests/test_flow_bundle_base_holds.py:484`.

**Evidence limits and gate accounting.** The C4 rerun kept all tests in place, stashed only `cli.py`, `flow.py`, and `integrate.py`, then popped that stash before the green run. Logs are `review-red.log` and `review-green.log`. The full driver run is `review-driver-suite.log`. Instance-scoped gate wrappers are outside the supplied artifact target; their absence is expected. The frozen production-path scanner log establishes only that the new driver test imports `pdca_harness` (`gate-logs/C5-prod-path.log:10`); the independent red→green run and probe additionally exercise production behavior. Copier is unavailable in this review interpreter, so root render/update tests were adjudicated from the frozen log, which shows their actual execution and success (`gate-logs/T3-suite.log:38`, `:54`). This is a local rerun limitation, not an unmet dependency in the recorded gate run. The brief declares no external dependency, and real git reproduced the forbidden STOPPING behavior without a tool alias or substitute topology. No added capability-probe/load-time symptom guard was found.

The prior-art investigation ran `git log HEAD -- <all six affected paths>`, `git remote -v`, and `git show-ref`; it found only the synthetic base and local master ref (`review-prior-art.log:1`). Neither merged history nor a closed/rejected-work archive was available. The supplied integration document is the uninstantiated template, whose human-only list remains TODO (`template/docs/INTEGRATION.md.jinja:80`); no additional instantiated project checklist was supplied.

<!-- pdca:leaf-complete -->
