# Build notes — #738, iteration 6: hold a bundle whose own base cannot be built

Target: eduralph/pdca-harness, built on the run's line `pdca-integration/main-r547f8028520f`
at `75a886e` (the worktree's HEAD). Every `path:line` below is on `75a886e` unless it says
"patched tree". `patch.diff` is `git diff` of the worktree against `75a886e`, nothing staged.

## What this iteration changes

The sign-off kept iteration 5's hold mechanism and asked for exactly three fixes, each with a
real-git test in `template/tests/test_flow_bundle_base_holds.py`. The iteration-5 patch was
applied as is, then only these were changed.

### 1. The "next fold stops the run" warning prints only when that fold runs

Before: the wave loop passed `fold_next=k < len(wave_list) - 1` (patched tree, iteration 5).
When every bundle of wave k was held, the loop's `if not runnable: continue` skipped that
wave's fold, but B's line still warned of it.

Now (patched tree `flow.py:2883-2890`): the held bundles are taken out of `runnable` first,
and the warning is passed as `fold_next=bool(runnable) and k < len(wave_list) - 1`. That is
the rule the sign-off gave: something of wave k is left to build, and a later wave remains.
It mirrors the fold's own test at `flow.py:2834`. When something is left, the fold really
runs: `_fold_lines` always calls `integrate.fold` over every accepted bundle (`flow.py:1090-1094`),
and that fold refuses the rewritten branch (#633, case 2c shows it).

Docstrings that described the old rule were updated:
- `_announce_base_holds` (new function, patched tree `flow.py:1101-1131`).
- `_Rewritten` (`integrate.py:127-129`): "when a later wave remains" became "when a fold
  follows that bundle's wave".

Test: `test_a_rewrite_hold_that_leaves_its_wave_nothing_to_fold_warns_of_no_fold`. A in
wave 0; B (`Depends on: A`) alone in wave 1; C (`Depends on: B`) in wave 2; `fix/A`
force-pushed after wave 0's fold. It asserts:
- B's line does not say "next fold";
- only one fold ran;
- C is skipped;
- the end-of-run check names A's rewrite;
- holds `{"B": "base", "A": "rewritten"}`, exit 1.

Case (2c) is unchanged and still passes. I used C, not "an unrelated V": with B alone in
wave 1, any bundle in wave 2 must have an edge to B (`waves.compute_waves`,
`waves.py:214-221`, levels a bundle one past its latest prerequisite), so an unrelated V
cannot be there.

### 2. A hold's cause is never lost to a broken worktree later in the same wave

Before: `_bundle_bases` put B in `held` and went on. When W's build then raised
`IntegrationTreeError`, the handler printed only W's `STOPPING` line and broke, so B's cause
was printed nowhere.

Now (patched tree `flow.py:2877-2882`): the handler first calls
`_announce_base_holds(cfg, failed, fold_next=False, stopping=True)` and records those
bundles in `held_base`, then prints the `STOPPING` line.

Two things here go a little past the literal sign-off text, both so the output stays true:
- **The `stopping` wording** (patched tree `flow.py:1119-1122`). The normal hold line ends
  "…and the rest of this wave goes on." Printed just before "STOPPING — wave 1 and later
  waves not run", that contradicts the next line, which breaks the invariant "never promises
  more than the run does". So with `stopping=True` the line keeps the cause and the fix and
  ends "issue_B is not built this run." Cost: one keyword argument plus 4 lines.
- **`held_base.update(failed)` in the handler** (1 line). The holds map then agrees with
  stderr (B's line says "held"). The exit code is unchanged: W, the bundle that stopped the
  run, is PLANNED with no hold, so rule 1 still gives 1. `holds` feeds only
  `cli._results_rc` (`cli.py:642-684`).

Test: `test_a_broken_worktree_after_a_hold_in_its_wave_names_that_hold_first`. A, Z in
wave 0; B (`Depends on: A`), W (`Depends on: Z`) in wave 1. B's `git fetch` fails, then the
`git reset` inside `_reset_tree` fails while W's base is built. It asserts:
- both faults fired, in that order;
- one `STOPPING` line, and it is W's base line;
- B's hold line names `could not fetch origin in …` and "check the remote … then re-run";
- B's line comes before the `STOPPING` line;
- B's line ends "issue_B is not built this run.", with no "goes on" and no "next fold";
- B and W are PLANNED; holds `{"B": "base"}`; exit 1.

### 3. `integrate._LineBroken` stops the run, as `IntegrationTreeError` does (decision 3)

`_bundle_bases` now re-raises `(integrate.IntegrationTreeError, integrate._LineBroken)`
(patched tree `flow.py:1050`; was `flow.py:1019-1022`). The wave-loop handler catches both
(patched tree `flow.py:2877`). This is the same pair the carry re-raises under `skipped`
(`integrate.py:645-647`; the carry-forward's `:649-651` is the same code in the patched
tree, shifted by the `_Rewritten` docstring). The `_bundle_bases` docstring and the
wave-loop comment now name both classes.

`build_bundle_base` can raise `_LineBroken` through `_member_clash` → `_trial`
(`integrate.py:969`, raise at `:1915-1916`), and through `_merge_published` → `_keep_merge`
→ `_reset_line` (`integrate.py:1318`, `:1349`/`:1353`, raise at `:1664-1665`).

Test: `test_a_base_branch_that_will_not_go_back_still_stops_the_run`. A, Y, Z in wave 0;
B (`Depends on: A, Y`), W (`Depends on: Z`) in wave 1. After wave 0's fold, main gets its own
`y.txt`, so on B's base Y clashes after A has merged. `_member_clash` then tries Y on main
alone (`_trial`). The test fails only the `git checkout -q <B's base branch>` that `_trial`'s
`finally` uses to put the branch back (`integrate.py:1914`). That is the only
`checkout -q <branch>` call in integrate.py; the others are `checkout -B` and
`checkout -q --detach`. So the real `_LineBroken` raise fires with its real words. It
asserts:
- that one checkout failed;
- one `STOPPING` line, the wave-loop base one (`could not build issue_B's own base from
  issue_A, issue_Y: could not put <branch> back at … after a trial merge`), not the fold's;
- no `issue_B held` line;
- B and W are PLANNED and never built; holds `{}`; exit 1.

Like case (8), this is a keep-behaviour guard: it passes with the whole production change
reverted, because the code before #738 stopped on every base failure.

## The rest of the patch (iteration 5's mechanism, kept)

- `flow.py:992-1034` `_bundle_bases`: new `held` dict. Any other `IntegrationError` goes
  into `held[d.name] = (whose, exc)` (was the re-raise at `:1019-1022`). The pointing loop
  (`:1024`) skips held bundles.
- New after `flow.py:1034`: `_BASE_HOLD_STEPS` and `_base_hold_why` (the fix wording, keyed
  on `exc.cause`; the fetch fix only for `could not fetch `, `integrate.py:2042`), and
  `_announce_base_holds` (one stderr line per hold, modelled on `_announce_conflict_holds`,
  `flow.py:1435`).
- `flow.py:681-856` `_runnable`: new `unbuilt` set. A `Conflicts with` partner of a base-held
  bundle is held with its own line, the way partners of `unpushed` are (`:757-762`,
  `:838-845`).
- `flow.py:2686-2688`: `stop_named` replaced by `held_base`. It is passed to `_runnable` in
  `held=` and `unbuilt=`, and in the `conflicts=` condition (`:2699-2713`), mirroring
  `held_unpushed`.
- `flow.py:2914`: the end-of-run check gets every accepted bundle, so a hold never takes the
  rewritten member out of it (#695 wins, decision 2).
- `flow.py:2921-2924`: `holds` gets `"base"` entries, written before the late
  `"rewritten"`/`"unchecked"` ones.
- `flow.py:2555-2564`: the `holds` docstring now covers `"base"`.
- `cli.py:692`: `_RC_HELD` comment. New `_BASE_HOLD = "base"` after `:693`. `_results_rc`
  docstring (`:703-716`). Rule 1 (`:728`): a key passes when its state is in `ok` or `holds`
  maps it to `"base"`.
- `integrate.py:127-129`: `_Rewritten` docstring only. No message text in integrate.py
  changed.
- Existing tests that pinned the old stop now assert the hold, with no expected exit code
  changed:
  - `test_flow_dependency_scoped_bases.py:500-548` (no exit-code assertions in that file);
  - `test_integrate_carried_rewrite_late.py:34-40, 204-216, 290-313, 347-371` (both
    `rc == 1` kept; iteration-v4's flip to 3 is not repeated).

## Ruled out, with the cost

1. **Wording the warning as "a later fold" instead of fixing when it prints** (the code
   review's other option). Rejected: the sign-off chose the rule. "A later fold" would also
   be untrue when no later wave builds, as in the new test.
2. **Predicting whether a LATER wave's fold will run**, to warn when wave k is fully held
   but wave k+1 still builds something. That needs the outcome of wave k+1's `_runnable`
   before wave k is done, which isn't known yet. Without the warning, the line promises
   nothing false.
3. **Moving the warning to just before the fold.** Then it would always be right, but it
   would come after the wave's whole build, and the fold's own `STOPPING` line names the
   rewrite at that point anyway. The early warning exists so the human can restore `fix/A`
   while the wave builds.
4. **Item 3's stub: wrap `integrate.build_bundle_base` to raise `integrate._LineBroken(...)`
   directly.** About 4 lines simpler, but then the raise is the test's, not production's. I
   failed one git call instead, as the brief asks of every stub ("the stubs replace a git
   call"). Cost: the test needs a second-member clash (Y after A) so that `_member_clash`
   runs `_trial`; that is 3 extra `_plan` lines.
5. **Iteration 5's "Ruled out" item 5** (hold on `_LineBroken`, since every later build
   resets the tree) is reversed by the sign-off's decision-3 reading, and the code now
   follows it.
6. **Unchanged from iteration 5, still true:**
   - `stop_named` removed rather than kept empty (−5 lines; nothing could add to it).
   - No new exception classes in integrate.py (out of scope; iteration-v4 needed about +40
     lines for them).
   - The extra fix rows for checkout-missing, worktree-not-made and git-step causes (8 lines
     of table, each pinned by a test).
   - No fold after a fully-held wave (it would fold an unchanged line).
   - The rule-1 exemption keyed on the `"base"` entry.
   - No separate reporter for case (6): `S` is a seam, so `line_cut[S]` →
     `_heads_taken` → `rewritten_carried`'s `line_prs` names it (`flow.py:1028`,
     `:1037-1049`, `integrate.py:1257-1266`).
   - Case (8) fails the `git reset` inside `_reset_tree` (`integrate.py:2003-2004`), so the
     real raise fires.

## Refute-your-own-test

- **(a) Genuine red? Yes.**
  - Project C4 runner, run from the instance root with `PDCA_BUNDLE` / `PDCA_WORKTREE` set
    and under `timeout`: `engine/scripts/run-verify.sh` → exit 0 and
    `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`. Log: `.c4-local.log` in
    this bundle.
  - Green leg: the new file 16/16 OK; `test_flow_dependency_scoped_bases` 25 OK;
    `test_integrate_carried_rewrite_late` 15 OK.
  - Red leg: the new file `FAILED (failures=14)`. The two that pass are the deliberate
    both-legs guards: case (8) and the new `_LineBroken` case. Item 1's test fails on
    `'STOPPING' unexpectedly found` (the old stop at B's base). Item 2's test fails on
    `['fetch'] != ['fetch', 'reset']`: the run stopped at B, so W was never built. The two
    edited existing files fail 2 each.
  - Each new test also fails on iteration 5's code, the code the sign-off rejected. I put
    the worktree's `template/src` back to `75a886e` plus iteration 5's production hunks and
    ran the file: `FAILED (failures=3)`, exactly the three new tests:
    - item 3: B held (`flow: issue_B held — … could not put … back …`), no `STOPPING`;
    - item 2: only W's `STOPPING` line, nothing about B;
    - item 1: B's line ends "But the next fold stops the run unless origin/fix/A is
      restored first", though no fold followed.

    Then I restored the new code and checked the worktree diff is byte-identical to
    `patch.diff`.
- **(b) Production path? Yes.**
  - The tests call `flow._drive_and_act` and `cli._results_rc` unmodified, so the changed
    code runs: `_bundle_bases`, `_announce_base_holds` (both modes), the wave-loop handler
    and the `fold_next` computation.
  - Real git runs the real `build_bundle_base`, `_fetch`, `_reset_tree`, `_member_clash` /
    `_trial`, the folds, and the end-of-run `rewritten_carried`.
  - Stubbed as in the peer suites: `flow._drive_wave`, `flow._publish_bundle`,
    `publish.draft_texts` and `gh`.
  - `integrate.fold` and `integrate.build_bundle_base` are wrapped call-through, only to
    count folds, run hooks and mark whose base is being built.
- **(c) Fixture includes the fault? Yes.**
  - Item 1: `fix/A` really force-pushed on origin.
  - Item 2: two real git calls fail, in two bundles' builds; both are asserted to have
    fired.
  - Item 3: a real clash on main, and the real checkout in `_trial` fails, asserted to have
    fired.
  - W, C and the members are all in the run; nothing is curated out.

## Runs

- The brief's nine listed suites plus the new file, each under `timeout`: all OK
  (`test_integrate_bundle_base` 26, `test_flow_dependency_scoped_bases` 25,
  `test_flow_carried_prereq_bases` 8, `test_flow_merged_prereq_dependency_base` 5,
  `test_flow_same_wave_conflict` 8, `test_flow_conflict_partner_hold` 4,
  `test_flow_hold_exit_code` 8, `test_integrate_stack_bases` 62,
  `test_integrate_carried_rewrite_late` 15, new file 16).
- Project T3 runner `engine/scripts/run-suite.sh`: root suite `Ran 24 tests … OK` (none
  skipped, so render/update-compat really ran). Driver suite
  `Ran 2610 tests … OK (skipped=2)`. `PDCA-EVIDENCE: root suite OK, driver suite OK`. Log:
  `.t3-local.log` in this bundle.
- Project T2 runner `engine/scripts/run-docs-check.sh`: docs lint clean, site render and
  link audit clean.

## Commit-ready

The target configures no formatter, linter or commit hook:
- no `.pre-commit-config.yaml`;
- no ruff/black/flake8/isort/mypy config;
- no `core.hooksPath`, and only `*.sample` files in the hooks directory;
- CI runs only the docs checks and the render suite (`.github/workflows/*.yml`).

CONTRIBUTING.md asks for a DCO sign-off (`git commit -s`), which publish adds. Checks done:
`git diff --check` is clean; no added line is over 100 characters (the files' wrap); all
four touched Python files pass `py_compile`.

## For the human at sign-off

- **A stray file outside the roots, my mistake:** `/tmp/.unused`, a copy of the worktree
  diff, left by a leftover redirect in one of my commands. I did not delete it (cleanup is
  not the builder's). It holds nothing secret.
- In this bundle I overwrote `.c4-local.log` (it held an earlier iteration's local C4 run)
  and added `.t3-local.log`.
- **A corner the sign-off's rule does not cover.** If a bundle of the same wave splits, and
  re-levelling the remaining schedule (`_adopt_split_children`, `flow.py:2250-2262`) holds
  every later bundle, the wave list can shrink after the warning was printed. Then a printed
  "next fold" warning would have no fold behind it. Fixing it means printing the warning
  after adoption, i.e. after the wave builds (ruled out 3). I left it.
- The adversary's side note that `cli.py:638-641` still says `holds` lists only bundles "a
  fold of this run held out of its line" that "read COMPLETE": still true of that comment,
  which this patch does not touch. Not changed, per "No other changes". A one-line fix for
  #740's docs pass.
- `IntegrationError`'s docstring (`integrate.py:85-94`) still says "The caller STOPs". True
  for the fold, no longer for a base build. Left alone: the brief limits integrate.py to
  `_Rewritten`'s docstring.
- In runs like cases (2) and (6) the rewrite of `fix/A` is named twice on stderr, on B's hold
  line and by the end-of-run check. The brief says this is intended (decision 2).
- No external dependency was missing. No NEEDS-HUMAN item from Do.
