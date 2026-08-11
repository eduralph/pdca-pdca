# Build notes — issue 459 (split convergence report)

## What shipped

`template/src/pdca_harness/split.py`:
- `preflight()` (`:238`) now also calls `_emit_convergence_report()` (`:266`) as its
  last step, after the existing proposal/CLOSE_MARKER/ordering checks — i.e. it fires
  only once the proposal is known valid, and strictly before the caller can do anything
  irreversible.
- `_staged_estimate()` (`:269`) stages one child's own body plus a synthetic
  `split-lineage.json` (siblings = the *other* children's proposal-local **labels**, not
  real ids — none exist yet) into a `tempfile.TemporaryDirectory()` named after the
  child's own label, then reads it back through `sizing.estimate()` — the exact code
  path a materialised child gets. `_LABEL_RE` (already pinned to `child-\d+`) makes the
  label safe as a directory name; the whole directory is gone on every exit via the
  context manager, so nothing is left behind on failure (brief Constraints).
- `_sibling_conflicts()` (`:294`) reads `SizeEstimate.sibling_conflicts` when present
  (issue #457's field), else falls back to the raw `Conflicts with` count. See "the
  457 dependency" below for why the fallback is *exact*, not approximate.
- `convergence_report()` (`:313`) is the pure builder: per-child band vs the parent's,
  the driving `.reasons`, and two independent NOT-CONVERGED signals — "most children
  don't band lower" and "every child conflicts with every sibling" (the leaves.py:1265
  "the point" fields, read from the proposal's own ordering data, so it can never be
  fooled by an estimator that later stops counting those conflicts as churn).
- `_emit_convergence_report()` (`:360`) prints it, guarded by a single
  `try/except OSError: pass` around BOTH the staging/estimate computation and the
  print — mirrors `cli.py`'s existing filed-ids guard (now `cli.py:796-799`) exactly.

`template/src/pdca_harness/cli.py` (`_split`, `:721`): the proposal is now parsed and
`split.preflight()` called **unconditionally**, before the `if not ids:` branch — so
both `--accept` (auto-filing) and `--accept --ids a,b` reach it before their respective
irreversible step (filing issues; materialising bundles). Previously `--ids` skipped
straight to `split.accept()` and never saw `preflight` at all (brief's cited
reproduction).

`docs/07-crosscutting.md` — one new paragraph inside `### The split`
(current `:209-223`, i.e. within the brief's cited `:174-218` range before my insertion
shifted line numbers), describing the report, its trigger point, and its advisory
guarantee. Left `### The process` / `### The estimate` untouched, as scoped.

`template/tests/test_split_convergence.py` — new module, 12 tests, one class. Imports
only `from pdca_harness import cli, split, sizing` (module import, never new symbols —
per the brief's red-leg discipline).

## The brief's line citations vs. this checkout

The brief cites `cli.py:733`/`cli.py:764` for the preflight/accept call sites and
`leaves.py:1274` for "the point" — in this checkout those are at `cli.py:769`/`cli.py:800`
and `leaves.py:1265` respectively (a consistent small offset, most likely the brief was
authored against a slightly different snapshot of the same lines). I verified the
*content* at the real locations matches what the brief describes and cited the real line
numbers above and in code comments, rather than the brief's.

## The `Depends on: 457` question (the bulk of the investigation time here)

The brief explicitly relies on `SizeEstimate.sibling_conflicts` (issue #457,
`sizing.py`), out of scope for this bundle to add. I resolved the target for this
bundle the way the driver itself does — `publish._resolve_target` /
`publish.read_stack_base` — and confirmed the **actual** verify base
(`PDCA_VERIFY_BASE` per `gates.py:379-397`) is `origin/pdca-integration/main`, currently
at `92a1fd5` ("pdca-integrate: issue_413"). I checked that commit's `sizing.py`
directly: it does **not** carry #457's `sibling_conflicts` field or
`sibling_conflict_count` function, even though issue 457 is `COMPLETE` and signed off
(`results/issue_457/SUMMARY.md` §9) — its patch was published as a stacked PR
(`results/issue_457/publish.json`) but has not been folded into
`pdca-integration/main`, and "Depends on" (unlike "Depends on (merged)") only requires
the prerequisite to reach `COMPLETE`, not to be folded into the base a sibling builds
on (`flow.py` wave docstring). So the dependency is real at the *PR-merge-order* level,
not at the *this-checkout's-sizing.py* level.

Given that, I did NOT hard-depend on the unlanded field. Two things make this both safe
and still correct to the brief's intent:
1. `_sibling_conflicts()` reads it via `getattr(..., None)` and falls back to the raw
   `Conflicts with` count. That fallback is *exact*, not a degraded approximation: at
   `preflight` time every ordering ref is a sibling **label** by construction
   (`_validate_ordering` refuses anything else) — so 100% of a staged child's declared
   conflicts already ARE its siblings, whether or not `sizing.py` currently excludes
   them from the score. Once #457 lands, `getattr` picks up the real field
   transparently, with no further change needed here.
2. The "every child conflicts with every sibling" NOT-CONVERGED signal is computed from
   the proposal's own `Conflicts with` labels (via `_sibling_conflicts`), independent of
   whatever `sizing.py`'s own score/`.reasons` currently do with them — so it can never
   be blinded by an exclusion whether or not that exclusion exists yet in this tree.

I verified point 1 with two direct unit tests against `split._sibling_conflicts`
(`test_sibling_conflict_reading_prefers_the_exposed_estimate_field` /
`..._falls_back_to_the_raw_count`), constructing a stand-in object with/without a
`sibling_conflicts` attribute — this exercises MY function (production code this patch
ships), not a mock of `sizing.py`.

### Alternative considered and rejected: cherry-pick #457's real patch into the base

I could have applied `results/issue_457/patch.diff` (the real, human-reviewed, signed-off
artifact) onto my build tree before testing, to exercise the exact `sizing.estimate()`
code path #457 adds. I did **not** ship that as part of my patch (it isn't mine, and
"Out of scope: sizing.py" is explicit), and decided not to even use it for local testing
because doing so would validate my code against a tree the REAL C4 gate — which resets
`$PDCA_WORKTREE` to `origin/pdca-integration/main` and applies ONLY `results/issue_459/
patch.diff` (`worktree.rebuild_for_gate`) — will not actually present. Testing against a
richer, hand-assembled tree would have been the "curated fixture that excludes the
failing element" the refutation questions warn about, just inverted (curated to *include*
something the real gate won't). Testing against the bare, real base (what I did) is the
fixture that actually matches production.

## Refutation (forced, per instructions)

**(a) Genuine red?** Yes — proven mechanically, not just asserted. I ran the project's
own gate, `engine/scripts/run-verify.sh`, from `pdca-pdca` against
`PDCA_WORKTREE=/home/eddie/pdca/pdca-harness.pdca-wt`, `PDCA_BUNDLE=results/issue_459`.
It resets the worktree to `origin/pdca-integration/main`, applies `patch.diff`, runs the
green leg (12/12 pass), reverts only the production hunks (`split.py`, `cli.py`, the docs
paragraph is non-behavioral and excluded), and reruns: 9 errors + 2 failures out of 12 on
the red leg (`AttributeError: module 'pdca_harness.split' has no attribute
'convergence_report'` etc.). Output: `C4 PASS: red without the fix, green with it`.

**(b) Production path?** Yes. The test drives `cli._split` and `split.preflight` /
`split.accept` / `split.convergence_report` directly — the real functions this patch
changes, not copies. The one place I hand the function a stand-in object
(`SimpleNamespace` for `_sibling_conflicts`'s `est` parameter) is a unit test of MY OWN
new function's duck-typed contract, not a mock of `sizing.py` or of anything the fix
depends on to behave correctly end-to-end (`convergence_report` itself always calls the
real `sizing.estimate()`).

**(c) Fixture includes the fault?** Yes. The reproduction the brief names
(`pdca split <id> --accept --ids a,b` printing nothing but the `pdca flow` follow-up) is
reproduced verbatim by `test_the_ids_path_now_reaches_preflight_and_prints_a_report` —
pre-fix, `cli._split` really does skip straight to `split.accept()` for the `--ids`
shape (this was the actual, unmodified control flow, not a fixture built to exclude it).
The stream-failure test (`test_a_broken_stream_...`) drives a real object whose `write()`
raises on the 2nd call, passed as the actual `file=` `_emit_convergence_report` writes
to — not a bypassed/disabled write path.

## Formatter / commit hooks

No `.pre-commit-config.yaml`, no `[tool.black]`/`[tool.ruff]` in `pyproject.toml`
(pdca-harness is a copier template repo with no root `pyproject.toml`), no `.flake8` /
`ruff.toml`. `CONTRIBUTING.md`'s only mechanical requirement is `git commit -s` (DCO) and
"keep the offline suite green" — verified above (1697/1697, exit 0). Matched the
surrounding file's existing style (line width, docstring voice, `#: ` attribute comments)
by hand since there is no automated formatter to run.

## Gates run (all through the project's own scripts, not hand-rolled)

- `engine/scripts/run-verify.sh` (C4, gating) → PASS, red→green as above.
- `engine/scripts/run-docs-check.sh` (T2) → OK (lint + full site render + link audit).
- `engine/scripts/run-suite.sh` (T3, advisory) → `root suite OK, driver suite OK`
  (copier 9.17.0 is importable in `.venv`, so the copier-gated root suites ran for real
  rather than skipping themselves).
- `cd template && PYTHONPATH=src python3 -m unittest discover -s tests` → 1697/1697,
  exit 0 (the full offline driver suite, unaffected).

## What I deliberately did not do

- Did not touch `sizing.py`, `plan_policy.py`, `leaves.py` (out of scope).
- Did not make the report block, prompt, or change what `--accept` files/materialises —
  `_emit_convergence_report` only ever prints; every existing `test_split.py` behavioral
  assertion (96 tests) still passes unchanged against this patch.
- Did not add a `max_split_depth` cap (explicitly out of scope, held in reserve).
- Did not widen the docs edit past `### The split`'s opening section — left the
  lineage/adoption prose immediately below untouched.
