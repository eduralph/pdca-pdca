# Build notes — issue 464 / wave-mode-none

Target: `eduralph/pdca-harness @ main`, worktree base `3c11556` (= `origin/main`).
Line numbers below are on the patched tree unless marked "base".

## What the change does

`[driver].wave_mode = "none"` is a third mode. Every accepted bundle publishes as a draft PR
against its real target base; at a wave boundary nothing happens; waves still order the
build; a dependent waits until its prerequisite's PR has merged into its own base.

### config.py — the value, validated at load (leg c)

- `config.py:39-42` — new `WAVE_MODES = ("stack", "merge", "none")`.
- `config.py:740-747` (base `config.py:733`) — an unknown value prints
  `config: unknown [driver].wave_mode '<v>' — expected stack | merge | none; using 'stack'`
  and falls back to `"stack"`. Same shape as `merge_requires` (base `config.py:738-742`).
- Deliberate difference from `merge_requires`: **no `.strip().lower()`**. Today every check
  is an exact `== "merge"` / `!= "merge"`, so `"Merge"` or `" merge"` silently runs as
  stack. Lower-casing would turn such a typo into unattended merging — the dangerous
  direction. Exact match + fall back to stack keeps today's behaviour for every non-exact
  value, and only adds the note. So for an instance with a typo, behaviour is unchanged
  (as the brief's Impact section says).
- `config.py:366-369` — field comment names the third value.

### flow.py — the three wave-boundary gates

All three checks keep "anything that is not merge/none behaves as stack", so an in-process
`Config` with an odd value still behaves as before (`not in ("merge", "none")`, rather
than `== "stack"`).

- `flow.py:2933` (base :2888) — `_carry_finished` runs only `not in ("merge", "none")`.
- `flow.py:2946` (base :2901) — `hold_unmerged` is False in `"none"`; `own_bases`
  (`flow.py:2950`) is the same value, so `_base_plans` / `_bundle_bases` (base :2924,
  :2994) do not run and the `else` branch `_point_at_integration(integ={}, …)` clears any
  stale stack-base marker, so every bundle is built from its real base.
- `flow.py:3131` (base :3078-3080) — the fold/merge block is skipped entirely in
  `"none"`: neither `merge.merge_wave` nor `integrate.fold` (nor the `held_unpushed`
  bookkeeping inside the stack branch) runs.
- `flow.py:2954-2955` — `wait_for_merge = do_publish and cfg.wave_mode == "none"` and the
  `held_waiting` collector, passed to `_runnable` at `flow.py:2995`.
- `flow.py:3230` — `held_waiting` is written into `holds` as `"unmerged"`, before the
  late-rewrite entries (which must stay last because they outrank a hold).

### flow.py — the new hold in `_runnable`

New code, modelled on the #647 hold (base `flow.py:786-841`) but not a reuse of it:

- `flow.py:807-823` — when `wait_for_merge`, after the COMPLETE check, EVERY prerequisite
  (in batch or not; `deps` is `waves.declared_deps`, so all three edges) goes through
  `merged.merged_into(cfg, dep, repo, base)` (`merged.py:72`). Not merged → `unlanded`
  (or `unmet` for a d with no usable target, keeping #186's "any merge counts / not
  ready" answer). Merged and patched → the #729 check `_base_lacks_merge` runs
  **unconditionally** (no `line is None → continue` as at base :807-809, since there is
  never a line in `"none"`), cached in `lacks` with the same key shape as base :818.
  Then `continue`: the stack-mode branches (`cand`, `carryable`, `held`) are never reached.
- `flow.py:873-877` — the one-line message:
  `flow: issue_B held — prerequisite(s) issue_A not merged into main (org/repo);
  wave_mode = "none" builds every bundle on main itself, so it is not built on a base
  missing them. To build it, merge their PR into main, then re-run.`
  No "line of this run", no "carries them", no "name X in the same `pdca flow <ids>`".
- `flow.py:926-929` — d is runnable only if `unlanded` is empty too; otherwise, in
  `"none"`, d is added to `waiting` unless a prerequisite is `unmet` (not ready at all —
  that stays a failure, exit 1).

### cli.py

- `cli.py:701-709` — `_UNMERGED_HOLD = "unmerged"`, `_UNBUILT_HOLDS = {base, unmerged}`.
- `cli.py:755` (base :741) — `_results_rc` counts both as held-before-built, so a PLANNED
  bundle held `"unmerged"` returns **3**, not 1. Docstring updated at :720-742.
- `cli.py:1113-1117` (base :1099-1100) — `pdca waves` prints `(none mode; every PR against
  its base; a dependent waits for its prerequisites' PRs to merge)`; the "each wave builds
  on the prior's accepted work" tail is printed only for the other modes.

### publish.py — `Stacks on` in `"none"`

- `publish.py:764-770` (base :762-765) — `_stacks_on_branch` returns None in `"none"`.
  This one change covers every reader: publish's `stack_branch` (`publish.py:239`, base
  :238) → `checkout_base = origin/main` (base :265) and `pr_base = base` (base :282);
  the Do worktree base `worktree.py:96` (via `_stack_base_branch`); `drift.py:67`.
- `publish.py:240` (base :239) — the "Stacks on a prereq with no published branch yet"
  refusal does not fire in `"none"`.
- I did NOT change `publish.py:251` (`wave_stacked`) or `_read_stack_base`: in `"none"`
  the flow clears every runnable bundle's stack-base marker (`_point_at_integration`
  with an empty `integ`), so `wave_base` is "". A direct `pdca publish` of a bundle that
  was built on a stack-mode line keeps publishing from that line, which matches what its
  patch was built against.
- The merge-mode #411 guard (`publish.py:296`) is `== "merge"`, so it does not apply.

### Docs

- `template/pdca.toml.jinja:114` and `:127-134` — a `"none"` paragraph, placed between
  the `"stack"` and `"merge"` paragraphs on purpose: NOT adjacent to the
  `wave_mode = "stack"` line (now :146), which instances commonly edit. An insertion
  abutting an instance-edited line becomes a conflict marker on `copier update` (the
  failure the `size_guard` comment in this instance's pdca.toml describes).
- `docs/07-crosscutting.md:644-646` and `:914-940` — the `"none"` bullet after
  `"merge"`.

## Choices the human should confirm at sign-off

1. **Leg (c) is in scope** (the brief flags it).
2. **(b2) is recorded as `"unmerged"` and exits 3.** The brief only says "still held".
   In `"none"` both the not-merged hold and the merged-but-fetched-base-lacks-it hold come
   from the new branch, and both mean "the prerequisite's merge is not (known to be) in
   d's base", so I record both. Stack mode's #729 hold (base :818-823, :854-862) is NOT
   recorded and still exits 1 — unchanged. If you would rather (b2) exit 1 in `"none"`
   too, change the condition at `flow.py:928` to `… and not unmet and unlanded` — a
   one-line change — and drop the b2 assertion on `(holds, rc)`.
3. **A dependent of a held bundle is "skipped — not ready", exit 1.** A → B → D in one
   `"none"` run: B is held `"unmerged"`, D is skipped because B is not COMPLETE. That is
   the existing rule for a hold with a dependent in the run (docs 07 :741-742, and
   `_results_rc`'s docstring for `"base"`). I kept it rather than invent a cascade.
4. **Dry-run (stub publisher):** the `"none"` hold applies (it is gated on `do_publish`
   only, not on `publisher.mode`). A dry-run publishes nothing, so an in-batch
   prerequisite has no PR and its dependent is held — which is what a real run would
   do. No `gh` call happens for that case (`merged_into` returns before `gh` when there is
   no `publish.json`).
5. **`--no-publish`:** nothing waits, same as stack/merge (gated on `do_publish`).

## Alternatives ruled out

- **Reusing the #647 hold** by widening its condition (base :795-798). Rejected per the
  brief: its `cand` is tied to the fold (`integrate._fold_candidates`), it only covers
  out-of-batch plain `Depends on`, and its message carries line advice. Making it serve
  `"none"` would need the same new conditions plus a message switch inside a branch whose
  meaning is "a line would carry it" — more coupling, not less.
- **Gates as `== "stack"`.** Equivalent for a loaded Config, but changes behaviour for an
  in-process Config with an unexpected value. `not in ("merge", "none")` keeps "stack is
  the fallback for anything" true everywhere.
- **Refusing a `"none"` batch with dependency edges** (the issue's first option) — the
  brief chose holding.

## Test — `template/tests/test_flow_wave_mode_none.py` (8 cases)

Drives `flow._drive_and_act` on the `StackFoldGit` fixture (loaded by path, as
`test_flow_same_wave_conflict.py:36-39` does). Stubbed: the build/sign-off leaves
(`flow._drive_wave`), publish text drafting (`publish.draft_texts`), and `gh` (in front of
`subprocess.run`). NOT stubbed: `flow._publish_bundle` → `publish.publish` (real cut,
commit, push to the bare origin; the `gh pr create` argv asserted on is the one publish
builds), `_runnable`, `merged.merged_into`, `_base_lacks_merge` (real fetch + ancestry),
`worktree._target` (the Do worktree base, called from the build stub), `Config.load`,
`cli._results_rc`, `cli._waves`.

| case | leg |
|---|---|
| independent A, C publish on main, B (`Depends on: A`) held | (a) |
| A merged, re-run builds B from fetched main, PR against main | (b) |
| B `Stacks on: A`: held; after merge built/cut/opened on main, not A's branch | (a2) |
| A reads MERGED but origin/main lacks merge commit and head → B still held | (b2) |
| same batch in stack mode folds a `pdca-integration/*` line, builds B | control |
| `pdca waves` in none mode doesn't claim "builds on the prior" | design bullet |
| `wave_mode = "bogus"` → note naming it and the 3 values, falls back to stack | (c) |
| `stack` / `merge` / `none` load as written, no note | (c) control |

## Refuting my own test

- **(a) Genuine red? Yes.** Run through the project's C4 runner
  (`engine/scripts/run-verify.sh`, `PDCA_BUNDLE`/`PDCA_WORKTREE` set, under `timeout`).
  Green leg: `Ran 8 tests … OK`. Red leg (production hunks reverted, test kept): `Ran 8
  tests … FAILED (failures=6)`, no import failure, `PDCA-EVIDENCE: C4 PASS — red without
  the fix, green with it`. The 6 reds fail on assertions: (a) extra PR for 11 opened —
  B was built on the line; (a2) same; (b)/(b2) `'11' unexpectedly found in built` with
  base `origin/pdca-integration/main-r…-b11`; (c) `'bogus' != 'stack'`; waves preview
  still prints "builds on the prior's accepted work". The 2 that stay green are the two
  controls, by design.
- **(b) Production path? Yes.** See the not-stubbed list above. The stubbed pieces are the
  model leaves and the `gh` host — what the harness's own peer tests stub.
- **(c) Fixture includes the fault? Yes.** The origin is a real bare repo that accepts a
  pushed integration line: the stack-mode control case sees `pdca-integration/*` on it,
  so "no such branch in `"none"`" is not vacuous. The prerequisite's PR is OPEN in run 1
  (the hold must fire on a real published PR, not a missing one); in (b) a real
  `--no-ff` merge is pushed to origin's main and `gh` reports that merge commit; in (b2)
  `gh` reports MERGED with a merge commit absent from the clone and a head that is not on
  origin/main, so `_base_lacks_merge` really has to fetch and find it missing.
- **Mutation check on (b2).** With the fix applied but the `_base_lacks_merge` call in the
  `"none"` branch disabled (`if False and …` at `flow.py:816`), the C4 runner's green leg
  fails exactly one case, `test_a_merged_prerequisite_the_fetched_base_lacks_still_holds_
  the_dependent` — so (b2) binds the #729 check, not just the merged_into check. File
  restored afterwards; the worktree diff is byte-identical to `patch.diff` (`cmp`).

## Other gates run

- **T3 (`engine/scripts/run-suite.sh`, under `timeout`):** root suite `Ran 50 tests … OK`
  (render + update-compat ran with copier — not skipped; `test_merge_leaves_no_conflict_
  markers` and `test_merged_config_still_loads` pass over the changed `pdca.toml.jinja`);
  driver suite `Ran 2655 tests … OK (skipped=2)` — the 2 skips are elsewhere, none in
  the new file. So (d) holds: stack and merge suites unchanged and green.
- **T2 (`engine/scripts/run-docs-check.sh`):** `lint_docs: OK`, `render_site: link audit
  OK`.
- **Commit-ready:** the target has no pre-commit hooks and no formatter/linter config
  (no `.pre-commit-config.yaml`, no ruff/black settings; CI is render-check, docs-check,
  DCO, workflows). Every added line is ≤ 100 columns, matching the files. DCO sign-off is
  added by publish (`git commit -s`). `git apply --cached --check` of `patch.diff` against
  a fresh `origin/main` index passes.
- Leftover from the mutation check: `.cache/flow.py.keep` (and an unused index path) in the
  worktree's git-ignored `.cache/` — not part of the patch; the harness reclaims the tree.
