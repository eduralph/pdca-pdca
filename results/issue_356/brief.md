# Brief — issue 356 / loop-telemetry-records-the-effective-tier

> The Plan artifact (docs 02 §PLAN). Do reads ONLY this file.

- **Slug:** loop-telemetry-records-the-effective-tier
- **Defect:** `_record_loop_attempt` (`template/src/pdca_harness/leaves.py:1214-1238`) records
  each Do attempt as `label = builder.argv[0] if builder.argv else builder.mode` plus
  `builder.family` (`:1232-1233`). For an escalation ladder that climbs **within one vendor** —
  the shape both the docs and the shipped `[[leaves.builder_escalation]]` example suggest
  (sonnet/high → opus/xhigh → opus/max) — every tier writes the identical
  `{"builder": "claude", "family": "claude"}`, so `loop-telemetry.json` cannot say which tier a
  bundle actually passed on. That is the one question the file exists to answer: its own
  docstring calls the attempt count "the go/no-go metric for adopting a cheaper local executor"
  (`:1215-1219`) and `pdca.toml.jinja`'s `builder_escalation` comment promises "which backend
  ran each pass". Cross-**vendor** ladders are distinguishable today; same-vendor ones are not.
  Found by a Codex review on the gramps-testbed-v2 instance (eduralph/gramps-testbed-v2#334).
- **Success criterion:** each entry `_record_loop_attempt` appends to `loop-telemetry.json`
  names the tier that **actually ran** the attempt, additively: alongside today's `n`,
  `builder`, `family` it records the effective model and the effective effort, resolved with
  **argv precedence** —
  (a) when the selected builder's argv already carries the family's model flag / effort mapping
  (`--model sonnet`, `-m opus`, `-c model_reasoning_effort=low`, and the `=`-joined `--model=…`
  form), the recorded values are those **argv** values;
  (b) when argv is silent, they are the leaf's `model` / `effort` keys;
  (c) when neither is set, they are empty strings — never a guessed CLI default;
  (d) the probe that decides (a) matches the flag token **exactly**, so a family whose model
  flag is `-m` does not match inside an unrelated `--model-info`-style argument.
  `n`, `builder` and `family` keep their existing shape and meaning (`_resolved_builder_family`,
  #200, reads `family`), and the sidecar stays best-effort — nothing here may raise out of Do.
- **Falsifiability:** RED on the base toolchain, no model and no network, on the target checkout
  Do is given. `cd template && PYTHONPATH=src python3 -m unittest tests.test_loop_escalation`
  fails on `origin/main` because the appended attempt dict has no model/effort keys at all
  (`leaves.py:1233`), and passes with the patch. The harness for it already exists in that
  module: `LoopTelemetry` (`template/tests/test_loop_escalation.py:73-116`) drives the real
  `leaves.do_build` with a no-op command builder and a brief that names no branch target, so no
  worktree, no network and no model are involved. C4-verify earns a real red→green:
  `leaves.py` classifies as a production hunk under `engine/scripts/run-verify.sh:41-46`, the
  red leg reverts it and keeps the test.
- **Invariant to restore:** the loop-telemetry sidecar records the backend that **actually ran**
  an attempt — the effective configuration after the precedence the driver itself applies — not
  the configuration that was requested. Quantified over the category: it binds every field the
  sidecar records about a backend, for every family and every ladder shape, not only the
  same-vendor case in the report — a patch that read `builder.model` / `builder.effort`
  directly would satisfy the report's example and still visibly fail this, because a leaf with
  keys opus/high and argv pinning sonnet/low **runs** sonnet/low. Source: `_mapped_argv`
  (`template/src/pdca_harness/leaves.py:150-165`), which states and implements the precedence —
  "Explicit argv is the escape hatch and always wins: a flag already present in `argv` is never
  added twice" — so reading the keys names what was asked for, corrupting the very calibration
  the field exists for. Internal rule, Tier C per `docs/principles.md` §5; §5/§6 are an unfilled
  scaffold in this instance, so no §6 category gate applies. This is a behavioural fix under
  §1.1: smallest reviewable delta.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Surfaces:** data
- **Difficulty:** low
- **Scope:** make the recorded attempt name the effective backend tier, including within one
  vendor. / out of scope: changing or reinterpreting `n` / `builder` / `family` (readers depend
  on them, #200); the ladder and selection logic (`select_builder`, `[[leaves.builder_variant]]`
  / `[[leaves.builder_escalation]]` semantics); telemetry for the reviewer, advisory or any
  other leaf; new `pdca.toml` keys; any change to `_mapped_argv`'s own behaviour; consumers /
  reporting of `loop-telemetry.json`.
- **Repro instruction:** on the target checkout, read
  `git -C ../pdca-harness show origin/main:template/src/pdca_harness/leaves.py` at 1232-1233 —
  the attempt dict is `{"n", "builder", "family"}` and nothing else. Then run the existing
  `LoopTelemetry` cases (`template/tests/test_loop_escalation.py:88-104`) with a
  same-vendor ladder — two `LeafConfig`s of the same `family` differing only in `model` /
  `effort` (or in the argv that pins them) — and observe both attempts serialise identically,
  so no assertion can tell tier 1 from tier 2. The added cases automate that → red pre-fix.
- **External dependencies:** none
- **Test file:** `template/tests/test_loop_escalation.py` — append a `TelemetryRecordsTheTier`
  class beside the existing `LoopTelemetry` (the instance work referenced on the issue carries
  tests of that name and can move up with the change). Appending to an existing suite earns its
  red fine here: `run-verify.sh:70-75` reverts **production** hunks only and keeps the test in
  place. Cover all four criterion legs plus the exact-token probe (d).
- **Citations expected:** Do must cite path:line on the target branch for every change. This is
  a composition slice — the resolution must agree with the mapping it mirrors. The peer callsite
  is `_mapped_argv`, `template/src/pdca_harness/leaves.py:150-165`: reuse its precedence
  ("argv wins") and derive the effort probe the way it does — `probe = rendered[0] if
  rendered[0].startswith("--") else rendered[-1].split("=", 1)[0]` — so the two stay in
  agreement about which flag a family's effort mapping owns. Do MAY open that one callsite.
  Supporting facts, already verified, that need no exploration: the family profile supplies
  `model_flag` / `effort_argv` (`template/src/pdca_harness/families.py:59-60`), claude is
  `--model` + `("--effort", "{effort}")` (`:91-92`), codex is `-m` +
  `("-c", "model_reasoning_effort={effort}")` (`:103-104`); the caller
  `do_build` (`leaves.py:1286`) already holds the `cfg` that `cfg.profile(builder)` needs.
  Note `_mapped_argv`'s own dedup test is the looser `probe in a`; the telemetry probe is
  deliberately exact per criterion (d), and the strictness only ever costs a fallback to the key.
- **Prior-art check (triage cycles):** by affected file path —
  `git -C ../pdca-harness log --oneline origin/main -- template/src/pdca_harness/leaves.py` →
  the sidecar was introduced by #135 (escalate-on-iterate + iterations-to-pass telemetry) and
  the shape at `:1232-1233` is unchanged since; `git grep -n "_record_loop_attempt" origin/main`
  → one writer (`:1214`), one caller (`:1286`), one doc reference (`state.py:129`).
  `gh search issues --repo eduralph/pdca-harness "telemetry"` → #135, #137, #200, #260, #332
  (all closed, none about tier attribution), #356 (this).
  `gh pr list -R eduralph/pdca-harness --state open` → empty. Not fixed, not in flight.
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.
