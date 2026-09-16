# Result — issue 480 / plan-advisory-reviews-what-the-session-wrote

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: after a **single-bundle** Plan session, the #301 plan-advisory pass reviews the
  bundle `do_plan` was handed, not the briefs the session wrote. `do_plan`
  (`template/src/pdca_harness/leaves.py:904-927`) ends with `run_plan_advisory(d, cfg)`
  (`:927`), which is `run_plan_advisory_batch(cfg, [d])` (`:3404-3406`). A split accepted
  inside that session (`pdca split <id> --accept`) creates child bundles the pass never
  sees. Two shapes:
  1. **Parent keeps its brief** (split after a rejected attempt: `split.accept` archives with
     `include_brief=False`, `split.py:837-838`). The pass reviews the superseded parent brief
     on a bundle already marked terminal (`close-disposition` = `split`, `split.py:862`;
     `state.CLOSE_MARKER`, `state.py:44`). If it finds anything, the revision session edits a
     brief nobody will build. It writes a `plan-advisory-*.md` and a benefit record, so it
     *looks* like coverage.
  2. **Parent has no brief** (split after `iterate-plan` cleared it). The filter at
     `leaves.py:3364-3365` drops it and the pass silently does nothing.
  The children get no second chance: `--accept` materialises them `PLANNED`, so
  `flow._plan_if_unplanned` returns early (`flow.py:367-368`) and never reaches the pass.
  `do_plan_batch` already selects by what the session produced (content-hash snapshot
  `leaves.py:1073-1075`, `fresh` at `:1129-1133`), so only the single-bundle path loses the
  children. But the batch path has the terminal-parent problem too: a parent briefed and then
  split in the same batch session is "fresh" and gets reviewed.
  Hit twice on getwyrd/wyrd (#711 → #721/#722, then #721 → #776/#777). Reviewing by hand
  afterwards found material errors in the children each time (a false race-injection recipe,
  a wrong size constant that would have re-created the defect the lineage exists to remove).
- Success criterion: offline, with a stub plan-advisory leaf configured:
  (a) a single-bundle `leaves.do_plan(parent, cfg)` whose session writes child bundles with
      authored briefs and marks the parent split produces a plan-advisory artifact and a
      `plan-advisory-benefit.json` on **every child**, and **none** on the parent. This holds
      for both shapes: parent brief kept (shape 1) and parent with no brief (shape 2);
  (b) a bundle carrying `close-disposition` is never reviewed on **either** Plan path
      (`do_plan` or `do_plan_batch`), and so can never trigger the revision session;
  (c) the single-bundle path selects the same way the batch path does. A bundle whose brief
      existed before the session and is byte-identical after it is **not** reviewed; one the
      session rewrote **is**. A placeholder brief is still never reviewed (`leaves.py:3364-3365`);
  (d) the existing plan-advisory suite (`template/tests/test_plan_advisory.py`) passes
      unchanged, and with no `[[leaves.plan_advisory]]` configured the Plan beat stays a no-op
      (`test_default_off_leaves_the_plan_beat_untouched`, `:58-63`).
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: make the plan-advisory selection after a Plan session cover what the session
  produced and skip terminal bundles, on both Plan paths, with one selection rule shared by
  `do_plan` and `do_plan_batch`. Confined to `template/src/pdca_harness/leaves.py`.
  / out of scope: children of a split accepted **outside** any Plan session (e.g. from a
  sign-off session or a shell), which never enter Plan at all. That is a separate gap; note
  it in build-notes if seen, don't fix it here. Also out: the revision prompt wording
  (`_plan_revision_prompt`, `:3337-3351`); following `split-lineage.json` to find children
  (the content-hash selection makes it unnecessary); `split.py`, `flow.py`; any prompt string.

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

Review issue #480: ensure Plan advisory review covers newly authored or rewritten child briefs after a session splits a bundle, and excludes terminal parents on both Plan paths.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The success criteria distinguish both split-parent shapes, unchanged versus rewritten briefs, terminal exclusion, and default-off behavior; the regression exercises the specified production entry point (`brief.md:24`; `target/template/tests/test_plan_advisory_split_children.py:66`). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing the production fix reproduced missing child reviews in both shapes and an unwanted terminal review: three assertion failures, with no import or setup failure (`review-red.log:44`; `target/template/tests/test_plan_advisory_split_children.py:76`). |
| C3 Change | PASS | The change stays within the three authorized functions plus shared helpers and the specified new test; session handoff blocks and prompts remain unchanged, preserving the adjacent work's boundary (`target/template/src/pdca_harness/leaves.py:923`; `target/template/src/pdca_harness/leaves.py:1139`). |
| C4 Verification (red→green) | PASS | Restoring the same production fix made all four regressions pass, alongside 25 existing advisory tests; supplemental checks confirmed unchanged-primary and batch split behavior (`review-green.log:33`; `review-green.log:39`; `review-selection.log:1`). |
| C5 Causal adequacy | PASS | Selecting session-produced briefs removes the wrong-bundle cause; terminal exclusion enforces lifecycle eligibility rather than probing an assumed capability, and real production calls reproduce the forbidden failure before the fix (`target/template/src/pdca_harness/leaves.py:939`; `target/template/src/pdca_harness/leaves.py:3386`; `target/template/src/pdca_harness/leaves.py:3405`). |
| T1 Structure | PASS | Both Plan paths share one freshness rule and one eligibility filter, preventing divergent review coverage without changing public APIs or introducing dependencies (`target/template/src/pdca_harness/leaves.py:3360`; `target/template/src/pdca_harness/leaves.py:3372`; `target/template/src/pdca_harness/leaves.py:3405`). |
| T2 Shape | PASS | Independent docs lint, site rendering, internal-link audit, and whitespace check passed; the frozen host-parity log also records successful lint and rendering (`review-docs-lint.log:1`; `review-docs-render.log:3`; `gate-logs/host-ci-docs.log:10`). |
| T3 Runtime | PASS | Independent driver execution passed 1,792 tests with two skips; frozen evidence records all 24 root render/update tests passing, which cannot be repeated here without Copier and release history (`review-suite.log:1103`; `gate-logs/T3-suite.log:40`; `gate-logs/T3-suite.log:54`). |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; their substantive audit is deferred to the mandatory publish gate (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Confirm affected-path prior art across merged and closed/rejected work before sign-off — the brief documents path-based merged history but only issue-number closed-PR searching, and the supplied target has one synthetic commit and no remotes (`brief.md:86`; `review-prior-art.log:1`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether demonstrated offline coverage of session-created children and terminal-parent exclusion meets the operational need — actual interactive model sessions were not exercised, and splits outside Plan remain explicitly outside this fix (`target/template/tests/test_plan_advisory_split_children.py:47`; `brief.md:67`; `review-selection.log:2`). |

## Evidence and limits

- **No patch defects found.** Target source was readable and the patch was present. The production change was stashed for the red leg and restored before the green leg; source and test contents were not edited by the review.
- **Independent reproduction:** `cd target/template && PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_plan_advisory_split_children.py' -v` failed three of four cases with the production change stashed. After restoration, discovery with `-p 'test_plan_advisory*.py'` passed all 29 cases. Logs: `review-red.log`, `review-green.log`.
- **Independent runtime/scanners:** full driver discovery passed; the production-import scanner confirmed the added test imports `pdca_harness`; docs lint and the CI renderer's `--check` passed. Supplemental execution confirmed an unchanged primary brief is skipped and a batch session creating two children plus a freshly briefed terminal parent reviews only the children (`review-selection.log`).
- **Frozen gate evidence:** all six supplied logs were inspected. C4's captured three-failure red leg and four-test green leg agree with the independent rerun. C5's import heuristic agrees with the scanner and direct production execution. Both docs logs show successful lint/render/link auditing. T3 records 24 root tests passing and 1,792 driver tests passing with two skips. This sandbox lacks importable Copier and release tags, so root render/update coverage is supported by the frozen gate output, not claimed as independently rerun. The gate did exercise that dependency; this is a local rerun limitation, not an undischarged dependency or patch defect.
- **Prior art:** inspection of the target's affected-path history returns only its synthetic pre-fix base; there are no remote definitions or release tags. The supplied brief's closed-work search does not establish a search by affected file path. Human confirmation remains owed for `template/src/pdca_harness/leaves.py` and `template/tests/test_plan_advisory_split_children.py` across merged and closed/rejected work.
- **Human-only rules:** the available `target/template/docs/INTEGRATION.md.jinja:80` leaves project-specific human-only items as a TODO; no additional enumerated items were supplied. The two NEEDS-HUMAN decisions above remain advisory and do not gate accept.

### Advisory — code-review

# Check advisory — code review (correctness + reuse/efficiency)

## Findings

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/leaves.py:917` (`do_plan`, `briefed_before = _brief_snapshot(cfg)`): this now runs on **every** `do_plan` call, unconditionally, before the planner even runs — it globs the whole `bundle_root`, reads every non-placeholder `brief.md`, and sha256-hashes each one. Before this patch, the equivalent work only happened inside `run_plan_advisory_batch`, which bails out in its first line (`if not cfg.plan_advisory_leaves: return`, `leaves.py:3401-3402`) — so with advisory unconfigured (the default: brief.md explicitly says "no-op unless configured" and success criterion (d) requires the no-op case stay a no-op) the old single-bundle path did near-zero work. `do_plan` is called once per still-UNPLANNED bundle in the serial per-wave pre-pass (`flow.py:493`, `_plan_if_unplanned`), so on a project whose `bundle_root` has accumulated many completed/published bundles over time, every wave now pays an O(n) full-root scan+hash per newly-planned bundle it processes, purely to build an argument list that gets thrown away by the early return one call later. `do_plan_batch` already paid this cost unconditionally pre-patch (not a regression there — the patch only refactored it into the same `_brief_snapshot` helper), but `do_plan` did not, and now does. A one-line guard mirroring `run_plan_advisory_batch`'s own check — `if not cfg.plan_advisory_leaves: return` (or `run_plan_advisory_batch(cfg, [])`) — before computing the snapshot in `do_plan` would restore the old near-free cost on the common default-off path without touching the split-children behavior this bundle is about.

## Everything else

No other correctness bugs found. The refactor correctly consolidates the two previously-duplicated glob/hash selection blocks (`do_plan_batch`'s old `briefed_before`/`fresh` locals) into `_brief_snapshot`/`_fresh_plan_briefs`, shared by both Plan paths as the brief asks — good reuse, not a re-implementation of existing logic. The new `close-disposition` guard in `run_plan_advisory_batch` (`leaves.py:3406-3407`) reads the same marker file split.py writes (`state.CLOSE_MARKER` = `"close-disposition"`, `split.py:862`), the diff stays confined to the three functions plus the two new helpers as the ordering note in the brief requires (the `handoff.session(...)` blocks and prompt strings are untouched), and the C4 verify log shows genuine red-then-green on the new test (3 of 4 cases fail with the fix reverted, the 4th — which only re-asserts pre-existing single-bundle selection behavior, not the split-children fix — correctly passes both ways). `run_plan_advisory` (the single-bundle wrapper) is left in place and still exercised directly by the untouched `test_plan_advisory.py` suite, so it isn't dead code despite `do_plan` no longer calling it.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — Confirm affected-path prior art across merged and closed/rejected work before sign-off — the brief documents path-based merged history but only issue-number closed-PR searching, and the supplied target has one synthetic commit and no remotes (`brief.md:86`; `review-prior-art.log:1`).
- [x] Validation — fitness-to-purpose — Decide whether demonstrated offline coverage of session-created children and terminal-parent exclusion meets the operational need — actual interactive model sessions were not exercised, and splits outside Plan remain explicitly outside this fix (`target/template/tests/test_plan_advisory_split_children.py:47`; `brief.md:67`; `review-selection.log:2`).
- [x] `template/src/pdca_harness/leaves.py:917` (`do_plan`, `briefed_before = _brief_snapshot(cfg)`): this now runs on **every** `do_plan` call, unconditionally, before the planner even runs — it globs the whole `bundle_root`, reads every non-placeholder `brief.md`, and sha256-hashes each one. Before this patch, the equivalent work only happened inside `run_plan_advisory_batch`, which bails out in its first line (`if not cfg.plan_advisory_leaves: return`, `leaves.py:3401-3402`) — so with advisory unconfigured (the default: brief.md explicitly says "no-op unless configured" and success criterion (d) requires the no-op case stay a no-op) the old single-bundle path did near-zero work. `do_plan` is called once per still-UNPLANNED bundle in the serial per-wave pre-pass (`flow.py:493`, `_plan_if_unplanned`), so on a project whose `bundle_root` has accumulated many completed/published bundles over time, every wave now pays an O(n) full-root scan+hash per newly-planned bundle it processes, purely to build an argument list that gets thrown away by the early return one call later. `do_plan_batch` already paid this cost unconditionally pre-patch (not a regression there — the patch only refactored it into the same `_brief_snapshot` helper), but `do_plan` did not, and now does. A one-line guard mirroring `run_plan_advisory_batch`'s own check — `if not cfg.plan_advisory_leaves: return` (or `run_plan_advisory_batch(cfg, [])`) — before computing the snapshot in `do_plan` would restore the old near-free cost on the common default-off path without touching the split-children behavior this bundle is about.

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
- By / date: Eduard Ralph / 2026-09-15

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
- do_plan: skip `_brief_snapshot` when no `[[leaves.plan_advisory]]` is configured (one-line guard at leaves.py:917; the scan is wasted work when review is off, ~2.5 ms on 61 briefs today).
