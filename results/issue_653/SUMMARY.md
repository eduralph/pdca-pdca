# Result — issue 653 / carry-holds-when-branch-tip-is-not-the-judged-head

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: The #646 pre-wave carry judges a finished prerequisite clean using its PR's `headRefOid` (`merged.pr_state`, `template/src/pdca_harness/merged.py:146-166`; `flow._finished_head`, `template/src/pdca_harness/flow.py:836-857`, which returns that head). It then folds through `integrate.fold` (`flow._fold_lines`, `flow.py:931-933`), which merges the branch's CURRENT tip (`integrate._merge_published` resolves `origin/<branch>`, `template/src/pdca_harness/integrate.py:461-475`), not the head that was judged. If a commit was pushed to the branch after the PR was approved or merged (a MERGED PR whose branch was not deleted and got another push; or an OPEN PR whose head moved and the `gh` answer is stale relative to the carry's fetch), that commit is carried onto the line and every dependent builds on it, though nobody reviewed it. Nothing compares the two.
- Success criterion: With the patch, driving `flow._drive_and_act` on the real-git fixture of `template/tests/test_flow_resume_stack_prereqs.py` (`ResumeStackPrereqs`):
  (1) **Merged, then pushed to.** `P` finished, its branch merged into `main` (`self.fx._merge_pr("P")`), PR state MERGED with `headRefOid` = the merged head. Then one more commit (adding `extra.txt`) is pushed onto `fix/P`, which still exists. `D` in the drive set with `Depends on: P`, and an unrelated `U`. Batch `["P", "D", "U"]`. `P` is not carried. `D` is never built, stays PLANNED, and ONE stderr line names `issue_P` and `issue_D` and says the branch tip is not the PR head that was judged (both SHAs shortened), with the new hint's advice (see Scope; the line contains `reset` or `delete` and the judged head's short SHA). No line on origin contains the extra commit. `U` is built (the run goes on).
  (2) **Open, head moved since the read.** `P` finished with its PR OPEN, but the `gh` answer reports a head older than `fix/P`'s tip (the stub returns the commit before the tip). `D` is held the same way, and the extra commit is on no line.
  (3) **Unchanged.** Every existing test in the file passes. When the branch tip IS the reported head (the fixture's default `gh` stub answers with the tip), a clean `P` is carried exactly as today (`test_a_clean_finished_prerequisite_is_on_the_line_its_dependent_builds_on`, `:176`).
  Pre-fix, in (1) and (2) `D` is built on a line that contains the extra commit. That is the RED.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: Make the pre-wave carry treat a finished prerequisite whose branch tip (as read in the carry's fetched checkout, `integrate.carry_view`) differs from the PR head it judged as not clean. Any tip other than the judged head is held, including a merged branch that only took the base in afterwards (GitHub's "Update branch" on a MERGED PR): that is intended fail-closed, since telling "only base commits" apart is a judgment the carry does not make. The not-clean result uses a NEW `_CARRY_HINTS` entry (`flow.py:858-864`), e.g. "reset or delete {name}'s branch to {head} (the PR head that was judged), or open a PR for the commit(s) after it, then re-issue", and the `.format(...)` call (`flow.py:951-952`) gains the judged head (and tip, for the reason). / out of scope: folding the judged head instead of the tip (the alternative the human declined); closing the race in which a push lands AFTER the carry's own read and BEFORE the fold's re-fetch (`_prepare_worktree` → `_fetch`, `integrate.py:623`; the fold re-resolves `origin/<branch>`, `integrate.py:468`). That window is seconds wide and would need the expected head passed into the fold; it is a known residual, not claimed by this fix; the in-run fold's handling of fixups and rewrites (#633); how PR state is read (`merged.pr_state`); a branch that is gone after its PR merged (unchanged: judged by the merged head as today, `_finished_head` + `integrate._gone_branch`).

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

Review issue #653: hold dependents when a finished prerequisite’s fetched branch tip differs from the PR head judged clean, while allowing unrelated work to continue.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The observable hold, diagnostic, isolation and unchanged-clean-carry requirements are falsifiable; the later fetch race is explicitly excluded (brief.md:13; brief.md:26; target/docs/07-crosscutting.md:686). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only production changes makes both new cases fail because issue_D is built despite the mismatch; the other 13 tests pass (reviewer-red.log:18; target/template/tests/test_flow_resume_stack_prereqs.py:389). |
| C3 Change | PASS | The three-file patch stays within the pre-wave carry judgment, its recovery message, documentation and regression coverage; it preserves the existing fold contract (target/template/src/pdca_harness/flow.py:860; target/template/src/pdca_harness/integrate.py:461). |
| C4 Verification (red→green) | PASS | Restoring the production fix changes the two assertion failures to all 15 passing, including clean carry; the tests verify held dependents, continued unrelated work and no line containing the extra commit (reviewer-green.log:18; target/template/tests/test_flow_resume_stack_prereqs.py:382). |
| C5 Causal adequacy | PASS | Comparing the actual published ref with the judged head directly enforces the chosen invariant at the fetched snapshot; this is no optional-capability or load-time workaround, and the real-git fixture can exhibit the forbidden carry (target/template/src/pdca_harness/flow.py:860; target/template/tests/test_flow_resume_stack_prereqs.py:128). |
| T1 Structure | PASS | Existing published-ref resolution and held-prerequisite reporting remain the shared integration boundaries; no parallel merge implementation or new dependency is introduced (target/template/src/pdca_harness/integrate.py:139; target/template/src/pdca_harness/flow.py:957). |
| T2 Shape | PASS | Independent diff whitespace check, docs lint and 22-page site render/link audit pass, consistent with both frozen documentation gates (target/docs/07-crosscutting.md:686; gate-logs/T2-docs.log:11; gate-logs/host-ci-docs.log:11). |
| T3 Runtime | PASS | Independent offline suite passes 2,371 tests with two skips; frozen evidence additionally records 24 passing root render/update tests, which the local interpreter cannot rerun with copier (reviewer-suite.log:1797; gate-logs/T3-suite.log:54; reviewer-root-suite.log:7). |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; their substantive audit is deferred to the required publish rerun (gate-logs/T4-contribution.log:10). |
| T5 Judgment | NEEDS-HUMAN | Confirm merged and closed/rejected prior art by all three affected paths — the brief records flow.py history but not the changed test/docs paths, and this isolated one-commit target cannot independently establish that history (brief.md:31; target/template/tests/test_flow_resume_stack_prereqs.py:389; target/docs/07-crosscutting.md:686). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Accept the scoped protection and recovery guidance for real operations — mismatches hold dependents at the carry snapshot, but a push between that read and the fold’s refetch remains possible, as explicitly accepted at Plan (brief.md:26; target/template/src/pdca_harness/integrate.py:468; target/template/src/pdca_harness/flow.py:873). |

Independent verification used the disposable target supplied in this sandbox. I stashed only `template/src/pdca_harness/flow.py`, kept the new tests, ran `PYTHONPATH=src python3 -m unittest discover -s tests -p test_flow_resume_stack_prereqs.py -v` from `target/template`, then popped the stash and repeated. The red failures are behavioral assertions, not import errors. The restored target’s complete diff matches `patch.diff` exactly. All temporary test files were directed beneath this review directory.

The full offline rerun used `PYTHONPATH=src python3 -m unittest discover -s tests`. Documentation checks used `python3 docs/publishing/tools/lint_docs.py` and `python3 docs/publishing/tools/render_site.py --check --out /tmp/pdca-review-6eomexob/reviewer-site` from the target root. Both passed; `git diff --check` was also clean.

The local root-suite attempt exited 77 because `/usr/bin/python3` cannot import copier; its skipped render/update cases are not independent verification. The frozen T3 log explicitly shows those cases running successfully, so this is a reviewer-host limitation, not an undischarged gate dependency or patch defect. The instance-scoped wrapper commands were adjudicated from their captured logs. In particular, the C5 scanner performed no assertion because no new test file was added (`gate-logs/C5-prod-path.log:10`); C5 above rests on the inspected production call path and independent red→green execution instead. The gh stub supplies PR metadata while real git performs the topology changes and merges; the reproduced red failures demonstrate that this fixture can exhibit the forbidden outcome.

Prior-art investigation: `git log --all --oneline -- template/src/pdca_harness/flow.py template/tests/test_flow_resume_stack_prereqs.py docs/07-crosscutting.md` returns only `0531c77 pre-fix base b5f5c29b31d93bb2e41a4692bc56affd1cfd72bb`; `git remote -v` returns nothing. No other checkout was consulted. The target is usable and matches the supplied patch; its intentionally flattened history limits the prior-art inquiry. The available integration template’s human-only list is unfilled (`target/template/docs/INTEGRATION.md.jinja:80`), so it supplies no additional enumerated decision.

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — issue 653 (carry-holds-when-branch-tip-is-not-the-judged-head)

I found no correctness bug that needs a human. The patch does what the brief asks. The notes below are small cleanups. None is tagged NEEDS-HUMAN.

## Correctness

- `template/src/pdca_harness/flow.py:860-863` — The new check reads the same ref the fold will merge. `ref` comes from `integrate._fold_candidates` → `_published_ref` (`template/src/pdca_harness/integrate.py:139-158`), and the fold resolves that same `ref` (`integrate.py:467-468`). It also runs in the checkout `carry_view` just fetched (`integrate.py:185-193`). Both values are full SHAs (`rev-parse --verify` and `gh`'s `headRefOid`), so `!=` compares like with like. A gone branch (`_rev` → None) skips the check and keeps today's `_gone_branch` path, as the brief says it should. The check comes after the MERGED-head-on-base check, so in test (1) the new branch is what fires, not the older "edge" reason. A held P is left out of `heads`, so `foreign_commit` (`flow.py:933`) never counts its extra commit as accounted for. No problem found.
- `template/src/pdca_harness/flow.py:960` — `hint.partition(":")` is safe for the existing hints (`open`, `edge`, `line` have no colon, so `head` becomes `""` and is unused). Every exception path that builds `why` (`flow.py:928, 931, 935-936, 948, 950`) uses plain hint keys, so nothing hits a `KeyError`.
- Tests (`template/tests/test_flow_resume_stack_prereqs.py:374-404`): both new tests are red without the production hunks and green with them (`gate-logs/C4-verify.log`: before the fix, `issue_D` was built on a line holding the carried P). `_lines_with` checks every non-`fix/*` branch on origin for the extra commit, which covers the "no line holds it" claim directly. `self.heads.get(iid) or …` in `_gh_stub` (`:101-102`) leaves every existing test on the old tip-as-head answer, so criterion (3) holds (T3 suite passes).

## Reuse / simplification

- `template/src/pdca_harness/flow.py:863` and `:960` — The judged head travels to the formatter packed into the hint string (`"tip:<sha>"`) and gets split back out with `partition`. That is a small hidden format inside a dict key. A simpler option: put the short head in the `reason` text, which already holds it (`... ({head[:12]})`), and word the `tip` hint without `{head}`. Or carry a third tuple field. It works as written, so this is optional.
- `template/src/pdca_harness/flow.py:873-874` — The hint reads "reset or delete {name}'s branch to {head}". "Delete … to {head}" does not parse. "reset {name}'s branch to {head} or delete it" says the same thing clearly. The test checks only for `reset`/`delete`/the short SHA, so rewording is safe. `docs/07-crosscutting.md:690` has the same wording.

## Scope

The new code adds one `git rev-parse` per finished prerequisite, which is negligible. It touches nothing outside what the brief scopes. The post-read/pre-fold race is left open, as the brief says it would be.
<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — Confirm merged and closed/rejected prior art by all three affected paths — the brief records flow.py history but not the changed test/docs paths, and this isolated one-commit target cannot independently establish that history (brief.md:31; target/template/tests/test_flow_resume_stack_prereqs.py:389; target/docs/07-crosscutting.md:686).
- [x] Validation — fitness-to-purpose — Accept the scoped protection and recovery guidance for real operations — mismatches hold dependents at the carry snapshot, but a push between that read and the fold’s refetch remains possible, as explicitly accepted at Plan (brief.md:26; target/template/src/pdca_harness/integrate.py:468; target/template/src/pdca_harness/flow.py:873).
- [x] **The planned comparison does not close the race that the Defect and Invariant claim to close.** The brief's Defect names "a push between the `gh` read and the fold's fetch". Its Invariant says a prerequisite "is carried only when the commit the fold would merge is the PR head judged clean". But Citations tell Do to compare in the `carry_view` checkout (`integrate.py:185-193`). The fold then fetches again before it merges: `_fold_lines` → `fold` → `_prepare_worktree` → `_fetch` (`integrate.py:623`). It then resolves `origin/<branch>` again in that fresh state (`integrate.py:468`). In `_carry_finished`, the `gh` read (`flow.py:914`) comes after the `carry_view` fetch (`flow.py:910`), so a push in that window makes head ≠ tip and is held. A push that lands after the `gh` read and before the fold's fetch at `integrate.py:623` is still merged without review. The fix only narrows that window. Since folding the judged SHA was declined, the brief needs one of two changes. Option 1: drop the race from the Defect/Invariant and claim only the persistent "merged then pushed" / stale-head cases. Option 2: require the check where the fold resolves `head` (`_merge_published`, `integrate.py:468`), for example by passing the expected head into the fold. Option 2 adds production surface beyond `flow.py`, and Scope does not mention it today. Criterion (2) as written cannot tell these two designs apart, because the stub's stale head is fixed before either fetch.
- [x] **"Builds on 652" is declared only as a conflict, not as a dependency, and the base is main as it stands before 652.** The Ordering note says "Separate waves: 652 first, and 653 builds on its result", and that 652 "edits the same carry judgment (`_finished_head` / `_carry_finished`, `flow.py:836-956`) and appends to the same test file". The brief declares only `Conflicts with: 652`. It has no `Depends on` / `Stacks on`, and `Repo + branch target: … @ main` is verified at `b5f5c29`, which does not include 652. There is no `dependency-state.json` in this bundle, so I could not confirm that bundle 652 exists or check its state. If 653 really must build on 652's result, the target must be wherever 652 lands. Otherwise every `flow.py:8xx-9xx` citation Do is told to match will have drifted, or the fold will conflict. Either declare the dependency, or reword the note to "order only" if 652 changes no line this fix touches.
- [x] **The hint is specified, but the criterion does not check it, and the existing hint mechanism cannot produce it.** Scope says the not-clean result carries "a reason and hint naming both commits". Hints are fixed templates keyed `open` / `edge` / `line`, filled only with `name`/`line`/`iid` (`flow.py:860-866`, `flow.py:951-952`), so a hint cannot name both commits without new plumbing. Also, none of the existing advice fits a MERGED PR whose branch got an extra push. `open` says "get {name}'s PR open … then re-issue", and that does not resolve this case. Success criterion (1) checks only that the stderr line names `issue_P` and `issue_D`, the "tip is not the judged head" reason, and both short SHAs. The hint text is left to Do and is not verified. The brief should name the remedy, for example "delete or reset `fix/P` to `<head>`, or open a PR for the extra commit, then re-issue", and say whether that needs a new `_CARRY_HINTS` key. If the hint is not meant to name the commits, Scope should drop "naming both commits" from the hint.
- [x] **Any tip ≠ head is held, including a merged branch that only took the base back in.** The fixture has `_update_branch` ("GitHub's 'Update branch': merge the base into `fix/<iid>`", `test_integrate_stack_bases.py:191-196`). If a MERGED PR's branch is updated from `main` afterwards, tip ≠ `headRefOid`, but the extra commits are only base commits plus a merge, so there is no unreviewed content. Under the brief's rule ("Any other commit is unreviewed work"), those dependents are held. That may be the intended fail-closed behaviour. If so, say so in Scope so Check does not raise it as a regression. If not, the comparison should be "tip has no non-merge commits outside `head` + `base_ref`", which is the shape of `foreign_commit` (`integrate.py:196-203`).

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: merged-wider
- Iteration delta (if iterating):
- By / date: Eduard Ralph / 2026-10-14

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 4 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
