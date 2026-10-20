Review the cross-wave fold fallback that holds a conflicting bundle and names exactly its direct and two-bundle joint conflict partners, while preserving conservative stops.

Source paths below are relative to `target/`, the disposable `$PDCA_TARGET`; evidence paths are relative to this review directory.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The naming rule, removal acceptance check, and explicit three-bundle/stacked limits give falsifiable outcomes without expanding the carry contract; brief.md:2, brief.md:12. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only production code produced five assertion failures, including all four required new hold cases, with STOPPING visible; review-red.log:80, template/tests/test_flow_cross_wave_joint_holds.py:275. |
| C3 Change | PASS | The fallback stays in fold classification, retains the existing acceptance rule, and leaves the carry's classifier unchanged; template/src/pdca_harness/integrate.py:1841, template/src/pdca_harness/integrate.py:1969. |
| C4 Verification (red→green) | PASS | Restoring production code changed the same 14-test run from five failures to all passing; the frozen gate independently records that transition; review-green.log:3, gate-logs/C4-verify.log:10. |
| C5 Causal adequacy | PASS | Real git proves joint conflict and exact attribution rather than file overlap; the removal trial rejects unexplained clashes, and an additional advanced-prerequisite probe names only P/R; template/src/pdca_harness/integrate.py:1850, template/tests/test_flow_cross_wave_joint_holds.py:321, review-own-change.log:1. |
| T1 Structure | PASS | Existing trial/worktree restoration machinery is reused, the acceptance predicate is extracted coherently, and the quadratic search runs only after conflict; template/src/pdca_harness/integrate.py:1859, template/src/pdca_harness/integrate.py:1934. |
| T2 Shape | PASS | Independent whitespace, docs lint, and site render/link checks passed; the host-parity log also shows lint and link audit success; gate-logs/host-ci-docs.log:10, template/src/pdca_harness/integrate.py:1916. |
| T3 Runtime | PASS | Independently reran 2,624 driver tests successfully (two skipped); frozen evidence additionally shows 24 root render/update tests passing; review-suite.log:1817, gate-logs/T3-suite.log:54. |
| T4 Contribution | N/A | Contribution artifacts are intentionally absent at Check; the substantive contribution audit must run at publish; gate-logs/T4-contribution.log:10. |
| T5 Judgment | NEEDS-HUMAN | Confirm the affected-path prior-art search covers merged history and closed/rejected work before accepting this approach — the provided target has only one synthetic commit, no remote, and no such search evidence; review-prior-art.log:1, brief.md:18. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether holds with exit 3 and continued unrelated work, together with deliberate stops for three-way and stacked joint clashes and quadratic conflict-only cost, meet operator expectations; template/tests/test_flow_cross_wave_joint_holds.py:244, template/tests/test_flow_cross_wave_joint_holds.py:371, template/src/pdca_harness/integrate.py:1934. |

Independent reproduction used `git stash push -- template/src/pdca_harness/integrate.py`, retained both patched test files, ran `PYTHONPATH=src python3 -m unittest tests.test_flow_cross_wave_fold_holds tests.test_flow_cross_wave_joint_holds` from `target/template`, restored with `git stash pop`, and repeated the command. The production file was restored to the patch's expected blob (`25238c93c0e5abf95da9db43c250d4882c518a95`). The four new hold cases and flipped predecessor test fail without the fix; all 14 pass with it. The three-bundle stop guard remains green in both legs.

The full driver suite was independently rerun with `PYTHONPATH=src python3 -m unittest discover -s tests`. It includes the unchanged mid-wave-base stop regression at template/tests/test_flow_same_wave_conflict.py:435. Docs checks used the target workflow's lint and render commands, producing 22 pages with a clean link audit. The root render/update suite could not be rerun because this interpreter lacks copier; its frozen log explicitly records 24 executed, passing tests, rather than a skipped-only run (gate-logs/T3-suite.log:54). All supplied gate logs were inspected; no external dependency is declared or shown unexercised for the offline git fix.

The additional real-git probe cut H from K's old tip, advanced K, and combined the rename/rewrite pair P/R on the line. `_own_change` returned K's old shared tip, and `_together` returned exactly P/R (review-own-change.log:1). No capability-probe/load-time symptom guard was introduced. No implementation defect was established.

Prior-art investigation by all three affected file paths returned only the synthetic base commit, and `git remote -v` returned nothing (review-prior-art.log:1). The brief names earlier attempts but supplies no affected-path merged/closed/rejected search record. The unfilled project-human-items entry in template/docs/INTEGRATION.md.jinja:80 supplies no additional concrete human-only criteria.

<!-- pdca:leaf-complete -->
