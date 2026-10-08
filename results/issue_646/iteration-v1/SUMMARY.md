# Result — issue 646 / stack-reissue-continues-batch-line

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: In stack mode the recovery for a run that stopped part-way (an integrity stop,
  the pass budget, a crash, Ctrl-C) is to re-issue the same `pdca flow <ids>`. That resumed
  run builds a dependent on a base missing its prerequisite, when the prerequisite finished
  in the earlier run:
  - the finished id is skipped as already terminal (`template/src/pdca_harness/flow.py:2320-2325`),
    so it is not in the drive set and never enters `accepted` or the fold
    (`flow.py:2031`, `:2067-2070`);
  - `_runnable` sees it as out-of-batch (`batch_names` is the drive set, `flow.py:706`) and
    accepts it as ready because it is COMPLETE (`flow.py:710`) — COMPLETE only means a draft
    PR was opened;
  - nothing has been folded yet, so `_point_at_integration` clears the dependent's stack base
    (`flow.py:736-742`) and it is cut from the plain target base.
  The dependent is built, C4-verified and published without its prerequisite. Nothing
  reports it. The earlier run's line is usually still on `origin` under the same name (#591:
  the batch key comes from the ids as asked for, skipped ones included, `flow.py:2357-2363`,
  `integrate.py:67-83`), holding the prerequisite — but the resumed run never uses it, and
  its first in-run fold force-replaces it (`integrate.py:344-345`, `:401`), which strands any
  accepted-but-unpublished bundle whose recorded line tip was on it
  (`publish._line_tip_refusal`, `publish.py:691-726`).
- Success criterion: With the patch, in stack mode with publishing on (non-stub publisher),
  real git against a bare `origin`, a run driven as `flow._drive_and_act(cfg, [D], …,
  batch=["P", "D"])` (the shape `flow_ids` produces when `P` is skipped as finished) where
  `P` is COMPLETE, has a non-empty `patch.diff`, a resolvable target, a `publish.json` naming
  a pushed branch and an OPEN PR, and `D` has `- **Depends on:** P`:
  (1) before `D`'s wave is driven, origin's line `integrate.integration_branch(cfg, "main",
  ["P", "D"])` contains `P`'s branch head, and `D`'s recorded stack base
  (`publish.read_stack_base`) names that line and its tip (`publish.read_stack_base_tip`)
  is the line's tip. Pre-fix `D`'s stack base is cleared and no such line holds `P` — RED.
  (2) **Continue, never replace:** when origin already has that line (the earlier run's,
  holding `P` and an accepted-but-unpublished `H` whose recorded `stack-base-tip` is a commit
  on it), the run continues it: the old tip stays an ancestor of the new tip, no force-push
  happens, and after the run `publish._line_tip_refusal` for `H` returns `""`.
  (3) **Append-only across waves:** with a second driven bundle `E` (`Depends on: D`), the
  fold after wave 0 continues the same line without force and without `IntegrationError`;
  it then holds `P` and `D`, and `E`'s stack base names it.
  (4) **Holds, per prerequisite, named on stderr, rest of the run goes on:** each case below
  leaves `P` out of the fold, holds exactly `P`'s dependents in the drive set (they stay
  PLANNED, are not built), prints one line naming `P`, the held dependents and the reason
  with advice that works under (2), and lets an unrelated bundle `U` build:
  (a) `P` has no branch on record; (c) `P`'s PR state is
  CLOSED (not merged); (d) `P`'s PR state cannot be read (no `pr_url`, a `gh` failure, or
  `gh` missing — an `OSError` — never a traceback).
  (5) **Nothing to carry:** `P` COMPLETE with an empty or missing `patch.diff` ⇒ nothing is
  folded, `D` is not held and builds on the base as today. `P`'s PR MERGED ⇒ `P` is handed to
  the fold like an open one; the fold already decides it (`integrate._gone_branch`,
  `integrate.py:442-490`: line has the merged head ⇒ skip; base has it ⇒ take base in;
  otherwise raise).
  (6) **Fail closed:** the pre-wave fold raising `IntegrationError` stops the run before
  wave 0: nothing is driven, stderr names the failure the way the in-run fold's
  "did not integrate; STOPPING" line does (`flow.py:2076-2079`), no traceback.
  (7) **Unchanged:** a run with no named-but-finished id that a drive-set bundle's plain
  `Depends on` names behaves exactly as today (no pre-wave fold, stale stack bases cleared);
  `Stacks on` and `Depends on (merged)` edges do not trigger the carry and keep their
  behaviour (#123, #186); a dry-run (stub publisher) asks no host, holds nothing, and only
  prints the plan; `--no-publish` and merge mode are untouched.
  (8) **Unrelated bundle on a carried line:** when the carry happens, an unrelated wave-0
  bundle `U` (no dependency on `P`) has its stack base pointed at the same line and tip as
  `D` (`publish.read_stack_base` / `read_stack_base_tip`), and its published PR still targets
  the real base `main` (#593) — the same outcome a later-wave `U` gets today. Pre-fix `U`'s
  stack base is cleared.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: Make a re-issued stack-mode `pdca flow <ids>` carry the named ids that are
  already finished (COMPLETE, patched, targeted) onto its batch's integration line before
  wave 0, CONTINUING origin's line when it exists (append-only, no force) and starting it
  fresh only when it does not; then point the run's bundles at it exactly as later waves
  already are. The carry happens only when some bundle in the drive set names such an id in
  its plain `Depends on`; when it happens, every carryable finished named id is carried (the
  line is the batch's line, as the in-run fold carries every accepted bundle), and every
  same-target runnable wave-0 bundle — including an unrelated `U` — is pointed at it
  (`_point_at_integration`, `flow.py:722-742`; its PR shows the carried changes until they
  merge, as any later-wave PR does). A dependent held for some other reason (a
  `Depends on (merged)` wait, another held prerequisite) does not cancel the carry: the line
  is the batch's own, not that dependent's. A finished named id that cannot be carried
  (criterion 4a, 4c, 4d) holds only its own dependents — the same `held_unpushed` path the in-run
  fold uses (`flow.py:2052-2058`, `:712-713`) — and the hold message's advice must be one that
  works now the line is kept (e.g. "publish it with `pdca publish <id>`, then re-issue the
  same command"; for a closed PR, "re-open it or re-drive <id>"; for an unreadable state,
  say what could not be read). A failing pre-wave fold stops the run before wave 0. Update
  the stack-mode paragraph in `docs/07-crosscutting.md:658-677`, the "resuming across runs
  is #616" wording in `publish.py:345`, `:696`, `:726`, and the "known cross-run limit (#616)"
  docstring in `drift.py:58-61` so they describe the kept line. Existing tests pin the old
  wording — `template/tests/test_integrate_stack_bases.py:834-852` (asserts `"#616"` and
  `"re-drive it in a new run"`) and `:1012` (asserts `"#616"`): update those assertions to the
  new advice text in the same patch (they are in Do's review surface, and C4 keeps
  `tests/*.py`, so they must pass post-fix).
  / out of scope: a prerequisite that is NOT one of the requested ids, including the
  `flow_batch` sweep path (child-2); `merged.is_merged`'s "merged where" rule (child-2);
  `Depends on (merged)` semantics (#186, unchanged); `Stacks on` (unchanged); merge mode
  (#531); split children adopted mid-run by an earlier run (name the gap in a docstring);
  rebuilding the line from scratch; a line on origin that an outside party rewrote (the
  continued fold merges onto whatever origin has — say so in the docstring); pruning old
  integration branches (#454).

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

Review the fix that makes a re-issued stack-mode flow carry finished requested prerequisites onto its existing batch integration line before building dependents, preserving earlier line commits.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The bounded recovery contract is falsifiable: dependents must receive their finished prerequisite before wave 0, while unrelated work proceeds through prerequisite-specific holds; target/docs/07-crosscutting.md:665 and target/template/tests/test_flow_resume_stack_prereqs.py:257. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only production/documentation changes leaves 12 behavioral and two wording assertions failing, including the missing prerequisite line; no import errors obscure the reproduction; review-red.log:189 and review-red.log:366. |
| C3 Change | PASS | The scoped recovery preserves requested-batch ancestry, keeps failed prerequisites from their dependents, and retains carried targets across later folds; target/template/src/pdca_harness/flow.py:719, :840, :2046, :2207. |
| C4 Verification (red→green) | PASS | Restoring the production changes makes all 63 focused tests pass after the same tests fail pre-fix; the real-git ancestry/publish assertions support the stated offline contract; review-green.log:158 and target/template/tests/test_flow_resume_stack_prereqs.py:266. |
| C5 Causal adequacy | PASS | Recovery repairs the missing pre-wave integration step and preserves the old line instead of merely suppressing dependent failures; the PR-read error handling is an execution-time failure boundary, not a capability probe masking a load-time cause; target/template/src/pdca_harness/flow.py:840 and target/template/src/pdca_harness/merged.py:112. |
| T1 Structure | PASS | Candidate eligibility and integration semantics remain shared with the existing fold, reducing divergence between carried and newly accepted work; target/template/src/pdca_harness/flow.py:807 and target/template/src/pdca_harness/integrate.py:158. |
| T2 Shape | PASS | Independent docs lint, 22-page site render/link audit, production-import scanner, and diff whitespace check pass; these reproduce the substantive documented CI checks; target/.github/workflows/docs-check.yml:31, gate-logs/T2-docs.log:11, gate-logs/host-ci-docs.log:11. |
| T3 Runtime | NEEDS-HUMAN | Decide whether mocked-host coverage suffices or require an authenticated PR-state check — real gh/GitHub was not exercised, so PR-state behavior rests on a response table despite 2,342 passing driver tests with two skips; target/template/tests/test_flow_resume_stack_prereqs.py:97 and review-suite.log:1931. |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the substantive contribution audit is deferred to the mandatory publish-time gate; gate-logs/T4-contribution.log:10. |
| T5 Judgment | NEEDS-HUMAN | Confirm prior art across every affected path in merged history and closed/rejected work — the supplied path-based check covers only part of this patch, and the disposable target has one synthetic commit and no remote, so redundancy and earlier rejection cannot be independently settled; brief.md:167 and target/template/src/pdca_harness/flow.py:754. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Accept the bounded recovery behavior and its operational tradeoff — unrelated same-target wave-0 bundles inherit carried changes, while unrequested prerequisites and earlier adopted split children remain outside this fix; target/template/tests/test_flow_resume_stack_prereqs.py:505 and target/template/src/pdca_harness/flow.py:788. |

No confirmed patch defect found. This review is advisory and does not authorize acceptance or publication.

Independent evidence:

- Ran `PYTHONPATH=src python3 -m unittest tests.test_flow_resume_stack_prereqs tests.test_integrate_stack_bases` from `target/template`, first with production changes stashed and then restored. Results: 63 tests, 14 failures pre-fix; 63 tests, all passing post-fix. The failures include actual missing ancestry, prerequisite holds, and continuation behavior, not merely changed message assertions. Captured output is in `review-red.log` and `review-green.log`.
- Ran `PYTHONPATH=src python3 -m unittest discover -s tests` from `target/template`: 2,342 tests, OK, two skips (`review-suite.log:1931`). Ran the repository docs lint/render tools and production-import scanner successfully. Temporary test files and rendered output were confined to this review workspace.
- Copier is not importable in this review interpreter, so I did not claim an independent root render/update-suite reproduction. The frozen gate log explicitly records those cases executing successfully: 24 tests, OK (`gate-logs/T3-suite.log:39`, `:54`). Its driver suite separately records 2,342 tests, OK, two skips (`gate-logs/T3-suite.log:1988`). This is a local toolchain limitation with readable successful gate evidence, not a patch failure or missing gate evidence.
- The target is readable and contains the required batch-scoping interfaces. `git apply --reverse --check ../patch.diff` succeeds after restoration, confirming the supplied patch is present; `git diff --check` passes. Source citations above refer to this target, not another checkout. No target-state caveat was needed.

For T3, the brief explicitly requests offline git evidence and declares no external dependencies (`brief.md:148`); that evidence is reproduced. The narrower outstanding dependency is the real host interface used by `merged.pr_state`. To discharge it, in the configured authenticated environment run `gh pr view <recorded-pr-url> --json state` against representative existing OPEN, CLOSED and MERGED PRs and compare the returned values with the handling at `target/template/src/pdca_harness/merged.py:120`. No host PR was created or modified during this review.

For T5, the investigation was performed: `git log --all --oneline -- <affected paths>` returns only synthetic base commit `84f01ee`; `git remote -v` returns nothing. The brief names historical commits and rejected attempts but supplies no independently inspectable history or closed-PR evidence. Confirm the seven patch paths, including docs, drift, publish and both test files, against merged and closed/rejected work before clearing this item.

The available integration document has no additional enumerated human-only items: `target/template/docs/INTEGRATION.md.jinja:80` is an unfilled template placeholder. The C5 smell-test found no added eager capability probe or fallback hiding a load-time side effect.

### Advisory — adversary

# Adversarial review — #646 (re-issued stack run continues its batch's line)

**The evidence holds.** `gate-logs/C4-verify.log` shows 12 of 17 new tests failing with the production change reverted (plus the 2 updated wording tests) and all passing with it. I re-ran the green leg at `$PDCA_TARGET`: 17 tests, OK. The tests drive the real `flow._drive_and_act`, the real `integrate.fold` against real git (a bare `origin`), and the real `publish.publish`. Only `_drive_wave` (build/sign-off) and `gh` are stubbed, so they test the production path and are not a copy of it. I found no tautology in the assertions.

**The fix has gaps.** I confirmed each one below by running a probe against the patched tree (the probe scripts are in this sandbox: `probe_adversary.py`, `probe_lock.py`).

- NEEDS-HUMAN — **A CLOSED PR still rides the continued line** (`template/src/pdca_harness/flow.py:782`, `:829-832`, `:840`). Criterion (2) (continue origin's line, never replace it) conflicts with (4c) (a closed PR must not ride the shared line). In the usual re-issue case, the earlier run already folded `P` onto the line, because `P` had a dependent in a later wave. Concrete case, run live: batch `[P, Q, D, E]`, the earlier run folded `P` and `Q`, then `P`'s PR was CLOSED. Re-issue with `D` (Depends on P) and `E` (Depends on Q). `P` is "held" and `Q` is carried, so the fold *continues* the old line, which already holds `P`. Result: `E` is built on a base that holds the closed `P`, and `E`'s published PR branch contains `P`'s commit (probe: both `True`). The stderr line also says `P` "is not carried onto the integration line", which is false here. `test_4c_a_closed_pr_holds_its_dependents` misses this because it starts with no line on `origin` (`assertIsNone(self._tip(self.line))`). A human has to pick the policy: refuse to continue a line that holds a closed PR (stop, or hold that whole target), or accept the leak and document it.

- NEEDS-HUMAN [impl] — **The carry fold reads its pushed tip after it has released the integration lock** (`template/src/pdca_harness/flow.py:840-843`). `_carry_finished` calls `integrate.fold(..., folded_this_run=None)` with no `locks`, so the per-group lock is released when `fold` returns, and only then does it call `integrate.pushed_tip(wt)`. Probe of the lock order for the carry: `lock+, lock-, pushed_tip`. The in-run fold does `lock+, pushed_tip, lock-`, because it passes `locks=locks` (`flow.py:2189-2199`). The worktree `repo.pdca-integ-<base>` is per base, not per batch (`integrate.py:187-192`), and #591 supports two runs with different batches on one base. So a concurrent fold can `checkout -B <its own line>` in that gap. `folded_tips` then records the other batch's commit, wave-0 bundles get it as their `stack-base-tip` (`flow.py:2100`), and the wave-0 fold stops with "another run moved it". Fix: wrap the carry fold and the tip read in a `contextlib.ExitStack()` passed as `locks`, the same way the in-run fold does.

- NEEDS-HUMAN [impl] — **The carried line is never re-gated** (`template/src/pdca_harness/flow.py:839-849` compared with `:2213-2221`). With `[driver].regate_between_waves = true`, the in-run fold re-gates the folded line before the next wave builds on it. The carry fold skips that step. Probe with `gates.run_integration` forced red: the only re-gate call came *after* `D` had been built and published on the carried line. The brief lists "an integrity stop" as a reason to re-issue. If the earlier run stopped because its re-gate found `P`+`Q` red together, the re-issued run carries the same red combination and builds wave 0 on it with no check. The brief asks to point bundles at the line "exactly as later waves already are", and later waves get a re-gated base. Fix: run the same re-gate after the carry fold when it is enabled, and return False on red.

- NEEDS-HUMAN — **The brief's invariant is only partly restored.** "Within a batch the integration line only ever grows" fails whenever no drive-set bundle plainly `Depends on` a finished id (`flow.py:803-804` returns early). Concrete case, run live: batch `[P, H, X, Y]`. The earlier run folded `P`, and `H` was accepted on that tip but not published. The re-issue drives `X` and `Y` (Y Depends on X), so nothing triggers a carry. The fold after wave 0 is `fresh` and does `push --force`, the old tip is gone from the line, and `publish._line_tip_refusal` for `H` refuses. Criterion (7) explicitly allows this, so the brief contradicts itself. A human should decide whether (7) or the invariant wins.

- NEEDS-HUMAN [impl] — **Two new texts overstate that guarantee** (`template/src/pdca_harness/publish.py:345`, `template/src/pdca_harness/drift.py:60-61`). The dry-run plan says "a re-issued run of the batch keeps it there", and the drift docstring says a re-issued run "continues it rather than replacing it". Both are unqualified, and the case above shows a re-issued run that replaces the line. `publish.py:728-731` and `docs/07-crosscutting.md:686` qualify the claim correctly ("a run that carried nothing"). Bring these two in line with them.

**What I tried and could not break:**
- `_runnable`'s `dep in plain_deps` check (`flow.py:719`) uses the same `brief._id_list` parsing as `waves.declared_deps`, so ids normalize the same way.
- Changing `integ =` to `integ.update` at `flow.py:2207` is safe: `fold` always returns every target of the cumulative accepted set.
- A finished id archived under `completed/` resolves through `find_bundle`.
- The dry-run, MERGED-PR, missing-`gh` (`OSError`) and empty-patch paths behave as the brief says.
- Nothing in `check-gates.json` overstates its gate log.

### Advisory — code-review

# Advisory code review — issue #646 (stack-reissue-continues-batch-line)

Lens: correctness bugs the patch adds, plus reuse/simplification. Advisory only; nothing here gates.

Gate evidence checked: in `gate-logs/C4-verify.log` the green leg is OK for both suites (17 + 46 tests). The red leg fails 12 of the new tests plus the 2 updated wording tests in `test_integrate_stack_bases.py`. The `FAILED (failures=2)` at the end of the log is the red leg, not a regression.

## Findings

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/flow.py:839-848` (`_carry_finished`): the carry fold skips the opt-in `[driver].regate_between_waves` check that the in-run fold runs on every folded tip before the next wave builds on it (`flow.py:2213-2221`). With re-gate on, wave 0 of a re-issued run builds on a line combination nobody re-gated: the earlier run's line plus the newly merged finished ids. That breaks the "validate each folded combination before the next wave builds on it" promise. The fix is to run `gates.run_integration` over each carried `wt` (holding the integ lock through it, as the in-run fold does with its `locks` stack) and stop before wave 0 when it is red. The fix is small, and no test covers it.

- NEEDS-HUMAN — `template/src/pdca_harness/flow.py:801-803` (the trigger) together with `integrate.py:344-345`: when a re-issued run has finished ids but no driven bundle plainly `Depends on` one, nothing is carried. The first in-run fold then runs in `"fresh"` mode and force-pushes over the earlier run's line. An accepted-but-unpublished bundle whose `stack-base-tip` was on that line is stranded (`publish._line_tip_refusal`). That matches brief criterion (7) ("behaves exactly as today"). It does not match the brief's stated invariant ("no run replaces commits an earlier run of the same batch recorded as a build base"). The patch is honest about it: the docs and messages now say "started fresh by a run that carried nothing" (`docs/07-crosscutting.md:685-687`, `publish.py:728-732`). A human should decide whether that gap is acceptable for this child, or whether a re-issued run (any finished id in `run_batch`) should always start its first fold in `"auto"` mode (continue if origin has the line).

- `template/src/pdca_harness/merged.py:98-127` (`pr_state`): this repeats the `gh pr view <pr_url> --json …` call, the `OSError` guard and the JSON parsing from `merged_head` (`merged.py:66-95`) and `is_merged`. A small shared helper that returns `(info_dict | None, why)` would let all three use one code path, so the missing-`gh` guard cannot drift between them. This is a cleanup, not a bug.

- `template/src/pdca_harness/flow.py:719-722` (`_runnable`): the widened held check `cfg.bundle(dep).name in held and (not out_of_batch or dep in plain_deps)` compares the raw `dep` string with raw `brief.depends_on` strings. Both come from the same brief parser (`waves.declared_deps` is `depends_on + …`, `waves.py:48`), so this is correct today. A comment saying that `held` can now hold out-of-batch names only through `_carry_finished` would make the rule easier to read. Minor; no action needed.

## Checked and found clean

- `integ.update(...)` replacing `integ = {...}` (`flow.py:2207`) does not change in-run behaviour. `fold` returns every target in the cumulative `accepted`, so the only difference is that a target only the carry folded keeps its line.
- The carried ids stay out of `accepted`, so `integrate.unpublished(accepted, pushed=pushed)` never reports them as unpushed in later waves. The fold after wave 0 runs in `"continue"` mode from the carry's recorded tip, without force. Test 3 pins this.
- `pushed_tip` raising `IntegrationError` falls inside the `try`, so the run stops before wave 0 with no traceback (`flow.py:839-847`).
- In a dry run (stub publisher) the carry calls no `gh`, holds nothing, leaves `integ` alone and records `None` tips, the same as the in-run dry fold.
- The tests match criteria (1)–(8) one-to-one. They drive the production `_drive_and_act` and `integrate.fold` against a real bare origin, and they spy on pushes to prove that no force-push happens.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T3 Runtime — Decide whether mocked-host coverage suffices or require an authenticated PR-state check — real gh/GitHub was not exercised, so PR-state behavior rests on a response table despite 2,342 passing driver tests with two skips; target/template/tests/test_flow_resume_stack_prereqs.py:97 and review-suite.log:1931.
- [ ] T5 Judgment — Confirm prior art across every affected path in merged history and closed/rejected work — the supplied path-based check covers only part of this patch, and the disposable target has one synthetic commit and no remote, so redundancy and earlier rejection cannot be independently settled; brief.md:167 and target/template/src/pdca_harness/flow.py:754.
- [ ] Validation — fitness-to-purpose — Accept the bounded recovery behavior and its operational tradeoff — unrelated same-target wave-0 bundles inherit carried changes, while unrequested prerequisites and earlier adopted split children remain outside this fix; target/template/tests/test_flow_resume_stack_prereqs.py:505 and target/template/src/pdca_harness/flow.py:788.
- [ ] **A CLOSED PR still rides the continued line** (`template/src/pdca_harness/flow.py:782`, `:829-832`, `:840`). Criterion (2) (continue origin's line, never replace it) conflicts with (4c) (a closed PR must not ride the shared line). In the usual re-issue case, the earlier run already folded `P` onto the line, because `P` had a dependent in a later wave. Concrete case, run live: batch `[P, Q, D, E]`, the earlier run folded `P` and `Q`, then `P`'s PR was CLOSED. Re-issue with `D` (Depends on P) and `E` (Depends on Q). `P` is "held" and `Q` is carried, so the fold *continues* the old line, which already holds `P`. Result: `E` is built on a base that holds the closed `P`, and `E`'s published PR branch contains `P`'s commit (probe: both `True`). The stderr line also says `P` "is not carried onto the integration line", which is false here. `test_4c_a_closed_pr_holds_its_dependents` misses this because it starts with no line on `origin` (`assertIsNone(self._tip(self.line))`). A human has to pick the policy: refuse to continue a line that holds a closed PR (stop, or hold that whole target), or accept the leak and document it.
- [ ] **The carry fold reads its pushed tip after it has released the integration lock** (`template/src/pdca_harness/flow.py:840-843`). `_carry_finished` calls `integrate.fold(..., folded_this_run=None)` with no `locks`, so the per-group lock is released when `fold` returns, and only then does it call `integrate.pushed_tip(wt)`. Probe of the lock order for the carry: `lock+, lock-, pushed_tip`. The in-run fold does `lock+, pushed_tip, lock-`, because it passes `locks=locks` (`flow.py:2189-2199`). The worktree `repo.pdca-integ-<base>` is per base, not per batch (`integrate.py:187-192`), and #591 supports two runs with different batches on one base. So a concurrent fold can `checkout -B <its own line>` in that gap. `folded_tips` then records the other batch's commit, wave-0 bundles get it as their `stack-base-tip` (`flow.py:2100`), and the wave-0 fold stops with "another run moved it". Fix: wrap the carry fold and the tip read in a `contextlib.ExitStack()` passed as `locks`, the same way the in-run fold does.
- [ ] **The carried line is never re-gated** (`template/src/pdca_harness/flow.py:839-849` compared with `:2213-2221`). With `[driver].regate_between_waves = true`, the in-run fold re-gates the folded line before the next wave builds on it. The carry fold skips that step. Probe with `gates.run_integration` forced red: the only re-gate call came *after* `D` had been built and published on the carried line. The brief lists "an integrity stop" as a reason to re-issue. If the earlier run stopped because its re-gate found `P`+`Q` red together, the re-issued run carries the same red combination and builds wave 0 on it with no check. The brief asks to point bundles at the line "exactly as later waves already are", and later waves get a re-gated base. Fix: run the same re-gate after the carry fold when it is enabled, and return False on red.
- [ ] **The brief's invariant is only partly restored.** "Within a batch the integration line only ever grows" fails whenever no drive-set bundle plainly `Depends on` a finished id (`flow.py:803-804` returns early). Concrete case, run live: batch `[P, H, X, Y]`. The earlier run folded `P`, and `H` was accepted on that tip but not published. The re-issue drives `X` and `Y` (Y Depends on X), so nothing triggers a carry. The fold after wave 0 is `fresh` and does `push --force`, the old tip is gone from the line, and `publish._line_tip_refusal` for `H` refuses. Criterion (7) explicitly allows this, so the brief contradicts itself. A human should decide whether (7) or the invariant wins.
- [ ] **Two new texts overstate that guarantee** (`template/src/pdca_harness/publish.py:345`, `template/src/pdca_harness/drift.py:60-61`). The dry-run plan says "a re-issued run of the batch keeps it there", and the drift docstring says a re-issued run "continues it rather than replacing it". Both are unqualified, and the case above shows a re-issued run that replaces the line. `publish.py:728-731` and `docs/07-crosscutting.md:686` qualify the claim correctly ("a run that carried nothing"). Bring these two in line with them.
- [ ] `template/src/pdca_harness/flow.py:839-848` (`_carry_finished`): the carry fold skips the opt-in `[driver].regate_between_waves` check that the in-run fold runs on every folded tip before the next wave builds on it (`flow.py:2213-2221`). With re-gate on, wave 0 of a re-issued run builds on a line combination nobody re-gated: the earlier run's line plus the newly merged finished ids. That breaks the "validate each folded combination before the next wave builds on it" promise. The fix is to run `gates.run_integration` over each carried `wt` (holding the integ lock through it, as the in-run fold does with its `locks` stack) and stop before wave 0 when it is red. The fix is small, and no test covers it.
- [ ] `template/src/pdca_harness/flow.py:801-803` (the trigger) together with `integrate.py:344-345`: when a re-issued run has finished ids but no driven bundle plainly `Depends on` one, nothing is carried. The first in-run fold then runs in `"fresh"` mode and force-pushes over the earlier run's line. An accepted-but-unpublished bundle whose `stack-base-tip` was on that line is stranded (`publish._line_tip_refusal`). That matches brief criterion (7) ("behaves exactly as today"). It does not match the brief's stated invariant ("no run replaces commits an earlier run of the same batch recorded as a build base"). The patch is honest about it: the docs and messages now say "started fresh by a run that carried nothing" (`docs/07-crosscutting.md:685-687`, `publish.py:728-732`). A human should decide whether that gap is acceptable for this child, or whether a re-issued run (any finished id in `run_batch`) should always start its first fold in `"auto"` mode (continue if origin has the line).
- [ ] **The declared target is not the code the brief was written against, and the success criterion can't run there.** The brief says `Repo + branch target: eduralph/pdca-harness @ main` (brief:87), but it says its own line numbers come from `origin/pdca-integration/main @ f594d8e` and that "#591's batch-scoped line name is REQUIRED by this fix and exists only there until PR #639 merges" (brief:4-7). The target checkout I was given (`$PDCA_TARGET`) is the `main` shape, and it lacks everything the criterion calls:
- [ ] **The rewording it plans breaks existing tests that the brief doesn't list.** The scope rewrites the "resuming across runs is #616" text at `publish.py:345`, `:696` and `:726` (brief:114-115). Existing tests check that text word for word:
- [ ] **The problem statement can't be checked against the tracker.** The bundle has no `notes.json` and no `sources/` directory; the cwd holds only `brief.md`. I can't confirm that the #616 thread frames the defect as "re-issued `pdca flow <ids>` builds a dependent without its finished prerequisite". I also can't check the claim that iterations v1-v3 were rejected for "fresh line + carry of any out-of-batch prerequisite" (brief:158-159), or whether a maintainer constraint came with that rejection. The human should confirm the thread before sign-off. The code side does support the hazard: the `_runnable` docstring says so at `flow.py:692-698`, and the out-of-batch COMPLETE acceptance is at `flow.py:706-711`.
- [ ] **Hidden second behaviour change: unrelated bundles get rebased onto the carried line.** The scope points "every same-target runnable wave-0 bundle — including an unrelated `U`" at the carried line, and accepts that "its PR shows the carried changes until they merge" (brief:103-106). That changes how bundles with no dependency on `P` are published. Today such a bundle's wave-0 stack base is cleared (`flow.py:736-742`). None of criteria (1)-(7) covers `U`'s PR diff, so it is unreviewed. Only (4) mentions `U`, and only to say it builds. Either justify it as part of the one fix or make it a criterion.
- [ ] **New PR-state hold policy is close to a second change.** Criteria (4b)-(4d) add new gating logic:

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
- Iteration delta (if iterating): Rejected at sign-off: the approach is right, but the review found real gaps in `_carry_finished`. Fix these in the rebuild: 1. Lock: hold the integration lock through the carry fold AND the `integrate.pushed_tip` read. Pass `locks=` (an ExitStack) to `integrate.fold`, the same way the in-run fold does (flow.py ~2189-2199). Today the lock is released before the tip is read, so a concurrent run on the same base can make us record its commit. 2. Re-gate: when `[driver].regate_between_waves` is on, re-gate the carried line (`gates.run_integration`, under the lock) before wave 0, and stop the run before any wave if it is red, the same way the in-run fold does (flow.py ~2213-2221). Add a test for it. 3. Closed PR already on the line: if origin's line already holds a finished id whose PR is CLOSED, do not continue that line silently and build on it. Fail closed: do not build that target's wave-0 bundles on it, and name it on stderr. Also fix the stderr text, which wrongly says the id "is not carried" when the line already has it. Add a test that starts with the line already on origin and already holding the closed P. 4. Overstated wording: `publish.py:345` (dry-run plan) and `drift.py:60-61` promise unconditionally that a re-issued run keeps the line. Qualify both the way `publish.py:728-731` and `docs/07-crosscutting.md:686` do ("a run that carried nothing" still starts fresh). Criterion (7) stays: the no-carry case is a documented limit, not something to fix here.
- By / date: Eduard Ralph / 2026-10-04

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 5 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
