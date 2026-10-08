# Result — issue 647 / stack-holds-dependent-of-out-of-batch-unmerged-prereq

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: In stack mode a dependent whose plain `Depends on` prerequisite is NOT one of
  the ids the run was asked to drive is built on a base missing that prerequisite, whenever
  the prerequisite is COMPLETE but its PR has not merged into the target base. `_runnable`
  accepts an out-of-batch prerequisite once it is COMPLETE
  (`template/src/pdca_harness/flow.py:710`); COMPLETE means only "a draft PR was opened",
  and nothing in the run carries an out-of-batch prerequisite's work into the base (the
  docstring says so, `flow.py:692-698`). Child-1 fixes this for the same ids re-issued; it
  cannot reach (i) the `flow_batch` sweep path, which gets a fresh line every run by design
  (finished bundles leave the sweep, `flow.py:2160-2170`), or (ii) a dependent driven in a
  different command from its prerequisite. Separately, `merged.is_merged`
  (`merged.py:32-59`) returns True for any PR whose state is MERGED, without checking it
  merged into the target base: a `"stacked-pr"` record whose PR targets an integration branch
  (`publish.py:420-421`, `"base": pr_base`), or an `Onto branch` record (`"stacked"`,
  `publish.py:540-541`), can be MERGED while the target base lacks its work — so even
  `Depends on (merged)` (#186) can be satisfied by a merge that never reached the base. And
  `is_merged` calls `gh` with no `OSError` guard (`merged.py:50-51`), so a missing `gh`
  crashes the run with a traceback.
- Success criterion: With the patch, in stack mode with publishing on: (1) a run that
  drives `D` (`- **Depends on:** P`) where `P` is NOT in the run's requested batch, is
  COMPLETE, has a non-empty `patch.diff` and a resolvable target, and its PR is OPEN, does
  NOT build `D`: `D` stays PLANNED, one stderr line names `D`, `P` and the reason — it must
  contain the substring `not merged into main` (`main` being `D`'s target base), which
  today's generic "prerequisite(s) not ready" line does not — with advice
  (name `P` in the same `pdca flow <ids>` command so its line carries it, or wait until its PR
  merges into the base), and an unrelated bundle `U` in the same run builds as today.
  Pre-fix `D` is built — RED. Shown for both entry points: `flow_ids` (named ids not
  including `P`) and `flow_batch` (sweep, `P` already COMPLETE). (2) `P`'s PR MERGED with its
  record's `base` equal to the target base and mode not `"stacked"` ⇒ `D` builds on the base
  as today. (3) `P`'s PR MERGED but its record's `base` is another branch (a `"stacked-pr"`
  record against an integration branch — e.g. #591's own record today: `"mode":
  "stacked-pr"`, `"base": "pdca-integration/main"`) or mode `"stacked"`, or its record's
  `repo` differs from `D`'s target repo ⇒ `D` is held, as in (1); in `_runnable` the same
  rule now also governs `Depends on (merged)` — a `Depends on (merged): P` dependent waits in
  this case too, and still builds once `P` merged into `D`'s base. (4) `P` COMPLETE
  with an empty or missing `patch.diff` ⇒ `D` builds (nothing to wait for). (5) `gh` missing
  (`OSError`) or failing while reading `P`'s PR ⇒ `D` held, named, no traceback; the run goes
  on. (6) Unchanged: a prerequisite in the run's requested batch (child-1's carry), `Stacks
  on` edges, `--no-publish` runs, merge mode, and a dry-run (stub publisher; asks no host,
  holds nothing). `merged.is_merged` itself is NOT changed: its other callers — merge mode's
  resume check (`merge.py:233`) and `status`'s `_blocked_by` (`cli.py:1084`) — keep today's
  answer; a test asserts `merged.is_merged` still returns True for a MERGED `"stacked"`
  record (the merge-mode resume case).
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: In stack mode with publishing, hold a dependent whose plain `Depends on`
  prerequisite is outside the run's requested batch and not merged into the target base,
  instead of building it. Add a new function in `merged.py` (beside `is_merged`, e.g.
  `merged_into(cfg, dep_id, repo, base)`) that `_runnable` alone calls for out-of-batch
  prerequisites — both plain `Depends on` (stack mode, publishing) and `Depends on (merged)` —
  passing the DEPENDENT's resolved target (`publish._resolve_target(D)`). It counts MERGED
  only when the record's `repo` and `base` equal that target and mode is not `"stacked"`, and
  reads `gh` failures — including a missing `gh` (`OSError`) — as "not merged" with a
  message, never a traceback. Leave `merged.is_merged` and its callers (`merge.py:233`,
  `cli.py:1084`) unchanged. Update `_runnable`'s docstring and the stack-mode paragraph in
  `docs/07-crosscutting.md` (near `:658-677`) to say a `Depends on` prerequisite outside the
  run's ids now waits for its merge.
  / out of scope: carrying out-of-batch prerequisites onto the line (rejected in
  iteration-v1..v3 — do not reintroduce); in-batch / re-issued prerequisites (child-1);
  `Stacks on` (#123, unchanged); merge mode (#531) and `--no-publish`; changing which ids the
  sweep path includes; changing `merged.is_merged` or the `status` display.

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

Review issue #647: hold stack-mode dependents whose out-of-batch prerequisites have not merged into the dependent’s target base, while preserving targetless and not-ready behavior.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief gives falsifiable readiness, diagnostic, and compatibility criteria, including the two carry-forward regressions; the target implements the same target/state distinctions (`brief.md:26`, `brief.md:144`, `target/template/src/pdca_harness/flow.py:723`). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only production changes makes the 31 new tests fail with 11 assertion failures and 2 missing-gh errors; both entry points wrongly build D before the fix (`reviewer-red.log:202`, `target/template/tests/test_flow_out_of_batch_prereq_hold.py:201`). |
| C3 Change | PASS | The readiness change stays within the requested scope: targetless dependents retain their old answer and non-COMPLETE prerequisites receive the not-ready reason; merge/status callers retain is_merged (`target/template/src/pdca_harness/flow.py:731`, `target/template/src/pdca_harness/merged.py:104`, `target/template/src/pdca_harness/merge.py:387`, `target/template/src/pdca_harness/cli.py:1084`). |
| C4 Verification (red→green) | PASS | Restoring the production stash makes all 31 regression tests pass; this independently reproduces the frozen gate’s behavioral red→green, including missing-gh handling (`reviewer-green.log:3`, `reviewer-red.log:204`, `gate-logs/C4-verify.log:1123`). |
| C5 Causal adequacy | PASS | Readiness now rejects a COMPLETE prerequisite whose work is absent from the dependent’s target; actual production flow fails before the fix and passes after it. This is a dependency precondition, not a capability probe masking a load-time cause (`target/template/src/pdca_harness/flow.py:736`, `target/template/src/pdca_harness/merged.py:104`, `target/template/tests/test_flow_out_of_batch_prereq_hold.py:129`). |
| T1 Structure | PASS | Both entry points share the readiness rule and reuse the existing fold-candidate, target-resolution, and PR-state helpers, keeping the merge/status contract separate (`target/template/src/pdca_harness/flow.py:2163`, `target/template/src/pdca_harness/integrate.py:161`, `target/template/src/pdca_harness/merged.py:97`). |
| T2 Shape | PASS | Independently rerun docs lint, site rendering/internal-link audit, production-import scanner, and git diff --check all pass; documentation explains the operational hold and exceptions (`target/docs/07-crosscutting.md:704`, `gate-logs/T2-docs.log:11`, `gate-logs/host-ci-docs.log:14`). |
| T3 Runtime | PASS | Independent driver-suite rerun passes 2,369 tests with 2 skips; frozen root-suite evidence shows 24 tests passing, including real Copier render/update cases, which this reviewer’s interpreter cannot rerun (`reviewer-suite.log:1797`, `gate-logs/T3-suite.log:38`, `gate-logs/T3-suite.log:54`, `reviewer-root-suite.log:6`). |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the substantive user-impact/tracker-reference audit must rerun at publish (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Confirm the claimed path-based merged-history and closed/rejected-work review is sufficient to rule out superseding or rejected work — the supplied snapshot exposes only one synthetic base commit and no remotes, so the brief’s historical claims cannot be independently confirmed (`brief.md:114`, `reviewer-prior-art.log:1`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether holding these dependents and the offered carry-or-wait recovery meet the intended workflow — both entry points behave correctly offline, but live-host/operator fitness remains a sign-off decision (`target/docs/07-crosscutting.md:704`, `target/template/tests/test_flow_out_of_batch_prereq_hold.py:201`, `target/template/tests/test_flow_out_of_batch_prereq_hold.py:207`). |

Independent verification used the disposable `$PDCA_TARGET` at `target/`; all source citations above resolve there. Production changes in `flow.py` and `merged.py` were stashed while the regression tests remained available, then restored before the green run and broader checks. No target-state caveat or confirmed patch defect was found. The supplied patch remains applied.

The focused command was `cd target/template && PYTHONPATH=src python3 -m unittest tests.test_flow_out_of_batch_prereq_hold`. The broader command was `PYTHONPATH=src python3 -m unittest discover -s tests` from the same directory. Both used `TMPDIR` inside this review workspace. Frozen C4 also includes an expected red-leg error from an existing test mocking the newly added symbol; the independent new-test-only red leg establishes behavioral failures without relying on that error.

The root-suite rerun exited 77 because this interpreter cannot import Copier (`reviewer-root-suite.log:6`). This is a reviewer-host limitation, not a patch failure or an unsatisfied dependency in the frozen gate: `gate-logs/T3-suite.log:38` shows the render tests executing, and `gate-logs/T3-suite.log:42` shows update compatibility executing. The brief declares no external dependencies. The deliberate gh stub permits the forbidden OPEN/wrong-base states and demonstrates the pre-fix failures; it establishes offline readiness behavior, not a live GitHub integration claim.

The prior-art investigation ran by both affected production paths. Its complete local result is one synthetic commit (`9d6d6a8`, pre-fix base `c1f2306984bb9b95469b08de3cea83598d48820f`) and no configured remotes (`reviewer-prior-art.log:2`). The brief names closed-unmerged work, but no independent closed/rejected-work evidence is supplied. The available integration template leaves project-specific human-only items as TODO (`target/template/docs/INTEGRATION.md.jinja:80`); no additional instantiated ruleset is in the supplied inputs.

### Advisory — code-review

# Advisory code review — issue_647

Line numbers are from the patched tree at `$PDCA_TARGET`. Gates: C4 shows red before the fix and green after (gate-logs/C4-verify.log), and T3 passes. The new test file covers the brief's cases (1)–(6) and the two items carried forward from iteration 1: an empty target, and a PLANNED or DISCONTINUED `Depends on (merged)` prerequisite. I found no crash or traceback path. Findings:

- NEEDS-HUMAN — **A prerequisite in another repo is held forever.** `template/src/pdca_harness/flow.py:736-750` together with `template/src/pdca_harness/merged.py:104`. Say D targets `org/repo @ main` and its plain `Depends on` prerequisite P targets `org/other @ main`. Then `cand` is not empty, because P has its own usable target. `merged_into` then compares P's record `repo` with D's repo, and that check can never pass. P's PR can merge into `org/other` and D still waits on every later run. Its message says "wait until their PR merges into main", which will never happen. `Depends on (merged)` across repos is also a behaviour change: before this patch any merge counted (`is_merged`), and now it never does. The brief's case (3) does ask to hold when the record's `repo` differs. But it is unclear whether a cross-repo edge, which no fold ever puts on D's line, should wait at all, or count P's merge into P's *own* target. The only test is `test_a_prereq_for_another_target_is_held_without_the_carry_advice` (`template/tests/test_flow_out_of_batch_prereq_hold.py:213`). It only covers the OPEN case and does not show the permanent hold after a merge.
- NEEDS-HUMAN [impl] — **A publish record with no `repo` key is never treated as merged.** `template/src/pdca_harness/merged.py:104` checks `rec.get("repo") != repo`, so a `publish.json` without a `repo` key fails the check even after its PR merged into D's base. Elsewhere the code treats a missing `repo` as "same repo": see `publish.py:798`, `rec.get("repo", repo_spec) == repo_spec`, and the defaults in `revert.py:101` and `merge.py:376`. That suggests such records exist. If they do, the dependent of an old prerequisite is held for good. Fix: `rec.get("repo", repo)`, or document why the stricter check is wanted. Add a test either way.
- **The hold message can be wrong for a carried `Depends on (merged)` prerequisite.** `template/src/pdca_harness/flow.py:758`. Take an out-of-batch `Depends on (merged)` prerequisite that is a finished named id, which `_carry_finished` did put on the line. It is still (correctly) held until merged. But the message says "no line of this run carries them", which is false here. Wording only; holding it is correct.
- **Some held cases print two stderr lines, not one.** `template/src/pdca_harness/merged.py:99-100` and `:107-109` print their own `merged:` line, then `flow.py:758` prints the `flow: … held` line. The brief asks for one line naming D, P and the reason. The required substring is on the `flow:` line, so the tests pass, but the reason ("merged into X instead", "gh failed") is only on the separate line. Minor.
- **Reuse: the first part of `merged_into` copies `is_merged`.** `template/src/pdca_harness/merged.py:85-95` repeats `merged.py:45-54`: the COMPLETE check, the empty-patch check, and the `pr_url` lookup. A small shared helper would stop them drifting apart. The brief keeps `is_merged`'s behaviour fixed, so this is optional.
- **Efficiency: the PR state is not cached.** `flow.py:743` calls `merged_into`, and so `gh pr view`, once per dependent per out-of-batch prerequisite. A run where several dependents share one prerequisite makes repeated network calls for the same PR. This is small at today's batch sizes. A per-run cache keyed by `pr_url` would remove the repeats.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — Confirm the claimed path-based merged-history and closed/rejected-work review is sufficient to rule out superseding or rejected work — the supplied snapshot exposes only one synthetic base commit and no remotes, so the brief’s historical claims cannot be independently confirmed (`brief.md:114`, `reviewer-prior-art.log:1`).
- [x] Validation — fitness-to-purpose — Decide whether holding these dependents and the offered carry-or-wait recovery meet the intended workflow — both entry points behave correctly offline, but live-host/operator fitness remains a sign-off decision (`target/docs/07-crosscutting.md:704`, `target/template/tests/test_flow_out_of_batch_prereq_hold.py:201`, `target/template/tests/test_flow_out_of_batch_prereq_hold.py:207`).
- [x] **A prerequisite in another repo is held forever.** `template/src/pdca_harness/flow.py:736-750` together with `template/src/pdca_harness/merged.py:104`. Say D targets `org/repo @ main` and its plain `Depends on` prerequisite P targets `org/other @ main`. Then `cand` is not empty, because P has its own usable target. `merged_into` then compares P's record `repo` with D's repo, and that check can never pass. P's PR can merge into `org/other` and D still waits on every later run. Its message says "wait until their PR merges into main", which will never happen. `Depends on (merged)` across repos is also a behaviour change: before this patch any merge counted (`is_merged`), and now it never does. The brief's case (3) does ask to hold when the record's `repo` differs. But it is unclear whether a cross-repo edge, which no fold ever puts on D's line, should wait at all, or count P's merge into P's *own* target. The only test is `test_a_prereq_for_another_target_is_held_without_the_carry_advice` (`template/tests/test_flow_out_of_batch_prereq_hold.py:213`). It only covers the OPEN case and does not show the permanent hold after a merge.
- [x] **A publish record with no `repo` key is never treated as merged.** `template/src/pdca_harness/merged.py:104` checks `rec.get("repo") != repo`, so a `publish.json` without a `repo` key fails the check even after its PR merged into D's base. Elsewhere the code treats a missing `repo` as "same repo": see `publish.py:798`, `rec.get("repo", repo_spec) == repo_spec`, and the defaults in `revert.py:101` and `merge.py:376`. That suggests such records exist. If they do, the dependent of an old prerequisite is held for good. Fix: `rec.get("repo", repo)`, or document why the stricter check is wanted. Add a test either way.
- [x] **The brief changes `merged.is_merged` for every caller, but says merge mode stays the same.** Scope says "make `merged.is_merged` count MERGED only for a PR merged into the target base … mode not `"stacked"`". Criterion (6) says merge mode (#531) is "Unchanged". But `is_merged` has two other callers that the brief never names:
- [x] **"Target base resolved for the bundle" is ambiguous, and `is_merged` can't see the dependent.** `is_merged(cfg: Config, dep_id: str)` (`merged.py:32`) only gets the prerequisite's id. The Invariant says "merged into the **dependent's** target base". The Scope says "record `base` equals the target base resolved for the bundle", which reads as the prerequisite's own `_resolve_target`. These two give different answers when P and D target different bases or repos.
- [x] **The main "merged elsewhere" case in the brief mostly can't happen on the current code.** The Defect says a `"stacked-pr"` record "whose PR targets an integration branch (`publish.py:420-421`, `"base": pr_base`)" can be MERGED without reaching the base. But `publish.py:282` sets `pr_base = stack_branch if (stack_branch and own_repo and not wave_stacked) else base`, and `publish.py:266-268` explains why: a wave stack-base bundle "opens its PR against its REAL target base … (#593)". `cli.py:1065-1067` says the same: "every PR targets the real base (#593), so it reads ↑main".
- [x] **This is two or three fixes, not one.** These are separate changes:
- [x] **Dependency 646 is still PLANNED, and the "requested batch" idea doesn't exist yet.** `dependency-state.json` shows `"646": {"declared": "Depends on", "exists": true, "state": "PLANNED"}`. The Ordering note says this child "needs child-1's 'requested batch' notion". The target `flow.py` has no such idea yet: `_runnable(cfg, wave, batch_names, *, held=…)` at `flow.py:681-682` only has `batch_names`. Do can't start until 646 is COMPLETE and folded in.
- [x] **Criterion (1)'s message wording isn't specified tightly enough to test.** "one stderr line names `D`, `P` and the reason, with advice (name `P` in the same `pdca flow <ids>` command … or wait until its PR merges)". Today `_runnable` already prints one generic line per skipped bundle (`flow.py:715-716`: "skipped — prerequisite(s) not ready (P)"). So a test that only checks for `D` and `P` passes against the existing message. The brief should name a distinctive substring the test must assert, for example the advice text. Otherwise the "message" part of RED→GREEN is satisfied by code that already exists.

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
