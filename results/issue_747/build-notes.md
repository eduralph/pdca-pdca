# Build notes — #747 (hold a single-partner cross-wave clash at the line fold), iteration 3

Target: eduralph/pdca-harness, built on the run's line `pdca-integration/main-r547f8028520f`
at `9f7c446` (#738 folded). "base" anchors are on `9f7c446`; every other `path:line` is on
that tree **with this patch applied** (`$PDCA_WORKTREE`).

This iteration starts from iteration 2's patch (`iteration-v2/patch.diff`, which applied
cleanly on `9f7c446`). It changes that patch where the carry-forward pointed, and fixes one
real bug that building the requested test exposed.

## What the carry-forward asked, and what I found

Round 2 asked for tests of the prerequisite branch of rule (e): (i) mixed partners (one is
the held bundle's own prerequisite, one is not), and (ii) "a rest bundle built on the
prerequisite whose own change also clashes with the head", which "should stop, because the
rest merge after head-winning fails", so that the `wins` trial is pinned.

**(ii) as worded is not a stop: such a bundle is a partner, so it is case (i).** `_partners`
(base `integrate.py:1821-1846`) tries each bundle on the line on what it was built on, then
the head with its side winning, then the bundle's own head. A bundle built on the
prerequisite whose own change clashes with the head fails exactly that trial, so it is
named; it is never part of "the rest". I built that fixture literally (20 built on 10; 20
and 21 both add `y.txt`): the fold names `issue_10` and `issue_20`, and without 20, 21
rebuilt on 10 merges. So it is a hold naming both, as the invariant asks ("names every
partner"). That is the new test
`test_a_clash_with_its_prerequisite_and_a_bundle_built_on_it_names_both`
(`template/tests/test_flow_cross_wave_fold_holds.py:477`); it covers (i) too.

**Building a stop test that really pins the trial found a bug in iteration 2.** For a bundle
left on the line to make the trial fail without being named, its clash with the head must
show only together with other line work. Fixture
(`test_a_clash_its_prerequisite_does_not_explain_alone_still_stops`, `:518`): 21 depends on
10 but is cut from the plain base (so it clashes with 10 on `other.txt`); P renames
`shared.txt`; 20, built on 10, rewrites most of `shared.txt`; 21 edits its last line.
Rebuilt on 10, 21 does **not** merge onto the line (P's rename plus 20's rewrite make git see
a delete, so 21's edit is a modify/delete conflict). The run must stop.

Iteration 2 held 21. Its trial was `base + 10 + 21 (wins) + P + W + 20`: the rebuilt head
merged **first**, the rest after. In that order git still sees the rename, so every merge is
clean. The fold merges a bundle **last**, onto the line, and git merges are order-dependent.
The test asserts both facts with plain git (`:547-548`): in line order the rebuilt head
conflicts (index 4); in iteration 2's order nothing does. Iteration 2's advice in that run
was also wrong: "to fold it, rebuild issue_21's branch on issue_10's" would not fold it.

## The fix (rule (e), prerequisite branch)

`template/src/pdca_harness/integrate.py:1837-1852`:

- `off` = partners that are **not** the held bundle's prerequisites (taken off the line);
  `left` = everything else on the line, in merge order, prerequisite partners included
  (`:1838-1839`).
- Built-on stop (`:1840-1842`): a bundle in `left` whose `_built_on` `under` commit holds an
  `off` partner's head stops the run. Iteration 2 checked only bundles that were no partner;
  now a prerequisite partner itself built on an `off` partner stops too (third new test).
- With prerequisite partners, one trial builds "the head rebuilt on them":
  `_trial(base_ref, [*pre, head], wins=len(pre), made=made)` (`:1843-1850`). The commit it
  ends on is on no branch.
- The rule (e) trial is `base + left (merge order) + that commit`, merged **last**
  (`:1851-1852`). With no prerequisite partner this is the brief's literal rule:
  `base + (line without the partners) + head`.

`_trial` gets one keyword-only out-parameter, `made` (`integrate.py:1981`, filled at
`:2013-2015`): when every merge was clean, the commit the trial ended on. No other caller
changes (default `None`).

Rejected alternatives, with cost:

- **Keep iteration 2's order** (head first, rest after): wrong — the new stop test goes red
  with it (mutation A).
- **Drop the bundles that carry the prerequisite and merge the plain head last**
  (iteration 1's idea, for prerequisites only): wrong — in the new stop test the trial
  becomes `base + P + W + 21`, which merges, because 20 (whose rewrite makes the clash) is
  gone (mutation I: the test goes red). The iteration-1 review rejected this shape too.
- **Return the rebuilt commit as a third element of `_trial`'s result**: changes the
  `(index, paths)` contract at all 8 other call sites (`integrate.py:993, 1785, 1787, 1790,
  1899, 1905, 1933, 1938`) for one caller. The keyword-only `made` changes none.
- **Build the rebuilt head with `git merge-tree`**: a second merge mechanism beside
  `_trial` / `_merge_over`; the brief says reuse.

## The judgement call from iteration 2 — still yours to confirm

Unchanged in substance and still NEEDS-HUMAN (C1/C5 of the last review): the brief
contradicts itself. Rule (e) says a remaining line bundle built on a partner fails (e);
case (4) requires 21 held although 20 (built on 10, the partner) stays on the line. The only
difference between case (4) and the reviewer's A→P stop case is that 10 is 21's declared
prerequisite. So the patch exempts **prerequisite** partners: they stay on the line and the
head is tried rebuilt on them. `_prerequisites` (`integrate.py:1860`) = the ids in the held
bundle's own `Depends on` / `Depends on (merged)` / `Stacks on` (`waves.declared_deps`), the
union `_runnable` uses. Direct prerequisites only: a transitive one (21 → 10 → A) is not
exempt, which the third new test pins as a stop. If you want the literal rule instead, case
(4) cannot be a hold in this child (mutation C: it goes back to a stop).

## What changed, by file

### `template/src/pdca_harness/integrate.py`

- `fold` gets keyword-only `finished_heads` (`:366`, documented `:507-511`). Used only as
  partner candidates, and only while that head is on the line being built (`_carries`,
  `:1830-1831`). Never merged, never in `took` or `carried`, never passed to `_carried_tips`
  (base `:533-534`), so the #633/#695 rewrite checks are unchanged.
- The conflict branch (base `:640-647`, now `:655-668`): `_held_by` is still tried first,
  only when `kept` is non-empty (`:659`), as before. When it gives nothing, `_held_by_line` is
  tried (`:660-664`); its result goes into `held_out` in the same `(partners, paths)` shape.
  The `kept` condition moved from the outer `if` into the `_held_by` call, so the first
  bundle of a wave can reach the new rule.
- `held_out` docstring (`:472-491`) says what is held now and what still raises.
- New `_held_by_line` (`:1794`). Not a second classifier: it calls `_built_on` and `_clash`
  the way the carry does (base `:697-706`) and goes on only for kind `"batch"`. `_clash` does
  rule (b) (its `"base"` trial) and rule (c) (`_partners`). Rule (d) is enforced inside
  `_partners`: a bundle is named only when `_trial(base, [its, head])` fails at index 1
  (base `:1837-1839`), i.e. `its` merged cleanly onto the base at index 0, on the same ref
  and tree. A separate `_trial(base, [partner])` could never fail there, so I did not add one
  (dead code costing one merge per partner). A partner whose head no longer fits the base is
  never named, `_clash` gives `"line"`, and the run stops — what
  `test_a_clash_with_a_partner_whose_head_no_longer_fits_the_base_still_stops` pins. Child-3
  (#749) needs to know (d) lives in `_partners`.
- New `_prerequisites` (`:1860`). `from . import … waves` (`:81`): no import cycle (`waves`
  imports only `brief`, `state`, `config`).
- `_trial` `made` (`:1981`, `:2013-2015`).
- "Built on" means "an `under` commit holds the partner's head" (`merge-base
  --is-ancestor`), not "equals": that also catches a bundle cut from the run's line (a seam),
  whose `under` is the line commit holding the partner — how `Z` holds `F` in
  `test_a_clash_with_a_carried_partner_that_a_line_bundle_holds_still_stops`.

### `template/src/pdca_harness/flow.py`

- `_fold_lines` passes `finished_heads` to `fold` (`:1160`, `:1197`; docstring `:1169-1186`).
- `_carry_finished` (`:1364-1367`, docstring `:1417-1419`): its `_fold_lines` call (base
  `:1459`, now `:1473-1476`) passes a local empty `carried=put`. `fold` fills it with `took`
  after the push (base `integrate.py:724-725`) — "the head it folded". An empty dict is falsy,
  so `_carried_tips` (base `integrate.py:533-534`) still checks nothing. The heads are
  recorded only when the carry's line is used (`:1500-1501`).
- `_drive_and_act`: run-level `finished_heads` (`:2825`), filled by the carry (`:2830`), passed
  to the in-run fold (`:3056`). The held bundle lands in `held_conflict`, which `_runnable`
  already honours (`held=` and `conflict_held=`), so its dependents and `Conflicts with`
  partners are held with no change to `_runnable`.
- Wording. `_announce_conflict_holds` (`:1569`) words each partner by where it is: in the
  wave → "merged before it in the same wave k" (unchanged for #674 holds); a carried finished
  id → "already on the line, finished in an earlier run"; else "already on the line from an
  earlier wave"; groups joined with ", and ". A prerequisite partner adds "issue_10 is
  issue_21's own prerequisite: rebuild issue_21's branch on issue_10's" (`_rebuild_on`,
  `:1563`). Iteration 2 said "to fold it, rebuild …", false when another partner is left, so
  "to fold it, " is gone. `_report_conflict_holds` (`:1593`): only prerequisites → "…:
  rebuild issue_21's branch on issue_10's, then re-run."; any other partner → "issue_10 is
  issue_21's own prerequisite." (when there is one), then the `_CONFLICT_STEP` proposal with
  `{ids}` = the non-prerequisite partners and `{partners}` = every partner: one rebuild, on a
  base that holds all of them. Iteration 2 printed two rebuild steps for the mixed case. For
  a #674 same-wave hold both lines are byte-for-byte as before.
- Helpers `_own_prereqs` (`:1548`), `_prerequisite` (`:1556`).
- Comments/docstrings fixed where the change made them wrong: `_drive_and_act`'s `holds`
  paragraph, the `held_conflict` comment, the fold-block comment, `_CONFLICT_STEP`'s comment
  (`:1246-1251`). Left alone (not functions this child changes; docs are #740's):
  `_runnable`'s and `cli._results_rc`'s docstrings still call `"conflict"` holds same-wave
  only.

**Code-review reuse suggestion not taken** (have `_held_by_line` return which partners are
prerequisites inside the hold record, instead of `_own_prereqs` reading the brief again):
the `(partners, paths)` record is #674's `held_out` contract. Widening it touches 10 typed or
unpacking lines (`flow.py:1153, 1569, 1579, 1594, 1600, 2750, 2878`, `integrate.py:360,
1768, 1797`), `_held_by`'s return, and the expected value of an existing #674 test
(`test_flow_same_wave_conflict.py:357`), to save one brief read per held bundle. Both reads
call the same function on a brief the run never writes, so they cannot disagree within a run.
The reviewer marked it non-blocking.

## Tests

New file `template/tests/test_flow_cross_wave_fold_holds.py` (the brief's test path).
Fixture additions: a `cut_from` override in the publish stub (`:94`, `:176`), the mechanism
`test_flow_same_wave_conflict.py` uses for the flip; and `_rebuilt` (`:274`), which makes
"21 rebuilt on 10" a real branch in the scratch clone after the run, so each fixture's facts
are asserted with plain git.

- Case (1) `:290`, case (2) `:325` — as in iteration 2.
- Case (3) stop guards `:363` (child-2 flips it), `:392` (child-3 flips it), and iteration 2's
  two built-on stops `:422`, `:448`.
- New, under "(4) its own prerequisite, and more on the line":
  - `:477` mixed partners — hold naming 10 and 20, the advice above, exit 3.
  - `:518` the prerequisite does not explain the clash alone — stop (pins the trial and its
    order).
  - `:555` a partner its prerequisite was built on (21 → 10 → A, 21 cut from the plain base)
    — stop. The one case where only the built-on check stops the run: rebuilt on 10, 21 holds
    A too, so the trial merges (`:579-580` asserts it). Iteration 2 checked only non-partner
    bundles, so it would have held 21 and proposed `Conflicts with: A` for a bundle 21
    depends on through 10.

### Tests that flip (before → after)

- `test_flow_same_wave_conflict.py::test_a_conflict_with_earlier_wave_work_still_stops_the_run`
  (base `:365`; asserted `wave 1 did not integrate`, `STOPPING`, no hold for 21) → renamed
  `test_a_conflict_with_its_own_prerequisite_on_the_line_holds_it` (`:367`; 21 held; fold-time
  line has `issue_10`, `(conflicts in shared.txt)`, `rebuild issue_21's branch on issue_10's`,
  not `issue_20`; end-of-run line has the rebuild step; whole stderr has no `Conflicts with:
  10` and no `same wave`; 30 not built, PLANNED; holds `{"21": "conflict"}`; exit 1). That
  file's `_run` now passes `holds=` and computes `self.rc`; no other test there reads them.
- **No other existing test flips.** Evidence: the whole driver suite with only the production
  hunks reverted (`git apply -R --exclude='tests/*' --exclude='template/tests/*' patch.diff`,
  then `cd template && PYTHONPATH=src python3 -m unittest discover -s tests` under `timeout
  1500`): 2619 tests, exactly 4 failures — the three hold cases of the new file (1), (2), the
  mixed hold, and the renamed flip. Restored afterwards; `git diff` matched `patch.diff`.
- `test_a_conflict_only_with_a_base_taken_in_mid_wave_still_stops_the_run` (`:435`) is
  unchanged and still prints `STOPPING`: 22's clash is with `origin/main` itself, so `_clash`
  gives `"base"`.

## Actual stderr (patched tree; line names and tips shortened)

```
case (1)
flow: issue_Y held out of the integration fold — its change conflicts with issue_A's, already on the line from an earlier wave (conflicts in shared.txt); bundles that depend on it or are its `Conflicts with` partners are held this run.
flow: issue_Y was held out of this run's integration line — its change conflicts with issue_A's (shared.txt). Proposed, for you to confirm: declare `Conflicts with: A` in issue_Y's brief, then rebuild issue_Y on a base that holds issue_A.
holds={'Y': 'conflict'} rc=3

case (2)
flow: carried issue_F (finished in an earlier run) onto <line> at <tip> before wave 0 — this run's org/repo @ main bundles build on it.
flow: issue_Y held out of the integration fold — its change conflicts with issue_F's, already on the line, finished in an earlier run (conflicts in shared.txt); bundles that depend on it or are its `Conflicts with` partners are held this run.
flow: issue_Y was held out of this run's integration line — its change conflicts with issue_F's (shared.txt). Proposed, for you to confirm: declare `Conflicts with: F` in issue_Y's brief, then rebuild issue_Y on a base that holds issue_F.
holds={'Y': 'conflict'} rc=3

case (4), the flip
flow: issue_21 held out of the integration fold — its change conflicts with issue_10's, already on the line from an earlier wave (conflicts in shared.txt); issue_10 is issue_21's own prerequisite: rebuild issue_21's branch on issue_10's; bundles that depend on it or are its `Conflicts with` partners are held this run.
flow: issue_30 skipped — prerequisite(s) not ready (21); not built on a base missing them.
flow: issue_21 was held out of this run's integration line — its change conflicts with issue_10's (shared.txt). issue_10 is issue_21's own prerequisite: rebuild issue_21's branch on issue_10's, then re-run.
holds={'21': 'conflict'} rc=1

mixed partners (new)
flow: issue_21 held out of the integration fold — its change conflicts with issue_20's, merged before it in the same wave 1, and issue_10's, already on the line from an earlier wave (conflicts in shared.txt, y.txt); issue_10 is issue_21's own prerequisite: rebuild issue_21's branch on issue_10's; bundles that depend on it or are its `Conflicts with` partners are held this run.
flow: issue_21 was held out of this run's integration line — its change conflicts with issue_10's, issue_20's (shared.txt, y.txt). issue_10 is issue_21's own prerequisite. Proposed, for you to confirm: declare `Conflicts with: 20` in issue_21's brief, then rebuild issue_21 on a base that holds issue_10, issue_20.
holds={'21': 'conflict'} rc=3

the two new stops (wording unchanged from today)
flow: wave 1 did not integrate (issue_21's branch origin/fix/21 does not merge cleanly onto <line> (conflicts in other.txt, shared.txt) — an undeclared cross-wave overlap; declare the conflict / re-order, then re-run); STOPPING — later waves not run.
flow: wave 2 did not integrate (issue_21's branch origin/fix/21 does not merge cleanly onto <line> (conflicts in a.txt, shared.txt) — an undeclared cross-wave overlap; declare the conflict / re-order, then re-run); STOPPING — later waves not run.
```

## Refuting my own test

- **(a) Genuine red? Yes.** `./engine/scripts/run-verify.sh` (the C4 gate), run from the
  instance root with `PDCA_BUNDLE` / `PDCA_WORKTREE` set, under `timeout 1800`: green leg
  9 + 8 tests OK; red leg (production hunks reverted, tests kept) fails case (1), case (2),
  the mixed hold and the flip, each on `'did not integrate' unexpectedly found` — the run
  printed `wave N did not integrate … STOPPING` and left the unrelated chain unbuilt.
  `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`. The seven stop tests are
  green on both legs by design: they pin stops this child must keep. To show each new piece
  is binding I broke one thing at a time on the patched tree and ran both test files
  (helper `.cache/claude-747/mutate.py`; production files restored and compared with their
  backups after every run):
  - A — iteration 2's trial order (rebuilt head first): `…does_not_explain_alone_still_stops`
    fails (21 held).
  - B — no trial when there are prerequisite partners: same test fails.
  - C — no prerequisite exemption: the flip fails (`STOPPING`).
  - D — in-run fold given no carried heads: case (2) fails (`STOPPING`).
  - E — no built-on check: `…its_prerequisite_was_built_on_still_stops` fails (21 held).
  - F — no rule (e) trial at all: `…does_not_explain_alone_still_stops` and
    `…cause_only_together_still_stops` fail.
  - G — iteration 2's mixed-case `{partners}` (non-prerequisites only): the mixed hold fails.
  - H — iteration 2's built-on check (non-partner bundles only): the built-on test fails.
  - I — iteration 1's idea for prerequisites (drop them and their carriers, plain head
    last): `…does_not_explain_alone_still_stops` fails.
- **(b) Production path? Yes.** Every case calls the real `flow._drive_and_act`, which runs
  the real `_carry_finished`, `_bundle_bases` / `build_bundle_base`, `_fold_lines`,
  `integrate.fold`, `_held_by`, `_held_by_line`, `_built_on`, `_clash`, `_partners`, `_trial`,
  `_merge_over`, `_runnable`, `_announce_conflict_holds` and `_report_conflict_holds`, on real
  git (a bare origin plus clones). Stubbed exactly as in `test_flow_same_wave_conflict.py`:
  the build/sign-off leaf (`_drive_wave`), `_publish_bundle` (which really cuts and pushes the
  branch), `draft_texts`, and `gh`. `integrate.fold` is wrapped (it calls the real one) only
  so the (d) guard can move main after the first fold. The exit code is the real
  `cli._results_rc`. `_merges` / `_rebuilt` only state fixture facts with plain git after
  the run; nothing the run decides goes through them.
- **(c) Fixture includes the fault? Yes.** The clashing branches really conflict in git (the
  red leg shows the real fold raising on them). The held bundle's head really lacks its
  prerequisite (asserted), the carriers really hold the partner (asserted: 20 holds 10, 10
  holds A, Z holds F), F is really carried by `_carry_finished` (asserted), and "21 rebuilt
  on 10" really conflicts or merges as each docstring says (asserted with real merges,
  including the order-dependence in the new stop test). The unrelated chains are really built
  (COMPLETE) in the hold cases and left PLANNED in the stop cases.

## Commit-readiness

The target has no formatter, linter or commit-hook config (no `.pre-commit-config.yaml`; no
ruff/black/flake8 settings in `template/pyproject.toml.jinja`; only sample hooks in the
repo's `.git/hooks`; CI runs `render-check.yml` and `docs-check.yml`). `CONTRIBUTING.md` asks
for a DCO sign-off (publish adds it) and green suites. Checked: `git diff --check` clean; the
widest added line is 98 columns (the files already go to 100–106); the four files have no
f-string syntax that only Python 3.12+ accepts (`requires-python >= 3.11`; only 3.14 is
installed here, so I scanned the tokens; the scanner flags a known 3.12-only probe).
`./engine/scripts/run-suite.sh` (T3, under `timeout 3000`): root suite 24 tests OK, driver
suite 2619 tests OK (2 skipped) — `PDCA-EVIDENCE: root suite OK, driver suite OK`. The final
C4 run is on the final tree. The patch touches no docs, so I did not run the T2 docs gate.

## Housekeeping

- Scratch files are in the worktree's git-ignored `.cache/claude-747/` (backups, mutation
  helper and logs, the stderr reader `show_err.py`, the f-string scanner, gate logs). The
  driver's reconstruction removes them; none is in `patch.diff`.
- The new test file is marked intent-to-add (`git add -N`) in the worktree index so `git diff`
  includes it.
- Nothing pushed, no PR opened.

## Not done here (left for the human or siblings)

- The prerequisite exemption needs your OK (above).
- The deferred findings in `deferred-findings.json` are about the brief and the thread, not
  build work; untouched.
- Joint ("together") attribution and refining the built-on stop — including whether a
  transitive prerequisite (21 → 10 → A) should count as one, which would turn the third new
  stop into a hold with "rebuild on 10" advice: child-2 (#748). A partner stranded by a moved
  base: child-3 (#749).
