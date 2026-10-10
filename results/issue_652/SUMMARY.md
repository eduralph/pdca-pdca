# Result — issue 652 / carry-not-clean-cascades-across-finished-ids

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: Before wave 0 a re-issued stack run carries its finished named ids onto the integration line (`flow._carry_finished`, `template/src/pdca_harness/flow.py:869-956`, called at `:2146-2149`). Each finished id is judged on its own: `_finished_head` (`flow.py:836-857`) checks only that id's PR state and head. A finished id that is not clean goes into `held` (`flow.py:947-956`), and `_runnable` then holds only the drive-set bundles whose plain `Depends on` names it (`flow.py:751-754`). Nothing looks at the edges BETWEEN finished ids. So when a finished `P` is not clean (e.g. its PR is CLOSED) and a finished `Q` was built on `P` (`Q`'s brief: `Depends on: P`, its branch cut from a line holding `P`) and is clean, `Q` is carried. `Q`'s branch carries `P`'s commits, so they come onto the line with it (the fold merges `Q`'s branch tip, `integrate._merge_published`, `template/src/pdca_harness/integrate.py:461-475`). A drive-set `D` with `Depends on: Q` is then built on a line holding `P`'s closed work, and nothing says so. #624's shape is the same gap one level up: `U` held → `D` finished before the run (`Depends on: U`) → `E` (`Depends on: D`) is built.
- Success criterion: With the patch, driving `flow._drive_and_act(cfg, [<drive set>], …, batch=[<all requested ids>])` on the real-git fixture of `template/tests/test_flow_resume_stack_prereqs.py` (`ResumeStackPrereqs`: stack mode, a non-stub publisher, `gh` stubbed):
  (1) **#652.** `P` finished with its PR CLOSED. `Q` finished with its PR OPEN, `Depends on: P`, its branch cut from `origin/fix/P` (so it contains `P`'s commit). `D` in the drive set with `Depends on: Q`. An unrelated `U` in the drive set. Run with batch `["P", "Q", "D", "U"]`. `Q` is not carried. `D` is never built and stays PLANNED, and ONE stderr line names `issue_Q` and `issue_D` and gives the reason (it names `issue_P` as the cause), and its advice is the new cascade hint (see Scope), not the `open` hint: `Q`'s PR is already open, so "get issue_Q's PR open" would be wrong. No commit of `P`'s branch is reachable from origin's line (if a line exists at all). `U` is built and COMPLETE: the run goes on.
  (2) **#624.** `U` finished with its PR CLOSED (not clean). `D` finished, PR OPEN, `Depends on: U`, its branch cut from `origin/fix/U`. `E` in the drive set with `Depends on: D`. Batch `["U", "D", "E"]`. `E` is never built, stays PLANNED, and is named on one stderr line with `issue_D`. No commit of `U`'s branch is on the line.
  (3) **Chain.** `P` (CLOSED) ← `Q` (OPEN, `Depends on: P`) ← `R` (OPEN, `Depends on: Q`), with `D` in the drive set `Depends on: R`: `D` is held. Not clean spreads through any number of finished ids.
  (4) **Unchanged.** Every existing test in `test_flow_resume_stack_prereqs.py` passes. In particular a clean `Q` on a clean `P` is still carried (`test_a_clean_finished_prerequisite_is_on_the_line_its_dependent_builds_on`, `:176`), and a not-clean `P` with no finished dependents still holds only its own dependents (`test_a_closed_prerequisite_holds_only_its_dependents`, `:226`).
  Pre-fix, in (1) and (2) `D` / `E` is built (in `self.seen`) on a line holding the closed bundle's commit. That is the RED.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: Make "not clean" spread along plain `Depends on` edges between the finished ids the pre-wave carry judges, so a finished id built on a not-clean one is itself not clean: not carried, its dependents held and named with the cause. The held line for a cascaded id uses a NEW `_CARRY_HINTS` entry (`flow.py:858-864`) whose text names the cause, e.g. "{name} was built on {cause}, which is not carried (see its line): get {cause} carried, or re-drive {name} on a base without it, then re-issue"; the `.format(...)` call at `flow.py:951-952` gains the cause. Also in scope, one clause: update the second sentence of `docs/07-crosscutting.md:686-691` and the `_carry_finished` docstring (`flow.py:883-885`) to say a not-clean finished id also holds the finished ids built on it, and their dependents. / out of scope: a finished id that becomes not clean only DURING the fold (state-clean, but its merge fails and the fold records it in `skipped`, `integrate.py:433-439`, `flow.py:937-938`) while a later finished id that contains its commits is still merged in the same fold. That id's PR is open and reviewed, so this is a conflict, not unreviewed work reaching the line; handling it needs pruning dependents during the fold, a larger change. It is a known residual for the human to confirm at sign-off; a prerequisite of a finished id that is NOT one of the requested ids (it is not judged by the carry; #647's `_runnable` rule covers drive-set dependents only); `Stacks on` and `Depends on (merged)` edges between finished ids (the carry's rule is plain `Depends on`, `flow.py:893-897`); a drive-set bundle that is not accepted or held this run, with a finished dependent made COMPLETE ahead of it (the #624 residual, stated exactly in `results/issue_624/brief.md`, recorded in #624's tracker comment as a known residual rather than lost); which head the carry folds (#653).

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

Review issue #652 / #624: prevent finished prerequisites rejected before folding from reaching a resumed stack through finished dependents, while allowing unrelated clean work to proceed.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The bounded pre-fold dependency invariant has falsifiable cases for direct, transitive, and unrelated work; fold-time failures are expressly excluded (brief.md:16; brief.md:29; target/docs/07-crosscutting.md:692). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only the production change leaves all tests runnable and produces five assertion failures, including dependent builds that should have been held (review-rerun.log:23; review-rerun.log:88; target/template/tests/test_flow_resume_stack_prereqs.py:394). |
| C3 Change | PASS | The three changed files stay within the requested carry behavior, regression coverage, and documentation scope; the restored target diff exactly matches patch.diff (target/template/src/pdca_harness/flow.py:960; target/template/tests/test_flow_resume_stack_prereqs.py:429; review-checks.log:8). |
| C4 Verification (red→green) | PASS | The same 18-test module fails five assertions without the production fix and passes after stash restoration; this independently corroborates the frozen gate (review-rerun.log:86; review-rerun.log:105; gate-logs/C4-verify.log:10). |
| C5 Causal adequacy | PASS | Real branch ancestry reproduces the forbidden carry, and the fixed graph closure excludes rejected descendants both from folding and from accounting for an existing line; no capability-probe workaround was introduced (target/template/src/pdca_harness/flow.py:889; target/template/src/pdca_harness/flow.py:961; target/template/tests/test_flow_resume_stack_prereqs.py:429; target/template/tests/test_flow_resume_stack_prereqs.py:452). |
| T1 Structure | PASS | Dependency propagation remains local to the pre-wave carry and reuses the existing dependency parser and hold/report machinery, without changing public interfaces (target/template/src/pdca_harness/flow.py:871; target/template/src/pdca_harness/flow.py:991). |
| T2 Shape | PASS | Independent diff whitespace check, documentation lint, and 22-page render with internal-link audit pass; frozen host-parity output agrees (review-checks.log:1; review-checks.log:9; gate-logs/host-ci-docs.log:10). |
| T3 Runtime | PASS | Independent offline suite passes 2,374 tests with two skips; the frozen root-suite log separately shows all 24 render/update tests passing (review-suite.log:1797; gate-logs/T3-suite.log:54). |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the deferred row requires the substantive contribution audit at publish (gate-logs/T4-contribution.log:10). |
| T5 Judgment | NEEDS-HUMAN | Confirm merged and closed/rejected prior art by all three affected file paths before contribution — the brief records flow.py history but omits the changed docs/test paths, and this target has only one synthetic base commit and no remotes to independently establish that history (brief.md:34; review-checks.log:3). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Accept the bounded pre-fold protection and its remaining limits — fold-time merge failures can still bring failed-prerequisite ancestry through a dependent; out-of-batch/other-edge cases, the stated #624 residual, and head selection remain excluded from this fix (brief.md:29; target/docs/07-crosscutting.md:696; target/template/src/pdca_harness/flow.py:920). |

Independent evidence: `review-rerun.log` records the production-only stash, red assertions, successful restoration, and green run. Temporary test fixtures stayed under this review sandbox through `TMPDIR`. `review-suite.log` records the subsequent full offline suite. The disposable target is current for this patch; no stale-target caveat applies. Source citations above refer to the supplied patched target, not the brief's older line numbers.

The mixed-target regression now proves an actual line exists, carries clean X, and excludes P/Q ancestry both at dependent build time and on the resulting line (target/template/tests/test_flow_resume_stack_prereqs.py:440). The documentation and docstring explicitly preserve the fold-time residual; the previously reported spacing defect is also resolved (target/template/src/pdca_harness/flow.py:970). No new builder-fixable defect was found.

Frozen gate evidence was read for every logged row. The C5 scanner reports only that no new test file was added (gate-logs/C5-prod-path.log:10); causal confidence instead comes from the independent production-reversion run and real-git assertions. The instance-scoped wrappers are not required in this disposable target. Copier is not importable in this review interpreter, so root render/update coverage rests on the frozen execution, which shows those cases actually ran and passed (gate-logs/T3-suite.log:38; gate-logs/T3-suite.log:54). The local docs checks and offline suite were independently executable. The brief's Python/git dependencies were exercised; the declared gh stub permits the forbidden ancestry and demonstrably reproduces it before the fix, rather than making the failure impossible.

The available INTEGRATION template leaves project-specific human-only items unenumerated (target/template/docs/INTEGRATION.md.jinja:80). No additional configured human-only list was supplied. Prior-art confirmation must cover `docs/07-crosscutting.md`, `template/src/pdca_harness/flow.py`, and `template/tests/test_flow_resume_stack_prereqs.py`; no other checkout was consulted.

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — issue 652 (carry-not-clean-cascades-across-finished-ids)

Lenses: correctness bugs the patch adds, and reuse / simplification / efficiency. All
`path:line` refs are on the target at `$PDCA_TARGET`. Gate evidence: C4 is red without the
fix and green with it (`gate-logs/C4-verify.log`, 5 failures pre-fix), and T3 passes in full
(`gate-logs/T3-suite.log`, 2374 tests OK).

I found no correctness bug. The cascade does what the brief asks, and the loop always ends.
Two small notes and one point for the human:

- NEEDS-HUMAN [human] — `template/src/pdca_harness/flow.py:892` spreads "not clean" from
  every entry in `why`, including the `edge` case from `_finished_head`
  (`flow.py:854-856`: PR MERGED, but its head is on neither the base nor the line). A
  squash-merge or rebase-merge into the base produces exactly that state, because the
  original head commit never lands on `origin/<base>`. In that case `P`'s work *was*
  reviewed and merged, yet a finished `Q` built on it is now held with the `built_on`
  advice ("get issue_P carried, or re-drive issue_Q on a base without it",
  `flow.py:866-867`). That advice is confusing for a squash-merged prerequisite. Before the
  patch, `Q` was carried. The brief's invariant ("judged not clean before the fold, from
  its PR state and head") does cover this case literally, so the code matches the brief.
  The human should decide whether an `edge` hold should cascade, or whether the cascade
  should cover only the `open`-hint reasons (closed PR, missing branch, state unreadable).
  No test covers a MERGED-not-on-base `P` with a finished dependent.

- `template/src/pdca_harness/flow.py:963-964`: `foreign_commit` now leaves out the heads of
  cascaded ids. So when an old line on origin holds a cascaded `Q`, every finished id of
  that target is held, clean ones included (the `line` hint). This follows from the
  invariant and is documented (`docs/07-crosscutting.md:692-696`: "none of
  them ... accounts for a commit on the line"). The new test
  `test_a_held_ids_head_does_not_vouch_for_an_old_line` covers it. No action needed. I
  list it only because it widens the hold beyond `Q`'s own dependents.

- Reuse nit (not blocking): `template/src/pdca_harness/flow.py:882-886` parses each
  finished id's plain `Depends on` with the same `brief.depends_on(bp) if bp.exists()` /
  `cfg.bundle(dep).name` pattern as the dependents loop at `flow.py:931-935`. It also calls
  `cfg.bundle(dep)` twice per edge (in the filter and in the value). A small helper, such
  as `_plain_dep_names(cfg, d) -> list[str]`, would remove the duplicate and the second
  call. The cost is trivial (a handful of briefs), so this is tidiness only.

- Tests (`template/tests/test_flow_resume_stack_prereqs.py`, new section (9)): these cover
  the brief's criteria (1)-(3), the "rest is still carried" mixed case
  (`test_a_clean_finished_id_beside_them_is_still_carried`, which now makes the
  "P's commit is not on the line" check meaningful because a line exists), and the
  old-line case. They check the `built_on` hint text and that the `open` hint is absent.
  The chain test asks for the ids in reverse order (`["R", "Q", "P", "D"]`), so the
  fixed-point loop is tested on input that is not in dependency order. I found no weak
  assertion.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — Confirm merged and closed/rejected prior art by all three affected file paths before contribution — the brief records flow.py history but omits the changed docs/test paths, and this target has only one synthetic base commit and no remotes to independently establish that history (brief.md:34; review-checks.log:3).
- [x] Validation — fitness-to-purpose — Accept the bounded pre-fold protection and its remaining limits — fold-time merge failures can still bring failed-prerequisite ancestry through a dependent; out-of-batch/other-edge cases, the stated #624 residual, and head selection remain excluded from this fix (brief.md:29; target/docs/07-crosscutting.md:696; target/template/src/pdca_harness/flow.py:920).
- [x] `template/src/pdca_harness/flow.py:892` spreads "not clean" from every entry in `why`, including the `edge` case from `_finished_head` (`flow.py:854-856`: PR MERGED, but its head is on neither the base nor the line). A squash-merge or rebase-merge into the base produces exactly that state, because the original head commit never lands on `origin/<base>`. In that case `P`'s work *was* reviewed and merged, yet a finished `Q` built on it is now held with the `built_on` advice ("get issue_P carried, or re-drive issue_Q on a base without it", `flow.py:866-867`). That advice is confusing for a squash-merged prerequisite. Before the patch, `Q` was carried. The brief's invariant ("judged not clean before the fold, from its PR state and head") does cover this case literally, so the code matches the brief. The human should decide whether an `edge` hold should cascade, or whether the cascade should cover only the `open`-hint reasons (closed PR, missing branch, state unreadable). No test covers a MERGED-not-on-base `P` with a finished dependent.
- [x] **The invariant is wider than the criterion, and a fold-time "not clean" is not covered.** The brief's invariant says "The pre-wave carry never puts onto the line work it has judged not clean, directly or through another finished bundle's branch". The criterion only spreads "not clean" from the PR-state judgment that runs before the fold (`_finished_head`, `flow.py:913-920`). An id can also become not clean *during* the fold. `integrate.fold` with `skipped` records a merge failure for one bundle "and the next bundle is merged" (`integrate.py:334-336`, `:433-439`). The carry then adds it to `why` after the fold (`flow.py:937-938`). So a finished `P` that is state-clean but skipped at fold time (a conflict, as in `test_of_two_conflicting_prerequisites…`, `:246`), followed in the same fold by a finished `Q` with `Depends on: P` whose branch contains `P`, still puts `P`'s commits on the line. A fix that only spreads the pre-fold `why` before line 927 meets criteria (1)–(3) and still breaks the stated invariant. The planner should either narrow the invariant to "judged not clean before the fold" and list the fold-time case as out of scope, or add a criterion: a `P` skipped at fold time means `Q` is not folded. Doing that means pruning dependents during the fold or re-folding without them, which is a larger change.
- [x] **The fix contradicts the documented contract the brief cites, and no doc update is in scope.** The brief draws its invariant from `docs/07-crosscutting.md:686-691`. The second sentence there says "A finished prerequisite that is not clean holds **only** the bundles whose plain `Depends on` names it". The `_carry_finished` docstring says the same: "Any other finished id goes into `held`, so only its plain `Depends on` dependents wait" (`flow.py:883-885`). After the fix, a closed `P` also holds `Q`'s dependents, so both texts become wrong. Yet the brief cites both as the source of the invariant. Scope and Citations do not list updating either one. Either add the doc and docstring edits to Scope as one clause, or a reviewer will flag them as drift (or as an unplanned change) during Check.
- [x] **#624 is closed as a duplicate while its literal shape is explicitly left out.** The thread describes #624 as "the hold of an **unpublished** bundle doesn't cascade through a pre-run COMPLETE dependent". Criterion (2) swaps in "`U` finished with its PR CLOSED". The brief's Scope then excludes "a drive-set bundle whose own push fails mid-run … the rare residual of #624, not briefed". There is no `sources/` directory in this bundle, so I could not check #624's own thread or the human's Plan decision against the brief. If #624 is closed as a duplicate of this bundle, that residual has no tracker item left. Before #624 closes, the human should confirm the residual is acceptable or file a follow-up for it.
- [x] **The 652 → 653 ordering is stated in prose but not declared.** The Ordering note says "Separate waves: 652 first, and 653 builds on it". The brief declares only `Conflicts with: 653`, which separates the two into different waves but does not set their order. There is no `dependency-state.json` here, so I could not check whether 653's brief declares `Depends on: 652` / `Stacks on: 652`. If it doesn't, the "652 first" order is not enforced by anything.
- [x] **The hint for a cascaded hold is not specified.** Criterion (1) requires that the held line "names `issue_P` as the cause", but the brief does not say which `_CARRY_HINTS` entry (`flow.py:860-866`) `Q`'s line uses. The existing hints are worded for the id itself. For example, `"open"` says "get {name}'s PR open", which would tell the operator to reopen `Q`'s PR, but `Q`'s PR is already OPEN. The useful action is to fix `P`, or to remove `Q`'s `Depends on: P` edge. The brief should state the expected advice, or a hint key, so that the line's wording can be checked rather than left to Do.
- [x] C3 Change — Confirm the recorded prior-art conclusions for the affected paths — the brief reports merged and closed-PR searches, but the supplied one-commit repository has no remote or review history to independently settle duplication/rejected-work status (brief.md:34; review-target.log:1).

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
- By / date: Eduard Ralph / 2026-10-10

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 5 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
- issue_652: the cascaded-hold advice ("get P carried, or re-drive Q…") is confusing when P was squash/rebase-merged (the `edge` case); revisit the wording, and add a test for a MERGED-not-on-base P with a finished dependent.
