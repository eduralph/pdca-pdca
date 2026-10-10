# Build notes — issue 652 (covers #624)

Target: `eduralph/pdca-harness` `main` @ `b5f5c29`, worktree `pdca-harness.pdca-wt-l1`.
Line numbers below are on the patched tree.

## What changed

- `template/src/pdca_harness/flow.py:866-867` — new `_CARRY_HINTS["built_on"]` entry, the
  cascade hint text from the brief's Scope: "{name} was built on {cause}, which is not
  carried (see its line): get {cause} carried, or re-drive {name} on a base without it,
  then re-issue".
- `flow.py:871-897` — new `_cascade_not_clean(cfg, ids, why)`. It reads each finished id's
  plain `Depends on` (`brief.depends_on`, the same reader the carry uses for drive-set
  dependents at `flow.py:926-931`), keeps only edges to other finished ids of the same
  target, and loops to a fixed point: any id that names an id already in `why` is added to
  `why` with reason "it was built on {cause} (its `Depends on`), which is not carried" and
  hint `built_on`. It returns name → direct cause.
- `flow.py:959-961` — `_carry_finished` calls it after the state judgment
  (`_finished_head`) and the foreign-line check, and **before** `clean = [...]` and the
  fold. So a cascaded id never reaches `_fold_lines` and its branch (which holds the
  not-clean id's commits) is never merged onto the line.
- `flow.py:987-989` — the held-line `.format(...)` call gets `cause=`. The other hints
  ignore the extra keyword (`str.format` allows unused keywords).
- `flow.py:913-917` — `_carry_finished` docstring: the "only its plain `Depends on`
  dependents wait" sentence now says the finished ids built on a not-clean id are held
  too. The rest of the paragraph was only rewrapped to keep lines ≤ 100 chars.
- `docs/07-crosscutting.md:689-695` — the second sentence of the carry paragraph, updated
  the same way.

The held line for a cascaded id keeps the existing shape (`flow.py:983-993`: one line
per finished id, naming its drive-set dependents). Holding those dependents needs no new
code: the cascaded id is in `held`, and `_runnable` already holds plain `Depends on`
dependents of a held id (`flow.py:751-754`).

## Why this shape

The brief's invariant is about the dependency edges between finished ids, so a check on
one id at a time (`_finished_head`) can't satisfy it. The cascade runs on the `why` map
right where the carry decides what is clean, before the fold, which is the smallest
place that covers all three clauses. The new function is about 27 lines, plus 3 call-site
lines.

Ruled out:
- **Pruning inside `integrate.fold`** (stop merging a later branch if an earlier one was
  skipped). That is the fold-time residual the brief puts out of scope, and it would touch
  `integrate.py:433-475`, shared by every in-run fold, not only the carry.
- **Checking commit ancestry** (is `fix/P`'s tip an ancestor of `fix/Q`'s head) instead
  of brief edges. The brief defines "clean" over plain `Depends on` edges
  (Invariant section), and ancestry would also need a `git` call per pair. I kept to the
  edge rule.
- **Naming the root cause instead of the direct one** in a chain. The held line names the
  direct cause (R's line says `issue_Q`, Q's line says `issue_P`), so following the lines
  leads to the root. This matches "see its line" in the hint.

Scope kept: only edges between the finished ids of the same target (`ids`) are followed.
A prerequisite that is not a requested id, `Stacks on` and `Depends on (merged)` edges, and
fold-time failures are not cascaded, as the brief says.

One cosmetic point for the human: `issue_P`'s own held line still says "holding no
bundle this run" when only finished ids (not drive-set bundles) depend on it. The cascaded
ids' lines name P as the cause, so the information is there, but P's line does not list
them. I left P's line alone to keep the change small and the existing line format.

## Tests

`template/tests/test_flow_resume_stack_prereqs.py`, appended to `ResumeStackPrereqs`:
- `_finished_on` helper (`:373-386`): publishes `iid` cut from `origin/fix/<prereq>`, then
  rewrites its brief with `Depends on: <prereq>` (after `_publish`, which rewrites the
  brief), accepts it, and asserts the prereq's tip is an ancestor of its branch.
- `test_a_finished_id_built_on_a_closed_one_is_not_carried` (`:393`) — clause 1: D held,
  one line naming `issue_Q`, `issue_D`, `issue_P` and "built on"; asserts it is NOT the
  `open` hint ("get issue_Q's PR open") and IS the new hint; P's line says CLOSED; Q is
  not carried; no commit of P or Q on the line; U is built on the base and COMPLETE.
- `test_a_hold_cascades_through_a_dependent_finished_before_the_run` (`:409`) — clause 2
  (#624): U CLOSED ← D ← E; E held and named on one line with `issue_D`; U not on the line.
- `test_not_clean_spreads_through_a_chain_of_finished_ids` (`:418`) — clause 3: P ← Q ← R
  ← D; D held on R's line, which names `issue_Q`; Q's line names `issue_P`; none of P, Q, R
  on the line.
- Clause 4: the 13 existing tests in the file pass unchanged.

## Runs (project runner: `engine/scripts/run-verify.sh`, the C4 gate)

Run with `PDCA_BUNDLE=results/issue_652 PDCA_WORKTREE=<worktree>`:

```
== C4 green leg: ... Ran 16 tests ... OK
== C4 red leg: ...
FAIL: test_a_finished_id_built_on_a_closed_one_is_not_carried
FAIL: test_a_hold_cascades_through_a_dependent_finished_before_the_run
FAIL: test_not_clean_spreads_through_a_chain_of_finished_ids
Ran 16 tests ... FAILED (failures=3)
PDCA-EVIDENCE: C4 PASS — red without the fix, green with it
```

Pre-fix failure output (red leg) matches the brief's RED exactly: e.g. clause 2,
"`issue_E` unexpectedly found in seen … flow: carried issue_D … onto
pdca-integration/main-r…", and clause 3, "carried issue_Q, issue_R".

Full offline suite (`cd template && PYTHONPATH=src python3 -m unittest discover -s
tests`, the CONTRIBUTING.md command, run under `timeout`): `Ran 2372 tests … OK
(skipped=2)`.

## Refuting my own test

- **(a) Genuine red?** Yes. The C4 red leg reverts the production hunks of `flow.py`
  (and the docs) and keeps the test: all three new tests fail on assertions (not import
  errors: the test imports only modules, and `_finished_on` is a test helper). In clauses
  1 and 3 D is in `self.seen`; in clause 2 E is in `self.seen`, built on a line the
  carry pushed holding the closed bundle's work.
- **(b) Production path?** Yes. The tests call the real `flow._drive_and_act`, which
  calls the real `_carry_finished`, `_cascade_not_clean`, `_finished_head`,
  `integrate.fold` and `_runnable` against real git (bare origin + checkout). Only the
  build/sign-off leaf (`_drive_wave`), `_publish_bundle`, `draft_texts` and `gh` are
  stubbed, as in the existing tests of this file.
- **(c) Fixture includes the fault?** Yes. P (or U) has a real CLOSED PR state from the
  `gh` stub, and Q (or D) has a real branch cut from `origin/fix/P`; the helper asserts
  P's commit is an ancestor of Q's branch, so the commits that must not reach the line
  are really there to leak.

## Commit-readiness

The target has no formatter config, no pre-commit config, and no installed git hooks
(checked: repo root, `template/`, `.git/hooks`). Its CI runs `lint_docs.py` (ran: `OK`)
and the render/doc checks. Commits need a DCO `Signed-off-by` trailer, which publish adds.
I kept added lines ≤ 100 chars to match the file's style (checked over the diff).
