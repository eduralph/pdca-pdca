# Build notes — issue 419 / reviewer-target-git-writable

Target: eduralph/pdca-harness @ main, built in `$PDCA_WORKTREE` at base `bc7deaf`
(the brief's citations were taken at `0fbfa26`; the seams are unmoved — line refs
below are on the patched worktree, base refs noted where they differ).

## The defect, restated from the code

`_run_review_sandboxed` hands the reviewer `$PDCA_TARGET = _reviewer_target(d, cfg)`
— normally the per-cycle **linked worktree** (base leaves.py:2091-2094 / `_reviewer_target`
at leaves.py:1656-1687 pre-patch) — and grants it via the family grounding flag
(codex `--add-dir` is explicitly "read+write … git stash/unstash", families.py:112-113).
But a linked worktree's git metadata lives under the **primary** checkout's
`.git/worktrees/<name>/` (its `.git` is an absolute pointer — worktree.py:14-15), and
stash writes objects into the shared `.git/objects`. Both are outside the granted dir
and read-only in the leaf's confinement, so the contract's own pre-fix restore
(`git stash`) fails: `Unable to create '….git/worktrees/….pdca-wt/index.lock':
Permission denied` — reproduced verbatim in the red leg below. The advisory leaves
(`_run_advisory_sandboxed`, base leaves.py:2421-2424) hand the identical shape.

## The fix — a disposable git-self-contained copy inside the sandbox

Of the brief's two sketched directions I chose the **disposable git-self-contained
copy**; the reviewer writes only it, the real target is not granted at all.

New `_reviewer_repo(d, target, sandbox)` (leaves.py:1696-1773): for a bundle **with a
patch**, materialize `<sandbox>/target` as

1. `git -C <target> archive --format=tar HEAD` → extract (read-only against the
   source; the lane's HEAD **is** the pre-fix base — `ensure`/`rebuild_for_gate`
   reset to the base and apply the patch uncommitted, worktree.py:260/280, 379);
2. `git init` + local `user.name`/`user.email`/`commit.gpgsign=false` (stash
   *commits* — the re-run must not depend on the operator's global git config);
   `add -A -f` (a tracked-but-gitignored base file must not drop out) + one commit
   `pre-fix base <sha>`;
3. `git apply <bundle>/patch.diff` — the patch sits **uncommitted** on top.

That is exactly the state the reviewer must stash away: `git stash` → pre-fix tree,
run the bundle's test, `git stash pop` → patched tree, all against git metadata that
lives **inside the sandbox cwd** (writable in both claude's and codex's confinement).
The primary checkout is only ever **read** (`archive`/`rev-parse`).

Wiring:
- `_run_review_sandboxed` (leaves.py:2174-2191): hand the copy as `$PDCA_TARGET`
  when it materializes; withhold the grounding grant then — the copy is under the
  sandbox cwd, and granting the real lane worktree besides would give a read+write
  family the shared lane for no reviewer need. Fallback (no patch / materialization
  declines): pre-#419 behavior, unchanged.
- `_run_advisory_sandboxed` (leaves.py:2519-2527): same shape. The brief's invariant
  carries a SELF-TEST ("not satisfiable by guarding one module") and the instance's
  observed §6 fallbacks come from the review *contract*, which the advisory
  adversary shares — fixing only the main reviewer would leave the same denial one
  callsite over.
- Reviewer prompt (leaves.py:1646-1651): the old "(read-only)" contradicted the
  re-run the contract asks for; it now states the copy's shape and that the re-run
  is executable in place, read-only otherwise.
- Best-effort posture mirrors the cited peer `_seed_sandbox_gate_logs`
  (leaves.py:1745-1777): any failure degrades to the old grounding with a stderr
  note, never an aborted Check.

## Alternatives ruled out

- **Granting the worktree's external git dir (+ objects) to the sandbox** — i.e.
  add `--add-dir <primary>/.git`. ~2 lines, but it is the exact thing the brief
  rules out of scope: it hands the leaf **write** access into the primary
  checkout's git metadata (codex's `--add-dir` is read+write), violating
  "the primary checkout and its `.git` receive no writes" and worktree.py's
  never-touch doctrine. The confinement is correct; the target's shape was wrong.
- **Harness-supplied pre-fix snapshot beside the patched target** (the brief's
  other direction): a second exported tree (`<sandbox>/target-prefix`) with no git
  at all. Similar size (~60 lines — the same archive/extract machinery, minus the
  init/commit/apply), but it changes the review contract: the instance's reviewer
  argv and the codex profile comment both say *stash/unstash*, so every instance
  prompt would need rewording to "diff two trees", and the reviewer loses `git
  diff`/`git status` as a self-check that the two trees differ by exactly
  patch.diff. The self-contained copy keeps the published contract's ops working
  verbatim.
- **`git clone` (shared or `--depth 1`) of the worktree** instead of
  archive+init: `--shared`/`--local` writes an `objects/info/alternates` pointing
  back into the primary `.git` — git-incomplete again inside the confinement (reads
  through the alternate are outside the grant); a full/shallow clone of a *linked
  worktree* as source has version-dependent quirks and copies history the reviewer
  doesn't need. Archive-of-HEAD is provably read-only on the source and
  self-contained by construction.

## Test — template/tests/test_reviewer_target_git.py

Per the brief's falsifiability recipe: tiny origin+clone repo, lane worktree built by
**production** `worktree.rebuild_for_gate` (base + patch applied as a tracked,
uncommitted modification — a clean stash would no-op green, brief's own warning),
primary `.git` chmod-ed `a-w` (restored in cleanup), then the **production** sandbox
setup is driven end-to-end with only the model invocation
(`leaves._invoke_leaf_resilient`) replaced by a fake that performs, from the sandbox,
exactly the contract's git ops against the handed `$PDCA_TARGET`.

- `test_review_target_supports_prefix_restore_primary_git_readonly` — the success
  criterion: stash succeeds, tree is `base` pre-fix, `stash pop` restores
  `base+patched`, the review round completes, and a full content snapshot of the
  primary (tree **and** `.git`) is identical before/after.
- `test_advisory_target_supports_prefix_restore_primary_git_readonly` — same via
  `_run_advisory_sandboxed` (the invariant's "not one module").
- `test_patchless_bundle_keeps_readonly_grounding_on_the_real_target` — scope
  guard: no patch ⇒ nothing to stash ⇒ the real target is handed as before (this
  one is green on both legs by design; it pins the degrade path).

## Verification (project runners only)

- Green leg (CONTRIBUTING.md:26 invocation): `cd template && PYTHONPATH=src
  python3 -m unittest tests.test_reviewer_target_git` → 3 tests OK.
- Formal red→green through the instance's C4 gate wrapper
  (`./engine/scripts/run-verify.sh`, pdca.toml:830), with `PDCA_BUNDLE`/
  `PDCA_WORKTREE` set: **`C4 PASS: red without the fix, green with it`**. The red
  leg (production hunks reverted) fails both writability tests with the exact
  predicted denial: `error: Unable to create
  '…/checkout/.git/worktrees/checkout.pdca-wt/index.lock': Permission denied`.
- T3 whole-suite wrapper (`./engine/scripts/run-suite.sh`): `T3: root suite OK,
  driver suite OK` — no regression across the template-repo and driver suites.

## Forced self-refutation (recorded answers)

- **(a) Genuine red?** **Yes.** `run-verify.sh` reverts exactly the production
  hunks (test files stay) and re-runs: both git-writability tests go red with the
  `index.lock: Permission denied` denial above — the semantic failure, not an
  import error — then green with the patch restored.
- **(b) Production path?** **Yes.** The tests drive `worktree.rebuild_for_gate`,
  `leaves._run_review_sandboxed`, `leaves._run_advisory_sandboxed` and (through
  them) `_reviewer_target`/`_reviewer_repo` — the production seams the fix
  changes. The only stand-in is the model invocation `_invoke_leaf_resilient`
  (a live model cannot run in the offline suite); the fake performs solely the
  contract's git ops against whatever `$PDCA_TARGET` production handed it, so a
  wiring regression (function present but not called) still goes red.
- **(c) Fixture includes the fault?** **Yes.** The primary `.git` is genuinely
  read-only during the whole review round (the confinement denial the brief says
  reproduces the sandbox deterministically); the worktree is genuinely dirty with
  a tracked modification (so the stash cannot no-op); and the byte-identical
  snapshot covers the primary's `.git` itself, so a "fix" that wrote through to
  the primary would fail the test even if stash succeeded.

## Commit-readiness

The target repo configures no formatter/linter/pre-commit hooks (pyproject.toml.jinja
carries only setuptools config; workflows lint docs only — no docs touched). New code
follows the file's prevailing style (≤100-col lines, module-doc conventions); the
offline suite CONTRIBUTING gates on is fully green. No PR opened, nothing pushed.
