# Build notes — issue 359 / act-sizing-calibration — **iteration 2**

Target: eduralph/pdca-harness @ main (`dfd0427`), built in `$PDCA_WORKTREE`
(`../pdca-harness.pdca-wt-l0`). All `path:line` cites are against that tree with the
patch applied, except where marked "pre-fix".

## What this iteration is

The carry-forward says iteration 1 met deliverables (a)–(d) and was rejected on exactly
two findings (T3 and C5). So this attempt **keeps the v1 patch as its base** (the brief
itself preserves it in `iteration-v1/patch.diff`, and the carry-forward says "otherwise
met and verified") and changes precisely what the two findings name — it does **not**
re-submit the rejected approach unchanged, and it does not rebuild accepted work from
scratch either. The v1 rationale for the accepted parts (column join semantics, the
recorded-signal-only outcome, `model_weight` config plumbing through `sizing.combine`
and its four callsites, the both-ways example-block guard) stands as reviewed; see
`iteration-v1/build-notes.md` for it in full.

## Finding 1 — T3: OverflowError aborts the whole index

**Defect (pre-fix, v1 state):** `_num()` guards the `int()` conversion
(`TypeError/ValueError/OverflowError`), but a recorded `patch_bytes` that parses as a
*Python int* yet exceeds float range (e.g. `10**400` — JSON carries arbitrary-precision
ints) sails through the guard and then `int / 1024` raises `OverflowError: integer
division result too large for a float` inside the f-string at **act.py:755 (v1 state)**
— confirmed verbatim in the red run below. One garbled `size-signal.json` aborted
`pdca act index` for every bundle.

**Fix:** the whole outcome-formatting expression is wrapped in `try/except
OverflowError`, returning the estimate with a **blank** outcome
(`template/src/pdca_harness/act.py:755-766`). Blank is the criterion's own word
("graceful blank") and the column's stated contract — "a blank side means 'not
measured', never 'small'" (`act.py:576-581`, the render comment).

**Alternatives, with cost:**

- **Clamp instead of blank** (the finding allowed either). Cheaper in lines — a 2-line
  range check inside `_num` (`if abs(v) > 2**63: return 0`) vs my 4-line try/except —
  but it renders `0 KB / 3 file(s) / 1 round(s)`: a fabricated *small measurement*,
  which is the one direction the criterion forbids ("a graceful blank … never 'measured
  small'"). The brief names an invariant-shaped contract here, so smallest-diff is not
  the deciding axis; blank restores the contract, clamp-to-0 violates it. Clamping to a
  *max* instead prints a 300-digit or saturated number that reads as a measurement
  nobody made — same violation, other end.
- **Fix "the cause" in the writer** (make `size_signal.measure` unable to record such a
  value): does not protect the reader — `size-signal.json` is a file on disk that hand
  edits, corruption, or other tools can garble regardless of what our writer refuses to
  emit, and already-frozen corpora keep whatever is in them. Reader-side tolerance is
  the codebase's established pattern for exactly this file:
  `size_signal._int` (`template/src/pdca_harness/size_signal.py:230-237`) documents the
  sibling failure (`1e309` → `inf` aborted summary assembly). This is not a
  symptom-guard hiding a removable cause; hostile input at the reader *is* the cause.

**Test:** `test_overflowing_recorded_value_blanks_outcome_never_aborts_index`
(`template/tests/test_act_index_sizing.py:131-153`). The fixture writes a real
`size-signal.json` with `patch_bytes = 10**400` **plus a healthy sibling bundle** —
asserting the garbled record blanks only its own cell while the sibling's
`34 KB / 3 file(s) / 1 round(s)` still renders. The sibling is the point: it binds
"never aborts the whole index", not merely "this entry is blank".

## Finding 2 — C5: model_weight retuning is blind

**Defect:** the index's `sizing:` line joins the *structural* estimate only (the stored
sizer verdict is deliberately omitted — the import-cycle rationale the reviewer
accepted, `act.py:728-732`), and `size-calibrate` mines no model-verdict feature
(`template/scripts/size-calibrate:240-242`, `FEATURES` has no such column). So
escalation-to-outcome correlation is unobservable, yet v1's retuning walk told the
reviewer to "raise it only once the Act index shows sizer escalations tracking real
churn" — pointing at evidence no shipped artifact can produce.

**Fix (the finding's named minimum):** the blind spot is stated wherever the retuning
walk / `model_weight` is documented, so an Act-cadence review knows it cannot yet
justify moving the weight off 0:

- config comment block every instance renders: `template/pdca.toml.jinja:192-202`
  ("know the loop's blind spot… a retuning pass has no evidence that can justify moving
  model_weight off 0: leave it at 0 and record the gap");
- harness docs: `docs/07-crosscutting.md:166-172` ("the evidenced Act-cadence outcome
  for `model_weight` is 'stays 0, gap recorded' — not a retune");
- at the default's definition: `template/src/pdca_harness/sizing.py:106-113`
  (`DEFAULT_MODEL_WEIGHT` docstring — "does not mistake 'no visible correlation' for
  'no correlation'").

**The optional calibrator model-verdict feature — measured, then declined:** the
reviewer allowed it "if small, not required". Concretely it is not small once made
honest: `Row` field + `FEATURES` entry (2 lines) and threading `cfg` into
`extract()`/`scan()` (~4 lines) are the easy part, but (i) "no verdict" vs "verdict ok"
both read 0, so it needs the same declared-subset treatment `difficulty_rank` gets
(`size-calibrate:104-106`, `size-calibrate:492-495` — a sentinel filter plus its own
starred correlation row, ~8-10 lines); and (ii) the staleness contract invalidates the
stored verdict once the brief changes — `leaves.current_sizing`
(`template/src/pdca_harness/leaves.py:914-931`) returns `None` when `brief_sha` no
longer matches, and an iterate *appends to the brief*, so churned bundles
systematically lose their verdict: the column would be missing on exactly the churned
half of the corpus, a one-sided hole of the same shape as the outcome-leak the miner's
docstring spends 30 lines guarding against (`size-calibrate:16-39`). An honest feature
therefore needs raw-read semantics plus its own leak analysis — realistically 30-40
lines of code + tests + prose in a read-only miner whose *other* numbers are already
published calibrations. That exceeds "small", and a misleading mostly-empty column is
worse than a named gap. Declined; the named gap is shipped instead, which is the
minimum the finding requires.

**Test:** `test_retuning_walk_names_the_model_verdict_blind_spot`
(`template/tests/test_act_index_sizing.py:226-235`) — asserts the shipped config
template carries the caveat (`"model-verdict"`, `"escalation-vs-outcome"`); runs in
both the template repo and a rendered instance via the same `_config_template()`
fallback as v1's docs tests.

## Red→green evidence — via the project's own runners

- **Official C4 gate** (`engine/scripts/run-verify.sh`, the `[[gates.checks]]`
  C4-verify cmd, run from the instance root with `PDCA_BUNDLE`/`PDCA_WORKTREE` set):
  green leg 11/11 OK with the fix; red leg (production hunks reverted)
  `FAILED (failures=2, errors=9)`; **`C4 PASS: red without the fix, green with it`**,
  exit 0.
- **Iteration-2-specific red** (the binding check for *this* attempt): with only
  `act.py` + `pdca.toml.jinja` reverted to the **v1 (rejected) state** and the rest of
  the patch in place, the bundle test module fails with **exactly the two new tests**
  red — the overflow test erroring `OverflowError: integer division result too large
  for a float` at `act.py:755 in _size_column` (the T3 finding, verbatim) and the
  blind-spot test failing `'model-verdict' not found` — `Ran 11 … FAILED (failures=1,
  errors=1)`; v1's nine tests stayed green, i.e. the accepted behaviour is untouched.
  State was then restored and re-verified 11/11 OK, and the tree re-diffed
  byte-identical to the shipped `patch.diff`.
- **T3 whole-suite gate** (`engine/scripts/run-suite.sh` — the gate the rejection was
  recorded under): render + update-compat suite `Ran 7 … OK`; offline driver suite
  `Ran 1325 tests … OK (skipped=2)`. Exit 0.
- **T2 docs gate** (`engine/scripts/run-docs-check.sh`, I touched
  `docs/07-crosscutting.md`): `lint_docs: OK`, `render_site: link audit OK`. Exit 0.

## Forced self-refutation (a)/(b)/(c)

- **(a) Genuine red?** **Yes**, at two granularities, actually run (above): full
  production revert → 2 failures + 9 errors; iteration-2-only revert to the previously
  rejected v1 state → exactly the two new tests red, with the finding's own traceback.
- **(b) Production path?** **Yes.** The tests import and drive the real
  `pdca_harness.act` / `pdca_harness.sizing` package from `template/src`
  (`PYTHONPATH=src`, the runner's own invocation), and the docs test reads the shipped
  `template/pdca.toml.jinja` itself — no mock, copy, or re-implementation anywhere in
  the module.
- **(c) Fixture includes the fault?** **Yes.** The fixture writes an actual
  `size-signal.json` containing the pathological value (`patch_bytes = 10**400` — the
  int-that-overflows-float class the finding names), inside a genuinely frozen bundle
  (real `SUMMARY.md` from the shipped template + `signoff.record` accept), and keeps a
  healthy sibling in the same index run rather than curating the corpus down to the
  happy path.

## Commit-readiness for the target repo

The target has no pre-commit/formatter config to run (no `.pre-commit-config.yaml`,
`pyproject.toml`, `setup.cfg`, or ruff/flake8 config at the repo root — checked), and
`CONTRIBUTING.md` mandates no formatter. Its CI is `docs-check` / `render-check` /
`require-linked-issue` workflows; the first two are exactly the T2 docs gate and the
render suite run green above, and the third is satisfied at publish (the PR references
#359). Python style matches the surrounding files (comment-heavy, ~95-col lines, same
guard idiom as `size_signal._int`).

## Criterion (d) — mining archived `iteration-v*/brief.md`: decision unchanged from v1

**For the PR prose (checked at sign-off, not by a gate):** this change does **not**
mine archived `iteration-v*/brief.md` files and therefore reports no correlation
delta — an explicit decision, for v1's reasons, which the reviewer did not contest:
(1) the corpus that would answer it lives in rendered instances, not this repo, so any
number produced here would be un-reproducible from the tree it lands in; (2) the miner
already names the gap aloud on every run (`size-calibrate:475-480` — "Mining the
archived iteration-v*/brief.md as its own data point would recover them; this run does
not."); (3) the proposal scopes this change to building the loop, with retuning itself
explicitly out of scope.

## External dependencies

None beyond the brief's declaration (`External dependencies: none`) — everything ran
offline through the instance's configured runners. No NEEDS-HUMAN items from this side.
