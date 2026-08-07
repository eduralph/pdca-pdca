# Build notes — issue 356 (loop telemetry records the effective tier)

Target: `eduralph/pdca-harness @ main`, built in `$PDCA_WORKTREE`
(`/home/eddie/pdca/pdca-harness.pdca-wt-l0`, base `5e655c2`). All `path:line`
citations below are post-patch lines in that worktree unless marked "pre-patch".

## What the change is

Three hunks (`patch.diff`: +58/−4 `leaves.py`, +111/−0 the test, +2/−1 `pdca.toml.jinja`).

1. **`_argv_pinned(argv, token)`** — `leaves.py:1214-1229`. Returns the value a flag
   token is pinned to in argv, or `None` when absent. Handles both spellings
   (`["--model", "opus"]` and `--model=opus` / `model_reasoning_effort=low`) and matches
   the token **exactly** (equality or the `token=` prefix) — criterion (d). `None` vs `""`
   is load-bearing: `None` = "argv is silent, fall back to the key"; `""` = "argv pins an
   empty value" (a trailing flag with no operand), which is still an argv answer.

2. **`_effective_tier(leaf, profile)`** — `leaves.py:1232-1253`. Mirrors `_mapped_argv`
   (`leaves.py:150-165`, the cited peer callsite) — the function that decides what
   actually reaches the CLI: "Explicit argv is the escape hatch and always wins". So:
   argv value if pinned, else the leaf's `model`/`effort` key, else `""`. The effort
   probe is derived with `_mapped_argv`'s own line verbatim
   (`probe = rendered[0] if rendered[0].startswith("--") else rendered[-1].split("=", 1)[0]`,
   `leaves.py:1250` vs `:161`), so the two stay in agreement about which flag a family's
   effort mapping owns. The probe is independent of the effort *value*, so an argv-pinned
   effort is found even when the leaf sets no `effort` key at all (rendering with
   `effort=leaf.effort` only ever fills the value slot).

3. **`_record_loop_attempt`** — `leaves.py:1256` (signature now takes `cfg`),
   `:1282-1287` (the two new fields). The attempt dict gains `model` / `effort`
   **additively**; `n` / `builder` / `family` are untouched in shape and meaning, so
   `_resolved_builder_family` (#200) keeps reading `family`. Caller updated at
   `leaves.py:1340` (was `_record_loop_attempt(d, n, builder)` at pre-patch `:1286`) —
   `_do_build_command` already holds `cfg`, exactly as the brief noted.

4. `pdca.toml.jinja:396-397` — the comment that *promised* "which backend ran each pass"
   now says what is actually recorded (family + effective model/effort). One line; the
   brief cites that promise as part of the defect.

## Decisions and rejected alternatives

**Read `builder.model` / `builder.effort` directly (rejected).** It is a 2-line patch and
it satisfies the report's example — but it records what was *requested*. `_mapped_argv`
never adds a flag already present in argv (`leaves.py:156`, `:162`), so a leaf with
`model = "opus"` whose argv carries `--model sonnet` **runs sonnet**. The invariant the
brief names ("the backend that actually ran … not the configuration that was requested")
is exactly what that patch would violate; the shipped
`[[leaves.builder_escalation]]` example in `pdca.toml.jinja:401` pins the model *in argv*
(`"--model", "opus"`), so the common ladder is the argv-pinned one and the cheap patch
would mis-record it in practice, not only in theory. Cost of doing it right over doing it
cheap: **+30 production lines** (`_argv_pinned` 16 incl. docstring, `_effective_tier` 22,
minus the 2-line cheap version and the 6 lines of shared call/append). That is the
smallest change that restores the invariant, not the smallest diff (§1.2/§2).

**Pass `profile` instead of `cfg` (rejected, cosmetic).** `_do_build_command` computes
`profile = cfg.profile(builder)` at `leaves.py:1345`, *after* the telemetry call at
`:1340`; passing the profile would mean reordering those two statements as well as
changing the signature — same size, more motion in an unrelated part of Do. `cfg` is what
the brief points at and keeps the resolution (`cfg.profile`, `config.py:414-417`) inside
the one function responsible for the record, so `[families.*]` overrides apply for free.

**Change `_mapped_argv`'s dedup probe to be exact too (rejected — out of scope).** The
brief's Scope excludes "any change to `_mapped_argv`'s own behaviour", and the two
strictnesses fail in opposite directions: a loose dedup probe *skips* adding a flag
(safe — the operator's argv wins anyway), a loose telemetry probe *invents* a value
(unsafe — a false calibration record). Noted in the `_argv_pinned` docstring
(`leaves.py:1221-1223`) so the divergence is deliberate and readable, not an oversight.

**Best-effort guard** (`leaves.py:1282-1285`). `str.format` on a `[families.*]`
`effort_argv` override carrying an unknown placeholder raises `KeyError` — inside a
sidecar whose contract is "never break Do". Three lines, and covered by a test
(`test_a_malformed_family_mapping_does_not_break_do`). Fallback is `""`/`""` rather than
the keys: with a broken family profile the harness cannot know what will run, and
inventing a value is the failure mode this whole issue is about.

**Field names** `model` / `effort` — same names as the `pdca.toml` leaf keys
(`config.py:66-67`) and the family profile mapping, so a reader of the sidecar and a
reader of the config are looking at the same vocabulary. No consumer reads them yet
(Scope excludes consumers); `state.py:134` treats the file as cycle evidence only.

## Verification (project runner only — no hand-rolled invocation)

Gate `C4-verify` (`pdca.toml:830` → `./engine/scripts/run-verify.sh`), run from the
instance root with `PDCA_BUNDLE` / `PDCA_WORKTREE` set:

```
== C4 green leg: bundle test(s) with the fix applied: template/tests/test_loop_escalation.py
Ran 11 tests ... OK
== C4 red leg: bundle test(s) with the production change reverted
Ran 11 tests ... FAILED (errors=6)
C4 PASS: red without the fix, green with it
```

Gate `T3-suite` (`./engine/scripts/run-suite.sh`): template-repo suite 7/7 OK; offline
driver suite **1474 tests OK** (skipped=2) — no other caller of `_record_loop_attempt`
and no consumer of the attempt shape regressed. Gate `T2-docs`
(`./engine/scripts/run-docs-check.sh`): lint OK, site render + link audit OK.

Style/commit-readiness: the target has no Python formatter/linter hook (`.github/workflows`
carries only docs/render checks); every added line is ≤ 99 cols, inside the file's existing
envelope (longest pre-existing line in `leaves.py` is 110).

## Refutation — the three forced questions

- **(a) Genuine red?** Yes, and by the gate's own mechanism, not by hand: `run-verify.sh`
  reverts the production hunks (`--exclude=template/tests/*`, `run-verify.sh:72-75`) and
  keeps the test — all **6** new cases go red (`TypeError: _record_loop_attempt() takes 3
  positional arguments but 4 were given`, and `KeyError: 'model'` in the end-to-end ladder
  case, which is precisely "the attempt dict has no model/effort keys at all"). The 5
  pre-existing cases in the module stay green in both legs, so the red is attributable.
- **(b) Production path?** Yes. The tests import `pdca_harness.leaves` under
  `PYTHONPATH=src` and call the production writer `leaves._record_loop_attempt`
  (`leaves.py:1256`) and the production entry point `leaves.do_build` (`leaves.py:1295`);
  the family profiles are the real built-ins (`families.py:82-109`) resolved through the
  real `Config.profile` (`config.py:414-417`). Nothing is re-implemented in the test — the
  expected values are literals, and the resolution under test is the shipped one. The one
  stub is `leaves._invoke` in the end-to-end case (the same technique as the peer test
  `test_do_confine.py:90-103`), which is *downstream* of the telemetry write at
  `leaves.py:1340`: it only prevents spawning a CLI, it cannot supply the record.
- **(c) Fixture includes the fault?** Yes. `test_same_vendor_ladder_is_distinguishable_end_to_end`
  uses the **same-vendor** ladder the report is about — two `claude` tiers, identical
  `family` and identical `argv[0]` — and asserts those two fields *are equal* before
  asserting the tiers are now tellable apart, so the fixture cannot quietly become a
  cross-vendor ladder (which is already distinguishable today and would prove nothing).
  Criterion (d) is tested against the real `codex` profile whose model flag `-m` really is
  a substring of `--model-info`, i.e. the argument that would fool a loose probe is present
  in the fixture rather than curated out.

## Not done / not in scope

No consumer, report, or `SUMMARY` surface reads the new fields yet (Scope). No new
`pdca.toml` keys. `select_builder` and the variant/escalation semantics are untouched.
No external dependency was needed (brief: none) and none was discovered.
