# Result — issue 694 / reissue-after-conflict-hold-names-the-partner

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: After a #674 hold, the run's own end-of-run advice and the advice on re-issue contradict each other. At the end of run 1, `_report_conflict_holds` (`template/src/pdca_harness/flow.py:1171-1180`) says: declare `Conflicts with: 10` in `issue_11`'s brief, then rebuild `issue_11` on a base that holds `issue_10`. Re-issuing the same batch reaches the #646 pre-wave carry (`flow._carry_finished`, `flow.py:1032-1130`). Its fold (`skipped=` mode) records `issue_11`'s merge failure with the in-run fold's conflict text, "does not merge cleanly … — an undeclared cross-wave overlap; declare the conflict / re-order, then re-run" (`template/src/pdca_harness/integrate.py:628-632`), files it under the `open` hint (`flow.py:1113`), and prints "get issue_11's PR open with its branch on origin (re-open it, `pdca publish 11`, or re-drive issue_11), then re-issue" (`_CARRY_HINTS["open"]`, `flow.py:992-993`; printed at `:1122-1130`). For a #674 hold that is wrong twice: the clash is with a finished same-batch bundle, not cross-wave, and the PR is already open, so re-publishing changes nothing. The partner is never named. Reproduced at Plan on `d6057eb` (run 1 then the re-issue below), with exactly that output.
- Success criterion: Real-git tests on the `SameWaveConflict` set-up of `template/tests/test_flow_same_wave_conflict.py:53-163`, with one change to its `gh` stub: a PR view reports `OPEN` with `headRefOid` = the branch's tip on origin (the stub there returns an empty head, which makes every finished id "not clean" before the fold and never reaches this code; the carry suite's stub does the same as needed here, `template/tests/test_flow_resume_stack_prereqs.py:90-102`).
  (1) **Re-issue after a #674 hold names the partner and gives the #674 remedy.** `shared.txt` = `x\n` on the base; plan `10` (`shared.txt` = `ten\n`), `11` (`shared.txt` = `eleven\n`), `12` (own file), `20` (`Depends on: 11`), `21` (`Depends on: 12`). Run 1 drives all five with `batch` = all five: `11` is held, `20` stays PLANNED. The test asserts this precondition before run 2: `11` is COMPLETE after run 1 and the `gh` stub reports its PR OPEN (`_finished_named` takes only COMPLETE ids, `flow.py:962`, and the carry runs only because `20`'s plain `Depends on` names `11`, `flow.py:1062-1067`), so a later change that stops this would fail the precondition, not the advice assertion. Run 2 drives `[20]` with the same `batch` (a re-issue: the finished ids are skipped and judged by the carry). Then exactly one stderr line of run 2 says `issue_11` is not carried, and it: names `issue_10` as the bundle whose change it conflicts with and `shared.txt`; tells the operator to declare `Conflicts with: 10` in `issue_11`'s brief and rebuild `issue_11` on a base that holds `issue_10` (the same step the end-of-run line of run 1 gives, `_report_conflict_holds`, `flow.py:1177-1180`, and `docs/07-crosscutting.md:704-706`); and does **not** contain `get issue_11's PR open`, `pdca publish 11`, or `cross-wave`. `20` is still not built and stays PLANNED; `10`, `12` and `21` are carried as today.
  (2) **No partner is blamed when there is none.** Set-up, same stubs: `shared.txt` = `x\n` on the base; plan `11` (`shared.txt` = `eleven\n`) and `20` (`Depends on: 11`). Run 1 drives `[11]` with `batch` = `[11, 20]`; assert `11` COMPLETE with an OPEN PR. Then the base changes the same line (`fx._push_from_human({"shared.txt": "y\n"}, to="main")`, `test_integrate_stack_bases.py:174`) and every `pdca-integration/*` branch on origin is deleted (`fx._delete(...)`, `:195`), so run 2's carry starts a fresh line from the base (`integrate.py:498-499`: `start_ref` is the base when origin's line is absent). Run 2 drives `[20]` with the same `batch`. Then exactly one stderr line says `issue_11` is not carried; it names `shared.txt`, names no other bundle id, and contains no `Conflicts with`. `20` stays PLANNED.
  (3) **Nothing else changes.** Every existing test in `template/tests/test_flow_resume_stack_prereqs.py` and `template/tests/test_flow_same_wave_conflict.py` stays green.
  Pre-fix, (1) fails: run 2's line is the `open` advice above with the "cross-wave overlap" reason. That is the RED.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: When the pre-wave carry's fold refuses a finished id because its branch conflicts textually with work other finished ids of the batch put on the line (in this fold, or already on origin's line from the earlier run), name those ids and the files, and give the #674 remedy per criterion (1) instead of the `open` hint; keep the other carry reasons and hints as they are. Do not reuse the fold's `held_out` mode unchanged: it judges a conflict against the line "as the wave found it" (`integrate._held_by`, `integrate.py:884-908`), and on a re-issue that line already holds `issue_10` from run 1, so it would find no partner (seen at Plan: the carry continues origin's line, on which `issue_10` is already merged). How the partner is found (pinned): when the carry's fold records a textual conflict for finished id `X`, first try `X`'s head onto the base ref alone (a trial `_merge` in the carry's worktree, undone with `_reset_line`, `integrate.py:841`, `:863`). If that conflicts, the clash is with the base: no partner is named and no `Conflicts with` proposed (criterion 2). If it merges cleanly, the partners are the other finished ids of this run's `batch` whose work is on the line (merged in this fold, or already on origin's line) and for which `X`'s head conflicts onto base + that id's head; name each one with the conflicting files. If none of the batch ids reproduces the conflict (the clashing work is on the line but belongs to no id of this run's batch, since `_finished_named` covers only `batch`, `flow.py:954-964`), name the files, say the conflict is with work already on the line, and propose no `Conflicts with`. Say in `build-notes.md` how this was coded. Update the carry paragraph of `docs/07-crosscutting.md` (`:711-741`, which lists "two finished prerequisites that conflict with each other" as a known limit) to say what the run now advises. / out of scope: which of the two conflicting ids is carried (still the one asked for first, so asking for `11` before `10` holds `10` instead, named with `issue_11`); the in-run fold's own conflict message (`integrate.py:628-632`) when the run stops; writing any brief; carrying the held bundle; exit codes (693); the carry's other hints.

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

Review issue #694: make re-issued conflict holds name the responsible finished bundles and give actionable recovery advice instead of telling operators to reopen an already-open PR.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The partner/base/unaccounted-work cases and unchanged hold behavior are falsifiable and bounded; brief.md:10, brief.md:23; target/template/tests/test_flow_reissue_after_conflict_hold.py:210. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing the production fix while retaining the new tests reproduces 22 assertion failures, including the incorrect reopen/cross-wave advice; review-red.log:259; target/template/tests/test_flow_reissue_after_conflict_hold.py:210. |
| C3 Change | PASS | The four affected files address carry diagnostics, shared recovery wording, documentation and regression coverage; merge eligibility remains unchanged; target/template/src/pdca_harness/flow.py:1189, target/template/src/pdca_harness/integrate.py:632. |
| C4 Verification (red→green) | PASS | Independently reproduced 22 red tests before the fix and 22 green after restoring it; this verifies the supplied cases, not the additional C5 case; review-red.log:259, review-green.log:3; gate-logs/C4-verify.log:10. |
| C5 Causal adequacy | NEEDS-HUMAN [impl] | Correct recovery advice when a later carried bundle removes the conflict — current attribution still demands a declaration/rebuild although a plain re-issue completes; target/template/src/pdca_harness/integrate.py:1231; review-final-line.log:1. |
| T1 Structure | PASS | Attribution runs under the existing fold lock and trial merges restore the integration branch; presentation stays in flow and in-run reporting shares its recovery wording; target/template/src/pdca_harness/integrate.py:640, target/template/src/pdca_harness/integrate.py:1341, target/template/src/pdca_harness/flow.py:1004. |
| T2 Shape | PASS | Independent docs lint, 22-page rendering/link audit and whitespace check pass; frozen host-CI evidence agrees; review-scanners.log:1, gate-logs/host-ci-docs.log:10; target/docs/07-crosscutting.md:767. |
| T3 Runtime | PASS | Independent driver suite passes 2,513 tests with two skips; frozen root suite passes 24 tests, while this interpreter lacks Copier (host caveat, not a patch defect); review-suite.log:1817, gate-logs/T3-suite.log:54, review-root.log:6. |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; their substantive audit must rerun at publish; gate-logs/T4-contribution.log:10. |
| T5 Judgment | NEEDS-HUMAN | Confirm the path-scoped merged and closed/rejected prior-art account before sign-off — the brief records it, but the supplied synthetic history and absent PR records cannot independently substantiate it; brief.md:28, review-prior-art.log:1. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the recovery instructions are sufficient for stack-mode operators after the C5 correction — real-git tests establish observable behavior, while operational suitability remains a human decision; target/docs/07-crosscutting.md:767, target/template/src/pdca_harness/flow.py:1017. |

**C5 finding — unnecessary rebuild after a later merge resolves the conflict (P2).** At target/template/src/pdca_harness/integrate.py:1231, `_clash` returns `batch` when a pairwise partner trial conflicts, before testing the branch against the final line at :1234. A historical pairwise clash can therefore override the fact that the final line accepts the branch. This also contradicts the retry behavior described at target/docs/07-crosscutting.md:792.

I exercised the production flow with real git using the supplied fixture: the base has `shared.txt = x`; finished 10 writes `ten`; finished 11 writes `eleven`; finished 12 is cut from 10 and restores `x`; 20 depends on 11. The carry merges 10, skips 11, then merges 12. Nothing is taken back off the line. Its pushed tree has `x`, yet the diagnostic says 11 does not merge cleanly and proposes `Conflicts with: 10` plus a rebuild. Without changing a brief or rebuilding any bundle, a plain re-issue carries 11 and completes 20. The observed output is in review-final-line.log:1; the successful re-issue is at :3. The additional assertion requiring retry advice fails at :17.

The correction should distinguish conflicts that remain on the final line from ones removed by a later carried merge before selecting the declaration/rebuild remedy, while preserving the separately tested removed-bundle cases. Add this case alongside target/template/tests/test_flow_reissue_after_conflict_hold.py:649; its existing later-merge case starts from unaccounted-for work, so it does not exercise the early return for a named partner. The brief pins pairwise attribution, but the demonstrated defect is the recovery advice and present-tense claim about the final line, not the historical observation that 10 and 11 conflict.

Reproduce from the review cwd with:

```bash
TMPDIR="$PWD/review-tmp" PYTHONDONTWRITEBYTECODE=1 python3 review-final-line.py
```

**Evidence and limits.** The disposable target contains the patch and its prerequisite base; no stale-target limitation was encountered. The production changes were stashed and restored, and a final reverse-apply check confirms the supplied patch remains intact. The new tests genuinely call production code: the independent import scanner passes at review-scanners.log:10, and real git exhibits the forbidden failure in the red leg. Python and git were exercised directly; the PR-state stub is the one specified by the brief and does not prevent the conflict from occurring. No capability probe guarding a load-time side effect was introduced.

The instance-scoped wrappers were adjudicated using their frozen logs and available underlying commands. Local root-suite execution exits 77 because Copier is not importable, rather than falsely claiming those tests ran. gate-logs/T3-suite.log:54 records the actual successful 24-test root run, so the local limitation does not establish an unmet dependency in the round's evidence. Both frozen documentation checks show successful rendering and link audits, independently reproduced here. T4 remains deferred to publish, not a missing-evidence finding.

The affected-path history investigation is recorded in review-prior-art.log:1: the scratch repository has only its synthetic base commit and no remotes. The brief names merged history for both production files and closed-unmerged PRs touching those files and the documentation, but the underlying history/PR records are not supplied. No other checkout was consulted. The available INTEGRATION template has only a TODO for project-specific human-only items (target/template/docs/INTEGRATION.md.jinja:80), so it supplies no additional enumerated decision.

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — issue 694 (round 4)

Overall: no correctness bug found that blocks this patch. The two points from earlier rounds that this lens can check are fixed. Partners are now judged after every pass, against the final `took` (`template/src/pdca_harness/integrate.py:635-652`). So a partner that comes later in the order, or one that is already on origin's line, gets named. A partner that a #672 hold takes back off is not named as carried. Criterion (2)'s test now asserts text that only the fix prints (`template/tests/test_flow_reissue_after_conflict_hold.py:536-537`). The C4 red leg shows all 22 tests failing without the fix (`gate-logs/C4-verify.log`). `_report_conflict_holds` now shares `_CONFLICT_STEP` with the carry hint (`template/src/pdca_harness/flow.py:1004-1005`, `:1268-1272`), so the two messages cannot drift apart. That is good reuse.

Minor findings. None of them needs a human.

- `template/src/pdca_harness/integrate.py:1150-1154`: `_merge_over` reads `git ls-files -u -z` with `text=True`. With `-z`, git prints paths as raw bytes with no quoting, so a conflicting file whose name is not valid UTF-8 raises `UnicodeDecodeError`. That error is not an `IntegrationError`, so `_clash` (`:1240-1243`) and the carry's `except integrate.IntegrationError` (`flow.py:1186`) both miss it, and the run crashes instead of falling back to `"line"`. The nearby `_merge` (`:1125`) uses `diff --name-only` without `-z`, which quotes such names, so this exposure is new. It is rare. A fix is to pass `errors="surrogateescape"` (and the same to `update-index`), or to catch the decode error and raise `IntegrationError`.
- `template/src/pdca_harness/integrate.py:1246-1271` and `:1274-1306` (efficiency, advisory only): for each conflicting id, `_partners` runs up to two full trials (checkout, merges, reset, checkout back) for every carried id in `took`. `_built_on` also runs one `merge-base --is-ancestor` per pair of tips. That is fine for the batch sizes the tests use. On a large re-issue with several conflicts it could be hundreds of git processes. A cheap filter would help: skip a candidate whose diff from the base touches none of the files the skipped branch changes. This is optional and only runs on the conflict path.

No NEEDS-HUMAN items from this lens.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] C5 Causal adequacy — Correct recovery advice when a later carried bundle removes the conflict — current attribution still demands a declaration/rebuild although a plain re-issue completes; target/template/src/pdca_harness/integrate.py:1231; review-final-line.log:1.
- [x] T5 Judgment — Confirm the path-scoped merged and closed/rejected prior-art account before sign-off — the brief records it, but the supplied synthetic history and absent PR records cannot independently substantiate it; brief.md:28, review-prior-art.log:1.
- [x] Validation — fitness-to-purpose — Decide whether the recovery instructions are sufficient for stack-mode operators after the C5 correction — real-git tests establish observable behavior, while operational suitability remains a human decision; target/docs/07-crosscutting.md:767, target/template/src/pdca_harness/flow.py:1017.
- [x] **The required remedy text contradicts the brief's own invariant.** Criterion (1) requires run 2's line to say "rebuild `issue_11` on a base that holds `issue_10` … **or to merge `issue_10`'s PR first**". The invariant says the advice must match "whichever step reports it" and must never be "a step that cannot change the outcome". But the end-of-run line it is meant to match (`flow.py:1177-1180`) offers only "declare `Conflicts with` … then rebuild". Also, merging `issue_10` first does not make `issue_11` carryable: `issue_11`'s branch still changes the same line of `shared.txt`. Once the base holds `issue_10`, that becomes a conflict with the base, which is criterion (2)'s case. `docs/07-crosscutting.md:704-706` likewise says to rebuild, and to re-run the partner only after the rebuilt PR merges. The "or merge the partner first" wording comes from the issue's "Possible fix", but the brief adopts it without checking it. Either drop it from (1), or state what it achieves and add it to `_report_conflict_holds` too, so the two lines really match.
- [x] **Criterion (2) has no set-up and may not be reachable through the carry as described.** It says the base "changed the same line after it was published", but gives no ids, no runs and no commands. In run 2 the carry continues origin's existing line from `tip` (`flow.py:1106-1107` → `integrate.py:488-499`: `start_ref = line` when not fresh). A base that moved after run 1 is therefore not on the line the carry merges onto, and the finished id would merge cleanly with no hold at all. The (2) conflict only appears if:
- [x] **The partner-finding rule is left to Do, but it decides whether (1) and (2) can be told apart.** The scope bans `_held_by` unchanged, correctly: `pre` is origin's line, which already holds `issue_10` from run 1. But the brief only says "Say in `build-notes.md` how the partner is found". The obvious replacement is "merges onto the base, fails onto base + finished id X". That needs the base ref and each finished id's head, which the carry has (`heads`, `base_ref` at `flow.py:1076-1078`). The brief should name the rule and its fallback. Two cases need a rule:
- [x] **The base and citations are for `d6057eb`, but the slice builds in wave 2 on top of 672 and 673.** Per the Ordering note, 672 edits `_carry_finished`'s skip handling and 673 edits the fold's merge loop near `_merge_published`'s conflict text. Those are exactly the hunks this brief cites (`flow.py:1104-1132`, `integrate.py:518-539`, `:628-632`). Every "Peer callsites" line number will have moved on the base Do actually gets. Also, 672's rewrite of the `skipped` → `why` mapping may already change the RED described under Falsifiability. No `dependency-state.json` was supplied, so I cannot confirm that 672 and 673 exist or what state they are in. Confirm the RED will be re-taken on the wave-2 base, not on `d6057eb`.
- [x] **The repro depends on `issue_11` being COMPLETE after run 1 and on the carry being triggered.** `_finished_named` takes only COMPLETE ids (`flow.py:962`). The carry runs only when a drive-set bundle's plain `Depends on` names a fold candidate (`flow.py:1062-1067`). The brief says this was reproduced at Plan, which is credible. Still, criterion (1) should assert this precondition explicitly (`issue_11` COMPLETE with an OPEN PR after run 1). Otherwise a later change that stops marking held bundles COMPLETE would turn the test vacuously into "no carry line at all", and the "exactly one stderr line" assertion would fail for the wrong reason.
- [x] size backstop — this slice is behaving oversized: 3 round(s) already spent (threshold 3). Recommend answering `iterate-plan` at sign-off and authoring the split in the re-plan (`pdca split`), rather than `iterate-do`: a slice that is too big yields implementation-shaped findings every round, and splitting authors briefs, which is Plan's beat.
- [x] T5 Judgment — Confirm the path-based prior-art conclusion, including merged docs history and closed/rejected work — the brief reports the search, but this synthetic single-commit target has no original history or remote with which to corroborate it; brief.md:28.
- [x] T5 Judgment — Confirm the affected-path merged-history and closed/rejected-work prior-art conclusion before accepting novelty — the brief records a search, but this artifact-only target has one synthetic commit and no remote history to substantiate it; brief.md:28 and review-prior-art.log:1.

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
- By / date: Eduard Ralph / 2026-10-15

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 5 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
- Follow-up (issue_694 sign-off): carry advice for a #674 hold still says "declare Conflicts with + rebuild" when a later carried merge has already removed the clash and a plain re-issue would succeed (`_clash` early-returns on a pairwise partner before checking the final line, integrate.py:1231 vs :1234; repro review-final-line.log). File as a separate issue.
