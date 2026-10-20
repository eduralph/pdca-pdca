# Build notes — #748 name the joint partners of a cross-wave fold clash (iteration 2)

Target: eduralph/pdca-harness, built on the run's line `pdca-integration/main-r547f8028520f`
at `72a774a` (#738 and #747 folded on top of `9f7c446`). Every `path:line` below is on that
tip with this patch applied.

## What this iteration changed

The iteration-1 review found one gap: nothing tested the own-change helper
(`_own_change`, `integrate.py:1887`). All five cases built H on K, and K only adds `k.txt`,
so the helper's leading revs never changed a trial. If `_own_change` returned `[]`, all
five cases still passed.

This iteration adds the missing case. The production code is unchanged from iteration 1:
the `integrate.py` hunks are byte-identical (same result blob `25238c9`). The only changes
are in `template/tests/test_flow_cross_wave_joint_holds.py`:

- New case (6), `test_a_branch_built_on_a_line_bundle_is_tried_on_its_own_change_only`
  (`test_flow_cross_wave_joint_holds.py:408`).
- One new paragraph in the module docstring (`:18-24`) that says what the case pins.

### The new case, and why it needs the helper

- L (wave 0) renames `two.txt` to `moved2.txt`.
- H (wave 1, `Depends on: L`) is built on a base that holds L. H's own change rewrites
  lines 1-7 of `moved2.txt` and edits line 10 of `shared.txt`.
- X (wave 0, on the line) edits line 10 of `two.txt`.
- P and R (wave 0) make the usual joint rename clash in `shared.txt`.
- W→V→U is the unrelated chain.

Tried from the base, all of H's branch is L's rename plus H's rewrite. That is too unlike
`two.txt` for git to see a rename, so git sees `two.txt` deleted, and X's edit hits a
deleted file: a conflict. Tried on L's head, where H started (what `_own_change` merges
first), X's edit lands on line 10 of `moved2.txt`, clear of H's lines 1-7: no conflict.
So X does not clash with H's own change, and must not be named.

The case checks these facts with plain git after the run
(`test_flow_cross_wave_joint_holds.py:428-434`):
- L's head is an ancestor of H's head;
- `X, H` from the base fails at H (index 1);
- `L, X, H` merges cleanly;
- `L, P, H` and `L, R, H` merge cleanly, and `L, P, R, H` fails at H;
- `L, X, W, H` (the line without P and R) merges cleanly.

Then it asserts the run held H naming exactly `issue_P's, issue_R's (conflicts in
shared.txt)`, proposed `Conflicts with: P, R`, never mentioned `issue_L`, `issue_X`,
`issue_W` or `issue_V`, completed W→V→U, and exits 3.

How the code gets there (traced, then confirmed by the runs below):
- `_clash` → `_partners` has no leading revs, so it names X alone (`kind == "batch"`).
  Child-1's acceptance check fails, because P+R still clash, so `_together` runs
  (`integrate.py:1842-1848`).
- In `_together`, `lead == [L's head]`. X's trial `[L, X, H]` is clean, so X goes to the
  pair candidates. The pair trial `[L, P, R, H]` fails at H, so P and R are named.
  `_explains({P, R})` passes.
- With `_own_change` returning `[]`, X's trial `[X, H]` fails at H, so X is named. The joint
  set becomes `{P, R, X}`, which `_explains` also accepts. H is held naming X: wrong.

### Evidence that it binds the helper (mutation probe)

I temporarily put `return []` at the top of `_own_change` and ran the file with the
project's command (`cd template && PYTHONPATH=src python3 -m unittest
tests.test_flow_cross_wave_joint_holds`, the one `run-verify.sh` uses, under `timeout`):

- Case (6) FAILED: `"its change conflicts with issue_P's, issue_R's, already on the line
  from an earlier wave (conflicts in shared.txt)" not found in "flow: issue_H held out of
  the integration fold — its change conflicts with issue_P's, issue_R's, issue_X's, …"`.
- Cases (1)-(5) passed. This confirms the reviewer's finding about them.

Then I removed the probe. `git diff` of `integrate.py` matched the iteration-1 hunks
exactly, and no probe text is left.

## What the patch does (unchanged from iteration 1)

`template/src/pdca_harness/integrate.py` only. `flow.py` is not changed.

- **`_held_by_line`** (`integrate.py:1796`). Child-1's call site in `fold` is unchanged
  (`integrate.py:661-666`: `_held_by` first, `_held_by_line` second). Inside it:
  - `kind == "batch"` and `_explains(...)` → child-1's partners, as before (`:1842-1844`).
  - Neither `"batch"` nor `"line"` → None, as before (`:1845-1846`). So a clash with the
    base still stops, and the new code never sees it.
  - Otherwise, `_together` names the joint set, and `_explains` checks it (`:1847-1851`).
    An empty set, or the same set that already failed, gives None (a stop).
- **`_explains`** (`integrate.py:1859`): child-1's rule (e), moved out of `_held_by_line`
  with no code change, so the joint set gets exactly the same acceptance check.
- **`_own_change`** (`integrate.py:1887`): the helper this child owns (child-3 #749 reuses
  it). For each line bundle, `git merge-base <head> <bundle's head>`; a result not on the
  base becomes a leading rev. These are plain extra revs passed to the existing `_trial`,
  with no new worktree code and no squash.
- **`_together`** (`integrate.py:1916`): the minimal-set search, by clean or not clean only.
  - Guard (`:1939-1941`): if `base + lead + head` does not merge, it returns `[]`.
  - Size 1 (`:1942-1951`): `[*lead, L, head]` for each line bundle cut from the base. Fails
    at head → named; clean → pair candidate. A stacked bundle is named only if `_partners`
    named it.
  - Size 2 (`:1952-1955`): `[*lead, X, Y, head]` over the candidates, named only if it fails
    exactly at head.
  - Cost comment in the docstring (`:1934-1938`).
- `fold`'s docstring (`integrate.py:485-489`) says what is now held and what still stops.

Contracts left alone, as the brief asks:
- `_clash` (`integrate.py:1969`) is untouched. Its #694 docstring (`:1972-1996`) is the one
  the brief cites at `:1777-1781` on `9f7c446`.
- `_partners` (`:2016`) is untouched.
- `_held_by` (`:1769`) and its "all of `kept`" fallback (`:1793`) are untouched.

Flow wording: child-1's `_announce_conflict_holds` (`flow.py:1569`) and
`_report_conflict_holds` (`flow.py:1593`) already list several partners, so `flow.py` is
not changed (the brief says to change it only if it cannot).

## Tests

`template/tests/test_flow_cross_wave_joint_holds.py` (new), six real-git cases through
`flow._drive_and_act` on `StackFoldGit`, loaded by path as
`test_flow_same_wave_conflict.py:36-39` does:

1. `..._make_only_together_holds_naming_both` (`:270`): holds H naming P and R; W→V→U
   complete; no STOPPING; holds `{"H": "conflict"}`; rc 3.
2. `..._does_not_need_is_not_named` (`:291`): (1) plus an unrelated X; `issue_X` is in
   neither the hold line nor the proposal.
3. `..._in_one_file_name_all_three` (`:314`): names A, P and R. H's change, redone on a base
   holding K, A, P and R, merges cleanly onto the pushed line; H as it is does not.
4. `two_joint_clashes_..._nothing_else` (`:353`): pairs (P, R) and (M, N), plus an
   unrelated X; exactly M, N, P, R are named.
5. `..._only_three_line_bundles_make_together_still_stops` (`:379`): STOPPING, U stays
   PLANNED, rc 1.
6. `..._tried_on_its_own_change_only` (`:408`): new, see above.

**Flipped guard (as the brief expects):** child-1's
`test_a_clash_two_line_bundles_cause_only_together_still_stops` failed after this change,
as predicted. It now holds H naming `issue_A's, issue_P's, issue_R's (conflicts in
other.txt, shared.txt)`. I renamed it to
`test_a_clash_two_line_bundles_cause_only_together_holds_naming_them`
(`test_flow_cross_wave_fold_holds.py:363`) and changed its assertions to the hold (the
proposal `Conflicts with: A, P, R`, the whole chain COMPLETE, rc 3, plus the fact that the
line without A, P and R merges H). Same as iteration 1.

The brief's case (5),
`test_flow_same_wave_conflict.py::test_a_conflict_only_with_a_base_taken_in_mid_wave_still_stops_the_run`
(`:435`), passes unchanged.

The case (3) evidence the brief cites, `results/issue_739/iteration-v3/review-evidence/
probe-same-file.log`, still does not exist (there is no `review-evidence/` directory). Case
(3)'s shape was rebuilt from that review's description in iteration 1.

## Runs (this iteration)

- C4 gate, `engine/scripts/run-verify.sh` with `PDCA_BUNDLE` / `PDCA_WORKTREE` set, under
  `timeout`:
  - green leg: `test_flow_cross_wave_fold_holds` ran 9, OK; the new file ran 6, OK.
  - red leg (production hunks reverted): fold_holds 1 failure (the flipped guard); new file
    5 failures, cases (1)-(4) and (6), each on `'did not integrate' unexpectedly found …
    STOPPING`. Case (5) passes, as a guard should.
  - `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`, rc 0.
- Mutation probe, `_own_change` → `[]`: only case (6) fails (above).
- `test_flow_same_wave_conflict` + `test_flow_cross_wave_fold_holds` + the new file: ran 23,
  OK.
- `engine/scripts/run-suite.sh` (T3): root suite ran 24, OK; driver suite ran 2625, OK
  (skipped=2). That is one more than iteration 1's 2624: the new case.
- Formatter / hooks: the target has none (no ruff/black/flake8/pre-commit config, no active
  git hooks; CI lints docs, renders the template, and checks DCO). No added line is over 99
  characters; `git diff --check` is clean; no unused imports in the new file. The publish
  commit needs a DCO sign-off, which publish adds.

## Refute my own test

- **(a) Genuine red?** Yes, two ways. Production hunks reverted (C4 red leg): case (6)
  fails on `wave 1 did not integrate (issue_H's branch … STOPPING`, child-1's stop, and
  cases (1)-(4) fail the same way. Only `_own_change` disabled: case (6) fails because H
  is held naming `issue_X` too. That second red is the one the carry-forward asked for.
- **(b) Production path?** Yes. The cases call `flow._drive_and_act`, which runs the real
  `integrate.fold` → `_held_by_line` → `_clash` / `_together` / `_own_change` / `_explains`
  / `_trial`, with real git merges against a bare origin. Only the build leaf, the publish
  leaf (which still cuts and pushes real branches, H's from the real base `flow` built for
  it with `build_bundle_base`), and `gh` are stubbed, as in child-1's suite. The publisher
  is in `command` mode, so the fold is not a dry run.
- **(c) Fixture includes the fault?** Yes. Case (6) puts L really on the line and really
  under H (asserted: L's head is an ancestor of H's), and X really on the line. It proves
  with plain git that H's whole branch clashes with X while H's own change does not. Every
  other case asserts its joint clash the same way (`_merges(...) == 3` after both, `None`
  after either one).

## Notes for sign-off

- **Child-1's direct path can still name a bundle the clash does not need, when the held
  branch is built on a line bundle.** `_partners` (child-1, out of scope here) tries the
  head's whole branch from the base, with no leading revs. When the clash is direct only,
  child-1's acceptance check passes and `_together` never runs, so the extra name stays. I
  confirmed this with a temporary probe case (removed afterwards): L renames `two.txt`, H
  (on L) rewrites lines 1-7 of `moved2.txt`, X edits `two.txt` line 10, Y edits `two.txt`
  line 3. The run held H naming `issue_X's, issue_Y's (conflicts in moved2.txt)` and
  proposed `Conflicts with: X, Y`, although `L, X, H` merges cleanly and only `L, Y, H`
  fails at H. When a joint clash is also present, `_together` re-judges size 1 with the
  leading revs and drops X (case (6) shows this). The brief puts `_partners` and "anything
  child-1 already does" out of scope, so I did not change it. A possible follow-up, about 5
  lines in `_held_by_line`: when `kind == "batch"`, keep only the partners whose
  `[*_own_change(...), its, head]` trial fails at head (a stacked one keeps `_partners`'
  verdict), before `_explains`. That changes which bundles #747 names, so it is the
  human's call, perhaps with child-3 #749, which reuses `_own_change`.
- **Untested on purpose: the guard at `integrate.py:1939-1941`.** It returns `[]` (a stop)
  when the head does not merge even onto `base + lead`. Every merge-base in `lead` is in
  the head's own history, and `build_bundle_base` refuses members that do not merge
  cleanly, so reaching it needs a hand-made branch whose base resolved a conflict between
  two line bundles. It is a safety check: without it, every bundle would be named in that
  case.
- **Merge-base, not the bundle's head:** the case does not tell `merge-base` apart from the
  bundle's current head, because L's branch does not move after H is cut. They differ only
  when a prerequisite moves on after the held branch was cut from it, and that is child-3's
  stranded-by-moved-base case.
- Stated limits, as in the brief: a clash only three or more bundles make together stops
  (case 5 pins this), and so does a joint clash that needs a stacked line bundle.
- Joint holds use child-1's wording ("its change conflicts with issue_P's, issue_R's"),
  which does not say "together". If the human wants that word, it is a small `flow.py`
  follow-up.
- **Process slip:** while running the C4 gate I sent its output to
  `/tmp/issue748-c4.log`, outside the worktree and bundle folders I am allowed to write to.
  It holds only that gate's test output. I did not delete it (cleanup is the harness's job);
  it can be removed by hand.
