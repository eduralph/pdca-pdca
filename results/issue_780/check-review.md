Review #780: prevent a standalone sign-off from leaving a stale flow decision that can accept a rebuilt bundle without a fresh sign-off session.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The decision lifetime is explicit and falsifiable: consume only after successful recording, including all four actions, while refused or failed records retain their input (template/tests/test_signoff_consumes_decision.py:111, :154, :162). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing the production fix produced eight assertion failures across seven tests, including the rebuilt bundle becoming COMPLETE with §6 clear and no fresh session (template/tests/test_signoff_consumes_decision.py:135, :147; review-reruns.log:9). |
| C3 Change | PASS | The standalone route now honors the existing consume-on-record boundary before any transition can fail or hold; the C6 and record-error exits remain earlier (template/src/pdca_harness/cli.py:1515, :1530, :1542, :1545; template/src/pdca_harness/flow.py:205). |
| C4 Verification (red→green) | PASS | After stash restoration, all seven regression tests passed independently; refusal and record-error controls passed on both legs, and raised/held transitions are covered (review-reruns.log:131; template/tests/test_signoff_consumes_decision.py:171, :179). |
| C5 Causal adequacy | PASS | With C6 explicitly permissive, the real flow replay now leaves the rebuilt bundle AWAITING_SIGNOFF and offers it a fresh session; deleting stale input removes the cause without a capability probe (template/tests/test_signoff_consumes_decision.py:135, :145, :150; template/src/pdca_harness/cli.py:1542). |
| T1 Structure | PASS | The lifecycle correction belongs at the recording boundary already used by flow; the patch introduces no new subsystem or unrelated behavior (template/src/pdca_harness/cli.py:1542; template/src/pdca_harness/flow.py:205). |
| T2 Shape | PASS | Independent docs lint, 22-page render/link audit, six checker tests, 458 relative-link checks, 12 ADR checks, and whitespace check all passed (review-scanners.log:1, :6, :13, :22, :27, :32). |
| T3 Runtime | PASS | Independent driver-suite run passed 2,654 tests with two skips; frozen root-suite evidence records 50 executed tests and OK (review-driver-suite.log:1819; gate-logs/T3-suite.log:80, :82). |
| T4 Contribution | N/A | Contribution artifacts are absent by design during Check; the substantive contribution audit must rerun at publish (gate-logs/T4-contribution.log:10). |
| T5 Judgment | NEEDS-HUMAN | Confirm no merged or closed/rejected work supersedes this fix on the affected paths — the disposable snapshot exposes one base commit and no remotes, so the supplied #395 provenance cannot settle prior art independently (review-scanners.log:36). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the demonstrated decision lifetime meets the intended approval workflow — the replay proves that a rebuilt attempt receives a fresh session, but fitness remains the human sign-off decision (template/tests/test_signoff_consumes_decision.py:150). |

Source citations above are relative to `$PDCA_TARGET` (`/tmp/pdca-review-sax61nuu/target`); evidence logs are relative to this review directory. The patch is present and reverse-apply checking succeeded. Only the production change was stashed for the red leg, retaining the new regression tests; stash pop restored the original production diff exactly (review-reruns.log:148).

The independent regression used `PYTHONPATH=src python3 -m unittest -v tests.test_signoff_consumes_decision` from the target's `template/` directory. It reproduced the forbidden stale acceptance before the fix and the fresh-session behavior afterward. All four recording actions, both non-recording controls, and both transition-ordering cases passed afterward. The fixtures can exhibit the forbidden failure, as the red leg demonstrates; the brief declares no external dependencies.

The instance-scoped gate wrappers are not available in this target snapshot. Their frozen logs were read: C4 reports the same red/green outcome; C5 reports a production-package import, independently confirmed at template/tests/test_signoff_consumes_decision.py:31 and by executing its production calls; both docs gates show successful lint and render audits. Copier is not importable in this review interpreter, so the root render/update suite was adjudicated from its full frozen log, which shows those cases actually executing and passing. This is a local rerun limitation, not an unmet dependency in the frozen gate run or a patch defect.

The prior-art investigation ran `git log --all --format='%h %s' -- template/src/pdca_harness/cli.py template/tests/test_signoff_consumes_decision.py` and `git remote -v` in the target. Results: only `9ec438a pre-fix base 3c11556651da9741e35f704c0497a5bf326cbd42`, and no remotes. Merged history and closed/rejected work therefore remain unconfirmed. The available integration template enumerates no additional concrete human-only checks (template/docs/INTEGRATION.md.jinja:80).

No implementation defect found. This review is advisory; acceptance remains the human's decision.

<!-- pdca:leaf-complete -->
