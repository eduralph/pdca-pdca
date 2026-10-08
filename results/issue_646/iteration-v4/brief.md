# Brief — re-issued stack-mode flow continues its batch's integration line

> The Plan artifact (docs 02 §PLAN). Do reads ONLY this file.
> Child 1 of the split of #616. Verified against `eduralph/pdca-harness`
> `origin/pdca-integration/main` @ `f594d8e` (`origin/main` @ `c67a14d` plus #531, #590,
> #591 folded). All `path:line` below are on that line. #591's batch-scoped line name is
> REQUIRED by this fix and exists only there until PR #639 merges. `origin/main` @ `c67a14d`
> lacks it (`integration_branch(cfg, base)` has no id list, `integrate.py:62`; no `batch=` on
> `fold` / `_drive_and_act`), so this bundle declares `Depends on (merged): 591` and must not
> be built until #639 is merged into `main`. Once it is, re-resolve every `path:line` below on
> `main` before citing it — the numbers will have moved.

- **Slug:** stack-reissue-continues-batch-line
- **Defect:** In stack mode the recovery for a run that stopped part-way (an integrity stop,
  the pass budget, a crash, Ctrl-C) is to re-issue the same `pdca flow <ids>`. That resumed
  run builds a dependent on a base missing its prerequisite, when the prerequisite finished
  in the earlier run:
  - the finished id is skipped as already terminal (`template/src/pdca_harness/flow.py:2320-2325`),
    so it is not in the drive set and never enters `accepted` or the fold
    (`flow.py:2031`, `:2067-2070`);
  - `_runnable` sees it as out-of-batch (`batch_names` is the drive set, `flow.py:706`) and
    accepts it as ready because it is COMPLETE (`flow.py:710`) — COMPLETE only means a draft
    PR was opened;
  - nothing has been folded yet, so `_point_at_integration` clears the dependent's stack base
    (`flow.py:736-742`) and it is cut from the plain target base.
  The dependent is built, C4-verified and published without its prerequisite. Nothing
  reports it. The earlier run's line is usually still on `origin` under the same name (#591:
  the batch key comes from the ids as asked for, skipped ones included, `flow.py:2357-2363`,
  `integrate.py:67-83`), holding the prerequisite — but the resumed run never uses it, and
  its first in-run fold force-replaces it (`integrate.py:344-345`, `:401`), which strands any
  accepted-but-unpublished bundle whose recorded line tip was on it
  (`publish._line_tip_refusal`, `publish.py:691-726`).
- **Success criterion:** With the patch, in stack mode with publishing on (non-stub publisher),
  real git against a bare `origin`, a run driven as `flow._drive_and_act(cfg, [D], …,
  batch=["P", "D"])` (the shape `flow_ids` produces when `P` is skipped as finished) where
  `P` is COMPLETE, has a non-empty `patch.diff`, a resolvable target, a `publish.json` naming
  a pushed branch and an OPEN PR, and `D` has `- **Depends on:** P`:
  (1) before `D`'s wave is driven, origin's line `integrate.integration_branch(cfg, "main",
  ["P", "D"])` contains `P`'s branch head, and `D`'s recorded stack base
  (`publish.read_stack_base`) names that line and its tip (`publish.read_stack_base_tip`)
  is the line's tip. Pre-fix `D`'s stack base is cleared and no such line holds `P` — RED.
  (2) **Continue, never replace:** when origin already has that line (the earlier run's,
  holding `P` and an accepted-but-unpublished `H` whose recorded `stack-base-tip` is a commit
  on it), the run continues it: the old tip stays an ancestor of the new tip, no force-push
  happens, and after the run `publish._line_tip_refusal` for `H` returns `""`.
  (3) **Append-only across waves:** with a second driven bundle `E` (`Depends on: D`), the
  fold after wave 0 continues the same line without force and without `IntegrationError`;
  it then holds `P` and `D`, and `E`'s stack base names it.
  (4) **Holds, per prerequisite, named on stderr, rest of the run goes on:** each case below
  leaves `P` out of the fold, holds exactly `P`'s dependents in the drive set (they stay
  PLANNED, are not built), prints one line naming `P`, the held dependents and the reason
  with advice that works under (2), and lets an unrelated bundle `U` build:
  (a) `P` has no branch on record; (c) `P`'s PR state is
  CLOSED (not merged); (d) `P`'s PR state cannot be read (no `pr_url`, a `gh` failure, or
  `gh` missing — an `OSError` — never a traceback).
  (5) **Nothing to carry:** `P` COMPLETE with an empty or missing `patch.diff` ⇒ nothing is
  folded, `D` is not held and builds on the base as today. `P`'s PR MERGED ⇒ `P` is handed to
  the fold like an open one; the fold already decides it (`integrate._gone_branch`,
  `integrate.py:442-490`: line has the merged head ⇒ skip; base has it ⇒ take base in;
  otherwise raise).
  (6) **Fail closed:** the pre-wave fold raising `IntegrationError` stops the run before
  wave 0: nothing is driven, stderr names the failure the way the in-run fold's
  "did not integrate; STOPPING" line does (`flow.py:2076-2079`), no traceback.
  (7) **Unchanged:** a run with no named-but-finished id that a drive-set bundle's plain
  `Depends on` names behaves exactly as today (no pre-wave fold, stale stack bases cleared);
  `Stacks on` and `Depends on (merged)` edges do not trigger the carry and keep their
  behaviour (#123, #186); a dry-run (stub publisher) asks no host, holds nothing, and only
  prints the plan; `--no-publish` and merge mode are untouched.
  (8) **Unrelated bundle on a carried line:** when the carry happens, an unrelated wave-0
  bundle `U` (no dependency on `P`) has its stack base pointed at the same line and tip as
  `D` (`publish.read_stack_base` / `read_stack_base_tip`), and its published PR still targets
  the real base `main` (#593) — the same outcome a later-wave `U` gets today. Pre-fix `U`'s
  stack base is cleared.
- **Falsifiability:** RED is reachable offline. `template/tests/test_integrate_stack_bases.py`
  (`StackFoldGit`, `:115`; `_publish`, `:142`) already provides a bare `origin`, a primary
  checkout, a production publish helper that pushes a branch and writes `publish.json`, and
  a `gh` stub. Driving `flow._drive_and_act` with stubbed build/sign-off leaves over `[D]`
  with `batch=["P","D"]` and `P` prepared as above shows `D`'s stack base cleared and no line
  holding `P` today — assertion (1) fails. Runs under the C4 gate as `cd template &&
  PYTHONPATH=src python3 -m unittest tests.test_flow_resume_stack_prereqs`. No network.
  The publisher must NOT be in stub mode for (1)-(6): a stub turns every fold into a dry-run
  (`flow.py:2038`), which records no line (`flow.py:2080`). Patch `flow._publish_bundle` (or
  reuse the fixture's `_publish`) instead of running the publisher leaf.
- **Invariant to restore:** Every bundle a stack-mode run builds is built, verified and
  published on a base that carries all of its declared prerequisites, whether the
  prerequisite was accepted in this run or in an earlier run of the same batch; and within a
  batch the integration line only ever grows — no run replaces commits an earlier run of the
  same batch recorded as a build base. Sources: the wave contract in `_drive_and_act`
  ("a dependent builds on its prerequisite's accepted result within one run"); `_runnable`'s
  docstring, which already states the hazard ("a dependent built on a COMPLETE-but-unmerged
  base would miss the prerequisite", `flow.py:692-698`); the append-only rule in
  `integrate.py:30-34` and docs `docs/07-crosscutting.md:658-664` ("running the same ids
  again gets the same line back"). Not a single-module guard: the property spans the
  readiness check, the fold's start mode, and the stack-base pointing.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Depends on (merged):** 591
- **Ordering note:** First child. Waits for #591 (PR #639) to MERGE into `main`: the fix and
  its test call `integration_branch(cfg, base, batch)` and `batch=` keywords that exist only
  with #591, so on a base without it both C4 legs would fail with a `TypeError` and red could
  not be told from green. A merge wait (not a plain `Depends on`) because a plain out-of-batch
  edge is satisfied by COMPLETE alone — the very hazard this issue is about. child-2 (#647)
  stacks on this one.
- **Surfaces:** data
- **Difficulty:** high — `_drive_and_act` gains a pre-wave step that feeds the same
  `integ` / `folded_tips` / `held_unpushed` bookkeeping the in-run fold uses; `_runnable`'s
  notion of "in batch" widens to the requested ids; the fold is called in its existing
  "continue if origin has it" start mode; a PR-state read with a missing-`gh` guard; docs.
  The reviewer must hold #593's in-run fold contract and #591's batch scoping in view.
- **Scope:** Make a re-issued stack-mode `pdca flow <ids>` carry the named ids that are
  already finished (COMPLETE, patched, targeted) onto its batch's integration line before
  wave 0, CONTINUING origin's line when it exists (append-only, no force) and starting it
  fresh only when it does not; then point the run's bundles at it exactly as later waves
  already are. The carry happens only when some bundle in the drive set names such an id in
  its plain `Depends on`; when it happens, every carryable finished named id is carried (the
  line is the batch's line, as the in-run fold carries every accepted bundle), and every
  same-target runnable wave-0 bundle — including an unrelated `U` — is pointed at it
  (`_point_at_integration`, `flow.py:722-742`; its PR shows the carried changes until they
  merge, as any later-wave PR does). A dependent held for some other reason (a
  `Depends on (merged)` wait, another held prerequisite) does not cancel the carry: the line
  is the batch's own, not that dependent's. A finished named id that cannot be carried
  (criterion 4a, 4c, 4d) holds only its own dependents — the same `held_unpushed` path the in-run
  fold uses (`flow.py:2052-2058`, `:712-713`) — and the hold message's advice must be one that
  works now the line is kept (e.g. "publish it with `pdca publish <id>`, then re-issue the
  same command"; for a closed PR, "re-open it or re-drive <id>"; for an unreadable state,
  say what could not be read). A failing pre-wave fold stops the run before wave 0. Update
  the stack-mode paragraph in `docs/07-crosscutting.md:658-677`, the "resuming across runs
  is #616" wording in `publish.py:345`, `:696`, `:726`, and the "known cross-run limit (#616)"
  docstring in `drift.py:58-61` so they describe the kept line. Existing tests pin the old
  wording — `template/tests/test_integrate_stack_bases.py:834-852` (asserts `"#616"` and
  `"re-drive it in a new run"`) and `:1012` (asserts `"#616"`): update those assertions to the
  new advice text in the same patch (they are in Do's review surface, and C4 keeps
  `tests/*.py`, so they must pass post-fix).
  / out of scope: a prerequisite that is NOT one of the requested ids, including the
  `flow_batch` sweep path (child-2); `merged.is_merged`'s "merged where" rule (child-2);
  `Depends on (merged)` semantics (#186, unchanged); `Stacks on` (unchanged); merge mode
  (#531); split children adopted mid-run by an earlier run (name the gap in a docstring);
  rebuilding the line from scratch; a line on origin that an outside party rewrote (the
  continued fold merges onto whatever origin has — say so in the docstring); pruning old
  integration branches (#454).
- **Repro instruction:** On `origin/pdca-integration/main`, in `template/` with
  `PYTHONPATH=src`, using the `StackFoldGit` shape: plan and publish `P` (`org/repo @ main`,
  a patch adding a file), mark it COMPLETE (sign-off accept, then `publish.json` written after
  it), stub `gh pr view` to report `OPEN`. Plan `D` with `- **Depends on:** P` and a patch that
  needs `P`'s file. Call `flow._drive_and_act(cfg, [D], do_publish=True, batch=["P", "D"], …)`
  with build/sign-off leaves stubbed and `flow._publish_bundle` patched; wrap
  `flow._drive_wave` to record `D`'s stack base when its wave runs. Observed: `D`'s
  `stack-base` is absent and no line on `origin` holds `P`.
- **External dependencies:** none
- **Test file:** template/tests/test_flow_resume_stack_prereqs.py (NEW file; the C4 gate
  reverts only production hunks and keeps `template/tests/*.py`, so a new file earns its red —
  confirmed on iteration-v3's C4 log). Import modules only, never a symbol the fix adds, so
  the red leg fails rather than erroring at import. Reuse the `StackFoldGit` fixture shape
  from `template/tests/test_integrate_stack_bases.py` (copy or subclass). One test per
  criterion item (1)-(8); 4a, 4c, 4d may be separate tests.
- **Citations expected:** Do must cite path:line on the target branch for every change. Peer
  callsites to mirror: the in-run fold and its hold in `_drive_and_act` (`flow.py:2052-2081`:
  `integrate.unpublished(…, pushed=…)` hold and its stderr line, the `integrate.fold(…,
  folded_this_run=…, batch=run_batch)` call, `folded_tips` / `integ` bookkeeping, the
  `IntegrationError` stop). The fold's start modes: `integrate.fold` docstring
  `integrate.py:265-272` and `:344-345` — `folded_this_run=None` is "continue if origin has
  it, else fresh", pushed without force when continuing (`:401`). The missing-`gh` guard to
  copy: `merged.merged_head` (`merged.py:75-79`). No record-age (mtime) check — dropped at
  plan review as fragile under copy/checkout/archive moves. Carried ids must not be reported by
  `integrate.unpublished(accepted, pushed=pushed)` as unpushed in later waves — either keep
  them out of `accepted` (they are already on the line, `_merge_published` skips them,
  `integrate.py:426-427`) or count them as pushed.
- **Prior-art check (triage cycles):** merged history by path —
  `git -C ../pdca-harness log --oneline origin/main -- template/src/pdca_harness/flow.py
  template/src/pdca_harness/integrate.py template/src/pdca_harness/merged.py`: `69abaa1`
  (#597), `b21f248` (#593: append-only fold, `held_unpushed`, `stack-base-tip`), `96c9704` /
  `389bf1a` (#469/#473 split adoption). None carries finished named ids or continues an
  earlier run's line. Open PRs on these paths: #639 (#591, the batch-scoped line this child
  needs), #638 (#590) — both in this run's wave 0. Closed-unmerged PRs touching them: #598,
  #599, #600 (auto-iterate / gate re-run / size signal — unrelated). Earlier attempts at this
  issue: `results/issue_616/iteration-v1..v3` (rejected approach: fresh line + carry of any
  out-of-batch prerequisite).
- **Disposition hint:** likely-fix
- **Plan-review response:** (1) target mismatch — fixed: declared `Depends on (merged): 591`
  and told Do to re-resolve lines on `main`. (2) wording tests + `drift.py` — added to Scope.
  (3) tracker framing — checked: `results/issue_616/notes.json` (#616 body: "When a run stops
  part-way … the recovery is to re-issue the same command. Today that resumed run builds
  dependents on a base that lacks their prerequisites"); v1-v3 rejections are in
  `results/issue_616/iteration-v*/SUMMARY.md`. Brief stands. (4) `U` re-pointing — kept (the
  line is the batch's; a later-wave `U` already gets it) and made criterion (8). (5) PR-state
  holds — dropped (4b, the mtime rule); kept (4c)/(4d): carrying a CLOSED PR's branch would
  put a rejected change on the shared line, and (4d) is the fail-closed half of the same
  read, mirroring `merged_head`'s guard.

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: Rejected at sign-off: the approach is right, but the review found real gaps in `_carry_finished`. Fix these in the rebuild: 1. Lock: hold the integration lock through the carry fold AND the `integrate.pushed_tip` read. Pass `locks=` (an ExitStack) to `integrate.fold`, the same way the in-run fold does (flow.py ~2189-2199). Today the lock is released before the tip is read, so a concurrent run on the same base can make us record its commit. 2. Re-gate: when `[driver].regate_between_waves` is on, re-gate the carried line (`gates.run_integration`, under the lock) before wave 0, and stop the run before any wave if it is red, the same way the in-run fold does (flow.py ~2213-2221). Add a test for it. 3. Closed PR already on the line: if origin's line already holds a finished id whose PR is CLOSED, do not continue that line silently and build on it. Fail closed: do not build that target's wave-0 bundles on it, and name it on stderr. Also fix the stderr text, which wrongly says the id "is not carried" when the line already has it. Add a test that starts with the line already on origin and already holding the closed P. 4. Overstated wording: `publish.py:345` (dry-run plan) and `drift.py:60-61` promise unconditionally that a re-issued run keeps the line. Qualify both the way `publish.py:728-731` and `docs/07-crosscutting.md:686` do ("a run that carried nothing" still starts fresh). Criterion (7) stays: the no-carry case is a documented limit, not something to fix here.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  Rejected at sign-off: the approach is right, but the review found real gaps in `_carry_finished`. Fix these in the rebuild:
  1. Lock: hold the integration lock through the carry fold AND the `integrate.pushed_tip` read. Pass `locks=` (an ExitStack) to `integrate.fold`, the same way the in-run fold does (flow.py ~2189-2199). Today the lock is released before the tip is read, so a concurrent run on the same base can make us record its commit.
  2. Re-gate: when `[driver].regate_between_waves` is on, re-gate the carried line (`gates.run_integration`, under the lock) before wave 0, and stop the run before any wave if it is red, the same way the in-run fold does (flow.py ~2213-2221). Add a test for it.
  3. Closed PR already on the line: if origin's line already holds a finished id whose PR is CLOSED, do not continue that line silently and build on it. Fail closed: do not build that target's wave-0 bundles on it, and name it on stderr. Also fix the stderr text, which wrongly says the id "is not carried" when the line already has it. Add a test that starts with the line already on origin and already holding the closed P.
  4. Overstated wording: `publish.py:345` (dry-run plan) and `drift.py:60-61` promise unconditionally that a re-issued run keeps the line. Qualify both the way `publish.py:728-731` and `docs/07-crosscutting.md:686` do ("a run that carried nothing" still starts fresh). Criterion (7) stays: the no-carry case is a documented limit, not something to fix here.
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).

## Iteration 2 — carry-forward (from the previous attempt)
- Sign-off rationale: Rejected at sign-off (attempt 2): the approach is still right, and last round's four fixes (lock, re-gate, closed PR already on the line, wording) are in. The remaining gaps share one cause: the continued line is trusted too much. Fix these in the rebuild, each with a regression test: 1. Unresolvable head = unknown, not absent. When a finished id's host-reported head cannot be resolved locally (e.g. a fixup was pushed, then the PR was closed and the branch deleted before we fetched), `integrate._holds` / the check at `integrate.py:~560` must not answer "not on the line". Treat it as unknown: block that target's wave-0 bundles and name it on stderr (do not print "is not carried"). Test: the reviewer's deleted-branch-after-fixup case (review C3 FAIL). 2. Check every requested id against the line, not only finished ones. Before continuing origin's line, check every requested id that has a publish record, including drive-set bundles the earlier run folded and that were since rejected/iterated (PR CLOSED, no longer COMPLETE). Their old commits must not ride into the rebuilt PR. Also catch an old commit of a finished id whose branch was force-pushed with a rebuild since the earlier fold (looking only at the current head misses it). If such commits are on the line, fail closed for that target, the same way as the closed-PR case. 3. Empty `pr_url` must not be a dead end. If the earlier run's `gh pr create` failed (`publish.json` has `pr_url: ""`) and the line holds that id, do not block the whole target with advice that doesn't work. Either look the PR up by its head branch when `pr_url` is empty, or make `pdca publish <id>` able to recover it, and print advice that actually gets the user unstuck. Optional cleanup from the code review: share one helper for the fold + lock + tip read + re-gate block between the carry and the in-run fold, so they cannot drift apart again.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  Rejected at sign-off (attempt 2): the approach is still right, and last round's four fixes (lock, re-gate, closed PR already on the line, wording) are in. The remaining gaps share one cause: the continued line is trusted too much. Fix these in the rebuild, each with a regression test:
  1. Unresolvable head = unknown, not absent. When a finished id's host-reported head cannot be resolved locally (e.g. a fixup was pushed, then the PR was closed and the branch deleted before we fetched), `integrate._holds` / the check at `integrate.py:~560` must not answer "not on the line". Treat it as unknown: block that target's wave-0 bundles and name it on stderr (do not print "is not carried"). Test: the reviewer's deleted-branch-after-fixup case (review C3 FAIL).
  2. Check every requested id against the line, not only finished ones. Before continuing origin's line, check every requested id that has a publish record, including drive-set bundles the earlier run folded and that were since rejected/iterated (PR CLOSED, no longer COMPLETE). Their old commits must not ride into the rebuilt PR. Also catch an old commit of a finished id whose branch was force-pushed with a rebuild since the earlier fold (looking only at the current head misses it). If such commits are on the line, fail closed for that target, the same way as the closed-PR case.
  3. Empty `pr_url` must not be a dead end. If the earlier run's `gh pr create` failed (`publish.json` has `pr_url: ""`) and the line holds that id, do not block the whole target with advice that doesn't work. Either look the PR up by its head branch when `pr_url` is empty, or make `pdca publish <id>` able to recover it, and print advice that actually gets the user unstuck.
  Optional cleanup from the code review: share one helper for the fold + lock + tip read + re-gate block between the carry and the in-run fold, so they cannot drift apart again.
- Full previous attempt preserved in `iteration-v2/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).

## Iteration 3 — carry-forward (from the previous attempt)
- Sign-off rationale: Rejected at sign-off (attempt 3): the approach is still right, and the round-1 and round-2 fixes are all in. Round 3 found three more gaps in the cross-run recovery logic. Fix each one and add a regression test for each: 1. Recovered PR identity is lost before the deleted-branch decision (review C3 FAIL, `reviewer-probe.py`). When `pr_url` is empty, `merged.pr_state` finds the MERGED PR by branch, but `integrate._gone_branch` -> `merged.merged_head` reads only the recorded URL and returns None, so the run stops before wave 0. Pass the recovered URL/state into the deleted-branch decision, or have that decision use the same branch lookup. Test the combination: empty pr_url + merged + branch deleted. 2. Squash- or rebase-merged prerequisite with its branch deleted (adversary, `scratch/attack_squash.py`). The fold raises at `integrate.py:~548` and the whole run stops, including unrelated bundles. Before the patch this case built fine. The re-issued command stops again every time, and the advice ("get that work into origin/main") is already true. A re-issue must not stop forever with advice that doesn't work. Criteria (5)/(6) asked for "otherwise raise", but no recovery policy was chosen at sign-off: pick one, state it in build-notes, and test it. 3. A closed PR that a newer open PR replaced (adversary, `scratch/attack_superseded.py`). `merged.pr_state` asks only about the recorded `pr_url`. When that PR is CLOSED, also run the same `gh pr list --head` branch lookup used for an empty `pr_url`, and use an OPEN/MERGED PR if one exists. Today the advice "re-open the PR" doesn't work, because GitHub won't reopen a PR while another open one uses the same head branch. Optional (adversary/code-review): fix the two doc wording slips at `docs/07-crosscutting.md:670-674` (only same-target wave-0 bundles are pointed at the line; only plain `Depends on` dependents are held), and build `merged_head` on the new `_gh`/`_json`/`_head` helpers.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  Rejected at sign-off (attempt 3): the approach is still right, and the round-1 and round-2 fixes are all in. Round 3 found three more gaps in the cross-run recovery logic. Fix each one and add a regression test for each:
  1. Recovered PR identity is lost before the deleted-branch decision (review C3 FAIL, `reviewer-probe.py`). When `pr_url` is empty, `merged.pr_state` finds the MERGED PR by branch, but `integrate._gone_branch` -> `merged.merged_head` reads only the recorded URL and returns None, so the run stops before wave 0. Pass the recovered URL/state into the deleted-branch decision, or have that decision use the same branch lookup. Test the combination: empty pr_url + merged + branch deleted.
  2. Squash- or rebase-merged prerequisite with its branch deleted (adversary, `scratch/attack_squash.py`). The fold raises at `integrate.py:~548` and the whole run stops, including unrelated bundles. Before the patch this case built fine. The re-issued command stops again every time, and the advice ("get that work into origin/main") is already true. A re-issue must not stop forever with advice that doesn't work. Criteria (5)/(6) asked for "otherwise raise", but no recovery policy was chosen at sign-off: pick one, state it in build-notes, and test it.
  3. A closed PR that a newer open PR replaced (adversary, `scratch/attack_superseded.py`). `merged.pr_state` asks only about the recorded `pr_url`. When that PR is CLOSED, also run the same `gh pr list --head` branch lookup used for an empty `pr_url`, and use an OPEN/MERGED PR if one exists. Today the advice "re-open the PR" doesn't work, because GitHub won't reopen a PR while another open one uses the same head branch.
  Optional (adversary/code-review): fix the two doc wording slips at `docs/07-crosscutting.md:670-674` (only same-target wave-0 bundles are pointed at the line; only plain `Depends on` dependents are held), and build `merged_head` on the new `_gh`/`_json`/`_head` helpers.
- Full previous attempt preserved in `iteration-v3/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).

## Iteration 4 — carry-forward (from the previous attempt)
- Sign-off rationale: Rejected at sign-off (attempt 4): four rounds have each added special cases for another combination of PR state (open/closed/merged/replaced/no pr_url) x branch state (deleted/force-pushed/squash-merged) x what the earlier run's line holds (rejected commits, conflicting finished ids). The adversary finds the next combination every round; patch is 149 KB, over the size backstop. Root cause: the brief never fixed a policy for the non-clean case, so Do invents one per scenario. Re-plan #646 around ONE rule written into the brief: - Carry a finished prerequisite only in the clean case: PR OPEN (or MERGED and already reachable), branch head resolvable, and it merges cleanly onto the line. - Anything else, for any reason, holds only that prerequisite's plain-`Depends on` dependents, names the id + reason on stderr, and the rest of the run goes on. Never stop the whole run because of an earlier run's leftovers. - The carry triggers only on a finished id that is itself carryable (patched + targeted), not merely COMPLETE (adversary finding 1). - Two finished ids that do not merge together: the one that fails is held with its dependents, not a run-wide stop (adversary finding 2). Optionally split the per-case recovery advice (how to get unstuck for each hold reason) into its own child. Keep the criteria to the rule, not an enumeration of host scenarios. Note: #639 (#591) is still OPEN, not merged to main.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  Rejected at sign-off (attempt 4): four rounds have each added special cases for another combination of PR state (open/closed/merged/replaced/no pr_url) x branch state (deleted/force-pushed/squash-merged) x what the earlier run's line holds (rejected commits, conflicting finished ids). The adversary finds the next combination every round; patch is 149 KB, over the size backstop. Root cause: the brief never fixed a policy for the non-clean case, so Do invents one per scenario.
  Re-plan #646 around ONE rule written into the brief:
  - Carry a finished prerequisite only in the clean case: PR OPEN (or MERGED and already reachable), branch head resolvable, and it merges cleanly onto the line.
  - Anything else, for any reason, holds only that prerequisite's plain-`Depends on` dependents, names the id + reason on stderr, and the rest of the run goes on. Never stop the whole run because of an earlier run's leftovers.
  - The carry triggers only on a finished id that is itself carryable (patched + targeted), not merely COMPLETE (adversary finding 1).
  - Two finished ids that do not merge together: the one that fails is held with its dependents, not a run-wide stop (adversary finding 2).
  Optionally split the per-case recovery advice (how to get unstuck for each hold reason) into its own child. Keep the criteria to the rule, not an enumeration of host scenarios. Note: #639 (#591) is still OPEN, not merged to main.
- Full previous attempt preserved in `iteration-v4/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
