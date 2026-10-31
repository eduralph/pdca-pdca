# Build notes — issue 838, iteration 3: merge mode names a block by review remarks

Target: eduralph/pdca-harness @ main, worktree base `3c11556` (= `origin/main`). "main :N"
is a line on that base; "post :N" is the line in the patched worktree. Unless a path is
given, lines are in `template/src/pdca_harness/merge.py`. The brief's own line numbers
(`merge.py:438/453/536/620-631`) come from an older main; on `3c11556` the same code is
`_undo_ready` main :460, `_refuse` main :475, the `merge_requires` gate main :626 and the
failed-merge branch main :715-725.

I started from the iteration-v2 patch, which still applies cleanly, and changed what the
carry-forward asked for plus the small related defects listed in section 3. Its other design
calls are unchanged (section 4).

## 1. Carry-forward: one shared `merge_wait_secs` (C5)

**The defect.** `_remarks_block` gave the `UNKNOWN` poll a fresh, full `merge_wait_secs`,
after the update and rollup waits had already used part of it. With 20 s that slept
`[15, 5, 5, 5, 5]`, 35 s in total, while the PR stayed marked ready. The brief says "polled
on the same budget" (brief.md:4, leg iii).

**The fix.** The cause is that `_wait_for_green` does not tell its caller what it used, so
it now does, the way `_wait_for_update` already returns `waited` (main :429-430):

- post :237-243 — the return becomes `(verdict, detail, waited)`; `waited` includes `spent`.
  All four return statements change (main :264, :273, :279-280, :286; post :277, :286,
  :293, :299).
- post :785 — `waited = 0` moves out of the `merge_requires` branch (from main :647), so it
  is defined under `"required"` too, where nothing has been spent.
- post :841 — `_merge_one` keeps the value (main :673).
- post :890 — `_remarks_block(d, str(pr_url), cfg.merge_wait_secs - waited)`. `_merge_state`
  (post :520) needed no new parameter: its `wait_secs` is now what is left. With nothing
  left it reads once and does not sleep (post :530-532).

What is left is never negative, because `_wait_for_green` never sleeps past `wait_secs` (main
:268, :278) and `Config.load` rejects a negative value (`config.py:753`).

Cost: 9 production lines (5 in `_wait_for_green`, the `waited = 0` move, 2 at the call, 1
argument) plus 2 lines in existing tests that use the return value
(`template/tests/test_merge.py:1210`, `template/tests/test_merge_third_remote.py:147`).

**Rejected alternatives.**

- A new `_wait_for_green_charged` returning three values, with `_wait_for_green` left as a
  wrapper: the same 9 lines plus about 3 for the wrapper, and no edit at `test_merge.py:1210`.
  But `_merge_one` would then bypass the `merge._wait_for_green` that
  `test_merge_third_remote.py:154` patches, so those tests would reach the real rollup read and
  fail on "unexpected gh call". It costs more and saves nothing.
- An out-parameter (`used: list[int]`): 1 parameter + 4 assignments + 2 lines at the caller +
  the same `waited` move and argument, also 9 lines. It would spare the 2 test edits, but the
  file has no such pattern and `_wait_for_update` already returns `waited`, so I followed that.
- `time.monotonic()` around the waits in `_merge_one`: about 3 lines and no test edits. Rejected
  on behaviour, not size: every wait here charges the sum of its `_sleep` steps (main
  :268-270) and tests patch `_sleep`, so a wall-clock figure would disagree with those
  counters and a regression test would have to patch the clock as well.
- One `_Budget` object passed to all three waits: about 20 lines, changing the signatures of
  `_wait_for_update` and `_wait_for_green`. It reads well, but it reworks #462/#531 code this
  issue does not need to touch.

## 2. Carry-forward: a failed thread read must not look like "no threads"

**The defect.** `threads = threads or []` (v2 `merge.py:607`) wrote `"threads": []` when the
read failed beside a CHANGES_REQUESTED review, and the message named only the review. The
file then said "none" when the truth was "unknown", and child-3 is meant to act on this file.

**The fix.**

- post :624 — the file records `threads` as it is: a list when read, `null` when not. I chose
  `null` over a second `threads_unreadable` key because one field then has one meaning, and a
  reader that loops over it fails loudly instead of acting as if there were none.
- post :638-641 — the message adds "Its review threads could not be read (`gh api graphql`),
  so there may be unresolved ones too."
- post :545-554 and post :592-605 (docstrings) state the contract: a list always means all of
  them, including when an earlier page succeeded and a later one failed.
- The no-review case is unchanged in behaviour: a warning line, the generic refusal, no file
  (post :615-619; brief.md:4, leg ii). I corrected the warning's wording, since `None` also
  covers a repeated cursor and an unreadable answer, not only "`gh api graphql` failed".

## 3. Related defects in this bundle's own new code (not in the carry-forward)

All of these sit between the failed `gh pr merge` and `_undo_ready`, where an exception
leaves the PR marked ready. That breaks the success criterion ("is not left marked ready")
and the rule in the module docstring (main :47-50). They cost little, so I fixed them. Each
has a test and is easy to drop if the human prefers a tighter scope.

- post :562-583 — the whole page read now sits in one `try`, catching `OSError` (`gh` missing)
  and `AttributeError` (an answer of another shape) as well. This closes two advisory-review
  items from iteration 2 (no `except OSError`, and `[0] or {}` crashing on a non-object
  comment) in one place.
- A thread node that is not an object was silently skipped in v2 (v2 `merge.py:562`), which
  is the same "partial read taken as complete" problem as section 2. It is now a failed read.
- post :538-541 — `_login` reads an author without assuming it is an object, in the style of
  `_bucket` / `_name` (main :199-204). Used for threads and for reviews.
- post :620-629 — a file that cannot be written (`OSError`, say a full disk) no longer raises:
  the message says so and the PR still goes back to draft.

The attempt-start `unlink` (post :735) can also raise, but nothing is readied at that point
(`gh pr ready` is main :610), so there is no ready-mark to leave behind. I left it.

## 4. Unchanged on purpose

- **Detection only at the failed `gh pr merge`** (post :886-892, main :715-725), under both
  `merge_requires` values, so a successful merge costs no extra `gh` call. This rests on
  `gh pr merge` refusing a `BLOCKED` PR when not given `--admin` (`_merge_one` never passes
  it, main :568). That is from my memory of `gh`'s behaviour. I did not verify it against a
  live `BLOCKED` PR, and the builder guard blocks any `gh pr merge` command, its `--help`
  included, so I did not read the help text either.
- **The repeated-cursor case still discards threads already read** (advisory, iteration 2,
  marked optional). It fails safe. Keeping them would need `(threads, complete)` as a return
  value, a third state in the file for child-3 to handle, and "at least N" wording: about 10
  lines. `null` for any failed read is simpler. A later-page failure with no review therefore
  gives the generic refusal plus the warning, though some remarks were known.
- **Deferred findings** (`deferred-findings.json`) are for the human, not build work. That
  includes the wording question: the message says "blocked by" when `BLOCKED` and remarks
  coincide, though the driver cannot confirm they are the cause. The brief requires that exact
  string, and the host's own error is printed just above it (main :717), so the real cause is
  not lost.
- **Docs: only the sentence the brief names** (`docs/07-crosscutting.md:887-891`), unchanged
  from v2. `template/pdca.toml.jinja:186-188`, `template/docs/fork-discipline.md.jinja:64-65`
  and `config.py:378-385` also describe `merge_wait_secs`. None is false: they describe the
  waits up to the merge, and the new poll only uses what they leave. A one-line addition to
  the toml comment would be a reasonable follow-up, but the brief scopes docs to one sentence.

## Test — `template/tests/test_merge_review_remarks.py` (20 tests)

Imports only modules (`merge, merged, state`, plus the existing `config.Config` /
`LeafConfig`), never a symbol this change adds, so the red leg imports and fails on
assertions. Stubs `subprocess.run` as `template/tests/test_merge.py` does, including `gh api
graphql`.

New this iteration:

- `test_the_poll_gets_only_what_the_rollup_wait_left` (:349) — the reviewer's exact case:
  default `merge_requires`, 20 s, persistent `UNKNOWN`. Sleeps `[15, 5]`, 2 state reads,
  generic refusal, no file, PR undone.
- `test_the_poll_finds_a_block_on_what_is_left` (:360) — `UNKNOWN` then `BLOCKED` within the
  5 s left: named, file written. Passes on v2 too; it guards against over-tightening.
- `test_an_update_wait_is_charged_to_the_same_budget` (:370) — a PR that is behind, so all
  three waits run: sleeps `[5, 15]`, one state read, no sleep of its own.
- `test_with_no_budget_left_the_state_is_read_once` (:382) — budget spent on the rollup wait,
  and `merge_wait_secs = 0` under both `merge_requires` values.
- `test_threads_that_cannot_be_read_are_unknown_not_none` (:435) — six ways the read fails
  beside a CHANGES_REQUESTED review (first request, later page after a good one, repeated
  cursor, not JSON, `resource: null`, `gh` gone). Each: review named, message says the threads
  could not be read, `threads` is `null`, never a partial count.
- `test_threads_that_cannot_be_read_with_no_review_stay_generic` (:464).
- `test_an_unexpected_answer_still_returns_the_pr_to_draft` (:474) — five malformed shapes.
- `test_an_author_that_is_not_an_object_is_no_author` (:498).
- `test_a_file_that_cannot_be_written_still_returns_the_pr_to_draft` (:512).

Changed:

- `test_changes_requested_without_threads_is_named` (:417) also asserts `threads == []`, so
  "read, none" and "not read" are told apart.
- `test_unknown_is_polled_then_read` (:324) and `test_unknown_to_the_end_is_not_a_remarks_block`
  (:334) now pin the exact sleeps.
- The stub now reports `DRAFT` while the PR is not marked ready (:133-135, :154), as a host
  does. That also proves the state is read before the undo: read after it, every "blocked by"
  assertion goes red. `_assert_undone` now checks the PR's final state (`gh.ready`).
- `template/tests/test_merge.py:1212` — the shared `_wait` helper also asserts
  `waited == sum(slept)`, so every scripted rollup sequence in that class checks the new
  return value.

## Runs

- **C4 gate on the final tree**, `engine/scripts/run-verify.sh` → `PDCA-EVIDENCE: C4 PASS — red
  without the fix, green with it`. Log: `results/issue_838/c4-local.log`.
  - Green leg: `test_merge` 59 OK, `test_merge_review_remarks` 20 OK,
    `test_merge_third_remote` 9 OK.
  - Red leg: `test_merge_review_remarks` `FAILED (failures=33)`, 0 errors, 19 of 20 tests red.
    The one that stays green on main is leg (ii), `test_blocked_without_remarks_keeps_generic_refusal`,
    by design: main already refuses generically and writes no file.
  - Red leg, the other two modules: `test_merge` errors=7 and `test_merge_third_remote`
    errors=2. The gate runs them only because this patch edits one line in each, and they error
    with `ValueError` because the reverted `_wait_for_green` returns two values. They say nothing
    about behaviour. The real red is the 33 assertion failures above.
- **New tests against the rejected v2 code** (v2 production `merge.py` applied, new test file,
  `python -m unittest` under `timeout`, then restored and confirmed with `cmp` against
  `patch.diff`): `FAILED (failures=9, errors=5)`, 14 items, exactly the defects above:
  - budget, 3: `[15, 5, 5, 5, 5] != [15, 5]`, `[5, 15, 5, 5, 5, 5] != [5, 15]`,
    `[15, 5, 5, 5] != [15]`;
  - failed read, 6: all six subtests of the test at :435;
  - crash or silent skip, 5: the write failure, the three non-object comment/author shapes
    (`AttributeError`), and the non-object thread (skipped).
- **Whole suite**, `engine/scripts/run-suite.sh`: root `Ran 50 tests … OK`, driver `Ran 2667
  tests … OK (skipped=2)`, `PDCA-EVIDENCE: root suite OK, driver suite OK`. 2667 = v2's 2658 + 9
  new tests. Log: `results/issue_838/suite-green.log`. After this run I only rewrapped a
  docstring in the test file, then re-ran C4, not the whole suite.
- **Docs**, `engine/scripts/run-docs-check.sh`: `PDCA-EVIDENCE: docs lint clean, site render +
  link audit clean`.
- **C5**, `engine/scripts/run-prod-path.py`: `1 added driver-suite test(s) import the production
  package 'pdca_harness'`.
- **Not run by me:** `run-host-ci.sh` (T2 host CI parity) and T4. Check runs both; the docs
  text they depend on is unchanged from v2, where they passed or deferred.
- **Formatter / commit hooks:** the target has none to run: no `.pre-commit-config.yaml`, no
  `core.hooksPath`, no active git hooks, no ruff/black/flake8/isort in
  `template/pyproject.toml.jinja`, and `CONTRIBUTING.md` names none. Checked by hand: `git diff
  --check` clean, Python lines ≤ 100, docs lines ≤ 80. Publish adds the DCO sign-off at commit
  time.

## Live check against GitHub (read-only)

I called the production readers once with the logged-in `gh`:

- `_review_threads` on PR #830: `[]` (its threads are all resolved).
- `_review_threads` on a PR that does not exist (#999999): `None`, so that is the real shape of
  "not found" and it takes the failed-read path.
- `_merge_state` on PR #830 with no budget: `mergeStateStatus: UNKNOWN`, one read. #830 is
  already merged, so a host really does return that value for such a PR.

**What this does not show.** None of the 60 most recent PRs has an unresolved thread, so a real
unresolved thread has not gone through the reader, and a real `BLOCKED` PR has not been seen at
all. Those paths rest on the stub. This is the validation gap Check already raised, and it stays
open for the human.

Steps for a human to close it, on a sandbox repo (the `sandbox-gh-token` doctor row in
`pdca.toml` names `eduralph/pdca-stack-sandbox`), with "require conversation resolution" on:

1. Open a PR with one unresolved line comment and run it as a non-final merge-mode wave.
   Expect: the stop names `path:line`, `merge-remarks.json` is in the bundle, and the PR is a
   draft again.
2. Resolve the thread and re-run. Expect: it merges and the file is gone.
3. With reviews required, repeat with a "request changes" review and no thread. Expect: the
   review is named, `threads` is `[]`.

## Self-refutation

- **(a) Genuine red? Yes.** `run-verify.sh` reverted the production hunks and re-ran: 33 assertion
  failures across 19 of the 20 tests, e.g. `'blocked by 2 unresolved review thread(s)' not found
  in '… did not merge — a conflict, no merge rights …'`. Separately, putting v2's production code
  back turned the 14 items above red, so the new tests catch these findings specifically and not
  merely "no feature at all".
- **(b) Production path? Yes.** Every test calls `merge.merge_wave` → `_merge_one` → the real
  `_wait_for_green`, `_wait_for_update`, `_remarks_block`, `_merge_state`, `merged._pr_view`,
  `_review_threads`, `_refuse`, `_undo_ready`. Only `subprocess.run` (the `gh`/`git` boundary),
  `state.state`, `merged.is_merged`, `_sleep` and, in one test, `Path.write_text` are patched.
  The live check called the production readers against GitHub itself.
- **(c) Fixture includes the fault? Yes, within the stub.** The budget tests use a state that stays
  `UNKNOWN` with a real rollup confirm and a real update wait in front of it. The failed-read tests
  fail the real request, including a later page after a good one. The stub models a draft reading
  `DRAFT`. Not modelled: GitHub computing `mergeStateStatus` live, and a real unresolved thread
  (see the live check).

## Housekeeping

- **My slip:** while comparing against v2 I wrote one file outside the harness roots,
  `/tmp/.unused`, a copy of the worktree diff with no other use. I did not delete it, since cleanup
  is the harness's.
- **The builder guard blocked two of my commands**, and I did not try to get around what it
  protects. One was a Python script editing files whose text contained `gh pr` in backticks; I
  made those edits with the Edit tool instead. The other was `gh pr merge --help`; I dropped it and
  marked that claim unverified in section 4. No `gh pr ready` or `gh pr merge` ran outside the
  stubs.
- **Reading beyond the brief:** the `iteration-v2/` artifacts the carry-forward points at, the
  cited peers, and the files that use `_wait_for_green` or describe `merge_wait_secs`, because
  changing that return value needed them.
- The worktree has the new test file registered intent-to-add (`git add -N`) so `git diff` includes
  it in `patch.diff`. Nothing committed, nothing pushed, no PR.
