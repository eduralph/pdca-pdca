# Brief — issue 357 / state-machine-consolidation-superseded-by-migration-steps

> The Plan artifact. Plan concludes this issue is covered by two accepted migration
> steps of the target architecture, so it carries a `duplicate` hint: the driver skips
> the builder and reviewer and routes it straight to sign-off, where the human confirms
> the close or overrides it. Nothing is built.

- **Slug:** state-machine-consolidation-superseded-by-migration-steps
- **Defect:** #357 asks to make the bundle state machine explicit and single-sourced: (1) a written spec checked against the code, (2) name the HELD state, (3) one definition per question ("is this finished?", "did a cycle run?", "what does an iterate archive?", "does this take the close path?"), (4) one dispatch boundary as a tested invariant, (5) transition guards as data. It was filed before the 2026-10-15 approach review. That review's accepted proposal (`docs/design/proposals/accepted/0002-target-architecture.md`) and roadmap (`docs/design/architecture/09-build-order-and-roadmap.md:34-41`) now schedule this work as migration step 4 (#713, 0.70: "`state(records) -> State` and `next(state, records, config) -> Action`, no I/O … collapses `flow.flow` and `flow_ids` … the transition-table test is generated from the state diagram") and step 5 (#714, 0.67: Policy protocol — sizing, plan policy, dependency halt etc. behind "records in, Hold or Proceed out"; every phase returns `Ok / Held(reason) / FailedInfra`). The state diagram itself is already written (`docs/design/architecture/06-runtime-view.md:13-38`). Doing #357 separately in 0.60 would build a second consolidation of the same machine ahead of the planned one.
- **Success criterion:** (1) #357 is closed as a duplicate (GitHub "not planned") with a closing comment that maps each of its five goals to where it now lives: (1) spec → #713 (transition-table test generated from the diagram) + `06-runtime-view.md` §6.1; (2) HELD → #714 (`Held(reason)` outcome); (3) one definition per question → not named in either, carried to #713 (below); (4) one dispatch boundary → #713 (one loop, `flow.flow` deleted) — the "tested invariant across all four entry paths" half is not in #713's exit gate, so it is carried to #713 explicitly (below); (5) guards as data → #714 (Policy protocol). The closing comment also names the one piece of #357 evidence that is not a goal — "a state reached without its predecessor" (BUILT from `brief.md` + `patch.diff` with no gate record; the #321 gating) — as **not carried: a behaviour change, to be filed separately if still wanted**, as #357 itself says. (2) A comment on **#713** and a comment on **#714**, each linking #357 and asking that step to check #357 for any input it does not cover yet before its design starts — the text is in "Tracker comments" below. The #713 comment also lists goal (3)'s open examples, so they are not lost. The maintainer confirmed this close in the Plan session (2026-10-23); that confirmation is not in notes.json, so sign-off must re-record it in §9, including explicit acceptance that the work moves from #357's 0.60 to 0.67 (#714) / 0.70 (#713), against the thread's "schedule it now" argument.
- **Falsifiability:** The close is wrong if a goal of #357 has no home after it. Checkable by reading #713, #714 and the three comments: the forbidden state is a #357 goal that no open issue names. Goal (3) is the one at risk today, which is why the criterion requires the carry-over comment. No code gate applies (no patch); judged at sign-off.
- **Repo + branch target:** eduralph/pdca-harness @ main (no patch)
- **Depends on:** none
- **Conflicts with:** none
- **Ordering note:** No patch, so it conflicts with nothing in this batch.
- **Surfaces:** data
- **Difficulty:** low — no code change; three tracker comments and a close.
- **Scope:** Close #357 as superseded, with the goal-by-goal mapping; comment on #713 and #714 asking each to check #357 for missing input, carrying goal (3) onto #713. / out of scope: any code or doc change; changing the milestones of #713/#714; re-opening the design of steps 4–5.
- **Repro instruction:** Read `docs/design/proposals/accepted/0002-target-architecture.md:46` (Machine) and :56 (Outcomes), the roadmap table at `docs/design/architecture/09-build-order-and-roadmap.md:34-41`, and `gh issue view 713 714 -R eduralph/pdca-harness`; compare with #357's five goals. On main @ a6af7f3 the predicates #357 cites still exist: `driver.held` (template/src/pdca_harness/driver.py:207), `driver._close_class` (driver.py:222), `state.DOWNSTREAM_OF_BRIEF` / `DOWNSTREAM_GLOBS` / `CYCLE_EVIDENCE_ONLY` (template/src/pdca_harness/state.py:116, :155, :174), `cleanup._plan_bundle` (template/src/pdca_harness/cleanup.py:311).
- **External dependencies:** `gh` (authenticated, to comment on and close issues).
- **Test file:** none — close / no-fix disposition; no patch.
- **Citations expected:** The closing comment cites the paths above on main @ a6af7f3.
- **Prior-art check (triage cycles):** `gh search prs --repo eduralph/pdca-harness "state machine specification"`: none. `git -C ../pdca-harness log --oneline origin/main -n 4 -- template/src/pdca_harness/state.py template/src/pdca_harness/driver.py` → incremental fixes (#409 iterate budgets, split re-plan, leaf error logs), no consolidation. Closed-unmerged PRs touching state.py / driver.py: #598, #599, #600 — closed as carried byte-identical by #615; none consolidates the machine. The superseding work is open issues #713 / #714, not merged code.
- **Disposition hint:** duplicate

## Tracker comments (post at sign-off, after the close)

**On #713:**

> Input check for this step: #357 ("Systematize the bundle state machine") was closed as covered by this step and #714. Before the design starts, please check #357 for anything this step does not cover yet. One goal is named in neither step, so it lands here: **one definition per question** ("is this finished?", "did a cycle run?", "what does an iterate archive?", "does this take the close path?"), each with one implementation and named callers. Open examples on main @ a6af7f3:
> - "held?" is answered twice: `driver.held` (`template/src/pdca_harness/driver.py:207`) and a separate `state.state(d) not in state.HALTED` check at `flow.py:523`;
> - `driver._close_class` (driver.py:222) combines the brief's hint, the close marker and the `iteration-v*` archive in an order documented only in the function body (#323);
> - a third, same-named predicate: `drive_claim.held(cfg, d)` (`template/src/pdca_harness/drive_claim.py:254`) asks a different question — does another live run hold the drive claim (#566) — and must not be merged with `driver.held`; the HALTED check is also inline in `run_issue`'s loop (`driver.py:197`);
> - `state.DOWNSTREAM_OF_BRIEF` / `DOWNSTREAM_GLOBS` / `CYCLE_EVIDENCE_ONLY` (`state.py:116`, `:155`, `:174`) answer two nearly identical questions, and only a test pins the difference (#334).
> Already resolved: the `cleanup` vs `is_resolved` drift (#345). Both now use `state.has_cycle_evidence` (`cleanup.py:369`).
>
> #357 goal 4 also asks for **one dispatch boundary as a tested invariant**: a test that `flow.flow`, the zero-id sweep, `flow.flow_ids` and `pdca run` all go through the same dispatch, so the next guard is not added to one path only. This step's exit gate (`flow.flow` deleted, `_drive_and_act` < 120 lines) does not yet name that test; please add it.
>
> On goal 1: this step's "transition-table test generated from the state diagram" covers it, but the diagram (`docs/design/architecture/06-runtime-view.md` §6.1) has no HELD state and no guards today. The diagram needs HELD (from #714's `Held(reason)`) before the generated test can cover goals 2 and 5.

**On #714:**

> Input check for this step: #357 was closed as covered by #713 and this step. Before the design starts, please check #357 for anything this step does not cover yet. Its goals 2 (a real HELD state instead of a predicate each caller must remember, #333) and 5 (transition guards as data: `_close_class`'s precedence, the placeholder-brief rule #113, the RESOLVED evidence guard #334, the pre-dispatch policy #321/#333) map to `Held(reason)` and the Policy protocol here.

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.

Plan-review response: Revised. Checked #713's body: the "transition-table test is generated from the state diagram" wording is there, so goal 1 stands, with a note that the diagram needs HELD first. Goal 4's tested-invariant half, the `drive_claim.held` name clash (plus the inline check at `driver.py:197`), and goal 1's HELD gap now go in the #713 comment. The closing comment says the "state without predecessor" evidence is not carried. Sign-off must re-record the maintainer's confirmation and accept the 0.60 → 0.67/0.70 delay.
