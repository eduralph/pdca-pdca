# Build notes — issue 481 / split-parent-keeps-a-plan-artifact (attempt 2)

Target: `eduralph/pdca-harness @ main`, base `4050da290242ac1c797c93d2bce997a00263ad47`
(`origin/main`, the worktree HEAD). "main:" citations are that commit; "patched:" citations
are the worktree with `patch.diff` applied. Files touched: `template/src/pdca_harness/split.py`,
`template/src/pdca_harness/state.py`, `template/tests/test_split.py` — the three the brief's
Ordering note allows, nothing else.

## What changed

### 1. `state.state()` asks "past Do?" before "is there a brief?"

main: `state.py:304-307` returned `RESOLVED`/`UNPLANNED` for any bundle without `brief.md`,
before the close marker or `patch.diff` were looked at (`:310`).

patched: `state.py:313-317` — the briefless check moved inside the pre-Do branch. A bundle
carrying `patch.diff` or the close marker now always goes down the same ladder a briefed one
does (`BUILT` → `CHECKED` → `AWAITING_SIGNOFF` → outcome, `state.py:329-339`). Net: 4 lines
moved, comment added. The only shape whose answer changes is "no brief + a Do artifact": it
was `UNPLANNED` (never `RESOLVED` — `is_resolved` already refused it, because the marker and
`patch.diff` are in `DOWNSTREAM_OF_BRIEF`, `state.py:292`), and is now what its briefed twin
derives. Both Do artifacts, not just the marker, because the brief's Invariant names both and
`state.py:310` (main) already treats them as one condition.

### 2. `split.accept` gives a briefless parent a Plan artifact

- patched `split.py:777-821` `_parent_plan(parent, cfg)`: returns `None` when the parent has
  its own `brief.md` (then nothing below ever opens it — criterion (f)). Otherwise it finds the
  brief the latest iterate-to-Plan archived (`_archived_brief`, `:761-774`: highest-numbered
  `iteration-v<N>/brief.md`, compared as a number), holds it to `handoff.check_planner(archive,
  cfg, dependencies=False)` — the same Plan exit contract criterion (b) names — and returns
  `(relative path, Slug, Repo + branch target)`. No archive, an unreadable one, or one that
  fails the contract → `SplitError`, before any write.
- patched `split.py:824-869` `_field` + `_split_parent_brief`: renders the new brief. Slug and
  Repo + branch target are copied from the archive through `brief.whole_field` and re-rendered
  so `whole_field` reads the same value back (continuation lines re-indented). Defect / Success
  criterion / Scope describe the split and name every child bundle; `External dependencies:
  none` (the parent builds nothing, so `check_planner`'s dependency clause is empty);
  `Disposition hint: split` only feeds SUMMARY §2 (routing reads the marker,
  `driver.py:235-242`; `split` is deliberately not a close class, `config.py:32-36`). No Test
  file / Depends on / Conflicts with: a `Depends on` on a parent that only goes to sign-off
  would just hold it.
- patched `split.py:919-926`: the text is built in accept's pre-write phase, next to the
  lineage snapshot (main `split.py:777-797`), so every read and every refusal happens before
  staging.
- patched `split.py:991-994`: the write, the LAST one before the marker (main order was
  archive → lineage → breadcrumb → marker, `split.py:835-862`). The parent can only turn
  terminal with the brief already on disk.
- patched `split.py:1010-1025`: rollback. When this run set out to write a brief, the failure
  path removes `brief.md` unconditionally, after the marker's own cleanup (main `:873-876`).
  A removal that fails is named on stderr, the `_restore_lineage` discipline (`:679-696`).
- patched `split.py:322-325`: `preflight` asks `_parent_plan` too (see "a gap I found" below).

## Iteration-1 carry-forward — what was rejected and what changed

1. **Check P2 (C3 FAIL): a torn parent-brief write escaped rollback.** Attempt 1 set
   `wrote_parent_brief = True` only after `write_text` returned, so a write that created the
   file, landed part of it and raised (ENOSPC) left the torn file; the retry then saw a
   `brief.md`, kept it as the parent's own, and finished with a brief `check_planner` rejects.
   Now the removal is keyed on `new_brief is not None`, decided before any write. The parent had
   no brief when the accept began, so anything at that path during the rollback is this run's —
   whole or torn. Test: `test_a_torn_brief_write_is_rolled_back_and_the_retry_completes`
   (patched `test_split.py:1984`) persists 40 characters, raises ENOSPC, asserts the file is
   gone, then runs the retry and asserts `check_planner == []`. Mutating the rollback back to
   attempt 1's "only if the write returned" makes exactly this test fail ("the torn brief
   survived the rollback").
2. **Advisory [impl]: the archive was judged by its Slug alone** (`is_placeholder`), so an
   archive with a placeholder Repo + branch target produced a terminal parent whose brief fails
   `check_planner`. Now the archive must pass `handoff.check_planner(..., dependencies=False)`.
   Tests: `test_an_archived_brief_with_an_unfilled_field_is_refused_before_any_write`
   (`:2037`) and the CLI test below. Mutating the check back to Slug-only fails both.
3. **Advisory (non-blocking): third copy of the `iteration-v<N>` regex.** Still a copy
   (patched `split.py:756-758`), named like `size_signal.py:70` and pointing at it. A shared
   helper would have to live in `size_signal.py` or `driver.py`, both outside this slice's
   files (the Ordering note promises no overlap). Left for a follow-up.
4. **Validation NEEDS-HUMAN: "every child reaches COMPLETE" as the parent's sign-off
   contract.** That wording was wrong: the parent's sign-off does not wait for its children,
   and flow only adopts the children once the parent is terminal (`flow.py:887-910`). The new
   Success criterion is what the parent's sign-off can actually confirm: the children exist,
   each with its own brief, and together they cover the archived original; each child is
   verified by its own cycle. Whether that is the contract you want is still your call.

### A gap I found that the review did not: attempt 1's refusal came after filing

`cli._split` runs `split.preflight` (main `cli.py:767-777`), then `split.file_children`, which
files real tracker issues (`cli.py:793-806`), and only then `split.accept` (`cli.py:812-836`).
`preflight`'s contract is "every reason acceptance would fail that does NOT depend on the ids"
(`split.py:294-301`). Attempt 1 added its "no archived brief" refusal to `accept` only, so a
`--accept` without `--ids` would have filed the children before refusing. `_parent_plan` needs
no ids, so both call it. Test: `test_the_cli_refuses_before_filing_a_single_tracker_issue`
(`:2058`) drives the real `cli._split` with `file_children` recorded; removing the preflight
call makes it fail with the filing call recorded.

## Rejected alternatives, with costs

- **Atomic write (temp file + `os.replace`) instead of unconditional removal.** Sketch: write
  `.brief.md.split-tmp`, `os.replace` it onto `brief.md`, and remove both paths in the except
  (+`import os`): about 6 more lines and a second artifact name. It does NOT remove the need
  for the unconditional removal, because a later write (the marker) can still fail after the
  replace. Its only extra benefit is SIGKILL mid-write leaving no torn `brief.md` — but a
  SIGKILL anywhere in that block already leaves child bundles on disk that need hand cleanup
  (pre-existing; `_rollback` only runs on exceptions). Not worth it.
- **A `wrote_brief = True` flag set just before the write.** Same behaviour as keying on
  `new_brief is not None` (the path cannot exist before the write), +2 lines and a variable.
- **Exclusive create (`open(..., "x")`).** Guards a concurrent writer between the pre-write
  check and the write. No other parent write in `accept` guards that (lineage, build-notes use
  plain `write_text`), and the rollback would then have to tell `FileExistsError` ("not ours")
  apart: about 5 lines for a race the single-process module does not otherwise consider.
- **Validate the generated text with `check_planner` (write it to a temp dir first).** About
  5 lines plus a `TemporaryDirectory`, and the refusal would then depend on a writable temp
  dir. Validating the source is read-only and gives the same verdict: the copied fields
  round-trip through `whole_field` (test (b) checks the real output with `check_planner`), and
  the generated fields are constant and filled.
- **Fill a missing target from the children's `Repo + branch target`.** About 10 lines
  (parse every child body, require one agreed value) and an inference no human made. Refusing
  costs the operator one hand-written `brief.md`, and happens in `preflight`, before anything
  irreversible.
- **Copy the proposal's "Why this slice is oversized" prose into the brief.** About 15-20
  lines (heading match, fence and comment skipping, placeholder check), plus neutralising
  field-shaped lines: a copied `- **Depends on:** child-2` line would be read by
  `brief.parse_fields` / `depends_on` (`brief.py:20-31`, `:196-202`) as the parent's own
  dependency. The brief points at `split-proposal.md` instead. The stub splitter's proposal
  has no such section anyway (`leaves.py:1841-1865`).
- **Refuse every briefless parent.** Ruled out by the brief's Scope: the iterated parent has
  to complete. Only a parent with nothing authored to rebuild from (no archive, or an archive
  failing the Plan exit contract) is refused.
- **A new state for "past Do, no brief", or making `assemble` tolerate a missing brief.** Both
  outside the three allowed files. The second also guards the symptom instead of restoring the
  Plan artifact.

## Findings for the human (not widened into this slice)

1. **The brief's self-test assumed `assemble` renders an empty §1 for a briefless bundle. It
   raises instead.** `assemble.assemble_summary` calls `brief.parse_fields(d / "brief.md")`
   (`assemble.py:270`), which is `read_text` → `FileNotFoundError`. Reproduced on main before
   the fix. Consequence for the (e) shape reached by some other route — in practice the stuck
   v0.56.0 bundles (`wyrd-pdca` issue_711 / issue_654): they now derive `BUILT`, the driver
   records the close gates and review note, and `assemble` raises. `flow._isolate`
   (`flow.py:51-70`) contains it per bundle. Probe output on the stuck shape:
   `flow: issue_711 — build/check failed (FileNotFoundError: … issue_711/brief.md); skipping
   this bundle (left CHECKED)`. Before the fix these bundles sat at `UNPLANNED` and reopened a
   Plan session every run. Now they fail loudly and name the missing file, and every batch run
   repeats that until someone repairs them. Hand repair (out of scope here): write `brief.md`
   for each (e.g. from its `iteration-v1/brief.md`) and re-run; the next beat assembles the
   SUMMARY. `pdca split <id> --accept` cannot repair them — it refuses an already-marked parent.
2. **A split accepted on a parent with no brief AND no archive is now refused** (in `preflight`
   and `accept`, before any write or filing). On main it "succeeded" into the stuck shape. It
   happens when a planner writes `split-proposal.md` by hand for a never-briefed bundle
   (`leaves.do_split` already refuses that bundle, `leaves.py:1802-1804`). The message tells
   the planner to write `brief.md` and re-run; a parent with its own brief keeps it untouched.
3. **`pdca cleanup` goes quiet on the legacy shape when its tracker issue is CLOSED.**
   `cleanup.py:271-295` reports briefless bundles only while they derive `UNPLANNED`. A
   briefless bundle carrying the marker now derives `BUILT`, so it falls through to
   `return None` (no row) instead of the "in-flight cycle — NOT marking resolved" row. Legacy
   shape only; bundles split after this fix have a brief and take the mid-flight branch.
4. `template/PCDA/quality-cycle.md:60-68` still shows "(no brief.md) → UNPLANNED". That table
   is the simplified ladder for an ordinary bundle (each row adds to the row above), so I left
   it alone.
5. `_do_close` (brief's out-of-scope note): confirmed it does not run for a split parent — with
   the brief written, the parent derives `BUILT`, not `PLANNED`, so `driver.py:69-72` is never
   reached.
6. Ordering note: #498 "touches the accept path after this lands". This patch adds blocks at
   patched `split.py:919-926`, `:991-994`, `:1010-1025` and one call in `preflight` (`:322-325`).
   Expect textual overlap there if #498 edits the same regions.

## The three self-refutation questions

**(a) Genuine red? Yes.** The project's C4 gate script (`./engine/scripts/run-verify.sh`, run
with `PDCA_BUNDLE` = this bundle, `PDCA_WORKTREE` = the worktree, from the instance root):
green leg `Ran 109 tests … OK`; red leg (production hunks reverted, tests kept)
`Ran 109 tests … FAILED (failures=16)`, every one an assertion failure, no import error →
`PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`, exit 0. The two tests that stay
green on main are the regression guards (d) and (f) — by design, "still names" and "nothing
changes". Partial reverts, to check the brief's "one module is not enough":
- only `state.py` reverted: the 6 (e) subtests fail, (a)-(d) pass (the parent has a brief);
- only `split.py` reverted: (b), (c), both rollback tests, both refusal tests and the CLI test
  fail, and driving the parent ERRORS at `assemble` (finding 1); (a) and (e) pass.
Mutations, each restoring the tree to `patch.diff` afterwards (checked with `cmp`):
attempt-1 rollback gating → only the torn-write test fails; Slug-only archive check → the two
unfilled-field tests fail; no `preflight` call → the CLI test fails; archives compared as text
→ `test_the_source_is_the_latest_re_plan_not_the_first_archive` fails ('plan-a' != 'plan-b').

**(b) Production path? Yes.** Every test calls the real `split.accept`, `state.state`,
`handoff.check_planner`, `driver._archive_iteration`, `driver.run_issue` or `cli._split`. The
module imports only pre-existing names (`brief`, `handoff` added to the existing
`from pdca_harness import …`, patched `test_split.py:24`), so the red leg imports cleanly.
Faults are injected at the disk boundary only — `Path.write_text` patched to land part (or
all) of the bytes, then raise ENOSPC — the technique the suite already uses (patched
`test_split.py:1336-1345`, `test_split_lineage.py:287-302`). No production logic is replaced.
Two patches are not the disk: the drive-to-sign-off test wires `do_build` / `run_review` to
raise (they must never run on a split parent, as in patched `test_split.py:877-883`), and the
CLI test records `file_children` instead of calling `gh`.

**(c) Fixture includes the fault? Yes.** The realistic parent is a complete authored brief
archived by the driver's own `_archive_iteration(…, include_brief=True)`, never hand-placed,
and `_iterated` asserts the shape (no top-level `brief.md`, `iteration-v1/brief.md` present)
before anything else runs. The (e) shapes include the exact stuck file set the brief lists
(`build-notes.md`, `close-disposition`, `iteration-v1`, `split-lineage.json`,
`split-proposal.md`), a tracker-resolved record, later ladder stages, and `patch.diff`. The
torn-write fixture really leaves 40 characters on disk before raising. The ordering fixture
builds a 10-round history (re-plans archived at rounds 2 and 10) through the driver's archive
call.

## Other gates run (project runners, under `timeout`)

- `./engine/scripts/run-suite.sh` (T3) on the final patch: root suite (copier render +
  update-compat) `Ran 24 tests … OK`; offline driver suite `Ran 1907 tests … OK (skipped=2)`
  (main has 1894; +13 new; same 2 skips).
- `git diff --check`: clean. No formatter, linter or commit hook is configured in the target
  (no pre-commit config, no installed hooks, and CI runs tests + docs checks only). No docs
  touched, so the T2 docs gates are unaffected.

## Housekeeping

- One slip: I wrote one full driver-suite log to `/tmp/pdca-481-driver-suite.log`, outside the
  allowed roots. It is a plain test log, nothing else; later runs kept their output in the
  terminal. Probes used `TemporaryDirectory(dir=<worktree>)`, which Python removes itself;
  `python3 -m py_compile` wrote `__pycache__/` inside the worktree (gitignored, not in the
  patch).
- External dependencies: none beyond the base toolchain and the already-registered copier row.
  No NEEDS-HUMAN dependency declaration.
