# Build notes — issue 650 / merge-mode-reads-head-from-its-own-remote (iteration 2)

Target: `eduralph/pdca-harness` @ `main` (`b5f5c29`), worktree
`/home/eddie/pdca/pdca-harness.pdca-wt-l0`. "main `X:N`" is a line on `b5f5c29`; a bare
`X:N` is the line after this patch in the worktree.

## What iteration 1 got wrong, and what changed because of it

The review's T5 finding (carry-forward block in `brief.md`): iteration 1's `_have`
refusal always ended with "the remote its branch was pushed to is not among them (or its
publish record does not name it)". That is a guess at the cause, and it is false whenever
the record's remote *was* fetched: a `new-pr` record (`origin` is always fetched), or the
reviewer's case, a `"stacked"` record whose remote `other` was fetched, but the
checkout's fetch refspec for `other` brings only `main`. The operator is sent to look for
a missing remote that isn't missing.

What I changed:

1. **The refusal now states only checked facts** (`merge.py:303-309`): the full head SHA,
   the checkout path, the remotes fetched, and then one of two things, chosen by what
   `integrate._published_ref(d)` returned:
   - it named a remote (always one of the fetched remotes, because `_remotes` adds it):
     "its publish record puts its branch at `<remote>/<branch>`, and fetching `<remote>`
     did not bring that commit in". Both halves are things the code checked.
   - it returned None: "its publish record does not say which remote its branch is on, so
     no other remote was fetched". Also checked: `_published_ref` returned None, and the
     fetch list is then exactly the base remote and `origin`.
   The possible causes (refspec leaves the branch out, the branch moved after the host
   read, the record names the wrong remote) are listed in the `_have` docstring
   (`merge.py:293-297`) for maintainers. They are not in the message, because nothing
   tells them apart at run time.
2. **"Not in the checkout" is now claimed only when git says so.** Iteration 1 ran
   `git cat-file -e <sha>^{commit}` and reported *any* non-zero exit as "not in the
   checkout". With the `^{commit}` peel git exits 128 for a missing commit and also for a
   wrong object type or a broken repo, so that claim was unverified too. I checked on the
   host's git 2.53.0:
   `git cat-file -e <missing sha>^{commit}` → 128 ("fatal: Not a valid object name");
   `git cat-file -e <missing sha>` → 1, silent; `git cat-file -e not-a-commit` → 128.
   So `_have` now runs `git cat-file -e <sha>` (no peel, `merge.py:298`). Exit 1 means
   missing. Any other non-zero goes to `_git_failed` (`merge.py:301-302`) and reads
   "git failed: `git cat-file -e …` … exited 128 (…)". A non-commit object that is present
   still reaches `_contains`, which reports it as a git failure, as on main.
3. **One value is passed instead of a remote list.** `_merge_one` reads
   `pub = integrate._published_ref(d)` once (`merge.py:481`) and passes it to `_base_read`
   (`:482`, `:534`) and `_wait_for_update` (`:498`). Those pass it on to `_fetch` and
   `_have`, and both derive the fetch list from `_remotes(cfg, pub)` (`:265-273`). The
   fetch and the message read the same source, so a message cannot name remotes other
   than the ones fetched.

Everything else from iteration 1 is unchanged in behaviour: the record's remote is fetched
on all three reads, a failed fetch of it is a refusal, and a record naming no remote
fetches exactly what main fetches.

## What changed, by file

`template/src/pdca_harness/merge.py`

- `:73-80`: a new module-docstring paragraph on #650. It is a separate paragraph, so no
  existing docstring line is rewrapped (iteration 1 rewrapped 15 lines of the #531
  paragraph).
- `:91`: `from . import integrate, merged, publish, state`. No import cycle. `integrate`
  imports `merged, publish` and `.config` at module level (main `integrate.py:59-60`,
  plus a lazy `worktree` import at `:239`). An AST walk of the package shows the only
  module importing `merge` is `flow` (main `flow.py:30`, which also imports `integrate`),
  and the module-level import closure of `integrate` (26 modules) contains neither
  `merge` nor `flow`. `import pdca_harness.merge, pdca_harness.flow` works in both
  orders. (A plain grep misses `flow.py:30`, because it is a multi-line import list.)
- `:265-273`: new `_remotes(cfg, pub)` returns `(base_remote, "origin", pub[0])`,
  deduplicated, in that order. For `new-pr`/`stacked-pr`, `pub[0]` is `"origin"`
  (main `integrate.py:158`), which is deduplicated away. For a record naming no remote it
  is None (main `integrate.py:151-152`, `:157`), so nothing is added. Both match main's
  `dict.fromkeys((cfg.base_remote, "origin"))` (main `merge.py:259`).
- `:276-284`: `_fetch(cfg, repo, pub)`. Same loop and same fail-closed `_git_failed` as
  main `merge.py:256-263`, now over `_remotes(cfg, pub)`.
- `:287-309`: new `_have(cfg, repo, pub, head)`, described above.
- `:322-352`: `_base_read(cfg, repo, pub, pr_url)` fetches with `pub` (`:337`) and calls
  `_have` once the base tip has resolved and before `_contains` (`:346-348`).
- `:355-384`: `_wait_for_update(cfg, repo, pub, pr_url, …)`. Each new head is fetched and
  checked with `_have` before `_contains` (`:376`). This is what makes the "behind" case
  work, because the `update-branch` merge commit exists only on `other`.
- `_merge_one` (`:478-482`, `:498`, `:534`): read `pub` once and pass it to the three
  reads. The signature is unchanged (main `merge.py:365`).

`template/tests/test_merge.py:824-825` (main `_Host._git`, `test_merge.py:808-832`): the
fake raises `AssertionError("unexpected git call")` on any git verb it does not know, and
every `MergeAgainstCurrentBase` read now calls `cat-file -e`. The 2 added lines answer it
with 0 if the commit is in the fake's fetched set `self.local`, else 1. I checked what
happens without them, in a scratch copy of the patched tree with only this hunk reverted
(`.cache/issue650-fakecheck`): `test_merge` `Ran 49 tests … FAILED (failures=70)`, which
is 14 distinct test methods (the rest are subtests), every one raising
"unexpected git call: ['cat-file', '-e', <sha>]". The brief requires every existing test
to pass, so this edit is needed. It sits inside `_Host._git`, away from #621's
rollup-wait code, so the fold with #621 conflicts only if #621 edits these exact lines.
(Iteration 1's notes said "30+ existing tests"; 14 methods / 70 entries is the measured
figure.)

`template/tests/test_merge_third_remote.py` (new; this is the brief's named file, and a
copy is in this bundle). It uses real git: bare `origin`, `upstream` and `other`, a seed
clone that writes and pushes commits, and a primary checkout with all three remotes and
nothing fetched, with `base_remote = "upstream"`. Only `gh` is scripted. Any other
non-git command, or a `gh` call the fake does not expect, raises, so no real `gh` can run.
Every `git` argv goes to the real `subprocess.run`, and every `git fetch` argv is recorded
in full. Each case calls `merge._merge_one(cfg, d, dry_run=False, method="merge",
fetched=set())`. `_wait_for_green` is patched to record the host's head when it is called,
then return "failing", or "green" in one case.

| Test | Criterion | Pre-fix (main) |
|---|---|---|
| `test_stacked_head_on_third_remote_reaches_rollup_wait` | (1) head only on `other` → wait reached; fetches `upstream, origin, other` | red |
| `test_stacked_head_behind_is_updated_on_third_remote_and_reaches_wait` | (1) behind; scripted update pushes a merge commit only to `other` → stdout "updated: head <it>", wait reached with it | red |
| `test_stacked_green_merges_pinned_to_the_head_on_third_remote` | (1) green → the read after the green fetches `other` again; `gh pr merge … --match-head-commit <head>` | red |
| `test_head_in_no_fetched_remote_is_named` | (2) head pushed nowhere → SHA, checkout, `upstream, origin, other`, "puts its branch at other/feat, and fetching other did not bring that commit in" | red |
| `test_record_remote_fetched_without_the_head_is_not_blamed_as_left_out` | carry-forward: `other` has the head (checked with `ls-remote`), but the checkout's `remote.other.fetch` brings only `main` → message says `other` was fetched; it does not say the record names no remote | red |
| `test_new_pr_head_not_on_origin_says_origin_was_fetched` | carry-forward: `new-pr` record, head only on `other` → fetches exactly `upstream, origin`; message says the record puts the branch at `origin/feat` and fetching `origin` did not bring it | red |
| `test_a_head_git_cannot_read_is_a_git_failure_not_a_missing_commit` | point 2 above: a head git cannot parse → "git failed: `git cat-file -e …`", not "not in the checkout" | red |
| `test_stacked_record_naming_no_remote_fetches_as_today_then_names_head` | (2b) both record shapes (no `branch`; `base` not ending `/feat`) → fetches exactly `upstream, origin`, then the "does not say which remote" refusal | red |
| `test_stacked_record_naming_no_remote_is_not_refused_up_front` | (2b) the same records with the head on `origin` → no refusal, wait reached | green (guard) |
| `test_new_pr_record_fetches_exactly_base_remote_then_origin` | (3) full fetch argv is `[fetch upstream, fetch origin]`; with `base_remote = "origin"` it is `[fetch origin]` once | green (guard) |

## Alternatives I ruled out

- **The carry-forward's other option, "none of these remotes has it".** It is false in the
  reviewer's own case: `git ls-remote other refs/heads/feat` returns the head, so `other`
  has it, and only the fetch did not bring it in. "Fetching X did not bring that commit in"
  is the claim the code actually checked.
- **Listing likely causes in the message**, e.g. "(a fetch refspec that leaves the branch
  out, or a branch that moved…)". Any such list is incomplete (it leaves out, for example,
  a record naming the wrong remote). An incomplete list in the message is the same kind
  of unchecked claim the review flagged. The list is in the docstring instead.
- **Fetching the record's branch with an explicit refspec** (`git fetch other
  +refs/heads/feat:refs/remotes/other/feat`), which would make a restricted refspec
  harmless. The review says "This does not require expanding scope to fetch arbitrary
  refspecs; refusing remains correct". Criterion (3) also pins the fetch argv. And it
  would change what every fetch does, not just the message.
- **Keeping iteration 1's `remotes` tuple and adding a second parameter** with the record's
  remote for the message. `_base_read` would then take
  `(cfg, repo, pr_url, remotes, pub)` and `_wait_for_update` would take both too: two
  values that must agree, threaded through three helpers. Passing `pub` alone
  (`_base_read(cfg, repo, pub, pr_url)`) and deriving the list where it is needed removes
  that coupling. The cost is calling the pure `_remotes` twice per read.
- **Re-parsing `publish.json` in `merge`.** Rejected, as the brief asks:
  `integrate._published_ref` is the one rule for where a record's branch lives.

## Refute-your-own-test (forced)

- **(a) Genuine red? Yes.** `engine/scripts/run-verify.sh` (the C4 gate, run with
  `PDCA_BUNDLE`/`PDCA_WORKTREE` set) reverts the `merge.py` hunks and keeps the tests.
  Final run, red leg: `test_merge_third_remote` `Ran 10 tests … FAILED (failures=9)`. 8
  test methods failed, one of them in both subtests, and all 9 entries are
  `AssertionError` (0 `ERROR:`, so no import or load failure). The failures are on
  behaviour, with the issue's own message, e.g. "git failed: `git merge-base
  --is-ancestor 8cd6b42933ba 170…` in …/repo exited 128 (fatal: Not a valid commit name
  …)". The refspec case fails earlier, on the fetch list (main never fetches `other`).
  The git-failure case fails because main reports `merge-base`, not `cat-file`. The 2
  "unchanged" guards stay green on main, by design. `test_merge.py` passes on both legs
  (49 OK): the `_Host` `cat-file` answer is simply unused on main. Green leg: `Ran 49 …
  OK` and `Ran 10 … OK`. Verdict: `PDCA-EVIDENCE: C4 PASS — red without the fix, green
  with it`. Afterwards `git diff` in the worktree was byte-identical to `patch.diff`,
  so the gate's restore trap put the production hunks back.
- **(b) Production path? Yes.** Every case calls the real `merge._merge_one`, which runs
  the real `integrate._published_ref`, `_remotes`, `_base_read`, `_fetch`, `_have`,
  `_contains` and `_wait_for_update`. Every git call is the real git binary on real
  repositories. Only `gh` (no network), `state.state`, `merged.is_merged`, `_sleep` and
  `_wait_for_green` (the stop point, #621's code, not touched here) are patched.
- **(c) Does the fixture contain the fault? Yes.** The head really exists only in the
  bare `other.git`. The primary checkout really has that remote and starts with nothing
  fetched. In the "behind" case the update's merge commit is really pushed only to
  `other`. In the refspec case `other` really holds the head (the test checks it with
  `git ls-remote`), and the checkout's real `remote.other.fetch` leaves it out. In
  case (2) the commit really is in no remote.

I also checked that the new tests reject iteration 1's code, not just main's. In a
scratch copy (`.cache/issue650-v1check`, git-ignored in the worktree) I applied
`iteration-v1/patch.diff` to main and ran the final test file against it (bounded with
`timeout 300`): `Ran 10 tests … FAILED (failures=6)`. Every failure is a message test:
(2), refspec, `new-pr`, both (2b) subtests, and the git-failure case. For the last one,
v1 printed "its head commit not-a-commit is not in the checkout … the remote its branch
was pushed to is not among them", which is both of the unchecked claims at once. The 4
behaviour tests passed against v1, as expected, because its fetching was right.

## Gates run

All gates were run with the instance's configured gate commands, from `pdca-pdca/`, with
`PDCA_BUNDLE` / `PDCA_WORKTREE` set and wrapped in `timeout`. All runs were on the final
patch.

- C4 `engine/scripts/run-verify.sh`: **PASS** (details under (a) above).
- T3 `engine/scripts/run-suite.sh`: root render/update suite `Ran 24 tests … OK`. Template
  driver suite `Ran 2379 tests … OK (skipped=2)`, which is 2369 existing + 10 new.
  Verdict: `PDCA-EVIDENCE: root suite OK, driver suite OK`. Log:
  `.cache/issue650-t3.log` in the worktree.
- C5 `engine/scripts/run-prod-path.py` (`PDCA_PROD_PACKAGE=pdca_harness`):
  `PDCA-EVIDENCE: 1 added driver-suite test(s) import the production package
  'pdca_harness'`.
- T2 (docs) not run: the patch touches no docs file.
- `patch.diff` applies cleanly (`git apply --check`) to a fresh `git archive b5f5c29`
  copy of `template/src` + `template/tests`. In the worktree, `git diff` is
  byte-identical to `patch.diff`. The new test file is staged intent-to-add (`git add
  -N`), so it shows up in `git diff`.

## Commit-readiness

The target has no formatter, linter or hook config: no `.pre-commit-config.yaml`,
`pyproject.toml` ruff/black section, `setup.cfg`, `tox.ini` or `.flake8`, and no
`core.hooksPath` or non-sample hooks in the common git dir. `CONTRIBUTING.md` asks only
for a DCO `Signed-off-by`, which belongs on the publish commit, not the patch.
`git diff --check` is clean. Every added line is at most 92 characters, the width
`merge.py` wraps to (some untouched lines in these files are longer, up to 99).

## Notes for the human

- Nothing was pushed, and no PR was opened or touched. No `gh` command was run.
- The worktree's ignored `.cache/` holds my scratch copies (`issue650-v1check/`,
  `issue650-fakecheck/`, `issue650-applycheck/`) and the gate logs (`issue650-c4.log`,
  `issue650-t3.log`). None of it shows up in `git diff`, and the harness owns cleanup.
