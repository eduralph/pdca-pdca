# Build notes — issue 412 / merge-mode-atomic-merge-group (iteration 4)

Target: `eduralph/pdca-harness @ main`, worktree base `a6af7f3` (`origin/main`). Every
`path:line` below is on the patched tree unless it says "base" or "round 3". Paths are under
`template/src/pdca_harness/` unless they start with `docs/` or `template/`.

I started from round 3's patch (`iteration-v3/patch.diff`, applies cleanly to the same base)
and fixed the seven round-3 findings the carry-forward lists. The brief's design is
unchanged: the field, the up-front refusals, the hold and release at the wave boundary, the
dependents' hold. This round's delta against round 3 is 555 lines added, 231 removed, 218 of
the added lines in the test file.

## The round-3 carry-forward, finding by finding

### 1. An archived sole declarer lost its group (C5) + its regression (T5)

`waves.merge_groups` read only `results/issue_*`. It now reads every bundle name under
`results/` and `results/completed/`, and reads each name once, at the path `member_path`
resolves it to (`waves.py:184-224`). `member_path` is `Config.find_bundle`, so the active
bundle wins over an archived copy of the same name. That is the one place that rule lives
(`config.py:524`); round 3's first draft of this fix had a second copy of it in the loop,
which I removed.

The finished-member path already resolved archived members (`waves.member_path`,
`merged.merged_into` → `find_bundle`), so once the declaration is seen, the archived A is
held at D's boundary and released with B, A first.

Tests:
- `test_an_archived_sole_declarer_still_binds_its_partner` (`template/tests/test_merge_group.py:859`):
  the reviewer's case (A finished, sole declarer, moved to `completed/`; `pdca flow B C D`).
  Before: B merged alone, no group line, rc 0.
- `test_an_archived_copy_of_an_active_bundle_declares_nothing` (`:880`): a guard, green
  both ways. A stale archived copy declares `Merges with: B`, the active A does not, and B
  `Depends on: A`. With the wrong precedence the run would be refused as a chained group.

### 2. The deadlock check got a conflict pair's build order wrong (C5, both directions) + regressions (T5)

Round 3's `_wait_edges` decided which side of a `Conflicts with` pair is built first from
`Depends on` edges only, and only when the name-lower side was a group member. The
scheduler (`compute_waves`) also counts the conflict edges it added for earlier pairs, so it
can build the name-higher side first.

I took the reviewer's fix: one shared function. `_build_order` (`waves.py:478`) is the
orientation loop that used to sit inline in `compute_waves` (base `waves.py:200-212`),
moved unchanged. `compute_waves` now calls it (`waves.py:537`), and so does `_wait_edges`
(`waves.py:357`). `_wait_edges` reads each pair's direction off that order
(`waves.py:358-362`: `first` is the side the other reaches) and adds a wait edge from the
later side to the first side when the first side is a group member. Edges into a member
finished on disk are kept as before (`waves.py:363-372`).

`group_refusals` and `_wait_edges` now take the batch's paths instead of names
(`waves.py:235`, `waves.py:335`), because the order needs `conflict_map(cfg, bundles)`, the
same call `compute_waves` makes. The two callers pass their bundles (`waves.py:158`,
`waves.py:679`).

Tests, each through `cli.main(["flow", …])`, and each first asserting the real wave plan
(`_plan`, `:500`, read in stack mode where the field is ignored):
- `test_a_group_that_waits_for_itself_in_the_order_the_scheduler_builds_is_refused` (`:693`):
  the reviewer's case (A/E group, waves [E] [B] [C] [A]). Before: built, rc 1. Now rc 2,
  `Ways out:`, nothing built, no `gh` call.
- `test_a_group_waiting_through_a_pair_an_earlier_pair_ordered_is_refused` (`:708`): the
  adversary's K/L case (waves [K] [F] [G] [H] [L]). Before: built, rc 1. Now rc 2.
- `test_a_group_that_works_in_the_order_the_scheduler_builds_is_not_refused` (`:725`): the
  adversary's H/L case, plus Z `Depends on: H` so H's wave has a boundary (waves [K] [F, L]
  [G] [H] [Z]). Before: refused, rc 2. Now rc 0: L is held at its boundary, then L and H
  merge together, L first, before Z builds.

### 3. A member an earlier run finished was merged into whatever base its old PR targets

Two parts.

**Merging it.** `merge_wave` takes a new `opened` argument, the bundles whose PR this run
opened (`merge.py:133`). The flow passes `pushed`, the bundles whose publish wrote a record
this run (`flow.py:3192`, `flow.py:3272`). For a member not in `opened`, `group_blocker`
asks `_foreign_refusal` first (`merge.py:243`). That function (`merge.py:252-282`) lets the
PR through only if merge mode's own publish could have opened it: a `new-pr` record, in its
brief's repo, on a base `publish._merge_base_refusal` (#411) does not refuse. That is the
check the adversary pointed at, called, not copied. A `stacked-pr` record is refused too: it
is either a legacy `Stacks on` PR onto a parent's branch, or a stack-mode wave > 0 PR whose
branch was cut from the run's line and carries other bundles' work (integrate reads such a
record the same way, `integrate.py:971-972`). Refused means the whole group is held, with
the reason on the hold line and at the end of the run.

**Counting it as landed.** `flow._groups()` used `merged.is_merged`, which answers "did the
PR merge?" into whatever it targeted. A PR merged into `fix/P` counted as landed, and B then
merged alone into main. It now uses `merged.merged_into` with the member's own target
(`flow.py:2999-3008`), the rule `_runnable` already uses for a merged prerequisite
(`flow.py:820`).

The module docstring's rule "merge mode readies and merges only a PR this run opened" now
names this one exception and its condition (`merge.py:86-88`, `merge.py:94-104`).

Tests (`:895-951`): `_foreign_member` finishes A with a chosen record, then runs
`pdca flow A B C D`. In every case neither A nor B is readied or merged, D merges, C is held
(its prerequisite B waits for the group), and the end line names A's PR.
- `…_whose_pr_targets_another_bundles_branch_holds_the_group` (`:926`): `stacked-pr` on
  `fix/P`, the adversary's case. Before: A merged into `fix/P`, B into main, rc 0.
- `…_whose_branch_was_cut_from_a_stack_mode_line_holds_the_group` (`:932`): `stacked-pr` on
  `main`.
- `…_on_a_branch_another_bundle_produced_holds_the_group` (`:938`): A's brief and its
  `new-pr` record both target P's fix branch (route 2 of `_merge_base_refusal`).
- `…_merged_into_another_branch_has_not_landed` (`:945`): A's `stacked-pr` PR merged into
  `fix/P`. Before: counted as landed, B merged alone.

### 4. `merge._member` copied `waves.member_path`

Removed. `group_blocker` and `_back_to_back` call `waves.member_path` (`merge.py:228`,
`merge.py:297`). `merge.py` now imports `waves`; `waves` imports nothing from `merge`, so
there is no cycle.

### 5. `_unmergeable` re-implemented `_merge_one`'s refusals, with an order gap

I took the reviewer's larger suggestion: one function both call. `_premerge`
(`merge.py:642-722`) holds everything `_merge_one` decides before its first `gh` call that
changes anything, in its order: not COMPLETE / no patch → skip; no PR → refuse; `Onto
branch` record → refuse; dry run → skip (plan printed); PR already merged → skip;
malformed `expected_checks` → stop; no repo under `merge_requires != "required"` → refuse.
`_merge_one` acts on it (`merge.py:729-731`). `group_blocker` asks it silently (`say=False`)
for every member before the first is readied (`merge.py:245`). `_unmergeable` is gone.

So the gap closes by construction: an already-merged PR is skipped before the repo check, in
both places. The `stop` verdict (a setting that refuses every PR alike) does not hold the
group. It is left to `_merge_one`, which stops before readying the group's first member,
as round 3 did and `test_a_malformed_expected_checks_…` (`:393`) still pins.

One behaviour change outside groups: the "record names no repo" refusal used to happen
after `gh pr ready` and then undo the ready-mark (base `merge.py:543-545`). It now happens
before the ready-mark (`merge.py:715-721`). Same STOP, same message text (`_refusal`,
`merge.py:628`), but no ready / undo pair. I probed it: rc 1, the only `gh` call is the
`gh pr view` of the merged check. No existing test covered that path. The other messages
are byte-identical: I compared every `print` argument of base `_merge_one` / `_refuse`
against the new functions with `ast.unparse`.

Test: `test_a_member_merged_by_hand_whose_record_names_no_repo_holds_nothing` (`:409`),
under `merge_requires = "all"`. A human merges D's PR as it opens and A's and B's once B is
built (a new fixture hook, `hand_merges`), and B's record names no repo. Round 3 held the
group forever and never built C. Now nothing is held, C is built, rc 0. The bare base fails
it too (A is readied at wave 0 and the base read has no checkout, so the run stops).

### 6. Exit code for a group whose PRs end as drafts

I kept the behaviour and wrote down the rule on purpose, in the three places that state the
exit code: the `_drive_and_act` docstring (`flow.py:2812-2822`), `cli._results_rc`
(`cli.py:725-728`), and `docs/07-crosscutting.md:918-923`. The rule: `"group"` (exit 3)
marks exactly a PR a boundary would have merged and held instead. So the base the run ends
on lacks work a run without the field would have landed, whatever happened later. A group
wholly in the final wave holds nothing, since merge mode leaves every final-wave PR a draft,
group or not. That run ends as it would without the field (exit 0). The existing tests at
`:433` (rc 0) and `:450` (rc 3) pin both.

## Other changes this round

- **A missing brief is guarded** in the two new target reads (`flow.py:3001-3003`,
  `merge.py:271-273`). A split parent can be COMPLETE with its brief gone (`state.py:345-350`,
  #481), and `publish._resolve_target` raises on a missing brief. With no brief there is no
  target: `merged_into` then counts any merge (its documented behaviour), and
  `_foreign_refusal` refuses (fail closed).
- **`_foreign_refusal` skips a bundle with no patch** (nothing to merge), as `_premerge` does.
- **`merge_wave` judges each group once per call** (`judged`, `merge.py:167-175`). Round 3
  asked once per member. The answer now includes a `gh pr view` per member (the merged
  check), so asking twice would double those calls.
- **Docs**: `docs/07-crosscutting.md:888-907` (archived declarations; the earlier-run PR
  rule), `:918-923` (exit code), `:938-940` (the conflict order is the scheduler's);
  `docs/03-plan.md:103-105` (the earlier-run PR condition). The brief template line is
  unchanged.

## Ruled out, with what each would have cost

- **Patching round 3's `_wait_edges` in place** (add the edges oriented for earlier pairs
  to its `ordered` map, and handle a member on either side of the pair). About the same
  size, roughly 8 changed lines, but it leaves two copies of the orientation loop that can
  drift. The reviewer asked for one shared function, and the drift is the bug being fixed.
  So the deciding point is the one-copy rule, not size. The shared version is 28 lines
  (`_build_order`, mostly the moved loop and its comment) plus 6 in `_wait_edges`, and
  `compute_waves` loses 13.
- **Refusing a member an earlier run opened up front**, in `check_dep_graph`. It would save
  building the rest of the group, but whether that PR has already merged into its target
  needs a host call (`merged_into`), and `check_dep_graph` makes none. A stack-mode wave > 0
  PR that a human already merged into main (a `stacked-pr` record on `main`, MERGED) would be
  refused although the group is fine. Holding at the boundary asks the host first.
- **Applying the earlier-run PR check to every member**, dropping `opened` (about 6 lines
  fewer). It would also hold a member this run published as a fork + legacy `Stacks on`
  (a `stacked-pr` record on the target base), which merge mode merges today. That is a
  behaviour change for no gain: publish's #411 guard already checked this run's records.
- **Keeping `_unmergeable` and adding a test that ties it to `_merge_one`** (the reviewer's
  smaller step, about 15 test lines). It keeps two copies, and closing the merged-PR gap
  would need an `is_merged` call inside `_unmergeable`, a third place that encodes the
  order. `_premerge` deletes `_unmergeable` (22 lines) and moves about 45 lines out of
  `_merge_one`, which shrinks by the same amount.
- **Keeping the no-repo refusal after the ready-mark** in `_merge_one` and teaching
  `_premerge` that it "will be refused later". That splits one check across two places
  again. Moving it before the ready-mark only drops a ready / undo pair before the same
  STOP.
- **Changing an exit code instead of documenting it** (make a wholly-final-wave group exit
  3, or a held-then-final group exit 0). Either changes a tested behaviour, and the
  reviewer accepted either rule if stated on purpose.
- **Keeping the relation across archival in a sidecar file** written when a bundle is
  archived. Archiving to `completed/` is a manual convention (#171, `config.py:524-535`);
  there is no step that runs at archive time to write it. Reading `completed/` is the only
  way to see an archived declaration.

## Known limits (not changed)

- **A dry run still judges no record**, the earlier-run PR rule included (`merge.py:237-238`).
  It asks the host nothing, so it cannot tell whether such a PR already merged into its
  target, and either answer could mislead. Same as round 3's documented limit for finished
  members. Probed: a dry run with a `stacked-pr` finished member rehearses the release, no
  `gh` call, rc 0.
- **`merged_into` reads the recorded base.** A PR that a human retargets to main and then
  merges still reads as "merged into `fix/P`", so the run keeps holding its group. The end
  line says to merge the group together by hand, or drop the edge. That is the harness's
  rule everywhere (`_runnable`, the fold), so I kept it.
- **A PR closed by a human during the run** fails at `gh pr ready` during the release. The
  release goes earlier-run members first, then held members, then this wave, so a held
  member's closed PR stops the run before anything lands. A later member's closed PR would
  land the group in part. That is a host-side state, in the window the brief's Impact
  section accepts.
- **Seen, not group-specific, not changed:** in merge mode a COMPLETE bundle whose publish
  failed this run but which has a record from an earlier attempt is merged from that old
  record (`_merge_one` reads whatever `publish.json` holds). For a group member that record
  now also goes through the earlier-run PR check, since it is not in `pushed`.
- Round 3's limits stand: symlinked bundle aliases, an unreadable brief's declaration, a
  group whose members are all finished and none driven or named.

## Deferred items this round touches (for the human, not build work)

- **Stale declarations can veto a run** (code review, deferred). Reading `completed/`
  extends that to archived briefs: an archived DISCONTINUED bundle that declares
  `Merges with: A` makes `pdca flow A` exit 2, "names issue_X (DISCONTINUED), which ended
  without completing", same as an active one (probed). The rule is consistent with the
  active case; whether either should veto is still the human's call.
- **A split member lets its partner land alone** (adversary, deferred): unchanged.

## Open question carried from the brief (maintainer)

The motivating wyrd pairs are chained. This design refuses them in merge mode (make them one
bundle, or use stack mode). Built as written; alternative A is not attempted.

## Test — `template/tests/test_merge_group.py` (41 cases)

The test imports only modules (`cli, driver, flow, leaves, merge, publish, signoff, split,
state, waves`), never a new symbol. A copy is in the bundle at
`template/tests/test_merge_group.py`, byte-identical to the patch's.

It drives the real code: `flow._drive_and_act`, `flow.flow_batch`, `cli.main`;
`merge.merge_wave` → `group_blocker` → `_foreign_refusal` / `_premerge` → `_merge_one` →
`merged.is_merged`; `merged.merged_into`; `waves.check_dep_graph` → `group_refusals` →
`_wait_edges` → `_build_order`; `split.accept` → `_adopt_split_children` → `_reschedule`;
and `driver._archive_iteration`. Stubbed: the build / sign-off leaf (`flow._drive_wave`
writes a patch, signs off, writes `publish.json`), `flow._publish_bundle`,
`publish.draft_texts`, `leaves.do_plan_batch`, `merge._sleep`, and `gh` (a recorder in
front of `subprocess.run`; every non-`gh` call runs for real). The publisher is in
`command` mode, so these are not dry runs.

New fixture hooks this round: `records` (fields a bundle's publish record differs in),
`no_repo`, `hand_merges`, `_brief(target=…)`, and `_plan` (the real wave plan).

| Finding | Test |
|---|---|
| r3-1 archived declarer | `test_an_archived_sole_declarer_still_binds_its_partner`, guard `test_an_archived_copy_of_an_active_bundle_declares_nothing` |
| r3-2 conflict order, missed deadlock | `…_waits_for_itself_in_the_order_the_scheduler_builds_is_refused`, `…_waiting_through_a_pair_an_earlier_pair_ordered_is_refused` |
| r3-2 conflict order, false refusal | `test_a_group_that_works_in_the_order_the_scheduler_builds_is_not_refused` |
| r3-3 earlier-run PR | the four `test_a_finished_member_…` cases at `:926-951` |
| r3-5 merged-PR gap | `test_a_member_merged_by_hand_whose_record_names_no_repo_holds_nothing` |
| r3-4, r3-6 | no behaviour to test (a dedupe; a docstring); r3-6's two rc cases stay pinned at `:433`, `:450` |

The 31 round-3 cases are kept unchanged.

### Refuting my own test

- **(a) Genuine red? Yes.**
  - The project's C4 runner (`engine/scripts/run-verify.sh`, with `PDCA_BUNDLE` and
    `PDCA_WORKTREE` set) on the final tree: green leg 41/41 OK; red leg (production hunks
    reverted in place) `FAILED (failures=37)`, all assertion failures, no `_FailedTest` or
    import error. Verdict `PDCA-EVIDENCE: C4 PASS`. Log: `results/issue_412/build-c4-run.log`.
  - The 4 cases green on both legs are the declared guards: stack mode unchanged (e), the
    malformed `expected_checks`, the already-merged finished member, and the new archived
    copy guard. The two edited test-double modules are green on both legs, as they should be.
  - I also ran the final test file against **round 3's** production code (round 3's source
    files over the same tree). The 9 new red→green cases fail, every one on an assertion,
    and each on its own gap: the foreign cases on A's `gh pr ready`, the two deadlocks on
    rc 1 instead of 2, the false refusal on rc 2 instead of 0, the no-repo case on C not
    built, the archived case on the missing hold line. The other 32 pass there.
  - After every swap the worktree went back to exactly base + `patch.diff` (checked with
    `cmp` against `git diff a6af7f3`).
- **(b) Production path? Yes.** The cases run the real driver, CLI, wave planner, merge
  boundary and split adoption. None of the group logic, the ordering, the record checks or
  the merged checks is mocked. Only the model leaves, the publish mechanics and the host are
  stubbed.
- **(c) Fixture includes the fault? Yes.**
  - The archived declarer really lives in `results/completed/issue_A` (the bundle dir is
    renamed there), and nothing else declares the group.
  - The deadlock and false-refusal batches are ones the real scheduler orders against name
    order; each test asserts that plan first.
  - The earlier-run members carry real `publish.json` records with the faulty mode / base,
    or a brief that targets another bundle's real published branch (P's record names
    `fix/P`). The merged-elsewhere case reads MERGED from the stubbed host.
  - The no-repo record really lacks `repo`, and `merge_requires` really is `"all"`.
  - Every `gh` call is recorded; none is filtered out.

## Other checks run

- **T3**, `engine/scripts/run-suite.sh` on the final tree: root render / update suite
  `Ran 24 tests … OK` (copier present, the render cases ran, nothing skipped; the changed
  `brief.md.tpl` renders); driver suite `Ran 2671 tests … OK (skipped=2)`;
  `PDCA-EVIDENCE: root suite OK, driver suite OK`. Log: `results/issue_412/build-t3-run.log`.
- **T2**, `engine/scripts/run-docs-check.sh`: `PDCA-EVIDENCE: docs lint clean, site render +
  link audit clean` (22 pages).
- **C5 prod-path**, `engine/scripts/run-prod-path.py`: `1 added driver-suite test(s) import
  the production package 'pdca_harness'`.
- **Ad-hoc probes** (run through the test file's own fixture, not added to it): the sweep
  on the H/L batch runs it whole (L merged before H, no holds); a dry run with a
  `stacked-pr` finished member (no `gh` call, rc 0); an archived DISCONTINUED declarer (rc 2,
  "ended without completing"); the no-repo refusal outside any group (rc 1, no ready-mark).
- **Commit-readiness.** The target has no Python formatter, linter config or pre-commit
  hooks (no `.pre-commit-config.yaml`, no `pyproject.toml` at the root, no ruff / flake8 /
  black in `.github/workflows/`). Its CI runs the docs lint and the render check, both run
  here. `git diff --check` is clean, and no added Python line is over 100 columns. The one
  long line is the template field line (`template/templates/brief.md.tpl:34`), unchanged
  from round 3 and matching the field lines around it.

## Housekeeping

I wrote nothing outside the worktree and the bundle. To track this round's delta I used two
temporary commits in the worktree (round 3's patch, then this round). Before hand-off I
reset them away (`git reset a6af7f3`), so the worktree is the base with the patch
uncommitted, as the harness expects. The probes ran inside the test fixture's own temp
directories, which its cleanup removed. The C4 and T3 logs in the bundle replace round 3's.

No external dependency beyond what the brief lists (none) was needed.
