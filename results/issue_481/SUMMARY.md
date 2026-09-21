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

Review issue #481: keep an iterated split parent’s Plan artifact and let it reach sign-off instead of reopening Plan.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | Criteria (a)–(f) distinguish a complete parent Plan artifact, downstream state, child traceability, and preservation of existing briefs; the regression exercises those outcomes (`brief.md:24`; `target/template/tests/test_split.py:1855`). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing production changes while retaining tests reproduced missing briefs and UNPLANNED parents: 109 tests, 16 assertion failures, no import errors (`review-red.log:175`; `target/template/tests/test_split.py:1857`). |
| C3 Change | PASS | Acceptance preserves existing briefs and unwinds newly written briefs on failure; independent tests cover torn writes, failed marker writes, retry, and refusal before tracker filing (`target/template/src/pdca_harness/split.py:978`; `target/template/tests/test_split.py:1989`). |
| C4 Verification (red→green) | PASS | After restoring the production patch, the same 109 tests passed; this includes reaching AWAITING_SIGNOFF with a child-bearing SUMMARY and no model leaf (`review-green.log:6`; `target/template/tests/test_split.py:1914`). |
| C5 Causal adequacy | PASS | Both causes are addressed: acceptance supplies the missing Plan artifact and state respects existing Do evidence; production-driven assertions confirm both, with no optional-capability probe masking a load-time cause (`target/template/src/pdca_harness/split.py:979`; `target/template/src/pdca_harness/state.py:347`). |
| T1 Structure | PASS | Shared archive interpretation preserves numeric re-plan ordering and the sizing boundary; existing Plan-field validation is reused, and production remains within existing modules (`target/template/src/pdca_harness/state.py:306`; `target/template/src/pdca_harness/size_signal.py:145`; `target/template/src/pdca_harness/split.py:795`). |
| T2 Shape | PASS | Independent docs lint, 22-page rendering/internal-link audit, and git diff whitespace checks passed; frozen host-parity output agrees (`review-lint.log:2`; `review-render.log:3`; `review-diff.log:3`; `gate-logs/host-ci-docs.log:11`). |
| T3 Runtime | PASS | Independent offline suite: 1,907 tests, two skips, no failures; root render/update coverage is supported by 24 passing frozen tests because local Python cannot import Copier (`review-suite.log:1656`; `gate-logs/T3-suite.log:54`; `review-root.log:7`). |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the substantive contribution audit must rerun at publish (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Confirm the shared-reader extraction belongs in this slice and settle prior art for all six affected paths — carry-forward supports deduplication, but the named scope/searches are narrower and this snapshot cannot verify merged or rejected work (`brief.md:63`; `brief.md:102`; `brief.md:121`; `review-history.log:2`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether a decomposition brief linking the archived goal, proposal, and children gives maintainers enough context to sign off the parent — automated progression and field completeness cannot establish that editorial sufficiency (`target/template/src/pdca_harness/split.py:838`; `target/template/tests/test_split.py:1914`). |

Independent evidence and limits:

- The disposable target was readable and matched the supplied patch. I stashed only the five changed production/support files, kept the changed test file, ran `python3 -m unittest discover -s tests -p test_split.py` from `target/template`, restored the stash, and repeated the command. The final target diff is byte-identical to `patch.diff`.
- The complete offline suite ran with `PYTHONPATH=src`; temporary files stayed under this review directory. The end-to-end regression actually drove the split parent to sign-off and checked its SUMMARY. No GUI/manual reproduction is needed to establish that behavior.
- Root-suite rerun returned 77: Copier is not importable by this interpreter. This is a reviewer-host limitation, not a patch failure. The frozen log explicitly records successful render and update cases (`gate-logs/T3-suite.log:38`) and all 24 root tests passing. The brief declares no external dependency; the relevant filesystem/driver behavior was exercised directly without a tool shim.
- I read all six frozen gate logs. The production-path scanner’s frozen output says no new test file was added (`gate-logs/C5-prod-path.log:10`); that heuristic supplies no substantive proof here. I reran the reference scanner, but grounded C5 in the actual production imports, driver archive call, and independent red→green run instead.
- Path-based `git log --all` for all six changed files returned only the synthetic pre-fix commit; `git remote -v` returned nothing. The brief records merged-history searches for `state.py`/`split.py` and closed-unmerged searches also covering `test_split.py`, but supplies none for `size_signal.py`, `handoff.py`, or `scripts/size-calibrate`. Therefore a complete prior-art conclusion remains outstanding. The available integration template has no populated project-specific human-only list (`target/template/docs/INTEGRATION.md.jinja:80`).

No independently confirmed patch defect was found. The NEEDS-HUMAN rows are advisory sign-off decisions, not deterministic acceptance gates.

### Advisory — code-review

# Check — advisory code review (issue #481)

Clean on both lenses. No correctness bugs found, and the patch's own reuse work is the kind this lens looks for (it removed rather than added duplication):

- **Reuse (already done right by the patch):** `template/src/pdca_harness/state.py:306-332` adds `iteration_archives`/`replan_archives` as the single reader of the `iteration-v<N>` archive shape, and `template/src/pdca_harness/size_signal.py:61,142-148` and `template/scripts/size-calibrate:9` (the removed `_ITERATION_DIR` at old line 9) both drop their private copies of that regex/glob logic in favor of the shared one. Confirmed no leftover `_ITERATION_DIR` definition outside `state.py` (`grep` across `template/src` and `template/scripts` turns up only the one in `state.py:303,317`). This is exactly the kind of duplicated-logic cleanup this lens flags when missing — here it's present.

- **`state()` reordering (`state.py:335-373`) is correct:** the "past Do" check (`patch.diff` or `CLOSE_MARKER`) now wraps the missing-brief and placeholder-brief checks instead of the old code returning `UNPLANNED`/`RESOLVED` before ever looking at `patch.diff`/`CLOSE_MARKER`. Traced by hand against all six shapes in `test_e_a_briefless_bundle_past_do_is_never_placed_before_plan` (`template/tests/test_split.py:504-535`) and the behavior matches for each. No regression for the brief-exists-and-placeholder-and-past-Do combination (unchanged path).

- **Transaction discipline in `split.accept` (`split.py:904-1011`) checked against both failure-injection tests** (`test_a_torn_brief_write_is_rolled_back_and_the_retry_completes`, `test_a_failure_after_the_brief_landed_takes_it_back_out`, `test_split.py:2029-2066`): the new-brief write sits second-to-last (after build-notes, before the close marker) on the forward path and is unconditionally (not gated on the write's own return value) unlinked on the rollback path, correctly handling the "write landed part of the file, then raised" case (a partial write left behind would otherwise be adopted by a retry as the parent's own brief).

- **`_parent_plan` (`split.py:756-806`) correctly reuses `handoff.check_planner(..., dependencies=False)`** rather than re-implementing the Plan-exit field checks, and the field values it copies (`slug`, `repo + branch target`) are only read after `check_planner` has confirmed they're non-empty and non-placeholder — so `_brief.whole_field`'s raw (unfiltered) return value can't leak a placeholder into the rebuilt brief.

- No circular-import risk from the new `size_signal → state` and `split → state` (pre-existing) imports — `state.py` imports only `brief` and `signoff`.

- Full offline suite (`gate-logs/T3-suite.log`) is green at 1907 tests, and `gate-logs/C4-verify.log` shows a genuine red leg (16 assertion failures with the production hunks reverted, not an import error), so the new test class exercises the fix rather than passing vacuously.

Nothing here needs a human's or the builder's attention beyond what the deterministic gates and the `reviewer` leaf already cover.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — Confirm the shared-reader extraction belongs in this slice and settle prior art for all six affected paths — carry-forward supports deduplication, but the named scope/searches are narrower and this snapshot cannot verify merged or rejected work (`brief.md:63`; `brief.md:102`; `brief.md:121`; `review-history.log:2`).
- [x] Validation — fitness-to-purpose — Decide whether a decomposition brief linking the archived goal, proposal, and children gives maintainers enough context to sign off the parent — automated progression and field completeness cannot establish that editorial sufficiency (`target/template/src/pdca_harness/split.py:838`; `target/template/tests/test_split.py:1914`).

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
- By / date: Eduard Ralph / 2026-09-18

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
