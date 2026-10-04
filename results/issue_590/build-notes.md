# Build notes — issue 590 / flow-dep-on-seed-child-refused (iteration 2)

Target: `eduralph/pdca-harness` @ `main` (`c67a14d`), worktree `pdca-harness.pdca-wt-l1`.
Line numbers are in the patched tree unless marked "base".

## What this iteration does

The sign-off kept the production change and asked for three more tests. So:

- **Production code: unchanged from iteration 1, byte for byte.** I applied
  `iteration-v1/patch.diff` to a clean `c67a14d` worktree and checked that the `flow.py` and
  `waves.py` hunks in the new `patch.diff` are identical to the old ones (`diff` of the two
  `template/src` sections is empty). For the record, the fix is:
  - `waves.check_dep_graph` takes `offered: frozenset[str] = frozenset()`
    (`template/src/pdca_harness/waves.py:65-66`). A `Depends on` / `Depends on (merged)`
    edge to an offered name is accepted and adds no edge (`waves.py:95-96`). A `Stacks on`
    edge to one falls through to the old check and is still refused.
    `compute_waves` passes the keyword through (`waves.py:172-173`, `:184`). With the
    default, both behave exactly as before.
  - `flow._offered_by_seeds` (`template/src/pdca_harness/flow.py:1743-1793`): a silent walk
    over `split.read_lineage` + `_lineage_children`, walking through children terminal on a
    split, keeping a child only if it has a brief and is not terminal.
  - Only the strict call in `_drive_and_act` passes `offered` (`flow.py:1887-1889`, base
    `flow.py:1830`). `_reschedule` (`flow.py:1267`), `partition_schedulable` and
    `pdca waves` are untouched.
- **Tests: three new methods appended to `AdoptRecovery`** in
  `template/tests/test_flow_adopt_recovery.py`, plus one small helper. All go through
  `cli._flow` with `--no-publish`, on a split made by the production `split.accept`.
  Nothing else in the file changed from iteration 1.

### The three new tests (carry-forward items, in order)

1. **Loop through an offered child** —
   `test_a_loop_through_an_offered_child_is_held_never_a_raise` (`:948`). 500 is split into
   601 and 602; 602's brief is edited by hand from `Depends on: 601` to
   `Depends on: 601, 810` (the new `_rebrief` helper, `:940`, which first asserts the old
   line is there so the edit cannot silently miss); 810 `Depends on: 602`. Pinned result of
   `pdca flow 500 810`: no traceback, no up-front refusal, `rc == 1`,
   `waves_driven == [["issue_601"]]`, 601 COMPLETE, 602 and 810 still PLANNED, and stderr
   has `flow: issue_602 held this run — dependency cycle` and the same for `issue_810`.
   - Why a hand edit: `split.accept` refuses a child whose `Depends on` names anything but a
     sibling label (`template/src/pdca_harness/split.py:358-368`), so the loop cannot come
     out of the proposal. Editing the child's brief is how an operator re-plans it, and the
     file already hand-edits lineage records the same way (`_record`, `:225`).
   - Why I pinned `rc == 1` (the sign-off did not list rc): 810 is an id the operator
     typed, and `_report_held`'s docstring says a held named id stays in the results map
     as PLANNED and the run fails (`flow.py:873-878`). Exit 0 here would tell automation
     the run succeeded while a typed id was not built, so that is worth pinning.
   - Why `waves_driven == [["issue_601"]]`: it shows the hold is limited to the loop. The
     rest of the request (601) still runs.
2. **`Stacks on` a seed child stays refused** —
   `test_stacks_on_an_offered_child_is_still_refused_up_front` (`:918`). Three subtests,
   each `pdca flow 500 810` on a fresh instance: `Stacks on: 602` alone;
   `Depends on: 601` + `Stacks on: 602` (the mixed case the sign-off asked for); and
   `Depends on: 602` + `Stacks on: 602` (one child in both fields). Each must give rc 2,
   the message `issue_810: declared dependency '602' is neither in this batch nor an
   existing COMPLETE bundle`, nothing driven, no passes, and 601/602/810 still PLANNED
   (reuses `_assert_refused_up_front`, `:729`).
   - In the mixed case the refusal names **602**, not 601. That is the point of the case:
     the `Depends on` edge to the offered 601 was accepted and the `Stacks on` edge to 602
     was refused. Before the fix the same input was refused on 601 (first dep in
     `declared_deps` order, `waves.py:48`), so this subtest is red without the fix.
3. **`Depends on (merged)` resolves like `Depends on`** —
   `test_depends_on_merged_on_an_offered_child_resolves_like_depends_on` (`:900`). 810
   `Depends on (merged): 602`. Result: rc 0,
   `waves_driven == [["issue_601"], ["issue_602"], ["issue_810"]]`, all three COMPLETE. The
   merge gate in `_runnable` (`flow.py:707-709`) applies only to a prerequisite outside the
   run's batch, and 602 is adopted into the batch, so it does not block 810.

## Red → green (project runner)

`PDCA_BUNDLE=…/results/issue_590 PDCA_WORKTREE=…/pdca-harness.pdca-wt-l1
PDCA_BRIEF_BASE=origin/main ./engine/scripts/run-verify.sh` (the configured C4 gate), run
from the pdca-pdca root:

- Green leg: `Ran 22 tests … OK`.
- Red leg (production hunks reverted, tests kept): `FAILED (failures=6)`:
  - the iteration-1 cases: the repro, the grandchild case, boundary (b);
  - the new loop test (fails on `assertNotIn(self._REFUSED, err)` — the old code refuses up
    front on `'602'`);
  - the new `Depends on (merged)` test (same refusal on `'602'`);
  - the mixed `Stacks on` subtest (the old code's refusal names `'601'`, not `'602'`).
- `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`.
- Afterwards the worktree diff equals `patch.diff` again (the script's restore trap ran).

Passing on both legs, as expected, because they pin the contract the fix must keep: the two
other `Stacks on` subtests, `test_without_the_seed_or_off_its_lineage_the_edge_is_still_refused`
and `test_a_child_not_offered_is_still_refused_up_front`.

Whole suite (`PDCA_WORKTREE=… ./engine/scripts/run-suite.sh`, the configured T3 runner):
root suite `Ran 24 tests … OK`; offline driver suite `Ran 2306 tests … OK (skipped=2)` —
three more than iteration 1's 2303, which are the three new methods. `PDCA-EVIDENCE: root
suite OK, driver suite OK`.

## Self-refutation

- **(a) Genuine red?** Yes. On the C4 red leg (production hunks reverted with
  `git apply -R`, tests kept) both new tests and the mixed `Stacks on` subtest fail, and the
  captured stderr shows the old up-front refusal (`issue_810: declared dependency '602' …`
  or `'601'` for the mixed case). The two `Stacks on` subtests that pass on both legs are
  guards, not red evidence.
- **(b) Production path?** Yes. Every case calls `cli._flow`, the operator's entry point.
  The split comes from the production `split.accept`; the parent is carried to COMPLETE by
  the production `flow._drive_wave`; the wave and pass spies call straight through to
  production code. The cycle hold comes from the real `_reschedule` →
  `waves.partition_schedulable` → `_report_held`. No stand-ins.
- **(c) Fixture includes the fault?** Yes. The seed really is terminal on `split` with its
  children PLANNED on disk (asserted inside `_strand_a_split`, `:252-265`). The loop is
  really in 602's brief (`_rebrief` asserts the line it edits was there), the `Stacks on`
  and `Depends on (merged)` fields are really in 810's brief, and the held-cycle lines on
  stderr show the loop was what stopped 602 and 810.

## Alternatives ruled out (this iteration)

- **Changing the production code to refuse the loop up front again** (for example, adding
  the offered children's own edges to the strict check). The sign-off asked to keep the
  production change and pin the hold as a deliberate change, and the brief says not to add
  offered names as a pseudo-batch with real edges.
- **Building the loop through the split proposal.** Not possible: `split.accept` validates
  that ordering fields name only sibling labels (`split.py:358-368`).
- **Giving 602 an independent body (`_SIBLING_TWO`) and appending `Depends on: 810`.** Also
  works, but it drops the 602 → 601 edge the other #590 tests use. Editing the one line keeps
  the fixture the same as the main repro, with 810 added to 602's list.

## Commit-readiness

The target has no formatter, linter config or active git hooks: no
`.pre-commit-config.yaml`, no ruff/black/flake8 settings, no `core.hooksPath`, and only
`*.sample` files in `.git/hooks`. CI runs docs checks, a render check and a linked-issue
check. Checked by hand: `git diff --check` is clean, all three files compile, and the
longest added line is 96 characters, the same as the longest line already in the test file.
DCO sign-off is publish's job.

## Housekeeping

I wrote no files outside the worktree and this bundle. Gate and suite output went to the
tool output only; the test fixtures create and remove their own temp dirs.
