# Build notes — issue 695 / run-catches-a-late-carried-rewrite-and-retries-the-fetch

Iteration 2. Base: the wave-3 worktree `/home/eddie/pdca/pdca-harness.pdca-wt` at `ec1a36e`
(`pdca-integrate: issue_694`; 693, 672, 673 and 694 folded in). "base `:N`" means a line on
`ec1a36e`; "post `:N`" means a line in the patched tree. The brief's citations were taken on
`d6057eb` and have moved; the ones below are re-checked on `ec1a36e`.

## What the carry-forward asked, and what I did

The round-1 finding: no test covered the `"unchecked"` path of the end-of-run check
(post `flow.py:2714-2720`) — nothing checked that a failing end-of-run fetch prints the
"could not check … by hand" line, exits 1, and prints no rewrite line.

Added `test_an_end_of_run_check_that_cannot_fetch_is_named_and_exits_1`
(`template/tests/test_integrate_carried_rewrite_late.py:211-239`), the case the finding
suggested: the two-wave run (A, then B depending on A) through `cli._flow`, with an
`integrate._git` spy that passes every call to real git until the run's one fold has pushed,
then fails every `fetch`. fix/A is not rewritten. The test asserts:

- both bundles COMPLETE (the run itself finished);
- exactly one stderr line starting "could not check whether a branch this run folded onto its
  line was rewritten", naming `issue_A`, the commit the line took from A (the head A's
  publish pushed), the cause ("could not fetch") and "by hand";
- no rewrite line ("was rewritten after this run folded" nowhere on stderr), no "STOPPING";
- exit code 1, read only from what `cli._flow` returns;
- the fault really happened: one push through `integrate._git` (the fold after wave 0) and
  exactly two failed fetches after it (the end check's fetch, tried twice).

Nothing else in a two-wave run fetches through `integrate._git` after that push: `_runnable`
fetches only for an out-of-batch prerequisite (`_line_lacks_merge`, base `flow.py:777-792`,
`:850-872`), and the sweep uses its own `sweep._git` and never fetches (`sweep.py:44`,
`:185-187`, `:293-304`). So the spy hits only the end-of-run check.

**The test binds every piece of that path** — checked by mutation through the C4 runner
(`engine/scripts/run-verify.sh`), each mutation reverted afterwards (the worktree was then
compared byte-for-byte with `patch.diff`: identical):

| mutation | result |
|---|---|
| fix reverted (C4 red leg) | FAIL `0 != 1` (no line; stderr shows only the sweep line) |
| `cli._FAILED_REASONS` without `"unchecked"` (post `cli.py:697`) | FAIL `3 != 1` |
| `_report_late_rewrites` swallows the error (`return {}`) | FAIL `0 != 1` (no line) |

## Other changes in this round (small, all mine from round 1)

- **The "could not check" line now names what to check.** Round 1 printed "check issue_A by
  hand" with no commit, which a human cannot act on. Post `flow.py:2715-2719` adds each
  carried bundle with the commit the line took from it, e.g. `(issue_A: c18b3f624117)`, and
  rewords the sentence ("could not check whether a branch … was rewritten since (…), so the
  line may carry commits no PR holds any more. Check by hand that each branch this run
  folded still contains the commit the line took from it (…)."). The docstring at post
  `flow.py:2706-2710` says so.
- **Docs wording.** Round 1's "The fetch that check makes before a fold takes its locks"
  came right after the sentence about the END-of-run check, so "that check" read as the end
  check. Now: "Both checks fetch while no integration lock is held …" — in
  `docs/07-crosscutting.md` (post `:675-684`, replacing base `:675`) and the `integrate.py`
  module docstring (post `:45-51`, replacing base `:45`). The doc paragraph also says that a
  run whose end check cannot run names the branches to check by hand and exits 1. Round 1
  left a 94-column line in the doc; the new text keeps base `:676` ("branch is deleted, the
  fold looks up …") untouched.
- **Report wording.** "No fold of this run came after it" → "No fold of this run ran after
  the rewrite" (post `integrate.py:727-732`; "it" was ambiguous).
- **cli.py comments.** The `holds` collector comment in `_flow_claimed` (post
  `cli.py:638-641`) and the `_results_rc` docstring's rule 1 (post `cli.py:704-708`) now
  name the #695 reasons accurately ("unchecked": the line *may* carry such commits).
  `_drive_and_act`'s `holds` paragraph (post `flow.py:2375-2379`) lost round 1's "carries a
  carried branch".
- **Fetch tests.** (3) now catches `IntegrationError` and fails with "one failed fetch
  stopped the fold: …" (post test `:311-321`), so its red is a FAIL, not an ERROR. (4) also
  asserts exactly two fetch attempts (test `:327`): a second failure stops the fold, and the
  retry does not loop. That makes (4) red before the fix too (`1 != 2`), which is right: the
  brief's scope says "retry it once … a second failure still raises".

The approach itself is unchanged from round 1: the finding was a missing test, not a wrong
design.

## The change (whole patch)

### (a) End-of-run check for a late rewrite

- `template/src/pdca_harness/integrate.py` `_carried_tips` (base `:681-718`, post
  `:688-741`): the rewrite message is split into a shared `facts` part (post `:721-725`) and
  two endings. New keyword-only `rewritten: dict[str, str] | None`. With it (the end check)
  a rewritten branch is recorded and the loop goes on (post `:726-733`); without it (every
  fold) it raises the same text as before (post `:734-740`). The judgment is unchanged: a
  branch that no longer resolves (`_rev` → None) is skipped and left to `_gone_branch`;
  `tip == took` or `took` an ancestor of `tip` passes (`_in_line`, base `:1097-1108`).
- New `integrate.rewritten_carried` (post `:744-765`): builds `groups`/`refs` from
  `_fold_candidates` (base `:201-209`) the way `fold` does (base `:458-478`), only for
  bundles in `carried` with a branch on record, and calls `_carried_tips(..., rewritten=…)`.
  One code path for the in-fold and end-of-run checks: same fetch, same ancestry rule, same
  facts wording.
- `template/src/pdca_harness/flow.py` `_drive_and_act`:
  - `line_stopped = False` before the wave loop (post `:2489-2491`), set at the two breaks
    the brief names: fold error (base `:2639-2644`, post `:2651`) and red re-gate (base
    `:2655-2659`, post `:2667`). Criterion (2b).
  - After `_report_conflict_holds` (base `:2672`, post `:2681`) — so after
    `_maybe_run_act` (base `:2663-2665`), as the brief asks — the check runs only when the
    loop did not stop on the line, `carried_heads` (base `:2408`) is not empty, and the run
    folded for real: publishing on, stack mode, publisher not a stub (post `:2682-2686`).
  - Its result goes into 693's `holds` collector last (post `:2689-2694`), so it overwrites
    any hold reason for the same id.
  - New `_report_late_rewrites` (post `:2698-2723`): one stderr line per rewritten bundle
    (`flow: <report>.`), returns `{name: "rewritten"}`; when the check cannot run it prints
    the one "could not check" line and returns every carried bundle as `"unchecked"`.
- `template/src/pdca_harness/cli.py`: `_FAILED_REASONS = {"rewritten", "unchecked"}` (post
  `:694-697`); `_results_rc` returns 1 for either before the hold branch (post `:729-730`;
  base `:717-719`). Return types of `flow_ids` / `flow_batch` / `_drive_and_act` unchanged;
  no second channel — it extends 693's `holds` collector (base `cli.py:640`, passed at
  `:650` and `:667`).

### (b) Retry the carried-branch fetch once

- `integrate._fetch` (base `:1440-1457`, post `:1487-1517`): keyword-only `attempts: int =
  1`; each remote's fetch is tried up to `attempts` times with a `_FETCH_RETRY_PAUSE = 1.0`
  s pause between (post `:1487-1488`, loop post `:1510-1517`). Default 1 keeps every other
  caller as it was (`carry_view` base `:232`, `_prepare_worktree` base `:1465`).
- `_carried_tips` calls it with `attempts=2` (post `:713`). The end-of-run check gets the
  retry too, since it goes through `_carried_tips`.

**Why retry, not "take the lock and retry"** (the brief left it to Do). The clash is with
*another git process in the primary checkout* holding a ref lock (an operator's `git fetch`,
a concurrent `pdca publish`). Our integration lock (`integ_lock`, base `:264-297`) is a
harness flock on a sidecar next to the *integration worktree*; no foreign git process takes
it, so holding it around the fetch would not prevent the clash at all. It would also cost:
`_carried_tips` runs at base `:485`, before the per-target loop that takes each lock at base
`:520-529`. Taking the locks for the fetch means entering every target's lock, in sorted
order, before `_carried_tips` (about 6 lines at `:485`), and then reworking `:520-529` so the
loop does not take the same lock a second time — a second `open()` + `flock(LOCK_EX)` from
the same process on a new file description blocks on our own lock — about 10-15 more lines,
and the end-of-run check would need its own copy. The plain retry is 6 changed lines in the
`_fetch` loop, a 2-line constant, `import time`, and one keyword at the call site, and it is
the step that actually helps against a held `*.lock`. The 1 s pause is a judgment: long
enough for a typical concurrent ref update to finish, and it only ever runs after a failure.

### Docs

`docs/07-crosscutting.md` (base `:669-675`, post `:675-684`) and the `integrate.py` module
docstring (base `:39-45`, post `:45-51`): the "next fold stops the run" sentences now also
say that a rewrite after the last fold is reported at the end of the run (exit 1), that a
run whose end check cannot run names the branches to check by hand and exits 1, that a
branch deleted by then is not judged there, and that the fetch is tried twice.

## Sample of the rewrite line (from test (1), round 1 — the wording of the remedy changed
only in "ran after the rewrite")

```
flow: issue_A's branch origin/fix/A was rewritten after this run folded it onto pdca-integration/main-r5601fafdbe44: it is now at 09575efb73a7, which does not contain c18b3f624117, the commit the line took from it. A re-publish (`pdca publish` force-pushes), a force-push or "Update with rebase" does this. No fold of this run ran after the rewrite, so pdca-integration/main-r5601fafdbe44 still carries the old commits, and so does every PR this run cut from pdca-integration/main-r5601fafdbe44 after it took c18b3f624117: they hold commits origin/fix/A no longer has. Restore origin/fix/A to c18b3f624117 or a commit that contains it; or rebuild those PRs on the rewritten branch before any of them merges.
```

The "could not check" line, as built by post `flow.py:2715-2719` (not captured from a run;
the test asserts each part of it):

```
flow: could not check whether a branch this run folded onto its line was rewritten since (could not fetch origin in <checkout> — the fold cannot see the branches it merges), so the line may carry commits no PR holds any more. Check by hand that each branch this run folded still contains the commit the line took from it (issue_A: <12-char head>).
```

## Test — `template/tests/test_integrate_carried_rewrite_late.py`

9 cases. Run cases go through `cli._flow` only (args built as
`tests/test_flow_hold_exit_code.py:147-148` builds them), on the real-git `StackFoldGit`
fixture (`tests/test_integrate_stack_bases.py:123-254`) loaded by path and used as a helper
object, never subclassed. Only modules are imported.

| criterion | test (line) | fix reverted | with fix |
|---|---|---|---|
| (1) | `test_a_rewrite_while_the_last_wave_builds_is_reported_and_exits_1` (:167) | FAIL, no line | pass, rc 1 |
| (1b) | `test_a_late_rewrite_outranks_a_hold` (:178) | FAIL, no line | pass, rc 1 |
| (1c) | `test_a_rewrite_during_the_last_fold_is_reported_and_exits_1` (:190) | FAIL, no line | pass, rc 1 |
| unchecked (carry-forward) | `test_an_end_of_run_check_that_cannot_fetch_is_named_and_exits_1` (:211) | FAIL, no line | pass, rc 1 |
| (2) fast-forward | `test_a_fast_forward_of_a_carried_branch_reports_nothing` (:243) | pass | pass, rc 0 |
| (2) merged + deleted | `test_a_carried_branch_merged_and_deleted_reports_nothing` (:251) | pass | pass, rc 0 |
| (2b) | `test_a_rewrite_the_next_fold_stops_on_is_reported_once` (:265) | pass | pass, 1 line, rc 1 |
| (3) | `test_one_failed_fetch_does_not_stop_the_fold` (:311) | FAIL "one failed fetch stopped the fold: could not fetch origin …" | pass |
| (4) | `test_a_fetch_that_keeps_failing_still_stops_the_fold` (:323) | FAIL `1 != 2` attempts | pass |

The (2)/(2b) cases pass before the fix by design: they guard against a false report and a
double report, and are not part of the RED the brief names.

**C4, through the project's runner** (`PDCA_BUNDLE=… PDCA_WORKTREE=… timeout 900
./engine/scripts/run-verify.sh`, on the final `patch.diff`): green leg `Ran 9 tests … OK`;
red leg `Ran 9 tests … FAILED (failures=6)` (no errors, no load failure);
`PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`.

**(5)** through `./engine/scripts/run-suite.sh` on the final tree: root suite `Ran 24 tests …
OK`; driver suite `Ran 2522 tests … OK (skipped=2)`; `PDCA-EVIDENCE: root suite OK, driver
suite OK`. That includes every #633 test in `test_integrate_stack_bases.py` (`:1151-1384`),
all of `test_flow_same_wave_conflict.py`, and 693's `test_flow_hold_exit_code.py`.

## Refuting my own test

- **(a) Genuine red? Yes.** With the production hunks reverted (C4 red leg), six cases
  FAIL on assertions: (1), (1b), (1c) and the new unchecked case find no line on stderr;
  (3) fails with the round-1 symptom, `IntegrationError: could not fetch origin in …/repo`
  raised from `_carried_tips` → `_fetch`; (4) sees one fetch attempt, not two. The module
  loads (no `_FailedTest`): it imports no symbol the fix adds. The new unchecked case also
  goes red under the two mutations above (exit 3; no line), so it binds the exit-code
  mapping and the printed line separately, not just "the fix exists".
- **(b) Production path? Yes.** The run cases call `cli._flow`, which runs the real
  `flow.flow_ids` → `_drive_and_act` → real `integrate.fold` (real git, a real bare origin,
  real pushes) → `_report_late_rewrites` → `integrate.rewritten_carried` →
  `_carried_tips` → the real `_fetch` → `cli._results_rc`. Only the leaves are stubbed
  (`_drive_wave` writes a patch and accepts, `_publish_bundle` pushes a real branch, `gh`
  answers OPEN, `draft_texts` returns True) — the same stubs 693's merged test uses. The
  `integrate._git` spies pass every call to real git except the ones they fail on purpose.
  The fetch cases call the real `integrate.fold`.
- **(c) Fixture includes the fault? Yes.** The rewrite is a real force-push of `fix/A` on
  the bare origin from a second clone, asserted not to be a fast-forward (test `:84`). In
  (1c) the force-push happens inside the fold's own `push` call, and the test asserts the
  line holds A's old head and not the rewrite. In the unchecked case the test asserts the
  fault was injected where it matters: exactly one push (the last fold) and two failed
  fetches after it. In (3) the spy fails the first fetch the fold makes, which is
  `_carried_tips`' (it runs at post `integrate.py:492`, before `_prepare_worktree`'s), and
  (4) asserts both attempts were made and failed.

## Commit-readiness

The target has no formatter config, no pre-commit config and no git hooks (`core.hooksPath`
unset; no non-sample hooks in the common git dir; no `.pre-commit-config.yaml`,
`pyproject.toml`, `setup.cfg`, `ruff.toml`, `.flake8`). Its CI runs the docs lint, the site
render with link audit (`.github/workflows/docs-check.yml:33,36`) and the root suite
(`render-check.yml:43,46`). I ran the project's T2 runner (`./engine/scripts/run-docs-check.sh`):
`lint_docs: OK`, `render_site: link audit OK`; the root suite is green above. No added line
is over 100 columns. No linter is installed here (no pyflakes/ruff), so I checked names by
hand: every annotation and call in the changed code resolves to an import (`flow.py:27`
has `Collection, Mapping`; `integrate.py:77-78` has `time`, `Iterable`).

## Not addressed

- The 8 deferred findings held in `deferred-findings.json` — the carry-forward marks them
  for the human at handover, not build work. I did not read them.

## A slip to report

I wrote one test-run log to `/tmp/issue695-t3.log` (the first `run-suite.sh` run), which is
outside the roots I may write to. It holds only test output. I did not delete it, since
cleanup is the harness's; later runs piped straight to a filter instead.

No external dependency was missing: Python 3 and git were enough.
