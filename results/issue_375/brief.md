# Brief — issue 375 / cli-name-ci-regate

> The Plan artifact (docs 02 §PLAN). Human-authored. Do reads ONLY this file.
> The field labels below are parsed by the driver — keep the `- **Label:** value`
> shape. The success criterion is the load-bearing field: it is the sentence
> Check tests "did this work" against.

- **Slug:** cli-name-ci-regate
- **Defect:** `template/.github/workflows/check-gates.yml.jinja:27` runs the merge
  re-gate as a literal `run: pdca gates --working-tree`, but the console script is
  installed under the copier answer `cli_name` (`template/pyproject.toml.jinja:16–17`,
  `[project.scripts]` → `{{ cli_name }} = "pdca_harness.cli:main"`). `copier.yml:92–97`
  explicitly recommends namespacing `cli_name` when several instances share a machine
  (e.g. "pdca-gramps") — any instance that follows that advice gets a CI re-gate that
  fails command-not-found on every PR, and the failure presents as a broken CI runner,
  not a render bug. Hit live by the self-hosting pdca-pdca instance
  (eduralph/pdca-harness → eduralph/pdca-pdca#1; its rendered workflow had to be
  hand-patched to `pdca-pdca gates --working-tree`). The same class — a `.jinja`
  source quoting the default command name literally — exists at ~50 more sites across
  ~10 other `.jinja` files (survey on origin/main: `template/pdca.toml.jinja` ×25
  comment sites, `template/agents/planner.md.jinja` ×7, `template/CLAUDE.md.jinja` ×7,
  `template/agents/publisher.md.jinja` ×3, `template/agents/splitter.md.jinja` ×2,
  `template/agents/signoff.md.jinja` ×2, `template/.claude/agents/publisher.md.jinja`,
  `template/CONTRIBUTING.md.jinja:24`, `template/docs/INTEGRATION.md.jinja`,
  `template/engine/README.md.jinja`, plus `check-gates.yml.jinja:2`). Several of those
  are instructions a model leaf or operator executes (the planner prompt says to run
  `pdca split <id>`), so they are functional under a namespaced render, not just prose.
- **Success criterion:** rendered with a namespaced `cli_name` (e.g. `pdca-nstest`):
  (a) the rendered `.github/workflows/check-gates.yml` invokes
  `pdca-nstest gates --working-tree` (no bare `pdca` invocation remains in it), and
  (b) a new render-check test renders the template with that namespaced answer and
  asserts that **no file rendered from a `template/**/*.jinja` source** still carries a
  bare `pdca <subcommand>` invocation (subcommands: gates, flow, run, status, signoff,
  publish, doctor, contribcheck, split, try, act, sweep, queue) — so the class stays
  caught. The default render (`cli_name = "pdca"`) keeps the docs' examples literal
  (the interpolation renders back to `pdca`), so existing single-instance renders are
  unchanged. Demonstrable by C4-verify in isolation (red leg below); the T3
  render/update suites are supplementary evidence only.
- **Falsifiability:** goes RED on this instance's C4 gate (`engine/scripts/run-verify.sh`):
  the red leg reverts every non-test hunk in `$PDCA_WORKTREE` (the `.jinja` templating
  edits included — `--exclude=tests/*` keeps only the test), the kept test re-renders
  the reverted working tree (the render suites copytree the WORKING TREE, so the revert
  is exercised) with `cli_name = "pdca-nstest"`, and finds `run: pdca gates
  --working-tree` in the rendered workflow → assertion fails → red. Green leg: full
  patch applied → no bare invocation in any jinja-rendered file → green. Environment:
  this instance's venv has copier (required doctor row `copier importable (.venv)`), so
  the render test cannot self-skip into a vacuous green. Classification check
  (run-verify.sh:39–53): `template/.github/workflows/check-gates.yml.jinja` and
  `template/pdca.toml.jinja` fall through to PROD (they match neither the bare
  `.github/*` nor the `*.md.jinja` non-behavioral patterns), so the patch is never
  misfiled as docs-only/UNVERIFIABLE.
- **Invariant to restore:** every rendered file references the instance's configured
  console-script name — `cli_name` is the single source of the command name
  (`copier.yml:94–97`; `template/pyproject.toml.jinja:16–17` `[project.scripts]`;
  `template/Makefile:9–10` "named per pyproject [project.scripts] — the cli_name copier
  answer"); the literal `pdca` is merely the default answer's rendering of it, never a
  hardcoded fact about the render. Stated over the class (all jinja-rendered command
  references), not the one workflow line. (Non-structural behavioural render bug —
  principles.md §1.1; the Plan-exit structural gate does not apply.)
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Ordering note:** independent of issue 376 in this batch — disjoint file sets (376
  edits `template/scripts/bootstrap-tools.sh` + `template/tests/test_bootstrap.py`;
  this bundle edits `.jinja` sources + a new `tests/` file). No `Depends on` /
  `Conflicts with`; both may run in the same wave.
- **Surfaces:** data
- **Difficulty:** medium
- **Scope:** replace the default-command-name **invocations** in `template/**/*.jinja`
  sources with `{{ cli_name }}` — the functional breakage is
  `check-gates.yml.jinja:27` (and its line-2 comment); the remaining sites listed in
  Defect are the same class and are exactly what the new render assertion enforces
  (the green leg fails until all are templated) — and ship the render-check regression
  test. The assertion must scope to files rendered from `.jinja` sources: enumerate
  `template/**/*.jinja` in the source tree and map each to its rendered path
  (strip the `.jinja` suffix) — do NOT scan all rendered files. The invocation pattern
  must not false-positive on `pdca.toml`, `pdca_harness`, `pdca-harness`, or the
  namespaced name itself (`pdca-nstest gates` is a pass). / out of scope: the
  verbatim-vendored model spec (`template/PCDA/**` — non-jinja, ships as-is; there
  `pdca` names the generic driver concept, and editing it is an INTEGRATION §4
  human-judgment category), non-jinja shipped files (`template/scripts/bootstrap-tools.sh`,
  `template/Makefile` — already name-agnostic, verified no bare invocations), and
  bare-`pdca` prose that is not invocation-shaped (e.g. "every `pdca` command" — the
  assertion does not cover it; do not chase it).
- **Repro instruction:** on the target checkout at origin/main:
  `git -C ../pdca-harness show origin/main:template/.github/workflows/check-gates.yml.jinja | sed -n 27p`
  → `        run: pdca gates --working-tree` (no `{{ cli_name }}`). End-to-end: render
  the template with `data={"project_name": "X", "tracker_url": "https://x/issues",
  "cli_name": "pdca-nstest"}, defaults=True, unsafe=True` (mirror
  `tests/test_render_and_run.py:45–52`), then grep the rendered
  `.github/workflows/check-gates.yml` for `run: pdca ` — present. The rendered
  instance's CI then fails command-not-found on every PR (as eduralph/pdca-pdca#1 did;
  that instance's workflow line 27 is hand-patched to `pdca-pdca gates` today).
- **External dependencies:** `copier importable (.venv)` (registered required
  [[doctor.checks]] row — without it the render suites skip themselves and the test
  can never go red); `sibling checkout ../pdca-harness` (registered required row — the
  target checkout every gate runs against). Base toolchain (git, python3) excluded.
- **Test file:** `tests/test_render_cli_name.py` — a NEW file at the target root
  (`../pdca-harness/tests/`). It runs under this instance's C4
  (`run-verify.sh:57–61` maps `tests/*.py` → `python -m unittest
  tests.test_render_cli_name` from the worktree root with the instance venv's python)
  and under T3's `discover -s tests`. A new file also earns its red under either C4
  classification variant (this instance's revert-production contract keeps it in
  place; an added-test-file classifier would see it as added). Mirror
  `tests/test_render_and_run.py`'s render harness (tagged git copy → `run_copy`),
  including the `skipUnless(HAVE_COPIER, …)` guard.
- **Citations expected:** Do must cite path:line on origin/main of
  eduralph/pdca-harness for every change. Composition peers Do MAY open:
  `template/pdca.toml.jinja:850` — `cmd = "{{ cli_name }} contribcheck"` — the
  established interpolation idiom for a command invocation in a rendered file (mirror
  it at every site); `tests/test_render_and_run.py:33–57` — the render-harness shape
  (throwaway tagged git copy of the working tree, `run_copy(..., data=…,
  defaults=True, unsafe=True)`, assertions on rendered output) the new test mirrors.
- **Prior-art check (triage cycles):** searched by file path on 2026-07-31:
  `git -C ../pdca-harness log origin/main -- template/.github/workflows/check-gates.yml.jinja`
  → a single commit (36e72c9, the file's introduction — the bug has been present since);
  `cli_name` was introduced in 8990877 (#73) without touching the workflow. Open PRs:
  only #378 (workspace chore, unrelated); remote branches `docs/373-relative-src-path`
  unrelated. `git grep cli_name origin/main -- tests/` → empty: no render test exercises
  a non-default `cli_name` anywhere, which is why the render suite never caught this.
  Issue #375 OPEN, no linked fix. Nothing merged, in flight, or rejected on this path.
- **Disposition hint:** likely-fix

## Note for sign-off

The class cleanup touches `template/agents/*.md.jinja` role prompts — an INTEGRATION
§4 human-review category, so expect the reviewer to route a NEEDS-HUMAN item for it.
The edits there are mechanical single-token substitutions (`pdca split` →
`{{ cli_name }} split` etc.); judge them as such.

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.
