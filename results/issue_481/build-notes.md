# Build notes — issue 481 / split-parent-keeps-a-plan-artifact (attempt 3)

Target: `eduralph/pdca-harness @ main`, base `4050da290242ac1c797c93d2bce997a00263ad47`
(`origin/main`, the worktree HEAD). "main:" citations are that commit. "patched:" citations
are the worktree with this attempt's `patch.diff` applied.

The fix itself is attempt 2's, which Check round 2 passed on every item ("No grounded patch
defect found"). This attempt answers the two implementation items the round-2 code review
raised, which the auto-iterate carried forward. Nothing else in the fix changed.

## What this attempt changed

### 1. One reader of the `iteration-v<N>` archives (carry-forward item 1)

Round 2 found the `^iteration-v(\d+)$` pattern and the "latest archive that holds a
`brief.md`" logic written twice: attempt 2's `split._archived_brief` and
`size_signal.iteration_rounds` (main `size_signal.py:69-70`, `:147-154`). Attempt 2 kept its
copy on purpose, to stay inside the Ordering note's three files. Check rejected that, so this
attempt removes the copies:

- patched `state.py:303` `_ITERATION_DIR` and `:306-320` `iteration_archives(d)`: every
  numbered archive directory as `(N, path)`, sorted by N as a number (as text,
  `iteration-v10` sorts before `iteration-v2`); a stray FILE with an archive's name is
  skipped, as `size_signal` did before. `import re` added at `state.py:12`.
- patched `state.py:323-332` `replan_archives(d)`: the archives that hold a `brief.md`, i.e.
  the ones an iterate-to-Plan wrote, oldest first. The last one holds the brief the bundle was
  last planned from.
- patched `size_signal.py:142-148`: `iteration_rounds` now reads both through `state`. Same
  results: the boundary is the last re-plan's N, rounds after it are counted, and the re-plan
  count is `len(replans)`. main's `_ITERATION_DIR` (`:69-70`) and `import re` (`:61`, used
  only by it) are gone; `from . import state, waves` at patched `:61`.
- patched `split.py:781-787`: `_parent_plan` takes `state.replan_archives(parent)[-1]` as its
  source. Attempt 2's `_ITERATION_DIR` and `_archived_brief` are gone from `split.py`.
- `template/scripts/size-calibrate:101` (main): deleted one line, a third copy of the same
  pattern. It has been dead since f616bc9 moved `iteration_rounds` out of the script into
  `size_signal` (the script imports it, main `size-calibrate:88`); nothing in the script reads
  the constant. With it gone, `state.py` holds the only copy.

Why `state.py`: both consumers already import it at module level (`split.py:36`;
`size_signal` through `waves.py:35`, and now directly), and it already owns the archive
definitions (`DOWNSTREAM_OF_BRIEF`, `DOWNSTREAM_GLOBS`), moved there in #334 for the same
import-cycle reason (main `state.py:112-114`).

### 2. The stale `check_planner` docstring (carry-forward item 2)

main `handoff.py:113-116` said "Only the reap passes" `dependencies=False`. Attempt 2 added a
second caller, `split._parent_plan`. Patched `handoff.py:113-118` names both callers and says
why split passes it: it checks an ARCHIVED brief only for the fields it copies into the new
parent brief, and that brief declares no dependency of its own. A matching comment sits at
the call (patched `split.py:791-795`). Docstring only; no behaviour change in `handoff.py`.

### 3. The test

One assertion added to `test_the_source_is_the_latest_re_plan_not_the_first_archive`
(patched `test_split.py:1907`): before the accept, `size_signal.iteration_rounds(parent)` must
be `(0, 2)`, i.e. the size backstop sees the same latest re-plan (`iteration-v10`) the split
rebuilds from. `size_signal` joins the test module's import (patched `test_split.py:24-25`).
It is pre-existing API on main, so the C4 red leg still imports cleanly. No new test methods;
the class is attempt 2's `SplitParentKeepsAPlanArtifact` (patched `test_split.py:1781`).

## Files touched, and the brief's Ordering note

The Ordering note said this bundle "stays in `split.py`, `state.py` and
`template/tests/test_split.py`" (no overlap with 508 / 526 / 528). The two carry-forward
items live in other files, so this attempt also touches:

- `template/src/pdca_harness/handoff.py`: docstring lines only (patched `:113-118`).
- `template/src/pdca_harness/size_signal.py`: imports (main `:58-63`), the removed constant
  (main `:69-70`), and the body of `iteration_rounds` (main `:147-154`).
- `template/scripts/size-calibrate`: one deleted line (main `:101`).

I did not read the briefs of 508 / 526 / 528 (outside a builder's input), so I cannot say
whether they edit these lines. **Please check for overlap at sign-off.** The hunks are small
and in stable regions; a conflict needs another bundle editing the same lines.

## The whole fix (unchanged in substance from attempt 2)

- **`state.state()` (criterion e).** main `state.py:304-307` returned `UNPLANNED`/`RESOLVED`
  for any bundle without `brief.md`, before looking at `patch.diff` or the close marker
  (`:310`). patched `state.py:347-351` asks "past Do?" first and only then "is there a
  brief?". A bundle with either Do artifact now follows the same ladder a briefed one does.
  The only shape whose answer changes is "no brief + a Do artifact": it was `UNPLANNED` (never
  `RESOLVED`: `is_resolved` already counted the marker and `patch.diff` as cycle evidence,
  main `state.py:292`) and is now what its briefed twin derives.
- **`split.accept` (criteria a-d, f).** patched `split.py:756-806` `_parent_plan`: `None` when
  the parent has its own `brief.md` (then nothing reads or writes it, criterion f). Otherwise
  it takes the latest re-plan's archived brief, holds it to `check_planner`'s field clause
  (slug, success criterion, repo + branch target), and returns
  `(relative path, Slug, Repo + branch target)`. No archive, an unreadable one, or one with an
  unfilled field → `SplitError` before any write.
  patched `:809-814` `_field` and `:817-854` `_split_parent_brief` render the new brief: Slug
  and target copied (re-indented so `whole_field` reads them back unchanged), Defect / Success
  criterion / Scope describing the split and naming every child bundle,
  `External dependencies: none`, `Disposition hint: split`.
  patched `:909-911`: rendered in accept's pre-write phase, next to the lineage snapshot (main
  `:777-797`). patched `:976-979`: written as the LAST write before the marker (main order:
  archive → lineage → breadcrumb → marker, `:835-862`), so the parent only turns terminal with
  its brief on disk. patched `:995-1010`: on failure the rollback removes it whatever write
  failed (a write can land part of a file and then raise), after the marker's own cleanup.
  patched `:322-325`: `preflight` asks `_parent_plan` too, so `cli._split` refuses before
  `file_children` files real tracker issues (main `cli.py:767-806`).

## Rejected alternatives, with costs

New this attempt:

- **Keep the copy and point at `size_signal` (attempt 2's choice).** 0 extra files, but it is
  what Check round 2 sent back.
- **Import `size_signal._ITERATION_DIR` into `split`.** Saves the regex line only: the "latest
  archive holding a brief" loop would still exist twice (split's max loop, size_signal's
  `max(replans)`), and split would import a private name from another module.
- **Put the helper in `driver.py`, next to `_archive_iteration` (the reviewer's other
  option).** `driver` imports `size_signal` at module level (main `driver.py:19-20`), so
  `size_signal` importing `driver` back would need a function-local import, and `split`
  already imports `driver` lazily (main `split.py:835`). That is 2 local imports and a
  documented cycle to step around, against 0 for `state.py`.
- **A single `latest_replan_archive(d) -> Path | None` (the reviewer's example name).**
  `size_signal` also needs every archive (to count rounds after the boundary) and the number
  of re-plans, so it would keep its own regex loop for those. Two small helpers
  (`iteration_archives` + `replan_archives`: patched `state.py:302-332`, 27 lines counting the
  pattern and the docstrings) remove every copy.
- **Route `driver._next_iteration_no` (main `driver.py:315-317`), `leaves.py:1405-1407`,
  `has_cycle_evidence` (main `state.py:298`) and `_close_class` (main `driver.py:244`)
  through the helper.** None of them parses N: two count entries, two test existence.
  Changing `_next_iteration_no` from "count + 1" to "max N + 1" changes how archives are
  numbered, which is not this slice.
- **Drop the second `dependencies=False` caller instead of editing the docstring**, by
  checking the generated brief with the default `check_planner`. It needs the text on disk:
  a `TemporaryDirectory` in both `preflight` (with child labels standing in for ids, as
  `_staged_estimates` does, `split.py:362-388`) and `accept`, about 8-10 lines, and a refusal
  that then depends on a writable temp dir. Same verdict on the fields as today; the
  docstring edit is 2 net lines.

Still valid from attempt 2 (details in `iteration-v2/build-notes.md`): an atomic
temp-file + `os.replace` write (+6 lines, and the unconditional removal is still needed
because the marker write can fail after it); a "wrote the brief" flag (+2 lines, same
behaviour); exclusive create (+5 lines for a race nothing else in `accept` guards); filling a
missing target from the children (+10 lines, an inference no human made); copying the
proposal's prose into the brief (+15-20 lines, and field-shaped lines would be parsed as the
parent's own fields); refusing every briefless parent (ruled out by the brief's Scope); a new
state or an `assemble` that tolerates no brief (other files, and it hides the missing Plan
artifact instead of restoring it).

## Findings for the human (not widened into this slice)

1. **Legacy stuck bundles now fail loudly in `assemble` instead of reopening Plan.** A
   briefless bundle with the marker (the v0.56.0 shape: `wyrd-pdca` issue_711 / issue_654) now
   derives `BUILT`; the driver records the close gates and review note, and
   `assemble.assemble_summary` raises `FileNotFoundError` on the missing `brief.md` (main
   `assemble.py:270`). `flow._isolate` (main `flow.py:51-70`) contains it per bundle and leaves
   it `CHECKED`, naming the file. The brief's self-test expected an empty §1 instead; it
   raises. Repair by hand (out of scope): write `brief.md` for each, for example from its
   `iteration-v1/brief.md`, and re-run. `pdca split <id> --accept` cannot repair them: it
   refuses an already-marked parent.
2. **A split on a parent with no brief AND no archived brief is now refused** (in `preflight`
   and `accept`, before any write or filing). On main it "succeeded" into the stuck shape.
   `leaves.do_split` already refuses that bundle (main `leaves.py:1800-1804`).
3. **`pdca cleanup` goes quiet on the legacy shape when its tracker issue is closed.** main
   `cleanup.py:271-295` reports briefless bundles only while they derive `UNPLANNED`. Legacy
   shape only; parents split after this fix have a brief.
4. `template/PCDA/quality-cycle.md:60-68` still shows "(no brief.md) → UNPLANNED". It is the
   simplified ladder for an ordinary bundle, so I left it.
5. `_do_close` (the brief's out-of-scope note): confirmed not reached for a split parent. With
   the brief written, the parent derives `BUILT`, not `PLANNED` (main `driver.py:69-72`).
6. **#498 overlap.** This patch adds blocks at patched `split.py:904-911`, `:976-979`,
   `:995-1010`, one call in `preflight` (`:322-325`), and the new functions at `:756-854`.
   Expect textual overlap there if #498 edits the same regions.
7. **New: the convergence report misreads a briefless parent.** `preflight`'s advisory report
   sizes the parent from `parent/brief.md`; for the realistic briefless parent that file does
   not exist, so the parent scores 0 ("no brief to size", main `sizing.py:288-289`) and the
   report will usually say NOT CONVERGED about a parent it never sized. Same on main, advisory
   only, changes nothing that is written. A fix would size the parent from `_parent_plan`'s
   source. Not widened.
8. **New: the file set is wider than the Ordering note** (see above). Please check 508 / 526 /
   528 for overlap in `handoff.py:113-118`, `size_signal.py` and `scripts/size-calibrate`.

## The generated brief, for the fitness-to-purpose item in §6

Round 2's reviewer left a standing NEEDS-HUMAN: does this brief give enough context to sign
off a split parent? This is what `split.accept` writes for the test's realistic parent
(authored brief archived by `driver._archive_iteration(..., include_brief=True)`, then a
two-child accept). Rendered with the patched code; afterwards `state.state()` = `BUILT` and
`handoff.check_planner()` = `[]`.

```
# Brief — issue 500 / widget-overflow (split parent)

> The Plan artifact (docs 02 §PLAN), written by `split --accept` (issue #481):
> this bundle had no brief.md when its split was accepted — an iterate-to-Plan
> had archived it to `iteration-v1/brief.md`.

- **Slug:** widget-overflow
- **Defect:** decomposed instead of built as one cycle: the slice was judged to be more
  than one shippable outcome. The seams are set out in `split-proposal.md`; the
  original defect and scope are in `iteration-v1/brief.md`.
- **Success criterion:** the slice is decomposed, not built here — the child bundles
  issue_601, issue_602 each carry their own brief, and together they cover
  the goal of `iteration-v1/brief.md`. No patch lands in this bundle; each child is verified
  by its own cycle.
- **Repo + branch target:** acme/widgets @ main
- **Scope:** decomposition only: no patch, test or gate run belongs to this bundle. / out
  of scope: building any part of the original slice here — the child bundles
  carry that work.
- **External dependencies:** none
- **Disposition hint:** split
```

## The three self-refutation questions

**(a) Genuine red? Yes.** The project's C4 gate script (`./engine/scripts/run-verify.sh`, from
the instance root, `PDCA_BUNDLE` = this bundle, `PDCA_WORKTREE` = the worktree, under
`timeout 900`): green leg `Ran 109 tests … OK`; red leg, with all five production files
reverted and the test kept, `Ran 109 tests … FAILED (failures=16)`, every one an assertion
failure, no import error → `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`,
exit 0. Partial breaks, each run through the same script (its green leg reports what fails on
the broken tree) and each restored afterwards, checked with `cmp` against `patch.diff`:
- `split.py` alone reverted: 8 failures + 1 error ((b), (c), both rollback tests, both refusal
  tests, the CLI test, the latest-re-plan test; driving the parent to sign-off errors in
  `assemble`, finding 1). (a) and (e) pass: the state fix alone covers them.
- only the `state()` reorder undone, the new helpers kept: exactly the 6 (e) subtests fail.
- the shared helper sorting archives as text instead of by number: the latest-re-plan test
  fails on the new assertion, `Tuples differ: (8, 2) != (0, 2)`, so the test pins the
  size backstop to the shared reader as well as the split.

**(b) Production path? Yes.** Every test calls the real `split.accept`, `state.state`,
`handoff.check_planner`, `driver._archive_iteration`, `driver.run_issue`, `cli._split` or
`size_signal.iteration_rounds`. The module imports only names that exist on main, which is
why the red leg imports cleanly. Faults are injected only at the disk boundary
(`Path.write_text` patched to land part or all of the bytes, then raise ENOSPC), the
technique the suite already uses. Two other patches: the drive-to-sign-off test wires
`do_build` / `run_review` to raise (they must never run on a split parent), and the CLI test
records `file_children` instead of calling `gh`.

**(c) Fixture includes the fault? Yes.** The realistic parent is a complete authored brief
archived by the driver's own `_archive_iteration(..., include_brief=True)`, never hand-placed,
and the fixture asserts the shape (no top-level `brief.md`, `iteration-v1/brief.md` present)
before anything runs. The (e) shapes include the exact stuck file set the brief lists
(`build-notes.md`, `close-disposition`, `iteration-v1`, `split-lineage.json`,
`split-proposal.md`), a tracker-resolved record, later ladder stages and `patch.diff`. The
torn-write fixture really leaves 40 characters on disk before raising. The ordering fixture
builds a 10-round history (re-plans at rounds 2 and 10) through the driver's archive call.

## Other gates run (project scripts, under `timeout`)

- `./engine/scripts/run-suite.sh` (T3): root suite (copier render + update-compat)
  `Ran 24 tests … OK`; offline driver suite `Ran 1907 tests … OK (skipped=2)`, the same count
  as attempt 2 (no new test methods this round). This suite includes `test_size_signal.py` and
  `test_size_calibrate.py`, which exercise the refactored `iteration_rounds` (stray-file
  archives, iterate-do histories, re-plan boundaries) and the edited script.
- T2 docs gate not run: no file under `docs/` changes, and no doc mentions the moved names
  (searched `*.md`, `*.jinja`, `*.tpl`, `*.toml`, `*.yml`).
- Commit-readiness: `git diff --check` clean. The target configures no formatter or commit
  hook: no pre-commit config, only `*.sample` files in the hooks directory, and CI runs docs
  and render checks only. New lines stay within the widths already used in each file.

## Housekeeping

- **One slip:** I redirected the first C4 run's output to `/tmp/.c4-481-unused`, outside the
  allowed roots. It is a plain test log and nothing else. I did not remove it (cleanup is the
  harness's). Every later run printed to the terminal.
- The sample brief above was rendered in a `TemporaryDirectory` inside the worktree's
  gitignored `.cache/`, which Python removed; `PYTHONDONTWRITEBYTECODE=1` was set.
  `python3 -m py_compile` earlier wrote `__pycache__/` inside the worktree (gitignored, not
  in the patch).
- External dependencies: none beyond the base toolchain and the already-registered copier
  row. No NEEDS-HUMAN dependency declaration.
