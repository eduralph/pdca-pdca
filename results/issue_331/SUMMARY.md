# Result — issue 331 / handoff-exit-contract

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: the interactive leaves get a checked exit contract: a rendered `/handoff
  <issue_id>` command that verifies the current leaf's contract and reports PASS/FAIL, a
  `Stop` hook that makes it non-optional, and driver-side capture of the session's
  carry-forward. Today the driver's entire completion signal is process exit — the
  interactive branch discards the exit code and captures nothing
  (`template/src/pdca_harness/leaves.py:250-257`, `subprocess.run(argv + [seed], ...)`
  with no `check=`), so "the human pressed Ctrl-D" and "the leaf discharged its
  contract" are the same event, and a malformed/absent artifact is discovered later, far
  from the cause.
- Success criterion: in a rendered instance: (a) `/handoff <issue_id>` exists
  (`template/.claude/commands/handoff.md.jinja`) and checks the *current* leaf's
  contract — planner: `brief.md` structurally against the brief template **and** every
  backticked `External dependencies` token resolves to a registered `[[doctor.checks]]`
  row whose detect `cmd` exits 0 or is annotated exempt (the #340 clause); signoff:
  `signoff-decision` one token from `VALID_DECISIONS` (`leaves.py:73`) with rationale
  for `iterate-*`/`discontinue`; publisher: `commit-msg.txt` + `pr-description.md`;
  act: the session NAMES the act-log entry it wrote; (b) the `Stop` hook
  (`template/.claude/hooks/handoff_guard.py`) blocks a session ending with a missing or
  malformed contract artifact, with feedback and a deliberate-abandon escape hatch;
  (c) ids are REQUIRED — there is no scan mode, and no `argument-hint` advertises one;
  (d) no new artifact is written into the bundle — the gate's verdict is exit status +
  report; (e) the session's carry-forward is captured while the session is live and
  merged with what `driver._carry_forward_into_brief` already extracts on iterate
  transitions; the registering and the consuming of that channel ship together;
  (f) which contract applies is derived from the render (the `interactive = true`
  leaves and their agent names), not hardcoded. Demonstrable by C4-verify: the hook and
  the contract checks are plain Python, unit-testable offline; red on current `main`
  (no `handoff` command, hook, or session-capture channel exists —
  `ls template/.claude/` confirms).
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: the three items of the issue, shaped by the prototype findings
  (getwyrd/wyrd-pdca#166, four review rounds / 27 findings): required ids, no bundle
  artifact, contract-fields checked against what the *corpus* actually satisfies (a
  named/scanned distinction or template-version check so an old bundle is never judged
  against a contract that postdates it; note the four traps measured: `Test file`
  legitimately empty in 7 bundles, `Falsifiability` absent in 52/85, `**User impact:**`
  absent in 43, and multi-line values read as empty by line-based `brief.parse_fields`),
  reuse of the instance's deterministic lint (`cli._contribcheck`) for the publisher
  contract rather than the configured T4 row, and the Act check requiring the session
  to name its entry. Batch wrinkle honoured: `/handoff issue_<id>` gates one bundle;
  the driver supplies the session-start baseline where authorship must be
  distinguished. / out of scope: resuming sessions (considered and rejected in the
  issue — incompatible with the escalation ladder, re-anchors on failed reasoning,
  moves state out of the bundle); any change to the sign-off write set beyond reading.

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
- T3 runtime: render/update-compat + offline driver suites: fail — /tmp/tmp58jvft5h/results/issue_500/split-proposal.md
- T4 PR body has a user-impact opener + tracker id in both artifacts: pass — pdca-pdca contribcheck
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Issue 331 adds a checked interactive-leaf handoff contract: `/handoff <id>`, a Stop hook, and session carry-forward capture.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief defines a concrete enhancement and success criteria for `/handoff`, Stop enforcement, required ids, no bundle artifact, and carry-forward capture; the human impact is avoiding late discovery of missing leaf contracts (`brief.md:7`). |
| C2 Reproduction (red pre-fix) | PASS | In a temporary copy with `patch.diff` reverse-applied, `python3 -m unittest tests.test_handoff tests.test_publish_slice` failed red with `ModuleNotFoundError: No module named 'tests.test_handoff'`, matching the test's stated pre-fix absence claim (`template/tests/test_handoff.py:20`). |
| C3 Change | PASS | The patch introduces the named command, Stop hook registration, per-role contract logic, leaf-session env registration, and carry-forward capture/merge in the intended surfaces (`template/.claude/commands/handoff.md.jinja:3`, `template/.claude/settings.json:68`, `template/src/pdca_harness/leaves.py:385`, `template/src/pdca_harness/flow.py:202`, `template/src/pdca_harness/driver.py:297`). |
| C4 Verification (red→green) | NEEDS-HUMAN | Decide whether the direct unittest red→green is sufficient, because the recorded C4 gate names `./engine/scripts/run-verify.sh` but the target runner is a skeleton that exits 1, so I could not independently reproduce the asserted gate row itself (`template/engine/scripts/run-verify.sh:50`). |
| C5 Causal adequacy | NEEDS-HUMAN | Decide whether the Stop hook may fail open on any bootstrap/check exception, because that runtime guard can turn the non-optional boundary back into an unchecked session end if the rendered contract is broken (`template/.claude/hooks/handoff_guard.py:75`). |
| T1 Structure | PASS | The implementation keeps contract checks in `pdca_harness.handoff` and leaves the hook as a thin protocol/bootstrap wrapper, which limits coupling and keeps the checks unit-testable (`template/src/pdca_harness/handoff.py:93`, `template/.claude/hooks/handoff_guard.py:55`). |
| T2 Shape | PASS | The user-facing command requires exactly one id, advertises no scan mode, and writes no bundle marker; this preserves the specified artifact shape (`template/.claude/commands/handoff.md.jinja:3`, `template/src/pdca_harness/handoff.py:324`, `template/tests/test_handoff.py:365`). |
| T3 Runtime | NEEDS-HUMAN | Decide how to treat the gate discrepancy: `check-gates.json` records an advisory T3 failure at a transient split-proposal path, while `PYTHONPATH=src python3 -m unittest discover -s tests` passed locally and the recorded temp path is not inspectable (`check-gates.json:69`). |
| T4 Contribution | NEEDS-HUMAN | Decide whether to accept the recorded T4 pass, because the reviewer inputs omit `commit-msg.txt` and `pr-description.md`, so I could not rerun the contribution gate against the actual published artifacts (`check-gates.json:78`). |
| T5 Judgment | NEEDS-HUMAN | Decide whether the chosen deliberate-abandon interface is acceptable, because the brief left escape-hatch shape as an open human judgment and the patch concretizes it as `--abandon "<why>"` (`brief.md:105`, `template/.claude/hooks/handoff_guard.py:104`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Human sign-off must decide whether this terminal workflow is fit for actual interactive use; I verified offline tests only, not a live Claude Code Stop-hook session (`brief.md:16`). |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] C4 Verification (red→green) — Decide whether the direct unittest red→green is sufficient, because the recorded C4 gate names `./engine/scripts/run-verify.sh` but the target runner is a skeleton that exits 1, so I could not independently reproduce the asserted gate row itself (`template/engine/scripts/run-verify.sh:50`).
- [x] C5 Causal adequacy — Decide whether the Stop hook may fail open on any bootstrap/check exception, because that runtime guard can turn the non-optional boundary back into an unchecked session end if the rendered contract is broken (`template/.claude/hooks/handoff_guard.py:75`).
- [x] T3 Runtime — Decide how to treat the gate discrepancy: `check-gates.json` records an advisory T3 failure at a transient split-proposal path, while `PYTHONPATH=src python3 -m unittest discover -s tests` passed locally and the recorded temp path is not inspectable (`check-gates.json:69`).
- [x] T4 Contribution — Decide whether to accept the recorded T4 pass, because the reviewer inputs omit `commit-msg.txt` and `pr-description.md`, so I could not rerun the contribution gate against the actual published artifacts (`check-gates.json:78`).
- [x] T5 Judgment — Decide whether the chosen deliberate-abandon interface is acceptable, because the brief left escape-hatch shape as an open human judgment and the patch concretizes it as `--abandon "<why>"` (`brief.md:105`, `template/.claude/hooks/handoff_guard.py:104`).
- [x] Validation — fitness-to-purpose — Human sign-off must decide whether this terminal workflow is fit for actual interactive use; I verified offline tests only, not a live Claude Code Stop-hook session (`brief.md:16`).

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
- By / date: Eduard Ralph / 2026-08-01

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
- The deliberate-abandon escape hatch should be a rendered slash command (e.g. `/abandon "<why>"`), not a raw `python3 .claude/hooks/handoff_guard.py --abandon` invocation — follow-up on the #331 interface.
