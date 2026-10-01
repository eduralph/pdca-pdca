Review issue #408: honor reviewer implementation tags within the taxonomy, recognize the three Validation-row forms, and prevent Basis quotes or duplicate Validation rows from misrouting work.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief defines observable routing outcomes and both carry-forward regressions; scope and external dependencies are explicit (`brief.md:13`, `brief.md:96`, `brief.md:192`). |
| C2 Reproduction (red pre-fix) | PASS | Independently retaining the new tests while stashing production changes produced 22 failures and 2 errors across 127 tests, including behavioral assertion failures (`review-red.log:478`). |
| C3 Change | FAIL | Newly promoted findings from reordered tables lose their actionable Basis: Verdict is located by header but Basis still means the following cell, so Do receives only “T5 Judgment” (`template/src/pdca_harness/assemble.py:818`, `template/src/pdca_harness/assemble.py:833`; reproduction below). |
| C4 Verification (red→green) | PASS | Restoring the exact production diff made all 127 focused tests pass; both requested carry-forward regressions are covered, although the additional reordered-Basis case remains uncovered (`review-green.log:111`, `template/tests/test_autoiterate.py:1927`, `template/tests/test_autoiterate.py:2045`). |
| C5 Causal adequacy | PASS | The fix changes classification and label matching at their cause, and counts duplicate standing rows before deduplication; it introduces no capability probe masking a load-time problem (`template/src/pdca_harness/assemble.py:324`, `template/src/pdca_harness/assemble.py:835`). |
| T1 Structure | PASS | Taxonomy-derived promotion and one shared label normalizer avoid independent routing definitions; changes remain within the five authorized files (`template/src/pdca_harness/assemble.py:69`, `template/src/pdca_harness/assemble.py:128`). |
| T2 Shape | PASS | Independent diff whitespace check, docs lint, and 22-page render/link audit passed; frozen T2 and host-parity logs agree (`review-docs.log:2`, `gate-logs/T2-docs.log:11`, `gate-logs/host-ci-docs.log:11`). |
| T3 Runtime | PASS | Independent driver run passed 2,202 tests with 2 skips; frozen evidence records 24 root tests including real render/update cases, which local missing Copier prevented repeating (`review-suite.log:1763`, `gate-logs/T3-suite.log:38`, `gate-logs/T3-suite.log:54`). |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the substantive audit is deferred to the mandatory publish gate (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Establish that merged and closed/rejected work across all five affected paths does not supersede this change — the supplied target has only a synthetic base commit and no remote, while the brief's recorded path searches cover only part of the changed set (`brief.md:111`; investigation below). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the resulting routing behavior serves the intended review workflow after the lost-Basis defect is resolved — deterministic parser tests cannot establish the quality of real reviewers' builder-fixability judgments (`template/agents/reviewer.md.jinja:114`, `template/agents/adversary.md.jinja:60`). |

Source citations beginning `template/` refer to the supplied `$PDCA_TARGET`; brief and log citations refer to this review sandbox. The target was readable and carried the patch; no stale-target caveat was needed. This review is advisory and does not gate acceptance.

**Finding — preserve the Basis when honoring reordered Verdict columns (P2).** At `template/src/pdca_harness/assemble.py:833`, Basis extraction still uses `cells[vi + 1]`. With the newly supported header `Item / Basis / Verdict`, `vi` points to the final column, so the explanation becomes empty. The newly enabled promotion then yields `NeedsHumanItem(text='T5 Judgment', kind='impl', ...)`, sending implementation work back without the actual defect description. Different findings on that element can also collapse to the same text. The added reordered-column test checks only the label and kind (`template/tests/test_autoiterate.py:1952`), so it misses this loss.

I exercised `_items_from_artifact(..., allow_standing=True)` with this input:

```text
| Item | Basis | Verdict |
|---|---|---|
| C1 Spec | ok | PASS |
| T5 Judgment | Handle empty input | NEEDS-HUMAN [impl] |
| Validation — fitness-to-purpose | human decision | NEEDS-HUMAN |
```

Actual promoted text: `T5 Judgment`. Expected: `T5 Judgment — Handle empty input`. Locate Basis through the header as well, and assert the entire resulting finding text in the regression test. The reproduction was executed directly against production code; `review-reordered.log` records the result.

Independent verification retained the patched test module, stashed only the four production/prompt files, ran the red leg, popped the stash, checked byte-identical restoration of the original diff, and ran the green leg. The production-import scanner also completed; its frozen wrapper reported no newly added test file, so that wrapper's pass alone was not treated as proof of production coverage. The behavioral tests import and exercise the production classifier and auto-iteration path.

The local root-suite attempt exited 77 because `/usr/bin/python3` cannot import Copier (`review-root-suite.log:6`). This is a reviewer-host limitation: the frozen T3 log explicitly shows render and update cases running successfully, rather than merely skipping. No unmet external dependency was inferred from that local limitation. All six frozen gate logs were inspected; the host-CI evidence demonstrates local command parity, not a hosted CI run.

The prior-art investigation ran `git log --all --oneline --` with all five changed paths and `git remote -v` inside the supplied target. It returned only `81bd363 pre-fix base 4b329e4d82319f6dcb2667da12f1f309b6ef636c` and no remote. The brief records merged-history searches for `assemble.py` and `leaves.py`, but its closed-unmerged path list omits the modified role files, test file, and `leaves.py`; complete merged/closed/rejected coverage cannot be confirmed from this artifact-only bundle. No other checkout was consulted.

The brief records explicit prior sign-off acceptance of mandatory advisory tags and approval of the other role changes (`brief.md:206`, `brief.md:208`). That decision is carried forward; this review does not reopen the accepted advisory-tag policy or request approval for it again.
