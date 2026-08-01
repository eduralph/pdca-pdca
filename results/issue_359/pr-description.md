# Act-index sizing column + configurable model weight

## Summary
**User impact:** The harness estimates how big a piece of work will be before it
starts, and flags likely-oversized tasks — but the numbers behind that estimate are
only ever checked when someone re-derives them by hand, so they can drift silently
for a long time. That is not hypothetical: the 0.56 release shipped a published
precision figure that had quietly moved from 67% to 62%, and nothing in the tool
would ever have surfaced it.

This PR makes that drift visible where maintainers already review cross-cycle
patterns: the periodic review index now shows, for every finished cycle, what the
estimator predicted next to what actually happened — and the config now documents
how to walk a fresh calibration run back into the thresholds, including one weight
that becomes tunable config instead of an engine constant.

Reported in [#359](https://github.com/eduralph/pdca-harness/issues/359).

## What to look at
Run `pdca act index` in an instance with settled cycles: each cycle now carries a
`sizing:` line — the up-front estimate beside the measured outcome, with `—` for
"not measured" (e.g. cycles that predate the recorded signal). Then open the
`[driver.sizing]` comment block in a rendered `pdca.toml`: it walks a
`scripts/size-calibrate` run back into the table step by step and defines the new
`model_weight` key, including the one thing a retuning pass cannot yet see. The
change concentrates in the review-index renderer and the size estimator; shipped
default weights are untouched.

## Root cause
The calibration loop opened by #320 (a-priori estimator) and #324 (recorded
Check-time size signal, merged as cad960143d6344f1ccf35899e5fcc42562488ea6) had no
read-back surface: the estimate and the recorded outcome were never joined anywhere
a human routinely looks, so estimator drift was undetectable short of re-running the
calibration by hand. The sizer verdict's contribution to the numeric score was
additionally hard-coded (band-only), so even a review that spotted drift had no
configuration point to act on.

## Fix
- `template/src/pdca_harness/act.py` — `_size_column` joins the brief-derived
  a-priori estimate with the outcome read from the cycle's recorded
  `size-signal.json` (never re-measured at review time), and `render_index` prints
  it per cycle. Either side is blank when unavailable: a cycle predating the signal,
  or a garbled recorded value — an integer beyond float range blanks its own cell
  instead of aborting the whole index. Blank means "not measured", never "measured
  small", so nothing is clamped into a number nobody measured.
- `template/src/pdca_harness/sizing.py` + `config.py` — `model_weight` is read from
  `[driver.sizing]` (`DEFAULT_MODEL_WEIGHT = 0`); an above-`ok` sizer verdict adds
  the configured weight to the score, escalate-only and clamped at 0, so the default
  reproduces today's scores byte-for-byte. Config is threaded through the four
  production `combine` callsites (`cli.py`, `leaves.py`, `plan_policy.py`).
- `template/pdca.toml.jinja` + `docs/07-crosscutting.md` — the documented retuning
  walk from `scripts/size-calibrate` output back into `[driver.sizing]`, revisited
  at Act cadence. It names the loop's blind spot explicitly: the index shows the
  structural estimate only and the calibrator mines no model-verdict feature, so
  escalation-vs-outcome correlation is not observable from any shipped artifact yet
  — an evidenced review therefore leaves `model_weight` at 0 and records the gap,
  rather than tuning it on taste.

### Correlation-mining decision (required by the issue)
This change does **not** mine archived `iteration-v*/brief.md` files and therefore
reports no correlation delta — an explicit decision: (1) the corpus that would
answer it lives in rendered instances, not this repo, so any number produced here
would be un-reproducible from the tree it lands in; (2) the miner already names the
gap aloud on every run (`template/scripts/size-calibrate:475-480`); (3) this change
builds the loop that keeps the numbers honest — retuning itself is out of scope.

## Verification
- **Claim (a):** the index renders the a-priori estimate beside the recorded
  outcome per frozen cycle, with a graceful blank for cycles predating the signal.
  **Checked:** `template/src/pdca_harness/act.py:725-766` (`_size_column` reads the
  recorded signal only) and `template/src/pdca_harness/act.py:576-581` (the rendered
  line + the blank contract).
  **Test:** `template/tests/test_act_index_sizing.py:95-129` — fails pre-fix (no
  join exists), passes post-fix; the blank case asserts no outcome is fabricated by
  measuring what is on disk at review time.
- **Claim (robustness):** one garbled recorded value costs its own cell, never the
  whole index.
  **Checked:** `template/src/pdca_harness/act.py:755-766` — an int that parses but
  exceeds float range blanks the outcome instead of raising through the renderer.
  **Test:** `template/tests/test_act_index_sizing.py:131-153` — a
  `patch_bytes = 10**400` record blanks its own cell while a healthy sibling cycle
  still renders; errors pre-fix with `OverflowError`.
- **Claim (b):** a documented retuning procedure exists.
  **Checked:** `template/pdca.toml.jinja:173-212` (the `[driver.sizing]` block:
  the step-by-step walk, `model_weight`, the named blind spot) and
  `docs/07-crosscutting.md:154-172`.
  **Test:** `template/tests/test_act_index_sizing.py:207-247` — walk present,
  blind spot named, and the example block matches the shipped defaults both ways.
- **Claim (c):** `model_weight` is config with today's behaviour as default,
  escalate-only.
  **Checked:** `template/src/pdca_harness/sizing.py:97-114` (default + its
  Act-cadence note), `template/src/pdca_harness/sizing.py:460-470` (score join,
  clamped at 0), `template/src/pdca_harness/config.py:319-327`.
  **Test:** `template/tests/test_act_index_sizing.py:156-205` — default 0 leaves
  scores byte-identical (with and without config), a configured weight joins only
  on escalation, and negative/malformed values cannot lower a structural score.
- **Suites:** the full offline driver suite (1325 tests), the render +
  `copier update` compatibility suites, and docs lint + site link audit all pass
  with the patch; the new test module fails 11/11 on the unpatched base.

Fixes #359
