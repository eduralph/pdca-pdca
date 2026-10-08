# Brief — issue 531 / merge-mode-stale-base-merge

> The Plan artifact (docs 02 §PLAN). Do reads ONLY this file.
> Verified against `eduralph/pdca-harness` `origin/main` @ `c67a14d`. The issue was written
> against a v0.57.0-era tree; its line numbers are stale and the current ones are cited below.
> Since then #462 (bounded wait) and #582 (confirmed green) landed in `merge.py`, so the
> waiting machinery the issue's suggested direction relies on now exists in the harness itself.

- **Slug:** merge-mode-stale-base-merge
- **Defect:** In `[driver].wave_mode = "merge"`, a wave's PRs are merged back-to-back and
  nothing verifies the combination. `merge_wave` merges each bundle in turn
  (`template/src/pdca_harness/merge.py:75-84`); `_merge_one` readies the PR, reads its check
  rollup (`merge.py:259-284`, `_wait_for_green`) and runs `gh pr merge`
  (`merge.py:228`, `:287`). The rollup it reads belongs to the PR's head commit, which was
  tested against the base as it stood BEFORE this wave's earlier PRs merged. Nothing reads
  whether the PR is behind its base and nothing brings it up to date — the module issues only
  `gh pr ready`, `gh pr checks`, `gh pr merge` (and `gh pr ready --undo`); there is no
  `update-branch` and no behind/stale read anywhere in `merge.py` or `flow.py`. So whether a
  stale PR merges is decided by the host's `required_status_checks.strict`, which the harness
  neither reads nor documents:
  wave 0 = {A, B}, independent; A and B are each green against `main@X`; the driver merges A
  (`main@Y`); B's rollup still describes `X`; with `strict: false` GitHub merges B
  (`main@Z`). If A and B conflict semantically (no shared file needed), `main@Z` is red and
  wave 1 builds on it. With `strict: true` the second merge is refused instead, the wave stops
  with one PR merged and the rest untouched, and every later wave is lost (the shape of #462).
  `_audit_wave_overlap` (`flow.py:745-760`) sees only file overlap and is advisory.
  The optional `regate_between_waves` re-gate exists only on the stack branch of the wave
  boundary (`flow.py:1973`, `:2015-2023`); the merge branch (`flow.py:1968-1972`) never
  re-gates, while the knob's comment says "in merge mode the PR's own CI is the merge-boundary
  check" (`template/pdca.toml.jinja:166-170`) — which is exactly what `strict: false` does not
  deliver.
- **Success criterion:** With the patch, under `merge_requires = "all"` (the default) merge
  mode never merges a PR whose head was behind its base at the driver's last read before
  `gh pr merge`, and never merges a head other than the one whose rollup it read green. For every
  PR `merge_wave` merges: (1) the driver reads whether the PR is behind its base after the
  ready-mark; (2) if behind (an earlier member of the same wave just merged, or the base moved
  for any other reason), it brings the PR up to date with a merge-commit update of the PR's own
  branch (`gh pr update-branch` without `--rebase`, whatever `merge_method` is), then waits for
  the NEW head's rollup under the same bounded wait (`merge_wait_secs`) and the same fail-closed
  rules, and confirms it (#582); (3) it merges pinned to the head SHA whose rollup it read green
  (e.g. `gh pr merge --match-head-commit <sha>`), so a head that changed after the green read is
  refused by the host instead of merged. A multi-member wave therefore completes on a host with
  `strict: true` instead of stopping after its first merge. A PR that cannot be brought up to
  date (a conflict with the base, the update refused), whose updated head is not green, or whose
  pinned merge is refused stops the run, readiness undone, as every other refusal in
  `_merge_one` does today. Under `merge_requires = "required"` nothing changes: no behind read,
  no update, no rollup read — that setting means "trust the host's protection" (see Scope).
  Demonstrated in `template/tests/test_merge.py`:
  (a) a two-member wave where the second PR reads as behind only after the first PR's merge:
  post-fix the second PR is updated, its new head's rollup is read green, and only then
  `gh pr merge` runs on it, pinned to the new head's SHA; pre-fix `gh pr merge` is called on the
  second PR straight after the first, with no update — the test fails;
  (b) the head changes between the green read and the merge (the fake reports a different head
  SHA, or refuses the pinned merge): the driver does not merge that head and stops, readiness
  undone — pre-fix the merge goes through unpinned;
  (c) under `merge_requires = "required"`, the call log is exactly today's (no update, no
  behind read).
  Existing `test_merge.py` cases (a single up-to-date PR merges exactly as before apart from the
  added behind/head read and the pin; red/pending/empty rollups refuse; dry-run merges nothing)
  keep passing.
  **Accepted gap (stated, not tested):** a client-side driver cannot stop the base moving
  between its last read and the host executing the merge. On `strict: true` the host refuses
  that merge (the run stops, fail-closed); on `strict: false` that narrow window remains. The
  config comment recommends `strict: true` for merge mode for this reason.
- **Falsifiability:** RED is reachable offline: `test_merge.py` already drives the production
  `merge.merge_wave` / `_merge_one` with `subprocess.run` patched and `merge._sleep` patched to
  cost no wall-clock time (#462). Runs under the C4 gate as
  `cd template && PYTHONPATH=src python3 -m unittest tests.test_merge`. The scenario is
  order-dependent, so the existing `_gh` stub (`test_merge.py:67-71`, keyed on `cmd[2]` alone,
  same answer for every PR) is NOT enough: write a STATEFUL fake keyed by PR URL that records
  merges, reports B as behind only once it has seen `gh pr merge` for A, reports a new head SHA
  for B only after `update-branch` on B, and answers the rollup for B's current head. A and B
  must have DISTINCT `pr_url`s (the fixture defaults every bundle to the same one,
  `test_merge.py:91` — override it). Do owns which `gh` read reports "behind" and "head SHA"
  (e.g. `gh pr view --json mergeStateStatus,headRefOid`); the fake answers that read. The live
  host behaviour (`strict` true/false on a real repo) is NOT exercisable at Check — record it as
  supplementary evidence only.
- **Invariant to restore:** A merge-mode merge lands only a combination that was verified: the
  green evidence a merge relies on must describe the tree the merge produces, i.e. the PR's head
  including the base it merges into. This is the same rule #413 stated for checks ("the next
  wave must never build on a base whose verification was not GREEN", `merge.py` module
  docstring, lines 19-31) and #462/#582 stated for timing (green AT MERGE TIME, `merge.py:33-43`),
  extended from "which checks / when" to "against which base" and "which head". Correctness must not hinge on
  per-instance host config (`merge.py:21-24` says so for required checks; the same holds for
  `strict`). Not a single-module guard: it governs every PR the wave merges, the first included
  (the base can move between waves or from outside the run).
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Conflicts with:** 591
- **Ordering note:** No dependency. `Conflicts with: 591` because both edit the `[driver]`
  wave-sequencing comment block in `template/pdca.toml.jinja` (591 the `wave_mode = "stack"`
  paragraph, lines 117-123; this one the `wave_mode = "merge"` paragraph right after it,
  lines 124-128, plus `merge_requires` / `regate_between_waves` further down). The hunks are
  one line apart, close enough to collide in a fold, so they go in different waves. This costs
  no extra wave: 591 and 590 form wave 0, this one and 616 (which depends on 591) form wave 1,
  and this brief touches nothing 616 touches. Its main file, `merge.py`, is touched by no other
  issue in the batch.
- **Surfaces:** data
- **Difficulty:** medium — mostly `merge.py` (`_merge_one` and its helpers), plus the merge-mode
  text in `template/pdca.toml.jinja` (`wave_mode` / `merge_requires` / `merge_wait_secs` /
  `regate_between_waves` comments) and `template/docs/fork-discipline.md.jinja:51-60`
  (mandatory: lines 57-58 describe the rollup read "after the ready-mark and immediately before
  the merge", which the update → re-wait step changes).
  The reviewer must hold the existing fail-closed paths (ready → wait → confirm → merge → undo
  on refusal, resume idempotence via `merged.is_merged`, `merge.py:233`) in view.
- **Scope:** Make merge mode's merges land only verified combinations, per the invariant: a PR
  whose head lacks the current base tip is brought up to date with the base and re-verified
  (same bounded, confirmed, fail-closed rollup rules) before it merges, and the merge itself
  cannot land a head other than the one verified. This is what makes a host with `strict: true`
  usable for multi-member waves and a host with `strict: false` safe. The issue's suggested
  direction is GitHub's `gh pr update-branch` followed by the existing rollup wait; Do may use
  it or an equivalent that keeps the PR's own branch as the thing that merges. Update the
  merge-mode config comments so they describe what the driver now does, and state honestly that
  `regate_between_waves` has no effect in merge mode (it applies to the stack fold only).
  Update `template/docs/fork-discipline.md.jinja:51-60` (required, not optional) to describe
  the new sequence: ready → behind read → update if behind → bounded rollup wait on the new head
  → merge pinned to that head.
  **`merge_requires = "required"` is unchanged on purpose:** that setting already means "skip
  the driver's rollup gate and trust the host's branch protection" (`merge.py:259`,
  `pdca.toml.jinja:145`). An update there would be followed by an immediate merge on pending
  checks, so the fix does not add one. Its config comment must say plainly that it keeps the
  stale-base behaviour: with `strict: false` a stale PR can merge, with `strict: true` a
  multi-member wave stops after its first merge; use `"all"` for merge mode.
  **What sign-off covered changes, and the docs must say so:** after an update the head that
  merges is a merge commit of the reviewed PR branch with the newer base. Check reviewed
  `patch.diff`, not that combination; the combination is verified by the PR's own CI (the
  green rollup the driver reads), not by the reviewer. Say this in the fork-discipline text.
  The update is always a merge-commit update, never a rebase (a rebase rewrites the reviewed
  commits), regardless of `merge_method`; `merge_method` still governs only the final merge.
  / out of scope: running `regate_between_waves` in merge mode (detect-after-landing backstop —
  a separate change if wanted); reading the host's `required_status_checks.strict` and refusing
  merge mode on it; any change to `merge_requires = "required"` behaviour (documented only);
  closing the base-moved-after-last-read race on `strict: false` (accepted gap, see criterion);
  atomic merge groups (#412); retargeting a wrong-based PR (#500); stack mode
  (#591, #616); `merge_method = "rebase"`/`"squash"` specifics beyond keeping them working.
- **Repro instruction:** On `origin/main`, in `template/` with `PYTHONPATH=src`: two COMPLETE
  bundles A, B with patches and `publish.json` PR URLs (the `test_merge.py` fixture), merge mode,
  `merge_requires = "all"`, `merge._sleep` patched. Stub `subprocess.run` so every rollup is
  green and record the calls. Run `merge.merge_wave(cfg, [A, B])`. Observed: the call log is
  `ready A, checks A…, merge A, git fetch, ready B, checks B…, merge B` — B is merged on the
  rollup of a head that never contained A's merge; no update of B and no read of whether B is
  behind.
- **External dependencies:** none
- **Test file:** template/tests/test_merge.py (append to `MergeWave` or a new class in the same
  file; the C4 gate reverts only production hunks, so an appended test earns its red). Import
  modules only (`from pdca_harness import merge`), never a symbol the fix adds.
- **Citations expected:** Do must cite path:line on the target branch for every change. Peer
  callsite: the existing ready → bounded-wait → confirm → merge → undo-on-refusal sequence in
  `_merge_one` (`merge.py:239-300`, `_wait_for_green` at `:148`, `_undo_ready` at `:196`) — the
  re-verification after an update must reuse `_wait_for_green` and the same refusal messages /
  `_undo_ready` path, not a second wait loop. `_check_rollup` (`merge.py:108`) returns no head
  SHA, so read the head SHA separately (before and after the wait, or once after it) and pin
  the merge to it; do not change `_check_rollup`'s return shape.
- **Prior-art check (triage cycles):** merged history by path —
  `git -C ../pdca-harness log --oneline origin/main -- template/src/pdca_harness/merge.py`:
  `b2740ea fix(merge): confirm a green check rollup before merging a PR` (#582),
  `87c7352 fix(merge): wait for a new PR's checks before merge mode gives up` (#462),
  `2261b53 fix(merge): require a green check rollup before merge mode merges` (#413),
  `126db1f fix(merge): ready a non-final wave's PR before merging it` (#279),
  `5c4e332 feat(flow): opt-in auto-merge wave mode`. None reads or fixes a stale base.
  Closed-unmerged PRs touching `merge.py`, `flow.py`, `integrate.py`, `waves.py`: none
  (INTEGRATION §5 command, empty output). Open PRs: none. `gh search issues update-branch`:
  only #531 itself and #625 (stack-mode live validation) mention it.
- **Disposition hint:** likely-fix

Plan-review response: all six findings taken. Decided here (human may overrule at sign-off): `merge_requires = "required"` keeps today's host-trusting behaviour and its comment says so (option 2 — an update there would be followed by a merge on pending checks); the criterion now promises "not behind at the driver's last read" and lists the base-moves-after-read race as an accepted gap; head pinning is required and tested (case b); the test fake must be stateful and keyed by distinct PR URLs; the fork-discipline edit is mandatory (:51-60) and states that sign-off covered `patch.diff`, not the updated combination; updates are merge-commit only, never rebase. Also declared `Conflicts with: 591` (adjacent `pdca.toml.jinja` hunks, raised in 591's review), which moves this to wave 1 at no extra wave.

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: The goal and the overall sequence are right (ready → behind check → update-branch → bounded rollup wait on the new head → merge pinned to that head; `merge_requires = "required"` unchanged). Change how "behind" is decided, and make the post-update check tolerate GitHub's lag: 1. Replace the GraphQL `baseRef { compare(headRef: <sha>) { behindBy } }` read (`_BEHIND_QUERY` / `_read_head`) with the same pattern #593 / PR #619 used in `publish.py:_line_tip_refusal`: record the base branch's tip SHA, fetch, and decide with `git merge-base --is-ancestor <base-tip-sha> <pr-head-sha>` (exit 0 = up to date, 1 = behind, anything else or a failed fetch = refuse, fail-closed, saying git failed). Plain git, consistent with the stack-mode check; no reliance on GraphQL compare semantics. 2. After `gh pr update-branch`, do not read the head once and refuse if still behind: GitHub may finish the update asynchronously. Poll, bounded by and charged to `merge_wait_secs`, until the PR head contains the recorded base-tip SHA; only then wait for that head's rollup and merge pinned to it. Timeout still refuses with readiness undone. 3. Tests in template/tests/test_merge.py: add a case where the update lands late (the fake reports the old head for one or two reads after update-branch, then the updated one) and the PR still merges, pinned to the updated head; and a case where it never lands within the wait and the run refuses, readiness undone. Replace the hard-coded red head `"u2".ljust(40, "0")` in `test_updated_head_that_is_not_green_is_not_merged` with a fake option that marks the head produced by update-branch as red.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  The goal and the overall sequence are right (ready → behind check → update-branch → bounded rollup wait on the new head → merge pinned to that head; `merge_requires = "required"` unchanged). Change how "behind" is decided, and make the post-update check tolerate GitHub's lag:
  1. Replace the GraphQL `baseRef { compare(headRef: <sha>) { behindBy } }` read (`_BEHIND_QUERY` / `_read_head`) with the same pattern #593 / PR #619 used in `publish.py:_line_tip_refusal`: record the base branch's tip SHA, fetch, and decide with `git merge-base --is-ancestor <base-tip-sha> <pr-head-sha>` (exit 0 = up to date, 1 = behind, anything else or a failed fetch = refuse, fail-closed, saying git failed). Plain git, consistent with the stack-mode check; no reliance on GraphQL compare semantics.
  2. After `gh pr update-branch`, do not read the head once and refuse if still behind: GitHub may finish the update asynchronously. Poll, bounded by and charged to `merge_wait_secs`, until the PR head contains the recorded base-tip SHA; only then wait for that head's rollup and merge pinned to it. Timeout still refuses with readiness undone.
  3. Tests in template/tests/test_merge.py: add a case where the update lands late (the fake reports the old head for one or two reads after update-branch, then the updated one) and the PR still merges, pinned to the updated head; and a case where it never lands within the wait and the run refuses, readiness undone. Replace the hard-coded red head `"u2".ljust(40, "0")` in `test_updated_head_that_is_not_green_is_not_merged` with a fake option that marks the head produced by update-branch as red.
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
