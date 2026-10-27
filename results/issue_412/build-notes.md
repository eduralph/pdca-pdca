# Build notes — issue 412 / merges-with-field-refused-in-merge-mode

Target: `eduralph/pdca-harness @ main`, base `a6af7f3` (= `origin/main`), built in the
worktree `/home/eddie/pdca/pdca-harness.pdca-wt-l1`. Line numbers are on the patched tree
unless marked "base". No hold, carry or release logic from iterations v1–v4 is in this patch
(I did not read those iterations); nothing in criteria (a)–(f) needed it.

## What changed, and why each piece is there

1. **Parser** — `template/src/pdca_harness/brief.py:227-235`, new `merges_with()`. Same
   shape as `conflicts_with` (base `brief.py:218-224`): `field(bp, "merges with",
   "merges_with")` through `_id_list` (base `brief.py:347`). That gives the criterion's
   parse rules for free: ids only on the value line, a trailing note ignored, `#12` / `12` /
   `issue_12` all read as `12`, and an unfilled template placeholder / `none` / `—` read as
   no ids.
2. **Group finder** — `template/src/pdca_harness/waves.py:170-196`, `merge_groups(cfg,
   bundles)`. Reads `Merges with` from the briefs in the run and joins declarer and named id
   into one group (a small union-find over bundle names), so either side's declaration binds
   both, as `conflict_map` (base `waves.py:136`) reads `Conflicts with` symmetrically. One
   deliberate difference from `conflict_map`: a partner **outside** the run is kept, not
   dropped. Criterion (b) needs that ("A alone, `Merges with: X`, X not in the run" must be
   refused), and it is the right call: the member this run would merge still lands without
   its partner.
3. **Strict refusal** — `waves.py:144-156`, at the end of `check_dep_graph` (base
   `waves.py:65`). Under `cfg.wave_mode == "merge"` (the comparison every other module uses:
   `flow.py:3080`, `publish.py:293`) a run with any group raises `DependencyGraphError(message,
   remedy=…)` (base `waves.py:51`). It sits after the existing dependency and cycle checks,
   so a batch those checks already refuse keeps exactly the message it gets today. Both
   strict callers go through `compute_waves` → `check_dep_graph` (`waves.py:248`): `pdca flow
   <ids>` (`flow.py:2855`, turned into rc 2 + `Ways out:` by `cli.py:673-679`, unchanged)
   and `pdca waves` (`cli.py:1095`, `unschedulable:` + rc 1, unchanged).
4. **Shared wording** — `waves.py:159-167`: `_GROUP_WAYS_OUT` (the two ways out: set
   `wave_mode = "stack"`, or fold the group into one bundle) and `_group_text`
   (`issue_A + issue_B`, an out-of-run name marked `(not in this run)`). One string for both
   paths, so the refusal and the hold cannot drift apart.
5. **Tolerant hold** — `waves.py:377-385`, in `partition_schedulable` (base `waves.py:275`),
   under merge mode: every in-run member is held with a reason naming `Merges with`, the
   group, and the two ways out. Placed before the first `_propagate_holds` (now `:389`, base
   `:313`), so the existing fixpoint holds the members' dependents with no new code. If a
   member is already held on an unresolved dependency, the two reasons are joined, so the
   operator sees both problems in one run. The remainder still levels in `compute_waves`
   without raising: a bundle left schedulable cannot be a member of the remainder (its own
   declaration, or the declaration naming it, would have held it).
6. **Docstrings** — module (`waves.py:23-26`), `check_dep_graph` (`:87-89`), `compute_waves`
   (`:244-245`), `partition_schedulable` (`:350-355`).
7. **Template** — `template/templates/brief.md.tpl:34`, right after `Conflicts with` (`:33`).
   It says to declare the field on every member, that it changes no wave, and what merge mode
   does. I left out a "docs NN" pointer: in a rendered instance "docs 07" would resolve to
   `PCDA/quality-cycle/07-case-study-ci-hardening.md`, the wrong document. It says
   `flow <ids>`, not `pdca flow <ids>`, because a rendered instance can rename the CLI (this
   one is `pdca-pdca`).
8. **Docs** — `docs/03-plan.md:97-106` (new bullet in the optional-fields list) and
   `docs/07-crosscutting.md:887-901` (end of the `"merge"` bullet, base `:858-886`). Between
   them they say: declare it on every member; stack mode is unaffected; merge mode refuses
   groups for now, single-wave ones too and why; the two ways out; the `--from-csv` sweep
   holds the group and its dependents; bare `pdca waves` refuses where the sweep holds (the
   accepted divergence from (f)); and the two #778 gaps (a group declared only outside the
   run is not seen; a split does not carry the field to children).

Not touched, per Scope: `merge.py`, `flow.py`, `config.py`, `cli.py`, `split.py`.

## Criterion → test (`template/tests/test_merge_group.py`)

| Criterion | Test | Production path driven |
|---|---|---|
| field parses like `Conflicts with` | `MergesWithField.test_parses_like_conflicts_with` | `brief.merges_with` vs `brief.conflicts_with` on the same values (got via `getattr`, so the red leg fails on an assertion, not an `AttributeError`) |
| (a) | `MergeModeStrict.test_a_declares_the_group`, `test_every_id_spelling_names_the_partner` | `waves.compute_waves` |
| (b) | `test_only_the_partner_declares_the_group`, `test_a_run_of_one_member_whose_partner_is_not_in_the_run` | `waves.compute_waves` |
| (c) | `FlowRefusesAGroup.test_flow_refuses_with_rc2_and_builds_nothing` | `cli._flow` → `flow.flow_ids` → `compute_waves` (`flow.py:2855`) → `cli.py:673-679` |
| (d) | `MergeModeTolerant.test_holds_the_group_and_its_dependent_and_keeps_the_rest` | `waves.partition_schedulable` (+ `compute_waves` on the remainder) |
| (e) | `StackModeUnchanged.test_same_result_as_without_the_field` | both, stack mode, with vs. without the lines, batches (a), (b), (b out-of-run), (d) |
| (f) | `WavesPreviewRefusesAGroup.test_bare_waves_reports_the_group_unschedulable` | `cli.main(["waves"])` → `Config.load()` of a temp `pdca.toml` with `[driver] wave_mode = "merge"` → `cli._waves` → `compute_waves` (`cli.py:1095`) |

The module imports only modules (`from pdca_harness import brief, cli, driver, state, waves`
plus the pre-existing `config.Config` / `LeafConfig`), never a symbol the patch adds. (c) copies
the setup of `test_flow_dependency_refusal.py:34-53, 74-83, 91-104`, adding only
`wave_mode="merge"`. (f) follows the `os.chdir` + temp `pdca.toml` shape of
`test_state_resolved.py:425-433`, and drops `PDCA_BUNDLE_ROOT` from a patched environment so
a gate's environment cannot point `results/` elsewhere.

## Evidence (all through the project's own runners)

**C4** — `PDCA_BUNDLE=…/results/issue_412 PDCA_WORKTREE=…/pdca-harness.pdca-wt-l1
./engine/scripts/run-verify.sh` from the instance root:

- green leg: `Ran 9 tests … OK`.
- red leg (production hunks reverted, test kept): `Ran 9 tests … FAILED (failures=11)`. Every
  failure is an assertion (`FFFFFFFFFF.F`; the counts include sub-tests), none an import
  error. The one `.` is (e), green on both legs as the brief intends.
- verdict line: `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`, exit 0.
- What the red leg showed is the defect itself: `compute_waves` returned `[['issue_A',
  'issue_B']]`; `partition_schedulable` scheduled all of `A, B, C, D`; `pdca flow A B` returned
  0 after running Do → Check → SUMMARY on both bundles; bare `pdca waves` returned 0 and
  printed `wave 0: A, B, D`.
- After the run the worktree diff is byte-identical to `patch.diff` (`git diff | cmp`).

**T2** — `./engine/scripts/run-docs-check.sh`: `lint_docs: OK`, `render_site: … link audit
OK` (covers the two new cross-links `07-crosscutting.md#waves-in-execution` and
`03-plan.md#ordering-and-routing-the-batch`).

**T3** — `./engine/scripts/run-suite.sh` (root render suite + offline driver suite), on the
final patch, run alone: root suite `Ran 24 tests … OK` with no test skipped (copier imports in
`.venv`), driver suite `Ran 2639 tests … OK (skipped=2)`, verdict `PDCA-EVIDENCE: root suite
OK, driver suite OK`, exit 0. (An earlier T3 run overlapped a C4 run, whose red leg reverts
the fix in the shared worktree for a moment; it passed too, but I re-ran T3 alone so this
evidence is not in doubt.)

**Commit-ready**: the target has no formatter or pre-commit hook (`.git/hooks` holds only
samples, no `core.hooksPath`, no ruff/black/flake8 config). Its CI runs the docs lint/render
(`docs-check.yml`) and the render suite (`render-check.yml`), both covered above. `git diff
--check` is clean, no line over 100 characters. Commits need a DCO `Signed-off-by` (publish's
job).

## Refuting my own test

- **(a) Genuine red? Yes.** The C4 red leg reverted the production hunks (`brief.py`,
  `waves.py`, the template, the docs) with the test in place and got 11 assertion failures
  across 8 of 9 tests; the 9th is (e), meant to be green on both legs.
- **(b) Production path? Yes.** Every case calls production entry points: `waves.compute_waves`,
  `waves.partition_schedulable`, `cli._flow` (the function `pdca flow` dispatches to) and
  `cli.main(["waves"])` with a real `Config.load()`. Nothing under test is mocked. The only
  wrapper is the build counter around `driver.run_issue`, and it still calls the real one; on
  the red leg it recorded both builds.
- **(c) Fixture includes the fault? Yes.** The batches hold the group members next to an
  unrelated bundle (D) and a dependent (C), merge mode is set through the real config field
  (and, for (f), through a real `pdca.toml`), and the red leg shows that fixture reproducing
  the defect: both members built, the preview levelling them into one wave.

## Alternatives I ruled out

- **Group check in `compute_waves` instead of `check_dep_graph`.** The brief points at
  `check_dep_graph`; it is already the "refuse before any build" step, and `compute_waves`
  calls it first (`waves.py:248`), so both strict callers are covered either way.
- **A name → partners map like `conflict_map`** instead of groups. One A↔B pair would then
  read "issue_A merges with issue_B; issue_B merges with issue_A". The groups cost 13 lines
  (`waves.py:180-196`: `root` plus two loops) and name each group once (`issue_A + issue_B`),
  which also handles A→X←B (two run members tied through one outside id) as one group.
- **Dropping out-of-run partners**, as `conflict_map` does. Fails criterion (b).
- **Refusing at the wave boundary in `flow.py`.** Out of scope, and too late: the builds
  have already happened.

## Things the human should know at sign-off

- **`pdca run <id>` is outside both paths.** It goes straight to `driver.run_issue` without
  any wave planning (`plan_policy.py:17`), so in merge mode it will build a group member.
  It never merges anything: the only call to `merge.merge_wave` is `flow.py:3081`. The PR it
  leaves open has the same exposure as the documented out-of-run gap (#778): a later run
  that does not name it does not see the group. The brief's invariant names only the strict
  and tolerant wave-planning paths, so I left `pdca run` alone.
- **Wording left stale in `flow.py`** (out of scope): `flow.py:3338` "nothing schedulable —
  every in-flight bundle is held on an unresolved dependency or a cycle" is now incomplete
  when the holds are group holds. Each held bundle still gets its own line carrying the
  `Merges with` reason (`_report_held`, `flow.py:1793-1795`), so the reason is not lost.
  A one-line follow-up.
- **`pdca waves` shows no ways-out line.** `cli.py:1096-1098` prints only the message, as it
  already does for every refusal; criterion (f) asks for exactly that. `pdca flow` prints
  both ways out.
- **Edge cases, decided toward refusing:** a brief that names itself (`Merges with: A` in A)
  is a group of one and is refused in merge mode, since the rule is "its own brief declares a
  non-empty `Merges with`". A member whose out-of-run partner is already COMPLETE or merged is
  still refused; (b) requires that.
- **Publish:** this delivers the field and a fail-safe only, so the PR must say `Refs #412`
  and `Refs #778`, never `Fixes #412` (brief, Scope).
