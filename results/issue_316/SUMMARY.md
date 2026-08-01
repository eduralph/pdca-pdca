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
- T3 runtime: render/update-compat + offline driver suites: fail — /tmp/tmpryzjc1oj/results/issue_500/split-proposal.md
- T4 PR body has a user-impact opener + tracker id in both artifacts: pass — pdca-pdca contribcheck
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Review of issue #316: add `pdca triage` to ingest, classify, route, and Act-register published PR review findings, including pagination and interrupted-run recovery.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief gives a falsifiable command-level contract and bounded routing/registration scope, represented by the public parser entry at `template/src/pdca_harness/cli.py:318`. |
| C2 Reproduction (red pre-fix) | PASS | Independently applying only the shipped test to target `HEAD` produced rc=1 at the new-module import (`template/tests/test_triage.py:28`), establishing a red pre-fix baseline. |
| C3 Change | FAIL | Unmatched review text receives no one-of-four fallback after the keyword loop and is routed as `UNCLASSIFIED`, so a valid external finding can evade the required class route (`template/src/pdca_harness/triage.py:245`, `template/src/pdca_harness/triage.py:438`). |
| C4 Verification (red→green) | PASS | An independent temporary reconstruction was red on target `HEAD` (rc=1) and green with the full patch (17/17 tests), including the page-2 and lock-recovery cases at `template/tests/test_triage.py:157` and `template/tests/test_triage.py:252`. |
| C5 Causal adequacy | NEEDS-HUMAN | Decide whether recurrence identity must be broad class, class+keyword, or a semantic slug — the current keyword-derived identity at `template/src/pdca_harness/triage.py:108` makes synonyms separate signals, which determines whether a repeated process failure is detected. |
| T1 Structure | PASS | The additive engine module has one CLI dispatch boundary and preserves the existing `register_signals` default contract while opting triage into first-sighting registration (`template/src/pdca_harness/cli.py:462`, `template/src/pdca_harness/act.py:479`). |
| T2 Shape | PASS | Independent documentation lint and a 22-page render/link audit both passed; the target-grounded CLI surface is coherent at `template/src/pdca_harness/cli.py:318`. |
| T3 Runtime | FAIL | Direct execution with neutral text returned `{'cls': '', 'signal': 'codex-pr:unclassified'}`, demonstrating that the green canned suite misses a required runtime class/routing outcome (`template/src/pdca_harness/triage.py:245`, `template/src/pdca_harness/triage.py:110`). |
| T4 Contribution | NEEDS-HUMAN | Confirm the eventual commit message and PR body retain the user-impact opener and #316 tracker identity — those contribution artifacts were withheld from this artifact-only review, so the recorded contribcheck pass could not be independently rerun. |
| T5 Judgment | NEEDS-HUMAN | Confirm no closed/rejected #316 implementation duplicates this contribution — affected-path merged history and local refs showed no triage work, but the GitHub closed-PR query was unreachable, leaving duplicate-work risk unsettled. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide live operational fitness by running `pdca triage OWNER/REPO#N` on a disposable merged PR and checking the triage record, Act ledger/log, and filed BUG issue — canned `gh` tests exercise subprocess shape but not real API pagination, authentication, or permissions (`template/src/pdca_harness/triage.py:123`). |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] C5 Causal adequacy — Decide whether recurrence identity must be broad class, class+keyword, or a semantic slug — the current keyword-derived identity at `template/src/pdca_harness/triage.py:108` makes synonyms separate signals, which determines whether a repeated process failure is detected.
- [x] T4 Contribution — Confirm the eventual commit message and PR body retain the user-impact opener and #316 tracker identity — those contribution artifacts were withheld from this artifact-only review, so the recorded contribcheck pass could not be independently rerun.
- [x] T5 Judgment — Confirm no closed/rejected #316 implementation duplicates this contribution — affected-path merged history and local refs showed no triage work, but the GitHub closed-PR query was unreachable, leaving duplicate-work risk unsettled.
- [x] Validation — fitness-to-purpose — Decide live operational fitness by running `pdca triage OWNER/REPO#N` on a disposable merged PR and checking the triage record, Act ledger/log, and filed BUG issue — canned `gh` tests exercise subprocess shape but not real API pagination, authentication, or permissions (`template/src/pdca_harness/triage.py:123`).

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: merged-wider
- Iteration delta (if iterating):
- By / date: Eduard Ralph / 2026-07-31

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
- Sign-off ruled unclassified an accepted 5th category (criterion (b)'s "one of four" vs scope's "unclassified remainder" tension) — future triage briefs/rubric should state five buckets explicitly.
