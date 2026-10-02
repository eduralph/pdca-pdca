# Build notes — issue 545 / split-parent-closes-with-children-bound-depth (iteration 2)

Target: `eduralph/pdca-harness @ main`, worktree `$PDCA_WORKTREE` =
`/home/eddie/pdca/pdca-harness.pdca-wt-l0` (HEAD `f33a23f`, same as `origin/main`). Every
`path:line` below is on that tree with this `patch.diff` applied.

## How this iteration was built

The sign-off kept the design and asked for implementation fixes only, so I applied the
previous attempt's patch (`iteration-v1/patch.diff`, applies cleanly to `f33a23f`) and
changed what the carry-forward names. Everything not listed under "What changed this
iteration" is as it was in iteration 1 (its notes still describe it).

## What changed this iteration (carry-forward items)

### 1. A partly damaged child list no longer closes the parent (reviewer C3 FAIL)

- `template/src/pdca_harness/cleanup.py:246-259` — `_split_parent_row` still reads the list
  through `flow._lineage_children` (`flow.py:690`, unchanged, as the carry-forward asks), but
  now refuses to close unless the reader kept **every** entry:
  `if not children or len(children) != len(record["children"])` (`cleanup.py:255`). The reader
  keeps exactly the entries that are non-blank strings and drops the rest, so "same length"
  is exactly "every entry is a non-blank string". A dropped entry → report "its children are
  unknown (… an entry that is not an id string: a null, a bare number, a blank) — no action;
  close the issue by hand once its children are done". No `gh` call is made for that row.
  `record["children"]` is safe there: the reader returns a non-empty list only when the
  record's `children` is a list (`flow.py:702-707`).
- Why this shape and not a second strict reader: brief (d) asks not to write a second,
  different reader of `children`. The length test adds one condition on top of the one
  reader instead of copying its filter (`isinstance(c, str) and c.strip()`) into cleanup,
  where the two copies could drift.
- A strict reader in cleanup would be about the same size (≈4 lines:
  `raw = record.get("children"); if not isinstance(raw, list) or not raw or not all(isinstance(c, str) and c.strip() for c in raw): …`),
  so size did not decide it; one filter instead of two did.
- Regression tests: `template/tests/test_split_parent_lifecycle.py:210-235`
  (`test_p5_a_partly_damaged_children_list_never_closes`) — `["601", null]`, `["601", 602]`
  and `["601", "  "]`, with #601 **and** #602 closed as completed, so the damaged entry is the
  only reason not to close (a fix that coerced `602` to `"602"` would also fail it).

### 2. Prompt and config text no longer overpromise (reviewer T2 FAIL)

- `template/agents/planner.md.jinja:164-169` — the "stays open" paragraph now says: once the
  parent's bundle is COMPLETE and every child issue is closed, `cleanup --apply` closes it
  with a comment naming every child, "as completed if at least one child was completed, else
  as not planned"; and "Only a COMPLETE parent waits for its children: one whose bundle ends
  DISCONTINUED is closed as not planned like any other discontinued bundle."
- `template/pdca.toml.jinja:513-518` — the splitter comment says the same, with the
  DISCONTINUED case in brackets.
- New wording test `test_the_planner_is_not_promised_a_completed_close`
  (`test_split_parent_lifecycle.py:433-441`): the paragraph(s) with "stays open" must also
  say "not planned" and "COMPLETE". The reviewer noted S1's keyword checks could not catch the
  overpromise; this one does (shown red on the iteration-1 prompt below). The config comment
  stays untested, as the brief's S4 says; read it in the diff.
- `docs/07-crosscutting.md:673` and the module docstring `cleanup.py:22-28` were already
  qualified; I only widened their "close by hand" clause to the new damaged-list rule.

### 3. Code-review nits

- `_close_issue` docstring rewrapped (`cleanup.py:185-189`); no line over 90 characters.
- Non-numeric child id: now its own report-only row that says "close the issue by hand"
  (`cleanup.py:260-267`): "child id `MANT-7` in split-lineage.json is not a tracker issue
  number, so its state cannot be read — no action; close the issue by hand once its children
  are done". It returns before any `gh issue view`, since waiting cannot resolve it.
  Test: `test_a_child_id_that_is_not_a_tracker_number_is_closed_by_hand` (`:237-249`).
  The gh-failure case (P4) keeps its own wording, "child state unknown for #602 (gh failed
  or gave no usable state; a later run retries)", because that one can resolve on its own.
- `test_d1_a_bare_namespace_without_force_is_refused_too` is gone. In its place are two
  tests through the **real CLI parser**, `cli.main(["split", "500", "--accept", …])` with
  `cli.Config.load` patched the way `test_autoiterate.py:776` does it
  (`test_split_parent_lifecycle.py:357-385`): without `--force` → refused, nothing filed, no
  child bundle, stderr names `--force`; with `--force` → accepted, children at depth 3. This
  also closes a gap in iteration 1: D2 passed `force=True` in a hand-built namespace, so it
  would have stayed green even if the `--force` argparse flag (`cli.py:197-200`) were
  missing. If argparse rejects the flag, the helper turns the `SystemExit` into a test
  failure (`:368-369`), so the red leg records a failure, not an error.
- P8 now also asserts the hand-written note is kept (`:279`).

### Small extras (not asked for; each one line or two)

- Closing comment lists each child with its own reason in words (`cleanup.py:294-297`):
  `#601 (completed), #602 (not planned)`. Iteration 1 printed "not planned" for any
  non-completed child, which would mislabel a child closed as `DUPLICATE`. P2 asserts the
  two strings (`test_split_parent_lifecycle.py:153-155`).
- `split.check_depth` message (`split.py:312-316`): "Nothing was filed or written" (true on
  the `--ids` path too, where nothing is filed by the tool anyway), and removed a stray
  `f` prefix on a literal with no placeholders.

## Unchanged from iteration 1 (for the reader's orientation)

- `cleanup.py:398-403` — split parent decided first in the COMPLETE/OPEN branch, before the
  recorded-PR checks (P9) and the empty-patch close (P7); DISCONTINUED keeps today's path.
- `cleanup.py:169-191` — `_bundle_comment` + `prefer_bundle_comment` on `_close_issue`
  (default `True`, so `test_bundle_tracker_comment_file_is_preferred`, `test_cleanup.py:383`,
  is unaffected).
- `split.py:298` `MAX_SPLIT_DEPTH = 2`; `split.py:301-316` `check_depth`; called from
  `preflight` at `split.py:349`, before `_parent_plan` and before any `gh issue create`.
- `cli.py:197-200` `--force`; `cli.py:814` passes `force=bool(getattr(args, "force", False))`
  so the ~20 existing bare-namespace callers keep working unedited.
- `cleanup.py:57` imports `flow` and `split`; no import cycle (`flow` does not import
  `cleanup`). The advisory review suggested moving `_lineage_children` / `_is_split_parent`
  into `split.py` later; not done here, since the brief asked to reuse them where they are.

## Evidence (all run on this iteration's final tree)

- **C4, the gate's own script** (`PDCA_BUNDLE=… PDCA_WORKTREE=… ./engine/scripts/run-verify.sh`
  from the instance root): green leg `Ran 21 tests … OK`; red leg (every non-test hunk
  reverted) `Ran 21 tests … FAILED (failures=23)` (subtests counted apart), all assertion
  failures, no import error; verdict `PDCA-EVIDENCE: C4 PASS — red without the fix, green
  with it`. Run twice, the second time on the final `patch.diff` (after a last wording
  change to one report message); same counts both times, and afterwards the worktree still
  matched `patch.diff` exactly (`git diff | cmp`).
- **Red against iteration 1, not only against main.** I put the iteration-1 `cleanup.py` back
  (from `iteration-v1/patch.diff`) with the new tests in place and ran the module
  (`cd template && PYTHONPATH=src python3 -m unittest tests.test_split_parent_lifecycle`):
  `Ran 21 tests … FAILED (failures=4)`: exactly the three damaged-list subtests and the
  non-numeric-id test. Each damaged-list case failed on `Lists differ: [['gh', 'issue',
  'close', '500', '--repo', …]] != []`, the premature close the reviewer reported. The same
  swap for the planner prompt made `test_the_planner_is_not_promised_a_completed_close` fail
  with `'not planned' not found in "The parent's tracker issue **stays open** … closes it —
  as completed, …"`. Afterwards `git diff` matched `patch.diff` byte for byte (`cmp`).
- **S3**: `cd template && PYTHONPATH=src python3 -m unittest tests.test_split` → `Ran 109
  tests … OK` (system python 3.14.4). With `tests.test_cleanup` and the new module too:
  `Ran 167 tests … OK`. `test_split.py` and `test_cleanup.py` are not in the patch, so no
  assertion in `TheDoctrineIsConsistent` / `ThePlannerIsToldItOwnsTheSplit` changed.
- **T3** (`./engine/scripts/run-suite.sh`, final tree): root suite (render + update-compat)
  `Ran 24 tests … OK`; driver suite `Ran 2092 tests … OK (skipped=2)` (iteration 1 had 2088;
  the 4 more are the new tests); `PDCA-EVIDENCE: root suite OK, driver suite OK`.
- **T2** (`./engine/scripts/run-docs-check.sh`): `lint_docs: OK`, `render_site: wrote 22
  page(s)`, `link audit OK`.
- **Commit-ready**: the target has no `.pre-commit-config.yaml`, no formatter/linter config,
  and no active hooks in its git dir (only `*.sample`). Its CI (`.github/workflows/`) runs
  the docs lint + site render (covered by T2) and the render check (covered by T3's root
  suite). DCO sign-off on the commit is the publish step's job.

## Refute-your-own-test (forced)

- **(a) Genuine red?** Yes. The C4 red leg reverts every production, prompt and docs hunk and
  re-runs the module: 23 assertion failures (P1–P5 including the new damaged-list and
  non-numeric cases, P8, P9, the case test, D1 ×2 + the real-CLI D1, the real-CLI D2 (argparse
  rejects `--force` on main), S1, S2 and the new wording test). The sharper red: with only
  iteration 1's `cleanup.py` back, the three damaged-list subtests and the non-numeric test
  fail, and nothing else does. That is the reviewer's C3 defect, reproduced by the new tests.
- **(b) Production path?** Yes. The P-tests call `cleanup.run(cfg, [], apply=…)` with only
  `subprocess.run` / `shutil.which` patched at `cleanup`'s module level (the `CleanupBase`
  pattern). The D-tests call `cli._split`, and two now call `cli.main([...])` (argparse
  included), with only `split.subprocess` / `split.shutil.which` faked (the
  `TheWholeChainUnmocked` pattern): the real `preflight`, `check_depth`, `file_children`,
  `accept` and `materialise` run, and child depth is read back from the real
  `split-lineage.json`. The wording tests read the real role prompt and the real module doc.
- **(c) Fixture includes the fault?** Yes. The parent is a real COMPLETE bundle (the helper
  asserts `state.state == COMPLETE`) with the real `close-disposition` marker and a real
  lineage file. The damaged entries (`null`, `602`, `"  "`), the non-numeric id, the open
  child, the unreadable child (fake `gh` returns rc 1), the merged pre-split PR and the
  `tracker-comment.md` are each present in the test that covers them. The damaged-list
  fixture closes every real child, so the damaged entry is the only thing standing between
  the parent and a close.

## Housekeeping

The harness owns cleanup, so I removed nothing. Two things outside the roots came from me:

- `/tmp/.unused`: while running the C4 gate the first time I sent its output there by
  mistake (it holds a copy of that run's gate log). I re-ran the gate with the output
  streamed instead. Harmless.
- `git add -N template/tests/test_split_parent_lifecycle.py` in the worktree (intent-to-add,
  so `git diff` includes the new file). The driver rebuilds the worktree from base +
  `patch.diff` at Check, so it does not matter there.

## Open questions left for sign-off (from the brief, unchanged)

The threshold (OQ1), the reversal of the issue's first acceptance line and what becomes of
#545 (OQ2, OQ6), all-dropped → not planned (OQ4), the DISCONTINUED case (OQ5) and one bundle
or two (OQ7) are the human's calls. The code follows the brief's chosen answers; this
iteration did not revisit them.
