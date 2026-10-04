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

Review issue #531: prevent merge-mode waves from merging stale-base PRs by updating their branches, waiting for the updated head, and pinning each merge to the verified head.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The stale second-member failure and late-update carry-forward have observable acceptance cases, with the non-strict last-read race explicitly bounded in scope; `target/template/tests/test_merge.py:923`, `target/template/tests/test_merge.py:1003`, `target/template/pdca.toml.jinja:132`. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only production preserves the regression tests and reproduces B merging without an update: 49 tests run, 76 assertion/subtest failures; `review-red.log:66`, `review-red.log:771`; production scenario at `target/template/tests/test_merge.py:923`. |
| C3 Change | PASS | The tested sequence addresses stale combinations while preserving host-trusting required mode, refusal cleanup, and resume behavior; delayed updates and pin refusals are covered; `target/template/src/pdca_harness/merge.py:413`, `target/template/tests/test_merge.py:988`, `target/template/tests/test_merge.py:1003`. |
| C4 Verification (red→green) | PASS | Independent production stash/pop reproduces red→green: all 49 merge tests pass after restoration, matching the frozen gate; this confirms the offline contract, not live GitHub behavior; `review-green.log:3`, `gate-logs/C4-verify.log:812`, `target/template/tests/test_merge.py:910`. |
| C5 Causal adequacy | PASS | Updating the stale combination and checking the verified head addresses the cause; no optional-capability probe or load-time symptom guard was introduced, and the tests invoke production merge_wave; `target/template/src/pdca_harness/merge.py:424`, `target/template/src/pdca_harness/merge.py:476`, `target/template/tests/test_merge.py:915`. |
| T1 Structure | PASS | The change stays within merge orchestration, its existing tests, and related documentation; it shares the existing rollup wait and refusal behavior rather than introducing a parallel gate; `target/template/src/pdca_harness/merge.py:303`, `target/template/src/pdca_harness/merge.py:355`, `target/template/src/pdca_harness/merge.py:451`. |
| T2 Shape | PASS | Independent docs lint, 22-page site render/link audit, and git diff --check pass; documentation identifies the changed sign-off boundary and the strict-protection recommendation; `target/template/docs/fork-discipline.md.jinja:67`, `target/template/pdca.toml.jinja:132`; frozen parity evidence at `gate-logs/host-ci-docs.log:10`. |
| T3 Runtime | PASS | Independent driver suite passes 2,314 tests with two skips; the frozen root suite actually ran 24 tests successfully, while this review host cannot import Copier and exits 77 for that suite; `review-suite.log:1798`, `gate-logs/T3-suite.log:54`, `review-root-suite.log:6`. |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; their substantive audit is owed to the mandatory publish rerun, not human clearance here; `gate-logs/T4-contribution.log:10`. |
| T5 Judgment | NEEDS-HUMAN | Confirm no superseding or rejected work across all five affected paths — the brief records partial path-based prior art, but the supplied target has one synthetic commit and no remotes, so full coverage cannot be independently established from these artifacts; `brief.md:153`, `review-history.log:1`. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether offline evidence suffices for unattended merges and accept the remaining non-strict race and CI-only combination review — real GitHub update/check/pinning and strict-protection behavior were not exercised; evidence uses mocked git/gh despite “External dependencies: none”; `target/template/tests/test_merge.py:910`, `target/template/docs/fork-discipline.md.jinja:67`, `target/template/pdca.toml.jinja:132`. |

No confirmed patch defect found. These verdicts are advisory; deterministic gates retain their own authority.

Independent verification used the supplied disposable target only. Its synthetic base identifies the brief's c67a14d base, and the patch is applied; no target-state staleness was found. I stashed only `template/src/pdca_harness/merge.py`, ran `PYTHONPATH=src python3 -m unittest tests.test_merge` from `target/template`, restored the stash, and reran the same command. The original five-file patch remains restored. Temporary test files were directed into this review sandbox.

The production-import scanner was rerun. Its heuristic only checks newly added test files, so its success is vacuous for this edit to an existing test file, as the frozen C5 log explicitly reports (`gate-logs/C5-prod-path.log:10`). Direct inspection and the independent red→green run establish that the new cases call production instead. All six named frozen gate logs were available; no missing-oracle escalation is warranted. The local Copier limitation is a review-host caveat, not a patch defect or an unmet dependency in the frozen root-suite run. The supplied INTEGRATION template leaves project-specific human-only items unenumerated (`target/template/docs/INTEGRATION.md.jinja:80`).

For the live-host validation decision, the runnable offline starting point is:

```sh
cd target/template
PYTHONPATH=src python3 -m unittest tests.test_merge.MergeAgainstCurrentBase
```

This exercises stale second members, delayed and never-completed updates, red updated heads, moved heads/base, strict-host simulation, and unchanged required mode. To obtain supplementary live evidence, a maintainer should use a disposable GitHub repository with two independently green PRs against the same base and run its configured merge-mode wave with `merge_requires = "all"`. After A merges, observe B receive a merge-commit update, new-head CI complete, and a merge command pinned to that updated SHA. Repeat with strict protection enabled; both members should complete. Make B's updated CI fail and confirm B returns to draft and later waves stop. Existing project rules reserve live ready/merge actions to the maintainer; no live PR was readied or merged during this review.

Prior-art investigation: `git log --all --oneline --` over all five affected paths returns only `ea2d44e pre-fix base c67a14d...`; `git remote -v` is empty. The brief lists merged history for merge.py and reports closed-unmerged searches for merge.py/flow.py/integrate.py/waves.py, but does not supply equivalent evidence for the affected tests/config/docs. The human decision concerns that missing historical coverage, not an assertion that conflicting prior art exists.

### Advisory — code-review

# Advisory code review — issue 531 (merge-mode stale base)

Lens: bugs the patch introduces, plus reuse / simplification / efficiency. Advisory only.
Line numbers are from the patched target at `$PDCA_TARGET`.

Overall: no correctness bug found on the main path. Ready → base read → `update-branch` →
poll until the update lands → bounded rollup wait with `spent` → re-read head and base →
pinned merge. Every new refusal goes through `_undo_ready`. The shared budget holds: in
`_wait_for_update` the sleeps never add up to more than `wait_secs`
(`template/src/pdca_harness/merge.py:331-337`), and `_wait_for_green` starts its count at
`spent` (`merge.py:204`). Gates C4 and T3 pass (gate-logs). The findings below are edge
cases and cleanups.

## Correctness / edge cases

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/merge.py:256-263`: `_fetch` only fetches
  `cfg.base_remote` and `origin`. A PR published by `publish._publish_stacked` is pushed to
  the brief's `Onto branch` remote (`template/src/pdca_harness/publish.py:484`,
  `git push <remote> HEAD:<branch>`), and that remote can be a third one. After
  `gh pr update-branch`, the new merge commit exists only on that remote. `_contains` then
  sees git exit 128 ("not a valid commit") and the run refuses with "git failed", which is
  misleading. This is fail-closed, so nothing merges wrongly, but such a PR can never merge
  in merge mode once it is behind. Either fetch the remote the publish record names, or
  make the message say that the head commit is not in the checkout. If `Onto branch` can't
  happen in merge mode, ignore this.
- `template/src/pdca_harness/merge.py:321-334`: when the head changes to a commit that still
  lacks `tip` (someone pushed to the PR during the update wait, or the update was replaced),
  the loop keeps polling and then refuses with "its update had not landed". That message is
  wrong for this case. The result is still fail-closed. Low priority: a separate message
  for "the head moved but still lacks the base tip" would save a human some confusion.
- `template/src/pdca_harness/merge.py:452-460`: after an update, the "pending"/"empty"
  refusal text still says "within {merge_wait_secs}s". Part of that budget went to the
  update wait (`spent=waited`, `merge.py:451`), so the rollup wait got less than that. This
  only affects the message, but the "raise merge_wait_secs" hint is the action the user
  needs, so it should say that the update wait used part of the budget.
- `template/pdca.toml.jinja` (the `merge_wait_secs` `0` bullet, unchanged by the patch):
  with `merge_wait_secs = 0`, a PR that is behind is now refused almost every time.
  `_wait_for_update` reads once (`merge.py:331`), and GitHub usually applies the update
  asynchronously. Even if it landed at once, the single rollup read of a brand-new head is
  `empty`. The new comment block says the update wait shares the budget, but the `0` line
  still reads as "the original immediate-refusal behaviour". It should also say that `0`
  means any wave member after the first gets refused. This is a docs gap, not a code bug.

## Reuse / simplification / efficiency

- `template/src/pdca_harness/merge.py:288-296` (`_base_read`): fetch, then
  `rev-parse --verify --quiet <ref>^{commit}`, is the same thing `publish._pinned_base`
  already does (`template/src/pdca_harness/publish.py:946-962`), including the
  "does not resolve after the fetch" failure. `_base_read` could call
  `publish._pinned_base(repo, cfg.base_remote, f"{cfg.base_remote}/{base}")` and fetch
  `origin` separately. The same goes for `_git` / `_git_failed` (`merge.py:246-253`), which
  repeat the "last stderr line" pattern of `publish._line_tip_refusal` / `_pinned_base`.
  This is optional; the module already calls `publish._checkout_path`, so the dependency
  exists.
- `template/src/pdca_harness/merge.py:355-362`: the new `_refuse` helper is used only by
  the new paths. The rollup refusal (`merge.py:461-469`) and the `gh pr merge` failure
  (`merge.py:493-500`, edited in this diff) still repeat the same print → `_undo_ready` →
  `return 1` sequence inline. They could call `_refuse` with their own `why` text. This is
  cosmetic; the separate refusal messages that existing tests check would need to stay.
- Efficiency: under `"all"`, each PR now runs `_base_read` twice. That is two `gh pr view`
  calls plus up to two `git fetch` calls each time (`merge.py:285-288`, `:476`), then more
  fetches for every new head seen in `_wait_for_update` (`merge.py:322`), then the existing
  post-merge fetch (`merge.py:502-506`). This is per PR, not in a hot loop, so it costs
  little. The second `_base_read` could skip the `origin` fetch, because it only needs the
  base tip, and the head is checked by SHA equality with a commit already fetched. Not
  worth a round on its own.

## Tests

- `template/tests/test_merge.py` (new `_Host` / `MergeAgainstCurrentBase`): the fake is
  stateful, keyed by distinct PR URLs, and drives the production `merge.merge_wave`. It
  covers brief cases (a), (b) (the push both after the green read and at merge time) and (c)
  (exact call log for `"required"`). It also covers the iteration-1 carry-forward cases:
  the update landing late, the update never landing, and a red updated head marked by a
  fake option instead of a hard-coded SHA. No weak or vacuous test found. One gap: no test
  hits the new `repo_spec` refusal (`merge.py:420-422`, "publish record names no repo").
  Publish always writes `repo` (`publish.py:421`, `:541`), so this is low risk.
- The C5 gate log only says "patch adds no new test file — nothing to assert". The tests
  were appended to an existing file, so that gate checked nothing here. By reading the
  code, the new tests import only `merge` and patch `subprocess.run` / `_sleep`, so they do
  exercise the production code.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — Confirm no superseding or rejected work across all five affected paths — the brief records partial path-based prior art, but the supplied target has one synthetic commit and no remotes, so full coverage cannot be independently established from these artifacts; `brief.md:153`, `review-history.log:1`.
- [x] Validation — fitness-to-purpose — Decide whether offline evidence suffices for unattended merges and accept the remaining non-strict race and CI-only combination review — real GitHub update/check/pinning and strict-protection behavior were not exercised; evidence uses mocked git/gh despite “External dependencies: none”; `target/template/tests/test_merge.py:910`, `target/template/docs/fork-discipline.md.jinja:67`, `target/template/pdca.toml.jinja:132`.
- [x] `template/src/pdca_harness/merge.py:256-263`: `_fetch` only fetches `cfg.base_remote` and `origin`. A PR published by `publish._publish_stacked` is pushed to the brief's `Onto branch` remote (`template/src/pdca_harness/publish.py:484`, `git push <remote> HEAD:<branch>`), and that remote can be a third one. After `gh pr update-branch`, the new merge commit exists only on that remote. `_contains` then sees git exit 128 ("not a valid commit") and the run refuses with "git failed", which is misleading. This is fail-closed, so nothing merges wrongly, but such a PR can never merge in merge mode once it is behind. Either fetch the remote the publish record names, or make the message say that the head commit is not in the checkout. If `Onto branch` can't happen in merge mode, ignore this.
- [x] **The brief does not cover `merge_requires = "required"`.** The criterion says "for every PR `merge_wave` merges, the head commit that merges is the head whose rollup was read green". Under `merge_requires = "required"`, `_merge_one` reads no rollup at all (`merge.py:259` skips the whole gate), so this clause cannot hold on that path. The brief also never says whether update-branch runs there. If it doesn't, `required` + `strict: false` still merges a stale base, and `required` + `strict: true` still stops after the first merge, which is the exact defect. The planner has to pick a side. Option 1: update-branch runs on both paths, and on the `required` path the merge just waits on the host's checks. Option 2: `required` explicitly keeps the stale-base behaviour, and the brief says so in out-of-scope and in the config comment. Either way the criterion's wording must be corrected and a test added for the chosen side.
- [x] **"Contains the base's tip as it stood at merge time" promises something the driver can't guarantee.** The criterion asks that the merged head "contains the base's tip as it stood at merge time", and that "on a host with `strict: false` no stale-base merge happens". The brief itself admits the base can move "for any other reason", for example outside pushes. A client-side driver can't rule out a move between its last behind/rollup read and `gh pr merge` (`merge.py:264` → `:287`). On `strict: false` only the host (strict mode or a merge queue) could close that window. As written, the criterion is unfalsifiable at Check and wrong in the race window. Restate it as: no merge on a head that was behind *at the driver's last read immediately before `gh pr merge`*. Then list the remaining race as accepted, or as a reason to recommend `strict: true`.
- [x] **No test covers "cannot land a head other than the one verified".** Scope says "the merge itself cannot land a head other than the one verified". The criterion says "the head that merges is the head whose rollup was read green". The test described only asserts update → green read → merge order. `_check_rollup` (`merge.py:108`, `gh pr checks --json name,bucket`) returns no head SHA, so reusing `_wait_for_green` unchanged, as the brief requires at "Citations expected", ties the verdict to no commit at all. Three ways around it:
- [x] **The test-fake guidance contradicts itself.** The Falsifiability section says to "keep the fake answering by command shape (as `_gh` does), not by call order". But the scenario is order-dependent by nature: B must read as behind only *after* `gh pr merge A`, and its rollup must describe the *new* head only after the update. `_gh` (`test_merge.py:67-71`) keys on `cmd[2]` alone, returns the same answer for every PR, and the bundle fixture defaults every bundle to the same `pr_url` (`test_merge.py:91`). Tell Do to write a stateful fake keyed by PR URL that flips B to behind when it sees a merge of A. Also require distinct `pr_url`s for A and B. Without both, the RED can pass or fail for the wrong reason.
- [x] **The doc edit is left conditional when it is already known to be needed.** The brief says to touch `fork-discipline.md.jinja:51-59` "if it describes the merge steps". It does: lines 57-58 say the driver reads the rollup "after the ready-mark and immediately before the merge". The new update-branch → re-wait step changes that sequence. Make the edit mandatory (and the range `:51-60`) so Check can verify it, rather than leaving it to Do's judgment.
- [x] **Nobody signs off on the fact that the merged tree is not the reviewed patch.** After `gh pr update-branch`, the PR head that merges is a new merge commit (or a rebase) that Check never reviewed. `patch.diff` / `publish.json` describe the pre-update head. That is arguably the point, since CI verifies the combination. But it is a change in what "accepted at sign-off" covers, and in merge mode the readiness is driver-granted (`fork-discipline.md.jinja:51-56`). The brief should say so explicitly. It should also say whether a rebase-style update (rewritten history, so no longer the reviewed commits) is allowed under `merge_method = "rebase"`, rather than leaving the choice of update style to Do.

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
- By / date: Eduard Ralph / 2026-10-04

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 6 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
- issue 531: merge mode `_fetch` fetches only `base_remote` + `origin`; a PR pushed to a third `Onto branch` remote cannot merge once behind (fails closed with a misleading "git failed") — fetch the publish record's remote or fix the message.
