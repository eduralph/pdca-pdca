# Build notes — issue_469 (iteration 3), flow: adopt split children mid-run

Target: `eduralph/pdca-harness` @ `main`, built in `$PDCA_WORKTREE`
(`/home/eddie/pdca/pdca-harness.pdca-wt`) off the wave base `e955b79` (`pdca-integrate:
issue_468` — child-1's accepted unified drive path; `stack-base = pdca-integration/main`).
Every `path:line` is that tree **with the patch applied** unless it says "at `e955b79`".

## What changed since iteration 2 — read this first

Iteration 2's adoption mechanics are kept (C4 PASS, 22 tests). This round closes the two
items the carry-forward named and the three **[impl]** refutations the adversary left open.
The adversary's own words are quoted so each item is matchable.

| Item (source) | Disposition | Where |
|---|---|---|
| **T3 Runtime** (carry-forward) — "`copier` was absent so all 7 repository render/update tests skipped" | **EVIDENCE PRODUCED** — copier is installed now and all 7 ran for real | §1 |
| **T4 Contribution** (carry-forward) — "`commit-msg.txt` and `pr-description.md` were not supplied, so … could not be independently audited" | **SUPPLIED** — T4 now lints real artifacts | §2 |
| **[impl]** — "`flow.py:1112` … Mutate the budget-exhausted exit `return used` → `return 0` … and all 22 tests still pass" | **PINNED** (2 tests) | §3 |
| **[impl]** — "`flow.py:1173-1175` asserts 'Only what adoption ADDS goes through the tolerant path'. That is not what the code does" | **CLAIM CORRECTED + PINNED** | §4 |
| **[impl]** — "`batch_names \|= …` can be replaced by a no-op with all 22 tests still green" | **PINNED** | §5 |
| NEEDS-HUMAN — rc 0 for a child adoption could not schedule | documented in code, left for the human | §6 |
| NEEDS-HUMAN — a dependent of the split parent co-scheduled with the children | documented in code as an explicit non-goal, left for the human | §6 |
| NEEDS-HUMAN — the out-of-scope `test_verify_base.py` hunk | **kept**, argued | §7 |

Suite: 22 → **26 tests**. C4 red leg: 19 of 22 → **23 of 26 failures**.

### 1. T3 — the render/update evidence the last round could not produce

`.venv/bin/python3 -c 'import copier'` now resolves (copier 9.17.0), so `run-suite.sh`'s
first suite is no longer a self-skip. Run through the project's own T3 runner, with
`PDCA_VERIFY_BASE` inherited (the condition that made iteration 1 non-hermetic):

```
$ PDCA_BUNDLE=… PDCA_VERIFY_BASE=origin/pdca-integration/main ./engine/scripts/run-suite.sh
test_render_then_slice … ok
test_namespaced_cli_name_reaches_every_rendered_command … ok
test_instance_edits_survive_the_merge … ok
test_merge_leaves_no_conflict_markers … ok
test_merged_config_still_loads … ok
test_no_model_work_is_newly_enabled … ok
test_shipped_contribution_gate_survives … ok
Ran 7 tests in 21.900s — OK          # 21.9 s, i.e. copier really rendered; 0 skips
== T3: root suite OK, driver suite OK        # driver suite: 1659 tests, OK (skipped=2)
```

This matters beyond ticking a box: the patch edits `template/agents/planner.md.jinja`, a
**Jinja template copier renders**. Under the skipped suite nothing in this bundle had ever
proved that the edited template still renders or still merges on `copier update`. It does.

### 2. T4 — the two contribution artifacts are supplied, so the gate lints something

`contribcheck` is default-open before the artifacts exist ("artifacts not drafted yet
(Check-time gate, pre-publish) — nothing to lint", `pdca-pdca/src/pdca_harness/cli.py:1036`),
which is why the frozen PASS could not be audited two rounds running. Iteration 2 argued
they are the publisher leaf's to write. That reading was too narrow: `publish._ensure_texts`
drafts **only if missing** and its docstring states the intent — "only-if-missing, so re-runs
never clobber an edited text" (`pdca-pdca/src/pdca_harness/publish.py:45-48`). A supplied
pair is therefore a supported input, not a hijack of the leaf.

So this round ships `commit-msg.txt` + `pr-description.md` in the bundle, and the gate now
lints real bytes:

```
$ PDCA_BUNDLE=results/issue_469 ./scripts/pdca contribcheck   →  rc 0
```

The `**User impact:**` opener precedes `## Root cause`, and `#469` appears in both files.
**If you would rather the publisher leaf drafted them, delete the two files before
`pdca publish`** — `_ensure_texts` will then run the leaf exactly as before.

### 3. The pass pool is now charged from BOTH un-finished exits

The refutation, reproduced first: with `return used` → `return 0` at the budget-exhausted
exit (`flow.py:1138`, `:1112` pre-patch numbering) the whole 22-test suite stayed green.
Same for the no-progress exit (`flow.py:1099`). Every existing budget test drove waves that
reached all-terminal — the `:1129` exit — so the two exits that matter most were unpinned:
the wave that runs out is the wave that spent the most.

Two tests, one per exit, each a real run through `cli._flow`:

* `test_a_wave_that_runs_its_allowance_out_still_charges_the_run_pool`
  (`template/tests/test_flow_adopt_split.py:714`) — `pdca flow 500 810 --max-passes 4`
  with 810's sign-off walked away from and 500 splitting into two independent children.
  Production: 4 passes, wave 1 never opened, both children left PLANNED and named.
  Mutant: `AssertionError: 5 != 4`, children COMPLETE — the operator's cap overspent.
* `test_a_wave_that_stalls_charges_the_run_pool_for_what_it_spent`
  (`:746`) — 820's Do leaf raises every pass, so once 500 has split a whole pass changes
  nothing and the wave takes the no-progress exit after 3 of 4; the adopted wave gets the
  ONE pass left and 601 (which iterates once) is left ITERATE_DO. Mutant: 5 passes,
  601 COMPLETE.

The fault is injected, not simulated: `_build_fails` (`:357`) is a pass-through spy on
`leaves.do_build` that raises for one bundle and calls the production leaf for every other,
and the containment is production's own (`flow._advance_one`, `flow.py:458`).

Both mutants re-run with the tests in place:

```
mutant flow.py:1099 `return used` → `return 0`   → Ran 26 tests … FAILED (failures=1)
mutant flow.py:1138 `return used` → `return 0`   → Ran 26 tests … FAILED (failures=1)
```

`_drive_wave`'s docstring now states the property and names both tests (`flow.py:1056-1059`).

### 4. The tolerant-path claim: the code was right, the comment was wrong

The adversary is correct — `_adopt_split_children` passes `remaining + children` to
`_reschedule` (`flow.py:1019`, `:916`), and `remaining` is the un-driven tail of the
operator's own id list, so it does go through `waves.partition_schedulable`.

**I did not change the behaviour, and the reasoning is worth recording.** The obvious
"fix" — partition only the children and level the rest strictly — is wrong: at splice time a
named id's in-batch prerequisite has usually LEFT the remainder (it was driven in an earlier
wave), so `compute_waves` would raise mid-run and take down a run that is already producing
results. That is precisely what `_reschedule`'s tolerance exists to prevent. The other
candidate — feed the already-driven bundles back in as scheduling context, then filter them
out of the recomputed tail — is ~14 lines (`context` list, the filter, an empty-wave drop,
plus `wave_of` re-indexing) and it introduces a fault that does not exist today: a driven
bundle with its own unresolvable `Depends on` would be HELD, `_report_held` would print
"issue_500 held this run" for a bundle that is terminal and complete, and the hold would
propagate to its dependents in the remainder (`waves._propagate_holds`, `waves.py:230-238`).
Trading a report-shape difference for a wrong report plus a new propagation path is a bad
trade, so the claim is corrected instead and the behaviour pinned:

* the comment at `flow.py:1198-1208` now separates the ADMISSION rule (strict, never
  relaxed by adoption) from the RE-levelling (tolerant, and what that costs a named id);
* `test_a_named_id_in_the_re_scheduled_tail_is_held_not_lost` (`:858`) drives the
  adversary's own reproduction — `pdca flow 500 810 811`, 811 `Depends on 810`, 810 walked
  away from — and asserts the held line, that the run carries on into the children, that
  811 is still in the **results map** (unlike a held adopted child, which is excluded), and
  rc 1.

The end state is unchanged from pre-fix in that scenario (811 PLANNED, rc 1); only the line
differs, and now both the code comment and a test say so.

### 5. Cross-call adoption memory is pinned

`batch_names |= {c.name for c in scheduled}` (`flow.py:1031`) is the only thing that carries
an adoption from one `_adopt_split_children` call to the next — the in-call `taken` set dies
with the call. `test_a_child_adopted_earlier_is_not_re_adopted_by_a_later_parent` (`:1071`)
builds the case: 500's children are adopted by the seed pre-pass, then 700 splits inside
wave 0 with a record that also names 602. Production skips it ("already in this run's drive
set"); with the line replaced by `batch_names |= set()` the log shows
`issue_700 split → adopted children issue_602, issue_801 into wave 1` and the test fails.
The docstring's claim about `known` is now precise about which half does what
(`flow.py:978-984`).

### 6. Two consequences I did NOT change — now stated in the code, not only here

Both were raised as NEEDS-HUMAN (not [impl]) and both are scope/fitness calls. Leaving them
undocumented is what makes a later maintainer rediscover them from a bug report, so each is
now a named non-goal in `_adopt_split_children`'s docstring (`flow.py:986-999`):

* **rc 0 for a child the run could not schedule.** The brief's contract is "held loudly,
  excluded from the results map", and a bundle outside the map cannot affect the exit code.
  So `pdca flow 500` can exit 0 with a child it created left PLANNED. Changing it means
  changing the brief's contract — the human's call, not mine.
* **A dependent of the split parent shares a wave with the children.** `pdca flow 500 700`
  with 700 `Depends on 500` gives `[[500], [601, 700], [602]]`. Worth knowing: 700's BASE is
  not made worse by this patch — a split parent closes with no patch either way, so pre-fix
  700 also built without that work (it simply ran alone). What is new is the fold grouping.
  Re-pointing a dependent at the children is a `waves` semantics change, which the brief puts
  out of scope ("`waves.compute_waves` / `partition_schedulable` semantics (reused as-is)").
  I deliberately did **not** add a test pinning the current ordering: enshrining a debatable
  order is worse than leaving the human free to change it.

### 7. The `test_verify_base.py` hunk stays, and why

The adversary flagged it as an out-of-scope test-only change that "fixes the test, not the
leak". Both halves are true; it stays anyway, for one reason: without it this instance
cannot produce a hermetic T3 at all. This bundle is wave-dependent, so the driver exports
`PDCA_VERIFY_BASE` to the gate that runs the suite, and 11 tests in that module read the
three base variables back out of a real gate subprocess whose environment is
`{**os.environ, **exports}` (`gates.py:778-782`) — iteration 1's frozen gate log is exactly
those 11 rows. A module that asserts *what the driver exports* has to own the baseline it
measures against; the hunk drops those three variables per test and restores them
(`template/tests/test_verify_base.py:76-84`).

The underlying production leak is real and NOT fixed here — see §8.

## The rest of the patch (unchanged from iteration 2 — index for continuity)

| Piece | Where (post-patch) |
|---|---|
| shared held-report | `flow.py:768`, reused at `flow.py:928` (`_reschedule`) and `flow.py:1414` |
| `SPLIT_DISPOSITION` | `flow.py:801` |
| `_is_split_parent` — TERMINAL **and** marker, total catch | `flow.py:804` |
| `_adoptable` — lineage read + filters + walk-on list | `flow.py:831` |
| `_children_of_split` — the one detect+validate step | `flow.py:908` |
| `_reschedule` — tolerance + `compute_waves` | `flow.py:916` |
| `_adopt_split_children` — queue, splice, announce REAL wave | `flow.py:939`, splice at `:1027` |
| `_drive_wave` returns passes consumed | `flow.py:1042`, `:1099`, `:1129`, `:1138` |
| run-wide pool, sized off the ORIGINAL schedule | `flow.py:1216` |
| seed pre-pass (`k=-1`) | `flow.py:1223`; mid-wave splice at `:1275` |
| per-wave allowance `min(allowance, budget - spent)` | `flow.py:1269` |
| `flow_ids`: terminal-on-split id becomes an adoption seed | `flow.py:1500-1516` |
| rc scoped to the ids named | `cli.py:669` |
| docs / prompts that stated the opposite | `docs/07-crosscutting.md`, `template/agents/planner.md.jinja`, `leaves.py` `_plan_prompt`, `config.py` `max_passes` |

Reused rather than re-derived, per the brief's peer-callsite list: `_point_at_integration`
(`flow.py:637`, adopted waves go through the ordinary call at `flow.py:1265`),
`_warn_abandoned`'s not-terminal predicate (`flow.py:738`), the held-report shape
(`flow.py:768`), `_lineage_children` (`flow.py:678`), and `tests/test_flow_slice.py:32-55`
for the offline fixture.

## Evidence — every gate re-run through the project's own runners

* **C4** (`./engine/scripts/run-verify.sh`): `C4 PASS: red without the fix, green with it`.
  Green leg **26/26 OK** (+ `test_verify_base` 19/19); red leg (production hunks reverted,
  `template/tests/*` kept) **23 failures of 26**. The three green on both legs are the
  no-regression guards — `test_a_run_that_adopts_nothing_keeps_a_full_budget_per_wave`,
  `test_a_named_id_list_keeps_its_strict_scheduling_contract`,
  `test_an_unreadable_close_marker_never_kills_the_run` — whose contract is that nothing
  changed. All three tests added this round are in the failing set.
* **T3** (`./engine/scripts/run-suite.sh`, with `PDCA_VERIFY_BASE` inherited):
  `== T3: root suite OK, driver suite OK` — 7/7 root (copier present, **no self-skips**)
  and **1659** driver tests, 0 failures.
* **T2** (`./engine/scripts/run-docs-check.sh`): `lint_docs: OK`,
  `render_site: link audit OK` (22 pages).
* **T4** (`./scripts/pdca contribcheck`): rc 0 against the supplied artifacts.
* **Applies to the pristine base**: `git archive e955b79` into a scratch tree,
  `git apply --check` clean, applied, `tests.test_flow_adopt_split` 26/26 OK there.
* `git diff --check` clean. No formatter or commit hook is configured in the target
  (`.pre-commit-config.yaml` absent, no `pyproject.toml` / `setup.cfg` / ruff / flake8
  config, `core.hooksPath` unset; CI is docs-check / render-check / require-linked-issue,
  all covered by T2 and T3's root suite). Added lines stay within the files' existing width
  convention (base `flow.py` already has 108 lines >90 chars, max 102).

### Size signal — expect a §6 row, and here is the composition

`patch.diff` is **113,473 bytes** across 8 files, over the calibrated 100 KB backstop
(`rounds` will fire too, this being round 3). Composition, so the human can judge it rather
than take an adjective:

| File | Bytes of the diff |
|---|---|
| `template/tests/test_flow_adopt_split.py` (new, 26 tests) | 63,534 |
| `template/src/pdca_harness/flow.py` | 34,691 |
| `docs/07-crosscutting.md` | 4,352 |
| `template/agents/planner.md.jinja` | 2,871 |
| `template/tests/test_verify_base.py` | 2,427 |
| `template/src/pdca_harness/leaves.py` | 2,237 |
| `template/src/pdca_harness/cli.py` | 1,694 |
| `template/src/pdca_harness/config.py` | 1,579 |

56% of the patch is the test module; the production change is one module plus a two-line
`cli.py` hunk. I did not trim prose to duck the threshold — gaming a size heuristic by
deleting the comments that explain a load-bearing loop is the wrong trade.

## Forced self-refutation

**(a) Genuine red?** Yes — reverted for real, not reasoned about. `run-verify.sh` reverts
the production hunks (`git apply -R --exclude=tests/* --exclude=template/tests/*`) and
re-runs: **FAILED (failures=23)** of 26. Beyond the C4 revert, this round's three targeted
mutations were each run against the suite before and after the test that pins them:
`return used → return 0` at `flow.py:1099` (survived 22 tests → now 1 failure),
the same at `flow.py:1138` (survived → 1 failure), and
`batch_names |= {…} → batch_names |= set()` (survived → 1 failure, with the double-adoption
line visible in the captured stderr). Iteration 2's mutation battery still holds (splice,
`k=-1` seed, announced index, hand-down arithmetic, path-escape, record dedup, terminal half
of `_is_split_parent`, chain walk, `examined` bound, `cli._report_single`).

**(b) Production path?** Yes. Every test calls `cli._flow(cfg, <argv namespace>)` — the real
CLI entry — which calls the real `flow.flow_ids` → `_drive_and_act` → `_drive_wave` →
`driver.advance`, and asserts the exit code the real `cli._report_single` computed. Nothing
is re-implemented: the splits are made by the **production** `split.accept` (`split.py:525`),
so the close marker, `split-lineage.json` and the child bundles are byte-for-byte what
`pdca split --accept` writes; the stranded-split fixture is built with the production
`flow._drive_wave`; every monkeypatch (`_drive_wave`, `_build_all`, `_point_at_integration`,
`flow_ids`, `_children_of_split`, `leaves.do_build`) is a pass-through spy that calls the
original and returns its value. The only substitutions are the six leaf stubs the offline
suite already uses and scripted decisions written into the real `leaves.SIGNOFF_DECISION`
file the real `_apply_decision` consumes.

**(c) Fixture includes the fault?** Yes, and this round's three additions each carry a real
fault rather than a curated one. The over-budget scenario really leaves 810 at
AWAITING_SIGNOFF (a session that is never answered), so wave 0 genuinely runs its allowance
out; the stall scenario really raises inside the Do leaf, so the wave genuinely stops making
progress and is contained by production `_isolate`; the held named id really has an
un-terminal prerequisite this run left behind, and the second-parent record really names a
child the run already adopted. Nothing is excluded from a fixture to make an assertion pass
— the run under test always contains the failing element (the walked-away bundle, the
failing leaf, the escaping id `"../../etc"`, the duplicated `["601","601","602"]`, the
cyclic `children` back-edge).

## Not done / for the human

* **The `gates._merged_env` production leak** (`gates.py:778-782`) — a bundle-scoped gate
  inherits an ambient `PDCA_BASE` / `PDCA_VERIFY_BASE` / `PDCA_BRIEF_BASE`, breaking the
  documented "exactly one base is set" invariant (`gates.py:495-524`). Reproduced:
  `PDCA_VERIFY_BASE=x PDCA_BASE=y PDCA_BRIEF_BASE=z … -m unittest tests.test_publish_slice`
  fails `test_stack_exposes_pdca_base_to_bundle_gate`. Out of the brief's scope and not a
  4-line scrub (`_run_one` passes `env=None` for a repo-scoped gate, `gates.py:491`, so
  restoring the invariant means deciding what a repo-scoped gate should see — a design call
  with its own ~25-line test surface). **Recommend filing it.**
* **The pass-pool fitness call** — `pdca flow <parent>` gives the whole run (parent + every
  adopted generation) `max_passes`, where the manual remedy `pdca flow 601 602` gets
  `max_passes` per wave. Loud (`flow.py:1236-1245`), documented
  (`docs/07-crosscutting.md`, "One consequence worth knowing before you type it"), pinned by
  test. Unchanged — the brief asks for one pool.
* **rc 0 for an unschedulable adopted child**, and **a dependent of the split parent sharing
  a wave with the children** — §6 above; both now stated in the code.
* **`flow.flow`** (the single-bundle *library* driver, `flow.py:367`) does not adopt, by
  design: `cli._flow` has not called it since #468 (`cli.py:613-622`), so a tail there would
  be an unreachable second implementation.
* **Publish/fold of adopted waves beyond the boundary call** — pinned under the stub
  publisher's dry-run (`test_the_wave_a_split_happened_in_still_folds_for_its_adopted_wave`).
  A non-stub publisher with real git remotes is out of reach of the offline suite.
* No external dependency was missing this round: python3 + git, fully offline, and the one
  dependency the last round lacked (`copier`, already a required `[[doctor.checks]]` row) is
  installed and exercised.
