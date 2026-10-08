# Brief — issue 591 / stack-integration-line-per-run

> The Plan artifact (docs 02 §PLAN). Do reads ONLY this file.
> Verified against `eduralph/pdca-harness` `origin/main` @ `c67a14d` (after #593 merged as
> `b21f248`). #593 narrowed this bug but did not fix it — see "What #593 already changed".

- **Slug:** stack-integration-line-per-run
- **Defect:** In `[driver].wave_mode = "stack"`, every run that targets the same base folds
  onto ONE shared branch: `integrate.integration_branch(cfg, base)` depends only on the base
  (`template/src/pdca_harness/integrate.py:62-68`, `"pdca-integration/" + _flatten_base(base)`).
  So two `pdca flow` runs going at once on `main` (two independent milestone tracks) share
  `pdca-integration/main`, and each run's first fold force-pushes that branch fresh from the
  base (`integrate.py:362-371`, `fresh` ⇒ `push --force`), replacing the other run's line.
  From wave 1 on, a run's Do worktree and its C4 verify base both read that shared, moving
  branch by NAME, not the commit the run pushed: the Do worktree bases off
  `origin/<stack-base>` (`template/src/pdca_harness/worktree.py:96-98`), and the C4 gate gets
  `PDCA_VERIFY_BASE=origin/<stack-base>` (`template/src/pdca_harness/gates.py:568-570`).
  So run A's wave k+1 can be built and verified on run B's line, which lacks A's waves 0..k.
  **What #593 already changed (so Do does not re-fix it):** wave PRs now target the real
  base (`publish.py:266-283`), so open PRs no longer change base under the run; publish cuts
  from the recorded tip `stack-base-tip` and refuses a tip the line no longer holds; and a
  continuing fold refuses a line another run moved (`integrate.py:351-360`, the message cites
  #591). What is left: (a) Do and C4 still read the moving branch, so the wrong-base build
  happens before anything notices; (b) the refusal only fires at the NEXT fold, and a run's
  final wave has none; (c) even when it fires, the result is that two concurrent runs on one
  base cannot both finish — one always stops. Single-wave runs are unaffected (no fold).
- **Success criterion:** With the patch, two runs that drive DIFFERENT batches against the
  same `(repo, base)` never share an integration branch, and a run that is re-issued with the
  same requested ids gets the same branch name back. Demonstrated in the offline driver suite
  with real git against a bare `origin` (the `StackFoldGit` fixture): run A folds wave 0
  (bundle a1); run B (a different batch) then makes its first fold on the same base (bundle
  b1); run A then makes its continuing fold (a1 + a2). All three folds succeed; A's line on
  `origin` contains a1 and a2 and not b1; B's line contains b1 and not a1 or a2; and the
  stack base the flow records for A's wave-1 bundle (`publish.read_stack_base`, which Do's
  worktree and `PDCA_VERIFY_BASE` both read) names A's line, not B's. Pre-fix the third fold
  raises `IntegrationError` ("another run on the same base has likely moved it (#591)")
  because B's fresh fold force-pushed over the shared branch. The branch name stays a valid,
  injective single ref segment under `pdca-integration/` (two different bases, or a base and a
  batch key, can never produce the same name — the existing `_flatten_base` injectivity tests
  keep passing).
  **Flow-level case (the batch identity is threaded from the request, not the drive set).** A
  second test drives `flow.flow_ids` (stubbed leaves, `integrate.fold` patched to record the
  branch name it would use, or a real fold) and asserts: `flow_ids([a1, a2])` and a re-issued
  `flow_ids([a1, a2])` in which `a1` is already COMPLETE (so skipped as terminal and absent from
  the drive set) fold onto the SAME branch name; `flow_ids([a2])` alone, or `flow_ids([a1, b1])`,
  folds onto a DIFFERENT name. Pre-fix all of them use `pdca-integration/main`, so the
  "different" assertions fail. Importing `flow` in the test file is allowed (modules only).
- **Falsifiability:** RED is reachable offline: `template/tests/test_integrate_stack_bases.py`'s
  `StackFoldGit` class already builds a bare `origin` + primary checkout and calls the
  production `integrate.fold` with `folded_this_run`; interleaving two runs' folds on the same
  base reproduces the force-push-over and the `IntegrationError` today (the existing
  `test_a_runs_first_fold_starts_fresh_over_an_earlier_runs_line` and
  `test_a_line_another_run_moved_is_refused`, `:291` and `:302`, show both halves). Runs under
  the C4 gate as `cd template && PYTHONPATH=src python3 -m unittest tests.test_integrate_stack_bases`.
  No network, no `gh` (patched).
- **Invariant to restore:** One run's integration line is written only by that run. Within a
  run the line is append-only (the #593 contract, `integrate.py` module docstring lines
  26-30); this extends it across runs: no fold of one batch may replace or add to the line
  another batch's Do / C4-verify / publish reads. Source: `integrate.py` module docstring
  ("a run-scoped integration branch", lines 9 and 28-30) and `integration_branch`'s own
  docstring ("deterministic (a resumed run rebuilds the same branch) and injective",
  `integrate.py:63-67`) — today "run-scoped" is false in the name.
  **Known gap this fix does not close (pending #616):** "same requested ids ⇒ same branch"
  means a resumed run's first fold is `fresh` (`folded_tips = {}`, `flow.py:1813`) and
  force-pushes the same-named line rebuilt only from the bundles still in its drive set
  (`integrate.py:314-315`, `:370`) — the earlier run's waves drop off it, exactly as they do
  today on the shared name. A held bundle from the earlier run then has a `stack-base-tip` the
  line no longer holds, and its late publish refuses (`test_integrate_stack_bases.py:829`).
  #616 (wave 1, depends on this) closes it by re-folding the earlier run's unmerged
  prerequisites. This brief does not make it worse; it only stops a DIFFERENT batch from
  causing it. A resume with a subset of the original ids gets a different name — that is
  correct under this rule (it is a different request), and the old line is simply left alone. Not a single-module guard:
  the property is about every reader of the branch name (Do worktree, C4 base, publish,
  sweep/doctor), not about one call.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Depends on:**
- **Conflicts with:** 531
- **Ordering note:** Wave 0. `Conflicts with: 531` because both edit the `[driver]` comment
  block in `template/pdca.toml.jinja` (this one the `wave_mode = "stack"` paragraph, lines
  117-123; 531 the `wave_mode = "merge"` paragraph one line below) — close enough to collide
  in a fold, so 531 moves to wave 1 next to 616 at no extra wave. #616 depends on this one (it re-folds an earlier run's unmerged
  branches onto the run's line, so it must build on the run-scoped name and the "same
  requested ids ⇒ same branch" rule). #590
  touches `flow.py` too, but at the strict levelling (`flow.py:1815-1860`), not the fold call.
- **Surfaces:** data
- **Difficulty:** medium — `integrate.py` (branch name; `fold` needs the run's key), the one
  `fold` caller in `flow._drive_and_act` (`flow.py:1996-1998`), threading the key from
  `flow_ids` / `flow_batch` into `_drive_and_act`, and the user-facing text that names
  `pdca-integration/<base>`: `docs/07-crosscutting.md:660`, `template/pdca.toml.jinja:120-122`,
  `template/engine/scripts/run-verify.sh:25`, `template/PCDA/quality-cycle/09-parallel-lanes.md:69`,
  the `integrate.py` docstrings and the force-push error at `:372-374`. Existing tests that pin
  the shared name must be updated, not deleted.
- **Scope:** Make the integration branch belong to one batch: two different batches on the
  same base get different branches; the same requested batch (re-issued with the same ids,
  including ids the run skips as already terminal) gets the same branch, so the module's
  "a resumed run rebuilds the same branch" contract holds. Derive the batch identity from the
  ids the run was ASKED to drive — for `flow_ids`, the `pdca flow <ids>` list as given
  (normalised to bundle names, de-duplicated and sorted, so order and `500` vs `issue_500` do not
  matter), including ids skipped as terminal or briefless — not from the post-filter drive set,
  so a resumed run whose finished bundles are skipped still lands on the same name. Today only
  the post-filter set reaches `_drive_and_act` (`flow.py:1793-1801`); the requested list lives
  in `flow_ids` (`flow.py:2233-2275`) and must be passed down.
  **`flow_batch` (the CSV sweep):** it has no requested id list — it sweeps every in-flight
  bundle under `bundle_root` (`flow.py:2088-2093`). Key it on the sorted names of that sweep as
  taken at run start (before the claim / `_admit` / `partition_schedulable` trims). No resume
  stability is promised for `flow_batch` (finished bundles drop out of the sweep, so a re-run
  gets a new name); that is acceptable because it only ever means a fresh line, never a shared
  one. Do not key on the CSV path or contents. The issue's suggested shape is
  `pdca-integration/<flattened base>-r<short hash of the batch>`; `-r` cannot appear in
  `_flatten_base`'s output (every `-` it emits is `-h` or `-s`), so that keeps the name
  injective — Do may use it or an equivalent that keeps injectivity. Everything that reads the
  branch must read the run's name: the `stack-base` marker already carries the exact branch to
  Do, C4 and publish, so those need no change beyond receiving the new name.
  **Worktree and lock stay keyed on the base** (`_integ_worktree`, `integrate.py:163-168`, and
  `integ_lock`): two runs on one base keep sharing one integration worktree and one lock, held
  across fold and re-gate (`flow.py:1994-2023`). That is correct — folds are serialised, and
  each fold does `checkout -B` of its own branch in that tree — at the cost that run B waits
  out run A's re-gate. Do not re-key them; `sweep.py:90` / `doctor.py:83` therefore need no
  change. Update the docs text that
  names `pdca-integration/<base>`. Keep the existing in-run refusal of a moved line (it still
  guards the same batch run twice at once, which drive claims #565 should already refuse).
  / out of scope: re-keying the integration worktree or lock per batch; resume overwriting its
  own earlier line (#616); deleting old integration branches on `origin` (one branch per batch now
  accumulates; a sweep of branches whose PRs are all merged/closed is follow-up work, see
  #454); re-folding an earlier run's unmerged branches on resume (#616); merge mode (#531);
  changing how Do/C4 resolve the base (they keep reading the branch by name — once the name is
  per-batch that is correct).
- **Repro instruction:** On `origin/main`, in `template/`: build the `StackFoldGit` fixture;
  create and publish bundles a1, a2 (run A) and b1 (run B), all `org/repo @ main`. Call
  `integrate.fold(cfg, [a1], folded_this_run={})` (A's first fold, record its tip), then
  `integrate.fold(cfg, [b1], folded_this_run={})` (B's first fold), then
  `integrate.fold(cfg, [a1, a2], folded_this_run={("org/repo","main"): <A's tip>})`. The third
  call raises `IntegrationError … (#591)`; `git ls-remote origin` shows one
  `pdca-integration/main` holding b1. Post-fix the calls carry each run's batch identity
  (however Do threads it) and all three succeed on two separate branches.
- **External dependencies:** none
- **Test file:** template/tests/test_integrate_stack_bases.py (append to the `StackFoldGit`
  class; the C4 gate reverts only production hunks and keeps this file, so an appended test
  earns its red). Import modules only (`from pdca_harness import integrate, …`), never a new
  symbol, so the red leg loads and fails instead of erroring at import (the file's docstring
  states this rule). The flow-level case (see criterion) goes in the same file. Also add/adjust a pure-function case in `template/tests/test_integrate.py`
  for the name: different batches ⇒ different names, same batch ⇒ same name, still distinct
  across bases.
- **Citations expected:** Do must cite path:line on the target branch for every change. Peer
  callsite: the per-target keying the fold already does — `fold` groups by `(repo, base)` and
  names each group's branch at `integrate.py:310-312`, and `_point_at_integration` writes that
  exact branch into each bundle's `stack-base` (`flow.py:722-742`). Thread the batch identity
  the same way the run already threads `folded_tips` into `fold` (`flow.py:1813`, `:1996-1998`).
- **Prior-art check (triage cycles):** merged history by path —
  `git -C ../pdca-harness log --oneline origin/main -- template/src/pdca_harness/integrate.py`:
  `b21f248 stack mode: keep wave PRs intact and open them against the real base` (#593 — added
  the in-run append-only line and the moved-line refusal, citing #591; does not scope the
  name), `386d83b fix(integrate): injective _flatten_base …` (#199), `87ed36e` / `6c40f8c` /
  `dd73b45` (#297 locks). Closed-unmerged PRs touching `integrate.py`, `flow.py`, `waves.py`,
  `merge.py`: none (INTEGRATION §5 command, empty output). Open PRs: none. Related open:
  #454 (refs never pruned), #625 (live validation of #593).
- **Disposition hint:** likely-fix

Plan-review response: all five findings taken. Added a flow-level test that the batch key comes from the requested ids (terminal ids included), not the drive set; `flow_batch` is keyed on its start-of-run sweep with no resume stability promised; the resume-overwrites-its-own-line gap is stated as known and left to #616; worktree and lock stay keyed on the base; the docs list now includes `run-verify.sh:25` and `09-parallel-lanes.md:69`; declared `Conflicts with: 531`.

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.
