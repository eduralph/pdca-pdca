# Brief — issue 527 / section6-keeps-whole-needs-human-bullet

- **Slug:** section6-keeps-whole-needs-human-bullet
- **Defect:** a `- NEEDS-HUMAN` bullet that wraps onto indented continuation lines reaches
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
- **Success criterion:** offline, on the template driver suite:
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
- **Falsifiability:** RED on the offline driver suite. Pre-fix, a bundle whose
  `check-advisory-*.md` carries a multi-line `- NEEDS-HUMAN [impl] — …` bullet (the 462 shape)
  renders a §6 item that lacks the bullet's last sentence, so an assertion that the item text
  (via `assemble.collect_needs_human`) and the SUMMARY §6 line contain it fails. The test uses
  only pre-existing API (`assemble.assemble_summary`, `assemble.collect_needs_human`,
  `signoff.open_needs_human`), so the red leg is a real assertion failure.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Conflicts with:** none
- **Ordering note:** run 3 of plan-0.60-bug-order.md, one wave with 534, 467, 480 and 529.
  Only this bundle edits `assemble.py`; no other bundle in the run touches it.
- **Surfaces:** data
- **Difficulty:** low
- **Scope:** `_needs_human` keeps a NEEDS-HUMAN bullet's full text, continuation lines
  included, as one single-line §6 item, per the criterion. One function in `assemble.py`.
  / out of scope: `leaves._plan_findings`' line count (`leaves.py:3141`), which counts bullets
  and is unaffected; the table branch; multi-paragraph bullets (a blank line ends the item);
  the §1–8 brief-field rendering (#336, already fixed); rewording any leaf prompt to forbid
  wrapped bullets.
- **Repro instruction:** on `main`, in `template/`: using the `_bundle` fixture of
  `template/tests/test_autoiterate.py:77-95`, create a bundle whose
  `check-advisory-adversary.md` is
  `"- NEEDS-HUMAN [impl] — src/x.py:12 (`f`):\n  the bound counts sleep seconds, not\n  wall-clock time, so it overshoots.\n"`,
  then read `assemble.collect_needs_human(d, cfg)`: the single item's text is
  ``src/x.py:12 (`f`):`` and "overshoots" appears nowhere in `SUMMARY.md` §6.
- **External dependencies:** none — offline; base toolchain only (python3 ≥ 3.11)
- **Test file:** template/tests/test_needs_human_multiline.py (new)
- **Citations expected:** Do cites path:line on `main` for every change. Peer callsites: the
  continuation rule already solved for brief fields is `brief._block_for` / `whole_field`
  (`template/src/pdca_harness/brief.py:37-106`, #336): membership by indentation deeper than
  the field's own bullet. Here the result is flattened to one line rather than kept as a
  block, because §6 items are one line each. The test fixture to mirror is
  `test_autoiterate.py:77-95` (`_bundle`), and the IMPL assertion shape is
  `test_advisory_impl_marker_auto_iterates_and_text_is_clean` (`:130-135`).
- **Prior-art check (triage cycles):** by path on origin/main (fetched 2026-09-15):
  `git log -- template/src/pdca_harness/assemble.py` shows `07766ed`, `a5a4d25`, `6f32bd5`,
  `7fe6aa0`, `cad9601`; none changes the bullet branch of `_needs_human`. No open PR touches
  `assemble.py` (open: #542, #543). No closed/merged PR references #527. `gh search issues
  "NEEDS-HUMAN multi-line"` finds nothing else. Filed from the instance's 2026-08-15 Act review.
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.
