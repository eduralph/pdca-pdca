Review issue #467: preserve a split parent's milestone and labels on every newly filed child, with best-effort metadata lookup.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The loss of release accounting has bounded, falsifiable criteria covering every child, lookup failures, and non-filing paths; the comma-label assumption is challenged below (brief.md:13; target/template/tests/test_split_child_metadata.py:110). |
| C2 Reproduction (red pre-fix) | PASS | Stashing only the production fix reproduced seven assertion failures in 11 tests, including missing metadata and warnings, with no import failures (review-red.log:1; target/template/tests/test_split_child_metadata.py:121). |
| C3 Change | FAIL | A parent label containing a comma can become multiple labels or prevent filing because raw names are passed to gh's CSV parser; repeated flags do not preserve such names (target/template/src/pdca_harness/split.py:1005; review-production-label.log:5). |
| C4 Verification (red→green) | PASS | The specified offline red→green is independently reproduced: seven failures before restoring the fix, all 11 tests green afterward; this establishes the mocked argv contract only (review-red.log:1; review-green.log:1; gate-logs/C4-verify.log:10). |
| C5 Causal adequacy | PASS | The change addresses missing metadata at the filing boundary; JSON/error handling protects an explicitly best-effort lookup, not an eager capability side effect, and the production-import scanner passes (target/template/src/pdca_harness/split.py:1040; target/template/src/pdca_harness/split.py:1098; gate-logs/C5-prod-path.log:10). |
| T1 Structure | PASS | The existing triage caller remains compatible through defaulted keyword arguments, and the partial/uncertain-filing handler retains its reporting responsibilities (target/template/src/pdca_harness/split.py:986; target/template/src/pdca_harness/triage.py:530; target/template/src/pdca_harness/split.py:1115). |
| T2 Shape | PASS | Independent whitespace, docs lint, and 22-page render/link checks pass; both frozen docs gates show the same successful checks (gate-logs/T2-docs.log:10; gate-logs/host-ci-docs.log:10). |
| T3 Runtime | PASS | The independent driver suite reports 1,799 tests with two skips; local root rerun exits 77 for unavailable Copier imports, while frozen evidence shows 24 root tests actually passed (review-driver.log:1103; review-root.log:6; gate-logs/T3-suite.log:54). |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the deferred substantive audit must rerun at publish (gate-logs/T4-contribution.log:10). |
| T5 Judgment | PASS | Scope remains one filing change plus sanctioned test-fake updates; path-based main history and all 233 closed PRs were checked, with nine matching PR diffs and no prior metadata-inheritance fix found (review-history.log:1; review-prior-art.log:1). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the release-accounting outcome is demonstrated after the label defect is corrected — actual GitHub child creation was not exercised, so the evidence rests on canned gh responses plus a real local flag-parser check, not persisted child metadata (brief.md:69; target/template/tests/test_split_child_metadata.py:82; review-production-label.log:1). |

## Finding

### P2 — Encode each label for gh's CSV parser

At `target/template/src/pdca_harness/split.py:1005`, a parent label such as `area,backend` is emitted verbatim as one `--label` argument. However, gh registers this flag as `StringSliceVarP`, whose parser reads **each occurrence** as CSV. Consequently that argument requests two labels, `area` and `backend`: if either does not exist, filing fails; if both exist, the child gets different labels from its parent. Repeating the flag does not change its value parser. This contradicts the comma-preservation requirement and the comment at `target/template/src/pdca_harness/split.py:996`. Sources: [gh v2.100.0 flag registration](https://github.com/cli/cli/blob/v2.100.0/pkg/cmd/issue/create/create.go#L174), [pflag CSV parsing](https://github.com/spf13/pflag/blob/v1.0.10/string_slice.go#L21).

I exercised the patched `_create_issue` with a captured subprocess call and fed its emitted label value to the installed gh 2.100.0 parser using `--help`, which performs no issue creation. The value `area, "quoted"` exits 1 with a CSV parsing error; encoding it as one CSV field exits 0. See `review-production-label.log:5` and `review-gh-label.log:1`. The plain-comma splitting conclusion follows from the upstream parser; `--help` alone does not display its parsed label list.

Encode each name as one CSV field, including CSV quote escaping, while retaining repeated `--label` flags. Add coverage for comma-containing names and check the downstream parsed names, alongside both returned child IDs. The current test only supplies `bug` and `help wanted` (`target/template/tests/test_split_child_metadata.py:113`), and its fake never parses flag values (`target/template/tests/test_split_child_metadata.py:90`), so the green suite cannot detect this defect.

## Independent checks and limits

- **Target grounding:** the disposable target has the expected production/test changes on its single pre-fix base. Production was stashed for the red run and restored for green; tests remained available in both legs. Source citations above refer to this target. No stale-target caveat arose.
- **Verification command:** from `target/template`, with `PYTHONPATH=src`, run `python3 -m unittest discover -s tests -p test_split_child_metadata.py`. Local red and green output is preserved in `review-red.log` and `review-green.log`.
- **Scanners:** reran `target/template/scripts/checks/test_exercises_production.py` with `PDCA_PROD_PACKAGE=pdca_harness` and `PDCA_BUNDLE` set to the review directory; reran the docs linter, site renderer with `--check`, and `git diff --check`. All passed. The instance-scoped wrappers themselves are not present here; their full frozen logs were read.
- **Runtime:** `python3 -m unittest discover -s tests` in the template passed. `python3 -m tests.run_root_suite` could not exercise Copier under this interpreter. This is a reviewer-host caveat, not a patch failure: the frozen root log explicitly records the render/update cases and their successful 24-test result (`gate-logs/T3-suite.log:39`).
- **Prior art:** queried main commit history separately for all three affected paths. Queried all 233 closed PRs by their changed-file paths, including closed-unmerged work, then inspected all nine matching diffs; all nine were merged and none introduced tracker metadata inheritance. Results are in `review-history.log` and `review-prior-art.log`. No other checkout was consulted.
- **Human-only integration rules:** the available integration template leaves the project-specific list as TODO (`target/template/docs/INTEGRATION.md.jinja:80`); it supplies no additional concrete human-only item.

## Sign-off validation steps

After correcting label encoding, use a disposable GitHub repository and a configured instance with a real, non-stub two-child proposal. Give the parent a milestone and the labels `bug`, `help wanted`, and `area,backend`. Run `pdca split <parent-id> --accept`, then run `gh issue view <child-id> --repo <owner/repo> --json milestone,labels` for **each** returned child. Confirm that both issues exist, have the parent's milestone title, and carry exactly the parent's label names, including the single comma-containing name. The human decision is whether those persisted results preserve release scope and progress accounting; the current offline fixture cannot establish that outcome.

This review is advisory. The C3 finding does not change the frozen deterministic gate results or make an acceptance decision.
