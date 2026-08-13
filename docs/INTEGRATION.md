# Repository integration — pdca-pdca

> What pdca-pdca provides to plug into the generic PDCA cycle (see
> [quality-cycle.md](../PCDA/quality-cycle.md)). This is the project's answer to the
> "which / where / how" questions the generic model deliberately leaves open.
> It does **not** restate the cycle. Conflict rule: generic wins on cycle
> *shape*; this integration wins on *instantiation*.
>
> **This instance is the self-hosting one**: the target project is
> [pdca-harness](https://github.com/eduralph/pdca-harness) itself — the harness
> drives contributions to the template that renders it. The target checkout is
> the sibling `../pdca-harness` (the `[publisher.checkouts]` sibling default);
> a required doctor row verifies it exists.
> Maintained by Act (append changes; don't silently rewrite).

## 1. Tracker integration
- **System / URL:** github — https://github.com/eduralph/pdca-harness/issues
- **Issue-ID format:** `#123`
- **Cross-link form (commit/PR → tracker):** `Fixes #{id}` trailer in the commit
  message and a closing keyword (`Closes #NNN`) in the PR body — the same reference
  satisfies the target's `require-linked-issue` required check.
- **Status → disposition mapping:** GitHub binary open/closed. open → in cycle;
  closed via merged PR → `fixed`; closed unmerged → the close reason is the
  disposition (`wontfix` / `duplicate` / `not-planned` — GitHub's "not planned"
  state), recorded in the closing comment.
- **Per-release field updated on a fix:** the **milestone**. One milestone is open
  per next release (`Milestone X.Y.0`); new issues are filed against it, and it is
  closed when the `vX.Y.0` tag is cut (see the target README §Releases).
- **Comment voice / template:** `templates/tracker-comment.md.tpl`
- **Plan seeding:** `[[plan.source]] type = "github", role = "tracker"` — the
  planner reads the full issue thread via `gh`; no scrape script exists or is needed.

## 2. Branch-target rules
- **Per-area branch map:** everything → `main` of `eduralph/pdca-harness` (single-line
  history; releases are annotated `vX.Y.0` tags, no maintenance branches).
  Changes to **this instance itself** (pdca.toml, engine/, docs/) are ordinary
  pdca-pdca PRs to its own `main`, outside the cycle machinery.
- **Override convention:** the brief's `Repo + branch target` field; disputes in
  the PR review thread.
- **Cross-version cherry-pick rules:** none — one shipping line.
- **Master-vs-maintenance rule:** not applicable; the target README §Releases is
  the normative statement (tags off `main`, one open milestone).

## 3. Reproduction fixtures and runners
- **Canonical fixture path:** the target's own test corpus — `tests/` at the
  target root (template render + `copier update` compatibility; both copy the
  **working tree** into a throwaway tagged repo, so an uncommitted patch in the
  worktree is exercised) and `template/tests/` (the offline driver suite the
  rendered instances ship).
- **Reproduction runner(s) + commands:** a failing unittest in either root:
  - root suites: `python3 -m unittest discover -s tests` (needs copier importable —
    the suites *skip themselves* without it, which is why the doctor row is required);
  - offline driver suite: `cd template && PYTHONPATH=src python3 -m unittest discover -s tests`
    (the command CONTRIBUTING.md names).
- **Verification runner (test suite):** `./engine/scripts/run-verify.sh` (C4
  red→green on the bundle's test, gating) and `./engine/scripts/run-suite.sh`
  (both suites, advisory T3). Hands-on validation: `pdca-pdca try <id>` opens a
  shell in the patched worktree (`[manual_test] cmd = "bash"`).
- **Platform variants:** none — pure-stdlib Python ≥ 3.11 + git; CI runs
  ubuntu-latest.
- **What counts as a successful repro:** a deterministic non-zero unittest exit
  naming the failing test, reproducible from a clean worktree of the target base.

## 4. Conformance ruleset (answers the validation-tooling matrix for this repo)
For each tier: the **written ruleset** it consumes, its **home**, and the
**single-sourced command** the driver and CI both run.

Gating policy (see `engine/README.md`): every tier **advisory**
(`gating = false`) except the per-fix C4 red→green and T4 (which audits this
cycle's own contribution artifacts, so the advisory caveat does not apply).

| Tier | Written ruleset | Home | Single-sourced command | Status |
|---|---|---|---|---|
| T1 structure | `copier.yml` + render-check rationale (no orphan `.jinja`, valid rendered TOML, answers file recorded) | target `tests/test_render_and_run.py` | (asserted inside the T3 run) | [built — via T3] |
| T2 shape | target docs conventions (`docs/publishing/tools/lint_docs.py` docstring: Obsidian syntax, internal links) | `engine/scripts/run-docs-check.sh` → the target's own checkers | `./engine/scripts/run-docs-check.sh` | advisory, bundle |
| T3 runtime | CONTRIBUTING.md "keep the offline suite green" + render-check.yml | `engine/scripts/run-suite.sh` | `./engine/scripts/run-suite.sh` | advisory, bundle |
| T4 contribution | CONTRIBUTING.md (DCO sign-off, one change per PR) + target branch protection (require-linked-issue) + PR-body template | `./scripts/pdca contribcheck` + the target's own CI | `./scripts/pdca contribcheck` | gating, bundle |
| T5 judgment | reviewer contract below | Check reviewer + sign-off | (model) | [built] |

C4 (per-fix correctness, **gating**): `./engine/scripts/run-verify.sh` — red with
the production hunks reverted, green with the patch; no-test / test-only /
docs-only patches exit 77 `PDCA-UNVERIFIABLE` → §6 (issue #165 discipline).
Contract-tested by `engine/tests/test_run_verify.py`.

- **Reviewer family (cross-vendor, ≠ builder):** codex — canonical role body
  `agents/reviewer.md`, inlined for a codex reviewer / resolved via `--agent reviewer` for a
  claude one (`.claude/agents/reviewer.md` renders only when the reviewer family is claude).
  `AGENTS.md` now carries general codex **project context** (STOP discipline, boundaries),
  not the reviewer role.
- **Builder family:** claude — canonical role body `agents/builder.md`; the
  Claude wrapper `.claude/agents/builder.md` (with the ready-mark block enforced by the
  `.claude/hooks/builder_guard.py` PreToolUse hook) is materialized only when the builder
  family is claude. A codex builder runs `codex exec --sandbox workspace-write`, confined to
  the worktree cwd.
- **Interactive family:** claude — the human-in-the-loop leaves (Plan,
  Sign-off, Publish, Act) run a seeded `claude --agent <name>` REPL or a `codex` TUI, chosen
  by `interactive_family`. A codex publisher gets the same `gh` STOP-shim the builder does
  (it has no PreToolUse hook), so it can't `gh pr ready`/`merge`.
- **Role prompts (vendor-neutral source):** each leaf's instructions live once in
  `agents/<name>.md`. Claude leaves also get `.claude/agents/<name>.md` (frontmatter wrapper
  that includes that body, so `--agent` resolves); non-Claude (inline) leaves read the
  `agents/` body directly. Only Claude leaves carry a `.claude/agents/` file.
- **Vendor profiles:** every family-specific behavior (streaming, extra-dir grounding,
  role-prompt injection, STOP-guard mechanism) is data in `pdca_harness.families`,
  overridable via `pdca.toml [families.<name>]` — swapping or adding a vendor is a
  config edit, not a driver change. A non-claude builder gets the STOP discipline
  from the driver's `gh` PATH shim (same `builder_guard.py` rules as the claude hook).
- **Project-defined human-only items** (reviewer emits NEEDS-HUMAN by design):
  - Validation — fitness-to-purpose (always-human, every cycle);
  - any `PDCA-UNVERIFIABLE` C4 (docs-only / test-only bundles — you judge them by reading);
  - changes to the **vendored model spec** (`template/PCDA/quality-cycle/`) or the
    **agent role prompts** (`template/agents/`) — process/prompt judgment no
    deterministic gate can score;
  - template-question changes in `copier.yml` that alter what existing instances
    get on `copier update` (compat judgment beyond what `test_update_compat` covers).

## 5. Upstream-isn't-ahead routine
- **What "upstream" is:** `eduralph/pdca-harness` `main` itself — own-repo model, no
  fork, no divergence to reconcile. "Ahead" can only mean *already fixed on main or
  in flight on a branch/PR*.
- **Search routine + tokenization gotchas:** by affected file path first:
  `git -C ../pdca-harness log --oneline origin/main -- <path>`; then
  `gh search issues --repo eduralph/pdca-harness "<keywords>"` (GitHub tokenizes on
  word boundaries — search bare terms like `worktree`, not `$PDCA_WORKTREE`), and
  scan the open milestone + open PRs (`gh pr list -R eduralph/pdca-harness`).
- **Merged-history check command:**
  `git -C ../pdca-harness fetch origin && git -C ../pdca-harness log --oneline origin/main -n 30 -- <affected paths>`

## 6. Brief and design-proposal templates
- **Brief template:** `templates/brief.md.tpl`
- **Design-proposal template:** `templates/design-proposal.md.tpl` [built] — the
  Plan artifact for the **exception** (major architecture / API / data-model / UX).
  The planner reserves it for changes that warrant a proposal; most work uses the
  brief. Any canonical upstream process (GEPS/RFC) still owns the final document;
  the cycle produces the draft + the Do spec.
- **Required project-specific frontmatter/sections:** none beyond the template;
  a brief touching `copier.yml` or `template/` SHOULD name the render/update
  suites in its verification plan (they are the only executable spec of the
  template contract).

## 7. Bundle and act-log paths
- **Bundle root + ID format:** `results/issue_<id>/`
- **Act log path:** `process/act-log.md`
- **Iterate archive:** a rejected attempt is preserved in `iteration-v<N>/` in the
  bundle (the brief is archived with it on iterate-to-Plan) — fixed by the harness

## 8. Committing and PR conventions
- **Commit-message format:** conventional-commit prefix with optional scope
  (`fix:`, `feat:`, `docs:`, `ci:`, `chore:`, e.g. `fix(split): …`), imperative
  subject ≤ 72 chars, body explaining the why, wrapped at ~74. Every commit carries
  the DCO `Signed-off-by:` trailer (`git commit -s`) and a fix ends with the
  tracker trailer `Fixes #{id}` (`[tracker].issue_trailer`).
- **PR description format:** see `templates/pr-description.md.tpl` (opens with
  `**User impact:**`, then Root cause / Fix / Verified against / Test) — the shape
  `./scripts/pdca contribcheck` (T4) lints. The wrapper — not a bare `pdca-pdca` —
  is what a gate row names: it resolves this checkout's CLI in any install layout
  (venv, source tree, PATH), so the row runs for a reviewer too.
- **Enforcement mechanism:** target branch protection (PR required,
  `require-linked-issue` check, conversation resolution, enforce-admins) + DCO
  expectation from CONTRIBUTING.md + the T4 gate at Check and publish + human review.

## 9. Repo-specific scripts and tooling
List every project-specific script the cycle invokes (role → path + invocation + status).

| Role | Path | Invocation | Status |
|---|---|---|---|
| Tracker scrape / handoff generator | (none — `gh` via `[[plan.source]] role=tracker`) | driver-run at Plan | [built] |
| Conformance gate runners | `engine/scripts/run-docs-check.sh`, `engine/scripts/run-suite.sh` | `pdca-pdca gates <id>` | [built] |
| Repro / verification runners | `engine/scripts/run-verify.sh` (+ `engine/tests/test_run_verify.py`) | `pdca-pdca gates <id>`; tests: `python3 -m unittest discover -s engine/tests` | [built] |
| Driver | `src/pdca_harness/` | `pdca-pdca run <id>` | [built] |
| Act tooling (L4) | `src/pdca_harness/act.py` | `pdca-pdca act index`, `pdca-pdca act log --date <d>` | [built] |
| Gates (single-sourced) | `pdca.toml` `[[gates.checks]]` | `pdca-pdca gates [<id>] [--working-tree]` | [built — C4/T2/T3/T4 wired] |
| Reviewer role prompt | `agents/reviewer.md` (canonical body; inlined for codex, `.claude/agents/reviewer.md` is the Claude packaging) | (model leaf) | [built — contract; wire command mode] |
| Builder role prompt | `agents/builder.md` (canonical body); `.claude/agents/builder.md` (Claude wrapper) + `.claude/hooks/builder_guard.py` | (model leaf) | [built — ready-mark blocked] |

## 10. Maintainer and governance
- **Who reviews:** Eduard Ralph
- **Ready-mark gate:** publish opens **draft** PRs; only the human marks a PR
  ready and merges, after §9 sign-off. The builder/publisher STOP discipline
  (`builder_guard.py` + the `gh` shim) blocks the leaves from doing either; branch
  protection (enforce-admins) binds the human to the same PR + linked-issue path.
- **External-contribution flow differences:** none — external contributors use the
  standard GitHub fork flow with DCO sign-off (CONTRIBUTING.md); the cycle applies
  to this instance's own contributions.
- **MAINTAINERS file:** none — single maintainer; CONTRIBUTING.md names the process.

### Composing with the host's CI / PR governance (issue #67)

PDCA **supplements** your existing PR/issue governance; it does not replace it. Map
the harness onto what your host already enforces:

| Host gate (governance layer) | PDCA equivalent (supplement) | How they compose |
|---|---|---|
| require-linked-issue on PRs | `[tracker].issue_trailer` (`Fixes #{id}`) in the publish commit/PR | The trailer satisfies the host's linked-issue rule; `init from brief` maps onto an issue that already passes it. |
| DCO / append-only-doc / ready-mark policy | builder/publisher STOP-discipline (`builder_guard.py` PreToolUse hook) | The hook is a *backstop* that blocks `gh pr ready` / `gh pr merge` for the leaves; your host policy is the authority. |
| Target CI (render-check, docs-check, require-linked-issue) | `pdca-pdca gates` runs the target's own checkers (T2/T3) at Check | Same implementations, run earlier — Check catches before the PR what the target's CI re-catches at merge. |

Note the self-hosting twist: the **instance's** merge re-gate
(`.github/workflows/check-gates.yml`, `pdca-pdca gates --working-tree`) governs
pdca-pdca's own PRs; the **target's** CI governs the PRs the cycle publishes to
pdca-harness. Both stay green independently.

## 11. Per-repo P-/D-/C-/A- extensions
None today. Add repo-prefixed rules (e.g. `pdca-pdca-C7`) that *tighten
or add to* a generic rule — never weaken one — as running cycles surface them.

## Answering an interactive leaf from another device

The four `interactive = true` leaves — planner, sign-off, publisher, Act — hand the terminal
to a human+model REPL and block there. That means the human has to be at the terminal the
flow runs in, for the whole batch: a `pdca-pdca flow` over several bundles can park on one
sign-off adjudication for hours because nobody is at that machine.

Claude Code's `--remote-control` flag removes the constraint. Add it to an interactive
leaf's `argv` in `pdca.toml` — anywhere but last: the driver appends the seed prompt as a
positional after the argv, and `--remote-control` takes an optional `[name]` value, so as
the final token it would swallow the whole seed as the RC session name (issue #396; the
claude-family spawn also inserts `--` before the seed as a backstop, but no flag with an
optional value should ever sit last). With the flag in place that leaf becomes answerable
from another enrolled device; nothing else changes — `signoff-decision`, the §6 ticks and
the C6 accept-guard all run the same code path, and only the human's location differs.

Enabling Remote Control in your own shell does **not** reach the leaves: each is a separate
`claude` subprocess whose argv comes from `pdca.toml`. That is the whole reason this needs
documenting.

The headless builder and reviewer must not carry the flag — it starts an *interactive*
session, and they have no human to reach.
