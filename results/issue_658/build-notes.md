# Build notes — issue 658 / merge-mode-never-merges-an-onto-branch-pr

Target: `eduralph/pdca-harness` `main` @ `41210bc`, worktree `pdca-harness.pdca-wt-l0`.
Line numbers below are in the patched worktree unless marked "base".

## The change

`template/src/pdca_harness/merge.py`

- **Refusal, `merge.py:479-494`** (new block in `_merge_one`, right after the `pr_url`
  check at base `merge.py:465-468`). If `rec.get("mode") == "stacked"` (read the way
  `merged.merged_into` reads it, base `merged.py:104`), print a STOP message to stderr
  and `return 1`. It sits ABOVE the `dry_run` early return (now `merge.py:497`) and the
  `merged.is_merged` skip (now `merge.py:501`), as Scope's Placement requires, so the
  dry-run case (criterion 4) and the already-merged case (criterion 3) are refused too.
  The shape follows the `expected_checks_error` refusal (base `merge.py:477-485`): stderr,
  `return 1`, no `gh` call, so nothing needs undoing.
- **Message** names `d.name` (`issue_<id>`), the PR URL, says it is an `Onto branch`
  commit added to an existing PR that merge mode does not ready or merge, and gives the
  two ways forward: `[driver] wave_mode = "stack"` or take the bundle out of this
  merge-mode batch. It says the PR stays the human's to ready or merge, but that doing
  so does not let this merge-mode run continue (criterion 2: no "merge it by hand"
  suggestion, since criterion 3 refuses a merged `"stacked"` record anyway).
- **Comments updated** (Scope): module docstring (base `merge.py:76-83`, now
  `merge.py:76-91`) now says `_merge_one` refuses a `"stacked"` record before reading the
  head and that `_remotes` keeps the record-named remote for a caller passing such a
  `pub` directly; a new paragraph states the invariant. `_remotes` docstring (now
  `merge.py:307-317`) and the inline #650 comment (base `merge.py:521-523`, now
  `merge.py:547-550`) say the same. No code from #650 removed (out of scope).

`merge_wave` (`merge.py:119-128`, unchanged) already returns the first non-zero, so the
wave stops and `flow` prints its existing STOPPING line.

## Tests

- **New: `template/tests/test_merge_onto_branch.py`.** Imports only `merge`, `state`,
  `config` — no symbol the fix adds, so the file loads with the fix reverted. Drives
  `merge.merge_wave(cfg, [b], dry_run=…, method="merge")` with the exact record from the
  Success criterion, `subprocess.run` recorded by a stub that would otherwise answer
  every call successfully (green rollup, up-to-date head), so an un-refused record goes
  all the way to `gh pr merge`.
  - `:115` criterion (1)+(2): rc ≠ 0, no `gh pr …` call at all (covers ready, ready
    --undo, update-branch, merge), message content.
  - `:124` criterion (3): `is_merged` → True, still refused with the same message.
  - `:132` criterion (4): dry run → rc ≠ 0, no subprocess call, no `gh pr merge` in stdout.
  - `:141` a later `new-pr` member of the same wave is not touched once the stacked one
    stops it.
  - `:160` criterion (5): `"new-pr"` and mode-less records still go ready → merge pinned
    to the head.
- **Changed: `template/tests/test_merge_third_remote.py`** (Scope split).
  - (a) base `:156`, `:165`, `:189` (stacked reaches wait / update / green merge) are
    replaced by one case `:181` that, for both a failing and a green rollup verdict,
    asserts the up-front refusal: rc 1, no `gh` call, no fetch, no wait. base `:281`
    ("not refused up front") becomes `:275`, asserting the refusal for both no-remote
    records. Base `:165` (behind → update-branch on the third remote) is removed rather
    than ported: `_wait_for_update` is not reachable for a stacked record any more, and
    porting it would need a direct `_wait_for_update` call; the brief lists only
    `_remotes`/`_fetch`/`_have`/`_base_read` as the code to keep tested.
  - (b) base `:203`, `:216`, `:249`, `:266` now call `merge._base_read(cfg, repo, pub,
    PR)` through a new helper `_read` (`:159`) with `pub = integrate._published_ref(d)`
    for the record. Their refusal-text assertions are unchanged. The `gh pr ready
    --undo` assertion in base `:203` was dropped (no ready-mark on this path).
  - I also added `:192` `test_stacked_head_on_third_remote_is_read_there`: the positive
    half of base `:156` at the `_base_read` level (fetches upstream, origin, other; head
    found; not behind), so #650's "fetch the third remote" success path keeps a test, not
    only its failure paths.
  - `new-pr` cases (base `:235`, `:292`) untouched. `test_merge.py` untouched.
  - Module docstring updated to describe the split.

## Red → green (project runner)

- `engine/scripts/run-suite.sh` (T3) with the fix: `Ran 2427 tests … OK (skipped=2)`,
  root suite OK, driver suite OK.
- `engine/scripts/run-verify.sh` (C4) with `PDCA_BUNDLE=results/issue_658`:
  green leg 5/5 + 9/9 OK; red leg (production hunks reverted) 4 failures in
  `test_merge_onto_branch` (all stacked cases; the new-pr case passes as it should) and
  4 sub-test failures in `test_merge_third_remote` (the refusal cases: pre-fix the
  recorded calls include `gh pr ready https://gh/pr/650` and its `--undo`, and the
  green verdict returns 0). Result line: `PDCA-EVIDENCE: C4 PASS — red without the fix,
  green with it`.

## Self-refutation

- **(a) Genuine red?** Yes. C4's red leg reverted the `merge.py` hunks and kept the
  tests: `test_stacked_record_is_refused_before_any_gh_call`,
  `…_already_merged_is_still_refused`, `…_dry_run_prints_no_merge_plan`,
  `test_wave_stops_at_the_stacked_member` all failed (`AssertionError: 0 == 0` — pre-fix
  `merge_wave` returned 0, i.e. it readied and merged, or skipped as merged, or printed a
  merge plan). No load failure.
- **(b) Production path?** Yes. The tests call `merge.merge_wave` → `merge._merge_one`,
  the function changed. Only `subprocess.run`, `state.state`, `merged.is_merged` and
  `_sleep` are stubbed — the same seams `test_merge.py`'s `MergeWave` uses. The record is
  read by the real `publish._publish_record` from a real `publish.json` on disk. The
  third-remote file uses real git against three bare remotes.
- **(c) Fixture includes the fault?** Yes. The fixture IS the faulting record: a
  `publish.json` with `"mode": "stacked"`, `base: "other/feat"`, the exact one from the
  Success criterion, on a COMPLETE bundle with a non-empty patch. The `gh` stub answers
  everything successfully, so nothing other than the new refusal stops the merge.

## Considered and ruled out

- Refusing at publish time (the issue's other option): out of scope; the brief's
  self-test notes a `"stacked"` record already on disk would still reach `_merge_one`.
- Placing the refusal beside the `expected_checks_error` refusal: would sit after the
  dry-run return and the `is_merged` skip, failing criteria (3) and (4).
- Removing #650's third-remote fetch / `_have`: out of scope per the brief.

## Formatter / hooks

The target has no pre-commit config, ruff, flake8 or black settings (checked repo root,
`template/pyproject.toml.jinja`, `.github/workflows/`: only render/docs/issue
workflows). Changed lines are all ≤ 100 columns, matching the surrounding code, and
`git diff --check` is clean. No new imports left unused (`integrate` is used by
`_read`).

No external dependency beyond what the brief named. Nothing pushed, no PR opened.
