# Brief — issue 616 / stack-resume-carries-unmerged-prereqs

> The Plan artifact (docs 02 §PLAN). Do reads ONLY this file.
> Verified against `eduralph/pdca-harness` `origin/main` @ `c67a14d`. The prerequisite the
> issue names, #593 (append-only fold over the real PR branches), is merged (`b21f248`), so
> the issue's line numbers are stale; the current ones are cited below.

- **Slug:** stack-resume-carries-unmerged-prereqs
- **Defect:** In stack mode, the recovery for a run that stopped part-way (an integrity stop,
  the pass budget, a crash, Ctrl-C) is to re-issue the same `pdca flow <ids>`. That resumed
  run builds dependents on a base that lacks their prerequisites:
  - bundles that finished in the earlier run are skipped as already terminal
    (`template/src/pdca_harness/flow.py:2242-2243`), so they are not in this run's batch and
    never enter `accepted` / the fold (`flow.py:1960`, `:1996-1998`);
  - with nothing folded yet, `_point_at_integration` clears the dependent's stack base
    (`flow.py:736-742`, `integ` is empty before the first fold), so it is cut from the plain
    target base;
  - `_runnable` accepts an out-of-batch prerequisite as ready once it is COMPLETE
    (`flow.py:706-711`). COMPLETE only means a draft PR was opened, so the prerequisite's work
    is not in the base unless that PR has merged. Only `Depends on (merged)` waits for the
    merge (#186, `flow.py:707-709`).
  Result: the dependent is built, C4-verified and published against a tree missing its
  prerequisite. Nothing reports it.
- **Success criterion:** With the patch, in stack mode with publishing on: a run whose batch
  holds a dependent `D` with `Depends on: P`, where `P` is NOT in the batch, is COMPLETE, has a
  published branch (its `publish.json` records the pushed branch) and its PR is NOT merged,
  builds `D` on a base that carries `P`'s published commits: before `D`'s wave is driven, the
  run's integration line on `origin` contains `P`'s branch head, and `D`'s recorded stack base
  (`publish.read_stack_base`, which Do's worktree and `PDCA_VERIFY_BASE` read) names that
  line. Demonstrated with real git against a bare `origin` (the `StackFoldGit`-style fixture)
  and stubbed leaves; pre-fix `D`'s stack base is cleared and the line is never created, so
  the same assertions fail. The pre-wave fold uses the SAME integration branch the run's own
  in-run folds use (#591's per-batch name, via the same `integrate.fold` call shape and batch
  key) and seeds `folded_tips`, so with a second in-batch bundle `E` (`Depends on: D`) the
  fold after wave 0 (D accepted) continues that line without a force-push and without
  `IntegrationError`: the line then holds `P` and `D`, and `E`'s recorded stack base names it. Every runnable bundle of the same `(repo, base)` target in
  the first wave is pointed at the line — including one that does not depend on `P` (assert it:
  an unrelated wave-0 bundle `U` of the same target also records the line as its stack base).
  That matches how later-wave stacking already behaves (`_point_at_integration`,
  `flow.py:722-742`); its PR shows `P`'s changes until `P` merges, as any later-wave PR does.
  Companion cases in the same file:
  (a) `P` COMPLETE, with a non-empty `patch.diff` and a resolvable target, but NO published
  branch ⇒ `D` is held (not built), named on stderr with the reason, and the rest of the run
  goes on;
  (b) `P` COMPLETE and its PR merged ⇒ nothing is folded for it and `D` builds on the base as
  today;
  (c) `P` COMPLETE with an empty or missing `patch.diff` (a close/no-fix disposition) ⇒ nothing
  is folded, `D` is NOT held and builds on the base as today (`merged.is_merged` already says
  True for it, `merged.py:44-45`; `integrate.unpublished` excludes it, `integrate.py:141-153`);
  (d) the pre-wave fold itself fails (`IntegrationError` — e.g. `P`'s branch was deleted and
  the host does not report its PR merged, `integrate.py:252-259`) ⇒ the run stops before
  wave 0, drives nothing, and stderr names the failure the same way the in-run fold's
  "did not integrate; STOPPING" line does (`flow.py:2004-2007`), with no traceback. Nothing is
  built on a base known to be missing a prerequisite.
  `Depends on (merged)` keeps its #186 behaviour (waits for the merge) unchanged.
- **Falsifiability:** RED is reachable offline. `template/tests/test_integrate_stack_bases.py`
  (`StackFoldGit`, `:113`) already provides a bare `origin`, a primary checkout, a production
  `_publish` helper that pushes a bundle's branch and writes `publish.json`, and patches `gh`
  (`merged.is_merged` can be patched to say merged / not merged). Driving
  `flow._drive_and_act` with stubbed leaves over `[D]` with `P` prepared as above shows `D`'s
  stack base cleared today. Runs under the C4 gate as `cd template && PYTHONPATH=src python3 -m
  unittest tests.test_flow_resume_stack_prereqs`. No network.
- **Invariant to restore:** Every bundle a stack-mode run builds is built, verified and
  published on a base that carries all of its declared prerequisites — whether the
  prerequisite was accepted in this run or in an earlier one. "COMPLETE" is not "in the base":
  an out-of-batch COMPLETE prerequisite is in the base only once its PR merged; until then
  only the integration line can carry it. Source: the wave contract in `_drive_and_act`'s
  docstring ("a dependent builds on its prerequisite's accepted result within one run",
  `flow.py:1757-1763`) and `_runnable`'s own docstring, which already states the hazard for
  `Depends on (merged)` ("a dependent built on a COMPLETE-but-unmerged base would miss the
  prerequisite", `flow.py:692-698`). Not a single-module guard: the property spans the
  readiness check, the fold and the stack-base pointing.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Depends on:** 591
- **Conflicts with:** 590
- **Ordering note:** Wave 1. `Depends on: 591` because the pre-wave fold this adds calls
  `integrate.fold` with the batch key #591 introduces and must land on the same per-batch branch
  the run's in-run folds continue — the criterion's `E` case (the fold after wave 0 continues
  the pre-wave line, no force, no `IntegrationError`) is what tests that. #591 also changes the
  `fold` signature and `_drive_and_act`'s arguments, so the line numbers cited here (taken from
  `c67a14d`, before #591) will have moved on the folded base Do gets: re-resolve each one
  there before citing it. `Conflicts with: 590` because both add work at the start of `_drive_and_act`,
  before the first wave (`flow.py:1815-1860`); #590 is in this batch (wave 0) and its brief
  edits exactly that region. #593 (named as a dependency in the issue) is
  already merged, so no edge is needed for it.
- **Surfaces:** data
- **Difficulty:** high — touches the readiness check (`_runnable`), the pre-wave set-up of
  `_drive_and_act` (a fold before wave 0), the stack-base pointing, and the fold's input
  (out-of-batch bundles), plus the hold reporting; the reviewer must hold the in-run fold
  contract (#593: append-only, first fold fresh, `folded_this_run` tips, `held_unpushed`) in
  view together with the new pre-wave fold.
- **Scope:** Make a re-issued (or any) stack-mode run carry its bundles' out-of-batch,
  COMPLETE, published-but-unmerged prerequisites into the base those bundles build on, so
  dependents are pointed at a line that has them. **One fold point: before the run's first
  wave** (not "before the first wave that needs them"), and only when some bundle in the drive
  set has such a prerequisite; with none, nothing changes. The issue's suggested direction:
  before the run's first wave, fold the published, still-unmerged
  branches of those prerequisites onto the run's integration line (#593's fold merges
  published branches, so this re-creates the earlier run's line from the same commits), then
  point the dependents at that line as usual. A prerequisite carried this way stays out of the
  run's results map (it is not driven). Every same-target bundle of the first wave is then
  pointed at the line, not just `P`'s dependents (as later waves already are). A prerequisite
  that is COMPLETE, patched and targeted but has no published branch holds its dependents (named on stderr, the same way `held_unpushed` holds in-batch
  dependents, `flow.py:1981-1987`, `:712-713`); it never lets them build on the wrong base. A
  merged prerequisite, or one with no patch, needs nothing: its work (or lack of it) is already
  the base. If the pre-wave fold raises, the run stops before wave 0 (criterion case (d)) —
  the same fail-closed stop the in-run fold applies. Transitive prerequisites
  come along for free when the prerequisite's branch was itself cut from an earlier line (its
  branch carries them); do not add a second walk unless the test shows one is needed.
  Applies only when the run publishes in stack mode (`--no-publish` sequences nothing,
  `flow.py:1784-1785`; merge mode merges instead). Update the stack-mode docs paragraph
  (`docs/07-crosscutting.md:640-700`) to say a re-issued run re-folds earlier
  unmerged prerequisites.
  / out of scope: the integration branch's naming / per-batch scoping (#591); `Depends on
  (merged)` semantics (#186 — unchanged); merge mode (#531); retargeting or rebasing earlier
  PRs; pruning old integration branches (#454).
- **Repro instruction:** On `origin/main`, in `template/` with `PYTHONPATH=src`, real git
  against a bare `origin`: plan and publish `P` (`org/repo @ main`, a patch adding a file),
  mark it COMPLETE, leave its PR unmerged (`merged.is_merged` → False). Plan `D` with
  `- **Depends on:** P` and a patch that needs `P`'s file. Call `flow._drive_and_act(cfg, [D],
  do_publish=True, …)` with the build/sign-off leaves stubbed. The publisher must NOT be in
  stub mode: a stub publisher turns every fold into a dry-run (`flow.py:1967`), and a dry-run
  never records an integration branch (`flow.py:2008-2009`), so the assertion would be
  vacuous. Patch `flow._publish_bundle` (or reuse the fixture's `_publish`) instead of running
  the real publisher leaf, and record the stack base `D` has when its wave is driven (e.g. by
  wrapping `flow._drive_wave`). Observed: `D`'s `stack-base` is absent when its wave runs, and
  no integration line on `origin` holds `P`; `D` is built on bare `main`.
- **External dependencies:** none
- **Test file:** template/tests/test_flow_resume_stack_prereqs.py (NEW file; the C4 gate
  classifies any `template/tests/*.py` in the patch as a test and reverts only production
  hunks, so a new file earns its red). Import modules only, never a symbol the fix adds, so
  the red leg loads and fails rather than erroring at import. Reuse the `StackFoldGit` fixture
  shape from `template/tests/test_integrate_stack_bases.py` (copy or subclass, Do's choice).
- **Citations expected:** Do must cite path:line on the target branch for every change. Peer
  callsites: the in-run fold and its holds in `_drive_and_act` (`flow.py:1973-2009`: the
  `integrate.unpublished(…, pushed=…)` hold, the `integrate.fold(…, folded_this_run=…)` call,
  and `folded_tips` / `integ` bookkeeping) — the pre-wave fold must feed the same `integ` /
  `folded_tips` so `_point_at_integration` (`flow.py:722-742`) and every later fold continue
  the same line append-only. Merged-ness: `merged.is_merged(cfg, dep)` as `_runnable` uses it
  (`flow.py:708`).
- **Prior-art check (triage cycles):** merged history by path —
  `git -C ../pdca-harness log --oneline origin/main -- template/src/pdca_harness/flow.py
  template/src/pdca_harness/integrate.py`: `b21f248 stack mode: keep wave PRs intact and open
  them against the real base` (#593, the prerequisite — adds `held_unpushed`, append-only fold,
  `stack-base-tip`; does not touch out-of-batch prerequisites), `69abaa1` (#597), `96c9704` /
  `389bf1a` (#469/#473 split adoption). Nothing re-folds out-of-batch prerequisites.
  Closed-unmerged PRs touching `flow.py`, `integrate.py`, `waves.py`, `merge.py`: none
  (INTEGRATION §5 command, empty output). Open PRs: none. Related open: #625 (live validation
  of #593), #591 (this brief's dependency).
- **Disposition hint:** likely-fix

Plan-review response: all four findings taken. Pointing every same-target first-wave bundle at the line is stated as intended and asserted (bundle `U`), with one fold point before the first wave; the no-published-branch hold applies only to patched, targeted prerequisites, and a no-patch prerequisite builds as today (case c); `Depends on: 591` is kept and now backed by the `E` case (the per-batch line continues without force), with a note that cited lines must be re-resolved on the folded base; a failing pre-wave fold stops the run before wave 0 (case d). #590 is confirmed in this batch and edits `flow.py:1815-1860`.

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: The core fix (pre-wave fold of out-of-batch, published, unmerged prerequisites) is sound; keep it. Fix these before resubmitting: - `Stacks on` edges must keep their pre-fix behaviour (PR against the parent branch, no re-pointing of wave-0 bundles). Only `Depends on` triggers the pre-wave carry. Add a test. - Hold per (prerequisite, dependent) pair: a cross-target dependent of an unpublished prerequisite must build as the docstring says, and the hold message must name exactly the held dependents. Add a cross-target test. - Guard `merged.is_merged` against a missing `gh` (OSError → "not merged", as `merged_head` does) so a plain `Depends on` never crashes the run with a traceback. - Do not silently carry a possibly stale `publish.json` (e.g. one older than the bundle's latest sign-off, left from a rejected attempt): hold its dependents and name it on stderr instead of building on it. - Mid-run split children are still out of scope; note the gap in the `_prereqs_to_carry` docstring.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  The core fix (pre-wave fold of out-of-batch, published, unmerged prerequisites) is sound; keep it. Fix these before resubmitting:
  - `Stacks on` edges must keep their pre-fix behaviour (PR against the parent branch, no re-pointing of wave-0 bundles). Only `Depends on` triggers the pre-wave carry. Add a test.
  - Hold per (prerequisite, dependent) pair: a cross-target dependent of an unpublished prerequisite must build as the docstring says, and the hold message must name exactly the held dependents. Add a cross-target test.
  - Guard `merged.is_merged` against a missing `gh` (OSError → "not merged", as `merged_head` does) so a plain `Depends on` never crashes the run with a traceback.
  - Do not silently carry a possibly stale `publish.json` (e.g. one older than the bundle's latest sign-off, left from a rejected attempt): hold its dependents and name it on stderr instead of building on it.
  - Mid-run split children are still out of scope; note the gap in the `_prereqs_to_carry` docstring.
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).

## Iteration 2 — carry-forward (from the previous attempt)
- Sign-off rationale: The pre-wave carry of out-of-batch, published, unmerged prerequisites is sound; keep it and the attempt-1 fixes. Fix these before resubmitting: - A prerequisite whose PR is CLOSED (not merged) must hold its dependents, never be carried — otherwise unrelated same-target PRs carry rejected work. Add a test. - A missing `pr_url`, or a `gh` failure, must not stop the whole run: hold only that prerequisite's dependents (named on stderr), and let unrelated bundles build. Covers a merged P with an empty `pr_url` and a deleted branch, which built correctly pre-fix. Add a test. - Work out the holds first; start a line for a prerequisite only if some dependent that needs it is not held. Add a test (D depends on carryable P and unpublished P2 ⇒ no line, U stays on the plain base). - Ask whether P is merged BEFORE the stale-record (timestamp) check, so a merged prerequisite never holds its dependents. - Narrow the `Stacks on` sentence in `flow.py` and `docs/07-crosscutting.md`: it holds only for a line the pre-wave fold starts, not for a line first folded after a later wave.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  The pre-wave carry of out-of-batch, published, unmerged prerequisites is sound; keep it and the attempt-1 fixes. Fix these before resubmitting:
  - A prerequisite whose PR is CLOSED (not merged) must hold its dependents, never be carried — otherwise unrelated same-target PRs carry rejected work. Add a test.
  - A missing `pr_url`, or a `gh` failure, must not stop the whole run: hold only that prerequisite's dependents (named on stderr), and let unrelated bundles build. Covers a merged P with an empty `pr_url` and a deleted branch, which built correctly pre-fix. Add a test.
  - Work out the holds first; start a line for a prerequisite only if some dependent that needs it is not held. Add a test (D depends on carryable P and unpublished P2 ⇒ no line, U stays on the plain base).
  - Ask whether P is merged BEFORE the stale-record (timestamp) check, so a merged prerequisite never holds its dependents.
  - Narrow the `Stacks on` sentence in `flow.py` and `docs/07-crosscutting.md`: it holds only for a line the pre-wave fold starts, not for a line first folded after a later wave.
- Full previous attempt preserved in `iteration-v2/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).

## Iteration 3 — carry-forward (from the previous attempt)
- Sign-off rationale: Three Do attempts have each closed the previous fix list and surfaced 3-5 new edge cases in the same hold/carry logic (patch now ~1400 lines). Re-check the approach in Plan before another build: decide whether to re-think or split it. Open findings the new plan must answer: - Holds must be known before any line starts. The current carry logic counts only its own hold reasons, so a dependent held by a `Depends on (merged)` wait, or by a held in-batch prerequisite, still starts a line and puts P's unmerged work under unrelated same-target bundles (U). This contradicts the patch's own docs ("A held bundle starts no line"). - "PR MERGED" is treated as "in the base" without checking where it merged. A PR merged into another fix's branch (stacked record, base != target base) lets D build silently without P. Count MERGED only when the record's base is the target base and it is not a stacked record; otherwise carry or hold. - Hold-message advice can loop: the pre-wave fold force-replaces an earlier run's line (so an accepted-but-unpublished H becomes unpublishable), and "re-publish" likely fails while the old PR is open. Decide: keep and extend the earlier run's line, or change the advice (re-drive / add PR URL by hand). Consider splitting: (1) carrying published unmerged prerequisites onto the line, vs (2) hold rules and user-facing hold messages.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  Three Do attempts have each closed the previous fix list and surfaced 3-5 new edge cases in the same hold/carry logic (patch now ~1400 lines). Re-check the approach in Plan before another build: decide whether to re-think or split it.
  Open findings the new plan must answer:
  - Holds must be known before any line starts. The current carry logic counts only its own hold reasons, so a dependent held by a `Depends on (merged)` wait, or by a held in-batch prerequisite, still starts a line and puts P's unmerged work under unrelated same-target bundles (U). This contradicts the patch's own docs ("A held bundle starts no line").
  - "PR MERGED" is treated as "in the base" without checking where it merged. A PR merged into another fix's branch (stacked record, base != target base) lets D build silently without P. Count MERGED only when the record's base is the target base and it is not a stacked record; otherwise carry or hold.
  - Hold-message advice can loop: the pre-wave fold force-replaces an earlier run's line (so an accepted-but-unpublished H becomes unpublishable), and "re-publish" likely fails while the old PR is open. Decide: keep and extend the earlier run's line, or change the advice (re-drive / add PR URL by hand).
  Consider splitting: (1) carrying published unmerged prerequisites onto the line, vs (2) hold rules and user-facing hold messages.
- Full previous attempt preserved in `iteration-v3/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
