# Build notes — issue #647, iteration 2 (stack mode holds a dependent of an out-of-batch unmerged prereq)

Base: the folded worktree `$PDCA_WORKTREE` (`/home/eddie/pdca/pdca-harness.pdca-wt`) at
`c1f2306` ("pdca-integrate: issue_646" — `main` plus #531, #590, #591, #646). Lines marked
"base" are on `c1f2306`; all other `path:line` references are on that tree with `patch.diff`
applied.

Inputs read: `brief.md`, and (because the carry-forward block points at it)
`iteration-v1/` — its patch, build notes, review, code review, gate files and
`session-carry-forward`.

## What iteration 1 got wrong, and what this attempt does about it

1. **A dependent with no usable target was held forever** (sign-off item 1). Iteration 1
   passed `("", "")` to `merged_into`, which then rejected every record, and printed
   "not merged into  ()". Now `_runnable` resolves the dependent's target once
   (`flow.py:723`) and sets `targeted = bool(repo and base)` (`flow.py:724`), the same
   test publish uses before it skips a target-less bundle (`publish.py:183-188` base).
   - Plain `Depends on`: no #647 hold unless `targeted` (`flow.py:737`).
   - `Depends on (merged)`: `merged_into` with an empty `repo` or `base` skips the base
     rule (`merged.py:95`, `merged.py:104`), so any merge counts. That is `is_merged`'s
     answer, read through the guarded `pr_state` (`merged.py:97`). A "not merged" answer
     goes to `unmet` with the old "prerequisite(s) not ready" line (`flow.py:745-747`).
2. **A `Depends on (merged)` prereq that is not COMPLETE got the "wait for its PR" advice**
   (sign-off item 2). The state check now runs first, for every edge (`flow.py:731-733`),
   so a PLANNED or DISCONTINUED prereq always goes to `unmet` ("not ready") and no `gh` call
   is made. This is the same routing as before #647: base `is_merged` returned False for a
   non-COMPLETE prereq without calling `gh` (`merged.py:43-44` base).
3. **C4 never ran.** Iteration 1's builder ran `./scripts/pdca gates 647` while its own Do
   run held the lane. The gate refused ("lane … is busy") and wrote a failing
   `check-gates.json` into the bundle (the refused run's log is still in the worktree at
   `.cache/gates-647.log`). `state.state` treats a bundle with `check-gates.json` as
   past BUILT (`pdca-pdca/src/pdca_harness/state.py:363`), so the driver most likely did
   not re-run the gates after Do, and that stale failure became the
   Check result. This time I did **not** run `pdca gates`. I ran the C4 command itself,
   `engine/scripts/run-verify.sh`, which takes no lane lock and writes nothing into the
   bundle. The bundle has no `check-gates.json`, so the driver's own gate step will run.
   Possible Act item: refuse `pdca gates <id>` from inside that bundle's Do leaf, or
   re-gate when `check-gates.json` is older than `patch.diff`.

Two more problems of the same kind as item 2 turned up while I fixed it. Both are fixed and
tested:

4. **A prereq with no usable target held its dependents forever** (iteration 1 did this
   implicitly: no `publish.json` means no PR, so `merged_into` returned False every time).
   Such a prereq never opens a PR (publish skips it), and neither the fold nor #646's carry
   ever puts it on a line (`integrate._fold_candidates`, `integrate.py:161-169` base). So
   naming it in the run, which is what the advice says to do, would release the dependent
   without carrying anything. The plain hold now applies only to a prereq the fold would
   carry: `integrate._fold_candidates([p])` (`flow.py:736-738`). This is the same
   definition `_carry_finished` uses (`flow.py:891`, `_fold_candidates(finished)`). The
   brief's criterion (1) already lists "a non-empty patch.diff and a resolvable target" as
   preconditions of the hold.
5. **The advice "name it in the same `pdca flow <ids>` command" was false in two cases.**
   (a) A `Depends on (merged)` edge: #646's carry only looks at plain `Depends on`
   (`brief.depends_on`, `flow.py:853` base), so naming the prereq does nothing for it.
   (b) A plain prereq whose target differs from the dependent's: the carry folds it onto
   *its* target's line, and `_point_at_integration` points the dependent at its own
   target's line (`flow.py:744` base). Now that advice is given only for a plain edge
   whose fold target equals the dependent's (`flow.py:749-750`). Otherwise the line says
   only "wait until their PR merges into main" (`flow.py:755-761`).

## What the patch changes

- `template/src/pdca_harness/merged.py:67-111` — new `merged_into(cfg, dep_id, repo, base)`,
  beside `is_merged`. Same shape as `is_merged` (`merged.py:34-61` base): not COMPLETE ⇒
  False; empty or missing patch ⇒ True; no `pr_url` ⇒ False. It then reads the PR with
  `pr_state`, which already has the `OSError` guard (`merged.py:102-106` base; the same guard
  as `merged_head`, `merged.py:77-81` base). An unreadable PR is "not merged", with a stderr
  line. MERGED counts only if mode is not `"stacked"` and the record's `repo` and `base` equal
  the passed target (`merged.py:104-110`). That is the fold's rule in
  `integrate._gone_branch` (`integrate.py:520` base: `if onto or rec.get("base") != base`),
  plus the repo check the brief asks for. With no target it skips that rule (item 1).
  The module docstring mentions it (`merged.py:21-23`). `is_merged` is unchanged, and so are
  its callers: `cli.py:1084` and `merge.py:387` (the brief's `merge.py:233` has moved on
  this base).
- `template/src/pdca_harness/flow.py:681-767` — `_runnable` gains `requested` and
  `hold_unmerged` (both keyword-only, defaults keep old behaviour for direct callers).
  Order per edge: not COMPLETE ⇒ `unmet` (`:731-733`); out-of-batch and either a
  `Depends on (merged)` edge or a plain edge that qualifies for the hold (`:736-739`) ⇒
  `merged_into` against the dependent's target (`:743`); false ⇒ `unmet` when the dependent
  has no target (`:745-747`), else `unmerged` (`:748`). `held` handling is as before
  (`:751-754`). One line per held dependent (`:755-761`), for example:
  `flow: issue_D held — prerequisite(s) issue_P not merged into main (org/repo), and no line of this run carries them; not built on a base missing them. To build it, name issue_P in the same `pdca flow <ids>` command so the run's line carries them, or wait until their PR merges into main, then re-run.`
  The docstring is rewritten to match (`:685-714`).
- `template/src/pdca_harness/flow.py:2155-2165` — `_drive_and_act` computes
  `hold_unmerged = do_publish and wave_mode != "merge" and publisher.mode != "stub"`
  (so `--no-publish`, merge mode and a dry-run hold nothing and ask no host for the new
  hold), and `requested` = the drive set plus the ids asked for, normalised the way
  `_finished_named` does (`flow.py:789` base). `flow_batch` passes the sweep as `batch`
  (`flow.py:2375` base), and the sweep never includes a COMPLETE prereq, so the hold
  applies there. `flow_ids` passes the ids as typed (`flow.py:2529` base), so a named but
  finished prereq stays with #646's carry.
- `template/src/pdca_harness/flow.py:887-889` — `_carry_finished`'s docstring no longer says
  #647 is "not covered".
- `docs/07-crosscutting.md:703-719` — new paragraph in the `"stack"` bullet.
- `template/tests/test_flow_slice.py:1954-1966` — `RunnableMergeGate.
  test_out_of_batch_depends_on_merged_waits_until_merged` mocked `merged.is_merged`, and its
  prereq `X` did not exist on disk. `_runnable` now calls `merged_into` (the brief requires
  it) and checks state first (sign-off item 2), so the test now makes `X` COMPLETE (which
  is what its own comment describes) and mocks `merged_into`, asserting it gets B's
  `("org/repo", "main")`. This is the only change to an existing test. Its two neighbours
  pass unchanged.

## The test — `template/tests/test_flow_out_of_batch_prereq_hold.py` (31 cases)

Offline. Bundles on disk with `publish.json` records. `subprocess.run` is patched, but only
`gh` argv is answered by the stub; everything else runs for real. `flow._drive_wave` is
stubbed to record what it was asked to build. `flow._publish_bundle`,
`publish.draft_texts` and `leaves.do_plan_batch` are stubbed. Imports modules only. A copy
is in the bundle at the path the brief names (`template/tests/…`), identical to the one in
`patch.diff`.

By criterion:
- (1) OPEN PR, prereq not requested: `flow_ids(["D","U"])` (`:201`) and `flow_batch` (`:207`)
  ⇒ D held, PLANNED, exactly one line naming `issue_D` and `issue_P` with
  `not merged into main` and the "name issue_P in the same `pdca flow <ids>` command"
  advice; U built. Prereq of another target ⇒ held without the carry advice (`:213`).
- (2) MERGED `new-pr` into main ⇒ built (`:222`); MERGED `stacked-pr` with base main ⇒
  built (`:228`).
- (3) MERGED into `pdca-integration/main` (#591's shape), both entry points (`:236`,
  `:243`); MERGED `"stacked"` on main (`:249`); record for `org/other` (`:255`) ⇒ held.
  `Depends on (merged)`: merged into the line ⇒ held (`:261`); OPEN ⇒ held with "wait"
  advice only (`:268`); merged into main ⇒ built (`:274`).
- (4) Empty patch (`:282`), no patch (`:288`), prereq with no target (`:294`) ⇒ built.
- (5) `gh` raising `FileNotFoundError`: plain (`:304`) and `(merged)` (`:311`) ⇒ held, no
  traceback. `gh` exiting 1 ⇒ held (`:319`).
- (6) Prereq named in the run (carry stubbed as clean) ⇒ built, no `gh` (`:327`); `Stacks
  on` (`:337`); `--no-publish` (`:343`); merge mode (`:350`); dry-run (`:358`) ⇒ built, no
  `gh`; `merged.is_merged` still True for a MERGED `"stacked"` record (`:366`).
- Sign-off item 1: dependent with no target field (`:377`) or no `@ branch` (`:385`) ⇒
  built, no `gh`, no "not merged into". Target-less `(merged)` dependent: the #591-shaped
  MERGED record ⇒ built, and `is_merged` agrees (`:393`); OPEN ⇒ the old "not ready" line
  (`:402`); `gh` missing ⇒ "not ready", no traceback (`:411`).
- Sign-off item 2: `(merged)` prereq PLANNED (`:425`) or DISCONTINUED (`:432`) ⇒ "not
  ready", never "not merged into"/"wait until", no `gh`. These two call `flow._runnable`
  directly: `waves.check_dep_graph` refuses a run with a non-COMPLETE out-of-batch prereq
  before any wave (`waves.py:102-109`), so `_runnable` only sees one when the prereq's
  state changes mid-run (an iterate or discontinue while earlier waves run).

## Runs

- **C4, the gate's own script**, from the instance root:
  `PDCA_BUNDLE=…/results/issue_647 PDCA_WORKTREE=…/pdca-harness.pdca-wt timeout 900 ./engine/scripts/run-verify.sh`
  on the final `patch.diff` ⇒ exit 0. Green leg: new module `Ran 31 … OK`, `test_flow_slice`
  `Ran 108 … OK`. Red leg (production hunks reverted, tests kept): new module
  `FAILED (failures=11, errors=2)`, `test_flow_slice` `FAILED (errors=1)`. Verdict line:
  `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`. The script's restore
  trap put the tree back, and `git apply --check -R patch.diff` confirmed it afterwards.
  Full log: worktree `.cache/c4-647.log` (gitignored).
- `patch.diff` applies to `c1f2306` (checked with `git apply --cached --check` on a
  throwaway index in `.cache/`) and exactly matches the worktree (`git apply --check -R`).
- Offline driver suite: `cd template && PYTHONPATH=src python3 -m unittest discover -s tests`
  ⇒ `Ran 2369 tests in 56.3s — OK (skipped=2)`.
- Root suite (render + update-compat, instance venv with copier):
  `python3 -m unittest discover -s tests` ⇒ `Ran 24 tests — OK`.
- T2 docs: `lint_docs.py` ⇒ OK; `render_site.py --check` (output to the gitignored
  `build/` in the worktree) ⇒ link audit OK.

## Refuting my own test

- **(a) Genuine red? Yes.** In the C4 red leg (only production hunks reverted) 13 of the 31
  cases go red. Eleven fail: D is built (the hold cases of (1), (3) and (5)), or
  `Depends on (merged)` prints "not ready" instead of "not merged into main". Two error:
  `FileNotFoundError: 'gh'` escapes `flow_ids` through base `is_merged`
  (`merged.py:52` base), which is the traceback the brief describes. The other 18 are
  "builds as today" or "unchanged" cases and should pass either way. Six of those are the
  sign-off pins (items 1 and 2), and they pass on the base because the base already
  behaved that way. They catch iteration 1's regressions instead. I checked that by putting
  **iteration 1's production hunks** under my tests: `FAILED (failures=20)`, including all 7
  sign-off cases. The rest of those 20 are the advice changes in items 4-5 and the new
  wording.
- **(b) Production path? Yes.** Real `flow.flow_ids` / `flow.flow_batch` →
  `_drive_and_act` → `_runnable` → `merged.merged_into` → `merged.pr_state` →
  `subprocess.run`, with only `gh` answered by the stub. The readiness decision is not
  stubbed anywhere. The two direct `_runnable` calls are explained above.
- **(c) Fixture includes the fault? Yes.** P is a real COMPLETE bundle (accepted through
  `signoff.record`) with a non-empty `patch.diff`, a resolvable target and a `publish.json`
  that the stub answers OPEN, MERGED, failing or missing. The #591 case uses the real record
  shape (`"mode": "stacked-pr"`, `"base": "pdca-integration/main"`). The missing-`gh` case
  raises a real `FileNotFoundError` from `subprocess.run`. Target-less dependents are real
  briefs without the field or without `@ branch`. The non-COMPLETE prereqs are a real
  PLANNED brief and a real DISCONTINUED sign-off.

## Choices and what I ruled out

- **Calling `merged.is_merged` literally for a target-less `(merged)` dependent** (the
  sign-off's wording). Ruled out because `is_merged` has no `OSError` guard
  (`merged.py:52-53` base), so a missing `gh` would still crash the run for those
  dependents, and criterion (5) does not exempt them. Keeping the literal call and still
  meeting (5) needs a second guard in `flow.py`:
  ```python
  try:
      ok = merged.is_merged(cfg, dep)
  except OSError:
      print(f"flow: could not run gh for {dep}; treating it as not merged", file=sys.stderr)
      ok = False
  ```
  That is +6 lines and a second place that reads `gh` for readiness, against +2 changed
  lines in `merged_into` (`targeted`, and the condition at `merged.py:104`). The answer is
  the same as `is_merged`'s, and `:393` asserts the two agree on the #591-shaped record.
- **A per-run cache of `gh` answers** (code-review efficiency nit). Not done. It needs a
  cache passed from `_drive_and_act` into `_runnable` (about +8 lines). A dependent sits in
  one wave, so this is one `gh pr view` per (dependent, out-of-batch prereq) per run, the
  same cost #186's path always had.
- **Carrying out-of-batch prereqs onto the line**: out of scope (rejected in #616 v1-v3).
- **Changing `is_merged`**: ruled out by the brief. Pinned by `:366`.
- **`Depends on (merged)` in a dry-run, merge mode or `--no-publish`**: it still asks `gh`,
  as `is_merged` did. The brief's "asks no host, holds nothing" is about the new hold, and
  says "the same rule now also governs `Depends on (merged)`" without a mode limit.

## Known limits for the human

- **A wave>0 dependent on the run's line.** "Merged" means merged into the dependent's
  target base, as the brief defines it. But a wave>0 dependent builds on the run's line,
  which was started from the base at the run's first fold. If P's PR merges into main
  *after* that fold and before D's wave, D is let through and built on a line tip without
  P. The window is narrow (P merges during the run), and #186's `(merged)` path already had
  the same gap. Closing it means checking P's merged head against the line tip with git,
  as `_finished_head` does (`flow.py:795-816` base). Out of scope here.
- **A prereq of another repo or branch** holds its dependent until someone removes the edge,
  because its record can never match the dependent's target. The brief's (3) asks for
  this. The held line gives only the "wait" advice, and `merged_into` prints where it did
  merge.
- **The repo comparison is exact (case-sensitive)**, which is how the fold keys targets too.

## Commit-readiness

The target has no pre-commit hook (none in `.git/hooks`, no `core.hooksPath`) and no
formatter or linter config (no `pyproject`, ruff, flake8 or `.pre-commit-config` at the
root). Its CI runs the docs checks and the render suites, and all of those pass above. I
also checked: `git diff --check` is clean; no added line is over 100 columns; an AST scan
finds no unused imports in the touched modules (pyflakes and ruff are not installed).

No external dependency was missing. Nothing pushed; no PR opened.
