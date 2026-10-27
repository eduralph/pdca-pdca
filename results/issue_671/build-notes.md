# Build notes — issue 671 / cleanup-closes-a-duplicate-as-a-duplicate

Target: `eduralph/pdca-harness` main. Worktree HEAD `a6af7f3`, which has the brief's
`d6057eb` as an ancestor. Between the two, only `docs/07-crosscutting.md` changed among
the files I touch, and that just moved the cleanup table from `:860-871` to `:945-953`.
Line numbers below are on the patched worktree unless marked "pre-patch".

## What changed

- `template/src/pdca_harness/cleanup.py`
  - `:31-39` module docstring matrix: a new row for the duplicate close. The old
    close/no-fix row now says "not a duplicate".
  - `:58` `import re`.
  - `:103-114` `_pr_state(url, repo="")`: an optional `--repo`, so a bare PR number from
    `Close when: PR #M merged` is looked up in the tracker repo (the brief's citation note).
    Existing callers pass a URL and no repo, so they behave as before.
  - `:322-326` the three `Close when` forms plus the `Duplicate of` form, as regexes
    (case-insensitive, `#` optional).
  - `:329-365` `_close_condition(cond, repo)` returns a verdict (`met` / `wait` / `never` /
    `unknown`) plus a text. Only `met` can lead to a close. PR: MERGED→met, OPEN→wait,
    CLOSED→never, unreadable→unknown. Issue (`_issue_state`): OPEN→wait,
    CLOSED+COMPLETED→met, CLOSED with any other reason (NOT_PLANNED, DUPLICATE, blank)→never,
    unreadable→unknown. A value that matches no form→unknown.
  - `:368-422` `_duplicate_row(d, st, number, repo)`, modelled on `_split_parent_row`
    (pre-patch `cleanup.py:235-308`). It returns None when the bundle has neither a
    `Duplicate of` field nor a `duplicate` marker, so the old not-planned row still
    runs. Otherwise it returns a report-only row for cases (2)–(5) and the unknown cases,
    or, for case (1), a close row built as `_close_issue(..., reason="duplicate",
    fallback_body=body, prefer_bundle_comment=False)`. The body is the hand
    `tracker-comment.md` (if present), then "Closed as a duplicate of #N." and, for a
    non-`now` condition, which condition was met. This is the same body-building pattern
    as the split-parent row (pre-patch `:300-308`).
  - `:538-544` (pre-patch `:425`) the hook: inside `if _empty_patch(d):`, the duplicate row
    is tried first. It sits after the merged-PR and unreadable-PR checks, so a merged PR
    still wins.
- `template/templates/brief.md.tpl:97-102`: the two optional fields, right after
  `Disposition hint`. Each placeholder opens with `<` and wraps, so `brief.field` reads an
  unfilled one as absent (`brief.py` `_is_placeholder`). An unedited template copy
  therefore never turns a bundle into a duplicate.
- `docs/07-crosscutting.md:952-953`: a new table row for the duplicate class. The old row
  now says "not a duplicate" and "as `not planned`".
- `template/tests/test_cleanup.py:628-` `DuplicateClose(CleanupBase)`, 16 tests.

## Choices and what I ruled out

- **Keyed on the field OR the marker.** The brief requires this, because
  `likely-close — duplicate of #463` writes the marker `likely-close`. A wontfix bundle with
  no field keeps `not planned`. `test_wontfix_marker_without_a_target_still_closes_not_planned`
  and the existing `test_complete_close_disposition_closes_not_planned` cover that.
- **A strict `Duplicate of` match** (`^#?(\d+)$`). A value like `#463 — same root cause`
  is treated as "not an issue number" and reported, not closed. This follows "unknown never
  acts". A looser "leading number" parse would be a two-line change if the human prefers it.
- **Issue closed with a reason other than COMPLETED counts as "can no longer be met"**, not
  just NOT_PLANNED. The brief names NOT_PLANNED. A DUPLICATE- or blank-reason close is not
  "completed" either, and calling it a wait would leave the row waiting forever. It is
  report-only either way, so this cannot cause a wrong close.
- **No `--duplicate-of`**, as the brief says. The argv is `--reason duplicate --comment <body>`.
- `_close_issue` is unchanged. Its retry probe (do not repost a comment that is already there)
  applies to the new row for free.

## Test runs

- Green: `cd template && PYTHONPATH=src timeout 300 python3 -m unittest tests.test_cleanup`
  ran 53 tests, OK.
- Project runner `engine/scripts/run-suite.sh` (T3): `PDCA-EVIDENCE: root suite OK,
  driver suite OK` (2646 driver tests OK, 2 skipped).
- `engine/scripts/run-docs-check.sh` (T2): `docs lint clean, site render + link audit clean`.
- Formatter / commit hooks: the target configures none (no ruff/black/flake8 config, no
  `.pre-commit-config.yaml`; CI workflows are docs/render/triage only). I kept new lines
  ≤100 chars to match the file. The only longer line, `cleanup.py:560`, was already there.

## Self-refutation

- **(a) Genuine red? Yes.** I reverted only `cleanup.py` (`git checkout` of that file, test
  file kept) and re-ran: `FAILED (failures=15)`. All 15 new duplicate tests failed on
  assertions: case (1) got `not planned` with no `#41`, and cases (2)–(5) plus the unknown
  cases saw a close mutation. The 16th test (wontfix still closes `not planned`) passed both
  ways, as it should. With the fix re-applied: 53/53 OK. The saved production hunk used for
  the revert is `results/issue_671/.red-leg-prod.patch` (scratch; I moved it out of the
  worktree, not deleted it).
- **(b) Production path? Yes.** Every test calls the real `cleanup.run` →
  `_plan_bundle` → `_duplicate_row` → `_close_issue`. Only `subprocess.run` / `shutil.which`
  are patched, using the existing `CleanupBase` fake `gh` (`test_cleanup.py:49-116`). The
  assertions read the exact `gh issue close` argv that production builds.
- **(c) Fixture includes the fault? Yes.** The fixture is a real COMPLETE bundle (accepted
  §9, whitespace-only `patch.diff`, a `close-disposition` marker, brief fields) with an OPEN
  tracker issue. That is the exact shape cleanup wrongly closed before. The "not yet met"
  tests also flip the PR/issue state and re-run to show the same bundle then closes.

## Runtime note (not a blocker)

GitHub's `duplicate` close reason needs a `gh` that accepts `--reason duplicate`. The
brief records the local gh 2.102.0 as listing it. An older gh makes the close call fail,
which `_close_issue` reports as a failed row (`cleanup.py:221-224`). It never turns into a
wrong close. Not tested against live GitHub. The test fakes `gh`, as the brief plans.
