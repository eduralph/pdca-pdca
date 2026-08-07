# Brief — issue 379 / headless-leaf-scratch-ownership

> The Plan artifact (docs 02 §PLAN). Do reads ONLY this file.

- **Slug:** headless-leaf-scratch-ownership
- **Defect:** no headless leaf's role body says who owns its filesystem, so the model invents
  an answer and the answer is wrong. Verified: `template/agents/reviewer.md.jinja` (130 lines),
  `adversary.md.jinja`, `code-review.md.jinja`, `plan-reviewer.md.jinja` and `builder.md.jinja`
  contain **zero** occurrences of "scratch" / "cwd" / "working directory" / "temp dir". The
  harness meanwhile owns that lifecycle mechanically: the reviewer's cwd is a
  `tempfile.TemporaryDirectory(prefix="pdca-review-")` deleted when the leaf exits
  (`template/src/pdca_harness/leaves.py:1831`), the advisory reviewers get the identical shape
  (`:2145` `pdca-advisory-`, `:2437` `pdca-plan-advisory-`), and the builder edits the
  per-cycle worktree the harness creates and reclaims (`:1290` `worktree.ensure`, plus
  `[driver].sweep_worktrees`). Left unstated, a conscientious model creates scratch **outside**
  its cwd and then feels obliged to delete it. Observed on a live `pdca flow` Check with a
  codex `exec` reviewer: it composed one compound self-validation script ending in an
  `rm -rf` of a scratch dir it had made for itself under `/var/tmp/pdca/pdca-reviewer-<id>-*`
  (case-guarded to its own path), and codex's command policy refused the **whole** script
  before executing any of it — `rejected: rm -f style commands are not permitted. Use a safer
  approach`. Per run it is benign (nothing half-executed, the leaf continued), but it is
  systematic: codex `exec` bans rm-style commands unconditionally in this mode, so **every**
  codex reviewer cycle that self-cleans pays a wasted model round-trip — and may loop hunting a
  "safer approach" — while the invented scratch leaks into `/var/tmp` when the model gives up.
- **Success criterion:** every headless leaf role body whose working files the harness creates
  and disposes states that ownership, in the vendor-neutral canonical source under
  `template/agents/` (inlined for codex, wrapped for claude, so every vendor inherits it).
  Concretely, for each of the five bodies named in Scope the rendered text must say (a) which
  roots the leaf may write in — for a sandboxed reviewer/advisory leaf, its cwd; for the
  builder, `$PDCA_WORKTREE` **and** the bundle dir it is granted (it must keep writing
  `patch.diff` / the test / `build-notes.md` there, so a blanket "never write outside your cwd"
  would be wrong for it); (b) that it must not create files outside those roots; and (c) that
  cleanup is **not the leaf's to perform** — the harness disposes of them — so no rm-style
  command is ever warranted. The statement is phrased over **"the roots the harness gives
  you"**, not "your cwd", so a future harness-provided root (#422) is covered without
  rewording. `test_role_prompts.py`'s wrapper/canonical sync assertion still passes.
- **Falsifiability:** RED on the base toolchain, no services and no network, on the target
  checkout Do is given. `cd template && PYTHONPATH=src python3 -m unittest
  tests.test_leaf_scratch_discipline` fails on `origin/main`, because all five bodies are
  silent (verified: 0 matches for scratch/cwd/working-directory in each), and passes with the
  patch. **The test must not skip in the template checkout** — see `Test file`; a skip here is
  a vacuous green in *both* C4 legs. The runtime symptom (a codex `exec` reviewer's compound
  script rejected at spawn) is reproducible by running a codex reviewer leaf and reading its
  `rejected: rm -f style commands are not permitted` line, but it is model-behavioural and not
  automatable at Check — the text assertion above is the binding criterion.
  **Gate posture — declared, not a gap:** the patch is five `*.md.jinja` bodies plus one
  `template/tests/*.py`, and `engine/scripts/run-verify.sh:43` classifies `*.md.jinja` as
  non-behavioral ("incl. the template's .md.jinja role prompts"), so `:51-53` finds no
  production hunk to revert and C4-verify exits 77 `PDCA-UNVERIFIABLE` → SUMMARY §6
  NEEDS-HUMAN rather than a false red. That is the sanctioned path here twice over: issue #165
  discipline, and `docs/INTEGRATION.md` §4 names "changes to the **agent role prompts**
  (`template/agents/`)" as a project-defined human-only item — process/prompt judgment no
  deterministic gate can score. The human judges it by reading the diff plus the unittest
  command above; do **not** invent a production edit to manufacture a red leg.
- **Invariant to restore:** a headless leaf is never left to invent its own filesystem
  lifetime — every role body whose working files the harness creates and disposes states that
  ownership: which roots the leaf may write in, and that reclaiming them is the harness's job,
  not the leaf's. Quantified over the category: it binds **every** such leaf body, not the one
  that was caught — self-test per `docs/principles.md` §3.2, could Do satisfy this by guarding
  a single module? No: adding the line to `reviewer.md.jinja` alone leaves `adversary`,
  `code-review`, `plan-reviewer` and `builder` with the identical silence and the identical
  failure, so a one-file patch visibly fails it. Source: the harness's own mechanical ownership
  — `leaves.py:1831`, `:2145`, `:2437` (auto-deleted `TemporaryDirectory` per leaf) and `:1290`
  + `[driver].sweep_worktrees` (harness-reclaimed worktree) — read against codex `exec`'s
  unconditional rejection of rm-style commands in this mode, which makes the invented cleanup
  not merely unnecessary but *impossible*. Internal rule, Tier C per `docs/principles.md` §5;
  §5/§6 are an unfilled scaffold in this instance, so no §6 category gate applies.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Ordering note:** deliberately **no** `Depends on` on #422 ("reviewer scratch is per-run and
  disposable — every review rebuilds cold"). #422 is not in this batch, and the two are
  sequenced by wording rather than by scheduling: this bundle ships only the **prohibition plus
  the ownership fact**, phrased over "the roots the harness gives you", so when #422 later adds
  a lane-stable harness-owned cache root the prompt gains a sanctioned destination *without*
  this text having to be rewritten or contradicted. That is why the criterion forbids naming or
  assuming any persistent location here — see Scope's exclusion.
- **Surfaces:** data
- **Difficulty:** medium
- **Scope:** state the harness's filesystem ownership in the canonical vendor-neutral role
  bodies of the headless leaves whose working files the harness creates and disposes — the
  sandboxed reviewer (`template/agents/reviewer.md.jinja`), the advisory reviewers
  (`adversary.md.jinja`, `code-review.md.jinja`) and the plan advisory
  (`plan-reviewer.md.jinja`), which share one sandbox shape, plus the builder
  (`builder.md.jinja`), whose worktree-and-granted-bundle shape differs and must be stated
  accurately rather than copied. / out of scope: **any persistent or cached scratch location**
  — do not name one, promise one, or imply one exists (#422 owns that, and pre-empting it here
  is exactly the contradiction the Ordering note avoids); any change to `leaves.py`, `sweep.py`
  or `config.py` — this bundle is prompt text plus its test, no driver code; the `sizer` and
  `splitter` bodies, whose cwd is the **bundle dir** (persistent harness state, `leaves.py:1066`
  / `:1149`), a different lifetime that would need its own statement; the interactive leaves;
  the `.claude/agents/*.md.jinja` wrappers, which are generated from the canonical bodies by
  `{% include %}` and must not be hand-edited (`test_role_prompts.py` enforces the sync); and
  re-litigating the reviewer's independent-re-verification mandate at
  `template/agents/reviewer.md.jinja:24-25`, which stays exactly as it is.
- **Repro instruction:** on a clean checkout of the target base —
  `for f in reviewer adversary code-review plan-reviewer builder; do git -C ../pdca-harness show
  origin/main:template/agents/$f.md.jinja | grep -ci "scratch\|temp dir\|your cwd\|working
  directory"; done` → prints `0` five times: no body says where the leaf may write or who
  cleans up. Cross-read the harness's actual ownership at
  `git -C ../pdca-harness show origin/main:template/src/pdca_harness/leaves.py` lines 1831,
  2145, 2437 and 1290 — the sandboxes are `TemporaryDirectory`s deleted on leaf exit and the
  worktree is harness-reclaimed, so nothing inside them ever needs a leaf-run cleanup. Runtime
  form: run a codex `exec` reviewer leaf and observe it create `/var/tmp/pdca/pdca-reviewer-*`
  and then be refused at spawn with `rejected: rm -f style commands are not permitted`. The
  named test automates the text assertion → red pre-fix.
- **External dependencies:** none
- **Test file:** `template/tests/test_leaf_scratch_discipline.py` (new file, top-level in
  `template/tests/`). **It must run non-vacuously in the template checkout**, which is the
  posture the C4 invocation uses (`cd template && PYTHONPATH=src python3 -m unittest
  tests.<name>`). Do **not** copy `template/tests/test_role_prompts.py`'s `ROOT/"agents"` +
  `glob("*.md")` shape: in the template checkout the bodies are still `.md.jinja`, so that
  module `skipTest`s itself (`test_role_prompts.py:16`, `:38-41`) and a test built on it would
  report `0 tests`-style vacuous success in *both* phases. Resolve the body path
  posture-aware instead — `agents/<name>.md.jinja` in the template checkout,
  `agents/<name>.md` in a rendered instance — so the assertion runs in both. Assert per body,
  with `subTest(agent=…)`, that the ownership statement is present; keep the assertion about
  the *property* (a writable-roots statement and a no-leaf-cleanup statement) rather than one
  brittle exact sentence.
- **Citations expected:** Do must cite path:line on the target branch for every change. This is
  a composition slice for the test's path resolution: the peer callsite is
  `template/tests/test_remote_control_docs.py:19-24` — `TEMPLATE =
  Path(__file__).resolve().parents[1]` and the `next(TEMPLATE / n for n in ("pdca.toml.jinja",
  "pdca.toml") if (TEMPLATE / n).is_file())` pick that makes one module work in both postures;
  mirror it for `agents/<name>.md.jinja` vs `agents/<name>.md`. Do MAY open that one file.
  Supporting facts, already verified, that need no exploration: the canonical bodies live in
  `template/agents/` and the `.claude/agents/` wrappers are `frontmatter + {% include %}` of
  them (`test_role_prompts.py:5-6`), so editing the canonical body reaches both vendors and no
  wrapper needs touching; `reviewer.md.jinja:110` carries a `{% if contribution_model == "fork" %}`
  block, so the new text must sit **outside** any conditional to render for every instance; the
  reviewer body's existing structure is `## Inputs …` (`:15`), `## What you do` (`:22`),
  `## Always emit the complete 5/5/1 verdict table` (`:47`), `## Emit NEEDS-HUMAN by design on`
  (`:79`).
- **Prior-art check (triage cycles):** by affected file path —
  `git -C ../pdca-harness log --oneline origin/main -5 -- template/agents/reviewer.md.jinja` →
  `2d75858` (#250 external dependencies), `a1a0f61` (#236 provisional gate verdicts),
  `e991a71` (codex parity), `53d273a` (canonical bodies moved to `agents/`); none of them says
  anything about scratch, cwd or cleanup, and the grep above confirms the silence across all
  five bodies today. `gh search issues --repo eduralph/pdca-harness "scratch"` → #379 (this),
  #422 (open, the persistence counterpart — see Ordering note), #313 and #342 (closed,
  unrelated). `gh pr list -R eduralph/pdca-harness --state open` → empty. Not fixed, not in
  flight, no closed/rejected attempt on this seam.
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.
