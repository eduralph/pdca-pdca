# Result — issue 549 / csv-batch-plan-reap-rereads-the-briefs-it-wrote

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: On the CSV/default batch-Plan path the session-end contract check never re-reads
  a brief. `do_plan_batch` registers no bundle set there, because the planner picks its ids
  mid-session (`template/src/pdca_harness/leaves.py:1195-1205`: `seeded = []` when
  `ids is None`). So `handoff.stop_problems` falls to its no-registered-bundles tail
  (`template/src/pdca_harness/handoff.py:622-625`): if any `/handoff` passed, it returns with
  nothing about the briefs. A session that runs `/handoff issue_7` and then writes
  `issue_8/brief.md` with an empty **Success criterion** (or empty `Slug` /
  `Repo + branch target`) ends with nothing reported. Nothing later catches those three empty
  fields. `state.py` only treats an unfilled template copy as UNPLANNED, and `plan_policy`
  checks size and dependencies only. So the empty criterion reaches Do (no stated end result)
  and Check (SUMMARY §1 is assembled from the empty field). The id-seeded path is not
  affected: its bundles are registered and each brief is re-read (`handoff.py:609-621`).
- Success criterion: With the patch, a `planner` session opened through `handoff.session`
  with **no registered bundles** reports at reap, bundle-prefixed and report-only, every
  `check_planner` problem in every `issue_*/brief.md` under `cfg.bundle_root` that the session
  **created or changed** (its content differs from session start, or it did not exist then).
  This holds whether or not a `/handoff` passed during the session. Concretely:
  (i) the issue's case: `/handoff` recorded for `issue_7` (discharged brief), then
  `issue_8/brief.md` written with an empty Success criterion → the reap prints
  `issue_8: brief.md field 'success criterion' is empty …`;
  (ii) a brief that existed before the session and is **byte-unchanged** is not re-read (even
  if malformed). It is not this session's work, which matches the
  `_brief_snapshot`/`_fresh_plan_briefs` "new or rewritten" rule the plan-advisory pass
  already uses (`leaves.py:3640-3669`);
  (iii) a session that changed no brief keeps today's behavior exactly: a passed `/handoff`
  ⇒ nothing about the session; no pass ⇒ the existing "registered no bundle set at spawn and
  verified none" item;
  (iv) when it changed briefs and all of them pass `check_planner`, nothing is reported for
  them and no "verified none" item is added, even without a `/handoff`. This is the rule the
  registered path already follows (`stop_problems` docstring, `handoff.py:579-584`: "a
  session that discharged them without ever typing `/handoff` is discharged too");
  (v) the unreadable-`[[doctor.checks]]`-table rule still holds. It is one item for the
  session, and the re-read briefs are then checked with `dependencies=False`, as for
  registered bundles (`handoff.py:606-614`). A brief whose check raises is its own
  `could not check (…)` item and never hides the others (`:615-620`).
  (vi) the registered paths (single Plan, id-seeded batch, sign-off, publish) and the `act`
  role are unchanged, and nothing in the reap writes, moves or deletes a file under the
  project root. Shown by the named test going red on the base (criterion (i) prints nothing
  about `issue_8`) and green with the fix, with every existing test in that module still
  green (including `test_a_broken_doctor_table_is_reported_at_every_planner_reap`,
  `:623-656`, whose "CSV batch" subtests pre-write their brief **before** the session, so
  criterion (ii) keeps them at their current item count).
- Repo + branch target: eduralph/pdca-harness @ main (base `70ea12b`; every `path:line`
  here re-verified against it)
- Scope (one logical fix) / out of scope: Remove the gap where an unregistered planner session's written briefs are never
  re-read at reap. The work set is derived by `handoff.py` itself from the bundle root at
  session start versus reap, so no caller changes (`do_plan_batch` and the `/handoff`
  command are untouched). Update the text that promises the old behavior: the `handoff.py`
  module docstring (`:13-18`), `report_at_reap` (`:483-487`), `stop_problems` (`:586-588`),
  and `docs/01-render-and-integrate.md:181-184` ("…and does not re-read what that session
  wrote"). / out of scope: the `act` role's no-bundles rule (it has no brief to re-read);
  the id-seeded path's `allow_absent` wrinkle; a brief deleted during the session; the
  `[[doctor.checks]]` read itself (#558) and the dependency-clause exception handling
  (#559); `leaves.py` (including `_brief_snapshot` / `_fresh_plan_briefs`: do not import
  `leaves` into `handoff.py`, which is kept import-light for the hook, `handoff.py:120`, `:392`); the
  `/handoff` command and `run_check`; making the reap blocking.

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

Review issue #549: make CSV/default batch Plan reap re-check briefs created or changed during the session, without changing registered-session behavior or making reap blocking.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The six success clauses define observable reporting, unchanged-brief exclusion, error isolation, and preserved registered paths; the production caller confirms the unregistered batch entry point (`brief.md:14`; `target/template/src/pdca_harness/leaves.py:1197`). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only production changes retained the regression tests and produced seven assertion failures, including silence after a passed handoff hides another malformed brief (`review-red.log:1`; `target/template/tests/test_handoff_reap.py:424`). |
| C3 Change | FAIL | A previously unreadable brief rewritten during the session remains silently excluded when its read error matches the baseline, violating coverage of content changes; independently reproduced with real file permissions (`target/template/src/pdca_harness/handoff.py:311`; `target/template/src/pdca_harness/handoff.py:331`; `review-boundary.log:1`). |
| C4 Verification (red→green) | PASS | Restoring production changes turns the same 37-test module green with no skips; this verifies the asserted regression cases, but does not discharge the additional C3 counterexample (`review-green.log:1`; `gate-logs/C4-verify.log:10`). |
| C5 Causal adequacy | PASS | Deriving the missing work set before considering passed handoffs directly repairs the original bypass; the patch adds no optional-capability probe, while C3 records its incomplete change detection (`target/template/src/pdca_harness/handoff.py:679`; `target/template/src/pdca_harness/handoff.py:692`). |
| T1 Structure | PASS | The change stays within the specified production module, documentation, and regression module; registered planners skip discovery and the driver's baseline remains authoritative (`target/template/src/pdca_harness/handoff.py:489`; `target/template/src/pdca_harness/handoff.py:521`). |
| T2 Shape | PASS | Independently rerun docs lint, 22-page site rendering, internal-link audit, and diff whitespace checks passed; both frozen docs gates show the same substantive checks passing (`target/.github/workflows/docs-check.yml:33`; `gate-logs/T2-docs.log:10`; `gate-logs/host-ci-docs.log:10`). |
| T3 Runtime | PASS | Independent offline suite: 1,929 tests, OK with two skips; frozen root-suite output shows all 24 render/update tests passing, including actual compatibility cases (`review-suite.log:1656`; `gate-logs/T3-suite.log:35`; `gate-logs/T3-suite.log:54`). |
| T4 Contribution | N/A | Contribution artifacts are intentionally absent at Check; the substantive contribution audit must rerun at publish (`gate-logs/T4-contribution.log:8`). |
| T5 Judgment | NEEDS-HUMAN | Confirm prior-art disposition by all three affected paths, including closed/rejected work — the brief records a search, but this target has only one synthetic base commit and no remote, so those results cannot be independently settled from the supplied evidence (`brief.md:117`; `review-history.log:1`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether to require detection of edits to previously unreadable briefs or explicitly narrow the contract before accepting — the observed silent edit contradicts the current byte-change promise despite green regression suites (`brief.md:14`; `target/template/src/pdca_harness/handoff.py:320`; `review-boundary.log:1`). |

The C3 counterexample uses the real `handoff.session` through the existing test harness. Create an authored `issue_8/brief.md`, set its mode to `000`, and confirm reading raises `PermissionError`. Start an unregistered planner session; inside it, temporarily set mode `0600`, rewrite the brief with an empty Success criterion, restore mode `000`, and record a passing handoff for `issue_7`. Reap returns empty stderr (`review-boundary.log:2`). Both snapshots contain the same permission-error string, so the changed brief never reaches the per-bundle `could not check` handler. This is a narrow uncovered boundary case; the new tests do exercise newly unreadable briefs and unchanged old unreadable briefs (`target/template/tests/test_handoff_reap.py:460`; `target/template/tests/test_handoff_reap.py:530`).

The two requested carry-forward fixes are present and pass their tests: registered sessions take no snapshot, and a newly unreadable brief produces its own item without hiding another malformed brief (`target/template/tests/test_handoff_reap.py:530`; `target/template/tests/test_handoff_reap.py:553`). The C5 scanner's frozen output says only that no new test file was added; causal coverage above comes from inspecting and executing the tests against production, not that scanner (`gate-logs/C5-prod-path.log:10`).

Instance-scoped gate wrappers were not sought in other checkouts. Their supplied logs were read. Copier is not importable in this review interpreter, so render/update compatibility relies on the frozen log's actual passing cases, not an independent rerun; the fix itself requires only Python and was exercised without tool aliases or mocked filesystem permission failures. No concrete project-specific human-only items are enumerated in the supplied integration template (`target/template/docs/INTEGRATION.md.jinja:80`). The target was readable, its production change was restored after the red leg, and its final diff matches `patch.diff` byte-for-byte. This review is advisory and does not gate acceptance.

### Advisory — code-review

# Check — advisory code review (issue #549)

Lens: bugs the patch introduces, plus reuse/simplification/efficiency. Grounded on
`$PDCA_TARGET/template/src/pdca_harness/handoff.py` and
`$PDCA_TARGET/template/tests/test_handoff_reap.py`.

## Correctness

No bug found in the new code paths. Specifically checked and found sound:

- `template/src/pdca_harness/handoff.py:315-331` (`_changed_briefs`) only ever returns a
  bundle whose `brief.md` exists right now (`_brief_fingerprints` skips a path where
  `bp.exists()` is false), so the `allow_absent=True` kwarg that
  `stop_problems` (`handoff.py:674-683`) now applies uniformly to both the registered and
  the unregistered bundle lists can never actually fire on an unregistered entry — the
  "missing brief" branch of `check_planner` (`handoff.py:126-129`) is unreachable for
  anything `_changed_briefs` returns. Harmless in practice, and matches the brief's own
  "brief deleted during the session" out-of-scope note (`brief.md:89`).
  `test_a_broken_doctor_table_is_one_item_and_the_briefs_are_still_checked` and the
  `allow_absent` propagation are exercised together correctly.
- Session-start snapshot vs. reap-time re-fingerprint is symmetric: a brief that predates
  the session and errors the same way both times (`"unreadable (...)"` unchanged) is
  correctly excluded from `_changed_briefs`, matching the documented "fails to read the
  same way it did at spawn" rule (`handoff.py:320-324`) and covered by
  `test_a_session_that_changed_no_brief_is_judged_as_before`.
  A brief that goes from readable-at-spawn to unreadable-at-reap (or vice versa) does show
  up as changed and is correctly routed through the bundle-level
  `try/except` in `stop_problems` (`handoff.py:684-690`), landing as its own
  `could not check (...)` item — covered by
  `test_a_brief_that_cannot_be_read_is_its_own_item_and_hides_no_other`.
- `state = {**_read_json(path), **registered}` (`handoff.py:521`) already guaranteed the
  driver-captured `baseline` wins over anything the leaf process could rewrite into the
  scratch file; `_changed_briefs` reads `state["baseline"]`, so it inherits that
  protection for free. `test_a_session_cannot_blank_its_own_spawn_snapshot` actually
  exercises this (writes `{"baseline": {}}` into the scratch file mid-session and checks
  the reap still uses the real snapshot) — a genuine regression guard, not a decorative
  test.
- The `_brief_fingerprints`/`leaves._brief_snapshot` duplication is deliberate, not
  redundant: `leaves.py:59` imports `handoff` at module scope, so `handoff.py` importing
  `leaves` would be circular. The two intentionally differ (placeholders are fingerprinted
  here but excluded in `_brief_snapshot`), and that difference is spelled out in
  `session()`'s docstring (`handoff.py:461-464`) — reviewed and correct.

## Efficiency

- `_brief_fingerprints` (`handoff.py:293-312`) reads every `issue_*/brief.md` under
  `cfg.bundle_root` in full, twice per CSV/default batch Plan session (once at spawn,
  once at reap). That's O(bundle count) file reads on a path that already spawns an
  interactive agent session, so it's not a hot loop — not worth flagging as a performance
  problem, just noting it scales with bundle-root size the id-seeded/single-Plan paths
  don't pay.

## Reuse / simplification

Nothing to flag — the new helpers are small, single-purpose, and the one place that looks
like duplicated logic (vs. `leaves._brief_snapshot`/`_fresh_plan_briefs`) is justified by
a real circular-import constraint and is documented as intentionally non-identical.

## Overall

Diff is clean on both lenses. No NEEDS-HUMAN items.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — Confirm prior-art disposition by all three affected paths, including closed/rejected work — the brief records a search, but this target has only one synthetic base commit and no remote, so those results cannot be independently settled from the supplied evidence (`brief.md:117`; `review-history.log:1`).
- [x] Validation — fitness-to-purpose — Decide whether to require detection of edits to previously unreadable briefs or explicitly narrow the contract before accepting — the observed silent edit contradicts the current byte-change promise despite green regression suites (`brief.md:14`; `target/template/src/pdca_harness/handoff.py:320`; `review-boundary.log:1`).

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
- By / date: Eduard Ralph / 2026-09-19

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
