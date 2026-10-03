# Result — issue 589 / flow-dep-graph-refusal-not-traceback

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: `pdca flow <ids>` over a batch where a brief declares a dependency that is
  neither in the batch nor a COMPLETE bundle ends in a Python traceback. The refusal itself
  is right: `waves.check_dep_graph` (`template/src/pdca_harness/waves.py:51-99`) validates
  the dependency graph before any build and raises `ValueError` naming the bundle and the
  dependency (`waves.py:78-80`), or `ValueError("dependency cycle: …")` for a cycle
  (`waves.py:93`). But nothing on the `flow` path catches it: `flow._drive_and_act` calls
  `waves.compute_waves` strictly (`flow.py:1694`), `flow.flow_ids` reaches it at
  `flow.py:2107`, and `cli._flow_claimed` catches only `flow.PreflightError` around
  `flow.flow_ids` (`cli.py:654-660`); `cli.main` catches only `worktree.WorktreeError`
  (`cli.py:457-461`). So an operator error (a stale `Depends on`, a prerequisite fixed
  outside the cycle whose bundle never reached COMPLETE) reads as a harness crash. Observed
  on getwyrd/wyrd-pdca (v0.58.0):
  `ValueError: issue_736: declared dependency '773' is neither in this batch nor an existing COMPLETE bundle`.
  **Which routes are live on `main`:** only the strict route — ids the operator names
  (`flow_ids` → `_drive_and_act` → `compute_waves`, `flow.py:1694`). The other routes are
  already tolerant and are NOT part of this fix: the `--from-csv` sweep (zero ids) goes
  through `flow_batch`, which runs `waves.partition_schedulable` first (`flow.py:1949`) and
  holds a bad-dep bundle; split adoption re-levels through `_reschedule`
  (`flow.py:1126-1146`), which also holds; and a split parent that is already terminal is
  passed as an adoption seed, outside the strictly levelled `bundles` (`flow.py:2088-2103`,
  `:1700-1703`). The thread's "easy to reach through a split parent's child" route is
  therefore expected to report the child as held on `main`, not raise; the v0.58.0 crash is
  reproduced here through named ids. Do must not change adoption.
- Success criterion: Driving `cli._flow` (the function `pdca flow` dispatches to,
  `cli.py:458`) with named ids, where one id's brief declares `Depends on: <X>` and `X` is
  neither in the batch nor a COMPLETE bundle on disk:
  (i) `cli._flow` **returns 2** (does not raise — rc 2 as the issue asks and as the
  `Config.load` operator-error handling does, `cli.py:443-447`; the preflight and claim
  refusals on the same path keep their existing rc 1, `cli.py:615`, `:643`, `:660` — the
  difference is intended, not a bug to "align"); stderr carries **no `Traceback`**, and
  carries the existing message text — the bundle name and the dependency id, e.g.
  `issue_A: declared dependency 'X' is neither in this batch nor an existing COMPLETE bundle`
  — plus the ways out, in one short block: add the prerequisite to the batch; drop the edge
  from the brief if the prerequisite landed outside the cycle; or finish the prerequisite
  first. No bundle is built (Do never runs on any bundle in the batch).
  (ii) A **dependency cycle** among named ids gets the same shape: rc 2, no traceback, the
  `dependency cycle: A → B → A` text on stderr.
  (iii) **Nothing else changes.** `check_dep_graph` / `compute_waves` still raise an
  exception that **is a `ValueError`** — every existing caller and test that expects
  `ValueError` keeps passing unchanged (`tests/test_waves.py:121,127`,
  `tests/test_deps_completed.py:92,101`, `tests/test_flow_slice.py:1077,1088`); `pdca waves`
  keeps its `unschedulable: …` line and rc 1 (`cli.py:1030-1034`,
  `tests/test_flow_slice.py:1252-1258`); the tolerant resume/adoption paths
  (`waves.partition_schedulable`, `flow._reschedule` `flow.py:1126-1145`) are untouched; any
  OTHER `ValueError` escaping `flow_ids` is not swallowed by the new handling (it still
  propagates as today) — pinned by a test (see Test file), so a fix that just catches
  `ValueError` fails. The whole `template/tests` suite stays green.
  Shown by the named test going red on `main` (the call raises `ValueError`) and green with
  the fix.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: Make an unschedulable dependency graph on the `flow` path for named ids (both CLI
  shapes: one id and several, with or without `--from-csv` — ids plus `--from-csv` still go
  through `flow_ids`, `cli.py:654-656`) end as
  a one-block refusal with rc 2, matching the issue's design: an exception type specific to
  "the dependency graph is unschedulable" that is still a `ValueError`, raised by
  `check_dep_graph` for both the unresolved-dependency and the cycle case, and handled in
  `cli._flow`. Update the one doc sentence that describes the up-front rejection if it
  needs to say what the operator sees (`docs/03-plan.md:102-104`). / out of scope: changing
  WHEN the graph is validated (it stays after the Plan pre-pass, before any build); making
  `flow` tolerant of the bad edge (holding the bundle instead of refusing — that is the
  resume path's behaviour, `waves.py:240-254`, and stays there); `pdca waves`' output and
  rc; the claim scope (`drive_claim.run`, `cli.py:575-576`) — the refusal must still leave
  every claim released, which the existing `with` already does; any handler in the zero-ids
  `--from-csv` branch (`cli.py:637-643`) — `flow_batch` cannot raise this error, so a handler
  there would be dead code; split adoption / `_reschedule`.

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

Review issue #589: make named-id `pdca flow` refuse unresolved dependencies and dependency cycles with exit 2 and actionable stderr, before any build, instead of a traceback.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | Named-id refusals, preserved ValueError compatibility, and unchanged tolerant routes form a concrete, testable scope; target/template/tests/test_flow_dependency_refusal.py:122 and target/template/src/pdca_harness/flow.py:1694 ground the requested behavior (brief.md:28). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing the production fix produced three behavioral failures for single-id, multi-id, and cyclic inputs; the unrelated-ValueError case passed, so this is the reported defect rather than an import failure; target/template/tests/test_flow_dependency_refusal.py:114; review-red.log. |
| C3 Change | PASS | Operator graph errors are distinguished without suppressing unrelated faults or changing validation timing; the existing claim scope still releases claims on refusal; target/template/src/pdca_harness/cli.py:661, target/template/src/pdca_harness/waves.py:51, target/template/src/pdca_harness/flow.py:1694. |
| C4 Verification (red→green) | PASS | Restoring the exact patch changed the same four-test run from three failures to four passes; extra named-id CSV runs returned 2, built nothing, and permitted claim reacquisition; target/template/tests/test_flow_dependency_refusal.py:122; review-green.log:1; review-extra.log:1. |
| C5 Causal adequacy | PASS | The cause is an uncaught operator-error category at the CLI boundary; typed handling fixes that boundary while retaining strict graph rejection and propagation of other ValueErrors, with no capability probe or fallback guard; target/template/src/pdca_harness/cli.py:661, target/template/tests/test_flow_dependency_refusal.py:156. |
| T1 Structure | PASS | Graph validation remains in the scheduler and command presentation remains in the CLI; no adoption/resume algorithm or claim ownership changes are needed; target/template/src/pdca_harness/waves.py:65, target/template/src/pdca_harness/cli.py:665. |
| T2 Shape | FAIL | The new documentation promises exit 2 for unqualified `pdca flow`, but the zero-id CSV sweep holds bad dependencies and continues; qualify this promise as `pdca flow <ids…>` so operators can predict resume behavior; target/docs/03-plan.md:104, target/template/src/pdca_harness/flow.py:1949; review-extra.log:13. |
| T3 Runtime | PASS | Independent driver-suite rerun passed 2,219 tests with two skips; root render/update coverage rests on the frozen log's 24 passing tests because the reviewer interpreter lacks Copier; target/CONTRIBUTING.md:26; review-suite.log; gate-logs/T3-suite.log:54. |
| T4 Contribution | N/A | Contribution artifacts are intentionally absent at Check; the substantive contribution audit is owed at publish and must rerun there; gate-logs/T4-contribution.log:10. |
| T5 Judgment | NEEDS-HUMAN | Confirm prior-art clearance across all affected paths, including docs and the new test — the brief records production-path merged/closed searches, but the supplied single-commit target has no remotes or closed/rejected-work evidence to independently establish that this work is not superseded; brief.md:113; target/docs/03-plan.md:104; target/template/tests/test_flow_dependency_refusal.py:1. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether exit 2 and the recovery wording adequately guide operators with stale dependencies or cycles — automated checks establish refusal/no-build behavior, but product suitability remains a sign-off judgment; target/template/src/pdca_harness/cli.py:665, target/template/src/pdca_harness/waves.py:96, target/template/src/pdca_harness/waves.py:113. |

Advisory finding: low-severity documentation scope error at `target/docs/03-plan.md:104`. In an independent run with an authored brief depending on absent bundle 773, named ids plus `--from-csv` returned 2 and released their claims. With zero ids, the same CSV route printed “issue_A held this run”, continued into the stub planner's other bundles, and returned 0 (`review-extra.log:13`). This is the intentionally unchanged tolerant behavior, not a runtime defect. Narrowing the documentation to named ids resolves the mismatch.

Independent verification used the disposable target only. `git stash push` saved the tracked fix while retaining the untracked regression test; unittest discovery produced three failures and one pass. `git stash pop` restored the patch, and the identical invocation passed all four tests. The tracked diff and added test were subsequently compared byte-for-byte with `patch.diff`; the original patch remains intact. Commands were `python3 -m unittest discover -s tests -p test_flow_dependency_refusal.py -v` from `target/template`, then `python3 -m unittest discover -s target/template/tests` from the review root, with `PYTHONPATH` pointing to the target production source and `TMPDIR` confined to this review sandbox.

The independent production-import scanner passed (`review-prod-path.log:1`). Documentation lint and `render_site.py --check` passed, rendering 22 pages with a clean link audit (`review-lint.log:1`, `review-render.log:1`); these reproduce the substantive docs and host-CI-parity checks, not a remote CI run. The prose finding above is outside those scanners' checks.

The frozen C4 log also contains the actual four-test green run and three-failure red run (`gate-logs/C4-verify.log:13`, `gate-logs/C4-verify.log:161`). The frozen full-suite log records 24 root tests passing and 2,219 driver tests passing with two skips (`gate-logs/T3-suite.log:54`, `gate-logs/T3-suite.log:1824`). The local root-suite attempt exited 77: Copier was not importable and its three dependent selections skipped (`review-root-suite.log:6`). This is a reviewer-host limitation, not a patch failure or an undischarged dependency in the frozen gate run; the brief declares no external dependencies. No CLI alias or replacement implementation was used to claim verification.

Prior-art investigation: `git -C target log --oneline --all -- docs/03-plan.md template/src/pdca_harness/cli.py template/src/pdca_harness/waves.py template/tests/test_flow_dependency_refusal.py` returned only `8158ec5 pre-fix base 24c7f83cca82764c279e75d0103f51ca33b97b18`; `git -C target remote -v` returned nothing. The supplied brief reports path-based production history and closed-unmerged PR checks, but their underlying evidence and coverage of the other affected paths are absent. No other checkout was consulted. The target source matches the patch; there is no stale-target caveat. The only supplied INTEGRATION §4 human-only enumeration is an unfilled template (`target/template/docs/INTEGRATION.md.jinja:80`), so it supplies no additional concrete items.

### Advisory — code-review

# Advisory code review — issue 589 (flow-dep-graph-refusal-not-traceback)

No correctness bugs found. The catch at `template/src/pdca_harness/cli.py:661` handles
only the new `waves.DependencyGraphError` subtype, so other `ValueError`s still propagate,
and `pdca waves` (`cli.py:1038-1041`, `except ValueError`) keeps working because the new
class subclasses `ValueError` (`waves.py:51`). `waves` was already imported in `cli.py`
(line 22), so no import was needed. The only strict call site is `flow.py:1694`, and it
runs before any wave builds, so the "no bundle was built" text is accurate. The tolerant
re-levelling (`flow.py:1142`) runs `partition_schedulable` first, so it never reaches the
new raise. C4 log shows 3 red / 1 green (by design) pre-fix and green post-fix.

Small, optional points (none block):

- `template/src/pdca_harness/waves.py:96-98` — the unresolved-dependency remedy says
  "if it landed outside the cycle". Here "cycle" means the PDCA cycle, but this text is
  printed next to errors that say "dependency cycle", so an operator could read it as a
  dependency cycle. Wording like "if it was fixed outside pdca" would be clearer. Cosmetic.
- `template/tests/test_flow_dependency_refusal.py:109` — `assertNotIn("Traceback", err)`
  can never fail. `redirect_stderr` only captures what is printed, and an uncaught
  exception goes to the test runner, not into `err`. The real guard is `_call`
  (`:113-119`), which turns a raised `ValueError` into a failure. This is harmless, but
  the line gives a false sense of coverage. It could be dropped or commented.
- `template/src/pdca_harness/waves.py:61-63, 96-98, 113-114` — the "ways out" text sits
  in the scheduling module as a `remedy` attribute, while the CLI adds the framing
  (`cli.py:665-666`). That is a fair split and matches `why.remedy` in `drive_claim`
  (`cli.py:613`), so there is no reuse gap. Noted only because `pdca waves`
  (`cli.py:1040`) does not print the remedy. The brief leaves that out of scope, so no
  change is needed.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — Confirm prior-art clearance across all affected paths, including docs and the new test — the brief records production-path merged/closed searches, but the supplied single-commit target has no remotes or closed/rejected-work evidence to independently establish that this work is not superseded; brief.md:113; target/docs/03-plan.md:104; target/template/tests/test_flow_dependency_refusal.py:1.
- [x] Validation — fitness-to-purpose — Decide whether exit 2 and the recovery wording adequately guide operators with stale dependencies or cycles — automated checks establish refusal/no-build behavior, but product suitability remains a sign-off judgment; target/template/src/pdca_harness/cli.py:665, target/template/src/pdca_harness/waves.py:96, target/template/src/pdca_harness/waves.py:113.
- [x] **The brief does not say whether the route the issue calls "easy to reach" is still live on `main`.** The thread says: "It is easy to reach: a split parent's `flow` adopts its children, so `pdca flow <parent>` hits it through a child's dependency the operator never named." On the target, both split-adoption paths are tolerant. `_adopt_split_children` re-waves through `_reschedule`, and `_reschedule` uses `partition_schedulable` and holds the bundle instead of raising (`flow.py:1126-1146`, called at `flow.py:1330`). A parent that is terminal on a split is passed as an adoption seed and is not part of the strictly-levelled `bundles` (`flow.py:2088-2101`, `:1700-1703`). So on `main`, `pdca flow <parent>` probably reports the child as held rather than raising. The brief also never says how the observed instance (v0.58.0) relates to `main`. Fix: state that on `main` the only strict route is the named ids, and that the split-parent route is already tolerant (or add a red test showing it is not). Otherwise a reviewer may ask for a test that cannot go red, or Do may "fix" adoption too.
- [x] **The `--from-csv` scope is left conditional, but the code already answers it.** The brief says "and the `--from-csv` batch if the same exception can reach it". With zero ids, `--from-csv` goes to `flow_batch`, which uses `partition_schedulable` (`flow.py:1949`) and cannot raise this error. A handler in the zero-ids branch (`cli.py:637-643`) would be dead code. With ids plus `--from-csv`, the call goes through `flow_ids` (`cli.py:655`), which the main handler already covers. Fix: replace the "if" with that decision, so Do does not add an untestable second handler.
- [x] **Some cited lines are off, and the brief requires Do to cite exact lines.** The brief cites the raise sites as "`waves.py:79-81` and `waves.py:91`". On the target the `raise ValueError(` is at `waves.py:78-80` and the cycle raise is at `waves.py:93`. Line 91 is the `if color[m] == GRAY:` check. `cli.main`'s handler is `cli.py:457-461`, not `453-461` (453 is the `if args.cmd in ("run", "flow")` line). Fix: correct the numbers so Do's citation check is not built on stale lines.
- [x] **Criterion (iii) "any OTHER `ValueError` escaping `flow_ids` is not swallowed" has no test to back it.** The test list under "Test file" covers an unresolved dependency (one id and two ids), a cycle, and "no build". Nothing pins this negative. A fix that just catches `ValueError` in `_flow_claimed` would pass every listed test and break (iii) without anyone noticing. The test file may not import the new exception class, so this part can only be checked by reading the code. Fix: add a test where a stubbed leaf raises a plain `ValueError` with a different message, and assert that it still propagates from `cli._flow`. Or state outright that (iii) is checked by code review only.
- [x] **The two refusals on the same path use different exit codes, and the brief does not say why.** The brief tells Do to mirror the `PreflightError` handling ("print `flow: {exc}` to stderr and return"), and that handling returns **1** (`cli.py:643`, `:660`). The claim refusal returns 1 as well (`cli.py:615`). The success criterion asks for **2**, following the issue and the `Config.load` handling (`cli.py:444`, `:447`). Both choices can be defended. But the brief's own invariant says every `flow` refusal of operator input should look the same, and it cites rc 1 and rc 2 as precedent. Fix: say in the brief that this refusal uses rc 2 (as the issue specifies) and the preflight/claim refusals keep rc 1, so a reviewer does not read the mismatch as a bug.

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
- By / date: Eduard Ralph / 2026-10-02

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 5 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
