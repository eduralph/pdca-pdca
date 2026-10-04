# Brief — issue 590 / flow-dep-on-seed-child-refused

> The Plan artifact (docs 02 §PLAN). Do reads ONLY this file.
> Verified against `eduralph/pdca-harness` `origin/main` @ `c67a14d`. Since #589 merged
> (`bad66f2`), the refusal is an rc-2 message, not a traceback; the refusal itself is the bug.

- **Slug:** flow-dep-on-seed-child-refused
- **Defect:** `pdca flow 809 810 776 777` is refused before any work when `809` is terminal on
  a split (its children `839`–`843` still PLANNED — the recovery-seed case #473 handles) and
  `810` (also named) declares `Depends on: 842`, a child of `809`:
  `issue_810: declared dependency '842' is neither in this batch nor an existing COMPLETE bundle`.
  `flow 809` alone works (the children are adopted), and `flow 839 840 841 842 843 810 776 777`
  works; only naming the seed AND an id that depends on one of its children fails.
  Cause: `flow_ids` moves the terminal split parent out of the drive set into `seeds`
  (`template/src/pdca_harness/flow.py:2232-2268`). `_drive_and_act` then levels the NAMED
  batch strictly first — `waves.compute_waves(cfg, bundles)` (`flow.py:1830`), which calls
  `check_dep_graph` (`template/src/pdca_harness/waves.py:171`) — and only afterwards splices
  the seeds' children in at `k=-1` (`flow.py:1836-1839`). At the strict check `842` is neither
  in the batch nor COMPLETE, so `check_dep_graph` raises (`waves.py:81-99`), although the very
  next statement would have scheduled `842` ahead of `810`. The comment above the strict call
  (`flow.py:1815-1818`) says the strictness "belongs to the request… and adoption never relaxes
  it"; here the prerequisite IS part of the request — the operator named its parent as a
  recovery seed.
- **Success criterion:** With the patch, through `cli._flow` (the operator surface) on the
  offline driver suite: given a parent `P` already terminal on a split (via the production
  `split.accept`) whose child `C` is PLANNED, and a named bundle `D` with `Depends on: C`,
  `pdca flow P D` is NOT refused: `C` is adopted and driven in an earlier wave than `D`, and
  `D` is driven after it (both reach COMPLETE with stubbed leaves). Exact shape for the repro
  below (`500` split into `601`, `602` with `602 Depends on: 601`, the fixture's `_CHILD_TWO`;
  `810 Depends on: 602`): `waves_driven == [["issue_601"], ["issue_602"], ["issue_810"]]`. Pre-fix the same call
  returns rc 2 with "declared dependency 'C' is neither in this batch nor an existing COMPLETE
  bundle" and drives nothing. The strict contract still holds for everything else: in the
  same suite, `pdca flow D` alone (no seed named) and `pdca flow P D` where `D` depends on an
  id that is NOT among `P`'s lineage children are still refused up front with rc 2, exactly
  as today. A grandchild reached by walking through a child that is itself terminal on a
  split (#473's 500 → 601 → 701 walk) counts as offered too.
  Boundary cases, both in the same file:
  (a) **Not offered ⇒ still refused up front.** `D` depends on a lineage child of `P` whose
  bundle is already terminal and not COMPLETE (DISCONTINUED or RESOLVED), or has no brief.md:
  `pdca flow P D` returns rc 2 with today's "neither in this batch nor an existing COMPLETE
  bundle" message and drives nothing. "Offered" means: a lineage child (reached transitively)
  whose bundle has a brief and is in flight (not terminal). A child that is COMPLETE already
  resolves today; a child terminal on a split is walked through, not offered.
  (b) **Offered, then not taken ⇒ held, never a raise.** `C` is offered but adoption does not
  take it because another run holds its drive claim (hold it the way
  `test_split_adoption_skips_a_child_another_live_run_holds` does,
  `template/tests/test_flow_single_driver.py:610-632` — a real second process holding the
  claim via that file's `_hold` helper; copy the technique, do not import from that file):
  `pdca flow P D` returns without a traceback and without rc 2, `C` and `D` are not driven,
  and stderr names `D` as not built for want of `C` (today's `_runnable` line "skipped —
  prerequisite(s) not ready (C)", `flow.py:714-715`, or the `_reschedule` hold line if a
  re-level ran — either shape, but `D` is named). The rc is not 2 (no up-front refusal);
  assert `D`'s state is still PLANNED rather than pinning an exact rc.
- **Falsifiability:** RED is reachable offline: `template/tests/test_flow_adopt_recovery.py`'s
  `AdoptRecovery` fixture already builds hermetic instances, makes real splits with
  `split.accept`, stubs all leaves, and runs `cli._flow` — the repro is one more case on it.
  Runs under the C4 gate as `cd template && PYTHONPATH=src python3 -m unittest
  tests.test_flow_adopt_recovery`. No network, no git remote (`--no-publish`).
- **Invariant to restore:** The up-front dependency check judges a dependency against
  everything the request will schedule, and nothing more: an id the run will adopt from a
  named recovery seed is part of the request (#473), so an edge to it is resolvable; an edge
  to anything else unresolvable still refuses before any work (the contract
  `waves.partition_schedulable`'s docstring calls "right for an explicit `flow <ids>`",
  `waves.py:264-267`, and `flow.py:1815-1818`). And an edge the adoption then does NOT take
  (the child is claimed by another run, already terminal, or refused) must never become a
  mid-run raise — it is held and reported by the tolerant re-level exactly as a mid-run hold
  is today: by `_runnable`'s skip at `D`'s wave when nothing was adopted (`_reschedule` runs
  only `if adopted:`, `flow.py:1454-1457`; `_runnable` skips at `flow.py:705-716`), or by the
  tolerant re-level (`flow._reschedule`, `flow.py:1251-1270`) when one ran. Source: the two docstrings cited;
  #473's recovery contract in `_drive_and_act`'s docstring (`flow.py:1768-1772`).
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Conflicts with:** 616
- **Ordering note:** Wave 0. `Conflicts with: 616` because both add work at the start of
  `flow._drive_and_act`, around the strict levelling and the seed splice
  (`flow.py:1815-1860`); 616 also depends on 591 so it lands in wave 1 anyway. No overlap
  with 591's hunks (integrate.py and the fold call at `flow.py:1996`).
- **Surfaces:** data
- **Difficulty:** medium — two files (`flow.py` around `_drive_and_act`'s strict levelling,
  and `waves.check_dep_graph` / `compute_waves`, whose strictness is shared with
  `partition_schedulable`'s callers and `pdca waves`), but the semantics of "what may be referenced up front"
  is shared by every batch entry point, so the reviewer must hold the strict path, the seed
  splice and the tolerant re-level in view together.
- **Scope:** Before the strict levelling, the names the seeds will offer must count as
  resolvable for the strict check. Collect them with a QUIET walk: read each seed's lineage
  record with `split.read_lineage` + `_lineage_children` (`flow.py:770-788`, the reader adoption
  itself uses — never a second parse), walk THROUGH children that are themselves terminal on a
  split (`_is_split_parent`), and keep a child only if its bundle has a brief and is not
  terminal (the "offered" definition in the criterion). Do NOT call `_adoptable` /
  `_adopt_split_children` for this: they print operator-facing lines (malformed record, "no
  readable children record", "NOT adopted: no brief.md", "is itself terminal on a split",
  "already terminal", `flow.py:1167-1175`, `:1231-1244`) and append to `refused`, so a second
  pass would print every line twice and break exact-count assertions such as
  `test_flow_adopt_recovery.py:393`. Do not refactor `_adoptable` either; the k=-1 adoption pass
  stays exactly as it is.
  How the names reach the check: add an optional keyword parameter (e.g. `offered:
  frozenset[str] = frozenset()`) to `waves.check_dep_graph` and pass it through
  `waves.compute_waves`; with the default, behaviour is byte-for-byte today's. A dependency on
  an offered name is resolvable and adds no edge in the strict levelling (the child is not in
  the named batch yet); the `k=-1` splice already re-levels the whole schedule with the
  children in it, and that is where the edge becomes a real ordering constraint. ONLY the
  strict call in `_drive_and_act` (`flow.py:1830`) passes `offered`. The other callers —
  `_reschedule`'s `compute_waves` (`flow.py:1267`), `partition_schedulable`, and `pdca waves` —
  stay unchanged. Do not pass the offered names in as a pseudo-batch (that would add real
  edges and bundles to the strict levelling).
  `Depends on` / `Depends on (merged)` only: a `Stacks on:` edge to a seed child stays refused
  up front as today (`waves.py:80-91` — a stack parent must be an active COMPLETE bundle with a
  live published branch, which a PLANNED child is not).
  A dependency that adoption then does not take is held (see Invariant) — never a mid-run raise.
  / out of scope: edges that point at the split PARENT itself (#499 — different case);
  changing what adoption adopts or how children are claimed (#565); the refusal's message
  shape (#589, done); `Stacks on` to a seed child (stays refused); `flow_batch` (CSV) — it has
  no seeds; refactoring `_adoptable`'s reporting.
- **Repro instruction:** On `origin/main`, in `template/` with `PYTHONPATH=src`: in an
  `AdoptRecovery`-style instance, plan parent `500`, accept a split of it into `601`, `602`
  with the production `split.accept` (so `500` is terminal on `split`, children PLANNED); plan
  `810` with `- **Depends on:** 602`. Run `cli._flow(cfg, args(["500", "810"]))` with
  `--no-publish`. Observed: rc 2, stderr names "declared dependency '602' is neither in this
  batch nor an existing COMPLETE bundle", nothing driven.
- **External dependencies:** none
- **Test file:** template/tests/test_flow_adopt_recovery.py (append to `AdoptRecovery`; the C4
  gate reverts only production hunks, so an appended case earns its red). Import modules only
  (the file's docstring rule), never a symbol the fix adds.
- **Citations expected:** Do must cite path:line on the target branch for every change. Peer
  callsite: the lineage reader adoption uses, `_lineage_children` (`flow.py:770-788`) over
  `split.read_lineage`, and the walk-through rule `_is_split_parent` — reuse those, silently,
  rather than `_adoptable` (which reports) or a new parser.
- **Prior-art check (triage cycles):** merged history by path —
  `git -C ../pdca-harness log --oneline origin/main -- template/src/pdca_harness/waves.py`:
  `bad66f2 flow: refuse an unschedulable dependency graph with rc 2, no traceback` (#589 — the
  message, not the cause), `54a35f6` / `5214d77` (#191 tolerant resume path), `f19a663` /
  `c9f1d55` (#171 archived deps). `flow.py`: `96c9704 feat(flow): drive a split's children in
  the run that split them` (#469), `389bf1a` (#473 recovery). None relaxes the strict check for
  seed children. Closed-unmerged PRs touching `flow.py`, `waves.py`, `integrate.py`,
  `merge.py`: none (INTEGRATION §5 command, empty output). Open PRs: none.
- **Disposition hint:** likely-fix

Plan-review response: all six findings taken. The offered names come from a quiet walk over `split.read_lineage` + `_lineage_children` (not `_adoptable`, which prints); "offered" is defined as in-flight, briefed lineage children, and a terminal-not-COMPLETE child stays refused up front (case a); the offered-then-not-taken path is named correctly (`_runnable` skip or `_reschedule` hold) and tested (case b); `Stacks on` to a seed child stays refused; the change is an optional keyword on `check_dep_graph` / `compute_waves` passed only by the strict call in `_drive_and_act`; the expected `waves_driven` is stated exactly.

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: The fix is sound (no defect found, all gates green), but three behaviours it touches have no test in the patch. Keep the production change as is and add these cases to template/tests/test_flow_adopt_recovery.py (AdoptRecovery, through cli._flow, --no-publish): 1. Dependency loop through an offered seed child (e.g. 810 Depends on: 602, 602 Depends on: 810, with 500 split into 601/602). Pre-patch this was refused up front with rc 2; post-patch it passes the strict check and the tolerant re-level holds both. Pin the current behaviour: no traceback, neither 602 nor 810 driven, both still PLANNED, stderr names the held ids. This is a deliberate behaviour change and needs a test. 2. `Stacks on: <seed child>` stays refused up front: rc 2, nothing driven (include a mixed Depends on + Stacks on declaration). 3. `Depends on (merged): <seed child>` resolves like `Depends on`: waves_driven == [["issue_601"], ["issue_602"], ["issue_810"]]. The reviewer already confirmed 2 and 3 by hand (reviewer-boundaries.log); they only need to be committed as tests.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  The fix is sound (no defect found, all gates green), but three behaviours it touches have no test in the patch. Keep the production change as is and add these cases to template/tests/test_flow_adopt_recovery.py (AdoptRecovery, through cli._flow, --no-publish):
  1. Dependency loop through an offered seed child (e.g. 810 Depends on: 602, 602 Depends on: 810, with 500 split into 601/602). Pre-patch this was refused up front with rc 2; post-patch it passes the strict check and the tolerant re-level holds both. Pin the current behaviour: no traceback, neither 602 nor 810 driven, both still PLANNED, stderr names the held ids. This is a deliberate behaviour change and needs a test.
  2. `Stacks on: <seed child>` stays refused up front: rc 2, nothing driven (include a mixed Depends on + Stacks on declaration).
  3. `Depends on (merged): <seed child>` resolves like `Depends on`: waves_driven == [["issue_601"], ["issue_602"], ["issue_810"]].
  The reviewer already confirmed 2 and 3 by hand (reviewer-boundaries.log); they only need to be committed as tests.
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
