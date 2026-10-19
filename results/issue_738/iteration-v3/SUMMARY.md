# Result — issue 738 / hold-a-bundle-whose-own-base-cannot-be-built

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: 
- Success criterion: Real-git tests through `flow._drive_and_act` on the `StackFoldGit` fixture (`template/tests/test_integrate_stack_bases.py:123`), loaded by path the way `template/tests/test_flow_same_wave_conflict.py:36-56` does. Every case asserts what is held (the holds map, or the bundle's state plus its stderr line) and the exit code. A test that passes on the red leg does not count. The cases:
  (1) **Moved base, last wave.** `A`, `Z` in wave 0; `B` (`Depends on: A`), `W` (`Depends on: Z`) in wave 1; after wave 0's fold, a different `a.txt` is pushed to `main`. `B` is held, and its line names `issue_A`, `<remote>/main` and the fix "rebuild issue_A's branch on the new <remote>/main". `W` is COMPLETE. No `STOPPING`.
  (2) **Rewritten in-batch prerequisite.** `A` is rewritten (force-pushed) after it lands on the line. Today this raises `integrate._Rewritten` inside `build_bundle_base` (`integrate.py:843`), which `_bundle_bases` re-raises (`flow.py:1019-1022`) into `STOPPING` (`flow.py:2765-2770`), so the red leg is the base path, not the fold. `B` (`Depends on: A`) is held; its line names `issue_A` as rewritten and keeps the restore/re-publish remedy `_rewrite_stop` already gives (asserted by the substrings `issue_A` and `rewritten`). An unrelated bundle in the same wave is COMPLETE.
  (3) **Failed fetch** of a member when building `B`'s base. Stub point: `integrate._prepare_worktree` as called from `build_bundle_base` (`integrate.py:835`), made to raise `IntegrationError` for `B` only. `B` is held; its line names the fetch as the cause and the fix "check the remote and re-run" (asserted by the substrings `fetch` and `re-run`; it must NOT say "rebuild"). The unrelated bundle completes.
  (4) **Refused push** of `B`'s per-bundle base branch. Stub point: the `_git(wt, *push)` call in `build_bundle_base` (`integrate.py:872`), made to return non-zero for `B`'s base branch only, so the real raise at `integrate.py:880` fires. `B` is held; its line keeps the cause text that raise already builds (`could not push <branch> to origin (…)`, with its origin-rules / force-push fix), asserted by the substrings `could not push` and the branch name. Same outcome for the unrelated bundle.
  The stubs replace a git call, never the `except` the fix adds, so the C4 revert still ends each case in `STOPPING`.
  (5) **Conflicts-with partner** (iteration-v1 §6 hole 1). Take case (3)'s shape and add `X` with `Conflicts with: B`, scheduled in a later wave. `X` is held, not built on the plain base. Fix direction: `_runnable` must see the base-held set in its partner check, the way `unpushed` is passed (`flow.py:2702-2714`).
  (6) **Stale line after a rewrite hold** (hole 4). Take case (2)'s shape and add `S` (`Stacks on: A`) in B's wave. `S`'s PR carries A's old head, so a stderr line must name `issue_S` as cut from the stale line. The rewritten member must keep being excluded from the end-of-run late-rewrite check, as today: `stop_named.add(exc.name)` at `flow.py:2768-2769`, read by the filter at `flow.py:2914` (iteration-v1 renamed this `base_rewrites`; the name is Do's choice, the behaviour is not).
  (7) **Dependent of a held bundle.** Add `C` (`Depends on: B`). `C` stays PLANNED and is reported as skipped. The exit code is 1 (human decision 3, same as #593/#674 holds today).
  In cases (1)-(4), where no dependent is left PLANNED, the run exits 3 (#693) and the held bundle is in the holds map under its own reason (not "unpushed"/"conflict").
  Pre-change, every case ends in `STOPPING` with the unrelated bundle PLANNED. Existing suites stay green: `test_integrate_bundle_base.py` (#723), `test_flow_dependency_scoped_bases.py` (#727), `test_flow_carried_prereq_bases.py` (#728), `test_flow_merged_prereq_dependency_base.py` (#729), `test_flow_same_wave_conflict.py`, `test_flow_conflict_partner_hold.py`, `test_flow_hold_exit_code.py`, `test_integrate_stack_bases.py`.
- Repo + branch target: eduralph/pdca-harness @ main (PRs target `main`). Do builds and the gate verifies on the run's line `pdca-integration/main-r547f8028520f` (tip `75a886e`, holding #723, #727, #728, #729), exported as `$PDCA_VERIFY_BASE`. `path:line` anchors are on `75a886e`.
- Scope (one logical fix) / out of scope: 

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: new-feature
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

Review whether a failure building one bundle's own base holds that bundle and affected successors while unrelated work continues, with accurate recovery guidance and exit codes (#738).

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The seven real-git scenarios distinguish isolated holds, skipped dependents, stale PRs, and exit 3 versus 1; the later line-fold failure is explicitly excluded (brief.md:3, brief.md:16; template/tests/test_flow_bundle_base_holds.py:340). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing the three production changes reproduced STOPPING: all 15 new cases and four updated assertions failed, with clean imports (review-red.log:72, review-red.log:315). |
| C3 Change | PASS | The six affected files stay within base-failure isolation, recovery messages, exit classification, and regression coverage; the hold is collected at the failing base operation (template/src/pdca_harness/flow.py:1040; template/src/pdca_harness/cli.py:742). |
| C4 Verification (red→green) | PASS | Restoring the production stash changed the same 55 tests from 19 assertion failures to all passing; this confirms the asserted regression evidence, while C5 records a separate uncovered defect (review-red.log:317; review-green.log:58). |
| C5 Causal adequacy | NEEDS-HUMAN [impl] | Fix the omitted stale-PR warning after successive rewrites — a real-git probe leaves S holding h1 absent from A without naming S, so recovery guidance misses an affected PR (template/src/pdca_harness/flow.py:1119, template/src/pdca_harness/flow.py:3056; review-probe.log:4). |
| T1 Structure | PASS | Failure isolation stays in the flow coordinator, git diagnosis stays in integrate, and the CLI retains the centralized exit rule; existing real-git fixtures provide coverage (template/src/pdca_harness/flow.py:2891; template/src/pdca_harness/integrate.py:860; template/src/pdca_harness/cli.py:742). |
| T2 Shape | PASS | Independently reran docs lint, site render with internal-link audit (22 pages), and git diff --check; all passed, consistent with both frozen shape logs (gate-logs/T2-docs.log:16; gate-logs/host-ci-docs.log:15). |
| T3 Runtime | PASS | Independent offline driver run passed 2,609 tests with two skips; frozen root evidence additionally shows 24 passing render/update tests (review-driver-suite.log:1817; gate-logs/T3-suite.log:54). |
| T4 Contribution | N/A | Contribution artifacts are drafted after Check; the substantive contribution audit must rerun at publish, as the deferred gate explicitly records (gate-logs/T4-contribution.log:10). |
| T5 Judgment | NEEDS-HUMAN | Confirm merged and closed/rejected prior art by each affected file path — the supplied target has one synthetic commit and no remote, so the brief's commit references cannot establish that search (review-prior-art.log:1; brief.md:22). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the hold/skip exit policy and recovery guidance fit batch operations, with later line-fold failures left to #739 — automated git scenarios support behavior but cannot grant operational acceptance (brief.md:11; template/tests/test_flow_bundle_base_holds.py:15). |

All production and test source citations above are grounded in the patched `$PDCA_TARGET` (`target/`), whose single base commit identifies the expected verification base `75a886e9370d7b51567c9f6803d827c66a4fac48`. No stale-target caveat applies. The original production changes were restored after the red leg; no source was patched by this review.

**Implementation finding: an additional rewrite can hide another affected PR.** At `template/src/pdca_harness/flow.py:1119` and `:1121`, the final check selects only heads already lost when the base was refused. The ordinary late-rewrite check then excludes that member at `:3056`. Re-reading its branch therefore cannot discover losses of heads that were still present at the refusal.

The independent probe uses the existing `DependencyScopedBases` real-git fixture and production `flow._drive_and_act`:

1. Wave 0 publishes A at h1 and Z. After its fold, A fast-forwards to h2.
2. Wave 1 publishes B (`Depends on: A`) on h2, S (`Stacks on: A`) on the earlier line holding h1, and W (`Depends on: Z`). The next fold takes h2.
3. After that fold, A is reset to h1. In wave 2, D (`Depends on: B`) is held because A lost h2. Its hold correctly names B; S still holds a valid h1 at that instant.
4. While unrelated V (`Depends on: W`) builds, A is force-pushed again to a branch containing neither h1 nor h2. At run end S is now stale, but no stderr line names it.

Observed: S contains h1, current A does not contain h1, and `S named in stderr: False` (`review-probe.log:4`, `:6`, `:8`). The run correctly exits 1 and names B; the defect is the missing S warning and corresponding recovery guidance. This window is the same long-running-wave window that motivated the previous iteration's restored-branch recheck.

Reproduce from this review directory:

```sh
TMPDIR="$PWD/review-tmp" PYTHONDONTWRITEBYTECODE=1 python3 review-probe.py
```

The assertion fails on the applied patch (`review-probe.log:17`). Recheck every head of the refused member held by a published PR at run end, including heads still present at the refusal, and add this sequence as a regression alongside the restored-branch case at `template/tests/test_flow_bundle_base_holds.py:484`.

**Evidence limits and gate accounting.** The C4 rerun kept all tests in place, stashed only `cli.py`, `flow.py`, and `integrate.py`, then popped that stash before the green run. Logs are `review-red.log` and `review-green.log`. The full driver run is `review-driver-suite.log`. Instance-scoped gate wrappers are outside the supplied artifact target; their absence is expected. The frozen production-path scanner log establishes only that the new driver test imports `pdca_harness` (`gate-logs/C5-prod-path.log:10`); the independent red→green run and probe additionally exercise production behavior. Copier is unavailable in this review interpreter, so root render/update tests were adjudicated from the frozen log, which shows their actual execution and success (`gate-logs/T3-suite.log:38`, `:54`). This is a local rerun limitation, not an unmet dependency in the recorded gate run. The brief declares no external dependency, and real git reproduced the forbidden STOPPING behavior without a tool alias or substitute topology. No added capability-probe/load-time symptom guard was found.

The prior-art investigation ran `git log HEAD -- <all six affected paths>`, `git remote -v`, and `git show-ref`; it found only the synthetic base and local master ref (`review-prior-art.log:1`). Neither merged history nor a closed/rejected-work archive was available. The supplied integration document is the uninstantiated template, whose human-only list remains TODO (`template/docs/INTEGRATION.md.jinja:80`); no additional instantiated project checklist was supplied.

<!-- pdca:leaf-complete -->

### Advisory — adversary

# Adversarial review — #738 (iteration 3)

The red→green proof holds, and I could not break the fix itself. One gap is real: a line the patch adds does work but no test pins it.

## Evidence, re-run

- I re-ran C4 myself. `template/tests/test_flow_bundle_base_holds.py`: 15/15 fail with the production files reverted (`git checkout -- template/src`, test file kept) and 15/15 pass with the patch. Every red-leg failure is the `assertNotIn("STOPPING", …)` at `test_flow_bundle_base_holds.py:303`, so each case goes red because the run stops, which is the defect. The eight suites the brief names, plus `test_integrate_carried_rewrite_late`, pass on the patched tree (161 tests).
- The tests run the production path. They call `flow._drive_and_act` and stub only git calls and the model leaves. The fetch failure runs the real `integrate._prepare_worktree` with only `git fetch` returning 1 (`test_flow_bundle_base_holds.py:223-233`), so the real `_FetchFailed` (`integrate.py:2111`) is what the wrapper at `integrate.py:862-874` sees. The push refusal fires the real raise at `integrate.py:921`. No stub replaces the `except` the fix adds (`flow.py:1041-1045`).
- Because every red leg fails at that first assertion, the red leg proves nothing about the later logic: the stale-PR check and the end-of-run re-read. I mutation-tested that logic instead. Five of seven mutations are caught. The two that survive are below.

## Findings

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/flow.py:3018` (`base_rewrites.clear()`) is not pinned by any test. Replacing it with `pass` leaves all 94 tests green across `test_flow_bundle_base_holds`, `test_flow_dependency_scoped_bases`, `test_integrate_carried_rewrite_late`, `test_flow_carried_prereq_bases`, `test_flow_merged_prereq_dependency_base` and `test_integrate_bundle_base`. The one test meant to cover it, `test_a_rewrite_mended_before_the_next_fold_fails_nothing` (`test_flow_bundle_base_holds.py:580-602`), ends the same with or without the line. The line matters, and here is the failing case (probe P1): `A`,`Z` / `B` dep `A`, `W` dep `Z` / `V` dep `W`.
  1. `fix/A` is force-pushed after fold 0, so `B` is held.
  2. `fix/A` is restored before fold 1, so fold 1 passes.
  3. `fix/A` is force-pushed again after fold 1, and wave 2 is the last wave.

  With the patch as written, the end-of-run check names A's rewrite: `holds={'B':'base','A':'rewritten'}`, exit **1**. With the line removed, A stays excluded from `_report_late_rewrites` (`flow.py:3056`), the second rewrite is reported nowhere, and the run exits **3**. Add P1 as a test.

  In the same function, `if not on: continue` (`flow.py:1122-1123`) is also unpinned. Probe P3: only `A` carried with a PR-less lost head, `B` held for its rewrite, every fetch failing at the end. Without the guard, the run adds `'A': 'unchecked'` and prints `flow: could not read issue_A's branch … these PRs may hold commits it no longer has: .` with an empty PR list. With it, neither appears. One assertion on `holds` in such a case would pin it. Both are test-only changes. The production code is correct.

## Notes (checked, not filed)

- Known limit, not new in this diff: a rewrite hold in a wave that is not the last still loses later waves. Probe P2 is case (2) plus `V` dep `W` in wave 2. `B` is held, `W` is COMPLETE, then the fold after wave 1 refuses `fix/A` (#633, `integrate.py:549`), prints `STOPPING`, and leaves `V` PLANNED. Brief case (2) is still met (the unrelated bundle in B's wave is COMPLETE). The test docstring says this plainly (`test_flow_bundle_base_holds.py:13-20`), and earlier rounds likely deferred it.
- An existing #695 assertion was flipped: `test_integrate_carried_rewrite_late.py` (1d) now expects exit 3, not 1. So "the line carries commits fix/A lost, no PR holds them" exits 3 when a base build saw the rewrite first, and 1 when only the end-of-run check sees it. The brief chose this ("cases (1)-(4) … exit 3"), and `cli.py:714-727` documents it. It is a deliberate choice, not a slip.
- Refutation attempts that failed:
  - A `KeyError` in `_report_stale_prs` on `dirs[m]` or `dirs[o]`: members come only from `built` = `accepted` (`flow.py:998`), and PR owners from `pushed` ⊆ `accepted` (`flow.py:1163`).
  - A dirty shared integration worktree after a base fails mid-merge: every base build and fold resets first (`integrate.py:891`, `:614`), and case (1) builds W's base right after B's clash.
  - A lock leak: `integ_lock` is a `with` block (`integrate.py:853`).
  - A `Conflicts with` partner in the held bundle's own wave: `compute_waves` never puts two partners in one wave.
  - `Stacks on` a held bundle: `declared_deps` includes it, so that bundle is skipped.
  - The `clear()` firing without fix/A being re-read on a multi-target run: `fold` checks every carried branch across all target groups before any merge (`integrate.py:549`).
  - Mismatched fix messages: each of the three raises in `_prepare_worktree`/`_fetch` now maps to its own fix (`integrate.py:863-871`).

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — issue #738 (hold a bundle whose own base cannot be built)

Lenses: bugs the patch introduces, and reuse / simplification. All anchors are on the patched target (`$PDCA_TARGET`).

I found no correctness bug in this diff. What I checked and found sound:

- The catch moved from the wave loop into `_bundle_bases` (`template/src/pdca_harness/flow.py:1040-1047`). A held bundle is never pointed, and the wave drops it before the build (`flow.py:2897-2900`). A wave left empty skips its fold the same way the existing empty-wave `continue` does.
- `held_base` is added to `_runnable`'s `held` set and to the `conflicts` trigger (`flow.py:2831-2843`). Dependents are skipped in every later wave, and `Conflicts with` partners are held (`flow.py:770-771`, `:863-871`). `waves.py:17-21` orients each conflict pair into separate waves, so a partner cannot share the held bundle's wave and slip past the check.
- The `_prepare_worktree` wrapper (`template/src/pdca_harness/integrate.py:859-873`) covers all three raise sites in that path: the missing checkout and the failed fetch (now `_NoCheckout` / `_FetchFailed`, both still `IntegrationError` subclasses, so existing `except` clauses still catch them), plus the worktree that cannot be made. `cause` is passed through, so `rewritten_carried`'s "unchecked" text is unchanged.
- `_report_stale_prs` (`flow.py:1092`) looks up names in `dirs = {accepted}`. Every name it looks up is accepted: owners come from `pushed`, which is a subset of `accepted`, and members come from `carried_heads`, which only the in-run fold of `accepted` fills (`_carry_finished` is not passed it). So no `KeyError`.
- `cli._results_rc` (`template/src/pdca_harness/cli.py:742-743`) excuses only bundles held as `"base"`. A dependent left PLANNED still gives exit 1, and `"rewritten"`/`"unchecked"` still win over 3.
- The existing tests that change (`test_flow_dependency_scoped_bases.py`, `test_integrate_carried_rewrite_late.py`) were moved from "STOPPING" to "held" and given exact `holds`/rc assertions. None of them was weakened. The new file asserts the holds map, the state and the rc in every case.

Small cleanups (optional, not blocking):

- `template/src/pdca_harness/integrate.py:1317` — `lost_now` repeats the per-branch read from `rewritten_carried` (`integrate.py:1240` onward): `_fold_candidates` → `_checkout_path` → `_fetch(attempts=2)` → `_rev` → `_carried_rewrite`. A small shared helper such as "read branch `ref` of `d` again and judge these heads" would keep the two end-of-run checks from drifting apart. Low priority, since both are short.
- `template/src/pdca_harness/flow.py:863-871` — the `unbuilt_partners` loop is a near copy of the #629 `partners` loop (`flow.py:848` onward) and the #674 `clashed` loop, with different wording. It is fine as written. If a fourth hold kind arrives, one table of (partner set → message) would be simpler than a fourth copy.
- `template/src/pdca_harness/flow.py:1131` — in the "unchecked" branch, `_report_stale_prs` lists every PR on a lost head, including ones the refusal already named (the `named` filter is applied only in the "rewritten" branch below it). This is harmless (one extra name on a line asking for a manual check) and arguably correct, since the branch could not be read again.

No NEEDS-HUMAN items from this lens.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] C5 Causal adequacy — Fix the omitted stale-PR warning after successive rewrites — a real-git probe leaves S holding h1 absent from A without naming S, so recovery guidance misses an affected PR (template/src/pdca_harness/flow.py:1119, template/src/pdca_harness/flow.py:3056; review-probe.log:4).
- [ ] T5 Judgment — Confirm merged and closed/rejected prior art by each affected file path — the supplied target has one synthetic commit and no remote, so the brief's commit references cannot establish that search (review-prior-art.log:1; brief.md:22).
- [ ] Validation — fitness-to-purpose — Decide whether the hold/skip exit policy and recovery guidance fit batch operations, with later line-fold failures left to #739 — automated git scenarios support behavior but cannot grant operational acceptance (brief.md:11; template/tests/test_flow_bundle_base_holds.py:15).
- [ ] `template/src/pdca_harness/flow.py:3018` (`base_rewrites.clear()`) is not pinned by any test. Replacing it with `pass` leaves all 94 tests green across `test_flow_bundle_base_holds`, `test_flow_dependency_scoped_bases`, `test_integrate_carried_rewrite_late`, `test_flow_carried_prereq_bases`, `test_flow_merged_prereq_dependency_base` and `test_integrate_bundle_base`. The one test meant to cover it, `test_a_rewrite_mended_before_the_next_fold_fails_nothing` (`test_flow_bundle_base_holds.py:580-602`), ends the same with or without the line. The line matters, and here is the failing case (probe P1): `A`,`Z` / `B` dep `A`, `W` dep `Z` / `V` dep `W`.
- [ ] **The grounding target is not the brief's base, so none of the code claims could be checked.** The brief says "`path:line` anchors are on `75a886e`" and cites `_bundle_bases` at `flow.py:1019-1022`, `STOPPING` at `flow.py:2765-2770`, `held_unpushed` at `:2584`/`:2851-2852`, `held_conflict` at `:2589`, `_announce_conflict_holds` at `:1435`. The `$PDCA_TARGET` I was given is checked out at `2ff8f3b` (`.git/worktrees/target/HEAD`). That commit has **no `_bundle_bases` anywhere under `template/`** (grep returns nothing). On it, `held_unpushed` is at `flow.py:2399`, set at `:2627-2628`; `held_conflict` is at `:2404`; `_announce_conflict_holds` is at `:1250`; `STOPPING` is at `:2614/:2649/:2666`. Only `_runnable` at `:681-690` and `_results_rc` at `cli.py:701` match. So the root-cause framing ("`_bundle_bases` re-raises") is unverified here. Either the driver resolved the wrong target, or the brief's base is not what the run will build on. A human should confirm that Do really gets `75a886e` as `$PDCA_VERIFY_BASE`.
- [ ] **There is no `Depends on` for the work this child is built on, but the PR targets `main`.** "Repo + branch target: eduralph/pdca-harness @ main (PRs target `main`)" and "External dependencies: none". Yet the defect only exists on the line "holding #723, #727, #728, #729". The regression suites the brief names, `test_integrate_bundle_base.py`, `test_flow_dependency_scoped_bases.py`, `test_flow_carried_prereq_bases.py` and `test_flow_merged_prereq_dependency_base.py`, do not exist at `2ff8f3b`. Only the other four (`test_flow_same_wave_conflict.py`, `test_flow_conflict_partner_hold.py`, `test_flow_hold_exit_code.py`, `test_integrate_stack_bases.py`) do. A PR against `main` that touches `_bundle_bases` cannot apply or pass until those four land. The brief should declare `Depends on`/`Stacks on` 723/727/728/729, or explain why it doesn't need to. Otherwise the bundle can be stranded at publish. No `dependency-state.json` was provided to check this against.
- [ ] **The tracker record is missing, so the problem statement can't be checked against the thread.** The sandbox has only `brief.md`. There is no `notes.json` and no `sources/`. The brief points to the human decisions at the #463 re-plan (2026-10-15) and the #725 re-plan (2026-10-17), "human decision 3", and `results/issue_725/iteration-v1/SUMMARY.md` §6/§9. None of these could be read. In particular I could not confirm that exit code 1 for case (7) versus 3 for cases (1)-(4) matches what the human actually decided.
- [ ] **Case (6) looks like a second change hidden inside this one.** The brief's goal is to "hold that bundle plus the bundles that declared `Depends on` or `Conflicts with` it, and nothing else". Case (6) does not hold `S` (`Stacks on: A`). It adds a new stale-line warning for `S` and changes the end-of-run rewrite check ("must not be dropped from the end-of-run check … near the old `d.name not in base_rewrites`"). That is a reporting/rewrite-detection fix (iteration-v1 hole 4), not a base-failure hold. Its anchor ("near the old …") also names no `path:line`, which goes against "Do must cite path:line on the base for every change". Consider splitting it out or giving it an exact anchor.
- [ ] **The success criterion is not fully pinned down for cases (2)-(6).** Only case (1) gives the exact stderr wording to assert. Cases (2)-(4) say "naming A and the restore/rebuild fix" or "same outcome", and the brief requires "a fix that works for that cause" for fetch and push failures without saying what that fix is. A reviewer can't tell whether a fetch-failure line that says "rebuild issue_A's branch" passes. Please specify the cause token and the fix wording expected for each case (fetch → retry/check the remote; push refused → check permissions/protection), the way case (1) does.
- [ ] **The red leg is uncertain for case (2), and the brief admits stubbing.** "With the production change reverted, every case prints `STOPPING`". For case (2), "A is rewritten (force-pushed) after it lands on the line", it is not shown that the current code raises in `_bundle_bases` rather than in the fold or the end-of-run rewrite check. The brief also leaves #633 rewrite detection out of the root-cause path. Cases (3)/(4) "may be stubbed for one bundle only", so how real they are depends on where the stub sits. The brief should say which call is stubbed (e.g. the fetch inside `integrate`'s base builder), so C4's revert check can't be met by a stub that throws past the new `except`.
- [ ] T5 Judgment — Confirm affected-path prior art in merged history and closed/rejected work for flow.py, integrate.py, and cli.py — the isolated target has one base commit and no remotes, and the brief's related commits/previous attempt do not establish both searches; `brief.md:22`.
- [ ] **A rewrite hold in any wave but the last still stops the run at the next fold.** Concrete case: `A`, `Z` in wave 0; `B` (`Depends on: A`), `W` (`Depends on: Z`), `U` (`Depends on: Z`) in wave 1; `V` (`Depends on: W`) and `U2` (`Depends on: U`) in wave 2; `fix/A` is force-pushed after wave 0's fold. Result: `B` is held, and its line (`template/src/pdca_harness/flow.py:1069-1071`) promises "the rest of the run goes on". Then the fold after wave 1 re-checks `A` (`template/src/pdca_harness/integrate.py:1139-1146`), refuses it, and prints `wave 1 did not integrate (…); STOPPING — later waves not run` (`flow.py:2972-2978`). `V` and `U2` stay PLANNED (rc 1), though neither has anything to do with `A` or `B`. The same rewrite is also named twice, with two different fixes ("then re-run" vs "re-issue the run; or let this run stop"). Brief case (2) only passes because `B`'s wave is the last one, and the last wave never folds (`flow.py:2935`). This is not a regression: before the patch the run stopped one step earlier. But the brief's invariant ("holds that bundle … and nothing else") only holds when the rewrite hold lands in the last wave. The out-of-scope clause covers "any clash at the line fold", and a rewrite is not a clash. A human should decide whether this belongs here (for example, the fold stops re-merging a member already in `base_rewrites`) or in a follow-up like #739. Either way, the hold line's unconditional "the rest of the run goes on" is wrong in this case.
- [ ] **The same rewrite exits 1 or 3 depending on whether some dependent's base happens to read it.** Probe P1: `A`, `Z`, `W` (`Depends on: Z`), with `fix/A` force-pushed after the fold. The end-of-run check says the line "still carries the old commits … no PR … holds them", holds = `{"A": "rewritten"}`, rc **1**. Probe P2: the same run plus `B` (`Depends on: A`). `B` is held, `A` is left out of the end-of-run check (`flow.py:3015`), and `in_prs` stays empty because only the line holds the old commits (`flow.py:2861-2865`). Holds = `{"B": "base"}`, rc **3**. In both runs the line carries exactly the same commits `fix/A` lost. The patch does what the brief asks (case (2): rc 3). But `_results_rc`'s own docstring (`template/src/pdca_harness/cli.py:709-714`) still says a rewrite where "the line carries commits no PR holds any more" is exit 1 (#695). The new comment at `flow.py:2773-2776` ("one only the run's line holds is a hold like any other") quietly overrides that rule. The edited test `template/tests/test_integrate_carried_rewrite_late.py:317` (1d, rc 1 → 3) locks the new rule in. A CI job reading rc 3 treats P2 as "held, not failed". A human should decide which rule wins and make the docstring and #695's rule agree.
- [ ] A rewrite hold is only a hold in the **last** wave. In any earlier wave, the next fold stops the run anyway. The hold message at `template/src/pdca_harness/flow.py:1069-1071` tells the operator "the rest of the run goes on". But the line fold after that wave gets every accepted bundle so far (`flow.py:2967-2970`), and that includes the rewritten prerequisite `A`. `integrate.fold` re-checks every carried branch (`template/src/pdca_harness/integrate.py:538`, `_carried_tips`), so it refuses `fix/A` and the run prints `wave k did not integrate … STOPPING`. The same goes for a moved base in a non-last wave: the next fold clashes with the new `main`. The brief puts that clash out of scope (#739). So in a run with more waves after the hold, the hold delays the stop by one wave rather than preventing it, and the stderr line promises more than the run delivers. All the new tests (`template/tests/test_flow_bundle_base_holds.py:239-362`) put the held bundle in the last wave, so none of them sees this. A human should decide one of three things: accept this as #739's territory, have Do soften the message when later waves remain, or extend the hold to the fold.
- [ ] T5 Judgment — Confirm path-scoped merged and closed/rejected prior art for all six affected files — this target has only a synthetic snapshot, no remote, and none of the three cited history commits, so duplicate or previously rejected work cannot be ruled out mechanically; review-prior-art.log:1, brief.md:22.
- [ ] **A rewrite hold in any wave but the last only delays the STOP by one fold.** The next fold re-reads `fix/A` (`template/src/pdca_harness/integrate.py:1143-1145`) and stops the whole run (`flow.py:2980-2986`). Failing case (probe P2): case (2)'s shape plus `V` (`Depends on: W`) in wave 2. `B` is held, then `flow: wave 1 did not integrate (issue_A's branch origin/fix/A was rewritten …); STOPPING`. `V` has no tie to `A` or `B` (it is built on its own base of `Z`+`W`), yet it stays PLANNED, and the run exits 1. The same rewrite is also named twice, with different advice: "then re-run" on B's hold line, "re-issue the run; or let this run stop" on the stop line. The brief's invariant says a base failure holds the bundle, its dependents and partners, "and nothing else". The brief's cases all sit in the last wave, so the gate never sees this. Someone has to decide whether this is accepted #633 fold behaviour (then say so and pin it with a test) or whether the fold should treat a rewrite a base already refused as a hold. Either way it is a scope call, not a builder iteration. (The moved-base case behaves the same way in a middle wave, probe P3: the next fold stops on `W`'s `a.txt`. The brief already puts that out of scope as #739, so I am not filing it.)

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
- Iteration delta (if iterating): Auto-iterate (round 3): rebuilding for the implementation-level findings — C5 Causal adequacy — Fix the omitted stale-PR warning after successive rewrites — a real-git probe leaves S holding h1 absent from A without naming S, so recovery guidance misses an affected PR (template/src/pdca_harness/flow.py:1119, template/src/pdca_harness/flow.py:3056; review-probe.log:4).; `template/src/pdca_harness/flow.py:3018` (`base_rewrites.clear()`) is not pinned by any test. Replacing it with `pass` leaves all 94 tests green across `test_flow_bundle_base_holds`, `test_flow_dependency_scoped_bases`, `test_integrate_carried_rewrite_late`, `test_flow_carried_prereq_bases`, `test_flow_merged_prereq_dependency_base` and `test_integrate_bundle_base`. The one test meant to cover it, `test_a_rewrite_mended_before_the_next_fold_fails_nothing` (`test_flow_bundle_base_holds.py:580-602`), ends the same with or without the line. The line matters, and here is the failing case (probe P1): `A`,`Z` / `B` dep `A`, `W` dep `Z` / `V` dep `W`.. Deferred, not addressed here: 7 finding(s) that need human judgment, held in deferred-findings.json for the human at handover — not build work
- By / date: auto-iterate / 2026-10-15

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 6 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
