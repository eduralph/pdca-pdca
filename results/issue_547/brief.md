# Design proposal — issue 547 / merge-mode-review-remarks-reenter-cycle

> Plan artifact for a three-part change. **Split required before Do** — see "Open
> questions". This brief is not to be built as one bundle: its criterion covers four
> separate changes that Check cannot judge apart. The route is `pdca-pdca split 547` (or
> `iterate-plan` at sign-off), using the children and the per-child rules listed below.
> Do reads ONLY this file.

- **Slug:** merge-mode-review-remarks-reenter-cycle
- **Kind:** enhancement (design proposal)
- **Goal:** In merge mode, a non-final wave's PR that has a green check rollup but is blocked by unresolved review threads (or a CHANGES_REQUESTED review) is (1) reported as *blocked by review remarks*, with each remark's body and file:line, and the remarks are written to the bundle; (2) optionally routed into a Do→Check round on the PR's own branch, archived as `iteration-v<N>`, after which the driver replies to and resolves the threads it addressed and merges once the rollup is green again; and (3) a COMPLETE-but-unmerged non-final PR left by an earlier run is taken through the same merge gates by a later `pdca flow <dependent ids>` instead of every dependent being skipped forever.
- **Success criterion:** With `wave_mode = "merge"` (merge mode merges non-final waves whenever it is set; there is no separate `auto_merge` key on main) and `gh` stubbed: (1) a PR whose rollup reads green and whose `gh pr view --json mergeStateStatus` is `BLOCKED`, with N unresolved review threads from the GraphQL `reviewThreads` query, makes `merge.merge_wave` return non-zero with stderr containing "blocked by N unresolved review thread(s)" and each thread's path:line, writes `merge-remarks.json` into the bundle listing every thread (id, path, line, body, author), and leaves the PR not marked ready; (2) with remark rounds enabled, the same PR leads to an `iteration-v<N>` archive in the bundle, a builder run whose worktree is the PR's branch head (not a fresh branch off base), gates and reviewer over the new head, and — after accept — one reply per addressed thread naming the commit, a resolve call per addressed thread, and a merge; `pdca status` shows the new iteration; with remark rounds disabled (the knob) the run stops after (1) unchanged; (3) a later `pdca flow <dependent>` whose prerequisite is COMPLETE, published by an earlier run **as a non-final wave of a merge-mode run (a marker recorded at publish/merge time)**, unmerged, and now clean (threads resolved, rollup green) merges that PR through `merge._merge_one`'s gates and then builds the dependent on the merged base — for both a plain `Depends on` and a `Depends on (merged)` edge; (3b) a COMPLETE draft PR with no such marker (a final-wave or single-bundle PR waiting for the human) is NOT readied or merged by a later flow — no `gh pr ready` / `gh pr merge` for it — and its dependent is held, naming it. Per-part legs the split children must carry are listed under Open questions.
- **Falsifiability:** RED offline with `gh` stubbed in front of `subprocess.run` (the pattern `template/tests/test_merge.py` uses) and, for part 3, a flow driven over the `StackFoldGit` real-git fixture (`template/tests/test_integrate_stack_bases.py`). Today: (1) `_merge_one` never reads `mergeStateStatus` or review threads (merge.py:463-638); a blocked merge ends in the generic "did not merge — a conflict, no merge rights …" message (merge.py:620-631) and writes nothing; (2) no code path rebuilds on a PR branch; (3) in merge mode `hold_unmerged` is off (flow.py:2901-2902), so an out-of-batch COMPLETE prerequisite named by a plain `Depends on` is not merged and not held, and one named by `Depends on (merged)` is held "until their PR merges" (flow.py:836-841) with no step that merges it. Each is assertable offline.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Depends on:** none
- **Conflicts with:** 500, 412, 464
- **Ordering note:** 500 edits `merge._merge_one`, the function part (1) changes; 412 changes `merge.merge_wave` and the merge branch of the wave boundary (flow.py:3080-3084); 464 adds a wave mode at the same boundary and in `config.py`. No build-on dependency.
- **Surfaces:** data
- **Difficulty:** high — `merge.py`, `flow.py`, `config.py`, `pdca.toml.jinja`, the iterate/archive path (`driver.py`, `autoiterate.py`, `state.py`), the builder's worktree base, and docs; part (2) changes where Do builds.
- **Scope:** The three parts above, and the knob that turns part (2) off (`[driver].remark_rounds`, default to be confirmed — see Open questions). Docs: the merge-mode bullet of `docs/07-crosscutting.md` (:858 onward) and the knob's comment in `template/pdca.toml.jinja`. / out of scope: stack mode (no driver merge); remarks on the final wave's PR (it stays a draft for the human); remarks posted after the merge; a reviewer-bot-specific parser (threads are read generically); re-deciding a remark the reviewer classes as needs-human (it goes to sign-off as usual); changing `merge_requires` semantics.
- **External dependencies:** none — every test stubs `gh` (including the GraphQL call); no live GitHub is needed to go red→green.
- **Test file:** `template/tests/test_merge_review_remarks.py` (new) for parts (1) and (3); part (2) may add `template/tests/test_merge_remark_round.py` (new). Import only modules (`from pdca_harness import cli, driver, flow, merge, merged, publish, state`), never a symbol the change adds, so the red leg still imports and fails on assertions (the C4 gate treats an import failure as UNVERIFIABLE).
- **Citations expected:** Do must cite path:line on the target branch for every change. Peer callsites: refuse and undo the ready-mark through `merge._refuse` (`template/src/pdca_harness/merge.py:453`) and `merge._undo_ready` (merge.py:438); read PR fields as `merged._pr_view` does (`template/src/pdca_harness/merged.py:187`); archive an attempt the way an iterate does (`driver.py`'s use of `state.DOWNSTREAM_OF_BRIEF`, `template/src/pdca_harness/state.py:116`) and carry findings in the existing `deferred-findings.json` shape (`state.CYCLE_EVIDENCE_ONLY`, state.py:174); build Do on an existing PR head the way an `Onto branch` bundle does (`brief.onto_branch`, `template/src/pdca_harness/brief.py:281`, and `$PDCA_BASE` in the C4 gate); for part (3), the out-of-batch prerequisite decision in `flow._runnable` (`template/src/pdca_harness/flow.py:786-835`).
- **Prior-art check (triage cycles):** `git -C ../pdca-harness log --oneline origin/main -n 15 -- template/src/pdca_harness/merge.py` → #279 ready-mark, #413/#462/#582/#621 rollup gate, #531 behind-base, #650, #658; nothing reads review threads or merge state. Closed-unmerged PRs on merge.py / flow.py: #637, #638, #639, #648, #649 — all closed as carried byte-identical by #657; none attempts this. `gh search prs "reviewThreads"`: none. Related open: #546 (`flow --only`). Result: no prior art.
- **Disposition hint:** new-feature

## Motivation

(The issue's mechanism — dependents "see `merge.has_contribution` + `is_merged == False` and are skipped" — does not match main: no `has_contribution` has ever existed in `template/src` on main (`git log -S has_contribution` is empty), so the wyrd run most likely used wyrd's local `src/` patches. On main a plain-edge dependent is *built*, and a `Depends on (merged)` one is *held* (flow.py:835-841). Before 547-c is built, the human confirms which edge type the #772 chain used and which harness version ran it, so the red test reproduces the real case and not one inferred from main.)

getwyrd/wyrd PR #793 (bundle #772, wave 1 of a five-bundle chain): every check green, `mergeStateStatus = BLOCKED` by required conversation resolution — two real P2 threads from the repo's automated reviewer. The driver could not merge, the run stopped, waves 2–3 never built, a later `pdca flow` skipped the dependents, and the fixes were made by hand outside the bundle. The bundle reads COMPLETE and its `patch.diff` no longer matches the PR. The finding never entered the cycle.

## Design

**Part 1 — detect and record.** After the rollup gate reads green (or when `gh pr merge` refuses), read `mergeStateStatus`. If `BLOCKED`, read unresolved `reviewThreads` (GraphQL, via `gh api graphql`) and any `CHANGES_REQUESTED` review. Write `merge-remarks.json` (one object per thread: id, path, line, body, author, url). Refuse with "blocked by N unresolved review thread(s)" and the list. The PR goes back to draft.

**Part 2 — remark round (behind a knob).** Bounded: a remark round counts against the bundle's existing iterate budget, and at most `[driver].remark_rounds` rounds (default 1 when on) run per PR; past the cap the run stops with a distinct "remark rounds exhausted" message. The accept that releases the merge is the human's sign-off, not the reviewer's: a non-final PR changed after Check is never merged with no human in the loop. Treat the remarks as late Check findings: archive the attempt as `iteration-v<N>`, carry the remarks forward as the round's findings, run the builder on the PR branch head, run gates and the reviewer over the new head, and on accept: commit onto the PR branch (no force), reply on each addressed thread with the commit, resolve it, re-wait the rollup, merge. Auto-iterate may fund it like an implementation-level round; a needs-human remark stops at sign-off.

**Part 3 — resumable stranded PR.** In merge mode, a prerequisite that is COMPLETE, published, unmerged (from an earlier run), and **recorded as a non-final wave PR of a merge-mode run** is merged through `_merge_one`'s gates before its dependent builds; if it cannot be merged, the dependent is held with the reason. This also closes a gap found while planning: today a plain `Depends on` to such a prerequisite in merge mode is neither merged nor held, so the dependent builds on a base without it (flow.py:794-829 with `hold_unmerged` off). That gap is a separate correctness bug the issue does not raise and must be its own child (547-b below), with its own red test.

The marker is needed because on disk a stranded non-final PR looks the same as a final-wave PR that "keeps its draft for the human's ready-mark" (merge.py:515-517): every refusal returns a PR to draft via `_undo_ready` (merge.py:438-460), and `publish.json` records no wave. Without the marker, part 3 would ready and merge PRs left for a human, against merge.py:481-482 ("Merge mode readies and merges only the PRs this run opened"). A PR that has the marker was opened by a merge-mode run *for* an unattended merge; merging it in a later run widens that rule from "this run" to "a merge-mode run", and the docs must say so.

## Alternatives considered

- **Only part 1 + part 3, leave fixes to the human.** Keeps the audit gap (a fix made outside the bundle) but removes the dead chain. A reasonable first child.
- **Auto-resolve threads without a round.** Hides real defects; rejected.

## Impact & compatibility

- New bundle file `merge-remarks.json`; new iteration source (remarks) in `iteration-v<N>`.
- New config knob in `pdca.toml.jinja` → a `copier update` brings it to instances (name the render/update suites in verification).
- Merge mode gains a `gh api graphql` call per blocked PR.

## Open questions

- **Split (required before Do).** Children:
  - **547-a — detect, record, distinct stop** (part 1; `merge.py`, low–medium). Extra legs: (i) the `merge_requires = "required"` path, where the rollup gate is skipped (merge.py:536) and the block shows only as a failed `gh pr merge` (merge.py:620-631) — detection must run there too; (ii) `BLOCKED` with zero unresolved threads and no CHANGES_REQUESTED (REVIEW_REQUIRED, required approvals, a ruleset) gets the generic refusal, not "blocked by 0 thread(s)"; (iii) `mergeStateStatus = UNKNOWN` right after `gh pr ready` is polled on the same budget as the #462 rollup wait, then treated as not-blocked-by-remarks; (iv) an outdated thread (`line: null`) reports `originalLine`.
  - **547-b — merge mode builds a dependent on a base without its plain-`Depends on` prerequisite** (bug; `flow.py`, medium). Red test: an out-of-batch COMPLETE, unmerged plain prerequisite in merge mode — the dependent is held, not built.
  - **547-c — resumable stranded PR** (part 3; `publish.py`/`merge.py` marker + `flow.py`, medium), `Depends on: 547-b`. Carries leg (3b).
  - **547-d — remark rounds** (part 2; driver/iterate/builder base, high), `Depends on: 547-a`. Carries the cap and human-sign-off rule above as legs.
  - 547-a and 547-c both edit `merge._merge_one` → `Conflicts with` each other. Fewer children is fine if the human prefers: 547-b may fold into 547-c as long as it keeps its own red test.
- Default of the knob: on (the issue's "may fund it") or off (today's stop, safer for instances that want a human first)? Recommended: off until part 2 has run on a real PR.

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.

Plan-review response: Revised, and the brief must not reach Do unsplit. Splitting needs new bundles, which this revision pass may not create, so the split is now a stated precondition (`pdca-pdca split 547` or `iterate-plan` at sign-off). The child list carries each finding: (1) part 3 needs a recorded non-final-wave marker, with leg (3b) showing a final-wave draft is never merged; (2) the plain-`Depends on` gap is its own child, 547-b; (3) the issue's `has_contribution` mechanism is not on main, so the human must confirm the edge type and harness version before 547-c; (4) part 1's four edge cases are legs of 547-a; (5) part 2 has a cap, a distinct stop, and a human-sign-off accept. `Conflicts with: 500, 412, 464` all resolve to bundles in this batch.
