# Build notes — issue 494 (admit interactive leaves to the checkout they are told to read)

Target: `eduralph/pdca-harness` @ `main`, base `acb214a`. All `path:line` citations below are
**post-patch** line numbers in the worktree (`$PDCA_WORKTREE=/home/eddie/pdca/pdca-harness.pdca-wt-l0`)
unless marked "(base)".

## What changed

One new production block plus six one-kwarg call-site changes in
`template/src/pdca_harness/leaves.py`:

| Where | Line (post-patch) | Change |
|---|---|---|
| new section | `leaves.py:734-838` | `_primary_checkout` / `_known_targets` / `_admission_set` / `_workspace_grant` |
| `do_plan` | `leaves.py:895` | `extra_argv=_workspace_grant([d], cfg, cfg.profile(cfg.planner))` |
| `do_plan_batch` | `leaves.py:1080`, `:1088` | hoist `seeded`; `extra_argv=_workspace_grant(seeded, …)` |
| `run_signoff` | `leaves.py:3380` | `extra_argv=_workspace_grant([d], cfg, cfg.profile(cfg.signoff))` |
| `run_signoff_batch` | `leaves.py:3431-3432` | `extra_argv=_workspace_grant(list(bundles), …)` |
| `run_act` | `leaves.py:3528` | `extra_argv=_workspace_grant(covered, cfg, cfg.profile(cfg.act))` |
| `run_publish` | `leaves.py:3597` | `extra_argv=_workspace_grant([d], cfg, profile)` |

Base positions of the same six spawns (for review against `acb214a`): `:781-783`, `:971-972`,
`:3260-3261`, `:3307-3309`, `:3399-3401`, `:3463-3466`.

New test module: `template/tests/test_leaf_workspace_admission.py` (323 lines, 12 cases).
Patch total: 462 insertions / 8 deletions across 2 files.

## Why this shape

**It is a composition, not an invention.** Both halves already exist in the tree and are
mirrored rather than re-derived:

* the *grant* shape is the reviewer's — resolve a directory, then pass
  `[profile.grounding_flag, str(dir)]` **only when the profile has a flag**
  (`leaves.py:2495-2500` base = `:2611-2616` post-patch). `_workspace_grant` is that
  conditional, generalised (`leaves.py:825-838`).
* the *resolution* is `_plan_fallback_target`'s — `publish._resolve_target` →
  `publish._checkout_path`, guarded (`leaves.py:3039-3045` base = `:3155-3161` post-patch).
  `_primary_checkout` (`leaves.py:756-782`) is that resolution with an `is_dir()` restriction
  instead of a `.git` one (criterion (i) says "directories that exist on disk"; a non-git
  target checkout is still a directory the leaf is told to read).

**cwd is not the mechanism.** A claude-family CLI discovers `.claude/agents` and its
PreToolUse hooks by walking up from cwd, so cwd must stay `cfg.root` — the reason `do_build`
grounds its builder by flag instead of by cwd (`leaves.py:1793-1802` base = `:1909-1918`
post-patch, `#136`). Every one of the six keeps `cfg.root`; the test asserts it
(`test_leaf_workspace_admission.py:184`, `:192`, `:228`, and the all-six loop at `:316`).

**Why `extra_argv` and not a settings file.** A grant that lives in the operator's
`.claude/settings.local.json` is untracked (`.gitignore:19`), so a lane worktree never
materialises it, and `--setting-sources project` (`families.py:100-102`) drops user *and*
local scope by design. `template/.claude/settings.json` is tracked and static — it cannot
carry an instance-specific absolute path — and is out of scope (issue 508 owns it). The
spawn's argv is the only durable channel, and it is the one the headless half already uses.

## The three Plan decisions, as implemented

1. **All six sites.** `do_plan` `:895`, `do_plan_batch` `:1088`, `run_signoff` `:3380`,
   `run_signoff_batch` `:3431`, `run_act` `:3528`, `run_publish` `:3597`. `run_act` is in.
   `_ALL_SIX` in the test module pins the set, and three cases drive all six in one
   instance (`_drive_all_six`, `test_leaf_workspace_admission.py:161-173`).
2. **Never a lane worktree.** `_primary_checkout` does not import `worktree` at all — the
   only two path sources are `publish._checkout_path` (a `[publisher.checkouts]` mapping, or
   the `<root>/../<repo>` sibling convention, `publish.py:579-587`) and nothing else. So
   `worktree.path()`'s serial answer — the unsuffixed `<name>.pdca-wt`, `worktree.py:107-112`
   + `lane.py:26-28` — is unreachable by construction, not filtered after the fact. The test
   makes the trap live before asserting the negative: it creates a real `repo.pdca-wt` git
   dir and asserts `worktree.path(probe, cfg) == wt` first
   (`test_leaf_workspace_admission.py:267-274`), then that no spawn admits any
   `WT_SUFFIX` path (`:275-280`). No `git fetch` either — `_reviewer_target:1996-1999`
   fetches the human's own checkout for a freshness these leaves do not need.
3. **Empty ⇒ the instance's known targets.** `_admission_set` (`leaves.py:813-822`) returns
   `dirs or _known_targets(cfg)`; `_known_targets` (`:784-810`) is `[publisher.checkouts]`
   (through the same `_checkout_path`, so a relative entry resolves as publish resolves it)
   ∪ the distinct primaries the instance's existing briefs resolve to, active
   (`results/issue_*`) and archived (`results/completed/issue_*`, the convention
   `config.py:496-512` names). Deduped, existence-restricted, config first then briefs in
   name order — deterministic.

## Alternatives considered and rejected

* **Reuse `_reviewer_target` (the previous attempt's `_target_grant`).** Rejected on
  correctness, not cost: it prefers `worktree.path()` (`leaves.py:1985-1987`), and the
  interactive leaves run serially, so it returns `<primary>.pdca-wt`. On this host that
  directory exists right now at `645c315`, one commit behind `main`, with **no `.owner`
  marker** — every interactive session would have been admitted to a stale unowned tree
  instead of the checkout the human has open. It also `git fetch`es that checkout on every
  spawn.
* **A defensive `WT_SUFFIX` filter in `_admission_set`.** Concretely 2 lines
  (`if worktree.WT_SUFFIX in p.name: continue` plus the import). Rejected because it is dead
  by construction (see decision 2 — no code path reaches `worktree`), and because the one
  input it *could* touch is a deliberate `[publisher.checkouts]` mapping, which criterion (ii)
  says to admit ("the paths `[publisher.checkouts]` names"). A filter there would silently
  drop an operator's own configuration. The property is asserted instead, which is where it
  belongs.
* **Grant centrally inside `_invoke`.** Rejected on correctness: `_invoke` has no bundle
  context, and the headless leaves deliberately grant *narrower* sets — the reviewer's grant
  is conditional on `repo is None` precisely so a sandboxed read+**write** family is not
  handed the shared lane worktree (`leaves.py:2495-2500` base). A central grant would undo
  that refusal for every headless leaf; the brief also puts them out of scope.
* **Confine the interactive leaves by cwd instead.** Rejected: it breaks agent/hook discovery
  for the claude family (`leaves.py:1793-1802`, `#136`) — the exact reason `do_build` uses the
  flag.
* **Scan only active bundles (skip `completed/`) in `_known_targets`.** Rejected as a
  false economy: criterion (ii) says "the instance's existing briefs", and an archived brief
  is one. Measured cost of the full scan in this instance (55 active bundles, 0 archived, 54
  briefs): **5.0 ms** for every brief parsed via `brief.repo_target` — and it runs only on the
  fallback path (a Plan spawn), once per session, against a session that then waits on a human.

## Round-8 caveat: why exposing the primary checkout is right *here*

`_plan_fallback_target`'s docstring (`leaves.py:3033-3035` base) refuses to hand the
operator's primary checkout to its leaf, because the grounding flag is read/**write** for
codex and that leaf is *sandboxed, unattended and headless* — a stray command could mutate
uncommitted work with nobody watching. That caveat does not transfer to these six:

* they are **interactive** — they run in the human's own terminal, seeded, with the human
  present for every tool call;
* the deterministic half of publish **already** runs `git -C <primary> fetch/checkout/apply/
  commit/push` against that very tree (`publish.py:439-448`), under the same human;
* the publisher and sign-off prompts *instruct* the model to read it
  (`publisher.md.jinja:65-66`, `planner.md.jinja:72-75`/`:214-215`, `_plan_prompt`'s
  citation line).

The primary checkout **is** the interactive band's working surface. Refusing to admit it
does not protect anything — it only moves the same access behind a per-session approval
prompt that cannot be made to stick.

## Refutation of my own test (forced)

**(a) Genuine red?** Yes — proven by the project's own C4 runner, not by hand:
`PDCA_BUNDLE=… PDCA_WORKTREE=… ./engine/scripts/run-verify.sh` → exit 0,
`PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`. Green leg: `Ran 12 tests … OK`.
Red leg (production hunks reverted, `--exclude=tests/* --exclude=template/tests/*`):
`Ran 12 tests … FAILED (failures=9)` — 12 ran, so no `unittest.loader._FailedTest`, no
`PDCA-UNVERIFIABLE`. The 9 red cases cover **all six spawn sites** plus (iii) and (iv):
`test_plan_admits_the_instances_known_targets`, `test_plan_batch_admits_the_instances_known_targets`,
`test_signoff_admits_the_bundles_own_checkout`, `test_signoff_batch_admits_each_targets_checkout_once`,
`test_act_admits_the_reviewed_bundles_checkouts_once`, `test_publish_admits_the_bundles_own_checkout`,
`test_an_archived_brief_still_names_a_known_target`, `test_no_spawn_admits_a_lane_worktree`,
`test_no_spawn_admits_a_directory_nobody_named`. The remaining 3 assert an **absence**
(`generic` family, an unknown instance, an off-disk target) and are correctly vacuous pre-fix —
they are the guards that stop a too-wide fix, not the red.

**(b) Production path?** Yes. The test imports `pdca_harness.leaves` and calls the real
`leaves.do_plan`, `do_plan_batch`, `run_signoff`, `run_signoff_batch`, `run_act`,
`run_publish`. The single stub is `leaves._invoke` — the process spawner, i.e. exactly the
boundary the criterion is stated over ("the argv the driver produces"), and the same seam
`test_do_confine.py:90-92` and `test_leaf_resilience.py` already use. Everything between the
entry point and that seam runs unmodified production code: `_workspace_grant` →
`_admission_set` → `_primary_checkout` → `publish._resolve_target` → `brief.repo_target` →
`publish._checkout_path`, plus `handoff.session`, `act.frozen_bundles`/`act_due`/
`mark_reviewed`, `state.state`. No collaborator is monkeypatched (the earlier attempt
substituted `act_mod.frozen_bundles`; this module builds genuinely COMPLETE bundles instead
— `_frozen`, `test_leaf_workspace_admission.py:124-131` — so `act.frozen_bundles` selects
them for real).

**(c) Fixture includes the fault?** Yes, twice over, and both are asserted to be live rather
than assumed:

* the lane-worktree negative creates a **real** `repo.pdca-wt` git directory and asserts
  `worktree.path(probe, cfg) == wt` **before** asserting no spawn admits it — the rejected
  resolver would have returned that exact path;
* the "nothing wider" negative creates a real third checkout (`unrelated`) **in the very
  directory the sibling convention searches** (`cfg.root.parent`), so it is reachable, not
  curated out, and asserts the admitted set is a subset of `{target, other}` plus explicit
  `assertNotIn` for `unrelated` and for the parent directory holding them all.

## Other verification run

* Whole target suite via the instance's T3 gate command
  (`PDCA_WORKTREE=… ./engine/scripts/run-suite.sh`): root suite `Ran 7 tests … OK`
  (copier render + update-compat both really ran, not skipped), driver suite
  `Ran 1770 tests … OK (skipped=2)`.
* `git diff --check` clean. `template/src/pdca_harness/leaves.py` is copied verbatim by copier
  (`copier.yml:14`, `_templates_suffix: .jinja`), so no Jinja escaping applies.
* Commit hooks: the target repo ships no formatter/linter config (no `pyproject.toml`,
  `ruff.toml`, `.flake8`, `.pre-commit-config.yaml`); its commit requirements are the DCO
  sign-off (`CONTRIBUTING.md:7-20`) and a conventional-prefix subject (`AGENTS.md:26-27`),
  both of which belong to the publish commit, not the patch. CI is render-check + docs-check
  (`.github/workflows/`), and this patch touches no docs and no `*.jinja`. Line lengths in the
  new code stay ≤ 92 (file max on base is 110).
* Test module stdout is empty (`python3 -m unittest … 2>/dev/null` prints nothing) — the
  house hygiene convention of `#402`; production chatter is captured by the module's own
  `_quiet()` helper.

## External dependencies

None beyond the base toolchain (stdlib Python 3.11+ and `git`, both already required). No
vendor CLI, no network, no live service was needed to build or to exercise this — the brief's
`External dependencies: none` held.

## What no gate can observe (for §6, not a claim of proof)

That Claude Code *stops asking the human* is a vendor-CLI prompting behaviour; the harness
controls only the argv, which is what the criterion is stated over and what the test asserts.
The supplementary human check is direct and available this cycle: this bundle's own sign-off
and publish sessions read `../pdca-harness`, so with the patch in place the human should see
no approval prompt for it. `pdca-pdca try 494` gives a patched worktree to check in.
