# Build notes — issue 359 / act-sizing-calibration

Target: eduralph/pdca-harness @ main (`dfd0427`), built in `$PDCA_WORKTREE`
(`../pdca-harness.pdca-wt-l1`). All citations below are on that base unless marked *new*.

## What was built, per criterion

### (a) Sizing column in the Act index

- `ActEntry` gains `size_estimate` / `size_outcome` (*new* `act.py:78-85`), defaulted to
  `""` so every existing constructor (e.g. `tests/test_act_ledger.py:33`) keeps working
  and a blank means "not measured".
- The join is one helper, `_size_column` (*new* `act.py:725-756`):
  - **estimate side** = `sizing.estimate(d / "brief.md", cfg)` — brief-derived, exactly as
    the proposal's Design section states. `sizing.estimate` already reads only the text
    above the first carry-forward heading (`sizing.py:302-317` on base), so the estimate
    stays a-priori even after an iterate appended to the brief.
  - **outcome side** = `size_signal.read(d)` (`size_signal.py:217-227` on base) — the
    *recorded* `size-signal.json` only, **never** `size_signal.current()`/`measure()`
    (`size_signal.py:200-214`). `current()` falls back to measuring whatever is on disk at
    review time, which would fabricate an "outcome" for every bundle predating #324's
    signal — the exact opposite of the criterion's "graceful blank". The second test pins
    this: the fixture bundle carries a 2 KB patch a fallback measurement would happily
    report, and the rendered line must show `—`, not `2 KB`.
- `index()` passes `cfg` into `_extract` (`act.py:530-540` base → *new* `act.py:544`);
  `_extract` keeps a `cfg=None` default so the direct test callers
  (`tests/test_signoff_authority.py:127,276,282`) are untouched.
- `render_index` (base `act.py:554`) emits one line per bundle beside the §6/§7/§10 lines
  (*new* `act.py:576-581`):
  `- sizing: estimate watch (score 6) → outcome 34 KB / 3 file(s) / 1 round(s)`
  with `—` for either blank side.

Why the estimate side does NOT fold in a stored sizer verdict: the stamped read is
`leaves.current_sizing` (`leaves.py:914-931`), and `leaves.py:48` imports `act` — folding
it in would close an import cycle for a decoration on an advisory column. Recorded in the
helper's docstring. (The raw `sizing.json` on disk is also explicitly *not* trustworthy
after an iterate-plan — that is `current_sizing`'s whole reason to exist — so reading the
file directly from `act.py` would be worse than omitting it.)

### (b) Documented retuning procedure

- The config comment block every rendered instance gets: a commented `[driver.sizing]`
  example block in `template/pdca.toml.jinja` (*new* lines 173-207), placed directly after
  `size_guard` and **before** the `[driver.size_signal]` block — see "Guard-test
  interaction" below for why the order is load-bearing. It walks the four steps from
  `scripts/size-calibrate` output (the rank-correlation table, `render()` at
  `scripts/size-calibrate:482-504`; the churn-split medians at `:497-504`) back into the
  table's keys, and documents `model_weight` with its Act-cadence review.
- `docs/07-crosscutting.md` (base :147-152 already said "retune under `[driver.sizing]`"):
  a new paragraph explains the loop — the Act index `sizing:` line is where drift shows,
  the procedure lives in the config block, `model_weight` is config reviewed at Act
  cadence (*new* :154-167).

### (c) `model_weight` as config

- `sizing.DEFAULT_MODEL_WEIGHT = 0` (*new* `sizing.py:97-107`) with the Act-cadence review
  note where it is defined, as the criterion asks.
- `combine()` grows a `cfg=None` third parameter (*new* `sizing.py:419`, applied at
  `:456-461`): a verdict naming a band above `ok` adds
  `max(0, _cfg_int(cfg, "model_weight", DEFAULT_MODEL_WEIGHT))` to the score — the same
  shape as a structural feature firing (`_cfg_int` is the existing tolerant
  `[driver.sizing]` reader, base `sizing.py:178-184`, so a typo degrades to the default,
  never aborts a beat). Clamped at 0 because a negative weight would let the model *lower*
  a structural score — the single-point-of-failure `combine`'s escalate-only contract
  exists to forbid (base `sizing.py:407-427` docstring).
- Default 0 ⇒ byte-identical behaviour: band escalation only, score untouched — asserted
  directly (`test_default_is_current_behaviour_band_only`, incl. `cfg=None`).
- All four callsites now pass `cfg` so the key is live end-to-end: `leaves.py:1071`,
  `plan_policy.py:119-120`, `cli.py:780`, `cli.py:818-820` (same line numbers on base).
- `config.py:319-322` (the `[driver.sizing]` dict passthrough the brief cites) now names
  `model_weight` + the Act-cadence review in its comment (*new* :322-326) — this also
  satisfies the proposal's falsifiability grep on `config.py`.

### (d) Mining archived `iteration-v*/brief.md` — explicit decision: NOT in this change

**For the PR prose (sign-off checks this):** this change does **not** mine archived
`iteration-v*/brief.md` files, and therefore reports no correlation delta. Rationale:

1. The corpus that would answer "does mining change the correlations" lives in rendered
   *instances* (`results/` bundle trees), not in this repo — the same reason
   `size-calibrate`'s own docstring gives for #336's deferral
   (`scripts/size-calibrate:127-148`): there is no bundle corpus here to re-run against,
   so a number produced in this PR would be un-reproducible from the tree it lands in.
2. The miner already *names* the gap out loud on every run so the deferral cannot hide:
   `scripts/size-calibrate:469-480` prints "Mining the archived iteration-v*/brief.md as
   its own data point would recover them; this run does not."
3. The proposal itself scopes the change to "builds the loop that keeps them honest", not
   to producing new numbers ("Scope": retuning itself explicitly out).

So the honest report is: **decided not to, this cycle**; the loop this change ships (Act
index column + documented recalibration walk) is precisely the mechanism that will show
whether the archived-brief blind spot matters, per instance, on real data.

## Guard-test interaction (found by running the full suite, not by luck)

`tests/test_size_signal.py:431-468` (`TheShippedExampleMatchesTheDefaults`) scans **every**
commented `key = int` line from the literal `[driver.size_signal]` to EOF and requires the
set to equal `size_signal.DEFAULT_THRESHOLDS`. My first placement (after that block) fed it
nine `[driver.sizing]` keys → 10 failures. Moving the sizing block *before* the
`size_signal` section keeps it out of that scan (first occurrence of the literal
`[driver.size_signal]` is that block's own header) and reads in pipeline order anyway
(a-priori estimate, then Check-time backstop). The new test carries the mirrored
two-direction guard for the sizing block, scoped at the `[driver.size_signal]` boundary so
the two guards can never read each other's keys (`RetuningDocs._sizing_block`).

## Alternatives considered, with cost

- **Recompute the outcome when no signal is recorded** (`size_signal.current()` instead of
  `read()`): 1 line cheaper, but it fabricates a record — the outcome column would show a
  review-time measurement as though #324 had recorded it, and for pre-#324 bundles the
  patch on disk can postdate publish-time reality. The invariant is "blank = not
  measured"; rejected on correctness, not cost.
- **Fold `leaves.current_sizing` into the estimate side**: needs either `import leaves` in
  `act.py` (import cycle — `leaves.py:48` imports `act`; breaking it means extracting
  `current_sizing` + `_sizer_key` + `_read_sizing` (~60 lines, `leaves.py:874-947`) into a
  new module and re-pointing 3 importers) or a raw `sizing.json` read that `current_sizing`
  exists to forbid (stale after iterate-plan). Cost ≈ a 60-line module extraction for a
  column decoration; the structural estimate is what the brief's Design names. Deferred.
- **A `[[gates]]`-style separate `model_weight` table / new config attribute**: the
  `[driver.sizing]` dict passthrough (`config.py:319-322`) already reaches `combine` via
  `cfg.sizing` with zero new plumbing; a dedicated attribute would add a Config field +
  loader line + doc row (~10 lines) to express one integer the existing table already
  carries. Rejected as pure duplication.
- **Extending `render_index` with a Markdown table instead of a per-bundle line**: the
  index renders per-bundle `##` sections with `- §N:` lines (`act.py:564-577`); a table
  would be a second layout for the same data and every existing consumer asserts on the
  line form. Rejected — the line matches the file's own idiom.

## Forced self-refutation (the three questions)

- **(a) Genuine red?** Yes — ran twice, both via the project's documented offline-suite
  runner (`cd template && PYTHONPATH=src python3 -m unittest …`, docs/INTEGRATION.md §3).
  With all eight production files stash-reverted and only the test present:
  `FAILED (failures=1, errors=8)` — every test red (AttributeError on `size_estimate`,
  TypeError on `combine(cfg)`, missing `[driver.sizing]` block). Restored:
  `Ran 9 tests … OK`. This matches run-verify.sh's revert classification: all eight
  reverted files are PROD to it except `docs/07-crosscutting.md` (docs are non-behavioral
  there — and no test binds on the docs file, so the red leg does not depend on it).
- **(b) Production path?** Yes — the tests drive `act.index` → `act._extract` →
  `act._size_column` → `sizing.estimate`/`size_signal.read`, `act.render_index`, and
  `sizing.combine` from the installed `pdca_harness` package under `template/src`; no
  copies, no mocks. The config-block tests read the shipped `pdca.toml.jinja`
  (or its rendered `pdca.toml` — same fallback the existing guard uses, because the render
  suite re-runs this test inside a rendered instance; first root-suite run caught exactly
  that and it is fixed, both suites green).
- **(c) Fixture includes the fault?** Yes — the joined bundle is a real COMPLETE bundle
  (SUMMARY.md.tpl + accepted §9 via `signoff.record`, the same `_freeze` shape as
  `test_act_frontier.py:44-59`) with a genuine `size-signal.json`; the predating-signal
  bundle deliberately **contains** the 2 KB patch that a wrong implementation
  (`current()` fallback) would measure and report — the failing element is in the
  fixture, not curated out.

## Verification runs (project runners)

- Offline driver suite (docs/INTEGRATION.md §3): `Ran 1323 tests … OK (skipped=2)`
  (both skips pre-existing, unrelated).
- Root render/update-compat suites (instance venv, copier importable):
  `Ran 7 tests … OK` — the render test re-runs the offline suite inside a rendered
  instance, so the new test ran there too.
- Red→green evidenced above; C4 (`engine/scripts/run-verify.sh`) will re-prove it at
  Check from `patch.diff`.

## Commit-readiness

The target has no formatter/linter config (no ruff/pre-commit/setup.cfg; checked at repo
root) — convention is manual: ≤ ~95-char lines, module-style comments, alphabetical
relative imports (`size_signal` before `sizing` — verified sort order). DCO sign-off and
the `Fixes #359` trailer are publish-step concerns (`docs/INTEGRATION.md` §8). Docs edits
keep the T2 conventions (plain ATX sections, no new links). No external dependencies
beyond the brief's "none" were needed.
