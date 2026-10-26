# Result — issue 749 / aim-the-fix-at-a-line-bundle-stranded-by-a-moved-base

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: 
- Success criterion: Real-git tests through `flow._drive_and_act` on `StackFoldGit`, as in child-1, asserting the holds map, stderr, and `cli._results_rc(results, holds=holds)`:
  (1) **Stranded partner** (parent case 3). child-1's case (1) shape plus `V` (`Depends on: W`), so a fold runs after wave 1. `main` moves mid-run. `W`'s own base came from the moved `main` and clashes with `A` on the line. `W` is held out of the line. Its line names `issue_A` and `<remote>/main` with the fix "rebuild issue_A's branch on the new <remote>/main", and does not blame `W` or tell W's owner to update its branch. `V` is skipped, an unrelated bundle completes, `W`'s base holds the moved `main`. Exit 1.
  (2) **Moved-on prerequisite not named** (iteration-4 adversary probe; a guard, green before and after). Base has a nine-line `shared.txt`. `K` (wave 0) adds `k.txt`. `N` (wave 0) edits line 2. `Y` (`Depends on: K`) edits line 2. Unrelated `W→V→U`. After `Y` publishes, K's owner pushes a fixup to `fix/K` that changes only `k.txt`. `Y` is held naming `issue_N` only. The line does not contain "conflicts with issue_K's" or "rebuild issue_Y's branch on issue_K's", and no K rebuild is proposed.
  (3) **Iteration-2/3 stranded probes**, one test each. The stranded trial runs on the base the head actually holds (`git merge-base head <remote>/main`), NOT on the current tip of `<remote>/main` (iteration-v3 SUMMARY §6, "main has moved twice"). (a) **`main` moved twice:** A edits lines 2 and 8 of a nine-line `shared.txt`; Y (`Depends on: Q`) edits line 2; an unrelated `m.txt` commit lands on main after the first fold, so Y's base holds it; after Y publishes, main edits line 8. A is NOT called stranded (it merges onto the base Y holds); Y gets the ordinary overlap hold naming `issue_A` with a `Conflicts with` proposal, and no "rebuild issue_A's branch on the new <remote>/main". (b) **`main` undid a commit:** A adds `a.txt`; main adds its own `a.txt` after the first fold; Y (adds `y.txt` only) and V (adds `v.txt` only) are built on that main; then main deletes `a.txt` again. Neither Y nor V is told to declare `Conflicts with: A`; their step is "update the branch from <remote>/main". (This probe may not pass through the (i)-(iii) re-try at all; Do states in `build-notes.md` which path it takes on the folded tip, and its assertion is only about the advice text.) (c) **Stranded check tied to the clash:** a partner counts as stranded only when the base move is what makes the head clash with it (the iteration-v2 finding: A edits `a.txt` and `shared.txt`, main later edits `a.txt`, Y edits `shared.txt` and does not hold that main commit) — Y gets the overlap advice, not only A's rebuild. (d) The `Conflicts with` partner `X` of a stranded hold gets no advice blaming the held bundle or waiting for its rebuild.
  (4) **Still a stop.** A clash with the base itself (`test_flow_same_wave_conflict.py::test_a_conflict_only_with_a_base_taken_in_mid_wave_still_stops_the_run`) still prints `STOPPING`. child-1's `test_a_clash_with_a_partner_whose_head_no_longer_fits_the_base_still_stops` (in `test_flow_cross_wave_fold_holds.py`) flips to a hold, and `build-notes.md` records that flip.
  With the production change reverted, (1) and (3a), (3c), (3d) print `STOPPING` (child-1's behaviour), so the file goes red; (2) is a guard and stays green. child-1's and child-2's suites and the existing suites stay green, apart from the flipped guard.
- Repo + branch target: eduralph/pdca-harness @ main (PRs target `main`). Do builds and the gate verifies on the run's line, `pdca-integration/main-r547f8028520f` with #738, child-1's (#747) and child-2's (#748) accepted work folded on top, exported as `$PDCA_VERIFY_BASE`. Anchors are on `9f7c446`. Do re-checks line numbers on the folded tip.
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

Review issue #749: distinguish a line partner stranded by a moved base from an ordinary overlap, hold the affected bundle, and direct rebuild advice to the correct owner.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | Ownership, start commit, stop boundaries, and offline acceptance cases are explicit and falsifiable; the same-file counterexample falls under the requirement that the base move actually cause the clash (brief.md:6; template/tests/test_flow_cross_wave_stranded_holds.py:504). |
| C2 Reproduction (red pre-fix) | PASS | Stashing only the two production files reproduced six assertion failures with `STOPPING` across the 16 focused tests; the failures match the frozen evidence (review-red.log:3; gate-logs/C4-verify.log:25). |
| C3 Change | PASS | The patch is confined to fold classification, hold advice, and regression coverage; it reuses the own-change and trial helpers without changing base selection or adding another trial worktree (template/src/pdca_harness/integrate.py:1974; template/src/pdca_harness/integrate.py:2024). |
| C4 Verification (red→green) | PASS | Restoring production changes made all 16 specified tests pass, independently reproducing the asserted transition; the additional regression is adjudicated in C5 (review-green.log:3; template/tests/test_flow_cross_wave_stranded_holds.py:324). |
| C5 Causal adequacy | NEEDS-HUMAN [impl] | Correct attribution when independent hunks share a file — file-name intersection admits an unrelated base move and incorrectly proposes the partner's rebuild; the real-git counterexample passes before the fix and fails afterward (template/src/pdca_harness/integrate.py:1968; review-same-file-probe.log:4). |
| T1 Structure | PASS | Classification stays in integrate and wording stays in flow, with one transient reason record and the existing trial lifecycle; no new persisted state or worktree mechanism is needed (template/src/pdca_harness/integrate.py:1803; template/src/pdca_harness/flow.py:1609; template/src/pdca_harness/integrate.py:2250). |
| T2 Shape | PASS | Independent whitespace/syntax checks, documentation lint, and 22-page rendering with internal-link audit passed; frozen host-parity output agrees (review-docs.log:2; gate-logs/host-ci-docs.log:10). |
| T3 Runtime | PASS | Independently ran 2,632 driver tests successfully with two skips; frozen evidence shows all 24 root render/update tests executed successfully (review-suite.log:1817; gate-logs/T3-suite.log:54). |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the deferred row explicitly reserves the substantive audit for publish (gate-logs/T4-contribution.log:10). |
| T5 Judgment | NEEDS-HUMAN | Confirm affected-path merged and closed/rejected prior art for flow.py and integrate.py — the supplied snapshot exposes one synthetic commit, no remotes, and none of the cited #739 iteration records, so the required historical comparison cannot be established (review-prior-art.log:1; brief.md:17). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the resulting owner-directed rebuild/update instructions are actionable for maintainers across the specified moving-base workflows — executable coverage establishes behavior but maintainer acceptance of that workflow remains owed (template/src/pdca_harness/flow.py:1635; template/tests/test_flow_cross_wave_stranded_holds.py:537). |

Source citations beginning `template/` are grounded in `$PDCA_TARGET` (`target/`). The target matches the patch: reverse application checks passed before and after the independent reruns, and the production changes were restored. No target-state caveat was encountered.

**Builder-fixable finding: independent conflicts in the same file receive moved-base blame.** At `template/src/pdca_harness/integrate.py:1968`, overlapping file names suffice to admit a stranded explanation. They do not establish that the base move caused the actual conflict. The existing guard at `template/tests/test_flow_cross_wave_stranded_holds.py:504` catches the equivalent case only when the two conflicts occupy different files.

I exercised a same-file variant through the production `flow._drive_and_act` and real Git. Start with nine lines in `shared.txt`. A changes lines 2 and 8. After the first fold, main independently changes line 8. Y depends on Q, is built on that moved main, changes line 2, and restores line 8 to its original content. An unrelated W → V → U chain forces subsequent folds, with V using `Stacks on: W`. A and Y conflict only on line 2: the captured plain-Git merge leaves line 8 clean (`review-same-file-probe.log:9`). Y has undone the base move, so that move does not explain this clash.

Without the production changes, the run preserves the stop and proposes no rebuild for A (`review-same-file-baseline.log:4`, exit 0 for the probe). With the patch, it records `{'Y': 'conflict'}`, returns 3, and tells A's owner to rebuild on new main (`review-same-file-probe.log:3`, probe assertion failure at line 28). This violates the same causal boundary the existing different-file guard protects. Add coverage for independent hunks in one file and establish causal attribution beyond path intersection before issuing the stranded-partner advice.

The standalone probe is `review-same-file-probe.py`. From this report's directory, reproduce its failure on the restored patched target with:

```sh
TMPDIR="$PWD/review-scratch" PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH="$PWD/target/template/src:$PWD/target/template" \
  python3 review-same-file-probe.py
```

Independent verification also exercised direct production imports and the real fold (`template/tests/test_flow_cross_wave_stranded_holds.py:61`, `:198`, `:214`), matching the C5 production-path log. The reviewer interpreter lacks Copier, so the root render/update assessment uses the frozen T3 log, which shows 24 actual successful tests; the full driver suite and docs checks were rerun locally. The instance-scoped gate wrappers are not supplied here; their frozen logs were read. The brief declares no external dependencies, and the relevant Git topology was exercised directly. No capability-probe/load-time symptom guard was introduced.

For prior art, the affected-path history query and absence of supplied rejected iterations are recorded in `review-prior-art.log`. The brief's historical references identify what must be checked but do not supply evidence that the merged-history and closed/rejected-work comparison ran. This remains a human decision, separate from the reproducible C5 implementation defect.

<!-- pdca:leaf-complete -->

### Advisory — adversary

# Adversarial review — issue #749 (stranded line bundle after a moved base)

**Bottom line:** the red→green proof holds up. I found one concrete input where the fix holds a bundle with advice that does not work, where the old code stopped. That case, plus two smaller points, is below.

## Evidence (attempted to refute; could not)

- **The red→green proof is real.** I re-ran it in sandbox copies of `$PDCA_TARGET/template`, one as-is and one with only `flow.py` and `integrate.py` put back to `HEAD`.
  - With the fix: `test_flow_cross_wave_stranded_holds` plus `test_flow_cross_wave_fold_holds` give 16/16 OK.
  - Without it: 6 FAIL — the 5 new hold cases and the flipped `test_a_clash_with_a_partner_whose_head_no_longer_fits_the_base_holds_it` (`template/tests/test_flow_cross_wave_fold_holds.py:404`), each ending in `STOPPING`. The two guards stay green, as the brief says they should.
  - This matches `gate-logs/C4-verify.log`.
  - The tests drive the production path: `flow._drive_and_act` on real git, importing modules only (`template/tests/test_flow_cross_wave_stranded_holds.py:61`). They stub only the build/publish leaves and `gh`. They are not a copy of the production logic.
  - Case (4) still stops (`kind == "base"` never reaches `_held_by_move`, `integrate.py:1878`), and the T3 log shows 2632 tests OK.
- **Attacks that did not land:**
  - *Stranded hold with no own-change clash.* The trial where the line's side wins (`integrate.py:1987`) catches any clash of the held branch's own change with line work. A clash that only P and R make together (P renames `shared.txt`, R rewrites it), with no other partner, still stops: `mine` stays empty (`integrate.py:2001`).
  - *Dry runs and the carry.* Both pass `moved=None` (`flow.py:3161`; `integrate.py:673`).
  - *`Conflicts with` partner wording.* `flow.py:863` uses the moved wording only when the partner is in `held_moved`.
  - *"Past" advice.* It is tried before it is given: the branch is updated from the base, then merged onto the line (`integrate.py:1977-1982`).

## Findings

- NEEDS-HUMAN [impl] — **The "own" sub-case of a stranded hold has no check that the named bundles explain the whole clash. A run that used to stop now holds with advice that does not work.** `integrate.py:1989-2005` (`_held_by_move`):
  - It names `own` from single-bundle trials only (`_partners` on `held`, plus each stranded bundle rebuilt). It never runs #748's `_together` and never runs an acceptance trial like `_explains`.
  - That breaks the promise in `fold`'s docstring (`integrate.py:496`): "one the named bundles do not explain — raises, as before".
  - **Failing case (run as a probe on the patched copy):**
    - Base has `shared.txt` = TEN and `b.txt` = `b0`.
    - Wave 0: A adds `a.txt`; B sets `b.txt` to `B's`; P renames `shared.txt` → `moved.txt`; R rewrites `shared.txt` lines 1-7 (the P/R recipe from `test_flow_cross_wave_joint_holds.py:270`); Z adds `z.txt`.
    - W (`Depends on: Z`) adds `w.txt`, sets `b.txt` to `W's`, and edits `shared.txt` line 10. V (`Depends on: W`).
    - After fold 1, main gets its own `a.txt`.
  - **Result with the fix:** W is held, naming only A (stranded) and B (own). It says "(conflicts in a.txt, b.txt, shared.txt)", but nothing is named for `shared.txt`. The end-of-run line says: "rebuild issue_A's branch on the new origin/main. Proposed … declare `Conflicts with: B` … rebuild issue_W on a base that holds issue_B."
  - **Following that advice still fails:** main + A rebuilt on main + B + P + R + (W merged with B) conflicts at W, in `shared.txt`. Without P and R it merges clean.
  - **Without the fix:** `STOPPING`.
  - **Suggested fix:** before returning `own`, run an acceptance trial with the stranded bundles rebuilt and the `own` partners treated as #747 treats them. Or run `_together` on `held` over the bundles that are not lost. Return None (stop) when the head still conflicts. Add this case as a still-stops (or names-P-and-R) test.
- NEEDS-HUMAN [impl] — **The "own change merges onto the base it holds" guard can never fire.** `integrate.py:1975-1976`, with its docstring at `:1939-1940`.
  - `held` is `git merge-base head base_ref`, and every `lead` rev is `git merge-base head <bundle>`. All of them are ancestors of `head`, so `_trial(held, [*lead, head])` is clean by construction. It can only fail if the `lead` revs clash with each other, which says nothing about the head's own change.
  - The brief's rule (ii) condition (`_trial(S, [head])` clean) has the same problem: it is always true. What actually separates "stranded" from an ordinary overlap is the trial where the line's side wins (`:1987`).
  - If the reviewer counted rule (ii) as a real guard, that credit is not earned. Drop the dead check, or replace it, and fix the docstring so it does not describe a case that cannot happen.
- NEEDS-HUMAN [impl] — **Minor wording error.** `flow.py:1635-1637` says the stranded bundle "does not merge cleanly onto origin/main, which issue_W's branch holds". `base` is the *current* `base_ref`, so when main moved again after W was built and A fails on both, W does not hold `origin/main` as it is now. Say "the origin/main issue_W's branch holds", as the `past` wording at `:1629` already does.
- NEEDS-HUMAN [human] — **The patch adds a fourth outcome the brief's (i)-(iii) do not define.** That outcome is the `past` hold: update the held branch from the base (`integrate.py:1971`, `:1977-1982`; `flow.py:1626-1632`).
  - It runs where child-1's rule (d) does **not** fail. In case (3b), A merges onto `origin/main` as it is now, so `now` is empty.
  - The brief scoped the re-try to "where child-1's rule (d) fails" and said "(iii) anything else stops as today". The brief did leave (3b)'s path to Do, though.
  - The advice is trial-checked and I found no input that makes it wrong. Still, it turns a class of stops into holds, which the brief did not spell out. Accept it at sign-off on purpose, not by default.

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — issue #749 (stranded partner on a moved base)

Lens: bugs the patch introduces, plus reuse / simplification / efficiency. Line numbers are on the patched target at `$PDCA_TARGET`. Gate evidence: C4 is red before the fix (5 of 7 new tests fail with `STOPPING`) and green after; T3 suites pass.

I found no correctness bug that would stop the run wrongly or hold the wrong bundle in the cases the brief covers. The new trials go through `_trial`, and the patch adds no second worktree helper. `_own_change` (child-2's helper) is reused, not copied, and nothing squashes the head onto its start. The findings below are one scope question, one fitness question, and two small cleanups.

- NEEDS-HUMAN [human] — `template/src/pdca_harness/integrate.py:1949-1952`, `:1977-1982`: the patch adds a third outcome the brief does not list, the `past` hold. A line bundle doesn't merge onto the base the head holds but does merge onto `<remote>/main` now, and the head is told to "update <name>'s branch from <remote>/main" (`flow.py:1626`). The brief's rule (iii) says "anything else stops as today". Probe (3b) does want that advice text, and the brief allowed (3b) to take another path, so this is a defensible reading. Still, it turns a class of former `STOPPING` runs into holds that the brief never specified. The test file shows this: `test_main_undid_the_commit_…` was red before the fix because it stopped. Confirm that this extra hold kind is wanted in this child, and is not a separate change.
- NEEDS-HUMAN [human] — `template/src/pdca_harness/integrate.py:1962-1966` with `template/tests/test_flow_cross_wave_stranded_holds.py:498`: in case (3c), A's branch on the line no longer merges onto the current `origin/main`, but Y gets only the ordinary overlap advice. The test asserts that "rebuild issue_A's branch" is **absent**. The brief says Y gets the overlap advice "not only A's rebuild", which can be read as wanting both. As built, nothing in the run tells A's owner that A's branch no longer fits main. Decide whether that silence is the intended reading.
- `template/src/pdca_harness/integrate.py:1974-1976` (simplification): `held` is `git merge-base head base_ref`, so it is an ancestor of `head`. Each `lead` rev is also an ancestor of `head`. That makes `_trial(held, [*lead, head])` a merge of a commit's own ancestors into it, which is clean except in rare criss-cross merges. The brief's "`_trial(S, [head])` clean" condition holds by construction and screens out almost nothing. The real "own change does not clash" test is the line-tip trial at `:1987`. This is harmless (one extra trial), but the comment "its own change does not merge onto the base it holds" overstates what the trial can catch. Either drop the trial or say in the docstring that it is a guard for a degenerate history.
- `template/src/pdca_harness/integrate.py:1958-1961` (efficiency, minor): `now` is always computed first. When `held != base_ref`, a second full `_unfit` pass runs on `held`, and each pass recomputes `_own_change` and `_built_on`. `_pinned` at `:1965` then runs `_built_on` on `held` again, and so does the `own` search at `:1989`. All of this runs only after a fold merge has already conflicted and no #747/#748 rule matched, so it is not on a hot path. Reusing the `under` that `_unfit(…, held, …)` already built would save one `_built_on` walk. This is optional.

Reuse looks good on the `flow.py` side. `_where` (`flow.py:1590`) and `_overlap_step` (`flow.py:1647`) pull out logic that `_announce_conflict_holds` and `_report_conflict_holds` used to duplicate inline, and the ordinary (non-moved) wording is unchanged. The `Conflicts with` partner line for a moved hold (`flow.py:863-869`) uses the same `_moved_hold` wording, and in the pure-stranded case it neither blames the held bundle nor waits on its rebuild. Test (3d) at `test_flow_cross_wave_stranded_holds.py:554` checks this.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] C5 Causal adequacy — Correct attribution when independent hunks share a file — file-name intersection admits an unrelated base move and incorrectly proposes the partner's rebuild; the real-git counterexample passes before the fix and fails afterward (template/src/pdca_harness/integrate.py:1968; review-same-file-probe.log:4).
- [ ] T5 Judgment — Confirm affected-path merged and closed/rejected prior art for flow.py and integrate.py — the supplied snapshot exposes one synthetic commit, no remotes, and none of the cited #739 iteration records, so the required historical comparison cannot be established (review-prior-art.log:1; brief.md:17).
- [ ] Validation — fitness-to-purpose — Decide whether the resulting owner-directed rebuild/update instructions are actionable for maintainers across the specified moving-base workflows — executable coverage establishes behavior but maintainer acceptance of that workflow remains owed (template/src/pdca_harness/flow.py:1635; template/tests/test_flow_cross_wave_stranded_holds.py:537).
- [ ] **The "own" sub-case of a stranded hold has no check that the named bundles explain the whole clash. A run that used to stop now holds with advice that does not work.** `integrate.py:1989-2005` (`_held_by_move`):
- [ ] **The "own change merges onto the base it holds" guard can never fire.** `integrate.py:1975-1976`, with its docstring at `:1939-1940`.
- [ ] **Minor wording error.** `flow.py:1635-1637` says the stranded bundle "does not merge cleanly onto origin/main, which issue_W's branch holds". `base` is the *current* `base_ref`, so when main moved again after W was built and A fails on both, W does not hold `origin/main` as it is now. Say "the origin/main issue_W's branch holds", as the `past` wording at `:1629` already does.
- [ ] **The patch adds a fourth outcome the brief's (i)-(iii) do not define.** That outcome is the `past` hold: update the held branch from the base (`integrate.py:1971`, `:1977-1982`; `flow.py:1626-1632`).
- [ ] `template/src/pdca_harness/integrate.py:1949-1952`, `:1977-1982`: the patch adds a third outcome the brief does not list, the `past` hold. A line bundle doesn't merge onto the base the head holds but does merge onto `<remote>/main` now, and the head is told to "update <name>'s branch from <remote>/main" (`flow.py:1626`). The brief's rule (iii) says "anything else stops as today". Probe (3b) does want that advice text, and the brief allowed (3b) to take another path, so this is a defensible reading. Still, it turns a class of former `STOPPING` runs into holds that the brief never specified. The test file shows this: `test_main_undid_the_commit_…` was red before the fix because it stopped. Confirm that this extra hold kind is wanted in this child, and is not a separate change.
- [ ] `template/src/pdca_harness/integrate.py:1962-1966` with `template/tests/test_flow_cross_wave_stranded_holds.py:498`: in case (3c), A's branch on the line no longer merges onto the current `origin/main`, but Y gets only the ordinary overlap advice. The test asserts that "rebuild issue_A's branch" is **absent**. The brief says Y gets the overlap advice "not only A's rebuild", which can be read as wanting both. As built, nothing in the run tells A's owner that A's branch no longer fits main. Decide whether that silence is the intended reading.
- [ ] **The prerequisite has not been built, so nothing the brief anchors on exists yet.** `dependency-state.json` gives `"747": {"declared": "Depends on", "exists": true, "state": "PLANNED"}`. Every part of the brief starts from child-1's work: "child-1's rule (d) fails", "child-1's case (1) shape", "child-1's 'partner's own head fails onto the base' guard flips". None of it is in the target. Grepping `rule \(d\)` across `template/` finds nothing. The classifier at `integrate.py:1316-1332` has only `base`/`batch`/`line`/`moved`/`off` branches. Until 747 reaches the line, Do cannot locate the call site, the guard to flip, or the case-(1) fixture shape. Make Plan wait until 747 is accepted, or state that this bundle cannot start before then.
- [ ] **#738 is a hard prerequisite, but it is not declared.** The Ordering note says "Needs #738 (accepted and folded on the line) for case (1) to be reachable". Falsifiability says "without it the run stops earlier, at the base build". Yet `Depends on:` lists only `747`, and `dependency-state.json` tracks only 747. The driver therefore cannot hold this bundle until #738 lands. Case (1) would then hit the existing `wave {k} did not integrate … STOPPING` path (`flow.py:2649`) for an unrelated reason, and red→green would mean nothing. Add `Depends on: 738`, or explain why it doesn't need to be declared.
- [ ] **The brief holds two or three logical changes, not one.**
- [ ] **Item (b) targets a bug in a patch that was never merged, not a defect in the target.** The brief calls it the bug in "`_rebuilt` in `results/issue_739/iteration-v4/patch.diff`" ("The squash in `_rebuilt` is the adversary's bug"), and it cites anchors from the "iteration-v4 tip" (`integrate.py:1329-1331`, `2080-2117`). On the target, `integrate.py:1329-1331` is the classifier's `except` block, not a fast-forward take, and there is no `_rebuilt`. The current `_partners` already names a partner only for its own change, and `_built_on` (`integrate.py:1363-1395`) already says "one whose branch moved on since owns its commits". The brief itself admits that case (2) "fails only if child-2 went first with a squashed trial; otherwise it is a guard". So on the expected path the "fix" has no red state. Say plainly that it is a guard, not a fix, and drop "Also fix" from the Defect line.
- [ ] **The success criterion depends on build order, which nothing fixes.** Case (2)'s red/green status, the scope ("if child-2 is already on the line") and the base ("and child-2's, if it went first") all branch on whether #748 has landed. `Conflicts with: 748` only keeps the two out of the same wave; it doesn't set their order. So a reviewer cannot know in advance which criterion applies. Pick an order (e.g. add `Depends on: 748`, or declare that this child goes first and child-2 adapts), so that Check has a single falsifiable target.
- [ ] **The rule that trials build from the head's own change is unclear about the start commit.** The Defect line says "merge into the trial start what the head already holds of each line bundle (`git merge-base head <its head>`)". Criterion (3) says the stranded trial runs on `git merge-base head <remote>/main`, "NOT on the current tip". The criterion also writes the stranded test as `_trial(base, [partner head])` without saying which `base`. The current classifier passes `base_ref`, the current base (`integrate.py:1317,1351`). If "base" here means the current `<remote>/main`, case (3a) contradicts case (1). Name the start commit explicitly for both the stranded trial and the own-change trial.
- [ ] **The tracker record cannot be checked.** The root cause and the "Invariant to restore" rest on "the human's #725 re-plan decision 2 (hole 3, `results/issue_725/iteration-v1/SUMMARY.md` §6/§9)", "the #739 iteration-v4 split decision" and the iteration-v2/v3 SUMMARY §6 rejections. None of these were provided: no `notes.json`, no `sources/`, and no `results/` under the target. I could not confirm that the thread asks for partner-aimed advice rather than, say, a stop with a different message. A human should confirm that decision 2 says what the brief says.
- [ ] **Stale anchors.** Scope cites `_announce_conflict_holds (flow.py:1532)`, but on the target it is at `flow.py:1250`. Its current text is "its change conflicts with …, merged before it in the same wave {k}", which is a same-wave-only message. `_trial` is at `integrate.py:1398`, not `2080`. The brief says "Anchors are on `9f7c446`", but the target is at `2ff8f3b`. Do re-anchors anyway, but the Scope line gives `1532` as a fact, and the same-wave wording of the message being extended is not mentioned. The stranded hold is cross-wave, so the docstring and the "same wave" text change too.

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
- Iteration delta (if iterating): Auto-iterate (round 1): rebuilding for the implementation-level findings — C5 Causal adequacy — Correct attribution when independent hunks share a file — file-name intersection admits an unrelated base move and incorrectly proposes the partner's rebuild; the real-git counterexample passes before the fix and fails afterward (template/src/pdca_harness/integrate.py:1968; review-same-file-probe.log:4).; **The "own" sub-case of a stranded hold has no check that the named bundles explain the whole clash. A run that used to stop now holds with advice that does not work.** `integrate.py:1989-2005` (`_held_by_move`):; **The "own change merges onto the base it holds" guard can never fire.** `integrate.py:1975-1976`, with its docstring at `:1939-1940`.; **Minor wording error.** `flow.py:1635-1637` says the stranded bundle "does not merge cleanly onto origin/main, which issue_W's branch holds". `base` is the *current* `base_ref`, so when main moved again after W was built and A fails on both, W does not hold `origin/main` as it is now. Say "the origin/main issue_W's branch holds", as the `past` wording at `:1629` already does.. Deferred, not addressed here: 12 finding(s) that need human judgment, held in deferred-findings.json for the human at handover — not build work
- By / date: auto-iterate / 2026-10-15

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 8 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
