# Build notes — issue 531 / merge-mode-stale-base-merge

Target: `eduralph/pdca-harness` @ `main` (`c67a14d`), worktree `pdca-harness.pdca-wt-l0`.
Line numbers below are on the patched tree.

## What changed

`template/src/pdca_harness/merge.py`

- Module docstring, new paragraph (`merge.py:49-67`): states the "against which base /
  which head" rule, the accepted gap (base moves after the last read), and that
  `merge_requires = "required"` is unchanged.
- `_BEHIND_QUERY` + `_read_head(pr_url)` (`merge.py:216-255`): two reads.
  `gh pr view <url> --json headRefOid` gives the head SHA; `gh api graphql` with
  `resource(url:) { ... on PullRequest { baseRef { compare(headRef: <sha>) { behindBy } } } }`
  gives how many commits of the base's current tip that exact head lacks. Any read it cannot
  parse returns `None` and the caller refuses (fail-closed).
- `_merge_one` (`merge.py:319-390`), only inside `if cfg.merge_requires != "required"`:
  - a local `refuse(why)` (`:319`) prints a STOP message and calls the existing
    `_undo_ready` (`:196` on base), so every new refusal undoes readiness the same way the
    existing ones do;
  - after the ready-mark: `_read_head` (`:333`); if behind, `gh pr update-branch <url>`
    with no `--rebase` (`:339`), then read again and refuse if still behind (`:346-351`);
  - the existing `_wait_for_green` call is reused unchanged (one wait loop, not two) — it
    now runs on the updated head when there was an update;
  - after the green read: `_read_head` again (`:380`); refuse if the head changed
    (the green rollup can't be attributed to it) or the base moved during the wait;
  - `cmd += ["--match-head-commit", head]` (`:390`) pins the merge. The existing
    merge-refusal path (message + `_undo_ready`) handles a host refusing the pin; its
    message now lists that cause.
- `_check_rollup` return shape untouched, as the brief required.

Docs:
- `template/pdca.toml.jinja` — `wave_mode = "merge"` paragraph (recommends `strict`),
  `merge_method` (governs only the final merge; update is always a merge commit),
  `merge_requires = "all"` (describes the new sequence), `merge_requires = "required"`
  (says plainly it keeps the stale-base behaviour, both `strict` outcomes, use `"all"`),
  `merge_wait_secs` (also bounds the post-update wait), `regate_between_waves` (now says it
  has NO effect in merge mode — the old "in merge mode the PR's own CI is the merge-boundary
  check" claim was the one the brief called out).
- `template/docs/fork-discipline.md.jinja:51-66` — the new sequence
  ready → behind read → update if behind → bounded wait → head re-read → pinned merge, and
  the required statement that after an update sign-off covered `patch.diff`, not the
  merged combination, which is verified by the PR's own CI.
- `docs/07-crosscutting.md` (~`:686-700`) — not listed in the brief, but it repeated the
  now-incomplete "read … immediately before merging" claim and the regate text, so I
  updated it with the same facts to keep the docs from contradicting each other. Two small
  hunks; easy to drop at sign-off if unwanted.

## Why `gh api graphql` compare and not `mergeStateStatus`

The brief suggested `gh pr view --json mergeStateStatus,headRefOid` as one option. I did
not use `mergeStateStatus == BEHIND` because GitHub reports `BEHIND` only when branch
protection requires up-to-date branches (`strict`). On a `strict: false` host — exactly the
dangerous case where a stale PR silently merges — it reads `CLEAN`/`UNSTABLE`, so the
behind check would never fire there. That would make correctness hinge on the host's
`strict` setting, which the brief's invariant rules out. The GraphQL `Ref.compare` is the
same comparison `gh pr update-branch` itself does to decide "already up to date", and it
is computed for the exact SHA we then pin to. `resource(url:)` avoids parsing owner/repo
out of the PR URL (the old fixture URL `https://gh/pr/1` would not even parse).

Cost: four extra `gh` calls per PR in the common no-update case (2 reads × 2 calls), six
plus the update when behind. Each is one small API call.

## What I ruled out

- **Looping update → wait when the base moves during the wait.** Refusing instead (the
  run resumes on re-run and updates then). A loop needs its own bound and can spin against
  a busy base; the brief asks for fail-closed, and a refusal costs one re-run. ~10 more lines
  for the loop plus a bound knob; not worth it for this slice.
- **Skipping the head read after the wait and relying on the pin alone.** The pin only
  guards "head changed after the last read"; it says nothing about whether the head the
  green rollup described is the one being pinned. `gh pr checks` does not report which
  head it read, so bracketing the wait with two head reads is what ties the green to a SHA.
- **Adding the update to `merge_requires = "required"`.** Out of scope per the brief: an
  update there would be followed by a merge on pending checks. Test (c) pins the call log.
- **Changing the fixture's default `pr_url`.** Not needed; the new class uses distinct
  realistic URLs (`PR_A`, `PR_B`) and the old fixture stays as is.

## Tests (`template/tests/test_merge.py`)

Existing `MergeWave` tests: the stub `_gh` and the three hand-written fakes now answer the
two new reads with "up to date, head `HEAD`" via `_up_to_date` (`test_merge.py:60-84`).
Assertions that listed the exact merge command or exact `gh pr` sequence were updated to
include the two `gh pr view` reads and the `--match-head-commit HEAD` pin — the brief
allows exactly that ("apart from the added behind/head read and the pin"). Red, pending,
empty, unreadable and dry-run tests are unchanged and pass.

New `_Host` stateful fake (`test_merge.py:718`) keyed by PR URL: the base is a merge
counter, each head SHA records how many base commits it contains, `update-branch` mints a
new head containing the current base, `merge` lands unconditionally (models `strict: false`,
the case where a stale merge goes through silently) unless pinned to a SHA that is no
longer the head. New class `MergeAgainstCurrentBase` (`test_merge.py:788`):

- (a) `test_second_member_is_updated_and_reverified_before_it_merges` — B behind only
  after A merges; asserts update (no `--rebase`) after A's merge, every rollup read of B
  happens between update and merge and describes the updated head, merge pinned to it.
- (b) `test_head_changed_after_the_green_read_is_not_merged` — push after the confirming
  green read; no merge, readiness undone.
- (b) `test_pinned_merge_refused_when_the_head_moves_at_merge_time` — push races the merge
  after the last read; the host refuses the pin; STOP, readiness undone.
- `test_update_that_fails_stops_the_wave_readiness_undone` — conflict on update.
- `test_updated_head_that_is_not_green_is_not_merged` — the combination is red.
- `test_first_member_behind_from_outside_the_run_is_updated` — the first PR is held to the
  same rule.
- (c) `test_merge_requires_required_call_log_is_unchanged` — exact call log
  `ready A, merge A, git fetch, ready B, merge B`. Green both pre- and post-fix by design.

## Red → green (project runner)

`PDCA_BUNDLE=… PDCA_WORKTREE=… ./engine/scripts/run-verify.sh` (the C4 gate):
`PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`. Green leg: 40 tests OK.
Red leg (production hunks reverted): 11 failures — all six new behaviour tests above plus
the five updated `MergeWave` assertions that expect the head read / pin. Worktree diff
identical to `patch.diff` after the run.

## Self-refutation

- **(a) Genuine red?** Yes. The C4 runner reverted the `merge.py` hunks and re-ran:
  `test_second_member_is_updated_and_reverified_before_it_merges` failed (B merged
  unpinned straight after A, no update), as did both (b) tests (unpinned merge went
  through), the update-failure, red-combination and first-member tests.
- **(b) Production path?** Yes. Every test calls the real `merge.merge_wave` →
  `_merge_one` → `_read_head` / `_wait_for_green` / `_undo_ready`. Only `subprocess.run`
  (the `gh` boundary), `merge._sleep`, `state.state` and `merged.is_merged` are patched,
  the same boundary the existing suite uses.
- **(c) Fixture includes the fault?** Yes. `_Host` actually moves the base when A merges,
  so B really is behind at the time of its merge; it merges a stale head if asked
  (unpinned, like `strict: false`), and actually changes the head mid-sequence for (b).
  Nothing is curated out: both PRs are in the wave, and the fake decides "behind" from its
  own state, not from a flag the test sets per call.

## Not exercised here (supplementary only, per brief)

The live host: a real `gh pr update-branch`, the GraphQL `compare` against real GitHub,
and `--match-head-commit` refusal on real `strict` true/false repos. The fake models the
documented behaviour; a human can confirm on a scratch repo with two independent PRs in
one merge-mode wave (`[driver] wave_mode = "merge"`), once with "require branches to be up
to date" on and once off: expect the second PR to show a "Merge branch 'main' into …"
commit, a fresh CI run, and then a merge. `gh pr update-branch` needs gh ≥ 2.42; an older
gh makes the update fail, which refuses (fail-closed).

## Commit-readiness

No formatter or pre-commit hook is configured in the target (no `.pre-commit-config.yaml`,
no ruff/black config; CI runs docs lint + render checks). Ran
`docs/publishing/tools/lint_docs.py` → `lint_docs: OK`. No line over 100 chars in the
touched Python files. No `{{`/`{%` added to the `.jinja` files.
