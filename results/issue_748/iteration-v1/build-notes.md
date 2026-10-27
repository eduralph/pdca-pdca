# Build notes — #748 name the joint partners of a cross-wave fold clash

Target: eduralph/pdca-harness, built on the run's line `pdca-integration/main-r547f8028520f`
at `72a774a` (#738 and #747 folded on top of `9f7c446`). All `path:line` below are on that
tip with this patch applied.

## What changed

`template/src/pdca_harness/integrate.py` only. No change to `flow.py`.

- **`_held_by_line`** (`integrate.py:1796`): child-1's call site in `fold` is unchanged
  (`integrate.py:661-666`; `_held_by` first, `_held_by_line` second). Inside it:
  - `kind == "batch"` and `_explains(...)` → return child-1's partners, as before
    (`integrate.py:1842-1844`).
  - `kind` is neither `"batch"` nor `"line"` → None, as before (`:1845-1846`). So a clash
    with the base (`"base"`) still stops and never reaches the new code.
  - Otherwise (`"batch"` whose partners fail rule (e), or `"line"`, where no bundle
    clashes alone), `_together` names the joint set, and `_explains` checks it (`:1847-1851`).
    If the set is empty, or the same as the partners that already failed, the result is None
    (a stop).
- **`_explains`** (`integrate.py:1859`): child-1's rule (e) block moved out of
  `_held_by_line` into its own function, with the code unchanged, so the joint set gets the
  exact same acceptance check (prerequisite rebuild, the "a bundle left on the line brings a
  partner back" check, the final trial).
- **`_own_change`** (`integrate.py:1887`): the own-change helper the brief gives to this
  child (child-3 #749 reuses it). For each line bundle, it runs `git merge-base <head> <L's
  head>`. If the result is not on `base_ref`, it goes into the list of leading revs. These
  are plain extra revs passed to the existing `_trial`, with no new worktree code. Nothing is
  squashed.
- **`_together`** (`integrate.py:1916`): the minimal-set search, by clean or not-clean only:
  - Before anything else, if `base + lead + head` does not merge, it returns `[]`
    (`:1939-1940`). Without this guard, every size-1 trial would fail at `head`, and every
    bundle would be named.
  - Size 1 (`:1943-1950`): for each line bundle cut from the base (empty `under`), the
    trial is `[*lead, L, head]`. If it fails at `head`, L is named. If it is clean, L becomes
    a pair candidate. If it fails earlier (at L itself), L is neither named nor a candidate.
    A stacked bundle (non-empty `under`) is named only if `_partners` named it (passed in as
    `partners`), because the brief keeps stacked bundles out of the new search.
  - Size 2 (`:1951-1954`): for each pair of the "clean alone" candidates, the trial is
    `[*lead, X, Y, head]`, and the pair is named only if it fails exactly at `head`. Bundles
    named at size 1 are never in a pair (a set holding one of them would not be minimal).
  - The cost comment is in the docstring (`:1934-1938`).
- `fold`'s docstring (`integrate.py:485-489`) now says what is held and what still stops.

Contracts left alone, as the brief asks:
- `_clash` (`integrate.py:1968`) is untouched; its docstring is the one the brief cites at
  `:1777-1781` on `9f7c446`.
- `_partners` (`:2015`) is untouched.
- `_held_by` (`:1769`) is untouched. Its "all of `kept`" fallback (`:1793`) is the #674
  together-naming this child narrows: `_held_by` names *every* bundle of the wave when none
  conflicts alone; `_together` names only the bundles in a minimal set of size 1 or 2.

### Flow wording

I checked child-1's announce on the folded tip first: `_announce_conflict_holds`
(`flow.py:1569-1590`) and `_report_conflict_holds` (`flow.py:1593-1612`) already list
several partners (`issue_P's, issue_R's, already on the line from an earlier wave`;
`declare \`Conflicts with: P, R\``). The brief says to change the wording only if it cannot
list several partners, so `flow.py` is not changed.

## Tests

New: `template/tests/test_flow_cross_wave_joint_holds.py`. These are real-git cases through
`flow._drive_and_act` on `StackFoldGit`, loaded by path as `test_flow_same_wave_conflict.py:36-39`
does. The stubs are copied from `test_flow_cross_wave_fold_holds.py`, trimmed. I chose not to
subclass that class, because subclassing would run all of child-1's tests a second time from
this file.

The joint clash is the rename shape from the #739 iteration-3 review: P renames `shared.txt`
to `moved.txt`, R rewrites seven of its ten lines, and H edits line 10. After P alone, git
follows the rename. After both, the file is below git's 50% similarity threshold, so H's
edit meets a deleted file. The cited `review-evidence/probe-same-file.log` is **not** in
`results/issue_739/iteration-v3/` (no `review-evidence/` directory). I rebuilt case (3)'s
shape from the review's description (`iteration-v3/check-review.md:19`): A edits line 10, P
renames, R rewrites lines 1-7, H edits line 10.

Each case first checks the fixture's own facts with plain git (`_merges`), then what the run
did:
1. `..._make_only_together_holds_naming_both`: holds H naming `issue_P's, issue_R's`,
   proposes `Conflicts with: P, R`, W→V→U complete, no STOPPING, holds `{"H": "conflict"}`,
   rc 3.
2. `..._does_not_need_is_not_named`: (1) plus X (changes `x.txt`, adds `x2.txt`). `issue_X`
   appears in neither the hold line nor the end-of-run proposal.
3. `..._in_one_file_name_all_three`: names A, P, R. The proposed rebuild is H's line-10 edit
   redone on a branch holding K, A, P, R. It merges cleanly onto the pushed line, and H as
   it is does not.
4. `two_joint_clashes_..._name_both_pairs_and_nothing_else`: the pairs (P, R) in `shared.txt`
   and (M, N) in `two.txt`, plus an unrelated X. Exactly M, N, P, R are named; the line
   merges a wave in name order, so that is the order printed.
5. `..._only_three_line_bundles_make_together_still_stops`: P renames, R rewrites lines 1-3,
   S rewrites lines 5-7. Each pair merges with H, and all three together do not. The run
   still prints STOPPING, U stays PLANNED, rc 1. (My first try had S on lines 4-6. Edits on
   touching lines conflict in git, so R+S conflicted on their own. Moving S to 5-7 fixed it.)

**Flipped guard (as the brief expects):** child-1's
`test_a_clash_two_line_bundles_cause_only_together_still_stops` in
`test_flow_cross_wave_fold_holds.py` failed after this change, as predicted: it now holds H
naming `issue_A's, issue_P's, issue_R's (conflicts in other.txt, shared.txt)`. I renamed it
to `test_a_clash_two_line_bundles_cause_only_together_holds_naming_them`
(`test_flow_cross_wave_fold_holds.py:363`) and changed its assertions to the hold:
- the hold line, and the proposal `Conflicts with: A, P, R`;
- the whole chain COMPLETE, holds `{"H": "conflict"}`, rc 3;
- one more fact: the line without A, P and R merges H.

Child-1's other "still stops" cases stay stops, because the pair search finds nothing new:
- `..._another_line_bundle_was_built_on_...` and `..._carried_partner_that_a_line_bundle_holds_...`:
  no new pair, so the set equals `partners` → None.
- `..._prerequisite_does_not_explain_alone_...`: 20 is stacked, so it is never in a pair.
- `..._head_no_longer_fits_the_base_...`: A's size-1 trial fails at A, not at Y, so A is
  never named.

Case (5) of the success criterion,
`test_flow_same_wave_conflict.py::test_a_conflict_only_with_a_base_taken_in_mid_wave_still_stops_the_run`
(`:435`), passes unchanged.

## Runs

- New file with the fix: 5/5 OK (`cd template && PYTHONPATH=src timeout 900 python3 -m
  unittest tests.test_flow_cross_wave_joint_holds`, the command INTEGRATION.md §3 names,
  with a timeout added).
- Production hunks reverted (`git apply -R` of the integrate.py diff only): cases (1)-(4)
  FAIL, each on `'did not integrate' unexpectedly found … STOPPING — later waves not run`.
  Case (5) passes, as a guard should.
- `engine/scripts/run-verify.sh` (the C4 gate) on the bundle:
  `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`, rc 0.
- Child-1's suite + `test_flow_same_wave_conflict`: 17 OK after the flip. Before the flip,
  only the expected guard failed.
- Full offline driver suite (`discover -s tests` in `template/`): `Ran 2624 tests … OK
  (skipped=2)`.
- Formatter / hooks: the target has none (no ruff/black/pre-commit config; CI lints only
  docs). No added line is over 99 chars (the two 100-char lines at `integrate.py:186-187`
  were there before).

## Refute my own test

- **(a) Genuine red?** Yes. With only the `integrate.py` hunks reverted, cases (1)-(4) fail
  on `STOPPING` and the chain left unbuilt (run above, and again through `run-verify.sh`,
  which reported C4 PASS).
- **(b) Production path?** Yes. The tests call `flow._drive_and_act`, which runs the real
  `integrate.fold` → `_held_by_line` → `_together` / `_explains` / `_trial` with real git
  merges on a bare origin. Only the build leaf, the publish leaf (which cuts real branches
  and pushes them) and `gh` are stubbed, as in child-1's suite. The publisher is in
  `command` mode, so the fold is not a dry run.
- **(c) Fixture includes the fault?** Yes. Each case asserts with plain git that the clash
  happens: H merges after P alone and after R alone, but not after both (`_merges(...) ==
  3`). Case (2) has the unrelated X really on the line. Case (5) asserts that every pair
  merges and the trio does not.

## What I considered and ruled out

- **Putting the search in `_clash`:** ruled out by the brief, because it would change the
  #694 carry's contract.
- **Using `_clash`'s `partners` as size 1 unchanged:** for bundles cut from the base, I
  redo the size-1 trial with the leading revs, so the size-1 test also uses H's own change
  only. When H shares nothing beyond the base with any line bundle, `lead` is empty and the
  trial is `_partners`'s trial (`[its, head]` on `base_ref`). Stacked bundles keep
  `_partners`'s verdict, because `_partners` alone knows how to try them on what they were
  built on.
- **A greedy smallest-set search on a squashed head (#739 v4 `_together`):** not copied.
  The squash is the bug the brief names, and the greedy search is not minimal-set naming.
- **Counting files or hunks:** never used. Every decision is a trial that merges cleanly or
  does not.

## Limits / notes for sign-off

- **The leading revs are exercised but not proven by a test.** In every case H depends on
  K, so `lead == [K's head]` and the leading-rev path runs. But no case has a branch whose
  result differs with or without the leading revs: that needs a head holding an older tip
  of a line bundle that conflicts with another. That is child-3's (#749) territory, and the
  brief's criterion does not ask for it.
- Stated limits, as in the brief:
  - a clash only three or more bundles make together stops (case 5 pins this);
  - a joint clash needing a stacked line bundle stops.
- Joint holds use child-1's wording ("its change conflicts with issue_P's, issue_R's"), which
  does not say "together". The brief keeps the wording unless it cannot list several
  partners. If the human wants "together" in the wording, it is a small `flow.py` follow-up.
