# Build notes — issue 419 / reviewer-target-git-writable — iteration 2

Target: eduralph/pdca-harness @ main, built in `$PDCA_WORKTREE` at base `bc7deaf`
(same base as iteration 1; the brief's citations were taken at `0fbfa26`, seams
unmoved). Line refs below are on the patched worktree unless marked "base".

## Iteration 1 carry-forward — what this round is about

The sign-off found **implementation-level items only** — the disposable
git-self-contained reviewer copy itself was not rejected. The failing gate was:

> T3 runtime: … == T3: root suite OK, **driver suite FAILED (rc 1)**

with no log preserved, so the reviewer could only call the red "provisional"
(their own clean rerun of all 1,591 tests was green). This round I **root-caused
the frozen red, reproduced it deterministically, and fixed it** — it is a
pre-existing environment leak in three driver tests, not a defect in the v1 patch.

### Diagnosis (reproduced, not speculated)

The T3 gate runs the driver suite with the **driver's inherited environment**:
`gates._merged_env` is `{**os.environ, **extra}` (`gates.py:778-782`), and under
in-driver lane concurrency the driver adds `PDCA_LANE=<slot>` to every gate's env
(`gates.py:539-542`). This instance runs lanes — `$PDCA_WORKTREE` is
`pdca-harness.pdca-wt-l1`, lane 1 — so the frozen T3 run's suite executed with an
ambient `PDCA_LANE` (and, in an auto-iterate flow, possibly `PDCA_AUTO_ITERATE`).
Three pre-existing driver tests assert *serial/default* behavior but let ambient
env leak into the unit:

- `test_flow_slice.LaneParallelism.test_serial_path_sets_no_pdca_lane`
  (`test_flow_slice.py:838-846`) — its `_LANE_GATE` shell gate prints
  `${PDCA_LANE:-none}`; the inner serial flow sets no lane, but the gate
  subprocess inherits the OUTER driver's `PDCA_LANE` via `gates.py:778-782` →
  `'l1' != 'none'`.
- `test_manual_test.ManualTestLaunch.test_lane_absent_when_serial`
  (`test_manual_test.py:105-112`) — `manual_test.launch` hands the app
  `{**os.environ, …}` (`manual_test.py:80`) → ambient `PDCA_LANE` appears in the
  asserted env.
- `test_autoiterate.ConfigPlumbing.test_off_by_default`
  (`test_autoiterate.py:747-750`) — `Config.load` honors the
  `PDCA_AUTO_ITERATE` env override (`config.py:658-659`) → ambient value flips
  the default to True.

Reproduction (all logs kept, commands below under Verification):

- clean shell, v1 patch applied: driver suite green **6/6 runs** (1,591 tests) —
  matches the reviewer's green rerun;
- same suite with `PDCA_LANE=l1 PDCA_AUTO_ITERATE=1` in env (simulating the lane
  gate env): **FAILED (failures=3)** — exactly those three tests, rc 1, the
  frozen signature ("root suite OK, driver suite FAILED (rc 1)");
- same adversarial env on the **unpatched base** (v1 hunks stashed): **the same
  3 failures** — the red pre-exists the #419 patch entirely;
- `PDCA_LANE=l1` alone → 2 failures; `PDCA_AUTO_ITERATE=1` alone → 1 failure.
  `PDCA_LANE` is *guaranteed* present in a lane run (`gates.py:539-542`), so the
  frozen rc 1 needs no further ingredients.

This also retro-explains the instance's history: upstream #402 records T3
driver-suite reds "not attributable to any of those patches" across whole waves,
green on clean-shell reruns — the same signature.

### Fix for the carry-forward (in the target, not the instance)

Make the three test classes hermetic: snapshot-and-strip `PDCA_*` from
`os.environ` in `setUp` (restored via `mock.patch.dict` + `addCleanup`):

- `test_autoiterate.py:722-735` (`ConfigPlumbing.setUp`)
- `test_flow_slice.py:787-801` (`LaneParallelism.setUp`)
- `test_manual_test.py:39-52` (`ManualTestLaunch.setUp`, plus `import os`,
  `test_manual_test.py:11`)

A test asserting a *default* must not read the operator's shell; the in-file
precedent is `test_env_overrides_the_toml` (`test_autoiterate.py:756`), which
already uses `mock.patch.dict` when it *wants* env. The same guard is added to
the new `test_reviewer_target_git.py` setUp (`:62-70`) as insurance against the
identical failure class. Instance-side alternatives (sanitizing env in the
instance's `run-suite.sh`) are explicitly out of the brief's scope
("instance-side config changes in pdca-pdca") and would fix only this instance,
not the target's suite for every lane-running project.

Re the second §6 item (T4, contribution artifacts withheld from review): those
artifacts are produced by the **publish** step, not by Do — nothing in this
bundle's three outputs can change that; it stays a human/process call.

## The #419 fix itself — unchanged from iteration 1 (deliberately)

The diagnosis above shows the frozen T3 red was not caused by the v1 production
change, and no review finding touched it, so `leaves.py` carries the identical,
already-C4-green change (do-not-resubmit-unchanged applies to the *rejected*
element — the T3 red — which is what this round fixes):

- **Defect** (base refs per the brief): `_reviewer_target`
  (base `leaves.py:1650-1680`) hands the per-cycle linked worktree as
  `$PDCA_TARGET`, granted via the family grounding flag (base
  `leaves.py:2084-2090`; codex `--add-dir` is read+write and its rationale names
  "git stash/unstash", `families.py:112-113`). But a linked worktree's git
  metadata — index included — lives under the PRIMARY checkout's
  `.git/worktrees/<name>/` (`worktree.py:14-16`), and stash writes objects into
  the shared `.git/objects`, both outside the granted dir and read-only in the
  leaf's confinement — so the contract's own pre-fix restore (`git stash`)
  always failed and C4 re-verification fell to §6 (issue_317, issue_372).
- **Fix**: `_reviewer_repo(d, target, sandbox)` (`leaves.py:1696-1774`) — for a
  bundle WITH a patch, materialize `<sandbox>/target` as a disposable,
  git-self-contained copy: `git archive HEAD` of the lane worktree (HEAD IS the
  pre-fix base; the patch sits uncommitted on top in the lane) → extract →
  `git init` + pinned local identity/`commit.gpgsign=false` (stash commits; the
  re-run must not depend on operator git config) → `add -A -f` + one commit
  `pre-fix base <sha>` → `git apply patch.diff` uncommitted on top. Exactly the
  state the reviewer must stash away; its whole `.git` lives inside the sandbox
  cwd, so stash/unstash write nothing near the primary checkout; the source is
  only ever READ (`archive`/`rev-parse`). Best-effort like the cited peer
  `_seed_sandbox_gate_logs` (`leaves.py:1746-1778`): any failure degrades to the
  old read-only grounding with a stderr note, never an aborted Check.
- **Wiring**: `_run_review_sandboxed` (`leaves.py:2182-2194`) and
  `_run_advisory_sandboxed` (`leaves.py:2522-2527`) hand the copy as
  `$PDCA_TARGET` when it materializes and withhold the grounding grant then (the
  copy is under the sandbox cwd; granting the real lane worktree besides would
  hand a read+write family the shared lane for no reviewer need). The brief's
  invariant SELF-TEST ("not satisfiable by guarding one module") is why the
  advisory seam is included. Reviewer prompt updated (`leaves.py:1646-1651`):
  the old "(read-only)" contradicted the re-run the contract asks for.

### Alternatives ruled out (with costs, from iteration 1 — still valid)

- **Grant the primary `.git` to the sandbox** (~2 lines: add `--add-dir
  <primary>/.git`): explicitly out of scope in the brief — it hands the leaf
  WRITE access into the primary checkout's git metadata (codex `--add-dir` is
  read+write, `families.py:112-113`), violating the success criterion's "the
  primary checkout and its `.git` receive no writes".
- **Harness-supplied pre-fix snapshot beside the patched target** (the brief's
  other sketched direction; ~60 lines — same archive/extract machinery, minus
  init/commit/apply): changes the review contract from stash/unstash to
  diff-two-trees, so every instance prompt naming "git stash/unstash" (this
  instance's reviewer argv, the codex profile comment) would need rewording, and
  the reviewer loses `git diff/status` as a self-check. The self-contained copy
  keeps the published contract's ops working verbatim.
- **`git clone --shared/--local/--depth 1`** instead of archive+init: shared
  clones write `objects/info/alternates` pointing back into the primary `.git` —
  git-incomplete again inside the confinement; a full clone copies history the
  reviewer doesn't need and cloning *from a linked worktree* has
  version-dependent quirks. Archive-of-HEAD is read-only on the source and
  self-contained by construction.

## Test — template/tests/test_reviewer_target_git.py (the brief's named file)

Per the brief's falsifiability recipe: tiny origin+clone fixture, lane worktree
built by **production** `worktree.rebuild_for_gate` (base + patch as a tracked,
uncommitted modification — a clean stash would no-op green), primary `.git`
chmod'ed `a-w` (restored in cleanup), then the **production** sandbox setup runs
end-to-end with only the model invocation (`_invoke_leaf_resilient`) faked; the
fake performs, from the sandbox, exactly the contract's git ops against whatever
`$PDCA_TARGET` production handed it.

- `test_review_target_supports_prefix_restore_primary_git_readonly` — the
  success criterion: stash succeeds in the confinement, pre-fix tree is `base`,
  `stash pop` restores `base+patched`, the round completes, and a full content
  snapshot of the primary (tree AND `.git`) is byte-identical before/after.
- `test_advisory_target_supports_prefix_restore_primary_git_readonly` — same
  via `_run_advisory_sandboxed` (the invariant's "not one module").
- `test_patchless_bundle_keeps_readonly_grounding_on_the_real_target` — scope
  guard pinning the degrade path (green on both legs by design).

New vs v1: the hermetic-env guard in `setUp` (`test_reviewer_target_git.py:62-70`).

## Verification (project runners; logs kept under /tmp on the Do host)

- **C4 gate** (`./engine/scripts/run-verify.sh`, the instance's configured
  oracle, run with `PDCA_BUNDLE`/`PDCA_WORKTREE`): **`C4 PASS: red without the
  fix, green with it`** (`/tmp/c4-run.log`). Red leg (production hunks reverted,
  tests kept): the two writability tests fail with the exact predicted denial —
  `error: Unable to create '…/checkout/.git/worktrees/checkout.pdca-wt/index.lock':
  Permission denied` — then green with the patch restored.
- **T3 wrapper** (`./engine/scripts/run-suite.sh`) from the instance root,
  including with the lane-gate env injected (`PDCA_LANE=l1 PDCA_AUTO_ITERATE=1`):
  **`== T3: root suite OK, driver suite OK`**, rc 0 (`/tmp/t3-run1.log`,
  `/tmp/t3-final.log`). Pre-fix, the same adversarial env yields
  `FAILED (failures=3)` (`/tmp/drv-gateenv.log`) — the frozen gate's rc 1,
  now red→green.
- **T2 docs** (`./engine/scripts/run-docs-check.sh`): `render_site: link audit
  OK`, rc 0 (no docs touched).
- Driver suite stability: 6/6 clean-shell green runs pre-change; post-change
  green in clean shell AND under the simulated gate env
  (`/tmp/drv-gateenv-fixed.log`, 1,591 tests OK).
- Patch applies cleanly on pristine base `bc7deaf` (`git apply --check` in a
  throwaway clone).

## Forced self-refutation (recorded answers)

- **(a) Genuine red?** **Yes, both parts.** (1) The C4 wrapper reverts exactly
  the production hunks and re-runs: both writability tests go red with the
  `index.lock: Permission denied` denial — the semantic failure, not an import
  error — then green restored. (2) The hermeticity fix: with the guard absent
  (v1 tree, and equally the bare base), the suite under the gate's env fails
  with exactly the 3 frozen-signature failures; with the guard, green — red→
  green shown on the same commands.
- **(b) Production path?** **Yes.** The named test drives
  `worktree.rebuild_for_gate`, `leaves._run_review_sandboxed`,
  `leaves._run_advisory_sandboxed` and through them
  `_reviewer_target`/`_reviewer_repo` — the seams the fix changes. The only
  stand-in is the model invocation (`_invoke_leaf_resilient` — a live model
  cannot run in the offline suite); the fake performs solely the contract's git
  ops against whatever `$PDCA_TARGET` production handed it, so a wiring
  regression still goes red. The three repaired driver tests keep asserting
  their original production units (`Config.load`, `flow`+gate env,
  `manual_test.launch`) — the guard only removes ambient-shell input.
- **(c) Fixture includes the fault?** **Yes.** The primary `.git` is genuinely
  read-only for the whole review round (the brief's deterministic stand-in for
  the confinement); the worktree is genuinely dirty with a tracked modification
  (stash cannot no-op); the byte-identical snapshot covers the primary's `.git`
  itself, so a "fix" that wrote through to the primary fails even if stash
  succeeds. For the T3 leg, the adversarial rerun injects the very variables
  (`PDCA_LANE`, `PDCA_AUTO_ITERATE`) the real lane gate env carries — the fault
  is in the fixture, not curated out.

## Commit-readiness

The target repo configures no formatter/linter/pre-commit hooks (no
`.pre-commit-config.yaml`; workflows are docs checks + require-linked-issue —
no docs touched). New code follows the files' prevailing style; no added line
exceeds the file's ~100-col convention (checked; all >100-col hits in touched
files pre-exist). No PR opened, nothing pushed, nothing marked ready.
