# Build notes — issue 593 / stack-mode-append-only-fold-real-base-prs

Target: `eduralph/pdca-harness @ main` (worktree base `24c7f83`). Line numbers below are in
the patched tree (`$PDCA_WORKTREE`) unless marked "base".

## What changed, by success-criterion item

**(i) Every wave PR targets the real base** — `template/src/pdca_harness/publish.py`
- `:258` still computes the chained base exactly as before, and the merge-mode guard
  `:270` (`_merge_base_refusal`, #411) still judges that value, so merge mode is unchanged.
- `:277-278` new: if the bundle has a recorded `stack-base` (`_read_stack_base`), `pr_base = base`.
  The branch is still cut from `origin/<integration branch>` (`checkout_base`, unchanged).
  `publish.json` records `base: pr_base` (unchanged line), so it now records `main`.
- A legacy `Stacks on:` parent with no stack-base keeps `--base <parent>` on own-repo
  (`tests/test_publish_slice.py:478-484`, `:1142-1160` pass unchanged). When both are
  present the stack-base wins, because `_stack_base_branch` already returns the stack-base
  first (`publish.py:647-649`), and `:277` retargets on the stack-base.
- Dry-run label `:318-319`: a stacked PR that targets the base reads "cumulative diff vs base
  until its predecessors merge" (the fork test only asserts the `cumulative diff` substring,
  `test_publish_slice.py:476`; own-repo legacy still prints plain "stacked draft PR").
- Comments `:243-256` and docstrings of `write_stack_base` / `clear_stack_base` /
  `_stack_base_branch` (`:606-646`) updated.

**(ii)/(iii)/(iv) The fold** — `template/src/pdca_harness/integrate.py`
- `fold` gains keyword-only `folded_this_run: Collection[tuple[str, str]] | None = None`
  (`:172-175`). `continuing` (`:251`) is True/False from it, or None ⇒ decided after fetch by
  whether `origin/<integration branch>` exists (`:285-286`).
- Up-front check `:230-235`: every accepted patched, targeted bundle must have a
  `publish.json` `branch` (`_published_branch`, `:85-99`, which reads it via
  `publish._publish_record` the way `_stack_base_branch` reads a parent's). Missing ⇒
  `IntegrationError` naming the bundle + `pdca publish <id>`, before any git step.
- Start (`:291-293`): `checkout -B <line> origin/<line>` when continuing, else
  `<base_remote>/<base>`. A target listed in `folded_this_run` whose line is gone from origin
  raises (`:287-290`) — fail-closed, see "Calls I made" below.
- Per bundle (`:294-315`): `origin/<branch>` must resolve (`_resolves`, `:80-82`); if not,
  `merged.is_merged(cfg, id)` ⇒ skip, else `IntegrationError` naming bundle + branch. Already
  an ancestor of HEAD ⇒ skip (not merged twice). Otherwise
  `git merge --ff --no-edit --signoff -m "pdca-integrate: merge <branch> (<bundle>)"`; on
  failure `merge --abort` and the existing overlap-shaped `IntegrationError`.
- Push (`:316-329`): continuing ⇒ plain `git push origin <line>` (no force; a refused
  non-fast-forward is an `IntegrationError`). Fresh start ⇒ `git push --force` (replaces a
  previous run's line); if that is refused the message says to delete the old branch or allow
  force-push on `pdca-integration/*`.
- `_prepare_worktree` `:338-344`: the origin fetch is now `fetch --prune origin`, so a PR
  branch deleted on origin stops resolving. Without the prune a stale tracking ref still
  resolves and "gone from origin" would never fire. The new test binds this (below).
- Dry-run `:252-267` prints the new steps (start ref, `git merge --ff --signoff origin/<branch>`
  per bundle, push with/without `--force`). It uses the recorded branch or, when the stubbed
  publisher recorded none, the name publish would give it (`_expected_branch`, `:102-108`).
  Still no subprocess (`test_integrate.py` `test_dry_run_shells_nothing` asserts it).
- Module docstring `:1-27` and `IntegrationError` docstring rewritten.

**flow call site** — `template/src/pdca_harness/flow.py:1844-1848`: passes
`folded_this_run=set(integ)`. `integ` is the existing per-run map (`:1677`), reassigned from
`folded` at `:1854`, so the run's first fold passes `set()`.

**(vi) Text** — `cli.py:1058-1061` comment only (behaviour unchanged: `mode` stays
`stacked-pr`, so `↑main` still shows). Docs: `template/PCDA/quality-cycle/09-parallel-lanes.md:57,69`,
`template/PCDA/quality-cycle/08-glossary.md:290-293`, `docs/07-crosscutting.md:642-654`,
`docs/05-check.md:813-819`, `template/pdca.toml.jinja:115-120` and `:177-178`.

**Tests**
- New: `template/tests/test_integrate_stack_bases.py` (9 cases; copy in the bundle dir).
- `template/tests/test_integrate.py`: `FoldGit._bundle` now publishes a real branch on origin
  and writes `publish.json` (the new contract). The DCO test now folds two siblings so the
  fold makes a merge commit, and asserts that commit has 2 parents and the sign-off (#405 intent).
  The dry-run assertions are updated to the new printed steps.
- `template/tests/test_flow_slice.py:1124` and `template/tests/test_flow_adopt_split.py:378`:
  these spies had a closed signature `(cfg, accepted, *, dry_run, locks)` and would `TypeError`
  on the new keyword. They now take `**kw` and forward it. The flow-slice spy also asserts the
  run's first fold gets `folded_this_run == set()` (pins the call site).

## Calls I made (not dictated by the brief)

1. **Retarget after the merge-mode guard, not before.** Retargeting before it would make a
   stale stack-base in merge mode pass route 1 of `_merge_base_refusal` (`pr_base == base`), so
   the PR would be cut from the integration line and then merged into main by the driver: a
   change to merge mode. Doing it after keeps the guard's inputs byte-identical. Cost: 2 lines
   (`publish.py:277-278`) vs. ~4 lines plus a changed refusal message for the "pass a
   different value to the guard" variant.
2. **`--ff`, not `--no-ff`.** With `--no-ff` every fold step makes a merge commit even when the
   branch was cut from the tip, and those commits stay in every dependent's PR commit list
   after the predecessor merges. Concretely, for an A → B → C chain, C's PR would carry 2 extra
   fold merge commits forever. With `--ff` a single chain needs no fold commits at all, and only
   same-wave siblings produce a (signed-off) merge. `--ff` is explicit so a user's
   `merge.ff = only/false` config can't change it.
3. **A target listed in `folded_this_run` whose line is gone from origin raises** instead of
   restarting silently. Restarting would be safe for the invariant, but it is an unexpected
   state mid-run (someone deleted it, or #591's concurrent run). Fail-closed matches the module.
4. **The unpublished-bundle check runs for all targets before any git step**, so a
   multi-target fold can't push target 1 and then stop on target 2.

## Known limits — for the human at sign-off

- **Displayed diff with same-wave siblings.** When two wave-0 siblings A and C are merged
  together on the line (merge commit M) and wave-1 B is cut from M, then after A and C both
  merge into main, `main...B` has **two** equally good merge-bases (A and C). git picks one,
  so B's three-dot diff can still show one sibling's file. Reproduced in a scratch repo:
  `git merge-base --all main B` → `A`, `C`; `git diff --stat main...B` →
  `b.txt | 1 +`, `c.txt | 1 +` with "multiple merge bases" warning. The **merge** of B is
  still clean, and a single chain shrinks exactly. The brief's wording ("then shrinks to its
  own") is used in the docs as dictated; it is exact for chains, not for multi-sibling waves.
  Decide whether the docs need a caveat. I did not add one to the vendored spec unasked.
- **`Onto branch` (#54) bundles on a non-origin remote.** Their `publish.json` `branch` lives on
  `<remote>`, but the fold looks for `origin/<branch>` (as the brief specifies). Such a bundle
  in a multi-wave batch now raises "gone from origin" (unless it reads as merged) instead of
  being re-applied from `patch.diff`. Fail-closed and rare. Supporting it would mean reading
  `<remote>` from `publish.json` `base` and fetching it (about 5 lines). Not done: out of the
  brief's decided mechanism.
- **The run's first fold force-pushes** (brief-decided). On an origin that refuses
  non-fast-forwards on `pdca-integration/*` with an old line present, the first fold raises
  with the remedy in the message (`integrate.py:325-329`) and in `09-parallel-lanes.md:69` /
  `docs/07-crosscutting.md:649-650`.
- Error texts say `pdca publish <id>`, like the existing flow messages (`flow.py:1819`). An
  instance with a different CLI name sees the generic name.
- Vendored spec edits (`08-glossary.md`, `09-parallel-lanes.md`) are NEEDS-HUMAN at Check by
  this project's rule (INTEGRATION §4), as the brief's notes say.

## Test design notes

- The test imports only modules (`integrate, merged, publish, signoff`, config), never a symbol
  the fix adds. Only `test_a_new_runs_first_fold_restarts_from_the_base` passes the new keyword;
  on the red leg it errors with `TypeError`, which the brief accepts.
- `_fold` in the test gives each fold its own `GIT_AUTHOR_DATE`/`GIT_COMMITTER_DATE` (one hour
  apart). Without it, on the base code two folds inside one wall-clock second wrote
  byte-identical `pdca-integrate:` commits, so the "rewritten tip" was invisible and the
  no-force push was a fast-forward by accident. In a real run a whole wave of Do/Check lies
  between folds. My first unpatched run showed exactly this: `test_later_folds_push_without_force`
  went red on the `b_sha` check instead of the refused push. After the change it goes red
  for the intended reason.
- The "gone from origin" case deletes the branch **inside the bare origin**
  (`git -C origin.git branch -D`), leaving the primary's `origin/fix/A` tracking ref stale, so
  only the `--prune` fetch makes it stop resolving.

## Runs (all via the project's own commands, bounded with `timeout`)

- Unpatched tree, `cd template && PYTHONPATH=src python3 -m unittest tests.test_integrate_stack_bases`
  (the invocation `engine/scripts/run-verify.sh` uses): `Ran 9 tests … FAILED (failures=7,
  errors=1)`. The reds: "the fold was refused: could not push pdca-integration/main to origin"
  (no-force origin), "the second fold rewrote the first fold's tip", "A's PR commit is not in
  the line", "IntegrationError not raised" ×2, `--base main` not found ×2 (prints
  `--base pdca-integration/main`). The 1 error is the `TypeError` case above.
- Patched: same module `Ran 9 tests … OK`.
- C4 gate, `PDCA_BUNDLE=… PDCA_WORKTREE=… ./engine/scripts/run-verify.sh` from the instance
  root: green leg 29/98/14/9 OK; red leg `test_flow_slice` 1 failure, `test_integrate` 2
  failures + 1 error, `test_integrate_stack_bases` 7 failures + 1 error, no load failure →
  `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`. The script restored the tree;
  `git diff` matched `patch.diff` byte for byte afterwards.
- Full offline driver suite (`cd template && PYTHONPATH=src python3 -m unittest discover -s tests`):
  `Ran 2224 tests … OK (skipped=2)`.
- Root suite (`python3 -m tests.run_root_suite`, instance venv with copier):
  `root suite OK: 24 executed, 0 skipped`. Its first run errored on **my scratch folder**, not
  the patch: copier mistook the nested experiment repo `.xb-Wdn0/r` for a submodule. I renamed
  that repo's `.git` to `dotgit` (no deletion) and the re-run passed.
- Docs: `lint_docs.py` OK; `render_site.py --check` "link audit OK".
- No formatter, linter config or commit hooks exist in the target (no `.pre-commit-config.yaml`,
  no `[tool.ruff]`/`[tool.black]`, no `core.hooksPath`); CONTRIBUTING requires only DCO
  sign-off, which publish adds (`commit -s`). New code lines are ≤ 101 columns, in line with
  the files (publish.py already had 104).

## Scratch left in the worktree

`.xb-Wdn0/` (untracked, not in `patch.diff`): the merge-base experiment repo (its `.git`
renamed `dotgit`), `c4.log`, `root.log`, and the rendered `site/`. Left for the harness to
reclaim, per the no-cleanup rule.

## Refute-your-own-test

- **(a) Genuine red? Yes.** With the production hunks reverted (C4 red leg, and separately on
  the untouched base tree) the named test fails 7 + errors 1, for the reasons listed above. The
  within-run test calls `fold` without the new keyword, so its red is the refused unforced push
  and the rewritten tip, not a `TypeError`.
- **(b) Production path? Yes.** The tests call `integrate.fold` and `publish.publish(dry_run=True)`
  themselves: real `git` subprocesses against a real bare `origin` and primary checkout, the
  real `_prepare_worktree` / lock / merge / push code. The only mock is
  `merged.is_merged`, because it calls `gh` (network). The decision that branches on its answer
  is production code.
- **(c) Fixture includes the fault? Yes.** The no-force origin is real
  (`receive.denyNonFastForwards true` set before the second fold). The second fold folds a
  wave-1 branch cut from the first fold's pushed tip, which is the exact middle-wave shape from
  the issue. The predecessor's PR commit is a real pushed commit whose SHA is checked. The
  unpublished bundle has a patch and no `publish.json`. The deleted branch leaves a stale
  tracking ref. The publish case carries a real `stack-base` stamp, and in one case also a
  `Stacks on:` parent with a published branch.

No external dependency beyond the brief's (git + stdlib Python). No NEEDS-HUMAN external
dependency to declare.
