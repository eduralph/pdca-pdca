# Build notes — issue 695 / run-catches-a-late-carried-rewrite-and-retries-the-fetch

Base: the wave-3 worktree `/home/eddie/pdca/pdca-harness.pdca-wt` at `ec1a36e`
(`pdca-integrate: issue_694`; 693, 673 and 694 folded in). Every `path:line` below is on
that commit unless marked "post-patch". The brief's citations were taken on `d6057eb`; they
moved, so the ones below are re-verified on `ec1a36e`.

## What changed

### (a) End-of-run check for a late rewrite

- `template/src/pdca_harness/integrate.py:681-718` (`_carried_tips`): split the existing
  rewrite message into a shared "facts" part and two tails. New keyword-only
  `rewritten: dict[str, str] | None`. When it is given, a rewritten branch is recorded
  (`rewritten[name] = report`) and the loop goes on; when it is `None` (every fold), the
  function raises exactly the message it raised before (same text, now built from the
  `facts` part plus the old tail). The judgment is unchanged: `_rev` → None (gone) is skipped
  and left to `_gone_branch`, `tip == took` or `_in_line(took, of=tip)` passes.
- New `integrate.rewritten_carried(cfg, bundles, carried, batch)` (post-patch
  `integrate.py:743-766`): builds `groups` / `refs` from `_fold_candidates` (`:201-209`) the
  same way `fold` does (`:452-480`), only for bundles in `carried` with a branch on record,
  then calls `_carried_tips(..., rewritten=found)`. So the end-of-run check and the in-fold
  check are one code path: same fetch, same ancestry rule, same wording of the facts.
- `template/src/pdca_harness/flow.py` `_drive_and_act`:
  - `line_stopped = False` before the wave loop (post-patch `:2489-2491`), set to `True` at
    the two breaks the brief names: fold `IntegrationError` (`ec1a36e` `:2641-2644`) and red
    re-gate (`:2655-2658`). Criterion (2b).
  - After `_report_conflict_holds` (`ec1a36e` `:2672`) — so after `_maybe_run_act`
    (`:2663-2665`), as the brief asks — the check runs only when the loop did not stop on
    the line, `carried_heads` is not empty, and the run folded for real (publishing on,
    stack mode, publisher not a stub). Its result goes into the 693 `holds` collector
    (`:2676-2678`) LAST, so it overwrites any hold reason for the same id.
  - New `_report_late_rewrites` (post-patch `flow.py:2698-2722`): one stderr line per
    rewritten bundle (`flow: <report>.`), returns `{name: "rewritten"}`. If the check itself
    cannot run (`IntegrationError`: fetch failed twice, missing checkout, git failure) it
    prints one line naming the carried bundles and returns them all as `"unchecked"`.
- `template/src/pdca_harness/cli.py`: `_FAILED_REASONS = {"rewritten", "unchecked"}`
  (post-patch `:693-697`) and in `_results_rc` (`ec1a36e` `:716-719`) a holds value in that
  set returns 1 before the `_RC_HELD` (3) branch. Return types of `flow_ids` /
  `flow_batch` / `_drive_and_act` are unchanged; no second channel — this extends 693's
  `holds: dict[str, str]` collector (`cli.py:640`, passed at `:650`, `:667`).

### (b) Retry the carried-branch fetch once

- `integrate._fetch` (`ec1a36e` `:1440-1457`) gains keyword-only `attempts: int = 1`; each
  remote's fetch is tried up to `attempts` times with a `_FETCH_RETRY_PAUSE = 1.0` s pause
  between (post-patch `:1486-1515`). Default 1 = unchanged behaviour for every other caller
  (`carry_view` `:232`, `_prepare_worktree` `:1466`).
- `_carried_tips` calls it with `attempts=2` (post-patch `:712`). That is the only fetch
  the brief puts in scope. The end-of-run check gets the retry too because it goes through
  `_carried_tips`.

**Why retry, not "take the lock and retry"** (the brief left it to Do): the clash in the
issue is with *another git process in the same checkout* holding a ref lock. Our
integration lock (`integ_lock`, `:264`) is a harness lock on the integration worktree; a
foreign git process does not take it, so holding it around the fetch would not prevent the
clash — it would only add lock ordering questions (the fold takes the locks per target in
sorted order at `:497`, after the check, and the check spans every target). A plain retry
after a short pause is the step that actually helps against a held `*.lock`, and it is 8
lines in `_fetch` plus one keyword at the call site. The 1 s pause is a guess at "long
enough for a typical concurrent ref update to finish, short enough not to matter": the
retry only ever happens after a failure.

### Docs

- `integrate.py` module docstring (`ec1a36e` `:39-45`) and `docs/07-crosscutting.md`
  (`ec1a36e` `:669-675`): the "next fold stops the run" sentences now also say that a
  rewrite after the last fold is reported at the end of the run (exit 1), that a branch
  deleted by then is not judged there, and that the check's fetch is tried twice.
- `_drive_and_act`'s `holds` paragraph and `_results_rc`'s docstring name the new reasons.

## A sample of the new stderr line (from test (1))

```
flow: issue_A's branch origin/fix/A was rewritten after this run folded it onto pdca-integration/main-r5601fafdbe44: it is now at 09575efb73a7, which does not contain c18b3f624117, the commit the line took from it. A re-publish (`pdca publish` force-pushes), a force-push or "Update with rebase" does this. No fold of this run came after it, so pdca-integration/main-r5601fafdbe44 still carries the old commits, and so does every PR this run cut from pdca-integration/main-r5601fafdbe44 after it took c18b3f624117: they hold commits origin/fix/A no longer has. Restore origin/fix/A to c18b3f624117 or a commit that contains it; or rebuild those PRs on the rewritten branch before any of them merges.
```

The remedy differs from the in-fold one on purpose: "re-issue the run" does not help at
the end — a re-issue skips the COMPLETE bundles, and the later-wave PRs already carry the
old commits. Restoring the branch, or rebuilding the dependent PRs, is what actually fixes it.

## Choices and what I ruled out

- **"unchecked" when the end-of-run check cannot run.** Not asked for by the brief. Without
  it, a fetch failure at the end would either crash the run with a traceback (the
  `IntegrationError` escapes `_drive_and_act`) or, if swallowed, let the run exit 0 without
  having checked — which is exactly the false success the invariant forbids. Fail-closed
  with a named line and exit 1 is the smallest honest option. Cost: 6 lines in
  `_report_late_rewrites` plus one set member in `cli`. Not covered by the test (the brief
  does not name it); a reviewer may want it dropped or tested.
- **A separate `late_rewrites` collector instead of reusing `holds`.** Ruled out by the
  brief ("do not build a second channel").
- **Re-implementing the check in `flow.py`.** Ruled out: it would duplicate `_carried_tips`'
  ancestry rule and wording. Sharing the function is ~10 changed lines in `_carried_tips`.
- **Checking after the budget-exhausted break too.** The flag is only set on the two breaks
  the brief names; on a budget break the check still runs. That run already exits 1 (bundles
  left PLANNED), and no fold reported the rewrite, so there is no double report.

## Test — `template/tests/test_integrate_carried_rewrite_late.py`

8 cases. Run cases go through `cli._flow` only (args as `test_flow_hold_exit_code.py`
builds them), on the real-git `StackFoldGit` fixture loaded by path and used as a helper
object (never subclassed). Imports are modules only.

| criterion | test | pre-fix | post-fix |
|---|---|---|---|
| (1) | `test_a_rewrite_while_the_last_wave_builds_is_reported_and_exits_1` | FAIL (no line) | pass, rc 1 |
| (1b) | `test_a_late_rewrite_outranks_a_hold` | FAIL (no line; rc would be 3) | pass, rc 1 |
| (1c) | `test_a_rewrite_during_the_last_fold_is_reported_and_exits_1` | FAIL (no line) | pass, rc 1 |
| (2) ff | `test_a_fast_forward_of_a_carried_branch_reports_nothing` | pass | pass, rc 0 |
| (2) merged+deleted | `test_a_carried_branch_merged_and_deleted_reports_nothing` | pass | pass, rc 0 |
| (2b) | `test_a_rewrite_the_next_fold_stops_on_is_reported_once` | pass | pass, 1 line, rc 1 |
| (3) | `test_one_failed_fetch_does_not_stop_the_fold` | ERROR "could not fetch" | pass |
| (4) | `test_a_fetch_that_keeps_failing_still_stops_the_fold` | pass | pass |

(5): full offline driver suite `cd template && PYTHONPATH=src python3 -m unittest discover
-s tests` → `Ran 2521 tests … OK (skipped=2)` with the patch. Includes every #633 test in
`test_integrate_stack_bases.py` and all of `test_flow_same_wave_conflict.py` and
`test_flow_hold_exit_code.py` (re-run on their own after the last edit: 86 tests OK).

Run through the project's C4 gate `engine/scripts/run-verify.sh` (with `PDCA_BUNDLE` and
`PDCA_WORKTREE` set): green leg `Ran 8 tests … OK`; red leg `FAILED (failures=3, errors=1)`;
`PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`.

## Refuting my own test

- **(a) Genuine red?** Yes. `run-verify.sh` reverted the production hunks (cli.py,
  flow.py, integrate.py) and kept the test: (1), (1b), (1c) failed on
  `assertEqual(len(lines), 1)` with stderr showing no rewrite line, and (3) errored with
  `IntegrationError: could not fetch origin in …/repo` raised from `_carried_tips` →
  `_fetch` — the exact pre-fix behaviour the brief describes. The module loaded fine (no
  `_FailedTest`), since it imports no new symbol.
- **(b) Production path?** Yes. The run cases call `cli._flow`, which runs the real
  `flow.flow_ids` → `_drive_and_act` → real `integrate.fold` (real git, real bare origin,
  real pushes) → the new end-of-run check → `cli._results_rc`. Only the leaves are stubbed
  (`_drive_wave` writes a patch and accepts, `_publish_bundle` pushes a real branch, `gh` is
  answered OPEN, `draft_texts` returns True) — the same stubs the merged 693/674 tests use.
  The fetch cases call the real `integrate.fold`; only `integrate._git` is wrapped, and it
  passes every call through to the real one except the fetch it fails.
- **(c) Fixture includes the fault?** Yes. The rewrite is a real force-push of `fix/A` on
  the bare origin from a second clone (`_push_from_human(..., force=True)`), and the test
  asserts it is not a fast-forward (`assertFalse(_ancestor(head, rebuilt))`). In (1c) the
  force-push happens inside the fold's own `push` call, and the test asserts the line holds
  A's old head and not the rewrite — so the line really carries commits the branch dropped.
  In (3) the injected fetch failure really happens (the spy returns 1 for the first fetch
  the fold makes, which is the `_carried_tips` fetch: it runs before `_prepare_worktree`'s).

## Commit-readiness

The target has no formatter config, no pre-commit config and no git hooks
(`core.hooksPath` unset, no hooks in the common git dir). I ran what its CI runs on these
files: `docs/publishing/tools/lint_docs.py` → `lint_docs: OK`;
`render_site.py --check` → `link audit OK`. No added line is over 100 columns. No unused
imports in the new test (checked by hand; pyflakes is not installed).
