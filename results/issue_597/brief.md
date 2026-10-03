# Brief — issue 597 / flow-never-drives-a-briefless-bundle

> The Plan artifact (docs 02 §PLAN). Do reads ONLY this file.

- **Slug:** flow-never-drives-a-briefless-bundle
- **Defect:** `pdca flow <ids>` crashes with `FileNotFoundError: …/issue_N/brief.md` when one
  of the ids is a split parent whose split was accepted **before #481**. How the disk gets
  there: an iterate-to-Plan archived the parent's brief to `iteration-vN/brief.md`; the split
  was accepted afterwards; before #481 `split --accept` wrote no replacement brief. So the
  parent has `close-disposition` = `split` and no `brief.md`. `state.state` checks the close
  marker before the brief (`template/src/pdca_harness/state.py:351`), finds no
  `check-gates.json`, and returns BUILT (`state.py:367-368`). BUILT is neither UNPLANNED nor
  terminal, so `flow.flow_ids` puts it in the drive set (`flow.py:2064-2104`); the same goes
  for the `--from-csv` sweep (`flow.py:1925-1930`) and for split adoption, which filters a
  child the same way (`flow.py:1105-1108`). The first brief read then crashes the whole run
  before any bundle is driven: `_drive_and_act` → `_point_at_integration` (`flow.py:1768`,
  `:694-706`) → `publish._resolve_target` (`publish.py:548`) → `brief.repo_target`
  (`brief.py:324`) → `brief.parse_fields` (`brief.py:23`) → `FileNotFoundError`. Found on
  getwyrd/wyrd-pdca (bundle issue_654).
- **Success criterion:** With the patch:
  (i) **A pre-#481 split parent is repaired at intake, then driven.** Given a split parent
  with `close-disposition` = `split`, no `brief.md`, and an authored iterate-to-Plan archive
  (`iteration-vN/brief.md`), `pdca flow <parent-id>` (through `cli._flow`) does not raise. Before
  the bundle enters the run — and only **after this run holds its claim** (see (iii)) —
  `<parent>/brief.md` is written, **byte-identical** to what
  `split --accept` writes for the same parent since #481 (`split._split_parent_brief`
  applied to `split._parent_plan`'s result, `split.py:937-939`; the child list is
  `[cfg.bundle(c).name for c in <lineage children>]` — bundle NAMES such as `issue_701`, in
  lineage record order, read with `flow._lineage_children` (`flow.py:736-752`); the lineage
  stores bare ids, `split.py:707`, so passing them unconverted breaks byte-identity), and one
  stderr line names the bundle and says its brief was rebuilt from `iteration-vN/brief.md`.
  **Observable end point:** the same test builds a control parent with the post-#481 disk
  (`split.accept`, brief left in place) and drives it the same way; the repaired parent's
  entry in the `cli._flow` results map and the call's exit code equal the control's. Do
  records the actual state reached (expected AWAITING_SIGNOFF or a terminal state with stub
  leaves and `no_publish=True`) in build-notes. Only **non-terminal** bundles (ones that
  would enter the drive set) are repaired: a briefless split parent that is already
  terminal (handed on as an adoption seed, `flow.py:2075-2102`, or walked by `_adoptable`,
  `flow.py:1109-1117`) is never written to.
  (ii) **No usable source → skipped, not crashed.** With no archive, an archive
  `_parent_plan` refuses (unfilled required field, unreadable), **or a lineage record that
  is missing, unreadable, or yields no children** (`flow._lineage_children` returns `[]`,
  `flow.py:747-752`), no `brief.md` is written, the
  bundle is NOT driven, one stderr line names it and says why and what to do (the
  `SplitError` text already carries the remedy, `split.py:806-833`), its claim is released
  (as the other intake skips do, `flow.py:2072-2073`), and every other bundle in the batch is
  still driven. Through `flow_ids` it still gets an entry in the results map (#468: every
  named id is answered for), so the run's exit code is non-zero.
  (iii) **Every intake path.** (i) and (ii) hold for a named id (`flow_ids`), for the
  `--from-csv` sweep (`flow_batch`), and for a split child reached through adoption
  (`_adoptable`). **The repair runs only after the claim succeeds** (#565): for named ids
  the claim is already taken before `flow_ids` (`cli.py:602-615`); in the sweep the repair
  must come after `_claim_swept` (`flow.py:1939-1940`), not in the state filter before it
  (`:1929-1934`); in adoption, after the adopted child is claimed. A bundle this run cannot
  claim (another live run holds it) is excluded as today and **never written to** — a test
  holds the bundle with another claim on the sweep path and asserts no `brief.md` appears. Any other bundle with no `brief.md` that is past Do (a close marker or
  `patch.diff`, but not a split parent) is skipped as in (ii) — never driven.
  (iv) **Nothing else changes.** A bundle that has its own `brief.md` is never rewritten
  (byte-identical before/after). A briefless split parent that is already terminal is not
  written to (tested). `state.state` is unchanged. The whole `template/tests`
  suite stays green.
  Shown by the named test going red on `main` (`FileNotFoundError` out of `cli._flow`) and
  green with the fix.
- **Falsifiability:** RED is reachable offline on the base toolchain (stdlib Python ≥ 3.11 +
  git), stub leaves, empty gates, no tracker. Build the pre-#481 disk with production code:
  run `split.accept` on a parent whose brief was archived to `iteration-v1/brief.md` (the
  setup in `tests/test_split.py:1782-1840`), read the `brief.md` it wrote (the expected bytes
  for (i)), then delete it — that is exactly the disk a pre-#481 accept left. On `main`,
  `cli._flow(cfg, args)` over that parent raises `FileNotFoundError`. Fixture shape for the
  flow side: `tests/test_flow_adopt_recovery.py:47-66` (`_stub_config`) and `:135-146`
  (`_args`/`_cli`, `no_publish=True`).
- **Invariant to restore:** The flow never drives a bundle that has no Plan artifact: every
  bundle that enters a run's drive set — named, swept, or adopted — has a `brief.md` at the
  moment it enters. Source: internal project rule (Tier C) — #481's "a terminal bundle needs
  a Plan artifact" (`split.py:784-803`), and the intake filters' own contract that a bundle
  with no brief is named and skipped, never driven (`flow.py:2068-2074`, `:1105-1108`). Self-
  test: guarding the one crashing read (`_point_at_integration`) does not satisfy this — the
  bundle would still be driven briefless into Check, sign-off and publish, which all read the
  brief.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Ordering note:** No `Depends on` / `Conflicts with`: this batch (582, 589, 593, 597) runs
  as ONE wave (the v0.58.0 instance driver carries #593's multi-wave stacking bug). 597 is the
  only bundle in the batch that edits `flow.py`'s intake (`flow_ids`, `flow_batch`,
  `_adoptable`). 593 also edits `flow.py`, but only the one fold call (`flow.py:1844`,
  passing its new `folded_this_run` keyword) — far from these intake hunks, so they fold
  cleanly.
- **Surfaces:** data
- **Difficulty:** medium
- **Scope:** Close the gap at intake: a bundle with no `brief.md` never reaches the drive set;
  a split parent left briefless by a pre-#481 accept gets the brief `split --accept` would
  have written, from the same source and by the same code (reuse — do not re-implement —
  `split._parent_plan` / `split._split_parent_brief`); everything else briefless is skipped
  with a message. All three intake paths, one shared rule. / out of scope: changing
  `state.state` (it correctly reads such a bundle as past Do, #481); changing
  `split --accept` itself; making `_point_at_integration` / `publish` tolerate a missing brief
  (that would drive a briefless bundle further, not stop it); repairing other kinds of damaged
  bundles (corrupt briefs) beyond the skip in (ii); writing a brief into a terminal bundle.
- **Repro instruction:** As in Falsifiability: parent `issue_654` with `iteration-v1/brief.md`
  (authored: Slug, Success criterion, Repo + branch target filled), a `split-proposal.md`
  with two children; `split.accept(parent, ["701", "702"], cfg)`; delete
  `issue_654/brief.md`; call `cli._flow(cfg, SimpleNamespace(issue_ids=["654"], from_csv=None,
  from_briefs=None, no_publish=True, no_act=True, by="", lanes=None, max_passes=None))`. On
  `main`: `FileNotFoundError: …/issue_654/brief.md` from `brief.parse_fields`.
- **External dependencies:** none
- **Test file:** `template/tests/test_flow_briefless_split_parent.py` (new). Import modules
  only (`from pdca_harness import cli, flow, split, state, …`), never a symbol the fix adds:
  the C4 red leg reverts production hunks, and a module that fails to import is reported
  PDCA-UNVERIFIABLE, not red. Cover (i) with the byte-identical brief and the control-parent
  end point, (ii) no-archive, refused-archive and missing/empty lineage, (iii) the
  `--from-csv` sweep, the adoption path, and a bundle held by another claim (not written),
  and (iv) a bundle with its own brief left untouched and a terminal briefless split parent
  left untouched.
- **Citations expected:** Do must cite path:line on the target branch for every change. Peer
  callsite to mirror for building the brief: `split.accept`, `split.py:937-939`
  (`plan = _parent_plan(parent, cfg)` then `_split_parent_brief(parent, plan, [child bundle
  names])`) and `:1004-1008` (the write, last before the marker). Peer for the skip message + claim release:
  `flow_ids`' no-brief skip, `flow.py:2068-2074`. Peer for reading the child list:
  `flow._lineage_children` (`flow.py:736-752`) over `split.read_lineage`.
- **Prior-art check (triage cycles):** Merged history by path —
  `git -C ../pdca-harness log --oneline origin/main -n 5 -- template/src/pdca_harness/flow.py`:
  `1bc12a5` (#409), `f81c4a0` (#566), `fe8208f` (#565), `51a65a2`, `389bf1a` (#473) — none
  touch the briefless-past-Do case. `split.py`: `5ced9bd`/`a30e0c4` (#481, merged as PR #561)
  fixed the cause for NEW accepts only; this is its leftover for disks written before it.
  Closed-unmerged PRs touching `flow.py`/`split.py`: #598, #599, #600 (auto-iterate / gate
  re-run / size-signal — unrelated). No open PR. The fix is carried downstream on
  getwyrd/wyrd-pdca as an instance delta. Result: not fixed upstream, not in flight.
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.

Plan-review response: all five findings accepted — repair only after the claim (sweep and
adoption ordering stated, held-bundle test added); child list given as bundle names via
`_lineage_children`; unusable lineage folded into (ii) and tested; (i)'s end point made
observable with an in-test control parent; repair limited to non-terminal bundles, tested.

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: The fix itself (intake admission after claim, rebuild via split._parent_plan / _split_parent_brief, skip-with-message otherwise) was accepted — keep it. Rebuild only to clear the four code-review points: 1. flow.py:1020 — drop the dead `plan is None or` condition (_parent_plan returns None only when brief.md exists, already handled at the top), so the lineage-blaming message can only fire for a missing/empty lineage. 2. flow.py:1017 — the skip message pastes SplitError text ("refusing to split", "then re-run: a parent with its own brief.md keeps it") into a flow run, then adds a second remedy. Give it a flow-side lead-in / one clear remedy so it reads right in `pdca flow`. 3. test_flow_briefless_split_parent.py:266 — `assertIsInstance(rc, int)` can never fail; compare the sweep's rc against a control (as the named-id test does) or remove it. 4. test_flow_briefless_split_parent.py:237 — claim release on a skipped bundle is tested only via flow_ids; add tests that another run can claim the bundle after the sweep (flow_batch, flow.py:2030) and adoption (flow.py:1397) paths skip it.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  The fix itself (intake admission after claim, rebuild via split._parent_plan /
  _split_parent_brief, skip-with-message otherwise) was accepted — keep it. Rebuild only to
  clear the four code-review points:
  1. flow.py:1020 — drop the dead `plan is None or` condition (_parent_plan returns None only
     when brief.md exists, already handled at the top), so the lineage-blaming message can only
     fire for a missing/empty lineage.
  2. flow.py:1017 — the skip message pastes SplitError text ("refusing to split", "then
     re-run: a parent with its own brief.md keeps it") into a flow run, then adds a second
     remedy. Give it a flow-side lead-in / one clear remedy so it reads right in `pdca flow`.
  3. test_flow_briefless_split_parent.py:266 — `assertIsInstance(rc, int)` can never fail;
     compare the sweep's rc against a control (as the named-id test does) or remove it.
  4. test_flow_briefless_split_parent.py:237 — claim release on a skipped bundle is tested only
     via flow_ids; add tests that another run can claim the bundle after the sweep
     (flow_batch, flow.py:2030) and adoption (flow.py:1397) paths skip it.
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
