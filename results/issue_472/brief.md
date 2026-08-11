# flow: adopt split children mid-run — the adoption core on the unified drive path

- **Slug:** flow-adopt-core
- **Kind:** enhancement
- **Defect / goal:** a split that happens inside a driven flow strands its own children
  (tracker #449 → #469): the parent goes terminal (`close-disposition = split`), the
  children materialise fully briefed, and the run never drives them — the operator
  restarts by hand with `pdca flow <child-ids>`. #469 v3 built and converged the full
  adoption feature but was split on the size backstop; this child re-lands the **mid-run
  adoption core** — detect / validate / splice / report on the unified single drive path
  (#468) — by CARVING it out of the converged v3 patch
  (`results/issue_469/iteration-v3/patch.diff`; 26-test suite preserved at
  `results/issue_469/test_flow_adopt_split.py`), not re-deriving it. Terminal-parent
  recovery and the operator-facing reporting/budget refinements are the sibling child's.
- **Success criterion:** exercised **through `cli._flow`** on byte-identical disk state:
  a run whose Plan/re-plan beat splits a drive-set bundle drives that bundle's children
  to a terminal state within the same call — in a wave AFTER the parent's, honouring
  their `Depends on` / `Conflicts with`, counted against ONE run-wide `max_passes`
  budget across original AND adopted waves (pool sized off the pre-adoption schedule —
  the converged v3 mechanics; live re-sizing is the sibling child's), each adoption
  announced on stderr with the child's REAL wave index from the recomputed schedule. A
  child with an unresolvable dependency is held loudly in the existing held-report
  shape, excluded from the results map, and the run continues — never aborts. Adoption
  is lineage-scoped and transitive (only descendants of the ids given), never a disk
  sweep; an adopted child that itself splits is re-adopted within the same shared budget
  — bounded, no recursion reset. Guards proven by test, not just present: a split-marked
  but NON-terminal parent (e.g. sign-off recorded `iterate-do`) does NOT have its
  children adopted; a parent whose lineage record is unreadable is reported and skipped,
  never a crash; a lineage child id that escapes the bundle root (e.g. `"../../etc"`) is
  skipped with a report; an id already in the run's drive set is not adopted twice —
  dedup against the batch, against a duplicate id within one record, AND against a child
  already taken by another parent adopted in the SAME wave (two parents splitting in one
  wave, the second's record also naming the first's child — the #469-v3 adversary's
  unpinned-`taken` mutation; the docstring's test citation must name this test).
  Demonstrable by C4-verify on the patch alone.
- **Falsifiability:** RED on the offline driver suite — `cd template && PYTHONPATH=src
  python3 -m unittest tests.test_flow_adopt_split`, the invocation
  `engine/scripts/run-verify.sh` uses for a `template/tests/*.py` test. With all six
  leaves stubbed (fixture shape at `template/tests/test_flow_slice.py:33`,
  `_stub_config`), a leaf patched to split the parent mid-run, and the fixture built
  with the production `split.accept` (`split.py:525`): pre-fix (post-#470 `main`, no
  adoption) the children stay PLANNED after the call returns — `_drive_and_act` computes
  `wave_list` once (`flow.py:868` on the #468 branch) and the drive set is built once —
  so assertions that children reached COMPLETE fail; post-fix green. The guard tests are
  red pre-fix by the same route. No tracker, network, `gh` or container.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Depends on (merged):** 468
- **Ordering note:** builds on #468's unified results-map drive path — adoption is
  implemented once on the shared path so `flow_batch` and both `flow_ids` shapes inherit
  it from one implementation; landing it on forked entry points is what produced #449's
  five-iteration divergence chase. 468 is COMPLETE but out-of-batch and its PR #470 is
  unmerged; per the driver's #186 rule nothing carries an out-of-batch prereq's diff
  into the base, so the merged-gate is the correct field: merge PR #470, then drive.
- **Surfaces:** data
- **Difficulty:** high — the adoption splice lives inside `_drive_and_act`'s run-scoped
  wave/fold/integration state, the most load-bearing loop in the driver; a reviewer must
  hold the wave/fold/publish/budget interaction in view.
- **Scope:** adopt the children of a bundle that goes `close-disposition = split` while
  in the drive set — detect (read `split.read_lineage`; a parent with the marker but no
  readable record is reported and skipped, never a crash), validate
  (`waves.partition_schedulable` tolerance; held children reported in the existing
  "held this run — <reason>; left in-flight" shape and EXCLUDED from the results map),
  splice (children join after the current wave; pointed at the same per-target
  integration branch via the existing `_point_at_integration`; one run-wide `max_passes`
  pool across original AND adopted waves, sized as converged in v3; adopted children
  join the set `_warn_abandoned` / final sweep cover), report (stderr announcements
  with real wave indices) — on the unified drive path, so every CLI shape inherits it
  from one implementation. Includes the same-wave two-parents dedup test (v3 carry-
  forward 3) and the corrected docstring citation, and the ancillary
  `template/tests/test_verify_base.py` environment cleanup the v3 review accepted as
  discharging an iteration carry-forward, not scope expansion.
  / out of scope: **terminal-parent recovery** (a run handed an id ALREADY terminal on a
  split — the pre-run short-circuit stays for now; sibling child) and **shape-parity
  assertions against that recovery path**; **single-id stdout reporting of adopted
  dispositions** and **budget re-sizing on adoption** (sibling child); changing why
  recursive splits happen (#448's line — merely never enable an infinite one); a disk
  sweep in `flow_ids` (the distinction from the CSV sweep is deliberate and stays); the
  `--accept` hint printing `pdca flow <child-ids>` (still right for a split accepted
  outside a running flow); `waves.compute_waves` / `partition_schedulable` semantics
  (reused as-is); the split command, `split.accept`, or the lineage schema (#456 shipped
  it); publish/fold semantics beyond the existing reconciliation.
- **External dependencies:** none — python3 ≥ 3.11 stdlib + git only; offline driver
  suite with stubbed leaves, no tracker, network or container.
- **Test file:** `template/tests/test_flow_adopt_split.py` (new module; the mid-run and
  guard subset of the preserved 26-test v3 suite — drive **through `cli._flow`**, build
  fixtures with the production `split.accept` — PLUS the same-wave two-parents dedup
  test the v3 adversary showed missing: mutation `known=batch_names | taken` →
  `known=batch_names` must fail it). The C4 gate reverts only the PRODUCTION hunks and
  keeps the test (`engine/scripts/run-verify.sh`, `--exclude=template/tests/*`).
  **Import modules, never new symbols** (`from pdca_harness import cli, flow, split,
  state, waves`; reach new names as attributes) — a named import of a new helper is
  ImportError on the red leg → PDCA-UNVERIFIABLE (exit 77), not red.
- **Citations expected:** Do must cite `path:line` on the merged base (post-#470 `main`;
  line numbers below verified on `origin/enhancement/468-flow-entrypoint-parity` and
  identical after a clean merge): `flow.py:845` (`_drive_and_act`; `wave_list` once at
  `:868`; `_point_at_integration` call at `:899`), `flow.py:630`
  (`_point_at_integration`), `flow.py:668` (`_TERMINAL`), `flow.py:731`
  (`_warn_abandoned`), `flow.py:1039` (the held-report shape to mirror), `flow.py:997`
  (`flow_batch`), `flow.py:1052` (`flow_ids`); `waves.py:104` (`conflict_map`), `:140`
  (`compute_waves`), `:240` (`partition_schedulable`); `state.py:44` (`CLOSE_MARKER`);
  `split.py:47` (`LINEAGE`), `:373` (`read_lineage`), `:525` (`accept`). **Peer
  callsites to mirror, not re-derive:** the held-report at `flow.py:1039`;
  `_point_at_integration` at `flow.py:630` (adopted children join the same `(repo,
  base)` integration branch through this call, not a second mechanism);
  `_warn_abandoned`'s not-terminal predicate at `flow.py:731`;
  `template/tests/test_flow_slice.py:33` for the offline fixture. **Reference
  implementation to carve from:** `results/issue_469/iteration-v3/patch.diff` and the
  preserved suite `results/issue_469/test_flow_adopt_split.py`.
- **Disposition hint:** new-feature

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: Auto-iterate (round 1): rebuilding for the implementation-level findings — T4 Contribution — The contribution-text decision remains owed — `commit-msg.txt` and `pr-description.md` were not supplied, so the asserted checker pass cannot be independently rerun and release-facing impact text remains unaudited.; `config.py:312-314` now states an invariant the patch breaks:; `template/tests/test_flow_adopt_split.py:821`; `flow.py:894` and `flow.py:898`: both `_adoptable` guards are unpinned.. 2 finding(s) needing human judgment were deferred to sign-off, not addressed here.
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).

## Iteration 2 — carry-forward (from the previous attempt)
- Sign-off rationale: Auto-iterate (round 2): rebuilding for the implementation-level findings — T4 Contribution — The release-text decision remains owed — `commit-msg.txt` and `pr-description.md` were not supplied, so the recorded checker pass cannot be independently rerun and the user-impact opener plus #472 linkage remain unaudited.; `flow.py:975` (and the same claim at `flow.py:948-950`) states an; `config.py:312` cites `config.py:671` for the clamp. 4 finding(s) needing human judgment were deferred to sign-off, not addressed here.
- Full previous attempt preserved in `iteration-v2/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).

## Iteration 3 — carry-forward (from the previous attempt)
- Sign-off rationale: Auto-iterate (round 3): rebuilding for the implementation-level findings — C5 Causal adequacy — Rebuild decision: make lineage containment resolution-aware—the lexical `d.parent` check accepts an `issue_<id>` symlink resolving outside the bundle root, and my probe returned that external target as adoptable, so the escape guard is incomplete (`template/src/pdca_harness/flow.py:881`).; T4 Contribution — Release-text approval is still owed—`commit-msg.txt` and `pr-description.md` were not supplied, so the user-impact opener and #472 linkage required by the contribution rule cannot be independently audited (`template/pdca.toml.jinja:960`).. 4 finding(s) needing human judgment were deferred to sign-off, not addressed here.
- Full previous attempt preserved in `iteration-v3/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).

## Iteration 4 — carry-forward (from the previous attempt)
- Sign-off rationale: Rejected on the round-3 adversary's implementation findings; the core mechanism is converged and must not be re-derived — fix narrowly: 1. `flow.py:914` (with `:696`): a lineage record whose `children` array holds a non-string entry (e.g. `[601, "602"]`) drops that child SILENTLY — never adopted, never named on stderr, run exits 0 with the child left PLANNED. Every neighbouring malformed-id class is loud; make `_adoptable` count/report the entries `_lineage_children` refused, and pin it with a `_record(iid, [601, "602"])` test. 2. `flow.py:775`: `_report_held`'s docstring claims unconditionally "a held bundle is never counted as work the run did", contradicted by the named-id case at `flow.py:1305` (PLANNED in the results map, rc=1). Scope the docstring to the child-only case. 3. `flow.py:849`: an in-flight `issue_<id>` symlink aliasing another named, un-driven bundle inside the root gets one directory driven as two bundles in the same wave (two lanes writing one dir under lanes>1). Close it with the cheap resolved-path dedup in `_adoptable` — not the wider re-keying of the drive set by resolved path.
- Full previous attempt preserved in `iteration-v4/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
