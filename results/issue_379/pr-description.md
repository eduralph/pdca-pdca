# PR description

## Summary
**User impact:** during a run, an automated review or build step can quietly waste a
turn — and sometimes leave litter on the machine. Because nothing tells these steps
where they are allowed to work or who tidies up, a careful model invents a scratch
folder of its own somewhere outside its workspace and then tries to delete it again.
Some vendors refuse delete-style commands outright and reject the *entire* command the
cleanup was bundled into, so the actual check that command was performing never runs
and has to be redone. When the model gives up on deleting instead, the folder it
invented is left behind under `/tmp` or `/var/tmp`. It is harmless per run, but it
happens on every affected run.

This PR states the missing fact in the five affected role descriptions: which places
the harness gives each step to write in, that it must not create files anywhere else,
and that clearing those places up afterwards is the harness's job, never the step's.

Reported in [#379](https://github.com/eduralph/pdca-harness/issues/379).

## What to look at
Five prose files and one new test. Each role description gains one short section,
"Filesystem — the harness owns it, you don't", written in two shapes: the four review
steps are told their working directory (with the target source read-only), and the
builder is told its worktree *and* the bundle directory it is granted, because it must
keep writing its results there — a blanket "stay in your working directory" would have
been wrong for it.

Two things are worth a reviewer's eye. First, the wording deliberately says "the roots
the harness gives you" and then lists today's roots as instances, so that if the
harness later hands out another place to write, this text extends rather than
contradicts — and no persistent or cached scratch location is named, promised, or
implied here. Second, the only concrete paths mentioned are the ones a step must *not*
invent (`/tmp`, `/var/tmp`, the home directory).

To see the gap before the change, on `main`:

```
for f in reviewer adversary code-review plan-reviewer builder; do
  grep -ci "scratch\|temp dir\|your cwd\|working directory" template/agents/$f.md.jinja
done
```

prints `0` five times. To exercise the change:

```
cd template && PYTHONPATH=src python3 -m unittest tests.test_leaf_scratch_discipline -v
```

The live symptom is reproducible by running a codex `exec` review step and reading its
`rejected: rm -f style commands are not permitted` line.

## Root cause
The harness owns these working files mechanically but never said so. The reviewer and
advisory steps run with their working directory set to a `tempfile.TemporaryDirectory`
that is deleted when the step exits, and the builder edits a per-cycle worktree the
driver creates and reclaims — yet none of the five role bodies mentions a working
directory, scratch space, or cleanup at all. An unstated rule is an invented one, and
the invention (self-made scratch plus self-cleanup) collides with vendor sandboxes that
ban delete-style commands unconditionally.

## Fix
- One new section in each of `template/agents/reviewer.md.jinja`,
  `adversary.md.jinja`, `code-review.md.jinja`, `plan-reviewer.md.jinja` and
  `builder.md.jinja` (13 lines each), stating in order: the roots the harness gives
  that step to write in; that it must not create files outside them (naming `/tmp`,
  `/var/tmp` and `$HOME` as the invented cases); and that cleanup is not the step's to
  perform, because the harness disposes of those roots — plus the operational reason,
  that a sandbox refusing a delete rejects the whole command it rides on.
- The text goes into the vendor-neutral canonical bodies only. The `.claude/agents/`
  wrappers are frontmatter plus an `{% include %}` of these bodies, so both vendors
  inherit the change and no wrapper is hand-edited. Each section sits outside every
  `{% if %}` block, so it renders for every instance.
- `sizer` and `splitter` are deliberately untouched: their working directory is the
  bundle directory, persistent harness state with a different lifetime that would need
  its own, different statement. Copying the sandbox wording there would be false.
- New test `template/tests/test_leaf_scratch_discipline.py` asserts the *property*
  per body (a writable-roots statement and a no-step-cleanup statement), not one exact
  sentence, so future rewording does not break it for no behavioural reason.

## Verification
- **Claim:** the harness really does own these working files, so a step-run cleanup is
  never needed.
  **Checked:** `template/src/pdca_harness/leaves.py:1831`, `:2145` and `:2437` on
  `main` — `tempfile.TemporaryDirectory(prefix="pdca-review-" / "pdca-advisory-" /
  "pdca-plan-advisory-")` used as context managers, deleted on step exit; `:1290`
  (`wt = worktree.ensure(d, cfg)`) with `[driver].sweep_worktrees` reclaiming the
  worktree, and `:1310-1315` granting the bundle directory as the builder's second
  writable root.
- **Claim:** all five bodies are silent today, so this is a category gap and not a
  one-file slip.
  **Checked:** `template/agents/{reviewer,adversary,code-review,plan-reviewer,
  builder}.md.jinja` on `main` — 0 matches for scratch / temp dir / cwd / working
  directory in each (the `grep` loop above).
- **Claim:** editing only the canonical bodies reaches both vendors, and the wrappers
  stay in sync.
  **Checked:** `template/tests/test_role_prompts.py:5-6` on `main` — the
  `.claude/agents/` files are frontmatter plus `{% include %}` of the `agents/` body;
  that suite's sync assertion still passes after the change.
- **Test:** `template/tests/test_leaf_scratch_discipline.py` — fails pre-fix, passes
  post-fix. With just the five bodies reverted (tests kept), `cd template &&
  PYTHONPATH=src python3 -m unittest tests.test_leaf_scratch_discipline` reports
  `FAILED (failures=10)` — all 5 bodies × 2 tests; with the change, `Ran 2 tests … OK`
  over 10 sub-tests. Path resolution is posture-aware (mirroring
  `template/tests/test_remote_control_docs.py:19-24`), so it runs non-vacuously both in
  this checkout (`.md.jinja`) and in a rendered instance (`.md`) — unlike a
  `glob("*.md")` shape, which would skip here and report a vacuous pass.
- **Full runs:** the offline suite per `CONTRIBUTING.md:26` — `cd template &&
  PYTHONPATH=src python3 -m unittest discover -s tests` → `Ran 1470 tests … OK
  (skipped=2)`; the repo-root suite (`tests.test_render_and_run`,
  `tests.test_update_compat`, `tests.test_render_cli_name`) → `Ran 7 tests … OK`. The
  render check renders the template and runs the generated instance's own suite, so the
  new test also passed there in the rendered `.md` posture, as did the wrapper/canonical
  sync assertion. `python3 docs/publishing/tools/lint_docs.py` → `lint_docs: OK`.
- **Not machine-scorable:** an automated "revert the production change and watch the
  test go red" check has nothing to bite on here, since the change is prose plus its
  test rather than executable behaviour. Nothing was added to the code to manufacture
  one; the revert run above is the red→green evidence, and the wording itself needs a
  human read of the diff.

Fixes #379
