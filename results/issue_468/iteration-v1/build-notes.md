# Build notes — issue #468 (flow entrypoint parity)

## What changed, and why

**`template/src/pdca_harness/cli.py:558-633`** (`_flow`): the single-id branch
(`len(ids) == 1`) and the multi-id branch used to be two structurally different code
paths — pre-fix `cli.py:602-657` (base `f7876f2`):
- single-id: a pre-run short-circuit on raw disk state (`state.state(d) == COMPLETE` /
  `RESOLVED`, `cli.py:604-636`) duplicating the RESOLVED-revalidation `flow_ids`
  already does, then a bare call to `flow.flow` (`cli.py:639`) which returns a state
  **string**, no `try/except` around it;
- multi-id: `flow.flow_ids` (`cli.py:651-654`) inside `try/except PreflightError`,
  returning a results **map**, presented by `_report_batch`.

Fixed by deleting the single-id short-circuit and the duplicate RESOLVED-revalidation
block, and routing `len(ids) == 1` through the exact same `flow.flow_ids(cfg, ids,
plan_missing=True, ...)` call the multi-id branch already makes — literally one call
site now, one `try/except PreflightError` around it, one results map. The
`len(ids) == 1` branch that remains is pure **presentation**: it reads the map (or,
for an id that never entered it — already-terminal, skipped before driving — re-reads
live disk state) and prints the single-id shape (`state<TAB>path`, the §6 listing, the
rc-0-at-AWAITING_SIGNOFF rule). `flow.flow` itself is untouched — it's still the
primitive `flow.flow_ids`/`_drive_and_act` and `flow.flow` both call into
(`_drive_wave` → `driver.advance`), and it's still exercised directly by
`tests/test_flow_slice.py`, `test_sweep.py`, `test_signoff_orphan.py` and others; only
`cli._flow`'s *routing* changed.

**`template/src/pdca_harness/flow.py:659-673,1044-1046`**: the terminal-skip message
`flow_ids` already prints for any id that's terminal *before* this run (`_TERMINAL`,
`flow.py:1039-1043` pre-fix) is now lineage-aware — `_split_recovery_hint` reads
`split.read_lineage(d)` (`split.py:373`) and, if the bundle carries a `children` edge
(written only by `split.accept`, `split.py:635` — "`children` iff split",
`split.py:392-395`), appends "drive them instead: `pdca flow <child-ids>`" instead of
staying silent. Since both CLI shapes now go through this ONE print, the destructive
`rm -rf` hint that used to live only in `cli.py`'s single-id short-circuit is gone
everywhere, by construction — not patched over with a special case for split parents.

## Alternatives considered

**Make `flow.flow` a thin wrapper over `flow_ids`** (the brief's other suggested
shape) instead of changing `cli._flow`'s routing. Rejected: `flow.flow` is a public,
heavily-used primitive (7 direct call sites across `test_flow_slice.py`,
`test_sweep.py`, `test_signoff_orphan.py`, all asserting on its **string** return) —
turning it into a map-returning wrapper would mean either breaking its signature
(touching every one of those call sites) or unwrapping the map back into a string at
the end of `flow.flow` itself, which just moves the "state-string vs results-map"
seam one function down without removing it. The `cli._flow` routing change is a
~50-line diff confined to one function; the `flow.flow` wrapper option would touch
`flow.py`'s public contract plus 7 test files for no behavioural gain the brief asks
for.

**Add a `split`-lineage check only in `cli.py`'s short-circuit** (patch the symptom,
keep the two drive paths). Rejected on the brief's own terms — the brief's diagnosis
is that a *new route each round* is the recurring failure across #449's five
iterations, not any single divergence; adding a sixth special case (`is this bundle a
split parent?`) to the short-circuit would be the same shape of fix that produced the
first five breaks. It would also do nothing for the "state-string vs results-map"
half of the defect (the multi-id shape already had no `rm -rf` bug — the destructive
message existed ONLY on the un-unified single-id path).

## Existing tests touched (not the new test file)

- `template/tests/test_flow_slice.py:1711-1719` — `MaxPassesConfig._run_cli` mocked
  `cli.flow.flow` and asserted it was called for a single id; that's the exact
  implementation detail this change replaces. Updated the mock target to
  `cli.flow.flow_ids` (returning a results map) — the assertion under test (CLI-flag
  config plumbing reaches the drive call) is unchanged, only the drive **entry point**
  it observes is.
- `template/tests/test_state_resolved.py:405-422` —
  `test_single_id_flow_exits_zero_on_a_resolved_bundle` asserted the OLD single-id-only
  remediation text ("resolved outside a cycle …"). That text lived in the
  cli.py block this change deletes (`RESOLVED revalidation already exists in
  `flow_ids`... — do not duplicate it`, brief Scope). Updated the assertion to the
  message both shapes now print (`flow_ids`'s terminal-skip line,
  `flow.py:1040-1043`); `rc == 0` (the behaviour actually under test) is unchanged and
  still asserted.

Both are genuine implementation-detail updates forced by the routing unification the
brief authorizes, not a weakening of what either test verifies.

## Test file — the three refutation questions

**(a) Genuine red?** Yes. Reverted `cli.py` + `flow.py` alone (kept the new test file
and the two edited pre-existing tests) and reran
`PYTHONPATH=src python3 -m unittest tests.test_flow_entrypoint_parity -v` against
`f7876f2`: 6 of 8 tests fail/error —
`test_complete_bundle_agrees_across_shapes`, `test_resolved_bundle_agrees_across_shapes`
(pre-fix, the COMPLETE/RESOLVED state line prints to **stderr**, not stdout — the
short-circuit's own asymmetry), `test_single_id_routes_through_flow_ids_not_flow`
(pre-fix, `flow.flow_ids` is never called for a single id),
`test_preflight_error_same_rc_and_message_both_shapes` (pre-fix, `flow.PreflightError`
from the single-id path propagates **uncaught** out of `cli._flow` — no
`try/except` there at all — vs. the batch path's clean `rc == 1`), and
`test_terminal_split_parent_names_children_never_rm_rf` (pre-fix, the parent's
disposition line never reaches stdout for the same reason as COMPLETE/RESOLVED above).
Restored the fix: all 8 green. Full command log is reproducible via
`git stash push -- template/src/pdca_harness/cli.py template/src/pdca_harness/flow.py`
then rerun, then `git stash pop`.

**(b) Production path?** Yes. Every assertion drives `cli._flow` (the brief's named
surface) directly — never a hand-picked `flow.flow` / `flow.flow_ids` call standing in
for it (the one exception is `test_single_id_routes_through_flow_ids_not_flow` and
`test_preflight_error_same_rc_and_message_both_shapes`, which deliberately monkeypatch
`flow.flow_ids`/`flow.flow` to *observe which one `cli._flow` calls* — the assertion
is about the real routing decision, not a stand-in's behaviour). The split-parent
fixture calls the real `split.accept` (`split.py:525`), not a reimplementation.

**(c) Fixture includes the fault?** Yes. The terminal-split-parent fixture
(`_split_parent`) builds a genuine lineage record via production `split.accept` (a
brief, a real `split-proposal.md`, real child ids) — the exact shape the brief's
"Concrete defect" describes (a bundle with a `children` edge in
`split-lineage.json`), not a hand-rolled dict standing in for one. The RESOLVED
fixture writes a real `notes.json` with a `resolved` object, read by the same
`state.is_resolved` production code path a tracker-seeded bundle would hit.

## Runner used

`cd template && PYTHONPATH=src python3 -m unittest tests.test_flow_entrypoint_parity`
— the exact invocation the brief's Falsifiability names (mirrors what
`engine/scripts/run-verify.sh` would use for a `template/tests/*.py` test; that script
is itself an unimplemented per-project skeleton in this repo, per its own header
comment, `template/engine/scripts/run-verify.sh:1-91` — not a dependency this fix
needs). Also ran the full offline suite
(`PYTHONPATH=src python3 -m unittest discover -s tests`) both pre- and post-fix:
1622 pre-existing tests green pre-fix (before adding the new test file), 1630 green
post-fix (1622 + 8 new) — no regressions. Re-verified the same on an independent
fresh clone of the worktree checked out at `f7876f2` with `patch.diff` applied via
`git apply`, confirming the patch is self-contained and applies cleanly against the
target base.

## No external dependency gap

Nothing beyond `python3 ≥ 3.11` stdlib + git — matches the brief's `External
dependencies: none`. No tracker, network, `gh`, or container touched; every fixture
(`leaves.do_plan`, `_stub_signoff`, `split.accept`) is stub-mode/offline as configured
by `_stub_config` (mirrors `tests/test_flow_slice.py:31-56`).

## Formatting / commit hooks

No formatter/linter config exists in this repo (no `pyproject.toml`, `.flake8`,
`ruff.toml`, or `.pre-commit-config.yaml`; checked `template/`, repo root, and
`.git/hooks/` — only the standard `*.sample` hooks are present). `CONTRIBUTING.md`'s
only gate is DCO sign-off (`git commit -s`) and "keep the offline suite green" (both
satisfied — see above). Line lengths in the new/changed code stay within the range
already present in the surrounding files (the base `cli.py` already carries lines up
to 236 chars in its argparse help text, so there is no house line-length limit to
match).
