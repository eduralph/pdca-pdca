# Build notes — #747 (hold a single-partner cross-wave clash at the line fold)

Target: eduralph/pdca-harness, built on the run's line `pdca-integration/main-r547f8028520f`
at `9f7c446` (#738 folded). All `path:line` anchors below are on that tree **with the patch
applied** unless marked "base".

## What changed

### `template/src/pdca_harness/integrate.py`

- `fold` gets one new keyword-only argument, `line_heads` (`integrate.py:366`): per target
  `(repo, base)`, finished id → the head the pre-wave carry folded. Documented at
  `integrate.py:509-512`. It is used **only** as extra partner candidates. It is never merged,
  never put in `took`, and never in `carried`, so the #633/#695 rewrite checks
  (`_carried_tips`, base `integrate.py:533`) are unchanged.
- The conflict branch of `fold` (base `integrate.py:640-647`, now `:656-673`): it still tries
  `_held_by` first (same-wave, #674). It no longer requires `kept` to be non-empty before
  trying. When `_held_by` gives nothing, it calls the new `_line_partners` with
  `on = [carried finished heads not already taken, present in the clone] + took.items()`, in
  merge order, and records a hold in `held_out` in the same `(partners, paths)` shape.
  `paths` are the files the failed line merge left conflicting (`exc.paths`).
- New `_line_partners` (`integrate.py:1800`). It is **not** a second classifier. It calls
  `_built_on` and `_clash` (base `:1774`) as the carry does at base `:688-706`, and
  continues only on kind `"batch"`. `_clash` already does rule (b) (its `"base"` trial) and
  rule (c) (`_partners`, base `:1821`). Then it runs one new trial for rule (e). A git step
  that fails gives `None` (the fold raises the conflict as before). A broken tree still
  raises.

### `template/src/pdca_harness/flow.py`

- `_fold_lines` gets `line_heads` and passes it to `fold` (`flow.py:1160`, `:1196`; docstring
  `:1169-1185`).
- `_carry_finished` gets `line_heads` (`flow.py:1364`, docstring `:1414-1417`). The carry's
  `_fold_lines` call now passes a local empty `carried=put` (`flow.py:1468-1473`), so `fold`
  reports back the exact head it put on the line for each carried id (base
  `integrate.py:724-725`: `carried.update(took)` after the push). An empty dict is falsy, so
  `_carried_tips` (base `integrate.py:533-534`, `if carried and not dry_run`) still checks
  nothing. The record is written only when the carry's line is used (not red, target folded:
  `flow.py:1495-1498`).
- `_drive_and_act`: a run-level `finished_heads` (`flow.py:2809`) is filled by the carry
  (`:2814`) and passed into the in-run fold (`:3041`). The held bundle goes into
  `held_conflict`, which `_runnable` already honours (`set(held_conflict)` in `held=` and
  `conflict_held=`), so its dependents are skipped and its `Conflicts with` partners are held
  without any change to `_runnable`.
- New `_own_prereqs` (`flow.py:1545`): which partners the held bundle's brief declares as
  prerequisites (`waves.declared_deps`, resolved with `cfg.find_bundle`, as `_runnable` does).
- `_announce_conflict_holds` (`flow.py:1555`) now takes `cfg`, `wave` and `finished`. If every
  partner is in the wave just published, the wording is the same as before ("merged before it
  in the same wave k"). If every partner is a carried finished id, it says "already on the
  line, finished in an earlier run and carried before wave 0". Otherwise it says "already on
  the line from an earlier wave". A partner that is the held bundle's own prerequisite adds
  "to fold it, rebuild X's branch on P's".
- `_report_conflict_holds` (`flow.py:1579`) now takes `cfg`. Prerequisite partners get "To fold
  it, rebuild X's branch on P's, then re-run."; any other partners get the existing
  `_CONFLICT_STEP` proposal. The `Conflicts with` proposal is never made for a prerequisite.

## Deviation from the brief: one clause of rule (e) — please weigh this at sign-off

The brief says: "If any remaining line bundle was built on a partner (`_built_on`'s `under`
names a partner's commit for it) … (e) counts as failed and the run stops." **Applied
literally, this clause makes two of the brief's own success cases stop:**

- **Case (4), the flip**: 20 (`Depends on: 10`) is on the line and its head holds 10. So
  "the line without 10" still contains 10 through 20, and the run stops.
- **Case (2)**: Z (`Depends on: F`) is on the line and its head holds F. Same thing.

I checked this. I put the literal clause in (`return None` if any non-partner on the line holds
a partner's head) and ran the two files: `test_a_clash_with_a_finished_bundle_carried_onto_the_line_names_it`
and `test_a_conflict_with_its_own_prerequisite_on_the_line_holds_it` both FAILED (they stopped).
Then I restored my version.

What I built instead (`integrate.py:1828-1832`): for rule (e), a line bundle whose head holds
a partner's head is left out of "the line without them", together with the partner. This is
the same rule the fold already uses for #672 (`_hold_work`: a bundle holding left-out work
comes off with it). It does not hide a clash from that bundle's **own** change. Every bundle in
`on` has already been through `_partners`, which judges a bundle built on another by its own
change (`below` + `wins`, base `integrate.py:1840-1844`). If its own change clashed with the
head, it would have been named a partner. What this can miss is a clash that only appears
when that bundle's own change and others combine. That is joint attribution, which is
child-2's (#748) scope. The docstring says so (`integrate.py:1815-1819`, comment at `:1832`).

The brief allows that "child-2 may refine this". I chose the Success criterion (the real end
result) over the clause that contradicts it. If the human wants the literal clause, cases (2)
and (4) cannot be held by this child.

## Rule (d) is already enforced by `_partners`; no separate trial

Rule (d) says every named partner's own head must merge cleanly onto the base alone. In
`_partners` (base `integrate.py:1837-1839`), the first trial for each candidate is
`_trial(base_ref, [its, head])`, and a partner is named only when `at == 1`. That means
`its` merged cleanly onto `base_ref` at index 0, which is exactly rule (d), on the same ref
and in the same tree with no fetch in between. A separate `_trial(base, [partner head])`
could never fail. So I did not add it (cost: one redundant git merge per partner per hold),
and the docstring explains why (`integrate.py:1813-1814`). The practical result: a partner
whose head no longer fits the base is never named. `_clash` then gives `"line"` (or
`"moved"`), and the run stops. `test_a_clash_with_a_partner_whose_head_no_longer_fits_the_base_still_stops`
checks exactly that.

## Stop guard for rule (e): fixture choice

`test_a_clash_two_line_bundles_cause_only_together_still_stops`. A pure P+R
"together only" clash, like the reference file's case, gives `_partners` = {} and so stops
at rule (c) (kind `"line"`), not rule (e). To make the test fail **rule (e)** as the brief
names it, H also clashes with A alone (both add `other.txt`). So `_clash` names A, rule (c)
passes, and the line without A (K, P, R) still does not merge H. The fixture facts are
asserted in the test (`_merges(main, A, H) == 1`, P and R alone clean, `K, P, R, H` → 3).
child-2 flips this into a hold naming A, P and R.

For the rule-(d) guard I made V `Stacks on: W` (as the reference file did). My first version
had `V depends_on W`, and V's own base also held main's moved `a.txt`, so the fold stopped on
V before reaching Y. That made the test pass for the wrong bundle.

## Tests that flip (before → after)

Full offline suite with the patch: `cd template && PYTHONPATH=src python3 -m unittest
discover -s tests` → `Ran 2614 tests … OK (skipped=2)`. Only one existing test flips:

- `test_flow_same_wave_conflict.py::test_a_conflict_with_earlier_wave_work_still_stops_the_run`
  (before: asserted `wave 1 did not integrate`, `STOPPING`, no hold for 21) → renamed
  `test_a_conflict_with_its_own_prerequisite_on_the_line_holds_it` (after: 21 held, fold-time
  line has `issue_10`, `(conflicts in shared.txt)`, `rebuild issue_21's branch on issue_10's`;
  the whole stderr has no `Conflicts with: 10` and no `same wave`; 30 not built and PLANNED; no
  `STOPPING`; holds `{"21": "conflict"}`; exit 1). That file's `_run` now passes
  `holds=self.holds` and computes `self.rc = cli._results_rc(...)`. No other test in it
  reads those, so the other 7 cases are unchanged and still pass.
- `test_a_conflict_only_with_a_base_taken_in_mid_wave_still_stops_the_run` is unchanged and
  still prints `STOPPING`. 22 conflicts with `origin/main` itself, so `_clash` gives `"base"`.

No other test pinned the old `_announce_conflict_holds` / `_report_conflict_holds` signature.
`test_flow_hold_exit_code.py` only matches the phrase `held out of the integration fold`,
which is unchanged.

## Actual stderr (from the hold cases)

```
flow: issue_Y held out of the integration fold — its change conflicts with issue_A's, already on the line from an earlier wave (conflicts in shared.txt); bundles that depend on it or are its `Conflicts with` partners are held this run.
flow: issue_Y was held out of this run's integration line — its change conflicts with issue_A's (shared.txt). Proposed, for you to confirm: declare `Conflicts with: A` in issue_Y's brief, then rebuild issue_Y on a base that holds issue_A.

flow: issue_21 held out of the integration fold — its change conflicts with issue_10's, already on the line from an earlier wave (conflicts in shared.txt); issue_10 is its own prerequisite: to fold it, rebuild issue_21's branch on issue_10's; bundles that depend on it or are its `Conflicts with` partners are held this run.
flow: issue_30 skipped — prerequisite(s) not ready (21); not built on a base missing them.
flow: issue_21 was held out of this run's integration line — its change conflicts with issue_10's (shared.txt). To fold it, rebuild issue_21's branch on issue_10's, then re-run.
```

Case (2) prints "… conflicts with issue_F's, already on the line, finished in an earlier run
and carried before wave 0 (conflicts in shared.txt) …" and proposes `Conflicts with: F`.

## Refuting my own test

- **(a) Genuine red? Yes.** `./engine/scripts/run-verify.sh` with `PDCA_BUNDLE` /
  `PDCA_WORKTREE` set. Green leg: both test files OK (4 + 8 tests). Red leg, production hunks
  reverted: case (1), case (2) and the flip FAIL, each on `'did not integrate' unexpectedly
  found` (the run printed `wave 1 did not integrate … STOPPING`).
  → `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`. The two stop guards are
  meant to be green on both legs: they pin stops this child must keep. Separately, I
  disconnected only the case-(2) route (`line_heads=None` at `flow.py:3041`) and case (2)
  went red with `wave 1 did not integrate (issue_Y'…`. So the carried-heads route is needed,
  not incidental.
- **(b) Production path? Yes.** Every case calls the real `flow._drive_and_act`, which calls
  the real `_carry_finished`, `_fold_lines`, `integrate.fold`, `_held_by`, `_clash`,
  `_partners`, `_built_on`, `_trial`, `_runnable`, `_announce_conflict_holds` and
  `_report_conflict_holds`, on real git (a bare origin plus clones). Only the build/sign-off
  leaf (`_drive_wave`), publish's push (`_publish_bundle`, which really cuts and pushes the
  branch), `draft_texts` and `gh` are stubbed, the same way as
  `test_flow_same_wave_conflict.py`. The exit code comes from the real `cli._results_rc`.
- **(c) Fixture includes the fault? Yes.** The clashing branches really conflict in git (the
  red leg shows the real fold raising on them). The partner is really on the line: A is folded
  in wave 0; F is really carried by `_carry_finished`, and the test asserts the "carried
  issue_F … onto" line; 10 is really on the line. The unrelated chain (`U`, `Z`) is really
  built, and the test asserts COMPLETE. Neither guard curates out the fault: the (e) guard
  asserts the fixture facts with real merges in a scratch clone, and the (d) guard really
  moves main after the first fold and asserts `_merges(origin/main, A) == 0`.

## Commit-readiness

The target has no pre-commit config, formatter or linter config (no
`.pre-commit-config.yaml`; no ruff/flake8/black in `pyproject.toml.jinja` or the workflows).
Added lines keep to the code's 100-column width (checked by character count on
`patch.diff`), and `py_compile` passes. Publish adds the DCO sign-off when it commits.

## Housekeeping

I left an untracked scratch copy, `.integrate.keep`, at the worktree root. I used it to
restore `integrate.py` after the literal-clause experiment. It is **not** in `patch.diff`
(the diff covers `template/` only). The harness reclaims the worktree.
