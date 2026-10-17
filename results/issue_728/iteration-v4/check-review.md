Review carried prerequisite bases and patchless resume traversal so each dependent receives its declared prerequisite work without unrelated carried work or false stops.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The separation, patchless traversal, foreign-ancestry refusal, and rewrite criteria are independently falsifiable with real git; the tests assert branch contents and completion (`template/tests/test_flow_carried_prereq_bases.py:267`, `:290`, `:386`, `:702`, `:743`; `brief.md:3`). |
| C2 Reproduction (red pre-fix) | PASS | Stashing only the two production files left all four test modules runnable: 82 tests ran, 37 assertion failures reproduced the missing behavior, with no import errors (`review-red.log:709`; `template/tests/test_flow_carried_prereq_bases.py:267`). |
| C3 Change | NEEDS-HUMAN | Ratify the expanded ownership contract and additional existing-test restatements against the bounded plan—`build_bundle_base` changes outside the named allowed functions, and the dependency-scoped tests are outside the original restatement list (`brief.md:10`, `:16`; `template/src/pdca_harness/integrate.py:738`, `:871`; `template/tests/test_flow_dependency_scoped_bases.py:375`, `:390`). |
| C4 Verification (red→green) | PASS | Restoring the production fix made all 82 focused tests pass, independently matching the frozen gate's red→green evidence; this verifies the supplied cases, while R1 below exposes a further failure (`review-green.log:3`; `gate-logs/C4-verify.log:13`; `template/tests/test_flow_carried_prereq_bases.py:645`). |
| C5 Causal adequacy | NEEDS-HUMAN [impl] | Fix shared late-merge handling before treating the carry race as covered—two dependents of the same newly merged prerequisite stop the whole wave, including unrelated work; the base completes all three (R1; `template/src/pdca_harness/flow.py:1023`, `:1064`; `review-probe-patched.log:2`, `review-probe-base.log:2`). |
| T1 Structure | PASS | Closure selection, carry eligibility, and git ownership remain separated into helpers, and the merged-prerequisite runnable branch is unchanged (`template/src/pdca_harness/flow.py:913`, `:1043`, `:1432`; `template/src/pdca_harness/integrate.py:992`). |
| T2 Shape | PASS | Independently re-ran docs lint, rendered 22 pages with the internal-link audit, and checked diff whitespace; all passed, consistent with both frozen docs checks (`gate-logs/T2-docs.log:11`, `gate-logs/host-ci-docs.log:11`; `.github/workflows/docs-check.yml:36`). |
| T3 Runtime | PASS | Independently ran the offline suite: 2,602 tests passed with two skips; Copier-backed rendering also passed locally, while release-update coverage relies on the frozen log because this copy has no release tags (`review-runtime.log:1817`; `review-root-with-copier.log:5`; `gate-logs/T3-suite.log:44`; `tests/test_update_compat.py:243`). |
| T4 Contribution | N/A | Contribution artifacts are absent by design; the substantive audit is deferred to its mandatory publish-time rerun, not awaiting human clearance (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Confirm prior-art review by every affected file path across merged history and closed/rejected work—the path-scoped investigation found only the synthetic base commit, no remotes, and no closed-work evidence, so the brief's issue references do not establish that review (`review-prior-art.log:1`; `brief.md:21`; `template/src/pdca_harness/flow.py:913`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | After R1 is corrected, accept whether inherited work vouched for by a prior own-base record meets the intended closure policy, including prerequisites omitted from the reissued batch—this determines which historical work a dependent may ship (`template/src/pdca_harness/flow.py:1084`, `:1125`; `template/tests/test_flow_carried_prereq_bases.py:622`). |

All repository-source citations above and below refer to `$PDCA_TARGET` (`target/`); brief, gate-log, and reviewer-evidence citations refer to this sandbox. The six patched files' git object hashes still match `patch.diff` after the stash/pop verification. No target-state mismatch was found.

**R1 — A second dependent of a prerequisite merged after carry stops the entire wave.**

Reproduced with the supplied real-git fixture, without modifying the patch. Run `[P, D, E, U]`, where both D and E declare `Depends on: P`, U is unrelated, and D/E/U fail on the first run. Reissue driving D/E/U, squash-merge P into main and delete `fix/P` immediately after the carry fold. The fixture confirms P's merge commit is on main. With the patch, D/E/U all remain PLANNED and none reaches the driver; the error names E's missing P branch and prints STOPPING. With both production modules loaded from the disposable target's pre-fix commit, all three are COMPLETE (`review-probe-patched.log:2`, `:4`, `:6`; `review-probe-base.log:2`).

The plans for the entire wave are computed before any base is built (`template/src/pdca_harness/flow.py:1014`). D's failed build recognizes P as newly merged, updates the shared `on_base`, and removes P from D's local member list (`:1064`–`:1069`). E's already-computed plan still contains P (`:1023`). E's build fails too, but the recovery explicitly excludes P because it is already in `on_base` (`:1065`), so it raises instead of removing the obsolete member. Since all bases precede driving, U is stopped as well. The supplied late-merge regression test has only one dependent and cannot reveal this shared-state interaction (`template/tests/test_flow_carried_prereq_bases.py:645`).

Reconcile each dependent's members with the current `on_base` before building, or refresh affected plans when that set grows, and add this two-dependent case to the production-driving suite. This is an implementation correction; no policy decision or external service is needed to reproduce it.

From the sandbox root, reproduce both results with:

```bash
TMPDIR="$PWD/review-tmp" PYTHONDONTWRITEBYTECODE=1 python3 review-late-merge.py patched
TMPDIR="$PWD/review-tmp" PYTHONDONTWRITEBYTECODE=1 python3 review-late-merge.py base
```

The probe's `base` mode reads the two production modules with `git show HEAD:<path>` and executes those snapshots in its own process; it does not alter the target tree. Both modes use identical real-git topology and the supplied PR-state stub.

**Evidence limits and remaining decisions.** The production-import scanner's frozen log reports one added driver-suite module importing `pdca_harness` (`gate-logs/C5-prod-path.log:10`); independent AST inspection confirms that import and the direct `flow._drive_and_act` call (`template/tests/test_flow_carried_prereq_bases.py:45`, `:177`). No capability probe masking an eager/load-time side effect was introduced. The standard-library/git dependencies specified in the brief were exercised. PR hosting, building, sign-off, and publishing are stubbed as the brief's fixture requires; these runs establish the driver/git behavior, not live-host fitness.

The default interpreter could not import Copier; using the already-installed Copier virtualenv successfully exercised rendering. Prior-release update tests still skip locally because the disposable repository has only one synthetic base commit and no release tags (`tests/test_update_compat.py:243`); the frozen gate log explicitly shows those five tests executing successfully (`gate-logs/T3-suite.log:42`). This is a local evidence limit, not a patch failure or an unmet dependency in the frozen verification. Instance-scoped gate wrappers are absent here; their full captured logs were used alongside the independent commands above, without treating wrapper absence as a defect. The template's integration guide does not enumerate additional project-specific human-only items (`template/docs/INTEGRATION.md.jinja:80`). Builder notes were not consulted.

<!-- pdca:leaf-complete -->
