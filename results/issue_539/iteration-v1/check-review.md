Review transient leaf-death classification so reported API failures can retry after work, signal deaths do not retry, and operator messages accurately describe both cases.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | Six criteria distinguish retryable causes, permanent errors, recovery, signals, retention, and unchanged callers; scope exceptions require reconciliation below (`brief.md:29`, `brief.md:110`). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing the three production changes leaves 40 classification tests runnable and produces 21 assertion failures, including connection-loss and signal cases (`review-red.log:1`; `template/tests/test_terminal_error_classification.py:221`). |
| C3 Change | FAIL | A typed permanent gateway failure in the supported transcript spelling is retried three times because `apiError` is overlooked; its `api_error` stream equivalent correctly gets one attempt (`template/src/pdca_harness/progress.py:838`; `review-typed-error.log:1`). |
| C4 Verification (red→green) | PASS | Restoring the patch makes all 74 classification/retention tests pass; the frozen C4 log verifies all three changed test modules, but they omit the C3 transcript case (`review-green.log:1`; `gate-logs/C4-verify.log:10`). |
| C5 Causal adequacy | PASS | Cause classification and signal exclusion directly address the proxy defect; recovered work clears the verdict while preserving evidence, with no added capability probe masking a load-time cause (`template/src/pdca_harness/progress.py:259`; `template/src/pdca_harness/leaves.py:109`). |
| T1 Structure | PASS | Stream interpretation remains in progress and the retry decision remains in LeafError; the shared retry loop receives wording changes without structural edits (`template/src/pdca_harness/progress.py:803`; `template/src/pdca_harness/leaves.py:109`). |
| T2 Shape | PASS | Independent docs lint, 22-page site render/link audit, and diff whitespace check pass; frozen docs and host-CI evidence agrees (`gate-logs/T2-docs.log:10`; `gate-logs/host-ci-docs.log:10`). |
| T3 Runtime | PASS | Independent offline suite passes 2,021 tests with two skips; local root tests lack importable Copier, but the frozen gate actually passed all 24 root tests, including update compatibility (`gate-logs/T3-suite.log:38`; `review-suite.log:1656`). |
| T4 Contribution | N/A | Contribution artifacts are absent by design; the substantive audit is deferred to the mandatory publish rerun (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Decide whether to approve excluded retention-test and builder-message edits, and discharge the incomplete prior-art audit — the brief forbids those edits and this snapshot cannot establish merged plus closed/rejected history for every affected path (`brief.md:123`, `brief.md:139`, `brief.md:198`; `template/tests/test_terminal_error_retention.py:368`; `template/src/pdca_harness/leaves.py:2201`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether stub-driven evidence and derived vendor records suffice for real CLI failures — no live vendor API-error session was exercised, and the current-version stream contract rests on binary reading rather than an observed run (`template/tests/fixtures/README.md:106`, `template/tests/fixtures/README.md:158`). |

C3 finding (medium): preserve typed permanent causes in both accepted spellings. The classifier accepts `isApiErrorMessage` alongside `is_api_error_message` (`template/src/pdca_harness/progress.py:829`), but its unknown-kind exclusion checks only `api_error`. A transcript record carrying `apiError="gateway_session_expired"` falls through to prose matching. With the same “gateway session timed out; connection lost” text used by the existing stream test, it incorrectly spends the complete retry budget on a credential/session failure. The provenance note identifies that typed cause as a sign-in stop (`template/tests/fixtures/README.md:134`). This is a reproduced parser defect in an accepted input spelling, not a claim that a live CLI emitted this exact constructed record during review.

Observed through `_invoke_leaf_resilient`, with real Python child processes:

```text
stream: typed gateway_session_expired; transient=False; attempts=1
transcript: typed gateway_session_expired; transient=True; attempts=3
```

Reproduce from `$PDCA_TARGET/template`, with `TMPDIR` set to a scratch directory inside the harness cwd:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests python3 - <<'PY'
import test_terminal_error_classification as t
case = t._StubLeafCase()
case.setUp()
event = t._report('unknown', 'API Error: gateway session timed out; connection lost')
event['isApiErrorMessage'] = event.pop('is_api_error_message')
event['apiError'] = 'gateway_session_expired'
event.pop('parent_tool_use_id')
err = case._run(t._stream(t._WORK, event))
print('transient:', err.transient, 'attempts:', case._runs())
assert not err.transient and case._runs() == 1
PY
```

Independent verification: `git stash push` was scoped to `assemble.py`, `leaves.py`, and `progress.py`, preserving the new tests; `git stash pop` restored the patch before the green leg. No source fix was made. The target includes prerequisite retention code and was usable, so there is no stale-target caveat. C4 passes for its asserted regression suite; it does not negate the additional C3 counterexample.

The local root runner reported `PDCA-UNVERIFIABLE` because `/usr/bin/python3` cannot import Copier (`review-root.log:6`). This is a local host limitation, not a patch failure or an undischarged Copier dependency: the frozen log shows the render/update cases actually ran. The vendor-contract dependency differs: the provenance note expressly says no real 2.1.284 API-error stream was observed. Sign-off should accept that evidence limitation explicitly or validate the kinds, typed causes, recovery traffic, and exit status against an actual CLI session.

For T5, the retention edits update assertions whose old values conflict with the intended classification, and the builder edit changes only diagnostic wording. They appear motivated by this task, but both cross explicit brief exclusions and require a scope decision. The brief records affected-path history for leaves/assemble and names rejected parent rounds; it does not supply a reproducible closed/rejected audit for every affected path. Investigation found exactly one synthetic base commit (`8ea9cca`) and no remotes; broader history cannot be established from this artifact-only target. The available `template/docs/INTEGRATION.md.jinja:80` leaves project-specific human-only items as TODO, adding no concrete items beyond this review contract.
