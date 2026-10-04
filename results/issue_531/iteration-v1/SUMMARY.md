# Result — issue 531 / merge-mode-stale-base-merge

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: In `[driver].wave_mode = "merge"`, a wave's PRs are merged back-to-back and
  nothing verifies the combination. `merge_wave` merges each bundle in turn
  (`template/src/pdca_harness/merge.py:75-84`); `_merge_one` readies the PR, reads its check
  rollup (`merge.py:259-284`, `_wait_for_green`) and runs `gh pr merge`
  (`merge.py:228`, `:287`). The rollup it reads belongs to the PR's head commit, which was
  tested against the base as it stood BEFORE this wave's earlier PRs merged. Nothing reads
  whether the PR is behind its base and nothing brings it up to date — the module issues only
  `gh pr ready`, `gh pr checks`, `gh pr merge` (and `gh pr ready --undo`); there is no
  `update-branch` and no behind/stale read anywhere in `merge.py` or `flow.py`. So whether a
  stale PR merges is decided by the host's `required_status_checks.strict`, which the harness
  neither reads nor documents:
  wave 0 = {A, B}, independent; A and B are each green against `main@X`; the driver merges A
  (`main@Y`); B's rollup still describes `X`; with `strict: false` GitHub merges B
  (`main@Z`). If A and B conflict semantically (no shared file needed), `main@Z` is red and
  wave 1 builds on it. With `strict: true` the second merge is refused instead, the wave stops
  with one PR merged and the rest untouched, and every later wave is lost (the shape of #462).
  `_audit_wave_overlap` (`flow.py:745-760`) sees only file overlap and is advisory.
  The optional `regate_between_waves` re-gate exists only on the stack branch of the wave
  boundary (`flow.py:1973`, `:2015-2023`); the merge branch (`flow.py:1968-1972`) never
  re-gates, while the knob's comment says "in merge mode the PR's own CI is the merge-boundary
  check" (`template/pdca.toml.jinja:166-170`) — which is exactly what `strict: false` does not
  deliver.
- Success criterion: With the patch, under `merge_requires = "all"` (the default) merge
  mode never merges a PR whose head was behind its base at the driver's last read before
  `gh pr merge`, and never merges a head other than the one whose rollup it read green. For every
  PR `merge_wave` merges: (1) the driver reads whether the PR is behind its base after the
  ready-mark; (2) if behind (an earlier member of the same wave just merged, or the base moved
  for any other reason), it brings the PR up to date with a merge-commit update of the PR's own
  branch (`gh pr update-branch` without `--rebase`, whatever `merge_method` is), then waits for
  the NEW head's rollup under the same bounded wait (`merge_wait_secs`) and the same fail-closed
  rules, and confirms it (#582); (3) it merges pinned to the head SHA whose rollup it read green
  (e.g. `gh pr merge --match-head-commit <sha>`), so a head that changed after the green read is
  refused by the host instead of merged. A multi-member wave therefore completes on a host with
  `strict: true` instead of stopping after its first merge. A PR that cannot be brought up to
  date (a conflict with the base, the update refused), whose updated head is not green, or whose
  pinned merge is refused stops the run, readiness undone, as every other refusal in
  `_merge_one` does today. Under `merge_requires = "required"` nothing changes: no behind read,
  no update, no rollup read — that setting means "trust the host's protection" (see Scope).
  Demonstrated in `template/tests/test_merge.py`:
  (a) a two-member wave where the second PR reads as behind only after the first PR's merge:
  post-fix the second PR is updated, its new head's rollup is read green, and only then
  `gh pr merge` runs on it, pinned to the new head's SHA; pre-fix `gh pr merge` is called on the
  second PR straight after the first, with no update — the test fails;
  (b) the head changes between the green read and the merge (the fake reports a different head
  SHA, or refuses the pinned merge): the driver does not merge that head and stops, readiness
  undone — pre-fix the merge goes through unpinned;
  (c) under `merge_requires = "required"`, the call log is exactly today's (no update, no
  behind read).
  Existing `test_merge.py` cases (a single up-to-date PR merges exactly as before apart from the
  added behind/head read and the pin; red/pending/empty rollups refuse; dry-run merges nothing)
  keep passing.
  **Accepted gap (stated, not tested):** a client-side driver cannot stop the base moving
  between its last read and the host executing the merge. On `strict: true` the host refuses
  that merge (the run stops, fail-closed); on `strict: false` that narrow window remains. The
  config comment recommends `strict: true` for merge mode for this reason.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: Make merge mode's merges land only verified combinations, per the invariant: a PR
  whose head lacks the current base tip is brought up to date with the base and re-verified
  (same bounded, confirmed, fail-closed rollup rules) before it merges, and the merge itself
  cannot land a head other than the one verified. This is what makes a host with `strict: true`
  usable for multi-member waves and a host with `strict: false` safe. The issue's suggested
  direction is GitHub's `gh pr update-branch` followed by the existing rollup wait; Do may use
  it or an equivalent that keeps the PR's own branch as the thing that merges. Update the
  merge-mode config comments so they describe what the driver now does, and state honestly that
  `regate_between_waves` has no effect in merge mode (it applies to the stack fold only).
  Update `template/docs/fork-discipline.md.jinja:51-60` (required, not optional) to describe
  the new sequence: ready → behind read → update if behind → bounded rollup wait on the new head
  → merge pinned to that head.
  **`merge_requires = "required"` is unchanged on purpose:** that setting already means "skip
  the driver's rollup gate and trust the host's branch protection" (`merge.py:259`,
  `pdca.toml.jinja:145`). An update there would be followed by an immediate merge on pending
  checks, so the fix does not add one. Its config comment must say plainly that it keeps the
  stale-base behaviour: with `strict: false` a stale PR can merge, with `strict: true` a
  multi-member wave stops after its first merge; use `"all"` for merge mode.
  **What sign-off covered changes, and the docs must say so:** after an update the head that
  merges is a merge commit of the reviewed PR branch with the newer base. Check reviewed
  `patch.diff`, not that combination; the combination is verified by the PR's own CI (the
  green rollup the driver reads), not by the reviewer. Say this in the fork-discipline text.
  The update is always a merge-commit update, never a rebase (a rebase rewrites the reviewed
  commits), regardless of `merge_method`; `merge_method` still governs only the final merge.
  / out of scope: running `regate_between_waves` in merge mode (detect-after-landing backstop —
  a separate change if wanted); reading the host's `required_status_checks.strict` and refusing
  merge mode on it; any change to `merge_requires = "required"` behaviour (documented only);
  closing the base-moved-after-last-read race on `strict: false` (accepted gap, see criterion);
  atomic merge groups (#412); retargeting a wrong-based PR (#500); stack mode
  (#591, #616); `merge_method = "rebase"`/`"squash"` specifics beyond keeping them working.

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

Review issue #531: prevent merge-mode waves from merging stale-base or unverified PR heads by updating behind branches, rechecking CI, and pinning the merge.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The last-read freshness guarantee, unchanged host-trusting mode, and accepted subsequent base-movement window define a testable scope; target/template/pdca.toml.jinja:128, target/template/pdca.toml.jinja:160. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only the production fix leaves 11 of 40 tests failing, including the second PR remaining stale after the first merges; target/template/tests/test_merge.py:822; reviewer-red.log:30. |
| C3 Change | PASS | Stale combinations and changed heads are refused before landing, with readiness undone; the required-mode call sequence remains unchanged in the passing regression; target/template/src/pdca_harness/merge.py:333, target/template/src/pdca_harness/merge.py:380, target/template/tests/test_merge.py:904. |
| C4 Verification (red→green) | PASS | Restoring the production stash changes the same 40-test run from 11 failures to all passing, independently confirming the offline contract; target/template/tests/test_merge.py:822, reviewer-red.log:163, reviewer-green.log:3. |
| C5 Causal adequacy | PASS | Updating the stale combination before verification addresses the cause, and the stateful test invokes production merge_wave; no optional-capability/load-time symptom guard was added; target/template/src/pdca_harness/merge.py:339, target/template/tests/test_merge.py:816. |
| T1 Structure | PASS | The existing bounded rollup wait and readiness rollback remain the shared control points, avoiding divergent verification behavior; target/template/src/pdca_harness/merge.py:319, target/template/src/pdca_harness/merge.py:356. |
| T2 Shape | PASS | Independent docs lint, 22-page render/link audit, and git diff --check pass; user-facing guidance explains CI's responsibility for the updated combination; target/template/docs/fork-discipline.md.jinja:65; gate-logs/T2-docs.log:11, gate-logs/host-ci-docs.log:10. |
| T3 Runtime | PASS | Independent offline suite ran 2,305 tests successfully with two skips; the frozen root-suite log separately shows 24 passing render/update tests, which this interpreter cannot rerun because copier is absent; reviewer-suite.log:1796, gate-logs/T3-suite.log:38, gate-logs/T3-suite.log:54. |
| T4 Contribution | N/A | Contribution artifacts are absent by design; the substantive contribution audit is deferred to the mandatory publish gate, not waived; gate-logs/T4-contribution.log:10. |
| T5 Judgment | PASS | Scope remains one merge-safety fix; path-based history and closed-unmerged PR inspection found no competing stale-base fix, and the changed sign-off coverage is explicit; reviewer-prior-art.log:1, target/template/docs/fork-discipline.md.jinja:65. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether CI-only verification of the updated combination and the documented last-read race are acceptable for deployment — live GitHub update/merge and strict-protection behavior were not exercised, so those outcomes rest on the stateful fake and API-contract inspection; target/template/docs/fork-discipline.md.jinja:65, target/template/pdca.toml.jinja:132. |

No grounded patch defect found. Source citations above resolve inside the supplied target. Its synthetic base identifies c67a14d, matching the brief; reverse-application checking confirms the supplied patch is present, and the production stash was restored. No target-state caveat applies.

Independent verification used `cd target/template && PYTHONPATH=src python3 -m unittest tests.test_merge`, first with `template/src/pdca_harness/merge.py` stashed and then restored, retaining the patched tests throughout. Full-suite verification used `PYTHONPATH=src python3 -m unittest discover -s tests`. Temporary test files were confined under this review directory. Docs verification used the target's `lint_docs.py` and `render_site.py --check` with output under this directory.

All six frozen gate logs were inspected. The C5 scanner explicitly did nothing because no new test file was added (gate-logs/C5-prod-path.log:10); C5's substantive judgment instead rests on tracing the production call and independently reproducing red→green. The instance-scoped wrappers are not needed to rerun the underlying merge tests, offline suite, or docs tools. Copier-dependent root coverage is supported by the frozen log, not claimed as an independent rerun.

The new `_read_head` was also exercised read-only against PR #620: it returned head `69abaa12bbc1d797a0ce83730ab51aca263c3032` and `behindBy = 7` (reviewer-host-read.log:1). This verifies an actual SHA-based comparison response, not update or merge behavior. The [GitHub CLI implementation](https://github.com/cli/cli/blob/trunk/pkg/cmd/pr/update-branch/update_branch.go) confirms that an update without `--rebase` requests a merge commit; its [comparison helper](https://github.com/cli/cli/blob/trunk/api/queries_pr.go) uses the same baseRef.compare field family.

Prior-art investigation queried merged history separately for all five affected paths and inspected all four closed-unmerged PRs' changed-file lists. PRs #598–600 touch the shared docs/config files, but their hunks concern auto-iteration, gate confirmation, and size accounting; none changes stale-base merging. The merge implementation and test history matches the brief's #582/#462/#413 predecessors. Results and overlapping hunks are retained in reviewer-prior-art.log and reviewer-prior-art-hunks.log. The supplied INTEGRATION template's §4 lists human-only items as TODO, with no additional concrete item to adjudicate (target/template/docs/INTEGRATION.md.jinja:80).

For supplementary live validation, use a maintainer-approved disposable GitHub repository and a rendered instance containing this patch. Prepare two COMPLETE bundles with distinct green PRs from the same base, configure `merge_requires = "all"`, and run the production wave from that instance with `PYTHONPATH=src python3 -c 'from pdca_harness.config import Config; from pdca_harness import merge; c=Config.load(); raise SystemExit(merge.merge_wave(c, [c.bundle("A"), c.bundle("B")], method="merge"))'`, substituting the actual bundle IDs. Observe A merging, B receiving a merge-commit update, B's updated-head checks completing and being confirmed, and the merge pinned to that updated SHA. Repeat with strict protection enabled and disabled; make B's combined tree fail CI and confirm B remains unmerged and returns to draft. This live exercise was not performed during this advisory review.

### Advisory — code-review

# Advisory code review — issue 531 / merge-mode-stale-base-merge

Lens: correctness bugs the patch adds, plus reuse/simplification. Advisory only.
The offline logic looks right: the order ready → behind read → update → bounded wait →
head re-read → pinned merge is correct, every new refusal undoes the ready-mark, and
`merge_requires = "required"` keeps its old call log (test (c)). The real risks are in how
GitHub behaves live, which the offline fake can't show.

- NEEDS-HUMAN — `template/src/pdca_harness/merge.py:222-224,241-243`: the behind read passes the head **SHA** to `baseRef { compare(headRef: $head) }`. The comment at `:216-218` says this is "the same GraphQL comparison `gh pr update-branch` itself makes", but as far as I know `gh` passes the head *branch name* there (with an `owner:` prefix for fork PRs), not a SHA. Nothing in the patch or the gates shows that `Ref.compare` accepts a bare commit SHA, including a fork PR's head commit. If it doesn't, `behind` comes back `None` and **every** merge-mode merge under `"all"` is refused at `:334-335`. That fails safe, but it would break merge mode completely. Run it once against a real PR (same-repo and fork) before sign-off, or fix the comment.
- NEEDS-HUMAN — `template/src/pdca_harness/merge.py:339-351`: the code reads the head again right after `gh pr update-branch` returns and refuses if it is still behind. GitHub's branch update may finish asynchronously (the REST endpoint returns 202 Accepted). If the GraphQL mutation behind `gh` works the same way, the read at `:346` can still see the old head, and the run stops with "still behind its base after `gh pr update-branch`". That would undo the main goal: multi-member waves finishing. If live testing shows the lag, fix it with a short bounded poll for a new head (charged to `merge_wait_secs`) rather than a single read. The offline `_Host` fake updates instantly, so the tests can't catch this.
- `template/src/pdca_harness/merge.py:311-326`: `def refuse` sits between the #413 comment block and the `if cfg.merge_requires != "required"` line that comment explains (the "`!= "required"` rather than `== "all"`" note now sits above an unrelated nested function). Move `refuse` above that comment block.
- `template/src/pdca_harness/merge.py:366-374` and `:394-404`: the patch adds `refuse()` (print + `_undo_ready` + `return 1`) but leaves the two older refusal paths in the same function writing out the same print/undo/return by hand. Optional cleanup: route them through `refuse` or one shared helper. Keep their specific wording, since tests check for strings like "FAILING" and "did not merge". It also removes the odd line break at `:400-402` (`"at the PR, "` / `"then re-run.\n"`).
- NEEDS-HUMAN [impl] — `template/tests/test_merge.py` (patch hunk `@@ -675`, `test_updated_head_that_is_not_green_is_not_merged`): the red head is hard-coded as `"u2".ljust(40, "0")`, which depends on `_Host` creating SHAs from `len(self.contains)`. If the fake changes, this test can silently stop meaning "the updated head is red". It would still fail on `rc`, but it's fragile. Better: let `_Host` mark the head *produced by* `update-branch` for a given URL as red (e.g. `red_after_update: set[str]`).
- `template/tests/test_merge.py` (`_Host.__call__`, graphql branch): it parses arguments with `a[:2] != "qu"` to skip the `query=` field. This works, but it's an obscure way to say `not a.startswith("query=")`. Small readability fix.
- One limitation the docs don't state: after `gh pr update-branch` succeeds but the run then refuses (red combined head, head changed, still behind), the merge commit the driver pushed stays on the PR branch. Only the ready-mark is undone. The fork-discipline text (`template/docs/fork-discipline.md.jinja:65`) says "stops the run with the PR back in draft", which is true but incomplete. Consider one clause saying the update commit remains.

Gates: C4 shows the new and changed tests red before the fix and green after (`gate-logs/C4-verify.log`). T3 runs the full suite: 2305 tests OK. C5 "adds no new test file" is expected, because the tests were appended to the existing `test_merge.py`.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] Validation — fitness-to-purpose — Decide whether CI-only verification of the updated combination and the documented last-read race are acceptable for deployment — live GitHub update/merge and strict-protection behavior were not exercised, so those outcomes rest on the stateful fake and API-contract inspection; target/template/docs/fork-discipline.md.jinja:65, target/template/pdca.toml.jinja:132.
- [ ] `template/src/pdca_harness/merge.py:222-224,241-243`: the behind read passes the head **SHA** to `baseRef { compare(headRef: $head) }`. The comment at `:216-218` says this is "the same GraphQL comparison `gh pr update-branch` itself makes", but as far as I know `gh` passes the head *branch name* there (with an `owner:` prefix for fork PRs), not a SHA. Nothing in the patch or the gates shows that `Ref.compare` accepts a bare commit SHA, including a fork PR's head commit. If it doesn't, `behind` comes back `None` and **every** merge-mode merge under `"all"` is refused at `:334-335`. That fails safe, but it would break merge mode completely. Run it once against a real PR (same-repo and fork) before sign-off, or fix the comment.
- [ ] `template/src/pdca_harness/merge.py:339-351`: the code reads the head again right after `gh pr update-branch` returns and refuses if it is still behind. GitHub's branch update may finish asynchronously (the REST endpoint returns 202 Accepted). If the GraphQL mutation behind `gh` works the same way, the read at `:346` can still see the old head, and the run stops with "still behind its base after `gh pr update-branch`". That would undo the main goal: multi-member waves finishing. If live testing shows the lag, fix it with a short bounded poll for a new head (charged to `merge_wait_secs`) rather than a single read. The offline `_Host` fake updates instantly, so the tests can't catch this.
- [ ] `template/tests/test_merge.py` (patch hunk `@@ -675`, `test_updated_head_that_is_not_green_is_not_merged`): the red head is hard-coded as `"u2".ljust(40, "0")`, which depends on `_Host` creating SHAs from `len(self.contains)`. If the fake changes, this test can silently stop meaning "the updated head is red". It would still fail on `rc`, but it's fragile. Better: let `_Host` mark the head *produced by* `update-branch` for a given URL as red (e.g. `red_after_update: set[str]`).
- [ ] **The brief does not cover `merge_requires = "required"`.** The criterion says "for every PR `merge_wave` merges, the head commit that merges is the head whose rollup was read green". Under `merge_requires = "required"`, `_merge_one` reads no rollup at all (`merge.py:259` skips the whole gate), so this clause cannot hold on that path. The brief also never says whether update-branch runs there. If it doesn't, `required` + `strict: false` still merges a stale base, and `required` + `strict: true` still stops after the first merge, which is the exact defect. The planner has to pick a side. Option 1: update-branch runs on both paths, and on the `required` path the merge just waits on the host's checks. Option 2: `required` explicitly keeps the stale-base behaviour, and the brief says so in out-of-scope and in the config comment. Either way the criterion's wording must be corrected and a test added for the chosen side.
- [ ] **"Contains the base's tip as it stood at merge time" promises something the driver can't guarantee.** The criterion asks that the merged head "contains the base's tip as it stood at merge time", and that "on a host with `strict: false` no stale-base merge happens". The brief itself admits the base can move "for any other reason", for example outside pushes. A client-side driver can't rule out a move between its last behind/rollup read and `gh pr merge` (`merge.py:264` → `:287`). On `strict: false` only the host (strict mode or a merge queue) could close that window. As written, the criterion is unfalsifiable at Check and wrong in the race window. Restate it as: no merge on a head that was behind *at the driver's last read immediately before `gh pr merge`*. Then list the remaining race as accepted, or as a reason to recommend `strict: true`.
- [ ] **No test covers "cannot land a head other than the one verified".** Scope says "the merge itself cannot land a head other than the one verified". The criterion says "the head that merges is the head whose rollup was read green". The test described only asserts update → green read → merge order. `_check_rollup` (`merge.py:108`, `gh pr checks --json name,bucket`) returns no head SHA, so reusing `_wait_for_green` unchanged, as the brief requires at "Citations expected", ties the verdict to no commit at all. Three ways around it:
- [ ] **The test-fake guidance contradicts itself.** The Falsifiability section says to "keep the fake answering by command shape (as `_gh` does), not by call order". But the scenario is order-dependent by nature: B must read as behind only *after* `gh pr merge A`, and its rollup must describe the *new* head only after the update. `_gh` (`test_merge.py:67-71`) keys on `cmd[2]` alone, returns the same answer for every PR, and the bundle fixture defaults every bundle to the same `pr_url` (`test_merge.py:91`). Tell Do to write a stateful fake keyed by PR URL that flips B to behind when it sees a merge of A. Also require distinct `pr_url`s for A and B. Without both, the RED can pass or fail for the wrong reason.
- [ ] **The doc edit is left conditional when it is already known to be needed.** The brief says to touch `fork-discipline.md.jinja:51-59` "if it describes the merge steps". It does: lines 57-58 say the driver reads the rollup "after the ready-mark and immediately before the merge". The new update-branch → re-wait step changes that sequence. Make the edit mandatory (and the range `:51-60`) so Check can verify it, rather than leaving it to Do's judgment.
- [ ] **Nobody signs off on the fact that the merged tree is not the reviewed patch.** After `gh pr update-branch`, the PR head that merges is a new merge commit (or a rebase) that Check never reviewed. `patch.diff` / `publish.json` describe the pre-update head. That is arguably the point, since CI verifies the combination. But it is a change in what "accepted at sign-off" covers, and in merge mode the readiness is driver-granted (`fork-discipline.md.jinja:51-56`). The brief should say so explicitly. It should also say whether a rebase-style update (rewritten history, so no longer the reviewed commits) is allowed under `merge_method = "rebase"`, rather than leaving the choice of update style to Do.

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
- Iteration delta (if iterating): The goal and the overall sequence are right (ready → behind check → update-branch → bounded rollup wait on the new head → merge pinned to that head; `merge_requires = "required"` unchanged). Change how "behind" is decided, and make the post-update check tolerate GitHub's lag: 1. Replace the GraphQL `baseRef { compare(headRef: <sha>) { behindBy } }` read (`_BEHIND_QUERY` / `_read_head`) with the same pattern #593 / PR #619 used in `publish.py:_line_tip_refusal`: record the base branch's tip SHA, fetch, and decide with `git merge-base --is-ancestor <base-tip-sha> <pr-head-sha>` (exit 0 = up to date, 1 = behind, anything else or a failed fetch = refuse, fail-closed, saying git failed). Plain git, consistent with the stack-mode check; no reliance on GraphQL compare semantics. 2. After `gh pr update-branch`, do not read the head once and refuse if still behind: GitHub may finish the update asynchronously. Poll, bounded by and charged to `merge_wait_secs`, until the PR head contains the recorded base-tip SHA; only then wait for that head's rollup and merge pinned to it. Timeout still refuses with readiness undone. 3. Tests in template/tests/test_merge.py: add a case where the update lands late (the fake reports the old head for one or two reads after update-branch, then the updated one) and the PR still merges, pinned to the updated head; and a case where it never lands within the wait and the run refuses, readiness undone. Replace the hard-coded red head `"u2".ljust(40, "0")` in `test_updated_head_that_is_not_green_is_not_merged` with a fake option that marks the head produced by update-branch as red.
- By / date: Eduard Ralph / 2026-10-04

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 6 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
