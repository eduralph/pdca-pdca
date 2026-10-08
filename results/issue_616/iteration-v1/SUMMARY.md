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

Fix resumed stack-mode publishing runs so dependents build on their earlier, published-but-unmerged prerequisites, and hold or stop when those prerequisites cannot be carried.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The recovery contract is falsifiable: prerequisite ancestry must exist before the dependent builds, persist into subsequent waves, and include unrelated first-wave bundles of the same target; target/template/tests/test_flow_resume_stack_prereqs.py:266 and target/docs/07-crosscutting.md:677. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing the production/docs changes reproduced four assertion failures in nine tests: missing prerequisite base, missing hold, missing early stop, and lost target line; reviewer-red.log:1, grounded at target/template/tests/test_flow_resume_stack_prereqs.py:294, :337, :356 and :417. |
| C3 Change | PASS | Dependents now receive the missing prerequisite commits before building, while unpublished prerequisites hold their dependents and fold failure prevents wave zero; target/template/src/pdca_harness/flow.py:2050, :2064, :2074 and :2118. |
| C4 Verification (red→green) | PASS | Restoring the same stash made all nine regression tests pass against real local Git repositories; assertions cover ancestry, recorded base tips, and continuation without force-push; reviewer-green.log:1 and target/template/tests/test_flow_resume_stack_prereqs.py:292. |
| C5 Causal adequacy | PASS | The omitted integration input is restored at its source and retained through later folds; the tests exercise production flow/integration and reproduce the forbidden failure, with no capability probe masking a load-time cause; target/template/src/pdca_harness/flow.py:2061 and :2205; target/template/tests/test_flow_resume_stack_prereqs.py:247. |
| T1 Structure | PASS | Sharing the fold operation preserves one batch identity and the existing lock-through-re-gate boundary, preventing the pre-wave and later-wave paths from diverging; target/template/src/pdca_harness/flow.py:809 and :830. |
| T2 Shape | PASS | Independently rerun docs lint, rendering of 22 pages, internal-link audit, and diff whitespace checks all passed; the recovery behavior is documented at target/docs/07-crosscutting.md:677; frozen parity evidence agrees at gate-logs/host-ci-docs.log:10. |
| T3 Runtime | PASS | Independent driver discovery passed 2,334 tests with two skips; the frozen root-suite log shows 24 passing tests including real render/update cases, which could not be rerun here because Copier is absent; reviewer-driver-suite.log:1798 and gate-logs/T3-suite.log:38. |
| T4 Contribution | N/A | Contribution artifacts are intentionally drafted after Check; the substantive audit is owed to the mandatory publish-time rerun, as recorded in gate-logs/T4-contribution.log:10. |
| T5 Judgment | NEEDS-HUMAN | Confirm the affected-path prior-art search covers merged history and closed/rejected work, including the changed docs and new test path — the brief records searches for flow/integrate and related code, but this one-commit, no-remote snapshot cannot independently establish the historical conclusion; brief.md:141 and target/template/src/pdca_harness/flow.py:748. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the demonstrated offline recovery is sufficient for intended operation, including unrelated same-target first-wave PRs carrying prerequisite changes — real Git ancestry was exercised, but live host responses and build/sign-off/publisher leaves were not; target/template/tests/test_flow_resume_stack_prereqs.py:18, :200 and :247; target/docs/07-crosscutting.md:679. |

No confirmed patch defects were found. This is an advisory review; acceptance remains the human's decision.

All source citations above resolve in the supplied `$PDCA_TARGET` (`target/`); brief and log citations refer to the supplied evidence in the review directory. The target contains the prerequisite batch-scoping and recovery code, and the patch was already applied successfully. No stale-target caveat was needed. The production/docs stash was restored, the new test remained available for both legs, and the target has exactly its original three changed paths with no remaining stash.

Independent evidence:

- Ran `PYTHONPATH=src python3 -m unittest tests.test_flow_resume_stack_prereqs` from `target/template` with tracked production/docs changes stashed, then again after `git stash pop`. Results: nine tests, four assertion failures before; nine tests, all passing after. Logs: `reviewer-red.log` and `reviewer-green.log`.
- Ran `PYTHONPATH=src python3 -m unittest discover -s tests` from `target/template`: 2,334 tests in 49.872 seconds, `OK (skipped=2)`. Log: `reviewer-driver-suite.log`. Test temporary files were confined through `TMPDIR` under this review directory.
- Ran the repository's `template/scripts/checks/test_exercises_production.py` against the supplied patch with `PDCA_PROD_PACKAGE=pdca_harness`: the added test imports production. Inspection also confirms that production `_drive_and_act` and `integrate.fold` execute; mocked leaves do not replace the integration algorithm.
- Ran `docs/publishing/tools/lint_docs.py` and `docs/publishing/tools/render_site.py --check --out ../reviewer-site` from `target`: lint clean, 22 pages rendered, link audit clean. `git -C target diff --check` was clean.
- Read all six supplied gate logs. Instance-scoped gate wrappers were not available in the target; their absence is expected. For root render/update coverage, `importlib.util.find_spec("copier")` returned `None` locally, while `gate-logs/T3-suite.log:38` explicitly shows those cases executing successfully on the gate host. This is a reviewer-host limitation, not an unmet dependency of the frozen verification.
- Investigated local prior-art availability: affected-path `git log --all` returns only synthetic base commit `39b81d8`; `git remote -v` is empty. The brief's reported merged/closed-work search therefore cannot be independently settled from this artifact-only snapshot. The available integration template has no enumerated additional human-only items (`target/template/docs/INTEGRATION.md.jinja:80`); its placeholder is not evidence of an unseen project rule.

The fixture can exhibit the claimed failure, as the red leg demonstrates; it is not a topology that makes the invariant vacuous. Its limits are explicit: it proves Git ancestry and stack-base selection with stubbed leaves and host responses, not a live end-to-end hosted recovery. Those limits belong to the validation decision above.

### Advisory — adversary

# Adversarial review — issue 616 (stack-resume-carries-unmerged-prereqs)

**Evidence: re-run, and it holds.** I re-ran `tests.test_flow_resume_stack_prereqs` on a scratch copy of `$PDCA_TARGET`. With the fix, all 9 pass. With `template/src/pdca_harness/flow.py` reset to `HEAD` (the pre-fix base), 4 fail: the criterion case, the line-outlives-a-wave case, case (a) and case (d). That matches `gate-logs/C4-verify.log`. The 5 that pass pre-fix are the "unchanged behaviour" cases ((b), (c), `Depends on (merged)`, other target, no out-of-batch prerequisite), so passing pre-fix is expected for them. The core assertions run through production code: the real `flow._drive_and_act`, `_prereqs_to_carry` and `integrate.fold`, with real git against a bare `origin`. I could not refute the main criterion: wave 0 is pointed at a line that holds P, and the fold after wave 0 continues it without a force-push. The findings below are inputs the patch handles wrongly or did not consider.

- NEEDS-HUMAN — **`Stacks on` edges are now carried too, which changes a case that was not broken.** `template/src/pdca_harness/flow.py:788` walks `waves.declared_deps`, which includes `Stacks on` (`waves.py:39-48`). Before the fix, a wave-0 `D` with `- **Stacks on:** P` (P out of batch, published, PR open) already built on P: its stack base was empty, so `publish._stack_base_branch` returned `fix/P` (`publish.py:738`). On an own-repo setup its PR also opened with `--base fix/P` (`publish.py:282`), so it showed only D's diff. After the fix, D *and the unrelated wave-0 bundle U* both get the integration line as their stack base, and the run force-pushes a new line. Probe output: pre-fix `{'issue_D': ('', 'fix/P'), 'issue_U': ('', None)}`, pushes `[]`; post-fix both `('pdca-integration/main-r…', 'pdca-integration/main-r…')`, one `--force` push. So D's PR now targets `main` and shows P's changes, and U's PR does too. The brief's defect and criterion are about `Depends on: P` only. Should a legacy (#123) `Stacks on` edge keep its old PR-against-parent behaviour, and should it alone be enough to re-point every same-target wave-0 bundle? That is a scope call. No test covers it.

- NEEDS-HUMAN [impl] — **A dependent on another target is held, though the new docstring says it is left alone.** `_prereqs_to_carry` skips a prerequisite whose target differs from the dependent's ("the dependent builds as it always has", `flow.py:770-772`). But `held_prereqs` stores only the prerequisite's *name* (`flow.py:2052`), and `_runnable` holds *every* dependent of a held name (`flow.py:713`). Failing case: P (`org/repo @ main`, COMPLETE, patched, unpublished); D (`main`, `Depends on: P`); D2 (`org/repo @ dev`, `Depends on: P`). Post-fix result is `{'D': 'PLANNED', 'D2': 'PLANNED'}`. The hold line names only `issue_D`, but D2 is skipped too ("prerequisite(s) not ready (P)"). Pre-fix both were COMPLETE. Either hold by (prerequisite, dependent) pair, or change the docstring and the stderr line to say cross-target dependents are held too.

- NEEDS-HUMAN [impl] — **A missing `gh` now crashes the run with a traceback for a plain `Depends on`.** `flow.py:797` calls `merged.is_merged` for every out-of-batch `Depends on` / `Stacks on` prerequisite that is COMPLETE, patched and same-target, including in a dry run (stub publisher). `merged.is_merged` calls `gh` at `merged.py:50` with no `OSError` guard; `merged_head` has one (`merged.py:75-78`). Reproduced: with `PATH` not containing `gh`, `flow._prereqs_to_carry(cfg, [D], {"issue_D"}, dry=True)`, where P has a recorded `pr_url`, raises `FileNotFoundError: 'gh'`. That error escapes `_drive_and_act` before wave 0. Before the fix, only `Depends on (merged)` reached `gh`. The brief's failure paths ask for "no traceback". Catch `OSError` around the call, treating it as "not merged" the way `merged_head` does.

- NEEDS-HUMAN — **The pre-wave fold trusts a `publish.json` that the in-run fold explicitly distrusts.** `flow.py:799` asks `integrate.unpublished([p])` with no `pushed=` set, so any `publish.json` that names a branch counts as "carry". But `flow.py:1980-1981` and `:2187-2200` say a record on disk cannot tell a fresh push from an old one: "An iterate keeps an earlier attempt's publish.json". Failing case: in run N, P is re-accepted after an iterate, and its re-publish fails before the push. The in-run fold holds P (`held_unpushed`), and `fix/P` on origin still holds the *rejected* earlier version. The operator re-issues the flow, as the docs say to. P is now out of batch, COMPLETE, and its `publish.json` names `fix/P`, so it is carried. D builds on the rejected P, with no message. What on-disk signal should mark such a record as stale (for example, `publish.json` older than the sign-off)? That needs a design decision, so I left off `[impl]`.

- NEEDS-HUMAN — **Split children adopted mid-run are never checked.** `_prereqs_to_carry` runs once, at `flow.py:2050`, over `bundles` as they stand before wave 0. Children adopted after wave k (`flow.py:2131`) join the drive set later. Failing case: parent A splits in wave 0, and its child A1 declares `Depends on: P2`, which A did not. P2 is out of batch, COMPLETE and unmerged. A1 is pointed at whatever line its target has (no P2), or at the bare base. If P2 is unpublished, A1 is not held either. So the brief's invariant ("every bundle a stack-mode run builds … carries all of its declared prerequisites") fails for adopted children. Children from recovery seeds at `k=-1` are covered, because that splice runs before line 2050. The single pre-wave fold point was a deliberate brief choice, so this is a scope question, not a builder slip.

- Minor, not a refutation: the assertion at `template/tests/test_flow_resume_stack_prereqs.py:300` ("D's PR branch is cut from that commit, so it carries P") checks the test's own `_publish_bundle` stub (`:219`), which cuts from the recorded tip by construction. It does not test production `publish`'s cut-from-tip path. The brief allows stubbing publish, and the stack-base and on-origin assertions around it do go through production code, so this only weakens that one line.

- Gate rows: nothing in `check-gates.json` is overstated. C4's red→green reproduces as logged. C5 is only an import check, but the test really does drive production `_drive_and_act`. T4 is honestly `deferred`.

### Advisory — code-review

# Advisory code review — issue 616 (stack-resume-carries-unmerged-prereqs)

Lens: bugs the patch introduces, plus reuse and simplification. Advisory only; this never gates.

Overall: the patch is in good shape. Moving the fold and re-gate into `_fold_onto_line` keeps the in-run behaviour the same: an `IntegrationError` or a red re-gate still stops the loop, and `folded_tips` is still written before the re-gate. The pre-wave fold now uses that same helper, so the two fold points cannot drift apart. Two small correctness gaps and one note follow.

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/flow.py:793` vs `:713` and `:2052`. Holds are tracked per prerequisite, not per dependent. `_prereqs_to_carry` skips a dependent whose `(repo, base)` target differs from the prerequisite's (`:793`), or that has no target (`:785`). Its docstring says such a dependent "builds as it always has". But `drive_and_act` puts the prerequisite's *name* into `held_prereqs` (`:2052`), and `_runnable` holds any dependent that names it (`:713`). Example: `P` targets repo A and is unpublished. `D1` on A and `D2` on B both depend on `P`. `D2` is also held, even though the code meant to let it build. The specific "has no published branch … held" message (`:2053-2056`) lists only `D1`. `D2` gets only the generic "skipped — prerequisite(s) not ready" line. Holding too much is the safe direction, but the code contradicts its own docstring and the stderr report is incomplete. Fix: either hold per dependent name, or say in the docstring that any dependent of a held prerequisite waits. Add a test with a cross-target dependent.
- `template/src/pdca_harness/flow.py:2050` — `_prereqs_to_carry` runs once, over `bundles` as they stand before wave 0. It does see the `k=-1` recovery adoption, which runs earlier (`:2024-2027`). It does not see children that a mid-run split adopts (`_adopt_split_children` at `:2131`). A child adopted after wave 0 with an out-of-batch, COMPLETE, unmerged prerequisite that no wave-0 bundle shares is neither carried nor held. That is the original #616 hazard, now limited to this path. The brief fixes "one fold point, before the first wave", so this is a scope question, not a defect. A child usually shares its parent's prerequisites, which were already carried, so the gap is small. Worth a sentence in the docstring or a follow-up issue.
- `template/src/pdca_harness/flow.py:797` — the "carry or base" choice depends on `merged.is_merged`, which treats any `gh` failure as "not merged" (`merged.py:52-55`). If `gh` is unreachable, an already-merged prerequisite gets carried. If its branch was deleted after the merge, the pre-wave fold raises, and the whole run stops before wave 0 (`:2064-2065`), including bundles that do not depend on it. This fails closed, which matches case (d) of the brief, so no change is needed. Operators may still see a full-run stop caused by a `gh` outage. `_runnable` has the same exposure for `Depends on (merged)`. No action unless the human wants a clearer message.
- Reuse: no duplication found. `_prereqs_to_carry` reuses `integrate._fold_candidates` and `integrate.unpublished` (the fold's own definitions) and `merged.is_merged`, rather than re-implementing them. The local `target()` helper (`flow.py:775-777`) only adds a `brief.md` existence check around `publish._resolve_target`, which is fine. Passing `carried` into every in-run fold (`:2206`) costs one extra entry per fold, and the in-line comment explains why: it keeps every target the line covers in `integ`.
- Tests (`template/tests/test_flow_resume_stack_prereqs.py`) cover the main case plus `E` and `U`, cases (a) through (d), and a line surviving a wave that accepts nothing of its target. The tests use real git against a bare origin and a non-stub publisher, so the assertions are not trivially true. Two cases are not covered: the cross-target over-hold above, and an out-of-batch `Depends on (merged)` prerequisite, to check that it is still never carried. The gates listed C4, T2 and T3 as passing.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T5 Judgment — Confirm the affected-path prior-art search covers merged history and closed/rejected work, including the changed docs and new test path — the brief records searches for flow/integrate and related code, but this one-commit, no-remote snapshot cannot independently establish the historical conclusion; brief.md:141 and target/template/src/pdca_harness/flow.py:748.
- [ ] Validation — fitness-to-purpose — Decide whether the demonstrated offline recovery is sufficient for intended operation, including unrelated same-target first-wave PRs carrying prerequisite changes — real Git ancestry was exercised, but live host responses and build/sign-off/publisher leaves were not; target/template/tests/test_flow_resume_stack_prereqs.py:18, :200 and :247; target/docs/07-crosscutting.md:679.
- [ ] **`Stacks on` edges are now carried too, which changes a case that was not broken.** `template/src/pdca_harness/flow.py:788` walks `waves.declared_deps`, which includes `Stacks on` (`waves.py:39-48`). Before the fix, a wave-0 `D` with `- **Stacks on:** P` (P out of batch, published, PR open) already built on P: its stack base was empty, so `publish._stack_base_branch` returned `fix/P` (`publish.py:738`). On an own-repo setup its PR also opened with `--base fix/P` (`publish.py:282`), so it showed only D's diff. After the fix, D *and the unrelated wave-0 bundle U* both get the integration line as their stack base, and the run force-pushes a new line. Probe output: pre-fix `{'issue_D': ('', 'fix/P'), 'issue_U': ('', None)}`, pushes `[]`; post-fix both `('pdca-integration/main-r…', 'pdca-integration/main-r…')`, one `--force` push. So D's PR now targets `main` and shows P's changes, and U's PR does too. The brief's defect and criterion are about `Depends on: P` only. Should a legacy (#123) `Stacks on` edge keep its old PR-against-parent behaviour, and should it alone be enough to re-point every same-target wave-0 bundle? That is a scope call. No test covers it.
- [ ] **A dependent on another target is held, though the new docstring says it is left alone.** `_prereqs_to_carry` skips a prerequisite whose target differs from the dependent's ("the dependent builds as it always has", `flow.py:770-772`). But `held_prereqs` stores only the prerequisite's *name* (`flow.py:2052`), and `_runnable` holds *every* dependent of a held name (`flow.py:713`). Failing case: P (`org/repo @ main`, COMPLETE, patched, unpublished); D (`main`, `Depends on: P`); D2 (`org/repo @ dev`, `Depends on: P`). Post-fix result is `{'D': 'PLANNED', 'D2': 'PLANNED'}`. The hold line names only `issue_D`, but D2 is skipped too ("prerequisite(s) not ready (P)"). Pre-fix both were COMPLETE. Either hold by (prerequisite, dependent) pair, or change the docstring and the stderr line to say cross-target dependents are held too.
- [ ] **A missing `gh` now crashes the run with a traceback for a plain `Depends on`.** `flow.py:797` calls `merged.is_merged` for every out-of-batch `Depends on` / `Stacks on` prerequisite that is COMPLETE, patched and same-target, including in a dry run (stub publisher). `merged.is_merged` calls `gh` at `merged.py:50` with no `OSError` guard; `merged_head` has one (`merged.py:75-78`). Reproduced: with `PATH` not containing `gh`, `flow._prereqs_to_carry(cfg, [D], {"issue_D"}, dry=True)`, where P has a recorded `pr_url`, raises `FileNotFoundError: 'gh'`. That error escapes `_drive_and_act` before wave 0. Before the fix, only `Depends on (merged)` reached `gh`. The brief's failure paths ask for "no traceback". Catch `OSError` around the call, treating it as "not merged" the way `merged_head` does.
- [ ] **The pre-wave fold trusts a `publish.json` that the in-run fold explicitly distrusts.** `flow.py:799` asks `integrate.unpublished([p])` with no `pushed=` set, so any `publish.json` that names a branch counts as "carry". But `flow.py:1980-1981` and `:2187-2200` say a record on disk cannot tell a fresh push from an old one: "An iterate keeps an earlier attempt's publish.json". Failing case: in run N, P is re-accepted after an iterate, and its re-publish fails before the push. The in-run fold holds P (`held_unpushed`), and `fix/P` on origin still holds the *rejected* earlier version. The operator re-issues the flow, as the docs say to. P is now out of batch, COMPLETE, and its `publish.json` names `fix/P`, so it is carried. D builds on the rejected P, with no message. What on-disk signal should mark such a record as stale (for example, `publish.json` older than the sign-off)? That needs a design decision, so I left off `[impl]`.
- [ ] **Split children adopted mid-run are never checked.** `_prereqs_to_carry` runs once, at `flow.py:2050`, over `bundles` as they stand before wave 0. Children adopted after wave k (`flow.py:2131`) join the drive set later. Failing case: parent A splits in wave 0, and its child A1 declares `Depends on: P2`, which A did not. P2 is out of batch, COMPLETE and unmerged. A1 is pointed at whatever line its target has (no P2), or at the bare base. If P2 is unpublished, A1 is not held either. So the brief's invariant ("every bundle a stack-mode run builds … carries all of its declared prerequisites") fails for adopted children. Children from recovery seeds at `k=-1` are covered, because that splice runs before line 2050. The single pre-wave fold point was a deliberate brief choice, so this is a scope question, not a builder slip.
- [ ] `template/src/pdca_harness/flow.py:793` vs `:713` and `:2052`. Holds are tracked per prerequisite, not per dependent. `_prereqs_to_carry` skips a dependent whose `(repo, base)` target differs from the prerequisite's (`:793`), or that has no target (`:785`). Its docstring says such a dependent "builds as it always has". But `drive_and_act` puts the prerequisite's *name* into `held_prereqs` (`:2052`), and `_runnable` holds any dependent that names it (`:713`). Example: `P` targets repo A and is unpublished. `D1` on A and `D2` on B both depend on `P`. `D2` is also held, even though the code meant to let it build. The specific "has no published branch … held" message (`:2053-2056`) lists only `D1`. `D2` gets only the generic "skipped — prerequisite(s) not ready" line. Holding too much is the safe direction, but the code contradicts its own docstring and the stderr report is incomplete. Fix: either hold per dependent name, or say in the docstring that any dependent of a held prerequisite waits. Add a test with a cross-target dependent.
- [ ] **Hidden behaviour change for bundles that don't depend on P.** The brief says "point the dependents at that line as usual" (Scope). However, `_point_at_integration` points **every** runnable bundle of the same `(repo, base)` target at `integ[target]`, not just the ones that depend on P (`flow.py:736-741`). If the fold runs before wave 0 and fills `integ`/`folded_tips`, as the brief's "Citations expected" section requires, then every wave-0 bundle of that target gets built on, and has its PR cut from, a line that carries P's unmerged commits. That applies even when the bundle has nothing to do with P, so its PR diff will show P's changes until P merges (`integrate.py:18-21`). The brief needs to either state this as intended (same as later-wave stacking) and add an assertion to the criterion, or limit the stack base to dependents. Related: the Scope says both "before the first wave that needs them" and "before the run's first wave". Those are different designs when D sits in wave ≥1, so the brief should pick one.
- [ ] **Companion case (a) will hold dependents of a no-patch prerequisite unless the brief rules it out.** The criterion says "`P` COMPLETE with NO published branch ⇒ `D` is held". A COMPLETE prerequisite with an empty or missing `patch.diff` (a close/no-fix disposition) also has no published branch, but it has nothing to carry. `merged.is_merged` returns True for it (`merged.py:44-45`), and `integrate.unpublished` deliberately excludes it and patched bundles with no target ("A patched bundle with no target is neither", `integrate.py:153`; `_fold_candidates`, `:141-142`). Today D builds in that case. Following the criterion as written would block it, and there is no test to catch that. The criterion should say "patched, targeted, and with no published branch", and the test should cover the no-patch case (D builds).
- [ ] **The `Depends on: 591` edge is not backed by anything the criterion checks, and every citation was taken from the code before #591.** `dependency-state.json` shows 591 exists and is `PLANNED` (not merged), so the dependency resolves, but #591 hasn't landed. The brief was "Verified against … `c67a14d`" without #591. Yet the Ordering note says this work "must build on #591's naming and fold signature". That is the same `integrate.fold(…, folded_this_run=…)` signature and the `integration_branch(cfg, base)` naming (`integrate.py:62-68`, `:219-222`) that Do is told to feed. If #591 changes either one, all of the "Citations expected" line numbers and the fixture's assumptions go stale mid-run. Also, no assertion in the success criterion depends on per-batch naming, so a reviewer can't tell whether the edge is actually needed. Either name the specific #591 behaviour the test depends on, or drop the edge. `Conflicts with: 590` can't be checked from these inputs (it isn't in `dependency-state.json`), so the human should confirm #590 exists and touches `flow.py:1815-1860`.
- [ ] **The brief doesn't cover the case where the merged check says "not merged" but the PR has actually merged.** `merged.is_merged` treats any `gh` failure, and a branch pushed with no `pr_url`, as not merged (`merged.py:48-55`). In that case the pre-wave fold will try to merge a branch that may already be deleted, and `_gone_branch` then raises `IntegrationError` unless the host reports the PR merged (`integrate.py:252-259`). The in-run handler turns that error into "wave k did not integrate; STOPPING" (`flow.py:2004-2007`). A fold that fails before wave 0 needs its own decision: stop the run, or hold only the affected dependents. Companion case (a) says "the rest of the run goes on", but the brief only says that for the case where nothing was published. The brief should state what happens when the pre-wave fold itself fails.

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: iterated-to-Do
- Iteration delta (if iterating): The core fix (pre-wave fold of out-of-batch, published, unmerged prerequisites) is sound; keep it. Fix these before resubmitting: - `Stacks on` edges must keep their pre-fix behaviour (PR against the parent branch, no re-pointing of wave-0 bundles). Only `Depends on` triggers the pre-wave carry. Add a test. - Hold per (prerequisite, dependent) pair: a cross-target dependent of an unpublished prerequisite must build as the docstring says, and the hold message must name exactly the held dependents. Add a cross-target test. - Guard `merged.is_merged` against a missing `gh` (OSError → "not merged", as `merged_head` does) so a plain `Depends on` never crashes the run with a traceback. - Do not silently carry a possibly stale `publish.json` (e.g. one older than the bundle's latest sign-off, left from a rejected attempt): hold its dependents and name it on stderr instead of building on it. - Mid-run split children are still out of scope; note the gap in the `_prereqs_to_carry` docstring.
- By / date: Eduard Ralph / 2026-10-04

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 4 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
