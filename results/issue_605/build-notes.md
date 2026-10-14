# Build notes — issue 605 / check-decorrelation-note-not-deferred (iteration 2)

Target: `eduralph/pdca-harness` `main`. The worktree (`$PDCA_WORKTREE`) is at `41210bc`. That
commit is newer than the brief's `b5f5c29`, and it already contains #603 (`355b4ee`, merged as
`30b7941`). Every production line the brief cites is at the same number on `41210bc`
(`assemble.py:47-53`, `:404`, `:405-409`; `autoiterate.py:300-326`; `flow.py:379-383`;
`leaves.py:3637-3642`, `:3655`, `:3675`; `state.py:155`), so no citation moved. Below, "base"
means `41210bc` and "patched" means the tree after `patch.diff`.

## The carry-forward, addressed

Iteration 1 was sent back for one IMPL finding. The new test class sat *after*
`if __name__ == "__main__": unittest.main()`, so running the file as a script exited before
the class was defined, and its tests were silently skipped.

- The class `CheckDecorrelationNoteIsNotDeferred` now sits at patched
  `template/tests/test_autoiterate.py:2453-2575`. That is after #603's
  `PlanAdvisoryTickSurvivesIterateDo` (`:2295-2450`) and before the guard, which moved from
  base `:2452` to patched `:2578`.
- Proof: `python3 tests/test_autoiterate.py` (script mode, from `template/`, `PYTHONPATH=src`)
  now runs **148 tests, OK**. That is the same count the module-mode runner gets.
  `python3 tests/test_autoiterate.py -v CheckDecorrelationNoteIsNotDeferred` runs the 3 tests
  as `__main__.CheckDecorrelationNoteIsNotDeferred.*`, all OK. These two runs were direct
  invocations wrapped in `timeout`. The project's runners load the module by name
  (`python -m unittest tests.test_autoiterate`), so they never hit the script-mode case.

The 5 deferred HUMAN findings in `deferred-findings.json` (T5 prior art, plus four
plan-review findings the brief's "Plan-review response" already answers) are for the human
at handover, not build work. I did not act on them.

## What changed and why

The Check-side decorrelation note (`check-advisory-decorrelation.md`, written by
`leaves._decorrelation_note`, base `leaves.py:3637-3642`) was read by
`assemble.collect_needs_human` as an ordinary advisory finding: HUMAN, `no_verdict=False`.
`autoiterate.deferrable` (base `autoiterate.py:300-326`) only skips `no_verdict` rows, so the
note went into the ledger. `assemble._deferred_needs_human` (base `assemble.py:654-683`) then
put it back into every later §6, even after a later round's selection worked and wrote no note.

1. **The fix:** patched `template/src/pdca_harness/assemble.py:408-420`. In the advisory loop
   of `collect_needs_human` (base `:405-409`), the items read from the artifact whose stem is
   `decorrelation` are marked after the fact with `it._replace(no_verdict=True)`. This copies
   the peer the brief cites: the missing-review placeholder at base `assemble.py:402-404`. The
   row stays HUMAN, so it still renders in §6, still blocks accept (C6), and still never
   *causes* a rebuild. The only readers of `no_verdict` are `autoiterate.deferrable` (patched
   `autoiterate.py:325`) and the flow notice count (`flow.py:379`). So the only behaviour
   change is that the note is no longer deferred, and the notice counts it as a row about
   this Check's own run.
2. **Field meaning widened:** patched `assemble.py:47-55` (base `:47-52`). The
   `NeedsHumanItem.no_verdict` comment now reads "a row about this Check's own run": a review
   or gate with no verdict, OR the note on this Check's advisory selection (#605).
3. **`deferrable` docstring:** patched `autoiterate.py:309-316` (base `:307-313`), widened the
   same way.
4. **Module docstring:** patched `autoiterate.py:23-28` (base `:23-26`). This spot is not
   named in the brief's Scope. But it described `no_verdict` in the old narrow terms ("One
   kind of HUMAN row is not deferred: a review or a gate that gave NO verdict"), which would
   contradict the code after the change. The brief says the field's "docstrings are updated
   to match".
5. **Flow notice:** patched `flow.py:382-383`. It now says "N row(s) about this Check's own
   run left for the next Check to re-check" (the brief's suggested wording), not "review/gate
   row(s) with no verdict … re-run".
6. **User docs:** patched `docs/07-crosscutting.md:464-468`. The auto-iterate section (base
   `:458-464`) is the user-facing statement of which HUMAN rows are not deferred. It said
   "One kind … a review or a gate that gave *no verdict*". I added one sentence covering the
   decorrelation note, so the docs match the code. This is also outside the three spots
   Scope names, for the same reason as item 4. I left the `template/pdca.toml.jinja:66-68`
   comment alone. It says "A review or gate that gave no verdict … is not held", which is
   still true and does not claim to be the full list. It is also rendered into every
   instance's `pdca.toml`, so editing it would show up in every instance's `copier update`
   for no correctness gain.
7. **Existing test:** `test_autoiterate.py:766-767` (base `:766`). The #409 test
   `test_a_review_or_gate_that_recovered_needs_no_clearing_at_handover` asserted the old
   notice text. Its assertion now checks the new text. The behaviour under test is the same.

No new flag. The brief chose to widen `no_verdict`. The mechanism the rule rests on already
holds for the note. An iterate archives `check-advisory-*.md` (`state.py:155`, through
`driver._archive_iteration`). Every Check under `vendor-complement` re-runs `_select_advisory`,
which unlinks the old note (`leaves.py:3655`) and writes it again only if decorrelation still
fails (`:3675`). So a note in the bundle always comes from this round's Check.

## The test

Patched `template/tests/test_autoiterate.py:2453-2575`, class
`CheckDecorrelationNoteIsNotDeferred`. A copy of the whole file is at
`results/issue_605/template/tests/test_autoiterate.py`.

- `_round1` (`:2480-2500`) builds a stub bundle with a C4 IMPL row (`_IMPL_ONLY_REVIEW`). The
  config is `vendor-complement` with one advisory leaf of family `codex`, and there is no
  `loop-telemetry.json` (asserted). It then runs **Check's real advisory step**,
  `leaves.run_advisory_leaves`. That calls `_select_advisory`, which writes the note
  ("builder family … unknown"), and the stub advisory leaf, which writes one ordinary HUMAN
  finding. It assembles, asserts round 1's §6 shows the note once, runs
  `autoiterate.write_decision(d, collect_needs_human(d, cfg))` and `flow._apply_decision`
  (→ `iterate-do`), then `driver.advance` (the archive). It asserts the round-1 note file is
  gone after `driver.advance`, so the premise is checked, not assumed.
- `_round2` (`:2502-2510`) runs `driver.run_issue`: stub Do, real gates, real
  `run_advisory_leaves` → `_select_advisory`, and real assembly. Only `leaves.run_review` is
  replaced by a clean review, as the existing #409 test does (`:735-760`).
- **Criterion (1)** (`:2521-2536`): `loop-telemetry.json` records builder family `claude`, so
  round 2's selection picks the `codex` complement and writes no note (asserted). Round 2's
  §6 has no row with the note text, `autoiterate.deferred(d)` does not hold it, and
  `accept_blockers` does not list it. It also asserts that round 1's *ordinary* advisory
  finding **is** in the ledger. So the fix keys on the note alone and does not stop other
  advisory findings from being deferred.
- **Criterion (2)** (`:2538-2558`): round 2 again has no telemetry, so round 2's own
  `_select_advisory` writes the note (asserted). §6 shows it **once**, as `- [ ] …`, and the
  ledger does not hold it. With every other row ticked, `accept_blockers` is exactly that row
  and `flow._apply_decision(accept)` returns `blocked`. After the human ticks it, the same
  accept goes through (`COMPLETE`). That is the invariant's "shows it until the human clears
  it".
- **Criterion (3)** (`:2560-2575`): `flow._maybe_auto_iterate` on a round with the note plus
  an IMPL row. The notice has no "with no verdict", says "; 1 row(s) about this Check's own
  run left for the next Check to re-check", and says nothing is deferred. No ledger is
  written.

Only pre-existing API is called, so on the red leg the module loads and fails on the
behaviour, not on an import.

## Red → green, through the project's runners (each wrapped in `timeout`)

- **C4, `engine/scripts/run-verify.sh`** (`PDCA_BUNDLE=results/issue_605`,
  `PDCA_WORKTREE=…-wt-l0`), on the final `patch.diff`: `PDCA-EVIDENCE: C4 PASS — red without
  the fix, green with it`.
  - Green leg: `tests.test_autoiterate`, 148 tests, OK.
  - Red leg (production hunks reverted, test kept): 148 run, 7 failures. These are the 3 new
    tests plus the 4 subcases of the #409 notice assertion. Each fails for the reason it
    should:
    - Case 1 is the RED the brief names: round 2's §6 holds `- [ ] advisory reviewer
      'adversary' could not be decorrelated from the builder — the builder family that ran
      is unknown (no loop-telemetry.json); …`, carried from the ledger.
    - Case 2: the ledger holds the note.
    - Criterion 3: the notice says "1 finding(s) needing human judgment deferred to handover".
    - The 4 #409 subcases: the notice says "1 review/gate row(s) with no verdict … re-run".
  - Afterwards the worktree diff was byte-identical to `patch.diff` (`cmp`).
- **T3, `engine/scripts/run-suite.sh`**: root suite 24 tests OK (copier present, not
  skipped). Driver suite 2426 tests OK (2 skipped).
- **T2, `engine/scripts/run-docs-check.sh`**: docs lint clean; site render + link audit clean
  (22 pages).
- **Mutation check** (temporary edit, restored, confirmed with `cmp` against `patch.diff`): I
  moved the check into the `no_verdict=` lambda, the placement the brief warns about. All 3
  new tests failed. This confirms the brief: `_items_from_artifact` only calls that callback
  for a text with a leaf-status marker (base `assemble.py:374`, `:380-382`), and the note has
  none (`leaves.py:3641-3642`).

## Refuting my own test

- **(a) Genuine red? Yes.** With the production hunks reverted by the project's C4 script, all
  3 new tests fail, for the reasons quoted above. With the fix, they pass. The wrong-placement
  mutation also leaves them red.
- **(b) Production path? Yes.** The note is written by the real writer chain
  (`run_advisory_leaves` → `_select_advisory` → `_decorrelation_note`) in round 1, and in
  round 2 for case 2. The criterion-3 test calls `_select_advisory` directly. The decision goes
  through `autoiterate.write_decision` + `flow._apply_decision`, and the iterate through
  `driver.advance`. Round 2 goes through `driver.run_issue`, §6 through
  `assemble.assemble_summary`, C6 through `flow.accept_blockers` + `flow._apply_decision`, and
  the notice through `flow._maybe_auto_iterate`. The only stand-in is the clean review from
  `leaves.run_review`, a leaf the fix does not touch. The Do leaf is the stock stub, which is
  also not under test.
- **(c) Fixture includes the fault? Yes.** Round 1 really has no `loop-telemetry.json`
  (asserted), and the real writer emits the note beside a real C4 IMPL row. Ledger, archive
  and re-selection are all real, and the note's absence after the iterate is asserted, not
  assumed. Case 2 keeps the fault live in round 2 through the real writer, not a hand-written
  file. Case 1 also has an ordinary advisory finding in the same round, so a fix that dropped
  every advisory row would fail it.

## Ruled out

- **A predicate in the `no_verdict=` lambda** (base `assemble.py:409`). It is never called for
  the note, as shown by the mutation run above.
- **Matching on the note's text.** The brief says to key on the artifact. A text match breaks
  the day someone rewords the note.
- **A new `NeedsHumanItem` field.** The brief chose to widen `no_verdict`. A new field gives
  the same behaviour with more code: a second skip in `deferrable` (`autoiterate.py:325`), a
  second count in the notice (`flow.py:379`), and a second docstring.
- **A shared constant for the `"decorrelation"` stem** (iteration 1's advisory review called
  it optional). Cost: +1 line in `assemble.py` for the constant, the check at `:413` using
  it, and 2 changed lines in the writer, `leaves.py:3641` and `:3655`. That is about 4 lines,
  and it touches the writer, which the brief keeps out of scope. I did not do it, for three
  reasons. The invariant does not need it. The new tests already tie the writer's stem to the
  reader: if `_select_advisory` wrote under another stem, cases 1 and 2 would go red. And the
  codebase's convention for this stem is the literal, used on the plan side too
  (`leaves.py:3840`, `:3853`, `:3918`, `:4273`), so a Check-only constant would cover half of
  it.
- **Also requiring `advisory_selection.mode == "vendor-complement"`** before marking. Cost:
  one more condition. But a note in the bundle always comes from this round's Check (archive
  + unlink, above), so the guard changes nothing for a real note. It would also add a config
  read to classification, and if the mode were switched off between a Check and a
  re-assembly, a real note would become deferrable again.
- **The plan-side note** (`_plan_decorrelation_note`, `leaves.py:3838-3841`). Out of scope,
  and its carry is #603.

## Known limit (pre-existing, not addressed)

A user-configured `[[leaves.advisory]]` entry with `id = "decorrelation"` would write the
same file name as the note (`advisory_artifact`, `leaves.py:3554-3556`). After this patch its
real findings would also be marked `no_verdict`, so they would never be deferred. They would
still render and still block accept in the round that produced them. The collision itself
already exists: under `vendor-complement`, `_select_advisory` unlinks that file before
selection. Nothing in `config.py` reserves the id. Fixing the naming is part of the
advisory-selection policy, which the brief keeps out of scope.

## Commit-readiness

The target has no formatter or commit-hook config: no `.pre-commit-config.yaml`, and no
ruff, black or flake8 settings. Its CI runs the docs lint + render and the root suite. All of
these pass locally (above). `git diff --check` is clean, and no added line is longer than 100
characters, which matches the files' style. The target requires a DCO `Signed-off-by:`
trailer on the commit (`CONTRIBUTING.md:7-19`); the publish step adds it.

## Housekeeping

- My first C4 run wrote its log to `/tmp/pdca605-verify.log`, outside the harness roots. That
  was a mistake. I did not delete it (harness rule); it is a harmless text file.
- Every later log is under `$PDCA_WORKTREE/.cache/pdca605/`. That path is git-ignored
  (`.gitignore:11`, `/.cache/`) and is not in `patch.diff`.

## Ordering

#603 is already on the base (`41210bc`), so this patch is built on top of it and needs no
rebase. The two edits to `collect_needs_human` are in separate places: #603 is the
plan-advisory fold at `assemble.py:461-462`, mine is the Check advisory loop at `:408-420`. In
the test file, my class follows #603's class.
