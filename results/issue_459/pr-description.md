# PR description

## Summary
**User impact:** accepting a split proposal files real tracker sub-issues that cannot
be withdrawn — and nothing ever tells you whether the split actually made the work
smaller. A split whose children are all just as big as the parent is only discovered a
full cycle later, when each child's own size warning fires and points you back at
splitting again. Operators who file the child issues by hand (the `--ids` route, the
required one when the tool cannot reach the tracker) got no feedback of any kind before
their issues and bundles became permanent.

This PR makes both acceptance routes print a convergence report — does this split make
the children smaller? — at the last moment the answer can still change the decision,
before anything irreversible happens. The report is purely informational: it never
blocks, never prompts, and never changes what is filed or created.

Reported in [#459](https://github.com/eduralph/pdca-harness/issues/459).

## What to look at
The report itself and the guarantee around it. Run `pdca split <id> --accept` (or
`--accept --ids a,b`) on any proposal: before any issue is filed or bundle created, you
now get one line per child comparing its size band to the parent's, and a plain verdict
— "converged", "NOT CONVERGED — the children do not band lower", or "NOT CONVERGED —
every pair of children declares a conflict, so the split separated nothing".

Two things worth a close look:

1. Because the report is advisory, its own output must never be able to abort an
   acceptance. Try `pdca split <id> --accept 2>&1 | head` — the pipe breaks both
   streams part-way, and the exit code and created bundles must be unchanged.
   Previously this produced either a traceback after the bundles were already on disk,
   or a flatly wrong "no split-proposal.md" refusal.
2. The pairwise-conflict verdict has to survive #457's sibling-conflict exclusion:
   with that exclusion active, conflicting children *look* clean in their scores, and
   the report must not be fooled by that.

## Root cause
`preflight` (pre-fix `split.py:224-245`) checked only the reasons acceptance would
*fail* — missing proposal, parent already split, bad ordering — never whether the split
converges; and the `--ids` path (pre-fix `cli.py:764`) called `accept` directly without
running `preflight` at all. Separately, output on the acceptance path was only
piecemeal-guarded: a `BrokenPipeError` escaping `preflight` was caught by `cli._split`'s
`except OSError` and misread as "no proposal" (rc 1 on a good proposal), and one raised
by the status line after `accept` returned became an unhandled traceback with the
irreversible half already done.

## Fix
- `split.convergence_report` (`split.py:393-466`) stages each child through the same
  `materialise()` writer acceptance uses, into a `TemporaryDirectory`, with sibling
  *labels* standing in for the not-yet-existing tracker ids — so the staged bundle is
  scored by `sizing.estimate` exactly as the live one will be, including #457's
  sibling-conflict exclusion. It returns lines; it prints nothing and writes nothing
  into the instance.
- The pairwise-conflict verdict reads `SizeEstimate.sibling_conflicts`
  (`split.py:373-390`), the count #457 exposes — never the score or reasons those
  declarations were excluded from. On an estimator without that count, the sibling
  edges are read from the proposal's own ordering fields (identical by construction —
  `_validate_ordering` has just proven every ref names a sibling) and the report says
  so explicitly rather than substituting silently.
- `preflight` emits the report last (`split.py:305`), after `_validate_ordering`; and
  `cli._split` hoists proposal parsing + `preflight` above the `if not ids:` branch
  (`cli.py:756-776`), so `--accept --ids a,b` reaches it too. `accept()` re-runs every
  check itself, so the hoist only moves refusals (and the report) earlier — it changes
  nothing about what is filed or materialised.
- One guarded writer, `split.advisory` (`split.py:238-273`), now carries *every* write
  on the acceptance path — the report, all eleven `cli._split` lines (stdout `print`
  of created bundles included), the rollback/restore notices, and `file_children`'s —
  so "output can never abort an acceptance" is a property of the whole path, not of
  the writes someone remembered to wrap. A report whose *computation* fails is named
  on the same guarded stream and skipped (`split.py:469-488`), never raised.
- `docs/07-crosscutting.md` documents the report in the `pdca split` section.

## Verification
- **Claim:** both acceptance routes emit the report before anything irreversible.
  **Checked:** `cli.py:756-776` — parse + `preflight` (which emits the report at
  `split.py:305`) run before `file_children` and before `accept` on both shapes.
  **Test:** `template/tests/test_split_convergence.py` —
  `test_the_ids_path_reports_before_it_materialises_anything` and
  `test_the_auto_filing_path_reports_before_a_single_issue_is_filed` assert the report
  is on the stream before the irreversible call executes.
- **Claim:** the report bands each child against the parent, names the driving
  feature, and says plainly when most children do not band lower.
  **Checked:** `split.py:393-466`. **Test:** the criterion-(b) tests cross-check the
  bands against the same estimator the report calls, so they cannot drift.
- **Claim:** the pairwise-conflict verdict is not blinded by #457's exclusion.
  **Checked:** `split.py:373-390` reads the exposed count, never the score. **Test:**
  `test_the_sibling_conflict_count_is_read_from_the_estimate_not_its_score` feeds an
  estimate whose score/reasons are clean and whose count is 1 — a score-reading report
  passes it vacuously; and the report was run live on a base with #457 in force,
  printing `[1 sibling conflict(s) declared]` and `NOT CONVERGED … separated nothing`.
- **Claim:** advisory output can never change the exit code or the created-bundle set.
  **Checked:** every write on the path goes through `split.advisory`
  (`split.py:238-273`); no bare `print` remains in `cli._split`. **Test:** the
  criterion-(d) tests drive a stream that, once broken, raises on *every* subsequent
  write and on flush (what a real broken pipe does) — from the first write, from the
  post-accept status line, and on stdout — asserting rc 0, the exact bundle set on
  disk, and that the stream really was hit (`raised >= N`).
- **Claim:** nothing is written into the instance and nothing survives the report.
  **Checked:** `split.py:344-370` stages into a `TemporaryDirectory`; labels are
  pinned to `child-\d+` so no composed path can traverse. **Test:**
  `test_the_report_writes_nothing_into_the_instance`.
- **Regression suite:** the new module (19 tests) fails pre-fix — 4 failures,
  15 errors with the production hunks reverted — and passes post-fix; the full offline
  driver suite (1,719 tests) and the root render/`copier update` compatibility suite
  (7 tests, copier importable, not skipped) pass with the patch applied.

Fixes #459
