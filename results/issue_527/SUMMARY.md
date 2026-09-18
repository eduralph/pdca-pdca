# Result — issue 527 / section6-keeps-whole-needs-human-bullet

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: a `- NEEDS-HUMAN` bullet that wraps onto indented continuation lines reaches
  SUMMARY §6 as its **first physical line only**. The human clearing §6 sees a question that
  stops mid-sentence and has to open the artifact to find out what is being asked.
  `_needs_human` (`template/src/pdca_harness/assemble.py:435-490`) walks
  `review_text.splitlines()` and, for a bullet, takes only the stripped current line
  (`:465-468`); continuation lines are never joined. Every artifact that feeds §6 goes
  through this parser (via `_items_from_artifact`, `:157-173`): `check-review.md`,
  `check-advisory-*.md` (`:192-194`) and `plan-advisory-*.md` (`:221-223`). Real cases in
  the self-hosting instance: `results/issue_462/SUMMARY.md` §6 shows
  ``- [x] `template/src/pdca_harness/merge.py:143-160` (`_wait_for_green`):`` from a
  well-formed 13-line `- NEEDS-HUMAN [impl] — …` bullet (pdca-pdca
  `results/issue_462/check-advisory-code-review.md:9-21`); `results/issue_472/SUMMARY.md` had
  four such stubs.
- Success criterion: offline, on the template driver suite:
  (a) a `- NEEDS-HUMAN` bullet followed by lines indented deeper than the bullet becomes
      **one** §6 item whose text is the bullet's first line plus every continuation line,
      joined with single spaces (each line's own leading/trailing whitespace stripped). In
      the rendered SUMMARY it is still exactly **one** `- [ ] …` line containing the last
      words of the bullet, and `signoff.open_needs_human` (`signoff.py:102-122`, line-based)
      counts it as one open item. The joined text must never contain a newline, since a
      second physical line would lose its checkbox and leave C6 unable to see it;
  (b) the item ends at the first line that is blank, not indented deeper than the bullet, or
      that starts a new list item (`-`, `*`, `+`, or `1.` at any indent), a heading (`#`), a
      table row (`|`) or a code fence. So two consecutive bullets stay two items, and an
      indented `  - NEEDS-HUMAN …` sub-bullet is still its own item, as today;
  (c) classification is unchanged: a multi-line `- NEEDS-HUMAN [impl] — …` bullet is still
      one IMPL item with the marker stripped (`_IMPL_MARKER_RE`, `:58`; `_classify_finding`,
      `:146-148`), so auto-iterate treats it as before. Single-line bullets and table rows
      produce byte-identical items to today (the verdict-table / STANDING logic at
      `:469-487` is untouched);
  (d) the existing suites that exercise §6 (`template/tests/test_autoiterate.py`,
      `test_plan_advisory.py`, `test_external_dependency_section6.py`,
      `test_leaf_status.py`) pass unchanged.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: `_needs_human` keeps a NEEDS-HUMAN bullet's full text, continuation lines
  included, as one single-line §6 item, per the criterion. One function in `assemble.py`.
  / out of scope: `leaves._plan_findings`' line count (`leaves.py:3141`), which counts bullets
  and is unaffected; the table branch; multi-paragraph bullets (a blank line ends the item);
  the §1–8 brief-field rendering (#336, already fixed); rewording any leaf prompt to forbid
  wrapped bullets.

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

Review issue #527: preserve every indented continuation of a wrapped NEEDS-HUMAN bullet as one complete, single-line SUMMARY §6 checkbox item.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The acceptance criteria make lost decision text observable through collection, SUMMARY rendering, and sign-off counting; the regression exercises those public interfaces (`template/tests/test_needs_human_multiline.py:76`, `template/src/pdca_harness/signoff.py:114`). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing the production fix produced nine assertion failures among ten tests, including missing “overshoots” in the collected finding (`template/tests/test_needs_human_multiline.py:80`; `review-red.log`). |
| C3 Change | PASS | Complete findings survive without absorbing adjacent structural blocks or losing nested findings; independent boundary checks passed, and table classification remains equivalent (`template/src/pdca_harness/assemble.py:498`, `template/src/pdca_harness/assemble.py:513`). |
| C4 Verification (red→green) | PASS | Restoring the identical production patch changed nine failures to ten passing tests, including complete checkbox text and one open sign-off item (`template/tests/test_needs_human_multiline.py:83`, `template/tests/test_needs_human_multiline.py:95`; `review-green.log`). |
| C5 Causal adequacy | PASS | The source of truncation is removed at the shared parser; real production collection/rendering is exercised, with no capability probe or fallback concealing a load-time cause (`template/src/pdca_harness/assemble.py:508`, `template/tests/test_needs_human_multiline.py:78`). |
| T1 Structure | PASS | The shared parser owns continuation membership, so callers retain one classification/rendering contract and no new dependency is introduced (`template/src/pdca_harness/assemble.py:70`, `template/src/pdca_harness/assemble.py:510`). |
| T2 Shape | PASS | Independent whitespace validation, docs lint, and 22-page site rendering with internal-link audit passed using the target CI commands (`.github/workflows/docs-check.yml:33`; frozen corroboration: `gate-logs/T2-docs.log:10`, `gate-logs/host-ci-docs.log:10`). |
| T3 Runtime | PASS | Independent driver suite passed 1,798 tests with two skips; frozen evidence records 24 root tests passing, including actual rendering/update cases; local root reproduction has a Copier host limitation described below (`review-suite.log:1113`, `gate-logs/T3-suite.log:38`). |
| T4 Contribution | N/A | Contribution artifacts are intentionally drafted after Check; their substantive audit is owed to the mandatory publish rerun (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Confirm no merged or closed/rejected work already resolves the affected paths — local history is a single synthetic base without remotes, and the brief's closed-work search uses issue/text rather than affected paths, leaving prior-art equivalence unsettled (`brief.md:70`; affected source: `template/src/pdca_harness/assemble.py:454`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether single-line joining and termination at blank/structural lines preserve the complete decision humans need in real advisory artifacts — automated checks establish text retention and checkbox counting, while acceptance of that presentation remains human judgment (`template/tests/test_needs_human_multiline.py:83`, `template/src/pdca_harness/assemble.py:501`). |

## Independent evidence and limits

- Used only this bundle and its disposable `$PDCA_TARGET`. Stashed only `template/src/pdca_harness/assemble.py`, retained the new test for the red leg, then restored the patch with `git stash pop`. The target still contains the original production diff and new test; no implementation edits were made.
- Red/green command, from `target/template`: `PYTHONPATH=src python3 -m unittest tests.test_needs_human_multiline`. Red: ten executed, nine assertion failures. Green: ten passed. Captured in `review-red.log` and `review-green.log`; agrees with `gate-logs/C4-verify.log`.
- Broader command, from `target/template`: `PYTHONPATH=src python3 -m unittest discover -s tests`. Result: 1,798 tests, OK, two skips (`review-suite.log:1113`). This includes the four existing suites named in the brief. Temporary files were directed inside the review sandbox with `TMPDIR`.
- Additional direct production-parser assertions passed for nine indented boundaries: dash, asterisk, plus, two numbered-list markers, heading, table row, backtick fence, and tilde fence. Also checked nested continuations and canonical-table STANDING classification. These cover structural cases absent from the new test module's dedicated assertions.
- Re-ran the target's production-import scanner with this bundle and `PDCA_PROD_PACKAGE=pdca_harness`: it confirmed the added test imports production, consistent with `gate-logs/C5-prod-path.log:10`.
- Re-ran `git diff --check`, `python3 docs/publishing/tools/lint_docs.py`, and `python3 docs/publishing/tools/render_site.py --check --out /tmp/pdca-review-ghx3l2tp/review-site`: all passed. The two frozen docs logs also record successful lint, rendering, and link audits.
- Local `python3 -m tests.run_root_suite` exited 77: 19 tests reported, three skipped, and no Copier-dependent case executed because Copier is not importable by `/usr/bin/python3` (`review-root.log:6`). This is a reviewer-host caveat. The frozen T3 log explicitly records rendering and update tests executing successfully and 24 root tests passing (`gate-logs/T3-suite.log:38`, `gate-logs/T3-suite.log:54`), so root coverage rests on that captured evidence rather than the local skipped run. The fix-specific Python red→green ran without an unmet external dependency.
- Prior-art investigation: `git log --all -- template/src/pdca_harness/assemble.py template/tests/test_needs_human_multiline.py` returns only `399cb2e pre-fix base 6ba00bad8e9c7257dacfd4b87c54450ab7259bc9`; `git remote -v` returns nothing. The supplied evidence cannot establish a closed/rejected-work search by affected file path. T5 names the remaining decision. The only available integration document is the uninstantiated template; its human-only list is still TODO (`template/docs/INTEGRATION.md.jinja:80`), so it enumerates no additional concrete human-only checks.

No grounded patch defect found. This review is advisory; the NEEDS-HUMAN rows identify the decisions owed at sign-off.

### Advisory — code-review

# Check advisory — code review (correctness / reuse lens), issue #527

Traced the new loop in `_needs_human` (`template/src/pdca_harness/assemble.py:489-522`)
line by line against the test cases and the gate evidence. No correctness bug found and
no reuse/simplification opportunity worth flagging.

- Loop control is sound: the bullet branch sets `i = j; continue`, so the bottom-of-loop
  `i += 1` never double-advances, and the table branch (now wrapped in
  `if vi is not None:` instead of an early `continue`) still falls through to that same
  `i += 1` — equivalent to the pre-patch control flow (`assemble.py:513-522`).
- `verdict_table` (line indices of the mandated 5/5/1 table) is computed once from the
  original `lines` before the loop and never re-derived, so skipping ahead over a
  bullet's continuation lines can't shift which index the STANDING check
  (`i in verdict_table`, `:520`) tests — table rows and NEEDS-HUMAN bullets are
  mutually exclusive branches, and `_ends_needs_human_continuation` breaks continuation
  scanning the moment it hits a `|` line, so a bullet can never swallow a table row.
- The "one line, never a newline" invariant the brief calls load-bearing for
  `signoff.open_needs_human` (`signoff.py:102-120`, which matches `- [ ] ` per physical
  line) holds end to end: continuation text is `" ".join`-ed (`:510`), never
  `"\n".join`-ed, and the only place §6 items get rendered back to text
  (`assemble.py:603`, `f"- [ ] {it}"`) does no further splitting.
- Dedup (`add()`, `:483-487`) now keys on the full joined text rather than just the
  first line — strictly finer-grained than before, so it can't newly collide two
  distinct multi-line bullets that happened to share a first line; it's a side benefit,
  not a regression.
- Checked the existing bullets in `test_autoiterate.py`, `test_plan_advisory.py`,
  `test_leaf_status.py`, `test_external_dependency_section6.py` that this patch must
  leave byte-identical: all are genuinely single physical lines (the ones assembled from
  multiple Python string literals join into one line with no embedded `\n` before the
  final one), so none exercises the new continuation path — consistent with the T3 gate
  log (1798 tests, OK) and with the C4 gate log showing the new suite's red leg fails
  9/10 and green leg passes 10/10, i.e. a real causal test, not a vacuous one.
- Reuse: the brief's peer callsite `brief._block_for` (`brief.py:70-104`) does something
  visibly similar (indentation-based continuation membership), but its semantics differ
  in two ways that matter here — it *preserves* a block's relative indentation instead of
  flattening to one line, and it treats a blank line as *inside* the block rather than
  ending it. The new code doesn't call it, and the docstring at `assemble.py:459-464`
  and the brief's Scope section both call this out explicitly, so this isn't
  unacknowledged duplication — it's a considered decision not to reuse a helper whose
  contract doesn't fit.

No findings requiring a human or a builder iteration.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — Confirm no merged or closed/rejected work already resolves the affected paths — local history is a single synthetic base without remotes, and the brief's closed-work search uses issue/text rather than affected paths, leaving prior-art equivalence unsettled (`brief.md:70`; affected source: `template/src/pdca_harness/assemble.py:454`).
- [x] Validation — fitness-to-purpose — Decide whether single-line joining and termination at blank/structural lines preserve the complete decision humans need in real advisory artifacts — automated checks establish text retention and checkbox counting, while acceptance of that presentation remains human judgment (`template/tests/test_needs_human_multiline.py:83`, `template/src/pdca_harness/assemble.py:501`).

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
- By / date: Eduard Ralph / 2026-09-15

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
