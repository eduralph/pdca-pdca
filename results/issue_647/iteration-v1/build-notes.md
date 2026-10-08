# Build notes — issue #647 (stack mode holds a dependent of an out-of-batch unmerged prereq)

Base: the folded worktree `$PDCA_WORKTREE` @ `c1f2306` ("pdca-integrate: issue_646", which
carries #591 and #646 on top of `main`). Every `path:line` below is on that tree with the
patch applied.

## What changed

1. **`merged.merged_into(cfg, dep_id, repo, base)`** — new, beside `is_merged`
   (`template/src/pdca_harness/merged.py:67-104`). Same shape as `is_merged`
   (`merged.py:37-64`): not COMPLETE ⇒ False; empty/missing `patch.diff` ⇒ True; no
   `pr_url` ⇒ False. Then:
   - reads the PR through the existing `pr_state` (`merged.py:91`), which already has the
     `OSError` guard (same guard as `merged_head`, cited in the brief) — so a missing `gh`
     is "not merged" with a stderr line, never a traceback;
   - counts MERGED only if the record's `mode != "stacked"` and `repo`/`base` equal the
     passed target (`merged.py:98`) — the `integrate._gone_branch` rule (`onto or
     rec.get("base") != base`), plus the repo check the brief asks for.
   - module docstring updated (`merged.py:20-22`).
   `is_merged` is untouched; its callers `merge.py:233` and `cli.py:1084` are untouched.

2. **`flow._runnable`** (`template/src/pdca_harness/flow.py:681-752`): two new keyword
   arguments, `requested` (bundle names the run was asked for) and `hold_unmerged`. The
   first branch of the dep loop (`flow.py:725-733`) now takes an out-of-batch dep when it is
   either a `Depends on (merged)` dep (as before, #186) **or** — with `hold_unmerged` — a
   plain `Depends on` dep that is not in `requested` and is COMPLETE. Both go through
   `merged.merged_into` with the DEPENDENT's target, `publish._resolve_target(d)[:2]`
   (`flow.py:731`, same call `_point_at_integration` makes at `flow.py:770`). A failing dep
   lands in `unmerged`, which prints ONE line per dependent (`flow.py:740-746`):
   `flow: issue_D held — prerequisite(s) issue_P not merged into main (org/repo), and no
   line of this run carries them; … Name them in the same \`pdca flow <ids>\` command so its
   line carries them, or wait until their PR merges into main, then re-run.`
   A non-COMPLETE plain dep still falls to the existing generic "not ready" branch.
   Docstring updated (`flow.py:685-712`).

3. **`_drive_and_act`** (`flow.py:2140-2149`): computes `hold_unmerged = do_publish and
   wave_mode != "merge" and publisher.mode != "stub"` (so `--no-publish`, merge mode and a
   dry-run hold nothing and ask no host) and `requested = batch_names ∪ bundle names of
   batch` (the same id→name normalisation `_finished_named` uses, `flow.py:814`). Passed
   into `_runnable`. For `flow_batch` the batch is the sweep (`flow.py:2371`), which never
   contains a COMPLETE P, so P is out of `requested` and the hold applies; for `flow_ids`
   the batch is the ids as typed, so a named-but-finished P stays child-1's (carried or in
   `held_finished`).

4. `_carry_finished` docstring "Not covered: … (#647)" now says `_runnable` holds those
   dependents (`flow.py:872-874`).

5. Docs: new paragraph in the stack-mode bullet of `docs/07-crosscutting.md:704-716`.

6. Existing test `test_flow_slice.py:1954-1965` (`RunnableMergeGate.
   test_out_of_batch_depends_on_merged_waits_until_merged`) mocked `merged.is_merged` and
   asserted `_runnable` called it. `_runnable` now calls `merged_into` for that case (the
   brief requires it), so the mock moves to `merged_into` and asserts it gets B's resolved
   `("org/repo", "main")`. This is the only existing-test edit. The neighbouring test
   `test_out_of_batch_plain_depends_on_keeps_complete_bar` still passes unchanged: it calls
   `_runnable` without `hold_unmerged`, i.e. the merge-mode / no-publish path.

## Test

`template/tests/test_flow_out_of_batch_prereq_hold.py` (new, 21 cases). Offline: bundles on
disk, `publish.json` records, `subprocess.run` patched only for `gh` argv, `_drive_wave`
stubbed to record what it built, `_publish_bundle` / `publish.draft_texts` /
`leaves.do_plan_batch` stubbed. Drives the real `flow.flow_ids` and `flow.flow_batch`.
Imports modules only.

Cases by success-criterion item:
- (1) OPEN PR: `flow_ids` (`["D","U"]`) and `flow_batch` (sweep) ⇒ D held, PLANNED, one
  line with `issue_D`, `issue_P`, `not merged into main`, `pdca flow`; U built.
- (2) MERGED `new-pr` into `main` ⇒ built; MERGED `stacked-pr` with base `main` ⇒ built.
- (3) MERGED `stacked-pr` into `pdca-integration/main` (#591's shape) — both entry points ⇒
  held; MERGED `stacked` on `main` ⇒ held; MERGED `new-pr` for `org/other` ⇒ held;
  `Depends on (merged)` merged into the line ⇒ held, merged into `main` ⇒ built.
- (4) empty patch / no patch (close marker) ⇒ built.
- (5) `gh` raising `FileNotFoundError` ⇒ held, no traceback (plain and `(merged)`); `gh`
  exiting 1 ⇒ held.
- (6) P named in the ids (carry stubbed as clean) ⇒ built, no `gh` call; `Stacks on` ⇒
  built; `--no-publish` ⇒ built, no `gh`; merge mode ⇒ built, no `gh`; dry-run (stub
  publisher) ⇒ built, no `gh`; `merged.is_merged` still True for a MERGED `"stacked"`
  record.

## Runs

The configured runner (`./scripts/pdca gates 647`) refused: "lane pdca-harness.pdca-wt is
busy (another Do or gate run holds it)" — it is my own Do run holding the lane. That refused
run wrote `check-gates.json` / `check-gates.md` (overall fail, C4 "worktree mismatch") into
the bundle at 12:01:25. They are stale and will be overwritten by the driver's own gate step
after Do; I did not delete them (cleanup is the harness's). So I used the runner command
`docs/INTEGRATION.md:53` and the brief name, wrapped in `timeout`:

- with fix: `cd template && PYTHONPATH=src timeout 600 python3 -m unittest
  tests.test_flow_out_of_batch_prereq_hold` ⇒ `Ran 21 tests … OK`.
- full offline driver suite with fix: `Ran 2359 tests in 57.5s — OK (skipped=2)`.
- `python3 docs/publishing/tools/lint_docs.py` ⇒ `lint_docs: OK`.
- Root (copier render) suite not run here; the change touches no template rendering. T3
  covers it at Check.

## Refuting my own test

- **(a) Genuine red? Yes.** I reverted only `template/src` (`git checkout -- template/src`,
  production diff kept in `.cache/prod-647.diff` and re-applied) and re-ran: `Ran 21 tests —
  FAILED (failures=9, errors=1)`. The 9 failures are every "held" case of (1), (3), (5)
  (pre-fix D is built, or `is_merged` counts the integration-line merge). The 1 error is
  the `Depends on (merged)` + missing-`gh` case: pre-fix `is_merged` raises
  `FileNotFoundError` out of the run. The 11 that pass pre-fix are the "builds as today" /
  "unchanged" cases, which should pass both ways.
- **(b) Production path? Yes.** The test calls the real `flow.flow_ids` / `flow.flow_batch`
  → `_drive_and_act` → `_runnable` → `merged.merged_into` → `merged.pr_state`. Only the
  build leaf, publish, text drafting, the Plan leaf and the `gh` process are stubbed; the
  readiness decision under test is not stubbed anywhere.
- **(c) Fixture includes the fault? Yes.** P is a real COMPLETE bundle on disk with a
  non-empty `patch.diff`, a resolvable `org/repo @ main` target and a `publish.json` whose
  `pr_url` the `gh` stub answers OPEN / MERGED; the #591 case uses the real record shape
  (`"mode": "stacked-pr"`, `"base": "pdca-integration/main"`). The missing-`gh` case raises
  the real `FileNotFoundError` from `subprocess.run`.

## Choices and what I ruled out

- **Hold vs. carry the out-of-batch prereq onto the line**: out of scope (rejected in #616
  v1–v3, per the brief). Not attempted.
- **Changing `is_merged`**: ruled out by the brief; its other callers keep their answer
  (pinned by the last test case).
- **`Depends on (merged)` now prints the new "held … not merged into <base>" line** instead
  of the generic "skipped — prerequisite(s) not ready" line. Brief (3) says such a
  dependent "is held, as in (1)". No existing test asserted the old wording for that case
  (`grep "not ready" template/tests` hits only in-batch / unpushed cases).
- **`Depends on (merged)` still asks `gh` in a dry-run / merge mode / `--no-publish`**, as
  it did before via `is_merged` — the brief scopes "asks no host" to the new hold, and #186
  gating is unchanged in those modes apart from the stricter "into which base" rule.
- **A record missing `repo` or `base`** (very old records) reads as "not merged into the
  base" ⇒ held. Fail-closed, matching the module's stated policy (`merged.py:10-14`).
- **`requested` is frozen before wave 0**, while `batch_names` can grow by split adoption.
  An adopted child is in `batch_names`, so it is in-batch and never reaches the new branch;
  only out-of-batch deps are checked against `requested`.
- **One `merged_into` call per dep per wave**: `_runnable` runs per wave, and a held D is
  not in later waves' runnable set except through the schedule; at most one `gh pr view` per
  out-of-batch prereq edge per wave — same cost as the existing #186 path.

## Commit-readiness

The target has no pre-commit hook in its git dir and no Python formatter config (no
`pyproject`/ruff/flake8 at the root; CI runs only `lint_docs.py`, render-check, and
linked-issue checks). I checked: `git diff --check` clean, no added line over 100 columns
(the files' existing width), `lint_docs.py` OK. `pyflakes` is not installed, so no
unused-import check beyond the suite importing every module.
