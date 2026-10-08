## Summary
**User impact:** with the default `stack` wave mode, two `pdca flow` runs going at the
same time against the same base branch (say, two separate milestone tracks on `main`)
step on each other. The second run wipes out the first run's staging branch, so the
first run's next wave is built and tested on the other run's work, missing its own
earlier fixes. The first run then stops with an error, so the two runs cannot both
finish.

This PR gives each run its own staging (integration) branch, named after the set of
issues it was asked to drive. Different runs no longer share one; running the same
issues again gets the same branch back.

Reported in [#591](https://github.com/eduralph/pdca-harness/issues/591).

## What to look at
- The branch name is now `pdca-integration/<base>-r<key>`, where the key is a short
  hash of the issue ids the run was given (order and `500` vs `issue_500` do not
  matter). Look at `integration_branch` / `batch_key` in `integrate.py`, then at how
  `flow_ids` and `flow_batch` pass the run's ids down to the one `fold` call.
- To see it: run `template/tests/test_integrate_stack_bases.py`. The new case
  interleaves two runs on one base against a real bare `origin`; without the fix the
  third fold fails with "another run on the same base has likely moved it (#591)".
- The integration worktree and lock stay per base on purpose, so two runs on one base
  still take turns folding (run B waits out run A's re-gate).
- This branch was cut from the line that already carries #531 and #590 from the same
  run, so their commits show in this PR's diff until those PRs merge. Merge them first,
  with a merge commit.

## Root cause
`integrate.integration_branch(cfg, base)` depended only on the base, so every run on a
base used `pdca-integration/<base>`, and each run's first fold force-pushes that branch
fresh from the base. Do's worktree and the verify gate read that branch by name from
wave 1 on, so a concurrent run's force-push silently changed what they built on.

## Fix
- `integration_branch` takes an optional `batch` and returns
  `pdca-integration/<flattened base>-r<batch_key(batch)>`. `batch_key` normalises ids
  to bundle names, de-duplicates, sorts, and keeps 12 hex chars of SHA-256. `-r` never
  appears in `_flatten_base`'s output (its `-`s are always `-h` or `-s`), so the name
  stays injective across bases. `batch=None` keeps the old name for direct callers.
- `fold` gets a `batch=` keyword, passed through to `integration_branch`.
- `_drive_and_act` gets `batch=`, fixes it once before split adoption can grow the drive
  set, and passes it to `fold`. `flow_ids` passes the ids as requested (ids skipped as
  finished or briefless included), so a re-issued run lands on the same branch.
  `flow_batch` passes its sweep as taken at run start; no resume stability is promised
  there, which only ever means a fresh branch, never a shared one.
- The existing refusal of a line moved under a run is kept; its message and the
  force-push hint now say what can still move it. Docs updated:
  `docs/07-crosscutting.md`, `template/pdca.toml.jinja` (the `stack` paragraph only),
  `template/engine/scripts/run-verify.sh`, `template/PCDA/quality-cycle/09-parallel-lanes.md`.

Not in this PR: a resumed run with the same ids still starts its own line fresh and
drops its earlier waves (#616 handles that), and old integration branches are not
pruned on `origin` (#454).

## Verification
- **Claim:** two runs driving different batches on the same base never share an
  integration branch; the same requested ids get the same branch back.
- **Checked (pre-fix, on `main`):**
  - `template/src/pdca_harness/integrate.py:62-68` — the name depends only on the base.
  - `template/src/pdca_harness/integrate.py:351-360` and `:370` — a continuing fold
    refuses a moved line; a fresh fold pushes with `--force`.
  - `template/src/pdca_harness/worktree.py:96-98` and
    `template/src/pdca_harness/gates.py:568-570` — Do's worktree and the verify base
    read the stack branch by name, so they follow whatever was last pushed there.
  - `template/src/pdca_harness/flow.py:1793-1801` — only the filtered drive set reached
    `_drive_and_act`; the requested ids lived only in `flow_ids` (`flow.py:2158-2281`).
- **Test:** `template/tests/test_integrate_stack_bases.py`
  - `test_two_batches_on_one_base_never_share_an_integration_line` — real git: A folds
    wave 0, B folds fresh on the same base, A folds again. Fails pre-fix with the #591
    `IntegrationError`; passes post-fix with A's line holding a1 + a2 and not b1, B's
    holding b1 only, and A's wave-1 recorded stack base naming A's line.
  - `test_the_flow_keys_the_line_on_the_ids_it_was_asked_for` — drives `flow.flow_ids`:
    `[X1,X2,X3]` and a re-issued `[X3,X2,X1]` with X1 already complete fold onto the same
    branch; `[X2,X3]` and `[X1,Y1,Y2]` do not. Fails pre-fix (all
    `pdca-integration/main`).
  - `template/tests/test_integrate.py::test_integration_branch_name_is_scoped_to_the_batch`
    — same batch ⇒ same name, different batch ⇒ different name, still distinct across
    bases (including a base literally named `main-r<key>`), valid per
    `git check-ref-format`.
  - Six `StackModeFlow` cases in `template/tests/test_flow_slice.py` that pinned
    `pdca-integration/main` now compute the run's branch; their assertions are unchanged.
  - Red/green through `engine/scripts/run-verify.sh` (production hunks reverted → red,
    restored → green). Full offline suite: `Ran 2325 tests, OK (skipped=2)`; docs lint
    and render check pass.

Fixes #591
