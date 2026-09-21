# Build notes — issue 549 / csv-batch-plan-reap-rereads-the-briefs-it-wrote

## What changed and why

The gap: `handoff.stop_problems` (`handoff.py:616-693` on the fixed tree; `:571-625` on
base `70ea12b`) only re-reads bundle artifacts when the driver registered a bundle set at
spawn. On the CSV/default batch Plan path the planner picks its ids mid-session, so
`do_plan_batch` passes `seeded = []` (`leaves.py:1197-1199`), and the reap fell straight to
the "no registered bundle set → require a passing `/handoff`" tail. A `/handoff` passed for
one id (e.g. `issue_7`) made `state.get("passed")` truthy, so nothing about a different,
malformed brief the same session wrote (e.g. `issue_8` with an empty Success criterion)
was ever reported.

Fix shape: for a **planner** session, `handoff.session` (`handoff.py:409-483`) now takes a
content-hash snapshot of every `issue_*/brief.md` under `cfg.bundle_root` at session start
(`_brief_sha`, `handoff.py:293-298`, deliberately mirroring — not importing —
`leaves._brief_sha`, `leaves.py:3250-3253`) and stores it in the session's `baseline` dict,
the same channel the `act` role already uses for its append-only check
(`handoff.py:462-470`, mirroring `handoff.py:426-441`/`:551` from the brief's citation).
At reap, when no bundle set was registered, `stop_problems` (`handoff.py:616-693`) now
computes `_changed_plan_briefs` (`handoff.py:301-317`) — every bundle whose brief is new or
whose bytes differ from the baseline, mirroring `leaves._fresh_plan_briefs`'s "new or
rewritten" rule (`leaves.py:3652-3669`) — and re-reads each one with `check_bundle`, bundle-
prefixed, exactly like the registered path does. Only when nothing changed does it fall
through to the pre-existing "passed `/handoff`, else 'registered no bundle set…'" logic, so
that behavior is untouched for every unchanged-brief and Act-role case (`handoff.py:690-693`).

Three docstrings (module top `:13-27`, `session` `:441-450`, `report_at_reap` `:524-530`,
`stop_problems` `:622-641`) and `docs/01-render-and-integrate.md:179-185` were updated to
stop promising "does not re-read what that session wrote" for the planner-without-bundles
case, per the brief's Scope.

## What I ruled out

- **Importing `leaves._brief_snapshot` / `_fresh_plan_briefs` into `handoff.py`.** The
  brief's Scope explicitly forbids this ("do not import `leaves` into `handoff.py`, which
  is kept import-light for the hook, `handoff.py:120`, `:392`"). `leaves.py` already does a
  local, deferred import of `handoff` in a couple of places; a module-level import the other
  direction would create an import cycle risk and defeat the module's own "kept import-light
  for the hook" design note (`handoff.py:1-37`). Cost of NOT ruling this out: one import
  line looks cheaper than ~25 lines of mirrored logic, but it contradicts an explicit Scope
  line in the brief, so I mirrored the two small helpers instead (`_brief_sha`,
  `_changed_plan_briefs`, `handoff.py:293-317`, ~25 lines total).
- **Snapshotting only when `bundles` is empty at `session()` time.** `bundles` is a
  parameter of `session()`, known at call time, so I could have branched the baseline
  capture on `not bundles`. I didn't: the id-seeded batch path also calls `session(cfg,
  "planner", seeded, ...)` with `seeded` sometimes empty when `ids` is `[]` — an edge case
  that would then silently lose the new re-read. Snapshotting unconditionally for every
  planner session costs one extra `glob` + per-file `read_bytes` at session start (bounded
  by however many `issue_*` dirs exist), and the snapshot is simply unused by
  `stop_problems` whenever `bundles` is non-empty (that branch returns before touching
  `state["baseline"]` at all, `handoff.py:668-674`), so there's no behavior cost to the
  registered paths — only a small, bounded I/O cost at every planner session start.
- **Treating a placeholder-brief-that-stays-a-placeholder as "changed".** I don't consult
  `brief.is_placeholder` when building the baseline (unlike `leaves._brief_snapshot`, which
  excludes placeholders from the "before" map). The brief's criterion (ii) says
  byte-unchanged is byte-unchanged, "even if malformed" — it doesn't carve out placeholders,
  and `check_planner` (`handoff.py:102-143`) already reports a placeholder brief as its own
  problem when a bundle DOES get checked. Simpler rule, same outcome for the cases the brief
  specifies.
- **Making the reap blocking, or writing anything back into the bundle.** Out of scope per
  the brief; nothing in the diff writes, moves or deletes a file under the project root —
  confirmed by the existing `ReportOnly.test_the_reap_changes_nothing` subtests, which still
  pass unmodified with `role="planner", bundles=None`.

## Verification

- `PYTHONPATH=src python3 -m unittest tests.test_handoff_reap` — 33 tests, green post-fix.
- `PYTHONPATH=src python3 -m unittest discover -s tests` (the project's `make check`
  target, `template/Makefile:73-74`) — 1925 tests, green post-fix (2 skips pre-existing and
  unrelated — Docker-backed C4/T5 gates and a stub git-remote warning, both present before
  this change too).
- Red/green: swapped `handoff.py` back to the base `70ea12b` version (keeping the new test
  hunks) and reran `tests.test_handoff_reap.ReportedAtReap` — the two new tests exercising
  criteria (i) and (iv) failed for the expected reason (`AssertionError:
  "issue_8: brief.md field 'success criterion' is empty" not found in ''`, and the "no
  brief was" the pre-existing "registered no bundle set" line appearing where nothing should
  print). All 11 other `ReportedAtReap` tests, including the two new ones covering (ii) and
  (iii), stayed green on the base tree, confirming they exercise the untouched code paths
  correctly and aren't accidentally red for the wrong reason. Restored the fixed
  `handoff.py` and reran the whole module: 33/33 green.

### The three refutation questions

**(a) Genuine red?** Yes — see the red/green run above: reverting only `handoff.py` to
`70ea12b` (test hunks kept) turns `test_csv_batch_reports_a_brief_it_wrote_after_a_handoff_for_another_id`
and `test_csv_batch_briefs_that_all_pass_report_nothing_even_without_a_handoff` red, for the
exact reason the brief's Falsifiability section predicts (empty stderr where an item is
expected).

**(b) Production path?** Yes — the test drives `handoff.session` and `handoff.stop_problems`
directly (`Base.reap`, `test_handoff_reap.py:173-191`), the same functions
`do_plan_batch` calls in production (`leaves.py:1198-1199`); no stand-in or mock is
introduced. `do_plan_batch` itself is untouched, per Scope — the fix lives entirely inside
`handoff.py`, so exercising `handoff.session`/`stop_problems` directly is exercising the
real changed code, not a copy of it.

**(c) Fixture includes the fault?** Yes — the new tests write the malformed
(`criterion=""`) brief and the "another id passed /handoff" state *inside* the `during`
callback, i.e. genuinely mid-session, reproducing the exact fault shape the brief's Defect
section describes (a `/handoff` for one id papering over a different bundle's bad brief).
`test_csv_batch_does_not_reread_a_brief_that_predates_the_session` deliberately writes its
malformed brief *before* `reap()` is called (before the session starts) to prove criterion
(ii) the other way — that this is NOT a false green from "everything gets rechecked
unconditionally."

## Formatter / commit hooks

No `.pre-commit-config.yaml`, `ruff`, `black`, or `flake8` config exists anywhere in this
checkout (checked `find`/`grep` across the repo root and `template/`), and `template/pyproject.toml.jinja`
declares no such tool. `python3 -m py_compile` on both touched Python files passes. Line
lengths in my new hunks stay in the same ~88-93 char band already used throughout
`handoff.py` (e.g. existing lines `handoff.py:117-118`, `:210` pre-date this change at
90-93 chars) — no reformatting was warranted or performed.
