Review issue #694: make re-issued batches name conflicting finished partners and give actionable rebuild advice instead of telling operators to reopen an already-open PR.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The required partner, base-conflict, and unchanged carry outcomes are falsifiable with real Git; brief.md:10 and brief.md:23, grounded by target/template/tests/test_flow_reissue_after_conflict_hold.py:150. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only the two production files produced 18 assertion failures, including the original misleading reopen advice; review-red.log:1 and target/template/tests/test_flow_reissue_after_conflict_hold.py:186. |
| C3 Change | PASS | The four changed files address carry diagnosis, shared remedy wording, regression coverage, and operator documentation within the requested surface; target/template/src/pdca_harness/flow.py:1179 and target/docs/07-crosscutting.md:767. |
| C4 Verification (red→green) | PASS | Restoring the production fix made all 18 shipped regression tests pass; this verifies their asserted cases, with the additional coverage defect recorded under C5; review-green.log:1 and gate-logs/C4-verify.log:10. |
| C5 Causal adequacy | NEEDS-HUMAN [impl] | Preserve attribution of a stacked partner's independent conflicting edit when an inherited deletion prevents the attribution trial from reaching it — otherwise the proposed declaration and rebuild base omit a real carried partner; target/template/src/pdca_harness/integrate.py:1227 and review-edge-case.log:2. |
| T1 Structure | PASS | Diagnosis stays within the locked fold and existing trial-merge restoration boundary, with wording handled by flow; target/template/src/pdca_harness/integrate.py:635 and target/template/src/pdca_harness/integrate.py:1294. |
| T2 Shape | PASS | Independent docs lint, 22-page render/link audit, production-import scanner, and diff whitespace check passed; review-docs.log:2, gate-logs/T2-docs.log:11, and gate-logs/host-ci-docs.log:11. |
| T3 Runtime | PASS | Independent driver suite passed 2,509 tests with two skips; local root rerun lacked copier, while frozen evidence shows all 24 root tests passed on the gate host; review-suite.log:1817 and gate-logs/T3-suite.log:54. |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the substantive contribution audit must rerun at publish; gate-logs/T4-contribution.log:10. |
| T5 Judgment | NEEDS-HUMAN | Confirm the affected-path merged-history and closed/rejected-work prior-art conclusion before accepting novelty — the brief records a search, but this artifact-only target has one synthetic commit and no remote history to substantiate it; brief.md:28 and review-prior-art.log:1. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the proposed declarations and rebuild instructions are sufficiently complete and actionable for operators after C5 is resolved — passing automated scenarios cannot approve the operational remedy; target/template/src/pdca_harness/flow.py:1017 and target/docs/07-crosscutting.md:767. |

The C5 finding is independently reproduced, not inferred from a failed environment check. Starting with `a.txt = x` and `b.txt = x`, issue_10 deletes `a.txt`; issue_12, built on issue_10, changes `b.txt` to `twelve`; issue_11 changes both files to `eleven`. The carry reports both issue_10 and issue_12 as carried, but issue_11's advice names only issue_10 and proposes only `Conflicts with: 10`. Issue_12's own conflicting `b.txt` edit is visible in review-edge-case.log:3; the carried partners are recorded at review-edge-case.log:12.

At target/template/src/pdca_harness/integrate.py:1227, the attribution trial merges the inherited history, then issue_11 using `-X theirs`. That option cannot resolve the inherited modify/delete conflict in `a.txt`, so line 1229 skips issue_12 entirely before testing its independent `b.txt` change. The shipped deletion test at target/template/tests/test_flow_reissue_after_conflict_hold.py:366 checks only an unrelated stacked change and misses this combination. Retain that no-false-blame test and add this mixed case; attribution needs to preserve independent conflicting changes even when an inherited structural conflict prevents a whole-tree trial. The expected advice names issue_10 for `a.txt` and issue_12 for `b.txt` and proposes both ids.

Reproduce from this review directory:

```sh
TMPDIR="$PWD/review-tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/target/template/src" python3 review-edge-case.py
```

This runs the shipped fixture through actual Git merges and fails its final assertion on the patched tree. The fixture stubs PR state and publishing orchestration, but the forbidden conflict and missing attribution occur in real production flow/fold code; no substitute Git tool or topology incapable of the failure is used.

The disposable target was readable and current enough to execute the patch. After the independent red leg, both production files were restored, and the tracked diff plus new test were checked against patch.diff exactly. No implementation edits were made. The full driver suite passed; the root-suite rerun exited 77 because this interpreter cannot import copier (review-root-suite.log:6). That is a local host limitation, not a patch defect or an unmet dependency in the recorded gate run: gate-logs/T3-suite.log:54 records 24 root tests followed by OK. The instance-scoped wrappers are unavailable here; their frozen logs were read, and accessible underlying checks were rerun. The template's human-only integration list is an unfilled placeholder at target/template/docs/INTEGRATION.md.jinja:80, so no additional enumerated project item could be derived from it.

The prior-art search is recorded by affected production/documentation paths in brief.md:28, including closed-unmerged PRs. The local history investigation returned only the synthetic base commit and no remotes (review-prior-art.log:1); it cannot independently settle that conclusion. No other checkout was consulted.

<!-- pdca:leaf-complete -->
