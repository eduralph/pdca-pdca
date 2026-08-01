# Result — issue 316 / pdca-triage

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: a `pdca triage` subcommand that ingests a published PR's external review
  findings into the Act ledger — pull via `gh api`, classify (BUG / CONVENTION / NOISE /
  TEST-GAP), route by class, and register every finding via `act.register_signals` with
  class-keyed signal names so `recurrences()` flags a class that reappears after its
  process delta was applied. Today the pipeline stops at the draft PR and the Act ledger
  only receives what a human remembers to register.
- Success criterion: `pdca triage <pr>` (gh subprocess stubbed in tests): (a) pulls
  the PR's review comments/reviews; (b) assigns each finding one of the four classes via
  keyword heuristics keyed to the instance rubric's class list; (c) routes by class —
  BUG on a merged PR → tracker issue + carry-forward note, CONVENTION → candidate gate
  row / rubric line appended to the act log, NOISE → candidate rubric-exclusion entry;
  (d) registers every finding through `act.register_signals` with class-keyed names
  (e.g. `codex-pr:option-default-vs-omit`) such that `recurrences()` reports a
  recurrence when the same class-keyed signal reappears. Demonstrable by C4-verify: the
  shipped test drives the command against canned `gh` output and asserts (a)–(d); red on
  current `main` (no `triage` subparser exists — verified against `cli.py`'s
  `add_parser` set).
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: the `pdca triage` verb: a new engine module + `cli.py` wiring, keyword
  classification with the class list read from the instance rubric where configured, the
  per-class routing above, and `register_signals` integration. The optional single model
  pass for the unclassified remainder is in scope only as a config-gated hook (off by
  default); keyword-only must be complete and useful on its own. / out of scope: the
  pre-publish review stage (#315); auto-*applying* any routed delta (the command
  proposes — appending candidates to the act log is the ceiling; it never edits
  `pdca.toml` or files gate rows itself); tracker-side automation beyond filing the BUG
  issue via the existing gh machinery.

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: new-feature
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: pass — C4 PASS: red without the fix, green with it
- C5 Causal adequacy: none — reviewer + human sign-off

## 4. Conformance (Check — stack)
- T1 Structure: none — (no gate configured)
- T2 shape: docs lint + site render link audit: pass — render_site: link audit OK
- T3 runtime: render/update-compat + offline driver suites: fail — /tmp/tmp382nti4b/results/issue_500/split-proposal.md
- T4 PR body has a user-impact opener + tracker id in both artifacts: pass — pdca-pdca contribcheck
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Reviewing issue #316: add `pdca triage` to ingest external PR-review findings, classify and route them, and register recurrence signals in the Act ledger.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The contract is bounded to one verb with observable pull, four-class classification, routing, registration, and recurrence outcomes, and the shipped oracle exercises those outcomes at `template/tests/test_triage.py:137`. |
| C2 Reproduction (red pre-fix) | PASS | A clean `HEAD` snapshot with only the shipped test fails at the triage import (`template/tests/test_triage.py:28`), establishing the absent-command baseline. |
| C3 Change | FAIL | The required “register every finding” outcome is not recoverable: after a held Act lock, the prescribed rerun returns on “no new findings” before registration, leaving the ledger permanently empty (`template/src/pdca_harness/triage.py:448`). |
| C4 Verification (red→green) | PASS | Independently reproduced red on clean `HEAD` and green with the patch: all 15 shipped triage tests pass, including the command-level path at `template/tests/test_triage.py:288`. |
| C5 Causal adequacy | FAIL | “Every finding” is not closed for large PRs: each endpoint is requested once with `per_page=100` and without pagination, so later reviews/comments are silently omitted (`template/src/pdca_harness/triage.py:422`). |
| T1 Structure | PASS | The additive engine is isolated behind the existing CLI, Config, split, rubric, and Act boundaries, with production behavior kept in `template/src/pdca_harness/triage.py:405`. |
| T2 Shape | PASS | Docs lint and the 22-page link audit rerun cleanly, and the optional model hook remains disabled by default at `template/src/pdca_harness/config.py:350`. |
| T3 Runtime | FAIL | Despite 1,329 offline tests and all 7 Copier render/update tests passing, a direct lock-contention run returns 1 then 0 while the ledger stays absent because the recovery path is unreachable (`template/src/pdca_harness/triage.py:497`). |
| T4 Contribution | NEEDS-HUMAN | Confirm no closed/rejected PR touching the five affected paths already implements this feature — merged `origin/main` path/history searches were clear and the contribution gate passed, but invalid `gh` authentication prevented the required closed/rejected-work check, so duplicate contribution risk remains. |
| T5 Judgment | NEEDS-HUMAN | Approve whether class-plus-first-keyword is a sufficiently stable recurrence identity — synonyms such as `crash` and `crashes` create distinct signals (`template/src/pdca_harness/triage.py:76`), which can hide a semantically repeated miss. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the four-way heuristic precedence and proposed routes fit the project’s operational review policy — live GitHub API/auth and irreversible tracker filing were not exercised, so evidence rests on the canned topology around `template/tests/test_triage.py:34`. |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T4 Contribution — Confirm no closed/rejected PR touching the five affected paths already implements this feature — merged `origin/main` path/history searches were clear and the contribution gate passed, but invalid `gh` authentication prevented the required closed/rejected-work check, so duplicate contribution risk remains.
- [ ] T5 Judgment — Approve whether class-plus-first-keyword is a sufficiently stable recurrence identity — synonyms such as `crash` and `crashes` create distinct signals (`template/src/pdca_harness/triage.py:76`), which can hide a semantically repeated miss.
- [ ] Validation — fitness-to-purpose — Decide whether the four-way heuristic precedence and proposed routes fit the project’s operational review policy — live GitHub API/auth and irreversible tracker filing were not exercised, so evidence rests on the canned topology around `template/tests/test_triage.py:34`.

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: iterated-to-Do
- Iteration delta (if iterating): Rejected on the advisory reviewer's two substantiated implementation defects (brief unchanged, approach sound): 1. C3/T3 — unreachable registration recovery: the "no new findings" early return sits BEFORE registration, so after a held Act lock (record written, exit 1) a re-run exits 0 without ever registering — ledger stays permanently empty (triage.py:448/:497). Reproduced dynamically by the reviewer. Fix: re-runs must re-derive registration from the full record history even when no NEW findings exist (make the self-heal claim in build-notes actually true), and cover the lock-contention-then-rerun path in the shipped test. 2. C5 — missing pagination: reviews/comments fetched once with per_page=100 (triage.py:422); PRs with >100 items silently drop findings, violating "register every finding". Fix: paginate both endpoints (or use gh api --paginate) and test the multi-page case.
- By / date: Eduard Ralph / 2026-07-31

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
