# Build notes — #739 hold a cross-wave clash at the line fold (iteration 2)

Target: eduralph/pdca-harness, built and verified on the folded line
`pdca-integration/main-r547f8028520f` at `9f7c446` (#738 folded on top of `75a886e`), the
worktree's base. In `path:line` below, **base** means `9f7c446` and **new** means the
patched tree. The brief's anchors are on `75a886e`; with #738 folded they moved a little
(`_held_by` 1743 → base 1747, `_clash` 1770 → 1774, `_partners` 1817 → 1821, the fold's hold
636-643 → 641-648, `_carry_finished` 1259 → 1356, `_announce_conflict_holds` 1435 → 1532,
the fold block `flow.py:2862-2879` → 2977-2999, `cli._results_rc` 701 → 707).

This iteration starts from the previous attempt's patch (`iteration-v1/patch.diff`), whose
design passed review, and fixes the two implementation findings in the carry-forward. The
12 deferred findings are for the human and are not touched (see "Known gaps").

## What changed this iteration (the carry-forward)

### 1. The "together" fallback named unrelated bundles

Before (v1, `integrate.py:1847-1850` of that patch): when `_clash` found no single partner
and base + every bundle on the line + the head conflicted at the head, it named every bundle
on the line except the head's own ancestors. With an unrelated `X` on the line, case (4)
named `P, R, X` (probe B).

Now: the fallback is `_together` (new `integrate.py:1864-1902`), called from `_held_on_line`
(new 1849-1850) for any `_clash` kind other than `"base"` / `"batch"`. Still decided only by
trial merges, still outside `_clash` (its #694 contract is unchanged):

1. The together trial must conflict at the head (new 1886-1888), as before.
2. **Own change** (new 1889-1891): bundle `n` is named when leaving out its own change lets
   the head merge — `n`'s head replaced in the trial by what it was built on (`under[n]`,
   from `_built_on`), every other bundle merged as it is. This is the leave-one-out the
   reviewer suggested, using `under` the way `_partners` (base 1821-1846) judges a bundle
   for its own change.
3. **Carried change** (new 1892-1902): a bundle not named by step 2 is still named when the
   bundles built on it (whose heads hold its head, so they carry its change onto the line)
   are none of them named for their own change, and leaving it out together with them lets
   the head merge.

Why step 3: plain leave-one-out misses a partner that has a dependent on the line, because
the dependent carries the partner's change back into the trial. My scratch probe (case (4)
with `P2`, built on `P`, on the line before `H`) named only `R` without step 3; with it,
`P, R`. That shape is ordinary in a three-wave batch. The condition "none of them named for
its own change" stops the opposite mistake: when the dependent's own change is the one
needed (`V` built on `W`, `V` rewrites the file), `W` must not be named. Mutation MC (below)
shows the test catches dropping that condition.

`[]` → `_held_on_line` returns None → the run stops as before, when: the head merges after
them all, one of them does not merge on the trial base, or no one of them is needed (the
clash takes any of several combinations, e.g. any 2 of 3). The fold does not guess there.

The v1 filter "less the head's own ancestors" (`_in_line(..., of=head)`) is gone: a
bundle the head already holds is never named by these trials, since the head brings its
change back (case (4)'s `K`, and `K0`/`K1` in the new chain test, show it).

Probe E from the adversary (the carry's finished heads withheld, so the true partner F is
missing from the bundles judged): v1 held Y naming `G, W, V`, all unrelated. Now the run
stops — `wave 1 did not integrate … STOPPING`, holds `{}`, rc 1 — because no bundle the
fold knows of is needed for the clash. Checked with mutation MJ applied to case (2)
(scratch `.cache/pdca739/probe_e.py`, `flow.py` restored byte for byte).

### 2. The "stranded" check ignored what the partner was built on

Before (v1, `integrate.py:1856-1857` of that patch): a partner was "stranded" when its whole
head did not merge onto the current base. A partner built on another bundle's branch, or cut
from the line, could fail that only because of what is under it.

Now (new `integrate.py:1853-1857`): stranded means the partner's **own change** does not
merge onto `<remote>/<base>` — trial `base + under[n] + head[n]` stops exactly at the
partner's head (index `len(under[n])`). If it stops earlier, at what the partner was built
on, the partner is not stranded by its own change, so it is not told to rebuild on the base;
it falls to the other message groups (`flow.py` `_line_hold`, new 1546-1595: a prerequisite,
or the `Conflicts with` proposal). This is the trial the code review suggested.

### Tests added or changed this iteration

- Case (4) now has an unrelated earlier-wave `X` on the line (new test file 382-417), and
  asserts `issue_X` is not named. v1 code: red (`… issue_P's, issue_R's, issue_X's …`).
- New `test_a_clash_together_names_whose_change_it_needs_not_who_carries_it` (419-455): a
  three-wave line where `P` (renames the file) is carried by `P2`, and `V` (rewrites it) is
  built on `W`. `H` must be held naming exactly `P, V`; `P2`, `W`, `K0`, `K1`, `J` must not
  be named. Pins both halves of step 3.
- New `test_a_partner_built_on_a_stranded_branch_is_not_told_to_rebuild_on_the_base`
  (342-378): `P1` adds `a.txt`; `P2` is built on `P1` and adds `s.txt`; after the second
  fold, main gets its own `a.txt`; `W`, built on the moved main in wave 2, carries main's
  `a.txt` and adds its own `s.txt`. Expected: `P1`'s owner is told to rebuild on the new
  main; `W` gets `Conflicts with: P2`; `P2`'s owner is not told to rebuild. v1 code: red
  (`rebuild issue_P1's and issue_P2's branches on the new origin/main`).
- The test file's `after_fold` hook now fires after a chosen fold (`dict[int, ...]`, new
  78, 164-176), since the new stranded case moves main after the second fold. Case (3) uses
  `after_fold[1]`, which is what v1's list form did.

## The whole change (carried from v1, still in this patch)

`template/src/pdca_harness/integrate.py`
- `fold` takes `on_line` (name → head of bundles on the line that `accepted` does not list:
  the carry's finished ids) and `across` (filled with each cross-wave hold → its stranded
  partners): new 367-368 (base 365). Docstring for `held_out`: base 479-484 → new 482-500.
- The fold's conflict branch (base 641-648 → new 657-674): `_held_by` first, exactly as
  before but only when a same-wave bundle was kept (the old `kept` condition moved into the
  call, new 658-660); then `_held_on_line`. A hold goes into the same `held_out` the flow
  reads as `held_conflict`, so `_runnable` holds dependents and partners unchanged.
- `_held_on_line` (new 1802-1861): head must merge onto the current base alone (else stop);
  bundles on the line = carried finished heads the line holds, then `took`; `_clash` on the
  commit where the line leaves the base (`_cut_point`), with `under` from `_built_on`;
  `"batch"` → its partners, other kinds → `_together`; then the stranded check.
- `_held_by` docstring (base 1756-1764 → new 1782-1792): it said the fold "stops on it as
  before"; now says the fold then tries `_held_on_line`. Code untouched. Module docstring
  (base 66-68 → new 66-69): one clause for #739.

`template/src/pdca_harness/flow.py`
- `_fold_lines` passes `on_line` / `across` through (new 1161-1162, 1177-1181, 1197-1198).
- `_carry_finished` takes `on_line` and records each carried id's head where it seeds the
  line (new 1365-1366, 1414-1418, 1498-1499).
- `_line_hold` (new 1546-1595): wording per partner group — stranded (rebuild the partner's
  branch on the new base, no blame on the held bundle), a declared prerequisite (rebuild
  the held bundle's branch on it, no `Conflicts with` proposal), any other (the existing
  `_CONFLICT_STEP` proposal, base 1244). Docstring updated this iteration for the new
  stranded rule.
- `_announce_conflict_holds` / `_report_conflict_holds` (new 1598-1617 / 1620-1636) take
  `cfg` and `across`; a same-wave hold prints exactly the old line.
- `_drive_and_act`: `held_across` (new 2774-2777, comment updated this iteration),
  `finished_on_line` (2850-2857), the fold call (3083-3084), the announce calls
  (3086-3088, 3093-3095), the report call (3121-3123). Docstrings: `holds` (2737-2739),
  `_runnable`'s `conflict_held` (730-734).

`template/tests/test_flow_same_wave_conflict.py`: the case-5 flip (below), and `_run` now
collects `holds` and computes `self.rc` with `cli._results_rc` (new 148, 162-164).

## Tests (real git, `StackFoldGit`, through `flow._drive_and_act`)

New file `template/tests/test_flow_cross_wave_fold_holds.py` (copy in this bundle), loaded by
path like `test_flow_same_wave_conflict.py:36-39`; exit code via
`cli._results_rc(results, holds=holds)` (base `cli.py:707`).

| case | test | holds | rc |
|---|---|---|---|
| (1) in-batch earlier-wave partner | `test_a_clash_with_an_earlier_wave_bundle_holds_only_that_bundle` | `{Y: conflict}` | 3 |
| (2) finished F carried onto the line | `test_a_clash_with_a_finished_bundle_carried_onto_the_line_names_it` | `{Y: conflict}` | 3 |
| (3) line bundle stranded by moved main | `test_a_line_bundle_a_moved_base_strands_is_named_with_the_fix_for_its_owner` | `{B: base, W: conflict}` | 1 |
| (3b) partner stranded only by what it is built on (new) | `test_a_partner_built_on_a_stranded_branch_is_not_told_to_rebuild_on_the_base` | `{W: conflict}` | 1 |
| (4) only two partners together, plus unrelated X | `test_a_clash_only_with_two_line_bundles_together_names_both` | `{H: conflict}` | 3 |
| (4b) together, partners carried by dependents (new) | `test_a_clash_together_names_whose_change_it_needs_not_who_carries_it` | `{H: conflict}` | 3 |
| kept stop: also clashes with the base | `test_a_branch_that_also_clashes_with_the_base_itself_still_stops_the_run` | `{}` | 1 |
| (5) flip | `test_flow_same_wave_conflict.py::test_a_conflict_with_its_own_prerequisite_on_the_line_holds_it_not_the_run` | `{21: conflict}` | 1 |
| (5) stays a stop | `test_flow_same_wave_conflict.py::test_a_conflict_only_with_a_base_taken_in_mid_wave_still_stops_the_run` | `{}` | (not asserted, unchanged) |

### Tests that flip, before and after

Only the one the brief names. Driver suite on the base `9f7c446` (clean copy): **2610 OK,
2 skipped**. Patched: **2617 OK, 2 skipped** = 2610 + the 7 new cases. No test that passed on
the base fails now.

- `test_flow_same_wave_conflict.py::test_a_conflict_with_earlier_wave_work_still_stops_the_run`
  — **before:** asserted `wave 1 did not integrate`, `issue_21's branch`, `STOPPING`, no hold
  line for 21, 30 not built. **After:** renamed
  `test_a_conflict_with_its_own_prerequisite_on_the_line_holds_it_not_the_run` (new 367):
  no `did not integrate` / `STOPPING`; one hold line for 21 containing `issue_10`,
  `(conflicts in shared.txt)` and `rebuild issue_21's branch on issue_10's`; no
  `Conflicts with: 10` on it or anywhere in stderr; 21's head not on the line; 30 not built
  and PLANNED; holds `{21: conflict}`; rc 1.
- `test_a_conflict_only_with_a_base_taken_in_mid_wave_still_stops_the_run` — unchanged and
  still green (22 does not merge onto the moved main, so the base-alone check stops it).

### Messages as printed (fix applied)

- (1) `flow: issue_Y held out of the integration fold — its change conflicts with issue_A's, already on the line (conflicts in shared.txt); bundles that depend on it or are its `Conflicts with` partners are held this run. Proposed, for you to confirm: declare `Conflicts with: A` in issue_Y's brief, then rebuild issue_Y on a base that holds issue_A.`
- (3) `flow: issue_W held out of the integration fold — issue_A's branch, already on the line, does not merge cleanly onto origin/main itself: origin/main moved since it was cut, and issue_W was built on the new origin/main (conflicts in a.txt); … To fold it, rebuild issue_A's branch on the new origin/main (update it from origin/main and resolve the conflicts there), then re-run.`
- (3b) `flow: issue_W held out of the integration fold — issue_P1's branch, already on the line, does not merge cleanly onto origin/main itself: origin/main moved since it was cut, and issue_W was built on the new origin/main; its change conflicts with issue_P2's, already on the line (conflicts in a.txt, s.txt); … To fold it, rebuild issue_P1's branch on the new origin/main (…), then re-run. Proposed, for you to confirm: declare `Conflicts with: P2` in issue_W's brief, then rebuild issue_W on a base that holds issue_P2.`
- (4) `… its change conflicts with issue_P's, issue_R's, already on the line (conflicts in shared.txt); … declare `Conflicts with: P, R` in issue_H's brief …`
- (4b) `… its change conflicts with issue_P's, issue_V's, already on the line …`
- (5) `flow: issue_21 held out of the integration fold — its change conflicts with issue_10's, already on the line, and issue_10 is its own prerequisite, which its branch does not hold (conflicts in shared.txt); … To fold it, rebuild issue_21's branch on issue_10's, then re-run.`

## Refuting my own test

**(a) Genuine red? Yes.** `./engine/scripts/run-verify.sh` (the configured C4 gate, run with
`PDCA_BUNDLE` / `PDCA_WORKTREE`) reverts only the production hunks. Red leg: 7 failures —
the case-5 flip and every new case except the kept stop — each on
`'did not integrate' unexpectedly found … STOPPING`. No import or load failure. Green leg:
all 15 tests of both files pass. Result `PDCA-EVIDENCE: C4 PASS`; the worktree's files were
byte-identical afterwards (sha256 checked). The kept-stop test passes on both legs by design.
Both carry-forward fixes were also checked against the v1 code directly: before changing
production, the updated case (4) and the new case (3b) failed on v1 with exactly the
reviewers' symptoms (`issue_X's` named; `rebuild issue_P1's and issue_P2's branches`).

Each piece was also broken on its own (scratch `.cache/pdca739/mutate.py`, file restored
byte for byte after each run):

| mutation | breaks | result |
|---|---|---|
| MA | v1's together fallback (all on the line, less head's own) | red: (4), (4b) |
| MB | no carried-change pass (plain leave-one-out) | red: (4b) |
| MC | carried-change pass even when a dependent is named for its own change | red: (4b) |
| MD | v1's stranded check (whole head onto the base) | red: (3b) |
| ME | own-change pass drops the bundle without merging `under` in its place | **green — not caught** |
| MF | no together fallback | red: (4), (4b) |
| MG | nothing ever stranded | red: (3), (3b) |
| MH | no base-alone check | red: kept stop |
| MI | judge on the base as fetched instead of the line's cut point | red: (3), (3b) |
| MJ | carry records no finished heads | red: (2) |
| MK | in-run fold not given the carried heads | red: (2) |
| ML | no prerequisite wording | red: (5) flip |

ME is not caught: in every shipped shape, what a bundle was built on is itself on the line
as its own entry, so merging `under` in its place or not gives the same trial. It matters
only when what a bundle was built on is not on the line (e.g. a base the line took in for a
gone branch, under a bundle cut from the line); then it keeps the bundle from being named
for a change it only carries — the same convention `_partners` uses. I did not build a
fixture for that edge.

**(b) Production path? Yes.** Every case drives `flow._drive_and_act` → the real
`integrate.fold` → `_held_on_line` → real `_clash` / `_partners` / `_together` / `_trial`
merges in the real integration worktree; case (2) runs the real `_carry_finished` (stderr
asserts `carried issue_F … onto`); cases (3) and (3b) run real `build_bundle_base` on a
really moved origin main (case (3) asserts B's #738 hold line). Stubbed, as in
`test_flow_same_wave_conflict.py`: the build leaf (`_drive_wave`), `_publish_bundle` (pushes
real branches to the bare origin), `publish.draft_texts`, and `gh`. The `integrate.fold`
wrapper only calls through, then runs the case's after-fold hook.

**(c) Fixture includes the fault? Yes.** The clashing branches are real pushed branches.
(3)/(3b) really move origin's main after a fold and assert W's base holds that commit and
P2's does not; (3b) asserts by real merges that P1 and P2 both fail onto the moved main and
that P2 holds P1. F is really put on the line by the carry. (4)/(4b) assert by real merges
that each partner alone merges with H and the combination conflicts at H, with X or not;
the kept stop asserts Y really does not merge onto the moved main.

## Alternatives ruled out

- **Plain leave-one-out (no carried-change pass).** Not a cost question: it under-names a
  partner whose dependent is on the line (probe: `R` only, instead of `P, R`); mutation MB
  shows (4b) catches it. Step 3 costs one ancestry check per pair of line bundles
  (`merge-base --is-ancestor`, n² calls) plus at most one trial per bundle, only on this
  fallback path.
- **Leave a bundle out together with everything built on it, always (a cascade).** Wrong
  the other way: it names `W` when the clash needs `V`'s own change (mutation MC, red).
- **Greedy minimisation** (drop each bundle whose removal keeps the conflict, in order). It
  would name a sufficient pair in an "any 2 of 3" clash, where leave-one-out names nobody
  and the run stops. Rejected: the result depends on the order, and with nested histories it
  can drop a needed prerequisite before its dependent is judged. Trial cost is the same
  (n trials). Stopping on an ambiguous clash is the brief's default ("every other outcome
  … stops the run as today").
- **Changing `_held_by`'s "all of `kept`"** (#674's same-wave rule) the same way: out of
  scope; the reviewer accepted it there because `kept` is one wave.
- **Skip the base-alone trial when the line's cut point is the base** (code-review advisory
  3): saves one trial (a detached checkout, one merge, a reset) per classified conflict;
  costs a `_rev` comparison of `root` and `base_ref` (2 `rev-parse` calls, ~2 lines and a
  comment about why `_clash`'s `"base"` covers it). Kept the plain version.
- Carried from v1, still valid: a 3-tuple `held_out` value instead of `across` (changes the
  type three flow readers unpack and breaks
  `test_a_hold_leaves_the_integration_tree_clean_on_the_line`, which asserts the 2-tuple);
  putting carried finished bundles into `accepted` (they would enter `carried_heads` and the
  #633 / #695 rewrite checks and `build_bundle_base(excluded=…)`, a behaviour change outside
  this slice).

## Trial cost

On the conflict path only. `_held_on_line` as before (1 base trial, `_clash`'s trials, one
stranded trial per partner). The together fallback adds, for n bundles on the line: 1
together trial + n own-change trials + at most n carried-change trials, each of up to n+1
merges, and up to n² ancestry checks. It runs only when `_clash` names no single partner.

## Known gaps (left for the human)

- The 12 deferred findings in `deferred-findings.json` are untouched by design, including
  "a stranded partner hides a real overlap" and "a stranded line bundle holds every later
  bundle after building it". This iteration's stranded change does not make either worse:
  a partner stranded only by what it is built on now gets the `Conflicts with` proposal
  instead of a rebuild-on-main step (case 3b).
- A clash that needs any two of several bundles, with no single one needed, stops the run
  (no one is needed by leave-one-out). Not exercised by a test.
- A needed bundle whose change reaches the line through a dependent that is itself named
  for its own change is not named separately; the dependent's rebuild takes it along
  (probe: R + its dependent R2 → only `R2` named).
- `_runnable`'s line for a `Conflicts with` partner of a stranded hold (new `flow.py:857-864`)
  still says "wait until W is rebuilt on a base that holds issue_A"; for a stranded hold the
  step is A's rebuild. Not asked for (from v1).
- `cli._results_rc`'s docstring (base `cli.py:722-723`) still describes `"conflict"` as a
  same-wave hold only; cli.py is outside this slice (#740 can take it).
- ME (above) has no test.

No external dependency was missing: git, the instance `.venv` Python and copier were all
present; nothing was stubbed in place of a tool.

## Commit-readiness

The target has no formatter, linter config or commit hooks (no `.pre-commit-config.yaml`;
no ruff/flake8/black config; `.git/hooks` holds only samples). CI runs the docs check and
the render suite. All four files compile; `git diff --check` is clean; no tabs or trailing
spaces in the new file; the longest added line is 97 characters (the files already go to
99-102). T2 docs gate: lint clean, 22 pages rendered, link audit OK. T3 (`run-suite.sh`):
root suite 24 OK, driver suite 2617 OK (2 skipped). The publish commit needs a DCO
sign-off (`CONTRIBUTING.md`), which publish adds. `patch.diff` was checked to apply cleanly
to `9f7c446` (scratch index) and to reproduce the worktree byte for byte.

## Housekeeping

Scratch files, all under the worktree's git-ignored `.cache/pdca739/`: `probe.py` (shape
probes), `mutate.py` (the table above), `show.py` (prints each case's lines),
`probe_e.py` (probe E under mutation MJ), `base/` (a
`git archive` copy of `9f7c446`, used for the base suite count), `base.idx` (scratch index
for the apply check), and the logs `c4.log`, `t3.log`, `base-suite.log`. Not removed;
cleanup is the harness's. `.cache/` is copied by the root render tests' `copytree`, but
copier renders only `template/` and the throwaway repo's `.gitignore` drops `/.cache/`, so
it cannot change a result. The T2 gate script makes its own `/tmp` dir (its `mktemp`); I
wrote nothing outside the worktree and this bundle. No push, no PR.
