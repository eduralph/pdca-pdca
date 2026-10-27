# Build notes — issue 695 / run-catches-a-late-carried-rewrite-and-retries-the-fetch

Iteration 3. Base: the wave-3 worktree `/home/eddie/pdca/pdca-harness.pdca-wt` at `ec1a36e`
(`pdca-integrate: issue_694`; 693, 672, 673 and 694 folded in). "base `:N`" is a line on
`ec1a36e`; "post `:N`" is a line in the patched tree. The brief's citations were taken on
`d6057eb` and have moved; the ones below are re-checked on `ec1a36e`.

I started from round 2's `patch.diff` (the carry-forward points at `iteration-v2/`); it
applied cleanly on `ec1a36e`. The design for (a) and (b) is round 2's. This round changes
only how the end-of-run check handles a failure, plus tests for it.

## What the carry-forward asked, and what I did

The round-2 finding: with carried bundles on more than one (repo, base) target, round 2's
`_carried_tips(..., rewritten=found)` filled `found` target by target. If a later target's
fetch or ancestry check (`_in_line`) then raised, the error escaped `rewritten_carried`,
and `_report_late_rewrites` dropped every rewrite already found: it printed only the
generic "could not check … by hand" line, listing every carried bundle. Exit code was still
1, but a rewrite the check had actually found was not reported as one.

I confirmed that on round 2's code before changing anything (the new tests below, run
through the C4 runner with round 2's production hunks swapped in). Round 2's stderr in the
two-target case, verbatim:

```
flow: could not check whether a branch this run folded onto its line was rewritten since (could not fetch origin in /tmp/tmplnn0m0uv/zrepo — the fold cannot see the branches it merges), so the line may carry commits no PR holds any more. Check by hand that each branch this run folded still contains the commit the line took from it (issue_A: c36c008c74a7; issue_Z: b5d74bcb5bd9).
```

A's rewrite is gone, and A is listed for a by-hand check though the check had judged it.

**The fix: every carried branch gets its own verdict.** The end-of-run check now runs its
own loop (`integrate.rewritten_carried`, post `integrate.py:746-796`): one fetch per target,
inside a `try`; then one judgment per branch, inside a `try`. Each carried branch ends up
in exactly one of three places:

- clean — nothing printed;
- `rewritten[name] = report` — the facts and the remedy (post `:789-795`);
- `unchecked[name] = (ref, why)` — every branch of a target whose checkout is missing or
  whose fetch failed twice (post `:774-778`), or one branch whose ancestry check failed
  (post `:784-788`).

A failure never stops the loop (`continue`, post `:778`, `:788`), so later targets and
branches are still checked, and nothing already found is dropped. The function no longer
raises `IntegrationError` (docstring, post `:764`).

`flow._report_late_rewrites` (post `flow.py:2701-2729`) prints one line per rewrite
first, then one "could not check" line per distinct cause, naming only the branches that
cause left unchecked, each as `issue_X's origin/fix/X (<commit the line took>)`. Before,
that line named bundles and commits only ("issue_A: c18b3f624117"). Now it names the branch
to check too. Rewritten branches map to `"rewritten"`, unchecked ones to `"unchecked"`
(post `:2728-2729`), as in round 2, so the exit code path is unchanged.

To share the judgment between the fold's check and the end-of-run check without making the
fold's check two-mode, I pulled it into `_carried_rewrite` (post `integrate.py:730-743`):
"is `took` still `tip` or an ancestor of it? — if not, the facts sentence". `_carried_tips`
(post `:688-727`) is back to one job, raising on the first rewrite. Its message is the
same text as base `:708-717`: `facts` ends "…does this." and the raise adds " Only commits
that extend…". Its only behaviour change from base is still the `attempts=2` fetch (post
`:710`). Round 2's `rewritten=` switch on `_carried_tips` is gone.

### Real stderr, this round (captured through the C4 runner; see "How I captured it")

Two targets, the second one's fetch failing (`test_a_target_that_cannot_be_fetched_does_not_hide_a_rewrite_on_another`), exit 1:

```
flow: issue_A's branch origin/fix/A was rewritten after this run folded it onto pdca-integration/main-rf6eb8414fc3b: it is now at 16e9c428a7d5, which does not contain 8cb6d7e1ed5c, the commit the line took from it. A re-publish (`pdca publish` force-pushes), a force-push or "Update with rebase" does this. No fold of this run ran after the rewrite, so pdca-integration/main-rf6eb8414fc3b still carries the old commits, and so does every PR this run cut from pdca-integration/main-rf6eb8414fc3b after it took 8cb6d7e1ed5c: they hold commits origin/fix/A no longer has. Restore origin/fix/A to 8cb6d7e1ed5c or a commit that contains it; or rebuild those PRs on the rewritten branch before any of them merges.
flow: could not check whether a branch this run folded onto its line was rewritten since (could not fetch origin in /tmp/tmpv1gmttxl/zrepo — the fold cannot see the branches it merges), so the line may carry commits no PR holds any more. Check by hand that each of these branches still contains the commit the line took from it: issue_Z's origin/fix/Z (eac46b653849).
```

One target, one branch's ancestry check failing next to a rewritten one
(`test_a_branch_that_cannot_be_judged_does_not_hide_a_rewrite_beside_it`), exit 1:

```
flow: issue_Y's branch origin/fix/Y was rewritten after this run folded it onto pdca-integration/main-r793750f6d0af: it is now at 51c0047d1946, which does not contain 3fa3568b7ffa, the commit the line took from it. A re-publish (`pdca publish` force-pushes), a force-push or "Update with rebase" does this. No fold of this run ran after the rewrite, so pdca-integration/main-r793750f6d0af still carries the old commits, and so does every PR this run cut from pdca-integration/main-r793750f6d0af after it took 3fa3568b7ffa: they hold commits origin/fix/Y no longer has. Restore origin/fix/Y to 3fa3568b7ffa or a commit that contains it; or rebuild those PRs on the rewritten branch before any of them merges.
flow: could not check whether a branch this run folded onto its line was rewritten since (could not tell whether issue_A's carried head d39223623507 is already in origin/fix/A — `git merge-base --is-ancestor` exited 128 in /tmp/tmpw6ac341f/repo; a git step failed (not an overlap): check that checkout, then re-run), so the line may carry commits no PR holds any more. Check by hand that each of these branches still contains the commit the line took from it: issue_A's origin/fix/A (d39223623507).
```

How I captured it: I added a temporary `self.fail(self.err)` at the end of those two tests,
ran them through `engine/scripts/run-verify.sh` (the runner prints output only for
failing tests), then removed the two lines and checked the worktree against `patch.diff`
byte for byte (identical).

## Alternatives I ruled out (with their cost)

The carry-forward offered two fixes. Both are smaller than mine, and each leaves a case
broken that a test below now pins.

1. **Catch per target, still through round 2's `_carried_tips(rewritten=found)`.** Sketch,
   about +6 lines over round 2 in `rewritten_carried`:

   ```python
   for target, mine in sorted(groups.items()):
       try:
           _carried_tips(cfg, {target: mine}, refs, carried, batch, rewritten=found)
       except IntegrationError as exc:
           unchecked.update({d.name: str(exc) for d in mine if d.name not in found})
   ```

   This fixes the two-target case. But inside one target, an ancestry-check failure on one
   branch still stops that target's loop. The branches after it are never judged, so a
   rewrite among them is listed only as "unchecked". Branches judged clean before the
   failure are listed for a by-hand check too. `test_a_branch_that_cannot_be_judged_does_not_hide_a_rewrite_beside_it`
   fails for it: Y's rewrite comes after A's failure. It also keeps `_carried_tips` two-mode.

2. **Print what `found` holds, then mark the rest "unchecked".** About +4 lines in
   `_report_late_rewrites`. But the check still stops at the first failure, so every target
   after the failing one is never fetched or judged, and a rewrite there is never found.
   `test_a_target_that_cannot_be_fetched_does_not_stop_the_check_of_the_next` (the
   failing target sorts first) fails for it. "The rest" also includes branches already
   judged clean.

3. **One loop, two-mode `_carried_tips`** (collect `rewritten` and `unchecked` inside the
   fold's own check). That avoids repeating the loop shape, but puts two `if collector is
   None: raise` branches (about +12 lines) into the function every in-run fold calls. I
   kept the fold's check one-mode instead.

**What mine costs.** `rewritten_carried` repeats about 6 lines of the loop shape
`_carried_tips` has: the per-target fetch, the line name, the per-branch `_rev`. The
judgment and its wording are shared (`_carried_rewrite`), and so is the fetch with its
retry (`_fetch(..., attempts=2)`), so the two checks cannot judge differently. Net size
against round 2 (numstat): `integrate.py` 70+/10- → 109+/16-, `flow.py` 46+/1- → 52+/1-,
`cli.py` 15+/3- → 16+/3- (comments only), docs 10+/1- → 11+/1-, test 333 → 452 lines.

## The whole change (for the human; the design of (a) and (b) is round 2's)

### (a) End-of-run check for a late rewrite

- `integrate.py`:
  - `_carried_tips` (base `:681-718`, post `:688-727`): the judgment moved to
    `_carried_rewrite`; `attempts=2` on its fetch (post `:710`); docstring says so (post
    `:694-697`). Raises the same message as base.
  - New `_carried_rewrite` (post `:730-743`): `tip == took` or `took` an ancestor of `tip`
    (`_in_line`, base `:1097-1108`) → None; else the facts sentence.
  - New `rewritten_carried` (post `:746-796`): groups carried bundles with a branch on
    record by target, read via `_fold_candidates` (base `:201-209`) as `fold` groups them
    (base `:476-478`); per target `_fetch(..., attempts=2)`; per branch `_rev`, then
    `_carried_rewrite`. A branch that no longer resolves is skipped (left alone, as the brief
    scopes it). Returns `(rewritten, unchecked)`.
  - Module docstring (base `:45`, post `:45-51`): a rewrite after the last fold is reported at
    the end of the run, with each branch the check could not judge, and the run exits 1;
    both checks' fetch is tried twice.
- `flow.py` `_drive_and_act`:
  - `line_stopped = False` before the wave loop (post `:2489-2491`; base loop `:2485`), set
    at the two breaks the brief names: fold error (base `:2642-2644`, post `:2651`) and red
    re-gate (base `:2656-2659`, post `:2667`). Criterion (2b).
  - After `_report_conflict_holds` (base `:2672`, post `:2681`), so after `_maybe_run_act`
    (base `:2663-2665`) as the brief asks: `late = _report_late_rewrites(...) if
    carried_heads and not line_stopped else {}` (post `:2682-2689`). Round 2 also tested
    `do_publish`, merge mode and the stub publisher here. I dropped those three because
    `carried_heads` (base `:2408`) only gets entries from a stack-mode fold that pushed:
    `integrate.fold` fills `carried` after the push (base `:675-676`), and a dry-run
    `continue`s before that (base `:498-513`). Publishing off or merge mode never call the
    fold with it (base `:2603-2638`). The comment at post `:2684-2687` says this.
  - The result goes into 693's `holds` collector last (post `:2694-2697`), so it outranks a
    hold for the same id.
  - `_report_late_rewrites` (post `:2701-2729`), as described above.
  - `holds` paragraph of the docstring (base `:2370-2375`, post `:2375-2379`).
- `cli.py`: `_FAILED_REASONS = {"rewritten", "unchecked"}` (post `:695-698`); `_results_rc`
  returns 1 for either before the hold rule (post `:730-731`; base `:717-719`); docstring
  rule 1 (post `:705-709`); the `holds` comment in `_flow_claimed` (post `:638-641`). The
  `{id: state}` return types of `flow_ids` / `flow_batch` / `_drive_and_act` are unchanged.
  No second channel: it extends 693's collector (base `cli.py:640`, passed at `:650`,
  `:667`).

### (b) Retry the carried-branch fetch once

- `integrate._fetch` (base `:1440-1457`, post `:1522-1550`): keyword-only `attempts: int =
  1`. Each remote's fetch is tried up to `attempts` times, with `_FETCH_RETRY_PAUSE = 1.0` s
  between (post `:1518-1519`, loop post `:1543-1550`). The default of 1 keeps every other
  caller as it was (`carry_view` base `:232`, `_prepare_worktree` base `:1465`). The
  docstring now names both callers that pass 2 (post `:1532-1537`).
- `_carried_tips` and `rewritten_carried` pass `attempts=2` (post `:710`, `:775`).

**Why retry, not "take the lock and retry"** (the brief left it to Do; unchanged from round
2). The clash is with *another git process in the same checkout* holding a ref lock (an
operator's `git fetch`, a concurrent `pdca publish`). Our integration lock (`integ_lock`,
base `:263-297`) is a harness `flock` on a sidecar next to the *integration worktree*. No
foreign git process takes it, so holding it around the fetch would not prevent the clash at
all. It would also cost more: `_carried_tips` runs at base `:485`, before the per-target
loop takes each lock at base `:520-529`. Taking the locks for the fetch means entering every
target's lock, in sorted order, before `:485` (about 6 lines), then reworking `:520-529` so
the loop does not take the same lock again: a second `open()` + `flock(LOCK_EX)` from the
same process on a new file description blocks on our own lock. That is about 10-15 more
lines, and the end-of-run check would need its own copy. The retry is 6 changed lines in
the `_fetch` loop, a 2-line constant, `import time` and one keyword per call site, and it
is the step that actually helps against a held `*.lock`. The 1 s pause is a judgment call:
long enough for a typical ref update to finish, and it only ever runs after a failure.

### Docs

`docs/07-crosscutting.md` (base `:669-675`, post `:675-685`): after "the next fold stops the
run", a rewrite after the last fold is reported at the end of the run (exit 1); a branch that
check cannot judge is named with its commit for a by-hand check, the run exits 1 as well,
and the other branches are still checked; a branch deleted by then is not judged; both
checks' fetch is tried twice, a second apart.

## Test — `template/tests/test_integrate_carried_rewrite_late.py`

12 cases (round 2 had 9). The run cases go through `cli._flow` only, on the real-git
`StackFoldGit` fixture (`tests/test_integrate_stack_bases.py:123-254`), loaded by path and
used as a helper object, never subclassed. Only modules are imported.

New this round:

- `_a_rewrite_and_a_target_that_cannot_be_fetched` (test `:282-313`), run twice:
  - `test_a_target_that_cannot_be_fetched_does_not_hide_a_rewrite_on_another` (`:315`): the
    failing target sorts after the rewritten one (`org/repo` < `org/zrepo`), which is the
    finding's exact case.
  - `test_a_target_that_cannot_be_fetched_does_not_stop_the_check_of_the_next` (`:320`):
    the failing target sorts first (`org/arepo`), so the check must go on past it.

  Setup: a second checkout of the same bare origin is registered as another repo's checkout
  (`_second_checkout`, `:105-115`). Z targets it on base `zbase`, so it folds onto a line of
  its own (the same base name on a shared origin would clobber A's line). Waves: {A, Z}
  then {B on A}. While B builds, fix/A is force-pushed with a rewrite and the
  `integrate._git` spy starts failing every fetch in Z's checkout (matched by resolved
  path). Asserts: all COMPLETE; Z's head really is on the zbase line (Z was carried); one
  rewrite line for A with its head and "Restore origin/fix/A"; one "could not check" line
  naming `issue_Z's origin/fix/Z`, Z's head, "could not fetch", "by hand", and not
  `issue_A`; exit 1; exactly two failed fetches (Z's fetch, tried twice).
- `test_a_branch_that_cannot_be_judged_does_not_hide_a_rewrite_beside_it` (`:325`): one
  target, waves {A, Y} then {B on A}. While B builds, fix/A gets a fast-forward commit (so
  the check must ask git), fix/Y is rewritten, and the spy makes `merge-base --is-ancestor
  <A's head> …` exit 128. A is judged first. Asserts: one rewrite line for Y, none for A;
  one "could not check" line naming `issue_A's origin/fix/A`, A's head, "exited 128", and
  not `issue_Y`; exit 1; the spy fired exactly once.
- Updated: `test_an_end_of_run_check_that_cannot_fetch_is_named_and_exits_1` (`:255`) now
  asserts the branch is named (`issue_A's origin/fix/A`), through the shared
  `_assert_unchecked` (`:198-207`); `_rewrite(iid)` and `_assert_reported(iid)` take a
  bundle id; `_plan` takes a `target`.

| criterion | test (line) | fix reverted (C4 red leg) | round-2 code | with fix |
|---|---|---|---|---|
| (1) | `test_a_rewrite_while_the_last_wave_builds_is_reported_and_exits_1` (:210) | FAIL | pass | pass, rc 1 |
| (1b) | `test_a_late_rewrite_outranks_a_hold` (:222) | FAIL | pass | pass, rc 1 |
| (1c) | `test_a_rewrite_during_the_last_fold_is_reported_and_exits_1` (:234) | FAIL | pass | pass, rc 1 |
| unchecked, one target | `test_an_end_of_run_check_that_cannot_fetch_is_named_and_exits_1` (:255) | FAIL | FAIL (wording only) | pass, rc 1 |
| round-2 finding | `test_a_target_that_cannot_be_fetched_does_not_hide_a_rewrite_on_another` (:315) | FAIL | **FAIL `0 != 1`** | pass, rc 1 |
| round-2 finding | `test_a_target_that_cannot_be_fetched_does_not_stop_the_check_of_the_next` (:320) | FAIL | **FAIL `0 != 1`** | pass, rc 1 |
| round-2 finding | `test_a_branch_that_cannot_be_judged_does_not_hide_a_rewrite_beside_it` (:325) | FAIL | **FAIL `0 != 1`** | pass, rc 1 |
| (2) fast-forward | `test_a_fast_forward_of_a_carried_branch_reports_nothing` (:362) | pass | pass | pass, rc 0 |
| (2) merged + deleted | `test_a_carried_branch_merged_and_deleted_reports_nothing` (:370) | pass | pass | pass, rc 0 |
| (2b) | `test_a_rewrite_the_next_fold_stops_on_is_reported_once` (:384) | pass | pass | pass, 1 line, rc 1 |
| (3) | `test_one_failed_fetch_does_not_stop_the_fold` (:430) | FAIL "one failed fetch stopped the fold: could not fetch origin …" | pass | pass |
| (4) | `test_a_fetch_that_keeps_failing_still_stops_the_fold` (:442) | FAIL (1 attempt, not 2) | pass | pass |

The (2)/(2b) cases pass before the fix by design: they guard against a false report and a
double report, and are not part of the RED the brief names. "`0 != 1`" on round 2's code
is the rewrite-line count: the rewrite was found but not printed.

**Mutations, each through the C4 runner and reverted afterwards** (worktree then compared
with `patch.diff` byte for byte: identical):

| mutation | result |
|---|---|
| fix reverted (C4 red leg) | 9 FAIL, 0 ERROR, module loads |
| round 2's production hunks under these tests | 4 FAIL (3 new cases `0 != 1`; one-target case on wording) |
| M1: no per-target `try` in `rewritten_carried` (fetch error escapes) | 2 ERROR (both one-failing-target cases at the time) |
| M2: no per-branch `try` (ancestry error escapes) | 1 ERROR (the per-branch case) |
| M3: `break` instead of `continue` after a failed target | 1 FAIL (`…does_not_stop_the_check_of_the_next`) |

M1 and M2 ran before I added the second order of the two-target case. M3 is why I added it:
with only the round-2 order, nothing pinned that the check goes on past a failed target.

## Gates I ran, through the project's runners (`/home/eddie/pdca/pdca-pdca/engine/scripts/`, each under `timeout`)

- **C4** `run-verify.sh` on the final `patch.diff`: green leg `Ran 12 tests … OK`; red leg
  `Ran 12 tests … FAILED (failures=9)`; `PDCA-EVIDENCE: C4 PASS — red without the fix,
  green with it`.
- **T3** `run-suite.sh` on the final tree: root suite `Ran 24 tests … OK`; driver suite `Ran
  2525 tests … OK (skipped=2)`; `PDCA-EVIDENCE: root suite OK, driver suite OK`. That covers
  criterion (5): every #633 test in `test_integrate_stack_bases.py` (`:1151-1384`), all of
  `test_flow_same_wave_conflict.py`, and 693's `test_flow_hold_exit_code.py`.
- **T2** `run-docs-check.sh`: `lint_docs: OK`, `render_site: link audit OK`.
- **C5** `run-prod-path.py` (`PDCA_PROD_PACKAGE=pdca_harness`): `1 added driver-suite
  test(s) import the production package 'pdca_harness'`.

## Refuting my own test

- **(a) Genuine red? Yes.** With the production hunks reverted (C4 red leg), 9 cases FAIL on
  assertions, none ERROR, and the module loads (it imports no symbol the fix adds). (1),
  (1b), (1c), the one-target unchecked case and the three new cases find no line on stderr.
  (3) fails with the original symptom, `could not fetch origin in …/repo` from
  `_carried_tips` → `_fetch`. (4) sees one attempt, not two. The three new cases also go red
  on round 2's code, so they pin this round's finding and not just "some fix exists". Each
  new error-handling branch is pinned by a mutation (M1, M2, M3 above).
- **(b) Production path? Yes.** The run cases call `cli._flow`, which runs the real
  `flow.flow_ids` → `_drive_and_act` → real `integrate.fold` (real git, a real bare origin,
  real pushes, a real second checkout) → `_report_late_rewrites` →
  `integrate.rewritten_carried` → the real `_fetch` / `_rev` / `_carried_rewrite` /
  `_in_line` → `cli._results_rc`. Only the leaves are stubbed, with the same stubs 693's
  merged test uses: `_drive_wave` writes a patch and accepts, `_publish_bundle` pushes a
  real branch, `gh` answers OPEN, `draft_texts` returns True. The `integrate._git` spies pass
  every call to real git except the ones they fail on purpose. The fetch cases call the real
  `integrate.fold`.
- **(c) Fixture includes the fault? Yes.** Each rewrite is a real force-push of the branch on
  the bare origin from a second clone, asserted not to be a fast-forward (test `:102`). In
  the two-target cases, Z is really carried (its head is asserted on the zbase line), and
  Z's checkout really fails its fetch: exactly two failed fetches, both after the fold. In
  the per-branch case, fix/A really moved (a real fast-forward push), so the check really
  calls `merge-base --is-ancestor`, and the spy fails exactly that one call (asserted once).
  In (1c) the force-push happens inside the fold's own `push` call, and the test asserts the
  line holds A's old head and not the rewrite.

## Commit-readiness

The target has no formatter config, no pre-commit config and no git hooks:
`core.hooksPath` unset, no non-sample hooks in the common git dir, and no
`.pre-commit-config.yaml`, `pyproject.toml`, `setup.cfg`, `ruff.toml` or `.flake8`. No
linter is installed (`pyflakes`, `ruff` absent from the instance venv). Its CI runs the
docs lint and site render (`docs-check.yml`) and the root suite (`render-check.yml`); both
are green above. All changed files byte-compile. The longest added line is 96 columns (base
max in `integrate.py` is 100). `git diff --check` is clean. I checked names by hand: `time`
and `Iterable` are imported in `integrate.py` (post `:77-78`); `Collection` and `Mapping` in
`flow.py` (`:27`); the dict union `|` at post `flow.py:2728-2729` needs Python 3.9+, and the
base is 3.11+.

## Not addressed

- The 8 deferred findings in `deferred-findings.json`. The carry-forward marks them for the
  human at handover, not build work. I did not read them.

## Files I left behind (for the harness to reclaim)

Scratch patches for the mutation and round-2 runs sit in
`/home/eddie/pdca/pdca-harness.pdca-wt/.cache/pdca-695-scratch/` (`v2-prod-v3-test/`, `m1/`,
`m2/`, `m3/`, `sample/`). `.cache/` is git-ignored by the target (`.gitignore:11`), so none
of it is in `git status` or `patch.diff`. I did not delete them: cleanup is the harness's.
The test file is staged intent-to-add (`git add -N`) in the worktree, so `git diff` shows
it. The worktree otherwise equals `ec1a36e` + `patch.diff`.

No external dependency was missing: Python 3 and git were enough.
