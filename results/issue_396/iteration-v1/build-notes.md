# Build notes — issue 396 / trailing-flag-swallows-interactive-seed

Target: eduralph/pdca-harness @ main (`0fbfa26`), built in `$PDCA_WORKTREE`
(`/home/eddie/pdca/pdca-harness.pdca-wt-l1`).

## What changed, and why this shape

The defect has two halves and the patch fixes both, per the brief's success criterion:

1. **Driver — make the seed argv-independent (the invariant).** The one interactive
   spawn site (`template/src/pdca_harness/leaves.py:379` on main:
   `subprocess.run(argv + [seed], …)`) now inserts the family's end-of-options
   separator between the configured argv and the seed:
   `subprocess.run(argv + sep + [seed], …)`, where `sep` comes from a new
   families-profile bit `FamilyProfile.seed_separator`
   (`template/src/pdca_harness/families.py:78` field block; claude built-in at
   `families.py:82-96` gets `seed_separator="--"`). POSIX guideline 10: after `--`
   everything is positional, so no trailing optional-value flag — whatever an instance
   puts in its argv — can consume the seed. Families without the bit (codex, gemini,
   generic) keep the byte-identical bare-positional spawn, exactly as the brief scopes
   ("ship the bit unset for them unless Do can verify" — I cannot verify vendor CLIs
   here, and the brief pre-verified only claude: `claude -p -- "<prompt>"` on 2.1.222).
   The memory-cap wrapper's own `--` (`leaves.py:317`, prepended ahead of the leaf
   argv at `leaves.py:370`) is unaffected: the new separator sits *after* the leaf's
   command token, so it is parsed by the leaf CLI, not by systemd-run.

2. **Docs — the example itself was the repro.** `template/pdca.toml.jinja:548-552`
   showed `--remote-control` as the LAST argv token; following it verbatim made the
   flag eat the whole seed as an RC session name (eduralph/pdca-pdca#19). The example
   now places the flag non-last and the comment states the rule and the why: the seed
   is appended as a positional, so *any* flag with an optional value must never sit
   last ("Put it anywhere but LAST: …", with the #396 pointer and the note that the
   claude spawn's `--` is a backstop, non-last placement being the posture every
   family supports). Both family branches of the RC section in
   `template/docs/INTEGRATION.md.jinja:155-171` got the same guidance — the non-claude
   branch additionally says families without a declared `seed_separator` have no
   backstop, so placement is their only protection.

Wording constraint honoured deliberately: the shipped suite phrase-asserts "APPEND"
and "do not add a second" (`template/tests/test_remote_control_docs.py:90-91` on
main), so the rewritten comment keeps both literals and *qualifies* placement rather
than replacing the append instruction — no weakening of an existing assertion.

## Tests (both ride the patch, per the brief's Test-file field)

- `template/tests/test_seed_spill.py` (appended `SeedSeparator` suite):
  - the interactive claude-family spawn carries `--` between the configured argv and
    the seed — asserted with the **exact defect argv** (`--remote-control` last, the
    doc-sanctioned repro), by full-argv equality;
  - a family without the bit keeps the bare positional (`argv + [seed]`, no `--`);
  - the bit is profile DATA: claude `"--"`, codex/gemini/generic `""`.
- `template/tests/test_remote_control_docs.py` (appended
  `test_the_example_never_shows_the_flag_last`): extracts every *commented*
  `argv = [...]` example from the shipped config (comment lines joined, so the
  wrapped example parses) and asserts no RC example ends in `--remote-control`, plus
  that the placement rule is stated ("anywhere but LAST"). The posture-harness
  `_DOC_BLOCK` (`test_remote_control_docs.py:156-167` on main) was updated to the new
  example shape — it feeds the child runs that re-execute this whole module against
  synthetic rendered configs, which now include the new assertion.

## Ruled out (with cost)

- **Doc-only fix** (move the flag in the example; ~2 changed lines): rejected because
  the brief names an *invariant to restore* — the seed must survive **every** argv the
  template sanctions. A doc fix protects only instances that re-read the doc; any
  existing flag-last argv, or any future optional-value flag, still swallows the seed.
  Cost is not the axis here (docs/principles.md §1.2): the smallest change restoring
  the invariant is the separator.
- **Unconditional `argv + ["--", seed]` for all families** (~6 lines smaller: no
  profile field, no claude override, no per-family test leg): rejected because `--`
  is only *verified* for claude; a vendor CLI that treats `--` as an ordinary argument
  would get a garbage positional prepended to its seed on every interactive leaf. The
  brief scopes exactly this out.
- **Config-load validation of trailing flags** (reject/warn when an interactive
  leaf's argv ends in a flag): needs a per-family table of which flags take optional
  values — unknowable for arbitrary CLIs and instance-added flags — so it fails open
  precisely on unknown flags; sketch: a `TRAILING_OPTIONAL_VALUE_FLAGS` dict plus a
  config-time walk over `[leaves.*].argv`, ≈40 lines in `config.py` + per-family data
  to maintain, and it still only *guards the symptom*. The separator *removes the
  cause* mechanically at the spawn.

## Refutation record (forced three questions)

- **(a) Genuine red?** Yes — via the project's C4 runner
  (`engine/scripts/run-verify.sh`, wired at `pdca.toml:830`), not a hand-rolled
  invocation: green leg passed, then with only the production hunks reverted the red
  leg failed — `test_seed_spill` FAILED (failures=1: the missing `--`; errors=1: the
  reverted profile has no `seed_separator` field) — and the runner printed
  `C4 PASS: red without the fix, green with it`. Separately, the doc suite against
  the pre-fix `pdca.toml.jinja` (stash/restore) FAILED (failures=2: the flag-last
  example subtest + the missing placement rule). Both halves of the criterion bind.
- **(b) Production path?** Yes — the spawn tests drive the real
  `leaves._invoke` interactive branch (profile resolution via `families.resolve`,
  role/model/memory argv assembly, `_seed_positional`) and record only the terminal
  `subprocess.run` call, which is precisely the observable under test (spawned argv);
  nothing is re-implemented. The doc test reads the real shipped
  `pdca.toml.jinja`/`pdca.toml`, resolved the way the existing suite does.
- **(c) Fixture includes the fault?** Yes — the claude spawn test uses the literal
  failing configuration from the field report: `["claude", "--agent", "planner",
  "--permission-mode", "acceptEdits", "--remote-control"]` with the flag LAST, the
  argv the old doc told instances to write.

## Verification summary

- C4 wrapper (`run-verify.sh`): **PASS** (green leg + red leg, both changed modules).
- Changed modules with fix: 26 tests, OK (1 posture skip, expected in the template
  checkout).
- Full offline driver suite (`cd template && PYTHONPATH=src python3 -m unittest
  discover -s tests`, the CONTRIBUTING.md:26 contract): **1567 tests, OK** —
  including the memory-cap and seed-spill suites that assert on `_invoke`'s spawn
  shape (generic-family spawns are byte-identical, so nothing else moved).
- T3 wrapper (`run-suite.sh`): root suite OK (render + update-compat — the shipped
  tests also pass *inside a rendered instance*, where `TOML = pdca.toml`), driver
  suite OK.
- Commit-readiness: the target repo configures no pre-commit hooks or formatter
  (no `.pre-commit-config.yaml`, no root `pyproject.toml`, no `core.hooksPath`);
  its stated bar is the offline suite green (CONTRIBUTING.md:24-26). `git diff
  --check` clean; every added line ≤ 95 columns (long lines flagged in the files
  pre-date this patch).
- External dependencies: none needed beyond plain python3 unittest, as the brief
  declared.
