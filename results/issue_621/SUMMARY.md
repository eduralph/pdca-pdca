# Result — issue 621 / merge-confirm-requires-complete-rollup

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: In merge mode under `merge_requires = "all"` (any value but `"required"`, `template/src/pdca_harness/merge.py:413`), `_wait_for_green` (`merge.py:172-224`) believes a green rollup once a second read one poll interval (15 s) later is also green (`merge.py:220-224`). It compares only the verdict, never which checks were present: its own docstring says so (`merge.py:192-194`, "This compares verdicts only, not check names: a slow job that has not registered within one poll interval still gets through"). `_check_rollup` (`merge.py:111-159`) returns only `(verdict, detail)`, so the names are dropped. So `green(dco)` → `green(dco)` merges on a partial rollup when a slow `e2e` job registers later, and `green(dco)` → `green(dco, e2e)` "confirms" on a different set of checks. PR #617's own description says it "narrows #582 but does not fully close it".
- Success criterion: With the patch, `merge._wait_for_green` (and so `_merge_one`), with `_sleep` patched and `_check_rollup`'s `gh pr checks` reads scripted:
  (1) **Expected checks declared.** With the new optional `[driver]` setting naming the checks a rollup must contain (e.g. `["dco", "e2e"]`), the reads `green(dco)` → `green(dco)` → … up to `merge_wait_secs` never return `green`: the wait ends `pending` with a detail naming the missing check `e2e`, and `_merge_one` refuses (no `gh pr merge`, PR returned to draft as on every refusal). Once `e2e` registers and passes, two consecutive green reads with the same names return `green`. A declared check is "present and passing" when it reports a bucket `_check_rollup` already counts as green-compatible (`pass` or `skipping`, where gh reports skipped and neutral checks as `skipping`: `_ROLLUP_OK`, `merge.py:90-95`), so a declared `e2e` that reports `skipping` (e.g. a path filter) does not block. (1b) **Single read.** With the same declared list and `merge_wait_secs = 0` (a documented value, `pdca.toml.jinja:193`), the single `green(dco)` read returns `pending` with a detail naming `e2e`, and `_merge_one` refuses: the declared list applies on the `wait_secs <= 0` path (`merge.py:201-203`) too, not only inside the loop.
  (2) **Names compared.** With nothing declared, `green(dco)` → `green(dco, e2e)` does NOT return `green` on the second read: a confirm read whose check names differ from the first green read's is not a confirmation, and the wait goes on. Names are compared as a multiset (each name with its count), so `green(build)` → `green(build, build)` (the same job name in two workflows, or a re-run listed twice) is also not a confirmation. A later read with the same names as that one (`green(dco, e2e)`) confirms it.
  (3) **Unchanged.** With nothing declared, `green(dco)` → `green(dco)` still returns `green` (today's behaviour: without a declared list the harness cannot know `e2e` exists). Every existing `test_merge.py` test still passes.
  (4) The setting parses from `pdca.toml` (`Config.load`) and defaults to empty. A bare string (`expected_checks = "e2e"`) is read as a one-item list. Any other malformed value (not a string or a list of strings) warns on stderr and fails CLOSED: in merge mode every PR is refused with a detail naming the bad setting, like `merge_requires` falling back to the stricter `"all"` (`config.py:728-732`). It does not fall back to empty, because empty is the weakest setting and would merge exactly what the operator configured against.
  Pre-fix, (1) and (1b) return `green` on `green(dco)` reads, and (2) returns `green` on the changed set. That is the RED.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: Make merge mode's green confirmation require a complete rollup: the confirm read must see the same check names as the green it confirms, and an optional operator-declared list of expected checks must all be present and passing. Add the setting to `Config` and to the rendered `pdca.toml` comment block next to `merge_wait_secs` (`template/pdca.toml.jinja:180-194`), and describe it in the merge-mode paragraph of `docs/07-crosscutting.md` (`:720-735`) and in `template/docs/fork-discipline.md.jinja:63` if that line describes the confirm. Residual, stated so the issue is not closed as fully fixed a second time (the #617 mistake): with nothing declared (the default), `green(dco)` → `green(dco)` still merges when a slow `e2e` registers later. The issue's "Done when" refusal is met only for an operator who declares the list. The human accepted this at Plan. The PR description must say "narrows #621" for that case (or the issue stays open for the default), not claim a full fix. / out of scope: deriving the expected set automatically (from branch protection, workflow files, or the base tip's check runs); `merge_requires = "required"` (it does not use the rollup); the update-branch wait (#531) and third-remote fetch (#650); stack mode (the harness never merges there).

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

Review issue #621: require declared checks and an unchanged check-name multiset before confirming a green merge rollup, while retaining the documented opt-in limitation.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The accepted scope is falsifiable for missing checks, changed names, duplicate names, zero wait, and malformed configuration; the default's late-registration residual is explicit (brief.md:11; brief.md:24; target/docs/07-crosscutting.md:731). |
| C2 Reproduction (red pre-fix) | PASS | With production changes stashed and regression tests retained, changed-name and duplicate-name sequences incorrectly returned green: two assertion failures demonstrate the original defect independently of seven missing-API errors (target/template/tests/test_merge.py:1270; target/template/tests/test_merge.py:1284; review-red.log:129). |
| C3 Change | PASS | The five-file patch stays within the accepted merge/configuration/test/documentation scope, including refusal on invalid configuration and missing checks at zero wait (target/template/src/pdca_harness/merge.py:233; target/template/src/pdca_harness/merge.py:427; target/template/src/pdca_harness/config.py:897). |
| C4 Verification (red→green) | PASS | Restoring the production changes turns the same 59-test run green; the restored target diff exactly matches patch.diff (review-green.log:15; target/template/tests/test_merge.py:1225; gate-logs/C4-verify.log:10). |
| C5 Causal adequacy | PASS | Production-path tests expose both forbidden confirmations and verify refusal/return-to-draft; explicit completeness and same-multiset checks address the specified cause without an optional-capability probe (target/template/tests/test_merge.py:1232; target/template/src/pdca_harness/merge.py:181; target/template/src/pdca_harness/merge.py:255). |
| T1 Structure | PASS | Configuration parsing and merge decisions remain in their existing modules; the rollup's changed return shape has one production consumer, and the public wait result stays unchanged (target/template/src/pdca_harness/config.py:897; target/template/src/pdca_harness/merge.py:186; target/template/src/pdca_harness/merge.py:196). |
| T2 Shape | PASS | Independent docs lint, 22-page site render/internal-link audit, and git diff --check pass; frozen host-parity evidence agrees (target/.github/workflows/docs-check.yml:33; gate-logs/host-ci-docs.log:10). |
| T3 Runtime | PASS | Independent offline suite ran 2,379 tests successfully with two skips; frozen evidence additionally shows 24 root render/update tests passing, which local Python could not reproduce because Copier is not importable (gate-logs/T3-suite.log:54; gate-logs/T3-suite.log:1854; review-root.log:6). |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the substantive contribution audit is deferred to the mandatory publish re-run (gate-logs/T4-contribution.log:10). |
| T5 Judgment | NEEDS-HUMAN | Confirm the affected-path prior-art record covers merged and closed/rejected work — brief.md:29 records that search for merge.py, but the supplied target has one synthetic base commit and no remotes, so its conclusions and coverage of the other affected paths cannot be independently settled here. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Accept the operator-maintained expected-check list and default late-job residual for deployment — undeclared jobs can still arrive after confirmation, so this narrows #621 rather than fully resolving the default case (target/docs/07-crosscutting.md:734; target/template/pdca.toml.jinja:195; brief.md:24). |

Independent verification used the disposable target only. Production config.py and merge.py changes were stashed for the red leg, then restored before the green leg; no implementation was edited. Both runs used `PYTHONPATH=src python3 -m unittest tests.test_merge` in `target/template`, with temporary files confined to this review sandbox. The full offline suite subsequently passed; its captured output is in `review-runtime.log`.

The root-suite limitation is a reviewer-host caveat, not a patch defect or an undischarged dependency in the frozen evidence: the local runner reported `PDCA-UNVERIFIABLE`, while `gate-logs/T3-suite.log:37` explicitly records render and update cases executing successfully. No live GitHub result is claimed; scripted rollups can exhibit the forbidden failures and are the brief's prescribed offline oracle.

The frozen C5 scanner reports only “patch adds no new test file” (`gate-logs/C5-prod-path.log:10`), so it supplies no substantive production-path proof. The C5 verdict instead rests on inspecting and running the appended tests, which invoke the real wait and merge-wave functions while scripting subprocess responses. The available integration template has no enumerated project-specific human-only checks (`target/template/docs/INTEGRATION.md.jinja:80`).

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — issue 621 (merge-confirm-requires-complete-rollup)

Lens: bugs the patch introduces, plus reuse / simplification / efficiency. Grounded on
`$PDCA_TARGET` (patch applied on `b5f5c29`).

**Overall: no correctness bugs found.** The wait loop, the multiset compare and the
fail-closed config path do what the brief asks. The gate logs agree: T3 ran 2379 tests OK,
and C4 shows red before the fix and green after. The notes below are minor and none needs
a human.

## Correctness

- `template/src/pdca_harness/merge.py:253-258`: the confirm logic is right. `first = names`
  is taken from the green that passed the budget check. When the confirm read is green over
  a different set, the outer `while True` goes round again: the inner pending loop is
  skipped, because the verdict is green, and the budget check at `:247-250` either confirms
  it a full poll interval later or refuses. So the existing budget rules stay as they were.
  Multiset compare holds because `_check_rollup` returns `tuple(sorted(...))` (`:153` in the
  diff), with duplicates kept. No bug.
- `template/src/pdca_harness/merge.py:181-193` (`_read_rollup`): the declared list is only
  checked on a `green` verdict, so a `failing`/`pending` read keeps its own detail. That is
  correct. The `wait_secs <= 0` path (`:232-234`) goes through `_read_rollup` too, so
  criterion (1b) is met.
- `template/src/pdca_harness/merge.py:427-431`: the malformed-setting refusal comes before
  the `merge_requires != "required"` branch (`:456`). So it also refuses every PR when
  `merge_requires = "required"`, where `expected_checks` is never read. That matches the
  brief's wording ("in merge mode every PR is refused") and errs toward refusing, so it is
  not a defect. It is just stricter than it has to be for that mode.
- Every `_check_rollup` caller is updated. The return went from a 2-tuple to a 3-tuple,
  and `grep` finds no other caller in `template/src` or `template/tests`.

## Small cleanups (optional, not blocking)

- `template/src/pdca_harness/config.py:902` strips declared names, but `merge.py:170-171`
  (`_name`) does not strip the names it reads back from the rollup. If a check name had
  stray whitespace it would never match, and every PR would wait out the budget and refuse.
  That fails closed and is unlikely in practice. Stripping in `_name` too, or not stripping
  in the config, would keep the two sides the same.
- `template/src/pdca_harness/merge.py:248-250`: if the budget runs out right after a
  changed-set confirm, the refusal says "green first seen with Ns of wait budget left". It
  does not say the check set changed between reads, so an operator reading the log gets less
  help. This is a wording nit only.
- `template/src/pdca_harness/merge.py:174-178`: `_names` now uses the new `_name` helper,
  so nothing is duplicated. Reuse is good.

## Tests

- `template/tests/test_merge.py` (new class `MergeConfirmRequiresCompleteRollup`) covers
  criteria (1), (1b), (2), (3) and (4) through both `_wait_for_green` and the real
  `merge_wave` → `_merge_one` path. The test for a changed set with the budget exhausted
  (29 s, two reads) pins the "no second confirm" edge. I found no test that checks a value
  without exercising the fix.

No NEEDS-HUMAN items.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — Confirm the affected-path prior-art record covers merged and closed/rejected work — brief.md:29 records that search for merge.py, but the supplied target has one synthetic base commit and no remotes, so its conclusions and coverage of the other affected paths cannot be independently settled here.
- [x] Validation — fitness-to-purpose — Accept the operator-maintained expected-check list and default late-job residual for deployment — undeclared jobs can still arrive after confirmation, so this narrows #621 rather than fully resolving the default case (target/docs/07-crosscutting.md:734; target/template/pdca.toml.jinja:195; brief.md:24).
- [x] **Criterion (4) asks for a fail-OPEN fallback in a module whose settings fail closed.** The brief says: "a malformed value (not a list of strings) warns on stderr and falls back to empty, the way `[driver].merge_wait_secs` does." The two cases are not alike. `merge_wait_secs` falls back to its *default*, and the suite calls that "fails CLOSED" (`test_merge.py:703`). `merge_requires` falls back to the stricter `"all"` (`config.py:728-732`, `test_merge.py:682` "an unknown value fails CLOSED"). Here empty is the weakest setting. Say an operator writes `expected_checks = "e2e"` (a string, not a list). The harness warns and then merges `green(dco)` → `green(dco)`, which is exactly the merge the operator configured against. The planner should pick one of two options. Option A: a malformed value refuses every merge in merge mode, or is coerced (a bare string becomes a one-item list). Option B: keep fall-back-to-empty, but have the brief say outright that this fails open and get the human to approve it. Criterion (4) should pin whichever is chosen.
- [x] **Criterion (1) does not cover the `wait_secs <= 0` path.** When `merge_wait_secs` is 0 or less, `_wait_for_green` does one read and returns its verdict as-is (`merge.py:201-203`). The configured template documents `0` as a supported value (`pdca.toml.jinja:193`). Criterion (1) is phrased "up to `merge_wait_secs`", so a fix that only checks the declared list inside the loop passes every listed test. With `expected_checks = ["dco","e2e"]` and `merge_wait_secs = 0`, that fix still merges `green(dco)`. Add a sub-criterion: with a declared list and `merge_wait_secs = 0`, a single `green(dco)` read returns non-green (`pending`, naming `e2e`) and `_merge_one` refuses.
- [x] **"Present and passing" is ambiguous for a declared check that reports `skipping`/`neutral`.** `_check_rollup` treats skipped and neutral as green-compatible (`merge.py:116`, `_ROLLUP_OK`). The Invariant section says each declared check "has reported and passed". The Scope says it "must all be present and passing". Suppose the declared `e2e` reports `skipping`, for example because of a path filter. Under one reading it merges; under the other the PR is refused until timeout, every time. Do will have to guess, and Check cannot judge the guess. The planner should name the intended outcome and add it to criterion (1).
- [x] **"Same check names" does not say whether it compares a set or a multiset.** The issue's "Done when" says "compares check names/counts". The brief keeps only "names" (criterion (2): "a confirm read whose check names differ"). `gh pr checks` can list the same name twice, for example a job called `build` in two workflows, or a re-run. A set comparison then treats `green(build)` → `green(build, build)` as a confirmation, even though a check has registered in between. One sentence in criterion (2) settling set vs. multiset (with or without counts) would close this.
- [x] **Default behaviour against the issue's own test requirement; the human has accepted this, so it is noted rather than disputed.** The issue's "Done when" asks for "A test pins `green(dco)` → `green(dco)` (with `e2e` registering later) as refused". Criterion (3) keeps that exact sequence merging when nothing is declared, so the issue's headline scenario stays open for every operator who never sets the new option, which is the default. The brief's header says the human approved this at Plan, and criterion (1) does pin the refusal under a declared list. But the Disposition says "likely-fix", while the residual is closed only on an opt-in basis. The PR and the Act notes should say that, or the issue will be closed as fully fixed a second time, which is the same mistake #617 made ("narrows #582 but does not fully close it").

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
- Plan advisory: 5 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
