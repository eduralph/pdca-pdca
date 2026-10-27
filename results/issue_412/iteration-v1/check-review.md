Review issue #412: add symmetric `Merges with` groups that wait and merge together in merge mode, hold dependents, and refuse unschedulable groups.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | NEEDS-HUMAN | Decide whether refusing chained pairs satisfies the motivating use cases or requires Plan re-entry for alternative A — the brief explicitly leaves this scope decision open (brief.md:51; target source: docs/03-plan.md:102). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing the tracked fix while retaining the added test reproduces 10 assertion failures in 11 tests, including premature ready/merge calls; imports succeed (review-red.log; template/tests/test_merge_group.py:201). |
| C3 Change | PASS | The optional field, scheduling refusals, group merge boundary, dependent holds, template, and docs address one declared feature; no unrelated production change found (template/src/pdca_harness/brief.py:227; template/src/pdca_harness/flow.py:3113; template/templates/brief.md.tpl:34). |
| C4 Verification (red→green) | PASS | Independently restored the stashed fix and reran the same 11 tests: all pass after 10 pre-fix assertion failures; this confirms the asserted regression coverage, with the additional missed case recorded under C5 (review-green.log; gate-logs/C4-verify.log:10; template/tests/test_merge_group.py:217). |
| C5 Causal adequacy | NEEDS-HUMAN [impl] | Cover and report groups whose members all finish in the final wave — the independent A/B case returns COMPLETE, rc 0, empty holds and empty stderr, omitting the promised instruction to merge together (template/src/pdca_harness/flow.py:3106; template/src/pdca_harness/flow.py:3192; docs/07-crosscutting.md:896; review-extra-cases.log:1). |
| T1 Structure | PASS | Parsing, graph policy, merge mechanics, and run-scoped holds remain in their existing modules; each member still uses the existing merge gates (template/src/pdca_harness/waves.py:174; template/src/pdca_harness/merge.py:164; template/src/pdca_harness/flow.py:2937). |
| T2 Shape | PASS | Independent docs lint, 22-page site render/link audit, and git diff whitespace check pass; frozen docs and host-CI logs corroborate the same commands (review-docs-lint.log:1; review-docs-render.log:1; gate-logs/host-ci-docs.log:10). |
| T3 Runtime | PASS | Independent driver discovery passes 2,641 tests with two skips; local root discovery skips three Copier suites because Copier is absent, but the frozen log shows actual render/update execution and all 24 root tests passing (review-driver-suite.log; review-root-suite.log; gate-logs/T3-suite.log:39; gate-logs/T3-suite.log:54). |
| T4 Contribution | N/A | Contribution artifacts are drafted after Check; the deferred gate explicitly requires the substantive contribution audit at publish (gate-logs/T4-contribution.log:10). |
| T5 Judgment | NEEDS-HUMAN | Confirm merged and closed/rejected prior art across the remaining affected paths — the brief records path-based checks only for brief.py, waves.py and merge.py; the supplied snapshot has one synthetic base commit and no remotes, preventing independent settlement for flow.py, cli.py, docs, template and tests (brief.md:22; review-prior-art.log:1). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Accept or reject best-effort grouping with a possible partially landed group after a later merge refusal, plus manual merging for final-wave groups — these limits determine whether the feature meets the operational need (docs/07-crosscutting.md:896; template/src/pdca_harness/merge.py:168; brief.md:47). |

Source citations are relative to `$PDCA_TARGET`; evidence paths are relative to this review directory. The target was readable, contained the applied patch, and was restored after the red leg. Production files were not edited. The instance-scoped gate wrappers are not supplied here; their complete frozen logs were inspected, and available underlying checks were rerun. The production-import scanner also passes independently against this patch (template/scripts/checks/test_exercises_production.py:71; template/tests/test_merge_group.py:38). The frozen Copier run exercised the required dependency, so its local absence is a rerun limitation rather than an undischarged dependency.

The C5 omission occurs because `held_group` is populated only through `merge_wave`, which is skipped for the final wave (template/src/pdca_harness/merge.py:158; template/src/pdca_harness/flow.py:3106). End-of-run reporting only visits that set (template/src/pdca_harness/flow.py:3228). When A declares `Merges with: B` and both are in the only wave, neither is registered, so the human receives no group-merge instruction. The existing final-wave test starts A in an earlier wave and therefore misses this case (template/tests/test_merge_group.py:265). Preserve the final-wave draft behavior while reporting these groups and adding regression coverage for this arrangement.

The independent reproduction is saved as `review-extra-cases.py`. From this review directory, run:

```sh
TMPDIR="$PWD/review-tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/target/template/src:$PWD/target/template" python3 review-extra-cases.py
```

Observed: both results COMPLETE, no merged PRs, `holds={}`, `rc=0`, `stderr=''`; the assertion requiring the group-merge notice fails. Additional probes passed: a connected three-member group merged consecutively, and an indirect dependency between group members was refused with exit 2 before any build (review-extra-cases.log:2; review-extra-cases.log:3).

This report is advisory; acceptance remains the human's decision.

<!-- pdca:leaf-complete -->
