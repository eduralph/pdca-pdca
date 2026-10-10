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

Review issue #650: let merge mode read PR heads from the remote named in the publish record, including updated heads, and clearly report commits still missing after fetch.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The third-remote failure, missing-head refusal, malformed-record fallback, and unchanged origin fetches have falsifiable acceptance criteria; the existing remote-ownership contract grounds the scope (`brief.md:12`, `target/template/src/pdca_harness/integrate.py:139`). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only the production fix produced five behavioral assertion failures with real git exit 128 for missing heads, without signature/import failures (`review-red.log:13`, `target/template/tests/test_merge_third_remote.py:138`). |
| C3 Change | PASS | The three affected files stay within the requested merge-read and regression-test scope; malformed records retain the existing fallback and failed fetches still refuse (`target/template/src/pdca_harness/merge.py:260`, `target/template/src/pdca_harness/merge.py:273`). |
| C4 Verification (red→green) | PASS | Restoring the unchanged patch made all 60 merge-related tests pass, including the existing 49 merge tests and new third-remote cases; the frozen C4 log independently agrees (`review-green.log:16`, `gate-logs/C4-verify.log:10`). |
| C5 Causal adequacy | PASS | Fetching the record's actual remote removes the missing-object cause on initial, update, and final reads; real-git cases reach the rollup wait, and the presence check supplies a fail-closed diagnostic rather than concealing a load-time cause (`target/template/src/pdca_harness/merge.py:355`, `target/template/src/pdca_harness/merge.py:512`, `review-additional.log:3`). |
| T1 Structure | PASS | Reusing the fold's remote-ownership parser avoids divergent interpretations of publish records and introduces no import cycle; production imports and the full driver suite succeed (`target/template/src/pdca_harness/merge.py:266`, `target/template/src/pdca_harness/integrate.py:139`). |
| T2 Shape | PASS | Independent docs lint, 22-page rendering/link audit, production-import scanner, and diff whitespace checks passed; frozen docs and host-CI parity logs show the same checks passing (`gate-logs/T2-docs.log:10`, `gate-logs/host-ci-docs.log:10`). |
| T3 Runtime | PASS | Independently reran all 2,374 driver tests successfully with two skips; frozen root-suite evidence shows all 24 render/update-compat tests passing, with no claim of an independent root-suite rerun (`review-suite.log`, `gate-logs/T3-suite.log:54`, `gate-logs/T3-suite.log:1854`). |
| T4 Contribution | N/A | Contribution artifacts are intentionally absent at Check; their substantive audit is deferred to the mandatory publish-time rerun (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN [impl] | Correct the unsupported explanation of a missing head — an actually fetched, correctly recorded remote with a restricted refspec is falsely blamed as absent, sending operators toward the wrong repair (`target/template/src/pdca_harness/merge.py:287`, `review-diagnostic.log:5`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the bounded offline behavior satisfies the intended merge workflow, and confirm the documented file-path prior-art search covers merged and closed/rejected work — the supplied snapshot has one synthetic commit and no remotes, so that history cannot be independently corroborated (`brief.md:25`, `brief.md:30`, `target/template/tests/test_merge_third_remote.py:124`). |

Independent verification used the disposable target at `/tmp/pdca-review-x99ur30b/target`, whose sole base commit identifies the brief's `b5f5c29` base. The production file was stashed for the red leg and restored before all green checks; no proposed fix was edited. Commands used `TMPDIR` inside this review sandbox. Code citations above resolve against this target; other citations identify the supplied or independently captured evidence.

The diagnostic finding is reproducible with the shipped real-git fixture: push both `main` and `feat` to `other`, set the primary checkout's `remote.other.fetch` to `+refs/heads/main:refs/remotes/other/main`, retain the valid stacked record naming `other/feat`, and call `_merge_one`. `git ls-remote other refs/heads/feat` confirms the head exists; the observed fetch list is `upstream, origin, other`. The refusal nevertheless says “the remote its branch was pushed to is not among them (or its publish record does not name it)” (`review-diagnostic.log:1`). Both alternatives are false. Keep the verified facts (missing commit, checkout, fetched remotes), remove or qualify the unproven cause, and cover this diagnostic case. This does not require expanding scope to fetch arbitrary refspecs; refusing remains correct.

Additional independent cases passed: `base_remote=origin` fetches origin once; an unavailable `other` refuses before the rollup wait; a scripted green rollup triggers another fetch of all three remotes before the pinned merge command (`review-additional.log:1`). All host commands in these cases were intercepted by the fixture. The real-git topology exhibits the forbidden pre-fix failure, so scripting `gh` does not leave the brief's stated offline dependency unmet. Live GitHub behavior and actual merging were not exercised.

The frozen C4, production-path, docs, host-CI docs, runtime, and deferred contribution logs were inspected. Instance-scoped wrapper paths were not treated as missing target tools. The root render/update-compat verdict relies on its frozen log rather than a rerun against the synthetic one-commit history. The prior-art section explicitly records a search by `template/src/pdca_harness/merge.py` across merged history and closed PRs; local `git log --all -- <affected paths>` yielded only the synthetic base, and `git remote -v` yielded no remotes. No other checkout was consulted. The target contains only the generic `INTEGRATION.md.jinja`, whose human-only list is an unfilled TODO, so no additional project-specific human-only requirement was inferred.

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — issue_650 (merge-mode-reads-head-from-its-own-remote)

Lens: bugs the patch introduces, plus reuse and simplification. All gates pass. I found no correctness bug that blocks the fix. Two small wording/test points and some notes follow.

## Findings

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/merge.py:287-289`: the `_have` refusal always ends with "the remote its branch was pushed to is not among them (or its publish record does not name it)". For a `new-pr` / `stacked-pr` record, the branch's remote (`origin`) *is* in the fetched list. A missing head there means something else, such as a force-push between the `gh pr view` read and the fetch, or a host reporting a commit no remote has yet. So the second clause is wrong for that case and sends the operator looking in the wrong place. Fix: add that clause only when `integrate._published_ref(d)` returned None or named a remote outside `remotes`, or reword it neutrally, e.g. "none of these remotes has it".
- `template/tests/test_merge_third_remote.py:120-122` (patch lines 336-338): the `_wait` stub records `self.head`, the value the `gh` stub will return next. It does not record a head that `_merge_one` read. In `test_stacked_head_behind_is_updated_on_third_remote_and_reaches_wait`, `self.waited == [merged_head]` therefore proves less than it seems. What does prove that the merge commit was fetched from `other` is that the wait was reached at all, because `_wait_for_update` (`merge.py:354-363`) only returns once `_have` and `_contains` succeed on the new head. The test still catches the regression and the C4 log shows red/green, so this is a clarity note, not a defect. It is optional to assert on the `--match-head-commit` argv or on stdout's "updated: head <sha>" line instead.

## Checked and clean

- Import cycle: `merge.py:86` now imports `integrate` at top level. `integrate.py:59-60` imports only `merged`, `publish` and `config`, and nothing under them imports `merge`; only `flow.py:31` does. No cycle.
- Reuse: `_remotes` (`merge.py:260-267`) uses `integrate._published_ref` as the brief asked, instead of parsing `publish.json` again. It reads the record a second time (`_merge_one` already holds `rec`, `merge.py:407`). That costs one small file read per bundle. It is not worth changing, because `_published_ref` takes a bundle path.
- Fail-closed: a failed fetch of the record's remote is a refusal (`merge.py:270-277`). `publish._publish_stacked` fetches and pushes that same remote from the same `repo_checkouts` checkout (`publish.py:467`, `:477`, `:485`), so the remote always exists where merge mode reads. This adds no new way to fail.
- Order and dedup: `dict.fromkeys((base_remote, "origin", record_remote))` (`merge.py:267`) keeps `[base_remote, "origin"]` exactly as before for `new-pr` records. Criterion (3) is covered by the argv test at patch lines 413-417.
- `_have` runs after the base tip resolves and before `_contains` (`merge.py:325-327`), and in the update poll (`merge.py:354`). Both `_base_read` calls, before and after the green read (`merge.py:463`, `:519`), use the same `remotes`.
- `test_merge.py:824-825`: the new `cat-file -e` branch in the `_Host` stub checks the same `self.local` set that its `merge-base` branch uses (`test_merge.py:830`), so existing tests keep their old behaviour. The T3 suite log is green.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T5 Judgment — Correct the unsupported explanation of a missing head — an actually fetched, correctly recorded remote with a restricted refspec is falsely blamed as absent, sending operators toward the wrong repair (`target/template/src/pdca_harness/merge.py:287`, `review-diagnostic.log:5`).
- [ ] Validation — fitness-to-purpose — Decide whether the bounded offline behavior satisfies the intended merge workflow, and confirm the documented file-path prior-art search covers merged and closed/rejected work — the supplied snapshot has one synthetic commit and no remotes, so that history cannot be independently corroborated (`brief.md:25`, `brief.md:30`, `target/template/tests/test_merge_third_remote.py:124`).
- [ ] `template/src/pdca_harness/merge.py:287-289`: the `_have` refusal always ends with "the remote its branch was pushed to is not among them (or its publish record does not name it)". For a `new-pr` / `stacked-pr` record, the branch's remote (`origin`) *is* in the fetched list. A missing head there means something else, such as a force-push between the `gh pr view` read and the fetch, or a host reporting a commit no remote has yet. So the second clause is wrong for that case and sends the operator looking in the wrong place. Fix: add that clause only when `integrate._published_ref(d)` returned None or named a remote outside `remotes`, or reword it neutrally, e.g. "none of these remotes has it".
- [ ] **The test fixture as written cannot turn green with the fix the brief prescribes.** The success criterion (1) and the repro instruction both give `publish.json` as `{"mode": "stacked", "base": "other/feat", "pr_url": …, "repo": …}`, with no `"branch"` key. The brief also tells Do to read the remote "exactly as `integrate._published_ref` does … reuse it rather than re-parse `publish.json`". But `_published_ref` returns `None` when there is no `branch` (`integrate.py:150-152`: `if not branch or not isinstance(branch, str): return None`). So with this fixture the reused helper finds no remote, `other` is never fetched, and criterion (1) stays RED even with a correct patch. Real records do carry `"branch": branch` (`publish.py:541`). The brief should add `"branch": "feat"` to the fixture in both places.
- [ ] **The RED depends on a call shape that the fix has to change.** The repro and criterion (1) call `merge._base_read(cfg, primary, url)`, and the criterion also uses `_wait_for_update`. Neither function can see the bundle or its record today: `_base_read(cfg, repo, pr_url)` (`merge.py:276`), `_wait_for_update(cfg, repo, pr_url, stale, tip, wait_secs)` (`merge.py:303`), and `_fetch(cfg, repo)` (`merge.py:256`). To fetch "the remote the record names", Do has to pass that remote (or `d`) through all three, which changes their signatures. The C4 gate keeps the new test and reverts the production code. On that revert, a test that calls the new signature fails with `TypeError`, not with the "git failed … exited 128" RED the brief promises (brief line "Pre-fix, (1) returns `behind=None` with "git failed""). The brief should do one of two things. Either fix the new parameter shape in advance, for example an optional keyword like `remotes=()` that defaults to today's behaviour so the pre-fix call still runs, or drive the RED through `_merge_one(cfg, d, …)`, whose signature does not change. Otherwise the falsifiability claim cannot be checked.
- [ ] **The brief does not say what happens when a `"stacked"` record names no remote.** `_published_ref` returns `None` for a stacked record whose `base` does not end in `/<branch>` (`integrate.py:153-157`). It also returns `None` for an older record with no `branch`. The brief says to keep every read fail-closed (`merge.py:259-262`) but does not say whether this case should quietly fall back to `base_remote`+`origin` (today's behaviour, which then ends in the criterion-(2) message) or refuse up front. The two choices behave differently. If the brief does not decide, Do will choose without telling anyone. The planner should pick one and add a criterion for it.
- [ ] **Criterion (3) may not be checkable by the existing tests.** "a `new-pr` / `stacked-pr` record … fetches exactly what it fetches today" is what keeps behaviour unchanged for the common path. But `test_merge.py`'s `_gh` stub makes every `git` call succeed (`test_merge.py:85-99`), and none of the `_base_read`/`_fetch` call sites in that file are named in the brief. "Every existing test still passes" therefore may not prove that the fetch list is unchanged. The brief should require a test that asserts the `git fetch` argv list for a `new-pr` record (`origin` + base remote only, in today's order), or name the existing test that already does.

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
- Iteration delta (if iterating): Auto-iterate (round 1): rebuilding for the implementation-level findings — T5 Judgment — Correct the unsupported explanation of a missing head — an actually fetched, correctly recorded remote with a restricted refspec is falsely blamed as absent, sending operators toward the wrong repair (`target/template/src/pdca_harness/merge.py:287`, `review-diagnostic.log:5`).; `template/src/pdca_harness/merge.py:287-289`: the `_have` refusal always ends with "the remote its branch was pushed to is not among them (or its publish record does not name it)". For a `new-pr` / `stacked-pr` record, the branch's remote (`origin`) *is* in the fetched list. A missing head there means something else, such as a force-push between the `gh pr view` read and the fetch, or a host reporting a commit no remote has yet. So the second clause is wrong for that case and sends the operator looking in the wrong place. Fix: add that clause only when `integrate._published_ref(d)` returned None or named a remote outside `remotes`, or reword it neutrally, e.g. "none of these remotes has it".. Deferred, not addressed here: 4 finding(s) that need human judgment, held in deferred-findings.json for the human at handover — not build work
- By / date: auto-iterate / 2026-10-10

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 4 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
