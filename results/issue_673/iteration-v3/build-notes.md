# Build notes — issue 673 / fold-stops-on-a-revert-brought-by-a-bundle-branch (iteration 3)

Base: the worktree at `ebef78c` (`pdca-integrate: issue_693`, on top of `2be8a16` issue_672
and `d6057eb`), the same base as iteration 2. Every `path:line` below is on the patched tree
in `$PDCA_WORKTREE` unless it says "base". The brief's `d6057eb` numbers moved (672 added the
`skipped` re-pass): the bundle merge's `rc == 0` return is base `integrate.py:681`,
`_take_in_base` base `:755`, `_undone_paths` base `:860`, `_reset_line` base `:897`.

I started from the iteration-2 patch (it applied cleanly to the same base) and changed only
what the carry-forward asked about, plus one docs correction I found on the way (below).

## What the carry-forward asked

Iteration 2 made each bundle's walk in `_undone_paths` stop at another bundle's CURRENT tip.
The review: if B was cut from `fix/A` and A later got another commit, A's tip is not in
B's history, so B's walk goes on into A's commit and B is named as an owner of `a.txt`. The
refusal for B's merge then says it would remove "issue_A, issue_B's work". Suggested fix:
"stop the walk at any commit reachable from another owner's tip", or accept and pin it.

### The suggested fix, taken literally, drops the bundle whose work it is

"Reachable from another owner's tip" works in both directions. In the reviewer's history,
A's commit A1 is reachable from B's tip (B was cut from it), so A's walk stops at A1 too and
A loses it. Then nobody is named and the message falls back to "folded work". It is worse
in the plain cases: in criterion (1), B (cut from the reverted main) holds A1 through main's
merge of A, so A is never named at all. Probe (below), rule swapped in at runtime: **10 of
the 14 tests fail**, criterion (1) included, all with "would remove folded work …
a.txt (last changed by <sha> on <line>)".

### Why no rule based on commits alone can be exact here

Take the reviewer's history H: A's commit A1 (adds `a.txt`) is folded; B is cut from
`fix/A` at A1 and adds B1; A's PR merges into main at A1 and main reverts it; A then gets
A2; B is updated from main. Now H*: B's commit B0 (adds `a.txt`) is folded; A is cut from
`fix/B` at B0 and adds A1; B's PR merges into main at B0 and main reverts it; B then gets
B1; B is updated from main. In both, A's tip is one commit on top of the shared commit, and
B's tip is an "Update branch" merge on top of one commit on top of it, with main's merge of
the shared commit and its revert behind it. The two commit graphs are the same, tip for tip.
But the shared commit is A's work in H and B's in H*. Only main's merge message (whose PR it
was) and the order the fold gets the bundles in tell them apart. So a rule that reads only
the commit graph names A in both, B in both, or both in both, and only "both" is never
missing the right one.

### The rule I chose (`integrate.py:992-999`)

1. Each bundle's walk is #623's walk, unchanged (`_own_commits`, `:899`): it stops at the
   line's and the base's first-parent chains.
2. **A bundle's own commits leave out the own commits of every other bundle whose tip its
   branch holds**, whichever route it holds it by (`_in_line(..., of=tip)`, a
   `git merge-base --is-ancestor`). This covers iteration 2's case (the walk reaches the
   other tip) and also the case where the branch holds the other tip by another route, such
   as through main after that bundle's PR merged with its later commits.
3. A commit two branches share while neither holds the other's tip counts for both: the
   message names both rather than guess. That never leaves out the bundle whose work it is.
   This matches #672, which also counts a shared commit as the work of both
   (`integrate.py:388`).

This fixes the most likely form of the reviewer's history. For B to bring a revert of A's
work, B must hold main's revert, so B holds main's merge of A's PR, and with it the tip A's
PR merged with. A fixup pushed before A's PR merged is part of that tip, so B holds A's tip,
and only A is named (new test, `test_integrate_revert_via_branch.py:255`). Only a commit
pushed onto `fix/A` *after* its PR merged leaves a true fork. That case is pinned: both are
named (`:272`), as the review allowed ("or accept this and add a test that pins the current
behavior").

What gets subtracted is the other bundle's own commits (its walk), not everything its tip
can reach. The walk stops at the line's first-parent chain, so a branch cut from the line
never takes away the commits the line's merges brought.

The change reaches the #623 base-merge message too, because `_undone_paths` is shared (the
review said so). That message's wording is unchanged; only which bundles it names changes,
and only when one bundle's branch holds another's tip. One test pins that
(`test_integrate_revert_via_branch.py:290`): before the fix that test reads
"issue_A, issue_B's work".

Cost: `own` is built from the walks that already existed, plus one `merge-base
--is-ancestor` for each ordered pair of bundles whose walks share a commit (the `isdisjoint`
check at `:997` skips every other pair, so branches that share no commit cost no extra git
call). This only runs when a merge would remove work, so only on the way to a refusal.

### Rules I rejected, with the evidence

Probe: `.cache/probe-673/probe.py` in the worktree (git-ignored, not in the patch). It swaps a
different rule in at runtime (`_undone_paths` for the naming rows, `_own_removals` for the
first-parent row) and runs the new test module under the same `PYTHONPATH=src` the runner
uses, wrapped in `timeout`.

| Rule | Result on the 14 tests |
|---|---|
| Chosen (above) | 14 pass |
| Iteration 2: stop only at another bundle's tip when the walk reaches it | 2 fail: `…holds_another_bundles_moved_tip_names_only_that_bundle`, `…base_merge_refusal_names_only_the_bundle_whose_tip_a_branch_holds` (both read "issue_A, issue_B") |
| Literal review suggestion: leave out everything reachable from any other bundle's tip | 10 fail, criterion (1) included ("folded work") |
| (exemption, not naming) first-parent instead of `rev-list -n 1` | 5 fail, 4 of them with no stop at all |

Two more I did not build, with the reason:

- **Fold order as the tie-break** (in a fork, the earlier bundle wins). Exact when the fold
  gets stack order (the in-run folds do: `accepted` is wave then name order). Not otherwise:
  the pre-wave carry folds "in the order asked for" (`flow.py:1079`), and bundles found only
  through `batch` come after the fold's own (`integrate.py:536-539`). With the order wrong
  it names only the wrong bundle and drops the right one, which is worse than naming both.
- **The fold's own merge messages** (`pdca-integrate: issue_X`, `integrate.py:697`): exact
  for commits the line's own merges brought. But it decides by commit message, which this
  module avoids on purpose (`integrate.py:353`, `:748`), and commits that came in through a
  base merge would need a second rule. Too big a change for a message-only finding.

## A docs correction (gap 1)

Iteration 2's docs said the checks miss "a revert of work that was already on your base
when the line started". That is not accurate. The cut point is where the line's
first-parent chain meets the base as it is NOW (`_cut_point`, `integrate.py:876`). When a
later wave's PR merges into the base, it brings the line commits under it, and the cut point
moves up. I hit this while writing a test: B (cut from the line) merged into main first, main
reverted it, and A was updated from main. The refusal named only `b.txt`. `a.txt` had become
base work, which is gap 1, the accepted limit. Reworded in `docs/07-crosscutting.md:691-695`
and the module docstring (`integrate.py:53-57`) so the user can see when it applies. I
dropped that test: it showed gap 1, not naming.

## The rest of the design (unchanged from iteration 2, re-checked)

- Hook: `_merge_published` reads the line tip before the merge (`integrate.py:693`), as the
  peer `_take_in_base` does (`:820`), and calls `_keep_merge` on the `rc == 0` return
  (`:699`).
- `_keep_merge` (`:713-742`): `_undone_paths(..., head=head)`; a hit resets the line
  (`_reset_line`, `:734`) and raises a plain `IntegrationError` with its own wording
  ("merging issue_B's branch origin/fix/B would remove issue_A's work …"). So the in-run fold
  stops, and under `skipped` only that bundle is left out (`fold`, `:578-583`). A line that
  will not go back raises `_LineBroken`, which stops even the carry.
- The own-change exemption (criterion 2b asks which rule): `_own_removals` (`:920-945`). A
  removal is the branch's own when the commit that gave the branch tip its content at that
  path (`git rev-list -n 1 <head> -- <path>`, `:941`, which follows the parent a merge took
  the path from) is one of the commits the merge brings and is not on the base's or line's
  first-parent chain. This is "an equivalent rule", not the first-parent rule: under
  first-parent, an "Update branch" merge whose merge base is A's commit looks like B's own
  deletion of `a.txt`. Re-measured with the probe (`fp`): 5 of the 14 tests fail, 4 of them
  because the fold does not stop at all (`IntegrationError not raised`, so the line would be
  pushed without `a.txt`): `…cut_from_the_line_then_updated…`,
  `…cut_from_another_bundles_branch_then_updated…`, `…edited_the_file_and_put_it_back…`
  and the fork test.
- `_removed` (`:853-862`) is the base-merge message's own code moved out of `_take_in_base`
  without change, so the base-merge wording stays byte-compatible (criterion 4).
- `_reset_line` takes what it undoes (`:1009-1016`), so a failed reset after a bundle refusal
  no longer blames the base merge (iteration 1's finding).

The other two advisory points from iteration 2's code review were not tagged, and I left
them as they are:

- A git read that fails inside the check raises a plain `IntegrationError`, so under the
  carry's `skipped` that bundle is skipped, with the git error as its reason. The flow names
  it, so this is not silent. `_take_in_base` behaves the same way. `IntegrationTreeError`
  means "the worktree could not be put back" (`integrate.py:85-91`). That is not the case
  here, since the line is reset first, so raising it would misuse the class.
- Efficiency (a `_cut_point` and two diffs per clean bundle merge): the reviewer marked it
  optional. That is 4 git calls per newly merged bundle, and already-carried bundles return
  early (`:691-692`).

## Tests

`template/tests/test_integrate_revert_via_branch.py` (copy in the bundle dir). It loads
`test_integrate_stack_bases.py` by path and uses `StackFoldGit` as a helper object (setUp
and tearDown by hand, `addCleanup`), never subclassed. It imports only `pdca_harness.integrate`
(plus `unittest.mock` for the one fault-injection test).

| Test (line) | Covers | Pre-fix | Post-fix |
|---|---|---|---|
| `…cut_from_a_base_that_reverted_line_work_stops_the_fold` (`:162`) | (1) | FAIL: not raised | pass |
| `…carry_skips_only_the_branch_that_brings_the_revert` (`:173`) | (2) with D | FAIL: `[] != ['issue_B']` | pass |
| `…updated_from_a_base_that_reverted_line_work_stops_the_fold` (`:184`) | (2b) | FAIL | pass |
| `…cut_from_the_line_then_updated_from_the_reverted_base_stops` (`:195`) | (2b) first-parent trap; stop + carry | FAIL | pass |
| `…cut_from_another_bundles_branch_then_updated_stops` (`:209`) | B cut from fix/A; stop + carry | FAIL | pass |
| `…edited_the_file_and_put_it_back_still_brings_the_revert` (`:220`) | own edits that cancel out; stop + carry | FAIL | pass |
| `…revert_merged_through_a_revert_pr_is_the_bases_not_the_branchs` (`:234`) | GitHub "Revert" button; stop + carry | FAIL | pass |
| **new** `…holds_another_bundles_moved_tip_names_only_that_bundle` (`:255`) | this iteration's finding: A moved on, B holds A's tip through main → only A named | FAIL | pass (fails under iteration 2's rule) |
| **new** `…two_branches_share_while_neither_holds_the_others_tip_names_both` (`:272`) | the true fork, pinned: both named | FAIL | pass |
| **new** `…base_merge_refusal_names_only_the_bundle_whose_tip_a_branch_holds` (`:290`) | the same naming in the #623 base-merge message | FAIL: "issue_A, issue_B's work" | pass (fails under iteration 2's rule) |
| `…dependent_that_deletes_the_file_itself_is_merged` (`:311`) | (3) delete | pass | pass |
| `…dependent_that_edits_the_file_is_merged` (`:320`) | (3) edit | pass | pass |
| `…dependent_deleting_the_file_then_updated_from_the_reverted_base_is_merged` (`:327`) | own deletion survives "Update branch" | pass | pass |
| `…line_that_will_not_go_back_after_refusing_a_branch_stops_even_the_carry` (`:343`) | `_LineBroken` for the new refusal; reset message names the merge | FAIL: not raised | pass |

The three "is merged" tests guard against false stops, so they pass before and after by
design.

## Runs (the project's runners)

- **C4**: `engine/scripts/run-verify.sh` with `PDCA_BUNDLE`/`PDCA_WORKTREE` set, wrapped in
  `timeout 600`, on the final `patch.diff`. Green leg `Ran 14 tests … OK`. Red leg (production
  hunks reverted, test kept) `Ran 14 tests … FAILED (failures=11)`, every failure an
  assertion. `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`. Afterwards the
  worktree's `git diff` matched `patch.diff` byte for byte (`cmp`).
- **T3**: `engine/scripts/run-suite.sh` with `PDCA_WORKTREE` set, wrapped in `timeout 3000`
  (log: `results/issue_673/.do-suite.log`). Root render/update-compat suite `Ran 24 tests …
  OK` (the copier render case ran, not skipped); offline driver suite `Ran 2490 tests … OK
  (skipped=2)`; `PDCA-EVIDENCE: root suite OK, driver suite OK`. 2490 = the base's 2476 + the
  14 new tests. That covers criterion (4): every `test_integrate_stack_bases`,
  `test_flow_same_wave_conflict` and `test_flow_resume_stack_prereqs` case is green, the #623
  base-merge wording assertions included.
- **Docs**: `docs/publishing/tools/lint_docs.py` → `lint_docs: OK`; `render_site.py --check
  --out .cache/site-check-673` → `22 page(s)`, `link audit OK` (instance venv, `timeout`).

## Refuting my own test

- **(a) Genuine red? Yes.** `run-verify.sh` reverted only the production hunks and ran the
  module: 11 of 14 fail, all on assertions (`IntegrationError not raised`, `[] !=
  ['issue_B']`, and the base-merge naming test on "issue_A, issue_B's work"). The probe also
  shows the two new naming tests fail under iteration 2's rule, so they pin this iteration's
  change, not just "some check exists".
- **(b) Production path? Yes.** Every test calls `integrate.fold` against real git: a bare
  origin, the primary checkout and a `human` clone. Nothing in `integrate` is replaced, except
  in the one fault-injection test, which wraps `integrate._git` so that only the reset back to
  the line's tip fails. The base-merge test patches only the host lookup
  `merged.merged_head`, through the fixture's own `_merged_heads`, as the #623 tests do. The
  path run is `fold` → `_merge_published` → `_keep_merge` (or `_take_in_base`) →
  `_undone_paths` → `_own_removals` / `_own_commits` / `_in_line`.
- **(c) Fixture includes the fault? Yes.** The revert really happens on origin's `main`, B's
  branch really is cut from or updated from that `main` (`_update_branch`), and the moved tip
  is a real commit pushed onto `fix/A` (before A's PR merges in one test, after it in the
  other). Nothing is curated out.

## Commit-readiness

The target has no Python formatter or linter configured: no pre-commit config, no
ruff/flake8/black config at the root (`template/pyproject.toml.jinja` is for generated
instances), no `core.hooksPath`, and no hooks in the common git dir. CI runs `docs-check.yml`
(the two docs checkers above) and `render-check.yml` (the root suite, part of T3). I ran
`git diff --check` (clean, the new file included) and `python3 -m py_compile` on both Python
files (OK). Line widths follow the file (it has lines up to 100 characters; the longest new
one is 96). DCO sign-off is added by publish when it commits.

## Housekeeping

Files I left (cleanup is the harness's): in the worktree, `.cache/probe-673/probe.py` and
`.cache/site-check-673/` (both git-ignored), and an intent-to-add index entry for the new
test file (`git add -N`, so `git diff` shows it). In the bundle, `.do-suite.log` (the T3
output). The iteration-1 stray `.prod-only.diff` is still there too. None of them is an
artifact.
