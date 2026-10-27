Review issue #749: distinguish a line partner stranded by a moved base from an ordinary overlap, hold the affected bundle, and direct rebuild advice to the correct owner.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | Ownership, start commit, stop boundaries, and offline acceptance cases are explicit and falsifiable; the same-file counterexample falls under the requirement that the base move actually cause the clash (brief.md:6; template/tests/test_flow_cross_wave_stranded_holds.py:504). |
| C2 Reproduction (red pre-fix) | PASS | Stashing only the two production files reproduced six assertion failures with `STOPPING` across the 16 focused tests; the failures match the frozen evidence (review-red.log:3; gate-logs/C4-verify.log:25). |
| C3 Change | PASS | The patch is confined to fold classification, hold advice, and regression coverage; it reuses the own-change and trial helpers without changing base selection or adding another trial worktree (template/src/pdca_harness/integrate.py:1974; template/src/pdca_harness/integrate.py:2024). |
| C4 Verification (red→green) | PASS | Restoring production changes made all 16 specified tests pass, independently reproducing the asserted transition; the additional regression is adjudicated in C5 (review-green.log:3; template/tests/test_flow_cross_wave_stranded_holds.py:324). |
| C5 Causal adequacy | NEEDS-HUMAN [impl] | Correct attribution when independent hunks share a file — file-name intersection admits an unrelated base move and incorrectly proposes the partner's rebuild; the real-git counterexample passes before the fix and fails afterward (template/src/pdca_harness/integrate.py:1968; review-same-file-probe.log:4). |
| T1 Structure | PASS | Classification stays in integrate and wording stays in flow, with one transient reason record and the existing trial lifecycle; no new persisted state or worktree mechanism is needed (template/src/pdca_harness/integrate.py:1803; template/src/pdca_harness/flow.py:1609; template/src/pdca_harness/integrate.py:2250). |
| T2 Shape | PASS | Independent whitespace/syntax checks, documentation lint, and 22-page rendering with internal-link audit passed; frozen host-parity output agrees (review-docs.log:2; gate-logs/host-ci-docs.log:10). |
| T3 Runtime | PASS | Independently ran 2,632 driver tests successfully with two skips; frozen evidence shows all 24 root render/update tests executed successfully (review-suite.log:1817; gate-logs/T3-suite.log:54). |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the deferred row explicitly reserves the substantive audit for publish (gate-logs/T4-contribution.log:10). |
| T5 Judgment | NEEDS-HUMAN | Confirm affected-path merged and closed/rejected prior art for flow.py and integrate.py — the supplied snapshot exposes one synthetic commit, no remotes, and none of the cited #739 iteration records, so the required historical comparison cannot be established (review-prior-art.log:1; brief.md:17). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the resulting owner-directed rebuild/update instructions are actionable for maintainers across the specified moving-base workflows — executable coverage establishes behavior but maintainer acceptance of that workflow remains owed (template/src/pdca_harness/flow.py:1635; template/tests/test_flow_cross_wave_stranded_holds.py:537). |

Source citations beginning `template/` are grounded in `$PDCA_TARGET` (`target/`). The target matches the patch: reverse application checks passed before and after the independent reruns, and the production changes were restored. No target-state caveat was encountered.

**Builder-fixable finding: independent conflicts in the same file receive moved-base blame.** At `template/src/pdca_harness/integrate.py:1968`, overlapping file names suffice to admit a stranded explanation. They do not establish that the base move caused the actual conflict. The existing guard at `template/tests/test_flow_cross_wave_stranded_holds.py:504` catches the equivalent case only when the two conflicts occupy different files.

I exercised a same-file variant through the production `flow._drive_and_act` and real Git. Start with nine lines in `shared.txt`. A changes lines 2 and 8. After the first fold, main independently changes line 8. Y depends on Q, is built on that moved main, changes line 2, and restores line 8 to its original content. An unrelated W → V → U chain forces subsequent folds, with V using `Stacks on: W`. A and Y conflict only on line 2: the captured plain-Git merge leaves line 8 clean (`review-same-file-probe.log:9`). Y has undone the base move, so that move does not explain this clash.

Without the production changes, the run preserves the stop and proposes no rebuild for A (`review-same-file-baseline.log:4`, exit 0 for the probe). With the patch, it records `{'Y': 'conflict'}`, returns 3, and tells A's owner to rebuild on new main (`review-same-file-probe.log:3`, probe assertion failure at line 28). This violates the same causal boundary the existing different-file guard protects. Add coverage for independent hunks in one file and establish causal attribution beyond path intersection before issuing the stranded-partner advice.

The standalone probe is `review-same-file-probe.py`. From this report's directory, reproduce its failure on the restored patched target with:

```sh
TMPDIR="$PWD/review-scratch" PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH="$PWD/target/template/src:$PWD/target/template" \
  python3 review-same-file-probe.py
```

Independent verification also exercised direct production imports and the real fold (`template/tests/test_flow_cross_wave_stranded_holds.py:61`, `:198`, `:214`), matching the C5 production-path log. The reviewer interpreter lacks Copier, so the root render/update assessment uses the frozen T3 log, which shows 24 actual successful tests; the full driver suite and docs checks were rerun locally. The instance-scoped gate wrappers are not supplied here; their frozen logs were read. The brief declares no external dependencies, and the relevant Git topology was exercised directly. No capability-probe/load-time symptom guard was introduced.

For prior art, the affected-path history query and absence of supplied rejected iterations are recorded in `review-prior-art.log`. The brief's historical references identify what must be checked but do not supply evidence that the merged-history and closed/rejected-work comparison ran. This remains a human decision, separate from the reproducible C5 implementation defect.

<!-- pdca:leaf-complete -->
