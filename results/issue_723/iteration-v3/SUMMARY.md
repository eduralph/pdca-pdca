# Result — issue 723 / fold-builds-a-per-bundle-base

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: `integrate.fold` can only fold onto the run's one line per target. It works out its destination itself from `integration_branch(cfg, base, batch)` (`template/src/pdca_harness/integrate.py:126`, used by `fold` at `:327` onward) and returns one entry per `(repo, base)` target. So there is no way to build a branch that carries exactly a chosen set of accepted bundles, which #463's dependency-scoped bases need (design: `results/issue_463/iteration-v1/brief.md`, Design §3).
- Success criterion: Real-git tests on the `StackFoldGit` fixture (`template/tests/test_integrate_stack_bases.py:123`), with branches published to the fixture's origin as that file's tests do, show the new per-bundle base build doing all of this:
  (1) **Exact contents.** Wave 0 = `A`, `Z` (unrelated, each with TWO commits on its own files). Fold the run's line with both. Then build `B`'s base from members `[A]`. The branch it pushes is on origin, contains every commit of `origin/main..fix/A`, contains no commit of `origin/main..fix/Z`, starts from `origin/main` as fetched, and the run's line branch and its recorded tip are unchanged by the build.
  (2) **Name.** The branch name is exactly `integration_branch(cfg, base, batch) + "-b" + _flatten_base(<id>)`, where `<id>` is the bundle id with any `issue_` prefix removed (so for `B` = `issue_12` on the run's line `pdca-integration/main-r<key>` it is `pdca-integration/main-r<key>-b12`). `-b` never appears in `_flatten_base`'s output (it emits only `-h` / `-s`), so the name decodes to one (base, batch, id). The test asserts the exact name, that it has no `/` after `pdca-integration/` (so it is never a ref-path prefix of, or under, the line or another base), and that ids `12`, `1-2`, `1/2` give three distinct names. Keep `integration_branch` and `_flatten_base` (`integrate.py:126`, `:154`) unchanged.
  (3) **Push rule.** Pinned on the push argv with the file's `_pushes` helper (`test_integrate_stack_bases.py:223`), as `test_a_continuing_fold_pushes_without_force` (`:275-283`) does, because `receive.denyNonFastForwards` accepts a forced create: creating the branch pushes with no `--force…` flag and no `+` refspec; re-building an existing one pushes with a `--force…` flag. Refused push: origin has `receive.denyNonFastForwards = true` and already holds the bundle's base branch at a commit that is not an ancestor of the new build (pushed there by the test); the build raises `integrate.IntegrationError` naming the branch and the remedy (delete it on origin, or allow force-pushes on `pdca-integration/*`).
  (4) **Every fold safeguard applies.** A member that doesn't merge cleanly raises `IntegrationError` naming both sides. A clash with the fetched base itself names `<remote>/<base>` and says to rebuild the member's branch on the new base, NOT "declare the conflict / re-order" (the wording at `integrate.py:842` stays for clashes between two bundles). A member whose branch is gone, or which brings in a revert of earlier work (#623 / 673's check), raises as the run's fold does.
  (5) **Rewritten carried member (#633).** Given a recorded head for a member, a member whose branch on origin no longer has that head raises `IntegrationError` naming the rewrite. Nothing is pushed.
  (6) **Foreign ancestry.** Given the published heads of the run's bundles that are NOT members, the build raises `IntegrationError` naming the excluded bundle and the member that brought it in when the result would hold a non-merge commit reachable from an excluded head but from neither the fetched base nor any member's head, the same shape as `foreign_commit` (`integrate.py:252-268`: `rev-list --no-merges <excluded head> --not <base> <member heads…>`; reuse it or its rule). Nothing is pushed. Red case: carried `P`'s branch was cut from an old line holding `X`; building `D`'s base from `[P]` with `X` excluded raises. Must-NOT-raise case: excluded `C` was cut from the run's line after wave 0, so `C`'s history holds member `A`'s commits; building `B`'s base from `[A]` with `C` excluded succeeds (A's commits are a member's, not foreign).
  (7) Every existing test in `template/tests/test_integrate_*.py` and `test_flow_*.py` stays green unchanged. This child changes no caller.
- Repo + branch target: eduralph/pdca-harness @ main (PRs target `main`). Base Do builds and the gate verifies on: the run's line `pdca-integration/main-r547f8028520f` at `489e5fb`, which already holds 672, 673, 693, 694, 695; the adopting run exports it as `$PDCA_VERIFY_BASE`. Every `path:line` in this brief is on `489e5fb`, not on `main` (`d6057eb`).
- Scope (one logical fix) / out of scope: `template/src/pdca_harness/integrate.py` only: a new sibling function `build_bundle_base(cfg, d, members, *, batch, carried, excluded) -> tuple[str, str]` (returns `(branch, pushed tip)`; `d` the destination bundle, `members` the ordered member bundle paths, `carried` member name → recorded head, `excluded` non-member name → published head). It is a sibling, not a `fold` keyword, so `fold`'s `folded_this_run` / `held_out` / `carried` / `wave` modes need no meaning here and `fold`'s body changes only where a shared helper is factored out of it. It shares `fold`'s merge path (`_merge_published`, `_take_in_base`, `_gone_branch`, the revert check). Do may add keywords but not drop these. It always starts fresh from the base as fetched. It runs under the same per-target `integ_lock` and worktree as the run's folds (`integrate.py:280`, `:538`) and resets the worktree as `fold` does. It returns its pushed tip without touching the run line's entry. Push rule and errors as in criteria (3)–(6). The test file. / out of scope: any caller (the flow does not use it yet; #724); `publish.py`, `flow.py`, `gates.py`, `worktree.py`; docs and the `integrate.py` module docstring's statement of the stack rule (#725); deleting per-bundle bases from origin (Open question 1 of the design: left for a follow-up).

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

Review the new per-bundle integration-base builder: publish exactly the fetched base plus selected bundles while preserving the run line and its safeguards.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The sibling API, destination naming, push policy, safeguards, and caller exclusion have concrete real-git acceptance cases; `brief.md:3`, `brief.md:17`, `target/template/tests/test_integrate_bundle_base.py:149`. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing the production change made all 23 tests execute and error at the absent entry point, rather than fail module import; `reviewer-red.log:14`, `reviewer-red.log:336`, `target/template/tests/test_integrate_bundle_base.py:66`. |
| C3 Change | PASS | The patch stays within the integration module and one new test file; the existing fold changes only by extracting its owner lookup, with no caller changes; `target/template/src/pdca_harness/integrate.py:581`, `patch.diff:303`. |
| C4 Verification (red→green) | PASS | Restoring the production patch independently changed the same 23 tests from red to green; this confirms the shipped cases, with the additional missed case recorded under C5; `reviewer-red.log:338`, `reviewer-green.log:3`, `gate-logs/C4-verify.log:10`. |
| C5 Causal adequacy | NEEDS-HUMAN [impl] | Correct ownership of member commits brought through topic merges and add a regression: an independent real-git probe rejects a valid A-only base as containing excluded C's work, so ordinary merge history can stop dependency builds; `target/template/src/pdca_harness/integrate.py:946`, `target/template/src/pdca_harness/integrate.py:949`, `reviewer-extra-probes.log:5`. |
| T1 Structure | PASS | The new builder uses the existing per-target lock, worktree, and production merge safeguards, preserving the established integration boundary; `target/template/src/pdca_harness/integrate.py:802`, `target/template/src/pdca_harness/integrate.py:839`. |
| T2 Shape | PASS | Independent docs lint, site rendering/link audit, and patch whitespace checks passed; both frozen docs gates also report clean results; `gate-logs/T2-docs.log:11`, `gate-logs/host-ci-docs.log:11`. |
| T3 Runtime | PASS | Independently ran all 480 integration/flow tests successfully; frozen evidence additionally records 24 root tests and 2,549 driver tests passing, with two driver skips; `reviewer-runtime.log:498`, `gate-logs/T3-suite.log:54`, `gate-logs/T3-suite.log:1874`. |
| T4 Contribution | N/A | Contribution artifacts are intentionally drafted after Check; the substantive contribution audit must run at publish, as the deferred gate records; `gate-logs/T4-contribution.log:10`. |
| T5 Judgment | NEEDS-HUMAN | Confirm path-based merged and closed/rejected prior art for both affected files before accepting novelty: the brief lists prior integration history, but the supplied target has only one snapshot commit and no remotes, so the closed/rejected-work check cannot be confirmed; `brief.md:22`, `reviewer-prior-art.log:1`. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether this standalone API and its ancestry-ownership contract are suitable for the later dependency-scoped flow after C5 is resolved; no caller is changed in this child, so passing API tests cannot establish end-to-end fitness; `brief.md:17`, `target/template/src/pdca_harness/integrate.py:723`. |

The C5 finding is a reproduced implementation defect. A publishes its own commit and merges an independently authored topic branch with `--no-ff`. The run folds A; C then branches from that run line and adds its own unrelated commit. Building B from `[A]`, with A's actual recorded head and C excluded, should succeed: C's own commit is absent from A, and every requested commit belongs to A. Instead the build reports A's topic commit as C's work and pushes nothing (`reviewer-extra-probes.log:1`).

`_foreign_work` subtracts other heads only when those heads lie on the excluded branch's first-parent chain (`target/template/src/pdca_harness/integrate.py:947`). Here A entered C's history through the run's merge, so that subtraction does not apply. The remaining filter recognizes other bundles' first-parent chains only; A's topic commit is off A's first-parent chain and is consequently misattributed to C (`target/template/src/pdca_harness/integrate.py:940`, `target/template/src/pdca_harness/integrate.py:949`). The shipped tests cover an excluded bundle's topic merge and a member's ordinary commits separately, but miss this combination (`target/template/tests/test_integrate_bundle_base.py:308`, `target/template/tests/test_integrate_bundle_base.py:330`). Preserve the existing contamination refusals while correcting this case.

Re-run the independent probe from this review directory:

```sh
TMPDIR="$PWD/reviewer-tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/target/template/src" python3 reviewer-extra-probes.py
```

Evidence boundaries: the disposable target matches the supplied patch (`git apply --reverse --check` passed), and the patch was restored after the red leg. Python and real git were exercised without tool substitutions. The instance-scoped gate wrappers are not supplied here; their frozen logs were read, and available underlying tests, docs tools, and the production-import scanner were run directly. The full root/driver totals above are frozen-log evidence, not an independent full-suite claim. The production-import scanner passed, but its import heuristic does not discharge C5. No optional-capability/load-time guard smell was found. The supplied target contains only the generic `template/docs/INTEGRATION.md.jinja`, whose human-only list is an unfilled placeholder, rather than a populated instance ruleset.

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — issue_723 (build_bundle_base)

Gates: C4 red→green (23 errors pre-fix, all pass post-fix), T3 suite OK (2549 tests). No gate disagreement found in gate-logs/.

## Correctness

- NEEDS-HUMAN [human] — `template/src/pdca_harness/integrate.py:930-932` (`_foreign_work` docstring) admits a case where excluded work gets through with no error. If an excluded branch X is fast-forwarded onto the head of a branch P that was cut from X, X's first-parent chain now runs through P's head. So X's earlier commits (for example `x1`) count as P's work, and building a base from `[P]` with X excluded pushes `x1` without refusing. The brief's invariant says a build is "refused, never silently widened". This attribution rule (first-parent chains, at `:940-949`) is not the rule the brief asked for. That rule was `foreign_commit`'s: `rev-list --no-merges <excluded> --not <base> <member heads…>`. The builder moved to chains to fix the round-1/2 false refusals. A human should decide whether this known false negative is acceptable, or whether the fast-forward case must fail closed (for example: refuse when an excluded head's chain contains a member's head that the member's branch no longer holds). No test covers it either way.
- `template/src/pdca_harness/integrate.py:820-829`: an excluded entry with an empty or missing head (`'(none given)'`) is a hard refusal, so a caller can never pass a run bundle that has no published branch (patchless or unpublished). That is consistent with the docstring, but #724's caller must filter those out first. Noting it for the caller; this is not a defect in the diff.
- `template/src/pdca_harness/integrate.py:830` and `:859-860`: the lease is pinned to the tip read right after the fetch, so a concurrent writer is caught (`--force-with-lease=<branch>:<existing>`), and creating the branch uses a plain push. Correct as written. The refused-push message at `:862-869` merges two causes, a protected branch and a moved branch, into one sentence. That is fine, since the remedy covers both.
- Refusals after the merge loop (foreign work at `:850-858`, a refused push at `:861`) leave the local `pdca-integration/…-b<id>` ref pointing at the unpushed build. The next build's `checkout -B … <base_ref>` (`:832`) and `_reset_tree` (`:831`) overwrite it, so nothing stale is reused. Same pattern as `fold`. No action needed.

## Tests

- `template/tests/test_integrate_bundle_base.py:195-211`: the create-without-force check reads the push argv only. No case runs a *create* against an origin with `receive.denyNonFastForwards = true` to show it succeeds. The argv check is what the brief asked for in (3), so this is fine. Mentioned only because the docstring at `integrate.py:763-765` claims the denyNonFastForwards behavior.
- The revert-check case (`test_integrate_bundle_base.py`, `test_a_member_that_brings_a_revert_of_an_earlier_members_work_stops_the_build`) now actually triggers the #623/#673 check and asserts the same refusal from `fold`. This fixes the round-1 finding.

## Reuse / simplification

- `template/src/pdca_harness/integrate.py:703-714` (`_owners`) is a clean extraction from `fold` (old body at `fold`'s `owners` loop). `fold`'s behavior is unchanged.
- `template/src/pdca_harness/integrate.py:873-904` (`_member_clash`): the `head is None` branch (`:886-887`) can't be reached, because `_Conflict` is only raised when a real head is merged (`_merge_published`, `:1101`). It's harmless, so leave it or drop it.
- `template/src/pdca_harness/integrate.py:946`: `theirs` rebuilds a union of every other chain once per excluded bundle (quadratic in the number of heads). Batches are small, so this costs nothing in practice. No change suggested.

Nothing else found: the shared merge path (`_merge_published` → `_gone_branch` / `_take_in_base` / revert check), the lock (`integ_lock`, `:802`), the worktree (`_prepare_worktree`, `:808`) and the name (`bundle_base_branch`, `:145`, which leaves `integration_branch` and `_flatten_base` untouched) are reused as the brief requires.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] C5 Causal adequacy — Correct ownership of member commits brought through topic merges and add a regression: an independent real-git probe rejects a valid A-only base as containing excluded C's work, so ordinary merge history can stop dependency builds; `target/template/src/pdca_harness/integrate.py:946`, `target/template/src/pdca_harness/integrate.py:949`, `reviewer-extra-probes.log:5`.
- [ ] T5 Judgment — Confirm path-based merged and closed/rejected prior art for both affected files before accepting novelty: the brief lists prior integration history, but the supplied target has only one snapshot commit and no remotes, so the closed/rejected-work check cannot be confirmed; `brief.md:22`, `reviewer-prior-art.log:1`.
- [ ] Validation — fitness-to-purpose — Decide whether this standalone API and its ancestry-ownership contract are suitable for the later dependency-scoped flow after C5 is resolved; no caller is changed in this child, so passing API tests cannot establish end-to-end fitness; `brief.md:17`, `target/template/src/pdca_harness/integrate.py:723`.
- [ ] `template/src/pdca_harness/integrate.py:930-932` (`_foreign_work` docstring) admits a case where excluded work gets through with no error. If an excluded branch X is fast-forwarded onto the head of a branch P that was cut from X, X's first-parent chain now runs through P's head. So X's earlier commits (for example `x1`) count as P's work, and building a base from `[P]` with X excluded pushes `x1` without refusing. The brief's invariant says a build is "refused, never silently widened". This attribution rule (first-parent chains, at `:940-949`) is not the rule the brief asked for. That rule was `foreign_commit`'s: `rev-list --no-merges <excluded> --not <base> <member heads…>`. The builder moved to chains to fix the round-1/2 false refusals. A human should decide whether this known false negative is acceptable, or whether the fast-forward case must fail closed (for example: refuse when an excluded head's chain contains a member's head that the member's branch no longer holds). No test covers it either way.
- [ ] **Thread record not checkable.** The sandbox has only `brief.md`. There is no `notes.json`, no `sources/` and no `dependency-state.json` (Glob of cwd). So I could not check the problem statement against the tracker thread: #463 "Done when", #630's comment, or the 2026-10-15 sign-off carry-forward that the brief cites as the source for (5)/(6). The prerequisites 672/673/693/694/695 could not be resolved either. Either the bundle was handed over incomplete, or the brief relies on records the reviewer cannot see.
- [ ] **The target lacks the prerequisites, and the brief's citations point at a tree that doesn't exist on `main`.** The target is `eduralph/pdca-harness @ main`. In `$PDCA_TARGET`:
- [ ] **Criterion (6) as worded refuses legitimate builds.** It says to raise if "any commit of `<base>..<excluded head>` would end up on the result". In this harness, later-wave bundles are cut from the run's line (module docstring `integrate.py:12-16`; `test_integrate_stack_bases.py:268` cuts B from `origin/{LINE}`). So an excluded later-wave bundle's `<base>..<head>` contains every earlier member's commits. Take criterion (1)'s own scenario and add any non-member C cut from the line after wave 0. Building B's base from `[A]` with C excluded would raise, because A's commits are in `base..C`. The check needs to be "commits reachable from the excluded head but not from the base or any member head". That is exactly the shape of the existing `foreign_commit` (`integrate.py:225-236`, `rev-list --no-merges tip --not base_ref *heads`). The brief doesn't mention that it exists. Add a red→green case where an excluded bundle stacks on a member and must NOT raise.
- [ ] **Criterion (3)'s "plain push" half can't be falsified as stated.** It proves "creating the branch is a plain push" by having "an origin with `receive.denyNonFastForwards = true` accept it". Creating a ref has no old value, so a `--force` create is accepted too. The existing suite says so: `test_integrate_stack_bases.py:276-277` ("receive.denyNonFastForwards ACCEPTS a forced push that happens to fast-forward, so the flag itself is what this pins"), and it checks the argv with `self._pushes(...)` (`:281-283`). The criterion should pin the push flags (no `--force` on create, `--force` on rebuild) with that helper. As written, a force-always implementation passes. The "refused push" leg also needs a stated way to provoke the refusal (e.g. `receive.denyNonFastForwards` plus a pre-existing divergent branch).
- [ ] **A hidden design choice is pushed onto Do.** The scope says "a new `fold` keyword or a sibling function … Do picks". These differ in review surface. A `fold` keyword touches `fold`'s ~260-line body (`integrate.py:300-566`), which already has `folded_this_run`, `carried`, `held_out` and `wave` interactions. All of these would need a defined meaning under the new mode: is `held_out` allowed? Is `folded_this_run` ignored? Criterion (7) only catches regressions in existing tests, not undefined combinations. Either pick one, or list which existing keywords are rejected or ignored in per-bundle mode.
- [ ] **Criterion (2) leaves the name format open, and the fallback sits on an unverifiable base.** "Line name plus a fixed suffix carrying `B`'s id" is checkable for prefix-freeness only once the format is fixed: does a suffix separator like `-b<id>` collide with the `-r<key>` / `-h` / `-s` escapes (`integrate.py:107-115`, `:128-135`)? The brief should state the format so the "never a path prefix / injective" test has a concrete oracle. Separately, the brief points Do at `iteration-v1/patch.diff` as reference, but that diff was cut against a base Do won't have (see the finding on the target above).
- [ ] C1 Spec — Resolve criterion (6)’s ancestry rule versus its required rejection example — subtracting all member heads also subtracts X inherited by P, whereas the implementation subtracts only heads ancestral to the excluded head; these define different acceptance rules (`brief.md:9`; `target/template/src/pdca_harness/integrate.py:879`).
- [ ] T5 Judgment — Confirm merged and closed/rejected prior art by affected file path — the brief lists merged history and an earlier attempt, but this target has only one synthetic base commit, no remotes, and no closed/rejected-work evidence (`brief.md:22`; `target/template/src/pdca_harness/integrate.py:717`).
- [ ] T5 Judgment — Confirm prior art by both affected file paths across merged history and closed/rejected work — the supplied target has only a synthetic base commit and no remote, while the brief lists merged examples without closed/rejected search evidence (`reviewer-target.log:1`; `brief.md:22`).

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
- Iteration delta (if iterating): Auto-iterate (round 3): rebuilding for the implementation-level findings — C5 Causal adequacy — Correct ownership of member commits brought through topic merges and add a regression: an independent real-git probe rejects a valid A-only base as containing excluded C's work, so ordinary merge history can stop dependency builds; `target/template/src/pdca_harness/integrate.py:946`, `target/template/src/pdca_harness/integrate.py:949`, `reviewer-extra-probes.log:5`.. Deferred, not addressed here: 8 finding(s) that need human judgment, held in deferred-findings.json for the human at handover — not build work
- By / date: auto-iterate / 2026-10-15

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 6 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
