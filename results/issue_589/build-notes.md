# Build notes — issue 589 / flow-dep-graph-refusal-not-traceback

Target: eduralph/pdca-harness @ main (`24c7f83`), worktree `pdca-harness.pdca-wt-l1`.
Line numbers below are post-patch in that worktree.

## What changed

1. `template/src/pdca_harness/waves.py:51-62` — new `DependencyGraphError(ValueError)` with a
   `remedy` attribute (the one-line "ways out").
2. `waves.py:93-98` (was `:78-80`) — the unresolved-dependency raise now raises
   `DependencyGraphError`, same message text, remedy: "add <dep> to this run's ids; or, if it
   landed outside the cycle, drop the edge from <bundle>'s brief; or finish <dep> first".
3. `waves.py:111-114` (was `:93`) — the cycle raise now raises `DependencyGraphError`, same
   `dependency cycle: A → B → A` text, remedy: drop one edge of the cycle from its brief.
4. Docstrings of `check_dep_graph` (`waves.py:65-72`) and `compute_waves` (`waves.py:166-169`)
   name the new type.
5. `template/src/pdca_harness/cli.py:661-667` — in `_flow_claimed`, next to the existing
   `except flow.PreflightError` around `flow.flow_ids` (`cli.py:657-660`, the peer the brief
   cites), `except waves.DependencyGraphError` prints `flow: <message>`, a "no bundle was
   built" line and `Ways out: <remedy>.` to stderr, and returns 2 (mirrors the `Config.load`
   rc 2 shape at `cli.py:443-447`). `cli._flow` returns whatever `_flow_claimed` returns, so
   `cli._flow` returns 2; the `with drive_claim.run(cfg)` scope in `_flow` still releases claims.
6. `docs/03-plan.md:102-106` — the "rejected up front" sentence now says `pdca flow` exits 2
   before building, naming the bundle/dependency (or cycle) and the ways out.
7. New test `template/tests/test_flow_dependency_refusal.py`.

## Why this shape

- The brief asked for an exception type specific to "unschedulable graph" that is still a
  `ValueError`, handled in the CLI. That is what this is. Catching plain `ValueError` would
  swallow unrelated faults — pinned by `test_other_value_error_still_propagates`.
- I put the handler in `_flow_claimed` rather than wrapping `_flow`'s `with` block: it sits
  right beside the `PreflightError` peer around the same `flow_ids` call, and the brief says not
  to add a handler in the zero-ids `--from-csv` branch (`flow_batch` can't raise this). Ids plus
  `--from-csv` also go through this same `flow_ids` call, so both CLI shapes are covered.
- The remedy lives on the exception (set at the raise site) because the right advice differs:
  an unresolved dep has three ways out, a cycle has one (drop an edge). Building the advice in
  the CLI would need it to re-parse the message to tell the two apart.
- No change to when validation runs, to `partition_schedulable`, `_reschedule`, adoption, or
  `pdca waves` (`cli._waves` still catches `ValueError`, which the subclass still is).
- rc 2 here vs rc 1 for preflight/claim refusals is intended per the brief.

Ruled out: a generic `except ValueError` in `_flow` (over-broad; fails the negative test);
catching in `flow._drive_and_act` and returning a result map (changes flow's contract and the
existing `tests/test_flow_slice.py:1077,1088` that expect `ValueError` out of `flow_ids`).

## Verification

- C4 runner (`engine/scripts/run-verify.sh`, the project's gate) on this patch:
  green leg `Ran 4 tests … OK`; red leg `Ran 4 tests … FAILED (failures=3)`;
  `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`.
- Full offline suite: `cd template && PYTHONPATH=src python3 -m unittest discover -s tests` —
  `Ran 2219 tests … OK (skipped=2)`.
- Existing `ValueError` expectations: `tests.test_waves`, `tests.test_deps_completed`,
  `tests.test_flow_slice` + the new test — `Ran 127 tests … OK`.
- T2 docs check (`engine/scripts/run-docs-check.sh`): `docs lint clean, site render + link
  audit clean`.
- Commit-readiness: the repo has no formatter / pre-commit config; its only commit rule is the
  DCO `Signed-off-by` trailer (CONTRIBUTING.md:7-17), which publish adds with `commit -s`. All
  added lines are ≤ 100 columns, matching the files' style.

## Self-refutation

- **(a) Genuine red?** Yes. The C4 runner reverts the production hunks (`waves.py`, `cli.py`)
  and re-runs: 3 of 4 tests fail, each with `AssertionError: \`pdca flow A\` raised instead of
  refusing: ValueError: issue_A: declared dependency '773' is neither in this batch nor an
  existing COMPLETE bundle` (and the cycle equivalent). The 4th test
  (`test_other_value_error_still_propagates`) is green on both legs by design, as the brief says.
- **(b) Production path?** Yes. The tests call `cli._flow` — what `pdca flow` dispatches to —
  which runs the real `flow.flow_ids` → `_drive_and_act` → `waves.compute_waves` →
  `check_dep_graph`. Nothing in that chain is mocked. Only `driver.run_issue` is wrapped (it
  still calls the real one) to count builds; the negative test replaces `flow.flow_ids` on
  purpose to inject an unrelated `ValueError`.
- **(c) Fixture includes the fault?** Yes. The briefs on disk carry the real bad edge
  (`Depends on: 773` with no bundle 773; `A ↔ B` for the cycle), parsed by the production brief
  parser. The two-id case includes a healthy bundle `B` alongside, and the test checks neither
  bundle was built (no `patch.diff`, state still PLANNED, `driver.run_issue` never called).
