# Build notes — issue 625 (stack-mode live GitHub check tool), iteration 7

Target: eduralph/pdca-harness @ main (a6af7f3, still `origin/main`), worktree
`/home/eddie/pdca/pdca-harness.pdca-wt-l1`. Line numbers are on the patched files (all four are
new files or carry new sections), or on main @ a6af7f3 where they name `template/src/...` or
`docs/...`.

Started from `iteration-v6/patch.diff` (it applies cleanly to a6af7f3). Everything outside the
fix below is iteration 6's code, unchanged.

## What the carry-forward asked for

The 2026-10-25 live run (`~/pdca/live-runs/issue_625-20261025-213712/report.md`) gave E0, E1,
E2, E3, E4, E5 PASS and E1b INCOMPLETE. GitHub does not move an open PR's `baseRefOid` or file
list when the base advances with no push to the PR: Q's PR stayed on base 6215b88 with
`p.txt` + `q.txt` while the run base was at 7317e69, so iteration 6's rule ("both last reads
show `baseRefOid` = the run base tip") could never hold, and every run would end INCOMPLETE.
The fix asked for: for reads with no push to the PR (E1b and the recorded-only "B after A"
read), settle on "head unchanged + mergeability recomputed", not on `baseRefOid`; and record
the compare API's `base...head` file list next to the PR files. Expected live result after the
fix: E1b FAIL (the PR still lists P's file), to be filed as its own bug.

## The change

**Which reads follow the new rule** — `NO_PUSH`, `tools/live/stack_mode_live.py:113-119`:
`B_files_after_A_merge`, `B_files_before_update`, `Q_files_after_P_merge`. The judge and
`run` both pick the rule from this one table, by observation key; the judge does not trust a
rule name written into the file. I added `B_files_before_update` to the two the carry-forward
named: it is the same kind of read (C merged, no push to B), recorded only, and the live run
shows it stuck the same way (33 reads, 185 s, `synced: false`). Left on the old rule it would
burn the full 180 s window on every run and record a list that never settles. It changes no
verdict either way. Every other polled list (B opened, Q opened, B after Update branch) follows
a push or the PR's creation, and keeps iteration 6's rule; E1 passed live on it.

**What "mergeability recomputed" means in code** — `read_off`, `:1052-1083`, one function that
`run`'s stop rule (`_poll`, `:751-753`, `:760`) and the judge (`settled_files`, `:1118-1119`)
both call. For a no-push read, the read is on the expected commits when:

1. `headRefOid` equals the head the run pushed (`:1072-1073`) — "head unchanged";
2. `mergeable` is `MERGEABLE` (`:1074-1075`);
3. GitHub's test merge (`potentialMergeCommit`) has exactly the run base tip `run` just fetched
   and that head as parents (`:1076-1082`, compared as a set, so parent order does not matter).

Point 3 is what makes it "recomputed" rather than "computed at some point". GitHub makes the
test merge when it works out mergeability, as a merge of the head into the base branch as it
is now. A test merge on the new tip can only exist if GitHub worked the PR out again after the
merge. I rejected the looser rule, `mergeable != UNKNOWN` alone: a read taken just after the
merge can still return the answer GitHub cached before it, and nothing in such a read tells
the two apart. That is the same "stale read judged as fresh" fault iteration 6 fixed (reviewer
F1). The price of the stricter rule is that it relies on GitHub regenerating the test merge;
see the risk below.

**Reading the test merge's parents** — `PR_READ`, `:120-127`, and `Live._read_pr`,
`:766-790`, which runs `gh api graphql` (`:771-772`) with `baseRefOid headRefOid mergeable
potentialMergeCommit { oid parents(first: 2) { nodes { oid } } } files(first: 100) { nodes {
path } }`. `gh pr view --json potentialMergeCommit` would not do: gh 2.103.2 asks GitHub for
`potentialMergeCommit{oid}` only, no parents (checked offline: `strings` on the gh binary shows
that fragment, and `gh pr view 1 -R example/example --json nosuchfield` with a dummy token lists
the fields while parsing flags, before any network call). I did not query `mergeStateStatus`:
the gh binary carries the `merge-info-preview` media type, the API preview that field came
with, so it may still need that header, and a refused field would break every read.
`_read_pr` replaces iteration 6's `gh pr view --json files,baseRefOid,headRefOid` for all six
polled lists, so every read now also records `mergeable` and the test merge.

**The compare record** — `Live._compare`, `:792-812`: `gh api repos/<repo>/compare/<tip>...<head>`
(`:800`), once per poll after it stops, on the same two commits the poll expected; it records
the files, the merge base, `status`, `ahead_by` and `behind_by`, or what gh said. The judge shows
it beside the PR's own list (`seen["compare"]`, `:1102`) on E1, E1b and the four lists recorded
but not judged. It is not judged: E1b judges the list GitHub shows on the PR, as the docs' claim
is about the PR (`docs/07-crosscutting.md:655-658`).

**`run`** — `_poll` (`:728-764`) replaces `_files`. It takes the observation key (so it can
pick the rule), records into `obs[key]` and saves at once. Call sites `:886`, `:889`, `:892`,
`:896`, `:916`, `:918`. One deliberate behaviour change: iteration 6's `run` treated an empty
expected value as matching, so a poll could stop early when the base tip or pushed head could
not be read, and the judge then said INCOMPLETE. With one shared rule (`read_off` returns
"cannot be checked", `:1066-1067`), such a poll now waits the full `--settle-max` (180 s) for
the same INCOMPLETE. That happens only when `git rev-parse` of the just-fetched tip or the
`ls-remote` of the PR's head failed. I kept it, because one rule for both sides is easier to
check than two rules that agree in every case but one.

**`judge`** — `settled_files`, `:1086-1133`. Same steps as iteration 6 (the last two lists
agree; the expected commits are recorded; both last reads on them; `synced` true), with step 3
now `read_off` for the key's rule. A no-push list that fails step 3 says why per read
(`:1120-1124`), e.g. "read 3 of 3 shows its test merge on 222222222222 + ffffffffffff, not on
444444444444 + ffffffffffff, so GitHub may not have taken in the move of the base yet". `seen`
now also has `compare`, `settle rule` (`SETTLE_RULE`, `:1038-1045`) and `last read` (the last
read's `baseRefOid`, `headRefOid`, `mergeable` and test merge), so the report shows the stuck
base commit next to the list. The four lists recorded but not judged now carry a `not settled`
reason when they did not settle (`:1214-1216`); they still change no check.

**Docs** — tool docstring `:45-55` and `CONTRIBUTING.md:77-89` ("Reading the report") describe
both rules and the compare record. `AGENTS.md` and the STOP-exception text
(`CONTRIBUTING.md:91-94`) are unchanged.

## What the next live run should show

- **E1b FAIL**, not INCOMPLETE: Q's list `[p.txt, q.txt]`, `compare.files` `[q.txt]`, and
  `last read.baseRefOid` still the base from before P merged. That is the carry-forward's
  expected result: file it as its own bug against the plain-chain claim at
  `docs/07-crosscutting.md:655-658`.
- "B after A", "B before Update branch" and Q's list after P merged settle in about 15-20 s
  each instead of running out the 180 s window (181 s, 185 s and 181 s on 2026-10-25), so the
  run is about eight minutes shorter; each list has its compare list beside it.
- E0, E1, E2, E3, E4, E5 as before.

**Risk I could not remove offline.** The rule depends on GitHub regenerating the test merge of
an open **draft** PR against the new base tip after a merge with no push to the PR. Reasons to
expect it: open PRs turn "conflicting" or "out of date" when their base moves without a push to
them, which needs mergeability worked out against the current base; GitHub documents the test
merge as the commit it makes when it computes mergeability; and the sign-off notes say Q showed
mergeable "clean" after P merged. If GitHub does not do it, E1b ends INCOMPLETE again and the
report says so per read ("shows no test merge (potentialMergeCommit)" or "shows its test merge
on <old tip> + <head>"). That would be the rule meeting a GitHub behaviour, not a driver bug.

**The saved 2026-10-25 observations cannot close #625 with the new judge.** Re-judging them
(`judge --observations ~/pdca/live-runs/issue_625-20261025-213712/observations.json`, into a
scratch dir) gives E1b INCOMPLETE: "read 31 of 32 shows mergeable null, not MERGEABLE; … shows
no test merge (potentialMergeCommit)". That file has no mergeability data, so it cannot show
GitHub took P's merge in. A fresh live run is needed.

## Test changes (`tests/test_stack_mode_live_tool.py`)

- `_read` / `_reads` (`:75-103`): every read now carries `mergeable` and a test merge with its
  parents; `kept=` makes every read show the PR's `baseRefOid` GitHub kept (a no-push read);
  `merge_on=` puts the test merge on another tip; every polled record carries a `compare`.
- `_good()` (`:142-177`) is shaped like the live run: B after A, B before Update branch and Q
  after P keep the PR's old base commit, with the test merge on the new tip. B's and Q's judged
  lists open with one stale read (old head or old test merge) and end on two fresh ones.
- (1) `:220-238` also asserts E1b settled with Q's base commit kept, the compare list is shown,
  and the four recorded lists settled (B after A and B before Update branch with B's base
  commit kept).
- (6) `:272-286` is now the live shape: kept base, test merge on the new tip, PR list `[p, q]`,
  compare `[q]` → E1b FAIL, exit 1, with the compare list and the kept base in `observed`.
- (7) `:347-457`, the settle cases, now 11 shapes, each one check INCOMPLETE and exit 3, with a
  reason that names the cause:

| Shape | Check | Rule it holds |
|---|---|---|
| B: reads agree on the expected commits, `synced: false` | E1 | the flag (iteration 6) |
| B: read before the last on B's old head | E1 | both reads, not only the last (iteration 6) |
| B: `expect.baseRefOid` empty | E1 | expected commits recorded (iteration 6) |
| B after Update branch: both reads on B's old base commit, test merge on the tip, marked synced | E1 | pushed reads still need `baseRefOid` = tip; the no-push rule does not apply to them |
| Q: three identical reads, test merge still on the old tip, `synced: false` | E1b | test merge on the new tip |
| Q: `mergeable` UNKNOWN, no test merge | E1b | mergeability computed |
| Q: read before the last still has the old test merge | E1b | both reads, no-push rule |
| Q: head moved, test merge from before the push, marked synced | E1b | head unchanged |
| Q: test merge on the tip but made for another head | E1b | test merge parents are tip **and** head |
| Q: reads with no mergeability (a file from before this rule) | E1b | no proof, no settle |
| Q: reads agree, `synced: false` | E1b | the flag |

- New `test_a_list_recorded_not_judged_that_did_not_settle_changes_no_check` (`:459-471`): B
  after A as the live run recorded it (stuck base, no mergeability, out of time) → every check
  PASS, exit 0, and the report says "not settled" for it.

## Red → green

- **Red against the bug** (iteration 6's tool, extracted byte for byte from
  `iteration-v6/patch.diff`, with the final test), through the target's runner
  `python3 -m tests.run_root_suite tests.test_stack_mode_live_tool`: "Ran 22 tests … FAILED
  (failures=26)", 0 errors. Every judge case that uses `_good()` fails because iteration 6's
  judge returns E1b INCOMPLETE for the live-shaped Q reads, with the live report's reason
  ("read 2 of 3 shows baseRefOid 222222222222, not 444444444444"); test (6) gets INCOMPLETE
  where FAIL is right; the no-push INCOMPLETE cases fail on their reasons (iteration 6 names
  `baseRefOid`, not the test merge or mergeability). The one settle case that passes on both is
  "Q's head moved": both rules need the head unchanged (it goes red under the "head check
  dropped" mutation below). The guard / preflight / teardown cases pass on both.
- **Green** (with the fix): "Ran 22 tests … OK", "root suite OK: 22 executed, 0 skipped".
- **C4 gate**, the configured command (`./engine/scripts/run-verify.sh` with `PDCA_BUNDLE` /
  `PDCA_WORKTREE`, under `timeout 900`): green leg "Ran 22 tests … OK"; red leg (tool and doc
  hunks reverted) "Ran 22 tests … FAILED (failures=46)", no `_FailedTest`; last line
  `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`. The four files were
  byte-identical to their pre-gate hashes afterwards.
- **Mutation checks** (one rule broken at a time, module re-run, file restored and compared by
  hash): Q after P not in `NO_PUSH` → 26 red; B after A not in it → 2 red; B before Update
  branch not in it → 1 red; the no-push rule also applied to B after Update branch → 1 red; head
  check dropped → 1; mergeable check dropped → 2; test merge check dropped → 3; test merge needs
  only the tip → 1; `synced` ignored → 2; only the last read checked → 4; compare not shown → 2
  (as errors: the assertion's key lookup raises); "not settled" never written → 1 (an error, the
  same way); pushed rule ignores `baseRefOid` → 1. All 13 caught. (The "test merge needs only the
  tip" mutation survived my first case set; the "test merge made for another head" case was
  added for it.)
- **`run`'s polling code** is not reachable from the shipped test (the brief forbids importing
  the tool, and `run` is checked by the live run). As a scratch check, not shipped, I drove the
  real `Live._poll` / `_read_pr` / `_compare` against a fake `gh` on `PATH` that answers two
  "UNKNOWN, no test merge" reads and then fresh ones: the poll waited through the two, stopped
  on two fresh reads, recorded `synced: true` and the compare list, and `settled_files` accepted
  Q's `[p.txt, q.txt]` (so E1b would FAIL). The logged argv was the intended
  `gh api graphql -f query=… -f owner=eduralph -f name=pdca-stack-sandbox -F number=6`.
- **T2 docs gate** (`./engine/scripts/run-docs-check.sh`): "lint_docs: OK", "render_site: link
  audit OK".
- **T3 suites** (`./engine/scripts/run-suite.sh`, with copier, under `timeout 3000`): root
  suite "Ran 46 tests … OK" (iteration 6 had 45; the one new test method is the difference),
  offline driver suite "Ran 2630 tests … OK (skipped=2)", `PDCA-EVIDENCE: root suite OK, driver
  suite OK`. `template/` is not touched.
- C4, T2 and T3 were run a second time on the final tree, after a last wording edit (one code
  comment and the `CONTRIBUTING.md` paragraph), with the same results; `patch.diff` was
  regenerated from that tree.

## Refute-your-own-test answers

- **(a) Genuine red?** Yes. Against iteration 6's tool (the live bug), the judge returns E1b
  INCOMPLETE on the live-shaped observations and 26 sub-cases fail on their assertions; with the
  production hunks reverted (C4 red leg) all 22 methods fail (46 failures), as a test that ran
  and failed, not an import error (the test runs the tool by path through `subprocess`). The 13
  mutations show each new rule is held by a case, not only the file's existence.
- **(b) Production path?** Yes. Every judge case runs `tools/live/stack_mode_live.py judge` as a
  subprocess: the real `read_off`, `settled_files`, `judge`, `report_md`, `cmd_judge`. `run`
  stops on the same `read_off` (`:751-753`), so the offline cases also pin `run`'s stop rule.
  No copy of the rule is in the test.
- **(c) Fixture includes the fault?** Yes. The fixtures are the live run's shape: Q's PR on its
  old base commit after P merged, listing P's file, with the compare list showing only Q's.
  The fault cases are the reads that must not count: test merge still on the old tip,
  mergeability still UNKNOWN, a stale read before the last, a moved head, a test merge of
  another head, a file with no mergeability data (as the saved live file is), and pushed reads
  stuck on the old base.

## Success criterion → test

| Criterion | Test |
|---|---|
| (1) all match → exit 0, all PASS | `test_observations_matching_every_check_pass` :220 |
| (2) A no headRefOid → E2 FAIL with the observed value | `test_a_merged_pr_reporting_no_head_oid_fails_e2` :241 |
| (3) B after Update branch lists a.txt → E1 FAIL | `test_b_still_listing_a_file_of_a_after_update_branch_fails_e1` :250 |
| (4) S head on base → E4 FAIL | `test_a_squash_merge_whose_head_is_on_the_base_fails_e4` :257 |
| (5) base is the line or main → E0 FAIL | `test_a_pr_against_the_line_or_main_fails_e0` :264 |
| (6) Q lists p.txt → E1b FAIL | `test_q_listing_a_file_of_p_after_p_merged_fails_e1b` :276 (now the live shape) |
| (7) preconditions missing → INCOMPLETE, not FAIL | `test_missing_preconditions_are_incomplete_not_fail` :289 (7 shapes) and `test_a_file_list_not_seen_settled_on_the_expected_commits_is_incomplete` :355 (11 shapes) |
| (7b) run 2 non-zero / raised after its preconditions → E3 FAIL | `test_run_2_failing_after_its_preconditions_were_observed_fails_e3` :474 |
| (8) sandbox token reaches gh, not the ambient one; exit 0 | `test_preflight_passes_the_sandbox_token_to_gh_and_writes_nothing` :600 |
| (9) `private: false` → non-zero | `test_preflight_refuses_a_repo_that_is_not_private` :620 |
| (10) `--repo eduralph/pdca-harness` → non-zero, gh never called | `test_preflight_refuses_the_harness_repo_without_calling_gh` :628 |
| (11) missing / empty token file → non-zero, gh never called | `test_preflight_refuses_a_missing_or_empty_token_file_without_calling_gh` :636 |
| (12) squash / merge commits off → non-zero, naming the setting | `test_preflight_refuses_a_repo_without_squash_or_merge_commits` :649 |
| (13) setup / run / teardown + harness repo → non-zero, no gh | `test_writing_steps_refuse_the_harness_repo_without_calling_gh` :666 |
| (14) setup / run / teardown + missing token → non-zero, no gh | `test_writing_steps_refuse_a_missing_token_file_without_calling_gh` :675 |
| (15) teardown deletes exactly the recorded base + branches, closes the PR; no heads/main, repo delete or settings PATCH | `test_teardown_removes_the_runs_branches_and_pr_and_nothing_else` :721 |

Extra cases: the recorded-not-judged list that did not settle (:462, new); from earlier
iterations, E3's whole success line (:504), teardown's unrecorded branch under the run's prefix
(:739), `--keep` (:747), preflight's draft warning (:613).

## For the human at sign-off

1. **Hard sign-off condition (brief): the live run.** Nothing here touched GitHub. Run once,
   in a fresh work directory:

   ```bash
   cd ../pdca-harness   # the patched checkout
   python3 tools/live/stack_mode_live.py preflight
   W=$(mktemp -d)
   python3 tools/live/stack_mode_live.py setup    --workdir "$W"
   python3 tools/live/stack_mode_live.py run      --workdir "$W"
   python3 tools/live/stack_mode_live.py judge    --workdir "$W"
   cp "$W/report.md" <pdca-pdca>/results/issue_625/live-report.md
   python3 tools/live/stack_mode_live.py teardown --workdir "$W"
   ```

   `run` exits 3 if anything is INCOMPLETE; with E1b FAIL as expected, `run` exits 0 and `judge`
   exits 1. INCOMPLETE blocks accept; each FAIL is its own bug (E1b: the plain-chain claim at
   `docs/07-crosscutting.md:655-658`). If E1b is INCOMPLETE with "no test merge" or "test merge
   on <old tip>" on every read, see the risk above. The #625 closing comment must say the check
   used the persistent private sandbox with a fresh `live-<stamp>` base per run instead of a
   disposable repo.
2. **Second §6 item (brief): the STOP-exception wording**, `AGENTS.md:14-18` and
   `CONTRIBUTING.md:91-94`, unchanged in this iteration, to review and accept on its own. The
   carry-forward defers it and the scope items to this sign-off.

## Commit-readiness

The target configures no formatter, linter or commit hook: no `.pre-commit-config.yaml`,
`pyproject.toml`, `setup.cfg`, `tox.ini`, ruff or flake8 config at the root; no active hooks in
the common git dir and no `core.hooksPath`. Checked anyway: `git diff --check` clean with the
new files included; no added line over 100 characters; both Python files parse, have no unused
imports and no unread module-level names (an `ast` check; pyflakes and ruff are not installed);
every file ends with a newline. Patch: 136,727 bytes, 4 files (`AGENTS.md` +5,
`CONTRIBUTING.md` +56, the test +758, the tool +1592 lines). It applies cleanly to a6af7f3
(checked with `git apply --cached --check` against a6af7f3's tree in a scratch index, so the
worktree's own index was not touched). The bundle's copy of the test matches the patch. The DCO
`Signed-off-by` comes from publish's `git commit -s`.

Nothing was pushed and no PR was opened. Do did not run `setup`, `run` or `teardown`; the only
`gh` call was the local flag-parsing one above, with a dummy token. Scratch files (the
iteration 6 tool copy, the mutation script, the fake-gh smoke check, gate logs) are in the
worktree's git-ignored `.cache/issue625/` and are not part of the patch.
