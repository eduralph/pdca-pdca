# sizing: stop scoring the split's own scheduling metadata as churn

- **Slug:** sizing-ignores-sibling-conflicts
- **Defect / goal:** three of the five weighted features in `sizing.estimate` are fields the
  split process itself installs into every child — `conflicts_with` (+3, the strongest churn
  weight), `difficulty_high` (+3, inherited from a `high` parent) and `ext_deps` (+3, the
  parent's tokens copied into each child that needs them) (`sizing.py:89-95`). 3+3+3 = 9 ≥
  the `oversized` cutoff of 7 (`sizing.py:126-127`) regardless of the child's actual scope,
  and the one de-escalating term, `is_plan_pointer` (−2), a split child never has. Sibling
  `Conflicts with` entries are *correct scheduling metadata*: the splitter is explicitly
  told the ordering fields "BETWEEN children are the point" (`leaves.py:1261`), and
  `split.rewrite_ordering` turns sibling labels into real ids (`split.py:320-345`). Yet
  `estimate` counts them identically to organic conflicts (`sizing.py:241`, `:268`), and the
  ρ 0.32 calibration behind that weight was measured over *organic* bundles. Stop scoring
  the artifact the process itself created.
- **Success criterion:**
  (a) for a bundle carrying child lineage, `Conflicts with` entries naming its own
      `siblings` are excluded from the conflict count — a materialised child whose churn
      features are N sibling conflicts plus an inherited `Difficulty: high` plus inherited
      external-dependency tokens scores **below** the `oversized` cutoff of 7, where it
      scores ≥ 7 today;
  (b) **organic** conflicts — any id not in `siblings` — still score at full weight, and a
      bundle with no lineage scores byte-identically to today (assert against an existing
      fixture, not only a synthetic one);
  (c) the sibling-conflict **count is exposed** on the estimate (e.g. a field on
      `SizeEstimate`). This is not decoration: child-3 must key its wording on whether
      sibling conflicts actually carry the score rather than on mere presence of lineage,
      and child-4's convergence report must still be able to *see* a proposal whose children
      all conflict pairwise — which is the splitter's own statement that the split separated
      nothing, and would otherwise be scored as a clean split by the very report that exists
      to detect non-convergence;
  (d) **`sizing.estimate` and `template/scripts/size-calibrate` agree on what
      `conflicts_with` means.** The calibrator mines `len(set(brief.conflicts_with(ap)))`
      raw (`size-calibrate:300`), so after (a) a *shared* feature name denotes two different
      quantities, and any Act-cadence retune of the weight (#324/#359 — the loop this
      change explicitly leaves the weights to) would fit it on a value the engine no longer
      uses for split children. Resolve it here rather than deferring: either mine the same
      excluded count, or mine both under distinct names. A test asserts the agreement.
- **Constraints (verified against `main`, carry forward):**
  * Read the record via `brief_path.parent / …`. Inside `estimate`, `brief_path` is a real
    `Path` (`sizing.py:217`; the `AprioriBrief` is constructed below it). **Do not** widen
    the `AprioriBrief` allowlist to get there — `_DELEGATED` (`sizing.py:363`) and its
    `__getattr__` (`:400-412`) refuse every attribute outside a short allowlist *by design*,
    and that guard must stay closed.
  * `estimate` must keep its promise never to raise on a malformed or absent brief
    (`sizing.py:220-224`): a lineage read failure abstains, it does not crash the Plan beat.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Falsifiability:** RED on `cd template && PYTHONPATH=src python3 -m unittest
  tests.test_sizing_split_child`. Pre-fix a materialised child with two sibling conflicts,
  `Difficulty: high` and one external-dependency token scores 3+3+3 = 9 ≥ the `oversized`
  cutoff of 7 (`sizing.py:89-95`, `:126-127`, `:277-278`), so the "scores below the cutoff"
  assertion fails outright; criteria (c) and (d) fail on `AttributeError` for the not-yet-
  exposed count. **This is a wave-1 bundle**: its Do worktree and its gate run on the run's
  folded integration branch (`PDCA_VERIFY_BASE`, `gates.py:379-397`), which already carries
  child-1's accepted `split.py` — so the lineage reader this child calls exists on the base,
  and reverting only THIS child's production hunks still leaves a genuine red. No network,
  tracker, `gh` or container.
- **Reproduction:** materialise a split child carrying two sibling `Conflicts with` entries,
  `Difficulty: high` and one external-dependency token, then run `sizing.estimate` over its
  brief: it scores 9 and bands `oversized` on `sizing.py:277-278`, with
  `2 conflict(s) declared` among its reasons — although its actual scope is one function.
- **Scope (one logical fix) / out of scope:** `template/src/pdca_harness/sizing.py`,
  `template/scripts/size-calibrate`, the `[driver.sizing]` documentation rows in
  `docs/07-crosscutting.md` — restricted to `### The estimate` (`:100-173`; the weights table
  and its retune procedure at `:110` and `:149-162`) — and the new test module. Leave
  `### The process` (`:36-99`) to child-3 and `### The split` (`:174-218`) to child-4.
  **Out of scope:**
  changing any existing weight or cutoff (that is the #324/#359 Act-cadence loop); adding a
  new `split_child` weight — the previous attempt registered one defaulting to 0, a
  documented no-op that added `pdca.toml.jinja` surface and a docs claim without changing
  behaviour, and the sibling exclusion is the deterministic mechanism that actually works;
  the remedy wording and the leaf prompts (child-3); the convergence report (child-4);
  `plan_policy.py`, `split.py`, `cli.py`, `leaves.py`.
- **External dependencies:** `copier importable (.venv)` — the patch changes files under
  `template/`, so the target's render and `copier update` compatibility root suites exercise
  it; without copier those seven tests skip themselves and T3 reports a green that tested
  nothing. Otherwise python3 ≥ 3.11 stdlib + git only; the test runs in the offline driver
  suite with no tracker, network or container.
- **Test file:** `template/tests/test_sizing_split_child.py` — a new module in the offline
  driver suite. The C4 gate reverts only the PRODUCTION hunks and keeps the test
  (`run-verify.sh:121-130`), so a new file earns its red. **Import the module, never the new
  symbols** — `from pdca_harness import sizing, split`, then attribute access inside test
  bodies; a module-level `from pdca_harness.sizing import <helper>` raises ImportError on
  the red leg, giving 0 tests run and exit 77 `PDCA-UNVERIFIABLE` (`run-verify.sh:145`)
  instead of a red that proves anything.
- **Difficulty:** medium
- **Depends on:** 456

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: Rejected on the reviewer's C3 finding only; the approach (sibling-conflict exclusion, shared helper, exposed count) is accepted in principle — keep it. 1) C3: `sibling_conflict_count` does `set(siblings)` on raw lineage JSON — a malformed record like `"siblings": [[]]` (unhashable member) passes the isinstance-list guard and raises TypeError at `template/src/pdca_harness/sizing.py:251`. The brief's constraint is abstain-not-crash: harden the helper (e.g. keep only `str` ids before building the set) and add the malformed-lineage case to `template/tests/test_sizing_split_child.py`. 2) The T3 gate red (11 failures in `template/tests/test_verify_base.py`, `PDCA_VERIFY_BASE` leaking into its subprocesses) is a pre-existing harness test-isolation fault affecting every stacked bundle — it is NOT this patch's defect and is out of scope. Do not chase it; expect the same non-gating red on the rebuild.
- Failing gate: T3 runtime: render/update-compat + offline driver suites (advisory) — == T3: root suite OK, driver suite FAILED (rc 1)
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).

## Iteration 2 — carry-forward (from the previous attempt)
- Sign-off rationale: Auto-iterate (round 1): Check found implementation-level items only, no architectural judgment required — T3 Runtime — Decide whether to accept template compatibility only after running the seven root render/update tests with Copier installed — Copier is absent here so all seven skipped; the offline driver suite passed, and the reported 11 failures reproduce only when `PDCA_VERIFY_BASE` leaks into subprocesses expecting it unset at `template/tests/test_verify_base.py:126`.; T4 Contribution — Decide whether the PR opener and tracker references satisfy contribution policy after rerunning the bundle's validator — `./scripts/pdca` and the PR/commit artifacts were not supplied, so the asserted green could not be independently reproduced.
- Failing gate: T3 runtime: render/update-compat + offline driver suites (advisory) — == T3: root suite OK, driver suite FAILED (rc 1)
- Full previous attempt preserved in `iteration-v2/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
