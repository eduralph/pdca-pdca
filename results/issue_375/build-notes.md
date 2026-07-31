# Build notes — issue 375 / cli-name-ci-regate

Target: eduralph/pdca-harness @ main (`2fbd613`); all edits made in
`$PDCA_WORKTREE` (= base `2fbd613` exactly; verified `git rev-parse HEAD` ==
`origin/main`). `patch.diff` verified to apply cleanly on a pristine checkout of
that commit. Line citations below are against origin/main.

## What the change is

The invariant the brief names: **`cli_name` is the single source of the command
name** (`copier.yml:94–97`; `template/pyproject.toml.jinja:16–17`). Every bare
`pdca <subcommand>` invocation in a `template/**/*.jinja` source was replaced
with the established interpolation idiom `{{ cli_name }} <subcommand>` — the
one composition peer the brief cites, `template/pdca.toml.jinja:850`
(`cmd = "{{ cli_name }} contribcheck"`), mirrored at every site. The default
render (`cli_name = "pdca"`) is **byte-identical** to before at every site, so
existing single-instance renders are unchanged (the T3 render/update suites
confirm: 7/7 green, incl. the update-compat merge tests).

Substitution sites (58 occurrences; every one a single-token `pdca` →
`{{ cli_name }}` in front of one of the 13 subcommands, except the two wrapped
sites noted):

- `template/.github/workflows/check-gates.yml.jinja:27` — the functional
  breakage (`run: pdca gates --working-tree`) — and its line-2 comment.
- `template/pdca.toml.jinja:33,45,49,108,132,135,138,147,148,206,209,219,231,234,277,361,370,437,636,704,736,762,810,838,841` (25 comment sites).
- `template/agents/planner.md.jinja:150,153,155,165,169(×2),171,266` — incl. the
  functional `pdca split <id>` / `pdca split <id> --accept` instructions.
- `template/CLAUDE.md.jinja:11(×2),12(×2),13,31,49,52,53`.
- `template/agents/publisher.md.jinja:23,87,93`, plus the two **line-wrapped**
  invocations at `5–6` and `75–76` (`` `pdca\npublish` `` — `pdca` at EOL,
  `publish` at next line's start; found by grepping `pdca\s*$`). These are the
  same invocation shape, merely wrapped, so they fall under the brief's Scope
  ("replace the default-command-name invocations"); I rewrapped so
  `{{ cli_name }} publish` sits on one line. A line-based scan cannot catch
  these (the brief's assertion is line-shaped), so they are fixed at source.
- `template/agents/signoff.md.jinja:66(×2),93`;
  `template/agents/splitter.md.jinja:15,52`;
  `template/.claude/agents/publisher.md.jinja:6` (frontmatter description; the
  other `.claude/agents/*.md.jinja` are `{% include %}` wrappers of the
  canonical bodies — verified, e.g. `template/.claude/agents/planner.md.jinja:12`
  — so fixing `template/agents/*` fixes both renders);
  `template/CONTRIBUTING.md.jinja:24`; `template/docs/INTEGRATION.md.jinja:152`;
  `template/engine/README.md.jinja:24`.

Left alone, per the brief's out-of-scope list: `template/PCDA/**` (non-jinja,
vendored), non-jinja shipped files, and non-invocation-shaped prose
(`template/CLAUDE.md.jinja:11` "`` `pdca` `` advances a result bundle…",
`template/agents/planner.md.jinja:268` "any `` `pdca` `` / driver command").
Survey confirmation: a broadened grep (`pdca[ ]+[a-z-]+` minus the 13
subcommands) over all `.jinja` sources returns nothing — the 13-subcommand
list covers every invocation-shaped site.

## One consequential change beyond the brief's file list — and why it was forced

`template/tests/test_split.py:965,1265,1268` hardcoded the **default** command
name in assertions against the planner role *source* (`_role()` /
`_prompts()` read `agents/planner.md.jinja`, falling back to `agents/planner.md`
— `test_split.py:956–961,1178–1180`). Templating the planner prompt therefore
redded the target's own offline suite (T3: 2 failures —
`test_the_planner_role_names_the_command_and_the_beat`,
`test_the_prompts_name_the_csv_batch_as_the_only_self_scheduling_shape[role]`).
A patch that reds the target's shipped suite is not commit-ready
(CONTRIBUTING.md:27 "Keep the offline suite green"), so I made those three
assertions name-agnostic (`"pdca split"` → `"split <id>"`,
`"pdca flow 500 501"` → `"flow 500 501"`, `"pdca flow <child-ids>"` →
`"flow <child-ids>"`), each with a comment citing #375. This is *more* correct,
not just convenient: `template/tests/` ships into rendered instances, where the
role file spells the invocation with the *instance's* `cli_name` — the
hardcoded default was the same defect class in a non-jinja shipped file.
The `where == "runtime"` legs of those tests still pass unchanged (the runtime
prompt in `template/src/pdca_harness/leaves.py` is non-jinja driver source —
out of this brief's scope; the brief scopes the assertion to jinja-rendered
files, and I did not chase it).

Rejected alternative for keeping the suite green: teach `test_split.py` to
resolve the instance's actual `cli_name` (parse rendered
`pyproject.toml [project.scripts]`, with a fallback for the template checkout
where no rendered pyproject exists) ≈ +12–15 lines and a new test→packaging
coupling, vs. 3 changed assertion lines that keep each test's intent (the role
names the command shape and the beat). Since the brief names an invariant, the
target is the smallest change restoring it — the name-agnostic form is that.

Rejected alternative for the fix itself: patch only
`check-gates.yml.jinja:27` (1-line diff). Ruled out because the brief's
success criterion (b) and the Invariant are stated **over the class**; the
green leg of the shipped test fails until all ~50 sites are templated, and
several are functional under a namespaced render (the planner's
`pdca split <id>` instruction is executed by a leaf, `planner.md.jinja:150`).

## The test

`tests/test_render_cli_name.py` (new, at the target root — runs under this
instance's C4 via `run-verify.sh:57–61` and under T3's `discover -s tests`;
confirmed discovered: T3 log lists
`test_namespaced_cli_name_reaches_every_rendered_command ... ok`). It mirrors
the cited harness (`tests/test_render_and_run.py:33–57`): copytree of the
working tree → throwaway tagged git repo → `run_copy(..., defaults=True,
unsafe=True)` with `cli_name="pdca-nstest"`, incl. the
`skipUnless(HAVE_COPIER, …)` guard (the instance's required doctor row
`copier importable (.venv)` — `pdca.toml:718–720` — keeps that skip from ever
being a vacuous green here).

Assertions map 1:1 to the success criterion:
- (a) rendered `.github/workflows/check-gates.yml` contains
  `pdca-nstest gates --working-tree` and no bare invocation;
- (b) enumerate `template/**/*.jinja` in the **source** tree, map each to its
  rendered path by stripping `.jinja` (per the brief's Scope — never a scan of
  all rendered files), and assert no line matches the bare-invocation pattern.

Pattern-precision (the brief's explicit no-false-positive list):
`(?<![\w{./-])pdca[ \t]+(?:gates|flow|…|queue)\b` — `pdca.toml` (followed by
`.`), `pdca_harness` (`_`), `pdca-harness` / `pdca-nstest gates` (`-`) all
cannot match; a real invocation after a space/backtick/`run: ` does.

Edge cases handled explicitly rather than skipped silently:
- `template/{{ _copier_conf.answers_file }}.jinja` has an interpolated *name*;
  it is mapped to `.copier-answers.yml` (the default copier.yml keeps —
  `copier.yml:55–57`), and any *other* templated filename fails the test
  ("unmapped templated filename") instead of escaping the scan.
- Conditionally excluded renders (`copier.yml:33,49–54` `_exclude`) are
  skipped, but a vacuous pass is barred: the test asserts
  `.github/workflows/check-gates.yml` and `pdca.toml` are in the scanned set.

## Red→green evidence (via the project's own runners, not hand-rolled)

Run through this instance's configured gate commands (`pdca.toml:826,830,835`),
from the instance root with the driver's env (`PDCA_BUNDLE`, `PDCA_WORKTREE`):

- **C4** `./engine/scripts/run-verify.sh` → `C4 PASS: red without the fix,
  green with it`. Green leg: both bundle tests OK. Red leg (script reverts every
  non-test hunk in the worktree, `run-verify.sh:72–75`): the render test failed
  on exactly the defect —
  `'pdca-nstest gates --working-tree' not found in '…run: pdca gates --working-tree…'`.
  Classification fell through to PROD as the brief predicted
  (`run-verify.sh:39–53`): `check-gates.yml.jinja` + `pdca.toml.jinja` are
  PROD; `template/tests/test_split.py` classifies as TESTS, so the red leg kept
  my name-agnostic assertions in place and they stayed green against the
  reverted source (correct: they assert shape, not the fix).
- **T3** `./engine/scripts/run-suite.sh` → exit 0 (template-repo suite 7/7 incl.
  render + update-compat; offline driver suite 1308 tests, OK, skipped=2 —
  pre-existing skips).
- **T2** `./engine/scripts/run-docs-check.sh` → exit 0 (docs lint + site
  render/link audit — relevant since the patch touches many `.md.jinja`).

## Forced self-refutation (a)/(b)/(c)

- **(a) Genuine red?** Yes — proven mechanically twice by the C4 red leg
  (`git apply -R --exclude=tests/*` of this very `patch.diff`): with all
  production hunks reverted the test fails, message quoted above. It went red
  on criterion (a)'s exact line, not on an adjacent proxy.
- **(b) Production path?** Yes — the test renders the **production template
  sources of the tree under test** through the **production render pipeline**
  (copier + this repo's `copier.yml`); the copytree-into-throwaway-git step is
  the target's own established harness (`tests/test_render_and_run.py:37–43`)
  and copies the working tree, which is why the C4 revert was actually
  exercised (the red leg proves the test observes the tree, not a snapshot).
- **(c) Fixture includes the fault?** Yes — the render answer is the
  fault-exhibiting configuration itself (`cli_name="pdca-nstest"`, the
  namespaced shape `copier.yml:92–97` recommends), the scan enumerates every
  jinja source including the failing workflow, and vacuity is barred by the
  `assertIn(".github/workflows/check-gates.yml", scanned)` /
  `assertIn("pdca.toml", scanned)` guards.

## Commit-readiness

The target repo ships no pre-commit/formatter config (checked: no
`.pre-commit-config*`, no root `pyproject.toml`/lint config; CONTRIBUTING.md
requires only DCO sign-off — publish's job — and a green offline suite, which
T3 shows). Test file style matches the sibling suite (same header/docstring
shape, `from __future__ import annotations`, stdlib-only imports plus the
guarded copier import). No external dependency beyond the brief's registered
rows was needed (copier importable ✓, sibling checkout ✓) — no NEEDS-HUMAN
external-dependency marker.

## Note for sign-off (echoing the brief's)

The `template/agents/*.md.jinja` role-prompt edits are the INTEGRATION §4
human-review category the brief flagged; every one is a mechanical
single-token `pdca` → `{{ cli_name }}` substitution (plus the two rewrapped
publisher lines shown in the diff). The `template/tests/test_split.py`
assertion loosening is the only judgment call in this patch — rationale and
the costed alternative above.
