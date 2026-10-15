# Result — issue 650 / merge-mode-reads-head-from-its-own-remote

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: In merge mode (`[driver].wave_mode = "merge"`, `merge_requires` other than `"required"`), `_merge_one` reads whether the PR head is behind its base in git (`template/src/pdca_harness/merge.py:420-446`). `_fetch` (`merge.py:256-263`) fetches only `cfg.base_remote` and `origin`. A bundle with a brief `Onto branch: <remote>/<branch>` is published by `publish._publish_stacked`, which pushes to THAT remote (`git push <remote> HEAD:<branch>`, `template/src/pdca_harness/publish.py:465`, `:476-485`) and records it as `{"mode": "stacked", "base": "<remote>/<branch>", …}` (`publish.py:539-547`). When `<remote>` is a third remote, the PR's head commit, and after `gh pr update-branch` its new merge commit, exist only there. `_contains` (`merge.py:266-273`) then gets git exit 128 ("not a valid commit") and the run refuses with "git failed: `git merge-base --is-ancestor …` … exited 128" (`_git_failed`, `merge.py:250-253`). This fails closed, so nothing merges wrongly. But such a PR can never merge in merge mode once it falls behind, and the message hides the real cause.
- Success criterion: With the patch, on a real-git fixture (a primary checkout with remotes `origin`, the base remote, and a third remote `other`; `gh` scripted). The test drives everything through `merge._merge_one(cfg, d, dry_run=False, method="merge", fetched=set())` (`merge.py:365`), whose signature this fix does not change, so the C4 revert leg fails on behaviour, not with a `TypeError` from a changed helper signature. Do may change the private helpers' signatures (`_fetch`, `_base_read`, `_wait_for_update`) however it likes; the test must not call them directly.
  (1) A COMPLETE bundle whose `publish.json` is `{"mode": "stacked", "branch": "feat", "base": "other/feat", "pr_url": …, "repo": …}` (real records carry `branch`, `publish.py:541`; without it `integrate._published_ref` returns None, `integrate.py:150-152`), and whose PR head (`gh pr view … headRefOid`) is a commit that exists only on `other`: `_merge_one` does not refuse with "git failed"; it reads `behind` and reaches the rollup wait (the test patches `merge._wait_for_green` to record that it was called). A second case where the head is behind: after a scripted `gh pr update-branch` that moves `other/feat` to a new merge commit, `_merge_one` sees that commit and reaches the rollup wait.
  (2) When the reported head commit is in no remote the run fetched, the refusal names that commit and says the checkout does not have it (and which remotes were fetched). It does not say only "git failed … exited 128".
  (2b) A `"stacked"` record from which `_published_ref` can name no remote (no `branch`, or a `base` that does not end in `/<branch>`, `integrate.py:153-157`) fetches what it fetches today (base remote and `origin`) and, if the head is still missing, refuses with the (2) message. No up-front refusal.
  (3) Unchanged: a `new-pr` record (branch on `origin`) runs exactly the fetches it runs today. A test in the new file wraps the real `subprocess.run` to record every `git fetch` argv and asserts the list is `[base_remote, "origin"]` deduplicated, in that order (as `merge.py:259`), for a `new-pr` record. Every existing `test_merge.py` test still passes.
  Pre-fix, (1) refuses with "git failed … exited 128", and (2) says "git failed". That is the RED.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: Make merge mode's base/head reads fetch the remote the bundle's publish record says its branch was pushed to (in addition to the base remote and `origin`), and make a head commit that is still missing after the fetches a refusal that names it. / out of scope: whether an `Onto branch` bundle should be allowed in merge mode at all (it bypasses the #411 merge-mode base guard because `publish.py:225-228` returns before `:289`; a separate issue if wanted); the rollup wait (#621); stack mode's fold (it already fetches these remotes); fork-model `base_remote` handling beyond adding the record's remote.

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

Review issue #650: make merge mode fetch the PR branch’s recorded remote and accurately explain a head commit still missing after fetching.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The scoped failure and offline success criteria are falsifiable and consistent with publish-record ownership; malformed records retain existing fallback behavior (`brief.md:13`, `target/template/src/pdca_harness/integrate.py:139`). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only the production fix produced nine behavioral assertion failures across ten tests, including the third-remote head’s git exit 128; no helper-signature failure (`review-red.log:127`, `target/template/tests/test_merge_third_remote.py:156`). |
| C3 Change | PASS | Changes stay within remote selection, missing-head diagnostics, and their tests; normal records preserve fetch order and deduplication (`target/template/src/pdca_harness/merge.py:273`, `target/template/tests/test_merge_third_remote.py:292`). |
| C4 Verification (red→green) | PASS | Restoring the production fix passed all 65 selected merge tests, including all ten new regressions and 49 existing merge tests; independent results corroborate the frozen gate (`review-green.log:70`, `gate-logs/C4-verify.log:10`). |
| C5 Causal adequacy | PASS | Fetching the recorded remote removes the missing-object cause on initial, post-update, and final reads; real git reproduces the forbidden failure, and added failure-path probes preserve refusal (`target/template/src/pdca_harness/merge.py:280`, `target/template/src/pdca_harness/merge.py:376`, `target/template/src/pdca_harness/merge.py:534`, `review-extra.log:1`). |
| T1 Structure | PASS | Shared publish-record interpretation avoids divergent remote parsing, and importing the existing integration helper executes successfully through production tests (`target/template/src/pdca_harness/merge.py:481`, `target/template/src/pdca_harness/integrate.py:139`, `review-green.log:72`). |
| T2 Shape | PASS | Independent production-import scan, docs lint, 22-page render/link audit, and diff whitespace check pass; both frozen docs gates agree (`review-scanners.log:1`, `gate-logs/T2-docs.log:10`, `gate-logs/host-ci-docs.log:10`). |
| T3 Runtime | PASS | Independent driver run passed 2,379 tests with two skips; root render/update coverage rests on the frozen 24-test passing run because this interpreter lacks Copier (`review-suite.log:1797`, `gate-logs/T3-suite.log:54`, `review-root.log:6`). |
| T4 Contribution | N/A | Contribution artifacts are intentionally absent at Check; the substantive contribution audit is deferred to its mandatory publish-time rerun (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Confirm the affected-path prior-art disposition against merged and closed/rejected work — the brief records a search, but this artifact-only snapshot exposes only a synthetic base commit and no PR records, so independent confirmation is unavailable (`brief.md:30`, `review-history.log:1`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the demonstrated offline behavior and revised diagnostic satisfy operator needs within the agreed merge-mode scope — actual host update/merge behavior is scripted, and the broader policy for Onto-branch bundles remains outside this fix (`brief.md:25`, `target/template/tests/test_merge_third_remote.py:115`, `target/template/src/pdca_harness/merge.py:303`). |

No implementation defect found. The prior iteration’s misleading diagnostic is corrected: a successfully fetched remote with a restrictive refspec is reported as having failed to bring in the commit, without claiming that remote was omitted. Both that case and a missing origin head passed independently (`target/template/tests/test_merge_third_remote.py:216`, `target/template/tests/test_merge_third_remote.py:235`, `review-green.log:55`). Additional real-git probes confirmed refusal on third-remote fetch failure and accurate reporting of an unavailable post-update head (`review-extra.log:1`, `review-extra.log:6`).

The capability-probe smell test does not identify a symptom-only workaround: the omitted fetch is corrected; the object check supplies the explicitly requested diagnostic when fetching still cannot supply the head. Git operations were real, with no tool aliases or shims; the fixture exhibited the original failure. Scripted host calls bound the evidence to the brief’s offline scope rather than establishing live host behavior.

The target matched the supplied patch, and reverse-apply checking succeeded after the production stash was restored. Source citations above refer to that target. The local root-suite attempt exited 77 because Copier is not importable; its apparent unittest success with three skips is not counted as verification. The frozen T3 log explicitly shows the render/update cases executing and all 24 root tests passing, so the local limitation is a reviewer-host caveat, not a patch defect or an unmet dependency in the frozen gate run. The available integration template enumerates no additional project-specific human-only items (`target/template/docs/INTEGRATION.md.jinja:80`).

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — issue 650 (merge mode reads head from its own remote)

The patch is clean on both lenses. I found no correctness bug and nothing that needs a human or another build round. The notes below are informational only, and none is tagged NEEDS-HUMAN.

**Correctness: checked and OK**

- `template/src/pdca_harness/merge.py:298-302`: `_have` treats exit 1 from `git cat-file -e` as "commit not here" and any other exit as a git failure. I checked this against real git: a well-formed 40-hex SHA that is missing exits 1, and a malformed name (`not-a-commit`, or a short SHA it can't resolve) exits 128. So the split is right, and the "missing" message only fires for a real, well-formed SHA. The host reports full SHAs (`headRefOid`), so that is the normal case.
- `template/src/pdca_harness/merge.py:265-273`: `_remotes` keeps the old fetch order (`base_remote`, `origin`) and adds the record's remote last, with duplicates removed. A `new-pr`/`stacked-pr` record (remote `origin`) or a record that names no remote (`None`) fetches exactly what it fetched before. This matches brief criteria (3) and (2b). The test at `template/tests/test_merge_third_remote.py:292` checks the exact `git fetch` argv list, including the case where `base_remote == "origin"`.
- `template/src/pdca_harness/merge.py:303-309`: last round's finding was that the refusal blamed a remote that had actually been fetched. That is fixed. The message now says only what was checked: the commit, the checkout, the remotes fetched, and either where the record puts the branch or that the record names no remote. The refspec case and the `new-pr`-head-not-on-origin case each have a test that pins the wording.
- `template/src/pdca_harness/merge.py:376`: in `_wait_for_update`, `_fetch(...) or _have(...)` runs `_have` only after a successful fetch. A missing head refuses before `_contains` runs, so this stays fail-closed.
- `template/src/pdca_harness/merge.py:481`: `pub` is read once and passed to all three reads (first read, update wait, read after green). The record's remote is fetched every time, and the test at `test_merge_third_remote.py` (`..._green_merges_pinned_...`) asserts this.
- `template/tests/test_merge.py:825`: the fake host's new `cat-file -e` branch answers from the same `self.local` set that the `merge-base` fake already uses (`:830`). Existing tests keep their behavior, and the suite passed (T3 log: 2379 tests OK).
- The C4 gate log shows the new tests failing on the unpatched code with the old `git failed … exited 128` message. That is a real behavioral RED, not a `TypeError` from a changed signature. The patched code passes.

**Reuse / simplification / efficiency: nothing to act on**

- `template/src/pdca_harness/merge.py:481` against `:428`: `integrate._published_ref(d)` reads `publish.json` again, even though `_merge_one` already holds `rec`. This is one extra small file read per bundle. The brief asks for exactly this reuse, so the record is parsed the same way the fold parses it. Not worth changing.
- `template/src/pdca_harness/merge.py:304`: `_have` calls `_remotes` again to build its message. The function is pure and cheap and gives the same answer `_fetch` used, so this is fine.
- `template/tests/test_merge_third_remote.py:281`: this test doesn't assert `rc`. It doesn't need to, because the point is "not refused up front" and `self.waited == [self.feat]` already proves the rollup wait was reached.

No findings for SUMMARY §6.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — Confirm the affected-path prior-art disposition against merged and closed/rejected work — the brief records a search, but this artifact-only snapshot exposes only a synthetic base commit and no PR records, so independent confirmation is unavailable (`brief.md:30`, `review-history.log:1`).
- [x] Validation — fitness-to-purpose — Decide whether the demonstrated offline behavior and revised diagnostic satisfy operator needs within the agreed merge-mode scope — actual host update/merge behavior is scripted, and the broader policy for Onto-branch bundles remains outside this fix (`brief.md:25`, `target/template/tests/test_merge_third_remote.py:115`, `target/template/src/pdca_harness/merge.py:303`).
- [x] **The test fixture as written cannot turn green with the fix the brief prescribes.** The success criterion (1) and the repro instruction both give `publish.json` as `{"mode": "stacked", "base": "other/feat", "pr_url": …, "repo": …}`, with no `"branch"` key. The brief also tells Do to read the remote "exactly as `integrate._published_ref` does … reuse it rather than re-parse `publish.json`". But `_published_ref` returns `None` when there is no `branch` (`integrate.py:150-152`: `if not branch or not isinstance(branch, str): return None`). So with this fixture the reused helper finds no remote, `other` is never fetched, and criterion (1) stays RED even with a correct patch. Real records do carry `"branch": branch` (`publish.py:541`). The brief should add `"branch": "feat"` to the fixture in both places.
- [x] **The RED depends on a call shape that the fix has to change.** The repro and criterion (1) call `merge._base_read(cfg, primary, url)`, and the criterion also uses `_wait_for_update`. Neither function can see the bundle or its record today: `_base_read(cfg, repo, pr_url)` (`merge.py:276`), `_wait_for_update(cfg, repo, pr_url, stale, tip, wait_secs)` (`merge.py:303`), and `_fetch(cfg, repo)` (`merge.py:256`). To fetch "the remote the record names", Do has to pass that remote (or `d`) through all three, which changes their signatures. The C4 gate keeps the new test and reverts the production code. On that revert, a test that calls the new signature fails with `TypeError`, not with the "git failed … exited 128" RED the brief promises (brief line "Pre-fix, (1) returns `behind=None` with "git failed""). The brief should do one of two things. Either fix the new parameter shape in advance, for example an optional keyword like `remotes=()` that defaults to today's behaviour so the pre-fix call still runs, or drive the RED through `_merge_one(cfg, d, …)`, whose signature does not change. Otherwise the falsifiability claim cannot be checked.
- [x] **The brief does not say what happens when a `"stacked"` record names no remote.** `_published_ref` returns `None` for a stacked record whose `base` does not end in `/<branch>` (`integrate.py:153-157`). It also returns `None` for an older record with no `branch`. The brief says to keep every read fail-closed (`merge.py:259-262`) but does not say whether this case should quietly fall back to `base_remote`+`origin` (today's behaviour, which then ends in the criterion-(2) message) or refuse up front. The two choices behave differently. If the brief does not decide, Do will choose without telling anyone. The planner should pick one and add a criterion for it.
- [x] **Criterion (3) may not be checkable by the existing tests.** "a `new-pr` / `stacked-pr` record … fetches exactly what it fetches today" is what keeps behaviour unchanged for the common path. But `test_merge.py`'s `_gh` stub makes every `git` call succeed (`test_merge.py:85-99`), and none of the `_base_read`/`_fetch` call sites in that file are named in the brief. "Every existing test still passes" therefore may not prove that the fetch list is unchanged. The brief should require a test that asserts the `git fetch` argv list for a `new-pr` record (`origin` + base remote only, in today's order), or name the existing test that already does.

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
- By / date: Eduard Ralph / 2026-10-10

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 4 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
