# Build notes — issue 411 / merge-mode-wrong-base-fail-closed

Target: `eduralph/pdca-harness` @ `main` (worktree `/home/eddie/pdca/pdca-harness.pdca-wt-l0`,
base `9d503d1` == `origin/main`). All `path:line` below are **post-patch** lines in that
worktree unless marked "base".

## What changed

Three files, 175 added lines, no deletions.

1. **`template/src/pdca_harness/publish.py:258-272`** — the guard, inside `publish.publish`,
   placed immediately after `pr_base` is computed (`:257`) and before `steps` is built
   (`:273`). Under `cfg.wave_mode == "merge"` it calls `_merge_base_refusal(...)`; a non-empty
   message is printed to stderr and `publish` returns `1`.
2. **`template/src/pdca_harness/publish.py:648-694`** — `_merge_base_refusal` (the two routes,
   with the message naming both branches) and `_batch_branch_producer` (the offline scan of
   sibling bundles' `publish.json`, reusing the existing `_publish_record` accessor at
   `:606-614`).
3. **`docs/07-crosscutting.md:353-363`** — user-facing driver documentation, appended to
   §Waves in execution right under the `"merge"` bullet (the section the brief's Ordering note
   assigns to this bundle; #420 owns `:300-332` / `:359-380` and `template/pdca.toml.jinja`,
   which I deliberately did **not** touch to keep the declared conflict to the one file the
   scheduler already separated).
4. **`template/tests/test_publish_slice.py:975-1072`** — a new `MergeModeBaseGuard` TestCase
   appended to the existing suite (4 tests).

### Why the guard sits where it does

The brief says "after the target is resolved, before any branch/push/PR work". Line 258 is the
first point where the **actual** PR base (`pr_base`) exists as a single value, and nothing
side-effecting has run yet: `branch`/`repo`/`git` above it (`:235-239` base) are pure name
computation, `steps` is only *built* at `:273` and only *executed* at `:354`, and the dry-run
plan is printed at `:313`. So a refusal here pushes nothing, opens no PR and writes no
`publish.json` — the tests assert all three.

Route 1 is `pr_base != base`: `pr_base` diverges from the resolved target base only via
`_stack_base_branch` (base `publish.py:615-630`) — the run-scoped integration marker or the
legacy `Stacks on:` parent's fix branch. Both are branches this run produced.

Route 2 is `pr_base == base` **and** some other bundle in `cfg.bundle_root` recorded that
branch in its `publish.json`. The brief is explicit that route 1's comparison is blind here,
because the brief's target base genuinely *is* the predecessor's branch.

The bundle's own base is **not** re-parsed: `base` comes from `_resolve_target` at
`publish.py:174` (base `:531-544`) and is passed into the helper. That is the #235/#262/#387
one-parse rule.

## Alternatives considered, with the cost

- **Guard at merge time (`merge.py::_merge_one`, compare `pr.baseRefName`).** Not re-litigated:
  the brief records this as the human's call at Plan (publish is interactive, the wave merge is
  unattended; refusing to *create* the wrong-based PR removes the cause instead of guarding the
  symptom). Also `merge.py` is explicitly out of scope.
- **A separate earlier pre-check (before `_ensure_texts`/T4) that recomputes the PR base.**
  Rejected on a concrete cost: it duplicates three lines that already exist —
  `base_remote = cfg.base_remote` (`:240`), `own_repo = base_remote == "origin"` (`:256`),
  `pr_base = stack_branch if (stack_branch and own_repo) else base` (`:257`) — i.e. a second
  derivation of the very value the guard is about. That is the same drift hazard #235/#262/#387
  closed for the base parse. The only thing gained is skipping one stub-leaf artifact write on
  a bundle that is about to be refused; the artifacts are idempotent and not pushed.
  (Hoisting those three lines + their 15-line explanatory comment above the guard was the other
  option: same behaviour, but it moves a load-bearing comment block 20 lines away from the
  `checkout_base`/fork reasoning it explains, for zero behavioural gain.)
- **Detecting route 2 by regenerating each batch bundle's branch name** from
  `cfg.fix_branch_pattern` / `feature_branch_pattern` instead of reading their `publish.json`.
  Rejected: it re-implements `_branch_name` (`publish.py:551-559` base — pattern choice via the
  brief's Kind + `_slugify`), ~10 duplicated lines, and it is both over- and under-inclusive —
  it would flag any base that merely *looks* like the pattern, and would miss a branch published
  under an older pattern. `publish.json` (`:381-393`; base `:364-377`) is the record the brief
  points at, and it is exactly the data merge mode itself consumes.
- **Refusing the `Onto branch` (#54) path too** (`publish.py:219-222`). Not done: `Onto branch`
  names an existing, human-declared PR head — not a branch this run produced — and it returns
  through `_publish_stacked` before the guard. The brief lists it as a neighbour that must keep
  working untouched.

### Fail-closed choices worth a reviewer's eye

- `_batch_branch_producer` treats a sibling record with **no `repo` field** as this repo's
  (`publish.py:692-693`). A false refusal is recoverable (fix the brief, re-publish); a silent
  wrong merge is not.
- Only the **active** `results/issue_*` bundles are scanned, not `results/completed/`: "this
  batch" is the run's own product. A branch produced by an *earlier* run is the known limitation
  the brief already accepts (a PR published under a previous run never passes through publish
  again). Related and equally out of scope: route 2 is invisible if the producing bundle has not
  published yet — wave ordering publishes predecessors first, which is the reported scenario.

## Red → green, through the project's runner

Ran the configured C4 gate (`pdca.toml` `[[gates.checks]] id = "C4-verify"` →
`./engine/scripts/run-verify.sh`), which runs the green leg, reverts the production hunks
(keeping the tests) and runs the red leg:

```
== C4 green leg …  Ran 62 tests … OK
== C4 red leg …
FAIL: test_merge_mode_refuses_a_pr_based_on_a_stacked_prereq_branch … AssertionError: 0 != 1
FAIL: test_merge_mode_refuses_a_target_base_another_bundle_produced … AssertionError: 0 != 1
Ran 62 tests … FAILED (failures=2)
C4 PASS: red without the fix, green with it
```

Also ran the advisory whole-suite gate `./engine/scripts/run-suite.sh` (T3):
`== T3: root suite OK, driver suite OK` — including `test_flow_slice`'s merge-mode wave test
(`template/tests/test_flow_slice.py:1196-1199` base), which is unaffected.

Commit-hook readiness: the target has no formatter/pre-commit config (no `.pre-commit-config.yaml`,
no `pyproject.toml`/`setup.cfg` lint settings; `CONTRIBUTING.md:26` names the offline suite as the
discipline). Its PR-time CI includes `docs-check` — ran both of its steps against the patched tree:
`python3 docs/publishing/tools/lint_docs.py` → `lint_docs: OK`, and
`python3 docs/publishing/tools/render_site.py --check` → `render_site: link audit OK`. No added line
exceeds 95 columns (the file's prevailing width).

## Forced self-refutation

- **(a) Genuine red?** **Yes.** The C4 red leg reverted `publish.py` (tests kept) and both new
  refusal tests failed on `self.assertEqual(rc, 1)` → `AssertionError: 0 != 1` — a failing
  assertion on the return code of the existing public `publish.publish`, not an import or
  attribute error (the #434 hazard the brief calls out: `MergeModeBaseGuard` imports nothing
  new; it uses `publish`, `json`, `io`, already imported at `test_publish_slice.py:11-24`).
- **(b) Production path?** **Yes.** Every test calls `publish.publish(self.cfg, id,
  dry_run=True, …)` — the same production entry point the driver and `pdca publish` call — and
  the guard lives inside that function (`publish.py:258-272`). No copy, no mock of the guard;
  the only stubs are the pre-existing offline ones (leaf `mode="stub"`, no configured gates, a
  tmp `bundle_root`), i.e. the fixtures the rest of the file already uses.
- **(c) Fixture includes the fault?** **Yes.** Route 1's fixture *contains* the failing element:
  a real sibling bundle `issue_PARENT` with a `publish.json` recording `fix/PARENT-my-fix`
  (`test_publish_slice.py:1013`) plus a brief with `- **Stacks on:** PARENT`, so
  `_stack_base_branch` really returns that branch and `pr_base` really becomes it. Route 2's
  fixture contains a real `issue_PRED` record whose `branch` **is** the string the brief's
  `Repo + branch target` names (`:1029-1035`) — the wrong base is present, not curated out.
  And the guard is proved not to be a blanket stop: `:1041` publishes an ordinary bundle in
  merge mode with an unrelated sibling branch recorded (rc 0, `--base main`), and `:1051`
  re-runs *both* refused shapes under the default `"stack"` mode and asserts they still
  publish (`--base fix/PARENT-my-fix`, `--base fix/PRED-groundwork`).

## STOP discipline

Nothing pushed, no branch created, no PR opened.
