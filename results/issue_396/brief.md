# Brief — issue 396 / trailing-flag-swallows-interactive-seed

> The Plan artifact (docs 02 §PLAN). Human-authored. Do reads ONLY this file.
> The field labels below are parsed by the driver — keep the `- **Label:** value`
> shape. The success criterion is the load-bearing field: it is the sentence
> Check tests "did this work" against.

- **Slug:** trailing-flag-swallows-interactive-seed
- **Defect:** The template's REMOTE CONTROL doc (`template/pdca.toml.jinja:548-552`) and
  `template/docs/INTEGRATION.md.jinja:156-157` both instruct "APPEND the flag to the
  argv line", with the example showing `--remote-control` as the LAST argv token. But
  the driver seeds every interactive leaf as `subprocess.run(argv + [seed])`
  (`template/src/pdca_harness/leaves.py:379`, via `_seed_positional`,
  `leaves.py:183-216`, #313) — the prompt is the FINAL positional — and
  `--remote-control` takes an optional `[name]` value. Following the doc verbatim makes
  the flag consume the entire seed prompt as the RC session name: Remote Control fails to
  start ("check the debug log") and the REPL opens with no seed. Hit in practice on this
  instance the first time the flow reached a planner after enabling RC
  (eduralph/pdca-pdca#19; worked around there by moving the flag before `--agent`).
- **Success criterion:** (1) Docs: the example in pdca.toml.jinja and the INTEGRATION
  template place the flag NON-last and say why — any flag with an optional value must
  never sit last in an interactive leaf's argv, because the seed is appended as a
  positional after it. (2) Driver: when seeding an interactive leaf of a family whose CLI
  supports an end-of-options separator, the driver appends the seed after it
  (`argv + ["--", seed]`), declared as a families-profile bit (claude: `--`; a family
  without the bit keeps the current bare-positional spawn) — so NO trailing
  optional-value flag can ever swallow the seed, whatever an instance puts in its argv.
  A shipped test asserts the interactive claude-family spawn carries the separator
  between the configured argv and the seed.
- **Falsifiability:** RED is producible offline: a `test_seed_spill.py` test that
  monkeypatches the interactive spawn and asserts the separator sits between argv and
  seed fails on current `main` (`leaves.py:379` appends the bare seed, verified at
  `0fbfa26`); the doc assertion likewise fails against the current example
  (`pdca.toml.jinja:551-552` shows the flag last). Environment: plain python3 unittest,
  no claude binary needed (spawn is monkeypatched). The CLI fact is pre-verified at Plan:
  `claude -p -- "<prompt>"` parses the prompt as the positional on claude 2.1.222.
- **Invariant to restore:** An interactive leaf's seed must reach the REPL as the prompt
  under every argv the template sanctions — an option's greed for a value must never be
  able to eat it. Source: the #313 seed contract (`leaves.py:184-199`: the seed "goes as
  ``claude "<seed>"``") and the POSIX Utility Syntax Guidelines' end-of-options
  convention (guideline 10: `--` terminates option parsing), which is exactly the
  mechanism that makes the guarantee argv-independent.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Conflicts with:** 419
- **Ordering note:** conflicts-with 419 because both patch
  `template/src/pdca_harness/leaves.py` (this bundle the interactive spawn at ~380, 419
  the reviewer-sandbox seam) — different regions, but same file: schedule into different
  waves rather than build blind on the same base. Also touches pdca.toml.jinja, which 413
  edits too; 413 already declares that conflict.
- **Surfaces:** data
- **Difficulty:** medium
- **Scope:** the two doc examples + the interactive-seed separator (families-profile bit
  in `families.py`, applied at the one spawn site in `leaves.py`) / out of scope: the
  headless stdin path (`leaves.py:384+`, not affected — the prompt rides stdin there),
  any change to `_seed_positional`'s spill logic, enabling Remote Control by default,
  non-claude families' separator support (ship the bit unset for them unless Do can
  verify a vendor's CLI accepts `--`).
- **Repro instruction:** Configure an interactive leaf's argv per the current doc example
  (uncomment `pdca.toml.jinja:551-552`, flag last) and run a flow to any interactive
  leaf: the REPL opens with no seed and RC errors "error trying to start remote control /
  check the debug log", while in-session `/remote-control` works on the same machine
  (the symptom signature; observed as eduralph/pdca-pdca#19). Mechanically:
  `leaves.py:379` shows the seed appended after whatever argv ends with.
- **External dependencies:** none
- **Test file:** template/tests/test_seed_spill.py (append: the interactive spawn places
  the family's end-of-options separator before the seed for a claude-family leaf, and no
  separator for a family without the bit. The doc-example assertion — the RC flag is not
  the argv-final token in the shipped example — belongs beside the existing RC doc suite
  `template/tests/test_remote_control_docs.py`; both files ride the patch and the
  instance C4 contract runs every changed test module.)
- **Citations expected:** Do must cite path:line on the target branch for every change —
  `leaves.py:379` (the spawn), `leaves.py:183-216` (`_seed_positional`),
  `pdca.toml.jinja:548-552` (the APPEND instruction + example),
  `docs/INTEGRATION.md.jinja:156-170` (both family branches of the RC section),
  `families.py:86-96` (claude profile, where the separator bit lands).
- **Prior-art check (triage cycles):** `git -C ../pdca-harness log --oneline origin/main
  -- template/pdca.toml.jinja` and the RC test suite — #337 documented the seam
  (`a641742`) and #386 hardened its test (`75294d1`); both keep the flag-last example,
  and `leaves.py` still seeds a bare positional at `0fbfa26`. No open PRs.
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: Auto-iterate (round 1): Check found implementation-level items only, no architectural judgment required — T2 Shape — Decide whether the passing documentation unit coverage is sufficient or the exact site-render/link audit must be rerun — `./engine/scripts/run-docs-check.sh` is not present in the target, so the asserted audit was not independently reproducible (`template/tests/test_remote_control_docs.py:128`).; T3 Runtime — Decide whether argv-level proof is enough for release — 1,567 offline tests pass, but the mocked spawn cannot demonstrate that installed Claude 2.1.223 starts Remote Control and preserves the seed with `--remote-control -- <seed>` (`template/tests/test_seed_spill.py:201`).; T4 Contribution — Confirm the user-impact opener and tracker reference in the contribution artifacts before publish — those artifacts are intentionally absent from the reviewer inputs, so the reported gate pass cannot be rerun from this sandbox.
- Failing gate: T3 runtime: render/update-compat + offline driver suites (advisory) — == T3: root suite OK, driver suite FAILED (rc 1)
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
