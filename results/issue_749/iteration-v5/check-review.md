Review #749: hold moved-base fold clashes consistently across one or several files, using strict subsets of conflicting head-line positions and advice aimed at the bundle that can act.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The shared head-file frame, strict-subset rule, stop guards, and retained exclusions make the requested behavior falsifiable; brief.md:37 and brief.md:45. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only the production fix reproduced 16 assertion failures across 30 tests, including the one-file STOPPING symptom; review-red.log:205 and template/tests/test_flow_cross_wave_stranded_holds.py:915. |
| C3 Change | PASS | The affected production paths and real-git flow tests address the scoped classifier and inherited hold behavior; template/src/pdca_harness/integrate.py:2247 and template/src/pdca_harness/flow.py:1621. |
| C4 Verification (red→green) | PASS | Restoring the production fix made all 30 regression tests pass; independent mutations also exposed the old file rule and weaker line-drop rule; review-green.log:3 and review-mutations.log:1. |
| C5 Causal adequacy | NEEDS-HUMAN [impl] | Handle configured Git conflict-marker lengths — an ordinary text file with conflict-marker-size=9 still stops the run instead of holding W, because valid diff3 blocks are discarded; template/src/pdca_harness/integrate.py:1896 and review-marker-size.log:16. |
| T1 Structure | PASS | Conflict capture stays inside trial merges, resets remain protected by finally, and attribution uses production helpers rather than a parallel merge implementation; template/src/pdca_harness/integrate.py:1767 and template/src/pdca_harness/integrate.py:2563. |
| T2 Shape | PASS | Independent docs lint, site render/link audit, production-import scanner, and git diff --check passed; frozen docs and host-parity logs corroborate the docs results; gate-logs/T2-docs.log:11 and gate-logs/host-ci-docs.log:11. |
| T3 Runtime | PASS | Independent offline driver discovery passed 2,646 tests with two skips; frozen evidence also shows 24 passing root render/update tests; review-suite.log:1817 and gate-logs/T3-suite.log:54. |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the deferred row explicitly reserves the substantive contribution audit for publish; gate-logs/T4-contribution.log:10. |
| T5 Judgment | NEEDS-HUMAN | Confirm prior art by all four affected paths across merged history and closed/rejected work — this copy has only a synthetic base commit, no remote, and no iteration archives, so the brief's historical claims cannot be independently settled; review-prior-art.log:1 and brief.md:56. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Accept whether the rebuild/update advice and retained same-wave/overlap exclusions fit the intended workflow — real-git advised rebuilds pass, but the operational scope remains a maintainer decision; template/tests/test_flow_cross_wave_stranded_holds.py:908 and brief.md:51. |

Source citations beginning `template/` resolve inside `$PDCA_TARGET` (`target/`). The target's sole base commit identifies the expected `2d18208` base; no stale-target caveat arose. The supplied patch was restored after the red leg, and production source was not edited for this review.

**Builder-fixable finding: configured conflict markers recreate the stop (C5).** At `template/src/pdca_harness/integrate.py:1896`, `_diff3_blocks` recognizes exactly seven marker characters. Git honors `.gitattributes`' `conflict-marker-size=9` even with the trial's diff3/rerere settings (`template/src/pdca_harness/integrate.py:1759`). Adding only `shared.txt conflict-marker-size=9` to the base of the existing one-file regression produces valid nine-character diff3 markers, but the parser returns `[]`. The run then says the text file has no diff3 blocks, prints `STOPPING`, and abandons later unrelated work. This is a readable text conflict, with neither a binary file nor a custom merge driver. Honor the effective marker length and cover this case with a real-git regression.

Run the independent reproducer from this report's directory:

```sh
python3 review-marker-size.py
```

It exits 1 on the existing hold assertion; `review-marker-size.log` captures the actual Git markers, empty parser result, and STOPPING output. The same test passes without the attribute in the independently green regression run.

The in-memory mutation checks left source unchanged: replacing strict subset with “some line left” made case (8b) fail; replacing it with the file-name rule made cases (5), (7), and (10) fail (`review-mutations.log`). The green real-git suite also exercised the proposed rebuild steps, the still-stop guards, one-file/two-file parity, repeated lines, deleted files, and the binary-file diagnostic.

All six supplied gate logs were read. Their instance-scoped wrappers are not present in this target, so available underlying validators were run directly. Copier is absent from this review interpreter; root render/update compatibility is supported by the frozen log's actual 24-test pass, not a claimed local rerun (`gate-logs/T3-suite.log:54`). This is a local toolchain limitation; the frozen gate did exercise that dependency. The publish contribution audit remains deferred as specified, with no Check-time escalation.

The prior-art investigation ran `git log --all -- <affected-path>` separately for both production files and both test files, inspected configured remotes, and searched the tracked `results/` tree. It found one synthetic base commit for the existing files, no history for the new test, no remotes, and no archived rejected work (`review-prior-art.log`). The human decision is to confirm the missing merged/closed-work search, including iterations 1–4 and the rejected parent approach named in the brief.

<!-- pdca:leaf-complete -->
