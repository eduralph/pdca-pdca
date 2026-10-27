## Summary
**User impact:** A `pdca flow` run in stack mode can leave an accepted fix off the
branch it builds, and still exit 0. The run lists that fix as COMPLETE, and the only
warning is one line on stderr. A script or CI job that checks the exit code sees a
clean run, while one fix's work is missing from the result.

This PR makes such a run exit **3** ("finished, but something was held back"), so the
exit code alone shows it. A run with a failed bundle still exits 1, and a clean run
still exits 0.

Reported in [#693](https://github.com/eduralph/pdca-harness/issues/693).

## What to look at
- The exit-code rule in the CLI, and the small hand-off that tells the CLI which
  bundles the run held back. Nothing about *which* bundles get held, or what is printed,
  changes.
- To try it: set up two bundles in the same wave that edit the same line of a file,
  plus a third bundle, and run `pdca flow` over them with publishing on. On `main` the
  run exits 0 even though stderr says `issue_11 held out of the integration fold`. With
  this PR it exits 3. The new test file does exactly this against a real local git
  remote.
- `pdca flow --help` now lists the exit codes 0 / 1 / 2 / 3.

## Root cause
The flow exit code comes from one rule over the results map: 0 if every bundle reached
COMPLETE (or RESOLVED). A held bundle *is* COMPLETE (built, signed off, published; only
the fold left it out), and the drive returned nothing but `{id: state}`, so the CLI had
no way to know a hold happened.

## Fix
- `flow._drive_and_act` takes an optional keyword-only `holds: dict[str, str]`
  collector. At the end of the run it fills it with `{id: "unpushed"}` for the #593
  hold and `{id: "conflict"}` for the #674 hold. `flow_ids` and `flow_batch` pass it
  through. Return types are unchanged, and the default `None` leaves every existing
  caller alone.
- `cli._flow` creates the collector and hands it to `_report_single` / `_report_batch`,
  which pass it to `_results_rc`. New precedence: unfinished bundle → 1; else any hold →
  3; else 0. The single-id shape keeps AWAITING_SIGNOFF as success.
- Docs: the rule is in `_results_rc`'s docstring, in the `flow` subcommand's help epilog,
  and in a new paragraph after the stack-mode hold paragraphs in
  `docs/07-crosscutting.md`.
- One existing test spy (`test_flow_single_driver.py`) took only `results`. It now
  forwards any extra arguments.

Out of scope: an accepted bundle in the last (or only) wave that pushed no branch. No
fold runs after it, so it is never held, and the run still exits 0. Merge mode and
dry-run runs hold nothing and are unaffected.

## Verification
Line numbers on `main` @ `d6057eb` unless marked "post-patch".

- **Claim:** a run that finished every bundle but held one exits 3; an unfinished bundle
  still wins with 1; a run with no hold still exits 0.
  - **Checked:** `template/src/pdca_harness/cli.py:679-690` — the old rule returned 0
    for any all-COMPLETE map. Post-patch `cli.py:717-719` checks "not all ok → 1" before
    "holds → 3".
- **Claim:** both holds reach the CLI.
  - **Checked:** `template/src/pdca_harness/flow.py:2295` (`held_unpushed`, filled at
    `:2518-2525`) and `:2300` (`held_conflict`, filled at `:2529-2546`). Post-patch
    `flow.py:2581-2585` copies both into `holds` after the end-of-run report, keyed the
    same way as the results map, so a run that stops early still reports holds made
    before the stop.
- **Claim:** all three CLI routes carry the signal.
  - **Checked:** `cli.py:638-640` (`--from-csv` → `flow_batch`), `:655-657` (ids →
    `flow_ids`), `:671` (single vs. batch report); `flow.py:2671` and `:2824` (the two
    `_drive_and_act` calls).
- **Claim:** no existing caller changes.
  - **Checked:** the return type of `_drive_and_act` / `flow_ids` / `flow_batch` stays
    `dict[str, str]`; the only callers in `src/` are the ones above.
- **Test:** `template/tests/test_flow_hold_exit_code.py` (new, 8 cases). Each one runs
  the full `cli._flow` route against a real bare git origin with real folds, and only
  the build, sign-off, publish and `gh` steps stubbed.
  - Fail before the fix (`0 != 3`), pass after: #674 hold (batch), #593 hold (batch),
    #674 hold via `--from-csv`, #674 hold with a single id over a split parent, and the
    same with the last child waiting for sign-off.
  - Pass both before and after (controls): no hold → 0 (batch and single id), and a
    held bundle's dependent left unbuilt → 1.
- **Suites:** the offline suite is green (root 24 OK, driver 2467 OK, 2 skipped), and
  the docs lint, site render and link audit are clean.

Fixes #693
