# Result — issue 724 / flow-builds-each-bundle-on-its-declared-prerequisites

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: In stack mode every runnable bundle is pointed at the run's one integration line (`_point_at_integration`, `template/src/pdca_harness/flow.py:890`, called at `:2549`). That line holds every earlier-wave bundle of the target, so a PR's branch carries unrelated bundles' work. Merging it lands work whose own PR the human closed (#630, moved onto #463).
- Success criterion: Real-git tests driving `flow._drive_and_act` through real folds on the `StackFoldGit` fixture, with build and sign-off stubbed and `_publish_bundle` cutting each PR branch from the recorded stack-base tip, as `template/tests/test_flow_same_wave_conflict.py:131` does:
  (1) **The #630 case.** `A`, `Z` (wave 0, unrelated, two commits each), `B` (`Depends on: A`). Every commit of `origin/main..fix/A` is on `fix/B`; no commit of `origin/main..fix/Z` is. `B`'s recorded stack base is a branch on origin holding `fix/A`'s tip and not `fix/Z`'s, and `B` was built on it. All COMPLETE.
  (2) **Transitive.** Add `C` (`Depends on: B`). `fix/C` has `fix/A` and `fix/B`, not `fix/Z`.
  (3) **Conflict partner.** Add `E` (`Conflicts with: A`; the scheduler puts the name-higher id in the later wave, `waves.compute_waves`). `fix/E` has `fix/A`, not `fix/Z`.
  (4) **In-batch `Depends on (merged)`.** Add `G` (`Depends on (merged): A`). `fix/G` has `fix/A`, not `fix/Z`.
  (5) **Empty closure → real base.** Add `H` whose only edge is to an in-batch `N` that closed with no patch. `H`'s stack base is cleared (`publish.read_stack_base` empty); `fix/H` has neither `fix/A` nor `fix/Z`.
  (6) **Carried prerequisites (#646).** In `test_flow_resume_stack_prereqs.py`'s carry fixture: carried clean `P` and `X`, planned `D` (`Depends on: P`) and `E` (`Depends on: X`). `D`'s base has `fix/P`, not `fix/X`; `E`'s has `fix/X`, not `fix/P`. Both COMPLETE.
  (7) **Carry defect: foreign ancestry.** Carried `P` whose branch was cut from an old line holding `X` (also carried, not in `D`'s closure); `D` (`Depends on: P`). Observable: `D` is never built (it stays PLANNED and has no stack-base record); the run prints a `STOPPING` line whose text contains `issue_P` and `issue_X` (the `IntegrationError` from #723's `build_bundle_base`); no branch holding `X`'s commits is recorded as anyone's stack base. (Until #725 the run stops there; #725 makes it a hold.)
  (8) **Carry defect: rewritten carried prerequisite (#633).** Carried `P`; after the carry, `fix/P` is force-pushed to a different commit; `D` (`Depends on: P`). Observable: `D` stays PLANNED with no stack-base record; the run prints a `STOPPING` line whose text contains `issue_P` and the word `rewritten` (or the wording #723's rewrite error uses, which the test reads from that error, not a copy). The carry's recorded heads reach `build_bundle_base`'s `carried`.
  (9) **#655 judged on the base `d` gets.** The set-up of `test_flow_merged_prereq_on_line.py` where out-of-batch `P`'s PR merges into `main` after the first fold: `D` is not held; it is built, COMPLETE, and its base contains `P`'s merge commit.
  (10) **Nothing else regresses.** The existing suites `test_integrate_stack_bases.py`, `test_flow_same_wave_conflict.py`, `test_flow_resume_stack_prereqs.py`, `test_flow_merged_prereq_on_line.py`, `test_flow_conflict_partner_hold.py`, `test_flow_reissue_after_conflict_hold.py`, `test_flow_hold_exit_code.py`, `test_integrate_carried_rewrite_late.py`, `test_flow_slice.py` (all present on `489e5fb`; the three from 693-695 are not on `main`) and #723's `template/tests/test_integrate_bundle_base.py` stay green. An existing assertion may change ONLY by restating the base it checks in terms of content ("the recorded base contains the tip of each closure member, and no commit of any other run bundle's branch"), never by branch name and never weaker. The #655 hold tests flip per (9). Known to need it: `test_flow_same_wave_conflict.py` `_built_on_line` (`:169`); `test_flow_resume_stack_prereqs.py`'s `self._line([...])` / `self.line` assertions; `test_flow_merged_prereq_on_line.py`'s hold cases. A test INPUT may change only where its premise ("X is built on Y") now needs a declared edge, and `build-notes.md` names every such change with before and after.
  Pre-change, (1)–(8) fail (every wave>0 and carry dependent is on the line, which holds `Z` / `X`); (9) fails because `D` is held.
- Repo + branch target: eduralph/pdca-harness @ main (PRs target `main`). Base Do builds and the gate verifies on: the run's line (`pdca-integration/main-r547f8028520f`, from `489e5fb`) after #723 has folded onto it — the adopting run exports it as `$PDCA_VERIFY_BASE`, and the pre-#463 rule this child replaces is what builds this child there. Every `path:line` in this brief is on `489e5fb`, not on `main` (`d6057eb`); #723 adds only `integrate.build_bundle_base` and its test, so no `flow.py` anchor moves.
- Scope (one logical fix) / out of scope: `template/src/pdca_harness/flow.py`: compute each runnable bundle's closure per the Invariant (only accepted bundles whose branch the fold carries count, `integrate._fold_candidates` `integrate.py:217`; a patchless one adds nothing; a held one already holds `d` via `_runnable`). Give `d` an empty-closure `clear_stack_base`, or a base built by #723's `integrate.build_bundle_base` with its members, their carried heads (from the pre-wave carry, `_carry_finished` `flow.py:1091`), and the other run bundles' heads as excluded. Record it with `publish.write_stack_base(d, branch, tip)` (`publish.py:647`); worktree, `$PDCA_VERIFY_BASE` and the PR cut already read that record. Keep the run's line, folded after each wave as today, as the integration check (re-gate, #674 holds, #646 carry); nothing is cut from it any more. #655: `_runnable` judges an out-of-batch merged prerequisite by `merged.merged_into` alone for every bundle; remove `_line_lacks_merge` (`flow.py:850`) and the now-unused `merged.merge_and_head` (`merged.py:149`), fixing the `merged.py` docstrings (`:24`, `:188`). A base build failure stops the run before the wave, with the error #723 raises (#725 turns it into a hold). Restate the existing tests per (10). / out of scope: holds for base-build failures and for cross-wave overlaps at the line fold (#725); every doc, glossary and docstring stating the stack rule, including `integrate.py`'s module docstring, `publish.py:42-44`, `:252-277`, `:648-690`, `gates.py:535-539`, `drift.py:53`, `_adopt_split_children`'s docstring (#725); merge mode; wave scheduling; PR targets (still the real base, #593); per-bundle base cleanup on origin.

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

Review dependency-scoped stack bases so each bundle carries its declared prerequisites without unrelated bundles’ commits.

Source citations below resolve under `$PDCA_TARGET`; brief and evidence citations resolve in this review directory. The target includes #723 and matches the supplied patch (`git apply --reverse --check` passed); there is no target-state caveat.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The offline ancestry contract distinguishes declared work, unrelated work, carry failures and merged prerequisites with falsifiable outcomes; `brief.md:3`, `brief.md:16`, `brief.md:24`. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only the three production changes left the tests runnable and produced 19 assertion failures, including unrelated Z commits reaching B; `review-red.log:172`, `review-red.log:354`; test assertion: `template/tests/test_flow_dependency_scoped_bases.py:296`. |
| C3 Change | PASS | The patch addresses base selection and the obsolete merge-on-line check, with head bookkeeping needed by the prior iteration; it applies exactly to the supplied target and passes whitespace checking; `template/src/pdca_harness/flow.py:2678`, `template/src/pdca_harness/integrate.py:867`, `brief.md:33`. |
| C4 Verification (red→green) | PASS | After stash restoration, the same 19 tests passed independently; the frozen C4 log also records all affected suites green and the production-reverted leg red; `review-green.log:3`, `gate-logs/C4-verify.log:10`, `gate-logs/C4-verify.log:976`, `gate-logs/C4-verify.log:2636`. |
| C5 Causal adequacy | NEEDS-HUMAN [impl] | Preserve transitive edges through finished patchless prerequisites on resume — two independent real-git cases show either COMPLETE with missing prerequisite commits or an unjustified STOPPING; the graph excludes those nodes at `template/src/pdca_harness/flow.py:2597` and `template/src/pdca_harness/flow.py:983`, then drops their edges at `template/src/pdca_harness/flow.py:909`; `review-carried-patchless.log:8`, `review-carried-patchless-member.log:5`. |
| T1 Structure | PASS | Closure calculation and base construction remain in the flow/integration boundary, and base records are assigned before build leaves start; no additional structural defect found; `template/src/pdca_harness/flow.py:955`, `template/src/pdca_harness/flow.py:2691`. |
| T2 Shape | PASS | Independently reran docs lint and the host workflow’s renderer/link audit: both clean, 22 pages rendered; whitespace check clean; frozen docs and host-parity logs agree; `gate-logs/T2-docs.log:11`, `gate-logs/host-ci-docs.log:11`, `.github/workflows/docs-check.yml:36`. |
| T3 Runtime | PASS | Independent driver-suite run passed 2,573 tests (two skips); local root runner returned 77 for unavailable Copier, while frozen evidence explicitly records all 24 root tests executed and passed; `review-suite.log:1817`, `review-root-suite.log:6`, `gate-logs/T3-suite.log:54`. |
| T4 Contribution | N/A | Contribution artifacts are intentionally drafted after Check; the deferred gate owes its substantive audit to publish and is not a reproduced green; `gate-logs/T4-contribution.log:10`. |
| T5 Judgment | NEEDS-HUMAN | Confirm prior art by affected file path across merged history and closed/rejected work — this snapshot has one synthetic base commit and no remotes, while the brief documents selected flow history and an earlier rejection but not a complete closed-work search; `brief.md:27`; affected paths include `template/src/pdca_harness/flow.py:845` and `template/src/pdca_harness/integrate.py:716`. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether dependency-only PR ancestry with a retained combined integration check and whole-run stops fits the intended operator workflow — real-git tests establish offline behavior, but the resume defect below must be addressed before judging completeness; `brief.md:16`, `brief.md:22`, `template/tests/test_flow_dependency_scoped_bases.py:27`. |

**Implementation finding: finished patchless nodes sever the dependency graph on resume.**

`_carry_finished` admits only bundles with a patch into its carry candidates (`template/src/pdca_harness/flow.py:1243`; `template/src/pdca_harness/integrate.py:237`). The caller then passes only those actually carried to `_bundle_bases` (`template/src/pdca_harness/flow.py:2597`). Its `paths` graph contains scheduled bundles and carried bundles, so a finished patchless N is absent (`template/src/pdca_harness/flow.py:983`). `_ordered_after` discards the edge to N before `_closure` can traverse N’s prerequisites (`template/src/pdca_harness/flow.py:907`). This contradicts the transitivity already tested for a scheduled patchless N (`template/tests/test_flow_dependency_scoped_bases.py:325`).

I exercised two histories entirely through the patched production flow, using the supplied real-git fixture and its specified leaf/publish stubs:

- Run `[A, N, D, W]`, with `N Depends on A` and closed without a patch, `D Depends on N`, and `W Depends on A`. Initially fail D and W; reissue the same batch driving D and W. The carry takes A. D becomes COMPLETE on the real base and contains none of A, while W correctly contains A (`review-carried-patchless.log:1`).
- Run `[A, N, P, D]`, with patchless N depending on A, P depending on N, and D depending on P. Initially fail D after P is successfully built on A; reissue driving D. The carry takes A and P, but D’s members contain P alone. The run wrongly stops, calling A’s declared transitive work foreign (`review-carried-patchless-member.log:1`). No external rewrite or foreign branch was introduced.

Keep finished patchless bundles available for dependency traversal while retaining the clean-candidate restriction on actual base members. Add resume coverage for both the missing-work and false-stop outcomes. This is one implementation concern with two observed effects; the existing passing gates do not cover it. The fix removes the original integration-line cause rather than adding a capability probe; the symptom-guard smell-test does not fire.

The following reproduces both cases from this review directory with the patch applied. It writes fixture data only below the existing `review-tmp` directory:

```bash
cd "$PDCA_TARGET/template"
TMPDIR="$PDCA_TARGET/../review-tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 - <<'PYCODE'
from tests.test_flow_dependency_scoped_bases import DependencyScopedBases, TWO
from pdca_harness import state

outcomes = []
for through_member in (False, True):
    c = DependencyScopedBases()
    c.setUp()
    try:
        c._plan('A', TWO)
        c._plan('N', depends_on='A')
        c.close.add('N')
        if through_member:
            ids = ['A', 'N', 'P', 'D']
            c._plan('P', depends_on='N')
            c._plan('D', depends_on='P')
            c.failing.add('D')
            drive = ['D']
        else:
            ids = ['A', 'N', 'D', 'W']
            c._plan('D', depends_on='N')
            c._plan('W', depends_on='A')
            c.failing.update({'D', 'W'})
            drive = ['D', 'W']
        c._run(ids)
        c.failing.clear()
        c._run(ids, drive=drive)
        complete = c.results['D'] == state.COMPLETE
        has_a = complete and c.fx._ancestor(c._head('A'), c._head('D'))
        print('through_member:', through_member, 'results:', c.results,
              'D contains A:', has_a)
        print(c.err)
        outcomes.append(complete and has_a)
    finally:
        c.doCleanups()
assert all(outcomes), 'Resume must preserve the declared transitive A prerequisite'
PYCODE
```

The production stash was restored before all green and supplemental runs. Instance-scoped gate wrappers were not invoked from another checkout: production-import evidence was corroborated by the actual import and real flow calls (`template/tests/test_flow_dependency_scoped_bases.py:58`, `template/tests/test_flow_dependency_scoped_bases.py:210`), and frozen logs supplied the root-suite and deferred-contribution evidence. The brief’s required Python/git dependencies were exercised; Copier’s local absence is a reviewer-host limitation, not a patch defect or an unmet dependency for the ancestry tests.

<!-- pdca:leaf-complete -->

### Advisory — adversary

# Adversarial review — issue_724 (dependency-scoped bases, #463)

The red→green evidence holds up. I re-ran the new file and every suite named in criterion (10), plus `test_integrate_bundle_base.py`, on the patched tree: 308 tests, all OK. `gate-logs/C4-verify.log:1335-1337` shows all 19 new cases failing with the production change reverted, and they fail on assertions, not on import. The tests go through the real `flow._drive_and_act`, real folds and the real `integrate.build_bundle_base`; only build, sign-off, publish and `gh` are stubbed, which the brief allows. I found no tautology: `_built_on` compares ancestry against origin, and `_beyond`/`_own` (`tests/test_integrate_stack_bases.py:219-238`) do real rev-list checks.

I could not break `_closure` / `_ordered_after` on these cases:
- transitive edges through a bundle with no patch;
- a `Conflicts with` partner that never completed;
- carried partners found through `_cut_above`;
- held prerequisites in `held_unpushed`, `held_conflict` and `held_finished` (`_runnable` holds the dependent first in each case);
- members on another target;
- a same-wave newer head picked up through `carried_heads`.

The removal of the #655 check is clean: there are no callers left of `_line_lacks_merge` or `merge_and_head`. Two findings are left.

- NEEDS-HUMAN [impl] — **The rewrite reports now give the wrong commit and the wrong PRs.** The patch feeds heads that a bundle's own base took into the #633/#695 checks (`template/src/pdca_harness/flow.py:1017`, `carried_heads.update(took)`). But the messages still say the head is "the commit the line took" (`template/src/pdca_harness/integrate.py:1087-1090`). They also say the line "still carries the old commits, and so does every PR this run cut from {line}" (`integrate.py:1139-1144`), and the "unchecked" message says the same (`flow.py:2870-2877`). Since this patch, no PR is cut from the line. Concrete case: I ran the fixture from `test_a_head_a_base_took_is_checked_at_the_end_of_the_run` (`tests/test_flow_dependency_scoped_bases.py:495-505`) in a probe. The line tip holds h1 and **does not** hold h2. B's stack base is `pdca-integration/main-r…-bB`, not the line, and `fix/B` holds h2. Yet the report says h2 is "the commit the line took", that the line "still carries the old commits", and tells the human to rebuild "every PR this run cut from pdca-integration/main-r…". That set is empty. The PR that actually holds the dropped commit is B's, and the message never names it. The fold-time stop in `test_a_head_a_base_took_is_checked_by_the_next_fold` uses the same wrong wording through `_carried_rewrite`. The tests only check the message prefix and the sha (`:501-503`), so they miss it. Fix: record which bundle's base took each head, and say "B's base (`…-bB`) took h2; rebuild B's PR". Drop "cut from the line". These are runtime messages, not the docs or docstrings the brief defers to #725.

- NEEDS-HUMAN [human] — **A dependent of a legacy `Stacks on` or `Onto branch` prerequisite now stops the whole run, where before it was built.** Neither case appears in the brief's scope or out-of-scope list, and no test covers them. I checked both against a pre-fix copy of the tree:
  - *Legacy `Stacks on`, parent outside the batch:* B has `Stacks on: A` (A finished in an earlier run, not in the batch), and C has `Depends on: B`. A is not in `paths`, so B's closure is empty. `_point_at_integration` then clears B's stack-base record (`flow.py:842`). At wave 1, #723 refuses B as C's member because B "declares `Stacks on`" but has no record (`integrate.py:927-935`). Result: `STOPPING`, C PLANNED. Pre-fix, B and C are both COMPLETE.
  - *`Onto branch` prerequisite:* A is published with `Onto branch: upstream/feat`, and B has `Depends on: A`. `_member_cut_point` refuses any `Onto branch` member (`integrate.py:906-908`). Result: `STOPPING` at wave 1, B PLANNED. Pre-fix, B is COMPLETE. The line fold explicitly supports `Onto branch` bundles (`tests/test_integrate_stack_bases.py:354-376`, `:842-870`).

  Under #723's ownership rule, C's or B's base can never be built without commits that belong to no member. So writing a record will not fix this; it needs a decision. The options: support these as base members, hold the dependent (#725), or declare both edges unsupported in stack mode and refuse them at plan time. Until then, one such bundle stops every other bundle in its wave and every later wave.

Not filed, because the brief already accepts or defers them:
- Base-build failures, including a transient fetch failure (`test_flow_merged_prereq_on_line.py`'s fetch case), now stop the run instead of holding one bundle.
- A carried prerequisite built on a line from before this change, holding unrelated work, stops a re-issued run (criterion 7).
- Cross-wave text conflicts at the line fold now stop runs, because later bundles are no longer built on the line (#725).

Not checkable here, since `build-notes.md` is withheld: criterion (10) requires every test-input change to be listed in `build-notes.md` with before and after. Three input changes need checking:
- `tests/test_flow_reissue_after_conflict_hold.py`: 21's edge goes from `Depends on: 12` to `12, 10`.
- `tests/test_flow_resume_stack_prereqs.py`: `_publish_bundle` now restores the brief.
- `tests/test_integrate_carried_rewrite_late.py`: the race trigger moved to B's base push. The old line-push race is kept as the new case (1d).

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — issue_724 (dependency-scoped bundle bases, #463)

Lenses: correctness bugs the patch introduces, and reuse / simplification / efficiency.
Grounded on the patched tree at `$PDCA_TARGET`. Gates: C4 (red pre-fix, green post-fix), T3
(2573 tests OK, 2 skipped) and host-ci-docs all pass in `gate-logs/`.

Overall: I found no correctness bug that needs the builder to iterate. All five
round-1 findings are fixed in this diff:
- the closure now follows edges from carried bundles (`_closure` `flow.py:845`, `_ordered_after` `:885`, `_cut_above` `:924`);
- `Conflicts with` is read over drive-set plus carried bundles (`flow.py:985`);
- a base build now records the head it took (`merged_heads`, `integrate.py:867-868`, folded
  into `carried_heads` at `flow.py:1017`), and carried ids get the end-of-run check
  (`flow.py:2829-2831`);
- a `Conflicts with` partner that never completed is no longer walked through (`_closure`, `flow.py:845-883`,
  test at `test_flow_dependency_scoped_bases.py:356`);
- the old line-push race in `test_integrate_carried_rewrite_late.py` is kept as its own case
  (1d) instead of being replaced.

Minor notes (advisory, no action required):

- `template/src/pdca_harness/flow.py:981` — the `_bundle_bases` docstring says that on a failure
  "the caller stops the run before the wave builds and records nothing". That holds for the
  stack-base records. But if bundle 2 of a wave fails, bundle 1's base is already pushed to
  origin, and `carried_heads` was already updated at `:1017`. Today nothing goes wrong:
  `line_stopped` skips the end-of-run check (`:2829-2831`), and cleaning up per-bundle bases is out
  of scope per the brief. The wording could say "records no stack base" so a later reader
  doesn't rely on `carried_heads` being untouched.
- `template/src/pdca_harness/flow.py:837` — `_point_at_integration` now takes keys that are
  either a bundle name or a `(repo, base)` tuple. The flow only ever passes name keys
  (`:2691`). The tuple path is kept only for the older direct callers in
  `test_integrate.py:351,362` and `test_integrate_stack_bases.py:1100`. That's fine as a way
  to keep old callers working; a name-only signature would be simpler, but changing it would
  mean editing tests that criterion (10) says to leave alone, so leaving it is reasonable.
- `template/src/pdca_harness/flow.py:950-951` — `_cut_above` returns False on any git error. This
  fails closed on purpose and is documented: a base missing the partner's work is then refused
  by `build_bundle_base`, which names the partner, and the run stops. The cost is that a
  transient git failure here shows up as a foreign-work stop, not as the real git error. This
  is acceptable until #725 turns those stops into holds.
- Efficiency: each runnable bundle with members now gets its own fetch, merge and push under
  the integration lock (`flow.py:1009-1017` → `integrate.py:811-868`), on top of the line fold.
  The brief asks for this design. Any of those network steps failing now stops the run before
  the wave (`flow.py:2683-2687`), which the brief also accepts until #725.

No NEEDS-HUMAN items from this lens.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] C5 Causal adequacy — Preserve transitive edges through finished patchless prerequisites on resume — two independent real-git cases show either COMPLETE with missing prerequisite commits or an unjustified STOPPING; the graph excludes those nodes at `template/src/pdca_harness/flow.py:2597` and `template/src/pdca_harness/flow.py:983`, then drops their edges at `template/src/pdca_harness/flow.py:909`; `review-carried-patchless.log:8`, `review-carried-patchless-member.log:5`.
- [ ] T5 Judgment — Confirm prior art by affected file path across merged history and closed/rejected work — this snapshot has one synthetic base commit and no remotes, while the brief documents selected flow history and an earlier rejection but not a complete closed-work search; `brief.md:27`; affected paths include `template/src/pdca_harness/flow.py:845` and `template/src/pdca_harness/integrate.py:716`.
- [ ] Validation — fitness-to-purpose — Decide whether dependency-only PR ancestry with a retained combined integration check and whole-run stops fits the intended operator workflow — real-git tests establish offline behavior, but the resume defect below must be addressed before judging completeness; `brief.md:16`, `brief.md:22`, `template/tests/test_flow_dependency_scoped_bases.py:27`.
- [ ] **The rewrite reports now give the wrong commit and the wrong PRs.** The patch feeds heads that a bundle's own base took into the #633/#695 checks (`template/src/pdca_harness/flow.py:1017`, `carried_heads.update(took)`). But the messages still say the head is "the commit the line took" (`template/src/pdca_harness/integrate.py:1087-1090`). They also say the line "still carries the old commits, and so does every PR this run cut from {line}" (`integrate.py:1139-1144`), and the "unchecked" message says the same (`flow.py:2870-2877`). Since this patch, no PR is cut from the line. Concrete case: I ran the fixture from `test_a_head_a_base_took_is_checked_at_the_end_of_the_run` (`tests/test_flow_dependency_scoped_bases.py:495-505`) in a probe. The line tip holds h1 and **does not** hold h2. B's stack base is `pdca-integration/main-r…-bB`, not the line, and `fix/B` holds h2. Yet the report says h2 is "the commit the line took", that the line "still carries the old commits", and tells the human to rebuild "every PR this run cut from pdca-integration/main-r…". That set is empty. The PR that actually holds the dropped commit is B's, and the message never names it. The fold-time stop in `test_a_head_a_base_took_is_checked_by_the_next_fold` uses the same wrong wording through `_carried_rewrite`. The tests only check the message prefix and the sha (`:501-503`), so they miss it. Fix: record which bundle's base took each head, and say "B's base (`…-bB`) took h2; rebuild B's PR". Drop "cut from the line". These are runtime messages, not the docs or docstrings the brief defers to #725.
- [ ] **A dependent of a legacy `Stacks on` or `Onto branch` prerequisite now stops the whole run, where before it was built.** Neither case appears in the brief's scope or out-of-scope list, and no test covers them. I checked both against a pre-fix copy of the tree:
- [ ] **The tracker record is missing, so the problem statement can't be checked against the thread.** The cwd holds only `brief.md` and `dependency-state.json`. There is no `notes.json` and no `sources/`. The Invariant cites "#630's finding (the comment on #463, 2026-10-10)". The Repro cites "the #630 test from the issue comment". Prior-art cites `iteration-v1/patch.diff` and says the review "reproduced" (7) and (8) against it. None of these is in the inputs, so neither this review nor Check can confirm that (7) and (8) are what that review asked for. Either attach the thread and the v1 review, or quote the load-bearing lines in the brief.
- [ ] **`Depends on: 723` points at a bundle that isn't built, and the brief treats its code as already on the base.** `dependency-state.json` says `"723": {"exists": true, "state": "PLANNED"}`. On the target there is no per-bundle base-build function: `integrate.py`'s top-level defs (`:99`–`:980`) contain none, and no file under `template/` mentions `723`. Yet the Falsifiability line says "with the production change reverted (#723's code stays, it is on the base) it loads and fails on assertions". The Scope says "a base built by #723's function", never naming that function. Against `main` as it stands (`Repo + branch target: eduralph/pdca-harness @ main`), Do would be calling an API that doesn't exist yet, and the red→green claim can't be tested. Options: gate this bundle on 723 reaching accepted/merged; or name the exact function and signature 723 must provide and the base this bundle builds on (723's branch versus `main`); or make the dependency a stack edge.
- [ ] **The brief's anchors are from a different tree than the target.** The target worktree HEAD is `d6057ebc8c9b`, but the brief keeps saying "On `489e5fb`". Several cited lines don't match the target:
- [ ] **Criterion (10) names suites that don't exist on the target, so as written it can't be checked.** These are absent from `template/tests/`:
- [ ] **Criteria (7) and (8) depend on behaviour that belongs to the unbuilt prerequisite, and don't say what "reports" means.** "the run reports the foreign ancestry naming `P` and `X`" and "the run reports the rewrite naming `P`" don't say where (stderr, exit code, a bundle record) or which message. Scope says the failure comes "with the error #723 raises". So whether (7) and (8) pass is decided by 723's error text and exit behaviour, which aren't fixed anywhere in this brief. Pin the observable: for example, the run exits non-zero before the wave, D's state stays unbuilt, and the error text contains `P` and `X`. Otherwise the test can be made to pass loosely.
- [ ] **The #655 rework is a second change bundled in.** Scope removes `_line_lacks_merge` (`flow.py:850`, called at `:792`) and `merged.merge_and_head` (`merged.py:149`), rewrites docstrings `merged.py:24` and `:188`, and flips the existing #655 hold tests (criterion 9). It is causally linked: once D isn't cut from the line, asking whether the line lacks P's merge is the wrong question. But it changes hold behaviour for every bundle ("by `merged.merged_into` alone for every bundle"), including bundles whose closure is empty. Meanwhile the brief defers every other doc and docstring change to #725, so deleting this code and editing these docstrings here is inconsistent with that deferral. The human should decide explicitly whether #655's flip belongs in this child or a sibling.
- [ ] size backstop — this slice is behaving oversized: patch is 151 KB (threshold 125 KB). Recommend answering `iterate-plan` at sign-off and authoring the split in the re-plan (`pdca split`), rather than `iterate-do`: a slice that is too big yields implementation-shaped findings every round, and splitting authors briefs, which is Plan's beat.
- [ ] T5 Judgment — Confirm merged-history and closed/rejected-work coverage by every affected file path before deciding this duplicates no prior solution — the brief lists flow.py history and a rejected attempt, but the supplied target has one synthetic base commit and no remotes, so the full check cannot be independently established; brief.md:27; review-prior-art.log:1.

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
- Iteration delta (if iterating): Slice is oversized (patch 151 KB > 125 KB backstop, 12 files) and keeps producing new implementation-level findings each round (round 1: 5 findings, auto-rebuilt; round 2: 2 new ones). Split it in re-plan (pdca split), e.g.: - (a) dependency-scoped stack bases for in-batch bundles (criteria 1-5, 10); - (b) resume/carry handling (criteria 6-8): keep finished patchless bundles in the dependency graph so transitive edges survive (reviewer's two repros: D COMPLETE missing A; false foreign-work STOPPING), and fix the #633/#695 rewrite messages to name the bundle base that took the head and the PR to rebuild (no PR is cut from the line any more); - (c) the #655 merged-prerequisite rework (remove _line_lacks_merge / merge_and_head, flip hold tests, criterion 9) as its own child. Decide in plan: dependents of a legacy `Stacks on` or `Onto branch` prerequisite now stop the whole run (built pre-fix) — support them as base members, hold the dependent (#725), or refuse at plan time. Refresh stale plan-advisory items (#723 now on base; anchors; criterion 10 suite list) and attach the #463/#630 thread lines that criteria 7-8 rest on.
- By / date: Eduard Ralph / 2026-10-15

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 6 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
