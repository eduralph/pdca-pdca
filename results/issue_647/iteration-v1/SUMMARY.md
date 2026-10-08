# Result — issue 647 / stack-holds-dependent-of-out-of-batch-unmerged-prereq

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: In stack mode a dependent whose plain `Depends on` prerequisite is NOT one of
  the ids the run was asked to drive is built on a base missing that prerequisite, whenever
  the prerequisite is COMPLETE but its PR has not merged into the target base. `_runnable`
  accepts an out-of-batch prerequisite once it is COMPLETE
  (`template/src/pdca_harness/flow.py:710`); COMPLETE means only "a draft PR was opened",
  and nothing in the run carries an out-of-batch prerequisite's work into the base (the
  docstring says so, `flow.py:692-698`). Child-1 fixes this for the same ids re-issued; it
  cannot reach (i) the `flow_batch` sweep path, which gets a fresh line every run by design
  (finished bundles leave the sweep, `flow.py:2160-2170`), or (ii) a dependent driven in a
  different command from its prerequisite. Separately, `merged.is_merged`
  (`merged.py:32-59`) returns True for any PR whose state is MERGED, without checking it
  merged into the target base: a `"stacked-pr"` record whose PR targets an integration branch
  (`publish.py:420-421`, `"base": pr_base`), or an `Onto branch` record (`"stacked"`,
  `publish.py:540-541`), can be MERGED while the target base lacks its work — so even
  `Depends on (merged)` (#186) can be satisfied by a merge that never reached the base. And
  `is_merged` calls `gh` with no `OSError` guard (`merged.py:50-51`), so a missing `gh`
  crashes the run with a traceback.
- Success criterion: With the patch, in stack mode with publishing on: (1) a run that
  drives `D` (`- **Depends on:** P`) where `P` is NOT in the run's requested batch, is
  COMPLETE, has a non-empty `patch.diff` and a resolvable target, and its PR is OPEN, does
  NOT build `D`: `D` stays PLANNED, one stderr line names `D`, `P` and the reason — it must
  contain the substring `not merged into main` (`main` being `D`'s target base), which
  today's generic "prerequisite(s) not ready" line does not — with advice
  (name `P` in the same `pdca flow <ids>` command so its line carries it, or wait until its PR
  merges into the base), and an unrelated bundle `U` in the same run builds as today.
  Pre-fix `D` is built — RED. Shown for both entry points: `flow_ids` (named ids not
  including `P`) and `flow_batch` (sweep, `P` already COMPLETE). (2) `P`'s PR MERGED with its
  record's `base` equal to the target base and mode not `"stacked"` ⇒ `D` builds on the base
  as today. (3) `P`'s PR MERGED but its record's `base` is another branch (a `"stacked-pr"`
  record against an integration branch — e.g. #591's own record today: `"mode":
  "stacked-pr"`, `"base": "pdca-integration/main"`) or mode `"stacked"`, or its record's
  `repo` differs from `D`'s target repo ⇒ `D` is held, as in (1); in `_runnable` the same
  rule now also governs `Depends on (merged)` — a `Depends on (merged): P` dependent waits in
  this case too, and still builds once `P` merged into `D`'s base. (4) `P` COMPLETE
  with an empty or missing `patch.diff` ⇒ `D` builds (nothing to wait for). (5) `gh` missing
  (`OSError`) or failing while reading `P`'s PR ⇒ `D` held, named, no traceback; the run goes
  on. (6) Unchanged: a prerequisite in the run's requested batch (child-1's carry), `Stacks
  on` edges, `--no-publish` runs, merge mode, and a dry-run (stub publisher; asks no host,
  holds nothing). `merged.is_merged` itself is NOT changed: its other callers — merge mode's
  resume check (`merge.py:233`) and `status`'s `_blocked_by` (`cli.py:1084`) — keep today's
  answer; a test asserts `merged.is_merged` still returns True for a MERGED `"stacked"`
  record (the merge-mode resume case).
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: In stack mode with publishing, hold a dependent whose plain `Depends on`
  prerequisite is outside the run's requested batch and not merged into the target base,
  instead of building it. Add a new function in `merged.py` (beside `is_merged`, e.g.
  `merged_into(cfg, dep_id, repo, base)`) that `_runnable` alone calls for out-of-batch
  prerequisites — both plain `Depends on` (stack mode, publishing) and `Depends on (merged)` —
  passing the DEPENDENT's resolved target (`publish._resolve_target(D)`). It counts MERGED
  only when the record's `repo` and `base` equal that target and mode is not `"stacked"`, and
  reads `gh` failures — including a missing `gh` (`OSError`) — as "not merged" with a
  message, never a traceback. Leave `merged.is_merged` and its callers (`merge.py:233`,
  `cli.py:1084`) unchanged. Update `_runnable`'s docstring and the stack-mode paragraph in
  `docs/07-crosscutting.md` (near `:658-677`) to say a `Depends on` prerequisite outside the
  run's ids now waits for its merge.
  / out of scope: carrying out-of-batch prerequisites onto the line (rejected in
  iteration-v1..v3 — do not reintroduce); in-batch / re-issued prerequisites (child-1);
  `Stacks on` (#123, unchanged); merge mode (#531) and `--no-publish`; changing which ids the
  sweep path includes; changing `merged.is_merged` or the `status` display.

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 Verification (worktree mismatch): fail — issue_647: lane pdca-harness.pdca-wt is busy (another Do or gate run holds it) — refusing to reconstruct under a live run; retry when it finishes.
- C5 Causal adequacy: none — reviewer + human sign-off

## 4. Conformance (Check — stack)
- T1 Structure: none — (no gate configured)
- T2 Shape: none — (no gate configured)
- T3 Runtime: none — (no gate configured)
- T4 Contribution: none — (no gate configured)
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Review task: hold stack-mode dependents until an out-of-batch prerequisite has merged into the dependent’s target repository and branch, while preserving unrelated work and existing carry behavior.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The readiness contract distinguishes an opened PR from a contribution present in the dependent’s base, with falsifiable entry-point and compatibility cases; target/template/src/pdca_harness/flow.py:696 and target/template/tests/test_flow_out_of_batch_prereq_hold.py:164. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only production changes reproduced nine assertion failures (including both entry points building D incorrectly) and one missing-gh exception across 21 tests; target/template/tests/test_flow_out_of_batch_prereq_hold.py:164 and review-red.log:1. |
| C3 Change | PASS | The specified hold admits no work-bearing prerequisite on an open or differently targeted PR, while preserving empty-patch and legacy is_merged behavior; target/template/src/pdca_harness/flow.py:725 and target/template/src/pdca_harness/merged.py:81. |
| C4 Verification (red→green) | NEEDS-HUMAN | Obtain a successful authoritative gate rerun after the lane unlocks, and discharge release-upgrade coverage — independent red→green succeeds, but the frozen worktree-mismatch row has no log key or log file, and upgrade tests lack release tags; check-gates.json:33, review-green.log:3, target/tests/test_update_compat.py:55. |
| C5 Causal adequacy | PASS | Readiness now tests the missing prerequisite-in-base condition at admission; this is a scheduling precondition, not a capability probe hiding an eager/load-time side effect; target/template/src/pdca_harness/flow.py:728 and target/template/src/pdca_harness/merged.py:98. |
| T1 Structure | PASS | Both entry points share the admission rule, and the separate merged_into predicate contains the new target semantics without altering legacy callers; target/template/src/pdca_harness/flow.py:2148 and target/template/src/pdca_harness/merged.py:67. |
| T2 Shape | PASS | The patch stays within readiness, its explanatory docs, and regression coverage; diff whitespace validation, documentation lint, and production-import scanning pass; target/docs/07-crosscutting.md:704 and target/template/tests/test_flow_out_of_batch_prereq_hold.py:29. |
| T3 Runtime | PASS | The 21-case regression suite and 2,359-test offline suite pass after restoration, covering missing/failing gh and continued unrelated work; target/template/tests/test_flow_out_of_batch_prereq_hold.py:244 and review-green.log:3 (offline suite: two skips). |
| T4 Contribution | NEEDS-HUMAN | Confirm merged and closed/rejected prior art by every affected path — local history contains only the synthetic base commit and no remote, so the brief’s reported history search cannot establish that this work is still needed; brief.md:114 and target/template/src/pdca_harness/flow.py:681. |
| T5 Judgment | PASS | Holding rather than carrying unrequested work matches the agreed scope, and narrowing the new predicate preserves merge-mode/status semantics; no additional Plan re-entry or contested capability guard was found; target/template/src/pdca_harness/flow.py:2143 and target/template/tests/test_flow_out_of_batch_prereq_hold.py:307. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether waiting for a direct merge into the dependent’s recorded target, with same-command carry as the alternative, fits the intended workflow — offline tests establish admission behavior but do not exercise a live GitHub merge and subsequent build; target/docs/07-crosscutting.md:704 and target/template/tests/test_flow_out_of_batch_prereq_hold.py:116. |

Independent evidence: the disposable target was readable and contained the prerequisite implementation. Production files were stashed while retaining the new regression tests, then restored with stash pop. The same command, `cd target/template && PYTHONPATH=src python3 -m unittest tests.test_flow_out_of_batch_prereq_hold`, changed from exit 1 (nine failures, one error) to exit 0 (21 passing tests). Full output is in `review-red.log` and `review-green.log`. A reverse-apply check of the supplied patch succeeds after restoration; no source changes were made by this review.

Additional checks: `PYTHONPATH=src python3 -m unittest discover -s tests` in target/template passed 2,359 tests with two skips (`review-suite.log`). `git -C target diff --check`, the documentation linter (`review-docs.log`), and the production-import scanner (`review-production-scan.log`) passed. The root suite initially returned 77 because system Python could not import Copier (`review-root-suite.log`); rerunning with the installed Copier virtual environment’s interpreter passed 19 tests with one skip (`review-root-copier.log`). The upgrade-from-release class cannot run without release tags; the fresh-render checks did run. This is a target-evidence limitation, not a patch defect.

Frozen gate adjudication: check-gates.json contains one failing deterministic row, worktree-mismatch, whose stated cause is another run holding the lane lock. There is no log key on that row and no gate-logs directory in this bundle. The other ten rows have result none; none is deferred. The lock condition cannot be reconstructed in this isolated target. Accordingly the frozen red is a host caveat, not a confirmed verification defect, and the independent passing checks do not replace that authoritative gate run.

Prior-art investigation: `git -C target log --all --oneline -- template/src/pdca_harness/flow.py template/src/pdca_harness/merged.py` returns only `dbf4c1c pre-fix base c1f2306984bb9b95469b08de3cea83598d48820f`; `git -C target remote -v` returns nothing. No merged-history or closed/rejected-work evidence is supplied for independent inspection. The available INTEGRATION template leaves project-specific human-only items as TODO (target/template/docs/INTEGRATION.md.jinja:80), so it supplies no additional enumerated items.

No confirmed patch defect was found. This review is advisory; the missing gate evidence, prior-art confirmation, release-upgrade coverage, and fitness decision remain explicit human follow-up.

### Advisory — code-review

# Advisory code review — issue_647

Overall the patch does what the brief asks. `merged_into` is a new function next to `is_merged`, and `is_merged` is untouched. The `OSError` guard comes from reusing `pr_state`. The hold is limited to stack mode with publishing on and no dry-run. I ran `tests.test_flow_out_of_batch_prereq_hold` and `tests.test_flow_slice` on the target with the patch applied: 129 tests, OK. Findings:

- NEEDS-HUMAN [impl] — A dependent whose brief has no usable `Repo + branch target` (no field, or no `@ branch`) is now held forever. `template/src/pdca_harness/flow.py:731` gets `("", "")` from `publish._resolve_target`, and `template/src/pdca_harness/merged.py:98` then rejects every record because `rec["repo"] != ""`. This breaks a case that worked before: a `Depends on (merged)` dependent with no target used to build once `is_merged` said True, and now it never builds. The plain `Depends on` hold also fires for such a dependent, even though publish treats a target-less bundle as non-contributing (`publish.py:182-188`, `skip_if_no_target`) and nothing would be published on a wrong base. The stderr line also reads "not merged into  ()" (`flow.py:741-746`). Suggested fix: when the dependent's target is empty, skip the #647 hold and keep the old `is_merged` answer for `Depends on (merged)`, or else name the missing target in the message. Add a test for it.
- NEEDS-HUMAN [impl] — The message for an out-of-batch `Depends on (merged)` prerequisite that is not COMPLETE is now wrong (`flow.py:725-733`). Before, a PLANNED or DISCONTINUED prerequisite here gave "skipped — prerequisite(s) not ready". Now it goes through `merged_into`, which returns False without printing anything (`merged.py:84-85`). The user sees "held — … not merged into main … wait until their PR merges". For a DISCONTINUED prerequisite there is no PR to wait for. The bundle is still held either way. Only the reason and advice are wrong. Suggested fix: check `state != COMPLETE` first so it goes to `unmet`, as the plain-dependency branch already does.
- `template/src/pdca_harness/flow.py:741` — `target or ("", "")` is dead code: `unmerged` is only appended after `target` is set at `:731`. It could be removed. Nit.
- `template/src/pdca_harness/flow.py:727` and `merged.py:84` — the prerequisite's state is computed twice (once in `_runnable`, again in `merged_into`), and `cfg.find_bundle(dep)` runs up to three times per dependency. Cheap, but `merged_into` already returns False for non-COMPLETE prerequisites, so the `== COMPLETE` check in `_runnable` is only there to route non-COMPLETE plain dependencies to `unmet`. A short comment saying that would help. Nit.
- `template/src/pdca_harness/flow.py:732` — `merged_into` runs `gh pr view` once per (dependent, prerequisite) pair per wave, with no cache. When several dependents share one out-of-batch prerequisite, the same PR is fetched over the network each time. A small per-run cache would fix it. Efficiency nit, not a bug.
- NEEDS-HUMAN — The C4 gate's `fail` (`check-gates.json`, rule `worktree-mismatch`) is not a verdict on this patch. The lane was busy ("refusing to reconstruct under a live run"), so the red→green check never ran. There is no gate log for it in `gate-logs/`. Re-run C4 before sign-off. My local test run only shows the tests pass with the fix applied. It does not show they fail without it.

The tests look sound. They import only modules, stub `gh` at `subprocess.run`, cover both `flow_ids` and `flow_batch`, and pin `is_merged`'s unchanged answer for a `"stacked"` record. The single-line assertion in `_held` matches only the `flow:` line, because `merged.py`'s line names the bare id `P`, not `issue_P`. So `merged_into`'s extra stderr line does not trip it.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] C4 Verification (red→green) — Obtain a successful authoritative gate rerun after the lane unlocks, and discharge release-upgrade coverage — independent red→green succeeds, but the frozen worktree-mismatch row has no log key or log file, and upgrade tests lack release tags; check-gates.json:33, review-green.log:3, target/tests/test_update_compat.py:55.
- [ ] T4 Contribution — Confirm merged and closed/rejected prior art by every affected path — local history contains only the synthetic base commit and no remote, so the brief’s reported history search cannot establish that this work is still needed; brief.md:114 and target/template/src/pdca_harness/flow.py:681.
- [ ] Validation — fitness-to-purpose — Decide whether waiting for a direct merge into the dependent’s recorded target, with same-command carry as the alternative, fits the intended workflow — offline tests establish admission behavior but do not exercise a live GitHub merge and subsequent build; target/docs/07-crosscutting.md:704 and target/template/tests/test_flow_out_of_batch_prereq_hold.py:116.
- [ ] A dependent whose brief has no usable `Repo + branch target` (no field, or no `@ branch`) is now held forever. `template/src/pdca_harness/flow.py:731` gets `("", "")` from `publish._resolve_target`, and `template/src/pdca_harness/merged.py:98` then rejects every record because `rec["repo"] != ""`. This breaks a case that worked before: a `Depends on (merged)` dependent with no target used to build once `is_merged` said True, and now it never builds. The plain `Depends on` hold also fires for such a dependent, even though publish treats a target-less bundle as non-contributing (`publish.py:182-188`, `skip_if_no_target`) and nothing would be published on a wrong base. The stderr line also reads "not merged into  ()" (`flow.py:741-746`). Suggested fix: when the dependent's target is empty, skip the #647 hold and keep the old `is_merged` answer for `Depends on (merged)`, or else name the missing target in the message. Add a test for it.
- [ ] The message for an out-of-batch `Depends on (merged)` prerequisite that is not COMPLETE is now wrong (`flow.py:725-733`). Before, a PLANNED or DISCONTINUED prerequisite here gave "skipped — prerequisite(s) not ready". Now it goes through `merged_into`, which returns False without printing anything (`merged.py:84-85`). The user sees "held — … not merged into main … wait until their PR merges". For a DISCONTINUED prerequisite there is no PR to wait for. The bundle is still held either way. Only the reason and advice are wrong. Suggested fix: check `state != COMPLETE` first so it goes to `unmet`, as the plain-dependency branch already does.
- [ ] The C4 gate's `fail` (`check-gates.json`, rule `worktree-mismatch`) is not a verdict on this patch. The lane was busy ("refusing to reconstruct under a live run"), so the red→green check never ran. There is no gate log for it in `gate-logs/`. Re-run C4 before sign-off. My local test run only shows the tests pass with the fix applied. It does not show they fail without it.
- [ ] C4 Verification (worktree mismatch) FAILED (gating) — issue_647: lane pdca-harness.pdca-wt is busy (another Do or gate run holds it) — refusing to reconstruct under a live run; retry when it finishes.
- [ ] **The brief changes `merged.is_merged` for every caller, but says merge mode stays the same.** Scope says "make `merged.is_merged` count MERGED only for a PR merged into the target base … mode not `"stacked"`". Criterion (6) says merge mode (#531) is "Unchanged". But `is_merged` has two other callers that the brief never names:
- [ ] **"Target base resolved for the bundle" is ambiguous, and `is_merged` can't see the dependent.** `is_merged(cfg: Config, dep_id: str)` (`merged.py:32`) only gets the prerequisite's id. The Invariant says "merged into the **dependent's** target base". The Scope says "record `base` equals the target base resolved for the bundle", which reads as the prerequisite's own `_resolve_target`. These two give different answers when P and D target different bases or repos.
- [ ] **The main "merged elsewhere" case in the brief mostly can't happen on the current code.** The Defect says a `"stacked-pr"` record "whose PR targets an integration branch (`publish.py:420-421`, `"base": pr_base`)" can be MERGED without reaching the base. But `publish.py:282` sets `pr_base = stack_branch if (stack_branch and own_repo and not wave_stacked) else base`, and `publish.py:266-268` explains why: a wave stack-base bundle "opens its PR against its REAL target base … (#593)". `cli.py:1065-1067` says the same: "every PR targets the real base (#593), so it reads ↑main".
- [ ] **This is two or three fixes, not one.** These are separate changes:
- [ ] **Dependency 646 is still PLANNED, and the "requested batch" idea doesn't exist yet.** `dependency-state.json` shows `"646": {"declared": "Depends on", "exists": true, "state": "PLANNED"}`. The Ordering note says this child "needs child-1's 'requested batch' notion". The target `flow.py` has no such idea yet: `_runnable(cfg, wave, batch_names, *, held=…)` at `flow.py:681-682` only has `batch_names`. Do can't start until 646 is COMPLETE and folded in.
- [ ] **Criterion (1)'s message wording isn't specified tightly enough to test.** "one stderr line names `D`, `P` and the reason, with advice (name `P` in the same `pdca flow <ids>` command … or wait until its PR merges)". Today `_runnable` already prints one generic line per skipped bundle (`flow.py:715-716`: "skipped — prerequisite(s) not ready (P)"). So a test that only checks for `D` and `P` passes against the existing message. The brief should name a distinctive substring the test must assert, for example the advice text. Otherwise the "message" part of RED→GREEN is satisfied by code that already exists.

## 7. Proven / not proven
- Proven by which oracle: gates overall = fail (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: iterated-to-Do
- Iteration delta (if iterating): Design is sound and in scope; two confirmed implementation bugs from the code review must be fixed, each with a test: 1. Empty-target regression: when the dependent's resolved target is ("", "") (no `Repo + branch target`, or no `@ branch`), skip the #647 hold and keep the old `merged.is_merged` answer for `Depends on (merged)` — today merged_into rejects every record (merged.py:98) so the dependent is held forever and the message reads "not merged into ()". 2. Wrong reason/advice: an out-of-batch `Depends on (merged)` prerequisite that is not COMPLETE (PLANNED/DISCONTINUED) must go to `unmet` ("prerequisite(s) not ready"), not `unmerged` ("wait until their PR merges") — check state != COMPLETE first (flow.py:725-733), as the plain-dependency branch already does. Also: C4 (worktree mismatch) never ran — lane was busy — so it must produce a real red→green result on the rebuild.
- By / date: Eduard Ralph / 2026-10-04

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 6 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
