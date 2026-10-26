# Result — issue 671 / cleanup-closes-a-duplicate-as-a-duplicate

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: `pdca cleanup --apply` closes every COMPLETE close/no-fix bundle's open issue at once as **not planned**: an empty `patch.diff` takes the row at `template/src/pdca_harness/cleanup.py:425-432` (`_close_issue(..., reason="not planned", ...)`). It does not look at which close class the bundle took (the `close-disposition` marker, `state.CLOSE_MARKER`, `template/src/pdca_harness/state.py:45`, written by the driver from the brief's Disposition hint, `driver.py:222-249`). So a bundle closed as `duplicate` is closed with the wrong reason ("not planned" instead of GitHub's `duplicate`), its comment does not name the issue it duplicates, and any condition the human attached at Plan is ignored. Two real cases: bundle issue_624 was to be closed only once #652's PR merged (`results/issue_624/brief.md`, pdca-pdca), and bundle issue_630 left the close to the human. Cleanup would have closed both at once. Neither bundle records its target or its condition in a form the driver can read, so cleanup has nothing to check.
- Success criterion: A brief can record two new optional fields, read with the existing brief field parser (`brief.field`, `template/src/pdca_harness/brief.py:122`):
  - `- **Duplicate of:** #N` (the issue this one duplicates; `N` or `#N`),
  - `- **Close when:** <condition>`, where the condition is one of: `now` (close at the next `--apply`), `PR #M merged` (the tracker repo's PR M has state MERGED), or `#M closed` (the tracker repo's issue M has state CLOSED with `stateReason` COMPLETED).
  The duplicate row applies to a COMPLETE close/no-fix bundle (empty patch) whose tracker issue is OPEN and which EITHER has a `Duplicate of` field (whatever its `close-disposition` marker says: a hint such as `likely-close — duplicate of #463` writes the marker `likely-close`, `config.py:542-553`, `:21-27`, and must still be handled as a duplicate) OR whose `close-disposition` marker reads `duplicate`. For such a bundle `pdca cleanup` behaves as follows (each case pinned by a test driving `cleanup.run` with the `CleanupBase` fake `gh` of `template/tests/test_cleanup.py:49-116`):
  (1) **`Duplicate of` set, `Close when` met** (`now`; or `PR #M merged` with PR M MERGED; or `#M closed` with issue M CLOSED/COMPLETED): under `--apply` it makes exactly one `gh issue close` call for the issue whose argv carries `--reason duplicate` (not `not planned`) and a `--comment` body that names `#N`. Without `--apply` the row is a `would:` line naming `#N`. One sub-case writes a `tracker-comment.md` in the bundle: the posted body is that hand comment followed by the generated text, and still names `#N` (build the body yourself and call `_close_issue(..., prefer_bundle_comment=False)`, as the split-parent row does, `cleanup.py:300-308`).
  (2) **`Duplicate of` set, `Close when` not yet met** (`PR #M merged` with PR M OPEN, or `#M closed` with issue M OPEN): no `gh issue comment` or `gh issue close` call is made, even under `--apply`, and the row's text names the condition that is not yet met. The same row, once the fake reports PR M MERGED (or issue M CLOSED/COMPLETED), closes as in (1).
  (3) **`Duplicate of` set, `Close when` can no longer be met** (PR M CLOSED unmerged, or issue M CLOSED with `stateReason` NOT_PLANNED, i.e. the work it waited on was descoped): report-only, no mutation under `--apply`, and the row says the condition can no longer be met and needs a human decision.
  (4) **`Duplicate of` set, no `Close when`:** report-only (the issue's "when no condition is recorded for a `duplicate`, reports it and does not close it"); the row names `#N` and says to add `Close when: now` (or a condition) to close it.
  (5) **Marker `duplicate`, no `Duplicate of`** (or a value that is not an issue number): report-only, and the row says the duplicate target is not recorded and how to record it.
  A condition whose state `gh` cannot read, or a `Close when` value that matches none of the three forms, is report-only too (never a close). A bundle with neither a `Duplicate of` field nor a `duplicate` marker (`wontfix`, `likely-close`, …) and the DISCONTINUED row still close as `not planned` exactly as today (the existing `test_complete_close_disposition_closes_not_planned`, `test_cleanup.py:356-362`, stays green).
  Pre-fix, (1) fails (the close carries `not planned` and no `#N`), and (2)–(5) fail (a close is made). That is the RED.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: Make the open-issue COMPLETE close/no-fix row of `cleanup._plan_bundle` (`cleanup.py:425-432`) honour a `duplicate` close per the criterion: read `Duplicate of` / `Close when` from the bundle's `brief.md`, check the condition against the tracker repo cleanup already resolves (`repo`) with `_pr_state` / `_issue_state`, and close through the existing `_close_issue(..., reason="duplicate", prefer_bundle_comment=False)` (so one `gh issue close --reason duplicate --comment <body>` call; do NOT use `--duplicate-of`), or report. Add the two optional fields to `template/templates/brief.md.tpl` (next to `Disposition hint`, line 89) with a one-line explanation each. Update cleanup's module docstring matrix (`cleanup.py:29-34`) and the cleanup table in `docs/07-crosscutting.md:860-871`. / out of scope: other close classes with no `Duplicate of` field (they keep `not planned`); DISCONTINUED bundles; the split-parent row; issues already closed; writing these fields into any existing bundle (issue_624 / issue_630 are pdca-pdca records, not this repo); the planner role prompt (`template/agents/planner.md` — a prompt change is a human-only item, INTEGRATION §4); a minimum `gh` version check.

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

Review issue #671: make cleanup close duplicate no-fix bundles with the recorded duplicate target and only when their recorded close condition permits it.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The permitted timing, missing-data behavior, and preserved nonduplicate behavior are explicit and falsifiable; the authored fields and reconciliation table express that contract (`template/templates/brief.md.tpl:97`, `docs/07-crosscutting.md:952`; bundle `brief.md:13`). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing production changes while retaining the new tests produced 15 assertion failures, including the wrong close reason and premature mutations (`template/tests/test_cleanup.py:649`; `review-red.log:322`). |
| C3 Change | PASS | The four affected files stay within the cleanup decision, brief fields, documentation, and regression coverage authorized by the brief; existing split-parent and merged-PR precedence remains intact (`template/src/pdca_harness/cleanup.py:510`, `template/src/pdca_harness/cleanup.py:538`). |
| C4 Verification (red→green) | PASS | Restoring the production changes made all 53 cleanup tests pass after the independently observed red leg; this establishes the offline controller behavior (`template/tests/test_cleanup.py:656`; `review-green.log:3`, `gate-logs/C4-verify.log:339`). |
| C5 Causal adequacy | PASS | Closure authority now depends on the recorded target and condition, addressing the unconditional no-fix close at its decision point; absent, waiting, unknown, and descoped conditions cannot authorize a duplicate close; no capability-probe symptom guard was introduced (`template/src/pdca_harness/cleanup.py:385`, `template/src/pdca_harness/cleanup.py:400`, `template/src/pdca_harness/cleanup.py:541`). |
| T1 Structure | PASS | The decision remains within the existing planner and reuses the shared brief parser, tracker probes, and retry-aware close helper; no parallel tracker mechanism is introduced (`template/src/pdca_harness/cleanup.py:331`, `template/src/pdca_harness/cleanup.py:379`, `template/src/pdca_harness/cleanup.py:419`). |
| T2 Shape | PASS | Independently rerun docs lint and site render/link audit passed for 22 pages, and diff whitespace checks passed; both frozen docs gates also show substantive clean results (`docs/07-crosscutting.md:952`; `gate-logs/T2-docs.log:11`, `gate-logs/host-ci-docs.log:15`). |
| T3 Runtime | PASS | Independent offline driver discovery passed 2,646 tests with two skips; the frozen log additionally records 24 passing root render/update tests, whose Copier dependency is unavailable in this reviewer interpreter (`template/tests/test_cleanup.py:628`; `review-suite.log:1819`, `gate-logs/T3-suite.log:54`). |
| T4 Contribution | N/A | Contribution artifacts are intentionally drafted after Check; the frozen row defers their substantive audit to the required publish rerun (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | PASS | Scope is bounded, hand comments retain the duplicate reference, and independent file-path history plus all 303 closed PRs revealed no competing duplicate-close work; the seven rejected PRs touching the docs concern other sections (`template/src/pdca_harness/cleanup.py:415`, `template/tests/test_cleanup.py:671`; `review-prior-art.log:53`, `review-prior-art.log:62`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the recorded close conditions and offline evidence suffice for release, or require a live disposable-repo check — real GitHub duplicate closure and condition transitions were not exercised; the tests replace gh even though installed gh 2.103.0 advertises the required reason (`template/tests/test_cleanup.py:83`, `template/src/pdca_harness/cleanup.py:419`; bundle `brief.md:28`). |

Source citations above resolve relative to `$PDCA_TARGET` (`target/`); bundle inputs and review logs are cited relative to this report. The restored target diff exactly matches `patch.diff`. No patch defect or target-state caveat was found.

Independent verification used `PYTHONPATH=src python3 -m unittest tests.test_cleanup` from `target/template/`, first with only production/documentation/template changes stashed, then after `git stash pop`. The tests remained present for both legs. Full driver discovery used `PYTHONPATH=src python3 -m unittest discover -s tests`. Reviewer temporary files were confined beneath this sandbox.

The instance-scoped gate wrappers were adjudicated through their frozen logs and equivalent available commands. The C5 scanner's log only says no new test file was added (`gate-logs/C5-prod-path.log:10`); that is not proof of production coverage. Independently inspecting the import and call to `cleanup.run` (`template/tests/test_cleanup.py:21`, `template/tests/test_cleanup.py:86`), together with the production-only red→green rerun, supplies that evidence. The root render/update result rests on the frozen log, not a reviewer rerun: `copier` is not importable here.

The prior-art recheck queried merged history separately for all four affected paths and inspected file lists for all ten closed-unmerged PRs (there were no open PRs). None touched the cleanup implementation, its tests, or the brief template. Seven touched `docs/07-crosscutting.md`; their changed hunks contain no duplicate-close or cleanup changes (`review-prior-art.log:1`, `review-prior-art.log:53`, `review-prior-art.log:62`).

For the outstanding service validation, use an accepted empty-patch bundle tied to a disposable tracker issue: record `Duplicate of: #N` and `Close when: now`, run `pdca cleanup <id>` to inspect the proposed action, then `pdca cleanup <id> --apply` and inspect `gh issue view <id> --repo OWNER/REPO --json state,stateReason,comments`. Expect a duplicate closure with a comment naming #N. For conditional timing, use a fresh disposable issue with `Close when: PR #M merged`: it must remain open while that PR is open and close as duplicate after merge. These live mutations were not performed during this advisory review.

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — issue 671 (cleanup closes a duplicate as a duplicate)

I found no correctness bug that would make cleanup close an issue when it should not, or with the wrong reason. The new row fails closed (report only) on every unknown: no target, a target that is not a number, no condition, an unrecognized condition, a state `gh` can't read, and a condition that can no longer be met. It closes through the existing `_close_issue(..., prefer_bundle_comment=False)` path exactly as the split-parent row does. The C4 gate log shows 15 of the 16 new tests fail before the fix and pass after it. The 16th (wontfix still closes as not planned) is meant to pass both ways. The notes below are small and none blocks.

- NEEDS-HUMAN [impl] — template/tests/test_cleanup.py:632 — No test covers the case the new template lines create most often: a non-duplicate close bundle (e.g. `wontfix`) whose brief still has the untouched `- **Duplicate of:** <optional, …` placeholder. Today `brief.field` drops it, because `_is_placeholder` treats a value that opens with `<` and has no closing `>` as unfilled (template/src/pdca_harness/brief.py:107-128). So `_duplicate_row` returns None and the bundle still closes as not planned. But nothing pins this. If the placeholder check ever changes, every wontfix/by-design bundle written from the new template would quietly stop closing and become report-only. One test would cover it: copy the two placeholder lines from `brief.md.tpl` with marker `wontfix` and assert a `not planned` close.
- template/src/pdca_harness/cleanup.py:393 — There is no check that the duplicate target differs from the issue being closed. `Duplicate of: #40` on bundle issue_40 with `Close when: now` would close #40 "as a duplicate of #40". It's a typo case and the comment would show the mistake, but a one-line `target == number` → report-only guard would match the module's "unknown never acts" rule. This is optional.
- template/src/pdca_harness/cleanup.py:360 — The "never" text reads "closed as closed, not completed" when `stateReason` is empty. That is cosmetic; it copies the `or 'closed'` fallback from the split-parent row (cleanup.py:308), where the wording works. Something like "was closed (no reason given)" would read better.
- template/src/pdca_harness/cleanup.py:323 — Simplification: `_COND_NOW` is a regex for a fixed word. `cond.strip().lower() == "now"` (or a small helper) says the same thing more plainly, and it's used twice (:333 and :413). This is a style nit only.
- template/src/pdca_harness/cleanup.py:322 — Style: the new module-level constants follow `_split_parent_row` after one blank line, not two (PEP 8 E305). template/tests/test_cleanup.py:627-628 has three blank lines before `class DuplicateClose`. No lint gate flagged either one.
- template/tests/test_cleanup.py:795 — `test_wontfix_marker_without_a_target_still_closes_not_planned` mostly repeats the existing `test_complete_close_disposition_closes_not_planned` (:356). It's harmless. Keep it only if the point is to show the fixture path `_dup(fields="")` in the new class.

Reuse check: the patch reuses `brief.field`, `_issue_state`, `_pr_state` (extended with an optional `repo`, and existing url callers are unchanged), `_bundle_comment` and `_close_issue`. The `#M closed` state reading mirrors the split-parent row's logic and doesn't copy a helper that already exists. I see no needless work in a hot path: at most one extra `gh` probe per duplicate bundle, and only when a condition needs one.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] Validation — fitness-to-purpose — Decide whether the recorded close conditions and offline evidence suffice for release, or require a live disposable-repo check — real GitHub duplicate closure and condition transitions were not exercised; the tests replace gh even though installed gh 2.103.0 advertises the required reason (`template/tests/test_cleanup.py:83`, `template/src/pdca_harness/cleanup.py:419`; bundle `brief.md:28`).
- [ ] template/tests/test_cleanup.py:632 — No test covers the case the new template lines create most often: a non-duplicate close bundle (e.g. `wontfix`) whose brief still has the untouched `- **Duplicate of:** <optional, …` placeholder. Today `brief.field` drops it, because `_is_placeholder` treats a value that opens with `<` and has no closing `>` as unfilled (template/src/pdca_harness/brief.py:107-128). So `_duplicate_row` returns None and the bundle still closes as not planned. But nothing pins this. If the placeholder check ever changes, every wontfix/by-design bundle written from the new template would quietly stop closing and become report-only. One test would cover it: copy the two placeholder lines from `brief.md.tpl` with marker `wontfix` and assert a `not planned` close.
- [ ] **Case (1) goes against the issue's own "Done when".** The issue says: "when no condition is recorded for a `duplicate`, reports it and does not close it" (notes.json body, third bullet under "Done when"). Brief case (1) says the opposite: "**`Duplicate of` set, no `Close when`:** under `--apply` it makes exactly one `gh issue close` call". The brief reads the issue's "condition" as "the duplicate target". Under the issue's literal wording, a `duplicate` close with no `Close when` stays report-only, so case (1) would be a regression the issue asked to prevent. The #630 case points the same way: its brief "leaves it to the human to choose" (issue body), and an automatic close on `Duplicate of` alone removes that choice. A human must decide which reading is meant before Do starts. If the issue's reading wins, the RED/GREEN for case (1) has to change (for example, a close only with an explicit `Close when: now` or an equivalent field).
- [ ] **Keying on the marker reading exactly `duplicate` can miss real duplicates.** `Config.close_class` (`config.py:542-553`) returns the *first* configured class whose token is a substring of the hint, in `DEFAULT_CLOSE_DISPOSITIONS` order (`config.py:21-27`: `likely-close` comes before `duplicate`). A hint such as `likely-close — duplicate of #463` therefore writes the marker `likely-close`, not `duplicate` (`driver.py:249`). Under the brief, that bundle still closes as `not planned` with no `#N`, even when it records `- **Duplicate of:** #463`. The same thing happens on an instance whose `[driver].close_dispositions` leaves out `duplicate` or spells it differently. The invariant the brief states ("never closes a tracker issue for a reason ... other than the one the bundle's recorded decision gives") does not hold for those bundles. The brief should either key the row on the `Duplicate of` field being present, whatever the marker says, or move these cases explicitly out of scope and pin them with a test.
- [ ] **The brief does not handle the issue's "descoped" concern.** The issue says: "If #652 is later descoped, #624's gap is lost." Case (2) only defines "unmet" as PR M **OPEN** or issue M **OPEN**. It says nothing about `PR #M merged` when PR M is **CLOSED** unmerged (the descoped case), or about `#M closed` when M was closed as `NOT_PLANNED`. As written, Do could treat a closed-unmerged PR as either "unmet" or "unknown", and nothing checks which. Pin it: report-only, with row text saying the condition can no longer be met and needs a human decision, plus a test.
- [ ] **"The comment it posts names `#N`" clashes with `tracker-comment.md` precedence.** `_close_issue` posts the bundle's hand-written `tracker-comment.md` in place of `fallback_body` whenever that file exists (`cleanup.py:191`). If Do calls it the way the current row does (`prefer_bundle_comment` defaulting to True), a bundle with a hand comment closes as a duplicate without naming `#N`. The repro (`brief.md:25`) creates no `tracker-comment.md`, so a test would not catch this. The brief names the split-parent row as the peer to mirror, and that row builds `hand + generated text` with `prefer_bundle_comment=False` (`cleanup.py:300-308`). The brief should say so explicitly and add one test case that has a `tracker-comment.md`.
- [ ] **The success criterion depends on `gh` flag spelling, which the brief leaves open.** The brief says only that Do "should say in build-notes.md which flags it uses" (`brief.md:26`), and it mentions a "duplicate-of flag". The test asserts "reason `duplicate`" and a comment naming `#N`. If Do uses `--duplicate-of`, the fake `gh` (`test_cleanup.py:77-78`) accepts any `issue close` argv, so the test passes even if real `gh` would reject that argument combination. A failed close is reported rather than mis-closed (`cleanup.py:209-212`), so it fails safe, but it never takes effect on a host with an older `gh`. The brief should pick one form (`--reason duplicate` plus a comment, *or* `--duplicate-of`) so the reviewer can check the argv precisely.

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome:
- Iteration delta (if iterating):
- By / date:

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 5 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
