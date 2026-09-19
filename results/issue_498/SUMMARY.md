# Result — issue 498 / one-live-driver-per-bundle-and-an-honest-split-hint

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: Two linked problems.
  (a) **Nothing stops two drivers from holding the same bundle.** No drive-path code takes
  any ownership of a bundle; the only cross-process claim in the driver is Act's session
  lock (`template/src/pdca_harness/act.py:125-159`). Bundle state is plain files in
  `results/issue_<id>/`, so two `pdca flow` runs over overlapping ids write the same
  artifacts with no ordering — reachable with or without the hint below.
  (b) **The split hint is wrong inside a flow.** `pdca split <id> --accept` always ends
  with `"<parent> marked split; run `pdca flow <child-ids>` to drive the children"`
  (`template/src/pdca_harness/cli.py:843-844`). Since #469/#473 a run adopts the children
  of a split it is driving (`flow.py:1554`, `_adopt_split_children` `flow.py:1119`; a split
  parent named on an id run is an adoption seed, `flow.py:1784-1797`), and a CSV batch
  sweeps every in-flight bundle after its Plan session (`flow.py:1673-1692`). An operator
  who follows the printed instruction starts a second driver over bundles the first run is
  about to drive.
  Two build rounds proved (a)'s fix sound and failed (b) both times: the v2 criterion asked
  the hint to *promise* the run would drive the children, which nothing at accept time can
  know (the run's sign-off may go unanswered, the parent may sit behind an unready
  prerequisite, or the run may already be past the parent's adoption point).
- Success criterion: Through the CLI entry points (`cli._flow`, `cli._split`):
  **Drive claim (child-1).** (i) While run A (`pdca flow` naming 7) is mid-drive, a run B
  whose named ids include 7 exits non-zero before it changes any bundle's state and names
  `issue_7` as held by another run. (ii) A CSV batch's in-flight sweep and split adoption
  skip a bundle another live run holds, with a line naming it, and carry on. (iii) A's claim
  ends when A returns, raises, or its process is killed. (iv) A run never refuses itself or
  anything it spawns. (v) A claim that cannot be recorded fails closed. (vi) Every claim the
  run takes and then decides not to drive is released at that point, and every release path
  is pinned by a test. (vii) A `pdca flow <id>` resume line the run prints for a bundle it
  still holds says the command applies once this run has ended.
  **Honest hint (child-2).** (viii) When `split --accept` runs while a live `pdca flow` run
  holds the parent — or while a live CSV batch run has not yet swept its in-flight bundles —
  it prints a conditional line in place of today's instruction: it names the children, says
  that run drives them only if it reaches them, and gives `pdca flow <child-ids>` for after
  that run ends; it never promises and never says "do not start another flow". Otherwise it
  prints today's line byte-identical. (ix) At the end of every CLI flow run, every child of a
  split parent the run drove or seeded that is still not terminal and not in the run's drive
  set is named on stderr with a `pdca flow <ids>` command. (x) Checking for a live holder
  never makes a concurrent `pdca flow` refuse a bundle no run holds.
  **Both.** Nothing else changes for a single run with no second driver, and the whole
  `template/tests` suite stays green. The children's briefs carry the exact, testable form
  of each clause.
- Repo + branch target: eduralph/pdca-harness @ main (base `70ea12b`, unchanged since
  iteration 2; every `path:line` here re-verified against it on 2026-09-19)
- Scope (one logical fix) / out of scope: One outcome split into two children: make bundle ownership by a live run
  exclusive for the life of the run (child-1), then make `split --accept`'s closing line and
  the run's end-of-run report honest about what a live run will and will not drive
  (child-2). / out of scope: `pdca run` / `signoff` / `publish` and other single-step verbs;
  the library-only `flow.flow()` (`flow.py:379`); lane and worktree locks (`lane.py`,
  `worktree.py`); the adoption algorithm itself; the Plan session's own writes (a CSV batch's
  Plan session runs before any claim — a known gap, documented, not fixed); cross-host
  coordination; Windows beyond not breaking import.

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — N/A — close disposition (no patch to verify)
- C3 Change: none — patch.diff
- C4 Verification (red→green): none — N/A — close disposition (no patch to verify)
- C5 Causal adequacy: none — reviewer + human sign-off

## 4. Conformance (Check — stack)
- T1 Structure: none — N/A — close disposition (no patch to verify)
- T2 Shape: none — N/A — close disposition (no patch to verify)
- T3 Runtime: none — N/A — close disposition (no patch to verify)
- T4 Contribution: none — N/A — close disposition (no patch to verify)
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

# Advisory review — SKIPPED (close disposition)

The reviewer leaf was skipped: this bundle's Plan concluded a close / no-fix disposition (split), so there is no patch to review.

- NEEDS-HUMAN — Confirm the close disposition 'split' (no patch was built). Override to a fix path (iterate-to-Do) if the close is wrong.


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] Confirm the close disposition 'split' (no patch was built). Override to a fix path (iterate-to-Do) if the close is wrong.

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: merged-wider
- Iteration delta (if iterating):
- By / date: Eduard Ralph / 2026-09-19

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
