# Build notes — issue 653 / carry-holds-when-branch-tip-is-not-the-judged-head

Target: `eduralph/pdca-harness` @ `main`, worktree base `b5f5c29`. Line numbers below are
in the patched worktree (`$PDCA_WORKTREE` = `pdca-harness.pdca-wt-l1`).

## The change

1. `template/src/pdca_harness/flow.py:860-864` (`_finished_head`): after every existing
   check passes, resolve the published branch ref the fold will merge (`ref[1]`, the
   `integrate._published_ref` value the carry already passes in as `ref`,
   `integrate.py:139-158`) in the carry's own fetched checkout (`repo` from
   `integrate.carry_view`, `integrate.py:185-193`). If it resolves and is not the judged PR
   head, return `(reason, "tip:<head12>")`. The reason names the branch, its tip (12 chars)
   and the judged head (12 chars). This takes the same `(reason, hint)` path as every other
   not-clean case (`flow.py:846-859`), so the carry holds the dependents and prints one
   line per id (`flow.py:956-968`) with no new control flow.
   - The branch does not resolve (`None`): unchanged. A merged PR whose branch was deleted is
     still judged by the merged head, and `integrate._gone_branch` handles the fold
     (brief Scope, out of scope).
   - The check comes last, after the MERGED/edge check, so the older reasons keep
     priority and their existing tests don't change.
2. `flow.py:873-874`: new `_CARRY_HINTS["tip"]`: "reset or delete {name}'s branch to {head}
   (the PR head that was judged), or open a PR for the commit(s) after it, then re-issue".
   This is the hint text the brief asked for.
3. `flow.py:960-962`: the `.format(...)` call splits `hint` on `:` so the judged head
   reaches the advice text; other hints carry no `:`, so `head=""` is passed and ignored.
   I chose this over widening `why` to a 3-tuple. The 3-tuple would touch every writer of
   `why` (the 5 sites at `flow.py:929, 932, 934, 947, 949`, plus `_finished_head`'s 6 returns) to add a third element.
   The string suffix touches one reader and one writer.
4. `flow.py:838-844`: docstring now states the tip rule.
5. `docs/07-crosscutting.md:688-691`: the user-facing "Only a clean prerequisite is
   carried" definition now includes "its branch is still at that PR head". It names the
   "Update branch" fail-closed case and says what to do. Without this the doc would no longer
   match the code. `lint_docs.py` and `render_site.py --check` both pass.

The rejected alternative (fold the judged head instead of the tip) was declined by the human
at Plan, so I did not try it.

## Tests (`template/tests/test_flow_resume_stack_prereqs.py`)

- Fixture: `self.heads` (`:54`) lets a test pin the `headRefOid` the `gh` stub reports
  (`:101-102`). It defaults to empty, so every existing test still gets the branch tip as
  before (criterion 3).
- `test_a_merged_prerequisite_pushed_to_after_the_merge_is_not_carried` (`:389`):
  criterion (1). P is MERGED via `_merge_pr`, the head is recorded, and `extra.txt` is
  pushed onto `fix/P`. The batch is `["P","D","U"]`.
- `test_an_open_prerequisite_whose_head_moved_since_the_read_is_not_carried` (`:398`):
  criterion (2). P is OPEN, the stub reports the commit before the tip.
- Shared check `_tip_held` (`:382`): D is never built and stays PLANNED. Exactly one stderr
  line names `issue_P` and `issue_D` and contains "not the PR head that was judged", both
  short SHAs, "reset", "delete" and "re-issue". No branch on origin outside `fix/*` contains
  the extra commit (`git for-each-ref --contains`, `:376-380`, helper `_lines_with`). U is built on the base.

## Runs

- C4 gate, run through the project's `engine/scripts/run-verify.sh` with `PDCA_BUNDLE` and
  `PDCA_WORKTREE` set: `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`. The
  red leg had both new tests fail with "issue_D unexpectedly found in seen … carried
  issue_P … onto pdca-integration/main-r7f802288d0f6". That is the defect itself.
- Green: `tests.test_flow_resume_stack_prereqs` ran 15 tests, OK. The full offline suite
  (`cd template && PYTHONPATH=src python3 -m unittest discover -s tests`) ran 2371 tests,
  OK (2 skipped). I ran it before the doc edit; the doc edit changes no code, and no test
  under `tests/` or `template/tests/` references `07-crosscutting`.
- Commit-readiness: the target has no pre-commit config, no `core.hooksPath` and no Python
  formatter. CI only runs the docs lint and render checks (both pass) and the render suites.
  Lines are kept to the file's existing width (≤ 92 cols).

## Refuting my own test

- **(a) Genuine red?** Yes. The C4 red leg reverts only the production hunks of
  `flow.py` and keeps the test. Both new tests then fail: D is built on a line the carry made
  from `fix/P`'s tip, which holds the extra commit.
- **(b) Production path?** Yes. The tests drive `flow._drive_and_act` →
  `_carry_finished` → `_finished_head` → the real `integrate.carry_view` / `integrate.fold`
  against real git (bare origin + checkout). Only `gh`, the build leaf and the publish leaf
  are stubbed, as in the existing file.
- **(c) Fixture includes the fault?** Yes. The extra commit really is pushed to `fix/P` on
  the bare origin, and the carry really fetches it. The `gh` stub reports the earlier head,
  which is exactly the stale or merged-head answer the defect is about.

## Known residual (out of scope, per brief)

A push that lands after the carry's own fetch and before the fold's re-fetch
(`integrate.py:623`, `:468`) is still merged. Closing it would mean passing the expected
head into the fold.
