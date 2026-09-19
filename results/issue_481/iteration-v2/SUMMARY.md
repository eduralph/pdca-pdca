# Result — issue 481 / split-parent-keeps-a-plan-artifact

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: A split parent that was sent back by `iterate-plan` *before* it was split ends up
  terminal and `UNPLANNED` at the same time. `iterate-plan` archives the brief
  (`template/src/pdca_harness/driver.py:140`, `_archive_iteration(d, n, include_brief=True)`, which
  moves it to `iteration-v<N>/brief.md`, `driver.py:411-450`). The Plan session then splits the
  slice. `split.accept` (`template/src/pdca_harness/split.py:752`) has no brief to keep: it archives
  with `include_brief=False` (`split.py:836-838`, inside the `try` at `:828`), writes `build-notes.md` (`split.py:854-861`) and
  the `close-disposition: split` marker (`split.py:862`), and never writes a parent brief.
  `state.state()` checks for `brief.md` first (`template/src/pdca_harness/state.py:301-307`) and only
  looks at the close marker inside the has-brief branch (`state.py:310`), so the parent derives
  `UNPLANNED`. Every `pdca flow <parent>` then opens an interactive Plan session with nothing to
  decide, gets no brief back, and stops; the parent never reaches sign-off, never gets a
  `SUMMARY.md`, never freezes. `split.py:824-826` itself calls the iterated parent "the realistic
  case". The drafting door already refuses a briefless parent (`leaves.do_split`,
  `template/src/pdca_harness/leaves.py:1800-1804`, pinned by
  `test_a_bundle_with_no_brief_is_refused`, `template/tests/test_split.py:236`); the accept door
  does not (`split.accept` checks only the proposal and the marker, `split.py:763-773`). Observed on
  `getwyrd/wyrd-pdca` v0.56.0: `issue_711` and `issue_654` (both iterated, then split) are stuck;
  `issue_682` / `issue_692` (split on the first attempt) are fine.
- Success criterion: With a parent bundle shaped like the realistic case (an authored brief
  and a first attempt archived by the driver's own iterate-plan path, so `iteration-v1/` holds the
  brief and no `brief.md` is left at the top level) and a valid two-child `split-proposal.md`,
  `split.accept(parent, [ids], cfg)` leaves the parent such that ALL of these hold:
  (a) `state.state(parent)` is not `UNPLANNED` (and not `RESOLVED`);
  (b) `parent/brief.md` exists, `brief.is_placeholder` is False for it, and
  `handoff.check_planner(parent, cfg)` returns `[]`, i.e. slug, success criterion and repo + branch
  target are filled;
  (c) that brief names every child bundle the accept created;
  (d) `build-notes.md` still names the child bundles.
  Separately, (e) any bundle that carries the close marker and no `brief.md`, however it got that
  way, never derives `UNPLANNED` from `state.state()`. And (f) nothing changes for a parent that
  still has its own brief at accept time: its `brief.md` is byte-identical before and after, and
  every existing test in `template/tests/test_split.py` stays green.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: Remove the briefless-terminal shape: a split accepted on a parent with no top-level
  `brief.md` must leave the parent with a Plan artifact that describes the split (why, which
  children), and `state()` must not derive `UNPLANNED` for a bundle carrying the close marker.
  The parent's original brief is on disk at `iteration-v<N>/brief.md` and the proposal is at
  `split-proposal.md`; which of these the Plan artifact is built from is Do's call. Keep
  `accept`'s transaction discipline (`split.py:828-878`: every write before the marker, rollback
  on failure). A failed accept must not leave a new parent brief behind either. / out of scope:
  hand-repairing the stuck `wyrd-pdca` bundles; the #498 hint wording; child adoption (#469/#473/#449);
  the #357 state-machine rewrite; `leaves.do_split` (its refusal stays as is); the `_do_close`
  build-notes overwrite the issue mentions (on main a bundle with brief + marker derives `BUILT`,
  so `driver.py:69-72` `_do_close` does not run for it; if Do finds otherwise, record it in
  build-notes rather than widening this slice). Refusing the accept on a briefless parent does
  NOT meet the criterion: the in-session split after iterate-plan is the realistic case and has
  to complete.

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

Review issue #481: preserve a usable Plan artifact when accepting an iterated split parent, and prevent bundles already past Do from returning to UNPLANNED.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The six success conditions distinguish restored parent context, correct state, child traceability and preservation of existing briefs; the regression exercises those observable contracts (`target/template/tests/test_split.py:1856`, `target/template/tests/test_split.py:1930`, `target/template/tests/test_split.py:1965`). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only the production changes while retaining the tests reproduced UNPLANNED and missing-brief failures: 109 tests ran, 16 assertion/subtest failures (`review-red.log:32`, `review-red.log:174`; fixture: `target/template/tests/test_split.py:1824`). |
| C3 Change | PASS | An accepted split retains an authored identity and target, names its children, and preserves existing briefs; failed writes remove the newly created brief so retry remains viable (`target/template/src/pdca_harness/split.py:797`, `target/template/src/pdca_harness/split.py:924`, `target/template/src/pdca_harness/split.py:993`, `target/template/src/pdca_harness/split.py:1017`). |
| C4 Verification (red→green) | PASS | Restoring the exact production diff turned the same 109 tests green, including the driver reaching AWAITING_SIGNOFF with child names in SUMMARY; the complete diff was unchanged after stash/pop (`review-green.log:5`; `target/template/tests/test_split.py:1909`). |
| C5 Causal adequacy | PASS | Both demonstrated causes are removed: accept supplies the missing Plan artifact and state gives Do evidence precedence; no optional-capability probe masks a load-time cause, and the regression calls real archive/accept/state/driver APIs (`target/template/src/pdca_harness/split.py:993`, `target/template/src/pdca_harness/state.py:313`, `target/template/tests/test_split.py:1824`). |
| T1 Structure | PASS | The existing archive convention, Plan contract and accept transaction remain the authorities; preflight rejects unusable source briefs before tracker filing, avoiding orphaned external issues (`target/template/src/pdca_harness/split.py:325`, `target/template/src/pdca_harness/split.py:810`, `target/template/tests/test_split.py:2058`). |
| T2 Shape | PASS | Independent docs lint and the host workflow's renderer/link audit passed for all 22 pages; git diff --check was clean (`review-docs-lint.log:1`, `review-docs-render.log:2`; workflow: `target/.github/workflows/docs-check.yml:35`). |
| T3 Runtime | PASS | Independent offline suite: 1,907 tests, two skips, no failures; frozen evidence separately confirms real Copier render/update coverage passed, which this review interpreter could not rerun (`review-driver.log:1656`, `gate-logs/T3-suite.log:38`, `gate-logs/T3-suite.log:54`; `target/CONTRIBUTING.md:27`). |
| T4 Contribution | N/A | Contribution artifacts are intentionally not drafted at Check; the substantive contribution audit must rerun at publish (`gate-logs/T4-contribution.log:10`; publish contract: `target/template/src/pdca_harness/handoff.py:166`). |
| T5 Judgment | PASS | Scope matches the two-part invariant; path-based merged-history and closed/unmerged-PR checks found no competing fix, and main equals the review base; the supplied integration template enumerates no additional human-only items (`review-prior-art.json:1`; `target/template/docs/INTEGRATION.md.jinja:80`, `target/template/src/pdca_harness/state.py:313`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Confirm the generated decomposition brief plus links to the archived original and proposal give maintainers enough context to sign off a split parent — execution proves reachability and child traceability, but not whether that presentation adequately supports their decision (`target/template/src/pdca_harness/split.py:848`, `target/template/tests/test_split.py:1909`). |

No grounded patch defect found. This is an advisory review; the fitness-to-purpose decision remains with the human.

Independent verification used the supplied disposable target, whose synthetic base records commit `4050da290242ac1c797c93d2bce997a00263ad47`. Only the two production files were stashed for the red leg; the added tests remained present. Stash/pop restored the original full diff byte for byte. All temporary test data and rendered output were directed inside this review workspace. The rollback tests exercised both a partially written brief and a marker write that landed before raising; retry succeeded. The end-to-end regression exercised the real driver through SUMMARY creation and AWAITING_SIGNOFF, with model leaves forbidden from running.

The C5 gate log explicitly says its new-test-file heuristic had nothing to inspect (`gate-logs/C5-prod-path.log:10`). Rerunning the repository scanner also exited successfully, but that heuristic does not establish coverage for edits to an existing test module. The C5 judgment instead rests on the production calls in the regression and the independent red→green result.

The root-suite rerun exited 77 because Copier is not importable in this interpreter (`review-root.log:6`); this is a reviewer-host limitation, not a patch failure. The frozen T3 log explicitly records both rendering cases and all five update-compatibility cases as executed and passing (`gate-logs/T3-suite.log:38`), followed by 24 tests passing (`gate-logs/T3-suite.log:54`). Thus that dependency was exercised in the supplied gate evidence; the brief declares no other external dependency. The instance-scoped gate wrappers were adjudicated from their captured logs, with the available underlying driver tests, docs tools and production-path scanner rerun locally.

Prior-art investigation used the GitHub API for all three affected paths at the review base: 20 state.py history entries, 18 split.py entries and 22 test_split.py entries. Inspection of all 239 closed PRs found one unmerged PR, #4, affecting only README.md. Comparing the review base with main returned identical, zero ahead and zero behind. The captured path lists and subjects are in `review-prior-art.json`; the independently reproduced defect establishes that the base still needs this fix. No other checkout was used for source grounding.

### Advisory — code-review

# Advisory code review — issue #481

Scope: correctness bugs the patch introduces, and reuse/simplification opportunities.
Not re-litigating fix adequacy (that's the `reviewer` leaf's job).

## Findings

- NEEDS-HUMAN [impl] — `_ITERATION_DIR` (the `^iteration-v(\d+)$` regex) and the "find the
  highest-numbered `iteration-v<N>` that holds a `brief.md`" computation are now defined
  **twice**: `template/src/pdca_harness/split.py:756-774` (`_archived_brief`) duplicates
  `template/src/pdca_harness/size_signal.py:69-70,148-153` (`iteration_rounds`'s `boundary =
  max(replans, ...)` logic) almost line for line. The new code's own comment
  (`split.py:756-757`, "The same pattern `size_signal.iteration_rounds` reads its re-plan
  boundary with") shows the author noticed the overlap and duplicated anyway rather than
  factoring out a shared helper (e.g. `latest_replan_archive(d) -> Path | None` in `state.py`
  or `driver.py`, next to `_archive_iteration`). Two private copies of the same regex + max
  logic can drift silently if one is edited without the other — worth a follow-up extraction,
  not a blocker.

- NEEDS-HUMAN [impl] — `handoff.py:113-116`'s docstring for `check_planner`'s `dependencies`
  parameter says "Only the reap passes it" (`dependencies=False`). The patch adds a second
  caller — `split.py:810` (`_parent_plan`) — that also passes `dependencies=False`, for an
  unrelated reason (skipping the archived-brief's doctor-registered dependency check, since
  the rebuilt parent brief declares `External dependencies: none` itself and doesn't carry
  the archive's declarations forward). `handoff.py` isn't touched by this diff, so that
  comment is now stale/inaccurate about which code paths rely on the flag — a future reader
  chasing "who passes dependencies=False and why" will be misled. One-line docstring fix.

## Everything else checked and clean

- `_archived_brief`'s "latest re-plan" tie-break correctly parses the numeric suffix
  (`int(m.group(1))`) rather than sorting directory names as text, so `iteration-v10` beats
  `iteration-v2` as intended (`split.py:769-774`, exercised by
  `test_the_source_is_the_latest_re_plan_not_the_first_archive`).
- The rollback path added to `accept()` (`split.py:1010-1025`) removes a torn/partial
  `brief.md` write unconditionally (not gated on which write raised), which is the right
  call for the "write lands part of the file, then the disk fills" case — verified against
  `test_a_torn_brief_write_is_rolled_back_and_the_retry_completes`. The pre-existing gap
  where a failed `build-notes.md` write is never itself rolled back is unchanged by this
  patch (not introduced here) — out of scope.
- `_parent_plan` is invoked twice per accepted split (once from `preflight`, once from
  `accept`) rather than threading a single computed value through — a few extra small-file
  reads on an infrequent, human-gated path. Not worth flagging as a performance problem; it's
  the same "ask again right before the irreversible step" pattern the rest of `preflight`/
  `accept` already uses for the proposal and marker checks.
- Traced the resulting state machine through to sign-off: the freshly-written `brief.md`'s
  `Disposition hint: split` is irrelevant to routing once `state.CLOSE_MARKER` exists —
  `driver._close_class` (`driver.py:236-242`) reads the marker content directly and wins
  outright before ever consulting the brief, so `split` correctly staying out of
  `DEFAULT_CLOSE_DISPOSITIONS` (`config.py:32-36`) does not strand the parent. No new
  builder/reviewer invocation risk on a patch-less split parent.
- `state.py`'s reordering (check patch.diff/CLOSE_MARKER before brief.md) is scoped
  correctly: the placeholder-brief branch (`state.py:318-328`, issue #113) is still reached
  only pre-Do, so an in-flight PLANNED bundle with a placeholder brief keeps its existing
  UNPLANNED-on-placeholder behavior; only the past-Do branch changed.

No implementation defects beyond the two duplication/doc-drift items above; both are minor
and independently fixable without touching the fix's substance.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] Validation — fitness-to-purpose — Confirm the generated decomposition brief plus links to the archived original and proposal give maintainers enough context to sign off a split parent — execution proves reachability and child traceability, but not whether that presentation adequately supports their decision (`target/template/src/pdca_harness/split.py:848`, `target/template/tests/test_split.py:1909`).
- [ ] `_ITERATION_DIR` (the `^iteration-v(\d+)$` regex) and the "find the
- [ ] `handoff.py:113-116`'s docstring for `check_planner`'s `dependencies`

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
- Iteration delta (if iterating): Auto-iterate (round 2): Check found implementation-level items only, no architectural judgment required — `_ITERATION_DIR` (the `^iteration-v(\d+)$` regex) and the "find the; `handoff.py:113-116`'s docstring for `check_planner`'s `dependencies`
- By / date: auto-iterate / 2026-09-18

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
