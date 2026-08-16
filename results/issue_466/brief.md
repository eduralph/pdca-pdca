# Brief — issue 466 / stub-split-never-reaches-the-tracker

> The Plan artifact (docs 02 §PLAN). Do reads ONLY this file.

- **Slug:** stub-split-never-reaches-the-tracker
- **Defect:** With `[leaves.splitter] mode = "stub"`, `pdca split <id> --accept` files the
  **offline placeholder** proposal as real tracker sub-issues and materialises child bundles
  from fixture text. Observed live: `getwyrd/wyrd#708` and `#709` are open as sub-issues of
  `#682`, titled literally `stub-child-one` / `stub-child-two`, with `results/issue_708/brief.md`
  and `issue_709/brief.md` carrying the fixture body — nothing to do with #682's work. Verified
  on the target base, nothing in the chain can tell a stub proposal from a real one:
  * `leaves.do_split` (`template/src/pdca_harness/leaves.py:1594-1602`) branches on
    `cfg.splitter.mode == "command"` and falls through to `_stub_split` for **any** other mode —
    silently: same rc 0, same printed proposal path, nothing on stderr. The operator's only
    signal that no model ran is recognising the fixture by eye.
  * `leaves._stub_split` (`:1605-1631`) writes `<!-- pdca:split-proposal v1 -->` — byte-identical
    in shape to a real splitter's header — so **nothing on disk records the provenance**, and
    `--accept` runs in a different process from `do_split`, where an in-memory flag could not
    reach it.
  * `split.preflight` (`split.py:276-305`) and `split.validate` check structure only (proposal
    present, parent not already split, ordering labels resolve, no cycles). The stub passes
    every one, because it was written to.
  * `split.can_file` (`split.py:912-928`) asks only whether the tracker is GitHub, the repo
    resolves and `gh` is on PATH. Its "never a silent skip" docstring is about the opposite
    failure; nothing asks whether the proposal is **fit to file**.
  * `split.child_title` (`split.py:939-…`) falls back to the child's slug, so the fixture slug
    becomes the tracker issue title verbatim.
  This is the same path #358 specifies as the **offline** end-to-end test ("stub splitter →
  accept → flow over the children"), which is harmless only because `can_file` fails or `--ids`
  is supplied. In a live checkout with a working `gh` and no `--ids`, the fixture reaches the
  tracker — and tracker issues cannot be withdrawn, which is precisely the irreversibility the
  whole accept path is built around (`cli.py:756-766`, `split.py:279-283`).
- **Success criterion:** With the patch:
  (a) a stub-produced `split-proposal.md` is **self-identifying on disk** — the provenance is
  written into the proposal by the stub itself and survives the process boundary, so a reader
  that never saw `do_split` run can tell it apart (not a slug-name sniff, not an in-memory
  flag);
  (b) `pdca split <id> --accept` **refuses** on a stub-marked proposal **before** `can_file`
  and before any `gh issue create`, naming the cause and the remedy
  (`[leaves.splitter] mode = "command"`); the refusal is on the **filing**, not on acceptance
  as such — it exits non-zero, creates no child bundle and does not mark the parent split;
  (c) `--ids` still accepts a stub-marked proposal unchanged, so #358's offline round-trip
  keeps working: that path files nothing, the ids already exist, and the operator supplied them
  deliberately — this is the seam between "exercising the machinery" and "reaching the tracker";
  (d) `pdca split <id>` in stub mode **says so on stderr at the moment it runs**, rather than
  leaving the operator to infer it from the proposal's contents;
  (e) with `mode = "stub"` and `can_file` returning `(True, repo)`, `pdca split <id> --accept`
  invokes **no** `gh issue create` and creates **no** bundles — asserted on the *absence of the
  call*, not on the exit code alone, because a refusal that filed the first child before
  erroring is the failure mode worth locking.
  Demonstrable by C4-verify offline: the whole path is driven in-process with `subprocess.run`
  stubbed, so (b)-(e) are assertions over recorded argv.
- **Falsifiability:** RED is reachable on the base toolchain — pure-stdlib Python ≥ 3.11, no
  network, no `gh` binary, in the target checkout Do is given. Pre-fix, with the splitter leaf
  configured `mode = "stub"` and `split.can_file` stubbed to `(True, "org/repo")`, the accept
  path runs `file_children` → `gh issue create` for each fixture child: a test asserting that no
  such argv was recorded fails today, which is the red. `template/tests/test_split.py` and
  `test_split_lineage.py` already drive `cli`/`split.accept` this way with `gh` mocked, so no
  live tracker is involved in either leg. C4's red leg reverts production
  (`leaves.py`/`split.py`/`cli.py`) and keeps every `template/tests/*.py` hunk
  (`engine/scripts/run-verify.sh:214-217`), so the new file goes red — provided it imports no
  symbol the patch adds (see Citations expected).
- **Invariant to restore:** An **irreversible external action** — filing tracker issues — may
  never be taken on an artifact that no model authored, and the **provenance of a generated
  artifact must survive to the process that consumes it**. Stated over the category, not the
  splitter: any placeholder any stub leaf writes is indistinguishable from real output unless
  the artifact itself records where it came from, and the accept path's own doctrine is that
  everything checkable is checked *before* the first unrecallable act. Self-test: this cannot
  be satisfied by guarding one module — it constrains what `_stub_split` writes AND what the
  filing path refuses, in two different modules and two different processes. Source: internal
  project invariant (Tier C) — the target's own written rule, `split.py:279-283` ("filing
  happens BEFORE the ids exist, and a tracker issue cannot be withdrawn", #358),
  `cli.py:756-766` ("Tracker issues cannot be withdrawn and a materialised bundle is barely
  better, so this order is the whole guarantee", #459), and `split.py:713-721` (the rollback
  doctrine). `docs/principles.md` §5/§6 are unfilled scaffolds in this instance, so no §6
  category gate applies.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Ordering note:** No `Depends on` / `Conflicts with` on purpose. This bundle is one of the
  nine ids of run 2 of the 0.60 bug phase, sequenced by the human as a **single wave**
  (`plan-0.60-bug-order.md`): declaring an ordering field would split the run into waves, and a
  wave > 0 bundle in this instance is what issue 474 (also in this run) false-reds. Ordering
  lives in the run boundaries. Known same-file neighbours, accepted by that plan: 494 and 506
  also touch `leaves.py`, in distant regions (`:782`/`:3261`/`:3400` and `:647`/`:1740` versus
  this slice's `:1594-1631`) — expect the advisory "both touch" line at publish; the human
  merges in number order and git resolves distant hunks. Issue 467 (split children lose
  milestone/labels, `split.py:580-607`) is adjacent to this slice's `split.py` region and is
  deliberately held to **run 3**, after this merges — that run boundary is the ordering.
- **Surfaces:** data
- **Difficulty:** low
- **Scope:** Make a stub-authored split proposal self-identifying, and make the **filing**
  branch of `pdca split --accept` refuse one; announce stub mode on stderr when `do_split` takes
  the stub branch. **Out of scope:** whether a split child should route through Plan at all (the
  issue parks it deliberately: today `split.py`'s docstring calls each child body "a full draft
  brief" and the run continues straight to Do; changing that needs a new state distinguishing
  "split seed" from "planned brief" — a separate decision); retroactive cleanup of
  `getwyrd/wyrd#708`/`#709` (instance data, by hand); the `--ids` path's behaviour, which must
  stay byte-identical; `split.validate` / `split.preflight`'s structural checks and the
  convergence report (#459), which answer a different question — whether a *real* split
  converged; `state.state`'s PLANNED derivation (`state.py:167-187`) and `brief.is_placeholder`
  (`brief.py:161-…`), which the issue cites only to explain the blast radius;
  `template/pdca.toml.jinja`; every other stub leaf (this slice is the one whose output reaches
  a tracker).
- **Repro instruction:** On a clean checkout of the target base (`origin/main` of
  eduralph/pdca-harness), offline, from `template/`:
  1. `PYTHONPATH=src python3 -m unittest tests.test_split -v` — green today, and none of its
     cases asks where the proposal came from.
  2. Read the path end to end: `leaves.py:1594-1602` (any non-`command` mode silently takes
     `_stub_split`, rc 0, same printed path) → `leaves.py:1612-1631` (the fixture, carrying the
     real header comment) → `cli.py:766-780` (`parse` + `preflight`, then straight into
     `file_children` when no `--ids` were given) → `split.py:912-928` (`can_file` asks only
     whether the tracker is reachable).
  3. The live evidence is in the issue body: `getwyrd/wyrd#708` and `#709`, open as sub-issues
     of `#682`, titled `stub-child-one` / `stub-child-two`.
- **External dependencies:** none — the accept path is driven with the GitHub CLI stubbed, so
  the slice builds and goes red→green on the base toolchain with no network and no tracker.
- **Test file:** `template/tests/test_split_stub_guard.py` (new, the path the issue names).
  A new module is right here: the file is the record of "a stub must never reach the tracker",
  and C4's red leg keeps every test hunk while reverting production, so a new file earns its red
  exactly as an appended one does.
- **Citations expected:** Do must cite path:line on the target branch for every change.
  Composition cues — this slice wires into patterns the codebase already applies:
  * `split.preflight` (`split.py:276-305`) is the one place **both** acceptance shapes converge
    before anything irreversible, and is therefore the wrong home for this refusal — it would
    also block `--ids`, which criterion (c) requires to keep working. The filing branch is
    `cli.py:777-796` (`if not ids:` → `split.file_children`); refuse there, before `can_file`
    is consulted, in the shape the neighbouring `TrackerUnavailable` handler already uses —
    `split.advisory(...)` for the message plus a non-zero return, never a raise into the CLI.
  * the stderr note for (d) belongs with the branch that chooses the stub,
    `leaves.py:1596-1597`; the sibling shape to copy is the "never a silent skip" messaging at
    `cli.py:781-788`.
  * `template/tests/test_split.py` shows how this suite stubs `subprocess.run` for `gh` and
    builds a parent bundle; reuse that harness rather than inventing a second one.
  The new test must not import a symbol this patch introduces at module level (e.g. a new
  marker constant): C4's red leg reverts production first, and a test module that then fails to
  import is recorded `PDCA-UNVERIFIABLE`, not red
  (`engine/scripts/run-verify.sh:231-234`). Drive the stub through `leaves._stub_split` /
  `leaves.do_split`, which exist on both legs.

  **Path convention in this brief:** every `template/…`, `tests/…` and `docs/…` path is on the
  **target branch** (eduralph/pdca-harness @ main) — those are the files Do reads and edits. Every
  `engine/…`, `pdca.toml` and `results/…` path is in **this pdca-pdca instance** (the verification
  engine and the bundles that run the cycle); they are cited to explain how the gates will judge
  this patch, and Do must not edit them.
- **Prior-art check (triage cycles):** By file path on `origin/main`:
  `template/src/pdca_harness/split.py` — `a2eefe1` (#459 convergence report, PR #486),
  `5c83070` (lineage), `3a3d8ce`, `5f3ee1d` (both about irreversible tracker state on the
  *filing* path) — every one of them hardens what happens *around* filing; none asks whether the
  proposal was authored by a model. `gh pr list -R eduralph/pdca-harness --state open` → **no
  open PRs**. Closed: #486 (#459) is the nearest relative and is merged — and it does not catch
  this, since the stub's two children would report as converged. #358's offline round-trip test
  is the path that must keep working (criterion (c)). Open issues: #467 (children lose
  milestone/labels) and #481 (split parent left briefless) share the module and are scheduled
  after this in the run plan. Not previously attempted, not rejected.
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.
