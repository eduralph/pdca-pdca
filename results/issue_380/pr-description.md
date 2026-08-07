## Summary
**User impact:** every Claude Code session — in this repo and in every project generated
from the template — ends with two red warnings saying that a permission rule in the
settings file is not matched and has no effect. The rules in question were meant to keep
`.env` files from being written, so anyone reading the settings believed a protection was
in place that the tool never applied.

This PR removes the rules that can never take effect, leaves the `.env` protection that
does work exactly as it is, and adds a test that stops such a rule from coming back.

Reported in [#380](https://github.com/eduralph/pdca-harness/issues/380).

## What to look at
Two shipped settings files — `template/.claude/settings.json` (what generated projects
get) and this repo's own `.claude/settings.json` — plus one new test,
`template/tests/test_settings_permissions.py`.

To see the problem: start any Claude Code session in a project generated from the current
template and read the two red warnings printed at the end. To see it as a test:

```
cd template && PYTHONPATH=src python3 -m unittest tests.test_settings_permissions
```

That fails on today's `main` and passes with this change.

## Root cause
Claude Code resolves file-permission rules only through `Read(path)` and `Edit(path)` —
`Edit` rules already cover every file-editing tool, `Write` included — so a rule written
as `Write(<path>)` is never consulted and the runtime warns about it once per session.
Both shipped settings files carried such rules, added beside the correct `Edit` ones in
`0103877cae660131c81ccda685deeea3aaf6adb9` and never removed since.

## Fix
Delete every file-path rule addressed to a tool the checker cannot match, from both
settings files: `Write(.env)` / `Write(.env.*)` from each `deny` list, and `Write(**)`
from this repo's own `allow` list — a third instance of the same defect, on the grant
side, where `Edit(**)` is what actually grants. Nothing that is genuinely enforced
changes: the `Read(.env)`, `Read(.env.*)`, `Edit(.env)` and `Edit(.env.*)` rows stay
byte-identical, as do the `Bash(...)` rules and the `ask` list. The bare `Write` entry in
the template's `allow` list is a tool-scope rule with no path argument, so it is not
affected and is left alone.

The new test enforces the general rule rather than the three specific rows, and runs in
both postures the suite covers (the template checkout, where it also inspects this repo's
own settings file, and a generated project).

## Verification
- **Claim:** no settings file this repo ships contains a file-path permission rule in a
  form the checker cannot match, in any of its `allow` / `ask` / `deny` lists.
- **Checked:** on `main` (`5e655c2`), `template/.claude/settings.json:53-54` and
  `.claude/settings.json:82-83` hold `Write(.env)` / `Write(.env.*)`, and
  `.claude/settings.json:53` holds `Write(**)`; those five lines are the whole population
  of such rules and all five are removed here.
- **Claim:** the `.env` protection is not weakened by the removal.
- **Checked:** `template/.claude/settings.json:45-52` and `.claude/settings.json:74-81` on
  `main` — the `Read(.env)`, `Read(.env.*)`, `Edit(.env)`, `Edit(.env.*)` rows are
  unchanged by this PR (only the trailing comma on the last of them moves), and
  `test_the_env_protection_is_intact` pins them so a later cleanup cannot quietly drop
  them.
- **Test:** `template/tests/test_settings_permissions.py` — fails pre-fix with five
  failures, one per offending rule, and passes post-fix. It reads the shipped files
  themselves rather than a fixture copy, and derives the file set and rule set from the
  files, so a newly added bad rule is covered without editing the test.
- **Suites:** the template-repo suite (7 tests) and the generated project's suite (1471
  tests) both pass; the former renders the template and runs the generated project's
  tests, so the new test is exercised in that posture too.

Fixes #380
