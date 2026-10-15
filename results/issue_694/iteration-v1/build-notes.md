# Build notes — issue 694 / reissue-after-conflict-hold-names-the-partner

Target: `eduralph/pdca-harness` @ main, built on the wave-2 stack base
`pdca-integration/main-r547f8028520f` at `a2e38fe` (672, 693 and 673 folded in). All
`path:line` below are on that tree with the patch applied.

## What changed

1. `template/src/pdca_harness/integrate.py`
   - `_Conflict` (`:99-107`) now carries `paths`, the files the merge left conflicting.
     `_merge_published` passes them (`:723`). Before, only the message text had them.
   - `fold` gets a new keyword `clashes` (`:321`, docstring `:438-441`). Under `skipped`,
     when a bundle's merge raises `_Conflict`, the fold calls `_clash` and records
     `clashes[name] = (kind, partners, paths)` (`:592-597`). It is only computed when the
     caller passes `clashes`, so the in-run folds and direct callers are unchanged.
   - New `_clash` (`:1128-1163`), the partner finding the brief pins:
     1. Try the head on `<base_remote>/<base>` alone. If that conflicts, the result is `"base"`
        with no partner (criterion 2).
     2. Else try it on base + each `(name, head)` already on the line at the time of the
        conflict. That is the fold's `took` for this pass: bundles merged in this fold, plus
        ones `_merge_published` found already on origin's line (`_in_line` early return,
        which still lands in `took`). A partner is any id where the trial fails on the second
        merge (index 1), i.e. its change and X's conflict.
     3. A partner whose head holds another partner's head (it was built on it, e.g. `21` cut
        from a line that holds `10`) is dropped, so only the id whose own change clashes is
        named. Without this, asking `[10, 21, 11]` would also blame `21`.
     4. No partner left → `"line"`: the conflict is with other work on the line; only the
        files are named.
     I used the existing `_trial` (`integrate.py`, #674) rather than a raw `_merge` +
     `_reset_line`. `_trial` is exactly that: `_merge` on a detached HEAD, then the tree is
     reset and the branch is checked to be back at its tip, raising `_LineBroken` if not. So
     it meets the brief's "trial `_merge` in the carry's worktree, undone" and reuses the
     #674 code instead of a second copy. A trial that fails with no conflicting path
     (a plain `IntegrationError`) makes `_clash` return `None`, so the carry falls back to the
     old message rather than stopping; tree/line errors still raise.
2. `template/src/pdca_harness/flow.py`
   - `_fold_lines` passes `clashes` through (`:921`, `:951`, docstring `:939-941`).
   - `_CARRY_HINTS` gets three hints (`:1000-1016`, new entries `:1008-1015`). `"conflict"` uses the end-of-run wording
     of `_report_conflict_holds` (`flow.py:1241-1250`): declare `Conflicts with: <ids>` in
     the held bundle's brief, then rebuild it on a base that holds the partners.
     `"base_conflict"` and `"line_conflict"` name no bundle id.
   - New `_clash_why` (`:1019-1035`) builds the reason. It keeps the phrase
     "its branch <ref> does not merge cleanly onto the line": five existing tests in
     `test_flow_resume_stack_prereqs.py` (`:561`, `:577`, `:632`, `:670`, `:734`) assert it
     for base conflicts, and criterion (3) needs them green. The "cross-wave overlap" text is
     gone from these lines.
   - `_carry_finished` (`:1124`, `:1153-1173`) collects `clashes`, overrides the `open`
     reason/hint for each clashed id that is in `skipped` and not in `holds` (the #672
     `built_on` hold still wins), and passes `partners` / `ids` / `base` to the hint format
     (`:1190-1198`). Docstring updated (`:1093-1098`; `_clash` at `integrate.py:1128`, `_trial` at `integrate.py:1166`).
3. `docs/07-crosscutting.md` — carry paragraph: new paragraph after the #672 text
   describing the three outcomes, and the "known limits" entry now says the conflicting pair
   is named.
4. Test: `template/tests/test_flow_reissue_after_conflict_hold.py` (new).

Run-2 lines the fix now prints:

```
flow: issue_11 (finished in an earlier run) is not carried onto pdca-integration/main-r…: its branch origin/fix/11 does not merge cleanly onto the line — its change conflicts with issue_10's (shared.txt), finished in this batch and on the line — holding issue_20 this run; proposed, for you to confirm: declare `Conflicts with: 10` in issue_11's brief, then rebuild issue_11 on a base that holds issue_10, then re-issue.
flow: issue_11 (finished in an earlier run) is not carried onto pdca-integration/main-r…: its branch origin/fix/11 does not merge cleanly onto the line — its change conflicts with origin/main itself (shared.txt) — holding issue_20 this run; rebuild issue_11 on the current origin/main (or update its branch from it, resolving the conflict), then re-issue.
```

## Ruled out

- Reusing the fold's `held_out` / `_held_by` unchanged: ruled out by the brief. It judges
  against the line "as the wave found it", which on a re-issue already holds `issue_10`.
- Finding partners in `flow.py` after the fold: the fold's worktree, lock and per-pass `took`
  are only available inside `fold`; doing it outside would need a second worktree checkout
  and lock scope. Recording inside the fold costs one keyword and ~6 lines at the skip site.
- Dropping the "does not merge cleanly" lead: broke five existing carry tests (seen on the
  first full-suite run); keeping it is accurate and costs nothing.

## Known gaps (out of scope or edge)

- Partners are judged against the line at the moment of the conflict in the pass where it
  happened. If a later #672 pass takes a named partner off the line, the line still names it
  (the conflict between the two is real either way).
- Which of the pair is carried is unchanged (the one asked for first), as the brief says.

## Test runs

- Template suite (`cd template && PYTHONPATH=src python3 -m unittest discover -s tests`,
  the CONTRIBUTING.md command): `Ran 2493 tests … OK (skipped=2)`, including all of
  `test_flow_resume_stack_prereqs.py` and `test_flow_same_wave_conflict.py` (criterion 3).
- C4, `engine/scripts/run-verify.sh` with `PDCA_BUNDLE` / `PDCA_WORKTREE`:
  `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`.
- T2, `engine/scripts/run-docs-check.sh`: lint clean, render + link audit clean.
- Commit hooks: the target has no pre-commit config, formatter or hooksPath; CONTRIBUTING.md
  asks for DCO sign-off (publish adds it) and a green offline suite. No new line over 100
  columns (the three over it in `flow.py` are pre-existing).

## Self-refutation

- **(a) Genuine red? Yes.** C4's red leg reverts the production hunks and keeps the test.
  Criterion (1) fails on `assertIn("issue_10", said)`, with the exact defect line: "…does not
  merge cleanly onto … — an undeclared cross-wave overlap; … get issue_11's PR open … `pdca
  publish 11` …". Criterion (2) passes before the fix too. That is expected: the brief names
  only (1) as the RED, and (2) guards against the fix wrongly naming a partner when the clash
  is with the base.
- **(b) Production path? Yes.** Both runs go through `flow._drive_and_act` →
  `_carry_finished` → `_fold_lines` → `integrate.fold` → `_merge_published` / `_clash` /
  `_trial` against real git (a bare origin plus a checkout). Only the build leaf, the publish
  leaf (which still pushes a real branch), `draft_texts` and `gh` are stubbed, as in the
  existing `SameWaveConflict` suite. The test imports modules only.
- **(c) Fixture includes the fault? Yes.** Run 1 really holds `issue_11` (asserted: the
  "held out of the integration fold" line), and before run 2 the test asserts `10`, `11`,
  `12`, `21` are COMPLETE and that `merged.pr_state` through the stub reports each PR OPEN
  with its real head. So the carry really reaches the fold and the fold really hits the
  conflict on origin's continued line, which already holds `issue_10`. Case (2) really
  moves the base (`_push_from_human` to `main`) and checks that no line of the run is left
  on origin (run 1 drives one wave, so it never pushed one), so the carry starts fresh from
  the changed base.
