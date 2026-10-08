<!-- pdca:split-proposal v1 -->
# Split proposal — issue 616

## Why this slice is oversized

Three Do attempts (iteration-v1..v3) each closed the previous sign-off list and surfaced
3-5 new edge cases in the same carry/hold logic; the v3 patch was ~1400 lines. The cause
was the design the brief prescribed, not the builder: every run started a **fresh** line and
tried to carry **any** out-of-batch prerequisite onto it, so it had to decide, per
prerequisite, whether a line should exist at all, where a merged PR merged, and what to do
about the earlier run's line it force-replaced (which broke a held bundle's recorded tip).

Since then #591 (on this run's integration line, PR #639) made the line batch-scoped:
`flow_ids` passes the ids as asked for, skipped finished ones included
(`template/src/pdca_harness/flow.py:2357-2363`), so re-issuing the same `pdca flow <ids>`
already lands on the SAME line name as the earlier run. That splits the issue along a clean
seam, agreed with the human at Plan (2026-10-05):

- **child-1** — the issue's own "Expected": a re-issued `pdca flow <ids>` CONTINUES its
  batch's line (append-only, never force-replaced) and carries the named-but-already-finished
  ids onto it before wave 0. The prerequisite is in the requested batch, so the line is the
  batch's own and needs no per-dependent "should a line exist" analysis; the fold already
  judges merged / deleted branches (`integrate._gone_branch`).
- **child-2** — the general case child-1 cannot reach: a `Depends on` prerequisite outside
  the run's requested ids (the `flow_batch` sweep, which gets a new line every run by design,
  `flow.py:2166-2170`; or a dependent driven in a different command). That one is held, not
  carried, until its PR has merged into the target base — and `merged.is_merged` learns to
  count MERGED only for a PR that merged into the target base.

## Wave sketch

child-1 first, child-2 after it (`Depends on: child-1`). Both edit `_runnable` and the
pre-wave part of `_drive_and_act` in `flow.py`; child-2 also needs child-1's notion of
"the run's requested batch" to tell an in-batch prerequisite (carried) from an out-of-batch
one (held). So they stack, never share a base.

Both need #591's batch-scoped line (`integrate.integration_branch(cfg, base, batch)`), which
is not on `origin/main` yet (PR #639, open). The live run (`pdca flow 591 590 531 616`)
adopts these children after #616's wave and points them at its integration line, which
carries #591 — so no edge to 591 is declared (a split child's ordering fields may name only
siblings). If the children are ever driven by a later standalone run instead, merge
#637/#638/#639 first.

<!-- pdca:child child-1 -->
# Brief — re-issued stack-mode flow continues its batch's integration line

> The Plan artifact (docs 02 §PLAN). Do reads ONLY this file.
> Child 1 of the split of #616. Verified against `eduralph/pdca-harness`
> `origin/pdca-integration/main` @ `f594d8e` (`origin/main` @ `c67a14d` plus #531, #590,
> #591 folded). All `path:line` below are on that line. #591's batch-scoped line name is
> REQUIRED by this fix and exists only there until PR #639 merges.

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
  (a) `P` has no branch on record; (b) `P`'s `publish.json` is older than its latest
  sign-off (`SUMMARY.md`) — a record left by a rejected attempt; (c) `P`'s PR state is
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
- **Ordering note:** First child. No declared edge: #591 (needed for the batch-scoped line
  name) reaches this child through the live run's integration line, which the run points it
  at; a split child may only name siblings. child-2 stacks on this one.
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
  (criterion 4a-d) holds only its own dependents — the same `held_unpushed` path the in-run
  fold uses (`flow.py:2052-2058`, `:712-713`) — and the hold message's advice must be one that
  works now the line is kept (e.g. "publish it with `pdca publish <id>`, then re-issue the
  same command"; for a closed PR, "re-open it or re-drive <id>"; for an unreadable state,
  say what could not be read). A failing pre-wave fold stops the run before wave 0. Update
  the stack-mode paragraph in `docs/07-crosscutting.md:658-677` and the "resuming across runs
  is #616" wording in `publish.py:345`, `:696`, `:726` so they describe the kept line.
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
  criterion item (1)-(7); 4a-4d may be separate tests.
- **Citations expected:** Do must cite path:line on the target branch for every change. Peer
  callsites to mirror: the in-run fold and its hold in `_drive_and_act` (`flow.py:2052-2081`:
  `integrate.unpublished(…, pushed=…)` hold and its stderr line, the `integrate.fold(…,
  folded_this_run=…, batch=run_batch)` call, `folded_tips` / `integ` bookkeeping, the
  `IntegrationError` stop). The fold's start modes: `integrate.fold` docstring
  `integrate.py:265-272` and `:344-345` — `folded_this_run=None` is "continue if origin has
  it, else fresh", pushed without force when continuing (`:401`). The missing-`gh` guard to
  copy: `merged.merged_head` (`merged.py:75-79`). The record-age comparison: `_record_mtime`
  (`flow.py:668-674`) against `SUMMARY.md`'s mtime. Carried ids must not be reported by
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

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.
<!-- pdca:end child-1 -->

<!-- pdca:child child-2 -->
# Brief — stack mode holds a dependent of an unmerged prerequisite outside the run's batch

> The Plan artifact (docs 02 §PLAN). Do reads ONLY this file.
> Child 2 of the split of #616. Verified against `eduralph/pdca-harness`
> `origin/pdca-integration/main` @ `f594d8e`; builds on child-1 (folded into this child's
> base by the run). Line numbers below are from `f594d8e` and may have moved on that folded
> base — re-resolve each one there before citing it.

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
  NOT build `D`: `D` stays PLANNED, one stderr line names `D`, `P` and the reason, with advice
  (name `P` in the same `pdca flow <ids>` command so its line carries it, or wait until its PR
  merges into the base), and an unrelated bundle `U` in the same run builds as today.
  Pre-fix `D` is built — RED. Shown for both entry points: `flow_ids` (named ids not
  including `P`) and `flow_batch` (sweep, `P` already COMPLETE). (2) `P`'s PR MERGED with its
  record's `base` equal to the target base and mode not `"stacked"` ⇒ `D` builds on the base
  as today. (3) `P`'s PR MERGED but its record's `base` is another branch (a `"stacked-pr"`
  record against an integration branch) or mode `"stacked"` ⇒ `D` is held, as in (1); the
  same rule now also governs `Depends on (merged)` — a `Depends on (merged): P` dependent
  waits in this case too, and still builds once `P` merged into the base. (4) `P` COMPLETE
  with an empty or missing `patch.diff` ⇒ `D` builds (nothing to wait for). (5) `gh` missing
  (`OSError`) or failing while reading `P`'s PR ⇒ `D` held, named, no traceback; the run goes
  on. (6) Unchanged: a prerequisite in the run's requested batch (child-1's carry), `Stacks
  on` edges, `--no-publish` runs, merge mode, and a dry-run (stub publisher; asks no host,
  holds nothing).
- **Falsifiability:** RED is reachable offline: no real git needed for (1)-(5), only a
  `gh` stub (`subprocess.run` patched for `gh pr view`) and bundles on disk with
  `publish.json` records. Pre-fix, (1) builds `D` (a stubbed build leaf records it ran) and
  (3) passes `merged.is_merged` — both assertions fail. Runs under the C4 gate as `cd
  template && PYTHONPATH=src python3 -m unittest tests.test_flow_out_of_batch_prereq_hold`.
  No network.
- **Invariant to restore:** Every bundle a stack-mode run builds is built on a base that
  carries all of its declared prerequisites; "merged" means merged into the dependent's
  target base, not into some branch. A prerequisite the run's line does not carry is in the
  base only once its PR merged there; until then the dependent waits, loudly. Sources:
  `_runnable`'s docstring (`flow.py:692-698`: "a dependent built on a COMPLETE-but-unmerged
  base would miss the prerequisite"); `merged.py:1-14` ("is a prerequisite's contribution
  merged into its base?"); the fold's own refusal to trust a merge whose record base is not
  the target base (`integrate._gone_branch`, `integrate.py:474-482`). Not a single-module
  guard: the readiness check and the merged-ness answer must agree for both `Depends on` and
  `Depends on (merged)`.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Depends on:** child-1
- **Ordering note:** Stacks on child-1: both edit `_runnable` and the start of
  `_drive_and_act` in `flow.py`, and this child needs child-1's "requested batch" notion to
  tell a carried in-batch prerequisite from a held out-of-batch one.
- **Surfaces:** data
- **Difficulty:** medium — `_runnable` (one new hold for plain out-of-batch `Depends on` in
  stack mode with publishing), `merged.is_merged` (target-base rule, `OSError` guard), the
  hold message, docs. The reviewer must keep #186's `Depends on (merged)` behaviour in view.
- **Scope:** In stack mode with publishing, hold a dependent whose plain `Depends on`
  prerequisite is outside the run's requested batch and not merged into the target base,
  instead of building it; make `merged.is_merged` count MERGED only for a PR merged into the
  target base (record `base` equals the target base resolved for the bundle, mode not
  `"stacked"`), and read `gh` failures — including a missing `gh` — as "not merged" with a
  message, never a traceback. Update `_runnable`'s docstring and the stack-mode paragraph in
  `docs/07-crosscutting.md` (near `:658-677`) to say a `Depends on` prerequisite outside the
  run's ids now waits for its merge.
  / out of scope: carrying out-of-batch prerequisites onto the line (rejected in
  iteration-v1..v3 — do not reintroduce); in-batch / re-issued prerequisites (child-1);
  `Stacks on` (#123, unchanged); merge mode (#531) and `--no-publish`; changing which ids the
  sweep path includes.
- **Repro instruction:** On the folded base, in `template/` with `PYTHONPATH=src`: create
  bundle `P` COMPLETE with a non-empty `patch.diff`, a brief targeting `org/repo @ main`, and
  a `publish.json` with `pr_url` set; stub `gh pr view` to return `{"state": "OPEN"}`. Create
  `D` with `- **Depends on:** P` and `U` with no dependencies. Call `flow.flow_ids(cfg, ["D",
  "U"], …)` with the build/sign-off leaves stubbed (and publishing patched). Observed: `D` is
  built. Then set the stub to `{"state": "MERGED"}` with the record's `base` set to
  `pdca-integration/main-r<key>`: `merged.is_merged(cfg, "P")` returns True.
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

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.
<!-- pdca:end child-2 -->
