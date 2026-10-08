Review of #646: make a re-issued stack-mode flow carry finished prerequisites onto its batch’s existing integration line before wave 0, preserving prior build bases and refusing rejected work.

Source paths below are relative to `$PDCA_TARGET` (`target/`); evidence paths are relative to this review directory. This review is advisory and does not gate acceptance.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | Recovery, append-only history, per-prerequisite holds and the prior review’s target-wide closed-PR refusal have explicit observable outcomes; the no-carry exception is documented (`brief.md:33`, `brief.md:201`; `docs/07-crosscutting.md:675`). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing production changes while retaining the tests produced 21 assertion failures in 70 tests, including a dependent missing its prerequisite’s file and integration base (`review-red.log:298`, `review-red.log:630`). |
| C3 Change | FAIL | A closed PR’s unavailable head is treated as proof its work is absent, allowing same-target bundles to build on the rejected changes already on the line; reproduced below (`template/src/pdca_harness/integrate.py:560`; `review-closed-head.log:15`). |
| C4 Verification (red→green) | PASS | Restoring the production changes made all 70 focused tests pass, independently confirming the frozen C4 result; this establishes the shipped regressions, but they miss the C3 case (`review-green.log:178`; `gate-logs/C4-verify.log:10`). |
| C5 Causal adequacy | PASS | Carrying skipped finished prerequisites before wave 0 addresses their omission from the fold; the fold, tip read and re-gate share the lock. No capability probe masks a load-time cause; the remaining fail-closed defect is C3 (`template/src/pdca_harness/flow.py:798`, `template/src/pdca_harness/flow.py:883`). |
| T1 Structure | PASS | Existing flow, merge-state and integration modules retain their responsibilities, with shared fetch behavior and production-path regression coverage; no new dependency or parallel implementation (`template/src/pdca_harness/integrate.py:632`; `template/tests/test_flow_resume_stack_prereqs.py:44`). |
| T2 Shape | PASS | Independently rerun docs lint, 22-page rendering/link audit and production-import scanner passed; diff whitespace checks passed, consistent with both frozen docs gates (`review-scanners.log:1`; `gate-logs/host-ci-docs.log:10`). |
| T3 Runtime | PASS | Independent driver suite: 2,349 tests, two skipped, no failures; frozen root-suite evidence reports 24 passing tests. Local root rerun lacks importable Copier, a reviewer-host limitation rather than a patch defect (`review-suite.log:1951`; `gate-logs/T3-suite.log:54`; `review-root-suite.log:6`). |
| T4 Contribution | N/A | Contribution artifacts are intentionally absent at Check; the deferred gate’s substantive audit must rerun at publish (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Confirm prior-art coverage across all affected paths and closed/rejected work — the brief records a path-based search for three modules, but the supplied target has only a synthetic base commit and no remotes, so broader history and rejected-PR conclusions cannot be independently settled (`brief.md:167`; `review-prior-art.log:1`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the scoped recovery behavior and host coverage suffice after addressing C3 — real Git history, publishing and re-gating ran, but live GitHub/gh state retrieval was not exercised; its evidence rests on mocked host responses, and no-carry runs still replace the line (`template/tests/test_flow_resume_stack_prereqs.py:112`; `docs/07-crosscutting.md:681`). |

Confirmed finding — unavailable closed-PR head permits rejected work (high priority).

`template/src/pdca_harness/integrate.py:560` returns `False` when `git cat-file` cannot resolve the host-reported head. That answer reaches `flow.py:847` as “not on the line,” bypassing the target-wide refusal. An unavailable head cannot establish that earlier commits from the same PR are absent.

I exercised this sequence against the patched target using the shipped fixture and real Git:

1. Publish P and Q; fold both onto the batch’s line.
2. From another checkout, push a fixup to P, then close its PR and delete its branch before the harness fetches again. The host reports the fixup’s SHA, which the harness checkout does not have.
3. Resume the same batch with D depending on P, E depending on Q, and unrelated U; report P CLOSED and Q OPEN through the fixture’s host-response table.

Observed: the line still contains P’s original commit; D remains PLANNED, but E and U are driven and published COMPLETE. E’s recorded build base is the earlier line holding CLOSED P. Stderr incorrectly says P “is not carried.” This contradicts the explicit carry-forward requirement (`brief.md:201`) and the published refusal contract (`docs/07-crosscutting.md:675`). Evidence: `review-closed-head.log:15`. The existing deleted-branch test (`template/tests/test_flow_resume_stack_prereqs.py:513`) only checks a head already available from the earlier fold, so it misses this case.

Treat an unresolvable head as unknown and block that target, or obtain sufficient history to prove absence before continuing. Add this deleted-branch-after-fixup case to the regression suite. The standalone reproduction is preserved in `review-closed-head.py`; run from this review directory:

```sh
TMPDIR="$PWD/review-tmp" PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH="$PWD/target/template/src:$PWD/target/template" \
python3 review-closed-head.py
```

The supplied target was readable and compatible with the patch; no stale-target caveat applies. Production changes were restored after the red leg, and no fix was made. The frozen root-suite log discharges the Copier coverage absent from this reviewer’s interpreter; it is not an unmet dependency of the submitted gate run. The project’s supplied `template/docs/INTEGRATION.md.jinja:80` leaves human-only items as a TODO and enumerates no additional project-specific decisions.
