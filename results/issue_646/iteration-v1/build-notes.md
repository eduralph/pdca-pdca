# Build notes — issue #646 (stack-reissue-continues-batch-line)

Withheld from the reviewer. For the human at sign-off.

## Base I built on

The worktree (`$PDCA_WORKTREE` = `/home/eddie/pdca/pdca-harness.pdca-wt`) is at
`origin/pdca-integration/main` @ `12405dc`: `origin/main` @ `c67a14d` plus the folds of #531,
#590 and #591 (`git log --oneline -4`). The bundle's `stack-base` file says
`pdca-integration/main`, so the driver put this bundle in stack mode on the integration line.
The brief was verified on `f594d8e` (the same three folds); I re-resolved every line on
`12405dc`. Most `flow.py` numbers in `_drive_and_act` sit about 100 lines earlier than the
brief's (for example the in-run hold is at `flow.py:2177-2182` after the patch, not `:2052`).

**For the human:** the brief says not to build until #639 (#591) is merged into `main`. It is
not merged on `origin/main` yet, but the worktree already contains #591 through the
integration line, so the `TypeError` concern behind that rule does not apply to this build.
The resulting PR is a stacked PR cut from the integration line. Until #531/#590/#591 merge,
its diff against `main` will show their changes too. Confirm that is what you want before
publishing.

All `path:line` below are on the patched worktree (`12405dc` + `patch.diff`).

## What changed and why

The defect has three parts that all have to change together (the brief's "not a single-module
guard"):

1. **The fold never sees the finished id.** New `_carry_finished`
   (`template/src/pdca_harness/flow.py:754-850`), called once before the wave loop
   (`flow.py:2040-2055`). It runs only in stack mode with publishing on. It looks at the ids
   the run was asked for (`run_batch`) that are not in the drive set and are COMPLETE
   (`flow.py:791-797`). If no drive-set bundle names one of them in its plain `Depends on`,
   it returns at once and nothing changes (`flow.py:798-804`, criterion 7). Otherwise it folds
   every carryable finished id with `integrate.fold(..., folded_this_run=None,
   batch=run_batch)` (`flow.py:840-841`). That is the fold's existing "auto" start mode
   (`integrate.py:344-345`, `:390`, `:401`): continue origin's line when it exists and push
   without force, start fresh only when it does not. The pushed tip goes into `folded_tips`
   and the branch into `integ` (`flow.py:842-849`). The existing per-wave
   `_point_at_integration(integ, runnable, folded_tips)` call then points every same-target
   wave-0 bundle at the line, including an unrelated `U` (criterion 8). The fold after wave 0
   sees the target in `folded_this_run`, so it continues the line without force
   (`integrate.py:381-389`, criterion 3).
2. **Readiness.** `_runnable` used to apply the `held` check to in-drive-set prerequisites
   only. Now it also applies it to an out-of-drive-set prerequisite reached through a plain
   `Depends on` edge (`flow.py:710`, `:719-722`). Only `_carry_finished` ever puts such a name
   in `held`, so nothing changes for existing runs. `Depends on (merged)` still hits the #186
   merge gate first (`flow.py:714-716`), and `Stacks on` does not consult `held` for
   out-of-batch names.
3. **Holds.** A finished id the fold cannot carry is added to `held_unpushed`, the same set
   the in-run fold's hold uses. One stderr line names it, the dependents it holds, the reason,
   and what to do (`flow.py:806-831`). The cases: no branch on record (4a); a CLOSED PR (4c);
   a PR state that cannot be read (4d). 4d covers no `pr_url`, a `gh` failure, or `gh`
   missing. The PR state comes from the new `merged.pr_state` (`merged.py:98-127`), which
   copies `merged_head`'s `OSError` guard (`merged.py:79-83`) and returns the reason as text.
   OPEN and MERGED are carried. For a merged PR whose branch is gone, the fold's
   `_gone_branch` decides (`integrate.py:442-490`).
4. **Fail closed.** If the carry fold raises `IntegrationError`, it prints
   `flow: the finished prerequisite(s) … did not integrate (…); STOPPING — no wave run.`
   (`flow.py:844-847`) and returns False. The wave loop then iterates an empty list
   (`flow.py:2055`), so nothing is driven. The end-of-run tail (sweep, results) still runs,
   just as after the in-run fold's `break`.
5. **`integ` is added to, not replaced** (`flow.py:2205-2207`). Carried ids are kept out of
   `accepted` (the brief allows this: they are already on the line). Without this change, a
   later in-run fold that does not touch a carried target would drop that target's line from
   `integ`. Today this is a no-op: `accepted` is cumulative, so each fold already returns
   every earlier target.
6. **Dry-run** (stub publisher): carry every candidate, ask no host, hold nothing
   (`flow.py:809-811`). `integrate.fold(dry_run=True)` prints the plan with
   "continue … if origin has it" (`integrate.py:351-352`).
7. **Wording.** `publish.py:345-346` (dry-run plan line), `publish.py:696-700`
   (`_line_tip_refusal` docstring), `publish.py:727-732` (the refusal), `drift.py:58-64`, and
   `docs/07-crosscutting.md:665-676` and `:685-688` now describe the kept line instead of
   "#616". The old-wording assertions are updated in
   `template/tests/test_integrate_stack_bases.py:832-854` and `:1013-1015`.
   `_carry_finished`'s docstring names the two gaps the brief asked for
   (`flow.py:788-790`): split children adopted mid-run, and a line rewritten outside the
   harness (`flow.py:772-773`).

## Alternatives ruled out (with cost)

- **Keep carried ids IN `accepted` and add them to `pushed`**, instead of keeping them out and
  changing `integ =` to `integ.update(...)`. Cost: about the same (2 lines,
  `accepted += carry` and `pushed |= {d.name for d in carry}`, against 1 changed line). I
  chose keep-out because it is the brief's first option and every later fold then skips the
  carried ids. Keeping them in would make every later in-run fold check them again. For a
  merged PR whose branch is deleted, that is one extra `gh pr view` per fold
  (`integrate.py:462`). **Trade-off accepted:** a fixup pushed onto a carried bundle's branch
  *during* the re-issued run does not reach the line in that run (one pushed before the run
  does: the carry fold merges the branch's current tip, `integrate.py:422-428`).
- **Widening `batch_names` itself to the requested ids** (the brief's wording "in batch
  widens"). Rejected: at `flow.py:714-716` a `Depends on (merged): P` edge would leave the
  #186 merge gate for the COMPLETE bar, which breaks criterion (7). So the widening is per
  edge, at `flow.py:719`, for plain `Depends on` only.
- **Making every run's first in-run fold "auto"** (`folded_this_run=dict(folded_tips) or None`
  at `flow.py:2193`). This is a 1-line change that would also close the gap below. But
  (a) it changes behaviour that criterion (7) pins as "exactly as today". (b) It breaks the
  existing `test_flow_slice.py:1377`, which asserts the first fold gets `{}`. (c) On its own it
  does not fix the main defect: wave 0 would still be cut from the plain base, because the
  first in-run fold only happens *after* wave 0. Not done.
- **Re-gating the carried line** (`regate_between_waves`) before wave 0. Not in the brief.
  About 12 lines copying the lock-scope + `gates.run_integration` block at
  `flow.py:2189-2222`. The carried combination is either a single finished bundle or what an
  earlier run already folded and re-gated, if re-gating was on. Left out; flagged as an open
  question below.
- **Test `gh` stub as a fake executable on `PATH`.** Rejected for the `gh`-missing case: `gh`
  is installed here, and dropping it from `PATH` would also drop `git`. The test replaces
  `merged.subprocess` with a proxy that answers only `gh` calls from a table and passes every
  other call to the real `subprocess.run`. This is a stub at the process boundary, not a
  stand-in for production code. The flow's own `merged.pr_state`, `merged.merged_head` and
  `merged.is_merged` all run unchanged through it.

## Residual gap — please weigh at sign-off (not an external dependency)

The invariant's second half says "no run replaces commits an earlier run of the same batch
recorded as a build base". That now holds **only when the carry triggers**. Scenario: the
earlier run of `[A, H(dep A), Z, W(dep Z)]` folds A, builds H on the line, and H's publish
fails (H is held with a recorded tip). The re-issued run drives `[Z, W]`; neither depends on a
finished id, so there is no carry. Its fold after wave 0 starts fresh and force-pushes over
the line, and H is stranded. This is exactly what criterion (7) requires ("behaves exactly as
today"), so I did not widen the trigger. The publish refusal now names this cause ("started
fresh by a run that carried nothing", `publish.py:727-732`). The CLOSED-PR advice "re-drive
<id>" can lead to the same shape when the re-driven id is back in the drive set. A follow-up
could make the first in-run fold continue whenever the request has finished ids. That is a
product decision, so it is yours.

## Self-refutation (forced)

- **(a) Genuine red? Yes.** The C4 gate (`engine/scripts/run-verify.sh`) reverted the
  production hunks only and re-ran both test modules: 12 of the 17 new tests failed, plus the
  2 updated wording tests. Every failure is the defect itself, not a side effect:
  - (1): "no pdca-integration/main-r… on origin before D's wave".
  - (2): `[['push', '--force', 'origin', 'pdca-integration/main-r…']]`, the earlier line
    being replaced.
  - (3): one fold instead of two, so the line lacks P.
  - 4a/4c/4d×3 and (8): D was built. Its real publish then failed with "patch may not apply
    against origin/main", which is the user-visible symptom.
  - (5-merged): D's stack base was `('', '')`.
  - (6): D and U were driven.
  - (7-dry-run): no carry plan was printed.

  The 5 tests that pass on both legs are the "unchanged" guards: empty patch, close-marker
  (no patch), no dependency, `Stacks on`/`Depends on (merged)`, `--no-publish`/merge mode.
  They should pass on both legs.
- **(b) Production path? Yes.** The tests call the real `flow._drive_and_act` with
  `batch=[…]`, the shape `flow_ids` produces at `flow.py:2486-2489`. Inside it, the real
  `_runnable`, `_carry_finished`, `_point_at_integration`, `integrate.fold` (real git against
  a bare `origin`), `merged.pr_state` / `merged_head` / `is_merged`, `_publish_bundle`, and
  the real `publish.publish` all run. `publish.publish` is called with `open_pr=False`; it
  cuts the branch from the recorded tip, applies the patch, commits and pushes. Stubbed:
  `flow._drive_wave` (accepts the bundle and records its stack base), `publish.draft_texts`
  (texts are written by the stub), `publish._warn_if_squash_only` (a `gh repo view` call),
  and `gh`.
- **(c) Fixture includes the fault? Yes.** P is only in `batch`, never in the drive set,
  exactly as a re-issued `flow_ids` skips it. P has a real pushed branch and `publish.json`.
  In (2), origin really has the earlier run's line (made by the real fold with the same batch
  key) holding P, and H's recorded tip is on it. The hold cases really lack the branch
  record, really answer CLOSED, really fail `gh` (rc 1), or really raise `FileNotFoundError`.
  (6) really deletes P's branch on origin. (5-merged) really merges P into `main` and deletes
  the branch.

## Commands run (the project's runners)

- C4: `PDCA_BUNDLE=… PDCA_WORKTREE=… ./engine/scripts/run-verify.sh` → `PDCA-EVIDENCE: C4 PASS
  — red without the fix, green with it`. Green: 17/17 + 46/46. Red: 12 + 2 failures.
- T3: `./engine/scripts/run-suite.sh` → root suite OK (24), driver suite OK (2342, 2 skipped).
- T2: `./engine/scripts/run-docs-check.sh` → docs lint clean, site render + link audit clean.
- Commit-readiness: the target has no formatter or pre-commit config (no
  `.pre-commit-config.yaml`, no installed hooks, no ruff/black config). `CONTRIBUTING.md`
  asks for a DCO sign-off, which publish adds (`git commit -s`). No added line is over 96
  columns, and I removed the one unused import. The docs CI (`docs-check.yml`) runs the same
  two checkers as T2, and they are clean.

No external dependency was missing.
