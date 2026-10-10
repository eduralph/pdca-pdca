# Build notes — issue 650 / merge-mode-reads-head-from-its-own-remote

Target: `eduralph/pdca-harness` @ `main` (`b5f5c29`), worktree
`/home/eddie/pdca/pdca-harness.pdca-wt-l0`. Line numbers below are post-patch in that
worktree unless marked "main".

## What changed

`template/src/pdca_harness/merge.py`

- `:86` — import `integrate` so merge mode reads the publish record the way the fold does.
  No cycle: `integrate` imports only `merged, publish` and `.config` (main
  `integrate.py:59-60`), plus a lazy `worktree` import; nothing in that set imports `merge`.
- `:260-267` new `_remotes(cfg, d)` — `(base_remote, "origin", <record's remote>)`,
  deduplicated, in that order. The record's remote comes from
  `integrate._published_ref(d)[0]` (main `integrate.py:139-158`), reused rather than
  re-parsing `publish.json`, as the brief asks. For a `new-pr`/`stacked-pr` record it returns
  `"origin"` (deduped away), and for a `"stacked"` record that names no remote it returns
  None (nothing added). So both cases fetch exactly what main fetches (main `merge.py:259`).
- `:270-277` `_fetch(repo, remotes)` — same loop and same fail-closed `_git_failed` refusal
  as main `merge.py:256-263`. It now takes the remote list instead of building it. A failed
  fetch of the record's remote is a refusal, like the other fetches.
- `:280-289` new `_have(repo, head, remotes)` — `git cat-file -e <head>^{commit}`. If the
  commit is missing, the refusal names the full head SHA, the checkout, and the remotes
  fetched ("its head commit <sha> is not in the checkout <repo> after fetching upstream,
  origin, other — …"). It no longer falls through to `_contains` and its bare "exited 128".
- `_base_read` (`:302-331`): takes `remotes`, fetches them (`:316`), checks `_have` after
  the base tip resolves (`:325`) and before `_contains`.
- `_wait_for_update` (`:334-…`): takes `(repo, remotes, …)` instead of `(cfg, repo, …)`
  (`cfg` was only used for `_fetch`). Each new head is fetched and checked with `_have`
  before `_contains` (`:355`). This is what makes the "behind" case work: the
  `update-branch` merge commit exists only on `other`.
- `_merge_one`: computes `remotes = _remotes(cfg, d)` once (`:459`) and passes it to all
  three reads (`:460`, `:476`, `:512`). Its signature is unchanged (`merge.py:365` on main).
- Module docstring (`:58-61`) gains two sentences on the extra fetch and the named refusal.
  I rewrapped the rest of that paragraph to keep lines ≤ 92 characters.

`template/tests/test_merge.py:824-825` — the `_Host` fake (main `test_merge.py:808-832`)
raises `AssertionError("unexpected git call")` on any git verb it doesn't know. Every
`MergeAgainstCurrentBase` test now hits `cat-file`, so without this 2-line answer (present
iff the commit is in the fake's fetched set `self.local`) 30+ existing tests fail. The brief
requires "every existing test_merge.py test still passes", so this edit is needed. Fold risk
with #621 (which adds tests to `test_merge.py`): this is a 2-line hunk inside `_Host._git`,
nowhere near the rollup-wait code. It only conflicts if 621 edits those same lines.

`template/tests/test_merge_third_remote.py` (new, the brief's named file; a copy sits in this
bundle). It uses real git: bare `origin`/`upstream`/`other`, a seed clone that authors and
pushes commits, and a primary checkout with all three remotes and nothing fetched.
`base_remote = "upstream"`. Only `gh` is scripted. Every `git` argv goes to the real
`subprocess.run`, and `git fetch` argvs are recorded. Everything goes through
`merge._merge_one(cfg, d, dry_run=False, method="merge", fetched=set())`.
`_wait_for_green` is patched to record the head it was reached with and return "failing",
so the run stops there.

- (1a) stacked record `{"mode":"stacked","branch":"feat","base":"other/feat"}`, head pushed
  only to `other` → no "git failed", rollup wait reached with that head, `other` fetched.
- (1b) same record, base moved so the head is behind. The scripted `gh pr update-branch`
  merges `upstream/main` into `feat` and pushes it only to `other` → the wait is reached
  with that new merge commit.
- (2) head pushed nowhere → rc 1, message names the SHA, "not in the checkout",
  "upstream, origin, other"; no "git failed".
- (2b) two stacked records that name no remote (no `branch`; `base` not ending in
  `/feat`) → fetches exactly `["upstream", "origin"]`, then the (2) refusal. No up-front
  refusal.
- (3) `new-pr` record, head on `origin` → fetches exactly `["upstream", "origin"]` and
  reaches the wait. This guards unchanged behaviour, so it passes before and after the fix.

## Alternatives I ruled out

- **Probe the head with `git rev-parse --verify <sha>^{commit}` instead of `cat-file -e`.**
  This would also need no fake change for the real-git test. But `_Host` answers any
  `rev-parse` it can't parse as `<remote>/main` with exit 1. That would make the
  `git_breaks` test (`test_merge_base_failure_refuses_saying_git_failed`) report "missing
  head" instead of "git failed", which is wrong for that fake, so the fake would need an edit
  either way. `cat-file -e` is the plain existence check, so I used it.
- **Probe only after `_contains` returns None.** Same fake edit either way (the `git_breaks`
  test reaches the probe). The brief's invariant is "before merge mode judges … the checkout
  holds every commit", so I check before judging. The cost is one extra local git call per
  read.
- **Re-parse `publish.json` in `merge`.** Rejected per the brief: `_published_ref` is the
  single rule for "where a record's branch lives". A second parser could drift from it.
- **Keep `_fetch(cfg, repo)` and add an `extra=` kwarg.** That also works. I passed the full
  list instead, so `_have`'s message names exactly what was fetched, from the same tuple.

## Refute-your-own-test (forced)

- **(a) Genuine red? Yes.** `engine/scripts/run-verify.sh` (the C4 gate) reverted the
  `merge.py` hunks and kept the tests: `Ran 5 tests … FAILED (failures=5)`. The failures
  were (1a), (1b), (2), and both (2b) subtests. Each failed on `assertNotIn("git failed",
  err)` with the exact message from the issue: "git failed: `git merge-base --is-ancestor
  8e2ed781de1c d18328dadfa0` in …/repo exited 128 (fatal: Not a valid commit name …)".
  (3) stays green pre-fix by design: it is the "unchanged" guard. With the fix: `Ran 5 tests
  … OK`. The verify script ended with `PDCA-EVIDENCE: C4 PASS — red without the fix, green
  with it`.
- **(b) Production path? Yes.** The test calls the real `merge._merge_one`, which calls the
  real `_remotes` → `integrate._published_ref`, `_base_read`, `_fetch`, `_have`,
  `_contains`, and `_wait_for_update`. Every git call is the real git binary on real
  repositories. Only `gh` (no network), `state.state`, `_sleep`, and `_wait_for_green` (the
  stop point, the #621 code outside this fix) are patched.
- **(c) Fixture includes the fault? Yes.** The head commit really exists only in the third
  bare repo `other.git`. The primary checkout really has that remote and has fetched
  nothing. In (1b), the update's merge commit is really pushed only to `other`. The
  unreachable-head case (2) is a real commit that no remote has.

## Gates run

- C4 `engine/scripts/run-verify.sh`: PASS (above).
- T3 `engine/scripts/run-suite.sh`: root render/update suite `Ran 24 … OK`; template
  suite `Ran 2374 … OK (skipped=2)`. An earlier run, before the `_Host` fix, showed the
  `test_merge` failures plus `test_render_then_slice`, which runs the rendered suite. Both
  are green now.
- Commit-readiness: the target has no pre-commit config, formatter or linter config (no
  `.pre-commit-config.yaml`, no hooks in the worktree's hooks dir, no ruff/flake8 in
  `.github/workflows`). I checked `git diff --check` (clean) and kept every new or changed
  line ≤ 92 characters. Some untouched lines in these files were already longer.

## Note for the human

The guard hook blocked one of my shell commands because a Python heredoc contained the
literal text "gh pr update-branch" inside backticks. I made those docstring edits with the
Edit tool instead. No `gh` command was run, and nothing was pushed.
