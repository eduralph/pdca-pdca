# PR description

## Summary
**User impact:** If you let a bundle escalate to a stronger backend, `loop-telemetry.json`
was supposed to tell you which one finally got the work done — that is the number you use
to decide whether a cheaper executor is good enough. It only did so when the escalation
crossed vendors. For a ladder that climbs inside a single vendor (a mid model at high
effort, then a top model at max effort — the shape the shipped escalation example
suggests), every attempt was recorded identically, so the file could not say which tier a
bundle actually passed on, and the escalation could not be calibrated at all.

This PR makes each recorded attempt also name the model and the effort that actually ran
it. Reported in [#356](https://github.com/eduralph/pdca-harness/issues/356).

## What to look at
The change is confined to the telemetry writer in the driver's Do leaf, plus the one call
site that now hands it the config it needs to resolve the family profile. The fields are
**added** — `n`, `builder` and `family` are untouched — so nothing that reads the sidecar
today has to change.

The subtlety worth a reviewer's eye is *which* model gets recorded. A leaf can name a
model and effort in its own config keys, or pin them directly in `argv`; when both are
present, the pinned `argv` value is what the CLI actually receives. The new fields follow
that same order rather than reporting what was requested — otherwise the file would still
lie, just more convincingly. The shipped escalation example happens to pin its model in
`argv`, so this is the common case, not a corner one.

To try it: configure a `[[leaves.builder_escalation]]` entry of the same family as
`[leaves.builder]`, differing only in model/effort, run a bundle that needs a second Do
attempt, and read the bundle's `loop-telemetry.json` — the two attempts are now distinct.
The suite covering it is `cd template && PYTHONPATH=src python3 -m unittest
tests.test_loop_escalation`.

## Root cause
The attempt record was built from the selected leaf's `argv[0]` (or mode) and its family
only — `template/src/pdca_harness/leaves.py:1233` — two fields that are identical for
every rung of a same-vendor ladder. Nothing in the record reflected the model or effort,
which is precisely what such a ladder varies, so the config template's promise of "which
backend ran each pass" (`template/pdca.toml.jinja:396`) held only across vendors.

## Fix
Two small helpers in the same module resolve the *effective* tier of the selected leaf and
`_record_loop_attempt` appends it as `model` / `effort`:

- the value pinned in `argv` for the family's model flag or effort mapping, accepting both
  the separate-pair and `=`-joined spellings;
- otherwise the leaf's own `model` / `effort` keys;
- otherwise empty strings — the CLI picks its own default and the harness must not invent
  one, since a guessed value is a false calibration record.

The flag probe is derived exactly as the invocation mapper derives its own
(`template/src/pdca_harness/leaves.py:161`), so the two agree on which flag a family's
effort mapping owns, but matches the token exactly rather than by substring, so `-m` is
not read out of `--model-info`. Resolution is wrapped so a malformed `[families.*]`
override records empty values instead of raising out of a best-effort sidecar. The
escalation comment in the config template is updated to describe what is recorded.

## Verification
- **Claim:** every recorded attempt names the tier that actually ran it — argv-pinned
  values first, then the leaf's `model` / `effort` keys, then empty strings — with the
  flag token matched exactly, while `n`, `builder` and `family` keep their existing shape.
- **Checked:** `template/src/pdca_harness/leaves.py:1233` on `main` — the appended record
  is `{n, builder, family}` and nothing else, so two same-vendor tiers serialise
  identically; `:1286` is its only caller, and it already holds the config the resolution
  needs. `:150-165` on `main` is the mapper that decides what actually reaches the CLI
  ("explicit argv is the escape hatch and always wins"); the new resolution mirrors that
  precedence, so the record matches the invocation. `template/pdca.toml.jinja:396` on
  `main` is the promise the file was not keeping. `template/src/pdca_harness/families.py:91-92`
  and `:103-104` on `main` supply the real per-family model flag and effort mapping used
  by the tests (`--model` with `--effort`; `-m` with `-c model_reasoning_effort=…`).
- **Test:** `template/tests/test_loop_escalation.py` — a new `TelemetryRecordsTheTier`
  class beside the existing telemetry cases, six tests covering argv precedence (both
  spellings, and the `-c key=value` form), fallback to the leaf keys, the unset case, the
  exact-token probe against a real `--model-info` decoy, an end-to-end same-vendor ladder
  through `do_build`, and the malformed-family guard. With the production hunks reverted
  and the tests kept, all six fail; with the patch, the module passes 11/11. The full
  offline driver suite (1474 tests) and the template render/docs checks pass unchanged.
  The end-to-end case asserts that `builder` and `family` are *equal* across the two
  attempts before asserting the tiers are now distinguishable, so the fixture cannot
  quietly degrade into a cross-vendor ladder that would prove nothing.

Fixes #356
