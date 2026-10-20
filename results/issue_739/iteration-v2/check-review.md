Review cross-wave integration-fold conflicts so a bundle-local clash holds that bundle and lets unrelated work continue, with accurate partner and rebuild advice.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief defines the bundle-versus-line failure boundary, five concrete outcomes, exit codes, and the #738 prerequisite; the target includes that prerequisite and the negative base-conflict case (`brief.md:2`, `template/tests/test_flow_cross_wave_fold_holds.py:458`). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only the two production files makes seven of 15 tests fail with the original STOPPING symptom, rather than import/setup errors (`review-evidence/red.log:3`, `review-evidence/red.log:86`). |
| C3 Change | PASS | The four-file patch stays within fold classification, carried-head tracking, operator advice, and regression coverage; the restored target passes reverse-application checking (`template/src/pdca_harness/integrate.py:665`, `template/src/pdca_harness/flow.py:3083`). |
| C4 Verification (red→green) | PASS | After stash restoration all 15 selected tests independently pass, matching the frozen gate's seven assertion failures without production changes and successful green leg (`review-evidence/green-restored.log:3`, `gate-logs/C4-verify.log:10`); this does not establish completeness beyond those cases. |
| C5 Causal adequacy | NEEDS-HUMAN [impl] | Preserve bundle-local holds when several independent joint clashes coexist — the global leave-one-out criterion finds no partners, so a real-git probe still stops unrelated L with no holds and exit 1 (`template/src/pdca_harness/integrate.py:1889`, `review-evidence/probe-joint.log:19`). |
| T1 Structure | PASS | Conflict attribution reuses the existing classifier and trial machinery, while hold propagation uses the existing flow state; the prior carrier-versus-own-change distinction is exercised (`template/src/pdca_harness/integrate.py:1846`, `template/src/pdca_harness/integrate.py:1854`, `template/tests/test_flow_cross_wave_fold_holds.py:342`). |
| T2 Shape | PASS | Independently reran docs lint, rendered 22 pages with a clean internal-link audit, and passed git diff whitespace checking; both frozen docs gates also show actual successful output (`gate-logs/T2-docs.log:12`, `gate-logs/host-ci-docs.log:11`). |
| T3 Runtime | PASS | Independent driver discovery passes 2,617 tests with two skips; the frozen root-suite log records 24 passing tests, while the local root rerun exits 77 because Copier is not importable, so that portion rests on the frozen evidence (`review-evidence/driver-suite.log:1817`, `gate-logs/T3-suite.log:54`, `review-evidence/root-suite.log:6`). |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the gate explicitly defers the substantive PR/commit audit to its mandatory publish rerun (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | PASS | One logical change extends the existing hold model; prior-art searches ran by all four affected paths against merged history and closed/unmerged PRs, including changed-file confirmation, with no duplicate cross-wave hold found in those bounded results (`review-evidence/prior-art-summary.md:1`, `template/src/pdca_harness/integrate.py:1802`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the observed hold/exit behavior and owner-directed rebuild advice fit real operator workflows — offline real-git cases exercise them, but operational acceptance remains a human decision (`template/src/pdca_harness/flow.py:1574`, `template/tests/test_flow_cross_wave_fold_holds.py:320`, `template/tests/test_flow_cross_wave_fold_holds.py:417`). |

Source citations beginning `template/` refer to the patched source under `$PDCA_TARGET` (`target/`). Gate-log and reviewer-evidence citations refer to the supplied bundle and this review's scratch evidence. The production patch was restored after the red leg; no implementation or supplied tests were edited.

The remaining implementation concern is reproducible with two copies of the requested joint-conflict topology on different files. P1 renames the first file and R1 rewrites most of it; P2 and R2 do the same to the second file. H edits the last line of both files and depends only on unrelated K. H merges onto the base and after every single partner; it conflicts after P1+R1 and after P2+R2. Removing any one partner leaves the other pair's conflict, so `_together` finds no individually necessary partner and returns an empty list (`template/src/pdca_harness/integrate.py:1889`, `template/src/pdca_harness/integrate.py:1902`). The flow prints STOPPING, returns no holds, leaves unrelated L PLANNED, and exits 1. This meets the brief's combined-trial bundle-local condition, yet retains the original run-wide failure.

The builder should identify the participating conflicting groups without requiring any single partner's removal to cure every independent conflict, continue excluding unrelated bundles, and add this multi-group regression. The existing test covers one conflicting pair plus an unrelated X (`template/tests/test_flow_cross_wave_fold_holds.py:391`); the added reviewer probe exposes the missing combination. This is an implementation iteration concern, not a C4 gate failure or a target-state caveat. No capability-probe symptom guard was introduced.

To rerun the independent probe from this review directory:

```bash
TMPDIR="$PWD/review-evidence/tmp" PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=target/template/src:target/template \
  python3 review-evidence/probe_joint_conflicts.py
```

The probe imports the supplied fixture and production flow, runs real git merges, and fails on the unwanted stop (`review-evidence/probe_joint_conflicts.py:17`, `review-evidence/probe-joint.log:18`). The original two carried-forward implementation cases now pass: unrelated X is excluded, and a partner built on a stranded branch is not itself told to rebuild on main. The new failure requires two independent joint-conflict groups.

The wrapper oracles belong to the originating instance, so their frozen logs were inspected rather than treated as missing target tools. The production-import check was also independently confirmed by parsing the added test: it imports `pdca_harness` and calls `flow._drive_and_act` (`template/tests/test_flow_cross_wave_fold_holds.py:46`, `template/tests/test_flow_cross_wave_fold_holds.py:189`). The brief declares no external dependency, and the relevant git topology was exercised; the local Copier limitation is confined to reproducing the already-successful root-suite gate.

<!-- pdca:leaf-complete -->
