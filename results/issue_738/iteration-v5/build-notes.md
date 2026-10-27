# Build notes — #738: hold a bundle whose own base cannot be built

Target: eduralph/pdca-harness, built on the run's line `pdca-integration/main-r547f8028520f`
at `75a886e` (the worktree's HEAD). Every `path:line` below is on `75a886e` unless it says
otherwise. The patch applies cleanly to `75a886e` (`git apply --cached --check`).

## What the patch does

Before: any `IntegrationError` from `integrate.build_bundle_base` was re-raised by
`_bundle_bases` (`template/src/pdca_harness/flow.py:1019-1022`) and the wave loop printed
`STOPPING` (`flow.py:2765-2770`), so bundles unrelated to the failure stayed PLANNED.

After: the failure holds that bundle. Its dependents are skipped and its `Conflicts with`
partners are held by `_runnable`; the rest of the wave goes on. Only an
`IntegrationTreeError` (`integrate.py:101`) still stops the run at a base. A rewrite hold
before the last wave says the next fold stops the run (the #633 stop at `flow.py:2871-2877`
is unchanged). The rewritten member stays in the end-of-run check, so a rewrite the line
still carries at the end of the run is exit 1 (#695 wins).

### `template/src/pdca_harness/flow.py`

1. `_bundle_bases` (`flow.py:992-1034`): new required `held` parameter. The `except` at
   `:1019-1022` now re-raises only `integrate.IntegrationTreeError`, with its args rewritten
   as before so the STOPPING line still says whose base it is. Any other `IntegrationError`
   goes into `held[d.name] = (whose, exc)`, and the loop goes on to the next bundle. The
   pointing loop (`:1024`) skips held bundles. Docstring `:1000-1008` rewritten.
2. New, inserted after `:1034` (before `_heads_taken`, `:1037`):
   - `_BASE_HOLD_STEPS`: the fix for the causes whose own message gives no step, or gives
     a fold's step. Keyed on the start of `exc.cause`: the fetch (`integrate.py:2042`, whose
     message adds "the fold cannot see the branches it merges", a fold's words), checkout
     not found (`:2032`), integration worktree not made (`:2056`), and the two bare git-step
     failures in the base build (`:853` "could not start …", `:214` via `pushed_tip` at
     `:865`).
   - `_base_hold_why(exc)`: `exc.cause` plus the table's step, or else the message as
     raised (every other refusal names its own step, `_Rewritten`'s restore/re-publish
     remedy included).
   - `_announce_base_holds(cfg, held, fold_next=…)`: one stderr line per hold, modelled on
     `_announce_conflict_holds` (`flow.py:1435`). For a `_Rewritten` cause with a later wave
     left it adds: "But the next fold stops the run unless origin/fix/A is restored first: a
     fold refuses a branch rewritten after the line took it (#633)." The branch name comes
     from the member's publish record (`integrate._published_ref`, `integrate.py:218`).
3. `_runnable` (`flow.py:681-856`): new `unbuilt` parameter (default empty, so every
   existing caller is unchanged). Partners are computed like `partners` / `clashed`
   (`:758-762`), the target is resolved for them (`:768-769`), one stderr line is printed
   per partner (after `:846-853`), and they are left out of `runnable` (`:854`). Docstring
   `:731-734` extended.
4. `_drive_and_act`:
   - the docstring's `holds` paragraph (`:2555-2564`) adds `"base"`.
   - `stop_named` (`:2686-2688`) is replaced by `held_base` (see "Ruled out" 1).
   - the `_runnable` call (`:2699-2713`) passes `held_base` in `held=`, in the
     `conflicts=` condition, and as `unbuilt=`, mirroring how `held_unpushed` is passed.
   - the base step (`:2757-2770`): a `failed` dict is filled by `_bundle_bases`. The handler
     catches `IntegrationTreeError` only. Then it announces the holds, adds them to
     `held_base`, filters `runnable`, and `continue`s if nothing of the wave is left.
   - end of run (`:2907-2924`): `_report_late_rewrites` gets every accepted bundle (no
     `stop_named` filter). `holds` gets `"base"` entries before the late ones, so a late
     `"rewritten"` / `"unchecked"` still wins.

### `template/src/pdca_harness/integrate.py`

Only the `_Rewritten` docstring (`integrate.py:127-129`) changed. It no longer says the
end-of-run check skips the branch. No message text changed. `_fetch`'s text
(`:2042-2044`) is untouched, because the fold, the carry and `rewritten_carried` share it.

### `template/src/pdca_harness/cli.py`

- `_RC_HELD` comment (`cli.py:692`) now covers a bundle held before it was built.
- New `_BASE_HOLD = "base"`, placed between `_RC_HELD` and `_FAILED_REASONS` (`:695-698`).
- `_results_rc` docstring bullets "1" and "3" (`:705-716`) rewritten.
- Rule 1 (`:728`): a key passes when its state is in `ok` or `holds` maps it to `"base"`.

### Tests

- New `template/tests/test_flow_bundle_base_holds.py`: the brief's cases (1), (2), (2b),
  (2c), (3), (4), (5), (6), (7), (8), plus three for the extra step rows (checkout missing,
  worktree blocked, `checkout -B` failing). Each asserts holds and
  `cli._results_rc(results, holds=holds)`.
- `template/tests/test_flow_dependency_scoped_bases.py:503-545`: two cases asserted the old
  `STOPPING` at a base. They now assert the hold. One holds map gains `"C": "base"`, and one
  now expects the end-of-run report of A, which used to be suppressed by `stop_named`. That
  file has no exit-code assertions.
- `template/tests/test_integrate_carried_rewrite_late.py:34-37, 207-213, 293-312, 350-372`:
  same change (`_stopped_at_b` became `_held_at_b`). Both `rc == 1` assertions are
  unchanged. Iteration-v4's flip of (1d) to 3 is not repeated (decision 2). (1d) now
  expects the rewrite to be named twice: once on B's hold line and once by the end-of-run
  check.

## Ruled out, with the cost

1. **Keeping `stop_named` with a rewritten comment** (the brief says to rewrite that
   comment). After this change its only `add` sits in a handler for
   `IntegrationTreeError`. `_Rewritten` is not one: both subclass `IntegrationError`
   directly (`integrate.py:101`, `:126`). So the set is always empty, and the filter at
   `flow.py:2914` never filters. Keeping it would leave 3 dead code lines plus a 2-line
   comment describing a case that cannot happen. Removing it is −5 lines. The brief's aim
   (a hold does not take the member out of the end-of-run check, and no comment claims it
   does) holds either way. The `_Rewritten` docstring was rewritten as asked.
2. **New exception classes for the fetch / no-checkout causes in integrate.py**
   (iteration-v4's `_NoCheckout`, `_FetchFailed`, and its `_prepare_worktree` try/except,
   about +40 lines in integrate.py). Out of scope: the brief limits integrate.py to the
   `_Rewritten` docstring. The flow-side prefix match on `exc.cause` is what the brief asks
   for. Drift is caught: if `_fetch`'s cause text changes, case (3)'s full-phrase assert
   goes red.
3. **Fixing only the fetch cause.** Then "checkout not found at X", "could not create the
   integration worktree at X" and "could not start <branch> off origin/main" would print
   with no fix at all, against the invariant ("every hold message names the cause and a fix
   that works for that cause"). The extra rows cost 8 lines of table. Each row is pinned by
   a test that also asserts the line does not say "check the remote". One prefix is not
   tested directly: "could not read the folded tip in" (`pushed_tip`, `integrate.py:214`).
   Failing that one `rev-parse` only after the merges would need a stub on
   `subprocess.run` keyed on call order, not on a git call. It shares its row's step with
   the tested "could not start" prefix.
4. **Folding after a wave whose every bundle was held** (instead of v4's `continue`). Cost:
   a fold, plus a re-gate if `regate_between_waves` is on, over an unchanged line. It would
   also break the existing rule that a wave with nothing to build does not fold
   (`flow.py:2714-2715` skips the fold the same way). What I gave up: in that corner the
   next-fold warning refers to a later wave's fold, or to none (then the end-of-run check
   reports the rewrite and the run exits 1). The warning stays true as a statement of what
   the next fold does.
5. **Stopping on `_LineBroken` too** (the carry treats it like a tree error,
   `integrate.py:645-646`). The brief keeps the stop "for that class alone". It is also
   safe to hold: every later base build and every fold starts with `_reset_tree` +
   `checkout -B` (`integrate.py:851-852`, `:593-595`). A base branch left on a trial commit
   cannot leak into the next user of the tree, and a tree that really cannot be reset
   raises `IntegrationTreeError` there, which stops the run.
6. **A rule-1 exemption limited to PLANNED keys.** I keyed it on the `holds` entry alone.
   A base-held bundle is never driven, so its state is whatever in-flight state it entered
   the wave with: PLANNED when fresh, possibly AWAITING_SIGNOFF etc. on a resumed run. With
   the entry as the key, such a resumed hold is also exit 3 ("only holds left ⇒ 3",
   decision 4). It still meets the brief's sentence: PLANNED is not in `ok`, so a PLANNED
   key passes only through the `"base"` entry. Cases (5) and (7) pin that a PLANNED
   dependent or partner with no entry gives 1.
7. **The rest of iteration-v4** that the existing end-of-run check covers: `_report_stale_prs`,
   `_note_base_rewrites`, `_BaseRewrite`, `base_rewrites` (+ its `.clear()` after a fold),
   `integrate.lost_now`, `_Rewritten.ref/.prs`, the `:853` message change and the
   `IntegrationError` docstring change. All dropped. v4's flow.py diff was +200/−49; this
   one is +154/−44 including the new wording table.
8. **A separate reporter for case (6).** Not needed. `S` (`Stacks on: A`) is a seam, so
   `_bundle_bases` records `line_cut[S]` with A's carried head (`flow.py:1028`).
   `_heads_taken` (`flow.py:1037-1049`) turns that into `line_prs[issue_A] = [(issue_S,
   head)]`. `rewritten_carried` (`integrate.py:1257-1266`) then passes it to
   `_late_line_rewrite` (`integrate.py:1285-1289`), whose line names "(issue_S): they hold
   commits origin/fix/A no longer has". Case (6) asserts that line.
9. **Case (8) stub point.** The brief names `integrate._reset_tree`. I failed the `git
   reset` call inside it (`integrate.py:2003-2004`) while `build_bundle_base` runs for
   issue_B, so the real `_reset_tree` raises its real `IntegrationTreeError`
   (`:2005-2008`). The effect and the window are the same; the raise is production code,
   as in cases (3) and (4).

## Refute-your-own-test

- **(a) Genuine red? Yes.** Run through the project's C4 runner
  (`engine/scripts/run-verify.sh`, with `PDCA_BUNDLE` / `PDCA_WORKTREE` set, under
  `timeout`). It reverted the production hunks and re-ran all three test files.
  - New file: 12 of 13 failed. The one that passed is
    `test_a_shared_worktree_that_cannot_be_reset_still_stops_the_run`, case (8), the
    brief's deliberate guard that passes on both legs.
  - The two edited existing files: 2 failures each (the edited cases).
  - Every red-leg failure is the old behaviour: `'STOPPING' unexpectedly found in "flow:
    wave 1 — could not build issue_B's own base from issue_A: …"`. For (2c) it is "no
    `issue_B held` line", because the run stopped first.
  - Verdict printed: `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`.
- **(b) Production path? Yes.**
  - The tests call `flow._drive_and_act` and `cli._results_rc` unmodified, so the changed
    production code runs: `_bundle_bases`, `_base_hold_why`, `_announce_base_holds`,
    `_runnable`, the wave loop and rule 1.
  - Real git runs the real `integrate.build_bundle_base`, `_prepare_worktree` / `_fetch`,
    `_reset_tree`, the folds and the end-of-run `rewritten_carried`.
  - Stubbed, as in the peer suites: the build/sign-off leaves (`flow._drive_wave`), publish
    mechanics (`flow._publish_bundle`, `publish.draft_texts`) and `gh`.
  - `integrate.fold` and `integrate.build_bundle_base` are wrapped call-through, only to
    count folds, run hooks and mark B's build window.
- **(c) Fixture includes the fault? Yes.** Every fault is real or is a failing git call:
  - Real git state: `main` moved and clashing (1); `fix/A` force-pushed (2, 2b, 2c, 6);
    the checkout really moved away; a plain directory really sitting at the worktree path.
  - A git call returning non-zero only while issue_B's base is built: fetch (3, 5, 7), the
    push of B's base branch (4), `reset` (8), `checkout -B`. In each case integrate's own
    raise fires with its own text.
  - B, its dependents and partners, and the unrelated W are all in the run. Nothing is
    curated out.

## Runs

- The brief's nine listed suites: OK on `75a886e` before the change (161 tests). With the
  production change alone, 4 cases in the two edited files failed (they asserted the old
  `STOPPING`); with their edits, all nine plus the new file are OK.
- Full offline driver suite, `cd template && PYTHONPATH=src python3 -m unittest discover -s
  tests`: `Ran 2607 tests … OK (skipped=2)`.
- Root template suite (`python3 -m unittest discover -s tests` at the target root, copier
  9.17.0 importable): `Ran 24 tests in 83.022s … OK`, none skipped, so the render and
  update-compat cases really ran.
- C4 (`engine/scripts/run-verify.sh`): PASS, as above.

## Commit-ready

The target configures no formatter, linter or commit hook: no `.pre-commit-config.yaml`, no
ruff/black/flake8 config in `pyproject*`, no `core.hooksPath`, and only `*.sample` files in
`.git/hooks`. CONTRIBUTING.md asks for a DCO sign-off (`git commit -s`), which publish adds,
and a green offline suite (done). Every added line is ≤ 100 characters, matching the files'
existing wrap. All three modules pass `py_compile`.

## For the human at sign-off

- In runs like case (2) and case (6) the rewrite of `fix/A` is named twice on stderr: on
  B's hold line (why B was not built) and by the end-of-run check (what the line and the
  PRs still hold). The brief says this is intended (decision 2).
- `IntegrationError`'s docstring (`integrate.py:85-94`) still says "The caller STOPs". That
  is true for the fold, but `build_bundle_base` raises the same class and is now held. I
  left it, since the brief limits integrate.py to `_Rewritten`'s docstring; worth a line in
  #740's docs pass.
- No external dependency was missing. No NEEDS-HUMAN item from Do.
