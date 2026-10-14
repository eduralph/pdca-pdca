# Build notes — issue 655 / merged-prereq-gate-checks-the-line (iteration 2)

Worktree: `/home/eddie/pdca/pdca-harness.pdca-wt-l0`, base `420f8b4` (the run's integration
line `pdca-integration/main-r8bf6d15b2de3`, which already holds 629, 605, 633, 651, 658).
All `path:line` below are on that base with this patch applied. They have moved from the
brief's `b5f5c29` numbers because 629 landed in `_runnable` first.

## What the carry-forward asked for, and what I did

1. **C5: the recovery advice was wrong.** The v1 message and docs said "re-run once this
   run ends, so it is cut from a base that has the merge". A re-run of the same batch does
   not do that: W is finished, so the #646 carry (`flow.py:1008`, reading origin's line at
   `flow.py:1056`) continues the line already on origin from its old tip, and D is held
   again. I changed the advice to the path that works: **once this run ends, delete the
   line on origin, then re-run.** With no line on origin, the carry (or the run's first
   fold) starts the line from the base (`integrate.py:425`, `:472`), which has the merge.
   The message says why the plain re-run is not enough ("a re-run that finds the line on
   origin may continue it and hold issue_D again"). The test
   `test_the_way_out_is_to_delete_the_line_then_re_run`
   (`template/tests/test_flow_merged_prereq_on_line.py:293`) walks the whole path: run 1
   holds D; run 2 (same batch, line still on origin) continues the line at the same tip and
   holds D again; then the line is deleted on origin; run 3 builds D on a new line whose tip
   has P's merge commit and W's branch. I did not add any line refresh (out of scope).

2. **False hold for a carried prerequisite.** v1 counted P as on the line only if its PR's
   `mergeCommit` was an ancestor of the tip. On a resumed run the carry continues an old
   line that already has P's PR **head**, while main's merge commit is not on it, so v1 held
   D although P's work was there. Now P counts as on the line when **either** the merge
   commit **or** the PR head is an ancestor of the recorded tip
   (`flow.py:857-863`). Both come from one `gh pr view --json
   state,headRefOid,mergeCommit` call (`merged.merge_and_head`, `merged.py:149-169`). The
   test `test_a_carried_prerequisite_whose_head_is_on_the_line_counts`
   (`template/tests/test_flow_merged_prereq_on_line.py:269`) builds exactly the reviewer's
   case with real git: an earlier run's fold put P's head on the line, P's PR then merged
   into main with a merge commit, the re-issued run names P and E's plain `Depends on: P`
   makes the carry continue the line. It asserts D is built at the old tip, the tip has
   P's head, and the tip does NOT have the merge commit (so the head check is what lets
   it through). Criterion (4) still holds: a squash merge passes on `mergeCommit`.

## What changed (production)

- `template/src/pdca_harness/merged.py`
  - `merge_and_head(cfg, dep_id)` (`merged.py:149-169`): `(merge commit, head)` of the
    recorded PR when it is MERGED, `""` for a field `gh` does not report, `None` when the
    PR is not merged or `gh` cannot be read (missing, failing, bad JSON). Fail-closed and
    silent, like `pr_state`.
  - `_pr_view(pr_url, fields)` (`merged.py:185-200`): the one `gh pr view --json` call,
    `OSError` guard and JSON parse, shared by `merge_and_head` and `pr_state`. `pr_state`
    (`merged.py:172-182`) now uses it; same arguments to `gh`, same results (the advisory
    review's reuse finding).
  - Module docstring line for `merge_and_head` (`merged.py:24-26`).
- `template/src/pdca_harness/flow.py`
  - `_runnable` takes `lines=` (`flow.py:687`): target → `(line branch, recorded tip)`.
    Docstring paragraph `flow.py:728-737`.
  - Per-call caches: the fetched checkout per repo (`flow.py:740`) and the verdict per
    (prerequisite, target) (`flow.py:741`), so several dependents of one P in a wave cost
    one fetch and one extra `gh` call, not one each (the advisory efficiency finding).
  - The gate (`flow.py:773-785`): after `merged.merged_into` says yes, if d is targeted,
    the run has a line with a recorded tip for d's target, and P has a non-empty patch, ask
    `_line_lacks_merge`. A close/no-fix P is not checked (it merged nothing). A `None` tip
    (dry-run) is skipped, so a dry-run still holds nothing.
  - The held line (`flow.py:803-814`): ONE stderr line naming d, each prerequisite with its
    reason, "their PR merged into <base> (<repo>)", the line and its 12-char tip, "does not
    have that merge" (or "is not known to have that merge" when the check failed), and the
    way out. It never says the run cut the line.
  - `runnable.append` also needs `not off_line` (`flow.py:826`).
  - `_line_lacks_merge` (`flow.py:831-868`): reads the checkout through
    `integrate.carry_view` (fetches first, read-only, no lock; `integrate.py:205`), gets
    `merged.merge_and_head`, and asks `integrate._carries(view, c, …, of=<tip>)`
    (`integrate.py:648`) for the merge commit, then the head. A commit the clone lacks is
    "not on the line". Returns `None` (on the line), `(reason, True)` (known to lack it:
    the merge commit was read and neither commit is on the tip) or `(reason, False)` (could
    not check: fetch failed, merge commit unreadable, git failure). A MERGED PR with no
    `mergeCommit` and a head not on the line is "could not check": the head alone cannot
    rule out a squash or rebase merge that the line does have.
  - Caller (`flow.py:2334-2336`): `lines={tgt: (branch, folded_tips.get(tgt)) for tgt,
    branch in integ.items()}` — the same maps `_point_at_integration` uses to write d's
    stack base and tip (`flow.py:2380`), so the gate checks the commit d is cut from. The
    carry seeds them (`flow.py:1094`) and each in-run fold updates them (`flow.py:2477`,
    `:2480`). Merge mode never fills `integ` (no carry, `flow.py:2309`; the merge branch at
    `flow.py:2443` skips the fold), so merge mode is unchanged.
- `docs/07-crosscutting.md:744-759`: a paragraph after the #647 one. It says the line does
  not follow the base, that the dependent also waits until the line has the merge commit
  or the PR head, that it fails closed, and the way out (delete the line once the run
  ends, then re-run), including after the #647 "wait for the merge and re-run" advice.

## Alternatives ruled out

- **Check only `mergeCommit` (v1).** Rejected by the carry-forward: false hold for a
  carried prerequisite. The mutation check below shows the new test catches it.
- **Check only the head (`headRefOid`).** Wrong for squash and rebase merges: the head is
  never on the base, so a line started after such a merge has P's work and not the head.
  Criterion (4)'s test (`…:230`) catches that.
- **Use the run's own record of heads (`carried_heads`) instead of `gh`'s head.** The carry
  folds with `carried=None` (`flow.py:1082-1084`, docstring of `_fold_lines`), so that
  record never holds a carried finished id, and it cannot know a head an earlier run put on
  the line. It would miss exactly the reviewer's case.
- **Advise "re-run" with a different id list, or "wait until every PR on the line merges and
  run D alone".** The first works only because a different batch gets a different line
  name (`integrate.integration_branch`, `integrate.py:90`); the second needs W merged too
  (D's plain `Depends on: W` is then held by #647 until W merges). Deleting the line is the
  remedy the carry already gives for a line it cannot use (`_CARRY_HINTS["line"]`,
  `flow.py:971`).
- **Fold `merged_head` into `_pr_view` as well.** `merged_head` prints a stderr line on a
  `gh` failure but stays silent on bad JSON; one shared helper cannot tell those apart, so
  it would need its own branch for the print — about the same 20 lines it has now. Left
  as it is (out of the brief's scope).
- **One `gh` call instead of two per checked prerequisite.** `merged_into` already reads the
  PR state; returning the commits from it would change its return type and contract
  (`merged.py:70-114`, "Only `flow._runnable` calls it", but the brief keeps it as is).
  The per-call cache keeps the second call to one per (prerequisite, target) per wave.
- **Refresh or re-cut the line.** Declined at Plan.

## Tests — `template/tests/test_flow_merged_prereq_on_line.py` (new, 9 cases)

Real git (the `StackFoldGit` fixture, loaded by path as
`test_flow_resume_stack_prereqs.py:36-39` loads it), driven through `flow._drive_and_act`
with a non-stub publisher. `gh` is stubbed in front of `subprocess.run` and answers
`state`, `headRefOid` and `mergeCommit{oid}`. `integrate.fold` is wrapped only to run a hook
once, after the first real fold returns.

| Case | Criterion | Pre-fix | Post-fix |
|---|---|---|---|
| merge after line started, `Depends on (merged)` (`:202`) | (1) | FAIL: D built on the line | OK: held, one line |
| merge after line started, plain `Depends on` (`:212`) | (2) | FAIL | OK |
| merge-commit merge before run (`:222`) | (3) | OK | OK |
| squash merge before run (`:230`) | (4) | OK | OK |
| `mergeCommit` query fails (`:241`) | (5) | FAIL | OK: held, "could not be read" |
| checkout fetch fails (`:249`) | (5) | FAIL | OK: held, "could not be fetched" |
| no line for D's target (`:257`) | (5) | OK | OK: built from the base |
| carried P, head on line, merge commit not (`:269`) | carry-forward 2 | OK | OK (FAIL under v1's logic) |
| the way out: re-run holds again, delete line, re-run builds (`:293`) | carry-forward 1 | FAIL | OK |

Runs, all through the project's own scripts (each wrapped in `timeout`):

- C4: `PDCA_BUNDLE=… PDCA_WORKTREE=… ./engine/scripts/run-verify.sh` →
  green leg `Ran 9 tests … OK`; red leg `Ran 9 tests … FAILED (failures=5)`, the five
  listed above, every one an assertion failure (`'issue_D' unexpectedly found in {…
  'issue_D': ('pdca-integration/main-r1bf7d0372cf7', '<tip>')}`). Final line:
  `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`.
- T3: `./engine/scripts/run-suite.sh` → root suite `Ran 24 tests … OK`; driver suite
  `Ran 2451 tests … OK (skipped=2)`. That includes every case in
  `test_flow_out_of_batch_prereq_hold.py`, `test_flow_resume_stack_prereqs.py` and
  `test_integrate_stack_bases.py` (its `MergedHead` / `pr_state` cases too).
- T2: `./engine/scripts/run-docs-check.sh` → `lint_docs: OK`, `render_site: link audit OK`.
- Host CI parity: `engine/scripts/run-host-ci.sh` from the worktree → docs lint clean, site
  render + link audit clean.
- C5: `PDCA_PROD_PACKAGE=pdca_harness ./engine/scripts/run-prod-path.py` → `1 added
  driver-suite test(s) import the production package 'pdca_harness'`.

### Mutation check (the carried case binds the head check)

I changed `flow.py:862` to check the merge commit only (v1's logic) and ran C4: the green
leg failed on exactly one case, `test_a_carried_prerequisite_whose_head_is_on_the_line_counts`
(`'issue_D' not found in {'issue_E': …}` — D held, E built). I then restored the line;
`git diff` matches `patch.diff` byte for byte.

## Refute-your-own-test

- **(a) Genuine red?** Yes. The C4 script reverted the production hunks (`flow.py`,
  `merged.py`), kept the test, and ran it: 5 of 9 cases FAIL on assertions, because D was
  built on the line at a tip without P's merge (and, in the way-out case, already in run 1).
  The 4 green-both cases are the ones the brief and carry-forward say must stay green: (3),
  (4), no line, and the carried prerequisite (green before #655 and with this fix; red under
  v1's logic, shown by the mutation check).
- **(b) Production path?** Yes. The tests call the real `flow._drive_and_act` → the real
  `_carry_finished`, `_runnable`, `merged.merged_into`, `_line_lacks_merge`,
  `merged.merge_and_head` / `merged._pr_view`, `integrate.carry_view`, `integrate._carries`
  and the real `integrate.fold` (wrapped only to run a hook after it returns). Stubbed: the
  build/sign-off leaves (`_drive_wave`), publish (`_publish_bundle`, which is the fixture's
  real-git publish), `publish.draft_texts`, and `gh` (the brief says to stub it).
- **(c) Fixture includes the fault?** Yes. P's PR is really merged into `main` on the bare
  origin (`fx._merge_pr`, or a real `git merge --squash` + push) after the real wave-0 fold
  pushed the line; the test asserts the line lacks both the merge commit and P's head
  before it checks the hold. The carried case really folds P onto an earlier run's line and
  asserts the merge commit is not on it. The way-out case really deletes the line on the bare
  origin (`git branch -D`) and the next run's real fetch prunes it. The fetch-failure case
  points the real checkout's `origin` at a path that does not exist.

## Commit-readiness

The target has no formatter config and no commit hooks (no `.pre-commit-config.yaml`, no
`core.hooksPath`, only `*.sample` files in `.git/hooks`, no ruff/flake8/black/mypy in
`.github/workflows` or `CONTRIBUTING.md`). CONTRIBUTING.md asks for a DCO sign-off
(`git commit -s`), which publish adds. No added line is longer than 96 characters.

## Left as is, on purpose

- The fetch-failure reason quotes `integrate._fetch`'s own error, whose tail says "the fold
  cannot see the branches it merges" (`integrate.py:874-875`). I prefixed it with "its
  checkout could not be fetched to check:" but did not cut the tail off by string-splitting
  another module's message.
- The #647 held line still says "wait until their PR merges …, then re-run". After that
  merge, a re-run whose carry continues the old line now gets this hold, whose line gives
  the next step; the docs paragraph says so. I did not reword #647's message (not in the
  brief's scope).
- Deleting the line makes a later `pdca publish` of an accepted-but-unpushed bundle built on
  it refuse (`publish._line_tip_refusal`, `publish.py:700`). That is already the documented
  result of any re-run that replaces the line (`docs/07-crosscutting.md:689-692`).
- The five deferred findings (`deferred-findings.json`) are for the human; not build work.

No external dependency beyond the brief's (Python 3.11+, git; `gh` stubbed). Nothing was
pushed and no PR was opened. I wrote no files outside the worktree and this bundle.
