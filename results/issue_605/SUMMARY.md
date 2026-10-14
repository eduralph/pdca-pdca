# Result — issue 605 / check-decorrelation-note-not-deferred

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: Under `[leaves.advisory_selection] mode = "vendor-complement"`, `leaves._select_advisory` (`template/src/pdca_harness/leaves.py:3645-3679`) deletes the previous round's note (`:3655`) and, when it cannot pick a different-vendor advisory, writes a fresh one with `_decorrelation_note` (`:3637-3642`, written at `:3675`) as `check-advisory-decorrelation.md`. The note describes THAT Check's leaf selection ("Confirm the review's independence by hand"), not the patch. But `assemble.collect_needs_human` reads it like any advisory artifact (`template/src/pdca_harness/assemble.py:405-409`). It is not recognised as a no-verdict row (only `_is_advisory_unavailable`, `assemble.py:229-234`, is), so it is an ordinary HUMAN item, and the #409 auto-iterate defers it into the ledger (`autoiterate.deferrable`, `template/src/pdca_harness/autoiterate.py:300-326`, skips only `no_verdict` rows). Example: round 1 has no `loop-telemetry.json`, so the note says the builder family is "unknown" and gets deferred. Round 2 knows the family and writes no note. The handover §6 still asks the human to confirm the independence of a review of a patch that was thrown away (`assemble._deferred_needs_human`, `assemble.py:571-598`, adds every ledger entry).
- Success criterion: With the patch: (1) a bundle whose round-1 Check items include an IMPL finding and the Check decorrelation note goes through an auto-iterate decision (`autoiterate.write_decision`) and an iterate-do (`driver.advance`). Its round-2 Check writes no `check-advisory-decorrelation.md`. Round 2's assembled §6 then has no row carrying the decorrelation note's text, and `autoiterate.deferred(d)` does not hold it. (2) Same flow, but round 2's Check writes the note again through `leaves._select_advisory` under a `mode = "vendor-complement"` config with no `loop-telemetry.json` (the real writer, not a hand-written file): round 2's §6 shows it once, as an open `- [ ]` row that blocks accept. Premise for both cases: the round-1 note is gone from the bundle before round 2, because the iterate archives `check-advisory-*.md` (`state.DOWNSTREAM_GLOBS`, `state.py:155`) and `_select_advisory` also unlinks it (`leaves.py:3655`); the test asserts the file is absent after `driver.advance` rather than assuming it. (3) The flow's auto-iterate notice (`flow.py:379-383`) no longer calls the note a "review/gate row with no verdict" (see Scope for the wording). Pre-fix, case (1)'s §6 carries the round-1 note from the ledger. That is the RED.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: Treat the Check-side decorrelation note as a row about this Check's own run, so auto-iterate never defers it and it appears in a round's §6 only when that round emitted it. Use the existing `NeedsHumanItem.no_verdict` flag rather than a new one, and widen its documented meaning to "a row about this Check's own run (no verdict, or the Check's own leaf selection)". This is in scope: update the comment at `assemble.py:45-50`, the `deferrable` docstring at `autoiterate.py:307-313`, and the flow notice at `flow.py:379-383`, so a decorrelation note is not counted as "review/gate row(s) with no verdict" (e.g. "row(s) about this Check's own run left for the next Check to re-check"). / out of scope: the plan-side note (`_plan_decorrelation_note`, `leaves.py:3838-3841`: plan advisory is not re-run on iterate-do, and its carry is #603); changing when or how the note is written, or its text; the advisory-selection policy itself; cleaning ledgers already written by older versions.

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: pass — C4 PASS — red without the fix, green with it
- C5 added test exercises production, not a copy: pass — patch adds no new test file — nothing to assert

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

Review issue #605: keep Check decorrelation notes out of the deferral ledger so later rounds show only their own outstanding reviewer-independence concern.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief defines observable disappearance, recurrence, accept blocking, and notice wording, with historical-ledger cleanup explicitly excluded; the tests cover these outcomes (`brief.md:11`, `brief.md:20`, `template/tests/test_autoiterate.py:2521`). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing the production changes while retaining the tests produced three assertion failures, including the obsolete round-1 note returning in round-2 §6 (`review-red.log:9`, `template/tests/test_autoiterate.py:2530`). |
| C3 Change | PASS | The five-file patch addresses the specified classification and its documentation/notice consistently, without changing advisory-selection policy or plan-side handling (`template/src/pdca_harness/assemble.py:413`, `template/src/pdca_harness/flow.py:382`, `docs/07-crosscutting.md:464`). |
| C4 Verification (red→green) | PASS | Restoring the same production changes makes all 148 tests pass through direct script execution, including the three regressions; the previous test-placement defect is resolved (`review-green.log:55`, `review-green.log:304`, `template/tests/test_autoiterate.py:2578`). |
| C5 Causal adequacy | PASS | The actual cause is incorrect eligibility for deferral: exercising the real selection, iteration, assembly, and accept paths proves stale notes disappear while fresh notes still block accept and ordinary findings remain deferred; no capability probe or symptom guard is added (`template/src/pdca_harness/assemble.py:419`, `template/tests/test_autoiterate.py:2491`, `template/tests/test_autoiterate.py:2534`, `template/tests/test_autoiterate.py:2551`). |
| T1 Structure | PASS | The existing shared classification flag controls deferral and notice counts, avoiding a second ledger policy or changed artifact schema (`template/src/pdca_harness/assemble.py:56`, `template/src/pdca_harness/autoiterate.py:325`, `template/src/pdca_harness/flow.py:379`). |
| T2 Shape | PASS | Independent docs lint, 22-page rendering/internal-link audit, and git diff whitespace checks pass; these match the host workflow's checks (`review-docs-lint.log:1`, `review-docs-render.log:3`, `.github/workflows/docs-check.yml:33`). |
| T3 Runtime | PASS | Independent offline discovery passes 2,426 tests with two skips; frozen evidence additionally shows all 24 root render/update tests passed, including actual Copier cases (`gate-logs/T3-suite.log:38`, `gate-logs/T3-suite.log:54`; independent run recorded in `review-suite.log`). |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the substantive PR/commit audit is owed at publish, as the deferred gate explicitly records (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Confirm merged and closed/rejected prior art for every affected path before accepting novelty — the brief records checks for assemble/autoiterate/leaves but omits changed flow/tests/docs paths, and this target has one snapshot commit, no remotes, and no closed-PR evidence to resolve that gap (`brief.md:25`, `docs/07-crosscutting.md:464`, `template/src/pdca_harness/flow.py:382`, `template/tests/test_autoiterate.py:2453`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Accept whether review-independence obligations should expire with their Check while newly emitted notes still require clearance — automated lifecycle and accept-blocking evidence establishes behavior, but the adequacy of that human-review policy remains a sign-off decision (`docs/07-crosscutting.md:464`, `template/tests/test_autoiterate.py:2538`). |

Source citations without the `target/` prefix refer to the inspected `$PDCA_TARGET` tree (`/tmp/pdca-review-8x8ixbzz/target`); brief, patch, and log citations refer to this review bundle. The target was readable and matched the patch; no stale-target fallback was needed.

Independent verification used `git stash push` scoped to the four production/documentation files, leaving the patched test file in place. From `target/template`, `PYTHONPATH=src python3 tests/test_autoiterate.py CheckDecorrelationNoteIsNotDeferred -v` failed all three cases on the pre-fix code. After `git stash pop`, `PYTHONPATH=src python3 tests/test_autoiterate.py -v` passed all 148 tests, including the new class. The target diff was byte-for-byte identical before and after this operation. `PYTHONPATH=src python3 -m unittest discover -s tests` then passed 2,426 tests with two skips. Temporary test files were rooted inside this sandbox.

The documentation validators were rerun from the target root: `python3 docs/publishing/tools/lint_docs.py` and `python3 docs/publishing/tools/render_site.py --check --out /tmp/pdca-review-8x8ixbzz/review-site`. Both passed. The available production-import scanner was also rerun; its new-file-only predicate does not substantively audit this edit to an existing test file. Accordingly, C5 rests on direct inspection and the independently reproduced behavioral failures, not that scanner's success message (`gate-logs/C5-prod-path.log:10`).

Instance-scoped gate wrappers were adjudicated using their frozen logs and the equivalent available commands above. Copier is not importable in this reviewer environment, so the root render/update suite was not independently rerun; its frozen log shows real render and update cases passing, not skips (`gate-logs/T3-suite.log:38`). This is a local rerun limitation, not an undischarged dependency of the demonstrated pure-Python fix. The stub builder/reviewer fixtures still reproduce the forbidden stale-note outcome against pre-fix production code.

The prior-art investigation ran `git log --all -- <affected paths>`, `git rev-list --count --all`, and `git remote -v` inside the supplied target: only the synthetic pre-fix snapshot exists and no remote is configured. No other checkout was consulted. The available integration template lists project-specific human-only items as TODO rather than enumerating additional decisions (`template/docs/INTEGRATION.md.jinja:80`). No builder-fixable concern was found.

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — issue 605 (check-decorrelation-note-not-deferred)

I found no correctness bugs in this patch, and nothing needs human adjudication. The fix is small, follows the existing pattern in the same function, and the tests run the real writer and the real iterate.

- `template/src/pdca_harness/assemble.py:413-419` — Correct. The note is marked `no_verdict` after it is parsed, keyed on the artifact stem `decorrelation`. This mirrors the missing-review pattern at `assemble.py:405-407`. It also avoids the `no_verdict=` callback, which `_items_from_artifact` only calls for placeholder text, and `_decorrelation_note` (`leaves.py:3637-3642`) writes none. The only consumers of the flag are `autoiterate.py:325` (skip deferral) and `flow.py:379` (the notice count), and both should treat the note this way. Plan-side `plan-advisory-decorrelation.md` does not match the `check-advisory-*.md` glob, so it stays out of scope as the brief requires.
- `template/tests/test_autoiterate.py:2453` — Last round's issue is fixed. The new class `CheckDecorrelationNoteIsNotDeferred` now sits above the `if __name__ == "__main__"` guard (`:2578`), so the tests also run when the file is run as a script. The tests drive the real `leaves.run_advisory_leaves` / `_select_advisory`, `autoiterate.write_decision`, `driver.advance` and `driver.run_issue`. They assert the round-1 note is gone before round 2 (`:2482-2483` of the diff's class) instead of assuming it. They also check that an ordinary advisory finding is still deferred, which shows the fix is narrow. The C4 log shows red without the fix and green with it. The T3 log shows 2426 tests OK.
- `template/tests/test_autoiterate.py:769-773` — Minor wording nit, no action required. The docstring of the existing test `test_only_a_review_or_gate_with_no_verdict_is_left_to_the_next_check` still says only "the row the harness writes itself because a review or a gate returned nothing" counts, and that "a finding is never one of them". After this patch the decorrelation note (a NEEDS-HUMAN bullet the harness writes) also counts. The code is right and only the comment is a little stale. If the builder touches the file again, a short "(and the Check decorrelation note, #605)" would keep it in line with the widened meaning at `assemble.py:45-56`.
- Reuse and simplification: nothing to flag. The patch reuses the existing `no_verdict` field and the `_replace` idiom instead of adding a new flag, and adds no work on any hot path.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — Confirm merged and closed/rejected prior art for every affected path before accepting novelty — the brief records checks for assemble/autoiterate/leaves but omits changed flow/tests/docs paths, and this target has one snapshot commit, no remotes, and no closed-PR evidence to resolve that gap (`brief.md:25`, `docs/07-crosscutting.md:464`, `template/src/pdca_harness/flow.py:382`, `template/tests/test_autoiterate.py:2453`).
- [x] Validation — fitness-to-purpose — Accept whether review-independence obligations should expire with their Check while newly emitted notes still require clearance — automated lifecycle and accept-blocking evidence establishes behavior, but the adequacy of that human-review policy remains a sign-off decision (`docs/07-crosscutting.md:464`, `template/tests/test_autoiterate.py:2538`).
- [x] **The brief points Do at a callsite that cannot carry the fix.** It says (`Citations expected`) that the note "should get the same treatment" as `assemble.py:405-409`, i.e. via the `no_verdict=` callback of `_items_from_artifact`. But that callback only runs for a **placeholder**. `assemble.py:380-381` reads `if not label: return items`, and the label is non-empty only when `leaf_status(text)` finds a `pdca:leaf-status` marker (`assemble.py:263-264`, `:374`). `_decorrelation_note` (`leaves.py:3641-3642`) writes no marker, so a predicate added to the lambda at `:409` is never called for the note, and the fix silently does nothing. The pattern that actually fits is the post-hoc `_replace(no_verdict=True)` at `assemble.py:402-404`, applied when `p == leaves.advisory_artifact(d, "decorrelation")`, or with the stem check `leaf == "decorrelation"` in the loop at `:405-406`. The brief should name that, or Do will spend a round finding out on its own. The RED test would catch the mistake, but only after a wasted build.
- [x] **Reusing `no_verdict` stretches its documented meaning, which the brief treats as already covering the note.** The `Invariant` line says the note "fits that rule but is not marked by it". The rule's own text is narrower. `assemble.py:47-48` says the flag is for "a review or a gate that gave NO verdict this round". `autoiterate.py:307-309` lists "the review missing or a placeholder, an advisory leaf's placeholder, a gate that could not run". The decorrelation note is a selection lapse, and the review behind it **did** give a verdict. Marking it `no_verdict` also changes the operator message: `flow.py:379-383` counts every `no_verdict` row as "review/gate row(s) with no verdict left for the next Check to re-run", so a decorrelation note would be misreported there. The brief should choose one:
- [x] **Ordering is declared as a conflict but described as a dependency.** `Ordering note` says "603 first, and 605 builds on its result", but the brief declares only `Conflicts with: 603`, with no `Depends on` / `Stacks on`, and no `dependency-state.json` was supplied. Nothing in this fix needs 603's code: it changes the Check-advisory loop (`assemble.py:405-409`) and `deferrable`, while 603 is the plan-advisory carry. So "builds on its result" is either wrong and should be dropped, or real and should be a declared `Stacks on: 603` that the driver can enforce. Right now a scheduler that only reads the declared fields could run 605 on a base that the note claims is required.
- [x] **Success criterion (2) needs a pinned premise.** "Round 2's §6 shows it once, as an open `- [ ]` row that blocks accept" assumes the round-1 note is gone from the bundle before round 2's Check. That holds today only because `_select_advisory` unlinks it at `leaves.py:3655`, and only under `mode = "vendor-complement"` (`:3653-3655`). The test should use the vendor-complement config and drive the note through `_select_advisory`, not hand-write the file in both rounds. Otherwise case (2) passes whether or not the old note survives, and the "shows it once" leg proves nothing about dedup against a stale ledger entry.
- [x] T5 Judgment — Confirm merged and closed/rejected prior art for all four affected paths, including `flow.py` and `test_autoiterate.py` — the brief records searches for assemble/autoiterate/leaves, but this single-commit, remote-free snapshot cannot independently establish completeness or rejection history (`brief.md:25`, `target/template/src/pdca_harness/flow.py:382`, `target/template/tests/test_autoiterate.py:2299`).

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
- By / date: Eduard Ralph / 2026-10-14

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 4 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
