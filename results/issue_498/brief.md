# Brief — issue 498 / one-live-driver-per-bundle-and-an-honest-split-hint

> The Plan artifact (docs 02 §PLAN). Do reads ONLY this file.
> **This slice is split in this Plan beat** (iteration 3, after `iterate-plan`) into two
> children — see `split-proposal.md`: child-1 the drive claim (one live driver per bundle),
> child-2 the honest split hint, which depends on child-1. This brief is the parent's record
> of the whole re-planned outcome; the children are what gets built.

- **Slug:** one-live-driver-per-bundle-and-an-honest-split-hint
- **Defect:** Two linked problems.
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
- **Success criterion:** Through the CLI entry points (`cli._flow`, `cli._split`):
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
- **Falsifiability:** RED is reachable offline on the base toolchain (stdlib Python ≥ 3.11
  + git) with stub leaves and empty gates: `template/tests/test_flow_adopt_split.py:43-63`
  (`_stub_config`) already drives real `cli._flow` runs, and `:190-216` swaps a stub leaf for
  a stand-in that acts mid-run. v2's suite showed 17 of 22 tests red on the base for real
  reasons (a second process drove a held bundle; the in-flow accept printed the
  instruction). Each child's brief names its own red leg.
- **Invariant to restore:** At most one live driver advances a given bundle at a time, and
  a claim lives exactly as long as the run that took it; the driver never tells the
  operator something about a live run that the run cannot guarantee. This holds for every
  CLI drive path (named ids, CSV batch, split adoption), not only the split-hint case.
  Source: internal project invariant (Tier C) — the target states bundle state is only the
  files in the bundle (`template/CLAUDE.md.jinja:13-14`, "nothing is hidden in a
  database"), so two writers have nothing to serialize on; Act's session lock states the
  same rule for its resource (`act.py:125-141`). `docs/principles.md` §5/§6 are unfilled in
  this instance, so no §6 category gate applies; treated as structural (process lifetime /
  ownership), so the Plan-exit gate was applied: Scope names no mechanism, and guarding
  `cli.py`'s hint alone cannot satisfy the invariant.
- **Repo + branch target:** eduralph/pdca-harness @ main (base `70ea12b`, unchanged since
  iteration 2; every `path:line` here re-verified against it on 2026-09-19)
- **Depends on:** none
- **Conflicts with:** none
- **Ordering note:** The parent is split, not built. child-2 declares `Depends on: child-1`
  (it reads child-1's claim to decide what to print, and both edit `cli.py` / `flow.py`),
  so the run adopting them puts child-2 in a second, stacked wave. This instance's driver is
  rendered v0.57.0, where a stacked bundle can show a false advisory T3 red (#474, fixed
  upstream, not here): read child-2's T3 row with that in mind. #496 (test-only pin of "a
  split never aborts the flow") runs after both children land.
- **Surfaces:** data
- **Difficulty:** high — changes who may drive a bundle across every CLI drive path
  (`flow_ids`, `flow_batch`, `_adopt_split_children`), the accept path in `cli.py`, the
  end-of-run reporting in `_drive_and_act`, and model-facing text in three places.
- **Scope:** One outcome split into two children: make bundle ownership by a live run
  exclusive for the life of the run (child-1), then make `split --accept`'s closing line and
  the run's end-of-run report honest about what a live run will and will not drive
  (child-2). / out of scope: `pdca run` / `signoff` / `publish` and other single-step verbs;
  the library-only `flow.flow()` (`flow.py:379`); lane and worktree locks (`lane.py`,
  `worktree.py`); the adoption algorithm itself; the Plan session's own writes (a CSV batch's
  Plan session runs before any claim — a known gap, documented, not fixed); cross-host
  coordination; Windows beyond not breaking import.
- **Repro instruction:** On `eduralph/pdca-harness@70ea12b`, from `template/`: (a) pause a
  stubbed `cli._flow` run over 7 inside a leaf and start a second `cli._flow` over 7 in
  another process — it drives 7 to COMPLETE while the first still holds it;
  `grep -n "lock" src/pdca_harness/flow.py src/pdca_harness/driver.py` finds no ownership
  check. (b) With `tests/test_flow_adopt_split.py`'s stub fixture, make 500's stand-in Plan
  leaf call `cli._split(cfg, SimpleNamespace(issue_id="500", accept=True, ids="601,602"))`
  inside a `cli._flow` run over 500: stderr carries `issue_500 marked split; run \`… flow
  601 602\` to drive the children` while the same run then drives 601 and 602 itself.
- **External dependencies:** none — the base toolchain (Python ≥ 3.11, git) suffices;
  stub leaves, no vendor CLI, no network.
- **Test file:** `template/tests/test_flow_single_driver.py` (new, child-1) and
  `template/tests/test_split_hint_live_run.py` (new, child-2).
- **Citations expected:** Do must cite `path:line` on the target branch for every change.
  Peer to mirror for the claim: `act.act_session` (`template/src/pdca_harness/act.py:125-159`)
  with the cross-platform `_lock_exclusive` / `_unlock` helpers (`act.py:29-62`). Each child
  brief carries its own citations.
- **Prior-art check (triage cycles):** `git -C ../pdca-harness log --oneline origin/main -n 6
  -- template/src/pdca_harness/cli.py template/src/pdca_harness/flow.py` → `6ddfca4` /
  `51a65a2` (#475), `9a19cb5` (#466), `a2eefe1` (#459), `389bf1a` / `96c9704` (#469/#473) —
  none adds drive ownership or conditions the closing instruction. Open PRs touching
  `cli.py` / `flow.py` / `split.py`: none. Closed-unmerged PRs touching them or a
  `drive_claim` module: none. Tracker search "drive claim OR concurrent flow OR lock
  bundle": #130 (closed; git maintenance under a live flow — the harness checkout, a
  different resource), #452 (open; setup validation, unrelated). Own prior attempts:
  `iteration-v1/`, `iteration-v2/` of this bundle (lock half accepted as sound; hint half
  sent back to Plan).
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.
