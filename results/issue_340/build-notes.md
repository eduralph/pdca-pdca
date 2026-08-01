# Build notes — issue 340 / dependency-probe-at-plan-exit

Target: eduralph/pdca-harness @ main (`dfd0427`), built in `$PDCA_WORKTREE`
(`pdca-harness.pdca-wt-l0`). All `path:line` cites below are against that base.

## What the change is

The Plan-exit dependency guard now **executes** the detect `cmd` of exactly the
registered `[[doctor.checks]]` rows the brief's `External dependencies` tokens name, and
holds the bundle on a non-zero exit — quoting the row's `hint` — before Do dispatches.

Two production seams, mirroring the #333 split exactly:

1. **`doctor.failing_dependencies(brief_path, cfg)`** (new, inserted after
   `unregistered_dependencies`, `doctor.py:353`). Tokens come from
   `brief.external_dependency_tokens` (`brief.py:250`) — so `(no-check: …)` /
   `(topology …)` annotations and plain prose yield no token and are never probed
   (criterion d, no new parsing). Rows come from `Config.current_doctor_checks()`
   (`config.py:391`) — disk, not the run snapshot — so a row registered during the Plan
   beat is probed in the same pass (criterion f). Matching mirrors
   `doctor.registered_ids` (`doctor.py:306`): raw row `id` (default: its `cmd`),
   case-insensitive, so "registered" and "probed" cannot disagree about which row a
   token names. Each matching cmd runs with the exact subprocess shape doctor itself
   uses for a row (`doctor.py:492`): `subprocess.run(cmd, shell=True,
   capture_output=True, cwd=cfg.root).returncode`. A row the brief does **not** name is
   never spawned (criterion c) — the `rid.lower() not in wanted` filter.

2. **`plan_policy.dependency_reasons`** (`plan_policy.py:156-189` pre-change) appends
   `HoldReason("failed-dependency", …)` (or `failed-dependency-warn` under `warn`)
   **after** the #333 registration reasons, and `_BLOCKING` (`plan_policy.py:62`) gains
   `failed-dependency`. The hold rides the existing `PolicyHold` mechanism
   (`plan_policy.py:65`) via `driver.advance` (`driver.py:55-67`) unchanged — nothing
   new in the driver. Mode handling (`plan_policy.py:174-180`) is untouched: `off`
   returns before any probe (byte-identical, criterion h), `warn` maps to a code
   `blocking()` ignores so `advance` prints it and proceeds, and the existing
   typo-fails-safe branch covers the probe for free.

Docs/config, per the brief's Impact section ("the cheapness expectation moves into the
config comment"): the `[[doctor.checks]]` comment in `template/pdca.toml.jinja:713` now
states that named rows run every beat the policy is consulted and must stay cheap and
side-effect-free (and that a probe is a read — `[install].extra_bootstrap` keeps
provisioning); matching comment updates at `config.py:332-339` and `config.py:346-349`;
the dependency-guard bullet in `docs/03-plan.md:235-252` no longer describes
registration as the whole guard.

## Why this shape

- **Probe lives in `doctor`, not `plan_policy`.** Same anti-drift rationale
  `unregistered_dependencies` documents on itself (`doctor.py:341-343`): the Plan-exit
  caller and any later consumer (#341 reuses the probe at Do exit per the brief's
  ordering note) share one implementation. Inlining it in `plan_policy` would duplicate
  the row-read + id-normalisation already in `registered_ids` (`doctor.py:318-322`) —
  ~15 duplicated lines and exactly the two-enumerations drift the existing test
  `test_both_callers_share_one_implementation` exists to prevent.
- **Registration check first, probe second (criterion g).** Reasons are concatenated
  with the unregistered ones leading; the probe by construction never executes an
  unregistered token (there is no row to run). I deliberately did **not** early-return
  on an unregistered token: with two tokens (one unregistered, one registered-failing)
  both reasons surface in one pass, so the human fixes both before the retry instead of
  discovering the second hold after registering the first row. Cost of the alternative
  (early return): one extra held-retry cycle per mixed case; cost of mine: probing a
  registered row while already held — cheap by the documented contract.
- **No subprocess timeout.** The brief's cited pattern is "the cheap-subprocess pattern
  doctor itself uses to run a row's cmd", and doctor's own row runner (`doctor.py:492`)
  sets none. Diverging (say a 10 s timeout here) could make the guard and `pdca doctor`
  disagree about the same row. The cheapness expectation is documented where the brief
  says it belongs (config comment).
- **Rejected: full `pdca doctor` sweep at Plan exit** (also rejected in the brief). It
  would execute every registered row for every bundle — e.g. the pdca-pdca instance
  registers 3 rows including two venv-import probes (`pdca.toml:711-727` in this
  instance) — and hold bundles on tooling they never named. The scoping filter is 2
  lines (`doctor.py`, the `wanted` set + membership test).

## Test changes (`template/tests/test_dependency_guard.py`, the brief's named file)

- New `DependencyProbe` class (appended, per the brief's Falsifiability): nine tests
  mapping to the criteria — (a) failing detect ⇒ blocking hold quoting the hint, Do not
  dispatched, state stays PLANNED; asserts `cfg.lanes == 1` (criterion e — the path with
  zero preflight; the probe never consults lanes); (b) passing detect ⇒ `evaluate == []`
  and Do dispatches; (c) an unnamed registered row is **not executed** — its cmd both
  fails *and* touches a marker, so execution is observable either way (no hold AND no
  marker); (d) exempt/prose deps not probed (same marker technique); (f) disk rows beat
  a stale snapshot whose row would pass; (g) reason order
  `[unregistered-dependency, failed-dependency]`; (h) `off` spawns nothing
  (marker-proven) and `warn` reports `failed-dependency-warn` without holding; plus the
  self-clearing hold (fix the row ⇒ next beat proceeds, no replan).
- Existing stub rows switched from `cmd = "protoc --version"` to `cmd = "true"`
  (`test_dependency_guard.py:29,66,249` pre-change). Required, not cosmetic: the probe
  now executes registered rows, and this host has no `protoc`, so
  `test_registering_the_row_clears_it`, `test_the_hold_clears_without_replanning` and
  `test_pdca_run_still_exits_zero_when_it_finishes` would false-red. The brief
  anticipates exactly this: "stub rows with `true`/`false` as detect cmds". Those tests
  are about registration semantics; `true` keeps them that and probe-passing.

## Red→green evidence (project's own runner)

Runner: the offline driver suite command INTEGRATION.md §3 / CONTRIBUTING.md name —
`cd template && PYTHONPATH=src python3 -m unittest …` (same invocation
`engine/scripts/run-verify.sh:60` uses for C4).

- **Green leg** (fix applied): `tests.test_dependency_guard` — 27 tests, OK.
- **Red leg** (production hunks reverted via `git stash push` of the 5 non-test files,
  tests kept — mirroring run-verify.sh's exclude-tests revert): **FAILED (failures=5)**
  — the probe tests; restored afterwards.
- Full offline driver suite: **1323 tests, OK** (2 pre-existing skips).
- Root template-repo suite (render + update-compat, exercises `pdca.toml.jinja` with
  the instance venv's copier, as `run-suite.sh:20` does): 7 tests, OK.
- Docs lint (`docs/publishing/tools/lint_docs.py`, the docs-check CI job): OK.

## Forced self-refutation (recorded per the Do contract)

- **(a) Genuine red?** **Yes.** Reverted the five production files (stash), re-ran the
  module: 5 failures (`failed-dependency` expectations came back empty /
  `failed-dependency-warn` absent). Restored; 27/27 green.
- **(b) Production path?** **Yes.** The tests drive `plan_policy.evaluate` and
  `driver.advance` — the exact entry points the driver uses before Do (`driver.py:55`)
  — which call the new `doctor.failing_dependencies` in production. No mock, no copy;
  the only stub is the builder leaf, which is the driver's own configured offline mode.
- **(c) Fixture includes the fault?** **Yes.** The failing dependency is real: a
  `[[doctor.checks]]` row written to a real on-disk `pdca.toml` whose cmd (`false`)
  is genuinely executed and genuinely exits non-zero; the negative-space claims
  (row not named / exempt / `off`) are proven by marker files the cmd would have
  created had it run — absence of the marker is positive evidence of non-execution,
  not a curated fixture.

## Commit-readiness

Target repo has no pre-commit/formatter config (checked repo root and
`.github/workflows/`: docs-check, docs, render-check, require-linked-issue). The two CI
checks my changed files trigger — the docs lint and the render suite — both pass above.
New code keeps the file-local style (≤95-char lines in my hunks).

## Scope notes for sign-off

- The probe also fires at BUILT (before Check): `driver.advance` already consults
  `plan_policy.evaluate` for both PLANNED and BUILT (`driver.py:50-55`), and the #333
  registration check already behaves that way. That is the existing mechanism's shape,
  not added scope; #341's Do-exit reuse remains its own bundle.
- No external dependencies were needed (matches the brief's `External dependencies:
  none`); everything ran offline through the driver suite. No NEEDS-HUMAN items.
