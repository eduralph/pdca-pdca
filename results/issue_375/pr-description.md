## Summary

**User impact:** Projects that install this toolkit under their own command name —
exactly what the setup questionnaire recommends when more than one instance shares
a machine — get a broken CI: the automated check guarding every pull request fails
with "command not found", every time, and it looks like the CI runner is at fault
rather than the generated configuration. Instructions in the generated docs and
agent prompts quote the same wrong command, so following them fails too.

This PR makes every generated file use the command name the project actually
chose, and adds a regression test so no generated command can regress to the
default name.

Reported in [#375](https://github.com/eduralph/pdca-harness/issues/375).

## What to look at

The generated CI workflow is the load-bearing change: its gate step now runs the
project's configured command instead of the literal default. The remaining edits
are the same one-token substitution across the generated configuration comments,
docs, and agent prompts, plus one new test. To see the bug and the fix: render the
template with a namespaced command name (for example `pdca-nstest`) and look at
the gate step of the generated CI workflow — before this change it still invokes
`pdca`; after it, `pdca-nstest`. One judgment call is flagged in Fix below (three
loosened assertions in a shipped test file).

## Root cause

The console script is installed under the copier answer `cli_name`
(`template/pyproject.toml.jinja:16–17`, `[project.scripts]`), and
`copier.yml:92–97` explicitly recommends namespacing it — but
`template/.github/workflows/check-gates.yml.jinja:27` ran the merge re-gate as the
literal `run: pdca gates --working-tree`, and the same literal default appeared at
57 more sites across 11 `.jinja` sources, several of them instructions an agent or
operator executes. No render test exercised a non-default `cli_name`
(`git grep cli_name origin/main -- tests/` is empty), so nothing caught the class.

## Fix

Every bare `pdca <subcommand>` invocation in a `template/**/*.jinja` source now
renders through `{{ cli_name }}`, mirroring the established idiom at
`template/pdca.toml.jinja:850` (`cmd = "{{ cli_name }} contribcheck"`) — 58 sites
across 11 files; two line-wrapped invocations in
`template/agents/publisher.md.jinja` (lines 5–6 and 75–76) were rewrapped so the
interpolation sits on one line. The default render (`cli_name = "pdca"`) is
byte-identical to before, so existing single-instance renders are unchanged.
Deliberately untouched: the non-jinja vendored spec under `template/PCDA/` and
prose mentions of `pdca` that are not command invocations.

One change beyond the `.jinja` sources:
`template/tests/test_split.py:965,1265,1268` asserted the literal default name
against the role-prompt source, which now spells `{{ cli_name }} split` — those
three assertions are now name-agnostic (`"pdca split"` → `"split <id>"`, etc.,
each commented with #375). This is the same defect class in a shipped non-jinja
file: that suite ships into rendered instances, where the prompt spells the
instance's own command name.

## Verification

- **Claim:** rendered with a namespaced answer (`cli_name = "pdca-nstest"`), the
  generated `.github/workflows/check-gates.yml` invokes
  `pdca-nstest gates --working-tree`, and no file rendered from a
  `template/**/*.jinja` source carries a bare `pdca <subcommand>` invocation; the
  default render is unchanged.
- **Checked:** on `main` (base 2fbd61357be6fecf250341a69bd1c2296f90c92b):
  `template/.github/workflows/check-gates.yml.jinja:27` — the literal invocation
  (the defect); `template/pyproject.toml.jinja:16–17` — the console script
  installs under `cli_name`; `copier.yml:92–97` — namespacing is the recommended
  configuration; `template/pdca.toml.jinja:850` — the interpolation idiom mirrored
  at every site.
- **Test:** `tests/test_render_cli_name.py` (new) — renders the tree with the
  namespaced answer via the same harness as `tests/test_render_and_run.py:33–57`,
  then scans exactly the files rendered from `.jinja` sources. Pre-fix it fails on
  the defect itself (`'pdca-nstest gates --working-tree' not found in '…run: pdca
  gates --working-tree…'`); post-fix it passes. It guards against a vacuous pass
  (asserts the CI workflow and `pdca.toml` are in the scanned set), skips cleanly
  where copier is not importable, and its pattern does not false-positive on
  `pdca.toml`, `pdca_harness`, `pdca-harness`, or the namespaced name itself.
- **Suites:** the template render + `copier update` compatibility suites pass
  unchanged (7/7), and the offline driver suite passes (1308 tests) — consistent
  with the default render being byte-identical.

Fixes #375
