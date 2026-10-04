# Build notes — issue 591 / stack-integration-line-per-run

Target: `eduralph/pdca-harness` @ main, built in `$PDCA_WORKTREE`
(`/home/eddie/pdca/pdca-harness.pdca-wt`). Its HEAD is `9d2c539` (the run's stack base
`pdca-integration/main`: `c67a14d` + the issue_531 and issue_590 folds). `patch.diff` is
`git diff` against that HEAD. Line numbers below are post-patch in that tree unless marked.

## What changed and why

The bug: `integrate.integration_branch(cfg, base)` depended only on the base
(pre-patch `integrate.py:62-68`). So every run on one base shared one line, and a second
run's fresh first fold force-pushed over the first run's line. The fix makes the name
depend on the batch the run was asked to drive, and threads that batch from the request
down to the one `fold` call.

1. **Batch-scoped name** — `template/src/pdca_harness/integrate.py:67-92`.
   `integration_branch(cfg, base, batch=None)` returns
   `pdca-integration/<_flatten_base(base)>-r<batch_key(batch)>`. `batch_key` (`:86-92`)
   turns each id into a bundle name (`500` and `issue_500` give the same name), removes
   repeats, sorts, takes SHA-256, and keeps 12 hex chars.
   Why the name stays injective: `_flatten_base` turns every `-` into `-h` and every `/`
   into `-s`, so a `-` followed by `r` never appears in its output. The first `-r` in the
   name therefore marks exactly where the base ends. Two different bases still give two
   different names, and a base name can never be mistaken for base + batch key.
   `batch=None` keeps the old unscoped name. Only direct callers (tests, library use) get
   that. The flow always passes a batch.
2. **`fold` takes the batch** — `integrate.py:246` (new `batch=` keyword), `:342`
   (`integration_branch(cfg, base, batch)`), with the docstring paragraph at `:274-277`.
   Grouping by `(repo, base)` is unchanged. This is the peer pattern the brief cites
   (pre-patch `integrate.py:310-312`).
3. **Error and comment text** — `integrate.py:384-389` (moved-line refusal: "another run of
   the same batch, or someone outside the harness"), `:396-400` (push comment), and
   `:403-405` (force-push refusal hint). Also the module docstring at `:10-12` and
   `:31-34`. I kept the in-run refusal itself, as the brief requires.
4. **Threading in flow** — `template/src/pdca_harness/flow.py`:
   - `_drive_and_act(..., batch=None)` at `:1807`, documented at `:1847-1853`.
     `run_batch` is fixed at `:1866` from `batch`, or from `named` (the drive set as
     passed) for a library call. It is fixed before split adoption grows the drive set, so
     every fold in one run uses one branch.
   - Passed to `integrate.fold(..., batch=run_batch)` at `:2069-2070`, next to
     `folded_this_run`. This is the peer pattern cited at pre-patch `flow.py:1996-1998`.
   - `flow_ids` passes `batch=list(ids)` at `:2363`: the ids exactly as asked for, including
     ids skipped as terminal or briefless. `batch_key` does the normalising.
   - `flow_batch` records `swept = [d.name for d in bundles]` at `:2170`, right after the
     state filter and before the claim / `_admit` / `partition_schedulable` trims. It is
     passed at `:2209`.
   - `_point_at_integration` is untouched. It already writes the exact branch `fold`
     returned into each bundle's `stack-base`, so Do's worktree, `PDCA_VERIFY_BASE` and
     publish all get the run's own name with no further change (per the brief).
5. **Worktree and lock stay keyed on the base** (`_integ_worktree`, `integ_lock`
   unchanged), as the brief says. `sweep.py` and `doctor.py` are not touched.
6. **Docs that name the branch**: `docs/07-crosscutting.md:657-665`,
   `template/pdca.toml.jinja:120-125` (the `stack` paragraph only; the `merge` paragraph,
   which #531 touches, is not edited), `template/engine/scripts/run-verify.sh:24-29`, and
   `template/PCDA/quality-cycle/09-parallel-lanes.md:69` (two phrases in that one long line).

## Tests

- **Brief-named test file** `template/tests/test_integrate_stack_bases.py` (a copy is in
  the bundle). These were added to `StackFoldGit`:
  - `test_two_batches_on_one_base_never_share_an_integration_line`. Real git, bare
    `origin`. A folds wave 0 (A1). The flow-style `_point_at_integration` stamps A2's
    `stack-base`. B makes its first fold (B1). A2 is published, cut from the recorded
    stack base. A makes its continuing fold (A1 + A2). The test checks: the two lines
    differ; A's line has a1 and a2 but not b1; B's line has b1 but not a1 or a2; A's first
    tip is still on A's line; `publish.read_stack_base(A2)` names A's line and not B's.
  - `test_the_flow_keys_the_line_on_the_ids_it_was_asked_for`. This drives the real
    `flow.flow_ids` with stub leaves, so the real `integrate.fold` runs as a dry-run, and a
    spy wraps it to record the branch each fold returns. `[X1,X2,X3]` and a re-issued
    `[X3,X2,X1]` with X1 already COMPLETE (skipped as terminal) give the same name.
    `[X2,X3]` and `[X1,Y1,Y2]` give different names. I used three-bundle batches, not the
    brief's literal `[a1,a2]`: with a1 skipped, `[a1,a2]` drives one wave, and the flow
    only folds between waves, so there would be no fold to observe. X3 depends on X2, so
    two waves remain after X1 is skipped.
  - Helper `_fold_as`. It passes `batch=` only if `integrate.fold` has that parameter.
    That way the red leg fails the way the bug does (the third fold raises
    `IntegrationError … (#591)`) instead of on a `TypeError`. Post-fix it always passes the
    batch. If the parameter were renamed, the lines would be shared again and the test
    would still go red, so this does not weaken it.
  - Only modules are imported (`flow` was added, as the brief allows), and
    `inspect` from the standard library.
- **Pure-function case** `template/tests/test_integrate.py`
  `test_integration_branch_name_is_scoped_to_the_batch`. Different batches give different
  names. The same batch gives the same name regardless of order, repeats, or `500` vs
  `issue_500`. The scoped name differs from the unscoped one. It is still injective across
  bases, including a base literally named `main-r<key>`. `git check-ref-format` accepts it.
  The existing `_flatten_base` injectivity test is unchanged and still passes.
- **Existing tests updated, none deleted** — `template/tests/test_flow_slice.py`. Six
  `StackModeFlow` cases pinned `pdca-integration/main` for a `flow_ids` run. They now
  compute the run's line with a `_line(*ids)` helper (`integrate.integration_branch(cfg,
  "main", ids)`), and `_in_line` reads `self.line`. What each case asserts is the same.

`500` vs `issue_500` is tested only at the `batch_key` level. At the flow level,
`flow_ids(["issue_X2"])` maps to the directory `issue_issue_X2` (`cfg.bundle` always adds
the prefix), which is an existing CLI quirk this brief does not cover. I found it when my
first draft of the flow test used `issue_X2` and failed with a `DependencyGraphError`.

## Red → green (through the project's C4 script)

`PDCA_BUNDLE=… PDCA_WORKTREE=… ./engine/scripts/run-verify.sh` (the C4 gate command from
`pdca.toml`, run under `timeout 900`), result:

```
== C4 green leg … Ran 108 OK / Ran 15 OK / Ran 46 OK
== C4 red leg (production hunks reverted)
ERROR test_two_batches_on_one_base_never_share_an_integration_line
  pdca_harness.integrate.IntegrationError: origin's pdca-integration/main is at 65d9a20…,
  not at 52261f6…, the tip this run's last fold pushed — another run on the same base has
  likely moved it (#591)…
FAIL  test_the_flow_keys_the_line_on_the_ids_it_was_asked_for
  AssertionError: 'pdca-integration/main' == 'pdca-integration/main'
ERROR test_integration_branch_name_is_scoped_to_the_batch (TypeError: no batch param)
(+ the six updated test_flow_slice cases error the same way)
PDCA-EVIDENCE: C4 PASS — red without the fix, green with it
```

Full offline driver suite with the patch:
`cd template && PYTHONPATH=src python3 -m unittest discover -s tests` → `Ran 2325 tests,
OK (skipped=2)`. Docs checks (`lint_docs.py`, `render_site.py --check`) → OK.

## Self-refutation (forced)

- **(a) Genuine red?** Yes. The C4 script reverted the production hunks
  (`git apply -R --exclude=tests/*`), and the brief-named test failed. The main case raised
  the exact `IntegrationError … (#591)` the brief's Falsifiability predicts, on the third
  fold. The flow case failed its assertion because every run used
  `pdca-integration/main`. Afterwards the script restored the patch; I confirmed
  `git diff` matches `patch.diff` byte for byte.
- **(b) Production path?** Yes. The git case calls the production `integrate.fold`
  against a real bare `origin` and the production `flow._point_at_integration` /
  `publish.read_stack_base`. The flow case calls the production `flow.flow_ids` →
  `_drive_and_act` → `integrate.fold`. The spy only records what the real fold returns. No
  copy or re-implementation of the logic.
- **(c) Fixture includes the fault?** Yes. The fault is a second batch folding fresh on
  the same base between two folds of the first run, and the git case does exactly that
  with the real fold and a real force-push to `origin`. Nothing is left out: B's fold
  really runs and really pushes. Pre-fix it really overwrites A's line, which is why A's
  third fold refuses.

## Ruled out / alternatives

- **Hash the drive set (or `accepted`) instead of the requested ids.** Ruled out by the
  brief: a resumed run whose finished bundles are skipped would get a new name. `accepted`
  also grows each wave, so the name would change mid-run.
- **Put the batch key in `Config`.** That would hide per-run state in shared config. Two
  `flow_*` calls in one process (as the tests do) would leak it between runs. The keyword
  follows the same path `folded_this_run` already takes (one keyword on `fold`, one at the
  single call site).
- **Remove the `batch=None` unscoped fallback.** That would force all ~59 direct
  `integrate.fold(...)` calls in tests to pass a batch. Count, post-patch:
  `grep -c "integrate.fold(" template/tests/test_integrate*.py` → 11 + 48 lines. It would not
  make the flow any safer, because the flow always passes a batch. Kept as is.
- **Re-key the integration worktree / lock per batch.** The brief explicitly puts this out
  of scope. Not done.

## Leftovers / caveats

- The docs-render check wrote `.build-check/` into the worktree (I gave `--out` a path
  inside it). It is untracked, so it is not in `patch.diff`. My `rm` of it was blocked, so
  it is left for the harness to reclaim. Do not `git add -A` it at publish.
- Commit-readiness: the target has no formatter or pre-commit hooks. CI runs the docs
  linter, the render check and the suites. All new lines are ≤ 100 chars, matching the
  surrounding code. The commit needs a DCO `Signed-off-by` (publish adds it).
- Known gap, as stated in the brief and left to #616: a resumed run with the same ids does
  a fresh first fold onto the same-named line and drops the earlier run's waves.
