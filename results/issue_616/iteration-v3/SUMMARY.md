# Result — issue 616 / stack-resume-carries-unmerged-prereqs

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: In stack mode, the recovery for a run that stopped part-way (an integrity stop,
  the pass budget, a crash, Ctrl-C) is to re-issue the same `pdca flow <ids>`. That resumed
  run builds dependents on a base that lacks their prerequisites:
  - bundles that finished in the earlier run are skipped as already terminal
    (`template/src/pdca_harness/flow.py:2242-2243`), so they are not in this run's batch and
    never enter `accepted` / the fold (`flow.py:1960`, `:1996-1998`);
  - with nothing folded yet, `_point_at_integration` clears the dependent's stack base
    (`flow.py:736-742`, `integ` is empty before the first fold), so it is cut from the plain
    target base;
  - `_runnable` accepts an out-of-batch prerequisite as ready once it is COMPLETE
    (`flow.py:706-711`). COMPLETE only means a draft PR was opened, so the prerequisite's work
    is not in the base unless that PR has merged. Only `Depends on (merged)` waits for the
    merge (#186, `flow.py:707-709`).
  Result: the dependent is built, C4-verified and published against a tree missing its
  prerequisite. Nothing reports it.
- Success criterion: With the patch, in stack mode with publishing on: a run whose batch
  holds a dependent `D` with `Depends on: P`, where `P` is NOT in the batch, is COMPLETE, has a
  published branch (its `publish.json` records the pushed branch) and its PR is NOT merged,
  builds `D` on a base that carries `P`'s published commits: before `D`'s wave is driven, the
  run's integration line on `origin` contains `P`'s branch head, and `D`'s recorded stack base
  (`publish.read_stack_base`, which Do's worktree and `PDCA_VERIFY_BASE` read) names that
  line. Demonstrated with real git against a bare `origin` (the `StackFoldGit`-style fixture)
  and stubbed leaves; pre-fix `D`'s stack base is cleared and the line is never created, so
  the same assertions fail. The pre-wave fold uses the SAME integration branch the run's own
  in-run folds use (#591's per-batch name, via the same `integrate.fold` call shape and batch
  key) and seeds `folded_tips`, so with a second in-batch bundle `E` (`Depends on: D`) the
  fold after wave 0 (D accepted) continues that line without a force-push and without
  `IntegrationError`: the line then holds `P` and `D`, and `E`'s recorded stack base names it. Every runnable bundle of the same `(repo, base)` target in
  the first wave is pointed at the line — including one that does not depend on `P` (assert it:
  an unrelated wave-0 bundle `U` of the same target also records the line as its stack base).
  That matches how later-wave stacking already behaves (`_point_at_integration`,
  `flow.py:722-742`); its PR shows `P`'s changes until `P` merges, as any later-wave PR does.
  Companion cases in the same file:
  (a) `P` COMPLETE, with a non-empty `patch.diff` and a resolvable target, but NO published
  branch ⇒ `D` is held (not built), named on stderr with the reason, and the rest of the run
  goes on;
  (b) `P` COMPLETE and its PR merged ⇒ nothing is folded for it and `D` builds on the base as
  today;
  (c) `P` COMPLETE with an empty or missing `patch.diff` (a close/no-fix disposition) ⇒ nothing
  is folded, `D` is NOT held and builds on the base as today (`merged.is_merged` already says
  True for it, `merged.py:44-45`; `integrate.unpublished` excludes it, `integrate.py:141-153`);
  (d) the pre-wave fold itself fails (`IntegrationError` — e.g. `P`'s branch was deleted and
  the host does not report its PR merged, `integrate.py:252-259`) ⇒ the run stops before
  wave 0, drives nothing, and stderr names the failure the same way the in-run fold's
  "did not integrate; STOPPING" line does (`flow.py:2004-2007`), with no traceback. Nothing is
  built on a base known to be missing a prerequisite.
  `Depends on (merged)` keeps its #186 behaviour (waits for the merge) unchanged.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: Make a re-issued (or any) stack-mode run carry its bundles' out-of-batch,
  COMPLETE, published-but-unmerged prerequisites into the base those bundles build on, so
  dependents are pointed at a line that has them. **One fold point: before the run's first
  wave** (not "before the first wave that needs them"), and only when some bundle in the drive
  set has such a prerequisite; with none, nothing changes. The issue's suggested direction:
  before the run's first wave, fold the published, still-unmerged
  branches of those prerequisites onto the run's integration line (#593's fold merges
  published branches, so this re-creates the earlier run's line from the same commits), then
  point the dependents at that line as usual. A prerequisite carried this way stays out of the
  run's results map (it is not driven). Every same-target bundle of the first wave is then
  pointed at the line, not just `P`'s dependents (as later waves already are). A prerequisite
  that is COMPLETE, patched and targeted but has no published branch holds its dependents (named on stderr, the same way `held_unpushed` holds in-batch
  dependents, `flow.py:1981-1987`, `:712-713`); it never lets them build on the wrong base. A
  merged prerequisite, or one with no patch, needs nothing: its work (or lack of it) is already
  the base. If the pre-wave fold raises, the run stops before wave 0 (criterion case (d)) —
  the same fail-closed stop the in-run fold applies. Transitive prerequisites
  come along for free when the prerequisite's branch was itself cut from an earlier line (its
  branch carries them); do not add a second walk unless the test shows one is needed.
  Applies only when the run publishes in stack mode (`--no-publish` sequences nothing,
  `flow.py:1784-1785`; merge mode merges instead). Update the stack-mode docs paragraph
  (`docs/07-crosscutting.md:640-700`) to say a re-issued run re-folds earlier
  unmerged prerequisites.
  / out of scope: the integration branch's naming / per-batch scoping (#591); `Depends on
  (merged)` semantics (#186 — unchanged); merge mode (#531); retargeting or rebasing earlier
  PRs; pruning old integration branches (#454).

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: pass — C4 PASS — red without the fix, green with it
- C5 added test exercises production, not a copy: pass — 1 added driver-suite test(s) import the production package 'pdca_harness'

## 4. Conformance (Check — stack)
- T1 Structure: none — (no gate configured)
- T2 shape: docs lint + site render link audit: pass — docs lint clean, site render + link audit clean
- T2 host CI parity: target docs-check.yml on the pushed tree: pass — host CI parity on the patched tree — docs lint clean, site render + link audit clean
- T3 runtime: render/update-compat + offline driver suites: pass — root suite OK, driver suite OK
- T4 PR body has a user-impact opener + tracker id in both artifacts: deferred — pr-description.md not drafted yet — the substantive T4 audit of the contribution artifacts runs at publish
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Review issue #616: resumed stack-mode runs must carry earlier published, unmerged prerequisites before building dependents, while held dependents must not cause unnecessary integration lines.

Source citations below resolve under `$PDCA_TARGET` (`target/`); evidence citations resolve in this review directory. The disposable target contains the prerequisite changes needed by this patch; no stale-target caveat was necessary. Verdicts are advisory, not acceptance gates.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The required prerequisite ancestry, continuation of the same integration line, and hold behavior are observable with real Git; the main regression checks the dependent, unrelated first-wave bundle, and next wave (`template/tests/test_flow_resume_stack_prereqs.py:341`; `brief.md:178`). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing the tracked fix while retaining its new tests produced 14 assertion failures among 21 tests, including the missing first-wave stack base; this reproduces the defect without import failures (`template/tests/test_flow_resume_stack_prereqs.py:369`; `review-red.log`). |
| C3 Change | FAIL | Known holds do not fully prevent unnecessary carries: a merge-wait or a held in-batch ancestor leaves D unbuilt, yet unrelated U inherits P; this violates the carry-forward requirement that held dependents start no line (`template/src/pdca_harness/flow.py:866`; `template/src/pdca_harness/flow.py:871`; finding below). |
| C4 Verification (red→green) | PASS | Restoring the patch made all 186 focused/related tests pass, including the same 21 regression cases; this verifies the asserted red→green, but those cases omit the hold-propagation defect found separately (`template/tests/test_flow_resume_stack_prereqs.py:341`; `review-green.log:500`; `gate-logs/C4-verify.log:196`). |
| C5 Causal adequacy | PASS | Carrying actual prerequisite commits before base selection addresses the missing-base cause; real Git ancestry is asserted, and unavailable-host handling is an explicitly required input case rather than a probe masking a load-time side effect (`template/src/pdca_harness/flow.py:2202`; `template/tests/test_flow_resume_stack_prereqs.py:372`; `template/src/pdca_harness/merged.py:90`). |
| T1 Structure | PASS | Both fold sites retain one implementation for branch continuity, lock scope, and re-gating, limiting divergence between resumed and ordinary waves (`template/src/pdca_harness/flow.py:943`; `template/src/pdca_harness/flow.py:2347`). |
| T2 Shape | PASS | Independent docs lint, rendering of 22 pages, internal-link audit, and diff whitespace check passed; the frozen host-parity log agrees (`docs/07-crosscutting.md:677`; `gate-logs/host-ci-docs.log:10`). |
| T3 Runtime | PASS | Independent full driver run passed 2,346 tests with two skips; the frozen root-suite evidence shows 24 tests passed, including Copier render/update cases that this review interpreter cannot run (`review-suite.log`; `gate-logs/T3-suite.log:54`; `gate-logs/T3-suite.log:1855`). |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; their substantive audit must run at publish, as the deferred gate explicitly records (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Confirm affected-path merged and closed/rejected prior art, including the newly changed `merged.py` surface — the brief records narrower path searches, while this target has only one synthetic base commit and no remotes, so independent historical confirmation is unavailable (`brief.md:141`; `template/src/pdca_harness/merged.py:52`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the offline evidence suffices for operational sign-off or require a live resumed-flow check — real Git was exercised, but GitHub/`gh` and build/publish leaves were simulated, leaving live host behavior unexercised despite “External dependencies: none” (`template/tests/test_flow_resume_stack_prereqs.py:26`; `template/tests/test_flow_resume_stack_prereqs.py:290`; `brief.md:128`). |

One substantive finding: **[P2] Account for already-known dependency holds before starting a line.** `_prereqs_to_carry` excludes merge-gated and in-batch edges from its eligibility calculation (`template/src/pdca_harness/flow.py:846`), then selects targets using only its direct prerequisite verdicts (`template/src/pdca_harness/flow.py:866`). `_runnable` applies the omitted holds only after the integration branch has been pushed (`template/src/pdca_harness/flow.py:2214`). Consequently, a bundle that cannot build still causes another bundle's PR to contain unnecessary unmerged work.

I exercised two cases with the patched production flow and real local Git:

- D has `Depends on: P` and `Depends on (merged): Q`; P and Q are COMPLETE with open PRs. Only U builds, D stays PLANNED, but U's published branch contains P.
- A has `Depends on: Q`, where Q is COMPLETE but unpublished; D has `Depends on: A, P`, where P is published and open. A and D both stay PLANNED and only U builds, but U's published branch again contains P.

Both cases print `P_IS_ANCESTOR_OF_UNRELATED_U True` in `review-edge-cases.log`. Reproduce from this directory with `python3 review-edge-cases.py`; the probe uses disposable local repositories and the supplied test fixture. The expected result under the hold-first requirement (`brief.md:178`) is that U stays on the plain base when no buildable dependent needs P. Include merge-wait holds and propagate known holds through in-batch dependencies before selecting carries; merely unfinished in-batch prerequisites that can still run must remain eligible.

Verification used `git stash push` on the three tracked changed files, ran the new test module against the base, restored with `git stash pop`, then ran the focused and full driver suites. The supplied patch was restored unchanged. The production-import scanner also passed independently. All six frozen gate logs were read; none is missing. The local root-suite attempt exited 77 because Copier is not importable by `/usr/bin/python3`; this is a review-host limitation, not a patch defect or evidence that the frozen passing root run failed.

For live validation, use a disposable configured GitHub repository: publish and accept P while leaving its PR open, then resume `pdca flow P D E U` with D depending on P and E depending on D. Confirm P's head is an ancestor of D's recorded base before D builds, the next fold retains P and D for E, and U shares the intended line. Also exercise the two hold cases above and confirm U remains on the plain base after the finding is addressed. The supplied target contains only the unrendered `INTEGRATION.md` template, whose human-only list is TODO; it supplies no additional project-specific human-only items.

### Advisory — adversary

# Adversarial review — issue 616 (stack-resume-carries-unmerged-prereqs)

The red→green evidence holds. Three inputs still break the fix. Each was reproduced with a
scratch test that reuses the shipped fixture (real git, bare `origin`, production
`flow._drive_and_act`); the tests are in `scratch/test_adversary{,2,3}.py` in this sandbox.

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/flow.py:871-872` (`wants` / `lined`) still
  starts the line for a dependent that `_runnable` will hold under its #186 gate
  (`flow.py:711-713`). `_prereqs_to_carry` drops `Depends on (merged)` ids (`flow.py:861`) and
  counts only its own five hold reasons. **Failing case:** D has `Depends on: P` (P from an
  earlier run, published, PR open) and `Depends on (merged): M` (M COMPLETE, PR open). U has
  the same target and no prerequisites. Result: "carrying … issue_P", a force-push of
  `pdca-integration/main-…`, then "issue_D skipped — prerequisite(s) not ready (M)". U is built
  on the line with P under it (`do_base: origin/pdca-integration/main-…`). Before the fix U
  built on plain `main`. This is the iteration-2 sign-off item that was not done ("start a line
  for a prerequisite only if some dependent that needs it is not held"). It also contradicts
  the patch's own claims at `docs/07-crosscutting.md:689` ("A held bundle starts no line") and
  `flow.py:809`. Fix: when deciding whether to start a line, treat an out-of-batch, unmerged
  `Depends on (merged)` prerequisite as a hold, and add the test.

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/flow.py:838` takes `pr_state == "MERGED"` to
  mean "its work is already the base" without checking where the PR merged. `integrate.py:474`
  already refuses to trust such a merge when the record's `base` is not the target base.
  **Failing case:** P0 is published with its PR open against `main`. P has `Stacks on: P0`;
  its `publish.json` has `base: fix/P0`, and its PR was merged into `fix/P0`, not `main`.
  D has `Depends on: P`. Result: no hold, no line, no stderr. D reaches COMPLETE built on
  `origin/main`, and P's head is not an ancestor of that commit. That breaks the brief's
  invariant ("built … on a base that carries all of its declared prerequisites"). Fix: count
  MERGED as "in the base" only when the record's `base` is the target base and the record is
  not an `Onto branch` one (`mode: stacked`). Otherwise carry the branch, or hold the
  dependent.

- NEEDS-HUMAN — the hold messages' advice can lead nowhere (`flow.py:903-908`).
  **Shown by test:** H comes from an earlier run of the same batch. It was accepted, its
  publish failed before the push, and it has a recorded stack base and tip on that batch's
  line. D has `Depends on: H`; D2 has `Depends on: P` (P can be carried). One wave. The run
  prints "Publish it (`pdca publish H`), then re-run". Its own pre-wave fold then starts the
  line fresh and force-pushes over it. After the run, `publish._line_tip_refusal` refuses H
  ("a commit origin's pdca-integration/main-… no longer holds … Re-drive it in a new run
  (#616)", `publish.py:725`). Before the fix, a re-issued run with one wave never folded, so H
  stayed publishable. `publish.py:696` names #616 as the issue that handles resuming across
  runs. **Reasoned from the code, not run:** the `_STALE` advice "Re-publish it" goes through
  publish's new-PR path, which never looks for an existing PR (`publish.py:330`, `:417`,
  `:421`). With P's PR still open, `gh pr create` should fail and the new record gets
  `pr_url: ""`, so the next run holds D again, this time as `_NO_PR`. A human should decide:
  should the pre-wave fold keep the earlier run's line instead of replacing it, or should the
  messages send the user to re-drive the bundle or add the PR URL by hand?

- Evidence (no finding): the C4 log shows 14 of 21 tests red with the production change
  reverted and 21 of 21 green with it. I re-ran the file on the patched target: `Ran 21 tests …
  OK`. The 7 tests that pass before the fix are no-change guards (merged, no-patch, other
  target, no out-of-batch prerequisite, `Depends on (merged)`, `Stacks on`). The tests use the
  production paths `_drive_and_act`, `integrate.fold`, `merged` (only `subprocess.run` faked)
  and `worktree._target`. One weak assertion: "D's PR branch carries P" (patch.diff:931)
  checks the test's own `_publish_bundle` stand-in, not `publish.publish`. It is still tied to
  the production-written `stack-base-tip`, so the impact is small.

- Tried and could not break: the E case (the fold after wave 0 continues the line without
  force); the line surviving a wave that accepts nothing of its target; `gh` missing or
  failing; a closed PR; per-pair holds across targets; dry run (no host call, no holds);
  fail-closed when the pre-wave fold or its re-gate fails. I also looked for false `_STALE`
  holds in the normal order. On the paths I found, nothing rewrites `SUMMARY.md` after
  publish writes `publish.json` (`signoff.record`; `accept_blockers` runs only at accept time).

Housekeeping: my first test run wrote git-ignored `__pycache__/` folders under
`target/template/src/pdca_harness/` and `target/template/tests/`. Later runs used a cache
folder in this sandbox. I did not remove anything.

### Advisory — code-review

# Advisory code review — issue 616 (stack-resume-carries-unmerged-prereqs)

Lenses: correctness bugs the patch introduces, and reuse / simplification / efficiency.
Advisory only. Gates: C4 red→green (gate-logs/C4-verify.log: 14 of 21 new tests fail without
the fix), full suite green (gate-logs/T3-suite.log: 2346 tests OK).

No blocking correctness bug found. I traced the pre-wave fold
(`template/src/pdca_harness/flow.py:2187-2208`), the shared `_fold_onto_line`, the hold/carry
logic in `_prereqs_to_carry`, and the `held_pairs` check in `_runnable`
(`template/src/pdca_harness/flow.py:718`). They match the brief and both carry-forward lists:
holds are worked out before any line starts; PR state is asked before the timestamp check;
`Stacks on` starts no line; holds are per (dependent, prerequisite) pair. The in-run fold
keeps `carried` at the head of every later fold. Already-merged branches are a no-op `git merge`
there, and doing it keeps the carried target in `integ`. The `E` continuation goes through the
`folded_this_run` "continue" path (`template/src/pdca_harness/integrate.py:344-401`), so it
does not force-push. The `merged.py` refactor keeps `is_merged`'s old answers and adds the
`OSError` guard through the shared `_pr_view`.

Minor points, none needing a human decision:

- `template/src/pdca_harness/flow.py:925-940` — `_record_predates_signoff` compares file
  mtimes (modification times). It fails closed, but any copy that does not keep mtimes makes a
  good `publish.json` look older than `SUMMARY.md`. Examples: a manual move to `completed/`
  done with `cp -r` instead of `mv` (`config.py:514-530` calls this archive a manual
  convention), restoring `results/` from git or a backup, or moving to another machine. The
  dependents are then held and the user is told to re-publish a prerequisite that is fine.
  This is safe, not a wrong build. The heuristic was asked for in iteration 1. It is worth one
  line in the docs paragraph (`docs/07-crosscutting.md:676-700`) so a user who hits a false
  `stale` hold knows why.
- `template/src/pdca_harness/flow.py:889-894` — `_recorded_pr` repeats the `pr_url` read that
  `merged._pr_view` already does (`template/src/pdca_harness/merged.py:86-88`), through a
  different `_publish_record` helper (`publish._publish_record` instead of
  `merged._publish_record`). The two disagree on a truthy non-string `pr_url`. `_pr_view` passes
  `str(pr_url)` to `gh`, while `_recorded_pr` returns "", so a failed `gh` call there gets the
  `_NO_PR` message ("records no PR URL") instead of `_UNREAD` (`flow.py:843`). This is an edge
  case. A small public `merged.recorded_pr_url(d)` used by both would remove the duplicate.
- `template/src/pdca_harness/merged.py:96-97` — `_pr_view` now serves `pr_state` too, but its
  stderr line still says "treating as not merged". On the #616 path, the next line on stderr is
  a hold ("held this run …"), not a not-merged wait. "could not read PR state for X (url)" alone
  would be accurate for all three callers. Wording only.

Tests (`template/tests/test_flow_resume_stack_prereqs.py`) use real git against a bare origin.
They patch only `_drive_wave`, `_publish_bundle`, `draft_texts`, and `merged.subprocess` (the
`gh` boundary). They cover the success criterion, cases (a) to (d), the `U` and `E` bundles,
and every carry-forward item. I found no test that misses the code path it claims to test.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T5 Judgment — Confirm affected-path merged and closed/rejected prior art, including the newly changed `merged.py` surface — the brief records narrower path searches, while this target has only one synthetic base commit and no remotes, so independent historical confirmation is unavailable (`brief.md:141`; `template/src/pdca_harness/merged.py:52`).
- [ ] Validation — fitness-to-purpose — Decide whether the offline evidence suffices for operational sign-off or require a live resumed-flow check — real Git was exercised, but GitHub/`gh` and build/publish leaves were simulated, leaving live host behavior unexercised despite “External dependencies: none” (`template/tests/test_flow_resume_stack_prereqs.py:26`; `template/tests/test_flow_resume_stack_prereqs.py:290`; `brief.md:128`).
- [ ] `template/src/pdca_harness/flow.py:871-872` (`wants` / `lined`) still starts the line for a dependent that `_runnable` will hold under its #186 gate (`flow.py:711-713`). `_prereqs_to_carry` drops `Depends on (merged)` ids (`flow.py:861`) and counts only its own five hold reasons. **Failing case:** D has `Depends on: P` (P from an earlier run, published, PR open) and `Depends on (merged): M` (M COMPLETE, PR open). U has the same target and no prerequisites. Result: "carrying … issue_P", a force-push of `pdca-integration/main-…`, then "issue_D skipped — prerequisite(s) not ready (M)". U is built on the line with P under it (`do_base: origin/pdca-integration/main-…`). Before the fix U built on plain `main`. This is the iteration-2 sign-off item that was not done ("start a line for a prerequisite only if some dependent that needs it is not held"). It also contradicts the patch's own claims at `docs/07-crosscutting.md:689` ("A held bundle starts no line") and `flow.py:809`. Fix: when deciding whether to start a line, treat an out-of-batch, unmerged `Depends on (merged)` prerequisite as a hold, and add the test.
- [ ] `template/src/pdca_harness/flow.py:838` takes `pr_state == "MERGED"` to mean "its work is already the base" without checking where the PR merged. `integrate.py:474` already refuses to trust such a merge when the record's `base` is not the target base. **Failing case:** P0 is published with its PR open against `main`. P has `Stacks on: P0`; its `publish.json` has `base: fix/P0`, and its PR was merged into `fix/P0`, not `main`. D has `Depends on: P`. Result: no hold, no line, no stderr. D reaches COMPLETE built on `origin/main`, and P's head is not an ancestor of that commit. That breaks the brief's invariant ("built … on a base that carries all of its declared prerequisites"). Fix: count MERGED as "in the base" only when the record's `base` is the target base and the record is not an `Onto branch` one (`mode: stacked`). Otherwise carry the branch, or hold the dependent.
- [ ] the hold messages' advice can lead nowhere (`flow.py:903-908`). **Shown by test:** H comes from an earlier run of the same batch. It was accepted, its publish failed before the push, and it has a recorded stack base and tip on that batch's line. D has `Depends on: H`; D2 has `Depends on: P` (P can be carried). One wave. The run prints "Publish it (`pdca publish H`), then re-run". Its own pre-wave fold then starts the line fresh and force-pushes over it. After the run, `publish._line_tip_refusal` refuses H ("a commit origin's pdca-integration/main-… no longer holds … Re-drive it in a new run (#616)", `publish.py:725`). Before the fix, a re-issued run with one wave never folded, so H stayed publishable. `publish.py:696` names #616 as the issue that handles resuming across runs. **Reasoned from the code, not run:** the `_STALE` advice "Re-publish it" goes through publish's new-PR path, which never looks for an existing PR (`publish.py:330`, `:417`, `:421`). With P's PR still open, `gh pr create` should fail and the new record gets `pr_url: ""`, so the next run holds D again, this time as `_NO_PR`. A human should decide: should the pre-wave fold keep the earlier run's line instead of replacing it, or should the messages send the user to re-drive the bundle or add the PR URL by hand?
- [x] **Hidden behaviour change for bundles that don't depend on P.** The brief says "point the dependents at that line as usual" (Scope). However, `_point_at_integration` points **every** runnable bundle of the same `(repo, base)` target at `integ[target]`, not just the ones that depend on P (`flow.py:736-741`). If the fold runs before wave 0 and fills `integ`/`folded_tips`, as the brief's "Citations expected" section requires, then every wave-0 bundle of that target gets built on, and has its PR cut from, a line that carries P's unmerged commits. That applies even when the bundle has nothing to do with P, so its PR diff will show P's changes until P merges (`integrate.py:18-21`). The brief needs to either state this as intended (same as later-wave stacking) and add an assertion to the criterion, or limit the stack base to dependents. Related: the Scope says both "before the first wave that needs them" and "before the run's first wave". Those are different designs when D sits in wave ≥1, so the brief should pick one.
- [x] **Companion case (a) will hold dependents of a no-patch prerequisite unless the brief rules it out.** The criterion says "`P` COMPLETE with NO published branch ⇒ `D` is held". A COMPLETE prerequisite with an empty or missing `patch.diff` (a close/no-fix disposition) also has no published branch, but it has nothing to carry. `merged.is_merged` returns True for it (`merged.py:44-45`), and `integrate.unpublished` deliberately excludes it and patched bundles with no target ("A patched bundle with no target is neither", `integrate.py:153`; `_fold_candidates`, `:141-142`). Today D builds in that case. Following the criterion as written would block it, and there is no test to catch that. The criterion should say "patched, targeted, and with no published branch", and the test should cover the no-patch case (D builds).
- [x] **The `Depends on: 591` edge is not backed by anything the criterion checks, and every citation was taken from the code before #591.** `dependency-state.json` shows 591 exists and is `PLANNED` (not merged), so the dependency resolves, but #591 hasn't landed. The brief was "Verified against … `c67a14d`" without #591. Yet the Ordering note says this work "must build on #591's naming and fold signature". That is the same `integrate.fold(…, folded_this_run=…)` signature and the `integration_branch(cfg, base)` naming (`integrate.py:62-68`, `:219-222`) that Do is told to feed. If #591 changes either one, all of the "Citations expected" line numbers and the fixture's assumptions go stale mid-run. Also, no assertion in the success criterion depends on per-batch naming, so a reviewer can't tell whether the edge is actually needed. Either name the specific #591 behaviour the test depends on, or drop the edge. `Conflicts with: 590` can't be checked from these inputs (it isn't in `dependency-state.json`), so the human should confirm #590 exists and touches `flow.py:1815-1860`.
- [x] **The brief doesn't cover the case where the merged check says "not merged" but the PR has actually merged.** `merged.is_merged` treats any `gh` failure, and a branch pushed with no `pr_url`, as not merged (`merged.py:48-55`). In that case the pre-wave fold will try to merge a branch that may already be deleted, and `_gone_branch` then raises `IntegrationError` unless the host reports the PR merged (`integrate.py:252-259`). The in-run handler turns that error into "wave k did not integrate; STOPPING" (`flow.py:2004-2007`). A fold that fails before wave 0 needs its own decision: stop the run, or hold only the affected dependents. Companion case (a) says "the rest of the run goes on", but the brief only says that for the case where nothing was published. The brief should state what happens when the pre-wave fold itself fails.

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: iterated-to-Plan
- Iteration delta (if iterating): Three Do attempts have each closed the previous fix list and surfaced 3-5 new edge cases in the same hold/carry logic (patch now ~1400 lines). Re-check the approach in Plan before another build: decide whether to re-think or split it. Open findings the new plan must answer: - Holds must be known before any line starts. The current carry logic counts only its own hold reasons, so a dependent held by a `Depends on (merged)` wait, or by a held in-batch prerequisite, still starts a line and puts P's unmerged work under unrelated same-target bundles (U). This contradicts the patch's own docs ("A held bundle starts no line"). - "PR MERGED" is treated as "in the base" without checking where it merged. A PR merged into another fix's branch (stacked record, base != target base) lets D build silently without P. Count MERGED only when the record's base is the target base and it is not a stacked record; otherwise carry or hold. - Hold-message advice can loop: the pre-wave fold force-replaces an earlier run's line (so an accepted-but-unpublished H becomes unpublishable), and "re-publish" likely fails while the old PR is open. Decide: keep and extend the earlier run's line, or change the advice (re-drive / add PR URL by hand). Consider splitting: (1) carrying published unmerged prerequisites onto the line, vs (2) hold rules and user-facing hold messages.
- By / date: Eduard Ralph / 2026-10-04

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 4 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
