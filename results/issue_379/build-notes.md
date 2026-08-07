# Build notes — issue 379 / headless-leaf-scratch-ownership

Worktree: `/home/eddie/pdca/pdca-harness.pdca-wt-l1` (detached off the target base;
all citations below are line numbers **after** the patch unless marked "pre-patch").

## What the change is

Five canonical, vendor-neutral role bodies gain one `## Filesystem — the harness owns it,
you don't` section (two paragraphs, 13 added lines each):

| Body | Section at | Roots it states |
|---|---|---|
| `template/agents/reviewer.md.jinja:22-33` | after `## Inputs` (`:15-20`), before `## What you do` (`:35`) | its **cwd** (+ `$PDCA_TARGET` read-only) |
| `template/agents/adversary.md.jinja:37-48` | after `## Inputs` (`:30-35`), before `## Output` (`:50`) | its **cwd** |
| `template/agents/code-review.md.jinja:20-31` | after `## Inputs` (`:13-18`), before `## Output` (`:33`) | its **cwd** |
| `template/agents/plan-reviewer.md.jinja:34-45` | after `## Inputs` (`:28-32`), before `## Output` (`:47`) | its **cwd** |
| `template/agents/builder.md.jinja:43-54` | after the fork `{% endif %}` (`:41`), before "When you reject an alternative on cost" (`:56`) | `$PDCA_WORKTREE` **and** the bundle dir |

Each section states, in this order: (a) *"Write only inside **the roots the harness gives
you**"* followed by that leaf's actual roots; (b) *"Do **not** create files outside those
roots"*, naming `/tmp`, `/var/tmp` and `$HOME` as the invented-scratch cases; (c)
*"Cleanup is **not yours to perform**: the harness disposes of / reclaims those roots …
so no `rm`-style command is ever warranted"*, plus the operational reason (a vendor
sandbox that refuses `rm` rejects the **whole** command it rides on, so the self-clean
costs the validation it was attached to).

Grounding for the ownership claim, read (cited by the brief) and confirmed in the
worktree: `template/src/pdca_harness/leaves.py:1831` (`tempfile.TemporaryDirectory(
prefix="pdca-review-")`), `:2145` (`pdca-advisory-`), `:2437` (`pdca-plan-advisory-`) —
each a context manager, so the sandbox is deleted on leaf exit; `:1290`
(`wt = worktree.ensure(d, cfg)`) plus `:1302`/`:1314` (`PDCA_WORKTREE` in the child env)
and `:1315` (`extra = [profile.grounding_flag, str(d)]` — the **bundle dir** granted as a
second writable root for a sandboxing builder family), with `[driver].sweep_worktrees`
reclaiming the worktree.

Two shapes, not one, precisely because the builder's is different: a blanket "never write
outside your cwd" would be **wrong** for the builder (for a cwd-discovery family its cwd
is the harness root, `leaves.py:1292-1302`; for a sandboxed family its cwd is the worktree
and the bundle dir is outside it, `:1314-1315`), and it must keep writing `patch.diff` / the
test / `build-notes.md` into the bundle.

## Why phrased over "the roots the harness gives you"

The brief's Ordering note: #422 may later add a lane-stable harness-owned cache root. The
sentence enumerates today's roots *as instances of* "the roots the harness gives you", so
#422 adds a root without this text needing a rewrite or a contradiction. Nothing here
names, promises or implies a persistent scratch location — the only concrete paths named
are the ones the leaf must **not** invent (`/tmp`, `/var/tmp`, `$HOME`).

## What I ruled out, with the cost

- **Editing the `.claude/agents/*.md.jinja` wrappers too.** Ruled out: they are
  `frontmatter + {% include %}` of the canonical body (`template/tests/test_role_prompts.py:5-6`),
  so the canonical edit already reaches both vendors; hand-editing a wrapper is exactly
  what `test_role_prompts.py:49-53` exists to forbid. Cost of the wrong path: +5 files,
  ~65 duplicated lines, and a guaranteed sync-test failure.
- **A `[driver]`-side fix instead of prompt text** (e.g. exporting a `PDCA_SCRATCH` env
  var, or pre-creating a scratch dir per leaf). Out of scope by the brief (no `leaves.py`
  / `sweep.py` / `config.py` change), and it would not fix the defect: the observed
  failure is a model that invents scratch *and then feels obliged to delete it*. An extra
  env var the prompt never explains leaves the "who cleans up" question just as unstated.
  Cost sketch: ~1 env-var plumb in `_run_reviewer_sandboxed`/`_run_advisory_sandboxed`/
  `_run_plan_advisory_sandboxed` + a `TemporaryDirectory` per call site + the same prompt
  sentence anyway (≈30 driver lines on top of this patch, none of them removing the cause).
- **One sentence added to `reviewer.md.jinja` only.** This is the brief's own §3.2
  self-test and it fails: `adversary`, `code-review`, `plan-reviewer` and `builder` keep
  the identical silence and the identical failure mode. The test asserts per body with
  `subTest(agent=…)`, so a one-file patch fails 4 of 5 subTests in each of the two tests.
- **Adding it to `sizer` / `splitter`.** Deliberately not: their cwd is the **bundle dir**
  (persistent harness state, `leaves.py:1066` / `:1149`) — a different lifetime that would
  need its own, different statement. Copying the sandbox wording there would be false.
- **Asserting one exact sentence in the test.** Rejected as brittle: any future rewording
  of the prompt would fail the guard for no behavioural reason. The test asserts the
  *properties* instead (see below).

## The test — `template/tests/test_leaf_scratch_discipline.py` (new, 134 lines)

Posture-aware path resolution mirrored from the cited peer callsite
`template/tests/test_remote_control_docs.py:19-24`:
`next(AGENTS / n for n in (f"{agent}.md.jinja", f"{agent}.md") if (AGENTS / n).is_file())`
— so the module runs non-vacuously in the **template checkout** (`.md.jinja`, the posture
C4 uses) *and* in a rendered instance (`.md`, the posture `test_render_and_run.py:77`
drives). It deliberately does **not** copy `test_role_prompts.py`'s `glob("*.md")` shape,
which `skipTest`s itself in the template checkout (`test_role_prompts.py:38-41`) and would
have been a vacuous green in both C4 legs.

Two tests × 5 `subTest(agent=…)`:

1. `test_every_harness_owned_leaf_states_its_writable_roots` — there is a **paragraph**
   (blank-line block, whitespace-normalized) that (i) frames the roots as the harness's to
   give (`GRANTED`), (ii) is about writing (`WRITABLE`), (iii) names *that leaf's* roots
   (`\bcwd\b|\bworking director` for the four sandboxed leaves; `\$PDCA_WORKTREE` **and**
   `\bbundle\b` for the builder), and (iv) forbids creating files outside them (`OUTSIDE`).
2. `test_every_harness_owned_leaf_states_cleanup_is_not_its_job` — a paragraph that says
   the **harness** deletes/disposes/reclaims (`DISPOSES`) *and* that the cleanup is not the
   leaf's / no `rm`-style command is warranted (`NOT_THE_LEAF_S`).

Both also assert the statement is **not** inside a `{% if %}` block
(`inside_a_conditional`, if/endif balance before the paragraph offset) — the brief's
constraint that it must render for every instance (cf. `reviewer.md.jinja:123`'s
`{% if contribution_model == "fork" %}`). All regexes are synonym alternations spanning at
most one sentence (`[^.]{0,N}`), so they bind the property, not my wording.

## Red → green (project runner)

Runner per `docs/INTEGRATION.md` §3 ("offline driver suite"), run inside the worktree:

- **Green, post-fix:** `cd template && PYTHONPATH=src python3 -m unittest
  tests.test_leaf_scratch_discipline -v` → `Ran 2 tests … OK` (2 tests, 10 subTests — not
  `0 tests`, i.e. non-vacuous in the template checkout).
- **Red, pre-fix:** `git stash push -- template/agents` (reverts exactly the five bodies,
  leaves the new test in place) → same command → `FAILED (failures=10)`, i.e. every one of
  the 5 agents × 2 tests, e.g. `builder.md.jinja: no statement of which roots the harness
  gives this leaf to write in — the leaf is left to invent its own filesystem`. Restored
  with `git stash pop`.
- **Whole suite (T3):** `PDCA_WORKTREE=… ./engine/scripts/run-suite.sh` →
  template-repo suite `Ran 7 tests … OK` (this includes `test_render_and_run`, which
  renders the template and runs the generated instance's own suite — so the new test also
  passed in the **rendered** `.md` posture, and `test_role_prompts.py`'s wrapper/canonical
  sync assertion passed there too), offline driver suite `Ran 1470 tests … OK (skipped=2)`.
- **Docs lint (T2):** `python3 docs/publishing/tools/lint_docs.py` → `lint_docs: OK`.

## Gate posture — declared, matches the brief

`PDCA_BUNDLE=… PDCA_WORKTREE=… ./engine/scripts/run-verify.sh` prints
`PDCA-UNVERIFIABLE: no behavioral production change to revert (test-only or docs-only
patch)` and exits **77**, exactly as the brief predicted: `engine/scripts/run-verify.sh:43`
classifies `*.md.jinja` as non-behavioral, so with only `*.md.jinja` + `template/tests/*.py`
touched, `:51-53` finds no production hunk to revert. That is the sanctioned #165 path
(→ SUMMARY §6 NEEDS-HUMAN), and `docs/INTEGRATION.md` §4 independently names changes to
the **agent role prompts** (`template/agents/`) a project-defined human-only item. I did
**not** invent a production edit to manufacture a red leg. The human judges it by reading
the diff plus the unittest command above.

No formatter/pre-commit config exists in the target (`.pre-commit-config.yaml` absent; CI
is `docs-check.yml` / `render-check.yml` / `require-linked-issue.yml`). Both were run:
`lint_docs.py` OK, and `run-suite.sh` covers the render check. Line lengths of the added
lines are ≤ 96 (repo max in `template/tests/` is 121; the added prompt lines are ≤ 92,
matching the surrounding bodies).

## Refutation of my own test (forced, recorded)

- **(a) Genuine red?** Yes — actually reverted, not reasoned about: `git stash push --
  template/agents` and re-ran the same command → `FAILED (failures=10)` (5 agents × 2
  tests), then `git stash pop`. It is red for *every* leaf, which is what makes the
  invariant ("binds every such leaf body, not the one that was caught") the thing under
  test rather than the reviewer alone.
- **(b) Production path?** Yes. The "production" artifact here *is* the prompt text: the
  test reads the same `template/agents/<name>.md.jinja` files the patch edits — the
  canonical bodies the driver inlines for codex and the `.claude/` wrappers `{% include %}`
  for claude (`test_role_prompts.py:5-6`). No copy, no fixture, no mock of the text. And it
  reads them in **both** shipped postures (`.md.jinja` here, `.md` in the rendered instance
  that `test_render_and_run.py:77` runs), so neither leg is a stand-in.
- **(c) Fixture includes the fault?** Yes. `AGENT_ROOTS` enumerates all five failing
  bodies — including `builder`, whose root shape differs and which a "just check cwd"
  fixture would have quietly excluded — and the builder's row demands `$PDCA_WORKTREE`
  *and* `bundle`, so pasting the sandbox paragraph into `builder.md.jinja` would still
  fail. The `inside_a_conditional` assertion likewise keeps a statement hidden behind
  `{% if contribution_model == "fork" %}` from counting as a pass. Nothing is curated out:
  the four bodies that share a shape are each asserted separately rather than as a group.

## Not done, on purpose

No `leaves.py` / `sweep.py` / `config.py` change; no persistent/cached scratch location
named or implied (#422 owns that); no `.claude/agents/` wrapper touched; the reviewer's
independent-re-verification mandate at `template/agents/reviewer.md.jinja:37-38`
(pre-patch `:24-25`) is untouched. No branch pushed, no PR opened.
