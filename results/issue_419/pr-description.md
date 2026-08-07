## Summary
**User impact:** Every review round for a change that carries a patch ends with the
automated double-check stamped "needs a human". The reviewer is asked to temporarily
undo the fix, run the test against the unfixed code, then restore the fix — but the
workspace it is handed rejects every one of those operations, so the person signing
off has to redo that verification by hand, cycle after cycle (observed on every
patched cycle in a live instance).

This PR hands the reviewer a throwaway, self-contained copy of the code inside its
own workspace, so the undo/re-run/redo check works in place — while the real
checkout, including its git bookkeeping, receives no writes at all.

Reported in [#419](https://github.com/eduralph/pdca-harness/issues/419).

## What to look at
- `template/src/pdca_harness/leaves.py` — the new `_reviewer_repo()` helper (builds
  the disposable copy) and the hand-over in `_run_review_sandboxed` /
  `_run_advisory_sandboxed`. The reviewer prompt no longer calls the target
  "(read-only)" when a patch is present.
- Three existing test files gain a hermetic `setUp` that strips ambient `PDCA_*`
  variables — a pre-existing suite flakiness this work surfaced (details under Fix).
- To reproduce the defect on `main`: create a repo with one commit, `git worktree
  add` a linked worktree, modify a tracked file in the worktree, `chmod -R a-w` the
  primary repo's `.git`, then run `git stash` in the worktree — it fails with
  "unable to write new index file", because the worktree's index lives under the
  primary checkout's git directory.

## Root cause
The sandboxed review leaves ground on the per-cycle linked worktree as
`$PDCA_TARGET` (`template/src/pdca_harness/leaves.py:1649-1679`, handed and granted
at `leaves.py:2080-2087` on `main`), and the codex grounding flag is deliberately
read+write so the reviewer can "git stash/unstash, re-run tests"
(`families.py:101-102`). But a linked worktree's git metadata — its index included —
lives under the primary checkout's `.git/worktrees/<name>/` (`worktree.py:14-15`:
its `.git` is an absolute pointer), and stash writes objects into the shared
`.git/objects` — both outside the granted directory and read-only in the leaf's
confinement, so every index-writing git operation the contract asks for failed.

## Fix
- New `_reviewer_repo(d, target, sandbox)`: for a bundle WITH a patch, materialize
  `<sandbox>/target` as a disposable git-self-contained copy — `git archive HEAD`
  of the resolved target (HEAD is the pre-fix base; the patch sits uncommitted on
  top in the lane), extract, `git init` with pinned identity and
  `commit.gpgsign=false` (stash commits; the re-run must not depend on the
  operator's git config), one commit `pre-fix base <sha>`, then `patch.diff`
  applied uncommitted on top. Exactly the state the reviewer must stash away; its
  whole `.git` lives inside the sandbox cwd, and the source repository is only ever
  read (`archive`/`rev-parse`).
- `_run_review_sandboxed` and `_run_advisory_sandboxed` hand the copy as
  `$PDCA_TARGET` when it materializes and withhold the grounding grant then — the
  copy is under the sandbox cwd, and granting the real checkout besides would hand
  a read+write family the shared lane worktree for no reviewer need. Best-effort,
  mirroring `_seed_sandbox_gate_logs`: any failure degrades to the old read-only
  grounding with a stderr note, never an aborted review. Patchless bundles keep
  read-only grounding on the real target (nothing to stash → no re-run; full
  history serves citations better).
- Hermetic-env repair in three existing driver tests: a project's suite gate runs
  this suite with the driver's inherited environment (`gates.py:777-780` on `main`),
  and a lane-running driver exports `PDCA_LANE` into every gate's env
  (`gates.py:539-541`) — so `test_off_by_default` (`Config.load` honors
  `PDCA_AUTO_ITERATE`, `config.py:658-659`), `test_serial_path_sets_no_pdca_lane`
  (its gate subprocess inherits the outer `PDCA_LANE`), and
  `test_lane_absent_when_serial` (`manual_test.launch` hands the app
  `{**os.environ, …}`, `manual_test.py:80`) asserted defaults against the
  operator's shell. Their `setUp` now snapshots `os.environ` and strips `PDCA_*`
  (restored on cleanup); the new test guards itself the same way.

## Verification
- **Claim:** with the primary checkout's `.git` read-only (the deterministic
  stand-in for the reviewer's confinement), the target the production sandbox setup
  hands over supports the pre-fix restore and re-apply — `git stash` succeeds, the
  tree is the pre-fix base, `git stash pop` restores the patched state — and the
  primary checkout, tree AND git metadata, is byte-identical before/after.
  **Checked:** `template/src/pdca_harness/leaves.py:2080-2087` on `main` hands the
  linked worktree, whose index lives under the primary `.git/worktrees/<name>/`
  (`worktree.py:14-15`) — pre-fix the restore fails there with
  `Unable to create '…/.git/worktrees/…/index.lock': Permission denied`.
- **Claim:** the invariant holds for every consumer of the target, not one module —
  the advisory leaves share the reviewer's contract. **Checked:** the same
  end-to-end assertion runs through `_run_advisory_sandboxed`; patchless bundles
  are pinned to the unchanged read-only grounding by a third test.
- **Claim:** the driver-suite failures seen when this suite runs under a
  lane-running driver's gate are pre-existing ambient-env leaks, not caused by any
  patch. **Checked:** `gates.py:539-541` + `gates.py:777-780` on `main` guarantee
  `PDCA_LANE` in the suite's env there; with `PDCA_LANE=l1 PDCA_AUTO_ITERATE=1`
  injected, unpatched `main` fails exactly the three named tests
  (`test_autoiterate.py:736`, `test_flow_slice.py:828`, `test_manual_test.py:95`);
  with the hermetic `setUp`, the full suite (1,591 tests) is green both in a clean
  shell and under that adversarial env. In-file precedent for the technique:
  `test_env_overrides_the_toml` (`test_autoiterate.py:744`) already uses
  `mock.patch.dict` when it *wants* env.
- **Test:** `template/tests/test_reviewer_target_git.py` (new) — builds the
  origin/clone/worktree fixture with the production `worktree.rebuild_for_gate`,
  applies the patch as a tracked uncommitted modification (a clean stash would
  no-op green), chmods the primary `.git` read-only, and drives the production
  review/advisory runners with only the model invocation faked. Fails pre-fix with
  the exact index-lock denial; passes post-fix.

Fixes #419
