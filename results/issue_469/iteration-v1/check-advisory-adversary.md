# Adversarial review — issue_469 (flow: adopt split children mid-run)

Advisory only; gates are elsewhere. Everything below was re-run against
`$PDCA_TARGET` (`/home/eddie/pdca/pdca-harness.pdca-wt`) on faithful copies, never in the
target tree.

## The evidence — re-run, and it holds

- Red leg reproduced: production hunks (`flow.py`, `config.py`, `leaves.py`) reverted to
  `e955b79`, test kept ⇒ **16 of 19 fail**; post-fix **19/19 pass** (0.19 s). The three that
  are green pre-fix are no-regression guards
  (`test_a_named_id_list_keeps_its_strict_scheduling_contract`,
  `test_a_run_that_adopts_nothing_keeps_a_full_budget_per_wave`,
  `test_an_unreadable_close_marker_never_kills_the_run`), so the brief's "the guard tests
  are red pre-fix by the same route" is loose — but the **four guards the brief actually
  names** are all in the red set. C4's `pass` row is earned.
- The suite drives the production path: `cli._flow → flow.flow_ids → _drive_and_act`, with
  `flow._drive_wave` / `_build_all` / `_point_at_integration` wrapped as pass-through spies
  (`test_flow_adopt_split.py:243-255`) and the split produced by the real `split.accept`. No
  parallel re-implementation.
- 15-mutation battery on `flow.py`: **14 caught** (narrowed `except`, dropped path-escape
  guard, dropped record dedup, dropped drive-set dedup, hardcoded `k+1` wave index, per-wave
  budget, held-child-in-results-map, dropped terminal predicate, dropped chain walk, strict
  reschedule, append-instead-of-splice, dropped run-budget break, seeds never examined,
  dropped no-record report). One survived — see below.
- T3's recorded red is **not** this patch: the full driver suite is **1652/1652 green** with
  the patch applied in a faithful repo copy, and `tests.test_verify_base` fails (11/19) only
  when `PDCA_VERIFY_BASE` is inherited — exactly the pre-existing isolation fault the brief
  pre-declared. Not a refutation.

## Refutations

- **NEEDS-HUMAN — `template/src/pdca_harness/cli.py:661` + `flow.py:1009`: adoption breaks
  the CLI-shape exit-code parity the brief makes success criterion (3).** `_report_single`
  applies its `AWAITING_SIGNOFF`-is-OK leniency to the **whole** results map, and #469 has
  now put bundles the operator never typed into that map (`bundles += scheduled`).
  Reproduced on byte-identical disk (500 splits into 601/602; the sign-off session answers
  601 and walks away from 602 — the ordinary end of an interactive run):
  `pdca flow 500` → stdout `COMPLETE<TAB>…/issue_500`, **rc 0**;
  `pdca flow 500 999` (999 already COMPLETE, arity-only change — the exact fixture
  `test_both_cli_shapes_adopt_identically_on_the_same_bytes:427` uses) → stdout lists
  `AWAITING_SIGNOFF 602`, **rc 1**. Pre-patch both shapes returned 0 on that same disk, so
  the divergence is introduced here. The single-id run therefore reports total success on
  stdout *and* in rc while an adopted child sits un-terminal. The suite misses it because the
  only non-finishing parity test, `test_a_refused_adopted_wave_exits_1_at_either_arity:446`,
  picks the one failure path (`PreflightError`) that returns **before** the results map.
  Human call because the remedy touches #468's documented rc rule (restrict the leniency to
  the ids named, or ratify the widening) rather than being a local slip.

- **NEEDS-HUMAN [impl] — `template/src/pdca_harness/flow.py:1287` (`if k < len(wave_list) - 1
  and do_publish:`) is a load-bearing production hunk with zero test coverage.** Every test in
  `test_flow_adopt_split.py` runs with `no_publish=True` (`:158`), so the publish/fold branch
  is dead under the whole new suite. Verified: restoring the pre-patch cached
  `last = len(wave_list) - 1` **survives all 1652 driver tests**, yet on the canonical
  `pdca flow 500` split-and-adopt run with publishing on it takes `integrate.fold` calls from
  `[['issue_500'], ['issue_500','issue_601']]` down to `[]` — i.e. no wave ever folds, `integ`
  stays empty, and every adopted child builds off the unfolded base instead of the run's
  per-target integration branch. Add one adoption test with `no_publish=False` asserting the
  wave-0 fold happens (and, with a non-stub publisher, that adopted children are pointed at
  the integration branch — the present
  `test_adopted_children_go_through_the_same_integration_reconciliation:359` only asserts the
  *call list* under `dry=True`, where `_point_at_integration` can only ever clear a stale base).

- **NEEDS-HUMAN [impl] — `template/src/pdca_harness/flow.py:984` (`if parent.name in
  examined: continue`): the termination bound the docstring claims ("Adoption is bounded — a
  parent is examined once … the queue drains") is the one mutation the suite does not catch.**
  Deleting the `continue` keeps all 1652 tests green, and `cli._flow` then **hangs forever**
  (killed at 45 s) on a lineage record whose `children` edge names an ancestor — 500 split →
  601, 601's hand-edited `split-lineage.json` naming `500` back, driven as `pdca flow 500`.
  The shipped code is correct (the same scenario finishes in <1 s, rc 0, 602 COMPLETE); it is
  the *test* that is missing, and the hand-edited-record threat model is precisely the one the
  patch cites to justify the dedup (`flow.py:870`) and path-escape guards, both of which *are*
  pinned. A cyclic-lineage regression test costs ~10 lines.

- **NEEDS-HUMAN — `template/src/pdca_harness/flow.py:1181`
  (`budget = allowance * max(1, len(wave_list))`): adoption is strictly weaker than the manual
  restart it replaces, which is a fitness call, not a bug.** `pdca flow 500` sets out to drive
  one wave, so the whole run — parent plus however many adopted generations — gets
  `max_passes` passes total, while the operator's current remedy (`pdca flow 601 602 …`) gets
  `max_passes` **per wave**. At the default 20 a parent wave (~2 passes) plus a six-child brood
  levelled into six waves has ~3 passes each; a wider or deeper brood stops mid-run. It is
  loud, resumable and documented in the diff (`docs/07-crosscutting.md`, "One consequence
  worth knowing before you type it"), and `test_the_pass_budget_is_one_cap_for_the_whole_run`
  pins the behaviour — so this is for the human to ratify at sign-off, not for the builder to
  re-decide.

## Attempted and could not refute

- Mid-run re-scheduling (`_reschedule`, `flow.py:916`) dropping or re-ordering *original*
  batch members: dependency edges point backwards, so any dep path between two still-pending
  bundles runs entirely through still-pending bundles — order is preserved, and a conflict
  naming an already-driven bundle is correctly moot. Every case I could build where the
  tolerant path holds an original (prereq left non-COMPLETE) is a case `_runnable` already
  skipped loudly pre-patch; disposition unchanged.
- The strict-contract claim ("only what adoption ADDS goes through the tolerant path"): the
  seed splice at `k=-1` does re-level the *whole* remainder tolerantly, but
  `waves.compute_waves` still raises first (`flow.py:1175`), and I could not construct an id
  list that `check_dep_graph` admits and `partition_schedulable` then holds — the two resolve
  `Stacks on` / archived / out-of-batch prereqs identically (`waves.py:76`, `waves.py:262`).
- Path traversal: `../../etc`, `x/../600`, absolute ids and empty ids all fail the
  `d.parent != cfg.bundle_root` lexical check or land inside the root harmlessly.
- Budget non-regression for runs that adopt nothing: `spent ≤ allowance × k` before wave `k`,
  so `spent >= budget` provably cannot fire — verified by construction and by
  `test_a_run_that_adopts_nothing_keeps_a_full_budget_per_wave`.
- `_drive_wave`'s new `int` return: every exit path returns `used`; no other production caller
  exists (`flow.flow` keeps its own loop and, per `cli.py:614`, is no longer on any CLI path).
- Recursion/dedup across waves, `examined` being pre-seeded with every driven bundle, held
  children staying out of `bundles` / `batch_names`, and the announcement being read back from
  the recomputed tail: all behave as documented under direct scenario runs.
