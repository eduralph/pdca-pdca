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

Review issue #616: make resumed stack-mode runs carry earlier published, unmerged prerequisites into the base used to build their dependents.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The missing-prerequisite failure has observable ancestry, base-selection, hold and stop criteria; the mixed-edge scope decision is isolated under T5 (brief.md:23; brief.md:164). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing the tracked production changes while retaining the new tests produced eight assertion failures across 14 tests, including the absent prerequisite line (reviewer-red.log:1; target/template/tests/test_flow_resume_stack_prereqs.py:341). |
| C3 Change | PASS | For the specified plain dependency cases, dependents receive the prerequisite commits or are explicitly held; stale records, cross-target holds and missing gh have exercised regressions (target/template/src/pdca_harness/flow.py:809; target/template/src/pdca_harness/flow.py:2108; target/template/src/pdca_harness/merged.py:51). |
| C4 Verification (red→green) | PASS | Restoring the patch made all 14 tests pass with real git ancestry and append-only push assertions; this verifies the stated offline contract, with live-host limits reserved for Validation (reviewer-green.log:3; target/template/tests/test_flow_resume_stack_prereqs.py:341; gate-logs/C4-verify.log:10). |
| C5 Causal adequacy | PASS | The change restores the missing commits before driving wave 0 and retains them through later folds; it removes the base-selection cause rather than concealing it with a capability probe (target/template/src/pdca_harness/flow.py:2130; target/template/src/pdca_harness/flow.py:2275; gate-logs/C5-prod-path.log:10). |
| T1 Structure | PASS | Pre-wave and subsequent folds share batch identity, tip tracking and the lock covering fold plus re-gate, preserving the existing integration ownership contract (target/template/src/pdca_harness/flow.py:868; target/template/src/pdca_harness/flow.py:889). |
| T2 Shape | PASS | Independent docs lint, 22-page rendering, internal-link audit and git diff whitespace check passed; the frozen host-parity log also records these checks, not a hosted CI execution (reviewer-docs.log:2; gate-logs/T2-docs.log:10; gate-logs/host-ci-docs.log:10). |
| T3 Runtime | PASS | The independent driver suite ran 2,339 tests successfully with two skips; render/update compatibility rests on the frozen 24-test passing run because local Python cannot import copier (reviewer-suite.log:1798; gate-logs/T3-suite.log:42; gate-logs/T3-suite.log:54; reviewer-root-suite.log:7). |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the deferred gate explicitly owes its substantive audit to publish (gate-logs/T4-contribution.log:10). |
| T5 Judgment | NEEDS-HUMAN | Decide whether mixed-edge runs may change a legacy Stacks on PR base from its parent branch to main, or require Plan re-entry: the all-same-target line rule conflicts with the carry-forward preservation requirement in this case (brief.md:164; target/template/src/pdca_harness/flow.py:834; target/template/src/pdca_harness/publish.py:282; reviewer-mixed-stacks.log:2). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the offline result is sufficient for interrupted-run recovery or require a live draft-PR rehearsal: real GitHub merge-state responses and the production publish leaf were not exercised, so that external integration evidence still rests on host and leaf substitutes (target/template/tests/test_flow_resume_stack_prereqs.py:290; target/template/tests/test_flow_resume_stack_prereqs.py:294). |

The target snapshot was usable and the patch was restored after the independent red leg. A reverse-apply check against the complete supplied patch succeeded afterward. All source citations above refer to the supplied target tree, not another checkout. No confirmed implementation failure was found within the specified offline cases; the two human decisions above remain advisory and do not constitute an acceptance gate.

The mixed-edge decision is observable, not hypothetical. Using the shipped real-git fixture, a standalone W with `Stacks on: Q` built from `origin/fix/Q` and its substitute publisher recorded PR base `fix/Q`. With D declaring `Depends on: P` in the same target and first wave, W instead built from the shared integration line and recorded PR base `main` (reviewer-mixed-stacks.log:1). Production publish selects the same base at target/template/src/pdca_harness/publish.py:282. The added regression explicitly expects the latter behavior at target/template/tests/test_flow_resume_stack_prereqs.py:582, and the docs describe the exception at target/docs/07-crosscutting.md:688. This satisfies the original same-target line rule, but the carry-forward instruction at brief.md:164 does not explicitly authorize an exception for mixed runs. Resolve that scope tension at sign-off.

Independent verification used `TMPDIR` inside this review sandbox and `PYTHONDONTWRITEBYTECODE=1`. From `target/template`, `PYTHONPATH=src python3 -m unittest tests.test_flow_resume_stack_prereqs` produced eight failures with the production changes stashed and 14 passing tests after `git stash pop`; `PYTHONPATH=src python3 -m unittest discover -s tests` then passed 2,339 tests with two skips. The source import scanner also passed. From `target`, the docs linter and `render_site.py --check -o <sandbox>/reviewer-site` passed. The instance-scoped wrappers were not available here; their frozen logs were read. Local `python3 -m tests.run_root_suite` returned 77 because copier was not importable, while gate-logs/T3-suite.log:42 explicitly records executed update-compatibility cases and its 24-test success. This is a reviewer-host limitation, not a patch failure or a missing-evidence escalation.

Prior art was independently checked through GitHub by all four affected file paths, including merged.py and the new test path. The history queries returned the recent 15 commits per path (or the complete shorter result), and the new test had no history. All 263 closed PRs were enumerated; four were unmerged. Contrary to the brief's empty-result claim, PRs #598, #599 and #600 touch flow.py and the crosscutting docs. Their retrieved hunks concern auto-iteration and deferred findings, not the pre-wave stack carry; no matching rejected implementation was found in those hunks (reviewer-prior-art.log:1; reviewer-prior-art.log:39; reviewer-prior-art-diffs.log:105). The supplied INTEGRATION template leaves its project-specific human-only list as TODO (target/template/docs/INTEGRATION.md.jinja:80); it provides no additional concrete items to adjudicate.

For live fitness validation, use an authorized instance with stack mode and a command publisher: prepare P and D for the same target with D declaring `Depends on: P`; publish P's accepted draft while leaving it unmerged, then reissue `pdca flow P D`. Before D builds, inspect its recorded `stack-base` and `stack-base-tip`; after fetching origin, verify `git merge-base --is-ancestor origin/<P-published-branch> origin/<recorded-line>` exits zero. Inspect D's draft PR and recorded build/verification base for the same prerequisite ancestry. Exercise an unpublished or stale P and confirm D is held by name while an unrelated bundle proceeds. The reviewer exercised this behavior with real local git and substituted leaves; live publishing and human workflow suitability remain the sign-off decision. Mid-run adopted children's unique prerequisites remain explicitly outside this change at target/template/src/pdca_harness/flow.py:795.

### Advisory — adversary

# Adversarial review — issue 616 (stack-resume-carries-unmerged-prereqs)

Lens: refute the red→green evidence and find inputs that break the fix. I re-ran both legs and
tried five breaking inputs with scratch tests (sandbox only), each on the patched tree and on a
copy with the production hunks reverted.

- **Evidence holds.** Green: 14/14 on the patched tree. Red: 8/14 fail with
  `template/src/pdca_harness/{flow,merged}.py` reverted. The 6 that pass pre-fix are the
  "unchanged behaviour" cases, so that is expected. The tests drive the real
  `flow._drive_and_act` → `integrate.fold` → `_point_at_integration` → `worktree._target`
  against a real bare `origin`, so they are not a copy of production. One weak assertion:
  `template/tests/test_flow_resume_stack_prereqs.py:347-348` ("D's PR branch … carries P")
  checks the test's own `_publish_bundle` stub (`:254-265`), not `publish.publish`. Also,
  C5's "exercises production" only checks imports (gate-logs/C5-prod-path.log). My reading,
  not the gate, is what confirms the production path.

- NEEDS-HUMAN — **Regression: an empty `pr_url` on a merged prerequisite now stops the whole
  run.** `template/src/pdca_harness/flow.py:816` asks `merged.is_merged`, which returns False
  whenever `publish.json` has no `pr_url` (`merged.py:48-50`). So P is "carried". Its head
  branch was deleted on merge, so `integrate.py:462-467` raises, and `flow.py:2132-2133` sets
  `wave_list = []`. Verified case: P published with `pr_url: ""`, PR merged into main, branch
  deleted; D `Depends on: P`, U unrelated. Patched: D and U both PLANNED, nothing built. Pre-fix:
  both built on `origin/main`, which already has P, so pre-fix was correct. Ways to get an empty
  `pr_url`:
  - `gh pr create` failed and the human opened the PR by hand, as `publish.py:404-431` tells
    them to (the record keeps `pr_url: ""`).
  - The re-publish this patch tells the user to run for a stale record (`flow.py:2118`). The
    new-PR path runs `gh pr create` again, which fails when a PR already exists for that
    branch.

  With no `gh`, or a broken one, the same happens to any merged P whose branch was deleted
  (`merged.py:51-58`). The stop also takes down bundles of unrelated targets. Brief case (d)
  asks for this stop, but it assumed the host really does not know P merged; here the harness
  lost the URL itself. Human call: hold only that prerequisite's dependents (as the
  unpublished hold does), or check the base for P's work, instead of stopping everything.

- NEEDS-HUMAN — **A prerequisite whose PR was closed without merging is carried.**
  `flow.py:816` treats every state other than MERGED as "carry". Verified: P's PR CLOSED
  (rejected), `fix/P` still on origin. D and the unrelated U are both built on a line that
  carries P. Their PRs target main and include P's commits (`publish.py:266-277`), so merging
  U's PR would land P's rejected work. Pre-fix, both built on `origin/main`. The only stderr
  line is "carrying earlier runs' unmerged prerequisite(s) issue_P". The brief never covers
  CLOSED. A human should decide whether a closed PR holds its dependents.

- NEEDS-HUMAN — **The `Stacks on` claim is overstated.** `flow.py:767-769` and
  `docs/07-crosscutting.md:688-691` say a target that gets a line carries its `Stacks on`
  parent. That holds only for a line the pre-wave fold starts (`lined`, `flow.py:834-839`).
  Verified case: W has `Depends on: A` (in the batch) and `Stacks on: Q` (an earlier run's,
  published, PR open). In wave 1, W is pointed at the line folded after wave 0, which is
  main + A (`flow.py:742-746`). The stack base wins over `Stacks on` (`publish.py:738`,
  `worktree.py:96-98`), so W is built without Q. This also happens pre-fix, so it is not a
  regression. But it breaks the invariant the brief says to restore (`Stacks on` is a declared
  prerequisite, `waves.py:39-48`), and the new docs sentence is wrong for this case. Scope call:
  either carry such parents for any target that will get a line, or narrow the wording.

- NEEDS-HUMAN [impl] — **A line is started even when every dependent that needs it is held.**
  `lined` and `carried` (`flow.py:834-842`) never check whether the dependent is already held
  by another prerequisite. Verified: D `Depends on: P, P2`, where P can be carried and P2 has
  no published branch. D is held, yet the run force-pushes a fresh line carrying P, and the
  unrelated U is re-pointed at it (`do_base` = the line). So U's PR shows P's changes for no
  benefit. Fix: work out the holds first, then carry a prerequisite only for dependents that
  are not held.

- **Low: the stale check depends on file modification times** (`flow.py:850-865`). No harness
  code writes `SUMMARY.md` after a bundle is COMPLETE, so this is sound on the harness's own
  paths. A hand edit, or a `git pull` of recorded bundles (`[records]`,
  `template/pdca.toml.jinja:448-453`), can make `SUMMARY.md` newer than `publish.json` and hold
  a correct prerequisite. That fails safe, but the printed fix (re-publish) leads into the
  empty-`pr_url` problem above.

- **Tried and could not refute:**
  - Moving the in-run fold into `_fold_onto_line` (`flow.py:868-906`, `:2274-2281`) keeps the
    same stop and re-gate messages and the same break behaviour.
  - `carried + accepted` keeps a target's line through a wave that accepts nothing of it.
  - The fold after wave 0 continues the line without a force-push.
  - Holds are per pair across targets.
  - `Depends on (merged)` is unchanged.
  - A dry run makes no holds.
  - A missing `brief.md` on a COMPLETE prerequisite does not raise.

### Advisory — code-review

# Advisory code review — issue 616 (stack-resume-carries-unmerged-prereqs)

Lens: bugs the patch adds, plus reuse / simplification. Advisory only. All line numbers are from the patched tree at `$PDCA_TARGET`.

Overall: the main change is sound. The in-run fold was moved into `_fold_onto_line` (`template/src/pdca_harness/flow.py:868-906`), and I compared it line by line with the removed block. It behaves the same: tips are recorded before the re-gate, there is one lock scope, the re-gate runs only on a real fold, and `integ` is set only on a successful non-dry fold (a failed re-gate `break`s, as before). That move is a good reuse cleanup: both fold points now share one code path, so they can't drift apart. The `merged.is_merged` `OSError` guard (`template/src/pdca_harness/merged.py:575-583`) matches how `merged_head` handles it. Gates are green (C4 log: 8 of 14 new tests fail without the fix, all pass with it; T3 suite OK).

## Findings

- NEEDS-HUMAN — The "stale `publish.json`" check uses file times: a record counts as stale if its mtime is older than `SUMMARY.md`'s (`template/src/pdca_harness/flow.py:850-865`, called at `:813`). That can raise false alarms. Anything that rewrites or re-times `SUMMARY.md` after a good publish makes a correctly published prerequisite look stale, and its dependents get held. Examples: a human editing §6/§9 by hand after publishing, a second `pdca signoff` record (`template/src/pdca_harness/cli.py:1473`), or copying/archiving the bundle to `completed/` without keeping mtimes (#171). The check also runs *before* the merged-ness question (`flow.py:813` vs `:816`). So a prerequisite whose PR has already merged, but whose `SUMMARY.md` was touched later, holds its dependents even though "a merged prerequisite needs nothing" (brief, case (b)). This fails closed, so it is safe, but it can block real recovery runs. A human should decide whether a content-based signal is wanted instead, e.g. a sign-off/iteration stamp written into `publish.json` at publish, or comparing the recorded branch's diff with the current `patch.diff`. The sign-off carry-forward asked for "hold, don't silently carry", which this does. The open question is only how stale is detected.
- `_prereqs_to_carry` runs in a dry run too (stub publisher, `flow.py:2109-2110`). There, a plain out-of-batch `Depends on` now reaches `merged.is_merged` (`flow.py:816`), which shells out to `gh pr view` whenever a `pr_url` is on record. Before this patch, stub/dry runs made no `gh` call for a plain `Depends on`. It can't crash any more (the new `OSError` guard), but it can print "could not read PR state" noise or hit the network in an offline demo. Low impact. A simple fix: in a dry run, treat a published prerequisite as "carry" without asking the host.
- Held dependents are reported twice. The pre-wave hold line names them (`flow.py:2123-2124`), then `_runnable` prints its generic "skipped — prerequisite(s) not ready" line for the same bundle when its wave comes up (`flow.py:721-722`, via the `held_pairs` branch at `:718-719`). This is cosmetic and the information is correct, but the operator sees two messages for one hold. You could leave it as is: the in-batch `held_unpushed` path already double-reports the same way.
- Test gap (minor): the new file `template/tests/test_flow_resume_stack_prereqs.py` never runs the pre-wave fold with `regate_between_waves` on, or with a stub (dry) publisher. So the re-gate-red STOP and the dry path of the new pre-wave call (`flow.py:2129-2135`) are only covered indirectly, through the shared `_fold_onto_line` and the existing suites (T3 green). This isn't a correctness bug, so it is not flagged for a human.

No other correctness problems found. In particular:
- The per-(dependent, prerequisite) hold correctly leaves cross-target dependents alone.
- The `Stacks on` edge starts no line unless a `Depends on` already created one for that target.
- A failed pre-wave fold empties `wave_list` before any wave is pointed or driven.
- Each later fold includes `carried`, which keeps the target in `integ` through waves that accept nothing of that target.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T5 Judgment — Decide whether mixed-edge runs may change a legacy Stacks on PR base from its parent branch to main, or require Plan re-entry: the all-same-target line rule conflicts with the carry-forward preservation requirement in this case (brief.md:164; target/template/src/pdca_harness/flow.py:834; target/template/src/pdca_harness/publish.py:282; reviewer-mixed-stacks.log:2).
- [ ] Validation — fitness-to-purpose — Decide whether the offline result is sufficient for interrupted-run recovery or require a live draft-PR rehearsal: real GitHub merge-state responses and the production publish leaf were not exercised, so that external integration evidence still rests on host and leaf substitutes (target/template/tests/test_flow_resume_stack_prereqs.py:290; target/template/tests/test_flow_resume_stack_prereqs.py:294).
- [ ] **Regression: an empty `pr_url` on a merged prerequisite now stops the whole run.** `template/src/pdca_harness/flow.py:816` asks `merged.is_merged`, which returns False whenever `publish.json` has no `pr_url` (`merged.py:48-50`). So P is "carried". Its head branch was deleted on merge, so `integrate.py:462-467` raises, and `flow.py:2132-2133` sets `wave_list = []`. Verified case: P published with `pr_url: ""`, PR merged into main, branch deleted; D `Depends on: P`, U unrelated. Patched: D and U both PLANNED, nothing built. Pre-fix: both built on `origin/main`, which already has P, so pre-fix was correct. Ways to get an empty `pr_url`:
- [ ] **A prerequisite whose PR was closed without merging is carried.** `flow.py:816` treats every state other than MERGED as "carry". Verified: P's PR CLOSED (rejected), `fix/P` still on origin. D and the unrelated U are both built on a line that carries P. Their PRs target main and include P's commits (`publish.py:266-277`), so merging U's PR would land P's rejected work. Pre-fix, both built on `origin/main`. The only stderr line is "carrying earlier runs' unmerged prerequisite(s) issue_P". The brief never covers CLOSED. A human should decide whether a closed PR holds its dependents.
- [ ] **The `Stacks on` claim is overstated.** `flow.py:767-769` and `docs/07-crosscutting.md:688-691` say a target that gets a line carries its `Stacks on` parent. That holds only for a line the pre-wave fold starts (`lined`, `flow.py:834-839`). Verified case: W has `Depends on: A` (in the batch) and `Stacks on: Q` (an earlier run's, published, PR open). In wave 1, W is pointed at the line folded after wave 0, which is main + A (`flow.py:742-746`). The stack base wins over `Stacks on` (`publish.py:738`, `worktree.py:96-98`), so W is built without Q. This also happens pre-fix, so it is not a regression. But it breaks the invariant the brief says to restore (`Stacks on` is a declared prerequisite, `waves.py:39-48`), and the new docs sentence is wrong for this case. Scope call: either carry such parents for any target that will get a line, or narrow the wording.
- [ ] **A line is started even when every dependent that needs it is held.** `lined` and `carried` (`flow.py:834-842`) never check whether the dependent is already held by another prerequisite. Verified: D `Depends on: P, P2`, where P can be carried and P2 has no published branch. D is held, yet the run force-pushes a fresh line carrying P, and the unrelated U is re-pointed at it (`do_base` = the line). So U's PR shows P's changes for no benefit. Fix: work out the holds first, then carry a prerequisite only for dependents that are not held.
- [ ] The "stale `publish.json`" check uses file times: a record counts as stale if its mtime is older than `SUMMARY.md`'s (`template/src/pdca_harness/flow.py:850-865`, called at `:813`). That can raise false alarms. Anything that rewrites or re-times `SUMMARY.md` after a good publish makes a correctly published prerequisite look stale, and its dependents get held. Examples: a human editing §6/§9 by hand after publishing, a second `pdca signoff` record (`template/src/pdca_harness/cli.py:1473`), or copying/archiving the bundle to `completed/` without keeping mtimes (#171). The check also runs *before* the merged-ness question (`flow.py:813` vs `:816`). So a prerequisite whose PR has already merged, but whose `SUMMARY.md` was touched later, holds its dependents even though "a merged prerequisite needs nothing" (brief, case (b)). This fails closed, so it is safe, but it can block real recovery runs. A human should decide whether a content-based signal is wanted instead, e.g. a sign-off/iteration stamp written into `publish.json` at publish, or comparing the recorded branch's diff with the current `patch.diff`. The sign-off carry-forward asked for "hold, don't silently carry", which this does. The open question is only how stale is detected.
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
- Iteration delta (if iterating): The pre-wave carry of out-of-batch, published, unmerged prerequisites is sound; keep it and the attempt-1 fixes. Fix these before resubmitting: - A prerequisite whose PR is CLOSED (not merged) must hold its dependents, never be carried — otherwise unrelated same-target PRs carry rejected work. Add a test. - A missing `pr_url`, or a `gh` failure, must not stop the whole run: hold only that prerequisite's dependents (named on stderr), and let unrelated bundles build. Covers a merged P with an empty `pr_url` and a deleted branch, which built correctly pre-fix. Add a test. - Work out the holds first; start a line for a prerequisite only if some dependent that needs it is not held. Add a test (D depends on carryable P and unpublished P2 ⇒ no line, U stays on the plain base). - Ask whether P is merged BEFORE the stale-record (timestamp) check, so a merged prerequisite never holds its dependents. - Narrow the `Stacks on` sentence in `flow.py` and `docs/07-crosscutting.md`: it holds only for a line the pre-wave fold starts, not for a line first folded after a later wave.
- By / date: Eduard Ralph / 2026-10-04

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 4 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
