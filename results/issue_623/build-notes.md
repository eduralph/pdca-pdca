# Build notes — issue 623 / fold-refuses-base-that-reverts-line-work (iteration 2)

Target: eduralph/pdca-harness @ main (`b5f5c29`), worktree `pdca-harness.pdca-wt-l0`.
Line numbers are on the patched tree unless marked "base".

This iteration starts from the iteration-1 patch (`iteration-v1/patch.diff`, which applied
cleanly to `b5f5c29`) and fixes the two implementation findings in the carry-forward. The
detection rule, the pre-raise reset, the `_LineBroken` guard, the stderr fix and the docs
sentence are kept; the owner attribution is rewritten.

## The two carry-forward findings, and what changed for each

### 1. C5 — a change merged INTO a bundle's branch was not attributed to it

Cause (iteration 1): a bundle's work was taken to be its first-parent chain since the cut
point (`rev-list --first-parent <head> --not <cut>`). A topic branch merged into `fix/Z`
puts its commit on the second-parent side, so the path-limited history of `topic.txt`
found the topic commit, which was not on Z's chain, and Z went unnamed.

Fix: `_own_commits` (`integrate.py:651-669`). A bundle's own commits are every commit
reachable from its head (the published branch tip, or the head its PR merged with when the
branch is gone) **without passing through a commit of `skip`**, where `skip` is the
line's first-parent chain since the cut point plus the base's first-parent chain since the
cut point (`integrate.py:689-690`). The walk is a plain BFS over
`git rev-list --parents <head> --not <cut>`. So:

- a topic merged into the PR branch is the bundle's (the reviewer's case);
- what a bundle got by being cut from the line or the base, or by "Update branch", is not
  (the walk stops at the line/base commit it was cut from or merged in);
- a bundle whose work reached the line through an earlier base take-in (case 9's history)
  is still named, because its commits sit on the base's second-parent side, not in `skip`.

The owner check is then the same as before: an owner is named for a path when one of its
own commits is among the commits that changed the path on the line
(`rev-list <before> --not <cut> -- :(literal)<path>`, `integrate.py:702`).

### 2. Batch owners came from `cfg.bundle` and were deduped by path

Fix: `fold` builds the owners with `cfg.find_bundle(id)` (the active bundle, else the
archived `results/completed/issue_<id>`), the way `merged.merged_head` (`merged.py:123`)
and the flow (`flow.py:729`) find a bundle, and dedupes by `Path.name`, keeping the fold's
own bundle path first (`integrate.py:441-448`). 4 lines.

### Evidence that the new tests bind these findings

I put the iteration-1 `integrate.py` back into the worktree (my tests and docs kept) and
ran the C4 script. Its green leg failed exactly the three new tests, each with the
reported symptom:

- `test_a_reverted_topic_merged_into_a_bundles_branch_names_that_bundle`: message said
  `would remove folded work … topic.txt (last changed by a491bdd3ae43 on …)` — Z missing.
- `test_an_archived_batch_bundle_is_still_named`: `z.txt (last changed by 304e8712b1ea …)`
  — the archived Z missing.
- `test_a_bundle_reached_twice_is_named_once`: `a.txt (issue_A, issue_A)`.

All other tests passed on the iteration-1 code. Then I restored this patch's
`integrate.py` and checked `git diff` is byte-identical to `patch.diff`.

## All changes

- `template/src/pdca_harness/integrate.py`
  - `:45-46` module docstring; `:324-326` `fold` docstring; `:521-522` `_gone_branch`
    docstring; `:574-579` `_take_in_base` docstring.
  - `:71-73` `_LineBroken` and `:454` its re-raise under `skipped` (kept from iteration 1):
    a line that cannot be reset after a refusal still has the revert, so the carry must not
    record a skip and then merge and push onto it.
  - `:441-448` owners for the message (finding 2), passed through `_merge_published`
    (`:478-479`, `:488`) and `_gone_branch` (`:506-507`, `:555`) to `_take_in_base`.
  - `:567-614` `_take_in_base`: reads the line tip before the base merge (`:581`), runs
    the check after a clean merge (`:595`), resets to that tip before raising (`:597`,
    `:600`), and prints "reaches … through" (`:612-614`) only when nothing was undone, so
    the line is true whenever it is printed. The reset sits here, not in `_merge`
    (base `:583-595`), which 631 changes in the same wave.
  - `:628-641` `_cut_point` now returns `(cut, chain)`; the chain is reused as part of
    `skip`. The cut's parent is read with `rev-list --parents -n 1`, so a root commit
    (cut None, compare against the empty tree) is no longer the same answer as a failed
    git read (iteration 1 used `_rev(chain[-1]^1)`, None for both). A failed read now
    raises, and the line is reset. The docstring now states both the `(tip, [])` and the
    None case (the advisory review's docstring note).
  - `:644-648` `_changed`, `:617-625` `_out` (kept).
  - `:651-669` `_own_commits` (new, finding 1).
  - `:672-706` `_undone_paths`: detection rule unchanged (paths that differ between the cut
    point and the line before the merge, and no longer differ after it); attribution now
    uses `_own_commits`. The path is passed as `:(literal)<path>` so a file name with `*`,
    `?` or `[` is not read as a glob.
  - `:709-714` `_reset_line` (kept).
- `docs/07-crosscutting.md:671-675` — one sentence after "the run stops rather than build
  the next wave without that work": it also stops, naming the bundle, when merging the base
  in would undo work a bundle put on the line; a base that only edits such a file is merged
  in as usual. Only lines between 633's sentence (base `:665-666`) and 629's (base
  `:672-673`) change; 629's lines shift down by 4.
- `template/tests/test_integrate_stack_bases.py` — see Tests.

## Attribution: how it relates to the brief's wording (flag for the human)

The brief says: name a bundle "whose commits in `C..<its head>` touched the path". Read
literally (`rev-list <head> --not C`), this over-names. In criterion (1), B is cut from the
reverted `main`: `B1 → main2 (revert) → main1 (merge of fix/A) → F → A1`, so A's commit
`A1` and the revert are both in `C..B1`, and the message would read
`a.txt (issue_A, issue_B)` although B brought nothing to the line. That literal version
would be a 1-line change from iteration 1 (drop `--first-parent`), and it is wrong in the
brief's own criterion (1). `_own_commits` keeps the brief's intent ("the bundle that
brought it") and stays within its wording: a named bundle's own commits are a subset of
`C..<its head>`, and one of them touched the path. Criterion (1) now asserts
`a.txt (issue_A) would go back` exactly, so B being named would fail it.

Known edges of this rule (none affects whether the fold stops, only who is named):

- A PR merged by fast-forward (a manual push, not GitHub's merge button) puts the bundle's
  commits on the base's first-parent chain, so they are in `skip`: that bundle is not
  named, and the message falls back to the path and the commit that last changed it.
- A legacy `Stacks on` child whose branch was built on its parent's branch has the
  parent's commits as its own, so it is named with the parent. The literal brief rule does
  the same.

## Tests (appended to `StackFoldGit`, `template/tests/test_integrate_stack_bases.py`)

- Helpers: `:455` `_revert_on_main`; `:464` `_fixup_merged_then_reverted` (the brief's
  repro; now takes an optional `batch`, `None` keeps the unscoped `LINE`); `:478`
  `_z_reverted_then_a_gone` (criterion (2)'s history, with `topic=True` for the
  reviewer's topology: Z's PR branch merges a topic commit adding `topic.txt`, and `main`
  reverts only that commit).
- `:506` criterion (1) — now also asserts `a.txt (issue_A) would go back` (no B).
- `:525` criterion (2) — batch `["Z","A","B"]`, line from `integration_branch`.
- `:540` new — topic merged into Z's branch → `topic.txt (issue_Z) would go back`.
- `:555` new — Z archived to `results/completed/` after its fold → still named.
- `:568` new — A passed as an archived copy and found again by id at its active path →
  named once. This needs both copies to exist, which is contrived, but it is the exact
  second effect the review described.
- `:581` criterion (4) — `skipped={}`.
- `:600` new — the reset is made to fail (`integrate._git` patched for `reset` only, as
  the file's other failure tests patch it): the carry raises instead of recording a skip,
  and pushes nothing. The advisory review noted this guard had no test.
- `:620` criterion (5).
- Criterion (3): `test_a_merged_branch_the_line_never_carried_comes_in_through_the_base`
  (`:430`) and every other case in the file pass unchanged.
- Module docstring `:23-25`: one added paragraph.

### Criterion (4): B is published from the line, not from `main` (kept from iteration 1)

The brief's (1) repro publishes B from `origin/main`. In carry mode that B was cut from the
reverted `main`, so B's own branch carries the revert, and merging B (after A is skipped
and the line is reset) brings the revert in through B, not through the base. That is "a
revert on a bundle's own PR branch", out of this brief's scope (#633's territory). In the
flow a later-wave bundle (B depends on A) is cut from the line, so the test publishes B with
`cut_from=f"origin/{LINE}"` (`:588`), with a comment saying why. Criteria (1) and (2) keep
the brief's default publish; the fold stops at A before B is merged, so it does not matter
there. Worth a human look: a bundle cut from a base that has a revert still drops the
reverted work when it is merged. This patch does not cover that path (`_merge_published`
merging a live branch never takes the base in).

## Runs (project runner: the configured gate scripts)

- C4: `PDCA_BUNDLE=results/issue_623 PDCA_WORKTREE=… ./engine/scripts/run-verify.sh` →
  `PDCA-EVIDENCE: C4 PASS`. Green leg: `Ran 54 tests … OK`. Red leg (production hunks
  reverted, tests kept): `FAILED (failures=7)` — criteria (1), (2), (4) and the four new
  tests (topic, archived, reached-twice, reset-fails). Criterion (5) and all older cases
  are green on both legs. The tree was restored by the script and checked equal to
  `patch.diff`.
- T2: `./engine/scripts/run-docs-check.sh` → `lint_docs: OK`, `render_site: wrote 22
  page(s)`, `link audit OK`.
- T3: `./engine/scripts/run-suite.sh` → root suite `Ran 24 tests … OK`, driver suite
  `Ran 2377 tests … OK (skipped=2)`, `PDCA-EVIDENCE: root suite OK, driver suite OK`.
- Commit hooks: the target has no `.pre-commit-config.yaml`, no ruff/flake8/black config,
  no `core.hooksPath` and no installed hooks; CI runs the copier render check and the docs
  checks (both covered by T3/T2). No added line is over 100 columns (the file's existing
  maximum is 100); `git diff --check` is clean.

## Self-refutation

- **(a) Genuine red?** Yes. The C4 script reverted the production hunks of `patch.diff`
  and re-ran the module: 7 tests failed on their assertions (`IntegrationError not raised`
  for (1), (2), topic, archived, reached-twice and reset-fails; `[] != ['issue_A']` for
  (4)). None failed on import: the tests use only `integrate.fold`,
  `integrate.integration_branch` and `integrate.IntegrationError`, which exist before the
  fix. Separately, the three attribution tests fail on the iteration-1 code (above).
  Two mutations, each run through the same C4 script (green leg) and then restored:
  dropping the reset before the raise (`integrate.py:600`) fails criterion (4) (B merged
  and pushed onto the reverted line) and the reset-fails test; dropping the `_LineBroken`
  re-raise (`integrate.py:454`) fails only the reset-fails test. So each guard has a test
  that goes red without it.
- **(b) Production path?** Yes. Every test calls the real `integrate.fold` against real
  git: a bare origin, real `--no-ff` merges, a real topic merge into `fix/Z`, real
  `git revert -m 1` / `git revert`, real branch deletion, a real bundle dir moved to
  `results/completed/`. The only patches are the host answer (`merged.merged_head` via
  the existing `_merged_heads` helper, i.e. the GitHub API) and, in the reset-fails test,
  `integrate._git` returning 1 for `reset` only.
- **(c) Fixture includes the fault?** Yes. The revert commit is pushed to origin's `main`
  and the fold fetches and merges that `main`. (4) asserts the revert is not an ancestor of
  the pushed tip; (1), (2), topic and reset-fails assert origin's line is still at `t1`.
  The topic test's `fix/Z` really has the topic merge, and the archived test's Z really
  lives only under `results/completed/`.

## Ruled out

- **Step-based attribution** (for each line commit that changed the path, name the
  bundle whose first-parent chain holds that merge's second parent). About the same size
  (~20 lines), and it also fixes the topic case, but it does not name a bundle whose work
  reached the line through an earlier base take-in (case 9's history, then reverted): the
  step that brought the path is the base merge, whose second parent is a base commit.
  `_own_commits` names that bundle, because its commit is on the base's second-parent
  side.
- **The literal `C..<head>` rule**: over-names B in criterion (1) (see above).
- **Detecting reverts by commit message**: forbidden by the brief and easy to dodge.
- **Putting the reset in `_merge`**: conflicts with 631 in the same wave (brief).

## Limits of the brief's detection rule (not changed here; for the human)

The rule is path-level and starts at the cut point, as the brief specifies. It does not
see: a revert of only some hunks of a file another bundle also changed (the path keeps new
content); a revert of work below the cut point (after a wave PR carrying line commits was
merged into the base, the cut point moves up); a base that reverts only a fixup the line
never carried (the path is not back to the cut-point content). The brief already lists a
known false stop (a base reverting its own change that an earlier take-in brought in);
that case is named by path and commit, as the brief says.
