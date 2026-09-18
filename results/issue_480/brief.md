# Brief — issue 480 / plan-advisory-reviews-what-the-session-wrote

- **Slug:** plan-advisory-reviews-what-the-session-wrote
- **Defect:** after a **single-bundle** Plan session, the #301 plan-advisory pass reviews the
  bundle `do_plan` was handed, not the briefs the session wrote. `do_plan`
  (`template/src/pdca_harness/leaves.py:904-927`) ends with `run_plan_advisory(d, cfg)`
  (`:927`), which is `run_plan_advisory_batch(cfg, [d])` (`:3404-3406`). A split accepted
  inside that session (`pdca split <id> --accept`) creates child bundles the pass never
  sees. Two shapes:
  1. **Parent keeps its brief** (split after a rejected attempt: `split.accept` archives with
     `include_brief=False`, `split.py:837-838`). The pass reviews the superseded parent brief
     on a bundle already marked terminal (`close-disposition` = `split`, `split.py:862`;
     `state.CLOSE_MARKER`, `state.py:44`). If it finds anything, the revision session edits a
     brief nobody will build. It writes a `plan-advisory-*.md` and a benefit record, so it
     *looks* like coverage.
  2. **Parent has no brief** (split after `iterate-plan` cleared it). The filter at
     `leaves.py:3364-3365` drops it and the pass silently does nothing.
  The children get no second chance: `--accept` materialises them `PLANNED`, so
  `flow._plan_if_unplanned` returns early (`flow.py:367-368`) and never reaches the pass.
  `do_plan_batch` already selects by what the session produced (content-hash snapshot
  `leaves.py:1073-1075`, `fresh` at `:1129-1133`), so only the single-bundle path loses the
  children. But the batch path has the terminal-parent problem too: a parent briefed and then
  split in the same batch session is "fresh" and gets reviewed.
  Hit twice on getwyrd/wyrd (#711 → #721/#722, then #721 → #776/#777). Reviewing by hand
  afterwards found material errors in the children each time (a false race-injection recipe,
  a wrong size constant that would have re-created the defect the lineage exists to remove).
- **Success criterion:** offline, with a stub plan-advisory leaf configured:
  (a) a single-bundle `leaves.do_plan(parent, cfg)` whose session writes child bundles with
      authored briefs and marks the parent split produces a plan-advisory artifact and a
      `plan-advisory-benefit.json` on **every child**, and **none** on the parent. This holds
      for both shapes: parent brief kept (shape 1) and parent with no brief (shape 2);
  (b) a bundle carrying `close-disposition` is never reviewed on **either** Plan path
      (`do_plan` or `do_plan_batch`), and so can never trigger the revision session;
  (c) the single-bundle path selects the same way the batch path does. A bundle whose brief
      existed before the session and is byte-identical after it is **not** reviewed; one the
      session rewrote **is**. A placeholder brief is still never reviewed (`leaves.py:3364-3365`);
  (d) the existing plan-advisory suite (`template/tests/test_plan_advisory.py`) passes
      unchanged, and with no `[[leaves.plan_advisory]]` configured the Plan beat stays a no-op
      (`test_default_off_leaves_the_plan_beat_untouched`, `:58-63`).
- **Falsifiability:** RED on the offline driver suite with stub leaves. Pre-fix, in shape 1 the
  parent gets the artifact and the children get none; in shape 2 nothing is reviewed. Both
  fail (a) with a real assertion failure. The test calls only pre-existing API
  (`leaves.do_plan`, `leaves.plan_advisory_artifact` at `:3049`, `state.CLOSE_MARKER`) and
  simulates the session by patching `leaves._stub_plan` (`:1039`). The stub planner path
  reaches the advisory pass the same way the command path does (`do_plan` calls it after the
  `if/else`, `:927`), so no model or TTY is needed.
- **Invariant to restore:** the Plan-beat advisory review covers exactly the briefs a Plan
  session authored or changed, wherever they were written, and never a bundle already closed
  (terminal). Which bundle the driver *handed* the session must not decide what gets
  reviewed. Source: #301's contract for the pass (review "the freshly briefed OR rewritten
  bundles", `leaves.py:1126-1128`) and the close-marker semantics (`state.py:44`; a split
  parent "was decomposed rather than built", `split.py:856`).
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Conflicts with:** none
- **Ordering note:** run 3 of plan-0.60-bug-order.md, one wave with 534, 467, 527 and 529. 534
  also edits `leaves.py` but was scoped to stay out of `do_plan`, `do_plan_batch` and
  `run_plan_advisory_batch` (only prompt strings and comments elsewhere). **This bundle must
  likewise stay inside those three functions (plus any new helper it adds next to them)** and
  leave every prompt string and the `handoff.session(...)` blocks and their comments
  (`:916-925`, `:1104-1117`) untouched, so the two diffs don't overlap. 526 (`leaves.py`
  plan sandbox, run 4) and 481 (run 4, needs 480) come after.
- **Surfaces:** data
- **Difficulty:** medium
- **Scope:** make the plan-advisory selection after a Plan session cover what the session
  produced and skip terminal bundles, on both Plan paths, with one selection rule shared by
  `do_plan` and `do_plan_batch`. Confined to `template/src/pdca_harness/leaves.py`.
  / out of scope: children of a split accepted **outside** any Plan session (e.g. from a
  sign-off session or a shell), which never enter Plan at all. That is a separate gap; note
  it in build-notes if seen, don't fix it here. Also out: the revision prompt wording
  (`_plan_revision_prompt`, `:3337-3351`); following `split-lineage.json` to find children
  (the content-hash selection makes it unnecessary); `split.py`, `flow.py`; any prompt string.
- **Repro instruction:** on `main`, in `template/`: build a `Config` as
  `test_plan_advisory.py:29-37` does with `plan_advisory=[_REVIEWER]` (stub leaf). Create a
  parent bundle `issue_P` with an authored brief. Patch `leaves._stub_plan` with a side effect
  that writes authored briefs into `issue_C1` and `issue_C2` and writes `close-disposition`
  = `split` into the parent. Call `leaves.do_plan(parent, cfg)`: `issue_P` gets
  `plan-advisory-plan-reviewer.md`, and `issue_C1` / `issue_C2` get nothing. Repeat with the
  parent's brief deleted first (shape 2): nobody gets anything.
- **External dependencies:** none — offline stub leaves; base toolchain only (python3 ≥ 3.11)
- **Test file:** template/tests/test_plan_advisory_split_children.py (new)
- **Citations expected:** Do cites path:line on `main` for every change. Peer callsites: the
  selection rule to share is `do_plan_batch`'s content-hash snapshot and `fresh` filter
  (`leaves.py:1073-1075` and `:1129-1133`, using `_brief_sha` at `:3118-3121`). The test should
  mirror `test_rewritten_brief_gets_a_fresh_plan_review` (`test_plan_advisory.py:357-376`),
  which patches the stub planner with a side effect that writes extra briefs mid-session.
- **Prior-art check (triage cycles):** by path on origin/main (fetched 2026-09-15): `git log
  -S` on the selection lines (`run_plan_advisory(d, cfg)`, `reviewed = [d for d in bundles`,
  `briefed_before`) finds only the #301 commits `ed0e585` and `b5c4d34`. The last five
  `leaves.py` commits (`304ff71` #494, `9a19cb5` #466, `0881af9`, `9bc0c94`) don't touch it. No open PR edits these functions (open: #542, #543, error-log handling). No closed or
  merged PR references #480 (the #394 search hit was a line number). The issue's comment
  (2026-08-19) adds the second occurrence and the terminal-parent guard, both folded in here.
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.
