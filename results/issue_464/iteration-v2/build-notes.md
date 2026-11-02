# Build notes — issue 464 / wave-mode-none (iteration 2)

Target: `eduralph/pdca-harness @ main`, worktree base `3c11556` (= `origin/main`).
Line numbers are on the patched tree unless marked "base".

This iteration keeps iteration 1's patch and fixes the four implementation findings in the
carry-forward. Everything iteration 1 did is still in the patch (summary at the end).

## The four findings and what changed

### Findings 1 and 3 — a prerequisite with no PR was reported as "waiting for a merge" (exit 3)

Before: in `"none"`, `merged.merged_into` returns False when the prerequisite has no PR
(base `merged.py:99`), and `_runnable` put the dependent in `unlanded`: "merge their PR into
main, then re-run", recorded `"unmerged"`, exit 3 — for a PR that does not exist. And the
whole wave-boundary block was skipped in `"none"`, so a failed publish was never recorded.

Now:

- `flow.py:813-823` — in the `wait_for_merge` branch, before `merged_into` is asked, a
  patched prerequisite goes to a new `unpublished` list (`flow.py:806`) when it is in
  `unpushed` (in batch: this run pushed no branch of it) or its `publish.json` has no
  `pr_url`. No `gh` call is made for it. Read with `publish._publish_record`, as
  `flow.py:1349-1350` (`_finished_head`) already does.
- `flow.py:892-899` — its own one-line message, which does not claim a PR exists:
  `flow: issue_11 held — prerequisite(s) issue_10 accepted, but no PR of that work is on
  record (their publish did not push it, or opened no PR), so there is nothing to merge;
  not built on a base missing them. To build it, publish them (`pdca publish <id>` for 10),
  merge their PR into main (org/repo), then re-run.` For a dependent with no target, the
  "into …" part is dropped (same `into` idiom as the partner messages, `flow.py:926`).
- `flow.py:947-951` — the dependent is not runnable while `unpublished` is non-empty, and it
  is NOT added to `waiting`, so it gets no `"unmerged"` hold: PLANNED with no hold → exit 1.
  Same answer as stack mode for the same input (`holds={'10': 'unpushed'}`, exit 1).
- `flow.py:3159-3186` (base `flow.py:3078-3100`) — the "pushed no branch" bookkeeping runs
  in `"none"` again. Iteration 1 skipped the whole block (`and cfg.wave_mode != "none"` on
  the outer `if`); now only the fold is skipped, by a `continue` at `flow.py:3185-3186`
  after the bookkeeping. The bundle is recorded `"unpushed"` by the existing line
  `flow.py:3260`. The stack-mode stderr line is byte-identical to base `flow.py:3097-3100`
  (the text moved into `left`, `flow.py:3176-3179`); `"none"` prints
  `flow: issue_10 pushed no branch this run — no PR holds its accepted work; bundles that
  depend on it are held this run.` (no fold, no `Conflicts with` partners — below).
- Why `unpushed` is checked and not only `pr_url`: an iterate keeps `publish.json`, so after
  a failed re-publish the record still names the OLD PR, which holds the rejected work. With
  only the `pr_url` check, `merged_into` would ask about that old PR, hold the dependent as
  `"unmerged"` and tell the human to merge it — landing the rejected work.
  `test_an_iterated_prerequisite_not_published_again_is_not_waited_on_by_its_old_pr` pins
  this (mutation 1 below).
- `flow.py:3012-3016` (base `flow.py:2936-2938`) — `conflicts=None` in `"none"`. Needed
  because `held_unpushed` can now be non-empty in `"none"`: without this gate stack mode's
  #629 partner hold would fire there, with line advice ("no line of this run holds that
  work"). In `"none"` no bundle is built on a partner's work, so the edge only orders the
  build. This keeps iteration 1's behaviour for `Conflicts with` (where `held_unpushed` was
  always empty in `"none"`). Pinned by
  `test_a_conflicts_with_partner_of_a_bundle_that_pushed_no_branch_is_still_built`.

### Finding 2 — a dry-run asked the host and held every dependent

- `flow.py:2975-2982` — `wait_for_merge = do_publish and wave_mode == "none" and
  publisher.mode != "stub"`. Chosen on purpose: a dry-run asks no host and holds nothing,
  as `hold_unmerged` (`flow.py:2970-2971`) and the carry already do. A `"none"` dry-run now
  drives every wave, each dependent built on the unchanged base, as `--no-publish` does.
- Rejected: "rehearse the hold". The stub never opens a PR, so every dependent would be
  held, exit 3, told to "merge their PR" for a PR that does not exist, and wave 1+ of a
  `"none"` batch could never be rehearsed.
- This also settles deferred finding "`--rehearse` in `"none"` stops after wave 0" — the
  human should confirm the choice at sign-off.
- Pinned by `test_a_dry_run_asks_no_host_holds_nothing_and_plans_every_pr_on_the_base`: no
  `gh` call at all, B (`Stacks on: A`) built from `origin/main`, its dry-run plan line ends
  `→ main):`, holds `{}`, exit 0.

### Finding 4 — coverage for every edge kind, in batch or not, untargeted, `--no-publish`

New cases (all drive the real `_drive_and_act` on the real-git fixture):

- `Depends on (merged)` in batch → held `"unmerged"`, exit 3; after the merge, built on and
  published against main (`test_a_depends_on_merged_edge_in_the_batch_is_held_the_same_way`).
- Out-of-batch plain `Depends on`, not asked for (`flow 10`, then `flow 11`) — the path
  stack mode's #647 hold takes → held `"unmerged"`, exit 3, no "same `pdca flow <ids>`
  command" advice; after the merge, built and published against main
  (`test_a_prerequisite_an_earlier_run_finished_holds_its_dependent_the_same_way`).
- Untargeted dependent → `skipped — prerequisite(s) not ready (10)`, no hold, exit 1; after
  the merge, built (no target, no PR), exit 0
  (`test_a_dependent_with_no_target_is_not_ready_until_its_prerequisite_merges`).
- `--no-publish` → B built on `origin/main` once A is accepted, no `gh` call, no line, exit 0
  (`test_with_no_publish_a_dependent_builds_on_the_unchanged_base`).
- Plus the no-PR cases for findings 1/3: texts failed, `gh pr create` failed after the push,
  and the iterated prerequisite with a stale record.

## Docs

- `docs/07-crosscutting.md:932-946` — the `"none"` bullet now says what happens to a
  prerequisite with no PR (held with "publish it first", exit 1; `"unpushed"` as in stack
  mode), that a dry-run holds nothing, and that `Conflicts with` only orders the build.
- `template/pdca.toml.jinja:127-134` — unchanged from iteration 1.

## Choices the human should confirm at sign-off

1. Leg (c) (config validation) is in scope — the brief flags it.
2. Dry-run holds nothing (finding 2, above).
3. A dependent of a prerequisite with no PR exits 1 and gets no hold of its own; the
   prerequisite is recorded `"unpushed"` when this run pushed no branch of it.
4. `Conflicts with` only orders the build in `"none"` (deferred finding 6). I documented the
   current behaviour (`docs/07-crosscutting.md:944-946`) and pinned it with a test, because
   re-enabling the bookkeeping forced a decision at `flow.py:3016`. If you want a partner
   held until its partner's PR merges instead, that is a new rule, not a one-line flip.
5. Not addressed — deferred to you in `deferred-findings.json`: a chain A→B→C exits 1
   (C is skipped, not held); a dependent on a different base than its prerequisite's PR is
   held forever; a fetch failure in the #729 check is recorded `"unmerged"` (exit 3). For
   the last one the alternative is one line: `flow.py:950` add
   `and all(known for _n, _w, known in off_base)` so an unknown base exits 1.
6. A failed publish in the FINAL wave still exits 0 in every mode: the bookkeeping only
   runs between waves (base `flow.py:3078`). Unchanged; same as a one-bundle run.

## Alternatives ruled out (with cost)

- Treat a no-PR prerequisite as `unmet`, with the generic `skipped — prerequisite(s) not
  ready (10)` line: 8 lines smaller (no `unpublished` list, no message block at
  `flow.py:892-899`), but it names no way out, which the brief's goal asks for.
- Pass `pushed` into `_runnable` instead of re-enabling the bookkeeping: one more parameter
  and call-site argument (+2 lines), but the `"unpushed"` record would still be missing
  from `holds` — the carry-forward asked to keep it.
- The code-review cleanup (merge the duplicated `lacks` cache block, `flow.py:831-836` vs
  `flow.py:863-868`, into a helper): saves ~2 lines net but rewrites the stack-mode #729
  branch, which is out of scope ("any change to stack or merge behaviour"). Not done.

## Test — `template/tests/test_flow_wave_mode_none.py` (17 cases)

Drives `flow._drive_and_act` on `StackFoldGit` (loaded by path, as
`test_flow_same_wave_conflict.py:36-39`). Stubbed: the build/sign-off leaves
(`flow._drive_wave`), drafting of the publish texts (`publish.draft_texts`: ready, or
failed for the ids a case names), and `gh` (in front of `subprocess.run`; `gh pr create`
can fail for a named id). NOT stubbed: `_runnable`, `_publish_bundle` → `publish.publish`
(real cut, commit, push to the bare origin), `integrate.unpublished`, `merged.merged_into`,
`_base_lacks_merge` (real fetch + ancestry), `worktree._target`, `Config.load`,
`cli._results_rc`, `cli._waves`.

| case | leg / finding |
|---|---|
| independent A, C on main; B (`Depends on: A`) held `"unmerged"`, exit 3 | (a) |
| A merged → re-run builds B from fetched main, PR against main | (b) |
| B `Stacks on: A`: held; after the merge built/cut/opened on main | (a2) |
| `Depends on (merged)` in batch: held the same way, then built | finding 4 |
| out-of-batch, not-asked-for `Depends on`: held the same way, then built | finding 4 |
| untargeted dependent: "not ready", exit 1; built after any merge | finding 4 |
| A's texts fail: B held "no PR", A `"unpushed"`, exit 1, no `gh pr view` | findings 1/3 |
| A's `gh pr create` fails after the push: B held "no PR", exit 1 | findings 1/3 |
| A iterated, stale record names old PR, texts fail: old PR never asked about | findings 1/3 |
| `Conflicts with` partner of an unpushed A: built on main, A `"unpushed"`, exit 3 | gate at :3016 |
| `--no-publish`: B built on main, no `gh` call, exit 0 | finding 4 |
| dry-run (stub publisher): no `gh` call, B built, plan opens against main, exit 0 | finding 2 |
| A reads MERGED but fetched main lacks the merge → B still held | (b2) |
| stack mode control: the same batch folds a `pdca-integration/*` line | (d) control |
| `pdca waves` in none mode does not claim "builds on the prior" | design bullet |
| `wave_mode = "bogus"` → note naming it and the 3 values, falls back to stack | (c) |
| `stack` / `merge` / `none` load as written, no note | (c) control |

## Refuting my own test

- **(a) Genuine red? Yes.** The project's C4 runner (`engine/scripts/run-verify.sh`,
  `PDCA_BUNDLE`/`PDCA_WORKTREE` set, under `timeout 900`): green leg `Ran 17 tests … OK`;
  red leg (production hunks reverted, test kept) `Ran 17 tests … FAILED (failures=14)`, no
  import failure, `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`. Every red
  is an assertion on behaviour: B built on `pdca-integration/main-r…-b11`, an extra PR for
  11, the #647/#629 line advice, `'bogus' != 'stack'`. The 3 that stay green without the
  fix are controls by design (stack-mode fold, known values load, `--no-publish`).
- **Against iteration 1's production code** (same runner, v1 production hunks applied, new
  test kept): `Ran 17 tests … FAILED (failures=5)` — exactly the dry-run, texts-failed,
  PR-not-opened, iterated-prerequisite and `Conflicts with` cases. So the new cases bind
  this round's findings; the other 12 pass on v1 as they should.
- **Mutations** (each applied alone to the final `flow.py`, run through the C4 runner's
  green leg, file restored after; the worktree diff is byte-identical to `patch.diff`
  afterwards, checked with `cmp`):
  1. drop the `p.name in unpushed_set` check → the iterated-prerequisite case fails;
  2. let a dry-run wait for merges → the dry-run case fails;
  3. skip the `"unpushed"` bookkeeping in `"none"` → texts-failed, iterated and
     `Conflicts with` cases fail;
  4. drop the `pr_url` check → the PR-not-opened case fails;
  5. count a no-PR prerequisite as waiting again (`waiting` without `not unpublished`) →
     all three no-PR cases fail;
  6. drop the `"none"` gate on `conflicts=` → the `Conflicts with` case fails.
- **(b) Production path? Yes.** See the not-stubbed list above. The failed publish is the
  real one: `draft_texts` returning False makes `_drive_and_act` skip `_publish_bundle`
  (base `flow.py:3059-3069`), and a failing `gh pr create` reaches the real
  `publish.publish` after its real push (base `publish.py:425-432`), which writes
  `pr_url: ""`. The stubbed pieces are the model leaves and the `gh` host, as the peer tests
  stub them.
- **(c) Fixture includes the fault? Yes.** Each no-PR case has the real missing PR: no
  `publish.json` at all; a pushed branch on the bare origin with `pr_url: ""`; a real stale
  `publish.json` left by a real earlier publish, naming a PR the stub reads as OPEN. The
  bare origin can show an integration line (the stack control sees one), so "no line in
  `"none"`" is not vacuous.

## Other gates run

- **T3 (`engine/scripts/run-suite.sh`, under `timeout 3000`, on the final patch):** root
  suite `Ran 50 tests … OK` — render and update-compat ran with copier, not skipped
  (`test_render_then_slice`, `test_merge_leaves_no_conflict_markers`,
  `test_merged_config_still_loads` all ok over the changed `pdca.toml.jinja`); driver
  suite `Ran 2664 tests … OK (skipped=2)` (iteration 1: 2655; +9 new cases here; the 2
  skips are elsewhere). So (d) holds: the stack- and merge-mode suites are unchanged and
  green.
- **T2 (`engine/scripts/run-docs-check.sh`, under `timeout 900`):** `lint_docs: OK`,
  `render_site: link audit OK`. The CI link checker
  (`.github/docs-check/docs_links.py`): 458 relative links in 67 files, 0 broken.
- **Commit-ready:** the target has no pre-commit hooks, no `core.hooksPath`, and no
  formatter or linter config (no `.pre-commit-config.yaml`, no ruff/black/flake8 settings);
  its CI is render-check, docs-check, docs-immutability, DCO. Every added line is ≤ 100
  columns. `git apply --cached --check --whitespace=error-all` of `patch.diff` against a
  fresh `origin/main` index passes. DCO sign-off is added by publish (`git commit -s`).

## Housekeeping

- My first C4 run's log went to `/tmp/claude-c4-464.log` — outside the roots I was given,
  by mistake. Every later log is in the worktree's git-ignored `.cache/`. Not removed
  (cleanup is the harness's).
- The worktree's `.cache/` (git-ignored) holds `iter2-keep/` (backups for the mutation and
  v1 runs), `mutate.py`, `check-index` (the throwaway index for the apply check) and logs.
  None of it is in the patch.
- An earlier T3 run was stopped part-way (my own process group) because I had edited
  comments and the test file while it ran; the result above is from a clean run after the
  last edit.

## What iteration 1 did, still in this patch

- `config.py:42` `WAVE_MODES`; `config.py:740-747` (base `config.py:733`) unknown value →
  note, falls back to `"stack"`, same shape as `merge_requires` (base `config.py:738-742`);
  exact match, no lower-casing, so a near-miss never turns into merge mode.
- `flow.py:2957` (base :2888) no `_carry_finished` in `"none"`; `flow.py:2970` (base :2901)
  `hold_unmerged` False, so `own_bases` (`flow.py:2974`) is False: no `_base_plans` /
  `_bundle_bases`, and `_point_at_integration` with an empty `integ` clears stale markers.
- `flow.py:3159-3186` no fold / merge in `"none"` (see above for the bookkeeping).
- `flow.py:813-837` the `"none"` hold: `merged_into` against d's own base, then the #729
  `_base_lacks_merge` check with no line (base `flow.py:807-809` skipped it when no line
  existed); `flow.py:887-891` the `"none"`-worded message; `flow.py:3263` `"unmerged"` in
  `holds`.
- `cli.py:702-709` `_UNMERGED_HOLD`, `_UNBUILT_HOLDS`; `cli.py:757` (base :741) counts it as
  held-before-built → exit 3; `cli.py:1115-1119` (base :1099-1100) `pdca waves` wording.
- `publish.py:241` (base :239) no "Stacks on with no branch" refusal in `"none"`;
  `publish.py:764-774` (base :762-768) `_stacks_on_branch` → None in `"none"`, so publish
  cuts from `origin/<base>` (base :265) and opens against the base (base :282).
