# Build notes — issue 531 / merge-mode-stale-base-merge (iteration 2)

Target: `eduralph/pdca-harness` @ `main` (`c67a14d`), worktree `pdca-harness.pdca-wt-l0`.
Line numbers below are on the PATCHED tree unless marked "base".

## What the carry-forward asked, and what I did

1. **"Behind" is now decided in plain git, the `publish._line_tip_refusal` pattern (#593).**
   The GraphQL `baseRef { compare(headRef:) { behindBy } }` read (`_BEHIND_QUERY` /
   `_read_head`) is gone. `_base_read` (`template/src/pdca_harness/merge.py:276-300`):
   - head + base branch name from the host, one `gh pr view <url> --json
     headRefOid,baseRefName` (`_pr_head`, `merge.py:227-243`). The head has to be the
     host's: it is the SHA `--match-head-commit` is checked against.
   - fetch `base_remote`, then `origin` if different (`_fetch`, `merge.py:256-263`). Origin
     is where publish pushes every PR branch (`publish.py:319` base:
     `git push --force-with-lease -u origin branch`), so after an update the merge commit
     GitHub wrote is fetchable there; on an own-repo checkout it is one fetch.
   - record the base tip: `git rev-parse --verify --quiet <base_remote>/<base>^{commit}`
     (same form as `publish.py:713-714` base).
   - decide: `git merge-base --is-ancestor <tip> <head>` (`_contains`, `merge.py:266-273`):
     exit 0 up to date, exit 1 behind; any other exit, or a failed fetch, refuses with a
     message that starts `git failed:` and names the command, the checkout and git's last
     stderr line (`_git_failed`, `merge.py:250-253`). A commit the checkout lacks makes git
     exit 128, so it refuses through the same path, as the carry-forward's mapping says.
2. **The update is polled for, bounded by and charged to `merge_wait_secs`.**
   `_wait_for_update` (`merge.py:303-337`) re-reads the head right after
   `gh pr update-branch` returns, then every 5 s, until a head contains the RECORDED tip
   (it only fetches/checks a head it has not seen yet). Timeout or a failed read returns a
   reason and `_merge_one` refuses through `_refuse` (readiness undone). The time it took
   is passed to the rollup wait as `_wait_for_green(..., spent=waited)` (`merge.py:451`),
   so both waits share ONE bound (`merge.py:204`: `waited = spent`).
3. **Tests** (`template/tests/test_merge.py`):
   - update lands late: `test_update_that_lands_late_still_merges_pinned_to_the_updated_head`
     (`:1005`) — the fake reports B's old head for two reads after `update-branch`, then
     the merge commit; asserts the exact head sequence the driver saw
     (`[reviewed, reviewed, reviewed, updated, updated]`), that it slept in between, that
     every B rollup read described the updated head, and that the merge is pinned to it.
   - never lands: `test_update_that_never_lands_refuses_readiness_undone` (`:1026`) —
     refuses ("had not landed"), B never merged nor its rollup read, `gh pr ready --undo`,
     poll sleeps ≤ `merge_wait_secs`.
   - the hard-coded `"u2".ljust(40, "0")` red head is gone: `_Host.red_after_update`
     (a set of PR URLs) marks whatever head `update-branch` produces as red
     (`test_updated_head_that_is_not_green_is_not_merged`, `:1040`).

The overall sequence the sign-off accepted is unchanged: ready → behind read → update if
behind → bounded rollup wait on the new head → read head + base again → merge pinned to
that head; `merge_requires = "required"` untouched (test (c) pins its exact call log).

## Files

- `template/src/pdca_harness/merge.py` — module docstring paragraph (`:49-71`);
  `_wait_for_green` gains `spent` (`:172-173`, docstring `:178-182`, `:204`); new helpers
  `_pr_head`, `_git`, `_git_failed`, `_fetch`, `_contains`, `_base_read`,
  `_wait_for_update` (`:227-337`); `_refuse` (`:355-362`), module-level so the #413
  comment block stays directly above the `if` it explains (the v1 review's placement
  note); `_merge_one` gated section (`:413-487`); the merge command is printed as run, pin
  included (`:489`); the `gh pr merge` failure message now lists the pin and the strict
  case and no longer has the odd mid-sentence line break (`:493-498`).
- `template/tests/test_merge.py` — see Tests below.
- `template/pdca.toml.jinja` — `wave_mode = "merge"` (`:129-134`, added after line 128
  so the hunk stays clear of #591's stack paragraph at base `:117-123`), `merge_method`
  (`:137-138`), `merge_requires = "all"` (`:152-163`), `"required"` keeps the stale-base
  behaviour, both `strict` outcomes, "use all" (`:166-170`), `merge_wait_secs` covers the
  update poll (`:183-189`), `regate_between_waves` has NO effect in merge mode
  (`:196-198`).
- `template/docs/fork-discipline.md.jinja:57-73` — the required rewrite: the full
  sequence, "one budget for both waits", that an update commit already pushed stays on
  the PR branch (v1 review's last point), and the sign-off-coverage statement.
- `docs/07-crosscutting.md:686-696` — NOT in the brief's file list. Its merge bullet
  describes the sequence users see; without this it says nothing about the driver pushing
  merge commits onto PR branches. 9 added lines + 1 changed, merge bullet only. I first
  also added a sentence to its regate paragraph and took it back out: that paragraph sits
  in text the stack-mode issues may edit, and it already says "folded integration tip".
  Easy to drop at sign-off if unwanted.

## Decisions and what I ruled out

- **Base tip from git, not from the host.** `gh pr view --json baseRefOid` exists (gh
  2.102 lists it) and would save one `git rev-parse` per read (−1 call, +1 JSON field:
  same size). Ruled out on meaning, not cost: GitHub records a PR's base SHA on the PR and
  refreshes it on its own schedule; it is not documented as "the branch tip right now".
  The fetched `<base_remote>/<base>` is the branch tip, and it is what the carry-forward
  asked for ("plain git").
- **Fetch first, then record the tip.** The carry-forward wording is "record the base
  tip, fetch, decide". Recording from the ref right after the fetch gives the same SHA
  with no host/git skew between two reads; the recorded SHA is the one the poll then
  waits for (`merge.py:440`).
- **`spent=` instead of passing `merge_wait_secs - waited`.** The subtraction is the
  smaller diff (0 changed lines in `_wait_for_green`), but when the remainder is 0 with
  the wait enabled, `_wait_for_green` takes its `wait_secs <= 0` branch (base
  `merge.py:171`) and returns ONE unconfirmed read — a green would merge without the
  #582 confirm. Cost of the kwarg: 2 changed code lines + a 5-line docstring paragraph.
  The budget sweep test catches the subtraction (e.g. budget 10, lag 2: 0 s left).
- **The poll is a second loop, on purpose.** The brief says the RE-VERIFICATION must
  reuse `_wait_for_green` and not grow a second wait loop; it does (one call, `:451`). The
  update poll waits for something else (the head moving), and the carry-forward asked for
  it explicitly. It shares the budget and `_sleep`, so tests drive it at no wall-clock.
- **No `git cat-file -e` pre-checks** like `publish.py:712-714` base. There a missing tip
  has its own meaning ("no longer on the line"); here the carry-forward maps every exit
  other than 0/1 to "refuse, git failed". Saves 2 git calls per read.
- **Base moves during the rollup wait → refuse, not loop.** The re-run resumes and updates
  then. A loop (update → poll → wait again) needs its own stop rule and can chase a busy
  base; about 12 more lines in `_merge_one` plus a test. The criterion ("not behind at the
  last read before `gh pr merge`") holds by refusing. Unchanged from v1, not objected to.
- **Existing refusal blocks not routed through `_refuse`.** Optional per the v1 code
  review. They keep their specific advice text (rollup: "set merge_requires…/raise
  merge_wait_secs"; merge: the cause list); routing them would save ~6 lines and change
  nothing the invariant needs.
- **`config.py:367-386` (base) field comments not touched.** Outside the brief's list, and
  still true (the rollup is read after the ready-mark and before the merge); the
  user-facing text is `pdca.toml.jinja`, which is updated. Keeps the conflict surface to
  the brief's files.

## Tests (`template/tests/test_merge.py`)

Existing `MergeWave` cases: `_up_to_date` (`:72-82`) answers the new read as "up to date"
(head `HEAD`, base tip `BASE_TIP`), wired into `_gh` (`:85-99`) and the three hand-written
fakes. Five assertions that spelled the exact merge command or `gh pr` sequence now include
the two `gh pr view` reads and the pin — the brief allows exactly that. Two assertions
were tightened so the new pre-merge fetches cannot hide a regression:
`test_merges_then_fetches_base` (`:138`) now requires a fetch AFTER the merge;
`test_ready_failure_stops_before_merge` (`:219`) checks no `gh pr merge` of any shape.

`_Host` (`:723-883`): a stateful fake keyed by PR URL with a real commit graph. `main`
moves on every merge (a merge commit), `update-branch` makes a merge commit of the head and
`main` (lands after `lag[url]` `gh pr view` reads; `None` = never), `git fetch` copies only
what the host's refs reach, `git merge-base --is-ancestor` answers by graph reachability
and exits 128 for a commit the checkout lacks, `gh pr merge` merges stale heads unless
pinned to a stale SHA or `strict=True`. `MergeAgainstCurrentBase` (`:886`):

| test | covers |
|---|---|
| `test_second_member_is_updated_and_reverified_before_it_merges` | (a) |
| `test_update_is_a_merge_commit_whatever_the_merge_method` | never `--rebase`, any method |
| `test_head_changed_after_the_green_read_is_not_merged` | (b) push after the green |
| `test_pinned_merge_refused_when_the_head_moves_at_merge_time` | (b) pin refused |
| `test_merge_requires_required_call_log_is_unchanged` | (c) exact call log |
| `test_update_that_lands_late_still_merges_pinned_to_the_updated_head` | carry-forward 3 |
| `test_update_that_never_lands_refuses_readiness_undone` | carry-forward 3 |
| `test_updated_head_that_is_not_green_is_not_merged` | `red_after_update` |
| `test_update_that_fails_stops_the_wave_readiness_undone` | conflict on update |
| `test_first_member_behind_from_outside_the_run_is_updated` | first PR too |
| `test_strict_host_completes_a_multi_member_wave` | strict: wave completes |
| `test_base_that_moves_while_checks_are_read_is_not_merged` | "last read" clause |
| `test_failed_fetch_refuses_saying_git_failed` | fetch failure |
| `test_merge_base_failure_refuses_saying_git_failed` | exit other than 0/1 |
| `test_fork_checkout_reads_the_base_and_the_head_from_their_remotes` | `base_remote` ≠ origin |
| `test_update_poll_and_rollup_wait_share_one_budget` | 55-case sweep: total sleep ≤ budget; a merge only with ≥ 15 s left to confirm (or wait off) |

## Red → green (project runner)

`PDCA_BUNDLE=… PDCA_WORKTREE=… ./engine/scripts/run-verify.sh` from the pdca-pdca root
(the C4 gate's own `cmd`), on the final patch:

```
== C4 green leg: bundle test(s) with the fix applied: template/tests/test_merge.py
Ran 49 tests in 0.113s
OK
== C4 red leg: bundle test(s) with the production change reverted
Ran 49 tests in 0.112s
FAILED (failures=76)
PDCA-EVIDENCE: C4 PASS — red without the fix, green with it
```

The other configured gates, run the same way on the final patch:
- T2 `run-docs-check.sh`: `lint_docs: OK`, 22 pages rendered, `link audit OK`.
- T3 `run-suite.sh`: root suite (copier render + update-compat) 24 tests OK; template
  driver suite 2314 tests OK (2 skipped, the same skips as before).

After every run the worktree diff was byte-identical to `patch.diff`, and
`git apply -R --check patch.diff` is clean on `c67a14d`, so the patch applies to the base.
An earlier C4 run had 1 error instead of a failure on the red leg (my `runs.index(...)` in
`test_merges_then_fetches_base` raised `ValueError` before asserting); it now asserts
first, so all 76 are plain failures.

## Self-refutation

- **(a) Genuine red?** Yes. The C4 runner reverted the production hunks (`merge.py`, and
  `pdca.toml.jinja`, which its classifier counts as production) with the tests in place
  and ran the same 49 tests: 76 failures, 0 errors. The 76 are all 15 new behaviour tests
  (counting the 3 + 55 subtests) plus the 5 `MergeWave` assertions that encode the read
  and pin. Test (a) on the old code fails with the brief's repro call log verbatim:
  `ready A, checks A, sleep, checks A, merge A --merge, git fetch, ready B, checks B, sleep,
  checks B, merge B --merge` — B merged straight after A, no update. The strict-host test
  fails with the second merge refused ("Head branch is out of date") and rc 1. The only
  test green on both legs is (c), by design: it pins that `"required"` did not change.
- **(b) Production path?** Yes. Every test calls the real `merge.merge_wave` →
  `_merge_one` → `_base_read` / `_wait_for_update` / `_wait_for_green` / `_refuse` /
  `_undo_ready`. Patched: `subprocess.run` (the gh/git boundary), `merge._sleep`,
  `state.state`, `merged.is_merged` — the same boundary the existing suite patches. The
  tests import only `merge`, `state`, `Config`; no symbol the fix adds.
- **(c) Fixture includes the fault?** Yes. `_Host` actually moves `main` when A merges, so
  B's head really lacks the new tip and git (the fake's graph) says so; nothing tells the
  driver "behind" per call. The fake merges a stale head when asked (the `strict: false`
  danger), refuses it with `strict=True`, delays the update for the lag cases, pushes onto
  the PR or the base mid-sequence for (b) and the base-moved case. Both PRs are in the
  wave with distinct URLs.

## Not exercised here (supplementary only, per the brief)

Live GitHub: whether `gh pr update-branch` applies synchronously or later (the poll covers
both), the exact refusal text of a stale pin, and `strict` true/false behaviour on a real
repo. Suggested check on a scratch repo with merge rights: two independent PRs green
against `main`, `[driver] wave_mode = "merge"`, `merge_requires = "all"`, run one
non-final wave containing both. Expect A to merge, then for B: the log line
`head … lacks base commit …`, `→ gh pr update-branch`, `updated: head … contains …`, a new
CI run on B's merge commit, `check rollup green`, and
`→ gh pr merge <B> --merge --match-head-commit <sha>`. Repeat with "require branches to be
up to date" on (the wave should complete) and with a B that breaks only in combination
with A (B should stop, back in draft, the merge commit left on its branch). A `gh` without
`pr update-branch` fails the update, which refuses (fail-closed).

Two more live-only caveats, both fail-closed:
- `merge_method = "rebase"`: after an update the PR branch holds a merge commit of the
  base. I have not checked whether GitHub's rebase-merge accepts such a PR in every case.
  If it refuses, `gh pr merge` fails and the run stops with the PR back in draft. The
  brief fixed "update = merge commit whatever `merge_method` is", so I did not special-case
  it.
- If `gh` is authenticated with an Actions `GITHUB_TOKEN`, the update's push triggers no
  workflows (GitHub's rule for that token), so the updated head never gets a rollup and
  the wait refuses on EMPTY. A personal token or app token does trigger CI.

One residual risk I cannot test offline: `gh pr checks` reads the rollup of the PR's last
commit as GitHub's PR commit list reports it, while the head reads use `headRefOid`. If
right after an update the commit list lagged `headRefOid` by more than the 15 s confirm
interval, both green reads could be the old head's. The #582 confirm makes this unlikely,
and the brief rules out changing `_check_rollup` to return a SHA.

## Commit-readiness

The target has no formatter or commit-hook config (no `.pre-commit-config.yaml`, no
ruff/black config, no `core.hooksPath`, only sample hooks); its CI runs the docs lint,
the site render check and the copier render tests. `git diff --check` is clean; no line
over 100 characters in the touched Python; no `{{`/`{%` added to either `.jinja` file
(comment and prose text only).

## Process slip

My first C4 run wrote its log to `/tmp/claude-531-c4.log`, outside the worktree and the
bundle. Later runs piped their output instead. I did not delete the file (cleanup is the
harness's); it is a plain test log with nothing secret in it.
