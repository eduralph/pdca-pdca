# Result — issue 780 / standalone-signoff-consumes-decision

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: 
- Success criterion: 
  - (a) A bundle at AWAITING_SIGNOFF with `signoff-decision` = `accept` on disk. Run
    `cli._signoff` with `--iterate-plan` (leaves in stub mode). After it returns,
    `signoff-decision` does not exist in the bundle directory.
  - (b) End to end: after (a), bring the bundle back to AWAITING_SIGNOFF (stub Plan/Do/Check,
    or write a fresh SUMMARY) and CLEAR its §6 on the rebuilt SUMMARY (as
    `template/tests/test_signoff_orphan.py:171` does with `_clear_needs_human(d)`), so C6
    would permit a stale `accept`. Assert that precondition in the test
    (`signoff.open_needs_human(d / "SUMMARY.md") == []`) before driving. Then drive
    `flow._drive_wave(..., max_passes=1)` with `cfg.auto_iterate` off (the
    `_stub_config(..., auto_iterate=False)` pattern, `test_signoff_orphan.py:59`) and a
    stubbed `leaves.run_signoff_batch` that records the bundles it is offered and writes
    nothing. The bundle is still AWAITING_SIGNOFF, it is NOT COMPLETE, and
    `run_signoff_batch` was offered it (a fresh session). Red on `main`: the pre-apply
    (flow.py:2516-2522) applies the stale `accept` and the bundle reaches COMPLETE with no
    session. (With §6 left open the leg would pass on `main` too, via C6 — so §6 must be
    clear.)
  - (c) A standalone `--accept` refused by C6 (`cli.py:1515-1520`, returns before
    `signoff.record`) leaves `signoff-decision` untouched — nothing was recorded, so
    nothing is consumed. A `signoff.record` that raises `ValueError` (`cli.py:1532-1537`)
    also leaves it untouched.
  - (d) Each recording action (`accept`, `iterate-do`, `iterate-plan`, `discontinue`)
    removes the file. Parametrize.
  - (e) Ordering: with `driver.run_issue` patched to raise (and, separately, to return a
    held state so `_signoff` returns 1, `cli.py:1542-1549`), the `signoff-decision` file is
    already gone — it is deleted after `signoff.record` succeeds and BEFORE
    `driver.run_issue`, so a failed or held transition cannot leave the stale decision.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: 

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: pass — C4 PASS — red without the fix, green with it
- C5 added test exercises production, not a copy: pass — 1 added driver-suite test(s) import the production package 'pdca_harness'

## 4. Conformance (Check — stack)
- T1 Structure: none — (no gate configured)
- T2 shape: docs lint + site render link audit: pass — docs lint clean, site render + link audit clean
- T2 host CI parity: target docs-check.yml on the pushed tree: pass — host CI parity on the patched tree — docs lint clean, site render + link audit clean
- T3 runtime: render/update-compat + offline driver suites: pass — root suite OK, driver suite OK
- T4 PR body has a user-impact opener + tracker id in both artifacts: deferred — pr-description.md not drafted yet — the substantive T4 audit of the contribution artifacts runs at publish
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

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

### Advisory — code-review

# Advisory code review — issue #780 (standalone sign-off consumes `signoff-decision`)

No findings need a human. The diff is clean on both lenses: correctness and reuse/simplification.

## Correctness

- `template/src/pdca_harness/cli.py:1542` — the new `unlink(missing_ok=True)` runs only after `signoff.record` succeeds (`cli.py:1529-1537`). It runs before `driver.run_issue` (`cli.py:1545`). The C6 refusal (`cli.py:1515-1520`) and the `ValueError` return (`cli.py:1532-1537`) both exit before it, so nothing is consumed when nothing was recorded. This is the same call `flow._apply_decision` makes (`template/src/pdca_harness/flow.py:205`). `missing_ok=True` covers the usual case, where no stale file exists. No off-by-one, leak or ordering problem found.
- `template/src/pdca_harness/cli.py:1542` — as the brief requires, the CLI does not copy the `state.SESSION_CARRY` capture from `flow.py:201-204`. The CLI takes its rationale from `--delta`, so deleting the file loses nothing the CLI path used. Any session rationale lines in a stale file are dropped, but that is the point of the fix and is out of scope here.

## Tests

- `template/tests/test_signoff_consumes_decision.py:100-189` — every brief leg is covered: (a) iterate-plan, (d) all four actions with `signoff.record` wrapped so a decision is actually recorded, (b) end to end with §6 cleared and the precondition asserted, (c) C6 refusal and `ValueError`, (e) a raising and a held `run_issue`. The tests call production `cli._signoff`, `flow._drive_wave` and `driver.run_issue` (C5 passes). `gate-logs/C4-verify.log` shows the tests fail without the fix, including the leg (b) `'COMPLETE' == 'COMPLETE'` failure, and pass with it.
- `template/tests/test_signoff_consumes_decision.py:37-62` — `_stub_config` and `_clear_needs_human` copy the ones in `test_signoff_orphan.py`. Leaving them is fine: 26 test files each define their own `_stub_config`, and no test imports helpers from another test. That is the house style, so this is not worth changing.

## Reuse / simplification / efficiency

- Nothing to raise. The fix is one line on a cold CLI path. A shared "record and consume" helper used by both `cli._signoff` and `flow._apply_decision` could stop the two paths drifting apart again. The brief rules out touching `flow._apply_decision`, so this is only a note, not a finding.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — Confirm no merged or closed/rejected work supersedes this fix on the affected paths — the disposable snapshot exposes one base commit and no remotes, so the supplied #395 provenance cannot settle prior art independently (review-scanners.log:36).
- [x] Validation — fitness-to-purpose — Decide whether the demonstrated decision lifetime meets the intended approval workflow — the replay proves that a rebuilt attempt receives a fresh session, but fitness remains the human sign-off decision (template/tests/test_signoff_consumes_decision.py:150).
- [x] **There is no tracker record to check the problem statement against.** The sandbox has only `brief.md`: no `notes.json`, no `sources/`, no `dependency-state.json`. The only provenance is "found as a sign-off finding on #395 iteration 7 (`results/issue_395/iteration-v9/brief.md:122`)", and nothing in the inputs lets me check it. The brief's own text doesn't match itself either: it says "iteration 7" but cites an `iteration-v9/` path. The human should confirm the source finding and which iteration it came from. The bug itself is real in code, so this is about provenance, not substance.
- [x] **Leg (b) can pass on `main`, which contradicts "Red on `main`", unless §6 is cleared.** It says "bring the bundle back to AWAITING_SIGNOFF (stub Plan/Do/Check, **or write a fresh SUMMARY**)". If that fresh or rebuilt SUMMARY keeps any open `- [ ]` §6 row, then on `main` the stale `accept` is refused by C6 (`flow.py:177-179`, returns `"blocked"`). `flow.py:2521-2522` then offers the bundle a session anyway, so every assertion in (b) holds on `main` too. The existing test shows exactly this: `test_signoff_orphan.py:191-207` (`test_c6_refused_accept_still_gets_a_fresh_session`) leaves §6 open and gets a session. The reproduction has the same gap: "goes straight to COMPLETE" only happens if the rebuilt §6 is clear. The brief should require leg (b) to clear §6 on the rebuilt SUMMARY (as `test_signoff_orphan.py:171` does with `_clear_needs_human(d)`) before driving the wave. It should also require the test to assert that the main-side precondition holds.
- [x] **Leg (b) leaves out the wave settings it depends on.** "The bundle is still AWAITING_SIGNOFF" depends on two things. First, `max_passes=1`, as the cited pattern uses at `test_signoff_orphan.py:179`; otherwise later passes keep looping. Second, `auto_iterate` being off: `_maybe_auto_iterate` (`flow.py:327-338`) can send a bundle with no decision and an IMPL §6 item to ITERATE_DO, which breaks the AWAITING_SIGNOFF assertion for a reason unrelated to the fix. The brief should state both, so the green leg proves consumption and not some incidental wave behaviour.
- [x] **The ordering is stated but not tested.** Scope says delete "after `signoff.record` succeeds and before `driver.run_issue`". No leg checks that ordering, though it matters. If the file were removed only after `run_issue`, a held result (`cli.py:1542-1549`, `return 1`) or an exception would leave the stale decision behind. Legs (a) and (d) only check the file after `_signoff` returns normally. Either add a leg where `driver.run_issue` is patched to raise or return a held state, and assert the file is already gone, or drop "before `driver.run_issue`" from the brief as an unverified constraint.

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
- By / date: Eduard Ralph / 2026-10-30

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 4 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
- Follow-up: add a shared "record and consume" helper used by both `cli._signoff` and `flow._apply_decision`, so the two sign-off paths can't drift apart again (code-review note, out of scope for #780).
