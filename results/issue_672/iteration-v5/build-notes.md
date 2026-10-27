# Build notes — issue 672 / carry-keeps-a-fold-time-skip-off-the-line (v5 brief)

Target: `eduralph/pdca-harness` `main` @ `d6057eb`, worktree `pdca-harness.pdca-wt-l1`.
Every `path:line` below is on that worktree with the patch applied (base lines marked
"base"). Files: `template/src/pdca_harness/integrate.py`, `template/src/pdca_harness/flow.py`,
`docs/07-crosscutting.md`, `template/tests/test_flow_resume_stack_prereqs.py`.

## What changed

**The fold enforces the invariant itself, before its one push** (`integrate.py`).

- `fold` takes two new keyword arguments, `pr_heads` and `holds` (`integrate.py:308-309`).
  `pr_heads` is the PR head the carry read from `gh` for each finished id; `holds` is
  filled in place with `name → the id whose work it holds`.
- The merge loop now runs in passes (`integrate.py:529-598`). Pass 1 is the old loop,
  unchanged in effect: same merge, same `#674` held-out path, same skip recording. Each
  branch tip is read once and cached in `read` (`:543-548`), so a later pass merges the
  same commit (the `#633` "read once" rule holds across passes).
- If the pass skipped anything (only possible with `skipped=`, `:578`), the fold:
  1. computes each skipped id's work with `_work` (`:584-586`, helper at `:998-1008`):
     `git rev-list <fold's branch-tip read> <pr_heads entry> --not <base_remote>/<base>
     <start_ref>`. That is the brief's Definition exactly: both heads, measured against the
     base and the commit the line started from (`start_ref`, `:513`, base `:498-499`),
     merge commits included, nothing exempt.
  2. leaves out every merged bundle whose merged head reaches any of that work
     (`_hold_work`, `:1017-1048`): recorded in `skipped` (so the existing "all skipped →
     push nothing" check at `:599-600` and the carry's `carried` list keep working) and in
     `holds` with the cause. A held bundle's own work joins the left-out set and the check
     repeats to a fixed point (see "transitive holds" below).
  3. if any merged bundle was left out, resets the tree and restarts the line from the
     same `start_ref` (`:592-594`) and merges only the bundles still in (`dropped` skips
     the rest, `:541-542`). A bundle that fails on the rebuilt line is skipped the same
     way and the loop repeats. Each extra pass drops at least one more bundle, so it ends.
- After the passes, `_built_on_skipped` (`:595-598`, helper `:1051-1069`) relabels a
  skipped bundle whose branch contains another skipped bundle's tip: it is reported for
  that one's work, not its own failure (criterion 5).
- The push is unchanged and happens once (`:601-615`).
- The `skipped` paragraph of `fold`'s docstring is rewritten (`integrate.py:372-392`).

**The carry reports the holds** (`flow.py`).

- `_fold_lines` passes `pr_heads` / `holds` through (`flow.py:919-920`, `:947-948`, doc
  `:935-938`).
- `_carry_finished` passes its existing `heads` dict as `pr_heads` and reads `holds` back
  (`flow.py:1116-1130`): each held id gets the existing `built_on` hint with the skipped
  id as `cause` (`causes.update(holds)`), so the line reads "issue_Q was built on issue_P,
  which is not carried (see its line)…" and its plain `Depends on` dependents wait through
  the existing `held` set. If the fold raises, `holds` is cleared so a half-filled map
  never mixes with the exception's message (`:1124`).
- Docstring `flow.py:1058-1069` replaces the residual sentence (base `flow.py:1052-1054`).

**Docs** (`docs/07-crosscutting.md:729-737`) replace the residual sentence (base
`:728-730`); the new text says the carry *adds none* of the failed one's commits, not that
the line is free of them. One sentence added to the known-limits paragraph
(`:748-755`) names over-holds (i), (ii), (iii) and the gap (v).

**Tests** (`template/tests/test_flow_resume_stack_prereqs.py:481-622`): criteria (1)
`:520`, (2) `:537`, (3) `:553`, (4) `:567`, (5) `:592`, (7) `:606`, with helpers
`_update_ours` `:483`, `_drop_edge` `:492`, `_carried_beside` `:500`, `_off_the_line`
`:515`. Fixture addition: `self.gh_heads` (`:57`, used in `_gh_stub` `:105-106`).

## Why in the fold and not in the carry

The brief left this to Do. The carry cannot know which ids the fold will skip until the
fold has tried the merges, and the fold pushes at the end of the same call
(`integrate.py:601-615`). So the decision has to sit between the last merge and the push,
which is inside `fold`. The two carry-side options both cost more:

- **Carry calls the fold twice** (a no-push pass to learn the skips, then a pushing pass):
  needs a `push=False` mode in `fold` (~8 lines), a way to return the heads it read
  (~6 lines), a second `_fold_lines` call and the work computation in `flow.py`
  (~45 lines). Every carry fold would merge everything twice, even when nothing is
  skipped, and the two calls take the integration lock separately (`_fold_lines` opens its
  own `ExitStack`, `flow.py:944`), so origin's line could move between them and the second
  fold would refuse it (`integrate.py:502-511`).
- **Carry re-implements the merges as trial merges** in its own clone: a copy of the
  conflict, gone-branch and base-take-in paths (`_merge_published` `integrate.py:662`,
  `_gone_branch` `:692`, `_take_in_base` `:753`), which is the parallel implementation the
  C5 gate exists to catch.

Inside the fold, the common cases cost nothing extra: no skip → one pass, as before; a
skip with no merged holder → one pass plus a few `rev-list` calls; only a merged holder
triggers the second pass. Rejected in-fold alternatives:

- **Always run a trial pass first** (detached HEAD, like `_trial`, `integrate.py:965-995`):
  doubles every carry fold's merges for the rare case. Same code size as the rebuild.
- **Check eagerly at each failure**: still needs the rebuild for a holder merged *before*
  the skip (criterion 3), so it saves no code.

## Choices the brief left open

1. **Held ids are recorded in `skipped`, and their work counts too (transitive holds).**
   The brief defines "skipped" as any id the fold records in `skipped=`. Recording held
   ids there keeps every existing caller and check unchanged, and then the literal
   definition says their work must stay off the line too. `_hold_work` therefore adds a
   held id's work (from its merged head and PR head) to the left-out set and repeats until
   nothing new is held. Cost: one `while grew` loop, about 5 lines over a one-shot check.
   It only adds holds (conservative). Probe S3 below shows it: Z, cut from Q's own first
   commit (not P's), is held with cause Q when Q is held for P.
2. **Which reason a skipped holder gets (criterion 5).** Two skipped ids that share a
   commit both "reach" each other's work, so the literal rule would make each name the
   other ("see its line" pointing in a circle, with neither line showing the actual
   conflict). I pick the asymmetric fact: a skipped id is relabeled only when the other's
   tip is a proper ancestor of its own tip (it was built on it). One tip per id makes
   this a strict order, so no two ids can name each other. Criterion 5's Q (built on P)
   names P; P keeps its own conflict reason, in either fold order (probe S1). Cost of the
   choice: a skipped id that shares only *part* of another skipped id's history (neither
   tip contains the other) keeps its own failure reason. Both are out either way; only
   the wording differs. A fold-order tie-break was rejected because in the reverse order
   it labels P "built on Q", which is false.
3. **Cause for a merged holder:** the first left-out id in fold order whose work it
   reaches; always one left out earlier, so no cycles.

## For the human at sign-off

- **The over-hold the brief asks you to accept explicitly** (plan-review note 5): any
  finished id whose branch shares a commit with a skipped id is held. That includes a
  *prerequisite* whose finished dependent fails: if Q is cut from P and Q's own merge
  fails, P is held too, because P's commit is on Q's branch and counts as Q's work (the
  brief: "not a `Depends on` prerequisite's history" is exempt). P's drive-set dependents
  then wait as well. Before this patch P was carried in that case.
- **Wording quirk in that same case:** P's line uses the mandated `built_on` hint, which
  reads "issue_P was built on issue_Q" — the roles are reversed there. The reason text
  before it is accurate ("issue_P's branch … holds <commit>, which is also issue_Q's
  work…"). #694 edits these hold messages and may want to cover it.
- **Known limit (v), confirmed by probe S2:** on a line continued from an earlier run, a
  skipped P's commits already on that line stay there; this carry adds none of P's new
  ones. Documented in the doc and the docstring.
- A rebuild re-runs `_merge_published` for the kept bundles, so a gone-branch bundle's
  `gh` lookup and its `integrate:` stderr line can repeat once in that (rare) case.

## Test fixture note (criterion 7)

The brief suggested `self.gh["P"] = <tip>` if the stub reads the branch. That would not
work: `self.gh` holds the PR *state* (`_gh_stub`, base test file `:100`), so the stub
would report state `<sha>` and `_finished_head` would reject P before the fold ("its PR
is …", `flow.py:987-988`), testing the pre-fold path instead. I added a separate
`self.gh_heads` override (`test_flow_resume_stack_prereqs.py:57`, `:105-106`); every
existing test leaves it empty, so they run unchanged. Criterion 7 asserts P reached the
fold: its not-carried line contains "is not known to be merged" (from `_gone_branch`,
`integrate.py:717`), which it does both before and after the fix.

## Refuting my own test

- **(a) Genuine red? Yes.** The C4 gate (`engine/scripts/run-verify.sh`) reverted the
  production hunks (flow.py, integrate.py, docs) and kept the test file: 6 failures, the
  six new tests; the 18 existing tests stayed green. Failure messages show the defect
  itself: for (1)–(4) and (7), `'issue_D' unexpectedly found in {...}` with stderr
  `flow: carried issue_Q, issue_X …` (Q carried with P's commit, D built on it); for (5),
  `'issue_P' not found in "flow: issue_Q … does not merge cleanly … get issue_Q's PR open
  …"`. With the fix: 24/24 green. `PDCA-EVIDENCE: C4 PASS — red without the fix, green
  with it`.
- **(b) Production path? Yes.** Each case calls `flow._drive_and_act` (the file's `_run`)
  → the real `_carry_finished` → real `_fold_lines` → the real `integrate.fold` (the
  spy in `_run` only counts calls and calls through) against a real bare origin and
  primary clone. Only the build/sign-off/publish leaves and `gh` are stubbed, exactly as
  in the existing #646/#652 cases of the same file.
- **(c) Fixture includes the fault? Yes.** P's merge really fails in real git: a real
  `base.txt` conflict in (1)–(5), and a really deleted `fix/P` with the PR stubbed OPEN in
  (7) (a gone-branch `IntegrationError`, not `_Conflict`). Q really holds P's commit
  (`_finished_on` asserts the ancestry, test file `:389-390`). In (3) Q really merges
  before P fails (order
  `["Q", "P", …]`); in (4) the earlier line L really existed on origin, P and Q were cut
  from it and record it as their stack base, and it was really deleted. Nothing is
  curated out.

## Gates run (project runners, from the instance root, with `timeout`)

- C4 `engine/scripts/run-verify.sh`: PASS (green 24/24; red 6 failing, all new).
- T2 `engine/scripts/run-docs-check.sh`: `docs lint clean, site render + link audit clean`.
- T3 `engine/scripts/run-suite.sh`: root suite 24 OK; driver suite 2465 OK (2 skips: env
  guards in unrelated files). This covers criterion (6): `test_flow_resume_stack_prereqs.py`,
  `test_integrate_stack_bases.py`, `test_flow_same_wave_conflict.py` and
  `test_integrate_clean_tree.py` (which also calls `fold(skipped=…)`) all green, unchanged.
- Commit readiness: the target has no formatter, linter or active git hook configured
  (no pre-commit config, no ruff/black/flake8 settings, only `.sample` hooks); its only
  commit rule is the DCO sign-off, which publish adds. New lines are ≤ 100 columns,
  matching `integrate.py`'s existing maximum.

## Exploratory probes (not shipped)

Run once through the same fixture from a stdin script (no files written; the fixture's
own temp repos are created and removed by its setUp/tearDown):

- **S1** criterion 5's shape in the reverse order `["Q", "P", …]`: Q still names P, P keeps
  "does not merge cleanly", one push.
- **S2** continued line: an earlier run of the batch put W and P(p1) on the line; P adds a
  p2 that conflicts with W; Q is cut from p1 with no edge. The carry continues the line
  with one unforced push, P is skipped, p2 is not on the line, p1 stays (known limit v),
  Q is carried (its only shared commit was already on the line).
- **S3** transitive hold: P gone (as in 7), Q = q1 + a merge of P, Z cut from q1. Q is held
  for P, Z is held for Q, q1 is off the line, D and F wait, one push.

## Housekeeping

On the first C4 run I redirected its output to `/tmp/claude-c4-672.log`, outside the roots
I may write to. Later runs piped output straight to the terminal instead. Per the
no-cleanup rule I left that one file in place for the harness.
