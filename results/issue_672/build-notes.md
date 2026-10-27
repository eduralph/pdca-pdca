# Build notes — issue 672 / carry-keeps-a-fold-time-skip-off-the-line (iteration 6)

Target: `eduralph/pdca-harness` `main` @ `d6057eb`, worktree `pdca-harness.pdca-wt-l1`.
Lines marked "base" are on `d6057eb`; all other `path:line` refs are in the worktree with
the patch applied. Files: `template/src/pdca_harness/integrate.py`,
`template/src/pdca_harness/flow.py`, `docs/07-crosscutting.md`,
`template/tests/test_flow_resume_stack_prereqs.py`. A copy of the test file is in the
bundle at `template/tests/test_flow_resume_stack_prereqs.py`.

## What this iteration did

The sign-off kept the v5 approach ("no leak, one push") and asked for three fixes. I
applied `iteration-v5/patch.diff` unchanged and then made only these changes.

### 1. Hold cause for a holder whose own merge fails too (code change)

`_built_on_skipped` (`integrate.py:1053-1074`) used to name another failed id as the cause
only when that id's *tip* was in the holder's history (v5: `tips[c] in mine`). Now it
checks against any of that id's *work* (`work[c]`, the same set `_work` computes at
`integrate.py:588`), and only ids **before** the holder in fold order can be its cause
(`failed[:i]`, `integrate.py:1068`). The first such id in fold order wins, and the
message names the shared commit it found (`integrate.py:1069-1074`).

- Why the fold-order restriction is required, not just a tie-break: a shared commit is in
  both work sets (the brief's Definition counts a shared commit as each one's work), so
  "holds the other's work" is symmetric. Without the restriction, P and Q name each other
  and neither line shows the real conflict. Mutant (d) below shows exactly that.
- The call site now passes `work` (`integrate.py:597-600`). `work` already holds an entry
  for every failed id, computed when it failed (`integrate.py:586-588`), so no new git
  call is needed for the cause side.
- `fold`'s docstring (`integrate.py:385-388`) and the doc (`docs/07-crosscutting.md:736-738`)
  now say this. The docstring says "whose merge failed" rather than "skipped", because held
  bundles are also recorded in `skipped`, and this rule only looks at failed ones.

Test: `test_a_failing_holder_of_an_earlier_commit_of_a_skipped_id_names_it`
(`test_flow_resume_stack_prereqs.py:652`), the reviewer's shape. P publishes p1. Q is cut
from p1 with no `Depends on`, and changes `other.txt`. P then adds p2 (`base.txt`). The base
changes both files. The test also checks that P and Q merge cleanly with each other
(`:662`), so this is not the "two that conflict with each other" limit (iii). Result
with the fix:

```
flow: issue_Q … is not carried onto <line>: issue_Q's branch origin/fix/Q holds <p1>, which is
also issue_P's work, and this fold leaves issue_P off <line> — holding issue_D this run;
issue_Q was built on issue_P, which is not carried (see its line): get issue_P carried, …
```

P keeps "does not merge cleanly". With the v5 rule the same run prints Q's own `other.txt`
conflict and "get issue_Q's PR open" (mutant (a) below reproduces that line exactly).

### 2. Two-step hold (test only)

`test_one_holding_only_a_commit_of_a_held_id_is_held_too` (`:673`). Q publishes q1. R is
`_finished_on("R", "Q")`, so it holds q1 and has no edge to P. Then `fix/Q` merges in `fix/P`
(helper `_merge_into`, `:492`), and P adds a conflicting p2. The test checks that Q holds p1
and R does not (`:688-689`). The fold skips P and holds Q for p1. R holds only q1, which is Q's work, so
it is held with cause Q. It is asked for as `["P", "R", "Q", …]`, R before Q, so R is only
caught on the second sweep of `_hold_work`, after Q's work has joined. This pins both
`work[n] = _work(...)` (`integrate.py:1044`) and the `while grew` loop (`:1034`): mutants
(b) and (b2) below each fail only this test.

### 3. A bundle that merges in pass 1, then fails on the restarted line (test only)

`test_one_merged_only_on_a_held_ids_work_fails_on_the_restarted_line` (`:698`).

- H is cut from P's p1 and adds `s.txt = s`.
- S is cut from the base and adds the same `s.txt = s`.
- T is cut from S.
- The base adds `s.txt = m` (and `base.txt = r`). H and T are updated from it, keeping
  their own `s.txt`. P adds a conflicting p2.

What the fold does:

- Pass 1: P fails, H merges, then S merges cleanly on top of H (same content), then T and
  X merge. H holds p1, so it comes off and the line restarts (`integrate.py:589-596`).
- Pass 2: S's `s.txt` now conflicts with the base, so S fails. T merges, and the second
  `_hold_work` call holds T because it holds S's commit s1.
- Pass 3: only X is left. It is carried with one push.

A spy around the real `integrate._merge_published` records S's results as
`[True, False]` (`:717-731`), so the test proves S really merged in the first pass and
failed in the second. Mutant (c) below, where the hold check runs in the first pass only,
fails only this test.

New test helpers: `_merge_into` (`:492`), `_merges_cleanly` (`:508`, a trial merge in the
fixture's scratch clone; plain `git merge`, so it does not need git ≥ 2.38 for
`merge-tree`), and `_finished_from` (`:518`).

## A behaviour change from v5 the human should see

v5's notes said a fold-order tie-break had been considered and rejected, because of the
reverse order. The sign-off asked for it, so it is in. The effect, from a probe I ran but
did not ship: criterion 5's shape (Q cut from P's tip, both conflict with the base), asked
for as `["Q", "P", …]`:

```
flow: issue_Q … does not merge cleanly … (conflicts in base.txt) … get issue_Q's PR open …
flow: issue_P … issue_P's branch origin/fix/P holds <p>, which is also issue_Q's work … issue_P
was built on issue_Q, which is not carried (see its line) …
```

One push, D held, and no commit of P or Q on the line, so nothing leaks. But in v5 this
order printed "Q names P" and P kept its own conflict. Now Q, asked for first, is the root
and P is named for Q's work. The `built_on` hint text then reads "issue_P was built on
issue_Q", which is the wrong way round. The reason text before it is accurate under the
brief's Definition (p is a commit Q shares, so it counts as Q's work). The doc's
known-limits sentence already covers this: "held for a commit its branch shares with the
failed one even when that commit is its own (say the failed one was built on it)"
(`docs/07-crosscutting.md:751-758`). In the order criterion 5 actually uses, `["P", "Q", …]`,
nothing changes.

**Rejected alternative, with its cost:** use tip ancestry first ("Q was built on P's tip")
and fall back to fold order only when neither tip contains the other. Done naively (one
cause per id, chosen per pair), this can form a loop. Example: n1 is first in fold order
and built on n2's tip, so n1 names n2. n3 sits between them in fold order and shares an
older commit with both, so n3 names n1 and n2 names n3. Three lines then point at each
other in a circle, and none of them shows a real failure. Making it loop-free needs one
combined order: a topological order of the tips, with fold order breaking ties.
That is about 10 more lines in `_built_on_skipped` (a Kahn-style loop over `failed`),
plus a two-level rule to explain in the docstring and the doc. I did not do it: the
sign-off named the rule ("breaking ties by the earlier id in fold order"), and this only
changes wording, never what is held. If you prefer v5's reverse-order wording, this
alternative is the way to get it.

## Kept from v5 unchanged (for reference)

- `fold` gains `pr_heads` / `holds` (`integrate.py:308-309`). The merge loop (base
  `integrate.py:515-544`) runs in passes (`integrate.py:531-596`). Each branch tip is read
  once and cached in `read` (`:531`, `:545-550`). A pass that skipped something computes
  each failed id's work with `_work` (`:586-588`, helper `:1000-1010`): `rev-list <tip read
  here> <PR head> --not <base_remote>/<base> <start_ref>`. That is the brief's Definition
  (both heads; measured against the base and the commit the line started from, base
  `integrate.py:498-499`; merge commits included; nothing exempt). `_hold_work`
  (`:1019-1050`) then leaves out every merged bundle whose head reaches any of that work,
  repeating until nothing new is held. If anything was held, the line restarts from the
  same `start_ref` with only the kept bundles (`:593-596`). The push is unchanged and runs
  once (`:608-617`; base `:552-561`). The in-run folds (`skipped=None`) raise before
  anything is appended to `new`, so they leave at `:580` with no work computed.
- `flow.py`: `_fold_lines` passes the two arguments through (`flow.py:919-920`, `:947-948`,
  doc `:935-938`). `_carry_finished` passes its `heads` as `pr_heads` and reads `holds` back
  (`flow.py:1116-1130`). Each held id gets the existing `built_on` hint (base
  `flow.py:997-998`) with the skipped id as `cause`, and its plain `Depends on` dependents
  wait through the existing `held` set (base `flow.py:1122-1132`). The docstring residual
  (base `flow.py:1052-1054`) is replaced (`flow.py:1058-1069`).
- Docs: the residual sentence (base `docs/07-crosscutting.md:728-730`) is replaced
  (`:728-740`). It says the carry *adds none* of the failed one's commits, not that the
  line is free of them. The over-holds (i)-(iii) and the gap (v) were added to the
  known-limits list (`:751-758`).
- The six brief criteria tests: (1) `:548`, (2) `:565`, (3) `:581`, (4) `:595`, (5) `:620`,
  (7) `:634`. The fixture gained `self.gh_heads` (`:57`, read at `:105`). (7) asserts that
  P reached the fold: its line has "is not known to be merged", from `_gone_branch`, base
  `integrate.py:660-664`.

## Why in the fold, not in the carry (the brief asks for this)

The carry cannot know which ids the fold skips until the fold has tried the merges, and
the fold pushes at the end of the same call (base `integrate.py:552-561`). So the decision
must sit between the last merge and the push, which is inside `fold`. The carry-side
options cost more:

- **Two fold calls** (one that does not push, to learn the skips, then one that does): needs a `push=False`
  mode in `fold` (~8 lines), a way to return the heads it read (~6), and a second
  `_fold_lines` call plus the work computation in `flow.py` (~45). Every carry fold would
  merge everything twice, even when nothing is skipped. And the two calls take the
  integration lock separately (`_fold_lines` opens its own `ExitStack`, base
  `flow.py:939`), so origin's line could move between them and the second fold would
  refuse it (base `integrate.py:488-497`).
- **Trial merges in the carry**: this would copy the conflict, gone-branch and base-take-in
  paths (base `integrate.py:608`, `:638`, `:699`). That is the parallel implementation the C5
  gate exists to catch.

Inside the fold, the common cases cost nothing extra. With no skip it is one pass, as
before. A skip with no merged holder costs a few `rev-list` calls. Only a merged holder
causes a second pass.

## Mutation checks (each run once, then restored from `patch.diff`, byte-identical)

The test module was run with `cd template && PYTHONPATH=src python3 -m unittest
tests.test_flow_resume_stack_prereqs` under `timeout 300`, the same command
`run-verify.sh` uses.

| Mutant | Change | Result |
|---|---|---|
| (a) | v5 cause rule (`tips[c] in mine`) | only the finding-1 test fails; Q's line shows its own conflict + "get issue_Q's PR open" |
| (d) | any other failed id can be the cause (no fold order) | finding-1 test and criterion (5) fail; P and Q name each other |
| (b) | `work[n] = []` in `_hold_work` (held ids add no work) | only the two-step test fails; R carried |
| (b2) | `_hold_work` makes one sweep, not a fixed point | only the two-step test fails; R carried |
| (c) | hold check only in the first pass with a failure | only the restarted-line test fails; T carried with s1 |

So each sign-off item has a test that fails when, and only when, its code is broken.

## Refuting my own test

- **(a) Genuine red? Yes.** C4 (`engine/scripts/run-verify.sh`) reverted the production
  hunks and kept the test file. 9 tests failed: the 6 brief criteria and the 3 new tests.
  The other 18 stayed green. Every red is an assertion failure, not a load error. For (1)-(4),
  (7) and the two-step and restarted-line tests, it is `'issue_D' unexpectedly found` (D
  was built on a line holding P's commit). For (5) and the finding-1 test, it is
  `'issue_P' not found` in Q's line. With the fix: 27/27 green.
  `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`. The mutants above show that
  each new test also goes red without its specific piece of code, not only without the
  whole fix.
- **(b) Production path? Yes.** Each case calls `flow._drive_and_act`, which runs the real
  `_carry_finished`, then the real `_fold_lines`, then the real `integrate.fold`, against a
  real bare origin and primary clone. Only the build, sign-off and publish leaves and `gh` are
  stubbed, as in the #646/#652 cases of the same file. The restarted-line test's spy calls
  the real `_merge_published` and re-raises its errors.
- **(c) Fixture includes the fault? Yes.** P's merge really fails in real git: a real
  `base.txt` conflict, or in (7) a really deleted `fix/P` with the PR stubbed OPEN. The
  holders really hold P's commits (the ancestry is asserted). In the finding-1 test Q
  really conflicts on its own, and really merges cleanly with P. In the two-step test R
  really lacks p1. In the restarted-line test S really merges and then really fails, as
  the spy shows. Nothing is curated out.

## Gates run (project runners, from the instance root, under `timeout`)

- C4 `engine/scripts/run-verify.sh`: PASS (green 27/27; red 9 failing, all of them new).
- T2 `engine/scripts/run-docs-check.sh`: `docs lint clean, site render + link audit clean`.
- T3 `engine/scripts/run-suite.sh`: root suite 24 OK; driver suite 2468 OK (2 skipped,
  environment guards in unrelated files). This covers criterion (6):
  `test_flow_resume_stack_prereqs.py` (its 18 tests on base are unchanged and green),
  `test_integrate_stack_bases.py` and `test_flow_same_wave_conflict.py` are all green.
- Commit readiness: the target has no formatter, linter, pre-commit config or active git
  hook (only `.sample` hooks). Its commit rule is the DCO sign-off (`CONTRIBUTING.md:11-19`),
  which publish adds. `git diff --check` is clean. The longest new line is 99 columns in
  `integrate.py` (that file already has a 100-column line) and 98 in the test file.

## For the human at sign-off

- **The reverse-order wording change** described above (v5 rejected that tie-break; the
  sign-off chose it).
- Still true from v5: any finished id whose branch shares a commit with a skipped id is
  held. That includes a prerequisite whose finished dependent fails: if Q is cut from P
  and Q's own merge fails, P is held, because P's commit counts as Q's work. P's
  dependents then wait. The brief asks you to accept this over-hold explicitly
  (plan-review note 5).
- Known limit (v): on a line continued from an earlier run, a skipped P's commits already
  on that line stay there. This carry adds none of P's new ones. It is in the doc and the
  docstring.
- After a restart, `_merge_published` runs again for the kept bundles. So a gone-branch
  bundle's `gh` lookup and its `integrate:` stderr line can repeat once in that rare case.

## Housekeeping

On the first T3 run I redirected the output to `/tmp/claude-672-t3.log`, which is outside
the folders I may write to. Later runs piped the output straight to the terminal. Under
the no-cleanup rule I left that one file in place for the harness. (v5 left a similar
`/tmp/claude-c4-672.log`.) The probe and the stderr capture above were run from stdin
scripts and wrote no files; the fixture creates and removes its own temporary repos.
