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

Prevent obsolete Check advisory-decorrelation notes from surviving auto-iteration, while retaining a current round’s note as an open sign-off item (issue #605).

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The three success criteria distinguish recovered selection, recurring selection failure, and accurate notice wording; existing-ledger cleanup and Plan-side notes are explicitly excluded (`brief.md:11`, `brief.md:20`). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only production changes reproduced all three regression failures, including the obsolete round-1 note in round-2 §6 (`review-red.log:10`, `target/template/tests/test_autoiterate.py:2357`). |
| C3 Change | PASS | The four-file diff stays within the specified classification, documentation, notice, and regression-test scope; current-round findings remain collected (`target/template/src/pdca_harness/assemble.py:412`, `target/template/src/pdca_harness/flow.py:382`). |
| C4 Verification (red→green) | PASS | Restoring the production changes made all 143 auto-iteration tests pass after the independent three-test red run; no import/tool failure substitutes for reproduction (`review-green.log:118`, `review-red.log:38`). |
| C5 Causal adequacy | PASS | The wrong deferral classification is corrected at artifact ingestion; actual selection, archival, ledger, summary, and accept-blocker paths demonstrate both disappearance and renewed blocking, with no capability probe or symptom guard (`target/template/src/pdca_harness/autoiterate.py:323`, `target/template/tests/test_autoiterate.py:2320`, `target/template/tests/test_autoiterate.py:2363`). |
| T1 Structure | PASS | Existing item metadata and the single deferrability rule preserve the current-round human finding without creating a parallel ledger or suppressing unrelated advisories (`target/template/src/pdca_harness/assemble.py:407`, `target/template/src/pdca_harness/autoiterate.py:323`). |
| T2 Shape | PASS | Independent whitespace checking, docs lint, and 22-page rendering/link audit passed; frozen host-CI parity output agrees (`review-docs.log:2`, `gate-logs/host-ci-docs.log:10`). |
| T3 Runtime | PASS | Independent offline suite passed 2,372 tests with two skips; frozen evidence separately shows all 24 root render/update tests passing (`review-suite.log:1800`, `gate-logs/T3-suite.log:42`, `gate-logs/T3-suite.log:54`). |
| T4 Contribution | N/A | Contribution artifacts are intentionally drafted later; the frozen gate defers their substantive audit to the required publish rerun (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Confirm merged and closed/rejected prior art for all four affected paths, including `flow.py` and `test_autoiterate.py` — the brief records searches for assemble/autoiterate/leaves, but this single-commit, remote-free snapshot cannot independently establish completeness or rejection history (`brief.md:25`, `target/template/src/pdca_harness/flow.py:382`, `target/template/tests/test_autoiterate.py:2299`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether dropping superseded Check-selection warnings while retaining a freshly emitted warning satisfies the intended sign-off policy, accepting that already-written ledgers remain outside this fix (`brief.md:20`, `target/template/tests/test_autoiterate.py:2357`, `target/template/tests/test_autoiterate.py:2370`). |

Independent verification used the supplied disposable target, which matched the patch: production-only `git stash` preserved the new tests for the red run, and `git stash pop` restored the original diff. A reverse-apply check and final status confirmed restoration. Test temporary files and reviewer outputs stayed under the supplied sandbox.

The targeted red command was `PYTHONPATH=src:tests python3 -m unittest -v test_autoiterate.CheckDecorrelationNoteIsNotDeferred` from `target/template`; the green command was `PYTHONPATH=src python3 -m unittest discover -s tests -p test_autoiterate.py`. The full-suite rerun used the same discovery command without the filename filter. The fixture can exhibit the forbidden failure, as the independent red run demonstrated; stub model leaves do not replace the production selection or deferral logic under test.

Instance-scoped gate wrappers were adjudicated from their frozen logs and available underlying checks. The C5 scanner explicitly did no substantive scan because no new test file was added (`gate-logs/C5-prod-path.log:10`); C5 above rests on source inspection and the actual regression rerun. Copier is not installed in this reviewer interpreter, so the root suite was not independently rerun; its frozen log records executed render/update cases and 24 passing tests, rather than a skip-only claim. There is no undischarged dependency for the specified pure-Python defect.

The path-scoped local history investigation returned only synthetic base commit `7aeb5bf`; `git remote -v` returned no entries. The brief’s prior-art account therefore remains reported evidence, with the completeness decision exposed in T5. The supplied target’s integration template enumerates no additional concrete human-only items (`target/template/docs/INTEGRATION.md.jinja:80`).

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — issue 605 (check-decorrelation-note-not-deferred)

The production change is correct and small. `collect_needs_human` marks the items read from `check-advisory-decorrelation.md` as `no_verdict` after the fact (`template/src/pdca_harness/assemble.py:409-419`). This follows the missing-review pattern at `assemble.py:404-406`, as the brief asked, and does not go through the marker-only callback. The docstring, comment and notice edits match. No other file in the target still uses the old notice text ("review/gate row(s) with no verdict"). In the C4 red leg (`gate-logs/C4-verify.log:249-275`), all three new tests fail for the right reason: the note is deferred or carried into §6, and the notice wording is the old one. They are not tripping on setup. Findings:

- NEEDS-HUMAN [impl] — The new test class `CheckDecorrelationNoteIsNotDeferred` is appended *after* the `if __name__ == "__main__": unittest.main()` block (`template/tests/test_autoiterate.py:2295-2299`). Run as a script (`python tests/test_autoiterate.py`), `unittest.main()` runs and exits before the class is defined, so its three tests are silently skipped. Discovery-based runs (the C4 and T3 gates) do pick it up, which is why the gates are green. Fix: move the class above the `__main__` guard.
- Minor reuse nit (not blocking): the artifact stem `"decorrelation"` is now a bare string literal in two modules: written and unlinked at `template/src/pdca_harness/leaves.py:3641` / `:3655`, matched at `template/src/pdca_harness/assemble.py:412`. If someone renames the writer's stem, the assemble check would silently stop matching, and only these tests would catch it. A shared module-level constant (e.g. in `assemble.py` or `state.py`, which `leaves` can import without a cycle) would tie the two together. Optional.
- Edge case, pre-existing and not added by this diff: a user-configured advisory leaf with `id = "decorrelation"` would share the artifact name with the note. After this patch, its real findings would also be marked `no_verdict` and never deferred (`assemble.py:412`). This is unlikely and comes from the existing naming scheme, so I'm only noting it.

Correctness lens: no other bugs found. Efficiency: no concerns (one string compare per advisory file).

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T5 Judgment — Confirm merged and closed/rejected prior art for all four affected paths, including `flow.py` and `test_autoiterate.py` — the brief records searches for assemble/autoiterate/leaves, but this single-commit, remote-free snapshot cannot independently establish completeness or rejection history (`brief.md:25`, `target/template/src/pdca_harness/flow.py:382`, `target/template/tests/test_autoiterate.py:2299`).
- [ ] Validation — fitness-to-purpose — Decide whether dropping superseded Check-selection warnings while retaining a freshly emitted warning satisfies the intended sign-off policy, accepting that already-written ledgers remain outside this fix (`brief.md:20`, `target/template/tests/test_autoiterate.py:2357`, `target/template/tests/test_autoiterate.py:2370`).
- [ ] The new test class `CheckDecorrelationNoteIsNotDeferred` is appended *after* the `if __name__ == "__main__": unittest.main()` block (`template/tests/test_autoiterate.py:2295-2299`). Run as a script (`python tests/test_autoiterate.py`), `unittest.main()` runs and exits before the class is defined, so its three tests are silently skipped. Discovery-based runs (the C4 and T3 gates) do pick it up, which is why the gates are green. Fix: move the class above the `__main__` guard.
- [ ] **The brief points Do at a callsite that cannot carry the fix.** It says (`Citations expected`) that the note "should get the same treatment" as `assemble.py:405-409`, i.e. via the `no_verdict=` callback of `_items_from_artifact`. But that callback only runs for a **placeholder**. `assemble.py:380-381` reads `if not label: return items`, and the label is non-empty only when `leaf_status(text)` finds a `pdca:leaf-status` marker (`assemble.py:263-264`, `:374`). `_decorrelation_note` (`leaves.py:3641-3642`) writes no marker, so a predicate added to the lambda at `:409` is never called for the note, and the fix silently does nothing. The pattern that actually fits is the post-hoc `_replace(no_verdict=True)` at `assemble.py:402-404`, applied when `p == leaves.advisory_artifact(d, "decorrelation")`, or with the stem check `leaf == "decorrelation"` in the loop at `:405-406`. The brief should name that, or Do will spend a round finding out on its own. The RED test would catch the mistake, but only after a wasted build.
- [ ] **Reusing `no_verdict` stretches its documented meaning, which the brief treats as already covering the note.** The `Invariant` line says the note "fits that rule but is not marked by it". The rule's own text is narrower. `assemble.py:47-48` says the flag is for "a review or a gate that gave NO verdict this round". `autoiterate.py:307-309` lists "the review missing or a placeholder, an advisory leaf's placeholder, a gate that could not run". The decorrelation note is a selection lapse, and the review behind it **did** give a verdict. Marking it `no_verdict` also changes the operator message: `flow.py:379-383` counts every `no_verdict` row as "review/gate row(s) with no verdict left for the next Check to re-run", so a decorrelation note would be misreported there. The brief should choose one:
- [ ] **Ordering is declared as a conflict but described as a dependency.** `Ordering note` says "603 first, and 605 builds on its result", but the brief declares only `Conflicts with: 603`, with no `Depends on` / `Stacks on`, and no `dependency-state.json` was supplied. Nothing in this fix needs 603's code: it changes the Check-advisory loop (`assemble.py:405-409`) and `deferrable`, while 603 is the plan-advisory carry. So "builds on its result" is either wrong and should be dropped, or real and should be a declared `Stacks on: 603` that the driver can enforce. Right now a scheduler that only reads the declared fields could run 605 on a base that the note claims is required.
- [ ] **Success criterion (2) needs a pinned premise.** "Round 2's §6 shows it once, as an open `- [ ]` row that blocks accept" assumes the round-1 note is gone from the bundle before round 2's Check. That holds today only because `_select_advisory` unlinks it at `leaves.py:3655`, and only under `mode = "vendor-complement"` (`:3653-3655`). The test should use the vendor-complement config and drive the note through `_select_advisory`, not hand-write the file in both rounds. Otherwise case (2) passes whether or not the old note survives, and the "shows it once" leg proves nothing about dedup against a stale ledger entry.

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
- Iteration delta (if iterating): Auto-iterate (round 1): rebuilding for the implementation-level findings — The new test class `CheckDecorrelationNoteIsNotDeferred` is appended *after* the `if __name__ == "__main__": unittest.main()` block (`template/tests/test_autoiterate.py:2295-2299`). Run as a script (`python tests/test_autoiterate.py`), `unittest.main()` runs and exits before the class is defined, so its three tests are silently skipped. Discovery-based runs (the C4 and T3 gates) do pick it up, which is why the gates are green. Fix: move the class above the `__main__` guard.. Deferred, not addressed here: 5 finding(s) that need human judgment, held in deferred-findings.json for the human at handover — not build work
- By / date: auto-iterate / 2026-10-10

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 4 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
