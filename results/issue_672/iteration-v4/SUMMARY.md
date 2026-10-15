# Result — issue 672 / carry-keeps-a-fold-time-skip-off-the-line

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: The pre-wave carry (`flow._carry_finished`, `template/src/pdca_harness/flow.py:1032-1130`) spreads "not clean" along `Depends on` edges only for ids judged not clean **before** the fold (`_cascade_not_clean`, `flow.py:1002-1029`, called at `:1093`). An id can also fail **during** the fold: `integrate.fold` with `skipped=` records a merge failure for that one bundle and goes on to the next (`template/src/pdca_harness/integrate.py:532-539`). The carry learns of it only after the fold has merged and pushed (`flow.py:1104-1113`). So a finished `Q` merged later in the same fold, whose branch holds `P`'s commits, puts `P`'s work on the line even though `P` itself was skipped. The docs and docstring state this as a known residual (`docs/07-crosscutting.md:728-730`; `flow.py:1052-1054`).
  A textual conflict of `P` alone does not leak: `Q` contains `P`'s change, so it conflicts the same way and is skipped too (checked with git at Plan). It leaks when `Q`'s branch already resolved that conflict. The realistic shape, also checked with git at Plan: `P` and `Q` (branch cut from `fix/P`) are finished with open PRs; the base then gets a change that conflicts with `P`; `Q`'s author updates `fix/Q` from the base and resolves the conflict, `P`'s author does not. The carry's fold starts from the base, `P` conflicts and is skipped, `Q` merges cleanly, and `P`'s commit is on the line.
- Success criterion: Real-git tests on the carry fixture of `template/tests/test_flow_resume_stack_prereqs.py` (`_finished`, `_finished_on`, `_planned`, `_run`, `_held`, `_built`, `:61-172`, `:373-385`):
  (1) **A declared dependent is held.** `_finished("P", {"base.txt": "p\n"})`; `_finished_on("Q", "P")`; `_finished("X", {"x.txt": "x\n"})`. Then the base gets `base.txt` = `r\n` (`self.fx._push_from_human({"base.txt": "r\n"}, to="main")`), and `fix/Q` is updated from the base with the conflict resolved in `Q`'s favour (in the fixture's `human` clone: check out `origin/fix/Q`, `git merge -X ours --no-edit origin/main`, push to `fix/Q`). Planned: `D` (`Depends on: Q`), `E` (`Depends on: X`). Run `_run([D, E], ["P", "Q", "X", "D", "E"])`. Then: `D` is never built and stays PLANNED; one stderr line names `issue_Q`, `issue_D` and `issue_P` as the cause (`_held("Q", "D", "issue_P")`); `P` is held with its own line (no dependent of it is planned, so the line says it holds no bundle, as today); `X` is carried, the line exists, `E` is built on it and is COMPLETE; and no commit `P`'s branch adds over the base is an ancestor of the line's tip or of `E`'s recorded tip (`_ancestor(_tip("fix/P"), …)` is false), nor is `fix/Q`'s tip. The run makes exactly one `git push` (the carry's), counted with the fixture's spy `self.fx._pushes(lambda: self._run(...))` (`test_integrate_stack_bases.py:223-235`, used at `test_flow_resume_stack_prereqs.py:199,212`): `len(pushes) == 1`. A fix that pushes, then finds the leak and re-folds or force-pushes, fails this.
  (2) **Containment, not only the declared edge.** Same as (1), but `Q`'s brief has no `Depends on: P` (its branch is still cut from `fix/P`, so it holds `P`'s commit). The outcome is the same: `Q` is not carried, `D` is held naming `issue_Q` and `issue_P`, and the line holds none of `P`'s or `Q`'s commits; again exactly one push.
  (3) **Nothing else changes.** The existing carry tests in that file stay green, including `test_of_two_conflicting_prerequisites_the_one_asked_for_first_is_carried` (`:246-258`) and `test_a_fold_given_skipped_passes_over_only_the_bundle_that_fails` (`:347`), and so do `template/tests/test_integrate_stack_bases.py` and `template/tests/test_flow_same_wave_conflict.py`.
  Pre-fix, (1) and (2) fail: `D` is built, on a line that holds `fix/P`'s commit. That is the RED.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: Keep every finished id whose branch holds a fold-time-skipped id's work off the line in the carry, hold it (and through it its plain `Depends on` dependents) with the skipped id named as the cause, and keep the line append-only: the carry's one push per target must not be followed by a rewrite of what it pushed (no extra force-push). Whether that is done inside `integrate.fold`'s `skipped` mode or by the carry before the push is Do's choice; say why in `build-notes.md`. Update the `_carry_finished` docstring (`flow.py:1052-1054`) and `docs/07-crosscutting.md:728-730`, which describe today's residual, and the fold's `skipped` docstring (`integrate.py`, the `skipped` paragraph of `fold`'s docstring) if its behaviour changes. Fold order: the carry folds ids in the requested order, as today. When the containing branch `Q` is folded BEFORE `P`, `P`'s own merge is a no-op (already in the line, `integrate.py:622-623`), so `P` is never skipped and both are carried; that is correct (no merge failed) and not changed. The criteria pin the P-before-Q order, where `P` is skipped and `Q` must not carry it. / out of scope: the pre-fold cascade `_cascade_not_clean` (`flow.py:1002-1029`) stays declared-edge-only, with its hint text unchanged; do not switch it to ancestry "for consistency" (a finished id judged not clean before the fold and held only through an undeclared branch cut is a separate gap). A red re-gate of the carried line (`flow.py:947-950`, `:1114-1116`): the line was already pushed and the wave-0 fold replaces it, as `test_a_red_regate_of_the_carried_line_holds_and_the_run_goes_on` pins; unchanged. The in-run folds (they pass `skipped=None`, so any failure there stops the run or is a #674 hold, whose dependents are not yet built); which of two conflicting finished ids is carried (still the one asked for first); work of a skipped id that is already on the base (a merged PR's head the base holds is not "not clean" work); the end-of-run or re-issue wording for #674 holds (694); exit codes (693).

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: pass — C4 PASS — red without the fix, green with it
- C5 added test exercises production, not a copy: pass — patch adds no new test file — nothing to assert

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

Review issue 672: prevent a finished bundle skipped during the pre-wave carry from reaching the integration line through another finished branch, before the carry's sole push.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The requested invariant, declared/undeclared containment cases, push count, and exclusions are falsifiable; the base-relative invariant remains the review standard (`brief.md:10`, `brief.md:16`, `brief.md:22`). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only the production changes leaves the new tests executable and produces 14 assertion failures in 36 tests, including both specified leak cases (`review-red.log:227`; `target/template/tests/test_flow_resume_stack_prereqs.py:532`). |
| C3 Change | PASS | The four changed files address carry admission, fold behavior, its documentation, and regression coverage; ordinary folds retain their first-failure behavior (`target/template/src/pdca_harness/integrate.py:586`, `target/template/src/pdca_harness/flow.py:1121`). |
| C4 Verification (red→green) | PASS | Restoring the production patch passes all 36 carry tests, independently matching the frozen red→green evidence; this verifies the shipped tests, not the uncovered case below (`review-green.log:3`, `gate-logs/C4-verify.log:10`). |
| C5 Causal adequacy | NEEDS-HUMAN [impl] | Preserve a skipped bundle's own earlier work when its recorded build line contains that work, and add a regression — subtracting that entire line lets skipped P's original commit reach a fresh line through Q and lets D build (`target/template/src/pdca_harness/integrate.py:983`, `review-recorded-base.log:12`, `review-recorded-base.log:17`). |
| T1 Structure | PASS | Containment decisions and local retries occur under the existing integration lock before the push; each retry permanently excludes another previously merged bundle, bounding termination (`target/template/src/pdca_harness/integrate.py:500`, `target/template/src/pdca_harness/integrate.py:616`, `target/template/src/pdca_harness/integrate.py:660`). |
| T2 Shape | PASS | Independently rerun docs lint, 22-page render/link audit, and diff whitespace check pass; the frozen host-CI parity log corroborates the same docs checks (`review-docs-lint.log:1`, `review-docs-render.log:3`, `gate-logs/host-ci-docs.log:10`). |
| T3 Runtime | PASS | The independent offline suite passes 2,477 tests with two skips; root render/update coverage is supported by the frozen 24-test pass, since this interpreter lacks Copier (`review-suite.log:1817`, `gate-logs/T3-suite.log:54`, `review-root-suite.log:6`). |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the substantive audit is deferred to its required publish-time rerun (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Accept or revise the conservative holds for shared history, including whole-target holds on an existing line, and confirm path-based merged/closed-work prior art — these affect recovery and duplicate-work risk; the disposable target contains only a synthetic base commit and no remote (`target/docs/07-crosscutting.md:750`, `review-prior-art.log:1`, `brief.md:27`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the eventual corrected behavior and its recovery costs satisfy resumed-stack users — the shipped examples pass, but the independently reproduced earlier-work leak prevents treating the stated invariant as established (`target/docs/07-crosscutting.md:729`, `review-recorded-base.log:12`, `review-recorded-base.log:17`). |

The C5 finding is an observed leak of P's own work, not merely an attribution disagreement about another prerequisite's commits. The reproduction uses the existing real-git fixture and its recorded-line publication helper (`target/template/tests/test_flow_resume_stack_prereqs.py:725`):

1. Publish P's original commit `p1` and fold P onto an earlier integration line L.
2. Rebuild P on L with a later change to `base.txt`; publish Q on L with an unrelated file. Both record L as their build base.
3. Change `base.txt` differently on main, then delete the earlier integration line so the carry starts fresh.
4. Request P, Q, and D, where D depends on Q. P conflicts and is skipped. Q merges with `p1`, D builds, and the carry pushes once. `p1` is absent from main but present on the resulting line.

`_work` removes every ancestor of the recorded cut, explicitly including the same bundle's earlier head (`target/template/src/pdca_harness/integrate.py:978`). Consequently `p1` never enters the excluded-work set. This contradicts `brief.md:16`, which excludes every commit of the skipped branch over the base; the new documentation narrows that invariant at `target/docs/07-crosscutting.md:731`. Retain the bundle's own earlier contribution in that set, or obtain an explicit Plan-level revision of the invariant; documenting the exemption alone does not satisfy the current brief.

Run the independent failing probe from this review directory:

```bash
TMPDIR="$PWD/review-tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/target/template/src" python3 review-recorded-base.py
```

It exits 1 on the fresh-line assertion. Its continued-line control carries P successfully and is not a defect; the finding is the fresh-line case beginning at `review-recorded-base.log:10`.

The production-path scanner was rerun, but it only checks newly added test files; this patch extends an existing file, so its success is vacuous (`gate-logs/C5-prod-path.log:10`). Direct inspection and execution establish that the tests invoke real `flow._drive_and_act` and `integrate.fold`, with real git repositories and merges (`target/template/tests/test_flow_resume_stack_prereqs.py:123`). The host PR responses and build leaves are stubbed; the forbidden git topology itself is exercised and demonstrably fails before the fix. No missing git/Python dependency or capability-probe symptom guard was found.

The local root-suite limitation is a host caveat, not a patch failure: its runner correctly exits 77 for unavailable Copier library coverage. The frozen log actually executes the render/update cases successfully. Prior-art evidence is less complete: the brief names merged and closed-unmerged work by production/docs paths, but no independently inspectable history or closed-PR evidence is supplied, and its entry does not cover the changed test file. The T5 decision therefore remains open. The supplied integration template's human-only list is unfilled (`target/template/docs/INTEGRATION.md.jinja:80`), so it supplies no additional enumerated decision.

The target was restored after the stash/pop experiment, and its final binary diff matches `patch.diff` byte for byte. No production or test source was edited. All independent evidence and the probe reside in the harness review directory.

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — issue 672 (carry keeps a fold-time skip off the line)

Lens: bugs the patch introduces, plus reuse / simplification / efficiency. Grounded on the
patched target at `$PDCA_TARGET`. Gates: C4 is red before the fix and green after
(14 of 36 fail pre-fix, `gate-logs/C4-verify.log`). The T3 suite passes, 2477 tests
(`gate-logs/T3-suite.log`). I found no leak of skipped work onto the line. The findings
below are about wrong holds, misleading messages, and some dead or duplicated code.

- NEEDS-HUMAN [impl] — **A restart can hold both bundles, each naming the other as the
  cause, and the real conflict is never reported.** `template/src/pdca_harness/integrate.py:557`
  builds `excl` for the next pass from every `out` bundle's full work. `:570` then checks
  each bundle against it, including the bundle whose skip caused the restart. If Q was cut
  by hand from P's first commit `p1`, `out[Q]`'s work (`:618`, `_work` at `:971`) includes
  `p1`. So on pass 2, P is held for "holding a commit of Q's branch", and that commit is
  P's own `p1`. I reproduced this with a real-git probe on the carry fixture
  (`probe/test_probe_circular.py` in this sandbox): P adds `p-first.txt`; Q is
  `_finished_on("Q", "P")`; P then adds `q.txt` (which conflicts with Q's file, not with
  the base); order `Q, P`. Result: no push, D and E both PLANNED, and stderr says
  "issue_Q's branch … holds 63aebcc…, a commit of issue_P's branch … get issue_P carried"
  and "issue_P's branch … holds 63aebcc…, a commit of issue_Q's branch … get issue_Q
  carried". The advice loops, and neither line says the two conflict. P would merge alone
  on pass 2. Nothing leaks (the invariant holds), and `docs/07-crosscutting.md:750-753`
  does call "cut by hand, both held" a known limit. Still, this case is P failing *because
  of* Q, which is the case the restart exists to fix
  (`test_one_holding_a_later_ones_commit_is_held_when_they_conflict` covers only the
  stack-base form). Suggested fix: when judging bundle `d` on a later pass, leave out every
  `out` entry whose recorded cause is `d` (`out[n][0] == d.name`). Then P merges, and Q
  gets the existing "without {n} it is [carried]" message (`:645-649`). Add the probe as a
  regression test.

- NEEDS-HUMAN [impl] — **When a branch holds skipped work and also conflicts, the conflict
  message wins, and the "holds" cause and hint are lost.** `integrate.py:570-589`: `hit` is
  known before the merge, but the merge runs anyway. If the merge fails, the bundle goes
  into `left` with the conflict text, and `held` is never set. So `flow.py:1133-1134` gives
  it the `open` hint ("get issue_Q's PR open … re-open it"), which is wrong because its PR
  is open, and `causes` does not name the skipped id. The brief (`brief.md:9`) calls this
  the usual shape when P conflicts ("Q contains P's change, so it conflicts the same
  way"). It is simpler and cheaper to skip the merge when `hit` is set: record
  `_holds_why(...)` and `held[d.name]` directly, which also removes the merge-then-reset at
  `:571-574` and `:599`. No test covers a holder that also conflicts.

- **Dead code: the `held_out` re-judging on restart can never run.** `integrate.py:619-621`
  only runs when `skipped is not None` (restarts break out at `:607-608` otherwise).
  `held_out` is only passed by the in-run folds (`flow.py:2555-2560`), and those always
  pass `skipped=None`. The carry (`flow.py:1121-1123`) passes `skipped` and no `held_out`.
  Either delete the block and the `aside` list (`:554`, `:584`), or add an assertion that
  the two modes never combine.

- **Duplicate host call for a gone branch.** `integrate.py:990-998` (`_gone_work`) calls
  `merged.merged_head` again for a bundle whose `_merge_published` → `_gone_branch`
  (`integrate.py:767`) just asked the host the same question, which costs one more `gh pr
  view` round trip per gone, skipped bundle. Small cost, since it happens only on the
  gone-branch path. You could have `_gone_branch` return or record the head it read.

- **Minor efficiency: `_holding` scans in nested loops.** `integrate.py:1001-1012`:
  `next(... for name, work in excl.items() for c in work if c in adds[tip])` is called for
  every bundle, every pass, and once more for each `took` entry (`:609-610`) and each `out`
  entry (`:640`). The membership test uses a set, so each call is linear in the total
  excluded work, which is fine for realistic batch sizes. I note it only; no change needed.

Nothing else found. The restart terminates (each pass adds at least one name from `took`
to `out`). The skipped and `skip_causes` dicts are filled only after the
`SkippedWorkOnLine` and gone-branch raises, so the carry's `except` branch
(`flow.py:1124-1130`) never sees a half-filled `within`. The in-run folds (`skipped=None`)
keep their old single-pass behaviour.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] C5 Causal adequacy — Preserve a skipped bundle's own earlier work when its recorded build line contains that work, and add a regression — subtracting that entire line lets skipped P's original commit reach a fresh line through Q and lets D build (`target/template/src/pdca_harness/integrate.py:983`, `review-recorded-base.log:12`, `review-recorded-base.log:17`).
- [ ] T5 Judgment — Accept or revise the conservative holds for shared history, including whole-target holds on an existing line, and confirm path-based merged/closed-work prior art — these affect recovery and duplicate-work risk; the disposable target contains only a synthetic base commit and no remote (`target/docs/07-crosscutting.md:750`, `review-prior-art.log:1`, `brief.md:27`).
- [ ] Validation — fitness-to-purpose — Decide whether the eventual corrected behavior and its recovery costs satisfy resumed-stack users — the shipped examples pass, but the independently reproduced earlier-work leak prevents treating the stated invariant as established (`target/docs/07-crosscutting.md:729`, `review-recorded-base.log:12`, `review-recorded-base.log:17`).
- [ ] **A restart can hold both bundles, each naming the other as the cause, and the real conflict is never reported.** `template/src/pdca_harness/integrate.py:557` builds `excl` for the next pass from every `out` bundle's full work. `:570` then checks each bundle against it, including the bundle whose skip caused the restart. If Q was cut by hand from P's first commit `p1`, `out[Q]`'s work (`:618`, `_work` at `:971`) includes `p1`. So on pass 2, P is held for "holding a commit of Q's branch", and that commit is P's own `p1`. I reproduced this with a real-git probe on the carry fixture (`probe/test_probe_circular.py` in this sandbox): P adds `p-first.txt`; Q is `_finished_on("Q", "P")`; P then adds `q.txt` (which conflicts with Q's file, not with the base); order `Q, P`. Result: no push, D and E both PLANNED, and stderr says "issue_Q's branch … holds 63aebcc…, a commit of issue_P's branch … get issue_P carried" and "issue_P's branch … holds 63aebcc…, a commit of issue_Q's branch … get issue_Q carried". The advice loops, and neither line says the two conflict. P would merge alone on pass 2. Nothing leaks (the invariant holds), and `docs/07-crosscutting.md:750-753` does call "cut by hand, both held" a known limit. Still, this case is P failing *because of* Q, which is the case the restart exists to fix (`test_one_holding_a_later_ones_commit_is_held_when_they_conflict` covers only the stack-base form). Suggested fix: when judging bundle `d` on a later pass, leave out every `out` entry whose recorded cause is `d` (`out[n][0] == d.name`). Then P merges, and Q gets the existing "without {n} it is [carried]" message (`:645-649`). Add the probe as a regression test.
- [ ] **When a branch holds skipped work and also conflicts, the conflict message wins, and the "holds" cause and hint are lost.** `integrate.py:570-589`: `hit` is known before the merge, but the merge runs anyway. If the merge fails, the bundle goes into `left` with the conflict text, and `held` is never set. So `flow.py:1133-1134` gives it the `open` hint ("get issue_Q's PR open … re-open it"), which is wrong because its PR is open, and `causes` does not name the skipped id. The brief (`brief.md:9`) calls this the usual shape when P conflicts ("Q contains P's change, so it conflicts the same way"). It is simpler and cheaper to skip the merge when `hit` is set: record `_holds_why(...)` and `held[d.name]` directly, which also removes the merge-then-reset at `:571-574` and `:599`. No test covers a holder that also conflicts.
- [ ] **The "Invariant to restore" is false today in cases this slice leaves out of scope, so a reviewer cannot hold Do to it as written.** The brief says: "Precisely: after the carry, no commit a not-carried finished id's branch adds over the base is reachable from the line's tip." That fails in at least two cases this fix does not touch: (a) **Red re-gate.** `_fold_lines` pushes the line before the re-gate (`integrate.fold` pushes at `integrate.py:552-553`; the re-gate runs at `flow.py:947-950`). On red, the carry only adds the carried ids to `why` (`flow.py:1114-1116`). Origin's line still holds their commits, as `test_a_red_regate_of_the_carried_line_holds_and_the_run_goes_on` (`tests/test_flow_resume_stack_prereqs.py:326-343`) shows: it relies on the wave-0 fold replacing the line. (b) **A finished id judged not clean before the fold with no declared edge.** For example, P is CLOSED and Q is cut from `fix/P` without `Depends on: P`. `_cascade_not_clean` follows only declared `Depends on` edges (`flow.py:1011-1017`), so Q is still carried with P's commit. Fix: narrow the invariant to fold-time skips (or to "the line the carry hands to wave 0"), or name (a) and (b) as out of scope.
- [ ] **Criterion (2) invites a hidden second change to the pre-fold cascade.** Criterion (2) requires detecting containment by ancestry ("Q's brief has no `Depends on: P`") for fold-time skips only. The pre-fold path (`_cascade_not_clean`, `flow.py:1002-1029`) stays declared-edge-only. Given finding (b) above, Do may reasonably switch `_cascade_not_clean` to ancestry too "for consistency". That changes #652's behaviour and its hint text (`flow.py:1025-1026`, "its `Depends on` names …"), which nothing in the brief covers. The brief should say explicitly that the pre-fold cascade stays edge-only (out of scope), or include that change and test it.
- [ ] **The append-only requirement in Scope has no check that could fail.** Scope says "the carry's one push per target must not be followed by a rewrite of what it pushed (no extra force-push)". The issue itself allows "re-fold without them", and a re-fold done after the push is exactly what this bans. Yet criteria (1)-(3) only check ancestry of the final line and of E's tip. A fix that pushes, detects the leak, then re-folds and force-pushes would pass all three. The fixture already has a push counter (`self.fx._pushes`, used at `tests/test_flow_resume_stack_prereqs.py:366`). Add a criterion that the carry makes exactly one push to the line in (1) and (2).
- [ ] **The criteria pin only one fold order.** Both cases ask for `["P", "Q", "X", …]`, so P is folded before Q. If the order is Q then P, Q merges first. P's own merge then becomes a no-op ("already in the line", `integrate.py:622-623`), so P is never skipped and is reported as carried through Q. That may be acceptable (P's merge never failed), but the brief neither states nor pins it. A Do that removes only dependents folded *after* the skipped id passes, and so does one that re-checks every carried id. Name the intended order semantics, or add a reversed-order case.
- [ ] **I could not check the dependency and conflict ids.** `Conflicts with: 673, 694` and "463 (last wave) depends on this" cite other bundles. This leaf received no `sources/` directory and no `dependency-state.json`, so I could not confirm those bundles exist or that 673/694 really edit `integrate.py:518-544` and the `_carry_finished` hold messages. The order (672 first) is only as good as those claims; the human should check them at sign-off.
- [ ] size backstop — this slice is behaving oversized: 3 round(s) already spent (threshold 3). Recommend answering `iterate-plan` at sign-off and authoring the split in the re-plan (`pdca split`), rather than `iterate-do`: a slice that is too big yields implementation-shaped findings every round, and splitting authors briefs, which is Plan's beat.
- [ ] T5 Judgment — Confirm the recorded path-based merged/closed-work conclusions and cover the affected test path — the supplied target has one synthetic base commit and no remote, preventing independent historical verification; `brief.md:27`, `review-target-state.log:3`.
- [ ] T5 Judgment — Decide whether to revise the promised ownership boundary — the brief excludes every skipped-branch commit beyond the base, while the patch exempts prerequisite-owned commits and documents a new false-hold limitation; `brief.md:16`, `target/docs/07-crosscutting.md:733`, `target/docs/07-crosscutting.md:745`.
- [ ] T5 Judgment — Approve or revise the narrower ownership contract and confirm affected-path prior art — the patch excludes prerequisite/recorded-line history beyond the brief’s base exclusion, while this snapshot cannot verify merged or closed/rejected history; `brief.md:16`, `target/docs/07-crosscutting.md:735`, `review-prior-art.log:2`.
- [ ] `template/src/pdca_harness/integrate.py:591-596` with `template/src/pdca_harness/flow.py:1125-1126`: on a re-issued run, origin's line usually already holds a finished id's earlier head, because the earlier run folded it there. If that id's branch later gets a commit that conflicts, `_own_work` (`integrate.py:930-958`) counts the earlier head, which is already on the line, as the skipped id's work. The fold then raises `SkippedWorkOnLine`, and the carry holds **every** finished id of the target with the "delete the line" hint. Before the patch, only the conflicting id was held and the rest were carried. This is deliberate: it is pinned by `test_a_line_already_holding_a_skipped_ids_work_is_not_carried_onto` and documented in `docs/07-crosscutting.md:737-741`. It also fits the brief's "append-only" rule. But that work is on the line already, so holding the whole target does not keep it off. The only effect is a larger hold on a common re-issue shape. A human should decide whether a commit the line already got from that id's own earlier head should count as "accounted for" here.

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
- Iteration delta (if iterating): Not converging: 4 builds, and each review found a new edge case in the same question, which commits count as a fold-time-skipped bundle's "own work" (round 1: shared base history; round 2: merge commits that resolve conflicts; round 3: Q's history pulled back into P; round 4: P's own earlier head on Q's recorded build line, which still leaks to a fresh line and lets D build). We have been round this loop on similar items before. Re-plan should decide which edge cases to cut off explicitly rather than chase each one: define "skipped id's work" precisely (over the base? over its recorded build line?), narrow the invariant to what is achievable, and put the rest (cut-by-hand containment, continued-line whole-target holds, stale conflict skips after restart, wrong hint when a holder also conflicts, mutual-blame on restart) out of scope or into separate issues. Consider splitting (pdca-pdca split): core declared-edge + containment hold vs. restart/hint cleanups.
- By / date: Eduard Ralph / 2026-10-15

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 5 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
