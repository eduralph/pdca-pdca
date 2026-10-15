# Build notes — issue 695 / run-catches-a-late-carried-rewrite-and-retries-the-fetch

Iteration 4. Base: the wave-3 worktree `/home/eddie/pdca/pdca-harness.pdca-wt` at `ec1a36e`
(`pdca-integrate: issue_694`; 693, 672, 673 and 694 folded in). "base `:N`" is a line on
`ec1a36e`; "post `:N`" is a line in the patched tree. The brief's citations were taken on
`d6057eb` and have moved; the ones below are re-checked on `ec1a36e`.

I started from round 3's `patch.diff` (`iteration-v3/`); it applied cleanly on `ec1a36e`.
The design of (a) and (b) is unchanged. This round changes only the wording of the "could
not check … by hand" line, plus two small items from round 3's advisory code review.

Round 3 → round 4, production and test only (numstat between the two patched trees):
`integrate.py` +22/−10, `flow.py` +11/−7, test +79/−17. `cli.py` and the docs are unchanged.

## What the carry-forward asked, and what I did

The finding: the "could not check … by hand" line put the raw `IntegrationError` text in
its `(…)`. That text was written for a fold that stopped, so it gave the wrong advice at
the end of a run: `_fetch` said "the fold cannot see the branches it merges", and
`_in_line` said "check that checkout, then re-run". Re-running is not the fix once the run
has pushed its line.

Round 3's real stderr (captured this round: round 3's production code under this round's
test, through the C4 runner; see "Mutations" below):

```
flow: could not check whether a branch this run folded onto its line was rewritten since (could not fetch origin in /tmp/tmpci7hi687/repo — the fold cannot see the branches it merges), so the line may carry commits no PR holds any more. Check by hand that each of these branches still contains the commit the line took from it: issue_A's origin/fix/A (a05754c35ff6).
flow: could not check whether a branch this run folded onto its line was rewritten since (could not tell whether issue_A's carried head 0372cd0ccc9c is already in origin/fix/A — `git merge-base --is-ancestor` exited 128 in /tmp/tmpctgbbzvc/repo; a git step failed (not an overlap): check that checkout, then re-run), so the line may carry commits no PR holds any more. Check by hand that each of these branches still contains the commit the line took from it: issue_A's origin/fix/A (0372cd0ccc9c).
```

**The fix: the error carries its short cause, and the end-of-run line prints only that.**

- `IntegrationError` (base `integrate.py:78-82`, post `:85-98`) gets a keyword-only
  `cause`: what failed, in a few words, without the step a fold's message tells the user
  to take. When a raiser gives none, `cause` is the whole message (post `:98`). Every
  existing raise passes one positional message, so none changes. I checked every
  constructor call in `integrate.py`, `gates.py` and `flow.py` with the AST (parse tree):
  22 `IntegrationError` calls with one argument (plus the 2 new ones with `cause=`), 7
  `IntegrationTreeError` and 2 `_LineBroken` with one, and 1 `_Conflict` with two, which
  its own `__init__` (post `:121`) takes before it calls `super().__init__(message)`;
  `gates.py:258` has one call with one argument. No test constructs it.
- The two raisers the end-of-run check can hit now name their cause:
  - `_fetch` (base `:1455-1457`, post `:1560-1562`): `cause = "could not fetch {remote}
    in {repo}"`. Its other raise, "checkout not found at {repo}" (post `:1550`), has no
    advice in it, so the default (the whole message) is already right.
  - `_in_line` (base `:1104-1107`, post `:1194-1197`): `cause = "`git merge-base
    --is-ancestor` exited {rc} in {wt}"`.
  Both messages stay **byte-identical** to base: each is now built as `cause` + the same
  surrounding words. Two guard tests pin that (below).
- `rewritten_carried` reads `exc.cause` instead of `str(exc)` in both of its `except`
  blocks (post `:788`, `:798`); its docstring says so (post `:771-773`).
- `flow._report_late_rewrites` (post `flow.py:2701-2733`) prints that cause in the `(…)`.
  With the wrong advice gone, the line only said "check by hand", with no step for a branch
  the check then finds rewritten. No rewrite line is printed in that case to supply one. So
  the line now ends with the same remedy the rewrite line gives (post `:2728-2731`).

This round's real stderr (captured through the C4 runner with a temporary
`self.fail("SAMPLE-STDERR\n" + self.err)` at the end of `_assert_unchecked`, since removed;
the remedy sentence was reworded once after this capture, final text in the next block):

```
flow: could not check whether a branch this run folded onto its line was rewritten since (could not fetch origin in /tmp/tmp6vjt_od_/repo), so the line may carry commits no PR holds any more. Check by hand that each of these branches still contains the commit the line took from it: issue_A's origin/fix/A (d89beecae606). …
flow: could not check whether a branch this run folded onto its line was rewritten since (`git merge-base --is-ancestor` exited 128 in /tmp/tmpoxbzk6z3/repo), so the line may carry commits no PR holds any more. Check by hand that each of these branches still contains the commit the line took from it: issue_A's origin/fix/A (619ccaaa4d87). …
```

Final remedy sentence (post `flow.py:2728-2731`), replacing the `…`:

```
Restore one that does not to that commit or a commit that contains it, or rebuild on that branch every PR this run cut from the line after it took that commit, before any of them merges.
```

It mirrors the rewrite line's remedy ("Restore origin/fix/A to … or a commit that contains
it; or rebuild those PRs on the rewritten branch before any of them merges"). The first
wording I captured put "before any of them merges" before the PRs it refers to, so I
reordered it.

## Alternatives I ruled out (with their cost)

1. **Strip the advice at the source**: make `_fetch` and `_in_line` raise only the short
   cause. About −4 lines, the smallest diff. But it changes the fold's own errors, where
   "check that checkout, then re-run" is the right advice: a fold that stopped can be
   re-run. That is outside this slice (criterion (5): nothing else changes). I ran this as
   a mutation: the two new guard tests go red (`test_a_fetch_that_keeps_failing_still_stops_the_fold`,
   `test_a_fold_stopped_by_a_git_failure_in_its_check_still_says_to_re_run`).
2. **Cut the message text in `rewritten_carried`** (e.g. `str(exc).split(" — ")[0]`).
   About 2 lines. But it depends on the wording of two messages in other functions, and
   one rule cannot serve both: `_in_line`'s cause sits in the middle of its message
   ("could not tell whether … — `git merge-base …` exited 128 in …; a git step failed …").
   It would break silently the next time either message is edited.
3. **A subclass with `cause`**, like `_Conflict.paths` (post `:115-123`). About 8 lines for
   the class, the same 3 raise-site changes, and then the reader needs
   `exc.cause if isinstance(exc, Sub) else str(exc)` in both `except` blocks (+2 lines), or
   must catch only the subclass, so any other `IntegrationError` would escape
   `_drive_and_act` after Act. More code than the base-class keyword for the same result.
4. **Have `rewritten_carried` write its own cause with no data from the error.** It cannot
   know which remote failed (`_fetch` loops over remotes, post `:1552`) or git's exit code,
   so it would have to copy `_fetch`'s loop, about 10 lines including the retry, and the
   two checks could drift apart.

What mine costs: in `integrate.py`, +9 lines in `IntegrationError` (5 of them docstring,
3 the `__init__`), +1 net line in `_fetch`, none net in `_in_line` (4 lines before and
after), 2 changed lines and +2 docstring lines in `rewritten_carried`.

## The two advisory items from round 3 I also took

- **No real sleep in the tests.** Every case that failed a fetch slept the real 1 s
  `_FETCH_RETRY_PAUSE`. Both `setUp`s now call `_no_retry_pause` (test `:77-81`), which
  patches it to 0 with `create=True`. `create=True` matters: the constant is added by the
  fix, so on the C4 red leg the attribute does not exist, and a plain `patch.object` would
  ERROR instead of FAIL. The red leg still shows 9 FAIL, 0 ERROR. The file now runs in
  about 1.7 s.
- **Duplicate filter.** `_report_late_rewrites` filtered `accepted` by `carried`, and
  `rewritten_carried` filters again (post `integrate.py:778`). The caller now passes
  `accepted` as is (post `flow.py:2718`).

I left the third advisory note (reuse) alone; it was praise, not a request.

## The whole change (for the human; the design of (a) and (b) is round 2's and round 3's)

### (a) End-of-run check for a late rewrite

- `integrate.py`:
  - `IntegrationError.cause` (post `:91-98`), as above.
  - `_carried_tips` (base `:681-718`, post `:697-736`): the judgment moved to
    `_carried_rewrite`; `attempts=2` on its fetch (base `:700`, post `:719`). It raises
    the same message as base.
  - `_carried_rewrite` (post `:739-752`): `tip == took` or `took` an ancestor of `tip`
    (`_in_line`) → None; otherwise the facts sentence. The one judgment both checks share.
  - `rewritten_carried` (post `:755-807`): groups carried bundles with a branch on record
    by target, as `fold` groups them; per target `_fetch(..., attempts=2)` in a `try`; per
    branch `_rev`, then `_carried_rewrite` in a `try`. A branch that no longer resolves is
    skipped (out of scope per the brief). Returns `(rewritten, unchecked)`, where
    `unchecked` holds each branch's ref and the error's `cause`. Never raises
    `IntegrationError`.
  - Module docstring (base `:39-45`, post `:45-51`).
- `flow.py` `_drive_and_act`:
  - `line_stopped` (post `:2491`), set at the fold-error break (base `:2642-2644`, post
    `:2651`) and the red re-gate break (base `:2656-2659`, post `:2667`). Criterion (2b).
  - After `_report_conflict_holds` (base `:2672`, post `:2681`), so after `_maybe_run_act`
    (base `:2664-2665`) as the brief asks: `late = _report_late_rewrites(...) if
    carried_heads and not line_stopped else {}` (post `:2688-2689`). `carried_heads` (base
    `:2408`) only gets entries from a stack-mode fold that pushed, so it is empty with
    publishing off, in merge mode and in a dry-run.
  - The result goes into 693's `holds` collector last (post `:2694-2697`), so it outranks a
    hold for the same id.
  - `_report_late_rewrites` (post `:2701-2733`), as above.
- `cli.py` (unchanged since round 3): `_FAILED_REASONS = {"rewritten", "unchecked"}` (post
  `:698`); `_results_rc` returns 1 for either before the hold rule (post `:730`). The
  `{id: state}` return types are unchanged. No second channel: it extends 693's collector
  (post `cli.py:642`).

### (b) Retry the carried-branch fetch once (unchanged since round 2)

`_fetch` (base `:1440-1457`, post `:1533-1562`) takes keyword-only `attempts: int = 1`;
each remote's fetch is tried up to `attempts` times with `_FETCH_RETRY_PAUSE = 1.0` s
between (post `:1530`). The default keeps every other caller as it was (`carry_view` base
`:232`, `_prepare_worktree`). `_carried_tips` and `rewritten_carried` pass 2.

**Why retry rather than "take the lock and retry"** (the brief left it to Do): the clash
is with another git process in the same checkout holding a ref lock. Our integration
lock (`integ_lock`) is a harness `flock` on a sidecar next to the integration worktree; no
foreign git process takes it, so holding it would not prevent the clash. Taking every
target's lock before the check (base `:485`) and then not re-taking it in the per-target
loop (base `:520-529`) is about 15-20 lines, and a second `flock` on a new file description
from the same process blocks on our own lock. The retry is a few lines in `_fetch` and one
keyword per caller.

### Docs

`docs/07-crosscutting.md` (base `:669-675`, post `:675-685`), unchanged since round 3.

## Test — `template/tests/test_integrate_carried_rewrite_late.py`

13 cases (round 3 had 12). The run cases go through `cli._flow` only, on the real-git
`StackFoldGit` fixture (`tests/test_integrate_stack_bases.py:123-254`), loaded by path and
used as a helper object, never subclassed. Only modules are imported.

Changed this round:

- `_assert_unchecked(iid, cause, not_named)` (test `:215-230`) now checks the line holds
  `({cause})` exactly (the short cause and nothing after it before the `)`), "Check by
  hand", `issue_X's origin/fix/X (<head>)`, and "Restore one that does not to that commit";
  and that it holds none of `_FOLD_ADVICE` (test `:68`): "re-run", "check that checkout",
  "the fold cannot see".
- Its callers pass the exact cause: `could not fetch origin in <checkout>` for the
  one-target case (test `:300-301`) and both two-target cases (test `:337`), and
  ``git merge-base --is-ancestor` exited 128 in <checkout>`` for the per-branch case
  (test `:383-385`).
- `test_a_fetch_that_keeps_failing_still_stops_the_fold` (test `:473-481`) now checks the
  fold's whole error, word for word, advice included.
- New: `test_a_fold_stopped_by_a_git_failure_in_its_check_still_says_to_re_run` (test
  `:483-510`): fix/A fast-forwarded, the `_git` spy makes `merge-base --is-ancestor <A's
  head>` exit 128 inside the fold's own check; the fold must raise `_in_line`'s whole
  message, word for word, and push nothing.
- `_no_retry_pause` in both `setUp`s (test `:77-81`, called at `:90` and `:432`).

| criterion | test (line) | fix reverted (C4 red leg) | round-3 production | with fix |
|---|---|---|---|---|
| (1) | `test_a_rewrite_while_the_last_wave_builds_is_reported_and_exits_1` (:234) | FAIL | pass | pass, rc 1 |
| (1b) | `test_a_late_rewrite_outranks_a_hold` (:246) | FAIL | pass | pass, rc 1 |
| (1c) | `test_a_rewrite_during_the_last_fold_is_reported_and_exits_1` (:258) | FAIL | pass | pass, rc 1 |
| unchecked, fetch | `test_an_end_of_run_check_that_cannot_fetch_is_named_and_exits_1` (:279) | FAIL | **FAIL (wording)** | pass, rc 1 |
| unchecked, fetch, 2 targets | `test_a_target_that_cannot_be_fetched_does_not_hide_a_rewrite_on_another` (:341) | FAIL | **FAIL (wording)** | pass, rc 1 |
| unchecked, fetch, 2 targets | `test_a_target_that_cannot_be_fetched_does_not_stop_the_check_of_the_next` (:346) | FAIL | **FAIL (wording)** | pass, rc 1 |
| unchecked, ancestry | `test_a_branch_that_cannot_be_judged_does_not_hide_a_rewrite_beside_it` (:351) | FAIL | **FAIL (wording)** | pass, rc 1 |
| (2) fast-forward | `test_a_fast_forward_of_a_carried_branch_reports_nothing` (:391) | pass | pass | pass, rc 0 |
| (2) merged + deleted | `test_a_carried_branch_merged_and_deleted_reports_nothing` (:399) | pass | pass | pass, rc 0 |
| (2b) | `test_a_rewrite_the_next_fold_stops_on_is_reported_once` (:413) | pass | pass | pass, 1 line, rc 1 |
| (3) | `test_one_failed_fetch_does_not_stop_the_fold` (:461) | FAIL "one failed fetch stopped the fold: could not fetch origin …" | pass | pass |
| (4) | `test_a_fetch_that_keeps_failing_still_stops_the_fold` (:473) | FAIL (1 attempt, not 2) | pass | pass |
| fold's own error unchanged | `test_a_fold_stopped_by_a_git_failure_in_its_check_still_says_to_re_run` (:483) | pass | pass | pass |

The (2), (2b) and last-row cases pass before the fix by design: they guard against a false
report, a double report, and a change to the fold's own error. They are not part of the
RED the brief names.

**Mutations, each through the C4 runner and reverted afterwards** (each time I then
compared `git diff` of the worktree with `patch.diff` byte for byte: identical):

| mutation | result |
|---|---|
| fix reverted (C4 red leg) | 9 FAIL, 0 ERROR, module loads |
| round 3's production hunks under this round's test | 4 FAIL, each `'(<cause>)' not found in "<round-3 line>"`: the round-3 stderr quoted above |
| advice stripped at the source (alternative 1: `_fetch` and `_in_line` raise only `cause`) | 2 FAIL: the two in-fold guard tests; the 4 unchecked cases still pass |

Round 3's mutations M1-M3 (per-target `try`, per-branch `try`, `continue` vs `break`) are
untouched by this round's change; the cases that pinned them are unchanged apart from the
cause they assert.

## Gates I ran, through the project's runners (`/home/eddie/pdca/pdca-pdca/engine/scripts/`, each under `timeout`)

- **C4** `run-verify.sh` on the final `patch.diff`: green leg `Ran 13 tests in 1.691s …
  OK`; red leg `Ran 13 tests … FAILED (failures=9)`; `PDCA-EVIDENCE: C4 PASS — red without
  the fix, green with it`.
- **T3** `run-suite.sh` on the final tree: root suite `Ran 24 tests … OK`; driver suite
  `Ran 2526 tests … OK (skipped=2)`; `PDCA-EVIDENCE: root suite OK, driver suite OK`.
  That covers criterion (5): every #633 test in `test_integrate_stack_bases.py`, all of
  `test_flow_same_wave_conflict.py`, and 693's `test_flow_hold_exit_code.py`.
- **T2** `run-docs-check.sh`: `lint_docs: OK`, `render_site: link audit OK`.
- **C5** `run-prod-path.py` (`PDCA_PROD_PACKAGE=pdca_harness`): `1 added driver-suite
  test(s) import the production package 'pdca_harness'`.

## Refuting my own test

- **(a) Genuine red? Yes.** With the production hunks reverted (C4 red leg), 9 cases FAIL
  on assertions, none ERROR, and the module loads: it imports no symbol the fix adds, and
  the one constant it patches is patched with `create=True`. (1), (1b), (1c) and the four
  unchecked cases find no line on stderr; (3) fails with the original symptom (`could not
  fetch origin in …/repo` from `_carried_tips` → `_fetch`); (4) sees one attempt, not two.
  This round's finding has its own red: the four unchecked cases fail on round 3's
  production code, on exactly the copied in-fold text.
- **(b) Production path? Yes.** The run cases call `cli._flow`, which runs the real
  `flow.flow_ids` → `_drive_and_act` → real `integrate.fold` (real git, a real bare origin,
  real pushes, a real second checkout) → `_report_late_rewrites` →
  `integrate.rewritten_carried` → the real `_fetch` / `_rev` / `_carried_rewrite` /
  `_in_line`, raising real `IntegrationError`s whose `cause` is printed → `cli._results_rc`.
  Only the leaves are stubbed, with the same stubs 693's merged test uses. The
  `integrate._git` spies pass every call to real git except the ones they fail on purpose.
  The fetch and guard cases call the real `integrate.fold`.
- **(c) Fixture includes the fault? Yes.** Each rewrite is a real force-push on the bare
  origin, asserted not to be a fast-forward. In the unchecked cases the failure is real at
  the point the code sees it: the spy fails the actual `git fetch` call (counted: exactly
  two attempts) or the actual `merge-base --is-ancestor` call for A's head (counted: once),
  and the cause printed names the real checkout path. In the new guard case, fix/A really
  moved forward, so the fold really asks git about ancestry.

## Commit-readiness

The target has no formatter config, no pre-commit config and no git hooks: `core.hooksPath`
unset, no non-sample hooks in the common git dir, and no `.pre-commit-config.yaml`,
`pyproject.toml`, `setup.cfg`, `ruff.toml` or `.flake8` at the root
(`template/pyproject.toml.jinja` is the template for generated projects, not the target's
own config). No linter is installed (`pyflakes`, `ruff` absent from the instance venv). Its
CI runs the docs lint and site render and the root suite; both are green above. Every
changed file parses. The longest added line is 96 columns (base max in `integrate.py` is
100). `git diff --check` is clean.

## Not addressed

- The 8 deferred findings in `deferred-findings.json`, held for the human at handover. One
  of them asks whether "unchecked" should exit 1 at all, or only warn. I kept exit 1 as
  rounds 1-3 did; that choice is the human's.

## Files I left behind (for the harness to reclaim)

Scratch logs, patches and two temporary index files for this round's runs are in
`/home/eddie/pdca/pdca-harness.pdca-wt/.cache/pdca-695-r4/`. Round 3's are in
`.cache/pdca-695-scratch/` if still there. `.cache/` is git-ignored by the target, so none
of it is in `git status` or `patch.diff`. I did not delete anything; cleanup is the
harness's. The test file is staged intent-to-add (`git add -N`) in the worktree, so `git
diff` shows it. The worktree otherwise equals `ec1a36e` + `patch.diff`.

No external dependency was missing: Python 3 and git were enough.
