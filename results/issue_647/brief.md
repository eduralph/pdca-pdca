# Brief — stack mode holds a dependent of an unmerged prerequisite outside the run's batch

> The Plan artifact (docs 02 §PLAN). Do reads ONLY this file.
> Child 2 of the split of #616. Verified against `eduralph/pdca-harness`
> `origin/pdca-integration/main` @ `f594d8e`; builds on child-1 (folded into this child's
> base by the run). Line numbers below are from `f594d8e` and may have moved on that folded
> base — re-resolve each one there before citing it. The target is `main`; #646 itself waits
> for #591 (PR #639) to merge into `main`, so by the time this child builds, `main` carries
> #591 and the folded base carries #646.

- **Slug:** stack-holds-dependent-of-out-of-batch-unmerged-prereq
- **Defect:** In stack mode a dependent whose plain `Depends on` prerequisite is NOT one of
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
- **Success criterion:** With the patch, in stack mode with publishing on: (1) a run that
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
- **Falsifiability:** RED is reachable offline: no real git needed for (1)-(5), only a
  `gh` stub (`subprocess.run` patched for `gh pr view`) and bundles on disk with
  `publish.json` records. Pre-fix, (1) builds `D` (a stubbed build leaf records it ran) and
  (3) passes `merged.is_merged` — both assertions fail. Runs under the C4 gate as `cd
  template && PYTHONPATH=src python3 -m unittest tests.test_flow_out_of_batch_prereq_hold`.
  No network.
- **Invariant to restore:** Every bundle a stack-mode run builds is built on a base that
  carries all of its declared prerequisites; for readiness, "merged" means merged into the
  DEPENDENT's target base (repo and branch, as `publish._resolve_target(D)` resolves them),
  not into some branch. A prerequisite the run's line does not carry is in the
  base only once its PR merged there; until then the dependent waits, loudly. Sources:
  `_runnable`'s docstring (`flow.py:692-698`: "a dependent built on a COMPLETE-but-unmerged
  base would miss the prerequisite"); `merged.py:1-14` ("is a prerequisite's contribution
  merged into its base?"); the fold's own refusal to trust a merge whose record base is not
  the target base (`integrate._gone_branch`, `integrate.py:474-482`). Not a single-module
  guard: the readiness check and the merged-ness answer must agree for both `Depends on` and
  `Depends on (merged)`.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Depends on:** 646
- **Ordering note:** Stacks on child-1: both edit `_runnable` and the start of
  `_drive_and_act` in `flow.py`, and this child needs child-1's "requested batch" notion to
  tell a carried in-batch prerequisite from a held out-of-batch one.
- **Surfaces:** data
- **Difficulty:** medium — `_runnable` (one new hold for plain out-of-batch `Depends on` in
  stack mode with publishing), one new base-aware merged check in `merged.py` used only by
  `_runnable` (target-base rule, `OSError` guard), the hold message, docs. The reviewer must keep #186's `Depends on (merged)` behaviour in view.
- **Scope:** In stack mode with publishing, hold a dependent whose plain `Depends on`
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
- **Repro instruction:** On the folded base, in `template/` with `PYTHONPATH=src`: create
  bundle `P` COMPLETE with a non-empty `patch.diff`, a brief targeting `org/repo @ main`, and
  a `publish.json` with `pr_url` set; stub `gh pr view` to return `{"state": "OPEN"}`. Create
  `D` with `- **Depends on:** P` and `U` with no dependencies. Call `flow.flow_ids(cfg, ["D",
  "U"], …)` with the build/sign-off leaves stubbed (and publishing patched). Observed: `D` is
  built. Then set the stub to `{"state": "MERGED"}` with the record's `mode` `"stacked-pr"`
  and `base` `pdca-integration/main` (the shape of #591's real record): `D` is still built.
- **External dependencies:** none
- **Test file:** template/tests/test_flow_out_of_batch_prereq_hold.py (NEW file; the C4 gate
  reverts only production hunks and keeps `template/tests/*.py`, so a new file earns its
  red). Import modules only, never a symbol the fix adds.
- **Citations expected:** Do must cite path:line on the target branch for every change. Peer
  callsites: the existing out-of-batch `Depends on (merged)` gate in `_runnable`
  (`flow.py:707-709`) — the new hold is its sibling for plain `Depends on` in stack mode; the
  missing-`gh` guard in `merged.merged_head` (`merged.py:75-79`); the "merged elsewhere"
  rule in `integrate._gone_branch` (`integrate.py:474-482`: `onto or rec.get("base") != base`);
  the target resolution `publish._resolve_target(d)` as `_point_at_integration` uses it
  (`flow.py:737`).
- **Prior-art check (triage cycles):** merged history by path —
  `git -C ../pdca-harness log --oneline origin/main -- template/src/pdca_harness/flow.py
  template/src/pdca_harness/merged.py`: #186's merge gate and #107's `merged.py` are the
  only readiness rules for out-of-batch prerequisites; `b21f248` (#593) added
  `merged_head` with the `OSError` guard but left `is_merged` unguarded. Open PRs on these
  paths: #639, #638 (this run's wave 0, unrelated to readiness). Closed-unmerged: #598-#600
  (unrelated). iteration-v2/v3 sign-offs of #616 raised the "merged where" and missing-`gh`
  findings this child closes.
- **Disposition hint:** likely-fix
- **Plan-review response:** (1) other `is_merged` callers — fixed: the base rule moves to a new
  function only `_runnable` calls; `is_merged`, `merge.py:233`, `cli.py:1084` unchanged, with a
  test pinning merge mode's resume answer. (2) whose base — fixed: the dependent's resolved
  repo + base, passed explicitly. (3) "can't happen" — disagree: #591's real record on disk
  (`results/issue_591/publish.json`) is `"stacked-pr"` with `"base": "pdca-integration/main"`,
  and #591 is the out-of-batch prerequisite of #646 — so a MERGED-into-the-line PR counting as
  merged is a live case, now cited in (3) and the repro. (4) three fixes — kept together: the
  new hold (a) is only sound if its merged check (b) is, since (a) without (b) still builds on
  a base lacking a PR merged into an integration line; the `OSError` guard (c) lives in the
  new function and is reachable only through (a). Moving (b) out of `is_merged` removes the
  side effects that made it risky. (5) #646 PLANNED — by design: `Depends on: 646` makes the
  driver build this in a later wave on a base folding #646; added a header note on #591.
  (6) message — fixed: the test asserts the substring `not merged into main`.

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: Design is sound and in scope; two confirmed implementation bugs from the code review must be fixed, each with a test: 1. Empty-target regression: when the dependent's resolved target is ("", "") (no `Repo + branch target`, or no `@ branch`), skip the #647 hold and keep the old `merged.is_merged` answer for `Depends on (merged)` — today merged_into rejects every record (merged.py:98) so the dependent is held forever and the message reads "not merged into ()". 2. Wrong reason/advice: an out-of-batch `Depends on (merged)` prerequisite that is not COMPLETE (PLANNED/DISCONTINUED) must go to `unmet` ("prerequisite(s) not ready"), not `unmerged` ("wait until their PR merges") — check state != COMPLETE first (flow.py:725-733), as the plain-dependency branch already does. Also: C4 (worktree mismatch) never ran — lane was busy — so it must produce a real red→green result on the rebuild.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  Design is sound and in scope; two confirmed implementation bugs from the code review must be fixed, each with a test:
  1. Empty-target regression: when the dependent's resolved target is ("", "") (no `Repo + branch target`, or no `@ branch`), skip the #647 hold and keep the old `merged.is_merged` answer for `Depends on (merged)` — today merged_into rejects every record (merged.py:98) so the dependent is held forever and the message reads "not merged into  ()".
  2. Wrong reason/advice: an out-of-batch `Depends on (merged)` prerequisite that is not COMPLETE (PLANNED/DISCONTINUED) must go to `unmet` ("prerequisite(s) not ready"), not `unmerged` ("wait until their PR merges") — check state != COMPLETE first (flow.py:725-733), as the plain-dependency branch already does.
  Also: C4 (worktree mismatch) never ran — lane was busy — so it must produce a real red→green result on the rebuild.
- Failing gate: C4 Verification (worktree mismatch) — issue_647: lane pdca-harness.pdca-wt is busy (another Do or gate run holds it) — refusing to reconstruct under a live run; retry when it finishes.
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
