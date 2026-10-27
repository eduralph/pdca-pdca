Review #727: give in-batch stack-mode bundles dependency-scoped bases and report rewritten prerequisite heads against each affected base and PR.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The required isolation, seam fallback, rewrite remedies, and exclusions are falsifiable and bounded (brief.md:4, brief.md:9, brief.md:18). |
| C2 Reproduction (red pre-fix) | PASS | With only the two production files stashed, the unchanged new suite runs 19 tests and fails 15, including B carrying unrelated Z (review-red.log:43, review-red.log:288; template/tests/test_flow_dependency_scoped_bases.py:256). |
| C3 Change | PASS | Source changes stay within base selection and rewrite accounting; `_line_lacks_merge` is AST-identical to the base, and the merged-prerequisite suite changes only its permitted helper (template/src/pdca_harness/flow.py:850; template/tests/test_flow_merged_prereq_on_line.py:191). |
| C4 Verification (red→green) | PASS | After stash-pop, all 2,575 driver tests pass, including the 19-test suite that failed pre-fix; the separate 58-test targeted run also passes (review-red.log:290; review-driver-suite.log:1817; target/review-green.log:3). |
| C5 Causal adequacy | NEEDS-HUMAN [impl] | Preserve the declared closure through a completed patchless prerequisite — N conflicts with A and H depends on N, yet H drops A although N was built on A; all four bundles become COMPLETE, violating the accepted-work invariant (template/src/pdca_harness/flow.py:953, template/src/pdca_harness/flow.py:964; brief.md:18; review-patchless-conflict.log:1). |
| T1 Structure | PASS | Base construction reuses the existing integration lock, fetched worktree, and merge validation; head ownership has a shared representation across both rewrite checks (template/src/pdca_harness/integrate.py:818, template/src/pdca_harness/integrate.py:1040). |
| T2 Shape | PASS | Independent docs lint and rendering audit pass for all 22 pages, and `git diff --check` passes; frozen host-parity evidence agrees (review-docs.log:1; gate-logs/host-ci-docs.log:10). |
| T3 Runtime | PASS | Independent driver run passes 2,575 tests with two skips; frozen root evidence shows all 24 render/update tests passed, while this interpreter cannot import copier (review-driver-suite.log:1817; gate-logs/T3-suite.log:39; review-root-suite.log:6). |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the deferred row explicitly requires the substantive audit at publish (gate-logs/T4-contribution.log:10). |
| T5 Judgment | NEEDS-HUMAN | Confirm prior art by both affected production paths against merged history and closed/rejected work — the disposable repository exposes only one synthetic base commit, and the cited #724 rejection artifacts are outside this input bundle (template/src/pdca_harness/flow.py:913; template/src/pdca_harness/integrate.py:724; brief.md:24). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the scoped isolation and retained line-based seam behavior satisfy the intended workflow, and honor the prerequisite merge order (#726 first) — green offline checks do not settle that product acceptance (brief.md:9, brief.md:13; template/src/pdca_harness/flow.py:1014). |

All source citations above resolve within `$PDCA_TARGET` (`target/`). The supplied patch reverse-checks cleanly against that tree; there is no target-state mismatch. The production stash was popped successfully, and no reviewed source was edited.

The C5 finding is independently exercised through real git and production `flow._drive_and_act`, using the brief's prescribed fixture and build/publish stubs. A and unrelated Z publish first; N declares `Conflicts with: A` and completes without a patch; H declares `Depends on: N`. The observed result is `A=N=H=Z=COMPLETE`, A is an ancestor of N's recorded base, and A is not an ancestor of `fix/H` (`review-patchless-conflict.log:1`). N is completed in this run, so neither the discontinued-node exclusion nor the resumed-patchless seam applies. At `flow.py:964`, visiting N with `every=False` removes its conflict edges at `flow.py:953`. The existing transparent-patchless test covers only `Depends on` (`template/tests/test_flow_dependency_scoped_bases.py:284`); add the conflict-edge counterpart while retaining the empty-closure and discontinued-node cases.

Reproduce from this review directory:

```bash
TMPDIR="$PWD/review-tmp" PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=target/template/src:target/template \
  python3 review-patchless-conflict.py
```

The earlier iteration's concrete concerns have regression coverage now: the original undeclared-overlap topology remains separate from its declared-edge variant (`template/tests/test_flow_reissue_after_conflict_hold.py:245`); older line-cut heads and a later base detecting a rewrite have production-flow tests (`template/tests/test_flow_dependency_scoped_bases.py:536`, `template/tests/test_flow_dependency_scoped_bases.py:492`). Removing the conflict-wave guard in memory makes its new regression fail on unwanted E commits, confirming that test detects the previously untested condition (`review-guard-mutation.log`; `template/tests/test_flow_dependency_scoped_bases.py:307`). This mutation did not alter source files.

All six frozen gate logs were inspected. The instance-scoped wrappers are not present here; their absence is expected. The production-import scanner's captured output establishes an import of `pdca_harness`, not causal sufficiency (`gate-logs/C5-prod-path.log:10`); the real-git reruns supply the latter evidence and expose the C5 gap. Local root-suite execution returns 77 because copier is not importable; this is a reviewer-host limitation, not a patch failure or an undischarged gate dependency: the frozen root log explicitly records successful render and update cases (`gate-logs/T3-suite.log:39`, `gate-logs/T3-suite.log:54`). No extra project human-only items are enumerated in the available integration template (`template/docs/INTEGRATION.md.jinja:80`).

Prior-art investigation ran `git log --all -- template/src/pdca_harness/flow.py template/src/pdca_harness/integrate.py`; its sole result was `ad488e2 pre-fix base fcae4aaee0233103ea0dac73c66c8811c713850c`. The brief summarizes prior rejected approaches, but does not supply their actual corpus. That limitation remains a human judgment under T5.

<!-- pdca:leaf-complete -->
