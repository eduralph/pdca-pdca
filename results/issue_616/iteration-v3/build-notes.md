# Build notes — issue 616 / stack-resume-carries-unmerged-prereqs (iteration 3)

Target: `eduralph/pdca-harness` @ `main`. Written in the cycle worktree
`$PDCA_WORKTREE` = `/home/eddie/pdca/pdca-harness.pdca-wt`, HEAD `f594d8e`: the brief's
verified `origin/main` (`c67a14d`) with #531, #590 and #591 folded on top (bundle
`stack-base` = `pdca-integration/main`). Every `path:line` below is on that tree **with
the patch applied** unless it says "base".

I started from the iteration-2 patch (it applied cleanly to `f594d8e`), kept its core —
the one pre-wave fold of earlier runs' prerequisites onto the run's own per-batch line,
the shared fold step `_fold_onto_line`, `carried +` in every later fold, the per-pair
holds, the `Stacks on` rule, the stale-record hold — and made the five changes the
iteration-2 sign-off asked for, plus two small ones the iteration-2 code review raised.

## The five sign-off items

1. **A CLOSED prerequisite holds its dependents and is never carried.** `merged.is_merged`
   only answers "merged or not", which cannot tell an open PR from a closed one, so
   iteration 2 carried a closed P and every same-target PR built on the line carried the
   rejected work. New `merged.pr_state` (`template/src/pdca_harness/merged.py:53-62`)
   returns the host's state — `"OPEN"`, `"CLOSED"`, `"MERGED"` — or `None` when not known.
   `_prereqs_to_carry`'s `verdict` (`template/src/pdca_harness/flow.py:828-844`) carries
   only on `"OPEN"` (`flow.py:841`); `"CLOSED"` is the new `_CLOSED` hold (`flow.py:842`).
   Test: `test_a_prerequisite_whose_pr_was_closed_unmerged_holds_its_dependents`
   (`template/tests/test_flow_resume_stack_prereqs.py:487`). It also starts a line for
   another, open prerequisite P3 in the same run and checks that the line (and U and D3
   built on it) holds P3 but never P's head.

2. **A missing `pr_url` or a `gh` failure holds only that prerequisite's dependents; it
   never stops the run.** `pr_state` returns `None` for both (no PR on record: nothing is
   asked; `gh` failing or missing: said on stderr). `verdict` turns `None` into a hold:
   `_UNREAD` when a URL is on record, `_NO_PR` when not (`flow.py:843`, `_recorded_pr`
   `flow.py:889-894`). Before, `None` read as "not merged" ⇒ carry, and the pre-wave fold
   of a merged P whose branch was deleted raised (`integrate.py:462-467`) and stopped the
   whole run. Tests:
   - `test_a_merged_prerequisite_with_no_pr_url_holds_only_its_dependents` (`:519`) — the
     exact case named: `pr_url: ""`, PR merged into main by hand, `fix/P` deleted. D held
     and named, U built on main, no stop, no `gh` call.
   - `test_a_gh_failure_holds_only_that_prerequisites_dependents` (`:546`) — `gh pr view`
     exits 1 for P's PR. D held; D3's open P3 still starts the line; D3 and U build on it.
   - `test_no_gh_holds_the_dependents_and_never_crashes_the_run` (`:577`) — `gh` not
     installed (`FileNotFoundError`). Replaces iteration 2's test of the same name stem,
     which expected D to be **carried** with no `gh`; the sign-off asked for the hold.

3. **Holds first; a line only for a dependent that is not held.** `_prereqs_to_carry` now
   works per dependent, not per edge (`flow.py:851-886`): it collects each drive-set
   bundle's same-target, out-of-batch `Depends on` and `Stacks on` prerequisites
   (`flow.py:853-864`), marks a bundle as *wanting* a line when one of its `Depends on`
   prerequisites is to be carried (`wants`, `flow.py:871`), gives a target a line only for
   a wanting bundle that nothing holds (`lined`, `flow.py:872`), and carries a
   prerequisite only for a bundle that is not held (`flow.py:882-885`). Test:
   `test_a_dependent_held_on_one_prerequisite_starts_no_line_for_another` (`:595`) — the
   sign-off's own case: D depends on carryable P and unpublished P2 ⇒ D held (named under
   P2), no line, nothing pushed, U on the plain base.

   How `Stacks on` fits in (unchanged rule, new place): a bundle's held `Stacks on`
   parents count against it only when it would build on the line (`holding`,
   `flow.py:866-869`; `on_line`, `flow.py:876`). So a bundle with a carryable `Depends on`
   P and an unpublished `Stacks on` Q is held (it would build on a line that cannot carry
   Q), while a bundle with only a `Stacks on` edge, on a target with no line, is left as
   it was before #616 — not judged, no `gh` call.

4. **Merged is asked before the stale-record check.** `verdict` asks `pr_state` first and
   returns "base" on `"MERGED"` before any hold is considered (`flow.py:837-838`). Order
   after that: no branch on record → stale record → open → closed → unknown
   (`flow.py:839-843`). Test: `test_a_merged_prerequisite_never_holds_however_old_its_record`
   (`:684`) — P merged, then its publish.json dated an hour before its SUMMARY.md; D
   builds on main, nothing held. (Green before #616 too, by design: it pins the order.
   Iteration 2's order would fail it — see mutation 4.)

5. **The `Stacks on` sentence is narrowed** to a line the pre-wave fold starts:
   `_prereqs_to_carry`'s docstring (`flow.py:775-779`: "A line THIS fold starts … Only
   that line: one first folded after a later wave … carries no earlier run's `Stacks on`
   parent, so a bundle stacking on one and pointed at it builds without that parent, as
   before #616") and the docs (`docs/07-crosscutting.md:696-699`). These were the only two
   places that claimed it (`grep -n "Stacks on" flow.py` → only `_prereqs_to_carry`). I did
   not change the behaviour, only the wording, as asked.

## Two more, from the iteration-2 code review

- **A dry run asks no host and holds nothing** (`flow.py:834-835`). Iteration 2 asked
  `gh` in a dry run (stub publisher) for every published prerequisite — before #616 a dry
  run made no `gh` call for a plain `Depends on`. Now a dry run plans the fold of each
  candidate, like the in-run dry fold plans each bundle as its would-be branch, and says
  so without claiming the PRs are unmerged (`flow.py:2195-2200`). A dry run never sets
  `integ` (`flow.py:2207-2208`), so no stack base changes. Test:
  `test_a_dry_run_asks_no_host_and_holds_nothing` (`:761`).
- **A red re-gate of the pre-wave line stops the run before wave 0** — already the
  behaviour (shared `_fold_onto_line`, `flow.py:943-981`), now with a test:
  `test_a_red_re_gate_of_the_pre_wave_line_stops_the_run_before_wave_0` (`:643`).

## Other code changes

- `merged.py`: the `gh pr view` call, its `OSError` guard and its parsing now live once,
  in `_pr_view` (`merged.py:81-103`), shared by `pr_state`, `is_merged` (`merged.py:50`)
  and `merged_head` (`merged.py:65-78`). Each keeps its exact argv (`--json state`,
  `--json state,headRefOid`), which `template/tests/test_merged.py` and
  `test_integrate_stack_bases.py:1175-1203` pin; both pass. `is_merged` behaviour is the
  same except that it no longer raises on a missing `gh` or on JSON that is not an object
  (both now read as not merged).
- `_hold_line` (`flow.py:897-922`): one stderr line per held prerequisite, naming why and
  what clears it, and exactly the dependents held on its account (sorted). Every reason
  starts `flow: <prereq> …` and contains `held this run`.
- `_drive_and_act` docstring (`flow.py:2080-2089`) and comments (`flow.py:2124-2128`,
  `:2181-2186`), `_runnable` docstring (`flow.py:694-703`), `_HOLDS` constants
  (`flow.py:751-761`): wording for the new holds.
- Docs (`docs/07-crosscutting.md:677-699`): lists every hold reason with its fix, says a
  held bundle starts no line, gives the re-fold failure example, and narrows `Stacks on`.

Kept, unchanged in behaviour from iteration 2: `_runnable`'s `held_pairs` check
(`flow.py:718-719`), `_record_predates_signoff` (`flow.py:925-940`), `_fold_onto_line`
(`flow.py:943-981`), the pre-wave block (`flow.py:2187-2208`), `carried +` in the in-run
fold (`flow.py:2347-2350`), the mid-run split-children note (`flow.py:818-821`).

## The test

`template/tests/test_flow_resume_stack_prereqs.py` (copied flat into the bundle too), 21
cases. Same fixture as iteration 2: real git, a bare `origin`, a primary checkout and a
"human" clone (the `StackFoldGit` shape, `test_integrate_stack_bases.py:115` on this
tree; the brief's `:113` is on `c67a14d`), copied
rather than imported. It drives the production `flow._drive_and_act` with `batch=` as a
re-issued `pdca flow <ids>` does. Stand-ins: `flow._drive_wave` (build/Check/sign-off),
`flow._publish_bundle` (real push + `publish.json`), `publish.draft_texts`, and the `gh`
binary (a fake `subprocess` inside `merged` only). New in the fixture: `_record` /
`_earlier` take `pr_url` (`""` = `gh pr create` failed), the fake `gh` can report
`CLOSED` or fail (state `"FAIL"` → exit 1), `_age_record`, `_held_exactly` (the hold line
names exactly these bundles) and `_on_the_plain_base`. It imports modules only — no
symbol the fix adds (checked: no `pr_state`, `_prereqs_to_carry`, `_hold_line`, … in the
file).

Red without the fix (14): the criterion (`:341`), line outlives a wave (`:393`), (a) no
branch (`:422`), per-pair hold (`:442`), stale record (`:464`), closed PR (`:487`), no
`pr_url` (`:519`), `gh` failure (`:546`), no `gh` (`:577`), holds first (`:595`), (d)
failing pre-wave fold (`:618`), red re-gate (`:643`), dry run (`:761`), `Stacks on`
parent carried on a line (`:825`). Green on both sides by design (7): (b) merged
(`:668`), merged however old its record (`:684`), (c) no patch (`:703`), other target / no
brief (`:726`), no out-of-batch prerequisite (`:749`), `Depends on (merged)` (`:784`),
`Stacks on` unchanged (`:802`).

### Refuting my own test

- **(a) Genuine red? Yes.** The project's C4 gate (`engine/scripts/run-verify.sh`, with
  `PDCA_BUNDLE` / `PDCA_WORKTREE` set) reverted the production hunks (`flow.py`,
  `merged.py`) and re-ran: `Ran 21 tests … FAILED (failures=14)` — 14 `FAIL:`, 0
  `ERROR:`, no `_FailedTest` (the module loads). Green leg: `Ran 21 tests … OK`. Verdict:
  `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`. On top of that, eight
  mutations of the fix, each run through the same script, each caught by exactly the
  test(s) meant for it (green leg red, nothing else failing), each undone afterwards:

  | # | mutation (what an earlier attempt, or a slip, would do) | caught by (only) |
  |---|---|---|
  | 1 | CLOSED carried like OPEN | closed PR test |
  | 2 | unknown state (`None`) carried — iteration 2's behaviour | no `pr_url`, `gh` failure, no `gh` (3 tests) |
  | 3 | line started, and P carried, for a held dependent — iteration 2 | holds-first test |
  | 4 | stale check before the merged check — iteration 2's order | merged-however-old test |
  | 5 | a dry run asks the host and holds — iteration 2 | dry-run test |
  | 6 | `Stacks on` starts a line (iteration-1 item) | `Stacks on` unchanged test |
  | 7 | holds keyed by prerequisite name, not pair (iteration-1 item) | per-pair test |
  | 8 | `except OSError` removed from `_pr_view` (iteration-1 item) | no-`gh` test, `FileNotFoundError` out of the run |

  After the last one, `git diff` in the worktree matched `patch.diff` byte for byte
  (`cmp`), and the final C4 run above was on that tree.
- **(b) Production path? Yes.** `_drive_and_act`, `_prereqs_to_carry`, `_hold_line`,
  `_record_predates_signoff`, `_fold_onto_line`, `_runnable`, `_point_at_integration`,
  `integrate.fold` (real git against the bare origin), `merged.pr_state` / `is_merged` /
  `merged_head` / `_pr_view`, `publish.read_stack_base` / `_stack_base_branch` and
  `worktree._target` all run unmocked. The stand-ins (build/Check/sign-off leaf, text
  drafting, publisher leaf, the `gh` binary, and `gates.run_integration` in the one
  re-gate case) are not code this fix changes.
- **(c) Fixture includes the fault? Yes.** P is really outside the drive set (only in
  `batch`), really COMPLETE (a recorded sign-off), its branch really pushed to the bare
  origin. Closed: the fake host answers `{"state": "CLOSED"}` and `fix/P` is still on
  origin, so carrying it was possible. No `pr_url`: the record really has `"pr_url": ""`,
  P really merged into origin's main by a human clone, and `fix/P` really deleted.
  `gh` failure: the host call really exits 1; no `gh`: it raises `FileNotFoundError`,
  which is what `subprocess.run` raises for a missing executable. Holds first: P really
  carryable (published, open) and P2 really unpublished. Merged-however-old: the record's
  mtime really precedes SUMMARY.md's (asserted in `_age_record`).

## Alternatives ruled out (with cost)

- **`pr_state` as a third copy of the host call** instead of the shared `_pr_view`:
  iteration 2's `is_merged` (+8/-4 in `merged.py`) plus a new ~20-line `pr_state` with its
  own `pr_url` read, `try/except OSError`, exit-code check, stderr line and JSON parse —
  about +28/-4, leaving three copies of the same block. The refactor is +33/-21 with one
  copy; the argv each caller sends is unchanged and pinned by the existing tests.
- **Look the PR up by branch when `pr_url` is missing** (`gh pr list --head <branch>
  --state all --json state,url`) instead of holding: about 10 lines in `merged.py`, plus
  `merged_head` would need the same fallback for the fold's gone-branch path
  (`integrate.py:462`), another ~5. It would let a by-hand PR be judged without a manual
  edit. Not done: the sign-off asked for a hold, and it is new host behaviour beyond the
  brief. A possible follow-up (see below).
- **Also predict `_runnable`'s own skips** (an unmerged out-of-batch `Depends on
  (merged)`, an unfinished out-of-batch prerequisite) when deciding whether a dependent
  "needs" the line. Not done: those states can change during the run (a PR merging
  mid-run). If the pre-wave step left the line out because it predicted a skip, and the
  PR then merged, the dependent would build later without the carried prerequisite —
  a wrong base. Making the prediction safe needs a binding hold for those pairs too
  (about 10 lines plus reordering `_runnable`'s checks). As shipped, the only effect is
  that a line is started for a dependent `_runnable` then skips: U's PR shows the carried
  prerequisite's changes until it merges — never a wrong base.
- **Walk a carried prerequisite's own prerequisites** (see the first item below). The
  brief: "do not add a second walk unless the test shows one is needed".

## Things the human should know at sign-off

- **Transitive closed prerequisite — not handled.** If P2 (open) was built in an earlier
  run on a line that held P, and P's PR is closed afterwards, P2's branch still contains
  P's commits. Carrying P2 then puts P's rejected work on the line, under every
  same-target PR of the run. P2's own PR already contains it, so the problem predates the
  run, but the line spreads it. The fix would be a walk of each carried prerequisite's
  declared prerequisites, holding on a closed one (about 12 lines + one `gh` call per
  prerequisite walked, and a choice about what an *unknown* transitive state means).
  The brief rules the walk out unless a test needs it; I would make it its own issue.
- **The stale-record remedy can lead to a second hold.** Re-publishing a bundle whose
  draft PR is still open pushes the branch (the open PR picks it up) but `gh pr create`
  fails, so `publish.json` gets `pr_url: ""` (`publish.py:402-431`). The next run then
  holds its dependents as "records no PR URL … Add its PR's URL to that file as
  `pr_url`". Loud and correct, but two steps. The `gh pr list --head` lookup above would
  make it one.
- **Merged wins, always** (sign-off item 4). Edge: a bundle whose PR merged and that was
  then iterated and re-accepted without re-publishing reads as merged; its dependents
  build on main, which has the first attempt, not the second. Iterating a merged bundle
  is unusual; I followed the sign-off.
- **A held dependent is reported twice:** the hold line before wave 0, then `_runnable`'s
  generic "skipped — prerequisite(s) not ready (P)" at its wave. The in-batch
  `held_unpushed` path already does the same. Cosmetic.
- **Case (d) is now narrower:** the run stops before wave 0 when the host reports the PR
  **open** and the fold cannot carry its branch (deleted, conflicts, push refused, red
  re-gate). When the host cannot be asked, or reports it closed, the dependents are held
  instead and the run goes on — sign-off items 1 and 2.
- **More `gh` calls in a real stack-mode run:** one `gh pr view` per earlier-run
  prerequisite that has a patch, a target and a recorded PR URL, asked once per run
  (cached per prerequisite). None in a dry run, none for `Stacks on`-only bundles on a
  target with no line.
- **Live validation** (the offline test stubs `gh` and the publisher leaf): in an
  instance with stack mode and a real publisher, publish P (`org/repo @ main`), leave its
  PR open, then re-issue `pdca flow P D U` with D `Depends on: P`. Before D builds, check
  `results/issue_D/stack-base` names `pdca-integration/main-r<key>` and
  `git merge-base --is-ancestor origin/fix/P origin/<that line>` exits 0. Then close P's
  PR without merging and re-issue: D is held with "closed without merging", U builds on
  main. Then blank `pr_url` in P's `publish.json` and re-issue: D is held with "records
  no PR URL", nothing stops.
- Not changed: `--no-publish`, merge mode, `Depends on (merged)` (#186), the branch
  naming (#591), retargeting PRs, pruning old lines (#454). Mid-run split children stay
  out of scope (docstring `flow.py:818-821`).

## Checks run (all through the project's scripts in `pdca-pdca/engine/scripts/`)

- C4 `run-verify.sh`: PASS (numbers above). Worktree left equal to `patch.diff`.
- T3 `run-suite.sh` (final tree): root suite `Ran 24 tests … OK`, driver suite
  `Ran 2346 tests … OK (skipped=2)`.
- T2 `run-docs-check.sh`: docs lint OK, 22 pages rendered, link audit OK.
- C5 `run-prod-path.py`: the added test imports `pdca_harness`.
- Commit-readiness: the target has no formatter, linter config or commit hooks (no
  `.pre-commit-config.yaml`, no ruff/flake8/black config, `core.hooksPath` unset; CI runs
  the docs checks and the render suite, both green above). `git diff --check` is clean;
  no added line is over 100 characters.
- No external dependency beyond what the brief lists (none) was needed.

## Housekeeping

Scratch logs inside the bundle: `results/issue_616/.c4-run.log` (last C4 run) and
`.t3-run.log` (last T3 run). I did not delete them; cleanup is the harness's. The
worktree index has the new test as intent-to-add (`git add -N`), so `git diff` shows it;
nothing else is staged. No branch pushed, no PR opened.
