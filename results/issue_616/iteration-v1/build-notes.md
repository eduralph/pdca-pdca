# Build notes — issue 616 / stack-resume-carries-unmerged-prereqs

Target: `eduralph/pdca-harness` @ `main`. The patch is written against the cycle's worktree
`$PDCA_WORKTREE` = `/home/eddie/pdca/pdca-harness.pdca-wt`, HEAD `f594d8e` — `c67a14d` (the
brief's verified `origin/main`) with #531, #590 and #591 folded on top (`pdca-integrate:`
commits; `stack-base` = `pdca-integration/main`). Every `path:line` below is on that tree
**with the patch applied** unless it says "base". The brief's line numbers were from
`c67a14d` and had moved, as its ordering note warned; all were re-resolved.

## What changed and why

The defect has three parts (brief): a finished prerequisite `P` is skipped, so it never
reaches the fold; with nothing folded, `_point_at_integration` clears the dependent's stack
base; and `_runnable` lets the dependent through because `P` is COMPLETE. The fix adds one
fold point before wave 0 and one hold, and leaves the in-run fold contract (#593) and the
per-batch line (#591) as they are.

1. **Which prerequisites to carry or hold** — new `_prereqs_to_carry`
   (`template/src/pdca_harness/flow.py:748-806`). For every drive-set bundle `d` and every
   declared prerequisite `dep` (`waves.declared_deps`, so `Depends on` and `Stacks on`) that
   is outside the batch and not one of `d`'s `Depends on (merged)` edges (#186 keeps waiting
   for the merge in `_runnable`, `flow.py:707-709`):
   - skip unless `dep` has the same `(repo, base)` target as `d` (`flow.py:793`) — a line is
     per target (#187), so no line could carry a prerequisite of another target into `d`'s
     base; `d` builds as today;
   - "base" (nothing to do) if not COMPLETE, not a fold candidate (no patch / no target —
     `integrate._fold_candidates`, `integrate.py:158-166`, the fold's own definition), or
     `merged.is_merged(cfg, dep)` (`flow.py:795-797`, called exactly as `_runnable` calls it
     at `flow.py:708`) — cases (b) and (c);
   - "hold" if not a dry-run and `integrate.unpublished([p])` (`flow.py:799`,
     `integrate.py:169-179`) — case (a);
   - otherwise "carry".
   Each prerequisite is judged once (`verdict` cache), so `gh` is asked at most once per
   prerequisite per run.

2. **One fold step for both fold points** — new `_fold_onto_line`
   (`flow.py:809-847`). This is the in-run fold body moved out verbatim: the
   `integrate.fold(..., locks=locks, folded_this_run=dict(folded_tips), batch=run_batch)`
   call, the `folded_tips` bookkeeping, the one lock scope over fold + re-gate, and the two
   STOP messages. The messages read exactly as before for the in-run call
   (`what=f"wave {k}"`, `then="later waves not run"`): "flow: wave {k} did not integrate
   (...); STOPPING — later waves not run." and the re-gate line. Base lines 2059-2097 (the
   in-run block) became `flow.py:2201-2212`.

3. **The pre-wave fold** — `flow.py:2043-2067`, after the `k=-1` seed splice (so recovery
   children adopted before wave 0 are covered) and before the wave loop. Only when
   `do_publish and cfg.wave_mode != "merge"` (brief: `--no-publish` sequences nothing, merge
   mode is out of scope). Holds are printed with the dependents' names and the reason
   (`flow.py:2051-2056`). Carried prerequisites are folded with `_fold_onto_line` onto
   `run_batch`'s line, starting fresh (`folded_tips` is empty, so `integrate.fold` treats it
   as the run's first fold: start from base, force-push — `integrate.py:344-345, 401`). On
   success `integ` is set (`flow.py:2066-2067`), so `_point_at_integration`
   (`flow.py:725-745`, unchanged) points **every** runnable wave-0 bundle of that target at
   the line — the `U` case. On `IntegrationError` (or a red re-gate) the stop line is printed
   and `wave_list = []` (`flow.py:2064-2065`): no wave runs, the post-loop sweep / results /
   Act run as after an in-run stop — case (d).

4. **Later folds keep carrying the line** — `flow.py:2206`: the in-run fold's input is
   `carried + [accepted not held]`. Without this, a wave that accepts nothing of the carried
   target makes `integ` lose that target (`integ` is *replaced* by each fold's result,
   `flow.py:2212`), and a later-wave dependent is cleared back to the bare base.
   `test_the_line_outlives_a_wave_that_accepts_nothing_of_its_target` pins it (mutation
   checked, below). Already on the line, a carried branch is skipped by `_merge_published`'s
   `_in_line` check (`integrate.py:426-427`) unless it moved since, in which case its new tip
   is merged — the same rule #593 applies to in-batch branches.

5. **The hold reaches `_runnable`** — `flow.py:713`: `elif not out_of_batch and ... in held`
   became `elif ... in held`, and the loop passes `held=held_unpushed | held_prereqs`
   (`flow.py:2074`). `held_unpushed` only ever holds in-batch names (it is filled from
   `accepted`, `flow.py:2195-2200`), so dropping the `not out_of_batch` qualifier changes
   nothing for #593's hold.

6. Docstrings: `_runnable` (`flow.py:683-700`), `_drive_and_act` (`flow.py:1946-1951`).
   Docs: `docs/07-crosscutting.md:677-685`, in the `"stack"` bullet the brief named.

## The test

`template/tests/test_flow_resume_stack_prereqs.py` (also copied flat into the bundle). Real
git: a bare `origin`, a primary checkout, a scratch "human" clone — the `StackFoldGit` shape
of `test_integrate_stack_bases.py:115-138`, copied rather than imported (no test module in
`template/tests` imports another; there is no `tests/__init__.py`). It drives the production
`flow._drive_and_act` with `batch=` as a re-issued `pdca flow <ids>` would. Stubbed:
`flow._drive_wave` (records each bundle's `stack-base`, `stack-base-tip` and the line's
commit on origin at that moment, then makes the bundle COMPLETE), `flow._publish_bundle`
(a real `git push` of `fix/<id>` cut from the recorded tip, plus `publish.json` — the real
publisher would open a PR with `gh`), `publish.draft_texts` (T4 texts). `gh` is faked by
swapping `merged.subprocess` for a namespace whose `run` answers `gh pr view` from a dict,
so the shipped `merged.is_merged` / `merged.merged_head` run unchanged. I could not patch
`pdca_harness.merged.subprocess.run` directly: that is the global `subprocess.run`, and
`integrate` needs it for git. The publisher is in `"command"` mode so every fold is real.

Cases: the criterion (P carried, D and U on the line before wave 0, E on the continued line,
pushes = forced then unforced); the line surviving a wave with nothing of its target; (a)
no published branch → D held and named, U goes on; (b) merged → nothing folded; (c) empty
`patch.diff` and close-disposition with no patch → nothing folded, nothing held, no `gh`
call; (d) branch deleted, PR not merged → stop before wave 0, one "did not integrate …
STOPPING" line, no traceback, nothing pushed; `Depends on (merged)` unchanged; a
prerequisite of another base and one with no `brief.md` left alone (no crash); a run with
no out-of-batch prerequisite asks `gh` nothing and folds nothing.

### Refuting my own test

- **(a) Genuine red?** Yes. The project's C4 gate (`engine/scripts/run-verify.sh`, run with
  `PDCA_BUNDLE`/`PDCA_WORKTREE` set) reverted the production hunks and re-ran: 4 of 9 failed
  on assertions (no import error) — the criterion case (`'' != 'pdca-integration/main-r…'`:
  D's stack base empty), (a) (D was driven), (d) (both bundles driven), and the line-survival
  case. Green leg 9/9. Verdict line: `PDCA-EVIDENCE: C4 PASS — red without the fix, green
  with it`. The five guard cases pass on both legs by design. Two mutation checks on top:
  removing the same-target filter makes the other-target case fail (`FileNotFoundError` from
  the briefless prerequisite); dropping `carried +` from the in-run fold makes the
  line-survival case fail. Both reverted; the patch is the un-mutated code.
- **(b) Production path?** Yes. `_drive_and_act`, `_prereqs_to_carry`, `_fold_onto_line`,
  `_runnable`, `_point_at_integration`, `integrate.fold` (real git against the bare origin),
  `publish.read_stack_base`/`read_stack_base_tip`, `merged.is_merged`/`merged_head` all run
  unmocked. Only the build/check/sign-off leaf, the T4 text drafting, the publisher leaf and
  the `gh` binary are stand-ins — none of them is code the fix changes. The stand-in publish
  cuts from the recorded tip the way publish does; publish's own use of the tip is already
  covered by `test_integrate_stack_bases.py:805-816`.
- **(c) Fixture includes the fault?** Yes. P is really outside the drive set (only in
  `batch`), really COMPLETE (sign-off recorded), its branch really pushed to origin, and the
  host fake reports its PR `OPEN`; the assertions read origin's refs. In (d) P's branch is
  really deleted on origin, with a stale tracking ref in the primary for the fold's
  `--prune` to drop.

## Alternatives I ruled out (with cost)

- **Merge check inside `_runnable`** instead of a pre-wave classifier. Rejected on behaviour,
  not size: `test_flow_slice.py:1974-1981`
  (`test_out_of_batch_plain_depends_on_keeps_complete_bar`) asserts `_runnable` does not call
  `merged.is_merged` for a plain out-of-batch dep, and `_runnable` runs once per wave, so it
  would ask `gh` once per wave per dependent per prerequisite instead of once per run.
- **Duplicate the fold + re-gate in the pre-wave block** instead of extracting
  `_fold_onto_line`. About 30 new lines in the pre-wave block (try/except, tips loop,
  re-gate, two messages) and 0 removed, versus what I shipped: a 39-line helper
  (`flow.py:809-847`, about half docstring) and the in-run block going from 38 lines to 12.
  Rejected because the brief requires the pre-wave fold to use the same call shape, batch
  key and `folded_tips` as the in-run fold; one function makes that structural instead of
  two copies that can drift.
- **`integ.update(...)` instead of `carried +` in later folds** (both about 1 line). Rejected:
  with `update`, a fixup pushed onto `P`'s branch mid-run never reaches the line, while an
  in-batch branch's fixup does (#593). Passing the carried bundles keeps the fold's input
  "the whole stack, in order", which is `integrate.fold`'s documented contract
  (`integrate.py:251-252`).
- **Put unpublished out-of-batch names into `held_unpushed`** instead of a new
  `held_prereqs`. Same line count; rejected for meaning: `held_unpushed` is "accepted this
  run, branch not pushed", and its loop at `flow.py:2195-2200` prints a message about that.
- **No same-target filter.** Without it, a cross-repo / cross-base prerequisite creates a line
  in its own target that no dependent can use, stacks unrelated wave-0 bundles of that
  target on it, and a COMPLETE prerequisite with no `brief.md` (possible, `state.py:345-350`)
  crashes the run with `FileNotFoundError` from `publish._resolve_target`. Cost of the
  filter: 8 lines (`flow.py:775-777, 784-786, 793-794`).

## Things the human should know at sign-off

- **Behaviour change for legacy `Stacks on` across runs.** `declared_deps` includes
  `Stacks on`, so an out-of-batch `Stacks on: P` (published, unmerged, same target) is now
  carried too. Its dependent then builds on the line and, because a recorded stack base wins
  over the `Stacks on` parent (`publish.py:729-738`), opens its PR against `main` rather than
  `fix/<P>`. Its base carries P either way. Excluding `Stacks on` would be worse: any other
  carried prerequisite of the same target points that dependent at a line without P. This is
  how in-batch `Stacks on` has behaved since #593.
- **Wave-0 PRs of a carried target show the prerequisites' changes until they merge.** The
  criterion asks for this (bundle `U`); docs say so (`docs/07-crosscutting.md:681-682`).
- **Not covered: a split child adopted mid-run** (after wave 0) whose brief adds an
  out-of-batch prerequisite that no drive-set bundle declared before wave 0. The brief fixes
  one fold point before wave 0, so that child behaves as before the fix. Children adopted
  from recovery seeds (`k=-1`) are covered because the pre-wave step runs after that splice.
- **`gh` exposure.** `merged.is_merged` does not catch `OSError` (`merged.py:50`), so with
  `gh` missing, a stack-mode publishing run whose bundle has an out-of-batch prerequisite
  with a recorded `pr_url` would raise. `_runnable` already has this exposure for
  `Depends on (merged)`, and a publishing run needs `gh` to open PRs anyway. Left alone as
  out of scope.
- `--no-publish` and merge mode are unchanged (brief: out of scope; #531 for merge mode).

## Checks run (all through the project's scripts in `pdca-pdca/engine/scripts/`)

- C4 `run-verify.sh`: PASS (above). Worktree restored afterwards; `git diff` matches
  `patch.diff` byte for byte.
- T3 `run-suite.sh`: root suite 24 tests OK, driver suite 2334 tests OK (2 skipped).
- T2 `run-docs-check.sh`: docs lint clean, site render + link audit clean.
- C5 `run-prod-path.py`: the added test imports `pdca_harness`.
- Commit-readiness: the target has no formatter or pre-commit hooks (no
  `.pre-commit-config.yaml`, `core.hooksPath` unset; CI runs only the docs lint/render,
  `.github/workflows/docs-check.yml:33`). `git diff --check` is clean; no added line is over
  100 characters, matching `flow.py`'s style.

## Housekeeping slip

The first full-suite run's output went to `/tmp/pdca616-suite.log`, outside the roots I may
write to. I did not delete it (cleanup is the harness's); it holds only test output. Later
runs were piped straight to the terminal. One quick `python -c` check made and removed a
temporary directory inside the worktree's `template/`; `git status` shows nothing left over.
