# Build notes — issue 673 / fold-stops-on-a-revert-brought-by-a-bundle-branch (iteration 4)

Base: the worktree at `ebef78c` (`pdca-integrate: issue_693`, on top of `2be8a16` issue_672
and `d6057eb`), the same base as iterations 2 and 3. Every `path:line` below is on the
patched tree in `$PDCA_WORKTREE` unless it says "base".

I started from iteration 3's patch (it still applies cleanly) and changed only what the
carry-forward asked for: the wording of the refusal when a bundle's branch merge is refused.
These stay exactly as in iteration 3:

- detection (which paths count as removed);
- the keep/refuse decision;
- who counts as an owner of a path (`names`);
- the #623 base-merge message.

## What the carry-forward asked

In the pinned history (two branches share a commit and neither holds the other's current
tip), the bundle-branch refusal said "merging issue_B's branch origin/fix/B would remove
issue_A, issue_B's work … a.txt (issue_A, issue_B)". That reads as if B removes its own
work. The ask:

- never describe the incoming bundle as removing its own work;
- name the bundle(s) whose work is removed;
- when git cannot tell which branch made the shared commit, say so plainly;
- update the pinned test;
- keep every other test and the base-merge message byte-compatible.

## What changed (`template/src/pdca_harness/integrate.py`)

1. **`_undone_paths`** (`:973-1036`) also returns, for each path, `groups`. For each line
   commit that changed the path, `groups` holds the bundles that have that commit as their
   own: one bundle, or the several that share it (`:1032`, `:1035`). It is built from the
   same `own` sets and `touched` list that `names` comes from, so it adds no git call.
   `names` is computed exactly as before (`:1033`). The tuple grows from 3 to 4 elements.
   Nothing outside `integrate.py` reads it: no test calls `_undone_paths`.
2. **`_removed`** (`:853-863`) unpacks the 4-tuple and ignores `groups`. Its formula is
   unchanged, so the base-merge refusal (`_take_in_base`, `:840-847`) is byte-identical.
   That code was inline at base `integrate.py:789-792`; iteration 3 moved it here.
3. **New `_branch_removed`** (`:866-887`), used only for a bundle's branch merge:
   - If every commit that changed a removed path belongs to exactly one bundle, and that
     bundle is not the incoming one, it returns `_removed`'s text (`:876-878`). This is
     the common case (one other bundle, no doubt), and its text is byte-identical to
     iteration 3's, so the 13 other tests' assertions still hold.
   - Otherwise the summary is just "work", and each path says whose (`:880-887`):
     - another bundle that alone has a commit: named as before (`issue_A`);
     - a commit several bundles share: "work from issue_A or issue_B — git cannot tell
       which branch made it". This is the carry-forward's own example phrase;
     - a commit only the incoming bundle has: "issue_A's earlier work, which its branch no
       longer has".
4. **`_keep_merge`** calls `_branch_removed` instead of `_removed` (`:735`). The rest of
   the message template (`:736-742`) is unchanged.

Docs: one sentence in `docs/07-crosscutting.md:689-691` ("If two bundles' branches share
the commit that made that work, git cannot tell which of them made it, and the message says
so."). It sits inside the paragraph this patch already adds, so re-wrapping the rest of
that paragraph changes no base line. Docstrings updated: `_keep_merge` (`:722-723`),
`_removed`, `_branch_removed`, `_undone_paths` (`:976-992`), and the test module's
docstring.

## The message for each shape

These come from calling the production `_removed` / `_branch_removed` on hand-made inputs.
The probe is `.cache/probe-673/fmt.py` in the worktree (git-ignored, not shipped), run with
`timeout`. Each entry shows the text inside the path's parentheses. The base merge's text
is unchanged in every row.

| Shape | Bundle-branch refusal (summary, then the path) |
|---|---|
| one other bundle (common) | `issue_A's work` / `a.txt (issue_A)`, **unchanged** |
| two other bundles, two commits | `issue_A, issue_C's work` / `a.txt (issue_A, issue_C)`, **unchanged** |
| nobody known | `folded work` / `a.txt (last changed by abcd on <line>)`, **unchanged** |
| shared with the incoming bundle (pinned test) | `work` / `a.txt (work from issue_A or issue_B — git cannot tell which branch made it)` |
| the incoming bundle's own earlier work | `work` / `a.txt (issue_A's earlier work, which its branch no longer has)` |
| three bundles share | `… (work from issue_A, issue_B or issue_C — git cannot tell which branch made it)` |
| two *other* bundles share | `… (work from issue_A or issue_C — git cannot tell which branch made it)` |
| one sure owner plus a shared commit, one path | `… (issue_C, and work from issue_A or issue_B — git cannot tell which branch made it)` |
| another bundle plus the incoming bundle's own, one path | `… (issue_A, and issue_B's earlier work, which its branch no longer has)` |

The two full new messages, as the tests see them:

- Shared: "merging issue_B's branch origin/fix/B would remove work from
  pdca-integration/main: a.txt (work from issue_A or issue_B — git cannot tell which branch
  made it) would go back to how origin/main had it before the line changed it, and that
  change is not one of issue_B's own commits: its branch brings it in (cut from, or updated
  from, origin/main after a revert there?). Not building the next wave on a line without
  that work — put it back on origin/fix/B (…), then re-run"
- Own earlier work: "merging issue_A's branch origin/fix/A would remove work from
  pdca-integration/main: a.txt (issue_A's earlier work, which its branch no longer has)
  would go back to how origin/main had it before the line changed it, and that change is
  not one of issue_A's own commits: its branch brings it in (…). … put it back on
  origin/fix/A (revert the revert there, …), then re-run"

## For the human at sign-off: two choices I made

1. **The incoming bundle's own earlier work.** I found this case while checking the word
   "never". A's PR merges into main and is reverted there. A's branch is then updated from
   main, so fix/A loses a.txt. The fold refuses A's new tip. Iteration 3 said "merging
   issue_A's branch origin/fix/A would remove issue_A's work … a.txt (issue_A)". The red leg
   of the run against iteration 3 printed exactly that (below). Here the work really is
   A's, put on the line by an earlier fold, so naming someone else, or nobody, would be
   false. The new text still says the merge would remove it, but it says the work is A's
   *earlier* work that A's branch *no longer has*. The next clause already says the change
   is not one of A's own commits, and the fix ("revert the revert there") is the right
   action. If you want a different phrase, it is one line (`integrate.py:883`) plus the
   new test's assertion.
2. **Two other bundles share a commit.** The bundle-branch refusal now says "work from
   issue_A or issue_C — git cannot tell which branch made it" here too, because the ask was
   to say so whenever git cannot tell. The base merge still says "issue_A, issue_C's work",
   kept byte-compatible as asked. No real-git test builds this history. The probe shows the
   text, and the code path is the same one the pinned test drives (any group of 2 or more).

## Alternatives I ruled out

- **Simpler rule: if the incoming bundle is among a path's names and there are 2 or more
  names, say "X or Y — git cannot tell".** This is wrong when two *different* commits
  changed the path, one A's and one B's (say A added a.txt and an earlier fold of B edited
  it). Git can tell there: it is both A's and B's work. That rule would print "git cannot
  tell" anyway. Telling the cases apart needs per-commit data, which is what `groups` is.
  Cost: one list comprehension plus a 4th tuple element in `_undone_paths` (+4 lines of
  code, `:1032-1035`), the 4-element unpack in `_removed` (2 lines), and no git call.
- **A neutral opening for every bundle-branch refusal** (for example "issue_B's branch
  brings in a change that would remove …"). This would avoid "merging X would remove" even
  in the own-earlier-work case. But it rewrites the common message that every other test
  in the file pins and that was already reviewed. Rejected to keep the rebuild narrow, as
  the carry-forward asked.
- **Say "folded work" for the own-earlier-work case.** This drops the bundle whose work it
  is, the opposite of "name the bundle(s) whose work is removed".

## Tests (`template/tests/test_integrate_revert_via_branch.py`, copy in the bundle)

- The pinned test is renamed to
  `test_a_commit_two_branches_share_is_work_from_either_and_git_cannot_tell` (`:275`). It
  asserts the full new clause, from "merging issue_B's branch origin/fix/B would remove work
  from pdca-integration/main: a.txt (work from issue_A or issue_B — git cannot tell which
  branch made it) would go back". It also asserts that "issue_A, issue_B" and "issue_B's
  work" are both absent.
- New: `test_a_branch_that_lost_its_own_earlier_work_is_not_said_to_remove_it` (`:296`).
  The history: A folded, A's PR merged into main and reverted, fix/A updated from main,
  then fold `[a]`. It asserts the "issue_A's earlier work, which its branch no longer has"
  clause, that "issue_A's work" is absent, and that nothing was pushed.
- The module docstring's naming paragraph is updated (`:19-26`).
- The other 13 tests are byte-identical to iteration 3. I checked this with a `git diff`
  between the iteration-3 tree and this one: only the docstring, the pinned test and the
  new test differ.

## Runs (the project's runners, each wrapped in `timeout`)

- **C4 against the base**: `engine/scripts/run-verify.sh` with `PDCA_BUNDLE` = this bundle
  and `PDCA_WORKTREE` set, on the final `patch.diff`.
  - Green leg: `Ran 15 tests … OK`.
  - Red leg (production hunks reverted, test kept): `Ran 15 tests … FAILED (failures=12)`,
    all 12 `AssertionError`.
  - `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`.
  - Afterwards the worktree's `git diff` matched `patch.diff` byte for byte (`cmp`).
- **C4 against iteration 3's code**: the same script, with `PDCA_BUNDLE` pointing at
  `.cache/probe-673/v3-delta/`. Its `patch.diff` is the diff from the iteration-3 tree
  (base + `iteration-v3/patch.diff`, tree `0c67341`) to the final tree (`4cb9002`), so the
  red leg runs iteration 3's production code with this iteration's tests.
  - Green leg: 15 OK.
  - Red leg: `FAILED (failures=2)`, exactly the two message tests. Their assertion output
    shows iteration 3's text: "… would remove issue_A, issue_B's work … a.txt (issue_A,
    issue_B) …" and "merging issue_A's branch origin/fix/A would remove issue_A's work … a.txt
    (issue_A) …".
  - So all detection, keep/refuse and naming behaviour the other 13 tests pin is the same on
    both trees.
- **T3**: `engine/scripts/run-suite.sh` (log: `results/issue_673/.do-suite.log`) on the
  final tree.
  - Root render/update-compat suite: `Ran 24 tests … OK`. The copier render cases ran; none
    was skipped.
  - Offline driver suite: `Ran 2491 tests … OK (skipped=2)`, which is the base's 2476 plus
    these 15.
  - `PDCA-EVIDENCE: root suite OK, driver suite OK`.
  - That covers criterion (4): every `test_integrate_stack_bases` case (the #623 base-merge
    wording included), plus `test_flow_same_wave_conflict` and
    `test_flow_resume_stack_prereqs`.
- **Docs**: `docs/publishing/tools/lint_docs.py` → `lint_docs: OK`. `render_site.py --check
  --out .cache/site-check-673` → 22 pages, `link audit OK` (instance venv).

## Refuting my own test

- **(a) Genuine red? Yes.** With the production hunks reverted to the base, 12 of 15 fail,
  all on assertions; the three "is merged" tests pass both ways by design. Against
  iteration 3's production code, exactly the two message tests fail, and their failure
  output shows the old wording. So they bind this iteration's change, not just "some
  refusal happens".
- **(b) Production path? Yes.** Both message tests call `integrate.fold` on real git: a
  bare origin, the primary checkout and the `human` clone. The text they check is built by
  `_keep_merge` → `_branch_removed` from `_undone_paths`' real `groups`. Nothing is mocked
  in these two tests. The formatter probe calls the production functions directly; it is a
  diagnostic, not a shipped test.
- **(c) Fixture includes the fault? Yes.** In the shared-commit test, B really is cut from
  fix/A, A's PR really merges into main and is reverted, A really gets a later commit, and
  B is really updated from main. In the own-work test, main's revert of A's merged PR
  really reaches fix/A through a real "Update branch" merge (`_update_branch`). Nothing is
  curated out.

## Commit-readiness

The target has no Python formatter or linter configured. There is no pre-commit config, no
ruff/flake8/black/setup.cfg/tox.ini at the root, no `core.hooksPath`, and no active hooks
in the common git dir. CI runs `docs-check.yml` (the two docs checkers above, green) and
`render-check.yml` (the root suite, part of T3, green). `git diff --check` is clean,
including the new file. `python3 -m py_compile` passes on both Python files. No line is
over 100 characters, which is the file's own maximum. Publish adds the DCO sign-off when
it commits.

## Housekeeping

Left in the worktree's git-ignored `.cache/`:

- `probe-673/fmt.py`;
- `probe-673/v3-delta/patch.diff`;
- `probe-673/idx3` and `probe-673/idx4`, the temporary index files used to build the two
  trees (their tree objects are unreferenced in the object store);
- `c4-673.log` and `c4-vs-v3.log`;
- `site-check-673/`.

The new test file also has an intent-to-add index entry (`git add -N`, so `git diff` shows
it). In the bundle, `.do-suite.log` is this iteration's T3 output, and the stale
`.prod-only.diff` from iteration 1 is still there. None of these is an artifact. Cleanup
is the harness's.
