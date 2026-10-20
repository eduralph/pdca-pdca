# Build notes — #747 (hold a single-partner cross-wave clash at the line fold), iteration 2

Target: eduralph/pdca-harness, built on the run's line `pdca-integration/main-r547f8028520f`
at `9f7c446` (#738 folded). "base" anchors are on `9f7c446`; every other `path:line` is on
that tree **with this patch applied**.

## What the carry-forward asked, and what changed because of it

Iteration 1 was sent back for one finding (C5): in the reviewer's A→P topology (A adds
`shared.txt`; P `Depends on: A` adds `p.txt`; Y `Depends on: Q` adds its own `shared.txt`),
the patched run held Y and finished the unrelated chain, where the brief's rule (e) says the
run must stop, because P (on the line) was built on the partner A.

Cause: iteration 1 removed every line bundle whose head held a partner from the rule (e)
trial (`iteration-v1/patch.diff`, `_line_partners`, `rest = [... if ... not any(_in_line(...))]`).
With P removed, the trial was `base + Q + W + V + Y`, which merges, so Y was held.

This iteration keeps those bundles in the trial and adds the brief's explicit check, so the
A→P run stops:

- the remainder ("the line without them") keeps every non-partner bundle, in merge order
  (`template/src/pdca_harness/integrate.py:1837`), and the trial is `base + rest + head`
  (`integrate.py:1841-1844`);
- a remaining bundle whose `_built_on` `under` commit holds a partner's head fails rule (e)
  outright (`integrate.py:1838-1840`), as the brief words it.

Both are pinned by new stop tests (see "Refuting my own test" for the mutation runs):
`test_a_clash_with_a_partner_another_line_bundle_was_built_on_still_stops`
(`template/tests/test_flow_cross_wave_fold_holds.py:400`, the reviewer's A→P topology: P on a
base of its own holding A) and
`test_a_clash_with_a_carried_partner_that_a_line_bundle_holds_still_stops` (`:426`, the same
shape through a carried finished partner F and a bundle Z cut from the line that holds F).

## The one judgement call — please confirm at sign-off

The brief contradicts itself, and the contradiction cannot be resolved by commits alone:

- Rule (e): "If any remaining line bundle was built on a partner … (e) counts as failed and
  the run stops (child-2 may refine this)."
- Case (4), the flip: 21 (`Depends on: 10`, cut from the plain base) must be **held** for its
  clash with 10. But the same fixture has 20 (`Depends on: 10`), built on a base of its own
  holding 10, folded before 21 in wave 1. `_built_on`'s `under` for 20 names 10's head. So the
  literal rule stops case (4).

By commit graph, case (4) and the reviewer's A→P case are the same shape: a head cut without
the partner, the partner on the line, another line bundle built on the partner. The only
difference is that 10 is 21's **declared prerequisite**, while A is not Y's. So any rule that
holds case (4) and stops A→P has to read the held bundle's declared prerequisites. I did that:

- `_prerequisites(cfg, d)` (`integrate.py:1852`) = the bundles d's brief names in `Depends on`,
  `Depends on (merged)` or `Stacks on` (`waves.declared_deps`, the same union `_runnable` uses),
  resolved with `cfg.find_bundle`.
- In rule (e), partners split into those prerequisites (`pre`) and the rest (`theirs`)
  (`integrate.py:1834-1836`). The built-on stop applies to `theirs` only. For `pre`, the trial
  is `base + pre heads + head (its side winning every clash with them) + the remainder`
  (`integrate.py:1841-1843`, `_trial(..., wins=len(pre))`): the held bundle is told to rebuild
  on that prerequisite, so the trial simulates that rebuild the way `_partners` already tries a
  bundle on what it was built on (base `integrate.py:1840-1844`), then checks that the rest of
  the line, carriers of the prerequisite included, still takes it.
- The same helper drives the wording (`flow.py:1547` `_own_prereqs`), so the fold's decision
  and the advice can't disagree.

Evidence that this is what decides case (4): with `_prerequisites` forced empty (mutation 2
below), case (4) goes red with `wave 1 did not integrate … STOPPING`.

If the human wants the literal rule instead, case (4) cannot be a hold in this child: drop the
exemption (`own = set()`), and the flip test must go back to a stop. The deferred code-review
finding in `deferred-findings.json` (item 2) asks the same question about iteration 1.

### Rejected alternatives for that call

- **Literal rule, no exemption.** Fails case (4) (proven by mutation 2). Not a cost question.
- **Iteration 1's approach (drop every carrier of a partner from the trial).** Rejected by the
  review; mutation 1b below shows it brings the A→P hold back.
- **Drop only the carriers of a prerequisite partner from the trial** (keep the literal
  `base + rest + head` shape). About the same size as mine — sketch:
  `rest = [(n, h) for n, h in on if n not in partners and not any(_in_line(wt, ph, …, of=u)
  for u in under.get(n, ()) for ph in pre)]` and `_trial(wt, branch, base_ref, [*rest, head])`
  (±2 lines against `integrate.py:1837-1843`). Rejected on correctness, not size: a dropped
  carrier's own change (20's `twenty.txt` here) is never trial-merged together with the head,
  which is exactly what the iteration-1 code review faulted. Mine keeps 20 in the trial
  (`base + 10 + 21(wins) + 20`).
- **Remove 20 from the case (4) fixture.** Would hide the contradiction rather than settle it,
  and 20 is the point of the original test (21's clash is not with the same-wave bundle 20).
  The flipped test asserts 20 holds 10 and that the hold line does not name 20
  (`test_flow_same_wave_conflict.py:382-391`).

## What changed, by file

### `template/src/pdca_harness/integrate.py`

- `fold` gets one new keyword-only argument, `finished_heads` (`integrate.py:366`), documented
  at `:507-511`. Used only as partner candidates, and only while that head is on the line being
  built (`_carries`, `:1827-1828`). Never merged, never put in `took` or `carried`, never passed
  to `_carried_tips` (base `integrate.py:533`), so the #633/#695 rewrite checks are unchanged.
- The conflict branch (base `integrate.py:640-647`, now `:654-668`): `_held_by` is still tried
  first for a same-wave conflict (`:659`, only when `kept` is non-empty, as before). When it
  gives nothing, `_held_by_line` is tried (`:660-664`); its result is recorded in `held_out` in
  the same `(partners, paths)` shape. The `kept` condition moved from the outer `if` into the
  `_held_by` call, so a conflicting first bundle of the wave can now reach the new rule.
- `fold`'s `held_out` docstring (`:480-488`) says what is held now and what still raises.
- New `_held_by_line` (`integrate.py:1794`). Not a second classifier: it calls `_built_on`
  (base `:1849`) and `_clash` (base `:1774`) the way the carry does at base `:697-706`, and goes
  on only for kind `"batch"`. `_clash` already does rule (b) (its `"base"` trial) and rule (c)
  (`_partners`, base `:1821`). The one new trial is rule (e). A failing git step gives `None`
  (the fold raises the original conflict); a tree that won't go back still raises.
- `paths` in the hold = the files the failed line merge left conflicting (`exc.paths`).
- `from . import … waves` (`integrate.py:81`): no cycle (waves imports only brief, state,
  config).

**Rule (d) has no separate trial.** `_partners` names a bundle only when
`_trial(base_ref, [its, head])` fails at index 1 (base `integrate.py:1837-1839`), i.e. its head
merged cleanly onto the base at index 0 — on the same ref, in the same tree, with no fetch in
between. A separate `_trial(base, [partner head])` could never fail, so it would be dead code
(cost: one merge per named partner). The docstring says so (`integrate.py:1810-1813`). A partner
whose head no longer fits the base is therefore never named, `_clash` returns `"line"`, and the
run stops — which is what `test_a_clash_with_a_partner_whose_head_no_longer_fits_the_base_still_stops`
pins. Child-3 (#749) needs to know (d) is enforced inside `_partners`.

**How "built on a partner" is detected.** The brief says "`_built_on`'s `under` names a
partner's commit". I check whether any `under` commit *holds* the partner's head
(`merge-base --is-ancestor`, `integrate.py:1838-1839`). That covers the brief's case
(`under == [partner head]`: built on an own base holding it, or cut from its branch) and also
a bundle cut from the run's line (a seam), whose `under` is the line commit that holds the
partner — that is how Z holds F in the carried-partner stop test. It does not flag two bundles
that were both cut from the same line commit. A bundle cut from an *older* commit of the
partner's branch is not flagged by this check, but the rule (e) trial still includes it.

### `template/src/pdca_harness/flow.py`

- `_fold_lines` passes `finished_heads` to `fold` (`flow.py:1160`, `:1197`; docstring
  `:1169-1186`).
- `_carry_finished` (`flow.py:1363-1366`, docstring `:1416-1418`): its `_fold_lines` call
  (base `flow.py:1459`, now `:1472-1475`) passes a local empty `carried=put`. `fold` fills it
  with `took` after the push (base `integrate.py:724-725`), which is exactly "the head it
  folded". An empty dict is falsy, so `_carried_tips` (base `integrate.py:533-534`, `if carried
  and not dry_run`) still checks nothing. The heads are recorded only when the carry's line is
  used (not red, target folded): `flow.py:1499-1500`.
- `_drive_and_act`: run-level `finished_heads` (`flow.py:2816`), filled by the carry (`:2821`),
  passed to the in-run fold (`:3047`). The held bundle lands in `held_conflict`, which
  `_runnable` already honours (`held=` and `conflict_held=`), so its dependents and
  `Conflicts with` partners are held with no change to `_runnable`.
- Wording. `_announce_conflict_holds` (`flow.py:1563`) now takes `cfg`, `wave` and `finished`
  and words each partner group by where it is: in `wave` → "merged before it in the same wave
  k" (unchanged text for #674 holds); a carried finished id → "already on the line, finished in
  an earlier run"; any other → "already on the line from an earlier wave". Mixed groups are
  joined with ", and " (this answers iteration 1's minor review point about mixed partner sets).
  A partner that is the held bundle's own prerequisite adds "issue_10 is issue_21's own
  prerequisite: to fold it, rebuild issue_21's branch on issue_10's" (`_rebuild_on`, `:1555`).
  `_report_conflict_holds` (`flow.py:1587`) gives that rebuild step for prerequisite partners
  and the existing `_CONFLICT_STEP` proposal only for the others, so `Conflicts with: <prereq>`
  is never proposed. For a #674 same-wave hold both lines are byte-for-byte as before.
- Docstrings/comments updated where my change made them wrong: `_drive_and_act`'s `holds`
  paragraph, the `held_conflict` comment (`flow.py:2736-2740`), the fold-block comment, and the
  `_CONFLICT_STEP` comment (`flow.py:1246-1250`). Left alone (not functions this child changes):
  `_runnable`'s docstring and `cli._results_rc`'s docstring still describe `"conflict"` holds as
  same-wave only. Docs are #740's.

## The case (2) fixture, and why its order matters

`Z` (`Depends on: F`) is cut from the run's line, because an edge to a finished id is a seam
(base `flow.py:974-976`, `_closure_members`), so Z holds F. Under rule (e), if Z is on the line
when Y is folded, the line without F still brings F back, and the run must stop. So case (2)
can only be a hold when Y is folded before Z. In my fixture Y and Z are both in wave 0 and
`issue_Y` sorts before `issue_Z` (`test_flow_cross_wave_fold_holds.py:303`). The fault is real:
F is really carried by `_carry_finished` (the test asserts the "carried issue_F" line), Y really
clashes with it, and Z really holds F (asserted). The opposite order is pinned as a stop by
`test_a_clash_with_a_carried_partner_that_a_line_bundle_holds_still_stops` (`:426`). Iteration
1's case (2) put Y in wave 1 after Z, which only held because of the relaxation the review
rejected.

## Tests that flip (before → after)

- `test_flow_same_wave_conflict.py::test_a_conflict_with_earlier_wave_work_still_stops_the_run`
  (base `:365`; before: asserted `wave 1 did not integrate`, `STOPPING`, no hold for 21) →
  renamed `test_a_conflict_with_its_own_prerequisite_on_the_line_holds_it` (`:367`; after: 21
  held; fold-time line has `issue_10`, `(conflicts in shared.txt)` and `rebuild issue_21's branch
  on issue_10's`, and does not name 20; end-of-run line has the same rebuild step; the whole
  stderr has no `Conflicts with: 10` and no `same wave`; 30 not built and PLANNED; holds
  `{"21": "conflict"}`; exit 1). That file's `_run` now passes `holds=` and computes
  `self.rc = cli._results_rc(...)`; no other test in it reads those.
- No other test flips. Evidence: the full suite with only the production hunks reverted
  (`git apply -R --exclude='template/tests/*'`, then `engine/scripts/run-suite.sh`) failed
  exactly 3 driver tests — the two hold cases of the new file and the renamed test — out of
  2616. The root suite's `test_render_then_slice` also failed on that leg, but only because it
  renders the template and runs the same driver suite inside it (same 3 failures). With the
  patch applied both suites pass.
- `test_a_conflict_only_with_a_base_taken_in_mid_wave_still_stops_the_run` (now `:435`) is
  unchanged and still prints `STOPPING`: 22's clash is with `origin/main` itself, so `_clash`
  gives `"base"`.

## Actual stderr (patched tree)

```
case (1)
flow: issue_Y held out of the integration fold — its change conflicts with issue_A's, already on the line from an earlier wave (conflicts in shared.txt); bundles that depend on it or are its `Conflicts with` partners are held this run.
flow: issue_Y was held out of this run's integration line — its change conflicts with issue_A's (shared.txt). Proposed, for you to confirm: declare `Conflicts with: A` in issue_Y's brief, then rebuild issue_Y on a base that holds issue_A.

case (2)
flow: carried issue_F (finished in an earlier run) onto pdca-integration/main-r6048ba7b1a2b at … before wave 0 — this run's org/repo @ main bundles build on it.
flow: issue_Y held out of the integration fold — its change conflicts with issue_F's, already on the line, finished in an earlier run (conflicts in shared.txt); bundles that depend on it or are its `Conflicts with` partners are held this run.
flow: issue_Y was held out of this run's integration line — its change conflicts with issue_F's (shared.txt). Proposed, for you to confirm: declare `Conflicts with: F` in issue_Y's brief, then rebuild issue_Y on a base that holds issue_F.

case (4)
flow: issue_21 held out of the integration fold — its change conflicts with issue_10's, already on the line from an earlier wave (conflicts in shared.txt); issue_10 is issue_21's own prerequisite: to fold it, rebuild issue_21's branch on issue_10's; bundles that depend on it or are its `Conflicts with` partners are held this run.
flow: issue_30 skipped — prerequisite(s) not ready (21); not built on a base missing them.
flow: issue_21 was held out of this run's integration line — its change conflicts with issue_10's (shared.txt). issue_10 is issue_21's own prerequisite: to fold it, rebuild issue_21's branch on issue_10's, then re-run.

every stop guard (wording unchanged from today)
flow: wave 1 did not integrate (issue_Y's branch origin/fix/Y does not merge cleanly onto pdca-integration/main-… (conflicts in shared.txt) — an undeclared cross-wave overlap; declare the conflict / re-order, then re-run); STOPPING — later waves not run.
```

## Refuting my own test

- **(a) Genuine red? Yes.** `./engine/scripts/run-verify.sh` (the C4 gate) with
  `PDCA_BUNDLE`/`PDCA_WORKTREE` set, under `timeout 1800`: green leg 6 + 8 tests OK; red leg
  (production hunks reverted, tests kept) fails case (1), case (2) and the flip, each on
  `'did not integrate' unexpectedly found` — the run printed `wave N did not integrate …
  STOPPING`. Result line: `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`. The
  four stop tests are green on both legs by design: they pin stops this child must keep. To
  show each is still binding, I broke one piece at a time on the patched tree and ran both
  files (restored afterwards; `git diff` matched `patch.diff` again):
  - mutation 1 (built-on check off): all 14 pass — the rule (e) trial alone still stops both
    A→P-shaped runs, because the carrier stays in the trial;
  - mutation 1b (iteration 1's behaviour: drop carriers of a partner from the trial, check
    off): **both new stop tests fail** (Y held instead of stopping);
  - mutation 2 (no prerequisite exemption): **case (4) fails** (`STOPPING`);
  - mutation 3 (rule (e) trial skipped): **`…cause_only_together_still_stops` fails** (H
    held); the two A→P-shaped tests still stop, through the built-on check alone;
  - mutation 4 (in-run fold passed `finished_heads=None`): **case (2) fails** (`STOPPING`).
  So the carried-heads route, the prerequisite exemption, the trial and the "keep the
  remainder" fix are each pinned by a test; the built-on check and the trial each stop the
  A→P-shaped runs on their own.
- **(b) Production path? Yes.** Every case calls the real `flow._drive_and_act`, which runs the
  real `_carry_finished`, `_bundle_bases`/`build_bundle_base`, `_fold_lines`, `integrate.fold`,
  `_held_by`, `_held_by_line`, `_built_on`, `_clash`, `_partners`, `_trial`, `_runnable`,
  `_announce_conflict_holds` and `_report_conflict_holds`, on real git (a bare origin plus
  clones). Stubbed exactly as in `test_flow_same_wave_conflict.py`: the build/sign-off leaf
  (`_drive_wave`), `_publish_bundle` (which really cuts and pushes the branch), `draft_texts`,
  and `gh`. `integrate.fold` is wrapped (it calls the real one) only so the (d) guard can move
  main after the first fold. The exit code comes from the real `cli._results_rc`.
- **(c) Fixture includes the fault? Yes.** The clashing branches really conflict in git (the
  red leg shows the real fold raising on them, and the stop tests assert the facts with real
  merges in a scratch clone: e.g. `base + Q + W + P + V + Y` conflicts at Y). The partners are
  really on the line: A folded in wave 0; F really carried by `_carry_finished` (asserted); 10
  folded in wave 0. The carriers are really built on the partner: P's base holds A, Z holds F
  and was cut from the line (asserted), 20 holds 10 (asserted). The unrelated chains are really
  built and asserted COMPLETE in the hold cases and PLANNED in the stop cases.

## Commit-readiness

The target has no pre-commit config, formatter or linter (no `.pre-commit-config.yaml`; no
ruff/flake8/black config; CI runs only `render-check.yml` and `docs-check.yml`). Checked: every
added line ≤ 100 columns (the code's width), `git diff --check` clean, `py_compile` clean, and
the four files parse under the Python 3.11 grammar (`requires-python >= 3.11`, and no f-string
reuses its own quote inside a field, which would need 3.12). The full suite runner
(`engine/scripts/run-suite.sh`) passes: root suite 24 tests OK, driver suite 2616 OK (2
skipped). After that run I made two small edits (a docstring wording fix in `_prerequisites`
and one more assertion in case (2), that Z's head is on the line); the final C4 run covers
both changed test files and passes. The patch touches no docs, so I did not run the T2 docs
gate. Publish adds the DCO
sign-off when it commits.

## Housekeeping

- I wrote one log file outside the roots I was given: `/tmp/claude-747-c4.log` (the first C4
  run's output). That was a mistake; it holds only test output. I did not delete it (cleanup is
  the harness's).
- Scratch files live in the worktree's git-ignored `.cache/claude-747/` (backups, mutation logs,
  `show_err.py`, a reading aid that prints each case's stderr). The driver's reconstruction
  (`git reset --hard` + `git clean -ffdxq`) removes them, and they are not in `patch.diff`.
- The new test file is marked intent-to-add (`git add -N`) in the worktree index so `git diff`
  includes it; the same reconstruction drops that.

## Not done here (left for the human or siblings)

- The prerequisite exemption above needs the human's OK.
- The ten deferred findings (`deferred-findings.json`) are about the brief and the thread, not
  build work, and are untouched.
- Joint ("together") attribution and refining the built-on stop: child-2 (#748). A partner
  stranded by a moved base: child-3 (#749).
