# Check — advisory code review (issue #508)

Second lens: bugs the patch introduces, plus reuse/simplification. Reviewed
`patch.diff` against the target tree; ran the new test both pre- and post-patch.

## Findings

Nothing that rises to a correctness bug or a missed-reuse opportunity. Specifics
that back that up:

- `template/.claude/commands/handoff.md.jinja:13-16` — the replacement line drops
  the `!` block and asks the model to run the command itself, mirroring the
  `--abandon` line already at `:26` (same shape: bare backtick span, no `!`, no
  quoting gymnastics). I ran the new test both ways to confirm the causal claim:
  on the pre-patch tree it fails with `$CLAUDE_PROJECT_DIR` flagged; on the
  patched tree it passes (`python3 -m unittest template.tests.test_slash_commands`
  — 1 test, OK both times, matching the file's own docstring claim of red→green).
- The relative path `python3 .claude/hooks/handoff_guard.py --check $1` (no
  `CLAUDE_PROJECT_DIR`) works with the guard's own fallback: `handoff_guard.py:38-39`
  resolves the instance root from `__file__` when the env var is unset, and
  interactive leaves are spawned with `cwd=cfg.root` per the brief's citations —
  so the relative call resolves correctly regardless of whether a session's Bash
  tool sees `CLAUDE_PROJECT_DIR`. No new dependency on that variable was introduced.
- `template/tests/test_slash_commands.py` — new file, doesn't duplicate any
  existing lint (checked: no prior `simple_expansion`/shell-expansion check
  anywhere else in the tree). It doesn't literally reuse `test_handoff.py`'s
  `_first` dual-home helper, but it doesn't need to: it enumerates every file
  under `.claude/commands/` by iterdir rather than hardcoding a `.jinja` vs
  rendered filename, so it already runs unchanged in both a template checkout
  and a rendered instance. That's a reasonable, arguably simpler substitute for
  copying `_first`, not a gap.
- Existing pins hold: `test_handoff.py:121-134` (`argument-hint`, "no scan mode",
  `$1`, `handoff_guard.py` named) all still match the new line 13-16 wording;
  `handoff_guard.py:9-10`'s `--check` description doesn't claim anything about a
  `!` block, so it correctly needed no edit, per the brief's own scope note.
- Minor, non-blocking observation: `BANG_BLOCK` in
  `template/tests/test_slash_commands.py:51` only matches a `!` block that is a
  single line ending in a backtick (`^!\`(.*)\`\s*$`). A hypothetical future `!`
  block with trailing text after the closing backtick, or a multi-line form,
  would silently not match and so not be checked. Today there's exactly one
  command file and its shape is what the regex expects, so this isn't a live bug
  — just a limit worth knowing if `/abandon` (#404) or later commands use a
  different `!` block shape.

No reuse/efficiency issue and no correctness bug introduced by this patch.
