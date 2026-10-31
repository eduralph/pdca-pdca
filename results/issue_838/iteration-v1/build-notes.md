# Build notes — issue 838: merge mode names a block by review remarks

Target: eduralph/pdca-harness @ main (worktree base `3c11556`). Line numbers below are
post-patch in the worktree unless marked "main".

## What changed

- `template/src/pdca_harness/merge.py:496-604` (new, beside `_refuse` at :483 and
  `_undo_ready` at :468):
  - `_THREADS_QUERY` (:496) — GraphQL `resource(url:)` → `reviewThreads(first: 100)` with
    `id isResolved isOutdated path line originalLine` and the first comment's
    `body url author{login}`. Querying by URL means no owner/repo/number parsing of the
    recorded `pr_url`; threads are read generically (no bot-specific parser, per scope).
  - `_merge_state` (:513) — reads `mergeStateStatus,reviewDecision,latestReviews` through
    `merged._pr_view` (main `merged.py:187`, the peer the brief cites). While the read is
    `UNKNOWN` it polls through `merge._sleep`, bounded by `cfg.merge_wait_secs` — the knob
    the #462 rollup wait uses (`_wait_for_green`, merge.py:226 on main). Still `UNKNOWN`
    at the end → returned as-is → not a remarks block.
  - `_review_threads` (:531) — `gh api graphql`, keeps unresolved threads only; an outdated
    thread (`line: null`) reports `originalLine` and `outdated: true`.
  - `_remarks_block` (:565) — only for `BLOCKED`. Unresolved threads and/or
    CHANGES_REQUESTED (from `latestReviews` authors, falling back to `reviewDecision`) →
    writes `<bundle>/merge-remarks.json` and returns the reason; otherwise "" (generic
    refusal kept, no file, never "0 thread(s)").
- `merge.py:838-844` — in `_merge_one`'s failed-`gh pr merge` branch (main :617-631),
  call `_remarks_block`; if it names a block, `return _refuse(d, pr_url, why)` (which
  prints the STOP message and calls `_undo_ready`). Otherwise the old generic message +
  `_undo_ready` path is untouched.
- `merge.py:52-58` — module docstring paragraph.
- `docs/07-crosscutting.md:887-890` — one sentence in the `"merge"` bullet (after the
  `merge_requires = "required"` sentence, main :885-886).

`merge-remarks.json` shape: `{"pr_url", "mergeStateStatus": "BLOCKED", "threads": [ {id,
path, line, outdated, body, author, url}, ... ], "changes_requested_by": [logins]}`. The
brief's "one object per thread (id, path, line, body, author, url)" is the `threads` list;
I used an object at top level rather than a bare list so leg (v) (CHANGES_REQUESTED, no
threads) still has somewhere to record its remark, and child-3 has the PR URL in the file.
If the reviewer reads the brief as "top-level list", that is the one judgement call here.

## Why detect only at the failed merge (not before it in "all" mode)

GitHub refuses `gh pr merge` on a `BLOCKED` PR, so the block always surfaces as that
failure under both `merge_requires` values. Putting detection in that one place:
- gives leg (i) and the default mode the same path, same message, same file;
- adds **zero** `gh` calls on the success path. A pre-merge read in "all" mode would add a
  `gh pr view` to every merge, and the `_Host` fake in `template/tests/test_merge.py:737`
  counts `gh pr view` reads (`views`, and `lag` counts down per view in `_land_update`), so
  it would shift the update-landing timing many #531 tests depend on. Detection-on-failure
  leaves all 2654 existing tests green with no edits to them.

Rejected: sharing the exact remaining seconds of the rollup wait. `_wait_for_green`
(main merge.py:226) does not return the time it spent, so sharing would mean changing its
return type (2-tuple → 3-tuple, its 4 `return` statements) and its 3 call sites
(`grep -rn "_wait_for_green(" template/` → 4 text matches incl. the def): about 8 changed
lines, small, but a signature change on a function other bundles touch, for a poll that
in practice runs once on an already-computed state after a failed merge. I read
"the same budget" as the same `merge_wait_secs` bound with the same patchable `_sleep`; the
UNKNOWN poll happens after the rollup wait is over, so it is its own bounded wait of at
most `merge_wait_secs`. Flagging in case the human wants it strictly shared.

Not done (out of scope or deliberately left): a stale `merge-remarks.json` from an earlier
run is not deleted when a later run refuses generically or merges (child-2/3 territory);
threads beyond the first 100 are not paginated.

## Test — `template/tests/test_merge_review_remarks.py` (7 tests)

Imports only `merge, merged, state` and `config` (no new symbol), stubs
`subprocess.run` as `test_merge.py` does, including the `gh api graphql` call.
Covers: main case (2 unresolved + 1 resolved thread → named with path:line, file has 2
objects with all six keys, PR undone and not re-readied); leg (i) `required` (asserts no
`gh pr checks` call); leg (ii) BLOCKED + REVIEW_REQUIRED → generic, no file, no
"0 unresolved"; leg (iii) UNKNOWN×2 → BLOCKED acted on, and UNKNOWN forever → polled >1
time, sleeps sum ≤ budget, generic; leg (iv) outdated → `src/old.py:77`; leg (v)
CHANGES_REQUESTED only → named with the requester, not the approver.

## Runs

- Whole suite via `engine/scripts/run-suite.sh` with the fix: `Ran 2654 tests … OK
  (skipped=2)`, `PDCA-EVIDENCE: root suite OK, driver suite OK` (log: `suite-green.log`
  in this bundle).
- C4 gate `engine/scripts/run-verify.sh` (PDCA_BUNDLE=this bundle):
  `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`. Red leg: 6 of 7 FAIL on
  assertions (no import error); the 7th (leg ii) passes on main by design — main already
  gives the generic refusal and writes no file; it guards against the fix over-reaching.
- Docs: `engine/scripts/run-docs-check.sh` → `docs lint clean, site render + link audit
  clean`.
- Formatter: the target configures none (no ruff/black in `template/pyproject.toml.jinja`,
  no pre-commit config; CI workflows are DCO / docs / render). Lines kept ≤ 100 like the
  file. The DCO sign-off is added by publish at commit time.

## Self-refutation

- **(a) Genuine red?** Yes. `run-verify.sh` reverted the production hunks of
  `patch.diff` and re-ran: 6 failures, e.g. `'blocked by 2 unresolved review thread(s)'
  not found in '… did not merge — a conflict, no merge rights …'` and, for the UNKNOWN
  test, `0 not greater than 1` (main never reads `mergeStateStatus`).
- **(b) Production path?** Yes. The tests call `merge.merge_wave` → `_merge_one` → the
  real `_remarks_block` / `_merge_state` / `merged._pr_view` / `_review_threads` /
  `_refuse` / `_undo_ready`. Only `subprocess.run` (the `gh`/`git` boundary),
  `state.state`, `merged.is_merged` and `_sleep` are patched.
- **(c) Fixture includes the fault?** Yes. The stub host reports `BLOCKED`, returns real
  GraphQL-shaped thread nodes (including a resolved one, and an outdated one with
  `line: null`), and fails `gh pr merge` with GitHub's "base branch policy prohibits the
  merge" error, after a green rollup in "all" mode. Nothing is filtered out of it; what is
  not modelled is GitHub's live computation of `mergeStateStatus`, which no offline test
  can reproduce (brief: External dependencies — none, all `gh` stubbed).
