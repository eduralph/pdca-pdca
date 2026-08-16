# Brief — issue 462 / merge-wave-waits-for-its-evidence

> The Plan artifact (docs 02 §PLAN). Do reads ONLY this file.

- **Slug:** merge-wave-waits-for-its-evidence
- **Defect:** In `wave_mode = "merge"`, a non-final wave's PRs are opened by `_publish_bundle`
  and merged **seconds later** by `merge.merge_wave`, before their required checks have had
  any chance to report. `_merge_one` (`template/src/pdca_harness/merge.py:127-204`) does three
  things back to back with no wait anywhere: `gh pr ready` (`:158-165`), then the full
  check-rollup gate (`:175-194`), then `gh pr merge` (`:196-204`). A PR created seconds ago has
  checks that are queued or not yet registered, so `_check_rollup` returns `pending` (a job
  still running/queued) or `empty` (no check reported yet) and `_merge_one` returns 1 — the run
  STOPs. **Nothing was wrong**: the evidence had simply not arrived. And the STOP is not clean —
  `gh pr ready` already succeeded, so that PR is left **non-draft**, advertising a readiness no
  human granted, while every later bundle in the wave keeps its draft, is never touched, and no
  later wave runs.
  Observed at getwyrd/wyrd-pdca 2026-08-08, wave 691/695/696/697: `getwyrd/wyrd#703` created
  `15:57:37Z`, `ready_for_review` `15:57:43Z` — six seconds later — merge refused; #704/#705/#706
  untouched; the repo's required `gate` context depends on `rust` + `tikv`, both still running.
  **Correction to the issue text, verified on the target base:** the report predates #413
  (PR #484, `2261b53`, merged 2026-08-11), which added the rollup gate at `:175-194`. The
  failure now lands one line earlier and with a precise message ("a check has not finished"),
  but the two defects the issue names are untouched: **the run still treats "the evidence has
  not arrived yet" as a terminal verdict**, and **it still leaves a readied PR behind when it
  declines**. `merge_requires = "required"` does not help either — it skips the rollup gate and
  hands the same race to `gh pr merge`, which refuses a `BLOCKED` PR just as immediately.
- **Success criterion:** With the patch, `merge.merge_wave` at a non-final wave boundary:
  (i) **waits** while the rollup verdict is `pending` or `empty`, re-reading it until it
  resolves or a **bounded, configurable** wall-clock limit expires — a rollup that turns green
  after the checks report is merged, and the run continues into the next wave;
  (ii) still **refuses and STOPs** — no merge, non-zero, later waves not run — on `failing`,
  on `unreadable`, and on a `pending`/`empty` rollup that is still unresolved when the bound
  expires, with a message that distinguishes "the checks never reported within Ns" from "a
  check is red";
  (iii) on **every** path where it declines to merge a PR it readied — the rollup refusal, the
  bound expiring, and a failing `gh pr merge` — that PR is returned to **draft** before
  `_merge_one` returns non-zero, so a stopped wave leaves no PR advertising a readiness no
  human granted; an already-merged or dry-run path readies nothing and undoes nothing;
  (iv) the existing contract is unchanged otherwise: dry-run shells nothing, a close/no-fix or
  already-merged bundle is skipped, a COMPLETE bundle with no recorded PR still fails closed,
  and `merge_requires = "required"` still skips the rollup gate.
  Demonstrable by C4-verify: `template/tests/test_merge.py` drives `merge.merge_wave` with
  every `gh`/`git` call mocked (`_gh(checks=…, ready=…, merge=…)`, `:50-60`) and asserts the
  exact verb sequence, so (i)-(iv) are assertions over recorded argv, offline and instant.
- **Falsifiability:** RED is reachable on the base toolchain — pure-stdlib Python ≥ 3.11, no
  network, no `gh`, no services — in the target checkout Do is given. `test_merge.py` already
  contains the negative control: `test_pending_check_refuses` (`:252-258`) asserts **today's**
  behaviour — a pending rollup refuses immediately, `gh pr merge` never runs. The new cases
  invert it (pending-then-green merges; the readied PR is undone on every refusal), and with
  `merge.py` reverted they fail against the mock's recorded calls. The wait must be driven
  through an injectable/patchable sleep so the red→green costs no wall-clock. C4-verify's red
  leg reverts `merge.py` (production) and keeps every `template/tests/*.py` hunk
  (`engine/scripts/run-verify.sh:214-217`), so an updated `test_pending_check_refuses` plus new
  cases in the same file earn a genuine red — no new file is required and no new production
  symbol may be imported at module level (see Citations expected).
- **Invariant to restore:** A wave boundary must not turn *absence of evidence* into a
  **verdict**, and must leave every PR it touched exactly as it found it whenever it declines
  to merge. Two halves of one rule, both quantified over the category rather than the observed
  race: (a) "no evidence" is neither pass nor fail anywhere in this harness — the same rule
  `engine/README.md:44-68` states for a gate leg that ran no test, and that
  `merge.py:20-31`/`:82-85` already applies in the fail-closed direction; a bounded wait is what
  makes "the checks have not reported *yet*" distinguishable from "the checks say no.
  (b) The harness never leaves a PR marked ready — `docs/INTEGRATION.md` §10 ("publish opens
  **draft** PRs; only the human marks a PR ready and merges") and `docs/05-check.md:787-797`,
  which names `wave_mode = "merge"` as the *one carve-out* and scopes it to PRs the run is
  merging. A PR that was not merged is outside the carve-out, so the ready-mark must not
  survive the decision not to merge. Source: internal project invariants (Tier C —
  `docs/principles.md` §5/§6 are unfilled scaffolds in this instance, so no §6 category gate
  applies; these are cited from the target's own written rules).
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Ordering note:** No `Depends on` / `Conflicts with` on purpose. This bundle is one of the
  nine ids of run 2 of the 0.60 bug phase, which the human sequenced as a **single wave**
  (`plan-0.60-bug-order.md` §"Recommended order"): declaring an ordering field here would split
  the run into waves, and a wave > 0 bundle in this instance is exactly what issue 474 (also in
  this run) false-reds. Ordering lives in the run boundaries instead. Two consequences handled
  at Plan: `docs/07-crosscutting.md` is **out of scope** below because issue 476 owns that file
  in this run, and the `template/pdca.toml.jinja` hunk this slice adds sits in `[driver]`,
  far from the `[gates]` block 474 may touch — a distant-hunk same-file pair the human merges
  in number order, as the run plan anticipates.
- **Surfaces:** data
- **Difficulty:** medium
- **Scope:** The non-final-wave merge boundary in `template/src/pdca_harness/merge.py`: make
  the boundary wait for the rollup to resolve within a bounded, configurable limit, and make
  every decline restore the draft state it changed. The bound is new configuration — plumb it
  through `Config` the way `merge_requires` is plumbed (`config.py:361-368`, `:703-707`,
  `:813`) and document it in the `[driver]` block of `template/pdca.toml.jinja` beside
  `merge_requires`, including what a sensible default is and that `0` means "do not wait"
  (today's behaviour). **Out of scope:** `gh pr merge --auto` (the issue's option A) — the
  driver must know the base has actually moved before the next wave's Do worktree resets to
  it, so `--auto` would need a second wait bolted on anyway, and it would relax the STOP
  discipline to PRs the run never confirmed merged; `docs/07-crosscutting.md` and
  `docs/05-check.md` (476 owns the former in this run; the `[driver]` block is this knob's
  documentation home, as it is for `merge_requires`); `wave_mode = "stack"` and the
  integration-fold path; publish, the reviewer, and any change to what `_check_rollup`
  classifies; retrying a *failing* check (a red check is a genuine stop).
- **Repro instruction:** On a clean checkout of the target base (`origin/main` of
  eduralph/pdca-harness), offline, from `template/`:
  `PYTHONPATH=src python3 -m unittest tests.test_merge -v` — green today, and
  `test_pending_check_refuses` documents the defect as intended behaviour: with a rollup whose
  only check is `("ci", "pending")`, `_merge_one` prints "a check has not finished", returns 1,
  and the recorded `gh` calls show `pr ready` ran while `pr merge` never did and **no**
  `pr ready --undo` followed. Read `merge.py:158-204` alongside it: the ready-mark at `:159`
  precedes both refusal paths and is never reversed. The live incident is in the issue body
  (getwyrd/wyrd#703-706, six seconds between create and ready_for_review).
- **External dependencies:** none — the suite mocks every GitHub-CLI and git call, so the slice
  builds and goes red→green on the base toolchain: no gh binary, no network, no merge rights.
- **Test file:** `template/tests/test_merge.py` — extend the existing suite (its `_gh` /
  `_rollup` mock harness is what makes the verb sequence assertable) and update
  `test_pending_check_refuses`, whose current assertion **is** the defect. C4-verify's red leg
  keeps all `template/tests/*.py` hunks and reverts only `merge.py`, so an appended test earns
  its red; a new file is unnecessary here.
- **Citations expected:** Do must cite path:line on the target branch for every change.
  Composition cues — this slice wires into patterns the codebase already applies:
  * the rollup verdict vocabulary and its fail-closed default are `merge.py:66-114`
    (`_check_rollup` already separates `pending` from `failing`/`empty`/`unreadable`; the wait
    keys off that classification, do not re-derive it);
  * a new `[driver]` scalar is plumbed exactly as `merge_requires` is —
    `config.py:361-368` (the dataclass field + docstring), `config.py:703-707` (read, coerce,
    warn on a bad value rather than crashing), `config.py:813` (constructor), and documented in
    `template/pdca.toml.jinja` `[driver]`; note the file's own warning that a key added after
    the next `[table]` header silently joins that table;
  * `gh pr ready --undo` is the documented inverse of the `gh pr ready` at `merge.py:159`;
    treat its failure the way `:160-165` treats a failed ready — reported, never masking the
    real reason the wave stopped.
  The regression test must not import a symbol this patch introduces at module level: C4's red
  leg reverts production first, and a module that then fails to import is recorded
  `PDCA-UNVERIFIABLE`, not red (`engine/scripts/run-verify.sh:231-234`).

  **Path convention in this brief:** every `template/…`, `tests/…` and `docs/…` path is on the
  **target branch** (eduralph/pdca-harness @ main) — those are the files Do reads and edits. Every
  `engine/…`, `pdca.toml` and `results/…` path is in **this pdca-pdca instance** (the verification
  engine and the bundles that run the cycle); they are cited to explain how the gates will judge
  this patch, and Do must not edit them.
- **Prior-art check (triage cycles):** By file path on `origin/main`:
  `template/src/pdca_harness/merge.py` — `2261b53` (#413, PR #484, the rollup gate),
  `126db1f` (#279, the ready-before-merge), `5c4e332` (the original opt-in merge mode); none
  waits, none reverses the ready-mark. `gh pr list -R eduralph/pdca-harness --state open` → **no
  open PRs at all**. Closed PRs: #484 is the nearest relative and is merged (it is why the
  failure message changed). Open issues searched for `transient`: #371 (a transient red on a
  *gating gate row*) and #506 (a transient API error inside a *leaf*) are the same family in
  two other layers and are deliberately separate slices; #500/#463/#464/#412/#395 are the wave
  machinery's own enhancement group (0.60 enhancement phase, not this). Not previously
  attempted, not rejected.
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.
