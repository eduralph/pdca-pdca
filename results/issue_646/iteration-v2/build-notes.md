# Build notes — issue #646 (stack-reissue-continues-batch-line), attempt 2

Withheld from the reviewer. For the human at sign-off.

## Base I built on

The worktree (`$PDCA_WORKTREE` = `/home/eddie/pdca/pdca-harness.pdca-wt`) is at
`origin/pdca-integration/main` @ `12405dc`: `origin/main` @ `c67a14d` plus the folds of #531,
#590 and #591. The bundle's `stack-base` file says `pdca-integration/main`. The brief was
verified on `f594d8e`; `git diff f594d8e 12405dc` is empty, so its line numbers held. All
`path:line` below are on the patched worktree (`12405dc` + `patch.diff`).

**For the human (same as attempt 1):** the brief says not to build until #639 (#591) is merged
into `main`. On my local refs `origin/main` is still `c67a14d`, so #639 is not merged there, but
the worktree has #591 through the integration line, so the `TypeError` concern behind that rule
does not apply. The PR this produces is a stacked PR cut from the integration line; until
#531/#590/#591 merge, its diff against `main` shows their changes too.

## What the sign-off asked for, and what changed

The approach of attempt 1 is kept (sign-off: "the approach is right"). The four fixes:

1. **Lock held through fold, tip read and re-gate.** `_carry_finished` now opens one
   `contextlib.ExitStack()` and passes it as `locks=` to `integrate.fold`
   (`template/src/pdca_harness/flow.py:883-888`), the same shape as the in-run fold
   (`flow.py:2252-2262`). The `pushed_tip` read (`flow.py:888`) and the re-gate (`flow.py:900`)
   both happen inside that stack, so no other fold on the same base can move the shared
   integration worktree in between.
2. **Re-gate before wave 0.** With `[driver].regate_between_waves` on, the carried line is
   re-gated with `gates.run_integration(cfg, wt, hold_lock=False)` under the lock, and a red
   result stops the run before any wave (`flow.py:894-905`), mirroring `flow.py:2270-2285`.
3. **Closed PR already on the line: fail closed.** Before the carry fold, the new
   `integrate.read_lines` (`template/src/pdca_harness/integrate.py:246-288`) reads origin's
   line under the target's integration lock (after the fold's own fetch) and reports, by
   commit, whether the line already holds each finished id that is not being carried because
   its PR is CLOSED or unreadable. If it does, that target goes into `blocked`
   (`flow.py:855-871`): the line is not continued, and no drive-set bundle of that target is
   built this run (`flow.py:2117-2118`). One stderr line names the line, the id, the reason, the
   held bundles and two ways on (re-open the PR / fix the state read, or delete the line). The
   wrong "is not carried" text is now only printed for ids the line does NOT hold
   (`flow.py:845-854`).
4. **Overstated wording.** `publish.py:343-348` (dry-run plan) and `drift.py:58-64` now say
   only a re-issued run *that carries* keeps the line, and that one that carried nothing starts
   it fresh, matching `publish.py:729-734`. Also qualified: the `_line_tip_refusal` docstring
   (`publish.py:697-702`), `docs/07-crosscutting.md:665-695`, and one sentence in
   `template/PCDA/quality-cycle/09-parallel-lanes.md:69` (it said the run's first fold always
   starts fresh; the file is edited in-tree by feature commits, e.g. `b21f248`, `12405dc`).

Unchanged from attempt 1 (kept, reviewed clean last time): the trigger and the finished-id
scan (`flow.py:798-807`), the `_runnable` widening for plain `Depends on` only
(`flow.py:710`, `:719-722`), carried ids kept out of `accepted`, and `integ.update(...)` instead
of `integ = ...` in the in-run fold (`flow.py:2270`). `merged.pr_state` now also returns the
PR's `headRefOid` from the same `gh pr view` call (`template/src/pdca_harness/merged.py:99-130`),
so a closed PR whose branch was deleted can still be found on the line.

## Design decisions you should know about

- **Two lock holds, and why that is safe.** `integ_lock` is an `flock`; taking it again in
  the same process on a new file handle blocks forever (the comment at `flow.py:2273-2275`
  says the same). So `read_lines` cannot hold the lock and then call `fold`, which takes it
  itself. Instead the fold is told to continue *exactly the tip `read_lines` saw*
  (`folded_this_run={target: tip}`, `flow.py:873-874`). The fold's existing guard refuses a
  line that is not at that tip (`integrate.py:431-440`), so a line that moved between the read
  and the fold stops the run. The one case not caught: a line that did not exist at the read
  and was created in between; the fold then starts fresh and force-pushes, as any first fold
  does. Only a run of the same batch (refused by the drive claims, #565) or someone outside
  the harness writes a batch-scoped line. I changed the fold's "moved" error text to "the tip
  this run last pushed or checked there" (`integrate.py:434-439`) so it reads correctly for
  this caller; the existing test asserts only the branch, the tips and `#591`, which stay.
- **Unreadable PR state counts like CLOSED for the on-line check.** The sign-off named CLOSED.
  I applied the same block when the state cannot be read (no `pr_url`, a `gh` failure, `gh`
  missing), because the brief frames 4d as "the fail-closed half" of 4c, and a line holding a
  bundle whose state is unknown might be holding a closed one. Consequence: with `gh` broken,
  a re-issued run whose earlier run folded its finished ids builds nothing of that target and
  says to fix `gh`. If you would rather only CLOSED block, set `find[d.name]` only when
  `pr == "CLOSED"` (`flow.py:828-834`; the test
  `test_4d_a_line_already_holding_an_unreadable_pr_is_not_built_on`,
  `tests/test_flow_resume_stack_prereqs.py:546`, pins the current choice).
- **"Cannot tell" also blocks.** If the state cannot be read *and* the branch is gone, there is
  no commit to look for; when the line exists the run treats it as possibly holding the id and
  blocks (`integrate.py:284-286`, message "may hold … cannot tell", `flow.py:858-863`).
- **The whole target is held, not only wave 0.** The sign-off said "that target's wave-0
  bundles". A later-wave bundle of the same target, built on the plain base, would make the
  run's first fold of that target start the line fresh with a force-push, which strands
  anything recorded on the old line (H). Holding every bundle of the target for the run avoids
  that; it costs nothing extra (the filter runs per wave, `flow.py:2117-2118`).
- **"Holds it" is decided by commit** (`integrate._holds`, `integrate.py:552-566`): some commit
  that the bundle's branch head adds on top of the commit its branch was cut from (its
  recorded `stack-base-tip`, else the base) is on the line. Counting all of them, not just the
  head, catches a fixup pushed after the fold. The cut point matters: a wave>0 PR branch is cut
  from the line, so without it the line commits under it would read as "held".

## Alternatives ruled out (with cost)

- **Do the closed-PR check inside `integrate.fold`, under its own lock** (a `keep_off=` kwarg,
  a `HeldOnLine(IntegrationError)` subclass, check-only groups for targets with nothing to
  carry, and one `fold` call per target so a refusal stays target-scoped). Sketch: about +20
  lines inside fold's per-group body (`integrate.py:391-461`), +6 for the exception, +10
  in flow. My version is about +45 (`read_lines`) +30 (`_holds`, `_count`) with fold's merging
  body untouched. Similar size; I chose not to change the fold's group body, which carries the
  most tests (46 in `test_integrate_stack_bases.py`), and the `{target: tip}` guard closes the
  same gap.
- **Hold one lock across read and fold** by giving `fold` a `hold_lock=False` mode like
  `gates.run_integration`'s. About +12 lines in fold (skip acquiring per group) and +8 in flow
  (take each target's lock in fold's sorted order). Not done: the tip guard above gives the same
  protection without a second way to lock inside fold.
- **Detect "on the line" by the fold's merge-commit subject** (`pdca-integrate: issue_P`,
  `integrate.py:478`): about 6 lines (`git log --format=%s base..line` + a match), and it works
  with the branch gone. Rejected: the module rule is "by commit, never by message" (#593), and
  it misses P's work reaching the line through another branch that contains it (a legacy
  `Stacks on` child).
- **`merge-base --is-ancestor head line` only** (3 lines, reuse `_carries`): misses a fixup
  pushed after the fold. Chose the counting version (+25 lines).
- **Make `merged_head` call `pr_state`** (the code reviewer's cleanup note, saves ~15 lines).
  Not done: `merged_head` would start printing on a malformed `gh` reply, and it sits on the
  fold's merged-and-deleted path; no functional gain for this issue.

## Known limits (named, not fixed)

- Criterion (7) stands, as the sign-off said: a re-issued run in which no driven bundle plainly
  `Depends on` a finished id carries nothing, and its first fold starts the line fresh. The
  docs and messages say so.
- A branch force-rewritten after the fold (re-published) reads as "not on the line", because
  none of its new commits are there. A host head this clone has never fetched reads as "not on
  the line" (as `_carries` does). A wave>0 finished bundle with no recorded line tip (a marker
  older than #593) may read as "on the line" and block its target (the fail-closed direction).
- A dependent in another target of a carryable id whose own target is blocked is not held
  (cross-target edges are never carried by the fold anyway, #187).
- Observation, not touched: `merged.is_merged` (`merged.py:32-59`) has no `OSError` guard, so
  `gh` missing during a `Depends on (merged)` check would raise. Pre-existing, and `is_merged`
  is child-2's area.

## Self-refutation (forced)

- **(a) Genuine red? Yes.** Through the project's C4 runner (`engine/scripts/run-verify.sh`,
  which reverts only the production hunks): green 24/24 new + 46/46 existing; red 19 of 24 new
  tests fail plus the 2 updated wording tests. The 5 that pass on both legs are the "unchanged"
  guards (empty patch, missing patch, no dependency, `Stacks on`/`Depends on (merged)`,
  `--no-publish`/merge mode), which must pass on both. I also put **attempt 1's production
  code** under the new tests (swapped hunks in the worktree, ran the same C4 runner, swapped
  back; `git diff | cmp - patch.diff` confirmed the restore). The new tests fail on exactly
  the four sign-off items:
  - lock: `test_1_the_carry_reads_its_tip_and_re_gates_under_the_integration_lock` recorded
    `['lock+', 'lock-', 'tip', 'wave issue_D', …]` — the tip read after the lock was released,
    and no re-gate;
  - re-gate: `test_6_a_red_re_gate_of_the_carried_line_stops_before_wave_0` — D and U built;
  - closed/unreadable on the line: the four `test_4c/4d_…line…` cases — E and U built on the
    line holding P;
  - wording: `test_a_recorded_tip_is_the_cut_point_and_the_plan_shows_its_guard` — the
    unqualified "a re-issued run of the batch keeps it there".
- **(b) Production path? Yes.** The tests call the real `flow._drive_and_act` with
  `batch=[…]`, the shape `flow_ids` passes (`flow.py:2549-2552`). Real code inside: `_runnable`,
  `_carry_finished`, `_point_at_integration`, `integrate.read_lines`, `integrate.fold` (real git
  against a bare `origin`), `integ_lock` (wrapped only to log enter/exit), `pushed_tip`,
  `merged.pr_state` / `merged_head` / `is_merged`, `gates.run_integration` running a real
  repo-scoped gate command (`test -e p.txt` / `test ! -e p.txt`) in the integration worktree,
  and the real `publish.publish` (with `open_pr=False`), which cuts, applies, commits and pushes.
  Stubbed: `flow._drive_wave` (build/sign-off), `publish.draft_texts`,
  `publish._warn_if_squash_only` (a `gh repo view`), and `gh` itself, answered from a table at
  `merged`'s `subprocess` boundary.
- **(c) Fixture includes the fault? Yes.** P is only in `batch`, never in the drive set, as
  `flow_ids` skips it. P has a real pushed branch and `publish.json`. The earlier run's line is
  made by the real fold with the same batch key, and really holds P (or only Q, in the
  "not on the line" case). P's PR is answered CLOSED, or `gh` really raises
  `FileNotFoundError`, or really exits 1. P's branch is really deleted on origin in the
  "branch gone" cases. The red re-gate is a real gate command that fails on the carried tree.

## Commands run (the project's runners)

- C4: `PDCA_BUNDLE=… PDCA_WORKTREE=… ./engine/scripts/run-verify.sh` → `PDCA-EVIDENCE: C4 PASS
  — red without the fix, green with it` (final run on the final `patch.diff`).
- T3: `PDCA_WORKTREE=… ./engine/scripts/run-suite.sh` → root suite OK (24), driver suite OK
  (2349, 2 skipped).
- T2: `./engine/scripts/run-docs-check.sh` → docs lint clean, site render + link audit clean.
- Commit-readiness: the target has no formatter, linter config or installed hooks (no
  `core.hooksPath`, no non-sample hooks, no ruff/black/flake8 config; CI runs only the docs
  checkers and the root render suite). `CONTRIBUTING.md` asks for a DCO sign-off, which
  publish adds (`git commit -s`). No unused imports in the touched files (checked with `ast`;
  pyflakes/ruff are not installed). Added lines are at most 96 columns.

## Housekeeping I owe you

- I wrote one log file outside the harness roots by mistake: `/tmp/c4-646-run1.log` (output
  of my first C4 run). I did not delete it (no `rm`); it is safe to remove.
- The hunk swap for the attempt-1 comparison stored two unreferenced blobs in the
  pdca-harness object store (`git hash-object -w`: `ce8816fe…`, `e98ec6e3…`); no ref points at
  them and `git gc` will drop them.
- The new test file is marked intent-to-add (`git add -N`) in the worktree's index, so
  `git diff` includes it.

No external dependency was missing.
