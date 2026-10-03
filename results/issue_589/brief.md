# Brief — issue 589 / flow-dep-graph-refusal-not-traceback

> The Plan artifact (docs 02 §PLAN). Do reads ONLY this file.

- **Slug:** flow-dep-graph-refusal-not-traceback
- **Defect:** `pdca flow <ids>` over a batch where a brief declares a dependency that is
  neither in the batch nor a COMPLETE bundle ends in a Python traceback. The refusal itself
  is right: `waves.check_dep_graph` (`template/src/pdca_harness/waves.py:51-99`) validates
  the dependency graph before any build and raises `ValueError` naming the bundle and the
  dependency (`waves.py:78-80`), or `ValueError("dependency cycle: …")` for a cycle
  (`waves.py:93`). But nothing on the `flow` path catches it: `flow._drive_and_act` calls
  `waves.compute_waves` strictly (`flow.py:1694`), `flow.flow_ids` reaches it at
  `flow.py:2107`, and `cli._flow_claimed` catches only `flow.PreflightError` around
  `flow.flow_ids` (`cli.py:654-660`); `cli.main` catches only `worktree.WorktreeError`
  (`cli.py:457-461`). So an operator error (a stale `Depends on`, a prerequisite fixed
  outside the cycle whose bundle never reached COMPLETE) reads as a harness crash. Observed
  on getwyrd/wyrd-pdca (v0.58.0):
  `ValueError: issue_736: declared dependency '773' is neither in this batch nor an existing COMPLETE bundle`.
  **Which routes are live on `main`:** only the strict route — ids the operator names
  (`flow_ids` → `_drive_and_act` → `compute_waves`, `flow.py:1694`). The other routes are
  already tolerant and are NOT part of this fix: the `--from-csv` sweep (zero ids) goes
  through `flow_batch`, which runs `waves.partition_schedulable` first (`flow.py:1949`) and
  holds a bad-dep bundle; split adoption re-levels through `_reschedule`
  (`flow.py:1126-1146`), which also holds; and a split parent that is already terminal is
  passed as an adoption seed, outside the strictly levelled `bundles` (`flow.py:2088-2103`,
  `:1700-1703`). The thread's "easy to reach through a split parent's child" route is
  therefore expected to report the child as held on `main`, not raise; the v0.58.0 crash is
  reproduced here through named ids. Do must not change adoption.
- **Success criterion:** Driving `cli._flow` (the function `pdca flow` dispatches to,
  `cli.py:458`) with named ids, where one id's brief declares `Depends on: <X>` and `X` is
  neither in the batch nor a COMPLETE bundle on disk:
  (i) `cli._flow` **returns 2** (does not raise — rc 2 as the issue asks and as the
  `Config.load` operator-error handling does, `cli.py:443-447`; the preflight and claim
  refusals on the same path keep their existing rc 1, `cli.py:615`, `:643`, `:660` — the
  difference is intended, not a bug to "align"); stderr carries **no `Traceback`**, and
  carries the existing message text — the bundle name and the dependency id, e.g.
  `issue_A: declared dependency 'X' is neither in this batch nor an existing COMPLETE bundle`
  — plus the ways out, in one short block: add the prerequisite to the batch; drop the edge
  from the brief if the prerequisite landed outside the cycle; or finish the prerequisite
  first. No bundle is built (Do never runs on any bundle in the batch).
  (ii) A **dependency cycle** among named ids gets the same shape: rc 2, no traceback, the
  `dependency cycle: A → B → A` text on stderr.
  (iii) **Nothing else changes.** `check_dep_graph` / `compute_waves` still raise an
  exception that **is a `ValueError`** — every existing caller and test that expects
  `ValueError` keeps passing unchanged (`tests/test_waves.py:121,127`,
  `tests/test_deps_completed.py:92,101`, `tests/test_flow_slice.py:1077,1088`); `pdca waves`
  keeps its `unschedulable: …` line and rc 1 (`cli.py:1030-1034`,
  `tests/test_flow_slice.py:1252-1258`); the tolerant resume/adoption paths
  (`waves.partition_schedulable`, `flow._reschedule` `flow.py:1126-1145`) are untouched; any
  OTHER `ValueError` escaping `flow_ids` is not swallowed by the new handling (it still
  propagates as today) — pinned by a test (see Test file), so a fix that just catches
  `ValueError` fails. The whole `template/tests` suite stays green.
  Shown by the named test going red on `main` (the call raises `ValueError`) and green with
  the fix.
- **Falsifiability:** RED is reachable offline on the base toolchain (stdlib Python ≥ 3.11 +
  git), stub leaves, empty gates. Today `cli._flow(cfg, args)` with a brief declaring an
  unresolvable `Depends on` raises `ValueError` out of the call — the test catches that as a
  failure (assert the call returns 2). Fixture shape: `tests/test_flow_adopt_recovery.py:47-66`
  (`_stub_config`) and `:135-146` (`_args` / `_cli` calling `cli._flow` with a
  `SimpleNamespace` argv, `no_publish=True, no_act=True`).
- **Invariant to restore:** Every refusal the `flow` command makes for operator input (a
  bad config, a claim held elsewhere, a lane preflight, an unschedulable dependency graph)
  reaches the operator as a short message and a non-zero exit, never as a traceback. Source:
  internal project rule (Tier C) — issue #92's "operator error is not a crash"
  (`cli.py:438-447`, the `Config.load` handling) and the existing `PreflightError` handling
  on the same path (`cli.py:637-643`, `:654-660`).
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Ordering note:** No `Depends on` / `Conflicts with` on purpose: this batch (582, 589, 593,
  597) is meant to run as ONE wave, because the instance driver (v0.58.0) carries #593's
  multi-wave stacking bug. 589 touches `waves.py` + `cli._flow`/`_flow_claimed`; 593 may
  touch `cli._publish_flag` (`cli.py:1041-1062`), far from this hunk — distant hunks in one
  file merge cleanly in sequence.
- **Surfaces:** data
- **Difficulty:** low
- **Scope:** Make an unschedulable dependency graph on the `flow` path for named ids (both CLI
  shapes: one id and several, with or without `--from-csv` — ids plus `--from-csv` still go
  through `flow_ids`, `cli.py:654-656`) end as
  a one-block refusal with rc 2, matching the issue's design: an exception type specific to
  "the dependency graph is unschedulable" that is still a `ValueError`, raised by
  `check_dep_graph` for both the unresolved-dependency and the cycle case, and handled in
  `cli._flow`. Update the one doc sentence that describes the up-front rejection if it
  needs to say what the operator sees (`docs/03-plan.md:102-104`). / out of scope: changing
  WHEN the graph is validated (it stays after the Plan pre-pass, before any build); making
  `flow` tolerant of the bad edge (holding the bundle instead of refusing — that is the
  resume path's behaviour, `waves.py:240-254`, and stays there); `pdca waves`' output and
  rc; the claim scope (`drive_claim.run`, `cli.py:575-576`) — the refusal must still leave
  every claim released, which the existing `with` already does; any handler in the zero-ids
  `--from-csv` branch (`cli.py:637-643`) — `flow_batch` cannot raise this error, so a handler
  there would be dead code; split adoption / `_reschedule`.
- **Repro instruction:** In a stub-leaf config (fixture above), create bundle `A` with an
  authored brief carrying `- **Depends on:** 773`, no bundle `773` on disk; call
  `cli._flow(cfg, SimpleNamespace(issue_ids=["A"], from_csv=None, from_briefs=None,
  no_publish=True, no_act=True, by="", lanes=None, max_passes=None))`. On `main` it raises
  `ValueError: issue_A: declared dependency '773' is neither in this batch nor an existing
  COMPLETE bundle`. Same with two bundles `A`/`B` that depend on each other (cycle).
- **External dependencies:** none
- **Test file:** `template/tests/test_flow_dependency_refusal.py` (new). Import modules only
  (`from pdca_harness import cli, …`) — **never** the new exception class by name: on the
  C4 red leg the production hunks are reverted, so a module-level import of a symbol the fix
  adds fails to load and `engine/scripts/run-verify.sh` reports PDCA-UNVERIFIABLE instead of
  red. Assert on behaviour (return code, stderr text, no build) — not on the exception type.
  Cover: unresolved dependency (single id and two ids), cycle, and that no bundle was built
  (e.g. no `patch.diff` written / `driver.run_issue` not called, as
  `tests/test_flow_slice.py:1068-1082` does). Also cover (iii)'s negative: patch
  `flow.flow_ids` (or a leaf it calls) to raise a plain `ValueError("something else")` and
  assert it still propagates out of `cli._flow` (`assertRaises(ValueError)`). That test is
  green on both legs by design; it guards against an over-broad catch.
- **Citations expected:** Do must cite path:line on the target branch for every change.
  Peer callsite to mirror: the `flow.PreflightError` handling in `cli._flow_claimed`
  (`cli.py:637-643` and `:654-660` — print `flow: {exc}` to stderr and return), and the
  `Config.load` error shape (`cli.py:438-447`, rc 2). The raise sites are `waves.py:78-80`
  and `waves.py:93`.
- **Prior-art check (triage cycles):** Merged history by path —
  `git -C ../pdca-harness log --oneline origin/main -n 5 -- template/src/pdca_harness/waves.py`:
  last touched by #191 (`5214d77`, `54a35f6`: hold a bad-dep bundle in the RESUME sweep —
  the tolerant path; the strict `flow <ids>` path was deliberately left raising) and #171;
  `cli.py`: recent commits (#409, #545, #566, #565) don't touch this handling. Closed-unmerged
  PRs touching `waves.py`/`cli.py`/`flow.py`: #598, #599, #600 (auto-iterate / gate re-run /
  size-signal — unrelated; superseded by the #615 integration merge). No open PR. No earlier
  issue covers it. Result: not fixed, not in flight.
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.

Plan-review response: all five findings accepted — live-route statement added (only named
ids are strict on `main`; adoption and the zero-id CSV sweep are tolerant and out of scope);
the `--from-csv` conditional replaced by the decision; line numbers corrected against
`origin/main` 24c7f83; a negative test pinned for (iii); rc 2 vs rc 1 stated as intended.
