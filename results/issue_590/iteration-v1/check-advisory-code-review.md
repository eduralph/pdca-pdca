# Advisory code review — issue 590 (flow-dep-on-seed-child-refused)

Lenses: correctness bugs the patch introduces; reuse / simplification / efficiency.
Grounded on `$PDCA_TARGET` (patched tree). Advisory only.

**Overall: no correctness bug found.** The fix does what the brief asks. The quiet walk
gives the same answers as `_adoptable` for every case the brief defines (plain-id guard,
containment guard, walk through split children, terminal / no-brief children not offered).
`check_dep_graph` behaves exactly as before when `offered` is empty. Only the strict call
passes it. C4 goes red for the right reason: all three new positive tests fail pre-fix on
the exact refusal message (`gate-logs/C4-verify.log`). T3 runs green. The holder-process
test cleans up in the right order (release runs before rmtree, because cleanups run last
in, first out) and uses `drive_claim.Run.take`'s real "None means held" contract.

Findings, all minor:

- `template/src/pdca_harness/waves.py:95` — **cycle through an offered child is no longer
  refused up front.** An offered name adds no edge to the strict levelling, so a loop like
  `810 Depends on: 602` + `602 Depends on: 810` (602 a seed child) now passes the strict
  check. The `k=-1` splice re-levels through the tolerant path (`_reschedule`), which holds
  both and reports them rather than raising. Before the patch the same request was refused
  with rc 2 (as an unresolved dependency). The end state is safe (nothing built, both
  PLANNED, reported), and the brief explicitly asked for "adds no edge". But it is a small
  change to "unschedulable ⇒ refused before any work" that no test pins. Noting it so the
  human knows. No action needed unless they want the cycle refused up front too.
- `template/src/pdca_harness/flow.py:1774-1792` — **one `try` per parent, not per child.**
  If one child's `state.state` / `_inside_bundle_root` raises, the `except` drops that
  child *and every later sibling* in the same record. That fails safe (fewer offered names
  means today's strict refusal), but it can refuse an edge to a healthy sibling that
  adoption will in fact adopt a moment later. Moving the `try` inside the `for cid` loop
  would limit the damage to the bad entry. Low likelihood (those helpers are documented as
  never raising), so this is a cleanup, not a defect.
- `template/src/pdca_harness/flow.py:1743-1793` — **the filter is a second copy of
  `_adoptable`'s rules** (`flow.py:1103-1244`): plain-id, containment, terminal/split walk,
  no-brief. The brief required this (no refactor of `_adoptable`, no second noisy pass), and
  the two match today. Small differences: the copy skips `_adoptable`'s dedupe-by-resolved-
  path and its `known` check. Neither changes the result, because `check_dep_graph` checks
  `names` first and an aliased name that adoption then skips is just held at the re-level.
  The risk is drift: a future change to what `_adoptable` accepts must also be made here, or
  the strict check and adoption will disagree. A one-line cross-reference comment inside
  `_adoptable` pointing at `_offered_by_seeds` would make that harder to miss. Not a blocker.
- `template/src/pdca_harness/flow.py:1770` — `to_examine.pop(0)` on a list is O(n) per
  pop. The lists are tiny (one lineage tree), so this does not matter in practice. A
  `collections.deque` or a plain `pop()` (order does not affect a set result) would be
  cleaner. Nit.

No NEEDS-HUMAN items. Nothing above needs an architecture or scope call, and none of it
is a defect the builder must fix before sign-off.
