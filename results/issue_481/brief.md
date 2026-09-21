# Brief — issue 481 / split-parent-keeps-a-plan-artifact

> The Plan artifact (docs 02 §PLAN). Human-authored. Do reads ONLY this file.

- **Slug:** split-parent-keeps-a-plan-artifact
- **Defect:** A split parent that was sent back by `iterate-plan` *before* it was split ends up
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
- **Success criterion:** With a parent bundle shaped like the realistic case (an authored brief
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
- **Falsifiability:** RED on the offline driver suite with no extra environment: on current
  `origin/main` the realistic-case parent derives `UNPLANNED` after `split.accept` and has no
  `brief.md`, so (a) and (b) fail. (e) is red on main too (`state.py:305-307` returns `UNPLANNED`
  for any briefless bundle without a `resolved` record). Both were reproduced during Plan on an
  export of `origin/main`: after `_archive_iteration(p, 1, include_brief=True)` and
  `split.accept(p, ["601","602"], cfg)`, `state.state(p)` = `UNPLANNED` and the parent holds only
  `build-notes.md`, `close-disposition`, `iteration-v1`, `split-lineage.json`, `split-proposal.md`.
  A bare bundle holding only `close-disposition` also derives `UNPLANNED`. The test drives only pre-existing API
  (`split.accept`, `state.state`, `handoff.check_planner`, and the driver's iterate-plan archive),
  so the C4 red leg (production hunks reverted, test kept) imports cleanly and fails on an assertion.
- **Invariant to restore:** Every bundle that carries a Do-era artifact (a `patch.diff`, or the
  close marker that stands in for one) has a Plan artifact, and the state derivation never places
  such a bundle before Plan. Source (internal, Tier C): the `CLOSE_MARKER` contract at
  `state.py:40-44` ("its close marker is the Do artifact — the symmetric stand-in for patch.diff —
  so the state machine reads it as 'past Do'"); the #334 rule in `is_resolved` /
  `has_cycle_evidence` (`state.py:266-273`, `:276-298`) that "briefless" is not the same as
  "never planned"; and the drafting door's rule "a split needs a Plan artifact" (`leaves.py:1800-1804`).
  Self-test: fixing only `state()` leaves a close bundle whose SUMMARY §1 Spec is empty
  (`assemble` builds §1-8 from the brief), which fails (b). Fixing only `split.accept` leaves any
  other path to the same shape deriving `UNPLANNED`, which fails (e). One module is not enough.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Depends on:**
- **Conflicts with:**
- **Ordering note:** Run 4 of `plan-0.60-bug-order.md`. The prereqs the plan named (#466, #480)
  are merged on `origin/main` (b0fe8c5, 60634b4). No file overlap with 508 / 526 / 528: this
  bundle stays in `split.py`, `state.py` and `template/tests/test_split.py`. #498 (run 5) touches
  the accept path after this lands.
- **Surfaces:** data
- **Difficulty:** medium (two production modules, one of which is `state()`, the function every
  driver path reads; the reviewer has to keep the whole state ladder and the split accept
  transaction in view)
- **Scope:** Remove the briefless-terminal shape: a split accepted on a parent with no top-level
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
- **Repro instruction:** On `origin/main`, in a temp bundle root: write an authored `brief.md`;
  run the driver's iterate-plan archive (`driver._archive_iteration(d, 1, include_brief=True)`),
  so `iteration-v1/brief.md` exists and `brief.md` does not; write a valid two-child
  `split-proposal.md` (shape as in `test_split.py` `Accepting.setUp`, `:88-111`); call
  `split.accept(parent, ["601", "602"], cfg)`; then `state.state(parent)` returns `UNPLANNED` and
  `parent/brief.md` does not exist.
- **External dependencies:** none
- **Test file:** template/tests/test_split.py (append to the `Accepting` class, `:88`, or a new
  class in the same file). Cover (a)-(f). For (e), build the briefless + close-marker shape
  directly. Build the realistic parent through the driver's own archive call, not by hand-placing
  files, so the test follows `_archive_iteration` if it changes. Seed that parent with a COMPLETE
  authored brief (slug, success criterion, repo + branch target) before archiving it. The
  `Accepting.setUp` brief is a bare `- **Slug:** parent`, and `check_planner` would rightly reject
  a Plan artifact built from it.
- **Citations expected:** Do must cite path:line on `origin/main` for every change. Peer callsites
  to mirror: the transaction order inside `split.accept` (`split.py:828-878`: archive → lineage →
  breadcrumb → marker, and the rollback branch) for where a parent-brief write goes and how it
  unwinds; the has-evidence reasoning in `state.is_resolved` (`state.py:266-273`) for how `state()`
  should treat "briefless but past Do".
- **Prior-art check (triage cycles):** by path, `git -C ../pdca-harness log --oneline origin/main -- template/src/pdca_harness/state.py template/src/pdca_harness/split.py`:
  latest are 7ab824f (error logs), f0bac00 (#467 child metadata), 9a19cb5 (#466 stub filing),
  a2eefe1 (#459 convergence), 5c83070 (#456 lineage). None touches `state()`'s briefless branch or
  gives `accept` a parent brief. Closed-unmerged PRs touching `state.py`, `split.py`,
  `test_split.py` (INTEGRATION §5 command): none (the repo has one closed-unmerged PR, and it
  touches none of these). Open PRs: none.
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: Auto-iterate (round 1): Check found implementation-level items only, no architectural judgment required — `template/src/pdca_harness/split.py:735-754` (`_archived_brief_source`)
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).

## Iteration 2 — carry-forward (from the previous attempt)
- Sign-off rationale: Auto-iterate (round 2): Check found implementation-level items only, no architectural judgment required — `_ITERATION_DIR` (the `^iteration-v(\d+)$` regex) and the "find the; `handoff.py:113-116`'s docstring for `check_planner`'s `dependencies`
- Full previous attempt preserved in `iteration-v2/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
