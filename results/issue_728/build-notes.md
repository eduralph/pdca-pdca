# Build notes — issue 728 / flow-carry-through-patchless-finished-bundles

Target: eduralph/pdca-harness, base `c423f9d` (#727 folded on `pdca-integration/main-r547f8028520f`).
Worktree `$PDCA_WORKTREE` = `/home/eddie/pdca/pdca-harness.pdca-wt`, HEAD `c423f9d`, the patch
applied on top. Line numbers below are on the PATCHED tree unless marked "base".
`$PDCA_VERIFY_BASE` was empty in my shell; the worktree HEAD is `c423f9d`, the same commit
as this bundle's `stack-base-tip` file, so that is the base everything was built and run on.

The old `test_flow_carried_prereq_bases.py` in the bundle directory (from the rejected wider
scope, iterations v1-v4) is replaced by the new test of the same name. Nothing from
`iteration-v1..v4/` was read or reused.

## What changed (one production file)

`template/src/pdca_harness/flow.py` — the re-issue carry (`_carry_finished`) now treats a
finished named id with no patch as a node of the graph, for all three of its decisions:

1. **New walk `_reached`** (`flow.py:1182-1204`). From a bundle, follow plain `Depends on`
   edges. Stop at an id in `stops` (and record it, with the patchless ids passed on the way).
   Continue only through ids in `through` (finished named ids with no patch). Ignore every
   other edge. Breadth first, a `seen` set (`:1192`) so a cycle between patchless ids ends.
   For a brief with direct edges only, the result is the same list, in brief order, as the
   old loops built (`:1195`: the start's own edges are walked first).
2. **Which finished ids get carried for which dependents** (`flow.py:1290-1295`, replacing
   base `:1254-1259`). `bare` = the run's `finished` ids with no patch (`integrate._has_patch`,
   the predicate `_runnable` already uses at `flow.py:788`). The dependents map is built
   with `_reached(cfg, b, cands, bare)`, so `D → N → A` records `D` under `A` and triggers
   A's target. The "is not carried … holding …" line (`:1379-1382`, unchanged) then names `D`.
3. **Which finished ids are not clean** (`_cascade_not_clean`, `flow.py:1207-1234`; call at
   `:1324`, base `:1287`). Each id's prerequisites now come from `_reached(cfg, d, names,
   through)` (`:1219`), so `P → N → A` with `A` not clean makes `P` not clean, cause `A`.
   The reason text is unchanged for a direct edge ("its `Depends on` names X, whose work its
   branch carries"); through a patchless id it reads "its `Depends on` reaches issue_A, whose
   work its branch carries, through issue_N (finished with no patch)" (`:1227-1231`). The
   `built_on` hint is reused with `cause = A` ("issue_P was built on issue_A … get issue_A
   carried, or re-drive issue_P on a base without it"). `through` defaults to `None` (direct
   edges only), so the old behaviour is one argument away.
4. **Which dependents wait** (`flow.py:1383-1387`, new, after the per-target loop). A
   patchless id that reaches (through patchless ids) a candidate now in `held` goes into
   `held` too. It prints nothing: the "is not carried" loop (`:1370-1382`) still runs over
   the fold candidates only. `_runnable` then holds its plain `Depends on` dependents with
   the code that is already there (`flow.py:803-806`, unchanged; the call site
   `:2671` passes `held_unpushed | held_finished | …`). In a dry-run nothing is held
   (candidates are never put in `held` there), so this adds nothing.
5. Docstrings: `_cascade_not_clean` (`:1209-1217`) and `_carry_finished` (`:1244-1245`,
   new last paragraph `:1279-1287`) say so; one comment at `:1321-1323`.

Where each change sits, base `c423f9d` → patched (`template/src/pdca_harness/flow.py`):

| Change | Base `c423f9d` | Patched |
|---|---|---|
| new `_reached` | inserted before `:1182` | `:1182-1204` |
| `_cascade_not_clean`: signature, docstring, prereqs via `_reached`, reason text | `:1182-1209` | `:1207-1234` |
| `_carry_finished` docstring: trigger sentence | `:1219` | `:1244-1245` |
| `_carry_finished` docstring: new last paragraph | after `:1251` | `:1279-1287` |
| `bare` + dependents map via `_reached` | `:1254-1259` | `:1290-1295` |
| cascade call passes `bare` (+ comment) | `:1285-1287` | `:1321-1324` |
| hold for a patchless id reaching a held one | after `:1345` (end of the held loop) | `:1383-1387` |

Not changed (as the brief expected): `_runnable` (`:681-847`), `_closure_members` /
`_bundle_bases` (`:913-1012`), `integrate.py`. Nothing in them needed to change: once `A` is
carried, `_closure_members` returns a seam for the edge to finished `N` (`:947-949`) and
`_point_at_integration` puts `D` on the line, which holds `A`.

## Test

`template/tests/test_flow_carried_prereq_bases.py` (new; copy in the bundle). It loads the
peer suite `tests/test_flow_resume_stack_prereqs.py` by path and uses its `ResumeStackPrereqs`
as a helper object (the way the peer itself uses `StackFoldGit`), so the peer's own cases are
not collected twice ("Ran 8 tests"). Imports only modules (`integrate`, `state`).

| Brief criterion | Test (line) | Base `c423f9d` | Patched |
|---|---|---|---|
| (1) carried through a patchless id | `test_a_prerequisite_reached_through_a_patchless_id_is_carried` (:111) | FAIL (no `flow: carried` line; D on `("", "")`) | ok |
| (1b) two patchless ids, batch reversed | `test_a_chain_of_patchless_ids_is_walked_through` (:122) | FAIL | ok |
| (2) held through a patchless id | `test_a_closed_prerequisite_reached_through_a_patchless_id_holds_the_dependent` (:135) | FAIL (D built) | ok |
| (3) not-clean spreads through a patchless id | `test_one_built_on_a_closed_id_through_a_patchless_id_is_not_carried` (:153) | FAIL (`flow: carried issue_P`, A's line "holding no bundle") | ok |
| (4a) guard | `test_a_dependent_through_a_patchless_id_beside_one_naming_the_prerequisite` (:178) | ok | ok |
| (4b) guard | peer `test_a_prerequisite_without_a_patch_carries_nothing` (`test_flow_resume_stack_prereqs.py:300`), unchanged | ok | ok |
| (4c) guard, false-stop repro | `test_a_clean_resume_through_a_patchless_id_carries_both_and_stops_nothing` (:189) | ok | ok |
| (4c), extra: earlier line on origin | `test_a_clean_resume_through_a_patchless_id_continues_the_earlier_line` (:204) | ok | ok |
| extra: dry-run | `test_a_dry_run_through_a_patchless_id_prints_the_plan_and_holds_nothing` (:224) | FAIL (no plan printed) | ok |
| (5) existing suites | see below | — | ok |

Two cases beyond the brief's list, both cheap:

- **(4c) with an earlier line.** The brief says (4c) guards the `foreign_commit` check
  (`flow.py:1325-1326`), but with no line on origin `tip` is `None` and that check is
  skipped (`… if tip else None`). This variant first folds A and P onto the run's line (as
  the peer's `test_a_held_ids_head_does_not_vouch_for_an_old_line` does), so the check
  really runs against A's and P's heads. Green before and after; it goes red under mutation
  M4 below.
- **Dry-run.** A side effect of change 2: a dry-run whose bundle reaches a candidate
  through a patchless id now prints the carry plan for it, as a real run would carry it.
  The test pins that it still asks no host (`gh_calls == []`) and holds nothing (D built,
  on the plain base) even with A's PR closed. Red before (nothing printed), green after.

## Red → green, through the project's own runner

`PDCA_BUNDLE=results/issue_728 PDCA_WORKTREE=… ./engine/scripts/run-verify.sh` (the C4 gate,
wrapped in `timeout 900`):

```
== C4 green leg: … Ran 8 tests … OK
== C4 red leg: bundle test(s) with the production change reverted
F..F.FFF … Ran 8 tests … FAILED (failures=5)
PDCA-EVIDENCE: C4 PASS — red without the fix, green with it
```

The 5 red-leg failures are assertion failures (no `_FailedTest`, the module loaded): (1),
(1b), (2), (3) and the dry-run case. The 3 guards stay green on the red leg. The worktree
was restored by the script's trap (`git apply -R --check patch.diff` passes afterwards).

## Refuting my own test (forced)

- **(a) Genuine red?** Yes. With only the production hunks reverted (run-verify's red leg),
  5 of 8 tests fail on assertions; the failure text matches the brief's falsifiability:
  (1) "0 != 1" on the `flow: carried` count, D seen at `('', '', None)`; (2) "'issue_D'
  unexpectedly found in {'issue_D': ('', '', None), …}"; (3) zero "issue_P … is not" lines,
  stderr showing `flow: carried issue_P` and A's line "holding no bundle this run". I also
  ran the module on the untouched base before writing any production code: the same 4
  brief cases failed, (4a)/(4c) passed.
- **(b) Production path?** Yes. Every case runs `flow._drive_and_act` through the peer's
  `_run` (`test_flow_resume_stack_prereqs.py:130-156`): the real `_finished_named`,
  `_carry_finished`, `_cascade_not_clean`, `_finished_head` (real `merged.pr_state`
  parsing of the stubbed `gh` JSON), `integrate.carry_view` / `foreign_commit` / `fold`
  (wrapped by a counting spy that calls the real one), `_runnable`, `_bundle_bases` /
  `_closure_members` / `_point_at_integration`, on real git (bare origin + checkout). Stubbed,
  exactly as the peer suite stubs them: the `gh` binary, the build/sign-off leaf
  (`_drive_wave` writes a patch and accepts), the publish mechanics (`_publish_bundle` cuts
  and pushes the branch from the recorded tip) and `publish.draft_texts`.
- **(c) Fixture includes the fault?** Yes. N is a real finished bundle with the close marker
  and no `patch.diff` (`_finished(iid, None, patch=None)`), its brief declaring
  `Depends on`, re-accepted (`_patchless`, :53); the helper asserts it is COMPLETE and that
  `integrate._fold_candidates([N]) == []`, i.e. it is exactly the "not a fold candidate"
  node of the defect. N is in the batch, so `_finished_named` returns it. A's not-clean
  state is a CLOSED PR as `gh` reports it. In (3) and (4c) P's branch really holds A's
  commit (`_finished_on` asserts the ancestry).

**Mutation check** (each part of the fix broken on its own, in memory, files untouched):

| Mutation | Fails |
|---|---|
| M1 dependents map walks direct edges only | (1), (1b), (2), dry-run |
| M2 cascade without `bare` | (3) |
| M3 no hold for a patchless id | (2) |
| M4 a bad walk: anything reached through a patchless id counts as not clean | (4c), (4c) with earlier line |

**Cycle probe** (not kept as a test): finished patchless N1 (`Depends on: N2, A`) and N2
(`Depends on: N1`), D → N2. The run ends normally, A is carried, D is COMPLETE on the line.
I did not keep it as a test because a regression there would hang rather than fail; the
`seen` set at `flow.py:1192` is what ends the walk.

## (5) Existing suites — no assertion changed

- The four the brief names, plus the new module: `test_flow_resume_stack_prereqs`,
  `test_flow_dependency_scoped_bases`, `test_flow_merged_prereq_on_line`,
  `test_integrate_carried_rewrite_late`, `test_flow_carried_prereq_bases`:
  `Ran 82 tests … OK`.
- Whole offline driver suite (`cd template && PYTHONPATH=src python3 -m unittest discover -s
  tests`, CONTRIBUTING.md), on the final patch: `Ran 2589 tests in 80.568s — OK
  (skipped=2)`. (An earlier full run, before I added the last two cases: 2587, OK.)
- Root template suite (`python3 -m tests.run_root_suite` with the instance venv, which has
  copier 9.17.0; it renders the patched working tree and runs the generated project):
  `Ran 24 tests … OK — root suite OK: 24 executed, 0 skipped`.
- No existing test file is touched by the patch, so no assertion was restated. Nothing to
  report as a finding.

## Choices and what I ruled out

- **Which ids are walked through: "no patch" (`not integrate._has_patch(d)`), not "not a
  fold candidate".** The two differ only for a finished id that has a patch but no usable
  target. The brief, the invariant and `_closure_members`' docstring (`flow.py:931-932`,
  "carried, or with no patch — #728") all say "no patch", and `_runnable` already uses
  `_has_patch` for "a close/no-fix prereq merged nothing" (`:788`). An untargeted patched id
  keeps today's behaviour (the walk stops there). If the human wants it walked through too,
  it is a one-line change at `:1291` (`if d.name not in cands`), plus the reason text
  "(finished with no patch)" at `:1229` would need a neutral wording.
- **The walk does not pass through fold candidates.** Walking through them would also put
  `D` in the "holding" list of a candidate that `D` reaches only through another candidate
  (e.g. in the existing chain test P ← Q ← R ← D, P's and Q's lines would add "holding
  issue_D"). That changes messages of existing, already-correct runs, which the brief did
  not ask for, and adds nothing to what is carried: every candidate of a triggered target
  is already judged (`ids` at `:1297`). So candidates stay the walk's end points, which is
  what makes the direct-only case byte-identical.
- **Holding the dependents by putting N in `held`, not by changing `_runnable`.** `_runnable`
  already holds a bundle whose plain `Depends on` names an out-of-batch id in `held`
  (`:803-806`), and `held` is already the carry's way of telling `_runnable` "wait for
  this one". The alternative is to make `_runnable` walk through patchless ids itself.
  Sketch, reusing `_reached`:

  ```diff
   def _runnable(cfg, wave, batch_names, *, held=frozenset(), …,
  +              cands: Collection[str] = (), bare: Mapping[str, Path] | None = None,
                 lines=None) -> list[Path]:
   …
  -            elif p.name in held and (not out_of_batch or dep in plain_deps):
  +            elif (p.name in held and (not out_of_batch or dep in plain_deps)) or (
  +                    out_of_batch and dep in plain_deps and bare and p.name in bare
  +                    and any(c in held for c in _reached(cfg, p, cands, bare))):
   …
  -        runnable = _runnable(cfg, wave, batch_names,
  +        runnable = _runnable(cfg, wave, batch_names, cands=…, bare=…,
  ```

  About 6 changed lines across `_runnable` and its call site at `:2671`, plus threading
  `cands` / `bare` out of `_carry_finished` to `_drive_and_act` (they are locals today),
  against the 2-line `held.update` here. Size is not the deciding point, though: the brief
  expects `_runnable` unchanged, #729 is editing `_runnable` in another wave, and keeping
  the hold in the carry keeps all three decisions (carry, not clean, wait) in one place.
  No `_runnable` change was needed.
- **No stderr line for N**, per the brief: the cause's line names the dependents
  (`issue_A … — holding issue_D`), and `_runnable` prints its usual
  "issue_D skipped — prerequisite(s) not ready (N)".
- Small side effect: the dependents list is now built per (candidate, bundle) once, so a
  brief listing the same id twice no longer lists its bundle twice on a "holding" line.

## Not done / for the human

- `docs/07-crosscutting.md:747-764` describes the re-issue carry in terms of a bundle that
  "names one of them in its plain `Depends on`". After this patch that also covers reaching
  one through finished ids with no patch. I left the doc alone because the brief scopes the
  change to `flow.py` ("Surfaces: none"); a one-sentence doc follow-up may be worth it.
- Out of scope and unchanged, as the brief says: an out-of-batch prerequisite reached only
  through a patchless id (f1, #734 → #729's `_runnable` branch); carried bundles as own-base
  members (f2, #735); `Stacks on` / `Depends on (merged)` / `Conflicts with` edges through a
  patchless id; candidates on another target reached through one (the cascade still reads
  one target's ids, as before).
- #729 also edits `flow.py` (`_runnable`). This patch does not touch `_runnable`, so the two
  should not conflict textually; they are in different functions.

## Commit-readiness

The target repo has no formatter, linter or pre-commit config (no `.pre-commit-config.yaml`,
no ruff/flake8/black settings; CONTRIBUTING.md asks only for a DCO sign-off, one change per
PR, and the offline suite green). Checked: `git diff --check` clean; no added line over 100
columns (the file's own limit, a handful of existing lines at 102-106); `py_compile` OK for
both files; `git apply -R --check patch.diff` passes on the worktree, so `patch.diff` is
exactly base `c423f9d` plus these two files. The DCO `Signed-off-by` is added by the
publish commit (`git commit -s`), not by the patch.

No external dependency was needed beyond Python 3 and git (the brief's "none").
