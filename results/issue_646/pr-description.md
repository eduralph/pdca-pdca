## Summary
**User impact:** In stack mode, if a run stops part-way (an integrity stop, the
pass budget, a crash, Ctrl-C), the documented way to recover is to run the same
`pdca flow <ids>` again. When one of those ids had already finished in the first
run, the second run quietly built the bundles that depend on it **without** it:
the dependent was checked, verified and opened as a PR missing the code it
needs, and no message said so. The second run then also overwrote the first
run's integration branch, which still held that finished work.

This PR makes the re-issued run put finished prerequisites back on the
integration branch before it builds anything that depends on them. A
prerequisite it can't add cleanly holds back only its own dependents, with one
clear message, and the rest of the run goes on.

Reported in [#646](https://github.com/eduralph/pdca-harness/issues/646) (first
part of the split of #616).

## What to look at
- The new pre-wave step in the flow driver (`_carry_finished` and its helpers in
  `flow.py`), and the one new optional argument on `integrate.fold` (`skipped=`).
- The rule is deliberately simple: **add the clean case, hold everything else.**
  "Clean" means the prerequisite's PR is open (or merged with its commit already
  on the base or the line), its commit exists, it merges without error, and the
  re-gate of the line is not red. Any other outcome holds that id's dependents,
  prints the reason plus one of three short hints, and the run continues.
- If origin already has the batch's integration branch from the earlier run, it
  is continued with a normal (non-force) push. If that branch holds commits the
  run can't account for, the run does not build on it and says to delete it.
- To try it: from `template/`, run
  `PYTHONPATH=src python3 -m unittest tests.test_flow_resume_stack_prereqs`.
  The tests drive the real flow and real git against a bare origin; only the
  build/sign-off steps, the publish call and `gh` are stubbed.

**Base note:** this was built and verified on top of the open fixes for #531,
#590 and #591 (PRs #638 and #639 among them), because it needs the batch-scoped
integration branch name from #591. Until those merge, this PR also shows their
commits. If #639 changes before it merges, this PR needs a rebuild.

## Root cause
A finished id is skipped as already done (`flow.py`, the terminal-skip in
`flow_ids`), so it never enters the run's fold, and `_runnable` accepts it as a
met dependency just because it is COMPLETE, which only means a draft PR exists.
With nothing folded yet, `_point_at_integration` clears the dependent's stack
base and it is cut from the plain target branch.

## Fix
- `flow._fold_lines` (`template/src/pdca_harness/flow.py:752`): the in-run
  "lock, fold, read tip, re-gate" block moved into one function, now used by both
  the in-run fold (`flow.py:2241-2263`, unchanged behaviour) and the new carry.
- `flow._finished_named` / `_finished_head` / `_carry_finished`
  (`flow.py:782`, `:795`, `:828`), called once before the wave loop when
  publishing in stack mode (`flow.py:2105`). It triggers only when a driven
  bundle's plain `Depends on` names a carryable finished id; `Stacks on` and
  `Depends on (merged)` do not trigger it. A dry run only prints the plan.
- Trust check: `integrate.carry_view` and `integrate.foreign_commit`
  (`template/src/pdca_harness/integrate.py:185`, `:196`) read origin's line and
  look for any non-merge commit not reachable from the base or a clean
  prerequisite's head.
- `integrate.fold(skipped=…)` (`integrate.py:275`, loop `:435-441`): a single
  bundle's merge error is recorded and the loop moves on. Without the argument,
  `fold` behaves exactly as before.
- `integrate._fetch` (`integrate.py:598`) split out of `_prepare_worktree`
  (`:618`) so the carry can read origin without creating the integration
  worktree outside the lock.
- `merged.pr_state` (`template/src/pdca_harness/merged.py:96`): reads PR state
  and head in one `gh` call, with the same missing-`gh` guard as `merged_head`.
- `_runnable` (`flow.py:681`, hold at `:717-720`) also holds a dependent whose
  plain `Depends on` names a held finished id.
- In the in-run fold, `integ = {…}` became `integ.update(…)` (`flow.py:2256`) so
  a carried target keeps its line when a later fold touches other targets only.
- Wording: `publish.py` and `drift.py` drop the "#616 will fix this" pointer and
  keep "re-drive it in a new run"; `docs/07-crosscutting.md` (stack-mode bullet,
  `:679-702`) describes the carry, the hold rule and its known limits. Two
  existing assertions in `test_integrate_stack_bases.py` follow the new wording.

## Known limits (not handled here, by design)
Each of these holds dependents until a person acts; none of them stops the run.
Most are listed in `docs/07-crosscutting.md:695-702`. Review raised three more,
accepted for follow-up:
- "Not clean" does not cascade across finished ids: if `P` is closed but a
  finished `Q` built on `P` is clean, carrying `Q` still brings `P`'s commits in.
- The carry approves the PR's head commit but folds the branch's current tip; a
  commit pushed to the branch after the PR was merged would be folded.
- A continued line keeps the earlier run's base, so after a long gap the
  dependents build on an older `main` than a fresh run would.

## Verification
- **Claim:** a clean finished prerequisite is on the line before its dependent
  is built, and the dependent's stack base names that line.
  **Checked:** `flow.py:2105` (carry before wave 0), `flow.py:828-` (carry).
  **Test:** `test_a_clean_finished_prerequisite_is_on_the_line_its_dependent_builds_on`
  (`template/tests/test_flow_resume_stack_prereqs.py:176`).
- **Claim:** an existing trusted line is continued, never force-replaced, and
  stays append-only into later waves.
  **Checked:** `integrate.py:275` start modes; origin set to deny non-fast-forward.
  **Tests:** `:188`, `:206`.
- **Claim:** a not-clean prerequisite holds only its dependents and an unrelated
  bundle still builds (closed PR, `gh` missing, two conflicting prerequisites).
  **Checked:** `flow.py:717-720`, `integrate.py:435-441`.
  **Tests:** `:226`, `:235`, `:246`.
- **Claim:** an untrusted line or a red re-gate is not built on; the run goes on.
  **Checked:** `integrate.py:196`, `flow.py:828-`.
  **Tests:** `:262`, `:326`.
- **Claim:** unchanged when nothing triggers the carry; a dry run asks no host.
  **Tests:** `:281`, `:290`, `:303`, `:312`; unit test for `fold(skipped=…)` at `:347`.
- **Red → green:** with only the production changes reverted, 10 of the 13 new
  tests fail on assertions (the 3 that pass are the "unchanged behaviour" checks,
  which must pass both ways). With the patch, all 13 pass, plus 46/46 in
  `test_integrate_stack_bases.py`.
- **Full suites:** driver suite 2338 OK (2 skipped), root suite 24/24, docs lint
  and render link check clean.
- **Not exercised:** a live `gh` / GitHub host. PR state comes from a stubbed
  `gh pr view` in the tests.

Fixes #646
