# Brief — issue 395 / same-wave-conflict-refused-at-accept (re-plan after iteration 9, to be SPLIT)

> Plan artifact. Re-planned 2026-10-27 after the iteration-9 sign-off (iterated-to-Plan).
> This parent brief is split into three children (see "Intended split"). Each child brief
> is what Do reads; this file records the whole design and the human's rulings.

## Rulings carried forward

- 2026-10-25: **every accepted bundle ends in a PR.** The conflict is found BEFORE accept; a
  bundle that would conflict is never accepted. Do NOT rebuild the iteration-1..5 "hold
  after accept" design (`conflict-hold.json`, a held COMPLETE bundle with no PR).
- 2026-10-23 (v9 sign-off): keep the hold-count rule ("a conflict" = the accepted siblings
  plus the candidate, folded in name order, make the fold hold more bundles than the
  accepted siblings alone); the conflict-row override loophole is accepted; the
  split-during-last-wave case is a follow-up.
- **2026-10-27 (this Plan): check-failure policy.** When the accept-time check cannot
  complete (it cannot run, or it breaks the shared integration worktree), the accept is
  REFUSED. A tick on that row means "retry the check", never "publish anyway": the next
  accept runs the check again, and if it fails again the row is re-opened unticked. There
  is NO shared-path fallback (the iteration-6..9 "refuse only if it shares a file" rule is
  dropped). Row keys never include the free-text error cause.
- **2026-10-27 (this Plan): split three ways** (below), not "detected vs check-failure":
  check-failure handling is small once the refusal exists, and splitting it off would force
  the core to pick an interim failure policy — the gap that sank v9.

- **Slug:** same-wave-conflict-refused-at-accept
- **Kind:** enhancement
- **Goal:** In a `pdca flow` run in stack mode, in a wave the fold runs after
  (`k < len(wave_list) - 1`, `do_publish`, publisher not `stub`, not a dry run — the
  condition of the fold's non-dry `held_out`, flow.py:3108-3118), a bundle is not accepted
  if its branch would textually conflict with an already-accepted bundle of its own wave,
  judged by the fold's own #674 rule in the fold's order; nor is it accepted when that check
  cannot complete. The driver refuses such an accept the way C6 refuses one today: the
  bundle stays AWAITING_SIGNOFF with an open §6 row. Siblings are accepted and published as
  before. The last wave, one-wave runs, single-issue `flow`, `--no-publish`, merge mode, dry
  runs and the standalone `pdca signoff --accept` do not change. Partial fix of #395
  (`refs #395`).
- **Defect:** see the issue: two real batches published same-wave PRs that conflict, found
  only at the post-publish fold.
- **Success criterion:** the union of the three children's criteria (each child is
  self-contained and gate-evaluable on its own).
- **Falsifiability:** per child. All three go RED on the offline driver suite with real git
  (`StackFoldGit` fixture, `template/tests/test_integrate_stack_bases.py`) or plain unit
  fixtures; no network.
- **Invariant to restore:** In a `pdca flow` run, an accepted (COMPLETE) bundle is one the
  run can publish without a same-wave textual conflict, and an accept is never granted on a
  check that did not complete. Sources: the human's 2026-10-25 ruling; project CLAUDE.md
  ("On an accept, publish … the driver opens a draft PR"); the C6 accept-guard (an accept is
  refused, never recorded and then undone). Binds every accept route of a flow run (the
  pre-apply at flow.py:2516-2522 and the post-session apply at :2530-2532, both via
  `_apply_decision`, flow.py:134) — not satisfiable by guarding one module.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Depends on:** none
- **Conflicts with:** 464, 740
- **Ordering note:** 464 adds a wave mode that gates the same wave/publish/fold block
  (flow.py:3021-3125). 740 rewrites `docs/07-crosscutting.md:647-735` (the same-wave and
  exit-code paragraphs). Neither is a build-on dependency.
- **Surfaces:** data
- **Difficulty:** high
- **Scope:** see "Intended split". / out of scope: the last wave and one-wave runs;
  re-sequencing a refused bundle into a later wave of the same run and writing
  `Conflicts with` automatically; a conflict that also involves line work (#747
  `_held_by_line`); the issue's layer 1 (Plan-exit advisory over predicted files); the
  standalone `pdca signoff --accept`; merge mode; the advisory `_audit_wave_overlap`
  (flow.py:1586) behaviour beyond child 3's parser fix; documenting "accepted ⇒ PR" with
  its two existing exceptions (T4-failed texts, failed push).
- **External dependencies:** none
- **Test file:** per child.
- **Citations expected:** per child; Do cites path:line on the target branch for every change.
- **Prior-art check (triage cycles):** `git -C ../pdca-harness log --oneline origin/main --
  template/tests/test_flow_same_wave_conflict.py` → 0c263a9 (#674 hold, not stop), 89c2017
  (#727), d51849a (#747); none checks before accept. origin/main `a6af7f3` unchanged on
  flow.py / integrate.py / waves.py / cli.py since iteration 9. Closed-unmerged PRs on
  flow.py / integrate.py (#638, #639, #648, #649, #598, #599, #600) were all carried by
  #657/#615. This bundle's iterations 1–9 are the prior attempts (1–5 rejected design;
  6–9 this design, rejected on implementation gaps the rulings above now close).
- **Disposition hint:** new-feature

## Intended split

1. **Child A — standalone sign-off consumes a stale recorded decision.** `cli._signoff`
   (cli.py:1504; records at :1530) never deletes `signoff-decision`, while
   `flow._apply_decision` does (flow.py:205). A later flow run's pre-apply
   (flow.py:2516-2522) can then apply an old `accept` to a re-planned, rebuilt bundle with no
   review. A defect on `main` today for any C6-refused bundle. Low difficulty, independent.
2. **Child B — `waves.diff_files` misreads Git-quoted paths.** `_DIFF_GIT_RE`
   (waves.py:329) / `diff_files` (:332) take `"a/caf\303\251.txt"` literally, so the
   advisory `_audit_wave_overlap` (flow.py:1586-1592) misses overlaps on non-ASCII /
   special-character paths. A defect on `main` today. Low difficulty, independent of the
   core (the core no longer uses a footprint fallback).
3. **Child C — the core: refuse a same-wave conflicting accept, and refuse on a check that
   cannot complete.** Depends on child A (its re-plan-and-re-run leg relies on the stale
   decision being consumed). Legs (a)–(d), (f)–(h) of iteration 9, the in-session
   iterate-plan parked to the next run (iteration 8), the iteration-6 fixes (count a session
   only after it returns; reset the session count per run instead of deleting the record;
   chain errors), and the 2026-10-27 check-failure policy with its own legs. High
   difficulty.

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.
