# Build notes — issue 396 / trailing-flag-swallows-interactive-seed (iteration 2)

## What changed and why

The brief's Success criterion mandates the design directly, so the shape was never in
question: (1) both doc examples place `--remote-control` non-last and say why; (2) the
interactive spawn appends the seed after a family-declared end-of-options separator
(`argv + ["--", seed]` for claude), so no trailing optional-value flag can swallow it.

Production hunks (unchanged from iteration 1 — the auto-iterate rationale said
"implementation-level items only, no architectural judgment required", and none of the
review items indicted the production change):

- `template/src/pdca_harness/families.py:85` — new `FamilyProfile.seed_separator: str = ""`
  (default: no separator, byte-identical spawn for families without a verified CLI fact).
- `template/src/pdca_harness/families.py:106` — claude profile carries `seed_separator="--"`
  (pre-verified at Plan on claude 2.1.222; re-corroborated on 2.1.223 below).
- `template/src/pdca_harness/leaves.py:384-386` — the one interactive spawn site
  (was `subprocess.run(argv + [seed])` at `leaves.py:379` on main@0fbfa26) becomes
  `argv + sep + [seed]`. The headless stdin path (`leaves.py:391+`) is untouched, per scope.
- `template/pdca.toml.jinja:548-558` — example now `["claude", "--remote-control",
  "--agent", "planner", "--permission-mode", "acceptEdits"]` (was flag-last at
  `pdca.toml.jinja:551-552` on main), with the why: the driver appends the seed as the
  final positional, an optional-value flag last swallows it (issue #396 / pdca-pdca#19).
- `template/docs/INTEGRATION.md.jinja:156-163` (claude branch) and `:174-179` (other-family
  branch, which has no `--` backstop and must rely on placement alone) — same rule stated.

Tests (both ride the patch; the instance C4 contract runs every changed test module):

- `template/tests/test_seed_spill.py:191-235` — `SeedSeparator`: the exact defect argv
  (flag LAST) must spawn `argv + ["--", seed]` for family=claude (`:213`); a family
  without the bit keeps the bare positional, byte-identical (`:224`); the separator is
  profile DATA, claude-only (`:230`). Only `leaves.subprocess.run` is patched — the
  production `_invoke` (profile resolution, `_seed_positional`, argv assembly) runs real.
- `template/tests/test_remote_control_docs.py:150-173` — the shipped example never shows
  the flag last, and the RC comment block states the rationale.

## Iteration-1 carry-forward — what I did about each item

**Failing gate, T3 "driver suite FAILED (rc 1)".** Not reproducible. I applied the
iteration-1 patch byte-identical to the brief's base (main@0fbfa26, the same base the
brief's falsifiability section verified) and ran the exact gate command
(`engine/scripts/run-suite.sh`, incl. the instance venv python it selects): root suite
7/7 OK, driver suite **1567/1567 OK (skipped=2)** — three runs, all green, plus the final
gate run on the iteration-2 content (root OK, driver OK). The reviewer's own independent
rerun in iteration 1 also reported "1,567 offline tests pass" — i.e. the same suite the
gate recorded red was green for the reviewer on the same patch. No T3 output log was
preserved in the bundle (only the last-line verdict, the very truncation
`run-suite.sh`'s Act-note describes), so the failing test cannot be named. The most
plausible cause is environmental: this instance runs `lanes = 2`, and the brief's own
ordering note warns #419 patches the same `leaves.py` and #413 the same
`pdca.toml.jinja` — a lane reconstructed against a base carrying a sibling bundle's
edits to those files is exactly what my exact-phrase doc assertion was brittle to.

**Iteration-2 delta (why this is not the rejected artifact resubmitted unchanged):**
the one assertion that couples the suite to a single case-sensitive wording of a comment
in a contended file — `assertIn("anywhere but LAST", self.text)` — is replaced by an
RC-block-anchored, case-insensitive check (`_rc_comment_blocks`,
`test_remote_control_docs.py:70-89`, applied at `:166-173`): extract the maximal `#`-line
runs mentioning `--remote-control` and require the rationale ingredients ("last", "seed",
"optional") there. It still binds the brief's "say why" (C4's red leg goes red on it —
the pre-fix block lacks them), but rewording or a concurrent edit elsewhere in the file
can no longer turn the shipped suite red. Anchoring to the RC blocks (not the whole
file) keeps it non-vacuous: pdca.toml.jinja's other comments contain those words.

**Reviewer T2 (docs audit not reproducible in reviewer sandbox).** Instance-side gate
script location, not something the patch can change; the T2 gate itself ran green here
(`render_site: link audit OK`, 22 pages).

**Reviewer T3 (is argv-level proof enough — does installed claude honor `--`?).**
Corroborated against the real installed binary, claude **2.1.223**:
- `claude --help` shows `Usage: claude [options] [command] [prompt]` and
  `--remote-control [name]  Start an interactive session … (optionally named)` — the
  optional value that eats the seed is real on this version.
- Discriminating probe pair: `claude -p --version` prints `2.1.223 (Claude Code)`
  instantly (flag parsed); `claude -p -- --version` prints **no version** and proceeds to
  a model turn (timed out offline at 20s) — i.e. `--` terminates option parsing and the
  next token is the prompt positional, on the installed CLI.
The full end-to-end (RC session actually starts AND the REPL opens seeded with
`--remote-control -- <seed>`) is irreducibly interactive — it needs an enrolled device, a
TTY and a human — so it cannot ride the headless suite. Manual validation for sign-off:
  1. In a scratch dir: `claude --remote-control -- "say SEEDED and stop"`.
  2. Expect: RC banner (no "error trying to start remote control"), and the REPL opens
     with the seed as the first user message.
  3. Negative control (the defect): `claude --remote-control "say SEEDED and stop"` —
     RC treats the prompt as the session name; pre-fix behavior per pdca-pdca#19.

**Reviewer T4 (contribution artifacts).** Publish-stage artifacts; not producible at Do.
The T4 gate ran green in iteration 1 and nothing in this iteration touches it.

## Alternatives ruled out, with cost

- **Docs-only fix (no separator).** Closes the trap only for people who read the
  comment; the invariant field says the seed must survive "every argv the template
  sanctions", which placement advice cannot guarantee — an instance appending any future
  optional-value flag last reintroduces the bug with zero warning. The brief names an
  Invariant to restore, so minimal-diff is not the deciding axis; the separator is the
  smallest change that restores it (1 data field + 1 line at the spawn).
- **Unconditional `argv + ["--", seed]` for every family.** Smaller by ~8 lines (no
  profile bit), but injects `--` into codex/gemini/generic spawns whose CLIs are
  unverified — for a TUI like `codex` the stray token could itself become a bogus
  positional. The brief's scope line explicitly ships the bit unset for them.
- **Validating/sanitizing the configured argv (reject flag-last configs at load).**
  Requires a per-family table of which flags take optional values (claude alone has
  dozens; the table goes stale on every CLI release) versus 1 separator line; and it
  turns a recoverable config nuance into a hard load failure.
- **Reproducing the T3 red before rebuilding.** Attempted first (three gate runs, base
  and content pinned); not reproducible, and no log survived to name the failing test.
  Betting the iteration on chasing an unpreserved transient instead of removing the one
  identified brittleness would spend the round producing nothing checkable.

## Forced refutation (a/b/c)

- **(a) Genuine red?** Yes — via the project's C4 runner (`engine/scripts/run-verify.sh`),
  which reverts only the production hunks and re-runs the bundle tests: red leg =
  `test_remote_control_docs` **FAILED (failures=2)** (flag-last example + missing
  rationale) and `test_seed_spill` **FAILED (failures=1, errors=1)**
  (`test_claude_family_separates_seed_from_argv` — no separator in the spawned argv;
  `test_the_separator_is_a_families_profile_bit` — no such profile field). Green leg:
  11/11 (1 skip) + 15/15. `C4 PASS: red without the fix, green with it`.
- **(b) Production path?** Yes — the seed tests call the production `leaves._invoke`
  with production `families.BUILTIN` profiles; only the terminal `subprocess.run` is
  recorded (patching the spawn is the only way to test a REPL spawn headlessly). The
  docs test reads the shipped `pdca.toml.jinja` itself.
- **(c) Fixture includes the fault?** Yes — the claude-family case uses the exact
  field-failure argv with `--remote-control` as the LAST token
  (`test_seed_spill.py:213-222`), and the strict-equality assertion
  (`spawned == argv + ["--", seed]`) proves the flag is still present, still last
  before the separator, and gets nothing to swallow. The docs assertion scans the real
  shipped example, not a curated copy.

## Gate evidence (this content, this base)

- C4: `C4 PASS: red without the fix, green with it`.
- T3: `== T3: root suite OK, driver suite OK` (7 + 1567 tests).
- T2: `render_site: link audit OK` (22 pages).
- Commit-readiness: the target repo configures no pre-commit hooks, no formatter/linter
  (no `.pre-commit-config.yaml`, no core.hooksPath, no lint workflow — CI is
  docs-check/render-check/require-linked-issue); files follow the surrounding style.
- `patch.diff` reverse-applies cleanly against the worktree state (consistency check).
