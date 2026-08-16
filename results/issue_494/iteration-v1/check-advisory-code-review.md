# Check advisory — code review (issue #494)

Scope: correctness bugs the patch introduces, and reuse/simplification/efficiency —
distinct from the reviewer leaf's fix-adequacy lens. Grounded on
`$PDCA_TARGET/template/src/pdca_harness/{leaves.py,worktree.py,act.py,flow.py,lane.py}`.

## Findings

- NEEDS-HUMAN — `leaves.py:2006-2036` (`_target_grant`) reuses `_reviewer_target`
  (`leaves.py:1973-2003`) unchanged for `run_act` (`leaves.py:3428-3438`), but Act's
  usage is a materially different reuse context than the reviewer's. `_reviewer_target`
  prefers the **lane worktree** (`worktree.path`, `worktree.py:135-148`), and
  `worktree.py:10-19` documents that worktree as "**reset and reused** per cycle" and
  "a warm checkout cache, never a trusted **content** cache" — gate reads
  (`for_gate`) deliberately reconstruct `base + patch.diff` rather than trust what is
  on disk there. The reviewer's use of this resolution is safe because it runs
  synchronously right after that same bundle's Do (same cycle, no intervening reset).
  Act reviews `act_mod.frozen_bundles(cfg)` (`act.py:87-94`) — bundles that froze over
  **many prior cycles**, often long before the Act session runs. By the time Act's
  session is spawned, the same lane-slot worktree directory (`worktree.py:107-112`,
  keyed only by `(primary checkout, lane slot)`, not by bundle) has almost certainly
  been reset and rebuilt for other, later bundles targeting the same repo — so the
  directory `_target_grant` admits for a given frozen bundle `d` need not hold `d`'s
  patch at all; it can silently hold a different bundle's (possibly still-unreviewed,
  or even concurrently in-progress, since only the Act *session* is lock-serialized —
  `act.py`'s `act_session`/`act_due` — not Do in other lanes) tree state. No ownership
  check (`worktree.owner_of`, `worktree.py:124-132`) gates the admission. This isn't
  merely stale grounding text (as with `_reviewer_target`'s own best-effort fallback);
  it is a directory grant handed to a live interactive+human session, so the content
  the session actually reads for a historical bundle can be wrong or belong to
  unrelated work. The brief itself flags this as open ("`worktree.py:104-110` — the
  single source of a lane worktree's path, **if lane trees are admitted at all**"),
  so this is the architectural question that citation was gesturing at, now
  materialized as a concrete risk in `run_act`'s call path specifically (not
  `do_plan`/`run_signoff`/`run_publish`, which act on the SAME cycle's own bundle and
  so keep the reviewer's original same-cycle safety property). The new test
  (`test_leaf_workspace_admission.py:143-158`, `test_act_admits_the_resolved_target_checkouts`)
  does not exercise this: its fixture repos have no `.pdca-wt*` directory on disk at
  all, so `worktree.path` always misses and the test only covers the sibling-checkout
  fallback branch — the worktree-reuse path for Act is untested as well as unguarded.

- `leaves.py:2028-2032` — the loop in `_target_grant` calls `_reviewer_target(d, cfg)`
  once per bundle in `bundles` *before* checking `seen`, so for `run_signoff_batch` /
  `run_act` with several bundles resolving to the **same** target checkout, the
  worktree-less fallback branch of `_reviewer_target`
  (`leaves.py:1989-2001`) runs `git -C <p> fetch <base_remote>` once **per bundle**
  instead of once per unique resolved directory — e.g.
  `test_signoff_batch_dedupes_a_shared_target` (`test_leaf_workspace_admission.py:243-249`)
  exercises exactly this shape and would, against real repos, fire the fetch twice for
  one target. Harmless (best-effort, exit code ignored) but avoidable: resolving
  targets into a `dict[Path-or-None, ...]` keyed by the already-visited bundle's
  resolution, or simply checking `seen` before invoking `_reviewer_target`'s fetch,
  would cut the redundant network calls without changing the observable argv.

## Not flagged

- The five call sites (`do_plan`, `run_signoff`, `run_signoff_batch`, `run_act`,
  `run_publish`) all pass `bundles, cfg, profile` in the same order and reuse an
  already-resolved `profile` where one existed (`run_publish`, `leaves.py:3496,3504`)
  rather than re-resolving it — no duplicated `families.resolve` call introduced.
- `extra_argv` is threaded through the existing `_invoke` machinery unchanged
  (`leaves.py:611,619,635`): it lands ahead of the interactive seed separator/positional,
  so criterion (iv) (the `--` / seed-positional contract, #396) holds structurally, not
  just by inspection of this diff.
- The `generic`/no-grounding-flag skip (`leaves.py:2026-2027`) and the empty-grant
  path for an unresolvable target (`do_plan` pre-brief) both match the reviewer's own
  conditional shape the brief asked to mirror.
