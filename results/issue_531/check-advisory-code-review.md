# Advisory code review — issue 531 (merge-mode stale base)

Lens: bugs the patch introduces, plus reuse / simplification / efficiency. Advisory only.
Line numbers are from the patched target at `$PDCA_TARGET`.

Overall: no correctness bug found on the main path. Ready → base read → `update-branch` →
poll until the update lands → bounded rollup wait with `spent` → re-read head and base →
pinned merge. Every new refusal goes through `_undo_ready`. The shared budget holds: in
`_wait_for_update` the sleeps never add up to more than `wait_secs`
(`template/src/pdca_harness/merge.py:331-337`), and `_wait_for_green` starts its count at
`spent` (`merge.py:204`). Gates C4 and T3 pass (gate-logs). The findings below are edge
cases and cleanups.

## Correctness / edge cases

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/merge.py:256-263`: `_fetch` only fetches
  `cfg.base_remote` and `origin`. A PR published by `publish._publish_stacked` is pushed to
  the brief's `Onto branch` remote (`template/src/pdca_harness/publish.py:484`,
  `git push <remote> HEAD:<branch>`), and that remote can be a third one. After
  `gh pr update-branch`, the new merge commit exists only on that remote. `_contains` then
  sees git exit 128 ("not a valid commit") and the run refuses with "git failed", which is
  misleading. This is fail-closed, so nothing merges wrongly, but such a PR can never merge
  in merge mode once it is behind. Either fetch the remote the publish record names, or
  make the message say that the head commit is not in the checkout. If `Onto branch` can't
  happen in merge mode, ignore this.
- `template/src/pdca_harness/merge.py:321-334`: when the head changes to a commit that still
  lacks `tip` (someone pushed to the PR during the update wait, or the update was replaced),
  the loop keeps polling and then refuses with "its update had not landed". That message is
  wrong for this case. The result is still fail-closed. Low priority: a separate message
  for "the head moved but still lacks the base tip" would save a human some confusion.
- `template/src/pdca_harness/merge.py:452-460`: after an update, the "pending"/"empty"
  refusal text still says "within {merge_wait_secs}s". Part of that budget went to the
  update wait (`spent=waited`, `merge.py:451`), so the rollup wait got less than that. This
  only affects the message, but the "raise merge_wait_secs" hint is the action the user
  needs, so it should say that the update wait used part of the budget.
- `template/pdca.toml.jinja` (the `merge_wait_secs` `0` bullet, unchanged by the patch):
  with `merge_wait_secs = 0`, a PR that is behind is now refused almost every time.
  `_wait_for_update` reads once (`merge.py:331`), and GitHub usually applies the update
  asynchronously. Even if it landed at once, the single rollup read of a brand-new head is
  `empty`. The new comment block says the update wait shares the budget, but the `0` line
  still reads as "the original immediate-refusal behaviour". It should also say that `0`
  means any wave member after the first gets refused. This is a docs gap, not a code bug.

## Reuse / simplification / efficiency

- `template/src/pdca_harness/merge.py:288-296` (`_base_read`): fetch, then
  `rev-parse --verify --quiet <ref>^{commit}`, is the same thing `publish._pinned_base`
  already does (`template/src/pdca_harness/publish.py:946-962`), including the
  "does not resolve after the fetch" failure. `_base_read` could call
  `publish._pinned_base(repo, cfg.base_remote, f"{cfg.base_remote}/{base}")` and fetch
  `origin` separately. The same goes for `_git` / `_git_failed` (`merge.py:246-253`), which
  repeat the "last stderr line" pattern of `publish._line_tip_refusal` / `_pinned_base`.
  This is optional; the module already calls `publish._checkout_path`, so the dependency
  exists.
- `template/src/pdca_harness/merge.py:355-362`: the new `_refuse` helper is used only by
  the new paths. The rollup refusal (`merge.py:461-469`) and the `gh pr merge` failure
  (`merge.py:493-500`, edited in this diff) still repeat the same print → `_undo_ready` →
  `return 1` sequence inline. They could call `_refuse` with their own `why` text. This is
  cosmetic; the separate refusal messages that existing tests check would need to stay.
- Efficiency: under `"all"`, each PR now runs `_base_read` twice. That is two `gh pr view`
  calls plus up to two `git fetch` calls each time (`merge.py:285-288`, `:476`), then more
  fetches for every new head seen in `_wait_for_update` (`merge.py:322`), then the existing
  post-merge fetch (`merge.py:502-506`). This is per PR, not in a hot loop, so it costs
  little. The second `_base_read` could skip the `origin` fetch, because it only needs the
  base tip, and the head is checked by SHA equality with a commit already fetched. Not
  worth a round on its own.

## Tests

- `template/tests/test_merge.py` (new `_Host` / `MergeAgainstCurrentBase`): the fake is
  stateful, keyed by distinct PR URLs, and drives the production `merge.merge_wave`. It
  covers brief cases (a), (b) (the push both after the green read and at merge time) and (c)
  (exact call log for `"required"`). It also covers the iteration-1 carry-forward cases:
  the update landing late, the update never landing, and a red updated head marked by a
  fake option instead of a hard-coded SHA. No weak or vacuous test found. One gap: no test
  hits the new `repo_spec` refusal (`merge.py:420-422`, "publish record names no repo").
  Publish always writes `repo` (`publish.py:421`, `:541`), so this is low risk.
- The C5 gate log only says "patch adds no new test file — nothing to assert". The tests
  were appended to an existing file, so that gate checked nothing here. By reading the
  code, the new tests import only `merge` and patch `subprocess.run` / `_sleep`, so they do
  exercise the production code.
